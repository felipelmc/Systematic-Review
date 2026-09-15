"""Publish or Perish (inclusive exportações do Google Scholar feitas pelo PoP).

USO
    rs.py importar --arquivo PoPCites.csv --busca-id CZ1 --metodo cinzenta

Decisões:
- O resumo do Scholar é um trecho com reticências ("… à transação no direito
  tributário …"): `resumo_truncado=1`. A triagem deve tratar o trecho como
  insuficiente (tende a `incerto`), e o dedup prefere o resumo completo de
  outra base.
- Autores: "PK Smith, J Mahdavi, M Carvalho, ..." — sempre iniciais antes do
  sobrenome, separados por vírgula; o item "..." (ou "…" colado ao último nome)
  indica lista cortada. `n_autores` usa AuthorCount quando maior que a lista.
- `Type` do PoP descreve o link (PDF, HTML, DOC), não o tipo do documento:
  vira tipo vazio (sem dado). BOOK e CITATION são mantidos (livro, outro).
- `id_fonte` = id do cluster do Scholar extraído de CitesURL (GS:<n>), que se
  repete entre buscas em idiomas diferentes e ajuda o R2 do dedup.
- QueryDate vira a data de execução da busca quando o estado não tiver uma.
"""

import re

from .detectar import Colunas, Leitura, ler_tabela
from .generico import paginas_de, tem_reticencias

_TIPOS_LINK = {"pdf", "html", "doc", "docx", "ps", "xml"}
_RETICENCIAS = re.compile(r"(\.\.\.|…)\s*$")


def autores_pop(valor):
    """Lista de autores e se ela foi cortada pelo Scholar."""
    itens, cortada = [], False
    for parte in str(valor or "").split(","):
        parte = parte.strip()
        if not parte:
            continue
        if _RETICENCIAS.search(parte):
            cortada = True
            parte = _RETICENCIAS.sub("", parte).strip()
            if not parte:
                continue
        itens.append(parte)
    return itens, cortada


def bruto_de_linha(linha, colunas):
    def c(*nomes):
        return colunas.valor(linha, *nomes)

    autores, _cortada = autores_pop(c("Authors"))
    tipo = c("Type")
    m = re.search(r"cites=(\d+)", c("CitesURL"))
    resumo = c("Abstract")
    bruto = {
        "fonte": "pop",
        "id_fonte": f"GS:{m.group(1)}" if m else "",
        "doi": c("DOI"),
        "doi_extra": [c("ArticleURL")],
        "titulo": c("Title"),
        "autores": autores,
        "n_autores": c("AuthorCount"),
        "ano": c("Year"),
        "tipo_publicacao_orig": tipo,
        "veiculo": c("Source"),
        "volume": c("Volume"),
        "numero": c("Issue"),
        "paginas": paginas_de(c("StartPage"), c("EndPage")),
        "resumo": resumo,
        "resumo_truncado": tem_reticencias(resumo),
        "url": c("ArticleURL", "FullTextURL"),
        "citado_por": c("Cites"),
        "_data": c("QueryDate"),
    }
    if tipo.strip().lower() in _TIPOS_LINK:
        bruto["tipo_hint"] = ""
    return bruto


def ler(caminho, formato="pop_csv", fonte_forcada=None):
    avisos = []
    cabecalho, linhas = ler_tabela(caminho, avisos=avisos)
    colunas = Colunas(cabecalho)
    registros = [bruto_de_linha(l, colunas) for l in linhas]
    datas = sorted({r.pop("_data", "")[:10] for r in registros} - {""})
    if fonte_forcada:
        for r in registros:
            r["fonte"] = fonte_forcada
    truncados = sum(1 for r in registros if r.get("resumo_truncado"))
    if truncados:
        avisos.append(f"{truncados} resumo(s) do Scholar são trechos com reticências (resumo_truncado=1)")
    return Leitura(registros, avisos, data_busca=datas[-1] if datas else None)
