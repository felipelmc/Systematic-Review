"""SciELO: CSV do portal search.scielo.org (e, por delegação, SciELO CI exportada pelo WoS).

USO
    rs.py importar --arquivo export_20250320.csv --busca-id B06
    rs.py importar --arquivo wos_scielo.txt --busca-id B06 --fonte scielo   # TSV/plaintext do WoS

Decisões:
- O CSV do portal tem cabeçalho com espaço sobrando ("Fulltext URL "), ID com
  espaço e aspas antes do valor (` "S0103-...-spa"`) e CRLF; a leitura tolerante
  de `detectar.ler_csv` cuida disso.
- Autores vêm como pares separados por vírgula ("Gomes, Crizian Saar, Silva,
  Alanna Gomes da"): com número par de partes, agrupa de dois em dois; senão,
  delega a `normalizar.autores_canonicos`.
- `id_fonte` = "SCIELO:" + PID sem o código da coleção (-spa, -scl): o mesmo
  artigo aparece em várias coleções e com o mesmo PID na SciELO Citation Index
  do WoS (UT "SCIELO:S0101-..."), então o R2 do dedup funde as cópias.
- "Source" ("Saúde em Debate; 48(141); 11-22") é decomposto em volume, número e
  páginas. O portal não exporta resumo, DOI nem tipo: ficam vazios (sem dado).
"""

import re

from .. import normalizar
from .detectar import Colunas, Leitura, ler_tabela
from . import wos

_PID = re.compile(r"^(S\d{4}-[\dXx]{4}\d{13})(?:-([A-Za-z]{2,4}))?$")
_FONTE = re.compile(r";\s*([^;()]*)\(([^)]*)\)\s*;\s*([^;]*)$")


def pid_de(valor):
    """PID SciELO normalizado ('SCIELO:S0103-11042024000200208') ou ''."""
    s = str(valor or "").strip().strip('"').strip()
    m = _PID.match(s)
    if m:
        return f"SCIELO:{m.group(1).upper()}"
    return f"SCIELO:{s}" if s else ""


def autores_em_pares(valor):
    """'Sob, Nome, Sob2, Nome2' -> ['Sob, Nome', 'Sob2, Nome2'] quando as partes são pares.

    Número ímpar de partes (autoria institucional, nome sem vírgula) volta como
    string para a separação geral de generico.autores_canonicos.
    """
    partes = [p.strip() for p in str(valor or "").split(",") if p.strip()]
    if partes and len(partes) % 2 == 0:
        return [f"{partes[i]}, {partes[i + 1]}" for i in range(0, len(partes), 2)]
    return normalizar.texto(valor)


def decompor_fonte(valor):
    """'Revista; 48(141); 11-22' -> (volume, numero, paginas)."""
    m = _FONTE.search(str(valor or ""))
    if not m:
        return "", "", ""
    paginas = m.group(3).strip()
    return m.group(1).strip(), m.group(2).strip(), "" if paginas in {"-", "--"} else paginas


def bruto_de_linha(linha, colunas):
    def c(*nomes):
        return colunas.valor(linha, *nomes)

    volume, numero, paginas = decompor_fonte(c("Source"))
    return {
        "fonte": "scielo",
        "id_fonte": pid_de(c("ID")),
        "doi": c("DOI"),
        "titulo": c("Title"),
        "autores": autores_em_pares(c("Author(s)", "Authors")),
        "ano": c("Publication year", "Year"),
        "idioma": c("Language(s)", "Language"),
        "veiculo": c("Journal") or (c("Source").split(";")[0] if c("Source") else ""),
        "volume": volume,
        "numero": numero,
        "paginas": paginas,
        "url": c("Fulltext URL"),
    }


def ler(caminho, formato="scielo_csv", fonte_forcada=None):
    if formato in {"wos_txt", "wos_tsv", "wos_tabela", "wos_bib", "wos_xls"}:
        return wos.ler(caminho, formato, fonte_forcada=fonte_forcada or "scielo")
    avisos = []
    cabecalho, linhas = ler_tabela(caminho, avisos=avisos)
    colunas = Colunas(cabecalho)
    registros = [bruto_de_linha(l, colunas) for l in linhas]
    if fonte_forcada:
        for r in registros:
            r["fonte"] = fonte_forcada
    return Leitura(registros, avisos)
