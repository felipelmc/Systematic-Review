"""Testes da bola de neve sem rede: resolução de sementes, referências, citações, corpus conhecido e reexecução."""

import argparse
import json

import pytest

from conftest import ler_jsonl
from test_busca_openalex import RespostaFalsa, SessaoFalsa, sessao_sem_rede


def obra(wid, titulo, ano=2020, doi=None, autor="Ana Costa"):
    return {"id": f"https://openalex.org/{wid}", "doi": doi, "title": titulo, "publication_year": ano,
            "type": "article", "language": "en", "authorships": [{"author": {"display_name": autor}}],
            "abstract_inverted_index": {"Resumo": [0], "curto": [1]}, "cited_by_count": 1}


OBRAS = {
    "W300": obra("W300", "Already imported paper", doi="10.9/known"),
    "W400": obra("W400", "Reference cited by two seeds"),
    "W500": obra("W500", "Reference of the second seed"),
    "W600": obra("W600", "Later paper citing the seeds", 2024),
}


def rotas(url, params):
    filtro = params.get("filter") or ""
    if url.endswith("/works/doi:10.1234/abc"):
        return RespostaFalsa(200, {"id": "https://openalex.org/W200"})
    if url.endswith("/works/W100"):
        return RespostaFalsa(200, {"id": "https://openalex.org/W100",
                                   "referenced_works": ["https://openalex.org/W300", "https://openalex.org/W400",
                                                        "https://openalex.org/W200"]})
    if url.endswith("/works/W200"):
        return RespostaFalsa(200, {"id": "https://openalex.org/W200",
                                   "referenced_works": ["https://openalex.org/W400", "https://openalex.org/W500"]})
    if url.endswith("/works/W250"):
        return RespostaFalsa(200, {"id": "https://openalex.org/W250", "referenced_works": []})
    if filtro.startswith("title.search:"):
        assert "publication_year:2019" in filtro
        return RespostaFalsa(200, {"meta": {"next_cursor": None}, "results": [
            {"id": "https://openalex.org/W250", "title": "Evaluating School Meals: A Randomized Trial",
             "publication_year": 2019},
            {"id": "https://openalex.org/W251", "title": "Evaluating school meals in rural areas",
             "publication_year": 2019}]})
    if filtro == "cites:W100":
        return RespostaFalsa(200, {"meta": {"next_cursor": None}, "results": [OBRAS["W600"]]})
    if filtro == "cites:W250":
        return RespostaFalsa(200, {"meta": {"next_cursor": None}, "results": [OBRAS["W600"]]})
    if filtro.startswith("cites:"):
        return RespostaFalsa(200, {"meta": {"next_cursor": None}, "results": []})
    if filtro.startswith("ids.openalex:"):
        ids = filtro.split(":", 1)[1].split("|")
        return RespostaFalsa(200, {"meta": {"next_cursor": None}, "results": [OBRAS[i] for i in ids if i in OBRAS]})
    return RespostaFalsa(404, {})


def preparar_projeto(raiz):
    from rslib import esquema
    from rslib.handoff import escrever_csv
    base = {c: "" for c in esquema.COLUNAS_UNICOS}
    unicos = [
        dict(base, id_rs="RS0001", id_estudo="RS0001", chave="Silva2020", id_fonte="W100", titulo="Seed one", ano="2020"),
        dict(base, id_rs="RS0002", id_estudo="RS0002", chave="Souza2021", id_fonte="WOS:000123", doi="10.1234/abc",
             titulo="Seed two", ano="2021"),
        dict(base, id_rs="RS0003", id_estudo="RS0003", chave="Lima2019", titulo="Evaluating school meals: a randomized trial",
             ano="2019"),
    ]
    escrever_csv(raiz / esquema.ARQ_UNICOS, esquema.COLUNAS_UNICOS, unicos)
    registro = {c: "" for c in esquema.COLUNAS_REGISTROS}
    escrever_csv(raiz / esquema.ARQ_REGISTROS, esquema.COLUNAS_REGISTROS, [
        dict(registro, id_registro="B01-00001", busca_id="B01", fonte="openalex", metodo_identificacao="base",
             id_fonte="W300", doi="10.9/known", titulo="Already imported paper")])
    escrever_csv(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL, esquema.COLUNAS_ELEGIBILIDADE_FINAL, [
        {"id_rs": "RS0001", "chave": "Silva2020", "decisao": "incluir"},
        {"id_rs": "RS0002", "chave": "Souza2021", "decisao": "incluir"},
        {"id_rs": "RS0003", "chave": "Lima2019", "decisao": "incluir"},
    ])


def rodar(argv, capsys):
    from rslib import bola_de_neve
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    sub = parser.add_subparsers(dest="comando")
    bola_de_neve.registrar(sub)
    args = parser.parse_args(argv)
    codigo = args.func(args)
    return codigo, json.loads(capsys.readouterr().out.strip().splitlines()[-1])


@pytest.fixture
def api_falsa(monkeypatch):
    from rslib import busca_openalex
    sessao = SessaoFalsa(rotas)
    monkeypatch.setattr(busca_openalex.time, "sleep", lambda s: None)
    monkeypatch.setattr(busca_openalex, "MODULO_IMPORTADOR", "rslib.importar._nao_existe_")
    monkeypatch.setattr("rslib.bola_de_neve.criar_sessao", lambda: sessao)
    return sessao


def test_bola_de_neve_ambas_direcoes(projeto_vazio, api_falsa, capsys, monkeypatch):
    from rslib import esquema, estado
    from rslib.handoff import ler_csv, ler_linhas
    preparar_projeto(projeto_vazio)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bola-de-neve", "--direcao", "ambas", "--rodada", "SN1"], capsys)
    assert codigo == 0, resumo
    assert resumo["n_sementes"] == 3 and resumo["n_nao_resolvidas"] == 0
    assert resumo["n_encontrados"] == 4 and resumo["n_ja_no_corpus"] == 1 and resumo["n_gravados"] == 3

    sementes = {s["id_rs"]: s for s in ler_linhas(projeto_vazio / "01-busca/bola_de_neve/SN1_sementes.csv")}
    assert (sementes["RS0001"]["metodo_resolucao"], sementes["RS0001"]["id_openalex"]) == ("id_fonte", "W100")
    assert (sementes["RS0002"]["metodo_resolucao"], sementes["RS0002"]["id_openalex"]) == ("doi", "W200")
    assert (sementes["RS0003"]["metodo_resolucao"], sementes["RS0003"]["id_openalex"]) == ("titulo_ano", "W250")

    prov = {p["id_openalex"]: p for p in ler_linhas(projeto_vazio / "01-busca/bola_de_neve/SN1_proveniencia.csv")}
    assert "W200" not in prov  # semente citada por outra semente não é registro novo
    assert prov["W300"]["ja_no_corpus"] == "1" and prov["W300"]["gravado"] == "0"
    assert prov["W400"]["sementes"] == "RS0001|RS0002" and prov["W400"]["direcoes"] == "tras"
    assert prov["W600"]["sementes"] == "RS0001|RS0003" and prov["W600"]["direcoes"] == "frente"

    brutos = ler_jsonl(projeto_vazio / "01-busca/brutos/SN1_openalex_citacao.jsonl")
    assert [o["id"].rsplit("/", 1)[-1] for o in brutos] == ["W400", "W500", "W600"]
    _, registros = ler_csv(projeto_vazio / esquema.ARQ_REGISTROS)
    novos = [r for r in registros if r["busca_id"] == "SN1"]
    assert len(novos) == 3 and {r["metodo_identificacao"] for r in novos} == {"citacao"}
    assert [r["id_registro"] for r in novos] == ["SN1-00001", "SN1-00002", "SN1-00003"]
    assert "rs.py dedup" in resumo["proximos_passos"][0]

    est = estado.carregar_estado(projeto_vazio)
    busca = next(b for b in est["buscas"] if b["id"] == "SN1")
    assert busca["metodo_identificacao"] == "citacao" and busca["n_bruto"] == 3

    # reexecução não chama a API nem duplica
    monkeypatch.setattr("rslib.bola_de_neve.criar_sessao", sessao_sem_rede)
    n_eventos = len(estado.ler_log(projeto_vazio))
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bola-de-neve", "--direcao", "ambas", "--rodada", "SN1"], capsys)
    assert codigo == 0 and resumo["reexecucao"] and resumo["n_gravados"] == 3
    assert len([r for r in ler_csv(projeto_vazio / esquema.ARQ_REGISTROS)[1] if r["busca_id"] == "SN1"]) == 3
    assert len(estado.ler_log(projeto_vazio)) == n_eventos


def test_incluir_conhecidos_e_so_tras(projeto_vazio, api_falsa, capsys):
    preparar_projeto(projeto_vazio)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bola-de-neve", "--direcao", "tras", "--rodada", "SN2",
                            "--incluir-conhecidos"], capsys)
    assert codigo == 0 and resumo["n_gravados"] == 3 and resumo["n_ja_no_corpus"] == 1  # W300, W400, W500
    assert not any(filtro.startswith("cites:") for _, p in api_falsa.chamadas for filtro in [p.get("filter") or ""])


def test_sementes_por_arquivo_e_erros(projeto_vazio, api_falsa, capsys, tmp_path):
    preparar_projeto(projeto_vazio)
    ids = tmp_path / "ids.csv"
    ids.write_text("chave\nSouza2021\n", encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bola-de-neve", "--direcao", "tras", "--rodada", "SN3",
                            "--ids", str(ids)], capsys)
    assert codigo == 0 and resumo["n_sementes"] == 1 and resumo["n_gravados"] == 2
    ids.write_text("id_rs\nRS9999\n", encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bola-de-neve", "--direcao", "tras", "--rodada", "SN4",
                            "--ids", str(ids)], capsys)
    assert codigo == 1 and "RS9999" in resumo["erro"]


def test_resolucao_por_titulo_exige_ano_e_desempate():
    from rslib.bola_de_neve import resolver_semente
    from rslib.busca_openalex import ClienteOpenAlex
    cliente = ClienteOpenAlex(sessao=sessao_sem_rede(), espera=lambda s: None)
    assert resolver_semente(cliente, {"titulo": "Algum título", "ano": ""}) == ("", "nao_resolvido", "")

    def empate(url, params):
        return RespostaFalsa(200, {"meta": {}, "results": [
            {"id": "https://openalex.org/W1", "title": "Same title here", "publication_year": 2019},
            {"id": "https://openalex.org/W2", "title": "Same title here.", "publication_year": 2019}]})
    cliente = ClienteOpenAlex(sessao=SessaoFalsa(empate), espera=lambda s: None)
    wid, metodo, _ = resolver_semente(cliente, {"titulo": "Same title here", "ano": "2019"})
    assert wid == "" and metodo == "titulo_ambiguo"

    def outro_ano(url, params):
        return RespostaFalsa(200, {"meta": {}, "results": [
            {"id": "https://openalex.org/W1", "title": "Same title here", "publication_year": 2020}]})
    cliente = ClienteOpenAlex(sessao=SessaoFalsa(outro_ano), espera=lambda s: None)
    assert resolver_semente(cliente, {"titulo": "Same title here", "ano": "2019"})[1] == "nao_resolvido"


def test_sem_elegibilidade_pede_ids(projeto_vazio, api_falsa, capsys):
    from rslib import esquema
    preparar_projeto(projeto_vazio)
    (projeto_vazio / esquema.ARQ_ELEGIBILIDADE_TC_FINAL).unlink()
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bola-de-neve", "--direcao", "frente", "--rodada", "SN1"], capsys)
    assert codigo == 1 and "--ids" in resumo["erro"]


def test_integracao_com_importador_do_projeto(projeto_vazio, capsys, monkeypatch):
    """Com o importador real (A2) instalado, a rodada entra por `rs.py importar --metodo citacao`."""
    pytest.importorskip("rslib.importar.cli")
    from rslib import busca_openalex, esquema
    from rslib.handoff import ler_csv
    monkeypatch.setattr(busca_openalex.time, "sleep", lambda s: None)
    monkeypatch.setattr("rslib.bola_de_neve.criar_sessao", lambda: SessaoFalsa(rotas))
    preparar_projeto(projeto_vazio)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bola-de-neve", "--direcao", "ambas", "--rodada", "SN1"], capsys)
    assert codigo == 0 and resumo["importacao"]["via"] == "importar"
    novos = [r for r in ler_csv(projeto_vazio / esquema.ARQ_REGISTROS)[1] if r["busca_id"] == "SN1"]
    assert len(novos) == 3 and {r["metodo_identificacao"] for r in novos} == {"citacao"}


# ---------------------------------------------------------------------------
# v1.1: rodada com a regra do importador e buscas substituídas
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("rodada", ["sn1", "SN-1", "SN1a"])
def test_rodada_invalida_recusada_antes_da_api(projeto_vazio, capsys, monkeypatch, rodada):
    monkeypatch.setattr("rslib.bola_de_neve.criar_sessao", sessao_sem_rede)
    preparar_projeto(projeto_vazio)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bola-de-neve", "--direcao", "tras", "--rodada", rodada,
                            "--sem-importador"], capsys)
    assert codigo == 1 and "--rodada inválido" in resumo["erro"]
    assert not list((projeto_vazio / "01-busca/bola_de_neve").iterdir())
    assert not list((projeto_vazio / "01-busca/brutos").iterdir())


def test_rodada_substituida_recusada_mesmo_na_reexecucao(projeto_vazio, api_falsa, capsys, monkeypatch):
    from rslib import estado
    preparar_projeto(projeto_vazio)
    assert rodar(["--dir", str(projeto_vazio), "bola-de-neve", "--direcao", "tras", "--rodada", "SN1"], capsys)[0] == 0
    est = estado.carregar_estado(projeto_vazio)
    next(b for b in est["buscas"] if b["id"] == "SN1").update(ativa=False, substituida_por="SN2")
    estado.salvar_estado(projeto_vazio, est)
    monkeypatch.setattr("rslib.bola_de_neve.criar_sessao", sessao_sem_rede)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bola-de-neve", "--direcao", "tras", "--rodada", "SN1"], capsys)
    assert codigo == 1 and "substituída por SN2" in resumo["erro"]


def test_corpus_conhecido_ignora_buscas_substituidas(projeto_vazio, api_falsa, capsys):
    from rslib import estado
    from rslib.handoff import ler_linhas
    preparar_projeto(projeto_vazio)
    est = estado.carregar_estado(projeto_vazio)
    est["buscas"].append({"id": "B01", "fonte": "openalex", "ativa": False, "substituida_por": "B02"})
    estado.salvar_estado(projeto_vazio, est)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bola-de-neve", "--direcao", "tras", "--rodada", "SN1"], capsys)
    assert codigo == 0 and resumo["n_ja_no_corpus"] == 0 and resumo["n_gravados"] == 3  # W300, W400, W500
    prov = {p["id_openalex"]: p for p in ler_linhas(projeto_vazio / "01-busca/bola_de_neve/SN1_proveniencia.csv")}
    assert prov["W300"]["ja_no_corpus"] == "0" and prov["W300"]["gravado"] == "1"


def test_sementes_de_cluster_inativo(projeto_vazio, api_falsa, capsys, tmp_path):
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_linhas
    preparar_projeto(projeto_vazio)
    unicos = ler_linhas(projeto_vazio / esquema.ARQ_UNICOS)
    unicos[1]["flags"] = "busca_inativa"  # RS0002
    escrever_csv(projeto_vazio / esquema.ARQ_UNICOS, esquema.COLUNAS_UNICOS, unicos)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bola-de-neve", "--direcao", "tras", "--rodada", "SN1"], capsys)
    assert codigo == 0 and resumo["n_sementes"] == 2
    assert any("RS0002" in a and "--ids" in a for a in resumo["avisos"])
    ids = tmp_path / "ids.csv"
    ids.write_text("id_rs\nRS0002\n", encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "bola-de-neve", "--direcao", "tras", "--rodada", "SN2",
                            "--ids", str(ids)], capsys)
    assert codigo == 0 and resumo["n_sementes"] == 1 and any("RS0002" in a for a in resumo["avisos"])
