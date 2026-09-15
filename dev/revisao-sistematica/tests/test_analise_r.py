"""Testes de `rs.py analise efeitos|meta|swim|combinados` (wrappers dos scripts R).

O que importa aqui é a costura Python ↔ R: o subcomando entra no `analise` já criado por
efeitos_verificar, o Rscript roda com a raiz do projeto como cwd, o código de saída do R
é devolvido, `analise_executada` cita a entrada e os artefatos com sha256, e dependência
ausente sai com 3 e instrução. Os valores numéricos são testados em tests/R.
Testes que executam R de verdade são pulados sem Rscript/metafor.
"""

import csv
import json
import os
import shutil
import stat
import subprocess
from functools import lru_cache

import pytest

from conftest import ler_jsonl

RSCRIPT = shutil.which("Rscript")


@lru_cache(maxsize=None)
def pacote_r(nome):
    if RSCRIPT is None:
        return False
    proc = subprocess.run([RSCRIPT, "-e", f'cat(requireNamespace("{nome}", quietly = TRUE))'],
                          capture_output=True, text=True, timeout=120)
    return proc.stdout.strip().endswith("TRUE")


def exigir_r(*pacotes):
    if RSCRIPT is None:
        pytest.skip("Rscript não encontrado")
    faltando = [p for p in pacotes if not pacote_r(p)]
    if faltando:
        pytest.skip(f"pacotes R ausentes: {', '.join(faltando)}")


def rodar(raiz, capsys, *argv):
    from rs import construir_parser
    args = construir_parser().parse_args(["--dir", str(raiz), *argv])
    codigo = args.func(args)
    saida = capsys.readouterr().out
    linhas = [l for l in saida.splitlines() if l.strip()]
    return codigo, json.loads(linhas[-1]), saida


def escrever_extraidos(raiz, linhas):
    from rslib import esquema
    caminho = raiz / esquema.ARQ_EFEITOS_EXTRAIDOS
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=esquema.COLUNAS_EFEITOS_EXTRAIDOS)
        w.writeheader()
        for l in linhas:
            w.writerow({c: l.get(c, "") for c in esquema.COLUNAS_EFEITOS_EXTRAIDOS})
    return caminho


def efeitos(modelo_principal_duplicado=False):
    """1 RCT (md_sd) + 3 não randomizados (t, beta_sd, md_sd) no mesmo construto, direções variadas."""
    comum = dict(construto_outcome="participacao", modelo_principal="sim", verificado_humano="sim")
    linhas = [
        dict(comum, id_efeito="Alves2015-E01", chave="Alves2015", id_estudo="ES0001", desenho="RCT",
             estimando="ITT", outcome="frequência", direcao_desejada="aumentar", tipo_estatistica="md_sd",
             m1="88", sd1="10", n1="300", m2="85", sd2="10", n2="300"),
        dict(comum, id_efeito="Borges2017-E01", chave="Borges2017", id_estudo="ES0002", desenho="DiD",
             estimando="ATT", outcome="abandono", direcao_desejada="reduzir", tipo_estatistica="t",
             t="-4.0", df="798", n1="400", n2="400"),
        dict(comum, id_efeito="Castro2019-E01", chave="Castro2019", id_estudo="ES0003",
             desenho="painel com efeitos fixos", estimando="ATE", outcome="matrícula", direcao_desejada="aumentar",
             tipo_estatistica="beta_sd", beta="0.9", se="0.21", sdy="3", n_total="900"),
        dict(comum, id_efeito="Souza2018-E01", chave="Souza2018", id_estudo="ES0004", desenho="RDD",
             estimando="RDD_local", outcome="frequência", direcao_desejada="aumentar", tipo_estatistica="md_sd",
             m1="86", sd1="10", n1="400", m2="83.2", sd2="10", n2="400"),
    ]
    if modelo_principal_duplicado:
        linhas.append(dict(linhas[1], id_efeito="Borges2017-E02", subgrupo="meninas", t="-3.1"))
    return linhas


def eventos_analise(raiz):
    from rslib import esquema
    return [e for e in ler_jsonl(raiz / esquema.ARQ_LOG) if e["evento"] == "analise_executada"]


# ---------------------------------------------------------------------------
# Sem R de verdade
# ---------------------------------------------------------------------------
def test_subcomandos_compartilham_o_comando_analise():
    from rs import construir_parser
    parser = construir_parser()
    for acao in ("preparar-efeitos", "verificar-efeitos", "efeitos", "meta", "swim", "combinados"):
        args = parser.parse_args(["analise", acao])
        assert callable(args.func), acao
    args = parser.parse_args(["analise", "meta", "--grupo", "familia_intervencao,construto_outcome", "--k-min", "2",
                              "--r-arg=--rho=0.5"])
    assert (args.acao_r, args.grupo, args.k_min, args.r_arg) == ("meta", "familia_intervencao,construto_outcome",
                                                                "2", ["--rho=0.5"])


def test_sem_rscript_sai_com_3_e_instrucao(projeto_vazio, capsys, monkeypatch):
    escrever_extraidos(projeto_vazio, efeitos())
    monkeypatch.setenv("RS_RSCRIPT", str(projeto_vazio / "nao_existe" / "Rscript"))
    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", "efeitos")
    assert codigo == 3 and resumo["ok"] is False
    assert "install.packages" in resumo["instrucao"]
    assert eventos_analise(projeto_vazio) == []


def _rscript_falso(pasta, corpo, codigo):
    script = pasta / "Rscript_falso"
    script.write_text(f"#!/bin/sh\necho 'mensagem do R'\necho '{corpo}'\nexit {codigo}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_pacote_ausente_no_r_sai_com_3(projeto_vazio, capsys, monkeypatch, tmp_path):
    from rslib import esquema
    efeitos_csv = projeto_vazio / esquema.ARQ_EFEITOS_CALCULADOS
    efeitos_csv.parent.mkdir(parents=True, exist_ok=True)
    efeitos_csv.write_text("yi,vi\n0.1,0.01\n", encoding="utf-8")
    corpo = json.dumps({"ok": False, "erro": "pacote(s) R ausente(s): metafor", "pacotes_ausentes": ["metafor"]})
    monkeypatch.setenv("RS_RSCRIPT", str(_rscript_falso(tmp_path, corpo, 3)))
    codigo, resumo, saida = rodar(projeto_vazio, capsys, "analise", "meta")
    assert codigo == 3
    assert resumo["pacotes_ausentes"] == ["metafor"] and 'install.packages(c("metafor"))' in resumo["instrucao"]
    assert eventos_analise(projeto_vazio) == []


def test_entrada_ausente_sai_com_1(projeto_vazio, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("RS_RSCRIPT", str(_rscript_falso(tmp_path, "{}", 0)))
    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", "swim")
    assert codigo == 1 and "analise efeitos" in resumo["erro"]


def test_repassa_argumentos_e_codigo_do_r(projeto_vazio, capsys, monkeypatch, tmp_path):
    """Com um Rscript falso que ecoa os argumentos, confere caminhos relativos à raiz e o evento."""
    from rslib import esquema
    efeitos_csv = projeto_vazio / esquema.ARQ_EFEITOS_CALCULADOS
    efeitos_csv.parent.mkdir(parents=True, exist_ok=True)
    efeitos_csv.write_text("yi,vi\n0.1,0.01\n", encoding="utf-8")
    (projeto_vazio / "06-analise/swim_resumo.json").write_text("{}", encoding="utf-8")
    script = tmp_path / "Rscript_eco"
    script.write_text('#!/bin/sh\necho "RESSALVA de teste"\n'
                      'printf \'{"ok": false, "argv": "%s", "resumo_json": "06-analise/swim_resumo.json"}\\n\' "$*"\n'
                      "exit 2\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("RS_RSCRIPT", str(script))
    codigo, resumo, saida = rodar(projeto_vazio, capsys, "analise", "swim", "--grupo", "construto_outcome",
                                  "--separar-desenho", "nao", "--r-arg=--nivel=0.9")
    assert codigo == 2 and resumo["codigo_r"] == 2
    assert saida.splitlines()[0] == "RESSALVA de teste"
    argv = resumo["resumo_r"]["argv"]
    assert "--in=06-analise/efeitos.csv" in argv and "--out-dir=06-analise" in argv
    assert "--grupo=construto_outcome" in argv and "--separar-desenho=nao" in argv and "--nivel=0.9" in argv
    ev = eventos_analise(projeto_vazio)[-1]
    assert ev["dados"]["codigo_saida"] == 2 and ev["dados"]["script"] == "swim.R"
    assert [a["caminho"] for a in ev["artefatos"]] == ["06-analise/efeitos.csv", "06-analise/swim_resumo.json"]


def test_meta_repassa_excluir_rob(projeto_vazio, capsys, monkeypatch, tmp_path):
    """Regressão: `analise meta --excluir-rob critico` chega ao meta.R como --excluir-rob=critico."""
    from rs import construir_parser
    from rslib import esquema
    args = construir_parser().parse_args(["analise", "meta", "--excluir-rob", "critico"])
    assert args.excluir_rob == "critico"
    efeitos_csv = projeto_vazio / esquema.ARQ_EFEITOS_CALCULADOS
    efeitos_csv.parent.mkdir(parents=True, exist_ok=True)
    efeitos_csv.write_text("yi,vi,rob_geral\n0.1,0.01,critico\n", encoding="utf-8")
    script = tmp_path / "Rscript_eco"
    script.write_text('#!/bin/sh\nprintf \'{"ok": true, "argv": "%s"}\\n\' "$*"\nexit 0\n', encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("RS_RSCRIPT", str(script))
    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", "meta", "--excluir-rob", "critico", "--delta", "0.1")
    assert codigo == 0
    assert "--excluir-rob=critico" in resumo["resumo_r"]["argv"] and "--delta=0.1" in resumo["resumo_r"]["argv"]


@pytest.mark.parametrize("acao", ["swim", "combinados"])
def test_regressao_swim_e_combinados_repassam_excluir_rob(projeto_vazio, capsys, monkeypatch, tmp_path, acao):
    """Regressão: swim e combinados não tinham --excluir-rob (o contorno era filtrar a entrada à mão)."""
    from rs import construir_parser
    from rslib import esquema
    assert construir_parser().parse_args(["analise", acao, "--excluir-rob", "critico"]).excluir_rob == "critico"
    efeitos_csv = projeto_vazio / esquema.ARQ_EFEITOS_CALCULADOS
    efeitos_csv.parent.mkdir(parents=True, exist_ok=True)
    efeitos_csv.write_text("yi,vi,rob_geral\n0.1,0.01,critico\n", encoding="utf-8")
    script = tmp_path / "Rscript_eco"
    script.write_text('#!/bin/sh\nprintf \'{"ok": true, "argv": "%s"}\\n\' "$*"\nexit 0\n', encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("RS_RSCRIPT", str(script))
    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", acao, "--excluir-rob", "critico")
    assert codigo == 0
    assert "--excluir-rob=critico" in resumo["resumo_r"]["argv"]


def test_swim_e_combinados_excluir_rob_com_r(projeto_vazio, capsys):
    exigir_r("jsonlite")
    from rslib import esquema
    linhas = efeitos()
    for l in linhas:
        l["rob_geral"] = "baixo"
    linhas[1]["rob_geral"] = "critico"
    caminho = projeto_vazio / esquema.ARQ_EFEITOS_EXTRAIDOS
    caminho.parent.mkdir(parents=True, exist_ok=True)
    colunas = esquema.COLUNAS_EFEITOS_EXTRAIDOS + ["rob_geral"]
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colunas)
        w.writeheader()
        for l in linhas:
            w.writerow({c: l.get(c, "") for c in colunas})
    assert rodar(projeto_vazio, capsys, "analise", "efeitos")[0] == 0
    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", "swim", "--excluir-rob", "critico")
    assert codigo == 0, resumo
    assert resumo["resumo_r"]["n_excluidos_rob_critico"] == 1
    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", "combinados", "--excluir-rob", "critico")
    assert codigo == 0, resumo
    assert resumo["resumo_r"]["n_excluidos_rob_critico"] == 1 and resumo["resumo_r"]["excluir_rob"] == "critico"


# ---------------------------------------------------------------------------
# Com R
# ---------------------------------------------------------------------------
def test_fluxo_efeitos_meta_swim_combinados(projeto_vazio, capsys):
    exigir_r("jsonlite", "metafor")
    from rslib import esquema, estado
    escrever_extraidos(projeto_vazio, efeitos())

    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", "efeitos")
    assert codigo == 0, resumo
    assert resumo["resumo_r"]["n_calculados"] == 4 and resumo["resumo_r"]["n_invertidos"] == 1
    assert resumo["arquivos"] == [esquema.ARQ_EFEITOS_CALCULADOS]
    with open(projeto_vazio / esquema.ARQ_EFEITOS_CALCULADOS, encoding="utf-8") as f:
        assert next(csv.reader(f)) == esquema.COLUNAS_EFEITOS_CALCULADOS

    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", "meta")
    assert codigo == 0, resumo
    meta = json.loads((projeto_vazio / esquema.ARQ_META_RESUMO).read_text(encoding="utf-8"))
    status = {g["grupo"]: g["status"] for g in meta["grupos"]}
    assert status == {"participacao | nao_randomizado": "meta_ajustada", "participacao | randomizado": "k_insuficiente"}
    assert meta["entrada"] == esquema.ARQ_EFEITOS_CALCULADOS  # relativo à raiz: o R rodou com cwd = projeto
    assert esquema.ARQ_META_RESUMO in resumo["arquivos"]
    assert any(a.startswith("06-analise/figuras/forest_") for a in resumo["arquivos"])

    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", "swim")
    assert codigo == 0 and esquema.ARQ_SWIM_RESUMO in resumo["arquivos"]

    codigo, resumo, saida = rodar(projeto_vazio, capsys, "analise", "combinados")
    assert codigo == 0 and saida.startswith("RESSALVA")
    assert "06-analise/testes_combinados.json" in resumo["arquivos"]

    evs = eventos_analise(projeto_vazio)
    assert [e["dados"]["script"] for e in evs] == ["efeitos.R", "meta.R", "swim.R", "testes_combinados.R"]
    for ev in evs:
        assert ev["etapa"] == "10_sintese" and ev["ator"]["tipo"] == "script"
        for art in ev["artefatos"]:
            assert art["sha256"] == estado.sha256_arquivo(projeto_vazio / art["caminho"]), art

    # reexecução com as mesmas entradas: novo evento marcado como reexecução, sem linhas duplicadas
    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", "efeitos")
    assert codigo == 0 and eventos_analise(projeto_vazio)[-1]["dados"]["reexecucao"] is True
    with open(projeto_vazio / esquema.ARQ_EFEITOS_CALCULADOS, encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 4


def test_meta_com_dependencia_nao_resolvida_devolve_2_e_registra(projeto_vazio, capsys):
    exigir_r("jsonlite", "metafor")
    linhas = efeitos(modelo_principal_duplicado=True)  # Borges2017 com dois modelos principais
    escrever_extraidos(projeto_vazio, linhas)
    assert rodar(projeto_vazio, capsys, "analise", "efeitos")[0] == 0
    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", "meta")
    assert codigo == 2 and resumo["ok"] is False
    assert resumo["resumo_r"]["n_dependencia_nao_resolvida"] == 1
    assert eventos_analise(projeto_vazio)[-1]["dados"]["codigo_saida"] == 2


def test_meta_excluir_rob_sem_coluna_rob_geral_sai_com_1(projeto_vazio, capsys):
    exigir_r("jsonlite", "metafor")
    escrever_extraidos(projeto_vazio, efeitos())
    assert rodar(projeto_vazio, capsys, "analise", "efeitos")[0] == 0
    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", "meta", "--excluir-rob", "critico")
    assert codigo == 1 and "rob_geral" in resumo["resumo_r"]["erro"]
    assert [e["dados"]["script"] for e in eventos_analise(projeto_vazio)] == ["efeitos.R"]  # erro de dados não registra


def test_dispatcher_real_por_subprocesso(projeto_vazio):
    """Mesmo caminho do usuário: `python3 rs.py analise efeitos` num processo novo."""
    exigir_r("jsonlite")
    import sys

    from conftest import SCRIPTS
    escrever_extraidos(projeto_vazio, efeitos())
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("RS_RSCRIPT", None)
    proc = subprocess.run([sys.executable, str(SCRIPTS / "rs.py"), "--dir", str(projeto_vazio), "analise", "efeitos"],
                          capture_output=True, text=True, timeout=600, env=env)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout.strip().splitlines()[-1])["ok"] is True


def test_regressao_analise_efeitos_em_parcial_meta_sem_pdfs_nao_manda_verificar(projeto_vazio, capsys, monkeypatch,
                                                                                 tmp_path):
    from rslib import esquema, estado
    est = estado.carregar_estado(projeto_vazio)
    est["projeto"]["parcial"] = "meta"
    est["projeto"]["etapas_ignoradas"] = [e for e in esquema.ETAPAS if e not in {"00_configuracao", "10_sintese"}]
    estado.salvar_estado(projeto_vazio, est)
    escrever_extraidos(projeto_vazio, [{"id_efeito": "E1", "chave": "Silva2019", "verificado_humano": "sim"},
                                       {"id_efeito": "E2", "chave": "Souza2020", "verificado_humano": ""}])
    (projeto_vazio / esquema.ARQ_EFEITOS_CALCULADOS).parent.mkdir(parents=True, exist_ok=True)
    (projeto_vazio / esquema.ARQ_EFEITOS_CALCULADOS).write_text("yi,vi\n0.1,0.01\n", encoding="utf-8")
    corpo = json.dumps({"ok": True, "saida": esquema.ARQ_EFEITOS_CALCULADOS})
    monkeypatch.setenv("RS_RSCRIPT", str(_rscript_falso(tmp_path, corpo, 0)))
    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", "efeitos")
    assert codigo == 0
    texto = " ".join(resumo["avisos"])
    assert "verificar-efeitos ainda não rodou" not in texto and "não rode `analise verificar-efeitos`" in texto
    assert "não foram verificados contra os PDFs" in texto and "1 de 2" in texto

    # projeto completo: o aviso de sempre
    est["projeto"]["parcial"] = None
    est["projeto"]["etapas_ignoradas"] = []
    estado.salvar_estado(projeto_vazio, est)
    codigo, resumo, _ = rodar(projeto_vazio, capsys, "analise", "efeitos")
    assert any("verificar-efeitos ainda não rodou" in a for a in resumo["avisos"])
