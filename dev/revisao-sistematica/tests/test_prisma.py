"""Testes do PRISMA calculado: contagens, invariantes (exit 2), SVG/Mermaid, NR e checklist."""

import argparse
import csv
import json
import xml.etree.ElementTree as ET

import pytest

from conftest import SKILL, ler_jsonl


# ---------------------------------------------------------------------------
# Ledger sintético
# ---------------------------------------------------------------------------
# bases: 10 registros (6 WoS, 4 Scopus) -> 7 únicos (3 duplicatas); 1 excluído por automação;
#        6 triados, 2 excluídos, 4 buscados; 1 PDF não recuperado; 3 avaliados; 1 excluído; 2 incluídos
# outros: 3 registros de bola de neve -> 2 novos únicos (1 já estava nas bases); 2 triados, 1 excluído,
#         1 buscado, 1 avaliado, 1 incluído
# incluídos: 3 relatos de 2 estudos (RS0001 e RS0006 são relatos do mesmo estudo)
REGISTROS = [
    ("B01-00001", "B01", "wos", "base"), ("B01-00002", "B01", "wos", "base"), ("B01-00003", "B01", "wos", "base"),
    ("B01-00004", "B01", "wos", "base"), ("B01-00005", "B01", "wos", "base"), ("B01-00006", "B01", "wos", "base"),
    ("B02-00001", "B02", "scopus", "base"), ("B02-00002", "B02", "scopus", "base"),
    ("B02-00003", "B02", "scopus", "base"), ("B02-00004", "B02", "scopus", "base"),
    ("SN1-00001", "SN1", "openalex", "citacao"), ("SN1-00002", "SN1", "openalex", "citacao"),
    ("SN1-00003", "SN1", "openalex", "citacao"),
]
UNICOS = [  # id_rs, id_estudo, chave, ids_registro
    ("RS0001", "ES0001", "Silva2020", "B01-00001|B02-00001"),
    ("RS0002", "RS0002", "Souza2019", "B01-00002|B02-00002"),
    ("RS0003", "RS0003", "Lima2021", "B01-00003|SN1-00003"),
    ("RS0004", "RS0004", "Alves2017", "B01-00004"),
    ("RS0005", "RS0005", "Dias2016", "B01-00005"),
    ("RS0006", "ES0001", "Costa2018", "B01-00006|B02-00003"),
    ("RS0007", "RS0007", "Melo1990", "B02-00004"),
    ("RS0008", "RS0008", "Rocha2022", "SN1-00001"),
    ("RS0009", "RS0009", "Nunes2015", "SN1-00002"),
]
FILTRO = [("RS0007", "ano", "exclui", "1990 < 2000"), ("RS0005", "idioma", "etiqueta", "fr")]
TRIAGEM = [("RS0001", "incluir"), ("RS0002", "incluir"), ("RS0003", "incerto"), ("RS0004", "excluir"),
           ("RS0005", "excluir"), ("RS0006", "incluir"), ("RS0008", "incluir"), ("RS0009", "excluir")]
PDFS = [("Silva2020", "ok"), ("Souza2019", "ok"), ("Lima2021", "nao_encontrado"), ("Costa2018", "ja_existia"),
        ("Rocha2022", "ok")]
ELEGIBILIDADE = [("RS0001", "Silva2020", "incluir", ""), ("RS0002", "Souza2019", "excluir", "desenho"),
                 ("RS0006", "Costa2018", "incluir", ""), ("RS0008", "Rocha2022", "incluir", "")]


def _escrever(caminho, colunas, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas)
        w.writeheader()
        for linha in linhas:
            w.writerow({c: linha.get(c, "") for c in colunas})


def montar_ledger(raiz, ate="elegibilidade", registros=None, unicos=None, triagem=None, elegibilidade=None):
    """Escreve os CSVs do ledger sintético até a etapa pedida (registros|unicos|triagem|pdfs|elegibilidade)."""
    from rslib import esquema
    ordem = ["registros", "unicos", "filtro", "triagem", "pdfs", "elegibilidade"]
    passos = set(ordem[: ordem.index(ate) + 1])
    _escrever(raiz / esquema.ARQ_REGISTROS, esquema.COLUNAS_REGISTROS,
              [{"id_registro": i, "busca_id": b, "fonte": f, "metodo_identificacao": m, "titulo": f"T {i}"}
               for i, b, f, m in (registros or REGISTROS)])
    if "unicos" in passos:
        _escrever(raiz / esquema.ARQ_UNICOS, esquema.COLUNAS_UNICOS,
                  [{"id_rs": r, "id_estudo": e, "chave": k, "ids_registro": ids} for r, e, k, ids in (unicos or UNICOS)])
    if "filtro" in passos:
        _escrever(raiz / esquema.ARQ_FILTRO_FORMAL, esquema.COLUNAS_FILTRO_FORMAL,
                  [{"id_rs": r, "filtro": f, "resultado": res, "detalhe": d} for r, f, res, d in FILTRO])
    if "triagem" in passos:
        _escrever(raiz / esquema.ARQ_TRIAGEM_TA_FINAL, esquema.COLUNAS_TRIAGEM_FINAL,
                  [{"id_rs": r, "decisao_final": d} for r, d in (triagem or TRIAGEM)])
    if "pdfs" in passos:
        _escrever(raiz / esquema.ARQ_RELATORIO_PDFS, esquema.COLUNAS_RELATORIO_PDFS,
                  [{"chave": k, "status": s} for k, s in PDFS])
    if "elegibilidade" in passos:
        _escrever(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL, esquema.COLUNAS_ELEGIBILIDADE_FINAL,
                  [{"id_rs": r, "chave": k, "decisao": d, "criterio_falhou": c}
                   for r, k, d, c in (elegibilidade or ELEGIBILIDADE)])


def rodar(capsys, *argv):
    """Roda os comandos deste módulo sem depender dos demais módulos do dispatcher."""
    from rslib import prisma, projeto
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    sub = parser.add_subparsers(dest="comando")
    projeto.registrar(sub)
    prisma.registrar(sub)
    args = parser.parse_args([str(a) for a in argv])
    codigo = args.func(args)
    saida = capsys.readouterr().out.strip().splitlines()
    return codigo, json.loads(saida[-1]) if saida else None


# ---------------------------------------------------------------------------
# Contagens e invariantes
# ---------------------------------------------------------------------------
def test_contagens_calculadas_do_ledger(projeto_vazio):
    from rslib import estado, prisma
    montar_ledger(projeto_vazio)
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    b, o = c["bases"], c["outros_metodos"]
    assert b["identificados"]["bases"] == 10 and b["identificados"]["registros_estudos"] == 0
    assert b["identificados"]["por_fonte"] == {"wos": 6, "scopus": 4}
    assert b["removidos_antes_triagem"]["duplicatas"] == 3
    assert b["removidos_antes_triagem"]["automacao"] == 1
    assert b["removidos_antes_triagem"]["automacao_por_filtro"] == {"ano": 1}
    assert (b["a_triar"], b["triados"], b["excluidos_triagem"], b["buscados"]) == (6, 6, 2, 4)
    assert (b["nao_recuperados"], b["avaliados"], b["incluidos_relatos"]) == (1, 3, 2)
    assert b["excluidos_elegibilidade"] == {"total": 1, "motivos": {"desenho": 1}}
    assert o["identificados"]["busca_citacoes"] == 3
    assert o["removidos_antes_triagem"]["duplicatas"] == 1
    assert (o["triados"], o["excluidos_triagem"], o["buscados"], o["nao_recuperados"], o["avaliados"]) == (2, 1, 1, 0, 1)
    assert c["incluidos"] == {"estudos": 2, "relatos": 3}
    assert not prisma.invariantes_quebradas(c)
    assert all(i["ok"] is True for i in c["invariantes"])


def test_prisma_gera_svg_mermaid_json_checklist_e_evento(projeto_vazio, capsys):
    from rslib import esquema
    montar_ledger(projeto_vazio)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert codigo == 0 and res["ok"] and res["incluidos"] == {"estudos": 2, "relatos": 3}
    rel = projeto_vazio / "07-relatorio"
    raiz_svg = ET.parse(rel / "prisma.svg").getroot()  # XML bem formado
    assert raiz_svg.tag.endswith("svg")
    texto_svg = (rel / "prisma.svg").read_text(encoding="utf-8")
    assert "Registros triados" in texto_svg and "Identificação de estudos via outros métodos" in texto_svg
    assert "desenho (n = 1)" in texto_svg and esquema.MARCA_RASCUNHO not in texto_svg
    mermaid = (rel / "prisma.mermaid").read_text(encoding="utf-8")
    assert mermaid.startswith("flowchart TD") and "o_avaliados --> incluidos" in mermaid
    contagens = json.loads((rel / "prisma_contagens.json").read_text(encoding="utf-8"))
    assert contagens["bases"]["buscados"] == 4 and "_tem_outros" not in contagens
    with open(rel / "checklist_prisma.csv", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    assert len({l["item"] for l in linhas}) == 42 and linhas[0]["item"] == "1"
    item16a = next(l for l in linhas if l["item"] == "16a")
    assert item16a["status"] == "material_disponivel" and "prisma.svg" in item16a["evidencia_no_projeto"]
    eventos = [e for e in ler_jsonl(projeto_vazio / "rs_log.jsonl") if e["evento"] == "prisma_gerado"]
    assert len(eventos) == 1
    assert {a["caminho"] for a in eventos[0]["artefatos"]} >= {"07-relatorio/prisma.svg", "07-relatorio/prisma_contagens.json"}


def test_prisma_reexecucao_nao_duplica_evento(projeto_vazio, capsys):
    montar_ledger(projeto_vazio)
    assert rodar(capsys, "--dir", projeto_vazio, "prisma")[0] == 0
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert codigo == 0 and res["reexecucao"] is True
    eventos = [e for e in ler_jsonl(projeto_vazio / "rs_log.jsonl") if e["evento"] == "prisma_gerado"]
    assert len(eventos) == 1


def test_invariante_quebrada_elegibilidade_incompleta_exit2(projeto_vazio, capsys):
    # RS0006 foi buscado e recuperado, mas não avaliado: avaliados (2) ≠ buscados − não recuperados (3)
    montar_ledger(projeto_vazio, elegibilidade=[e for e in ELEGIBILIDADE if e[0] != "RS0006"])
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert codigo == 2 and res["erro"] == "invariantes_quebradas"
    assert any(i["nome"] == "recuperacao_fecha" and i["ramo"] == "bases" for i in res["invariantes"])
    assert not (projeto_vazio / "07-relatorio" / "prisma.svg").exists()


def test_invariante_registros_fora_do_dedup_exit2(projeto_vazio, capsys):
    registros = REGISTROS + [("B03-00001", "B03", "scielo", "base")]  # importado depois do dedup
    montar_ledger(projeto_vazio, registros=registros)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    nomes = {i["nome"] for i in res["invariantes"]}
    assert codigo == 2 and {"registros_sem_cluster", "identificacao_fecha"} <= nomes


def test_invariante_triagem_sem_decisao_exit2(projeto_vazio, capsys):
    montar_ledger(projeto_vazio, ate="triagem", triagem=TRIAGEM[:-2] + [("RS0008", ""), ("RS0009", "excluir")])
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert codigo == 2
    assert any(i["nome"] == "triagem_fecha" and i["ramo"] == "outros_metodos" for i in res["invariantes"])


def test_triagem_de_id_desconhecido_exit2(projeto_vazio):
    from rslib import estado, prisma
    montar_ledger(projeto_vazio, ate="triagem", triagem=TRIAGEM + [("RS9999", "incluir")])
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    assert "triagem_ids_desconhecidos" in {i["nome"] for i in prisma.invariantes_quebradas(c)}


def test_rascunho_com_pendencias_abertas(projeto_vazio, capsys):
    from rslib import esquema, estado
    montar_ledger(projeto_vazio)
    pid = estado.abrir_pendencia(projeto_vazio, "validacao_humana", "06_triagem_ta", "codificar amostra", portao="G4")
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert codigo == 0 and res["rascunho"] is True and res["pendencias_abertas"] == [pid]
    svg = (projeto_vazio / "07-relatorio" / "prisma.svg").read_text(encoding="utf-8")
    assert esquema.MARCA_RASCUNHO in svg and pid in svg
    assert esquema.MARCA_RASCUNHO in (projeto_vazio / "07-relatorio" / "prisma.mermaid").read_text(encoding="utf-8")
    # fechar a pendência muda o hash dos insumos: o PRISMA é regenerado sem a marca
    estado.fechar_pendencia(projeto_vazio, pid, "amostra codificada")
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert codigo == 0 and res["reexecucao"] is False and res["rascunho"] is False
    assert esquema.MARCA_RASCUNHO not in (projeto_vazio / "07-relatorio" / "prisma.svg").read_text(encoding="utf-8")


def test_nr_em_projeto_parcial(tmp_path, capsys):
    raiz = tmp_path / "parcial"
    codigo, _ = rodar(capsys, "--dir", raiz, "init", "--titulo", "Só triagem", "--parcial", "triagem", "--sem-r")
    assert codigo == 0
    montar_ledger(raiz, ate="triagem")
    codigo, res = rodar(capsys, "--dir", raiz, "prisma")
    assert codigo == 0
    contagens = json.loads((raiz / "07-relatorio" / "prisma_contagens.json").read_text(encoding="utf-8"))
    assert contagens["bases"]["buscados"] == 4
    assert contagens["bases"]["avaliados"] == "NR" and contagens["incluidos"]["estudos"] == "NR"
    assert {"etapa": "07_textos_elegibilidade", "motivo": "ignorada"} in contagens["etapas_nr"]
    svg = (raiz / "07-relatorio" / "prisma.svg").read_text(encoding="utf-8")
    assert "(n = NR)" in svg
    assert all(i["ok"] is not False for i in contagens["invariantes"])


def test_resumo_maior_que_limite_padrao_do_csv(projeto_vazio):
    from rslib import esquema, estado, prisma
    montar_ledger(projeto_vazio, ate="unicos")
    with open(projeto_vazio / esquema.ARQ_UNICOS, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    linhas[0]["resumo"] = "palavra " * 40000  # ~320 kB num campo
    _escrever(projeto_vazio / esquema.ARQ_UNICOS, esquema.COLUNAS_UNICOS, linhas)
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    assert c["bases"]["a_triar"] == 7  # sem filtro formal ainda: nada removido por automação
    assert c["bases"]["removidos_antes_triagem"]["automacao"] == 0


def test_sem_registros_tudo_nr_sem_erro(projeto_vazio):
    from rslib import estado, prisma
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    assert c["bases"]["triados"] == "NR" and c["incluidos"]["relatos"] == "NR"
    assert not prisma.invariantes_quebradas(c)
    ET.fromstring(prisma.gerar_svg(c))


def test_sem_outros_metodos_usa_modelo_so_bases(projeto_vazio):
    from rslib import estado, prisma
    regs = [r for r in REGISTROS if r[3] == "base"]
    unicos = [(r, e, k, ids.replace("|SN1-00003", "")) for r, e, k, ids in UNICOS if not ids.startswith("SN1")]
    montar_ledger(projeto_vazio, ate="registros", registros=regs)
    montar_ledger(projeto_vazio, ate="unicos", registros=regs, unicos=unicos)
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    svg = prisma.gerar_svg(c)
    assert "outros métodos" not in svg and "Identificação de estudos via bases de dados e registros" in svg


# ---------------------------------------------------------------------------
# Modo manual, idiomas e checklist
# ---------------------------------------------------------------------------
def test_manual_sem_projeto_com_nr(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manual = tmp_path / "contagens.json"
    manual.write_text(json.dumps({
        "bases": {"identificados": {"bases": 120}, "removidos_antes_triagem": {"duplicatas": 20},
                  "triados": 100, "excluidos_triagem": 80, "buscados": 20,
                  "excluidos_elegibilidade": {"total": 12, "motivos": {"população": 7, "desenho": 5}},
                  "avaliados": 18, "incluidos_relatos": 6},
    }), encoding="utf-8")
    codigo, res = rodar(capsys, "prisma", "--manual", manual, "--idioma", "en")
    assert codigo == 0 and res["origem"] == "manual"
    svg = (tmp_path / "prisma.svg").read_text(encoding="utf-8")
    assert "Records screened" in svg and "Reports not retrieved" in svg and "(n = NR)" in svg
    contagens = json.loads((tmp_path / "prisma_contagens.json").read_text(encoding="utf-8"))
    assert contagens["bases"]["nao_recuperados"] == "NR" and contagens["incluidos"]["relatos"] == 6
    # reaproveitar o JSON gerado como entrada não cria um ramo "outros métodos" fantasma
    codigo, _ = rodar(capsys, "prisma", "--manual", tmp_path / "prisma_contagens.json", "--saida", tmp_path / "de_novo")
    assert codigo == 0
    assert "other methods" not in (tmp_path / "de_novo" / "prisma.svg").read_text(encoding="utf-8").lower()


def test_manual_invariante_quebrada_exit2(tmp_path, capsys):
    manual = tmp_path / "contagens.json"
    manual.write_text(json.dumps({"bases": {"triados": 100, "excluidos_triagem": 80, "buscados": 25}}), encoding="utf-8")
    codigo, res = rodar(capsys, "prisma", "--manual", manual)
    assert codigo == 2 and res["invariantes"][0]["nome"] == "triagem_fecha"
    assert not (tmp_path / "prisma.svg").exists()


def test_manual_estrutura_invalida_exit1(tmp_path, capsys):
    manual = tmp_path / "contagens.json"
    manual.write_text(json.dumps({"bases": {"removidos_antes_triagem": 5}}), encoding="utf-8")
    codigo, res = rodar(capsys, "prisma", "--manual", manual)
    assert codigo == 1 and res["erro"] == "manual_invalido"


def test_prisma_sem_projeto_e_sem_manual_exit1(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    codigo, res = rodar(capsys, "prisma")
    assert codigo == 1 and res["erro"] == "sem_projeto"


def test_tipo_scr_rotulos(projeto_vazio):
    from rslib import estado, prisma
    montar_ledger(projeto_vazio)
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio), tipo="scr")
    assert "Fontes de evidência incluídas" in prisma.gerar_svg(c)
    itens, _ = prisma.carregar_checklist("scr")
    assert len(itens) >= 20


def test_checklist_csv_bate_com_lista_embutida():
    from rslib import prisma
    with open(SKILL / "assets" / "checklists" / "prisma2020.csv", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    assert list(linhas[0]) == ["item", "secao", "topico", "descricao"]
    assert [tuple(l.values()) for l in linhas] == [tuple(i) for i in prisma.CHECKLIST_2020_EMBUTIDO]
    numeros = {int("".join(ch for ch in l["item"] if ch.isdigit())) for l in linhas}
    assert numeros == set(range(1, 28))


def test_texto_com_caracteres_especiais_no_svg(projeto_vazio):
    from rslib import estado, prisma
    montar_ledger(projeto_vazio, elegibilidade=[("RS0001", "Silva2020", "incluir", ""),
                                                ("RS0002", "Souza2019", "excluir", 'população <18 & "idosos"'),
                                                ("RS0006", "Costa2018", "incluir", ""),
                                                ("RS0008", "Rocha2022", "incluir", "")])
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    ET.fromstring(prisma.gerar_svg(c))
    assert "#quot;" in prisma.gerar_mermaid(c)


# ---------------------------------------------------------------------------
# Correções v1.1: buscas substituídas, "aguardando", inventário, tipo padrão e PNG
# ---------------------------------------------------------------------------
def _inativar_busca(raiz, busca_id):
    from rslib import estado
    est = estado.carregar_estado(raiz)
    est["buscas"] = [{"id": "B01", "fonte": "wos"}, {"id": busca_id, "fonte": "scopus", "ativa": False}]
    estado.salvar_estado(raiz, est)


def test_busca_substituida_fica_fora_dos_identificados(projeto_vazio, capsys):
    from rslib import estado, prisma
    montar_ledger(projeto_vazio)  # registros_unicos ainda cita B02 (dedup não refeito)
    antes = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    _inativar_busca(projeto_vazio, "B02")
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    b = c["bases"]
    assert b["identificados"]["bases"] == 6 and b["identificados"]["por_fonte"] == {"wos": 6}
    assert b["removidos_antes_triagem"]["duplicatas"] == 0
    assert b["removidos_antes_triagem"]["automacao"] == 0      # RS0007 só vinha de B02: saiu do fluxo
    assert (b["a_triar"], b["triados"], b["buscados"], b["avaliados"]) == (6, 6, 4, 3)
    assert c["buscas_inativas"] == {"buscas": ["B02"], "n_registros": 4}
    assert not prisma.invariantes_quebradas(c), prisma.invariantes_quebradas(c)
    assert c["insumos"]["estado.buscas_inativas"] and antes["insumos"]["estado.buscas_inativas"] is None
    assert any("buscas substituídas" in a for a in c["avisos"])
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert codigo == 0 and res["incluidos"] == {"estudos": 2, "relatos": 3}


def test_decisao_de_texto_completo_sobre_busca_substituida_exit2(projeto_vazio, capsys):
    from rslib import estado, prisma
    triagem = [t for t in TRIAGEM] + [("RS0007", "incluir")]
    montar_ledger(projeto_vazio, triagem=triagem, elegibilidade=ELEGIBILIDADE + [("RS0007", "Melo1990", "incluir", "")])
    _inativar_busca(projeto_vazio, "B02")
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    nomes = {i["nome"] for i in prisma.invariantes_quebradas(c)}
    assert "decisoes_de_busca_substituida" in nomes and "elegibilidade_fora_dos_buscados" not in nomes
    assert rodar(capsys, "--dir", projeto_vazio, "prisma")[0] == 2


def test_aguardando_classificacao_tem_caixa_e_fecha_invariante(projeto_vazio):
    from rslib import estado, prisma
    eleg = [("RS0001", "Silva2020", "incluir", ""), ("RS0002", "Souza2019", "aguardando", ""),
            ("RS0006", "Costa2018", "incluir", ""), ("RS0008", "Rocha2022", "incluir", "")]
    montar_ledger(projeto_vazio, elegibilidade=eleg)
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    b = c["bases"]
    assert (b["avaliados"], b["excluidos_elegibilidade"]["total"], b["aguardando_classificacao"], b["incluidos_relatos"]) \
        == (3, 0, 1, 2)
    assert c["outros_metodos"]["aguardando_classificacao"] == 0
    assert not prisma.invariantes_quebradas(c)
    svg = prisma.gerar_svg(c)
    ET.fromstring(svg)
    assert "Relatórios aguardando classificação" in svg and "4.4.5" in svg
    assert "b_avaliados --> b_aguardando" in prisma.gerar_mermaid(c)
    assert "o_aguardando" not in prisma.caixas(c)

    # "incerto" no texto completo continua quebrando: decida (ou marque aguardando) antes
    montar_ledger(projeto_vazio, elegibilidade=[e if e[0] != "RS0002" else ("RS0002", "Souza2019", "incerto", "")
                                                for e in eleg])
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    assert "elegibilidade_fecha" in {i["nome"] for i in prisma.invariantes_quebradas(c)}


def test_aguardando_no_modo_manual(tmp_path, capsys):
    manual = tmp_path / "contagens.json"
    manual.write_text(json.dumps({"bases": {"triados": 10, "excluidos_triagem": 4, "buscados": 6, "nao_recuperados": 0,
                                            "avaliados": 6, "excluidos_elegibilidade": 2, "aguardando_classificacao": 1,
                                            "incluidos_relatos": 3}}), encoding="utf-8")
    codigo, res = rodar(capsys, "prisma", "--manual", manual)
    assert codigo == 0, res
    assert "Relatórios aguardando classificação" in (tmp_path / "prisma.svg").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "prisma_contagens.json").read_text(encoding="utf-8"))["bases"]["aguardando_classificacao"] == 1
    manual.write_text(json.dumps({"bases": {"avaliados": 6, "excluidos_elegibilidade": 2, "incluidos_relatos": 3}}),
                      encoding="utf-8")
    codigo, res = rodar(capsys, "prisma", "--manual", manual, "--saida", tmp_path / "b")
    assert codigo == 2 and res["invariantes"][0]["nome"] == "elegibilidade_fecha"  # sem a caixa: 6 ≠ 5


def _inventario(raiz, recuperados):
    from rslib import esquema
    _escrever(raiz / esquema.ARQ_INVENTARIO_TEXTOS, esquema.COLUNAS_INVENTARIO_TEXTOS,
              [{"chave": k, "existe": "1", "recuperado": v} for k, v in recuperados.items()])


def test_inventario_recuperado_zero_conta_como_nao_recuperado(projeto_vazio):
    from rslib import estado, prisma
    montar_ledger(projeto_vazio)
    _inventario(projeto_vazio, {"Silva2020": "1", "Souza2019": "1", "Costa2018": "0", "Rocha2022": "1"})
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    quebradas = prisma.invariantes_quebradas(c)
    assert [i["nome"] for i in quebradas if i["nome"] == "avaliado_nao_recuperado"] == ["avaliado_nao_recuperado"]
    assert c["bases"]["nao_recuperados"] == 2  # Lima2021 (sem PDF) e Costa2018 (PDF "ok", mas de outro trabalho)

    montar_ledger(projeto_vazio, elegibilidade=[e for e in ELEGIBILIDADE if e[0] != "RS0006"])
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    assert not prisma.invariantes_quebradas(c), prisma.invariantes_quebradas(c)
    assert (c["bases"]["buscados"], c["bases"]["nao_recuperados"], c["bases"]["avaliados"]) == (4, 2, 2)
    assert c["insumos"]["03-textos/inventario_textos.csv"]


def test_inventario_sem_coluna_recuperado_mantem_regra_antiga(projeto_vazio):
    from rslib import esquema, estado, prisma
    montar_ledger(projeto_vazio)
    _escrever(projeto_vazio / esquema.ARQ_INVENTARIO_TEXTOS, ["chave", "id_rs", "arquivo", "existe"],
              [{"chave": "Costa2018", "existe": "0"}])
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    assert c["bases"]["nao_recuperados"] == 1 and not prisma.invariantes_quebradas(c)


def test_tipo_padrao_scr_para_escopo_e_mapa(projeto_vazio, capsys):
    from rslib import estado
    montar_ledger(projeto_vazio)
    est = estado.carregar_estado(projeto_vazio)
    est["projeto"]["tipo_revisao"] = "escopo"
    estado.salvar_estado(projeto_vazio, est)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert codigo == 0 and res["tipo"] == "scr"
    svg = (projeto_vazio / "07-relatorio" / "prisma.svg").read_text(encoding="utf-8")
    assert "Fontes de evidência incluídas" in svg
    with open(projeto_vazio / "07-relatorio" / "checklist_prisma.csv", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) < 27  # checklist do PRISMA-ScR
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma", "--tipo", "2020")
    assert codigo == 0 and res["tipo"] == "2020"
    est = estado.carregar_estado(projeto_vazio)
    est["projeto"]["tipo_revisao"] = "efetividade_meta"
    estado.salvar_estado(projeto_vazio, est)
    assert rodar(capsys, "--dir", projeto_vazio, "prisma")[1]["tipo"] == "2020"
    from rslib import prisma
    assert prisma.tipo_padrao({"projeto": {"tipo_revisao": "mapa_evidencias"}}) == "scr"
    assert prisma.tipo_padrao(None) == "2020"


def test_prisma_png_gerado_do_svg(projeto_vazio, capsys):
    pytest.importorskip("pymupdf")
    montar_ledger(projeto_vazio)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    png = projeto_vazio / "07-relatorio" / "prisma.png"
    assert codigo == 0 and png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert "07-relatorio/prisma.png" in res["arquivos"]
    evento = [e for e in ler_jsonl(projeto_vazio / "rs_log.jsonl") if e["evento"] == "prisma_gerado"][-1]
    assert "07-relatorio/prisma.png" in {a["caminho"] for a in evento["artefatos"]}
    svg = (projeto_vazio / "07-relatorio" / "prisma.svg").read_text(encoding="utf-8")
    assert "marker-end" not in svg and '<path d="M' in svg  # pontas de seta desenhadas (saem no PNG)
    png.unlink()  # PNG apagado: a próxima execução regenera em vez de dizer "reexecução"
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert res["reexecucao"] is False and png.exists()


def test_prisma_sem_pymupdf_so_avisa(projeto_vazio, capsys, monkeypatch):
    from rslib import prisma
    montar_ledger(projeto_vazio)
    monkeypatch.setattr(prisma, "_carregar_pymupdf", lambda: None)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert codigo == 0 and any("prisma.png não gerado" in a for a in res["avisos"])
    assert not (projeto_vazio / "07-relatorio" / "prisma.png").exists()
    assert (projeto_vazio / "07-relatorio" / "prisma.svg").exists()
    assert rodar(capsys, "--dir", projeto_vazio, "prisma")[1]["reexecucao"] is True


def test_regressao_aviso_de_cluster_inativo_nao_manda_rodar_dedup_se_ja_marcado(projeto_vazio):
    """Com a flag busca_inativa (dedup já rodou), o aviso só informa; sem ela, pede o dedup."""
    from rslib import esquema, estado, prisma
    montar_ledger(projeto_vazio)
    _inativar_busca(projeto_vazio, "B02")  # RS0007 só tinha B02-00004
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    sem_flag = [a for a in c["avisos"] if "RS0007" in a]
    assert sem_flag and "rode `rs.py dedup`" in sem_flag[0]

    caminho = projeto_vazio / esquema.ARQ_UNICOS
    with open(caminho, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
        colunas = list(linhas[0].keys())
    for l in linhas:
        if l["id_rs"] == "RS0007":
            l["flags"] = esquema.FLAG_BUSCA_INATIVA
    _escrever(caminho, colunas, linhas)
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    marcados = [a for a in c["avisos"] if esquema.FLAG_BUSCA_INATIVA in a]
    assert marcados and "ficaram fora do fluxo" in marcados[0]
    assert not any("dedup" in a for a in c["avisos"]), c["avisos"]
    assert not prisma.invariantes_quebradas(c)


# ---------------------------------------------------------------------------
# Correções v1.2: rótulo da fonte genérica, busca truncada e escrita atômica
# ---------------------------------------------------------------------------
def test_regressao_rotulo_da_fonte_generica_usa_plataforma_ou_busca_id(projeto_vazio, capsys):
    from rslib import estado, prisma
    registros = [(i, b, "generico" if b == "B02" else f, m) for i, b, f, m in REGISTROS]
    montar_ledger(projeto_vazio, registros=registros)
    est = estado.carregar_estado(projeto_vazio)
    est["buscas"] = [{"id": "B01", "fonte": "wos"}, {"id": "B02", "fonte": "generico", "plataforma": "planilha de teste"}]
    estado.salvar_estado(projeto_vazio, est)
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    assert c["bases"]["identificados"]["por_fonte"] == {"wos": 6, "planilha de teste": 4}
    assert not prisma.invariantes_quebradas(c)
    svg = prisma.gerar_svg(c)
    assert "planilha de teste (n = 4)" in svg and "generico" not in svg
    est = estado.carregar_estado(projeto_vazio)
    del est["buscas"][1]["plataforma"]
    estado.salvar_estado(projeto_vazio, est)
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    assert c["bases"]["identificados"]["por_fonte"] == {"wos": 6, "B02": 4}
    codigo, _ = rodar(capsys, "--dir", projeto_vazio, "prisma")
    with open(projeto_vazio / "07-relatorio" / "checklist_prisma.csv", encoding="utf-8") as f:
        item6 = next(l for l in csv.DictReader(f) if l["item"] == "6")
    assert codigo == 0 and "B02 (data?)" in item6["evidencia_no_projeto"]


def test_regressao_busca_truncada_ativa_marca_rascunho_com_motivo(projeto_vazio, capsys):
    from rslib import esquema, estado, prisma
    montar_ledger(projeto_vazio)
    est = estado.carregar_estado(projeto_vazio)
    est["buscas"] = [{"id": "B01", "fonte": "wos", esquema.CAMPO_BUSCA_TRUNCADA: True}, {"id": "B02", "fonte": "scopus"}]
    estado.salvar_estado(projeto_vazio, est)
    c = prisma.calcular(projeto_vazio, estado.carregar_estado(projeto_vazio))
    assert c["rascunho"] is True and c["buscas_truncadas"] == ["B01"] and c["pendencias_abertas"] == []
    assert c["motivos_rascunho"] == ["busca truncada: B01"] and c["insumos"]["estado.buscas_truncadas"]
    assert any("B01" in a and "truncados" in a for a in c["avisos"])
    assert "Buscas truncadas: B01" in prisma.gerar_mermaid(c)
    codigo, res = rodar(capsys, "--dir", projeto_vazio, "prisma")
    assert codigo == 0 and res["rascunho"] is True and res["motivos_rascunho"] == ["busca truncada: B01"]
    evento = [e for e in ler_jsonl(projeto_vazio / "rs_log.jsonl") if e["evento"] == "prisma_gerado"][-1]
    assert evento["dados"]["buscas_truncadas"] == ["B01"]


@pytest.mark.skipif(__import__("os").name == "nt", reason="permissões POSIX")
def test_regressao_saidas_do_prisma_com_permissao_de_arquivo_comum(projeto_vazio, capsys):
    import os
    import stat
    from rslib import estado
    montar_ledger(projeto_vazio)
    assert rodar(capsys, "--dir", projeto_vazio, "prisma")[0] == 0
    for nome in ("prisma_contagens.json", "prisma.svg", "prisma.mermaid", "checklist_prisma.csv"):
        assert stat.S_IMODE(os.stat(projeto_vazio / "07-relatorio" / nome).st_mode) == estado.modo_arquivo_padrao(), nome
    assert not [p for p in (projeto_vazio / "07-relatorio").iterdir() if p.name.endswith(".tmp")]
