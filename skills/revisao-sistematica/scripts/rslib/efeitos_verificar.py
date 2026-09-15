"""Preparação e verificação dos dados de efeito extraídos dos textos completos.

USO
    python3 rs.py analise preparar-efeitos [--entrada 05-decomposicao/efeitos/ ...] \
        [--master fichamentos_master.csv] [--codebook codebook.csv]
    python3 rs.py analise verificar-efeitos [--efeitos 05-decomposicao/efeitos_extraidos.csv] \
        [--pdfs 03-textos/pdfs] [--saida 05-decomposicao/verificacao_efeitos.csv]

preparar-efeitos
    Junta os CSVs escritos pelo subagente `extrator-efeitos` (um por PDF, padrão
    `05-decomposicao/efeitos/*.csv`) em `05-decomposicao/efeitos_extraidos.csv`: primeiro
    as colunas exatas de `esquema.COLUNAS_EFEITOS_EXTRAIDOS`, depois as colunas extras
    das entradas (ex.: `familia_intervencao`, `rob_geral`, `classe_desenho`, moderadores,
    quartis `q1_1, q3_1, q1_2, q3_2`, `g`/`d`, `m_preditores` e as colunas de desfecho binário
    `p0, p1, efeito_pp, se_pp`), em minúsculas e na ordem em que aparecem.
    meta.R, swim.R e efeitos.R leem essas extras (sensibilidade sem risco alto,
    --excluir-rob, agrupamento por família, moderadores, Wan et al.); descartá-las
    obrigava a uma junção manual. Normaliza vírgula decimal e enums; preenche
    `id_estudo` pelo join `chave` → `registros_unicos` (respeita a ligação de relatos) e
    gera `id_efeito` quando vazio.
    `desenho` vazio é preenchido pelo master de fichas só com uma variável de DESENHO:
    `desenho`, `b2_estrategia_identificacao`, `estrategia_identificacao`, `metodo_sms`,
    `desenho_waddington` ou uma variável do codebook terminada em
    `estrategia_identificacao`. Nunca pelo classificador a1/a2/b1/b2 (`tipo_estudo`):
    "b2" não diz se o estudo é randomizado e o R o lia como não randomizado mesmo em ECR.
    Sem essa variável o desenho fica vazio, com aviso (o R agrupa como
    `desenho_nao_informado`).
    Preserva `verificado_humano` e as colunas extras já presentes numa execução anterior
    (por `id_efeito`, só se os dados do efeito não mudaram), para que reprocessar nunca
    apague verificação humana nem colunas acrescentadas à mão.
    Recusa (exit 1, sem gravar) revisões e meta-análises como estudo primário
    (estudo > relato > efeito), chaves desconhecidas, `id_efeito` duplicado e enums inválidos;
    os problemas vão para `05-decomposicao/efeitos_preparacao_avisos.csv`.

    Em projeto parcial sem PDFs (etapa 09 ignorada, nenhum PDF em 03-textos/pdfs nem em relatorio_pdfs.csv),
    o `proximo_passo` é `analise efeitos` e o resumo avisa que os números não foram verificados contra os PDFs
    (com a contagem de linhas sem `verificado_humano`, também em `extracao_consolidada`).

verificar-efeitos
    Para cada efeito:
    1. trecho verbatim (`evidencia`) na página indicada (`pagina` = número da página
       no arquivo PDF, 1 = primeira). Usa `normalizar`/`extrair_paginas` do
       `fichamento-sistematico/scripts/verify_citacoes.py` quando a irmã existe, para
       que o critério de "trecho encontrado" seja o mesmo do gate das fichas; senão, a
       normalização própria equivalente com PyMuPDF. Trechos com reticências são
       conferidos por partes.
    2. plausibilidade: DP > 0, n > 0, n1 + n2 <= N, p em [0, 1], p coerente com t/df
       (ou F com 1 gl), IC ordenado e contendo a estimativa, OR > 0, |r| <= 1, ICC em
       [0, 1], `m_preditores` inteiro >= 1 com n − m − 1 > 0; desfecho binário (`dif_prop`, `rr`):
       p0 e p1 em (0, 1) como proporção (não percentual), p0 + efeito_pp/100 em (0, 1), |efeito_pp|
       <= 100, se_pp > 0, p1 − p0 coerente com efeito_pp, RR·p0 < 1; alerta para |g| aproximado > 2,
       dados insuficientes para o tipo e correlação parcial sem `m_preditores` (vira `parcial_r_d_gl` no R).
    3. `verificado_humano` (sim/1/true) é obrigatório para seguir ao G7.
    Grava `05-decomposicao/verificacao_efeitos.csv`. Exit 2 se algum trecho falhar ou
    houver erro de plausibilidade; `pode_seguir_g7` no resumo só é true com todos os
    efeitos aptos. No autopiloto, linhas não aptas viram a pendência `verificacao_humana_efeitos`, com
    n = linhas não aptas; reexecutar atualiza o n sem duplicar e, com todas aptas, fecha a pendência
    em qualquer modo (handoff.sincronizar_pendencia_unica).

Por que a coerência de p considera arredondamento: artigos arredondam t e p; a
checagem aceita p dentro do intervalo produzido por t ± meia unidade da última casa
decimal informada, alargado pela meia unidade de p. Isso separa erro de extração
(p = 0,03 com t = 0,5) de arredondamento legítimo. O g aproximado aqui só serve para
o alerta; o cálculo oficial é do `scripts/R/efeitos.R`.
"""

import importlib.util
import math
import re
import sys
import unicodedata
from pathlib import Path

from . import chave as _chave
from . import esquema, estado, normalizar
from .handoff import (carregar_unicos, escrever_csv, exigir_raiz, falhar, indexar, ler_csv, ler_linhas,
                      localizar_skill_irma, relativo, resolver_caminho, sim, sincronizar_pendencia_unica)
from .textos import ErroDependencia, _pymupdf, localizar_pdf

ATOR = "rs.py analise"
DIR_EFEITOS = "05-decomposicao/efeitos"
ARQ_AVISOS_PREPARACAO = "05-decomposicao/efeitos_preparacao_avisos.csv"
ARQ_VERIFICACAO_EFEITOS = esquema.ARQ_VERIFICACAO_EFEITOS
COLUNAS_AVISOS = ["id_efeito", "chave", "campo", "gravidade", "problema"]
COLUNAS_VERIFICACAO = ["id_efeito", "chave", "pagina", "status_trecho", "pagina_encontrada", "verificador",
                       "erros", "alertas", "g_aproximado", "p_calculado", "verificado_humano", "apto_g7"]

TIPOS_ESTATISTICA = ["md_sd", "t", "f1", "beta_sd", "or", "r", "p_n", "g", "d", "parcial_r", "mann_whitney",
                     "mediana_iqr", "dif_prop", "rr"]
ESTIMANDOS = ["ATE", "ITT", "LATE", "ATT", "RDD_local", "associacao", "outro"]
DIRECOES = ["aumentar", "reduzir"]
CAMPOS_NUMERICOS = ["m1", "sd1", "n1", "m2", "sd2", "n2", "t", "df", "f", "beta", "se", "sdy", "or_", "ci_lo",
                    "ci_hi", "r", "icc", "n_total"]
# Desfecho binário (dif_prop, rr): proporção do controle e do tratamento (0-1), efeito e EP em pontos percentuais.
# Colunas extras do extrator, depois de m_preditores. Em esquema.py desde a v1.3 (alias).
COLUNAS_EFEITOS_BINARIOS = esquema.COLUNAS_EFEITOS_BINARIOS
# colunas extras numéricas lidas por scripts/R/efeitos.R (quartis de Wan et al.; g/d informados; m_preditores;
# desfecho binário)
CAMPOS_NUMERICOS_EXTRAS = list(esquema.COLUNAS_EFEITOS_EXTRAS_NUMERICAS) + [
    c for c in COLUNAS_EFEITOS_BINARIOS if c not in esquema.COLUNAS_EFEITOS_EXTRAS_NUMERICAS]
# Requisito = campo, ou tupla de alternativas (basta uma); "a+b" exige a e b juntos.
# Espelha as entradas de scripts/R/efeitos.R: Mann-Whitney usa o z na coluna t e só precisa
# de p quando não há z; r aceita n1 + n2 (proporção dos grupos) ou n_total; parcial_r usa n e a coluna
# extra m_preditores (tabela de conversões) ou, sem ela, o df residual (parcial_r_d_gl), conferidos em checar_plausibilidade.
REQUISITOS = {
    "md_sd": ["m1", "sd1", "n1", "m2", "sd2", "n2"], "t": ["t"], "f1": ["f"], "beta_sd": ["beta", "sdy"],
    "or": ["or_"], "r": ["r", ("n1+n2", "n_total")], "p_n": ["p"],
    "parcial_r": [("r", "t"), ("df", "n_total", "n1+n2")],
    "mann_whitney": [("t", "p"), ("n1+n2", "n_total")],
    "mediana_iqr": ["m1", "m2", "n1", "n2", ("q1_1+q3_1+q1_2+q3_2", "sd1+sd2")],
    "dif_prop": ["p0", ("p1", "efeito_pp"), ("se_pp", "ci_lo+ci_hi", "n1+n2", "n_total")],
    "rr": ["or_", "p0", ("se", "ci_lo+ci_hi")],
}
STATUS_FALHA = {"NAO_ENCONTRADA", "PAGINA_ERRADA", "SEM_TRECHO", "SEM_PAGINA", "PDF_NAO_ENCONTRADO"}
_MARCAS_REVISAO = ("meta_anal", "metaanal", "metanalis", "revisao_sistem", "systematic_review", "meta_analysis",
                   "overview", "umbrella", "guarda_chuva", "scoping_review", "revisao_de_escopo")
# Variáveis do master que descrevem o DESENHO (ordem de preferência). O classificador
# a1/a2/b1/b2 do codebook OQF (tipo_estudo) não entra: não distingue ECR de não randomizado.
COLUNAS_DESENHO_MASTER = ["desenho", "b2_estrategia_identificacao", "estrategia_identificacao", "metodo_sms",
                          "desenho_waddington"]
_AUSENTES_MASTER = {"", "999", "na", "na_secao", "nr", "nao_se_aplica"}


# ---------------------------------------------------------------------------
# Números
# ---------------------------------------------------------------------------
def numero(valor):
    """float a partir de texto de artigo ('0,45', '−1.2', ' 3 '); None se vazio; ValueError se inválido."""
    s = normalizar.texto(valor).replace("−", "-").replace(" ", "")
    if not s or s.lower() in {"999", "na", "nr", "nan"}:
        return None
    if re.fullmatch(r"-?\d+,\d+", s):
        s = s.replace(",", ".")
    return float(s)


def decimais(valor):
    s = normalizar.texto(valor).replace(",", ".")
    m = re.search(r"\.(\d+)", s)
    return len(m.group(1)) if m else 0


def _betacf(a, b, x):
    """Fração contínua da beta incompleta (Numerical Recipes, lentz modificado)."""
    tiny, eps = 1e-300, 3e-14
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = tiny if abs(d) < tiny else d
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def beta_incompleta(a, b, x):
    """Beta incompleta regularizada I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    ln_bt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    bt = math.exp(ln_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def p_t_bicaudal(t, df):
    """p bicaudal da t de Student com df graus de liberdade."""
    return beta_incompleta(df / 2.0, 0.5, df / (df + t * t))


def ler_p(valor):
    """(operador, valor, casas) para '0.03', '<0,001', 'p = .05'; (None, None, 0) vazio; ('?', None, 0) ilegível."""
    s = normalizar.ascii_fold(valor).lower().replace(" ", "").replace(",", ".")
    if not s:
        return None, None, 0
    s = re.sub(r"^p", "", s)
    m = re.fullmatch(r"(<=|>=|<|>|=)?(\d*\.?\d+(?:e-?\d+)?)", s)
    if not m:
        return "?", None, 0
    num = m.group(2)
    return (m.group(1) or "="), float(num), (len(num.split(".")[1]) if "." in num and "e" not in num else 0)


def intervalo_p(estatistica, df, casas, tipo):
    """Faixa [p_min, p_max] compatível com o arredondamento da estatística informada."""
    meia = 0.5 * 10 ** (-casas) if casas else 0.5
    if tipo == "f1":
        f_min, f_max = max(estatistica - meia, 0.0), estatistica + meia
        p_de_f = lambda f: beta_incompleta(df / 2.0, 0.5, df / (df + f))  # noqa: E731
        return p_de_f(f_max), p_de_f(f_min), p_de_f(estatistica)
    t = abs(estatistica)
    return p_t_bicaudal(t + meia, df), p_t_bicaudal(max(t - meia, 0.0), df), p_t_bicaudal(t, df)


def g_aproximado(v, tipo):
    """g/d aproximado só para o alerta |g| > 2 (o cálculo oficial é do efeitos.R)."""
    try:
        if tipo == "md_sd" and None not in (v["m1"], v["m2"], v["sd1"], v["sd2"], v["n1"], v["n2"]):
            n1, n2 = v["n1"], v["n2"]
            sp = math.sqrt(((n1 - 1) * v["sd1"] ** 2 + (n2 - 1) * v["sd2"] ** 2) / (n1 + n2 - 2))
            return (1 - 3 / (4 * (n1 + n2) - 9)) * (v["m1"] - v["m2"]) / sp
        if tipo in ("t", "f1") and v["n1"] and v["n2"]:
            est = v["t"] if tipo == "t" else (math.sqrt(v["f"]) if v["f"] is not None else None)
            if est is not None:
                return (1 - 3 / (4 * (v["n1"] + v["n2"]) - 9)) * est * math.sqrt(1 / v["n1"] + 1 / v["n2"])
        if tipo == "beta_sd" and v["beta"] is not None and v["sdy"]:
            return v["beta"] / v["sdy"]
        if tipo in ("r", "parcial_r") and v["r"] is not None and abs(v["r"]) < 1:
            return 2 * v["r"] / math.sqrt(1 - v["r"] ** 2)
        if tipo == "or" and v["or_"] and v["or_"] > 0:
            return math.log(v["or_"]) * math.sqrt(3) / math.pi
        if tipo == "dif_prop":
            p0, p1 = v.get("p0"), v.get("p1")
            if p1 is None and p0 is not None and v.get("efeito_pp") is not None:
                p1 = p0 + v["efeito_pp"] / 100
            if None not in (p0, p1) and 0 < p0 < 1 and 0 < p1 < 1:
                return (math.log(p1 / (1 - p1)) - math.log(p0 / (1 - p0))) * math.sqrt(3) / math.pi
        if tipo == "rr" and v["or_"] and v.get("p0") is not None and 0 < v["p0"] < 1 and v["or_"] * v["p0"] < 1:
            razao = v["or_"] * (1 - v["p0"]) / (1 - v["or_"] * v["p0"])
            return math.log(razao) * math.sqrt(3) / math.pi
    except (ZeroDivisionError, ValueError):
        return None
    return None


def _checar_binario(linha, v, tipo):
    """Erros de plausibilidade de desfecho binário (dif_prop, rr). Proporções em 0-1; efeito e EP em pp."""
    erros = []
    for campo in ("p0", "p1"):
        x = v.get(campo)
        if x is None:
            continue
        if 1 < x <= 100:
            erros.append(f"{campo} = {x:g} parece percentual: use proporção entre 0 e 1")
        elif not 0 < x < 1:
            erros.append(f"{campo} fora de (0, 1)")
    pp = v.get("efeito_pp")
    if pp is not None and abs(pp) > 100:
        erros.append("|efeito_pp| > 100 pontos percentuais")
    if v.get("se_pp") is not None and v["se_pp"] <= 0:
        erros.append("se_pp <= 0")
    p0, p1 = v.get("p0"), v.get("p1")
    if tipo == "dif_prop" and p0 is not None and 0 < p0 < 1:
        if p1 is None and pp is not None and abs(pp) <= 100 and not 0 < p0 + pp / 100 < 1:
            erros.append(f"p0 + efeito_pp/100 = {p0 + pp / 100:g} fora de (0, 1): efeito_pp deve estar em pontos "
                         "percentuais")
        if p1 is not None and 0 < p1 < 1 and pp is not None:
            # arredondamento: meia unidade da última casa de efeito_pp e de cada proporção (no máximo 0,005 cada)
            def meia(campo, escala=1.0):
                return min(0.5 * 10 ** (-decimais(linha.get(campo))) / escala, 0.005)
            folga = meia("efeito_pp", 100) + meia("p1") + meia("p0") + 1e-9
            if abs((p1 - p0) - pp / 100) > folga:
                erros.append(f"p1 − p0 ({p1 - p0:g}) incoerente com efeito_pp/100 ({pp / 100:g})")
    if tipo == "rr" and p0 is not None and 0 < p0 < 1 and v["or_"] is not None and v["or_"] > 0 and v["or_"] * p0 >= 1:
        erros.append(f"RR·p0 = {v['or_'] * p0:g} >= 1: risco do tratado impossível")
    return erros


def checar_plausibilidade(linha):
    """Devolve (erros, alertas, g_aprox, p_calc) de uma linha de efeito."""
    erros, alertas = [], []
    v = {}
    for campo in CAMPOS_NUMERICOS:
        try:
            v[campo] = numero(linha.get(campo))
        except ValueError:
            v[campo] = None
            erros.append(f"{campo} não numérico: {linha.get(campo)!r}")
    tipo = normalizar.texto(linha.get("tipo_estatistica")).lower()
    for campo in COLUNAS_EFEITOS_BINARIOS:
        try:
            v[campo] = numero(linha.get(campo))
        except ValueError:
            v[campo] = None
            erros.append(f"{campo} não numérico: {linha.get(campo)!r}")
    for campo in ("sd1", "sd2", "sdy"):
        if v[campo] is not None and v[campo] <= 0:
            erros.append(f"{campo} <= 0")
    for campo in ("n1", "n2", "n_total"):
        if v[campo] is not None and v[campo] <= 0:
            erros.append(f"{campo} <= 0")
    if None not in (v["n1"], v["n2"], v["n_total"]) and v["n1"] + v["n2"] > v["n_total"]:
        erros.append(f"n1 + n2 ({v['n1'] + v['n2']:g}) > n_total ({v['n_total']:g})")
    if v["df"] is not None and v["df"] <= 0:
        erros.append("df <= 0")
    if v["se"] is not None and v["se"] <= 0:
        erros.append("se <= 0")
    if v["r"] is not None and abs(v["r"]) > 1:
        erros.append("|r| > 1")
    if v["icc"] is not None and not 0 <= v["icc"] <= 1:
        erros.append("icc fora de [0, 1]")
    if v["f"] is not None and v["f"] < 0:
        erros.append("F < 0")
    if None not in (v["ci_lo"], v["ci_hi"]) and v["ci_lo"] > v["ci_hi"]:
        erros.append("ci_lo > ci_hi")
    if tipo in ("or", "rr"):
        nome = "OR" if tipo == "or" else "RR"
        if v["or_"] is not None and v["or_"] <= 0:
            erros.append(f"{nome} <= 0")
        if (v["ci_lo"] is not None and v["ci_lo"] <= 0) or (v["ci_hi"] is not None and v["ci_hi"] <= 0):
            erros.append(f"IC de {nome} com limite <= 0")
    if tipo == "mediana_iqr":
        for grupo in ("1", "2"):
            try:
                q1, q3 = numero(linha.get(f"q1_{grupo}")), numero(linha.get(f"q3_{grupo}"))
            except ValueError:
                erros.append(f"q1_{grupo}/q3_{grupo} não numérico")
                continue
            mediana = v[f"m{grupo}"]
            if None not in (q1, q3) and q1 >= q3:
                erros.append(f"q1_{grupo} >= q3_{grupo}")
            elif None not in (q1, q3, mediana) and not q1 <= mediana <= q3:
                erros.append(f"mediana m{grupo} fora de [q1_{grupo}, q3_{grupo}]")
    if tipo == "parcial_r":
        # tabela de conversões: r_p = t/sqrt(t² + n − m − 1), Var = (1 − r_p²)²/(n − m); m = preditores com o focal, sem intercepto
        try:
            m = numero(linha.get("m_preditores"))
        except ValueError:
            m = None
            erros.append(f"m_preditores não numérico: {linha.get('m_preditores')!r}")
        n = v["n_total"] if v["n_total"] is not None else (
            v["n1"] + v["n2"] if None not in (v["n1"], v["n2"]) else None)
        if m is None:
            if normalizar.vazio(linha.get("m_preditores")):
                alertas.append("parcial_r sem m_preditores: efeitos.R usa o gl residual informado "
                               "(formula_id parcial_r_d_gl), não n − m − 1 (assets/mapas/conversoes_efeito.csv)")
        elif m < 1 or m != int(m):
            erros.append("m_preditores deve ser inteiro >= 1 (preditores com o focal, sem intercepto)")
        elif n is not None and n - m - 1 <= 0:
            erros.append(f"n − m_preditores − 1 <= 0 (n = {n:g}, m = {m:g})")
        elif n is not None and v["df"] is not None and abs(v["df"] - (n - m - 1)) > 0.5:
            alertas.append(f"df ({v['df']:g}) difere de n − m_preditores − 1 ({n - m - 1:g}): confira n e m")
    if tipo in ("dif_prop", "rr"):
        erros.extend(_checar_binario(linha, v, tipo))
    estimativa = v["or_"] if tipo in ("or", "rr") else (v["beta"] if tipo in ("beta_sd",) else None)
    if tipo == "dif_prop":
        estimativa = v.get("efeito_pp")  # IC do efeito em pontos percentuais
    if estimativa is not None and None not in (v["ci_lo"], v["ci_hi"]) and not v["ci_lo"] <= estimativa <= v["ci_hi"]:
        erros.append("estimativa fora do IC informado")

    def tem(campo):
        if "+" in campo:
            return all(tem(c) for c in campo.split("+"))
        if campo == "p":
            return bool(normalizar.texto(linha.get("p")))  # p pode vir como "<0.001"
        if campo in v:
            return v[campo] is not None
        try:
            return numero(linha.get(campo)) is not None  # colunas extras (q1_1, q3_1...)
        except ValueError:
            return False

    faltam = []
    for requisito in REQUISITOS.get(tipo, []):
        alternativas = requisito if isinstance(requisito, tuple) else (requisito,)
        if not any(tem(c) for c in alternativas):
            faltam.append(" ou ".join(alternativas))
    if tipo in ("t", "f1") and v["df"] is None and not (v["n1"] and v["n2"]):
        faltam.append("df ou n1/n2")
    if tipo == "or" and v["se"] is None and None in (v["ci_lo"], v["ci_hi"]):
        faltam.append("se ou IC")
    if faltam:
        alertas.append(f"dados insuficientes para {tipo or 'tipo vazio'}: faltam {', '.join(faltam)}")

    operador, p_rep, casas_p = ler_p(linha.get("p"))
    p_calc = None
    if operador == "?":
        alertas.append(f"p ilegível: {linha.get('p')!r}")
    elif p_rep is not None and not 0 <= p_rep <= 1:
        erros.append("p fora de [0, 1]")
    if tipo in ("t", "f1"):
        est = v["t"] if tipo == "t" else v["f"]
        df = v["df"]
        if df is None and v["n1"] and v["n2"]:
            df = v["n1"] + v["n2"] - 2
            alertas.append("df inferido como n1 + n2 - 2")
        if est is not None and df and df > 0 and (tipo == "t" or est >= 0):
            casas_est = decimais(linha.get("t" if tipo == "t" else "f"))
            p_min, p_max, p_calc = intervalo_p(est, df, casas_est, tipo)
            if p_rep is not None and 0 <= p_rep <= 1:
                folga = 0.5 * 10 ** (-casas_p) if casas_p else 0.0
                if operador == "=":
                    coerente = p_min - folga - 1e-9 <= p_rep <= p_max + folga + 1e-9
                    unilateral = p_min / 2 - folga - 1e-9 <= p_rep <= p_max / 2 + folga + 1e-9
                    if not coerente and unilateral:
                        alertas.append("p coerente com teste unilateral; confirme no texto")
                    elif not coerente:
                        erros.append(f"p = {p_rep:g} incoerente com {tipo} ({p_calc:.4g} calculado)")
                elif operador in ("<", "<=") and p_min > p_rep + 1e-9:
                    erros.append(f"p {operador} {p_rep:g} incoerente com {tipo} ({p_calc:.4g} calculado)")
                elif operador in (">", ">=") and p_max < p_rep - 1e-9:
                    erros.append(f"p {operador} {p_rep:g} incoerente com {tipo} ({p_calc:.4g} calculado)")
    g = g_aproximado(v, tipo)
    if g is not None and abs(g) > 2:
        alertas.append(f"|g| aproximado = {abs(g):.2f} > 2: confira unidade, DP x EP e sinal")
    return erros, alertas, g, p_calc


# ---------------------------------------------------------------------------
# Trecho verbatim na página
# ---------------------------------------------------------------------------
_LIG = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "ft", "ﬆ": "st"}


def normalizar_trecho(texto):
    """Normalização equivalente à do gate de citações (acentos, hifenização, aspas, espaços)."""
    if not texto:
        return ""
    for lig, rep in _LIG.items():
        texto = texto.replace(lig, rep)
    texto = unicodedata.normalize("NFKC", texto)
    acentos = {0x60, 0x5E, 0x7E, 0xA8, 0xAF, 0xB4, 0xB8} | set(range(0x2B0, 0x300))
    texto = "".join(ch for ch in texto if ord(ch) not in acentos)
    texto = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    texto = re.sub(r"[-­]\s*\n\s*", "", texto)
    texto = texto.translate(dict.fromkeys(map(ord, "‐‑‒–—―−"), "-"))
    texto = texto.translate({ord(c): '"' for c in "“”„‟″«»"})
    texto = texto.translate({ord(c): "'" for c in "‘’‚′"})
    texto = texto.lower().replace(" ", " ")
    texto = re.sub(r"(?<=\w)-\s*(?=\w)", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


class Verificador:
    """Extrai páginas (com cache) e procura trechos; usa o gate da irmã quando disponível."""

    def __init__(self, usar_irma=True):
        self.irma = carregar_gate_irma() if usar_irma else None
        self.nome = "verify_citacoes" if self.irma else "proprio"
        self._cache = {}

    def paginas(self, caminho):
        chave = str(caminho)
        if chave not in self._cache:
            if self.irma is not None:
                brutas = self.irma.extrair_paginas(str(caminho))
                norm = self.irma.normalizar
            else:
                mod = _pymupdf()
                with mod.open(str(caminho)) as doc:
                    brutas = [p.get_text("text") for p in doc]
                norm = normalizar_trecho
            amostra = [c for c in " ".join(brutas)[:20000] if not c.isspace()]
            letras = (sum(c.isalpha() for c in amostra) / len(amostra)) if amostra else 0.0
            normalizadas = [norm(p) for p in brutas]
            self._cache[chave] = (normalizadas, [p.replace(" ", "") for p in normalizadas], letras >= 0.5, norm)
        return self._cache[chave]

    def localizar(self, caminho, trecho, paginas_indicadas):
        """(status, páginas onde o trecho aparece)."""
        normalizadas, sem_espaco, tem_texto, norm = self.paginas(caminho)
        if not tem_texto:
            return "PDF_TEXTO_NAO_EXTRAIVEL", []
        partes = [norm(p) for p in re.split(r"\[?(?:\.\.\.|…)\]?", trecho)]
        partes = [p for p in partes if len(p) >= 3]
        if not partes:
            return "SEM_TRECHO", []

        def contem(i):
            return all(p in normalizadas[i] or p.replace(" ", "") in sem_espaco[i] for p in partes)

        alvos = [p - 1 for p in paginas_indicadas if 0 < p <= len(normalizadas)]
        if alvos and any(contem(i) for i in alvos):
            return "OK", []
        encontradas = [i + 1 for i in range(len(normalizadas)) if contem(i)]
        if not encontradas:
            return "NAO_ENCONTRADA", []
        return ("PAGINA_ERRADA" if paginas_indicadas else "SEM_PAGINA"), encontradas


def carregar_gate_irma():
    pasta = localizar_skill_irma("fichamento-sistematico", "scripts/verify_citacoes.py")
    if pasta is None:
        return None
    # Sem bytecode: importar a irmã não pode criar __pycache__ dentro da pasta dela.
    anterior = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("_rs_verify_citacoes_irma",
                                                      str(pasta / "scripts" / "verify_citacoes.py"))
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
    except Exception:  # noqa: BLE001 - irmã quebrada não impede a verificação própria
        return None
    finally:
        sys.dont_write_bytecode = anterior
    if hasattr(modulo, "normalizar") and hasattr(modulo, "extrair_paginas"):
        return modulo
    return None


def ler_paginas_indicadas(valor):
    """'12' -> [12]; '12-13' -> [12, 13]; 'p. 4; 6' -> [4, 6]."""
    s = normalizar.texto(valor)
    saida = []
    for parte in re.split(r"[;,/]|\se\s", s):
        m = re.search(r"(\d+)\s*[-–]\s*(\d+)", parte)
        if m and int(m.group(1)) <= int(m.group(2)) <= int(m.group(1)) + 50:
            saida.extend(range(int(m.group(1)), int(m.group(2)) + 1))
            continue
        m = re.search(r"\d+", parte)
        if m:
            saida.append(int(m.group()))
    return saida


# ---------------------------------------------------------------------------
# preparar-efeitos
# ---------------------------------------------------------------------------
def _arquivos_entrada(raiz, entradas):
    raiz = Path(raiz)
    if not entradas:
        pasta = raiz / DIR_EFEITOS
        if pasta.is_dir() and any(pasta.glob("*.csv")):
            return sorted(pasta.glob("*.csv"))
        if (raiz / esquema.ARQ_EFEITOS_EXTRAIDOS).exists():
            return [raiz / esquema.ARQ_EFEITOS_EXTRAIDOS]
        raise FileNotFoundError(f"nenhum CSV em {DIR_EFEITOS}/ nem {esquema.ARQ_EFEITOS_EXTRAIDOS}")
    arquivos = []
    for e in entradas:
        p = resolver_caminho(raiz, e)
        if p.is_dir():
            arquivos.extend(sorted(p.glob("*.csv")))
        elif p.exists():
            arquivos.append(p)
        else:
            raise FileNotFoundError(f"entrada não encontrada: {e}")
    return arquivos


def coluna_desenho_master(colunas, codebook=None):
    """Nome da variável de desenho/estratégia de identificação no master, ou None.

    Nunca devolve o classificador do codebook (a variável citada em `aplicavel_se`, ex.
    `tipo_estudo`), mesmo que ele se chame `desenho` em algum codebook.
    """
    classificadores = set()
    candidatas = list(COLUNAS_DESENHO_MASTER)
    if codebook:
        for l in ler_csv(codebook)[1]:
            cond = l.get("aplicavel_se", "").strip()
            if "=" in cond:
                classificadores.add(cond.split("=", 1)[0].strip())
            variavel = l.get("variavel", "").strip()
            if variavel.endswith("estrategia_identificacao") and variavel not in candidatas:
                candidatas.append(variavel)
    return next((c for c in candidatas if c in colunas and c not in classificadores), None)


def _desenho_do_master(master, codebook):
    """(função (ficha_id, chave) -> desenho, coluna usada ou None) a partir do master de fichas."""
    if not master:
        return (lambda ficha_id, chave: ""), None
    colunas, fichas = ler_csv(master)
    coluna = coluna_desenho_master(colunas, codebook)
    if coluna is None:
        return (lambda ficha_id, chave: ""), None

    def valor(f):
        v = normalizar.texto(f.get(coluna, ""))
        return "" if normalizar.ascii_fold(v).lower() in _AUSENTES_MASTER else v

    por_ficha = {f.get("ficha_id", ""): valor(f) for f in fichas}
    por_chave = {}
    for f in fichas:
        por_chave.setdefault(f.get("citekey", ""), set()).add(valor(f))

    def desenho(ficha_id, chave):
        if ficha_id and por_ficha.get(ficha_id, ""):
            return por_ficha[ficha_id]
        valores = {v for v in por_chave.get(chave, set()) if v}
        return valores.pop() if len(valores) == 1 else ""
    return desenho, coluna


def _impressao(linha):
    """Campos que um humano confere; mudança em qualquer um invalida a verificação anterior.

    Inclui as colunas extras que efeitos.R usa como número (quartis e g/d informados).
    """
    campos = ["chave", "outcome", "modelo", "subgrupo", "tipo_estatistica", "p", "evidencia", "pagina"]
    return tuple(normalizar.texto(linha.get(c, "")).replace(",", ".")
                 for c in campos + CAMPOS_NUMERICOS + CAMPOS_NUMERICOS_EXTRAS)


def colunas_efeitos(linhas):
    """Cabeçalho de saída: colunas do esquema e depois as extras, na ordem em que aparecem."""
    extras = []
    for l in linhas:
        extras.extend(c for c in l if c not in esquema.COLUNAS_EFEITOS_EXTRAIDOS and c not in extras)
    return list(esquema.COLUNAS_EFEITOS_EXTRAIDOS) + extras


def preparar_efeitos(raiz, entradas=None, master=None, codebook=None):
    """Consolida e normaliza os efeitos. Devolve (linhas, problemas).

    Cada linha traz as colunas do esquema e, depois delas, as colunas extras (use
    `colunas_efeitos(linhas)` para o cabeçalho).
    """
    raiz = Path(raiz)
    arquivos = _arquivos_entrada(raiz, entradas)
    saida = raiz / esquema.ARQ_EFEITOS_EXTRAIDOS
    anteriores = indexar(ler_linhas(saida), "id_efeito")
    unicos = carregar_unicos(raiz)
    por_chave = {r["chave"].strip(): r for r in unicos.values() if r.get("chave", "").strip()}
    desenho_de, coluna_desenho = _desenho_do_master(master, codebook)
    problemas = []

    def problema(linha, campo, gravidade, texto):
        problemas.append({"id_efeito": linha.get("id_efeito", ""), "chave": linha.get("chave", ""), "campo": campo,
                          "gravidade": gravidade, "problema": texto})

    if master and coluna_desenho is None:
        problemas.append({"id_efeito": "", "chave": "", "campo": "desenho", "gravidade": "aviso",
                          "problema": f"master sem variável de desenho ({', '.join(COLUNAS_DESENHO_MASTER)}): "
                                      "desenho vazio não é preenchido (o classificador a1/a2/b1/b2 não é desenho)"})

    brutas, extras = [], []
    for arq in arquivos:
        colunas, linhas = ler_csv(arq)
        for c in colunas:
            nome = c.strip().lower()
            if nome and nome not in esquema.COLUNAS_EFEITOS_EXTRAIDOS and nome not in extras:
                extras.append(nome)
        for l in linhas:
            minusculas = {}
            for k, v in l.items():
                minusculas.setdefault(k.strip().lower(), v)
            bruta = {c: normalizar.texto(minusculas.get(c, "")) if c != "evidencia"
                     else str(minusculas.get(c, "")).strip() for c in esquema.COLUNAS_EFEITOS_EXTRAIDOS}
            bruta.update({c: normalizar.texto(minusculas.get(c, "")) for c in extras})
            brutas.append(bruta)
    # extras acrescentadas à mão no consolidado anterior (ex.: rob_geral) também são preservadas
    extras_anteriores = []
    for a in anteriores.values():
        extras_anteriores.extend(c for c in a if c and c not in esquema.COLUNAS_EFEITOS_EXTRAIDOS
                                 and c not in extras and c not in extras_anteriores)
    for b in brutas:
        for c in extras + extras_anteriores:
            b.setdefault(c, "")

    contadores, vistos, saida_linhas = {}, set(), []
    ids_informados = {b["id_efeito"] for b in brutas if b["id_efeito"]}
    for l in brutas:
        ch = l["chave"]
        if not _chave.chave_valida(ch):
            problema(l, "chave", "erro", "chave vazia ou inválida")
            continue
        reg = por_chave.get(ch)
        if unicos and reg is None:
            problema(l, "chave", "erro", "chave não existe em registros_unicos.csv")
        if not l["id_efeito"]:
            contadores[ch] = contadores.get(ch, 0) + 1
            while f"{ch}-E{contadores[ch]:02d}" in vistos | ids_informados:
                contadores[ch] += 1
            l["id_efeito"] = f"{ch}-E{contadores[ch]:02d}"
        if l["id_efeito"] in vistos:
            problema(l, "id_efeito", "erro", "id_efeito duplicado")
        vistos.add(l["id_efeito"])
        if reg is not None and not l["id_estudo"]:
            l["id_estudo"] = reg.get("id_estudo", "").strip() or esquema.id_estudo_de(reg["id_rs"])
        if not l["id_estudo"]:
            l["id_estudo"] = ch
        if not l["desenho"]:
            l["desenho"] = desenho_de(l["ficha_id"], ch)
            if not l["desenho"]:
                problema(l, "desenho", "aviso",
                         "desenho vazio: preencha pela estratégia de identificação (RCT, DiD, RDD...); "
                         "o R agrupa como desenho_nao_informado")
        for campo in CAMPOS_NUMERICOS + ["p"] + [c for c in CAMPOS_NUMERICOS_EXTRAS if c in l]:
            if re.fullmatch(r"-?\d+,\d+", l[campo]):
                l[campo] = l[campo].replace(",", ".")
        l["tipo_estatistica"] = l["tipo_estatistica"].lower()
        if l["tipo_estatistica"] not in TIPOS_ESTATISTICA:
            problema(l, "tipo_estatistica", "erro", f"valor inválido {l['tipo_estatistica']!r}")
        l["direcao_desejada"] = normalizar.ascii_fold(l["direcao_desejada"]).lower()
        if l["direcao_desejada"] not in DIRECOES:
            problema(l, "direcao_desejada", "erro", "declare aumentar|reduzir (direção pelo estimador)")
        if l["estimando"]:
            canon = {e.lower(): e for e in ESTIMANDOS}.get(l["estimando"].lower())
            if canon is None:
                problema(l, "estimando", "aviso", f"estimando fora da lista: {l['estimando']!r}")
            else:
                l["estimando"] = canon
        marca = re.sub(r"[\s-]+", "_", normalizar.ascii_fold(l["desenho"]).lower())
        if (reg is not None and reg.get("tipo_publicacao") == "revisao") or any(m in marca for m in _MARCAS_REVISAO):
            problema(l, "desenho", "erro", "revisão/meta-análise não entra como estudo primário (use bola de neve)")
        anterior = anteriores.get(l["id_efeito"])
        mesmos_dados = bool(anterior) and _impressao(anterior) == _impressao(l)
        if anterior and not l["verificado_humano"] and anterior.get("verificado_humano"):
            # só herda a verificação se os dados verificados são os mesmos (ids gerados por ordem podem mudar)
            if mesmos_dados:
                l["verificado_humano"] = anterior["verificado_humano"]
            else:
                problema(l, "verificado_humano", "aviso", "dados do efeito mudaram: verificação humana descartada")
        if anterior:
            herdaveis = [c for c in extras_anteriores if normalizar.texto(anterior.get(c)) and not l.get(c)]
            if herdaveis and mesmos_dados:
                for c in herdaveis:
                    l[c] = normalizar.texto(anterior[c])
            elif herdaveis:
                problema(l, ",".join(herdaveis), "aviso",
                         "dados do efeito mudaram: colunas acrescentadas no consolidado anterior não foram herdadas")
        saida_linhas.append(l)
    # coluna extra do consolidado anterior que não sobrou em nenhuma linha sai do cabeçalho
    vazias = [c for c in extras_anteriores if not any(l.get(c) for l in saida_linhas)]
    for l in saida_linhas:
        for c in vazias:
            l.pop(c, None)

    principais = {}
    for l in saida_linhas:
        principais.setdefault((l["id_estudo"], l["construto_outcome"]), []).append(sim(l["modelo_principal"]))
    for (estudo, construto), marcas in principais.items():
        if len(marcas) > 1 and sum(marcas) != 1:
            problemas.append({"id_efeito": "", "chave": estudo, "campo": "modelo_principal", "gravidade": "aviso",
                              "problema": f"{sum(marcas)} modelos principais para {construto or 'outcome vazio'} "
                                          f"({len(marcas)} efeitos): aplique a regra do protocolo ou use CHE/RVE"})
    saida_linhas.sort(key=lambda l: (l["chave"], l["id_efeito"]))
    return saida_linhas, problemas


# ---------------------------------------------------------------------------
# Projeto parcial sem PDFs ("só a meta-análise" com a planilha do usuário)
# ---------------------------------------------------------------------------
ETAPA_EXTRACAO = "09_extracao_rob"


def projeto_parcial_sem_pdfs(raiz):
    """True se a etapa 09 está ignorada (projeto parcial, ex.: `init --parcial meta`) e não há PDFs no projeto.

    Nesse caso `verificar-efeitos` não tem o que conferir (toda linha sairia PDF_NAO_ENCONTRADO): os números vêm
    da fonte do usuário e o que se relata é a falta de verificação contra os PDFs.
    """
    raiz = Path(raiz)
    try:
        est = estado.carregar_estado(raiz)
    except (estado.ErroProjeto, OSError, ValueError):
        return False
    projeto = est.get("projeto") or {}
    ignorada = ETAPA_EXTRACAO in (projeto.get("etapas_ignoradas") or []) \
        or ((est.get("etapas") or {}).get(ETAPA_EXTRACAO) or {}).get("status") == "ignorada"
    if not (projeto.get("parcial") and ignorada):
        return False
    pasta = raiz / "03-textos" / "pdfs"
    if pasta.is_dir() and any(pasta.rglob("*.pdf")):
        return False
    return not any((l.get("status") or "").strip() in esquema.STATUS_PDF_OK
                   for l in ler_linhas(raiz / esquema.ARQ_RELATORIO_PDFS))


def aviso_sem_pdfs(linhas):
    """Aviso do projeto parcial sem PDFs, com a contagem de linhas sem verificado_humano."""
    total = len(linhas)
    sem = sum(1 for l in linhas if not sim(l.get("verificado_humano")))
    return (f"projeto parcial sem PDFs: os números de efeito vieram da fonte do usuário e não foram verificados contra "
            f"os PDFs pela skill ({sem} de {total} linhas sem verificado_humano); não rode `analise verificar-efeitos` "
            "e declare a limitação no relato (PRISMA 2020 item 23c; references/00-configuracao-estado.md, seção 7)")


def cmd_preparar(args):
    comando = "analise preparar-efeitos"
    raiz = exigir_raiz(args, comando)
    if raiz is None:
        return 1
    master = resolver_caminho(raiz, args.master) if args.master else None
    codebook = resolver_caminho(raiz, args.codebook) if args.codebook else None
    for arq in (master, codebook):
        if arq is not None and not arq.exists():
            return falhar(comando, f"arquivo não encontrado: {arq}")
    try:
        linhas, problemas = preparar_efeitos(raiz, args.entrada, master, codebook)
    except FileNotFoundError as e:
        return falhar(comando, str(e))
    escrever_csv(raiz / ARQ_AVISOS_PREPARACAO, COLUNAS_AVISOS, problemas)
    erros = [p for p in problemas if p["gravidade"] == "erro"]
    if erros:
        return falhar(comando, f"{len(erros)} erros nos efeitos; nada gravado (ver {ARQ_AVISOS_PREPARACAO})",
                      erros=erros[:10])
    colunas = colunas_efeitos(linhas)
    extras = colunas[len(esquema.COLUNAS_EFEITOS_EXTRAIDOS):]
    escrever_csv(raiz / esquema.ARQ_EFEITOS_EXTRAIDOS, colunas, linhas)
    n_desenho_vazio = sum(1 for l in linhas if not l["desenho"])
    sem_pdfs = projeto_parcial_sem_pdfs(raiz)
    avisos = [aviso_sem_pdfs(linhas)] if sem_pdfs else []
    n_nao_verificados = sum(1 for l in linhas if not sim(l.get("verificado_humano")))
    estado.registrar_evento(raiz, "extracao_consolidada", "09_extracao_rob", "script", ATOR,
                            dados={"n_efeitos": len(linhas), "n_estudos": len({l["id_estudo"] for l in linhas}),
                                   "n_avisos": len(problemas), "colunas_extras": extras,
                                   "n_desenho_vazio": n_desenho_vazio, "sem_pdfs": sem_pdfs,
                                   "n_nao_verificados_humano": n_nao_verificados},
                            artefatos=[esquema.ARQ_EFEITOS_EXTRAIDOS, ARQ_AVISOS_PREPARACAO])
    for aviso in avisos:
        print(f"[aviso] {aviso}", file=sys.stderr)
    estado.resumo({"comando": comando, "ok": True, "n_efeitos": len(linhas),
                   "n_estudos": len({l["id_estudo"] for l in linhas}), "n_avisos": len(problemas),
                   "colunas_extras": extras, "n_desenho_vazio": n_desenho_vazio,
                   "n_nao_verificados_humano": n_nao_verificados, "sem_pdfs": sem_pdfs, "avisos": avisos,
                   "arquivos": [esquema.ARQ_EFEITOS_EXTRAIDOS, ARQ_AVISOS_PREPARACAO],
                   "proximo_passo": "rs.py analise efeitos" if sem_pdfs else "rs.py analise verificar-efeitos"})
    return 0


# ---------------------------------------------------------------------------
# verificar-efeitos
# ---------------------------------------------------------------------------
def verificar_efeitos(raiz, arquivo_efeitos, pasta_pdfs=None, usar_irma=True):
    raiz = Path(raiz)
    _, linhas = ler_csv(arquivo_efeitos)
    relatorio = indexar(ler_linhas(raiz / esquema.ARQ_RELATORIO_PDFS), "chave")
    verificador = Verificador(usar_irma=usar_irma)
    saida = []
    for l in linhas:
        ch = l.get("chave", "").strip()
        paginas = ler_paginas_indicadas(l.get("pagina"))
        pdf = None
        if pasta_pdfs and (Path(pasta_pdfs) / f"{ch}.pdf").is_file():
            pdf = Path(pasta_pdfs) / f"{ch}.pdf"
        pdf = pdf or localizar_pdf(raiz, ch, relatorio)
        encontradas = []
        if not normalizar.texto(l.get("evidencia")):
            status = "SEM_TRECHO"
        elif pdf is None:
            status = "PDF_NAO_ENCONTRADO"
        else:
            status, encontradas = verificador.localizar(pdf, l["evidencia"], paginas)
        erros, alertas, g, p_calc = checar_plausibilidade(l)
        humano = sim(l.get("verificado_humano"))
        trecho_ok = status == "OK" or (status == "PDF_TEXTO_NAO_EXTRAIVEL" and humano)
        if status == "PDF_TEXTO_NAO_EXTRAIVEL":
            alertas.append("PDF sem camada de texto: conferência visual humana obrigatória")
        saida.append({
            "id_efeito": l.get("id_efeito", ""), "chave": ch, "pagina": l.get("pagina", ""), "status_trecho": status,
            "pagina_encontrada": ";".join(map(str, encontradas)), "verificador": verificador.nome,
            "erros": " | ".join(erros), "alertas": " | ".join(alertas),
            "g_aproximado": "" if g is None else f"{g:.3f}", "p_calculado": "" if p_calc is None else f"{p_calc:.4g}",
            "verificado_humano": "1" if humano else "0",
            "apto_g7": "1" if (trecho_ok and not erros and humano) else "0",
        })
    return saida, verificador.nome


def cmd_verificar(args):
    comando = "analise verificar-efeitos"
    raiz = exigir_raiz(args, comando)
    if raiz is None:
        return 1
    arquivo = resolver_caminho(raiz, args.efeitos)
    if not arquivo.exists():
        return falhar(comando, f"arquivo não encontrado: {arquivo} (rode `analise preparar-efeitos`)")
    pasta = resolver_caminho(raiz, args.pdfs) if args.pdfs else None
    try:
        linhas, via = verificar_efeitos(raiz, arquivo, pasta, usar_irma=not args.sem_irma)
    except ErroDependencia as e:
        return falhar(comando, str(e), codigo=3)
    saida = resolver_caminho(raiz, args.saida)
    escrever_csv(saida, COLUNAS_VERIFICACAO, linhas)
    contagem = {}
    for l in linhas:
        contagem[l["status_trecho"]] = contagem.get(l["status_trecho"], 0) + 1
    falhas_trecho = [l["id_efeito"] for l in linhas if l["status_trecho"] in STATUS_FALHA]
    com_erro = [l["id_efeito"] for l in linhas if l["erros"]]
    pendentes = [l["id_efeito"] for l in linhas if l["apto_g7"] != "1"]
    pode_seguir = bool(linhas) and not pendentes
    rel = relativo(raiz, saida)
    estado.registrar_evento(raiz, "efeitos_verificados", "09_extracao_rob", "script", ATOR,
                            dados={"n_efeitos": len(linhas), "status_trecho": contagem,
                                   "n_erros_plausibilidade": len(com_erro), "n_nao_aptos": len(pendentes),
                                   "pode_seguir_g7": pode_seguir, "verificador": via},
                            artefatos=[relativo(raiz, arquivo), rel])
    # n = linhas não aptas ao G7; zero fecha a pendência (em qualquer modo); n diferente atualiza sem duplicar.
    pendencia = sincronizar_pendencia_unica(
        raiz, esquema.PENDENCIA_VERIFICACAO_HUMANA_EFEITOS, "09_extracao_rob",
        "conferir 100% dos dados de efeito na página do PDF e marcar verificado_humano",
        len(pendentes), portao="G7", arquivo=rel, ator_id=ATOR,
        motivo_resolvida="todas as linhas aptas ao G7 (trecho, plausibilidade e verificado_humano)")
    estado.resumo({"comando": comando, "ok": not (falhas_trecho or com_erro), "n_efeitos": len(linhas),
                   "status_trecho": contagem, "falhas_trecho": falhas_trecho[:20], "erros_plausibilidade": com_erro[:20],
                   "n_alertas": sum(1 for l in linhas if l["alertas"]), "n_nao_aptos_g7": len(pendentes),
                   "pode_seguir_g7": pode_seguir, "verificador": via, "arquivo": rel, "pendencia": pendencia})
    return 2 if (falhas_trecho or com_erro) else 0


def registrar(subparsers):
    p = subparsers.add_parser("analise", help="dados de efeito e síntese: preparar-efeitos, verificar-efeitos, "
                                              "efeitos, meta, swim, combinados")
    sub = p.add_subparsers(dest="acao_analise", metavar="<ação>")
    q = sub.add_parser("preparar-efeitos", help="consolida CSVs do extrator em 05-decomposicao/efeitos_extraidos.csv")
    q.add_argument("--entrada", nargs="*", default=None, help=f"CSVs ou pastas (padrão {DIR_EFEITOS}/)")
    q.add_argument("--master", default=None, help="fichamentos_master.csv (desenho do estudo)")
    q.add_argument("--codebook", default=None, help="codebook da decomposição (variável classificadora)")
    q.set_defaults(func=cmd_preparar)
    q = sub.add_parser("verificar-efeitos", help="trecho verbatim na página + plausibilidade + verificação humana")
    q.add_argument("--efeitos", default=esquema.ARQ_EFEITOS_EXTRAIDOS)
    q.add_argument("--pdfs", default=None, help="pasta com <chave>.pdf (padrão: relatorio_pdfs.csv e 03-textos/pdfs)")
    q.add_argument("--saida", default=ARQ_VERIFICACAO_EFEITOS)
    q.add_argument("--sem-irma", action="store_true", help="não usar o gate do fichamento-sistematico")
    q.set_defaults(func=cmd_verificar)
    p.set_defaults(func=lambda a, _p=p: (_p.print_help(), 1)[1])
