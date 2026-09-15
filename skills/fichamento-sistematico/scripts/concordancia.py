#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
concordancia.py — Taxa de concordância entre o fichamento ORIGINAL e o RE-FICHAMENTO
cego (recodificação por um segundo agente, sem acesso à ficha original) sobre a amostra
de validação. Compara variável a variável, respeitando o `tipo` de cada uma declarado
no codebook do projeto (coluna `tipo`; default `textual` se ausente/vazia — ver
references/schema_codebook.md):

  - categorica    : igualdade exata após normalização do rótulo (remove justificativa
                    entre parênteses/após travessão); reporta % e Cohen's κ.
  - numerica_int  : igualdade com tolerância absoluta < 0.5 (equivale a "bate arredondado").
  - numerica_real : tolerância relativa <= 1%.
  - textual       : similaridade de Jaccard de tokens (concorda >=0.6 com mesma página
                    citada; parcial 0.3-0.6; discorda <0.3).

Convenções:
  - `999` vs `999`         -> concordam.
  - `NA_secao` vs `NA_secao` -> concordam (aplicabilidade).
  - `NA_secao` vs preenchido (ou vice-versa) -> divergência de APLICABILIDADE (reportada
    à parte, contabilizada na concordância "estrita" mas não na "de valores").
  - Métricas: concordância por variável (média entre textos), por texto (média entre
    variáveis aplicáveis) e global. `discorda_parcial` conta como 0,5 nas médias.
  - Categóricas também recebem PABAK (kappa ajustado para prevalência e viés).
    Por quê: com uma categoria dominante (ex. 90% "não"), o κ de Cohen despenca mesmo
    com concordância alta, e a decisão de redefinir a variável ficaria refém da
    prevalência. PABAK = (k·Po − 1)/(k − 1), com k = nº de categorias observadas nos
    dois lados (mínimo 2; para k = 2 é o clássico 2·Po − 1).
  - Sinalização por variável (limiares de validação de extração categórica numa revisão
    sistemática): sinalizada se a concordância de valores < 80% ou, para categóricas,
    se nem κ nem PABAK chegam a 0,7. Amostra com menos de 10 textos gera aviso de
    instabilidade. As colunas antigas do CSV não mudam; `pabak`,
    `concordancia_valores`, `sinalizada` e `motivo_sinalizacao` são acrescentadas ao
    fim do bloco por variável.

Se o codebook do projeto declarar seções condicionais (alguma linha com `aplicavel_se`
preenchido), a comparação é feita no nível do TEXTO — múltiplas fichas de um mesmo
citekey (desenho misto) são mescladas numa visão única por variável antes de comparar
os dois lados (prioridade: resposta real > 999 > NA_secao), e uma seção extra de
"concordância de desenho" é calculada e reportada à parte. Sem `aplicavel_se` no
codebook, essa seção simplesmente não aparece — cada texto tem 1 ficha, e não há nada
para desalinhar.

USO
---
  python3 concordancia.py \
     --original  caminho/para/fichamentos \
     --validacao caminho/para/fichamentos/_validacao \
     --codebook  caminho/para/codebook.csv \
     --amostra   caminho/para/amostra_validacao.csv \
     --out-dir   caminho/para/saidas \
     [--sinonimos caminho/para/sinonimos.json]

--sinonimos (opcional): JSON `{"<variavel>": {"<alias>": "<canonico>", ...}, ...}` para
projetos com categóricas multi-token que têm sinônimos conhecidos (ex. uma variável de
"estratégia metodológica" onde "DiD"/"dif em dif" devem contar como a mesma categoria).
Sem o flag, cada variável categórica é comparada por igualdade simples do rótulo — não
é uma feature obrigatória, é um ajuste fino por projeto.
"""
from __future__ import annotations
import argparse, csv, glob, json, os, re, unicodedata
from collections import defaultdict

# --------------------------------------------------------------------------- tipos e classificador (lidos do codebook)
TIPOS: dict[str, str] = {}
CLASSIFICADOR: str | None = None
CODIGOS_VALIDOS: list[str] = []
SINONIMOS: dict[str, dict[str, str]] = {}

_TIPOS_VALIDOS = {"categorica", "numerica_int", "numerica_real", "textual"}


def carregar_tipos(codebook_csv: str) -> tuple[dict[str, str], list[str]]:
    tipos: dict[str, str] = {}
    avisos: list[str] = []
    with open(codebook_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            v = (row.get("variavel") or "").strip()
            if not v:
                continue
            t = (row.get("tipo") or "").strip().lower()
            if t and t not in _TIPOS_VALIDOS:
                avisos.append(f"[aviso] variável '{v}': tipo '{t}' não reconhecido no codebook, "
                              f"tratando como textual")
                t = ""
            tipos[v] = t or "textual"
    return tipos, avisos


def detectar_classificador(codebook_csv: str) -> str | None:
    with open(codebook_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cond = (row.get("aplicavel_se") or "").strip()
            if cond and "=" in cond:
                return cond.split("=", 1)[0].strip()
    return None


def codigos_do_classificador(codebook_csv: str, classificador: str) -> list[str]:
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


def tipo_de(var: str) -> str:
    return TIPOS.get(var, "textual")


# --------------------------------------------------------------------------- parsing
def ler_frontmatter(md):
    fm = {}
    m = re.match(r"\s*---\s*\n(.*?)\n---\s*\n", md, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1); fm[k.strip()] = v.strip()
    return fm

_LINHA = re.compile(r"^\s*[-*]\s*\*\*(?P<var>[A-Za-z0-9_]+)\*\*\s*[—-]?\s*(?:resposta\s*:\s*)?(?P<corpo>.*)$")
_SPLIT_EV = re.compile(r"\s*[—-]\s*evid[eê]ncia\s*:\s*", re.IGNORECASE)
_PAG = re.compile(r"\(\s*p{1,2}\.?\s*([0-9]{1,4}(?:\s*[-–,;e]\s*[0-9]{1,4})*)\s*\)", re.IGNORECASE)

def parse(md):
    corpo = md
    m = re.match(r"\s*---\s*\n.*?\n---\s*\n(.*)$", md, re.DOTALL)
    if m: corpo = m.group(1)
    corpo = re.split(r"##\s*Notas do codificador", corpo, flags=re.IGNORECASE)[0]
    out = {}
    for line in corpo.splitlines():
        mm = _LINHA.match(line)
        if not mm: continue
        var = mm.group("var"); body = mm.group("corpo").strip()
        parts = _SPLIT_EV.split(body, maxsplit=1)
        resp, ev = (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else (body, body)
        pgs = _PAG.findall(ev)
        out[var] = {"resp": resp, "ev": ev, "pag": ";".join(pgs)}
    return out

def carregar_fichas(dirpath, citekey):
    """Retorna {ficha_id: parsed} de todas as fichas de um citekey (inclui #<codigo>)."""
    res = {}
    for f in glob.glob(os.path.join(dirpath, f"fichamento_{citekey}*.md")):
        # não casar Carrilho2022 com Carrilho2022a: exige que o sufixo comece por '#' ou '.'
        base = os.path.basename(f)[len("fichamento_"):-len(".md")]
        if base != citekey and not base.startswith(citekey + "#"):
            continue
        md = open(f, encoding="utf-8", errors="replace").read()
        fm = ler_frontmatter(md)
        fid = fm.get("ficha_id") or citekey
        res[fid] = parse(md)
    return res

def _rank_cell(cell):
    """Prioridade ao mesclar fichas de um texto: resposta real > 999 > NA_secao."""
    r = norm(cell["resp"])
    if r == "na_secao": return 0
    if r == "999": return 1
    return 2

def merge_side(fichas):
    """Colapsa as fichas de um texto (um lado) em UMA visão por variável — evita
    multiplicar divergência de desenho por todas as variáveis quando os codificadores
    discordam do nº de fichas (só relevante com classificador; sem ele, cada citekey
    já tem 1 ficha só, então isto é um no-op)."""
    merged = {}
    for parsed in fichas.values():
        for var, cell in parsed.items():
            if var not in merged or _rank_cell(cell) > _rank_cell(merged[var]):
                merged[var] = cell
    return merged

def designs_de(fichas):
    """Conjunto ordenado dos códigos de desenho das fichas de um texto, lido do campo
    classificador. Tupla vazia se não houver classificador declarado no codebook."""
    if not CLASSIFICADOR:
        return tuple()
    codes = set()
    pattern = "|".join(re.escape(c) for c in CODIGOS_VALIDOS) if CODIGOS_VALIDOS else None
    for parsed in fichas.values():
        tt = parsed.get(CLASSIFICADOR, {}).get("resp", "")
        if not tt:
            continue
        if pattern:
            m = re.match(rf"\s*({pattern})\b", tt, re.IGNORECASE)
            codes.add(m.group(1).lower() if m else norm(tt))
        else:
            codes.add(norm(tt))
    return tuple(sorted(codes))

# --------------------------------------------------------------------------- normalização/comparação
def norm(s):
    s = unicodedata.normalize("NFKC", str(s)).lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s

_STOP = set("de da do das dos a o as os e em no na nos nas um uma the of and in to for with".split())
def tokens(s):
    return {t for t in re.findall(r"\w+", norm(s)) if t not in _STOP and len(t) > 1}

def jaccard(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta and not tb: return 1.0
    if not ta or not tb: return 0.0
    return len(ta & tb) / len(ta | tb)

def _fold(s):
    s = norm(s)
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))

def canon_categorica(var, resp):
    """Reduz uma resposta categórica ao seu *rótulo* canônico, descartando a
    justificativa (parênteses e texto após travessão). Se o projeto forneceu
    --sinonimos para esta variável, trata a resposta como um conjunto de tokens
    (separados por ;,+/ ou 'e'/'and') e aplica o dicionário de alias->canônico antes
    de comparar — útil para categóricas que aceitam combinações (ex. "matching + IV")."""
    s = re.sub(r"\([^)]*\)", " ", str(resp))          # remove parentéticos
    s = re.split(r"\s[—–-]\s", s)[0]                    # corta justificativa após travessão
    s = _fold(s).strip(" .;:,")
    s = re.sub(r"\s+", " ", s)
    syn = SINONIMOS.get(var)
    if syn:
        parts = re.split(r"[;,+/]|\se\s|\band\b", s)
        toks = set()
        for p in parts:
            p = p.strip()
            if not p: continue
            toks.add(syn.get(p, p))
        return " | ".join(sorted(t for t in toks if t))
    return s

def num(s):
    m = re.search(r"-?−?\s*\d[\d.,]*", str(s))
    if not m: return None
    t = m.group(0).replace("−", "-").replace(" ", "")
    # heurística decimal: se tem vírgula e não ponto, vírgula=decimal
    if "," in t and "." not in t: t = t.replace(",", ".")
    else: t = t.replace(",", "")
    try: return float(t)
    except ValueError: return None

def comparar(var, a, b):
    """Retorna (status, score, aplicabilidade) com status em
    {concorda, discorda, discorda_parcial, div_aplicabilidade}."""
    ra, rb = norm(a["resp"]), norm(b["resp"])
    na, nb = (ra == "na_secao"), (rb == "na_secao")
    if na and nb:
        return ("concorda", 1.0, "ambos_na")
    if na != nb:
        return ("div_aplicabilidade", 0.0, "div_na")
    if ra == "999" and rb == "999":
        return ("concorda", 1.0, "ambos_999")
    if (ra == "999") != (rb == "999"):
        return ("discorda", 0.0, "aplic")
    t = tipo_de(var)
    if t == "categorica":
        ca, cb = canon_categorica(var, a["resp"]), canon_categorica(var, b["resp"])
        return ("concorda", 1.0, "aplic") if ca == cb else ("discorda", 0.0, "aplic")
    if t in ("numerica_int", "numerica_real"):
        va, vb = num(a["resp"]), num(b["resp"])
        if va is None or vb is None:
            return ("concorda", 1.0, "aplic") if ra == rb else ("discorda", 0.0, "aplic")
        if t == "numerica_int":
            ok = abs(va - vb) < 0.5
        else:
            ok = abs(va - vb) <= 0.01 * max(abs(va), abs(vb), 1e-9)
        return ("concorda", 1.0, "aplic") if ok else ("discorda", 0.0, "aplic")
    # textual
    j = jaccard(a["resp"], b["resp"])
    pag_ok = (a["pag"] == b["pag"]) and a["pag"] != ""
    if j >= 0.6:
        return ("concorda" if (pag_ok or a["pag"] == b["pag"]) else "discorda_parcial",
                1.0 if pag_ok or a["pag"] == b["pag"] else 0.5, "aplic")
    if j >= 0.3:
        return ("discorda_parcial", 0.5, "aplic")
    return ("discorda", 0.0, "aplic")

# --------------------------------------------------------------------------- kappa
def cohen_kappa(pairs):
    cats = sorted({x for p in pairs for x in p})
    if len(cats) < 2: return None
    n = len(pairs)
    obs = sum(1 for a, b in pairs if a == b) / n
    ca = defaultdict(int); cb = defaultdict(int)
    for a, b in pairs: ca[a] += 1; cb[b] += 1
    exp = sum((ca[c]/n)*(cb[c]/n) for c in cats)
    if exp == 1: return 1.0
    return (obs - exp) / (1 - exp)


def pabak(pairs):
    """PABAK (Byrt, Bishop & Carlin 1993) generalizado para k categorias.

    Diferente do κ, não depende das marginais: só da concordância observada Po e do
    número de categorias. k = categorias observadas nos dois lados, com mínimo 2 (uma
    variável em que todos marcaram a mesma categoria tem PABAK 1, não indefinido).
    Devolve None sem pares.
    """
    if not pairs:
        return None
    k = max(2, len({x for p in pairs for x in p}))
    po = sum(1 for a, b in pairs if a == b) / len(pairs)
    return (k * po - 1) / (k - 1)


# --------------------------------------------------------------------------- limiares de validação
LIMIAR_CONCORDANCIA = 0.80
LIMIAR_KAPPA_PABAK = 0.70
N_MINIMO_AMOSTRA = 10


def avaliar_limiares(tipo, concordancia, kappa, pabak_valor):
    """Devolve (sinalizada, motivos) para uma variável.

    Regra: concordância de valores >= 80% sempre; para categóricas, também κ OU PABAK
    >= 0,7 (basta um, porque o PABAK existe justamente para os casos em que o κ é
    distorcido pela prevalência). Sem nenhum dos dois calculável, a categórica é
    sinalizada — ausência de evidência de confiabilidade não é aprovação.
    """
    motivos = []
    if concordancia is None or concordancia < LIMIAR_CONCORDANCIA:
        motivos.append("concordancia<80%")
    if tipo == "categorica":
        valores = [v for v in (kappa, pabak_valor) if v is not None]
        if not valores or max(valores) < LIMIAR_KAPPA_PABAK:
            motivos.append("kappa_e_pabak<0.7")
    return bool(motivos), motivos

# --------------------------------------------------------------------------- main
def main():
    global TIPOS, CLASSIFICADOR, CODIGOS_VALIDOS, SINONIMOS

    ap = argparse.ArgumentParser()
    ap.add_argument("--original", required=True)
    ap.add_argument("--validacao", required=True)
    ap.add_argument("--codebook", required=True)
    ap.add_argument("--amostra", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--sinonimos", help="JSON opcional {variavel: {alias: canonico}}")
    args = ap.parse_args()

    TIPOS, avisos_tipo = carregar_tipos(args.codebook)
    for a in avisos_tipo:
        print(a)
    CLASSIFICADOR = detectar_classificador(args.codebook)
    CODIGOS_VALIDOS = codigos_do_classificador(args.codebook, CLASSIFICADOR) if CLASSIFICADOR else []
    if args.sinonimos:
        with open(args.sinonimos, encoding="utf-8") as f:
            SINONIMOS = json.load(f)

    var_order = list(TIPOS.keys())

    with open(args.amostra, encoding="utf-8") as f:
        citekeys = [r["citekey"].strip() for r in csv.DictReader(f) if r.get("citekey", "").strip()]

    # --- por_var/por_texto guardam TODAS as variáveis aplicáveis (inclui div_aplicabilidade);
    #     *_val guardam só as variáveis mutuamente aplicáveis (exclui div_aplicabilidade) ---
    por_var = defaultdict(list)
    por_texto = defaultdict(list)
    por_var_val = defaultdict(list)
    por_texto_val = defaultdict(list)
    kappa_pairs = defaultdict(list)  # var -> list de (a,b) categórica
    linhas = []                      # detalhamento
    divergencias = []
    desenho_rows = []                # [ck, designs_A, designs_B, concordam?] — só se houver CLASSIFICADOR

    for ck in citekeys:
        A = carregar_fichas(args.original, ck)
        B = carregar_fichas(args.validacao, ck)
        if CLASSIFICADOR:
            dA, dB = designs_de(A), designs_de(B)
            desenho_rows.append([ck, "+".join(dA) or "?", "+".join(dB) or "?", dA == dB])
        # colapsa as fichas de cada lado numa visão por variável (nível de texto)
        ma, mb = merge_side(A), merge_side(B)
        for var in var_order:
            da = ma.get(var); db = mb.get(var)
            if da is None and db is None:
                continue
            if da is None or db is None:
                status, score = "div_aplicabilidade", 0.0
                linhas.append([ck, ck, var, tipo_de(var), (da or {"resp": "<ausente>"})["resp"],
                               (db or {"resp": "<ausente>"})["resp"], status, score])
                divergencias.append([ck, ck, var, (da or {"resp": "<ausente>"})["resp"],
                                     (db or {"resp": "<ausente>"})["resp"],
                                     (da or {"pag": ""}).get("pag", ""), (db or {"pag": ""}).get("pag", "")])
                por_var[var].append(score); por_texto[ck].append(score)
                continue
            status, score, aplic = comparar(var, da, db)
            if aplic == "ambos_na":
                linhas.append([ck, ck, var, tipo_de(var), da["resp"], db["resp"], "concorda_NA", 1.0])
                continue
            linhas.append([ck, ck, var, tipo_de(var), da["resp"], db["resp"], status, score])
            por_var[var].append(score); por_texto[ck].append(score)
            if status != "div_aplicabilidade":
                por_var_val[var].append(score); por_texto_val[ck].append(score)
                if tipo_de(var) == "categorica":
                    kappa_pairs[var].append((canon_categorica(var, da["resp"]),
                                             canon_categorica(var, db["resp"])))
            if status in ("discorda", "discorda_parcial", "div_aplicabilidade"):
                divergencias.append([ck, ck, var, da["resp"][:120], db["resp"][:120],
                                     da["pag"], db["pag"]])

    # métricas por variável calculadas uma vez, usadas no CSV e no relatório (κ, PABAK,
    # concordância de valores e sinalização pelos limiares de validação)
    metricas_var = {}
    for var in var_order:
        if not por_var.get(var):
            continue
        scv = por_var_val.get(var, [])
        kp = kappa_pairs.get(var)
        k = cohen_kappa(kp) if kp else None
        pb = pabak(kp) if kp else None
        conc_val = sum(scv) / len(scv) if scv else None
        sinalizada, motivos = avaliar_limiares(tipo_de(var), conc_val, k, pb)
        metricas_var[var] = {"kappa": k, "pabak": pb, "conc_valores": conc_val,
                             "n_valores": len(scv), "sinalizada": sinalizada, "motivos": motivos}
    sinalizadas = [v for v in var_order if v in metricas_var and metricas_var[v]["sinalizada"]]

    os.makedirs(args.out_dir, exist_ok=True)
    # concordancia.csv (detalhe + resumos)
    with open(os.path.join(args.out_dir, "concordancia.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nivel", "chave", "variavel", "tipo", "valor_original", "valor_revalidacao", "status", "score"])
        for l in linhas: w.writerow(["detalhe"] + l)
        w.writerow([])
        w.writerow(["--- concordancia por variavel ---"])
        w.writerow(["nivel", "variavel", "n_textos", "concordancia_media", "cohen_kappa",
                    "pabak", "concordancia_valores", "sinalizada", "motivo_sinalizacao"])
        for var in var_order:
            sc = por_var.get(var, [])
            if not sc: continue
            m = metricas_var[var]
            k, pb, cv = m["kappa"], m["pabak"], m["conc_valores"]
            w.writerow(["por_variavel", var, len(sc), round(sum(sc)/len(sc), 4),
                        "" if k is None else round(k, 4),
                        "" if pb is None else round(pb, 4),
                        "" if cv is None else round(cv, 4),
                        "sim" if m["sinalizada"] else "nao", "|".join(m["motivos"])])
        w.writerow([])
        w.writerow(["--- concordancia por texto ---"])
        w.writerow(["nivel", "citekey", "n_vars_aplicaveis", "concordancia_estrita",
                    "n_vars_mutuamente_aplicaveis", "concordancia_valores"])
        for ck in citekeys:
            sc = por_texto.get(ck, [])
            scv = por_texto_val.get(ck, [])
            if sc:
                w.writerow(["por_texto", ck, len(sc), round(sum(sc)/len(sc), 4),
                            len(scv), round(sum(scv)/len(scv), 4) if scv else ""])
        if CLASSIFICADOR:
            w.writerow([])
            w.writerow([f"--- concordancia de desenho ({CLASSIFICADOR}: nº/códigos de ficha por texto) ---"])
            w.writerow(["nivel", "citekey", "desenho_original", "desenho_revalidacao", "concordam"])
            for ck, da, db, ok in desenho_rows:
                w.writerow(["desenho", ck, da, db, "sim" if ok else "NAO"])

    todos = [s for sc in por_texto.values() for s in sc]
    global_ = sum(todos)/len(todos) if todos else 0.0
    todos_val = [s for sc in por_texto_val.values() for s in sc]
    global_val = sum(todos_val)/len(todos_val) if todos_val else 0.0
    n_desenho_ok = sum(1 for _, _, _, ok in desenho_rows if ok) if CLASSIFICADOR else 0

    # dimensões: usa o rótulo `dimensao` do codebook tal como está (sem bucketing
    # hardcoded) — a lista de dimensões e sua ordem vêm do próprio arquivo do projeto.
    dims_ordem: list[str] = []
    dimmap: dict[str, str] = {}
    with open(args.codebook, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = (row.get("dimensao") or "").strip()
            v = (row.get("variavel") or "").strip()
            if not v:
                continue
            dimmap[v] = d
            if d and d not in dims_ordem:
                dims_ordem.append(d)
    dim_scores = defaultdict(list)
    dim_scores_val = defaultdict(list)
    for var, sc in por_var.items():
        dim_scores[dimmap.get(var, "")].extend(sc)
    for var, sc in por_var_val.items():
        dim_scores_val[dimmap.get(var, "")].extend(sc)

    with open(os.path.join(args.out_dir, "RELATORIO_CONCORDANCIA.md"), "w", encoding="utf-8") as f:
        f.write("# Relatório de Concordância — validação por recodificação cega\n\n")
        f.write(f"- Textos na amostra: **{len(citekeys)}** (re-fichados às cegas por um segundo codificador).\n")
        f.write(f"- **Concordância de valores** (variáveis que *ambos* os codificadores consideraram "
                f"aplicáveis): **{global_val:.1%}** ({len(todos_val)} comparações).\n")
        f.write(f"- **Concordância estrita** (inclui divergências de aplicabilidade de seção): "
                f"**{global_:.1%}** ({len(todos)} comparações).\n")
        if CLASSIFICADOR:
            f.write(f"- **Concordância de desenho** ({CLASSIFICADOR}: nº e códigos de ficha por texto): "
                    f"**{n_desenho_ok}/{len(desenho_rows)}** textos "
                    f"({(n_desenho_ok/len(desenho_rows) if desenho_rows else 0):.1%}).\n\n")
            f.write("> A diferença entre as duas taxas globais é, em grande parte, atribuível a "
                    "**discordâncias de classificação de desenho**: quando os codificadores divergem "
                    "sobre quais seções se aplicam, cada variável da seção conta como divergência de "
                    "aplicabilidade. A comparação é feita em **nível de texto** (as fichas de um mesmo "
                    "texto são mescladas por variável), de modo que uma discordância de desenho **não** "
                    "é multiplicada por todas as variáveis.\n\n")
        else:
            f.write("\n")
        f.write("### Como cada tipo de variável é comparado\n\n")
        f.write("- **Categóricas**: compara-se o **rótulo canônico**, descartando a justificativa entre "
                "parênteses/após travessão — a confiabilidade de uma variável categórica é sobre a "
                "*categoria* atribuída, não sobre a prosa. Reporta-se **Cohen's κ**.\n")
        f.write("- **Numéricas**: inteiras (contagens/ano) por igualdade exata; reais com tolerância "
                "relativa de 1%.\n")
        f.write("- **Textuais abertas**: similaridade de **Jaccard** de tokens (concorda ≥0,6 **com** "
                "mesma página citada; parcial 0,3–0,6 = 0,5; discorda <0,3). Divergência de palavreado "
                "entre dois codificadores descrevendo o mesmo achado reduz legitimamente a concordância "
                "— por isso as abertas têm taxas naturalmente menores.\n\n")
        if CLASSIFICADOR:
            f.write(f"## Concordância de desenho por texto ({CLASSIFICADOR})\n\n")
            f.write("| Citekey | Desenho (original) | Desenho (revalidação) | Concordam |\n|---|---|---|---|\n")
            for ck, da, db, ok in desenho_rows:
                f.write(f"| {ck} | {da} | {db} | {'sim' if ok else '**NÃO**'} |\n")
            f.write("\n")
        f.write("## Concordância por dimensão\n\n"
                "| Dimensão | N (valores) | Conc. valores | N (estrita) | Conc. estrita |\n|---|---|---|---|---|\n")
        for d in dims_ordem:
            sc = dim_scores.get(d, []); scv = dim_scores_val.get(d, [])
            if sc:
                cv = f"{sum(scv)/len(scv):.1%}" if scv else "—"
                f.write(f"| {d} | {len(scv)} | {cv} | {len(sc)} | {sum(sc)/len(sc):.1%} |\n")
        f.write("\n## Concordância por texto\n\n"
                "| Citekey | N vars aplic. | Conc. valores | Conc. estrita |\n|---|---|---|---|\n")
        for ck in citekeys:
            sc = por_texto.get(ck, []); scv = por_texto_val.get(ck, [])
            if sc:
                cv = f"{sum(scv)/len(scv):.1%}" if scv else "—"
                f.write(f"| {ck} | {len(scv)} | {cv} | {sum(sc)/len(sc):.1%} |\n")
        f.write("\n## Concordância de valores e κ por variável (ordenado da mais problemática)\n\n")
        f.write("_Somente variáveis mutuamente aplicáveis (exclui divergências de aplicabilidade)._\n\n")
        f.write("| Variável | N | Conc. valores | Cohen's κ | PABAK | Sinalizada |\n"
                "|---|---|---|---|---|---|\n")
        rows = []
        for var in var_order:
            sc = por_var_val.get(var, [])
            if not sc: continue
            k = cohen_kappa(kappa_pairs.get(var)) if kappa_pairs.get(var) else None
            rows.append((sum(sc)/len(sc), var, len(sc), k))
        for conc, var, n, k in sorted(rows):
            pb = metricas_var.get(var, {}).get("pabak")
            sin = "**sim**" if metricas_var.get(var, {}).get("sinalizada") else "não"
            f.write(f"| {var} | {n} | {conc:.1%} | {'—' if k is None else f'{k:.3f}'} | "
                    f"{'—' if pb is None else f'{pb:.3f}'} | {sin} |\n")
        f.write(f"\n## Divergências ({len(divergencias)})\n\n")
        f.write("| Citekey | Ficha | Variável | Valor A (original) | Valor B (revalidação) | pág A | pág B |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for d in divergencias:
            vals = [str(x).replace("|", "/").replace("\n", " ")[:80] for x in d]
            f.write("| " + " | ".join(vals) + " |\n")
        problem = [r for r in sorted(rows) if r[0] < 0.8]
        f.write("\n## Variáveis mais problemáticas (concordância de valores < 80%) — revisão humana sugerida\n\n")
        if problem:
            for conc, var, n, k in problem:
                f.write(f"- **{var}** — {conc:.1%} (N={n})\n")
        else:
            f.write("Nenhuma variável abaixo de 80%.\n")

        f.write("\n## Variáveis sinalizadas pelos limiares de validação\n\n"
                "_Critério: concordância de valores ≥ 80% e, para categóricas, κ de Cohen ou "
                "PABAK ≥ 0,7. Variável sinalizada pede redefinição no codebook e recodificação "
                "da variável, não só arbitragem caso a caso._\n\n")
        if len(citekeys) < N_MINIMO_AMOSTRA:
            f.write(f"> **Aviso:** a amostra tem {len(citekeys)} textos (< {N_MINIMO_AMOSTRA}); "
                    "κ, PABAK e percentuais por variável são instáveis nesse tamanho.\n\n")
        if sinalizadas:
            nomes_motivo = {"concordancia<80%": "concordância < 80%",
                            "kappa_e_pabak<0.7": "κ e PABAK < 0,7"}
            for var in sinalizadas:
                m = metricas_var[var]
                cv = "—" if m["conc_valores"] is None else f"{m['conc_valores']:.1%}"
                k = "—" if m["kappa"] is None else f"{m['kappa']:.3f}"
                pb = "—" if m["pabak"] is None else f"{m['pabak']:.3f}"
                motivos = "; ".join(nomes_motivo.get(x, x) for x in m["motivos"])
                f.write(f"- **{var}** ({tipo_de(var)}) — {motivos} "
                        f"(conc. valores {cv}, κ {k}, PABAK {pb}, N={m['n_valores']})\n")
        else:
            f.write("Nenhuma variável sinalizada.\n")

    desenho_str = f" | desenho ok = {n_desenho_ok}/{len(desenho_rows)}" if CLASSIFICADOR else ""
    print(f"[ok] conc. valores = {global_val:.1%} ({len(todos_val)}) | conc. estrita = {global_:.1%} ({len(todos)})"
          f"{desenho_str} | textos={len(citekeys)} | divergências={len(divergencias)}")
    print(f"[ok] -> {args.out_dir}/concordancia.csv e RELATORIO_CONCORDANCIA.md")
    print(f"[limiares] variáveis sinalizadas (conc. < 80% ou categórica com κ e PABAK < 0,7): "
          f"{len(sinalizadas)}" + (f" -> {', '.join(sinalizadas)}" if sinalizadas else ""))
    if len(citekeys) < N_MINIMO_AMOSTRA:
        print(f"[aviso] amostra com {len(citekeys)} textos (< {N_MINIMO_AMOSTRA}): métricas por variável instáveis.")

if __name__ == "__main__":
    main()
