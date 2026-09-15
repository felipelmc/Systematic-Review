"""Regras compartilhadas sobre buscas: formato do busca_id e buscas substituídas (inativas).

USO (programático; não é subcomando)
    from rslib.importar import buscas
    buscas.validar_busca_id("B05")                    # ErroImportacao se inválido
    inativas = buscas.inativas_do_projeto(raiz)        # {"B01", ...}
    ativos = [u for u in unicos if not buscas.cluster_inativo(u)]

POR QUE UM MÓDULO SÓ PARA ISSO
    `importar`, `buscar openalex`, `bola-de-neve`, `dedup` e `filtrar` precisam da
    MESMA regra. Antes, `buscar openalex` aceitava ids que o importador recusava
    (`B05a` gravava o JSONL e só falhava na importação, depois da chamada à API).

    Busca substituída (`rs.py importar --substituir B01 --motivo ...`): a entrada
    de estado["buscas"] ganha `ativa: false` (esquema.CAMPO_BUSCA_ATIVA). As linhas
    de registros.csv NÃO são apagadas (auditoria e PRISMA-S item 12); `dedup` passa a
    ignorá-las e marca com a flag `busca_inativa` os clusters de registros_unicos.csv
    que só tinham registros dessas buscas. Ausência do campo = busca ativa.
"""

import re

from .. import esquema, estado
from .detectar import ErroImportacao

RE_BUSCA_ID = re.compile(r"^[A-Z]{1,4}\d{1,4}$")
FLAG_BUSCA_INATIVA = esquema.FLAG_BUSCA_INATIVA
METODO_POR_PREFIXO = {"SN": "citacao", "CZ": "cinzenta", "MN": "manual"}


def metodo_por_prefixo(busca_id):
    """Método de identificação padrão pelo prefixo do id: SN -> citacao, CZ -> cinzenta, MN -> manual, resto -> base."""
    m = re.match(r"^[A-Za-z]+", str(busca_id or ""))
    return METODO_POR_PREFIXO.get(m.group(0).upper() if m else "", "base")


def validar_busca_id(busca_id, opcao="--busca-id"):
    """Levanta ErroImportacao se o id não seguir letras maiúsculas + número (B01, SN1, CZ1, MN1)."""
    if not busca_id or not RE_BUSCA_ID.match(str(busca_id)):
        raise ErroImportacao(f"{opcao} inválido: {busca_id!r}. Use letras maiúsculas + número (B01, SN1, CZ1, MN1)")


def busca_ativa(busca):
    """Só `ativa: false` explícito desativa; buscas antigas sem o campo continuam ativas."""
    return not (isinstance(busca, dict) and busca.get(esquema.CAMPO_BUSCA_ATIVA) is False)


def inativas(est):
    return {b.get("id") for b in (est or {}).get("buscas", []) if isinstance(b, dict) and not busca_ativa(b)}


def inativas_do_projeto(raiz):
    """Ids das buscas substituídas; conjunto vazio se o estado não puder ser lido."""
    try:
        return inativas(estado.carregar_estado(raiz))
    except (estado.ErroProjeto, OSError, ValueError):
        return set()


def descrever_inativa(est, busca_id):
    """Mensagem de erro para quem tenta usar uma busca substituída."""
    b = next((x for x in (est or {}).get("buscas", []) if x.get("id") == busca_id), {}) or {}
    por = b.get("substituida_por")
    return (f"a busca {busca_id} foi substituída" + (f" por {por}" if por else "")
            + (f" em {b['substituida_em']}" if b.get("substituida_em") else "")
            + "; buscas inativas não recebem novas importações nem reexecuções (use um novo id)")


def flags_de(linha):
    return [f for f in str((linha or {}).get("flags") or "").split("|") if f]


def cluster_inativo(linha):
    """Linha de registros_unicos.csv fora do conjunto ativo (só tinha registros de buscas substituídas)."""
    return FLAG_BUSCA_INATIVA in flags_de(linha)


def busca_de_id_registro(id_registro):
    """'B03-00017' -> 'B03' (o número é sempre o último bloco após o hífen)."""
    s = str(id_registro or "").strip()
    return s.rsplit("-", 1)[0] if "-" in s else ""
