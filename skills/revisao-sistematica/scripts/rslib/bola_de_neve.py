"""Bola de neve para trás (referências) e para frente (citações) pelo OpenAlex.

USO
    python3 rs.py bola-de-neve --direcao tras|frente|ambas --rodada SN1 \
        [--ids sementes.csv] [--incluir-conhecidos] [--max-paginas-citacoes N] [--sem-importador]

Sementes
    Por padrão, os incluídos da elegibilidade em texto completo
    (`03-textos/elegibilidade_tc_final.csv`, decisao = incluir). `--ids` aceita um CSV
    com coluna `id_rs` (ou `chave`) para rodadas seguintes sobre os novos incluídos.
    O join com os metadados é sempre por `id_rs`/`chave`, nunca por título.

Resolução do W id do OpenAlex (nesta ordem)
    1. `id_fonte` já é um W id (registro veio do OpenAlex);
    2. DOI normalizado (`/works/doi:...`);
    3. título normalizado com similaridade >= 95 E mesmo ano de publicação. Sem ano,
       não há resolução por título: o risco de casar com outra obra homônima é alto
       demais para uma etapa que alimenta o PRISMA.
    Sementes não resolvidas ficam listadas em `01-busca/bola_de_neve/<rodada>_sementes.csv`.

Saída
    - `01-busca/brutos/<rodada>_openalex_citacao.jsonl` (obras novas, ordem estável);
    - `01-busca/bola_de_neve/<rodada>_proveniencia.csv` (cada obra encontrada, direção,
      sementes que a trouxeram, se já estava no corpus e se foi gravada);
    - registros em `dados/registros.csv` com `metodo_identificacao = citacao` e
      `busca_id = <rodada>` (pelo importador do projeto ou pela conversão interna).

Por que obras já presentes no corpus não são gravadas por padrão: o ramo "outros
métodos" do PRISMA 2020 conta registros identificados por citação que ainda não
estavam no conjunto triado; regravar referências já importadas das bases só geraria
duplicatas para o dedup. A proveniência guarda todas, e `--incluir-conhecidos`
grava tudo quando o protocolo pedir essa contagem.

Depois: `rs.py dedup` e re-triagem T/A dos novos registros com a MESMA versão dos
critérios (Apêndice D da base de conhecimento, item 12; references/04-textos-elegibilidade.md §9). Repita a rodada (SN2, SN3...) sobre os novos incluídos
até não haver novas inclusões.

Id da rodada e buscas substituídas
    `--rodada` vira `busca_id` e segue a MESMA regra do `rs.py importar` (letras
    maiúsculas + número: SN1, SN2), conferida antes de qualquer chamada à API; antes,
    uma rodada como `sn1` coletava tudo e só falhava na importação. Uma rodada
    substituída (`importar --substituir SN1`, `ativa: false`) é recusada, inclusive
    na reexecução.
    O "corpus conhecido" é o conjunto ATIVO: registros de buscas substituídas e
    clusters `busca_inativa` de registros_unicos.csv não contam, porque saíram do
    PRISMA; uma obra que só estava numa busca substituída é gravada como nova.
    Sementes com `busca_inativa` saem do conjunto padrão (incluídos no texto
    completo) com aviso; por `--ids` são aceitas, também com aviso.
"""

import re
from pathlib import Path

from . import esquema, estado, normalizar
from .importar import buscas as _buscas
from .importar.detectar import ErroImportacao
from .busca_openalex import (ClienteOpenAlex, ErroOpenAlex, criar_sessao, escrever_jsonl, id_curto,
                             importar_jsonl, ler_jsonl, registrar_busca)
from .handoff import (carregar_unicos, escrever_csv, exigir_raiz, falhar, ler_linhas, resolver_caminho)

ATOR = "rs.py bola-de-neve"
LIMIAR_TITULO = 95.0
COLUNAS_SEMENTES = ["id_rs", "chave", "doi", "id_openalex", "metodo_resolucao", "score_titulo",
                    "n_referencias", "n_citacoes"]
COLUNAS_PROVENIENCIA = ["id_openalex", "doi", "titulo", "ano", "direcoes", "sementes", "ja_no_corpus",
                        "gravado", "motivo"]


def similaridade(a, b):
    """Similaridade 0-100 entre títulos normalizados (rapidfuzz se houver; senão difflib)."""
    a, b = normalizar.titulo_normalizado(a), normalizar.titulo_normalizado(b)
    if not a or not b:
        return 0.0
    try:
        from rapidfuzz import fuzz
        return float(fuzz.ratio(a, b))
    except ImportError:
        import difflib
        return 100.0 * difflib.SequenceMatcher(None, a, b).ratio()


def resolver_semente(cliente, registro):
    """Devolve (W id, método, score) para um registro de registros_unicos."""
    wid = id_curto(registro.get("id_fonte"))
    if wid:
        return wid, "id_fonte", ""
    doi = normalizar.doi(registro.get("doi"))
    if doi:
        obra = cliente.obra(f"doi:{doi}", select=["id"])
        if obra and id_curto(obra.get("id")):
            return id_curto(obra["id"]), "doi", ""
    titulo = normalizar.titulo_normalizado(registro.get("titulo"))
    ano = normalizar.ano(registro.get("ano"))
    if titulo and ano:
        filtro = f"title.search:{titulo},publication_year:{ano}"
        candidatos = []
        for _, obras in cliente.paginar(filtro=filtro, select=["id", "title", "display_name", "publication_year"],
                                        por_pagina=25, max_paginas=1):
            candidatos.extend(obras)
        pontuados = sorted(
            ((similaridade(registro.get("titulo"), o.get("title") or o.get("display_name")), id_curto(o.get("id")))
             for o in candidatos
             if normalizar.ano(o.get("publication_year")) == ano and id_curto(o.get("id"))),
            reverse=True)
        if pontuados and pontuados[0][0] >= LIMIAR_TITULO:
            empate = len(pontuados) > 1 and pontuados[1][0] >= LIMIAR_TITULO and pontuados[1][1] != pontuados[0][1]
            if not empate:
                return pontuados[0][1], "titulo_ano", f"{pontuados[0][0]:.1f}"
            return "", "titulo_ambiguo", f"{pontuados[0][0]:.1f}"
    return "", "nao_resolvido", ""


def carregar_sementes(raiz, arquivo_ids=None, avisos=None):
    """Lista de registros de registros_unicos usados como sementes (clusters inativos: ver docstring)."""
    avisos = avisos if avisos is not None else []
    unicos = carregar_unicos(raiz)
    if not unicos:
        raise FileNotFoundError(f"{esquema.ARQ_UNICOS} vazio ou ausente; rode `dedup` antes")
    if arquivo_ids:
        linhas = ler_linhas(arquivo_ids)
        if not linhas:
            raise FileNotFoundError(f"arquivo de sementes vazio ou ausente: {arquivo_ids}")
        por_chave = {r.get("chave"): r for r in unicos.values() if r.get("chave")}
        sementes, faltam = [], []
        for l in linhas:
            reg = unicos.get(l.get("id_rs", "").strip()) or por_chave.get(l.get("chave", "").strip())
            (sementes if reg else faltam).append(reg or (l.get("id_rs") or l.get("chave")))
        if faltam:
            raise ValueError(f"sementes sem correspondência por id_rs/chave: {faltam[:10]}")
        inativas = [r["id_rs"] for r in sementes if _buscas.cluster_inativo(r)]
        if inativas:
            avisos.append(f"{len(inativas)} sementes de --ids vêm só de buscas substituídas "
                          f"({', '.join(inativas[:10])}); usadas porque foram pedidas explicitamente")
        return sementes
    tc = Path(raiz) / esquema.ARQ_ELEGIBILIDADE_TC_FINAL
    if not tc.exists():
        raise FileNotFoundError(f"{esquema.ARQ_ELEGIBILIDADE_TC_FINAL} não existe; informe --ids com as sementes")
    ids = [l["id_rs"] for l in ler_linhas(tc) if normalizar.ascii_fold(l.get("decisao")).lower() == "incluir"]
    faltam = [i for i in ids if i not in unicos]
    if faltam:
        raise ValueError(f"incluídos ausentes de {esquema.ARQ_UNICOS}: {faltam[:10]}")
    ids = list(dict.fromkeys(ids))
    inativas = [i for i in ids if _buscas.cluster_inativo(unicos[i])]
    if inativas:
        avisos.append(f"{len(inativas)} incluídos vêm só de buscas substituídas e não viram sementes "
                      f"({', '.join(inativas[:10])}); passe --ids para usá-los")
    return [unicos[i] for i in ids if i not in inativas]


def corpus_conhecido(raiz):
    """W ids e DOIs já presentes no conjunto ATIVO de registros.csv e registros_unicos.csv.

    Registros de buscas substituídas (ativa=false) e clusters `busca_inativa` ficam de fora.
    """
    ws, dois = set(), set()
    inativas = _buscas.inativas_do_projeto(raiz)
    for arq in (esquema.ARQ_REGISTROS, esquema.ARQ_UNICOS):
        for l in ler_linhas(Path(raiz) / arq):
            if (arq == esquema.ARQ_REGISTROS and l.get("busca_id") in inativas) or _buscas.cluster_inativo(l):
                continue
            if id_curto(l.get("id_fonte")):
                ws.add(id_curto(l["id_fonte"]))
            if normalizar.doi(l.get("doi")):
                dois.add(normalizar.doi(l["doi"]))
    return ws, dois


def _ordem_w(wid):
    m = re.search(r"\d+", wid)
    return int(m.group()) if m else 0


def coletar(cliente, sementes, direcao, max_paginas_citacoes=None):
    """Resolve sementes e coleta referências/citações. Devolve (linhas_sementes, encontrados)."""
    encontrados = {}

    def anotar(wid, dir_, id_rs, obra=None):
        wid = id_curto(wid)
        if not wid:
            return
        e = encontrados.setdefault(wid, {"obra": None, "direcoes": set(), "sementes": set()})
        e["direcoes"].add(dir_)
        e["sementes"].add(id_rs)
        if obra is not None and e["obra"] is None:
            e["obra"] = obra

    linhas_sementes, ws_sementes = [], set()
    for reg in sementes:
        wid, metodo, score = resolver_semente(cliente, reg)
        linha = {"id_rs": reg["id_rs"], "chave": reg.get("chave", ""), "doi": normalizar.doi(reg.get("doi")),
                 "id_openalex": wid, "metodo_resolucao": metodo, "score_titulo": score,
                 "n_referencias": "", "n_citacoes": ""}
        linhas_sementes.append(linha)
        if not wid:
            continue
        ws_sementes.add(wid)
        if direcao in ("tras", "ambas"):
            obra = cliente.obra(wid, select=["id", "referenced_works"]) or {}
            refs = obra.get("referenced_works") or []
            linha["n_referencias"] = str(len(refs))
            for ref in refs:
                anotar(ref, "tras", reg["id_rs"])
        if direcao in ("frente", "ambas"):
            n = 0
            for _, obras in cliente.paginar(filtro=f"cites:{wid}", max_paginas=max_paginas_citacoes):
                for o in obras:
                    anotar(o.get("id"), "frente", reg["id_rs"], o)
                    n += 1
            linha["n_citacoes"] = str(n)
    for wid in ws_sementes:  # uma semente citada por outra não é registro novo
        encontrados.pop(wid, None)
    faltam = [w for w, e in encontrados.items() if e["obra"] is None]
    for obra in cliente.obras_por_ids(faltam):
        wid = id_curto(obra.get("id"))
        if wid in encontrados and encontrados[wid]["obra"] is None:
            encontrados[wid]["obra"] = obra
    return linhas_sementes, encontrados


def cmd_bola_de_neve(args):
    comando = "bola-de-neve"
    raiz = exigir_raiz(args, comando)
    if raiz is None:
        return 1
    try:  # mesma regra do importador, antes de qualquer chamada à API
        _buscas.validar_busca_id(args.rodada, "--rodada")
    except ErroImportacao as e:
        return falhar(comando, str(e))
    rodada = args.rodada
    est_inicial = estado.carregar_estado(raiz)
    if rodada in _buscas.inativas(est_inicial):
        return falhar(comando, _buscas.descrever_inativa(est_inicial, rodada))
    arq_jsonl = f"01-busca/brutos/{rodada}_openalex_citacao.jsonl"
    arq_sementes = f"01-busca/bola_de_neve/{rodada}_sementes.csv"
    arq_prov = f"01-busca/bola_de_neve/{rodada}_proveniencia.csv"
    reexecucao = (raiz / arq_jsonl).exists()
    avisos = []

    if reexecucao:
        obras = ler_jsonl(raiz / arq_jsonl)
        prov = ler_linhas(raiz / arq_prov)
        sementes_linhas = ler_linhas(raiz / arq_sementes)
        n_encontrados = len(prov)
        n_conhecidos = sum(1 for p in prov if p.get("ja_no_corpus") == "1")
    else:
        try:
            sementes = carregar_sementes(raiz, resolver_caminho(raiz, args.ids) if args.ids else None, avisos)
        except (FileNotFoundError, ValueError) as e:
            return falhar(comando, str(e))
        if not sementes:
            return falhar(comando, "nenhuma semente (nenhum incluído)")
        cliente = ClienteOpenAlex(sessao=criar_sessao())
        try:
            sementes_linhas, encontrados = coletar(cliente, sementes, args.direcao, args.max_paginas_citacoes)
        except ErroOpenAlex as e:
            estado.registrar_evento(raiz, "erro", "07_textos_elegibilidade", "script", ATOR,
                                    dados={"rodada": rodada, "erro": str(e)})
            return falhar(comando, f"{e} (nada foi gravado; rode de novo)")
        ws_corpus, dois_corpus = corpus_conhecido(raiz)
        obras, prov = [], []
        for wid in sorted(encontrados, key=_ordem_w):
            e = encontrados[wid]
            obra = e["obra"] or {}
            doi = normalizar.doi(obra.get("doi"))
            conhecido = wid in ws_corpus or (doi and doi in dois_corpus)
            gravar = bool(e["obra"]) and (args.incluir_conhecidos or not conhecido)
            motivo = "" if gravar else ("sem_metadados" if not e["obra"] else "ja_no_corpus")
            prov.append({"id_openalex": wid, "doi": doi, "titulo": normalizar.texto(obra.get("title")),
                         "ano": normalizar.ano(obra.get("publication_year")),
                         "direcoes": "|".join(sorted(e["direcoes"])), "sementes": "|".join(sorted(e["sementes"])),
                         "ja_no_corpus": "1" if conhecido else "0", "gravado": "1" if gravar else "0",
                         "motivo": motivo})
            if gravar:
                obras.append(obra)
        n_encontrados = len(prov)
        n_conhecidos = sum(1 for p in prov if p["ja_no_corpus"] == "1")
        if args.max_paginas_citacoes:
            avisos.append("citações limitadas por --max-paginas-citacoes: rodada incompleta para o PRISMA")
        escrever_csv(raiz / arq_sementes, COLUNAS_SEMENTES, sementes_linhas)
        escrever_csv(raiz / arq_prov, COLUNAS_PROVENIENCIA, prov)
        escrever_jsonl(raiz / arq_jsonl, obras)

    nao_resolvidas = [s["id_rs"] for s in sementes_linhas if not s.get("id_openalex")]
    if nao_resolvidas:
        avisos.append(f"{len(nao_resolvidas)} sementes sem W id no OpenAlex: busque manualmente (Scholar, sites)")
    # Registro anterior desta rodada lido ANTES de importar: o importador também grava a busca
    # (com o mesmo sha256), e comparar depois faria o evento busca_registrada nunca ser emitido.
    anterior = next((b for b in estado.carregar_estado(raiz)["buscas"] if b.get("id") == rodada), None)
    try:
        imp = importar_jsonl(raiz, arq_jsonl, rodada, "citacao", "", usar_importador=not args.sem_importador)
    except ValueError as e:
        return falhar(comando, str(e))

    sha = estado.sha256_arquivo(raiz / arq_jsonl)
    registro = {"id": rodada, "fonte": "openalex", "metodo_identificacao": "citacao", "string_id": None,
                "executada_em": (anterior or {}).get("executada_em") or estado.agora(), "n_bruto": len(obras),
                "filtros_na_base": f"direcao={args.direcao}", "arquivo": arq_jsonl, "sha256": sha, "importada": True,
                "n_sementes": len(sementes_linhas), "n_encontrados": n_encontrados}
    est = registrar_busca(raiz, registro)
    if not (anterior and anterior.get("sha256") == sha):
        estado.registrar_evento(raiz, "busca_registrada", "07_textos_elegibilidade", "script", ATOR,
                                dados={"rodada": rodada, "metodo": "citacao", "direcao": args.direcao,
                                       "n_sementes": len(sementes_linhas), "n_nao_resolvidas": len(nao_resolvidas),
                                       "n_encontrados": n_encontrados, "n_ja_no_corpus": n_conhecidos,
                                       "n_gravados": len(obras)},
                                artefatos=[arq_jsonl, arq_sementes, arq_prov], estado=est)
    criterios = est.get("versoes_ativas", {}).get("criterios_ta")
    estado.resumo({
        "comando": comando, "ok": True, "rodada": rodada, "direcao": args.direcao, "reexecucao": reexecucao,
        "n_sementes": len(sementes_linhas), "n_nao_resolvidas": len(nao_resolvidas),
        "n_encontrados": n_encontrados, "n_ja_no_corpus": n_conhecidos, "n_gravados": len(obras),
        "importacao": imp, "arquivos": [arq_jsonl, arq_sementes, arq_prov], "avisos": avisos,
        "proximos_passos": [
            "rs.py dedup",
            "rs.py triagem preparar --etapa ta ... só com os novos id_rs desta rodada e a MESMA versão de critérios"
            + (f" ({criterios})" if criterios else ""),
            "nova rodada de bola de neve sobre os novos incluídos até não haver inclusões",
        ],
    })
    return 0


def registrar(subparsers):
    p = subparsers.add_parser("bola-de-neve", help="referências e citações dos incluídos pelo OpenAlex")
    p.add_argument("--direcao", choices=["tras", "frente", "ambas"], required=True)
    p.add_argument("--rodada", required=True, help="id da rodada (vira busca_id), ex.: SN1")
    p.add_argument("--ids", default=None, help="CSV com id_rs (ou chave) das sementes; padrão: incluídos no TC")
    p.add_argument("--incluir-conhecidos", action="store_true",
                   help="gravar também obras que já estão no corpus (padrão: só as novas)")
    p.add_argument("--max-paginas-citacoes", type=int, default=None,
                   help="limite de páginas de citações por semente (marca a rodada como incompleta)")
    p.add_argument("--sem-importador", action="store_true", help="usar a conversão interna em vez de `rs.py importar`")
    p.set_defaults(func=cmd_bola_de_neve)
