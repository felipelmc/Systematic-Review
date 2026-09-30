"""Testes de `rs.py dedup`: pares plantados, bloqueios, ids estáveis, revisão humana e pendências."""

import argparse
import csv
import json
import shutil

import pytest

from conftest import FIXTURES, SKILL, ler_jsonl

PLANTADOS = FIXTURES / "dedup" / "registros_plantados.csv"


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------
def rodar(raiz, *argv):
    """Chama só o subcomando dedup (não depende dos outros módulos do dispatcher)."""
    from rslib import dedup
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    sub = parser.add_subparsers()
    dedup.registrar(sub)
    args = parser.parse_args(["--dir", str(raiz), "dedup", *argv])
    return args.func(args)


def ler(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def registros_plantados():
    return ler(PLANTADOS)


def escrever_registros(raiz, linhas):
    from rslib import esquema
    with open(raiz / esquema.ARQ_REGISTROS, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=esquema.COLUNAS_REGISTROS, lineterminator="\n")
        w.writeheader()
        for l in linhas:
            w.writerow({c: l.get(c, "") for c in esquema.COLUNAS_REGISTROS})


def registro(id_registro, titulo, autores, ano, **extra):
    from rslib import normalizar
    base = {
        "id_registro": id_registro, "busca_id": id_registro.split("-")[0], "fonte": extra.pop("fonte", "wos"),
        "metodo_identificacao": "base", "titulo": titulo, "autores": autores,
        "primeiro_autor_sobrenome": normalizar.sobrenome_primeiro_autor(autores), "ano": str(ano),
        "tipo_publicacao": extra.pop("tipo", "artigo"), "resumo": "Resumo.", "resumo_truncado": "0",
    }
    base.update(extra)
    return base


def unicos_por_registro(raiz):
    from rslib import esquema
    mapa = {}
    for u in ler(raiz / esquema.ARQ_UNICOS):
        for rid in u["ids_registro"].split("|"):
            mapa[rid] = u
    return mapa


def pares(raiz):
    from rslib import esquema
    return {(p["id_a"], p["id_b"]): p for p in ler(raiz / esquema.ARQ_DEDUP_PARES)}


@pytest.fixture
def projeto_plantado(projeto_vazio):
    from rslib import esquema
    shutil.copy(PLANTADOS, projeto_vazio / esquema.ARQ_REGISTROS)
    return projeto_vazio


# ---------------------------------------------------------------------------
# Regras e pares plantados
# ---------------------------------------------------------------------------
def test_pares_plantados_fundem_ou_nao(projeto_plantado, capsys):
    assert rodar(projeto_plantado) == 0
    u = unicos_por_registro(projeto_plantado)
    mesmo = lambda a, b: u[a]["id_rs"] == u[b]["id_rs"]
    # fundem
    assert mesmo("B01-00001", "B02-00001") and mesmo("B01-00001", "B03-00001")  # DOI com prefixo/caixa
    assert mesmo("B01-00002", "B03-00002")  # acentos e caixa, sem DOI, anos vizinhos
    assert mesmo("B01-00004", "B02-00003")  # título traduzido com o mesmo DOI
    assert mesmo("B01-00008", "B03-00003")  # fuzzy >= 95
    assert mesmo("B01-00010", "B05-00001")  # mesmo id da fonte
    # não fundem
    assert not mesmo("B01-00005", "B01-00006")  # Part I / Part II
    assert not mesmo("B04-00001", "B01-00007")  # tese <-> artigo
    assert not mesmo("B01-00009", "B03-00004")  # candidato fica separado até revisão
    assert not mesmo("B01-00011", "B01-00012")  # mesmo título com 4 anos de distância
    assert not mesmo("B01-00002", "B02-00004")  # mesmo autor e ano, títulos distintos
    # preprint <-> publicado: relatos do mesmo estudo, ligados por id_estudo, nunca fundidos
    assert not mesmo("B02-00002", "B01-00003")
    assert u["B02-00002"]["id_estudo"] == u["B01-00003"]["id_estudo"]

    resumo = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert resumo["comando"] == "dedup"
    assert resumo["n_registros"] == 22 and resumo["n_unicos"] == 16 and resumo["duplicatas_removidas"] == 6
    assert resumo["duplicatas_removidas_por_tipo"] == {"exato": 5, "fuzzy": 1}
    assert resumo["candidatos_pendentes"] == 1 and resumo["n_versoes_ligadas"] == 1 and resumo["n_estudos"] == 15


def test_regras_e_decisoes_no_dedup_pares(projeto_plantado):
    from rslib import dedup, esquema
    assert rodar(projeto_plantado) == 0
    with open(projeto_plantado / esquema.ARQ_DEDUP_PARES, encoding="utf-8") as f:
        assert next(csv.reader(f)) == esquema.COLUNAS_DEDUP_PARES
    p = pares(projeto_plantado)
    assert p[("B01-00001", "B02-00001")]["regra"] == "R1_doi"
    assert p[("B01-00001", "B02-00001")]["doi_a"] == p[("B01-00001", "B02-00001")]["doi_b"] == "10.1016/j.labeco.2016.04.004"
    assert p[("B01-00004", "B02-00003")]["regra"] == "R1_doi"
    assert p[("B01-00010", "B05-00001")]["regra"] == "R2_id_fonte"
    assert p[("B01-00002", "B03-00002")]["regra"] == "R3_titulo_exato"
    assert p[("B01-00008", "B03-00003")]["regra"] == "R4_fuzzy_auto"
    versao = p[("B01-00003", "B02-00002")]
    assert versao["regra"] == "versao" and versao["decisao"] == "ligado" and versao["decidido_por"] == "script"
    cand = p[("B01-00009", "B03-00004")]
    assert cand["regra"] == "R5_candidato" and cand["decisao"] == "candidato" and 85 <= float(cand["score"]) < 95
    parte = p[("B01-00005", "B01-00006")]
    assert parte["decisao"] == "rejeitado" and parte["decidido_por"] == "regra" and "parte" in parte["motivo"]
    tese = p[("B01-00007", "B04-00001")]
    assert tese["decisao"] == "rejeitado" and tese["motivo"] == "tese_artigo_nunca_funde"
    for linha in p.values():
        assert linha["regra"] in esquema.REGRAS_DEDUP and linha["decisao"] in dedup.DECISOES_PARES
    assert ("B01-00011", "B01-00012") not in p


def test_mesclagem_por_prioridade_e_versao(projeto_plantado):
    from rslib import esquema
    assert rodar(projeto_plantado) == 0
    u = unicos_por_registro(projeto_plantado)
    with open(projeto_plantado / esquema.ARQ_UNICOS, encoding="utf-8") as f:
        assert next(csv.reader(f)) == esquema.COLUNAS_UNICOS

    beland = u["B01-00001"]
    assert beland["fontes"] == "openalex|scopus|wos" and beland["n_fontes"] == "3"
    assert beland["tipo_duplicata"] == "exato" and beland["doi"] == "10.1016/j.labeco.2016.04.004"
    assert beland["titulo"] == "Ill Communication: Technology, Distraction & Student Performance"  # OpenAlex, sem HTML
    assert beland["resumo_truncado"] == "0" and "truncated" not in beland["resumo"]  # mais longo NÃO truncado
    assert beland["citado_por"] == "310"
    assert beland["palavras_chave"] == "Mobile Phones; student performance; schools"
    assert beland["titulo_alt"] == ""  # variação de pontuação não é título alternativo

    # versões não se mesclam: cada relato guarda os próprios metadados e o id_estudo é comum
    preprint, publicado = u["B02-00002"], u["B01-00003"]
    assert preprint["ids_registro"] == "B02-00002" and publicado["ids_registro"] == "B01-00003"
    assert preprint["tipo_duplicata"] == publicado["tipo_duplicata"] == "unico"
    assert publicado["doi"] == "10.1016/j.econedurev.2023.102001" and publicado["ano"] == "2023"
    assert "preprint" not in publicado["flags"].split("|") and publicado["tipo_publicacao"] == "artigo"
    assert "preprint" in preprint["flags"].split("|") and preprint["doi"] == "10.31235/osf.io/abcde"
    assert preprint["id_estudo"] == publicado["id_estudo"] == esquema.id_estudo_de(
        min(preprint["id_rs"], publicado["id_rs"]))

    traduzido = u["B01-00004"]
    assert traduzido["titulo"] == "Conditional cash transfers and school attendance"
    assert traduzido["titulo_alt"] == "Transferências condicionais de renda e frequência escolar"

    assert u["B01-00008"]["tipo_duplicata"] == "fuzzy"
    assert u["B01-00005"]["tipo_duplicata"] == "unico"
    assert "sem_resumo" in u["B02-00004"]["flags"].split("|")
    assert u["B02-00004"]["id_estudo"] == "ES" + u["B02-00004"]["id_rs"][2:]


def test_chaves_unicas_e_validas(projeto_plantado):
    from rslib import chave, esquema
    assert rodar(projeto_plantado) == 0
    linhas = ler(projeto_plantado / esquema.ARQ_UNICOS)
    chaves = [l["chave"] for l in linhas]
    assert len(set(chaves)) == len(chaves) and all(chave.chave_valida(k) for k in chaves)
    ids = [l["id_rs"] for l in linhas]
    assert ids == [f"RS{i:04d}" for i in range(1, len(linhas) + 1)]
    u = unicos_por_registro(projeto_plantado)
    assert {u["B01-00005"]["chave"], u["B01-00006"]["chave"]} == {"Costa2015", "Costa2015a"}


# ---------------------------------------------------------------------------
# Idempotência e estabilidade de ids
# ---------------------------------------------------------------------------
def test_reexecucao_idempotente(projeto_plantado, capsys):
    """Reexecução sem mudança não grava outro dedup_executado (antes enchia o log e desatualizava a declaração)."""
    from rslib import esquema
    arquivos = (esquema.ARQ_UNICOS, esquema.ARQ_DEDUP_PARES, esquema.ARQ_LIGACAO_RELATOS)
    assert rodar(projeto_plantado) == 0
    primeiro = ultimo_resumo(capsys)
    assert primeiro["reexecucao"] is False and primeiro["evento_registrado"] is True
    antes = [(projeto_plantado / a).read_bytes() for a in arquivos]
    n_linhas_log = len(ler_jsonl(projeto_plantado / esquema.ARQ_LOG))
    assert rodar(projeto_plantado) == 0
    segundo = ultimo_resumo(capsys)
    assert [(projeto_plantado / a).read_bytes() for a in arquivos] == antes
    assert segundo["sem_mudancas"] is True and segundo["reexecucao"] is True and segundo["evento_registrado"] is False
    assert len(ler_jsonl(projeto_plantado / esquema.ARQ_LOG)) == n_linhas_log
    eventos = [e for e in ler_jsonl(projeto_plantado / esquema.ARQ_LOG) if e["evento"] == "dedup_executado"]
    assert len(eventos) == 1 and eventos[0]["dados"]["sem_mudancas"] is False
    # parâmetro diferente é registrado mesmo sem mudança nas saídas
    assert rodar(projeto_plantado, "--limiar-auto", "96") == 0
    assert ultimo_resumo(capsys)["evento_registrado"] is True
    eventos = [e for e in ler_jsonl(projeto_plantado / esquema.ARQ_LOG) if e["evento"] == "dedup_executado"]
    assert len(eventos) == 2 and eventos[1]["dados"]["limiar_auto"] == 96


def test_ids_estaveis_com_novos_registros(projeto_plantado):
    from rslib import esquema
    assert rodar(projeto_plantado) == 0
    antes = {rid: (u["id_rs"], u["chave"]) for rid, u in unicos_por_registro(projeto_plantado).items()}
    linhas = registros_plantados()
    # Nova busca: duplicata do Beland (mesmo DOI) vinda do SciELO e um registro novo que vem antes na ordenação.
    linhas.insert(0, registro("A00-00001", "Um estudo inteiramente novo sobre transparência", "Almeida, Rita", 2020))
    linhas.append(registro("B06-00001", "Ill communication", "Beland, L.", 2016, doi="10.1016/j.labeco.2016.04.004",
                           fonte="scielo"))
    linhas.append(registro("B06-00002", "Outro estudo de Silva", "Silva, João Carlos", 2019))
    escrever_registros(projeto_plantado, linhas)
    assert rodar(projeto_plantado) == 0
    depois = unicos_por_registro(projeto_plantado)
    for rid, (id_rs, k) in antes.items():
        assert (depois[rid]["id_rs"], depois[rid]["chave"]) == (id_rs, k), rid
    assert depois["B06-00001"]["id_rs"] == antes["B01-00001"][0]
    assert depois["B06-00001"]["fontes"] == "openalex|scopus|wos|scielo"
    novos = sorted({depois["A00-00001"]["id_rs"], depois["B06-00002"]["id_rs"]})
    assert novos == ["RS0017", "RS0018"]
    assert depois["B06-00002"]["chave"] == "Silva2019b"  # Silva2019 e Silva2019a já emitidas


def test_revisar_confirma_candidato_e_aposenta_id(projeto_plantado, capsys):
    from rslib import esquema
    assert rodar(projeto_plantado) == 0
    u = unicos_por_registro(projeto_plantado)
    id_a, id_b = u["B01-00009"]["id_rs"], u["B03-00004"]["id_rs"]
    chave_aposentada = u["B03-00004"]["chave"]
    # O humano edita o próprio dedup_pares.csv
    caminho = projeto_plantado / esquema.ARQ_DEDUP_PARES
    linhas = ler(caminho)
    for l in linhas:
        if (l["id_a"], l["id_b"]) == ("B01-00009", "B03-00004"):
            l["decisao"], l["motivo"] = "confirmado", "mesmo artigo, título mudou na revisão"
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=esquema.COLUNAS_DEDUP_PARES, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)
    capsys.readouterr()
    assert rodar(projeto_plantado, "--revisar", str(caminho), "--por", "revisor_humano_2") == 0
    resumo = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert resumo["decisoes_novas"] == 1 and resumo["candidatos_pendentes"] == 0

    depois = unicos_por_registro(projeto_plantado)
    fundido = depois["B01-00009"]
    assert fundido["id_rs"] == min(id_a, id_b) == depois["B03-00004"]["id_rs"]
    assert fundido["tipo_duplicata"] == "fuzzy"
    assert all(l["id_rs"] != max(id_a, id_b) for l in ler(projeto_plantado / esquema.ARQ_UNICOS))
    par = pares(projeto_plantado)[("B01-00009", "B03-00004")]
    assert par["decisao"] == "confirmado" and par["decidido_por"] == "revisor_humano_2"

    eventos = ler_jsonl(projeto_plantado / esquema.ARQ_LOG)
    revisados = [e for e in eventos if e["evento"] == "dedup_revisado"]
    assert len(revisados) == 1 and revisados[0]["ator"] == {"tipo": "humano", "id": "revisor_humano_2", "modelo": None}
    ultimo = [e for e in eventos if e["evento"] == "dedup_executado"][-1]
    assert max(id_a, id_b) in ultimo["dados"]["ids_rs_aposentados"]

    # Reaplicar o mesmo arquivo não gera nova decisão; decisões persistem sem --revisar.
    assert rodar(projeto_plantado, "--revisar", str(caminho)) == 0  # decidido_por já preenchido pelo dedup
    assert rodar(projeto_plantado) == 0
    assert len([e for e in ler_jsonl(projeto_plantado / esquema.ARQ_LOG) if e["evento"] == "dedup_revisado"]) == 1
    assert unicos_por_registro(projeto_plantado)["B03-00004"]["id_rs"] == min(id_a, id_b)

    # id e chave aposentados nunca são reutilizados
    linhas = registros_plantados() + [registro("B07-00001", "Terceiro estudo de orçamento participativo",
                                               "Gonçalves, Sónia", 2014)]
    escrever_registros(projeto_plantado, linhas)
    assert rodar(projeto_plantado) == 0
    novo = unicos_por_registro(projeto_plantado)["B07-00001"]
    assert novo["id_rs"] == "RS0017" and novo["chave"] not in {"Goncalves2014", chave_aposentada}


def test_revisar_rejeita_auto_e_separa(projeto_plantado):
    from rslib import esquema
    assert rodar(projeto_plantado) == 0
    antes = unicos_por_registro(projeto_plantado)
    revisao = projeto_plantado / "revisao.csv"
    revisao.write_text("id_a,id_b,decisao,motivo\nB03-00003,B01-00008,rejeitado,capítulos diferentes\n", encoding="utf-8")
    assert rodar(projeto_plantado, "--revisar", "revisao.csv", "--por", "revisor_humano_1") == 0  # relativo à raiz
    depois = unicos_por_registro(projeto_plantado)
    assert depois["B01-00008"]["id_rs"] != depois["B03-00003"]["id_rs"]
    assert depois["B01-00008"]["id_rs"] == antes["B01-00008"]["id_rs"]  # quem mantém o id é o menor id_registro
    assert depois["B03-00003"]["id_rs"] == "RS0017"
    assert pares(projeto_plantado)[("B01-00008", "B03-00003")]["decisao"] == "rejeitado"


def test_revisar_nao_funde_tese_com_artigo(projeto_plantado, capsys):
    revisao = projeto_plantado / "revisao.csv"
    revisao.write_text("id_a,id_b,decisao\nB01-00007,B04-00001,confirmado\n", encoding="utf-8")
    assert rodar(projeto_plantado, "--revisar", str(revisao), "--por", "revisor_humano_1") == 0
    saida = capsys.readouterr().out
    assert "confirmação recusada" in saida
    u = unicos_por_registro(projeto_plantado)
    assert u["B01-00007"]["id_rs"] != u["B04-00001"]["id_rs"]


def test_revisar_valida_arquivo(projeto_plantado):
    revisao = projeto_plantado / "revisao.csv"
    revisao.write_text("id_a,id_b,decisao\nB01-00007,X99-00001,confirmado\n", encoding="utf-8")
    assert rodar(projeto_plantado, "--revisar", str(revisao)) == 1
    revisao.write_text("id_a,id_b,decisao\nB01-00007,B04-00001,talvez\n", encoding="utf-8")
    assert rodar(projeto_plantado, "--revisar", str(revisao)) == 1
    revisao.write_text("id_a,decisao\nB01-00007,confirmado\n", encoding="utf-8")
    assert rodar(projeto_plantado, "--revisar", str(revisao)) == 1
    assert rodar(projeto_plantado, "--revisar", "nao_existe.csv") == 1


# ---------------------------------------------------------------------------
# Restrições de cluster e casos-limite
# ---------------------------------------------------------------------------
def test_conflito_de_doi_transitivo_vira_candidato(projeto_vazio):
    titulo = "Municipal tax amnesties and fiscal performance in Latin America"
    escrever_registros(projeto_vazio, [
        registro("B01-00001", titulo, "Ramos, Luis", 2019, doi="10.1000/aaa"),
        registro("B02-00001", titulo, "Ramos, Luis", 2019, fonte="scopus"),
        registro("B03-00001", titulo, "Ramos, Luis", 2019, doi="10.1000/bbb", fonte="openalex"),
    ])
    assert rodar(projeto_vazio) == 0
    u = unicos_por_registro(projeto_vazio)
    assert u["B01-00001"]["id_rs"] != u["B03-00001"]["id_rs"]
    p = pares(projeto_vazio)
    assert any("conflito_doi" in l["motivo"] and l["decisao"] == "candidato" for l in p.values())


def test_preprint_com_anos_distantes_nao_funde(projeto_vazio):
    titulo = "Cash transfers and political participation: experimental evidence"
    escrever_registros(projeto_vazio, [
        registro("B01-00001", titulo, "Nunes, Paula", 2012, doi="10.2139/ssrn.1234", tipo="preprint"),
        registro("B01-00002", titulo, "Nunes, Paula", 2019, doi="10.1000/pub.2019"),
    ])
    assert rodar(projeto_vazio) == 0
    u = unicos_por_registro(projeto_vazio)
    assert u["B01-00001"]["id_rs"] != u["B01-00002"]["id_rs"]
    assert u["B01-00001"]["flags"] == "preprint"


def test_titulo_igual_sem_ano_vira_candidato(projeto_vazio):
    titulo = "Local government capacity and program implementation"
    escrever_registros(projeto_vazio, [
        registro("B01-00001", titulo, "Barros, Ivo", 2018),
        registro("B02-00001", titulo, "Barros, Ivo", ""),
    ])
    assert rodar(projeto_vazio) == 0
    p = pares(projeto_vazio)[("B01-00001", "B02-00001")]
    assert p["decisao"] == "candidato" and "ano_ausente" in p["motivo"]


def test_fallback_difflib_mesmos_clusters(projeto_plantado, monkeypatch):
    from rslib import dedup, esquema
    assert rodar(projeto_plantado) == 0
    com_rapidfuzz = (projeto_plantado / esquema.ARQ_UNICOS).read_bytes()
    monkeypatch.setattr(dedup, "_fuzz", None)
    monkeypatch.setattr(dedup, "BACKEND_FUZZY", "difflib")
    assert dedup.similaridade("abc def", "abc dex") < 100
    assert rodar(projeto_plantado) == 0
    assert (projeto_plantado / esquema.ARQ_UNICOS).read_bytes() == com_rapidfuzz
    ultimo = [e for e in ler_jsonl(projeto_plantado / esquema.ARQ_LOG) if e["evento"] == "dedup_executado"][-1]
    assert ultimo["dados"]["backend_similaridade"] == "difflib" and ultimo["dados"]["sem_mudancas"] is True


def test_apagar_unicos_nao_reutiliza_ids(projeto_plantado):
    """Sem registros_unicos.csv, os ids recomeçam depois do maior já emitido (registrado no log)."""
    from rslib import esquema
    assert rodar(projeto_plantado) == 0
    (projeto_plantado / esquema.ARQ_UNICOS).unlink()
    assert rodar(projeto_plantado) == 0
    ids = [l["id_rs"] for l in ler(projeto_plantado / esquema.ARQ_UNICOS)]
    assert ids[0] == "RS0017" and len(ids) == 16


# ---------------------------------------------------------------------------
# Pendências, erros e log
# ---------------------------------------------------------------------------
def test_pendencia_no_autopiloto_abre_e_fecha(projeto_plantado):
    from rslib import estado
    est = estado.carregar_estado(projeto_plantado)
    est["modo"]["autonomia"] = "autopiloto"
    estado.salvar_estado(projeto_plantado, est)
    assert rodar(projeto_plantado) == 0
    abertas = estado.pendencias_abertas(estado.carregar_estado(projeto_plantado))
    assert len(abertas) == 1 and abertas[0]["tipo"] == "dedup_candidatos" and abertas[0]["n"] == 1
    assert rodar(projeto_plantado) == 0  # não duplica a pendência
    assert len(estado.pendencias_abertas(estado.carregar_estado(projeto_plantado))) == 1
    revisao = projeto_plantado / "revisao.csv"
    revisao.write_text("id_a,id_b,decisao\nB01-00009,B03-00004,rejeitado\n", encoding="utf-8")
    assert rodar(projeto_plantado, "--revisar", str(revisao), "--tipo-ator", "ia_subagente", "--por", "revisor_A") == 0
    assert not estado.pendencias_abertas(estado.carregar_estado(projeto_plantado))


def test_checkpoints_nao_abre_pendencia(projeto_plantado, capsys):
    from rslib import estado
    assert rodar(projeto_plantado) == 0
    assert not estado.pendencias_abertas(estado.carregar_estado(projeto_plantado))
    assert "aguardam revisão" in capsys.readouterr().out


def test_erros_de_uso(projeto_vazio, tmp_path_factory):
    assert rodar(projeto_vazio) == 1  # sem registros.csv
    escrever_registros(projeto_vazio, [registro("B01-00001", "Um título qualquer aqui", "A, B", 2020),
                                       registro("B01-00001", "Outro título qualquer", "C, D", 2021)])
    assert rodar(projeto_vazio) == 1  # id_registro duplicado
    escrever_registros(projeto_vazio, [registro("B01-00001", "Um título qualquer aqui", "A, B", 2020)])
    assert rodar(projeto_vazio, "--limiar-auto", "80", "--limiar-candidato", "90") == 1
    (projeto_vazio / "dados" / "registros.csv").write_text("id_registro,titulo\nB01-00001,x\n", encoding="utf-8")
    assert rodar(projeto_vazio) == 1  # colunas ausentes
    sem_projeto = tmp_path_factory.mktemp("sem_projeto")
    assert rodar(sem_projeto) == 1


def test_eventos_validam_schema(projeto_plantado):
    jsonschema = pytest.importorskip("jsonschema")
    from rslib import esquema, estado
    est = estado.carregar_estado(projeto_plantado)
    est["modo"]["autonomia"] = "autopiloto"
    estado.salvar_estado(projeto_plantado, est)
    assert rodar(projeto_plantado) == 0
    schema = json.loads((SKILL / "assets/schemas/evento.schema.json").read_text(encoding="utf-8"))
    eventos = ler_jsonl(projeto_plantado / esquema.ARQ_LOG)
    for ev in eventos:
        jsonschema.validate(ev, schema)
    assert {"dedup_executado", "pendencia_aberta"} <= {e["evento"] for e in eventos}
    estado_schema = json.loads((SKILL / "assets/schemas/estado.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(estado.carregar_estado(projeto_plantado), estado_schema)


def test_id_estudo_convencao_e_ligacao_de_relatos_sobrevive_a_novo_dedup(projeto_vazio):
    """id_estudo = esquema.id_estudo_de(id_rs); dedup preserva o existente; tese↔artigo ligados continuam ligados."""
    from rslib import esquema, textos
    regs = [
        registro("B01-00001", "Transferencias condicionadas e frequencia escolar no semiarido", "Souza, Gabriela", 2017,
                 tipo="tese", fonte="openalex"),
        registro("B01-00002", "Transferencias condicionadas e frequencia escolar no semiarido brasileiro",
                 "Souza, Gabriela | Lima, Rui", 2018, doi="10.5555/rbe.2018.009"),
        registro("B01-00003", "Merenda escolar e aprendizagem em escolas rurais", "Costa, Ana", 2019),
    ]
    escrever_registros(projeto_vazio, regs)
    assert rodar(projeto_vazio) == 0
    u = unicos_por_registro(projeto_vazio)
    assert all(l["id_estudo"] == esquema.id_estudo_de(l["id_rs"]) for l in u.values())
    tese, artigo = u["B01-00001"], u["B01-00002"]
    assert tese["id_rs"] != artigo["id_rs"]
    assert pares(projeto_vazio)[("B01-00001", "B01-00002")]["motivo"] == "tese_artigo_nunca_funde"

    textos.ligar_relatos(projeto_vazio, [(artigo["id_rs"], tese["id_rs"])])
    estudo_ligado = esquema.id_estudo_de(min(tese["id_rs"], artigo["id_rs"]))
    ligacao_antes = (projeto_vazio / textos.ARQ_LIGACAO).read_text(encoding="utf-8")

    # nova busca traz o artigo de novo (mesmo DOI) e um estudo novo; dedup roda outra vez
    regs += [registro("B02-00001", "Transferências condicionadas e frequência escolar no semiárido brasileiro",
                      "Souza G.; Lima R.", 2018, doi="https://doi.org/10.5555/RBE.2018.009", fonte="scopus"),
             registro("B02-00002", "Bolsas para meninas e matricula em Bangladesh", "Pires, Rafael", 2013,
                      fonte="scopus")]
    escrever_registros(projeto_vazio, regs)
    assert rodar(projeto_vazio) == 0
    u2 = unicos_por_registro(projeto_vazio)
    assert u2["B02-00001"]["id_rs"] == artigo["id_rs"] and u2["B01-00001"]["id_rs"] == tese["id_rs"]
    assert u2["B01-00001"]["id_estudo"] == u2["B02-00001"]["id_estudo"] == estudo_ligado
    novo = u2["B02-00002"]
    assert novo["id_estudo"] == esquema.id_estudo_de(novo["id_rs"])
    # religar com a mesma lista é idempotente e não perde a ligação
    textos.ligar_relatos(projeto_vazio, [(artigo["id_rs"], tese["id_rs"])])
    assert (projeto_vazio / textos.ARQ_LIGACAO).read_text(encoding="utf-8") == ligacao_antes
    assert unicos_por_registro(projeto_vazio)["B01-00002"]["id_estudo"] == estudo_ligado


# ---------------------------------------------------------------------------
# Buscas substituídas (ativa=false) e flags da fonte (v1.1)
# ---------------------------------------------------------------------------
def desativar_busca(raiz, busca_id, por="B09"):
    from rslib import esquema, estado
    est = estado.carregar_estado(raiz)
    b = next((x for x in est["buscas"] if x["id"] == busca_id), None)
    if b is None:
        b = {"id": busca_id, "fonte": "wos"}
        est["buscas"].append(b)
    b.update({esquema.CAMPO_BUSCA_ATIVA: False, "substituida_por": por})
    estado.salvar_estado(raiz, est)


def ultimo_resumo(capsys):
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_busca_inativa_ignorada_sem_reatribuir_ids(projeto_vazio, capsys):
    from rslib import esquema, estado
    raiz = projeto_vazio
    regs = [
        registro("B01-00001", "Cash transfers and school attendance in Brazil", "Silva, Ana", 2019, doi="10.5555/cash.2019.1"),
        registro("B01-00002", "Municipal tax amnesties and compliance", "Souza, Rui", 2018, doi="10.5555/tax.2018.1"),
        registro("B02-00001", "Cash transfers and school attendance in Brazil", "Silva, A.", 2019, doi="10.5555/cash.2019.1",
                 fonte="scopus"),
        registro("B02-00002", "Participatory budgeting and infant mortality", "Costa, Lia", 2017, fonte="scopus"),
    ]
    escrever_registros(raiz, regs)
    assert rodar(raiz) == 0
    antes = {l["id_rs"]: l for l in ler(raiz / esquema.ARQ_UNICOS)}
    assert {l["id_rs"]: l["ids_registro"] for l in antes.values()} == {
        "RS0001": "B01-00001|B02-00001", "RS0002": "B01-00002", "RS0003": "B02-00002"}
    capsys.readouterr()

    # B01 foi substituída por B09; B09 reencontra o estudo que só estava em B01.
    # Decisão humana antiga envolvendo registro inativo continua no log e não quebra o dedup.
    estado.registrar_evento(raiz, "dedup_revisado", "05_organizacao", "humano", "revisor_humano_1",
                            dados={"decisoes": [{"id_a": "B01-00002", "id_b": "B02-00002", "decisao": "rejeitado"}]})
    desativar_busca(raiz, "B01")
    escrever_registros(raiz, regs + [registro("B09-00001", "Municipal tax amnesties and compliance", "Souza, Rui",
                                              2018, doi="10.5555/tax.2018.1", fonte="scopus")])
    assert rodar(raiz) == 0
    resumo = ultimo_resumo(capsys)
    depois = {l["id_rs"]: l for l in ler(raiz / esquema.ARQ_UNICOS)}
    # quem continua mantém o id; o cluster misto perde só o membro inativo
    assert depois["RS0001"]["ids_registro"] == "B02-00001" and depois["RS0001"]["chave"] == antes["RS0001"]["chave"]
    assert depois["RS0003"] == antes["RS0003"]
    # cluster só de registros inativos: linha preservada, marcada e fora do conjunto ativo
    inativo = depois["RS0002"]
    assert inativo["flags"].split("|").count("busca_inativa") == 1
    assert {k: v for k, v in inativo.items() if k != "flags"} == {k: v for k, v in antes["RS0002"].items() if k != "flags"}
    # o registro novo vira id novo (não herda o inativo) e o resumo avisa a coincidência de DOI
    assert depois["RS0004"]["ids_registro"] == "B09-00001"
    assert resumo["n_registros"] == 3 and resumo["n_unicos"] == 3 and resumo["duplicatas_removidas"] == 0
    assert resumo["buscas_inativas"] == ["B01"] and resumo["n_registros_inativos"] == 2
    assert resumo["n_unicos_inativos"] == 1
    ev = [e for e in ler_jsonl(raiz / esquema.ARQ_LOG) if e["evento"] == "dedup_executado"][-1]
    assert ev["dados"]["ids_rs_inativos"] == ["RS0002"] and ev["dados"]["ultimo_id_rs_num"] == 4
    assert any("RS0004" in a and "RS0002" in a for a in ev["dados"]["avisos"])
    assert "RS0002" not in ev["dados"]["ids_rs_aposentados"]
    assert not any("B01-" in p["id_a"] + p["id_b"] for p in ler(raiz / esquema.ARQ_DEDUP_PARES))
    from rslib.dedup import unicos_ativos
    assert {u["id_rs"] for u in unicos_ativos(ler(raiz / esquema.ARQ_UNICOS))} == {"RS0001", "RS0003", "RS0004"}

    # idempotente: nada muda e a flag não se repete
    conteudo = (raiz / esquema.ARQ_UNICOS).read_bytes()
    assert rodar(raiz) == 0
    assert (raiz / esquema.ARQ_UNICOS).read_bytes() == conteudo

    # sem registros_unicos.csv, ids e chave do cluster inativo não são reutilizados
    (raiz / esquema.ARQ_UNICOS).unlink()
    escrever_registros(raiz, regs + [registro("B09-00001", "Municipal tax amnesties and compliance", "Souza, Rui",
                                              2018, doi="10.5555/tax.2018.1", fonte="scopus"),
                                     registro("B09-00002", "Municipal tax amnesties revisited", "Souza, Rui", 2018)])
    assert rodar(raiz) == 0
    novos = {l["ids_registro"]: l for l in ler(raiz / esquema.ARQ_UNICOS)}
    assert all(int(l["id_rs"][2:]) >= 5 for l in novos.values())
    assert novos["B09-00002"]["chave"] != antes["RS0002"]["chave"]


def test_substituicao_pelo_importador_e_dedup(projeto_vazio, capsys):
    """Fluxo real: importar B02, dedup, importar B06 --substituir B02, dedup."""
    from rslib import esquema
    from rslib.importar import cli
    raiz = projeto_vazio
    fix = FIXTURES / "importar"
    cli.importar_arquivo(raiz, fix / "scopus.csv", "B02")
    assert rodar(raiz) == 0
    n_antes = len(ler(raiz / esquema.ARQ_UNICOS))
    resumo = cli.importar_arquivo(raiz, fix / "scopus_antigo.csv", "B06", substituir="B02", motivo="string v2")
    assert any("rs.py dedup" in a for a in resumo["avisos"])
    capsys.readouterr()
    assert rodar(raiz) == 0
    r = ultimo_resumo(capsys)
    unicos = ler(raiz / esquema.ARQ_UNICOS)
    inativos = [u for u in unicos if "busca_inativa" in u["flags"]]
    assert len(inativos) == n_antes and all(u["ids_registro"].startswith("B02-") for u in inativos)
    ativos = [u for u in unicos if "busca_inativa" not in u["flags"]]
    assert {rid.split("-")[0] for u in ativos for rid in u["ids_registro"].split("|")} == {"B06"}
    assert r["n_registros"] == sum(1 for l in ler(raiz / esquema.ARQ_REGISTROS) if l["busca_id"] == "B06")


def test_retratado_da_fonte_vira_flag_do_unico(projeto_vazio):
    from rslib import esquema
    from rslib.importar import flags
    raiz = projeto_vazio
    escrever_registros(raiz, [
        registro("B04-00001", "Programas de anistia: um estudo", "Lima, Rui", 2020, fonte="openalex"),
        registro("B05-00001", "Programas de anistia: um estudo", "Lima, Rui", 2020, fonte="scopus"),
        registro("B04-00002", "Parcelamentos tributários e arrecadação", "Rocha, Ana", 2021, fonte="openalex"),
    ])
    flags.acrescentar(raiz, [{"id_registro": "B05-00001", "flag": "retratado", "origem": "openalex:is_retracted"}])
    assert rodar(raiz) == 0
    u = unicos_por_registro(raiz)
    assert u["B04-00001"]["id_rs"] == u["B05-00001"]["id_rs"]
    assert "retratado" in u["B04-00001"]["flags"].split("|")  # membro não representante marcado basta
    assert "retratado" not in u["B04-00002"]["flags"]
    ev = [e for e in ler_jsonl(raiz / esquema.ARQ_LOG) if e["evento"] == "dedup_executado"][-1]
    assert ev["dados"]["n_retratados"] == 1 and flags.ARQ_REGISTROS_FLAGS in {a["caminho"] for a in ev["artefatos"]}


def test_retratado_openalex_do_importador_ao_dedup(projeto_vazio):
    """is_retracted do OpenAlex sem 'retract' no título: antes o dedup não marcava."""
    from rslib.importar import cli
    raiz = projeto_vazio
    cli.importar_arquivo(raiz, FIXTURES / "importar" / "openalex.csv", "B04")
    assert rodar(raiz) == 0
    por_fonte = {u["id_fonte"]: u for u in ler(raiz / "dados/registros_unicos.csv")}
    assert "retratado" in por_fonte["W1000000002"]["flags"].split("|")
    assert not any("retratado" in u["flags"] for k, u in por_fonte.items() if k != "W1000000002")


# ---------------------------------------------------------------------------
# Versões preprint/working paper <-> publicado: relatos ligados, não fundidos (v1.2)
# ---------------------------------------------------------------------------
TITULO_VERSAO = "Cash transfers and school attendance: experimental evidence from Honduras"


def registros_versao():
    return [
        registro("B01-00001", TITULO_VERSAO, "Dias, Elena", 2020, doi="10.2139/ssrn.555", tipo="preprint",
                 fonte="openalex", resumo="Working paper com amostra piloto."),
        registro("B02-00001", TITULO_VERSAO, "Dias, Elena", 2021, doi="10.5555/jde.2021.005", fonte="scopus",
                 resumo="Versão publicada com a amostra completa."),
        registro("B02-00002", "Merenda escolar e aprendizagem em escolas rurais", "Costa, Ana", 2019, fonte="scopus"),
    ]


def ligacao(raiz):
    from rslib import esquema
    caminho = raiz / esquema.ARQ_LIGACAO_RELATOS
    return {l["id_rs"]: l for l in ler(caminho)} if caminho.exists() else {}


def test_versao_nao_funde_e_liga_por_id_estudo(projeto_vazio, capsys):
    """Regressão: preprint/WP e publicado eram fundidos (perdia-se o relato); agora ficam ligados."""
    from rslib import esquema
    raiz = projeto_vazio
    escrever_registros(raiz, registros_versao())
    assert rodar(raiz) == 0
    resumo = ultimo_resumo(capsys)
    u = unicos_por_registro(raiz)
    wp, pub, outro = u["B01-00001"], u["B02-00001"], u["B02-00002"]
    assert wp["id_rs"] != pub["id_rs"] and wp["ids_registro"] == "B01-00001" and pub["ids_registro"] == "B02-00001"
    assert wp["id_estudo"] == pub["id_estudo"] == esquema.id_estudo_de(min(wp["id_rs"], pub["id_rs"]))
    assert outro["id_estudo"] == esquema.id_estudo_de(outro["id_rs"])
    assert wp["resumo"] == "Working paper com amostra piloto." and "preprint" in wp["flags"].split("|")
    par = pares(raiz)[("B01-00001", "B02-00001")]
    assert (par["regra"], par["decisao"], par["decidido_por"]) == ("versao", "ligado", "script")
    lig = ligacao(raiz)
    assert set(lig) == {wp["id_rs"], pub["id_rs"]} and {l["id_estudo"] for l in lig.values()} == {wp["id_estudo"]}
    assert resumo["n_unicos"] == 3 and resumo["duplicatas_removidas"] == 0 and resumo["candidatos_pendentes"] == 0
    assert resumo["n_versoes_ligadas"] == 1 and resumo["n_estudos"] == 2
    assert esquema.ARQ_LIGACAO_RELATOS in resumo["arquivos"]
    ev = [e for e in ler_jsonl(raiz / esquema.ARQ_LOG) if e["evento"] == "dedup_executado"][-1]
    assert ev["dados"]["ligacao_relatos"]["pares_versao"] == [sorted([wp["id_rs"], pub["id_rs"]])]
    assert esquema.ARQ_LIGACAO_RELATOS in {a["caminho"] for a in ev["artefatos"]}
    from rslib import dedup
    assert dedup.pares_versao_ligados(raiz) == [tuple(sorted([wp["id_rs"], pub["id_rs"]]))]
    # idempotente, sem evento novo
    assert rodar(raiz) == 0
    assert ultimo_resumo(capsys)["reexecucao"] is True
    assert len([e for e in ler_jsonl(raiz / esquema.ARQ_LOG) if e["evento"] == "dedup_executado"]) == 1


def test_versao_preserva_ligacao_humana_e_revisao_desfaz_so_a_automatica(projeto_vazio, capsys):
    from rslib import esquema, textos
    raiz = projeto_vazio
    regs = registros_versao() + [
        registro("B03-00001", "Transferencias condicionadas e frequencia escolar no semiarido", "Souza, Gabriela", 2017,
                 tipo="tese", fonte="openalex"),
        registro("B03-00002", "Transferencias condicionadas e frequencia escolar no semiarido brasileiro",
                 "Souza, Gabriela | Lima, Rui", 2018, doi="10.5555/rbe.2018.009", fonte="openalex"),
    ]
    escrever_registros(raiz, regs)
    assert rodar(raiz) == 0
    u = unicos_por_registro(raiz)
    wp, pub = u["B01-00001"]["id_rs"], u["B02-00001"]["id_rs"]
    tese, artigo = u["B03-00001"]["id_rs"], u["B03-00002"]["id_rs"]
    estudo_versao = esquema.id_estudo_de(min(wp, pub))
    estudo_tese = esquema.id_estudo_de(min(tese, artigo))

    # humano liga tese e artigo no texto completo (a lista dele não traz o par de versão)
    textos.ligar_relatos(raiz, [(artigo, tese)])
    # nova busca e novo dedup: as duas ligações ficam de pé
    escrever_registros(raiz, regs + [registro("B04-00001", "Bolsas para meninas e matricula", "Pires, Rafael", 2013)])
    assert rodar(raiz) == 0
    u = unicos_por_registro(raiz)
    assert u["B01-00001"]["id_estudo"] == u["B02-00001"]["id_estudo"] == estudo_versao
    assert u["B03-00001"]["id_estudo"] == u["B03-00002"]["id_estudo"] == estudo_tese
    assert set(ligacao(raiz)) == {wp, pub, tese, artigo}
    ev = [e for e in ler_jsonl(raiz / esquema.ARQ_LOG) if e["evento"] == "dedup_executado"][-1]
    assert ev["dados"]["ligacao_relatos"]["pares_preservados"] == [sorted([tese, artigo])]
    assert ev["dados"]["ligacao_relatos"]["origem_preservados"] == "arquivo"
    assert rodar(raiz) == 0  # agora os preservados vêm do log (arquivo intacto)
    assert ultimo_resumo(capsys)["reexecucao"] is True

    # humano rejeita a ligação de versão: só ela é desfeita
    revisao = raiz / "revisao.csv"
    revisao.write_text("id_a,id_b,decisao,motivo\nB01-00001,B02-00001,rejeitado,amostras de programas diferentes\n",
                       encoding="utf-8")
    assert rodar(raiz, "--revisar", str(revisao), "--por", "revisor_humano_2") == 0
    u = unicos_por_registro(raiz)
    assert u["B01-00001"]["id_estudo"] == esquema.id_estudo_de(wp)
    assert u["B02-00001"]["id_estudo"] == esquema.id_estudo_de(pub)
    assert u["B03-00001"]["id_estudo"] == u["B03-00002"]["id_estudo"] == estudo_tese
    assert set(ligacao(raiz)) == {tese, artigo}
    par = pares(raiz)[("B01-00001", "B02-00001")]
    assert (par["decisao"], par["decidido_por"]) == ("rejeitado", "revisor_humano_2")


def test_versao_candidata_confirmada_vira_ligacao_nao_fusao(projeto_vazio, capsys):
    from rslib import esquema
    raiz = projeto_vazio
    escrever_registros(raiz, [
        registro("B01-00001", TITULO_VERSAO, "Dias, Elena", 2020, doi="10.31235/osf.io/abcd1", tipo="preprint"),
        registro("B02-00001", TITULO_VERSAO, "Ramos, Tito | Dias, Elena", 2021, doi="10.5555/jde.2021.005"),
    ])
    assert rodar(raiz) == 0
    par = pares(raiz)[("B01-00001", "B02-00001")]
    assert par["regra"] == "versao" and par["decisao"] == "candidato" and "sobrenome" in par["motivo"]
    assert ultimo_resumo(capsys)["candidatos_pendentes"] == 1
    linhas = ler(raiz / esquema.ARQ_DEDUP_PARES)
    linhas[0].update(decisao="confirmado", decidido_por="revisor_humano_1")  # decidido_por na planilha basta
    with open(raiz / esquema.ARQ_DEDUP_PARES, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=esquema.COLUNAS_DEDUP_PARES, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)
    assert rodar(raiz, "--revisar", esquema.ARQ_DEDUP_PARES) == 0
    resumo = ultimo_resumo(capsys)
    u = unicos_por_registro(raiz)
    assert u["B01-00001"]["id_rs"] != u["B02-00001"]["id_rs"]
    assert u["B01-00001"]["id_estudo"] == u["B02-00001"]["id_estudo"]
    par = pares(raiz)[("B01-00001", "B02-00001")]
    assert (par["decisao"], par["decidido_por"]) == ("ligado", "revisor_humano_1")
    assert resumo["candidatos_pendentes"] == 0 and resumo["n_versoes_ligadas"] == 1
    ev = [e for e in ler_jsonl(raiz / esquema.ARQ_LOG) if e["evento"] == "dedup_revisado"]
    assert len(ev) == 1 and ev[0]["ator"]["id"] == "revisor_humano_1"
    # a linha 'ligado' decidida por humano não é reaplicada como decisão nova
    assert rodar(raiz, "--revisar", esquema.ARQ_DEDUP_PARES) == 0
    assert ultimo_resumo(capsys)["decisoes_novas"] == 0


def test_ligacao_automatica_nao_junta_dois_publicados(projeto_vazio, capsys):
    raiz = projeto_vazio
    escrever_registros(raiz, [
        registro("B01-00001", TITULO_VERSAO, "Dias, Elena", 2020, doi="10.2139/ssrn.555", tipo="preprint"),
        registro("B02-00001", TITULO_VERSAO, "Dias, Elena", 2021, doi="10.5555/jde.2021.005"),
        registro("B03-00001", TITULO_VERSAO, "Dias, Elena", 2021, doi="10.5555/outra.2021.777"),
    ])
    assert rodar(raiz) == 0
    u = unicos_por_registro(raiz)
    assert len({l["id_rs"] for l in u.values()}) == 3
    assert len({l["id_estudo"] for l in u.values()}) == 2  # o preprint liga só a um dos publicados
    p = pares(raiz)
    assert any("ligaria_dois_publicados_no_estudo" in l["motivo"] and l["decisao"] == "candidato"
               for l in p.values() if l["regra"] == "versao")
    assert ultimo_resumo(capsys)["candidatos_pendentes"] >= 1


def test_revisar_exige_por_ou_decidido_por(projeto_plantado, capsys):
    """Regressão: sem --por, o dedup atribuía revisor_humano_1 a decisões sem declaração explícita."""
    from rslib import esquema
    assert rodar(projeto_plantado) == 0
    n_eventos = len(ler_jsonl(projeto_plantado / esquema.ARQ_LOG))
    revisao = projeto_plantado / "revisao.csv"
    revisao.write_text("id_a,id_b,decisao,decidido_por\nB01-00009,B03-00004,confirmado,\n", encoding="utf-8")
    capsys.readouterr()
    assert rodar(projeto_plantado, "--revisar", str(revisao)) == 1
    erro = capsys.readouterr().err
    assert "decidido_por" in erro and "--por revisor_humano_1" in erro
    assert len(ler_jsonl(projeto_plantado / esquema.ARQ_LOG)) == n_eventos  # nada gravado
    assert rodar(projeto_plantado, "--revisar", str(revisao), "--por", "script") == 1
    revisao.write_text("id_a,id_b,decisao,decidido_por\nB01-00009,B03-00004,confirmado,script\n", encoding="utf-8")
    assert rodar(projeto_plantado, "--revisar", str(revisao)) == 1  # 'script' não é papel humano
    revisao.write_text("id_a,id_b,decisao,decidido_por\nB01-00009,B03-00004,confirmado,revisora_x\n", encoding="utf-8")
    assert rodar(projeto_plantado, "--revisar", str(revisao)) == 0
    ev = [e for e in ler_jsonl(projeto_plantado / esquema.ARQ_LOG) if e["evento"] == "dedup_revisado"]
    assert len(ev) == 1 and ev[0]["ator"]["id"] == "revisora_x" and ev[0]["dados"]["decisoes"][0]["decidido_por"] == "revisora_x"
    # o dedup_pares.csv regravado (com as ligações automáticas e os bloqueios por regra) volta sem pedir --por
    assert rodar(projeto_plantado, "--revisar", esquema.ARQ_DEDUP_PARES) == 0
    assert ultimo_resumo(capsys)["decisoes_novas"] == 0


def test_cluster_antigo_de_versao_e_separado_com_aviso(projeto_vazio, capsys):
    """Projeto de versão anterior (preprint fundido ao publicado): o id fica com um relato e o outro ganha id novo."""
    from rslib import esquema
    raiz = projeto_vazio
    escrever_registros(raiz, registros_versao())
    antigo = {c: "" for c in esquema.COLUNAS_UNICOS}
    antigo.update(id_rs="RS0001", id_estudo="ES0001", chave="Dias2021", ids_registro="B01-00001|B02-00001",
                  fontes="openalex|scopus", n_fontes="2", tipo_duplicata="versao", titulo=TITULO_VERSAO,
                  autores="Dias, Elena", ano="2021")
    outro = dict(antigo, id_rs="RS0002", id_estudo="ES0002", chave="Costa2019", ids_registro="B02-00002",
                 fontes="scopus", n_fontes="1", tipo_duplicata="unico")
    with open(raiz / esquema.ARQ_UNICOS, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=esquema.COLUNAS_UNICOS, lineterminator="\n")
        w.writeheader()
        w.writerows([antigo, outro])
    assert rodar(raiz) == 0
    saida = capsys.readouterr().out
    u = unicos_por_registro(raiz)
    assert u["B01-00001"]["id_rs"] == "RS0001" and u["B02-00001"]["id_rs"] == "RS0003"
    assert u["B01-00001"]["chave"] == "Dias2021" and u["B02-00001"]["chave"] not in {"Dias2021", "Costa2019"}
    assert u["B01-00001"]["id_estudo"] == u["B02-00001"]["id_estudo"] == "ES0001"
    assert "RS0003 (novo) reúne registros que estavam em RS0001" in saida


def test_par_de_versao_repetido_em_textos_continua_automatico(projeto_vazio):
    """Quem copia o par de versão para a lista de `textos ligar-relatos` não impede desfazê-lo no dedup."""
    from rslib import esquema, textos
    raiz = projeto_vazio
    escrever_registros(raiz, registros_versao())
    assert rodar(raiz) == 0
    u = unicos_por_registro(raiz)
    wp, pub = u["B01-00001"]["id_rs"], u["B02-00001"]["id_rs"]
    textos.ligar_relatos(raiz, [(pub, wp)])
    assert rodar(raiz) == 0
    assert set(ligacao(raiz)) == {wp, pub}
    ev = [e for e in ler_jsonl(raiz / esquema.ARQ_LOG) if e["evento"] == "dedup_executado"][-1]
    assert ev["dados"]["ligacao_relatos"]["pares_preservados"] == []
    revisao = raiz / "revisao.csv"
    revisao.write_text("id_a,id_b,decisao,decidido_por\nB01-00001,B02-00001,rejeitado,revisor_humano_1\n",
                       encoding="utf-8")
    assert rodar(raiz, "--revisar", str(revisao)) == 0
    u = unicos_por_registro(raiz)
    assert u["B01-00001"]["id_estudo"] != u["B02-00001"]["id_estudo"] and ligacao(raiz) == {}


def test_rejeitar_versao_logo_depois_de_textos_desfaz_a_ligacao(projeto_vazio):
    """Sem dedup entre `textos ligar-relatos` (que repetiu o par) e a rejeição, a ligação também é desfeita."""
    from rslib import textos
    raiz = projeto_vazio
    escrever_registros(raiz, registros_versao())
    assert rodar(raiz) == 0
    u = unicos_por_registro(raiz)
    textos.ligar_relatos(raiz, [(u["B02-00001"]["id_rs"], u["B01-00001"]["id_rs"])])
    revisao = raiz / "revisao.csv"
    revisao.write_text("id_a,id_b,decisao,decidido_por\nB01-00001,B02-00001,rejeitado,revisor_humano_1\n",
                       encoding="utf-8")
    assert rodar(raiz, "--revisar", str(revisao)) == 0
    u = unicos_por_registro(raiz)
    assert u["B01-00001"]["id_estudo"] != u["B02-00001"]["id_estudo"] and ligacao(raiz) == {}


def test_mensagens_dos_modulos_de_busca_e_dedup_nao_citam_o_plano_interno():
    """Mensagens e docstrings apontam para references/ ou para o Apêndice D, nunca para o plano interno."""
    import re
    rslib = SKILL / "scripts" / "rslib"
    arquivos = [rslib / "dedup.py", rslib / "busca_openalex.py", rslib / "bola_de_neve.py", rslib / "filtrar.py",
                *sorted((rslib / "importar").glob("*.py"))]
    proibido = re.compile(r"Ap[êe]ndice\s+[BC]\b|\bPLANO\b|plano interno|§C\d")
    achados = [f"{a.name}:{n}" for a in arquivos
               for n, linha in enumerate(a.read_text(encoding="utf-8").splitlines(), 1) if proibido.search(linha)]
    assert achados == []


def test_ajuda_do_dedup_sem_papel_padrao_implicito(capsys):
    import argparse as _ap
    from rslib import dedup, esquema
    parser = _ap.ArgumentParser()
    sub = parser.add_subparsers()
    dedup.registrar(sub)
    args = parser.parse_args(["dedup"])
    assert args.por is None
    with pytest.raises(SystemExit):
        parser.parse_args(["dedup", "--help"])
    assert f"ex.: {esquema.PAPEL_HUMANO_PADRAO}" in " ".join(capsys.readouterr().out.split())


# ---------------------------------------------------------------------------
# v1.3: avisos de busca substituída agregados, contagem de candidatos, contrato e permissões
# ---------------------------------------------------------------------------
def _substituir_busca_com_equivalentes(raiz, capsys, decidir=()):
    """B01 com 4 estudos, dedup, decisões de triagem opcionais, B01 substituída por B09 com os mesmos DOIs, dedup."""
    from rslib import esquema
    from rslib import triagem_lotes as tl
    antigos = [registro(f"B01-{k:05d}", f"Estudo número {k} sobre transferências", f"Autor{k}, Ana", 2019,
                        doi=f"10.5555/est.{k}") for k in range(1, 5)]
    escrever_registros(raiz, antigos)
    assert rodar(raiz) == 0
    if decidir:
        tl.registrar_decisoes(raiz, [tl.nova_decisao(i, "ta", "ta_v1", "A", "ia_subagente", "incluir",
                                                     trecho="x", justificativa="x") for i in decidir])
    capsys.readouterr()
    desativar_busca(raiz, "B01")
    novos = [dict(r, id_registro=r["id_registro"].replace("B01", "B09"), busca_id="B09", fonte="openalex")
             for r in antigos]
    escrever_registros(raiz, antigos + novos)
    assert rodar(raiz) == 0
    saida = capsys.readouterr().out
    ev = [e for e in ler_jsonl(raiz / esquema.ARQ_LOG) if e["evento"] == "dedup_executado"][-1]
    return saida, json.loads(saida.strip().splitlines()[-1]), ev["dados"]["avisos"]


def test_substituicao_sem_decisoes_de_triagem_gera_um_aviso_agregado(projeto_vazio, capsys):
    saida, resumo, avisos = _substituir_busca_com_equivalentes(projeto_vazio, capsys)
    agregados = [a for a in avisos if "nada a herdar" in a]
    assert len(agregados) == 1 and "4 clusters novos" in agregados[0] and "RS0005~RS0001" in agregados[0], avisos
    assert not [a for a in avisos if "com decisão de triagem" in a]
    assert resumo["avisos"] == len(avisos) and saida.count("aviso:") == len(avisos)


def test_substituicao_com_decisao_de_triagem_avisa_o_cluster(projeto_vazio, capsys):
    _, _, avisos = _substituir_busca_com_equivalentes(projeto_vazio, capsys, decidir=["RS0002"])
    individuais = [a for a in avisos if "com decisão de triagem" in a]
    agregados = [a for a in avisos if "nada a herdar" in a]
    assert len(individuais) == 1 and "RS0002" in individuais[0] and "trie o novo id" in individuais[0], avisos
    assert len(agregados) == 1 and "3 clusters novos" in agregados[0]


def test_candidatos_pendentes_ignoram_os_resolvidos_por_transitividade(projeto_plantado, capsys):
    from rslib import dedup, esquema
    pares_sint = [
        {"decisao": "candidato", "motivo": "fuzzy"},
        {"decisao": "candidato", "motivo": f"fuzzy;{esquema.MARCA_RESOLVIDO_TRANSITIVAMENTE}"},
        {"decisao": "auto", "motivo": ""},
    ]
    assert dedup.candidatos_pendentes(pares_sint) == [pares_sint[0]]
    assert rodar(projeto_plantado) == 0
    resumo = ultimo_resumo(capsys)
    total_candidatos = resumo["pares_por_decisao"].get("candidato", 0)
    assert resumo["candidatos_resolvidos_transitivamente"] == total_candidatos - resumo["candidatos_pendentes"]
    assert dedup.contar_candidatos_pendentes(projeto_plantado) == resumo["candidatos_pendentes"]
    ev = [e for e in ler_jsonl(projeto_plantado / esquema.ARQ_LOG) if e["evento"] == "dedup_executado"][-1]
    assert ev["dados"]["candidatos_resolvidos_transitivamente"] == resumo["candidatos_resolvidos_transitivamente"]


def test_decisao_ligado_promovida_ao_esquema():
    from rslib import dedup, esquema
    assert esquema.DECISAO_LIGADO == "ligado" and esquema.DECISOES_DEDUP[-1] == "ligado"
    assert esquema.DECISOES_DEDUP[:4] == ["auto", "candidato", "confirmado", "rejeitado"]
    assert dedup.DECISAO_LIGADO is esquema.DECISAO_LIGADO and dedup.DECISOES_PARES == esquema.DECISOES_DEDUP
    assert dedup.MOTIVO_VERSAO_LIGADA == esquema.MOTIVO_VERSAO_LIGADA == "preprint_publicado"


@pytest.mark.skipif(__import__("os").name == "nt", reason="permissões POSIX")
def test_regressao_saidas_do_dedup_com_permissao_de_arquivo_comum(projeto_vazio):
    import stat
    from rslib import esquema, estado
    # sem par de versão: registros_unicos.csv é gravado só pelo dedup (a ligação de relatos usa outro escritor)
    escrever_registros(projeto_vazio, [
        registro("B01-00001", "Cash transfers and school attendance", "Silva, Ana", 2019, doi="10.5555/c1"),
        registro("B02-00001", "Cash transfers and school attendance", "Silva, A.", 2019, doi="10.5555/c1", fonte="scopus"),
        registro("B02-00002", "Participatory budgeting and infant mortality", "Costa, Lia", 2017, fonte="scopus")])
    assert rodar(projeto_vazio) == 0
    for rel in (esquema.ARQ_UNICOS, esquema.ARQ_DEDUP_PARES):
        assert stat.S_IMODE((projeto_vazio / rel).stat().st_mode) == estado.modo_arquivo_padrao(), rel


# ---------------------------------------------------------------------------
# Ids absorvidos depois da triagem (v1.4)
# ---------------------------------------------------------------------------
def _dedup_com_aposentados(raiz, aposentados):
    from rslib import estado
    estado.registrar_evento(raiz, "dedup_executado", "05_organizacao", "script", "dedup",
                            dados={"ids_rs_aposentados": aposentados})


def test_mapa_absorvidos_segue_cadeia_e_filtra_destino(projeto_vazio):
    from rslib import dedup
    raiz = projeto_vazio
    assert dedup.mapa_absorvidos(raiz) == {} and dedup.chaves_absorvidas(raiz) == {}
    _dedup_com_aposentados(raiz, {"RS0005": {"absorvido_por": "RS0003", "chave": "Dias2016"}})
    _dedup_com_aposentados(raiz, {"RS0003": {"absorvido_por": "RS0002", "chave": "Lima2021"},
                                  "RS0009": {"absorvido_por": "", "chave": ""}})
    assert dedup.mapa_absorvidos(raiz) == {"RS0005": "RS0002", "RS0003": "RS0002", "RS0009": ""}
    assert dedup.mapa_absorvidos(raiz, {"RS0001"}) == {"RS0005": "", "RS0003": "", "RS0009": ""}
    assert dedup.chaves_absorvidas(raiz, {"RS0002"}) == {"Dias2016": "RS0002", "Lima2021": "RS0002"}
