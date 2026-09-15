# efeitos.R — converte estatísticas extraídas em tamanho de efeito comum (g de Hedges).
#
# USO
#     Rscript efeitos.R --in=05-decomposicao/efeitos_extraidos.csv \
#                       --out=06-analise/efeitos.csv [--delta=0.1]
#
# Entrada: CSV com as colunas de esquema.COLUNAS_EFEITOS_EXTRAIDOS (colunas extras,
# como rob_geral, são preservadas no fim). Saída: as mesmas linhas com
# yi (g), vi (variância), sei (erro-padrão), formula_id, aproximado (0/1),
# sinal_alinhado (mantido|invertido|sem_direcao) e aviso.
#
# Convenções de sinal: o grupo 1 (m1, sd1, n1) é o tratamento e o grupo 2 o
# comparador; t, beta e r positivos significam "tratamento maior". Depois do
# cálculo o sinal é alinhado por `direcao_desejada`: com "reduzir" o efeito é
# multiplicado por −1, de modo que yi > 0 SEMPRE significa efeito benéfico.
# Sem direção declarada o sinal fica bruto e a linha não entra na meta-análise.
#
# Convenções de colunas (as mesmas de agentes/extrator-efeitos.md)
# - g/d informados: valor em `beta` (ou colunas extras `g`/`d`) com `se` ou `ci_lo`/`ci_hi`.
# - Mann-Whitney: z em `t` (positivo = grupo 1 maior); sem z, `p` bilateral + sinal de m1 − m2.
# - Medianas: m1/m2 = medianas; quartis nas colunas extras q1_1, q3_1, q1_2, q3_2;
#   sem quartis, sd1/sd2 = amplitude interquartil.
# - OR: `or_` na escala OR; `ci_lo`/`ci_hi` na escala OR; `se` é o EP de ln(OR).
# - Cluster: `cluster` = tamanho médio do cluster (número) e `icc`.
# - Correlação parcial: `r` (ou `t`), `n_total` e a coluna extra `m_preditores` (preditores do
#   modelo com o focal, sem intercepto); sem ela, `df` residual (formula_id `parcial_r_d_gl`).
# - Desfecho binário (`dif_prop`): colunas extras `p0` (proporção no controle, 0–1), `p1` (no
#   tratamento) ou `efeito_pp` (efeito em pontos percentuais) e `se_pp` (EP do efeito em pp; sem ele,
#   IC95 do efeito em pp em ci_lo/ci_hi, ou n1/n2). Razão de riscos (`rr`): RR em `or_`, IC na escala
#   da razão e `p0`. As duas vão a d pelo log OR (Chinn 2000); ver conv_dif_prop e conv_rr.
#
# Por que assim (references/06-decomposicao.md e references/07a-sintese-quantitativa.md; Apêndice D
# da base de conhecimento, itens 2, 3 e 6)
# - Fórmulas re-derivadas de Borenstein et al. (2009, caps. 4–7), Wilson (2023),
#   Cochrane Handbook v6.5 (caps. 6, 10 e 23), Wan et al. (2014) e documentação de
#   metafor/esc e Chinn (2000) e Zhang & Yu (1998) para desfechos binários; a tabela com fórmula e
#   pressupostos por linha fica em
#   assets/mapas/conversoes_efeito.csv e todo formula_id emitido aqui precisa existir nela.
# - g = J·d com J = 1 − 3/(4·gl − 1) e Var(g) = J²·Var(d) (Borenstein, eq. 4.22–4.24).
# - Conversões fora da tabela "exata" (p arredondado, Mann-Whitney, medianas,
#   correlação parcial, n dividido ao meio, r sem n1/n2) saem com aproximado = 1 para
#   que a meta-análise rode a sensibilidade sem elas.
# - Correlação parcial segue a tabela de conversões com n e m (r_p = t/√(t² + n − m − 1), Var = (1 − r_p²)²/(n − m),
#   `parcial_r_d`); sem m, a rota pelo gl residual sai como `parcial_r_d_gl`, com aviso.
# - r ponto-bisserial → d usa a proporção do grupo 1 (p1 = n1/N) quando n1 e n2 existem
#   (`r_d`); só com n_total, p1 = 0,5 e `r_d_n_total` aproximado.
# - Mann-Whitney usa z (normal), nunca a distribuição t: r = z/√N e depois r → d
#   (tabela de conversões). Converter o p de um teste não paramétrico como se fosse t infla o efeito.
# - Medianas com quartis seguem Wan et al. (2014) (`mediana_iqr_wan`); só com IQR, a
#   aproximação IQR/1,35 sai como `mediana_iqr_aprox`, para que o nome não prometa Wan.
# - F só informa magnitude; sem uma fonte de sinal (m1−m2, beta ou t) o efeito
#   fica sem cálculo em vez de assumir benefício.
# - Revisões e meta-análises nunca entram como estudo primário (dupla contagem).
# - |g| > 2 é quase sempre erro de extração (EP lido como DP, unidades, sinal).
# - Delineamento em cluster: com tamanho médio de cluster (coluna `cluster`) e ICC,
#   a variância derivada de n é multiplicada pelo efeito de desenho 1 + (m − 1)·ICC
#   (Cochrane 23.1.4). EP informado pelo artigo é presumido já ajustado.

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

Z975 <- stats::qnorm(0.975)
ESTIMANDOS_LOCAIS <- c("itt", "late", "rdd_local", "att")

# ---------------------------------------------------------------------------
# Blocos de fórmula (valores escalares; NA quando faltam insumos)
# ---------------------------------------------------------------------------

#' Fator de correção de pequenas amostras de Hedges (Borenstein eq. 4.22).
fator_j <- function(gl) {
  ifelse(is.na(gl) | gl <= 1, NA_real_, 1 - 3 / (4 * gl - 1))
}

#' Var(d) para dois grupos independentes (Borenstein eq. 4.20).
var_d_n <- function(d, n1, n2) {
  (n1 + n2) / (n1 * n2) + d^2 / (2 * (n1 + n2))
}

#' EP a partir de IC95 simétrico (na escala em que o IC é simétrico).
se_de_ic <- function(lo, hi) {
  ifelse(is.na(lo) | is.na(hi) | hi <= lo, NA_real_, (hi - lo) / (2 * Z975))
}

d_de_t <- function(t, n1, n2) t * sqrt(1 / n1 + 1 / n2)

#' r → d (Borenstein eq. 7.5–7.6), com a variância de r (eq. 6.1).
d_de_r <- function(r, var_r) {
  list(d = 2 * r / sqrt(1 - r^2), vd = 4 * var_r / (1 - r^2)^3)
}

#' r ponto-bisserial → d com a proporção do grupo 1 (Wilson 2023, eq. 1.26; esc::esc_rpb).
#'
#' d = r / √((1 − r²)·p₁(1 − p₁)), p₁ = n₁/N. Com p₁ = 0,5 recai em 2r/√(1 − r²).
d_de_r_grupos <- function(r, n1, n2) {
  p1 <- n1 / (n1 + n2)
  r / sqrt((1 - r^2) * p1 * (1 - p1))
}

#' η(n) de Wan et al. (2014, eq. 15): DP ≈ (q3 − q1)/η(n); tende a 1,349 com n grande.
eta_wan <- function(n) {
  2 * stats::qnorm((0.75 * n - 0.125) / (n + 0.25))
}

#' Resultado vazio de uma linha.
resultado <- function(d = NA_real_, vd = NA_real_, gl = NA_real_, formula_id = "sem_calculo",
                      aproximado = 0L, avisos = character(0), var_de_n = FALSE, ja_g = FALSE) {
  list(d = d, vd = vd, gl = gl, formula_id = formula_id, aproximado = as.integer(aproximado),
       avisos = avisos, var_de_n = var_de_n, ja_g = ja_g)
}

#' Grupos a partir de n1/n2 ou, na falta, n_total dividido ao meio (aproximado).
grupos <- function(v) {
  if (!is.na(v$n1) && !is.na(v$n2) && v$n1 > 0 && v$n2 > 0) {
    return(list(n1 = v$n1, n2 = v$n2, dividido = FALSE))
  }
  if (!is.na(v$n_total) && v$n_total > 2) {
    return(list(n1 = v$n_total / 2, n2 = v$n_total / 2, dividido = TRUE))
  }
  if (!is.na(v$df) && v$df > 0) {
    return(list(n1 = (v$df + 2) / 2, n2 = (v$df + 2) / 2, dividido = TRUE))
  }
  NULL
}

#' Primeira fonte de sinal disponível (t, beta, m1 − m2, r).
sinal_linha <- function(v) {
  for (x in list(v$t, v$beta, v$m1 - v$m2, v$r)) {
    if (!is.na(x) && x != 0) return(sign(x))
  }
  NA_real_
}

# ---------------------------------------------------------------------------
# Conversões por tipo_estatistica
# ---------------------------------------------------------------------------

conv_md_sd <- function(v, formula_id = "md_sd", aproximado = 0L, avisos = character(0)) {
  if (any(is.na(c(v$m1, v$sd1, v$n1, v$m2, v$sd2, v$n2)))) {
    return(resultado(avisos = c(avisos, "md_sd exige m1, sd1, n1, m2, sd2, n2")))
  }
  if (v$sd1 <= 0 || v$sd2 <= 0 || v$n1 < 2 || v$n2 < 2) {
    return(resultado(avisos = c(avisos, "DP deve ser > 0 e n >= 2 em cada grupo")))
  }
  gl <- v$n1 + v$n2 - 2
  sp <- sqrt(((v$n1 - 1) * v$sd1^2 + (v$n2 - 1) * v$sd2^2) / gl)
  d <- (v$m1 - v$m2) / sp
  resultado(d, var_d_n(d, v$n1, v$n2), gl, formula_id, aproximado, avisos, var_de_n = TRUE)
}

conv_t <- function(v) {
  if (is.na(v$t)) return(resultado(avisos = "t ausente"))
  g <- grupos(v)
  if (is.null(g)) return(resultado(avisos = "t exige n1 e n2 (ou n_total/df)"))
  avisos <- "assume t de dois grupos independentes sem covariáveis"
  fid <- "t_ind"
  aprox <- 0L
  if (g$dividido) {
    fid <- "t_ind_n_total"
    aprox <- 1L
    avisos <- c(avisos, "grupos assumidos iguais (n_total/2)")
  }
  d <- d_de_t(v$t, g$n1, g$n2)
  resultado(d, var_d_n(d, g$n1, g$n2), g$n1 + g$n2 - 2, fid, aprox, avisos, var_de_n = TRUE)
}

conv_f1 <- function(v) {
  if (is.na(v$f) || v$f < 0) return(resultado(avisos = "F ausente ou negativo"))
  s <- sinal_linha(v)
  if (is.na(s)) {
    return(resultado(avisos = "F(1, gl) não informa direção: preencha m1/m2, beta ou t com sinal"))
  }
  g <- grupos(v)
  if (is.null(g)) return(resultado(avisos = "F exige n1 e n2 (ou n_total/df)"))
  aprox <- if (g$dividido) 1L else 0L
  avisos <- c("assume F de 1 gl no numerador comparando dois grupos; sinal tomado de outra coluna",
              if (g$dividido) "grupos assumidos iguais (n_total/2)")
  d <- s * sqrt(v$f) * sqrt(1 / g$n1 + 1 / g$n2)
  resultado(d, var_d_n(d, g$n1, g$n2), g$n1 + g$n2 - 2, "f1_ind", aprox, avisos, var_de_n = TRUE)
}

conv_beta_sd <- function(v, estimando) {
  if (is.na(v$beta)) return(resultado(avisos = "beta ausente"))
  avisos <- character(0)
  sdy <- v$sdy
  if (is.na(sdy) && !is.na(v$sd2)) {
    sdy <- v$sd2
    avisos <- c(avisos, "sdy ausente: usado sd2 (DP do grupo de comparação)")
  }
  if (is.na(sdy) || sdy <= 0) {
    return(resultado(avisos = c(avisos, "beta_sd exige sdy > 0 (DP de Y no grupo de controle)")))
  }
  d <- v$beta / sdy
  se <- if (!is.na(v$se)) v$se else se_de_ic(v$ci_lo, v$ci_hi)
  g <- grupos(v)
  gl <- if (!is.null(g)) g$n1 + g$n2 - 2 else NA_real_
  if (!is.na(v$df)) gl <- v$df
  if (!is.na(se) && se > 0) {
    vd <- (se / sdy)^2
    aprox <- 0L
    var_de_n <- FALSE
  } else if (!is.null(g)) {
    vd <- var_d_n(d, g$n1, g$n2)
    aprox <- 1L
    var_de_n <- TRUE
    avisos <- c(avisos, "sem EP do coeficiente: variância por n ignora o ajuste por covariáveis")
  } else {
    return(resultado(avisos = c(avisos, "beta_sd exige se, IC ou tamanhos de amostra")))
  }
  if (tolower(estimando) %in% ESTIMANDOS_LOCAIS) {
    avisos <- c(avisos, sprintf("estimando %s: não comparável diretamente a ATE; analisar em separado ou em sensibilidade", estimando))
  }
  resultado(d, vd, gl, "beta_sd", aprox, avisos, var_de_n = var_de_n)
}

conv_or <- function(v) {
  if (is.na(v$or_) || v$or_ <= 0) return(resultado(avisos = "or_ ausente ou <= 0"))
  se_log <- v$se
  avisos <- "assume distribuição logística latente (d = ln(OR)·√3/π)"
  if (is.na(se_log) && !is.na(v$ci_lo) && !is.na(v$ci_hi) && v$ci_lo > 0) {
    se_log <- se_de_ic(log(v$ci_lo), log(v$ci_hi))
  } else if (!is.na(se_log)) {
    avisos <- c(avisos, "se interpretado como EP de ln(OR)")
  }
  if (is.na(se_log) || se_log <= 0) return(resultado(avisos = c(avisos, "OR exige EP de ln(OR) ou IC95")))
  n <- if (!is.na(v$n_total)) v$n_total else v$n1 + v$n2
  d <- log(v$or_) * sqrt(3) / pi
  vd <- se_log^2 * 3 / pi^2
  resultado(d, vd, if (!is.na(n)) n - 2 else NA_real_, "or_logit", 0L, avisos)
}

#' Correlação parcial → d (aproximado).
#'
#' Com `m` (coluna extra `m_preditores`: preditores do modelo com o focal, sem intercepto) e n
#' (`n_total` ou n1 + n2), segue a tabela de conversões (Aloe & Becker 2012): r_p = t/√(t² + n − m − 1)
#' e Var(r_p) = (1 − r_p²)²/(n − m) (`parcial_r_d`). Sem `m` (coluna ausente ou vazia), mantém a
#' rota anterior com o gl residual informado fazendo o papel de n − m − 1: r_p = t/√(t² + gl) e
#' Var = (1 − r_p²)²/gl (sem gl, n − 1, que equivale a m = 1), com formula_id próprio
#' (`parcial_r_d_gl`) e aviso. Nas duas rotas, d = 2r/√(1 − r²) e Var(d) = 4·Var(r)/(1 − r²)³.
conv_parcial_r <- function(v, m = NA_real_) {
  r <- v$r
  avisos <- "correlação parcial depende das covariáveis do modelo: não equivale a d bivariado"
  n <- if (!is.na(v$n_total)) v$n_total else if (!is.na(v$n1) && !is.na(v$n2)) v$n1 + v$n2 else NA_real_
  if (!is.na(m)) {
    if (m < 1 || m != round(m)) return(resultado(avisos = c(avisos, "m_preditores deve ser inteiro >= 1")))
    if (is.na(n)) return(resultado(avisos = c(avisos, "parcial com m_preditores exige n_total (ou n1 e n2)")))
    gl_res <- n - m - 1
    if (gl_res <= 0) return(resultado(avisos = c(avisos, "n − m_preditores − 1 <= 0")))
    if (is.na(r)) {
      if (is.na(v$t)) return(resultado(avisos = c(avisos, "r parcial exige r ou t")))
      r <- v$t / sqrt(v$t^2 + gl_res)
      avisos <- c(avisos, "r parcial calculado de t com n − m − 1 (Aloe & Becker 2012)")
    }
    if (!is.na(v$df) && abs(v$df - gl_res) > 0.5) {
      avisos <- c(avisos, sprintf("df informado (%g) difere de n − m − 1 (%g): conferir n e m_preditores", v$df, gl_res))
    }
    if (abs(r) >= 1) return(resultado(avisos = c(avisos, "|r| >= 1")))
    conv <- d_de_r(r, (1 - r^2)^2 / (n - m))
    return(resultado(conv$d, conv$vd, gl_res, "parcial_r_d", 1L, avisos))
  }
  avisos <- c(avisos, paste("sem m_preditores: gl residual no lugar de n − m − 1 e Var(r_p) com gl em vez de n − m",
                            "(fora da tabela de conversões; informe m_preditores)"))
  if (is.na(r) && !is.na(v$t) && !is.na(v$df) && v$df > 0) {
    r <- v$t / sqrt(v$t^2 + v$df)
    avisos <- c(avisos, "r parcial calculado de t e gl residual")
  }
  if (is.na(r) || abs(r) >= 1) return(resultado(avisos = c(avisos, "r ausente ou |r| >= 1")))
  gl_var <- if (!is.na(v$df)) v$df else n - 1
  if (is.na(v$df)) avisos <- c(avisos, "gl residual ausente: Var(r parcial) com n − 1")
  if (is.na(gl_var) || gl_var <= 0) return(resultado(avisos = c(avisos, "r parcial exige gl ou n")))
  conv <- d_de_r(r, (1 - r^2)^2 / gl_var)
  gl <- if (!is.na(v$df)) v$df else n - 2
  resultado(conv$d, conv$vd, gl, "parcial_r_d_gl", 1L, avisos)
}

conv_r <- function(v, parcial = FALSE, m = NA_real_) {
  if (parcial) return(conv_parcial_r(v, m))
  r <- v$r
  avisos <- character(0)
  if (is.na(r) || abs(r) >= 1) return(resultado(avisos = c(avisos, "r ausente ou |r| >= 1")))
  n <- if (!is.na(v$n_total)) v$n_total else v$n1 + v$n2
  avisos <- c(avisos, "r→d pressupõe X dicotômico (ponto-bisserial); r entre variáveis contínuas vai para z de Fisher")
  if (!is.na(v$n1) && !is.na(v$n2) && v$n1 > 0 && v$n2 > 0) {
    # Wilson eq. 1.26: usa a proporção real do grupo 1 e a variância de base de d.
    if (v$n1 + v$n2 <= 3) return(resultado(avisos = c(avisos, "r exige n1 + n2 > 3")))
    d <- d_de_r_grupos(r, v$n1, v$n2)
    return(resultado(d, var_d_n(d, v$n1, v$n2), v$n1 + v$n2 - 2, "r_d", 0L, avisos, var_de_n = TRUE))
  }
  if (is.na(n) || n <= 3) return(resultado(avisos = c(avisos, "r exige n1 e n2 (ou n_total) com N > 3")))
  # Sem n1/n2 a proporção do grupo tratado é desconhecida: p1 = 0,5 (fora da tabela de conversões).
  d <- 2 * r / sqrt(1 - r^2)
  resultado(d, var_d_n(d, n / 2, n / 2), n - 2, "r_d_n_total", 1L,
            c(avisos, "sem n1 e n2: grupos assumidos iguais (p1 = 0,5)"), var_de_n = TRUE)
}

conv_p_n <- function(v) {
  if (is.na(v$p) || v$p <= 0 || v$p > 1) return(resultado(avisos = "p ausente ou fora de (0, 1]"))
  s <- sinal_linha(v)
  if (is.na(s)) return(resultado(avisos = "p não informa direção: preencha t, beta ou m1/m2 com sinal"))
  g <- grupos(v)
  if (is.null(g)) return(resultado(avisos = "p_n exige n1 e n2 (ou n_total)"))
  gl <- g$n1 + g$n2 - 2
  t <- s * stats::qt(1 - v$p / 2, gl)
  avisos <- c("p bicaudal convertido em t com gl = N − 2; p arredondado distorce o efeito",
              if (g$dividido) "grupos assumidos iguais (n_total/2)")
  d <- d_de_t(t, g$n1, g$n2)
  resultado(d, var_d_n(d, g$n1, g$n2), gl, "p_n_t", 1L, avisos, var_de_n = TRUE)
}

#' Mann-Whitney pela tabela de conversões (Fiel Peres 2026, eq. 2): r = z/√N e depois r → d com p₁ = n₁/N.
#'
#' Escolha documentada: a rota antiga d = z·√(1/n₁ + 1/n₂) trata z como t de duas médias;
#' a da tabela passa pelo r de postos e coincide com ela só quando r² ≈ 0. O z fica na
#' coluna `t`, com sinal positivo quando o grupo 1 (tratamento) tem valores maiores.
conv_mann_whitney <- function(v) {
  z <- v$t
  avisos <- "Mann-Whitney via z (normal), não via t: r = z/√N, depois r → d com p1 = n1/N"
  if (is.na(z)) {
    if (is.na(v$p) || v$p <= 0 || v$p > 1) return(resultado(avisos = c(avisos, "exige z (coluna t) ou p")))
    s <- sinal_linha(v)
    if (is.na(s)) return(resultado(avisos = c(avisos, "p sem direção: preencha beta ou m1/m2 (medianas) com sinal")))
    z <- s * stats::qnorm(1 - v$p / 2)
    avisos <- c(avisos, "z reconstruído do p bicaudal: conferir se o p é bilateral")
  } else {
    avisos <- c(avisos, "coluna t interpretada como z padronizado do teste")
    dif <- v$m1 - v$m2
    if (!is.na(dif) && dif != 0 && z != 0 && sign(dif) != sign(z)) {
      avisos <- c(avisos, "sinal de z oposto a m1 − m2: conferir o sentido do z (o software ordena os grupos)")
    }
  }
  g <- grupos(v)
  if (is.null(g)) return(resultado(avisos = c(avisos, "exige n1 e n2 (ou n_total)")))
  n <- g$n1 + g$n2
  r <- z / sqrt(n)
  if (abs(r) >= 1) return(resultado(avisos = c(avisos, "|z|/√N >= 1: z incompatível com o N informado")))
  if (g$dividido) avisos <- c(avisos, "grupos assumidos iguais (n_total/2)")
  d <- d_de_r_grupos(r, g$n1, g$n2)
  resultado(d, var_d_n(d, g$n1, g$n2), n - 2, "mann_whitney_z", 1L, avisos, var_de_n = TRUE)
}

CAMPOS_QUARTIS <- c("q1_1", "q3_1", "q1_2", "q3_2")

#' Medianas → médias e DP. m1/m2 guardam as medianas.
#'
#' Com quartis nas colunas extras q1_1, q3_1, q1_2, q3_2 e n por grupo: Wan et al. (2014,
#' cenário S3), média ≈ (q1 + m + q3)/3 e DP ≈ (q3 − q1)/η(n) (`mediana_iqr_wan`).
#' Sem quartis, sd1/sd2 guardam a amplitude interquartil e vale a aproximação da Cochrane
#' (média ≈ mediana, DP ≈ IQR/1,35), com formula_id próprio (`mediana_iqr_aprox`).
conv_mediana_iqr <- function(v, q = list()) {
  q <- lapply(CAMPOS_QUARTIS, function(k) if (is.null(q[[k]]) || length(q[[k]]) == 0L) NA_real_ else q[[k]])
  names(q) <- CAMPOS_QUARTIS
  aviso_normal <- "pressupõe distribuição aproximadamente normal; medianas costumam ser relatadas por assimetria"
  if (all(!is.na(c(unlist(q), v$m1, v$m2, v$n1, v$n2)))) {
    if (v$n1 < 2 || v$n2 < 2) return(resultado(avisos = "mediana_iqr exige n >= 2 em cada grupo"))
    if (q$q3_1 <= q$q1_1 || q$q3_2 <= q$q1_2) return(resultado(avisos = "quartis inválidos: q3 deve ser maior que q1"))
    if (v$m1 < q$q1_1 || v$m1 > q$q3_1 || v$m2 < q$q1_2 || v$m2 > q$q3_2) {
      return(resultado(avisos = "mediana fora de [q1, q3]: conferir a extração"))
    }
    v2 <- v
    v2$m1 <- (q$q1_1 + v$m1 + q$q3_1) / 3
    v2$m2 <- (q$q1_2 + v$m2 + q$q3_2) / 3
    v2$sd1 <- (q$q3_1 - q$q1_1) / eta_wan(v$n1)
    v2$sd2 <- (q$q3_2 - q$q1_2) / eta_wan(v$n2)
    return(conv_md_sd(v2, "mediana_iqr_wan", 1L,
                      c("média ≈ (q1 + mediana + q3)/3 e DP ≈ (q3 − q1)/η(n) (Wan et al. 2014)", aviso_normal)))
  }
  avisos <- c("média ≈ mediana e DP ≈ IQR/1,35 (sd1/sd2 = IQR; sem quartis não se aplica Wan et al.)", aviso_normal)
  if (any(!is.na(unlist(q)))) avisos <- c(avisos, "quartis incompletos (q1_1, q3_1, q1_2, q3_2): usado o IQR de sd1/sd2")
  if (is.na(v$sd1) || is.na(v$sd2)) {
    return(resultado(avisos = c(avisos, "mediana_iqr exige quartis q1_1, q3_1, q1_2, q3_2 ou IQR em sd1/sd2")))
  }
  v2 <- v
  v2$sd1 <- v$sd1 / 1.35
  v2$sd2 <- v$sd2 / 1.35
  conv_md_sd(v2, "mediana_iqr_aprox", 1L, avisos)
}

conv_informado <- function(v, tipo, valor) {
  if (is.na(valor)) return(resultado(avisos = sprintf("%s informado ausente (colunas %s ou beta)", tipo, tipo)))
  se <- if (!is.na(v$se)) v$se else se_de_ic(v$ci_lo, v$ci_hi)
  g <- grupos(v)
  gl <- if (!is.null(g)) g$n1 + g$n2 - 2 else if (!is.na(v$df)) v$df else NA_real_
  j <- fator_j(gl)
  if (tipo == "g") {
    d <- if (!is.na(j)) valor / j else valor
    if (!is.na(se) && se > 0) {
      vd <- if (!is.na(j)) se^2 / j^2 else se^2
      return(resultado(d, vd, gl, "g_informado", 0L, "g e EP informados pelo estudo", ja_g = TRUE))
    }
    if (is.null(g)) return(resultado(avisos = "g informado exige se, IC ou tamanhos de amostra"))
    return(resultado(d, var_d_n(d, g$n1, g$n2), gl, "g_informado", as.integer(g$dividido),
                     "g informado; variância por n", var_de_n = TRUE))
  }
  if (!is.na(se) && se > 0) return(resultado(valor, se^2, gl, "d_informado", 0L, "d e EP informados pelo estudo"))
  if (is.null(g)) return(resultado(avisos = "d informado exige se, IC ou tamanhos de amostra"))
  resultado(valor, var_d_n(valor, g$n1, g$n2), gl, "d_informado", as.integer(g$dividido),
            "d informado; variância por n", var_de_n = TRUE)
}

# ---------------------------------------------------------------------------
# Desfechos binários (avaliação de políticas: matrícula, evasão, emprego formal...)
# ---------------------------------------------------------------------------

CAMPOS_BINARIOS <- c("p0", "p1", "efeito_pp", "se_pp")

#' LPM, DiD e RDD: a diferença de proporções vem de um coeficiente de regressão (ajustado).
PADRAO_REGRESSAO_BINARIA <- paste0(
  "(^|[^a-z])(did|dd|rdd|lpm|mpl|its)([^a-z]|$)|diferencas?[ _-]+em[ _-]+diferencas?|",
  "differences?[ _-]+in[ _-]+differences?|descontinu|discontinu|probabilidade[ _-]+linear|",
  "linear[ _-]+probability|rdd_local"
)

eh_regressao_binaria <- function(linha) {
  texto <- paste(vapply(c("desenho", "modelo", "estimando"), function(k) {
    if (is.null(linha[[k]])) "" else as.character(linha[[k]])
  }, character(1)), collapse = " ")
  grepl(PADRAO_REGRESSAO_BINARIA, ascii_minusculo(texto))
}

#' log OR → d (Chinn 2000; Borenstein eq. 7.1–7.2): d = ln(OR)·√3/π, Var(d) = Var(ln OR)·3/π².
d_de_log_or <- function(log_or, var_log_or) {
  list(d = log_or * sqrt(3) / pi, vd = var_log_or * 3 / pi^2)
}

logit_p <- function(p) log(p / (1 - p))

#' Diferença de proporções → d via log OR (Chinn 2000).
#'
#' p0 = proporção no grupo de comparação (controle); p1 = proporção no tratamento, ou
#' p1 = p0 + efeito_pp/100 quando o texto dá o efeito em pontos percentuais (coeficiente de LPM,
#' DiD ou RDD). ln OR = logit(p1) − logit(p0).
#' Variância de ln OR, nesta ordem:
#' - EP do efeito em pp (`se_pp`, ou IC95 do efeito em pp em ci_lo/ci_hi): método delta com p0
#'   fixo, Var(ln OR) = (se_pp/100)² / [p1(1 − p1)]². Carrega o ajuste do estudo (cluster, covariáveis).
#' - contagens (n1, n2): Var(ln OR) = 1/(n1·p1) + 1/(n1·(1 − p1)) + 1/(n2·p0) + 1/(n2·(1 − p0)).
#' formula_id `dif_prop_contagens` (aproximado = 0) só com p1 e p0 observados, contagens e desenho que
#' não é LPM/DiD/RDD; todo o resto sai como `dif_prop_lpm` (aproximado = 1): efeito em pp, EP do
#' coeficiente ou desenho de regressão, porque a proporção do tratado é reconstruída e o log OR de um
#' efeito ajustado não equivale ao de uma tabela 2×2.
conv_dif_prop <- function(v, b, regressao = FALSE) {
  avisos <- "d via log OR (Chinn 2000): pressupõe distribuição logística latente"
  p0 <- b$p0
  if (is.na(p0) || p0 <= 0 || p0 >= 1) {
    return(resultado(avisos = c(avisos, "dif_prop exige p0 (proporção no controle) em (0, 1); percentual vira proporção")))
  }
  usa_pp <- is.na(b$p1) && !is.na(b$efeito_pp)
  p1 <- if (!is.na(b$p1)) b$p1 else if (usa_pp) p0 + b$efeito_pp / 100 else NA_real_
  if (is.na(p1)) return(resultado(avisos = c(avisos, "dif_prop exige p1 ou efeito_pp (pontos percentuais)")))
  if (p1 <= 0 || p1 >= 1) {
    return(resultado(avisos = c(avisos, sprintf("p1 = %g fora de (0, 1): confira p0 e efeito_pp (pp, não proporção)", p1))))
  }
  if (!is.na(b$p1) && !is.na(b$efeito_pp) && abs(b$p1 - p0 - b$efeito_pp / 100) > 0.0051) {
    avisos <- c(avisos, "p1 − p0 difere de efeito_pp/100: usado p1")
  }
  if (usa_pp) avisos <- c(avisos, "p1 reconstruído como p0 + efeito_pp/100")
  log_or <- logit_p(p1) - logit_p(p0)
  se_pp <- b$se_pp
  if (is.na(se_pp) && !is.na(b$efeito_pp)) se_pp <- se_de_ic(v$ci_lo, v$ci_hi)
  g <- grupos(v)
  gl <- if (!is.null(g)) g$n1 + g$n2 - 2 else NA_real_
  aproximado <- usa_pp || regressao || !is.na(se_pp)
  if (!is.na(se_pp) && se_pp > 0) {
    var_log_or <- (se_pp / 100)^2 / (p1 * (1 - p1))^2
    avisos <- c(avisos, "Var(ln OR) pelo EP do efeito em pp (método delta, p0 fixo)")
    var_de_n <- FALSE
  } else if (!is.null(g) && !g$dividido) {
    var_log_or <- 1 / (g$n1 * p1) + 1 / (g$n1 * (1 - p1)) + 1 / (g$n2 * p0) + 1 / (g$n2 * (1 - p0))
    var_de_n <- TRUE
    if (aproximado) avisos <- c(avisos, "variância pelas contagens ignora o ajuste do modelo (sem se_pp)")
  } else if (!is.null(g)) {
    var_log_or <- 1 / (g$n1 * p1) + 1 / (g$n1 * (1 - p1)) + 1 / (g$n2 * p0) + 1 / (g$n2 * (1 - p0))
    var_de_n <- TRUE
    aproximado <- TRUE
    avisos <- c(avisos, "grupos assumidos iguais (n_total/2)")
  } else {
    return(resultado(avisos = c(avisos, "dif_prop exige se_pp (ou IC do efeito em pp) ou n1 e n2")))
  }
  if (regressao) avisos <- c(avisos, "efeito de LPM/DiD/RDD: conversão aproximada (sensibilidade sem aproximados)")
  conv <- d_de_log_or(log_or, var_log_or)
  resultado(conv$d, conv$vd, gl, if (aproximado) "dif_prop_lpm" else "dif_prop_contagens",
            as.integer(aproximado), avisos, var_de_n = var_de_n)
}

#' Razão de riscos (RR) com IC → OR com p0 (Zhang & Yu 1998) → d via log OR (Chinn 2000).
#'
#' RR vai em `or_` (com tipo_estatistica = rr) e o IC95 em ci_lo/ci_hi, na escala da razão; `se`, se
#' informado, é o EP de ln(RR). OR = RR·(1 − p0)/(1 − RR·p0); pelo método delta com p0 fixo,
#' EP(ln OR) = EP(ln RR)/(1 − RR·p0). Sempre aproximado.
conv_rr <- function(v, b) {
  avisos <- c("RR convertido em OR com p0 (Zhang & Yu 1998) e d via log OR (Chinn 2000)",
              "EP(ln OR) = EP(ln RR)/(1 − RR·p0) (método delta, p0 fixo)")
  rr <- v$or_
  if (is.na(rr) || rr <= 0) return(resultado(avisos = "rr exige a razão de riscos (> 0) em or_"))
  p0 <- b$p0
  if (is.na(p0) || p0 <= 0 || p0 >= 1) return(resultado(avisos = c(avisos, "rr exige p0 (proporção no controle) em (0, 1)")))
  if (rr * p0 >= 1) return(resultado(avisos = c(avisos, sprintf("RR·p0 = %g >= 1: p1 impossível; confira RR e p0", rr * p0))))
  se_log_rr <- v$se
  if (is.na(se_log_rr) && !is.na(v$ci_lo) && !is.na(v$ci_hi) && v$ci_lo > 0) {
    se_log_rr <- se_de_ic(log(v$ci_lo), log(v$ci_hi))
  } else if (!is.na(se_log_rr)) {
    avisos <- c(avisos, "se interpretado como EP de ln(RR)")
  }
  if (is.na(se_log_rr) || se_log_rr <= 0) return(resultado(avisos = c(avisos, "rr exige EP de ln(RR) ou IC95")))
  or <- rr * (1 - p0) / (1 - rr * p0)
  conv <- d_de_log_or(log(or), (se_log_rr / (1 - rr * p0))^2)
  n <- if (!is.na(v$n_total)) v$n_total else v$n1 + v$n2
  resultado(conv$d, conv$vd, if (!is.na(n)) n - 2 else NA_real_, "rr_logit", 1L, avisos)
}

#' Infere tipo_estatistica pelas colunas preenchidas quando o campo vem vazio.
inferir_tipo <- function(v, b = list(p0 = NA_real_, p1 = NA_real_, efeito_pp = NA_real_)) {
  if (!is.na(b$p0) && (!is.na(b$p1) || !is.na(b$efeito_pp))) return("dif_prop")
  if (all(!is.na(c(v$m1, v$sd1, v$n1, v$m2, v$sd2, v$n2)))) return("md_sd")
  if (!is.na(v$beta) && !is.na(v$sdy)) return("beta_sd")
  if (!is.na(v$t)) return("t")
  if (!is.na(v$or_)) return("or")
  if (!is.na(v$r)) return("r")
  if (!is.na(v$f)) return("f1")
  if (!is.na(v$p)) return("p_n")
  ""
}

CAMPOS_NUMERICOS <- c("m1", "sd1", "n1", "m2", "sd2", "n2", "t", "df", "f", "beta", "se", "sdy",
                      "or_", "ci_lo", "ci_hi", "r", "p", "n_total", "cluster", "icc")

#' Converte uma linha (lista de textos) em yi/vi/sei alinhados.
converter_linha <- function(linha) {
  v <- lapply(linha[CAMPOS_NUMERICOS], como_num)
  names(v) <- CAMPOS_NUMERICOS
  tipo <- ascii_minusculo(trimws(linha$tipo_estatistica))
  avisos_pre <- character(0)

  vazio_saida <- function(formula_id, avisos, sinal = "") {
    list(yi = NA_real_, vi = NA_real_, sei = NA_real_, formula_id = formula_id,
         aproximado = NA_integer_, sinal_alinhado = sinal, aviso = paste(unique(avisos), collapse = "; "))
  }

  if (eh_revisao(linha$desenho)) {
    return(vazio_saida("rejeitado_revisao",
                       "revisão/meta-análise não entra como estudo primário: usar na bola de neve ou num overview"))
  }
  # [[ ]] e não $: `$` faz casamento parcial em listas ("d" casaria com "df").
  extra_g <- if (!is.null(linha[["g"]])) como_num(linha[["g"]]) else NA_real_
  extra_d <- if (!is.null(linha[["d"]])) como_num(linha[["d"]]) else NA_real_
  quartis <- lapply(CAMPOS_QUARTIS, function(k) if (!is.null(linha[[k]])) como_num(linha[[k]]) else NA_real_)
  names(quartis) <- CAMPOS_QUARTIS
  m_preditores <- if (!is.null(linha[["m_preditores"]])) como_num(linha[["m_preditores"]]) else NA_real_
  binarios <- lapply(CAMPOS_BINARIOS, function(k) if (!is.null(linha[[k]])) como_num(linha[[k]]) else NA_real_)
  names(binarios) <- CAMPOS_BINARIOS
  if (!nzchar(tipo)) {
    tipo <- inferir_tipo(v, binarios)
    if (nzchar(tipo)) avisos_pre <- sprintf("tipo_estatistica vazio: inferido '%s'", tipo)
  }

  res <- switch(tipo,
    dif_prop = conv_dif_prop(v, binarios, regressao = eh_regressao_binaria(linha)),
    rr = conv_rr(v, binarios),
    md_sd = conv_md_sd(v),
    t = conv_t(v),
    f1 = , f = conv_f1(v),
    beta_sd = conv_beta_sd(v, trimws(as.character(linha$estimando))),
    or = , or_ = conv_or(v),
    r = conv_r(v),
    parcial_r = conv_r(v, parcial = TRUE, m = m_preditores),
    p_n = conv_p_n(v),
    g = conv_informado(v, "g", if (!is.na(extra_g)) extra_g else v$beta),
    d = conv_informado(v, "d", if (!is.na(extra_d)) extra_d else v$beta),
    mann_whitney = conv_mann_whitney(v),
    mediana_iqr = conv_mediana_iqr(v, quartis),
    resultado(avisos = sprintf("tipo_estatistica desconhecido: '%s'", tipo))
  )
  avisos <- c(avisos_pre, res$avisos)
  if (is.na(res$d) || is.na(res$vd)) {
    return(vazio_saida(if (res$formula_id == "sem_calculo") "sem_calculo" else res$formula_id, avisos))
  }

  # Para g informado, conv_informado já devolveu d = g/J e Var(d) = Var(g)/J²,
  # então a mesma multiplicação abaixo recupera exatamente o g e a variância do estudo.
  j <- fator_j(res$gl)
  if (is.na(j)) {
    yi <- res$d
    vi <- res$vd
    if (!res$ja_g) avisos <- c(avisos, "gl indisponível: sem correção J (valor é d, não g)")
  } else {
    yi <- res$d * j
    vi <- res$vd * j^2
  }

  formula_id <- res$formula_id
  if (!vazio(linha$cluster)) {
    m <- v$cluster
    icc <- v$icc
    if (!is.na(m) && m > 1 && !is.na(icc) && icc >= 0 && icc <= 1 && res$var_de_n) {
      vi <- vi * (1 + (m - 1) * icc)
      formula_id <- paste0(formula_id, "+de_cluster")
      avisos <- c(avisos, sprintf("variância multiplicada pelo efeito de desenho 1 + (%g − 1)·%g", m, icc))
    } else if (res$var_de_n && (is.na(icc) || is.na(m))) {
      avisos <- c(avisos, "desenho em cluster sem tamanho médio (coluna cluster) e ICC: variância subestimada")
    } else if (!res$var_de_n) {
      avisos <- c(avisos, "cluster: EP informado presumido já ajustado ao delineamento")
    }
  }

  fator <- fator_direcao(linha$direcao_desejada)
  if (is.na(fator)) {
    sinal <- "sem_direcao"
    avisos <- c(avisos, "direcao_desejada ausente: sinal bruto; linha fora da síntese até declarar aumentar|reduzir")
  } else if (fator < 0) {
    yi <- -yi
    sinal <- "invertido"
  } else {
    sinal <- "mantido"
  }
  if (abs(yi) > 2) avisos <- c(avisos, "|g| > 2: conferir extração (EP lido como DP, unidades, sinal)")
  if (!is.finite(vi) || vi <= 0) {
    avisos <- c(avisos, "variância não positiva")
    vi <- NA_real_
  }
  list(yi = yi, vi = vi, sei = if (is.na(vi)) NA_real_ else sqrt(vi), formula_id = formula_id,
       aproximado = res$aproximado, sinal_alinhado = sinal, aviso = paste(unique(avisos), collapse = "; "))
}

#' Converte um data.frame inteiro. Devolve o data.frame com as colunas calculadas.
calcular_efeitos <- function(df) {
  df <- completar_colunas(df, COLUNAS_EFEITOS_EXTRAIDOS)
  ausentes <- attr(df, "colunas_ausentes")
  n <- nrow(df)
  yi <- vi <- sei <- rep(NA_real_, n)
  formula_id <- sinal <- aviso <- character(n)
  aproximado <- rep(NA_integer_, n)
  for (i in seq_len(n)) {
    linha <- as.list(df[i, , drop = FALSE])
    r <- converter_linha(linha)
    yi[i] <- r$yi
    vi[i] <- r$vi
    sei[i] <- r$sei
    formula_id[i] <- r$formula_id
    aproximado[i] <- r$aproximado
    sinal[i] <- r$sinal_alinhado
    aviso[i] <- r$aviso
  }
  df$yi <- yi
  df$vi <- vi
  df$sei <- sei
  df$formula_id <- formula_id
  df$aproximado <- aproximado
  df$sinal_alinhado <- sinal
  df$aviso <- aviso
  extras <- setdiff(names(df), COLUNAS_EFEITOS_CALCULADOS)
  saida <- df[, c(COLUNAS_EFEITOS_CALCULADOS, extras), drop = FALSE]
  attr(saida, "colunas_ausentes") <- ausentes
  saida
}

#' Lê a tabela de conversões para conferir que todo formula_id está documentado.
formulas_mapeadas <- function() {
  caminho <- normalizePath(file.path(RS_DIR_R, "..", "..", "assets", "mapas", "conversoes_efeito.csv"),
                           mustWork = FALSE)
  if (!file.exists(caminho)) return(NULL)
  ler_csv_texto(caminho)$formula_id
}

main_efeitos <- function(args) {
  entrada <- cli_arg(args, "in", obrigatorio = TRUE)
  saida <- cli_arg(args, "out", obrigatorio = TRUE)
  # δ (SESOI) só descreve quantos efeitos individuais têm IC dentro de ±δ; a decisão
  # de "Nulo" é da célula (meta.R/caixa) com δ fixado no protocolo.
  delta <- cli_num(args, "delta", 0.1)
  df <- ler_csv_texto(entrada)
  if (nrow(df) == 0L) cli_falhar("entrada sem linhas", SAIDA_ERRO_DADOS)
  if (!"tipo_estatistica" %in% names(df) && !any(c("m1", "t", "beta", "or_", "r", "p", "p0") %in% names(df))) {
    cli_falhar("entrada não tem tipo_estatistica nem colunas de estatística reconhecíveis", SAIDA_ERRO_DADOS)
  }
  calc <- calcular_efeitos(df)
  escrever_csv(calc, saida)

  base_formula <- sub("\\+de_cluster$", "", calc$formula_id)
  mapa <- formulas_mapeadas()
  sem_mapa <- if (is.null(mapa)) character(0) else
    setdiff(unique(base_formula[!base_formula %in% c("sem_calculo", "rejeitado_revisao")]), mapa)
  calculados <- !is.na(calc$yi) & !is.na(calc$vi)
  lo <- calc$yi - Z975 * calc$sei
  hi <- calc$yi + Z975 * calc$sei
  por_formula <- as.list(table(calc$formula_id))

  message(sprintf("efeitos: %d linhas, %d calculadas, %d aproximadas, %d revisões rejeitadas",
                  nrow(calc), sum(calculados), sum(calc$aproximado == 1L, na.rm = TRUE),
                  sum(calc$formula_id == "rejeitado_revisao")))
  list(codigo = SAIDA_OK, resumo = list(
    ok = TRUE, comando = "efeitos", entrada = entrada, saida = saida,
    n_linhas = nrow(calc),
    n_calculados = sum(calculados),
    n_aproximados = sum(calc$aproximado == 1L, na.rm = TRUE),
    n_rejeitados_revisao = sum(calc$formula_id == "rejeitado_revisao"),
    n_sem_calculo = sum(calc$formula_id == "sem_calculo" | (!calculados & calc$formula_id != "rejeitado_revisao")),
    n_sem_direcao = sum(calc$sinal_alinhado == "sem_direcao"),
    n_invertidos = sum(calc$sinal_alinhado == "invertido"),
    n_g_maior_2 = sum(abs(calc$yi) > 2, na.rm = TRUE),
    n_ajuste_cluster = sum(grepl("+de_cluster", calc$formula_id, fixed = TRUE)),
    # Informativo: a verificação humana é exigida no G7 (rs.py analise verificar-efeitos).
    n_nao_verificados_humano = sum(calculados & !eh_verdadeiro(coluna(calc, "verificado_humano"))),
    delta = delta,
    # mesmo critério de rs.py caixa (Nulo): -δ <= ic_inf e ic_sup <= δ
    n_ic_dentro_delta = sum(calculados & lo >= -delta & hi <= delta, na.rm = TRUE),
    por_formula = por_formula,
    colunas_ausentes = as.list(attr(calc, "colunas_ausentes")),
    formulas_sem_mapa = as.list(sem_mapa)
  ))
}

if (sys.nframe() == 0L) {
  quit(status = cli_executar(function() main_efeitos(cli_args())), save = "no")
}
