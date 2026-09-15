"""Testes da declaração de uso de IA gerada do log: modelos, prompts com hash, validação, rascunho e idempotência."""

import argparse
import json


def rodar(argv, capsys):
    from rslib import declaracao_ia
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    sub = parser.add_subparsers(dest="comando")
    declaracao_ia.registrar(sub)
    args = parser.parse_args(argv)
    codigo = args.func(args)
    return codigo, json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def decisoes(raiz, linhas):
    with open(raiz / "dados" / "decisoes.jsonl", "w", encoding="utf-8") as f:
        for l in linhas:
            f.write(json.dumps(l) + "\n")


def processo_com_ia(raiz, atende=True):
    from rslib import estado
    prompt = raiz / "02-triagem/prompts/ta_v1.md"
    prompt.write_text("# Critérios T/A v1\nC1 população\n", encoding="utf-8")
    estado.registrar_evento(raiz, "artefato_versionado", "06_triagem_ta", "humano", "revisor_humano_1",
                            dados={"versao": "ta_v1"}, artefatos=["02-triagem/prompts/ta_v1.md"])
    estado.registrar_evento(raiz, "lote_mesclado", "06_triagem_ta", "ia_subagente", "revisor_A",
                            dados={"lote": "lote_001", "criterios_sha": "c" * 64, "parametros": {"lote": 25}},
                            modelo="modelo-teste-a")
    estado.registrar_evento(raiz, "lote_mesclado", "06_triagem_ta", "ia_api", "revisor_B",
                            dados={"lote": "api", "custo_usd": 1.25}, modelo="modelo-teste-b")
    decisoes(raiz, [
        {"id_rs": "RS0001", "etapa": "ta", "rodada": "ta_v1", "revisor": "A", "tipo_ator": "ia_subagente",
         "modelo": "modelo-teste-a", "prompt_sha": "a" * 64, "decisao": "incluir", "ts": "2026-01-02T10:00:00Z"},
        {"id_rs": "RS0002", "etapa": "ta", "rodada": "ta_v1", "revisor": "B", "tipo_ator": "ia_api",
         "modelo": "modelo-teste-b", "prompt_sha": "b" * 64, "decisao": "excluir", "ts": "2026-01-03T10:00:00Z"},
        {"id_rs": "RS0002", "etapa": "ta", "rodada": "ta_v1", "revisor": "humano_1", "tipo_ator": "humano",
         "decisao": "incluir", "ts": "2026-01-04T10:00:00Z"},
    ])
    estado.registrar_evento(raiz, "validacao_calculada", "06_triagem_ta", "script", "rs.py validar",
                            dados={"sensibilidade": 0.97, "sensibilidade_ic95": [0.91, 0.99], "kappa": 0.72,
                                   "pabak": 0.8, "atende_limiares": atende, "elusao": {"n": 300, "perdidos_estimados": 2}})
    estado.registrar_portao(raiz, "G4", "revisor_humano_1", criterios={"recall_li": 0.91})


def test_declaracao_completa_e_idempotente(projeto_vazio, capsys):
    from rslib import esquema, estado
    processo_com_ia(projeto_vazio)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    assert codigo == 0 and resumo["rascunho"] is False
    assert resumo["modelos"] == ["modelo-teste-a", "modelo-teste-b"] and resumo["n_validacoes"] == 1
    md = (projeto_vazio / "07-relatorio/declaracao_uso_ia.md").read_text(encoding="utf-8")
    assert esquema.MARCA_RASCUNHO not in md
    assert "| modelo-teste-a | ia_subagente | 06_triagem_ta, decisões ta | 2026-01-02 |" in md
    assert '{"lote": 25}' in md
    sha_prompt = estado.sha256_arquivo(projeto_vazio / "02-triagem/prompts/ta_v1.md")
    assert "02-triagem/prompts/ta_v1.md" in md and sha_prompt[:16] in md
    assert "a" * 16 in md and "c" * 16 in md  # prompt_sha das decisões e criterios_sha do evento
    assert "Atende aos limiares: **sim**" in md and "sensibilidade_ic95 | [0.91; 0.99]" in md
    assert "Amostras de elusão registradas: 1." in md
    assert "| G4 | 06_triagem_ta | humano | revisor_humano_1 |" in md
    assert "US$ 1.25 em 1 eventos" in md
    assert "responsabilidade dos revisores humanos" in md

    n = len(estado.ler_log(projeto_vazio))
    assert estado.ler_log(projeto_vazio)[-1]["evento"] == "relatorio_gerado"
    codigo, _ = rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    assert codigo == 0 and len(estado.ler_log(projeto_vazio)) == n
    assert (projeto_vazio / "07-relatorio/declaracao_uso_ia.md").read_text(encoding="utf-8") == md

    # pendência aberta: regenerar marca rascunho
    estado.abrir_pendencia(projeto_vazio, "verificacao_humana_efeitos", "09_extracao_rob", "conferir efeitos",
                           portao="G7", n=4)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    md = (projeto_vazio / "07-relatorio/declaracao_uso_ia.md").read_text(encoding="utf-8")
    assert resumo["rascunho"] is True and esquema.MARCA_RASCUNHO in md and "conferir efeitos" in md


def test_validacao_abaixo_do_limiar_marca_rascunho(projeto_vazio, capsys):
    from rslib import esquema
    processo_com_ia(projeto_vazio, atende=False)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    md = (projeto_vazio / "07-relatorio/declaracao_uso_ia.md").read_text(encoding="utf-8")
    assert resumo["rascunho"] is True and "validações abaixo dos limiares" in md
    assert "Atende aos limiares: **não**" in md and esquema.MARCA_RASCUNHO in md


def test_ia_na_triagem_sem_validacao(projeto_vazio, capsys):
    decisoes(projeto_vazio, [{"id_rs": "RS0001", "etapa": "ta", "rodada": "ta_v1", "revisor": "A",
                              "tipo_ator": "ia_subagente", "modelo": None, "decisao": "incluir", "ts": "2026-01-02T00:00:00Z"}])
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    md = (projeto_vazio / "07-relatorio/declaracao_uso_ia.md").read_text(encoding="utf-8")
    assert resumo["rascunho"] is True and "sem validação calculada" in md
    assert "modelo não registrado: ia_subagente" in md


def test_sem_uso_de_ia(projeto_vazio, capsys):
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "declaracao-ia", "--out", "07-relatorio/decl.md"], capsys)
    md = (projeto_vazio / "07-relatorio/decl.md").read_text(encoding="utf-8")
    assert codigo == 0 and resumo["rascunho"] is False and "Nenhum uso de IA registrado no log." in md


# ---------------------------------------------------------------------------
# Validação que decide, histórico e custo (v1.1)
# ---------------------------------------------------------------------------
def _validacao(raiz, finalidade, atende, rodada="ta_v2", **extra):
    from rslib import estado
    dados = {"tipo": "amostra", "finalidade": finalidade, "rodada": rodada, "etapa": "ta", "amostra_id": extra.pop(
        "amostra_id", f"{finalidade}01"), "sensibilidade": 0.9, "kappa_humanos": 0.7, "atende_limiares": atende, **extra}
    return estado.registrar_evento(raiz, "validacao_calculada", "06_triagem_ta", "script", "validacao", dados=dados)


def _rodada_ativa(raiz, rodada):
    from rslib import esquema, estado
    est = estado.carregar_estado(raiz)
    est["versoes_ativas"][esquema.VERSAO_ATIVA_RODADA_TA] = rodada
    estado.salvar_estado(raiz, est)


def _decisao_ia(raiz, rodada="ta_v2"):
    decisoes(raiz, [{"id_rs": "RS0001", "etapa": "ta", "rodada": rodada, "revisor": "A", "tipo_ator": "ia_subagente",
                     "modelo": "m", "decisao": "incluir", "ts": "2026-01-02T00:00:00Z"}])


def test_calibracao_reprovada_nao_marca_rascunho_e_vira_historico(projeto_vazio, capsys):
    """Regressão: qualquer calibração reprovada deixava a declaração em rascunho para sempre."""
    from rslib import esquema
    _decisao_ia(projeto_vazio)
    _rodada_ativa(projeto_vazio, "ta_v2")
    _validacao(projeto_vazio, "calibracao", False, rodada="calib_v1")
    _validacao(projeto_vazio, "desenvolvimento", False)
    _validacao(projeto_vazio, "validacao", False, amostra_id="amostra01")  # reprovada e substituída
    _validacao(projeto_vazio, "validacao", True, amostra_id="amostra02", sensibilidade_ic=[0.93, 0.99])
    _validacao(projeto_vazio, "elusao", None, tipo="elusao", elusao=0.01, perdidos_estimados=2.5)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    md = (projeto_vazio / "07-relatorio/declaracao_uso_ia.md").read_text(encoding="utf-8")
    assert codigo == 0 and resumo["rascunho"] is False and esquema.MARCA_RASCUNHO not in md
    assert resumo["n_validacoes"] == 5
    decide = md.split("### Validação que decide")[1].split("###")[0]
    assert "rodada ta_v2" in decide and "Atende aos limiares: **sim**" in decide and "amostra02" in decide
    historico = md.split("### Histórico")[1].split("###")[0]
    assert "calibração" in historico and "desenvolvimento" in historico and "amostra01" in historico
    assert "### Elusão e estabilidade" in md and "Amostras de elusão registradas: 1." in md


def test_validacao_que_decide_e_da_rodada_ativa(projeto_vazio, capsys):
    from rslib import esquema
    _decisao_ia(projeto_vazio, "ta_v3")
    _validacao(projeto_vazio, "validacao", True, rodada="ta_v2")
    _validacao(projeto_vazio, "validacao", False, rodada="ta_v3")
    _rodada_ativa(projeto_vazio, "ta_v2")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    assert resumo["rascunho"] is False, "a reprovada é de outra rodada"
    _rodada_ativa(projeto_vazio, "ta_v3")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    md = (projeto_vazio / "07-relatorio/declaracao_uso_ia.md").read_text(encoding="utf-8")
    assert resumo["rascunho"] is True and "validações abaixo dos limiares (a que decide: seq" in md
    assert esquema.MARCA_RASCUNHO in md
    _rodada_ativa(projeto_vazio, "ta_v4")  # rodada ativa sem validação
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    md = (projeto_vazio / "07-relatorio/declaracao_uso_ia.md").read_text(encoding="utf-8")
    assert resumo["rascunho"] is True and "sem validação calculada" in md


def test_so_calibracao_com_ia_na_triagem_e_rascunho(projeto_vazio, capsys):
    _decisao_ia(projeto_vazio)
    _validacao(projeto_vazio, "calibracao", True, rodada="ta_v2")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    md = (projeto_vazio / "07-relatorio/declaracao_uso_ia.md").read_text(encoding="utf-8")
    assert resumo["rascunho"] is True and "sem validação calculada" in md


def test_custo_calculado_de_uso_tokens_e_nao_registrado(projeto_vazio, capsys):
    from rslib import estado
    raiz = projeto_vazio
    # 1) evento com uso_tokens e tabela de preços, sem custo: calculado pela tabela do evento
    estado.registrar_evento(raiz, "lote_mesclado", "06_triagem_ta", "ia_api", "triagem_api", modelo="m", dados={
        "rodada": "ta_v2", "modo": "sincrono", "modelos": {"A": "ma", "B": "mb"},
        "uso_tokens": {"A": {"chamadas": 2, "tokens_entrada": 1_000_000, "tokens_saida": 0},
                       "B": {"chamadas": 1, "tokens_entrada": 0, "tokens_saida": 500_000}},
        "tabela_precos": {"ma": {"entrada": 1.0, "saida": 2.0}, "mb": {"entrada": 3.0, "saida": 4.0}}})
    # 2) custo_usd e custo_estimado_usd no mesmo evento contam uma vez só
    estado.registrar_evento(raiz, "lote_mesclado", "06_triagem_ta", "ia_api", "triagem_api", modelo="m",
                            dados={"custo_usd": 0.5, "custo_estimado_usd": 0.5})
    # 3) uso de API sem custo nem tokens
    estado.registrar_evento(raiz, "lote_mesclado", "06_triagem_ta", "ia_api", "triagem_api", modelo="m",
                            dados={"lote": "api"})
    # 4) estimativa prévia: listada, nunca somada
    estado.registrar_evento(raiz, "artefato_versionado", "06_triagem_ta", "script", "triagem_api",
                            dados={"tipo": "estimativa_custo_api", "rodada": "ta_v2", "chamadas_api": 0,
                                   "estimativa": {"custo_total_usd": 99.0}})
    codigo, _ = rodar(["--dir", str(raiz), "declaracao-ia"], capsys)
    md = (raiz / "07-relatorio/declaracao_uso_ia.md").read_text(encoding="utf-8")
    assert "Custo de API registrado: US$ 3.50 em 2 eventos." in md  # 1,00 + 2,00 + 0,50
    assert "tokens × tabela do evento" in md
    assert "sem custo nem tokens com preço registrados em 1 eventos" in md and "custo não registrado" in md
    assert "Estimativas prévias" in md and "US$ 99.00" in md


def test_sem_custo_registrado_declara(projeto_vazio, capsys):
    _decisao_ia(projeto_vazio)
    rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    md = (projeto_vazio / "07-relatorio/declaracao_uso_ia.md").read_text(encoding="utf-8")
    assert "Custo de API registrado: não registrado." in md
    assert "Nenhum evento do log traz custo ou uso de tokens de API" in md


def test_regressao_evento_da_declaracao_grava_ultimo_seq(projeto_vazio, capsys):
    """O G9 compara por dados.ultimo_seq (e o sha do arquivo), não pela frase do texto."""
    from rslib import declaracao_ia, esquema, estado
    processo_com_ia(projeto_vazio)
    antes = max(e["seq"] for e in estado.ler_log(projeto_vazio))
    codigo, _ = rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    ev = estado.ler_log(projeto_vazio)[-1]
    assert codigo == 0 and ev["evento"] == "relatorio_gerado" and ev["ator"]["id"] == declaracao_ia.ATOR
    assert ev["dados"]["ultimo_seq"] == antes and ev["seq"] == antes + 1
    sha = estado.sha256_arquivo(projeto_vazio / esquema.ARQ_DECLARACAO_IA)
    assert {"caminho": esquema.ARQ_DECLARACAO_IA, "sha256": sha} in ev["artefatos"]
    md = (projeto_vazio / esquema.ARQ_DECLARACAO_IA).read_text(encoding="utf-8")
    assert "Apêndice B" not in md and "references/ia-validacao.md" in md


def test_regressao_declaracao_com_estado_corrompido_sai_com_erro(projeto_vazio, capsys):
    (projeto_vazio / "rs_estado.json").write_text("{", encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    assert codigo == 1 and resumo["ok"] is False and "corrompido" in resumo["detalhe"]
