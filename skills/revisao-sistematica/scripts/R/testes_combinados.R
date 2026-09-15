# testes_combinados.R — combinação de p-valores (análise SECUNDÁRIA, com ressalva obrigatória).
#
# USO
#     Rscript testes_combinados.R --in=06-analise/efeitos.csv --out-dir=06-analise \
#         [--grupo=construto_outcome|familia_intervencao,construto_outcome] [--separar-desenho=sim|nao] \
#         [--excluir-rob=nenhum|critico]
#
# Saídas em --out-dir:
#   testes_combinados.json                  resultado por grupo + ressalva
#   tabelas/testes_combinados.csv           uma linha por grupo × teste
#   tabelas/testes_combinados_estudos.csv   o p usado de cada estudo e sua fonte
#
# Testes (references/07a-sintese-quantitativa.md; Borenstein et al. 2009 cap. 36; Becker 1994)
# - Stouffer ponderado: z_i = Φ⁻¹(1 − p_i) com p_i UNILATERAL na direção declarada
#   (benefício); Z = Σ w_i z_i / √Σ w_i², w_i = √n_i; p = 1 − Φ(Z).
#   Estudos sem n ficam de fora (não recebem peso arbitrário).
# - Winer: Z = Σ t_i / √Σ [gl_i / (gl_i − 2)], com t alinhado à direção e só gl > 2
#   (a variância de t com gl graus de liberdade é gl/(gl − 2)). Usa t, não z: o script
#   de análise do REFIS usava z no numerador, o que torna o denominador incoerente. Sem t mas com
#   p e gl, t é reconstruído do p unilateral e contado à parte.
# - Cooper = teste de sinal binomial exato sobre a DIREÇÃO do estimador pontual.
# - Fisher: X² = −2 Σ ln p_i com p BILATERAL, gl = 2k. Rotulado "não direcional":
#   rejeitar H0 só diz que algum estudo tem efeito em alguma direção; efeitos
#   opostos se somam em vez de se cancelar.
# - Um p por estudo (modelo_principal); estudo com vários efeitos sem principal
#   bloqueia o grupo (exit 2), porque p dependentes inflam todos os testes.
# - Fonte do p unilateral, em ordem: t + gl (ou z do Mann-Whitney); p informado +
#   direção do estimador; yi/sei (normal). p = 0 informado é tratado como ausente.
#   Sem direcao_desejada não há p unilateral (Stouffer, Winer e Cooper ignoram o
#   estudo), mas o p bilateral ainda entra no Fisher.
# - Nunca definem rótulo da caixa de ferramentas; a ressalva sai no stdout e no JSON.
# - --excluir-rob=critico (mesmo contrato de meta.R): o p de cada estudo é escolhido antes
#   (modelo principal) e só depois o estudo com rob_geral crítico sai dos testes principais;
#   os testes com ele ficam em `sensibilidade.com_rob_critico` e a tabela de estudos marca
#   `excluido_rob_critico`.

.rs_dir_script <- function() {
  for (i in rev(seq_len(sys.nframe()))) {
    arquivo <- sys.frame(i)$ofile
    if (!is.null(arquivo)) return(dirname(normalizePath(arquivo)))
  }
  arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
  if (length(arg)) return(dirname(normalizePath(sub("^--file=", "", arg[1]))))
  getwd()
}
RS_DIR_R <- .rs_dir_script()
source(file.path(RS_DIR_R, "_cli.R"), encoding = "UTF-8")

RESSALVA_TESTES_COMBINADOS <- paste(
  "RESSALVA: testes combinados são análise secundária. Indicam se há evidência de algum",
  "efeito não nulo, mas não estimam magnitude, ignoram heterogeneidade, qualidade e viés de",
  "publicação, e são sensíveis ao número de estudos. O teste de Fisher é não direcional.",
  "Nunca definem sozinhos o rótulo da caixa de ferramentas (usar meta-análise ou SWiM + GRADE)."
)
P_MIN <- 1e-300

# ---------------------------------------------------------------------------
# p por estudo
# ---------------------------------------------------------------------------

#' p unilateral (na direção benéfica), p bilateral, t alinhado e fonte, por linha.
p_por_linha <- function(d) {
  t <- como_num(coluna(d, "t"))
  gl <- como_num(coluna(d, "df"))
  p <- como_num(coluna(d, "p"))
  yi <- como_num(coluna(d, "yi"))
  sei <- como_num(coluna(d, "sei"))
  fator <- fator_direcao(coluna(d, "direcao_desejada"))
  eh_z <- ascii_minusculo(coluna(d, "tipo_estatistica")) == "mann_whitney"
  alinhado <- coluna(d, "sinal_alinhado") %in% c("mantido", "invertido")
  dir <- direcao_linha(d)
  n <- nrow(d)
  p_uni <- rep(NA_real_, n)
  fonte <- rep("sem_p", n)
  t_al <- rep(NA_real_, n)
  for (i in seq_len(n)) {
    if (!is.na(t[i]) && !is.na(fator[i]) && eh_z[i]) {
      p_uni[i] <- stats::pnorm(t[i] * fator[i], lower.tail = FALSE)
      fonte[i] <- "z"
    } else if (!is.na(t[i]) && !is.na(fator[i]) && !is.na(gl[i]) && gl[i] > 0) {
      t_al[i] <- t[i] * fator[i]
      p_uni[i] <- stats::pt(t_al[i], gl[i], lower.tail = FALSE)
      fonte[i] <- "t"
    } else if (!is.na(p[i]) && p[i] > 0 && p[i] <= 1 && !is.na(dir[i]) && dir[i] != 0) {
      p_uni[i] <- if (dir[i] > 0) p[i] / 2 else 1 - p[i] / 2
      fonte[i] <- "p_informado"
    } else if (!is.na(yi[i]) && !is.na(sei[i]) && sei[i] > 0 && alinhado[i]) {
      p_uni[i] <- stats::pnorm(yi[i] / sei[i], lower.tail = FALSE)
      fonte[i] <- "yi_sei"
    }
  }
  p_uni <- pmin(pmax(p_uni, P_MIN), 1 - 1e-16)
  # p bilateral para o Fisher não depende de direção declarada: t/z, p informado ou yi/sei.
  p_bi <- ifelse(!is.na(t) & eh_z, 2 * stats::pnorm(-abs(t)),
          ifelse(!is.na(t) & !is.na(gl) & gl > 0, 2 * stats::pt(-abs(t), gl),
          ifelse(!is.na(p) & p > 0 & p <= 1, p,
          ifelse(!is.na(yi) & !is.na(sei) & sei > 0, 2 * stats::pnorm(-abs(yi / sei)), NA_real_))))
  t_rec <- ifelse(is.na(t_al) & !is.na(p_uni) & !is.na(gl) & gl > 2 & !eh_z,
                  stats::qt(p_uni, gl, lower.tail = FALSE), NA_real_)
  data.frame(
    id_estudo = d$.estudo, grupo = d$.grupo, chave = coluna(d, "chave"), id_efeito = coluna(d, "id_efeito"),
    fonte_p = fonte, p_unilateral = p_uni,
    p_bilateral = pmax(p_bi, P_MIN),
    direcao = dir, t_alinhado = t_al, t_reconstruido = t_rec, gl = gl, n = n_amostra(d),
    stringsAsFactors = FALSE
  )
}

# ---------------------------------------------------------------------------
# Testes (funções puras, testadas com vetores fixos)
# ---------------------------------------------------------------------------

#' Stouffer ponderado por √n com p unilateral.
stouffer_ponderado <- function(p_unilateral, n) {
  ok <- !is.na(p_unilateral) & !is.na(n) & n > 0
  k <- sum(ok)
  if (k == 0L) return(list(k = 0L, k_sem_n = sum(!is.na(p_unilateral) & (is.na(n) | n <= 0))))
  w <- sqrt(n[ok])
  z <- stats::qnorm(p_unilateral[ok], lower.tail = FALSE)
  Z <- sum(w * z) / sqrt(sum(w^2))
  list(k = k, k_sem_n = sum(!is.na(p_unilateral) & (is.na(n) | n <= 0)), Z = Z,
       p_unilateral = stats::pnorm(Z, lower.tail = FALSE),
       hipotese = "H1: efeito benéfico (direção declarada)", pesos = "sqrt(n)")
}

#' Winer: soma de t sobre a raiz da soma das variâncias de t (gl > 2).
winer <- function(t, gl, reconstruido = rep(FALSE, length(t))) {
  ok <- !is.na(t) & !is.na(gl) & gl > 2
  k <- sum(ok)
  if (k == 0L) return(list(k = 0L, k_excluidos_gl = sum(!is.na(t) & !(gl > 2 & !is.na(gl)))))
  Z <- sum(t[ok]) / sqrt(sum(gl[ok] / (gl[ok] - 2)))
  list(k = k, k_t_reconstruido = sum(reconstruido[ok]),
       k_excluidos_gl = sum(!is.na(t) & !(gl > 2 & !is.na(gl))),
       Z = Z, p_unilateral = stats::pnorm(Z, lower.tail = FALSE),
       hipotese = "H1: efeito benéfico (direção declarada)")
}

#' Cooper: teste de sinal binomial exato sobre a direção dos estimadores.
cooper_sinal <- function(direcao) {
  n_b <- sum(direcao > 0, na.rm = TRUE)
  n_d <- sum(direcao < 0, na.rm = TRUE)
  n <- n_b + n_d
  base <- list(n_benefico = n_b, n_danoso = n_d, n_nulo = sum(direcao == 0, na.rm = TRUE),
               n_sem_direcao = sum(is.na(direcao)))
  if (n == 0L) return(c(base, list(k = 0L)))
  bt <- stats::binom.test(n_b, n, p = 0.5, alternative = "two.sided")
  c(base, list(k = n, proporcao_benefica = n_b / n, ic = as.numeric(bt$conf.int),
               p_bilateral = as.numeric(bt$p.value), metodo = "binomial exato; IC Clopper-Pearson"))
}

#' Fisher com p bilateral: NÃO direcional.
fisher_nao_direcional <- function(p_bilateral) {
  p <- p_bilateral[!is.na(p_bilateral)]
  k <- length(p)
  if (k == 0L) return(list(k = 0L, rotulo = "não direcional"))
  X2 <- -2 * sum(log(pmax(p, P_MIN)))
  list(k = k, X2 = X2, gl = 2L * k, p = stats::pchisq(X2, 2L * k, lower.tail = FALSE),
       rotulo = "não direcional",
       nota = "rejeitar H0 indica efeito não nulo em algum estudo, em qualquer direção")
}

# ---------------------------------------------------------------------------
# Grupo e principal
# ---------------------------------------------------------------------------

#' Os quatro testes sobre a tabela de p por estudo (uma linha por estudo).
calcular_testes <- function(est) {
  t_winer <- ifelse(!is.na(est$t_alinhado), est$t_alinhado, est$t_reconstruido)
  list(
    stouffer_ponderado = stouffer_ponderado(est$p_unilateral, est$n),
    winer = winer(t_winer, est$gl, is.na(est$t_alinhado) & !is.na(est$t_reconstruido)),
    cooper_teste_de_sinal = cooper_sinal(est$direcao),
    fisher_nao_direcional = fisher_nao_direcional(est$p_bilateral)
  )
}

testar_grupo <- function(dg, rotulo, opcoes) {
  sel <- selecionar_um_por_estudo(dg, dg$.estudo)
  saida <- c(list(grupo = rotulo), atributos_grupo(dg, opcoes$grupo, opcoes$separar_desenho),
             list(metodo = "testes combinados (análise secundária)", n_linhas = nrow(dg)))
  if (length(sel$conflitos)) {
    saida$status <- "dependencia_nao_resolvida"
    saida$estudos_com_varios_efeitos <- as.list(sel$conflitos)
    saida$motivo <- "um p por estudo: marque modelo_principal nos estudos com vários efeitos"
    return(list(resumo = saida, estudos = NULL))
  }
  est_todos <- p_por_linha(dg[sel$manter, , drop = FALSE])
  # --excluir-rob=critico: fora dos testes principais DEPOIS da escolha de um p por estudo.
  critico <- if (identical(opcoes$excluir_rob, "critico")) {
    eh_rob_critico(coluna(dg[sel$manter, , drop = FALSE], "rob_geral"))
  } else {
    rep(FALSE, nrow(est_todos))
  }
  est_todos$excluido_rob_critico <- critico
  est <- est_todos[!critico, , drop = FALSE]
  saida$status <- "calculado"
  saida$k_estudos <- nrow(est)
  saida$k_sem_p <- sum(is.na(est$p_unilateral))
  saida$fontes_p <- as.list(table(est$fonte_p))
  saida$testes <- calcular_testes(est)
  if (identical(opcoes$excluir_rob, "critico")) {
    rob <- coluna(dg[sel$manter, , drop = FALSE], "rob_geral")
    saida$excluidos_rob_critico <- list(
      n_estudos = sum(critico), estudos = as.list(unique(est_todos$id_estudo[critico])),
      n_sem_rob_geral = sum(vazio(rob)),
      nota = "risco de viés crítico fora dos testes principais; os testes com esses estudos estão em sensibilidade$com_rob_critico"
    )
    saida$sensibilidade <- list(com_rob_critico = if (!any(critico)) {
      list(executado = FALSE, motivo = "nenhum estudo com risco de viés crítico no grupo")
    } else {
      list(executado = TRUE, n_incluidos = sum(critico), k_estudos = nrow(est_todos), testes = calcular_testes(est_todos))
    })
  }
  if (nrow(est) < 2L) saida$aviso <- "k < 2: testes combinados não fazem sentido"
  list(resumo = saida, estudos = est_todos)
}

linhas_tabela_testes <- function(g) {
  if (g$status != "calculado") {
    return(data.frame(grupo = g$grupo, teste = NA_character_, estatistica = NA_real_, gl = NA_real_,
                      k = NA_integer_, p = NA_real_, tipo_p = NA_character_, observacao = g$motivo))
  }
  tt <- g$testes
  v <- function(x) if (is.null(x)) NA_real_ else x
  data.frame(
    grupo = g$grupo,
    teste = c("Stouffer ponderado (sqrt n)", "Winer (t)", "Cooper (teste de sinal)", "Fisher (não direcional)"),
    estatistica = c(v(tt$stouffer_ponderado$Z), v(tt$winer$Z),
                    v(tt$cooper_teste_de_sinal$proporcao_benefica), v(tt$fisher_nao_direcional$X2)),
    gl = c(NA, NA, NA, v(tt$fisher_nao_direcional$gl)),
    k = c(tt$stouffer_ponderado$k, tt$winer$k, tt$cooper_teste_de_sinal$k, tt$fisher_nao_direcional$k),
    p = c(v(tt$stouffer_ponderado$p_unilateral), v(tt$winer$p_unilateral),
          v(tt$cooper_teste_de_sinal$p_bilateral), v(tt$fisher_nao_direcional$p)),
    tipo_p = c("unilateral (benefício)", "unilateral (benefício)", "bilateral", "não direcional"),
    observacao = c("", "", "estatística = proporção benéfica", ""),
    stringsAsFactors = FALSE
  )
}

executar_testes <- function(df, opcoes) {
  excluir <- linha_excluida_sintese(df)
  d <- df[!excluir, , drop = FALSE]
  if (!nrow(d)) cli_falhar("nenhuma linha elegível", SAIDA_ERRO_DADOS)
  d$.estudo <- id_estudo_efetivo(d)
  d$.grupo <- rotulo_grupo(d, opcoes$grupo, opcoes$separar_desenho)
  rotulos <- sort(unique(d$.grupo))
  res <- lapply(rotulos, function(r) testar_grupo(d[d$.grupo == r, , drop = FALSE], r, opcoes))
  estudos <- do.call(rbind, lapply(res, `[[`, "estudos"))
  list(grupos = lapply(res, `[[`, "resumo"), estudos = estudos, n_excluidos_revisao = sum(excluir),
       n_excluidos_rob_critico = if (is.null(estudos)) 0L else sum(estudos$excluido_rob_critico))
}

main_testes <- function(args) {
  entrada <- cli_arg(args, "in", obrigatorio = TRUE)
  opcoes <- list(
    out_dir = cli_arg(args, "out-dir", "06-analise"),
    grupo = cli_colunas_grupo(args),
    separar_desenho = cli_bool(args, "separar-desenho", TRUE),
    excluir_rob = cli_excluir_rob(args)
  )
  df <- ler_csv_texto(entrada)
  if (!nrow(df)) cli_falhar("entrada sem linhas", SAIDA_ERRO_DADOS)
  cli_excluir_rob(args, df)
  cat(RESSALVA_TESTES_COMBINADOS, "\n")
  res <- executar_testes(df, opcoes)

  arq_json <- file.path(opcoes$out_dir, "testes_combinados.json")
  arq_tab <- file.path(opcoes$out_dir, "tabelas", "testes_combinados.csv")
  arq_est <- file.path(opcoes$out_dir, "tabelas", "testes_combinados_estudos.csv")
  escrever_json(list(
    versao = "1", comando = "testes_combinados",
    gerado_em = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    entrada = entrada, ressalva = RESSALVA_TESTES_COMBINADOS,
    parametros = list(grupo = as.list(opcoes$grupo), separar_desenho = opcoes$separar_desenho,
                      excluir_rob = opcoes$excluir_rob),
    n_linhas_excluidas_revisao = res$n_excluidos_revisao,
    n_excluidos_rob_critico = res$n_excluidos_rob_critico,
    grupos = res$grupos
  ), arq_json)
  escrever_csv(do.call(rbind, lapply(res$grupos, linhas_tabela_testes)), arq_tab)
  if (!is.null(res$estudos)) escrever_csv(res$estudos, arq_est)

  status <- vapply(res$grupos, function(g) g$status, character(1))
  bloqueados <- sum(status == "dependencia_nao_resolvida")
  codigo <- if (bloqueados > 0L) SAIDA_CHECAGEM else SAIDA_OK
  message(sprintf("testes combinados: %d grupos (%d bloqueados por dependência)", length(status), bloqueados))
  list(codigo = codigo, resumo = list(
    ok = codigo == SAIDA_OK, comando = "testes_combinados", entrada = entrada, out_dir = opcoes$out_dir,
    resumo_json = arq_json, tabela = arq_tab, tabela_estudos = if (is.null(res$estudos)) NULL else arq_est,
    n_grupos = length(status), n_calculados = sum(status == "calculado"),
    n_dependencia_nao_resolvida = bloqueados, n_excluidos_revisao = res$n_excluidos_revisao,
    excluir_rob = opcoes$excluir_rob, n_excluidos_rob_critico = res$n_excluidos_rob_critico,
    ressalva = RESSALVA_TESTES_COMBINADOS
  ))
}

if (sys.nframe() == 0L) {
  quit(status = cli_executar(function() main_testes(cli_args())), save = "no")
}
