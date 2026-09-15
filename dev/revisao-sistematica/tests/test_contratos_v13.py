"""Contratos v1.3: constantes promovidas a esquema.py com os mesmos valores e aliases nos módulos."""

import importlib

import pytest

from rslib import esquema


def test_valores_das_constantes_v13():
    assert esquema.DECISOES_DEDUP == ["auto", "candidato", "confirmado", "rejeitado", "ligado"]
    assert esquema.DECISAO_LIGADO == "ligado" and esquema.MOTIVO_VERSAO_LIGADA == "preprint_publicado"
    assert esquema.COLUNAS_FILA_HUMANA_TC == ["id_rs", "chave", "proposta", "criterio_proposto", "evidencia", "pagina",
                                             "decisao_humana", "criterio_humano", "motivo"]
    assert esquema.ARQ_CODEBOOK_ELEGIBILIDADE == "00-protocolo/codebook_elegibilidade.csv"
    assert (esquema.PENDENCIA_PRESS, esquema.PENDENCIA_CONCORDANCIA, esquema.PENDENCIA_CONSENSO_ROB) == (
        "revisao_press", "concordancia_extracao", "consenso_rob")
    assert esquema.PADRAO_CONCORDANCIA == esquema.PADRAO_CONCORDANCIA_ROB == "04-qualidade/rob_{ferramenta}_concordancia.csv"
    assert set(esquema.TIPOS_SEM_CERTEZA) == {"escopo", "mapa_evidencias", "realista"}
    assert (esquema.CRITERIO_ATALHO_RAPIDA, esquema.FRACAO_MINIMA_DUPLA_RAPIDA) == ("atalho_rapida", 0.20)
    assert esquema.CAMPOS_ATALHO_RAPIDA == ["atalho_rapida", "fracao_dupla_humana", "n_dupla_humana", "n_populacao",
                                           "kappa_humanos", "segunda_leitura_excluidos", "n_excluidos_ia",
                                           "n_excluidos_relidos"]
    assert esquema.MIN_INCLUIDOS_LIMIAR_ALCANCAVEL == 36
    assert esquema.COLUNAS_EFEITOS_BINARIOS == ["p0", "p1", "efeito_pp", "se_pp"]
    assert not set(esquema.COLUNAS_EFEITOS_BINARIOS) & set(esquema.COLUNAS_EFEITOS_EXTRAS_NUMERICAS)
    assert (esquema.DIMENSAO_PAINEL, esquema.REGRA_VERSAO_CAIXA) == ("efeito_painel", "caixa-3")
    assert esquema.CAMPO_ULTIMO_SEQ_RELATORIO == "ultimo_seq"


def test_modulos_do_contrato_importam_de_esquema():
    from rslib import dedup, efeitos_verificar, triagem_lotes
    assert dedup.DECISAO_LIGADO is esquema.DECISAO_LIGADO
    assert triagem_lotes.COLUNAS_FILA_HUMANA_TC is esquema.COLUNAS_FILA_HUMANA_TC
    assert triagem_lotes.ARQ_CODEBOOK_ELEGIBILIDADE is esquema.ARQ_CODEBOOK_ELEGIBILIDADE
    assert efeitos_verificar.COLUNAS_EFEITOS_BINARIOS is esquema.COLUNAS_EFEITOS_BINARIOS


@pytest.mark.parametrize("modulo, local, promovida", [
    ("projeto", "PENDENCIA_PRESS", "PENDENCIA_PRESS"),
    ("projeto", "PENDENCIA_CONCORDANCIA", "PENDENCIA_CONCORDANCIA"),
    ("projeto", "TIPOS_SEM_CERTEZA", "TIPOS_SEM_CERTEZA"),
    ("projeto", "CRITERIO_ATALHO_RAPIDA", "CRITERIO_ATALHO_RAPIDA"),
    ("projeto", "FRACAO_MINIMA_DUPLA_RAPIDA", "FRACAO_MINIMA_DUPLA_RAPIDA"),
    ("projeto", "MIN_INCLUIDOS_LIMIAR_ALCANCAVEL", "MIN_INCLUIDOS_LIMIAR_ALCANCAVEL"),
    ("qualidade", "PENDENCIA_CONSENSO_ROB", "PENDENCIA_CONSENSO_ROB"),
    ("qualidade", "PADRAO_CONCORDANCIA", "PADRAO_CONCORDANCIA_ROB"),
    ("caixa", "DIMENSAO_PAINEL", "DIMENSAO_PAINEL"),
    ("caixa", "REGRA_VERSAO", "REGRA_VERSAO_CAIXA"),
])
def test_constantes_locais_restantes_tem_o_mesmo_valor_do_esquema(modulo, local, promovida):
    """Módulos que ainda definem a constante localmente precisam concordar com o valor promovido."""
    mod = importlib.import_module(f"rslib.{modulo}")
    if not hasattr(mod, local):
        pytest.skip(f"{modulo}.{local} não existe mais (usa esquema.{promovida})")
    valor = getattr(mod, local)
    esperado = getattr(esquema, promovida)
    if isinstance(valor, (set, frozenset, list, tuple)):
        assert set(valor) == set(esperado)
    else:
        assert valor == esperado


def test_campos_do_atalho_lidos_pelo_g4_sao_os_gravados_pela_validacao():
    projeto = importlib.import_module("rslib.projeto")
    lidos = set()
    for nome in ("CAMPOS_FRACAO_DUPLA", "CAMPOS_N_DUPLA", "CAMPOS_N_POPULACAO", "CAMPOS_KAPPA_DUPLA"):
        lidos |= set(getattr(projeto, nome, ()))
    if not lidos:
        pytest.skip("projeto.py não expõe os campos lidos do atalho")
    gravados = set(esquema.CAMPOS_ATALHO_RAPIDA)
    for grupo in ("CAMPOS_FRACAO_DUPLA", "CAMPOS_N_DUPLA", "CAMPOS_N_POPULACAO", "CAMPOS_KAPPA_DUPLA"):
        alternativas = set(getattr(projeto, grupo, ()))
        assert not alternativas or alternativas & gravados, grupo
