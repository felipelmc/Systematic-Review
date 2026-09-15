"""Web of Science: plaintext, tab-delimited (inclusive SciELO Citation Index), BibTeX e Excel.

USO
    rs.py importar --arquivo savedrecs.txt --busca-id B01            # detecção automática
    rs.py importar --arquivo wos_scielo.txt --busca-id B02 --fonte scielo

    from rslib.importar import wos
    leitura = wos.ler("savedrecs.txt", "wos_txt")

Decisões:
- Plaintext: cada linha começa com uma tag de 2 caracteres; linhas de
  continuação começam com 3 espaços. Em AU/AF/C1 cada continuação é um item
  novo (um autor, um endereço); nas demais tags é quebra de linha do texto e
  vira espaço. Registros terminam em `ER`; o arquivo, em `EF`.
- Autores: AF (nomes completos) tem precedência sobre AU (iniciais), porque o
  dedup e a chave de citação ficam melhores com nomes completos; sem autor
  pessoal usa CA/GP (autoria institucional, sem inverter nome).
- Palavras-chave: só DE (do autor), mais X5/Y5/Z5 (DE em outros idiomas no
  SciELO). ID/Keywords Plus é gerado por algoritmo do WoS e poluiria filtros por
  dicionário.
- Fonte por registro: UT `SCIELO:` -> `scielo`; senão `wos`. Assim uma busca na
  SciELO Citation Index pela plataforma WoS entra como SciELO no PRISMA.
- Ano: PY; na falta (early access), EY ou o ano de EA.
- País: último trecho de cada endereço de C1 (colchetes com nomes removidos).
"""

import re

from .detectar import Colunas, Leitura, ler_csv, ler_planilha, ler_texto, tipo_planilha
from .generico import bruto_de_bibtex, dividir, entradas_bibtex, pais_de_endereco, paginas_de

TAGS_ITEM_POR_LINHA = {"AU", "AF", "BA", "BF", "CA", "GP", "BE", "C1", "CR", "RP", "EM", "RI", "OI"}


def normalizar_ut(ut):
    """UT com prefixo em maiúsculas ('scielo:s0101-...' -> 'SCIELO:S0101-...'), comparável entre formatos."""
    s = str(ut or "").strip()
    if ":" in s:
        prefixo, resto = s.split(":", 1)
        return f"{prefixo.strip().upper()}:{resto.strip().upper()}"
    return s


def _fonte_por_ut(ut, forcada=None):
    if forcada:
        return forcada
    return "scielo" if str(ut).upper().startswith("SCIELO:") else "wos"


# ---------------------------------------------------------------------------
# Plaintext
# ---------------------------------------------------------------------------
def registros_plaintext(texto):
    """Texto plaintext -> lista de dicts tag -> string (itens por linha unidos com '; ')."""
    registros, atual, tag = [], None, None
    for linha in texto.split("\n"):
        if not linha.strip():
            continue
        if linha.startswith("   ") or linha.startswith("\t"):
            if atual is not None and tag:
                atual.setdefault(tag, []).append(linha.strip())
            continue
        tag_linha = linha[:2]
        valor = linha[3:].strip() if len(linha) > 2 else ""
        if tag_linha in {"FN", "VR"}:
            tag = None
            continue
        if tag_linha == "EF":
            break
        if tag_linha == "ER":
            atual, tag = None, None
            continue
        if not re.fullmatch(r"[A-Z][A-Z0-9]", tag_linha):
            continue
        if tag_linha == "PT" or atual is None:
            atual = {}
            registros.append(atual)
        tag = tag_linha
        atual.setdefault(tag, []).append(valor)
    saida = []
    for reg in registros:
        campos = {}
        for t, linhas in reg.items():
            juntar = "; " if t in TAGS_ITEM_POR_LINHA else " "
            campos[t] = juntar.join(l for l in linhas if l)
        saida.append(campos)
    return saida


# ---------------------------------------------------------------------------
# Tags (plaintext e TSV) -> bruto
# ---------------------------------------------------------------------------
def bruto_de_tags(campos, fonte_forcada=None):
    """Dict tag -> string (plaintext já agregado ou linha do TSV) -> dict intermediário."""
    def t(*tags):
        for tag in tags:
            v = str(campos.get(tag, "") or "").strip()
            if v:
                return v
        return ""

    ut = normalizar_ut(t("UT"))
    pessoais = dividir(t("AF", "AU", "BF", "BA"), [";"])
    corporativos = not pessoais
    autores = pessoais or dividir(t("CA", "GP"), [";"])
    enderecos = [e for e in re.split(r";\s*(?![^\[]*\])", t("C1")) if e.strip()]
    ano = t("PY") or t("EY") or t("EA") or t("PD")
    tipo = t("DT") or t("PT")
    return {
        "fonte": _fonte_por_ut(ut, fonte_forcada),
        "id_fonte": ut,
        "doi": t("DI"),
        "doi_extra": [t("D2")],
        "titulo": t("TI"),
        "titulo_alt": [t("X1"), t("Y1"), t("Z1")],
        "autores": autores,
        "autores_corporativos": corporativos,
        "ano": ano,
        "tipo_publicacao_orig": tipo,
        "idioma": t("LA"),
        "veiculo": t("SO") or t("SE") or t("BS"),
        "volume": t("VL"),
        "numero": t("IS"),
        "paginas": paginas_de(t("BP"), t("EP"), t("AR")),
        "resumo": t("AB") or t("X4") or t("Y4") or t("Z4"),
        "palavras_chave": [t("DE"), t("X5"), t("Y5"), t("Z5")],
        "pais_afiliacao": [pais_de_endereco(e) for e in enderecos],
        "instituicao": t("C3"),
        "url": "",
        "citado_por": t("TC"),
        "_data_exportacao": t("DA"),
    }


# ---------------------------------------------------------------------------
# Excel (colunas por extenso)
# ---------------------------------------------------------------------------
def bruto_de_planilha(linha, colunas, fonte_forcada=None):
    def c(*nomes):
        return colunas.valor(linha, *nomes)

    ut = normalizar_ut(c("UT (Unique WOS ID)", "UT (Unique ID)", "UT"))
    pessoais = dividir(c("Author Full Names", "Authors", "Book Author Full Names", "Book Authors"), [";"])
    corporativos = not pessoais
    autores = pessoais or dividir(c("Group Authors", "Book Group Authors"), [";"])
    enderecos = [e for e in re.split(r";\s*(?![^\[]*\])", c("Addresses")) if e.strip()]
    return {
        "fonte": _fonte_por_ut(ut, fonte_forcada),
        "id_fonte": ut,
        "doi": c("DOI"),
        "doi_extra": [c("DOI Link")],
        "titulo": c("Article Title", "Title"),
        "titulo_alt": [c("Article Title - SciELO"), c("Article Title - SciELO.1"),
                       c("Article Title - Chinese"), c("Article Title - Russian")],
        "autores": autores,
        "autores_corporativos": corporativos,
        "ano": c("Publication Year") or c("Early Access Date") or c("Publication Date"),
        "tipo_publicacao_orig": c("Document Type") or c("Publication Type"),
        "idioma": c("Language"),
        "veiculo": c("Source Title", "Book Series Title"),
        "volume": c("Volume"),
        "numero": c("Issue"),
        "paginas": paginas_de(c("Start Page"), c("End Page"), c("Article Number")),
        "resumo": c("Abstract") or c("Abstract - Foreign"),
        "palavras_chave": c("Author Keywords"),
        "pais_afiliacao": [pais_de_endereco(e) for e in enderecos],
        "instituicao": c("Affiliations", "Institution"),
        "url": "",
        "citado_por": c("Times Cited, WoS Core", "Times Cited, All Databases"),
        "_data_exportacao": c("Date of Export"),
    }


# ---------------------------------------------------------------------------
# Entrada única do módulo
# ---------------------------------------------------------------------------
def ler(caminho, formato, fonte_forcada=None):
    """Lê qualquer formato do WoS e devolve Leitura com registros intermediários."""
    avisos = []
    if formato == "wos_txt":
        registros = [bruto_de_tags(c, fonte_forcada) for c in registros_plaintext(ler_texto(caminho, avisos))]
    elif formato == "wos_tsv":
        _, linhas = ler_csv(caminho, separador="\t", avisos=avisos, sem_aspas=True)
        registros = [bruto_de_tags(l, fonte_forcada) for l in linhas]
    elif formato == "wos_tabela":
        _, linhas = ler_csv(caminho, avisos=avisos) if not tipo_planilha(caminho) else ler_planilha(caminho)
        registros = [bruto_de_tags(l, fonte_forcada) for l in linhas]
    elif formato == "wos_bib":
        registros = []
        for tipo, chave_entrada, campos, _linha in entradas_bibtex(ler_texto(caminho, avisos)):
            bruto = bruto_de_bibtex(tipo, campos)
            if not bruto["id_fonte"] and chave_entrada.upper().startswith(("WOS:", "SCIELO:")):
                bruto["id_fonte"] = chave_entrada
            bruto["id_fonte"] = normalizar_ut(bruto["id_fonte"])
            bruto["fonte"] = _fonte_por_ut(bruto["id_fonte"], fonte_forcada)
            bruto["_data_exportacao"] = campos.get("da", "")
            registros.append(bruto)
    elif formato == "wos_xls":
        cabecalho, linhas = ler_planilha(caminho) if tipo_planilha(caminho) else ler_csv(caminho, avisos=avisos)
        colunas = Colunas(cabecalho)
        registros = [bruto_de_planilha(l, colunas, fonte_forcada) for l in linhas]
    else:
        raise ValueError(f"formato não suportado pelo leitor WoS: {formato}")
    datas = sorted({r.pop("_data_exportacao", "") for r in registros} - {""})
    return Leitura(registros, avisos, data_busca=datas[-1] if datas else None)
