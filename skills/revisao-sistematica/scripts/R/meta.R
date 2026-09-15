# meta.R — meta-análise de efeitos aleatórios por grupo comparável.
#
# USO
#     Rscript meta.R --in=06-analise/efeitos.csv --out-dir=06-analise \
#         [--grupo=construto_outcome|familia_intervencao,construto_outcome] \
#         [--moderadores=x,y] [--k-min=3] \
#         [--dependencia=um_por_estudo|che] [--rho=0.6] [--delta=0.1] \
#         [--separar-desenho=sim|nao] [--excluir-rob=nenhum|critico]
#
# Entrada: saída de efeitos.R (yi alinhado: positivo = benéfico). Saídas em --out-dir:
#   meta_resumo.json                 resumo por grupo (lido por `rs.py caixa`)
#   tabelas/meta_grupos.csv          uma linha por grupo
#   tabelas/loo_<grupo>.csv          leave-one-out
#   figuras/forest_<grupo>.png|pdf   forest plot com intervalo de predição
#   figuras/funil_<grupo>.png        só com k >= 10
#
# Por que assim (references/07a-sintese-quantitativa.md; Apêndice D da base de conhecimento, itens 4, 5 e 7;
# Cochrane Handbook v6.5 cap. 10)
# - Grupo = construto do outcome × classe de desenho: randomizados e não
#   randomizados nunca são agregados juntos (desligável com --separar-desenho=nao).
# - k >= 3 estudos para agregar; τ² só é "interpretável" com k >= 5 (fica no JSON).
# - Modelo: efeitos aleatórios REML com Hartung-Knapp-Sidik-Jonkman modificado
#   (metafor test="adhoc": o EP ajustado nunca fica menor que o do método padrão),
#   τ² com IC (Q-profile), I², Q e intervalo de predição com t de k − 2 gl (Riley 2011).
# - Dependência: por padrão um efeito por estudo, escolhido pela coluna
#   modelo_principal (regra do protocolo). Estudo com várias linhas sem um único
#   modelo principal bloqueia o grupo (exit 2) em vez de o script escolher sozinho.
#   Com --dependencia=che: modelo correlated-hierarchical effects (rma.mv, estudo/efeito,
#   V imputada com ρ) + inferência robusta CR2 com gl de Satterthwaite (clubSandwich);
#   gl < 4 é marcado como não confiável; sensibilidade a ρ ∈ {0,2; 0,5; 0,8}.
# - Viés de publicação (funil, Egger, PET-PEESE, seleção 3PSM) só com k >= 10;
#   no CHE esses diagnósticos usam efeitos agregados por estudo (aggregate.escalc).
#   Como yi é diferença padronizada (g), Egger e PET-PEESE usam o EP modificado
#   √((n1+n2)/(n1·n2)) de Pustejovsky & Rodgers (2019) quando todos os estudos têm n1 e
#   n2: o EP de g depende do próprio g e infla o erro tipo I (Cochrane 13.3).
#   Sem n1/n2 em algum estudo, volta ao EP de g e o JSON diz qual preditor foi usado.
#   PET-PEESE na variante WLS de Stanley & Doucouliagos (2014): stats::lm(yi ~ EP) e
#   lm(yi ~ EP²) ponderados por 1/vi, com erro multiplicativo (EP dos coeficientes escalado
#   pela variância residual) e t com k − 2 gl; não é o rma(method = "FE"), que fixa a escala
#   em 1 e usa z. PEESE só com intercepto do PET positivo e p unilateral < 0,05. O JSON traz
#   `variante`, `gl`, `pet_t`, pet_p_unilateral e a regra.
# - Sensibilidade: leave-one-out, sem conversões aproximadas, sem risco de viés
#   alto/crítico (coluna rob_geral, se houver).
# - --excluir-rob=critico tira da análise PRINCIPAL as linhas com rob_geral crítico
#   (ROBINS-I "critical": Cochrane cap. 24 recomenda não sintetizá-las); a análise com
#   elas vira a sensibilidade `com_rob_critico` e as demais sensibilidades continuam.
#   A seleção de um efeito por estudo é feita antes da exclusão, para que retirar o
#   modelo principal crítico não promova um modelo secundário.
# - Subgrupo exige k >= 3 por nível; meta-regressão contínua ~10 estudos por covariável.
# - Com --delta (SESOI fixado a priori), informa se o IC inteiro cabe em ±δ;
#   sem --delta, o campo fica nulo: equivalência não se decide a posteriori.
#   Os campos ic_dentro_delta e pi_cobre_beneficio_e_dano usam o mesmo critério das
#   regras Nulo e Misto de rslib/caixa.py (limites inclusivos); o contrato vai no JSON
#   em `contrato_campos`.
# - Sem fallback caseiro: sem metafor o script sai com código 3.

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

K_TAU2_INTERPRETAVEL <- 5L
K_VIES_PUBLICACAO <- 10L
K_POR_NIVEL_SUBGRUPO <- 3L
ESTUDOS_POR_COVARIAVEL <- 10L
GL_RVE_MINIMO <- 4
RHOS_SENSIBILIDADE <- c(0.2, 0.5, 0.8)
PADRAO_ALTO_RISCO <- "alto|high|critico|critical|serio|serious|grave"

#' Contrato dos campos derivados de δ (espelha rotular_efeito() de rslib/caixa.py, regra caixa-3).
CONTRATO_CAMPOS <- list(
  ic_dentro_delta = paste(
    "TRUE se -delta <= ic_inf e ic_sup <= delta (limites inclusivos, igual à regra Nulo de rs.py caixa);",
    "null sem --delta > 0"),
  pi_cobre_beneficio_e_dano = paste(
    "com --delta > 0: ip_inf <= -delta e ip_sup >= delta (condição de IP da regra Misto de rs.py caixa, que exige",
    "também k >= 5 e achado explicativo com CERQual >= baixa);",
    "sem delta: ip_inf < 0 < ip_sup; null sem intervalo de predição.",
    "pi_referencia diz qual critério foi usado ('delta' ou 'zero')"),
  observacao = paste(
    "rs.py caixa recalcula as regras a partir de ic/ip e do delta da célula (certeza.csv ou --delta);",
    "estes campos são descritivos e só coincidem com a caixa quando o delta é o mesmo")
)

#' PET-PEESE: variante adotada (documentada no JSON de cada grupo).
VARIANTE_PET_PEESE <- list(
  nome = "WLS (Stanley & Doucouliagos 2014)",
  metodo = paste(
    "stats::lm(yi ~ EP) (PET) e lm(yi ~ EP^2) (PEESE) ponderados por 1/vi: erro multiplicativo",
    "(EP dos coeficientes escalado pela variância residual) e teste t com k - 2 gl;",
    "não é rma(method = 'FE'), que fixa a escala em 1 e usa z")
)

#' δ válido para os critérios de equivalência: número finito > 0 (como `if delta` em caixa.py).
delta_valido <- function(delta) {
  !is.null(delta) && length(delta) == 1L && is.finite(delta) && delta > 0
}

# ---------------------------------------------------------------------------
# Preparação
# ---------------------------------------------------------------------------

#' Mantém só linhas analisáveis e conta os motivos de exclusão.
preparar_dados_meta <- function(df) {
  df <- completar_colunas(df, COLUNAS_EFEITOS_CALCULADOS)
  yi <- como_num(df$yi)
  vi <- como_num(df$vi)
  fid <- coluna(df, "formula_id")
  sinal <- coluna(df, "sinal_alinhado")
  motivos <- list(
    rejeitado_revisao = sum(fid == "rejeitado_revisao"),
    sem_efeito_calculado = sum(fid != "rejeitado_revisao" & (is.na(yi) | is.na(vi) | vi <= 0)),
    sem_direcao = sum(!is.na(yi) & !is.na(vi) & vi > 0 & fid != "rejeitado_revisao" &
                        !sinal %in% c("mantido", "invertido"))
  )
  ok <- fid != "rejeitado_revisao" & !is.na(yi) & !is.na(vi) & vi > 0 & sinal %in% c("mantido", "invertido")
  d <- df[ok, , drop = FALSE]
  d$yi <- yi[ok]
  d$vi <- vi[ok]
  d$estudo <- id_estudo_efetivo(d)
  d$efeito <- seq_len(nrow(d))
  chave <- coluna(d, "chave")
  d$rotulo <- ifelse(vazio(chave), d$estudo, chave)
  d$aproximado_num <- como_num(coluna(d, "aproximado"))
  list(dados = d, excluidos = motivos)
}

#' Descreve o que foi agregado, para o checklist de comparabilidade.
comparabilidade <- function(d) {
  valores <- function(col) {
    v <- unique(coluna(d, col))
    as.list(sort(v[!vazio(v)]))
  }
  estimandos <- tolower(unlist(valores("estimando")))
  avisos <- character(0)
  if (length(estimandos) > 1L) {
    avisos <- c(avisos, "estimandos diferentes no mesmo grupo: conferir comparabilidade (ATE × ITT/LATE/local)")
  }
  if (length(unique(classe_desenho(coluna(d, "desenho")))) > 1L) {
    avisos <- c(avisos, "randomizados e não randomizados agregados juntos")
  }
  if (length(unlist(valores("outcome"))) > 1L) {
    avisos <- c(avisos, "vários outcomes no mesmo construto: conferir se medem o mesmo conceito")
  }
  list(estimandos = valores("estimando"), desenhos = valores("desenho"),
       outcomes = valores("outcome"), avisos = as.list(avisos))
}

# ---------------------------------------------------------------------------
# Ajuste
# ---------------------------------------------------------------------------

#' Tenta o ajuste REML e, se não convergir, repete com passos menores.
tentar_ajuste <- function(expr_fn) {
  primeiro <- tryCatch(expr_fn(list()), error = function(e) e)
  if (!inherits(primeiro, "error")) return(primeiro)
  segundo <- tryCatch(expr_fn(list(stepadj = 0.5, maxiter = 1000)), error = function(e) e)
  if (!inherits(segundo, "error")) return(segundo)
  stop(conditionMessage(primeiro))
}

ajustar_uni <- function(d, mods = NULL) {
  tentar_ajuste(function(ctrl) {
    if (is.null(mods)) {
      metafor::rma(yi, vi, data = d, method = "REML", test = "adhoc", slab = d$rotulo, control = ctrl)
    } else {
      metafor::rma(yi, vi, mods = mods, data = d, method = "REML", test = "adhoc", control = ctrl)
    }
  })
}

ajustar_che <- function(d, rho, mods = NULL) {
  V <- metafor::vcalc(vi, cluster = estudo, obs = efeito, data = d, rho = rho)
  fit <- tentar_ajuste(function(ctrl) {
    if (is.null(mods)) {
      metafor::rma.mv(yi, V, random = ~ 1 | estudo / efeito, data = d, method = "REML",
                      test = "t", dfs = "contain", slab = d$rotulo, control = ctrl)
    } else {
      metafor::rma.mv(yi, V, mods = mods, random = ~ 1 | estudo / efeito, data = d, method = "REML",
                      test = "t", dfs = "contain", control = ctrl)
    }
  })
  list(fit = fit, robusto = metafor::robust(fit, cluster = d$estudo, clubSandwich = TRUE))
}

#' Ajusta o modelo principal do grupo e devolve (objeto para o forest, resumo em lista).
ajustar_modelo <- function(d, dependencia, rho, delta = NULL) {
  k_estudos <- length(unique(d$estudo))
  if (dependencia == "che") {
    m <- ajustar_che(d, rho)
    fit <- m$fit
    rob <- m$robusto
    est <- as.numeric(rob$b)
    se <- as.numeric(rob$se)
    gl <- as.numeric(rob$ddf)
    sigma2 <- as.numeric(fit$sigma2)
    # Intervalo de predição manual: t com k_estudos − 2 gl e EP robusto (Riley 2011).
    gl_pi <- max(k_estudos - 2L, 1L)
    meia <- stats::qt(0.975, gl_pi) * sqrt(sum(sigma2) + se^2)
    # I² multinível (Nakagawa & Santos 2012; fórmula da documentação do metafor).
    W <- solve(fit$V)
    X <- stats::model.matrix(fit)
    P <- W - W %*% X %*% solve(t(X) %*% W %*% X) %*% t(X) %*% W
    v_tipica <- (fit$k - fit$p) / sum(diag(P))
    i2_total <- 100 * sum(sigma2) / (sum(sigma2) + v_tipica)
    resumo <- list(
      modelo = "CHE (rma.mv estudo/efeito, REML) + RVE CR2 (Satterthwaite)",
      k_estudos = k_estudos, k_efeitos = nrow(d), rho = rho,
      estimativa = est, ep = se, ic = c(as.numeric(rob$ci.lb), as.numeric(rob$ci.ub)),
      p = as.numeric(rob$pval), gl = gl, rve_confiavel = gl >= GL_RVE_MINIMO,
      tau2 = sum(sigma2), tau2_entre_estudos = sigma2[1], tau2_dentro_estudos = sigma2[2],
      tau2_ic = NULL, tau = sqrt(sum(sigma2)),
      I2 = i2_total, I2_entre_estudos = 100 * sigma2[1] / (sum(sigma2) + v_tipica),
      I2_dentro_estudos = 100 * sigma2[2] / (sum(sigma2) + v_tipica), I2_ic = NULL,
      Q = as.numeric(fit$QE), Q_gl = fit$k - fit$p, Q_p = as.numeric(fit$QEp),
      pi = c(est - meia, est + meia), pi_gl = gl_pi
    )
    if (!resumo$rve_confiavel) {
      resumo$aviso_rve <- sprintf("gl de Satterthwaite = %.2f < 4: inferência robusta não confiável", gl)
    }
    objeto <- rob
  } else {
    fit <- ajustar_uni(d)
    ic_het <- tryCatch(stats::confint(fit)$random, error = function(e) NULL)
    pred <- tryCatch(stats::predict(fit, predtype = "Riley"), error = function(e) NULL)
    resumo <- list(
      modelo = "efeitos aleatórios REML + HKSJ modificado (metafor test='adhoc')",
      k_estudos = k_estudos, k_efeitos = nrow(d),
      estimativa = as.numeric(fit$b), ep = as.numeric(fit$se),
      ic = c(as.numeric(fit$ci.lb), as.numeric(fit$ci.ub)), p = as.numeric(fit$pval),
      gl = fit$k - fit$p,
      tau2 = as.numeric(fit$tau2),
      tau2_ic = if (!is.null(ic_het)) as.numeric(ic_het["tau^2", c("ci.lb", "ci.ub")]) else NULL,
      tau = sqrt(as.numeric(fit$tau2)),
      I2 = as.numeric(fit$I2),
      I2_ic = if (!is.null(ic_het)) as.numeric(ic_het["I^2(%)", c("ci.lb", "ci.ub")]) else NULL,
      H2 = as.numeric(fit$H2),
      Q = as.numeric(fit$QE), Q_gl = fit$k - fit$p, Q_p = as.numeric(fit$QEp),
      pi = if (fit$k >= 3 && !is.null(pred)) c(as.numeric(pred$pi.lb), as.numeric(pred$pi.ub)) else NULL,
      pi_gl = if (fit$k >= 3 && !is.null(pred)) fit$k - 2 else NULL
    )
    objeto <- fit
  }
  # Limites também como escalares (ic_inf/ic_sup, ip_inf/ip_sup) para consumidores que
  # não leem vetores; direcao_alinhada = TRUE porque só entram linhas com sinal alinhado.
  resumo$ic_inf <- resumo$ic[1]
  resumo$ic_sup <- resumo$ic[2]
  resumo$ip_inf <- if (is.null(resumo$pi)) NULL else resumo$pi[1]
  resumo$ip_sup <- if (is.null(resumo$pi)) NULL else resumo$pi[2]
  resumo$direcao_alinhada <- TRUE
  resumo$tau2_interpretavel <- k_estudos >= K_TAU2_INTERPRETAVEL
  resumo$direcao <- if (resumo$estimativa > 0) "benefica" else if (resumo$estimativa < 0) "danosa" else "nula"
  resumo$ic_exclui_zero <- resumo$ic[1] > 0 || resumo$ic[2] < 0
  # Mesmos critérios de rslib/caixa.py (Misto e Nulo): ver CONTRATO_CAMPOS.
  com_delta <- delta_valido(delta)
  if (is.null(resumo$pi)) {
    resumo$pi_cobre_beneficio_e_dano <- NULL
  } else if (com_delta) {
    resumo$pi_cobre_beneficio_e_dano <- resumo$pi[1] <= -delta && resumo$pi[2] >= delta
    resumo$pi_referencia <- "delta"
  } else {
    resumo$pi_cobre_beneficio_e_dano <- resumo$pi[1] < 0 && resumo$pi[2] > 0
    resumo$pi_referencia <- "zero"
  }
  resumo$ic_dentro_delta <- if (com_delta) (resumo$ic[1] >= -delta && resumo$ic[2] <= delta) else NULL
  list(objeto = objeto, resumo = resumo)
}

#' Resumo curto usado em sensibilidades (estimativa, IC, PI, τ², k).
resumo_curto <- function(d, dependencia, rho) {
  r <- tryCatch(ajustar_modelo(d, dependencia, rho)$resumo, error = function(e) list(erro = conditionMessage(e)))
  if (!is.null(r$erro)) return(list(executado = FALSE, motivo = paste("erro de ajuste:", r$erro)))
  list(executado = TRUE, k_estudos = r$k_estudos, k_efeitos = r$k_efeitos, estimativa = r$estimativa,
       ic = r$ic, pi = r$pi, tau2 = r$tau2, ic_exclui_zero = r$ic_exclui_zero)
}

# ---------------------------------------------------------------------------
# Sensibilidade
# ---------------------------------------------------------------------------

sensibilidade_subconjunto <- function(d, remover, motivo_nome, dependencia, rho, k_min) {
  n_removidos <- sum(remover)
  if (n_removidos == 0L) return(list(executado = FALSE, motivo = paste("nenhuma linha", motivo_nome)))
  resto <- d[!remover, , drop = FALSE]
  k <- length(unique(resto$estudo))
  if (k < k_min) {
    return(list(executado = FALSE, n_removidos = n_removidos, k_restante = k,
                motivo = sprintf("k restante (%d) < k-min (%d)", k, k_min)))
  }
  c(resumo_curto(resto, dependencia, rho), list(n_removidos = n_removidos))
}

leave_one_out <- function(d, dependencia, rho, principal) {
  estudos <- unique(d$estudo)
  if (length(estudos) < 3L) return(list(tabela = NULL, resumo = list(executado = FALSE, motivo = "k < 3")))
  linhas <- lapply(estudos, function(e) {
    r <- resumo_curto(d[d$estudo != e, , drop = FALSE], dependencia, rho)
    if (!isTRUE(r$executado)) {
      return(data.frame(estudo_removido = e, estimativa = NA_real_, ic_inf = NA_real_, ic_sup = NA_real_,
                        tau2 = NA_real_, ic_exclui_zero = NA))
    }
    data.frame(estudo_removido = e, estimativa = r$estimativa, ic_inf = r$ic[1], ic_sup = r$ic[2],
               tau2 = r$tau2, ic_exclui_zero = r$ic_exclui_zero)
  })
  tab <- do.call(rbind, linhas)
  muda <- tab$estudo_removido[!is.na(tab$ic_exclui_zero) & tab$ic_exclui_zero != principal$ic_exclui_zero]
  list(tabela = tab, resumo = list(
    executado = TRUE,
    estimativa_min = min(tab$estimativa, na.rm = TRUE),
    estimativa_max = max(tab$estimativa, na.rm = TRUE),
    estudos_que_mudam_conclusao = as.list(muda)
  ))
}

# ---------------------------------------------------------------------------
# Viés de publicação (k >= 10)
# ---------------------------------------------------------------------------

#' EP modificado de Pustejovsky & Rodgers (2019) para diferenças padronizadas.
#'
#' √((n1 + n2)/(n1·n2)) só depende do tamanho dos grupos; o EP de g depende de g
#' (Var(g) tem o termo g²/2N), o que cria correlação artificial entre efeito e precisão.
#' Devolve `se = NULL` (e o motivo) se algum estudo não tiver n1 e n2 positivos: misturar
#' os dois preditores na mesma regressão não teria interpretação.
ep_modificado_smd <- function(d) {
  n1 <- como_num(coluna(d, "n1"))
  n2 <- como_num(coluna(d, "n2"))
  ok <- !is.na(n1) & !is.na(n2) & n1 > 0 & n2 > 0
  if (!nrow(d) || !all(ok)) {
    return(list(se = NULL, motivo = sprintf("%d de %d estudos sem n1 e n2: usado o EP de g", sum(!ok), nrow(d))))
  }
  list(se = sqrt((n1 + n2) / (n1 * n2)), motivo = NULL)
}

#' n1/n2 por estudo para os efeitos agregados do CHE: o valor único do estudo, senão NA.
n_grupos_por_estudo <- function(d, estudos) {
  unico <- function(col, e) {
    v <- unique(como_num(coluna(d, col))[d$estudo == e])
    v <- v[!is.na(v)]
    if (length(v) == 1L) v else NA_real_
  }
  list(n1 = vapply(estudos, function(e) unico("n1", e), numeric(1)),
       n2 = vapply(estudos, function(e) unico("n2", e), numeric(1)))
}

#' Regra condicional do PET-PEESE (Stanley & Doucouliagos 2014): PEESE só quando o intercepto do
#' PET é positivo (yi alinhado: positivo = benéfico) e significativo a 5% unilateral na direção benéfica,
#' o que equivale a p bilateral < 0,10 com intercepto > 0. Intercepto negativo, mesmo "significativo",
#' fica com o PET: não há efeito benéfico genuíno a corrigir pelo PEESE.
regra_pet_peese <- function(intercepto, t_intercepto, gl, peese_intercepto) {
  p_unilateral <- stats::pt(t_intercepto, df = gl, lower.tail = FALSE)
  usa_peese <- isTRUE(intercepto > 0) && isTRUE(p_unilateral < 0.05)
  list(
    pet_p_unilateral = p_unilateral,
    escolhido = if (usa_peese) "PEESE" else "PET",
    estimativa_corrigida = if (usa_peese) peese_intercepto else intercepto,
    regra = paste("PEESE se o intercepto do PET for positivo (benéfico) com p unilateral < 0,05",
                  "(= p bilateral < 0,10 no sentido benéfico); senão, PET (references/07a-sintese-quantitativa.md)")
  )
}

#' Diagnósticos de pequenos estudos em dados independentes (um efeito por estudo).
vies_publicacao <- function(d, arquivo_funil) {
  k <- nrow(d)
  if (k < K_VIES_PUBLICACAO) {
    return(list(executado = FALSE, motivo = sprintf("k = %d < %d: funil, Egger, PET-PEESE e 3PSM não são informativos", k, K_VIES_PUBLICACAO)))
  }
  fit <- ajustar_uni(d)
  saida <- list(executado = TRUE, k = k)
  saida$funil <- salvar_grafico(arquivo_funil, 7, 6, function() {
    metafor::funnel(fit, xlab = "g de Hedges (positivo = benéfico)")
  })

  mod <- ep_modificado_smd(d)
  usa_mod <- !is.null(mod$se)
  preditor <- if (usa_mod) mod$se else sqrt(d$vi)
  saida$preditor_precisao <- if (usa_mod) "ep_modificado_smd" else "sei"
  saida$nota_preditor <- if (usa_mod) {
    paste("Egger e PET-PEESE com EP modificado sqrt((n1+n2)/(n1*n2)) como preditor e pesos pela variância",
          "amostral de g (Pustejovsky & Rodgers 2019); o funil e o 3PSM seguem com o EP de g;",
          "efeito de desenho de cluster não entra no EP modificado")
  } else {
    paste(mod$motivo, "(o Egger com EP de g infla o erro tipo I para SMD: ler com cautela)")
  }

  if (usa_mod) {
    d$.se_mod <- preditor
    eg <- tryCatch(tentar_ajuste(function(ctrl) {
      metafor::rma(yi, vi, mods = ~ .se_mod, data = d, method = "REML", test = "adhoc", control = ctrl)
    }), error = function(e) NULL)
    saida$egger <- if (is.null(eg)) list(executado = FALSE, preditor = "ep_modificado_smd") else
      list(executado = TRUE, preditor = "ep_modificado_smd", estatistica = as.numeric(eg$zval[2]),
           gl = nulo_se_na(as.numeric(eg$ddf[1])), p = as.numeric(eg$pval[2]),
           estimativa_limite = as.numeric(eg$b[1]), ic_limite = c(as.numeric(eg$ci.lb[1]), as.numeric(eg$ci.ub[1])))
  } else {
    eg <- tryCatch(metafor::regtest(fit, model = "rma", predictor = "sei"), error = function(e) NULL)
    saida$egger <- if (is.null(eg)) list(executado = FALSE, preditor = "sei") else
      list(executado = TRUE, preditor = "sei", estatistica = as.numeric(eg$zval), gl = nulo_se_na(as.numeric(eg$dfs)),
           p = as.numeric(eg$pval), estimativa_limite = as.numeric(eg$est),
           ic_limite = c(as.numeric(eg$ci.lb), as.numeric(eg$ci.ub)))
  }

  # PET-PEESE (Stanley & Doucouliagos 2014): mínimos quadrados ponderados por 1/vi,
  # com o EP (PET) ou seu quadrado (PEESE) como preditor; EP modificado quando há n1/n2.
  pet_ajuste <- stats::lm(d$yi ~ preditor, weights = 1 / d$vi)
  pet <- summary(pet_ajuste)$coefficients
  peese_ajuste <- stats::lm(d$yi ~ I(preditor^2), weights = 1 / d$vi)
  peese <- summary(peese_ajuste)$coefficients
  gl_pet <- stats::df.residual(pet_ajuste)
  saida$pet_peese <- c(list(
    variante = VARIANTE_PET_PEESE$nome, metodo = VARIANTE_PET_PEESE$metodo,
    preditor = saida$preditor_precisao, gl = gl_pet,
    pet_intercepto = pet[1, 1], pet_ep = pet[1, 2], pet_t = pet[1, 3], pet_p = pet[1, 4],
    peese_intercepto = peese[1, 1], peese_ep = peese[1, 2], peese_t = peese[1, 3], peese_p = peese[1, 4]
  ), regra_pet_peese(pet[1, 1], pet[1, 3], gl_pet, peese[1, 1]))

  # Modelo de seleção de 3 parâmetros: corte em p unilateral 0,025 (efeito benéfico significativo).
  avisos <- character(0)
  sel <- tryCatch(
    withCallingHandlers(
      metafor::selmodel(metafor::rma(yi, vi, data = d, method = "ML"), type = "stepfun", steps = 0.025),
      warning = function(w) {
        avisos <<- c(avisos, conditionMessage(w))
        invokeRestart("muffleWarning")
      }),
    error = function(e) e)
  if (inherits(sel, "error")) {
    saida$selecao_3psm <- list(executado = FALSE, motivo = conditionMessage(sel))
  } else {
    sem_p <- any(grepl("do not contain", avisos))
    saida$selecao_3psm <- list(
      executado = TRUE, estimavel = !sem_p,
      estimativa = as.numeric(sel$beta), ic = c(as.numeric(sel$ci.lb), as.numeric(sel$ci.ub)),
      p = as.numeric(sel$pval), lrt = as.numeric(sel$LRT), lrt_p = as.numeric(sel$LRTp),
      peso_nao_significativos = as.numeric(sel$delta[length(sel$delta)]),
      avisos = as.list(avisos),
      nota = "sensibilidade; com um intervalo sem p observados o modelo não é identificável"
    )
  }
  saida
}

# ---------------------------------------------------------------------------
# Moderadores
# ---------------------------------------------------------------------------

resumo_moderacao <- function(ajuste, dependencia) {
  obj <- if (dependencia == "che") ajuste$robusto else ajuste
  coefs <- data.frame(termo = rownames(obj$b), estimativa = as.numeric(obj$b), ep = as.numeric(obj$se),
                      p = as.numeric(obj$pval), ic_inf = as.numeric(obj$ci.lb), ic_sup = as.numeric(obj$ci.ub))
  list(QM = as.numeric(obj$QM), QM_gl = as.numeric(obj$QMdf), QM_p = as.numeric(obj$QMp),
       R2 = nulo_se_na(if (!is.null(obj$R2)) as.numeric(obj$R2) else NA_real_),
       coeficientes = coefs)
}

analisar_moderadores <- function(d, moderadores, dependencia, rho) {
  resultados <- list()
  gl_total <- 0L
  usaveis <- character(0)
  for (m in moderadores) {
    if (!m %in% names(d)) {
      resultados[[m]] <- list(executado = FALSE, motivo = "coluna ausente")
      next
    }
    valor <- coluna(d, m)
    ok <- !vazio(valor)
    dm <- d[ok, , drop = FALSE]
    x_num <- como_num(valor[ok])
    continuo <- length(x_num) > 0L && all(!is.na(x_num))
    k <- length(unique(dm$estudo))
    base <- list(tipo = if (continuo) "continuo" else "categorico", k_estudos = k,
                 n_sem_valor = sum(!ok))
    if (continuo) {
      if (k < ESTUDOS_POR_COVARIAVEL) {
        resultados[[m]] <- c(base, list(executado = FALSE, motivo = sprintf("meta-regressão exige ~%d estudos por covariável (k = %d)", ESTUDOS_POR_COVARIAVEL, k)))
        next
      }
      dm$.x <- x_num
      formula <- ~ .x
      gl_m <- 1L
    } else {
      niveis <- tapply(dm$estudo, valor[ok], function(e) length(unique(e)))
      if (length(niveis) < 2L) {
        resultados[[m]] <- c(base, list(executado = FALSE, motivo = "menos de 2 níveis"))
        next
      }
      if (any(niveis < K_POR_NIVEL_SUBGRUPO)) {
        resultados[[m]] <- c(base, list(executado = FALSE, estudos_por_nivel = as.list(niveis),
                                        motivo = sprintf("subgrupo exige k >= %d por nível", K_POR_NIVEL_SUBGRUPO)))
        next
      }
      dm$.x <- factor(valor[ok])
      formula <- ~ .x
      gl_m <- length(niveis) - 1L
    }
    ajuste <- tryCatch(
      if (dependencia == "che") ajustar_che(dm, rho, mods = formula) else ajustar_uni(dm, mods = formula),
      error = function(e) e)
    if (inherits(ajuste, "error")) {
      resultados[[m]] <- c(base, list(executado = FALSE, motivo = paste("erro de ajuste:", conditionMessage(ajuste))))
      next
    }
    res <- c(base, list(executado = TRUE), resumo_moderacao(ajuste, dependencia))
    res$coeficientes$termo <- sub("^\\.x", m, res$coeficientes$termo)
    if (!continuo) {
      res$subgrupos <- lapply(split(dm, dm$.x), function(s) {
        c(list(nivel = as.character(s$.x[1])), resumo_curto(s, dependencia, rho))
      })
      names(res$subgrupos) <- NULL
    }
    resultados[[m]] <- res
    gl_total <- gl_total + gl_m
    usaveis <- c(usaveis, m)
  }
  conjunto <- NULL
  if (length(usaveis) >= 2L) {
    completos <- Reduce(`&`, lapply(usaveis, function(m) !vazio(coluna(d, m))))
    dm <- d[completos, , drop = FALSE]
    k <- length(unique(dm$estudo))
    if (k < ESTUDOS_POR_COVARIAVEL * gl_total) {
      conjunto <- list(executado = FALSE, motivo = sprintf("modelo conjunto exige ~%d estudos (k = %d)", ESTUDOS_POR_COVARIAVEL * gl_total, k))
    } else {
      for (m in usaveis) {
        x <- como_num(coluna(dm, m))
        dm[[paste0(".m_", m)]] <- if (resultados[[m]]$tipo == "continuo") x else factor(coluna(dm, m))
      }
      formula <- stats::as.formula(paste("~", paste0("`.m_", usaveis, "`", collapse = " + ")))
      ajuste <- tryCatch(
        if (dependencia == "che") ajustar_che(dm, rho, mods = formula) else ajustar_uni(dm, mods = formula),
        error = function(e) e)
      conjunto <- if (inherits(ajuste, "error")) list(executado = FALSE, motivo = conditionMessage(ajuste)) else
        c(list(executado = TRUE, k_estudos = k), resumo_moderacao(ajuste, dependencia))
    }
  }
  list(individuais = resultados, conjunto = conjunto)
}

# ---------------------------------------------------------------------------
# Figuras
# ---------------------------------------------------------------------------

salvar_forest <- function(objeto, base, titulo, n_linhas) {
  altura <- max(4, 1.8 + 0.25 * (n_linhas + 4))
  desenhar <- function() {
    metafor::forest(objeto, addpred = TRUE, header = c("Estudo", "g [IC 95%]"),
                    xlab = "g de Hedges (positivo = benéfico)", mlab = "Modelo (IC e intervalo de predição)")
    graphics::title(titulo, cex.main = 0.9)
  }
  unlist(list(salvar_grafico(paste0(base, ".png"), 8, altura, desenhar),
              salvar_grafico(paste0(base, ".pdf"), 8, altura, desenhar)))
}

# ---------------------------------------------------------------------------
# Grupo e principal
# ---------------------------------------------------------------------------

analisar_grupo <- function(d, rotulo, indice, opcoes) {
  base_nome <- sprintf("%02d_%s", indice, slug(rotulo))
  saida <- c(list(grupo = rotulo), atributos_grupo(d, opcoes$grupo, opcoes$separar_desenho),
             list(arquivo_base = base_nome, n_linhas = nrow(d), comparabilidade = comparabilidade(d)))
  dependencia <- opcoes$dependencia

  if (dependencia == "um_por_estudo") {
    sel <- selecionar_um_por_estudo(d, d$estudo)
    if (length(sel$conflitos)) {
      saida$status <- "dependencia_nao_resolvida"
      saida$estudos_com_varios_efeitos <- as.list(sel$conflitos)
      saida$motivo <- paste("estudos com mais de um efeito e sem um único modelo_principal;",
                            "marque o modelo principal (regra do protocolo) ou use --dependencia=che")
      return(saida)
    }
    saida$n_descartados_nao_principais <- sum(!sel$manter)
    d <- d[sel$manter, , drop = FALSE]
    saida$comparabilidade <- comparabilidade(d)
  }

  # --excluir-rob=critico: fora da análise principal DEPOIS da seleção do modelo principal.
  d_com_critico <- d
  n_critico <- 0L
  if (identical(opcoes$excluir_rob, "critico")) {
    critico <- eh_rob_critico(coluna(d, "rob_geral"))
    n_critico <- sum(critico)
    saida$excluidos_rob_critico <- list(
      n_linhas = n_critico, estudos = as.list(unique(d$rotulo[critico])),
      n_sem_rob_geral = sum(vazio(coluna(d, "rob_geral"))),
      nota = "risco de viés crítico fora da análise principal; a análise com essas linhas está em sensibilidade$com_rob_critico"
    )
    if (n_critico > 0L) {
      d <- d[!critico, , drop = FALSE]
      saida$comparabilidade <- comparabilidade(d)
    }
  }

  k <- length(unique(d$estudo))
  saida$k_estudos <- k
  saida$k_efeitos <- nrow(d)
  saida$estudos <- as.list(unique(d$rotulo))
  if (k < opcoes$k_min) {
    saida$status <- "k_insuficiente"
    saida$motivo <- sprintf("k = %d < k-min = %d: não agregar; usar SWiM", k, opcoes$k_min)
    if (n_critico > 0L) saida$motivo <- paste0(saida$motivo, sprintf(" (depois de excluir %d linha(s) com RoB crítico)", n_critico))
    return(saida)
  }

  ajuste <- tryCatch(ajustar_modelo(d, dependencia, opcoes$rho, opcoes$delta), error = function(e) e)
  if (inherits(ajuste, "error")) {
    saida$status <- "erro_ajuste"
    saida$motivo <- conditionMessage(ajuste)
    return(saida)
  }
  saida$status <- "meta_ajustada"
  saida$resultado <- ajuste$resumo

  saida$figuras <- as.list(salvar_forest(ajuste$objeto, file.path(opcoes$out_dir, "figuras", paste0("forest_", base_nome)),
                                         rotulo, nrow(d)))

  loo <- leave_one_out(d, dependencia, opcoes$rho, ajuste$resumo)
  saida$sensibilidade <- list(leave_one_out = loo$resumo)
  if (!is.null(loo$tabela)) {
    arq <- file.path(opcoes$out_dir, "tabelas", paste0("loo_", base_nome, ".csv"))
    escrever_csv(loo$tabela, arq)
    saida$sensibilidade$leave_one_out$tabela <- arq
  }
  saida$sensibilidade$sem_aproximados <- sensibilidade_subconjunto(
    d, !is.na(d$aproximado_num) & d$aproximado_num == 1, "aproximada", dependencia, opcoes$rho, opcoes$k_min)
  if ("rob_geral" %in% names(d)) {
    alto <- grepl(PADRAO_ALTO_RISCO, ascii_minusculo(coluna(d, "rob_geral")))
    saida$sensibilidade$sem_alto_risco <- sensibilidade_subconjunto(
      d, alto, "com risco de viés alto/crítico", dependencia, opcoes$rho, opcoes$k_min)
  } else {
    saida$sensibilidade$sem_alto_risco <- list(executado = FALSE, motivo = "coluna rob_geral ausente")
  }
  if (identical(opcoes$excluir_rob, "critico")) {
    saida$sensibilidade$com_rob_critico <- if (n_critico == 0L) {
      list(executado = FALSE, motivo = "nenhuma linha com risco de viés crítico no grupo")
    } else {
      c(resumo_curto(d_com_critico, dependencia, opcoes$rho), list(n_incluidos = n_critico))
    }
  }
  if (dependencia == "che") {
    saida$sensibilidade$rho <- lapply(setdiff(RHOS_SENSIBILIDADE, opcoes$rho), function(r) {
      c(list(rho = r), resumo_curto(d, "che", r))
    })
  }

  # Viés de publicação: no CHE, sobre efeitos agregados por estudo (independentes).
  d_vies <- d
  if (dependencia == "che") {
    esc <- metafor::escalc(yi = yi, vi = vi, data = d)
    ag <- as.data.frame(stats::aggregate(esc, cluster = estudo, rho = opcoes$rho))
    d_vies <- data.frame(yi = as.numeric(ag$yi), vi = as.numeric(ag$vi), rotulo = ag$estudo)
    ns <- n_grupos_por_estudo(d, as.character(ag$estudo))  # para o EP modificado do Egger
    d_vies$n1 <- ns$n1
    d_vies$n2 <- ns$n2
  }
  saida$vies_publicacao <- vies_publicacao(d_vies, file.path(opcoes$out_dir, "figuras", paste0("funil_", base_nome, ".png")))
  if (!is.null(saida$vies_publicacao$funil)) saida$figuras <- c(saida$figuras, list(saida$vies_publicacao$funil))

  if (length(opcoes$moderadores)) {
    saida$moderadores <- analisar_moderadores(d, opcoes$moderadores, dependencia, opcoes$rho)
  }
  saida
}

linha_tabela <- function(g) {
  r <- g$resultado
  num <- function(x, i = 1L) if (is.null(x) || length(x) < i) NA_real_ else x[[i]]
  data.frame(
    grupo = g$grupo, status = g$status, k_estudos = num(g$k_estudos), k_efeitos = num(g$k_efeitos),
    estimativa = num(r$estimativa), ic_inf = num(r$ic, 1L), ic_sup = num(r$ic, 2L), p = num(r$p),
    pi_inf = num(r$pi, 1L), pi_sup = num(r$pi, 2L), tau2 = num(r$tau2),
    tau2_ic_inf = num(r$tau2_ic, 1L), tau2_ic_sup = num(r$tau2_ic, 2L), I2 = num(r$I2),
    Q = num(r$Q), Q_p = num(r$Q_p), tau2_interpretavel = if (is.null(r)) NA else r$tau2_interpretavel,
    motivo = if (is.null(g$motivo)) "" else g$motivo,
    n_excluidos_rob_critico = if (is.null(g$excluidos_rob_critico)) NA_integer_ else g$excluidos_rob_critico$n_linhas,
    stringsAsFactors = FALSE
  )
}

executar_meta <- function(df, opcoes) {
  prep <- preparar_dados_meta(df)
  d <- prep$dados
  grupos <- rotulo_grupo(d, opcoes$grupo, opcoes$separar_desenho)
  rotulos <- sort(unique(grupos))
  resultados <- lapply(seq_along(rotulos), function(i) {
    analisar_grupo(d[grupos == rotulos[i], , drop = FALSE], rotulos[i], i, opcoes)
  })
  list(excluidos = prep$excluidos, grupos = resultados, n_linhas_analisaveis = nrow(d))
}

main_meta <- function(args) {
  entrada <- cli_arg(args, "in", obrigatorio = TRUE)
  opcoes <- list(
    out_dir = cli_arg(args, "out-dir", "06-analise"),
    grupo = cli_colunas_grupo(args),
    moderadores = cli_lista(args, "moderadores"),
    k_min = as.integer(cli_num(args, "k-min", 3)),
    dependencia = as.character(cli_arg(args, "dependencia", "um_por_estudo")),
    rho = cli_num(args, "rho", 0.6),
    delta = cli_num(args, "delta", NULL),
    separar_desenho = cli_bool(args, "separar-desenho", TRUE),
    excluir_rob = ascii_minusculo(as.character(cli_arg(args, "excluir-rob", "nenhum")))
  )
  if (!opcoes$dependencia %in% c("um_por_estudo", "che")) {
    cli_falhar("--dependencia deve ser um_por_estudo ou che", SAIDA_ERRO_DADOS)
  }
  if (!opcoes$excluir_rob %in% OPCOES_EXCLUIR_ROB) {
    cli_falhar(sprintf("--excluir-rob deve ser %s", paste(OPCOES_EXCLUIR_ROB, collapse = " ou ")), SAIDA_ERRO_DADOS)
  }
  if (!is.null(opcoes$delta) && !delta_valido(opcoes$delta)) {
    message("aviso: --delta <= 0 equivale a δ não declarado (ic_dentro_delta fica nulo, como em rs.py caixa)")
  }
  if (opcoes$k_min < 2L) cli_falhar("--k-min deve ser >= 2", SAIDA_ERRO_DADOS)
  if (opcoes$rho < 0 || opcoes$rho >= 1) cli_falhar("--rho deve estar em [0, 1)", SAIDA_ERRO_DADOS)
  exigir_pacotes(c("metafor", if (opcoes$dependencia == "che") "clubSandwich"))

  df <- ler_csv_texto(entrada)
  if (!all(c("yi", "vi") %in% names(df))) {
    cli_falhar("entrada sem yi/vi: rode efeitos.R antes de meta.R", SAIDA_ERRO_DADOS)
  }
  if (opcoes$excluir_rob == "critico" && !"rob_geral" %in% names(df)) {
    cli_falhar("--excluir-rob=critico exige a coluna rob_geral na entrada (preserve-a em preparar-efeitos)",
               SAIDA_ERRO_DADOS)
  }
  ausentes <- setdiff(opcoes$grupo, names(df))
  if (length(ausentes)) {
    message(sprintf("aviso: coluna(s) de grupo ausente(s): %s", paste(ausentes, collapse = ", ")))
  }
  dir.create(file.path(opcoes$out_dir, "figuras"), recursive = TRUE, showWarnings = FALSE)
  dir.create(file.path(opcoes$out_dir, "tabelas"), recursive = TRUE, showWarnings = FALSE)

  res <- executar_meta(df, opcoes)
  status <- vapply(res$grupos, function(g) g$status, character(1))
  n_critico_total <- sum(vapply(res$grupos, function(g) {
    if (is.null(g$excluidos_rob_critico)) 0L else as.integer(g$excluidos_rob_critico$n_linhas)
  }, integer(1)))
  arquivo_json <- file.path(opcoes$out_dir, "meta_resumo.json")
  arquivo_tab <- file.path(opcoes$out_dir, "tabelas", "meta_grupos.csv")
  escrever_json(list(
    versao = "1", comando = "meta", gerado_em = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    entrada = entrada,
    parametros = list(grupo = as.list(opcoes$grupo), separar_desenho = opcoes$separar_desenho,
                      dependencia = opcoes$dependencia, rho = opcoes$rho, k_min = opcoes$k_min,
                      delta = opcoes$delta,
                      delta_fonte = if (is.null(opcoes$delta)) "nao_informado" else "argumento (confirmar no protocolo)",
                      excluir_rob = opcoes$excluir_rob,
                      moderadores = as.list(opcoes$moderadores),
                      pacotes = list(metafor = as.character(utils::packageVersion("metafor")))),
    linhas_excluidas = res$excluidos,
    n_excluidos_rob_critico = n_critico_total,
    contrato_campos = CONTRATO_CAMPOS,
    ressalvas = list(
      "yi positivo = benéfico (sinal alinhado por direcao_desejada em efeitos.R)",
      "τ² e I² com k < 5 são imprecisos e não devem ser interpretados",
      "rótulo da caixa de ferramentas exige certeza (GRADE); este resumo não define rótulo"
    ),
    grupos = res$grupos
  ), arquivo_json)
  if (length(res$grupos)) escrever_csv(do.call(rbind, lapply(res$grupos, linha_tabela)), arquivo_tab)

  bloqueados <- sum(status == "dependencia_nao_resolvida")
  codigo <- if (bloqueados > 0L) SAIDA_CHECAGEM else SAIDA_OK
  figuras <- unlist(lapply(res$grupos, function(g) g$figuras))
  message(sprintf("meta: %d grupos (%d ajustados, %d com k insuficiente, %d bloqueados por dependência)",
                  length(status), sum(status == "meta_ajustada"), sum(status == "k_insuficiente"), bloqueados))
  list(codigo = codigo, resumo = list(
    ok = codigo == SAIDA_OK, comando = "meta", entrada = entrada, out_dir = opcoes$out_dir,
    resumo_json = arquivo_json, tabela = arquivo_tab, dependencia = opcoes$dependencia,
    n_grupos = length(status),
    n_meta_ajustadas = sum(status == "meta_ajustada"),
    n_k_insuficiente = sum(status == "k_insuficiente"),
    n_dependencia_nao_resolvida = bloqueados,
    n_erro_ajuste = sum(status == "erro_ajuste"),
    n_linhas_analisaveis = res$n_linhas_analisaveis,
    excluir_rob = opcoes$excluir_rob,
    n_excluidos_rob_critico = n_critico_total,
    linhas_excluidas = res$excluidos,
    figuras = as.list(figuras)
  ))
}

if (sys.nframe() == 0L) {
  quit(status = cli_executar(function() main_meta(cli_args())), save = "no")
}
