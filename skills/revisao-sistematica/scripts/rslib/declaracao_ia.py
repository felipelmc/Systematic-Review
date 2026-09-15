"""Declaração de uso de IA gerada do log do projeto (RAISE / PRISMA-trAIce).

USO
    python3 rs.py declaracao-ia [--out 07-relatorio/declaracao_uso_ia.md]

Lê `rs_log.jsonl`, `dados/decisoes.jsonl` e `rs_estado.json` e escreve um Markdown com:
    1. ferramentas e modelos (tipo de ator, etapas, primeira e última data, nº de
       eventos e de decisões, parâmetros registrados);
    2. papel da IA e dos humanos por etapa;
    3. prompts, critérios e codebooks arquivados com sha256 (artefatos do log e
       `prompt_sha` das decisões);
    4. validação: a validação que decide (métricas, IC, limiares e se atendeu), o histórico
       de calibração e desenvolvimento, elusão e estabilidade;
    5. portões (quem aprovou, humano ou autopiloto) e custo de API;
    6. pendências abertas e a marca RASCUNHO NÃO VALIDADO quando couber;
    7. declaração de responsabilidade humana.

Por que gerar do log e não escrever à mão: a declaração só é verificável se cada
número remeter a um evento com seq e hash. Nada é digitado; o que o log não tem
aparece como "não registrado", o que também denuncia lacunas do processo.

A marca de rascunho aparece quando há pendências abertas, quando a validação que
decide não atingiu os limiares, ou quando houve decisão de IA na triagem sem validação
que decide (references/ia-validacao.md, seção 7). A validação que decide é, por etapa, a última
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

import json
import sys
from pathlib import Path

from . import esquema, estado, provedores
from . import triagem_lotes as tl
from .handoff import exigir_raiz, relativo, resolver_caminho

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
    """Estruturas da declaração a partir do log, das decisões e do estado."""
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
    for ev in eventos:
        ator = ev.get("ator") or {}
        tipo, etapa = ator.get("tipo"), ev.get("etapa")
        dados = ev.get("dados") or {}
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
            "sem_custo": sem_custo, "estimativas": estimativas}


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
    rascunho = bool(abertas or falhas_validacao or sem_validacao)
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
    md += _tabela(["Id", "Tipo", "Etapa", "Portão", "Descrição", "N"],
                  [[p.get("id"), p.get("tipo"), p.get("etapa"), p.get("portao"), p.get("descricao"), p.get("n")]
                   for p in abertas]) if abertas else ["Nenhuma.", ""]

    md += ["## 7. Declaração de responsabilidade", "",
           "As ferramentas de IA listadas foram usadas como apoio sob supervisão humana. Critérios, protocolo, "
           "juízos de risco de viés, de certeza (GRADE/CERQual), rótulos da caixa de ferramentas e conclusões são "
           "responsabilidade dos revisores humanos, que conferiram as saídas conforme os portões e as validações "
           "acima. Decisões de IA não validadas estão sinalizadas como pendências.", ""]
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
                                artefatos=[rel, esquema.ARQ_LOG])
    estado.resumo({"comando": comando, "ok": True, "arquivo": rel, "rascunho": rascunho,
                   "modelos": sorted(dados["modelos"]), "n_validacoes": len(dados["validacoes"]),
                   "n_pendencias_abertas": len(estado.pendencias_abertas(dados["estado"]))})
    return 0


def registrar(subparsers):
    p = subparsers.add_parser("declaracao-ia", help="gera 07-relatorio/declaracao_uso_ia.md a partir do log")
    p.add_argument("--out", default=ARQ_DECLARACAO)
    p.set_defaults(func=cmd_declaracao_ia)
