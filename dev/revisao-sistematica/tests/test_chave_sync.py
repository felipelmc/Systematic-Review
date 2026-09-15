"""Sincronia de chave.py entre as skills de revisão e smoke tests das skills irmãs.

Por que existe: a chave Sobrenome+Ano é o único elo entre PDF (`<chave>.pdf`), ficha
(`fichamento_<chave>.md`), entrada do .bib e `id_rs` da revisão. Uma cópia de chave.py
que divirja das outras quebra esses joins em silêncio. Este teste compara o sha256 das
quatro cópias, confere que os scripts irmãos usam o módulo (e não uma reimplementação
local), e roda cada script irmão com `--help` e com uma entrada mínima sintética.

As irmãs ficam em `skills/` na raiz deste repositório (cópia versionada). O diretório pode
ser trocado por `RS_SKILLS_DIR` (por exemplo, `~/.claude/skills` para testar a instalação).
"""

import csv
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import FIXTURES, RAIZ_REPO, SCRIPTS

DIR_SKILLS = Path(os.environ.get("RS_SKILLS_DIR") or RAIZ_REPO / "skills")
IRMAS = ["baixar-pdfs-academicos", "gerar-bibtex", "fichamento-sistematico"]
CHAVE_CANONICA = SCRIPTS / "rslib" / "chave.py"

pytestmark = pytest.mark.skipif(
    not all((DIR_SKILLS / s / "scripts").is_dir() for s in IRMAS),
    reason=f"skills irmãs não encontradas em {DIR_SKILLS} (defina RS_SKILLS_DIR)",
)

# Scripts irmãos e os pacotes de que cada um precisa para rodar.
SCRIPTS_IRMAOS = {
    ("baixar-pdfs-academicos", "baixar_pdfs.py"): ["pandas", "requests"],
    ("baixar-pdfs-academicos", "verificar_conteudo.py"): ["pandas"],
    ("baixar-pdfs-academicos", "mesclar_achados_agentes.py"): ["pandas"],
    ("gerar-bibtex", "gerar_bib.py"): ["pandas"],
    ("fichamento-sistematico", "verify_citacoes.py"): [],
    ("fichamento-sistematico", "consolida.py"): [],
    ("fichamento-sistematico", "amostrar_validacao.py"): [],
    ("fichamento-sistematico", "concordancia.py"): [],
}


# ---------------------------------------------------------------------------
# utilitários
# ---------------------------------------------------------------------------
def _sha256(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def _script(skill, nome):
    return DIR_SKILLS / skill / "scripts" / nome


def _rodar(skill, nome, *args, cwd=None, timeout=120):
    """Roda um script irmão num processo novo, sem gravar bytecode na pasta da skill."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    env.pop("PDF_DOWNLOADER_EMAIL", None)
    return subprocess.run(
        [sys.executable, str(_script(skill, nome)), *map(str, args)],
        capture_output=True, text=True, cwd=cwd, env=env, timeout=timeout,
    )


def _importar(skill, nome):
    """Importa um script irmão como módulo sem escrever __pycache__ na skill."""
    for pacote in SCRIPTS_IRMAOS.get((skill, nome), []):
        pytest.importorskip(pacote)
    anterior = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        modulo_nome = f"_irma_{skill.replace('-', '_')}_{Path(nome).stem}"
        spec = importlib.util.spec_from_file_location(modulo_nome, _script(skill, nome))
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return modulo
    finally:
        sys.dont_write_bytecode = anterior


def _golden():
    with open(FIXTURES / "chaves_golden.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _descricao(skill_md):
    """Texto da `description` do frontmatter (bloco dobrado `>-` ou linha simples)."""
    texto = Path(skill_md).read_text(encoding="utf-8")
    frontmatter = texto.split("---", 2)[1]
    try:
        import yaml
        return yaml.safe_load(frontmatter)["description"]
    except ImportError:
        m = re.search(r"description: >-\n((?:  .*\n)+)", frontmatter)
        if m:
            return " ".join(l.strip() for l in m.group(1).splitlines())
        return re.search(r"description:\s*(.*)", frontmatter).group(1).strip()


def _pdf_minimo(caminho):
    """Bytes que passam em baixar_pdfs.is_valid_pdf (%PDF, %%EOF, >= 1000 bytes)."""
    Path(caminho).write_bytes(b"%PDF-1.4\n" + b"%" + b"0" * 1200 + b"\n%%EOF\n")


# ---------------------------------------------------------------------------
# sincronia do módulo de chave
# ---------------------------------------------------------------------------
def test_sha256_das_quatro_copias_iguais():
    esperado = _sha256(CHAVE_CANONICA)
    copias = {s: _sha256(_script(s, "chave.py")) for s in IRMAS}
    assert copias == {s: esperado for s in IRMAS}


def test_scripts_nao_reimplementam_chave():
    """Nenhuma cópia local de gerar_chave/sobrenome: todos importam de chave.py."""
    for skill, nome in SCRIPTS_IRMAOS:
        fonte = _script(skill, nome).read_text(encoding="utf-8")
        assert "def gerar_chave" not in fonte, (skill, nome)
    for skill, nome in [("baixar-pdfs-academicos", "baixar_pdfs.py"), ("gerar-bibtex", "gerar_bib.py")]:
        fonte = _script(skill, nome).read_text(encoding="utf-8")
        assert re.search(r"^from chave import .*gerar_chave", fonte, re.M), (skill, nome)
    fonte = _script("baixar-pdfs-academicos", "verificar_conteudo.py").read_text(encoding="utf-8")
    assert re.search(r"^import chave\b", fonte, re.M)


@pytest.mark.parametrize("skill,nome", [("baixar-pdfs-academicos", "baixar_pdfs.py"),
                                        ("gerar-bibtex", "gerar_bib.py")])
def test_gerar_chave_das_irmas_bate_com_tabela_ouro(skill, nome):
    modulo = _importar(skill, nome)
    for linha in _golden():
        assert modulo.gerar_chave("", linha["autores"], linha["ano"], set()) == linha["chave_esperada"], linha


def test_aliases_de_chave_sem_id_nem_key():
    baixar = _importar("baixar-pdfs-academicos", "baixar_pdfs.py")
    bib = _importar("gerar-bibtex", "gerar_bib.py")
    assert baixar.ALIASES_COLUNA["chave"] == ["chave", "citekey", "bib_key"]
    assert bib.ALIASES["chave"] == ["chave", "citekey", "bib_key"]


def test_sobrenome_autor_usa_chave():
    verificar = _importar("baixar-pdfs-academicos", "verificar_conteudo.py")
    casos = {
        "Weihs M.": "weihs",
        "Shahidul Islam M.; Rahman A.": "shahidul islam",
        "João da Silva Filho": "silva",
        "Brigitti Bonetti|Viviane Theiss": "bonetti",
        "Hedström, Peter": "hedstrom",
        "JF de Oliveira, JC Libâneo": "de oliveira",
    }
    for autores, esperado in casos.items():
        assert verificar.sobrenome_autor(autores) == esperado, autores
    assert verificar.sobrenome_autor("") is None
    assert verificar.sobrenome_autor(float("nan")) is None


def test_veredito_casa_sobrenome_composto_quebrado_em_linhas():
    verificar = _importar("baixar-pdfs-academicos", "verificar_conteudo.py")
    texto = ("Microcredit and household welfare in rural Bangladesh\nM. Shahidul\nIslam and A. Rahman\n"
             + "Abstract. " + "We study credit access and consumption smoothing. " * 8)
    r = verificar.veredito_conteudo("Microcredit and household welfare in rural Bangladesh",
                                    "Shahidul Islam M.; Rahman A.", texto)
    assert r["autor_encontrado"] is True and r["veredito"] == "confere"


def test_formatar_autores_usa_lista_autores():
    bib = _importar("gerar-bibtex", "gerar_bib.py")
    assert bib.formatar_autores("Weihs M.; Rahman A.") == "Weihs M. and Rahman A."
    assert bib.formatar_autores("Brigitti Bonetti|Viviane Theiss") == "Brigitti Bonetti and Viviane Theiss"
    assert bib.formatar_autores("Silva, João, Souza, Maria") == "Silva, João and Souza, Maria"
    assert bib.formatar_autores("Viana, Renata and Campagnoni, Mariana") == "Viana, Renata and Campagnoni, Mariana"
    assert bib.formatar_autores("Organisation for Economic Co-operation and Development") == \
        "{Organisation for Economic Co-operation and Development}"
    assert bib.formatar_autores(None) is None and bib.formatar_autores(float("nan")) is None


# ---------------------------------------------------------------------------
# SKILL.md e higiene das irmãs
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("skill", IRMAS)
def test_skill_md_portavel_e_description_curta(skill):
    skill_md = DIR_SKILLS / skill / "SKILL.md"
    texto = skill_md.read_text(encoding="utf-8")
    assert "~/.claude/skills" not in texto
    assert "${CLAUDE_SKILL_DIR}/" in texto
    descricao = _descricao(skill_md)
    assert 0 < len(descricao) <= 1024, len(descricao)


def test_sem_referencia_a_fichamento_academico():
    for skill in IRMAS:
        for arq in (DIR_SKILLS / skill).rglob("*"):
            if arq.is_file() and arq.suffix in {".md", ".py", ".csv", ".txt"}:
                assert "fichamento-academico" not in arq.read_text(encoding="utf-8"), arq


def test_gatilhos_principais_preservados():
    gatilhos = {
        "baixar-pdfs-academicos": ["baixar os PDFs desses papers", "buscar esse artigo/DOI",
                                   "baixar essa tese/dissertação", "checar quais artigos ainda faltam baixar"],
        "fichamento-sistematico": ["fichar o corpus", "extrair os dados dos textos incluídos",
                                   "data extraction", "calcular a concordância entre codificadores",
                                   "gerar o codebook da minha revisão"],
        "gerar-bibtex": ["gerar o .bib", "criar as referências em BibTeX", "LaTeX/Overleaf"],
    }
    for skill, frases in gatilhos.items():
        descricao = _descricao(DIR_SKILLS / skill / "SKILL.md")
        for frase in frases:
            assert frase in descricao, (skill, frase)


def test_irmas_sem_ds_store():
    for skill in IRMAS:
        assert not list((DIR_SKILLS / skill).rglob(".DS_Store")), skill


def test_irmas_sem_caminhos_pessoais():
    padrao = re.compile(r"/Users/|/home/[a-z]|hotmail|gmail\.com", re.IGNORECASE)
    for skill in IRMAS:
        for arq in (DIR_SKILLS / skill).rglob("*"):
            if arq.is_file() and arq.suffix in {".md", ".py", ".csv", ".txt"}:
                assert not padrao.search(arq.read_text(encoding="utf-8")), arq


# ---------------------------------------------------------------------------
# smoke tests: --help
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("skill,nome", list(SCRIPTS_IRMAOS))
def test_help_de_cada_script_irmao(skill, nome):
    for pacote in SCRIPTS_IRMAOS[(skill, nome)]:
        pytest.importorskip(pacote)
    pycache = _script(skill, nome).parent / "__pycache__"
    existia = pycache.exists()
    r = _rodar(skill, nome, "--help")
    assert r.returncode == 0, r.stderr
    assert "usage" in r.stdout.lower()
    if not existia:
        assert not pycache.exists(), "script gravou __pycache__ na pasta da skill"


# ---------------------------------------------------------------------------
# smoke tests: CSV mínimo
# ---------------------------------------------------------------------------
def _escrever_csv(caminho, cabecalho, linhas):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cabecalho)
        w.writerows(linhas)


def test_gerar_bib_csv_minimo(tmp_path):
    pytest.importorskip("pandas")
    planilha = tmp_path / "incluidos.csv"
    _escrever_csv(planilha, ["titulo", "autores", "ano", "doi", "tipo", "journal", "chave", "id"], [
        ["Sharing detailed research data", "Piwowar, Heather A.; Day, Roger S.", "2007",
         "https://doi.org/10.1371/journal.pone.0000308", "article", "PLoS ONE", "Piwowar2007", "W1"],
        ["Screen time and grades", "Weihs M.; Rahman A.", "2025", "", "article", "Revista A",
         "https://openalex.org/W2741809807", "https://openalex.org/W2"],
        ["Contabilidade rural", "Brigitti Bonetti|Viviane Theiss", "2020", "", "", "", "", "W3"],
        ["Second paper same author", "Weihs M.", "2025.0", "", "Book Chapter", "Livro B", "", "W4"],
        ["Education at a glance", "Organisation for Economic Co-operation and Development", "2020",
         "", "report", "OECD", "", "W5"],
    ])
    saida = tmp_path / "references.bib"
    r = _rodar("gerar-bibtex", "gerar_bib.py", "--planilha", planilha, "--out", saida)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "chave inválida" in r.stdout and "1 chaves existentes inválidas" in r.stdout
    bib = saida.read_text(encoding="utf-8")
    chaves = re.findall(r"^@\w+\{([^,]+),", bib, re.M)
    assert chaves == ["Piwowar2007", "Weihs2025", "Bonetti2020", "Weihs2025a", "Development2020"]
    assert "author  = {Weihs M. and Rahman A.}" in bib
    assert "author  = {Brigitti Bonetti and Viviane Theiss}" in bib
    assert "author  = {{Organisation for Economic Co-operation and Development}}" in bib
    assert "doi     = {10.1371/journal.pone.0000308}" in bib
    assert "@incollection{Weihs2025a," in bib


def test_gerar_bib_ignora_coluna_id(tmp_path):
    pytest.importorskip("pandas")
    planilha = tmp_path / "openalex.csv"
    _escrever_csv(planilha, ["id", "title", "authors", "year"], [
        ["https://openalex.org/W1", "A title", "Hedström, Peter", "2010"],
    ])
    saida = tmp_path / "refs.bib"
    r = _rodar("gerar-bibtex", "gerar_bib.py", "--planilha", planilha, "--out", saida)
    assert r.returncode == 0, r.stderr
    assert saida.read_text(encoding="utf-8").startswith("@article{Hedstrom2010,")


def test_gerar_bib_dissertacao_e_evento(tmp_path):
    """tipo_publicacao do esquema (dissertacao, evento) vira @mastersthesis/school e @inproceedings/booktitle."""
    pytest.importorskip("pandas")
    planilha = tmp_path / "incluidos.csv"
    _escrever_csv(planilha, ["chave", "titulo", "autores", "ano", "doi", "tipo_publicacao", "nome_publicacao"], [
        ["Souza2017", "Transferências e frequência escolar", "Souza, Gabriela", "2017", "", "dissertacao", "UFPE"],
        ["Lima2018", "Bolsa e evasão", "Lima, Rui", "2018", "", "dissertação", "USP"],
        ["Reis2016", "Mestrado sobre merenda", "Reis, Ana", "2016", "", "Dissertação de mestrado", "UFMG"],
        ["Costa2019", "Anais sobre programas", "Costa, Bia", "2019", "", "evento", "Anais do Encontro X"],
        ["Dias2020", "Doctoral work", "Dias, Eva", "2020", "", "tese", "Unicamp"],
        ["Melo2021", "Paper at a conference", "Melo, Rui", "2021", "", "Conference paper", "Proc. Y"],
    ])
    saida = tmp_path / "references.bib"
    r = _rodar("gerar-bibtex", "gerar_bib.py", "--planilha", planilha, "--out", saida, "--col-chave", "chave")
    assert r.returncode == 0, r.stderr + r.stdout
    bib = saida.read_text(encoding="utf-8")
    for chave in ("Souza2017", "Lima2018", "Reis2016"):
        assert f"@mastersthesis{{{chave}," in bib
    assert "school = {UFPE}" in bib and "@phdthesis{Dias2020," in bib
    assert "@inproceedings{Costa2019," in bib and "booktitle = {Anais do Encontro X}" in bib
    assert "@inproceedings{Melo2021," in bib


def test_gerar_bib_chave_gerada_nao_colide_com_chave_de_linha_posterior(tmp_path):
    pytest.importorskip("pandas")
    planilha = tmp_path / "papers.csv"
    _escrever_csv(planilha, ["titulo", "autores", "ano", "chave"], [
        ["Primeiro texto", "Silva, João", "2020", ""],
        ["Segundo texto", "Silva, Maria", "2020", "Silva2020"],
        ["Terceiro texto", "Silva, Ana", "2020", "https://openalex.org/W1"],
    ])
    saida = tmp_path / "refs.bib"
    r = _rodar("gerar-bibtex", "gerar_bib.py", "--planilha", planilha, "--out", saida)
    assert r.returncode == 0, r.stderr
    chaves = re.findall(r"^@\w+\{([^,]+),", saida.read_text(encoding="utf-8"), re.M)
    assert chaves == ["Silva2020a", "Silva2020", "Silva2020b"]


def test_baixar_pdfs_batch_chave_gerada_nao_colide_com_linha_posterior(tmp_path):
    pytest.importorskip("pandas")
    pytest.importorskip("requests")
    planilha = tmp_path / "para_baixar.csv"
    _escrever_csv(planilha, ["chave", "titulo", "autores", "ano", "doi"], [
        ["", "Primeiro texto", "Silva, João", "2020", ""],
        ["Silva2020", "Segundo texto", "Silva, Maria", "2020", ""],
    ])
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    for chave in ("Silva2020a", "Silva2020"):  # PDFs presentes: o script não sai para a rede
        _pdf_minimo(pdfs / f"{chave}.pdf")
    relatorio = tmp_path / "relatorio_pdfs.csv"
    r = _rodar("baixar-pdfs-academicos", "baixar_pdfs.py", "batch", "--planilha", planilha,
               "--saida-pdfs", pdfs, "--relatorio", relatorio, "--email", "revisor@example.org", timeout=60)
    assert r.returncode == 0, r.stderr + r.stdout
    with open(relatorio, encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f))
    assert [(l["chave"], l["status"]) for l in linhas] == [("Silva2020a", "ja_existia"), ("Silva2020", "ja_existia")]


def test_baixar_pdfs_batch_csv_minimo_sem_rede(tmp_path):
    """PDFs já presentes para as chaves esperadas: o script não sai para a rede."""
    pytest.importorskip("pandas")
    pytest.importorskip("requests")
    planilha = tmp_path / "para_baixar.csv"
    _escrever_csv(planilha, ["chave", "titulo", "autor", "ano", "doi", "id"], [
        ["https://openalex.org/W1", "Screen time and grades", "Weihs M.; Rahman A.", "2025", "", "W1"],
        ["", "Microcredit in rural Bangladesh", "João da Silva Filho", "2014", "10.1234/abc", "W2"],
        ["Piwowar2007", "Sharing detailed research data", "Piwowar, H", "2007", "", "W3"],
    ])
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    for chave in ["Weihs2025", "Silva2014", "Piwowar2007"]:
        _pdf_minimo(pdfs / f"{chave}.pdf")
    relatorio = tmp_path / "relatorio_pdfs.csv"
    r = _rodar("baixar-pdfs-academicos", "baixar_pdfs.py", "batch", "--planilha", planilha,
               "--saida-pdfs", pdfs, "--relatorio", relatorio, "--email", "revisor@example.org",
               timeout=60)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "chave inválida" in r.stdout
    with open(relatorio, encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f))
    assert [l["chave"] for l in linhas] == ["Weihs2025", "Silva2014", "Piwowar2007"]
    assert {l["status"] for l in linhas} == {"ja_existia"}
    assert sorted(p.name for p in pdfs.iterdir()) == ["Piwowar2007.pdf", "Silva2014.pdf", "Weihs2025.pdf"]


def test_verificar_conteudo_csv_minimo(tmp_path):
    pytest.importorskip("pandas")
    fitz = pytest.importorskip("fitz")
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    doc = fitz.open()
    pagina = doc.new_page()
    texto = ("Microcredit and household welfare in rural Bangladesh\n\nM. Shahidul\nIslam and A. Rahman\n\n"
             "Abstract. We study how access to microcredit changes household consumption\n"
             "smoothing in rural districts, using survey panels collected over five years.\n"
             "Results indicate modest gains for the poorest households and none for others.\n")
    pagina.insert_text((50, 72), texto, fontsize=10)
    doc.save(pdfs / "ShahidulIslam2019.pdf")
    doc.close()
    relatorio = tmp_path / "relatorio_pdfs.csv"
    _escrever_csv(relatorio, ["chave", "titulo", "autores", "ano", "doi", "status", "fonte", "url",
                              "versao", "motivo", "arquivo"], [
        ["ShahidulIslam2019", "Microcredit and household welfare in rural Bangladesh",
         "Shahidul Islam M.; Rahman A.", "2019", "", "ok", "teste", "", "", "", ""],
    ])
    r = _rodar("baixar-pdfs-academicos", "verificar_conteudo.py", "--pdfs", pdfs, "--relatorio", relatorio)
    assert r.returncode == 0, r.stderr + r.stdout
    with open(tmp_path / "verificacao_conteudo.csv", encoding="utf-8-sig") as f:
        linha = next(csv.DictReader(f))
    assert linha["chave"] == "ShahidulIslam2019"
    assert linha["veredito"] == "confere" and linha["autor_encontrado"] == "True"


def test_mesclar_achados_csv_minimo(tmp_path):
    pytest.importorskip("pandas")
    relatorio = tmp_path / "relatorio_pdfs.csv"
    _escrever_csv(relatorio, ["chave", "titulo", "autores", "ano", "doi", "status", "fonte", "url",
                              "versao", "motivo", "arquivo"], [
        ["Weihs2025", "Screen time", "Weihs M.", "2025", "", "nao_encontrado", "", "", "", "", ""],
    ])
    achados = tmp_path / "achados.json"
    achados.write_text(json.dumps([{"chave": "Weihs2025", "encontrado": False, "motivo": "sem cópia"}]),
                       encoding="utf-8")
    r = _rodar("baixar-pdfs-academicos", "mesclar_achados_agentes.py", "--relatorio", relatorio,
               "--achados", achados, "--saida-pdfs", tmp_path)
    assert r.returncode == 0, r.stderr
    with open(relatorio, encoding="utf-8-sig") as f:
        linha = next(csv.DictReader(f))
    assert linha["status"] == "nao_encontrado" and linha["motivo"] == "sem cópia"


# ---------------------------------------------------------------------------
# fichamento-sistematico: fluxo mínimo e PABAK
# ---------------------------------------------------------------------------
CODEBOOK = [
    ["Identificacao", "ano", "Ano", "Extraia o ano.", "numerica_int", ""],
    ["Metodo", "tipo_estudo", "Tipo de estudo", "Classifique.", "categorica", ""],
    ["Resultados", "principal_achado", "Achado", "Resuma.", "textual", ""],
]


def _ficha(pasta, citekey, ano, tipo, achado):
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"fichamento_{citekey}.md").write_text(
        f"---\ncitekey: {citekey}\nficha_id: {citekey}\nn_fichas_do_texto: 1\noffset_pagina: 0\n---\n\n"
        f"## Identificacao\n- **ano** — resposta: {ano} — evidência: \"published in {ano}\" (p. 1)\n\n"
        f"## Metodo\n- **tipo_estudo** — resposta: {tipo} — evidência: \"we use survey data\" (p. 1)\n\n"
        f"## Resultados\n- **principal_achado** — resposta: {achado} — evidência: \"gains were modest\" (p. 1)\n\n"
        "## Notas do codificador\nnenhuma\n",
        encoding="utf-8",
    )


def test_fichamento_fluxo_minimo_com_pabak(tmp_path):
    codebook = tmp_path / "codebook.csv"
    _escrever_csv(codebook, ["dimensao", "variavel", "descricao", "prompt", "tipo", "aplicavel_se"], CODEBOOK)
    orig, val = tmp_path / "fichas", tmp_path / "fichas" / "_validacao"
    tipos_a = ["teorico", "teorico", "empirico-quantitativo"]
    tipos_b = ["teorico", "empirico-qualitativo", "empirico-quantitativo"]
    for i, ck in enumerate(["Silva2020", "Souza2021", "Weihs2025"]):
        _ficha(orig, ck, 2020 + i, tipos_a[i], "credit access raised consumption modestly")
        _ficha(val, ck, 2020 + i, tipos_b[i], "credit access raised consumption modestly")

    master = tmp_path / "fichamentos_master.csv"
    r = _rodar("fichamento-sistematico", "consolida.py", "--fichas", orig, "--codebook", codebook,
               "--out-csv", master)
    assert r.returncode == 0, r.stderr
    with open(master, encoding="utf-8") as f:
        assert [l["citekey"] for l in csv.DictReader(f)] == ["Silva2020", "Souza2021", "Weihs2025"]

    amostra = tmp_path / "amostra_validacao.csv"
    r = _rodar("fichamento-sistematico", "amostrar_validacao.py", "--consolidado", master,
               "--fracao", "1", "--semente", "7", "--out", amostra)
    assert r.returncode == 0, r.stderr

    saidas = tmp_path / "saidas"
    r = _rodar("fichamento-sistematico", "concordancia.py", "--original", orig, "--validacao", val,
               "--codebook", codebook, "--amostra", amostra, "--out-dir", saidas)
    assert r.returncode == 0, r.stderr
    assert "[limiares] variáveis sinalizadas" in r.stdout and "tipo_estudo" in r.stdout

    with open(saidas / "concordancia.csv", encoding="utf-8") as f:
        linhas = list(csv.reader(f))
    cabecalho = next(l for l in linhas if l[:2] == ["nivel", "variavel"])
    # colunas antigas intactas e na mesma ordem; novas só acrescentadas no fim
    assert cabecalho[:5] == ["nivel", "variavel", "n_textos", "concordancia_media", "cohen_kappa"]
    assert cabecalho[5:] == ["pabak", "concordancia_valores", "sinalizada", "motivo_sinalizacao"]
    por_var = {l[1]: dict(zip(cabecalho, l)) for l in linhas if l and l[0] == "por_variavel"}
    tipo = por_var["tipo_estudo"]
    assert float(tipo["pabak"]) == pytest.approx(0.5, abs=1e-4)       # k=3, Po=2/3
    assert tipo["sinalizada"] == "sim"
    assert set(tipo["motivo_sinalizacao"].split("|")) == {"concordancia<80%", "kappa_e_pabak<0.7"}
    assert por_var["principal_achado"]["sinalizada"] == "nao" and por_var["principal_achado"]["pabak"] == ""
    assert por_var["ano"]["sinalizada"] == "nao"

    relatorio = (saidas / "RELATORIO_CONCORDANCIA.md").read_text(encoding="utf-8")
    assert "| Variável | N | Conc. valores | Cohen's κ | PABAK | Sinalizada |" in relatorio
    assert "## Variáveis sinalizadas pelos limiares de validação" in relatorio
    assert "- **tipo_estudo** (categorica)" in relatorio
    assert "a amostra tem 3 textos" in relatorio


def test_pabak_e_limiares_unitarios():
    conc = _importar("fichamento-sistematico", "concordancia.py")
    # prevalência alta: κ negativo, mas PABAK 0,8 e concordância 90% -> não sinaliza
    pares = [("nao", "nao")] * 18 + [("sim", "nao"), ("nao", "sim")]
    k, pb = conc.cohen_kappa(pares), conc.pabak(pares)
    assert k == pytest.approx(-0.0526, abs=1e-3) and pb == pytest.approx(0.8)
    assert conc.avaliar_limiares("categorica", 0.9, k, pb) == (False, [])
    # k observado = 1 categoria -> PABAK com k = 2
    assert conc.pabak([("a", "a")] * 5) == pytest.approx(1.0)
    assert conc.pabak([]) is None
    assert conc.avaliar_limiares("categorica", 0.85, 0.65, 0.69) == (True, ["kappa_e_pabak<0.7"])
    assert conc.avaliar_limiares("categorica", 0.75, 0.9, 0.9) == (True, ["concordancia<80%"])
    assert conc.avaliar_limiares("categorica", 0.9, None, None) == (True, ["kappa_e_pabak<0.7"])
    assert conc.avaliar_limiares("textual", 0.8, None, None) == (False, [])
    assert conc.avaliar_limiares("textual", None, None, None) == (True, ["concordancia<80%"])


def test_verify_citacoes_pdf_minimo(tmp_path):
    fitz = pytest.importorskip("fitz")
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    doc = fitz.open()
    doc.new_page().insert_text((50, 72), "This article was published in 2020.\nWe use survey data from "
                                          "three districts.\nOverall, gains were modest for most households.",
                               fontsize=10)
    doc.save(pdfs / "Silva2020.pdf")
    doc.close()
    fichas = tmp_path / "fichas"
    _ficha(fichas, "Silva2020", 2020, "teorico", "achado")
    r = _rodar("fichamento-sistematico", "verify_citacoes.py", "--ficha", fichas / "fichamento_Silva2020.md",
               "--pdf", pdfs / "Silva2020.pdf")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "problemas=0" in r.stdout
