"""Declaração de uso de IA gerada do log do projeto (RAISE / PRISMA-trAIce).

USO
    python3 rs.py declaracao-ia [--out 07-relatorio/declaracao_uso_ia.md]

Lê `rs_log.jsonl`, `dados/decisoes.jsonl`, `rs_estado.json` e os `certeza*.csv` da pasta de
`06-analise/certeza.csv` (só essa pasta, sem subpastas) e escreve um Markdown com:
    1. ferramentas e modelos (tipo de ator, etapas, primeira e última data, nº de
       eventos e de decisões, parâmetros registrados);
    2. papel da IA e dos humanos por etapa;
    3. prompts, critérios e codebooks arquivados com sha256 (artefatos do log e
       `prompt_sha` das decisões);
    4. validação: a validação que decide (métricas, IC, limiares e se atendeu), o histórico
       de calibração e desenvolvimento, elusão e estabilidade;
    5. portões (quem aprovou, humano ou autopiloto) e custo de API;
    6. pendências abertas, com a descrição como foi registrada na abertura (data e seq do evento
       `pendencia_aberta`) e, entre colchetes, o fechamento e as sucessoras das pendências citadas
       que já foram fechadas; a marca RASCUNHO NÃO VALIDADO quando couber;
    7. declaração de responsabilidade humana montada do que está registrado: juízos de IA sem
       validação humana (dados de efeito, RoB por ferramenta, certeza GRADE/CERQual por arquivo,
       rótulos da caixa, portões aprovados sem humano e ainda sem confirmação), problemas da
       validação da triagem e demais pendências abertas por etapa; depois, os portões confirmados
       por humano mais tarde e as validações humanas completas.

Por que gerar do log e não escrever à mão: a declaração só é verificável se cada
número remeter a um evento com seq e hash. Nada é digitado; o que o log não tem
aparece como "não registrado", o que também denuncia lacunas do processo.

Por que a seção 7 sai dos dados: um texto fixo afirmava que risco de viés, certeza e rótulos
da caixa eram juízos dos revisores humanos, conferidos nos portões, mesmo quando o autopiloto
aprovou os portões e ninguém marcou `validado_humano`. A declaração não pode atestar validação
que o log e os arquivos não registram; esses juízos são rascunho de IA e vão listados como tal.
Sem nada em aberto, a seção sai com o texto de sempre, byte a byte, para que projetos limpos
não ganhem versão nova da declaração sem mudança no processo. Os `certeza*.csv` lidos entram,
com sha256, nos artefatos do evento da declaração. Um `certeza*.csv` sem a coluna `validado_humano`
segue a regra da caixa (formato anterior, não rebaixa a rascunho) e só é citado na seção 7, para
que caixa, PRISMA e declaração concordem sobre a marca de rascunho.

Por que a seção 6 anota as pendências citadas em vez de reescrever a descrição: a descrição é
gravada uma vez, na abertura, e cita contagens e pendências daquele momento ("Pxxx aberta").
Reescrevê-la apagaria o registro; a nota diz o que houve depois. A cadeia de sucessoras vem do
"[substitui Pxxx]" no fim da descrição da nova e do "substituída por Pxxx" no motivo do
fechamento da antiga, e só liga pendências do mesmo tipo: a confirmação de um portão
(`revisao_humana_portao`) copia na descrição o texto de outras pendências, inclusive o
"[substitui ...]" delas, sem substituir nenhuma. A citada cuja cadeia chega à própria
pendência (a que ela substituiu) não é anotada.

A marca de rascunho aparece quando há pendências abertas, quando a validação que
decide não atingiu os limiares, quando houve decisão de IA na triagem sem validação
que decide (references/ia-validacao.md, seção 7), ou quando a seção 7 lista juízos de IA
sem validação humana. A validação que decide é, por etapa, a última
`validacao_calculada` com `dados.finalidade = validacao` da rodada ativa
(`versoes_ativas.rodada_ta`, ou as rodadas da última consolidação que a contém). Eventos
antigos sem `finalidade` contam como validação, salvo `tipo` elusao/estabilidade. Calibração
e desenvolvimento reprovados não marcam rascunho: são o caminho normal até a validação
(references/ia-validacao.md, seção 4, passos A e B) e aparecem como histórico.

O evento `relatorio_gerado` da declaração grava `dados.ultimo_seq` (último seq do log coberto, fora os
eventos deste comando): o G9 compara esse campo com o log, e o sha256 do arquivo no evento confirma que é
a mesma versão (sem depender da frase do texto).

Custo: soma `custo_usd`/`custo_estimado_usd`/`custo` dos eventos (uma chave por evento). Evento
com `uso_tokens` e sem custo tem o custo calculado com a `tabela_precos` do próprio evento (ou,
na falta dela, com a tabela atual de provedores.py, marcada "verificar"). O que não tem custo
nem tokens é declarado como não registrado; estimativas de `--estimar` são listadas à parte e
nunca somadas.
"""

import csv
import json
import re
import sys
from pathlib import Path

from . import esquema, estado, provedores
from . import triagem_lotes as tl
from .handoff import exigir_raiz, ler_csv, relativo, resolver_caminho, sim

ATOR = "rs.py declaracao-ia"
ARQ_DECLARACAO = esquema.ARQ_DECLARACAO_IA
TIPOS_IA = {"ia_coordenador", "ia_subagente", "ia_api"}
PASTAS_PROMPT = ("02-triagem/prompts", "00-protocolo", "agentes", "05-decomposicao", "04-qualidade")
CHAVES_CUSTO = ("custo_usd", "custo_estimado_usd", "custo")
TIPO_ESTIMATIVA_CUSTO = "estimativa_custo_api"
ETAPA_DECISAO_DO_PROJETO = {v: k for k, v in tl.ETAPA_PROJETO.items()}
ROTULO_FINALIDADE = {"calibracao": "calibração", "desenvolvimento": "desenvolvimento", "validacao": "validação",
                     "elusao": "elusão", "estabilidade": "estabilidade"}
LIMIARES_REFERENCIA = [
    "Triagem T/A: recall >= 0,95 com limite inferior do IC >= 0,90; amostra com >= 60 incluídos humanos",
    "Calibração humana: kappa >= 0,6 e concordância >= 75%",
    "Extração categórica: kappa ou PABAK >= 0,7 e concordância >= 80% por variável",
    "Dados numéricos de efeito: 100% verificados na página do PDF",
]
# Seção 7 quando nada está em aberto: o texto de sempre, sem mudar um byte (projetos limpos não ganham versão nova).
TEXTO_RESPONSABILIDADE = (
    "As ferramentas de IA listadas foram usadas como apoio sob supervisão humana. Critérios, protocolo, "
    "juízos de risco de viés, de certeza (GRADE/CERQual), rótulos da caixa de ferramentas e conclusões são "
    "responsabilidade dos revisores humanos, que conferiram as saídas conforme os portões e as validações "
    "acima. Decisões de IA não validadas estão sinalizadas como pendências.")
FECHO_RESPONSABILIDADE = "Decisões de IA não validadas estão sinalizadas como pendências."
MOTIVO_JUIZOS = "juízos de IA sem validação humana (seção 7)"
TIPO_PENDENCIA_PORTAO = "revisao_humana_portao"  # aberta pelo autopiloto em `portao` (projeto.cmd_portao)
RE_SUBSTITUI = re.compile(r"\[substitui (P\d{3,})\]\s*$")  # fim da descrição da nova (handoff.sincronizar_*)
RE_SUBSTITUIDA_POR = re.compile(r"substitu[íi]da por (P\d{3,})")  # motivo do fechamento da antiga
RE_PENDENCIA = re.compile(r"\bP\d{3,}\b")
ROTULO_ETAPA = {
    "00_configuracao": "configuração", "01_pergunta": "pergunta", "02_teoria_framework": "teoria do programa",
    "03_protocolo": "protocolo", "04_busca": "busca", "05_organizacao": "organização e deduplicação",
    "06_triagem_ta": "triagem de títulos e resumos", "07_textos_elegibilidade": "textos completos e elegibilidade",
    "08_piloto_extracao": "piloto da extração", "09_extracao_rob": "extração e risco de viés",
    "10_sintese": "síntese e certeza", "11_relato": "relato",
}


def ler_decisoes(raiz):
    caminho = Path(raiz) / esquema.ARQ_DECISOES
    saida = []
    if not caminho.exists():
        return saida
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                try:
                    saida.append(json.loads(linha))
                except json.JSONDecodeError:
                    continue
    return saida


def _achatar(dados, prefixo=""):
    itens = []
    if isinstance(dados, dict):
        for k, v in dados.items():
            itens += _achatar(v, f"{prefixo}{k}.")
    elif isinstance(dados, list) and dados and all(isinstance(x, (int, float)) for x in dados) and len(dados) <= 3:
        numeros = "; ".join(f"{x:g}" if isinstance(x, float) else str(x) for x in dados)
        itens.append((prefixo.rstrip("."), f"[{numeros}]"))
    elif isinstance(dados, list):
        itens.append((prefixo.rstrip("."), f"{len(dados)} itens"))
    else:
        itens.append((prefixo.rstrip("."), dados))
    return itens


def _data(ts):
    return (ts or "")[:10]


def _num(valor):
    if isinstance(valor, bool) or valor is None:
        return "" if valor is None else valor
    return f"{valor:.3f}" if isinstance(valor, float) else valor


def _md(valor):
    return str("" if valor is None else valor).replace("|", "/").replace("\n", " ")


def _tabela(cabecalho, linhas):
    if not linhas:
        return ["_não registrado_", ""]
    saida = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    saida += ["| " + " | ".join(_md(c) for c in linha) + " |" for linha in linhas]
    return saida + [""]


def coletar(raiz):
    """Estruturas da declaração a partir do log, das decisões, do estado e dos certeza*.csv (ler_certezas)."""
    raiz = Path(raiz)
    # Os eventos que este próprio comando registra ficam de fora: assim a declaração
    # só muda quando o processo muda, e reexecutar não gera versões novas à toa.
    eventos = [e for e in estado.ler_log(raiz) if (e.get("ator") or {}).get("id") != ATOR]
    decisoes = ler_decisoes(raiz)
    est = estado.carregar_estado(raiz)

    modelos = {}

    def anotar_modelo(modelo, tipo, etapa, ts, n_evento=0, n_decisao=0, parametros=None):
        if not modelo and tipo not in TIPOS_IA:
            return
        m = modelos.setdefault(modelo or f"(modelo não registrado: {tipo})",
                               {"tipos": set(), "etapas": set(), "inicio": ts, "fim": ts, "eventos": 0,
                                "decisoes": 0, "parametros": set()})
        m["tipos"].add(tipo)
        if etapa:
            m["etapas"].add(etapa)
        if ts:
            m["inicio"] = min(filter(None, [m["inicio"], ts]))
            m["fim"] = max(filter(None, [m["fim"], ts]))
        m["eventos"] += n_evento
        m["decisoes"] += n_decisao
        if parametros:
            m["parametros"].add(json.dumps(parametros, ensure_ascii=False, sort_keys=True))

    papeis = {}
    prompts = {}
    validacoes, portoes, custos, sem_custo, estimativas = [], [], [], [], []
    # Para as seções 6 e 7: abertura e último fechamento de cada pendência, última decisão de cada
    # portão (portao ou etapa_nao_aplicavel), última consolidação do RoB por ferramenta e os últimos
    # efeitos_verificados e caixa_gerada.
    aberturas, fechamentos, decisoes_portao, rob, ultimos = {}, {}, {}, {}, {}
    for ev in eventos:
        ator = ev.get("ator") or {}
        tipo, etapa = ator.get("tipo"), ev.get("etapa")
        dados = ev.get("dados") or {}
        nome = ev.get("evento")
        if nome == "pendencia_aberta" and dados.get("pendencia"):
            aberturas.setdefault(dados["pendencia"], ev)
        elif nome == "pendencia_fechada" and dados.get("pendencia"):
            fechamentos[dados["pendencia"]] = ev
        elif nome in ("portao", "etapa_nao_aplicavel") and dados.get("portao"):
            decisoes_portao[dados["portao"]] = ev
        elif nome == "rob_consolidado":
            rob[dados.get("ferramenta")] = ev
        elif nome in ("efeitos_verificados", "caixa_gerada"):
            ultimos[nome] = ev
        if tipo in TIPOS_IA or ator.get("modelo"):
            anotar_modelo(ator.get("modelo"), tipo, etapa, ev.get("ts"), n_evento=1,
                          parametros=dados.get("parametros"))
        chave_papel = (etapa, tipo, ator.get("id"))
        p = papeis.setdefault(chave_papel, {"eventos": set(), "n": 0})
        p["eventos"].add(ev.get("evento"))
        p["n"] += 1
        for art in ev.get("artefatos") or []:
            caminho = art.get("caminho", "")
            if caminho.startswith(PASTAS_PROMPT) and (caminho.endswith((".md", ".txt", ".json", ".csv"))):
                prompts.setdefault((caminho, art.get("sha256", "")), ev.get("seq"))
        for k in ("prompt_sha", "criterios_sha"):
            valor = dados.get(k)
            if isinstance(valor, dict):  # triagem via API grava {"revisor": sha, "arbitro": sha}
                for papel, sha in sorted(valor.items()):
                    if isinstance(sha, str) and sha:
                        prompts.setdefault((f"{k} {papel} (evento {ev.get('evento')})", sha), ev.get("seq"))
            elif isinstance(valor, str) and valor:
                prompts.setdefault((f"{k} (evento {ev.get('evento')})", valor), ev.get("seq"))
        if ev.get("evento") == "validacao_calculada":
            validacoes.append(ev)
        if ev.get("evento") == "portao":
            portoes.append(ev)
        if dados.get("tipo") == TIPO_ESTIMATIVA_CUSTO:
            estimativas.append(ev)
            continue
        valor = next((float(dados[k]) for k in CHAVES_CUSTO
                      if isinstance(dados.get(k), (int, float)) and not isinstance(dados.get(k), bool)), None)
        if valor is not None:  # uma chave por evento: custo_usd e custo_estimado_usd juntos não somam duas vezes
            custos.append((ev.get("seq"), ev.get("evento"), valor, "evento"))
            continue
        calculado = custo_de_uso_tokens(dados)
        if calculado is not None:
            custos.append((ev.get("seq"), ev.get("evento"), calculado[0], calculado[1]))
        elif (tipo == "ia_api" and not isinstance(dados.get("uso_tokens"), dict)) or _houve_chamadas(dados):
            sem_custo.append(ev.get("seq"))  # houve (ou pode ter havido) chamada paga sem custo apurável
    for d in decisoes:
        tipo = d.get("tipo_ator")
        if tipo in TIPOS_IA or d.get("modelo"):
            anotar_modelo(d.get("modelo"), tipo, f"decisões {d.get('etapa')}", d.get("ts"), n_decisao=1)
        if d.get("prompt_sha"):
            prompts.setdefault((f"prompt da rodada {d.get('rodada')} ({d.get('revisor')})", d["prompt_sha"]), None)
    return {"eventos": eventos, "decisoes": decisoes, "estado": est, "modelos": modelos, "papeis": papeis,
            "prompts": prompts, "validacoes": validacoes, "portoes": portoes, "custos": custos,
            "sem_custo": sem_custo, "estimativas": estimativas, "aberturas": aberturas, "fechamentos": fechamentos,
            "sucessoras": sucessoras_de_pendencias(est, aberturas, fechamentos), "decisoes_portao": decisoes_portao,
            "rob": rob, "ultimos": ultimos, "certeza": ler_certezas(raiz)}


# ---------------------------------------------------------------------------
# Pendências: sucessoras e notas sobre as citadas (seção 6)
# ---------------------------------------------------------------------------
def sucessoras_de_pendencias(est, aberturas, fechamentos):
    """{antiga: nova} pelo "[substitui Pxxx]" da abertura da nova e pelo "substituída por Pxxx" do fechamento da antiga.

    Só liga pendências do mesmo tipo e nunca sobrescreve uma ligação já feita (a primeira no log vale):
    a confirmação de portão copia o "[substitui ...]" de outra pendência sem substituí-la.
    """
    tipos = {pid: (ev.get("dados") or {}).get("tipo") for pid, ev in aberturas.items()}
    tipos.update({p.get("id"): p.get("tipo") for p in est.get("pendencias", []) if p.get("id") and p.get("tipo")})
    ligacoes = []
    for pid, ev in aberturas.items():
        m = RE_SUBSTITUI.search(str((ev.get("dados") or {}).get("descricao") or ""))
        if m:
            ligacoes.append((int(ev.get("seq") or 0), m.group(1), pid))
    for pid, ev in fechamentos.items():
        m = RE_SUBSTITUIDA_POR.search(str(ev.get("motivo") or ""))
        if m:
            ligacoes.append((int(ev.get("seq") or 0), pid, m.group(1)))
    sucessoras = {}
    for _, antiga, nova in sorted(ligacoes):
        if antiga != nova and tipos.get(antiga) and tipos.get(antiga) == tipos.get(nova):
            sucessoras.setdefault(antiga, nova)
    return sucessoras


def cadeia_de_sucessoras(pid, sucessoras):
    """[P1, P2, ...]: sucessoras de `pid` em ordem, sem repetir (um ciclo no log não trava o laço)."""
    cadeia, vistos = [], {pid}
    atual = sucessoras.get(pid)
    while atual and atual not in vistos:
        cadeia.append(atual)
        vistos.add(atual)
        atual = sucessoras.get(atual)
    return cadeia


def _quando(ev):
    return f"{_data(ev.get('ts'))} (seq {ev.get('seq')})"


def notas_citadas(pid, descricao, dados, ids_abertas):
    """Notas "[Pxxx: fechada em ...; substituída por ... , situação]" das pendências citadas já fechadas.

    Pula a própria pendência, as citadas ainda abertas (ou sem fechamento no log) e a citada cuja
    cadeia de sucessoras chega à própria pendência (ela substituiu a citada).
    """
    fechamentos, sucessoras = dados["fechamentos"], dados["sucessoras"]
    notas = []
    for citada in dict.fromkeys(RE_PENDENCIA.findall(str(descricao or ""))):
        if citada == pid or citada in ids_abertas or citada not in fechamentos:
            continue
        cadeia = cadeia_de_sucessoras(citada, sucessoras)
        if pid in cadeia:
            continue
        nota = f"{citada}: fechada em {_quando(fechamentos[citada])}"
        if cadeia:
            ultima = cadeia[-1]
            if ultima in ids_abertas:
                situacao = "aberta"
            elif ultima in fechamentos:
                situacao = f"fechada em {_data(fechamentos[ultima].get('ts'))}"
            else:
                situacao = "situação não registrada"
            nota += f"; substituída por {' → '.join(cadeia)}, {situacao}"
        notas.append(f"[{nota}]")
    return notas


# ---------------------------------------------------------------------------
# Certeza (GRADE/CERQual) e responsabilidade humana (seção 7)
# ---------------------------------------------------------------------------
def ler_certezas(raiz):
    """[{arquivo, sha256, n_linhas, n_sem_validacao, sem_coluna, erro}] dos certeza*.csv da pasta de esquema.ARQ_CERTEZA.

    Só a própria pasta: subpastas guardam versões superadas e sensibilidades, que não são o juízo relatado.
    Arquivo sem a coluna `validado_humano` fica com `sem_coluna` e sem contagem: a caixa (caixa._validado)
    trata esse caso como formato anterior e não o rebaixa a rascunho, e a declaração segue a mesma regra
    para que caixa, PRISMA e declaração concordem sobre a marca; ele só é citado na seção 7.
    """
    pasta_rel = Path(esquema.ARQ_CERTEZA).parent
    pasta = Path(raiz) / pasta_rel
    saida = []
    if not pasta.is_dir():
        return saida
    for caminho in sorted(pasta.glob("certeza*.csv")):
        if not caminho.is_file():
            continue
        item = {"arquivo": (pasta_rel / caminho.name).as_posix(), "sha256": estado.sha256_arquivo(caminho),
                "n_linhas": None, "n_sem_validacao": None, "sem_coluna": False, "erro": None}
        try:
            colunas, linhas = ler_csv(caminho)
        except (OSError, UnicodeDecodeError, csv.Error) as e:
            item["erro"] = type(e).__name__
        else:
            item["n_linhas"] = len(linhas)
            if "validado_humano" in colunas:
                item["n_sem_validacao"] = sum(1 for l in linhas if not sim(l.get("validado_humano", "")))
            else:
                item["sem_coluna"] = True
        saida.append(item)
    return saida


def _ordem_portao(g):
    ordem = list(esquema.PORTOES)
    return (ordem.index(g) if g in ordem else len(ordem), str(g))


def _ordem_etapa(etapa):
    return (esquema.ETAPAS.index(etapa) if etapa in esquema.ETAPAS else len(esquema.ETAPAS), str(etapa or ""))


def situacao_portoes(dados, ids_abertas):
    """(pendentes, confirmados) dos portões cuja última decisão é aprovação por ator não humano.

    pendentes: [(g, evento, [pendências abertas] ou [])], com lista vazia quando não há confirmação humana
    registrada; confirmados: [(g, pendência, evento de fechamento)] quando a última pendência de confirmação
    do portão foi fechada por humano depois da aprovação.
    """
    pendencias = dados["estado"].get("pendencias", [])
    pendentes, confirmados = [], []
    for g, ev in sorted(dados["decisoes_portao"].items(), key=lambda kv: _ordem_portao(kv[0])):
        d = ev.get("dados") or {}
        if (ev.get("evento") != "portao" or d.get("decisao", "aprovado") != "aprovado"
                or (ev.get("ator") or {}).get("tipo") == "humano"):
            continue
        do_portao = [p.get("id") for p in pendencias if p.get("tipo") == TIPO_PENDENCIA_PORTAO and p.get("portao") == g]
        abertas_g = [pid for pid in do_portao if pid in ids_abertas]
        if abertas_g:
            pendentes.append((g, ev, abertas_g))
            continue
        ultima = max(do_portao, key=lambda pid: int((dados["aberturas"].get(pid) or {}).get("seq") or 0), default=None)
        fecho = dados["fechamentos"].get(ultima) if ultima else None
        if (fecho and (fecho.get("ator") or {}).get("tipo") == "humano"
                and int(fecho.get("seq") or 0) > int(ev.get("seq") or 0)):
            confirmados.append((g, ultima, fecho))
        else:
            pendentes.append((g, ev, []))
    return pendentes, confirmados


def responsabilidade(dados, abertas, falhas_validacao, sem_validacao):
    """Itens da seção 7: {juizos, triagem, outras, confirmados, completos, sem_coluna} (listas de texto).

    `juizos` são os juízos de IA sem validação humana registrada (entram no motivo de rascunho);
    `triagem` repete os problemas da validação da triagem (seção 4); `outras` são as pendências abertas
    que não são confirmação de portão já listada, por etapa.
    """
    ids_abertas = {p.get("id") for p in abertas}
    juizos, triagem, outras, confirmados, completos, sem_coluna = [], [], [], [], [], []

    ef = dados["ultimos"].get("efeitos_verificados")
    if ef:
        d = ef.get("dados") or {}
        n_ef, n_nao = d.get("n_efeitos"), d.get("n_nao_aptos")
        if isinstance(n_ef, int) and isinstance(n_nao, int) and n_ef > 0:
            origem = f"`efeitos_verificados`, seq {ef.get('seq')}, {_data(ef.get('ts'))}"
            if n_nao == 0:
                completos.append(f"dados de efeito, {n_ef} de {n_ef} efeitos verificados por humano na página do PDF "
                                 f"e aptos para o G7 ({origem})")
            else:
                juizos.append(f"Dados de efeito: {n_nao} de {n_ef} efeitos não aptos para o G7 (sem `verificado_humano` "
                              f"ou com trecho ou plausibilidade a corrigir; {origem}).")

    for ferramenta, ev in sorted(dados["rob"].items(), key=lambda kv: int(kv[1].get("seq") or 0)):
        d = ev.get("dados") or {}
        rotulo = ferramenta or "sem ferramenta no evento"
        origem = f"`rob_consolidado`, seq {ev.get('seq')}, {_data(ev.get('ts'))}"
        n_res, n_val = d.get("n_resultados"), d.get("n_validados_humano")
        contagem = isinstance(n_res, int) and isinstance(n_val, int)
        if d.get("todos_validados_humano") is True:
            completos.append(f"risco de viés ({rotulo}), " + (f"{n_val} de {n_res} resultados " if contagem else "")
                             + f"({origem})")
        else:
            qtd = f"{n_res - n_val} de {n_res} resultados" if contagem else "resultados"
            juizos.append(f"Risco de viés ({rotulo}): {qtd} sem validação humana na consolidação ({origem}); "
                          "a concordância entre avaliadores de IA não valida.")

    for c in dados["certeza"]:
        local = f"`{c['arquivo']}` (sha256 `{c['sha256'][:16]}…`)"
        if c["erro"]:
            juizos.append(f"Certeza da evidência (GRADE/CERQual) em {local}: arquivo ilegível ({c['erro']}), "
                          "validação humana não verificável.")
        elif c["sem_coluna"]:
            sem_coluna.append(local)
        elif c["n_sem_validacao"]:
            juizos.append(f"Certeza da evidência (GRADE/CERQual) em {local}: {c['n_sem_validacao']} de "
                          f"{c['n_linhas']} linhas sem `validado_humano`.")
        elif c["n_linhas"]:
            completos.append(f"certeza da evidência em {local}, {c['n_linhas']} de {c['n_linhas']} linhas")

    cx = dados["ultimos"].get("caixa_gerada")
    if cx:
        d = cx.get("dados") or {}
        n_lin, n_pend = d.get("n_linhas"), d.get("n_pendentes")
        origem = f"`caixa_gerada`, seq {cx.get('seq')}, {_data(cx.get('ts'))}"
        if isinstance(n_pend, int) and n_pend > 0:
            total = f" de {n_lin}" if isinstance(n_lin, int) else ""
            juizos.append(f"Rótulos da caixa de ferramentas: {n_pend}{total} linhas pendentes ou em rascunho ({origem}).")
        elif isinstance(n_pend, int) and isinstance(n_lin, int) and n_lin > 0:
            completos.append(f"rótulos da caixa de ferramentas, {n_lin} de {n_lin} linhas definidas ({origem})")

    pendentes, confirmados_ev = situacao_portoes(dados, ids_abertas)
    listadas = set()
    for g, ev, pids in pendentes:
        ator = ev.get("ator") or {}
        inicio = (f"Portão {g} ({ev.get('etapa')}), aprovado por {ator.get('id')} ({ator.get('tipo')}) em "
                  f"{_quando(ev)}: ")
        if pids:
            listadas.update(pids)
            juizos.append(inicio + f"confirmação humana pendente ({', '.join(pids)}).")
        else:
            juizos.append(inicio + "sem confirmação humana registrada.")
    for g, pid, fecho in confirmados_ev:
        confirmados.append(f"{g} ({pid}, fechada em {_data(fecho.get('ts'))}, seq {fecho.get('seq')})")

    for v in falhas_validacao:
        triagem.append(f"Validação que decide abaixo dos limiares: seq {v.get('seq')}, etapa {etapa_evento(v)}, rodada "
                       f"{(v.get('dados') or {}).get('rodada') or 'não registrada'} (seção 4).")
    if sem_validacao:
        triagem.append("Triagem de títulos e resumos: decisões de IA sem validação calculada com finalidade validação "
                       "da rodada ativa (seção 4).")

    por_etapa = {}
    for p in abertas:
        if p.get("id") not in listadas:
            por_etapa.setdefault(p.get("etapa"), []).append(p)
    for etapa in sorted(por_etapa, key=_ordem_etapa):
        lista = ", ".join(f"{p.get('id')} ({p.get('tipo')})" for p in por_etapa[etapa])
        outras.append(f"Pendências abertas em {ROTULO_ETAPA.get(etapa, etapa or 'etapa não registrada')} "
                      f"({etapa or 'sem etapa'}): {lista}; descrição na seção 6.")
    return {"juizos": juizos, "triagem": triagem, "outras": outras, "confirmados": confirmados, "completos": completos,
            "sem_coluna": sem_coluna}


def secao_responsabilidade(itens):
    """Linhas da seção 7: o texto de sempre sem nada em aberto; senão, a exceção listada item a item."""
    md = ["## 7. Declaração de responsabilidade", ""]
    if not (itens["juizos"] or itens["triagem"] or itens["outras"]):
        return md + [TEXTO_RESPONSABILIDADE, ""]
    md += ["As ferramentas de IA listadas foram usadas como apoio sob supervisão humana. A decisão de usar IA e a "
           "forma de uso, os critérios, o protocolo e as conclusões são responsabilidade dos revisores humanos, que "
           "conferiram as saídas conforme os portões e as validações acima, exceto nos juízos listados abaixo: eles "
           "foram feitos por IA sem validação humana registrada, são rascunhos de IA e devem ser relatados como "
           "tais.", ""]
    md += [f"- {item}" for item in itens["juizos"] + itens["triagem"] + itens["outras"]] + [""]
    if itens["confirmados"]:
        md += ["Portões aprovados sem humano e confirmados depois por humano: " + "; ".join(itens["confirmados"]) + ".",
               ""]
    if itens["completos"]:
        md += ["Validação humana completa registrada: " + "; ".join(itens["completos"]) + ".", ""]
    if itens["sem_coluna"]:
        md += ["Certeza sem a coluna `validado_humano`, onde a validação humana não fica registrada (formato anterior; "
               "como na caixa de ferramentas, não conta como rascunho): " + "; ".join(itens["sem_coluna"]) + ".", ""]
    return md + [FECHO_RESPONSABILIDADE, ""]


# ---------------------------------------------------------------------------
# Custo de API
# ---------------------------------------------------------------------------
def _houve_chamadas(dados):
    uso = dados.get("uso_tokens")
    return isinstance(uso, dict) and any(isinstance(u, dict) and (u.get("chamadas") or 0) > 0 for u in uso.values())


def custo_de_uso_tokens(dados):
    """(US$, origem) a partir de `uso_tokens` × preços, ou None se não houver tokens ou preço para algum modelo."""
    if not _houve_chamadas(dados):
        return None
    modelos = dados.get("modelos") or {}
    tabela = dados.get("tabela_precos") or None
    desconto = dados.get("desconto_lote")
    if not isinstance(desconto, (int, float)):
        desconto = 1.0
        if dados.get("modo") == "lote":
            try:
                from . import triagem_api
                desconto = triagem_api.DESCONTO_LOTE
            except ImportError:  # pragma: no cover
                desconto = 0.5
    total = 0.0
    for papel, uso in dados["uso_tokens"].items():
        if not isinstance(uso, dict) or not (uso.get("chamadas") or 0):
            continue
        valor = provedores.preco(modelos.get(papel) or "", tabela) if tabela else provedores.preco(modelos.get(papel) or "")
        if valor is None:
            return None
        total += desconto * ((uso.get("tokens_entrada") or 0) * valor[0] + (uso.get("tokens_saida") or 0) * valor[1]) / 1e6
    origem = "tokens × tabela do evento" if tabela else \
        f"tokens × tabela atual da skill ({provedores.PRECOS_CONSULTADOS_EM})"
    return round(total, 6), origem


# ---------------------------------------------------------------------------
# Validação que decide
# ---------------------------------------------------------------------------
def finalidade_evento(ev):
    """Finalidade de um `validacao_calculada`; eventos antigos sem ela contam como validação."""
    dados = ev.get("dados") or {}
    if dados.get("finalidade"):
        return dados["finalidade"]
    if dados.get("tipo") in ("elusao", "estabilidade"):
        return dados["tipo"]
    return "validacao"


def etapa_evento(ev):
    dados = ev.get("dados") or {}
    return dados.get("etapa") or ETAPA_DECISAO_DO_PROJETO.get(ev.get("etapa")) or ev.get("etapa")


def rodadas_ativas(eventos, est, etapa):
    """Rodadas que valem para a etapa: a ativa do estado e as da última consolidação que a contém."""
    ativa = (est.get("versoes_ativas") or {}).get(tl.chave_rodada_ativa(etapa))
    if not ativa:
        return None
    for ev in reversed(eventos):
        dados = ev.get("dados") or {}
        if ev.get("evento") == "triagem_consolidada" and dados.get("etapa", "ta") == etapa:
            rodadas = dados.get("rodadas") or []
            return set(rodadas) if ativa in rodadas else {ativa}
    return {ativa}


def validacoes_que_decidem(eventos, validacoes, est):
    """{etapa: evento}: por etapa, a última validação com finalidade `validacao` da rodada ativa."""
    decisoras = {}
    for ev in validacoes:
        if finalidade_evento(ev) != "validacao":
            continue
        etapa = etapa_evento(ev)
        rodadas = rodadas_ativas(eventos, est, etapa)
        rodada = (ev.get("dados") or {}).get("rodada")
        if rodadas and rodada and rodada not in rodadas:
            continue
        decisoras[etapa] = ev
    return decisoras


def ultimo_seq_coberto(eventos):
    """Último seq do log que a declaração cobre (os eventos da própria declaração já vêm excluídos)."""
    return max([int(e.get("seq", 0) or 0) for e in eventos] or [0])


def gerar_markdown(raiz, dados):
    est = dados["estado"]
    eventos = dados["eventos"]
    abertas = estado.pendencias_abertas(est)
    decisoras = validacoes_que_decidem(eventos, dados["validacoes"], est)
    falhas_validacao = [v for v in decisoras.values() if (v.get("dados") or {}).get("atende_limiares") is False]
    ia_na_triagem = any((d.get("tipo_ator") in TIPOS_IA) and d.get("etapa") == "ta" for d in dados["decisoes"])
    sem_validacao = ia_na_triagem and "ta" not in decisoras
    itens_responsabilidade = responsabilidade(dados, abertas, falhas_validacao, sem_validacao)
    rascunho = bool(abertas or falhas_validacao or sem_validacao or itens_responsabilidade["juizos"])
    ultimo_seq = ultimo_seq_coberto(eventos)
    sha_log = estado.sha256_texto("".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in eventos))

    md = ["# Declaração de uso de inteligência artificial", ""]
    if rascunho:
        motivos = []
        if abertas:
            motivos.append(f"{len(abertas)} pendências abertas")
        if falhas_validacao:
            quais = ", ".join(f"seq {v.get('seq')}, etapa {etapa_evento(v)}, rodada "
                              f"{(v.get('dados') or {}).get('rodada') or 'não registrada'}" for v in falhas_validacao)
            motivos.append(f"{len(falhas_validacao)} validações abaixo dos limiares (a que decide: {quais})")
        if sem_validacao:
            motivos.append("decisões de IA na triagem sem validação calculada com finalidade validação "
                           "da rodada ativa")
        if itens_responsabilidade["juizos"]:
            motivos.append(MOTIVO_JUIZOS)
        md += [f"**{esquema.MARCA_RASCUNHO}** ({'; '.join(motivos)}).", ""]
    projeto, modo = est["projeto"], est.get("modo", {})
    md += [f"Projeto: {projeto.get('titulo', '')}. Tipo de revisão: {projeto.get('tipo_revisao', '')}. "
           f"Modo de autonomia: {modo.get('autonomia', '')}; triagem: {modo.get('triagem', '')}.", "",
           f"Gerado a partir de `{esquema.ARQ_LOG}` até o evento seq {ultimo_seq} "
           f"(sha256 dos eventos `{sha_log[:16]}…`) e de `{esquema.ARQ_DECISOES}` "
           f"({len(dados['decisoes'])} decisões). Nenhum número foi digitado à mão.", ""]

    md += ["## 1. Ferramentas e modelos", ""]
    if not dados["modelos"]:
        md += ["Nenhum uso de IA registrado no log.", ""]
    else:
        linhas = []
        for nome, m in sorted(dados["modelos"].items()):
            linhas.append([nome, ", ".join(sorted(m["tipos"])), ", ".join(sorted(m["etapas"])), _data(m["inicio"]),
                           _data(m["fim"]), m["eventos"], m["decisoes"],
                           "; ".join(sorted(m["parametros"])) or "não registrados"])
        md += _tabela(["Modelo", "Tipo de ator", "Etapas", "Primeiro uso", "Último uso", "Eventos", "Decisões",
                       "Parâmetros"], linhas)

    md += ["## 2. Papéis por etapa", ""]
    linhas = [[etapa, tipo, ator_id, ", ".join(sorted(p["eventos"])), p["n"]]
              for (etapa, tipo, ator_id), p in sorted(dados["papeis"].items(), key=lambda kv: tuple(map(str, kv[0])))]
    md += _tabela(["Etapa", "Tipo de ator", "Papel", "Eventos", "N"], linhas)

    md += ["## 3. Prompts, critérios e instrumentos arquivados", ""]
    linhas = [[nome, f"`{sha[:16]}`" if sha else "sem hash", seq if seq is not None else "decisoes.jsonl"]
              for (nome, sha), seq in sorted(dados["prompts"].items(), key=lambda kv: kv[0])]
    md += _tabela(["Arquivo ou referência", "sha256 (prefixo)", "Primeiro evento (seq)"], linhas)
    versoes = est.get("versoes_ativas") or {}
    if versoes:
        md += ["Versões ativas no estado: " + "; ".join(f"{k} = {v}" for k, v in sorted(versoes.items())) + ".", ""]

    md += ["## 4. Validação do uso de IA", "", "Limiares de referência (references/ia-validacao.md da skill):", ""]
    md += [f"- {l}" for l in LIMIARES_REFERENCIA] + [""]
    if not dados["validacoes"]:
        md += ["_Nenhuma validação calculada no log._", ""]
    for etapa, v in sorted(decisoras.items()):
        d = v.get("dados") or {}
        atende = d.get("atende_limiares")
        texto_atende = "sim" if atende is True else ("não" if atende is False else "não informado")
        md += [f"### Validação que decide: seq {v.get('seq')} ({_data(v.get('ts'))}, etapa {v.get('etapa')}, "
               f"rodada {d.get('rodada') or 'não registrada'})", "",
               f"Atende aos limiares: **{texto_atende}**.", ""]
        md += _tabela(["Métrica", "Valor"], [[k, val] for k, val in _achatar(d) if k != "atende_limiares"])
    if dados["validacoes"] and "ta" not in decisoras and ia_na_triagem:
        ativa = (est.get("versoes_ativas") or {}).get(esquema.VERSAO_ATIVA_RODADA_TA)
        md += [f"_Nenhuma validação com finalidade validação da rodada ativa ({ativa or 'não definida'})._", ""]
    ids_decisoras = {id(v) for v in decisoras.values()}
    historico = [v for v in dados["validacoes"]
                 if id(v) not in ids_decisoras and finalidade_evento(v) not in ("elusao", "estabilidade")]
    if historico:
        md += ["### Histórico: calibração, desenvolvimento e validações que não decidem", "",
               "Não entram na marca de rascunho: calibração e desenvolvimento reprovados são o caminho até a "
               "validação (references/ia-validacao.md, seção 4, passos A e B); validações antigas foram substituídas "
               "pela que decide.", ""]
        linhas = []
        for v in historico:
            d = v.get("dados") or {}
            atende = d.get("atende_limiares")
            linhas.append([v.get("seq"), _data(v.get("ts")), etapa_evento(v),
                           ROTULO_FINALIDADE.get(finalidade_evento(v), finalidade_evento(v)),
                           d.get("rodada") or "", d.get("amostra_id") or "",
                           "sim" if atende is True else ("não" if atende is False else "não informado"),
                           _num(d.get("sensibilidade")), _num(d.get("kappa_humanos")),
                           _num(d.get("concordancia_humanos"))])
        md += _tabela(["Seq", "Data", "Etapa", "Finalidade", "Rodada", "Amostra", "Atende", "Sensibilidade",
                       "κ humanos", "Concordância humanos"], linhas)
    outras = [v for v in dados["validacoes"] if finalidade_evento(v) in ("elusao", "estabilidade")]
    if outras:
        md += ["### Elusão e estabilidade", ""]
        linhas = []
        for v in outras:
            d = v.get("dados") or {}
            linhas.append([v.get("seq"), _data(v.get("ts")), ROTULO_FINALIDADE.get(finalidade_evento(v)),
                           d.get("rodada") or "", d.get("amostra_id") or d.get("rodada_reexecucao") or "",
                           _num(d.get("elusao")) if not isinstance(d.get("elusao"), dict) else "ver métricas",
                           _num(d.get("perdidos_estimados")), d.get("n_codificados") or d.get("n_ids") or ""])
        md += _tabela(["Seq", "Data", "Finalidade", "Rodada", "Amostra ou reexecução", "Taxa de elusão",
                       "Perdidos estimados", "N"], linhas)
    elusao = [v for v in dados["validacoes"]
              if finalidade_evento(v) == "elusao" or isinstance((v.get("dados") or {}).get("elusao"), dict)]
    md += [f"Amostras de elusão registradas: {len(elusao)}.", ""]

    md += ["## 5. Portões e responsabilidade humana", ""]
    linhas = [[(p.get("dados") or {}).get("portao"), p.get("etapa"), (p.get("ator") or {}).get("tipo"),
               (p.get("ator") or {}).get("id"), _data(p.get("ts")), p.get("motivo") or ""] for p in dados["portoes"]]
    md += _tabela(["Portão", "Etapa", "Tipo de ator", "Aprovado por", "Data", "Motivo"], linhas)
    total_custo = sum(c for _, _, c, _ in dados["custos"])
    custo = f"US$ {total_custo:.2f} em {len(dados['custos'])} eventos" if dados["custos"] else "não registrado"
    md += [f"Custo de API registrado: {custo}.", ""]
    calculados = [(seq, origem) for seq, _, _, origem in dados["custos"] if origem != "evento"]
    if calculados:
        md += [f"Custo calculado a partir de `uso_tokens` em {len(calculados)} eventos ("
               + "; ".join(f"seq {s}: {o}" for s, o in calculados[:10]) + ").", ""]
    if dados["sem_custo"]:
        md += [f"Uso de API sem custo nem tokens com preço registrados em {len(dados['sem_custo'])} eventos "
               f"(seq {', '.join(str(s) for s in dados['sem_custo'][:20])}): custo não registrado.", ""]
    if not dados["custos"] and not dados["sem_custo"]:
        md += ["Nenhum evento do log traz custo ou uso de tokens de API. A triagem por subagentes do Claude Code "
               "não registra custo por chamada.", ""]
    if dados["estimativas"]:
        ultima = dados["estimativas"][-1]
        valor = ((ultima.get("dados") or {}).get("estimativa") or {}).get("custo_total_usd")
        md += [f"Estimativas prévias (`triagem api --estimar`, não somadas ao custo): {len(dados['estimativas'])}; "
               f"última seq {ultima.get('seq')}"
               + (f", US$ {valor:.2f}" if isinstance(valor, (int, float)) else "") + ".", ""]

    md += ["## 6. Pendências abertas", ""]
    if abertas:
        ids_abertas = {p.get("id") for p in abertas}
        md += ["As descrições estão como foram registradas na abertura de cada pendência (data e seq do evento "
               "`pendencia_aberta` na coluna \"Aberta em\"): contagens e pendências citadas podem ter mudado desde "
               "então. Pendências citadas que já foram fechadas levam, entre colchetes, o fechamento e as sucessoras; "
               "a seção 7 traz o estado atual.", ""]
        linhas = []
        for p in abertas:
            abertura = dados["aberturas"].get(p.get("id"))
            descricao = " ".join([str(p.get("descricao") or "")]
                                 + notas_citadas(p.get("id"), p.get("descricao"), dados, ids_abertas))
            linhas.append([p.get("id"), p.get("tipo"), p.get("etapa"), p.get("portao"),
                           _quando(abertura) if abertura else "não registrado", descricao, p.get("n")])
        md += _tabela(["Id", "Tipo", "Etapa", "Portão", "Aberta em", "Descrição (como registrada na abertura)", "N"],
                      linhas)
    else:
        md += ["Nenhuma.", ""]

    md += secao_responsabilidade(itens_responsabilidade)
    return "\n".join(md), rascunho


def cmd_declaracao_ia(args):
    comando = "declaracao-ia"
    raiz = exigir_raiz(args, comando)
    if raiz is None:
        return 1
    try:
        dados = coletar(raiz)
    except estado.ErroProjeto as e:
        print(f"erro: {e}", file=sys.stderr)
        estado.resumo({"comando": comando, "ok": False, "erro": "estado_invalido", "detalhe": str(e)})
        return 1
    texto, rascunho = gerar_markdown(raiz, dados)
    saida = resolver_caminho(raiz, args.out)
    anterior = saida.read_text(encoding="utf-8") if saida.exists() else None
    if anterior != texto:
        estado.escrever_atomico(saida, texto, newline="")
    rel = relativo(raiz, saida)
    if anterior != texto:
        estado.registrar_evento(raiz, "relatorio_gerado", "11_relato", "script", ATOR,
                                dados={"produto": "declaracao_uso_ia", "rascunho": rascunho,
                                       "n_modelos": len(dados["modelos"]), "n_validacoes": len(dados["validacoes"]),
                                       "ultimo_seq": ultimo_seq_coberto(dados["eventos"])},
                                artefatos=[rel, esquema.ARQ_LOG] + [c["arquivo"] for c in dados["certeza"]])
    estado.resumo({"comando": comando, "ok": True, "arquivo": rel, "rascunho": rascunho,
                   "modelos": sorted(dados["modelos"]), "n_validacoes": len(dados["validacoes"]),
                   "n_pendencias_abertas": len(estado.pendencias_abertas(dados["estado"]))})
    return 0


def registrar(subparsers):
    p = subparsers.add_parser("declaracao-ia", help="gera 07-relatorio/declaracao_uso_ia.md a partir do log")
    p.add_argument("--out", default=ARQ_DECLARACAO)
    p.set_defaults(func=cmd_declaracao_ia)
