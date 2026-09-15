"""Testes de efeitos: estatística t, plausibilidade, preparação e verificação de trechos em PDF sintético."""

import argparse
import json
import math

import pytest

from test_textos import criar_pdf, escrever_unicos

CAB = ("id_efeito,ficha_id,chave,id_estudo,desenho,estimando,outcome,construto_outcome,direcao_desejada,modelo,"
       "modelo_principal,subgrupo,tipo_estatistica,m1,sd1,n1,m2,sd2,n2,t,df,f,beta,se,sdy,or_,ci_lo,ci_hi,r,p,"
       "n_total,cluster,icc,evidencia,pagina,verificado_humano")


def rodar(argv, capsys):
    from rslib import efeitos_verificar
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    sub = parser.add_subparsers(dest="comando")
    efeitos_verificar.registrar(sub)
    args = parser.parse_args(argv)
    codigo = args.func(args)
    return codigo, json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def linha(**campos):
    base = {c: "" for c in CAB.split(",")}
    base.update({"chave": "Alves2020", "tipo_estatistica": "t", "direcao_desejada": "aumentar"})
    base.update({k: str(v) for k, v in campos.items()})
    return base


def escrever_extrator(caminho, extras, linhas):
    """CSV no formato do extrator: cabeçalho do esquema + colunas extras."""
    import csv
    colunas = CAB.split(",") + list(extras)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colunas)
        w.writeheader()
        for l in linhas:
            w.writerow({c: l.get(c, "") for c in colunas})


# ---------------------------------------------------------------------------
def test_p_da_t_de_student():
    from rslib.efeitos_verificar import beta_incompleta, p_t_bicaudal
    assert p_t_bicaudal(2.228, 10) == pytest.approx(0.05, abs=5e-4)
    assert p_t_bicaudal(1.96, 1e6) == pytest.approx(0.05, abs=5e-4)
    assert p_t_bicaudal(0.0, 5) == pytest.approx(1.0)
    assert beta_incompleta(2, 3, 0.4) == pytest.approx(0.5248, abs=1e-4)
    scipy_stats = pytest.importorskip("scipy.stats")
    for t, df in [(0.5, 3), (2.1, 48), (4.7, 7), (10.0, 200)]:
        assert p_t_bicaudal(t, df) == pytest.approx(2 * scipy_stats.t.sf(t, df), rel=1e-6, abs=1e-12)


def test_ler_p():
    from rslib.efeitos_verificar import ler_p
    assert ler_p("0,03") == ("=", 0.03, 2)
    assert ler_p("p < .001") == ("<", 0.001, 3)
    assert ler_p("n.s.")[0] == "?"
    assert ler_p("") == (None, None, 0)


@pytest.mark.parametrize("campos,trecho_erro", [
    ({"sd1": "0", "tipo_estatistica": "md_sd"}, "sd1 <= 0"),
    ({"n1": "60", "n2": "50", "n_total": "100"}, "n1 + n2"),
    ({"t": "0.50", "df": "40", "p": "0.03"}, "incoerente"),
    ({"t": "5.0", "df": "50", "p": ">0.05"}, "incoerente"),
    ({"p": "1.3"}, "fora de [0, 1]"),
    ({"tipo_estatistica": "or", "or_": "-0.5"}, "OR <= 0"),
    ({"tipo_estatistica": "or", "or_": "2.5", "ci_lo": "1.1", "ci_hi": "2.0"}, "fora do IC"),
    ({"r": "1.2", "tipo_estatistica": "r", "n_total": "30"}, "|r| > 1"),
    ({"ci_lo": "0.5", "ci_hi": "0.1"}, "ci_lo > ci_hi"),
    ({"sd2": "abc"}, "não numérico"),
])
def test_plausibilidade_erros(campos, trecho_erro):
    from rslib.efeitos_verificar import checar_plausibilidade
    erros, _, _, _ = checar_plausibilidade(linha(**campos))
    assert any(trecho_erro in e for e in erros), erros


def test_plausibilidade_aceita_arredondamento_e_alertas():
    from rslib.efeitos_verificar import checar_plausibilidade, p_t_bicaudal
    # t = 2.10 com df = 48 dá p = 0,041; artigo imprime 0.04
    erros, alertas, _, p_calc = checar_plausibilidade(linha(t="2.10", df="48", p="0.04", n1="25", n2="25"))
    assert not erros and p_calc == pytest.approx(p_t_bicaudal(2.1, 48))
    erros, _, _, _ = checar_plausibilidade(linha(t="4.9", df="50", p="<0.001"))
    assert not erros
    erros, alertas, _, _ = checar_plausibilidade(linha(t="2.10", df="48", p="0.02"))
    assert not erros and any("unilateral" in a for a in alertas)
    erros, alertas, g, _ = checar_plausibilidade(linha(
        tipo_estatistica="md_sd", m1="10", sd1="1", n1="20", m2="7", sd2="1", n2="20", n_total="40"))
    assert not erros and g > 2 and any("|g|" in a for a in alertas)
    assert g == pytest.approx((1 - 3 / (4 * 40 - 9)) * 3.0)
    _, alertas, _, _ = checar_plausibilidade(linha(tipo_estatistica="md_sd", m1="1"))
    assert any("insuficientes" in a for a in alertas)
    erros, alertas, _, _ = checar_plausibilidade(linha(t="2.10", n1="25", n2="25", p="0.04"))
    assert not erros and any("df inferido" in a for a in alertas)
    _, _, g_or, _ = checar_plausibilidade(linha(tipo_estatistica="or", or_="3.0", ci_lo="1.5", ci_hi="6"))
    assert g_or == pytest.approx(math.log(3) * math.sqrt(3) / math.pi)


# ---------------------------------------------------------------------------
def test_preparar_efeitos(projeto_vazio, capsys):
    from rslib import esquema, estado
    from rslib.efeitos_verificar import ARQ_AVISOS_PREPARACAO
    from rslib.handoff import ler_csv, escrever_csv
    escrever_unicos(projeto_vazio, ["Alves2020", "Borges2019", "Castro2018"])
    cols, unicos = ler_csv(projeto_vazio / esquema.ARQ_UNICOS)
    unicos[1]["id_estudo"] = "ES0001"  # Borges2019 é relato do mesmo estudo de Alves2020
    escrever_csv(projeto_vazio / esquema.ARQ_UNICOS, cols, unicos)
    pasta = projeto_vazio / "05-decomposicao/efeitos"
    pasta.mkdir(parents=True, exist_ok=True)  # já criada pelo layout (esquema.PASTAS_PROJETO)
    (pasta / "Alves2020.csv").write_text(CAB + "\n" + ",Alves2020,Alves2020,,,itt,attendance,frequencia,Aumentar,T3c1,sim,,"
                                         "T,,,,,,,\"2,10\",48,,,,,,,,,0.04,50,,,\"treatment increased attendance\",2,\n"
                                         + ",Alves2020,Alves2020,,,ITT,attendance,frequencia,aumentar,T3c2,sim,,t,,,,,,,1.5,48,"
                                         ",,,,,,,,0.14,50,,,\"robustness\",3,\n", encoding="utf-8")
    (pasta / "Borges2019.csv").write_text(CAB + ",coluna_extra\n" + "Borges2019-E01,,Borges2019,,,ATE,grades,notas,reduzir,"
                                          "M1,sim,,md_sd,1,2,30,2,2,30,,,,,,,,,,,,60,,,\"table 2\",4,,x\n", encoding="utf-8")
    master = projeto_vazio / "master.csv"
    master.write_text("ficha_id,citekey,tipo_estudo,n_fichas_do_texto\nAlves2020,Alves2020,b2,1\n"
                      "Borges2019,Borges2019,b2,1\n", encoding="utf-8")
    codebook = projeto_vazio / "codebook.csv"
    codebook.write_text("dimensao,variavel,descricao,prompt,tipo,aplicavel_se\nM,tipo_estudo,d,p,categorica,\n"
                        "E,estimador,d,p,categorica,tipo_estudo=b2\n", encoding="utf-8")
    argv = ["--dir", str(projeto_vazio), "analise", "preparar-efeitos", "--master", str(master), "--codebook", str(codebook)]
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 0, resumo
    colunas, linhas = ler_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS)
    # colunas extras preservadas depois das do esquema
    assert colunas == esquema.COLUNAS_EFEITOS_EXTRAIDOS + ["coluna_extra"] and len(linhas) == 3
    assert resumo["colunas_extras"] == ["coluna_extra"]
    d = {l["id_efeito"]: l for l in linhas}
    assert set(d) == {"Alves2020-E01", "Alves2020-E02", "Borges2019-E01"}
    assert d["Borges2019-E01"]["coluna_extra"] == "x" and d["Alves2020-E01"]["coluna_extra"] == ""
    a = d["Alves2020-E01"]
    assert (a["t"], a["tipo_estatistica"], a["direcao_desejada"], a["estimando"]) == ("2.10", "t", "aumentar", "ITT")
    # o master só tem o classificador a1/a2/b1/b2: desenho fica vazio, com aviso (antes virava "b2")
    assert a["id_estudo"] == "ES0001" and a["desenho"] == ""
    assert d["Borges2019-E01"]["id_estudo"] == "ES0001"
    _, avisos = ler_csv(projeto_vazio / ARQ_AVISOS_PREPARACAO)
    assert any(p["campo"] == "desenho" and "classificador" in p["problema"] for p in avisos)
    assert any(p["campo"] == "desenho" and p["id_efeito"] == "Alves2020-E01" for p in avisos)
    assert resumo["n_desenho_vazio"] == 3
    assert any(p["campo"] == "modelo_principal" for p in avisos)  # dois modelos principais no mesmo estudo × outcome
    assert estado.ler_log(projeto_vazio)[-1]["evento"] == "extracao_consolidada"

    # verificação humana preservada ao reprocessar
    cols, linhas = ler_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS)
    for l in linhas:
        l["verificado_humano"] = "sim"
    escrever_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS, cols, linhas)
    codigo, _ = rodar(argv, capsys)
    assert codigo == 0
    assert {l["verificado_humano"] for l in ler_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS)[1]} == {"sim"}

    # se o extrator mudar um número, a verificação daquele efeito não é herdada
    bruto = (pasta / "Borges2019.csv").read_text(encoding="utf-8").replace("md_sd,1,2,30", "md_sd,1,3,30")
    (pasta / "Borges2019.csv").write_text(bruto, encoding="utf-8")
    codigo, _ = rodar(argv, capsys)
    d = {l["id_efeito"]: l["verificado_humano"] for l in ler_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS)[1]}
    assert codigo == 0 and d == {"Alves2020-E01": "sim", "Alves2020-E02": "sim", "Borges2019-E01": ""}


def test_preparar_preserva_extras_e_desenho_pela_estrategia(projeto_vazio, capsys):
    """Regressão: preparar-efeitos descartava familia_intervencao/rob_geral/moderadores e punha 'b2' em desenho."""
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_csv
    escrever_unicos(projeto_vazio, ["Alves2020", "Borges2019", "Castro2018"])
    pasta = projeto_vazio / "05-decomposicao/efeitos"
    base = dict(modelo_principal="sim", modelo="M1", direcao_desejada="aumentar", pagina="2", evidencia="trecho")
    escrever_extrator(pasta / "Alves2020.csv", ["familia_intervencao", "rob_geral", "Classe_Desenho", "nivel_ensino"], [
        dict(base, ficha_id="Alves2020", chave="Alves2020", estimando="ITT", outcome="freq",
             construto_outcome="frequencia", tipo_estatistica="t", n1="30", n2="30", t="2.1", df="58",
             familia_intervencao="TCR", rob_geral="Crítico", Classe_Desenho="randomizado", nivel_ensino="fundamental")])
    escrever_extrator(pasta / "Borges2019.csv", ["q1_1", "q3_1", "q1_2", "q3_2", "rob_geral"], [
        dict(base, ficha_id="Borges2019#b2", chave="Borges2019", estimando="ATE", outcome="nota",
             construto_outcome="notas", tipo_estatistica="mediana_iqr", m1="12", n1="25", m2="10", n2="40",
             n_total="65", q1_1="9", q3_1="16", q1_2="7", q3_2="12", rob_geral="baixo")])
    escrever_extrator(pasta / "Castro2018.csv", [], [
        dict(base, chave="Castro2018", desenho="RDD", estimando="RDD_local", outcome="freq",
             construto_outcome="frequencia", tipo_estatistica="t", n1="50", n2="50", t="1.9", df="98")])
    master = projeto_vazio / "master.csv"
    master.write_text("ficha_id,citekey,tipo_estudo,b2_estrategia_identificacao\n"
                      "Alves2020,Alves2020,b2,experimento_aleatorizado_individual\n"
                      "Borges2019#b2,Borges2019,b2,diferencas_em_diferencas\n"
                      "Castro2018,Castro2018,b2,999\n", encoding="utf-8")
    codebook = projeto_vazio / "codebook.csv"
    codebook.write_text("dimensao,variavel,descricao,prompt,tipo,aplicavel_se\nM,tipo_estudo,d,p,categorica,\n"
                        "B2,b2_estrategia_identificacao,d,p,categorica,tipo_estudo=b2\n", encoding="utf-8")
    argv = ["--dir", str(projeto_vazio), "analise", "preparar-efeitos", "--master", str(master),
            "--codebook", str(codebook)]
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 0, resumo
    colunas, linhas = ler_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS)
    assert colunas[:len(esquema.COLUNAS_EFEITOS_EXTRAIDOS)] == esquema.COLUNAS_EFEITOS_EXTRAIDOS
    assert colunas[len(esquema.COLUNAS_EFEITOS_EXTRAIDOS):] == ["familia_intervencao", "rob_geral", "classe_desenho",
                                                                "nivel_ensino", "q1_1", "q3_1", "q1_2", "q3_2"]
    d = {l["chave"]: l for l in linhas}
    assert (d["Alves2020"]["familia_intervencao"], d["Alves2020"]["rob_geral"], d["Alves2020"]["nivel_ensino"]) == \
        ("TCR", "Crítico", "fundamental")
    assert (d["Borges2019"]["q1_1"], d["Borges2019"]["q3_2"], d["Borges2019"]["rob_geral"]) == ("9", "12", "baixo")
    assert d["Castro2018"]["familia_intervencao"] == ""
    # desenho pela estratégia de identificação (por ficha_id); valor do extrator tem precedência; 999 = ausente
    assert d["Alves2020"]["desenho"] == "experimento_aleatorizado_individual"
    assert d["Borges2019"]["desenho"] == "diferencas_em_diferencas"
    assert d["Castro2018"]["desenho"] == "RDD"

    # coluna acrescentada à mão no consolidado sobrevive ao reprocessamento (se os dados não mudaram)
    for l in linhas:
        l["moderador_manual"] = "sim" if l["chave"] == "Alves2020" else ""
    escrever_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS, colunas + ["moderador_manual"], linhas)
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 0
    colunas2, linhas2 = ler_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS)
    assert colunas2[-1] == "moderador_manual"
    assert {l["chave"]: l["moderador_manual"] for l in linhas2}["Alves2020"] == "sim"

    # quartis entram na impressão do efeito: mudar q3_2 descarta a verificação humana daquele efeito
    for l in linhas2:
        l["verificado_humano"] = "sim"
    escrever_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS, colunas2, linhas2)
    bruto = (pasta / "Borges2019.csv").read_text(encoding="utf-8").replace(",9,16,7,12,", ",9,16,7,13,")
    (pasta / "Borges2019.csv").write_text(bruto, encoding="utf-8")
    codigo, _ = rodar(argv, capsys)
    assert codigo == 0
    verif = {l["chave"]: l["verificado_humano"] for l in ler_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS)[1]}
    assert verif == {"Alves2020": "sim", "Borges2019": "", "Castro2018": "sim"}


def test_desenho_do_master_nunca_usa_classificador(tmp_path):
    from rslib.efeitos_verificar import coluna_desenho_master
    codebook = tmp_path / "codebook.csv"
    codebook.write_text("dimensao,variavel,descricao,prompt,tipo,aplicavel_se\nM,desenho,d,p,categorica,\n"
                        "B,meu_bloco_estrategia_identificacao,d,p,categorica,desenho=b2\n", encoding="utf-8")
    # 'desenho' é o classificador neste codebook: usa a variável de estratégia
    assert coluna_desenho_master(["desenho", "meu_bloco_estrategia_identificacao"], codebook) == \
        "meu_bloco_estrategia_identificacao"
    assert coluna_desenho_master(["tipo_estudo"], None) is None
    assert coluna_desenho_master(["tipo_estudo", "metodo_sms"], None) == "metodo_sms"


def test_mann_whitney_nao_exige_p_com_z():
    """Regressão: REQUISITOS['mann_whitney'] exigia p e gerava alerta espúrio com o z na coluna t."""
    from rslib.efeitos_verificar import checar_plausibilidade
    _, alertas, _, _ = checar_plausibilidade(linha(tipo_estatistica="mann_whitney", t="-2.151", n1="25", n2="35"))
    assert not any("insuficientes" in a for a in alertas), alertas
    _, alertas, _, _ = checar_plausibilidade(linha(tipo_estatistica="mann_whitney", p="0.03", n_total="60"))
    assert not any("insuficientes" in a for a in alertas), alertas
    _, alertas, _, _ = checar_plausibilidade(linha(tipo_estatistica="mann_whitney", n1="25", n2="35"))
    assert any("faltam t ou p" in a for a in alertas), alertas
    _, alertas, _, _ = checar_plausibilidade(linha(tipo_estatistica="r", r="0.3", n1="30", n2="90"))
    assert not any("insuficientes" in a for a in alertas), alertas
    med = dict(tipo_estatistica="mediana_iqr", m1="12", m2="10", n1="25", n2="40")
    _, alertas, _, _ = checar_plausibilidade(linha(**med, q1_1="9", q3_1="16", q1_2="7", q3_2="12"))
    assert not any("insuficientes" in a for a in alertas), alertas
    _, alertas, _, _ = checar_plausibilidade(linha(**med))
    assert any("q1_1+q3_1+q1_2+q3_2 ou sd1+sd2" in a for a in alertas), alertas
    erros, _, _, _ = checar_plausibilidade(linha(**med, q1_1="13", q3_1="16", q1_2="12", q3_2="7"))
    assert "mediana m1 fora de [q1_1, q3_1]" in erros and "q1_2 >= q3_2" in erros, erros


def test_preparar_recusa_revisao_e_invalidos(projeto_vazio, capsys):
    from rslib import esquema
    from rslib.handoff import ler_csv, escrever_csv
    escrever_unicos(projeto_vazio, ["Alves2020", "Borges2019"])
    cols, unicos = ler_csv(projeto_vazio / esquema.ARQ_UNICOS)
    unicos[1]["tipo_publicacao"] = "revisao"
    escrever_csv(projeto_vazio / esquema.ARQ_UNICOS, cols, unicos)
    entrada = projeto_vazio / "efeitos.csv"
    entrada.write_text(CAB + "\n" + ",,Borges2019,,,,x,x,aumentar,,sim,,g,,,,,,,,,,,,,,,,,,,,,,,\n"
                       + ",,Alves2020,,meta-analysis,,x,x,aumentar,,sim,,g,,,,,,,,,,,,,,,,,,,,,,,\n"
                       + ",,Zzz1999,,,,x,x,subir,,sim,,qualquer,,,,,,,,,,,,,,,,,,,,,,,\n", encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "analise", "preparar-efeitos", "--entrada", str(entrada)], capsys)
    assert codigo == 1
    problemas = {(e["chave"], e["campo"]) for e in resumo["erros"]}
    assert ("Borges2019", "desenho") in problemas and ("Alves2020", "desenho") in problemas
    assert ("Zzz1999", "chave") in problemas
    assert not (projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS).exists()


# ---------------------------------------------------------------------------
TEXTO_P2 = ("Results. The treatment increased attendance by 0.45 standard deviations "
            "(t = 2.10, p = 0.04) in municipal schools. Robustness checks follow in Table 3.")


def preparar_verificacao(raiz, linhas_efeito, com_texto=True):
    from rslib import esquema
    from rslib.handoff import escrever_csv
    escrever_unicos(raiz, ["Alves2020", "Borges2019"])
    criar_pdf(raiz / "03-textos/pdfs/Alves2020.pdf",
              ["Introduction page with background.", TEXTO_P2, "Table 3: robustness estimates 1.50 (0.90)."])
    criar_pdf(raiz / "03-textos/pdfs/Borges2019.pdf", ["", ""])
    escrever_csv(raiz / esquema.ARQ_EFEITOS_EXTRAIDOS, esquema.COLUNAS_EFEITOS_EXTRAIDOS, linhas_efeito)


def test_verificar_efeitos_trechos_e_g7(projeto_vazio, capsys):
    from rslib import esquema, estado
    from rslib.efeitos_verificar import ARQ_VERIFICACAO_EFEITOS
    from rslib.handoff import escrever_csv, ler_csv
    efeitos = [
        linha(id_efeito="E01", t="2.10", df="48", p="0.04", pagina="2",
              evidencia="The treatment increased attendance by 0.45 standard deviations (t = 2.10, p = 0.04)"),
        linha(id_efeito="E02", t="2.10", df="48", p="0.04", pagina="1", evidencia="increased attendance by 0.45"),
        linha(id_efeito="E03", t="2.10", df="48", p="0.04", pagina="2", evidencia="decreased attendance by 0.99"),
        linha(id_efeito="E04", t="2.10", df="48", p="0.04", pagina="2",
              evidencia="The treatment increased ... in municipal schools"),
        linha(id_efeito="E05", chave="Borges2019", tipo_estatistica="md_sd", m1="1", sd1="1", n1="10", m2="0",
              sd2="1", n2="10", pagina="1", evidencia="scanned table"),
        linha(id_efeito="E06", t="0.50", df="48", p="0.03", pagina="3", evidencia="robustness estimates 1.50"),
    ]
    preparar_verificacao(projeto_vazio, efeitos)
    est = estado.carregar_estado(projeto_vazio)
    est["modo"]["autonomia"] = "autopiloto"
    estado.salvar_estado(projeto_vazio, est)
    argv = ["--dir", str(projeto_vazio), "analise", "verificar-efeitos", "--sem-irma"]
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 2
    colunas, linhas = ler_csv(projeto_vazio / ARQ_VERIFICACAO_EFEITOS)
    v = {l["id_efeito"]: l for l in linhas}
    assert v["E01"]["status_trecho"] == "OK" and v["E01"]["erros"] == ""
    assert v["E02"]["status_trecho"] == "PAGINA_ERRADA" and v["E02"]["pagina_encontrada"] == "2"
    assert v["E03"]["status_trecho"] == "NAO_ENCONTRADA"
    assert v["E04"]["status_trecho"] == "OK"  # reticências conferidas por partes
    assert v["E05"]["status_trecho"] == "PDF_TEXTO_NAO_EXTRAIVEL" and "visual" in v["E05"]["alertas"]
    assert v["E06"]["status_trecho"] == "OK" and "incoerente" in v["E06"]["erros"]
    assert all(l["apto_g7"] == "0" for l in linhas) and resumo["pode_seguir_g7"] is False
    assert set(resumo["falhas_trecho"]) == {"E02", "E03"} and resumo["erros_plausibilidade"] == ["E06"]
    assert resumo["pendencia"] and estado.ler_log(projeto_vazio)[-1]["evento"] in ("efeitos_verificados", "pendencia_aberta")

    # corrigido e verificado por humano: segue para o G7
    corrigidos = [efeitos[0], dict(efeitos[1], pagina="2"), dict(efeitos[4]),
                  dict(efeitos[5], t="2.10", p="0.04")]
    for c in corrigidos:
        c["verificado_humano"] = "sim"
    escrever_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS, esquema.COLUNAS_EFEITOS_EXTRAIDOS, corrigidos)
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 0, resumo
    assert resumo["pode_seguir_g7"] is True and resumo["n_nao_aptos_g7"] == 0


def test_verificar_usa_gate_da_irma(projeto_vazio, capsys, tmp_path, monkeypatch):
    from rslib import efeitos_verificar
    irma = tmp_path / "fichamento-sistematico" / "scripts"
    irma.mkdir(parents=True)
    (irma / "verify_citacoes.py").write_text(
        "import pymupdf\n"
        "def extrair_paginas(p):\n    with pymupdf.open(p) as d:\n        return [x.get_text('text') for x in d]\n"
        "def normalizar(t):\n    return ' '.join(t.lower().split())\n", encoding="utf-8")
    monkeypatch.setattr(efeitos_verificar, "localizar_skill_irma", lambda nome, arq=None: irma.parent)
    preparar_verificacao(projeto_vazio, [linha(id_efeito="E01", t="2.10", df="48", p="0.04", pagina="2",
                                               evidencia="increased attendance by 0.45", verificado_humano="1")])
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "analise", "verificar-efeitos"], capsys)
    assert codigo == 0 and resumo["verificador"] == "verify_citacoes" and resumo["pode_seguir_g7"] is True


def test_ler_paginas_indicadas():
    from rslib.efeitos_verificar import ler_paginas_indicadas
    assert ler_paginas_indicadas("12") == [12]
    assert ler_paginas_indicadas("p. 12-14") == [12, 13, 14]
    assert ler_paginas_indicadas("4; 6") == [4, 6]
    assert ler_paginas_indicadas("") == []


def test_preparar_efeitos_id_estudo_vazio_usa_convencao_es(projeto_vazio, capsys):
    """Regressão: registro sem id_estudo caía para o id_rs ("RS0002"); a convenção é esquema.id_estudo_de."""
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_csv
    escrever_unicos(projeto_vazio, ["Alves2020", "Borges2019"])
    cols, unicos = ler_csv(projeto_vazio / esquema.ARQ_UNICOS)
    for u in unicos:
        u["id_estudo"] = ""
    escrever_csv(projeto_vazio / esquema.ARQ_UNICOS, cols, unicos)
    (projeto_vazio / "05-decomposicao/efeitos/Borges2019.csv").write_text(
        CAB + "\n,,Borges2019,,RCT,ATE,notas,notas,aumentar,M1,sim,,t,,,30,,,30,2.0,58,,,,,,,,,,,60,,,\"t = 2.0\",4,\n",
        encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "analise", "preparar-efeitos"], capsys)
    assert codigo == 0, resumo
    linha = ler_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS)[1][0]
    assert linha["id_estudo"] == "ES0002"


def test_gate_da_irma_nao_grava_pycache_na_pasta_da_irma(tmp_path, monkeypatch):
    """Regressão: `verificar-efeitos` criava fichamento-sistematico/scripts/__pycache__ ao importar o gate."""
    from rslib import efeitos_verificar
    scripts = tmp_path / "skills" / "fichamento-sistematico" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "verify_citacoes.py").write_text(
        "def normalizar(t):\n    return t.lower()\n\ndef extrair_paginas(p):\n    return ['x']\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_SKILL_DIR", str(tmp_path / "skills" / "revisao-sistematica"))
    modulo = efeitos_verificar.carregar_gate_irma()
    assert modulo is not None and modulo.normalizar("ABC") == "abc"
    assert not (scripts / "__pycache__").exists()


def test_regressao_pendencia_verificacao_atualiza_n_e_fecha_sozinha(projeto_vazio, capsys):
    """verificacao_humana_efeitos: n acompanha as linhas não aptas (sem duplicar) e fecha quando todas ficam aptas."""
    from rslib import esquema, estado
    from rslib.handoff import escrever_csv
    boa = "The treatment increased attendance by 0.45 standard deviations (t = 2.10, p = 0.04)"
    efeitos = [linha(id_efeito=f"E0{i}", t="2.10", df="48", p="0.04", pagina="2", evidencia=boa) for i in (1, 2, 3)]
    preparar_verificacao(projeto_vazio, efeitos)
    est = estado.carregar_estado(projeto_vazio)
    est["modo"]["autonomia"] = "autopiloto"
    estado.salvar_estado(projeto_vazio, est)
    argv = ["--dir", str(projeto_vazio), "analise", "verificar-efeitos", "--sem-irma"]

    def abertas():
        return [p for p in estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))
                if p["tipo"] == esquema.PENDENCIA_VERIFICACAO_HUMANA_EFEITOS]

    codigo, r1 = rodar(argv, capsys)
    assert codigo == 0 and r1["n_nao_aptos_g7"] == 3 and [p["n"] for p in abertas()] == [3]
    codigo, r1b = rodar(argv, capsys)
    assert r1b["pendencia"] == r1["pendencia"] and len(abertas()) == 1

    efeitos[0]["verificado_humano"] = "sim"
    escrever_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS, esquema.COLUNAS_EFEITOS_EXTRAIDOS, efeitos)
    codigo, r2 = rodar(argv, capsys)
    assert r2["n_nao_aptos_g7"] == 2 and r2["pendencia"] != r1["pendencia"]
    assert [(p["id"], p["n"]) for p in abertas()] == [(r2["pendencia"], 2)]

    for e in efeitos:
        e["verificado_humano"] = "sim"
    escrever_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS, esquema.COLUNAS_EFEITOS_EXTRAIDOS, efeitos)
    codigo, r3 = rodar(argv, capsys)
    assert codigo == 0 and r3["pode_seguir_g7"] is True and r3["pendencia"] is None and abertas() == []
    fechamento = [e for e in estado.ler_log(projeto_vazio) if e["evento"] == "pendencia_fechada"][-1]
    assert fechamento["dados"]["pendencia"] == r2["pendencia"] and fechamento["ator"]["tipo"] == "script"
    assert "aptas" in fechamento["motivo"]
    # o G7 não acusa mais pendência aberta dessa verificação
    from rslib import projeto
    est = estado.carregar_estado(projeto_vazio)
    bloqueios, _ = projeto.checar_portao(projeto_vazio, est, "G7", estado.ler_log(projeto_vazio))
    assert not [b for b in bloqueios if b["tipo"] in ("pendencia", "verificacao")], bloqueios


def test_regressao_parcial_r_m_preditores_plausibilidade():
    from rslib.efeitos_verificar import CAMPOS_NUMERICOS_EXTRAS, checar_plausibilidade
    assert "m_preditores" in CAMPOS_NUMERICOS_EXTRAS
    _, alertas, _, _ = checar_plausibilidade(linha(tipo_estatistica="parcial_r", t="2.5", df="74", n_total="80"))
    assert any("sem m_preditores" in a and "parcial_r_d_gl" in a for a in alertas), alertas
    erros, alertas, _, _ = checar_plausibilidade(linha(tipo_estatistica="parcial_r", t="2.5", df="74", n_total="80",
                                                       m_preditores="5"))
    assert not erros and not any("m_preditores" in a for a in alertas), (erros, alertas)
    _, alertas, _, _ = checar_plausibilidade(linha(tipo_estatistica="parcial_r", t="2.5", df="60", n_total="80",
                                                   m_preditores="5"))
    assert any("difere de n − m_preditores − 1" in a for a in alertas), alertas
    erros, _, _, _ = checar_plausibilidade(linha(tipo_estatistica="parcial_r", t="2.5", n_total="5", m_preditores="4"))
    assert any("<= 0" in e for e in erros), erros
    erros, _, _, _ = checar_plausibilidade(linha(tipo_estatistica="parcial_r", t="2.5", n_total="80",
                                                 m_preditores="2.5"))
    assert any("inteiro" in e for e in erros), erros


# ---------------------------------------------------------------------------
# Regressões: desfecho binário (dif_prop, rr) em avaliação de políticas
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("campos,trecho_erro", [
    ({"tipo_estatistica": "dif_prop", "p0": "40", "efeito_pp": "5", "se_pp": "2"}, "parece percentual"),
    ({"tipo_estatistica": "dif_prop", "p0": "0.97", "efeito_pp": "5", "se_pp": "2"}, "fora de (0, 1)"),
    ({"tipo_estatistica": "dif_prop", "p0": "0.4", "efeito_pp": "0.05", "p1": "0.45"}, "incoerente com efeito_pp"),
    ({"tipo_estatistica": "dif_prop", "p0": "0.4", "efeito_pp": "5", "se_pp": "0"}, "se_pp <= 0"),
    ({"tipo_estatistica": "dif_prop", "p0": "0.4", "efeito_pp": "150"}, "|efeito_pp| > 100"),
    ({"tipo_estatistica": "dif_prop", "p0": "0.4", "p1": "-0.2", "n1": "10", "n2": "10"}, "p1 fora de (0, 1)"),
    ({"tipo_estatistica": "dif_prop", "p0": "0.4", "p1": "45", "n1": "10", "n2": "10"}, "p1 = 45 parece percentual"),
    ({"tipo_estatistica": "rr", "or_": "3", "ci_lo": "2", "ci_hi": "4", "p0": "0.5"}, "RR·p0"),
    ({"tipo_estatistica": "rr", "or_": "-1", "p0": "0.2"}, "RR <= 0"),
    ({"tipo_estatistica": "rr", "or_": "1.25", "ci_lo": "1.3", "ci_hi": "1.5", "p0": "0.2"}, "fora do IC"),
    ({"tipo_estatistica": "dif_prop", "p0": "0.4", "efeito_pp": "5", "ci_lo": "6", "ci_hi": "9"}, "fora do IC"),
    ({"tipo_estatistica": "dif_prop", "p0": "abc", "efeito_pp": "5"}, "p0 não numérico"),
])
def test_regressao_binario_plausibilidade_erros(campos, trecho_erro):
    from rslib.efeitos_verificar import checar_plausibilidade
    erros, _, _, _ = checar_plausibilidade(linha(**campos))
    assert any(trecho_erro in e for e in erros), erros


def test_regressao_binario_aceita_valores_validos_e_calcula_g_aproximado():
    from rslib.efeitos_verificar import CAMPOS_NUMERICOS_EXTRAS, TIPOS_ESTATISTICA, checar_plausibilidade
    assert {"dif_prop", "rr"} <= set(TIPOS_ESTATISTICA)
    assert CAMPOS_NUMERICOS_EXTRAS[-4:] == ["p0", "p1", "efeito_pp", "se_pp"]
    erros, alertas, g, _ = checar_plausibilidade(linha(tipo_estatistica="dif_prop", p0="0.40", efeito_pp="5",
                                                       se_pp="2", ci_lo="1.1", ci_hi="8.9"))
    assert not erros and not any("insuficientes" in a for a in alertas), (erros, alertas)
    assert g == pytest.approx((math.log(0.45 / 0.55) - math.log(0.4 / 0.6)) * math.sqrt(3) / math.pi)
    # p1 e efeito_pp coerentes dentro do arredondamento
    erros, _, _, _ = checar_plausibilidade(linha(tipo_estatistica="dif_prop", p0="0.40", p1="0.45", efeito_pp="5.3",
                                                 n1="300", n2="300"))
    assert not erros, erros
    erros, alertas, g_rr, _ = checar_plausibilidade(linha(tipo_estatistica="rr", or_="1.25", ci_lo="1.05",
                                                          ci_hi="1.49", p0="0.4"))
    assert not erros and not any("insuficientes" in a for a in alertas)
    assert g_rr == pytest.approx(math.log(1.5) * math.sqrt(3) / math.pi)
    _, alertas, _, _ = checar_plausibilidade(linha(tipo_estatistica="dif_prop", p0="0.4", efeito_pp="5"))
    assert any("faltam se_pp ou ci_lo+ci_hi ou n1+n2 ou n_total" in a for a in alertas), alertas
    _, alertas, _, _ = checar_plausibilidade(linha(tipo_estatistica="rr", or_="1.2", se="0.1"))
    assert any("faltam p0" in a for a in alertas), alertas


def test_regressao_preparar_normaliza_e_guarda_colunas_binarias(projeto_vazio, capsys):
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_csv
    escrever_unicos(projeto_vazio, ["Alves2020"])
    pasta = projeto_vazio / "05-decomposicao/efeitos"
    extras = ["q1_1", "q3_1", "q1_2", "q3_2", "m_preditores", "p0", "p1", "efeito_pp", "se_pp", "familia_intervencao"]
    escrever_extrator(pasta / "Alves2020.csv", extras, [
        dict(chave="Alves2020", desenho="DiD", estimando="ATT", outcome="evasão", construto_outcome="evasao",
             direcao_desejada="reduzir", modelo="Tabela 2 col. 3", modelo_principal="sim", tipo_estatistica="dif_prop",
             p0="0,40", efeito_pp="-3,2", se_pp="1,1", evidencia="-3.2 (1.1)", pagina="7",
             familia_intervencao="TCR")])
    argv = ["--dir", str(projeto_vazio), "analise", "preparar-efeitos"]
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 0, resumo
    colunas, linhas = ler_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS)
    assert colunas[len(esquema.COLUNAS_EFEITOS_EXTRAIDOS):] == extras  # ordem do extrator: depois de m_preditores
    assert (linhas[0]["p0"], linhas[0]["efeito_pp"], linhas[0]["se_pp"]) == ("0.40", "-3.2", "1.1")
    # mudar se_pp descarta a verificação humana (a coluna entra na impressão do efeito)
    linhas[0]["verificado_humano"] = "sim"
    escrever_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS, colunas, linhas)
    bruto = (pasta / "Alves2020.csv").read_text(encoding="utf-8").replace('"1,1"', '"1,3"')
    (pasta / "Alves2020.csv").write_text(bruto, encoding="utf-8")
    codigo, _ = rodar(argv, capsys)
    assert codigo == 0
    assert ler_csv(projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS)[1][0]["verificado_humano"] == ""


def test_regressao_extrator_documenta_colunas_binarias_depois_de_m_preditores():
    from conftest import SKILL
    texto = (SKILL / "agentes" / "extrator-efeitos.md").read_text(encoding="utf-8")
    cabecalho = next(l for l in texto.splitlines() if l.startswith("id_efeito,ficha_id,"))
    assert cabecalho.endswith(",verificado_humano,q1_1,q3_1,q1_2,q3_2,m_preditores,p0,p1,efeito_pp,se_pp")
    for termo in ("dif_prop", "`rr`", "efeito_pp", "se_pp", "depois de `se_pp`"):
        assert termo in texto, termo
    import csv
    mapa = SKILL / "assets" / "mapas" / "conversoes_efeito.csv"
    with open(mapa, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    ids = {l["formula_id"]: l for l in linhas}
    assert {"dif_prop_contagens", "dif_prop_lpm", "rr_logit"} <= set(ids)
    assert ids["dif_prop_lpm"]["aproximado"] == "1" and ids["dif_prop_contagens"]["aproximado"] == "0"
    assert not any("base de conhecimento" in l["fonte"] or "cap. 07" in (l["fonte"] + l["avisos"]) for l in linhas)


# ---------------------------------------------------------------------------
# v1.3: projeto parcial de meta-análise sem PDFs
# ---------------------------------------------------------------------------
def _parcial_meta(raiz):
    from rslib import esquema, estado
    est = estado.carregar_estado(raiz)
    est["projeto"]["parcial"] = "meta"
    manter = {"00_configuracao", "10_sintese"}
    est["projeto"]["etapas_ignoradas"] = [e for e in esquema.ETAPAS if e not in manter]
    for e in est["projeto"]["etapas_ignoradas"]:
        est["etapas"][e]["status"] = "ignorada"
    estado.salvar_estado(raiz, est)


def test_regressao_parcial_meta_sem_pdfs_nao_sugere_verificar_efeitos(projeto_vazio, capsys):
    from rslib import efeitos_verificar
    raiz = projeto_vazio
    _parcial_meta(raiz)
    entrada = raiz / "05-decomposicao" / "efeitos" / "usuario.csv"
    escrever_extrator(entrada, [], [
        linha(chave="Silva2019", t="2.1", df="58", n1="30", n2="30", evidencia="planilha do usuário, linha 2",
              verificado_humano="sim"),
        linha(chave="Souza2020", id_efeito="E2", t="1.2", df="40", n1="21", n2="21",
              evidencia="planilha do usuário, linha 3")])
    assert efeitos_verificar.projeto_parcial_sem_pdfs(raiz) is True
    codigo, resumo = rodar(["--dir", str(raiz), "analise", "preparar-efeitos", "--entrada", str(entrada)], capsys)
    assert codigo == 0, resumo
    assert resumo["proximo_passo"] == "rs.py analise efeitos" and resumo["sem_pdfs"] is True
    assert resumo["n_nao_verificados_humano"] == 1
    aviso = " ".join(resumo["avisos"])
    assert "não foram verificados contra os PDFs" in aviso and "1 de 2" in aviso and "relato" in aviso

    # com PDF no projeto, volta a valer a verificação na página
    criar_pdf(raiz / "03-textos" / "pdfs" / "Silva2019.pdf", ["Resultados: t = 2.1"])
    assert efeitos_verificar.projeto_parcial_sem_pdfs(raiz) is False
    codigo, resumo = rodar(["--dir", str(raiz), "analise", "preparar-efeitos", "--entrada", str(entrada)], capsys)
    assert resumo["proximo_passo"] == "rs.py analise verificar-efeitos" and resumo["avisos"] == []


def test_projeto_completo_continua_sugerindo_verificar_efeitos(projeto_vazio):
    from rslib import efeitos_verificar
    assert efeitos_verificar.projeto_parcial_sem_pdfs(projeto_vazio) is False
