"""Testes dos importadores (rs.py importar) com mini-exportações sintéticas.

As fixtures em tests/fixtures/importar/ imitam os formatos reais (BOM, CRLF,
linhas de continuação, chaves aninhadas, autores com '|', pares com vírgula,
reticências do Scholar, latin-1 com ';' da CAPES). Planilhas são geradas no
teste com openpyxl para não versionar binários.
"""

import argparse
import json
import os
from pathlib import Path

import pytest

from conftest import FIXTURES, SKILL, ler_jsonl

FIX = FIXTURES / "importar"


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------
def converter(nome, **kw):
    from rslib.importar import cli
    return cli.converter(FIX / nome if isinstance(nome, str) else nome, **kw)


def por_id(conv):
    return {r["id_fonte"]: r for r in conv.registros}


def parser():
    from rslib.importar import cli
    p = argparse.ArgumentParser(prog="rs.py")
    p.add_argument("--dir", default=None)
    sub = p.add_subparsers(dest="comando")
    cli.registrar(sub)
    return p


def rodar(capsys, *argv):
    args = parser().parse_args(list(argv))
    codigo = args.func(args)
    saida = capsys.readouterr().out.strip().splitlines()
    return codigo, json.loads(saida[-1])


def ler_registros_csv(raiz):
    import csv
    with open(raiz / "dados/registros.csv", encoding="utf-8", newline="") as f:
        leitor = csv.reader(f)
        cabecalho = next(leitor)
        return cabecalho, [dict(zip(cabecalho, l)) for l in leitor]


def eventos(raiz, tipo):
    return [e for e in ler_jsonl(raiz / "rs_log.jsonl") if e["evento"] == tipo]


@pytest.fixture
def xlsx_wos(tmp_path):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    df = pd.DataFrame([
        {"Publication Type": "J", "Authors": "Almeida, Beatriz Costa; Rocha, Tiago", "Article Title": "Excel record one",
         "Article Title - SciELO": None, "Source Title": "FICTIONAL JOURNAL", "Volume": 14, "Issue": 4.0,
         "Start Page": None, "End Page": None, "Article Number": 351, "DOI": "10.9999/XLS.1", "Document Type": "Article",
         "Publication Year": 2024, "Abstract": "Resumo planilha.", "Addresses": "[Almeida, Beatriz Costa] Univ Ficticia, Recife, Brazil",
         "Affiliations": "Universidade Ficticia", "Times Cited, WoS Core": 2, "Language": "English",
         "Author Keywords": "a; b", "UT (Unique WOS ID)": "WOS:000000000000099", "Date of Export": "2025-02-11"},
        {"Publication Type": "J", "Authors": None, "Group Authors": "Consortium of Fictional Studies",
         "Article Title": "Excel record two", "Source Title": "FICTIONAL JOURNAL", "Volume": None, "Issue": None,
         "Start Page": 10, "End Page": 20, "DOI": None, "Document Type": "Review", "Publication Year": 2022.0,
         "UT (Unique WOS ID)": "WOS:000000000000098"},
        {c: None for c in ["Publication Type", "Authors", "Article Title"]},
    ])
    caminho = tmp_path / "Web of Science.xls.xlsx"
    df.to_excel(caminho, index=False)
    return caminho


@pytest.fixture
def xlsx_capesr(tmp_path):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    df = pd.DataFrame([
        {"ano_base": "2000", "ies": "PONTIFÍCIA UNIVERSIDADE FICTÍCIA", "area": "ADMINISTRAÇÃO",
         "nome_programa": "CIÊNCIAS CONTÁBEIS", "tipo": "Mestrado", "titulo": "Planejamento tributário rural",
         "resumo": "Resumo.", "idioma": "Português", "autoria": "MANOEL DOS REIS E SILVA", "orientacao": "ORIENTADOR FICTÍCIO",
         "regiao": "SUDESTE", "uf": "SP"},
        {"ano_base": 2011, "ies": "UNIVERSIDADE FICTÍCIA", "area": "DIREITO", "nome_programa": "DIREITO",
         "tipo": "Doutorado", "titulo": "Transação tributária", "resumo": None, "idioma": "Português",
         "autoria": "ANA DE SOUZA", "orientacao": None, "regiao": "SUL", "uf": "RS"},
    ])
    caminho = tmp_path / "bdtd.xlsx"
    df.to_excel(caminho, index=False)
    return caminho


# ---------------------------------------------------------------------------
# Detecção por assinatura e contagens
# ---------------------------------------------------------------------------
CASOS = [
    ("wos_plaintext.txt", "wos", "wos_txt", 5),
    ("wos_scielo_tab.txt", "wos", "wos_tsv", 5),
    ("wos.bib", "wos", "wos_bib", 3),
    ("zotero.bib", "generico", "bibtex", 2),
    ("scopus.csv", "scopus", "scopus_csv", 5),
    ("scopus_antigo.csv", "scopus", "scopus_csv", 2),
    ("openalex.csv", "openalex", "openalex_csv", 5),
    ("openalex_works.jsonl", "openalex", "openalex_json", 3),
    ("openalex_pagina.json", "openalex", "openalex_json", 2),
    ("pop.csv", "pop", "pop_csv", 4),
    ("scielo_portal.csv", "scielo", "scielo_csv", 5),
    ("zotero.csv", "zotero", "zotero_csv", 5),
    ("zotero.ris", "ris", "ris", 4),
    ("scopus.ris", "ris", "ris", 2),
    ("capes_dados_abertos.csv", "capes", "capes_csv", 3),
    ("bdtd.csv", "bdtd", "bdtd_csv", 2),
    ("bdtd_api.json", "bdtd", "bdtd_json", 2),
    ("generico_apelidos.csv", "generico", "generico", 2),
]


@pytest.mark.parametrize("nome,familia,formato,n", CASOS)
def test_detecta_formato_e_conta(nome, familia, formato, n):
    from rslib.importar import detectar
    det = detectar.detectar(FIX / nome)
    assert (det.familia, det.formato) == (familia, formato), det.motivo
    conv = converter(nome)
    assert len(conv.registros) == n
    for r in conv.registros:
        assert r["titulo"] and not r["titulo"].startswith("\ufeff")
        assert "\r" not in "".join(r.values())
        assert r["resumo_truncado"] in {"0", "1"}


def test_detecta_planilhas(xlsx_wos, xlsx_capesr):
    from rslib.importar import detectar
    assert detectar.detectar(xlsx_wos).formato == "wos_xls"
    assert detectar.detectar(xlsx_capesr).formato == "capesr"


def test_registro_tem_todas_as_colunas():
    from rslib import esquema
    from rslib.importar import generico
    conv = converter("wos_plaintext.txt")
    esperadas = set(generico.CAMPOS_CONTEUDO) | {"fonte", "linha_origem"}
    assert set(conv.registros[0]) == esperadas
    assert esperadas <= set(esquema.COLUNAS_REGISTROS)


# ---------------------------------------------------------------------------
# Web of Science
# ---------------------------------------------------------------------------
def test_wos_plaintext_continuacoes_e_campos():
    conv = converter("wos_plaintext.txt")
    r = por_id(conv)
    a = r["WOS:000000000000001"]
    assert a["titulo"] == "Tax amnesty programs and compliance: evidence from municipal panels"
    assert a["autores"] == "Almeida, Beatriz Costa | Rocha, Tiago | Nakamura, Ken"  # AF > AU
    assert a["primeiro_autor_sobrenome"] == "Almeida" and a["n_autores"] == "3"
    assert a["palavras_chave"] == "tax amnesty; compliance; municipal finance; panel data"  # sem Keywords Plus
    assert a["pais_afiliacao"] == "Brazil; USA"
    assert a["instituicao"] == "Universidade Ficticia do Sul; State University of Example"
    assert a["resumo"] == "We study repeated tax amnesty programs using a synthetic panel of municipalities."
    assert (a["volume"], a["numero"], a["paginas"], a["citado_por"]) == ("12", "3", "101-130", "3")
    assert (a["ano"], a["tipo_publicacao"], a["idioma"], a["doi"]) == ("2021", "artigo", "en", "10.9999/jfpf.2021.0003")

    b = r["WOS:000000000000002"]
    assert b["ano"] == "2024" and b["paginas"] == "e2024001"  # ano de EA; número do artigo
    assert b["tipo_publicacao"] == "revisao" and b["idioma"] == "pt" and b["doi"] == ""

    c = r["WOS:000000000000003"]
    assert c["autores"] == "Grupo de Estudos Fiscais Ficticios"  # autoria institucional não é invertida
    assert c["primeiro_autor_sobrenome"] == "Grupo de Estudos Fiscais Ficticios"
    assert c["tipo_publicacao"] == "editorial"

    assert r["WOS:000000000000004"]["doi"] == "10.9999/fct.2020.abc"
    assert r["WOS:000000000000004"]["tipo_publicacao"] == "evento"
    assert r["SCIELO:S0000-00002019000100001"]["fonte"] == "scielo"
    assert r["WOS:000000000000001"]["fonte"] == "wos"
    assert conv.data_busca == "2025-01-10"
    assert [x["linha_origem"] for x in conv.registros] == ["1", "2", "3", "4", "5"]


def test_wos_tsv_scielo_crlf_bom_e_campos_alternativos():
    conv = converter("wos_scielo_tab.txt")
    r = por_id(conv)
    a = r["SCIELO:S0101-00002014000200004"]
    assert a["fonte"] == "scielo"
    assert a["resumo"] == 'This paper evaluates "installment programs and revenue.'  # aspas soltas preservadas
    assert a["palavras_chave"] == "tax installment; revenues; parcelamento; arrecadação"
    assert a["pais_afiliacao"] == "Brasil" and a["paginas"] == "323-350"
    b = r["SCIELO:S1519-00002023000300502"]
    assert b["titulo_alt"] == "Parcelamento tributário como determinante da agressividade fiscal"
    assert b["autores"] == "Marques, Luana Lopes da Silva | Macedo, Lucio de Souza"
    assert b["doi"] == "10.9999/1808-057x20231754.en"
    assert r["SCIELO:S0000-11112018000100001"]["resumo"] == "Resumo apenas no campo alternativo."
    assert r["SCIELO:S0000-11112018000100001"]["tipo_publicacao"] == "revisao"
    assert r["SCIELO:S0000-22222016000200002"]["tipo_publicacao"] == "artigo"  # brief-report
    assert r["SCIELO:S0000-22222016000200002"]["idioma"] == "es"


def test_wos_bibtex_chaves_aninhadas_e_latex():
    conv = converter("wos.bib")
    r = por_id(conv)
    a = r["WOS:000000000000011"]
    assert a["titulo"] == '"It must not disturb": tax installment in Brazil & who benefits?'
    assert a["autores"] == "Viana, Renato Kenji | Campos, Mariana | Estevão, Henrique Soares"
    assert a["resumo"] == "This exploratory study [Anonymous] aims to understand who benefits from 'special' installment programs."
    assert a["pais_afiliacao"] == "Brazil"  # Address (editora) não entra
    assert a["palavras_chave"] == "PERT; Tax regularization; Tax installment"
    assert (a["citado_por"], a["paginas"], a["numero"]) == ("1", "855-878", "1")
    assert conv.data_busca == "2026-04-26"
    b = r["WOS:000000000000012"]
    assert b["autores"] == "Lindström, Petra | José da Silva Filho, João | Grupo de Pesquisa Fiscal and Tributário"
    assert b["n_autores"] == "3" and b["paginas"] == "1-10"
    assert b["titulo"] == "Nested Braces Inside titles: a stress test"
    assert b["doi"] == "10.9999/fel.2020.12"
    c = r["WOS:000000000000013"]
    assert c["tipo_publicacao"] == "capitulo" and c["veiculo"] == "FICTIONAL HANDBOOK OF TAX BEHAVIOR"


def test_wos_planilha(xlsx_wos):
    conv = converter(xlsx_wos)
    assert conv.deteccao.formato == "wos_xls"
    assert len(conv.registros) == 2 and conv.n_descartados == 0  # linha vazia não conta como registro
    r = por_id(conv)
    a = r["WOS:000000000000099"]
    assert (a["volume"], a["numero"], a["paginas"], a["ano"], a["citado_por"]) == ("14", "4", "351", "2024", "2")
    assert a["autores"] == "Almeida, Beatriz Costa | Rocha, Tiago" and a["doi"] == "10.9999/xls.1"
    assert a["pais_afiliacao"] == "Brazil"
    b = r["WOS:000000000000098"]
    assert b["autores"] == "Consortium of Fictional Studies" and b["paginas"] == "10-20" and b["ano"] == "2022"
    assert conv.data_busca == "2025-02-11"


# ---------------------------------------------------------------------------
# Scopus
# ---------------------------------------------------------------------------
def test_scopus_nomes_completos_resumo_multilinha_e_tipos():
    r = por_id(converter("scopus.csv"))
    a = r["2-s2.0-00000000001"]
    assert a["autores"] == "Hossain Chowdhury, Rafiq | Karim, Arif | Boyd, Wendel"  # ids entre parênteses removidos
    assert a["primeiro_autor_sobrenome"] == "Hossain Chowdhury"
    assert a["resumo"] == "This study explored, with care, the online education experiences of kindergarten."
    assert a["pais_afiliacao"] == "Bangladesh; Australia"
    assert a["palavras_chave"] == "COVID-19; kindergarten"  # sem Index Keywords
    assert r["2-s2.0-00000000002"]["resumo"] == ""  # [No abstract available]
    assert r["2-s2.0-00000000002"]["tipo_publicacao"] == "outro"  # Conference review não é revisão
    assert r["2-s2.0-00000000003"]["tipo_publicacao"] == "capitulo"
    assert r["2-s2.0-00000000003"]["paginas"] == "45-67" and r["2-s2.0-00000000003"]["idioma"] == "en"
    assert r["2-s2.0-00000000004"]["paginas"] == "e15" and r["2-s2.0-00000000004"]["tipo_publicacao"] == "revisao"
    assert r["2-s2.0-00000000005"]["tipo_publicacao"] == "errata"


def test_scopus_autores_antigos_com_iniciais():
    r = por_id(converter("scopus_antigo.csv"))
    assert r["2-s2.0-00000000010"]["autores"] == "Lindqvist, M. | Okafor, A."
    assert r["2-s2.0-00000000011"]["primeiro_autor_sobrenome"] == "Weber"
    assert r["2-s2.0-00000000011"]["tipo_publicacao"] == "editorial"


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------
def test_openalex_csv_barras_e_tipos():
    conv = converter("openalex.csv")
    r = por_id(conv)
    a = r["W1000000001"]
    assert a["autores"] == "Bortolini, Brígida Bruno | Tessaro, Viviane | Molin, Kátia Dal"
    assert a["doi"] == "10.9999/2176-9036.2025v17" and a["pais_afiliacao"] == "BR"
    assert a["instituicao"] == "Universidade Fictícia de Santa Catarina"
    assert a["palavras_chave"] == ""  # primary_topic não vira palavra-chave
    assert r["W1000000002"]["tipo_publicacao"] == "tese" and r["W1000000002"]["pais_afiliacao"] == "BR; NL"
    assert r["W1000000002"]["resumo"] == ""
    assert r["W1000000003"]["tipo_publicacao"] == "preprint"
    assert r["W1000000003"]["autores"] == "Silva, João da Filho"
    assert r["W1000000004"]["tipo_publicacao"] == "capitulo"
    assert r["W1000000005"]["tipo_publicacao"] == "outro"  # peer-review
    assert any("retratados" in a for a in conv.avisos)


def test_openalex_jsonl_resumo_invertido_e_linha_truncada():
    conv = converter("openalex_works.jsonl")
    r = por_id(conv)
    a = r["W2000000001"]
    assert a["resumo"] == "Amnesties reduce compliance in the long compliance run."
    assert a["palavras_chave"] == "tax amnesty; compliance"
    assert a["pais_afiliacao"] == "BR; US"
    assert a["paginas"] == "11-29" and a["doi"] == "10.9999/tax.2021.1"
    assert a["url"] == "https://example.org/artigo/1"
    assert r["W2000000002"]["resumo"] == "" and r["W2000000002"]["tipo_publicacao"] == "revisao"
    assert any("truncada" in x for x in conv.avisos)
    assert any("retratados" in x for x in conv.avisos)


def test_openalex_json_pagina_da_api():
    conv = converter("openalex_pagina.json")
    assert [r["id_fonte"] for r in conv.registros] == ["W2000000004", "W2000000005"]
    assert conv.registros[1]["tipo_publicacao"] == "livro"


def test_openalex_jsonl_invalido_no_meio_e_erro(tmp_path):
    from rslib.importar.detectar import ErroImportacao
    linhas = (FIX / "openalex_works.jsonl").read_text(encoding="utf-8").splitlines()
    arquivo = tmp_path / "quebrado.jsonl"
    arquivo.write_text("\n".join([linhas[0], "{quebrado", linhas[1]]) + "\n", encoding="utf-8")
    with pytest.raises(ErroImportacao):
        converter(arquivo)


# ---------------------------------------------------------------------------
# Publish or Perish / Scholar
# ---------------------------------------------------------------------------
def test_pop_reticencias_autores_cortados_e_tipos():
    conv = converter("pop.csv")
    r = {x["titulo"]: x for x in conv.registros}
    a = r["Transação e arbitragem no âmbito tributário"]
    assert a["resumo_truncado"] == "1" and a["id_fonte"] == "GS:1111111111111111111"
    assert a["autores"] == "Moraes, HB" and a["ano"] == "2007"
    b = r["Cyberbullying in fictional schools"]
    assert b["autores"] == "Silveira, PK | Mahmoud, J | Carvalhal, M" and b["n_autores"] == "4"
    assert b["tipo_publicacao"] == "" and b["tipo_publicacao_orig"] == "PDF"  # tipo do link, não do documento
    assert b["doi"] == "10.9999/j.1469-7610.2007.01846.x" and b["resumo_truncado"] == "1"
    c = r["Planejamento tributário em cooperativas"]
    assert c["autores"] == "Seguro, LC | Formiga, H" and c["n_autores"] == "3"
    assert c["ano"] == "" and c["tipo_publicacao"] == "outro" and c["resumo_truncado"] == "0"
    d = r["Educação fiscal: um livro fictício"]
    assert d["tipo_publicacao"] == "livro" and d["resumo_truncado"] == "0"
    assert d["autores"] == "de Oliveira, JF | Libório, JC"
    assert conv.data_busca == "2025-12-04"


# ---------------------------------------------------------------------------
# SciELO portal
# ---------------------------------------------------------------------------
def test_scielo_portal_pares_pid_e_fonte():
    conv = converter("scielo_portal.csv")
    regs = conv.registros
    assert regs[0]["id_fonte"] == regs[2]["id_fonte"] == "SCIELO:S0103-00002024000200208"  # coleções spa/scl
    assert regs[0]["autores"] == "Gomes, Cristina Sá | Silva, Alana Gomes da | Barros, Marisa Bento de Azevedo"
    assert (regs[0]["volume"], regs[0]["numero"], regs[0]["paginas"]) == ("48", "141", "")
    assert regs[0]["idioma"] == "pt" and regs[0]["tipo_publicacao"] == ""  # portal não informa tipo
    assert regs[0]["url"].startswith("http://www.scielo.example/") and not regs[0]["url"].endswith(" ")
    assert regs[1]["autores"] == "Ramos Duarte, Silvia | Martínez Robles, Elena"
    assert regs[1]["primeiro_autor_sobrenome"] == "Ramos Duarte" and regs[1]["paginas"] == "11-22"
    assert regs[1]["idioma"] == "es"
    assert regs[4]["autores"] == "Instituto Fictício de Pesquisa"


# ---------------------------------------------------------------------------
# Zotero e RIS
# ---------------------------------------------------------------------------
def test_zotero_csv_ignora_key_tipos_e_doi_em_extra():
    regs = converter("zotero.csv").registros
    assert all(r["id_fonte"] == "" for r in regs)  # Key nunca vira id_fonte (PLUCK001 aparece duas vezes)
    assert regs[0]["idioma"] == "pt" and regs[0]["palavras_chave"] == "Adolescente; Covid-19; Food insecurity"
    assert regs[1]["tipo_publicacao"] == "capitulo" and regs[1]["paginas"] == "10-30"
    assert regs[2]["tipo_publicacao"] == "dissertacao" and regs[2]["instituicao"] == "Universidade Fictícia"
    assert regs[3]["doi"] == "10.9999/td.2021.7" and regs[3]["tipo_publicacao"] == "relatorio"
    assert regs[3]["autores"] == "Instituto Fictício de Pesquisa Econômica" and regs[3]["idioma"] == "pt"
    assert regs[4]["doi"] == "10.31235/osf.io/abcd1" and regs[4]["tipo_publicacao"] == "preprint"


def test_ris_zotero_continuacao_e_tese():
    regs = converter("zotero.ris").registros
    a = regs[0]
    assert a["resumo"] == "We study repeated amnesties continuing on a second line."
    assert a["doi"] == "10.9999/rff.2021.3" and a["palavras_chave"] == "amnesty; revenue"
    assert (a["ano"], a["idioma"], a["paginas"], a["fonte"]) == ("2021", "pt", "101-130", "ris")
    assert regs[1]["tipo_publicacao"] == "tese" and regs[1]["instituicao"] == "Universidade Fictícia"
    assert regs[2]["tipo_publicacao"] == "capitulo"
    assert regs[3]["doi"] == "10.9999/rel.2020.1" and regs[3]["autores"] == "Instituto Fictício"


def test_ris_scopus_define_fonte_e_id():
    regs = converter("scopus.ris").registros
    assert [r["fonte"] for r in regs] == ["scopus", "scopus"]
    assert regs[0]["id_fonte"] == "2-s2.0-00000000001" and regs[1]["tipo_publicacao"] == "evento"


def test_bibtex_generico():
    regs = converter("zotero.bib").registros
    assert regs[0]["titulo"] == "Parcelamentos tributários no Brasil" and regs[0]["tipo_publicacao"] == "tese"
    assert regs[0]["autores"] == "Silva, Joana | Instituto Ficticio" and regs[0]["idioma"] == "pt"
    assert regs[1]["doi"] == "10.9999/osf.io/abcd1" and regs[1]["fonte"] == "generico"


# ---------------------------------------------------------------------------
# CAPES e BDTD
# ---------------------------------------------------------------------------
def test_capes_dados_abertos_latin1_ponto_e_virgula():
    conv = converter("capes_dados_abertos.csv")
    assert any("UTF-8" in a for a in conv.avisos)
    r = por_id(conv)
    a = r["CAPES:9000001"]
    assert a["autores"] == "Silva, Manoel dos Reis e" and a["titulo"] == "PARCELAMENTOS TRIBUTÁRIOS E ARRECADAÇÃO"
    assert (a["ano"], a["tipo_publicacao"], a["idioma"]) == ("2019", "dissertacao", "pt")
    assert a["palavras_chave"] == "PARCELAMENTO; REFIS" and a["pais_afiliacao"] == "Brazil"
    assert a["instituicao"] == "Universidade Federal Fictícia" and a["veiculo"] == "Ciências Contábeis"
    b = r["CAPES:9000002"]
    assert b["tipo_publicacao"] == "tese" and b["resumo"] == "Amnesties in municipalities." and b["ano"] == "2020"
    assert b["autores"] == "Costa-Lima, Ana Maria da"
    c = r["CAPES:9000003"]
    assert c["tipo_publicacao"] == "dissertacao" and c["ano"] == "2021" and c["idioma"] == "en"


def test_capesr_planilha(xlsx_capesr):
    conv = converter(xlsx_capesr)
    assert conv.familia == "capes"
    a, b = conv.registros
    assert a["autores"] == "Silva, Manoel dos Reis e" and a["tipo_publicacao"] == "dissertacao" and a["ano"] == "2000"
    assert b["ano"] == "2011" and b["tipo_publicacao"] == "tese" and a["fonte"] == "capes"


def test_bdtd_csv_e_api():
    a, b = converter("bdtd.csv").registros
    assert a["tipo_publicacao"] == "dissertacao" and a["palavras_chave"] == "REFIS; empresas" and a["fonte"] == "bdtd"
    assert b["tipo_publicacao"] == "tese" and b["resumo"] == "Only English abstract."
    x, y = converter("bdtd_api.json").registros
    assert x["id_fonte"] == "BDTD:UFXX_0123456789abcdef" and x["tipo_publicacao"] == "tese"
    assert x["palavras_chave"] == "Federalismo; Finanças públicas" and x["idioma"] == "pt"
    assert y["autores"] == "Rocha, Tiago" and y["tipo_publicacao"] == "dissertacao" and y["idioma"] == "en"


# ---------------------------------------------------------------------------
# Genérico
# ---------------------------------------------------------------------------
def test_generico_com_mapa():
    mapa = json.loads((FIX / "mapa_generico.json").read_text(encoding="utf-8"))
    conv = converter("generico.csv", mapa=mapa)
    a, b, c = conv.registros
    assert a["autores"] == "Souza, Ana | Lima, Pedro" and a["doi"] == "10.9999/aval.2019.1"
    assert a["palavras_chave"] == "política; avaliação; municípios"
    assert b["autores"] == "Instituto Fictício" and b["doi"] == ""
    assert c["doi"] == "10.9999/terc.2021" and c["linha_origem"] == "3"
    assert all(r["fonte"] == "generico" for r in conv.registros)


def test_generico_por_apelidos_avisa():
    conv = converter("generico_apelidos.csv")
    assert any("apelido" in a for a in conv.avisos)
    assert conv.registros[0]["autores"] == "Almeida, Beatriz | Rocha, Tiago"
    assert conv.registros[0]["tipo_publicacao"] == "artigo" and conv.registros[1]["tipo_publicacao"] == ""


def test_generico_erros_de_mapa(tmp_path):
    from rslib.importar.detectar import ErroImportacao
    with pytest.raises(ErroImportacao, match="não existem"):
        converter("generico.csv", mapa={"colunas": {"titulo": "Nome do trabalho", "inventado": "x"}})
    with pytest.raises(ErroImportacao, match="ausentes"):
        converter("generico.csv", mapa={"titulo": "Coluna que não existe"})
    sem_titulo = tmp_path / "sem_titulo.csv"
    sem_titulo.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ErroImportacao, match="--mapa"):
        converter(sem_titulo)
    with pytest.raises(ErroImportacao, match="só vale"):
        converter("wos.bib", mapa={"titulo": "Title"})


def test_fonte_forcada():
    from rslib.importar.detectar import ErroImportacao
    conv = converter("wos_plaintext.txt", fonte="scielo")
    assert {r["fonte"] for r in conv.registros} == {"scielo"}
    with pytest.raises(ErroImportacao, match="não lê"):
        converter("wos_plaintext.txt", fonte="scopus")
    assert {r["fonte"] for r in converter("zotero.ris", fonte="zotero").registros} == {"zotero"}


# ---------------------------------------------------------------------------
# Funções puras
# ---------------------------------------------------------------------------
def test_funcoes_de_normalizacao():
    from rslib.importar import generico, openalex, pop, scielo
    assert generico.limpar_latex(r"Hedstr{\"o}m {\'e} \c{c} {[}x{]} \& ``a'' `b'") == "Hedström é ç [x] & \"a\" 'b'"
    assert generico.autores_bibtex("A, B and {C and D} and E, F") == ["A, B", "C and D", "E, F"]
    assert openalex.reconstruir_resumo({"b": [1], "a": [0], "c": [2]}) == "a b c"
    assert openalex.reconstruir_resumo('{"x": [0]}') == "x" and openalex.reconstruir_resumo(None) == ""
    assert scielo.pid_de(' "S0103-00002024000200208-spa"') == "SCIELO:S0103-00002024000200208"
    assert scielo.decompor_fonte("Revista; 11(1); 11-22") == ("11", "1", "11-22")
    assert scielo.autores_em_pares("Sob, Nome, Sob Dois, Nome") == ["Sob, Nome", "Sob Dois, Nome"]
    assert generico.idioma_de("pt-BR") == "pt" and generico.idioma_de("Turkish") == "tr" and generico.idioma_de("") == ""
    assert generico.tipo_de("journalArticle") == "artigo" and generico.tipo_de("") == ""
    assert generico.tipo_de("DISSERTAÇÃO") == "dissertacao" and generico.tipo_de("Book Review") == "editorial"
    assert pop.autores_pop("A Silva, B Souza…") == (["A Silva", "B Souza"], True)
    assert generico.inteiro_texto("12.0") == "12" and generico.inteiro_texto("1,050") == "1050"
    assert generico.inteiro_texto("n/a") == ""
    assert generico.nome_proprio("ANA DA COSTA-LIMA") == "Ana da Costa-Lima"
    assert generico.pais_de_endereco("[A; B] Univ X, Austin, TX 78712 USA.") == "USA"
    assert generico.doi_de("", "Citation Key: x\nDOI: 10.1234/ABC") == "10.1234/abc"


# ---------------------------------------------------------------------------
# Comando no projeto
# ---------------------------------------------------------------------------
def test_importar_grava_registros_bruto_estado_e_evento(projeto_vazio, capsys):
    from rslib import esquema, estado
    raiz = projeto_vazio
    codigo, resumo = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "wos_plaintext.txt"),
                           "--busca-id", "B01", "--estrutura", "PICOC")
    assert codigo == 0 and resumo["ok"] and resumo["n_importados"] == 5
    cabecalho, linhas = ler_registros_csv(raiz)
    assert cabecalho == esquema.COLUNAS_REGISTROS
    assert [l["id_registro"] for l in linhas] == [f"B01-{i:05d}" for i in range(1, 6)]
    assert {l["busca_id"] for l in linhas} == {"B01"} and {l["metodo_identificacao"] for l in linhas} == {"base"}
    assert {l["estrutura"] for l in linhas} == {"PICOC"}
    assert {l["arquivo_origem"] for l in linhas} == {"01-busca/brutos/wos_plaintext.txt"}
    assert all(l["importado_em"] for l in linhas)
    bruto = raiz / "01-busca/brutos/wos_plaintext.txt"
    assert estado.sha256_arquivo(bruto) == estado.sha256_arquivo(FIX / "wos_plaintext.txt")

    est = estado.carregar_estado(raiz)
    busca = est["buscas"][0]
    assert (busca["id"], busca["fonte"], busca["importada"], busca["n_importado"]) == ("B01", "wos", True, 5)
    assert busca["arquivo"] == "01-busca/brutos/wos_plaintext.txt" and busca["executada_em"] == "2025-01-10"
    ev = eventos(raiz, "importacao")
    assert len(ev) == 1
    assert {a["caminho"] for a in ev[0]["artefatos"]} == {"dados/registros.csv", "01-busca/brutos/wos_plaintext.txt"}
    assert all(a["sha256"] for a in ev[0]["artefatos"])
    assert ev[0]["dados"]["fontes"] == {"wos": 4, "scielo": 1} and ev[0]["etapa"] == "05_organizacao"


def test_reimportar_mesmo_arquivo_nao_duplica(projeto_vazio, capsys):
    raiz = projeto_vazio
    argv = ["--dir", str(raiz), "importar", "--arquivo", str(FIX / "scopus.csv"), "--busca-id", "B02"]
    assert rodar(capsys, *argv)[0] == 0
    codigo, resumo = rodar(capsys, *argv)
    assert codigo == 0 and resumo["reexecucao"] and resumo["n_importados"] == 0
    _, linhas = ler_registros_csv(raiz)
    assert len(linhas) == 5 and len(eventos(raiz, "importacao")) == 1
    # a cópia que já está em brutos/ também é reconhecida
    codigo, resumo = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo",
                           str(raiz / "01-busca/brutos/scopus.csv"), "--busca-id", "B02")
    assert codigo == 0 and resumo["reexecucao"] and len(ler_registros_csv(raiz)[1]) == 5


def test_varios_arquivos_na_mesma_busca_continuam_ids(projeto_vazio, capsys):
    from rslib import estado
    raiz = projeto_vazio
    rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "wos_plaintext.txt"), "--busca-id", "B01")
    codigo, resumo = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "wos.bib"), "--busca-id", "B01")
    assert codigo == 0 and (resumo["id_primeiro"], resumo["id_ultimo"]) == ("B01-00006", "B01-00008")
    busca = estado.carregar_estado(raiz)["buscas"][0]
    assert len(busca["arquivos"]) == 2 and busca["n_importado"] == 8
    assert len(eventos(raiz, "importacao")) == 2


def test_mesmo_arquivo_em_outra_busca_exige_flag(projeto_vazio, capsys):
    raiz = projeto_vazio
    arquivo = str(FIX / "pop.csv")
    assert rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", arquivo, "--busca-id", "CZ1")[0] == 0
    codigo, resumo = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", arquivo, "--busca-id", "CZ2")
    assert codigo == 1 and not resumo["ok"] and "CZ1" in resumo["erro"]
    codigo, _ = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", arquivo, "--busca-id", "CZ2",
                      "--permitir-repetido")
    assert codigo == 0
    _, linhas = ler_registros_csv(raiz)
    assert {l["metodo_identificacao"] for l in linhas} == {"cinzenta"}
    assert len([l for l in linhas if l["busca_id"] == "CZ2"]) == 4


def test_bruto_alterado_depois_de_importado_e_recusado(projeto_vazio, capsys):
    raiz = projeto_vazio
    destino = raiz / "01-busca/brutos/lista.ris"
    destino.write_bytes((FIX / "zotero.ris").read_bytes())
    assert rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(destino), "--busca-id", "MN1")[0] == 0
    with open(destino, "a", encoding="utf-8") as f:
        f.write("\nTY  - JOUR\nTI  - Registro enfiado depois\nER  - \n")
    codigo, resumo = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(destino), "--busca-id", "MN1")
    assert codigo == 1 and "mudou" in resumo["erro"]
    assert len(ler_registros_csv(raiz)[1]) == 4


def test_nome_repetido_com_conteudo_diferente_ganha_sufixo(projeto_vazio, capsys, tmp_path):
    raiz = projeto_vazio
    outro = tmp_path / "outra" / "scopus.csv"
    outro.parent.mkdir()
    outro.write_bytes((FIX / "scopus_antigo.csv").read_bytes())
    rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "scopus.csv"), "--busca-id", "B02")
    codigo, resumo = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(outro), "--busca-id", "B02")
    assert codigo == 0 and resumo["arquivo"].startswith("01-busca/brutos/scopus_") and resumo["arquivo"].endswith(".csv")
    assert (raiz / "01-busca/brutos/scopus.csv").read_bytes() == (FIX / "scopus.csv").read_bytes()


def test_recupera_estado_quando_linhas_ja_foram_gravadas(projeto_vazio, capsys):
    from rslib import estado
    raiz = projeto_vazio
    argv = ["--dir", str(raiz), "importar", "--arquivo", str(FIX / "openalex.csv"), "--busca-id", "B04"]
    rodar(capsys, *argv)
    est = estado.carregar_estado(raiz)
    est["buscas"] = []  # simula queda depois de gravar registros.csv e antes do estado
    estado.salvar_estado(raiz, est)
    codigo, resumo = rodar(capsys, *argv)
    assert codigo == 0 and resumo["recuperado"] and resumo["n_importados"] == 0
    assert len(ler_registros_csv(raiz)[1]) == 5
    assert estado.carregar_estado(raiz)["buscas"][0]["n_importado"] == 5
    assert eventos(raiz, "importacao")[-1]["dados"]["recuperado"] is True


def test_metodo_inferido_e_explicito(projeto_vazio, capsys):
    raiz = projeto_vazio
    rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "openalex_works.jsonl"), "--busca-id", "SN1")
    rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "bdtd.csv"), "--busca-id", "B07",
          "--metodo", "cinzenta")
    _, linhas = ler_registros_csv(raiz)
    assert {l["metodo_identificacao"] for l in linhas if l["busca_id"] == "SN1"} == {"citacao"}
    assert {l["metodo_identificacao"] for l in linhas if l["busca_id"] == "B07"} == {"cinzenta"}


def test_aviso_quando_n_bruto_declarado_difere(projeto_vazio, capsys):
    from rslib import estado
    raiz = projeto_vazio
    est = estado.carregar_estado(raiz)
    est["buscas"].append({"id": "B03", "fonte": "scielo", "string_id": "S-scielo-v1", "executada_em": "2025-03-20",
                          "n_bruto": 7, "filtros_na_base": None, "arquivo": None, "sha256": None, "importada": False})
    estado.salvar_estado(raiz, est)
    codigo, resumo = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "scielo_portal.csv"),
                           "--busca-id", "B03")
    assert codigo == 0 and any("7 resultados" in a for a in resumo["avisos"])
    busca = estado.carregar_estado(raiz)["buscas"][0]
    assert busca["string_id"] == "S-scielo-v1" and busca["executada_em"] == "2025-03-20" and busca["importada"]


def test_erros_de_uso(projeto_vazio, capsys, tmp_path, tmp_path_factory):
    raiz = projeto_vazio
    codigo, resumo = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "pop.csv"), "--busca-id", "b1")
    assert codigo == 1 and "busca-id" in resumo["erro"]
    codigo, _ = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "pop.csv"))
    assert codigo == 1
    codigo, _ = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(tmp_path / "nao_existe.csv"),
                      "--busca-id", "B01")
    assert codigo == 1
    vazio = tmp_path_factory.mktemp("sem_projeto")  # fora da árvore do projeto
    codigo, resumo = rodar(capsys, "--dir", str(vazio), "importar", "--arquivo", str(FIX / "pop.csv"), "--busca-id", "B01")
    assert codigo == 1 and not resumo["ok"]
    (raiz / "dados/registros.csv").write_text("id,titulo\n", encoding="utf-8")
    codigo, resumo = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "pop.csv"), "--busca-id", "B01")
    assert codigo == 1 and "cabeçalho" in resumo["erro"]
    assert (raiz / "dados/registros.csv").read_text(encoding="utf-8") == "id,titulo\n"


def test_simular_nao_exige_projeto_nem_grava(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    codigo, resumo = rodar(capsys, "importar", "--arquivo", str(FIX / "scielo_portal.csv"), "--simular")
    assert codigo == 0 and resumo["simulacao"] and resumo["formato"] == "scielo_csv" and resumo["n_validos"] == 5
    assert len(resumo["amostra"]) == 3 and list(tmp_path.iterdir()) == []


def test_importar_arquivo_api_programatica(projeto_vazio):
    from rslib.importar.cli import importar_arquivo
    resumo = importar_arquivo(projeto_vazio, FIX / "openalex_pagina.json", "B05", fonte="openalex")
    assert resumo["n_importados"] == 2 and resumo["fonte"] == "openalex"


def test_eventos_e_estado_validam_schema(projeto_vazio, capsys):
    jsonschema = pytest.importorskip("jsonschema")
    raiz = projeto_vazio
    rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "capes_dados_abertos.csv"), "--busca-id", "B08")
    esquema_estado = json.loads((SKILL / "assets/schemas/estado.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(json.loads((raiz / "rs_estado.json").read_text(encoding="utf-8")), esquema_estado)
    esquema_evento = json.loads((SKILL / "assets/schemas/evento.schema.json").read_text(encoding="utf-8"))
    for ev in ler_jsonl(raiz / "rs_log.jsonl"):
        jsonschema.validate(ev, esquema_evento)


# ---------------------------------------------------------------------------
# Metadados PRISMA-S, substituição de busca e flags da fonte (v1.1)
# ---------------------------------------------------------------------------
def test_metadados_prisma_s_gravados_no_estado_e_no_evento(projeto_vazio, capsys):
    from rslib import estado
    raiz = projeto_vazio
    (raiz / "01-busca/strings/S-scopus-v2.txt").write_text("TITLE-ABS-KEY(amnesty)\n", encoding="utf-8")
    argv = ["--dir", str(raiz), "importar", "--arquivo", str(FIX / "scopus.csv"), "--busca-id", "B02",
            "--string-id", "S-scopus-v2", "--executada-em", "2025-03-20", "--n-base", "5",
            "--filtros-na-base", "DOCTYPE(ar)", "--plataforma", "Scopus (Elsevier)"]
    codigo, resumo = rodar(capsys, *argv)
    assert codigo == 0 and resumo["busca_registrada"] is True and resumo["n_importados"] == 5
    assert not any("resultados" in a for a in resumo["avisos"])  # n informado = n importado
    busca = estado.carregar_estado(raiz)["buscas"][0]
    assert (busca["string_id"], busca["executada_em"], busca["n_bruto"], busca["filtros_na_base"],
            busca["plataforma"]) == ("S-scopus-v2", "2025-03-20", 5, "DOCTYPE(ar)", "Scopus (Elsevier)")
    assert busca["ativa"] is True and busca["executada_em_origem"] == "declarada"
    ev = eventos(raiz, "busca_registrada")
    assert len(ev) == 1 and ev[0]["etapa"] == "04_busca"
    assert ev[0]["dados"]["n_bruto"] == 5 and ev[0]["dados"]["plataforma"] == "Scopus (Elsevier)"
    assert ev[0]["dados"]["origem"] == "importar" and set(ev[0]["dados"]["campos_declarados"]) == {
        "string_id", "executada_em", "n_bruto", "filtros_na_base", "plataforma"}
    assert {a["caminho"] for a in ev[0]["artefatos"]} == {"01-busca/brutos/scopus.csv", "01-busca/strings/S-scopus-v2.txt"}
    # reexecução idêntica: nenhum evento novo
    n_eventos = len(ler_jsonl(raiz / "rs_log.jsonl"))
    codigo, resumo = rodar(capsys, *argv)
    assert codigo == 0 and resumo["reexecucao"] and resumo["busca_registrada"] is False
    assert len(ler_jsonl(raiz / "rs_log.jsonl")) == n_eventos


def test_metadados_completam_busca_importada_e_conflito_e_recusado(projeto_vazio, capsys):
    from rslib import estado
    raiz = projeto_vazio
    base = ["--dir", str(raiz), "importar", "--arquivo", str(FIX / "wos_plaintext.txt"), "--busca-id", "B01"]
    assert rodar(capsys, *base)[0] == 0
    busca = estado.carregar_estado(raiz)["buscas"][0]
    assert busca["executada_em"] == "2025-01-10" and busca["executada_em_origem"] == "arquivo"
    # completa depois, sem linhas novas; a data declarada vale sobre a data do arquivo, com aviso
    codigo, resumo = rodar(capsys, *base, "--n-base", "7", "--executada-em", "2025-01-09")
    assert codigo == 0 and resumo["n_importados"] == 0 and resumo["busca_registrada"]
    assert any("2025-01-10" in a and "declarada" in a for a in resumo["avisos"])
    assert any("7 resultados" in a for a in resumo["avisos"])
    busca = estado.carregar_estado(raiz)["buscas"][0]
    assert (busca["n_bruto"], busca["executada_em"]) == (7, "2025-01-09")
    assert len(ler_registros_csv(raiz)[1]) == 5 and len(eventos(raiz, "importacao")) == 1
    # buscas são imutáveis: valor declarado diferente é recusado sem tocar em nada
    for extra in (["--n-base", "8"], ["--executada-em", "2025-01-08"]):
        codigo, resumo = rodar(capsys, *base, *extra)
        assert codigo == 1 and "já registrado" in resumo["erro"] and "--substituir" in resumo["erro"]
    assert estado.carregar_estado(raiz)["buscas"][0]["n_bruto"] == 7
    assert len(eventos(raiz, "busca_registrada")) == 1


@pytest.mark.parametrize("extra, trecho", [
    (["--executada-em", "20-03-2025"], "AAAA-MM-DD"),
    (["--executada-em", "2025-02-30"], "AAAA-MM-DD"),
    (["--executada-em", "2999-01-01"], "futuro"),
    (["--n-base", "-1"], "--n-base"),
    (["--string-id", "S scopus"], "--string-id"),
    (["--plataforma", "  "], "--plataforma"),
    (["--motivo", "sem substituir"], "--substituir"),
])
def test_metadados_invalidos_da_exit_1_sem_gravar(projeto_vazio, capsys, extra, trecho):
    raiz = projeto_vazio
    codigo, resumo = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "pop.csv"),
                           "--busca-id", "CZ1", *extra)
    assert codigo == 1 and trecho in resumo["erro"]
    assert not (raiz / "dados/registros.csv").exists()


def test_substituir_desativa_busca_antiga_sem_apagar_linhas(projeto_vazio, capsys):
    from rslib import esquema, estado
    raiz = projeto_vazio
    assert rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "scopus.csv"), "--busca-id", "B02")[0] == 0
    argv = ["--dir", str(raiz), "importar", "--arquivo", str(FIX / "scopus_antigo.csv"), "--busca-id", "B06",
            "--substituir", "B02", "--motivo", "âncora A07 perdida na string v1"]
    codigo, resumo = rodar(capsys, *argv)
    assert codigo == 0 and resumo["substituicao"]["busca_id_antiga"] == "B02"
    assert resumo["substituicao"]["n_registros_antiga"] == 5
    est = estado.carregar_estado(raiz)
    b02 = next(b for b in est["buscas"] if b["id"] == "B02")
    b06 = next(b for b in est["buscas"] if b["id"] == "B06")
    assert b02[esquema.CAMPO_BUSCA_ATIVA] is False and b02["substituida_por"] == "B06"
    assert b02["motivo_substituicao"] == "âncora A07 perdida na string v1" and b02["substituida_em"]
    assert b06[esquema.CAMPO_BUSCA_ATIVA] is True and b06["substitui"] == ["B02"]
    _, linhas = ler_registros_csv(raiz)
    assert len([l for l in linhas if l["busca_id"] == "B02"]) == 5  # nada apagado
    ev = eventos(raiz, "busca_substituida")
    assert len(ev) == 1 and ev[0]["motivo"] == "âncora A07 perdida na string v1"
    assert ev[0]["dados"]["busca_id_nova"] == "B06" and ev[0]["etapa"] == "04_busca"
    # idempotente
    codigo, resumo = rodar(capsys, *argv)
    assert codigo == 0 and resumo["reexecucao"] and resumo["substituicao"]["ja_aplicada"]
    assert len(eventos(raiz, "busca_substituida")) == 1
    # busca inativa não recebe importações
    codigo, resumo = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "scopus.ris"),
                           "--busca-id", "B02")
    assert codigo == 1 and "substituída por B06" in resumo["erro"]
    # nem pode ser substituída de novo por outra busca
    codigo, resumo = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "scopus.ris"),
                           "--busca-id", "B07", "--substituir", "B02", "--motivo", "outra")
    assert codigo == 1 and "B06" in resumo["erro"]
    assert not any(l["busca_id"] == "B07" for l in ler_registros_csv(raiz)[1])


def test_substituir_valida_antes_de_gravar(projeto_vazio, capsys):
    raiz = projeto_vazio
    rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "scopus.csv"), "--busca-id", "B02")
    casos = [
        (["--substituir", "B09", "--motivo", "x"], "inexistente"),
        (["--substituir", "B02"], "--motivo"),
        (["--substituir", "B06", "--motivo", "x"], "própria busca"),
        (["--substituir", "b2", "--motivo", "x"], "--substituir inválido"),
    ]
    for extra, trecho in casos:
        codigo, resumo = rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "scopus_antigo.csv"),
                               "--busca-id", "B06", *extra)
        assert codigo == 1 and trecho in resumo["erro"], (extra, resumo)
    assert {l["busca_id"] for l in ler_registros_csv(raiz)[1]} == {"B02"}


def test_retratado_do_openalex_persistido_em_registros_flags(projeto_vazio, capsys):
    import csv
    raiz = projeto_vazio
    argv = ["--dir", str(raiz), "importar", "--arquivo", str(FIX / "openalex.csv"), "--busca-id", "B04"]
    codigo, resumo = rodar(capsys, *argv)
    assert codigo == 0 and resumo["n_retratados"] == 1
    por_fonte = {l["id_fonte"]: l["id_registro"] for l in ler_registros_csv(raiz)[1]}
    arq = raiz / "dados/registros_flags.csv"
    with open(arq, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    assert [(l["id_registro"], l["flag"], l["origem"]) for l in linhas] == [
        (por_fonte["W1000000002"], "retratado", "openalex:is_retracted")]
    ev = eventos(raiz, "importacao")[-1]
    assert ev["dados"]["ids_retratados"] == [por_fonte["W1000000002"]]
    assert "dados/registros_flags.csv" in {a["caminho"] for a in ev["artefatos"]}
    # reimportar não duplica; apagada a tabela (projeto anterior à v1.1), a reimportação a recompõe
    rodar(capsys, *argv)
    assert len(arq.read_text(encoding="utf-8").splitlines()) == 2
    arq.unlink()
    codigo, resumo = rodar(capsys, *argv)
    assert codigo == 0 and resumo["n_importados"] == 0 and arq.exists()
    assert eventos(raiz, "importacao")[-1]["dados"]["flags_acrescentadas"] == 1
    # o conversor sem projeto também conta
    assert converter("openalex_works.jsonl").flags and simular_retratados() == 1


def simular_retratados():
    from rslib.importar import cli
    return cli.simular(FIX / "openalex_works.jsonl")["n_retratados"]


def test_regra_de_busca_id_compartilhada():
    from rslib.importar import buscas
    from rslib.importar.detectar import ErroImportacao
    for valido in ("B01", "SN1", "CZ12", "MN1", "ABCD9999"):
        buscas.validar_busca_id(valido)
    for invalido in ("B05a", "b01", "B", "SN-1", "", None, "ABCDE1"):
        with pytest.raises(ErroImportacao):
            buscas.validar_busca_id(invalido)
    assert buscas.busca_ativa({"id": "B01"}) and not buscas.busca_ativa({"id": "B01", "ativa": False})
    assert buscas.inativas({"buscas": [{"id": "B01", "ativa": False}, {"id": "B02"}]}) == {"B01"}
    assert buscas.metodo_por_prefixo("SN2") == "citacao" and buscas.metodo_por_prefixo("B03") == "base"


def test_estado_com_busca_substituida_valida_schema(projeto_vazio, capsys):
    jsonschema = pytest.importorskip("jsonschema")
    raiz = projeto_vazio
    rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "scopus.csv"), "--busca-id", "B02",
          "--string-id", "S-scopus-v1", "--n-base", "5", "--executada-em", "2025-03-20")
    rodar(capsys, "--dir", str(raiz), "importar", "--arquivo", str(FIX / "scopus_antigo.csv"), "--busca-id", "B06",
          "--substituir", "B02", "--motivo", "PRESS")
    esquema_estado = json.loads((SKILL / "assets/schemas/estado.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(json.loads((raiz / "rs_estado.json").read_text(encoding="utf-8")), esquema_estado)
    esquema_evento = json.loads((SKILL / "assets/schemas/evento.schema.json").read_text(encoding="utf-8"))
    for ev in ler_jsonl(raiz / "rs_log.jsonl"):
        jsonschema.validate(ev, esquema_evento)


# ---------------------------------------------------------------------------
# Exportações reais do repositório OSF do MAPE/IESP-UERJ (opcional, só com RS_OSF_DIR)
# ---------------------------------------------------------------------------
OSF_CONTAGENS = [
    ("wos.bib", 3), ("savedrecs.txt", 115), ("savedrecs.bib", 115), ("savedrecs.xls", 115),
    ("scopus.csv", 798), ("openalex.csv", 4), ("Web of Science.xls", 455), ("bdtd.xlsx", 158),
    ("export.csv", 87), ("export_20250320.csv", 87), ("PoPCites.csv", 200), ("wos_scielo.txt", 21),
]


@pytest.mark.osf
@pytest.mark.skipif(not os.environ.get("RS_OSF_DIR"), reason="defina RS_OSF_DIR com a pasta do repositório OSF do MAPE/IESP-UERJ")
@pytest.mark.parametrize("nome,n", OSF_CONTAGENS)
def test_osf_contagens(nome, n):
    candidatos = sorted(Path(os.environ["RS_OSF_DIR"]).rglob(nome))
    if not candidatos:
        pytest.skip(f"{nome} não encontrado em RS_OSF_DIR")
    conv = converter(candidatos[0])
    assert len(conv.registros) == n


@pytest.mark.skipif(__import__("os").name == "nt", reason="permissões POSIX")
def test_regressao_registros_e_flags_com_permissao_de_arquivo_comum(projeto_vazio):
    import stat
    from rslib import esquema, estado
    from rslib.importar import flags
    from rslib.importar.cli import importar_arquivo
    importar_arquivo(projeto_vazio, FIX / "openalex_pagina.json", "B05", fonte="openalex")
    flags.acrescentar(projeto_vazio, [{"id_registro": "B05-00001", "flag": "retratado", "origem": "teste"}])
    for rel in (esquema.ARQ_REGISTROS, esquema.ARQ_REGISTROS_FLAGS):
        assert stat.S_IMODE((projeto_vazio / rel).stat().st_mode) == estado.modo_arquivo_padrao(), rel
