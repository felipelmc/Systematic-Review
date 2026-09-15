# Testes de efeitos.R: valores de referência de Borenstein et al. (2009) e dos pacotes esc/metafor.
#
# Rodar: Rscript -e 'testthat::test_dir("tests/R")'  (a partir da raiz do repositório)

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
source(file.path(localizar_scripts_r(), "efeitos.R"), encoding = "UTF-8")

linha_efeito <- function(...) {
  campos <- list(...)
  df <- as.data.frame(setNames(replicate(length(COLUNAS_EFEITOS_EXTRAIDOS), "", simplify = FALSE),
                               COLUNAS_EFEITOS_EXTRAIDOS), stringsAsFactors = FALSE)
  for (nome in names(campos)) df[[nome]] <- as.character(campos[[nome]])
  if (!"direcao_desejada" %in% names(campos)) df$direcao_desejada <- "aumentar"
  df
}

calc1 <- function(...) calcular_efeitos(linha_efeito(...))

test_that("médias e DP reproduzem o exemplo de Borenstein (cap. 4)", {
  r <- calc1(tipo_estatistica = "md_sd", m1 = 103, sd1 = 5.5, n1 = 50, m2 = 100, sd2 = 4.5, n2 = 50)
  # Borenstein et al. 2009: d = 0,5970; Var(d) = 0,0418; J = 0,9923; g = 0,5924; Var(g) = 0,0411
  expect_equal(r$yi, 0.5924, tolerance = 1e-4)
  expect_equal(r$vi, 0.0411, tolerance = 1e-3)
  expect_equal(r$sei, sqrt(r$vi))
  expect_equal(r$formula_id, "md_sd")
  expect_equal(r$aproximado, 0L)
  expect_equal(r$sinal_alinhado, "mantido")
  d <- (103 - 100) / sqrt((49 * 5.5^2 + 49 * 4.5^2) / 98)
  vd <- 100 / 2500 + d^2 / 200
  j <- 1 - 3 / (4 * 98 - 1)
  expect_equal(r$yi, j * d, tolerance = 1e-12)
  expect_equal(r$vi, j^2 * vd, tolerance = 1e-12)
})

test_that("g de médias/DP bate com esc::esc_mean_sd", {
  skip_if_not_installed("esc")
  ref <- esc::esc_mean_sd(grp1m = 12.4, grp1sd = 3.1, grp1n = 34, grp2m = 10.9, grp2sd = 2.8, grp2n = 29, es.type = "g")
  r <- calc1(tipo_estatistica = "md_sd", m1 = 12.4, sd1 = 3.1, n1 = 34, m2 = 10.9, sd2 = 2.8, n2 = 29)
  expect_equal(r$yi, ref$es, tolerance = 1e-8)
})

test_that("g a partir de t bate com esc::esc_t e usa Var(g) = J²·Var(d)", {
  skip_if_not_installed("esc")
  ref <- esc::esc_t(t = 2.5, grp1n = 30, grp2n = 25, es.type = "g")
  r <- calc1(tipo_estatistica = "t", t = 2.5, n1 = 30, n2 = 25)
  expect_equal(r$yi, ref$es, tolerance = 1e-8)
  j <- 1 - 3 / (4 * 53 - 1)
  d <- 2.5 * sqrt(1 / 30 + 1 / 25)
  expect_equal(r$vi, j^2 * (55 / 750 + d^2 / 110), tolerance = 1e-12)
  expect_equal(r$formula_id, "t_ind")
})

test_that("t só com n_total divide os grupos e marca aproximado", {
  r <- calc1(tipo_estatistica = "t", t = 2, n_total = 100)
  expect_equal(r$formula_id, "t_ind_n_total")
  expect_equal(r$aproximado, 1L)
  expect_equal(r$yi / (1 - 3 / (4 * 98 - 1)), 2 * 2 / sqrt(100), tolerance = 1e-12)
})

test_that("OR → d via logit bate com a fórmula e com esc::convert_or2d", {
  r <- calc1(tipo_estatistica = "or", or_ = 2, ci_lo = 1.2, ci_hi = 3.3333)
  se_log <- (log(3.3333) - log(1.2)) / (2 * qnorm(0.975))
  expect_equal(r$yi, log(2) * sqrt(3) / pi, tolerance = 1e-12)  # sem N: J = 1
  expect_equal(r$vi, se_log^2 * 3 / pi^2, tolerance = 1e-12)
  expect_match(r$aviso, "sem correção J")
  skip_if_not_installed("esc")
  ref <- esc::convert_or2d(or = 2, se = se_log, es.type = "d")
  expect_equal(r$yi, ref$es, tolerance = 1e-10)
  expect_equal(r$vi, ref$var, tolerance = 1e-10)
})

test_that("coeficiente binário dividido pelo DP de Y (beta_sd)", {
  r <- calc1(tipo_estatistica = "beta_sd", beta = 0.5, sdy = 2, se = 0.1)
  expect_equal(r$yi, 0.25)
  expect_equal(r$sei, 0.05)
  r2 <- calc1(tipo_estatistica = "beta_sd", beta = 0.5, sdy = 2, se = 0.1, df = 98, estimando = "LATE")
  j <- 1 - 3 / (4 * 98 - 1)
  expect_equal(r2$yi, 0.25 * j, tolerance = 1e-12)
  expect_equal(r2$vi, (0.1 / 2)^2 * j^2, tolerance = 1e-12)
  expect_match(r2$aviso, "LATE")
  r3 <- calc1(tipo_estatistica = "beta_sd", beta = 0.5, sd2 = 2, n1 = 50, n2 = 50)
  expect_equal(r3$aproximado, 1L)
  expect_match(r3$aviso, "sdy ausente")
})

test_that("r → d só com n_total assume p1 = 0,5 e sai aproximado (fora da tabela do cap. 07)", {
  r <- calc1(tipo_estatistica = "r", r = 0.3, n_total = 100)
  d <- 2 * 0.3 / sqrt(1 - 0.09)
  vd <- 100 / 2500 + d^2 / 200  # V_d de base com n1 = n2 = 50
  j <- 1 - 3 / (4 * 98 - 1)
  expect_equal(r$yi, j * d, tolerance = 1e-12)
  expect_equal(r$vi, j^2 * vd, tolerance = 1e-12)
  expect_equal(unname(round(d, 5)), 0.62897)
  expect_equal(r$formula_id, "r_d_n_total")
  expect_equal(r$aproximado, 1L)
  skip_if_not_installed("esc")
  ref <- esc::esc_rpb(r = 0.3, totaln = 100, es.type = "d")
  expect_equal(r$yi / j, ref$es, tolerance = 1e-10)
  expect_equal(r$vi / j^2, ref$var, tolerance = 1e-10)
})

test_that("regressão: r → d usa p1 = n1/N quando n1 e n2 existem (cap. 07; esc::esc_rpb)", {
  r <- calc1(tipo_estatistica = "r", r = 0.3, n1 = 30, n2 = 90, n_total = 120)
  p1 <- 30 / 120
  d <- 0.3 / sqrt((1 - 0.09) * p1 * (1 - p1))
  j <- 1 - 3 / (4 * 118 - 1)
  expect_equal(r$yi, j * d, tolerance = 1e-12)
  expect_equal(r$vi, j^2 * (120 / 2700 + d^2 / 240), tolerance = 1e-12)
  expect_equal(r$formula_id, "r_d")
  expect_equal(r$aproximado, 0L)
  # com grupos desbalanceados, a fórmula de grupos iguais subestima d
  expect_gt(r$yi, j * 2 * 0.3 / sqrt(1 - 0.09))
  skip_if_not_installed("esc")
  ref <- esc::esc_rpb(r = 0.3, grp1n = 30, grp2n = 90, es.type = "d")
  expect_equal(r$yi / j, ref$es, tolerance = 1e-10)
  expect_equal(r$vi / j^2, ref$var, tolerance = 1e-10)
})

test_that("correlação parcial vem de t e gl e sai como aproximada", {
  r <- calc1(tipo_estatistica = "parcial_r", t = 3, df = 60)
  rp <- 3 / sqrt(9 + 60)
  expect_equal(r$yi / (1 - 3 / (4 * 60 - 1)), 2 * rp / sqrt(1 - rp^2), tolerance = 1e-12)
  expect_equal(r$aproximado, 1L)
  # sem a coluna m_preditores: rota pelo gl residual, com formula_id próprio e aviso honesto
  expect_equal(r$formula_id, "parcial_r_d_gl")
  expect_match(r$aviso, "sem m_preditores")
})

test_that("regressão: correlação parcial com n e m segue o cap. 07 (n − m − 1; Var = (1 − r²)²/(n − m))", {
  n <- 80; m <- 5; t <- 2.5
  r <- calc1(tipo_estatistica = "parcial_r", t = t, n_total = n, m_preditores = m)
  rp <- t / sqrt(t^2 + n - m - 1)
  var_r <- (1 - rp^2)^2 / (n - m)
  d <- 2 * rp / sqrt(1 - rp^2)
  vd <- 4 * var_r / (1 - rp^2)^3
  j <- 1 - 3 / (4 * (n - m - 1) - 1)
  expect_equal(r$formula_id, "parcial_r_d")
  expect_equal(r$aproximado, 1L)
  expect_equal(r$yi, j * d, tolerance = 1e-12)
  expect_equal(r$vi, j^2 * vd, tolerance = 1e-12)
  # a rota antiga (gl = n − m − 1 também na variância) dá variância maior: não é a do capítulo
  expect_false(isTRUE(all.equal(r$vi, j^2 * 4 * ((1 - rp^2)^2 / (n - m - 1)) / (1 - rp^2)^3)))
  # r informado diretamente, com n1 + n2 no lugar de n_total
  r2 <- calc1(tipo_estatistica = "parcial_r", r = 0.2, n1 = 40, n2 = 40, m_preditores = 3)
  expect_equal(r2$formula_id, "parcial_r_d")
  expect_equal(r2$vi / (1 - 3 / (4 * 76 - 1))^2, 4 * ((1 - 0.04)^2 / 77) / (1 - 0.04)^3, tolerance = 1e-12)
  # df informado incoerente com n − m − 1 gera aviso; m inválido não calcula
  r3 <- calc1(tipo_estatistica = "parcial_r", t = t, n_total = n, m_preditores = m, df = 60)
  expect_match(r3$aviso, "difere de n − m − 1")
  r4 <- calc1(tipo_estatistica = "parcial_r", t = t, n_total = 5, m_preditores = 4)
  expect_true(is.na(r4$yi))
  # coluna presente mas vazia nesta linha: volta à rota pelo gl residual
  r5 <- calc1(tipo_estatistica = "parcial_r", t = 3, df = 60, m_preditores = "")
  expect_equal(r5$formula_id, "parcial_r_d_gl")
})

test_that("Mann-Whitney usa z (normal), não t: erro do código do Anexo J da proposta OQF", {
  r <- calc1(tipo_estatistica = "mann_whitney", p = 0.03, n1 = 20, n2 = 20, m1 = 14, m2 = 11)
  z <- qnorm(1 - 0.03 / 2)
  j <- 1 - 3 / (4 * 38 - 1)
  rr <- z / sqrt(40)
  d <- rr / sqrt((1 - rr^2) * 0.25)
  expect_equal(r$yi, j * d, tolerance = 1e-12)
  t_errado <- qt(1 - 0.03 / 2, 38)
  rr_errado <- t_errado / sqrt(40)
  expect_false(isTRUE(all.equal(r$yi, j * rr_errado / sqrt((1 - rr_errado^2) * 0.25))))
  expect_equal(r$formula_id, "mann_whitney_z")
  expect_equal(r$aproximado, 1L)
})

test_that("regressão: Mann-Whitney segue o cap. 07 (r = z/√N, depois r → d com p1 = n1/N)", {
  r <- calc1(tipo_estatistica = "mann_whitney", t = -2.151, n1 = 25, n2 = 35)
  rr <- -2.151 / sqrt(60)
  p1 <- 25 / 60
  d <- rr / sqrt((1 - rr^2) * p1 * (1 - p1))
  j <- 1 - 3 / (4 * 58 - 1)
  expect_equal(r$yi, j * d, tolerance = 1e-12)
  expect_equal(r$vi, j^2 * (60 / 875 + d^2 / 120), tolerance = 1e-12)
  # a rota antiga (z como t de duas médias) dava outro valor
  expect_false(isTRUE(all.equal(r$yi, j * -2.151 * sqrt(1 / 25 + 1 / 35))))
  expect_match(r$aviso, "coluna t interpretada como z")
  # z com sinal oposto a m1 − m2 gera alerta (o sinal impresso depende da ordem dos grupos)
  r2 <- calc1(tipo_estatistica = "mann_whitney", t = -2.151, n1 = 25, n2 = 35, m1 = 11, m2 = 9)
  expect_match(r2$aviso, "sinal de z oposto")
  r3 <- calc1(tipo_estatistica = "mann_whitney", t = 9, n1 = 20, n2 = 20)
  expect_true(is.na(r3$yi))
  expect_match(r3$aviso, "incompatível")
})

test_that("F sem fonte de sinal não é calculado; com sinal, vira t", {
  r <- calc1(tipo_estatistica = "f1", f = 6.25, n1 = 30, n2 = 30)
  expect_true(is.na(r$yi))
  expect_match(r$aviso, "não informa direção")
  r2 <- calc1(tipo_estatistica = "f1", f = 6.25, n1 = 30, n2 = 30, m1 = 9, m2 = 10)
  expect_lt(r2$yi, 0)
  expect_equal(abs(r2$yi), (1 - 3 / 231) * 2.5 * sqrt(2 / 30), tolerance = 1e-12)
})

test_that("p e n viram t com gl = N − 2 e marcam aproximado", {
  r <- calc1(tipo_estatistica = "p_n", p = 0.04, n1 = 40, n2 = 40, beta = -1)
  t <- -qt(1 - 0.02, 78)
  expect_equal(r$yi, (1 - 3 / (4 * 78 - 1)) * t * sqrt(2 / 40), tolerance = 1e-12)
  expect_equal(r$aproximado, 1L)
})

test_that("g e d informados preservam o valor e o EP", {
  r <- calc1(tipo_estatistica = "g", beta = 0.4, se = 0.15)
  expect_equal(r$yi, 0.4)
  expect_equal(r$vi, 0.0225)
  r2 <- calc1(tipo_estatistica = "g", g = 0.4, n1 = 30, n2 = 30)
  expect_equal(r2$yi, 0.4, tolerance = 1e-12)
  r3 <- calc1(tipo_estatistica = "d", beta = 0.5, se = 0.2, n1 = 20, n2 = 20)
  j <- 1 - 3 / (4 * 38 - 1)
  expect_equal(r3$yi, 0.5 * j, tolerance = 1e-12)
  expect_equal(r3$vi, 0.04 * j^2, tolerance = 1e-12)
})

test_that("mediana/IQR sem quartis usa IQR/1,35 com formula_id honesto (não Wan)", {
  r <- calc1(tipo_estatistica = "mediana_iqr", m1 = 12, sd1 = 4, n1 = 25, m2 = 10, sd2 = 4, n2 = 25)
  d <- 2 / (4 / 1.35)
  expect_equal(r$yi, (1 - 3 / (4 * 48 - 1)) * d, tolerance = 1e-12)
  expect_equal(r$aproximado, 1L)
  expect_equal(r$formula_id, "mediana_iqr_aprox")
})

test_that("regressão: mediana com q1, q3 e n usa Wan et al. (2014), cenário S3", {
  df <- linha_efeito(tipo_estatistica = "mediana_iqr", m1 = 12, n1 = 25, m2 = 10, n2 = 40)
  df$q1_1 <- "9"; df$q3_1 <- "16"; df$q1_2 <- "7"; df$q3_2 <- "12"
  r <- calcular_efeitos(df)
  eta <- function(n) 2 * qnorm((0.75 * n - 0.125) / (n + 0.25))
  m1 <- (9 + 12 + 16) / 3
  m2 <- (7 + 10 + 12) / 3
  s1 <- (16 - 9) / eta(25)
  s2 <- (12 - 7) / eta(40)
  sp <- sqrt((24 * s1^2 + 39 * s2^2) / 63)
  d <- (m1 - m2) / sp
  j <- 1 - 3 / (4 * 63 - 1)
  expect_equal(r$yi, j * d, tolerance = 1e-12)
  expect_equal(r$vi, j^2 * (65 / 1000 + d^2 / 130), tolerance = 1e-12)
  expect_equal(r$formula_id, "mediana_iqr_wan")
  expect_equal(r$aproximado, 1L)
  expect_equal(names(r)[seq_along(COLUNAS_EFEITOS_CALCULADOS)], COLUNAS_EFEITOS_CALCULADOS)
  expect_true(all(c("q1_1", "q3_1", "q1_2", "q3_2") %in% names(r)))
  # η(n) de Wan converge para o divisor 1,35 da Cochrane
  expect_equal(eta_wan(1e7), 2 * qnorm(0.75), tolerance = 1e-6)
  expect_equal(eta_wan(25), 2 * qnorm(18.625 / 25.25), tolerance = 1e-12)
  # mediana fora de [q1, q3] não é calculada
  df$q3_1 <- "11"
  expect_match(calcular_efeitos(df)$aviso, "fora de \\[q1, q3\\]")
  # quartis incompletos caem na aproximação por IQR (sd1/sd2)
  df2 <- linha_efeito(tipo_estatistica = "mediana_iqr", m1 = 12, sd1 = 4, n1 = 25, m2 = 10, sd2 = 4, n2 = 25)
  df2$q1_1 <- "9"
  r2 <- calcular_efeitos(df2)
  expect_equal(r2$formula_id, "mediana_iqr_aprox")
  expect_match(r2$aviso, "quartis incompletos")
})

test_that("sinal é alinhado pela direção desejada", {
  base <- list(tipo_estatistica = "md_sd", m1 = 10, sd1 = 2, n1 = 30, m2 = 12, sd2 = 2, n2 = 30)
  reduzir <- do.call(calc1, c(base, direcao_desejada = "reduzir"))
  aumentar <- do.call(calc1, c(base, direcao_desejada = "aumentar"))
  sem <- do.call(calc1, c(base, direcao_desejada = ""))
  expect_gt(reduzir$yi, 0)
  expect_equal(reduzir$sinal_alinhado, "invertido")
  expect_equal(reduzir$yi, -aumentar$yi)
  expect_equal(sem$sinal_alinhado, "sem_direcao")
  expect_match(sem$aviso, "direcao_desejada ausente")
})

test_that("revisões e meta-análises são rejeitadas como estudo", {
  r <- calc1(tipo_estatistica = "g", beta = 0.3, se = 0.1, desenho = "Meta-análise")
  expect_equal(r$formula_id, "rejeitado_revisao")
  expect_true(is.na(r$yi))
  r2 <- calc1(tipo_estatistica = "g", beta = 0.3, se = 0.1, desenho = "systematic review")
  expect_equal(r2$formula_id, "rejeitado_revisao")
})

test_that("|g| > 2 gera alerta de extração", {
  r <- calc1(tipo_estatistica = "md_sd", m1 = 20, sd1 = 2, n1 = 30, m2 = 10, sd2 = 2, n2 = 30)
  expect_match(r$aviso, "\\|g\\| > 2")
})

test_that("delineamento em cluster multiplica a variância pelo efeito de desenho", {
  base <- list(tipo_estatistica = "md_sd", m1 = 11, sd1 = 2, n1 = 100, m2 = 10, sd2 = 2, n2 = 100)
  sem <- do.call(calc1, base)
  com <- do.call(calc1, c(base, cluster = 20, icc = 0.05))
  expect_equal(com$vi, sem$vi * (1 + 19 * 0.05), tolerance = 1e-12)
  expect_equal(com$formula_id, "md_sd+de_cluster")
  sem_icc <- do.call(calc1, c(base, cluster = 20))
  expect_match(sem_icc$aviso, "sem tamanho médio")
})

test_that("vírgula decimal e tipo vazio são tratados", {
  r <- calc1(tipo_estatistica = "", m1 = "103,0", sd1 = "5,5", n1 = 50, m2 = "100", sd2 = "4,5", n2 = 50)
  expect_equal(r$formula_id, "md_sd")
  expect_equal(r$yi, 0.5924, tolerance = 1e-4)
  expect_match(r$aviso, "inferido")
})

test_that("colunas de saída seguem esquema.COLUNAS_EFEITOS_CALCULADOS e extras vão ao fim", {
  df <- linha_efeito(tipo_estatistica = "t", t = 2, n1 = 10, n2 = 10)
  df$rob_geral <- "baixo"
  saida <- calcular_efeitos(df)
  expect_equal(names(saida), c(COLUNAS_EFEITOS_CALCULADOS, "rob_geral"))
})

test_that("todo formula_id emitido está documentado em conversoes_efeito.csv", {
  mapa <- formulas_mapeadas()
  expect_false(is.null(mapa))
  emitidos <- c("md_sd", "t_ind", "t_ind_n_total", "f1_ind", "beta_sd", "or_logit", "r_d", "r_d_n_total",
                "parcial_r_d", "parcial_r_d_gl", "p_n_t", "g_informado", "d_informado", "mann_whitney_z",
                "mediana_iqr_wan", "mediana_iqr_aprox", "de_cluster", "dif_prop_contagens", "dif_prop_lpm", "rr_logit")
  expect_true(all(emitidos %in% mapa))
  codigo <- readLines(file.path(RS_DIR_R, "efeitos.R"), encoding = "UTF-8")
  literais <- unique(unlist(regmatches(codigo, gregexpr('"(md_sd|t_ind[a-z_]*|f1_ind|beta_sd|or_logit|r_d[a-z_]*|parcial_r_d[a-z_]*|p_n_t|[gd]_informado|mann_whitney_z|mediana_iqr_[a-z]+)"', codigo))))
  expect_true(all(gsub('"', "", literais) %in% mapa))
  expect_true(all(c('"r_d_n_total"', '"mediana_iqr_aprox"', '"mediana_iqr_wan"', '"parcial_r_d"', '"parcial_r_d_gl"')
                  %in% literais))
})

test_that("main_efeitos grava CSV e devolve resumo com contagens", {
  dir <- withr::local_tempdir()
  entrada <- file.path(dir, "in.csv")
  df <- rbind(
    linha_efeito(id_efeito = "E1", tipo_estatistica = "md_sd", m1 = 103, sd1 = 5.5, n1 = 50, m2 = 100, sd2 = 4.5, n2 = 50),
    linha_efeito(id_efeito = "E2", tipo_estatistica = "g", beta = 0.3, se = 0.1, desenho = "revisão sistemática"),
    linha_efeito(id_efeito = "E3", tipo_estatistica = "p_n", p = 0.2, n_total = 60, t = 1)
  )
  utils::write.csv(df, entrada, row.names = FALSE)
  saida <- file.path(dir, "out", "efeitos.csv")
  res <- main_efeitos(cli_args(c(paste0("--in=", entrada), paste0("--out=", saida))))
  expect_equal(res$codigo, 0L)
  expect_true(file.exists(saida))
  expect_equal(res$resumo$n_calculados, 2L)
  expect_equal(res$resumo$n_rejeitados_revisao, 1L)
  expect_equal(res$resumo$n_aproximados, 1L)
  expect_length(res$resumo$formulas_sem_mapa, 0L)
  lido <- ler_csv_texto(saida)
  expect_equal(names(lido), COLUNAS_EFEITOS_CALCULADOS)
})

test_that("regressão: n_ic_dentro_delta usa limites inclusivos, como rs.py caixa", {
  dir <- withr::local_tempdir()
  entrada <- file.path(dir, "in.csv")
  utils::write.csv(linha_efeito(id_efeito = "E1", tipo_estatistica = "g", beta = 0.05, se = 0.1), entrada, row.names = FALSE)
  hi <- 0.05 + qnorm(0.975) * 0.1  # o IC do efeito termina exatamente em δ
  res <- main_efeitos(cli_args(c(paste0("--in=", entrada), paste0("--out=", file.path(dir, "o.csv")),
                                 sprintf("--delta=%.17g", hi))))
  expect_equal(res$resumo$n_ic_dentro_delta, 1L)
})


# ---------------------------------------------------------------------------
# Desfechos binários (avaliação de políticas): diferença de proporções e RR -> d via log OR (Chinn 2000)
# ---------------------------------------------------------------------------

test_that("diferença de proporções com contagens reproduz escalc('OR') + Chinn e esc::esc_2x2", {
  r <- calc1(tipo_estatistica = "dif_prop", p1 = 0.6, p0 = 0.5, n1 = 500, n2 = 500, desenho = "RCT")
  # OR = (0,6/0,4)/(0,5/0,5) = 1,5; Var(ln OR) = 1/300 + 1/200 + 1/250 + 1/250
  log_or <- log(1.5)
  v_log <- 1 / 300 + 1 / 200 + 1 / 250 + 1 / 250
  j <- 1 - 3 / (4 * 998 - 1)
  expect_equal(r$yi, j * log_or * sqrt(3) / pi, tolerance = 1e-12)
  expect_equal(r$vi, j^2 * v_log * 3 / pi^2, tolerance = 1e-12)
  expect_equal(unname(round(log_or * sqrt(3) / pi, 5)), 0.22354)
  expect_equal(r$formula_id, "dif_prop_contagens")
  expect_equal(r$aproximado, 0L)
  skip_if_not_installed("metafor")
  ref <- metafor::escalc("OR", ai = 300, bi = 200, ci = 250, di = 250)
  expect_equal(r$yi / j, as.numeric(ref$yi) * sqrt(3) / pi, tolerance = 1e-12)
  expect_equal(r$vi / j^2, as.numeric(ref$vi) * 3 / pi^2, tolerance = 1e-12)
  skip_if_not_installed("esc")
  esc_ref <- esc::esc_2x2(grp1yes = 300, grp1no = 200, grp2yes = 250, grp2no = 250, es.type = "d")
  expect_equal(r$yi / j, esc_ref$es, tolerance = 1e-8)
  expect_equal(r$vi / j^2, esc_ref$var, tolerance = 1e-8)
})

test_that("efeito em pontos percentuais de DiD com p0 e EP em pp: método delta, aproximado", {
  r <- calc1(tipo_estatistica = "dif_prop", p0 = 0.40, efeito_pp = 5, se_pp = 2, desenho = "DiD",
             outcome = "evasão", direcao_desejada = "reduzir")
  p1 <- 0.45
  log_or <- log(p1 / (1 - p1)) - log(0.4 / 0.6)          # 0,204794
  v_log <- (0.02)^2 / (p1 * (1 - p1))^2                  # 0,0065299
  expect_equal(r$yi, -log_or * sqrt(3) / pi, tolerance = 1e-12)  # sem n: J = 1; "reduzir" inverte o sinal
  expect_equal(r$vi, v_log * 3 / pi^2, tolerance = 1e-12)
  expect_equal(unname(round(-r$yi, 5)), 0.11291)
  expect_equal(unname(round(r$vi, 7)), 0.0019849)
  expect_equal(r$formula_id, "dif_prop_lpm")
  expect_equal(r$aproximado, 1L)
  expect_equal(r$sinal_alinhado, "invertido")
  expect_match(r$aviso, "LPM/DiD/RDD")
  expect_match(r$aviso, "p0 \\+ efeito_pp/100")
})

test_that("LPM, DiD e RDD marcam aproximado mesmo com p1 observado; IC do efeito em pp substitui se_pp", {
  base <- calc1(tipo_estatistica = "dif_prop", p1 = 0.3, p0 = 0.2, n1 = 400, n2 = 400, desenho = "RCT")
  expect_equal(base$aproximado, 0L)
  for (marca in list(list(desenho = "RDD"), list(desenho = "diferenças em diferenças"),
                     list(modelo = "modelo de probabilidade linear (LPM), tabela 2"), list(estimando = "RDD_local"))) {
    r <- do.call(calc1, c(list(tipo_estatistica = "dif_prop", p1 = 0.3, p0 = 0.2, n1 = 400, n2 = 400), marca))
    expect_equal(r$formula_id, "dif_prop_lpm", info = paste(unlist(marca)))
    expect_equal(r$aproximado, 1L)
    expect_equal(r$yi, base$yi, tolerance = 1e-12)  # mesmo ponto; só a marca muda
  }
  com_ic <- calc1(tipo_estatistica = "dif_prop", p0 = 0.2, efeito_pp = 10, ci_lo = 6.08, ci_hi = 13.92, desenho = "RDD")
  com_se <- calc1(tipo_estatistica = "dif_prop", p0 = 0.2, efeito_pp = 10, se_pp = (13.92 - 6.08) / (2 * qnorm(0.975)),
                  desenho = "RDD")
  expect_equal(com_ic$vi, com_se$vi, tolerance = 1e-12)
})

test_that("diferença de proporções recusa percentual no lugar de proporção e p1 fora de (0, 1)", {
  r <- calc1(tipo_estatistica = "dif_prop", p0 = 40, efeito_pp = 5, se_pp = 2)
  expect_equal(r$formula_id, "sem_calculo")
  expect_match(r$aviso, "p0")
  r2 <- calc1(tipo_estatistica = "dif_prop", p0 = 0.97, efeito_pp = 5, se_pp = 2)
  expect_equal(r2$formula_id, "sem_calculo")
  expect_match(r2$aviso, "fora de \\(0, 1\\)")
  r3 <- calc1(tipo_estatistica = "dif_prop", p0 = 0.4, efeito_pp = 5)
  expect_equal(r3$formula_id, "sem_calculo")
  expect_match(r3$aviso, "se_pp")
})

test_that("tipo vazio com p0 e efeito_pp é inferido como dif_prop", {
  r <- calc1(tipo_estatistica = "", p0 = 0.4, efeito_pp = 5, se_pp = 2, desenho = "DiD")
  expect_equal(r$formula_id, "dif_prop_lpm")
  expect_match(r$aviso, "inferido 'dif_prop'")
})

test_that("RR com IC e p0 vira OR (Zhang & Yu) e d via log OR", {
  r <- calc1(tipo_estatistica = "rr", or_ = 1.25, ci_lo = 1.05, ci_hi = 1.49, p0 = 0.4, n_total = 800)
  # p1 = 1,25 × 0,4 = 0,5 -> OR = (0,5/0,5)/(0,4/0,6) = 1,5
  expect_equal(1.25 * 0.6 / (1 - 0.5), 1.5)
  se_log_rr <- (log(1.49) - log(1.05)) / (2 * qnorm(0.975))
  j <- 1 - 3 / (4 * 798 - 1)
  expect_equal(r$yi, j * log(1.5) * sqrt(3) / pi, tolerance = 1e-12)
  expect_equal(r$vi, j^2 * (se_log_rr / 0.5)^2 * 3 / pi^2, tolerance = 1e-12)
  expect_equal(r$formula_id, "rr_logit")
  expect_equal(r$aproximado, 1L)
  sem_p0 <- calc1(tipo_estatistica = "rr", or_ = 1.25, ci_lo = 1.05, ci_hi = 1.49)
  expect_equal(sem_p0$formula_id, "sem_calculo")
  expect_match(sem_p0$aviso, "p0")
  impossivel <- calc1(tipo_estatistica = "rr", or_ = 3, ci_lo = 2, ci_hi = 4, p0 = 0.5)
  expect_equal(impossivel$formula_id, "sem_calculo")
})
