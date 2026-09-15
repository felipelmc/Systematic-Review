"""Testes da busca OpenAlex sem rede: sessão HTTP falsa, cursor, re-tentativas, conversão e idempotência."""

import argparse
import json
import sys
import types

import pytest

from conftest import FIXTURES, ler_jsonl

OBRAS = json.loads((FIXTURES / "busca_openalex" / "obras.json").read_text(encoding="utf-8"))


class RespostaFalsa:
    def __init__(self, status=200, dados=None, headers=None):
        self.status_code = status
        self._dados = dados
        self.headers = headers or {}
        self.text = json.dumps(dados)

    def json(self):
        return self._dados


class SessaoFalsa:
    """Responde por uma função (url, params) -> RespostaFalsa | Exception e guarda as chamadas."""

    def __init__(self, rotas):
        self.rotas = rotas
        self.chamadas = []

    def get(self, url, params=None, timeout=None):
        self.chamadas.append((url, dict(params or {})))
        r = self.rotas(url, dict(params or {}))
        if isinstance(r, Exception):
            raise r
        return r


def sessao_sem_rede():
    def proibido(url, params):
        raise AssertionError(f"chamada de rede inesperada: {url} {params}")
    return SessaoFalsa(proibido)


def rotas_duas_paginas(url, params):
    if params.get("per-page") == 1:
        return RespostaFalsa(200, {"meta": {"count": 3}, "results": []})
    if params.get("cursor") == "*":
        return RespostaFalsa(200, {"meta": {"count": 3, "next_cursor": "c2"}, "results": OBRAS[:2]})
    if params.get("cursor") == "c2":
        # a API às vezes repete uma obra entre páginas: não pode duplicar
        return RespostaFalsa(200, {"meta": {"count": 3, "next_cursor": "c3"}, "results": [OBRAS[1], OBRAS[2]]})
    return RespostaFalsa(200, {"meta": {"count": 3, "next_cursor": None}, "results": []})


def rodar(argv, capsys):
    from rslib import busca_openalex
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    sub = parser.add_subparsers(dest="comando")
    busca_openalex.registrar(sub)
    args = parser.parse_args(argv)
    codigo = args.func(args)
    saida = capsys.readouterr().out.strip().splitlines()
    return codigo, json.loads(saida[-1])


@pytest.fixture
def sem_importador(monkeypatch):
    from rslib import busca_openalex
    monkeypatch.setattr(busca_openalex, "MODULO_IMPORTADOR", "rslib.importar._nao_existe_")


def test_reconstruir_resumo():
    from rslib.busca_openalex import reconstruir_resumo
    assert reconstruir_resumo({"b": [1, 3], "a": [0], "c": [2]}) == "a b c b"
    assert reconstruir_resumo(None) == ""


def test_obra_para_registro_achata_campos():
    from rslib import esquema
    from rslib.busca_openalex import obra_para_registro
    r = obra_para_registro(OBRAS[0], "B05", 1, "01-busca/brutos/B05_openalex.jsonl", estrutura="PICOC")
    assert list(r) == esquema.COLUNAS_REGISTROS
    assert r["id_registro"] == "B05-00001" and r["id_fonte"] == "W1001"
    assert r["doi"] == "10.1234/abc.2020.01"
    assert r["titulo"] == "Conditional cash transfers and school attendance"
    assert r["autores"] == "Silva, João da Filho | Souza, Maria"
    assert r["primeiro_autor_sobrenome"] == "Silva" and r["n_autores"] == "2"
    assert r["resumo"] == "Transfers raise attendance in schools"
    assert (r["tipo_publicacao"], r["idioma"], r["ano"]) == ("artigo", "en", "2020")
    assert r["paginas"] == "10-25" and r["numero"] == "2" and r["veiculo"] == "Journal of Policy Tests"
    assert r["pais_afiliacao"] == "BR; PT" and r["palavras_chave"] == "cash transfers; education"
    assert r["estrutura"] == "PICOC" and r["metodo_identificacao"] == "base"
    r2 = obra_para_registro(OBRAS[1], "B05", 2, "x")
    assert r2["tipo_publicacao"] == "tese" and r2["doi"] == "" and r2["resumo"] == "" and r2["url"] == ""
    r3 = obra_para_registro(OBRAS[2], "B05", 3, "x")
    assert r3["tipo_publicacao"] == "preprint" and r3["autores"] == "" and r3["url"] == "https://doi.org/10.5555/xyz"


def test_montar_consulta():
    from rslib.busca_openalex import montar_consulta
    assert montar_consulta('"cash transfer" AND school', "title_and_abstract", "publication_year:2000-2020") == \
        ('title_and_abstract.search:"cash transfer" AND school,publication_year:2000-2020', None)
    assert montar_consulta("a, b", "search") == (None, "a, b")
    with pytest.raises(ValueError):
        montar_consulta("a, b", "title_and_abstract")


def test_paginacao_cursor_retentativa_e_credenciais(monkeypatch):
    from rslib.busca_openalex import ClienteOpenAlex
    monkeypatch.setenv("RS_EMAIL", "revisor@example.org")
    monkeypatch.setenv("OPENALEX_API_KEY", "chave-de-teste")
    falhas = {"429": 1, "500": 1, "rede": 1}

    def rotas(url, params):
        if params.get("cursor") == "*" and falhas["429"]:
            falhas["429"] -= 1
            return RespostaFalsa(429, {}, {"Retry-After": "3"})
        if params.get("cursor") == "c2" and falhas["500"]:
            falhas["500"] -= 1
            return RespostaFalsa(503, {})
        if params.get("cursor") == "c3" and falhas["rede"]:
            falhas["rede"] -= 1
            return ConnectionError("queda")
        return rotas_duas_paginas(url, params)

    esperas = []
    sessao = SessaoFalsa(rotas)
    cliente = ClienteOpenAlex(sessao=sessao, espera=esperas.append, pausa=1.0)
    paginas = [obras for _, obras in cliente.paginar(filtro="title.search:x")]
    assert [len(p) for p in paginas] == [2, 2, 0]
    assert esperas[0] == 3.0 and len(esperas) == 3  # Retry-After respeitado; cada falha re-tentada
    assert all(p.get("mailto") == "revisor@example.org" and p.get("api_key") == "chave-de-teste"
               for _, p in sessao.chamadas)
    assert cliente.contar(filtro="title.search:x") == 3


def test_erro_4xx_nao_e_retentado():
    from rslib.busca_openalex import ClienteOpenAlex, ErroOpenAlex
    sessao = SessaoFalsa(lambda u, p: RespostaFalsa(400, {"error": "filtro inválido"}))
    with pytest.raises(ErroOpenAlex, match="400"):
        ClienteOpenAlex(sessao=sessao, espera=lambda s: None).contar(filtro="x")
    assert len(sessao.chamadas) == 1


def test_falha_persistente_esgota_tentativas():
    from rslib.busca_openalex import ClienteOpenAlex, ErroOpenAlex
    sessao = SessaoFalsa(lambda u, p: RespostaFalsa(502, {}))
    with pytest.raises(ErroOpenAlex, match="3 tentativas"):
        ClienteOpenAlex(sessao=sessao, tentativas=3, espera=lambda s: None).contar(filtro="x")
    assert len(sessao.chamadas) == 3


def test_buscar_grava_importa_e_e_idempotente(projeto_vazio, monkeypatch, capsys, sem_importador):
    from rslib import busca_openalex, esquema, estado
    from rslib.handoff import ler_csv
    monkeypatch.setenv("RS_EMAIL", "revisor@example.org")
    sessao = SessaoFalsa(rotas_duas_paginas)
    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: sessao)
    argv = ["--dir", str(projeto_vazio), "buscar", "openalex", "--busca-id", "B05", "--query", "cash transfer",
            "--filtro", "publication_year:2000-2025", "--string-id", "S-oa-v1"]
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 0 and resumo["n_bruto"] == 3 and resumo["n_api"] == 3 and resumo["importacao"]["via"] == "interno"
    brutos = ler_jsonl(projeto_vazio / "01-busca/brutos/B05_openalex.jsonl")
    assert [o["id"][-5:] for o in brutos] == ["W1001", "W1002", "W1003"]
    consulta = json.loads((projeto_vazio / "01-busca/brutos/B05_openalex.consulta.json").read_text())
    assert "chave" not in json.dumps(consulta).lower() or "api_key" not in consulta
    assert consulta["filter"].startswith("title_and_abstract.search:cash transfer")
    colunas, linhas = ler_csv(projeto_vazio / esquema.ARQ_REGISTROS)
    assert colunas == esquema.COLUNAS_REGISTROS and len(linhas) == 3
    est = estado.carregar_estado(projeto_vazio)
    busca = next(b for b in est["buscas"] if b["id"] == "B05")
    assert busca["n_bruto"] == 3 and busca["string_id"] == "S-oa-v1" and busca["sha256"]
    eventos = [e["evento"] for e in estado.ler_log(projeto_vazio)]
    assert eventos.count("busca_registrada") == 1 and eventos.count("importacao") == 1

    # reexecução: sem rede, sem duplicar linhas nem eventos de dados
    monkeypatch.setattr(busca_openalex, "criar_sessao", sessao_sem_rede)
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 0 and resumo["reexecucao"] is True
    assert len(ler_csv(projeto_vazio / esquema.ARQ_REGISTROS)[1]) == 3
    eventos = [e["evento"] for e in estado.ler_log(projeto_vazio)]
    assert eventos.count("busca_registrada") == 1 and eventos.count("importacao") == 1

    # mesma busca-id com outra consulta: recusa
    codigo, resumo = rodar(argv[:6] + ["--query", "outra string"], capsys)
    assert codigo == 1 and "imutáveis" in resumo["erro"]


def test_contar_nao_exige_projeto_nem_grava(tmp_path, monkeypatch, capsys):
    from rslib import busca_openalex
    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: SessaoFalsa(rotas_duas_paginas))
    codigo, resumo = rodar(["--dir", str(tmp_path), "buscar", "openalex", "--query", "x", "--contar"], capsys)
    assert codigo == 0 and resumo["n"] == 3
    assert not any(tmp_path.iterdir())


def test_busca_truncada_avisa(projeto_vazio, monkeypatch, capsys, sem_importador):
    from rslib import busca_openalex
    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: SessaoFalsa(rotas_duas_paginas))
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "buscar", "openalex", "--busca-id", "B06", "--query", "x",
                            "--max-paginas", "1"], capsys)
    assert codigo == 0 and resumo["n_bruto"] == 2
    assert any("truncada" in a for a in resumo["avisos"])


def test_delegacao_ao_importador_pelo_contrato_de_cli(projeto_vazio, monkeypatch, capsys):
    """Se `rslib.importar.cli` existir, a busca chama `importar` com as flags do contrato A2."""
    from rslib import busca_openalex
    chamadas = []
    falso = types.ModuleType("rslib_importador_falso")

    def registrar(sub):
        p = sub.add_parser("importar")
        for flag in ("--arquivo", "--busca-id", "--fonte", "--metodo", "--estrutura", "--mapa"):
            p.add_argument(flag)

        def func(args):
            chamadas.append(vars(args))
            print(json.dumps({"comando": "importar", "n_novos": 3}))
            return 0
        p.set_defaults(func=func)

    falso.registrar = registrar
    monkeypatch.setitem(sys.modules, "rslib_importador_falso", falso)
    monkeypatch.setattr(busca_openalex, "MODULO_IMPORTADOR", "rslib_importador_falso")
    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: SessaoFalsa(rotas_duas_paginas))
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "buscar", "openalex", "--busca-id", "B07", "--query", "x",
                            "--estrutura", "PICOC"], capsys)
    assert codigo == 0 and resumo["importacao"]["via"] == "importar"
    assert resumo["importacao"]["resumo_importador"]["n_novos"] == 3
    assert chamadas[0]["busca_id"] == "B07" and chamadas[0]["fonte"] == "openalex" and chamadas[0]["metodo"] == "base"
    assert chamadas[0]["arquivo"].endswith("B07_openalex.jsonl") and chamadas[0]["estrutura"] == "PICOC"


def test_integracao_com_importador_do_projeto(projeto_vazio, monkeypatch, capsys):
    """Com o importador real (A2) instalado, a busca delega a ele e a reexecução não duplica."""
    pytest.importorskip("rslib.importar.cli")
    from rslib import busca_openalex, esquema
    from rslib.handoff import ler_csv
    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: SessaoFalsa(rotas_duas_paginas))
    argv = ["--dir", str(projeto_vazio), "buscar", "openalex", "--busca-id", "B05", "--query", "cash"]
    for _ in range(2):
        codigo, resumo = rodar(argv, capsys)
        assert codigo == 0 and resumo["importacao"]["via"] == "importar"
    colunas, linhas = ler_csv(projeto_vazio / esquema.ARQ_REGISTROS)
    assert colunas == esquema.COLUNAS_REGISTROS and [l["id_registro"] for l in linhas] == ["B05-00001", "B05-00002", "B05-00003"]


def test_sessao_de_teste_por_variavel_de_ambiente(tmp_path, monkeypatch, capsys):
    """Ponto de injeção do e2e (processo novo, sem monkeypatch): RS_TESTE_OPENALEX_RESPOSTAS."""
    from rslib import busca_openalex as bo
    obra = {"id": "https://openalex.org/W11", "doi": "https://doi.org/10.5555/ABC", "title": "Um", "publication_year": 2020,
            "referenced_works": ["https://openalex.org/W12"]}
    citante = {"id": "https://openalex.org/W13", "title": "Cita", "publication_year": 2022}
    arq = tmp_path / "respostas.json"
    arq.write_text(json.dumps({"obras": {"W11": obra, "W13": citante}, "citacoes": {"W11": ["W13"]}}), encoding="utf-8")
    monkeypatch.setenv(bo.VAR_TESTE_RESPOSTAS, str(arq))
    sessao = bo.criar_sessao()
    assert getattr(sessao, "falsa", False) and "só para testes" in capsys.readouterr().err
    cliente = bo.ClienteOpenAlex(sessao=sessao, email="", api_key="")
    assert cliente.obra("W11")["referenced_works"] == ["https://openalex.org/W12"]
    assert bo.id_curto(cliente.obra("doi:10.5555/abc")["id"]) == "W11"
    assert cliente.obra("W99") is None
    assert [bo.id_curto(o["id"]) for _, obras in cliente.paginar(filtro="cites:W11") for o in obras] == ["W13"]
    assert [bo.id_curto(o["id"]) for o in cliente.obras_por_ids(["W13", "W11", "W404"])] == ["W13", "W11"]
    titulo = [o for _, obras in cliente.paginar(filtro="title.search:um,publication_year:2020") for o in obras]
    assert [bo.id_curto(o["id"]) for o in titulo] == ["W11"]
    monkeypatch.delenv(bo.VAR_TESTE_RESPOSTAS)
    assert not getattr(bo.criar_sessao(), "falsa", False)


# ---------------------------------------------------------------------------
# v1.1: busca-id com a regra do importador, campos exatos, --listar, buscas inativas, retratação
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("busca_id", ["B05a", "b05", "B-05", None])
def test_busca_id_invalido_recusado_antes_da_api(projeto_vazio, monkeypatch, capsys, busca_id):
    from rslib import busca_openalex
    monkeypatch.setattr(busca_openalex, "criar_sessao", sessao_sem_rede)
    argv = ["--dir", str(projeto_vazio), "buscar", "openalex", "--query", "cash"]
    if busca_id is not None:
        argv += ["--busca-id", busca_id]
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 1 and "--busca-id inválido" in resumo["erro"]
    assert not list((projeto_vazio / "01-busca/brutos").iterdir())


def test_campos_exatos_montam_filtro_e_sao_aceitos_na_cli(projeto_vazio, monkeypatch, capsys, sem_importador):
    from rslib import busca_openalex
    from rslib.busca_openalex import CAMPOS_BUSCA_EXATOS, montar_consulta
    assert set(CAMPOS_BUSCA_EXATOS) == {"title_and_abstract.search.exact", "title.search.exact", "abstract.search.exact"}
    assert montar_consulta('"cash transfer*" AND school*', "title_and_abstract.search.exact", "type:article") == \
        ('title_and_abstract.search.exact:"cash transfer*" AND school*,type:article', None)
    assert montar_consulta("x", "title.search.exact") == ("title.search.exact:x", None)
    assert montar_consulta("x", "abstract") == ("abstract.search:x", None)
    with pytest.raises(ValueError):
        montar_consulta("a, b*", "abstract.search.exact")
    with pytest.raises(ValueError):
        montar_consulta("x", "title.search.no_stem")
    sessao = SessaoFalsa(rotas_duas_paginas)
    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: sessao)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "buscar", "openalex", "--busca-id", "B08", "--query",
                            "transfer*", "--campo", "title.search.exact"], capsys)
    assert codigo == 0 and resumo["n_bruto"] == 3
    assert all(p["filter"] == "title.search.exact:transfer*" for _, p in sessao.chamadas)


def test_http_400_com_curinga_sugere_campo_exato(tmp_path, monkeypatch, capsys):
    from rslib import busca_openalex
    monkeypatch.setattr(busca_openalex, "criar_sessao",
                        lambda: SessaoFalsa(lambda u, p: RespostaFalsa(400, {"error": "invalid query"})))
    codigo, resumo = rodar(["--dir", str(tmp_path), "buscar", "openalex", "--query", "school*", "--contar"], capsys)
    assert codigo == 1 and "--campo title_and_abstract.search.exact" in resumo["erro"]
    codigo, resumo = rodar(["--dir", str(tmp_path), "buscar", "openalex", "--query", "school", "--contar"], capsys)
    assert codigo == 1 and "dica" not in resumo["erro"]


def test_listar_sem_projeto_grava_exploracao(tmp_path, monkeypatch, capsys):
    from rslib import busca_openalex
    from rslib.handoff import ler_csv
    sessao = SessaoFalsa(rotas_duas_paginas)
    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: sessao)
    codigo, resumo = rodar(["--dir", str(tmp_path), "buscar", "openalex", "--busca-id", "B09", "--query", "cash",
                            "--listar", "2"], capsys)
    assert codigo == 0 and resumo["listar"] and resumo["n_listadas"] == 2 and resumo["com_projeto"] is False
    colunas, linhas = ler_csv(tmp_path / "00-protocolo" / "exploracao_B09.csv")
    assert colunas == ["posicao", "id_openalex", "titulo", "ano", "doi", "citado_por"]
    assert [(l["posicao"], l["id_openalex"]) for l in linhas] == [("1", "W1001"), ("2", "W1002")]
    assert linhas[0]["titulo"] == "Conditional cash transfers and school attendance"
    assert (linhas[0]["ano"], linhas[0]["doi"], linhas[0]["citado_por"]) == ("2020", "10.1234/abc.2020.01", "12")
    assert len(sessao.chamadas) == 1 and sessao.chamadas[0][1]["per-page"] == 2  # não pagina além do necessário
    assert sorted(p.name for p in tmp_path.iterdir()) == ["00-protocolo"]  # sem estado, sem registros


def test_listar_com_projeto_nao_importa_nem_registra_busca(projeto_vazio, monkeypatch, capsys):
    from rslib import busca_openalex, esquema, estado
    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: SessaoFalsa(rotas_duas_paginas))
    argv = ["--dir", str(projeto_vazio), "buscar", "openalex", "--busca-id", "B09", "--query", "cash", "--listar", "10"]
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 0 and resumo["n_listadas"] == 3 and resumo["arquivo"] == "00-protocolo/exploracao_B09.csv"
    assert resumo["importado"] is False and resumo["busca_registrada"] is False
    est = estado.carregar_estado(projeto_vazio)
    assert est["buscas"] == [] and not (projeto_vazio / esquema.ARQ_REGISTROS).exists()
    eventos = estado.ler_log(projeto_vazio)
    assert [e["evento"] for e in eventos].count("busca_registrada") == 0
    assert not any(e["evento"] == "importacao" for e in eventos)
    ev = [e for e in eventos if e["evento"] == "artefato_versionado"][-1]
    assert ev["dados"]["tipo"] == "exploracao_openalex" and ev["dados"]["n_listadas"] == 3
    # arquivo congelado no G2 não é sobrescrito
    est["artefatos"]["00-protocolo/exploracao_B09.csv"] = {"caminho": "00-protocolo/exploracao_B09.csv",
                                                           "sha256": "x", "congelado_em": "2026-01-01T00:00:00Z"}
    estado.salvar_estado(projeto_vazio, est)
    monkeypatch.setattr(busca_openalex, "criar_sessao", sessao_sem_rede)
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 1 and "congelado" in resumo["erro"]


@pytest.mark.parametrize("extra, trecho", [
    (["--listar", "3", "--contar", "--busca-id", "B09"], "alternativos"),
    (["--listar", "0", "--busca-id", "B09"], "N >= 1"),
    (["--listar", "3"], "--busca-id inválido"),
    (["--listar", "3", "--busca-id", "b9"], "--busca-id inválido"),
])
def test_listar_erros_sem_chamar_api(tmp_path, monkeypatch, capsys, extra, trecho):
    from rslib import busca_openalex
    monkeypatch.setattr(busca_openalex, "criar_sessao", sessao_sem_rede)
    codigo, resumo = rodar(["--dir", str(tmp_path), "buscar", "openalex", "--query", "x", *extra], capsys)
    assert codigo == 1 and trecho in resumo["erro"]
    assert not any(tmp_path.iterdir())


def test_busca_substituida_e_recusada(projeto_vazio, monkeypatch, capsys):
    from rslib import busca_openalex, estado
    est = estado.carregar_estado(projeto_vazio)
    est["buscas"].append({"id": "B05", "fonte": "openalex", "ativa": False, "substituida_por": "B06"})
    estado.salvar_estado(projeto_vazio, est)
    monkeypatch.setattr(busca_openalex, "criar_sessao", sessao_sem_rede)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "buscar", "openalex", "--busca-id", "B05", "--query", "x"],
                           capsys)
    assert codigo == 1 and "substituída por B06" in resumo["erro"]


def test_busca_nova_fica_ativa_e_retratacao_vai_para_flags(projeto_vazio, monkeypatch, capsys, sem_importador):
    from rslib import busca_openalex, estado
    from rslib.handoff import ler_linhas
    retratada = dict(OBRAS[2], is_retracted=True)

    def rotas(url, params):
        return RespostaFalsa(200, {"meta": {"count": 2, "next_cursor": None}, "results": [OBRAS[0], retratada]})
    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: SessaoFalsa(rotas))
    codigo, _ = rodar(["--dir", str(projeto_vazio), "buscar", "openalex", "--busca-id", "B05", "--query", "x"], capsys)
    assert codigo == 0
    busca = next(b for b in estado.carregar_estado(projeto_vazio)["buscas"] if b["id"] == "B05")
    assert busca["ativa"] is True
    flags = ler_linhas(projeto_vazio / "dados/registros_flags.csv")
    assert [(f["id_registro"], f["flag"]) for f in flags] == [("B05-00002", "retratado")]


def test_sessao_de_teste_aceita_filtro_exato(tmp_path, monkeypatch, capsys):
    from rslib import busca_openalex as bo
    arq = tmp_path / "respostas.json"
    arq.write_text(json.dumps({"obras": {"W11": {"id": "https://openalex.org/W11", "title": "Um",
                                                 "publication_year": 2020}}}), encoding="utf-8")
    monkeypatch.setenv(bo.VAR_TESTE_RESPOSTAS, str(arq))
    cliente = bo.ClienteOpenAlex(sessao=bo.criar_sessao(), email="", api_key="")
    obras = [o for _, pg in cliente.paginar(filtro="title_and_abstract.search.exact:um*") for o in pg]
    assert [bo.id_curto(o["id"]) for o in obras] == ["W11"]


# ---------------------------------------------------------------------------
# v1.2: busca_registrada no resumo, --substituir e --n-base conferido com n_api
# ---------------------------------------------------------------------------
def rodar_importar(argv, capsys):
    from rslib.importar import cli
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    sub = parser.add_subparsers(dest="comando")
    cli.registrar(sub)
    args = parser.parse_args(argv)
    codigo = args.func(args)
    captura = capsys.readouterr()
    return codigo, json.loads(captura.out.strip().splitlines()[-1]), captura.err


def test_resumo_reflete_busca_registrada(projeto_vazio, monkeypatch, capsys):
    """Regressão: com o importador real, o resumo dizia busca_registrada=false embora o evento tivesse sido gravado."""
    pytest.importorskip("rslib.importar.cli")
    from rslib import busca_openalex, estado
    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: SessaoFalsa(rotas_duas_paginas))
    argv = ["--dir", str(projeto_vazio), "buscar", "openalex", "--busca-id", "B01", "--query", "cash"]
    codigo, resumo = rodar(argv, capsys)
    eventos = [e for e in estado.ler_log(projeto_vazio) if e["evento"] == "busca_registrada"]
    assert codigo == 0 and len(eventos) == 1
    assert resumo["busca_registrada"] is True and resumo["busca_registrada_agora"] is True
    assert resumo["evento_busca_registrada_seq"] == eventos[0]["seq"]
    assert resumo["importacao"]["resumo_importador"]["busca_registrada"] is True
    monkeypatch.setattr(busca_openalex, "criar_sessao", sessao_sem_rede)
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 0 and resumo["reexecucao"] is True
    assert resumo["busca_registrada"] is True and resumo["busca_registrada_agora"] is False
    assert resumo["evento_busca_registrada_seq"] == eventos[0]["seq"]
    assert len([e for e in estado.ler_log(projeto_vazio) if e["evento"] == "busca_registrada"]) == 1


def test_buscar_substituir_com_mesma_semantica_do_importar(projeto_vazio, monkeypatch, capsys):
    from rslib import busca_openalex, esquema, estado
    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: SessaoFalsa(rotas_duas_paginas))
    base = ["--dir", str(projeto_vazio), "buscar", "openalex"]
    assert rodar(base + ["--busca-id", "B01", "--query", "cash"], capsys)[0] == 0

    # validação antes de qualquer chamada à API e antes de gravar
    monkeypatch.setattr(busca_openalex, "criar_sessao", sessao_sem_rede)
    for extra, trecho in ((["--substituir", "B01"], "--motivo"),
                          (["--motivo", "string v2"], "--motivo só vale"),
                          (["--substituir", "B09", "--motivo", "x"], "inexistente"),
                          (["--substituir", "B02", "--motivo", "x"], "própria busca"),
                          (["--substituir", "b1", "--motivo", "x"], "--substituir inválido")):
        codigo, resumo = rodar(base + ["--busca-id", "B02", "--query", "cash v2", *extra], capsys)
        assert codigo == 1 and trecho in resumo["erro"], (extra, resumo)
    codigo, resumo = rodar(base + ["--query", "x", "--contar", "--substituir", "B01", "--motivo", "x"], capsys)
    assert codigo == 1 and "busca completa" in resumo["erro"]
    assert not (projeto_vazio / "01-busca/brutos/B02_openalex.jsonl").exists()

    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: SessaoFalsa(rotas_duas_paginas))
    argv = base + ["--busca-id", "B02", "--query", "cash v2", "--substituir", "B01", "--motivo", "âncora perdida na v1"]
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 0 and resumo["substituicao"]["busca_id_antiga"] == "B01"
    est = estado.carregar_estado(projeto_vazio)
    antiga = next(b for b in est["buscas"] if b["id"] == "B01")
    nova = next(b for b in est["buscas"] if b["id"] == "B02")
    assert antiga[esquema.CAMPO_BUSCA_ATIVA] is False and antiga["substituida_por"] == "B02"
    assert antiga["motivo_substituicao"] == "âncora perdida na v1"
    assert nova[esquema.CAMPO_BUSCA_ATIVA] is True and nova["substitui"] == ["B01"]
    eventos = estado.ler_log(projeto_vazio)
    nomes = [e["evento"] for e in eventos]
    assert nomes.count("busca_substituida") == 1
    assert nomes.index("busca_substituida") > max(i for i, n in enumerate(nomes) if n == "busca_registrada")
    ev = next(e for e in eventos if e["evento"] == "busca_substituida")
    assert ev["motivo"] == "âncora perdida na v1" and ev["dados"]["busca_id_nova"] == "B02"
    # linhas da busca antiga continuam em registros.csv
    from rslib.handoff import ler_csv
    assert {l["busca_id"] for l in ler_csv(projeto_vazio / esquema.ARQ_REGISTROS)[1]} == {"B01", "B02"}
    # reexecução idempotente: sem rede e sem novo evento de substituição
    monkeypatch.setattr(busca_openalex, "criar_sessao", sessao_sem_rede)
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 0 and resumo["substituicao"]["ja_aplicada"] is True
    assert [e["evento"] for e in estado.ler_log(projeto_vazio)].count("busca_substituida") == 1
    # a busca antiga não aceita reexecução
    codigo, resumo = rodar(base + ["--busca-id", "B01", "--query", "cash"], capsys)
    assert codigo == 1 and "substituída por B02" in resumo["erro"]


def test_importar_n_base_em_busca_do_openalex_confere_com_n_api(projeto_vazio, monkeypatch, capsys):
    """Regressão: --n-base 185 numa busca truncada (50 baixadas) era recusado como conflito com n_bruto."""
    from rslib import busca_openalex, estado
    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: SessaoFalsa(rotas_duas_paginas))
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "buscar", "openalex", "--busca-id", "B01", "--query", "x",
                            "--max-paginas", "1", "--string-id", "S-oa-v1"], capsys)
    assert codigo == 0 and (resumo["n_api"], resumo["n_bruto"]) == (3, 2)
    jsonl = str(projeto_vazio / "01-busca/brutos/B01_openalex.jsonl")
    base = ["--dir", str(projeto_vazio), "importar", "--arquivo", jsonl, "--busca-id", "B01"]
    n_eventos = len(estado.ler_log(projeto_vazio))

    codigo, resumo, _ = rodar_importar(base + ["--n-base", "3", "--string-id", "S-oa-v1", "--plataforma",
                                               "OpenAlex (API)"], capsys)
    assert codigo == 0, resumo
    assert resumo["n_base_openalex"] == {"n_base": 3, "n_api": 3, "confere": True}
    assert resumo["busca_registrada"] is True and resumo["metadados_declarados"] == {"plataforma": "OpenAlex (API)"}
    busca = next(b for b in estado.carregar_estado(projeto_vazio)["buscas"] if b["id"] == "B01")
    assert (busca["n_api"], busca["n_bruto"], busca["plataforma"]) == (3, 2, "OpenAlex (API)")
    ev = [e for e in estado.ler_log(projeto_vazio)[n_eventos:] if e["evento"] == "busca_registrada"]
    assert len(ev) == 1 and ev[0]["dados"]["n_api"] == 3

    codigo, resumo, erro = rodar_importar(base + ["--n-base", "2"], capsys)
    assert codigo == 1
    assert "n_api=3" in resumo["erro"] and "n_bruto=2" in resumo["erro"] and "truncada" in resumo["erro"]
    assert "buscar openalex --busca-id <novo id>" in resumo["erro"] and "--substituir B01" in resumo["erro"]
    assert "outro --busca-id e --substituir" not in resumo["erro"]
    busca = next(b for b in estado.carregar_estado(projeto_vazio)["buscas"] if b["id"] == "B01")
    assert (busca["n_api"], busca["n_bruto"]) == (3, 2)


def test_importar_n_base_em_busca_manual_continua_comparando_n_bruto(projeto_vazio, capsys):
    from conftest import FIXTURES as FX
    base = ["--dir", str(projeto_vazio), "importar", "--arquivo", str(FX / "importar" / "scopus.csv"), "--busca-id", "B02"]
    assert rodar_importar(base + ["--n-base", "7"], capsys)[0] == 0
    codigo, resumo, _ = rodar_importar(base + ["--n-base", "8"], capsys)
    assert codigo == 1 and "n_bruto já registrado como 7" in resumo["erro"]
    assert "--substituir B02" in resumo["erro"] and "buscar openalex" not in resumo["erro"]


def test_buscar_substituir_com_conversao_interna(projeto_vazio, monkeypatch, capsys, sem_importador):
    from rslib import busca_openalex, estado
    monkeypatch.setattr(busca_openalex, "criar_sessao", lambda: SessaoFalsa(rotas_duas_paginas))
    base = ["--dir", str(projeto_vazio), "buscar", "openalex"]
    assert rodar(base + ["--busca-id", "B01", "--query", "cash"], capsys)[0] == 0
    codigo, resumo = rodar(base + ["--busca-id", "B02", "--query", "cash v2", "--substituir", "B01", "--motivo", "v2"],
                           capsys)
    assert codigo == 0 and resumo["importacao"]["via"] == "interno" and resumo["busca_registrada"] is True
    assert resumo["substituicao"]["busca_id_nova"] == "B02"
    est = estado.carregar_estado(projeto_vazio)
    assert next(b for b in est["buscas"] if b["id"] == "B01")["ativa"] is False
    assert [e["evento"] for e in estado.ler_log(projeto_vazio)].count("busca_substituida") == 1
