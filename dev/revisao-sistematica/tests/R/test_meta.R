# Testes de meta.R contra ajustes diretos do metafor em datasets conhecidos
# (dat.bcg, dat.assink2016) e das checagens metodológicas (k, dependência, desenho).

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
source(file.path(localizar_scripts_r(), "meta.R"), encoding = "UTF-8")

opcoes_padrao <- function(out_dir, ...) {
  o <- list(out_dir = out_dir, grupo = "construto_outcome", moderadores = character(0), k_min = 3L,
            dependencia = "um_por_estudo", rho = 0.6, delta = NULL, separar_desenho = TRUE)
  modifyList(o, list(...))
}

#' dat.bcg com sinal alinhado: log RR < 0 é benéfico (menos tuberculose), então yi = −log RR.
efeitos_bcg <- function() {
  dat <- metafor::escalc("RR", ai = tpos, bi = tneg, ci = cpos, di = cneg, data = metadat::dat.bcg)
  data.frame(
    id_efeito = paste0("E", dat$trial), chave = paste0(gsub("[^A-Za-z]", "", dat$author), dat$year),
    id_estudo = paste0("ES", dat$trial), desenho = "RCT", construto_outcome = "tuberculose",
    direcao_desejada = "reduzir", modelo_principal = "1",
    yi = as.character(-as.numeric(dat$yi)), vi = as.character(as.numeric(dat$vi)),
    sei = as.character(sqrt(as.numeric(dat$vi))), formula_id = "d_informado", aproximado = "0",
    sinal_alinhado = "invertido", ablat = as.character(dat$ablat), alloc = dat$alloc,
    stringsAsFactors = FALSE
  )
}

test_that("REML + HKSJ modificado reproduz metafor em dat.bcg", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  res <- executar_meta(efeitos_bcg(), opcoes_padrao(dir))
  expect_length(res$grupos, 1L)
  g <- res$grupos[[1]]
  expect_equal(g$status, "meta_ajustada")
  dat <- metafor::escalc("RR", ai = tpos, bi = tneg, ci = cpos, di = cneg, data = metadat::dat.bcg)
  ref <- metafor::rma(-yi, vi, data = dat, method = "REML", test = "adhoc")
  r <- g$resultado
  expect_equal(r$estimativa, as.numeric(ref$b), tolerance = 1e-8)
  expect_equal(r$estimativa, 0.7145323, tolerance = 1e-6)  # valor publicado do exemplo (sinal alinhado)
  expect_equal(r$ic, c(ref$ci.lb, ref$ci.ub), tolerance = 1e-8)
  expect_equal(r$tau2, 0.3132433, tolerance = 1e-6)
  expect_equal(r$I2, as.numeric(ref$I2), tolerance = 1e-8)
  expect_equal(r$Q, as.numeric(ref$QE), tolerance = 1e-8)
  ic_tau <- confint(ref)$random
  expect_equal(r$tau2_ic, as.numeric(ic_tau["tau^2", c("ci.lb", "ci.ub")]), tolerance = 1e-6)
  pred <- predict(ref, predtype = "Riley")
  expect_equal(r$pi, c(pred$pi.lb, pred$pi.ub), tolerance = 1e-8)
  # Riley: t com k − 2 gl
  meia <- qt(0.975, 11) * sqrt(ref$tau2 + ref$se^2)
  expect_equal(r$pi, as.numeric(ref$b) + c(-meia, meia), tolerance = 1e-8)
  expect_true(r$tau2_interpretavel)
  expect_equal(r$direcao, "benefica")
  expect_true(r$ic_exclui_zero)
  expect_true(r$pi_cobre_beneficio_e_dano)
  expect_equal(c(r$ic_inf, r$ic_sup), r$ic)
  expect_equal(c(r$ip_inf, r$ip_sup), r$pi)
  expect_true(r$direcao_alinhada)
  expect_equal(g$construto_outcome, "tuberculose")
  expect_equal(g$classe_desenho, "randomizado")
  expect_length(g$estudos, 13L)
})

test_that("viés de publicação roda com k >= 10 e bate com regtest", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  g <- executar_meta(efeitos_bcg(), opcoes_padrao(dir))$grupos[[1]]
  vp <- g$vies_publicacao
  expect_true(vp$executado)
  dat <- metafor::escalc("RR", ai = tpos, bi = tneg, ci = cpos, di = cneg, data = metadat::dat.bcg)
  ref <- metafor::regtest(metafor::rma(-yi, vi, data = dat, method = "REML", test = "adhoc"), model = "rma", predictor = "sei")
  expect_equal(vp$egger$p, ref$pval, tolerance = 1e-8)
  expect_true(file.exists(vp$funil))
  expect_true(vp$selecao_3psm$executado)
  expect_true(vp$pet_peese$escolhido %in% c("PET", "PEESE"))
  pet <- summary(lm(-dat$yi ~ sqrt(dat$vi), weights = 1 / dat$vi))$coefficients
  expect_equal(vp$pet_peese$pet_intercepto, pet[1, 1], tolerance = 1e-10)
  # variante WLS de Stanley & Doucouliagos documentada no JSON: EP escalado e t com k − 2 gl
  expect_match(vp$pet_peese$variante, "WLS")
  expect_match(vp$pet_peese$metodo, "k - 2 gl")
  expect_equal(vp$pet_peese$gl, nrow(dat) - 2L)
  expect_equal(vp$pet_peese$pet_ep, pet[1, 2], tolerance = 1e-10)
  expect_equal(vp$pet_peese$pet_t, pet[1, 3], tolerance = 1e-10)
  expect_equal(vp$pet_peese$pet_p, 2 * pt(-abs(pet[1, 3]), nrow(dat) - 2), tolerance = 1e-10)
  fe <- metafor::rma(-dat$yi, dat$vi, mods = ~ sqrt(dat$vi), method = "FE")
  expect_false(isTRUE(all.equal(vp$pet_peese$pet_ep, as.numeric(fe$se[1]))))  # não é a variante FE (escala 1, z)
  expect_false(grepl("cap\\. 08a|Apêndice B", vp$pet_peese$regra))
})

test_that("regra PET-PEESE: PEESE só com intercepto do PET positivo e p unilateral < 0,05 (cap. 08a)", {
  # unilateral 0,043 (bilateral 0,086) com intercepto positivo -> PEESE
  r <- regra_pet_peese(0.2, 1.9, 10, 0.15)
  expect_equal(r$escolhido, "PEESE")
  expect_equal(r$estimativa_corrigida, 0.15)
  expect_equal(r$pet_p_unilateral, pt(1.9, 10, lower.tail = FALSE))
  # mesmo |t| com intercepto negativo: bilateral < 0,10, mas não é efeito benéfico -> PET
  r <- regra_pet_peese(-0.2, -1.9, 10, -0.15)
  expect_equal(r$escolhido, "PET")
  expect_equal(r$estimativa_corrigida, -0.2)
  # positivo, mas unilateral 0,082 (bilateral 0,16) -> PET
  expect_equal(regra_pet_peese(0.2, 1.5, 10, 0.15)$escolhido, "PET")
  expect_match(r$regra, "positivo")
})

test_that("regressão: PET-PEESE no meta.R não escolhe PEESE com intercepto negativo significativo", {
  skip_if_not_installed("metafor")
  dir <- withr::local_tempdir()
  k <- 12
  se <- seq(0.05, 0.5, length.out = k)
  ruido <- c(0.01, -0.02, 0.015, -0.01, 0.02, -0.015, 0.005, -0.005, 0.01, -0.02, 0.015, -0.01)
  base <- function(yi) data.frame(
    id_efeito = paste0("E", seq_len(k)), chave = paste0("Autor", 2000 + seq_len(k)),
    id_estudo = paste0("ES", seq_len(k)), desenho = "RCT", construto_outcome = "nota",
    direcao_desejada = "aumentar", modelo_principal = "1",
    yi = as.character(yi), vi = as.character(se^2), sei = as.character(se),
    formula_id = "d_informado", aproximado = "0", sinal_alinhado = "mantido", stringsAsFactors = FALSE)
  y <- 0.3 + 1.2 * se + ruido
  pos <- executar_meta(base(y), opcoes_padrao(dir))$grupos[[1]]$vies_publicacao$pet_peese
  neg <- executar_meta(base(-y), opcoes_padrao(dir))$grupos[[1]]$vies_publicacao$pet_peese
  expect_gt(pos$pet_intercepto, 0)
  expect_lt(neg$pet_intercepto, 0)
  expect_lt(neg$pet_p, 0.10)  # a regra antiga (só p bilateral < 0,10) escolheria PEESE aqui
  expect_equal(pos$escolhido, "PEESE")
  expect_equal(pos$estimativa_corrigida, pos$peese_intercepto)
  expect_equal(neg$escolhido, "PET")
  expect_equal(neg$estimativa_corrigida, neg$pet_intercepto)
  expect_equal(pos$pet_p_unilateral, pos$pet_p / 2, tolerance = 1e-10)
  expect_equal(neg$pet_p_unilateral, 1 - neg$pet_p / 2, tolerance = 1e-10)
})

test_that("com k < 10 não há funil nem Egger", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  g <- executar_meta(efeitos_bcg()[1:6, ], opcoes_padrao(dir))$grupos[[1]]
  expect_equal(g$status, "meta_ajustada")
  expect_false(g$vies_publicacao$executado)
  expect_match(g$vies_publicacao$motivo, "k = 6 < 10")
})

test_that("tau² só é interpretável com k >= 5", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  g4 <- executar_meta(efeitos_bcg()[1:4, ], opcoes_padrao(dir))$grupos[[1]]
  g5 <- executar_meta(efeitos_bcg()[1:5, ], opcoes_padrao(dir))$grupos[[1]]
  expect_false(g4$resultado$tau2_interpretavel)
  expect_true(g5$resultado$tau2_interpretavel)
})

test_that("k abaixo de k-min não agrega", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  g <- executar_meta(efeitos_bcg()[1:2, ], opcoes_padrao(dir))$grupos[[1]]
  expect_equal(g$status, "k_insuficiente")
  expect_null(g$resultado)
})

test_that("estudo com vários efeitos sem modelo principal bloqueia o grupo (exit 2)", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  df <- efeitos_bcg()
  extra <- df[1, ]
  extra$id_efeito <- "E1b"
  df$modelo_principal[1] <- ""
  extra$modelo_principal <- ""
  df <- rbind(df, extra)
  g <- executar_meta(df, opcoes_padrao(dir))$grupos[[1]]
  expect_equal(g$status, "dependencia_nao_resolvida")
  expect_equal(unlist(g$estudos_com_varios_efeitos), "ES1")

  entrada <- file.path(dir, "efeitos.csv")
  utils::write.csv(df, entrada, row.names = FALSE)
  out <- main_meta(cli_args(c(paste0("--in=", entrada), paste0("--out-dir=", file.path(dir, "saida")))))
  expect_equal(out$codigo, 2L)
  expect_false(out$resumo$ok)
  expect_equal(out$resumo$n_dependencia_nao_resolvida, 1L)

  # Marcando o principal, o outro efeito é descartado e o grupo roda.
  df$modelo_principal[1] <- "1"
  g2 <- executar_meta(df, opcoes_padrao(dir))$grupos[[1]]
  expect_equal(g2$status, "meta_ajustada")
  expect_equal(g2$n_descartados_nao_principais, 1L)
})

test_that("randomizados e não randomizados viram grupos separados", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  df <- efeitos_bcg()
  df$desenho[1:6] <- "DiD"
  res <- executar_meta(df, opcoes_padrao(dir))
  rotulos <- vapply(res$grupos, function(g) g$grupo, character(1))
  expect_setequal(rotulos, c("tuberculose | nao_randomizado", "tuberculose | randomizado"))
  juntos <- executar_meta(df, opcoes_padrao(dir, separar_desenho = FALSE))
  expect_length(juntos$grupos, 1L)
  expect_match(unlist(juntos$grupos[[1]]$comparabilidade$avisos), "randomizados e não randomizados", all = FALSE)
})

test_that("linhas sem direção, sem efeito ou revisões ficam fora e são contadas", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  df <- efeitos_bcg()
  df$sinal_alinhado[1] <- "sem_direcao"
  df$yi[2] <- ""
  df$formula_id[3] <- "rejeitado_revisao"
  res <- executar_meta(df, opcoes_padrao(dir))
  expect_equal(res$excluidos$sem_direcao, 1L)
  expect_equal(res$excluidos$sem_efeito_calculado, 1L)
  expect_equal(res$excluidos$rejeitado_revisao, 1L)
  expect_equal(res$grupos[[1]]$k_estudos, 10L)
})

test_that("sensibilidades: leave-one-out, sem aproximados e sem alto risco", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  df <- efeitos_bcg()
  df$aproximado[1:2] <- "1"
  df$rob_geral <- c("baixo", "alto", "Crítico", rep("baixo", 10))
  g <- executar_meta(df, opcoes_padrao(dir))$grupos[[1]]
  s <- g$sensibilidade
  expect_true(s$leave_one_out$executado)
  expect_true(file.exists(s$leave_one_out$tabela))
  loo <- read.csv(s$leave_one_out$tabela)
  ref <- metafor::leave1out(metafor::rma(as.numeric(df$yi), as.numeric(df$vi), method = "REML", test = "adhoc"))
  expect_equal(loo$estimativa, as.numeric(ref$estimate), tolerance = 1e-6)
  expect_equal(s$sem_aproximados$n_removidos, 2L)
  expect_equal(s$sem_aproximados$k_estudos, 11L)
  expect_equal(s$sem_alto_risco$n_removidos, 2L)
})

test_that("delta só é avaliado quando informado", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  sem <- executar_meta(efeitos_bcg(), opcoes_padrao(dir))$grupos[[1]]$resultado
  com <- executar_meta(efeitos_bcg(), opcoes_padrao(dir, delta = 0.1))$grupos[[1]]$resultado
  expect_null(sem$ic_dentro_delta)
  expect_false(com$ic_dentro_delta)
  zero <- executar_meta(efeitos_bcg(), opcoes_padrao(dir, delta = 0))$grupos[[1]]$resultado
  expect_null(zero$ic_dentro_delta)  # δ = 0 é δ não declarado, como `if delta` em caixa.py
})

test_that("regressão: ic_dentro_delta é inclusivo e pi_cobre usa ±δ, como rs.py caixa", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  df <- efeitos_bcg()
  df$yi <- as.character(as.numeric(df$yi) / 20)  # efeitos pequenos: IC perto de zero
  df$vi <- as.character(as.numeric(df$vi) / 400)
  base <- executar_meta(df, opcoes_padrao(dir))$grupos[[1]]$resultado
  expect_equal(base$pi_referencia, "zero")
  # δ igual ao maior limite do IC: dentro com <= (a caixa rotula Nulo), fora com <
  delta_limite <- max(abs(base$ic))
  lim <- executar_meta(df, opcoes_padrao(dir, delta = delta_limite))$grupos[[1]]$resultado
  expect_true(lim$ic_dentro_delta)
  expect_equal(lim$ic, base$ic)
  # PI que cruza zero mas não chega a ±δ: não cobre benefício E dano relevantes
  pi <- base$pi
  expect_true(pi[1] < 0 && pi[2] > 0)
  delta_pi <- min(abs(pi)) * 1.01
  r <- executar_meta(df, opcoes_padrao(dir, delta = delta_pi))$grupos[[1]]$resultado
  expect_true(base$pi_cobre_beneficio_e_dano)
  expect_false(r$pi_cobre_beneficio_e_dano)
  expect_equal(r$pi_referencia, "delta")
  # no limite exato de ±δ, inclusivo (caixa: plo <= -delta and phi >= delta)
  r2 <- executar_meta(df, opcoes_padrao(dir, delta = min(abs(pi))))$grupos[[1]]$resultado
  expect_true(r2$pi_cobre_beneficio_e_dano)
})

test_that("regressão: Egger e PET-PEESE usam o EP modificado do SMD quando há n1/n2", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  bcg <- metadat::dat.bcg
  df <- efeitos_bcg()
  df$n1 <- as.character(bcg$tpos + bcg$tneg)
  df$n2 <- as.character(bcg$cpos + bcg$cneg)
  vp <- executar_meta(df, opcoes_padrao(dir))$grupos[[1]]$vies_publicacao
  expect_true(vp$executado)
  expect_equal(vp$preditor_precisao, "ep_modificado_smd")
  expect_equal(vp$egger$preditor, "ep_modificado_smd")
  n1 <- as.numeric(bcg$tpos + bcg$tneg)  # double: n1*n2 estoura inteiro
  n2 <- as.numeric(bcg$cpos + bcg$cneg)
  dat <- data.frame(yi = as.numeric(df$yi), vi = as.numeric(df$vi), se_mod = sqrt((n1 + n2) / (n1 * n2)))
  ref <- metafor::rma(yi, vi, mods = ~ se_mod, data = dat, method = "REML", test = "adhoc")
  expect_equal(vp$egger$p, as.numeric(ref$pval[2]), tolerance = 1e-8)
  expect_equal(vp$egger$estimativa_limite, as.numeric(ref$b[1]), tolerance = 1e-8)
  expect_equal(vp$egger$gl, 11)
  pet <- summary(lm(dat$yi ~ dat$se_mod, weights = 1 / dat$vi))$coefficients
  peese <- summary(lm(dat$yi ~ I(dat$se_mod^2), weights = 1 / dat$vi))$coefficients
  expect_equal(vp$pet_peese$pet_intercepto, pet[1, 1], tolerance = 1e-10)
  expect_equal(vp$pet_peese$peese_intercepto, peese[1, 1], tolerance = 1e-10)
  expect_equal(vp$pet_peese$preditor, "ep_modificado_smd")
  # o EP modificado muda o teste em relação ao EP de g
  sem_n <- executar_meta(efeitos_bcg(), opcoes_padrao(dir))$grupos[[1]]$vies_publicacao
  expect_equal(sem_n$preditor_precisao, "sei")
  expect_false(isTRUE(all.equal(sem_n$egger$p, vp$egger$p)))
  # um estudo sem n1 volta ao EP de g no grupo inteiro (não mistura preditores)
  df$n2[3] <- ""
  vp2 <- executar_meta(df, opcoes_padrao(dir))$grupos[[1]]$vies_publicacao
  expect_equal(vp2$preditor_precisao, "sei")
  expect_match(vp2$nota_preditor, "1 de 13 estudos sem n1 e n2")
})

test_that("n1/n2 por estudo para o CHE: só o valor único do estudo", {
  d <- data.frame(estudo = c("A", "A", "B", "B", "C"), n1 = c("10", "10", "5", "6", ""), n2 = c("12", "", "7", "7", "3"),
                  stringsAsFactors = FALSE)
  ns <- n_grupos_por_estudo(d, c("A", "B", "C"))
  expect_equal(unname(ns$n1), c(10, NA, NA))
  expect_equal(unname(ns$n2), c(12, 7, 3))
})

test_that("regressão: --excluir-rob=critico tira o crítico da análise principal e mantém sensibilidade", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  df <- efeitos_bcg()
  df$rob_geral <- c("baixo", "alto", "Crítico", rep("baixo", 10))
  sem_flag <- executar_meta(df, opcoes_padrao(dir))$grupos[[1]]
  g <- executar_meta(df, opcoes_padrao(dir, excluir_rob = "critico"))$grupos[[1]]
  expect_equal(g$status, "meta_ajustada")
  expect_equal(g$k_estudos, 12L)
  expect_equal(g$excluidos_rob_critico$n_linhas, 1L)
  expect_equal(unlist(g$excluidos_rob_critico$estudos), df$chave[3])
  ref <- metafor::rma(as.numeric(df$yi[-3]), as.numeric(df$vi[-3]), method = "REML", test = "adhoc")
  expect_equal(g$resultado$estimativa, as.numeric(ref$b), tolerance = 1e-8)
  s <- g$sensibilidade
  expect_true(s$com_rob_critico$executado)
  expect_equal(s$com_rob_critico$k_estudos, 13L)
  expect_equal(s$com_rob_critico$estimativa, sem_flag$resultado$estimativa, tolerance = 1e-8)
  expect_equal(s$sem_alto_risco$n_removidos, 1L)  # sensibilidade continua sobre a análise principal
  expect_true(s$leave_one_out$executado)
  expect_null(sem_flag$excluidos_rob_critico)

  # principal crítico não promove o modelo secundário do mesmo estudo
  extra <- df[1, ]
  extra$id_efeito <- "E1b"
  extra$modelo_principal <- ""
  extra$yi <- "5"
  df2 <- df
  df2$rob_geral[1] <- "critical"
  df2$rob_geral[3] <- "baixo"
  df2 <- rbind(df2, extra)
  g2 <- executar_meta(df2, opcoes_padrao(dir, excluir_rob = "critico"))$grupos[[1]]
  expect_equal(g2$n_descartados_nao_principais, 1L)
  expect_equal(g2$k_estudos, 12L)
  expect_false("ES1" %in% unlist(g2$estudos) || df$chave[1] %in% unlist(g2$estudos))

  # só críticos: k insuficiente, com o motivo
  df3 <- df[1:4, ]
  df3$rob_geral <- c("crítico", "crítico", "baixo", "baixo")
  g3 <- executar_meta(df3, opcoes_padrao(dir, excluir_rob = "critico"))$grupos[[1]]
  expect_equal(g3$status, "k_insuficiente")
  expect_match(g3$motivo, "RoB crítico")
})

test_that("main_meta: --excluir-rob valida valor e exige rob_geral; JSON traz contrato dos campos", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  entrada <- file.path(dir, "efeitos.csv")
  utils::write.csv(efeitos_bcg(), entrada, row.names = FALSE)
  expect_error(main_meta(cli_args(c(paste0("--in=", entrada), "--excluir-rob=alto"))), class = "rs_saida")
  expect_error(main_meta(cli_args(c(paste0("--in=", entrada), "--excluir-rob=critico",
                                    paste0("--out-dir=", file.path(dir, "a"))))), "rob_geral", class = "rs_saida")
  df <- efeitos_bcg()
  df$rob_geral <- c("baixo", "alto", "Crítico", rep("baixo", 10))
  utils::write.csv(df, entrada, row.names = FALSE)
  out_dir <- file.path(dir, "b")
  res <- main_meta(cli_args(c(paste0("--in=", entrada), paste0("--out-dir=", out_dir), "--excluir-rob=crítico",
                              "--delta=0.1")))
  expect_equal(res$codigo, 0L)
  expect_equal(res$resumo$n_excluidos_rob_critico, 1L)
  json <- jsonlite::fromJSON(file.path(out_dir, "meta_resumo.json"), simplifyVector = FALSE)
  expect_equal(json$parametros$excluir_rob, "critico")
  expect_match(json$contrato_campos$ic_dentro_delta, "-delta <= ic_inf")
  expect_match(json$contrato_campos$pi_cobre_beneficio_e_dano, "ip_inf <= -delta")
  expect_equal(json$grupos[[1]]$resultado$pi_referencia, "delta")
  tab <- utils::read.csv(file.path(out_dir, "tabelas", "meta_grupos.csv"))
  expect_equal(tab$n_excluidos_rob_critico, 1L)
})

test_that("moderadores: subgrupo exige k >= 3 por nível; contínuo exige ~10 estudos", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  g <- executar_meta(efeitos_bcg(), opcoes_padrao(dir, moderadores = c("alloc", "ablat", "inexistente")))$grupos[[1]]
  m <- g$moderadores$individuais
  expect_true(m$ablat$executado)
  dat <- metafor::escalc("RR", ai = tpos, bi = tneg, ci = cpos, di = cneg, data = metadat::dat.bcg)
  ref <- metafor::rma(-yi, vi, mods = ~ ablat, data = dat, method = "REML", test = "adhoc")
  expect_equal(m$ablat$QM_p, as.numeric(ref$QMp), tolerance = 1e-8)
  # alloc: alternate 2, random 7, systematic 4 -> um nível com k < 3 impede o subgrupo
  expect_false(m$alloc$executado)
  expect_match(m$alloc$motivo, "k >= 3 por nível")
  expect_false(m$inexistente$executado)
  expect_equal(m$inexistente$motivo, "coluna ausente")
  # sem o nível pequeno, o subgrupo roda e traz uma estimativa por nível
  df <- efeitos_bcg()
  df <- df[df$alloc != "alternate", ]
  g2 <- executar_meta(df, opcoes_padrao(dir, moderadores = "alloc"))$grupos[[1]]
  expect_true(g2$moderadores$individuais$alloc$executado)
  expect_length(g2$moderadores$individuais$alloc$subgrupos, 2L)
  expect_null(g2$moderadores$conjunto)
})

test_that("CHE + RVE CR2 reproduz robust(rma.mv) em dat.assink2016", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  skip_if_not_installed("clubSandwich")
  dir <- withr::local_tempdir()
  dat <- metadat::dat.assink2016
  df <- data.frame(
    id_efeito = paste0("E", seq_len(nrow(dat))), id_estudo = paste0("ES", dat$study),
    chave = paste0("Estudo", dat$study), desenho = "", construto_outcome = "delinquencia",
    direcao_desejada = "aumentar", yi = as.character(dat$yi), vi = as.character(dat$vi),
    sei = as.character(sqrt(dat$vi)), formula_id = "d_informado", aproximado = "0",
    sinal_alinhado = "mantido", stringsAsFactors = FALSE
  )
  g <- executar_meta(df, opcoes_padrao(dir, dependencia = "che", separar_desenho = FALSE))$grupos[[1]]
  expect_equal(g$status, "meta_ajustada")
  V <- metafor::vcalc(vi, cluster = study, obs = esid, data = dat, rho = 0.6)
  fit <- metafor::rma.mv(yi, V, random = ~ 1 | study / esid, data = dat, method = "REML", test = "t", dfs = "contain")
  rob <- metafor::robust(fit, cluster = dat$study, clubSandwich = TRUE)
  ct <- clubSandwich::coef_test(fit, vcov = "CR2", cluster = dat$study)
  r <- g$resultado
  expect_equal(r$estimativa, as.numeric(rob$b), tolerance = 1e-6)
  expect_equal(r$ep, ct$SE, tolerance = 1e-6)
  expect_equal(r$gl, ct$df_Satt, tolerance = 1e-4)
  expect_equal(r$k_estudos, 17L)
  expect_equal(r$k_efeitos, 100L)
  expect_true(r$rve_confiavel)
  expect_length(g$sensibilidade$rho, 3L)
  expect_true(g$vies_publicacao$executado)  # 17 estudos agregados
})

test_that("main_meta grava JSON, tabela e forest (PNG e PDF)", {
  skip_if_not_installed("metafor"); skip_if_not_installed("metadat")
  dir <- withr::local_tempdir()
  entrada <- file.path(dir, "efeitos.csv")
  utils::write.csv(efeitos_bcg(), entrada, row.names = FALSE)
  out_dir <- file.path(dir, "06-analise")
  res <- main_meta(cli_args(c(paste0("--in=", entrada), paste0("--out-dir=", out_dir))))
  expect_equal(res$codigo, 0L)
  expect_true(file.exists(file.path(out_dir, "meta_resumo.json")))
  expect_true(file.exists(file.path(out_dir, "tabelas", "meta_grupos.csv")))
  pdfs <- list.files(file.path(out_dir, "figuras"), pattern = "^forest_.*\\.pdf$")
  pngs <- list.files(file.path(out_dir, "figuras"), pattern = "^forest_.*\\.png$")
  expect_length(pdfs, 1L)
  expect_length(pngs, 1L)
  json <- jsonlite::fromJSON(file.path(out_dir, "meta_resumo.json"), simplifyVector = FALSE)
  expect_equal(json$grupos[[1]]$status, "meta_ajustada")
  expect_equal(json$parametros$dependencia, "um_por_estudo")
  expect_equal(json$parametros$delta_fonte, "nao_informado")
})

test_that("argumentos inválidos saem com código 1", {
  dir <- withr::local_tempdir()
  expect_error(main_meta(cli_args(c("--in=x.csv", "--dependencia=outra"))), class = "rs_saida")
  codigo <- suppressMessages(capture.output(
    cod <- cli_executar(function() main_meta(cli_args(c(paste0("--in=", file.path(dir, "nao_existe.csv"))))))
  ))
  expect_equal(cod, 1L)
})
