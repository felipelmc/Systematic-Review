"""Templates de relato (.qmd): renderizam com Quarto usando arquivos gerados falsos num diretório temporário.

Cada template é copiado para `<tmp>/07-relatorio/`, ao lado de `prisma.svg`, `declaracao_uso_ia.md` e
`references.bib` falsos, com `../06-analise/caixa_ferramentas.md` falso. Confere que:
- `quarto render --to html` sai com código 0 (includes resolvidos, bibliografia encontrada);
- o conteúdo dos arquivos incluídos aparece no HTML;
- o aviso de rascunho aparece com `rascunho: true` e some com `rascunho: false`;
- placeholders `{{PREFIXO_NOME}}` sobrevivem ao render (não são engolidos pelo Pandoc).
Sem Quarto no PATH, os testes são pulados.
"""

import csv
import re
import shutil
import subprocess

import pytest

from conftest import SKILL

TEMPLATES = SKILL / "assets" / "templates"
QUARTO = shutil.which("quarto")
AVISO_RASCUNHO = "Não circule"

SVG_FALSO = """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60">
<rect x="1" y="1" width="198" height="58" fill="#fff" stroke="#000"/>
<text x="10" y="35" font-size="12">Fluxograma de teste</text></svg>
"""
DECLARACAO_FALSA = """# Declaração de uso de inteligência artificial

Gerado a partir de `rs_log.jsonl` (teste).

## 1. Ferramentas e modelos

| Modelo | Etapas |
|---|---|
| modelo-teste | 06_triagem_ta |
"""
CAIXA_FALSA = """# Caixa de ferramentas

Regras: `caixa-2` (Apêndice B). Entradas: 06-analise/certeza.csv.

| Família × outcome | Dimensão | Rótulo | Status |
|---|---|---|---|
| Família teste × desfecho teste | efeito | Inconclusivo | definido |
"""
BIB_FALSA = """@article{Teste2020,
  title = {Artigo de teste},
  author = {Teste, Ana},
  year = {2020},
  journal = {Revista de Teste}
}
"""
CASOS = {
    "relatorio_oqf.qmd": ["Caixa de ferramentas", "Declaração de uso de inteligência artificial", "Família teste"],
    "manuscrito_prisma.qmd": ["Declaração de uso de inteligência artificial"],
    "relatorio_escopo.qmd": ["Declaração de uso de inteligência artificial"],
    "policy_brief.qmd": ["Mensagens principais"],
}

pytestmark = pytest.mark.skipif(QUARTO is None, reason="Quarto não instalado")


def _montar(tmp_path, nome):
    rel = tmp_path / "07-relatorio"
    analise = tmp_path / "06-analise"
    rel.mkdir(parents=True)
    analise.mkdir(parents=True)
    alvo = rel / nome
    shutil.copy(TEMPLATES / nome, alvo)
    (rel / "prisma.svg").write_text(SVG_FALSO, encoding="utf-8")
    (rel / "declaracao_uso_ia.md").write_text(DECLARACAO_FALSA, encoding="utf-8")
    (rel / "references.bib").write_text(BIB_FALSA, encoding="utf-8")
    (analise / "caixa_ferramentas.md").write_text(CAIXA_FALSA, encoding="utf-8")
    return alvo


def _render(qmd):
    proc = subprocess.run([QUARTO, "render", qmd.name, "--to", "html"], cwd=qmd.parent,
                          capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    html = qmd.with_suffix(".html")
    assert html.exists()
    return html.read_text(encoding="utf-8")


@pytest.mark.parametrize("nome", sorted(CASOS))
def test_template_renderiza_com_arquivos_gerados(tmp_path, nome):
    qmd = _montar(tmp_path, nome)
    texto = qmd.read_text(encoding="utf-8")
    assert re.search(r"^rascunho: true$", texto, re.MULTILINE), "template deve nascer como rascunho"
    assert "<!--" in texto and re.search(r"\{\{[A-Z][A-Z0-9_]+\}\}", texto)

    html = _render(qmd)
    for trecho in CASOS[nome]:
        assert trecho in html, f"{nome}: '{trecho}' não apareceu no HTML"
    assert AVISO_RASCUNHO in html
    assert "{{TEXTO_AUTORES}}" in html, "placeholder foi engolido no render"
    assert "{{<" not in html, "shortcode não resolvido"

    qmd.write_text(texto.replace("\nrascunho: true\n", "\nrascunho: false\n"), encoding="utf-8")
    html = _render(qmd)
    assert AVISO_RASCUNHO not in html


def test_includes_apontam_para_arquivos_da_skill():
    """Os includes dos templates só referenciam arquivos que comandos da skill geram."""
    gerados = {"declaracao_uso_ia.md", "../06-analise/caixa_ferramentas.md"}
    for qmd in TEMPLATES.glob("*.qmd"):
        includes = set(re.findall(r"\{\{< include (\S+) >\}\}", qmd.read_text(encoding="utf-8")))
        assert includes <= gerados, f"{qmd.name}: include desconhecido {includes - gerados}"


def test_checklists_prisma_scr_e_swim():
    from rslib import prisma
    pasta = SKILL / "assets" / "checklists"
    itens, origem = prisma.carregar_checklist("scr")
    assert origem == "prisma_scr.csv", "prisma.py deve ler o CSV (sem linha de comentário), não a lista embutida"
    assert [tuple(i.values()) for i in itens] == [tuple(i) for i in prisma.CHECKLIST_SCR_EMBUTIDO]

    linhas = [l for l in open(pasta / "swim.csv", encoding="utf-8") if not l.startswith("#")]
    swim = list(csv.DictReader(linhas))
    assert list(swim[0]) == ["item", "secao", "topico", "descricao"]
    assert [l["item"] for l in swim] == ["1a", "1b", "2", "3", "4", "5", "6", "7", "8", "9"]
    assert all(l["descricao"].strip() for l in swim)
