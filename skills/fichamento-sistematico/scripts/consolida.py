#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consolida.py — Consolida as fichas `.md` em `fichamentos_master.csv` (+ `.xlsx`).

Uma linha por ficha (`ficha_id`). Upsert determinístico: o master é RECONSTRUÍDO a
partir de todas as fichas presentes em `--fichas`, de modo que reprocessar nunca
duplica linhas. O esquema de colunas segue o codebook do projeto (CSV com colunas
`dimensao,variavel,descricao,prompt[,tipo,aplicavel_se]` — ver references/schema_codebook.md):

    ficha_id, citekey, [<classificador>,] n_fichas_do_texto,
    <var_1>, <var_1>__evidencia, ..., <var_N>, <var_N>__evidencia,
    pdf_path, paginacao, offset_pagina, agente_fichador, data_fichamento, notas_codificador

A coluna `<classificador>` só aparece se o codebook declarar seções condicionais
(alguma linha com `aplicavel_se` preenchido) — nesse caso, a variável classificadora
(a que aparece à esquerda do `=` em `aplicavel_se`) vira coluna de cabeçalho em vez de
par variável/evidência, e seu valor é normalizado para o código curto (ex. "a1"). Sem
`aplicavel_se` no codebook, TODAS as variáveis viram pares var/evidência normais —
caminho mais simples, sem essa coluna extra.

USO
---
    python3 consolida.py \
        --fichas   caminho/para/fichamentos \
        --codebook caminho/para/codebook.csv \
        --out-csv  caminho/para/fichamentos_master.csv \
        --out-xlsx caminho/para/fichamentos_master.xlsx
"""
from __future__ import annotations
import argparse, csv, glob, os, re, sys

PROC_COLS = ["pdf_path", "paginacao", "offset_pagina", "agente_fichador",
             "data_fichamento", "notas_codificador"]


def detectar_classificador(codebook_csv: str) -> str | None:
    """Variável classificadora = a que aparece à esquerda de algum 'aplicavel_se' no
    codebook. None se nenhuma linha usa aplicavel_se (codebook "simples", sem seções
    condicionais — todas as variáveis sempre se aplicam, uma ficha por texto)."""
    with open(codebook_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cond = (row.get("aplicavel_se") or "").strip()
            if cond and "=" in cond:
                return cond.split("=", 1)[0].strip()
    return None


def codigos_validos(codebook_csv: str, classificador: str) -> list[str]:
    """Valores possíveis do classificador (lado direito de 'aplicavel_se'), na ordem
    em que aparecem no codebook. Pode haver múltiplos valores por linha, separados
    por vírgula (ex. 'tipo_trabalho=a1,b1')."""
    vistos: list[str] = []
    with open(codebook_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cond = (row.get("aplicavel_se") or "").strip()
            if not cond or "=" not in cond:
                continue
            var, valores = cond.split("=", 1)
            if var.strip() != classificador:
                continue
            for v in valores.split(","):
                v = v.strip()
                if v and v not in vistos:
                    vistos.append(v)
    return vistos


def ordem_variaveis(codebook_csv: str, classificador: str | None) -> list[str]:
    """Ordem canônica das variáveis do codebook. A variável classificadora (se houver)
    é excluída: ela vira coluna de cabeçalho, não par variável/evidência."""
    vars_ = []
    with open(codebook_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            v = (row.get("variavel") or "").strip()
            if v and v != classificador:
                vars_.append(v)
    return vars_


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


_LINHA = re.compile(
    r"^\s*[-*]\s*\*\*(?P<var>[A-Za-z0-9_]+)\*\*\s*[—-]?\s*"
    r"(?:resposta\s*:\s*)?(?P<corpo>.*)$"
)
_SPLIT_EV = re.compile(r"\s*[—-]\s*evid[eê]ncia\s*:\s*", re.IGNORECASE)


def parse_ficha(md: str) -> dict:
    """Retorna {var: (resposta, evidencia)} + notas."""
    valores: dict[str, tuple[str, str]] = {}
    corpo = md
    # remover frontmatter para varrer só o corpo
    m = re.match(r"\s*---\s*\n.*?\n---\s*\n(.*)$", md, re.DOTALL)
    if m:
        corpo = m.group(1)
    notas = ""
    mnotas = re.search(r"##\s*Notas do codificador\s*\n(.*)$", corpo, re.DOTALL | re.IGNORECASE)
    if mnotas:
        notas = re.sub(r"\s+", " ", mnotas.group(1)).strip()
        corpo = corpo[:mnotas.start()]
    for line in corpo.splitlines():
        mm = _LINHA.match(line)
        if not mm:
            continue
        var = mm.group("var")
        body = mm.group("corpo").strip()
        parts = _SPLIT_EV.split(body, maxsplit=1)
        if len(parts) == 2:
            resp, ev = parts[0].strip(), parts[1].strip()
        else:
            resp, ev = body.strip(), body.strip()
        valores[var] = (resp, ev)
    return {"valores": valores, "notas": notas}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fichas", required=True)
    ap.add_argument("--codebook", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-xlsx")
    ap.add_argument("--glob", default="fichamento_*.md")
    args = ap.parse_args()

    classificador = detectar_classificador(args.codebook)
    codigos = codigos_validos(args.codebook, classificador) if classificador else []
    var_order = ordem_variaveis(args.codebook, classificador)

    head_cols = ["ficha_id", "citekey"]
    if classificador:
        head_cols.append(classificador)
    head_cols.append("n_fichas_do_texto")

    cols = list(head_cols)
    for v in var_order:
        cols += [v, f"{v}__evidencia"]
    cols += PROC_COLS

    fichas = sorted(glob.glob(os.path.join(args.fichas, args.glob)))
    linhas = {}  # ficha_id -> row (upsert)
    faltas = []
    for fp in fichas:
        md = open(fp, encoding="utf-8", errors="replace").read()
        fm = ler_frontmatter(md)
        parsed = parse_ficha(md)
        vals = parsed["valores"]
        ficha_id = fm.get("ficha_id") or fm.get("citekey") or os.path.basename(fp)
        row = {c: "" for c in cols}
        row["ficha_id"] = ficha_id
        row["citekey"] = fm.get("citekey", "")
        if classificador:
            raw = (fm.get(classificador, "") or vals.get(classificador, ("", ""))[0]).strip()
            if codigos:
                pattern = "|".join(re.escape(c) for c in codigos)
                m = re.match(rf"\s*({pattern})\b", raw, re.IGNORECASE)
                row[classificador] = m.group(1).lower() if m else raw
            else:
                row[classificador] = raw
        row["n_fichas_do_texto"] = fm.get("n_fichas_do_texto", "")
        for v in var_order:
            resp, ev = vals.get(v, ("", ""))
            row[v] = resp
            row[f"{v}__evidencia"] = ev
            if v not in vals:
                faltas.append((ficha_id, v))
        for pc in PROC_COLS:
            if pc == "notas_codificador":
                row[pc] = parsed["notas"] or fm.get("notas_codificador", "")
            else:
                row[pc] = fm.get(pc, "")
        linhas[ficha_id] = row

    ordenadas = [linhas[k] for k in sorted(linhas)]
    os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(ordenadas)
    print(f"[ok] {len(ordenadas)} fichas -> {args.out_csv}")

    if args.out_xlsx:
        import openpyxl
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "fichamentos"
        ws.append(cols)
        for r in ordenadas:
            ws.append([r[c] for c in cols])
        wb.save(args.out_xlsx)
        print(f"[ok] -> {args.out_xlsx}")

    if faltas:
        print(f"[AVISO] {len(faltas)} pares (ficha, variável) ausentes na ficha:", file=sys.stderr)
        for fid, v in faltas[:40]:
            print(f"   {fid} :: {v}", file=sys.stderr)
    else:
        print(f"[ok] todas as fichas têm as {len(var_order)} variáveis do codebook.")


if __name__ == "__main__":
    main()
