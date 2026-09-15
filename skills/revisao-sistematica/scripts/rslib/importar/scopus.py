"""Scopus: exportação CSV (ou a mesma tabela salva como planilha).

USO
    rs.py importar --arquivo scopus.csv --busca-id B02

Decisões:
- Autores: `Author full names` ("Shahidul Islam, Md. (58318980700); ...") tem
  precedência; o id numérico entre parênteses é removido. Exportações antigas só
  têm `Authors` com iniciais ("Weihs M.; Rahman A."), normalizado por
  `normalizar.autores_canonicos`. Isso corrige o erro das versões anteriores
  (sobrenome "M" para "Shahidul Islam M.").
- `id_fonte` = EID (2-s2.0-...), usado pela regra R2 do dedup.
- Resumo "[No abstract available]" vira vazio: é ausência de dado, e o filtro
  textual não pode tratá-lo como texto.
- Palavras-chave: só `Author Keywords`; `Index Keywords` são termos de
  indexação (EMTREE/controlados) e distorceriam filtros por dicionário.
- País: último trecho de cada afiliação separada por ';'.
"""

import re

from .detectar import Colunas, Leitura, ler_tabela
from .generico import dividir, pais_de_endereco, paginas_de

_ID_AUTOR = re.compile(r"\s*\(\d+\)\s*$")


def bruto_de_linha(linha, colunas):
    def c(*nomes):
        return colunas.valor(linha, *nomes)

    completos = [_ID_AUTOR.sub("", a) for a in dividir(c("Author full names"), [";"])]
    autores = completos or c("Authors")
    if autores and isinstance(autores, str) and re.fullmatch(r"\[\s*no author name available\s*\]", autores, re.I):
        autores = ""
    afiliacoes = dividir(c("Affiliations"), [";"])
    return {
        "fonte": "scopus",
        "id_fonte": c("EID"),
        "doi": c("DOI"),
        "doi_extra": [c("Link")],
        "titulo": c("Title", "Document Title"),
        "autores": autores,
        "ano": c("Year"),
        "tipo_publicacao_orig": c("Document Type"),
        "idioma": c("Language of Original Document"),
        "veiculo": c("Source title", "Source Title"),
        "volume": c("Volume"),
        "numero": c("Issue"),
        "paginas": paginas_de(c("Page start"), c("Page end"), c("Art. No.")),
        "resumo": c("Abstract"),
        "palavras_chave": c("Author Keywords"),
        "pais_afiliacao": [pais_de_endereco(a) for a in afiliacoes],
        "instituicao": afiliacoes,
        "url": c("Link"),
        "citado_por": c("Cited by"),
    }


def ler(caminho, formato="scopus_csv", fonte_forcada=None):
    avisos = []
    cabecalho, linhas = ler_tabela(caminho, avisos=avisos)
    colunas = Colunas(cabecalho)
    registros = []
    for linha in linhas:
        bruto = bruto_de_linha(linha, colunas)
        if fonte_forcada:
            bruto["fonte"] = fonte_forcada
        registros.append(bruto)
    return Leitura(registros, avisos)
