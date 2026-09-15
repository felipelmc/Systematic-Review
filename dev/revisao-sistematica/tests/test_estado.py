"""Testes de estado.py: trava entre processos, mescla em três vias, estado corrompido e permissões."""

import json
import os
import stat
import subprocess
import sys
import time

import pytest

from conftest import SCRIPTS, ler_jsonl

N_PROCESSOS = 8
N_POR_PROCESSO = 5

TRABALHADOR = r"""
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from rslib import estado
raiz, n_proc, n = Path(sys.argv[2]), sys.argv[3], int(sys.argv[4])
largada = raiz / "largada"
while not largada.exists():
    time.sleep(0.005)
for i in range(n):
    # 1) pendência (id calculado dentro da trava)
    estado.abrir_pendencia(raiz, "teste", "06_triagem_ta", f"p{n_proc}-{i}")
    # 2) estado carregado FORA da trava, alterado e salvo por registrar_evento (mescla em três vias)
    est = estado.carregar_estado(raiz)
    est["versoes_ativas"][f"proc{n_proc}_{i}"] = i
    est["artefatos"][f"arq_{n_proc}_{i}"] = {"caminho": f"arq_{n_proc}_{i}", "sha256": ""}
    time.sleep(0.002)
    estado.registrar_evento(raiz, "erro", "00_configuracao", "script", f"proc{n_proc}", dados={"i": i}, estado=est)
    # 3) evento sem estado
    estado.registrar_evento(raiz, "erro", "00_configuracao", "script", f"proc{n_proc}", dados={"j": i})
"""


def test_regressao_trava_entre_processos_seq_nunca_repete_e_nada_se_perde(projeto_vazio, tmp_path):
    """8 processos em paralelo: seq único e contíguo, pendências com ids únicos e nenhuma mudança de estado perdida."""
    from rslib import estado
    script = tmp_path / "trabalhador.py"
    script.write_text(TRABALHADOR, encoding="utf-8")
    procs = [subprocess.Popen([sys.executable, str(script), str(SCRIPTS), str(projeto_vazio), str(k), str(N_POR_PROCESSO)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) for k in range(N_PROCESSOS)]
    time.sleep(0.3)
    (projeto_vazio / "largada").write_text("ok", encoding="utf-8")
    for p in procs:
        _, erro = p.communicate(timeout=120)
        assert p.returncode == 0, erro.decode("utf-8", "replace")

    eventos = ler_jsonl(projeto_vazio / "rs_log.jsonl")
    seqs = [e["seq"] for e in eventos]
    total = 1 + N_PROCESSOS * N_POR_PROCESSO * 3  # projeto_criado + 3 eventos por iteração
    assert len(seqs) == total and len(set(seqs)) == total
    assert sorted(seqs) == list(range(1, total + 1)) and seqs == sorted(seqs)

    est = estado.carregar_estado(projeto_vazio)
    ids = [p["id"] for p in est["pendencias"]]
    assert len(ids) == N_PROCESSOS * N_POR_PROCESSO and len(set(ids)) == len(ids)
    assert {p["descricao"] for p in est["pendencias"]} == {
        f"p{k}-{i}" for k in range(N_PROCESSOS) for i in range(N_POR_PROCESSO)}
    abertas = [e["dados"]["pendencia"] for e in eventos if e["evento"] == "pendencia_aberta"]
    assert sorted(abertas) == sorted(ids)
    for k in range(N_PROCESSOS):
        for i in range(N_POR_PROCESSO):
            assert est["versoes_ativas"][f"proc{k}_{i}"] == i
            assert f"arq_{k}_{i}" in est["artefatos"]
    assert est["ultimo_seq"] == total


def test_mescla_em_tres_vias_preserva_mudancas_de_outro_processo(projeto_vazio):
    from rslib import estado
    meu = estado.carregar_estado(projeto_vazio)
    # outro "processo" grava depois da leitura: nova busca, nova pendência e modo alterado
    outro = estado.carregar_estado(projeto_vazio)
    outro["buscas"].append({"id": "B01", "fonte": "wos"})
    outro["modo"]["autonomia"] = "autopiloto"
    outro["projeto"]["etapas_ignoradas"] = ["02_teoria_framework"]
    estado.salvar_estado(projeto_vazio, outro)
    pid = estado.abrir_pendencia(projeto_vazio, "teste", "06_triagem_ta", "de outro processo")
    # este processo muda outros campos e o mesmo campo de busca (conflito: vale quem grava agora)
    meu["buscas"].append({"id": "B02", "fonte": "scopus"})
    meu["projeto"]["pergunta"] = "X reduz Y?"
    meu["projeto"]["etapas_ignoradas"] = ["08_piloto_extracao"]
    estado.registrar_evento(projeto_vazio, "erro", "00_configuracao", "script", "teste", estado=meu)
    final = estado.carregar_estado(projeto_vazio)
    assert [b["id"] for b in final["buscas"]] == ["B01", "B02"]
    assert final["modo"]["autonomia"] == "autopiloto" and final["projeto"]["pergunta"] == "X reduz Y?"
    assert [p["id"] for p in final["pendencias"]] == [pid]
    assert sorted(final["projeto"]["etapas_ignoradas"]) == ["02_teoria_framework", "08_piloto_extracao"]
    assert final["ultimo_seq"] == max(e["seq"] for e in estado.ler_log(projeto_vazio))
    # o objeto do chamador foi atualizado no lugar: salvar de novo não desfaz a mudança do outro
    estado.salvar_estado(projeto_vazio, meu)
    assert estado.carregar_estado(projeto_vazio)["modo"]["autonomia"] == "autopiloto"


def test_mudanca_propria_vence_e_dict_novo_substitui(projeto_vazio):
    from rslib import estado
    est = estado.carregar_estado(projeto_vazio)
    est["ultimo_seq"] = 0  # mudança deliberada deste processo vale (status acusa estado atrás do log)
    estado.salvar_estado(projeto_vazio, est)
    assert estado.carregar_estado(projeto_vazio)["ultimo_seq"] == 0
    novo = estado.estado_inicial("Outro título")  # dict que não veio do disco: substitui o arquivo
    estado.salvar_estado(projeto_vazio, novo)
    assert estado.carregar_estado(projeto_vazio)["projeto"]["titulo"] == "Outro título"


def test_trava_e_reentrante(projeto_vazio):
    from rslib import estado
    with estado.trava(projeto_vazio):
        with estado.trava(projeto_vazio):
            pid = estado.abrir_pendencia(projeto_vazio, "teste", "06_triagem_ta", "dentro da trava")
        assert estado.fechar_pendencia(projeto_vazio, pid, "ok")
    assert (projeto_vazio / estado.ARQ_TRAVA).exists()


def test_regressao_estado_corrompido_vira_erro_projeto_com_dica(projeto_vazio, capsys):
    from rslib import estado
    (projeto_vazio / "rs_estado.json").write_text('{"schema": "rs-estado/1", "projeto": ', encoding="utf-8")
    with pytest.raises(estado.ErroProjeto) as erro:
        estado.carregar_estado(projeto_vazio)
    assert "corrompido" in str(erro.value) and "controle de versão" in str(erro.value)
    from test_prisma import rodar
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "status")
    assert codigo == 1 and res["ok"] is False and "corrompido" in res["detalhe"]
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert codigo == 1 and res["ok"] is False and "corrompido" in res["detalhe"]


@pytest.mark.skipif(os.name == "nt", reason="permissões POSIX")
def test_regressao_escrita_atomica_com_permissao_de_arquivo_comum(projeto_vazio):
    from rslib import estado
    modo = stat.S_IMODE(os.stat(projeto_vazio / "rs_estado.json").st_mode)
    assert modo == estado.modo_arquivo_padrao() and modo & 0o044  # legível pelo grupo/outros com umask 022
    alvo = projeto_vazio / "07-relatorio" / "x.csv"
    estado.escrever_atomico(alvo, "a,b\n1,2\n", newline="")
    assert alvo.read_text(encoding="utf-8") == "a,b\n1,2\n"
    assert stat.S_IMODE(os.stat(alvo).st_mode) == estado.modo_arquivo_padrao()
    assert not [p for p in alvo.parent.iterdir() if p.name.endswith(".tmp")]
    json.loads((projeto_vazio / "rs_estado.json").read_text(encoding="utf-8"))
