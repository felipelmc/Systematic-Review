#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
amostrar_validacao.py — Sorteia a amostra de validação (recodificação cega) a partir
do fichamento consolidado.

A unidade amostral é o TEXTO (`citekey`), não a ficha — um texto com múltiplas fichas
(desenho misto) conta uma vez só, e seu "estrato" é a combinação ordenada dos valores
do classificador entre suas fichas (ex. "a1+b2"). Sem `--classificador`, a amostra é
aleatória simples sobre todos os citekeys do consolidado. Com `--classificador`,
estratifica por esse valor/combinação, com pelo menos `--min-por-estrato` por estrato.

USO
---
    # Amostra aleatória simples de 25% (codebook sem seções condicionais)
    python3 amostrar_validacao.py --consolidado fichamentos_master.csv \
        --fracao 0.25 --semente 20260819 --out amostra_validacao.csv

    # Amostra estratificada por classificador (equivalente ao caso RS)
    python3 amostrar_validacao.py --consolidado fichamentos_master.csv \
        --classificador tipo_trabalho --fracao 0.25 --semente 20260819 \
        --out amostra_validacao.csv
"""
from __future__ import annotations
import argparse, csv, math, random
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--consolidado", required=True, help="fichamentos_master.csv")
    ap.add_argument("--classificador", help="nome da coluna de desenho/tipo no consolidado (opcional)")
    ap.add_argument("--fracao", type=float, default=0.25)
    ap.add_argument("--semente", type=int, required=True, help="semente fixa, para reprodutibilidade")
    ap.add_argument("--min-por-estrato", type=int, default=1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.consolidado, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))

    tem_classificador = bool(args.classificador) and linhas and args.classificador in linhas[0]
    if args.classificador and not tem_classificador:
        print(f"[aviso] coluna '{args.classificador}' não encontrada em {args.consolidado} "
              f"— amostrando sem estratificação.")

    valores_por_citekey: dict[str, set[str]] = defaultdict(set)
    for row in linhas:
        ck = (row.get("citekey") or "").strip()
        if not ck:
            continue
        if tem_classificador:
            v = (row.get(args.classificador) or "").strip()
            if v:
                valores_por_citekey[ck].add(v)
        else:
            valores_por_citekey[ck]  # garante a chave mesmo sem valor de classificador

    citekeys = sorted(valores_por_citekey)
    rng = random.Random(args.semente)

    if not tem_classificador:
        n = min(len(citekeys), max(1, math.ceil(args.fracao * len(citekeys)))) if citekeys else 0
        amostra = sorted(rng.sample(citekeys, n))
        estratos: dict[str, str] = {}
    else:
        estratos = {ck: ("+".join(sorted(vs)) or "?") for ck, vs in valores_por_citekey.items()}
        por_estrato: dict[str, list[str]] = defaultdict(list)
        for ck, estrato in estratos.items():
            por_estrato[estrato].append(ck)
        amostra = []
        for estrato, cks in sorted(por_estrato.items()):
            cks = sorted(cks)
            n = min(len(cks), max(args.min_por_estrato, math.ceil(args.fracao * len(cks))))
            amostra.extend(rng.sample(cks, n))
        amostra = sorted(amostra)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if tem_classificador:
            w.writerow(["citekey", "estrato"])
            for ck in amostra:
                w.writerow([ck, estratos.get(ck, "")])
        else:
            w.writerow(["citekey"])
            for ck in amostra:
                w.writerow([ck])

    modo = f"estratificado por {args.classificador}" if tem_classificador else "aleatorio simples"
    print(f"[ok] {len(amostra)}/{len(citekeys)} textos amostrados ({modo}, "
          f"fracao={args.fracao}, semente={args.semente}) -> {args.out}")
    if tem_classificador:
        dist = defaultdict(int)
        for ck in amostra:
            dist[estratos.get(ck, "")] += 1
        for estrato, n in sorted(dist.items()):
            print(f"    {estrato}: {n}")


if __name__ == "__main__":
    main()
