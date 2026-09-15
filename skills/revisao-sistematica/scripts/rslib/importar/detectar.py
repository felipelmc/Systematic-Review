"""Leitura tolerante de exportações e detecção do formato por assinatura.

USO
    from rslib.importar import detectar
    det = detectar.detectar("01-busca/brutos/savedrecs.txt")
    det.familia, det.formato, det.motivo      # ("wos", "wos_txt", "primeira linha 'FN ...'")
    cabecalho, linhas = detectar.ler_tabela("scopus.csv")

Por que por assinatura e não por extensão: as bases exportam o mesmo conteúdo
com extensões enganosas (o "bdtd.xlsx" do exemplo do REFIS é na verdade CAPES via capesR;
o "wos_scielo.txt" é TSV do WoS com registros SciELO; RIS chega como .txt).
A detecção olha só o conteúdo: cabeçalhos de colunas, marcadores de início
de registro (`FN `, `PT\\t`, `TY  - `, `@article{ WOS:`) e bytes mágicos de
planilhas. Em caso de dúvida cai no leitor genérico, que exige conferência.

Leitura tolerante: remove BOM, normaliza CRLF/CR para LF, tenta UTF-8 e cai
para cp1252/latin-1 (dados abertos da CAPES), descobre o separador (vírgula,
ponto e vírgula ou tabulação) pelo cabeçalho e aumenta o limite de tamanho de
campo do módulo csv (a coluna de referências do Scopus passa de 131 kB).
Só stdlib no topo do módulo: pandas é importado dentro de `ler_planilha`, para
que a ausência dele não derrube o dispatcher `rs.py`.
"""

import csv
import io
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

# O maior inteiro aceito varia por plataforma; o limite padrão (131 kB) quebra no Scopus.
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:  # pragma: no cover - plataformas com long de 32 bits
    csv.field_size_limit(2**31 - 1)


class ErroImportacao(Exception):
    """Erro de uso ou de dados na importação; `codigo` segue a convenção de saída do rs.py."""

    def __init__(self, mensagem, codigo=1):
        super().__init__(mensagem)
        self.codigo = codigo


@dataclass
class Deteccao:
    familia: str   # wos|scopus|openalex|scielo|pop|zotero|ris|capes|bdtd|generico
    formato: str   # ver FORMATOS
    motivo: str    # assinatura que decidiu (vai para o log, para auditoria)


@dataclass
class Leitura:
    """Resultado de um leitor: registros brutos (dicts intermediários) e metadados."""

    registros: list
    avisos: list = field(default_factory=list)
    data_busca: str = None


# formato -> família padrão. Um formato pode ser lido por mais de uma família
# quando o usuário força --fonte (ex.: TSV do WoS com registros SciELO).
FORMATOS = {
    "wos_txt": "wos",          # WoS plaintext (FN Clarivate ... ER / EF)
    "wos_tsv": "wos",          # WoS tab-delimited (PT\tAU\t...), inclusive SciELO Citation Index
    "wos_tabela": "wos",       # planilha com colunas-tag do WoS (PT, AU, TI, UT)
    "wos_bib": "wos",          # WoS BibTeX (@article{ WOS:...)
    "wos_xls": "wos",          # WoS Excel (colunas por extenso: Article Title, UT (Unique WOS ID))
    "scopus_csv": "scopus",
    "openalex_csv": "openalex",
    "openalex_json": "openalex",  # JSON, página da API ({"results": [...]}) ou JSONL
    "pop_csv": "pop",          # Publish or Perish / Google Scholar
    "scielo_csv": "scielo",    # portal search.scielo.org
    "zotero_csv": "zotero",
    "ris": "ris",
    "bibtex": "generico",      # BibTeX que não é do WoS (Zotero, Mendeley, Scholar)
    "capes_csv": "capes",      # dados abertos do Catálogo de Teses e Dissertações
    "capesr": "capes",         # tabela produzida pelo pacote R capesR
    "bdtd_csv": "bdtd",
    "bdtd_json": "bdtd",       # API VuFind da BDTD
    "generico": "generico",
}

FAMILIAS = ["wos", "scopus", "openalex", "scielo", "pop", "zotero", "ris", "capes", "bdtd", "generico"]

_CODIFICACOES = ("utf-8-sig", "cp1252", "latin-1")


# ---------------------------------------------------------------------------
# Leitura de texto
# ---------------------------------------------------------------------------
def decodificar(dados, avisos=None):
    """Bytes -> str sem BOM e com quebras de linha LF."""
    for cod in _CODIFICACOES:
        try:
            texto = dados.decode(cod)
        except UnicodeDecodeError:
            continue
        if cod != "utf-8-sig" and avisos is not None:
            avisos.append(f"arquivo não está em UTF-8; lido como {cod}")
        break
    texto = texto.lstrip("\ufeff")
    return texto.replace("\r\n", "\n").replace("\r", "\n")


def ler_texto(caminho, avisos=None):
    return decodificar(Path(caminho).read_bytes(), avisos)


def tipo_planilha(caminho):
    """'xls', 'xlsx' ou None pelos bytes mágicos (não pela extensão)."""
    with open(caminho, "rb") as f:
        inicio = f.read(8)
    if inicio.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "xls"
    if inicio.startswith(b"PK\x03\x04"):
        return "xlsx"
    return None


def chave_coluna(nome):
    """Forma comparável de um nome de coluna: ASCII, minúsculo, só letras e dígitos.

    'Author(s)' -> 'authors'; 'Fulltext URL ' -> 'fulltexturl'; 'Título' -> 'titulo'.
    """
    s = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def achar_coluna(cabecalho, *aliases):
    """Primeira coluna do cabeçalho que casa (por chave_coluna) com algum alias, na ordem dos aliases."""
    por_chave = {}
    for c in cabecalho:
        por_chave.setdefault(chave_coluna(c), c)
    for alias in aliases:
        encontrada = por_chave.get(chave_coluna(alias))
        if encontrada is not None:
            return encontrada
    return None


class Colunas:
    """Acesso a uma linha por apelidos de coluna, resolvidos uma vez por arquivo.

    `Colunas(cabecalho).valor(linha, "Author full names", "Authors")` devolve o
    primeiro valor não vazio entre as colunas existentes, na ordem dada.
    """

    def __init__(self, cabecalho):
        self.cabecalho = list(cabecalho)
        self._cache = {}

    def nome(self, apelido):
        if apelido not in self._cache:
            self._cache[apelido] = achar_coluna(self.cabecalho, apelido)
        return self._cache[apelido]

    def valor(self, linha, *apelidos):
        for apelido in apelidos:
            col = self.nome(apelido)
            if col is not None:
                v = str(linha.get(col, "") or "").strip()
                if v:
                    return v
        return ""


def _cabecalho_unico(nomes):
    """Remove espaços das pontas e desambigua nomes repetidos com sufixo .1, .2 (como o pandas)."""
    vistos, saida = {}, []
    for nome in nomes:
        nome = str(nome).strip().lstrip("\ufeff")
        if nome in vistos:
            vistos[nome] += 1
            nome = f"{nome}.{vistos[nome]}"
        else:
            vistos[nome] = 0
        saida.append(nome)
    return saida


def descobrir_separador(primeira_linha):
    """Separador mais frequente no cabeçalho entre vírgula, ponto e vírgula e tabulação."""
    contagens = {sep: primeira_linha.count(sep) for sep in (",", ";", "\t")}
    melhor = max(contagens, key=lambda s: contagens[s])
    return melhor if contagens[melhor] > 0 else ","


def ler_csv(caminho, texto=None, separador=None, avisos=None, sem_aspas=False):
    """Lê CSV/TSV em (cabecalho, linhas) com linhas como dicts de strings.

    `skipinitialspace` resolve o ID do portal SciELO, que vem como ` "S0103-..."`.
    `sem_aspas` é usado no TSV do WoS, que não usa aspas e tem `"` soltas nos resumos.
    Linhas totalmente vazias são ignoradas; linhas curtas são completadas com ''.
    """
    if texto is None:
        texto = ler_texto(caminho, avisos)
    primeira = texto.split("\n", 1)[0]
    sep = separador or descobrir_separador(primeira)
    opcoes = {"delimiter": sep, "skipinitialspace": True}
    if sem_aspas:
        opcoes = {"delimiter": sep, "quoting": csv.QUOTE_NONE}
    leitor = csv.reader(io.StringIO(texto), **opcoes)
    try:
        cabecalho = _cabecalho_unico(next(leitor))
    except StopIteration:
        return [], []
    linhas = []
    for bruta in leitor:
        if not any(str(v).strip() for v in bruta):
            continue
        valores = [str(v).strip() for v in bruta] + [""] * (len(cabecalho) - len(bruta))
        linhas.append(dict(zip(cabecalho, valores)))
    return cabecalho, linhas


def valor_celula(v):
    """Converte célula do pandas em string: NaN -> '', 14.0 -> '14', datas -> ISO."""
    if v is None:
        return ""
    if isinstance(v, float):
        if v != v:
            return ""
        return str(int(v)) if v.is_integer() else repr(v)
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()[:10] if getattr(v, "hour", 0) == 0 else v.isoformat()
        except (TypeError, ValueError):  # pragma: no cover - NaT
            return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan", "nat"} else s


def ler_planilha(caminho, planilha=0, apenas_cabecalho=False):
    """Lê .xls/.xlsx com pandas (xlrd/openpyxl). Dependência ausente -> ErroImportacao código 3."""
    try:
        import pandas as pd
    except ImportError as e:  # pragma: no cover - pandas é obrigatório
        raise ErroImportacao("pandas não instalado; rode `pip install pandas openpyxl xlrd`", 3) from e
    motor = "xlrd" if tipo_planilha(caminho) == "xls" else "openpyxl"
    try:
        __import__(motor)
    except ImportError as e:
        raise ErroImportacao(f"pacote {motor} ausente para ler {Path(caminho).name}; rode `pip install {motor}`", 3) from e
    try:
        df = pd.read_excel(caminho, sheet_name=planilha, dtype=object, engine=motor,
                           nrows=0 if apenas_cabecalho else None)
    except ValueError as e:
        raise ErroImportacao(f"não foi possível ler a planilha {Path(caminho).name}: {e}") from e
    cabecalho = _cabecalho_unico(df.columns)
    df.columns = cabecalho
    linhas = []
    for registro in df.to_dict(orient="records"):
        convertido = {k: valor_celula(v) for k, v in registro.items()}
        if any(convertido.values()):
            linhas.append(convertido)
    return cabecalho, linhas


def ler_tabela(caminho, planilha=0, avisos=None):
    """CSV/TSV ou planilha, conforme os bytes do arquivo."""
    if tipo_planilha(caminho):
        return ler_planilha(caminho, planilha=planilha)
    return ler_csv(caminho, avisos=avisos)


# ---------------------------------------------------------------------------
# JSON / JSONL
# ---------------------------------------------------------------------------
def ler_json_objetos(caminho, avisos=None):
    """Objetos de um JSON (lista, objeto único, página com 'results'/'records') ou JSONL.

    JSONL: uma linha final truncada (queda durante a gravação) vira aviso; linha
    inválida no meio do arquivo é erro, porque perder registros em silêncio
    quebraria as contagens do PRISMA.
    """
    avisos = avisos if avisos is not None else []
    texto = ler_texto(caminho, avisos).strip()
    if not texto:
        return []
    try:
        dados = json.loads(texto)
        return _desembrulhar(dados)
    except json.JSONDecodeError:
        pass
    objetos = []
    linhas = [l for l in texto.split("\n") if l.strip()]
    for i, linha in enumerate(linhas, 1):
        try:
            objetos.extend(_desembrulhar(json.loads(linha)))
        except json.JSONDecodeError as e:
            if i == len(linhas):
                avisos.append(f"última linha do JSONL truncada/ inválida foi ignorada (linha {i})")
                continue
            raise ErroImportacao(f"JSON inválido na linha {i} de {Path(caminho).name}: {e}") from e
    return objetos


def _desembrulhar(dados):
    if isinstance(dados, list):
        saida = []
        for item in dados:
            if _eh_pagina(item):
                saida.extend(_desembrulhar(item))
            elif isinstance(item, dict):
                saida.append(item)
        return saida
    if isinstance(dados, dict):
        if _eh_pagina(dados):
            for chave in ("results", "records", "works", "items"):
                if isinstance(dados.get(chave), list):
                    return [o for o in dados[chave] if isinstance(o, dict)]
        return [dados]
    return []


def _eh_pagina(obj):
    return isinstance(obj, dict) and any(isinstance(obj.get(k), list) for k in ("results", "records", "works", "items"))


# ---------------------------------------------------------------------------
# Detecção
# ---------------------------------------------------------------------------
def classificar_colunas(cabecalho, linhas=None):
    """Formato de uma tabela a partir dos nomes de coluna (e, se preciso, da primeira linha)."""
    chaves = {chave_coluna(c) for c in cabecalho}
    primeira = (linhas or [{}])[0] if linhas else {}

    if "gsrank" in chaves or {"citesurl", "ecc", "citesperyear"} <= chaves:
        return Deteccao("pop", "pop_csv", "coluna GSRank/CitesURL do Publish or Perish")
    if "eid" in chaves and ("sourcetitle" in chaves or "title" in chaves):
        return Deteccao("scopus", "scopus_csv", "coluna EID do Scopus")
    fonte_scopus = achar_coluna(cabecalho, "Source")
    if {"authorsid", "sourcetitle"} <= chaves and fonte_scopus and str(primeira.get(fonte_scopus, "")).lower() == "scopus":
        return Deteccao("scopus", "scopus_csv", "coluna Source = Scopus")
    if any(c.startswith("authorships") for c in chaves) or {"displayname", "publicationyear"} <= chaves:
        return Deteccao("openalex", "openalex_csv", "colunas authorships.*/display_name do OpenAlex")
    if {"authors", "languages", "fulltexturl"} <= chaves:
        return Deteccao("scielo", "scielo_csv", "cabeçalho do portal SciELO (Author(s), Language(s), Fulltext URL)")
    if {"itemtype", "abstractnote"} <= chaves:
        return Deteccao("zotero", "zotero_csv", "colunas Item Type/Abstract Note do Zotero")
    if "nmproducao" in chaves or {"anbase", "nmdiscente"} <= chaves:
        return Deteccao("capes", "capes_csv", "colunas NM_PRODUCAO/AN_BASE dos dados abertos da CAPES")
    if {"titulo", "autoria", "anobase"} <= chaves:
        return Deteccao("capes", "capesr", "colunas ano_base/autoria do capesR")
    if "anodedefesa" in chaves or {"autora", "tipodedocumento"} <= chaves:
        return Deteccao("bdtd", "bdtd_csv", "colunas Ano de defesa/Autor(a) da BDTD")
    if "utuniquewosid" in chaves or "utuniqueid" in chaves or {"articletitle", "sourcetitle"} <= chaves:
        return Deteccao("wos", "wos_xls", "colunas UT (Unique WOS ID)/Article Title do WoS")
    if {"pt", "au", "ti", "ut"} <= chaves:
        return Deteccao("wos", "wos_tabela", "colunas-tag PT/AU/TI/UT do WoS")
    return Deteccao("generico", "generico", "nenhuma assinatura conhecida nas colunas")


_RE_WOS_BIB = re.compile(r"^\s*@\s*\w+\s*\{\s*WOS:", re.MULTILINE)
_RE_BIB = re.compile(r"^\s*@\s*(article|book|inbook|incollection|inproceedings|conference|phdthesis|mastersthesis|"
                     r"techreport|misc|unpublished|online|report|thesis|proceedings|manual)\s*\{", re.MULTILINE | re.IGNORECASE)
_RE_RIS = re.compile(r"^TY\s{1,2}-", re.MULTILINE)


def detectar(caminho):
    """Deteccao(familia, formato, motivo) do arquivo. Não lança erro para formato desconhecido."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroImportacao(f"arquivo não encontrado: {caminho}")
    if tipo_planilha(caminho):
        cabecalho, _ = ler_planilha(caminho, apenas_cabecalho=True)
        return classificar_colunas(cabecalho)

    with open(caminho, "rb") as f:
        inicio = decodificar(f.read(256_000))
    corpo = inicio.lstrip()
    primeira = corpo.split("\n", 1)[0]

    if primeira.startswith("PT\t") and ("\tAU\t" in primeira or "\tTI\t" in primeira):
        return Deteccao("wos", "wos_tsv", "cabeçalho 'PT\\tAU' do tab-delimited do WoS")
    if re.match(r"^FN ", corpo) or (re.match(r"^PT [A-Z]", corpo) and re.search(r"^ER\s*$", corpo, re.MULTILINE)):
        return Deteccao("wos", "wos_txt", "marcador 'FN'/'PT ... ER' do plaintext do WoS")
    if _RE_WOS_BIB.search(corpo):
        return Deteccao("wos", "wos_bib", "entrada BibTeX com chave 'WOS:'")
    if _RE_RIS.search(corpo):
        return Deteccao("ris", "ris", "linhas 'TY  - ' de RIS")
    if corpo.startswith("@") or _RE_BIB.search(corpo):
        return Deteccao("generico", "bibtex", "entradas BibTeX sem chave WOS:")
    if corpo.startswith("{") or corpo.startswith("["):
        objetos = ler_json_objetos(caminho, [])
        amostra = objetos[:5]
        if any(str(o.get("id", "")).startswith(("https://openalex.org/W", "W")) and
               ("authorships" in o or "abstract_inverted_index" in o or "publication_year" in o) for o in amostra):
            return Deteccao("openalex", "openalex_json", "objetos com id https://openalex.org/W e authorships")
        if any(isinstance(o.get("authors"), dict) and ("formats" in o or "publicationDates" in o) for o in amostra):
            return Deteccao("bdtd", "bdtd_json", "objetos VuFind com authors.primary/formats da BDTD")
        return Deteccao("generico", "json_desconhecido", "JSON sem assinatura conhecida")

    cabecalho, primeira_linha = _cabecalho_e_primeira_linha(inicio)
    return classificar_colunas(cabecalho, [primeira_linha] if primeira_linha else None)


def _cabecalho_e_primeira_linha(texto):
    """Cabeçalho e primeira linha de dados de um trecho inicial (que pode cortar um registro no meio)."""
    sep = descobrir_separador(texto.split("\n", 1)[0])
    leitor = csv.reader(io.StringIO(texto), delimiter=sep, skipinitialspace=True)
    try:
        cabecalho = _cabecalho_unico(next(leitor))
    except (StopIteration, csv.Error):
        return [], None
    try:
        valores = next(leitor)
    except (StopIteration, csv.Error):
        return cabecalho, None
    return cabecalho, dict(zip(cabecalho, [v.strip() for v in valores]))
