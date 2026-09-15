# swim.R — síntese sem meta-análise (SWiM): direção do efeito, teste de sinal e gráficos.
#
# USO
#     Rscript swim.R --in=06-analise/efeitos.csv --out-dir=06-analise \
#         [--grupo=construto_outcome|familia_intervencao,construto_outcome] \
#         [--limiar-consistencia=0.7] [--separar-desenho=sim|nao] [--excluir-rob=nenhum|critico]
#
# Entrada: saída de efeitos.R (ou extração com direcao_desejada e sinal em t/beta/m1−m2/r).
# Saídas em --out-dir:
#   swim_resumo.json                    contagens por grupo, proporção benéfica com IC, teste de sinal
#   tabelas/swim_direcao.csv            direção por estudo × grupo
#   figuras/direcao_efeito.png|pdf      effect direction plot (Thomson & Thomas 2013)
#   figuras/albatross_<grupo>.png       quando há estudos só com p e n (Harrison et al. 2017)
#
# Por que assim (references/07a-sintese-quantitativa.md; SWiM, Campbell et al. 2020; Cochrane v6.5 cap. 12)
# - Direção pelo estimador pontual, nunca pela significância: "p > 0,05" não é
#   "sem efeito". Por isso o vote counting é por DIREÇÃO, com teste de sinal
#   binomial exato (H0: proporção benéfica = 0,5) e IC de Clopper-Pearson.
# - Um voto por estudo. Estudo com vários efeitos: vale o modelo_principal; sem ele,
#   a regra de Boon & Thomson (2021): >= 70% dos efeitos numa direção define a
#   direção do estudo; abaixo disso o estudo é "misto" e fica fora do teste.
# - Os números saem prontos para as regras da caixa de ferramentas (>= 5 estudos,
#   >= 70% benéficos, p < 0,05, não só risco alto), mas o rótulo exige certeza
#   GRADE e é decidido por `rs.py caixa`, não aqui.
# - Albatross: eixo x = p bilateral em escala log com o lado indicando a direção;
#   contornos de d = 0,2; 0,5; 0,8 assumindo dois grupos iguais (z ≈ d·√N / 2).
# - --excluir-rob=critico (mesmo contrato de meta.R): a direção de cada estudo é decidida
#   antes com todas as suas linhas (modelo principal ou regra de 70%), e só então o estudo
#   com rob_geral crítico sai do teste de sinal principal, do effect direction plot e do
#   albatross. O rob_geral do estudo é o do modelo principal (senão, o primeiro informado).
#   A contagem com os críticos vai para `sensibilidade.com_rob_critico` de cada grupo, e
#   `swim_direcao.csv` marca `excluido_rob_critico`.

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

K_MIN_REGRA_CAIXA <- 5L
PROP_MIN_REGRA_CAIXA <- 0.70
CONTORNOS_ALBATROSS <- c(0.2, 0.5, 0.8)
PADRAO_ALTO_RISCO_SWIM <- "alto|high|critico|critical|serio|serious|grave"

# ---------------------------------------------------------------------------
# Direção por estudo e teste de sinal
# ---------------------------------------------------------------------------

rotulo_direcao <- function(x) {
  ifelse(is.na(x), "sem_direcao", ifelse(x > 0, "benefico", ifelse(x < 0, "danoso", "nulo")))
}

#' Direção de um estudo a partir das direções dos seus efeitos.
direcao_estudo <- function(dirs, principal, limiar = 0.7) {
  if (sum(principal) == 1L) {
    return(list(direcao = rotulo_direcao(dirs[principal]), regra = "modelo_principal"))
  }
  validos <- dirs[!is.na(dirs)]
  if (!length(validos)) return(list(direcao = "sem_direcao", regra = "sem_direcao"))
  if (length(validos) == 1L) return(list(direcao = rotulo_direcao(validos), regra = "efeito_unico"))
  if (all(validos == 0)) return(list(direcao = "nulo", regra = "todos_nulos"))
  if (mean(validos > 0) >= limiar) return(list(direcao = "benefico", regra = sprintf("consistencia>=%.0f%%", 100 * limiar)))
  if (mean(validos < 0) >= limiar) return(list(direcao = "danoso", regra = sprintf("consistencia>=%.0f%%", 100 * limiar)))
  list(direcao = "misto", regra = sprintf("consistencia<%.0f%%", 100 * limiar))
}

#' Tabela estudo × grupo com direção, n e risco de viés.
direcoes_por_estudo <- function(d, limiar) {
  d$.dir <- direcao_linha(d)
  d$.principal <- eh_verdadeiro(coluna(d, "modelo_principal"))
  d$.n <- n_amostra(d)
  rob <- coluna(d, "rob_geral")
  chave <- coluna(d, "chave")
  chaves <- unique(paste(d$.grupo, d$.estudo, sep = "\r"))
  linhas <- lapply(chaves, function(ch) {
    idx <- which(paste(d$.grupo, d$.estudo, sep = "\r") == ch)
    r <- direcao_estudo(d$.dir[idx], d$.principal[idx], limiar)
    n_valid <- d$.n[idx][!is.na(d$.n[idx])]
    principal_i <- idx[d$.principal[idx]]
    rob_principal <- if (length(principal_i) == 1L) rob[principal_i][!vazio(rob[principal_i])] else character(0)
    rob_i <- if (length(rob_principal)) rob_principal else rob[idx][!vazio(rob[idx])]
    chave_i <- chave[idx][!vazio(chave[idx])]
    data.frame(
      grupo = d$.grupo[idx[1]], id_estudo = d$.estudo[idx[1]],
      chave = if (length(chave_i)) chave_i[1] else "",
      direcao = r$direcao, regra = r$regra, n_efeitos = length(idx),
      n_beneficos = sum(d$.dir[idx] > 0, na.rm = TRUE), n_danosos = sum(d$.dir[idx] < 0, na.rm = TRUE),
      n_amostra = if (length(n_valid)) max(n_valid) else NA_real_,
      rob_geral = if (length(rob_i)) rob_i[1] else "",
      stringsAsFactors = FALSE
    )
  })
  do.call(rbind, linhas)
}

#' Teste de sinal binomial exato e proporção benéfica com IC de Clopper-Pearson.
teste_sinal <- function(n_benefico, n_danoso, nivel = 0.95) {
  n <- n_benefico + n_danoso
  if (n == 0L) {
    return(list(n = 0L, proporcao_benefica = NULL, ic = NULL, p_bilateral = NULL))
  }
  bt <- stats::binom.test(n_benefico, n, p = 0.5, alternative = "two.sided", conf.level = nivel)
  list(n = n, proporcao_benefica = n_benefico / n, ic = as.numeric(bt$conf.int),
       p_bilateral = as.numeric(bt$p.value), metodo = "binomial exato; IC Clopper-Pearson")
}

resumir_grupo <- function(tab, nivel) {
  cont <- function(x) sum(tab$direcao == x)
  sinal <- teste_sinal(cont("benefico"), cont("danoso"), nivel)
  alto <- grepl(PADRAO_ALTO_RISCO_SWIM, ascii_minusculo(tab$rob_geral))
  com_direcao <- tab$direcao %in% c("benefico", "danoso")
  rob_informado <- !vazio(tab$rob_geral)
  # "Não só risco alto": nulo sem RoB informado; TRUE só se todos os estudos
  # do teste de sinal têm RoB informado e alto/crítico.
  so_risco_alto <- if (!any(rob_informado[com_direcao])) NULL else
    all(rob_informado[com_direcao] & alto[com_direcao])
  list(
    k_estudos = nrow(tab),
    n_estudos = sinal$n,
    n_beneficos = cont("benefico"), n_danosos = cont("danoso"), n_mistos = cont("misto"),
    n_nulos = cont("nulo"), n_sem_direcao = cont("sem_direcao"),
    proporcao_benefica = sinal$proporcao_benefica,
    ic_proporcao = sinal$ic,
    p_sinal = sinal$p_bilateral,
    so_risco_alto = so_risco_alto,
    teste_sinal = sinal,
    insumos_regra_caixa = list(
      k_minimo = K_MIN_REGRA_CAIXA, proporcao_minima = PROP_MIN_REGRA_CAIXA,
      atinge_k = sinal$n >= K_MIN_REGRA_CAIXA,
      atinge_proporcao_benefica = !is.null(sinal$proporcao_benefica) && sinal$proporcao_benefica >= PROP_MIN_REGRA_CAIXA,
      atinge_proporcao_danosa = !is.null(sinal$proporcao_benefica) && (1 - sinal$proporcao_benefica) >= PROP_MIN_REGRA_CAIXA,
      p_menor_005 = !is.null(sinal$p_bilateral) && sinal$p_bilateral < 0.05,
      nota = "n_estudos = estudos com direção definida (entram no teste de sinal); rótulo exige certeza GRADE e é decidido em rs.py caixa"
    ),
    estudos = as.list(unique(ifelse(vazio(tab$chave), tab$id_estudo, tab$chave)))
  )
}

# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

#' Effect direction plot: linhas = estudos, colunas = grupos; triângulo para cima benéfico,
#' para baixo danoso, losango misto; tamanho pela amostra; cor pelo risco de viés.
desenhar_direcao <- function(tab) {
  estudos <- unique(ifelse(vazio(tab$chave), tab$id_estudo, tab$chave))
  grupos <- unique(tab$grupo)
  rot_estudo <- ifelse(vazio(tab$chave), tab$id_estudo, tab$chave)
  y <- match(rot_estudo, estudos)
  x <- match(tab$grupo, grupos)
  pch <- c(benefico = 24, danoso = 25, misto = 23, nulo = 21, sem_direcao = 4)[tab$direcao]
  n <- tab$n_amostra
  cex <- ifelse(is.na(n), 1, ifelse(n < 300, 1.2, ifelse(n <= 1000, 1.8, 2.4)))
  rob <- ascii_minusculo(tab$rob_geral)
  cor <- ifelse(vazio(tab$rob_geral), "grey70",
                ifelse(grepl(PADRAO_ALTO_RISCO_SWIM, rob), "#d7301f",
                       ifelse(grepl("baixo|low", rob), "#1a9850", "#fdae61")))
  margem_esq <- min(12, 2 + max(nchar(estudos)) * 0.45)
  margem_inf <- min(12, 2 + max(nchar(grupos)) * 0.35)
  graphics::par(mar = c(margem_inf, margem_esq, 7, 1))
  graphics::plot(NA, xlim = c(0.5, length(grupos) + 0.5), ylim = c(length(estudos) + 0.5, 0.5),
                 xaxt = "n", yaxt = "n", xlab = "", ylab = "")
  graphics::title("Direção do efeito por estudo", line = 5.2)
  graphics::axis(1, at = seq_along(grupos), labels = grupos, las = 2, cex.axis = 0.7)
  graphics::axis(2, at = seq_along(estudos), labels = estudos, las = 1, cex.axis = 0.7)
  graphics::abline(h = seq_along(estudos), col = "grey92")
  graphics::points(x, y, pch = pch, cex = cex, bg = cor, col = "grey20")
  graphics::legend("top", inset = c(0, -0.11), xpd = TRUE, horiz = TRUE, bty = "n", cex = 0.7,
                   pch = c(24, 25, 23, 21), pt.bg = "grey80",
                   legend = c("benéfico", "danoso", "misto", "nulo"))
  graphics::legend("top", inset = c(0, -0.06), xpd = TRUE, horiz = TRUE, bty = "n", cex = 0.7,
                   pch = 22, pt.bg = c("#1a9850", "#fdae61", "#d7301f", "grey70"), pt.cex = 1.3,
                   legend = c("RoB baixo", "RoB intermediário", "RoB alto/crítico", "RoB não informado"))
}

salvar_direcao <- function(tab, out_dir) {
  base <- file.path(out_dir, "figuras", "direcao_efeito")
  n_estudos <- length(unique(paste(tab$chave, tab$id_estudo)))
  altura <- max(4, 2.5 + 0.28 * n_estudos)
  largura <- max(7.5, 3 + 1.1 * length(unique(tab$grupo)))
  desenhar <- function() desenhar_direcao(tab)
  unlist(list(salvar_grafico(paste0(base, ".png"), largura, altura, desenhar),
              salvar_grafico(paste0(base, ".pdf"), largura, altura, desenhar)))
}

#' Pontos do albatross: p bilateral (informado ou de yi/sei), N e direção.
pontos_albatross <- function(d) {
  p <- como_num(coluna(d, "p"))
  yi <- como_num(coluna(d, "yi"))
  sei <- como_num(coluna(d, "sei"))
  alinhado <- coluna(d, "sinal_alinhado") %in% c("mantido", "invertido")
  t <- como_num(coluna(d, "t"))
  gl <- como_num(coluna(d, "df"))
  p_t <- ifelse(!is.na(t) & !is.na(gl) & gl > 0, 2 * stats::pt(-abs(t), gl), NA_real_)
  p_calc <- ifelse(!is.na(yi) & !is.na(sei) & sei > 0 & alinhado, 2 * stats::pnorm(-abs(yi / sei)), NA_real_)
  p_final <- ifelse(!is.na(p) & p > 0 & p <= 1, p, ifelse(!is.na(p_t), p_t, p_calc))
  dir <- direcao_linha(d)
  n <- n_amostra(d)
  ok <- !is.na(p_final) & !is.na(n) & n > 0 & !is.na(dir) & dir != 0
  data.frame(estudo = d$.estudo[ok], p = pmax(p_final[ok], 1e-12), n = n[ok], direcao = dir[ok],
             so_p = is.na(yi[ok]) | is.na(sei[ok]))
}

desenhar_albatross <- function(pts, titulo) {
  x <- pts$direcao * -log10(pts$p)
  lim <- max(4, ceiling(max(abs(x))) + 0.5)
  n_grade <- exp(seq(log(max(4, min(pts$n) / 2)), log(max(pts$n) * 2), length.out = 200))
  graphics::par(mar = c(5, 5, 3, 1))
  graphics::plot(x, pts$n, log = "y", xlim = c(-lim, lim), ylim = range(n_grade),
                 pch = ifelse(pts$so_p, 1, 19), xaxt = "n",
                 xlab = "p bilateral (\u2190 danoso | benéfico \u2192)", ylab = "N (escala log)",
                 main = titulo, cex.main = 0.9)
  marcas <- seq(-floor(lim), floor(lim), by = 1)
  graphics::axis(1, at = marcas, labels = format(10^(-abs(marcas)), scientific = FALSE, drop0trailing = TRUE),
                 cex.axis = 0.7)
  graphics::abline(v = 0, col = "grey60")
  for (dd in CONTORNOS_ALBATROSS) {
    p_c <- 2 * stats::pnorm(-dd * sqrt(n_grade) / 2)
    xc <- -log10(pmax(p_c, 1e-300))
    graphics::lines(xc, n_grade, lty = 2, col = "grey40")
    graphics::lines(-xc, n_grade, lty = 2, col = "grey40")
    dentro <- which(xc <= lim * 0.95)
    if (length(dentro)) {
      j <- max(dentro)
      graphics::text(xc[j], n_grade[j], sprintf("d = %.1f", dd), cex = 0.6, pos = 2, col = "grey30")
    }
  }
  graphics::legend("bottomleft", bty = "n", cex = 0.7, pch = c(19, 1),
                   legend = c("com efeito calculado", "só p e N"))
}

salvar_albatross <- function(pts, arquivo, titulo) {
  salvar_grafico(arquivo, 7, 6, function() desenhar_albatross(pts, titulo))
}

# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------

executar_swim <- function(df, opcoes) {
  excluir <- linha_excluida_sintese(df)
  d <- df[!excluir, , drop = FALSE]
  d$.estudo <- id_estudo_efetivo(d)
  d$.grupo <- rotulo_grupo(d, opcoes$grupo, opcoes$separar_desenho)
  if (!nrow(d)) cli_falhar("nenhuma linha elegível para a síntese", SAIDA_ERRO_DADOS)
  excluir_rob <- identical(opcoes$excluir_rob, "critico")
  # Direção do estudo decidida com todas as linhas ANTES da exclusão por RoB crítico (como meta.R).
  tab_todos <- direcoes_por_estudo(d, opcoes$limiar)
  tab_todos$excluido_rob_critico <- if (excluir_rob) eh_rob_critico(tab_todos$rob_geral) else rep(FALSE, nrow(tab_todos))
  tab_todos <- tab_todos[order(tab_todos$grupo, tab_todos$direcao, tab_todos$id_estudo), , drop = FALSE]
  rotulos <- unique(tab_todos$grupo)
  grupos <- lapply(seq_along(rotulos), function(i) {
    sub <- d[d$.grupo == rotulos[i], , drop = FALSE]
    tg_todos <- tab_todos[tab_todos$grupo == rotulos[i], , drop = FALSE]
    critico <- tg_todos$excluido_rob_critico
    tg <- tg_todos[!critico, , drop = FALSE]
    g <- c(list(grupo = rotulos[i]), atributos_grupo(sub, opcoes$grupo, opcoes$separar_desenho),
           resumir_grupo(tg, opcoes$nivel))
    if (excluir_rob) {
      g$excluidos_rob_critico <- list(
        n_estudos = sum(critico),
        estudos = as.list(unique(ifelse(vazio(tg_todos$chave[critico]), tg_todos$id_estudo[critico], tg_todos$chave[critico]))),
        n_sem_rob_geral = sum(vazio(tg_todos$rob_geral)),
        nota = "risco de viés crítico fora do teste de sinal principal; a contagem com esses estudos está em sensibilidade$com_rob_critico"
      )
      g$sensibilidade <- list(com_rob_critico = if (!any(critico)) {
        list(executado = FALSE, motivo = "nenhum estudo com risco de viés crítico no grupo")
      } else {
        com <- resumir_grupo(tg_todos, opcoes$nivel)
        list(executado = TRUE, n_incluidos = sum(critico), k_estudos = com$k_estudos, n_estudos = com$n_estudos,
             n_beneficos = com$n_beneficos, n_danosos = com$n_danosos, proporcao_benefica = com$proporcao_benefica,
             ic_proporcao = com$ic_proporcao, p_sinal = com$p_sinal)
      })
      sub <- sub[!sub$.estudo %in% tg_todos$id_estudo[critico], , drop = FALSE]
    }
    so_p <- is.na(como_num(coluna(sub, "yi"))) & !is.na(como_num(coluna(sub, "p"))) & !is.na(n_amostra(sub))
    if (any(so_p)) {
      pts <- pontos_albatross(sub)
      if (nrow(pts) >= 2L) {
        arq <- file.path(opcoes$out_dir, "figuras", sprintf("albatross_%02d_%s.png", i, slug(rotulos[i])))
        g$albatross <- list(arquivo = salvar_albatross(pts, arq, rotulos[i]), n_pontos = nrow(pts),
                            n_so_p = sum(pts$so_p), nota = "pontos = efeitos; círculo vazio = só p e n")
      } else {
        g$albatross <- list(arquivo = NULL, motivo = "menos de 2 pontos com p, N e direção")
      }
    }
    g
  })
  list(tabela = tab_todos, grupos = grupos, n_excluidos_revisao = sum(excluir),
       n_excluidos_rob_critico = sum(tab_todos$excluido_rob_critico))
}

main_swim <- function(args) {
  entrada <- cli_arg(args, "in", obrigatorio = TRUE)
  opcoes <- list(
    out_dir = cli_arg(args, "out-dir", "06-analise"),
    grupo = cli_colunas_grupo(args),
    limiar = cli_num(args, "limiar-consistencia", 0.7),
    nivel = cli_num(args, "nivel", 0.95),
    separar_desenho = cli_bool(args, "separar-desenho", TRUE),
    excluir_rob = cli_excluir_rob(args)
  )
  if (opcoes$limiar <= 0.5 || opcoes$limiar > 1) cli_falhar("--limiar-consistencia deve estar em (0,5; 1]", SAIDA_ERRO_DADOS)
  df <- ler_csv_texto(entrada)
  if (!nrow(df)) cli_falhar("entrada sem linhas", SAIDA_ERRO_DADOS)
  cli_excluir_rob(args, df)
  res <- executar_swim(df, opcoes)

  arq_tab <- escrever_csv(res$tabela, file.path(opcoes$out_dir, "tabelas", "swim_direcao.csv"))
  principal <- res$tabela[!res$tabela$excluido_rob_critico, , drop = FALSE]
  figuras <- if (nrow(principal)) salvar_direcao(principal, opcoes$out_dir) else character(0)
  arq_json <- file.path(opcoes$out_dir, "swim_resumo.json")
  escrever_json(list(
    versao = "1", comando = "swim", gerado_em = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    entrada = entrada,
    parametros = list(grupo = as.list(opcoes$grupo), limiar_consistencia = opcoes$limiar, nivel = opcoes$nivel,
                      separar_desenho = opcoes$separar_desenho, excluir_rob = opcoes$excluir_rob),
    n_linhas_excluidas_revisao = res$n_excluidos_revisao,
    n_excluidos_rob_critico = res$n_excluidos_rob_critico,
    ressalvas = list(
      "direção pelo estimador pontual; significância não define direção",
      "teste de sinal não estima magnitude nem considera precisão ou tamanho dos estudos",
      "rótulo da caixa de ferramentas exige certeza (GRADE)"
    ),
    figuras = as.list(figuras),
    grupos = res$grupos
  ), arq_json)

  albatross <- unlist(lapply(res$grupos, function(g) g$albatross$arquivo))
  message(sprintf("swim: %d grupos, %d estudos×grupo", length(res$grupos), nrow(res$tabela)))
  list(codigo = SAIDA_OK, resumo = list(
    ok = TRUE, comando = "swim", entrada = entrada, out_dir = opcoes$out_dir,
    resumo_json = arq_json, tabela = arq_tab,
    n_grupos = length(res$grupos), n_estudos_grupo = nrow(res$tabela),
    n_excluidos_revisao = res$n_excluidos_revisao,
    excluir_rob = opcoes$excluir_rob,
    n_excluidos_rob_critico = res$n_excluidos_rob_critico,
    figuras = as.list(c(figuras, albatross))
  ))
}

if (sys.nframe() == 0L) {
  quit(status = cli_executar(function() main_swim(cli_args())), save = "no")
}
