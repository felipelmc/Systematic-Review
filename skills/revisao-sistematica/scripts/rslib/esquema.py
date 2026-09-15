"""Contratos de dados da skill revisao-sistematica (colunas, layout, vocabulários).

Fonte única de verdade para nomes de colunas, pastas do projeto e enums. Todo
script importa daqui; nenhum script escreve nomes de coluna "soltos". Mudanças
aqui exigem atualizar dev/revisao-sistematica/CONTRATOS.md e os testes.
"""

VERSAO_ESQUEMA = "1"

# ---------------------------------------------------------------------------
# Layout do projeto criado por `rs.py init`
# ---------------------------------------------------------------------------
PASTAS_PROJETO = [
    "00-protocolo",
    "01-busca/brutos",
    "01-busca/strings",
    "01-busca/bola_de_neve",
    "02-triagem/lotes",
    "02-triagem/prompts",
    "02-triagem/validacao",
    "02-triagem/api",
    "03-textos/pdfs",
    "04-qualidade",
    "05-decomposicao",
    "05-decomposicao/efeitos",
    "06-analise/figuras",
    "06-analise/tabelas",
    "07-relatorio",
    "dados",
]
ARQ_ESTADO = "rs_estado.json"
ARQ_LOG = "rs_log.jsonl"
ARQ_REGISTROS = "dados/registros.csv"
ARQ_UNICOS = "dados/registros_unicos.csv"
ARQ_DECISOES = "dados/decisoes.jsonl"
ARQ_DEDUP_PARES = "01-busca/dedup_pares.csv"
ARQ_FILTRO_FORMAL = "02-triagem/filtro_formal.csv"
ARQ_TRIAGEM_TA_FINAL = "02-triagem/triagem_ta_final.csv"
ARQ_ELEGIBILIDADE_TC_FINAL = "03-textos/elegibilidade_tc_final.csv"
ARQ_PARA_BAIXAR = "03-textos/para_baixar.csv"
ARQ_RELATORIO_PDFS = "03-textos/relatorio_pdfs.csv"
ARQ_VERIFICACAO_CONTEUDO = "03-textos/verificacao_conteudo.csv"
ARQ_INVENTARIO_TEXTOS = "03-textos/inventario_textos.csv"
ARQ_EFEITOS_EXTRAIDOS = "05-decomposicao/efeitos_extraidos.csv"
ARQ_INCLUIDOS = "07-relatorio/incluidos.csv"
DIR_BRUTOS = "01-busca/brutos"
ARQ_FILTRO_FORMAL_CONTAGENS = "02-triagem/filtro_formal_contagens.json"
ARQ_LIGACAO_RELATOS = "03-textos/ligacao_relatos.csv"
ARQ_VERIFICACAO_EFEITOS = "05-decomposicao/verificacao_efeitos.csv"
ARQ_EFEITOS_CALCULADOS = "06-analise/efeitos.csv"
ARQ_META_RESUMO = "06-analise/meta_resumo.json"
ARQ_SWIM_RESUMO = "06-analise/swim_resumo.json"
ARQ_CERTEZA = "06-analise/certeza.csv"
ARQ_CAIXA = "06-analise/caixa_ferramentas.csv"
ARQ_PRISMA_CONTAGENS = "07-relatorio/prisma_contagens.json"
ARQ_DECLARACAO_IA = "07-relatorio/declaracao_uso_ia.md"
ARQ_BIB = "07-relatorio/references.bib"
REVISORES_LEDGER = ["A", "B", "arbitro", "regra"]  # além de ids humanos (humano_1, revisor_humano_1...)


def id_estudo_de(id_rs):
    """Convenção única: RS0007 -> ES0007."""
    s = str(id_rs or "").strip()
    return "ES" + s[2:] if s.startswith("RS") else s

# ---------------------------------------------------------------------------
# dados/registros.csv — uma linha por registro importado (imutável após importar)
# ---------------------------------------------------------------------------
COLUNAS_REGISTROS = [
    "id_registro",            # "<busca_id>-<linha:05d>", ex. B03-00017
    "busca_id",               # B01, B02... ou SN1 (bola de neve), CZ1 (cinzenta), MN1 (manual)
    "fonte",                  # wos|scopus|openalex|scielo|pop|zotero|ris|capes|bdtd|generico|...
    "metodo_identificacao",   # base|citacao|cinzenta|manual
    "arquivo_origem",
    "linha_origem",
    "id_fonte",               # UT do WoS, EID do Scopus, W do OpenAlex, PID SciELO, id CAPES
    "doi",                    # minúsculo, sem prefixo https://doi.org/
    "titulo",
    "titulo_alt",
    "autores",                # canônico "Sobrenome, Nomes | Sobrenome, Nomes"
    "primeiro_autor_sobrenome",
    "n_autores",
    "ano",
    "tipo_publicacao_orig",
    "tipo_publicacao",        # ver TIPOS_PUBLICACAO
    "idioma",                 # ISO 639-1 (pt, en, es...) ou vazio
    "veiculo",
    "volume",
    "numero",
    "paginas",
    "resumo",
    "resumo_truncado",        # 0|1
    "palavras_chave",         # separadas por "; "
    "pais_afiliacao",
    "instituicao",
    "url",
    "citado_por",
    "estrutura",              # bloco/estratégia de busca (ex.: PICOC, CMMO) ou vazio
    "importado_em",           # ISO 8601
]

TIPOS_PUBLICACAO = [
    "artigo", "capitulo", "livro", "tese", "dissertacao", "evento",
    "preprint", "relatorio", "revisao", "editorial", "errata", "outro",
]

# ---------------------------------------------------------------------------
# dados/registros_unicos.csv — uma linha por cluster após dedup
# ---------------------------------------------------------------------------
COLUNAS_UNICOS = [
    "id_rs",                  # RS0001... atribuído de forma append-only
    "id_estudo",              # "ES" + número do id_rs do relato principal (RS0007 -> ES0007); relatos ligados compartilham
    "chave",                  # citekey (chave.py), estável após gerada
    "ids_registro",           # "B01-00001|B03-00017"
    "fontes",                 # "wos|scopus"
    "n_fontes",
    "tipo_duplicata",         # unico|exato|fuzzy|versao
    "flags",                  # "sem_resumo|preprint|retratado|autores_ambiguos"
] + [c for c in COLUNAS_REGISTROS if c not in {
    "id_registro", "busca_id", "fonte", "arquivo_origem", "linha_origem", "importado_em"}]

PRIORIDADE_FONTES = ["openalex", "scopus", "wos", "scielo", "capes", "bdtd", "zotero", "ris", "pop", "generico"]

# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------
COLUNAS_DEDUP_PARES = [
    "id_a", "id_b", "regra", "score", "ano_a", "ano_b", "sobrenome_a", "sobrenome_b",
    "doi_a", "doi_b", "decisao", "decidido_por", "motivo",
]
REGRAS_DEDUP = ["R1_doi", "R2_id_fonte", "R3_titulo_exato", "R4_fuzzy_auto", "R5_candidato", "versao"]
DECISOES_DEDUP = ["auto", "candidato", "confirmado", "rejeitado", "ligado"]  # "ligado" acrescentado na v1.3 (DECISAO_LIGADO)
PREFIXOS_PREPRINT = ["10.31235", "10.2139", "10.31219", "10.48550", "10.1101", "10.21203", "10.20944"]

# ---------------------------------------------------------------------------
# Funil formal (etiqueta por padrão; exclusão só com previsão no protocolo)
# ---------------------------------------------------------------------------
COLUNAS_FILTRO_FORMAL = ["id_rs", "filtro", "resultado", "detalhe"]  # resultado: passa|exclui|etiqueta|sem_dado

# ---------------------------------------------------------------------------
# Triagem e decisões
# ---------------------------------------------------------------------------
ETAPAS_DECISAO = ["ta", "tc", "qualidade", "dedup"]
DECISOES = ["incluir", "excluir", "incerto"]
TIPOS_ATOR = ["humano", "ia_coordenador", "ia_subagente", "ia_api", "script", "regra"]
CAMPOS_DECISAO = [
    "id_rs", "etapa", "rodada", "revisor", "tipo_ator", "modelo", "prompt_sha",
    "decisao", "criterio_falhou", "justificativa", "trecho", "lote", "ts",
    "override_de", "motivo_override",
]
COLUNAS_TRIAGEM_FINAL = [
    "id_rs", "decisao_final", "decidido_por", "criterio_falhou", "divergente", "revisado_humano",
]
COLUNAS_ELEGIBILIDADE_FINAL = ["id_rs", "chave", "decisao", "criterio_falhou", "evidencia", "pagina"]

# ---------------------------------------------------------------------------
# Handoffs com as skills irmãs (colunas exatas)
# ---------------------------------------------------------------------------
COLUNAS_PARA_BAIXAR = ["chave", "titulo", "autores", "ano", "doi", "id_rs"]
COLUNAS_RELATORIO_PDFS = ["chave", "titulo", "autores", "ano", "doi", "status", "fonte", "url", "versao", "motivo", "arquivo"]
STATUS_PDF_OK = {"ok", "ja_existia", "scihub_ok"}
COLUNAS_VERIFICACAO_CONTEUDO = ["chave", "titulo", "veredito", "cobertura_titulo", "autor_encontrado"]
COLUNAS_INVENTARIO_TEXTOS = ["chave", "id_rs", "arquivo", "existe", "n_paginas", "tem_texto", "n_chars", "veredito_conteudo",
                             "recuperado"]  # recuperado: 1 se existe e o conteúdo confere (ou foi conferido à mão); 0 senão
COLUNAS_CODEBOOK = ["dimensao", "variavel", "descricao", "prompt", "tipo", "aplicavel_se"]
COLUNAS_INCLUIDOS = ["chave", "titulo", "autores", "ano", "doi", "tipo_publicacao", "nome_publicacao"]

# ---------------------------------------------------------------------------
# Efeitos (várias linhas por estudo)
# ---------------------------------------------------------------------------
COLUNAS_EFEITOS_EXTRAIDOS = [
    "id_efeito", "ficha_id", "chave", "id_estudo", "desenho", "estimando",  # estimando: ATE|ITT|LATE|ATT|RDD_local|associacao|outro
    "outcome", "construto_outcome", "direcao_desejada",                      # direcao_desejada: aumentar|reduzir
    "modelo", "modelo_principal", "subgrupo",
    "tipo_estatistica",  # md_sd|t|f1|beta_sd|or|r|p_n|g|d|parcial_r|mann_whitney|mediana_iqr|dif_prop|rr
    "m1", "sd1", "n1", "m2", "sd2", "n2", "t", "df", "f", "beta", "se", "sdy",
    "or_", "ci_lo", "ci_hi", "r", "p", "n_total", "cluster", "icc",
    "evidencia", "pagina", "verificado_humano",
]
COLUNAS_EFEITOS_CALCULADOS = COLUNAS_EFEITOS_EXTRAIDOS + ["yi", "vi", "sei", "formula_id", "aproximado", "sinal_alinhado", "aviso"]

# ---------------------------------------------------------------------------
# Log de eventos (rs_log.jsonl) e estado
# ---------------------------------------------------------------------------
EVENTOS = [
    "projeto_criado", "modo_definido", "ambiente_verificado", "artefato_versionado",
    "emenda_protocolo", "busca_registrada", "importacao", "dedup_executado", "dedup_revisado",
    "filtro_formal", "lote_preparado", "lote_mesclado", "lote_rejeitado", "decisao_override",
    "triagem_consolidada", "validacao_calculada", "portao", "pendencia_aberta", "pendencia_fechada",
    "textos_atualizados", "ligacao_relatos", "extracao_consolidada", "efeitos_verificados",
    "analise_executada", "caixa_gerada", "prisma_gerado", "relatorio_gerado", "erro",
    # acréscimos (v1.1)
    "busca_substituida", "retratacoes_verificadas", "contato_autores", "etapa_nao_aplicavel",
    # acréscimos (v1.2)
    "rob_consolidado", "fila_gerada",
]
ETAPAS = [
    "00_configuracao", "01_pergunta", "02_teoria_framework", "03_protocolo", "04_busca",
    "05_organizacao", "06_triagem_ta", "07_textos_elegibilidade", "08_piloto_extracao",
    "09_extracao_rob", "10_sintese", "11_relato",
]
STATUS_ETAPA = ["pendente", "em_andamento", "concluida", "ignorada"]
PORTOES = {
    "G1": "01_pergunta", "G2": "03_protocolo", "G3": "04_busca", "G4": "06_triagem_ta",
    "G5": "07_textos_elegibilidade", "G6": "08_piloto_extracao", "G7": "09_extracao_rob",
    "G8": "10_sintese", "G9": "11_relato",
}
PORTOES_SEMPRE_PARAM_AUTOPILOTO = {"G1", "G2"}  # autopiloto para só nestes; os demais viram pendências
MODOS_AUTONOMIA = ["checkpoints", "autopiloto"]
MODOS_TRIAGEM = ["subagentes", "api"]
TIPOS_REVISAO = [
    "efetividade_meta", "efetividade_swim", "oqf_mista_sequencial", "escopo", "mapa_evidencias",
    "qualitativa", "realista", "metodos_mistos", "rapida", "guarda_chuva",
]
MARCA_RASCUNHO = "RASCUNHO NÃO VALIDADO"


# ---------------------------------------------------------------------------
# Acréscimos de contrato (v1.1) entre módulos
# ---------------------------------------------------------------------------
# validacao_calculada.dados.finalidade: separa calibração/desenvolvimento da validação que decide o G4.
FINALIDADES_VALIDACAO = ["calibracao", "desenvolvimento", "validacao", "elusao", "estabilidade"]
# Rodada de T/A que vale para o PRISMA e para o G4 (gravada por `triagem consolidar` em versoes_ativas).
VERSAO_ATIVA_RODADA_TA = "rodada_ta"
# Decisões finais de elegibilidade em texto completo (aguardando = "awaiting classification", Cochrane 4.4.5).
DECISAO_TC_AGUARDANDO = "aguardando"
DECISOES_TC_FINAL = ["incluir", "excluir", DECISAO_TC_AGUARDANDO]
# estado["buscas"][i]["ativa"]: False quando a busca foi substituída (`importar --substituir`); dedup e prisma ignoram.
CAMPO_BUSCA_ATIVA = "ativa"
# etapas que um tipo de revisão dispensa (status as trata como ignoradas); o G correspondente não é exigido.
ETAPAS_NAO_APLICAVEIS_POR_TIPO = {
    "escopo": [],  # escopo extrai (charting); RoB e certeza dispensados via PORTOES_OPCIONAIS_POR_TIPO
    "mapa_evidencias": [],
}
PORTOES_OPCIONAIS_POR_TIPO = {
    # tipo -> portões que podem ser marcados como "não se aplica" (com motivo) sem quebrar a ordem
    "escopo": ["G7", "G8"],
    "mapa_evidencias": ["G6", "G7", "G8"],
    "realista": ["G4"],
}
# projeto.variante (`init --variante`, critério `variante` do G1): variante de um tipo de origem; não muda portões.
VARIANTES_REVISAO = ["rapida"]


# ---------------------------------------------------------------------------
# Acréscimos de contrato (v1.1): artefatos e flags promovidos dos módulos
# (mesmos valores de antes; os módulos importam daqui). Ver dev/revisao-sistematica/CONTRATOS.md, "Contratos v1.1".
# ---------------------------------------------------------------------------
# Busca e deduplicação
FLAG_BUSCA_INATIVA = "busca_inativa"   # registros_unicos.flags: cluster só com registros de buscas substituídas
FLAG_RETRATADO = "retratado"           # registros_unicos.flags e registros_flags.flag (is_retracted da fonte)
ARQ_REGISTROS_FLAGS = "dados/registros_flags.csv"   # append-only, sem duplicata (id_registro, flag)
COLUNAS_REGISTROS_FLAGS = ["id_registro", "flag", "origem", "registrado_em"]
ARQ_RECALL_ANCORAS = "01-busca/recall_ancoras.json"  # `filtrar --ancoras`: combinado, por_busca, por_base
DIR_STRINGS = "01-busca/strings"

# Textos completos
ARQ_CONFERENCIA_PDFS = "03-textos/conferencia_pdfs.csv"   # conferência humana que prevalece em inventario.recuperado
COLUNAS_CONFERENCIA_PDFS = ["chave", "recuperado", "motivo"]
ARQ_RETRATACOES = "03-textos/retratacoes.csv"             # `textos retratacoes`
COLUNAS_RETRATACOES = ["chave", "id_rs", "doi", "openalex_is_retracted", "crossref_avisos", "retratado", "status",
                       "verificado_em"]
ARQ_CONTATO_AUTORES = "03-textos/contato_autores.csv"     # `textos contato-autores --registrar`
COLUNAS_CONTATO_AUTORES = ["chave", "autor_contatado", "data", "pedido", "resposta", "dados_recebidos"]

# Validação (triagem e filtro de dicionário)
DIR_VALIDACAO = "02-triagem/validacao"   # validar: <DIR_VALIDACAO>/<rodada>/; filtrar: elusao_<versao>_*
SUFIXO_PLANILHA_CEGA = "_cega.xlsx"
SUFIXO_DESENHO = "_desenho.json"
SUFIXO_METRICAS = "_metricas.json"
ARQ_DESENHO_ESTABILIDADE = "estabilidade_desenho.json"   # dentro de <DIR_VALIDACAO>/<rodada>/

# Relato (PRISMA; ARQ_PRISMA_CONTAGENS, ARQ_DECLARACAO_IA e ARQ_BIB ficam acima)
ARQ_PRISMA_MERMAID = "07-relatorio/prisma.mermaid"
ARQ_PRISMA_SVG = "07-relatorio/prisma.svg"
ARQ_PRISMA_PNG = "07-relatorio/prisma.png"
ARQ_CHECKLIST_PRISMA = "07-relatorio/checklist_prisma.csv"

# Tipos de pendência abertos pelos comandos (estado.pendencias[].tipo)
PENDENCIA_CONFERENCIA_ELEGIBILIDADE_TC = "conferencia_elegibilidade_tc"
PENDENCIA_RETRATACAO_TEXTO = "retratacao_texto"          # aberta em qualquer modo de autonomia
PENDENCIA_VERIFICACAO_HUMANA_EFEITOS = "verificacao_humana_efeitos"
PENDENCIA_CERTEZA_CAIXA = "certeza_caixa"
PENDENCIA_CALIBRACAO_REPROVADA = "calibracao_reprovada"
PENDENCIA_VALIDACAO_TRIAGEM_REPROVADA = "validacao_triagem_reprovada"

# Ledger de decisões (assets/schemas/decisao.schema.json aceita só incluir|excluir|incerto):
# `incerto` de tipo_ator humano na etapa `tc` é lido como `aguardando` (DECISOES_TC_FINAL).
DECISAO_LEDGER_AGUARDANDO_TC = "incerto"

# Extração de efeitos: colunas extras (depois de COLUNAS_EFEITOS_EXTRAIDOS) lidas por scripts/R/efeitos.R
COLUNAS_EFEITOS_EXTRAS_NUMERICAS = ["q1_1", "q3_1", "q1_2", "q3_2", "g", "d", "m_preditores"]


# ---------------------------------------------------------------------------
# Acréscimos de contrato (v1.2)
# ---------------------------------------------------------------------------
# Busca com resultados não baixados por inteiro (ex.: --max-paginas): não serve para o PRISMA sem justificativa.
CAMPO_BUSCA_TRUNCADA = "truncada"
# Risco de viés consolidado (rs.py qualidade consolidar). Julgamento por domínio e geral por chave × outcome.
DIR_QUALIDADE = "04-qualidade"
PADRAO_ROB_CONSENSO = "04-qualidade/rob_{ferramenta}_consenso.csv"
COLUNAS_ROB_CONSENSO = [
    "chave", "id_estudo", "construto_outcome", "ferramenta", "dominio",
    "julgamento_a", "julgamento_b", "julgamento_consenso", "justificativa", "trecho", "pagina", "resolvido_por",
]
ARQ_ROB_GERAL = "04-qualidade/rob_geral.csv"
COLUNAS_ROB_GERAL = ["chave", "id_estudo", "construto_outcome", "ferramenta", "rob_geral", "validado_humano"]
# Tipos de revisão que dispensam risco de viés no G7 (sem avaliação formal de qualidade).
TIPOS_SEM_ROB = ["escopo", "mapa_evidencias"]
# Fila humana do texto completo (rs.py triagem fila --etapa tc).
ARQ_FILA_HUMANA_TC = "03-textos/fila_humana_tc.csv"
# Papel humano padrão em todos os comandos que registram decisão humana.
PAPEL_HUMANO_PADRAO = "revisor_humano_1"
# Onde o usuário encontra as regras citadas em mensagens dos scripts (nunca o plano interno).
REF_REGRAS = "references/ (ver SKILL.md) e Apêndice D da base de conhecimento"


# ---------------------------------------------------------------------------
# Acréscimos de contrato (v1.3): constantes promovidas dos módulos (mesmos valores; os módulos
# mantêm os nomes antigos como aliases). Ver dev/revisao-sistematica/CONTRATOS.md, "Contratos v1.3".
# ---------------------------------------------------------------------------
# Dedup: par de versão (preprint/working paper <-> publicado) ligado por id_estudo, nunca fundido.
DECISAO_LIGADO = "ligado"   # também em DECISOES_DEDUP
MOTIVO_VERSAO_LIGADA = "preprint_publicado"
MARCA_RESOLVIDO_TRANSITIVAMENTE = "resolvido_transitivamente"  # sufixo em dedup_pares.motivo (candidato já resolvido)

# Triagem: fila humana do texto completo (ARQ_FILA_HUMANA_TC) e codebook de elegibilidade do protocolo.
COLUNAS_FILA_HUMANA_TC = [
    "id_rs", "chave", "proposta", "criterio_proposto", "evidencia", "pagina",
    "decisao_humana", "criterio_humano", "motivo",
]
ARQ_CODEBOOK_ELEGIBILIDADE = "00-protocolo/codebook_elegibilidade.csv"

# Portões e pendências (projeto.py, qualidade.py).
PENDENCIA_PRESS = "revisao_press"
PENDENCIA_CONCORDANCIA = "concordancia_extracao"
PENDENCIA_CONSENSO_ROB = "consenso_rob"
PADRAO_CONCORDANCIA_ROB = "04-qualidade/rob_{ferramenta}_concordancia.csv"
PADRAO_CONCORDANCIA = PADRAO_CONCORDANCIA_ROB   # nome usado em qualidade.py
TIPOS_SEM_CERTEZA = ["escopo", "mapa_evidencias", "realista"]
MIN_INCLUIDOS_LIMIAR_ALCANCAVEL = 36   # recall >= 0,95 com LI >= 0,90 exige >= 36 incluídos humanos

# Variante rápida: atalho da triagem no G4 (critério do G1 e campos de validacao_calculada.dados).
CRITERIO_ATALHO_RAPIDA = "atalho_rapida"
FRACAO_MINIMA_DUPLA_RAPIDA = 0.20
CAMPOS_ATALHO_RAPIDA = [
    "atalho_rapida",               # true só com projeto.variante = rapida e desenho (ou --atalho-rapida) do atalho
    "fracao_dupla_humana",         # n_dupla_humana / n_populacao
    "n_dupla_humana",              # registros da amostra com >= 2 códigos humanos
    "n_populacao",                 # registros ativos da rodada (populacao_rodada do desenho)
    "kappa_humanos",               # κ binário da dupla humana
    "segunda_leitura_excluidos",   # true se todos os excluídos pela IA foram relidos por humano
    "n_excluidos_ia",              # excluídos pela IA (só IA, sem overrides) na rodada, fora inativos e funil
    "n_excluidos_relidos",         # desses, quantos têm leitura humana (segunda leitura ou amostra)
]
ARQ_SEGUNDA_LEITURA = "segunda_leitura.json"   # dentro de <DIR_VALIDACAO>/<rodada>/ (`validar segunda-leitura`)
TIPO_SEGUNDA_LEITURA = "segunda_leitura"       # validacao_calculada.dados.tipo (finalidade elusao)

# Síntese e caixa de ferramentas.
COLUNAS_EFEITOS_BINARIOS = ["p0", "p1", "efeito_pp", "se_pp"]   # extras de desfecho binário (dif_prop, rr)
DIMENSAO_PAINEL = "efeito_painel"
REGRA_VERSAO_CAIXA = "caixa-3"

# Relato: relatorio_gerado.dados.ultimo_seq (último seq do log coberto pela declaração de IA).
CAMPO_ULTIMO_SEQ_RELATORIO = "ultimo_seq"
