# Testes de swim.R: direção por estudo, teste de sinal exato e gráficos.

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
source(file.path(localizar_scripts_r(), "swim.R"), encoding = "UTF-8")

efeitos_swim <- function() {
  data.frame(
    id_efeito = paste0("E", 1:9),
    id_estudo = c("S1", "S2", "S3", "S4", "S5", "S6", "S6", "S6", "S7"),
    chave = c("A2020", "B2020", "C2020", "D2020", "E2020", "F2020", "F2020", "F2020", "G2020"),
    desenho = "DiD", construto_outcome = "renda", direcao_desejada = "aumentar",
    modelo_principal = "",
    yi = c("0.3", "0.1", "-0.2", "0.05", "0.4", "0.2", "0.1", "-0.3", ""),
    sei = c("0.1", "0.2", "0.1", "0.05", "0.2", "0.1", "0.1", "0.1", ""),
    sinal_alinhado = c(rep("mantido", 8), ""),
    formula_id = c(rep("md_sd", 8), "sem_calculo"),
    p = c("", "", "", "", "", "", "", "", "0.02"), beta = c(rep("", 8), "1.5"),
    n_total = c("200", "80", "150", "900", "60", "300", "300", "300", "1200"),
    rob_geral = c("baixo", "alto", "baixo", "alto", "algumas preocupações", "baixo", "baixo", "baixo", ""),
    stringsAsFactors = FALSE
  )
}

test_that("direção do estudo: modelo principal, efeito único e regra de 70%", {
  expect_equal(direcao_estudo(c(1, -1), c(FALSE, TRUE))$direcao, "danoso")
  expect_equal(direcao_estudo(c(1, 1, -1), c(FALSE, FALSE, FALSE))$direcao, "misto")  # 67% < 70%
  expect_equal(direcao_estudo(c(1, 1, 1, -1), c(FALSE, FALSE, FALSE, FALSE))$direcao, "benefico")  # 75%
  expect_equal(direcao_estudo(c(-1, -1, -1, NA), rep(FALSE, 4))$direcao, "danoso")
  expect_equal(direcao_estudo(c(NA, NA), c(FALSE, FALSE))$direcao, "sem_direcao")
  expect_equal(direcao_estudo(c(0, 0), c(FALSE, FALSE))$direcao, "nulo")
})

test_that("direção vem do estimador, não da significância", {
  df <- data.frame(yi = c("0.01", "-0.5"), sei = c("10", "0.01"), sinal_alinhado = "mantido",
                   direcao_desejada = "aumentar", stringsAsFactors = FALSE)
  expect_equal(direcao_linha(df), c(1, -1))
  bruto <- data.frame(t = c("-2", "1"), direcao_desejada = c("reduzir", ""), stringsAsFactors = FALSE)
  expect_equal(direcao_linha(bruto), c(1, NA))
})

test_that("teste de sinal é o binomial exato com IC de Clopper-Pearson", {
  r <- teste_sinal(8L, 2L)
  ref <- binom.test(8, 10, 0.5)
  expect_equal(r$p_bilateral, ref$p.value)
  expect_equal(r$ic, as.numeric(ref$conf.int))
  expect_equal(r$proporcao_benefica, 0.8)
  expect_null(teste_sinal(0L, 0L)$p_bilateral)
})

test_that("executar_swim conta direções por estudo e prepara insumos da caixa", {
  dir <- withr::local_tempdir()
  res <- executar_swim(efeitos_swim(), list(out_dir = dir, grupo = "construto_outcome", limiar = 0.7,
                                            nivel = 0.95, separar_desenho = TRUE))
  expect_length(res$grupos, 1L)
  g <- res$grupos[[1]]
  expect_equal(g$k_estudos, 7L)
  # S1, S2, S4, S5, S7 (só p e beta positivo) benéficos; S3 danoso; S6 com 2/3 = misto
  expect_equal(g$n_beneficos, 5L)
  expect_equal(g$n_danosos, 1L)
  expect_equal(g$n_mistos, 1L)
  expect_equal(g$n_estudos, 6L)  # só os que entram no teste de sinal
  expect_equal(g$proporcao_benefica, 5 / 6)
  expect_equal(g$p_sinal, binom.test(5, 6)$p.value)
  expect_equal(g$teste_sinal$p_bilateral, binom.test(5, 6)$p.value)
  expect_true(g$insumos_regra_caixa$atinge_k)
  expect_true(g$insumos_regra_caixa$atinge_proporcao_benefica)
  expect_false(g$insumos_regra_caixa$p_menor_005)
  expect_false(g$so_risco_alto)
  expect_equal(g$construto_outcome, "renda")
  expect_equal(g$classe_desenho, "nao_randomizado")
  expect_length(g$estudos, 7L)
  tab <- res$tabela
  expect_equal(tab$direcao[tab$id_estudo == "S6"], "misto")
  expect_equal(tab$regra[tab$id_estudo == "S6"], "consistencia<70%")
})

test_that("modelo_principal define a direção do estudo com vários efeitos", {
  dir <- withr::local_tempdir()
  df <- efeitos_swim()
  df$modelo_principal[8] <- "sim"
  res <- executar_swim(df, list(out_dir = dir, grupo = "construto_outcome", limiar = 0.7, nivel = 0.95,
                                separar_desenho = TRUE))
  expect_equal(res$tabela$direcao[res$tabela$id_estudo == "S6"], "danoso")
})

test_that("revisões ficam fora da SWiM", {
  dir <- withr::local_tempdir()
  df <- efeitos_swim()
  df$desenho[1] <- "revisão sistemática"
  res <- executar_swim(df, list(out_dir = dir, grupo = "construto_outcome", limiar = 0.7, nivel = 0.95,
                                separar_desenho = TRUE))
  expect_equal(res$n_excluidos_revisao, 1L)
  expect_equal(res$grupos[[1]]$k_estudos, 6L)
})

test_that("main_swim grava JSON, tabela, effect direction plot e albatross", {
  dir <- withr::local_tempdir()
  entrada <- file.path(dir, "efeitos.csv")
  utils::write.csv(efeitos_swim(), entrada, row.names = FALSE)
  out_dir <- file.path(dir, "06-analise")
  res <- main_swim(cli_args(c(paste0("--in=", entrada), paste0("--out-dir=", out_dir))))
  expect_equal(res$codigo, 0L)
  expect_true(file.exists(file.path(out_dir, "swim_resumo.json")))
  expect_true(file.exists(file.path(out_dir, "tabelas", "swim_direcao.csv")))
  expect_true(file.exists(file.path(out_dir, "figuras", "direcao_efeito.pdf")))
  expect_true(file.exists(file.path(out_dir, "figuras", "direcao_efeito.png")))
  albatross <- list.files(file.path(out_dir, "figuras"), pattern = "^albatross_")
  expect_length(albatross, 1L)
  json <- jsonlite::fromJSON(file.path(out_dir, "swim_resumo.json"), simplifyVector = FALSE)
  expect_equal(json$grupos[[1]]$albatross$n_so_p, 1L)
})

test_that("limiar de consistência inválido sai com erro de uso", {
  expect_error(main_swim(cli_args(c("--in=x.csv", "--limiar-consistencia=0.4"))), class = "rs_saida")
})

test_that("so_risco_alto: nulo sem RoB, TRUE só se todos os estudos com direção são de risco alto", {
  tab <- data.frame(grupo = "g", id_estudo = c("A", "B", "C"), chave = "", direcao = c("benefico", "benefico", "misto"),
                    rob_geral = c("alto", "Crítico", "baixo"), stringsAsFactors = FALSE)
  expect_true(resumir_grupo(tab, 0.95)$so_risco_alto)
  tab$rob_geral <- ""
  expect_null(resumir_grupo(tab, 0.95)$so_risco_alto)
  tab$rob_geral <- c("alto", "baixo", "")
  expect_false(resumir_grupo(tab, 0.95)$so_risco_alto)
})

test_that("--grupo aceita várias colunas e expõe cada uma no JSON", {
  dir <- withr::local_tempdir()
  df <- efeitos_swim()
  df$familia_intervencao <- c(rep("transferencia", 5), rep("credito", 4))
  res <- executar_swim(df, list(out_dir = dir, grupo = c("familia_intervencao", "construto_outcome"),
                                limiar = 0.7, nivel = 0.95, separar_desenho = TRUE))
  expect_length(res$grupos, 2L)
  familias <- vapply(res$grupos, function(g) g$familia_intervencao, character(1))
  expect_setequal(familias, c("transferencia", "credito"))
  expect_true(all(vapply(res$grupos, function(g) g$construto_outcome == "renda", logical(1))))
  expect_equal(cli_colunas_grupo(cli_args("--grupo=")), character(0))
  expect_equal(cli_colunas_grupo(cli_args(character(0))), "construto_outcome")
})

test_that("regressão: --excluir-rob=critico tira o estudo crítico do teste de sinal e guarda a sensibilidade", {
  dir <- withr::local_tempdir()
  df <- efeitos_swim()
  df$rob_geral[1] <- "Crítico"   # S1 benéfico, crítico
  df$rob_geral[6:8] <- c("baixo", "critico", "baixo")  # S6: o principal (linha 8) não é crítico
  df$modelo_principal[8] <- "sim"
  opc <- list(out_dir = dir, grupo = "construto_outcome", limiar = 0.7, nivel = 0.95, separar_desenho = TRUE)
  sem <- executar_swim(df, opc)$grupos[[1]]
  res <- executar_swim(df, c(opc, list(excluir_rob = "critico")))
  g <- res$grupos[[1]]
  expect_equal(g$k_estudos, sem$k_estudos - 1L)
  expect_equal(g$n_beneficos, sem$n_beneficos - 1L)
  expect_equal(g$excluidos_rob_critico$n_estudos, 1L)
  expect_equal(unlist(g$excluidos_rob_critico$estudos), "A2020")
  expect_equal(g$sensibilidade$com_rob_critico$n_beneficos, sem$n_beneficos)
  expect_equal(g$sensibilidade$com_rob_critico$p_sinal, sem$p_sinal)
  expect_equal(g$p_sinal, binom.test(g$n_beneficos, g$n_estudos)$p.value)
  # a direção de S6 vem do modelo principal (danoso) e o RoB do estudo é o do principal: S6 fica
  expect_equal(res$tabela$direcao[res$tabela$id_estudo == "S6"], "danoso")
  expect_false(res$tabela$excluido_rob_critico[res$tabela$id_estudo == "S6"])
  expect_equal(res$n_excluidos_rob_critico, 1L)
  expect_null(sem$excluidos_rob_critico)
})

test_that("main_swim: --excluir-rob valida a opção, exige rob_geral e grava no JSON", {
  dir <- withr::local_tempdir()
  df <- efeitos_swim()
  df$rob_geral[5] <- "critical"
  entrada <- file.path(dir, "efeitos.csv")
  utils::write.csv(df, entrada, row.names = FALSE)
  out_dir <- file.path(dir, "06-analise")
  res <- main_swim(cli_args(c(paste0("--in=", entrada), paste0("--out-dir=", out_dir), "--excluir-rob=critico")))
  expect_equal(res$codigo, 0L)
  expect_equal(res$resumo$n_excluidos_rob_critico, 1L)
  json <- jsonlite::fromJSON(file.path(out_dir, "swim_resumo.json"), simplifyVector = FALSE)
  expect_equal(json$parametros$excluir_rob, "critico")
  expect_true(json$grupos[[1]]$sensibilidade$com_rob_critico$executado)
  tab <- read.csv(file.path(out_dir, "tabelas", "swim_direcao.csv"))
  expect_equal(sum(tab$excluido_rob_critico), 1L)
  expect_error(main_swim(cli_args(c(paste0("--in=", entrada), "--excluir-rob=alto"))), class = "rs_saida")
  sem_rob <- df[, setdiff(names(df), "rob_geral")]
  utils::write.csv(sem_rob, entrada, row.names = FALSE)
  expect_error(main_swim(cli_args(c(paste0("--in=", entrada), paste0("--out-dir=", out_dir), "--excluir-rob=critico"))),
               "rob_geral", class = "rs_saida")
})
