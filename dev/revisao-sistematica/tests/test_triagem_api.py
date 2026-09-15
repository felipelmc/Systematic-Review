"""Testes da triagem via API (triagem_api.py + provedores.py) com provedores e clientes falsos.

Nenhum teste faz chamada real, lê .env ou exige pacote de SDK.
"""

import argparse
import csv
import json
import threading
from types import SimpleNamespace

import pytest

from conftest import SKILL, ler_jsonl
from rslib import esquema, estado, provedores, triagem_api

CRITERIOS = """# Critérios de elegibilidade — ta_v2

- C1: população de estudantes da educação básica.
- C2: desenho quantitativo que estima efeito de um programa.
- C3: publicado a partir de 2000.
"""

REGISTROS = [
    ("RS0001", "Transferência de renda e evasão escolar: evidência experimental",
     "Avaliamos um programa de transferência de renda com ensaio randomizado em escolas públicas."),
    ("RS0002", "Bolsa e frequência escolar: um estudo qualitativo",
     "Entrevistas com famílias beneficiárias sobre a frequência escolar dos filhos."),
    ("RS0003", "Registro importado sem resumo", ""),
    ("RS0004", "Volatilidade no mercado de ações brasileiro",
     "Modelamos a volatilidade diária de ações com GARCH."),
    ("RS0005", "Registro excluído pelo funil formal", "Resumo qualquer sobre escolas e renda."),
    ("RS0006", "Outro registro sem resumo na base", "[No abstract available]"),
]

# decisão por (modelo, palavra do título)
ROTEIRO = {
    ("modelo-a", "renda"): {"decisao": "incluir", "criterio_falhou": None, "justificativa": "Atende.",
                            "trecho": "ensaio randomizado em escolas públicas"},
    ("modelo-b", "renda"): {"decisao": "incluir", "criterio_falhou": None, "justificativa": "Atende.", "trecho": None},
    ("modelo-a", "Bolsa"): {"decisao": "incluir", "criterio_falhou": None, "justificativa": "Pode atender.",
                            "trecho": "frequência escolar"},
    ("modelo-b", "Bolsa"): {"decisao": "excluir", "criterio_falhou": "C2", "justificativa": "Qualitativo.",
                            "trecho": "Entrevistas com famílias"},
    ("modelo-c", "Bolsa"): {"decisao": "excluir", "criterio_falhou": "C2", "justificativa": "Divergem em C2.",
                            "trecho": "Entrevistas com famílias beneficiárias"},
    ("modelo-a", "ações"): {"decisao": "excluir", "criterio_falhou": "C1", "justificativa": "Não é educação.",
                            "trecho": None},
    ("modelo-b", "ações"): {"decisao": "excluir", "criterio_falhou": "C1", "justificativa": "Fora do tema.",
                            "trecho": "mercado de ações"},
}

ARGS_BASE = ["--rodada", "ta_v2", "--criterios", "02-triagem/prompts/ta_v2.md",
             "--modelo-a", "falso:modelo-a", "--modelo-b", "falso:modelo-b", "--arbitro", "falso:modelo-c",
             "--concorrencia", "1"]


# ---------------------------------------------------------------------------
# Infraestrutura de teste
# ---------------------------------------------------------------------------
def escrever_registros(raiz, registros):
    with open(raiz / esquema.ARQ_UNICOS, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=esquema.COLUNAS_UNICOS)
        w.writeheader()
        for id_rs, titulo, resumo in registros:
            linha = {c: "" for c in esquema.COLUNAS_UNICOS}
            linha.update({"id_rs": id_rs, "id_estudo": id_rs, "titulo": titulo, "resumo": resumo, "ano": "2019",
                          "tipo_publicacao": "artigo", "idioma": "pt"})
            w.writerow(linha)


@pytest.fixture
def projeto(projeto_vazio):
    escrever_registros(projeto_vazio, REGISTROS)
    (projeto_vazio / "02-triagem/prompts/ta_v2.md").write_text(CRITERIOS, encoding="utf-8")
    with open(projeto_vazio / esquema.ARQ_FILTRO_FORMAL, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(esquema.COLUNAS_FILTRO_FORMAL)
        w.writerow(["RS0005", "ano", "exclui", "previsto no protocolo"])
        w.writerow(["RS0001", "ano", "passa", ""])
    return projeto_vazio


class Queda(BaseException):
    """Simula o processo morrendo no meio (não é Exception: não é re-tentada)."""


class ProvedorFalso(provedores.Provedor):
    nome = "falso"
    suporta_lote = True

    def __init__(self, modelo, cenario, **kw):
        super().__init__(modelo, **kw)
        self.cenario = cenario

    def _resposta(self, usuario):
        for (modelo, palavra), resposta in self.cenario.roteiro.items():
            if modelo == self.modelo and palavra in usuario.split("</registro>")[0]:
                return dict(resposta)
        return {"decisao": "incluir", "criterio_falhou": None, "justificativa": "padrão", "trecho": None}

    def decidir(self, sistema, usuario, schema):
        if self.cenario.tokens:
            self._somar_uso(*self.cenario.tokens)  # a API cobra mesmo quando a resposta não serve
        with self.cenario.trava:
            self.cenario.chamadas.append((self.modelo, sistema, usuario))
            n = len(self.cenario.chamadas)
            if self.cenario.queda_a_partir_de and n >= self.cenario.queda_a_partir_de:
                raise Queda()
            for (modelo, palavra), fila in self.cenario.falhas.items():
                if modelo == self.modelo and palavra in usuario.split("</registro>")[0] and fila:
                    erro = fila.pop(0) if not isinstance(fila, Sempre) else fila.erro
                    raise erro
        return self._resposta(usuario)

    def enviar_lote(self, pedidos, schema):
        with self.cenario.trava:
            id_lote = f"lote_{self.modelo}_{len(self.cenario.lotes) + 1}"
            self.cenario.lotes[id_lote] = (list(pedidos), schema)
        return id_lote

    def coletar_lote(self, id_lote):
        if not self.cenario.lotes_prontos:
            return "em_andamento", {}
        pedidos, schema = self.cenario.lotes[id_lote]
        return "concluido", {cid: self.decidir(s, u, schema) for cid, s, u in pedidos}


class Sempre(list):
    """Fila de falhas que nunca se esgota."""

    def __init__(self, erro):
        super().__init__([erro])
        self.erro = erro


class Cenario:
    def __init__(self, roteiro=None):
        self.roteiro = dict(roteiro or ROTEIRO)
        self.chamadas = []
        self.falhas = {}
        self.queda_a_partir_de = None
        self.lotes = {}
        self.lotes_prontos = False
        self.tokens = None
        self.trava = threading.Lock()

    def chamadas_de(self, modelo):
        return [c for c in self.chamadas if c[0] == modelo]


@pytest.fixture
def cenario(monkeypatch):
    c = Cenario()
    monkeypatch.setitem(provedores.FABRICAS, "falso", lambda modelo, **kw: ProvedorFalso(modelo, c, **kw))
    esperas = []
    monkeypatch.setattr(triagem_api, "_dormir", esperas.append)
    c.esperas = esperas
    return c


def construir_parser():
    parser = argparse.ArgumentParser(prog="rs.py")
    parser.add_argument("--dir", default=None)
    sub = parser.add_subparsers(dest="comando")
    triagem_api.registrar(sub)
    return parser


def rodar(raiz, capsys, *extra):
    args = construir_parser().parse_args(["--dir", str(raiz), "triagem", "api", *ARGS_BASE, *extra])
    codigo = args.func(args)
    saida = capsys.readouterr().out.strip().splitlines()
    return codigo, json.loads(saida[-1])


def decisoes(raiz):
    return triagem_api.ler_decisoes(raiz / esquema.ARQ_DECISOES)


def chaves(raiz):
    return [(l["id_rs"], l["revisor"]) for l in decisoes(raiz)]


def eventos(raiz, nome):
    return [e for e in estado.ler_log(raiz) if e["evento"] == nome]


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------
def test_fluxo_completo_arbitro_so_em_divergencia(projeto, cenario, capsys):
    codigo, resumo = rodar(projeto, capsys)
    assert codigo == 0, resumo
    assert sorted(chaves(projeto)) == sorted([
        ("RS0001", "A"), ("RS0001", "B"), ("RS0002", "A"), ("RS0002", "B"), ("RS0002", "arbitro"),
        ("RS0003", "regra"), ("RS0004", "A"), ("RS0004", "B"), ("RS0006", "regra"),
    ])
    # árbitro chamado uma única vez, só para a divergência
    arb = cenario.chamadas_de("modelo-c")
    assert len(arb) == 1 and "Bolsa" in arb[0][2]
    # cego: rótulos Revisor A/B, sem nomes de modelo; instrução depois do texto
    _, sistema_arb, usuario_arb = arb[0]
    assert "<revisor_a>" in usuario_arb and "<revisor_b>" in usuario_arb
    assert "modelo-a" not in usuario_arb + sistema_arb and "modelo-b" not in usuario_arb + sistema_arb
    assert usuario_arb.index("</registro>") < usuario_arb.index("Releia")
    for _, _, usuario in cenario.chamadas:
        assert usuario.rstrip().endswith("trecho.")
        assert usuario.index("</registro>") < usuario.index("Releia")
    # sem resumo e excluídos pelo funil nunca vão à API
    todos = " ".join(u for _, _, u in cenario.chamadas)
    assert "sem resumo" not in todos and "funil formal" not in todos and "Outro registro" not in todos
    assert "RS0005" not in {l["id_rs"] for l in decisoes(projeto)}

    linhas = {(l["id_rs"], l["revisor"]): l for l in decisoes(projeto)}
    regra = linhas[("RS0003", "regra")]
    assert regra["decisao"] == "incerto" and regra["tipo_ator"] == "regra" and regra["modelo"] is None
    a1 = linhas[("RS0001", "A")]
    assert a1["tipo_ator"] == "ia_api" and a1["modelo"] == "modelo-a" and a1["etapa"] == "ta"
    doc = (projeto / "02-triagem/api/ta_v2/prompt_revisor.md").read_text(encoding="utf-8")
    assert a1["prompt_sha"] == estado.sha256_texto(doc)
    doc_arb = (projeto / "02-triagem/api/ta_v2/prompt_arbitro.md").read_text(encoding="utf-8")
    assert linhas[("RS0002", "arbitro")]["prompt_sha"] == estado.sha256_texto(doc_arb)
    assert set(a1) == set(esquema.CAMPOS_DECISAO)

    assert resumo["divergentes"] == 1 and resumo["arbitrados"] == 1 and resumo["consenso"] == 2
    assert resumo["sem_resumo_regra"] == 2 and resumo["excluidos_filtro_formal"] == 1
    assert resumo["completos"] == 5 and resumo["faltando"] == 0 and resumo["pendentes"] == 0
    assert len(eventos(projeto, "lote_mesclado")) == 1 and len(eventos(projeto, "artefato_versionado")) == 1
    ev = eventos(projeto, "lote_mesclado")[0]
    assert ev["ator"]["tipo"] == "ia_api" and "modelo-c" in ev["ator"]["modelo"]
    assert estado.carregar_estado(projeto)["versoes_ativas"]["prompt_triagem_api"].startswith("ta_v2:")

    # idempotência: nada novo, nenhuma chamada, nenhum evento de dados novo
    n_chamadas, n_linhas = len(cenario.chamadas), len(decisoes(projeto))
    codigo, resumo2 = rodar(projeto, capsys)
    assert codigo == 0 and len(cenario.chamadas) == n_chamadas and len(decisoes(projeto)) == n_linhas
    assert resumo2["novas"] == {"regra": 0, "revisores": 0, "arbitro": 0}
    assert len(eventos(projeto, "lote_mesclado")) == 1 and len(eventos(projeto, "artefato_versionado")) == 1


def test_fluxo_sem_modulo_de_lotes_usa_escritor_de_reserva(projeto, cenario, monkeypatch, capsys):
    monkeypatch.setattr(triagem_api, "_escritor_lotes", lambda: None)
    assert rodar(projeto, capsys)[0] == 0
    assert len(chaves(projeto)) == len(set(chaves(projeto))) == 9
    assert all(set(l) == set(esquema.CAMPOS_DECISAO) for l in decisoes(projeto))


def test_decisoes_validam_schema_e_log_valida(projeto, cenario, capsys):
    jsonschema = pytest.importorskip("jsonschema")
    assert rodar(projeto, capsys)[0] == 0
    schema = json.load(open(SKILL / "assets/schemas/decisao.schema.json", encoding="utf-8"))
    for linha in ler_jsonl(projeto / esquema.ARQ_DECISOES):
        jsonschema.validate(linha, schema)
    ev_schema = json.load(open(SKILL / "assets/schemas/evento.schema.json", encoding="utf-8"))
    for ev in estado.ler_log(projeto):
        jsonschema.validate(ev, ev_schema)
    est_schema = json.load(open(SKILL / "assets/schemas/estado.schema.json", encoding="utf-8"))
    jsonschema.validate(estado.carregar_estado(projeto), est_schema)


def test_divergencia_padrao_binaria_nao_arbitra_incluir_vs_incerto(projeto, cenario, capsys):
    cenario.roteiro[("modelo-b", "renda")] = {"decisao": "incerto", "criterio_falhou": None,
                                              "justificativa": "Ambíguo.", "trecho": None}
    codigo, resumo = rodar(projeto, capsys)
    assert codigo == 0
    assert [c for c in cenario.chamadas_de("modelo-c") if "renda" in c[2]] == []
    assert resumo["arbitrados"] == 1 and resumo["divergencia"] == "binaria"  # só Bolsa (incluir × excluir)


def test_divergencia_rotulo_arbitra_incluir_vs_incerto(projeto, cenario, capsys):
    cenario.roteiro[("modelo-b", "renda")] = {"decisao": "incerto", "criterio_falhou": None,
                                              "justificativa": "Ambíguo.", "trecho": None}
    assert rodar(projeto, capsys, "--divergencia", "rotulo")[0] == 0
    assert len(cenario.chamadas_de("modelo-c")) == 2


def test_ordem_dos_pareceres_do_arbitro_e_sorteada_e_reprodutivel():
    reg = {"titulo": "T", "resumo": "R"}
    a = {"decisao": "incluir", "justificativa": "parecer do papel A"}
    b = {"decisao": "excluir", "criterio_falhou": "C2", "justificativa": "parecer do papel B"}
    sorteios = {i: triagem_api.ordem_trocada("ta_v2", f"RS{i:04d}") for i in range(1, 41)}
    assert set(sorteios.values()) == {True, False}
    assert sorteios == {i: triagem_api.ordem_trocada("ta_v2", f"RS{i:04d}") for i in range(1, 41)}
    trocado = triagem_api.montar_usuario_arbitro(reg, a, b, trocar=True)
    assert trocado.index("parecer do papel B") < trocado.index("parecer do papel A")
    assert trocado.index("<revisor_a>") < trocado.index("parecer do papel B") < trocado.index("<revisor_b>")
    normal = triagem_api.montar_usuario_arbitro(reg, a, b)
    assert normal.index("parecer do papel A") < normal.index("parecer do papel B")


def test_saida_compativel_com_consolidacao_dos_lotes(projeto, cenario, capsys):
    """A consolidação do módulo de lotes lê as linhas da API sem adaptação."""
    triagem_lotes = pytest.importorskip("rslib.triagem_lotes")
    if not hasattr(triagem_lotes, "consolidar_decisoes"):
        pytest.skip("módulo de lotes sem consolidar_decisoes")
    assert rodar(projeto, capsys)[0] == 0
    vigentes = triagem_lotes.decisoes_vigentes(triagem_lotes.ler_decisoes(projeto), "ta", ["ta_v2"])
    final = triagem_lotes.consolidar_decisoes(vigentes, regra="consenso")
    assert final["RS0001"]["decisao_final"] == "incluir" and final["RS0001"]["decidido_por"] == "consenso"
    assert final["RS0002"]["decidido_por"] == "arbitro" and final["RS0002"]["decisao_final"] == "excluir"
    assert final["RS0003"]["decisao_final"] == "incerto" and final["RS0006"]["decisao_final"] == "incerto"
    assert final["RS0004"]["decisao_final"] == "excluir" and final["RS0004"]["criterio_falhou"] == "C1"
    assert "RS0005" not in final


def test_erro_transitorio_e_max_tokens_sao_retentados(projeto, cenario, capsys):
    cenario.falhas[("modelo-a", "renda")] = [
        provedores.ErroTransitorio("429 rate limit"),
        provedores.RespostaInvalida("resposta truncada (stop_reason=max_tokens)"),
    ]
    codigo, resumo = rodar(projeto, capsys)
    assert codigo == 0
    assert chaves(projeto).count(("RS0001", "A")) == 1
    assert len([c for c in cenario.chamadas_de("modelo-a") if "renda" in c[2]]) == 3
    assert resumo["retentativas"] == 2 and len(cenario.esperas) == 2
    assert all(e > 0 for e in cenario.esperas)


def test_resposta_fora_do_esquema_e_retentada(projeto, cenario, capsys):
    # exclusão sem critério e critério inexistente não viram decisão
    cenario.falhas[("modelo-b", "ações")] = []
    respostas = iter([
        {"decisao": "excluir", "criterio_falhou": None, "justificativa": "x", "trecho": None},
        {"decisao": "excluir", "criterio_falhou": "C9", "justificativa": "x", "trecho": None},
        {"decisao": "EXCLUIR", "criterio_falhou": "c1", "justificativa": "ok", "trecho": None},
    ])
    original = ProvedorFalso._resposta

    def resposta(self, usuario):
        if self.modelo == "modelo-b" and "ações" in usuario:
            return next(respostas)
        return original(self, usuario)

    ProvedorFalso._resposta = resposta
    try:
        codigo, resumo = rodar(projeto, capsys)
    finally:
        ProvedorFalso._resposta = original
    assert codigo == 0
    linha = {(l["id_rs"], l["revisor"]): l for l in decisoes(projeto)}[("RS0004", "B")]
    assert linha["decisao"] == "excluir" and linha["criterio_falhou"] == "C1"
    assert resumo["retentativas"] == 2


def test_falha_persistente_nao_e_pulada_e_retomada_completa(projeto, cenario, capsys):
    cenario.falhas[("modelo-b", "ações")] = Sempre(provedores.ErroTransitorio("503"))
    codigo, resumo = rodar(projeto, capsys, "--tentativas", "2", "--passadas", "2")
    assert codigo == 1
    assert resumo["pendentes"] == 1 and resumo["pendentes_ids"] == ["RS0004:B"]
    assert ("RS0004", "B") not in chaves(projeto)
    assert len([c for c in cenario.chamadas_de("modelo-b") if "ações" in c[2]]) == 4
    assert any("503" in e for e in resumo["ultimos_erros"])

    cenario.falhas.clear()
    antes = len(cenario.chamadas)
    codigo, resumo = rodar(projeto, capsys)
    assert codigo == 0 and resumo["pendentes"] == 0 and resumo["faltando"] == 0
    novas = cenario.chamadas[antes:]
    assert [(m, "ações" in u) for m, _, u in novas] == [("modelo-b", True)]
    assert chaves(projeto).count(("RS0004", "B")) == 1


def test_erro_de_requisicao_nao_e_repetido_na_passada(projeto, cenario, capsys):
    cenario.falhas[("modelo-a", "ações")] = Sempre(provedores.ErroRequisicao("400 prompt too long"))
    codigo, resumo = rodar(projeto, capsys, "--tentativas", "5", "--passadas", "1")
    assert codigo == 1 and resumo["pendentes_ids"] == ["RS0004:A"]
    assert len([c for c in cenario.chamadas_de("modelo-a") if "ações" in c[2]]) == 1


def test_erro_fatal_aborta_rodada(projeto, cenario, capsys):
    cenario.falhas[("modelo-a", "renda")] = Sempre(provedores.ErroFatal("401 credencial", codigo_saida=3))
    codigo, resumo = rodar(projeto, capsys)
    assert codigo == 3 and resumo["ok"] is False
    assert len(eventos(projeto, "erro")) == 1


def test_queda_no_meio_e_retomada_sem_duplicar(projeto, cenario, capsys):
    cenario.queda_a_partir_de = 4
    with pytest.raises(Queda):
        rodar(projeto, capsys)
    parciais = chaves(projeto)
    assert 0 < len([k for k in parciais if k[1] in ("A", "B")]) == 3
    # a queda deixou uma linha truncada no fim do arquivo
    with open(projeto / esquema.ARQ_DECISOES, "a", encoding="utf-8") as f:
        f.write('{"id_rs": "RS0004", "etapa": "ta", "rodada": "ta_v2", "revis')

    cenario.queda_a_partir_de = None
    antes = len(cenario.chamadas)
    codigo, resumo = rodar(projeto, capsys)
    assert codigo == 0 and resumo["faltando"] == 0
    feitas_antes = {k for k in parciais}
    esperadas = {("RS0001", "A"), ("RS0001", "B"), ("RS0002", "A"), ("RS0002", "B"),
                 ("RS0002", "arbitro"), ("RS0004", "A"), ("RS0004", "B")}
    assert len(cenario.chamadas) - antes == len(esperadas - feitas_antes)
    finais = chaves(projeto)
    assert len(finais) == len(set(finais))
    assert set(finais) == esperadas | {("RS0003", "regra"), ("RS0006", "regra")}
    # o fragmento truncado ficou isolado na própria linha; tudo depois dele é JSON válido
    brutas = (projeto / esquema.ARQ_DECISOES).read_text(encoding="utf-8").splitlines()
    invalidas = []
    for b in brutas:
        try:
            json.loads(b)
        except json.JSONDecodeError:
            invalidas.append(b)
    assert len(invalidas) == 1 and invalidas[0].endswith('"revis')


def test_concorrencia_sem_duplicatas(projeto_vazio, cenario, capsys):
    registros = [(f"RS{i:04d}", f"Estudo {i} sobre renda" if i % 3 else f"Estudo {i} sobre Bolsa",
                  "Resumo com ensaio randomizado em escolas públicas e frequência escolar.") for i in range(1, 41)]
    escrever_registros(projeto_vazio, registros)
    (projeto_vazio / "02-triagem/prompts/ta_v2.md").write_text(CRITERIOS, encoding="utf-8")
    args = [a if a != "1" else "8" for a in ARGS_BASE]
    parser_args = construir_parser().parse_args(["--dir", str(projeto_vazio), "triagem", "api", *args])
    assert parser_args.concorrencia == 8
    assert parser_args.func(parser_args) == 0
    resumo = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    finais = chaves(projeto_vazio)
    assert len(finais) == len(set(finais)) == 80 + resumo["divergentes"]
    assert resumo["divergentes"] == 13 and resumo["faltando"] == 0


def test_rodada_congelada(projeto, cenario, capsys):
    assert rodar(projeto, capsys)[0] == 0
    args = construir_parser().parse_args(
        ["--dir", str(projeto), "triagem", "api", *[a if a != "falso:modelo-a" else "falso:modelo-x" for a in ARGS_BASE]])
    assert args.func(args) == 1
    assert "congelada" in capsys.readouterr().err
    (projeto / "02-triagem/prompts/ta_v2.md").write_text(CRITERIOS + "- C4: novo critério.\n", encoding="utf-8")
    codigo, resumo = rodar(projeto, capsys)
    assert codigo == 1 and "congelada" in resumo["erro"]
    codigo, _ = rodar(projeto, capsys, "--esforco", "low")
    assert codigo == 1


def test_arbitro_precisa_ser_terceiro_modelo(projeto, cenario, capsys):
    args = construir_parser().parse_args(
        ["--dir", str(projeto), "triagem", "api", *[a if a != "falso:modelo-c" else "falso:modelo-a" for a in ARGS_BASE]])
    assert args.func(args) == 1
    assert "terceiro modelo" in capsys.readouterr().err
    assert cenario.chamadas == []


def test_trecho_inventado_e_descartado(projeto, cenario, capsys):
    cenario.roteiro[("modelo-a", "renda")] = {"decisao": "incluir", "criterio_falhou": None,
                                              "justificativa": "Atende.", "trecho": "frase que não está no resumo"}
    codigo, resumo = rodar(projeto, capsys)
    assert codigo == 0 and resumo["trechos_descartados"] == 1
    linha = {(l["id_rs"], l["revisor"]): l for l in decisoes(projeto)}[("RS0001", "A")]
    assert linha["trecho"] is None
    linha_ok = {(l["id_rs"], l["revisor"]): l for l in decisoes(projeto)}[("RS0002", "A")]
    assert linha_ok["trecho"] == "frequência escolar"


def test_limite_e_ids(projeto, cenario, capsys):
    codigo, resumo = rodar(projeto, capsys, "--limite", "1")
    assert codigo == 0
    assert {k for k in chaves(projeto) if k[1] in ("A", "B")} == {("RS0001", "A"), ("RS0001", "B")}
    lista = projeto / "ids.csv"
    lista.write_text("id_rs\nRS0004\n", encoding="utf-8")
    codigo, resumo = rodar(projeto, capsys, "--ids", str(lista))
    assert codigo == 0 and resumo["registros_elegiveis"] == 1
    assert ("RS0004", "B") in chaves(projeto) and ("RS0002", "A") not in chaves(projeto)


# ---------------------------------------------------------------------------
# Modo lote
# ---------------------------------------------------------------------------
def test_modo_lote_envia_coleta_e_arbitra(projeto, cenario, capsys):
    codigo, resumo = rodar(projeto, capsys, "--batch")
    assert codigo == 0 and len(resumo["lotes_enviados"]) == 2 and resumo["lotes_em_andamento"] == 2
    assert set(chaves(projeto)) == {("RS0003", "regra"), ("RS0006", "regra")}
    assert cenario.chamadas == []

    # ainda em andamento: nada reenviado
    codigo, resumo = rodar(projeto, capsys, "--batch")
    assert codigo == 0 and resumo["lotes_enviados"] == [] and resumo["lotes_em_andamento"] == 2
    assert len(cenario.lotes) == 2

    cenario.lotes_prontos = True
    codigo, resumo = rodar(projeto, capsys, "--batch")
    assert codigo == 0
    assert resumo["com_decisao_a"] == 3 and resumo["com_decisao_b"] == 3
    assert [l["papel"] for l in resumo["lotes_enviados"]] == ["arbitro"]
    lotes = {(l["id_rs"], l["revisor"]): l["lote"] for l in decisoes(projeto)}
    assert lotes[("RS0001", "A")].startswith("lote_modelo-a")

    codigo, resumo = rodar(projeto, capsys, "--batch")
    assert codigo == 0 and resumo["faltando"] == 0 and resumo["lotes_em_andamento"] == 0
    assert ("RS0002", "arbitro") in chaves(projeto)
    n = len(decisoes(projeto))
    codigo, resumo = rodar(projeto, capsys, "--batch")
    assert codigo == 0 and len(decisoes(projeto)) == n and resumo["lotes_enviados"] == []
    assert len(set(chaves(projeto))) == len(chaves(projeto))


# ---------------------------------------------------------------------------
# Estimativa e dependências
# ---------------------------------------------------------------------------
def test_estimar_nao_chama_nem_importa_sdk(projeto, monkeypatch, capsys):
    def proibido(*a, **k):
        raise AssertionError("--estimar não pode importar SDK nem instanciar provedor")

    monkeypatch.setattr(provedores, "_importar", proibido)
    monkeypatch.setattr(provedores, "criar_provedor", proibido)
    base = ["--dir", str(projeto), "triagem", "api", "--rodada", "ta_v2", "--criterios", "02-triagem/prompts/ta_v2.md",
            "--modelo-a", "claude-haiku-4-5", "--modelo-b", "gpt-4o-mini", "--arbitro", "claude-sonnet-5", "--estimar"]
    args = construir_parser().parse_args(base)
    assert args.func(args) == 0
    resumo = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert resumo["estimativa"] and resumo["tarefas_ab"] == 6 and resumo["sem_resumo_regra"] == 2
    assert resumo["custo_total_usd"] >= 0 and resumo["por_papel"]["A"]["custo_usd"] > 0
    assert resumo["por_papel"]["arbitro"]["chamadas"] == pytest.approx(0.6)
    assert not (projeto / esquema.ARQ_DECISOES).exists()
    # a estimativa entra no log como artefato versionado, sem chamadas, e não duplica (v1.1)
    ev = [e for e in eventos(projeto, "artefato_versionado") if e["dados"].get("tipo") == "estimativa_custo_api"]
    assert len(ev) == 1 and ev[0]["dados"]["chamadas_api"] == 0 and ev[0]["dados"]["rodada"] == "ta_v2"
    assert ev[0]["dados"]["estimativa"]["custo_total_usd"] == resumo["custo_total_usd"]
    assert ev[0]["artefatos"][0]["caminho"] == "02-triagem/prompts/ta_v2.md" and resumo["reexecucao"] is False
    assert ev[0]["ator"]["tipo"] == "script" and resumo["tabela_precos"]["claude-haiku-4-5"] == {"entrada": 1.0,
                                                                                                  "saida": 5.0}
    args = construir_parser().parse_args(base)
    assert args.func(args) == 0
    repetido = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert repetido["reexecucao"] is True and repetido["evento_seq"] == ev[0]["seq"]
    assert len([e for e in eventos(projeto, "artefato_versionado")
                if e["dados"].get("tipo") == "estimativa_custo_api"]) == 1
    # a pasta 02-triagem/api existe desde o init (esquema.PASTAS_PROJETO); --estimar não grava nada nela
    assert not [a for a in (projeto / "02-triagem/api").rglob("*") if a.is_file()]

    args = construir_parser().parse_args(base + ["--batch"])
    assert args.func(args) == 0
    lote = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert lote["por_papel"]["A"]["custo_usd"] == pytest.approx(resumo["por_papel"]["A"]["custo_usd"] / 2, rel=0.01)


def test_chave_ausente_sai_com_3(projeto, monkeypatch, capsys):
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(provedores, "_importar", lambda nome: SimpleNamespace())
    args = construir_parser().parse_args(
        ["--dir", str(projeto), "triagem", "api", "--rodada", "ta_v2", "--criterios", "02-triagem/prompts/ta_v2.md",
         "--modelo-a", "claude-haiku-4-5", "--modelo-b", "gpt-4o-mini", "--arbitro", "claude-sonnet-5"])
    assert args.func(args) == 3
    capturado = capsys.readouterr()
    assert "ANTHROPIC_API_KEY" in capturado.err and ".env" in capturado.err
    assert json.loads(capturado.out.strip().splitlines()[-1])["dependencia_ausente"] is True
    assert not (projeto / esquema.ARQ_DECISOES).exists()


def test_pacote_ausente_vira_erro_dependencia(monkeypatch):
    def sem_pacote(nome):
        raise ImportError(nome)

    monkeypatch.setattr(provedores, "_importar", sem_pacote)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "teste")
    monkeypatch.setenv("OPENAI_API_KEY", "teste")
    with pytest.raises(provedores.ErroDependencia, match="pip install anthropic"):
        provedores.criar_provedor("claude-haiku-4-5")
    with pytest.raises(provedores.ErroDependencia, match="pip install openai"):
        provedores.criar_provedor("gpt-4o-mini")


# ---------------------------------------------------------------------------
# Provedores reais com clientes falsos
# ---------------------------------------------------------------------------
JSON_OK = '{"decisao": "incluir", "criterio_falhou": null, "justificativa": "ok", "trecho": null}'


def msg_anthropic(parada="end_turn", texto=JSON_OK, pensamento=True):
    blocos = [SimpleNamespace(type="thinking", thinking="", signature="x")] if pensamento else []
    blocos.append(SimpleNamespace(type="text", text=texto))
    return SimpleNamespace(stop_reason=parada, content=blocos, usage=SimpleNamespace(input_tokens=100, output_tokens=20))


class ClienteAnthropicFalso:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []
        self.messages = SimpleNamespace(create=self._criar)

    def _criar(self, **corpo):
        self.chamadas.append(corpo)
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


@pytest.mark.parametrize("modelo, aceita", [
    ("claude-opus-5", False), ("claude-sonnet-5", False), ("claude-fable-5-1", False),
    ("claude-opus-4-8", False), ("claude-opus-4-7", False), ("claude-opus-4-6", True),
    ("claude-sonnet-4-6", True), ("claude-haiku-4-5", True), ("claude-haiku-4-5-20251001", True),
    ("claude-modelo-futuro", False), ("gpt-4o-mini", True), ("gpt-5-mini", False), ("o3", False),
])
def test_temperature_por_modelo(modelo, aceita):
    assert provedores.aceita_temperature(modelo) is aceita


@pytest.mark.parametrize("modelo", ["claude-opus-5", "claude-sonnet-5"])
def test_anthropic_claude5_sem_temperature_e_saida_estruturada(modelo):
    cliente = ClienteAnthropicFalso([msg_anthropic()])
    prov = provedores.ProvedorAnthropic(modelo, cliente=cliente)
    schema = triagem_api.schema_resposta(["C1", "C2"])
    assert prov.decidir("sistema", "usuario", schema)["decisao"] == "incluir"
    corpo = cliente.chamadas[0]
    assert "temperature" not in corpo
    assert corpo["output_config"]["format"] == {"type": "json_schema", "schema": schema}
    assert corpo["max_tokens"] == provedores.MAX_TOKENS_PADRAO_PENSANTE
    assert corpo["system"] == "sistema" and corpo["messages"] == [{"role": "user", "content": "usuario"}]
    assert prov.uso == {"chamadas": 1, "tokens_entrada": 100, "tokens_saida": 20}


def test_anthropic_haiku_envia_temperature_zero_e_esforco_opcional():
    cliente = ClienteAnthropicFalso([msg_anthropic(pensamento=False), msg_anthropic(pensamento=False)])
    provedores.ProvedorAnthropic("claude-haiku-4-5", cliente=cliente).decidir("s", "u", {})
    assert cliente.chamadas[0]["temperature"] == 0 and "effort" not in cliente.chamadas[0]["output_config"]
    provedores.ProvedorAnthropic("claude-haiku-4-5", cliente=cliente, esforco="low", max_tokens=300).decidir("s", "u", {})
    assert cliente.chamadas[1]["output_config"]["effort"] == "low" and cliente.chamadas[1]["max_tokens"] == 300


def test_anthropic_max_tokens_e_recusa_nao_sao_sucesso():
    truncada = msg_anthropic(parada="max_tokens", texto=JSON_OK)  # JSON "válido", mas truncado por definição
    prov = provedores.ProvedorAnthropic("claude-opus-5", cliente=ClienteAnthropicFalso([truncada]))
    with pytest.raises(provedores.RespostaInvalida, match="max_tokens"):
        prov.decidir("s", "u", {})
    prov = provedores.ProvedorAnthropic("claude-opus-5", cliente=ClienteAnthropicFalso([msg_anthropic(parada="refusal")]))
    with pytest.raises(provedores.RespostaInvalida, match="recusou"):
        prov.decidir("s", "u", {})


def test_anthropic_le_so_blocos_de_texto():
    msg = msg_anthropic(texto='```json\n' + JSON_OK + '\n```')
    msg.content.insert(0, SimpleNamespace(type="redacted_thinking", data="abc"))
    prov = provedores.ProvedorAnthropic("claude-opus-5", cliente=ClienteAnthropicFalso([msg]))
    assert prov.decidir("s", "u", {})["justificativa"] == "ok"


def test_max_tokens_na_orquestracao_nao_grava_e_retenta(projeto, monkeypatch, capsys):
    """Ponta a ponta: um stop_reason=max_tokens do SDK vira re-tentativa, não decisão."""
    cenario = Cenario()
    respostas = {"n": 0}

    def criar(**corpo):
        usuario = corpo["messages"][0]["content"]
        respostas["n"] += 1
        if respostas["n"] == 1:
            return msg_anthropic(parada="max_tokens",
                                 texto='{"decisao": "excluir", "criterio_falhou": "C1", "justificativa": "cort')
        return msg_anthropic(texto=json.dumps(ProvedorFalso("modelo-a", cenario)._resposta(usuario)))

    cliente = SimpleNamespace(messages=SimpleNamespace(create=criar))
    monkeypatch.setitem(provedores.FABRICAS, "cf",
                        lambda modelo, **kw: provedores.ProvedorAnthropic(modelo, cliente=cliente, **kw))
    monkeypatch.setitem(provedores.FABRICAS, "falso", lambda modelo, **kw: ProvedorFalso(modelo, cenario, **kw))
    monkeypatch.setattr(triagem_api, "_dormir", lambda s: None)
    args = construir_parser().parse_args(
        ["--dir", str(projeto), "triagem", "api", *[a if a != "falso:modelo-a" else "cf:claude-opus-5" for a in ARGS_BASE]])
    assert args.func(args) == 0
    resumo = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert resumo["retentativas"] == 1
    linhas = {(l["id_rs"], l["revisor"]): l for l in decisoes(projeto)}
    assert linhas[("RS0001", "A")]["decisao"] == "incluir" and linhas[("RS0001", "A")]["modelo"] == "claude-opus-5"
    assert resumo["parametros"]["A"]["temperature"] is None


def resposta_openai(fim="stop", conteudo=JSON_OK, recusa=None):
    return SimpleNamespace(
        choices=[SimpleNamespace(finish_reason=fim, message=SimpleNamespace(content=conteudo, refusal=recusa))],
        usage=SimpleNamespace(prompt_tokens=50, completion_tokens=10))


class ClienteOpenAIFalso:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._criar))

    def _criar(self, **corpo):
        self.chamadas.append(corpo)
        return self.respostas.pop(0)


def test_openai_json_schema_estrito_e_temperature():
    cliente = ClienteOpenAIFalso([resposta_openai(), resposta_openai()])
    schema = triagem_api.schema_resposta(["C1"])
    provedores.ProvedorOpenAI("gpt-4o-mini", cliente=cliente).decidir("s", "u", schema)
    corpo = cliente.chamadas[0]
    assert corpo["response_format"]["type"] == "json_schema"
    assert corpo["response_format"]["json_schema"]["strict"] is True
    assert corpo["response_format"]["json_schema"]["schema"] == schema
    assert corpo["temperature"] == 0 and corpo["messages"][0]["role"] == "system"
    provedores.ProvedorOpenAI("gpt-5-mini", cliente=cliente, esforco="low").decidir("s", "u", schema)
    assert "temperature" not in cliente.chamadas[1] and cliente.chamadas[1]["reasoning_effort"] == "low"


def test_openai_length_e_recusa_nao_sao_sucesso():
    prov = provedores.ProvedorOpenAI("gpt-4o-mini", cliente=ClienteOpenAIFalso([resposta_openai(fim="length")]))
    with pytest.raises(provedores.RespostaInvalida, match="truncada"):
        prov.decidir("s", "u", {})
    prov = provedores.ProvedorOpenAI("gpt-4o-mini", cliente=ClienteOpenAIFalso([resposta_openai(recusa="não")]))
    with pytest.raises(provedores.RespostaInvalida, match="recusou"):
        prov.decidir("s", "u", {})


def test_anthropic_lote_interpreta_resultados():
    lote = SimpleNamespace(id="msgbatch_1", processing_status="ended")
    itens = [
        SimpleNamespace(custom_id="RS0001__A", result=SimpleNamespace(type="succeeded", message=msg_anthropic())),
        SimpleNamespace(custom_id="RS0002__A", result=SimpleNamespace(type="succeeded",
                                                                     message=msg_anthropic(parada="max_tokens"))),
        SimpleNamespace(custom_id="RS0003__A", result=SimpleNamespace(type="errored")),
    ]
    enviados = []
    batches = SimpleNamespace(create=lambda requests: enviados.append(requests) or lote,
                              retrieve=lambda i: lote, results=lambda i: iter(itens))
    cliente = SimpleNamespace(messages=SimpleNamespace(batches=batches))
    prov = provedores.ProvedorAnthropic("claude-sonnet-5", cliente=cliente)
    assert prov.enviar_lote([("RS0001__A", "s", "u")], {}) == "msgbatch_1"
    assert "temperature" not in enviados[0][0]["params"]
    status, res = prov.coletar_lote("msgbatch_1")
    assert status == "concluido" and res["RS0001__A"]["decisao"] == "incluir"
    assert isinstance(res["RS0002__A"], provedores.RespostaInvalida)
    assert isinstance(res["RS0003__A"], provedores.ErroTransitorio)


class _ErroHTTP(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.status_code = status


@pytest.mark.parametrize("status, classe", [
    (401, provedores.ErroFatal), (403, provedores.ErroFatal), (404, provedores.ErroFatal),
    (400, provedores.ErroRequisicao), (429, provedores.ErroTransitorio), (529, provedores.ErroTransitorio),
    (None, provedores.ErroTransitorio),
])
def test_classificar_excecao(status, classe):
    exc = _ErroHTTP(status) if status else ConnectionError("rede caiu")
    classificada = provedores.classificar_excecao(exc)
    assert isinstance(classificada, classe)
    if status in (401, 403):
        assert classificada.codigo_saida == 3


def test_resolver_modelo():
    assert provedores.resolver_modelo("claude-haiku-4-5") == ("anthropic", "claude-haiku-4-5")
    assert provedores.resolver_modelo("gpt-4o-mini") == ("openai", "gpt-4o-mini")
    assert provedores.resolver_modelo("openai:o4-mini") == ("openai", "o4-mini")
    with pytest.raises(ValueError):
        provedores.resolver_modelo("modelo-misterioso")
    assert provedores.preco("claude-haiku-4-5-20251001") == (1.0, 5.0)
    assert provedores.preco("modelo-misterioso") is None


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def test_extrair_ids_criterios():
    texto = """# Critérios (CRITÉRIOS v2)
- C1: população
**C2** — desenho
| C3A | período |
Texto que remete ao C1 de novo.
"""
    assert triagem_api.extrair_ids_criterios(texto) == ["C1", "C2", "C3A"]
    outra_letra = """# Critérios
- I1: inclui estudantes
1. E2) exclui revisões
Frase com X9 no meio não conta.
"""
    assert triagem_api.extrair_ids_criterios(outra_letra) == ["I1", "E2"]
    assert triagem_api.extrair_ids_criterios("sem identificadores") == []


def test_sem_resumo():
    assert triagem_api.sem_resumo("") and triagem_api.sem_resumo(None) and triagem_api.sem_resumo("nan")
    assert triagem_api.sem_resumo("[No abstract available]") and triagem_api.sem_resumo("Resumo não disponível.")
    assert not triagem_api.sem_resumo("Estudo sobre escolas.")


@pytest.mark.parametrize("escritor_de_reserva", [True, False])
def test_anexar_depois_de_linha_truncada(tmp_path, monkeypatch, escritor_de_reserva):
    if escritor_de_reserva:
        monkeypatch.setattr(triagem_api, "_escritor_lotes", lambda: None)
    elif triagem_api._escritor_lotes() is None:
        pytest.skip("módulo de lotes ausente")
    caminho = tmp_path / esquema.ARQ_DECISOES
    caminho.parent.mkdir(parents=True)
    anterior = {c: None for c in esquema.CAMPOS_DECISAO}
    anterior.update({"id_rs": "RS0001", "etapa": "ta", "rodada": "r", "revisor": "A", "tipo_ator": "ia_api",
                     "decisao": "incluir", "ts": "2026-01-01T00:00:00Z"})
    caminho.write_text(json.dumps(anterior) + '\n{"id_rs": "RS00', encoding="utf-8")
    nova = dict(anterior, id_rs="RS0002")
    assert triagem_api.anexar_decisoes(tmp_path, [nova]) == 1
    linhas = triagem_api.ler_decisoes(caminho)
    assert [l["id_rs"] for l in linhas] == ["RS0001", "RS0002"]
    brutas = caminho.read_text(encoding="utf-8").splitlines()
    assert brutas[1] == '{"id_rs": "RS00' and json.loads(brutas[2])["id_rs"] == "RS0002"
    assert (tmp_path / "dados/.decisoes.lock").exists()


def test_registrar_reaproveita_triagem_de_outro_modulo():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    sub = parser.add_subparsers(dest="comando")
    triagem = sub.add_parser("triagem")  # como o módulo de lotes faria
    sub_triagem = triagem.add_subparsers(dest="subcomando_triagem")
    preparar = sub_triagem.add_parser("preparar")
    preparar.set_defaults(func=lambda a: "preparar")
    triagem_api.registrar(sub)
    args = parser.parse_args(["triagem", "api", "--rodada", "r", "--criterios", "c", "--modelo-a", "a",
                              "--modelo-b", "b", "--arbitro", "c", "--estimar"])
    assert args.func is triagem_api.executar and args.estimar
    assert parser.parse_args(["triagem", "preparar"]).func(None) == "preparar"


# ---------------------------------------------------------------------------
# Custo registrado no log e árbitro de terceiro modelo (v1.1)
# ---------------------------------------------------------------------------
PRECOS = {"modelo-a": [1.0, 2.0], "modelo-b": [3.0, 4.0], "modelo-c": [5.0, 6.0]}


def test_custo_estimado_por_chamada_e_total_no_evento(projeto, cenario, capsys):
    cenario.tokens = (100, 20)
    precos = projeto / "precos.json"
    precos.write_text(json.dumps(PRECOS), encoding="utf-8")
    codigo, resumo = rodar(projeto, capsys, "--precos", str(precos), "--limite", "1")
    assert codigo == 0
    ev1 = eventos(projeto, "lote_mesclado")[-1]["dados"]
    # --limite 1: A e B em RS0001 (sem divergência) → 2 chamadas
    assert ev1["custo_estimado_usd"] == pytest.approx((100 * 1 + 20 * 2 + 100 * 3 + 20 * 4) / 1e6)
    assert ev1["custo_estimado_rodada_usd"] == pytest.approx(ev1["custo_estimado_usd"])

    codigo, resumo = rodar(projeto, capsys, "--precos", str(precos))
    assert codigo == 0
    dados = eventos(projeto, "lote_mesclado")[-1]["dados"]
    # restantes: A e B em RS0002 e RS0004 (4 chamadas) + árbitro em RS0002 (1 chamada)
    esperado = (2 * (100 * 1 + 20 * 2) + 2 * (100 * 3 + 20 * 4) + (100 * 5 + 20 * 6)) / 1e6
    assert dados["custo_estimado_usd"] == pytest.approx(esperado)
    assert dados["custo_estimado_rodada_usd"] == pytest.approx(esperado + ev1["custo_estimado_usd"])
    assert dados["custo_por_papel"]["arbitro"]["chamadas"] == 1
    assert dados["custo_por_papel"]["A"]["custo_medio_por_chamada_usd"] == pytest.approx(140 / 1e6)
    assert dados["tabela_precos"]["modelo-c"] == {"entrada": 5.0, "saida": 6.0}
    assert dados["chamadas_api"] == 5 and dados["desconto_lote"] == 1.0 and dados["modelos_sem_preco"] == []
    assert resumo["custo_estimado_usd"] == pytest.approx(esperado)

    # a declaração de IA soma o custo das execuções (não o acumulado)
    from rslib import declaracao_ia
    dados_decl = declaracao_ia.coletar(projeto)  # regressão: prompt_sha em dict (API) quebrava a coleta
    assert sum(c for _, _, c, _ in dados_decl["custos"]) == pytest.approx(esperado + ev1["custo_estimado_usd"])
    sha_arbitro = estado.sha256_texto((projeto / "02-triagem/api/ta_v2/prompt_arbitro.md").read_text(encoding="utf-8"))
    assert any(sha == sha_arbitro and "arbitro" in nome for nome, sha in dados_decl["prompts"])

    n = len(eventos(projeto, "lote_mesclado"))
    assert rodar(projeto, capsys, "--precos", str(precos))[0] == 0
    assert len(eventos(projeto, "lote_mesclado")) == n, "sem chamadas, sem evento novo"


def test_modelo_sem_preco_deixa_custo_nulo(projeto, cenario, capsys):
    cenario.tokens = (10, 10)
    codigo, resumo = rodar(projeto, capsys, "--limite", "1")
    assert codigo == 0
    dados = eventos(projeto, "lote_mesclado")[-1]["dados"]
    assert dados["custo_estimado_usd"] is None and dados["modelos_sem_preco"] == ["modelo-a", "modelo-b"]
    assert dados["custo_parcial_usd"] == 0.0


def test_chamadas_sem_decisao_registram_custo_em_erro(projeto, cenario, capsys):
    cenario.tokens = (50, 5)
    for modelo in ("modelo-a", "modelo-b"):
        cenario.falhas[(modelo, "ações")] = Sempre(provedores.RespostaInvalida("resposta truncada"))
    lista = projeto / "ids.csv"
    lista.write_text("id_rs\nRS0004\n", encoding="utf-8")
    precos = projeto / "precos.json"
    precos.write_text(json.dumps(PRECOS), encoding="utf-8")
    codigo, resumo = rodar(projeto, capsys, "--ids", str(lista), "--tentativas", "2", "--passadas", "1",
                           "--precos", str(precos))
    assert codigo == 1 and resumo["pendentes"] == 2
    assert not eventos(projeto, "lote_mesclado")
    erro = eventos(projeto, "erro")[-1]["dados"]
    assert erro["chamadas_api"] == 4 and erro["custo_estimado_usd"] == pytest.approx(
        2 * (50 * 1 + 5 * 2) / 1e6 + 2 * (50 * 3 + 5 * 4) / 1e6)
    assert "sem decisão válida" in erro["erro"]


def test_arbitro_terceiro_modelo_preferencialmente_outro_provedor(projeto, cenario, capsys):
    assert "terceiro modelo, preferencialmente de outro provedor" in triagem_api.__doc__
    assert "adaptadores `anthropic` e `openai`" in provedores.__doc__
    codigo, resumo = rodar(projeto, capsys, "--limite", "1")
    assert codigo == 0
    assert any("preferencialmente de outro provedor" in a for a in resumo["avisos"])


def test_regressao_api_ignora_clusters_de_busca_substituida(projeto, cenario, capsys):
    """Cluster com a flag busca_inativa não vai à API, nem quando pedido em --ids."""
    registros = [("RS0007", "Transferência de renda de busca antiga", "Resumo sobre renda e escolas.")]
    escrever_registros(projeto, REGISTROS + registros)
    caminho = projeto / esquema.ARQ_UNICOS
    with open(caminho, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    for l in linhas:
        if l["id_rs"] in ("RS0004", "RS0007"):
            l["flags"] = esquema.FLAG_BUSCA_INATIVA
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=esquema.COLUNAS_UNICOS)
        w.writeheader()
        w.writerows(linhas)
    codigo, est = rodar(projeto, capsys, "--estimar")
    assert codigo == 0 and est["registros_elegiveis"] == 4  # 7 menos o funil (RS0005) e 2 inativos
    codigo, resumo = rodar(projeto, capsys)
    assert codigo == 0 and resumo["n_inativos_ignorados"] == 2 and resumo["registros_elegiveis"] == 4
    assert not {"RS0004", "RS0007"} & {l["id_rs"] for l in decisoes(projeto)}
    assert "Volatilidade" not in " ".join(u for _, _, u in cenario.chamadas)
    assert any(esquema.FLAG_BUSCA_INATIVA in a for a in resumo["avisos"])
    (projeto / "ids.csv").write_text("id_rs\nRS0007\n", encoding="utf-8")
    codigo, resumo = rodar(projeto, capsys, "--ids", str(projeto / "ids.csv"))
    assert codigo == 0 and resumo["registros_elegiveis"] == 0 and resumo["n_inativos_ignorados"] == 1


def test_ids_criterios_iguais_nos_dois_modos():
    from rslib import triagem_api, triagem_lotes
    texto = """# Critérios
Estudar não é mencionar (ver C5).

## C1 População
...
## C2 Intervenção
...
## C3 Resultado
...
## C4 Desenho elegível
...
## C5 Estudo primário
...
"""
    assert triagem_api.extrair_ids_criterios(texto) == triagem_lotes.ids_criterios(texto)
