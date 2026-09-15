import csv
import json

from conftest import FIXTURES, ler_jsonl


def test_chave_golden():
    from rslib import chave
    with open(FIXTURES / "chaves_golden.csv", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            assert chave.gerar_chave("", linha["autores"], linha["ano"], set()) == linha["chave_esperada"], linha


def test_sufixos_colisao():
    from rslib import chave
    usadas = set()
    ks = []
    for _ in range(28):
        k = chave.gerar_chave("", "Silva, J", 2020, usadas)
        usadas.add(k)
        ks.append(k)
    assert ks[:2] == ["Silva2020", "Silva2020a"] and ks[26:28] == ["Silva2020z", "Silva2020aa"]


def test_chave_valida_rejeita_url():
    from rslib import chave
    assert not chave.chave_valida("https://openalex.org/W2741809807")
    assert chave.chave_valida("Silva2020a")


def test_estado_log_seq_monotonico(projeto_vazio):
    from rslib import estado
    for i in range(3):
        estado.registrar_evento(projeto_vazio, "erro", "00_configuracao", "script", "t", dados={"i": i})
    eventos = ler_jsonl(projeto_vazio / "rs_log.jsonl")
    seqs = [e["seq"] for e in eventos]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    assert estado.carregar_estado(projeto_vazio)["ultimo_seq"] == seqs[-1]


def test_log_linha_truncada_nao_quebra(projeto_vazio):
    from rslib import estado
    with open(projeto_vazio / "rs_log.jsonl", "a", encoding="utf-8") as f:
        f.write('{"seq": 99, "ts": "x", "evento": "err')
    ev = estado.registrar_evento(projeto_vazio, "erro", "00_configuracao", "script", "t")
    assert ev["seq"] >= 2


def test_pendencias_e_portao_autopiloto(projeto_vazio):
    import pytest
    from rslib import estado
    est = estado.carregar_estado(projeto_vazio)
    est["modo"]["autonomia"] = "autopiloto"
    estado.salvar_estado(projeto_vazio, est)
    with pytest.raises(estado.ErroProjeto):
        estado.registrar_portao(projeto_vazio, "G2", "autopiloto", ator_tipo="script")
    estado.registrar_portao(projeto_vazio, "G4", "autopiloto", criterios={"recall_li": 0.93}, ator_tipo="script")
    pid = estado.abrir_pendencia(projeto_vazio, "validacao_humana", "06_triagem_ta", "codificar amostra", portao="G4", n=120)
    assert estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))[0]["id"] == pid
    assert estado.fechar_pendencia(projeto_vazio, pid, "amostra codificada")
    assert not estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))


def test_estado_valida_schema(projeto_vazio):
    jsonschema = __import__("pytest").importorskip("jsonschema")
    from conftest import SKILL
    schema = json.load(open(SKILL / "assets/schemas/estado.schema.json"))
    jsonschema.validate(json.load(open(projeto_vazio / "rs_estado.json")), schema)
    ev_schema = json.load(open(SKILL / "assets/schemas/evento.schema.json"))
    for ev in ler_jsonl(projeto_vazio / "rs_log.jsonl"):
        jsonschema.validate(ev, ev_schema)


def test_normalizar():
    from rslib import normalizar as n
    assert n.doi("https://doi.org/10.1016/J.ELECTSTUD.2016.03.005") == "10.1016/j.electstud.2016.03.005"
    assert n.doi("doi: 10.1590/1678-98732331e005.") == "10.1590/1678-98732331e005"
    assert n.doi("sem doi") == ""
    assert n.idioma("Português, Inglês") == "pt" and n.idioma("ENGLISH") == "en" and n.idioma("spa") == "es"
    assert n.tipo_publicacao("DISSERTAÇÃO") == "dissertacao" and n.tipo_publicacao("Article; Early Access") == "artigo"
    assert n.tipo_publicacao("Review") == "revisao" and n.tipo_publicacao("posted-content") == "preprint"
    assert n.titulo_normalizado("<i>Ill</i> Communication: Technology, distraction &amp; student performance") == \
        "ill communication technology distraction student performance"
    assert n.marcador_parte("Evaluation, Part II") == ["part ii"]
    assert n.autores_canonicos("Weihs M.; Rahman A.") == "Weihs, M. | Rahman, A."
    assert n.autores_canonicos("Brigitti Bonetti|Viviane Theiss") == "Bonetti, Brigitti | Theiss, Viviane"


def test_regressao_contratos_v11_em_esquema_e_modulos_importam_de_la():
    """Constantes v1.1 promovidas a esquema.py com os MESMOS valores de antes; os módulos usam as de esquema."""
    from rslib import caixa, declaracao_ia, dedup, efeitos_verificar, esquema, filtrar, handoff, prisma, projeto, textos
    from rslib import triagem_lotes as tl
    from rslib.importar import buscas, flags
    esperado = {
        "ARQ_REGISTROS_FLAGS": "dados/registros_flags.csv",
        "COLUNAS_REGISTROS_FLAGS": ["id_registro", "flag", "origem", "registrado_em"],
        "FLAG_BUSCA_INATIVA": "busca_inativa", "FLAG_RETRATADO": "retratado",
        "ARQ_RECALL_ANCORAS": "01-busca/recall_ancoras.json",
        "ARQ_RETRATACOES": "03-textos/retratacoes.csv",
        "COLUNAS_RETRATACOES": ["chave", "id_rs", "doi", "openalex_is_retracted", "crossref_avisos", "retratado",
                                "status", "verificado_em"],
        "ARQ_CONTATO_AUTORES": "03-textos/contato_autores.csv",
        "COLUNAS_CONTATO_AUTORES": ["chave", "autor_contatado", "data", "pedido", "resposta", "dados_recebidos"],
        "ARQ_CONFERENCIA_PDFS": "03-textos/conferencia_pdfs.csv",
        "COLUNAS_CONFERENCIA_PDFS": ["chave", "recuperado", "motivo"],
        "ARQ_PRISMA_CONTAGENS": "07-relatorio/prisma_contagens.json", "ARQ_PRISMA_MERMAID": "07-relatorio/prisma.mermaid",
        "ARQ_PRISMA_SVG": "07-relatorio/prisma.svg", "ARQ_PRISMA_PNG": "07-relatorio/prisma.png",
        "ARQ_CHECKLIST_PRISMA": "07-relatorio/checklist_prisma.csv", "DIR_VALIDACAO": "02-triagem/validacao",
        "VARIANTES_REVISAO": ["rapida"], "DECISAO_TC_AGUARDANDO": "aguardando",
    }
    for nome, valor in esperado.items():
        assert getattr(esquema, nome) == valor, nome
    assert flags.ARQ_REGISTROS_FLAGS is esquema.ARQ_REGISTROS_FLAGS
    assert flags.COLUNAS_REGISTROS_FLAGS is esquema.COLUNAS_REGISTROS_FLAGS
    assert buscas.FLAG_BUSCA_INATIVA is esquema.FLAG_BUSCA_INATIVA and dedup.FLAG_BUSCA_INATIVA is esquema.FLAG_BUSCA_INATIVA
    assert filtrar.ARQ_RECALL_ANCORAS is esquema.ARQ_RECALL_ANCORAS and filtrar.DIR_VALIDACAO is esquema.DIR_VALIDACAO
    assert textos.ARQ_RETRATACOES is esquema.ARQ_RETRATACOES and textos.COLUNAS_CONTATO_AUTORES is esquema.COLUNAS_CONTATO_AUTORES
    assert textos.ARQ_CONFERENCIA_PDFS is esquema.ARQ_CONFERENCIA_PDFS
    assert (prisma.ARQ_CONTAGENS, prisma.ARQ_MERMAID, prisma.ARQ_SVG, prisma.ARQ_PNG, prisma.ARQ_CHECKLIST) == (
        esquema.ARQ_PRISMA_CONTAGENS, esquema.ARQ_PRISMA_MERMAID, esquema.ARQ_PRISMA_SVG, esquema.ARQ_PRISMA_PNG,
        esquema.ARQ_CHECKLIST_PRISMA)
    assert declaracao_ia.ARQ_DECLARACAO is esquema.ARQ_DECLARACAO_IA and handoff.ARQ_BIB is esquema.ARQ_BIB
    assert caixa.ARQ_CAIXA is esquema.ARQ_CAIXA and efeitos_verificar.ARQ_VERIFICACAO_EFEITOS is esquema.ARQ_VERIFICACAO_EFEITOS
    assert projeto.VARIANTES is esquema.VARIANTES_REVISAO and tl.DECISAO_AGUARDANDO == esquema.DECISAO_TC_AGUARDANDO
    assert esquema.DECISAO_TC_AGUARDANDO in esquema.DECISOES_TC_FINAL
    assert set(esquema.COLUNAS_EFEITOS_EXTRAS_NUMERICAS) >= {"q1_1", "q3_1", "q1_2", "q3_2", "m_preditores"}


def test_regressao_schemas_declaram_campos_v11(projeto_vazio):
    """estado.schema: projeto.variante, buscas[].ativa e PRISMA-S; decisao.schema: incerto humano em tc = aguardando."""
    from conftest import SKILL
    from rslib import estado
    schema = json.load(open(SKILL / "assets/schemas/estado.schema.json", encoding="utf-8"))
    props_busca = schema["properties"]["buscas"]["items"]["properties"]
    for campo in ("ativa", "plataforma", "executada_em_origem", "string_id", "executada_em", "n_bruto",
                  "filtros_na_base", "substituida_por", "substituida_em", "motivo_substituicao", "substitui"):
        assert campo in props_busca, campo
    assert "variante" in schema["properties"]["projeto"]["properties"]
    decisao = json.load(open(SKILL / "assets/schemas/decisao.schema.json", encoding="utf-8"))
    assert decisao["properties"]["decisao"]["enum"] == ["incluir", "excluir", "incerto"]
    assert "aguardando" in decisao["properties"]["decisao"]["description"]
    jsonschema = __import__("pytest").importorskip("jsonschema")
    est = estado.carregar_estado(projeto_vazio)
    est["projeto"]["variante"] = "rapida"
    est["buscas"] = [
        {"id": "B01", "fonte": "scopus", "string_id": "S-scopus-v2", "executada_em": "2026-03-01",
         "executada_em_origem": "declarada", "n_bruto": 120, "n_importado": 118, "filtros_na_base": "2000-2025",
         "plataforma": "Scopus", "ativa": False, "substituida_por": "B06", "substituida_em": "2026-03-02T00:00:00Z",
         "motivo_substituicao": "âncora perdida", "importada": True},
        {"id": "B06", "fonte": "scopus", "ativa": True, "substitui": ["B01"]},
    ]
    jsonschema.validate(est, schema)
    est["buscas"][0]["ativa"] = "nao"
    with __import__("pytest").raises(jsonschema.ValidationError):
        jsonschema.validate(est, schema)
