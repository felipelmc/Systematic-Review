"""Risco de viés (RoB) e apreciação crítica: concordância de A e B, fila de desacordos e rob_geral consolidado.

USO
    # 1) duas avaliações independentes -> concordância por domínio e arquivo de consenso com a fila humana
    python3 rs.py qualidade consolidar --ferramenta rob2 \
        --a 04-qualidade/rob_rob2_A.csv --b 04-qualidade/rob_rob2_B.csv \
        [--avaliador-a revisor_humano_1] [--avaliador-b revisor_humano_2] [--codebook 00-protocolo/codebook_v0_rob2.csv]
    # 2) depois que humanos resolveram os desacordos no arquivo de consenso -> rob_geral
    python3 rs.py qualidade consolidar --ferramenta rob2 --consenso 04-qualidade/rob_rob2_consenso.csv \
        [--por revisor_humano_1] [--ignorar-no-geral D1,D2]

Ferramentas: rob2, robins_i, epoc, casp_qualitativo, jbi_transversal, mmat (os codebooks de
assets/codebooks/ e a seção de vocabulário de references/05-qualidade.md).

ENTRADAS --a e --b (CSV com vírgula, ponto e vírgula ou tabulação, ou .xlsx), em um de três formatos:
    longo      chave, construto_outcome, dominio, julgamento, trecho, pagina [, id_estudo, justificativa]
    largo      chave, construto_outcome, D1, ..., Dk [, rob_geral] (checklists: Q1, ..., Qk
               [, preocupacao_metodologica]) [, id_estudo, justificativa, fonte]
    master     fichamentos_master do fichamento-sistematico (ficha_id, citekey, <variavel>,
               <variavel>__evidencia): RoB 2 e ROBINS-I usam `dN_julgamento[_proposto]` como domínio N e
               `geral_julgamento[_proposto]` como geral; EPOC, CASP, JBI e MMAT usam as variáveis do
               codebook (critérios `PROPOSTA` no EPOC; itens categóricos nas checklists) e
               `preocupacao_metodologica[_proposta]` como geral. O sufixo de `ficha_id`
               (`Chave#sufixo`) vira construto_outcome, salvo quando é o nome da ferramenta; no MMAT o
               sufixo é a categoria da ficha. O trecho e a página saem de `<variavel>__evidencia`.
    Valores com prefixo `proposta_` são rascunho de IA: são aceitos, mas o avaliador daquele arquivo
    passa a contar como IA (concordância com ele não valida nada sozinha).

Vocabulário (acentos, caixa e inglês são normalizados; outro valor é erro, código 1)
    rob2       domínio e geral: baixo | algumas_preocupacoes | alto
    robins_i   domínio: baixo_exceto_confundimento (ou baixo) | moderado | grave | critico;
               geral: baixo_exceto_confundimento | moderado | grave | critico
    epoc       critério: baixo | incerto | alto; geral: baixo | moderado | alto
    casp_qualitativo, mmat   itens: S | N | NPD
    jbi_transversal          itens: S | N | I | NA
    checklists, geral        preocupacao_metodologica: nenhuma_ou_muito_pequena | menores | moderadas | graves
    Vazio, NA_secao e "não se aplica" = domínio não aplicável (RoB 2 D1b fora de cluster, variante
    do domínio 1 do ROBINS-I). No JBI, NA é resposta válida do item.

FASE 1 (--a e --b)
    - A e B precisam avaliar os mesmos resultados e domínios (senão código 1, com a lista).
    - Concordância por domínio: proporção de concordância, κ de Cohen e PABAK = (k·Po − 1)/(k − 1),
      com k = número de níveis da escala do domínio (RoB 2: 3; ROBINS-I: 4; EPOC: 3; itens: 3 ou 4).
      Sinalizado quando Po < 0,80 ou quando nem κ nem PABAK chegam a 0,70 (o mesmo limiar da
      extração categórica). A concordância descreve a confiabilidade: não substitui o consenso.
      Grava PADRAO_CONCORDANCIA.
    - Grava esquema.PADRAO_ROB_CONSENSO (colunas esquema.COLUNAS_ROB_CONSENSO), uma linha por
      resultado × domínio: julgamento_a, julgamento_b; julgamento_consenso preenchido e
      resolvido_por = `concordancia:<avaliador A>+<avaliador B>` quando A e B concordam; vazios nos
      desacordos (a fila humana). No RoB 2, ROBINS-I e EPOC o geral de A e B entra só na
      concordância (o geral do consenso sai do algoritmo, fase 2); nas checklists a linha
      `dominio = geral` (preocupação metodológica) entra no consenso, porque não há algoritmo.
    - Reexecutar nunca apaga resolução humana: a linha com o mesmo julgamento_a e julgamento_b
      mantém julgamento_consenso, justificativa e resolvido_por; linhas `dominio = geral`
      acrescentadas à mão também ficam. Se A ou B mudou, a resolução antiga cai, com aviso.
    - Evento `fila_gerada` (fila `consenso_rob`) e pendência `consenso_rob` com n = desacordos sem
      resolução humana (via handoff.sincronizar_pendencia_unica: só abre no autopiloto; n = 0 fecha).

FASE 2 (--consenso)
    - Todo desacordo precisa de julgamento_consenso válido e resolvido_por humano (um papel com
      "humano", ex.: esquema.PAPEL_HUMANO_PADRAO). `--por <papel>` preenche resolvido_por onde ele
      está vazio e o consenso foi editado (declaração explícita; papel não humano é recusado).
      Faltando algo: código 2, lista das linhas, pendência atualizada e nada gravado em rob_geral.
    - rob_geral por chave × construto_outcome:
        RoB 2      pior domínio (baixo < algumas_preocupacoes < alto); com preocupações em dois ou
                   mais domínios e nenhum alto, aviso: a ferramenta permite julgar alto quando elas
                   reduzem muito a confiança (decisão humana, ver sobreposição)
        ROBINS-I   pior domínio (baixo_exceto_confundimento < moderado < grave < critico); com dois
                   ou mais domínios no pior nível moderado ou grave, aviso do julgamento aditivo
                   (vários moderados -> grave; vários graves -> crítico)
        EPOC       pior critério, com incerto = moderado (convenção declarada no protocolo; o EPOC
                   não define geral); `--ignorar-no-geral` tira critérios do algoritmo (ex.:
                   sequência e ocultação, altos por definição em antes-depois controlado)
        checklists linha `dominio = geral` do consenso (preocupação metodológica, sem soma de itens)
      Sobreposição: uma linha `dominio = geral` com julgamento_consenso, resolvido_por humano e
      justificativa substitui o algoritmo, só para um nível igual ou mais grave que o pior domínio.
    - validado_humano = 1 quando todas as linhas do resultado foram resolvidas por humano ou
      concordadas por A e B com ao menos um avaliador humano.
    - Grava esquema.ARQ_ROB_GERAL (colunas esquema.COLUNAS_ROB_GERAL), trocando só as linhas da
      ferramenta; registra `rob_consolidado` com a concordância; fecha a pendência `consenso_rob`.
      Reexecução com o mesmo consenso e o mesmo resultado não registra evento novo.

POR QUE ASSIM
    MECIR C53 exige RoB em dupla independente com regra de desacordo, e a especificação desta
    skill (references/05-qualidade.md; Apêndice D da base de conhecimento, item 8) exige julgamento
    por domínio e humano. O script não julga: mede a concordância, separa o que precisa de
    decisão humana e aplica o algoritmo da ferramenta ao consenso. A regra do pior domínio é a
    padrão do RoB 2 (Sterne et al. 2019) e do ROBINS-I V2 (guidance note 17, 20/11/2025); os
    julgamentos aditivos continuam humanos.
"""

import csv
import io
import re
import unicodedata
from collections import Counter
from pathlib import Path

from . import esquema, estado
from .handoff import (DIR_ASSETS, carregar_unicos, escrever_csv, exigir_raiz, falhar, ler_csv, relativo,
                      resolver_caminho, sincronizar_pendencia_unica)

ATOR = "rs.py qualidade"
ETAPA = "09_extracao_rob"
PORTAO = "G7"
FERRAMENTAS = ["rob2", "robins_i", "epoc", "casp_qualitativo", "jbi_transversal", "mmat"]
FERRAMENTAS_ALGORITMO = ["rob2", "robins_i", "epoc"]
# Pendência dos desacordos e arquivo de concordância: valem as de esquema.py (v1.3); aqui ficam como aliases.
PENDENCIA_CONSENSO_ROB = getattr(esquema, "PENDENCIA_CONSENSO_ROB", "consenso_rob")
PADRAO_CONCORDANCIA = getattr(esquema, "PADRAO_CONCORDANCIA_ROB", "04-qualidade/rob_{ferramenta}_concordancia.csv")
COLUNAS_CONCORDANCIA = ["ferramenta", "dominio", "n", "n_concordantes", "n_desacordos", "concordancia", "kappa",
                        "pabak", "k_niveis", "sinalizado"]
DOMINIO_GERAL = "geral"
NAO_SE_APLICA = "nao_se_aplica"
LIMIAR_CONCORDANCIA = 0.80
LIMIAR_KAPPA_PABAK = 0.70
PREFIXO_CONCORDANCIA = "concordancia:"

ESCALA_DOMINIO = {
    "rob2": {"baixo": 1, "algumas_preocupacoes": 2, "alto": 3},
    "robins_i": {"baixo_exceto_confundimento": 1, "baixo": 1, "moderado": 2, "grave": 3, "critico": 4},
    "epoc": {"baixo": 1, "incerto": 2, "alto": 3},
}
ESCALA_GERAL = {
    "rob2": {"baixo": 1, "algumas_preocupacoes": 2, "alto": 3},
    "robins_i": {"baixo_exceto_confundimento": 1, "moderado": 2, "grave": 3, "critico": 4},
    "epoc": {"baixo": 1, "moderado": 2, "alto": 3},
}
GERAL_POR_NIVEL = {ferr: {n: rotulo for rotulo, n in escala.items()} for ferr, escala in ESCALA_GERAL.items()}
ESCALA_ITENS = {"casp_qualitativo": ["S", "N", "NPD"], "mmat": ["S", "N", "NPD"], "jbi_transversal": ["S", "N", "I", "NA"]}
ESCALA_PREOCUPACAO = {"nenhuma_ou_muito_pequena": 1, "menores": 2, "moderadas": 3, "graves": 4}

_ALIASES = {
    "low": "baixo", "baixo_risco": "baixo", "risco_baixo": "baixo",
    "some_concerns": "algumas_preocupacoes", "preocupacoes": "algumas_preocupacoes",
    "algumas_preocupacao": "algumas_preocupacoes",
    "high": "alto", "alto_risco": "alto", "risco_alto": "alto",
    "moderate": "moderado", "moderada": "moderado", "serious": "grave", "serio": "grave", "critical": "critico",
    "unclear": "incerto", "incerta": "incerto",
    "low_except_for_concerns_about_uncontrolled_confounding": "baixo_exceto_confundimento",
}
_ALIASES_ITENS = {
    "s": "S", "sim": "S", "y": "S", "yes": "S", "n": "N", "nao": "N", "no": "N",
    "npd": "NPD", "nao_e_possivel_dizer": "NPD", "cant_tell": "NPD", "can_t_tell": "NPD",
    "i": "I", "incerto": "I", "unclear": "I", "na": "NA", "not_applicable": "NA",
}
_ALIASES_PREOCUPACAO = {
    "nenhuma": "nenhuma_ou_muito_pequena", "muito_pequena": "nenhuma_ou_muito_pequena",
    "nenhuma_ou_muito_pequenas": "nenhuma_ou_muito_pequena", "no_or_very_minor": "nenhuma_ou_muito_pequena",
    "menor": "menores", "minor": "menores", "moderada": "moderadas", "moderate": "moderadas",
    "grave": "graves", "serious": "graves",
}
_TOKENS_NAO_APLICA = {"", "na_secao", "nao_se_aplica", "nao_aplicavel", "n_a"}
RE_JULGAMENTO_MASTER = re.compile(r"^(d\d+[a-z]?)_julgamento(_proposto)?$", re.IGNORECASE)
RE_DOMINIO_CURTO = re.compile(r"^([dq])(\d+[a-z]?)$", re.IGNORECASE)
COLUNAS_GERAL = {"rob_geral", "geral", "julgamento_geral", "geral_julgamento", "geral_julgamento_proposto",
                 "preocupacao_metodologica", "preocupacao_metodologica_proposta", "overall"}
RE_EVIDENCIA = re.compile(r'"([^"]+)"\s*\(pp?\.?\s*(\d+(?:\s*[-–]\s*\d+)?)\)')


class ErroEntrada(ValueError):
    """Entrada inválida (código 1)."""


class ErroDependenciaXlsx(RuntimeError):
    """openpyxl ausente para ler .xlsx (código 3)."""


# ---------------------------------------------------------------------------
# Leitura de tabelas humanas
# ---------------------------------------------------------------------------
def _texto(valor):
    """Texto com espaços colapsados. Não usa normalizar.texto, que apaga "NA" (resposta válida no JBI)."""
    return re.sub(r"\s+", " ", "" if valor is None else str(valor)).strip()


def _fold(valor):
    return unicodedata.normalize("NFKD", _texto(valor)).encode("ascii", "ignore").decode("ascii")


def ler_tabela(caminho):
    """(colunas, linhas) de CSV com `,`, `;` ou tabulação (UTF-8 ou cp1252) ou de .xlsx (primeira aba)."""
    caminho = Path(caminho)
    if caminho.suffix.lower() in (".xlsx", ".xlsm"):
        try:
            import openpyxl
        except ImportError as e:
            raise ErroDependenciaXlsx("openpyxl ausente para ler .xlsx: pip install openpyxl (ou salve como CSV)") from e
        livro = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
        linhas_brutas = list(livro.worksheets[0].iter_rows(values_only=True))
        if not linhas_brutas:
            return [], []
        colunas = [str(c or "").strip() for c in linhas_brutas[0]]
        linhas = [{c: ("" if v is None else str(v)) for c, v in zip(colunas, r)}
                  for r in linhas_brutas[1:] if any(v not in (None, "") for v in r)]
        return colunas, linhas
    try:
        texto = caminho.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        texto = caminho.read_text(encoding="cp1252")
    primeira = texto.splitlines()[0] if texto.strip() else ""
    try:
        delimitador = csv.Sniffer().sniff(primeira, delimiters=",;\t").delimiter
    except csv.Error:
        delimitador = ","
    leitor = csv.DictReader(io.StringIO(texto, newline=""), delimiter=delimitador)
    colunas = [c.strip() for c in (leitor.fieldnames or [])]
    linhas = [{(k or "").strip(): ("" if v is None else str(v)) for k, v in l.items() if k is not None} for l in leitor]
    return colunas, linhas


# ---------------------------------------------------------------------------
# Vocabulário
# ---------------------------------------------------------------------------
def _token(valor):
    s = _fold(valor).lower().strip()
    s = re.sub(r"[\s\-/()]+", "_", s).strip("_")
    return s


def normalizar_valor(ferramenta, valor, papel="dominio"):
    """(canônico, proposta) para um julgamento; canônico = NAO_SE_APLICA ou None (inválido).

    `papel`: dominio (julgamento de domínio ou item) ou geral.
    """
    bruto = _texto(valor)
    proposta = _token(bruto).startswith("proposta_")
    s = _token(bruto)
    if proposta:
        s = s[len("proposta_"):]
    itens = ferramenta in ESCALA_ITENS
    if itens and papel == "dominio":
        if s == "na" and "NA" in ESCALA_ITENS[ferramenta]:
            return "NA", proposta
        if s in _TOKENS_NAO_APLICA or s == "na":
            return NAO_SE_APLICA, proposta
        canon = _ALIASES_ITENS.get(s, bruto.strip().upper())
        return (canon if canon in ESCALA_ITENS[ferramenta] else None), proposta
    if s in _TOKENS_NAO_APLICA or s == "na":
        return NAO_SE_APLICA, proposta
    if itens:  # geral das checklists
        canon = _ALIASES_PREOCUPACAO.get(s, s)
        return (canon if canon in ESCALA_PREOCUPACAO else None), proposta
    if s.startswith("baixo_exceto") or s.startswith("low_except"):
        s = "baixo_exceto_confundimento"
    canon = _ALIASES.get(s, s)
    if ferramenta == "epoc" and papel == "geral" and canon == "incerto":
        canon = "moderado"
    escala = ESCALA_GERAL[ferramenta] if papel == "geral" else ESCALA_DOMINIO[ferramenta]
    if ferramenta == "robins_i" and papel == "geral" and canon == "baixo":
        canon = "baixo_exceto_confundimento"
    return (canon if canon in escala else None), proposta


def nivel(ferramenta, valor, papel="dominio"):
    """Posição na escala ordinal (None fora dela ou em itens de checklist)."""
    if ferramenta in ESCALA_ITENS:
        return ESCALA_PREOCUPACAO.get(valor) if papel == "geral" else None
    escala = ESCALA_GERAL[ferramenta] if papel == "geral" else ESCALA_DOMINIO[ferramenta]
    return escala.get(valor)


def niveis_da_escala(ferramenta, papel="dominio"):
    if ferramenta in ESCALA_ITENS:
        return len(ESCALA_PREOCUPACAO) if papel == "geral" else len(ESCALA_ITENS[ferramenta])
    escala = ESCALA_GERAL[ferramenta] if papel == "geral" else ESCALA_DOMINIO[ferramenta]
    return len(set(escala.values()))


def rotulo_comparavel(ferramenta, valor):
    """Rótulo usado para comparar A e B (no ROBINS-I, baixo e baixo_exceto_confundimento são o mesmo nível)."""
    if ferramenta == "robins_i" and valor == "baixo_exceto_confundimento":
        return "baixo"
    return valor


def normalizar_dominio(nome):
    s = _texto(nome)
    t = _token(s)
    if t in COLUNAS_GERAL:
        return DOMINIO_GERAL
    m = RE_JULGAMENTO_MASTER.match(s)
    if m:
        s = m.group(1)
    m = RE_DOMINIO_CURTO.match(s)
    if m:
        return m.group(1).upper() + m.group(2).lower()
    return s


def eh_papel_humano(papel):
    """True para papéis humanos (`revisor_humano_1`, `humano_2`); `concordancia:X+Y` é humano se X ou Y for."""
    s = _fold(papel).lower().strip()
    if s.startswith(PREFIXO_CONCORDANCIA):
        return any(eh_papel_humano(p) for p in s[len(PREFIXO_CONCORDANCIA):].split("+"))
    if not s or re.search(r"(^|[^a-z])(ia|ai|llm|modelo|subagente|api|script|regra|arbitro|autopiloto|proposta)([^a-z]|$)",
                          s):
        return False
    return "human" in s


# ---------------------------------------------------------------------------
# Leitura de uma avaliação (A ou B)
# ---------------------------------------------------------------------------
def _codebook(raiz, ferramenta, indicado=None):
    if indicado:
        return Path(indicado)
    candidatos = [Path(raiz) / "00-protocolo" / f"codebook_v0_{ferramenta}.csv",
                  DIR_ASSETS / "codebooks" / f"{ferramenta}.csv"]
    return next((c for c in candidatos if c.is_file()), None)


def variaveis_dominio_codebook(ferramenta, codebook):
    """Variáveis do codebook que são julgamentos de domínio (EPOC) ou itens (checklists)."""
    if not codebook or not Path(codebook).is_file() or ferramenta in ("rob2", "robins_i"):
        return []
    _, linhas = ler_csv(codebook)
    classificadores = {l.get("aplicavel_se", "").split("=", 1)[0].strip() for l in linhas if "=" in l.get("aplicavel_se", "")}
    saida = []
    for l in linhas:
        var = l.get("variavel", "").strip()
        prompt = _texto(l.get("prompt"))
        if not var or var in classificadores or var == "resultado_avaliado" or l.get("tipo", "").strip() != "categorica":
            continue
        if ferramenta == "epoc":
            if prompt.startswith("PROPOSTA"):
                saida.append(var)
        elif not var.endswith(("_proposta", "_proposto")) and var not in ("direcao_vies_proposta",):
            saida.append(var)
    return saida


def _evidencia(texto):
    achados = RE_EVIDENCIA.findall(texto or "")
    return " | ".join(t for t, _ in achados), ";".join(p.replace(" ", "") for _, p in achados)


def _chave_resultado(linha, ferramenta, colunas_low):
    chave = _texto(linha.get(colunas_low.get("chave", ""), "") or linha.get(colunas_low.get("citekey", ""), ""))
    construto = _texto(linha.get(colunas_low.get("construto_outcome", ""), ""))
    ficha = _texto(linha.get(colunas_low.get("ficha_id", ""), ""))
    if "construto_outcome" not in colunas_low and "#" in ficha:
        sufixo = ficha.split("#", 1)[1]
        construto = "" if sufixo == ferramenta else sufixo
    if not chave and "#" in ficha:
        chave = ficha.split("#", 1)[0]
    return chave, construto


def ler_avaliacao(caminho, ferramenta, codebook=None):
    """{(chave, construto, dominio): registro} de uma avaliação, mais (erros, n_propostas, formato)."""
    colunas, linhas = ler_tabela(caminho)
    colunas_low = {c.strip().lower(): c for c in colunas}
    nome = Path(caminho).name
    if not linhas:
        raise ErroEntrada(f"{nome}: sem linhas")
    if "chave" not in colunas_low and "citekey" not in colunas_low and "ficha_id" not in colunas_low:
        raise ErroEntrada(f"{nome}: falta a coluna chave (ou citekey/ficha_id)")
    registros, erros, n_propostas = {}, [], 0
    if "dominio" in colunas_low and "julgamento" in colunas_low:
        formato = "longo"
        pares = []
        for i, l in enumerate(linhas, start=2):
            pares.append((i, l, normalizar_dominio(l.get(colunas_low["dominio"], "")), colunas_low["julgamento"],
                          l.get(colunas_low.get("trecho", ""), ""), l.get(colunas_low.get("pagina", ""), "")))
    else:
        variaveis = set(variaveis_dominio_codebook(ferramenta, codebook))
        dominios = [c for c in colunas if RE_JULGAMENTO_MASTER.match(c) or RE_DOMINIO_CURTO.match(c)
                    or c in variaveis or _token(c) in COLUNAS_GERAL]
        if ferramenta in ("rob2", "robins_i"):
            dominios = [c for c in dominios if not RE_DOMINIO_CURTO.match(c) or c[0] in "dD"]
        if not dominios:
            raise ErroEntrada(f"{nome}: nenhuma coluna de domínio reconhecida (D1..Dk, Q1..Qk, dN_julgamento, "
                              "variáveis do codebook) nem formato longo (dominio, julgamento)")
        formato = "master" if "ficha_id" in colunas_low or any(f"{c}__evidencia" in colunas for c in dominios) else "largo"
        pares = []
        for i, l in enumerate(linhas, start=2):
            for c in dominios:
                trecho, pagina = _evidencia(l.get(f"{c}__evidencia", ""))
                pares.append((i, l, normalizar_dominio(c), c, trecho, pagina))
    for i, l, dominio, coluna_valor, trecho, pagina in pares:
        chave, construto = _chave_resultado(l, ferramenta, colunas_low)
        if not chave:
            erros.append(f"{nome}:linha {i}: chave vazia")
            continue
        if not dominio:
            erros.append(f"{nome}:linha {i}: dominio vazio")
            continue
        papel = "geral" if dominio == DOMINIO_GERAL else "dominio"
        bruto = l.get(coluna_valor, "")
        valor, proposta = normalizar_valor(ferramenta, bruto, papel)
        if valor is None:
            erros.append(f"{nome}:linha {i}: {dominio} = {bruto!r} fora do vocabulário de {ferramenta}")
            continue
        n_propostas += int(proposta)
        k = (chave, construto, dominio)
        if k in registros:
            erros.append(f"{nome}:linha {i}: {chave} × {construto or '(sem construto)'} × {dominio} repetido")
            continue
        justificativa = " ; ".join(x for x in (_texto(l.get(colunas_low.get("justificativa", ""), "")),
                                               _texto(l.get(colunas_low.get("fonte", ""), ""))) if x)
        registros[k] = {"valor": valor, "id_estudo": _texto(l.get(colunas_low.get("id_estudo", ""), "")),
                        "trecho": _texto(trecho), "pagina": _texto(pagina),
                        "justificativa": justificativa}
    return registros, erros, n_propostas, formato


# ---------------------------------------------------------------------------
# Concordância
# ---------------------------------------------------------------------------
def concordancia(pares, k_niveis):
    """{n, n_concordantes, concordancia, kappa, pabak, k_niveis, sinalizado} para pares (a, b)."""
    n = len(pares)
    if not n:
        return {"n": 0, "n_concordantes": 0, "n_desacordos": 0, "concordancia": None, "kappa": None, "pabak": None,
                "k_niveis": k_niveis, "sinalizado": True}
    iguais = sum(a == b for a, b in pares)
    po = iguais / n
    categorias = {x for par in pares for x in par}
    cont_a, cont_b = Counter(a for a, _ in pares), Counter(b for _, b in pares)
    pe = sum((cont_a[c] / n) * (cont_b[c] / n) for c in categorias)
    kappa = None if abs(1.0 - pe) < 1e-15 else (po - pe) / (1.0 - pe)
    k = max(2, k_niveis, len(categorias))
    pabak = (k * po - 1.0) / (k - 1.0)
    validos = [x for x in (kappa, pabak) if x is not None]
    sinalizado = po < LIMIAR_CONCORDANCIA or not validos or max(validos) < LIMIAR_KAPPA_PABAK
    return {"n": n, "n_concordantes": iguais, "n_desacordos": n - iguais, "concordancia": round(po, 4),
            "kappa": None if kappa is None else round(kappa, 4), "pabak": round(pabak, 4), "k_niveis": k,
            "sinalizado": sinalizado}


def concordancia_por_dominio(ferramenta, pares_por_dominio):
    saida = {}
    for dominio in sorted(pares_por_dominio, key=lambda d: (d == DOMINIO_GERAL, d)):
        papel = "geral" if dominio == DOMINIO_GERAL else "dominio"
        saida[dominio] = concordancia(pares_por_dominio[dominio], niveis_da_escala(ferramenta, papel))
    return saida


def _linhas_concordancia(ferramenta, conc):
    return [{"ferramenta": ferramenta, "dominio": d, **{k: ("" if v is None else v) for k, v in c.items()}}
            for d, c in conc.items()]


# ---------------------------------------------------------------------------
# Fase 1: A e B -> consenso com fila
# ---------------------------------------------------------------------------
def _juntar_texto(a, b):
    a, b = _texto(a), _texto(b)
    if not a or not b or a == b:
        return a or b
    return f"A: {a} || B: {b}"


def status_linha(ferramenta, linha):
    """'ok' ou o motivo pelo qual a linha do consenso ainda não está resolvida."""
    papel = "geral" if linha["dominio"] == DOMINIO_GERAL else "dominio"
    a, b = linha.get("julgamento_a", ""), linha.get("julgamento_b", "")
    consenso = _texto(linha.get("julgamento_consenso"))
    por = _texto(linha.get("resolvido_por"))
    if not consenso:
        return "sem julgamento_consenso"
    valor, _ = normalizar_valor(ferramenta, consenso, papel)
    if valor is None:
        return f"julgamento_consenso {consenso!r} fora do vocabulário"
    if _token(consenso).startswith("proposta_"):
        return "julgamento_consenso com prefixo proposta_ (rascunho de IA)"
    if not por:
        return "resolvido_por vazio"
    if por.lower().startswith(PREFIXO_CONCORDANCIA):
        va = normalizar_valor(ferramenta, a, papel)[0]
        vb = normalizar_valor(ferramenta, b, papel)[0]
        if not (va and vb and rotulo_comparavel(ferramenta, va) == rotulo_comparavel(ferramenta, vb)
                == rotulo_comparavel(ferramenta, valor)):
            return "resolvido_por = concordancia, mas A, B e consenso não coincidem"
        return "ok"
    if not eh_papel_humano(por):
        return f"resolvido_por {por!r} não é papel humano (ex.: {esquema.PAPEL_HUMANO_PADRAO})"
    return "ok"


def montar_consenso(raiz, ferramenta, reg_a, reg_b, avaliador_a, avaliador_b, anterior):
    """(linhas do consenso, pares por domínio, avisos). Levanta ErroEntrada se A e B divergem no conjunto."""
    aplicaveis_a = {k for k, r in reg_a.items() if r["valor"] != NAO_SE_APLICA}
    aplicaveis_b = {k for k, r in reg_b.items() if r["valor"] != NAO_SE_APLICA}
    so_a = sorted(k for k in aplicaveis_a - aplicaveis_b if k not in reg_b)
    so_b = sorted(k for k in aplicaveis_b - aplicaveis_a if k not in reg_a)
    if so_a or so_b:
        fmt = lambda ks: ", ".join(f"{c}×{o or '-'}×{d}" for c, o, d in ks[:10])  # noqa: E731
        raise ErroEntrada("A e B não avaliaram os mesmos resultados e domínios"
                          + (f"; só em A: {fmt(so_a)}" if so_a else "") + (f"; só em B: {fmt(so_b)}" if so_b else ""))
    por_chave = {r.get("chave", "").strip(): r for r in carregar_unicos(raiz).values() if r.get("chave", "").strip()}
    anterior_por_chave = {(l.get("chave", ""), l.get("construto_outcome", ""), normalizar_dominio(l.get("dominio", ""))): l
                          for l in anterior}
    concordancia_token = f"{PREFIXO_CONCORDANCIA}{avaliador_a}+{avaliador_b}"
    linhas, pares, avisos = [], {}, []
    for k in sorted(aplicaveis_a | aplicaveis_b):
        chave, construto, dominio = k
        ra = reg_a.get(k, {"valor": NAO_SE_APLICA, "id_estudo": "", "trecho": "", "pagina": "", "justificativa": ""})
        rb = reg_b.get(k, {"valor": NAO_SE_APLICA, "id_estudo": "", "trecho": "", "pagina": "", "justificativa": ""})
        comp_a, comp_b = rotulo_comparavel(ferramenta, ra["valor"]), rotulo_comparavel(ferramenta, rb["valor"])
        pares.setdefault(dominio, []).append((comp_a, comp_b))
        if dominio == DOMINIO_GERAL and ferramenta in FERRAMENTAS_ALGORITMO:
            continue  # o geral do RoB 2, ROBINS-I e EPOC sai do algoritmo (fase 2); aqui só conta na concordância
        id_estudo = ra["id_estudo"] or rb["id_estudo"]
        if not id_estudo and chave in por_chave:
            reg = por_chave[chave]
            id_estudo = reg.get("id_estudo", "").strip() or esquema.id_estudo_de(reg.get("id_rs", ""))
        concordam = comp_a == comp_b
        linha = {"chave": chave, "id_estudo": id_estudo, "construto_outcome": construto, "ferramenta": ferramenta,
                 "dominio": dominio, "julgamento_a": ra["valor"], "julgamento_b": rb["valor"],
                 "julgamento_consenso": ra["valor"] if concordam else "",
                 "justificativa": _juntar_texto(ra["justificativa"], rb["justificativa"]),
                 "trecho": _juntar_texto(ra["trecho"], rb["trecho"]), "pagina": _juntar_texto(ra["pagina"], rb["pagina"]),
                 "resolvido_por": concordancia_token if concordam else ""}
        velha = anterior_por_chave.get(k)
        if velha and _texto(velha.get("julgamento_consenso")) and _texto(velha.get("resolvido_por")) \
                and not _texto(velha.get("resolvido_por")).lower().startswith(PREFIXO_CONCORDANCIA):
            mesmos = (_texto(velha.get("julgamento_a")) == ra["valor"]
                      and _texto(velha.get("julgamento_b")) == rb["valor"])
            if mesmos:
                for campo in ("julgamento_consenso", "resolvido_por"):
                    linha[campo] = _texto(velha.get(campo))
                if _texto(velha.get("justificativa")):
                    linha["justificativa"] = _texto(velha.get("justificativa"))
            else:
                avisos.append(f"{chave}×{construto or '-'}×{dominio}: A ou B mudou desde a resolução de "
                              f"{velha.get('resolvido_por')}; a resolução antiga foi descartada")
        linhas.append(linha)
    chaves_novas = {(l["chave"], l["construto_outcome"], l["dominio"]) for l in linhas}
    for k, velha in anterior_por_chave.items():
        if k[2] == DOMINIO_GERAL and k not in chaves_novas and ferramenta in FERRAMENTAS_ALGORITMO:
            linhas.append({c: _texto(velha.get(c)) for c in esquema.COLUNAS_ROB_CONSENSO} | {"dominio": DOMINIO_GERAL})
    linhas.sort(key=lambda l: (l["chave"], l["construto_outcome"], l["dominio"] == DOMINIO_GERAL, l["dominio"]))
    return linhas, pares, avisos


# ---------------------------------------------------------------------------
# Fase 2: consenso -> rob_geral
# ---------------------------------------------------------------------------
def calcular_rob_geral(ferramenta, linhas, ignorar=()):
    """(linhas de rob_geral, problemas, avisos, n_sobreposicoes)."""
    grupos = {}
    for l in linhas:
        grupos.setdefault((l["chave"], l["construto_outcome"]), []).append(l)
    saida, problemas, avisos, n_sobre = [], [], [], 0
    ignorar = {normalizar_dominio(d) for d in ignorar}
    for (chave, construto), rows in sorted(grupos.items()):
        rotulo = f"{chave}×{construto or '-'}"
        id_estudo = next((r["id_estudo"] for r in rows if r.get("id_estudo")), "")
        dominios, geral_linhas = [], []
        for r in rows:
            papel = "geral" if r["dominio"] == DOMINIO_GERAL else "dominio"
            valor, _ = normalizar_valor(ferramenta, r["julgamento_consenso"], papel)
            if r["dominio"] == DOMINIO_GERAL:
                geral_linhas.append((r, valor))
            elif valor != NAO_SE_APLICA and r["dominio"] not in ignorar:
                dominios.append((r, valor))
        geral, regra = "", ""
        if ferramenta in FERRAMENTAS_ALGORITMO:
            niveis = [nivel(ferramenta, v) for _, v in dominios if nivel(ferramenta, v)]
            if not niveis:
                problemas.append(f"{rotulo}: nenhum domínio aplicável para o algoritmo")
                continue
            pior = max(niveis)
            geral, regra = GERAL_POR_NIVEL[ferramenta][pior], "pior_dominio"
            no_pior = sum(1 for n in niveis if n == pior)
            if ferramenta == "rob2" and pior == 2 and no_pior >= 2:
                avisos.append(f"{rotulo}: RoB 2 com algumas_preocupacoes em {no_pior} domínios; a ferramenta permite "
                              "julgar alto quando elas reduzem muito a confiança (decida numa linha dominio=geral)")
            if ferramenta == "robins_i" and pior in (2, 3) and no_pior >= 2:
                avisos.append(f"{rotulo}: ROBINS-I com {no_pior} domínios {geral}; o julgamento aditivo "
                              f"({'vários moderados -> grave' if pior == 2 else 'vários graves -> crítico'}) é decisão "
                              "humana numa linha dominio=geral")
            if geral_linhas:
                r, valor = geral_linhas[-1]
                if _texto(r.get("julgamento_consenso")):
                    n_geral = nivel(ferramenta, valor, "geral") if valor and valor != NAO_SE_APLICA else None
                    if n_geral is None:
                        problemas.append(f"{rotulo}: geral {r.get('julgamento_consenso')!r} fora do vocabulário")
                        continue
                    if n_geral < pior:
                        problemas.append(f"{rotulo}: geral {valor} menos grave que o pior domínio ({geral}); a "
                                         "sobreposição só pode agravar o julgamento")
                        continue
                    if not _texto(r.get("justificativa")):
                        problemas.append(f"{rotulo}: sobreposição do geral sem justificativa")
                        continue
                    if n_geral != pior or valor != geral:
                        n_sobre += 1
                        regra = "sobreposicao_humana"
                    geral = valor
        else:
            validos = [(r, v) for r, v in geral_linhas if v and v != NAO_SE_APLICA]
            if not validos:
                problemas.append(f"{rotulo}: sem linha dominio=geral (preocupacao_metodologica) no consenso; "
                                 f"{ferramenta} não tem algoritmo de julgamento geral")
                continue
            geral, regra = validos[-1][1], "consenso_geral"
        usadas = [r for r, _ in dominios] + [r for r, v in geral_linhas if _texto(r.get("julgamento_consenso"))]
        validado = bool(usadas) and all(eh_papel_humano(r.get("resolvido_por")) for r in usadas)
        saida.append({"chave": chave, "id_estudo": id_estudo, "construto_outcome": construto, "ferramenta": ferramenta,
                      "rob_geral": geral, "validado_humano": "1" if validado else "0", "_regra": regra})
    return saida, problemas, avisos, n_sobre


# ---------------------------------------------------------------------------
# Comando
# ---------------------------------------------------------------------------
def _ultimo_evento(raiz, evento, ferramenta):
    for ev in reversed(estado.ler_log(raiz)):
        if ev.get("evento") == evento and (ev.get("dados") or {}).get("ferramenta") == ferramenta:
            return ev
    return None


def _shas(raiz, arquivos):
    return {a: (estado.sha256_arquivo(Path(raiz) / a) if (Path(raiz) / a).is_file() else "") for a in arquivos}


def _mesmos_artefatos(ev, shas):
    if not ev:
        return False
    registrados = {a.get("caminho"): a.get("sha256") for a in ev.get("artefatos") or []}
    return all(registrados.get(c) == s for c, s in shas.items())


def _pendencia(raiz, ferramenta, arquivo, n):
    return sincronizar_pendencia_unica(
        raiz, PENDENCIA_CONSENSO_ROB, ETAPA,
        f"resolver desacordos de risco de viés ({ferramenta}) por domínio: julgamento_consenso e resolvido_por humano",
        n, portao=PORTAO, arquivo=arquivo, ator_id=ATOR,
        motivo_resolvida="todos os desacordos de RoB resolvidos por humano")


def _resumo_conc(conc):
    return {d: {k: c[k] for k in ("n", "concordancia", "kappa", "pabak", "sinalizado")} for d, c in conc.items()}


def cmd_consolidar(args):
    comando = "qualidade consolidar"
    raiz = exigir_raiz(args, comando)
    if raiz is None:
        return 1
    ferramenta = args.ferramenta
    if bool(args.consenso) == bool(args.a or args.b):
        return falhar(comando, "use --a e --b (fase 1) ou --consenso (fase 2), não os dois nem nenhum")
    arq_consenso = esquema.PADRAO_ROB_CONSENSO.format(ferramenta=ferramenta)
    arq_conc = PADRAO_CONCORDANCIA.format(ferramenta=ferramenta)
    avisos = []
    tipo_revisao = (estado.carregar_estado(raiz).get("projeto") or {}).get("tipo_revisao")
    if tipo_revisao in esquema.TIPOS_SEM_ROB:
        avisos.append(f"tipo de revisão {tipo_revisao} dispensa risco de viés no G7; a consolidação é opcional")
    try:
        if args.consenso:
            return _fase_consenso(args, raiz, ferramenta, arq_consenso, arq_conc, avisos)
        return _fase_desacordos(args, raiz, ferramenta, arq_consenso, arq_conc, avisos)
    except ErroEntrada as e:
        return falhar(comando, str(e), ferramenta=ferramenta)
    except ErroDependenciaXlsx as e:
        return falhar(comando, str(e), codigo=3, ferramenta=ferramenta)


def _fase_desacordos(args, raiz, ferramenta, arq_consenso, arq_conc, avisos):
    comando = "qualidade consolidar"
    if not (args.a and args.b):
        raise ErroEntrada("a fase 1 exige --a e --b (as duas avaliações independentes)")
    entradas = []
    for valor in (args.a, args.b):
        p = resolver_caminho(raiz, valor)
        if not p.is_file():
            raise ErroEntrada(f"arquivo não encontrado: {valor}")
        entradas.append(p)
    codebook = _codebook(raiz, ferramenta, resolver_caminho(raiz, args.codebook) if args.codebook else None)
    reg_a, erros_a, prop_a, formato_a = ler_avaliacao(entradas[0], ferramenta, codebook)
    reg_b, erros_b, prop_b, formato_b = ler_avaliacao(entradas[1], ferramenta, codebook)
    if erros_a or erros_b:
        erros = erros_a + erros_b
        raise ErroEntrada(f"{len(erros)} valores inválidos em A/B: " + "; ".join(erros[:15]))
    avaliadores = []
    for nome, declarado, n_prop in (("A", args.avaliador_a, prop_a), ("B", args.avaliador_b, prop_b)):
        papel = _texto(declarado) or nome
        if n_prop:
            avisos.append(f"avaliação {nome} tem {n_prop} julgamentos com prefixo proposta_ (rascunho de IA): conta como IA")
            papel = f"ia_proposta_{nome}"
        elif not eh_papel_humano(papel):
            avisos.append(f"avaliador {nome} sem papel humano declarado (--avaliador-{nome.lower()}, ex.: "
                          f"{esquema.PAPEL_HUMANO_PADRAO}): concordâncias com ele não validam rob_geral")
        avaliadores.append(papel)
    if avaliadores[0] == avaliadores[1] and eh_papel_humano(avaliadores[0]):
        avisos.append(f"A e B com o mesmo papel ({avaliadores[0]}): a avaliação precisa ser independente (MECIR C53)")
    anterior = ler_csv(raiz / arq_consenso)[1] if (raiz / arq_consenso).is_file() else []
    linhas, pares, avisos_montagem = montar_consenso(raiz, ferramenta, reg_a, reg_b, avaliadores[0], avaliadores[1],
                                                     anterior)
    avisos += avisos_montagem
    conc = concordancia_por_dominio(ferramenta, pares)
    sha_antes = _shas(raiz, [arq_consenso, arq_conc])
    escrever_csv(raiz / arq_consenso, esquema.COLUNAS_ROB_CONSENSO, linhas)
    escrever_csv(raiz / arq_conc, COLUNAS_CONCORDANCIA, _linhas_concordancia(ferramenta, conc))
    pendentes = [l for l in linhas if status_linha(ferramenta, l) != "ok"]
    n_desacordos = sum(1 for l in linhas if rotulo_comparavel(ferramenta, l["julgamento_a"])
                       != rotulo_comparavel(ferramenta, l["julgamento_b"]))
    shas = _shas(raiz, [arq_consenso, arq_conc])
    reexecucao = shas == sha_antes and _mesmos_artefatos(_ultimo_evento(raiz, "fila_gerada", ferramenta), shas)
    if not reexecucao:
        estado.registrar_evento(
            raiz, "fila_gerada", ETAPA, "script", ATOR,
            dados={"fila": PENDENCIA_CONSENSO_ROB, "ferramenta": ferramenta, "arquivo": arq_consenso,
                   "entradas": [relativo(raiz, p) for p in entradas], "formatos": [formato_a, formato_b],
                   "avaliadores": {"A": avaliadores[0], "B": avaliadores[1]}, "n_linhas": len(linhas),
                   "n_desacordos": n_desacordos, "n_pendentes": len(pendentes), "concordancia": _resumo_conc(conc)},
            artefatos=[arq_consenso, arq_conc])
    pendencia = _pendencia(raiz, ferramenta, arq_consenso, len(pendentes))
    proxima = (f"rs.py qualidade consolidar --ferramenta {ferramenta} --consenso {arq_consenso}" if not pendentes else
               f"resolver {len(pendentes)} desacordo(s) em {arq_consenso} (julgamento_consenso, justificativa e "
               f"resolvido_por humano, ex.: {esquema.PAPEL_HUMANO_PADRAO}); depois rs.py qualidade consolidar "
               f"--ferramenta {ferramenta} --consenso {arq_consenso}")
    estado.resumo({"comando": comando, "ok": True, "fase": "desacordos", "ferramenta": ferramenta,
                   "arquivos": [arq_consenso, arq_conc], "n_resultados": len({(l["chave"], l["construto_outcome"])
                                                                            for l in linhas}),
                   "n_linhas": len(linhas), "n_desacordos": n_desacordos, "n_pendentes": len(pendentes),
                   "concordancia": _resumo_conc(conc),
                   "dominios_sinalizados": [d for d, c in conc.items() if c["sinalizado"]],
                   "reexecucao": reexecucao, "pendencia": pendencia, "avisos": avisos, "proxima_acao": proxima})
    return 0


def _fase_consenso(args, raiz, ferramenta, arq_consenso, arq_conc, avisos):
    comando = "qualidade consolidar"
    caminho = resolver_caminho(raiz, args.consenso)
    if not caminho.is_file():
        raise ErroEntrada(f"arquivo não encontrado: {args.consenso}")
    colunas, linhas = ler_tabela(caminho)
    faltam = [c for c in esquema.COLUNAS_ROB_CONSENSO if c not in colunas]
    if faltam:
        raise ErroEntrada(f"{caminho.name}: faltam colunas {faltam} (gere o arquivo com a fase 1: --a e --b)")
    por = _texto(args.por)
    if por and not eh_papel_humano(por):
        raise ErroEntrada(f"--por {por!r} não é papel humano (ex.: {esquema.PAPEL_HUMANO_PADRAO})")
    outras = sorted({l["ferramenta"] for l in linhas if _texto(l.get("ferramenta")) not in ("", ferramenta)})
    if outras:
        raise ErroEntrada(f"{caminho.name}: linhas de outra ferramenta ({', '.join(outras)}); use --ferramenta certa")
    preenchidas = 0
    for l in linhas:
        for c in esquema.COLUNAS_ROB_CONSENSO:
            l[c] = _texto(l.get(c))
        l["ferramenta"] = ferramenta
        l["dominio"] = normalizar_dominio(l["dominio"])
        if por and l["julgamento_consenso"] and not l["resolvido_por"]:
            l["resolvido_por"] = por
            preenchidas += 1
    problemas = [f"{l['chave']}×{l['construto_outcome'] or '-'}×{l['dominio']}: {s}"
                 for l in linhas for s in [status_linha(ferramenta, l)] if s != "ok"]
    rel_consenso = relativo(raiz, caminho)
    if not problemas:
        geral_linhas, problemas_geral, avisos_geral, n_sobre = calcular_rob_geral(
            ferramenta, linhas, [d.strip() for d in (args.ignorar_no_geral or "").split(",") if d.strip()])
        problemas += problemas_geral
        avisos += avisos_geral
    if problemas:
        pendencia = _pendencia(raiz, ferramenta, rel_consenso, len(problemas))
        estado.resumo({"comando": comando, "ok": False, "fase": "consenso", "ferramenta": ferramenta,
                       "erro": f"{len(problemas)} linhas do consenso sem resolução válida", "problemas": problemas[:30],
                       "n_problemas": len(problemas), "pendencia": pendencia, "avisos": avisos,
                       "proxima_acao": f"preencher julgamento_consenso, justificativa e resolvido_por humano em "
                                       f"{rel_consenso} (ou rodar com --por {esquema.PAPEL_HUMANO_PADRAO} para "
                                       "declarar quem resolveu) e repetir o comando"})
        return 2
    if preenchidas:
        escrever_csv(caminho, esquema.COLUNAS_ROB_CONSENSO, linhas)
    pares = {}
    for l in linhas:
        if l["julgamento_a"] or l["julgamento_b"]:
            pares.setdefault(l["dominio"], []).append((rotulo_comparavel(ferramenta, l["julgamento_a"] or NAO_SE_APLICA),
                                                       rotulo_comparavel(ferramenta, l["julgamento_b"] or NAO_SE_APLICA)))
    conc = concordancia_por_dominio(ferramenta, pares)
    escrever_csv(raiz / arq_conc, COLUNAS_CONCORDANCIA, _linhas_concordancia(ferramenta, conc))
    existentes = ler_csv(raiz / esquema.ARQ_ROB_GERAL)[1] if (raiz / esquema.ARQ_ROB_GERAL).is_file() else []
    mantidas = [l for l in existentes if _texto(l.get("ferramenta")) != ferramenta]
    todas = sorted(mantidas + geral_linhas, key=lambda l: (l["ferramenta"], l["chave"], l["construto_outcome"]))
    escrever_csv(raiz / esquema.ARQ_ROB_GERAL, esquema.COLUNAS_ROB_GERAL, todas)
    n_validados = sum(1 for l in geral_linhas if l["validado_humano"] == "1")
    distribuicao = dict(Counter(l["rob_geral"] for l in geral_linhas))
    artefatos = [rel_consenso, esquema.ARQ_ROB_GERAL, arq_conc]
    shas = _shas(raiz, artefatos)
    reexecucao = _mesmos_artefatos(_ultimo_evento(raiz, "rob_consolidado", ferramenta), shas)
    if not reexecucao:
        estado.registrar_evento(
            raiz, "rob_consolidado", ETAPA, "script", ATOR,
            dados={"ferramenta": ferramenta, "arquivo_consenso": rel_consenso, "arquivo_geral": esquema.ARQ_ROB_GERAL,
                   "arquivo_concordancia": arq_conc, "n_resultados": len(geral_linhas), "n_linhas_consenso": len(linhas),
                   "n_desacordos": sum(1 for l in linhas if l["julgamento_a"] and l["julgamento_b"]
                                       and rotulo_comparavel(ferramenta, l["julgamento_a"])
                                       != rotulo_comparavel(ferramenta, l["julgamento_b"])),
                   "n_validados_humano": n_validados, "todos_validados_humano": n_validados == len(geral_linhas),
                   "rob_geral": distribuicao, "n_sobreposicoes": n_sobre,
                   "regra_geral": sorted({l["_regra"] for l in geral_linhas}),
                   "ignorar_no_geral": args.ignorar_no_geral or "", "concordancia": _resumo_conc(conc),
                   "n_dominios_sinalizados": sum(1 for c in conc.values() if c["sinalizado"]),
                   "resolvido_por": sorted({l["resolvido_por"] for l in linhas if l["resolvido_por"]}),
                   "avisos": avisos[:20]},
            artefatos=artefatos)
    pendencia = _pendencia(raiz, ferramenta, rel_consenso, 0)
    if n_validados < len(geral_linhas):
        avisos.append(f"{len(geral_linhas) - n_validados} resultados com validado_humano = 0 (concordância só entre "
                      "avaliadores não humanos): o G7 exige julgamento humano")
    estado.resumo({"comando": comando, "ok": True, "fase": "consenso", "ferramenta": ferramenta,
                   "arquivos": artefatos, "n_resultados": len(geral_linhas), "rob_geral": distribuicao,
                   "n_validados_humano": n_validados, "n_sobreposicoes": n_sobre, "concordancia": _resumo_conc(conc),
                   "n_resolvido_por_preenchido": preenchidas, "reexecucao": reexecucao, "pendencia": pendencia,
                   "avisos": avisos,
                   "proxima_acao": f"juntar rob_geral de {esquema.ARQ_ROB_GERAL} aos efeitos (coluna extra rob_geral, "
                                   "por chave e construto_outcome) e rodar analise efeitos, meta e swim"})
    return 0


def registrar(subparsers):
    existente = subparsers._name_parser_map.get("qualidade")
    if existente is None:
        p = subparsers.add_parser("qualidade", help="risco de viés: concordância de A e B, consenso e rob_geral",
                                  description="risco de viés: concordância de A e B, consenso e rob_geral")
        p.set_defaults(func=lambda a, _p=p: (_p.print_help(), 1)[1])
        sub = p.add_subparsers(dest="acao_qualidade", metavar="<ação>")
    else:
        sub = next(a for a in existente._actions if a.__class__.__name__ == "_SubParsersAction")
    q = sub.add_parser("consolidar", help="fase 1 (--a/--b): concordância e fila de desacordos; fase 2 (--consenso): "
                                          "valida o consenso humano e grava rob_geral")
    q.add_argument("--ferramenta", required=True, choices=FERRAMENTAS)
    q.add_argument("--a", default=None, help="avaliação independente A (CSV longo, largo ou master; .xlsx aceito)")
    q.add_argument("--b", default=None, help="avaliação independente B (mesmo formato de A)")
    q.add_argument("--avaliador-a", default=None, help="papel de quem fez A (ex.: revisor_humano_1)")
    q.add_argument("--avaliador-b", default=None, help="papel de quem fez B (ex.: revisor_humano_2)")
    q.add_argument("--codebook", default=None,
                   help="codebook da ferramenta para ler masters de EPOC e checklists "
                        "(padrão 00-protocolo/codebook_v0_<ferramenta>.csv ou o da skill)")
    q.add_argument("--consenso", default=None, help="arquivo de consenso resolvido (fase 2)")
    q.add_argument("--por", default=None,
                   help=f"papel humano que resolveu linhas com resolvido_por vazio (ex.: {esquema.PAPEL_HUMANO_PADRAO})")
    q.add_argument("--ignorar-no-geral", default=None,
                   help="domínios fora do algoritmo do geral, declarados no protocolo (ex.: EPOC cg_sequencia_aleatoria)")
    q.set_defaults(func=cmd_consolidar)
