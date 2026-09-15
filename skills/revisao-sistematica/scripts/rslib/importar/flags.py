"""Flags por registro vindas da fonte (ex.: `is_retracted` do OpenAlex): dados/registros_flags.csv.

USO (programático)
    from rslib.importar import flags
    flags.acrescentar(raiz, [{"id_registro": "B04-00003", "flag": "retratado", "origem": "openalex:is_retracted"}])
    por_registro = flags.ler(raiz)          # {"B04-00003": {"retratado"}}

POR QUE UMA TABELA À PARTE
    `dados/registros.csv` tem cabeçalho fixo (esquema.COLUNAS_REGISTROS) e é imutável
    depois de importado. Uma informação da fonte que não cabe nas colunas (a marca de
    retratação do OpenAlex) era só contada num aviso e descartada, e o `dedup` só
    marcava `retratado` por texto no título ou no tipo. Esta tabela guarda a flag por
    `id_registro` (join, nunca por título), é append-only e sem duplicatas
    (id_registro, flag), e o `dedup` a propaga para registros_unicos.flags.

    Colunas: id_registro, flag, origem (fonte:campo), registrado_em (ISO 8601).
    Reimportar o mesmo arquivo preenche flags que faltem (projetos importados antes
    desta tabela), sem repetir linhas.
"""

import csv
import io
from pathlib import Path

from .. import esquema, estado

ARQ_REGISTROS_FLAGS = esquema.ARQ_REGISTROS_FLAGS
COLUNAS_REGISTROS_FLAGS = esquema.COLUNAS_REGISTROS_FLAGS
FLAG_RETRATADO = esquema.FLAG_RETRATADO


def _linhas(raiz):
    caminho = Path(raiz) / ARQ_REGISTROS_FLAGS
    if not caminho.exists() or caminho.stat().st_size == 0:
        return []
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in l.items() if k} for l in csv.DictReader(f)]


def ler(raiz):
    """{id_registro: {flag, ...}} (vazio se a tabela não existir)."""
    saida = {}
    for l in _linhas(raiz):
        rid, flag = l.get("id_registro", "").strip(), l.get("flag", "").strip()
        if rid and flag:
            saida.setdefault(rid, set()).add(flag)
    return saida


def acrescentar(raiz, itens):
    """Acrescenta (id_registro, flag) ainda ausentes, com escrita atômica. Devolve as linhas novas."""
    existentes = _linhas(raiz)
    vistos = {(l.get("id_registro"), l.get("flag")) for l in existentes}
    agora = estado.agora()
    novos = []
    for item in itens:
        chave = (str(item.get("id_registro") or "").strip(), str(item.get("flag") or "").strip())
        if not all(chave) or "|" in chave[1] or chave in vistos:
            continue
        vistos.add(chave)
        novos.append({"id_registro": chave[0], "flag": chave[1], "origem": item.get("origem") or "",
                      "registrado_em": item.get("registrado_em") or agora})
    if not novos:
        return []
    caminho = Path(raiz) / ARQ_REGISTROS_FLAGS
    buffer = io.StringIO()
    w = csv.DictWriter(buffer, fieldnames=COLUNAS_REGISTROS_FLAGS, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(existentes + novos)
    estado.escrever_atomico(caminho, buffer.getvalue(), newline="")  # 0666 menos a umask
    return novos
