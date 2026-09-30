"""Caixa de ferramentas (formato OQF) montada com regras explícitas e fontes por célula.

USO
    python3 rs.py caixa [--master fichamentos_master.csv] [--efeitos 06-analise/meta_resumo.json] \
        [--swim 06-analise/swim_resumo.json] [--certeza 06-analise/certeza.csv] \
        [--mapa assets/mapas/caixa_ferramentas_mapa.csv] [--delta 0.1] \
        [--faixas "<faixa>:<limite>,... (faixas do campo fixadas no protocolo, na métrica g)"] [--k-min 3]

Célula = família de intervenção × construto de outcome × classe de desenho, com uma
linha-resumo de painel por família × construto (ver "Painel"). O comando NÃO julga: só
aplica as regras da versão `REGRA_VERSAO` (references/07b-sintese-qualitativa-integracao.md;
Apêndice D da base de conhecimento) aos resultados da síntese e aos juízos de certeza feitos
por humanos, e registra de onde veio cada rótulo. As faixas de magnitude vêm do protocolo,
nunca das convenções genéricas de Cohen.

Classe de desenho (randomizado × não randomizado)
    meta.R e swim.R separam randomizados e não randomizados por padrão (nunca agregar os
    dois juntos) e gravam `classe_desenho` em cada grupo (também como
    sufixo do rótulo "outcome | nao_randomizado"). A caixa usa a mesma separação: cada
    classe presente na síntese vira uma linha de efeito própria, com a coluna
    `classe_desenho`; nenhum grupo sobrescreve outro. Síntese rodada com
    --separar-desenho=nao gera célula com `classe_desenho` vazia.
    Certeza: uma linha de certeza.csv com `classe_desenho` preenchida vale só para essa
    classe; sem a coluna (ou vazia), vale para todas as classes da célula, com aviso,
    porque o GRADE parte de certeza alta para ECR e baixa para não randomizados e o
    juízo deveria ser feito por classe. Mais de uma linha de efeito para a mesma célula
    e classe segue a seção "Subcélulas": nenhuma linha é descartada em silêncio.
    Família: um grupo da síntese sem família (agrupado só por construto_outcome) herda a
    família quando ela é única entre as linhas de efeito de certeza.csv daquele outcome
    (ou, sem elas, a única família de certeza.csv e do master); com mais de uma, a
    célula fica sem família e o aviso pede --grupo=familia_intervencao,construto_outcome.

Entradas
    meta_resumo.json   saída do `scripts/R/meta.R` (lista de grupos ou {"grupos": [...]});
                       aceita nomes do metafor (b, ci.lb, ci.ub, pi.lb, pi.ub, k) e em
                       português (estimativa, ci_lo, ci_hi, pi_lo, pi_hi). Estimativas já
                       alinhadas: positivo = benéfico (`sinal_alinhado` do efeitos.R).
    swim_resumo.json   saída do `scripts/R/swim.R` (teste de sinal por grupo:
                       n_estudos, n_beneficos, n_danosos, p_sinal, estudos).
    certeza.csv        juízos humanos: familia_intervencao, construto_outcome, dimensao
                       (efeito|implementacao|mecanismo|moderador|percepcao|custo), certeza
                       (alta|moderada|baixa|muito_baixa), abordagem (GRADE|CERQual),
                       enunciado, estudos, justificativa, delta, moderador_explica,
                       classe_desenho (opcional: randomizado|nao_randomizado),
                       explica_heterogeneidade (opcional, linhas de moderador/mecanismo:
                       sim quando o achado explica a heterogeneidade do efeito da célula),
                       validado_humano (opcional).
    fichamentos_master.csv + mapa: variáveis do master que dão família, outcome,
                       critérios de implementação, achados e risco de viés.

Regras de rótulo do efeito (versão caixa-3, nesta ordem)
    sem certeza (GRADE) na célula ........ Pendente (nunca se inventa certeza)
    certeza muito baixa .................. Inconclusivo (antes de Misto)
    Misto ................................ k >= 5 (τ² e IP interpretáveis), δ declarado,
                                           IP cobre benefício e dano além de ±δ E uma linha
                                           de certeza.csv (dimensao moderador ou mecanismo,
                                           mesma família, outcome da célula ou vazio,
                                           explica_heterogeneidade = sim) com enunciado e
                                           confiança CERQual >= baixa
    heterogeneidade alegada sem sustentação  Inconclusivo (`inconclusivo_misto_nao_sustentado`):
                                           a célula declara explicação (moderador_explica ou
                                           achado marcado) e o IP cruza zero ou ±δ, mas falta
                                           k >= 5, δ ou o achado com CERQual >= baixa; a
                                           justificativa lista o que falta
    Positivo / Negativo (com MA, k >= 3) . IC exclui 0 no sentido benéfico/danoso e
                                           certeza >= baixa
    Positivo / Negativo (sem MA) ......... teste de sinal p < 0,05, >= 5 estudos,
                                           >= 70% na direção, não só risco alto, certeza >= baixa
    Nulo ................................. δ declarado, IC inteiro em [-δ, +δ] e certeza >= moderada
    Inconclusivo ......................... todos os demais casos
    Misto é avaliado antes de Positivo/Negativo porque, quando a heterogeneidade é
    explicada, a média não descreve o efeito esperado num contexto concreto. Quando a
    explicação é alegada mas não sustentada, a média também não pode ser lida como efeito
    típico sem ressalva: por isso Inconclusivo, e não Positivo.
    Força: alta = forte, moderada = moderada, baixa = fraca, muito baixa = insuficiente.
    Testes combinados (Fisher, Stouffer, Winer, Cooper) são ignorados para rótulo,
    mesmo que apareçam nos JSONs.

Painel (linha `dimensao = efeito_painel`, uma por família × construto)
    Resume os corpos de evidência da célula (uma linha de efeito por classe de desenho) para
    o painel e o policy brief:
    - algum corpo pendente ............... Pendente (`painel_pendente`)
    - um só corpo ........................ o rótulo dele (`painel_corpo_unico`)
    - corpos com o mesmo rótulo .......... esse rótulo, com a maior certeza (`painel_mesmo_rotulo`)
    - rótulos diferentes ................. o rótulo do corpo de maior certeza, com o outro anotado
                                           na justificativa (`painel_maior_certeza`)
    - empate de certeza, rótulos diferentes  Inconclusivo por heterogeneidade por desenho
                                           (`painel_empate_desenho`)
    Status `rascunho` se algum corpo estiver em rascunho. As linhas de painel entram em
    `n_pendentes` como qualquer outra linha não definida.

Subcélulas (regra de agregação `REGRA_AGREGACAO` = subcelulas-1)
    certeza.csv pode ser mais fino que a célula da caixa: colunas fora do contrato
    (`COLUNAS_CERTEZA`), como comparador_tipo ou celula_alvo, separam juízos GRADE dentro
    da mesma família × construto × classe. Até a caixa-3 original valia só a última linha,
    e as demais sumiam sem aviso (uma certeza moderada podia ficar escondida atrás de uma
    muito baixa). Agora, para as linhas de efeito da célula:
    - uma linha ......................... o caminho de sempre (saída idêntica à anterior);
    - várias, sem coluna que as distinga  duplicatas: vale a última, como antes, com aviso
                                          que lista as linhas;
    - várias, que diferem em colunas fora do contrato (`colunas_de_subcelula`): cada linha
      passa sozinha pelas regras caixa-3 (δ, moderador_explica, risco alto, achado
      explicativo, validado_humano, ajuste do Misto) e `agregar_subcelulas` combina as
      subcélulas como o painel combina os corpos:
      alguma subcélula pendente ......... Pendente (`subcelulas_pendente`)
      todas com o mesmo rótulo .......... esse rótulo, com a maior certeza (`subcelulas_mesmo_rotulo`)
      rótulos diferentes ................ o rótulo da subcélula de maior certeza, com as demais
                                          anotadas na justificativa (`subcelulas_maior_certeza`)
      empate na maior certeza com rótulos diferentes  Inconclusivo (`subcelulas_empate`)
    Status: pendente se alguma subcélula estiver pendente, senão rascunho se alguma estiver
    em rascunho, senão definido. Certeza e força vêm da subcélula escolhida (a primeira do
    arquivo no empate); `estudos` é a união (síntese e subcélulas); `fontes` lista todas as
    linhas de certeza.csv; a justificativa começa por "agregação subcelulas-1 (<regra>)" e
    descreve cada subcélula (linha, valores que a distinguem, rótulo, certeza, δ, estudos e
    a justificativa das regras caixa-3). Vale a maior certeza pela mesma razão do painel:
    um juízo menos certo não pode esconder um mais certo, e o que discorda fica à vista; no
    empate não há como escolher a direção, e a célula não afirma nenhuma. As subcélulas
    continuam no certeza.csv e no relatório.
    Implementação com mais de uma linha para a família: vale a de maior confiança CERQual
    (a última no empate, a regra anterior), a linha sai rascunho se alguma não estiver
    validada, e todas vão para `fontes` e para a justificativa, com aviso.

Implementação (por família): 1 ponto por critério do mapa (> 2 componentes; > 1
nível de governo ou múltiplos atores; nova infraestrutura/pessoal; barreiras de
fidelidade/adoção em >= 2 estudos; longo tempo até o efeito) → 0-1 Simples,
2-3 Moderada, >= 4 Complexa; sem confiança CERQual o rótulo fica Pendente (o
proposto aparece em `rotulo_proposto`).

Mecanismo, moderador, percepção e custo: um enunciado por linha de certeza.csv
com a confiança CERQual; estudos com o achado no master mas sem enunciado viram
linha pendente; custo sem nenhum dado vira "Não reportado".

Validação humana: com a coluna `validado_humano` em certeza.csv, toda linha definida
(efeito, implementação, mecanismo, moderador, percepção, custo) cuja linha de certeza
não esteja marcada (sim/1/true) sai com status `rascunho`. Sem a coluna, nada muda.
Códigos de ausência do fichamento (999, NA_secao, "não", NA) não contam como achado.

Saída: `06-analise/caixa_ferramentas.csv` (toda linha com `fontes` e `assinatura`
sha256) e `06-analise/caixa_ferramentas.md`, marcado RASCUNHO NÃO VALIDADO se houver
célula pendente ou pendências abertas no projeto.

Evento `caixa_gerada` (lido por `rs.py status`): dados = {regra_versao, n_linhas,
rotulos_efeito, rotulos_painel, n_pendentes (linhas com status_rotulo != definido, isto é,
pendente ou rascunho), n_rascunho, rascunho, regra_agregacao, n_celulas_agregadas (linhas
de efeito com regra subcelulas_*)}. Os dois últimos campos são acréscimos: quem lê o evento
só pelos anteriores não muda.
"""

import json
from pathlib import Path

from . import esquema, estado, normalizar
from .handoff import (DIR_ASSETS, escrever_csv, escrever_texto, exigir_raiz, falhar, ler_csv, relativo,
                      resolver_caminho, sincronizar_pendencia_unica)

ATOR = "rs.py caixa"
REGRA_VERSAO = "caixa-3"
REGRA_AGREGACAO = "subcelulas-1"  # várias linhas de certeza numa célula (seção "Subcélulas" da docstring)
ARQ_CAIXA = esquema.ARQ_CAIXA
ARQ_CAIXA_MD = "06-analise/caixa_ferramentas.md"
MAPA_PADRAO = DIR_ASSETS / "mapas" / "caixa_ferramentas_mapa.csv"
REF_REGRAS_CAIXA = "references/07b-sintese-qualitativa-integracao.md; Apêndice D da base de conhecimento"

NIVEL_CERTEZA = {"muito_baixa": 1, "baixa": 2, "moderada": 3, "alta": 4}
FORCA = {"alta": "forte", "moderada": "moderada", "baixa": "fraca", "muito_baixa": "insuficiente"}
DIMENSOES_ACHADO = ["mecanismo", "moderador", "percepcao", "custo"]
DIMENSOES_EXPLICATIVAS = ("moderador", "mecanismo")  # achados que podem explicar a heterogeneidade (Misto)
DIMENSAO_PAINEL = "efeito_painel"
K_MISTO_MIN = 5  # τ² e intervalo de predição só são interpretáveis com k >= 5
_MARCAS_SIM = {"sim", "s", "1", "true", "yes", "y", "x"}
TESTES_COMBINADOS = ("stouffer", "fisher", "winer", "cooper", "combinad")
COLUNAS_CAIXA = [
    "celula_id", "familia_intervencao", "construto_outcome", "classe_desenho", "dimensao", "rotulo", "rotulo_proposto",
    "status_rotulo", "forca", "certeza", "abordagem_certeza", "escala", "estimativa", "ci_lo", "ci_hi", "pi_lo",
    "pi_hi", "k", "n_estudos", "pontos_implementacao", "criterios_implementacao", "enunciado", "regra_aplicada",
    "regra_versao", "estudos", "fontes", "justificativa", "assinatura",
]
# Colunas do contrato de certeza.csv (seção "Entradas"). Qualquer outra coluna, como comparador_tipo ou
# celula_alvo, é do projeto: quando ela separa as linhas de uma célula, as linhas são subcélulas.
COLUNAS_CERTEZA = [
    "familia_intervencao", "construto_outcome", "dimensao", "classe_desenho", "certeza", "abordagem", "enunciado",
    "estudos", "justificativa", "delta", "moderador_explica", "explica_heterogeneidade", "validado_humano",
]
_SEPARADORES_GRUPO = (" :: ", " | ", " × ", "::", "|")
CLASSES_DESENHO = ("randomizado", "nao_randomizado", "desenho_nao_informado")  # classe_desenho() de scripts/R/_cli.R
_ALIASES_CLASSE = {"rct": "randomizado", "ecr": "randomizado", "randomizados": "randomizado",
                   "nao_randomizados": "nao_randomizado", "nrs": "nao_randomizado", "nrsi": "nao_randomizado"}


# ---------------------------------------------------------------------------
# Leitura tolerante dos resumos do R
# ---------------------------------------------------------------------------
def _escalar(v):
    while isinstance(v, list) and len(v) == 1:  # jsonlite sem auto_unbox
        v = v[0]
    return None if isinstance(v, (dict, list)) else v


def _num(v):
    v = _escalar(v)
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        x = float(str(v).replace(",", "."))
    except ValueError:
        return None
    return None if x != x else x


def _valor(grupo, aliases, blocos=("modelo", "principal", "reml", "resultado", "meta", "efeito", "sinal")):
    for a in aliases:
        if a in grupo and _escalar(grupo[a]) is not None:
            return _escalar(grupo[a])
    for b in blocos:
        sub = grupo.get(b)
        if isinstance(sub, dict):
            for a in aliases:
                if a in sub and _escalar(sub[a]) is not None:
                    return _escalar(sub[a])
    return None


def _lista(v):
    if v is None:
        return []
    if isinstance(v, list):
        return [str(_escalar(x)) for x in v if _escalar(x) not in (None, "")]
    return [s.strip() for s in str(v).replace(";", "|").split("|") if s.strip()]


def _dobrar(s):
    return normalizar.ascii_fold(s).lower().strip()


def _grupos(dados):
    if isinstance(dados, dict):
        for k in ("grupos", "resultados", "celulas", "groups"):
            if k in dados:
                dados = dados[k]
                break
        else:
            chaves_escalares = {"k", "b", "estimativa", "grupo", "construto_outcome", "n_estudos", "p_sinal"}
            if chaves_escalares & set(dados) or "modelo" in dados:
                return [dados]
            return [dict(v, grupo=v.get("grupo", k)) for k, v in dados.items() if isinstance(v, dict)]
    if isinstance(dados, dict):
        return [dict(v, grupo=v.get("grupo", k)) for k, v in dados.items() if isinstance(v, dict)]
    return [g for g in (dados or []) if isinstance(g, dict)]


def classe_desenho(valor):
    """'randomizado' | 'nao_randomizado' | 'desenho_nao_informado' | '' (sem classe ou valor desconhecido)."""
    s = _dobrar(valor).replace("-", "_").replace(" ", "_")
    s = _ALIASES_CLASSE.get(s, s)
    return s if s in CLASSES_DESENHO else ""


def _celula_do_grupo(g):
    """(familia, outcome, classe_desenho) de um grupo de meta.R/swim.R (ou JSON equivalente)."""
    familia = _valor(g, ["familia_intervencao", "familia", "intervencao"])
    outcome = _valor(g, ["construto_outcome", "outcome", "desfecho"])
    classe = classe_desenho(_valor(g, ["classe_desenho"]) or "")
    nome = _valor(g, ["grupo", "group", "nome"])
    if nome is not None:
        # rótulo de _cli.R::rotulo_grupo: "<colunas do grupo> | <classe de desenho>"
        partes = str(nome).split(" | ")
        if len(partes) > 1 and classe_desenho(partes[-1]):
            classe = classe or classe_desenho(partes[-1])
            nome = " | ".join(partes[:-1])
    if outcome is None and nome is not None:
        for sep in _SEPARADORES_GRUPO:
            if sep in str(nome):
                a, b = str(nome).split(sep, 1)
                return (familia or a).strip(), b.strip(), classe
        outcome = nome
    return str(familia or "").strip(), str(outcome or "").strip(), classe


def _guardar(saida, chave, item, nome_arquivo, avisos):
    """Guarda o grupo na célula sem sobrescrever: dois grupos na mesma célula geram aviso."""
    if chave in saida:
        anterior = saida[chave]
        avisos.append(f"{nome_arquivo}: grupos {anterior['indice']} e {item['indice']} caem na mesma célula "
                      f"{chave[0] or '*'} × {chave[1] or '*'} [{chave[2] or 'sem classe'}]; mantido o grupo "
                      f"{anterior['indice']}")
        return
    saida[chave] = item


def _usa_teste_combinado(g):
    metodo = _dobrar(_valor(g, ["metodo", "method", "teste"]) or "")
    return any(t in metodo for t in TESTES_COMBINADOS)


def ler_meta(caminho, avisos):
    """{(familia, outcome, classe_desenho): dict} a partir do meta_resumo.json (chaves dobradas)."""
    if not caminho:
        return {}
    saida = {}
    for i, g in enumerate(_grupos(json.loads(Path(caminho).read_text(encoding="utf-8")))):
        familia, outcome, classe = _celula_do_grupo(g)
        if _usa_teste_combinado(g):
            avisos.append(f"grupo {i} de {Path(caminho).name} usa teste combinado: ignorado para rótulo")
            continue
        item = {
            "familia": familia, "outcome": outcome, "classe": classe, "indice": i,
            "estimativa": _num(_valor(g, ["estimativa", "b", "beta", "yi", "g", "estimate", "pooled"])),
            "ci_lo": _num(_valor(g, ["ci_lo", "ci.lb", "ci_lb", "ic_inf", "ic_lo", "lower", "ci_inf"])),
            "ci_hi": _num(_valor(g, ["ci_hi", "ci.ub", "ci_ub", "ic_sup", "ic_hi", "upper", "ci_sup"])),
            "pi_lo": _num(_valor(g, ["pi_lo", "pi.lb", "pi_lb", "ip_inf", "cr.lb", "cr_lb", "pred_lo"])),
            "pi_hi": _num(_valor(g, ["pi_hi", "pi.ub", "pi_ub", "ip_sup", "cr.ub", "cr_ub", "pred_hi"])),
            "k": _num(_valor(g, ["k", "k_estudos", "n_estudos"])),
            "tau2_interpretavel": _valor(g, ["tau2_interpretavel"]),
            "estudos": _lista(g.get("estudos") or g.get("ids_estudo") or g.get("chaves")),
            "alinhado": _valor(g, ["direcao_alinhada", "sinal_alinhado"]),
            "fonte": f"{Path(caminho).name}#grupos[{i}]",
        }
        _guardar(saida, (_dobrar(familia), _dobrar(outcome), classe), item, Path(caminho).name, avisos)
    return saida


def ler_swim(caminho, avisos):
    """{(familia, outcome, classe_desenho): dict} a partir do swim_resumo.json (só teste de sinal)."""
    if not caminho:
        return {}
    saida = {}
    for i, g in enumerate(_grupos(json.loads(Path(caminho).read_text(encoding="utf-8")))):
        familia, outcome, classe = _celula_do_grupo(g)
        if _usa_teste_combinado(g):
            avisos.append(f"grupo {i} de {Path(caminho).name} usa teste combinado: ignorado para rótulo")
            continue
        n = _num(_valor(g, ["n_estudos", "k", "n"]))
        benef = _num(_valor(g, ["n_beneficos", "beneficos", "n_positivos"]))
        danos = _num(_valor(g, ["n_danosos", "danosos", "n_negativos"]))
        prop = _num(_valor(g, ["proporcao_benefica", "prop_benefica", "proporcao"]))
        if prop is None and benef is not None and n:
            prop = benef / n
        prop_dano = (danos / n) if (danos is not None and n) else (None if prop is None else 1 - prop)
        item = {
            "familia": familia, "outcome": outcome, "classe": classe, "indice": i, "n": n,
            "prop_benefica": prop, "prop_danosa": prop_dano,
            "p": _num(_valor(g, ["p_sinal", "p_binomial", "p", "p_valor"])),
            "so_risco_alto": _valor(g, ["so_risco_alto", "apenas_risco_alto"]),
            "estudos": _lista(g.get("estudos") or g.get("ids_estudo") or g.get("chaves")),
            "fonte": f"{Path(caminho).name}#grupos[{i}]",
        }
        _guardar(saida, (_dobrar(familia), _dobrar(outcome), classe), item, Path(caminho).name, avisos)
    return saida


def herdar_familia(resumos, certezas, familias_master, avisos):
    """Dá a família única declarada aos grupos da síntese agrupados só por outcome (ver docstring)."""
    efeito = [c for c in certezas if c["_dim"] == "efeito" and normalizar.texto(c.get("familia_intervencao"))]
    gerais = {_dobrar(c.get("familia_intervencao")): normalizar.texto(c.get("familia_intervencao"))
              for c in certezas if normalizar.texto(c.get("familia_intervencao"))}
    gerais.update({_dobrar(f): f for f in familias_master if normalizar.texto(f)})
    for nome_arquivo, resumo in resumos:
        for chave in [k for k in resumo if not k[0]]:
            item = resumo[chave]
            por_outcome = {_dobrar(c.get("familia_intervencao")): normalizar.texto(c.get("familia_intervencao"))
                           for c in efeito if _dobrar(c.get("construto_outcome")) == chave[1]}
            candidatas = por_outcome or gerais
            if len(candidatas) != 1:
                if candidatas:
                    avisos.append(f"{nome_arquivo}: grupo {item['indice']} ({item['outcome'] or '*'}) sem família e "
                                  f"{len(candidatas)} famílias declaradas; rode a síntese com "
                                  "--grupo=familia_intervencao,construto_outcome")
                continue
            familia = next(iter(candidatas.values()))
            nova = (_dobrar(familia), chave[1], chave[2])
            del resumo[chave]
            item["familia"] = familia
            avisos.append(f"{nome_arquivo}: grupo {item['indice']} ({item['outcome'] or '*'}) sem família herdou "
                          f"'{familia}', a única declarada")
            _guardar(resumo, nova, item, nome_arquivo, avisos)


def normalizar_certeza(valor):
    s = _dobrar(valor).replace("-", " ").replace("_", " ")
    s = " ".join(s.split())
    mapa = {"alta": "alta", "high": "alta", "moderada": "moderada", "moderate": "moderada", "media": "moderada",
            "baixa": "baixa", "low": "baixa", "muito baixa": "muito_baixa", "very low": "muito_baixa"}
    return mapa.get(s, "")


def _primeiro_token(valor):
    s = _dobrar(valor)
    for sep in (" ", "-", ",", ";", ":", ".", "—"):
        s = s.split(sep)[0]
    return s


# Códigos de ausência do fichamento: 999 (ausente), NA_secao (seção não se aplica), "não", NA.
TOKENS_AUSENTES = {"999", "nao", "na", "na_secao"}


def _validado(linha_certeza):
    """True/False conforme `validado_humano`; None quando a coluna não existe no certeza.csv.

    Vale para todas as dimensões (efeito, implementação e achados): juízos de certeza,
    CERQual e enunciados são humanos, então uma coluna presente e não marcada
    rebaixa a linha a rascunho. Sem a coluna, o comportamento anterior é mantido.
    """
    if "validado_humano" not in linha_certeza:
        return None
    return _dobrar(linha_certeza.get("validado_humano")) in {"sim", "s", "1", "true"}


def _status_validado(status, linha_certeza):
    return "rascunho" if status == "definido" and _validado(linha_certeza) is False else status


# ---------------------------------------------------------------------------
# Regras
# ---------------------------------------------------------------------------
def _requisitos_misto(meta, delta, achado_explicativo):
    """Lista do que falta para sustentar Misto (vazia = sustentado). Ver docstring do módulo."""
    faltas = []
    k = meta.get("k") or 0
    if k < K_MISTO_MIN:
        faltas.append(f"k = {k:g} < {K_MISTO_MIN}: τ² e intervalo de predição não são interpretáveis")
    elif meta.get("tau2_interpretavel") is False:
        faltas.append("meta-análise marca tau2_interpretavel = false")
    if not delta:
        faltas.append("δ não declarado: 'benefício e dano relevantes' exige δ fixado a priori")
    if not achado_explicativo:
        faltas.append("nenhuma linha de moderador ou mecanismo em certeza.csv com explica_heterogeneidade = sim "
                      "para a célula")
    else:
        conf = normalizar_certeza(achado_explicativo.get("certeza"))
        if not normalizar.texto(achado_explicativo.get("enunciado")):
            faltas.append(f"achado explicativo sem enunciado ({achado_explicativo.get('fonte', 'certeza.csv')})")
        elif NIVEL_CERTEZA.get(conf, 0) < NIVEL_CERTEZA["baixa"]:
            faltas.append(f"achado explicativo com confiança CERQual {conf or 'ausente'} (exige >= baixa; "
                          f"{achado_explicativo.get('fonte', 'certeza.csv')})")
    return faltas


def rotular_efeito(meta, swim, certeza, delta=None, moderador_explica=False, k_min=3, so_risco_alto=None,
                   achado_explicativo=None):
    """Aplica as regras da versão caixa-3 a uma célula. Devolve dict com rotulo, regra e justificativa.

    `achado_explicativo`: dict {certeza (CERQual), enunciado, fonte} da linha de moderador ou mecanismo
    de certeza.csv que explica a heterogeneidade da célula, ou None. `moderador_explica` (da linha de
    efeito) só declara que há explicação: sozinho não sustenta Misto.
    """
    cert = normalizar_certeza(certeza)
    if not cert:
        return {"rotulo": "Pendente", "rotulo_proposto": "", "status": "pendente", "regra": "sem_certeza",
                "forca": "", "justificativa": "sem juízo de certeza (GRADE) para a célula: rótulo não é atribuído"}
    nivel = NIVEL_CERTEZA[cert]
    base = {"forca": FORCA[cert], "status": "definido"}
    if meta and meta.get("alinhado") is False:
        return {**base, "rotulo": "Pendente", "rotulo_proposto": "", "status": "pendente",
                "regra": "sinal_nao_alinhado", "justificativa": "estimativas não alinhadas à direção desejada"}
    if cert == "muito_baixa":
        # Certeza muito baixa não sustenta nem "Misto": a heterogeneidade "explicada" também é incerta.
        return {**base, "rotulo": "Inconclusivo", "rotulo_proposto": "Inconclusivo", "regra": "certeza_muito_baixa",
                "justificativa": "certeza muito baixa (GRADE): nenhum rótulo direcional ou Misto é sustentado"}
    tem_meta = bool(meta) and (meta.get("k") or 0) >= k_min and None not in (meta.get("ci_lo"), meta.get("ci_hi"))
    if tem_meta:
        lo, hi, plo, phi = meta["ci_lo"], meta["ci_hi"], meta.get("pi_lo"), meta.get("pi_hi")
        alegada = bool(moderador_explica) or achado_explicativo is not None
        if alegada and None not in (plo, phi):
            cruza = (plo <= -delta and phi >= delta) if delta else (plo < 0 < phi)
            if cruza:
                faltas = _requisitos_misto(meta, delta, achado_explicativo)
                if not faltas:
                    conf = normalizar_certeza(achado_explicativo.get("certeza"))
                    return {**base, "rotulo": "Misto", "rotulo_proposto": "Misto", "regra": "misto_pi_moderador",
                            "justificativa": f"IP [{plo:g}; {phi:g}] cobre benefício e dano além de ±{delta:g} "
                                             f"(k = {meta.get('k'):g}); heterogeneidade explicada por "
                                             f"'{normalizar.texto(achado_explicativo.get('enunciado'))}' "
                                             f"(CERQual {conf}; {achado_explicativo.get('fonte', 'certeza.csv')})"}
                return {**base, "rotulo": "Inconclusivo", "rotulo_proposto": "Inconclusivo",
                        "regra": "inconclusivo_misto_nao_sustentado",
                        "justificativa": f"IP [{plo:g}; {phi:g}] cobre benefício e dano e a célula declara explicação "
                                         "da heterogeneidade, mas Misto não se sustenta: " + "; ".join(faltas)}
        if lo > 0 and nivel >= 2:
            return {**base, "rotulo": "Positivo", "rotulo_proposto": "Positivo", "regra": "positivo_ic",
                    "justificativa": f"IC [{lo:g}; {hi:g}] exclui 0 no sentido benéfico; certeza {cert}"}
        if hi < 0 and nivel >= 2:
            return {**base, "rotulo": "Negativo", "rotulo_proposto": "Negativo", "regra": "negativo_ic",
                    "justificativa": f"IC [{lo:g}; {hi:g}] exclui 0 no sentido danoso; certeza {cert}"}
        if delta and -delta <= lo and hi <= delta and nivel >= 3:
            return {**base, "rotulo": "Nulo", "rotulo_proposto": "Nulo", "regra": "nulo_equivalencia",
                    "justificativa": f"IC [{lo:g}; {hi:g}] dentro de ±{delta:g}; certeza {cert}"}
        motivos = []
        if lo <= 0 <= hi:
            motivos.append("IC inclui 0" + ("" if delta else " e δ não declarado"))
        if nivel < 2:
            motivos.append("certeza muito baixa")
        elif delta and -delta <= lo and hi <= delta and nivel < 3:
            motivos.append("equivalência exige certeza >= moderada")
        return {**base, "rotulo": "Inconclusivo", "rotulo_proposto": "Inconclusivo", "regra": "inconclusivo_ma",
                "justificativa": "; ".join(motivos) or "não atende às regras de Positivo/Negativo/Nulo/Misto"}
    if swim and swim.get("n") is not None and swim.get("p") is not None:
        so_alto = bool(swim.get("so_risco_alto")) if swim.get("so_risco_alto") is not None else bool(so_risco_alto)
        requisitos = swim["n"] >= 5 and swim["p"] < 0.05 and not so_alto and nivel >= 2
        if requisitos and (swim.get("prop_benefica") or 0) >= 0.70:
            return {**base, "rotulo": "Positivo", "rotulo_proposto": "Positivo", "regra": "positivo_sinal",
                    "justificativa": f"teste de sinal p = {swim['p']:.3g}, {swim['n']:g} estudos, "
                                     f"{swim['prop_benefica']:.0%} benéficos; certeza {cert}"}
        if requisitos and (swim.get("prop_danosa") or 0) >= 0.70:
            return {**base, "rotulo": "Negativo", "rotulo_proposto": "Negativo", "regra": "negativo_sinal",
                    "justificativa": f"teste de sinal p = {swim['p']:.3g}, {swim['n']:g} estudos, "
                                     f"{swim['prop_danosa']:.0%} danosos; certeza {cert}"}
        motivos = []
        if swim["n"] < 5:
            motivos.append("menos de 5 estudos")
        if swim["p"] >= 0.05:
            motivos.append("teste de sinal p >= 0,05")
        if so_alto:
            motivos.append("só estudos de risco alto")
        if nivel < 2:
            motivos.append("certeza muito baixa")
        if max(swim.get("prop_benefica") or 0, swim.get("prop_danosa") or 0) < 0.70:
            motivos.append("menos de 70% na mesma direção")
        return {**base, "rotulo": "Inconclusivo", "rotulo_proposto": "Inconclusivo", "regra": "inconclusivo_sinal",
                "justificativa": "; ".join(motivos)}
    motivo = "sem meta-análise com k >= %d nem teste de sinal" % k_min
    if meta and (meta.get("k") or 0) < k_min:
        motivo = f"meta-análise com k = {meta.get('k') or 0:g} < {k_min} não sustenta rótulo; sem teste de sinal"
    return {**base, "rotulo": "Inconclusivo", "rotulo_proposto": "Inconclusivo", "regra": "inconclusivo_sem_sintese",
            "justificativa": motivo}


def escala(estimativa, faixas):
    """Rótulo de magnitude pelas faixas do protocolo [(limite_inferior, nome)]."""
    if estimativa is None:
        return "não estimada"
    if not faixas:
        return "faixas não declaradas no protocolo"
    nome = faixas[0][1]
    for limite, rotulo in faixas:
        if abs(estimativa) >= limite:
            nome = rotulo
    return nome


def ler_faixas(texto):
    faixas = []
    for parte in (texto or "").split(","):
        if ":" in parte:
            nome, limite = parte.split(":", 1)
            faixas.append((float(limite.replace(" ", "")), nome.strip()))
    return sorted(faixas)


def rotulo_implementacao(pontos):
    return "Simples" if pontos <= 1 else ("Moderada" if pontos <= 3 else "Complexa")


def pontuar_implementacao(fichas, mapa, colunas_master):
    """(pontos, detalhes, estudos, avaliavel) para as fichas de uma família."""
    criterios = {}
    for m in mapa:
        if m.get("papel") == "criterio_implementacao":
            criterios.setdefault(m["criterio"], []).append(m)
    pontos, detalhes, estudos, avaliavel = 0, [], set(), False
    for nome, linhas in criterios.items():
        variaveis = [m["variavel_master"] for m in linhas if m["variavel_master"] in colunas_master]
        if not variaveis:
            detalhes.append(f"{nome}=sem_dado")
            continue
        avaliavel = True
        valores = {v.strip() for m in linhas for v in m.get("valores_sim", "").split("|") if v.strip()}
        limiar = max(int(float(linhas[0].get("limiar_estudos") or 1)), 1)
        com = sorted({f.get("citekey", "") for f in fichas
                      if any(_primeiro_token(f.get(v, "")) in valores for v in variaveis)})
        if len(com) >= limiar:
            pontos += 1
            estudos.update(com)
            detalhes.append(f"{nome}=1({'|'.join(com)})")
        else:
            detalhes.append(f"{nome}=0")
    return pontos, detalhes, sorted(estudos), avaliavel


def achado_explicativo(certezas, chave_familia, chave_outcome, classe=""):
    """Melhor linha de moderador/mecanismo marcada `explica_heterogeneidade` para a célula (ou None).

    Vale a linha da mesma família cujo construto_outcome é o da célula ou vazio (achado da família
    inteira) e cuja classe_desenho é a da célula ou vazia. Entre várias, a de maior confiança CERQual
    com enunciado; a escolha é determinística (ordem do arquivo no empate).
    """
    candidatas = []
    for c in certezas:
        if c.get("_dim") not in DIMENSOES_EXPLICATIVAS:
            continue
        if _dobrar(c.get("familia_intervencao")) != chave_familia:
            continue
        if _dobrar(c.get("construto_outcome")) not in ("", chave_outcome):
            continue
        if c.get("_classe") and classe and c["_classe"] != classe:
            continue
        if _dobrar(c.get("explica_heterogeneidade")) not in _MARCAS_SIM:
            continue
        enunciado = normalizar.texto(c.get("enunciado"))
        conf = normalizar_certeza(c.get("certeza"))
        nivel = NIVEL_CERTEZA.get(conf, 0) if enunciado else 0
        candidatas.append((nivel, -len(candidatas), {"certeza": conf, "enunciado": enunciado,
                                                     "fonte": c.get("_fonte", "certeza.csv"), "_linha": c}))
    if not candidatas:
        return None
    return max(candidatas, key=lambda x: (x[0], x[1]))[2]


def painel_efeito(corpos):
    """Linha-resumo de painel de uma família × construto a partir das linhas de efeito (corpos por desenho).

    Devolve dict com rotulo, status, regra, justificativa e o corpo escolhido (ou None). Regras na
    docstring do módulo (seção "Painel").
    """
    def descrever(c):
        return f"{c.get('classe_desenho') or 'sem classe'}: {c['rotulo']} (certeza {c.get('certeza') or 'ausente'})"

    status = "rascunho" if any(c["status_rotulo"] == "rascunho" for c in corpos) else "definido"
    pendentes = [c for c in corpos if c["status_rotulo"] == "pendente"]
    if pendentes:
        return {"rotulo": "Pendente", "status": "pendente", "regra": "painel_pendente", "escolhido": None,
                "justificativa": "corpo(s) sem rótulo definido: " + "; ".join(descrever(c) for c in pendentes)}
    if len(corpos) == 1:
        return {"rotulo": corpos[0]["rotulo"], "status": status, "regra": "painel_corpo_unico",
                "escolhido": corpos[0], "justificativa": "um só corpo de evidência: " + descrever(corpos[0])}

    def nivel(c):
        return NIVEL_CERTEZA.get(c.get("certeza"), 0)

    maior = max(nivel(c) for c in corpos)
    topo = [c for c in corpos if nivel(c) == maior]
    rotulos = {c["rotulo"] for c in corpos}
    if len(rotulos) == 1:
        return {"rotulo": topo[0]["rotulo"], "status": status, "regra": "painel_mesmo_rotulo", "escolhido": topo[0],
                "justificativa": "corpos com o mesmo rótulo; vale a maior certeza: "
                                 + "; ".join(descrever(c) for c in corpos)}
    if len({c["rotulo"] for c in topo}) == 1:
        outros = [c for c in corpos if c not in topo]
        return {"rotulo": topo[0]["rotulo"], "status": status, "regra": "painel_maior_certeza", "escolhido": topo[0],
                "justificativa": f"rótulos diferentes; vale o corpo de maior certeza ({descrever(topo[0])}); "
                                 "anotado: " + "; ".join(descrever(c) for c in outros)}
    return {"rotulo": "Inconclusivo", "status": status, "regra": "painel_empate_desenho", "escolhido": None,
            "justificativa": "heterogeneidade por desenho: corpos com a mesma certeza e rótulos diferentes ("
                             + "; ".join(descrever(c) for c in topo) + ")"}


def colunas_de_subcelula(linhas):
    """Colunas fora do contrato de certeza.csv cujos valores diferem entre as linhas de uma célula.

    Ignora as colunas do contrato (`COLUNAS_CERTEZA`: elas são o próprio juízo, não o recorte) e as
    internas com prefixo "_". A comparação dobra acento e caixa, como as chaves da célula. Lista vazia
    com mais de uma linha quer dizer duplicata; ordem = ordem das colunas no arquivo.
    """
    colunas = []
    for linha in linhas:
        for c in linha:
            if c and not c.startswith("_") and c not in COLUNAS_CERTEZA and c not in colunas:
                colunas.append(c)
    return [c for c in colunas if len({_dobrar(linha.get(c) or "") for linha in linhas}) > 1]


def agregar_subcelulas(subs, colunas):
    """Rótulo de uma célula de efeito com várias linhas de certeza (subcélulas), regra subcelulas-1.

    `subs`: uma entrada por linha de certeza.csv, na ordem do arquivo, com fonte, valores (das
    `colunas` que distinguem as subcélulas), rotulo, status_rotulo, certeza, regra, justificativa,
    delta e estudos (os da linha), já avaliados pelas regras caixa-3. Espelha `painel_efeito`, um
    nível abaixo; regras na docstring do módulo (seção "Subcélulas"). Devolve dict com rotulo,
    status, regra, justificativa e a subcélula escolhida (None só quando alguma está pendente; no
    empate é a primeira do arquivo entre as de maior certeza, e dá só a certeza e a força).
    """
    def nivel(c):
        return NIVEL_CERTEZA.get(c.get("certeza"), 0)

    def descrever(i, c):
        valores = "; ".join(f"{col} = {c['valores'].get(col) or 'vazio'}" for col in colunas)
        partes = [c["rotulo"], f"status {c['status_rotulo']}", f"certeza {c.get('certeza') or 'ausente'}"]
        if c.get("delta"):
            partes.append(f"δ = {c['delta']:g}")
        partes.append(f"estudos {'|'.join(c.get('estudos') or []) or 'não informados'}")
        return f"[{i}] {c['fonte']} ({valores}): {', '.join(partes)}; {c['regra']}: {c['justificativa']}."

    if any(c["status_rotulo"] == "pendente" for c in subs):
        status = "pendente"
    elif any(c["status_rotulo"] == "rascunho" for c in subs):
        status = "rascunho"
    else:
        status = "definido"
    niveis = sorted({c["certeza"] for c in subs if nivel(c)}, key=NIVEL_CERTEZA.get)
    faixa = (niveis[0] if len(niveis) == 1 else f"{niveis[0]} a {niveis[-1]}") if niveis else "ausente"
    sem_certeza = sum(1 for c in subs if not nivel(c))
    if niveis and sem_certeza:
        faixa += f" (sem certeza em {sem_certeza})"

    pendentes = [c for c in subs if c["status_rotulo"] == "pendente"]
    if pendentes:
        rotulo, regra, escolhido = "Pendente", "subcelulas_pendente", None
        nota = "subcélula(s) sem rótulo definido: " + ", ".join(c["fonte"] for c in pendentes)
    else:
        maior = max(nivel(c) for c in subs)
        topo = [c for c in subs if nivel(c) == maior]
        escolhido = topo[0]
        if len({c["rotulo"] for c in subs}) == 1:
            rotulo, regra = escolhido["rotulo"], "subcelulas_mesmo_rotulo"
            nota = f"todas com o rótulo {rotulo}; vale a maior certeza ({escolhido['fonte']})"
        elif len({c["rotulo"] for c in topo}) == 1:
            rotulo, regra = escolhido["rotulo"], "subcelulas_maior_certeza"
            nota = (f"rótulos diferentes; vale o da subcélula de maior certeza ({escolhido['fonte']}); anotadas: "
                    + ", ".join(f"{c['fonte']} ({c['rotulo']})" for c in subs if c not in topo))
        else:
            rotulo, regra = "Inconclusivo", "subcelulas_empate"
            nota = ("subcélulas com a mesma certeza máxima e rótulos diferentes ("
                    + ", ".join(f"{c['fonte']}: {c['rotulo']}" for c in topo) + "): nenhuma direção é afirmada")
    justificativa = (f"agregação {REGRA_AGREGACAO} ({regra}): a célula reúne {len(subs)} linhas de certeza que "
                     f"diferem em {', '.join(colunas)}; certeza das subcélulas: {faixa}; {nota}. "
                     + " ".join(descrever(i, c) for i, c in enumerate(subs, start=1)))
    return {"rotulo": rotulo, "status": status, "regra": regra, "escolhido": escolhido, "justificativa": justificativa}


# ---------------------------------------------------------------------------
# Montagem
# ---------------------------------------------------------------------------
def _linha(celula_familia, celula_outcome, dimensao, classe="", **campos):
    linha = {c: "" for c in COLUNAS_CAIXA}
    celula_id = f"{celula_familia or '*'} × {celula_outcome or '*'}" + (f" [{classe}]" if classe else "")
    linha.update({"familia_intervencao": celula_familia, "construto_outcome": celula_outcome, "dimensao": dimensao,
                  "classe_desenho": classe, "celula_id": celula_id, "regra_versao": REGRA_VERSAO})
    for k, v in campos.items():
        linha[k] = "" if v is None else (f"{v:g}" if isinstance(v, float) else v)
    return linha


def _assinar(linha):
    conteudo = json.dumps({k: linha[k] for k in COLUNAS_CAIXA if k != "assinatura"}, ensure_ascii=False,
                          sort_keys=True)
    linha["assinatura"] = estado.sha256_texto(conteudo)
    return linha


def montar_caixa(master=None, meta_arq=None, swim_arq=None, certeza_arq=None, mapa_arq=MAPA_PADRAO, delta=None,
                 faixas=None, k_min=3):
    """Monta as linhas da caixa. Devolve (linhas, avisos)."""
    avisos = []
    _, mapa = ler_csv(mapa_arq)
    papel = lambda p: [m for m in mapa if m.get("papel") == p]  # noqa: E731
    colunas_master, fichas = ler_csv(master) if master else ([], [])
    nome_master = Path(master).name if master else ""
    def coluna_do_papel(nome):
        return next((m["variavel_master"] for m in papel(nome) if m["variavel_master"] in colunas_master), None)

    col_familia = coluna_do_papel("celula_familia")
    meta = ler_meta(meta_arq, avisos)
    swim = ler_swim(swim_arq, avisos)
    certezas = []
    if certeza_arq:
        for i, c in enumerate(ler_csv(certeza_arq)[1], start=2):
            c["_fonte"] = f"{Path(certeza_arq).name}:linha {i}"
            c["_dim"] = _dobrar(c.get("dimensao"))
            certezas.append(c)

    rob_alto = set()
    for m in papel("rob"):
        if m["variavel_master"] in colunas_master:
            valores = {v.strip() for v in m.get("valores_sim", "").split("|") if v.strip()}
            rob_alto |= {f.get("citekey", "") for f in fichas if _primeiro_token(f.get(m["variavel_master"])) in valores}

    familias = {}
    celulas = {}

    def registrar_familia(nome):
        familias.setdefault(_dobrar(nome), nome)

    for c in certezas:
        c["_classe"] = classe_desenho(c.get("classe_desenho"))
        if normalizar.texto(c.get("classe_desenho")) and not c["_classe"]:
            avisos.append(f"{c['_fonte']}: classe_desenho {c.get('classe_desenho')!r} desconhecida "
                          f"(use {'|'.join(CLASSES_DESENHO[:2])}); tratada como sem classe")
    herdar_familia([(Path(meta_arq).name if meta_arq else "", meta), (Path(swim_arq).name if swim_arq else "", swim)],
                   certezas, [f.get(col_familia, "") for f in fichas] if col_familia else [], avisos)
    classes_sintese = {}
    for chave, item in list(meta.items()) + list(swim.items()):
        celulas.setdefault(chave, (item["familia"], item["outcome"], item["classe"]))
        classes_sintese.setdefault(chave[:2], set()).add(chave[2])
        registrar_familia(item["familia"])
    for c in certezas:
        registrar_familia(c.get("familia_intervencao", "").strip())
        if c["_dim"] == "efeito":
            fo = (_dobrar(c.get("familia_intervencao")), _dobrar(c.get("construto_outcome")))
            # sem classe e com síntese na célula: a certeza vale para as classes da síntese (não cria linha nova)
            if c["_classe"] or not classes_sintese.get(fo):
                celulas.setdefault(fo + (c["_classe"],), (c.get("familia_intervencao", "").strip(),
                                                          c.get("construto_outcome", "").strip(), c["_classe"]))
    for f in fichas:
        registrar_familia((f.get(col_familia) if col_familia else "") or "")
    if not familias:
        registrar_familia("")

    linhas = []
    avisados_classe = set()

    def avaliar(cert, m, s, chave, classe):
        """Regras caixa-3 para uma linha de certeza de efeito da célula (ou {} sem linha).

        É o corpo de sempre do laço de efeito, isolado para ser aplicado a cada subcélula. Devolve
        (resultado de rotular_efeito, status, δ, estudos da célula, fontes do achado explicativo).
        """
        d = _num(cert.get("delta")) if cert.get("delta") else delta
        moderador = _dobrar(cert.get("moderador_explica")) in {"sim", "s", "1", "true", "pre_especificado",
                                                                "pre-especificado", "quali", "qualitativo"}
        estudos = sorted(set((m or {}).get("estudos", []) + (s or {}).get("estudos", []) + _lista(cert.get("estudos"))))
        so_alto = bool(estudos) and bool(rob_alto) and all(e in rob_alto for e in estudos)
        achado = achado_explicativo(certezas, chave[0], chave[1], classe)
        r = rotular_efeito(m, s, cert.get("certeza"), d, moderador, k_min, so_risco_alto=so_alto,
                           achado_explicativo=achado)
        status = _status_validado(r["status"], cert)
        fontes_achado = []
        if achado and r["regra"] in ("misto_pi_moderador", "inconclusivo_misto_nao_sustentado"):
            fontes_achado.append(achado["fonte"])
            if r["regra"] == "misto_pi_moderador" and status == "definido" and _validado(achado["_linha"]) is False:
                status = "rascunho"
                r = dict(r, justificativa=r["justificativa"] + "; validado_humano do achado explicativo não marcado")
        return r, status, d, estudos, fontes_achado

    # --- efeito ---------------------------------------------------------------
    for chave, (fam, out, classe) in sorted(celulas.items()):
        m, s = meta.get(chave), swim.get(chave)
        da_celula = [c for c in certezas if c["_dim"] == "efeito"
                     and (_dobrar(c.get("familia_intervencao")), _dobrar(c.get("construto_outcome"))) == chave[:2]]
        cert_linhas = [c for c in da_celula if c["_classe"] == classe] or [c for c in da_celula if not c["_classe"]]
        cert = cert_linhas[-1] if cert_linhas else {}
        classes_da_celula = {k[2] for k in celulas if k[:2] == chave[:2]}
        if cert and not cert["_classe"] and len(classes_da_celula - {""}) > 1 and chave[:2] not in avisados_classe:
            avisados_classe.add(chave[:2])
            avisos.append(f"{', '.join(c['_fonte'] for c in cert_linhas)}: certeza sem classe_desenho aplicada a "
                          f"{' e '.join(sorted(classes_da_celula - {''}))} de {fam or '*'} × {out or '*'}; "
                          "o GRADE julga randomizados e não randomizados separadamente: declare uma linha por classe")
        colunas_sub = colunas_de_subcelula(cert_linhas) if len(cert_linhas) > 1 else []
        if len(cert_linhas) > 1 and not colunas_sub:
            avisos.append(f"{fam or '*'} × {out or '*'} [{classe or 'sem classe'}]: {len(cert_linhas)} linhas de "
                          f"certeza sem coluna que as distinga ({', '.join(c['_fonte'] for c in cert_linhas)}); vale a "
                          f"última ({cert['_fonte']}): apague as duplicatas ou declare a coluna que separa as subcélulas")
        if colunas_sub:
            # subcélulas (regra subcelulas-1): cada linha pelas regras caixa-3, depois a agregação
            subs, estudos, fontes = [], set(), [x["fonte"] for x in (m, s) if x] + [c["_fonte"] for c in cert_linhas]
            for c in cert_linhas:
                r, status, d, estudos_c, fontes_achado = avaliar(c, m, s, chave, classe)
                estudos.update(estudos_c)
                fontes += [f for f in fontes_achado if f not in fontes]
                subs.append({"fonte": c["_fonte"], "valores": {col: normalizar.texto(c.get(col)) for col in colunas_sub},
                             "rotulo": r["rotulo"], "status_rotulo": status, "certeza": normalizar_certeza(c.get("certeza")),
                             "forca": r["forca"], "regra": r["regra"], "justificativa": r["justificativa"], "delta": d,
                             "estudos": _lista(c.get("estudos")), "abordagem": c.get("abordagem", "GRADE")})
            ag = agregar_subcelulas(subs, colunas_sub)
            esc = ag["escolhido"] or {}
            estudos = sorted(estudos)
            pendente = ag["regra"] == "subcelulas_pendente"
            linhas.append(_linha(
                fam, out, "efeito", classe, rotulo=ag["rotulo"], rotulo_proposto="" if pendente else ag["rotulo"],
                status_rotulo=ag["status"], forca=esc.get("forca", ""), certeza=esc.get("certeza", ""),
                abordagem_certeza=(esc or subs[-1])["abordagem"], escala=escala((m or {}).get("estimativa"), faixas),
                estimativa=(m or {}).get("estimativa"), ci_lo=(m or {}).get("ci_lo"), ci_hi=(m or {}).get("ci_hi"),
                pi_lo=(m or {}).get("pi_lo"), pi_hi=(m or {}).get("pi_hi"), k=(m or {}).get("k"),
                n_estudos=str(len(estudos)) if estudos else ((s or {}).get("n") and f"{s['n']:g}") or "",
                regra_aplicada=ag["regra"], estudos="|".join(estudos), fontes=" ; ".join(fontes),
                justificativa=ag["justificativa"]))
            continue
        r, status, d, estudos, fontes_achado = avaliar(cert, m, s, chave, classe)
        fontes = [x["fonte"] for x in (m, s) if x] + ([cert["_fonte"]] if cert else []) + fontes_achado
        if not fontes:
            fontes = ["nenhum resumo de síntese nem certeza para a célula"]
        linhas.append(_linha(
            fam, out, "efeito", classe, rotulo=r["rotulo"], rotulo_proposto=r["rotulo_proposto"], status_rotulo=status,
            forca=r["forca"], certeza=normalizar_certeza(cert.get("certeza")),
            abordagem_certeza=cert.get("abordagem", "GRADE" if cert else ""),
            escala=escala((m or {}).get("estimativa"), faixas),
            estimativa=(m or {}).get("estimativa"), ci_lo=(m or {}).get("ci_lo"), ci_hi=(m or {}).get("ci_hi"),
            pi_lo=(m or {}).get("pi_lo"), pi_hi=(m or {}).get("pi_hi"), k=(m or {}).get("k"),
            n_estudos=str(len(estudos)) if estudos else ((s or {}).get("n") and f"{s['n']:g}") or "",
            regra_aplicada=r["regra"], estudos="|".join(estudos), fontes=" ; ".join(fontes),
            justificativa=r["justificativa"] + (f"; δ = {d:g}" if d else "")))

    # --- painel: uma linha por família × construto ---------------------------
    por_celula = {}
    for l in [l for l in linhas if l["dimensao"] == "efeito"]:
        por_celula.setdefault((_dobrar(l["familia_intervencao"]), _dobrar(l["construto_outcome"])), []).append(l)
    for _, corpos in sorted(por_celula.items()):
        p = painel_efeito(corpos)
        esc = p["escolhido"] or {}
        certeza_painel = esc.get("certeza", "")
        if p["regra"] == "painel_empate_desenho":
            certeza_painel = max((c["certeza"] for c in corpos if c["certeza"]), key=lambda x: NIVEL_CERTEZA[x],
                                 default="")
        estudos_painel = sorted({e for c in corpos for e in c["estudos"].split("|") if e})
        linhas.append(_linha(
            corpos[0]["familia_intervencao"], corpos[0]["construto_outcome"], DIMENSAO_PAINEL, "",
            celula_id=f"{corpos[0]['familia_intervencao'] or '*'} × {corpos[0]['construto_outcome'] or '*'} [painel]",
            rotulo=p["rotulo"], rotulo_proposto="" if p["regra"] == "painel_pendente" else p["rotulo"],
            status_rotulo=p["status"], forca=FORCA.get(certeza_painel, "") if p["regra"] != "painel_pendente" else "",
            certeza=certeza_painel if p["regra"] != "painel_pendente" else "",
            abordagem_certeza=esc.get("abordagem_certeza", "GRADE" if certeza_painel else ""),
            escala=esc.get("escala", ""), estimativa=esc.get("estimativa", ""), ci_lo=esc.get("ci_lo", ""),
            ci_hi=esc.get("ci_hi", ""), pi_lo=esc.get("pi_lo", ""), pi_hi=esc.get("pi_hi", ""), k=esc.get("k", ""),
            n_estudos=str(len(estudos_painel)) if estudos_painel else "", estudos="|".join(estudos_painel),
            regra_aplicada=p["regra"], fontes=" ; ".join(f"caixa: {c['celula_id']}" for c in corpos),
            justificativa=p["justificativa"]))

    # --- implementação (por família) -----------------------------------------
    for chave_fam, fam in sorted(familias.items()):
        fichas_fam = [f for f in fichas if not col_familia or _dobrar(f.get(col_familia)) == chave_fam]
        cert_linhas = [c for c in certezas if c["_dim"] == "implementacao"
                       and _dobrar(c.get("familia_intervencao")) == chave_fam]
        cert = cert_linhas[-1] if cert_linhas else {}
        nota_varias = ""
        if len(cert_linhas) > 1:
            # várias linhas para a família: a de maior CERQual (a última no empate, a regra anterior); todas nas fontes
            cert = max(enumerate(cert_linhas),
                       key=lambda x: (NIVEL_CERTEZA.get(normalizar_certeza(x[1].get("certeza")), 0), x[0]))[1]
            nota_varias = (f"; {len(cert_linhas)} linhas de implementação em certeza.csv ("
                           + ", ".join(f"{c['_fonte']}: {normalizar_certeza(c.get('certeza')) or 'sem CERQual'}"
                                       for c in cert_linhas)
                           + f"); vale a de maior confiança CERQual ({cert['_fonte']})")
            avisos.append(f"{fam or '*'}: {len(cert_linhas)} linhas de implementação em certeza.csv "
                          f"({', '.join(c['_fonte'] for c in cert_linhas)}); vale a de maior confiança CERQual "
                          f"({cert['_fonte']}) e a linha sai rascunho se alguma não estiver validada")
        fontes = [f"{Path(mapa_arq).name} (critérios de implementação)"]
        if fichas_fam:
            fontes.append(f"{nome_master}: {len(fichas_fam)} fichas")
        fontes += [c["_fonte"] for c in cert_linhas]
        pontos, detalhes, estudos, avaliavel = pontuar_implementacao(fichas_fam, mapa, colunas_master)
        if not avaliavel:
            rotulo, proposto, status, just = "Não avaliada", "", "pendente", \
                "master sem as variáveis de implementação do mapa"
        else:
            proposto = rotulo_implementacao(pontos)
            conf = normalizar_certeza(cert.get("certeza"))
            if conf:
                rotulo, status, just = proposto, "definido", f"{pontos} pontos; confiança CERQual {conf}"
            else:
                rotulo, status, just = "Pendente", "pendente", f"{pontos} pontos; falta confiança CERQual"
            sem_dado = [d for d in detalhes if d.endswith("sem_dado")]
            if sem_dado:
                just += f"; pontuação mínima ({len(sem_dado)} critérios sem dado)"
            status = _status_validado(status, cert)
            if status == "definido" and any(_validado(c) is False for c in cert_linhas):
                status = "rascunho"  # uma linha não validada basta: o juízo escolhido depende de todas
            if status == "rascunho":
                just += "; validado_humano não marcado"
        just += nota_varias
        linhas.append(_linha(
            fam, "", "implementacao", rotulo=rotulo, rotulo_proposto=proposto, status_rotulo=status,
            certeza=normalizar_certeza(cert.get("certeza")),
            abordagem_certeza=cert.get("abordagem", "CERQual" if cert else ""),
            pontos_implementacao=str(pontos) if avaliavel else "", criterios_implementacao="; ".join(detalhes),
            enunciado=cert.get("enunciado", ""), regra_aplicada="implementacao_pontos", estudos="|".join(estudos),
            n_estudos=str(len(estudos)), fontes=" ; ".join(fontes),
            justificativa=just + (f"; {cert.get('justificativa')}" if cert.get("justificativa") else "")))

        # --- achados: mecanismo, moderador, percepção, custo -------------------
        for dim in DIMENSOES_ACHADO:
            achados = [c for c in certezas if c["_dim"] == dim and _dobrar(c.get("familia_intervencao")) == chave_fam]
            for c in achados:
                conf = normalizar_certeza(c.get("certeza"))
                enunciado = normalizar.texto(c.get("enunciado"))
                ok = bool(conf and enunciado)
                status_achado = _status_validado("definido" if ok else "pendente", c)
                linhas.append(_linha(
                    fam, c.get("construto_outcome", "").strip(), dim, rotulo=enunciado or "Pendente",
                    rotulo_proposto=enunciado, status_rotulo=status_achado, certeza=conf,
                    abordagem_certeza=c.get("abordagem", "CERQual"), enunciado=enunciado, regra_aplicada="achado_cerqual",
                    estudos="|".join(_lista(c.get("estudos"))), n_estudos=str(len(_lista(c.get("estudos")))),
                    fontes=c["_fonte"],
                    justificativa="; ".join(x for x in (
                        normalizar.texto(c.get("justificativa")) or ("" if ok else "falta enunciado ou confiança CERQual"),
                        "validado_humano não marcado" if status_achado == "rascunho" else "") if x)))
            vars_dim = [m for m in mapa if _dobrar(m.get("dimensao_caixa")) == dim
                        and m.get("papel") in ("achado", "custo_unitario") and m["variavel_master"] in colunas_master]
            com_achado = set()
            for m in vars_dim:
                valores = {v.strip() for v in m.get("valores_sim", "").split("|") if v.strip()}
                for f in fichas_fam:
                    valor = f.get(m["variavel_master"], "")
                    token = _primeiro_token(valor)
                    preenchido = normalizar.texto(valor) and token not in TOKENS_AUSENTES
                    if (valores and token in valores) or (not valores and preenchido):
                        com_achado.add(f.get("citekey", ""))
            fonte_master = f"{nome_master}: {', '.join(m['variavel_master'] for m in vars_dim)}" if vars_dim else ""
            if com_achado and not achados:
                linhas.append(_linha(
                    fam, "", dim, rotulo="Pendente", status_rotulo="pendente", regra_aplicada="achado_sem_sintese",
                    estudos="|".join(sorted(com_achado)), n_estudos=str(len(com_achado)), fontes=fonte_master,
                    justificativa="estudos relatam o achado, mas não há enunciado sintetizado com CERQual"))
            elif dim == "custo" and not achados:
                if master:
                    linhas.append(_linha(
                        fam, "", dim, rotulo="Não reportado", rotulo_proposto="Não reportado", status_rotulo="definido",
                        regra_aplicada="custo_nao_reportado", n_estudos="0",
                        fontes=fonte_master or f"{nome_master}: sem variáveis de custo do mapa",
                        justificativa="nenhuma ficha relata custo unitário ou custo-efetividade"))
                else:
                    linhas.append(_linha(
                        fam, "", dim, rotulo="Pendente", status_rotulo="pendente", regra_aplicada="custo_sem_master",
                        fontes="sem fichamentos_master.csv", justificativa="custo não avaliado: informe --master"))
    return [_assinar(l) for l in linhas], avisos


def contar_agregadas(linhas):
    """Linhas de efeito rotuladas pela regra de subcélulas (regra_aplicada subcelulas_*)."""
    return sum(1 for l in linhas if l["dimensao"] == "efeito" and l["regra_aplicada"].startswith("subcelulas_"))


def markdown_caixa(linhas, rascunho, fontes_entrada):
    cab = ["# Caixa de ferramentas", ""]
    if rascunho:
        cab += [f"**{esquema.MARCA_RASCUNHO}**: há rótulos pendentes ou pendências abertas no projeto.", ""]
    cab += [f"Regras: `{REGRA_VERSAO}` ({REF_REGRAS_CAIXA}). Entradas: {', '.join(fontes_entrada) or 'nenhuma'}.",
            "Testes combinados não definem rótulos. Linhas `efeito_painel` resumem os corpos por desenho "
            "de cada família × outcome."]
    n_agregadas = contar_agregadas(linhas)
    if n_agregadas:  # sem subcélulas, o cabeçalho fica como antes
        cab.append(f"Agregação `{REGRA_AGREGACAO}`: {n_agregadas} células de efeito reúnem mais de uma linha de "
                   "certeza (subcélulas); o rótulo vem da regra de subcélulas e a justificativa descreve cada uma.")
    cab += ["", "| Família × outcome | Dimensão | Rótulo | Status | Força/certeza | Escala | Estudos | Fontes |",
            "|---|---|---|---|---|---|---|---|"]
    for l in linhas:
        forca = " / ".join(x for x in (l["forca"], l["certeza"]) if x)
        celulas = [l["celula_id"], l["dimensao"], l["rotulo"], l["status_rotulo"], forca, l["escala"],
                   l["estudos"].replace("|", ", "), l["fontes"]]
        cab.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in celulas) + " |")
    return "\n".join(cab) + "\n"


def cmd_caixa(args):
    comando = "caixa"
    raiz = exigir_raiz(args, comando)
    if raiz is None:
        return 1

    def opcional(valor, padrao):
        if valor:
            p = resolver_caminho(raiz, valor)
            if not p.exists():
                raise FileNotFoundError(f"arquivo não encontrado: {valor}")
            return p
        p = raiz / padrao
        return p if p.exists() else None

    try:
        meta_arq = opcional(args.efeitos, "06-analise/meta_resumo.json")
        swim_arq = opcional(args.swim, "06-analise/swim_resumo.json")
        certeza_arq = opcional(args.certeza, "06-analise/certeza.csv")
        master = opcional(args.master, "03-textos/fichamentos_master.csv") if args.master else None
        mapa = resolver_caminho(raiz, args.mapa) if args.mapa else MAPA_PADRAO
        if not mapa.exists() and args.mapa and (MAPA_PADRAO.parent / Path(args.mapa).name).exists():
            mapa = MAPA_PADRAO.parent / Path(args.mapa).name  # caminho relativo à pasta da skill
        if not mapa.exists():
            raise FileNotFoundError(f"mapa não encontrado: {args.mapa}")
        faixas = ler_faixas(args.faixas)
    except (FileNotFoundError, ValueError) as e:
        return falhar(comando, str(e))
    if not any((meta_arq, swim_arq, certeza_arq, master)):
        return falhar(comando, "nenhuma entrada: informe --efeitos, --swim, --certeza e/ou --master")
    try:
        linhas, avisos = montar_caixa(master, meta_arq, swim_arq, certeza_arq, mapa, args.delta, faixas, args.k_min)
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return falhar(comando, f"entrada inválida: {e}")
    pendentes = [l for l in linhas if l["status_rotulo"] != "definido"]  # pendente ou rascunho
    n_rascunho = sum(1 for l in pendentes if l["status_rotulo"] == "rascunho")
    if not pendentes:
        # A condição sumiu (todas as células definidas): fecha certeza_caixa antes de decidir a marca de
        # rascunho, para que a própria pendência resolvida não mantenha o produto como rascunho.
        sincronizar_pendencia_unica(raiz, esquema.PENDENCIA_CERTEZA_CAIXA, "10_sintese", "", 0, portao="G8",
                                    arquivo=ARQ_CAIXA, ator_id=ATOR,
                                    motivo_resolvida="todas as células da caixa com status_rotulo definido")
    est = estado.carregar_estado(raiz)
    rascunho = bool(pendentes) or bool(estado.pendencias_abertas(est))
    entradas = [relativo(raiz, p) for p in (meta_arq, swim_arq, certeza_arq, master) if p]
    escrever_csv(raiz / ARQ_CAIXA, COLUNAS_CAIXA, linhas)
    escrever_texto(raiz / ARQ_CAIXA_MD, markdown_caixa(linhas, rascunho, entradas))
    contagem, painel = {}, {}
    for l in linhas:
        if l["dimensao"] == "efeito":
            contagem[l["rotulo"]] = contagem.get(l["rotulo"], 0) + 1
        elif l["dimensao"] == DIMENSAO_PAINEL:
            painel[l["rotulo"]] = painel.get(l["rotulo"], 0) + 1
    n_agregadas = contar_agregadas(linhas)
    estado.registrar_evento(raiz, "caixa_gerada", "10_sintese", "script", ATOR,
                            dados={"regra_versao": REGRA_VERSAO, "n_linhas": len(linhas), "rotulos_efeito": contagem,
                                   "rotulos_painel": painel, "n_pendentes": len(pendentes), "n_rascunho": n_rascunho,
                                   "rascunho": rascunho, "regra_agregacao": REGRA_AGREGACAO,
                                   "n_celulas_agregadas": n_agregadas},
                            artefatos=[ARQ_CAIXA, ARQ_CAIXA_MD] + entradas)
    pendencia = None
    if pendentes:  # n diferente atualiza a pendência aberta sem duplicar
        pendencia = sincronizar_pendencia_unica(raiz, esquema.PENDENCIA_CERTEZA_CAIXA, "10_sintese",
                                                "completar certeza (GRADE/CERQual) e enunciados das células pendentes",
                                                len(pendentes), portao="G8", arquivo=ARQ_CAIXA, ator_id=ATOR)
    estado.resumo({"comando": comando, "ok": True, "n_linhas": len(linhas), "rotulos_efeito": contagem,
                   "rotulos_painel": painel, "n_pendentes": len(pendentes), "n_rascunho": n_rascunho, "rascunho": rascunho,
                   "regra_versao": REGRA_VERSAO, "regra_agregacao": REGRA_AGREGACAO, "n_celulas_agregadas": n_agregadas,
                   "arquivos": [ARQ_CAIXA, ARQ_CAIXA_MD], "pendencia": pendencia, "avisos": avisos})
    return 0


def registrar(subparsers):
    p = subparsers.add_parser("caixa", help="caixa de ferramentas com rótulos por regra explícita e fontes por célula")
    p.add_argument("--master", default=None, help="fichamentos_master.csv da decomposição")
    p.add_argument("--efeitos", default=None, help="meta_resumo.json do meta.R (padrão 06-analise/meta_resumo.json)")
    p.add_argument("--swim", default=None, help="swim_resumo.json do swim.R (padrão 06-analise/swim_resumo.json)")
    p.add_argument("--certeza", default=None, help="certeza.csv com GRADE/CERQual (padrão 06-analise/certeza.csv)")
    p.add_argument("--mapa", default=None, help="mapa de variáveis (padrão assets/mapas/caixa_ferramentas_mapa.csv)")
    p.add_argument("--delta", type=float, default=None, help="δ/SESOI do protocolo (se certeza.csv não trouxer)")
    p.add_argument("--faixas", default=None,
                   help='faixas de magnitude do protocolo, ex. "pequena:0,moderada:0.3,grande:0.6"')
    p.add_argument("--k-min", type=int, default=3,
                   help=f"k mínimo para usar a meta-análise no rótulo (Misto exige k >= {K_MISTO_MIN}, δ e achado "
                        "explicativo com CERQual >= baixa)")
    p.set_defaults(func=cmd_caixa)
