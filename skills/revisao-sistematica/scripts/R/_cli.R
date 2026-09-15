# _cli.R — utilitários comuns dos scripts R da skill revisao-sistematica.
#
# USO (dentro de outro script R desta pasta)
#     source(file.path(.rs_dir_script(), "_cli.R"), encoding = "UTF-8")
#     main <- function(args) {
#       entrada <- cli_arg(args, "in", obrigatorio = TRUE)
#       list(codigo = SAIDA_OK, resumo = list(ok = TRUE, entrada = entrada))
#     }
#     if (sys.nframe() == 0L) quit(status = cli_executar(function() main(cli_args())), save = "no")
#
# Por que existe
# - Sem optparse: o pacote não vem com o R base e o contrato pede `--chave=valor`.
#   Aceitamos também `--chave valor` e flags soltas (`--flag` = TRUE), por tolerância.
# - Um único formato de saída: a ÚLTIMA linha do stdout é um JSON (jsonlite) com
#   contagens e caminhos, igual aos comandos Python (rs.py). Mensagens de progresso e
#   avisos vão para o stderr (message) para nunca atrapalhar quem lê o JSON; só a
#   ressalva obrigatória dos testes combinados é impressa no stdout, antes do JSON.
# - Códigos de saída alinhados ao dispatcher Python: 0 ok; 1 erro de uso/dados;
#   2 checagem metodológica falhou; 3 dependência ausente.
# - As colunas de efeitos espelham `rslib/esquema.py` (COLUNAS_EFEITOS_EXTRAIDOS e
#   COLUNAS_EFEITOS_CALCULADOS). O teste tests/test_r_smoke.py compara as duas listas
#   para impedir que divirjam.
# - Este arquivo não grava rs_log.jsonl nem rs_estado.json: só o Python (rslib/estado.py)
#   escreve o estado do projeto. Quem chama os scripts R registra o evento.

COLUNAS_EFEITOS_EXTRAIDOS <- c(
  "id_efeito", "ficha_id", "chave", "id_estudo", "desenho", "estimando",
  "outcome", "construto_outcome", "direcao_desejada",
  "modelo", "modelo_principal", "subgrupo",
  "tipo_estatistica",
  "m1", "sd1", "n1", "m2", "sd2", "n2", "t", "df", "f", "beta", "se", "sdy",
  "or_", "ci_lo", "ci_hi", "r", "p", "n_total", "cluster", "icc",
  "evidencia", "pagina", "verificado_humano"
)
COLUNAS_EFEITOS_CALCULADOS <- c(
  COLUNAS_EFEITOS_EXTRAIDOS,
  "yi", "vi", "sei", "formula_id", "aproximado", "sinal_alinhado", "aviso"
)

SAIDA_OK <- 0L
SAIDA_ERRO_DADOS <- 1L
SAIDA_CHECAGEM <- 2L
SAIDA_DEPENDENCIA <- 3L

# ---------------------------------------------------------------------------
# Argumentos
# ---------------------------------------------------------------------------

#' Converte o vetor de argumentos em lista nomeada.
#'
#' `--k-min=3` vira `args$k_min == "3"`; hífens viram sublinhados para que o
#' acesso em R seja natural. Valores ficam como texto: cada script converte.
cli_args <- function(argv = commandArgs(trailingOnly = TRUE)) {
  saida <- list()
  posicionais <- character(0)
  i <- 1L
  while (i <= length(argv)) {
    a <- argv[[i]]
    if (startsWith(a, "--")) {
      corpo <- substring(a, 3L)
      if (grepl("=", corpo, fixed = TRUE)) {
        nome <- sub("=.*$", "", corpo)
        valor <- sub("^[^=]*=", "", corpo)
      } else if (i < length(argv) && !startsWith(argv[[i + 1L]], "--")) {
        nome <- corpo
        valor <- argv[[i + 1L]]
        i <- i + 1L
      } else {
        nome <- corpo
        valor <- TRUE
      }
      saida[[gsub("-", "_", nome, fixed = TRUE)]] <- valor
    } else {
      posicionais <- c(posicionais, a)
    }
    i <- i + 1L
  }
  saida[[".posicionais"]] <- posicionais
  saida
}

cli_arg <- function(args, nome, padrao = NULL, obrigatorio = FALSE) {
  valor <- args[[gsub("-", "_", nome, fixed = TRUE)]]
  if (is.null(valor) || (is.character(valor) && !nzchar(valor) && obrigatorio)) {
    if (obrigatorio) cli_falhar(sprintf("argumento obrigatório ausente: --%s=...", nome), SAIDA_ERRO_DADOS)
    return(padrao)
  }
  valor
}

cli_num <- function(args, nome, padrao = NULL) {
  valor <- cli_arg(args, nome, NULL)
  if (is.null(valor)) return(padrao)
  n <- como_num(valor)
  if (is.na(n)) cli_falhar(sprintf("--%s precisa ser numérico (recebido: %s)", nome, valor), SAIDA_ERRO_DADOS)
  n
}

cli_lista <- function(args, nome) {
  valor <- cli_arg(args, nome, NULL)
  if (is.null(valor) || isTRUE(valor)) return(character(0))
  partes <- trimws(strsplit(as.character(valor), ",", fixed = TRUE)[[1]])
  partes[nzchar(partes)]
}

cli_bool <- function(args, nome, padrao = FALSE) {
  valor <- cli_arg(args, nome, NULL)
  if (is.null(valor)) return(padrao)
  if (isTRUE(valor)) return(TRUE)
  eh_verdadeiro(valor)
}

# ---------------------------------------------------------------------------
# Saída, erros e dependências
# ---------------------------------------------------------------------------

#' Erro controlado: carrega o código de saída e um resumo parcial.
cli_falhar <- function(mensagem, codigo = SAIDA_ERRO_DADOS, resumo = list()) {
  condicao <- structure(
    class = c("rs_saida", "error", "condition"),
    list(message = mensagem, call = NULL, codigo = as.integer(codigo), resumo = resumo)
  )
  stop(condicao)
}

#' Serializa em JSON numa linha. `digits = NA` preserva a precisão numérica.
cli_json <- function(dados) {
  as.character(jsonlite::toJSON(dados, auto_unbox = TRUE, null = "null", na = "null",
                                digits = NA, force = TRUE))
}

#' Imprime o resumo JSON como última linha do stdout (convenção de todos os comandos).
cli_resumo <- function(dados) {
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    cat('{"ok": false, "erro": "pacote R jsonlite ausente"}\n')
    return(invisible(NULL))
  }
  cat(cli_json(dados), "\n", sep = "")
  invisible(NULL)
}

#' Falha com código 3 se faltar algum pacote, com a instrução de instalação.
exigir_pacotes <- function(pacotes) {
  faltando <- pacotes[!vapply(pacotes, requireNamespace, logical(1), quietly = TRUE)]
  if (length(faltando)) {
    cli_falhar(
      sprintf("pacote(s) R ausente(s): %s. Instale com install.packages(c(%s)).",
              paste(faltando, collapse = ", "),
              paste(sprintf('"%s"', faltando), collapse = ", ")),
      SAIDA_DEPENDENCIA,
      resumo = list(pacotes_ausentes = as.list(faltando))
    )
  }
  invisible(TRUE)
}

#' Roda `main` e converte erros em código de saída + resumo JSON.
#'
#' Uso típico no fim de cada script, só quando executado via Rscript (não ao ser
#' carregado com source() nos testes):
#'     if (sys.nframe() == 0L) quit(status = cli_executar(function() main(cli_args())), save = "no")
#'
#' `main` deve devolver list(codigo = <int>, resumo = <list>). Erros controlados
#' (cli_falhar) preservam seu código; erros inesperados viram código 1.
cli_executar <- function(main) {
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    message("pacote R jsonlite ausente: install.packages(\"jsonlite\")")
    cat('{"ok": false, "erro": "pacote R jsonlite ausente"}\n')
    return(SAIDA_DEPENDENCIA)
  }
  resultado <- tryCatch(
    main(),
    rs_saida = function(e) {
      message("erro: ", conditionMessage(e))
      list(codigo = e$codigo, resumo = c(list(ok = FALSE, erro = conditionMessage(e)), e$resumo))
    },
    error = function(e) {
      message("erro inesperado: ", conditionMessage(e))
      list(codigo = SAIDA_ERRO_DADOS, resumo = list(ok = FALSE, erro = conditionMessage(e)))
    }
  )
  cli_resumo(resultado$resumo)
  as.integer(resultado$codigo)
}

# ---------------------------------------------------------------------------
# Valores e textos
# ---------------------------------------------------------------------------

#' TRUE para vazio, NA, "NA", "nan", "null" (planilhas e CSVs chegam assim).
vazio <- function(x) {
  if (is.null(x)) return(TRUE)
  s <- trimws(as.character(x))
  is.na(x) | !nzchar(s) | tolower(s) %in% c("na", "nan", "null", "none", "n/a")
}

#' Texto → número. Aceita vírgula decimal ("0,45") quando não há ponto, pois
#' extrações manuais em PT-BR costumam vir assim. Vazio e lixo viram NA.
como_num <- function(x) {
  if (is.numeric(x)) return(as.numeric(x))
  s <- trimws(as.character(x))
  s[vazio(s)] <- NA_character_
  virgula <- !is.na(s) & grepl(",", s, fixed = TRUE) & !grepl(".", s, fixed = TRUE)
  s[virgula] <- sub(",", ".", s[virgula], fixed = TRUE)
  s <- sub("^\\+", "", s)
  suppressWarnings(as.numeric(s))
}

eh_verdadeiro <- function(x) {
  s <- tolower(trimws(as.character(x)))
  !is.na(s) & s %in% c("1", "sim", "s", "true", "t", "verdadeiro", "yes", "y", "x")
}

#' Minúsculas sem acentos, para comparar rótulos livres (desenho, risco de viés).
#'
#' Não usa iconv(..., "ASCII//TRANSLIT"): no macOS ele produz "an'alise" em vez
#' de "analise", o que quebraria os casamentos por regex. Acentos em escapes
#' \u para o arquivo funcionar mesmo em locale não UTF-8.
ACENTOS_DE <- paste0(
  "áàâãäéèêëíìîï",
  "óòôõöúùûüçñ",
  "ÁÀÂÃÄÉÈÊËÍÌÎÏ",
  "ÓÒÔÕÖÚÙÛÜÇÑ"
)
ACENTOS_PARA <- "aaaaaeeeeiiiiooooouuuucnaaaaaeeeeiiiiooooouuuucn"

ascii_minusculo <- function(x) {
  s <- as.character(x)
  s[is.na(s)] <- ""
  s <- chartr(ACENTOS_DE, ACENTOS_PARA, enc2utf8(s))
  tolower(iconv(s, from = "UTF-8", to = "ASCII", sub = ""))
}

#' Nome de arquivo seguro a partir de um rótulo de grupo.
slug <- function(x) {
  s <- gsub("[^a-z0-9]+", "_", ascii_minusculo(x))
  s <- gsub("^_+|_+$", "", s)
  s[!nzchar(s)] <- "grupo"
  substr(s, 1L, 60L)
}

nulo_se_na <- function(x) {
  if (is.null(x) || length(x) == 0L || (length(x) == 1L && (is.na(x) || !is.finite(x)))) NULL else x
}

# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

#' Lê CSV UTF-8 (com ou sem BOM) mantendo tudo como texto.
#'
#' Ler como texto evita que o R converta "001" em 1 ou "T" em TRUE; cada script
#' converte explicitamente só as colunas numéricas.
ler_csv_texto <- function(caminho) {
  if (!file.exists(caminho)) cli_falhar(sprintf("arquivo não encontrado: %s", caminho), SAIDA_ERRO_DADOS)
  df <- utils::read.csv(caminho, colClasses = "character", na.strings = character(0),
                        check.names = FALSE, fileEncoding = "UTF-8-BOM", stringsAsFactors = FALSE)
  names(df) <- trimws(names(df))
  df
}

#' Garante as colunas esperadas (cria vazias) e devolve quais faltavam.
completar_colunas <- function(df, colunas) {
  faltando <- setdiff(colunas, names(df))
  for (col in faltando) df[[col]] <- rep("", nrow(df))
  attr(df, "colunas_ausentes") <- faltando
  df
}

escrever_csv <- function(df, caminho) {
  dir.create(dirname(caminho), recursive = TRUE, showWarnings = FALSE)
  utils::write.csv(df, caminho, row.names = FALSE, na = "", fileEncoding = "UTF-8")
  invisible(caminho)
}

escrever_json <- function(dados, caminho) {
  dir.create(dirname(caminho), recursive = TRUE, showWarnings = FALSE)
  texto <- jsonlite::toJSON(dados, auto_unbox = TRUE, null = "null", na = "null",
                            digits = NA, pretty = TRUE, force = TRUE)
  writeLines(enc2utf8(as.character(texto)), caminho, useBytes = TRUE)
  invisible(caminho)
}

# ---------------------------------------------------------------------------
# Regras compartilhadas de síntese (meta.R, swim.R, testes_combinados.R)
# ---------------------------------------------------------------------------

#' Coluna por nome exato (texto); vetor vazio do tamanho certo se não existir.
#'
#' Evita `df$x`, que em data.frame faz casamento parcial ("t" casaria com "tipo_estatistica").
coluna <- function(df, nome) {
  if (nome %in% names(df)) as.character(df[[nome]]) else rep("", nrow(df))
}

#' Identificador do estudo: id_estudo; senão chave; senão id_efeito.
#'
#' A hierarquia estudo > relato > efeito exige agrupar por
#' estudo. Sem id_estudo caímos na chave (um relato = um estudo) e avisamos.
id_estudo_efetivo <- function(df) {
  ids <- coluna(df, "id_estudo")
  sem <- vazio(ids)
  ids[sem] <- coluna(df, "chave")[sem]
  sem <- vazio(ids)
  ids[sem] <- paste0("efeito:", coluna(df, "id_efeito")[sem])
  sem <- vazio(ids) | ids == "efeito:"
  ids[sem] <- paste0("linha:", which(sem))
  ids
}

#' Negações e prefixos que tornam um rótulo com "randomizado" NÃO randomizado.
#'
#' Avaliados antes do regex de randomizados: "não randomizado", "non-randomized",
#' "nonrandomised", "sem aleatorização", "quasi-randomized", "quase-experimental",
#' "pseudo-randomizado", "como se aleatório" (as-if random) e "not randomly assigned"
#' não são ECR. O separador entre as palavras pode ser espaço, hífen ou sublinhado
#' (valores de codebook como `nao_randomizado` ou `como_se_randomizado`).
PADRAO_NAO_RANDOMIZADO <- paste0(
  "(^|[^a-z])(nao|non|not|sem|without|un|no)[ _-]*(randomi[sz]|random|aleatori)|",
  "(^|[^a-z])(quas[ei]|pseudo)[ _-]*(randomi[sz]|random|aleatori|experim)|",
  "(^|[^a-z])(como[ _-]*se|as[ _-]*if)[ _-]*(randomi[sz]|random|aleatori)"
)
PADRAO_RANDOMIZADO <- paste0(
  "(^|[^a-z])(rct|ecr|ecra)([^a-z]|$)|randomi[sz]|aleatori|experimento de campo|",
  "field experiment|ensaio clinico"
)
#' "Aleatório" que descreve o modelo ou a amostragem, não a atribuição do tratamento.
PADRAO_ALEATORIO_NAO_ATRIBUICAO <- paste0(
  "(efeitos?|interceptos?|coeficientes?)[ _-]+aleatori[a-z]*|random[ _-]+(effects?|intercepts?|slopes?)|",
  "(amostra|amostragem)[ _-]+aleatori[a-z]*|random(ly)?[ _-]+(sampl[a-z]*|selected)"
)

#' Classe do desenho para separar randomizados de não randomizados antes de agregar.
#'
#' Negação e prefixos quase/quasi/pseudo/como se são tratados antes do regex de
#' randomizados, porque "não randomizado" contém a raiz "randomi" e seria lido como ECR.
#' "Efeitos aleatórios" e "amostra aleatória" são retirados do texto antes do teste:
#' descrevem o modelo ou a amostragem, não a atribuição do tratamento.
classe_desenho <- function(desenho) {
  s <- ascii_minusculo(desenho)
  nao_randomizado <- grepl(PADRAO_NAO_RANDOMIZADO, s)
  s <- gsub(PADRAO_ALEATORIO_NAO_ATRIBUICAO, " ", s)
  randomizado <- !nao_randomizado & grepl(PADRAO_RANDOMIZADO, s)
  ifelse(vazio(desenho), "desenho_nao_informado", ifelse(randomizado, "randomizado", "nao_randomizado"))
}

#' Rótulo do grupo de síntese: colunas de agrupamento × classe de desenho.
#'
#' `colunas_grupo` aceita várias colunas (ex.: familia_intervencao, construto_outcome),
#' para que o grupo coincida com a célula da caixa de ferramentas. Colunas ausentes
#' são ignoradas; sem nenhuma, tudo vira o grupo "todos".
rotulo_grupo <- function(df, colunas_grupo, separar_desenho = TRUE) {
  colunas <- colunas_grupo[nzchar(colunas_grupo) & colunas_grupo %in% names(df)]
  if (length(colunas)) {
    partes <- lapply(colunas, function(col) {
      g <- coluna(df, col)
      g[vazio(g)] <- "(sem valor)"
      g
    })
    g <- do.call(paste, c(partes, sep = " | "))
  } else {
    g <- rep("todos", nrow(df))
  }
  if (separar_desenho) paste(g, classe_desenho(coluna(df, "desenho")), sep = " | ") else g
}

#' Campos explícitos do grupo para quem consome os JSONs (ex.: `rs.py caixa`).
#'
#' Evita que o consumidor precise desmontar o rótulo "a | b | c": cada coluna de
#' agrupamento (e familia_intervencao/construto_outcome, quando têm valor único no
#' grupo) vira uma chave própria, mais a classe de desenho.
atributos_grupo <- function(df, colunas_grupo, separar_desenho = TRUE) {
  saida <- list()
  for (col in unique(c(colunas_grupo, "familia_intervencao", "construto_outcome"))) {
    if (!nzchar(col) || !col %in% names(df)) next
    v <- unique(coluna(df, col))
    v <- v[!vazio(v)]
    if (length(v) == 1L) saida[[col]] <- v
  }
  classes <- unique(classe_desenho(coluna(df, "desenho")))
  if (length(classes) == 1L) saida$classe_desenho <- classes
  saida
}

#' Lê --grupo como lista de colunas; ausente = construto_outcome; vazio = sem agrupamento.
cli_colunas_grupo <- function(args) {
  if (is.null(args[["grupo"]])) return("construto_outcome")
  cli_lista(args, "grupo")
}

#' Termos que identificam revisões e meta-análises (não estudos primários).
#'
#' Exige o tipo de revisão ("revisão sistemática", "systematic review", "scoping review",
#' "meta-análise", "overview", "umbrella"...). "Revisão" ou "review" sozinhos não bastam:
#' "revisão de prontuários", "chart review", "record review" e "peer review" descrevem
#' a coleta de dados de um estudo primário, não uma síntese de estudos.
PADRAO_REVISAO <- paste0(
  "revis(ao|oes)[ _-]+(sistematica|de[ _-]+escopo|guarda[ _-]*chuva|rapida|integrativa|narrativa|",
  "de[ _-]+literatura|da[ _-]+literatura|bibliografica|de[ _-]+revisoes)|",
  "(systematic|scoping|umbrella|rapid|literature|narrative|integrative|realist)[ _-]+reviews?|",
  "reviews?[ _-]+of[ _-]+(the[ _-]+)?(literature|reviews|systematic[ _-]+reviews)|",
  "meta[ _-]*anali[sz]|metanali[sz]|meta[ _-]*analy|overviews?|umbrella|guarda[ _-]*chuva|",
  "sintese[ _-]+de[ _-]+evidencias?|evidence[ _-]+synthesis"
)

#' Revisões e meta-análises nunca entram como estudo primário.
eh_revisao <- function(desenho) {
  grepl(PADRAO_REVISAO, ascii_minusculo(desenho))
}

#' Um efeito por estudo: marca `modelo_principal`; estudos ambíguos voltam em `conflitos`.
#'
#' A regra de modelo principal é do protocolo; o script não escolhe sozinho entre
#' estimativas do mesmo estudo porque isso abriria espaço para seleção a posteriori.
selecionar_um_por_estudo <- function(df, estudo) {
  manter <- logical(nrow(df))
  conflitos <- character(0)
  principal <- eh_verdadeiro(coluna(df, "modelo_principal"))
  for (e in unique(estudo)) {
    idx <- which(estudo == e)
    if (length(idx) == 1L) {
      manter[idx] <- TRUE
    } else if (sum(principal[idx]) == 1L) {
      manter[idx[principal[idx]]] <- TRUE
    } else {
      conflitos <- c(conflitos, e)
    }
  }
  list(manter = manter, conflitos = conflitos)
}

#' Sinal bruto (grupo 1 − grupo 2 / coeficiente positivo) a partir das colunas extraídas.
#'
#' Usado quando não há yi (ex.: só p e n): procura t, beta, diferença de médias e r,
#' nessa ordem. Devolve +1, −1, 0 ou NA.
sinal_bruto <- function(df) {
  candidatos <- list(
    como_num(coluna(df, "t")), como_num(coluna(df, "beta")),
    como_num(coluna(df, "m1")) - como_num(coluna(df, "m2")), como_num(coluna(df, "r"))
  )
  s <- rep(NA_real_, nrow(df))
  for (v in candidatos) {
    usar <- is.na(s) & !is.na(v) & v != 0
    s[usar] <- sign(v[usar])
  }
  s
}

#' Multiplicador que alinha o sinal à direção desejada (+1 aumentar, −1 reduzir, NA sem direção).
fator_direcao <- function(direcao_desejada) {
  s <- ascii_minusculo(direcao_desejada)
  ifelse(s %in% c("aumentar", "aumento", "increase", "maior", "+"), 1,
         ifelse(s %in% c("reduzir", "reducao", "diminuir", "decrease", "menor", "-"), -1, NA_real_))
}

#' Tamanho da amostra: n_total; senão n1 + n2.
n_amostra <- function(df) {
  n <- como_num(coluna(df, "n_total"))
  soma <- como_num(coluna(df, "n1")) + como_num(coluna(df, "n2"))
  n[is.na(n)] <- soma[is.na(n)]
  n
}

#' Direção de cada linha: +1 benéfica, −1 danosa, 0 nula, NA sem direção.
#'
#' Direção vem do estimador pontual, nunca da significância.
#' Usa yi já alinhado quando existe; senão o sinal bruto (t, beta, m1 − m2, r)
#' multiplicado pela direção desejada. Assim swim.R e testes_combinados.R aceitam
#' tanto a saída de efeitos.R quanto uma extração só com p, n e sinal.
direcao_linha <- function(df) {
  yi <- como_num(coluna(df, "yi"))
  alinhado <- coluna(df, "sinal_alinhado") %in% c("mantido", "invertido")
  dir <- ifelse(!is.na(yi) & alinhado, sign(yi), NA_real_)
  bruto <- sinal_bruto(df) * fator_direcao(coluna(df, "direcao_desejada"))
  dir[is.na(dir)] <- bruto[is.na(dir)]
  dir
}

#' Opções de --excluir-rob (meta.R, swim.R e testes_combinados.R).
OPCOES_EXCLUIR_ROB <- c("nenhum", "critico")

#' rob_geral crítico (ROBINS-I "critical"; RoB 2 não tem esse nível).
eh_rob_critico <- function(x) {
  s <- ascii_minusculo(x)
  grepl("critic", s) & !grepl("(nao|non|not|sem)[ _-]*critic", s)
}

#' Lê e valida --excluir-rob; `critico` exige a coluna rob_geral na entrada.
#'
#' Resultado com risco de viés crítico sai da análise PRINCIPAL e a análise com ele vira a
#' sensibilidade `com_rob_critico` (Cochrane Handbook v6.5, caps. 24 e 25: resultados com risco crítico
#' no ROBINS-I em geral não entram na síntese). Mesmo contrato nos três scripts de síntese.
cli_excluir_rob <- function(args, df = NULL) {
  opcao <- ascii_minusculo(as.character(cli_arg(args, "excluir-rob", "nenhum")))
  if (!opcao %in% OPCOES_EXCLUIR_ROB) {
    cli_falhar(sprintf("--excluir-rob deve ser %s", paste(OPCOES_EXCLUIR_ROB, collapse = " ou ")), SAIDA_ERRO_DADOS)
  }
  if (opcao == "critico" && !is.null(df) && !"rob_geral" %in% names(df)) {
    cli_falhar("--excluir-rob=critico exige a coluna rob_geral na entrada (preserve-a em preparar-efeitos)",
               SAIDA_ERRO_DADOS)
  }
  opcao
}

#' Linhas que nunca entram numa síntese de estudos primários.
linha_excluida_sintese <- function(df) {
  coluna(df, "formula_id") == "rejeitado_revisao" | eh_revisao(coluna(df, "desenho"))
}

# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

#' Desenha num arquivo PNG ou PDF (pela extensão) e devolve o caminho, ou NULL se falhar.
#'
#' Usa o bitmapType padrão da sessão (quartz no macOS, cairo/Xlib no Linux) em vez de
#' forçar cairo: no macOS sem XQuartz, capabilities("cairo") diz TRUE mas a DLL não
#' carrega e o PNG simplesmente não é escrito. Por isso o arquivo é conferido depois.
salvar_grafico <- function(arquivo, largura, altura, desenhar) {
  dir.create(dirname(arquivo), recursive = TRUE, showWarnings = FALSE)
  if (file.exists(arquivo)) unlink(arquivo)
  aberto <- tryCatch({
    if (grepl("\\.pdf$", arquivo, ignore.case = TRUE)) {
      grDevices::pdf(arquivo, width = largura, height = altura)
    } else {
      grDevices::png(arquivo, width = largura, height = altura, units = "in", res = 150,
                     type = getOption("bitmapType"))
    }
    TRUE
  }, error = function(e) {
    message("aviso: não foi possível abrir o dispositivo gráfico para ", arquivo, ": ", conditionMessage(e))
    FALSE
  })
  if (!aberto) return(NULL)
  dispositivo <- grDevices::dev.cur()
  tryCatch(desenhar(), error = function(e) {
    message("aviso: falha ao desenhar ", arquivo, ": ", conditionMessage(e))
  }, finally = if (dispositivo > 1L) grDevices::dev.off(dispositivo))
  if (file.exists(arquivo) && file.info(arquivo)$size > 0) arquivo else NULL
}
