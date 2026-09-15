"""Testes do leitor único de planilhas humanas (rslib/planilhas.py) e de quem passou a usá-lo."""

import pytest

from rslib import planilhas
from rslib import triagem_lotes as tl


COLUNAS = ["id_rs", "decisao_humana", "motivo_humano"]


def _texto(delimitador):
    return delimitador.join(COLUNAS) + "\r\n" + delimitador.join(["RS0001", "excluir", "não é município; nem estado"
                                                                  if delimitador != ";" else "não é município"]) + "\r\n"


@pytest.mark.parametrize("codificacao", ["utf-8", "utf-8-sig", "cp1252", "utf-16", "utf-16-le"])
@pytest.mark.parametrize("delimitador", [",", ";", "\t"])
def test_le_todas_as_combinacoes_de_codificacao_e_delimitador(tmp_path, codificacao, delimitador):
    arq = tmp_path / "fila.csv"
    texto = _texto(delimitador)
    if delimitador == ",":
        texto = texto.replace("não é município; nem estado", '"não é município, nem estado"')
    arq.write_bytes(texto.encode(codificacao))
    colunas, linhas, info = planilhas.ler_tabela_humana(arq, ["id_rs", "decisao_humana"])
    assert colunas == COLUNAS and info["delimitador"] == delimitador
    assert linhas[0]["id_rs"] == "RS0001" and linhas[0]["motivo_humano"].startswith("não é município")
    assert info["codificacao"] == {"utf-8-sig": "utf-8", "utf-16-le": "utf-16"}.get(codificacao, codificacao)
    assert any("cp1252" in a for a in info["avisos"]) == (codificacao == "cp1252")


def test_xlsx_aba_e_meta(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "instrucoes"
    ws.append(["leia"])
    cod = wb.create_sheet("codificacao")
    cod.append(["ID_RS", "decisao_h1", "ano"])
    cod.append(["RS0002", "incluir", 2020.0])
    meta = wb.create_sheet("_meta")
    meta.append(["desenho", "02-triagem/validacao/ta_v1/amostra01_desenho.json"])
    arq = tmp_path / "amostra.xlsx"
    wb.save(arq)
    colunas, linhas, info = planilhas.ler_tabela_humana(arq, ["id_rs"], aba="codificacao")
    assert info["formato"] == "xlsx" and linhas == [{"id_rs": "RS0002", "decisao_h1": "incluir", "ano": "2020"}]
    assert planilhas.ler_meta_xlsx(arq) == {"desenho": "02-triagem/validacao/ta_v1/amostra01_desenho.json"}
    assert planilhas.ler_meta_xlsx(tmp_path / "nao_e_xlsx.csv") == {}


def test_erros_e_aliases(tmp_path):
    arq = tmp_path / "t.csv"
    arq.write_text("id;obs\nRS0001;x\n", encoding="utf-8")
    with pytest.raises(planilhas.ErroUso, match="colunas obrigatórias"):
        planilhas.ler_tabela_humana(arq, ["id_rs"])
    with pytest.raises(planilhas.ErroUso, match=".xls antigo"):
        (tmp_path / "v.xls").write_bytes(b"x")
        planilhas.ler_tabela_humana(tmp_path / "v.xls")
    # triagem_lotes mantém os nomes: quem captura tl.ErroUso continua capturando
    assert tl.ErroUso is planilhas.ErroUso and tl.ErroDependencia is planilhas.ErroDependencia
    assert tl.ler_tabela_humana is planilhas.ler_tabela_humana
    assert issubclass(planilhas.ErroDependencia, planilhas.ErroUso)


def test_ler_texto_humano(tmp_path):
    arq = tmp_path / "criterios.md"
    arq.write_bytes("﻿# Critérios\n- C1 população\n".encode("utf-8"))
    texto, codificacao, avisos = planilhas.ler_texto_humano(arq)
    assert texto.startswith("# Critérios") and codificacao == "utf-8" and avisos == []
    arq.write_bytes("# Critérios\n".encode("cp1252"))
    texto, codificacao, avisos = planilhas.ler_texto_humano(arq)
    assert texto == "# Critérios\n" and codificacao == "cp1252" and avisos
