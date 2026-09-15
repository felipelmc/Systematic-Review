#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_citacoes.py — Gate de verificação de citações verbatim.

Para cada ficha `fichamento_<citekey>[#<codigo>].md`, confere que TODA evidência com
citação literal aparece, de fato, na página indicada do PDF correspondente. O texto do
PDF é extraído por página on-the-fly (PyMuPDF; fallback pdfplumber) — NÃO depende de
nenhum cache de .txt. Antes de comparar, tanto a citação quanto o texto da página são
normalizados (minúsculas, colapso de espaços, remoção de hifenização de fim de linha,
uniformização de aspas/travessões, ligaduras tipográficas, acentos soltos).

Este script não depende do codebook do projeto — só do formato de linha
`- **<variavel>** — resposta: ... — evidência: "<citação>" (p. N)` e do frontmatter
YAML da ficha (`citekey`, `offset_pagina`). Funciona para qualquer projeto que use
esse template, gerado por references/INSTRUCOES_FICHADOR.md desta skill.

USO
---
    # Verificar TODAS as fichas de um diretório contra pdfs/:
    python3 verify_citacoes.py \
        --fichas caminho/para/fichamentos \
        --pdfs   caminho/para/pdfs \
        --out    caminho/para/verificacao_citacoes.csv

    # Verificar UMA ficha contra UM PDF:
    python3 verify_citacoes.py --ficha fichamento_Silva2023.md --pdf pdfs/Silva2023.pdf

    # Verificar as fichas de validação (re-fichamentos cegos):
    python3 verify_citacoes.py --fichas fichamentos/_validacao --pdfs pdfs \
        --out fichamentos/_saidas/verificacao_citacoes_validacao.csv

Convenções lidas do frontmatter YAML de cada ficha:
    - `citekey`      : usado para localizar o PDF (<pdfs>/<citekey>.pdf) quando --pdf não é dado.
    - `offset_pagina`: página impressa P -> página do PDF (1-based) = P + offset.
    - `paginacao`    : informativo (impressa | indice-do-PDF).

STATUS por citação (coluna `status` do CSV):
    OK             — citação encontrada na página impressa indicada (após aplicar offset).
    PAGINA_ERRADA  — citação encontrada no PDF, porém em página diferente da indicada.
    NAO_ENCONTRADA — citação não localizada em nenhuma página do PDF.
    PDF_TEXTO_NAO_EXTRAIVEL — o PDF não tem camada de texto extraível (fonte sem
                     ToUnicode ou digitalização sem OCR); exceção documentada, precisa
                     de checagem visual humana, não conta como problema no gate.

Evidências `999` e `NA_secao` (sem citação literal) não geram linha de verificação.
Código de saída: 0 se não houver nenhum problema (exceto PDF_TEXTO_NAO_EXTRAIVEL,
tratado como exceção documentada); 1 caso contrário.
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import re
import sys
import unicodedata

# ----------------------------------------------------------------------------
# Extração de texto por página
# ----------------------------------------------------------------------------

def extrair_paginas(pdf_path: str) -> list[str]:
    """Retorna lista com o texto de cada página do PDF (índice 0 = 1ª página do PDF)."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        pags = [doc[i].get_text("text") for i in range(doc.page_count)]
        doc.close()
        return pags
    except Exception:
        pass
    # fallback
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return [(pg.extract_text() or "") for pg in pdf.pages]


# ----------------------------------------------------------------------------
# Normalização
# ----------------------------------------------------------------------------

_WS = re.compile(r"\s+")
# hifenização de fim de linha: "desmata-\nmento" -> "desmatamento"
_HYPHEN_BREAK = re.compile(r"[-­]\s*\n\s*")
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
_QUOTES = {ord(c): '"' for c in "“”„‟″«»"}
_APOS = {ord(c): "'" for c in "‘’‚′"}
# ligaduras tipográficas comuns em PDFs (a extração pode devolver a ligadura literal)
_LIG = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "ft", "ﬆ": "st"}
# hífen intra-palavra (com espaço/quebra opcional): "company- community" / "company-\ncommunity"
_INWORD_HYPHEN = re.compile(r"(?<=\w)-\s*(?=\w)")
# glifos de acento ISOLADOS que a extração devolve separados da letra ("strate´giques", "cauˆe"):
# removidos SEM deixar espaço, antes do folding de diacríticos.


def _fold_diacriticos(texto: str) -> str:
    """Remove acentos para comparação (PDFs francês/português frequentemente separam o acento
    da letra). Primeiro tira o glifo isolado (sem espaço), depois dobra os precompostos via NFKD."""
    _acc = {0x60, 0x5e, 0x7e, 0xa8, 0xaf, 0xb4, 0xb8, 0x374, 0x375} | set(range(0x2b0, 0x300))
    texto = "".join(ch for ch in texto if ord(ch) not in _acc)
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    for lig, rep in _LIG.items():
        texto = texto.replace(lig, rep)
    # NFKC decompõe ligaduras/sobrescritos/caracteres de compatibilidade (ﬁ->fi, ² ->2),
    # tornando a comparação robusta a artefatos de extração de PDF.
    texto = unicodedata.normalize("NFKC", texto)
    texto = _fold_diacriticos(texto)              # comparação insensível a acento (é~e, ç~c)
    texto = _HYPHEN_BREAK.sub("", texto)          # colar hifenização de quebra de linha
    texto = texto.translate(_DASHES)
    texto = texto.translate(_QUOTES)
    texto = texto.translate(_APOS)
    texto = texto.lower()
    texto = texto.replace(" ", " ")
    texto = _INWORD_HYPHEN.sub("", texto)          # colar hifenização "company- community"
    texto = _WS.sub(" ", texto)                    # colapsar espaços/quebras
    return texto.strip()


# ----------------------------------------------------------------------------
# Parsing da ficha .md
# ----------------------------------------------------------------------------

def ler_frontmatter(md: str) -> dict:
    fm = {}
    m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n", md, re.DOTALL)
    if not m:
        return fm
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


# variável em linha: "- **<var>** — resposta: ... — evidência: <ev>"
_LINHA_VAR = re.compile(r"^\s*[-*]\s*\*\*(?P<var>[A-Za-z0-9_]+)\*\*\s*(?P<resto>.*)$")
# extrai o trecho de evidência (após "evidência:" / "evidencia:")
_EVID = re.compile(r"evid[eê]ncia\s*:\s*(?P<ev>.*)$", re.IGNORECASE)
# pares "citação" (p. N) — aceita p., pp., "p", múltiplas páginas "12, 14", intervalos "12-13"
_PAR = re.compile(
    r"[\"“«](?P<q>[^\"”»]+)[\"”»]\s*"
    r"\(\s*p{1,2}\.?\s*(?P<pgs>[0-9]{1,4}(?:\s*[-–,;e]\s*[0-9]{1,4})*)\s*\)",
    re.IGNORECASE,
)


def parse_paginas(pgs: str) -> list[int]:
    """'12-14' -> [12,13,14]; '12, 16' -> [12,16]; '7' -> [7]."""
    out: list[int] = []
    for parte in re.split(r"[,;e]", pgs):
        parte = parte.strip()
        if not parte:
            continue
        m = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", parte)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a <= b and b - a <= 50:
                out.extend(range(a, b + 1))
            else:
                out.append(a)
        else:
            m2 = re.match(r"^(\d+)$", parte)
            if m2:
                out.append(int(m2.group(1)))
    return out


def extrair_citacoes(md: str) -> list[dict]:
    """Retorna [{variavel, citacao, paginas:[int]}] para toda evidência com citação."""
    itens = []
    for line in md.splitlines():
        m = _LINHA_VAR.match(line)
        if not m:
            continue
        var = m.group("var")
        ev = _EVID.search(m.group("resto"))
        trecho = ev.group("ev") if ev else m.group("resto")
        for par in _PAR.finditer(trecho):
            q = par.group("q").strip()
            pgs = parse_paginas(par.group("pgs"))
            if q and pgs:
                itens.append({"variavel": var, "citacao": q, "paginas": pgs})
    return itens


# ----------------------------------------------------------------------------
# Verificação
# ----------------------------------------------------------------------------

def verificar_ficha(ficha_path: str, pdf_path: str) -> list[dict]:
    md = open(ficha_path, encoding="utf-8", errors="replace").read()
    fm = ler_frontmatter(md)
    citekey = fm.get("citekey") or os.path.basename(ficha_path).replace("fichamento_", "").replace(".md", "")
    try:
        offset = int(re.sub(r"[^0-9\-]", "", fm.get("offset_pagina", "0")) or "0")
    except ValueError:
        offset = 0

    paginas_pdf = extrair_paginas(pdf_path)
    paginas_norm = [normalizar(p) for p in paginas_pdf]
    # variante sem espaços: neutraliza palavras quebradas por espaço na extração ("inter viewed").
    paginas_ns = [p.replace(" ", "") for p in paginas_norm]
    n_pag = len(paginas_norm)

    # Detecção de PDF sem camada de texto extraível (fontes sem ToUnicode → só devolvem
    # "(cid:N)" ou bytes de controle). Nesse caso NENHUMA citação é verificável por script;
    # marcamos com status próprio para não confundir com citação incorreta.
    amostra = " ".join(paginas_pdf)[:20000]
    nao_espaco = [c for c in amostra if not c.isspace()]
    frac_alfa = (sum(c.isalpha() for c in nao_espaco) / len(nao_espaco)) if nao_espaco else 0.0
    if frac_alfa < 0.5:
        return [{
            "citekey": citekey, "ficha": os.path.basename(ficha_path), "variavel": var,
            "pagina_indicada": ";".join(map(str, item["paginas"])), "status": "PDF_TEXTO_NAO_EXTRAIVEL",
            "pagina_encontrada_impressa": "", "offset_pagina": offset,
            "citacao": item["citacao"][:200].replace("\n", " "),
        } for item in extrair_citacoes(md) for var in [item["variavel"]]]

    def contido(q_norm, i):
        return bool(q_norm) and (q_norm in paginas_norm[i] or q_norm.replace(" ", "") in paginas_ns[i])

    resultados = []
    for item in extrair_citacoes(md):
        q = normalizar(item["citacao"])
        # páginas impressas -> índice 0-based no PDF: pdf_1based = P + offset ; idx = pdf_1based - 1
        alvos = []
        for p in item["paginas"]:
            idx = p + offset - 1
            if 0 <= idx < n_pag:
                alvos.append(idx)
        achou_na_pagina = any(contido(q, i) for i in alvos)
        if achou_na_pagina:
            status = "OK"
            pag_encontrada = ""
        else:
            encontrada = [i + 1 for i in range(n_pag) if contido(q, i)]
            if encontrada:
                status = "PAGINA_ERRADA"
                pag_encontrada = ";".join(str(e - offset) for e in encontrada)  # impressa
            else:
                status = "NAO_ENCONTRADA"
                pag_encontrada = ""
        resultados.append({
            "citekey": citekey,
            "ficha": os.path.basename(ficha_path),
            "variavel": item["variavel"],
            "pagina_indicada": ";".join(map(str, item["paginas"])),
            "status": status,
            "pagina_encontrada_impressa": pag_encontrada,
            "offset_pagina": offset,
            "citacao": item["citacao"][:200].replace("\n", " "),
        })
    return resultados


def encontrar_pdf(citekey: str, ficha_path: str, pdfs_dir: str) -> str | None:
    cand = os.path.join(pdfs_dir, f"{citekey}.pdf")
    if os.path.exists(cand):
        return cand
    return None


def main():
    ap = argparse.ArgumentParser(description="Gate de verificação de citações verbatim.")
    ap.add_argument("--ficha", help="uma ficha .md")
    ap.add_argument("--pdf", help="o PDF correspondente (usado com --ficha)")
    ap.add_argument("--fichas", help="diretório com fichamento_*.md")
    ap.add_argument("--pdfs", help="diretório com os PDFs (<citekey>.pdf)")
    ap.add_argument("--out", help="CSV de saída (modo diretório)")
    args = ap.parse_args()

    resultados = []
    if args.ficha:
        pdf = args.pdf
        if not pdf:
            fm = ler_frontmatter(open(args.ficha, encoding="utf-8", errors="replace").read())
            ck = fm.get("citekey")
            pdf = encontrar_pdf(ck, args.ficha, args.pdfs or "pdfs")
        if not pdf or not os.path.exists(pdf):
            print(f"[ERRO] PDF não encontrado para {args.ficha}", file=sys.stderr)
            sys.exit(2)
        resultados = verificar_ficha(args.ficha, pdf)
    elif args.fichas:
        pdfs_dir = args.pdfs or "pdfs"
        fichas = sorted(glob.glob(os.path.join(args.fichas, "fichamento_*.md")))
        for f in fichas:
            fm = ler_frontmatter(open(f, encoding="utf-8", errors="replace").read())
            ck = fm.get("citekey") or os.path.basename(f).replace("fichamento_", "").replace(".md", "")
            pdf = encontrar_pdf(ck, f, pdfs_dir)
            if not pdf:
                resultados.append({"citekey": ck, "ficha": os.path.basename(f), "variavel": "",
                                   "pagina_indicada": "", "status": "PDF_NAO_ENCONTRADO",
                                   "pagina_encontrada_impressa": "", "offset_pagina": "", "citacao": ""})
                continue
            resultados.extend(verificar_ficha(f, pdf))
    else:
        ap.error("informe --ficha ou --fichas")

    cols = ["citekey", "ficha", "variavel", "pagina_indicada", "status",
            "pagina_encontrada_impressa", "offset_pagina", "citacao"]
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", newline="", encoding="utf-8") as fo:
            w = csv.DictWriter(fo, fieldnames=cols)
            w.writeheader()
            w.writerows(resultados)
        print(f"[ok] {len(resultados)} citações verificadas -> {args.out}")

    # resumo
    from collections import Counter
    c = Counter(r["status"] for r in resultados)
    total = len(resultados)
    problemas = total - c.get("OK", 0) - c.get("PDF_TEXTO_NAO_EXTRAIVEL", 0)
    print("STATUS:", dict(c), f"| total={total} problemas={problemas}")
    if not args.out:
        for r in resultados:
            if r["status"] not in ("OK", "PDF_TEXTO_NAO_EXTRAIVEL"):
                print(f"  [{r['status']}] {r['citekey']}::{r['variavel']} "
                      f"(p.{r['pagina_indicada']}) :: {r['citacao'][:80]}")
    sys.exit(0 if problemas == 0 else 1)


if __name__ == "__main__":
    main()
