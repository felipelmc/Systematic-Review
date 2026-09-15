# Testes de _cli.R: argumentos, códigos de saída, números e regras compartilhadas.

localizar_scripts_r <- function() {
  atual <- normalizePath(getwd())
  repeat {
    candidato <- file.path(atual, "skills", "revisao-sistematica", "scripts", "R")
    if (dir.exists(candidato)) return(candidato)
    pai <- dirname(atual)
    if (identical(pai, atual)) stop("pasta scripts/R não encontrada a partir de ", getwd())
    atual <- pai
  }
}
source(file.path(localizar_scripts_r(), "_cli.R"), encoding = "UTF-8")

test_that("cli_args aceita --chave=valor, --chave valor e flags", {
  # "--flag valor" consome o próximo token; um posicional vai antes das opções
  a <- cli_args(c("solto", "--in=a.csv", "--k-min=5", "--grupo", "construto", "--verbose"))
  expect_equal(a$`in`, "a.csv")
  expect_equal(cli_num(a, "k-min"), 5)
  expect_equal(cli_arg(a, "grupo"), "construto")
  expect_true(isTRUE(a$verbose))
  expect_equal(a$.posicionais, "solto")
  expect_equal(cli_lista(cli_args("--moderadores=x, y,,z"), "moderadores"), c("x", "y", "z"))
  expect_false(cli_bool(cli_args("--separar-desenho=nao"), "separar-desenho", TRUE))
  expect_true(cli_bool(cli_args(character(0)), "separar-desenho", TRUE))
  expect_equal(cli_arg(cli_args("--grupo="), "grupo", "padrao"), "")
})

test_that("argumento obrigatório ausente e número inválido são erro de uso", {
  expect_error(cli_arg(cli_args(character(0)), "in", obrigatorio = TRUE), class = "rs_saida")
  expect_error(cli_num(cli_args("--rho=abc"), "rho"), class = "rs_saida")
})

test_that("cli_executar preserva códigos e imprime JSON na última linha", {
  saida <- capture.output(cod <- suppressMessages(cli_executar(function() list(codigo = 0L, resumo = list(ok = TRUE, n = 2L)))))
  expect_equal(cod, 0L)
  expect_equal(jsonlite::fromJSON(saida[length(saida)])$n, 2L)
  saida <- capture.output(cod <- suppressMessages(cli_executar(function() exigir_pacotes("pacoteQueNaoExiste123"))))
  expect_equal(cod, 3L)
  expect_false(jsonlite::fromJSON(saida[length(saida)])$ok)
  saida <- capture.output(cod <- suppressMessages(cli_executar(function() cli_falhar("checagem", SAIDA_CHECAGEM))))
  expect_equal(cod, 2L)
  saida <- capture.output(cod <- suppressMessages(cli_executar(function() stop("inesperado"))))
  expect_equal(cod, 1L)
  expect_equal(jsonlite::fromJSON(saida[length(saida)])$erro, "inesperado")
})

test_that("como_num lida com vírgula decimal, vazios e lixo", {
  expect_equal(como_num(c("0,45", "1.5", "", "NA", "abc", "+2", " 3 ")), c(0.45, 1.5, NA, NA, NA, 2, 3))
})

test_that("ascii_minusculo remove acentos sem apóstrofos (iconv do macOS)", {
  expect_equal(ascii_minusculo(c("Meta-Análise", "REVISÃO", "Crítico", NA)), c("meta-analise", "revisao", "critico", ""))
})

test_that("classe de desenho e detecção de revisões", {
  expect_equal(classe_desenho(c("RCT", "ECR por cluster", "DiD", "experimento natural", "", "Randomized field experiment")),
               c("randomizado", "randomizado", "nao_randomizado", "nao_randomizado", "desenho_nao_informado", "randomizado"))
  expect_equal(eh_revisao(c("meta-análise", "RCT", "Revisão sistemática", "scoping review", "painel")),
               c(TRUE, FALSE, TRUE, TRUE, FALSE))
})

test_that("regressão: negação e quase/quasi não viram randomizado", {
  nao <- c("não randomizado", "non-randomized", "nonrandomised", "sem aleatorização", "quasi-randomized",
           "quase-experimental", "Ensaio clínico não randomizado", "nao_randomizado", "Quasi-Experiment",
           "pseudo-randomised", "como_se_randomizado", "not randomly assigned", "unrandomized")
  expect_equal(unname(classe_desenho(nao)), rep("nao_randomizado", length(nao)))
  # "aleatório" do modelo ou da amostragem não é atribuição aleatória
  expect_equal(classe_desenho(c("painel com efeitos aleatórios", "survey com amostra aleatória", "random effects panel")),
               rep("nao_randomizado", 3))
  sim <- c("RCT com efeitos aleatórios", "randomized, non-blinded trial", "ensaio sem cegamento, randomizado",
           "experimento_aleatorizado_individual", "ECR (sorteio)")
  expect_equal(unname(classe_desenho(sim)), rep("randomizado", length(sim)))
})

test_that("regressão: eh_revisao exige o tipo de revisão e não casa revisão de prontuários", {
  revisoes <- c("revisão sistemática", "Systematic Review and Meta-Analysis", "meta-analysis", "metanálise",
                "overview of reviews", "umbrella review", "scoping review", "revisão de escopo", "revisão guarda-chuva")
  expect_true(all(eh_revisao(revisoes)))
  primarios <- c("revisão de prontuários", "chart review", "retrospective chart review", "record review",
                 "peer review", "revisão por pares", "review", "coorte com revisão de registros")
  expect_false(any(eh_revisao(primarios)))
})

test_that("um efeito por estudo respeita modelo_principal e aponta conflitos", {
  df <- data.frame(modelo_principal = c("", "1", "", "", "0"), stringsAsFactors = FALSE)
  estudo <- c("A", "B", "B", "C", "C")
  sel <- selecionar_um_por_estudo(df, estudo)
  expect_equal(sel$manter, c(TRUE, TRUE, FALSE, FALSE, FALSE))
  expect_equal(sel$conflitos, "C")
})

test_that("id do estudo cai para chave e depois para id_efeito", {
  df <- data.frame(id_estudo = c("ES1", "", ""), chave = c("K1", "K2", ""), id_efeito = c("E1", "E2", "E3"),
                   stringsAsFactors = FALSE)
  expect_equal(id_estudo_efetivo(df), c("ES1", "K2", "efeito:E3"))
})

test_that("coluna() não faz casamento parcial de nomes", {
  df <- data.frame(tipo_estatistica = "t", stringsAsFactors = FALSE)
  expect_equal(coluna(df, "t"), "")
})

test_that("salvar_grafico devolve o caminho só quando o arquivo existe", {
  dir <- withr::local_tempdir()
  arq <- salvar_grafico(file.path(dir, "x.pdf"), 4, 4, function() plot(1:3))
  expect_true(file.exists(arq))
  falha <- suppressMessages(salvar_grafico(file.path(dir, "y.pdf"), 4, 4, function() stop("quebrou")))
  expect_true(is.null(falha) || file.exists(falha))
})
