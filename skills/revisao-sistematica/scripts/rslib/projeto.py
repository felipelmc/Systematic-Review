"""Projeto de revisão: init, status, portões, pendências e emendas (e registra `ambiente`).

USO
    python3 rs.py init --titulo "Efeito de X sobre Y" [--tipo oqf_mista_sequencial] [--variante rapida]
                       [--autonomia checkpoints|autopiloto] [--triagem subagentes|api]
                       [--parcial triagem|meta|prisma] [--idioma pt-BR] [--adotar] [--sem-r]
    python3 rs.py init --autonomia autopiloto          # projeto existente: muda modo/triagem sem --titulo
    python3 rs.py status
    python3 rs.py ambiente [--sem-r]
    python3 rs.py portao G4 --aprovar --por revisor_humano_1 [--criterios '{"recall_li": 0.93}'] [--motivo ...]
    python3 rs.py portao G4 --reprovar --por revisor_humano_1 --motivo "recall abaixo do limiar"
    python3 rs.py portao G7 --nao-se-aplica --por revisor_humano_1 --motivo "escopo: sem RoB (JBI)"
    python3 rs.py portao G4 --aprovar --por revisor_humano_1 --forcar --motivo "..."   # bloqueios ficam no log
    python3 rs.py pendencia listar [--todas]
    python3 rs.py pendencia abrir --tipo validacao_humana --etapa 06_triagem_ta --descricao "..." [--portao G4] [--n 120]
    python3 rs.py pendencia fechar P003 --motivo "amostra codificada" [--por revisor_humano_1]
    python3 rs.py emenda --arquivo 00-protocolo/protocolo.md --motivo "novo critério de idioma"

Por que existe
    O estado precisa sobreviver entre sessões sem que ninguém edite JSON à mão.
    `status` é o primeiro comando de toda sessão: ele NÃO confia no cache rs_estado.json.
    Recalcula o status de cada etapa a partir do log de portões e dos artefatos em disco,
    aponta inconsistências (artefato congelado alterado sem emenda, contagens que não fecham,
    estado atrás do log) e devolve a próxima ação como um comando exato ou um portão.

Decisões
    - `init` é idempotente: rodar de novo não recria estado nem duplica `projeto_criado`;
      só cria pastas que faltam e registra `modo_definido` se o modo mudou de fato.
    - `init` recusa pasta com artefatos da skill sem `--adotar` (evita "iniciar por cima"
      de uma revisão existente), pasta dentro de outro projeto e pasta que contém projeto em
      subpasta (até 2 níveis; com ou sem `--adotar`): o certo é retomar com `--dir <subpasta> status`.
    - `status` sem projeto procura rs_estado.json em subpastas (até 2 níveis) e sugere
      `--dir <subpasta> status`; arquivos de dentro de um projeto e arquivos canônicos da skill
      (registros*.csv, log_buscas.csv, exploracao_*.csv...) nunca são sugeridos como exportação.
      Exportação OpenAlex em CSV é reconhecida pelo cabeçalho (authorships.* ou display_name +
      publication_year), nunca pelo conteúdo.
    - Projetos parciais marcam etapas como ignoradas; o PRISMA mostra NR nelas.
    - Portões: aprovação por papel (`--por`), nunca por nome. Em checkpoints, só humano
      aprova. No autopiloto, G1 e G2 continuam humanos; G3–G9 podem ser aprovados como
      `autopiloto`, mas cada aprovação automática abre uma pendência de revisão humana
      (os produtos saem como rascunho até ela ser fechada).
    - Checagens antes de aprovar (checar_portao) saem com código 2. Um humano pode forçar com
      `--forcar --motivo`, e o forçamento (com os bloqueios) fica no log. No autopiloto só barram
      os bloqueios `artefato` e `limiar`; os que dependem de humano viram pendência.
        G1  pergunta preenchida e tipo_revisao diferente de "indefinido" (dos critérios ou do estado)
        G2  00-protocolo/protocolo*, 00-protocolo/codebook_v0*.csv e codebook de elegibilidade
            (00-protocolo/codebook_elegibilidade*.csv ou 03-textos/codebook_elegibilidade*.csv), sem
            placeholders <...> ou {...} no protocolo nem {...} nos codebooks (artefato); aviso sem
            00-protocolo/revisao_metodologica* (revisor metodológico)
        G3  alguma busca ativa, exportação em 01-busca/brutos ou registros importados (artefato);
            nenhuma busca ativa com truncada = true (limiar); PRESS registrado em 01-busca/press_*.md
            ou pendência revisao_press aberta (artefato); avisos (não barram) sem
            01-busca/recall_ancoras.json ou com recall combinado < 1 (lista as âncoras não achadas)
        G4  triagem_ta_final.csv e a última validacao_calculada com finalidade "validacao" da rodada
            em versoes_ativas.rodada_ta (evento sem finalidade conta como validação, com aviso).
            Variante rápida (projeto.variante = rapida e critério atalho_rapida aprovado no G1): vale
            também a validação com dados.atalho_rapida = true, que dispensa recall >= 0,95 mas exige
            dupla humana em >= 20% (fracao_dupla_humana, ou n_dupla_humana/n_populacao), κ calculado
            (kappa_humanos) e segunda leitura humana de todos os excluídos pela IA
            (segunda_leitura_excluidos = true, ou n_excluidos_relidos >= n_excluidos_ia)
        G5  elegibilidade_tc_final.csv e contagens que fecham
        G6  piloto consolidado: evento extracao_consolidada ou 05-decomposicao/**/fichamentos_master*.csv
        G7  com efeitos_extraidos.csv: verificação atual (verificacao_efeitos.csv posterior à última
            mudança dos efeitos), sem trecho/plausibilidade reprovados e sem linha não apta (humano);
            fora de esquema.TIPOS_SEM_ROB, por ferramenta: último rob_consolidado com artefatos que não
            mudaram, sem fase 1 pendente de fase 2 e cobrindo as ferramentas de resultados_avaliados.csv
            (artefato), com todos_validados_humano = true (validacao), e rob_geral para todo resultado
            avaliado (resultados_avaliados.csv ou chave × construto dos efeitos; artefato); avisos sem
            concordancia.csv da extração ou com variáveis sinalizadas sem arbitragem registrada
            (pendência concordancia_extracao fechada para o arquivo)
        G8  nenhuma linha de caixa_ferramentas.csv com status_rotulo diferente de "definido"; caixa
            obrigatória em oqf_mista_sequencial (artefato); 06-analise/certeza.csv (artefato, salvo em
            TIPOS_SEM_CERTEZA) com linha de certeza para cada célula de efeito da caixa (certeza); com a
            etapa 09 ignorada, aviso de efeitos calculados sem verificado_humano
        G9  prisma_gerado cujos insumos e pendências batem com os atuais, e declaração de uso de IA; avisos
            sem 07-relatorio/references.bib e com declaração que cobre o log só até um seq anterior ao
            último evento relevante (fora os da própria declaração e as reexecuções sem mudança). O seq
            coberto vem de dados.ultimo_seq do evento relatorio_gerado cuja cópia do arquivo (sha256)
            é a atual; sem esse evento, a declaração é tratada como escrita ou editada à mão
      Pendências abertas do portão ou da etapa sempre entram como bloqueio.
    - G1 aprovado com `--criterios '{"pergunta": ..., "tipo_revisao": ..., "variante": "rapida"}'`
      grava esses campos no estado: a pergunta e o tipo são exatamente o que o G1 aprova.
    - G2 congela os arquivos de 00-protocolo/ (sha256), G3 as strings (01-busca/strings/) e os
      filtros (01-busca/filtros_*.json) e G4 os critérios em 02-triagem/prompts/. Mudar um arquivo
      congelado exige `rs.py emenda`, que registra `emenda_protocolo`.
    - `portao GN --nao-se-aplica --motivo` só vale para os portões que o tipo de revisão dispensa
      (esquema.PORTOES_OPCIONAIS_POR_TIPO, ex.: G7 e G8 em escopo) e depois do G1. Registra
      `etapa_nao_aplicavel`; o status passa a tratar a etapa como ignorada e não exige o portão.
    - `init --variante rapida` guarda projeto.variante (revisão rápida como variante de um tipo de
      origem, references/tipos-de-revisao.md, seção 6), sem mudar TIPOS_REVISAO.
    - `status` marca rascunho com pendências abertas, com a última caixa gerada com células
      pendentes ou com busca ativa truncada; alerta buscas ativas truncadas (busca_truncada), sem
      data (busca_sem_data, calado quando 04_busca está ignorada) ou executadas há mais de 12 meses
      (references/02-busca.md, seção 11); ignora buscas substituídas (ativa: false) nas contagens.
    - `proxima_acao` nunca inventa valores de critério: onde o valor depende de conferência, o
      comando traz um placeholder explícito entre <> (ex.: <valor de 01-busca/recall_ancoras.json>),
      que não é JSON válido e falha se colado sem preencher. Com A e B mesclados e divergências sem
      árbitro (triagem por subagentes), sugere `triagem preparar --revisor arbitro
      --apenas-divergentes` antes de `triagem consolidar`.
    - `status` chamado com `--dir` devolve todo `$RS ...` sugerido com o mesmo `--dir` (com_dir). Busca
      truncada feita pela API do OpenAlex se refaz com `buscar openalex ... --substituir` (a consulta vem
      do estado); `importar --substituir` só para exportações. `dedup --revisar` sai com `--por`.
    - No autopiloto, tarefa humana com pendência aberta da etapa vem com `exige_humano`, `pendencia` e
      `alternativa`/`acao_seguinte` (o próximo passo que não depende dela). Com todas as etapas feitas,
      `fim` só sem motivo de rascunho e sem G8 forçado com bloqueio vigente; senão, tarefa na etapa
      seguinte. G4 reprovado segue `motivo_reprovacao` (largura_ic: ampliar amostra ou elusão).
    - Na pasta-mãe com vários projetos, `projetos` traz título, etapa atual e último evento de cada um.
    - Papel humano padrão: esquema.PAPEL_HUMANO_PADRAO.
"""

import argparse
import collections
import csv
import datetime as _dt
import json
import os
import re
import shlex
import sys
from pathlib import Path

from . import ambiente, esquema, estado, normalizar, prisma

RS = "$RS"  # abreviação de python3 "<pasta da skill>/scripts/rs.py" (a função rs() do SKILL.md), não uma variável

ETAPAS_PARCIAL = {
    "triagem": ["00_configuracao", "05_organizacao", "06_triagem_ta"],
    "meta": ["00_configuracao", "10_sintese"],
    "prisma": ["00_configuracao", "11_relato"],
}
ARTEFATOS_CANONICOS = [
    esquema.ARQ_REGISTROS, esquema.ARQ_UNICOS, esquema.ARQ_DECISOES, esquema.ARQ_DEDUP_PARES,
    esquema.ARQ_FILTRO_FORMAL, esquema.ARQ_TRIAGEM_TA_FINAL, esquema.ARQ_ELEGIBILIDADE_TC_FINAL,
    esquema.ARQ_PARA_BAIXAR, esquema.ARQ_RELATORIO_PDFS, esquema.ARQ_VERIFICACAO_CONTEUDO,
    esquema.ARQ_INVENTARIO_TEXTOS, esquema.ARQ_EFEITOS_EXTRAIDOS, esquema.ARQ_INCLUIDOS,
]
# portão -> [(pasta, padrão, recursivo)]; arquivos "emenda*" nunca são congelados.
CONGELAR_NO_PORTAO = {
    "G2": [("00-protocolo", "*", False)],
    "G3": [("01-busca/strings", "*", True), ("01-busca", "filtros_*.json", False)],
    "G4": [("02-triagem/prompts", "*.md", False)],
}
VARIANTES = esquema.VARIANTES_REVISAO
MESES_BUSCA_DESATUALIZADA = 12
TIPOS_BLOQUEIO_DUROS = ("artefato", "limiar")  # barram inclusive a aprovação automática do autopiloto
PADRAO_TEORIA = re.compile(r"teoria|dag|framework|picoc|cmmo|cmo|pcc|spider|mudanca", re.IGNORECASE)
INVARIANTE_ETAPA = {
    "registros_sem_cluster": "05_organizacao", "ids_registro_desconhecidos": "05_organizacao",
    "filtro_ids_desconhecidos": "05_organizacao", "identificacao_fecha": "05_organizacao",
    "duplicatas_nao_negativo": "05_organizacao", "a_triar_nao_negativo": "05_organizacao",
    "triagem_ids_desconhecidos": "06_triagem_ta", "triagem_de_excluidos_por_automacao": "06_triagem_ta",
    "triagem_fecha": "06_triagem_ta", "triagem_ids_absorvidos": "06_triagem_ta",
    "decisoes_de_busca_substituida": "07_textos_elegibilidade", "avaliado_nao_recuperado": "07_textos_elegibilidade",
    "elegibilidade_ids_absorvidos": "07_textos_elegibilidade",
}
SEM_PROJETO_IGNORAR = {".git", "node_modules", "__pycache__", ".venv", "venv", ".quarto", "_site", "docs"}
PROFUNDIDADE_SUBPROJETOS = 2
PAPEL_HUMANO = esquema.PAPEL_HUMANO_PADRAO
# Nomes de arquivos que a própria skill escreve: nunca são exportações a importar.
PADRAO_ARQUIVO_INTERNO = re.compile(
    r"^(registros(_unicos|_flags)?|log_buscas|exploracao_.+|dedup_pares|filtro_formal(_contagens)?|triagem_ta_final"
    r"|fila_humana_.+|elegibilidade_tc_final|para_baixar|inventario_textos|conferencia_pdfs|retratacoes"
    r"|contato_autores|ligacao_relatos|verificacao_efeitos|efeitos(_extraidos|_para_sintese)?|incluidos"
    r"|prisma_contagens|checklist_prisma|recall_ancoras|caixa_ferramentas|certeza|rob_.+|resultados_avaliados"
    r"|decisoes|rs_log|rs_estado|meta_resumo|swim_resumo|concordancia)(_v\d+)?\.(csv|json|jsonl)$",
    re.IGNORECASE)
COLUNAS_MINIMAS_CODEBOOK = {"dimensao", "variavel", "descricao", "prompt"}
# G2: onde ficam o codebook v0 e o de elegibilidade; extensões de protocolo que dá para ler como texto.
PADRAO_CODEBOOK_V0 = ("00-protocolo", "codebook_v0*.csv")
LOCAIS_CODEBOOK_ELEGIBILIDADE = (("00-protocolo", "codebook_elegibilidade*.csv"), ("03-textos", "codebook_elegibilidade*.csv"))
EXTENSOES_PROTOCOLO_TEXTO = {".md", ".qmd", ".txt", ".markdown", ".rmd", ""}
# G3: PRESS registrado.
PADRAO_PRESS = ("01-busca", "press_*.md")
# Constantes de contrato: valem as de esquema.py quando promovidas (v1.3); os nomes daqui ficam como aliases.
PENDENCIA_PRESS = getattr(esquema, "PENDENCIA_PRESS", "revisao_press")
# G4, variante rápida: critério do G1 e campos esperados no evento validacao_calculada (validar calcular).
CRITERIO_ATALHO_RAPIDA = getattr(esquema, "CRITERIO_ATALHO_RAPIDA", "atalho_rapida")
FRACAO_MINIMA_DUPLA_RAPIDA = getattr(esquema, "FRACAO_MINIMA_DUPLA_RAPIDA", 0.20)
CAMPOS_FRACAO_DUPLA = ("fracao_dupla_humana", "proporcao_dupla_humana")
CAMPOS_N_DUPLA = ("n_dupla_humana",)
CAMPOS_N_POPULACAO = ("n_populacao", "n_populacao_rodada", "n_triados")
CAMPOS_KAPPA_DUPLA = ("kappa_humanos", "kappa_dupla_humana")
# G7: arbitragem humana das variáveis sinalizadas na concordância da extração; lista de resultados avaliados no RoB.
PENDENCIA_CONCORDANCIA = getattr(esquema, "PENDENCIA_CONCORDANCIA", "concordancia_extracao")
ARQ_RESULTADOS_AVALIADOS = getattr(esquema, "ARQ_RESULTADOS_AVALIADOS", "04-qualidade/resultados_avaliados.csv")
FILA_CONSENSO_ROB = getattr(esquema, "PENDENCIA_CONSENSO_ROB", "consenso_rob")  # fila_gerada.dados.fila da fase 1
# G8: tipos sem juízo de certeza por célula (escopo e mapa não avaliam certeza; realista usa enunciado narrativo).
TIPOS_SEM_CERTEZA = set(getattr(esquema, "TIPOS_SEM_CERTEZA", ["escopo", "mapa_evidencias", "realista"]))
# abaixo disso recall >= 0,95 com LI >= 0,90 é inalcançável (remédio 5)
MIN_INCLUIDOS_LIMIAR_ALCANCAVEL = getattr(esquema, "MIN_INCLUIDOS_LIMIAR_ALCANCAVEL", 36)
REF_PORTOES = "references/00-configuracao-estado.md, seção 4"


class ErroUso(RuntimeError):
    """Erro de uso ou de dados (código de saída 1)."""


class ErroMetodologico(RuntimeError):
    """Checagem metodológica falhou (código de saída 2)."""


# ---------------------------------------------------------------------------
# Utilidades de disco
# ---------------------------------------------------------------------------
def _arquivos(raiz, pasta, padrao="*", recursivo=False):
    p = Path(raiz) / pasta
    if not p.exists():
        return []
    it = p.rglob(padrao) if recursivo else p.glob(padrao)
    return sorted(str(x.relative_to(raiz)) for x in it
                  if x.is_file() and not x.name.startswith(".") and not x.name.endswith(".tmp"))


def _existe(raiz, rel):
    return (Path(raiz) / rel).exists()


def _ler_jsonl(caminho):
    linhas = []
    if not Path(caminho).exists():
        return linhas
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            if linha.strip():
                try:
                    linhas.append(json.loads(linha))
                except json.JSONDecodeError:
                    continue
    return linhas


def _procurar_chave(obj, chave):
    """Primeiro valor de `chave` em qualquer nível de um dict/list (eventos de outros módulos variam)."""
    if isinstance(obj, dict):
        if chave in obj:
            return obj[chave]
        for v in obj.values():
            achado = _procurar_chave(v, chave)
            if achado is not None:
                return achado
    elif isinstance(obj, list):
        for v in obj:
            achado = _procurar_chave(v, chave)
            if achado is not None:
                return achado
    return None


# ---------------------------------------------------------------------------
# Detecção de artefatos soltos (status sem projeto, init --adotar)
# ---------------------------------------------------------------------------
def _colunas_cabecalho(primeira):
    """Nomes de coluna da primeira linha (vírgula, ponto e vírgula ou tab; aspas respeitadas)."""
    delimitador = max((",", ";", "\t"), key=primeira.count)
    try:
        campos = next(csv.reader([primeira], delimiter=delimitador))
    except (csv.Error, StopIteration):
        campos = primeira.split(delimitador)
    return [c.strip().strip('"').strip() for c in campos]


def _chave_coluna(nome):
    return re.sub(r"[^a-z0-9]", "", str(nome).lower())


def _cabecalho_openalex(chaves):
    """Colunas típicas do CSV do OpenAlex (as mesmas que o importador reconhece)."""
    return any(c.startswith("authorships") for c in chaves) or {"displayname", "publicationyear"} <= chaves


def _cheirar(caminho):
    """Classifica um arquivo pelo nome e pelo cabeçalho (nunca pelo conteúdo das linhas)."""
    try:
        with open(caminho, "rb") as f:
            cabeca = f.read(4096).decode("utf-8-sig", errors="ignore")
    except OSError:
        return None
    primeira = cabeca.splitlines()[0] if cabeca.splitlines() else ""
    nome = caminho.name.lower()
    if nome == "relatorio_pdfs.csv" or primeira.startswith("chave,titulo,autores,ano,doi,status"):
        return "handoff_relatorio_pdfs"
    if nome == "verificacao_conteudo.csv":
        return "handoff_verificacao_conteudo"
    if nome.startswith("fichamentos_master"):
        return "handoff_fichamentos_master"
    if nome.startswith("codebook") and nome.endswith(".csv"):
        return "codebook"
    if PADRAO_ARQUIVO_INTERNO.match(nome):
        return None  # arquivo que a própria skill escreve: não é exportação
    if cabeca.startswith(("FN Clarivate", "FN Thomson")):
        return "exportacao_wos_texto"
    if primeira.startswith("PT\tAU"):
        return "exportacao_wos_tsv"
    if "@article{ WOS:" in cabeca or "@article{WOS:" in cabeca:
        return "exportacao_wos_bibtex"
    if nome.endswith(".ris") or re.search(r"^TY  - ", cabeca, re.MULTILINE):
        return "exportacao_ris"
    if nome.endswith(".csv"):
        campos = _colunas_cabecalho(primeira)
        chaves = {_chave_coluna(c) for c in campos}
        if COLUNAS_MINIMAS_CODEBOOK <= {c.lower() for c in campos}:
            return "codebook"
        if "EID" in campos:
            return "exportacao_scopus"
        if "GSRank" in campos:
            return "exportacao_publish_or_perish"
        if "Key" in campos and "Item Type" in campos:
            return "exportacao_zotero"
        if _cabecalho_openalex(chaves):
            return "exportacao_openalex"
    if nome.endswith((".jsonl", ".json")) and re.search(r'"id"\s*:\s*"https://openalex\.org/W\d+', cabeca):
        return "exportacao_openalex"
    if nome.endswith(".bib"):
        return "bibtex"
    if nome.endswith((".xls", ".xlsx")):
        return "planilha"
    return None


def projetos_em_subpastas(pasta, profundidade=PROFUNDIDADE_SUBPROJETOS, limite=20):
    """Subpastas (relativas, até `profundidade` níveis) que já têm rs_estado.json."""
    pasta = Path(pasta)
    achados = []
    for atual, dirs, arquivos in os.walk(pasta):
        rel = Path(atual).relative_to(pasta)
        nivel = len(rel.parts)
        if nivel > 0 and esquema.ARQ_ESTADO in arquivos:
            achados.append(rel.as_posix())
            dirs[:] = []
            if len(achados) >= limite:
                break
            continue
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SEM_PROJETO_IGNORAR) \
            if nivel < profundidade else []
    return sorted(achados)


def _comando_status(dir_=None):
    """`$RS status`, com `--dir` quando o projeto não está na pasta corrente."""
    return f'{RS} --dir "{dir_}" status' if dir_ else f"{RS} status"


_RE_RS_SEM_DIR = re.compile(re.escape(RS) + r" (?!--dir\b)")


def com_dir(valor, dir_):
    """Acrescenta `--dir "<dir>"` a todo `$RS ...` (strings, listas e dicts), quando o comando foi chamado com --dir."""
    if not dir_:
        return valor
    if isinstance(valor, str):
        return _RE_RS_SEM_DIR.sub(lambda _m: f'{RS} --dir "{dir_}" ', valor)
    if isinstance(valor, list):
        return [com_dir(v, dir_) for v in valor]
    if isinstance(valor, dict):
        return {k: com_dir(v, dir_) for k, v in valor.items()}
    return valor


def resumo_subprojeto(raiz):
    """Título, tipo, etapa atual e último evento de um projeto em subpasta (status na pasta-mãe)."""
    try:
        est = estado.carregar_estado(raiz)
        eventos = estado.ler_log(raiz)
        etapas, _ = recalcular_etapas(raiz, est, eventos)
    except Exception as e:  # noqa: BLE001 - um projeto corrompido não impede listar os demais
        return {"titulo": None, "etapa_atual": None, "ultimo_evento_em": None, "erro": str(e)[:200]}
    ultimo = max(eventos, key=lambda ev: int(ev.get("seq") or 0), default=None)
    return {"titulo": (est.get("projeto") or {}).get("titulo"), "tipo_revisao": (est.get("projeto") or {}).get("tipo_revisao"),
            "etapa_atual": next((e for e in esquema.ETAPAS if etapas[e]["status"] not in ("concluida", "ignorada")), None),
            "ultimo_evento_em": (ultimo or {}).get("ts"), "ultimo_evento": (ultimo or {}).get("evento"),
            "n_pendencias_abertas": len(estado.pendencias_abertas(est))}


def detectar_artefatos(pasta, profundidade=3, limite=300):
    """Artefatos canônicos da skill e exportações/handoffs reconhecíveis numa pasta sem estado.

    Subpastas que já são projeto (têm rs_estado.json) não são percorridas: seus arquivos são
    internos daquele projeto, que se retoma com `--dir <subpasta> status`.
    """
    pasta = Path(pasta)
    achados = [{"caminho": rel, "tipo": "canonico"} for rel in ARTEFATOS_CANONICOS if (pasta / rel).exists()]
    canonicos = {a["caminho"] for a in achados}
    vistos = 0
    for atual, dirs, arquivos in os.walk(pasta):
        nivel = len(Path(atual).relative_to(pasta).parts)
        if nivel > 0 and esquema.ARQ_ESTADO in arquivos:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SEM_PROJETO_IGNORAR and nivel < profundidade]
        for nome in sorted(arquivos):
            vistos += 1
            if vistos > limite:
                return achados
            caminho = Path(atual) / nome
            rel = str(caminho.relative_to(pasta))
            if rel in canonicos or nome.startswith("."):
                continue
            tipo = _cheirar(caminho)
            if tipo:
                achados.append({"caminho": rel, "tipo": tipo})
    return achados


def sugestoes_adocao(achados):
    """Comandos para trazer artefatos soltos para o layout do projeto (nada é movido sozinho)."""
    sugestoes, n_busca = [], 0
    destino = {
        "handoff_relatorio_pdfs": esquema.ARQ_RELATORIO_PDFS,
        "handoff_verificacao_conteudo": esquema.ARQ_VERIFICACAO_CONTEUDO,
    }
    for a in achados:
        if a["tipo"].startswith("exportacao") or a["tipo"] in ("bibtex", "planilha"):
            n_busca += 1
            sugestoes.append(f'{RS} importar --arquivo "{a["caminho"]}" --busca-id B{n_busca:02d}')
        elif a["tipo"] in destino and a["caminho"] != destino[a["tipo"]]:
            sugestoes.append(f'copiar "{a["caminho"]}" para {destino[a["tipo"]]}')
        elif a["tipo"] == "handoff_fichamentos_master":
            sugestoes.append(f'usar "{a["caminho"]}" em `{RS} textos elegibilidade consolidar --master ...`')
    return sugestoes


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------
def criar_pastas(raiz):
    criadas = []
    for pasta in esquema.PASTAS_PROJETO:
        p = Path(raiz) / pasta
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            criadas.append(pasta)
    return criadas


def etapas_ignoradas_para(parcial):
    if not parcial:
        return []
    manter = set(ETAPAS_PARCIAL[parcial])
    return [e for e in esquema.ETAPAS if e not in manter]


def cmd_init(args):
    alvo = Path(args.dir or os.getcwd()).resolve()
    existente = (alvo / esquema.ARQ_ESTADO).exists()
    if not existente and not (args.titulo or "").strip():
        raise ErroUso("--titulo é obrigatório para criar um projeto (num projeto existente pode ser omitido)")
    alvo.mkdir(parents=True, exist_ok=True)
    pai = estado.encontrar_projeto(alvo)
    if not existente and pai is not None:
        raise ErroUso(f"já existe um projeto em {pai}; não crio projeto aninhado. Use --dir para outra pasta.")
    if existente:
        return _init_existente(alvo, args)
    subprojetos = projetos_em_subpastas(alvo)
    if subprojetos:
        raise ErroUso("a pasta contém projeto de revisão em subpasta (" + ", ".join(subprojetos[:5]) + "); não crio "
                      "outro projeto por cima dele" + (" nem adoto os arquivos dele" if args.adotar else "") +
                      f". Para retomar: `{_comando_status((Path(args.dir or '.') / subprojetos[0]).as_posix())}`; para um projeto "
                      "novo, use --dir com uma pasta que não contenha outro projeto.")

    achados = detectar_artefatos(alvo)
    canonicos = [a["caminho"] for a in achados if a["tipo"] == "canonico"]
    if canonicos and not args.adotar:
        raise ErroUso("a pasta já tem artefatos da skill (" + ", ".join(canonicos[:5]) +
                      "); use `init --adotar` para adotá-los sem sobrescrever.")
    criadas = criar_pastas(alvo)
    est = estado.estado_inicial(args.titulo, args.tipo or "indefinido", args.idioma or "pt-BR",
                                args.autonomia or "checkpoints", args.triagem or "subagentes", args.parcial)
    ignoradas = etapas_ignoradas_para(args.parcial)
    est["projeto"]["etapas_ignoradas"] = ignoradas
    if args.variante:
        est["projeto"]["variante"] = args.variante
    for etapa in ignoradas:
        est["etapas"][etapa]["status"] = "ignorada"
    adotados = []
    if args.adotar:
        for rel in canonicos:
            est["artefatos"][rel] = {"caminho": rel, "sha256": estado.sha256_arquivo(alvo / rel),
                                     "adotado_em": estado.agora(), "congelado_em": None}
            adotados.append(rel)
    sugestoes = sugestoes_adocao(achados) if args.adotar else []
    estado.salvar_estado(alvo, est)
    estado.registrar_evento(
        alvo, "projeto_criado", "00_configuracao", "script", "init",
        dados={"titulo": args.titulo, "tipo_revisao": est["projeto"]["tipo_revisao"], "modo": est["modo"],
               "variante": args.variante, "parcial": args.parcial, "etapas_ignoradas": ignoradas, "adotado": bool(args.adotar),
               "artefatos_adotados": adotados, "sugestoes": sugestoes},
        artefatos=adotados or None, estado=est)
    diag = ambiente.verificar(incluir_r=not args.sem_r)
    ambiente.gravar_no_estado(alvo, diag)
    estado.resumo({
        "ok": True, "criado": True, "ja_existia": False, "raiz": str(alvo), "pastas_criadas": len(criadas),
        "modo": est["modo"]["autonomia"], "triagem": est["modo"]["triagem"], "parcial": args.parcial,
        "variante": args.variante, "etapas_ignoradas": ignoradas, "artefatos_adotados": adotados, "sugestoes": sugestoes,
        "ambiente": diag["resumo"], "proxima_acao": _comando_status(args.dir),
    })
    return 0


def _init_existente(alvo, args):
    est = estado.carregar_estado(alvo)
    criadas = criar_pastas(alvo)
    avisos, mudancas = [], {}
    if args.titulo and args.titulo != est["projeto"]["titulo"]:
        avisos.append("título diferente do registrado; mantido o do estado")
    if args.parcial and args.parcial != est["projeto"].get("parcial"):
        avisos.append("escopo parcial diferente do registrado; mantido o do estado")
    for campo, valor in (("autonomia", args.autonomia), ("triagem", args.triagem)):
        if valor and valor != est["modo"].get(campo):
            mudancas[campo] = {"de": est["modo"].get(campo), "para": valor}
            est["modo"][campo] = valor
    g1_aprovado = _estado_portoes(estado.ler_log(alvo)).get("G1", {}).get("decisao") == "aprovado"
    for campo, valor, rotulo in (("tipo_revisao", args.tipo, "tipo de revisão"), ("variante", args.variante, "variante")):
        if not valor or valor == est["projeto"].get(campo):
            continue
        if g1_aprovado:
            avisos.append(f"{rotulo} já aprovado no G1; mude por emenda e novo G1, não por init")
        else:
            mudancas[campo] = {"de": est["projeto"].get(campo), "para": valor}
            est["projeto"][campo] = valor
    if mudancas:
        est["modo"]["definido_em"] = estado.agora()
        estado.registrar_evento(alvo, "modo_definido", "00_configuracao", "script", "init",
                                dados={"mudancas": mudancas}, estado=est)
    ambiente_rodado = False
    if not est.get("ambiente"):
        ambiente.gravar_no_estado(alvo, ambiente.verificar(incluir_r=not args.sem_r))
        ambiente_rodado = True
    estado.resumo({"ok": True, "criado": False, "ja_existia": True, "raiz": str(alvo), "pastas_criadas": len(criadas),
                   "mudancas": mudancas, "avisos": avisos, "ambiente_verificado": ambiente_rodado,
                   "proxima_acao": _comando_status(args.dir)})
    return 0


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------
def _estado_portoes(eventos):
    """Última decisão de cada portão segundo o log (fonte de verdade, não o cache)."""
    portoes = {}
    for ev in eventos:
        if ev.get("evento") != "portao":
            continue
        dados = ev.get("dados") or {}
        g = dados.get("portao")
        if g:
            portoes[g] = {"decisao": dados.get("decisao", "aprovado"), "por": (ev.get("ator") or {}).get("id"),
                          "tipo_ator": (ev.get("ator") or {}).get("tipo"), "seq": ev.get("seq"), "ts": ev.get("ts"),
                          "motivo": ev.get("motivo")}
    return portoes


def _nao_aplicaveis(eventos):
    """{portão: evento etapa_nao_aplicavel} quando essa é a última decisão registrada para o portão."""
    ultimo = {}
    for ev in eventos:
        nome = ev.get("evento")
        g = (ev.get("dados") or {}).get("portao")
        if g and nome in ("portao", "etapa_nao_aplicavel"):
            ultimo[g] = ev
    return {g: ev for g, ev in ultimo.items() if ev.get("evento") == "etapa_nao_aplicavel"}


def _buscas_ativas(est):
    return [b for b in (est.get("buscas") or []) if not prisma.busca_inativa(b)]


def _busca_da_api_openalex(busca):
    """Busca registrada por `buscar openalex` (fonte openalex com a consulta ou o JSONL bruto do comando)."""
    return (str((busca or {}).get("fonte") or "").lower() == "openalex"
            and (bool(busca.get("query")) or str(busca.get("arquivo") or "").endswith("_openalex.jsonl")))


def comando_refazer_busca(busca):
    """Comando para registrar a execução completa de uma busca truncada, pela mesma via que a criou.

    Busca da API do OpenAlex: `buscar openalex` com a mesma consulta (query, campo, filtro, string_id do estado) e
    --substituir; exportação manual: `importar --arquivo <exportação completa> --substituir`.
    """
    antigo = (busca or {}).get("id")
    motivo = '--motivo "busca completa, sem --max-paginas"'
    if _busca_da_api_openalex(busca):
        partes = [f"{RS} buscar openalex --busca-id <novo busca_id>",
                  f"--query {shlex.quote(str(busca['query']))}" if busca.get("query")
                  else f"--query <consulta da busca {antigo}, entre aspas>"]
        if busca.get("campo"):
            partes.append(f"--campo {busca['campo']}")
        if busca.get("filtros_na_base"):
            partes.append(f"--filtro {shlex.quote(str(busca['filtros_na_base']))}")
        if busca.get("string_id"):
            partes.append(f"--string-id {shlex.quote(str(busca['string_id']))}")
        return " ".join(partes + [f"--substituir {antigo}", motivo])
    return (f"{RS} importar --arquivo 01-busca/brutos/<exportacao completa> --busca-id <novo busca_id> "
            f'--substituir {antigo} --motivo "busca completa"')


def _dedup_coberto(raiz, est=None):
    """Todo registro de busca ativa está em algum cluster de registros_unicos.csv."""
    regs = prisma._ler_csv(Path(raiz) / esquema.ARQ_REGISTROS)
    unicos = prisma._ler_csv(Path(raiz) / esquema.ARQ_UNICOS)
    if regs is None or unicos is None:
        return False
    inativas = prisma.buscas_inativas(est)
    cobertos = set()
    for u in unicos:
        cobertos.update(i.strip() for i in (u.get("ids_registro") or "").split("|") if i.strip())
    return {r.get("id_registro") for r in regs if (r.get("busca_id") or "") not in inativas} <= cobertos


def _data_busca(valor):
    """Data de execução da busca (ISO AAAA-MM[-DD] ou DD/MM/AAAA) ou None."""
    texto = str(valor or "").strip()
    m = re.match(r"(\d{4})-(\d{2})(?:-(\d{2}))?", texto)
    try:
        if m:
            return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3) or 1))
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
        if m:
            return _dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None
    return None


def _somar_meses(data, meses):
    total = data.year * 12 + data.month - 1 + meses
    ano, mes = divmod(total, 12)
    mes += 1
    ultimo_dia = (_dt.date(ano + (mes == 12), mes % 12 + 1, 1) - _dt.timedelta(days=1)).day
    return _dt.date(ano, mes, min(data.day, ultimo_dia))


def alertas_buscas(est, hoje=None, meses=MESES_BUSCA_DESATUALIZADA):
    """Alertas das buscas ativas (PRISMA 2020 item 6; references/02-busca.md, seções 5 e 11).

    busca_truncada: resultados não baixados por inteiro (ex.: `buscar openalex --max-paginas`);
    busca_sem_data: sem data de execução interpretável (calado quando a etapa 04_busca está ignorada,
    como no projeto parcial de triagem, em que a planilha do usuário não tem data de busca);
    busca_desatualizada: executada há mais de `meses`.
    """
    hoje = hoje or _dt.datetime.now(_dt.timezone.utc).date()
    busca_ignorada = "04_busca" in set(((est or {}).get("projeto") or {}).get("etapas_ignoradas") or [])
    alertas = []
    for b in _buscas_ativas(est):
        if prisma.busca_truncada(b):
            via = "buscar openalex" if _busca_da_api_openalex(b) else "importar"
            alertas.append({"tipo": "busca_truncada", "busca": b.get("id"),
                            "detalhe": f"busca {b.get('id')} com resultados truncados (ex.: --max-paginas): não serve para "
                                       f"o PRISMA; rode a busca inteira e registre-a com `{via} ... --substituir "
                                       f"{b.get('id')} --motivo ...` (references/02-busca.md, seção 5). O G3 bloqueia e o "
                                       "PRISMA sai como rascunho enquanto ela estiver ativa",
                            "comando": comando_refazer_busca(b)})
        data = _data_busca(b.get("executada_em"))
        if data is None:
            if not busca_ignorada:
                alertas.append({"tipo": "busca_sem_data", "busca": b.get("id"), "executada_em": b.get("executada_em"),
                                "detalhe": f"busca {b.get('id')} sem data de execução interpretável: registre executada_em "
                                           "(PRISMA 2020 item 6; PRISMA-S)"})
        elif _somar_meses(data, meses) < hoje:
            alertas.append({"tipo": "busca_desatualizada", "busca": b.get("id"), "executada_em": data.isoformat(),
                            "dias": (hoje - data).days,
                            "detalhe": f"busca {b.get('id')} executada em {data.isoformat()}, há mais de {meses} meses: "
                                       "atualize a busca antes de publicar (references/02-busca.md, seção 11)"})
    return alertas


def _candidatos_dedup_pendentes(raiz):
    """Pares candidatos que ainda pedem revisão humana: a mesma contagem do `dedup` e da pendência dedup_candidatos
    (sem os resolvidos por transitividade)."""
    try:
        from . import dedup
        return dedup.contar_candidatos_pendentes(raiz)
    except (ImportError, AttributeError):  # versão do dedup sem o helper: conta os candidatos
        pares = prisma._ler_csv(Path(raiz) / esquema.ARQ_DEDUP_PARES) or []
        return sum(1 for p in pares if p.get("decisao") == "candidato")


def _evidencias_etapa(raiz, est, etapa):
    """(concluida_por_artefato, [evidências]) para uma etapa; portões são tratados à parte."""
    r = raiz
    if etapa == "00_configuracao":
        return bool(est.get("ambiente")), (["estado.ambiente"] if est.get("ambiente") else [])
    if etapa == "01_pergunta":
        ev = (["estado.projeto.pergunta"] if est["projeto"].get("pergunta") else []) + _arquivos(r, "00-protocolo", "pergunta*")
        return False, ev
    if etapa == "02_teoria_framework":
        ev = [a for a in _arquivos(r, "00-protocolo") if PADRAO_TEORIA.search(Path(a).name)]
        return bool(ev), ev
    if etapa == "03_protocolo":
        return False, _arquivos(r, "00-protocolo", "protocolo*")
    if etapa == "04_busca":
        ev = _arquivos(r, "01-busca/strings") + _arquivos(r, "01-busca/brutos")
        ativas = _buscas_ativas(est)
        if ativas:
            ev.append(f"estado.buscas ({len(ativas)})")
        return False, ev[:10]
    if etapa == "05_organizacao":
        ev = [a for a in (esquema.ARQ_REGISTROS, esquema.ARQ_UNICOS, esquema.ARQ_DEDUP_PARES, esquema.ARQ_FILTRO_FORMAL)
              if _existe(r, a)]
        return _dedup_coberto(r, est) and _candidatos_dedup_pendentes(r) == 0, ev
    if etapa == "06_triagem_ta":
        ev = [a for a in (esquema.ARQ_DECISOES, esquema.ARQ_TRIAGEM_TA_FINAL) if _existe(r, a)] + _arquivos(r, "02-triagem/lotes")[:3]
        return False, ev
    if etapa == "07_textos_elegibilidade":
        return False, [a for a in (esquema.ARQ_PARA_BAIXAR, esquema.ARQ_RELATORIO_PDFS, esquema.ARQ_INVENTARIO_TEXTOS,
                                   esquema.ARQ_ELEGIBILIDADE_TC_FINAL) if _existe(r, a)]
    if etapa == "08_piloto_extracao":
        return False, [a for a in _arquivos(r, "05-decomposicao") if a != esquema.ARQ_EFEITOS_EXTRAIDOS][:10]
    if etapa == "09_extracao_rob":
        ev = ([esquema.ARQ_EFEITOS_EXTRAIDOS] if _existe(r, esquema.ARQ_EFEITOS_EXTRAIDOS) else []) + _arquivos(r, "04-qualidade")
        return False, ev[:10]
    if etapa == "10_sintese":
        return False, _arquivos(r, "06-analise", recursivo=True)[:10]
    if etapa == "11_relato":
        return False, _arquivos(r, "07-relatorio")[:10]
    return False, []


def recalcular_etapas(raiz, est, eventos=None):
    """Status de cada etapa derivado do log de portões e dos artefatos (o cache só informa)."""
    eventos = eventos if eventos is not None else estado.ler_log(raiz)
    portoes = _estado_portoes(eventos)
    nao_aplicaveis = _nao_aplicaveis(eventos)
    portao_de = {etapa: g for g, etapa in esquema.PORTOES.items()}
    ignoradas = set(est["projeto"].get("etapas_ignoradas") or [])
    etapas = {}
    for etapa in esquema.ETAPAS:
        g = portao_de.get(etapa)
        concluida_art, evidencias = _evidencias_etapa(raiz, est, etapa)
        info = {"status": "pendente", "portao": g, "evidencias": evidencias, "fonte": "artefatos"}
        cache = (est.get("etapas") or {}).get(etapa, {})
        if g and g in nao_aplicaveis:
            info.update(status="ignorada", fonte="nao_se_aplica", motivo=nao_aplicaveis[g].get("motivo"))
        elif etapa in ignoradas or cache.get("status") == "ignorada":
            info.update(status="ignorada", fonte="projeto_parcial")
        elif g and portoes.get(g, {}).get("decisao") == "aprovado":
            info.update(status="concluida", fonte="log_portao", aprovado_por=portoes[g]["por"])
        elif g and portoes.get(g, {}).get("decisao") == "reprovado":
            info.update(status="em_andamento", fonte="log_portao", reprovado=True, motivo=portoes[g].get("motivo"))
        elif not g and (concluida_art or cache.get("status") == "concluida"):
            info.update(status="concluida", fonte="artefatos" if concluida_art else "estado")
        elif evidencias:
            info["status"] = "em_andamento"
        # Teoria/framework é revista no G2: se o protocolo foi aprovado, a etapa 02 está fechada.
        if etapa == "02_teoria_framework" and info["status"] != "ignorada" and portoes.get("G2", {}).get("decisao") == "aprovado":
            info.update(status="concluida", fonte="log_portao")
        etapas[etapa] = info
    return etapas, portoes


def _inconsistencias(raiz, est, etapas, portoes, eventos, contagens):
    itens = []
    # 1. Artefatos congelados alterados ou ausentes
    for chave_art, info in (est.get("artefatos") or {}).items():
        if not isinstance(info, dict) or not info.get("congelado_em"):
            continue
        rel = info.get("caminho") or chave_art
        p = Path(raiz) / rel
        if not p.exists():
            itens.append({"tipo": "artefato_congelado_ausente", "gravidade": "erro", "caminho": rel,
                          "detalhe": f"{rel} foi congelado em {info['congelado_em']} e não existe mais"})
        elif info.get("sha256") and estado.sha256_arquivo(p) != info["sha256"]:
            itens.append({"tipo": "artefato_congelado_alterado", "gravidade": "erro", "caminho": rel,
                          "detalhe": f"{rel} mudou depois de congelado; registre com `{RS} emenda --arquivo {rel} --motivo ...` "
                                     "ou restaure a versão congelada"})
    # 2. Contagens que não fecham (invariantes do PRISMA sobre o ledger)
    for inv in prisma.invariantes_quebradas(contagens):
        etapa = INVARIANTE_ETAPA.get(inv["nome"], "07_textos_elegibilidade")
        concluida = etapas.get(etapa, {}).get("status") == "concluida"
        itens.append({"tipo": "contagens_nao_fecham", "gravidade": "erro" if concluida else "aviso",
                      "invariante": inv["nome"], "ramo": inv["ramo"], "etapa": etapa, "detalhe": inv["detalhe"]})
    # 3. Estado (cache) atrás ou à frente do log; seq repetido no log (gravação concorrente antiga)
    seqs = [int(e.get("seq", 0) or 0) for e in eventos]
    seq_log = max(seqs, default=0)
    if int(est.get("ultimo_seq", 0)) > seq_log:
        itens.append({"tipo": "log_atras_do_estado", "gravidade": "erro",
                      "detalhe": f"estado diz seq {est.get('ultimo_seq')} e o log termina em {seq_log} (log truncado?)"})
    elif int(est.get("ultimo_seq", 0)) < seq_log:
        itens.append({"tipo": "estado_atras_do_log", "gravidade": "aviso",
                      "detalhe": f"estado em seq {est.get('ultimo_seq')}, log em {seq_log}; o cache será atualizado no próximo comando"})
    repetidos = sorted(s for s, n in collections.Counter(seqs).items() if n > 1)
    if repetidos:
        itens.append({"tipo": "seq_repetido_no_log", "gravidade": "aviso", "seqs": repetidos[:20],
                      "detalhe": f"{len(repetidos)} seq repetidos em rs_log.jsonl (ex.: {', '.join(map(str, repetidos[:5]))}): "
                                 "comandos gravaram ao mesmo tempo numa versão antiga da skill; o log não é reescrito, "
                                 "confira pendências e eventos desses seq"})
    # 4. Portão marcado no cache sem evento no log (edição manual do estado?)
    for g, etapa in esquema.PORTOES.items():
        cache = (est.get("etapas") or {}).get(etapa, {})
        if cache.get("status") == "concluida" and portoes.get(g, {}).get("decisao") != "aprovado":
            itens.append({"tipo": "portao_sem_evento", "gravidade": "aviso", "portao": g,
                          "detalhe": f"rs_estado.json marca {etapa} como concluída sem evento de aprovação do {g} no log"})
    # 5. Portões fora de ordem
    ordem = list(esquema.PORTOES)
    for i, g in enumerate(ordem):
        if portoes.get(g, {}).get("decisao") != "aprovado":
            continue
        for anterior in ordem[:i]:
            etapa_ant = esquema.PORTOES[anterior]
            if etapas[etapa_ant]["status"] not in ("concluida", "ignorada"):
                itens.append({"tipo": "portao_fora_de_ordem", "gravidade": "aviso", "portao": g,
                              "detalhe": f"{g} aprovado antes de {anterior} ({etapa_ant} está {etapas[etapa_ant]['status']})"})
                break
    return itens


def _criterios_ta(raiz):
    arqs = _arquivos(raiz, "02-triagem/prompts", "ta_v*.md")

    def versao(a):
        m = re.search(r"ta_v(\d+)", a)
        return int(m.group(1)) if m else 0

    return max(arqs, key=versao) if arqs else None


def _reexecucoes_estabilidade(eventos):
    return {(ev.get("dados") or {}).get("rodada_reexecucao") for ev in (eventos or [])
            if ev.get("evento") == "validacao_calculada"} - {None}


def _rodadas_ativas(est, etapa="ta", eventos=None):
    """Rodadas em versoes_ativas (rodada_ta; "a+b" ou "a,b" quando a consolidação juntou rodadas),
    sem reexecuções de estabilidade."""
    chave = esquema.VERSAO_ATIVA_RODADA_TA if etapa == "ta" else f"rodada_{etapa}"
    valor = ((est or {}).get("versoes_ativas") or {}).get(chave) or ""
    reexecucoes = _reexecucoes_estabilidade(eventos)
    return [r.strip() for r in re.split(r"[+,]", str(valor))
            if r.strip() and not _rodada_de_estabilidade(r.strip(), reexecucoes)]


def _rodada_de_estabilidade(rodada, reexecucoes=()):
    return str(rodada).endswith("_estab") or rodada in reexecucoes


def _ultima_rodada(raiz, etapa="ta", est=None, eventos=None):
    """Rodada que a próxima ação deve citar: a ativa no estado; senão a última do ledger que não seja
    reexecução de estabilidade (`<rodada>_estab` ou `rodada_reexecucao` de um evento de estabilidade)."""
    ativas = _rodadas_ativas(est, etapa, eventos)
    if ativas:
        return ativas[-1]
    reexecucoes = _reexecucoes_estabilidade(eventos)
    rodada = None
    for d in _ler_jsonl(Path(raiz) / esquema.ARQ_DECISOES):
        if d.get("etapa") == etapa and d.get("rodada") and not _rodada_de_estabilidade(d["rodada"], reexecucoes):
            rodada = d["rodada"]
    return rodada


def _ultimo_evento(eventos, nome):
    for ev in reversed(eventos):
        if ev.get("evento") == nome:
            return ev
    return None


def validacao_do_portao(est, eventos, etapa="06_triagem_ta"):
    """Validação que decide o G4: (evento, atende_limiares, avisos) ou (None, None, avisos).

    Vale a última `validacao_calculada` da etapa com `atende_limiares` (ou com `dados.atalho_rapida`
    true, da variante rápida) e `dados.finalidade == "validacao"` cuja rodada está em
    versoes_ativas.rodada_ta. Calibração, desenvolvimento, elusão e estabilidade nunca decidem o
    portão, mesmo que calculadas depois. Compatibilidade: evento sem `finalidade` conta como validação
    (com aviso); evento sem `rodada`, ou projeto sem rodada ativa, também (com aviso).
    """
    ativas = set(_rodadas_ativas(est, "ta", eventos))
    avisos, ignoradas = [], []
    for ev in reversed(eventos):
        if ev.get("evento") != "validacao_calculada" or ev.get("etapa") != etapa:
            continue
        dados = ev.get("dados") or {}
        atende = dados["atende_limiares"] if "atende_limiares" in dados else _procurar_chave(dados, "atende_limiares")
        if atende is None and not _eh_atalho_rapida(ev):
            continue  # estabilidade/elusão: sem limiar vinculante
        finalidade = dados.get("finalidade")
        if finalidade is not None and finalidade != "validacao":
            ignoradas.append(f"seq {ev.get('seq')} ({finalidade})")
            continue
        rodada = dados.get("rodada")
        if ativas and rodada and rodada not in ativas:
            ignoradas.append(f"seq {ev.get('seq')} (rodada {rodada})")
            continue
        if finalidade is None:
            avisos.append(f"validação seq {ev.get('seq')} sem `finalidade`: tratada como validação final")
        if not ativas:
            avisos.append("versoes_ativas.rodada_ta não definida: usada a última validação da etapa")
        elif not rodada:
            avisos.append(f"validação seq {ev.get('seq')} sem `rodada`: não dá para conferir se é da rodada ativa")
        if ignoradas:
            avisos.append("validações que não decidem o portão foram ignoradas: " + ", ".join(ignoradas[:5]))
        return ev, atende, avisos
    if ignoradas:
        avisos.append("há validações calculadas, mas nenhuma com finalidade validacao da rodada ativa "
                      f"({', '.join(sorted(ativas)) or 'sem rodada ativa'}): " + ", ".join(ignoradas[:5]))
    return None, None, avisos


def _eh_atalho_rapida(evento):
    valor = ((evento or {}).get("dados") or {}).get(CRITERIO_ATALHO_RAPIDA)
    return valor is True or (isinstance(valor, str) and valor.strip().lower() in {"true", "sim", "1"})


def atalho_rapida_aprovado(est, eventos):
    """projeto.variante == rapida e critério `atalho_rapida` verdadeiro na última aprovação do G1."""
    if ((est or {}).get("projeto") or {}).get("variante") != "rapida":
        return False
    g1 = None
    for ev in eventos or []:
        dados = ev.get("dados") or {}
        if ev.get("evento") == "portao" and dados.get("portao") == "G1":
            g1 = ev if dados.get("decisao", "aprovado") == "aprovado" else None
    valor = (((g1 or {}).get("dados") or {}).get("criterios") or {}).get(CRITERIO_ATALHO_RAPIDA)
    return bool(valor) and not (isinstance(valor, str) and valor.strip().lower() in {"false", "nao", "não", "0", ""})


def _ultima_validacao(eventos, etapa="06_triagem_ta", est=None):
    """Compatibilidade: (evento, atende) da validação que decide o portão (ver validacao_do_portao)."""
    ev, atende, _ = validacao_do_portao(est, eventos, etapa)
    return ev, atende


def _acao(tipo, descricao, comando=None, **extra):
    acao = {"tipo": tipo, "descricao": descricao}
    if comando:
        acao["comando"] = comando
    acao.update(extra)
    return acao


def _acao_portao(g, est, descricao, criterios_exemplo=None):
    """Ação de aprovar um portão. Valores que dependem de conferência saem como placeholders <...>.

    Os placeholders ficam fora de aspas de propósito: o JSON só vale depois de preenchido, então
    colar o comando sem conferir sai com código 1 em vez de registrar um valor inventado.
    """
    autopiloto = est["modo"]["autonomia"] == "autopiloto" and g not in esquema.PORTOES_SEMPRE_PARAM_AUTOPILOTO
    por = "autopiloto" if autopiloto else PAPEL_HUMANO
    humano = "" if autopiloto else " (mostrar o resumo ao usuário e aguardar aprovação explícita)"
    criterios = criterios_exemplo or f'{{"<critério>": <valor conferido; ver {REF_PORTOES}>}}'
    return _acao("portao", descricao + humano + "; troque cada <...> pelo valor conferido",
                 f"{RS} portao {g} --aprovar --por {por} --criterios '{criterios}'", portao=g, exige_humano=not autopiloto)


def proxima_acao(raiz, est, etapas, portoes, eventos, inconsistencias):
    erros = [i for i in inconsistencias if i["gravidade"] == "erro"]
    for i in erros:
        if i["tipo"].startswith("artefato_congelado"):
            return _acao("corrigir", i["detalhe"], f"{RS} emenda --arquivo {i['caminho']} --motivo \"...\"")
    for i in erros:
        if i["tipo"] == "contagens_nao_fecham":
            cmd = f"{RS} dedup" if i["etapa"] == "05_organizacao" else f"{RS} prisma"
            return _acao("corrigir", f"contagens não fecham ({i['invariante']}): {i['detalhe']}", cmd)
    if erros:
        return _acao("corrigir", erros[0]["detalhe"])

    atual = next((e for e in esquema.ETAPAS if etapas[e]["status"] not in ("concluida", "ignorada")), None)
    abertas = estado.pendencias_abertas(est)
    if atual is None:
        if abertas:
            return _acao("pendencia", f"todas as etapas concluídas, mas há {len(abertas)} pendências abertas "
                                      "(produtos seguem como rascunho)",
                         f"{RS} pendencia fechar {abertas[0]['id']} --motivo \"...\"", pendencia=abertas[0]["id"])
        return _acao_depois_da_ultima_etapa(raiz, est, etapas, eventos)

    g = etapas[atual]["portao"]
    if est["modo"]["autonomia"] == "checkpoints":
        bloqueando = [p for p in abertas if p.get("etapa") == atual or (g and p.get("portao") == g)]
        if bloqueando:
            p = bloqueando[0]
            return _acao("pendencia", f"{p['id']}: {p.get('descricao', '')}",
                         f"{RS} pendencia fechar {p['id']} --motivo \"...\"", pendencia=p["id"])
    if etapas[atual].get("reprovado"):
        acao = _acao("tarefa", f"{g} foi reprovado ({etapas[atual].get('motivo') or 'sem motivo'}); refaça a etapa e "
                               "submeta de novo", etapa=atual)
    else:
        acao = _acao_etapa(raiz, est, atual, eventos) | {"etapa": atual}
    if est["modo"]["autonomia"] == "autopiloto" and acao.get("tipo") == "tarefa":
        # Tarefa humana já registrada como pendência não bloqueia o autopiloto: diz que é humana e aponta como seguir.
        pendentes = [p for p in abertas if _pendencia_da_etapa(p, atual, g)]
        if pendentes:
            acao.update(exige_humano=True, pendencia=pendentes[0]["id"])
            seguir = _acao_seguinte_autopiloto(raiz, est, etapas, eventos, atual, abertas)
            if seguir:
                acao["alternativa"] = (f"seguir sem esperar a pendência {pendentes[0]['id']} (autopiloto; os produtos saem "
                                       f"como rascunho até um humano fechá-la): "
                                       + (seguir.get("comando") or seguir["descricao"]))
                acao["acao_seguinte"] = seguir
    if g and g in esquema.PORTOES_OPCIONAIS_POR_TIPO.get(est["projeto"].get("tipo_revisao"), []):
        dispensa = (f"{RS} portao {g} --nao-se-aplica --por {PAPEL_HUMANO} --motivo \"<motivo>\" "
                    f"(o tipo {est['projeto']['tipo_revisao']} permite dispensar esta etapa)")
        if "alternativa" in acao:
            acao.setdefault("alternativas", []).append(dispensa)
        else:
            acao["alternativa"] = dispensa
    return acao


def _pendencia_da_etapa(pendencia, etapa, portao):
    return pendencia.get("etapa") == etapa or bool(portao and pendencia.get("portao") == portao)


def _acao_seguinte_autopiloto(raiz, est, etapas, eventos, atual, abertas):
    """Próximo passo que não depende da pendência humana da etapa atual (autopiloto), ou None.

    Não passa por cima de portão que o autopiloto não pode aprovar: se o portão da etapa atual tem bloqueio
    `artefato` ou `limiar`, não há como seguir sem resolver a etapa.
    """
    if atual == "05_organizacao" and not _existe(raiz, esquema.ARQ_FILTRO_FORMAL):
        return _acao("comando", "aplicar o funil formal (opcional; etiqueta por padrão) enquanto os pares aguardam revisão",
                     f"{RS} filtrar --config 01-busca/filtros_v1.json", etapa=atual)
    portao = etapas[atual]["portao"]
    if portao and any(b["tipo"] in TIPOS_BLOQUEIO_DUROS for b in checar_portao(raiz, est, portao, eventos)[0]):
        return None
    for etapa in esquema.ETAPAS[esquema.ETAPAS.index(atual) + 1:]:
        if etapas[etapa]["status"] in ("concluida", "ignorada"):
            continue
        acao = _acao_etapa(raiz, est, etapa, eventos)
        if acao.get("exige_humano") and any(_pendencia_da_etapa(p, etapa, etapas[etapa]["portao"]) for p in abertas):
            continue
        return acao | {"etapa": etapa}
    return None


def _portoes_forcados_vigentes(raiz, est, eventos, portoes=("G8",)):
    """[(portão, bloqueios que continuam valendo)] dos portões cuja aprovação vigente foi forçada (--forcar)."""
    vigentes = []
    decisao = _estado_portoes(eventos)
    for g in portoes:
        if decisao.get(g, {}).get("decisao") != "aprovado":
            continue
        ev = next((e for e in reversed(eventos) if e.get("evento") == "portao"
                   and (e.get("dados") or {}).get("portao") == g), None)
        checagens = (((ev or {}).get("dados") or {}).get("criterios") or {}).get("checagens_script") or {}
        if not checagens.get("forcado"):
            continue
        restantes = [b for b in checar_portao(raiz, est, g, eventos)[0] if b["tipo"] != "pendencia"]
        if restantes:
            vigentes.append((g, restantes))
    return vigentes


def _acao_depois_da_ultima_etapa(raiz, est, etapas, eventos):
    """Todas as etapas do projeto concluídas: fim, ou a etapa seguinte quando os produtos seguem como rascunho.

    Aprovação forçada do G8 com bloqueios que continuam valendo, ou motivos de rascunho (caixa com células
    pendentes, busca truncada), não são "fim": a ação aponta a etapa seguinte à última aprovada e o que falta.
    """
    motivos = motivos_de_rascunho(est, eventos)
    forcados = _portoes_forcados_vigentes(raiz, est, eventos)
    if not motivos and not forcados:
        return _acao("fim", "revisão concluída; nenhuma pendência aberta")
    aprovados = [g for g, info in _estado_portoes(eventos).items() if info.get("decisao") == "aprovado"]
    ultimo = forcados[-1][0] if forcados else (max(aprovados, key=lambda g: int(g[1:])) if aprovados else None)
    etapa_ultima = esquema.PORTOES.get(ultimo) if ultimo else None
    posteriores = esquema.ETAPAS[esquema.ETAPAS.index(etapa_ultima) + 1:] if etapa_ultima else []
    seguinte = posteriores[0] if posteriores else "11_relato"
    ignorada = etapas.get(seguinte, {}).get("status") == "ignorada"
    faltas = list(motivos) + [f"{g} aprovado com --forcar e ainda com: " + "; ".join(b["detalhe"] for b in bl[:3])
                              for g, bl in forcados]
    comando = None
    if any("caixa de ferramentas" in m for m in motivos):
        comando = f"{RS} caixa --master <master>"
    elif prisma.buscas_truncadas(est):
        busca = next(b for b in _buscas_ativas(est) if prisma.busca_truncada(b))
        comando = comando_refazer_busca(busca)
    if ignorada:
        relato = f"relate os resultados fora do fluxo PRISMA desta skill (etapa {seguinte} ignorada no projeto parcial),"
    elif etapas.get(seguinte, {}).get("status") == "concluida":
        relato = f"mantenha no relatório ({seguinte})"
    else:
        relato = f"siga para {seguinte}"
    return _acao("tarefa", "etapas do projeto aprovadas, mas os produtos seguem como rascunho: " + " | ".join(faltas)
                 + f". Resolva o que falta e gere os produtos de novo, ou {relato} declarando essas lacunas como limitação "
                   "(PRISMA 2020 item 23c)", comando, etapa=seguinte, rascunho=True, motivos_rascunho=motivos,
                 portoes_forcados=[g for g, _ in forcados], exige_humano=True)


def _acao_etapa(raiz, est, etapa, eventos):
    r = raiz
    if etapa == "00_configuracao":
        return _acao("comando", "verificar dependências e skills irmãs", f"{RS} ambiente")
    if etapa == "01_pergunta":
        if not est["projeto"].get("pergunta") or est["projeto"].get("tipo_revisao") == "indefinido":
            return _acao("tarefa", "definir com o usuário pergunta (X, Y, M, Z), escala, RS existentes e tipo de revisão "
                                   "(references/01-pergunta-protocolo.md, references/tipos-de-revisao.md); depois o G1; "
                                   "troque cada <...> pelo valor combinado",
                         f"{RS} portao G1 --aprovar --por {PAPEL_HUMANO} "
                         "--criterios '{\"pergunta\": <pergunta aprovada pelo usuário, entre aspas>, "
                         "\"tipo_revisao\": <tipo de references/tipos-de-revisao.md, entre aspas>}'",
                         portao="G1", exige_humano=True)
        return _acao_portao("G1", est, "aprovar pergunta e tipo de revisão",
                            '{"pergunta": <pergunta aprovada pelo usuário, entre aspas>, "tipo_revisao": "'
                            + est["projeto"]["tipo_revisao"] + '"}')
    if etapa == "02_teoria_framework":
        return _acao("tarefa", "elaborar teoria do programa (DAG com incentivos perversos) e framework (PICOC/CMMO, PCC...) "
                               "em 00-protocolo/teoria_programa.md")
    if etapa == "03_protocolo":
        if not _arquivos(r, "00-protocolo", "protocolo*"):
            return _acao("tarefa", "redigir 00-protocolo/protocolo.md a partir de assets/templates/protocolo.md "
                                   "(critérios, RoB, codebook v0, plano de síntese e de IA) e revisar com "
                                   "agentes/revisor-metodologico.md")
        faltas = checar_g2(r)[0]
        if faltas:
            return _acao("tarefa", "antes do G2: " + "; ".join(b["detalhe"] for b in faltas),
                         exige_humano=True)
        codebook = (_arquivos(r, *PADRAO_CODEBOOK_V0) or ["<codebook v0>"])[0]
        return _acao_portao("G2", est, "aprovar e congelar o protocolo (registro OSF recomendado)",
                            '{"protocolo": "' + _arquivos(r, "00-protocolo", "protocolo*")[0] + '", "codebook_v0": "'
                            + codebook + '", "revisor_metodologico": <parecer do revisor metodológico, entre aspas>, '
                            '"registro": <DOI do OSF ou "pendente">}')
    if etapa == "04_busca":
        if not (_arquivos(r, "01-busca/brutos") or _buscas_ativas(est) or _existe(r, esquema.ARQ_REGISTROS)):
            if not _arquivos(r, "01-busca/strings"):
                return _acao("tarefa", "montar strings por base em 01-busca/strings/ (references/02-busca.md), PRESS e "
                                       "estudos-âncora independentes")
            return _acao("comando", "executar as buscas e importar as exportações",
                         f"{RS} importar --arquivo 01-busca/brutos/<exportacao> --busca-id B01")
        truncadas = [b for b in _buscas_ativas(est) if prisma.busca_truncada(b)]
        if truncadas:
            ids = ", ".join(str(b.get("id")) for b in truncadas)
            api = _busca_da_api_openalex(truncadas[0])
            return _acao("tarefa", f"buscas com resultados truncados ({ids}): rode cada uma inteira (sem --max-paginas) e "
                                   "registre a execução completa com um busca_id novo e --substituir, "
                                   + ("pela API do OpenAlex, como a busca truncada foi feita" if api else
                                      "importando a exportação completa da base")
                                   + " (references/02-busca.md, seção 5); o G3 bloqueia enquanto houver busca truncada ativa",
                         comando_refazer_busca(truncadas[0]), buscas_truncadas=[b.get("id") for b in truncadas])
        if not _press_registrado(r, est):
            if est["modo"]["autonomia"] == "autopiloto":
                return _acao("comando", "PRESS da estratégia principal por revisor humano: registre a pendência antes do G3 "
                                        "(references/02-busca.md, seção 8)",
                             f"{RS} pendencia abrir --tipo {PENDENCIA_PRESS} --etapa 04_busca --portao G3 "
                             "--descricao \"PRESS de <string_id> por revisor humano\" --arquivo 01-busca/strings/<string_id>.txt")
            return _acao("tarefa", "PRESS da estratégia principal por um humano que não escreveu a string; registre em "
                                   "01-busca/press_<string_id>.md (references/02-busca.md, seção 8) antes do G3",
                         exige_humano=True)
        descricao = "aprovar a busca (PRESS, recall nas âncoras, log PRISMA-S)"
        recall = _recall_combinado(r)
        if recall is not None:
            descricao += f"; recall combinado em {esquema.ARQ_RECALL_ANCORAS}: {recall:.2f}"
        else:
            descricao += f"; {esquema.ARQ_RECALL_ANCORAS} ainda não existe (rode `filtrar --ancoras` depois do dedup)"
        return _acao_portao("G3", est, descricao,
                            f'{{"recall_ancoras": <valor de {esquema.ARQ_RECALL_ANCORAS}>, '
                            '"press": <press: true só com revisão humana registrada>}')
    if etapa == "05_organizacao":
        if not _existe(r, esquema.ARQ_REGISTROS):
            return _acao("comando", "importar as exportações", f"{RS} importar --arquivo <exportacao> --busca-id B01")
        if not _dedup_coberto(r, est):
            return _acao("comando", "deduplicar (há registros fora de registros_unicos.csv)", f"{RS} dedup")
        n = _candidatos_dedup_pendentes(r)
        if n:
            return _acao("tarefa", f"revisar {n} pares candidatos de duplicata (decisao confirmado, rejeitado ou ligado; "
                                   "--por é o papel humano de quem decidiu, se a coluna decidido_por estiver vazia)",
                         f"{RS} dedup --revisar {esquema.ARQ_DEDUP_PARES} --por {PAPEL_HUMANO}", exige_humano=True)
        return _acao("comando", "aplicar o funil formal (opcional; etiqueta por padrão)",
                     f"{RS} filtrar --config 01-busca/filtros_v1.json")
    if etapa == "06_triagem_ta":
        criterios = _criterios_ta(r)
        rodada = _ultima_rodada(r, est=est, eventos=eventos)
        if not criterios:
            return _acao("tarefa", "redigir critérios de triagem em 02-triagem/prompts/ta_v1.md "
                                   "(assets/templates/criterios_triagem.md) e calibrar com dupla humana")
        nome_rodada = Path(criterios).stem
        if not _existe(r, esquema.ARQ_DECISOES):
            if est["modo"]["triagem"] == "api":
                return _acao("comando", "triagem via API (estime custo antes)",
                             f"{RS} triagem api --rodada {nome_rodada} --criterios {criterios} --modelo-a <modelo> "
                             "--modelo-b <modelo> --arbitro <modelo> --estimar")
            return _acao("comando", "preparar lotes do revisor A",
                         f"{RS} triagem preparar --etapa ta --rodada {nome_rodada} --revisor A --criterios {criterios}")
        if not _existe(r, esquema.ARQ_TRIAGEM_TA_FINAL):
            rodadas = _rodadas_ativas(est, "ta", eventos) or [rodada or nome_rodada]
            if est["modo"]["triagem"] != "api":
                antes = _acao_antes_de_consolidar(r, rodadas, criterios)
                if antes:
                    return antes
            return _acao("comando", "consolidar a rodada de triagem",
                         f"{RS} triagem consolidar " + " ".join(f"--rodada {x}" for x in rodadas))
        ev, atende, _ = validacao_do_portao(est, eventos)
        if ev is None:
            return _acao("comando", "amostra de validação humana (enriquecida para ≥ 60 incluídos) da rodada ativa",
                         f"{RS} validar amostrar --etapa ta --rodada {rodada or nome_rodada} --n 100 --semente 7 "
                         "--enriquecer-incluidos 60")
        atalho = _eh_atalho_rapida(ev) and atalho_rapida_aprovado(est, eventos)
        if _eh_atalho_rapida(ev) and not atalho and atende is not True:
            return _acao("tarefa", f"validação seq {ev.get('seq')} marcada atalho_rapida, mas o projeto não é variante rápida "
                                   f"com `{CRITERIO_ATALHO_RAPIDA}` aprovado no G1: vale a regra geral do G4 (recall ≥ 0,95 "
                                   "com LI ≥ 0,90). Registre o atalho no G1 (references/tipos-de-revisao.md, seção 6) ou "
                                   "valide a IA", exige_humano=True)
        if atende is False and not atalho:
            if atalho_rapida_aprovado(est, eventos):
                planilha = _planilha_da_validacao(ev)
                return _acao("tarefa", f"variante rápida com `{CRITERIO_ATALHO_RAPIDA}` aprovado no G1, mas a validação seq "
                                       f"{ev.get('seq')} não traz os campos do atalho (atalho_rapida, fração em dupla "
                                       "humana, κ e segunda leitura dos excluídos) e fica abaixo da regra geral: calcule "
                                       "de novo com --atalho-rapida (dupla humana em ≥ 20% da rodada; os excluídos pela IA "
                                       "relidos com `validar segunda-leitura`). Sem esses campos, a aprovação só é "
                                       "possível por humano com --forcar (references/tipos-de-revisao.md, seção 6)",
                             f"{RS} validar calcular --planilha {planilha} --atalho-rapida",
                             alternativa=f"{RS} portao G4 --aprovar --por {PAPEL_HUMANO} --forcar --motivo \"<atalho da "
                                         "variante rápida: dupla humana em <fração>, κ = <κ>, segunda leitura de todos os "
                                         "excluídos>\"", exige_humano=True)
            return _acao_validacao_reprovada(r, ev)
        seq = ev.get("seq")
        faltas_atalho = checar_atalho_rapida(ev) if atalho else []
        if faltas_atalho:
            dados = ev.get("dados") or {}
            rodada_ev = dados.get("rodada") or rodada or nome_rodada
            sem_segunda = any("segunda leitura" in b["detalhe"] for b in faltas_atalho)
            comando = (f"{RS} validar segunda-leitura --rodada {rodada_ev} --planilha <planilha codificada com todos os "
                       "excluídos pela IA>" if sem_segunda else
                       f"{RS} validar amostrar --etapa ta --rodada {rodada_ev} --n <≥ 20% da rodada> --semente <outra> "
                       "--atalho-rapida")
            return _acao("tarefa", "atalho da variante rápida incompleto: " + "; ".join(b["detalhe"] for b in faltas_atalho)
                         + f"; depois rode `validar calcular --planilha {_planilha_da_validacao(ev)} --atalho-rapida` de "
                           "novo (references/tipos-de-revisao.md, seção 6)", comando, exige_humano=True)
        if atalho:
            return _acao_portao("G4", est, "aprovar a triagem de título/resumo pelo atalho da variante rápida "
                                           "(dupla humana em ≥ 20%, κ e segunda leitura dos excluídos)",
                                f'{{"{CRITERIO_ATALHO_RAPIDA}": true, "fracao_dupla_humana": <fração em dupla humana '
                                f'(seq {seq})>, "kappa_humanos": <κ da dupla humana (seq {seq})>, '
                                '"segunda_leitura_excluidos": <true só se todos os excluídos pela IA foram relidos>}')
        return _acao_portao("G4", est, "aprovar a triagem de título/resumo",
                            f'{{"recall": <sensibilidade da validação seq {seq}>, "recall_li": <limite inferior do IC '
                            f'(seq {seq})>, "kappa": <κ da validação seq {seq}>}}')
    if etapa == "07_textos_elegibilidade":
        if not _existe(r, esquema.ARQ_PARA_BAIXAR):
            return _acao("comando", "gerar a lista de textos para baixar", f"{RS} textos para-baixar")
        if not _existe(r, esquema.ARQ_RELATORIO_PDFS):
            return _acao("skill", "baixar PDFs com a skill baixar-pdfs-academicos",
                         f"entrada {esquema.ARQ_PARA_BAIXAR}; saída 03-textos/pdfs e {esquema.ARQ_RELATORIO_PDFS}",
                         skill="baixar-pdfs-academicos")
        if not _existe(r, esquema.ARQ_INVENTARIO_TEXTOS):
            return _acao("comando", "inventariar os PDFs (páginas, camada de texto, conteúdo)", f"{RS} textos inventario")
        if not _existe(r, esquema.ARQ_ELEGIBILIDADE_TC_FINAL):
            return _acao("tarefa", "elegibilidade em texto completo (fichamento-sistematico com codebook de elegibilidade) "
                                   "e consolidação",
                         f"{RS} textos elegibilidade consolidar --master <fichamentos_master.csv> --codebook <codebook.csv>")
        return _acao_portao("G5", est, "aprovar a elegibilidade em texto completo (motivos, relatos ligados, bola de neve)")
    if etapa == "08_piloto_extracao":
        if checar_piloto(r, eventos):
            return _acao("tarefa", "piloto de extração com 2–3 estudos por bloco (a1/a2/b1/b2) via fichamento-sistematico, "
                                   "consolidado em 05-decomposicao/**/fichamentos_master.csv",
                         skill="fichamento-sistematico")
        return _acao_portao("G6", est, "aprovar o codebook após o piloto")
    if etapa == "09_extracao_rob":
        if not (_existe(r, esquema.ARQ_EFEITOS_EXTRAIDOS) or _arquivos(r, "04-qualidade")):
            return _acao("tarefa", "extração completa e risco de viés em paralelo (fichamento-sistematico; "
                                   "agentes/extrator-efeitos.md; agentes/avaliador-rob.md)")
        bloqueios = checar_efeitos(r, eventos)
        if any(b.get("acao") == "verificar" for b in bloqueios):
            return _acao("comando", "verificar efeitos (trecho na página e plausibilidade)", f"{RS} analise verificar-efeitos")
        if any(b["tipo"] == "artefato" for b in bloqueios):
            return _acao("tarefa", next(b["detalhe"] for b in bloqueios if b["tipo"] == "artefato")
                         + " (agentes/extrator-efeitos.md) e rode verificar-efeitos de novo")
        if bloqueios and est["modo"]["autonomia"] == "checkpoints":
            return _acao("tarefa", bloqueios[0]["detalhe"] + ": humano confere na página e marca verificado_humano; "
                         f"depois `{RS} analise verificar-efeitos`", exige_humano=True)
        rob = checar_rob(r, est, eventos)
        if est["modo"]["autonomia"] != "checkpoints":
            rob = [b for b in rob if b["tipo"] in TIPOS_BLOQUEIO_DUROS]  # no autopiloto, validação humana vira pendência
        if rob:
            extra = {} if rob[0]["tipo"] in TIPOS_BLOQUEIO_DUROS else {"exige_humano": True}
            return _acao("tarefa", rob[0]["detalhe"] + " (references/05-qualidade.md, seção 5)", rob[0].get("comando"),
                         **extra)
        return _acao_portao("G7", est, "aprovar extração e RoB (efeitos verificados por humano)")
    if etapa == "10_sintese":
        if not _arquivos(r, "06-analise", recursivo=True):
            return _acao("tarefa", "síntese: checklist de comparabilidade, efeitos.R e meta.R ou swim.R, síntese qualitativa "
                                   "(references/07a e 07b)")
        if _ultimo_evento(eventos, "caixa_gerada") is None and est["projeto"].get("tipo_revisao") == "oqf_mista_sequencial":
            return _acao("comando", "montar a caixa de ferramentas", f"{RS} caixa --master <master> --efeitos 06-analise/meta_resumo.json")
        certeza = checar_certeza(r, est)
        if certeza and (est["modo"]["autonomia"] == "checkpoints"
                        or any(b["tipo"] in TIPOS_BLOQUEIO_DUROS for b in certeza)):
            return _acao("tarefa", certeza[0]["detalhe"], exige_humano=True)
        bloqueios = checar_caixa(r)
        if bloqueios and est["modo"]["autonomia"] == "checkpoints":
            return _acao("tarefa", bloqueios[0]["detalhe"], f"{RS} caixa --master <master>", exige_humano=True)
        return _acao_portao("G8", est, "aprovar síntese, certeza e rótulos")
    if etapa == "11_relato":
        if checar_prisma(r, est, eventos):
            return _acao("comando", "gerar (ou regenerar) o PRISMA do ledger", f"{RS} prisma")
        if not _existe(r, esquema.ARQ_DECLARACAO_IA):
            return _acao("comando", "gerar a declaração de uso de IA do log", f"{RS} declaracao-ia")
        return _acao_portao("G9", est, "aprovar o relatório final")
    return _acao("tarefa", f"etapa {etapa}")


def _planilha_da_validacao(ev):
    """Planilha codificada citada pelo evento validacao_calculada (ou um placeholder)."""
    for art in (ev or {}).get("artefatos") or []:
        rel = str(art.get("caminho") or "")
        if rel.endswith((".xlsx", ".csv")) and not rel.endswith("_falsos_negativos.csv"):
            return rel
    return "<planilha codificada da validação>"


def _plano_da_validacao(raiz, ev):
    """validacao.plano_reprovacao a partir do *_metricas.json citado no evento (a mesma ação de `validar calcular`)."""
    dados = (ev or {}).get("dados") or {}
    for art in (ev or {}).get("artefatos") or []:
        rel = str(art.get("caminho") or "")
        if not rel.endswith(esquema.SUFIXO_METRICAS):
            continue
        try:
            from . import validacao
            metricas = json.loads((Path(raiz) / rel).read_text(encoding="utf-8"))
            return validacao.plano_reprovacao(raiz, metricas, dados.get("motivo_reprovacao")) or {}
        except Exception:  # noqa: BLE001 - métricas ilegíveis ou módulo diferente: a ação cai no texto local
            return {}
    return {}


def _acao_validacao_reprovada(raiz, ev):
    """Próxima ação para a validação do G4 abaixo dos limiares, pelo `motivo_reprovacao` do evento.

    largura_ic (0 falsos negativos, só o limite inferior do IC falhou): ampliar a amostra enriquecida ou a elusão,
    nunca revisar critérios; se a rodada não tem incluídos pela IA suficientes, remédio 5 com --forcar humano.
    humanos: discutir as discordâncias humanas. desempenho_ia (ou evento antigo): falsos negativos e critérios vN+1.
    """
    dados = (ev or {}).get("dados") or {}
    motivo = dados.get("motivo_reprovacao")
    n_incl = dados.get("n_incluidos_humanos")
    n_incl = n_incl if isinstance(n_incl, int) and not isinstance(n_incl, bool) else None
    sem_fn = not dados.get("n_falsos_negativos")
    remedio5 = _acao("tarefa", f"validação sem falsos negativos, mas com {n_incl if n_incl is not None else 'poucos'} "
                               f"incluídos humanos (< {MIN_INCLUIDOS_LIMIAR_ALCANCAVEL}) e sem incluídos pela IA suficientes "
                               "para ampliar a amostra: o limite inferior do recall não chega a 0,90. Não revise os "
                               "critérios; vá ao remédio 5 (dupla humana completa, references/ia-validacao.md, seção 4, E) e "
                               "aprove o G4 com --forcar --motivo humano",
                     f"{RS} portao G4 --aprovar --por {PAPEL_HUMANO} --forcar --motivo "
                     "\"<remédio 5: dupla humana completa, planilha e κ>\"", exige_humano=True,
                     motivo_reprovacao=motivo or "largura_ic")
    if motivo is None and n_incl is not None and n_incl < MIN_INCLUIDOS_LIMIAR_ALCANCAVEL and sem_fn:
        return remedio5  # evento antigo, sem motivo_reprovacao
    if motivo == "largura_ic":
        plano = _plano_da_validacao(raiz, ev)
        necessarios = plano.get("incluidos_humanos_necessarios") or MIN_INCLUIDOS_LIMIAR_ALCANCAVEL
        disponiveis = plano.get("incluidos_ia_nao_sorteados")
        if isinstance(disponiveis, int) and disponiveis < necessarios:
            if plano.get("proxima_acao"):
                remedio5["descricao"] = plano["proxima_acao"]
            return remedio5
        etapa, rodada = dados.get("etapa") or "ta", dados.get("rodada") or "<rodada>"
        regra = f" --regra {dados['regra']}" if dados.get("regra") not in (None, "", "consenso") else ""
        alvo = max(necessarios, 60) if not isinstance(disponiveis, int) else min(max(necessarios, 60), disponiveis)
        descricao = plano.get("proxima_acao") or (
            f"validação reprovada só pela largura do IC do recall (0 falsos negativos; {n_incl} incluídos humanos, são "
            f"precisos ≥ {necessarios}): não revise os critérios. Amplie a validação com amostra nova da mesma rodada, "
            "enriquecida, ou meça os perdidos com a elusão (references/ia-validacao.md, seção 4 C, D e F)")
        return _acao("comando", descricao,
                     f"{RS} validar amostrar --etapa {etapa} --rodada {rodada} --n <n> --semente <outra semente> "
                     f"--enriquecer-incluidos {alvo}{regra}",
                     alternativa=f"{RS} validar elusao --etapa {etapa} --rodada {rodada} --n 300 --semente <outra semente>"
                                 f"{regra}", motivo_reprovacao=motivo,
                     incluidos_humanos_necessarios=necessarios, incluidos_ia_nao_sorteados=disponiveis)
    if motivo == "humanos":
        return _acao("tarefa", "validação reprovada pela concordância entre os humanos, não pela IA: discuta as "
                               "discordâncias e preencha decisao_consenso na planilha; se a concordância seguir baixa, "
                               "recalibre os critérios com a dupla humana (references/ia-validacao.md, seção 4 A e C)",
                     exige_humano=True, motivo_reprovacao=motivo)
    return _acao("tarefa", "validação abaixo do limiar: analisar falsos negativos e testar critérios vN+1 em "
                           "amostra nova (ou regra liberal; references/ia-validacao.md, seção 4 E)",
                 **({"motivo_reprovacao": motivo} if motivo else {}))


def _acao_antes_de_consolidar(raiz, rodadas, criterios):
    """Triagem por subagentes: lotes ainda não mesclados ou divergências de A e B sem árbitro.

    Lê os manifestos em 02-triagem/lotes/<rodada>/<revisor>/manifesto.json e o ledger (decisões
    vigentes de cada rodada, com a mesma consolidação do `triagem consolidar`).
    """
    try:
        from . import triagem_lotes as tl
    except Exception:  # noqa: BLE001 - sem o módulo de lotes, a sugestão volta a ser consolidar
        return None
    for rodada in rodadas:
        pendentes = {}
        for manifesto in sorted((Path(raiz) / "02-triagem" / "lotes" / rodada).glob("*/manifesto.json")):
            try:
                dados = json.loads(manifesto.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            n = sum(1 for l in dados.get("lotes") or [] if isinstance(l, dict) and l.get("status") != "mesclado")
            if n:
                pendentes[manifesto.parent.name] = n
        if pendentes:
            revisor, n = sorted(pendentes.items())[0]
            return _acao("comando", f"rodada {rodada}: {n} lotes do revisor {revisor} ainda não mesclados (despache os "
                                    "subagentes que faltam e mescle antes de consolidar)",
                         f"{RS} triagem mesclar --rodada {rodada} --revisor {revisor}", lotes_pendentes=pendentes)
        try:
            vigentes = tl.decisoes_vigentes(tl.ler_decisoes(raiz), etapa="ta", rodadas=[rodada])
            resultado = tl.consolidar_decisoes(vigentes)
        except Exception:  # noqa: BLE001 - ledger com formato inesperado: não bloqueia a sugestão
            continue
        revisores = {rev for res in resultado.values() for rev in (res.get("primarias") or {})}
        # Só divergências com parecer de IA vão ao árbitro cego; dupla humana desempata com humano (fila).
        sem_arbitro = sorted(i for i, res in resultado.items()
                             if res.get("divergente") and res.get("arbitro") is None and res.get("override") is None
                             and any(l.get("tipo_ator") != "humano" for l in (res.get("primarias") or {}).values()))
        if len(revisores) >= 2 and sem_arbitro:
            arquivo = Path(raiz) / "02-triagem" / "prompts" / f"{rodada}.md"
            crit = f"02-triagem/prompts/{rodada}.md" if arquivo.exists() else criterios
            return _acao("comando", f"rodada {rodada}: {len(sem_arbitro)} divergências entre "
                                    f"{' e '.join(sorted(revisores))} sem árbitro; prepare os lotes do árbitro cego antes de "
                                    "consolidar (references/03-organizacao-triagem.md, seção 7)",
                         f"{RS} triagem preparar --etapa ta --rodada {rodada} --revisor arbitro --apenas-divergentes "
                         f"--criterios {crit}", n_divergentes=len(sem_arbitro),
                         alternativa=f"{RS} triagem consolidar --rodada {rodada} --regra liberal (só se o protocolo "
                                     "previu a regra liberal; as divergências vão à fila humana)")
    return None


def _recall_combinado(raiz):
    try:
        dados = json.loads((Path(raiz) / esquema.ARQ_RECALL_ANCORAS).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    valor = ((dados.get("combinado") if isinstance(dados, dict) else None) or {}).get("recall")
    return float(valor) if isinstance(valor, (int, float)) and not isinstance(valor, bool) else None


def _press_registrado(raiz, est):
    """PRESS registrado: 01-busca/press_*.md ou pendência revisao_press aberta (autopiloto)."""
    if _arquivos(raiz, *PADRAO_PRESS):
        return True
    return any(p.get("tipo") == PENDENCIA_PRESS for p in estado.pendencias_abertas(est))


def cmd_status(args):
    raiz = estado.encontrar_projeto(args.dir)
    if raiz is None:
        pasta = Path(args.dir or os.getcwd()).resolve()
        subprojetos = projetos_em_subpastas(pasta)
        achados = detectar_artefatos(pasta)
        base = Path(args.dir) if args.dir else Path(".")
        resumos = [dict(resumo_subprojeto(pasta / s), dir=(base / s).as_posix()) for s in subprojetos]
        if subprojetos:
            # O mais recente (último evento) primeiro: é o palpite para retomar; com vários, confirme com o usuário.
            ordem = sorted(resumos, key=lambda r: r.get("ultimo_evento_em") or "", reverse=True)
            linhas = [f"{r['dir']}: {r.get('titulo') or '(sem título)'}; etapa {r.get('etapa_atual') or 'nenhuma (concluída)'}; "
                      f"último evento {r.get('ultimo_evento_em') or 'sem data'}" for r in ordem]
            descricao = ("nenhum projeto nesta pasta, mas há projeto de revisão em subpasta: retome-o com --dir "
                         "(não crie outro projeto por cima)")
            if len(ordem) > 1:
                descricao += (f". Há {len(ordem)} projetos (do mais recente ao mais antigo): " + " | ".join(linhas)
                              + ". Pergunte ao usuário qual retomar")
            acao = _acao("comando", descricao, _comando_status(ordem[0]["dir"]),
                         alternativas=[_comando_status(r["dir"]) for r in ordem[1:5]],
                         **({"exige_humano": True} if len(ordem) > 1 else {}))
        elif achados:
            acao = _acao("comando", "há artefatos de revisão nesta pasta; adote-os num projeto",
                         f'{RS} init --titulo "<título>" --adotar', sugestoes=sugestoes_adocao(achados))
        else:
            acao = _acao("comando", "nenhum projeto aqui; converse com o usuário e crie um",
                         f'{RS} init --titulo "<título>" --tipo <tipo> --autonomia checkpoints --triagem subagentes')
        estado.resumo({"projeto": None, "pasta": str(pasta), "projetos_em_subpastas": subprojetos,
                       "projetos": sorted(resumos, key=lambda r: r.get("ultimo_evento_em") or "", reverse=True),
                       "artefatos_encontrados": achados, "proxima_acao": com_dir(acao, args.dir)})
        return 0

    est = estado.carregar_estado(raiz)
    eventos = estado.ler_log(raiz)
    etapas, portoes = recalcular_etapas(raiz, est, eventos)
    contagens = prisma.calcular(raiz, est)
    inconsistencias = _inconsistencias(raiz, est, etapas, portoes, eventos, contagens)
    acao = com_dir(proxima_acao(raiz, est, etapas, portoes, eventos, inconsistencias), args.dir)
    atual = next((e for e in esquema.ETAPAS if etapas[e]["status"] not in ("concluida", "ignorada")), None)
    motivos_rascunho = motivos_de_rascunho(est, eventos)
    estado.resumo({
        "projeto": {"titulo": est["projeto"]["titulo"], "tipo_revisao": est["projeto"]["tipo_revisao"],
                    "variante": est["projeto"].get("variante"), "parcial": est["projeto"].get("parcial"),
                    "raiz": str(raiz)},
        "modo": {"autonomia": est["modo"]["autonomia"], "triagem": est["modo"]["triagem"]},
        "etapa_atual": atual,
        "etapas": {e: {k: v for k, v in info.items() if k != "evidencias" or v} for e, info in etapas.items()},
        "pendencias": estado.pendencias_abertas(est),
        "inconsistencias": com_dir(inconsistencias, args.dir),
        "alertas": com_dir(alertas_buscas(est), args.dir),
        "contagens": {"incluidos": contagens["incluidos"], "a_triar_bases": contagens["bases"]["a_triar"],
                      "etapas_nr": contagens["etapas_nr"], "buscas_inativas": contagens.get("buscas_inativas")},
        "rascunho": bool(motivos_rascunho),
        "motivos_rascunho": motivos_rascunho,
        "proxima_acao": acao,
    })
    return 0


def motivos_de_rascunho(est, eventos):
    """Por que os produtos saem como rascunho: pendências abertas, caixa com células pendentes, busca truncada."""
    motivos = []
    abertas = estado.pendencias_abertas(est)
    if abertas:
        motivos.append(f"{len(abertas)} pendências abertas")
    caixa = _ultimo_evento(eventos, "caixa_gerada")
    try:
        n_pendentes = int(((caixa or {}).get("dados") or {}).get("n_pendentes") or 0)
    except (TypeError, ValueError):
        n_pendentes = 0
    if n_pendentes > 0:
        motivos.append(f"última caixa de ferramentas (seq {caixa.get('seq')}) com {n_pendentes} células pendentes")
    truncadas = prisma.buscas_truncadas(est)
    if truncadas:
        motivos.append(f"buscas ativas truncadas: {', '.join(truncadas)}")
    return motivos


# ---------------------------------------------------------------------------
# portao
# ---------------------------------------------------------------------------
def _ler_criterios(texto):
    if not texto:
        return {}
    p = Path(texto)
    try:
        conteudo = p.read_text(encoding="utf-8") if p.suffix == ".json" and p.exists() else texto
        valor = json.loads(conteudo)
    except (OSError, json.JSONDecodeError) as e:
        raise ErroUso(f"--criterios não é JSON válido nem arquivo .json: {e}") from e
    if not isinstance(valor, dict):
        raise ErroUso("--criterios deve ser um objeto JSON")
    return valor


STATUS_TRECHO_FALHA = {"NAO_ENCONTRADA", "PAGINA_ERRADA", "SEM_TRECHO", "SEM_PAGINA", "PDF_NAO_ENCONTRADO"}


def _status_trecho_falha():
    try:
        from .efeitos_verificar import STATUS_FALHA
        return set(STATUS_FALHA)
    except Exception:  # noqa: BLE001 - módulo opcional aqui; a lista local cobre a versão atual
        return set(STATUS_TRECHO_FALHA)


def _sha_citado(evento, rel):
    for a in (evento or {}).get("artefatos") or []:
        if a.get("caminho") == rel:
            return a.get("sha256") or None
    return None


def _bloqueio(tipo, detalhe, **extra):
    return {"tipo": tipo, "detalhe": detalhe, **extra}


def checar_g1(est, criterios):
    pergunta = str((criterios or {}).get("pergunta") or est["projeto"].get("pergunta") or "").strip()
    tipo = (criterios or {}).get("tipo_revisao") or est["projeto"].get("tipo_revisao")
    bloqueios = []
    if not pergunta:
        bloqueios.append(_bloqueio("artefato", "pergunta não definida: aprove com --criterios '{\"pergunta\": \"...\", "
                                               "\"tipo_revisao\": \"...\"}'"))
    if not tipo or tipo == "indefinido":
        bloqueios.append(_bloqueio("artefato", "tipo_revisao indefinido: escolha o tipo (references/tipos-de-revisao.md) "
                                               "e informe-o nos critérios do G1"))
    return bloqueios


def _numero(dados, campos):
    for campo in campos:
        valor = dados.get(campo)
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            return float(valor)
    return None


def checar_atalho_rapida(evento):
    """G4 pelo atalho da variante rápida: dupla humana >= 20% com κ e segunda leitura de todos os excluídos pela IA."""
    dados = (evento or {}).get("dados") or {}
    seq = (evento or {}).get("seq")
    bloqueios = []
    fracao = _numero(dados, CAMPOS_FRACAO_DUPLA)
    if fracao is None:
        n_dupla, n_pop = _numero(dados, CAMPOS_N_DUPLA), _numero(dados, CAMPOS_N_POPULACAO)
        fracao = n_dupla / n_pop if n_dupla is not None and n_pop else None
    if fracao is None:
        bloqueios.append(_bloqueio("validacao", f"atalho da variante rápida (seq {seq}) sem a fração em dupla humana "
                                                "(fracao_dupla_humana, ou n_dupla_humana e n_populacao)"))
    elif fracao < FRACAO_MINIMA_DUPLA_RAPIDA:
        bloqueios.append(_bloqueio("limiar", f"atalho da variante rápida (seq {seq}): dupla humana em {fracao:.0%} dos "
                                             f"registros, abaixo de {FRACAO_MINIMA_DUPLA_RAPIDA:.0%}"))
    if _numero(dados, CAMPOS_KAPPA_DUPLA) is None:
        bloqueios.append(_bloqueio("validacao", f"atalho da variante rápida (seq {seq}) sem κ calculado da dupla humana "
                                                "(kappa_humanos)"))
    relidos, excluidos = dados.get("n_excluidos_relidos"), dados.get("n_excluidos_ia")
    segunda = dados.get("segunda_leitura_excluidos") is True or (
        isinstance(relidos, int) and isinstance(excluidos, int) and not isinstance(relidos, bool) and relidos >= excluidos)
    if not segunda:
        bloqueios.append(_bloqueio("validacao", f"atalho da variante rápida (seq {seq}) sem segunda leitura humana de "
                                                "todos os excluídos pela IA (segunda_leitura_excluidos = true, ou "
                                                "n_excluidos_relidos >= n_excluidos_ia)"))
    return bloqueios


def checar_g2(raiz):
    """G2: protocolo, codebook v0 e de elegibilidade, sem placeholders. Devolve (bloqueios, avisos)."""
    bloqueios, avisos = [], []
    protocolos = _arquivos(raiz, "00-protocolo", "protocolo*")
    if not protocolos:
        bloqueios.append(_bloqueio("artefato", "00-protocolo/protocolo* não existe (assets/templates/protocolo.md)"))
    codebooks_v0 = _arquivos(raiz, *PADRAO_CODEBOOK_V0)
    if not codebooks_v0:
        bloqueios.append(_bloqueio("artefato", "codebook v0 ausente: copie o codebook da família (assets/codebooks/) para "
                                               "00-protocolo/codebook_v0_<familia>.csv (references/01-pergunta-protocolo.md, "
                                               "seção 10)"))
    elegibilidade = [a for pasta, padrao in LOCAIS_CODEBOOK_ELEGIBILIDADE for a in _arquivos(raiz, pasta, padrao)]
    if not elegibilidade:
        bloqueios.append(_bloqueio("artefato", "codebook de elegibilidade ausente: copie "
                                               "assets/codebooks/elegibilidade_modelo.csv para "
                                               "00-protocolo/codebook_elegibilidade.csv e ajuste os critérios "
                                               "(references/01-pergunta-protocolo.md, seção 10)"))
    restantes = {}
    for rel in protocolos:
        if Path(rel).suffix.lower() in EXTENSOES_PROTOCOLO_TEXTO:
            achados = placeholders_no_texto(_ler_texto(raiz, rel), angulares=True)
            if achados:
                restantes[rel] = achados
    for rel in codebooks_v0 + elegibilidade:
        achados = placeholders_no_texto(_ler_texto(raiz, rel), angulares=False)
        if achados:
            restantes[rel] = achados
    for rel, achados in restantes.items():
        bloqueios.append(_bloqueio("artefato", f"placeholders não preenchidos em {rel} ({len(achados)}; ex.: "
                                               f"{', '.join(achados[:3])}): substitua pelo que o protocolo decidiu ou "
                                               "escreva \"Não se aplica: <motivo>\" sem os sinais", arquivo=rel,
                                   n=len(achados)))
    if not _arquivos(raiz, "00-protocolo", "revisao_metodologica*"):
        avisos.append("sem parecer do revisor metodológico em 00-protocolo/revisao_metodologica* "
                      "(agentes/revisor-metodologico.md)")
    return bloqueios, avisos


_RE_COMENTARIO_HTML = re.compile(r"<!--.*?-->", re.S)
_RE_CERCA_CODIGO = re.compile(r"(?ms)^[ \t]*(`{3,}|~{3,}).*?^[ \t]*\1[ \t]*$")
_RE_CODIGO_INLINE = re.compile(r"`[^`\n]*`")
_RE_MATEMATICA = re.compile(r"\$\$.*?\$\$|\$[^$\n]+\$", re.S)
_RE_ANGULAR = re.compile(r"<(?![\s=\-!/])([^<>\n]{1,300}?)(?<!\s)>")
_RE_CHAVES = re.compile(r"(?<![\\$^_\w{}]){(?![#.=%\s<{\"'])([^{}\n]{1,300}?)}")
_RE_TAG_HTML = re.compile(r"^/?([A-Za-z][A-Za-z0-9]*)(\s[^<>]*)?/?$")
TAGS_HTML = {
    "a", "abbr", "b", "blockquote", "br", "caption", "center", "cite", "code", "col", "colgroup", "dd", "del", "details",
    "div", "dl", "dt", "em", "figcaption", "figure", "font", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img",
    "ins", "kbd", "li", "mark", "ol", "p", "pre", "q", "s", "small", "span", "strong", "sub", "summary", "sup",
    "table", "tbody", "td", "th", "thead", "tr", "u", "ul", "wbr", "section", "article", "aside", "header", "footer",
}


def placeholders_no_texto(texto, angulares=True):
    """Placeholders de modelo ainda no texto: `<...>` (se `angulares`) e `{...}`.

    Ignora comentários HTML, blocos e trechos de código, matemática, autolinks (<https://...>), tags HTML
    comuns (<br>, <sup>...), atributos do Quarto ({#sec-x}, {.classe}) e comparações com espaço (a < b).
    """
    limpo = _RE_COMENTARIO_HTML.sub(" ", texto or "")
    limpo = _RE_CERCA_CODIGO.sub(" ", limpo)
    limpo = _RE_CODIGO_INLINE.sub(" ", limpo)
    limpo = _RE_MATEMATICA.sub(" ", limpo)
    achados = []
    if angulares:
        for m in _RE_ANGULAR.finditer(limpo):
            conteudo = m.group(1).strip()
            tag = _RE_TAG_HTML.match(conteudo)
            if re.match(r"(?i)^(https?|ftp|mailto):", conteudo) or re.fullmatch(r"[^\s@]+@[^\s@]+", conteudo):
                continue
            if tag and tag.group(1).lower() in TAGS_HTML:
                continue
            achados.append(m.group(0))
    achados += [m.group(0) for m in _RE_CHAVES.finditer(limpo)]
    return list(dict.fromkeys(achados))


def _ler_texto(raiz, rel):
    try:
        return (Path(raiz) / rel).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def checar_g3(raiz, est):
    """G3: busca registrada, nenhuma busca ativa truncada, PRESS registrado; avisos de recall das âncoras."""
    bloqueios = []
    if not (_buscas_ativas(est) or _arquivos(raiz, "01-busca/brutos") or _existe(raiz, esquema.ARQ_REGISTROS)):
        bloqueios.append(_bloqueio("artefato", "nenhuma busca registrada nem exportação em 01-busca/brutos"))
    truncadas = prisma.buscas_truncadas(est)
    if truncadas:
        bloqueios.append(_bloqueio("limiar", f"buscas ativas com resultados truncados ({', '.join(truncadas)}): os "
                                             "identificados do PRISMA ficariam subcontados; rode cada busca inteira e "
                                             "registre-a com --substituir (`buscar openalex` para buscas feitas pela API, "
                                             "`importar` para exportações; references/02-busca.md, seção 5), "
                                             "ou (humano) siga com --forcar --motivo", buscas=truncadas))
    if not _press_registrado(raiz, est):
        bloqueios.append(_bloqueio("artefato", "PRESS não registrado: nenhum 01-busca/press_*.md nem pendência "
                                               f"{PENDENCIA_PRESS} aberta (references/02-busca.md, seção 8)"))
    return bloqueios, avisos_recall_ancoras(raiz)


def _cmd_rob_fase1(ferramenta="<ferramenta>"):
    return (f"{RS} qualidade consolidar --ferramenta {ferramenta} --a <avaliação A> --b <avaliação B> "
            f"--avaliador-a {PAPEL_HUMANO} --avaliador-b <papel humano do segundo avaliador>")


def _cmd_rob_fase2(ferramenta):
    return (f"{RS} qualidade consolidar --ferramenta {ferramenta} --consenso "
            f"{esquema.PADRAO_ROB_CONSENSO.format(ferramenta=ferramenta)} --por {PAPEL_HUMANO}")


def ultimos_rob_por_ferramenta(eventos):
    """{ferramenta: último evento rob_consolidado}; eventos antigos sem `dados.ferramenta` ficam na chave None."""
    ultimos = {}
    for ev in eventos or []:
        if ev.get("evento") == "rob_consolidado":
            ultimos[(ev.get("dados") or {}).get("ferramenta")] = ev
    return ultimos


def resultados_exigidos_rob(raiz):
    """(resultados que precisam de rob_geral, origem): [(chave, construto_outcome, ferramenta)].

    Vale 04-qualidade/resultados_avaliados.csv quando existe (a lista do protocolo, references/05-qualidade.md,
    seção 5); senão, os pares chave × construto_outcome de efeitos_extraidos.csv (ferramenta vazia = qualquer uma).
    """
    caminho = Path(raiz) / ARQ_RESULTADOS_AVALIADOS
    if caminho.exists():
        try:
            from . import qualidade
            _, linhas = qualidade.ler_tabela(caminho)
        except Exception:  # noqa: BLE001 - arquivo humano ilegível: lê como CSV simples
            linhas = prisma._ler_csv(caminho) or []
        exigidos = {((l.get("chave") or "").strip(), (l.get("construto_outcome") or "").strip(),
                     (l.get("ferramenta") or "").strip()) for l in linhas if (l.get("chave") or "").strip()}
        return sorted(exigidos), ARQ_RESULTADOS_AVALIADOS
    efeitos = prisma._ler_csv(Path(raiz) / esquema.ARQ_EFEITOS_EXTRAIDOS)
    if efeitos:
        exigidos = {((l.get("chave") or "").strip(), (l.get("construto_outcome") or "").strip(), "")
                    for l in efeitos if (l.get("chave") or "").strip()}
        return sorted(exigidos), esquema.ARQ_EFEITOS_EXTRAIDOS
    return [], None


def _linhas_rob_conferem(linhas_ferramenta, dados):
    """As linhas de uma ferramenta em rob_geral.csv batem com o que o evento rob_consolidado registrou."""
    if not isinstance(dados.get("rob_geral"), dict) or not isinstance(dados.get("n_resultados"), int):
        return True
    distribuicao = collections.Counter((l.get("rob_geral") or "").strip() for l in linhas_ferramenta)
    n_validados = sum(1 for l in linhas_ferramenta if (l.get("validado_humano") or "").strip() == "1")
    return (len(linhas_ferramenta) == dados["n_resultados"]
            and dict(distribuicao) == {str(k): v for k, v in dados["rob_geral"].items()}
            and (not isinstance(dados.get("n_validados_humano"), int) or n_validados == dados["n_validados_humano"]))


def checar_rob(raiz, est, eventos):
    """G7: risco de viés consolidado e validado por humano, cobrindo todos os resultados avaliados.

    Fora de esquema.TIPOS_SEM_ROB:
      - artefato: nenhum rob_consolidado; fase 1 (fila_gerada de consenso_rob) de uma ferramenta sem a fase 2;
        ferramenta citada em resultados_avaliados.csv sem consolidação; arquivo citado pelo último rob_consolidado
        de uma ferramenta que mudou ou sumiu (rob_geral.csv, que todas as ferramentas regravam, é conferido pelo
        último evento que o gravou e, para as demais, pelas linhas da ferramenta); resultado avaliado sem rob_geral
        (04-qualidade/resultados_avaliados.csv, ou chave × construto_outcome de efeitos_extraidos.csv).
      - validacao: último rob_consolidado de uma ferramenta sem todos_validados_humano = true.
    """
    tipo = ((est or {}).get("projeto") or {}).get("tipo_revisao")
    if tipo in esquema.TIPOS_SEM_ROB:
        return []
    ultimos = ultimos_rob_por_ferramenta(eventos)
    fase1 = {}
    for ev in eventos or []:
        dados = ev.get("dados") or {}
        if ev.get("evento") == "fila_gerada" and dados.get("fila") == FILA_CONSENSO_ROB and dados.get("ferramenta"):
            fase1[dados["ferramenta"]] = ev
    if not ultimos:
        pendentes = sorted(fase1)
        if pendentes:
            return [_bloqueio("artefato", f"risco de viés sem a fase 2 da consolidação ({', '.join(pendentes)}): resolva os "
                                          "desacordos no arquivo de consenso e rode a fase 2 (references/05-qualidade.md, "
                                          "seção 5)", comando=_cmd_rob_fase2(pendentes[0]))]
        return [_bloqueio("artefato", "risco de viés não consolidado: nenhum evento rob_consolidado (avaliação em dupla "
                                      f"e consenso por domínio em {esquema.PADRAO_ROB_CONSENSO.format(ferramenta='<ferramenta>')}"
                                      f" e {esquema.ARQ_ROB_GERAL}, com `rs.py qualidade consolidar`; "
                                      "references/05-qualidade.md, seção 5). Tipos sem RoB: "
                                      + ", ".join(esquema.TIPOS_SEM_ROB), comando=_cmd_rob_fase1())]
    bloqueios = []
    for ferramenta in sorted(f for f in fase1 if f not in ultimos):
        bloqueios.append(_bloqueio("artefato", f"risco de viés com {ferramenta}: fase 1 feita (seq {fase1[ferramenta].get('seq')}) "
                                               "sem a fase 2 (rob_geral); resolva os desacordos e consolide",
                                   comando=_cmd_rob_fase2(ferramenta)))
    escritor_geral = max(ultimos.values(), key=lambda ev: int(ev.get("seq") or 0))
    rob_geral = prisma._ler_csv(Path(raiz) / esquema.ARQ_ROB_GERAL)
    for ferramenta, ev in sorted(ultimos.items(), key=lambda kv: int(kv[1].get("seq") or 0)):
        rotulo = ferramenta or "(sem ferramenta no evento)"
        dados = ev.get("dados") or {}
        refazer = _cmd_rob_fase2(ferramenta) if ferramenta else None
        for art in ev.get("artefatos") or []:
            rel, sha = art.get("caminho"), art.get("sha256")
            if not rel or not sha:
                continue
            p = Path(raiz) / rel
            if rel == esquema.ARQ_ROB_GERAL and ev is not escritor_geral:
                if p.exists() and ferramenta and rob_geral is not None and not _linhas_rob_conferem(
                        [l for l in rob_geral if (l.get("ferramenta") or "").strip() == ferramenta], dados):
                    bloqueios.append(_bloqueio("artefato", f"linhas de {ferramenta} em {rel} diferem da consolidação do "
                                                           f"RoB (seq {ev.get('seq')}): consolide de novo", comando=refazer))
                continue
            if not p.exists():
                bloqueios.append(_bloqueio("artefato", f"{rel} citado pela consolidação do RoB de {rotulo} (seq "
                                                       f"{ev.get('seq')}) não existe mais: consolide de novo", comando=refazer))
            elif estado.sha256_arquivo(p) != sha:
                bloqueios.append(_bloqueio("artefato", f"{rel} mudou depois da consolidação do RoB de {rotulo} (seq "
                                                       f"{ev.get('seq')}): consolide de novo", comando=refazer))
        if dados.get("todos_validados_humano") is not True:
            n_res, n_val = dados.get("n_resultados"), dados.get("n_validados_humano")
            contagem = (f"{n_res - n_val} de {n_res} resultados" if isinstance(n_res, int) and isinstance(n_val, int)
                        else "resultados")
            bloqueios.append(_bloqueio("validacao", f"RoB de {rotulo} (seq {ev.get('seq')}) com {contagem} sem validação "
                                                    "humana (todos_validados_humano diferente de true): a concordância entre "
                                                    "avaliadores não humanos não valida; resolva por humano no consenso e "
                                                    "consolide de novo", comando=refazer))
    exigidos, origem = resultados_exigidos_rob(raiz)
    ferramentas_exigidas = sorted({f for _, _, f in exigidos if f} - set(ultimos))
    if ferramentas_exigidas and None not in ultimos:
        bloqueios.append(_bloqueio("artefato", f"ferramentas de {ARQ_RESULTADOS_AVALIADOS} sem consolidação do RoB: "
                                               f"{', '.join(ferramentas_exigidas)}",
                                   comando=_cmd_rob_fase1(ferramentas_exigidas[0])))
    if exigidos:
        avaliados = [(_dobrar_texto(l.get("chave")), _dobrar_texto(l.get("construto_outcome")),
                      _dobrar_texto(l.get("ferramenta"))) for l in rob_geral or [] if (l.get("rob_geral") or "").strip()]
        faltam = []
        for chave, construto, ferramenta in exigidos:
            c, o, f = _dobrar_texto(chave), _dobrar_texto(construto), _dobrar_texto(ferramenta)
            if not any(ac == c and (not o or not ao or ao == o) and (not f or af == f) for ac, ao, af in avaliados):
                faltam.append(f"{chave}×{construto or '-'}" + (f" ({ferramenta})" if ferramenta else ""))
        if faltam:
            bloqueios.append(_bloqueio("artefato", f"{len(faltam)} resultados avaliados ({origem}) sem rob_geral em "
                                                   f"{esquema.ARQ_ROB_GERAL} (ex.: {', '.join(faltam[:5])}): avalie em dupla e "
                                                   "consolide (MECIR C52)", n=len(faltam), comando=_cmd_rob_fase1()))
    return bloqueios


def _arquivos_concordancia(raiz):
    """concordancia.csv da extração (05-decomposicao/**), sem os do piloto; o de 05-decomposicao/concordancia/ primeiro."""
    todos = [a for a in _arquivos(raiz, "05-decomposicao", "concordancia.csv", recursivo=True)
             if "piloto" not in Path(a).parts]
    preferido = "05-decomposicao/concordancia/concordancia.csv"
    return sorted(todos, key=lambda a: (a != preferido, a))


def variaveis_sinalizadas(caminho):
    """Variáveis com `sinalizada` = sim no concordancia.csv do fichamento-sistematico (bloco por variável)."""
    sinalizadas, cabecalho = [], None
    try:
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            for linha in csv.reader(f):
                if not linha:
                    continue
                if "sinalizada" in linha and "variavel" in linha:
                    cabecalho = linha
                    continue
                if cabecalho is None or len(linha) < len(cabecalho) or (linha[0] != "por_variavel" and cabecalho[0] == "nivel"):
                    continue
                registro = dict(zip(cabecalho, linha))
                if (registro.get("sinalizada") or "").strip().lower() in {"sim", "1", "true", "s"}:
                    sinalizadas.append(registro.get("variavel", "?"))
    except OSError:
        return []
    return sinalizadas


def avisos_concordancia(raiz, est):
    """G7 (só avisos): concordância da extração calculada e variáveis sinalizadas com arbitragem registrada."""
    arquivos = _arquivos_concordancia(raiz)
    if not arquivos:
        return ["concordância da extração não calculada: nenhum 05-decomposicao/**/concordancia.csv fora do piloto "
                "(segundo codificador cego em ≥ 20% dos estudos, mínimo 10; κ ou PABAK ≥ 0,7 e concordância ≥ 80% por "
                "variável; references/ia-validacao.md, seção 5)"]
    rel = arquivos[0]
    sinalizadas = variaveis_sinalizadas(Path(raiz) / rel)
    arbitradas = any(p.get("tipo") == PENDENCIA_CONCORDANCIA and p.get("status") == "fechada"
                     and (not p.get("arquivo") or p.get("arquivo") == rel) for p in (est or {}).get("pendencias") or [])
    if sinalizadas and not arbitradas:
        return [f"{len(sinalizadas)} variáveis sinalizadas em {rel} (κ/PABAK < 0,7 ou concordância < 80%) sem arbitragem "
                f"registrada: {', '.join(sinalizadas[:10])}; redefina no codebook e recodifique, ou arbitre e feche a "
                f"pendência {PENDENCIA_CONCORDANCIA} (references/06-decomposicao.md)"]
    return []


def _dobrar_texto(valor):
    return re.sub(r"\s+", " ", normalizar.ascii_fold(str(valor or "")).strip().lower())


def checar_certeza(raiz, est):
    """G8: caixa obrigatória em OQF; 06-analise/certeza.csv com uma linha de certeza por célula de efeito da caixa."""
    tipo = ((est or {}).get("projeto") or {}).get("tipo_revisao")
    caixa = prisma._ler_csv(Path(raiz) / esquema.ARQ_CAIXA)
    bloqueios = []
    if caixa is None and tipo == "oqf_mista_sequencial":
        bloqueios.append(_bloqueio("artefato", f"{esquema.ARQ_CAIXA} não existe: numa revisão OQF a caixa de ferramentas é "
                                               f"o produto da síntese (rode `{RS} caixa`)"))
    if tipo in TIPOS_SEM_CERTEZA and caixa is None:
        return bloqueios
    certeza = prisma._ler_csv(Path(raiz) / esquema.ARQ_CERTEZA)
    if certeza is None:
        bloqueios.append(_bloqueio("artefato", f"{esquema.ARQ_CERTEZA} não existe: registre o juízo de certeza (GRADE por "
                                               "célula de efeito, CERQual por achado) feito por humanos "
                                               "(references/07b-sintese-qualitativa-integracao.md)"))
        return bloqueios
    julgadas = []
    for linha in certeza:
        dimensao = _dobrar_texto(linha.get("dimensao") or "efeito")
        if dimensao == "efeito" and (linha.get("certeza") or "").strip():
            julgadas.append((_dobrar_texto(linha.get("familia_intervencao")), _dobrar_texto(linha.get("construto_outcome")),
                             _dobrar_texto(linha.get("classe_desenho"))))
    sem_certeza = []
    for linha in caixa or []:
        if _dobrar_texto(linha.get("dimensao")) != "efeito":
            continue
        fam, out, classe = (_dobrar_texto(linha.get(c)) for c in ("familia_intervencao", "construto_outcome", "classe_desenho"))
        if not any((not fam or f == fam) and o == out and (not c or not classe or c == classe) for f, o, c in julgadas):
            sem_certeza.append(linha.get("celula_id") or f"{linha.get('familia_intervencao', '')} × "
                                                        f"{linha.get('construto_outcome', '')}")
    if sem_certeza:
        bloqueios.append(_bloqueio("certeza", f"{len(sem_certeza)} células de efeito da caixa sem linha de certeza em "
                                              f"{esquema.ARQ_CERTEZA} (ex.: {', '.join(sem_certeza[:5])}): faça o GRADE da "
                                              "célula e rode `caixa` de novo", n=len(sem_certeza)))
    return bloqueios


def _declaracao_cobre_ate(raiz, eventos):
    """(seq coberto, origem) da declaração de uso de IA atual, ou (None, motivo).

    Vale `dados.ultimo_seq` do evento relatorio_gerado da declaração cuja cópia do arquivo (sha256) é a atual.
    Declarações antigas, sem o campo, caem na frase "até o evento seq N" do próprio texto.
    """
    arq = Path(raiz) / esquema.ARQ_DECLARACAO_IA
    sha = estado.sha256_arquivo(arq)
    for ev in reversed(eventos):
        if ev.get("evento") != "relatorio_gerado" or _sha_citado(ev, esquema.ARQ_DECLARACAO_IA) != sha:
            continue
        valor = (ev.get("dados") or {}).get("ultimo_seq")
        if isinstance(valor, int) and not isinstance(valor, bool):
            return valor, "evento"
        break
    try:
        texto = arq.read_text(encoding="utf-8")
    except OSError:
        texto = ""
    m = _RE_SEQ_DECLARACAO.search(texto)
    if m and any(ev.get("evento") == "relatorio_gerado" and _sha_citado(ev, esquema.ARQ_DECLARACAO_IA) == sha
                 for ev in eventos):
        return int(m.group(1)), "texto"
    return None, "sem_evento"


def checar_piloto(raiz, eventos):
    """G6: piloto consolidado (evento extracao_consolidada ou um fichamentos_master em 05-decomposicao/)."""
    if _ultimo_evento(eventos, "extracao_consolidada") or _arquivos(raiz, "05-decomposicao", "*fichamentos_master*.csv",
                                                                    recursivo=True):
        return []
    return [_bloqueio("artefato", "piloto de extração não consolidado: nenhum fichamentos_master*.csv em 05-decomposicao/ "
                                  "nem evento extracao_consolidada (rode o piloto com fichamento-sistematico)")]


def checar_efeitos(raiz, eventos):
    """G7: efeitos_extraidos.csv verificado depois da última mudança, sem falhas e com verificação humana."""
    if not _existe(raiz, esquema.ARQ_EFEITOS_EXTRAIDOS):
        return []
    verificacao = prisma._ler_csv(Path(raiz) / esquema.ARQ_VERIFICACAO_EFEITOS)
    ultimo = _ultimo_evento(eventos, "efeitos_verificados")
    if verificacao is None or ultimo is None:
        return [_bloqueio("artefato", f"{esquema.ARQ_EFEITOS_EXTRAIDOS} existe, mas os efeitos não foram verificados "
                                      f"(rode `{RS} analise verificar-efeitos`)", acao="verificar")]
    bloqueios = []
    sha_verificado = _sha_citado(ultimo, esquema.ARQ_EFEITOS_EXTRAIDOS)
    if sha_verificado and sha_verificado != estado.sha256_arquivo(Path(raiz) / esquema.ARQ_EFEITOS_EXTRAIDOS):
        bloqueios.append(_bloqueio("artefato", f"{esquema.ARQ_EFEITOS_EXTRAIDOS} mudou depois da última verificação "
                                               f"(seq {ultimo.get('seq')}); rode `{RS} analise verificar-efeitos` de novo",
                                   acao="verificar"))
    falha_trecho = _status_trecho_falha()
    reprovados = [l.get("id_efeito", "?") for l in verificacao
                  if (l.get("status_trecho") or "").upper() in falha_trecho or (l.get("erros") or "").strip()]
    sem_humano = [l.get("id_efeito", "?") for l in verificacao
                  if l.get("apto_g7") != "1" and l.get("id_efeito", "?") not in reprovados]
    if reprovados:
        bloqueios.append(_bloqueio("artefato", f"{len(reprovados)} efeitos com trecho não localizado na página ou erro de "
                                               f"plausibilidade (ex.: {', '.join(reprovados[:5])}): refaça a extração",
                                   n=len(reprovados)))
    if sem_humano:
        bloqueios.append(_bloqueio("verificacao", f"{len(sem_humano)} efeitos sem verificação humana na página do PDF "
                                                  f"(apto_g7 = 0; ex.: {', '.join(sem_humano[:5])})", n=len(sem_humano)))
    return bloqueios


def checar_caixa(raiz):
    """G8: toda linha da caixa de ferramentas com status_rotulo 'definido'."""
    caixa = prisma._ler_csv(Path(raiz) / esquema.ARQ_CAIXA)
    if caixa is None:
        return []
    pendentes = [l.get("celula_id") or f"{l.get('dimensao', '')}:{l.get('rotulo', '')}" for l in caixa
                 if (l.get("status_rotulo") or "").strip() != "definido"]
    if not pendentes:
        return []
    return [_bloqueio("certeza", f"{len(pendentes)} células da caixa de ferramentas com status_rotulo diferente de "
                                 f"'definido' (ex.: {', '.join(pendentes[:5])}): complete certeza e enunciados e rode "
                                 f"`{RS} caixa` de novo", n=len(pendentes))]


def avisos_meta(raiz):
    """G8: grupos do meta_resumo.json que não ajustaram (dependência não resolvida, erro de ajuste)."""
    try:
        meta = json.loads((Path(raiz) / esquema.ARQ_META_RESUMO).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    grupos = meta.get("grupos") if isinstance(meta, dict) else None
    problemas = [g for g in grupos or [] if isinstance(g, dict)
                 and g.get("status") in ("dependencia_nao_resolvida", "erro_ajuste")]
    if not problemas:
        return []
    exemplos = ", ".join(f"{g.get('construto_outcome') or g.get('grupo') or '?'} ({g.get('status')})" for g in problemas[:5])
    return [f"{len(problemas)} grupos da meta-análise sem ajuste válido em {esquema.ARQ_META_RESUMO}: {exemplos}; "
            "declare-os como não sintetizados ou resolva a dependência (--dependencia che)"]


VALORES_VERIFICADO = {"sim", "s", "1", "true", "yes", "y", "x"}


def avisos_efeitos_nao_verificados(raiz, est, eventos):
    """G8 (só aviso): sem o G7 (etapa 09 ignorada, ex.: projeto parcial meta), efeitos que nenhum humano conferiu.

    Lê `resumo_r.n_nao_verificados_humano` do último `analise_executada` do efeitos.R; sem esse evento, conta as
    linhas calculadas de 06-analise/efeitos.csv sem verificado_humano.
    """
    if "09_extracao_rob" not in set(((est or {}).get("projeto") or {}).get("etapas_ignoradas") or []):
        return []
    n, origem = None, None
    for ev in reversed(eventos or []):
        dados = ev.get("dados") or {}
        resumo_r = dados.get("resumo_r") or {}
        if ev.get("evento") == "analise_executada" and (dados.get("script") == "efeitos.R" or resumo_r.get("comando") == "efeitos"):
            valor = resumo_r.get("n_nao_verificados_humano")
            if isinstance(valor, int) and not isinstance(valor, bool):
                n, origem = valor, f"analise efeitos, seq {ev.get('seq')}"
            break
    if n is None:
        linhas = prisma._ler_csv(Path(raiz) / esquema.ARQ_EFEITOS_CALCULADOS)
        if linhas is None:
            return []
        n = sum(1 for l in linhas if (l.get("yi") or "").strip() not in ("", "NA")
                and (l.get("verificado_humano") or "").strip().lower() not in VALORES_VERIFICADO)
        origem = esquema.ARQ_EFEITOS_CALCULADOS
    if n <= 0:
        return []
    return [f"{n} efeitos calculados sem verificado_humano ({origem}): o projeto não passa pelo G7, então a síntese "
            "usa números que nenhum humano conferiu contra a fonte; confirme com o usuário e declare como limitação "
            "(references/07a-sintese-quantitativa.md, passo 4; a síntese é rascunho)"]


def checar_prisma(raiz, est, eventos):
    """G9: PRISMA gerado depois da última mudança nos dados (insumos) e nas pendências."""
    arq = Path(raiz) / prisma.ARQ_CONTAGENS
    ultimo = _ultimo_evento(eventos, "prisma_gerado")
    if ultimo is None or not arq.exists():
        return [_bloqueio("artefato", f"PRISMA não gerado no projeto (rode `{RS} prisma`)")]
    sha = _sha_citado(ultimo, prisma.ARQ_CONTAGENS)
    if sha and sha != estado.sha256_arquivo(arq):
        return [_bloqueio("artefato", f"{prisma.ARQ_CONTAGENS} foi alterado depois do último `prisma`; gere de novo")]
    try:
        gerado = json.loads(arq.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [_bloqueio("artefato", f"{prisma.ARQ_CONTAGENS} ilegível ({e}); gere de novo")]
    bloqueios = []
    if gerado.get("origem") != "manual":
        atual = prisma.calcular(raiz, est, gerado.get("tipo") or "2020")
        mudaram = sorted(k for k in set(atual["insumos"]) | set(gerado.get("insumos") or {})
                         if atual["insumos"].get(k) != (gerado.get("insumos") or {}).get(k))
        if mudaram:
            bloqueios.append(_bloqueio("artefato", "os dados mudaram depois do último PRISMA (" + ", ".join(mudaram[:6])
                                                   + f"); rode `{RS} prisma` de novo"))
    abertas = sorted(p["id"] for p in estado.pendencias_abertas(est))
    if sorted(gerado.get("pendencias_abertas") or []) != abertas:
        bloqueios.append(_bloqueio("artefato", "as pendências abertas mudaram depois do último PRISMA (a marca de rascunho "
                                               f"está desatualizada); rode `{RS} prisma` de novo"))
    return bloqueios


ATOR_DECLARACAO_IA = "rs.py declaracao-ia"  # espelha declaracao_ia.ATOR (eventos que a declaração não conta)
_RE_SEQ_DECLARACAO = re.compile(r"até o evento seq (\d+)")


def avisos_recall_ancoras(raiz):
    """G3 (só avisos): recall relativo das âncoras em 01-busca/recall_ancoras.json (`filtrar --ancoras`).

    Não bloqueia: o recall é relativo ao conjunto de âncoras e 0,95 é referência, não limiar
    (references/02-busca.md, seção 7). Avisa quando o arquivo não existe, quando o recall combinado (buscas nas
    bases) é menor que 1, listando as âncoras não achadas, e quando foi calculado sobre outro
    registros_unicos.csv.
    """
    caminho = Path(raiz) / esquema.ARQ_RECALL_ANCORAS
    if not caminho.exists():
        return [f"{esquema.ARQ_RECALL_ANCORAS} não existe: rode `{RS} filtrar --config 01-busca/filtros_v1.json "
                "--ancoras 00-protocolo/ancoras_validacao.csv` e leve o recall das âncoras aos critérios do G3"]
    try:
        recall = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"{esquema.ARQ_RECALL_ANCORAS} ilegível ({e}): rode `{RS} filtrar --ancoras` de novo"]
    avisos = []
    combinado = recall.get("combinado") if isinstance(recall, dict) else None
    combinado = combinado if isinstance(combinado, dict) else {}
    valor = combinado.get("recall")
    if not isinstance(valor, (int, float)) or isinstance(valor, bool):
        avisos.append(f"{esquema.ARQ_RECALL_ANCORAS} sem recall combinado (nenhuma âncora indexada com DOI ou "
                      "título + ano): confira o arquivo de âncoras")
    elif valor < 1:
        perdidas = [str(a) for a in combinado.get("perdidas") or []]
        avisos.append(f"recall combinado das âncoras = {valor:.2f} ({combinado.get('n_encontradas')} de "
                      f"{combinado.get('n_ancoras')}) < 1; não achadas pelas buscas nas bases: "
                      f"{', '.join(perdidas[:20]) or '(lista ausente no arquivo)'}"
                      f"{' e mais ' + str(len(perdidas) - 20) if len(perdidas) > 20 else ''}. Diagnostique a string "
                      "(nova versão com `importar --substituir`) ou declare a âncora como não indexada (indexada_em)")
    sha = recall.get("unicos_sha256") if isinstance(recall, dict) else None
    unicos = Path(raiz) / esquema.ARQ_UNICOS
    if sha and unicos.exists() and sha != estado.sha256_arquivo(unicos):
        avisos.append(f"{esquema.ARQ_RECALL_ANCORAS} foi calculado sobre outra versão de {esquema.ARQ_UNICOS}: "
                      f"rode `{RS} filtrar --ancoras` de novo")
    return avisos


def avisos_relato(raiz, eventos):
    """G9 (só avisos): .bib dos incluídos e declaração de IA atualizada em relação ao log."""
    avisos = []
    if not _existe(raiz, esquema.ARQ_BIB):
        avisos.append(f"{esquema.ARQ_BIB} não existe: rode `{RS} bib` (os templates de relato citam por ele)")
    if not _existe(raiz, esquema.ARQ_DECLARACAO_IA):
        return avisos  # a ausência já é bloqueio do G9
    # Eventos da própria declaração e reexecuções sem mudança não tornam a declaração desatualizada.
    relevantes = [ev for ev in eventos if (ev.get("ator") or {}).get("id") != ATOR_DECLARACAO_IA
                  and (ev.get("dados") or {}).get("reexecucao") is not True]
    if not relevantes:
        return avisos
    ultimo = max(relevantes, key=lambda ev: int(ev.get("seq") or 0))
    coberto, origem = _declaracao_cobre_ate(raiz, eventos)
    if coberto is None:
        avisos.append(f"{esquema.ARQ_DECLARACAO_IA} não corresponde a nenhuma declaração gerada pelo comando (escrita à "
                      f"mão ou editada depois): gere de novo com `{RS} declaracao-ia`")
    elif coberto < int(ultimo.get("seq") or 0):
        n_depois = sum(1 for ev in relevantes if int(ev.get("seq") or 0) > coberto)
        avisos.append(f"{esquema.ARQ_DECLARACAO_IA} cobre o log até o seq {coberto}, mas há {n_depois} eventos "
                      f"posteriores (o último: seq {ultimo.get('seq')}, {ultimo.get('evento')}): rode "
                      f"`{RS} declaracao-ia` de novo, por último (depois de `prisma` e `bib`)")
    return avisos


def checar_portao(raiz, est, g, eventos, criterios=None):
    """Checagens antes de aprovar um portão: (bloqueios, avisos).

    Bloqueio = {tipo, detalhe}, tipo artefato|limiar (barram também o autopiloto) ou
    validacao|verificacao|certeza|pendencia (dependem de humano: no autopiloto viram pendência).
    Avisos não barram; ficam no resumo e no log do portão.
    """
    bloqueios, avisos = [], []
    if g == "G1":
        bloqueios += checar_g1(est, criterios)
    if g == "G2":
        b, a = checar_g2(raiz)
        bloqueios += b
        avisos += a
    if g == "G3":
        b, a = checar_g3(raiz, est)
        bloqueios += b
        avisos += a
    if g == "G4":
        if not _existe(raiz, esquema.ARQ_TRIAGEM_TA_FINAL):
            bloqueios.append(_bloqueio("artefato", f"{esquema.ARQ_TRIAGEM_TA_FINAL} não existe"))
        ev, atende, avisos_val = validacao_do_portao(est, eventos)
        avisos += avisos_val
        ativas = _rodadas_ativas(est, "ta", eventos)
        if ev is None:
            bloqueios.append(_bloqueio("validacao", "nenhuma validação humana (finalidade validacao) calculada para a rodada "
                                                    f"ativa {'+'.join(ativas) or '(não definida)'} (rs.py validar calcular)"))
        elif _eh_atalho_rapida(ev) and atalho_rapida_aprovado(est, eventos):
            bloqueios += checar_atalho_rapida(ev)
            avisos.append(f"G4 pelo atalho da variante rápida (validação seq {ev.get('seq')}): recall ≥ 0,95 não exigido; "
                          "declare o atalho como limitação do processo (PRISMA 2020 item 23c)")
        elif _eh_atalho_rapida(ev):
            avisos.append(f"validação seq {ev.get('seq')} marcada atalho_rapida, mas o projeto não é variante rápida com "
                          f"`{CRITERIO_ATALHO_RAPIDA}` aprovado no G1: vale a regra geral (references/tipos-de-revisao.md, "
                          "seção 6)")
            if atende is not True:
                bloqueios.append(_bloqueio("limiar", f"a validação da rodada ativa (seq {ev.get('seq')}) não atende os "
                                                     "limiares do protocolo (recall ≥ 0,95 com LI ≥ 0,90)"))
        elif atende is False:
            bloqueios.append(_bloqueio("limiar", f"a validação da rodada ativa (seq {ev.get('seq')}) não atende os limiares "
                                                 "do protocolo (recall ≥ 0,95 com LI ≥ 0,90)"))
            if atalho_rapida_aprovado(est, eventos):
                avisos.append(f"o G1 aprovou `{CRITERIO_ATALHO_RAPIDA}`, mas a validação seq {ev.get('seq')} não traz os "
                              "campos do atalho (atalho_rapida, fração em dupla humana, κ, segunda leitura dos excluídos): "
                              "sem eles vale a regra geral; calcule de novo com `validar calcular --atalho-rapida` "
                              "(references/tipos-de-revisao.md, seção 6)")
    if g == "G5" and not _existe(raiz, esquema.ARQ_ELEGIBILIDADE_TC_FINAL):
        bloqueios.append(_bloqueio("artefato", f"{esquema.ARQ_ELEGIBILIDADE_TC_FINAL} não existe"))
    if g in ("G4", "G5"):
        etapa_limite = {"G4": {"05_organizacao", "06_triagem_ta"}, "G5": None}[g]
        contagens = prisma.calcular(raiz, est)
        for inv in prisma.invariantes_quebradas(contagens):
            if etapa_limite is None or INVARIANTE_ETAPA.get(inv["nome"], "07_textos_elegibilidade") in etapa_limite:
                bloqueios.append(_bloqueio("artefato", f"contagens não fecham: {inv['detalhe']}"))
        if g == "G5":
            aguardando = sum(contagens[r].get("aguardando_classificacao") or 0 for r in ("bases", "outros_metodos")
                             if isinstance(contagens[r].get("aguardando_classificacao"), int))
            if aguardando:
                avisos.append(f"{aguardando} relatórios aguardando classificação: relate-os no PRISMA e no texto")
    if g == "G6":
        bloqueios += checar_piloto(raiz, eventos)
    if g == "G7":
        bloqueios += checar_efeitos(raiz, eventos)
        bloqueios += checar_rob(raiz, est, eventos)
        avisos += avisos_concordancia(raiz, est)
    if g == "G8":
        bloqueios += checar_caixa(raiz)
        bloqueios += checar_certeza(raiz, est)
        avisos += avisos_meta(raiz)
        avisos += avisos_efeitos_nao_verificados(raiz, est, eventos)
    if g == "G9":
        bloqueios += checar_prisma(raiz, est, eventos)
        if not _existe(raiz, esquema.ARQ_DECLARACAO_IA):
            bloqueios.append(_bloqueio("artefato", f"{esquema.ARQ_DECLARACAO_IA} não existe (rode `{RS} declaracao-ia`)"))
        avisos += [a["detalhe"] for a in alertas_buscas(est)]
        avisos += avisos_relato(raiz, eventos)
    etapa = esquema.PORTOES[g]
    for p in estado.pendencias_abertas(est):
        if p.get("portao") == g or p.get("etapa") == etapa:
            bloqueios.append(_bloqueio("pendencia", f"{p['id']} aberta: {p.get('descricao', '')}"))
    return bloqueios, avisos


def checagens_portao(raiz, est, g, eventos, criterios=None):
    """Compatibilidade: só a lista de bloqueios de checar_portao."""
    return checar_portao(raiz, est, g, eventos, criterios)[0]


def _congelar(raiz, est, g):
    congelados = []
    for pasta, padrao, recursivo in CONGELAR_NO_PORTAO.get(g, []):
        for rel in _arquivos(raiz, pasta, padrao, recursivo=recursivo):
            if Path(rel).name.lower().startswith("emenda"):
                continue  # o registro de emendas nasce para mudar depois do congelamento
            atual = est["artefatos"].get(rel) or {}
            if atual.get("congelado_em"):
                continue
            est["artefatos"][rel] = {"caminho": rel, "sha256": estado.sha256_arquivo(Path(raiz) / rel),
                                     "congelado_em": estado.agora(), "portao": g, "versao": 1}
            congelados.append(rel)
    if g == "G2" and congelados:
        est["versoes_ativas"]["protocolo"] = "v1"
    if g == "G4" and congelados:
        est["versoes_ativas"]["criterios_ta"] = Path(max(congelados)).stem
    return congelados


def _reverter_nao_se_aplica(est, eventos, g):
    """Aprovar ou reprovar um portão marcado como não aplicável devolve a etapa ao fluxo normal."""
    if g not in _nao_aplicaveis(eventos):
        return False
    etapa = esquema.PORTOES[g]
    do_parcial = set(etapas_ignoradas_para(est["projeto"].get("parcial")))
    ignoradas = est["projeto"].get("etapas_ignoradas") or []
    if etapa in ignoradas and etapa not in do_parcial:
        est["projeto"]["etapas_ignoradas"] = [e for e in ignoradas if e != etapa]
    return True


def cmd_nao_se_aplica(raiz, est, eventos, g, ator_tipo, args):
    """`portao GN --nao-se-aplica --motivo`: dispensa um portão que o tipo de revisão permite dispensar."""
    etapa = esquema.PORTOES[g]
    if not (args.motivo or "").strip():
        raise ErroUso("--nao-se-aplica exige --motivo")
    tipo = est["projeto"].get("tipo_revisao")
    permitidos = esquema.PORTOES_OPCIONAIS_POR_TIPO.get(tipo, [])
    if g not in permitidos:
        raise ErroMetodologico(f"{g} não pode ser dispensado numa revisão do tipo {tipo}; dispensáveis para esse tipo: "
                               f"{', '.join(permitidos) or 'nenhum'} (esquema.PORTOES_OPCIONAIS_POR_TIPO)")
    portoes = _estado_portoes(eventos)
    if portoes.get("G1", {}).get("decisao") != "aprovado":
        raise ErroMetodologico("o tipo de revisão só vale depois do G1 aprovado; aprove o G1 antes de dispensar etapas")
    if ator_tipo != "humano" and est["modo"]["autonomia"] == "checkpoints":
        raise ErroMetodologico(f"modo checkpoints: só humano dispensa o {g}")
    if g in _nao_aplicaveis(eventos):
        estado.resumo({"ok": True, "portao": g, "decisao": "nao_se_aplica", "etapa": etapa, "ja_registrado": True})
        return 0
    if portoes.get(g, {}).get("decisao") == "aprovado":
        raise ErroUso(f"{g} já foi aprovado; reprove-o (--reprovar --motivo) antes de marcá-lo como não aplicável")
    est["etapas"][etapa].update({"status": "ignorada", "aprovado_por": None, "em": estado.agora()})
    ignoradas = est["projeto"].setdefault("etapas_ignoradas", [])
    if etapa not in ignoradas:
        ignoradas.append(etapa)
    estado.registrar_evento(raiz, "etapa_nao_aplicavel", etapa, ator_tipo, args.por,
                            dados={"portao": g, "etapa": etapa, "tipo_revisao": tipo,
                                   "variante": est["projeto"].get("variante")},
                            motivo=args.motivo, estado=est)
    pendencia = None
    if ator_tipo != "humano":
        pendencia = estado.abrir_pendencia(raiz, "revisao_humana_portao", etapa,
                                           f"confirmar que o {g} não se aplica: {args.motivo}", portao=g,
                                           ator_id="autopiloto")
    estado.resumo({"ok": True, "portao": g, "decisao": "nao_se_aplica", "etapa": etapa, "por": args.por,
                   "tipo_revisao": tipo, "pendencia_aberta": pendencia, "proxima_acao": _comando_status(args.dir)})
    return 0


def cmd_portao(args):
    raiz = estado.exigir_projeto(args.dir)
    g = args.portao.upper()
    if g not in esquema.PORTOES:
        raise ErroUso(f"portão desconhecido: {args.portao} (use {', '.join(esquema.PORTOES)})")
    est = estado.carregar_estado(raiz)
    eventos = estado.ler_log(raiz)
    etapa = esquema.PORTOES[g]
    ator_tipo = args.ator_tipo or ("ia_coordenador" if args.por == "autopiloto" else "humano")
    if ator_tipo not in esquema.TIPOS_ATOR:
        raise ErroUso(f"tipo de ator desconhecido: {ator_tipo}")
    criterios = _ler_criterios(args.criterios)
    autonomia = est["modo"]["autonomia"]

    if getattr(args, "nao_se_aplica", False):
        return cmd_nao_se_aplica(raiz, est, eventos, g, ator_tipo, args)

    if args.reprovar:
        if not args.motivo:
            raise ErroUso("--reprovar exige --motivo")
        revertido = _reverter_nao_se_aplica(est, eventos, g)
        est["etapas"][etapa].update({"status": "em_andamento", "aprovado_por": None, "em": estado.agora()})
        # Reprovar desfaz o congelamento feito por este portão: o texto volta a ser rascunho e
        # mudá-lo não é emenda. O histórico fica no log.
        descongelados = []
        for rel, info in (est.get("artefatos") or {}).items():
            if isinstance(info, dict) and info.get("portao") == g and info.get("congelado_em"):
                info.update({"congelado_em": None, "descongelado_em": estado.agora()})
                descongelados.append(rel)
        estado.registrar_evento(raiz, "portao", etapa, ator_tipo, args.por,
                                dados={"portao": g, "decisao": "reprovado", "criterios": criterios,
                                       "descongelados": descongelados, "reverte_nao_se_aplica": revertido},
                                motivo=args.motivo, estado=est)
        estado.resumo({"ok": True, "portao": g, "decisao": "reprovado", "etapa": etapa,
                       "descongelados": descongelados, "proxima_acao": _comando_status(args.dir)})
        return 0

    # Aprovação ---------------------------------------------------------------
    if ator_tipo != "humano":
        if autonomia == "checkpoints":
            raise ErroMetodologico(f"modo checkpoints: {g} só pode ser aprovado por humano")
        if g in esquema.PORTOES_SEMPRE_PARAM_AUTOPILOTO:
            raise ErroMetodologico(f"{g} exige aprovação humana mesmo no autopiloto")
    if args.forcar and (ator_tipo != "humano" or not args.motivo):
        raise ErroUso("--forcar só vale para humano e exige --motivo")
    anterior = _estado_portoes(eventos).get(g, {})
    if anterior.get("decisao") == "aprovado" and not criterios and not args.forcar:
        estado.resumo({"ok": True, "portao": g, "decisao": "aprovado", "ja_aprovado": True, "por": anterior.get("por")})
        return 0
    if g == "G1" and "tipo_revisao" in criterios and criterios["tipo_revisao"] not in esquema.TIPOS_REVISAO:
        raise ErroUso(f"tipo_revisao inválido: {criterios['tipo_revisao']}")
    if g == "G1" and criterios.get("variante") not in (None, "", *VARIANTES):
        raise ErroUso(f"variante inválida: {criterios['variante']} (use {', '.join(VARIANTES)})")

    bloqueios, avisos = checar_portao(raiz, est, g, eventos, criterios)
    automatico = ator_tipo != "humano"
    if automatico:
        # No autopiloto a falta de validação humana vira pendência; artefato ausente e limiar não atingido barram.
        duros = [b for b in bloqueios if b["tipo"] in TIPOS_BLOQUEIO_DUROS]
    else:
        duros = bloqueios
    if duros and not args.forcar:
        estado.resumo({"ok": False, "portao": g, "erro": "checagens_do_portao", "bloqueios": duros, "avisos": avisos,
                       "dica": "corrija, ou (humano) repita com --forcar --motivo \"...\""})
        return 2

    revertido = _reverter_nao_se_aplica(est, eventos, g)
    congelados = _congelar(raiz, est, g)
    if g == "G1":
        if criterios.get("pergunta"):
            est["projeto"]["pergunta"] = str(criterios["pergunta"])
        if criterios.get("tipo_revisao"):
            est["projeto"]["tipo_revisao"] = criterios["tipo_revisao"]
        if criterios.get("variante"):
            est["projeto"]["variante"] = criterios["variante"]
    estado.salvar_estado(raiz, est)
    criterios_log = dict(criterios)
    checagens = {"bloqueios": bloqueios, "forcado": bool(args.forcar and bloqueios), "congelados": congelados}
    if avisos:
        checagens["avisos"] = avisos
    if revertido:
        checagens["reverte_nao_se_aplica"] = True
    if bloqueios or congelados or avisos or revertido:
        criterios_log["checagens_script"] = checagens
    try:
        estado.registrar_portao(raiz, g, args.por, criterios=criterios_log, ator_tipo=ator_tipo, motivo=args.motivo)
    except estado.ErroProjeto as e:
        raise ErroMetodologico(str(e)) from e

    pendencia = None
    if automatico:
        est = estado.carregar_estado(raiz)
        ja = [p for p in estado.pendencias_abertas(est) if p.get("tipo") == "revisao_humana_portao" and p.get("portao") == g]
        if not ja:
            pendencia = estado.abrir_pendencia(
                raiz, "revisao_humana_portao", etapa,
                f"confirmar a aprovação automática do {g}"
                + (": " + "; ".join(b["detalhe"] for b in bloqueios) if bloqueios else ""), portao=g, ator_id="autopiloto")
        else:
            pendencia = ja[0]["id"]
    estado.resumo({"ok": True, "portao": g, "decisao": "aprovado", "etapa": etapa, "por": args.por,
                   "forcado": checagens["forcado"], "bloqueios": bloqueios, "avisos": avisos, "congelados": congelados,
                   "pendencia_aberta": pendencia, "proxima_acao": _comando_status(args.dir)})
    return 0


# ---------------------------------------------------------------------------
# pendencia
# ---------------------------------------------------------------------------
def cmd_pendencia(args):
    raiz = estado.exigir_projeto(args.dir)
    est = estado.carregar_estado(raiz)
    if args.acao_pendencia == "listar":
        lista = est.get("pendencias", []) if args.todas else estado.pendencias_abertas(est)
        if args.portao:
            lista = [p for p in lista if p.get("portao") == args.portao.upper()]
        estado.resumo({"n": len(lista), "abertas": len(estado.pendencias_abertas(est)), "pendencias": lista})
        return 0
    if args.acao_pendencia == "abrir":
        if args.etapa not in esquema.ETAPAS:
            raise ErroUso(f"etapa desconhecida: {args.etapa}")
        if args.portao and args.portao.upper() not in esquema.PORTOES:
            raise ErroUso(f"portão desconhecido: {args.portao}")
        portao = args.portao.upper() if args.portao else None
        for p in estado.pendencias_abertas(est):
            if (p.get("tipo"), p.get("etapa"), p.get("portao"), p.get("descricao")) == (args.tipo, args.etapa, portao, args.descricao):
                estado.resumo({"ok": True, "pendencia": p["id"], "ja_existia": True})
                return 0
        pid = estado.abrir_pendencia(raiz, args.tipo, args.etapa, args.descricao, portao=portao, n=args.n,
                                     arquivo=args.arquivo, ator_id=args.por or "script")
        estado.resumo({"ok": True, "pendencia": pid, "ja_existia": False})
        return 0
    # fechar
    if not args.motivo:
        raise ErroUso("fechar exige --motivo")
    ator_tipo = args.ator_tipo or "humano"
    if ator_tipo != "humano":
        raise ErroMetodologico("pendências registram validações humanas; só um humano (--ator-tipo humano) as fecha")
    try:
        fechou = estado.fechar_pendencia(raiz, args.id, args.motivo, ator_tipo=ator_tipo, ator_id=args.por)
    except estado.ErroProjeto as e:
        raise ErroUso(str(e)) from e
    est = estado.carregar_estado(raiz)
    restantes = estado.pendencias_abertas(est)
    regenerar = []
    if not restantes:
        eventos = estado.ler_log(raiz)
        if _ultimo_evento(eventos, "prisma_gerado"):
            regenerar.append(f"{RS} prisma")
        if _ultimo_evento(eventos, "relatorio_gerado") or _existe(raiz, esquema.ARQ_DECLARACAO_IA):
            regenerar.append(f"{RS} declaracao-ia")
    estado.resumo({"ok": True, "pendencia": args.id, "fechada": fechou, "ja_estava_fechada": not fechou,
                   "abertas_restantes": len(restantes), "regenerar": regenerar})
    return 0


# ---------------------------------------------------------------------------
# emenda
# ---------------------------------------------------------------------------
def cmd_emenda(args):
    """Registra a mudança de um artefato congelado (emenda ao protocolo) e atualiza o hash de referência."""
    raiz = estado.exigir_projeto(args.dir)
    est = estado.carregar_estado(raiz)
    rel = str(Path(args.arquivo))
    p = raiz / rel
    if not p.exists():
        raise ErroUso(f"{rel} não existe (caminho relativo à raiz do projeto)")
    info = est["artefatos"].get(rel)
    if not info or not info.get("congelado_em"):
        raise ErroUso(f"{rel} não está congelado; emendas só se aplicam a artefatos congelados")
    novo = estado.sha256_arquivo(p)
    if novo == info.get("sha256"):
        estado.resumo({"ok": True, "arquivo": rel, "mudou": False})
        return 0
    anterior = info.get("sha256")
    info.update({"sha256": novo, "versao": int(info.get("versao", 1)) + 1, "emendado_em": estado.agora()})
    etapa = esquema.PORTOES.get(info.get("portao"), "03_protocolo")
    estado.registrar_evento(raiz, "emenda_protocolo", etapa, args.ator_tipo or "humano", args.por,
                            dados={"arquivo": rel, "sha256_anterior": anterior, "versao": info["versao"]},
                            artefatos=[rel], motivo=args.motivo, estado=est)
    estado.resumo({"ok": True, "arquivo": rel, "mudou": True, "versao": info["versao"],
                   "lembrete": "descreva a emenda em 00-protocolo/emendas.md (item 24c do PRISMA)"})
    return 0


# ---------------------------------------------------------------------------
# Registro no dispatcher
# ---------------------------------------------------------------------------
def _executar(func):
    """Converte exceções conhecidas em códigos de saída do contrato (1 uso/dados, 2 metodológico)."""
    def envoltorio(args):
        try:
            return func(args)
        except ErroMetodologico as e:
            print(f"erro metodológico: {e}", file=sys.stderr)
            estado.resumo({"ok": False, "erro": "checagem_metodologica", "detalhe": str(e)})
            return 2
        except (ErroUso, estado.ErroProjeto) as e:
            print(f"erro: {e}", file=sys.stderr)
            estado.resumo({"ok": False, "erro": "uso", "detalhe": str(e)})
            return 1
    return envoltorio


def registrar(subparsers):
    p = subparsers.add_parser("init", help="cria (ou adota) um projeto de revisão e verifica o ambiente",
                              description="Cria pastas, rs_estado.json e rs_log.jsonl. Idempotente.")
    p.add_argument("--titulo", help="obrigatório para criar; num projeto existente pode ser omitido")
    p.add_argument("--tipo", choices=esquema.TIPOS_REVISAO + ["indefinido"])
    p.add_argument("--variante", choices=VARIANTES,
                   help="variante do tipo de origem (rapida: revisão rápida, Cochrane Rapid Reviews); grava projeto.variante")
    p.add_argument("--idioma", help="idioma dos produtos (padrão pt-BR)")
    p.add_argument("--autonomia", choices=esquema.MODOS_AUTONOMIA)
    p.add_argument("--triagem", choices=esquema.MODOS_TRIAGEM)
    p.add_argument("--parcial", choices=list(ETAPAS_PARCIAL), help="projeto só de triagem, meta-análise ou PRISMA")
    p.add_argument("--adotar", action="store_true", help="adota artefatos já existentes na pasta")
    p.add_argument("--sem-r", action="store_true", help="não checar R ao verificar o ambiente")
    p.set_defaults(func=_executar(cmd_init))

    p = subparsers.add_parser("status", help="onde estou: etapas, pendências, inconsistências e próxima ação (JSON)",
                              description="Recalcula o status das etapas a partir do log e dos artefatos.")
    p.set_defaults(func=_executar(cmd_status))

    ambiente.registrar(subparsers)

    p = subparsers.add_parser("portao", help="aprova, reprova ou dispensa (não se aplica) um portão (G1–G9)",
                              description="Registra a decisão de um portão com papel, critérios e motivo.")
    p.add_argument("portao", metavar="G#")
    grupo = p.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--aprovar", action="store_true")
    grupo.add_argument("--reprovar", action="store_true")
    grupo.add_argument("--nao-se-aplica", action="store_true",
                       help="dispensa o portão quando o tipo de revisão permite (esquema.PORTOES_OPCIONAIS_POR_TIPO); "
                            "exige --motivo")
    p.add_argument("--por", required=True, help=f"id de papel (ex.: {PAPEL_HUMANO}, autopiloto); nunca nome real")
    p.add_argument("--criterios", help="JSON com os valores dos critérios (ou caminho para .json)")
    p.add_argument("--motivo")
    p.add_argument("--ator-tipo", choices=esquema.TIPOS_ATOR, help="padrão: humano (ia_coordenador se --por autopiloto)")
    p.add_argument("--forcar", action="store_true", help="humano aprova apesar de bloqueios (exige --motivo)")
    p.set_defaults(func=_executar(cmd_portao))

    p = subparsers.add_parser("pendencia", help="lista, abre ou fecha pendências de validação humana")
    sub = p.add_subparsers(dest="acao_pendencia", metavar="<acao>", required=True)
    pl = sub.add_parser("listar", help="pendências abertas (ou --todas)")
    pl.add_argument("--todas", action="store_true")
    pl.add_argument("--portao")
    pl.set_defaults(func=_executar(cmd_pendencia))
    pa = sub.add_parser("abrir", help="registra uma pendência (usado no autopiloto)")
    pa.add_argument("--tipo", required=True)
    pa.add_argument("--etapa", required=True, choices=esquema.ETAPAS)
    pa.add_argument("--descricao", required=True)
    pa.add_argument("--portao")
    pa.add_argument("--n", type=int)
    pa.add_argument("--arquivo")
    pa.add_argument("--por", help="id de papel de quem abre (padrão: script)")
    pa.set_defaults(func=_executar(cmd_pendencia))
    pf = sub.add_parser("fechar", help="fecha uma pendência com motivo")
    pf.add_argument("id")
    pf.add_argument("--motivo", required=True)
    pf.add_argument("--por", default=PAPEL_HUMANO)
    pf.add_argument("--ator-tipo", choices=esquema.TIPOS_ATOR)
    pf.set_defaults(func=_executar(cmd_pendencia))

    p = subparsers.add_parser("emenda", help="registra emenda a um artefato congelado (protocolo, critérios)")
    p.add_argument("--arquivo", required=True, help="caminho relativo à raiz do projeto")
    p.add_argument("--motivo", required=True)
    p.add_argument("--por", default=PAPEL_HUMANO)
    p.add_argument("--ator-tipo", choices=esquema.TIPOS_ATOR)
    p.set_defaults(func=_executar(cmd_emenda))
