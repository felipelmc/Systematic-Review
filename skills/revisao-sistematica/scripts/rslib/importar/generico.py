"""Montagem do registro unificado e importador genérico (por mapa de colunas ou por apelidos).

USO
    rs.py importar --arquivo planilha.xlsx --busca-id MN1 --mapa mapa.json
    rs.py importar --arquivo lista.csv --busca-id MN1 --fonte generico   # apelidos automáticos

    mapa.json (chaves = colunas de esquema.COLUNAS_REGISTROS; valores = coluna do arquivo
    ou lista de colunas; lista = primeira não vazia, ou concatenação em palavras_chave,
    pais_afiliacao e instituicao):
    {
      "fonte": "generico",
      "planilha": "Plan1",
      "separador_autores": ";",
      "colunas": {"titulo": "Title", "autores": "Authors", "ano": "Year",
                  "doi": "DOI", "resumo": "Abstract",
                  "palavras_chave": ["Author Keywords", "Keywords"]}
    }
    Um dicionário "plano" ({"titulo": "Title", ...}) também é aceito.

Este módulo concentra o que todos os importadores compartilham:

- `montar_registro(bruto)`: cada leitor específico devolve um dict intermediário
  com os campos que a fonte oferece (listas ou strings, ainda sujos) e esta
  função aplica `normalizar.*` do mesmo jeito para todas as fontes. Assim a
  normalização de DOI, título, autores canônicos, ano, idioma e tipo não
  diverge entre bases, e o dedup compara iguais com iguais.
- Tabela de pré-tipos: códigos de tipo das fontes (journalArticle, JOUR,
  book-chapter, research-article, Conference review...) são traduzidos antes de
  `normalizar.tipo_publicacao`, que casa por expressões regulares e erraria
  alguns ("Conference review" viraria revisão; "peer-review" do OpenAlex também).
- Tipo sem informação na fonte fica vazio (sem dado), não "outro": filtros
  formais tratam campo ausente como `sem_dado` e mantêm o registro, enquanto
  "outro" seria lido como um tipo conhecido e poderia excluir literatura
  cinzenta sem justificativa (Apêndice D da base de conhecimento, item 1).
- Leitor de BibTeX próprio (sem bibtexparser): chaves aninhadas, valores em
  várias linhas e comandos LaTeX comuns do WoS ({[}Anonymous], \\&, {''}).
  Evita dependência opcional e mantém o resultado determinístico.
"""

import re
import unicodedata

from .. import chave as _chave
from .. import esquema, normalizar
from .detectar import ErroImportacao, Leitura, achar_coluna, ler_tabela, ler_texto

CAMPOS_CONTROLE = {
    "id_registro", "busca_id", "fonte", "metodo_identificacao", "arquivo_origem",
    "linha_origem", "estrutura", "importado_em",
}
CAMPOS_CONTEUDO = [c for c in esquema.COLUNAS_REGISTROS if c not in CAMPOS_CONTROLE]
CAMPOS_CONCATENADOS = {"palavras_chave", "pais_afiliacao", "instituicao"}

# ---------------------------------------------------------------------------
# Tipos de publicação: códigos das fontes -> termo que normalizar entende ou tipo final
# ---------------------------------------------------------------------------
_PRE_TIPOS = {
    # Zotero (Item Type)
    "journalarticle": "artigo", "booksection": "capitulo", "book": "livro", "thesis": "tese",
    "conferencepaper": "evento", "presentation": "evento", "report": "relatorio", "preprint": "preprint",
    "manuscript": "outro", "webpage": "outro", "blogpost": "outro", "magazinearticle": "outro",
    "newspaperarticle": "outro", "encyclopediaarticle": "outro", "dictionaryentry": "outro",
    "document": "outro", "dataset": "outro", "computerprogram": "outro", "letter": "editorial",
    # RIS (TY)
    "jour": "artigo", "ejour": "artigo", "jfull": "artigo", "chap": "capitulo", "echap": "capitulo",
    "ebook": "livro", "edbook": "livro", "thes": "tese", "conf": "evento", "cpaper": "evento",
    "rprt": "relatorio", "govdoc": "relatorio", "unpb": "preprint", "gen": "outro", "mgzn": "outro",
    "news": "outro", "elec": "outro", "blog": "outro", "data": "outro", "abst": "outro", "ser": "outro",
    # BibTeX (tipo de entrada)
    "article": "artigo", "inbook": "capitulo", "incollection": "capitulo", "inproceedings": "evento",
    "proceedings": "evento", "conference": "evento", "phdthesis": "tese", "mastersthesis": "dissertacao",
    "techreport": "relatorio", "misc": "outro", "unpublished": "preprint", "online": "outro",
    # OpenAlex (type)
    "bookchapter": "capitulo", "dissertation": "tese", "peerreview": "outro", "paratext": "outro",
    "libguides": "outro", "supplementarymaterials": "outro", "standard": "outro", "grant": "outro",
    "other": "outro", "erratum": "errata", "retraction": "errata", "review": "revisao",
    # SciELO (research-article etc.)
    "researcharticle": "artigo", "reviewarticle": "revisao", "briefreport": "artigo", "casereport": "artigo",
    "rapidcommunication": "artigo", "articlecommentary": "editorial", "bookreview": "editorial",
    "productreview": "editorial", "reply": "editorial", "correction": "errata", "partialretraction": "errata",
    "addendum": "errata", "abstract": "outro", "announcement": "outro", "obituary": "outro",
    # Scopus (Document Type)
    "conferencereview": "outro", "conferencepaper2": "evento", "shortsurvey": "revisao", "datapaper": "artigo",
    # WoS (PT)
    "j": "artigo", "b": "livro", "s": "livro", "c": "evento", "p": "outro",
}


def tipo_de(valor):
    """Tipo de publicação final a partir do tipo original da fonte ('' se a fonte não informa)."""
    s = normalizar.texto(valor)
    if not s:
        return ""
    chave = re.sub(r"[^a-z0-9]", "", normalizar.ascii_fold(s).lower())
    pre = _PRE_TIPOS.get(chave)
    if pre in esquema.TIPOS_PUBLICACAO:
        return pre
    return normalizar.tipo_publicacao(pre or s)


# ---------------------------------------------------------------------------
# Idioma
# ---------------------------------------------------------------------------
_IDIOMAS_EXTRA = {
    "turkish": "tr", "hungarian": "hu", "czech": "cs", "croatian": "hr", "catalan": "ca", "galician": "gl",
    "arabic": "ar", "hebrew": "he", "greek": "el", "swedish": "sv", "norwegian": "no", "danish": "da",
    "finnish": "fi", "romanian": "ro", "ukrainian": "uk", "indonesian": "id", "malay": "ms", "persian": "fa",
    "lithuanian": "lt", "slovenian": "sl", "slovak": "sk", "serbian": "sr", "bulgarian": "bg",
    "estonian": "et", "latvian": "lv", "afrikaans": "af", "vietnamese": "vi", "thai": "th", "hindi": "hi",
    "portugues brasileiro": "pt", "ingles": "en", "espanol": "es",
}
_CODIGOS_ISO1 = set(_IDIOMAS_EXTRA.values()) | {"pt", "en", "es", "fr", "de", "it", "pl", "zh", "ru", "ja", "ko", "nl"}


def idioma_de(valor):
    """ISO 639-1 a partir de nome, código de 3 letras ou etiqueta de localidade ('pt-BR')."""
    if isinstance(valor, (list, tuple)):
        valor = next((v for v in valor if not normalizar.vazio(v)), "")
    s = normalizar.ascii_fold(valor).lower().strip()
    if not s:
        return ""
    m = re.match(r"^([a-z]{2})[-_][a-z]{2,4}$", s)
    if m:
        return m.group(1)
    codigo = normalizar.idioma(s)
    if codigo:
        return codigo
    primeiro = re.split(r"[;,/|]", s)[0].strip()
    if primeiro in _CODIGOS_ISO1:
        return primeiro
    return _IDIOMAS_EXTRA.get(primeiro, "")


# ---------------------------------------------------------------------------
# Autores
# ---------------------------------------------------------------------------
_PARTICULAS_NOME = {"de", "da", "do", "dos", "das", "e", "del", "della", "di", "du", "van", "von", "der", "la", "le", "y"}


def nome_proprio(nome):
    """'MANOEL DOS SANTOS E SILVA' -> 'Manoel dos Santos e Silva' (só para nomes todos em maiúsculas)."""
    s = normalizar.texto(nome)
    if not s or not s.isupper():
        return s
    saida = []
    for i, token in enumerate(s.lower().split()):
        if i > 0 and token in _PARTICULAS_NOME:
            saida.append(token)
        else:
            saida.append("-".join(p[:1].upper() + p[1:] for p in token.split("-")))
    return " ".join(saida)


_INSTITUCIONAL = re.compile(
    r"\b(instituto|institute|institut|grupo|group|universidade|university|universidad|faculdade|faculty|"
    r"organi[sz]ation|organiza[cç][aã]o|organizaci[oó]n|minist[eé]rio|ministry|secretaria|banco|bank|"
    r"funda[cç][aã]o|foundation|fundaci[oó]n|centro|center|centre|associa[cç][aã]o|association|council|"
    r"conselho|ag[eê]ncia|agency|comiss[aã]o|commission|committee|comit[eê]|departamento|department|"
    r"tribunal|governo|government|prefeitura|consortium|cons[oó]rcio|network|observat[oó]rio|"
    r"programa|programme|project|projeto|equipe|collaboration|colabora[cç][aã]o|"
    r"ipea|ibge|oecd|ocde|unesco|unicef|world bank|united nations)\b",
    re.IGNORECASE,
)


def eh_institucional(nome):
    """Autoria institucional ('Instituto Fictício de Pesquisa') não deve ser invertida em 'Pesquisa, Instituto...'."""
    s = normalizar.texto(nome)
    return bool(s) and "," not in s and bool(_INSTITUCIONAL.search(s))


def autor_canonico(nome):
    """Um autor já separado em 'Sobrenome, Nomes'.

    Mesma regra do laço interno de normalizar.autores_canonicos, aplicada item a
    item: a função congelada re-parte a string com chave.lista_autores, o que
    quebraria itens já separados como "Costa Lima, Ana Maria" em dois autores.
    Acrescenta duas proteções: autoria institucional fica como está e espaços
    duplicados deixados pela remoção do sobrenome são colapsados.
    """
    a = normalizar.texto(nome).strip(" ;,")
    if not a:
        return ""
    if "," in a:
        sob, nomes = a.split(",", 1)
        return f"{sob.strip()}, {nomes.strip()}".strip(", ")
    if eh_institucional(a):
        return a
    sob = _chave.sobrenome(a)
    if not sob:
        return a
    resto = re.sub(r"\s+", " ", a.replace(sob, "", 1)).strip()
    return f"{sob}, {resto}".strip(", ")


def autores_canonicos(valor, corporativos=False):
    """Lista (itens já separados) ou string (separada por chave.lista_autores) -> 'Sob, Nomes | Sob, Nomes'."""
    if isinstance(valor, (list, tuple)):
        itens = [normalizar.texto(v) for v in valor if not normalizar.vazio(v)]
    elif normalizar.vazio(valor):
        return ""
    else:
        texto = normalizar.texto(valor)
        itens = [texto] if eh_institucional(texto) else _chave.lista_autores(texto)
    if corporativos:
        return " | ".join(i for i in itens if i)
    return " | ".join(c for c in (autor_canonico(i) for i in itens) if c)


def sobrenome_primeiro(autores):
    """Sobrenome do primeiro autor canônico; autoria institucional devolve o nome inteiro."""
    if not autores:
        return ""
    primeiro = autores.split(" | ")[0]
    if eh_institucional(primeiro):
        return primeiro
    return normalizar.sobrenome_primeiro_autor(autores)


# ---------------------------------------------------------------------------
# Utilidades de campo
# ---------------------------------------------------------------------------
def dividir(valor, separadores=";"):
    """String com separadores -> lista limpa; lista -> lista limpa."""
    if normalizar.vazio(valor):
        return []
    if isinstance(valor, (list, tuple)):
        itens = []
        for v in valor:
            itens.extend(dividir(v, separadores))
        return itens
    padrao = "|".join(re.escape(s) for s in separadores)
    return [p for p in (normalizar.texto(x) for x in re.split(padrao, str(valor))) if p]


def unicos(itens):
    """Remove repetições preservando a ordem (comparação sem caixa)."""
    vistos, saida = set(), []
    for item in itens:
        chave = item.casefold()
        if item and chave not in vistos:
            vistos.add(chave)
            saida.append(item)
    return saida


def pais_de_endereco(endereco):
    """País de um endereço de afiliação: último trecho após vírgula ('..., Baton Rouge, LA 70803 USA.' -> 'USA')."""
    s = normalizar.texto(re.sub(r"\[[^\]]*\]", " ", str(endereco or ""))).strip(" .;")
    if not s:
        return ""
    ultimo = s.rsplit(",", 1)[-1].strip(" .")
    if re.search(r"\bUSA$", ultimo):
        return "USA"
    return ultimo


def inteiro_texto(valor):
    """Contagem inteira como string ('12', '12.0' -> '12'; '1,050' -> '1050'); '' se não for número."""
    s = normalizar.texto(valor).replace(" ", "")
    m = re.fullmatch(r"(\d+)\.0+", s)
    if m:
        return m.group(1)
    s = s.replace(",", "")
    return s if re.fullmatch(r"\d+", s) else ""


def paginas_de(inicial, final=None, artigo=None):
    ini, fim = normalizar.texto(inicial), normalizar.texto(final)
    if ini and fim and ini != fim:
        return f"{ini}-{fim}"
    if ini:
        return ini
    return normalizar.texto(artigo)


_DOI_EM_TEXTO = re.compile(r"(?:doi\.org/|doi:\s*|\bDOI\s*:?\s*)(10\.\d{4,9}/[^\s\"<>]+)", re.IGNORECASE)


def doi_de(valor, *alternativas):
    """DOI normalizado do campo próprio; senão, de URLs doi.org ou de 'DOI: 10.x' em campos livres."""
    d = normalizar.doi(valor)
    if d:
        return d
    for alt in alternativas:
        if normalizar.vazio(alt):
            continue
        m = _DOI_EM_TEXTO.search(str(alt))
        if m:
            d = normalizar.doi(m.group(1))
            if d:
                return d
    return ""


def _primeiro(valor):
    if isinstance(valor, (list, tuple)):
        return next((v for v in valor if not normalizar.vazio(v)), "")
    return valor


def tem_reticencias(texto):
    """Trecho cortado pela fonte (Scholar/PoP): começa ou termina com reticências."""
    t = normalizar.texto(texto)
    return t.startswith(("…", "...")) or t.endswith(("…", "..."))


def _verdadeiro(valor):
    if isinstance(valor, str):
        return valor.strip().lower() not in {"", "0", "false", "nao", "não", "no"}
    return bool(valor)


def _como_lista(valor):
    """Lista de strings limpas sem repartir cada string."""
    if isinstance(valor, (list, tuple)):
        return [t for t in (normalizar.texto(v) for v in valor if not normalizar.vazio(v)) if t]
    t = normalizar.texto(valor)
    return [t] if t else []


def montar_registro(bruto):
    """Dict intermediário de um leitor -> campos de conteúdo de registros.csv, normalizados.

    Chaves aceitas no bruto: id_fonte, doi, titulo, titulo_alt (str|lista), autores (str|lista),
    autores_corporativos (bool), n_autores, ano, tipo_publicacao_orig, tipo_hint, idioma, veiculo,
    volume, numero, paginas, resumo, resumo_truncado (bool), palavras_chave, pais_afiliacao,
    instituicao (str|lista), url, citado_por, doi_extra (textos onde procurar DOI).
    """
    reg = {c: "" for c in CAMPOS_CONTEUDO}
    reg["id_fonte"] = normalizar.texto(_primeiro(bruto.get("id_fonte")))
    reg["url"] = normalizar.texto(_primeiro(bruto.get("url")))
    reg["doi"] = doi_de(_primeiro(bruto.get("doi")), reg["url"], *(bruto.get("doi_extra") or []))
    reg["titulo"] = normalizar.texto(_primeiro(bruto.get("titulo")))

    titulo_cmp = normalizar.titulo_normalizado(reg["titulo"])
    alternativos = [t for t in _como_lista(bruto.get("titulo_alt"))
                    if normalizar.titulo_normalizado(t) != titulo_cmp]
    if not reg["titulo"] and alternativos:
        reg["titulo"] = alternativos.pop(0)
    reg["titulo_alt"] = " | ".join(unicos(alternativos))

    reg["autores"] = autores_canonicos(bruto.get("autores"), bool(bruto.get("autores_corporativos")))
    n = len(reg["autores"].split(" | ")) if reg["autores"] else 0
    declarado = inteiro_texto(bruto.get("n_autores"))
    if declarado and int(declarado) > n:
        n = int(declarado)
    reg["n_autores"] = str(n) if n else ""
    reg["primeiro_autor_sobrenome"] = sobrenome_primeiro(reg["autores"])

    reg["ano"] = normalizar.ano(_primeiro(bruto.get("ano")))
    reg["tipo_publicacao_orig"] = normalizar.texto(_primeiro(bruto.get("tipo_publicacao_orig") or bruto.get("tipo_publicacao")))
    if "tipo_hint" in bruto:
        reg["tipo_publicacao"] = tipo_de(bruto["tipo_hint"])
    else:
        reg["tipo_publicacao"] = tipo_de(reg["tipo_publicacao_orig"])
    reg["idioma"] = idioma_de(bruto.get("idioma"))

    for campo in ("veiculo", "volume", "numero", "paginas"):
        reg[campo] = normalizar.texto(_primeiro(bruto.get(campo)))

    resumo = normalizar.texto(_primeiro(bruto.get("resumo")))
    if re.fullmatch(r"\[?\s*no abstract available\s*\]?\.?", resumo, re.IGNORECASE):
        resumo = ""
    reg["resumo"] = resumo
    reg["resumo_truncado"] = "1" if resumo and _verdadeiro(bruto.get("resumo_truncado")) else "0"

    reg["palavras_chave"] = "; ".join(unicos(dividir(bruto.get("palavras_chave"), [";"])))
    reg["pais_afiliacao"] = "; ".join(unicos(dividir(bruto.get("pais_afiliacao"), [";"])))
    reg["instituicao"] = "; ".join(unicos(dividir(bruto.get("instituicao"), [";"])))
    reg["citado_por"] = inteiro_texto(_primeiro(bruto.get("citado_por")))
    return reg


def registro_vazio(reg):
    """Sem título, DOI nem id da fonte: linha de rodapé, separador ou lixo de planilha."""
    return not (reg.get("titulo") or reg.get("doi") or reg.get("id_fonte"))


# ---------------------------------------------------------------------------
# BibTeX
# ---------------------------------------------------------------------------
_ACENTOS_LATEX = {"'": "\u0301", "`": "\u0300", "^": "\u0302", '"': "\u0308", "~": "\u0303",
                  "=": "\u0304", ".": "\u0307", "c": "\u0327", "v": "\u030c", "H": "\u030b", "u": "\u0306"}


def limpar_latex(valor):
    """Remove marcação LaTeX comum em exportações BibTeX, preservando o texto."""
    s = str(valor or "")
    s = s.replace("{[}", "[").replace("{]}", "]")
    s = re.sub(r"\\i\b", "i", s)

    def _acento(m):
        base = m.group(2)
        return unicodedata.normalize("NFC", base + _ACENTOS_LATEX[m.group(1)])

    s = re.sub(r"\{?\\([\'`^\"~=.])\s*\{?\s*([A-Za-z])\s*\}?\}?", _acento, s)
    s = re.sub(r"\{?\\([cvHu])[\s{]+([A-Za-z])\s*\}?\}?", _acento, s)
    s = re.sub(r"\\([&%$#_{}])", r"\1", s)
    # Aspas LaTeX: ``x'' -> "x"; o WoS também troca o apóstrofo de abertura por crase (`x').
    s = s.replace("``", '"').replace("''", '"').replace("`", "'")
    s = re.sub(r"\\(?:textit|textbf|emph|textsc|textrm|mathrm|url)\s*", "", s)
    s = re.sub(r"\\[a-zA-Z]+\s*", "", s)
    s = s.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", s).strip()


def _ler_valor_bib(texto, pos):
    """Lê um valor BibTeX a partir de `pos` (após '='); devolve (valor_bruto, nova_pos)."""
    n = len(texto)
    partes = []
    while pos < n:
        while pos < n and texto[pos].isspace():
            pos += 1
        if pos >= n:
            break
        c = texto[pos]
        if c == "{":
            profundidade, inicio = 1, pos + 1
            pos += 1
            while pos < n and profundidade:
                if texto[pos] == "\\":
                    pos += 2
                    continue
                if texto[pos] == "{":
                    profundidade += 1
                elif texto[pos] == "}":
                    profundidade -= 1
                pos += 1
            partes.append(texto[inicio:pos - 1])
        elif c == '"':
            inicio, profundidade = pos + 1, 0
            pos += 1
            while pos < n and not (texto[pos] == '"' and profundidade == 0 and texto[pos - 1] != "\\"):
                if texto[pos] == "{":
                    profundidade += 1
                elif texto[pos] == "}":
                    profundidade -= 1
                pos += 1
            partes.append(texto[inicio:pos])
            pos += 1
        else:
            m = re.compile(r"[^,}\s#]+").match(texto, pos)
            partes.append(m.group(0) if m else "")
            pos = m.end() if m else pos + 1
        while pos < n and texto[pos].isspace():
            pos += 1
        if pos < n and texto[pos] == "#":
            pos += 1
            continue
        break
    return "".join(partes), pos


def entradas_bibtex(texto):
    """Lista de (tipo, chave, {campo_minúsculo: valor_bruto}, linha_inicial)."""
    entradas = []
    padrao = re.compile(r"@\s*(\w+)\s*([{(])")
    pos = 0
    while True:
        m = padrao.search(texto, pos)
        if not m:
            break
        tipo = m.group(1).lower()
        fechamento = "}" if m.group(2) == "{" else ")"
        linha = texto.count("\n", 0, m.start()) + 1
        pos = m.end()
        if tipo in {"comment", "preamble", "string"}:
            _, pos = _ler_valor_bib(texto, m.end() - 1)
            continue
        virgula = texto.find(",", pos)
        chave_entrada = texto[pos:virgula].strip() if virgula != -1 else ""
        pos = virgula + 1 if virgula != -1 else len(texto)
        campos = {}
        nome_re = re.compile(r"\s*([A-Za-z][\w\-:.+]*)\s*=\s*")
        while pos < len(texto):
            while pos < len(texto) and (texto[pos].isspace() or texto[pos] == ","):
                pos += 1
            if pos >= len(texto) or texto[pos] == fechamento:
                pos += 1
                break
            mn = nome_re.match(texto, pos)
            if not mn:  # lixo: pula até a próxima vírgula ou fim da entrada
                prox = min([p for p in (texto.find(",", pos + 1), texto.find(fechamento, pos + 1)) if p != -1] or [len(texto)])
                pos = prox
                continue
            valor, pos = _ler_valor_bib(texto, mn.end())
            campos[mn.group(1).lower()] = valor
        entradas.append((tipo, chave_entrada, campos, linha))
    return entradas


def autores_bibtex(valor):
    """Divide 'A and B and {Org and Co}' em ' and ' fora de chaves (linear no tamanho do campo)."""
    s = str(valor or "")
    itens, inicio, profundidade, ultimo = [], 0, 0, 0
    for m in re.finditer(r"\s+and\s+", s, flags=re.IGNORECASE):
        trecho = s[ultimo:m.start()]
        profundidade += trecho.count("{") - trecho.count("}")
        ultimo = m.start()
        if profundidade == 0:
            itens.append(s[inicio:m.start()])
            inicio = m.end()
    itens.append(s[inicio:])
    return [x for x in (limpar_latex(i) for i in itens) if x]


def enderecos_bibtex(valor):
    """Campo de afiliação em várias linhas -> endereços (um endereço termina com ponto final)."""
    enderecos, atual = [], []
    for linha in str(valor or "").split("\n"):
        linha = limpar_latex(linha)
        if not linha:
            continue
        atual.append(linha)
        if linha.endswith("."):
            enderecos.append(" ".join(atual))
            atual = []
    if atual:
        enderecos.append(" ".join(atual))
    return enderecos


def bruto_de_bibtex(tipo, campos):
    """Campos BibTeX (WoS ou genérico) -> dict intermediário."""
    def c(*nomes):
        for nome in nomes:
            if nome in campos and limpar_latex(campos[nome]):
                return limpar_latex(campos[nome])
        return ""

    # "Address" no BibTeX do WoS é o endereço da editora, não da afiliação: não entra em país.
    enderecos = enderecos_bibtex(campos.get("affiliation", ""))
    ano = c("year") or c("date")
    paginas = c("pages").replace("--", "-") or c("article-number", "eid")
    return {
        "id_fonte": c("unique-id"),
        "doi": c("doi"),
        "doi_extra": [c("note"), c("url")],
        "titulo": c("title"),
        "autores": autores_bibtex(campos["author"]) if "author" in campos else autores_bibtex(campos.get("editor", "")),
        "ano": ano,
        "tipo_publicacao_orig": c("type") or tipo,
        "idioma": c("language", "langid"),
        "veiculo": c("journal", "journaltitle", "booktitle", "series", "publisher"),
        "volume": c("volume"),
        "numero": c("number", "issue"),
        "paginas": paginas,
        "resumo": c("abstract"),
        "palavras_chave": c("keywords", "author-keywords"),
        "pais_afiliacao": [pais_de_endereco(e) for e in enderecos],
        "instituicao": c("affiliations", "school", "institution"),
        "url": c("url"),
        "citado_por": c("times-cited"),
    }


def ler_bibtex(caminho, fonte="generico"):
    """BibTeX qualquer (Zotero, Mendeley, Scholar). Registros do WoS vão por wos.ler."""
    avisos = []
    texto = ler_texto(caminho, avisos)
    registros = []
    for tipo, chave_entrada, campos, _linha in entradas_bibtex(texto):
        bruto = bruto_de_bibtex(tipo, campos)
        if not bruto["id_fonte"] and chave_entrada.upper().startswith("WOS:"):
            bruto["id_fonte"] = chave_entrada
        bruto["fonte"] = fonte
        registros.append(bruto)
    return Leitura(registros, avisos)


# ---------------------------------------------------------------------------
# Leitor genérico de tabelas
# ---------------------------------------------------------------------------
APELIDOS = {
    # Sem "id": numeração de linha de planilha colidiria entre arquivos e o dedup (R2) fundiria registros.
    "id_fonte": ["id_fonte", "accession number", "ut", "eid"],
    "doi": ["doi", "doi_limpo", "di"],
    "titulo": ["titulo", "título", "title", "article title", "document title", "display_name", "ti", "nm_producao"],
    "titulo_alt": ["titulo_alt", "titulo alternativo", "alternative title"],
    "autores": ["autores", "autor", "autor(a)", "autoria", "authors", "author", "author(s)", "author full names", "au"],
    "ano": ["ano", "year", "publication year", "publication_year", "ano de publicacao", "ano de defesa", "py", "date"],
    "tipo_publicacao_orig": ["tipo_publicacao", "tipo", "tipo de documento", "document type", "type", "item type", "dt"],
    "idioma": ["idioma", "language", "lingua", "língua", "la"],
    "veiculo": ["veiculo", "nome_publicacao", "journal", "source title", "publication title", "periodico", "periódico", "source", "so"],
    "volume": ["volume", "vl"],
    "numero": ["numero", "número", "issue", "number", "is"],
    "paginas": ["paginas", "páginas", "pages", "page range"],
    "resumo": ["resumo", "abstract", "abstract note", "ab"],
    "palavras_chave": ["palavras_chave", "palavras-chave", "palavras chave", "keywords", "author keywords", "de"],
    "pais_afiliacao": ["pais_afiliacao", "pais", "país", "country", "countries"],
    "instituicao": ["instituicao", "instituição", "institution", "affiliations", "ies"],
    "url": ["url", "link", "article url", "fulltext url"],
    "citado_por": ["citado_por", "cited by", "citations", "cites", "times cited"],
}


def validar_mapa(mapa):
    """Normaliza o JSON do mapa em {'colunas': {...}, 'fonte': ..., 'planilha': ..., 'separador_autores': ...}."""
    if not isinstance(mapa, dict):
        raise ErroImportacao("mapa deve ser um objeto JSON")
    if "colunas" in mapa:
        colunas = mapa["colunas"]
        extras = {k: v for k, v in mapa.items() if k != "colunas"}
    else:
        opcoes = {"fonte", "planilha", "separador_autores"}
        colunas = {k: v for k, v in mapa.items() if k not in opcoes}
        extras = {k: v for k, v in mapa.items() if k in opcoes}
    if not isinstance(colunas, dict) or not colunas:
        raise ErroImportacao("mapa sem 'colunas' (ex.: {\"colunas\": {\"titulo\": \"Title\"}})")
    desconhecidas = sorted(set(colunas) - set(CAMPOS_CONTEUDO) - {"primeiro_autor_sobrenome"})
    if desconhecidas:
        raise ErroImportacao(f"mapa com campos que não existem em registros.csv: {', '.join(desconhecidas)}. "
                             f"Campos válidos: {', '.join(CAMPOS_CONTEUDO)}")
    fonte = extras.get("fonte") or "generico"
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,30}", str(fonte)):
        raise ErroImportacao(f"fonte inválida no mapa: {fonte!r} (use minúsculas, ex.: 'generico')")
    return {"colunas": colunas, "fonte": fonte, "planilha": extras.get("planilha", 0),
            "separador_autores": extras.get("separador_autores")}


def mapa_por_apelidos(cabecalho):
    """Mapa automático por nomes de coluna comuns; exige ao menos a coluna de título."""
    colunas = {}
    for campo, apelidos in APELIDOS.items():
        col = achar_coluna(cabecalho, *apelidos)
        if col is not None and col not in colunas.values():
            colunas[campo] = col
    if "titulo" not in colunas:
        raise ErroImportacao("formato não reconhecido e sem coluna de título identificável. "
                             f"Colunas encontradas: {', '.join(cabecalho[:40])}. Passe --mapa mapa.json.")
    return {"colunas": colunas, "fonte": "generico", "planilha": 0, "separador_autores": None}


def ler(caminho, mapa=None, fonte=None):
    """Planilha/CSV arbitrário -> Leitura, usando o mapa (validado) ou apelidos automáticos."""
    avisos = []
    planilha = (mapa or {}).get("planilha", 0) if isinstance(mapa, dict) else 0
    cabecalho, linhas = ler_tabela(caminho, planilha=planilha, avisos=avisos)
    if mapa is None:
        mapa = mapa_por_apelidos(cabecalho)
        avisos.append("formato sem assinatura conhecida: colunas mapeadas por apelido "
                      + ", ".join(f"{k}<-{v}" for k, v in mapa["colunas"].items())
                      + ". Confira; se estiver errado, passe --mapa.")
    else:
        mapa = validar_mapa(mapa)
        faltando = []
        for campo, origem in mapa["colunas"].items():
            for col in ([origem] if isinstance(origem, str) else list(origem)):
                if col not in cabecalho and achar_coluna(cabecalho, col) is None:
                    faltando.append(f"{campo}<-{col}")
        if faltando:
            raise ErroImportacao(f"colunas do mapa ausentes no arquivo: {', '.join(faltando)}. "
                                 f"Colunas disponíveis: {', '.join(cabecalho[:60])}")
    fonte = fonte or mapa["fonte"]
    sep_autores = mapa.get("separador_autores")

    resolvidas = {}
    for campo, origem in mapa["colunas"].items():
        nomes = [origem] if isinstance(origem, str) else list(origem)
        resolvidas[campo] = [n if n in cabecalho else achar_coluna(cabecalho, n) for n in nomes]

    registros = []
    for linha in linhas:
        bruto = {"fonte": fonte}
        for campo, colunas_origem in resolvidas.items():
            valores = []
            for col in colunas_origem:
                if col is not None and not normalizar.vazio(linha.get(col)):
                    valores.append(linha[col])
            if not valores:
                continue
            if campo in CAMPOS_CONCATENADOS:
                bruto[campo] = valores
            else:
                bruto[campo] = valores[0]
        if sep_autores and bruto.get("autores"):
            bruto["autores"] = dividir(bruto["autores"], [sep_autores])
        registros.append(bruto)
    return Leitura(registros, avisos)
