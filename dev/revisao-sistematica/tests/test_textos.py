"""Testes de textos: para-baixar, inventário com PDFs sintéticos, elegibilidade consolidada e ligação de relatos."""

import argparse
import json

import pytest

from conftest import FIXTURES

CHAVES = ["Alves2020", "Borges2019", "Castro2018", "Dias2021", "Esteves2022", "Faria2017", "Gomes2016"]


def rodar(argv, capsys):
    from rslib import textos
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    sub = parser.add_subparsers(dest="comando")
    textos.registrar(sub)
    args = parser.parse_args(argv)
    codigo = args.func(args)
    return codigo, json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def criar_pdf(caminho, paginas):
    import pymupdf
    caminho.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for texto in paginas:
        pagina = doc.new_page()
        if texto:
            pagina.insert_textbox(pymupdf.Rect(50, 50, 550, 800), texto, fontsize=11)
    doc.save(str(caminho))
    doc.close()


def escrever_unicos(raiz, chaves=CHAVES, metodos=None):
    from rslib import esquema
    from rslib.handoff import escrever_csv
    base = {c: "" for c in esquema.COLUNAS_UNICOS}
    unicos, registros = [], []
    for i, ch in enumerate(chaves, start=1):
        id_rs = f"RS{i:04d}"
        id_reg = f"B01-{i:05d}"
        unicos.append(dict(base, id_rs=id_rs, id_estudo=esquema.id_estudo_de(id_rs), chave=ch, ids_registro=id_reg, fontes="wos",
                           titulo=f"Title {ch}", autores=f"{ch[:-4]}, Ana | Costa, Bruno", ano=ch[-4:],
                           doi=f"10.1234/{ch.lower()}", tipo_publicacao="artigo", veiculo="Revista Teste"))
        metodo = (metodos or {}).get(ch, "base")
        registros.append(dict({c: "" for c in esquema.COLUNAS_REGISTROS}, id_registro=id_reg, busca_id="B01",
                              metodo_identificacao=metodo))
    escrever_csv(raiz / esquema.ARQ_UNICOS, esquema.COLUNAS_UNICOS, unicos)
    escrever_csv(raiz / esquema.ARQ_REGISTROS, esquema.COLUNAS_REGISTROS, registros)


def autopiloto(raiz):
    from rslib import estado
    est = estado.carregar_estado(raiz)
    est["modo"]["autonomia"] = "autopiloto"
    estado.salvar_estado(raiz, est)


# ---------------------------------------------------------------------------
def test_para_baixar_incluidos_e_incertos(projeto_vazio, capsys):
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_csv
    escrever_unicos(projeto_vazio)
    escrever_csv(projeto_vazio / esquema.ARQ_TRIAGEM_TA_FINAL, esquema.COLUNAS_TRIAGEM_FINAL, [
        {"id_rs": "RS0003", "decisao_final": "incerto"}, {"id_rs": "RS0001", "decisao_final": "incluir"},
        {"id_rs": "RS0002", "decisao_final": "excluir"}])
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "textos", "para-baixar"], capsys)
    assert codigo == 0 and resumo["n"] == 2
    colunas, linhas = ler_csv(projeto_vazio / esquema.ARQ_PARA_BAIXAR)
    assert colunas == esquema.COLUNAS_PARA_BAIXAR
    assert [(l["id_rs"], l["chave"]) for l in linhas] == [("RS0001", "Alves2020"), ("RS0003", "Castro2018")]
    assert linhas[0]["doi"] == "10.1234/alves2020"
    codigo, _ = rodar(["--dir", str(projeto_vazio), "textos", "para-baixar"], capsys)  # idempotente
    assert codigo == 0 and len(ler_csv(projeto_vazio / esquema.ARQ_PARA_BAIXAR)[1]) == 2
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "textos", "para-baixar", "--decisoes", "incluir,talvez"], capsys)
    assert codigo == 1


def test_para_baixar_exige_chave(projeto_vazio, capsys):
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_csv
    escrever_unicos(projeto_vazio)
    cols, linhas = ler_csv(projeto_vazio / esquema.ARQ_UNICOS)
    linhas[0]["chave"] = ""
    escrever_csv(projeto_vazio / esquema.ARQ_UNICOS, cols, linhas)
    escrever_csv(projeto_vazio / esquema.ARQ_TRIAGEM_TA_FINAL, esquema.COLUNAS_TRIAGEM_FINAL,
                 [{"id_rs": "RS0001", "decisao_final": "incluir"}])
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "textos", "para-baixar"], capsys)
    assert codigo == 1 and "dedup" in resumo["erro"]


def test_inventario_pdfs(projeto_vazio, capsys):
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_csv
    escrever_unicos(projeto_vazio)
    escrever_csv(projeto_vazio / esquema.ARQ_PARA_BAIXAR, esquema.COLUNAS_PARA_BAIXAR, [
        {"chave": "Alves2020", "id_rs": "RS0001"}, {"chave": "Borges2019", "id_rs": "RS0002"},
        {"chave": "Castro2018", "id_rs": "RS0003"}, {"chave": "Dias2021", "id_rs": "RS0004"}])
    texto = "Conditional transfers and school attendance. " * 40
    criar_pdf(projeto_vazio / "03-textos/pdfs/Alves2020.pdf", [texto, texto])
    criar_pdf(projeto_vazio / "03-textos/pdfs/Borges2019.pdf", ["", ""])  # sem camada de texto
    (projeto_vazio / "03-textos/pdfs/Dias2021.pdf").write_bytes(b"%PDF-1.4 corrompido")
    escrever_csv(projeto_vazio / esquema.ARQ_RELATORIO_PDFS, esquema.COLUNAS_RELATORIO_PDFS, [
        {"chave": "Alves2020", "status": "ok", "arquivo": "pdfs/Alves2020.pdf"},
        {"chave": "Borges2019", "status": "ja_existia", "arquivo": "/caminho/que/nao/existe/Borges2019.pdf"},
        {"chave": "Castro2018", "status": "nao_encontrado", "arquivo": ""}])
    escrever_csv(projeto_vazio / esquema.ARQ_VERIFICACAO_CONTEUDO, esquema.COLUNAS_VERIFICACAO_CONTEUDO, [
        {"chave": "Alves2020", "veredito": "confere"}, {"chave": "Borges2019", "veredito": "suspeito"}])
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "textos", "inventario"], capsys)
    assert codigo == 0, resumo
    colunas, linhas = ler_csv(projeto_vazio / esquema.ARQ_INVENTARIO_TEXTOS)
    assert colunas == esquema.COLUNAS_INVENTARIO_TEXTOS
    inv = {l["chave"]: l for l in linhas}
    assert inv["Alves2020"]["existe"] == "1" and inv["Alves2020"]["n_paginas"] == "2" and inv["Alves2020"]["tem_texto"] == "1"
    assert inv["Alves2020"]["arquivo"] == "03-textos/pdfs/Alves2020.pdf"
    assert inv["Borges2019"]["tem_texto"] == "0" and inv["Borges2019"]["veredito_conteudo"] == "suspeito"
    assert inv["Castro2018"]["existe"] == "0" and inv["Castro2018"]["tem_texto"] == ""
    assert inv["Dias2021"]["existe"] == "1" and inv["Dias2021"]["n_paginas"] == "0"
    assert resumo["n_faltando"] == 1 and "Borges2019" in resumo["conferir_conteudo"]
    assert any("ilegível" in a for a in resumo["avisos"])
    # coluna recuperado (v1.1): existe e veredito confere; sem veredito ou suspeito = 0
    assert {c: inv[c]["recuperado"] for c in inv} == {"Alves2020": "1", "Borges2019": "0", "Castro2018": "0",
                                                      "Dias2021": "0"}
    assert resumo["n_recuperados"] == 1 and set(resumo["existe_nao_recuperado"]) == {"Borges2019", "Dias2021"}

    # conferência humana: Borges conferido à mão; Alves era PDF de outro trabalho (0 prevalece sobre confere)
    (projeto_vazio / "03-textos/conferencia_pdfs.csv").write_text(
        "chave,recuperado,motivo\nBorges2019,sim,conferido título e autores\nAlves2020,0,PDF de outro trabalho\n"
        "Castro2018,1,cópia impressa\n", encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "textos", "inventario"], capsys)
    assert codigo == 0, resumo
    inv = {l["chave"]: l for l in ler_csv(projeto_vazio / esquema.ARQ_INVENTARIO_TEXTOS)[1]}
    assert {c: inv[c]["recuperado"] for c in inv} == {"Alves2020": "0", "Borges2019": "1", "Castro2018": "0",
                                                      "Dias2021": "0"}
    assert any("Castro2018" in a and "não foi encontrado" in a for a in resumo["avisos"])
    from rslib import estado
    ev = [e for e in estado.ler_log(projeto_vazio) if e["evento"] == "textos_atualizados"][-1]
    assert "03-textos/conferencia_pdfs.csv" in [a["caminho"] for a in ev["artefatos"]]
    (projeto_vazio / "03-textos/conferencia_pdfs.csv").write_text("chave,recuperado,motivo\nAlves2020,talvez,x\n",
                                                                 encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "textos", "inventario"], capsys)
    assert codigo == 1 and "talvez" in resumo["erro"]


# ---------------------------------------------------------------------------
@pytest.mark.parametrize("valor,esperado", [
    ("Sim", "atende"), ("sim — o estudo usa escolas", "atende"), ("Não", "falha"), ("NAO ATENDE", "falha"),
    ("Não — ensaio teórico", "falha"), ("999", "incerto"), ("", "incerto"), ("parcialmente", "incerto"),
    ("NA_secao", "nao_aplica"), ("talvez", "incerto"), ("1", "atende"), ("0", "falha"),
])
def test_classificar_resposta(valor, esperado):
    from rslib.textos import classificar_resposta
    assert classificar_resposta(valor) == esperado


def test_detectar_criterios():
    from rslib.handoff import ler_csv
    from rslib.textos import detectar_criterios
    _, cb = ler_csv(FIXTURES / "textos" / "codebook_elegibilidade.csv")
    assert detectar_criterios(cb) == ["C1_populacao", "C2_desenho", "C3_outcome"]
    assert detectar_criterios(cb, ["C3_outcome", "C1_populacao"]) == ["C1_populacao", "C3_outcome"]
    with pytest.raises(ValueError):
        detectar_criterios(cb, ["C9"])
    with pytest.raises(ValueError):
        detectar_criterios([{"dimensao": "Metodo", "variavel": "estimador"}])


def test_elegibilidade_consolidar(projeto_vazio, capsys, tmp_path):
    from rslib import esquema, estado
    from rslib.handoff import ler_csv
    escrever_unicos(projeto_vazio, metodos={"Esteves2022": "citacao", "Faria2017": "citacao"})
    autopiloto(projeto_vazio)
    gate = tmp_path / "verificacao_citacoes.csv"
    gate.write_text("citekey,ficha,variavel,pagina_indicada,status,pagina_encontrada_impressa,offset_pagina,citacao\n"
                    "Gomes2016,fichamento_Gomes2016.md,C3_outcome,2,NAO_ENCONTRADA,,0,attendance\n"
                    "Alves2020,fichamento_Alves2020.md,C3_outcome,4,OK,,0,attendance\n", encoding="utf-8")
    argv = ["--dir", str(projeto_vazio), "textos", "elegibilidade", "consolidar",
            "--master", str(FIXTURES / "textos" / "master_elegibilidade.csv"),
            "--codebook", str(FIXTURES / "textos" / "codebook_elegibilidade.csv"), "--verificacao", str(gate)]
    codigo, resumo = rodar(argv, capsys)
    assert codigo == 0, resumo
    colunas, linhas = ler_csv(projeto_vazio / esquema.ARQ_ELEGIBILIDADE_TC_FINAL)
    assert colunas == esquema.COLUNAS_ELEGIBILIDADE_FINAL
    d = {l["chave"]: l for l in linhas}
    assert d["Alves2020"]["decisao"] == "incluir" and d["Alves2020"]["id_rs"] == "RS0001"
    assert (d["Borges2019"]["decisao"], d["Borges2019"]["criterio_falhou"], d["Borges2019"]["pagina"]) == \
        ("excluir", "C2_desenho", "3")
    assert "theoretical essay" in d["Borges2019"]["evidencia"]
    assert (d["Castro2018"]["decisao"], d["Castro2018"]["criterio_falhou"]) == ("excluir", "C2_desenho")
    assert d["Dias2021"]["decisao"] == "incerto" and "C2_desenho" in d["Dias2021"]["evidencia"]
    assert d["Esteves2022"]["decisao"] == "incluir"  # NA_secao não reprova
    assert d["Faria2017"]["decisao"] == "incluir"  # uma das fichas do texto inclui
    assert d["Gomes2016"]["decisao"] == "incerto"  # citação reprovada no gate
    assert "Desconhecido2000" not in d and any("Desconhecido2000" in a for a in resumo["avisos"])
    assert resumo["contagem"] == {"incluir": 3, "excluir": 2, "incerto": 2}
    assert resumo["motivos_exclusao"] == {"C2_desenho": 2}
    assert resumo["fracao_outros_metodos"] == pytest.approx(0.667, abs=0.001)
    assert any("outros métodos" in a for a in resumo["avisos"])
    assert resumo["pendencia"] and estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))

    n_pend = len(estado.carregar_estado(projeto_vazio)["pendencias"])
    codigo, resumo2 = rodar(argv, capsys)
    assert codigo == 0 and resumo2["pendencia"] == resumo["pendencia"]
    assert len(estado.carregar_estado(projeto_vazio)["pendencias"]) == n_pend
    assert ler_csv(projeto_vazio / esquema.ARQ_ELEGIBILIDADE_TC_FINAL)[1] == linhas


def test_elegibilidade_checkpoints_sem_pendencia(projeto_vazio, capsys):
    from rslib import estado
    escrever_unicos(projeto_vazio)
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "textos", "elegibilidade", "consolidar",
                            "--master", str(FIXTURES / "textos" / "master_elegibilidade.csv"),
                            "--codebook", str(FIXTURES / "textos" / "codebook_elegibilidade.csv")], capsys)
    assert codigo == 0 and resumo["pendencia"] is None and "G5" in resumo["acao_humana"]
    assert not estado.pendencias_abertas(estado.carregar_estado(projeto_vazio))


# ---------------------------------------------------------------------------
def test_ligar_relatos(projeto_vazio, capsys, tmp_path):
    from rslib import esquema
    from rslib.handoff import ler_csv
    escrever_unicos(projeto_vazio, CHAVES[:5])
    _, antes = ler_csv(projeto_vazio / esquema.ARQ_UNICOS)
    pares = tmp_path / "pares.csv"
    pares.write_text("id_rs_a,id_rs_b\nRS0003,RS0001\nRS0004,RS0003\n", encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "textos", "ligar-relatos", "--pares", str(pares)], capsys)
    assert codigo == 0 and resumo["n_grupos"] == 1 and resumo["n_relatos_ligados"] == 3 and resumo["n_estudos_total"] == 3
    colunas, depois = ler_csv(projeto_vazio / esquema.ARQ_UNICOS)
    assert colunas == esquema.COLUNAS_UNICOS
    estudo = {l["id_rs"]: l["id_estudo"] for l in depois}
    assert estudo == {"RS0001": "ES0001", "RS0002": "ES0002", "RS0003": "ES0001", "RS0004": "ES0001", "RS0005": "ES0005"}
    for a, b in zip(antes, depois):  # só id_estudo muda
        assert {k: v for k, v in a.items() if k != "id_estudo"} == {k: v for k, v in b.items() if k != "id_estudo"}

    # a lista é acréscimo: a ligação antiga fica
    pares.write_text("id_rs,id_rs_relacionado\nRS0005,RS0002\n", encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "textos", "ligar-relatos", "--pares", str(pares)], capsys)
    assert codigo == 0 and resumo["modo"] == "acrescimo" and resumo["n_pares_manuais_mantidos"] == 2
    estudo = {l["id_rs"]: l["id_estudo"] for l in ler_csv(projeto_vazio / esquema.ARQ_UNICOS)[1]}
    assert estudo == {"RS0001": "ES0001", "RS0002": "ES0002", "RS0003": "ES0001", "RS0004": "ES0001", "RS0005": "ES0002"}

    # --substituir-manuais: a nova lista substitui as ligações manuais antigas
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "textos", "ligar-relatos", "--pares", str(pares),
                            "--substituir-manuais"], capsys)
    assert codigo == 0 and resumo["modo"] == "substituir_manuais" and resumo["n_pares_manuais_descartados"] == 2
    estudo = {l["id_rs"]: l["id_estudo"] for l in ler_csv(projeto_vazio / esquema.ARQ_UNICOS)[1]}
    assert estudo == {"RS0001": "ES0001", "RS0002": "ES0002", "RS0003": "ES0003", "RS0004": "ES0004", "RS0005": "ES0002"}

    pares.write_text("id_rs_a,id_rs_b\nRS0001,RS0999\n", encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "textos", "ligar-relatos", "--pares", str(pares)], capsys)
    assert codigo == 1 and "RS0999" in resumo["erro"]


def test_ligar_relatos_fallback_usa_id_estudo_de(projeto_vazio, capsys, tmp_path):
    """Regressão: `id_estudo` vazio caía para o id_rs ("RS0002") em vez da convenção ES."""
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_csv, ler_linhas
    escrever_unicos(projeto_vazio, CHAVES[:3])
    colunas, unicos = ler_csv(projeto_vazio / esquema.ARQ_UNICOS)
    for u in unicos:
        u["id_estudo"] = ""
    escrever_csv(projeto_vazio / esquema.ARQ_UNICOS, colunas, unicos)
    pares = tmp_path / "pares.csv"
    pares.write_text("id_rs_a,id_rs_b\nRS0003,RS0002\n", encoding="utf-8")
    codigo, resumo = rodar(["--dir", str(projeto_vazio), "textos", "ligar-relatos", "--pares", str(pares)], capsys)
    assert codigo == 0 and resumo["n_estudos_total"] == 2
    estudo = {l["id_rs"]: l["id_estudo"] for l in ler_linhas(projeto_vazio / esquema.ARQ_UNICOS)}
    assert estudo == {"RS0001": "", "RS0002": "ES0002", "RS0003": "ES0002"}
    ligacao = {l["id_rs"]: l for l in ler_linhas(projeto_vazio / "03-textos/ligacao_relatos.csv")}
    assert ligacao["RS0003"]["id_estudo_anterior"] == "ES0003" and ligacao["RS0002"]["id_estudo_anterior"] == "ES0002"
    # desfazer a ligação (lista vazia com --substituir-manuais) restaura a convenção, não o id_rs
    pares.write_text("id_rs_a,id_rs_b\n", encoding="utf-8")
    assert rodar(["--dir", str(projeto_vazio), "textos", "ligar-relatos", "--pares", str(pares),
                  "--substituir-manuais"], capsys)[0] == 0
    estudo = {l["id_rs"]: l["id_estudo"] for l in ler_linhas(projeto_vazio / esquema.ARQ_UNICOS)}
    assert estudo["RS0003"] == "ES0003"


def test_regressao_ligar_relatos_mantem_versoes_do_dedup(projeto_vazio, capsys, tmp_path):
    """A lista de `ligar-relatos` sem o par de versão não desfaz a ligação automática do dedup."""
    from rslib import esquema, estado
    from rslib.handoff import escrever_csv, ler_linhas
    raiz = projeto_vazio
    escrever_unicos(raiz, CHAVES[:5])
    base = {c: "" for c in esquema.COLUNAS_DEDUP_PARES}
    escrever_csv(raiz / esquema.ARQ_DEDUP_PARES, esquema.COLUNAS_DEDUP_PARES, [
        dict(base, id_a="B01-00001", id_b="B01-00002", regra="versao", score="100", decisao="ligado",
             decidido_por="script", motivo="preprint_publicado"),
        dict(base, id_a="B01-00003", id_b="B01-00005", regra="R5_candidato", score="88", decisao="rejeitado",
             decidido_por="revisor_humano_1", motivo="outro estudo")])
    pares = tmp_path / "pares.csv"
    pares.write_text("id_rs_a,id_rs_b\nRS0004,RS0003\n", encoding="utf-8")  # não repete o par de versão

    def estudos():
        return {l["id_rs"]: l["id_estudo"] for l in ler_linhas(raiz / esquema.ARQ_UNICOS)}

    codigo, r = rodar(["--dir", str(raiz), "textos", "ligar-relatos", "--pares", str(pares)], capsys)
    assert codigo == 0 and r["n_pares_versao_dedup"] == 1 and r["n_grupos"] == 2 and r["n_relatos_ligados"] == 4
    assert any("versão do dedup mantidas" in a for a in r["avisos"])
    assert estudos() == {"RS0001": "ES0001", "RS0002": "ES0001", "RS0003": "ES0003", "RS0004": "ES0003",
                         "RS0005": "ES0005"}
    ev = [e for e in estado.ler_log(raiz) if e["evento"] == "ligacao_relatos"][-1]
    assert ev["dados"]["modo"] == "acrescimo" and ev["dados"]["n_pares_aplicados"] == 2

    pares.write_text("id_rs_a,id_rs_b\nRS0005,RS0003\n", encoding="utf-8")  # acréscimo: RS0004 continua ligado
    codigo, r = rodar(["--dir", str(raiz), "textos", "ligar-relatos", "--pares", str(pares)], capsys)
    assert codigo == 0 and estudos()["RS0004"] == estudos()["RS0005"] == "ES0003" and estudos()["RS0002"] == "ES0001"

    pares.write_text("id_rs_a,id_rs_b\n", encoding="utf-8")
    codigo, r = rodar(["--dir", str(raiz), "textos", "ligar-relatos", "--pares", str(pares), "--substituir-manuais"],
                      capsys)
    assert codigo == 0 and r["n_pares_manuais_descartados"] == 2 and r["n_grupos"] == 1
    assert estudos() == {"RS0001": "ES0001", "RS0002": "ES0001", "RS0003": "ES0003", "RS0004": "ES0004",
                         "RS0005": "ES0005"}  # a versão do dedup ficou; as manuais saíram


# ---------------------------------------------------------------------------
# Decisão humana de texto completo, aguardando e pendência que não reabre (v1.1)
# ---------------------------------------------------------------------------
def humana_tc(raiz, id_rs, decisao, criterio=None, motivo="li o texto completo"):
    from rslib import triagem_lotes as tl
    tl.registrar_decisoes(raiz, [tl.nova_decisao(id_rs, "tc", "tc", "humano_1", "humano", decisao,
                                                 criterio_falhou=criterio, justificativa=motivo,
                                                 motivo_override=motivo)])


def _argv_eleg(raiz, gate=None):
    argv = ["--dir", str(raiz), "textos", "elegibilidade", "consolidar",
            "--master", str(FIXTURES / "textos" / "master_elegibilidade.csv"),
            "--codebook", str(FIXTURES / "textos" / "codebook_elegibilidade.csv")]
    return argv + (["--verificacao", str(gate)] if gate else [])


def test_elegibilidade_aplica_decisoes_humanas_e_nao_reabre_pendencia(projeto_vazio, capsys, tmp_path):
    from rslib import esquema, estado
    from rslib.handoff import ler_linhas
    raiz = projeto_vazio
    escrever_unicos(raiz)
    autopiloto(raiz)
    gate = tmp_path / "verificacao_citacoes.csv"
    gate.write_text("citekey,ficha,variavel,pagina_indicada,status,pagina_encontrada_impressa,offset_pagina,citacao\n"
                    "Gomes2016,f.md,C3_outcome,2,NAO_ENCONTRADA,,0,attendance\n", encoding="utf-8")
    codigo, r1 = rodar(_argv_eleg(raiz, gate), capsys)
    assert codigo == 0 and r1["pendencia"] and r1["n_pendentes_conferencia"] == 7

    humana_tc(raiz, "RS0004", "excluir", "C2_desenho", "sem estimativa de efeito")  # proposta: incerto
    humana_tc(raiz, "RS0007", "incluir", motivo="citação conferida no PDF")         # incerto só pelo gate
    humana_tc(raiz, "RS0002", "incerto", motivo="autores contatados, sem resposta")  # aguardando
    humana_tc(raiz, "RS0003", "excluir", "C2_desenho", "confirmo")                   # confirma a proposta
    codigo, r2 = rodar(_argv_eleg(raiz, gate), capsys)
    assert codigo == 0 and r2["n_pendentes_conferencia"] == 3
    # n atualizado sem duplicar (handoff.sincronizar_pendencia_unica): a antiga fecha e a nova diz o que falta
    abertas = estado.pendencias_abertas(estado.carregar_estado(raiz))
    assert [(p["id"], p["n"]) for p in abertas] == [(r2["pendencia"], 3)] and r2["pendencia"] != r1["pendencia"]
    assert f"[substitui {r1['pendencia']}]" in abertas[0]["descricao"]
    codigo, r2b = rodar(_argv_eleg(raiz, gate), capsys)
    assert r2b["pendencia"] == r2["pendencia"] and len(estado.pendencias_abertas(estado.carregar_estado(raiz))) == 1
    d = {l["chave"]: l for l in ler_linhas(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL)}
    assert (d["Dias2021"]["decisao"], d["Dias2021"]["criterio_falhou"]) == ("excluir", "C2_desenho")
    assert d["Dias2021"]["evidencia"].startswith("[decisão humana: humano_1] sem estimativa")
    assert d["Gomes2016"]["decisao"] == "incluir", "decisão humana prevalece sobre o gate"
    assert d["Borges2019"]["decisao"] == "aguardando" and d["Borges2019"]["criterio_falhou"] == ""
    assert d["Castro2018"]["pagina"] == "7" and "proposta confirmada" in d["Castro2018"]["evidencia"]
    assert r2["contagem"] == {"incluir": 4, "excluir": 2, "incerto": 0, "aguardando": 1}
    assert r2["motivos_exclusao"] == {"C2_desenho": 2}
    assert sorted(r2["mudadas_por_humano"]) == ["Borges2019", "Dias2021", "Gomes2016"]

    n_pend = len(estado.carregar_estado(raiz)["pendencias"])
    estado.fechar_pendencia(raiz, r2["pendencia"], "conferi as propostas restantes")
    codigo, r3 = rodar(_argv_eleg(raiz, gate), capsys)
    assert codigo == 0 and r3["pendencia"] is None and r3["conferencia_ja_feita"] is True
    assert len(estado.carregar_estado(raiz)["pendencias"]) == n_pend, "não reabre a cada execução"
    n_ev = len(estado.ler_log(raiz))
    codigo, r4 = rodar(_argv_eleg(raiz, gate), capsys)
    assert r4["reexecucao"] is True and len(estado.ler_log(raiz)) == n_ev

    for id_rs in ("RS0001", "RS0005", "RS0006"):
        humana_tc(raiz, id_rs, "incluir")
    codigo, r5 = rodar(_argv_eleg(raiz, gate), capsys)
    assert r5["n_pendentes_conferencia"] == 0 and r5["pendencia"] is None
    assert not estado.pendencias_abertas(estado.carregar_estado(raiz))
    ev = [e for e in estado.ler_log(raiz) if e["evento"] == "textos_atualizados"][-1]["dados"]
    assert ev["n_decisoes_humanas"] == 7 and ev["contagem"]["aguardando"] == 1


def test_elegibilidade_fecha_pendencia_quando_tudo_e_humano_e_sem_master(projeto_vazio, capsys):
    from rslib import esquema, estado
    from rslib.handoff import ler_linhas
    raiz = projeto_vazio
    escrever_unicos(raiz)
    autopiloto(raiz)
    codigo, r1 = rodar(_argv_eleg(raiz), capsys)
    assert r1["pendencia"]
    for i in range(1, 8):
        humana_tc(raiz, f"RS{i:04d}", "incluir" if i % 2 else "excluir", None if i % 2 else "C1_populacao")
    codigo, r2 = rodar(_argv_eleg(raiz), capsys)
    assert codigo == 0 and r2["pendencia"] is None
    pend = {p["id"]: p for p in estado.carregar_estado(raiz)["pendencias"]}
    assert pend[r1["pendencia"]]["status"] == "fechada"

    # só decisões humanas, sem master
    codigo, r3 = rodar(["--dir", str(raiz), "textos", "elegibilidade", "consolidar"], capsys)
    assert codigo == 0 and r3["n_textos"] == 7 and r3["criterios"] == []
    assert r3["motivos_exclusao"] == {"C1_populacao": 3}
    assert len(ler_linhas(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL)) == 7
    codigo, r4 = rodar(["--dir", str(raiz), "textos", "elegibilidade", "consolidar",
                        "--master", str(FIXTURES / "textos" / "master_elegibilidade.csv")], capsys)
    assert codigo == 1 and "--codebook" in r4["erro"]


def test_elegibilidade_sem_master_nem_decisoes_humanas(projeto_vazio, capsys):
    escrever_unicos(projeto_vazio)
    codigo, r = rodar(["--dir", str(projeto_vazio), "textos", "elegibilidade", "consolidar"], capsys)
    assert codigo == 1 and "override --etapa tc" in r["erro"]


# ---------------------------------------------------------------------------
# Retratações (sessão HTTP falsa, sem rede)
# ---------------------------------------------------------------------------
class RespostaFalsa:
    def __init__(self, status, dados):
        self.status_code, self._dados, self.headers, self.text = status, dados, {}, json.dumps(dados)

    def json(self):
        return self._dados


class SessaoFalsa:
    def __init__(self, obras=None, avisos=None, falhar=False):
        self.obras, self.avisos, self.falhar, self.chamadas = obras or {}, avisos or {}, falhar, []

    def get(self, url, params=None, timeout=None):
        self.chamadas.append((url, dict(params or {})))
        if self.falhar:
            raise ConnectionError("rede caiu")
        if url.startswith("https://api.openalex.org/works/doi:"):
            doi = url.split("doi:", 1)[1]
            if doi in self.obras:
                return RespostaFalsa(200, {"id": "https://openalex.org/W1", "doi": doi, "is_retracted": self.obras[doi]})
            return RespostaFalsa(404, {"error": "not found"})
        if url == "https://api.crossref.org/works":
            doi = params["filter"].split("updates:", 1)[1]
            return RespostaFalsa(200, {"message": {"items": self.avisos.get(doi, [])}})
        return RespostaFalsa(500, {})


def _preparar_retratacoes(raiz):
    from rslib import esquema
    from rslib.handoff import escrever_csv, ler_csv
    escrever_unicos(raiz)
    cols, unicos = ler_csv(raiz / esquema.ARQ_UNICOS)
    for u in unicos:
        if u["chave"] == "Faria2017":
            u["doi"] = ""
    escrever_csv(raiz / esquema.ARQ_UNICOS, cols, unicos)
    escrever_csv(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL, esquema.COLUNAS_ELEGIBILIDADE_FINAL, [
        {"id_rs": "RS0001", "chave": "Alves2020", "decisao": "incluir"},
        {"id_rs": "RS0002", "chave": "Borges2019", "decisao": "incluir"},
        {"id_rs": "RS0003", "chave": "Castro2018", "decisao": "incerto"},
        {"id_rs": "RS0004", "chave": "Dias2021", "decisao": "incluir"},
        {"id_rs": "RS0005", "chave": "Esteves2022", "decisao": "excluir", "criterio_falhou": "C1"},
        {"id_rs": "RS0006", "chave": "Faria2017", "decisao": "incluir"},
    ])


def test_retratacoes_openalex_e_crossref(projeto_vazio, capsys, monkeypatch):
    from rslib import estado, textos
    from rslib.handoff import ler_csv
    raiz = projeto_vazio
    _preparar_retratacoes(raiz)
    monkeypatch.setenv("OPENALEX_API_KEY", "chave-secreta-teste")
    monkeypatch.setenv("RS_EMAIL", "pessoa@example.org")
    sessao = SessaoFalsa(
        obras={"10.1234/alves2020": False, "10.1234/borges2019": True, "10.1234/castro2018": False,
               "10.1234/dias2021": False},
        avisos={"10.1234/castro2018": [{"DOI": "10.9999/notice1",
                                        "update-to": [{"DOI": "10.1234/CASTRO2018", "type": "retraction"}]}],
                "10.1234/dias2021": [{"DOI": "10.9999/eoc",
                                      "update-to": [{"DOI": "10.1234/dias2021", "type": "expression-of-concern"}]}],
                "10.1234/alves2020": [{"DOI": "10.9999/outro", "update-to": [{"DOI": "10.1/x", "type": "retraction"}]}]})
    monkeypatch.setattr(textos, "criar_sessao_http", lambda: sessao)
    monkeypatch.setattr(textos, "_dormir", lambda s: None)
    codigo, r = rodar(["--dir", str(raiz), "textos", "retratacoes"], capsys)
    assert codigo == 0, r
    assert r["universo"] == "tc_nao_excluidos" and r["n"] == 5, "o excluído no texto completo não é consultado"
    assert r["retratados"] == ["Borges2019", "Castro2018"] and r["expressao_preocupacao"] == ["Dias2021"]
    assert r["sem_verificacao"] == ["Faria2017"]
    colunas, linhas = ler_csv(raiz / textos.ARQ_RETRATACOES)
    assert colunas == textos.COLUNAS_RETRATACOES
    d = {l["chave"]: l for l in linhas}
    assert (d["Borges2019"]["openalex_is_retracted"], d["Borges2019"]["retratado"]) == ("true", "1")
    assert d["Castro2018"]["crossref_avisos"] == "retraction:10.9999/notice1" and d["Castro2018"]["retratado"] == "1"
    assert d["Alves2020"]["crossref_avisos"] == "nenhum" and d["Alves2020"]["retratado"] == "0"
    assert d["Dias2021"]["retratado"] == "0" and d["Dias2021"]["crossref_avisos"].startswith("expression_of_concern:")
    assert (d["Faria2017"]["status"], d["Faria2017"]["retratado"]) == ("sem_doi", "")
    # a chave do OpenAlex nunca vai para a Crossref; o mailto vai para as duas
    for url, params in sessao.chamadas:
        assert params.get("mailto") == "pessoa@example.org"
        assert ("api_key" in params) == url.startswith("https://api.openalex.org"), url

    # pendência mesmo no modo checkpoints: fato externo que muda a elegibilidade
    pend = estado.pendencias_abertas(estado.carregar_estado(raiz))
    assert [(p["tipo"], p["portao"], p["n"]) for p in pend] == [("retratacao_texto", "G5", 2)]
    ev = [e for e in estado.ler_log(raiz) if e["evento"] == "retratacoes_verificadas"]
    assert len(ev) == 1 and ev[0]["dados"]["n_retratados"] == 2 and ev[0]["dados"]["reexecucao"] is False
    assert "chave-secreta-teste" not in json.dumps(estado.ler_log(raiz))

    codigo, r2 = rodar(["--dir", str(raiz), "textos", "retratacoes", "--fonte", "ambas"], capsys)
    assert r2["reexecucao"] is True and r2["pendencia"] == pend[0]["id"]
    assert len(estado.pendencias_abertas(estado.carregar_estado(raiz))) == 1

    # só OpenAlex; os retratados saíram (excluídos no texto completo): a pendência fecha
    sessao2 = SessaoFalsa(obras={"10.1234/alves2020": False, "10.1234/dias2021": False})
    monkeypatch.setattr(textos, "criar_sessao_http", lambda: sessao2)
    (raiz / "ids.csv").write_text("id_rs\nRS0001\nRS0004\n", encoding="utf-8")
    codigo, r3 = rodar(["--dir", str(raiz), "textos", "retratacoes", "--fonte", "openalex", "--ids", "ids.csv"], capsys)
    assert codigo == 0 and r3["retratados"] == [] and r3["universo"] == "ids"
    assert all(u.startswith("https://api.openalex.org") for u, _ in sessao2.chamadas)
    assert not estado.pendencias_abertas(estado.carregar_estado(raiz))


def test_retratacoes_sem_rede_nao_grava(projeto_vazio, capsys, monkeypatch):
    from rslib import textos
    raiz = projeto_vazio
    _preparar_retratacoes(raiz)
    monkeypatch.setattr(textos, "criar_sessao_http", lambda: SessaoFalsa(falhar=True))
    monkeypatch.setattr(textos, "_dormir", lambda s: None)
    codigo, r = rodar(["--dir", str(raiz), "textos", "retratacoes"], capsys)
    assert codigo == 1 and "nenhuma consulta" in r["erro"]
    assert not (raiz / textos.ARQ_RETRATACOES).exists()


# ---------------------------------------------------------------------------
# Contato com autores
# ---------------------------------------------------------------------------
def test_contato_autores_valida_e_registra(projeto_vazio, capsys):
    from rslib import estado, textos
    from rslib.handoff import ler_csv
    raiz = projeto_vazio
    escrever_unicos(raiz)
    arq = raiz / "contatos.csv"
    arq.write_text(
        "chave,autor_contatado,data,pedido,resposta,dados_recebidos,observacao\n"
        "Castro2018,autor correspondente,2026-03-02,texto completo,,,x\n"
        "Alves2020,primeira autora,2026-03-01,médias e DP por grupo,enviou a tabela 2,Sim,\n"
        "Castro2018,autor correspondente,2026-03-02,texto completo,,,x\n", encoding="utf-8")
    codigo, r = rodar(["--dir", str(raiz), "textos", "contato-autores", "--registrar", str(arq)], capsys)
    assert codigo == 0, r
    assert (r["n_contatos"], r["n_textos"], r["n_sem_resposta"]) == (2, 2, 1)
    assert r["dados_recebidos"] == {"sim": 1, "parcial": 0, "nao": 0, "aguardando": 1}
    assert any("repetida" in a for a in r["avisos"]) and any("observacao" in a for a in r["avisos"])
    colunas, linhas = ler_csv(raiz / textos.ARQ_CONTATO_AUTORES)
    assert colunas == textos.COLUNAS_CONTATO_AUTORES and [l["chave"] for l in linhas] == ["Alves2020", "Castro2018"]
    assert linhas[0]["dados_recebidos"] == "sim"
    ev = [e for e in estado.ler_log(raiz) if e["evento"] == "contato_autores"]
    assert len(ev) == 1 and ev[0]["dados"]["chaves_sem_resposta"] == ["Castro2018"]

    codigo, r2 = rodar(["--dir", str(raiz), "textos", "contato-autores"], capsys)  # arquivo canônico
    assert codigo == 0 and r2["reexecucao"] is True
    assert len([e for e in estado.ler_log(raiz) if e["evento"] == "contato_autores"]) == 1

    arq.write_text(
        "chave,autor_contatado,data,pedido,resposta,dados_recebidos\n"
        "Alves2020,alves@universidade.br,2026-03-01,dados,,\n"
        "Nada1999,autor,01/03/2026,dados,,talvez\n", encoding="utf-8")
    codigo, r3 = rodar(["--dir", str(raiz), "textos", "contato-autores", "--registrar", str(arq)], capsys)
    assert codigo == 1
    for trecho in ("e-mail", "chave não existe", "AAAA-MM-DD", "talvez"):
        assert trecho in r3["erro"], trecho
    arq.write_text("chave,data\nAlves2020,2026-03-01\n", encoding="utf-8")
    codigo, r4 = rodar(["--dir", str(raiz), "textos", "contato-autores", "--registrar", str(arq)], capsys)
    assert codigo == 1 and "autor_contatado" in r4["erro"]


@pytest.mark.parametrize("argv", [
    ["textos", "retratacoes"], ["textos", "contato-autores"], ["textos", "elegibilidade", "consolidar"],
    ["textos", "inventario"],
])
def test_ajuda_dos_subcomandos_de_textos(argv, capsys):
    from rslib import textos
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    textos.registrar(parser.add_subparsers(dest="comando"))
    with pytest.raises(SystemExit) as saida:
        parser.parse_args([*argv, "--help"])
    assert saida.value.code == 0 and "usage" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# v1.2: pendência de retratação estável e planilhas humanas em qualquer formato
# ---------------------------------------------------------------------------
def test_regressao_retratacao_fechada_por_humano_nao_reabre_no_dia_seguinte(projeto_vazio, capsys, monkeypatch):
    from rslib import estado, textos
    raiz = projeto_vazio
    _preparar_retratacoes(raiz)
    obras = {"10.1234/alves2020": False, "10.1234/borges2019": True, "10.1234/castro2018": True,
             "10.1234/dias2021": False}
    monkeypatch.setattr(textos, "criar_sessao_http", lambda: SessaoFalsa(obras=dict(obras)))
    monkeypatch.setattr(textos, "_dormir", lambda s: None)
    monkeypatch.setattr(textos, "_hoje", lambda: "2026-09-01")
    codigo, r1 = rodar(["--dir", str(raiz), "textos", "retratacoes", "--fonte", "openalex"], capsys)
    assert codigo == 0 and r1["pendencia"] and r1["retratados"] == ["Borges2019", "Castro2018"]
    estado.fechar_pendencia(raiz, r1["pendencia"], "mantidos: retratação parcial de uma tabela não usada")

    # outro dia: retratacoes.csv muda (verificado_em), mas os retratados são os mesmos → não reabre
    monkeypatch.setattr(textos, "_hoje", lambda: "2026-09-15")
    codigo, r2 = rodar(["--dir", str(raiz), "textos", "retratacoes", "--fonte", "openalex"], capsys)
    assert codigo == 0 and r2["pendencia"] is None and r2["conferencia_ja_feita"] is True
    assert not estado.pendencias_abertas(estado.carregar_estado(raiz))
    codigo, r3 = rodar(["--dir", str(raiz), "textos", "retratacoes", "--fonte", "openalex"], capsys)
    assert r3["pendencia"] is None and not estado.pendencias_abertas(estado.carregar_estado(raiz))

    # retratação nova muda o conjunto → abre de novo, em qualquer modo
    obras["10.1234/alves2020"] = True
    codigo, r4 = rodar(["--dir", str(raiz), "textos", "retratacoes", "--fonte", "openalex"], capsys)
    abertas = estado.pendencias_abertas(estado.carregar_estado(raiz))
    assert r4["pendencia"] and [(p["tipo"], p["n"]) for p in abertas] == [("retratacao_texto", 3)]


def test_regressao_retratacao_mesmo_n_outros_textos_reabre(projeto_vazio, capsys, monkeypatch):
    from rslib import estado, textos
    raiz = projeto_vazio
    _preparar_retratacoes(raiz)
    obras = {"10.1234/alves2020": False, "10.1234/borges2019": True, "10.1234/castro2018": False,
             "10.1234/dias2021": False}
    monkeypatch.setattr(textos, "criar_sessao_http", lambda: SessaoFalsa(obras=dict(obras)))
    monkeypatch.setattr(textos, "_dormir", lambda s: None)
    codigo, r1 = rodar(["--dir", str(raiz), "textos", "retratacoes", "--fonte", "openalex"], capsys)
    estado.fechar_pendencia(raiz, r1["pendencia"], "conferido")
    obras.update({"10.1234/borges2019": False, "10.1234/castro2018": True})
    codigo, r2 = rodar(["--dir", str(raiz), "textos", "retratacoes", "--fonte", "openalex"], capsys)
    assert r2["pendencia"] and r2["conferencia_ja_feita"] is False, "mesmo n, outro texto retratado"


def test_regressao_planilhas_humanas_com_ponto_e_virgula(projeto_vazio, capsys, tmp_path):
    from rslib import esquema
    from rslib.handoff import ler_linhas
    raiz = projeto_vazio
    escrever_unicos(raiz, CHAVES[:4])
    pares = tmp_path / "pares.csv"
    pares.write_bytes("﻿id_rs_a;id_rs_b\r\nRS0002;rs0001\r\n".encode("utf-8"))
    codigo, r = rodar(["--dir", str(raiz), "textos", "ligar-relatos", "--pares", str(pares)], capsys)
    assert codigo == 0 and r["n_relatos_ligados"] == 2
    assert {l["id_rs"]: l["id_estudo"] for l in ler_linhas(raiz / esquema.ARQ_UNICOS)}["RS0002"] == "ES0001"

    contatos = tmp_path / "contatos.csv"
    contatos.write_text("chave;autor_contatado;data;pedido;resposta;dados_recebidos\n"
                        "Alves2020;primeira autora;2026-03-01;médias, DP;enviou;Sim\n", encoding="cp1252")
    codigo, r = rodar(["--dir", str(raiz), "textos", "contato-autores", "--registrar", str(contatos)], capsys)
    assert codigo == 0 and r["n_contatos"] == 1 and any("cp1252" in a for a in r["avisos"])
    assert ler_linhas(raiz / esquema.ARQ_CONTATO_AUTORES)[0]["pedido"] == "médias, DP"

    ids = tmp_path / "ids.csv"
    ids.write_text("id_rs;chave\nRS0001;Alves2020\nRS0003;Castro2018\n", encoding="utf-8")
    codigo, r = rodar(["--dir", str(raiz), "textos", "para-baixar", "--ids", str(ids)], capsys)
    assert codigo == 0 and r["n"] == 2


# ---------------------------------------------------------------------------
# Ids absorvidos pelo dedup depois da triagem (v1.4)
# ---------------------------------------------------------------------------
def test_elegibilidade_leva_ficha_e_decisao_de_absorvido_ao_registro_que_absorveu(projeto_vazio, capsys):
    from rslib import esquema, estado
    from rslib.handoff import ler_linhas
    raiz = projeto_vazio
    escrever_unicos(raiz, chaves=CHAVES[:6])  # Gomes2016 (RS0007) foi absorvido por Faria2017 (RS0006)
    estado.registrar_evento(raiz, "dedup_executado", "05_organizacao", "script", "dedup",
                            dados={"ids_rs_aposentados": {"RS0007": {"absorvido_por": "RS0006", "chave": "Gomes2016"}}})
    codigo, r1 = rodar(_argv_eleg(raiz), capsys)
    assert codigo == 0
    d = {l["chave"]: l for l in ler_linhas(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL)}
    assert "Gomes2016" not in d and d["Faria2017"]["id_rs"] == "RS0006"
    assert any("Gomes2016→Faria2017" in a for a in r1["avisos"])
    assert not any("Gomes2016" in a and "sem chave" in a for a in r1["avisos"])

    humana_tc(raiz, "RS0007", "excluir", "C2_desenho", "decidido antes da fusão")
    codigo, r2 = rodar(_argv_eleg(raiz), capsys)
    d = {l["chave"]: l for l in ler_linhas(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL)}
    assert (d["Faria2017"]["decisao"], d["Faria2017"]["criterio_falhou"]) == ("excluir", "C2_desenho")
    assert any("RS0007 passou a RS0006" in a for a in r2["avisos"])

    humana_tc(raiz, "RS0006", "incluir", motivo="decisão própria do registro que absorveu")
    codigo, r3 = rodar(_argv_eleg(raiz), capsys)
    d = {l["chave"]: l for l in ler_linhas(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL)}
    assert d["Faria2017"]["decisao"] == "incluir"
    assert any("RS0006 já tem decisão humana própria" in a for a in r3["avisos"])
