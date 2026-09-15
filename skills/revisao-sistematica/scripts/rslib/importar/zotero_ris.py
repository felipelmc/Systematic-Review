"""Zotero (CSV) e RIS (Zotero, Mendeley, EndNote, Scopus, WoS).

USO
    rs.py importar --arquivo export.csv --busca-id MN1 --metodo manual
    rs.py importar --arquivo biblioteca.ris --busca-id MN2

Decisões:
- Zotero CSV: a coluna `Key` é o id interno da biblioteca local do usuário;
  não identifica a obra e é ignorada (não vai para `id_fonte`, senão o R2 do
  dedup fundiria itens de bibliotecas diferentes com a mesma chave).
- Tipo: `Item Type` (journalArticle, bookSection, thesis...) traduzido pela
  tabela de pré-tipos; em teses, o campo `Type` ("Dissertação (Mestrado)")
  distingue tese de dissertação.
- DOI: coluna própria ou, na falta (relatórios, preprints antigos), "DOI: 10.x"
  dentro de `Extra` ou uma URL doi.org.
- Palavras-chave: `Manual Tags` + `Automatic Tags`.
- RIS: parser próprio (sem rispy): tag de 2 caracteres, "  - ", valor; linhas sem
  tag continuam o campo anterior; `ER` fecha o registro. `DB  - Scopus` ou `AN`
  com EID/UT definem a fonte (scopus/wos) e o `id_fonte`; demais ficam `ris`.
"""

import re

from .detectar import Colunas, Leitura, ler_tabela, ler_texto
from .generico import dividir, paginas_de

_TAG_RIS = re.compile(r"^([A-Z][A-Z0-9])\s{1,2}-(?:\s(.*))?$")


# ---------------------------------------------------------------------------
# Zotero CSV
# ---------------------------------------------------------------------------
def _tipo_tese(item_type, tipo_livre):
    """Para teses, o texto livre de 'Type' diz se é mestrado ou doutorado."""
    if item_type.strip().lower() == "thesis" and tipo_livre:
        return tipo_livre
    return item_type


def bruto_de_linha_zotero(linha, colunas):
    def c(*nomes):
        return colunas.valor(linha, *nomes)

    item_type = c("Item Type")
    tipo_livre = c("Type")
    return {
        "fonte": "zotero",
        "id_fonte": "",
        "doi": c("DOI"),
        "doi_extra": [c("Extra"), c("Url")],
        "titulo": c("Title"),
        "autores": dividir(c("Author"), [";"]),
        "ano": c("Publication Year") or c("Date"),
        "tipo_publicacao_orig": item_type if not tipo_livre else f"{item_type}; {tipo_livre}",
        "tipo_hint": _tipo_tese(item_type, tipo_livre),
        "idioma": c("Language"),
        "veiculo": c("Publication Title") or (c("Publisher") if item_type.lower() in {"book", "report"} else ""),
        "volume": c("Volume"),
        "numero": c("Issue", "Number"),
        "paginas": c("Pages"),
        "resumo": c("Abstract Note"),
        "palavras_chave": [c("Manual Tags"), c("Automatic Tags")],
        "instituicao": c("University") or (c("Publisher") if item_type.lower() == "thesis" else ""),
        "url": c("Url"),
    }


def ler_zotero(caminho, formato="zotero_csv", fonte_forcada=None):
    if formato == "ris":
        return ler_ris(caminho, fonte_forcada=fonte_forcada or "zotero")
    if formato == "bibtex":
        from .generico import ler_bibtex
        return ler_bibtex(caminho, fonte=fonte_forcada or "zotero")
    avisos = []
    cabecalho, linhas = ler_tabela(caminho, avisos=avisos)
    colunas = Colunas(cabecalho)
    registros = [bruto_de_linha_zotero(l, colunas) for l in linhas]
    if fonte_forcada:
        for r in registros:
            r["fonte"] = fonte_forcada
    return Leitura(registros, avisos)


# ---------------------------------------------------------------------------
# RIS
# ---------------------------------------------------------------------------
def registros_ris(texto):
    """Texto RIS -> lista de dicts tag -> lista de valores."""
    registros, atual, ultima = [], None, None
    for linha in texto.split("\n"):
        if not linha.strip():
            continue
        m = _TAG_RIS.match(linha.rstrip())
        if not m:
            if atual is not None and ultima:
                atual[ultima][-1] = (atual[ultima][-1] + " " + linha.strip()).strip()
            continue
        tag, valor = m.group(1), (m.group(2) or "").strip()
        if tag == "TY":
            atual = {"TY": [valor]}
            registros.append(atual)
            ultima = "TY"
            continue
        if tag == "ER":
            atual, ultima = None, None
            continue
        if atual is None:
            atual = {}
            registros.append(atual)
        atual.setdefault(tag, []).append(valor)
        ultima = tag
    return registros


def _fonte_ris(campos):
    db = " ".join(campos.get("DB", [])).lower()
    an = " ".join(campos.get("AN", [])).upper()
    if "scopus" in db or an.startswith("2-S2.0-"):
        return "scopus"
    if "web of science" in db or an.startswith("WOS:"):
        return "wos"
    if "scielo" in db or an.startswith("SCIELO:"):
        return "scielo"
    return "ris"


def bruto_de_ris(campos, fonte_forcada=None):
    def v(*tags):
        for tag in tags:
            for valor in campos.get(tag, []):
                if valor.strip():
                    return valor.strip()
        return ""

    def todos(*tags):
        return [x for tag in tags for x in campos.get(tag, []) if x.strip()]

    an = v("AN")
    id_fonte = an if re.match(r"^(WOS:|2-s2\.0-|SCIELO:)", an, re.IGNORECASE) else ""
    ty = v("TY")
    m3 = v("M3")
    return {
        "fonte": fonte_forcada or _fonte_ris(campos),
        "id_fonte": id_fonte,
        "doi": v("DO"),
        "doi_extra": todos("UR", "N1", "M3"),
        "titulo": v("TI", "T1", "CT", "BT"),
        "titulo_alt": todos("TT"),  # TT = título traduzido; ST (título curto) não é título alternativo
        "autores": todos("AU", "A1") or todos("A2"),
        "ano": v("PY", "Y1", "DA"),
        "tipo_publicacao_orig": ty if not m3 else f"{ty}; {m3}",
        "tipo_hint": m3 if ty.upper() == "THES" and m3 else ty,
        "idioma": v("LA"),
        "veiculo": v("T2", "JO", "JF", "JA", "J2", "SE"),
        "volume": v("VL"),
        "numero": v("IS", "CP"),
        "paginas": paginas_de(v("SP"), v("EP")),
        "resumo": v("AB", "N2"),
        "palavras_chave": todos("KW"),
        "instituicao": todos("AD") if ty.upper() != "THES" else (todos("PB") or todos("AD")),
        "url": v("UR", "L2"),
        "citado_por": "",
    }


def ler_ris(caminho, formato="ris", fonte_forcada=None):
    avisos = []
    registros = [bruto_de_ris(c, fonte_forcada) for c in registros_ris(ler_texto(caminho, avisos))]
    return Leitura(registros, avisos)
