"""Smoke tests dos scripts R (efeitos, meta, swim, testes combinados) chamados como o Python chamaria.

Por que existe: os scripts R são executados por `Rscript` a partir da skill, então o
contrato que importa é o de linha de comando — código de saída, JSON na última linha
do stdout e colunas exatamente iguais a `esquema.COLUNAS_EFEITOS_CALCULADOS`. Os
valores numéricos de referência ficam nos testes testthat (tests/R), que este
arquivo também dispara quando o testthat está instalado.

Tudo é pulado sem Rscript; os testes que precisam de metafor/clubSandwich são
pulados sem esses pacotes (a skill degrada: sem metafor, sem meta-análise).
"""

import csv
import json
import shutil
import subprocess
from functools import lru_cache

import pytest

from conftest import DIR_TESTES, RAIZ_REPO, SCRIPTS

DIR_R = SCRIPTS / "R"
RSCRIPT = shutil.which("Rscript")

pytestmark = pytest.mark.skipif(RSCRIPT is None, reason="Rscript não encontrado")


@lru_cache(maxsize=None)
def pacote_r(nome):
    saida = subprocess.run(
        [RSCRIPT, "-e", f'cat(requireNamespace("{nome}", quietly = TRUE))'],
        capture_output=True, text=True, timeout=120,
    )
    return saida.stdout.strip().endswith("TRUE")


def exigir_r(*pacotes):
    faltando = [p for p in pacotes if not pacote_r(p)]
    if faltando:
        pytest.skip(f"pacotes R ausentes: {', '.join(faltando)}")


def rodar(script, *args, cwd=None):
    """Roda um script R e devolve (código, resumo JSON da última linha, stdout, stderr)."""
    proc = subprocess.run(
        [RSCRIPT, str(DIR_R / script), *args],
        capture_output=True, text=True, timeout=600, cwd=cwd,
    )
    linhas = [l for l in proc.stdout.splitlines() if l.strip()]
    assert linhas, f"sem stdout de {script}; stderr:\n{proc.stderr}"
    resumo = json.loads(linhas[-1])
    return proc.returncode, resumo, proc.stdout, proc.stderr


def escrever_extraidos(caminho, linhas, extras=()):
    from rslib import esquema

    colunas = list(esquema.COLUNAS_EFEITOS_EXTRAIDOS) + list(extras)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colunas)
        w.writeheader()
        for linha in linhas:
            w.writerow({c: linha.get(c, "") for c in colunas})


def efeitos_sinteticos():
    """12 RCTs com médias/DP (aprendizagem, aumentar) + 6 DiD com t ou p (evasão, reduzir) + 1 meta-análise."""
    linhas = []
    deltas = [3.1, 1.2, 4.5, 2.0, 5.2, 0.4, 2.8, 3.3, 1.9, 0.8, 4.0, 2.2]
    tamanhos = [(60, 55), (120, 118), (40, 42), (200, 190), (35, 30), (80, 85),
                (150, 140), (45, 50), (90, 95), (300, 310), (70, 66), (25, 28)]
    for i, (delta, (n1, n2)) in enumerate(zip(deltas, tamanhos), start=1):
        linhas.append(dict(
            id_efeito=f"E{i:03d}", chave=f"Autor{i}2020", id_estudo=f"ES{i:04d}", desenho="RCT",
            estimando="ATE", outcome="nota", construto_outcome="aprendizagem", direcao_desejada="aumentar",
            modelo_principal="1", tipo_estatistica="md_sd", m1=f"{50 + delta:.1f}", sd1="10", n1=n1,
            m2="50", sd2="10", n2=n2, rob_geral=["baixo", "alto", "algumas preocupações"][i % 3],
        ))
    for i in range(13, 19):
        base = dict(id_efeito=f"E{i:03d}", chave=f"Autor{i}2021", id_estudo=f"ES{i:04d}", desenho="DiD",
                    estimando="ATT", outcome="evasao", construto_outcome="evasao", direcao_desejada="reduzir",
                    n1="100", n2="120", rob_geral="alto")
        if i % 2:
            base.update(tipo_estatistica="t", t=f"-{1 + i / 10:.2f}", df="218")
        else:
            base.update(tipo_estatistica="p_n", p="0.03", beta="-0.2")
        linhas.append(base)
    linhas.append(dict(id_efeito="E900", chave="Revisao2019", id_estudo="ES0900", desenho="meta-análise",
                       construto_outcome="aprendizagem", direcao_desejada="aumentar", tipo_estatistica="g",
                       beta="0.3", se="0.05"))
    return linhas


def test_colunas_de_saida_iguais_ao_esquema(tmp_path):
    exigir_r("jsonlite")
    from rslib import esquema

    entrada = tmp_path / "efeitos_extraidos.csv"
    saida = tmp_path / "06-analise" / "efeitos.csv"
    escrever_extraidos(entrada, efeitos_sinteticos(), extras=["rob_geral"])
    codigo, resumo, _, stderr = rodar("efeitos.R", f"--in={entrada}", f"--out={saida}")
    assert codigo == 0, stderr
    assert resumo["ok"] is True
    assert resumo["n_linhas"] == 19
    assert resumo["n_calculados"] == 18
    assert resumo["n_rejeitados_revisao"] == 1
    assert resumo["n_invertidos"] == 6
    assert resumo["formulas_sem_mapa"] == []
    with open(saida, encoding="utf-8") as f:
        cabecalho = next(csv.reader(f))
    assert cabecalho == list(esquema.COLUNAS_EFEITOS_CALCULADOS) + ["rob_geral"]


def test_colunas_do_cli_r_espelham_esquema():
    """_cli.R repete as listas de esquema.py; divergência quebraria o handoff Python ↔ R."""
    exigir_r("jsonlite")
    from rslib import esquema

    proc = subprocess.run(
        [RSCRIPT, "-e", f'source("{DIR_R / "_cli.R"}"); cat(jsonlite::toJSON(list('
                        'e = COLUNAS_EFEITOS_EXTRAIDOS, c = COLUNAS_EFEITOS_CALCULADOS)))'],
        capture_output=True, text=True, timeout=120,
    )
    listas = json.loads(proc.stdout.strip().splitlines()[-1])
    assert listas["e"] == list(esquema.COLUNAS_EFEITOS_EXTRAIDOS)
    assert listas["c"] == list(esquema.COLUNAS_EFEITOS_CALCULADOS)


def test_mapa_de_conversoes_tem_colunas_e_formulas():
    caminho = SCRIPTS.parent / "assets" / "mapas" / "conversoes_efeito.csv"
    with open(caminho, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    ids = {l["formula_id"] for l in linhas}
    assert {"md_sd", "t_ind", "or_logit", "beta_sd", "r_d", "r_d_n_total", "mann_whitney_z", "mediana_iqr_wan",
            "mediana_iqr_aprox"} <= ids
    for l in linhas:
        assert l["formula_d"] and l["pressupostos"] and l["fonte"], l["formula_id"]
        assert l["aproximado"] in {"0", "1"}


def test_pipeline_efeitos_meta_swim_testes(tmp_path):
    exigir_r("jsonlite", "metafor")
    entrada = tmp_path / "efeitos_extraidos.csv"
    efeitos = tmp_path / "06-analise" / "efeitos.csv"
    out_dir = tmp_path / "06-analise"
    escrever_extraidos(entrada, efeitos_sinteticos(), extras=["rob_geral"])
    assert rodar("efeitos.R", f"--in={entrada}", f"--out={efeitos}")[0] == 0

    codigo, resumo, _, stderr = rodar("meta.R", f"--in={efeitos}", f"--out-dir={out_dir}", "--moderadores=rob_geral")
    assert codigo == 0, stderr
    assert resumo["n_grupos"] == 2
    assert resumo["n_meta_ajustadas"] == 2
    assert resumo["linhas_excluidas"]["rejeitado_revisao"] == 1
    meta = json.loads((out_dir / "meta_resumo.json").read_text(encoding="utf-8"))
    grupos = {g["grupo"]: g for g in meta["grupos"]}
    rct = grupos["aprendizagem | randomizado"]
    assert rct["resultado"]["k_estudos"] == 12
    assert rct["vies_publicacao"]["executado"] is True
    assert grupos["evasao | nao_randomizado"]["vies_publicacao"]["executado"] is False
    assert rct["resultado"]["estimativa"] > 0
    assert len(rct["resultado"]["pi"]) == 2
    assert (out_dir / "tabelas" / "meta_grupos.csv").exists()
    assert any(p.suffix == ".pdf" for p in (out_dir / "figuras").iterdir())

    codigo, resumo, _, stderr = rodar("swim.R", f"--in={efeitos}", f"--out-dir={out_dir}")
    assert codigo == 0, stderr
    swim = json.loads((out_dir / "swim_resumo.json").read_text(encoding="utf-8"))
    evasao = [g for g in swim["grupos"] if g["grupo"].startswith("evasao")][0]
    assert evasao["n_beneficos"] == 6  # t negativo com direção "reduzir" é benéfico

    codigo, resumo, stdout, stderr = rodar("testes_combinados.R", f"--in={efeitos}", f"--out-dir={out_dir}")
    assert codigo == 0, stderr
    assert stdout.startswith("RESSALVA")
    assert "não direcional" in (out_dir / "testes_combinados.json").read_text(encoding="utf-8")


def test_jsons_legiveis_pela_caixa(tmp_path):
    """meta_resumo.json e swim_resumo.json expõem célula, IC, IP, k e teste de sinal como escalares.

    Usa os leitores de `rslib.caixa` (B3) quando existem; o teste é pulado se a API mudar,
    para não acoplar os dois lados além do contrato de campos.
    """
    exigir_r("jsonlite", "metafor")
    try:
        from rslib import caixa
    except Exception:  # módulo de outro agente ausente ou quebrado
        pytest.skip("rslib.caixa indisponível")
    if not all(hasattr(caixa, f) for f in ("ler_meta", "ler_swim")):
        pytest.skip("rslib.caixa sem ler_meta/ler_swim")
    entrada = tmp_path / "extraidos.csv"
    efeitos = tmp_path / "efeitos.csv"
    out_dir = tmp_path / "06-analise"
    escrever_extraidos(entrada, efeitos_sinteticos(), extras=["rob_geral"])
    assert rodar("efeitos.R", f"--in={entrada}", f"--out={efeitos}")[0] == 0
    assert rodar("meta.R", f"--in={efeitos}", f"--out-dir={out_dir}")[0] == 0
    assert rodar("swim.R", f"--in={efeitos}", f"--out-dir={out_dir}")[0] == 0
    avisos = []
    meta = caixa.ler_meta(out_dir / "meta_resumo.json", avisos)
    item = [v for (fam, out, classe), v in meta.items() if out == "aprendizagem"][0]  # chave inclui classe_desenho
    assert item["classe"] == "randomizado"
    assert item["k"] == 12 and item["ci_lo"] is not None and item["ci_hi"] is not None
    assert item["pi_lo"] is not None and item["estimativa"] > 0
    swim = caixa.ler_swim(out_dir / "swim_resumo.json", avisos)
    evasao = [v for (fam, out, classe), v in swim.items() if out == "evasao"][0]
    assert evasao["classe"] == "nao_randomizado"
    assert evasao["n"] == 6 and evasao["prop_benefica"] == 1 and evasao["p"] is not None
    assert evasao["so_risco_alto"] is True


def test_campos_de_delta_do_meta_casam_com_regras_da_caixa(tmp_path):
    """Contrato meta.R × rslib/caixa.py: ic_dentro_delta (Nulo) e pi_cobre_beneficio_e_dano (Misto).

    Regressão: meta.R usava < no IC e comparava o IP com zero, enquanto a caixa usa <= e ±δ.
    """
    exigir_r("jsonlite", "metafor")
    try:
        from rslib import caixa
    except Exception:
        pytest.skip("rslib.caixa indisponível")
    entrada = tmp_path / "extraidos.csv"
    efeitos = tmp_path / "efeitos.csv"
    linhas = []
    # heterogêneo (IP cruza zero e, conforme δ, também ±δ) e quase nulo (IC estreito em torno de zero)
    for construto, deltas, n in (("heterogeneo", [-4, 6, -3, 7, 1, 5, -2, 8], 60),
                                 ("quase_nulo", [0.2, -0.1, 0.1, 0.0, 0.15, -0.05], 3000)):
        for i, dm in enumerate(deltas, start=1):
            linhas.append(dict(id_efeito=f"{construto}{i}", chave=f"{construto.title()}{i}2020",
                               id_estudo=f"{construto}{i}", desenho="RCT", construto_outcome=construto,
                               direcao_desejada="aumentar", modelo_principal="1", tipo_estatistica="md_sd",
                               m1=str(50 + dm), sd1="10", n1=str(n), m2="50", sd2="10", n2=str(n)))
    escrever_extraidos(entrada, linhas)
    assert rodar("efeitos.R", f"--in={entrada}", f"--out={efeitos}")[0] == 0
    vistos = set()
    for delta in ("0.02", "0.05", "0.3", "0.6", "1.5"):
        out_dir = tmp_path / f"d{delta}"
        codigo, _, _, stderr = rodar("meta.R", f"--in={efeitos}", f"--out-dir={out_dir}", f"--delta={delta}")
        assert codigo == 0, stderr
        meta = json.loads((out_dir / "meta_resumo.json").read_text(encoding="utf-8"))
        assert "ic_dentro_delta" in meta["contrato_campos"] and "pi_cobre_beneficio_e_dano" in meta["contrato_campos"]
        d = float(delta)
        for chave, item in caixa.ler_meta(out_dir / "meta_resumo.json", []).items():
            grupo = next(g for g in meta["grupos"] if g["construto_outcome"] == chave[1])
            r = grupo["resultado"]
            assert r["ic_dentro_delta"] == (-d <= item["ci_lo"] and item["ci_hi"] <= d)
            # Misto na caixa (moderador explica) <=> pi_cobre_beneficio_e_dano no meta.R
            achado = {"certeza": "baixa", "enunciado": "moderador pré-especificado", "fonte": "teste"}
            misto = caixa.rotular_efeito(item, None, "moderada", d, moderador_explica=True,
                                         achado_explicativo=achado)["rotulo"] == "Misto"
            assert misto == r["pi_cobre_beneficio_e_dano"], (delta, chave, r["pi"])
            nulo = caixa.rotular_efeito(item, None, "alta", d)["rotulo"] == "Nulo"
            assert nulo == (r["ic_dentro_delta"] and not r["ic_exclui_zero"])
            vistos.add((chave[1], "misto", misto))
            vistos.add((chave[1], "nulo", nulo))
    # os dados cobrem os dois lados de cada regra (o teste não passa por vacuidade)
    assert {("heterogeneo", "misto", True), ("heterogeneo", "misto", False),
            ("quase_nulo", "nulo", True), ("quase_nulo", "nulo", False)} <= vistos


def test_excluir_rob_critico_pela_linha_de_comando(tmp_path):
    exigir_r("jsonlite", "metafor")
    linhas = efeitos_sinteticos()
    linhas[0]["rob_geral"] = "Crítico"
    entrada = tmp_path / "extraidos.csv"
    efeitos = tmp_path / "efeitos.csv"
    escrever_extraidos(entrada, linhas, extras=["rob_geral"])
    assert rodar("efeitos.R", f"--in={entrada}", f"--out={efeitos}")[0] == 0
    codigo, resumo, _, stderr = rodar("meta.R", f"--in={efeitos}", f"--out-dir={tmp_path / 'out'}",
                                      "--excluir-rob=critico")
    assert codigo == 0, stderr
    assert resumo["n_excluidos_rob_critico"] == 1 and resumo["excluir_rob"] == "critico"
    meta = json.loads((tmp_path / "out" / "meta_resumo.json").read_text(encoding="utf-8"))
    rct = next(g for g in meta["grupos"] if g["grupo"] == "aprendizagem | randomizado")
    assert rct["k_estudos"] == 11 and rct["sensibilidade"]["com_rob_critico"]["k_estudos"] == 12
    assert rct["vies_publicacao"]["preditor_precisao"] == "ep_modificado_smd"  # md_sd traz n1 e n2
    codigo, resumo, _, _ = rodar("meta.R", f"--in={efeitos}", f"--out-dir={tmp_path / 'x'}", "--excluir-rob=tudo")
    assert codigo == 1 and "--excluir-rob" in resumo["erro"]


def test_dependencia_nao_resolvida_sai_com_2(tmp_path):
    exigir_r("jsonlite", "metafor")
    linhas = efeitos_sinteticos()[:12]
    linhas.append(dict(linhas[0], id_efeito="E050", modelo_principal="", tipo_estatistica="t", t="2", n1="60", n2="55"))
    linhas[0]["modelo_principal"] = ""
    entrada = tmp_path / "extraidos.csv"
    efeitos = tmp_path / "efeitos.csv"
    escrever_extraidos(entrada, linhas, extras=["rob_geral"])
    assert rodar("efeitos.R", f"--in={entrada}", f"--out={efeitos}")[0] == 0
    codigo, resumo, _, _ = rodar("meta.R", f"--in={efeitos}", f"--out-dir={tmp_path / 'saida'}")
    assert codigo == 2
    assert resumo["ok"] is False and resumo["n_dependencia_nao_resolvida"] == 1
    codigo, resumo, _, _ = rodar("testes_combinados.R", f"--in={efeitos}", f"--out-dir={tmp_path / 'saida'}")
    assert codigo == 2


def test_erro_de_uso_sai_com_1_e_json(tmp_path):
    exigir_r("jsonlite")
    codigo, resumo, _, _ = rodar("efeitos.R", f"--out={tmp_path / 'x.csv'}")
    assert codigo == 1
    assert resumo["ok"] is False and "--in" in resumo["erro"]
    codigo, resumo, _, _ = rodar("meta.R", f"--in={tmp_path / 'nao_existe.csv'}", "--dependencia=xyz")
    assert codigo == 1


def test_suite_testthat(tmp_path):
    """Roda tests/R (valores de referência) para que `pytest` cubra também o lado R."""
    exigir_r("testthat", "jsonlite", "withr")
    proc = subprocess.run(
        [RSCRIPT, "-e", 'res <- as.data.frame(testthat::test_dir("' + str(DIR_TESTES / "R") + '", reporter = "summary", '
                        'stop_on_failure = FALSE)); cat("\\nFALHAS=", sum(res$failed) + sum(res$error), "\\n")'],
        capture_output=True, text=True, timeout=900, cwd=RAIZ_REPO,
    )
    assert "FALHAS= 0" in proc.stdout, proc.stdout[-4000:] + proc.stderr[-4000:]
