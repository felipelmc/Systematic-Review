"""Testes de `rs.py qualidade consolidar`: concordância por domínio, fila de desacordos e rob_geral."""

import json

import pytest

from conftest import ler_jsonl
from test_textos import escrever_unicos


def rodar(raiz, capsys, *argv):
    from rs import construir_parser
    args = construir_parser().parse_args(["--dir", str(raiz), "qualidade", "consolidar", *argv])
    codigo = args.func(args)
    return codigo, json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def _modo(raiz, modo):
    from rslib import estado
    est = estado.carregar_estado(raiz)
    est["modo"]["autonomia"] = modo
    estado.salvar_estado(raiz, est)


def _eventos(raiz, nome):
    from rslib import esquema
    return [e for e in ler_jsonl(raiz / esquema.ARQ_LOG) if e["evento"] == nome]


def _abertas(raiz):
    from rslib import estado
    return [p for p in estado.pendencias_abertas(estado.carregar_estado(raiz)) if p["tipo"] == "consenso_rob"]


def _escrever(caminho, texto):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
    return caminho


# RoB 2 no formato largo, como sai de uma planilha pt-BR (ponto e vírgula). D1b vazio: randomização individual.
A_ROB2 = """chave;construto_outcome;resultado;D1;D1b;D2;D3;D4;D5;rob_geral;justificativa
Alves2020;frequencia;Tab 2;baixo;;baixo;algumas preocupações;baixo;baixo;algumas_preocupacoes;perdas de 12%
Borges2019;frequencia;Tab 3;Low;;alto;baixo;baixo;baixo;alto;desvios
"""
B_ROB2 = """chave;construto_outcome;resultado;D1;D1b;D2;D3;D4;D5;rob_geral;justificativa
Alves2020;frequencia;Tab 2;baixo;;baixo;baixo;baixo;baixo;baixo;
Borges2019;frequencia;Tab 3;baixo;;alto;baixo;baixo;some concerns;alto;desvios e plano não registrado
"""


def _fase1_rob2(raiz, capsys, *extra):
    a = _escrever(raiz / "04-qualidade/rob_rob2_A.csv", A_ROB2)
    b = _escrever(raiz / "04-qualidade/rob_rob2_B.csv", B_ROB2)
    return rodar(raiz, capsys, "--ferramenta", "rob2", "--a", str(a), "--b", str(b),
                 "--avaliador-a", "revisor_humano_1", "--avaliador-b", "revisor_humano_2", *extra)


# ---------------------------------------------------------------------------
# Unidades
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("ferramenta,valor,papel,esperado", [
    ("rob2", "Algumas preocupações", "dominio", "algumas_preocupacoes"),
    ("rob2", "Some concerns", "dominio", "algumas_preocupacoes"),
    ("rob2", "HIGH", "geral", "alto"),
    ("rob2", "moderado", "dominio", None),
    ("robins_i", "Serious", "dominio", "grave"),
    ("robins_i", "Crítico", "dominio", "critico"),
    ("robins_i", "Low (except for concerns about uncontrolled confounding)", "dominio", "baixo_exceto_confundimento"),
    ("robins_i", "baixo", "geral", "baixo_exceto_confundimento"),
    ("robins_i", "proposta_moderado", "dominio", "moderado"),
    ("epoc", "Unclear", "dominio", "incerto"),
    ("epoc", "incerto", "geral", "moderado"),
    ("casp_qualitativo", "Sim", "dominio", "S"),
    ("casp_qualitativo", "não é possível dizer", "dominio", "NPD"),
    ("casp_qualitativo", "NA", "dominio", "nao_se_aplica"),
    ("jbi_transversal", "NA", "dominio", "NA"),
    ("jbi_transversal", "incerto", "dominio", "I"),
    ("mmat", "Menores", "geral", "menores"),
    ("rob2", "NA_secao", "dominio", "nao_se_aplica"),
    ("rob2", "", "dominio", "nao_se_aplica"),
])
def test_vocabulario_normalizado(ferramenta, valor, papel, esperado):
    from rslib.qualidade import normalizar_valor
    assert normalizar_valor(ferramenta, valor, papel)[0] == esperado


def test_kappa_e_pabak_com_valores_de_referencia():
    from rslib.qualidade import concordancia
    pares = [("baixo", "baixo")] * 4 + [("baixo", "alto")] + [("alto", "alto")] * 4 + [("alto", "baixo")]
    c = concordancia(pares, 3)
    assert c["concordancia"] == 0.8 and c["kappa"] == pytest.approx(0.6) and c["pabak"] == pytest.approx(0.7)
    assert c["n_desacordos"] == 2 and c["sinalizado"] is False  # PABAK chega a 0,7
    # prevalência extrema: κ indefinido, PABAK = 1
    todos = concordancia([("baixo", "baixo")] * 6, 3)
    assert todos["kappa"] is None and todos["pabak"] == 1.0 and todos["sinalizado"] is False
    ruim = concordancia([("baixo", "alto"), ("alto", "baixo"), ("baixo", "baixo")], 3)
    assert ruim["sinalizado"] is True
    sk = pytest.importorskip("sklearn.metrics")
    a, b = zip(*pares)
    assert c["kappa"] == pytest.approx(sk.cohen_kappa_score(a, b), abs=1e-4)


def test_papel_humano():
    from rslib.qualidade import eh_papel_humano
    assert eh_papel_humano("revisor_humano_1") and eh_papel_humano("humano_2")
    assert not any(eh_papel_humano(p) for p in ("", "A", "ia_proposta_A", "autopiloto", "script", "subagente_humano"))
    assert eh_papel_humano("concordancia:ia_proposta_A+revisor_humano_2")
    assert not eh_papel_humano("concordancia:A+B")


# ---------------------------------------------------------------------------
# Fase 1 e fase 2 com RoB 2
# ---------------------------------------------------------------------------
def test_fase1_concordancia_fila_e_evento(projeto_vazio, capsys):
    from rslib import esquema
    from rslib.handoff import ler_csv
    from rslib.qualidade import COLUNAS_CONCORDANCIA
    _modo(projeto_vazio, "autopiloto")
    escrever_unicos(projeto_vazio, ["Alves2020", "Borges2019"])
    codigo, resumo = _fase1_rob2(projeto_vazio, capsys)
    assert codigo == 0, resumo
    arq = esquema.PADRAO_ROB_CONSENSO.format(ferramenta="rob2")
    colunas, linhas = ler_csv(projeto_vazio / arq)
    assert colunas == esquema.COLUNAS_ROB_CONSENSO
    por = {(l["chave"], l["dominio"]): l for l in linhas}
    assert len(linhas) == 10  # 2 resultados × D1..D5; D1b vazio nos dois = não se aplica; geral só na concordância
    assert not any(l["dominio"] in ("D1b", "geral") for l in linhas)
    d3 = por[("Alves2020", "D3")]
    assert (d3["julgamento_a"], d3["julgamento_b"], d3["julgamento_consenso"], d3["resolvido_por"]) == \
        ("algumas_preocupacoes", "baixo", "", "")
    d1 = por[("Borges2019", "D1")]  # "Low" e "baixo" concordam
    assert d1["julgamento_consenso"] == "baixo" and d1["resolvido_por"] == "concordancia:revisor_humano_1+revisor_humano_2"
    assert d1["id_estudo"] == "ES0002" and d1["ferramenta"] == "rob2"
    assert por[("Borges2019", "D5")]["justificativa"] == "A: desvios || B: desvios e plano não registrado"
    assert resumo["n_desacordos"] == 2 and resumo["n_pendentes"] == 2 and resumo["n_resultados"] == 2
    conc = resumo["concordancia"]
    assert conc["D3"]["n"] == 2 and conc["D3"]["concordancia"] == 0.5 and conc["D3"]["sinalizado"] is True
    assert conc["geral"]["concordancia"] == 0.5 and "D3" in resumo["dominios_sinalizados"]
    colunas_c, linhas_c = ler_csv(projeto_vazio / "04-qualidade/rob_rob2_concordancia.csv")
    assert colunas_c == COLUNAS_CONCORDANCIA and {l["dominio"] for l in linhas_c} == {"D1", "D2", "D3", "D4", "D5", "geral"}
    ev = _eventos(projeto_vazio, "fila_gerada")[-1]
    assert ev["dados"]["fila"] == "consenso_rob" and ev["dados"]["n_pendentes"] == 2 and ev["dados"]["ferramenta"] == "rob2"
    assert [p["n"] for p in _abertas(projeto_vazio)] == [2] and resumo["pendencia"]
    assert "Apêndice" not in resumo["proxima_acao"] and "revisor_humano_1" in resumo["proxima_acao"]
    # reexecução idêntica: sem evento novo nem pendência duplicada
    n_ev = len(_eventos(projeto_vazio, "fila_gerada"))
    codigo, resumo2 = _fase1_rob2(projeto_vazio, capsys)
    assert codigo == 0 and resumo2["reexecucao"] is True and len(_eventos(projeto_vazio, "fila_gerada")) == n_ev
    assert len(_abertas(projeto_vazio)) == 1


def _resolver(raiz, resolucoes, por="revisor_humano_1"):
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_csv
    arq = raiz / esquema.PADRAO_ROB_CONSENSO.format(ferramenta="rob2")
    colunas, linhas = ler_csv(arq)
    for l in linhas:
        if (l["chave"], l["dominio"]) in resolucoes:
            l["julgamento_consenso"] = resolucoes[(l["chave"], l["dominio"])]
            l["resolvido_por"] = por
            l["justificativa"] = l["justificativa"] or "reunião de consenso"
    escrever_csv(arq, colunas, linhas)
    return arq


def test_fase2_exige_resolucao_humana_e_grava_rob_geral(projeto_vazio, capsys):
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_csv
    _modo(projeto_vazio, "autopiloto")
    escrever_unicos(projeto_vazio, ["Alves2020", "Borges2019"])
    assert _fase1_rob2(projeto_vazio, capsys)[0] == 0
    arq = esquema.PADRAO_ROB_CONSENSO.format(ferramenta="rob2")
    # sem resolução: código 2, nada em rob_geral, pendência continua
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--consenso", arq)
    assert codigo == 2 and resumo["n_problemas"] == 2 and not (projeto_vazio / esquema.ARQ_ROB_GERAL).exists()
    assert any("sem julgamento_consenso" in p for p in resumo["problemas"])
    assert [p["n"] for p in _abertas(projeto_vazio)] == [2]
    # consenso preenchido por IA não vale
    _resolver(projeto_vazio, {("Alves2020", "D3"): "algumas_preocupacoes", ("Borges2019", "D5"): "algumas_preocupacoes"},
              por="ia_subagente")
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--consenso", arq)
    assert codigo == 2 and any("não é papel humano" in p for p in resumo["problemas"])
    # resolvido_por vazio: recusa sem --por; com --por humano, preenche e segue
    colunas, linhas = ler_csv(projeto_vazio / arq)
    for l in linhas:
        if l["resolvido_por"] == "ia_subagente":
            l["resolvido_por"] = ""
    escrever_csv(projeto_vazio / arq, colunas, linhas)
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--consenso", arq)
    assert codigo == 2 and any("resolvido_por vazio" in p for p in resumo["problemas"])
    assert "--por revisor_humano_1" in resumo["proxima_acao"]
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--consenso", arq, "--por", "script")
    assert codigo == 1 and "não é papel humano" in resumo["erro"]
    # rob_geral de outra ferramenta já gravado é preservado
    escrever_csv(projeto_vazio / esquema.ARQ_ROB_GERAL, esquema.COLUNAS_ROB_GERAL, [
        {"chave": "Castro2018", "construto_outcome": "frequencia", "ferramenta": "robins_i", "rob_geral": "grave",
         "validado_humano": "1"}])
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--consenso", arq, "--por", "revisor_humano_1")
    assert codigo == 0, resumo
    assert resumo["n_resolvido_por_preenchido"] == 2 and resumo["n_validados_humano"] == 2
    colunas_g, geral = ler_csv(projeto_vazio / esquema.ARQ_ROB_GERAL)
    assert colunas_g == esquema.COLUNAS_ROB_GERAL
    g = {(l["ferramenta"], l["chave"]): l for l in geral}
    assert g[("rob2", "Alves2020")]["rob_geral"] == "algumas_preocupacoes"   # pior domínio
    assert g[("rob2", "Borges2019")]["rob_geral"] == "alto"
    assert g[("rob2", "Borges2019")]["validado_humano"] == "1" and g[("rob2", "Borges2019")]["id_estudo"] == "ES0002"
    assert g[("robins_i", "Castro2018")]["rob_geral"] == "grave"
    assert [l["resolvido_por"] for l in ler_csv(projeto_vazio / arq)[1] if l["dominio"] == "D3"
            and l["chave"] == "Alves2020"] == ["revisor_humano_1"]
    ev = _eventos(projeto_vazio, "rob_consolidado")[-1]
    assert ev["dados"]["ferramenta"] == "rob2" and ev["dados"]["todos_validados_humano"] is True
    assert ev["dados"]["concordancia"]["D3"]["concordancia"] == 0.5 and ev["dados"]["n_desacordos"] == 2
    assert {a["caminho"] for a in ev["artefatos"]} == {arq, esquema.ARQ_ROB_GERAL, "04-qualidade/rob_rob2_concordancia.csv"}
    assert _abertas(projeto_vazio) == []  # pendência fechada
    # reexecução: sem evento novo
    n = len(_eventos(projeto_vazio, "rob_consolidado"))
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--consenso", arq)
    assert codigo == 0 and resumo["reexecucao"] is True and len(_eventos(projeto_vazio, "rob_consolidado")) == n
    # fase 1 de novo com as mesmas avaliações: a resolução humana não é apagada
    codigo, resumo = _fase1_rob2(projeto_vazio, capsys)
    assert codigo == 0 and resumo["n_pendentes"] == 0
    d3 = [l for l in ler_csv(projeto_vazio / arq)[1] if (l["chave"], l["dominio"]) == ("Alves2020", "D3")][0]
    assert (d3["julgamento_consenso"], d3["resolvido_por"]) == ("algumas_preocupacoes", "revisor_humano_1")


def test_rob2_varias_preocupacoes_avisa_e_sobreposicao_so_agrava(projeto_vazio, capsys):
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_csv
    a = _escrever(projeto_vazio / "A.csv", "chave,construto_outcome,D1,D2,D3,D4,D5\n"
                                          "Dias2021,notas,algumas_preocupacoes,algumas_preocupacoes,baixo,baixo,baixo\n")
    b = _escrever(projeto_vazio / "B.csv", "chave,construto_outcome,D1,D2,D3,D4,D5\n"
                                          "Dias2021,notas,algumas_preocupacoes,algumas_preocupacoes,baixo,baixo,baixo\n")
    assert rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--a", str(a), "--b", str(b),
                 "--avaliador-a", "revisor_humano_1", "--avaliador-b", "revisor_humano_2")[0] == 0
    arq = esquema.PADRAO_ROB_CONSENSO.format(ferramenta="rob2")
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--consenso", arq)
    assert codigo == 0 and resumo["rob_geral"] == {"algumas_preocupacoes": 1}
    assert any("algumas_preocupacoes em 2 domínios" in x for x in resumo["avisos"])
    colunas, linhas = ler_csv(projeto_vazio / arq)
    base = dict(linhas[0], dominio="geral", julgamento_a="", julgamento_b="", trecho="", pagina="")
    # sobreposição para baixo é recusada
    escrever_csv(projeto_vazio / arq, colunas, linhas + [dict(base, julgamento_consenso="baixo",
                                                              resolvido_por="revisor_humano_1", justificativa="x")])
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--consenso", arq)
    assert codigo == 2 and any("menos grave que o pior domínio" in p for p in resumo["problemas"])
    # sem justificativa também
    escrever_csv(projeto_vazio / arq, colunas, linhas + [dict(base, julgamento_consenso="alto",
                                                              resolvido_por="revisor_humano_1", justificativa="")])
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--consenso", arq)
    assert codigo == 2 and any("sem justificativa" in p for p in resumo["problemas"])
    escrever_csv(projeto_vazio / arq, colunas, linhas + [dict(
        base, julgamento_consenso="alto", resolvido_por="revisor_humano_1",
        justificativa="preocupações em D1 e D2 reduzem muito a confiança")])
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--consenso", arq)
    assert codigo == 0 and resumo["rob_geral"] == {"alto": 1} and resumo["n_sobreposicoes"] == 1
    # a linha de sobreposição sobrevive a uma nova fase 1
    assert rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--a", str(a), "--b", str(b),
                 "--avaliador-a", "revisor_humano_1", "--avaliador-b", "revisor_humano_2")[0] == 0
    assert any(l["dominio"] == "geral" and l["julgamento_consenso"] == "alto"
               for l in ler_csv(projeto_vazio / arq)[1])


# ---------------------------------------------------------------------------
# ROBINS-I (formato longo, rascunho de IA), master do fichamento, checklists e EPOC
# ---------------------------------------------------------------------------
def test_robins_i_longo_com_ia_pior_dominio_e_validacao(projeto_vazio, capsys):
    from rslib import esquema
    from rslib.handoff import ler_csv
    cab = "chave,construto_outcome,dominio,julgamento,trecho,pagina\n"
    linhas_a = ["Castro2018,emprego,D1,proposta_moderado,\"controlou renda\",4",
                "Castro2018,emprego,D2,proposta_baixo,,", "Castro2018,emprego,D3,proposta_grave,,",
                "Castro2018,emprego,D4,proposta_grave,,", "Castro2018,emprego,D5,proposta_baixo,,",
                "Castro2018,emprego,D6,proposta_baixo,,"]
    linhas_b = ["Castro2018,emprego,D1,Moderate,,", "Castro2018,emprego,D2,low,,", "Castro2018,emprego,D3,serious,,",
                "Castro2018,emprego,D4,Grave,,", "Castro2018,emprego,D5,baixo,,", "Castro2018,emprego,D6,baixo,,"]
    a = _escrever(projeto_vazio / "A.csv", cab + "\n".join(linhas_a) + "\n")
    b = _escrever(projeto_vazio / "B.csv", cab + "\n".join(linhas_b) + "\n")
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "robins_i", "--a", str(a), "--b", str(b),
                           "--avaliador-a", "revisor_humano_1", "--avaliador-b", "revisor_humano_2")
    assert codigo == 0, resumo
    assert any("proposta_" in x and "conta como IA" in x for x in resumo["avisos"])
    arq = esquema.PADRAO_ROB_CONSENSO.format(ferramenta="robins_i")
    linhas = ler_csv(projeto_vazio / arq)[1]
    assert resumo["n_pendentes"] == 0
    assert linhas[0]["resolvido_por"] == "concordancia:ia_proposta_A+revisor_humano_2"
    assert linhas[0]["trecho"] == "controlou renda" and linhas[0]["pagina"] == "4"
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "robins_i", "--consenso", arq)
    assert codigo == 0, resumo
    geral = ler_csv(projeto_vazio / esquema.ARQ_ROB_GERAL)[1]
    assert [(l["rob_geral"], l["validado_humano"]) for l in geral] == [("grave", "1")]  # B é humano
    assert any("2 domínios grave" in x and "vários graves -> crítico" in x for x in resumo["avisos"])
    # os dois avaliadores sem papel humano: rob_geral sai com validado_humano = 0
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "robins_i", "--a", str(a), "--b", str(b))
    assert any("sem papel humano" in x for x in resumo["avisos"])
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "robins_i", "--consenso", arq)
    assert codigo == 0 and resumo["n_validados_humano"] == 0
    assert any("validado_humano = 0" in x for x in resumo["avisos"])


def test_master_do_fichamento_com_evidencia_e_sufixo(projeto_vazio, capsys):
    from rslib import esquema
    from rslib.handoff import ler_csv
    cab = ("ficha_id,citekey,unidade_randomizacao,unidade_randomizacao__evidencia,d1_julgamento_proposto,"
           "d1_julgamento_proposto__evidencia,d1b_julgamento_proposto,d2_julgamento_proposto,d3_julgamento_proposto,"
           "d4_julgamento_proposto,d5_julgamento_proposto,geral_julgamento_proposto,direcao_vies_proposta\n")
    a = _escrever(projeto_vazio / "A_master.csv", cab +
                  'Silva2020#desempenho,Silva2020,cluster,"""escolas sorteadas"" (p. 3)",proposta_baixo,'
                  '"""sorteio público"" (p. 4); ""envelopes"" (p. 5)",proposta_alto,proposta_baixo,proposta_baixo,'
                  'proposta_baixo,proposta_baixo,proposta_alto,imprevisivel\n')
    b = _escrever(projeto_vazio / "B.csv", "chave,construto_outcome,D1,D1b,D2,D3,D4,D5,rob_geral\n"
                                          "Silva2020,desempenho,baixo,algumas_preocupacoes,baixo,baixo,baixo,baixo,"
                                          "algumas_preocupacoes\n")
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--a", str(a), "--b", str(b),
                           "--avaliador-b", "revisor_humano_2")
    assert codigo == 0, resumo
    linhas = {l["dominio"]: l for l in ler_csv(projeto_vazio / esquema.PADRAO_ROB_CONSENSO.format(ferramenta="rob2"))[1]}
    assert set(linhas) == {"D1", "D1b", "D2", "D3", "D4", "D5"}
    assert linhas["D1"]["construto_outcome"] == "desempenho"
    assert linhas["D1"]["trecho"] == "sorteio público | envelopes" and linhas["D1"]["pagina"] == "4;5"
    assert (linhas["D1b"]["julgamento_a"], linhas["D1b"]["julgamento_b"], linhas["D1b"]["julgamento_consenso"]) == \
        ("alto", "algumas_preocupacoes", "")


def test_checklist_casp_usa_geral_do_consenso(projeto_vazio, capsys):
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_csv
    cab = "chave,Q1,Q2,Q3,preocupacao_metodologica\n"
    a = _escrever(projeto_vazio / "A.csv", cab + "Lima2022,S,S,NPD,menores\n")
    b = _escrever(projeto_vazio / "B.csv", cab + "Lima2022,Sim,N,NPD,moderadas\n")
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "casp_qualitativo", "--a", str(a), "--b", str(b),
                           "--avaliador-a", "revisor_humano_1", "--avaliador-b", "revisor_humano_2")
    assert codigo == 0 and resumo["n_pendentes"] == 2  # Q2 e geral
    arq = esquema.PADRAO_ROB_CONSENSO.format(ferramenta="casp_qualitativo")
    colunas, linhas = ler_csv(projeto_vazio / arq)
    assert {l["dominio"] for l in linhas} == {"Q1", "Q2", "Q3", "geral"} and linhas[0]["construto_outcome"] == ""
    for l in linhas:
        if not l["julgamento_consenso"]:
            l["julgamento_consenso"] = "N" if l["dominio"] == "Q2" else "moderadas"
            l["resolvido_por"] = "revisor_humano_1"
    escrever_csv(projeto_vazio / arq, colunas, linhas)
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "casp_qualitativo", "--consenso", arq)
    assert codigo == 0, resumo
    assert resumo["rob_geral"] == {"moderadas": 1}
    # sem a linha geral, checklist não tem algoritmo: código 2
    escrever_csv(projeto_vazio / arq, colunas, [l for l in linhas if l["dominio"] != "geral"])
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "casp_qualitativo", "--consenso", arq)
    assert codigo == 2 and any("não tem algoritmo" in p for p in resumo["problemas"])


def test_epoc_pior_criterio_incerto_moderado_e_ignorar_no_geral(projeto_vazio, capsys):
    from rslib import esquema
    from rslib.handoff import ler_csv
    cab = "chave,construto_outcome,cg_sequencia_aleatoria,cg_ocultacao_alocacao,cg_linha_base_outcome,cg_contaminacao\n"
    texto = cab + "Mota2019,matricula,alto,alto,incerto,baixo\n"
    a = _escrever(projeto_vazio / "A.csv", texto)
    b = _escrever(projeto_vazio / "B.csv", texto)
    argv = ["--ferramenta", "epoc", "--a", str(a), "--b", str(b), "--avaliador-a", "revisor_humano_1",
            "--avaliador-b", "revisor_humano_2"]
    assert rodar(projeto_vazio, capsys, *argv)[0] == 0
    arq = esquema.PADRAO_ROB_CONSENSO.format(ferramenta="epoc")
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "epoc", "--consenso", arq)
    assert codigo == 0 and resumo["rob_geral"] == {"alto": 1}
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "epoc", "--consenso", arq, "--ignorar-no-geral",
                           "cg_sequencia_aleatoria,cg_ocultacao_alocacao")
    assert codigo == 0 and resumo["rob_geral"] == {"moderado": 1}
    assert ler_csv(projeto_vazio / esquema.ARQ_ROB_GERAL)[1][0]["rob_geral"] == "moderado"


# ---------------------------------------------------------------------------
# Erros de uso e contrato
# ---------------------------------------------------------------------------
def test_erros_de_entrada(projeto_vazio, capsys):
    a = _escrever(projeto_vazio / "A.csv", "chave,construto_outcome,D1,D2\nX2020,y,baixo,alto\nZ2021,y,baixo,baixo\n")
    b = _escrever(projeto_vazio / "B.csv", "chave,construto_outcome,D1,D2\nX2020,y,baixo,alto\n")
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--a", str(a), "--b", str(b))
    assert codigo == 1 and "não avaliaram os mesmos" in resumo["erro"] and "Z2021" in resumo["erro"]
    b2 = _escrever(projeto_vazio / "B2.csv", "chave,construto_outcome,D1,D2\nX2020,y,baixo,muito alto\nZ2021,y,baixo,baixo\n")
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--a", str(a), "--b", str(b2))
    assert codigo == 1 and "fora do vocabulário" in resumo["erro"]
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--a", str(a))
    assert codigo == 1
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--a", str(a), "--b", str(b),
                           "--consenso", "x.csv")
    assert codigo == 1 and "não os dois" in resumo["erro"]
    ruim = _escrever(projeto_vazio / "consenso.csv", "chave,dominio\nX2020,D1\n")
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "rob2", "--consenso", str(ruim))
    assert codigo == 1 and "faltam colunas" in resumo["erro"]


def test_registrado_no_dispatcher_sem_citar_documento_interno():
    import rs
    from rs import construir_parser
    assert "rslib.qualidade" in rs.MODULOS_COMANDOS
    parser = construir_parser()
    args = parser.parse_args(["qualidade", "consolidar", "--ferramenta", "robins_i", "--consenso", "x.csv"])
    assert callable(args.func) and args.ferramenta == "robins_i"
    sub = next(a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction")
    ajuda = sub.choices["qualidade"].format_help()
    consolidar = next(a for a in sub.choices["qualidade"]._actions if a.__class__.__name__ == "_SubParsersAction")
    ajuda += consolidar.choices["consolidar"].format_help()
    for proibido in ("Apêndice B", "Apêndice C", "PLANO"):
        assert proibido not in ajuda
    from conftest import SCRIPTS
    fonte = (SCRIPTS / "rslib" / "qualidade.py").read_text(encoding="utf-8")
    assert "Apêndice B" not in fonte and "Apêndice C" not in fonte and "PLANO" not in fonte


def test_regressao_jbi_na_e_resposta_valida_e_xlsx_e_lido(projeto_vazio, capsys):
    """Regressão: normalizar.texto apagava 'NA' (item não aplicável do JBI) e a planilha xlsx não era aceita."""
    openpyxl = pytest.importorskip("openpyxl")
    from rslib import esquema
    from rslib.handoff import ler_csv
    livro = openpyxl.Workbook()
    aba = livro.active
    for linha in (["chave", "Q1", "Q2", "preocupacao_metodologica"], ["Reis2023", "NA", "S", "menores"]):
        aba.append(linha)
    a = projeto_vazio / "A.xlsx"
    livro.save(a)
    b = _escrever(projeto_vazio / "B.csv", "chave\tQ1\tQ2\tpreocupacao_metodologica\nReis2023\tNA\tSim\tMenores\n")
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "jbi_transversal", "--a", str(a), "--b", str(b),
                           "--avaliador-a", "revisor_humano_1", "--avaliador-b", "revisor_humano_2")
    assert codigo == 0, resumo
    arq = esquema.PADRAO_ROB_CONSENSO.format(ferramenta="jbi_transversal")
    linhas = {l["dominio"]: l for l in ler_csv(projeto_vazio / arq)[1]}
    assert linhas["Q1"]["julgamento_consenso"] == "NA" and resumo["n_pendentes"] == 0
    codigo, resumo = rodar(projeto_vazio, capsys, "--ferramenta", "jbi_transversal", "--consenso", arq)
    assert codigo == 0 and resumo["rob_geral"] == {"menores": 1} and resumo["n_validados_humano"] == 1


# ---------------------------------------------------------------------------
# Codebook ROBINS-I V2 (códigos oficiais) e coerência com o consolidar
# ---------------------------------------------------------------------------
def _codebook(nome):
    import csv
    from conftest import SKILL
    with open(SKILL / "assets" / "codebooks" / f"{nome}.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_regressao_robins_i_usa_codigos_oficiais_da_v2():
    import re
    oficiais = {"Y", "PY", "PN", "N", "NI", "NA", "SY", "WY", "WN", "SN"}
    usados = set()
    for l in _codebook("robins_i"):
        m = re.match(r"Responda (.*?)\. ", l["prompt"])
        if not m:
            continue
        opcoes = {o.strip().split(" ")[0] for o in m.group(1).split("|")}
        assert opcoes <= oficiais, (l["variavel"], opcoes - oficiais)
        usados |= opcoes
        assert not re.search(r"\b(S/PS|PS|SI|NF|NG|SF|SG)\b", l["prompt"]), l["variavel"]
    assert {"WN", "SN", "SY", "WY", "NI"} <= usados
    por = {l["variavel"]: l["prompt"] for l in _codebook("robins_i")}
    assert por["d4_q7_imputacao"].startswith("Responda NA | Y | PY | PN | NI.")  # sem N, como no documento oficial
    assert "Se 3.1 = SN ou 3.5 = Y/PY" in por["d3_q6_analise_corrigiu"]
    assert "B2 ou B3 = Y/PY" in por["geral_julgamento_proposto"]


def test_propostas_dos_codebooks_cabem_no_vocabulario_do_consolidar():
    import re
    from rslib.qualidade import normalizar_valor
    for ferramenta in ("rob2", "robins_i", "epoc", "casp_qualitativo", "jbi_transversal", "mmat"):
        vistos = 0
        for l in _codebook(ferramenta):
            var = l["variavel"]
            eh_geral = var in ("geral_julgamento_proposto", "preocupacao_metodologica_proposta")
            eh_dominio = var.endswith("_julgamento_proposto") or (ferramenta == "epoc" and l["prompt"].startswith("PROPOSTA"))
            if not (eh_geral or eh_dominio):
                continue
            for valor in re.findall(r"\bproposta_[a-z_]+", l["prompt"]):
                canon, proposta = normalizar_valor(ferramenta, valor, "geral" if eh_geral else "dominio")
                assert proposta and canon not in (None, "nao_se_aplica"), (ferramenta, var, valor)
                vistos += 1
        assert vistos, ferramenta


def test_avaliador_rob_documenta_codigos_da_v2_e_vocabulario_do_consenso():
    from conftest import SKILL
    texto = (SKILL / "agentes" / "avaliador-rob.md").read_text(encoding="utf-8")
    for codigo in ("`WN`", "`SN`", "`SY`", "`WY`", "`NI`", "`algumas_preocupacoes`", "`baixo_exceto_confundimento`",
                   "rs.py qualidade consolidar"):
        assert codigo in texto, codigo
    import re
    assert not re.search(r"`(NF|NG|SF|SG)`", texto)
    assert texto.count("```") % 2 == 0
