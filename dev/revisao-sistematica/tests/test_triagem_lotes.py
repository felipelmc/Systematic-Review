"""Testes da triagem por lotes (preparar, mesclar, consolidar, override) e do ledger de decisões.

Os dados são sintéticos e gerados aqui mesmo: registros_unicos.csv com N registros, um
arquivo de critérios C1–C3 e respostas de subagente simuladas a partir de um gabarito.
"""

import argparse
import csv
import json

import pytest

from conftest import SKILL, ler_jsonl

from rslib import esquema, estado
from rslib import triagem_lotes as tl

CRITERIOS = """# Critérios de triagem de títulos e resumos — v2

Aplique em sequência.

- C1 — População: municípios ou estados brasileiros.
- C2 — Intervenção: o programa de parcelamento é analisado empiricamente (não só mencionado).
- C3 — Desfecho: arrecadação, adimplência ou receita tributária.
"""


# ---------------------------------------------------------------------------
# Auxiliares (também usados por test_validacao.py)
# ---------------------------------------------------------------------------
def criar_registros(raiz, n=12, sem_resumo=()):
    linhas = []
    for k in range(1, n + 1):
        id_rs = f"RS{k:04d}"
        linha = {c: "" for c in esquema.COLUNAS_UNICOS}
        linha.update({
            "id_rs": id_rs, "id_estudo": id_rs, "chave": f"Autor{2000 + k}", "ids_registro": f"B01-{k:05d}",
            "fontes": "wos", "n_fontes": "1", "tipo_duplicata": "unico",
            "titulo": f"Programa de parcelamento numero {k} e arrecadação municipal no Brasil",
            "resumo": "" if k in sem_resumo else (
                f"Estimamos o efeito do programa {k} sobre a arrecadação dos municípios brasileiros "
                "com dados em painel entre 2005 e 2019."),
            "autores": "Silva, Ana", "ano": "2020", "tipo_publicacao": "artigo", "idioma": "pt",
            "veiculo": "Revista de Teste", "resumo_truncado": "0",
        })
        linhas.append(linha)
    caminho = raiz / esquema.ARQ_UNICOS
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=esquema.COLUNAS_UNICOS)
        w.writeheader()
        w.writerows(linhas)
    return [l["id_rs"] for l in linhas]


def criar_criterios(raiz, texto=CRITERIOS, nome="ta_v2.md"):
    caminho = raiz / "02-triagem" / "prompts" / nome
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
    return f"02-triagem/prompts/{nome}"


def parser():
    p = argparse.ArgumentParser(prog="rs.py")
    p.add_argument("--dir", default=None)
    sub = p.add_subparsers(dest="comando")
    tl.registrar(sub)
    from rslib import validacao
    validacao.registrar(sub)
    return p


def rodar(capsys, raiz, *argv):
    """Executa um subcomando como o dispatcher e devolve (código, resumo JSON da última linha)."""
    args = parser().parse_args(["--dir", str(raiz), *argv])
    codigo = args.func(args)
    saida = capsys.readouterr().out.strip().splitlines()
    return codigo, json.loads(saida[-1])


def responder_lote(raiz, caminho_lote, gabarito, criterio="C2", mutar=None, texto_bruto=None):
    """Escreve a resposta de um "subagente" que segue o gabarito {id_rs: decisão}."""
    with open(caminho_lote, encoding="utf-8") as f:
        lote = json.load(f)
    resposta = {k: lote[k] for k in ("lote_id", "rodada", "revisor", "criterios_sha")}
    resposta["decisoes"] = []
    for r in lote["registros"]:
        d = gabarito.get(r["id_rs"], "incluir")
        if r["sem_resumo"] and d == "excluir":
            d = "incerto"
        resposta["decisoes"].append({
            "id_rs": r["id_rs"], "decisao": d,
            "criterio_falhou": criterio if d == "excluir" else None,
            "justificativa": f"Decisão de teste: {d}.",
            "trecho": " ".join(r["titulo"].split()[:4]) if d != "incerto" else None,
        })
    if mutar:
        mutar(resposta)
    destino = raiz / lote["arquivo_resposta"]
    destino.write_text(texto_bruto if texto_bruto is not None else json.dumps(resposta, ensure_ascii=False),
                       encoding="utf-8")
    return resposta


def responder_todos(raiz, rodada, revisor, gabarito, **kw):
    manifesto = tl.ler_manifesto(raiz, rodada, revisor)
    for lote in manifesto["lotes"]:
        if lote["status"] != "mesclado":
            responder_lote(raiz, raiz / lote["arquivo"], gabarito, **kw)


def eventos(raiz, nome):
    return [e for e in ler_jsonl(raiz / esquema.ARQ_LOG) if e["evento"] == nome]


def triar_rodada(capsys, raiz, rodada, gabaritos, tamanho=5, criterios=None):
    """Prepara e mescla uma rodada completa com um gabarito por revisor."""
    criterios = criterios or criar_criterios(raiz)
    for revisor, gabarito in gabaritos.items():
        codigo, _ = rodar(capsys, raiz, "triagem", "preparar", "--rodada", rodada, "--revisor", revisor,
                          "--criterios", criterios, "--tamanho", str(tamanho))
        assert codigo == 0
        responder_todos(raiz, rodada, revisor, gabarito)
        codigo, res = rodar(capsys, raiz, "triagem", "mesclar", "--rodada", rodada, "--revisor", revisor,
                            "--modelo", "modelo-teste")
        assert codigo == 0, res
    return criterios


# ---------------------------------------------------------------------------
# preparar
# ---------------------------------------------------------------------------
def test_preparar_cria_lotes_embaralhados_e_idempotente(projeto_vazio, capsys):
    raiz = projeto_vazio
    ids = criar_registros(raiz, n=12)
    criterios = criar_criterios(raiz)
    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "A",
                        "--criterios", criterios, "--tamanho", "5")
    assert codigo == 0 and res["n_lotes"] == 3 and res["registros_novos"] == 12
    assert len(res["lotes_pendentes"]) == 3
    man_a = tl.ler_manifesto(raiz, "ta_v2", "A")
    assert sorted(i for l in man_a["lotes"] for i in l["ids"]) == ids
    assert [len(l["ids"]) for l in man_a["lotes"]] == [5, 5, 2]
    lote = json.loads((raiz / man_a["lotes"][0]["arquivo"]).read_text(encoding="utf-8"))
    assert lote["ids_criterios"] == ["C1", "C2", "C3"]
    assert "autores" not in lote["registros"][0] and "chave" not in lote["registros"][0]

    rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "B",
          "--criterios", criterios, "--tamanho", "5")
    man_b = tl.ler_manifesto(raiz, "ta_v2", "B")
    ordem_a = [i for l in man_a["lotes"] for i in l["ids"]]
    ordem_b = [i for l in man_b["lotes"] for i in l["ids"]]
    assert ordem_a != ordem_b, "cada revisor deve ter embaralhamento próprio"

    n_eventos = len(eventos(raiz, "lote_preparado"))
    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "A",
                        "--criterios", criterios, "--tamanho", "5")
    assert codigo == 0 and res["reexecucao"] and res["lotes_novos"] == 0
    assert len(eventos(raiz, "lote_preparado")) == n_eventos
    assert tl.ler_manifesto(raiz, "ta_v2", "A") == man_a
    est = estado.carregar_estado(raiz)
    assert est["versoes_ativas"]["criterios_ta"] == criterios
    assert est["etapas"]["06_triagem_ta"]["status"] == "em_andamento"


def test_preparar_append_de_registros_novos_e_funil(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=6)
    (raiz / esquema.ARQ_FILTRO_FORMAL).write_text(
        "id_rs,filtro,resultado,detalhe\nRS0002,ano,exclui,1990\nRS0003,idioma,etiqueta,fr\n", encoding="utf-8")
    criterios = criar_criterios(raiz)
    rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "A", "--criterios", criterios)
    man = tl.ler_manifesto(raiz, "ta_v2", "A")
    alocados = {i for l in man["lotes"] for i in l["ids"]}
    assert "RS0002" not in alocados and "RS0003" in alocados and len(alocados) == 5
    criar_registros(raiz, n=9)  # bola de neve trouxe 3 registros novos
    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "A",
                        "--criterios", criterios)
    man2 = tl.ler_manifesto(raiz, "ta_v2", "A")
    assert codigo == 0 and res["lotes_novos"] == 1 and res["registros_novos"] == 3
    assert man2["lotes"][0] == man["lotes"][0], "lotes existentes não mudam"
    assert set(man2["lotes"][1]["ids"]) == {"RS0007", "RS0008", "RS0009"}


def test_preparar_recusa_criterios_alterados_na_rodada(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=4)
    criterios = criar_criterios(raiz)
    rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "A", "--criterios", criterios)
    criar_criterios(raiz, CRITERIOS + "\n- C4 — novo critério\n")
    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "B",
                        "--criterios", criterios)
    assert codigo == 1 and not res["ok"] and "rodada nova" in res["erro"]


def test_preparar_exige_ids_de_criterio(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=3)
    criterios = criar_criterios(raiz, "Inclua estudos relevantes.\n", nome="sem_ids.md")
    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v1", "--revisor", "A",
                        "--criterios", criterios)
    assert codigo == 1 and "C1" in res["erro"]


def test_ids_criterios_iguais_ao_modo_api():
    texto = "# Critérios (CRITÉRIOS v2)\n- C1: população\n**C2** — desenho\n| C3A | período |\nRemete ao C1 de novo.\n"
    assert tl.ids_criterios(texto) == ["C1", "C2", "C3A"]
    outra_letra = "# Critérios\n- I1: inclui estudantes\n1. E2) exclui revisões\nFrase com X9 no meio não conta.\n"
    assert tl.ids_criterios(outra_letra) == ["I1", "E2"]
    assert tl.ids_criterios("sem identificadores") == []
    try:
        from rslib import triagem_api
    except ImportError:
        return
    for t in (texto, outra_letra, CRITERIOS):
        assert tl.ids_criterios(t) == triagem_api.extrair_ids_criterios(t)


def test_preparar_com_arquivo_de_ids(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=8)
    criterios = criar_criterios(raiz)
    (raiz / "ids.csv").write_text("id_rs\nRS0003\nRS0005\n", encoding="utf-8")
    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "piloto", "--revisor", "A",
                        "--criterios", criterios, "--ids", "ids.csv")
    assert codigo == 0 and res["n_registros"] == 2
    (raiz / "ids_ruins.txt").write_text("RS0003\nRS9999\n", encoding="utf-8")
    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "piloto2", "--revisor", "A",
                        "--criterios", criterios, "--ids", "ids_ruins.txt")
    assert codigo == 1 and "RS9999" in res["erro"]


# ---------------------------------------------------------------------------
# mesclar
# ---------------------------------------------------------------------------
def test_mesclar_valido_grava_ledger_e_e_idempotente(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=7, sem_resumo={7})
    criterios = criar_criterios(raiz)
    rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "A", "--criterios", criterios,
          "--tamanho", "4")
    gabarito = {"RS0001": "excluir", "RS0002": "incerto", "RS0007": "incerto"}
    responder_todos(raiz, "ta_v2", "A", gabarito)
    codigo, res = rodar(capsys, raiz, "triagem", "mesclar", "--rodada", "ta_v2", "--revisor", "A",
                        "--modelo", "modelo-x")
    assert codigo == 0 and res["ok"] and len(res["mesclados"]) == 2 and not res["lotes_pendentes"]
    linhas = ler_jsonl(raiz / esquema.ARQ_DECISOES)
    assert len(linhas) == 7
    por_id = {l["id_rs"]: l for l in linhas}
    assert por_id["RS0001"]["decisao"] == "excluir" and por_id["RS0001"]["criterio_falhou"] == "C2"
    assert por_id["RS0003"]["tipo_ator"] == "ia_subagente" and por_id["RS0003"]["modelo"] == "modelo-x"
    assert por_id["RS0003"]["prompt_sha"] == estado.sha256_texto(CRITERIOS)
    assert all(list(l.keys()) == esquema.CAMPOS_DECISAO for l in linhas)
    assert len(eventos(raiz, "lote_mesclado")) == 2

    codigo, res = rodar(capsys, raiz, "triagem", "mesclar", "--rodada", "ta_v2", "--revisor", "A")
    assert codigo == 0 and res["reexecucao"] and res["ja_mesclados"] == 2
    assert len(ler_jsonl(raiz / esquema.ARQ_DECISOES)) == 7
    assert len(eventos(raiz, "lote_mesclado")) == 2


def test_decisoes_validam_contra_schema(projeto_vazio, capsys):
    jsonschema = pytest.importorskip("jsonschema")
    raiz = projeto_vazio
    criar_registros(raiz, n=4)
    triar_rodada(capsys, raiz, "ta_v2", {"A": {"RS0001": "excluir"}})
    schema = json.loads((SKILL / "assets/schemas/decisao.schema.json").read_text(encoding="utf-8"))
    for linha in ler_jsonl(raiz / esquema.ARQ_DECISOES):
        jsonschema.validate(linha, schema)
    ev_schema = json.loads((SKILL / "assets/schemas/evento.schema.json").read_text(encoding="utf-8"))
    for ev in ler_jsonl(raiz / esquema.ARQ_LOG):
        jsonschema.validate(ev, ev_schema)


def _primeiro_outro(resp, campo, valor):
    resp["decisoes"][0][campo] = valor


CASOS_INVALIDOS = {
    "id_faltando": (lambda r: r["decisoes"].pop(), "IDs faltando"),
    "id_extra": (lambda r: r["decisoes"].append({**r["decisoes"][0], "id_rs": "RS0999"}), "ID extra"),
    "id_duplicado": (lambda r: r["decisoes"].append(dict(r["decisoes"][0])), "IDs duplicados"),
    "enum_invalido": (lambda r: _primeiro_outro(r, "decisao", "Include"), "decisao inválida"),
    "criterio_inexistente": (lambda r: r["decisoes"][1].update(decisao="excluir", criterio_falhou="C9"),
                             "não existe no arquivo de critérios"),
    "exclusao_sem_criterio": (lambda r: r["decisoes"][1].update(decisao="excluir", criterio_falhou=None),
                              "exclusão sem criterio_falhou"),
    "trecho_inventado": (lambda r: _primeiro_outro(r, "trecho", "ensaio clínico randomizado em hospitais"),
                         "trecho não encontrado"),
    "trecho_longo": (lambda r: _primeiro_outro(r, "trecho", " ".join(["arrecadação"] * 30)), "mais de 25 palavras"),
    "campo_extra": (lambda r: r["decisoes"][0].update(confianca=0.9), "campos não permitidos"),
    "sha_errado": (lambda r: r.update(criterios_sha="0" * 64), "criterios_sha"),
    "revisor_errado": (lambda r: r.update(revisor="B"), "revisor"),
    "sem_decisoes": (lambda r: r.update(decisoes=[]), "lista não vazia"),
    "justificativa_longa": (lambda r: _primeiro_outro(r, "justificativa", "x" * 401), "máx. 400"),
}


@pytest.mark.parametrize("caso", sorted(CASOS_INVALIDOS))
def test_mesclar_rejeita_resposta_invalida(projeto_vazio, capsys, caso):
    raiz = projeto_vazio
    criar_registros(raiz, n=3)
    criterios = criar_criterios(raiz)
    rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "A", "--criterios", criterios)
    mutar, trecho_erro = CASOS_INVALIDOS[caso]
    responder_todos(raiz, "ta_v2", "A", {}, mutar=mutar)
    codigo, res = rodar(capsys, raiz, "triagem", "mesclar", "--rodada", "ta_v2", "--revisor", "A")
    assert codigo == 1 and not res["ok"] and len(res["rejeitados"]) == 1
    assert any(trecho_erro in e for e in res["rejeitados"][0]["erros"]), res["rejeitados"][0]["erros"]
    assert not (raiz / esquema.ARQ_DECISOES).exists(), "lote inválido não grava nada"
    pasta = raiz / "02-triagem/lotes/ta_v2/A"
    assert not (pasta / "lote_001.resposta.json").exists()
    assert len(list((pasta / "rejeitados").glob("*.resposta.*.json"))) == 1
    assert len(list((pasta / "rejeitados").glob("*.erros.*.json"))) == 1
    ev = eventos(raiz, "lote_rejeitado")
    assert len(ev) == 1 and ev[0]["dados"]["lote"] == "lote_001"
    assert tl.ler_manifesto(raiz, "ta_v2", "A")["lotes"][0]["status"] == "rejeitado"
    assert res["lotes_pendentes"], "lote rejeitado volta a ficar pendente"


def test_mesclar_json_malformado_e_reenvio(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=3)
    criterios = criar_criterios(raiz)
    rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "A", "--criterios", criterios)
    lote = raiz / tl.ler_manifesto(raiz, "ta_v2", "A")["lotes"][0]["arquivo"]
    responder_lote(raiz, lote, {}, texto_bruto='{"lote_id": "lote_001", "decisoes": [')
    codigo, res = rodar(capsys, raiz, "triagem", "mesclar", "--rodada", "ta_v2", "--revisor", "A")
    assert codigo == 1 and "JSON malformado" in res["rejeitados"][0]["erros"][0]
    responder_lote(raiz, lote, {"RS0002": "excluir"})  # novo subagente
    codigo, res = rodar(capsys, raiz, "triagem", "mesclar", "--rodada", "ta_v2", "--revisor", "A")
    assert codigo == 0 and res["mesclados"][0]["n_decisoes"] == 3
    man = tl.ler_manifesto(raiz, "ta_v2", "A")
    assert man["lotes"][0]["status"] == "mesclado" and man["lotes"][0]["rejeicoes"] == 1


def test_mesclar_recusa_excluir_sem_resumo(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=2, sem_resumo={1})
    criterios = criar_criterios(raiz)
    rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "A", "--criterios", criterios)

    def excluir_sem_resumo(resp):
        for d in resp["decisoes"]:
            if d["id_rs"] == "RS0001":
                d.update(decisao="excluir", criterio_falhou="C1", trecho="Programa de parcelamento")

    responder_todos(raiz, "ta_v2", "A", {}, mutar=excluir_sem_resumo)
    codigo, res = rodar(capsys, raiz, "triagem", "mesclar", "--rodada", "ta_v2", "--revisor", "A")
    assert codigo == 1 and any("sem resumo" in e for e in res["rejeitados"][0]["erros"])


def test_resumo_placeholder_conta_como_sem_resumo(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=2)
    caminho = raiz / esquema.ARQ_UNICOS
    caminho.write_text(caminho.read_text(encoding="utf-8").replace(
        "Estimamos o efeito do programa 2 sobre a arrecadação dos municípios brasileiros com dados em painel "
        "entre 2005 e 2019.", "[No abstract available]"), encoding="utf-8")
    assert tl.ids_sem_resumo(tl.ler_unicos(raiz)) == {"RS0002"}
    criterios = criar_criterios(raiz)
    rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "A", "--criterios", criterios)
    lote = json.loads((raiz / tl.ler_manifesto(raiz, "ta_v2", "A")["lotes"][0]["arquivo"]).read_text(encoding="utf-8"))
    reg = next(r for r in lote["registros"] if r["id_rs"] == "RS0002")
    assert reg["sem_resumo"] is True and reg["resumo"] == ""


def test_trecho_confere_normaliza_e_respeita_fronteira():
    registro = {"titulo": "Efeitos do REFIS: evidências", "resumo": "Usamos dados; a bolsa não entra."}
    assert tl.trecho_confere("efeitos do refis evidencias", registro)
    assert tl.trecho_confere("Usamos dados, a bolsa", registro)
    assert not tl.trecho_confere("ols", registro), "'ols' dentro de 'bolsa' não conta"
    assert not tl.trecho_confere("...", registro)


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------
def test_ledger_ultima_linha_vence_e_tolera_truncada(projeto_vazio):
    raiz = projeto_vazio
    tl.registrar_decisoes(raiz, [tl.nova_decisao("RS0001", "ta", "r1", "A", "ia_subagente", "excluir",
                                                 criterio_falhou="C1")])
    with open(raiz / esquema.ARQ_DECISOES, "a", encoding="utf-8") as f:
        f.write('{"id_rs": "RS0001", "etapa": "ta", "rod')  # queda no meio da escrita
    tl.registrar_decisoes(raiz, [tl.nova_decisao("RS0001", "ta", "r1", "A", "ia_subagente", "incluir")])
    linhas = tl.ler_decisoes(raiz)
    assert len(linhas) == 2
    vig = tl.decisoes_vigentes(linhas, "ta", ["r1"])
    assert len(vig) == 1 and vig[0]["decisao"] == "incluir"
    with pytest.raises(ValueError):
        tl.registrar_decisoes(raiz, [tl.nova_decisao("X1", "ta", "r1", "A", "ia_subagente", "incluir")])
    with pytest.raises(ValueError):
        tl.registrar_decisoes(raiz, [tl.nova_decisao("RS0002", "ta", "r1", "A", "robo", "incluir")])
    longa = tl.nova_decisao("RS0003", "ta", "r1", "A", "ia_api", "incluir", justificativa="y" * 900)
    assert len(longa["justificativa"]) == 600


def _d(id_rs, revisor, decisao, tipo="ia_subagente", **kw):
    return tl.nova_decisao(id_rs, "ta", "ta_v2", revisor, tipo, decisao, **kw)


def test_consolidar_decisoes_precedencia_pura():
    vig = [
        _d("RS0001", "A", "incluir"), _d("RS0001", "B", "incluir"),                       # consenso
        _d("RS0002", "A", "excluir", criterio_falhou="C1"), _d("RS0002", "B", "excluir", criterio_falhou="C3"),
        _d("RS0003", "A", "incluir"), _d("RS0003", "B", "incerto"),                       # não diverge
        _d("RS0004", "A", "incluir"), _d("RS0004", "B", "excluir", criterio_falhou="C2"),  # vai à fila
        _d("RS0005", "A", "incerto"), _d("RS0005", "B", "excluir", criterio_falhou="C2"),
        _d("RS0005", "arbitro", "excluir", criterio_falhou="C2"),                          # árbitro decide
        _d("RS0006", "A", "excluir", criterio_falhou="C1"), _d("RS0006", "B", "incluir"),
        _d("RS0006", "arbitro", "excluir", criterio_falhou="C1"),
        _d("RS0006", "humano_1", "incluir", tipo="humano", motivo_override="li o texto"),  # override vence
        _d("RS0007", "A", "excluir", criterio_falhou="C1"), _d("RS0007", "B", "excluir", criterio_falhou="C1"),
        _d("RS0008", "regra", "incerto", tipo="regra"),                                    # sem resumo (API)
        _d("RS0009", "A", "incluir"), _d("RS0009", "B", "incerto"), _d("RS0009", "arbitro", "excluir"),
    ]
    res = tl.consolidar_decisoes(vig, "consenso", sem_resumo=frozenset({"RS0007"}))
    assert (res["RS0001"]["decisao_final"], res["RS0001"]["decidido_por"]) == ("incluir", "consenso")
    assert res["RS0002"]["decisao_final"] == "excluir" and res["RS0002"]["criterio_falhou"] == "C1|C3"
    assert (res["RS0003"]["decisao_final"], res["RS0003"]["divergente"]) == ("incerto", 0)
    assert res["RS0004"]["decidido_por"] == "pendente_humano" and res["RS0004"]["na_fila"]
    assert res["RS0004"]["decisao_final"] == "incerto" and res["RS0004"]["divergente"] == 1
    assert (res["RS0005"]["decisao_final"], res["RS0005"]["decidido_por"]) == ("excluir", "arbitro")
    # Apêndice B, F: a divergência arbitrada também vai à fila humana (a decisão do árbitro vale até lá)
    assert res["RS0005"]["na_fila"] and res["RS0005"]["motivo_fila"] == "arbitrada"
    assert res["RS0004"]["motivo_fila"] == "divergencia"
    assert (res["RS0006"]["decisao_final"], res["RS0006"]["decidido_por"]) == ("incluir", "humano")
    assert res["RS0006"]["revisado_humano"] == 1 and not res["RS0006"]["na_fila"], "override tira da fila"
    assert not res["RS0009"]["na_fila"] and not res["RS0001"]["na_fila"]
    assert (res["RS0007"]["decisao_final"], res["RS0007"]["decidido_por"]) == ("incerto", "regra_sem_resumo")
    assert (res["RS0008"]["decisao_final"], res["RS0008"]["decidido_por"]) == ("incerto", "regra")
    assert (res["RS0009"]["decisao_final"], res["RS0009"]["decidido_por"]) == ("incerto", "consenso"), \
        "árbitro não exclui o que nenhum revisor excluiu"

    sem_humano = tl.consolidar_decisoes(vig, "consenso", usar_overrides=False)
    assert (sem_humano["RS0006"]["decisao_final"], sem_humano["RS0006"]["decidido_por"]) == ("excluir", "arbitro")

    liberal = tl.consolidar_decisoes(vig, "liberal")
    assert (liberal["RS0004"]["decisao_final"], liberal["RS0004"]["decidido_por"]) == ("incluir", "regra_liberal")
    assert liberal["RS0004"]["motivo_fila"] == "divergencia_regra_liberal"
    assert (liberal["RS0005"]["decisao_final"], liberal["RS0005"]["decidido_por"]) == ("incerto", "regra_liberal")
    assert liberal["RS0006"]["decidido_por"] == "humano"


# ---------------------------------------------------------------------------
# consolidar, árbitro, override
# ---------------------------------------------------------------------------
def test_fluxo_completo_com_arbitro_fila_e_override(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=10, sem_resumo={10})
    gab_a = {"RS0001": "excluir", "RS0002": "excluir", "RS0003": "incluir", "RS0004": "excluir", "RS0010": "excluir"}
    gab_b = {"RS0001": "excluir", "RS0002": "incluir", "RS0003": "excluir", "RS0004": "incluir",
             "RS0005": "incerto", "RS0010": "excluir"}
    criterios = triar_rodada(capsys, raiz, "ta_v2", {"A": gab_a, "B": gab_b}, tamanho=4)

    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "A",
                        "--criterios", criterios, "--apenas-divergentes")
    assert codigo == 1 and "arbitro" in res["erro"]
    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "arbitro",
                        "--criterios", criterios)
    assert codigo == 1 and "divergências" in res["erro"]
    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "arbitro",
                        "--criterios", criterios, "--apenas-divergentes")
    assert codigo == 0 and res["n_registros"] == 3 and res["agente_prompt"].endswith("arbitro-cego.md")
    man = tl.ler_manifesto(raiz, "ta_v2", "arbitro")
    lote = json.loads((raiz / man["lotes"][0]["arquivo"]).read_text(encoding="utf-8"))
    assert lote["papel"] == "arbitro"
    texto_lote = json.dumps(lote)
    assert "modelo-teste" not in texto_lote and '"revisor": "A"' not in texto_lote
    for reg in lote["registros"]:
        assert [p["rotulo"] for p in reg["pareceres"]] == ["Revisor 1", "Revisor 2"]
        assert set(reg["pareceres"][0]) == {"rotulo", "decisao", "criterio_falhou", "justificativa", "trecho"}
    # árbitro decide só RS0002 (exclui) e RS0003 (inclui); RS0004 fica sem árbitro para ir à fila
    responder_lote(raiz, raiz / man["lotes"][0]["arquivo"], {"RS0002": "excluir", "RS0003": "incluir",
                                                           "RS0004": "incerto"})
    codigo, _ = rodar(capsys, raiz, "triagem", "mesclar", "--rodada", "ta_v2", "--revisor", "arbitro")
    assert codigo == 0
    # remove a decisão do árbitro para RS0004 simulando um árbitro que não cobriu o registro
    linhas = [l for l in ler_jsonl(raiz / esquema.ARQ_DECISOES)
              if not (l["id_rs"] == "RS0004" and l["revisor"] == "arbitro")]
    (raiz / esquema.ARQ_DECISOES).write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in linhas),
                                             encoding="utf-8")

    est = estado.carregar_estado(raiz)
    est["modo"]["autonomia"] = "autopiloto"
    estado.salvar_estado(raiz, est)
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    # regressão: as 2 divergências arbitradas (RS0002, RS0003) também entram na fila (Apêndice B, F)
    assert codigo == 0 and res["n"] == 10 and res["fila_humana"] == 3 and res["pendencia"]
    assert res["arbitradas_na_fila"] == 2 and res["motivos_fila"] == {"arbitrada": 2, "divergencia": 1}
    assert res["rodada_ativa"] == "ta_v2"
    assert estado.carregar_estado(raiz)["versoes_ativas"][esquema.VERSAO_ATIVA_RODADA_TA] == "ta_v2"
    with open(raiz / esquema.ARQ_TRIAGEM_TA_FINAL, encoding="utf-8") as f:
        final = {l["id_rs"]: l for l in csv.DictReader(f)}
    with open(raiz / esquema.ARQ_TRIAGEM_TA_FINAL, encoding="utf-8") as f:
        assert f.readline().strip().split(",") == esquema.COLUNAS_TRIAGEM_FINAL
    assert final["RS0001"]["decisao_final"] == "excluir" and final["RS0001"]["decidido_por"] == "consenso"
    assert final["RS0002"]["decidido_por"] == "arbitro" and final["RS0002"]["decisao_final"] == "excluir"
    assert final["RS0002"]["revisado_humano"] == "0"
    assert final["RS0003"]["decidido_por"] == "arbitro" and final["RS0003"]["decisao_final"] == "incluir"
    assert final["RS0004"]["decidido_por"] == "pendente_humano" and final["RS0004"]["divergente"] == "1"
    assert final["RS0005"]["decisao_final"] == "incerto" and final["RS0005"]["divergente"] == "0"
    assert final["RS0010"]["decisao_final"] == "incerto"
    pend = estado.pendencias_abertas(estado.carregar_estado(raiz))
    assert len(pend) == 1 and pend[0]["tipo"] == "fila_humana_triagem" and pend[0]["n"] == 3
    assert "arbitradas" in pend[0]["descricao"]

    # reexecução não duplica evento nem pendência
    n_ev = len(eventos(raiz, "triagem_consolidada"))
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    assert res["reexecucao"] and len(eventos(raiz, "triagem_consolidada")) == n_ev
    assert len(estado.pendencias_abertas(estado.carregar_estado(raiz))) == 1

    # humano preenche a divergência sem árbitro; reconsolidar antes do override preserva o preenchimento
    fila = raiz / "02-triagem/fila_humana_ta_v2.csv"

    def ler_fila():
        with open(fila, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def gravar_fila(linhas):
        with open(fila, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=tl.COLUNAS_FILA_HUMANA)
            w.writeheader()
            w.writerows(linhas)

    linhas_fila = {l["id_rs"]: l for l in ler_fila()}
    assert sorted(linhas_fila) == ["RS0002", "RS0003", "RS0004"]
    assert {i: l["motivo_fila"] for i, l in linhas_fila.items()} == {
        "RS0002": "arbitrada", "RS0003": "arbitrada", "RS0004": "divergencia"}
    assert "A=excluir" in linhas_fila["RS0004"]["pareceres"] and "arbitro=excluir" in linhas_fila["RS0002"]["pareceres"]
    linhas_fila["RS0004"].update(decisao_humana="incluir", motivo_humano="programa é o tratamento")
    gravar_fila(list(linhas_fila.values()))
    rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    assert {l["id_rs"]: l["decisao_humana"] for l in ler_fila()}["RS0004"] == "incluir"

    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", "02-triagem/fila_humana_ta_v2.csv")
    assert codigo == 0 and res["registrados"] == 1
    ov = [l for l in ler_jsonl(raiz / esquema.ARQ_DECISOES) if l.get("motivo_override")]
    assert ov[0]["override_de"] == "incerto:pendente_humano" and ov[0]["tipo_ator"] == "humano"
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", "02-triagem/fila_humana_ta_v2.csv")
    assert res["reexecucao"] and res["ja_registrados"] == 1
    assert len(eventos(raiz, "decisao_override")) == 1

    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    assert res["fila_humana"] == 2 and res["decidido_por"]["humano"] == 1 and res["arbitradas_na_fila"] == 2
    pend = estado.pendencias_abertas(estado.carregar_estado(raiz))
    assert len(pend) == 1 and pend[0]["n"] == 2, "arbitradas seguem pendentes de conferência humana"

    # conferência humana das arbitradas: confirma uma e corrige a outra
    linhas_fila = {l["id_rs"]: l for l in ler_fila()}
    assert sorted(linhas_fila) == ["RS0002", "RS0003"]
    linhas_fila["RS0002"].update(decisao_humana="excluir", criterio_humano="C2", motivo_humano="árbitro confirmado")
    linhas_fila["RS0003"].update(decisao_humana="excluir", criterio_humano="C1", motivo_humano="fora da população")
    gravar_fila(list(linhas_fila.values()))
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", "02-triagem/fila_humana_ta_v2.csv")
    assert codigo == 0 and res["registrados"] == 2
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    assert res["fila_humana"] == 0 and res["decidido_por"]["humano"] == 3
    assert not estado.pendencias_abertas(estado.carregar_estado(raiz)), "fila resolvida fecha a pendência"

    # override avulso sem --rodada vai para a rodada ativa
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--id", "RS0002", "--decisao", "incluir",
                        "--motivo", "texto completo mostra avaliação do programa")
    assert codigo == 0 and res["rodadas"] == ["ta_v2"]
    rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    with open(raiz / esquema.ARQ_TRIAGEM_TA_FINAL, encoding="utf-8") as f:
        final = {l["id_rs"]: l for l in csv.DictReader(f)}
    assert final["RS0002"]["decisao_final"] == "incluir" and final["RS0002"]["revisado_humano"] == "1"
    assert final["RS0003"]["decisao_final"] == "excluir" and final["RS0003"]["decidido_por"] == "humano"


def test_consolidar_varias_rodadas_e_erros(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=4)
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    assert codigo == 1 and "nenhuma decisão" in res["erro"]
    tl.registrar_decisoes(raiz, [_d("RS0001", "A", "excluir", criterio_falhou="C1"),
                                 _d("RS0001", "B", "excluir", criterio_falhou="C1"),
                                 _d("RS0002", "A", "incluir")])
    sn = [tl.nova_decisao("RS0003", "ta", "ta_v2_sn1", r, "ia_subagente", "incluir") for r in ("A", "B")]
    tl.registrar_decisoes(raiz, sn)
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2", "--rodada", "ta_v2_sn1")
    assert codigo == 0 and res["n"] == 3 and res["decidido_por"]["revisor_unico"] == 1
    assert any("só um revisor" in a for a in res["avisos"]) and res["sem_decisao"] == 1
    assert (raiz / "02-triagem/fila_humana_ta_v2+ta_v2_sn1.csv").exists()
    (raiz / esquema.ARQ_FILTRO_FORMAL).write_text("id_rs,filtro,resultado,detalhe\nRS0002,ano,exclui,1990\n",
                                                 encoding="utf-8")
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2", "--rodada", "ta_v2_sn1")
    assert res["n"] == 2 and any("funil formal" in a for a in res["avisos"])


def test_override_valida_entrada(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=2)
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--id", "RS0001", "--decisao", "incluir",
                        "--motivo", "x")
    assert codigo == 1 and "--rodada" in res["erro"]
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--id", "RS0099", "--decisao", "incluir",
                        "--motivo", "x", "--rodada", "ta_v2")
    assert codigo == 1 and "não existe" in res["erro"]


def test_dispatcher_registra_triagem_e_validar():
    import rs

    p = rs.construir_parser()
    args = p.parse_args(["triagem", "consolidar", "--rodada", "ta_v2"])
    assert args.func and args.regra == "consenso"
    args = p.parse_args(["validar", "calcular", "--planilha", "x.xlsx"])
    assert args.func
    assert p.parse_args(["triagem"]).func(None) == 1  # sem subcomando: ajuda e código 1


@pytest.mark.parametrize("argv", [
    ["triagem"], ["triagem", "preparar"], ["triagem", "mesclar"], ["triagem", "consolidar"], ["triagem", "override"],
    ["triagem", "fila"], ["validar"], ["validar", "amostrar"], ["validar", "elusao"], ["validar", "calcular"], ["validar", "estabilidade"],
])
def test_ajuda_de_todos_os_subcomandos_renderiza(argv, capsys):
    with pytest.raises(SystemExit) as saida:
        parser().parse_args([*argv, "--help"])
    assert saida.value.code == 0 and "usage" in capsys.readouterr().out


def test_trava_compartilhada_do_ledger(projeto_vazio):
    tl.registrar_decisoes(projeto_vazio, [_d("RS0001", "A", "incluir")])
    assert (projeto_vazio / "dados/.decisoes.lock").exists()


# ---------------------------------------------------------------------------
# Rodada ativa, rodadas de estabilidade e aguardando (v1.1)
# ---------------------------------------------------------------------------
def _dup(id_rs, rodada, decisao, revisores=("A", "B"), **kw):
    return [tl.nova_decisao(id_rs, "ta", rodada, r, "ia_subagente", decisao, **kw) for r in revisores]


def test_consolidar_grava_rodada_ativa_e_recusa_estabilidade(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=4)
    tl.registrar_decisoes(raiz, _dup("RS0001", "ta_v2", "incluir") + _dup("RS0002", "ta_v2", "incluir")
                          + _dup("RS0003", "ta_v2_sn1", "incluir") + _dup("RS0001", "ta_v2_estab", "incluir"))
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2", "--rodada", "ta_v2_sn1")
    assert codigo == 0 and res["rodada_ativa"] == "ta_v2_sn1", "a rodada de maior prioridade é a última"
    est = estado.carregar_estado(raiz)
    assert est["versoes_ativas"][esquema.VERSAO_ATIVA_RODADA_TA] == "ta_v2_sn1"
    assert eventos(raiz, "triagem_consolidada")[-1]["dados"]["rodada_ativa"] == "ta_v2_sn1"

    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    assert codigo == 0
    assert estado.carregar_estado(raiz)["versoes_ativas"]["rodada_ta"] == "ta_v2"

    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2_estab")
    assert codigo == 1 and "estabilidade" in res["erro"]
    # rodada de reexecução com nome livre, declarada no desenho de estabilidade
    desenho = raiz / "02-triagem/validacao/ta_v2/estabilidade_desenho.json"
    desenho.parent.mkdir(parents=True, exist_ok=True)
    desenho.write_text(json.dumps({"parametros": {"rodada": "ta_v2", "rodada_reexecucao": "reexec1"}}), encoding="utf-8")
    tl.registrar_decisoes(raiz, _dup("RS0002", "reexec1", "excluir", criterio_falhou="C1"))
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "reexec1")
    assert codigo == 1 and "estabilidade" in res["erro"]
    assert estado.carregar_estado(raiz)["versoes_ativas"]["rodada_ta"] == "ta_v2"


def test_preparar_nao_sobrescreve_rodada_ativa(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=4)
    criterios = criar_criterios(raiz)
    rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "A", "--criterios", criterios)
    assert estado.carregar_estado(raiz)["versoes_ativas"]["rodada_ta"] == "ta_v2", "preenche a lacuna"
    rodar(capsys, raiz, "triagem", "preparar", "--rodada", "calib", "--revisor", "A", "--criterios",
          criar_criterios(raiz, CRITERIOS, nome="calib.md"))
    assert estado.carregar_estado(raiz)["versoes_ativas"]["rodada_ta"] == "ta_v2", "preparar não troca a ativa"


def test_override_sem_rodada_usa_ativa_e_recusa_estab(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=5)
    tl.registrar_decisoes(raiz, _dup("RS0001", "ta_v2", "incluir") + _dup("RS0002", "ta_v2", "excluir",
                                                                           criterio_falhou="C1")
                          + _dup("RS0004", "ta_v2_sn1", "incluir"))
    assert rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2", "--rodada", "ta_v2_sn1")[0] == 0
    # depois da consolidação o ledger ganha uma reexecução de estabilidade e uma rodada de desenvolvimento
    tl.registrar_decisoes(raiz, _dup("RS0001", "ta_v2_estab", "excluir", criterio_falhou="C1")
                          + _dup("RS0003", "ta_v3_dev", "incluir"))

    # rodadas escritas direto no ledger não têm lotes nem criterios.md: sem --criterios não há como conferir
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--id", "RS0001", "--decisao", "excluir",
                        "--criterio", "C2", "--motivo", "não avalia o programa")
    assert codigo == 1 and "--criterios" in res["erro"]
    criterios = criar_criterios(raiz)
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--id", "RS0001", "--decisao", "excluir",
                        "--criterio", "C2", "--motivo", "não avalia o programa", "--criterios", criterios)
    assert codigo == 0 and res["rodadas"] == ["ta_v2"], "vai à última rodada consolidada em que o ID tem decisão"
    assert "--rodada ta_v2 --rodada ta_v2_sn1" in res["proxima_acao"]
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--id", "RS0004", "--decisao", "excluir",
                        "--criterio", "c3", "--motivo", "sem desfecho", "--criterios", criterios)
    assert codigo == 0 and res["rodadas"] == ["ta_v2_sn1"]
    ov = {l["id_rs"]: l for l in ler_jsonl(raiz / esquema.ARQ_DECISOES) if l.get("motivo_override")}
    assert ov["RS0001"]["rodada"] == "ta_v2" and ov["RS0004"]["rodada"] == "ta_v2_sn1"
    assert ov["RS0004"]["criterio_falhou"] == "C3", "gravado com o nome canônico"
    assert ov["RS0001"]["revisor"] == esquema.PAPEL_HUMANO_PADRAO

    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2", "--rodada", "ta_v2_sn1")
    with open(raiz / esquema.ARQ_TRIAGEM_TA_FINAL, encoding="utf-8") as f:
        final = {l["id_rs"]: l for l in csv.DictReader(f)}
    assert final["RS0001"]["decidido_por"] == "humano" and final["RS0004"]["decisao_final"] == "excluir"

    codigo, res = rodar(capsys, raiz, "triagem", "override", "--id", "RS0001", "--decisao", "incluir",
                        "--motivo", "x", "--rodada", "ta_v2_estab")
    assert codigo == 1 and "estabilidade" in res["erro"]
    fila_estab = raiz / "02-triagem/fila_humana_ta_v2_estab.csv"
    fila_estab.write_text(",".join(tl.COLUNAS_FILA_HUMANA) + "\nRS0001,t,r,2020,v,divergencia,p,incluir,,x\n",
                          encoding="utf-8")
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", str(fila_estab))
    assert codigo == 1 and "estabilidade" in res["erro"]

    # sem rodada ativa no estado: a mais recente do ledger que não é de estabilidade
    est = estado.carregar_estado(raiz)
    del est["versoes_ativas"]["rodada_ta"]
    estado.salvar_estado(raiz, est)
    tl.registrar_decisoes(raiz, _dup("RS0005", "ta_v3_dev", "incluir") + _dup("RS0005", "ta_v4_estab", "incluir"))
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--id", "RS0005", "--decisao", "incluir", "--motivo", "y")
    assert codigo == 0 and res["rodadas"] == ["ta_v3_dev"]


def test_override_tc_aguardando(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=3)
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--etapa", "tc", "--id", "RS0002",
                        "--decisao", "aguardando", "--motivo", "autores não responderam")
    assert codigo == 0 and res["rodadas"] == ["tc"] and "textos elegibilidade consolidar" in res["proxima_acao"]
    linha = [l for l in ler_jsonl(raiz / esquema.ARQ_DECISOES) if l["etapa"] == "tc"][-1]
    assert (linha["decisao"], linha["tipo_ator"], linha["rodada"]) == ("incerto", "humano", "tc")
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--id", "RS0002", "--decisao", "aguardando",
                        "--motivo", "x", "--rodada", "ta_v2")
    assert codigo == 1 and "--etapa tc" in res["erro"]
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--etapa", "tc", "--id", "RS0002", "--decisao",
                        "aguardando", "--criterio", "C1", "--motivo", "x")
    assert codigo == 1 and "critério" in res["erro"]


def test_consolidar_tc_avisa_que_o_prisma_le_textos(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=2)
    tl.registrar_decisoes(raiz, [tl.nova_decisao("RS0001", "tc", "tc_v1", r, "ia_subagente", "incluir") for r in "AB"])
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--etapa", "tc", "--rodada", "tc_v1")
    assert codigo == 0 and any("textos elegibilidade consolidar" in a for a in res["avisos"])
    assert estado.carregar_estado(raiz)["versoes_ativas"]["rodada_tc"] == "tc_v1"
    assert esquema.VERSAO_ATIVA_RODADA_TA not in estado.carregar_estado(raiz)["versoes_ativas"]


def marcar_inativos(raiz, ids):
    """Simula o dedup depois de `importar --substituir`: clusters só com registros inativos ganham a flag."""
    caminho = raiz / esquema.ARQ_UNICOS
    with open(caminho, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    for l in linhas:
        if l["id_rs"] in ids:
            l["flags"] = "|".join([f for f in l["flags"].split("|") if f] + [esquema.FLAG_BUSCA_INATIVA])
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=esquema.COLUNAS_UNICOS)
        w.writeheader()
        w.writerows(linhas)


def test_regressao_preparar_ignora_clusters_de_busca_substituida(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=8)
    marcar_inativos(raiz, {"RS0002", "RS0005"})
    criterios = criar_criterios(raiz)
    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "A",
                        "--criterios", criterios)
    alocados = {i for l in tl.ler_manifesto(raiz, "ta_v2", "A")["lotes"] for i in l["ids"]}
    assert codigo == 0 and res["n_registros"] == 6 and res["n_inativos_ignorados"] == 2
    assert not alocados & {"RS0002", "RS0005"}
    assert any(esquema.FLAG_BUSCA_INATIVA in a for a in res["avisos"])
    # também quando pedidos explicitamente em --ids
    (raiz / "ids.csv").write_text("id_rs\nRS0001\nRS0002\n", encoding="utf-8")
    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "piloto", "--revisor", "A",
                        "--criterios", criterios, "--ids", "ids.csv")
    assert codigo == 0 and res["n_registros"] == 1 and res["n_inativos_ignorados"] == 1
    assert any("RS0002" in a for a in res["avisos"])
    assert tl.ids_inativos(tl.ler_unicos(raiz)) == {"RS0002", "RS0005"}


# ---------------------------------------------------------------------------
# v1.2: fila humana lida em qualquer formato, nunca regravada com decisões pendentes;
# exclusão humana com critério validado; inativos fora da consolidação; fila do texto completo
# ---------------------------------------------------------------------------
def _projeto_com_fila(capsys, raiz):
    """Rodada ta_v2 com 2 divergências sem árbitro (RS0002, RS0003) e fila humana gerada."""
    criar_registros(raiz, n=6)
    gab_a = {"RS0001": "excluir", "RS0002": "excluir", "RS0003": "incluir"}
    gab_b = {"RS0001": "excluir", "RS0002": "incluir", "RS0003": "excluir"}
    triar_rodada(capsys, raiz, "ta_v2", {"A": gab_a, "B": gab_b}, tamanho=3)
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    assert codigo == 0 and res["fila_humana"] == 2
    return raiz / "02-triagem/fila_humana_ta_v2.csv"


def _regravar_fila(caminho, linhas, delimitador=";", encoding="utf-8-sig", colunas=None):
    """Simula o Excel pt-BR: ponto e vírgula, BOM e CRLF."""
    colunas = colunas or tl.COLUNAS_FILA_HUMANA
    with open(caminho, "w", encoding=encoding, newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas, delimiter=delimitador, lineterminator="\r\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)


def test_regressao_fila_ponto_e_virgula_nao_perde_decisoes(projeto_vazio, capsys):
    raiz = projeto_vazio
    fila = _projeto_com_fila(capsys, raiz)
    linhas = {l["id_rs"]: l for l in tl.ler_tabela_humana(fila, ["id_rs"])[1]}
    linhas["RS0002"].update(decisao_humana="Incluir", motivo_humano="avalia o programa")
    _regravar_fila(fila, list(linhas.values()))
    bruto = fila.read_bytes()

    # consolidar antes do override: lê a fila com ; e BOM e NÃO a regrava (decisão ainda não aplicada)
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    assert codigo == 0 and res["fila_preservada"] is True and res["linhas_fila_nao_aplicadas"] == ["RS0002"]
    assert "override --fila" in res["proxima_acao"]
    assert fila.read_bytes() == bruto, "a fila do usuário não pode ser regravada"

    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", "02-triagem/fila_humana_ta_v2.csv")
    assert codigo == 0 and res["registrados"] == 1 and res["por"] == esquema.PAPEL_HUMANO_PADRAO
    ov = [l for l in ler_jsonl(raiz / esquema.ARQ_DECISOES) if l.get("motivo_override")]
    assert [(l["id_rs"], l["decisao"], l["revisor"]) for l in ov] == [("RS0002", "incluir", "revisor_humano_1")]

    # aplicada a decisão, a fila volta a ser gerada pela skill (sem a linha resolvida)
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    assert codigo == 0 and res["fila_preservada"] is False and res["fila_humana"] == 1
    assert [l["id_rs"] for l in tl.ler_tabela_humana(fila, ["id_rs"])[1]] == ["RS0003"]


def test_regressao_fila_cp1252_e_xlsx(projeto_vazio, capsys):
    raiz = projeto_vazio
    fila = _projeto_com_fila(capsys, raiz)
    linhas = {l["id_rs"]: l for l in tl.ler_tabela_humana(fila, ["id_rs"])[1]}
    linhas["RS0003"].update(decisao_humana="excluir", criterio_humano="c1", motivo_humano="não é município")
    _regravar_fila(fila, list(linhas.values()), encoding="cp1252")
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", str(fila))
    assert codigo == 0 and res["registrados"] == 1 and any("cp1252" in a for a in res["avisos"])
    ov = [l for l in ler_jsonl(raiz / esquema.ARQ_DECISOES) if l.get("motivo_override")][-1]
    assert (ov["criterio_falhou"], ov["motivo_override"]) == ("C1", "não é município")

    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["ID_RS", "decisao_humana", "criterio_humano", "motivo_humano"])
    ws.append(["RS0002", "excluir", "C2", "só menciona o programa"])
    wb.save(raiz / "02-triagem/fila_humana_ta_v2.xlsx")
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", "02-triagem/fila_humana_ta_v2.xlsx")
    assert codigo == 0 and res["registrados"] == 1 and res["rodadas"] == ["ta_v2"]


def test_regressao_fila_com_cabecalho_errado_aborta_sem_tocar(projeto_vazio, capsys):
    raiz = projeto_vazio
    fila = _projeto_com_fila(capsys, raiz)
    final = raiz / esquema.ARQ_TRIAGEM_TA_FINAL
    antes_final = final.read_bytes()
    fila.write_text("id;decisao;obs\nRS0002;incluir;ok\n", encoding="utf-8")
    bruto = fila.read_bytes()
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    assert codigo == 1 and "decisao_humana" in res["erro"] and "não foi alterado" in res["erro"]
    assert fila.read_bytes() == bruto and final.read_bytes() == antes_final
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", str(fila))
    assert codigo == 1 and "id_rs" in res["erro"]
    assert not [l for l in ler_jsonl(raiz / esquema.ARQ_DECISOES) if l.get("motivo_override")]


def test_regressao_override_exclusao_exige_criterio_valido(projeto_vazio, capsys):
    raiz = projeto_vazio
    fila = _projeto_com_fila(capsys, raiz)  # rodada com lotes: IDs C1–C3 no manifesto

    def overrides():
        return [l for l in ler_jsonl(raiz / esquema.ARQ_DECISOES) if l.get("motivo_override")]

    codigo, res = rodar(capsys, raiz, "triagem", "override", "--id", "RS0002", "--decisao", "excluir", "--motivo", "x")
    assert codigo == 1 and "exige --criterio" in res["erro"]
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--id", "RS0002", "--decisao", "excluir",
                        "--criterio", "C9", "--motivo", "x")
    assert codigo == 1 and "C9" in res["erro"] and "C1, C2, C3" in res["erro"]
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--id", "RS0002", "--decisao", "incluir",
                        "--criterio", "C1", "--motivo", "x")
    assert codigo == 1 and "inclusão não tem critério" in res["erro"]
    assert overrides() == []

    # fila: uma linha boa e uma exclusão sem critério → nada é gravado (tudo ou nada)
    linhas = {l["id_rs"]: l for l in tl.ler_tabela_humana(fila, ["id_rs"])[1]}
    linhas["RS0002"].update(decisao_humana="incluir", motivo_humano="ok")
    linhas["RS0003"].update(decisao_humana="excluir", motivo_humano="sem critério")
    _regravar_fila(fila, list(linhas.values()), delimitador=",")
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", str(fila))
    assert codigo == 1 and "linha 3 (RS0003)" in res["erro"] and "criterio_humano" in res["erro"]
    assert overrides() == []
    linhas["RS0003"].update(criterio_humano="C2")
    _regravar_fila(fila, list(linhas.values()), delimitador="\t")
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", str(fila))
    assert codigo == 0 and res["registrados"] == 2
    assert {l["id_rs"]: l["criterio_falhou"] for l in overrides()} == {"RS0002": None, "RS0003": "C2"}


def test_regressao_override_tc_valida_contra_codebook(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=3)
    codebook = raiz / tl.ARQ_CODEBOOK_ELEGIBILIDADE
    codebook.parent.mkdir(parents=True, exist_ok=True)
    codebook.write_text("dimensao;variavel;descricao\nIdentificacao;texto_confere;x\n"
                        "Criterios de elegibilidade;c1_populacao_contexto;x\n"
                        "Criterios de elegibilidade;c2_intervencao_estudada;x\n", encoding="utf-8-sig")
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--etapa", "tc", "--id", "RS0001", "--decisao", "excluir",
                        "--motivo", "x")
    assert codigo == 1 and "exige --criterio" in res["erro"]
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--etapa", "tc", "--id", "RS0001", "--decisao", "excluir",
                        "--criterio", "C4", "--motivo", "x")
    assert codigo == 1 and "c1_populacao_contexto" in res["erro"]
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--etapa", "tc", "--id", "RS0001", "--decisao", "excluir",
                        "--criterio", "C2", "--motivo", "\"só menciona\" (p. 3)")
    assert codigo == 0 and res["registrados"] == 1
    linha = [l for l in ler_jsonl(raiz / esquema.ARQ_DECISOES) if l["etapa"] == "tc"][-1]
    assert (linha["criterio_falhou"], linha["revisor"]) == ("c2_intervencao_estudada", esquema.PAPEL_HUMANO_PADRAO)


def test_regressao_consolidar_tira_inativos_do_final_e_da_fila(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=6)
    gab_a = {"RS0001": "excluir", "RS0002": "excluir", "RS0003": "incluir"}
    gab_b = {"RS0001": "excluir", "RS0002": "incluir", "RS0003": "excluir"}
    triar_rodada(capsys, raiz, "ta_v2", {"A": gab_a, "B": gab_b}, tamanho=3)
    marcar_inativos(raiz, {"RS0002", "RS0005"})  # busca substituída depois da triagem
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    assert codigo == 0 and res["n_inativos_ignorados"] == 2 and res["n"] == 4 and res["sem_decisao"] == 0
    assert res["fila_humana"] == 1 and any(esquema.FLAG_BUSCA_INATIVA in a for a in res["avisos"])
    with open(raiz / esquema.ARQ_TRIAGEM_TA_FINAL, encoding="utf-8") as f:
        assert not {l["id_rs"] for l in csv.DictReader(f)} & {"RS0002", "RS0005"}
    assert [l["id_rs"] for l in tl.ler_tabela_humana(raiz / "02-triagem/fila_humana_ta_v2.csv", ["id_rs"])[1]] == ["RS0003"]
    assert eventos(raiz, "triagem_consolidada")[-1]["dados"]["n_inativos_ignorados"] == 2


def test_ler_tabela_humana_formatos(tmp_path):
    arq = tmp_path / "t.csv"
    arq.write_bytes("id_rs\tdecisao_humana\tmotivo_humano\r\nRS0001\tincluir\t\"a; b, c\"\r\n\r\n".encode("utf-16"))
    colunas, linhas, info = tl.ler_tabela_humana(arq, ["id_rs", "decisao_humana"])
    assert info["delimitador"] == "\t" and info["codificacao"] == "utf-16" and linhas[0]["motivo_humano"] == "a; b, c"
    arq.write_text("﻿ID_RS;Decisao_Humana\nRS0001;excluir\n", encoding="utf-8")
    colunas, linhas, info = tl.ler_tabela_humana(arq, ["id_rs", "decisao_humana"])
    assert colunas == ["id_rs", "decisao_humana"] and linhas == [{"id_rs": "RS0001", "decisao_humana": "excluir"}]
    arq.write_text("id_rs;titulo\nrs0002;x, y\n", encoding="utf-8")
    assert tl.ler_ids_arquivo(arq) == ["RS0002"]
    with pytest.raises(tl.ErroUso, match="colunas obrigatórias"):
        tl.ler_tabela_humana(arq, ["id_rs", "decisao_humana"])


# ---------------------------------------------------------------------------
# triagem fila --etapa tc
# ---------------------------------------------------------------------------
def test_triagem_fila_tc_gera_aplica_e_nao_regrava(projeto_vazio, capsys):
    from conftest import FIXTURES
    from test_textos import escrever_unicos

    raiz = projeto_vazio
    escrever_unicos(raiz)
    master = str(FIXTURES / "textos" / "master_elegibilidade.csv")
    codebook = str(FIXTURES / "textos" / "codebook_elegibilidade.csv")
    tl.registrar_decisoes(raiz, [tl.nova_decisao("RS0007", "tc", "tc", "revisor_humano_1", "humano", "incluir",
                                                 justificativa="li", motivo_override="li")])
    codigo, res = rodar(capsys, raiz, "triagem", "fila", "--etapa", "tc", "--master", master, "--codebook", codebook)
    assert codigo == 0, res
    rel = esquema.ARQ_FILA_HUMANA_TC
    assert res["arquivo"] == rel and res["n"] == 6 and res["n_com_decisao_humana"] == 1
    assert res["propostas"] == {"incerto": 1, "excluir": 2, "incluir": 3}
    assert res["criterios"] == ["C1_populacao", "C2_desenho", "C3_outcome"]
    with open(raiz / rel, encoding="utf-8") as f:
        assert f.readline().strip().split(",") == tl.COLUNAS_FILA_HUMANA_TC
    linhas = tl.ler_tabela_humana(raiz / rel, ["id_rs"])[1]
    assert [l["id_rs"] for l in linhas] == ["RS0004", "RS0002", "RS0003", "RS0001", "RS0005", "RS0006"]
    assert (linhas[1]["proposta"], linhas[1]["criterio_proposto"], linhas[1]["pagina"]) == ("excluir", "C2_desenho", "3")
    ev = eventos(raiz, "fila_gerada")
    assert len(ev) == 1 and ev[0]["dados"]["etapa"] == "tc" and ev[0]["artefatos"][0]["caminho"] == rel
    codigo, res = rodar(capsys, raiz, "triagem", "fila", "--etapa", "tc", "--master", master, "--codebook", codebook)
    assert res["reexecucao"] is True and len(eventos(raiz, "fila_gerada")) == 1

    # humano preenche no Excel (ponto e vírgula); gerar de novo recusa regravar
    por_id = {l["id_rs"]: l for l in linhas}
    por_id["RS0004"].update(decisao_humana="aguardando", motivo="autores contatados")
    por_id["RS0002"].update(decisao_humana="excluir", criterio_humano="C2", motivo="\"theoretical essay\" (p. 3)")
    _regravar_fila(raiz / rel, list(por_id.values()), colunas=tl.COLUNAS_FILA_HUMANA_TC)
    bruto = (raiz / rel).read_bytes()
    codigo, res = rodar(capsys, raiz, "triagem", "fila", "--etapa", "tc", "--master", master, "--codebook", codebook)
    assert codigo == 1 and "não aplicadas" in res["erro"] and (raiz / rel).read_bytes() == bruto

    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", rel)
    assert codigo == 1 and "--etapa tc" in res["erro"]
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", rel, "--etapa", "tc")
    assert codigo == 0 and res["registrados"] == 2 and "textos elegibilidade consolidar" in res["proxima_acao"]
    humanas = {l["id_rs"]: l for l in ler_jsonl(raiz / esquema.ARQ_DECISOES) if l["etapa"] == "tc"}
    assert (humanas["RS0002"]["criterio_falhou"], humanas["RS0004"]["decisao"]) == ("C2_desenho", "incerto")

    # aplicadas, a fila é regenerada só com o que falta
    codigo, res = rodar(capsys, raiz, "triagem", "fila", "--etapa", "tc", "--master", master, "--codebook", codebook)
    assert codigo == 0 and res["n"] == 4 and res["n_com_decisao_humana"] == 3
    assert len(eventos(raiz, "fila_gerada")) == 2


def test_triagem_fila_tc_sem_master_usa_elegibilidade_final(projeto_vazio, capsys):
    from test_textos import escrever_unicos
    from rslib.handoff import escrever_csv

    raiz = projeto_vazio
    escrever_unicos(raiz)
    codigo, res = rodar(capsys, raiz, "triagem", "fila", "--etapa", "tc")
    assert codigo == 1 and "--master" in res["erro"]
    escrever_csv(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL, esquema.COLUNAS_ELEGIBILIDADE_FINAL, [
        {"id_rs": "RS0001", "chave": "Alves2020", "decisao": "incluir"},
        {"id_rs": "RS0002", "chave": "Borges2019", "decisao": "excluir", "criterio_falhou": "C2", "pagina": "4"},
        {"id_rs": "RS0003", "chave": "Castro2018", "decisao": "aguardando", "evidencia": "[decisão humana: h] x"},
    ])
    marcar_inativos(raiz, {"RS0001"})
    codigo, res = rodar(capsys, raiz, "triagem", "fila", "--etapa", "tc")
    assert codigo == 0 and res["n"] == 1 and res["n_inativos_ignorados"] == 1
    assert res["fonte"] == esquema.ARQ_ELEGIBILIDADE_TC_FINAL


def test_regressao_xlsx_sem_openpyxl_sai_com_codigo_3(projeto_vazio, capsys, monkeypatch):
    import sys

    raiz = projeto_vazio
    criar_registros(raiz, n=2)
    (raiz / "02-triagem/fila_humana_ta_v2.xlsx").write_bytes(b"PK")
    monkeypatch.setitem(sys.modules, "openpyxl", None)  # import openpyxl -> ImportError
    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", "02-triagem/fila_humana_ta_v2.xlsx")
    assert codigo == 3 and res["dependencia_ausente"] is True and "openpyxl" in res["erro"]
    codigo, res = rodar(capsys, raiz, "validar", "calcular", "--planilha", "02-triagem/fila_humana_ta_v2.xlsx")
    assert codigo == 3 and "openpyxl" in res["erro"]


# ---------------------------------------------------------------------------
# v1.3: leitor único de planilhas, proxima_acao do mesclar, IDs de critério e permissões
# ---------------------------------------------------------------------------
def test_regressao_fila_cp1252_ponto_e_virgula_override_e_depois_consolidar(projeto_vazio, capsys):
    """O caso que quebrava: fila devolvida pelo Excel em cp1252 com ';', override aplicado e consolidar em seguida."""
    raiz = projeto_vazio
    fila = _projeto_com_fila(capsys, raiz)
    final = raiz / esquema.ARQ_TRIAGEM_TA_FINAL
    linhas = {l["id_rs"]: l for l in tl.ler_tabela_humana(fila, ["id_rs"])[1]}
    linhas["RS0002"].update(decisao_humana="incluir", motivo_humano="avalia a política (decisão da reunião)")
    linhas["RS0003"].update(decisao_humana="excluir", criterio_humano="C1", motivo_humano="não é município")
    _regravar_fila(fila, list(linhas.values()), delimitador=";", encoding="cp1252")
    assert b"\xe3" in fila.read_bytes() or b"\xe9" in fila.read_bytes()  # acentos em cp1252, não UTF-8

    codigo, res = rodar(capsys, raiz, "triagem", "override", "--fila", "02-triagem/fila_humana_ta_v2.csv")
    assert codigo == 0 and res["registrados"] == 2 and any("cp1252" in a for a in res["avisos"])
    n_eventos = len(eventos(raiz, "triagem_consolidada"))
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    assert codigo == 0, res
    assert res["fila_preservada"] is False and res["fila_humana"] == 0 and res["decidido_por"].get("humano") == 2
    assert len(eventos(raiz, "triagem_consolidada")) == n_eventos + 1
    with open(final, encoding="utf-8") as f:
        assert {l["id_rs"]: l["decisao_final"] for l in csv.DictReader(f)}["RS0003"] == "excluir"
    assert fila.read_bytes().decode("utf-8").startswith("id_rs,")  # fila regenerada pela skill, em UTF-8


def test_regressao_consolidar_nao_grava_final_se_a_leitura_falhar(projeto_vazio, capsys, monkeypatch):
    raiz = projeto_vazio
    _projeto_com_fila(capsys, raiz)
    final = raiz / esquema.ARQ_TRIAGEM_TA_FINAL
    final.write_text("id_rs,decisao_final\n", encoding="utf-8")
    antes = final.read_bytes()

    def falha(*a, **k):
        raise tl.ErroUso("falha simulada depois das leituras")

    monkeypatch.setattr(tl, "linhas_fila_nao_aplicadas", falha)
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2")
    assert codigo == 1 and final.read_bytes() == antes


def test_mesclar_proxima_acao_segue_o_status(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=6)
    criterios = criar_criterios(raiz)
    gab_a = {"RS0001": "excluir", "RS0002": "excluir", "RS0003": "incluir"}
    gab_b = {"RS0001": "excluir", "RS0002": "incluir", "RS0003": "incluir"}
    for revisor in ("A", "B"):
        codigo, _ = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", revisor,
                          "--criterios", criterios, "--tamanho", "3")
        assert codigo == 0
    responder_todos(raiz, "ta_v2", "A", gab_a)
    codigo, res = rodar(capsys, raiz, "triagem", "mesclar", "--rodada", "ta_v2", "--revisor", "A")
    assert codigo == 0 and res["proxima_acao"] == "triagem mesclar --rodada ta_v2 --revisor B"
    assert res["proxima_acao_detalhe"]["lotes_pendentes"] == {"B": 2}

    responder_todos(raiz, "ta_v2", "B", gab_b)
    codigo, res = rodar(capsys, raiz, "triagem", "mesclar", "--rodada", "ta_v2", "--revisor", "B")
    assert codigo == 0
    # 1 divergência (RS0002) sem árbitro: o próximo passo é o árbitro cego, não consolidar
    assert res["proxima_acao"].startswith("triagem preparar --etapa ta --rodada ta_v2 --revisor arbitro "
                                          "--apenas-divergentes --criterios 02-triagem/prompts/ta_v2.md")
    detalhe = res["proxima_acao_detalhe"]
    assert detalhe["n_divergentes_sem_arbitro"] == 1 and "--regra liberal" in detalhe["alternativa"]

    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v2", "--revisor", "arbitro",
                        "--criterios", criterios, "--apenas-divergentes")
    assert codigo == 0
    responder_todos(raiz, "ta_v2", "arbitro", {"RS0002": "incluir"})
    codigo, res = rodar(capsys, raiz, "triagem", "mesclar", "--rodada", "ta_v2", "--revisor", "arbitro")
    assert codigo == 0 and res["proxima_acao"] == "triagem consolidar --rodada ta_v2"


def test_ids_criterios_so_das_definicoes_nao_de_mencoes():
    modelo = (SKILL / "assets" / "templates" / "criterios_triagem.md").read_text(encoding="utf-8")
    assert "ver C5" in modelo and modelo.index("ver C5") < modelo.index("### C1.")
    assert tl.ids_criterios(modelo) == ["C1", "C2", "C3", "C4", "C5"]
    texto = "# Critérios\n\nIntrodução: o C9 do protocolo antigo saiu.\n\n### C1. População\n- ver C3\n### C2. Desenho\n"
    assert tl.ids_criterios(texto) == ["C1", "C2"]
    # prosa corrida sem definição em início de linha: continua valendo C<n> em qualquer lugar
    assert tl.ids_criterios("Aplique C1 (população) e depois C2 (desenho).") == ["C1", "C2"]


def test_preparar_aceita_criterios_em_cp1252(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=3)
    caminho = raiz / "02-triagem" / "prompts" / "ta_v1.md"
    caminho.write_bytes("# Critérios\n- C1 — População: municípios\n- C2 — Intervenção estudada\n".encode("cp1252"))
    codigo, res = rodar(capsys, raiz, "triagem", "preparar", "--rodada", "ta_v1", "--revisor", "A",
                        "--criterios", "02-triagem/prompts/ta_v1.md")
    assert codigo == 0 and any("cp1252" in a for a in res["avisos"])
    assert tl.ler_manifesto(raiz, "ta_v1", "A")["ids_criterios"] == ["C1", "C2"]


@pytest.mark.skipif(__import__("os").name == "nt", reason="permissões POSIX")
def test_regressao_escritas_da_triagem_com_permissao_de_arquivo_comum(projeto_vazio, capsys):
    import stat

    raiz = projeto_vazio
    fila = _projeto_com_fila(capsys, raiz)
    esperado = estado.modo_arquivo_padrao()
    for arq in (raiz / esquema.ARQ_TRIAGEM_TA_FINAL, fila, tl.caminho_manifesto(raiz, "ta_v2", "A")):
        assert stat.S_IMODE(arq.stat().st_mode) == esperado, arq


# ---------------------------------------------------------------------------
# Ids absorvidos pelo dedup depois da triagem (v1.4)
# ---------------------------------------------------------------------------
def _res(id_rs, decisao, por="consenso"):
    return {"id_rs": id_rs, "decisao_final": decisao, "decidido_por": por, "criterio_falhou": None,
            "divergente": 0, "revisado_humano": int(por == "humano"), "na_fila": False, "motivo_fila": None,
            "primarias": {}, "arbitro": None, "override": None}


def test_fundir_absorvidos_regra_pura():
    final = {
        "RS0001": _res("RS0001", "excluir"), "RS0011": _res("RS0011", "incerto"),        # mais inclusiva vence
        "RS0002": _res("RS0002", "incluir"), "RS0012": _res("RS0012", "excluir"),        # destino mantém
        "RS0003": _res("RS0003", "incluir"), "RS0013": _res("RS0013", "excluir", "humano"),  # override vence IA
        "RS0014": _res("RS0014", "incerto"),                                              # destino sem decisão
        "RS0015": _res("RS0015", "incluir"),                                              # sem destino: cai
        "RS0004": _res("RS0004", "incerto"), "RS0016": _res("RS0016", "incerto"),        # empate: destino
    }
    mapa = {"RS0011": "RS0001", "RS0012": "RS0002", "RS0013": "RS0003", "RS0014": "RS0005", "RS0015": "",
            "RS0016": "RS0004"}
    final, relatos = tl.fundir_absorvidos(final, mapa)
    assert not set(mapa) & set(final)
    assert (final["RS0001"]["decisao_final"], final["RS0001"]["id_rs"]) == ("incerto", "RS0001")
    assert final["RS0002"]["decisao_final"] == "incluir"
    assert (final["RS0003"]["decisao_final"], final["RS0003"]["decidido_por"]) == ("excluir", "humano")
    assert final["RS0005"]["decisao_final"] == "incerto" and final["RS0005"]["id_rs"] == "RS0005"
    assert final["RS0004"]["decisao_final"] == "incerto"
    por = {r["absorvido"]: r["resultado"] for r in relatos}
    assert por == {"RS0011": "substituida", "RS0012": "mantida", "RS0013": "substituida", "RS0014": "herdada",
                   "RS0015": "descartada", "RS0016": "mantida"}
    assert tl.fundir_absorvidos({"RS0001": _res("RS0001", "incluir")}, {}) == ({"RS0001": _res("RS0001", "incluir")}, [])


def test_consolidar_leva_decisao_de_absorvido_ao_registro_que_absorveu(projeto_vazio, capsys):
    raiz = projeto_vazio
    criar_registros(raiz, n=4)  # RS0005 foi absorvido por RS0002 e não está mais em registros_unicos
    tl.registrar_decisoes(raiz, _dup("RS0001", "ta_v2", "incluir") + _dup("RS0002", "ta_v2", "excluir",
                                                                           criterio_falhou="C1")
                          + _dup("RS0003", "ta_v2", "excluir", criterio_falhou="C1")
                          + _dup("RS0004", "ta_v2", "incluir") + _dup("RS0005", "ta_v2", "incerto"))
    estado.registrar_evento(raiz, "dedup_executado", "05_organizacao", "script", "dedup",
                            dados={"ids_rs_aposentados": {"RS0005": {"absorvido_por": "RS0002", "chave": "Autor2005"}}})
    codigo, res = rodar(capsys, raiz, "triagem", "consolidar", "--rodada", "ta_v2", "--regra", "liberal")
    assert codigo == 0 and res["n_absorvidos_dedup"] == 1
    with open(raiz / esquema.ARQ_TRIAGEM_TA_FINAL, encoding="utf-8") as f:
        final = {l["id_rs"]: l for l in csv.DictReader(f)}
    assert "RS0005" not in final and final["RS0002"]["decisao_final"] == "incerto"
    assert any("absorvidos pelo dedup" in a for a in res["avisos"])
    ev = eventos(raiz, "triagem_consolidada")[-1]["dados"]
    assert ev["absorvidos_dedup"] == [{"absorvido": "RS0005", "destino": "RS0002", "decisao_absorvido": "incerto",
                                       "decisao_destino": "excluir", "resultado": "substituida"}]
