"""Testes da caixa de ferramentas: regras de rótulo (caixa-3), painel por família × construto, testes combinados
ignorados e fontes por célula."""

import argparse
import json
import re

import pytest

from conftest import FIXTURES

FIX = FIXTURES / "caixa"


def rodar(argv, capsys):
    from rslib import caixa
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    sub = parser.add_subparsers(dest="comando")
    caixa.registrar(sub)
    args = parser.parse_args(argv)
    codigo = args.func(args)
    return codigo, json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def meta(lo, hi, k=5, est=None, plo=None, phi=None):
    return {"k": k, "estimativa": est if est is not None else (lo + hi) / 2, "ci_lo": lo, "ci_hi": hi,
            "pi_lo": plo, "pi_hi": phi}


# ---------------------------------------------------------------------------
@pytest.mark.parametrize("m,swim,certeza,delta,moderador,rotulo,regra", [
    (meta(0.1, 0.4), None, "baixa", None, False, "Positivo", "positivo_ic"),
    (meta(-0.5, -0.1), None, "moderada", None, False, "Negativo", "negativo_ic"),
    (meta(0.1, 0.4), None, "muito baixa", None, False, "Inconclusivo", "certeza_muito_baixa"),
    (meta(-0.05, 0.08), None, "moderada", 0.1, False, "Nulo", "nulo_equivalencia"),
    (meta(-0.05, 0.08), None, "baixa", 0.1, False, "Inconclusivo", "inconclusivo_ma"),
    (meta(-0.05, 0.08), None, "alta", None, False, "Inconclusivo", "inconclusivo_ma"),  # sem δ não há Nulo
    (meta(-0.2, 0.15), None, "moderada", 0.1, False, "Inconclusivo", "inconclusivo_ma"),
    # caixa-3: moderador_explica sozinho não sustenta Misto (falta a linha de achado com CERQual)
    (meta(0.05, 0.3, plo=-0.3, phi=0.6), None, "moderada", 0.1, True, "Inconclusivo",
     "inconclusivo_misto_nao_sustentado"),
    (meta(0.05, 0.3, plo=-0.3, phi=0.6), None, "moderada", 0.1, False, "Positivo", "positivo_ic"),
    (meta(0.05, 0.3, plo=-0.05, phi=0.6), None, "moderada", 0.1, True, "Positivo", "positivo_ic"),  # dano irrelevante
    (meta(0.1, 0.4), None, "", None, False, "Pendente", "sem_certeza"),
    (meta(0.1, 0.4, k=2), None, "alta", None, False, "Inconclusivo", "inconclusivo_sem_sintese"),
    (None, {"n": 6, "p": 0.031, "prop_benefica": 1.0, "prop_danosa": 0.0}, "baixa", None, False, "Positivo", "positivo_sinal"),
    (None, {"n": 6, "p": 0.031, "prop_benefica": 0.0, "prop_danosa": 1.0}, "baixa", None, False, "Negativo", "negativo_sinal"),
    (None, {"n": 4, "p": 0.01, "prop_benefica": 1.0, "prop_danosa": 0.0}, "alta", None, False, "Inconclusivo", "inconclusivo_sinal"),
    (None, {"n": 10, "p": 0.3, "prop_benefica": 0.6, "prop_danosa": 0.4}, "alta", None, False, "Inconclusivo", "inconclusivo_sinal"),
    (None, {"n": 8, "p": 0.01, "prop_benefica": 1.0, "prop_danosa": 0.0, "so_risco_alto": True}, "alta", None, False,
     "Inconclusivo", "inconclusivo_sinal"),
    (None, None, "alta", None, False, "Inconclusivo", "inconclusivo_sem_sintese"),
])
def test_regras_de_rotulo(m, swim, certeza, delta, moderador, rotulo, regra):
    from rslib.caixa import rotular_efeito
    r = rotular_efeito(m, swim, certeza, delta, moderador)
    assert (r["rotulo"], r["regra"]) == (rotulo, regra), r
    assert r["justificativa"]


def test_forca_mapeada_do_grade():
    from rslib.caixa import rotular_efeito
    assert rotular_efeito(meta(0.1, 0.4), None, "alta")["forca"] == "forte"
    assert rotular_efeito(meta(0.1, 0.4), None, "Moderate")["forca"] == "moderada"
    assert rotular_efeito(meta(0.1, 0.4), None, "baixa")["forca"] == "fraca"
    assert rotular_efeito(meta(0.1, 0.4), None, "muito_baixa")["forca"] == "insuficiente"


def test_escala_e_implementacao():
    from rslib.caixa import escala, ler_faixas, rotulo_implementacao
    faixas = ler_faixas("grande:0.5,pequena:0,moderada:0.2")
    assert faixas == [(0.0, "pequena"), (0.2, "moderada"), (0.5, "grande")]
    assert escala(-0.25, faixas) == "moderada" and escala(0.7, faixas) == "grande" and escala(0.1, faixas) == "pequena"
    assert escala(0.3, []) == "faixas não declaradas no protocolo" and escala(None, faixas) == "não estimada"
    assert [rotulo_implementacao(p) for p in range(6)] == ["Simples", "Simples", "Moderada", "Moderada", "Complexa", "Complexa"]


def test_testes_combinados_nunca_definem_rotulo(tmp_path):
    from rslib.caixa import montar_caixa
    m = tmp_path / "meta.json"
    m.write_text(json.dumps([{"familia_intervencao": "F", "construto_outcome": "Y", "metodo": "Stouffer",
                              "k": 10, "estimativa": 0.4, "ci_lo": 0.2, "ci_hi": 0.6},
                             {"familia_intervencao": "F", "construto_outcome": "Z", "k": 1,
                              "stouffer": {"p": 0.00001}, "fisher": {"p": 0.00001}, "cooper": {"p": 0.001}}]))
    c = tmp_path / "certeza.csv"
    c.write_text("familia_intervencao,construto_outcome,dimensao,certeza\nF,Y,efeito,alta\nF,Z,efeito,alta\n")
    linhas, avisos = montar_caixa(meta_arq=m, certeza_arq=c)
    efeito = {l["construto_outcome"]: l for l in linhas if l["dimensao"] == "efeito"}
    assert efeito["Y"]["rotulo"] == "Inconclusivo" and efeito["Z"]["rotulo"] == "Inconclusivo"
    assert any("teste combinado" in a for a in avisos)


def test_caixa_completa(projeto_vazio, capsys):
    from rslib import esquema, estado
    from rslib.caixa import ARQ_CAIXA, ARQ_CAIXA_MD, COLUNAS_CAIXA
    from rslib.handoff import ler_csv
    est = estado.carregar_estado(projeto_vazio)
    est["modo"]["autonomia"] = "autopiloto"
    estado.salvar_estado(projeto_vazio, est)
    argv = ["--dir", str(projeto_vazio), "caixa", "--master", str(FIX / "master.csv"),
            "--efeitos", str(FIX / "meta_resumo.json"), "--swim", str(FIX / "swim_resumo.json"),
            "--certeza", str(FIX / "certeza.csv"), "--mapa", "assets/mapas/caixa_ferramentas_mapa.csv",
            "--faixas", "pequena:0,moderada:0.2,grande:0.5"]
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 0, resumo
    colunas, linhas = ler_csv(projeto_vazio / ARQ_CAIXA)
    assert colunas == COLUNAS_CAIXA

    # toda célula tem fontes e assinatura
    assert all(l["fontes"].strip() for l in linhas)
    assert all(re.fullmatch(r"[0-9a-f]{64}", l["assinatura"]) for l in linhas)
    assert all(l["regra_versao"] == "caixa-3" for l in linhas)

    ef = {(l["familia_intervencao"], l["construto_outcome"]): l for l in linhas if l["dimensao"] == "efeito"}
    tc, me = "Transferência condicionada", "Merenda escolar"
    assert len(ef) == 8
    assert (ef[(tc, "frequencia")]["rotulo"], ef[(tc, "frequencia")]["forca"], ef[(tc, "frequencia")]["escala"]) == \
        ("Positivo", "moderada", "moderada")
    assert "meta_resumo.json#grupos[0]" in ef[(tc, "frequencia")]["fontes"]
    assert "certeza.csv:linha 2" in ef[(tc, "frequencia")]["fontes"]
    assert ef[(tc, "frequencia")]["estimativa"] == "0.25" and ef[(tc, "frequencia")]["k"] == "6"
    assert ef[(tc, "notas")]["rotulo"] == "Nulo"
    assert (ef[(tc, "evasao")]["rotulo"], ef[(tc, "evasao")]["regra_aplicada"]) == ("Positivo", "positivo_sinal")
    assert ef[(tc, "trabalho_infantil")]["rotulo"] == "Inconclusivo"  # só havia Stouffer
    assert ef[(tc, "saude")]["rotulo"] == "Pendente" and ef[(tc, "saude")]["status_rotulo"] == "pendente"
    assert ef[(me, "frequencia")]["rotulo"] == "Misto"
    assert "certeza.csv:linha 13" in ef[(me, "frequencia")]["fontes"]  # achado explicativo (moderador, CERQual)
    painel = {(l["familia_intervencao"], l["construto_outcome"]): l for l in linhas if l["dimensao"] == "efeito_painel"}
    assert set(painel) == set(ef)  # uma linha de painel por família × construto
    assert all(painel[c]["rotulo"] == ef[c]["rotulo"] for c in ef)  # corpo único: o painel repete o corpo
    assert painel[(tc, "frequencia")]["regra_aplicada"] == "painel_corpo_unico"
    assert painel[(tc, "saude")]["status_rotulo"] == "pendente"
    assert ef[(me, "notas")]["rotulo"] == "Inconclusivo"
    assert ef[(me, "peso")]["rotulo"] == "Inconclusivo"  # Fisher ignorado

    impl = {l["familia_intervencao"]: l for l in linhas if l["dimensao"] == "implementacao"}
    assert (impl[tc]["pontos_implementacao"], impl[tc]["rotulo"], impl[tc]["status_rotulo"]) == ("3", "Moderada", "definido")
    assert "barreiras=0" in impl[tc]["criterios_implementacao"]  # só 1 estudo relata barreiras
    assert "componentes=1(Alves2020)" in impl[tc]["criterios_implementacao"]
    assert (impl[me]["rotulo"], impl[me]["rotulo_proposto"], impl[me]["status_rotulo"]) == ("Pendente", "Simples", "pendente")

    outras = [(l["familia_intervencao"], l["dimensao"], l["rotulo"], l["status_rotulo"]) for l in linhas
              if l["dimensao"] not in ("efeito", "implementacao")]
    assert (tc, "mecanismo", "Condicionalidade reduz o custo de oportunidade da escola", "definido") in outras
    assert (tc, "moderador", "Pendente", "pendente") in outras  # master tem achado sem síntese CERQual
    assert (tc, "percepcao", "Pendente", "pendente") in outras  # linha de certeza sem enunciado
    assert (tc, "custo", "Não reportado", "definido") in outras and (me, "custo", "Não reportado", "definido") in outras

    md = (projeto_vazio / ARQ_CAIXA_MD).read_text(encoding="utf-8")
    assert esquema.MARCA_RASCUNHO in md and "Testes combinados não definem rótulos" in md
    assert resumo["rascunho"] is True and resumo["pendencia"] and len(resumo["avisos"]) == 2
    assert resumo["rotulos_efeito"] == {"Positivo": 2, "Nulo": 1, "Inconclusivo": 3, "Pendente": 1, "Misto": 1}
    assert resumo["rotulos_painel"] == resumo["rotulos_efeito"] and resumo["regra_versao"] == "caixa-3"
    assert estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))[0]["tipo"] == "certeza_caixa"

    # reexecução: mesmas linhas e assinaturas, sem pendência duplicada
    codigo, resumo2 = rodar(argv, capsys)
    assert codigo == 0 and ler_csv(projeto_vazio / ARQ_CAIXA)[1] == linhas and resumo2["pendencia"] == resumo["pendencia"]


def test_so_risco_alto_pelo_master_bloqueia_sinal(tmp_path):
    from rslib.caixa import montar_caixa
    swim = tmp_path / "swim.json"
    swim.write_text(json.dumps({"grupos": [{"familia_intervencao": "Transferência condicionada",
                                            "construto_outcome": "y", "n_estudos": 6, "n_beneficos": 6,
                                            "p_sinal": 0.03, "estudos": ["Borges2019", "Dias2021"]}]}))
    cert = tmp_path / "certeza.csv"
    cert.write_text("familia_intervencao,construto_outcome,dimensao,certeza\nTransferência condicionada,y,efeito,alta\n")
    linhas, _ = montar_caixa(master=FIX / "master.csv", swim_arq=swim, certeza_arq=cert)
    ef = [l for l in linhas if l["dimensao"] == "efeito"][0]
    assert ef["rotulo"] == "Inconclusivo" and "risco alto" in ef["justificativa"]


def test_sem_entradas(projeto_vazio, capsys):
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "caixa"], capsys)
    assert codigo == 1 and "nenhuma entrada" in resumo["erro"]


# ---------------------------------------------------------------------------
# Classe de desenho: meta.R/swim.R separam randomizados e não randomizados
# ---------------------------------------------------------------------------
def _certeza(tmp_path, linhas, cabecalho="familia_intervencao,construto_outcome,dimensao,certeza,classe_desenho"):
    c = tmp_path / "certeza.csv"
    c.write_text(cabecalho + "\n" + "\n".join(linhas) + "\n", encoding="utf-8")
    return c


def test_caixa_separa_classes_com_json_real_do_r(tmp_path):
    """Regressão: com (familia, outcome) como chave, o grupo randomizado sobrescrevia o não randomizado."""
    import csv
    import shutil
    import subprocess

    from conftest import SCRIPTS
    from test_analise_r import efeitos, exigir_r
    exigir_r("jsonlite", "metafor")
    from rslib import esquema
    from rslib.caixa import montar_caixa
    entrada = tmp_path / "extraidos.csv"
    with open(entrada, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=esquema.COLUNAS_EFEITOS_EXTRAIDOS)
        w.writeheader()
        for l in efeitos():
            w.writerow({c: l.get(c, "") for c in esquema.COLUNAS_EFEITOS_EXTRAIDOS})
    rscript = shutil.which("Rscript")
    for script, args in (("efeitos.R", [f"--in={entrada}", f"--out={tmp_path / 'efeitos.csv'}"]),
                         ("meta.R", [f"--in={tmp_path / 'efeitos.csv'}", f"--out-dir={tmp_path}"]),
                         ("swim.R", [f"--in={tmp_path / 'efeitos.csv'}", f"--out-dir={tmp_path}"])):
        proc = subprocess.run([rscript, str(SCRIPTS / "R" / script), *args], capture_output=True, text=True, timeout=600)
        assert proc.returncode == 0, proc.stderr
    meta = json.loads((tmp_path / "meta_resumo.json").read_text(encoding="utf-8"))
    assert {g["classe_desenho"] for g in meta["grupos"]} == {"randomizado", "nao_randomizado"}
    assert {g["construto_outcome"] for g in meta["grupos"]} == {"participacao"}
    certeza = _certeza(tmp_path, ["Transferência condicionada,participacao,efeito,moderada,randomizado",
                                  "Transferência condicionada,participacao,efeito,baixa,nao_randomizado"])
    linhas, avisos = montar_caixa(meta_arq=tmp_path / "meta_resumo.json", swim_arq=tmp_path / "swim_resumo.json",
                                  certeza_arq=certeza)
    ef = {l["classe_desenho"]: l for l in linhas if l["dimensao"] == "efeito"}
    assert set(ef) == {"randomizado", "nao_randomizado"}  # nenhum grupo perdido
    nr, rct = ef["nao_randomizado"], ef["randomizado"]
    assert all(l["familia_intervencao"] == "Transferência condicionada" for l in ef.values())
    assert any("herdou 'Transferência condicionada'" in a for a in avisos)
    i_nr = next(i for i, g in enumerate(meta["grupos"]) if g["classe_desenho"] == "nao_randomizado")
    i_rct = 1 - i_nr
    assert (nr["rotulo"], nr["regra_aplicada"], nr["forca"], nr["k"]) == ("Positivo", "positivo_ic", "fraca", "3")
    assert float(nr["estimativa"]) == pytest.approx(meta["grupos"][i_nr]["resultado"]["estimativa"], rel=1e-5)
    assert f"meta_resumo.json#grupos[{i_nr}]" in nr["fontes"] and "certeza.csv:linha 3" in nr["fontes"]
    assert nr["celula_id"] == "Transferência condicionada × participacao [nao_randomizado]"
    assert (rct["rotulo"], rct["regra_aplicada"], rct["k"]) == ("Inconclusivo", "inconclusivo_sinal", "1")
    assert f"meta_resumo.json#grupos[{i_rct}]" in rct["fontes"] and "swim_resumo.json#grupos[" in rct["fontes"]
    assert "certeza.csv:linha 2" in rct["fontes"] and rct["certeza"] == "moderada"
    # painel: rótulos diferentes, vale o corpo de maior certeza (randomizado, moderada) com o outro anotado
    painel = [l for l in linhas if l["dimensao"] == "efeito_painel"]
    assert len(painel) == 1 and painel[0]["rotulo"] == "Inconclusivo"
    assert painel[0]["regra_aplicada"] == "painel_maior_certeza" and painel[0]["certeza"] == "moderada"
    assert "nao_randomizado: Positivo (certeza baixa)" in painel[0]["justificativa"]


def test_classe_pelo_rotulo_certeza_generica_e_colisao(tmp_path):
    from rslib.caixa import classe_desenho, montar_caixa
    assert [classe_desenho(v) for v in ("RCT", "não randomizado", "nao_randomizado", "", "quase")] == \
        ["randomizado", "nao_randomizado", "nao_randomizado", "", ""]
    m = tmp_path / "meta.json"
    m.write_text(json.dumps({"grupos": [
        # rótulo de rotulo_grupo() sem os atributos explícitos: a classe vem do sufixo
        {"grupo": "F :: y | randomizado", "k_estudos": 4, "resultado": {"estimativa": 0.3, "ic_inf": 0.1, "ic_sup": 0.5}},
        {"grupo": "F :: y | nao_randomizado", "k_estudos": 5,
         "resultado": {"estimativa": -0.02, "ic_inf": -0.08, "ic_sup": 0.05}},
        {"familia_intervencao": "F", "construto_outcome": "y", "classe_desenho": "randomizado", "k_estudos": 9,
         "resultado": {"estimativa": 9, "ic_inf": 8, "ic_sup": 10}},
    ]}), encoding="utf-8")
    certeza = _certeza(tmp_path, ["F,y,efeito,moderada"], cabecalho="familia_intervencao,construto_outcome,dimensao,certeza")
    linhas, avisos = montar_caixa(meta_arq=m, certeza_arq=certeza, delta=0.1)
    ef = {l["classe_desenho"]: l for l in linhas if l["dimensao"] == "efeito"}
    assert set(ef) == {"randomizado", "nao_randomizado"}
    assert (ef["randomizado"]["rotulo"], ef["randomizado"]["estimativa"]) == ("Positivo", "0.3")  # 1º grupo mantido
    assert ef["nao_randomizado"]["rotulo"] == "Nulo"
    assert any("mesma célula" in a for a in avisos)
    assert any("certeza sem classe_desenho aplicada a nao_randomizado e randomizado" in a for a in avisos)


def test_grupo_sem_familia_com_familias_ambiguas_avisa(tmp_path):
    from rslib.caixa import montar_caixa
    s = tmp_path / "swim.json"
    s.write_text(json.dumps({"grupos": [{"grupo": "y | nao_randomizado", "construto_outcome": "y",
                                         "classe_desenho": "nao_randomizado", "n_estudos": 6, "n_beneficos": 6,
                                         "p_sinal": 0.03}]}), encoding="utf-8")
    certeza = _certeza(tmp_path, ["F,y,efeito,alta,nao_randomizado", "G,y,efeito,alta,nao_randomizado"])
    linhas, avisos = montar_caixa(swim_arq=s, certeza_arq=certeza)
    ef = [(l["familia_intervencao"], l["classe_desenho"], l["rotulo"]) for l in linhas if l["dimensao"] == "efeito"]
    assert ("", "nao_randomizado", "Pendente") in ef  # não chuta a família
    assert any("--grupo=familia_intervencao,construto_outcome" in a for a in avisos)


def test_certeza_muito_baixa_precede_misto():
    from rslib import caixa
    meta = {"k": 6, "ci_lo": -0.1, "ci_hi": 0.5, "pi_lo": -0.6, "pi_hi": 0.9, "alinhado": True}
    r = caixa.rotular_efeito(meta, None, "muito baixa", delta=0.1, moderador_explica=True)
    assert r["rotulo"] == "Inconclusivo" and r["regra"] == "certeza_muito_baixa"
    achado = {"certeza": "baixa", "enunciado": "efeito maior em escolas rurais", "fonte": "certeza.csv:linha 3"}
    r = caixa.rotular_efeito(meta, None, "muito baixa", delta=0.1, moderador_explica=True, achado_explicativo=achado)
    assert r["rotulo"] == "Inconclusivo" and r["regra"] == "certeza_muito_baixa"
    r2 = caixa.rotular_efeito(meta, None, "baixa", delta=0.1, moderador_explica=True, achado_explicativo=achado)
    assert r2["rotulo"] == "Misto"


# ---------------------------------------------------------------------------
# Regressões (S3): validação humana em todas as dimensões, NA_secao, n_pendentes no evento
# ---------------------------------------------------------------------------
def _master_impl(tmp_path, custo_unitario):
    m = tmp_path / "master.csv"
    m.write_text("ficha_id,citekey,familia_intervencao,impl_componentes,impl_multinivel,impl_infraestrutura,"
                 "impl_barreiras_fidelidade,impl_tempo_longo,mecanismo_id,custo_id,custo_unitario\n"
                 + "".join(f"{c},{c},F,Sim,Não,Não,Não,Não,Sim,Não,{custo_unitario}\n" for c in ("Alves2020", "Borges2019")),
                 encoding="utf-8")
    return m


def test_validado_humano_vale_para_implementacao_e_achados(tmp_path):
    """Regressão: só as linhas de efeito viravam rascunho sem validado_humano."""
    from rslib.caixa import montar_caixa
    certeza = tmp_path / "certeza.csv"
    certeza.write_text(
        "familia_intervencao,construto_outcome,dimensao,certeza,abordagem,enunciado,estudos,validado_humano\n"
        "F,y,efeito,moderada,GRADE,,,nao\n"
        "F,,implementacao,moderada,CERQual,Exige coordenação,Alves2020,\n"
        "F,,mecanismo,baixa,CERQual,Condicionalidade reduz custo,Alves2020,\n"
        "F,,percepcao,alta,CERQual,Famílias aprovam,Borges2019,sim\n", encoding="utf-8")
    meta = tmp_path / "meta.json"
    meta.write_text(json.dumps({"grupos": [{"familia_intervencao": "F", "construto_outcome": "y", "k": 4,
                                            "estimativa": 0.3, "ci_lo": 0.1, "ci_hi": 0.5}]}), encoding="utf-8")
    linhas, _ = montar_caixa(master=_master_impl(tmp_path, "999"), meta_arq=meta, certeza_arq=certeza)
    por_dim = {l["dimensao"]: l for l in linhas}
    assert (por_dim["efeito"]["rotulo"], por_dim["efeito"]["status_rotulo"]) == ("Positivo", "rascunho")
    assert (por_dim["implementacao"]["rotulo"], por_dim["implementacao"]["status_rotulo"]) == ("Simples", "rascunho")
    assert "validado_humano não marcado" in por_dim["implementacao"]["justificativa"]
    assert por_dim["mecanismo"]["status_rotulo"] == "rascunho"
    assert "validado_humano não marcado" in por_dim["mecanismo"]["justificativa"]
    assert por_dim["percepcao"]["status_rotulo"] == "definido"
    # sem a coluna validado_humano, o comportamento anterior continua (definido)
    sem_coluna = tmp_path / "certeza_sem.csv"
    sem_coluna.write_text("familia_intervencao,construto_outcome,dimensao,certeza,abordagem,enunciado\n"
                          "F,,implementacao,moderada,CERQual,Exige coordenação\n", encoding="utf-8")
    linhas, _ = montar_caixa(master=_master_impl(tmp_path, "999"), certeza_arq=sem_coluna)
    assert [l["status_rotulo"] for l in linhas if l["dimensao"] == "implementacao"] == ["definido"]


def test_na_secao_conta_como_ausente(tmp_path):
    """Regressão: custo_unitario (sem valores_sim no mapa) = NA_secao contava como achado de custo."""
    from rslib.caixa import montar_caixa
    for valor in ("NA_secao", "999", "na_secao"):
        linhas, _ = montar_caixa(master=_master_impl(tmp_path, valor))
        custo = [(l["rotulo"], l["regra_aplicada"]) for l in linhas if l["dimensao"] == "custo"]
        assert custo == [("Não reportado", "custo_nao_reportado")], (valor, custo)
    linhas, _ = montar_caixa(master=_master_impl(tmp_path, "R$ 120 por aluno"))
    custo = [(l["rotulo"], l["regra_aplicada"]) for l in linhas if l["dimensao"] == "custo"]
    assert custo == [("Pendente", "achado_sem_sintese")]


def test_evento_caixa_gerada_traz_n_pendentes(projeto_vazio, capsys, tmp_path):
    """Contrato lido por `rs.py status`: n_pendentes (pendente + rascunho) e n_rascunho no evento caixa_gerada."""
    from rslib import estado
    certeza = tmp_path / "certeza.csv"
    certeza.write_text(
        "familia_intervencao,construto_outcome,dimensao,certeza,abordagem,enunciado,validado_humano\n"
        "F,y,efeito,,GRADE,,\n"
        "F,,mecanismo,baixa,CERQual,Condicionalidade reduz custo,\n", encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "caixa", "--certeza", str(certeza)], capsys)
    assert codigo == 0, resumo
    from rslib.caixa import ARQ_CAIXA
    from rslib.handoff import ler_csv
    status = [l["status_rotulo"] for l in ler_csv(projeto_vazio / ARQ_CAIXA)[1]]
    ev = [e for e in estado.ler_log(projeto_vazio) if e["evento"] == "caixa_gerada"][-1]
    # efeito sem certeza e seu painel, implementação e custo sem master (pendentes) + mecanismo sem validação (rascunho)
    assert ev["dados"]["n_pendentes"] == resumo["n_pendentes"] == sum(s != "definido" for s in status) == 5
    assert ev["dados"]["n_rascunho"] == resumo["n_rascunho"] == status.count("rascunho") == 1
    assert ev["dados"]["rascunho"] is True


def test_regressao_certeza_caixa_atualiza_n_e_fecha_sozinha(projeto_vazio, capsys, tmp_path, monkeypatch):
    """certeza_caixa: n acompanha as células não definidas (sem duplicar) e fecha quando todas ficam definidas."""
    from rslib import caixa, esquema, estado
    est = estado.carregar_estado(projeto_vazio)
    est["modo"]["autonomia"] = "autopiloto"
    estado.salvar_estado(projeto_vazio, est)
    swim = tmp_path / "swim.json"
    grupos = [{"familia_intervencao": "Tutoria", "construto_outcome": c, "n_estudos": 6, "n_beneficos": 6,
               "p_sinal": 0.03, "estudos": ["Alves2020"]} for c in ("notas", "evasao", "frequencia")]
    swim.write_text(json.dumps({"grupos": grupos}), encoding="utf-8")
    cert = tmp_path / "certeza.csv"
    cert.write_text("familia_intervencao,construto_outcome,dimensao,certeza\nTutoria,notas,efeito,moderada\n",
                    encoding="utf-8")
    modelo, _ = caixa.montar_caixa(swim_arq=swim, certeza_arq=cert)
    n_pendentes = {"valor": 3}

    def montar_falso(*args, **kwargs):  # mesmas linhas reais, com n células ainda não definidas
        linhas = [dict(l) for l in modelo]
        for k, l in enumerate(linhas):
            l["status_rotulo"] = "pendente" if k < n_pendentes["valor"] else "definido"
        return linhas, []

    monkeypatch.setattr(caixa, "montar_caixa", montar_falso)
    argv = ["--dir", str(projeto_vazio), "caixa", "--swim", str(swim), "--certeza", str(cert)]

    def abertas():
        return [p for p in estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))
                if p["tipo"] == esquema.PENDENCIA_CERTEZA_CAIXA]

    codigo, r1 = rodar(argv, capsys)
    assert codigo == 0 and r1["n_pendentes"] == 3 and [p["n"] for p in abertas()] == [3]
    codigo, r1b = rodar(argv, capsys)
    assert r1b["pendencia"] == r1["pendencia"] and len(abertas()) == 1
    n_pendentes["valor"] = 1
    codigo, r2 = rodar(argv, capsys)
    assert r2["n_pendentes"] == 1 and r2["pendencia"] != r1["pendencia"]
    assert [(p["id"], p["n"]) for p in abertas()] == [(r2["pendencia"], 1)]

    n_pendentes["valor"] = 0
    codigo, r3 = rodar(argv, capsys)
    assert codigo == 0 and r3["n_pendentes"] == 0 and r3["pendencia"] is None and abertas() == []
    # a pendência resolvida não deixa o produto como rascunho
    assert r3["rascunho"] is False
    assert esquema.MARCA_RASCUNHO not in (projeto_vazio / caixa.ARQ_CAIXA_MD).read_text(encoding="utf-8")
    fechamento = [e for e in estado.ler_log(projeto_vazio) if e["evento"] == "pendencia_fechada"][-1]
    assert fechamento["dados"]["pendencia"] == r2["pendencia"] and fechamento["ator"]["tipo"] == "script"
    # idempotente: reexecutar não registra novo fechamento
    n_fechadas = len([e for e in estado.ler_log(projeto_vazio) if e["evento"] == "pendencia_fechada"])
    rodar(argv, capsys)
    assert len([e for e in estado.ler_log(projeto_vazio) if e["evento"] == "pendencia_fechada"]) == n_fechadas


# ---------------------------------------------------------------------------
# Regressões (caixa-3): Misto com k >= 5, δ e achado explicativo com CERQual; painel por família × construto
# ---------------------------------------------------------------------------
ACHADO_BAIXA = {"certeza": "baixa", "enunciado": "efeito maior em municípios pequenos", "fonte": "certeza.csv:linha 5"}


@pytest.mark.parametrize("k,delta,moderador,achado,tau2,rotulo,trecho", [
    (5, 0.1, False, ACHADO_BAIXA, None, "Misto", "municípios pequenos"),  # o achado marcado basta como alegação
    (6, 0.1, True, ACHADO_BAIXA, True, "Misto", "CERQual baixa"),
    (4, 0.1, True, ACHADO_BAIXA, None, "Inconclusivo", "k = 4 < 5"),       # regressão: k = 3 ou 4 dava Misto
    (3, 0.1, True, None, None, "Inconclusivo", "k = 3 < 5"),
    (7, None, True, ACHADO_BAIXA, None, "Inconclusivo", "δ não declarado"),  # sem δ o IP cruzava zero e virava Misto
    (7, 0.1, True, None, None, "Inconclusivo", "explica_heterogeneidade"),
    (7, 0.1, True, dict(ACHADO_BAIXA, certeza="muito baixa"), None, "Inconclusivo", "CERQual muito_baixa"),
    (7, 0.1, True, dict(ACHADO_BAIXA, certeza=""), None, "Inconclusivo", "CERQual ausente"),
    (7, 0.1, True, dict(ACHADO_BAIXA, enunciado=""), None, "Inconclusivo", "sem enunciado"),
    (7, 0.1, True, ACHADO_BAIXA, False, "Inconclusivo", "tau2_interpretavel = false"),
])
def test_regressao_misto_exige_k5_delta_e_achado_cerqual(k, delta, moderador, achado, tau2, rotulo, trecho):
    from rslib.caixa import rotular_efeito
    m = dict(meta(0.05, 0.3, k=k, plo=-0.3, phi=0.6), tau2_interpretavel=tau2)
    r = rotular_efeito(m, None, "moderada", delta, moderador, achado_explicativo=achado)
    assert r["rotulo"] == rotulo, r
    assert r["regra"] == ("misto_pi_moderador" if rotulo == "Misto" else "inconclusivo_misto_nao_sustentado")
    assert trecho in r["justificativa"], r["justificativa"]


def test_sem_alegacao_de_explicacao_ip_largo_segue_para_positivo():
    from rslib.caixa import rotular_efeito
    r = rotular_efeito(meta(0.05, 0.3, k=3, plo=-0.3, phi=0.6), None, "moderada", None, False)
    assert (r["rotulo"], r["regra"]) == ("Positivo", "positivo_ic")


def test_achado_explicativo_casado_por_familia_outcome_classe_e_marca(tmp_path):
    from rslib.caixa import montar_caixa
    m = tmp_path / "meta.json"
    m.write_text(json.dumps({"grupos": [{"familia_intervencao": "F", "construto_outcome": "y", "k": 8,
                                         "estimativa": 0.2, "ci_lo": 0.05, "ci_hi": 0.35, "pi_lo": -0.4,
                                         "pi_hi": 0.8, "classe_desenho": "randomizado"}]}), encoding="utf-8")
    cab = ("familia_intervencao,construto_outcome,dimensao,certeza,abordagem,enunciado,delta,moderador_explica,"
           "classe_desenho,explica_heterogeneidade,validado_humano")

    def rodar_com(*achados):
        c = tmp_path / "certeza.csv"
        c.write_text("\n".join([cab, "F,y,efeito,moderada,GRADE,,0.1,sim,randomizado,,sim", *achados]) + "\n",
                     encoding="utf-8")
        linhas, _ = montar_caixa(meta_arq=m, certeza_arq=c)
        return next(l for l in linhas if l["dimensao"] == "efeito")

    # moderador sem a marca, de outro outcome, de outra classe ou de outra família não explica
    ef = rodar_com("F,y,moderador,alta,CERQual,Maior em rurais,,,,,sim",
                   "F,z,moderador,alta,CERQual,Outro outcome,,,,sim,sim",
                   "F,y,mecanismo,alta,CERQual,Outra classe,,,nao_randomizado,sim,sim",
                   "G,y,moderador,alta,CERQual,Outra família,,,,sim,sim")
    assert (ef["rotulo"], ef["regra_aplicada"]) == ("Inconclusivo", "inconclusivo_misto_nao_sustentado")
    # achado da família inteira (outcome vazio), marcado: vale; entre dois, o de maior confiança
    ef = rodar_com("F,,mecanismo,baixa,CERQual,Custo de oportunidade,,,,sim,sim",
                   "F,y,moderador,moderada,CERQual,Maior em rurais,,,,sim,sim")
    assert ef["rotulo"] == "Misto" and ef["status_rotulo"] == "definido"
    assert "Maior em rurais" in ef["justificativa"] and "certeza.csv:linha 4" in ef["fontes"]
    # achado explicativo sem validado_humano rebaixa a linha Misto a rascunho
    ef = rodar_com("F,y,moderador,moderada,CERQual,Maior em rurais,,,,sim,nao")
    assert ef["rotulo"] == "Misto" and ef["status_rotulo"] == "rascunho"
    assert "achado explicativo" in ef["justificativa"]


def _corpo(classe, rotulo, certeza, status="definido", estudos="A2020"):
    return {"classe_desenho": classe, "rotulo": rotulo, "certeza": certeza, "status_rotulo": status,
            "estudos": estudos, "celula_id": f"F × y [{classe}]"}


@pytest.mark.parametrize("corpos,rotulo,regra,status", [
    ([_corpo("randomizado", "Positivo", "moderada")], "Positivo", "painel_corpo_unico", "definido"),
    ([_corpo("randomizado", "Positivo", "baixa"), _corpo("nao_randomizado", "Positivo", "moderada")],
     "Positivo", "painel_mesmo_rotulo", "definido"),
    ([_corpo("randomizado", "Positivo", "moderada"), _corpo("nao_randomizado", "Inconclusivo", "baixa")],
     "Positivo", "painel_maior_certeza", "definido"),
    ([_corpo("randomizado", "Inconclusivo", "alta"), _corpo("nao_randomizado", "Positivo", "baixa")],
     "Inconclusivo", "painel_maior_certeza", "definido"),
    ([_corpo("randomizado", "Positivo", "baixa"), _corpo("nao_randomizado", "Negativo", "baixa")],
     "Inconclusivo", "painel_empate_desenho", "definido"),
    ([_corpo("randomizado", "Positivo", "alta"), _corpo("nao_randomizado", "Pendente", "", "pendente")],
     "Pendente", "painel_pendente", "pendente"),
    ([_corpo("randomizado", "Positivo", "alta", "rascunho"), _corpo("nao_randomizado", "Positivo", "baixa")],
     "Positivo", "painel_mesmo_rotulo", "rascunho"),
])
def test_painel_regra_de_combinacao_dos_corpos(corpos, rotulo, regra, status):
    from rslib.caixa import painel_efeito
    p = painel_efeito(corpos)
    assert (p["rotulo"], p["regra"], p["status"]) == (rotulo, regra, status), p
    if regra == "painel_maior_certeza":
        outro = [c for c in corpos if c is not p["escolhido"]][0]
        assert f"{outro['classe_desenho']}: {outro['rotulo']}" in p["justificativa"]  # o outro corpo fica anotado
    if regra == "painel_mesmo_rotulo":
        assert p["escolhido"]["certeza"] == max((c["certeza"] for c in corpos),
                                                key=lambda x: ["baixa", "moderada", "alta"].index(x))
    if regra == "painel_empate_desenho":
        assert "heterogeneidade por desenho" in p["justificativa"]


def test_painel_integrado_empate_vira_inconclusivo(tmp_path):
    from rslib.caixa import montar_caixa
    m = tmp_path / "meta.json"
    m.write_text(json.dumps({"grupos": [
        {"familia_intervencao": "F", "construto_outcome": "y", "classe_desenho": "randomizado", "k": 4,
         "estimativa": 0.3, "ci_lo": 0.1, "ci_hi": 0.5, "estudos": ["A2020"]},
        {"familia_intervencao": "F", "construto_outcome": "y", "classe_desenho": "nao_randomizado", "k": 5,
         "estimativa": -0.3, "ci_lo": -0.5, "ci_hi": -0.1, "estudos": ["B2021"]},
    ]}), encoding="utf-8")
    c = _certeza(tmp_path, ["F,y,efeito,baixa,randomizado", "F,y,efeito,baixa,nao_randomizado"])
    linhas, _ = montar_caixa(meta_arq=m, certeza_arq=c)
    painel = [l for l in linhas if l["dimensao"] == "efeito_painel"]
    assert len(painel) == 1
    p = painel[0]
    assert (p["rotulo"], p["regra_aplicada"], p["certeza"], p["classe_desenho"]) == \
        ("Inconclusivo", "painel_empate_desenho", "baixa", "")
    assert p["celula_id"] == "F × y [painel]" and p["estudos"] == "A2020|B2021" and p["regra_versao"] == "caixa-3"
    assert "caixa: F × y [randomizado]" in p["fontes"] and "caixa: F × y [nao_randomizado]" in p["fontes"]


def test_markdown_da_caixa_nao_cita_documento_interno(projeto_vazio, capsys, tmp_path):
    from rslib.caixa import ARQ_CAIXA_MD
    c = _certeza(tmp_path, ["F,y,efeito,baixa,randomizado"])
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "caixa", "--certeza", str(c)], capsys)
    assert codigo == 0, resumo
    md = (projeto_vazio / ARQ_CAIXA_MD).read_text(encoding="utf-8")
    assert "Apêndice B" not in md and "PLANO" not in md and "references/" in md
