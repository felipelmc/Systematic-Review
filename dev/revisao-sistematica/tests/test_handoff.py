"""Testes dos handoffs: incluidos.csv, .bib (irmã falsa e fallback), descoberta de irmãs e CSV atômico."""

import argparse
import json
import re

from test_textos import escrever_unicos


def rodar(argv, capsys):
    from rslib import handoff
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    sub = parser.add_subparsers(dest="comando")
    handoff.registrar(sub)
    args = parser.parse_args(argv)
    codigo = args.func(args)
    return codigo, json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def preparar(raiz):
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_csv
    escrever_unicos(raiz, ["Alves2020", "Borges2019", "Castro2018"])
    cols, linhas = ler_csv(raiz / esquema.ARQ_UNICOS)
    linhas[1]["tipo_publicacao"] = "tese"
    linhas[1]["veiculo"] = "Universidade Exemplo"
    linhas[1]["autores"] = "Borges, Carla | Organisation for Research and Development"
    escrever_csv(raiz / esquema.ARQ_UNICOS, cols, linhas)
    escrever_csv(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL, esquema.COLUNAS_ELEGIBILIDADE_FINAL, [
        {"id_rs": "RS0002", "chave": "Borges2019", "decisao": "incluir"},
        {"id_rs": "RS0001", "chave": "Alves2020", "decisao": "incluir"},
        {"id_rs": "RS0003", "chave": "Castro2018", "decisao": "excluir", "criterio_falhou": "C2"}])


def test_incluidos(projeto_vazio, capsys):
    from rslib import esquema, estado
    from rslib.handoff import ler_csv
    preparar(projeto_vazio)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "incluidos"], capsys)
    assert codigo == 0 and resumo["n_incluidos"] == 2 and resumo["fonte"] == "tc"
    colunas, linhas = ler_csv(projeto_vazio / esquema.ARQ_INCLUIDOS)
    assert colunas == esquema.COLUNAS_INCLUIDOS
    assert [l["chave"] for l in linhas] == ["Alves2020", "Borges2019"]
    assert linhas[1]["nome_publicacao"] == "Universidade Exemplo" and linhas[1]["tipo_publicacao"] == "tese"
    assert estado.ler_log(projeto_vazio)[-1]["evento"] == "relatorio_gerado"


def test_incluidos_sem_tc_e_fonte_ta(projeto_vazio, capsys):
    from rslib import esquema
    from rslib.handoff import escrever_csv
    escrever_unicos(projeto_vazio, ["Alves2020", "Borges2019"])
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "incluidos"], capsys)
    assert codigo == 1 and "--fonte ta" in resumo["erro"]
    escrever_csv(projeto_vazio / esquema.ARQ_TRIAGEM_TA_FINAL, esquema.COLUNAS_TRIAGEM_FINAL, [
        {"id_rs": "RS0001", "decisao_final": "incluir"}, {"id_rs": "RS0002", "decisao_final": "incerto"}])
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "incluidos", "--fonte", "ta"], capsys)
    assert codigo == 0 and resumo["n_incluidos"] == 1 and resumo["avisos"]


def test_bib_fallback_minimo(projeto_vazio, capsys):
    preparar(projeto_vazio)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bib", "--sem-irma"], capsys)
    assert codigo == 0 and resumo["via"] == "fallback" and resumo["avisos"] == []
    bib = (projeto_vazio / "07-relatorio/references.bib").read_text(encoding="utf-8")
    assert re.findall(r"@(\w+)\{(\w+),", bib) == [("article", "Alves2020"), ("phdthesis", "Borges2019")]
    assert "school = {Universidade Exemplo}" in bib and "doi = {10.1234/alves2020}" in bib
    assert "author = {Borges, Carla and {Organisation for Research and Development}}" in bib


def test_bib_via_irma_falsa(projeto_vazio, capsys, tmp_path, monkeypatch):
    from rslib import handoff
    preparar(projeto_vazio)
    irma = tmp_path / "skills" / "gerar-bibtex"
    (irma / "scripts").mkdir(parents=True)
    (irma / "scripts" / "gerar_bib.py").write_text(
        "import argparse, csv\n"
        "ap = argparse.ArgumentParser(); ap.add_argument('--planilha'); ap.add_argument('--out');"
        " ap.add_argument('--col-chave'); a = ap.parse_args()\n"
        "rows = list(csv.DictReader(open(a.planilha, encoding='utf-8')))\n"
        "open(a.out, 'w').write('\\n'.join('@article{%s,\\n}' % r[a.col_chave] for r in rows))\n",
        encoding="utf-8")
    monkeypatch.setenv("CLAUDE_SKILL_DIR", str(tmp_path / "skills" / "revisao-sistematica"))
    assert handoff.localizar_skill_irma("gerar-bibtex", "scripts/gerar_bib.py") == irma.resolve()
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bib"], capsys)
    assert codigo == 0 and resumo["via"] == "gerar-bibtex" and resumo["avisos"] == []

    # irmã que falha cai no fallback com aviso
    (irma / "scripts" / "gerar_bib.py").write_text("raise SystemExit(4)\n", encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bib"], capsys)
    assert codigo == 0 and resumo["via"] == "fallback" and "falhou" in resumo["avisos"][0]


def test_bib_avisa_chaves_divergentes(projeto_vazio, capsys, tmp_path, monkeypatch):
    preparar(projeto_vazio)
    irma = tmp_path / "skills" / "gerar-bibtex"
    (irma / "scripts").mkdir(parents=True)
    (irma / "scripts" / "gerar_bib.py").write_text(
        "import argparse\nap = argparse.ArgumentParser(); ap.add_argument('--planilha'); ap.add_argument('--out');"
        " ap.add_argument('--col-chave'); a = ap.parse_args()\nopen(a.out, 'w').write('@article{Outra2000,\\n}')\n",
        encoding="utf-8")
    monkeypatch.setenv("CLAUDE_SKILL_DIR", str(tmp_path / "skills" / "revisao-sistematica"))
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bib"], capsys)
    assert codigo == 0 and any("diferem" in a for a in resumo["avisos"])


def test_csv_utilitarios(tmp_path):
    from rslib.handoff import escrever_csv, ler_csv
    arq = tmp_path / "x.csv"
    arq.write_bytes("﻿a,b\n1,\"com, vírgula\"\n".encode("utf-8"))
    assert ler_csv(arq) == (["a", "b"], [{"a": "1", "b": "com, vírgula"}])
    escrever_csv(arq, ["b", "a"], [{"a": "1", "b": "2", "extra": "ignorado"}, {"a": None}])
    assert arq.read_text(encoding="utf-8") == "b,a\n2,1\n,\n"
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]


def test_sem_projeto(tmp_path, capsys):
    codigo, resumo = rodar(["--dir", str(tmp_path), "incluidos"], capsys)
    assert codigo == 1 and resumo["ok"] is False


# ---------------------------------------------------------------------------
# Pendências únicas: sem duplicar, n atualizado, fechamento automático, sem reabrir o resolvido
# ---------------------------------------------------------------------------
def _modo(raiz, autonomia):
    from rslib import estado
    est = estado.carregar_estado(raiz)
    est["modo"]["autonomia"] = autonomia
    estado.salvar_estado(raiz, est)


def _eventos(raiz, nome):
    from rslib import estado
    return [e for e in estado.ler_log(raiz) if e["evento"] == nome]


def _arquivo(raiz, texto):
    caminho = raiz / "06-analise" / "caixa_ferramentas.csv"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
    return "06-analise/caixa_ferramentas.csv"


def test_pendencia_unica_nao_duplica_e_atualiza_n(projeto_vazio):
    from rslib import estado
    from rslib.handoff import abrir_pendencia_unica
    _modo(projeto_vazio, "autopiloto")
    rel = _arquivo(projeto_vazio, "celula,status_rotulo\nC1,pendente\n")
    args = ("certeza_caixa", "10_sintese", "completar certeza")
    p1 = abrir_pendencia_unica(projeto_vazio, *args, portao="G8", n=3, arquivo=rel)
    assert abrir_pendencia_unica(projeto_vazio, *args, portao="G8", n=3, arquivo=rel) == p1
    assert len(_eventos(projeto_vazio, "pendencia_aberta")) == 1

    p2 = abrir_pendencia_unica(projeto_vazio, *args, portao="G8", n=5, arquivo=rel)
    assert p2 != p1
    abertas = estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))
    assert [(p["id"], p["n"]) for p in abertas] == [(p2, 5)] and f"[substitui {p1}]" in abertas[0]["descricao"]
    fechamento = _eventos(projeto_vazio, "pendencia_fechada")[-1]
    assert fechamento["dados"]["pendencia"] == p1 and "3 -> 5" in fechamento["motivo"]
    assert fechamento["ator"]["tipo"] == "script"
    assert abrir_pendencia_unica(projeto_vazio, *args, portao="G8", n=5, arquivo=rel) == p2
    assert len(_eventos(projeto_vazio, "pendencia_aberta")) == 2


def test_pendencia_unica_fecha_duplicatas_herdadas(projeto_vazio):
    from rslib import estado
    from rslib.handoff import abrir_pendencia_unica
    _modo(projeto_vazio, "autopiloto")
    rel = _arquivo(projeto_vazio, "x\n")
    a = estado.abrir_pendencia(projeto_vazio, "certeza_caixa", "10_sintese", "d", n=2, arquivo=rel)
    estado.abrir_pendencia(projeto_vazio, "certeza_caixa", "10_sintese", "d", n=2, arquivo=rel)
    assert abrir_pendencia_unica(projeto_vazio, "certeza_caixa", "10_sintese", "d", n=2, arquivo=rel) == a
    assert [p["id"] for p in estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))] == [a]


def test_fechar_se_resolvida_idempotente_e_em_qualquer_modo(projeto_vazio):
    from rslib import estado
    from rslib.handoff import abrir_pendencia_unica, fechar_se_resolvida
    _modo(projeto_vazio, "autopiloto")
    rel = _arquivo(projeto_vazio, "x\n")
    pid = abrir_pendencia_unica(projeto_vazio, "verificacao_humana_efeitos", "09_extracao_rob", "conferir", n=2,
                                arquivo=rel)
    outra = abrir_pendencia_unica(projeto_vazio, "verificacao_humana_efeitos", "09_extracao_rob", "conferir", n=1,
                                  arquivo="05-decomposicao/outro.csv")
    _modo(projeto_vazio, "checkpoints")  # mudou de modo: a pendência antiga ainda precisa fechar
    assert fechar_se_resolvida(projeto_vazio, "verificacao_humana_efeitos", arquivo=rel) == [pid]
    assert fechar_se_resolvida(projeto_vazio, "verificacao_humana_efeitos", arquivo=rel) == []
    assert len(_eventos(projeto_vazio, "pendencia_fechada")) == 1
    ev = _eventos(projeto_vazio, "pendencia_fechada")[-1]
    assert ev["ator"]["tipo"] == "script" and "resolvida" in ev["motivo"]
    assert [p["id"] for p in estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))] == [outra]
    assert fechar_se_resolvida(projeto_vazio, "verificacao_humana_efeitos", qualquer_arquivo=True,
                               motivo="todos aptos") == [outra]


def test_nao_reabre_o_que_humano_resolveu_sobre_o_mesmo_conteudo(projeto_vazio):
    from rslib import estado
    from rslib.handoff import abrir_pendencia_unica
    _modo(projeto_vazio, "autopiloto")
    rel = _arquivo(projeto_vazio, "id_rs,decisao\nRS0001,incluir\n")
    args = ("conferencia_elegibilidade_tc", "07_textos_elegibilidade", "conferir decisões")
    pid = abrir_pendencia_unica(projeto_vazio, *args, portao="G5", n=1, arquivo=rel)
    estado.fechar_pendencia(projeto_vazio, pid, "conferi as decisões")  # humano
    assert abrir_pendencia_unica(projeto_vazio, *args, portao="G5", n=1, arquivo=rel) is None
    assert estado.pendencias_abertas(estado.carregar_estado(projeto_vazio)) == []
    assert len(_eventos(projeto_vazio, "pendencia_aberta")) == 1

    _arquivo(projeto_vazio, "id_rs,decisao\nRS0001,excluir\n")  # conteúdo novo precisa de nova conferência
    nova = abrir_pendencia_unica(projeto_vazio, *args, portao="G5", n=1, arquivo=rel)
    assert nova and nova != pid

    estado.fechar_pendencia(projeto_vazio, nova, "resolvida", ator_tipo="script", ator_id="teste")
    assert abrir_pendencia_unica(projeto_vazio, *args, portao="G5", n=1, arquivo=rel)  # fechada por script reabre


def test_sincronizar_pendencia_unica_e_checkpoints(projeto_vazio):
    from rslib import estado
    from rslib.handoff import abrir_pendencia_unica, sincronizar_pendencia_unica
    rel = _arquivo(projeto_vazio, "x\n")
    assert abrir_pendencia_unica(projeto_vazio, "certeza_caixa", "10_sintese", "d", n=2, arquivo=rel) is None
    _modo(projeto_vazio, "autopiloto")
    pid = sincronizar_pendencia_unica(projeto_vazio, "certeza_caixa", "10_sintese", "d", 2, portao="G8", arquivo=rel)
    assert pid
    assert sincronizar_pendencia_unica(projeto_vazio, "certeza_caixa", "10_sintese", "d", 0, portao="G8",
                                       arquivo=rel, motivo_resolvida="todas as células definidas") is None
    assert estado.pendencias_abertas(estado.carregar_estado(projeto_vazio)) == []
    assert _eventos(projeto_vazio, "pendencia_fechada")[-1]["motivo"] == "todas as células definidas"


def test_regressao_pendencia_aberta_atualiza_n_mesmo_fora_do_autopiloto(projeto_vazio):
    """Criar depende do modo; atualizar o n de uma pendência já aberta e fechá-la valem em qualquer modo."""
    from rslib import estado
    from rslib.handoff import abrir_pendencia_unica, sincronizar_pendencia_unica
    rel = _arquivo(projeto_vazio, "x\n")
    _modo(projeto_vazio, "autopiloto")
    p1 = sincronizar_pendencia_unica(projeto_vazio, "fila_humana_triagem", "06_triagem_ta", "d", 4, portao="G4",
                                     arquivo=rel)
    _modo(projeto_vazio, "checkpoints")
    assert abrir_pendencia_unica(projeto_vazio, "fila_humana_triagem", "06_triagem_ta", "d", n=4, arquivo=rel) == p1
    p2 = sincronizar_pendencia_unica(projeto_vazio, "fila_humana_triagem", "06_triagem_ta", "d", 2, portao="G4",
                                     arquivo=rel)
    assert p2 and p2 != p1
    assert [(p["id"], p["n"]) for p in estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))] == [(p2, 2)]
    # em checkpoints, sem pendência aberta, nada é criado
    assert sincronizar_pendencia_unica(projeto_vazio, "outra", "06_triagem_ta", "d", 3, arquivo=rel) is None
    assert sincronizar_pendencia_unica(projeto_vazio, "fila_humana_triagem", "06_triagem_ta", "d", 0,
                                       arquivo=rel) is None
    assert estado.pendencias_abertas(estado.carregar_estado(projeto_vazio)) == []


def test_regressao_qualquer_modo_e_qualquer_arquivo_ao_fechar(projeto_vazio):
    from rslib import estado
    from rslib.handoff import sincronizar_pendencia_unica
    rel = _arquivo(projeto_vazio, "x\n")
    pid = sincronizar_pendencia_unica(projeto_vazio, "retratacao_texto", "07_textos_elegibilidade", "d", 2,
                                      portao="G5", arquivo=rel, qualquer_modo=True)  # checkpoints
    assert pid and estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))[0]["n"] == 2
    herdada = estado.abrir_pendencia(projeto_vazio, "dedup_candidatos", "05_organizacao", "d", n=1,
                                     arquivo="01-busca/caminho_antigo.csv")
    sincronizar_pendencia_unica(projeto_vazio, "dedup_candidatos", "05_organizacao", "d", 0,
                                arquivo="01-busca/dedup_pares.csv", qualquer_arquivo_ao_fechar=True)
    assert herdada not in [p["id"] for p in estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))]


def test_regressao_comandos_usam_a_sincronizacao_do_handoff():
    """Nenhum comando abre pendência por contagem sem passar por handoff (evita duplicar ou deixar aberta)."""
    import re
    from conftest import SCRIPTS
    permitidos = {"estado.py", "handoff.py", "projeto.py"}  # projeto: pendências manuais e de portão
    for arq in sorted((SCRIPTS / "rslib").rglob("*.py")):
        if arq.name in permitidos:
            continue
        texto = arq.read_text(encoding="utf-8")
        assert not re.search(r"estado\.(abrir|fechar)_pendencia\(", texto), arq.name
        assert "abrir_pendencia_unica(" not in texto, f"{arq.name}: use sincronizar_pendencia_unica"


def test_regressao_escrita_atomica_do_handoff_usa_permissao_padrao(tmp_path):
    """CSV e texto dos handoffs (registros_unicos.csv regravado por textos, filas, .bib) legíveis por coautores."""
    import os
    import stat
    import pytest
    from rslib import estado, handoff
    if os.name == "nt":
        pytest.skip("permissões POSIX")
    handoff.escrever_csv(tmp_path / "sub" / "t.csv", ["x", "y"], [{"x": 1, "y": None, "z": "extra"}])
    handoff.escrever_texto(tmp_path / "t.md", "linha 1\r\nlinha 2\n")
    for caminho in (tmp_path / "sub" / "t.csv", tmp_path / "t.md"):
        modo = stat.S_IMODE(caminho.stat().st_mode)
        assert modo == estado.modo_arquivo_padrao() and modo & 0o044, (caminho, oct(modo))
    assert (tmp_path / "sub" / "t.csv").read_bytes() == b"x,y\n1,\n"
    assert (tmp_path / "t.md").read_bytes() == b"linha 1\r\nlinha 2\n"  # quebras de linha preservadas
    assert not [p for p in tmp_path.rglob("*") if p.name.endswith(".tmp")]
