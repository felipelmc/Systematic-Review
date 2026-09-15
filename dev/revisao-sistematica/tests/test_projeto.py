"""Testes de init, status, ambiente, portões, pendências e emendas."""

import json

import pytest

from conftest import SKILL, ler_jsonl
from test_prisma import ELEGIBILIDADE, montar_ledger, rodar


G1_OK = '{"pergunta": "X reduz Y?", "tipo_revisao": "efetividade_meta"}'
CODEBOOK = "dimensao,variavel,descricao,prompt,tipo,aplicavel_se\nId,tipo_estudo,Tipo,Classifique o estudo,categorica,\n"


def protocolo_completo(raiz, texto="# Protocolo\n"):
    """Protocolo, codebook v0 e codebook de elegibilidade sem placeholders (o mínimo que o G2 exige)."""
    (raiz / "00-protocolo").mkdir(parents=True, exist_ok=True)
    (raiz / "00-protocolo" / "protocolo.md").write_text(texto, encoding="utf-8")
    (raiz / "00-protocolo" / "codebook_v0_oqf.csv").write_text(CODEBOOK, encoding="utf-8")
    (raiz / "00-protocolo" / "codebook_elegibilidade.csv").write_text(CODEBOOK, encoding="utf-8")


def press_registrado(raiz, string_id="S-scopus-v1"):
    (raiz / "01-busca").mkdir(parents=True, exist_ok=True)
    (raiz / "01-busca" / f"press_{string_id}.md").write_text("PRESS 2015: revisor_humano_2, sem mudanças\n",
                                                            encoding="utf-8")


def rob_consolidado(raiz, chaves=("Silva2020", "Souza2019", "Outro2000"), ferramenta="rob2", validados=True):
    """rob_geral.csv e evento rob_consolidado como `qualidade consolidar` fase 2 os grava (um resultado por chave)."""
    from rslib import esquema, estado
    (raiz / "04-qualidade").mkdir(parents=True, exist_ok=True)
    linhas = [f"{c},ES{i:04d},notas,{ferramenta},baixo,{1 if validados else 0}" for i, c in enumerate(chaves, start=1)]
    (raiz / esquema.ARQ_ROB_GERAL).write_text(",".join(esquema.COLUNAS_ROB_GERAL) + "\n" + "\n".join(linhas) + "\n",
                                             encoding="utf-8")
    estado.registrar_evento(raiz, "rob_consolidado", "09_extracao_rob", "script", "qualidade",
                            dados={"ferramenta": ferramenta, "n_resultados": len(chaves),
                                   "n_validados_humano": len(chaves) if validados else 0,
                                   "todos_validados_humano": validados, "rob_geral": {"baixo": len(chaves)}},
                            artefatos=[esquema.ARQ_ROB_GERAL])


def _eventos(raiz, nome=None):
    eventos = ler_jsonl(raiz / "rs_log.jsonl")
    return [e for e in eventos if nome is None or e["evento"] == nome]


@pytest.fixture
def sem_ambiente_lento(monkeypatch):
    """Evita chamar Rscript/quarto em todo teste de init (o diagnóstico real tem teste próprio)."""
    from rslib import ambiente
    falso = {"verificado_em": "2026-01-01T00:00:00Z", "python": {}, "r": {}, "quarto": {}, "chaves_api": {},
             "skills_irmas": {}, "resumo": {"python_ok": True}}
    monkeypatch.setattr(ambiente, "verificar", lambda incluir_r=True: dict(falso))
    return falso


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------
def test_init_cria_projeto_e_e_idempotente(tmp_path, capsys, sem_ambiente_lento):
    from rslib import esquema, estado
    raiz = tmp_path / "rev"
    codigo, res = rodar(capsys, "--dir", raiz, "init", "--titulo", "Efeito de X sobre Y", "--tipo", "escopo")
    assert codigo == 0 and res["criado"] is True
    assert all((raiz / p).is_dir() for p in esquema.PASTAS_PROJETO)
    est = estado.carregar_estado(raiz)
    assert est["projeto"]["tipo_revisao"] == "escopo" and est["ambiente"]["resumo"]["python_ok"]
    assert [e["evento"] for e in _eventos(raiz)] == ["projeto_criado", "ambiente_verificado"]

    codigo, res = rodar(capsys, "--dir", raiz, "init", "--titulo", "Efeito de X sobre Y", "--tipo", "escopo")
    assert codigo == 0 and res["ja_existia"] is True and res["mudancas"] == {}
    assert len(_eventos(raiz)) == 2  # nada duplicado

    codigo, res = rodar(capsys, "--dir", raiz, "init", "--titulo", "Efeito de X sobre Y", "--autonomia", "autopiloto")
    assert codigo == 0 and res["mudancas"]["autonomia"] == {"de": "checkpoints", "para": "autopiloto"}
    assert len(_eventos(raiz, "modo_definido")) == 1
    assert estado.carregar_estado(raiz)["modo"]["autonomia"] == "autopiloto"


def test_init_estado_e_log_validam_schema(tmp_path, capsys, sem_ambiente_lento):
    jsonschema = pytest.importorskip("jsonschema")
    raiz = tmp_path / "rev"
    rodar(capsys, "--dir", raiz, "init", "--titulo", "T", "--parcial", "triagem")
    rodar(capsys, "--dir", raiz, "pendencia", "abrir", "--tipo", "validacao_humana", "--etapa", "06_triagem_ta",
          "--descricao", "codificar amostra", "--portao", "G4", "--n", "100")
    schema_estado = json.loads((SKILL / "assets/schemas/estado.schema.json").read_text(encoding="utf-8"))
    schema_evento = json.loads((SKILL / "assets/schemas/evento.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(json.loads((raiz / "rs_estado.json").read_text(encoding="utf-8")), schema_estado)
    for ev in _eventos(raiz):
        jsonschema.validate(ev, schema_evento)


def test_init_parcial_marca_etapas_ignoradas(tmp_path, capsys, sem_ambiente_lento):
    from rslib import estado
    raiz = tmp_path / "rev"
    rodar(capsys, "--dir", raiz, "init", "--titulo", "Só meta", "--parcial", "meta")
    est = estado.carregar_estado(raiz)
    assert "10_sintese" not in est["projeto"]["etapas_ignoradas"]
    assert est["etapas"]["06_triagem_ta"]["status"] == "ignorada"
    codigo, res = rodar(capsys, "--dir", raiz, "status")
    assert res["etapa_atual"] == "10_sintese"


def test_init_recusa_projeto_aninhado_e_artefatos_sem_adotar(tmp_path, capsys, sem_ambiente_lento):
    from rslib import esquema, estado
    raiz = tmp_path / "rev"
    rodar(capsys, "--dir", raiz, "init", "--titulo", "T")
    codigo, res = rodar(capsys, "--dir", raiz / "00-protocolo", "init", "--titulo", "Outro")
    assert codigo == 1 and "aninhado" in res["detalhe"]

    solta = tmp_path / "solta"
    montar_ledger(solta, ate="unicos")
    (solta / "scopus_export.csv").write_text('"Authors","Title","EID"\n"A","B","2-s2.0-1"\n', encoding="utf-8")
    codigo, res = rodar(capsys, "--dir", solta, "init", "--titulo", "T")
    assert codigo == 1 and "--adotar" in res["detalhe"]
    assert not (solta / esquema.ARQ_ESTADO).exists()
    codigo, res = rodar(capsys, "--dir", solta, "init", "--titulo", "T", "--adotar")
    assert codigo == 0 and set(res["artefatos_adotados"]) == {esquema.ARQ_REGISTROS, esquema.ARQ_UNICOS}
    assert any("scopus_export.csv" in s for s in res["sugestoes"])
    est = estado.carregar_estado(solta)
    assert est["artefatos"][esquema.ARQ_REGISTROS]["sha256"]


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------
def test_status_sem_projeto_sugere_adotar(tmp_path, capsys):
    (tmp_path / "exportacoes").mkdir()
    (tmp_path / "exportacoes" / "savedrecs.txt").write_text("FN Clarivate Analytics Web of Science\nVR 1.0\n",
                                                            encoding="utf-8")
    codigo, res = rodar(capsys, "--dir", tmp_path, "status")
    assert codigo == 0 and res["projeto"] is None
    assert {"caminho": "exportacoes/savedrecs.txt", "tipo": "exportacao_wos_texto"} in res["artefatos_encontrados"]
    assert "--adotar" in res["proxima_acao"]["comando"]
    assert any("importar" in s for s in res["proxima_acao"]["sugestoes"])


def test_status_sem_projeto_e_sem_artefatos(tmp_path, capsys):
    codigo, res = rodar(capsys, "--dir", tmp_path, "status")
    assert codigo == 0 and res["artefatos_encontrados"] == [] and "init" in res["proxima_acao"]["comando"]


def test_status_com_pendencias(projeto_vazio, capsys):
    from rslib import estado
    pid = estado.abrir_pendencia(projeto_vazio, "definir_pergunta", "01_pergunta", "entrevista com o usuário")
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert codigo == 0 and res["rascunho"] is True
    assert [p["id"] for p in res["pendencias"]] == [pid]
    assert res["etapa_atual"] == "00_configuracao"  # projeto_vazio não verificou ambiente
    est = estado.carregar_estado(projeto_vazio)
    est["ambiente"] = {"resumo": {"python_ok": True}}
    estado.salvar_estado(projeto_vazio, est)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert res["etapa_atual"] == "01_pergunta"
    assert res["proxima_acao"]["tipo"] == "pendencia" and res["proxima_acao"]["pendencia"] == pid


def test_status_recalcula_etapas_do_ledger_e_aponta_proxima_acao(projeto_vazio, capsys):
    from rslib import estado
    est = estado.carregar_estado(projeto_vazio)
    est["ambiente"] = {"resumo": {"python_ok": True}}
    est["etapas"]["06_triagem_ta"]["status"] = "concluida"  # cache adulterado, sem evento no log
    estado.salvar_estado(projeto_vazio, est)
    for g, criterios in (("G1", '{"pergunta": "X reduz Y?", "tipo_revisao": "efetividade_meta"}'), ("G2", None)):
        protocolo_completo(projeto_vazio)
        argv = ["--dir", projeto_vazio, "portao", g, "--aprovar", "--por", "revisor_humano_1"]
        codigo, _ = rodar(capsys, *(argv + (["--criterios", criterios] if criterios else [])))
        assert codigo == 0
    est = estado.carregar_estado(projeto_vazio)
    assert est["projeto"]["pergunta"] == "X reduz Y?" and est["projeto"]["tipo_revisao"] == "efetividade_meta"
    montar_ledger(projeto_vazio, ate="unicos")
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    etapas = res["etapas"]
    assert etapas["01_pergunta"]["status"] == "concluida" and etapas["02_teoria_framework"]["status"] == "concluida"
    assert etapas["05_organizacao"]["status"] == "concluida"  # dedup cobre todos os registros
    assert etapas["06_triagem_ta"]["status"] == "pendente"  # o cache não vale sem evento de portão
    assert res["etapa_atual"] == "04_busca"
    # sem PRESS registrado a próxima ação é o PRESS humano, não o G3
    assert res["proxima_acao"]["tipo"] == "tarefa" and "PRESS" in res["proxima_acao"]["descricao"]
    assert any(i["tipo"] == "portao_sem_evento" for i in res["inconsistencias"])
    press_registrado(projeto_vazio)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert res["proxima_acao"]["tipo"] == "portao" and "portao G3" in res["proxima_acao"]["comando"]
    # nunca valores inventados: placeholders explícitos que não são JSON válido
    assert "<valor de 01-busca/recall_ancoras.json>" in res["proxima_acao"]["comando"]
    assert "<press: true só com revisão humana registrada>" in res["proxima_acao"]["comando"]
    assert "0.0" not in res["proxima_acao"]["comando"]


def test_status_detecta_artefato_congelado_alterado_e_emenda_resolve(projeto_vazio, capsys):
    from rslib import estado
    protocolo = projeto_vazio / "00-protocolo" / "protocolo.md"
    protocolo_completo(projeto_vazio, "# Protocolo v1\n")
    assert rodar(capsys, "--dir", projeto_vazio, "portao", "G1", "--aprovar", "--por", "revisor_humano_1",
                 "--criterios", G1_OK)[0] == 0
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G2", "--aprovar", "--por", "revisor_humano_1")
    assert codigo == 0 and "00-protocolo/protocolo.md" in res["congelados"]
    congelados_g2 = sorted(res["congelados"])
    assert estado.carregar_estado(projeto_vazio)["versoes_ativas"]["protocolo"] == "v1"

    protocolo.write_text("# Protocolo v1 com critério novo\n", encoding="utf-8")
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    alterados = [i for i in res["inconsistencias"] if i["tipo"] == "artefato_congelado_alterado"]
    assert alterados and alterados[0]["gravidade"] == "erro"
    assert res["proxima_acao"]["tipo"] == "corrigir" and "emenda" in res["proxima_acao"]["comando"]

    codigo, res = rodar(capsys, "--dir", projeto_vazio, "emenda", "--arquivo", "00-protocolo/protocolo.md",
                        "--motivo", "inclui literatura cinzenta")
    assert codigo == 0 and res["mudou"] and res["versao"] == 2
    assert len(_eventos(projeto_vazio, "emenda_protocolo")) == 1
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert not [i for i in res["inconsistencias"] if i["tipo"].startswith("artefato_congelado")]

    # G2 reprovado descongela: editar o protocolo volta a ser rascunho, não emenda
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G2", "--reprovar", "--por", "revisor_humano_1",
                        "--motivo", "falta plano de síntese")
    assert codigo == 0 and sorted(res["descongelados"]) == congelados_g2
    protocolo.write_text("# Protocolo v2 com plano de síntese\n", encoding="utf-8")
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert not [i for i in res["inconsistencias"] if i["tipo"].startswith("artefato_congelado")]
    assert res["etapas"]["03_protocolo"]["status"] == "em_andamento"
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G2", "--aprovar", "--por", "revisor_humano_1")
    assert codigo == 0 and sorted(res["congelados"]) == congelados_g2
    info = estado.carregar_estado(projeto_vazio)["artefatos"]["00-protocolo/protocolo.md"]
    assert info["congelado_em"] and info["sha256"] == estado.sha256_arquivo(protocolo)


def test_status_contagens_que_nao_fecham(projeto_vazio, capsys):
    montar_ledger(projeto_vazio, elegibilidade=[e for e in ELEGIBILIDADE if e[0] != "RS0006"])
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    quebradas = [i for i in res["inconsistencias"] if i["tipo"] == "contagens_nao_fecham"]
    assert codigo == 0 and quebradas and quebradas[0]["invariante"] == "recuperacao_fecha"
    assert quebradas[0]["gravidade"] == "aviso"  # G5 ainda não aprovado


def test_status_estado_atras_do_log(projeto_vazio, capsys):
    from rslib import estado
    est = estado.carregar_estado(projeto_vazio)
    est["ultimo_seq"] = 0
    estado.salvar_estado(projeto_vazio, est)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert any(i["tipo"] == "estado_atras_do_log" for i in res["inconsistencias"])


# ---------------------------------------------------------------------------
# portao
# ---------------------------------------------------------------------------
def test_portao_checkpoints_exige_humano(projeto_vazio, capsys):
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G3", "--aprovar", "--por", "autopiloto")
    assert codigo == 2 and res["erro"] == "checagem_metodologica"


def test_portao_autopiloto_g2_humano_e_g3_abre_pendencia(projeto_vazio, capsys):
    from rslib import estado
    est = estado.carregar_estado(projeto_vazio)
    est["modo"]["autonomia"] = "autopiloto"
    estado.salvar_estado(projeto_vazio, est)
    codigo, _ = rodar(capsys, "--dir", projeto_vazio, "portao", "G2", "--aprovar", "--por", "autopiloto")
    assert codigo == 2
    assert not _eventos(projeto_vazio, "portao")

    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G3", "--aprovar", "--por", "autopiloto")
    assert codigo == 2 and res["bloqueios"][0]["tipo"] == "artefato"  # sem busca nenhuma

    montar_ledger(projeto_vazio, ate="registros")
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G3", "--aprovar", "--por", "autopiloto",
                        "--criterios", '{"recall_ancoras": 0.92}')
    assert codigo == 2 and [b["tipo"] for b in res["bloqueios"]] == ["artefato"] and "PRESS" in res["bloqueios"][0]["detalhe"]
    press_registrado(projeto_vazio)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G3", "--aprovar", "--por", "autopiloto",
                        "--criterios", '{"recall_ancoras": 0.92}')
    assert codigo == 0 and res["pendencia_aberta"]
    est = estado.carregar_estado(projeto_vazio)
    abertas = estado.pendencias_abertas(est)
    assert len(abertas) == 1 and abertas[0]["portao"] == "G3" and abertas[0]["tipo"] == "revisao_humana_portao"
    ev = _eventos(projeto_vazio, "portao")[-1]
    assert ev["ator"]["tipo"] == "ia_coordenador" and ev["dados"]["criterios"]["recall_ancoras"] == 0.92

    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G3", "--aprovar", "--por", "autopiloto",
                        "--criterios", '{"recall_ancoras": 0.92}')
    assert codigo == 0 and len(estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))) == 1


def test_portao_g4_bloqueia_sem_triagem_e_forcar_fica_no_log(projeto_vazio, capsys):
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G4", "--aprovar", "--por", "revisor_humano_1")
    assert codigo == 2 and {b["tipo"] for b in res["bloqueios"]} >= {"artefato", "validacao"}
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G4", "--aprovar", "--por", "revisor_humano_1",
                        "--forcar")
    assert codigo == 1  # --forcar sem motivo
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G4", "--aprovar", "--por", "revisor_humano_1",
                        "--forcar", "--motivo", "triagem feita fora da skill; validação no anexo")
    assert codigo == 0 and res["forcado"] is True
    ev = _eventos(projeto_vazio, "portao")[-1]
    assert ev["dados"]["criterios"]["checagens_script"]["forcado"] is True and ev["motivo"]


def test_portao_g4_limiar_nao_atingido_bloqueia(projeto_vazio, capsys):
    from rslib import estado
    montar_ledger(projeto_vazio, ate="triagem")
    estado.registrar_evento(projeto_vazio, "validacao_calculada", "06_triagem_ta", "script", "validacao",
                            dados={"metricas": {"recall": 0.81, "atende_limiares": False}})
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G4", "--aprovar", "--por", "revisor_humano_1")
    assert codigo == 2 and any(b["tipo"] == "limiar" for b in res["bloqueios"])
    # estabilidade (sem atende_limiares) e validação do texto completo não liberam o G4
    estado.registrar_evento(projeto_vazio, "validacao_calculada", "06_triagem_ta", "script", "validacao",
                            dados={"tipo": "estabilidade", "rodada": "ta_v1"})
    estado.registrar_evento(projeto_vazio, "validacao_calculada", "07_textos_elegibilidade", "script", "validacao",
                            dados={"atende_limiares": True})
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G4", "--aprovar", "--por", "revisor_humano_1")
    assert codigo == 2 and any(b["tipo"] == "limiar" for b in res["bloqueios"])
    # nem o autopiloto passa por cima de limiar não atingido
    est = estado.carregar_estado(projeto_vazio)
    est["modo"]["autonomia"] = "autopiloto"
    estado.salvar_estado(projeto_vazio, est)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G4", "--aprovar", "--por", "autopiloto")
    assert codigo == 2 and [b["tipo"] for b in res["bloqueios"]] == ["limiar"]


def test_proxima_acao_da_triagem_passo_a_passo(projeto_vazio):
    from rslib import esquema, estado, projeto
    raiz = projeto_vazio

    def acao():
        est = estado.carregar_estado(raiz)
        return projeto._acao_etapa(raiz, est, "06_triagem_ta", estado.ler_log(raiz))

    assert "critérios" in acao()["descricao"]
    (raiz / "02-triagem/prompts/ta_v1.md").write_text("critérios v1", encoding="utf-8")
    (raiz / "02-triagem/prompts/ta_v2.md").write_text("critérios v2", encoding="utf-8")
    assert acao()["comando"] == ("$RS triagem preparar --etapa ta --rodada ta_v2 --revisor A "
                                 "--criterios 02-triagem/prompts/ta_v2.md")
    (raiz / esquema.ARQ_DECISOES).write_text(json.dumps({"id_rs": "RS0001", "etapa": "ta", "rodada": "ta_v2"}) + "\n",
                                             encoding="utf-8")
    assert acao()["comando"] == "$RS triagem consolidar --rodada ta_v2"
    montar_ledger(raiz, ate="triagem")
    assert acao()["comando"].startswith("$RS validar amostrar --etapa ta --rodada ta_v2")
    estado.registrar_evento(raiz, "validacao_calculada", "06_triagem_ta", "script", "validacao",
                            dados={"atende_limiares": False})
    assert "falsos negativos" in acao()["descricao"]
    estado.registrar_evento(raiz, "validacao_calculada", "06_triagem_ta", "script", "validacao",
                            dados={"atende_limiares": True})
    assert acao()["tipo"] == "portao" and acao()["portao"] == "G4" and acao()["exige_humano"] is True


def test_autopiloto_pendencia_nao_bloqueia_proxima_acao(projeto_vazio, capsys):
    from rslib import estado
    est = estado.carregar_estado(projeto_vazio)
    est["modo"]["autonomia"] = "autopiloto"
    est["ambiente"] = {"resumo": {"python_ok": True}}
    estado.salvar_estado(projeto_vazio, est)
    estado.abrir_pendencia(projeto_vazio, "revisao_humana_portao", "01_pergunta", "confirmar")
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert res["proxima_acao"]["tipo"] != "pendencia" and res["rascunho"] is True


def test_portao_reprovar_exige_motivo_e_volta_etapa(projeto_vazio, capsys):
    from rslib import estado
    codigo, _ = rodar(capsys, "--dir", projeto_vazio, "portao", "G1", "--reprovar", "--por", "revisor_humano_1")
    assert codigo == 1
    assert rodar(capsys, "--dir", projeto_vazio, "portao", "G1", "--aprovar", "--por", "revisor_humano_1",
                 "--criterios", G1_OK)[0] == 0
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G1", "--reprovar", "--por", "revisor_humano_1",
                        "--motivo", "pergunta ampla demais")
    assert codigo == 0 and res["decisao"] == "reprovado"
    assert estado.carregar_estado(projeto_vazio)["etapas"]["01_pergunta"]["status"] == "em_andamento"
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert res["etapas"]["01_pergunta"]["status"] == "em_andamento" and res["etapas"]["01_pergunta"]["reprovado"]


def test_portao_ja_aprovado_nao_duplica(projeto_vazio, capsys):
    assert rodar(capsys, "--dir", projeto_vazio, "portao", "G1", "--aprovar", "--por", "revisor_humano_1",
                 "--criterios", G1_OK)[0] == 0
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G1", "--aprovar", "--por", "revisor_humano_1")
    assert codigo == 0 and res["ja_aprovado"] is True
    assert len(_eventos(projeto_vazio, "portao")) == 1


def test_portao_criterios_invalidos(projeto_vazio, capsys):
    codigo, _ = rodar(capsys, "--dir", projeto_vazio, "portao", "G1", "--aprovar", "--por", "r1", "--criterios", "{nao json")
    assert codigo == 1
    codigo, _ = rodar(capsys, "--dir", projeto_vazio, "portao", "G1", "--aprovar", "--por", "r1",
                      "--criterios", '{"tipo_revisao": "narrativa"}')
    assert codigo == 1


# ---------------------------------------------------------------------------
# pendencia
# ---------------------------------------------------------------------------
def test_pendencia_abrir_listar_fechar(projeto_vazio, capsys):
    argv = ["--dir", projeto_vazio, "pendencia", "abrir", "--tipo", "validacao_humana", "--etapa", "06_triagem_ta",
            "--descricao", "codificar amostra de 100", "--portao", "g4", "--n", "100"]
    codigo, res = rodar(capsys, *argv)
    assert codigo == 0 and res["pendencia"] == "P001" and not res["ja_existia"]
    codigo, res = rodar(capsys, *argv)
    assert res["pendencia"] == "P001" and res["ja_existia"]

    codigo, res = rodar(capsys, "--dir", projeto_vazio, "pendencia", "listar")
    assert res["n"] == 1 and res["pendencias"][0]["portao"] == "G4"

    codigo, res = rodar(capsys, "--dir", projeto_vazio, "pendencia", "fechar", "P001", "--motivo", "ok",
                        "--ator-tipo", "ia_coordenador")
    assert codigo == 2
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "pendencia", "fechar", "P001", "--motivo", "amostra codificada")
    assert codigo == 0 and res["fechada"] and res["abertas_restantes"] == 0
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "pendencia", "fechar", "P001", "--motivo", "de novo")
    assert codigo == 0 and res["ja_estava_fechada"]
    assert len(_eventos(projeto_vazio, "pendencia_fechada")) == 1
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "pendencia", "fechar", "P999", "--motivo", "x")
    assert codigo == 1
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "pendencia", "listar", "--todas")
    assert res["n"] == 1 and res["abertas"] == 0


def test_pendencia_fechar_sugere_regenerar_prisma(projeto_vazio, capsys):
    from rslib import estado
    montar_ledger(projeto_vazio)
    pid = estado.abrir_pendencia(projeto_vazio, "validacao_humana", "06_triagem_ta", "codificar")
    assert rodar(capsys, "--dir", projeto_vazio, "prisma")[0] == 0
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "pendencia", "fechar", pid, "--motivo", "feito")
    assert "$RS prisma" in res["regenerar"]


def test_comandos_exigem_projeto(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    codigo, res = rodar(capsys, "pendencia", "listar")
    assert codigo == 1 and res["erro"] == "uso"


# ---------------------------------------------------------------------------
# ambiente
# ---------------------------------------------------------------------------
def test_ambiente_chaves_so_booleanos(projeto_vazio, capsys, monkeypatch):
    segredo = "valor-secreto-de-teste-123"
    monkeypatch.setenv("ANTHROPIC_API_KEY", segredo)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "ambiente", "--sem-r")
    assert codigo in (0, 3) and res["gravado_no_projeto"] is True
    assert res["chaves_api"]["ANTHROPIC_API_KEY"] is True and res["chaves_api"]["OPENAI_API_KEY"] is False
    texto_estado = (projeto_vazio / "rs_estado.json").read_text(encoding="utf-8")
    texto_log = (projeto_vazio / "rs_log.jsonl").read_text(encoding="utf-8")
    assert segredo not in texto_estado and segredo not in texto_log
    assert len(_eventos(projeto_vazio, "ambiente_verificado")) == 1
    diag = json.loads(texto_estado)["ambiente"]
    assert set(diag["python"]["pacotes_obrigatorios"]) == {"pandas", "openpyxl", "xlrd", "requests", "pymupdf"}
    assert diag["r"]["pulado"] is True


def test_ambiente_irmas_por_claude_skill_dir(tmp_path, monkeypatch):
    from rslib import ambiente
    skills = tmp_path / "skills"
    (skills / "revisao-sistematica").mkdir(parents=True)
    (skills / "gerar-bibtex").mkdir()
    (skills / "gerar-bibtex" / "SKILL.md").write_text("---\nname: gerar-bibtex\n---\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_SKILL_DIR", str(skills / "revisao-sistematica"))
    monkeypatch.setenv("HOME", str(tmp_path / "casa_vazia"))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    irmas = ambiente.verificar_irmas()
    assert irmas["gerar-bibtex"]["instalada"] and irmas["gerar-bibtex"]["local"] == "skill_dir_vizinha"
    assert not irmas["fichamento-sistematico"]["instalada"] and irmas["fichamento-sistematico"]["fallback"]


def test_ambiente_r_real_ou_ausente():
    from rslib import ambiente
    r = ambiente.verificar_r(timeout=90)
    assert "disponivel" in r
    if r["disponivel"]:
        assert set(r["faltando"]) <= set(ambiente.PACOTES_R)


# ---------------------------------------------------------------------------
# Correções v1.1: checagens de artefato nos portões, status, etapas não aplicáveis, init
# ---------------------------------------------------------------------------
def _portao(capsys, raiz, g, *extra, por="revisor_humano_1"):
    return rodar(capsys, "--dir", raiz, "portao", g, "--aprovar", "--por", por, *extra)


def _autopiloto(raiz):
    from rslib import estado
    est = estado.carregar_estado(raiz)
    est["modo"]["autonomia"] = "autopiloto"
    estado.salvar_estado(raiz, est)


def test_g1_exige_pergunta_e_tipo_definido(projeto_vazio, capsys):
    from rslib import estado
    codigo, res = _portao(capsys, projeto_vazio, "G1")
    assert codigo == 2 and [b["tipo"] for b in res["bloqueios"]] == ["artefato", "artefato"]
    codigo, res = _portao(capsys, projeto_vazio, "G1", "--criterios", '{"pergunta": "X reduz Y?"}')
    assert codigo == 2 and "tipo_revisao indefinido" in res["bloqueios"][0]["detalhe"]
    assert not _eventos(projeto_vazio, "portao")
    codigo, res = _portao(capsys, projeto_vazio, "G1", "--criterios",
                          '{"pergunta": "X reduz Y?", "tipo_revisao": "escopo", "variante": "rapida"}')
    assert codigo == 0
    projeto = estado.carregar_estado(projeto_vazio)["projeto"]
    assert (projeto["pergunta"], projeto["tipo_revisao"], projeto["variante"]) == ("X reduz Y?", "escopo", "rapida")
    codigo, _ = rodar(capsys, "--dir", projeto_vazio, "portao", "G1", "--aprovar", "--por", "r1",
                      "--criterios", '{"pergunta": "X", "tipo_revisao": "escopo", "variante": "lenta"}')
    assert codigo == 1


def test_g1_forcar_exige_motivo_e_registra(projeto_vazio, capsys):
    codigo, _ = _portao(capsys, projeto_vazio, "G1", "--forcar")
    assert codigo == 1
    codigo, res = _portao(capsys, projeto_vazio, "G1", "--forcar", "--motivo", "pergunta registrada no OSF")
    assert codigo == 0 and res["forcado"] is True
    ev = _eventos(projeto_vazio, "portao")[-1]
    assert ev["motivo"] == "pergunta registrada no OSF" and ev["dados"]["criterios"]["checagens_script"]["bloqueios"]


def test_g2_exige_protocolo_e_avisa_sem_revisor_metodologico(projeto_vazio, capsys):
    codigo, res = _portao(capsys, projeto_vazio, "G2")
    assert codigo == 2 and res["bloqueios"][0]["tipo"] == "artefato" and "protocolo" in res["bloqueios"][0]["detalhe"]
    protocolo_completo(projeto_vazio)
    codigo, res = _portao(capsys, projeto_vazio, "G2")
    assert codigo == 0 and any("revisor metodológico" in a for a in res["avisos"])
    assert _eventos(projeto_vazio, "portao")[-1]["dados"]["criterios"]["checagens_script"]["avisos"]
    rodar(capsys, "--dir", projeto_vazio, "portao", "G2", "--reprovar", "--por", "revisor_humano_1", "--motivo", "rever")
    (projeto_vazio / "00-protocolo" / "revisao_metodologica_v1.md").write_text("parecer\n", encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G2")
    assert codigo == 0 and res["avisos"] == []


def test_g3_congela_strings_e_filtros(projeto_vazio, capsys):
    from rslib import estado
    montar_ledger(projeto_vazio, ate="registros")
    strings = projeto_vazio / "01-busca" / "strings"
    (strings / "scopus").mkdir(parents=True)
    (strings / "B01_wos.txt").write_text('TS=("cash transfer*")\n', encoding="utf-8")
    (strings / "scopus" / "B02.txt").write_text('TITLE-ABS-KEY("cash transfer*")\n', encoding="utf-8")
    (projeto_vazio / "01-busca" / "filtros_v1.json").write_text('{"versao": "filtros_v1", "filtros": []}', encoding="utf-8")
    (projeto_vazio / "01-busca" / "log_buscas.csv").write_text("busca_id\nB01\n", encoding="utf-8")
    press_registrado(projeto_vazio)
    codigo, res = _portao(capsys, projeto_vazio, "G3")
    assert codigo == 0
    assert set(res["congelados"]) == {"01-busca/strings/B01_wos.txt", "01-busca/strings/scopus/B02.txt",
                                      "01-busca/filtros_v1.json"}
    (strings / "B01_wos.txt").write_text('TS=("cash transfer*" OR "bolsa")\n', encoding="utf-8")
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    alterados = [i for i in res["inconsistencias"] if i["tipo"] == "artefato_congelado_alterado"]
    assert [i["caminho"] for i in alterados] == ["01-busca/strings/B01_wos.txt"]
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "emenda", "--arquivo", "01-busca/strings/B01_wos.txt",
                        "--motivo", "PRESS pediu sinônimo")
    assert codigo == 0 and res["versao"] == 2
    assert _eventos(projeto_vazio, "emenda_protocolo")[-1]["etapa"] == "04_busca"
    assert estado.carregar_estado(projeto_vazio)["artefatos"]["01-busca/filtros_v1.json"]["portao"] == "G3"


def _projeto_triado(raiz, rodada_ativa):
    from rslib import estado
    raiz.mkdir(parents=True, exist_ok=True)
    estado.salvar_estado(raiz, estado.estado_inicial("P"))
    montar_ledger(raiz, ate="triagem")
    est = estado.carregar_estado(raiz)
    est["versoes_ativas"]["rodada_ta"] = rodada_ativa
    estado.salvar_estado(raiz, est)
    return raiz


def _validacao(raiz, atende, **dados):
    from rslib import estado
    estado.registrar_evento(raiz, "validacao_calculada", "06_triagem_ta", "script", "validacao",
                            dados={"atende_limiares": atende, **dados})


def test_g4_usa_validacao_final_da_rodada_ativa(tmp_path, capsys):
    raiz = _projeto_triado(tmp_path / "a", "ta_v2")
    _validacao(raiz, True, finalidade="validacao", rodada="ta_v2")
    _validacao(raiz, False, finalidade="calibracao", rodada="ta_v2")       # calibração posterior não decide
    _validacao(raiz, False, finalidade="validacao", rodada="ta_v1")        # rodada antiga não decide
    _validacao(raiz, False, finalidade="desenvolvimento", rodada="ta_v2")
    codigo, res = _portao(capsys, raiz, "G4")
    assert codigo == 0, res
    assert any("ignoradas" in a for a in res["avisos"])

    raiz = _projeto_triado(tmp_path / "b", "ta_v2")
    _validacao(raiz, False, finalidade="validacao", rodada="ta_v2")
    _validacao(raiz, True, finalidade="desenvolvimento", rodada="ta_v2")   # desenvolvimento posterior não libera
    _validacao(raiz, True, finalidade="validacao", rodada="ta_v2_estab")   # nem reexecução de estabilidade
    codigo, res = _portao(capsys, raiz, "G4")
    assert codigo == 2 and [b["tipo"] for b in res["bloqueios"]] == ["limiar"]

    raiz = _projeto_triado(tmp_path / "c", "ta_v1+ta_v2")                  # consolidação juntou rodadas
    _validacao(raiz, True, finalidade="validacao", rodada="ta_v1")
    assert _portao(capsys, raiz, "G4")[0] == 0


def test_g4_validacao_sem_finalidade_vale_com_aviso(projeto_vazio, capsys):
    from rslib import estado
    montar_ledger(projeto_vazio, ate="triagem")
    estado.registrar_evento(projeto_vazio, "validacao_calculada", "06_triagem_ta", "script", "validacao",
                            dados={"atende_limiares": True, "rodada": "ta_v1"})
    codigo, res = _portao(capsys, projeto_vazio, "G4")
    assert codigo == 0 and any("sem `finalidade`" in a for a in res["avisos"])


def test_g4_sem_validacao_da_rodada_ativa_bloqueia(projeto_vazio, capsys):
    from rslib import estado
    montar_ledger(projeto_vazio, ate="triagem")
    est = estado.carregar_estado(projeto_vazio)
    est["versoes_ativas"]["rodada_ta"] = "ta_v3"
    estado.salvar_estado(projeto_vazio, est)
    estado.registrar_evento(projeto_vazio, "validacao_calculada", "06_triagem_ta", "script", "validacao",
                            dados={"atende_limiares": True, "rodada": "ta_v2", "finalidade": "validacao"})
    codigo, res = _portao(capsys, projeto_vazio, "G4")
    assert codigo == 2 and res["bloqueios"][0]["tipo"] == "validacao" and "ta_v3" in res["bloqueios"][0]["detalhe"]


def test_g6_exige_piloto_consolidado(projeto_vazio, capsys):
    from rslib import estado
    codigo, res = _portao(capsys, projeto_vazio, "G6")
    assert codigo == 2 and "piloto" in res["bloqueios"][0]["detalhe"]
    (projeto_vazio / "05-decomposicao" / "efeitos" / "Silva2020.csv").write_text("id_efeito\nE1\n", encoding="utf-8")
    assert _portao(capsys, projeto_vazio, "G6")[0] == 2  # CSV solto do extrator não é piloto consolidado
    piloto = projeto_vazio / "05-decomposicao" / "piloto"
    piloto.mkdir()
    (piloto / "fichamentos_master.csv").write_text("ficha_id,citekey\nF1,Silva2020\n", encoding="utf-8")
    assert _portao(capsys, projeto_vazio, "G6")[0] == 0

    # alternativa: evento extracao_consolidada
    outro = projeto_vazio / "b"
    (outro / "05-decomposicao").mkdir(parents=True)
    estado.salvar_estado(outro, estado.estado_inicial("P2"))
    estado.registrar_evento(outro, "extracao_consolidada", "09_extracao_rob", "script", "teste", dados={"n_efeitos": 1})
    assert _portao(capsys, outro, "G6")[0] == 0


def _efeitos_verificados(raiz, linhas_verificacao):
    from rslib import esquema, estado
    import csv as _csv
    (raiz / esquema.ARQ_EFEITOS_EXTRAIDOS).write_text("id_efeito,chave\nE1,Silva2020\nE2,Souza2019\n", encoding="utf-8")
    colunas = ["id_efeito", "chave", "pagina", "status_trecho", "pagina_encontrada", "verificador", "erros", "alertas",
               "g_aproximado", "p_calculado", "verificado_humano", "apto_g7"]
    with open(raiz / esquema.ARQ_VERIFICACAO_EFEITOS, "w", encoding="utf-8", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=colunas)
        w.writeheader()
        for linha in linhas_verificacao:
            w.writerow({c: linha.get(c, "") for c in colunas})
    estado.registrar_evento(raiz, "efeitos_verificados", "09_extracao_rob", "script", "teste",
                            dados={"n_efeitos": len(linhas_verificacao)},
                            artefatos=[esquema.ARQ_EFEITOS_EXTRAIDOS, esquema.ARQ_VERIFICACAO_EFEITOS])


def test_g7_bloqueia_efeitos_nao_verificados(projeto_vazio, capsys):
    from rslib import esquema
    rob_consolidado(projeto_vazio)
    assert _portao(capsys, projeto_vazio, "G7")[0] == 0  # sem efeitos_extraidos (ex.: revisão só qualitativa)

    raiz = projeto_vazio / "p7"
    for pasta in ("05-decomposicao",):
        (raiz / pasta).mkdir(parents=True)
    from rslib import estado
    estado.salvar_estado(raiz, estado.estado_inicial("P7"))
    rob_consolidado(raiz)
    (raiz / esquema.ARQ_EFEITOS_EXTRAIDOS).write_text("id_efeito,chave\nE1,Silva2020\n", encoding="utf-8")
    codigo, res = _portao(capsys, raiz, "G7")
    assert codigo == 2 and "não foram verificados" in res["bloqueios"][0]["detalhe"]

    _efeitos_verificados(raiz, [{"id_efeito": "E1", "status_trecho": "OK", "verificado_humano": "1", "apto_g7": "1"},
                                {"id_efeito": "E2", "status_trecho": "OK", "verificado_humano": "0", "apto_g7": "0"}])
    codigo, res = _portao(capsys, raiz, "G7")
    assert codigo == 2 and [b["tipo"] for b in res["bloqueios"]] == ["verificacao"] and res["bloqueios"][0]["n"] == 1
    from rslib import projeto
    acao = projeto._acao_etapa(raiz, estado.carregar_estado(raiz), "09_extracao_rob", estado.ler_log(raiz))
    assert acao["tipo"] == "tarefa" and "verificado_humano" in acao["descricao"] and acao["exige_humano"]
    _autopiloto(raiz)
    codigo, res = _portao(capsys, raiz, "G7", por="autopiloto")  # autopiloto: vira pendência, não barra
    assert codigo == 0 and res["pendencia_aberta"]


def test_g7_trecho_reprovado_ou_efeitos_alterados_barram_ate_o_autopiloto(projeto_vazio, capsys):
    from rslib import esquema
    _autopiloto(projeto_vazio)
    rob_consolidado(projeto_vazio)
    _efeitos_verificados(projeto_vazio, [
        {"id_efeito": "E1", "status_trecho": "NAO_ENCONTRADA", "verificado_humano": "0", "apto_g7": "0"},
        {"id_efeito": "E2", "status_trecho": "OK", "erros": "", "verificado_humano": "1", "apto_g7": "1"}])
    codigo, res = _portao(capsys, projeto_vazio, "G7", por="autopiloto")
    assert codigo == 2 and [b["tipo"] for b in res["bloqueios"]] == ["artefato"]
    _efeitos_verificados(projeto_vazio, [
        {"id_efeito": "E1", "status_trecho": "OK", "verificado_humano": "1", "apto_g7": "1"},
        {"id_efeito": "E2", "status_trecho": "OK", "verificado_humano": "1", "apto_g7": "1"}])
    (projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS).write_text("id_efeito,chave\nE1,Silva2020\nE2,Outro2000\n",
                                                               encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G7", por="autopiloto")
    assert codigo == 2 and "mudou depois da última verificação" in res["bloqueios"][0]["detalhe"]
    from rslib import estado, projeto
    acao = projeto._acao_etapa(projeto_vazio, estado.carregar_estado(projeto_vazio), "09_extracao_rob",
                               estado.ler_log(projeto_vazio))
    assert acao["comando"] == "$RS analise verificar-efeitos"
    _efeitos_verificados(projeto_vazio, [
        {"id_efeito": "E1", "status_trecho": "OK", "verificado_humano": "1", "apto_g7": "1"},
        {"id_efeito": "E2", "status_trecho": "OK", "verificado_humano": "1", "apto_g7": "1"}])
    assert _portao(capsys, projeto_vazio, "G7", por="autopiloto")[0] == 0


def test_g8_bloqueia_caixa_com_rotulo_pendente(projeto_vazio, capsys):
    from rslib import esquema
    caixa = projeto_vazio / esquema.ARQ_CAIXA
    caixa.write_text("celula_id,dimensao,rotulo,status_rotulo\nC1,efeito,Positivo,definido\nC2,efeito,Pendente,pendente\n",
                     encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G8")
    assert codigo == 2 and res["bloqueios"][0]["tipo"] == "certeza" and "C2" in res["bloqueios"][0]["detalhe"]
    caixa.write_text("celula_id,dimensao,rotulo,status_rotulo\nC1,efeito,Positivo,definido\nC2,efeito,Nulo,definido\n",
                     encoding="utf-8")
    (projeto_vazio / esquema.ARQ_CERTEZA).write_text("familia_intervencao,construto_outcome,dimensao,certeza\n"
                                                    ",,efeito,moderada\n", encoding="utf-8")
    (projeto_vazio / esquema.ARQ_META_RESUMO).write_text(json.dumps({"grupos": [
        {"construto_outcome": "frequencia", "status": "meta_ajustada"},
        {"construto_outcome": "notas", "status": "dependencia_nao_resolvida"}]}), encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G8")
    assert codigo == 0 and any("notas (dependencia_nao_resolvida)" in a for a in res["avisos"])


def test_g9_exige_prisma_atual_e_declaracao(projeto_vazio, capsys):
    from rslib import esquema, estado
    codigo, res = _portao(capsys, projeto_vazio, "G9")
    detalhes = " ".join(b["detalhe"] for b in res["bloqueios"])
    assert codigo == 2 and "PRISMA não gerado" in detalhes and "declaracao_uso_ia.md" in detalhes
    montar_ledger(projeto_vazio)
    assert rodar(capsys, "--dir", projeto_vazio, "prisma")[0] == 0
    (projeto_vazio / esquema.ARQ_DECLARACAO_IA).write_text("# Declaração\n", encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G9")
    assert codigo == 0, res

    rodar(capsys, "--dir", projeto_vazio, "portao", "G9", "--reprovar", "--por", "revisor_humano_1", "--motivo", "dados")
    montar_ledger(projeto_vazio, elegibilidade=[("RS0001", "Silva2020", "incluir", ""), ("RS0002", "Souza2019", "excluir", "população"),
                                                ("RS0006", "Costa2018", "incluir", ""), ("RS0008", "Rocha2022", "incluir", "")])
    codigo, res = _portao(capsys, projeto_vazio, "G9")
    assert codigo == 2 and "os dados mudaram depois do último PRISMA" in res["bloqueios"][0]["detalhe"]
    assert esquema.ARQ_ELEGIBILIDADE_TC_FINAL in res["bloqueios"][0]["detalhe"]
    from rslib import projeto
    acao = projeto._acao_etapa(projeto_vazio, estado.carregar_estado(projeto_vazio), "11_relato",
                               estado.ler_log(projeto_vazio))
    assert acao["comando"] == "$RS prisma"
    assert rodar(capsys, "--dir", projeto_vazio, "prisma")[0] == 0
    assert _portao(capsys, projeto_vazio, "G9")[0] == 0

    rodar(capsys, "--dir", projeto_vazio, "portao", "G9", "--reprovar", "--por", "revisor_humano_1", "--motivo", "x")
    estado.abrir_pendencia(projeto_vazio, "validacao_humana", "06_triagem_ta", "codificar amostra", portao="G4")
    codigo, res = _portao(capsys, projeto_vazio, "G9")
    assert codigo == 2 and "pendências abertas mudaram" in res["bloqueios"][0]["detalhe"]


def test_status_rascunho_por_caixa_pendente(projeto_vazio, capsys):
    from rslib import estado
    assert rodar(capsys, "--dir", projeto_vazio, "status")[1]["rascunho"] is False
    estado.registrar_evento(projeto_vazio, "caixa_gerada", "10_sintese", "script", "caixa",
                            dados={"n_linhas": 4, "n_pendentes": 2, "rascunho": True})
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert res["rascunho"] is True and "2 células pendentes" in res["motivos_rascunho"][0]
    estado.registrar_evento(projeto_vazio, "caixa_gerada", "10_sintese", "script", "caixa",
                            dados={"n_linhas": 4, "n_pendentes": 0, "rascunho": False})
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert res["rascunho"] is False and res["motivos_rascunho"] == []


def test_alertas_de_busca_antiga_sem_data_e_inativa():
    import datetime as dt
    from rslib import projeto
    est = {"buscas": [
        {"id": "B01", "fonte": "wos", "executada_em": "2025-09-14"},
        {"id": "B02", "fonte": "scopus", "executada_em": "2025-09-15T10:00:00Z"},
        {"id": "B03", "fonte": "openalex", "executada_em": "2020-01-01", "ativa": False},
        {"id": "B04", "fonte": "scielo", "executada_em": None},
        {"id": "B05", "fonte": "capes", "executada_em": "14/03/2024"},
    ]}
    alertas = projeto.alertas_buscas(est, hoje=dt.date(2026, 9, 15))
    assert {(a["tipo"], a["busca"]) for a in alertas} == {
        ("busca_desatualizada", "B01"), ("busca_sem_data", "B04"), ("busca_desatualizada", "B05")}
    assert projeto._somar_meses(dt.date(2024, 2, 29), 12) == dt.date(2025, 2, 28)


def test_status_ignora_busca_inativa_e_mostra_alertas(projeto_vazio, capsys):
    from rslib import estado
    montar_ledger(projeto_vazio, ate="unicos",
                  registros=[r for r in __import__("test_prisma").REGISTROS] + [("B09-00001", "B09", "scopus", "base")])
    est = estado.carregar_estado(projeto_vazio)
    est["ambiente"] = {"resumo": {"python_ok": True}}
    est["buscas"] = [{"id": "B01", "fonte": "wos", "executada_em": "2019-01-01"},
                     {"id": "B09", "fonte": "scopus", "executada_em": "2019-01-01", "ativa": False}]
    estado.salvar_estado(projeto_vazio, est)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert res["etapas"]["05_organizacao"]["status"] == "concluida"  # B09 substituída não precisa de cluster
    assert not [i for i in res["inconsistencias"] if i["tipo"] == "contagens_nao_fecham"]
    assert [a["busca"] for a in res["alertas"]] == ["B01"]
    assert res["contagens"]["buscas_inativas"] == {"buscas": ["B09"], "n_registros": 1}
    assert "estado.buscas (1)" in res["etapas"]["04_busca"]["evidencias"]


def test_proxima_acao_usa_rodada_ativa_e_ignora_estabilidade(projeto_vazio):
    from rslib import esquema, estado, projeto
    raiz = projeto_vazio
    (raiz / "02-triagem/prompts/ta_v1.md").write_text("critérios v1", encoding="utf-8")
    linhas = [{"id_rs": "RS0001", "etapa": "ta", "rodada": "ta_v1"}, {"id_rs": "RS0001", "etapa": "ta", "rodada": "ta_v1_estab"},
              {"id_rs": "RS0001", "etapa": "ta", "rodada": "ta_v1_re"}]
    (raiz / esquema.ARQ_DECISOES).write_text("".join(json.dumps(l) + "\n" for l in linhas), encoding="utf-8")
    estado.registrar_evento(raiz, "validacao_calculada", "06_triagem_ta", "script", "validacao",
                            dados={"tipo": "estabilidade", "rodada": "ta_v1", "rodada_reexecucao": "ta_v1_re"})

    def acao():
        est = estado.carregar_estado(raiz)
        return projeto._acao_etapa(raiz, est, "06_triagem_ta", estado.ler_log(raiz))

    assert acao()["comando"] == "$RS triagem consolidar --rodada ta_v1"
    est = estado.carregar_estado(raiz)
    est["versoes_ativas"]["rodada_ta"] = "ta_v2"
    estado.salvar_estado(raiz, est)
    assert acao()["comando"] == "$RS triagem consolidar --rodada ta_v2"
    montar_ledger(raiz, ate="triagem")
    assert "--rodada ta_v2 " in acao()["comando"] and acao()["comando"].startswith("$RS validar amostrar")


def test_nao_se_aplica_por_tipo(projeto_vazio, capsys):
    from rslib import estado
    raiz = projeto_vazio
    base = ["--dir", raiz, "portao"]
    codigo, _ = rodar(capsys, *base, "G7", "--nao-se-aplica", "--por", "revisor_humano_1")
    assert codigo == 1  # sem motivo
    codigo, res = rodar(capsys, *base, "G7", "--nao-se-aplica", "--por", "revisor_humano_1", "--motivo", "escopo")
    assert codigo == 2 and "tipo indefinido" in res["detalhe"]  # tipo ainda não aprovado
    est = estado.carregar_estado(raiz)
    est["projeto"]["tipo_revisao"] = "escopo"
    est["ambiente"] = {"resumo": {"python_ok": True}}
    estado.salvar_estado(raiz, est)
    codigo, res = rodar(capsys, *base, "G7", "--nao-se-aplica", "--por", "revisor_humano_1", "--motivo", "escopo")
    assert codigo == 2 and "G1" in res["detalhe"]
    assert _portao(capsys, raiz, "G1", "--criterios", '{"pergunta": "O que se sabe sobre X?", "tipo_revisao": "escopo"}')[0] == 0
    codigo, res = rodar(capsys, *base, "G4", "--nao-se-aplica", "--por", "revisor_humano_1", "--motivo", "não quero")
    assert codigo == 2 and "G7, G8" in res["detalhe"]
    codigo, res = rodar(capsys, *base, "G7", "--nao-se-aplica", "--por", "autopiloto", "--motivo", "escopo sem RoB")
    assert codigo == 2  # checkpoints: só humano
    codigo, res = rodar(capsys, *base, "G7", "--nao-se-aplica", "--por", "revisor_humano_1",
                        "--motivo", "revisão de escopo: sem avaliação de risco de viés (JBI 10.2.7)")
    assert codigo == 0 and res["decisao"] == "nao_se_aplica"
    ev = _eventos(raiz, "etapa_nao_aplicavel")
    assert len(ev) == 1 and ev[0]["dados"]["portao"] == "G7" and ev[0]["etapa"] == "09_extracao_rob" and ev[0]["motivo"]
    codigo, res = rodar(capsys, *base, "G7", "--nao-se-aplica", "--por", "revisor_humano_1", "--motivo", "de novo")
    assert codigo == 0 and res["ja_registrado"] and len(_eventos(raiz, "etapa_nao_aplicavel")) == 1
    est = estado.carregar_estado(raiz)
    assert "09_extracao_rob" in est["projeto"]["etapas_ignoradas"] and est["etapas"]["09_extracao_rob"]["status"] == "ignorada"

    codigo, res = rodar(capsys, "--dir", raiz, "status")
    assert res["etapas"]["09_extracao_rob"]["status"] == "ignorada" and res["etapas"]["09_extracao_rob"]["fonte"] == "nao_se_aplica"
    assert not [i for i in res["inconsistencias"] if i["tipo"] == "portao_fora_de_ordem" and "G7" in i["detalhe"]]

    # aprovar depois devolve a etapa ao fluxo
    codigo, res = _portao(capsys, raiz, "G7")
    assert codigo == 0
    est = estado.carregar_estado(raiz)
    assert "09_extracao_rob" not in est["projeto"]["etapas_ignoradas"]
    assert rodar(capsys, "--dir", raiz, "status")[1]["etapas"]["09_extracao_rob"]["status"] == "concluida"
    codigo, res = rodar(capsys, *base, "G7", "--nao-se-aplica", "--por", "revisor_humano_1", "--motivo", "x")
    assert codigo == 1  # já aprovado: reprove antes


def test_nao_se_aplica_evento_valida_schema_e_status_sugere_alternativa(projeto_vazio, capsys):
    jsonschema = pytest.importorskip("jsonschema")
    from rslib import estado
    est = estado.carregar_estado(projeto_vazio)
    est["ambiente"] = {"resumo": {"python_ok": True}}
    estado.salvar_estado(projeto_vazio, est)
    assert _portao(capsys, projeto_vazio, "G1", "--criterios",
                   '{"pergunta": "Mapa de X", "tipo_revisao": "mapa_evidencias"}')[0] == 0
    _autopiloto(projeto_vazio)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "portao", "G6", "--nao-se-aplica", "--por", "autopiloto",
                        "--motivo", "mapa: sem piloto de extração de efeitos")
    assert codigo == 0 and res["pendencia_aberta"]  # autopiloto: confirmação humana pendente
    schema_evento = json.loads((SKILL / "assets/schemas/evento.schema.json").read_text(encoding="utf-8"))
    schema_estado = json.loads((SKILL / "assets/schemas/estado.schema.json").read_text(encoding="utf-8"))
    for ev in _eventos(projeto_vazio):
        jsonschema.validate(ev, schema_evento)
    jsonschema.validate(estado.carregar_estado(projeto_vazio), schema_estado)
    from rslib import projeto
    est = estado.carregar_estado(projeto_vazio)
    eventos = estado.ler_log(projeto_vazio)
    etapas, portoes = projeto.recalcular_etapas(projeto_vazio, est, eventos)
    for etapa in ("02_teoria_framework", "03_protocolo", "04_busca", "05_organizacao", "06_triagem_ta",
                  "07_textos_elegibilidade"):
        etapas[etapa]["status"] = "concluida"
    acao = projeto.proxima_acao(projeto_vazio, est, etapas, portoes, eventos, [])
    assert acao["etapa"] == "09_extracao_rob" and "--nao-se-aplica" in acao["alternativa"]


def test_init_variante_e_mudanca_de_modo_sem_titulo(tmp_path, capsys, sem_ambiente_lento):
    jsonschema = pytest.importorskip("jsonschema")
    from rslib import estado
    raiz = tmp_path / "rev"
    codigo, res = rodar(capsys, "--dir", raiz, "init", "--tipo", "efetividade_swim")
    assert codigo == 1 and "--titulo" in res["detalhe"] and not raiz.exists()
    codigo, res = rodar(capsys, "--dir", raiz, "init", "--titulo", "RR de X", "--tipo", "efetividade_swim",
                        "--variante", "rapida")
    assert codigo == 0 and res["variante"] == "rapida"
    est = estado.carregar_estado(raiz)
    assert est["projeto"]["variante"] == "rapida" and est["projeto"]["tipo_revisao"] == "efetividade_swim"
    assert _eventos(raiz, "projeto_criado")[0]["dados"]["variante"] == "rapida"
    schema_estado = json.loads((SKILL / "assets/schemas/estado.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(est, schema_estado)

    codigo, res = rodar(capsys, "--dir", raiz, "init", "--triagem", "api", "--autonomia", "autopiloto")
    assert codigo == 0 and set(res["mudancas"]) == {"triagem", "autonomia"}
    est = estado.carregar_estado(raiz)
    assert (est["modo"]["triagem"], est["modo"]["autonomia"]) == ("api", "autopiloto")
    assert _eventos(raiz, "modo_definido")[-1]["dados"]["mudancas"]["triagem"] == {"de": "subagentes", "para": "api"}


# ---------------------------------------------------------------------------
# Avisos do G3 (recall das âncoras) e do G9 (.bib e declaração atualizada)
# ---------------------------------------------------------------------------
def test_regressao_g3_avisa_sem_recall_e_recall_menor_que_1(projeto_vazio, capsys):
    from rslib import esquema, estado
    montar_ledger(projeto_vazio, ate="unicos")
    press_registrado(projeto_vazio)
    codigo, res = _portao(capsys, projeto_vazio, "G3")
    assert codigo == 0 and any("recall_ancoras.json não existe" in a for a in res["avisos"]), res
    rodar(capsys, "--dir", projeto_vazio, "portao", "G3", "--reprovar", "--por", "revisor_humano_1", "--motivo", "x")

    sha = estado.sha256_arquivo(projeto_vazio / esquema.ARQ_UNICOS)
    recall = {"combinado": {"n_ancoras": 4, "n_encontradas": 3, "recall": 0.75, "perdidas": ["A07"]},
              "unicos_sha256": sha}
    (projeto_vazio / esquema.ARQ_RECALL_ANCORAS).write_text(json.dumps(recall), encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G3")
    avisos = " ".join(res["avisos"])
    assert codigo == 0 and "recall combinado das âncoras = 0.75" in avisos and "A07" in avisos
    assert "não existe" not in avisos and "outra versão" not in avisos
    rodar(capsys, "--dir", projeto_vazio, "portao", "G3", "--reprovar", "--por", "revisor_humano_1", "--motivo", "x")

    recall["combinado"] = {"n_ancoras": 4, "n_encontradas": 4, "recall": 1.0, "perdidas": []}
    recall["unicos_sha256"] = "0" * 64
    (projeto_vazio / esquema.ARQ_RECALL_ANCORAS).write_text(json.dumps(recall), encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G3")
    assert codigo == 0 and not any("recall combinado" in a for a in res["avisos"])
    assert any("outra versão" in a for a in res["avisos"])
    ev = _eventos(projeto_vazio, "portao")[-1]
    assert any("outra versão" in a for a in ev["dados"]["criterios"]["checagens_script"]["avisos"])


def test_regressao_g9_avisa_sem_bib_e_declaracao_anterior_ao_log(projeto_vazio, capsys):
    import argparse
    from rslib import declaracao_ia, esquema, estado, projeto
    assert projeto.ATOR_DECLARACAO_IA == declaracao_ia.ATOR
    montar_ledger(projeto_vazio)

    def gerar_declaracao():
        parser = argparse.ArgumentParser()
        parser.add_argument("--dir")
        sub = parser.add_subparsers(dest="comando")
        declaracao_ia.registrar(sub)
        args = parser.parse_args(["--dir", str(projeto_vazio), "declaracao-ia"])
        assert args.func(args) == 0
        capsys.readouterr()

    assert rodar(capsys, "--dir", projeto_vazio, "prisma")[0] == 0
    gerar_declaracao()
    codigo, res = _portao(capsys, projeto_vazio, "G9")
    assert codigo == 0, res
    assert any("references.bib não existe" in a for a in res["avisos"])
    assert not any("declaracao_uso_ia.md" in a for a in res["avisos"]), res["avisos"]

    rodar(capsys, "--dir", projeto_vazio, "portao", "G9", "--reprovar", "--por", "revisor_humano_1", "--motivo", "x")
    (projeto_vazio / esquema.ARQ_BIB).write_text("@article{Silva2020,\n}\n", encoding="utf-8")
    estado.registrar_evento(projeto_vazio, "relatorio_gerado", "11_relato", "script", "rs.py handoff",
                            dados={"produto": "bib"}, artefatos=[esquema.ARQ_BIB])
    codigo, res = _portao(capsys, projeto_vazio, "G9")
    avisos = " ".join(res["avisos"])
    assert codigo == 0 and "references.bib" not in avisos
    assert "cobre o log até o seq" in avisos and "relatorio_gerado" in avisos

    rodar(capsys, "--dir", projeto_vazio, "portao", "G9", "--reprovar", "--por", "revisor_humano_1", "--motivo", "x")
    assert rodar(capsys, "--dir", projeto_vazio, "prisma")[0] == 0
    gerar_declaracao()  # por último: cobre todo o log (os próprios eventos da declaração não contam)
    codigo, res = _portao(capsys, projeto_vazio, "G9")
    assert codigo == 0 and not any("declaracao_uso_ia.md" in a for a in res["avisos"]), res["avisos"]

    rodar(capsys, "--dir", projeto_vazio, "portao", "G9", "--reprovar", "--por", "revisor_humano_1", "--motivo", "x")
    assert rodar(capsys, "--dir", projeto_vazio, "prisma")[0] == 0
    (projeto_vazio / esquema.ARQ_DECLARACAO_IA).write_text("# Declaração escrita à mão\n", encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G9")
    assert codigo == 0 and any("escrita à mão" in a for a in res["avisos"])


# ---------------------------------------------------------------------------
# Correções v1.2: projeto em subpasta, cabeçalhos, busca truncada, portões G2/G3/G4/G7/G8/G9, próxima ação
# ---------------------------------------------------------------------------
def test_regressao_status_na_pasta_mae_sugere_dir_e_init_recusa(tmp_path, capsys, sem_ambiente_lento):
    from rslib import esquema
    mae = tmp_path / "mae"
    filho = mae / "A_celulares"
    codigo, res = rodar(capsys, "--dir", filho, "init", "--titulo", "Celulares")
    assert codigo == 0 and res["proxima_acao"] == f'$RS --dir "{filho}" status'
    montar_ledger(filho, ate="unicos")
    (filho / "01-busca" / "log_buscas.csv").write_text("busca_id,base\nB01,wos\n", encoding="utf-8")
    (filho / "00-protocolo" / "exploracao_B01.csv").write_text("id,display_name,publication_year\nW1,T,2020\n",
                                                               encoding="utf-8")
    (mae / "exportacoes").mkdir()
    (mae / "exportacoes" / "savedrecs.txt").write_text("FN Clarivate Analytics Web of Science\nVR 1.0\n", encoding="utf-8")

    codigo, res = rodar(capsys, "--dir", mae, "status")
    assert codigo == 0 and res["projeto"] is None and res["projetos_em_subpastas"] == ["A_celulares"]
    assert res["proxima_acao"]["comando"] == f'$RS --dir "{(mae / "A_celulares").as_posix()}" status'
    caminhos = [a["caminho"] for a in res["artefatos_encontrados"]]
    assert caminhos == ["exportacoes/savedrecs.txt"]  # nada de dentro do projeto em subpasta
    assert "importar" not in json.dumps(res["proxima_acao"])

    for extra in ([], ["--adotar"]):
        codigo, res = rodar(capsys, "--dir", mae, "init", "--titulo", "Por cima", *extra)
        assert codigo == 1 and "A_celulares" in res["detalhe"] and "--dir" in res["detalhe"]
        assert not (mae / esquema.ARQ_ESTADO).exists()


def test_regressao_cheirar_classifica_openalex_pelo_cabecalho(tmp_path):
    from rslib import projeto
    assert projeto._cheirar(SKILL / "assets" / "codebooks" / "elegibilidade_modelo.csv") == "codebook"
    casos = {
        "anotacoes.csv": ("nota,texto\n1,exportei do openalex (https://openalex.org/W1) ontem\n", None),
        "works.csv": ("id,doi,display_name,publication_year\nhttps://openalex.org/W1,,T,2020\n", "exportacao_openalex"),
        "works2.csv": ('"id";"authorships.author.display_name";"title"\n"W1";"A";"T"\n', "exportacao_openalex"),
        "B01.jsonl": ('{"id": "https://openalex.org/W123", "title": "x"}\n', "exportacao_openalex"),
        "notas.jsonl": ('{"nota": "ver openalex.org/W123"}\n', None),
        "registros.csv": ("id,display_name,publication_year\nW1,T,2020\n", None),
        "log_buscas.csv": ("busca_id,display_name,publication_year\nB01,T,2020\n", None),
        "codigos.csv": ("dimensao,variavel,descricao,prompt,tipo,aplicavel_se\nA,b,c,openalex,categorica,\n", "codebook"),
    }
    pasta = tmp_path / "solta"
    pasta.mkdir()
    for nome, (texto, esperado) in casos.items():
        (pasta / nome).write_text(texto, encoding="utf-8")
        assert projeto._cheirar(pasta / nome) == esperado, nome
    sugestoes = projeto.sugestoes_adocao(projeto.detectar_artefatos(pasta))
    assert sorted(s.split('"')[1] for s in sugestoes) == ["B01.jsonl", "works.csv", "works2.csv"]


def test_regressao_busca_sem_data_calada_quando_busca_ignorada():
    import datetime as dt
    from rslib import projeto
    est = {"projeto": {"etapas_ignoradas": ["04_busca"]},
           "buscas": [{"id": "B01", "fonte": "generico", "executada_em": None}]}
    assert projeto.alertas_buscas(est, hoje=dt.date(2026, 9, 15)) == []
    est["projeto"]["etapas_ignoradas"] = []
    assert [a["tipo"] for a in projeto.alertas_buscas(est, hoje=dt.date(2026, 9, 15))] == ["busca_sem_data"]


def test_regressao_busca_truncada_alerta_bloqueia_g3_e_marca_rascunho(projeto_vazio, capsys):
    import datetime as dt
    from rslib import esquema, estado
    montar_ledger(projeto_vazio)
    press_registrado(projeto_vazio)
    hoje = dt.date.today().isoformat()
    est = estado.carregar_estado(projeto_vazio)
    est["buscas"] = [{"id": "B01", "fonte": "wos", "executada_em": hoje, esquema.CAMPO_BUSCA_TRUNCADA: True},
                     {"id": "B02", "fonte": "scopus", "executada_em": hoje}]
    estado.salvar_estado(projeto_vazio, est)

    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert [(a["tipo"], a["busca"]) for a in res["alertas"]] == [("busca_truncada", "B01")]
    assert res["rascunho"] is True and any("truncadas: B01" in m for m in res["motivos_rascunho"])

    _autopiloto(projeto_vazio)
    codigo, res = _portao(capsys, projeto_vazio, "G3", por="autopiloto")
    assert codigo == 2 and [b["tipo"] for b in res["bloqueios"]] == ["limiar"] and "B01" in res["bloqueios"][0]["detalhe"]
    est = estado.carregar_estado(projeto_vazio)
    est["modo"]["autonomia"] = "checkpoints"
    estado.salvar_estado(projeto_vazio, est)
    assert _portao(capsys, projeto_vazio, "G3")[0] == 2
    codigo, res = _portao(capsys, projeto_vazio, "G3", "--forcar", "--motivo", "API limitada; truncamento declarado")
    assert codigo == 0 and res["forcado"] is True

    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert codigo == 0 and res["rascunho"] is True and res["buscas_truncadas"] == ["B01"]
    assert any("truncados" in a for a in res["avisos"])
    svg = (projeto_vazio / esquema.ARQ_PRISMA_SVG).read_text(encoding="utf-8")
    assert esquema.MARCA_RASCUNHO in svg and "Buscas truncadas: B01" in svg

    est = estado.carregar_estado(projeto_vazio)
    est["buscas"][0]["ativa"] = False  # substituída: deixa de contar
    estado.salvar_estado(projeto_vazio, est)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert not [a for a in res["alertas"] if a["tipo"] == "busca_truncada"] and res["rascunho"] is False
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert codigo == 0 and res["reexecucao"] is False and res["rascunho"] is False


def test_regressao_g2_exige_codebooks_e_protocolo_sem_placeholders(projeto_vazio, capsys):
    from rslib import projeto
    protocolo = projeto_vazio / "00-protocolo" / "protocolo.md"
    protocolo.write_text("# Protocolo\n", encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G2")
    detalhes = " ".join(b["detalhe"] for b in res["bloqueios"])
    assert codigo == 2 and "codebook v0" in detalhes and "codebook de elegibilidade" in detalhes
    assert {b["tipo"] for b in res["bloqueios"]} == {"artefato"}
    (projeto_vazio / "00-protocolo" / "codebook_v0_oqf.csv").write_text(CODEBOOK, encoding="utf-8")
    (projeto_vazio / "03-textos" / "codebook_elegibilidade.csv").write_text(CODEBOOK, encoding="utf-8")  # local antigo vale
    codigo, res = _portao(capsys, projeto_vazio, "G2")
    assert codigo == 0, res
    rodar(capsys, "--dir", projeto_vazio, "portao", "G2", "--reprovar", "--por", "revisor_humano_1", "--motivo", "x")

    protocolo.write_text(
        "# Protocolo: <X> e <Y> em <contexto>\n<!-- Placeholders entre <>. -->\n"
        "Registro em <https://osf.io/abc>; contato <equipe@exemplo.org>.<br>Linha<sup>2</sup>\n"
        "## Métodos {#sec-metodos}\nUse `{json}` e $x_{i}$; n < 30 e k > 5.\n```r\nx <- list(a = 1) # {chave}\n```\n",
        encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G2")
    bloqueio = next(b for b in res["bloqueios"] if "placeholders" in b["detalhe"])
    assert codigo == 2 and bloqueio["n"] == 3 and "<X>" in bloqueio["detalhe"] and "<Y>" in bloqueio["detalhe"]
    assert projeto.placeholders_no_texto(protocolo.read_text(encoding="utf-8")) == ["<X>", "<Y>", "<contexto>"]
    protocolo.write_text("# Protocolo: transferências e frequência escolar no Brasil\n", encoding="utf-8")
    (projeto_vazio / "00-protocolo" / "codebook_v0_oqf.csv").write_text(
        CODEBOOK + 'Id,familia,Família,"Classifique em {lista fechada de famílias}",categorica,\n', encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G2")
    assert codigo == 2 and "{lista fechada de famílias}" in res["bloqueios"][0]["detalhe"]
    codigo, res = _portao(capsys, projeto_vazio, "G2", "--forcar", "--motivo", "prompt revisado no piloto")
    assert codigo == 0 and res["forcado"] is True


def test_regressao_g3_aceita_pendencia_press_no_autopiloto_e_status_sugere_abrir(projeto_vazio, capsys):
    from rslib import estado
    montar_ledger(projeto_vazio, ate="registros")
    _autopiloto(projeto_vazio)
    est = estado.carregar_estado(projeto_vazio)
    est["ambiente"] = {"resumo": {"python_ok": True}}
    estado.salvar_estado(projeto_vazio, est)
    acao = __import__("rslib.projeto", fromlist=["x"])._acao_etapa(projeto_vazio, est, "04_busca", estado.ler_log(projeto_vazio))
    assert "pendencia abrir --tipo revisao_press" in acao["comando"]
    assert rodar(capsys, "--dir", projeto_vazio, "pendencia", "abrir", "--tipo", "revisao_press", "--etapa", "04_busca",
                 "--portao", "G3", "--descricao", "PRESS de S-scopus-v1 por revisor humano")[0] == 0
    codigo, res = _portao(capsys, projeto_vazio, "G3", por="autopiloto")
    assert codigo == 0 and res["pendencia_aberta"], res


def _g1_rapida(capsys, raiz, atalho=True):
    criterios = {"pergunta": "X reduz Y?", "tipo_revisao": "efetividade_swim", "variante": "rapida"}
    if atalho:
        criterios["atalho_rapida"] = "dupla humana em 20% e segunda leitura de todos os excluídos"
    assert _portao(capsys, raiz, "G1", "--criterios", json.dumps(criterios))[0] == 0


def test_regressao_g4_aceita_atalho_da_variante_rapida(tmp_path, capsys):
    from rslib import estado, projeto
    raiz = _projeto_triado(tmp_path / "r", "ta_v1")
    (raiz / "02-triagem" / "prompts").mkdir(parents=True, exist_ok=True)
    (raiz / "02-triagem" / "prompts" / "ta_v1.md").write_text("critérios v1", encoding="utf-8")
    _decisoes_ab(raiz, [("RS0001", "A", "incluir")])
    _g1_rapida(capsys, raiz)
    _validacao(raiz, False, finalidade="validacao", rodada="ta_v1", atalho_rapida=True, fracao_dupla_humana=0.25,
               kappa_humanos=0.71, segunda_leitura_excluidos=True, sensibilidade=0.9)
    acao = projeto._acao_etapa(raiz, estado.carregar_estado(raiz), "06_triagem_ta", estado.ler_log(raiz))
    assert acao["portao"] == "G4" and '"atalho_rapida": true' in acao["comando"] and "<κ da dupla humana" in acao["comando"]
    codigo, res = _portao(capsys, raiz, "G4")
    assert codigo == 0, res
    assert any("atalho da variante rápida" in a for a in res["avisos"])
    rodar(capsys, "--dir", raiz, "portao", "G4", "--reprovar", "--por", "revisor_humano_1", "--motivo", "x")

    _validacao(raiz, None, finalidade="validacao", rodada="ta_v1", atalho_rapida=True, n_dupla_humana=10,
               n_populacao=100, n_excluidos_ia=40, n_excluidos_relidos=12)
    codigo, res = _portao(capsys, raiz, "G4")
    tipos = sorted(b["tipo"] for b in res["bloqueios"])
    assert codigo == 2 and tipos == ["limiar", "validacao", "validacao"], res["bloqueios"]
    detalhes = " ".join(b["detalhe"] for b in res["bloqueios"])
    assert "10%" in detalhes and "κ" in detalhes and "segunda leitura" in detalhes

    # sem o critério atalho_rapida no G1: vale a regra geral (recall)
    outro = _projeto_triado(tmp_path / "s", "ta_v1")
    _g1_rapida(capsys, outro, atalho=False)
    _validacao(outro, False, finalidade="validacao", rodada="ta_v1", atalho_rapida=True, fracao_dupla_humana=0.3,
               kappa_humanos=0.8, segunda_leitura_excluidos=True)
    codigo, res = _portao(capsys, outro, "G4")
    assert codigo == 2 and [b["tipo"] for b in res["bloqueios"]] == ["limiar"]
    assert any("regra geral" in a for a in res["avisos"])


def test_regressao_g7_exige_rob_consolidado_e_avisa_concordancia(projeto_vazio, capsys):
    from rslib import esquema, estado
    est = estado.carregar_estado(projeto_vazio)
    est["projeto"]["tipo_revisao"] = "efetividade_meta"
    estado.salvar_estado(projeto_vazio, est)
    codigo, res = _portao(capsys, projeto_vazio, "G7")
    assert codigo == 2 and [b["tipo"] for b in res["bloqueios"]] == ["artefato"]
    assert "rob_consolidado" in res["bloqueios"][0]["detalhe"]
    assert any("concordância da extração não calculada" in a for a in res["avisos"])

    rob_consolidado(projeto_vazio)
    (projeto_vazio / esquema.ARQ_ROB_GERAL).write_text("chave\nSilva2020\nOutro2021\n", encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G7")
    assert codigo == 2 and "mudou depois da consolidação do RoB" in res["bloqueios"][0]["detalhe"]
    rob_consolidado(projeto_vazio)

    concordancia = projeto_vazio / "05-decomposicao" / "concordancia" / "concordancia.csv"
    concordancia.parent.mkdir(parents=True)
    concordancia.write_text(
        "nivel,chave,variavel,tipo,valor_original,valor_revalidacao,status,score\n"
        "detalhe,Silva2020,desenho,categorica,rct,rct,ok,1\n\n--- concordancia por variavel ---\n"
        "nivel,variavel,n_textos,concordancia_media,cohen_kappa,pabak,concordancia_valores,sinalizada,motivo_sinalizacao\n"
        "por_variavel,familia,10,0.9,0.8,0.8,0.9,nao,\npor_variavel,desenho,10,0.6,0.4,0.5,0.6,sim,kappa\n\n"
        "--- concordancia por texto ---\nnivel,citekey,n_vars_aplicaveis,concordancia_estrita\npor_texto,Silva2020,3,sim\n",
        encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G7")
    assert codigo == 0, res
    assert any("1 variáveis sinalizadas" in a and "desenho" in a for a in res["avisos"]), res["avisos"]
    rodar(capsys, "--dir", projeto_vazio, "portao", "G7", "--reprovar", "--por", "revisor_humano_1", "--motivo", "x")
    rel = "05-decomposicao/concordancia/concordancia.csv"
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "pendencia", "abrir", "--tipo", "concordancia_extracao", "--etapa",
                        "09_extracao_rob", "--portao", "G7", "--descricao", "arbitrar desenho", "--arquivo", rel)
    rodar(capsys, "--dir", projeto_vazio, "pendencia", "fechar", res["pendencia"], "--motivo", "arbitrado por humano")
    codigo, res = _portao(capsys, projeto_vazio, "G7")
    assert codigo == 0 and not any("sinalizadas" in a for a in res["avisos"]), res["avisos"]

    escopo = projeto_vazio / "escopo"
    escopo.mkdir()
    est = estado.estado_inicial("Escopo", tipo_revisao="escopo")
    estado.salvar_estado(escopo, est)
    assert _portao(capsys, escopo, "G7")[0] == 0  # TIPOS_SEM_ROB: sem RoB


def test_regressao_g8_exige_certeza_para_cada_celula_de_efeito(projeto_vazio, capsys):
    from rslib import esquema, estado
    est = estado.carregar_estado(projeto_vazio)
    est["projeto"]["tipo_revisao"] = "oqf_mista_sequencial"
    estado.salvar_estado(projeto_vazio, est)
    codigo, res = _portao(capsys, projeto_vazio, "G8")
    detalhes = " ".join(b["detalhe"] for b in res["bloqueios"])
    assert codigo == 2 and "caixa_ferramentas.csv não existe" in detalhes and "certeza.csv não existe" in detalhes
    (projeto_vazio / esquema.ARQ_CAIXA).write_text(
        "celula_id,familia_intervencao,construto_outcome,classe_desenho,dimensao,rotulo,status_rotulo\n"
        "C1,TCR,Frequência,randomizado,efeito,Positivo,definido\n"
        "C2,TCR,Frequência,nao_randomizado,efeito,Inconclusivo,definido\n"
        "C3,TCR,,,implementacao,Simples,definido\n", encoding="utf-8")
    certeza = projeto_vazio / esquema.ARQ_CERTEZA
    certeza.write_text("familia_intervencao,construto_outcome,dimensao,certeza,classe_desenho\n"
                       "tcr,frequencia,efeito,moderada,randomizado\n", encoding="utf-8")
    codigo, res = _portao(capsys, projeto_vazio, "G8")
    assert codigo == 2 and [b["tipo"] for b in res["bloqueios"]] == ["certeza"] and "C2" in res["bloqueios"][0]["detalhe"]
    with open(certeza, "a", encoding="utf-8") as f:
        f.write("TCR,Frequência,efeito,baixa,nao_randomizado\n")
    assert _portao(capsys, projeto_vazio, "G8")[0] == 0

    escopo = projeto_vazio / "escopo"
    escopo.mkdir()
    estado.salvar_estado(escopo, estado.estado_inicial("Escopo", tipo_revisao="escopo"))
    assert _portao(capsys, escopo, "G8")[0] == 0  # escopo sem caixa: sem juízo de certeza


def test_regressao_g9_compara_ultimo_seq_do_evento_e_ignora_reexecucao(projeto_vazio, capsys, monkeypatch):
    import argparse
    import re as _re
    from rslib import declaracao_ia, esquema, estado, projeto
    montar_ledger(projeto_vazio)
    assert rodar(capsys, "--dir", projeto_vazio, "prisma")[0] == 0
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    declaracao_ia.registrar(parser.add_subparsers(dest="comando"))
    args = parser.parse_args(["--dir", str(projeto_vazio), "declaracao-ia"])
    assert args.func(args) == 0
    capsys.readouterr()
    eventos = estado.ler_log(projeto_vazio)
    ev = [e for e in eventos if e["evento"] == "relatorio_gerado"][-1]
    assert ev["dados"]["ultimo_seq"] == max(e["seq"] for e in eventos if e["ator"]["id"] != declaracao_ia.ATOR)

    def avisos_declaracao():
        return [a for a in projeto.avisos_relato(projeto_vazio, estado.ler_log(projeto_vazio)) if "declaracao_uso_ia" in a]

    monkeypatch.setattr(projeto, "_RE_SEQ_DECLARACAO", _re.compile(r"frase que o template não tem mais"))
    assert avisos_declaracao() == []  # não depende da frase do texto
    estado.registrar_evento(projeto_vazio, "analise_executada", "10_sintese", "script", "analise_r",
                            dados={"reexecucao": True})
    assert avisos_declaracao() == []  # reexecução sem mudança não desatualiza
    estado.registrar_evento(projeto_vazio, "caixa_gerada", "10_sintese", "script", "caixa", dados={"n_pendentes": 0})
    avisos = avisos_declaracao()
    assert len(avisos) == 1 and f"cobre o log até o seq {ev['dados']['ultimo_seq']}" in avisos[0] and "caixa_gerada" in avisos[0]
    with open(projeto_vazio / esquema.ARQ_DECLARACAO_IA, "a", encoding="utf-8") as f:
        f.write("\nEditado à mão.\n")
    assert "escrita à mão" in avisos_declaracao()[0]


def _decisoes_ab(raiz, linhas, tipo_ator="ia_subagente"):
    (raiz / "dados").mkdir(exist_ok=True)
    with open(raiz / "dados" / "decisoes.jsonl", "w", encoding="utf-8") as f:
        for id_rs, revisor, decisao in linhas:
            f.write(json.dumps({"id_rs": id_rs, "etapa": "ta", "rodada": "ta_v1", "revisor": revisor,
                                "tipo_ator": tipo_ator, "decisao": decisao, "ts": "2026-01-01T00:00:00Z"}) + "\n")


def test_regressao_proxima_acao_sugere_arbitro_antes_de_consolidar(projeto_vazio):
    from rslib import estado, projeto
    raiz = projeto_vazio
    (raiz / "02-triagem/prompts/ta_v1.md").write_text("critérios v1", encoding="utf-8")

    def acao():
        return projeto._acao_etapa(raiz, estado.carregar_estado(raiz), "06_triagem_ta", estado.ler_log(raiz))

    _decisoes_ab(raiz, [("RS0001", "A", "incluir"), ("RS0002", "A", "excluir")])
    assert acao()["comando"] == "$RS triagem consolidar --rodada ta_v1"  # só A: nada a arbitrar
    _decisoes_ab(raiz, [("RS0001", "A", "incluir"), ("RS0002", "A", "excluir"),
                        ("RS0001", "B", "incluir"), ("RS0002", "B", "incluir")])
    a = acao()
    assert a["comando"] == ("$RS triagem preparar --etapa ta --rodada ta_v1 --revisor arbitro --apenas-divergentes "
                            "--criterios 02-triagem/prompts/ta_v1.md") and a["n_divergentes"] == 1
    assert "--regra liberal" in a["alternativa"]
    _decisoes_ab(raiz, [("RS0002", "humano_1", "excluir"), ("RS0002", "humano_2", "incluir")], tipo_ator="humano")
    assert acao()["comando"] == "$RS triagem consolidar --rodada ta_v1"  # dupla humana: desempate humano, não árbitro de IA
    _decisoes_ab(raiz, [("RS0001", "A", "incluir"), ("RS0002", "A", "excluir"),
                        ("RS0001", "B", "incluir"), ("RS0002", "B", "incluir")])
    manifesto = raiz / "02-triagem" / "lotes" / "ta_v1" / "arbitro" / "manifesto.json"
    manifesto.parent.mkdir(parents=True)
    manifesto.write_text(json.dumps({"lotes": [{"status": "preparado"}]}), encoding="utf-8")
    assert acao()["comando"] == "$RS triagem mesclar --rodada ta_v1 --revisor arbitro"
    manifesto.write_text(json.dumps({"lotes": [{"status": "mesclado"}]}), encoding="utf-8")
    _decisoes_ab(raiz, [("RS0001", "A", "incluir"), ("RS0002", "A", "excluir"), ("RS0001", "B", "incluir"),
                        ("RS0002", "B", "incluir"), ("RS0002", "arbitro", "incluir")])
    assert acao()["comando"] == "$RS triagem consolidar --rodada ta_v1"
    est = estado.carregar_estado(raiz)
    est["modo"]["triagem"] = "api"
    estado.salvar_estado(raiz, est)
    _decisoes_ab(raiz, [("RS0002", "A", "excluir"), ("RS0002", "B", "incluir")])
    assert acao()["comando"] == "$RS triagem consolidar --rodada ta_v1"  # API: o árbitro roda no próprio comando


def test_regressao_proxima_acao_remedio_5_com_poucos_incluidos_e_placeholders_do_g4(projeto_vazio):
    from rslib import estado, projeto
    raiz = projeto_vazio
    (raiz / "02-triagem/prompts/ta_v1.md").write_text("critérios v1", encoding="utf-8")
    _decisoes_ab(raiz, [("RS0001", "A", "incluir")])
    montar_ledger(raiz, ate="triagem")
    _validacao(raiz, False, finalidade="validacao", rodada="ta_v1", n_incluidos_humanos=8, n_falsos_negativos=0)
    acao = projeto._acao_etapa(raiz, estado.carregar_estado(raiz), "06_triagem_ta", estado.ler_log(raiz))
    assert "remédio 5" in acao["descricao"] and "--forcar --motivo" in acao["comando"] and acao["exige_humano"]
    _validacao(raiz, True, finalidade="validacao", rodada="ta_v1")
    acao = projeto._acao_etapa(raiz, estado.carregar_estado(raiz), "06_triagem_ta", estado.ler_log(raiz))
    assert "<sensibilidade da validação seq" in acao["comando"] and "0.0" not in acao["comando"]


def test_regressao_status_acusa_seq_repetido_no_log(projeto_vazio, capsys):
    linha = {"seq": 1, "ts": "2026-01-01T00:00:00Z", "evento": "erro", "etapa": "00_configuracao",
             "ator": {"tipo": "script", "id": "x", "modelo": None}, "dados": {}, "artefatos": [], "motivo": None}
    with open(projeto_vazio / "rs_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(linha) + "\n")
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    repetidos = [i for i in res["inconsistencias"] if i["tipo"] == "seq_repetido_no_log"]
    assert repetidos and repetidos[0]["gravidade"] == "aviso" and repetidos[0]["seqs"] == [1]


def test_regressao_mensagens_nao_citam_documentos_internos():
    import re as _re
    from conftest import SCRIPTS
    for nome in ("estado.py", "projeto.py", "prisma.py", "declaracao_ia.py", "ambiente.py"):
        texto = (SCRIPTS / "rslib" / nome).read_text(encoding="utf-8")
        assert not _re.search(r"Apêndice [BC]\b|\bPLANO\b|plano de construção", texto), nome


# ---------------------------------------------------------------------------
# Correções v1.3: G7 por ferramenta, próxima ação (busca truncada, --dir, autopiloto, G8 forçado, G4 largura_ic),
# pasta-mãe com vários projetos, aviso do G8 em projeto parcial
# ---------------------------------------------------------------------------
def _qualidade(raiz, capsys, *argv):
    from rs import construir_parser
    args = construir_parser().parse_args(["--dir", str(raiz), "qualidade", "consolidar", *argv])
    codigo = args.func(args)
    return codigo, json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def _tipo(raiz, tipo, **projeto_extra):
    from rslib import estado
    est = estado.carregar_estado(raiz)
    est["projeto"]["tipo_revisao"] = tipo
    est["projeto"].update(projeto_extra)
    estado.salvar_estado(raiz, est)


def test_regressao_g7_rob_por_ferramenta_validado_por_humano_e_cobrindo_resultados(projeto_vazio, capsys):
    from rslib import esquema, estado, projeto
    raiz = projeto_vazio
    _tipo(raiz, "efetividade_meta")
    q = raiz / "04-qualidade"
    (q / "resultados_avaliados.csv").write_text(
        "chave;id_estudo;construto_outcome;resultado;ferramenta;classificador\n"
        "Alves2020;ES0001;frequencia;Tab 2;rob2;b1\nCastro2018;ES0003;Frequência;Tab 1;robins_i;b1\n", encoding="utf-8")
    rob2 = "chave,construto_outcome,D1,D2,D3,D4,D5\nAlves2020,frequencia,baixo,baixo,baixo,baixo,alto\n"
    (q / "A_rob2.csv").write_text(rob2, encoding="utf-8")
    (q / "B_rob2.csv").write_text(rob2, encoding="utf-8")

    def g7():
        codigo, res = _portao(capsys, raiz, "G7")
        return codigo, res.get("bloqueios") or [], " | ".join(b["detalhe"] for b in res.get("bloqueios") or [])

    codigo, bloqueios, detalhes = g7()
    assert codigo == 2 and "nenhum evento rob_consolidado" in detalhes

    # avaliadores sem papel humano: rob_geral sai com validado_humano = 0 e o G7 exige validação humana
    assert _qualidade(raiz, capsys, "--ferramenta", "rob2", "--a", str(q / "A_rob2.csv"), "--b", str(q / "B_rob2.csv"))[0] == 0
    codigo, bloqueios, detalhes = g7()
    assert codigo == 2 and "rob2: fase 1 feita" not in detalhes and "sem a fase 2" in detalhes  # só fase 1: rob_geral não existe
    assert _qualidade(raiz, capsys, "--ferramenta", "rob2", "--consenso", esquema.PADRAO_ROB_CONSENSO.format(ferramenta="rob2"))[0] == 0
    codigo, bloqueios, detalhes = g7()
    tipos = {b["tipo"] for b in bloqueios}
    assert codigo == 2 and tipos == {"validacao", "artefato"}
    assert "sem validação humana" in detalhes and "sem consolidação do RoB: robins_i" in detalhes
    assert "Castro2018×Frequência (robins_i)" in detalhes and "Alves2020" not in detalhes.split("resultados avaliados")[-1]
    acao = projeto._acao_etapa(raiz, estado.carregar_estado(raiz), "09_extracao_rob", estado.ler_log(raiz))
    assert acao["tipo"] == "tarefa" and acao["comando"].startswith("$RS qualidade consolidar --ferramenta")

    # dupla humana: todos validados; falta a outra ferramenta
    assert _qualidade(raiz, capsys, "--ferramenta", "rob2", "--a", str(q / "A_rob2.csv"), "--b", str(q / "B_rob2.csv"),
                      "--avaliador-a", "revisor_humano_1", "--avaliador-b", "revisor_humano_2")[0] == 0
    assert _qualidade(raiz, capsys, "--ferramenta", "rob2", "--consenso", esquema.PADRAO_ROB_CONSENSO.format(ferramenta="rob2"))[0] == 0
    codigo, bloqueios, detalhes = g7()
    assert codigo == 2 and {b["tipo"] for b in bloqueios} == {"artefato"} and "sem validação humana" not in detalhes

    robins = ("chave,construto_outcome,dominio,julgamento,trecho,pagina\n"
              + "".join(f"Castro2018,frequencia,D{i},moderado,,\n" for i in range(1, 7)))
    (q / "A_robins.csv").write_text(robins, encoding="utf-8")
    (q / "B_robins.csv").write_text(robins, encoding="utf-8")
    assert _qualidade(raiz, capsys, "--ferramenta", "robins_i", "--a", str(q / "A_robins.csv"), "--b", str(q / "B_robins.csv"),
                      "--avaliador-a", "revisor_humano_1", "--avaliador-b", "revisor_humano_2")[0] == 0
    codigo, bloqueios, detalhes = g7()
    assert codigo == 2 and "robins_i: fase 1 feita" in detalhes and "sem a fase 2" in detalhes
    assert _qualidade(raiz, capsys, "--ferramenta", "robins_i", "--consenso",
                      esquema.PADRAO_ROB_CONSENSO.format(ferramenta="robins_i"))[0] == 0
    codigo, bloqueios, detalhes = g7()
    assert codigo == 0, detalhes  # rob_geral.csv regravado pelo robins_i: as linhas do rob2 continuam conferindo

    rodar(capsys, "--dir", raiz, "portao", "G7", "--reprovar", "--por", "revisor_humano_1", "--motivo", "conferir")
    texto = (raiz / esquema.ARQ_ROB_GERAL).read_text(encoding="utf-8")
    (raiz / esquema.ARQ_ROB_GERAL).write_text(texto.replace("rob2,alto", "rob2,baixo"), encoding="utf-8")
    codigo, bloqueios, detalhes = g7()
    assert codigo == 2 and "linhas de rob2" in detalhes and "mudou depois da consolidação do RoB de robins_i" in detalhes


def test_regressao_proxima_acao_busca_truncada_do_openalex_sugere_buscar_openalex(projeto_vazio):
    import shlex as _shlex
    from rslib import esquema, estado, projeto
    raiz = projeto_vazio
    montar_ledger(raiz, ate="registros")
    est = estado.carregar_estado(raiz)
    query = '("conditional cash transfer" OR "bolsa família") AND school'
    est["buscas"] = [{"id": "B04", "fonte": "openalex", "query": query, "campo": "title_and_abstract",
                      "string_id": "S-oa-v1", "arquivo": "01-busca/brutos/B04_openalex.jsonl",
                      esquema.CAMPO_BUSCA_TRUNCADA: True}]
    estado.salvar_estado(raiz, est)
    acao = projeto._acao_etapa(raiz, estado.carregar_estado(raiz), "04_busca", estado.ler_log(raiz))
    assert acao["comando"].startswith("$RS buscar openalex --busca-id <novo busca_id> --query ")
    partes = _shlex.split(acao["comando"].replace("<novo busca_id>", "B05"))
    assert partes[partes.index("--query") + 1] == query and partes[partes.index("--substituir") + 1] == "B04"
    assert "--motivo" in partes and "--string-id" in partes and "importar" not in acao["comando"]
    alerta = projeto.alertas_buscas(estado.carregar_estado(raiz))[0]
    assert "buscar openalex" in alerta["detalhe"] and alerta["comando"] == acao["comando"]

    est = estado.carregar_estado(raiz)
    est["buscas"] = [{"id": "B01", "fonte": "wos", esquema.CAMPO_BUSCA_TRUNCADA: True}]
    estado.salvar_estado(raiz, est)
    acao = projeto._acao_etapa(raiz, estado.carregar_estado(raiz), "04_busca", estado.ler_log(raiz))
    assert acao["comando"].startswith("$RS importar --arquivo") and "--substituir B01" in acao["comando"]


def test_regressao_status_com_dir_propaga_dir_e_dedup_revisar_leva_por(projeto_vazio, capsys):
    from rslib import esquema, estado, projeto
    raiz = projeto_vazio
    codigo, res = rodar(capsys, "--dir", raiz, "status")
    assert res["proxima_acao"]["comando"] == f'$RS --dir "{raiz}" ambiente'
    assert projeto.com_dir({"a": ["$RS x", '$RS --dir "d" y'], "b": "rode `$RS prisma` e `$RS bib`"}, "p q") == \
        {"a": ['$RS --dir "p q" x', '$RS --dir "d" y'], "b": 'rode `$RS --dir "p q" prisma` e `$RS --dir "p q" bib`'}
    assert projeto.com_dir("$RS status", None) == "$RS status"

    montar_ledger(raiz, ate="unicos")
    with open(raiz / esquema.ARQ_DEDUP_PARES, "w", encoding="utf-8") as f:
        f.write(",".join(esquema.COLUNAS_DEDUP_PARES) + "\nB01-00001,B02-00001,R5_candidato,88,,,,,,,candidato,,\n")
    acao = projeto._acao_etapa(raiz, estado.carregar_estado(raiz), "05_organizacao", estado.ler_log(raiz))
    assert acao["comando"] == f"$RS dedup --revisar {esquema.ARQ_DEDUP_PARES} --por {esquema.PAPEL_HUMANO_PADRAO}"
    assert acao["exige_humano"] is True


def _etapas_ate(raiz, est, eventos, concluidas_ate):
    from rslib import esquema, projeto
    etapas, portoes = projeto.recalcular_etapas(raiz, est, eventos)
    for e in esquema.ETAPAS[: esquema.ETAPAS.index(concluidas_ate) + 1]:
        etapas[e]["status"] = "concluida"
    return etapas, portoes


def test_regressao_autopiloto_tarefa_humana_com_pendencia_aponta_como_seguir(projeto_vazio):
    from rslib import esquema, estado, projeto
    raiz = projeto_vazio
    _autopiloto(raiz)
    montar_ledger(raiz, ate="unicos")
    with open(raiz / esquema.ARQ_DEDUP_PARES, "w", encoding="utf-8") as f:
        f.write(",".join(esquema.COLUNAS_DEDUP_PARES) + "\nB01-00001,B02-00001,R5_candidato,88,,,,,,,candidato,,\n")

    def acao():
        est = estado.carregar_estado(raiz)
        eventos = estado.ler_log(raiz)
        etapas, portoes = _etapas_ate(raiz, est, eventos, "04_busca")
        return projeto.proxima_acao(raiz, est, etapas, portoes, eventos, [])

    a = acao()
    assert a["etapa"] == "05_organizacao" and "pendencia" not in a and "alternativa" not in a  # sem pendência: só a tarefa
    pid = estado.abrir_pendencia(raiz, "dedup_candidatos", "05_organizacao", "1 par candidato", n=1)
    a = acao()
    assert a["exige_humano"] is True and a["pendencia"] == pid and "dedup --revisar" in a["comando"]
    assert "seguir sem esperar a pendência" in a["alternativa"] and "$RS filtrar --config" in a["alternativa"]
    assert a["acao_seguinte"]["etapa"] == "05_organizacao"
    montar_ledger(raiz, ate="filtro")
    a = acao()
    assert a["acao_seguinte"]["etapa"] == "06_triagem_ta" and "critérios de triagem" in a["alternativa"]

    # portão da etapa com bloqueio duro (G4 abaixo do limiar): tarefa humana sem atalho para as etapas seguintes
    (raiz / "02-triagem/prompts/ta_v1.md").write_text("critérios v1", encoding="utf-8")
    _decisoes_ab(raiz, [("RS0001", "A", "incluir")])
    montar_ledger(raiz, ate="triagem")
    with open(raiz / esquema.ARQ_DEDUP_PARES, "w", encoding="utf-8") as f:
        f.write(",".join(esquema.COLUNAS_DEDUP_PARES) + "\n")
    estado.fechar_pendencia(raiz, pid, "pares revisados")
    _validacao(raiz, False, finalidade="validacao", rodada="ta_v1", motivo_reprovacao="desempenho_ia", n_falsos_negativos=2)
    pid_val = estado.abrir_pendencia(raiz, "validacao_triagem_reprovada", "06_triagem_ta", "2 falsos negativos", portao="G4")
    est = estado.carregar_estado(raiz)
    eventos = estado.ler_log(raiz)
    etapas, portoes = _etapas_ate(raiz, est, eventos, "05_organizacao")
    a = projeto.proxima_acao(raiz, est, etapas, portoes, eventos, [])
    assert a["etapa"] == "06_triagem_ta" and a["exige_humano"] is True and a["pendencia"] == pid_val
    assert "falsos negativos" in a["descricao"] and "alternativa" not in a


def test_regressao_g8_forcado_em_projeto_parcial_nao_e_fim_e_avisa_efeitos_nao_verificados(tmp_path, capsys):
    from rslib import esquema, estado, projeto
    raiz = tmp_path / "meta"
    for pasta in esquema.PASTAS_PROJETO:
        (raiz / pasta).mkdir(parents=True, exist_ok=True)
    est = estado.estado_inicial("Só a meta", tipo_revisao="efetividade_meta", parcial="meta")
    est["projeto"]["etapas_ignoradas"] = projeto.etapas_ignoradas_para("meta")
    for e in est["projeto"]["etapas_ignoradas"]:
        est["etapas"][e]["status"] = "ignorada"
    est["ambiente"] = {"resumo": {"python_ok": True}}
    estado.salvar_estado(raiz, est)
    estado.registrar_evento(raiz, "analise_executada", "10_sintese", "script", "rs.py analise",
                            dados={"script": "efeitos.R", "resumo_r": {"comando": "efeitos", "n_nao_verificados_humano": 3}})
    (raiz / esquema.ARQ_CAIXA).write_text(
        "celula_id,familia_intervencao,construto_outcome,classe_desenho,dimensao,rotulo,status_rotulo\n"
        "C1,TCR,frequencia,randomizado,efeito,Positivo,definido\nC2,TCR,,,implementacao,Não avaliada,pendente\n",
        encoding="utf-8")
    estado.registrar_evento(raiz, "caixa_gerada", "10_sintese", "script", "caixa", dados={"n_pendentes": 1})

    codigo, res = _portao(capsys, raiz, "G8")
    assert codigo == 2 and any("3 efeitos calculados sem verificado_humano" in a for a in res["avisos"])
    codigo, res = _portao(capsys, raiz, "G8", "--forcar", "--motivo", "dados do usuário; implementação não avaliada")
    assert codigo == 0 and res["forcado"] is True
    codigo, res = rodar(capsys, "--dir", raiz, "status")
    acao = res["proxima_acao"]
    assert res["etapa_atual"] is None and res["rascunho"] is True
    assert acao["tipo"] == "tarefa" and acao["etapa"] == "11_relato" and acao["portoes_forcados"] == ["G8"]
    assert "ignorada no projeto parcial" in acao["descricao"] and acao["comando"] == f'$RS --dir "{raiz}" caixa --master <master>'

    (raiz / esquema.ARQ_CAIXA).write_text(
        "celula_id,familia_intervencao,construto_outcome,classe_desenho,dimensao,rotulo,status_rotulo\n"
        "C1,TCR,frequencia,randomizado,efeito,Positivo,definido\n", encoding="utf-8")
    (raiz / esquema.ARQ_CERTEZA).write_text("familia_intervencao,construto_outcome,dimensao,certeza,classe_desenho\n"
                                            "TCR,frequencia,efeito,moderada,randomizado\n", encoding="utf-8")
    estado.registrar_evento(raiz, "caixa_gerada", "10_sintese", "script", "caixa", dados={"n_pendentes": 0})
    codigo, res = rodar(capsys, "--dir", raiz, "status")
    assert res["proxima_acao"]["tipo"] == "fim" and res["rascunho"] is False


def test_regressao_pasta_mae_com_varios_projetos_lista_titulo_etapa_e_ultimo_evento(tmp_path, capsys):
    from rslib import esquema, estado
    mae = tmp_path / "mae"
    for nome, titulo, ts in (("A_antigo", "Projeto antigo", "2026-01-10T10:00:00Z"),
                             ("B_recente", "Projeto recente", "2026-09-01T10:00:00Z")):
        raiz = mae / nome
        raiz.mkdir(parents=True)
        estado.salvar_estado(raiz, estado.estado_inicial(titulo))
        estado.registrar_evento(raiz, "projeto_criado", "00_configuracao", "script", "teste")
        log = raiz / esquema.ARQ_LOG
        linhas = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
        for l in linhas:
            l["ts"] = ts
        log.write_text("".join(json.dumps(l) + "\n" for l in linhas), encoding="utf-8")
    codigo, res = rodar(capsys, "--dir", mae, "status")
    assert codigo == 0 and res["projetos_em_subpastas"] == ["A_antigo", "B_recente"]
    assert [p["titulo"] for p in res["projetos"]] == ["Projeto recente", "Projeto antigo"]
    assert res["projetos"][0]["etapa_atual"] == "00_configuracao" and res["projetos"][0]["ultimo_evento_em"].startswith("2026-09")
    acao = res["proxima_acao"]
    assert acao["comando"] == f'$RS --dir "{(mae / "B_recente").as_posix()}" status' and acao["exige_humano"] is True
    assert acao["alternativas"] == [f'$RS --dir "{(mae / "A_antigo").as_posix()}" status']
    assert "Projeto antigo" in acao["descricao"] and "2026-01-10" in acao["descricao"]


def test_regressao_g4_largura_ic_amplia_amostra_e_nao_revisa_criterios(projeto_vazio, monkeypatch):
    from rslib import estado, projeto
    raiz = projeto_vazio
    (raiz / "02-triagem/prompts/ta_v1.md").write_text("critérios v1", encoding="utf-8")
    _decisoes_ab(raiz, [("RS0001", "A", "incluir")])
    montar_ledger(raiz, ate="triagem")

    def acao():
        return projeto._acao_etapa(raiz, estado.carregar_estado(raiz), "06_triagem_ta", estado.ler_log(raiz))

    _validacao(raiz, False, finalidade="validacao", rodada="ta_v1", etapa="ta", n_incluidos_humanos=20,
               n_falsos_negativos=0, motivo_reprovacao="largura_ic")
    a = acao()
    assert a["tipo"] == "comando" and a["motivo_reprovacao"] == "largura_ic"
    assert a["comando"].startswith("$RS validar amostrar --etapa ta --rodada ta_v1") and "--enriquecer-incluidos 60" in a["comando"]
    assert a["alternativa"].startswith("$RS validar elusao") and "não revise os critérios" in a["descricao"]
    assert "vN+1" not in a["descricao"]
    monkeypatch.setattr(projeto, "_plano_da_validacao", lambda r, ev: {"incluidos_humanos_necessarios": 36,
                                                                       "incluidos_ia_nao_sorteados": 4})
    a = acao()
    assert "remédio 5" in a["descricao"] and "--forcar --motivo" in a["comando"] and a["exige_humano"] is True
    _validacao(raiz, False, finalidade="validacao", rodada="ta_v1", motivo_reprovacao="humanos")
    assert "concordância entre os humanos" in acao()["descricao"]
    _validacao(raiz, False, finalidade="validacao", rodada="ta_v1", motivo_reprovacao="desempenho_ia", n_falsos_negativos=3)
    assert "falsos negativos" in acao()["descricao"]


def test_regressao_g4_variante_rapida_sem_campos_do_atalho_orienta_forcar(tmp_path, capsys):
    from rslib import estado, projeto
    raiz = tmp_path / "rapida"
    raiz.mkdir()
    estado.salvar_estado(raiz, estado.estado_inicial("Rápida", tipo_revisao="efetividade_swim"))
    montar_ledger(raiz, ate="triagem")
    est = estado.carregar_estado(raiz)
    est["projeto"]["variante"] = "rapida"
    est["versoes_ativas"]["rodada_ta"] = "ta_v1"
    estado.salvar_estado(raiz, est)
    assert rodar(capsys, "--dir", raiz, "portao", "G1", "--aprovar", "--por", "revisor_humano_1", "--criterios",
                 json.dumps({"pergunta": "X?", "tipo_revisao": "efetividade_swim", "variante": "rapida",
                             "atalho_rapida": True}))[0] == 0
    _validacao(raiz, False, finalidade="validacao", rodada="ta_v1", kappa_humanos=0.8)
    codigo, res = _portao(capsys, raiz, "G4")
    assert codigo == 2 and [b["tipo"] for b in res["bloqueios"]] == ["limiar"]
    assert any("não traz os campos do atalho" in a for a in res["avisos"])
    (raiz / "02-triagem/prompts").mkdir(parents=True, exist_ok=True)
    (raiz / "02-triagem/prompts/ta_v1.md").write_text("critérios v1", encoding="utf-8")
    _decisoes_ab(raiz, [("RS0001", "A", "incluir")])
    acao = projeto._acao_etapa(raiz, estado.carregar_estado(raiz), "06_triagem_ta", estado.ler_log(raiz))
    assert acao["comando"] == "$RS validar calcular --planilha <planilha codificada da validação> --atalho-rapida"
    assert "--forcar" in acao["alternativa"] and "atalho da variante" in acao["alternativa"] and acao["exige_humano"] is True
    # validação com os campos do atalho, mas sem a segunda leitura de todos os excluídos: completar o atalho
    _validacao(raiz, False, finalidade="validacao", rodada="ta_v1", atalho_rapida=True, fracao_dupla_humana=0.25,
               kappa_humanos=0.8, n_excluidos_ia=5, n_excluidos_relidos=2, segunda_leitura_excluidos=False)
    acao = projeto._acao_etapa(raiz, estado.carregar_estado(raiz), "06_triagem_ta", estado.ler_log(raiz))
    assert acao["comando"].startswith("$RS validar segunda-leitura --rodada ta_v1") and "incompleto" in acao["descricao"]
    _validacao(raiz, False, finalidade="validacao", rodada="ta_v1", atalho_rapida=True, fracao_dupla_humana=0.25,
               kappa_humanos=0.8, n_excluidos_ia=5, n_excluidos_relidos=5, segunda_leitura_excluidos=True)
    acao = projeto._acao_etapa(raiz, estado.carregar_estado(raiz), "06_triagem_ta", estado.ler_log(raiz))
    assert acao["tipo"] == "portao" and "atalho" in acao["descricao"]
    assert _portao(capsys, raiz, "G4")[0] == 0
