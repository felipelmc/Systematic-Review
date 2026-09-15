#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_bib.py — Gera um arquivo .bib a partir de uma planilha de papers (XLSX/CSV).

Detecta automaticamente as colunas mais comuns nos projetos do usuário (título,
autor(es), ano, DOI, tipo de publicação, periódico/veículo). Se a planilha já tiver
uma coluna de chave pronta (ex. `chave`, de baixar-pdfs-academicos; `citekey`, de
fichamento-sistematico), reaproveita essa coluna — as entradas do .bib ficam com o
mesmo nome dos PDFs/fichas já gerados para o mesmo corpus. Sem coluna de chave, gera
uma com `chave.gerar_chave` (scripts/chave.py, arquivo vendorizado idêntico nas skills
de revisão), para manter a chave consistente entre as skills quando rodadas sobre a
mesma planilha.

Por que os aliases de chave não incluem `id`/`key`: planilhas exportadas pelo Zotero
(`Key`) e pelo OpenAlex (`id` = URL do W) seriam tomadas como citekey, gerando
entradas como `@article{https://openalex.org/W123,`. Uma chave existente que não passe
em `chave_valida` (URL, espaço, começa com dígito...) é descartada com aviso e
regenerada.

USO
---
    python3 gerar_bib.py --planilha papers.xlsx --out references.bib

    # colunas com nomes fora do padrão detectado automaticamente:
    python3 gerar_bib.py --planilha papers.csv --out refs.bib \
        --col-titulo Title --col-autor Authors --col-ano Year --col-doi DOI
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

import pandas as pd

# chave.py mora ao lado deste script; o caminho explícito permite importar este módulo
# de fora da pasta (testes, outras skills). Sem bytecode para não sujar a pasta da skill.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chave import chave_valida, gerar_chave, lista_autores  # noqa: E402

# ==== Detecção de coluna (mesmo padrão de alias das outras duas skills) ====

ALIASES = {
    "titulo": ["titulo", "título", "title"],
    "autor": ["autor", "autores", "primeiro_autor", "author", "authors"],
    "ano": ["ano", "year"],
    "doi": ["doi", "doi_limpo"],
    "tipo": ["tipo", "tipo_publicacao", "type"],
    "journal": ["nome_publicacao", "journal", "periodico", "source"],
    "chave": ["chave", "citekey", "bib_key"],
}


def normalizar_nome_coluna(c):
    import unicodedata
    c = unicodedata.normalize("NFKD", str(c).lower())
    c = "".join(ch for ch in c if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", c)


def detectar_coluna(df, campo):
    cols_norm = {normalizar_nome_coluna(c): c for c in df.columns}
    for alias in ALIASES[campo]:
        alias_n = normalizar_nome_coluna(alias)
        if alias_n in cols_norm:
            return cols_norm[alias_n]
    return None


# ==== Geração de chave ====
# `gerar_chave(titulo, autores, ano, usadas)` vem de chave.py (importado no topo), com a
# mesma assinatura da antiga função local. A cópia local partia autores em [;,] e pegava
# o último token ("Weihs M." -> "M2025") e gerava sufixo "{" depois de "z".


def limpar_doi(doi):
    if doi is None or (isinstance(doi, float) and pd.isna(doi)):
        return None
    doi = str(doi).strip()
    if not doi or doi.lower() == "nan":
        return None
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    return doi.strip().lower() or None


# ==== Mapeamento tipo -> entrada BibTeX e campo de veículo ====

def tipo_bib(tipo):
    """Tipo BibTeX a partir do tipo de publicação (esquema da revisao-sistematica ou texto livre da base).

    Dissertação/mestrado vem antes de tese: "dissertação" (PT) é de mestrado e vira
    @mastersthesis; "dissertation" (EN) continua @phdthesis. "evento"/"anais" (valores
    em português) viram @inproceedings, como "conference"/"proceedings".
    """
    t = str(tipo).lower()
    if re.search(r"dissertac|dissertaç|mestrado|master", t):
        return "mastersthesis"
    if "thesis" in t or "tese" in t or "dissert" in t or "doutorado" in t:
        return "phdthesis"
    if "chapter" in t or "capitulo" in t or "capítulo" in t or "incollection" in t:
        return "incollection"
    if "book" in t or "livro" in t:
        return "book"
    if "preprint" in t or "report" in t or "relatorio" in t or "relatório" in t:
        return "techreport"
    if re.search(r"\bevento|conference|proceedings|anais|congress", t):
        return "inproceedings"
    return "article"


# Campo de "veículo" correto por tipo — corrige um bug do script original (RS), que
# usava `booktitle` também para phdthesis/techreport (BibTeX não reconhece esse campo
# para esses tipos; o correto é `school`/`institution`).
CAMPO_VENUE = {
    "article": "journal",
    "incollection": "booktitle",
    "inproceedings": "booktitle",
    "phdthesis": "school",
    "mastersthesis": "school",
    "techreport": "institution",
    "book": "publisher",
}


def formatar_autores(raw):
    """Campo `author` do BibTeX: autores individuais separados por " and ".

    Usa `chave.lista_autores`, que entende "|", ";", " and " e listas com vírgula
    ("Silva, João, Souza, Maria"), para que o .bib separe autores do mesmo jeito que a
    chave escolhe o primeiro. Nome institucional que contém " and " vai entre chaves,
    senão o BibTeX o partiria em dois autores.
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    partes = []
    for a in lista_autores(raw):
        a = a.strip()
        if not a:
            continue
        if re.search(r"\s+and\s+", a, flags=re.IGNORECASE):
            a = "{" + a.replace("{", "").replace("}", "") + "}"
        partes.append(a)
    return " and ".join(partes) if partes else None


def limpar_texto(t):
    """Remove tags HTML residuais e protege chaves de campo BibTeX."""
    t = re.sub(r"<[^>]+>", "", str(t))
    return t.replace("{", "").replace("}", "").strip()


def valor_valido(v):
    return v is not None and not (isinstance(v, float) and pd.isna(v)) and str(v).strip().lower() not in ("", "nan")


def entrada_bib(chave, titulo, autores, ano, doi, tipo_raw, journal_raw):
    tipo = tipo_bib(tipo_raw) if valor_valido(tipo_raw) else "article"
    linhas = [f"@{tipo}{{{chave},"]

    if valor_valido(titulo):
        linhas.append(f"  title   = {{{limpar_texto(titulo)}}},")
    aut = formatar_autores(autores)
    if aut:
        linhas.append(f"  author  = {{{aut}}},")
    if valor_valido(ano):
        try:
            ano_int = int(float(ano))
            linhas.append(f"  year    = {{{ano_int}}},")
        except (ValueError, TypeError):
            linhas.append(f"  year    = {{{ano}}},")
    if valor_valido(journal_raw):
        campo = CAMPO_VENUE.get(tipo, "journal")
        linhas.append(f"  {campo} = {{{limpar_texto(journal_raw)}}},")
    doi_limpo = limpar_doi(doi)
    if doi_limpo:
        linhas.append(f"  doi     = {{{doi_limpo}}},")

    linhas.append("}")
    return "\n".join(linhas)


def main():
    ap = argparse.ArgumentParser(description="Gera um .bib a partir de uma planilha de papers.")
    ap.add_argument("--planilha", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--col-titulo")
    ap.add_argument("--col-autor")
    ap.add_argument("--col-ano")
    ap.add_argument("--col-doi")
    ap.add_argument("--col-tipo")
    ap.add_argument("--col-journal")
    ap.add_argument("--col-chave")
    args = ap.parse_args()

    caminho = Path(args.planilha)
    df = pd.read_csv(caminho) if caminho.suffix.lower() == ".csv" else pd.read_excel(caminho)

    col_titulo = args.col_titulo or detectar_coluna(df, "titulo")
    col_autor = args.col_autor or detectar_coluna(df, "autor")
    col_ano = args.col_ano or detectar_coluna(df, "ano")
    col_doi = args.col_doi or detectar_coluna(df, "doi")
    col_tipo = args.col_tipo or detectar_coluna(df, "tipo")
    col_journal = args.col_journal or detectar_coluna(df, "journal")
    col_chave = args.col_chave or detectar_coluna(df, "chave")

    if not col_titulo:
        print(f"ERRO: não encontrei coluna de título. Colunas disponíveis: {list(df.columns)}")
        print("Use --col-titulo NOME para indicar manualmente.")
        raise SystemExit(1)

    # Pré-carrega as chaves válidas já existentes na coluna: sem isso, uma chave gerada para
    # uma linha anterior (ex.: Silva2020) colidiria com a chave já gravada numa linha
    # posterior (Silva2020), e o .bib teria duas entradas com a mesma citekey.
    usadas = set()
    if col_chave:
        usadas = {str(v).strip() for v in df[col_chave] if valor_valido(v) and chave_valida(v)}
    entradas = []
    sem_doi = sem_ano = regeneradas = 0
    contagem_tipo = {}

    for _, row in df.iterrows():
        titulo = row[col_titulo] if col_titulo else None
        if not valor_valido(titulo):
            continue
        autores = row[col_autor] if col_autor else None
        ano = row[col_ano] if col_ano else None
        doi = row[col_doi] if col_doi else None
        tipo_raw = row[col_tipo] if col_tipo else None
        journal_raw = row[col_journal] if col_journal else None

        chave_existente = row.get(col_chave) if col_chave else None
        if valor_valido(chave_existente) and chave_valida(chave_existente):
            chave = str(chave_existente).strip()
        else:
            if valor_valido(chave_existente):
                regeneradas += 1
                print(f"[aviso] chave inválida {str(chave_existente).strip()!r} "
                      f"(coluna {col_chave}); gerando uma nova.")
            chave = gerar_chave(titulo, autores, ano, usadas)
        usadas.add(chave)

        entradas.append(entrada_bib(chave, titulo, autores, ano, doi, tipo_raw, journal_raw))

        if not limpar_doi(doi):
            sem_doi += 1
        if not valor_valido(ano):
            sem_ano += 1
        tipo_final = tipo_bib(tipo_raw) if valor_valido(tipo_raw) else "article"
        contagem_tipo[tipo_final] = contagem_tipo.get(tipo_final, 0) + 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n".join(entradas) + "\n", encoding="utf-8")

    print(f"[ok] {len(entradas)} entradas -> {out_path}")
    if contagem_tipo:
        print("Por tipo:", ", ".join(f"{t}={n}" for t, n in sorted(contagem_tipo.items())))
    if sem_doi:
        print(f"[aviso] {sem_doi} entradas sem DOI.")
    if sem_ano:
        print(f"[aviso] {sem_ano} entradas sem ano.")
    if regeneradas:
        print(f"[aviso] {regeneradas} chaves existentes inválidas foram regeneradas.")


if __name__ == "__main__":
    main()
