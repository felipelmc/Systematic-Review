"""Fluxograma PRISMA 2020 calculado do ledger (contagens, Mermaid, SVG e checklist).

USO
    python3 rs.py prisma                        # calcula do projeto e escreve em 07-relatorio/
    python3 rs.py prisma --tipo scr             # rótulos de revisão de escopo (PRISMA-ScR)
    python3 rs.py prisma --manual contagens.json [--saida pasta]   # "só o PRISMA", sem projeto
    python3 rs.py prisma --idioma en            # rótulos em inglês (padrão: idioma dos produtos)

Saídas (em 07-relatorio/ ou --saida): prisma_contagens.json, prisma.mermaid, prisma.svg,
prisma.png (rasterizado do SVG com pymupdf, para DOCX sem rsvg-convert; se falhar, só aviso)
e checklist_prisma.csv. Sem --tipo, o padrão é `scr` quando o tipo de revisão do projeto é
escopo ou mapa_evidencias, e `2020` nos demais casos.

Por que existe
    Nos scripts de exemplo do REFIS os números do PRISMA eram digitados à mão e não fechavam
    (20 vs 21 incluídos; 110 vs 120 triados). Aqui toda contagem é derivada das tabelas
    (references/08-relato.md) e só é publicada se as
    invariantes fecharem:
        identificados − duplicatas − automação − outros motivos = a triar
        triados = excluídos na triagem + buscados para recuperação
        avaliados = buscados − não recuperados
        avaliados = excluídos no texto completo + incluídos + aguardando classificação
    Se alguma quebrar, o comando sai com código 2 e não escreve o fluxograma: um PRISMA
    que não fecha é pior do que nenhum.

Decisões de desenho
    - Joins só por `id_rs` (triagem, elegibilidade) e `chave` (relatório de PDFs). Nunca título.
    - Ramos: um registro único pertence ao ramo "bases e registros" se algum dos seus
      registros de origem veio de `metodo_identificacao=base`; senão, ao ramo "outros
      métodos" (bola de neve = busca de citações; cinzenta = sites e organizações; manual).
      Assim um estudo achado nas bases e também na bola de neve conta uma vez, nas bases.
    - "NR" (não reportado) quando o artefato que sustenta a contagem não existe, seja porque
      a etapa ainda não rodou, seja porque foi ignorada num projeto parcial. Invariantes
      com algum termo NR não são avaliadas.
    - "incerto" na triagem de título/resumo segue para texto completo (conta como buscado).
      No texto completo, "incerto" ou decisão vazia quebra a invariante: decida antes.
      A decisão "aguardando" (awaiting classification, Cochrane Handbook sec. 4.4.5) tem caixa
      própria e entra na invariante: avaliados = excluídos + incluídos + aguardando.
    - Um relatório conta como recuperado se o PDF está com status ok no relatório da skill
      irmã OU se ele foi avaliado no texto completo (recuperação manual acontece). A coluna
      `recuperado` do inventario_textos.csv prevalece: `0` (PDF de outro trabalho, removido,
      ilegível) conta como não recuperado mesmo com status ok, e um relatório assim com decisão
      no texto completo quebra a invariante `avaliado_nao_recuperado`. Sem relatorio_pdfs.csv
      nem inventário, "não recuperados" fica NR.
    - Registros de buscas com `ativa: false` no estado (substituídas por `importar --substituir`)
      ficam fora de "identificados" e de todo o fluxo; decisões de texto completo sobre eles
      quebram a invariante `decisoes_de_busca_substituida`.
    - Estudos incluídos = `id_estudo` distintos entre os relatos incluídos (hierarquia
      estudo > relato do Apêndice D da base de conhecimento, item 3).
    - Adaptações ao modelo oficial, declaradas na legenda do SVG: o ramo "outros métodos"
      ganha a caixa "removidos antes da triagem" (registros já identificados nas bases)
      e, quando houve triagem de título/resumo desses registros (bola de neve re-triada,
      references/02-busca.md, seção 10), as caixas de triagem.
    - SVG escrito à mão, sem dependências (nem Graphviz nem mermaid-cli).
    - Com pendências abertas no estado, SVG e Mermaid levam a marca RASCUNHO NÃO VALIDADO.
    - Busca ativa com `truncada: true` (ex.: `buscar openalex --max-paginas`) não baixou todos os
      resultados: as contagens saem com aviso e a marca de rascunho (motivo "busca truncada"), e a
      lista das truncadas entra nos insumos (mudar a busca invalida o PRISMA do G9).
    - Fonte `generico` (planilha com mapa) não diz nada no fluxograma: o rótulo por fonte usa a
      `plataforma` declarada na busca (`importar --plataforma`) ou, sem ela, o `busca_id`.

Modelo do fluxograma e checklist: Page MJ, McKenzie JE, Bossuyt PM, et al. The PRISMA 2020
statement. BMJ 2021;372:n71, licença CC BY 4.0. Rótulos e descrições do checklist aqui são
traduções/paráfrases.
"""

import csv
import io
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

from . import esquema, estado

NR = "NR"
ARQ_CONTAGENS = esquema.ARQ_PRISMA_CONTAGENS
ARQ_MERMAID = esquema.ARQ_PRISMA_MERMAID
ARQ_SVG = esquema.ARQ_PRISMA_SVG
ARQ_PNG = esquema.ARQ_PRISMA_PNG
ARQ_CHECKLIST = esquema.ARQ_CHECKLIST_PRISMA
TIPOS_REVISAO_SCR = {"escopo", "mapa_evidencias"}  # PRISMA-ScR por padrão
DIR_CHECKLISTS = Path(__file__).resolve().parents[2] / "assets" / "checklists"

# Fontes que são registros de estudos (e não bases bibliográficas). Em políticas públicas
# os relevantes são os registros de ensaios/pré-análise (RIDIE, AEA RCT Registry, EGAP/OSF).
REGISTROS_ESTUDOS = {
    "registro", "registros", "clinicaltrials", "ictrp", "prospero", "osf_registries", "osf",
    "ridie", "aea_rct", "aearctr", "egap", "campbell_registro",
}
METODO_OUTROS = {"citacao": "busca_citacoes", "cinzenta": "sites_organizacoes"}  # demais -> "outros"
COLUNAS_CHECKLIST_SAIDA = ["item", "secao", "topico", "descricao", "local_no_relato", "status", "evidencia_no_projeto"]


# ---------------------------------------------------------------------------
# Leitura tolerante dos artefatos
# ---------------------------------------------------------------------------
def _liberar_campos_longos():
    """Resumos longos passam do limite padrão de 131 kB por campo do módulo csv."""
    limite = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limite)
            return
        except OverflowError:
            limite //= 10


_liberar_campos_longos()


def _ler_csv(caminho):
    """Lista de dicts ou None se o arquivo não existe (ausência = etapa pendente, não erro)."""
    caminho = Path(caminho)
    if not caminho.exists():
        return None
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        # Colunas extras sem cabeçalho (chave None) são descartadas em vez de quebrar a leitura.
        return [{k.strip(): (v or "").strip() for k, v in linha.items() if isinstance(k, str) and not isinstance(v, list)}
                for linha in csv.DictReader(f)]


def _eh_num(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def busca_inativa(busca):
    """True se a busca foi substituída (estado["buscas"][i]["ativa"] falso); ausente = ativa."""
    valor = (busca or {}).get(esquema.CAMPO_BUSCA_ATIVA, True)
    if isinstance(valor, str):
        return valor.strip().lower() in {"false", "0", "nao", "não", "no"}
    return valor is False or valor == 0


def buscas_inativas(estado_projeto):
    """Ids das buscas substituídas no estado (conjunto vazio sem estado)."""
    return {str(b.get("id")) for b in ((estado_projeto or {}).get("buscas") or []) if busca_inativa(b)}


def busca_truncada(busca):
    """True se a busca não baixou todos os resultados (estado["buscas"][i]["truncada"])."""
    valor = (busca or {}).get(esquema.CAMPO_BUSCA_TRUNCADA, False)
    if isinstance(valor, str):
        return valor.strip().lower() in {"true", "1", "sim", "yes"}
    return valor is True or (isinstance(valor, int) and not isinstance(valor, bool) and valor == 1)


def buscas_truncadas(estado_projeto):
    """Ids das buscas ATIVAS com resultados truncados, em ordem (substituídas não contam)."""
    return sorted(str(b.get("id")) for b in ((estado_projeto or {}).get("buscas") or [])
                  if busca_truncada(b) and not busca_inativa(b))


FONTES_SEM_ROTULO = {"generico", "desconhecida", ""}


def rotulo_fonte(fonte, busca=None, busca_id=""):
    """Rótulo da fonte no fluxograma: a própria fonte; para `generico`, a plataforma declarada ou o busca_id."""
    fonte = (fonte or "").strip().lower()
    if fonte not in FONTES_SEM_ROTULO:
        return fonte
    plataforma = str((busca or {}).get("plataforma") or "").strip()
    return plataforma or str(busca_id or (busca or {}).get("id") or fonte or "desconhecida")


def tipo_padrao(estado_projeto):
    """`scr` para escopo e mapa de evidências; `2020` nos demais tipos (e sem projeto)."""
    tipo_rev = ((estado_projeto or {}).get("projeto") or {}).get("tipo_revisao")
    return "scr" if tipo_rev in TIPOS_REVISAO_SCR else "2020"


def _soma(*valores):
    """Soma que propaga NR."""
    if any(not _eh_num(v) for v in valores):
        return NR
    return sum(valores)


def _ramo_vazio(outros=False):
    identificados = ({"sites_organizacoes": NR, "busca_citacoes": NR, "outros": NR} if outros
                     else {"bases": NR, "registros_estudos": NR, "por_fonte": {}})
    return {
        "identificados": identificados,
        "removidos_antes_triagem": {"duplicatas": NR, "automacao": NR, "outros_motivos": NR, "automacao_por_filtro": {}},
        "a_triar": NR,
        "triados": NR,
        "excluidos_triagem": NR,
        "buscados": NR,
        "nao_recuperados": NR,
        "avaliados": NR,
        "excluidos_elegibilidade": {"total": NR, "motivos": {}},
        "aguardando_classificacao": NR,
        "incluidos_relatos": NR,
    }


def contagens_vazias(tipo="2020", origem="calculado"):
    return {
        "schema": "rs-prisma/1",
        "tipo": tipo,
        "origem": origem,
        "gerado_em": None,
        "bases": _ramo_vazio(),
        "outros_metodos": _ramo_vazio(outros=True),
        "incluidos": {"estudos": NR, "relatos": NR},
        "etapas_nr": [],
        "invariantes": [],
        "avisos": [],
        "insumos": {},
        "rascunho": False,
        "pendencias_abertas": [],
        "buscas_truncadas": [],
        "motivos_rascunho": [],
    }


def _total_identificados(ramo):
    """Soma das subcontagens de identificação; NR parciais contam 0 se alguma for conhecida."""
    valores = [v for k, v in ramo["identificados"].items() if k != "por_fonte"]
    conhecidos = [v for v in valores if _eh_num(v)]
    return sum(conhecidos) if conhecidos else NR


def _total_removidos(ramo):
    r = ramo["removidos_antes_triagem"]
    valores = [r["duplicatas"], r["automacao"], r["outros_motivos"]]
    conhecidos = [v for v in valores if _eh_num(v)]
    return sum(conhecidos) if conhecidos else NR


def _ramo_tem_dados(ramo):
    return _eh_num(_total_identificados(ramo)) and _total_identificados(ramo) > 0


# ---------------------------------------------------------------------------
# Cálculo a partir das tabelas do projeto
# ---------------------------------------------------------------------------
def calcular(raiz, estado_projeto=None, tipo="2020"):
    """Calcula as contagens PRISMA a partir dos CSVs do projeto (caminhos de esquema.py).

    Nunca levanta exceção por artefato ausente: devolve NR. As invariantes vêm em
    `contagens["invariantes"]` (lista de {nome, ramo, ok, detalhe}).
    """
    raiz = Path(raiz)
    c = contagens_vazias(tipo)
    arquivos = {
        "registros": esquema.ARQ_REGISTROS, "unicos": esquema.ARQ_UNICOS,
        "filtro_formal": esquema.ARQ_FILTRO_FORMAL, "triagem_ta": esquema.ARQ_TRIAGEM_TA_FINAL,
        "relatorio_pdfs": esquema.ARQ_RELATORIO_PDFS, "elegibilidade_tc": esquema.ARQ_ELEGIBILIDADE_TC_FINAL,
        "inventario_textos": esquema.ARQ_INVENTARIO_TEXTOS,
    }
    for rel in arquivos.values():
        p = raiz / rel
        c["insumos"][rel] = estado.sha256_arquivo(p) if p.exists() else None
    inativas = buscas_inativas(estado_projeto)
    # O estado também é insumo: aposentar uma busca muda as contagens sem mudar nenhum CSV.
    c["insumos"]["estado.buscas_inativas"] = estado.sha256_texto(json.dumps(sorted(inativas))) if inativas else None
    truncadas = buscas_truncadas(estado_projeto)
    c["insumos"]["estado.buscas_truncadas"] = estado.sha256_texto(json.dumps(truncadas)) if truncadas else None
    buscas_por_id = {str(bu.get("id")): bu for bu in ((estado_projeto or {}).get("buscas") or []) if isinstance(bu, dict)}
    regs = _ler_csv(raiz / esquema.ARQ_REGISTROS)
    unicos = _ler_csv(raiz / esquema.ARQ_UNICOS)
    filtro = _ler_csv(raiz / esquema.ARQ_FILTRO_FORMAL)
    ta = _ler_csv(raiz / esquema.ARQ_TRIAGEM_TA_FINAL)
    pdfs = _ler_csv(raiz / esquema.ARQ_RELATORIO_PDFS)
    tc = _ler_csv(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL)
    inventario = _ler_csv(raiz / esquema.ARQ_INVENTARIO_TEXTOS)
    extras = []  # invariantes específicas do modo calculado (IDs), além das aritméticas

    def falha(nome, ramo, detalhe):
        extras.append({"nome": nome, "ramo": ramo, "ok": False, "detalhe": detalhe})

    if regs is None:
        c["avisos"].append(f"{esquema.ARQ_REGISTROS} ausente: nada a contar (rode `rs.py importar`).")
        _finalizar(c, estado_projeto, extras)
        return c

    # Buscas substituídas: seus registros saem de todo o fluxo (não são "identificados").
    reg_inativos = {r.get("id_registro", "") for r in regs if (r.get("busca_id") or "") in inativas}
    if inativas:
        c["buscas_inativas"] = {"buscas": sorted(inativas), "n_registros": len(reg_inativos)}
        if reg_inativos:
            c["avisos"].append(f"{len(reg_inativos)} registros de buscas substituídas ({', '.join(sorted(inativas))}) "
                               "ficaram fora dos identificados.")
        regs = [r for r in regs if r.get("id_registro", "") not in reg_inativos]

    b, o = c["bases"], c["outros_metodos"]
    reg_por_id = {}
    for r in regs:
        reg_por_id[r.get("id_registro", "")] = r

    def metodo(r):
        return (r.get("metodo_identificacao") or "base").lower()

    # Identificação ---------------------------------------------------------
    b["identificados"] = {"bases": 0, "registros_estudos": 0, "por_fonte": {}}
    o["identificados"] = {"sites_organizacoes": 0, "busca_citacoes": 0, "outros": 0}
    for r in regs:
        if metodo(r) == "base":
            fonte = (r.get("fonte") or "desconhecida").lower()
            chave_id = "registros_estudos" if fonte in REGISTROS_ESTUDOS else "bases"
            b["identificados"][chave_id] += 1
            rotulo = rotulo_fonte(fonte, buscas_por_id.get(r.get("busca_id") or ""), r.get("busca_id"))
            b["identificados"]["por_fonte"][rotulo] = b["identificados"]["por_fonte"].get(rotulo, 0) + 1
        else:
            o["identificados"][METODO_OUTROS.get(metodo(r), "outros")] += 1

    if unicos is None:
        c["avisos"].append(f"{esquema.ARQ_UNICOS} ausente: duplicatas e etapas seguintes = NR (rode `rs.py dedup`).")
        _finalizar(c, estado_projeto, extras)
        return c

    # Clusters (registros únicos) e ramo de cada um --------------------------
    ramo_de, unico_por_id, cobertos, desconhecidos = {}, {}, set(), set()
    retirados = set()  # clusters só com registros de buscas substituídas
    reg_cobertos = {"bases": 0, "outros_metodos": 0}
    for u in unicos:
        id_rs = u.get("id_rs", "")
        unico_por_id[id_rs] = u
        ids = [i.strip() for i in (u.get("ids_registro") or "").split("|") if i.strip()]
        conhecidos = [i for i in ids if i in reg_por_id]
        desconhecidos.update(i for i in ids if i not in reg_por_id and i not in reg_inativos)
        if ids and not conhecidos and all(i in reg_inativos for i in ids):
            retirados.add(id_rs)
            continue
        metodos = {metodo(reg_por_id[i]) for i in conhecidos}
        ramo = "bases" if (not metodos or "base" in metodos) else "outros_metodos"
        ramo_de[id_rs] = ramo
        # Duplicatas por ramo: registros do próprio ramo dentro dos clusters, menos clusters.
        # Registros de outros métodos que caíram num cluster das bases são "já identificados".
        for i in conhecidos:
            r_ramo = "bases" if metodo(reg_por_id[i]) == "base" else "outros_metodos"
            reg_cobertos[r_ramo] += 1
        cobertos.update(conhecidos)
    sem_cluster = sorted(set(reg_por_id) - cobertos)
    if sem_cluster:
        falha("registros_sem_cluster", "geral",
              f"{len(sem_cluster)} registros importados não estão em registros_unicos.csv "
              f"(ex.: {', '.join(sem_cluster[:5])}); rode `rs.py dedup` de novo.")
    if desconhecidos:
        falha("ids_registro_desconhecidos", "geral",
              f"{len(desconhecidos)} ids_registro de registros_unicos.csv não existem em registros.csv "
              f"(ex.: {', '.join(sorted(desconhecidos)[:5])}).")
    n_clusters = {"bases": 0, "outros_metodos": 0}
    for ramo in ramo_de.values():
        n_clusters[ramo] += 1
    if retirados:
        # O dedup mantém de propósito esses clusters em registros_unicos.csv com a flag busca_inativa (trilha de
        # auditoria): com a flag, não há o que refazer. Sem ela, o dedup ainda não rodou depois da substituição.
        sem_flag = sorted(i for i in retirados
                          if esquema.FLAG_BUSCA_INATIVA not in (unico_por_id[i].get("flags") or "").split("|"))
        com_flag = len(retirados) - len(sem_flag)
        if com_flag:
            c["avisos"].append(f"{com_flag} registros únicos marcados {esquema.FLAG_BUSCA_INATIVA} (só registros de "
                               "buscas substituídas) ficaram fora do fluxo, como previsto.")
        if sem_flag:
            c["avisos"].append(f"{len(sem_flag)} registros únicos só têm registros de buscas substituídas, mas ainda "
                               f"não têm a flag {esquema.FLAG_BUSCA_INATIVA} (ex.: {', '.join(sem_flag[:5])}): ficaram "
                               "fora do fluxo; rode `rs.py dedup` para marcá-los.")

    def ignorar_retirados(ids, onde):
        achados = sorted(i for i in ids if i in retirados)
        if achados:
            c["avisos"].append(f"{len(achados)} decisões de {onde} sobre registros de buscas substituídas foram "
                               f"ignoradas (ex.: {', '.join(achados[:5])}).")
        return {i: v for i, v in ids.items() if i not in retirados}

    # Automação (filtro formal em modo excluir) ------------------------------
    excl_auto = {}
    for linha in filtro or []:
        if linha.get("resultado") == "exclui":
            excl_auto.setdefault(linha.get("id_rs", ""), linha.get("filtro") or "filtro")
    excl_auto = ignorar_retirados(excl_auto, "filtro formal")
    fora = sorted(i for i in excl_auto if i not in ramo_de)
    if fora:
        falha("filtro_ids_desconhecidos", "geral",
              f"{len(fora)} id_rs de filtro_formal.csv não existem em registros_unicos.csv (ex.: {', '.join(fora[:5])}).")

    ids_ramo = {"bases": set(), "outros_metodos": set()}
    for id_rs, ramo in ramo_de.items():
        ids_ramo[ramo].add(id_rs)
    a_triar_ids = {}
    for nome_ramo, ramo in (("bases", b), ("outros_metodos", o)):
        rem = ramo["removidos_antes_triagem"]
        rem["duplicatas"] = reg_cobertos[nome_ramo] - n_clusters[nome_ramo]
        auto = {i for i in excl_auto if i in ids_ramo[nome_ramo]}
        rem["automacao"] = len(auto)
        rem["outros_motivos"] = 0
        por_filtro = {}
        for i in auto:
            por_filtro[excl_auto[i]] = por_filtro.get(excl_auto[i], 0) + 1
        rem["automacao_por_filtro"] = dict(sorted(por_filtro.items()))
        a_triar_ids[nome_ramo] = ids_ramo[nome_ramo] - auto
        ramo["a_triar"] = len(a_triar_ids[nome_ramo])

    # Triagem de título/resumo ----------------------------------------------
    if ta is None:
        c["avisos"].append(f"{esquema.ARQ_TRIAGEM_TA_FINAL} ausente: triagem e etapas seguintes = NR.")
        _finalizar(c, estado_projeto, extras)
        return c
    decisao_ta = {}
    for linha in ta:
        decisao_ta[linha.get("id_rs", "")] = (linha.get("decisao_final") or "").lower()
    decisao_ta = ignorar_retirados(decisao_ta, "triagem de título/resumo")
    desconhecidos_ta = sorted(i for i in decisao_ta if i not in ramo_de)
    if desconhecidos_ta:
        falha("triagem_ids_desconhecidos", "geral",
              f"{len(desconhecidos_ta)} id_rs da triagem não existem em registros_unicos.csv (ex.: {', '.join(desconhecidos_ta[:5])}).")
    triados_excluidos_auto = sorted(i for i in decisao_ta if i in excl_auto)
    if triados_excluidos_auto:
        falha("triagem_de_excluidos_por_automacao", "geral",
              f"{len(triados_excluidos_auto)} registros excluídos por automação também têm decisão de triagem "
              f"(ex.: {', '.join(triados_excluidos_auto[:5])}); remova-os da triagem ou do filtro em modo excluir.")
    buscados_ids = set()
    for nome_ramo, ramo in (("bases", b), ("outros_metodos", o)):
        alvo = a_triar_ids[nome_ramo]
        decididos = {i: d for i, d in decisao_ta.items() if ramo_de.get(i) == nome_ramo and i not in excl_auto}
        excl = {i for i, d in decididos.items() if d == "excluir"}
        seguem = {i for i, d in decididos.items() if d in ("incluir", "incerto")}
        ramo["triados"] = ramo["a_triar"]
        ramo["excluidos_triagem"] = len(excl)
        ramo["buscados"] = len(seguem)
        buscados_ids |= seguem
        sem_decisao = sorted(alvo - excl - seguem)
        if sem_decisao:
            c["avisos"].append(f"{nome_ramo}: {len(sem_decisao)} registros a triar sem decisão final "
                               f"(ex.: {', '.join(sem_decisao[:5])}).")

    # Recuperação e elegibilidade no texto completo --------------------------
    decisao_tc, motivo_tc = {}, {}
    for linha in tc or []:
        decisao_tc[linha.get("id_rs", "")] = (linha.get("decisao") or "").lower()
        motivo_tc[linha.get("id_rs", "")] = linha.get("criterio_falhou") or "motivo não informado"
    if tc is not None:
        tc_retirados = sorted(i for i in decisao_tc if i in retirados)
        if tc_retirados:
            falha("decisoes_de_busca_substituida", "geral",
                  f"{len(tc_retirados)} relatórios com decisão no texto completo só vieram de buscas substituídas "
                  f"(ex.: {', '.join(tc_retirados[:5])}); retire-os de elegibilidade_tc_final.csv ou reative a busca.")
        fora_tc = sorted(i for i in decisao_tc if i not in buscados_ids and i not in retirados)
        if fora_tc:
            falha("elegibilidade_fora_dos_buscados", "geral",
                  f"{len(fora_tc)} relatórios avaliados no texto completo não passaram pela triagem "
                  f"(ex.: {', '.join(fora_tc[:5])}).")

    status_pdf = {}
    for linha in pdfs or []:
        status_pdf[linha.get("chave", "")] = (linha.get("status") or "").lower()
    # inventario_textos.recuperado (0/1) prevalece sobre o status da skill irmã: um PDF "ok" que é de
    # outro trabalho, ou que foi removido, não foi recuperado.
    recuperado_inv = {}
    for linha in inventario or []:
        valor = (linha.get("recuperado") or "").strip()
        if valor in ("0", "1") and linha.get("chave"):
            recuperado_inv[linha["chave"]] = valor
    base_recuperacao = pdfs is not None or bool(recuperado_inv)
    for nome_ramo, ramo in (("bases", b), ("outros_metodos", o)):
        seguem = {i for i in buscados_ids if ramo_de.get(i) == nome_ramo}
        if base_recuperacao:
            nao_rec, manuais, contraditorios = 0, 0, []
            for i in seguem:
                chave = unico_por_id[i].get("chave", "")
                inv = recuperado_inv.get(chave)
                if inv == "0":
                    nao_rec += 1
                    if i in decisao_tc:
                        contraditorios.append(i)
                    continue
                ok = inv == "1" or status_pdf.get(chave, "") in esquema.STATUS_PDF_OK
                if not ok and i in decisao_tc:
                    manuais += 1
                elif not ok:
                    nao_rec += 1
            ramo["nao_recuperados"] = nao_rec
            if manuais:
                c["avisos"].append(f"{nome_ramo}: {manuais} relatórios avaliados sem PDF ok no relatorio_pdfs.csv "
                                   "(contados como recuperados manualmente).")
            if contraditorios:
                falha("avaliado_nao_recuperado", nome_ramo,
                      f"{len(contraditorios)} relatórios têm decisão no texto completo, mas recuperado=0 em "
                      f"{esquema.ARQ_INVENTARIO_TEXTOS} (ex.: {', '.join(sorted(contraditorios)[:5])}); a decisão veio "
                      "de um texto que não é o relatório: retire-a ou corrija o inventário.")
        if tc is not None:
            avaliados = {i for i in decisao_tc if ramo_de.get(i) == nome_ramo}
            excl = {i for i in avaliados if decisao_tc[i] == "excluir"}
            incl = {i for i in avaliados if decisao_tc[i] == "incluir"}
            aguard = {i for i in avaliados if decisao_tc[i] == "aguardando"}
            ramo["avaliados"] = len(avaliados)
            motivos = {}
            for i in excl:
                motivos[motivo_tc[i]] = motivos.get(motivo_tc[i], 0) + 1
            ramo["excluidos_elegibilidade"] = {
                "total": len(excl), "motivos": dict(sorted(motivos.items(), key=lambda kv: (-kv[1], kv[0])))}
            ramo["aguardando_classificacao"] = len(aguard)
            ramo["incluidos_relatos"] = len(incl)
            pendentes = sorted(avaliados - excl - incl - aguard)
            if pendentes:
                c["avisos"].append(f"{nome_ramo}: {len(pendentes)} relatórios sem decisão incluir/excluir/aguardando "
                                   "no texto completo.")
    if not base_recuperacao and tc is not None:
        c["avisos"].append(f"{esquema.ARQ_RELATORIO_PDFS} ausente: relatórios não recuperados = NR.")
    if tc is not None:
        incluidos = [i for i, d in decisao_tc.items() if d == "incluir" and i in unico_por_id and i not in retirados]
        estudos = {(unico_por_id[i].get("id_estudo") or esquema.id_estudo_de(i)) for i in incluidos}
        c["incluidos"] = {"estudos": len(estudos), "relatos": len(incluidos)}
    else:
        c["avisos"].append(f"{esquema.ARQ_ELEGIBILIDADE_TC_FINAL} ausente: avaliados e incluídos = NR.")
    _finalizar(c, estado_projeto, extras)
    return c


# ---------------------------------------------------------------------------
# Modo manual ("só o PRISMA")
# ---------------------------------------------------------------------------
def _mesclar(base, novo):
    for k, v in novo.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _mesclar(base[k], v)
        else:
            base[k] = v
    return base


def _normalizar_manual(valor):
    """Inteiros ficam; null, '', 'NR' ou negativos viram NR; dicts são percorridos."""
    if isinstance(valor, dict):
        return {k: _normalizar_manual(v) for k, v in valor.items()}
    if isinstance(valor, bool) or valor is None:
        return NR
    if isinstance(valor, (int, float)) and valor >= 0 and float(valor).is_integer():
        return int(valor)
    if isinstance(valor, str) and valor.strip().isdigit():
        return int(valor.strip())
    return NR


def _tem_numero(obj):
    if isinstance(obj, dict):
        return any(_tem_numero(v) for v in obj.values())
    return _eh_num(obj)


class ErroManual(ValueError):
    """JSON de contagens manuais com estrutura inválida."""


def _coagir_ramo(ramo, nome):
    """Aceita atalhos comuns do JSON digitado e recusa estruturas ambíguas.

    `identificados: 120` vira `{"bases": 120}` (ou `{"outros": 120}` no ramo de outros métodos);
    `excluidos_elegibilidade: 12` vira `{"total": 12}`. Um número em `removidos_antes_triagem`
    é ambíguo (duplicatas? automação?) e gera erro.
    """
    ramo = dict(ramo)
    if not isinstance(ramo.get("identificados", {}), dict):
        ramo["identificados"] = {("outros" if nome == "outros_metodos" else "bases"): ramo["identificados"]}
    if not isinstance(ramo.get("excluidos_elegibilidade", {}), dict):
        ramo["excluidos_elegibilidade"] = {"total": ramo["excluidos_elegibilidade"]}
    if not isinstance(ramo.get("removidos_antes_triagem", {}), dict):
        raise ErroManual(f"{nome}.removidos_antes_triagem deve ser um objeto "
                         '{"duplicatas": n, "automacao": n, "outros_motivos": n}')
    desconhecidas = set(ramo) - set(_ramo_vazio())
    if desconhecidas:
        raise ErroManual(f"{nome}: chaves desconhecidas {sorted(desconhecidas)}; use as de prisma_contagens.json")
    return ramo


def de_manual(dados, tipo="2020"):
    """Monta as contagens a partir de um JSON digitado (mesma estrutura de prisma_contagens.json).

    Chaves ausentes ficam NR. Se `incluidos` não vier, soma os relatos dos ramos. O ramo
    "outros métodos" só aparece no diagrama se vier no JSON.
    """
    if not isinstance(dados, dict):
        raise ErroManual("o JSON de contagens deve ser um objeto")
    c = contagens_vazias(tipo, origem="manual")
    dados = dict(dados)
    # Um prisma_contagens.json reaproveitado traz "outros_metodos" todo NR: isso não é um ramo.
    tem_outros = _tem_numero(_normalizar_manual(dados.get("outros_metodos") or {}))
    for chave_ramo in ("bases", "outros_metodos"):
        if chave_ramo in dados and not isinstance(dados[chave_ramo], dict):
            raise ErroManual(f"{chave_ramo} deve ser um objeto")
        if isinstance(dados.get(chave_ramo), dict):
            ramo = _normalizar_manual(_coagir_ramo(dados[chave_ramo], chave_ramo))
            motivos = ramo.get("excluidos_elegibilidade", {}).get("motivos") if isinstance(
                ramo.get("excluidos_elegibilidade"), dict) else None
            _mesclar(c[chave_ramo], ramo)
            if isinstance(motivos, dict):
                c[chave_ramo]["excluidos_elegibilidade"]["motivos"] = {k: v for k, v in motivos.items() if _eh_num(v)}
            # "a_triar" é o que o modelo PRISMA chama de triados quando não há automação separada
            if c[chave_ramo]["a_triar"] == NR and _eh_num(c[chave_ramo]["triados"]):
                c[chave_ramo]["a_triar"] = c[chave_ramo]["triados"]
    if isinstance(dados.get("incluidos"), dict):
        _mesclar(c["incluidos"], _normalizar_manual(dados["incluidos"]))
    if c["incluidos"]["relatos"] == NR:
        c["incluidos"]["relatos"] = _soma(c["bases"]["incluidos_relatos"],
                                          c["outros_metodos"]["incluidos_relatos"] if tem_outros else 0)
    c["_tem_outros"] = tem_outros
    _finalizar(c, None, [])
    return c


# ---------------------------------------------------------------------------
# Invariantes e NR
# ---------------------------------------------------------------------------
_CAMPOS_ETAPA = [
    ("identificados", "04_busca"), ("removidos_antes_triagem", "05_organizacao"),
    ("triados", "06_triagem_ta"), ("excluidos_triagem", "06_triagem_ta"), ("buscados", "06_triagem_ta"),
    ("nao_recuperados", "07_textos_elegibilidade"), ("avaliados", "07_textos_elegibilidade"),
    ("excluidos_elegibilidade", "07_textos_elegibilidade"), ("incluidos_relatos", "07_textos_elegibilidade"),
]


def verificar_invariantes(c):
    """Asserções de soma do PRISMA 2020. Termos NR pulam a checagem (registrada como ok=None)."""
    resultado = []

    def checar(nome, ramo, esquerda, direita, texto):
        if not (_eh_num(esquerda) and _eh_num(direita)):
            resultado.append({"nome": nome, "ramo": ramo, "ok": None, "detalhe": f"não avaliada (NR): {texto}"})
        else:
            ok = esquerda == direita
            resultado.append({"nome": nome, "ramo": ramo, "ok": ok,
                              "detalhe": f"{texto}: {esquerda} {'=' if ok else '≠'} {direita}"})

    for nome_ramo in ("bases", "outros_metodos"):
        r = c[nome_ramo]
        if nome_ramo == "outros_metodos" and not (_ramo_tem_dados(r) or c.get("_tem_outros")):
            continue
        rem = r["removidos_antes_triagem"]
        checar("identificacao_fecha", nome_ramo,
               _soma(_total_identificados(r), -_total_removidos(r)) if _eh_num(_total_removidos(r)) else NR,
               r["a_triar"], "identificados − removidos antes da triagem = a triar")
        checar("triagem_fecha", nome_ramo, r["triados"], _soma(r["excluidos_triagem"], r["buscados"]),
               "triados = excluídos na triagem + buscados")
        checar("recuperacao_fecha", nome_ramo, r["avaliados"],
               _soma(r["buscados"], -r["nao_recuperados"]) if _eh_num(r["nao_recuperados"]) else NR,
               "avaliados = buscados − não recuperados")
        excl_tc = r["excluidos_elegibilidade"]["total"]
        aguard = r.get("aguardando_classificacao", NR)
        # "aguardando" é caixa opcional: NR (JSON manual sem ela) conta 0 para não anular a checagem.
        checar("elegibilidade_fecha", nome_ramo, r["avaliados"],
               _soma(excl_tc, r["incluidos_relatos"], aguard if _eh_num(aguard) else 0),
               "avaliados = excluídos no texto completo + incluídos + aguardando classificação")
        motivos = r["excluidos_elegibilidade"].get("motivos") or {}
        if motivos:
            checar("motivos_fecham", nome_ramo, excl_tc, sum(v for v in motivos.values() if _eh_num(v)),
                   "excluídos no texto completo = soma dos motivos")
        for campo, valor in (("duplicatas", rem["duplicatas"]), ("a_triar", r["a_triar"])):
            if _eh_num(valor) and valor < 0:
                resultado.append({"nome": f"{campo}_nao_negativo", "ramo": nome_ramo, "ok": False,
                                  "detalhe": f"{campo} negativo ({valor})"})
    total_ramos = _soma(c["bases"]["incluidos_relatos"],
                        c["outros_metodos"]["incluidos_relatos"]
                        if (_ramo_tem_dados(c["outros_metodos"]) or c.get("_tem_outros")) else 0)
    checar("incluidos_somam_ramos", "geral", c["incluidos"]["relatos"], total_ramos,
           "relatos incluídos = soma dos ramos")
    est, rel = c["incluidos"]["estudos"], c["incluidos"]["relatos"]
    if _eh_num(est) and _eh_num(rel):
        resultado.append({"nome": "estudos_ate_relatos", "ramo": "geral", "ok": est <= rel,
                          "detalhe": f"estudos ({est}) ≤ relatos ({rel})"})
    return resultado


def _campo_nr(valor):
    if isinstance(valor, dict):
        numericos = [v for k, v in valor.items() if k not in ("por_fonte", "motivos", "automacao_por_filtro")]
        return all(v == NR for v in numericos) if numericos else False
    return valor == NR


def _finalizar(c, estado_projeto, extras):
    c["invariantes"] = extras + verificar_invariantes(c)
    ignoradas = set((estado_projeto or {}).get("projeto", {}).get("etapas_ignoradas", []) or [])
    etapas_nr = {}
    for nome_ramo in ("bases", "outros_metodos"):
        if nome_ramo == "outros_metodos" and not (_ramo_tem_dados(c[nome_ramo]) or c.get("_tem_outros")):
            continue
        for campo, etapa in _CAMPOS_ETAPA:
            if _campo_nr(c[nome_ramo][campo]):
                motivo = ("ignorada" if etapa in ignoradas
                          else "nao_informado" if c.get("origem") == "manual" else "sem_artefato")
                etapas_nr.setdefault(etapa, motivo)
    c["etapas_nr"] = [{"etapa": e, "motivo": m} for e, m in sorted(etapas_nr.items())]
    if estado_projeto:
        marcar_rascunho(c, estado_projeto)
    c["gerado_em"] = estado.agora()


def marcar_rascunho(c, estado_projeto):
    """Pendências abertas e buscas truncadas marcam o fluxograma como rascunho (com os motivos)."""
    abertas = estado.pendencias_abertas(estado_projeto)
    truncadas = buscas_truncadas(estado_projeto)
    c["pendencias_abertas"] = [p["id"] for p in abertas]
    c["buscas_truncadas"] = truncadas
    motivos = []
    if abertas:
        motivos.append(f"{len(abertas)} pendências abertas")
    if truncadas:
        motivos.append("busca truncada: " + ", ".join(truncadas))
        aviso = (f"buscas com resultados truncados ({', '.join(truncadas)}): identificados subcontados; "
                 "rode a busca inteira (sem --max-paginas) e registre com `importar --substituir`, ou justifique "
                 "no relato. O fluxograma sai como rascunho")
        if aviso not in c["avisos"]:
            c["avisos"].append(aviso)
    c["motivos_rascunho"] = motivos
    c["rascunho"] = bool(motivos)
    return c


def invariantes_quebradas(c):
    return [i for i in c["invariantes"] if i["ok"] is False]


# ---------------------------------------------------------------------------
# Rótulos (PRISMA 2020 para novas revisões; PT traduzido, EN do modelo oficial)
# ---------------------------------------------------------------------------
ROTULOS = {
    "pt": {
        "cab_bases": "Identificação de estudos via bases de dados e registros",
        "cab_outros": "Identificação de estudos via outros métodos",
        "fase_identificacao": "Identificação", "fase_triagem": "Triagem", "fase_incluidos": "Incluídos",
        "identificados_de": "Registros identificados de:", "bases": "Bases de dados",
        "registros_estudos": "Registros de estudos",
        "sites_organizacoes": "Sites e organizações", "busca_citacoes": "Busca de citações", "outros": "Outros",
        "removidos": "Registros removidos antes da triagem:", "duplicatas": "Registros duplicados removidos",
        "duplicatas_outros": "Duplicados ou já identificados nas bases",
        "automacao": "Marcados como inelegíveis por automação", "outros_motivos": "Removidos por outros motivos",
        "triados": "Registros triados", "excluidos_triagem": "Registros excluídos",
        "buscados": "Relatórios buscados para recuperação", "nao_recuperados": "Relatórios não recuperados",
        "avaliados": "Relatórios avaliados para elegibilidade", "excluidos_tc": "Relatórios excluídos:",
        "sem_motivo": "Motivos não informados",
        "estudos": "Estudos incluídos na revisão", "relatos": "Relatórios dos estudos incluídos",
        "estudos_scr": "Fontes de evidência incluídas", "relatos_scr": "Relatórios das fontes incluídas",
        "legenda": "Modelo: PRISMA 2020 (Page et al., BMJ 2021;372:n71; CC BY 4.0). NR = não reportado.",
        "adaptacao": "Adaptação: ramo de outros métodos com remoção de já identificados e triagem de título/resumo.",
        "aguardando": "Relatórios aguardando classificação",
        "adaptacao_aguardando": "Adaptação: relatórios aguardando classificação (Cochrane Handbook, sec. 4.4.5) "
                                "fora de excluídos e incluídos.",
        "pendencias": "Pendências abertas",
        "buscas_truncadas": "Buscas truncadas",
    },
    "en": {
        "cab_bases": "Identification of studies via databases and registers",
        "cab_outros": "Identification of studies via other methods",
        "fase_identificacao": "Identification", "fase_triagem": "Screening", "fase_incluidos": "Included",
        "identificados_de": "Records identified from:", "bases": "Databases", "registros_estudos": "Registers",
        "sites_organizacoes": "Websites and organisations", "busca_citacoes": "Citation searching", "outros": "Other",
        "removidos": "Records removed before screening:", "duplicatas": "Duplicate records removed",
        "duplicatas_outros": "Duplicates or already identified in databases",
        "automacao": "Records marked as ineligible by automation tools",
        "outros_motivos": "Records removed for other reasons",
        "triados": "Records screened", "excluidos_triagem": "Records excluded",
        "buscados": "Reports sought for retrieval", "nao_recuperados": "Reports not retrieved",
        "avaliados": "Reports assessed for eligibility", "excluidos_tc": "Reports excluded:",
        "sem_motivo": "Reasons not reported",
        "estudos": "Studies included in review", "relatos": "Reports of included studies",
        "estudos_scr": "Sources of evidence included", "relatos_scr": "Reports of included sources",
        "legenda": "Template: PRISMA 2020 (Page et al., BMJ 2021;372:n71; CC BY 4.0). NR = not reported.",
        "adaptacao": "Adapted: other-methods branch shows already-identified records and title/abstract screening.",
        "aguardando": "Reports awaiting classification",
        "adaptacao_aguardando": "Adapted: reports awaiting classification (Cochrane Handbook, sec. 4.4.5) are "
                                "neither excluded nor included.",
        "pendencias": "Open issues",
        "buscas_truncadas": "Truncated searches",
    },
}


def _n(valor):
    return f"(n = {valor})"


def _texto_rascunho(c, t):
    """Motivos da marca de rascunho no cabeçalho: pendências abertas e buscas truncadas."""
    partes = []
    if c.get("pendencias_abertas") or not c.get("buscas_truncadas"):
        partes.append(f"{t['pendencias']}: {', '.join(c.get('pendencias_abertas') or [])}")
    if c.get("buscas_truncadas"):
        partes.append(f"{t['buscas_truncadas']}: {', '.join(c['buscas_truncadas'])}")
    return "; ".join(partes)


def _mostrar_outros(c):
    return bool(c.get("_tem_outros")) or _ramo_tem_dados(c["outros_metodos"])


def _triagem_outros_visivel(c):
    o = c["outros_metodos"]
    return _eh_num(o["triados"]) and (o["triados"] > 0 or (_eh_num(o["excluidos_triagem"]) and o["excluidos_triagem"] > 0))


def caixas(c, idioma="pt"):
    """Conteúdo das caixas do fluxograma: {id: [linhas]} (primeira linha = título da caixa)."""
    t = ROTULOS[idioma]
    scr = c.get("tipo") == "scr"
    b, o = c["bases"], c["outros_metodos"]
    rem_b = b["removidos_antes_triagem"]
    cx = {
        "b_ident": [t["identificados_de"], f"{t['bases']} {_n(b['identificados']['bases'])}"]
        + [f"  {fonte} {_n(n)}" for fonte, n in sorted((b["identificados"].get("por_fonte") or {}).items())
           if fonte not in REGISTROS_ESTUDOS]
        + [f"{t['registros_estudos']} {_n(b['identificados']['registros_estudos'])}"],
        "b_removidos": [t["removidos"], f"{t['duplicatas']} {_n(rem_b['duplicatas'])}",
                        f"{t['automacao']} {_n(rem_b['automacao'])}"]
        + [f"  {filtro} {_n(n)}" for filtro, n in (rem_b.get("automacao_por_filtro") or {}).items()]
        + [f"{t['outros_motivos']} {_n(rem_b['outros_motivos'])}"],
        "b_triados": [t["triados"], _n(b["triados"])],
        "b_excl_triagem": [t["excluidos_triagem"], _n(b["excluidos_triagem"])],
        "b_buscados": [t["buscados"], _n(b["buscados"])],
        "b_nao_rec": [t["nao_recuperados"], _n(b["nao_recuperados"])],
        "b_avaliados": [t["avaliados"], _n(b["avaliados"])],
        "b_excl_tc": _linhas_motivos(t, b),
        "incluidos": [t["estudos_scr" if scr else "estudos"], _n(c["incluidos"]["estudos"]),
                      t["relatos_scr" if scr else "relatos"], _n(c["incluidos"]["relatos"])],
    }
    if _mostrar_outros(c):
        rem_o = o["removidos_antes_triagem"]
        cx.update({
            "o_ident": [t["identificados_de"]] + [f"{t[k]} {_n(o['identificados'].get(k, NR))}"
                                                  for k in ("sites_organizacoes", "busca_citacoes", "outros")],
            "o_removidos": [t["removidos"], f"{t['duplicatas_outros']} {_n(rem_o['duplicatas'])}",
                            f"{t['automacao']} {_n(rem_o['automacao'])}"],
            "o_buscados": [t["buscados"], _n(o["buscados"])],
            "o_nao_rec": [t["nao_recuperados"], _n(o["nao_recuperados"])],
            "o_avaliados": [t["avaliados"], _n(o["avaliados"])],
            "o_excl_tc": _linhas_motivos(t, o),
        })
        if _triagem_outros_visivel(c):
            cx["o_triados"] = [t["triados"], _n(o["triados"])]
            cx["o_excl_triagem"] = [t["excluidos_triagem"], _n(o["excluidos_triagem"])]
        if _tem_aguardando(o):
            cx["o_aguardando"] = [t["aguardando"], _n(o["aguardando_classificacao"])]
    if _tem_aguardando(b):
        cx["b_aguardando"] = [t["aguardando"], _n(b["aguardando_classificacao"])]
    return cx


def _tem_aguardando(ramo):
    valor = ramo.get("aguardando_classificacao", NR)
    return _eh_num(valor) and valor > 0


def _linhas_motivos(t, ramo):
    excl = ramo["excluidos_elegibilidade"]
    linhas = [f"{t['excluidos_tc']} {_n(excl['total'])}"]
    motivos = excl.get("motivos") or {}
    if motivos:
        linhas += [f"  {m} {_n(n)}" for m, n in motivos.items()]
    elif _eh_num(excl["total"]) and excl["total"] > 0:
        linhas.append(f"  {t['sem_motivo']}")
    return linhas


# ---------------------------------------------------------------------------
# Mermaid
# ---------------------------------------------------------------------------
def _mermaid_rotulo(linhas):
    # Mermaid apaga espaços iniciais: subitens (por fonte, por filtro, por motivo) ganham um marcador.
    texto = "<br/>".join(("· " + l.strip()) if l.startswith(" ") else l.strip() for l in linhas)
    return texto.replace('"', "#quot;")


def gerar_mermaid(c, idioma="pt"):
    """Fluxograma em Mermaid (renderizado nativamente pelo Quarto)."""
    t = ROTULOS[idioma]
    cx = caixas(c, idioma)
    linhas = ["flowchart TD"]
    if c.get("rascunho"):
        linhas.append(f'  rascunho["{esquema.MARCA_RASCUNHO}<br/>{_texto_rascunho(c, t)}"]')
        linhas.append("  style rascunho fill:#fde2e2,stroke:#b91c1c,color:#b91c1c")
    linhas.append(f'  subgraph ramo_bases["{t["cab_bases"]}"]')
    for nid in ("b_ident", "b_removidos", "b_triados", "b_excl_triagem", "b_buscados", "b_nao_rec",
                "b_avaliados", "b_excl_tc") + (("b_aguardando",) if "b_aguardando" in cx else ()):
        linhas.append(f'    {nid}["{_mermaid_rotulo(cx[nid])}"]')
    linhas.append("  end")
    arestas = ["b_ident --> b_removidos", "b_ident --> b_triados", "b_triados --> b_excl_triagem",
               "b_triados --> b_buscados", "b_buscados --> b_nao_rec", "b_buscados --> b_avaliados",
               "b_avaliados --> b_excl_tc", "b_avaliados --> incluidos"]
    if "b_aguardando" in cx:
        arestas.append("b_avaliados --> b_aguardando")
    if "o_ident" in cx:
        linhas.append(f'  subgraph ramo_outros["{t["cab_outros"]}"]')
        ids_o = ["o_ident", "o_removidos"] + (["o_triados", "o_excl_triagem"] if "o_triados" in cx else []) + [
            "o_buscados", "o_nao_rec", "o_avaliados", "o_excl_tc"] + (["o_aguardando"] if "o_aguardando" in cx else [])
        for nid in ids_o:
            linhas.append(f'    {nid}["{_mermaid_rotulo(cx[nid])}"]')
        linhas.append("  end")
        arestas += ["o_ident --> o_removidos"]
        if "o_triados" in cx:
            arestas += ["o_ident --> o_triados", "o_triados --> o_excl_triagem", "o_triados --> o_buscados"]
        else:
            arestas += ["o_ident --> o_buscados"]
        arestas += ["o_buscados --> o_nao_rec", "o_buscados --> o_avaliados", "o_avaliados --> o_excl_tc",
                    "o_avaliados --> incluidos"]
        if "o_aguardando" in cx:
            arestas.append("o_avaliados --> o_aguardando")
    linhas.append(f'  incluidos["{_mermaid_rotulo(cx["incluidos"])}"]')
    linhas += [f"  {a}" for a in arestas]
    return "\n".join(linhas) + "\n"


# ---------------------------------------------------------------------------
# SVG (sem dependências)
# ---------------------------------------------------------------------------
_LARG_CAIXA = 250
_FONTE = 12
_ALT_LINHA = 16
_PAD = 9
_COR_CAB = "#d9e5f2"
_COR_FASE = "#c7d7ea"


def _quebrar(texto, largura_px, fonte=_FONTE):
    """Quebra de linha aproximada por número de caracteres (sem medir a fonte)."""
    max_chars = max(10, int((largura_px - 2 * _PAD) / (fonte * 0.55)))
    recuo = len(texto) - len(texto.lstrip(" "))
    # "(n = 12)" nunca é quebrado no meio: protege os espaços internos antes de partir em palavras.
    protegido = re.sub(r"\(n = [^)]*\)", lambda m: m.group(0).replace(" ", "\x00"), texto)
    palavras = [p.replace("\x00", " ") for p in protegido.split()]
    linhas, atual = [], " " * recuo
    for p in palavras:
        candidato = (atual + " " + p) if atual.strip() else (atual + p)
        if len(candidato) > max_chars and atual.strip():
            linhas.append(atual)
            atual = " " * (recuo + 2) + p
        else:
            atual = candidato
    if atual.strip():
        linhas.append(atual)
    return linhas or [""]


def _x(texto):
    return _xml_escape(str(texto), {'"': "&quot;"})


def _caixa_svg(x, y, w, h, linhas_quebradas, preenchimento="#ffffff"):
    partes = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{preenchimento}" stroke="#333" stroke-width="1.2"/>']
    ty = y + _PAD + _FONTE
    for i, (linha, negrito) in enumerate(linhas_quebradas):
        recuo = (len(linha) - len(linha.lstrip(" "))) * 3
        peso = ' font-weight="bold"' if negrito else ""
        partes.append(f'<text x="{x + _PAD + recuo}" y="{ty + i * _ALT_LINHA}"{peso}>{_x(linha.strip())}</text>')
    return "\n".join(partes)


def _preparar(linhas, w):
    saida = []
    for i, linha in enumerate(linhas):
        for sub in _quebrar(linha, w):
            saida.append((sub, i == 0))
    return saida


def _altura(linhas_q):
    return 2 * _PAD + len(linhas_q) * _ALT_LINHA


def _ponta_seta(x1, y1, x2, y2, comprimento=9, meia_largura=4):
    """Ponta de seta desenhada como triângulo (marker-end não sai na rasterização do pymupdf)."""
    dx, dy = x2 - x1, y2 - y1
    norma = (dx * dx + dy * dy) ** 0.5 or 1.0
    ux, uy = dx / norma, dy / norma
    bx, by = x2 - ux * comprimento, y2 - uy * comprimento
    pts = [(x2, y2), (bx - uy * meia_largura, by + ux * meia_largura), (bx + uy * meia_largura, by - ux * meia_largura)]
    return '<path d="M{:.1f},{:.1f} L{:.1f},{:.1f} L{:.1f},{:.1f} z" fill="#333"/>'.format(*(v for p in pts for v in p))


def gerar_svg(c, idioma="pt"):
    """SVG autocontido do fluxograma PRISMA 2020 (com ou sem ramo de outros métodos)."""
    t = ROTULOS[idioma]
    cx = caixas(c, idioma)
    outros = "o_ident" in cx
    tri_o = "o_triados" in cx
    w, gap, gap_ramos, x0 = _LARG_CAIXA, 40, 70, 54
    col = [x0, x0 + w + gap]
    if outros:
        col += [col[1] + w + gap_ramos, col[1] + w + gap_ramos + w + gap]
    largura = col[-1] + w + 24
    prep = {k: _preparar(v, w) for k, v in cx.items()}

    y = 20
    cabecalho = []
    if c.get("rascunho"):
        cabecalho.append(f'<text x="{x0}" y="{y + 14}" font-size="15" font-weight="bold" fill="#b91c1c">'
                         f'{_x(esquema.MARCA_RASCUNHO)} — {_x(_texto_rascunho(c, t))}</text>')
        y += 30
    # Cabeçalhos dos ramos
    alt_cab = 30
    cabecalho.append(f'<rect x="{col[0]}" y="{y}" width="{col[1] + w - col[0]}" height="{alt_cab}" rx="4" '
                     f'fill="{_COR_CAB}" stroke="#333"/>')
    cabecalho.append(f'<text x="{(col[0] + col[1] + w) / 2}" y="{y + 20}" text-anchor="middle" font-weight="bold">'
                     f'{_x(t["cab_bases"])}</text>')
    if outros:
        cabecalho.append(f'<rect x="{col[2]}" y="{y}" width="{col[3] + w - col[2]}" height="{alt_cab}" rx="4" '
                         f'fill="{_COR_CAB}" stroke="#333"/>')
        cabecalho.append(f'<text x="{(col[2] + col[3] + w) / 2}" y="{y + 20}" text-anchor="middle" font-weight="bold">'
                         f'{_x(t["cab_outros"])}</text>')
    y += alt_cab + 24

    linhas_grade = [  # (fase, [(coluna, id)])
        ("identificacao", [(0, "b_ident"), (1, "b_removidos"), (2, "o_ident"), (3, "o_removidos")]),
        ("triagem", [(0, "b_triados"), (1, "b_excl_triagem"), (2, "o_triados"), (3, "o_excl_triagem")]),
        ("triagem", [(0, "b_buscados"), (1, "b_nao_rec"), (2, "o_buscados"), (3, "o_nao_rec")]),
        ("triagem", [(0, "b_avaliados"), (1, "b_excl_tc"), (2, "o_avaliados"), (3, "o_excl_tc")]),
        ("triagem", [(1, "b_aguardando"), (3, "o_aguardando")]),  # só aparece se houver "aguardando"
        ("incluidos", [(0, "incluidos")]),
    ]
    pos = {}
    corpo = []
    faixas = {}
    gap_linha = 34
    for fase, itens in linhas_grade:
        presentes = [(ci, nid) for ci, nid in itens if nid in prep]
        if not presentes:
            continue
        alt = max(_altura(prep[nid]) for _, nid in presentes)
        for ci, nid in presentes:
            h = _altura(prep[nid])
            pos[nid] = (col[ci], y, w, h)
            corpo.append(_caixa_svg(col[ci], y, w, h, prep[nid]))
        ini, fim = faixas.get(fase, (y, y))
        faixas[fase] = (min(ini, y), y + alt)
        y += alt + gap_linha

    # Setas
    def meio_dir(nid):
        x, yy, ww, hh = pos[nid]
        return x + ww, yy + min(hh / 2, 28)

    def seta(x1, y1, x2, y2):
        return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#333" stroke-width="1.3"/>'
                + _ponta_seta(x1, y1, x2, y2))

    def seta_poligonal(pontos):
        texto = " ".join(f"{px},{py}" for px, py in pontos)
        return (f'<polyline points="{texto}" fill="none" stroke="#333" stroke-width="1.3"/>'
                + _ponta_seta(*pontos[-2], *pontos[-1]))

    def para_aguardando(a, b_):
        """Da borda direita (parte baixa) de `a`, pelo corredor entre colunas, até a caixa `b_` na linha de baixo."""
        xa, ya, wa, ha = pos[a]
        xb, yb, _, hb = pos[b_]
        y_ini = ya + max(ha - 10, min(ha / 2, 28) + 12)
        corredor = xa + wa + (xb - xa - wa) / 2
        alvo_y = yb + min(hb / 2, 28)
        return seta_poligonal([(xa + wa, y_ini), (corredor, y_ini), (corredor, alvo_y), (xb - 2, alvo_y)])

    def para_baixo(a, b_):
        xa, ya, wa, ha = pos[a]
        xb, yb, _, _ = pos[b_]
        return seta(xa + wa / 2, ya + ha, xb + wa / 2, yb - 2)

    def para_lado(a, b_):
        x1, y1 = meio_dir(a)
        xb, _, _, _ = pos[b_]
        return seta(x1, y1, xb - 2, y1)

    setas = [para_baixo("b_ident", "b_triados"), para_baixo("b_triados", "b_buscados"),
             para_baixo("b_buscados", "b_avaliados"), para_baixo("b_avaliados", "incluidos"),
             para_lado("b_ident", "b_removidos"), para_lado("b_triados", "b_excl_triagem"),
             para_lado("b_buscados", "b_nao_rec"), para_lado("b_avaliados", "b_excl_tc")]
    if "b_aguardando" in pos:
        setas.append(para_aguardando("b_avaliados", "b_aguardando"))
    if outros:
        setas.append(para_lado("o_ident", "o_removidos"))
        if tri_o:
            setas += [para_baixo("o_ident", "o_triados"), para_baixo("o_triados", "o_buscados"),
                      para_lado("o_triados", "o_excl_triagem")]
        else:
            setas.append(para_baixo("o_ident", "o_buscados"))
        setas += [para_baixo("o_buscados", "o_avaliados"), para_lado("o_buscados", "o_nao_rec"),
                  para_lado("o_avaliados", "o_excl_tc")]
        xa, ya, wa, ha = pos["o_avaliados"]
        xi, yi, wi, hi = pos["incluidos"]
        meio_x = xa + wa / 2
        alvo_y = yi + min(hi / 2, 28)
        setas.append(seta_poligonal([(meio_x, ya + ha), (meio_x, alvo_y), (xi + wi + 2, alvo_y)]))
        if "o_aguardando" in pos:
            setas.append(para_aguardando("o_avaliados", "o_aguardando"))

    # Faixas laterais das fases
    fases_svg = []
    nomes_fase = {"identificacao": t["fase_identificacao"], "triagem": t["fase_triagem"], "incluidos": t["fase_incluidos"]}
    for fase, (ini, fim) in faixas.items():
        cy = (ini + fim) / 2
        fases_svg.append(f'<rect x="12" y="{ini}" width="28" height="{fim - ini}" rx="4" fill="{_COR_FASE}" stroke="#333"/>')
        fases_svg.append(f'<text x="26" y="{cy}" text-anchor="middle" font-weight="bold" '
                         f'transform="rotate(-90 26 {cy})" dominant-baseline="middle">{_x(nomes_fase[fase])}</text>')

    rodape_y = y + 4
    rodape = [f'<text x="{x0}" y="{rodape_y}" font-size="10" fill="#555">{_x(t["legenda"])}</text>']
    if outros:
        rodape_y += 14
        rodape.append(f'<text x="{x0}" y="{rodape_y}" font-size="10" fill="#555">{_x(t["adaptacao"])}</text>')
    if "b_aguardando" in pos or "o_aguardando" in pos:
        rodape_y += 14
        rodape.append(f'<text x="{x0}" y="{rodape_y}" font-size="10" fill="#555">{_x(t["adaptacao_aguardando"])}</text>')
    altura = rodape_y + 16

    marca = []
    if c.get("rascunho"):
        cx_, cy_ = largura / 2, altura / 2
        # opacidade no grupo (e não fill-opacity no texto): o MuPDF, que gera o PNG, ignora fill-opacity em <text>
        marca.append(f'<g opacity="0.16"><text x="{cx_}" y="{cy_}" text-anchor="middle" font-size="52" font-weight="bold" '
                     f'fill="#b91c1c" transform="rotate(-28 {cx_} {cy_})">'
                     f'{_x(esquema.MARCA_RASCUNHO)}</text></g>')

    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" '
        f'viewBox="0 0 {largura} {altura}" font-family="Helvetica, Arial, sans-serif" font-size="{_FONTE}">',
        f"<title>PRISMA 2020{' — ' + esquema.MARCA_RASCUNHO if c.get('rascunho') else ''}</title>",
        f'<rect x="0" y="0" width="{largura}" height="{altura}" fill="#ffffff"/>',
        *cabecalho, *fases_svg, *corpo, *setas, *rodape, *marca,
        "</svg>",
    ]) + "\n"


# ---------------------------------------------------------------------------
# Checklist
# ---------------------------------------------------------------------------
# Lista embutida (usada só se assets/checklists/<arquivo>.csv não existir). Um teste garante
# que a lista embutida do PRISMA 2020 bate com o CSV.
CHECKLIST_2020_EMBUTIDO = [
    ("1", "Título", "Título", "Identificar o trabalho como revisão sistemática."),
    ("2", "Resumo", "Resumo", "Seguir o checklist PRISMA 2020 para resumos."),
    ("3", "Introdução", "Justificativa", "Explicar por que a revisão é necessária diante do conhecimento existente."),
    ("4", "Introdução", "Objetivos", "Declarar de forma explícita os objetivos ou perguntas da revisão."),
    ("5", "Métodos", "Critérios de elegibilidade", "Especificar critérios de inclusão e exclusão e como os estudos foram agrupados para as sínteses."),
    ("6", "Métodos", "Fontes de informação", "Listar bases, registros, sites, organizações, listas de referências e outras fontes consultadas, com a data da última consulta a cada uma."),
    ("7", "Métodos", "Estratégia de busca", "Apresentar as estratégias de busca completas de cada base, registro e site, com filtros e limites."),
    ("8", "Métodos", "Processo de seleção", "Descrever como se decidiu a inclusão: quantos revisores avaliaram cada registro e relatório, se de forma independente e, se houver, as ferramentas de automação usadas."),
    ("9", "Métodos", "Processo de coleta de dados", "Descrever como os dados foram extraídos dos relatórios: quantos revisores, independência, confirmação com autores e ferramentas de automação usadas."),
    ("10a", "Métodos", "Itens de dados", "Listar e definir os desfechos buscados e dizer se todos os resultados compatíveis com cada domínio foram coletados; se não, como se escolheu quais coletar."),
    ("10b", "Métodos", "Itens de dados", "Listar e definir as demais variáveis coletadas e os pressupostos adotados para informação ausente ou pouco clara."),
    ("11", "Métodos", "Avaliação do risco de viés dos estudos", "Especificar as ferramentas de risco de viés, quantos revisores avaliaram cada estudo, se de forma independente e as ferramentas de automação usadas."),
    ("12", "Métodos", "Medidas de efeito", "Especificar para cada desfecho as medidas de efeito usadas na síntese ou apresentação."),
    ("13a", "Métodos", "Métodos de síntese", "Descrever como se decidiu quais estudos entram em cada síntese."),
    ("13b", "Métodos", "Métodos de síntese", "Descrever a preparação dos dados para síntese, como tratamento de estatísticas ausentes e conversões."),
    ("13c", "Métodos", "Métodos de síntese", "Descrever como os resultados individuais e as sínteses foram tabulados ou exibidos graficamente."),
    ("13d", "Métodos", "Métodos de síntese", "Descrever e justificar os métodos de síntese; em meta-análise, informar modelo, avaliação da heterogeneidade e software."),
    ("13e", "Métodos", "Métodos de síntese", "Descrever métodos para explorar causas de heterogeneidade, como subgrupos e meta-regressão."),
    ("13f", "Métodos", "Métodos de síntese", "Descrever as análises de sensibilidade usadas para testar a robustez dos resultados."),
    ("14", "Métodos", "Avaliação de viés de relato", "Descrever como se avaliou o risco de viés por resultados ausentes numa síntese."),
    ("15", "Métodos", "Avaliação da certeza", "Descrever como se avaliou a certeza ou confiança no corpo de evidências de cada desfecho."),
    ("16a", "Resultados", "Seleção dos estudos", "Relatar o resultado da busca e da seleção, do número de registros identificados ao de estudos incluídos, de preferência com fluxograma."),
    ("16b", "Resultados", "Seleção dos estudos", "Citar estudos que pareciam elegíveis mas foram excluídos e explicar o motivo."),
    ("17", "Resultados", "Características dos estudos", "Citar cada estudo incluído e apresentar suas características."),
    ("18", "Resultados", "Risco de viés nos estudos", "Apresentar a avaliação de risco de viés de cada estudo incluído."),
    ("19", "Resultados", "Resultados dos estudos individuais", "Para cada desfecho e estudo, apresentar estatísticas por grupo quando couber e a estimativa de efeito com sua precisão, de preferência em tabelas ou gráficos."),
    ("20a", "Resultados", "Resultados das sínteses", "Resumir as características e o risco de viés dos estudos que contribuem para cada síntese."),
    ("20b", "Resultados", "Resultados das sínteses", "Apresentar os resultados de todas as sínteses estatísticas; em meta-análise, estimativa agregada, precisão e heterogeneidade; ao comparar grupos, a direção do efeito."),
    ("20c", "Resultados", "Resultados das sínteses", "Apresentar os resultados das investigações sobre causas de heterogeneidade."),
    ("20d", "Resultados", "Resultados das sínteses", "Apresentar os resultados das análises de sensibilidade."),
    ("21", "Resultados", "Vieses de relato", "Apresentar a avaliação do risco de viés por resultados ausentes em cada síntese avaliada."),
    ("22", "Resultados", "Certeza da evidência", "Apresentar a avaliação da certeza ou confiança no corpo de evidências de cada desfecho avaliado."),
    ("23a", "Discussão", "Discussão", "Interpretar os resultados à luz de outras evidências."),
    ("23b", "Discussão", "Discussão", "Discutir as limitações das evidências incluídas."),
    ("23c", "Discussão", "Discussão", "Discutir as limitações dos processos da revisão."),
    ("23d", "Discussão", "Discussão", "Discutir implicações para a prática, a política e pesquisas futuras."),
    ("24a", "Outras informações", "Registro e protocolo", "Informar o registro da revisão (nome do registro e número) ou declarar que não foi registrada."),
    ("24b", "Outras informações", "Registro e protocolo", "Indicar onde o protocolo pode ser acessado ou declarar que não houve protocolo."),
    ("24c", "Outras informações", "Registro e protocolo", "Descrever e justificar emendas ao registro ou ao protocolo."),
    ("25", "Outras informações", "Apoio", "Descrever fontes de apoio financeiro ou não financeiro e o papel dos financiadores."),
    ("26", "Outras informações", "Conflitos de interesse", "Declarar conflitos de interesse dos autores."),
    ("27", "Outras informações", "Disponibilidade de dados, código e materiais", "Informar quais materiais estão públicos e onde: formulários de coleta, dados extraídos, dados das análises, código e outros materiais."),
]

# PRISMA-ScR (Tricco et al. 2018): 20 itens essenciais + 2 opcionais (12 e 16), paráfrase curta.
CHECKLIST_SCR_EMBUTIDO = [
    ("1", "Título", "Título", "Identificar o trabalho como revisão de escopo."),
    ("2", "Resumo", "Resumo estruturado", "Resumir contexto, objetivos, critérios, fontes, métodos de mapeamento, resultados e conclusões."),
    ("3", "Introdução", "Justificativa", "Explicar a revisão diante do que já se sabe e por que o formato de escopo é adequado."),
    ("4", "Introdução", "Objetivos", "Declarar perguntas e objetivos com seus elementos (por exemplo, população, conceito e contexto)."),
    ("5", "Métodos", "Protocolo e registro", "Informar se há protocolo, onde acessá-lo e o registro, se houver."),
    ("6", "Métodos", "Critérios de elegibilidade", "Especificar as características das fontes usadas como critérios e justificá-las."),
    ("7", "Métodos", "Fontes de informação", "Descrever todas as fontes consultadas e a data da busca mais recente."),
    ("8", "Métodos", "Busca", "Apresentar a estratégia completa de pelo menos uma base, com limites, de forma reprodutível."),
    ("9", "Métodos", "Seleção das fontes de evidência", "Descrever o processo de seleção (triagem e elegibilidade)."),
    ("10", "Métodos", "Processo de mapeamento dos dados", "Descrever como os dados foram mapeados, com formulários testados, independência e confirmação com autores."),
    ("11", "Métodos", "Itens de dados", "Listar e definir as variáveis buscadas e os pressupostos."),
    ("12", "Métodos", "Avaliação crítica das fontes (opcional)", "Se feita, justificar e descrever os métodos e o uso dos resultados."),
    ("13", "Métodos", "Síntese dos resultados", "Descrever como os dados mapeados foram tratados e resumidos."),
    ("14", "Resultados", "Seleção das fontes de evidência", "Informar números triados, avaliados e incluídos, com motivos de exclusão, de preferência em fluxograma."),
    ("15", "Resultados", "Características das fontes", "Apresentar as características de cada fonte de evidência mapeada."),
    ("16", "Resultados", "Avaliação crítica nas fontes (opcional)", "Se feita, apresentar os dados da avaliação crítica."),
    ("17", "Resultados", "Resultados das fontes individuais", "Apresentar os dados relevantes de cada fonte em relação às perguntas."),
    ("18", "Resultados", "Síntese dos resultados", "Resumir e apresentar os resultados do mapeamento em relação às perguntas."),
    ("19", "Discussão", "Resumo das evidências", "Resumir os principais achados e conectá-los às perguntas e ao público."),
    ("20", "Discussão", "Limitações", "Discutir as limitações do processo de revisão de escopo."),
    ("21", "Discussão", "Conclusões", "Interpretar os resultados em relação às perguntas e apontar implicações e próximos passos."),
    ("22", "Financiamento", "Financiamento", "Descrever fontes de financiamento das fontes incluídas e da revisão e o papel dos financiadores."),
]


def carregar_checklist(tipo="2020"):
    """Itens do checklist: CSV em assets/checklists/ se existir; senão a lista embutida."""
    arquivo = DIR_CHECKLISTS / ("prisma2020.csv" if tipo == "2020" else "prisma_scr.csv")
    linhas = _ler_csv(arquivo)
    if linhas and {"item", "secao", "topico", "descricao"} <= set(linhas[0]):
        return [{k: l[k] for k in ("item", "secao", "topico", "descricao")} for l in linhas], str(arquivo.name)
    embutido = CHECKLIST_2020_EMBUTIDO if tipo == "2020" else CHECKLIST_SCR_EMBUTIDO
    return [dict(zip(("item", "secao", "topico", "descricao"), it)) for it in embutido], "embutido"


def _evidencias(raiz, estado_projeto, tipo):
    """Pistas de onde o projeto já tem material para cada item (não afirma que o item está cumprido)."""
    if raiz is None:
        return {}
    raiz = Path(raiz)
    ev = {}

    def existe(rel):
        return (raiz / rel).exists()

    def arquivos(pasta, padrao="*"):
        p = raiz / pasta
        return sorted(str(x.relative_to(raiz)) for x in p.glob(padrao) if x.is_file()) if p.exists() else []

    buscas = (estado_projeto or {}).get("buscas") or []
    if buscas:
        fontes = sorted({f"{rotulo_fonte(b.get('fonte'), b)} ({b.get('executada_em') or 'data?'})" for b in buscas})
        ev["fontes"] = "estado.buscas: " + "; ".join(fontes)
    if arquivos("01-busca/strings"):
        ev["strings"] = "; ".join(arquivos("01-busca/strings")[:5])
    if existe(esquema.ARQ_DECISOES):
        ev["selecao"] = esquema.ARQ_DECISOES + "; " + "; ".join(arquivos("02-triagem/validacao")[:3])
    if existe(esquema.ARQ_EFEITOS_EXTRAIDOS) or arquivos("05-decomposicao"):
        ev["coleta"] = "; ".join(arquivos("05-decomposicao")[:5])
    if arquivos("04-qualidade"):
        ev["rob"] = "; ".join(arquivos("04-qualidade")[:5])
    if arquivos("06-analise"):
        ev["sintese"] = "; ".join(arquivos("06-analise")[:5])
    ev["fluxograma"] = f"{ARQ_SVG}; {ARQ_PNG}; {ARQ_MERMAID}"
    if existe(esquema.ARQ_ELEGIBILIDADE_TC_FINAL):
        ev["excluidos_tc"] = esquema.ARQ_ELEGIBILIDADE_TC_FINAL + " (decisao=excluir, criterio_falhou)"
    if existe(esquema.ARQ_INCLUIDOS):
        ev["incluidos"] = esquema.ARQ_INCLUIDOS
    protocolo = arquivos("00-protocolo", "protocolo*")
    if protocolo:
        ev["protocolo"] = "; ".join(protocolo)
    emendas = [e for e in estado.ler_log(raiz) if e.get("evento") == "emenda_protocolo"]
    if emendas:
        ev["emendas"] = f"rs_log.jsonl: {len(emendas)} evento(s) emenda_protocolo"
    if existe(esquema.ARQ_REGISTROS):
        ev["dados"] = "dados/ (registros, decisões) e scripts versionados"
    if tipo == "2020":
        mapa = {"6": "fontes", "7": "strings", "8": "selecao", "9": "coleta", "10a": "coleta", "10b": "coleta",
                "11": "rob", "13d": "sintese", "16a": "fluxograma", "16b": "excluidos_tc", "17": "incluidos",
                "18": "rob", "20b": "sintese", "24b": "protocolo", "24c": "emendas", "27": "dados"}
    else:
        mapa = {"5": "protocolo", "7": "fontes", "8": "strings", "9": "selecao", "10": "coleta", "11": "coleta",
                "14": "fluxograma", "15": "incluidos", "18": "sintese"}
    return {item: ev[chave] for item, chave in mapa.items() if chave in ev}


def gerar_checklist(raiz, estado_projeto, tipo="2020"):
    itens, origem = carregar_checklist(tipo)
    evid = _evidencias(raiz, estado_projeto, tipo)
    linhas = []
    for it in itens:
        e = evid.get(it["item"], "")
        linhas.append({**it, "local_no_relato": "", "status": "material_disponivel" if e else "a_preencher",
                       "evidencia_no_projeto": e})
    return linhas, origem


# ---------------------------------------------------------------------------
# Escrita e CLI
# ---------------------------------------------------------------------------
def _escrever_texto(caminho, conteudo, newline=None):
    """Escrita atômica com permissão de arquivo comum (estado.escrever_atomico)."""
    estado.escrever_atomico(caminho, conteudo, newline=newline)


def escrever_saidas(c, pasta, idioma, linhas_checklist):
    pasta = Path(pasta)
    publico = {k: v for k, v in c.items() if not k.startswith("_")}
    _escrever_texto(pasta / "prisma_contagens.json", json.dumps(publico, ensure_ascii=False, indent=2) + "\n")
    _escrever_texto(pasta / "prisma.mermaid", gerar_mermaid(c, idioma))
    _escrever_texto(pasta / "prisma.svg", gerar_svg(c, idioma))
    caminho_chk = pasta / "checklist_prisma.csv"
    buffer = io.StringIO(newline="")
    w = csv.DictWriter(buffer, fieldnames=COLUNAS_CHECKLIST_SAIDA)
    w.writeheader()
    w.writerows(linhas_checklist)
    _escrever_texto(caminho_chk, buffer.getvalue(), newline="")
    return [pasta / "prisma_contagens.json", pasta / "prisma.mermaid", pasta / "prisma.svg", caminho_chk]


def _carregar_pymupdf():
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        try:
            import fitz
            return fitz
        except ImportError:
            return None


def png_disponivel():
    return _carregar_pymupdf() is not None


def escrever_png(svg_texto, caminho, zoom=2.0):
    """Rasteriza o SVG em PNG com pymupdf (DOCX sem rsvg-convert perde o SVG). Devolve None ou o aviso.

    Nunca derruba o comando: sem pymupdf ou com falha de conversão, o SVG continua sendo a saída.
    """
    pymupdf = _carregar_pymupdf()
    caminho = Path(caminho)
    if pymupdf is None:
        return "pymupdf ausente: prisma.png não gerado (use prisma.svg ou instale pymupdf)"
    tmp = caminho.with_name(caminho.name + ".tmp.png")
    try:
        doc = pymupdf.open(stream=svg_texto.encode("utf-8"), filetype="svg")
        try:
            pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            caminho.parent.mkdir(parents=True, exist_ok=True)
            pix.save(str(tmp))
        finally:
            doc.close()
        tmp.replace(caminho)
    except Exception as e:  # noqa: BLE001 - qualquer falha do MuPDF vira aviso, nunca erro
        if tmp.exists():
            tmp.unlink()
        return f"falha ao converter prisma.svg em PNG com pymupdf ({type(e).__name__}: {e}); use prisma.svg"
    return None


def _idioma_padrao(estado_projeto):
    idioma = ((estado_projeto or {}).get("projeto") or {}).get("idioma_produtos", "pt-BR") or "pt-BR"
    return "en" if idioma.lower().startswith("en") else "pt"


def comando(args):
    raiz = estado.encontrar_projeto(args.dir)
    try:
        est = estado.carregar_estado(raiz) if raiz else None
    except estado.ErroProjeto as e:
        print(f"erro: {e}", file=sys.stderr)
        estado.resumo({"ok": False, "erro": "estado_invalido", "detalhe": str(e)})
        return 1
    tipo = args.tipo or tipo_padrao(est)
    idioma = args.idioma or _idioma_padrao(est)

    if args.manual:
        try:
            with open(args.manual, encoding="utf-8") as f:
                dados = json.load(f)
            c = de_manual(dados, tipo)
        except (OSError, json.JSONDecodeError, ErroManual) as e:
            print(f"erro: não consegui usar {args.manual}: {e}", file=sys.stderr)
            estado.resumo({"ok": False, "erro": "manual_invalido", "detalhe": str(e)})
            return 1
        if est:
            marcar_rascunho(c, est)
        pasta = Path(args.saida) if args.saida else (raiz / "07-relatorio" if raiz else Path(args.manual).resolve().parent)
    else:
        if raiz is None:
            print("erro: nenhum projeto encontrado. Use `rs.py prisma --manual contagens.json` ou `rs.py init`.",
                  file=sys.stderr)
            estado.resumo({"ok": False, "erro": "sem_projeto"})
            return 1
        c = calcular(raiz, est, tipo)
        pasta = Path(args.saida) if args.saida else raiz / "07-relatorio"

    quebradas = invariantes_quebradas(c)
    if quebradas:
        for q in quebradas:
            print(f"INVARIANTE QUEBRADA [{q['ramo']}] {q['nome']}: {q['detalhe']}", file=sys.stderr)
        if raiz and not args.manual:
            estado.registrar_evento(raiz, "erro", "11_relato", "script", "prisma",
                                    dados={"comando": "prisma", "invariantes_quebradas": quebradas})
        estado.resumo({"ok": False, "erro": "invariantes_quebradas", "invariantes": quebradas,
                       "avisos": c["avisos"]})
        return 2

    linhas_chk, origem_chk = gerar_checklist(raiz, est, tipo)
    hash_insumos = estado.sha256_texto(json.dumps(
        {"insumos": c["insumos"], "manual": estado.sha256_arquivo(args.manual) if args.manual else None,
         "tipo": tipo, "idioma": idioma, "pendencias": c["pendencias_abertas"], "saida": str(pasta),
         "truncadas": c.get("buscas_truncadas") or []},
        sort_keys=True))
    nomes_saida = ["prisma_contagens.json", "prisma.mermaid", "prisma.svg", "checklist_prisma.csv"]
    exigir_png = png_disponivel()  # sem pymupdf o PNG nunca existirá: não força regeneração a cada execução
    cache = (est or {}).get("contagens_cache", {}).get("prisma") or {}
    reexecucao = bool(est and cache.get("hash_insumos") == hash_insumos
                      and all((pasta / n).exists() for n in nomes_saida + (["prisma.png"] if exigir_png else [])))
    resumo_base = {
        "ok": True, "tipo": tipo, "origem": c["origem"], "idioma": idioma,
        "incluidos": c["incluidos"], "rascunho": c["rascunho"], "pendencias_abertas": c["pendencias_abertas"],
        "buscas_truncadas": c.get("buscas_truncadas") or [], "motivos_rascunho": c.get("motivos_rascunho") or [],
        "etapas_nr": c["etapas_nr"], "avisos": list(c["avisos"]), "checklist_origem": origem_chk,
        "saida": str(pasta),
    }

    def relativos(nomes):
        if not raiz:
            return None
        try:
            return [str((pasta / n).relative_to(raiz)) for n in nomes]
        except ValueError:
            return None

    if reexecucao:
        existentes = nomes_saida + (["prisma.png"] if (pasta / "prisma.png").exists() else [])
        estado.resumo({**resumo_base, "reexecucao": True, "arquivos": relativos(existentes)})
        return 0

    escritos = escrever_saidas(c, pasta, idioma, linhas_chk)
    aviso_png = escrever_png(gerar_svg(c, idioma), pasta / "prisma.png")
    if aviso_png:
        print(f"aviso: {aviso_png}", file=sys.stderr)
        resumo_base["avisos"].append(aviso_png)
        if (pasta / "prisma.png").exists():
            (pasta / "prisma.png").unlink()  # PNG antigo não pode ficar ao lado de um SVG novo
    else:
        escritos.append(pasta / "prisma.png")
    saidas_rel = relativos(nomes_saida + ([] if aviso_png else ["prisma.png"]))
    if raiz:
        est = estado.carregar_estado(raiz)
        est.setdefault("contagens_cache", {})["prisma"] = {
            "hash_insumos": hash_insumos, "gerado_em": c["gerado_em"], "incluidos": c["incluidos"]}
        estado.registrar_evento(
            raiz, "prisma_gerado", "11_relato", "script", "prisma",
            dados={"tipo": tipo, "origem": c["origem"], "incluidos": c["incluidos"], "rascunho": c["rascunho"],
                   "buscas_truncadas": c.get("buscas_truncadas") or [], "etapas_nr": c["etapas_nr"],
                   "hash_insumos": hash_insumos},
            artefatos=saidas_rel, estado=est)
    estado.resumo({**resumo_base, "reexecucao": False,
                   "arquivos": saidas_rel if saidas_rel else [str(p) for p in escritos]})
    return 0


def registrar(subparsers):
    p = subparsers.add_parser(
        "prisma", help="fluxograma PRISMA 2020/ScR calculado do ledger (JSON, Mermaid, SVG, checklist)",
        description="Calcula as contagens PRISMA a partir das tabelas do projeto, checa invariantes (exit 2 se "
                    "não fecham) e escreve prisma_contagens.json, prisma.mermaid, prisma.svg, prisma.png e checklist_prisma.csv.")
    p.add_argument("--tipo", choices=["2020", "scr"], default=None,
                   help="modelo: PRISMA 2020 ou PRISMA-ScR (padrão: scr para escopo/mapa_evidencias, senão 2020)")
    p.add_argument("--manual", metavar="contagens.json", help="contagens digitadas (mesma estrutura de prisma_contagens.json)")
    p.add_argument("--saida", metavar="PASTA", help="pasta de saída (padrão: 07-relatorio/ do projeto)")
    p.add_argument("--idioma", choices=["pt", "en"], help="idioma dos rótulos (padrão: idioma dos produtos)")
    p.set_defaults(func=comando)
