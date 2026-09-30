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


# ---------------------------------------------------------------------------
# Seção 7 montada dos dados e seção 6 com notas sobre as pendências citadas (v1.3)
# ---------------------------------------------------------------------------
TEXTO_SECAO_7_LIMPA = (
    "## 7. Declaração de responsabilidade\n\n"
    "As ferramentas de IA listadas foram usadas como apoio sob supervisão humana. Critérios, protocolo, "
    "juízos de risco de viés, de certeza (GRADE/CERQual), rótulos da caixa de ferramentas e conclusões são "
    "responsabilidade dos revisores humanos, que conferiram as saídas conforme os portões e as validações "
    "acima. Decisões de IA não validadas estão sinalizadas como pendências.\n")


def _certeza(raiz, nome, validados):
    pasta = raiz / "06-analise"
    pasta.mkdir(parents=True, exist_ok=True)
    linhas = ["familia_intervencao,construto_outcome,certeza,validado_humano"]
    linhas += [f"fam,desfecho{i},baixa,{v}" for i, v in enumerate(validados)]
    (pasta / nome).write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return f"06-analise/{nome}"


def _rob(raiz, ferramenta, n_resultados, n_validados):
    from rslib import estado
    return estado.registrar_evento(raiz, "rob_consolidado", "09_extracao_rob", "script", "rs.py qualidade",
                                   dados={"ferramenta": ferramenta, "n_resultados": n_resultados,
                                          "n_validados_humano": n_validados,
                                          "todos_validados_humano": n_validados == n_resultados})


def _efeitos(raiz, n, n_nao_aptos):
    from rslib import estado
    return estado.registrar_evento(raiz, "efeitos_verificados", "09_extracao_rob", "script", "rs.py analise",
                                   dados={"n_efeitos": n, "n_nao_aptos": n_nao_aptos,
                                          "pode_seguir_g7": n_nao_aptos == 0})


def _caixa(raiz, n_linhas, n_pendentes):
    from rslib import estado
    return estado.registrar_evento(raiz, "caixa_gerada", "10_sintese", "script", "rs.py caixa",
                                   dados={"n_linhas": n_linhas, "n_pendentes": n_pendentes})


def _portao_automatico(raiz, g, confirmar=None):
    """Aprovação pelo autopiloto com a pendência de confirmação; `confirmar` = tipo do ator que a fecha."""
    from rslib import esquema, estado
    ev = estado.registrar_portao(raiz, g, "autopiloto", ator_tipo="ia_coordenador")
    pid = estado.abrir_pendencia(raiz, "revisao_humana_portao", esquema.PORTOES[g],
                                 f"confirmar a aprovação automática do {g}", portao=g, ator_id="autopiloto")
    if confirmar:
        estado.fechar_pendencia(raiz, pid, "confirmado", ator_tipo=confirmar,
                                ator_id="revisor_humano_1" if confirmar == "humano" else "script")
    return ev, pid


def _secao(md, numero):
    return md.split(f"## {numero}. ")[1].split("\n## ")[0]


def test_tudo_validado_mantem_a_secao_7_de_sempre(projeto_vazio, capsys):
    """Sem nada em aberto, a seção 7 sai byte a byte como antes (projetos limpos não ganham versão nova)."""
    from rslib import esquema, estado
    raiz = projeto_vazio
    processo_com_ia(raiz)
    _efeitos(raiz, 10, 0)
    _rob(raiz, "rob2", 4, 4)
    certeza = _certeza(raiz, "certeza.csv", ["sim", "1", "x"])
    _caixa(raiz, 3, 0)
    _portao_automatico(raiz, "G7", confirmar="humano")
    codigo, resumo = rodar(["--dir", str(raiz), "declaracao-ia"], capsys)
    md = (raiz / esquema.ARQ_DECLARACAO_IA).read_text(encoding="utf-8")
    assert codigo == 0 and resumo["rascunho"] is False and esquema.MARCA_RASCUNHO not in md
    assert md.endswith("## 6. Pendências abertas\n\nNenhuma.\n\n" + TEXTO_SECAO_7_LIMPA)
    ev = estado.ler_log(raiz)[-1]
    assert {"caminho": certeza, "sha256": estado.sha256_arquivo(raiz / certeza)} in ev["artefatos"]


def test_juizos_sem_validacao_humana_listados_na_secao_7(projeto_vazio, capsys):
    from rslib import esquema, estado
    raiz = projeto_vazio
    _decisao_ia(raiz)  # IA na triagem sem validação que decide
    _efeitos(raiz, 10, 3)
    ev_rob2 = _rob(raiz, "rob2", 5, 0)
    _rob(raiz, "robins_i", 2, 2)
    certeza = _certeza(raiz, "certeza.csv", ["1", "0", ""])
    amplo = _certeza(raiz, "certeza_agrupamento_amplo.csv", ["nao", "nao"])
    (raiz / "06-analise/superado").mkdir()
    _certeza(raiz, "superado/certeza_antiga.csv", ["0"])  # subpasta: não é lida
    _caixa(raiz, 4, 2)
    _, p_g5 = _portao_automatico(raiz, "G5", confirmar="humano")
    _portao_automatico(raiz, "G6", confirmar="humano")
    ev_g6 = estado.registrar_portao(raiz, "G6", "autopiloto", ator_tipo="ia_coordenador")  # nova aprovação depois
    ev_g7, p_g7 = _portao_automatico(raiz, "G7")
    ev_g8 = estado.registrar_portao(raiz, "G8", "autopiloto", ator_tipo="ia_coordenador")  # sem pendência
    _portao_automatico(raiz, "G9", confirmar="script")  # fechada sem humano
    estado.registrar_portao(raiz, "G3", "autopiloto", ator_tipo="ia_coordenador")
    estado.registrar_portao(raiz, "G3", "revisor_humano_1")  # a última decisão é humana: nada a declarar
    p_dedup = estado.abrir_pendencia(raiz, "dedup_candidatos", "05_organizacao", "12 pares candidatos", n=12)

    codigo, resumo = rodar(["--dir", str(raiz), "declaracao-ia"], capsys)
    md = (raiz / esquema.ARQ_DECLARACAO_IA).read_text(encoding="utf-8")
    assert codigo == 0 and resumo["rascunho"] is True
    assert "; juízos de IA sem validação humana (seção 7))." in md.splitlines()[2]
    s7 = _secao(md, 7)
    assert TEXTO_SECAO_7_LIMPA.split("\n\n")[1].strip() not in s7
    assert "exceto nos juízos listados abaixo" in s7 and "são rascunhos de IA" in s7
    sha_certeza, sha_amplo = (estado.sha256_arquivo(raiz / c)[:16] for c in (certeza, amplo))
    esperados = [
        "- Dados de efeito: 3 de 10 efeitos não aptos para o G7",
        f"- Risco de viés (rob2): 5 de 5 resultados sem validação humana na consolidação (`rob_consolidado`, "
        f"seq {ev_rob2['seq']},",
        f"- Certeza da evidência (GRADE/CERQual) em `{certeza}` (sha256 `{sha_certeza}…`): 2 de 3 linhas sem "
        "`validado_humano`.",
        f"- Certeza da evidência (GRADE/CERQual) em `{amplo}` (sha256 `{sha_amplo}…`): 2 de 2 linhas sem "
        "`validado_humano`.",
        "- Rótulos da caixa de ferramentas: 2 de 4 linhas pendentes ou em rascunho",
        f"- Portão G6 (08_piloto_extracao), aprovado por autopiloto (ia_coordenador) em "
        f"{ev_g6['ts'][:10]} (seq {ev_g6['seq']}): sem confirmação humana registrada.",
        f"- Portão G7 (09_extracao_rob), aprovado por autopiloto (ia_coordenador) em {ev_g7['ts'][:10]} "
        f"(seq {ev_g7['seq']}): confirmação humana pendente ({p_g7}).",
        f"- Portão G8 (10_sintese), aprovado por autopiloto (ia_coordenador) em {ev_g8['ts'][:10]} "
        f"(seq {ev_g8['seq']}): sem confirmação humana registrada.",
        "- Portão G9 (11_relato), aprovado por autopiloto (ia_coordenador) em",
        "- Triagem de títulos e resumos: decisões de IA sem validação calculada com finalidade validação da rodada "
        "ativa (seção 4).",
        f"- Pendências abertas em organização e deduplicação (05_organizacao): {p_dedup} (dedup_candidatos); "
        "descrição na seção 6.",
    ]
    posicoes = [s7.index(e) for e in esperados]
    assert posicoes == sorted(posicoes)
    assert "Portão G3" not in s7 and "certeza_antiga" not in md
    assert p_g7 not in s7.split("- Pendências abertas")[1]  # já listada no portão, não se repete
    assert f"Portões aprovados sem humano e confirmados depois por humano: G5 ({p_g5}, fechada em" in s7
    assert "G6 (" not in s7.split("Portões aprovados sem humano")[1]  # confirmação anterior à nova aprovação
    assert "Validação humana completa registrada: risco de viés (robins_i), 2 de 2 resultados" in s7
    assert s7.rstrip().endswith("Decisões de IA não validadas estão sinalizadas como pendências.")
    ev = estado.ler_log(raiz)[-1]
    assert {a["caminho"] for a in ev["artefatos"]} >= {certeza, amplo}


def test_secao_7_so_com_pendencia_aberta_nao_repete_o_texto_limpo(projeto_vazio, capsys):
    """Pendência aberta sem juízo de IA: exceção na seção 7, sem o motivo de juízos no cabeçalho."""
    from rslib import esquema, estado
    estado.abrir_pendencia(projeto_vazio, "revisao_press", "04_busca", "PRESS por humano", portao="G3")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "declaracao-ia"], capsys)
    md = (projeto_vazio / esquema.ARQ_DECLARACAO_IA).read_text(encoding="utf-8")
    assert resumo["rascunho"] is True and "(1 pendências abertas)." in md and "juízos de IA" not in md
    assert "- Pendências abertas em busca (04_busca): P001 (revisao_press); descrição na seção 6." in _secao(md, 7)


def test_sucessoras_so_entre_pendencias_do_mesmo_tipo():
    """A confirmação de portão copia o "[substitui ...]" de outra pendência e não pode virar sucessora dela."""
    from rslib import declaracao_ia

    def ab(seq, pid, tipo, descricao):
        return pid, {"seq": seq, "evento": "pendencia_aberta", "dados": {"pendencia": pid, "tipo": tipo,
                                                                          "descricao": descricao}}
    aberturas = dict([ab(1, "P001", "verificacao_humana_efeitos", "conferir 10 efeitos"),
                      ab(2, "P003", "revisao_humana_portao", "confirmar o G7: P002 aberta: conferir [substitui P001]"),
                      ab(3, "P002", "verificacao_humana_efeitos", "conferir 12 efeitos [substitui P001]"),
                      ab(4, "P005", "certeza_humana", "GRADE de 7 células"),
                      ab(5, "P006", "certeza_humana", "GRADE refeito"),
                      ab(6, "P007", "outro_tipo", "x [substitui P006]")])
    fechamentos = {"P005": {"seq": 7, "motivo": "substituída por P006 (mesma tarefa)"},
                   "P006": {"seq": 8, "motivo": "substituida por P007"}}
    suc = declaracao_ia.sucessoras_de_pendencias({"pendencias": []}, aberturas, fechamentos)
    assert suc == {"P001": "P002", "P005": "P006"}
    assert declaracao_ia.cadeia_de_sucessoras("P001", {"P001": "P002", "P002": "P004", "P004": "P001"}) == [
        "P002", "P004"]  # ciclo não trava


def test_secao_6_anota_citadas_fechadas_com_sucessoras(projeto_vazio, capsys):
    from rslib import esquema, estado
    raiz = projeto_vazio

    def abrir(tipo, etapa, descricao, portao=None):
        return estado.abrir_pendencia(raiz, tipo, etapa, descricao, portao=portao)

    def fechar(pid, motivo, ator_tipo="script"):
        estado.fechar_pendencia(raiz, pid, motivo, ator_tipo=ator_tipo, ator_id="teste")
        return estado.ler_log(raiz)[-1]

    ef = "verificacao_humana_efeitos"
    p1 = abrir(ef, "09_extracao_rob", "conferir 10 efeitos", "G7")                                 # P001
    f1 = fechar(p1, "atualizada automaticamente: n 10 -> 12")
    p2 = abrir(ef, "09_extracao_rob", f"conferir 12 efeitos [substitui {p1}]", "G7")                # P002
    p3 = abrir("revisao_humana_portao", "09_extracao_rob",                                           # P003
               f"confirmar a aprovação automática do G7: 12 efeitos sem verificação; {p2} aberta: conferir 12 "
               f"efeitos [substitui {p1}]", "G7")
    f2 = fechar(p2, "atualizada automaticamente: n 12 -> 15")
    p4 = abrir(ef, "09_extracao_rob", f"conferir 15 efeitos [substitui {p2}]", "G7")                # P004
    f4 = fechar(p4, "conferidos", ator_tipo="humano")
    p5 = abrir("dedup_candidatos", "05_organizacao", "10 pares")                                    # P005
    fechar(p5, "atualizada automaticamente: n 10 -> 12")
    p6 = abrir("dedup_candidatos", "05_organizacao", f"12 pares [substitui {p5}]")                  # P006
    p7 = abrir("certeza_humana", "10_sintese", "GRADE de 7 células")                                # P007
    p8 = abrir("certeza_humana", "10_sintese", "GRADE refeito: 9 células")                          # P008
    f7 = fechar(p7, f"substituída por {p8} (mesma tarefa humana)", ator_tipo="humano")
    p9 = abrir("revisao_humana_portao", "10_sintese",                                               # P009
               f"confirmar a aprovação automática do G8: {p7} aberta: GRADE de 7 células; P999 citada", "G8")

    codigo, _ = rodar(["--dir", str(raiz), "declaracao-ia"], capsys)
    md = (raiz / esquema.ARQ_DECLARACAO_IA).read_text(encoding="utf-8")
    s6 = _secao(md, 6)
    assert "As descrições estão como foram registradas na abertura de cada pendência" in s6
    assert "| Id | Tipo | Etapa | Portão | Aberta em | Descrição (como registrada na abertura) | N |" in s6
    linhas = {l.split(" | ")[0][2:]: l for l in s6.splitlines() if l.startswith("| P")}
    assert set(linhas) == {p3, p6, p8, p9}
    ab3 = next(e for e in estado.ler_log(raiz) if e["evento"] == "pendencia_aberta"
               and e["dados"]["pendencia"] == p3)
    assert f"| {ab3['ts'][:10]} (seq {ab3['seq']}) |" in linhas[p3]
    d = lambda ev: ev["ts"][:10]
    assert linhas[p3].endswith(
        f"[substitui {p1}] [{p2}: fechada em {d(f2)} (seq {f2['seq']}); substituída por {p4}, fechada em {d(f4)}] "
        f"[{p1}: fechada em {d(f1)} (seq {f1['seq']}); substituída por {p2} → {p4}, fechada em {d(f4)}] |  |")
    assert linhas[p6].endswith(f"12 pares [substitui {p5}] |  |")  # sem nota: a cadeia da citada chega nela
    assert f"[{p5}:" not in linhas[p6]
    assert linhas[p9].endswith(f"P999 citada [{p7}: fechada em {d(f7)} (seq {f7['seq']}); substituída por {p8}, "
                               "aberta] |  |")
    assert "P999:" not in linhas[p9] and f"{p9}:" not in linhas[p9]


def test_certeza_sem_coluna_validado_humano_segue_a_regra_da_caixa(projeto_vazio, capsys):
    """Sem a coluna, a caixa não rebaixa a rascunho; a declaração concorda e só cita o arquivo na seção 7."""
    from rslib import esquema, estado
    raiz = projeto_vazio
    pasta = raiz / "06-analise"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "certeza.csv").write_text("familia_intervencao,construto_outcome,certeza\nfam,desfecho,baixa\n",
                                       encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(raiz), "declaracao-ia"], capsys)
    md = (raiz / esquema.ARQ_DECLARACAO_IA).read_text(encoding="utf-8")
    assert codigo == 0 and resumo["rascunho"] is False and md.endswith(TEXTO_SECAO_7_LIMPA)
    estado.abrir_pendencia(raiz, "dedup_candidatos", "05_organizacao", "3 pares", n=3)
    codigo, resumo = rodar(["--dir", str(raiz), "declaracao-ia"], capsys)
    s7 = _secao((raiz / esquema.ARQ_DECLARACAO_IA).read_text(encoding="utf-8"), 7)
    assert "Certeza sem a coluna `validado_humano`" in s7 and "`06-analise/certeza.csv` (sha256" in s7
    assert "- Certeza da evidência" not in s7
