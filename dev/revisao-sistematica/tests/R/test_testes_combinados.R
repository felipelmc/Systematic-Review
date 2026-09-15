# Testes de testes_combinados.R com vetores fixos e valores calculados à mão.

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
source(file.path(localizar_scripts_r(), "testes_combinados.R"), encoding = "UTF-8")

test_that("Stouffer ponderado por √n com p unilateral", {
  p <- c(0.01, 0.04, 0.20, 0.60)
  n <- c(100, 50, 80, 30)
  r <- stouffer_ponderado(p, n)
  Z <- sum(sqrt(n) * qnorm(1 - p)) / sqrt(sum(n))
  expect_equal(r$Z, Z, tolerance = 1e-12)
  expect_equal(r$p_unilateral, 1 - pnorm(Z), tolerance = 1e-12)
  expect_equal(r$k, 4L)
  # estudo sem n não recebe peso arbitrário
  r2 <- stouffer_ponderado(c(p, 0.001), c(n, NA))
  expect_equal(r2$Z, Z, tolerance = 1e-12)
  expect_equal(r2$k_sem_n, 1L)
})

test_that("Winer usa t e gl/(gl − 2), só com gl > 2", {
  t <- c(2.5, 1.2, -0.5, 3)
  gl <- c(30, 20, 2, NA)
  r <- winer(t, gl)
  Z <- (2.5 + 1.2) / sqrt(30 / 28 + 20 / 18)
  expect_equal(r$Z, Z, tolerance = 1e-12)
  expect_equal(r$k, 2L)
  expect_equal(r$k_excluidos_gl, 2L)
  # não é a versão errada com z no numerador
  z_errado <- qnorm(pt(c(2.5, 1.2), c(30, 20)))
  expect_false(isTRUE(all.equal(r$Z, sum(z_errado) / sqrt(30 / 28 + 20 / 18))))
})

test_that("Cooper é o teste de sinal binomial exato sobre a direção", {
  r <- cooper_sinal(c(1, 1, 1, -1, 0, NA))
  expect_equal(r$k, 4L)
  expect_equal(r$n_nulo, 1L)
  expect_equal(r$n_sem_direcao, 1L)
  expect_equal(r$p_bilateral, binom.test(3, 4)$p.value)
})

test_that("Fisher usa p bilateral e é rotulado não direcional", {
  r <- fisher_nao_direcional(c(0.02, 0.5, NA))
  X2 <- -2 * (log(0.02) + log(0.5))
  expect_equal(r$X2, X2, tolerance = 1e-12)
  expect_equal(r$gl, 4L)
  expect_equal(r$p, pchisq(X2, 4, lower.tail = FALSE), tolerance = 1e-12)
  expect_equal(r$rotulo, "não direcional")
})

base_estudos <- function() {
  data.frame(
    id_efeito = paste0("E", 1:4), id_estudo = paste0("S", 1:4), chave = paste0("K", 1:4),
    desenho = "RCT", construto_outcome = "x", direcao_desejada = c("aumentar", "aumentar", "reduzir", "aumentar"),
    tipo_estatistica = c("t", "p_n", "t", "mann_whitney"),
    t = c("2.1", "", "-1.5", "1.8"), df = c("40", "", "58", ""), p = c("", "0.04", "", ""),
    beta = c("", "-0.3", "", ""), n_total = c("42", "100", "60", "30"),
    yi = "", sei = "", sinal_alinhado = "", modelo_principal = "",
    stringsAsFactors = FALSE
  )
}

test_that("p unilateral segue a direção declarada e a fonte correta", {
  d <- base_estudos()
  d$.estudo <- d$id_estudo
  d$.grupo <- "x"
  est <- p_por_linha(d)
  expect_equal(est$fonte_p, c("t", "p_informado", "t", "z"))
  expect_equal(est$p_unilateral[1], pt(2.1, 40, lower.tail = FALSE), tolerance = 1e-12)
  expect_equal(est$p_unilateral[2], 1 - 0.04 / 2)                 # beta negativo com "aumentar": danoso
  expect_equal(est$p_unilateral[3], pt(1.5, 58, lower.tail = FALSE), tolerance = 1e-12)  # t −1,5 com "reduzir"
  expect_equal(est$p_unilateral[4], pnorm(1.8, lower.tail = FALSE), tolerance = 1e-12)
  expect_equal(est$p_bilateral[2], 0.04)
  expect_equal(est$direcao, c(1, -1, 1, 1))
  expect_equal(est$t_alinhado[3], 1.5)
  expect_true(is.na(est$t_reconstruido[4]))  # z do Mann-Whitney nunca vira t
})

test_that("Fisher não distingue direções opostas; Stouffer distingue", {
  d <- base_estudos()[c(1, 1), ]
  d$id_estudo <- c("S1", "S2")
  d$.estudo <- d$id_estudo
  d$.grupo <- "x"
  d2 <- d
  d2$t[2] <- "-2.1"
  a <- p_por_linha(d)
  b <- p_por_linha(d2)
  expect_equal(fisher_nao_direcional(a$p_bilateral)$p, fisher_nao_direcional(b$p_bilateral)$p)
  expect_lt(stouffer_ponderado(a$p_unilateral, a$n)$p_unilateral, 0.05)
  expect_equal(stouffer_ponderado(b$p_unilateral, b$n)$Z, 0, tolerance = 1e-12)
})

test_that("um p por estudo: dependência não resolvida bloqueia com código 2", {
  dir <- withr::local_tempdir()
  df <- base_estudos()
  df$id_estudo[2] <- "S1"
  entrada <- file.path(dir, "efeitos.csv")
  utils::write.csv(df, entrada, row.names = FALSE)
  saida <- capture.output(res <- main_testes(cli_args(c(paste0("--in=", entrada), paste0("--out-dir=", dir)))))
  expect_equal(res$codigo, 2L)
  expect_match(paste(saida, collapse = " "), "RESSALVA")
  df$modelo_principal[1] <- "1"
  utils::write.csv(df, entrada, row.names = FALSE)
  saida <- capture.output(res <- main_testes(cli_args(c(paste0("--in=", entrada), paste0("--out-dir=", dir)))))
  expect_equal(res$codigo, 0L)
})

test_that("main_testes grava JSON com ressalva e tabelas", {
  dir <- withr::local_tempdir()
  entrada <- file.path(dir, "efeitos.csv")
  utils::write.csv(base_estudos(), entrada, row.names = FALSE)
  saida <- capture.output(res <- main_testes(cli_args(c(paste0("--in=", entrada), paste0("--out-dir=", dir)))))
  expect_equal(res$codigo, 0L)
  expect_match(saida[1], "^RESSALVA")
  json <- jsonlite::fromJSON(file.path(dir, "testes_combinados.json"), simplifyVector = FALSE)
  expect_match(json$ressalva, "análise secundária")
  tt <- json$grupos[[1]]$testes
  expect_equal(tt$fisher_nao_direcional$rotulo, "não direcional")
  expect_equal(tt$cooper_teste_de_sinal$k, 4L)
  expect_equal(tt$winer$k, 2L)  # S1 e S3 com t; S2 sem gl; S4 é z
  tab <- read.csv(file.path(dir, "tabelas", "testes_combinados.csv"))
  expect_equal(nrow(tab), 4L)
  expect_true(file.exists(file.path(dir, "tabelas", "testes_combinados_estudos.csv")))
})

test_that("regressão: --excluir-rob=critico tira o p crítico dos testes principais, depois do modelo principal", {
  df <- base_estudos()
  df$rob_geral <- c("critico", "baixo", "moderado", "")
  df$.estudo <- df$id_estudo
  df$.grupo <- "x"
  sem <- testar_grupo(df, "x", list(grupo = "construto_outcome", separar_desenho = TRUE))
  com <- testar_grupo(df, "x", list(grupo = "construto_outcome", separar_desenho = TRUE, excluir_rob = "critico"))
  r <- com$resumo
  expect_equal(r$k_estudos, 3L)
  expect_equal(r$testes$cooper_teste_de_sinal$k, sem$resumo$testes$cooper_teste_de_sinal$k - 1L)
  expect_equal(r$testes$winer$k, 1L)  # S1 (t, crítico) saiu; sobra S3
  expect_equal(r$excluidos_rob_critico$n_estudos, 1L)
  expect_equal(unlist(r$excluidos_rob_critico$estudos), "S1")
  expect_equal(r$sensibilidade$com_rob_critico$testes$stouffer_ponderado$Z, sem$resumo$testes$stouffer_ponderado$Z)
  expect_equal(sum(com$estudos$excluido_rob_critico), 1L)
  expect_null(sem$resumo$excluidos_rob_critico)
  # estudo com dois efeitos: o principal (não crítico) é escolhido antes, então o estudo continua
  df2 <- rbind(df, df[1, ])
  df2$id_efeito[5] <- "E5"
  df2$rob_geral[5] <- "baixo"
  df2$modelo_principal[c(1, 5)] <- c("", "1")
  r2 <- testar_grupo(df2, "x", list(grupo = "construto_outcome", separar_desenho = TRUE, excluir_rob = "critico"))
  expect_equal(r2$resumo$excluidos_rob_critico$n_estudos, 0L)
  expect_false(r2$resumo$sensibilidade$com_rob_critico$executado)
})

test_that("main_testes: --excluir-rob exige rob_geral e vai para o JSON", {
  dir <- withr::local_tempdir()
  entrada <- file.path(dir, "efeitos.csv")
  utils::write.csv(base_estudos(), entrada, row.names = FALSE)
  expect_error(capture.output(main_testes(cli_args(c(paste0("--in=", entrada), paste0("--out-dir=", dir),
                                                     "--excluir-rob=critico")))), "rob_geral", class = "rs_saida")
  df <- base_estudos()
  df$rob_geral <- c("baixo", "critical", "", "")
  utils::write.csv(df, entrada, row.names = FALSE)
  saida <- capture.output(res <- main_testes(cli_args(c(paste0("--in=", entrada), paste0("--out-dir=", dir),
                                                        "--excluir-rob=critico"))))
  expect_equal(res$codigo, 0L)
  expect_equal(res$resumo$n_excluidos_rob_critico, 1L)
  json <- jsonlite::fromJSON(file.path(dir, "testes_combinados.json"), simplifyVector = FALSE)
  expect_equal(json$parametros$excluir_rob, "critico")
  expect_equal(json$grupos[[1]]$k_estudos, 3L)
})
