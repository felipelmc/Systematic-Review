# Notas de leitura: 08a Síntese quantitativa

Convenções. Páginas do arquivo do curso seguem a numeração impressa do periódico, salvo indicação. Na proposta OQF (`schaefer_oqfunciona`), páginas do PDF do preprint (marcador `--- pN ---` do texto-base), como nos capítulos 03 e 07. Em Slough & Tyson, páginas do manuscrito de 2022 no OSF do curso (`7 Reportar os achados/ev_ma.pdf`, 35 p.). Cálculos "(cálculo nosso)" feitos em R 4.5.2 com metafor 5.0.1, meta 8.5-0, esc 0.5.1 e clubSandwich 0.7.0 sobre os dados do Anexo J da proposta OQF; scripts `reanalise.R` e `teste_codigo.R` no scratchpad da sessão (não copiados para o repositório). Todos os blocos de código R do capítulo foram executados com dados simulados para conferir sintaxe. Versão revisada nesta rodada: a versão anterior do capítulo foi conferida contra as fontes e corrigida (ver "Correções em relação à versão anterior", no fim).

## figueiredo2014meta — Figueiredo Filho et al. (2014), O que é, para que serve e como se faz uma meta-análise?
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/1 Tipos de revisão/FIGUEIREDO MEta análise.pdf` (Teoria & Pesquisa 23(2): 205-228; DOI 10.4322/tp.2014.018)
- O que foi lido: inteiro; p. 213 vista como imagem (Quadro 2 com fórmulas)
- Pontos usados no capítulo:
  - Três pressupostos para acumular achados: mesma questão, testes independentes, resultados válidos (Cooper 2010) — p. 212
  - Forma "mais simples": contar significativos na direção esperada, na não esperada e não significativos; comparar significativos em cada direção — p. 212 — "contar quantos achados foram estatisticamente significativos na direção esperada"
  - Quadro 2: Fisher χ² = −2Σ log_e p, gl = 2n; Winer Zc = Σt/√Σ[df/df−2], normal com df ≥ 10; Stouffer Zc = Σz/√N ("ao invés de utilizar estatística t, emprega-se a estatística z"); Cooper Zc = (Np − ½N)/(½√N), "Utiliza apenas a direção" — p. 213
  - Nota 6 (Fisher): inconsistente "quando a maior parte dos estudos demonstra resultados na mesma direção"; nota 7 (Winer): inconsistente com N < 10 — p. 213
  - Agregar coeficientes de regressão exige VD/VI medidas igual, controles constantes e distribuições similares — p. 214
  - Exemplo aplicado de contagem por significância: 60,5% significativos, 23,7% não significativos, 15,8% mistos; "seis em cada dez artigos" — p. 218
- Limitações/observações: texto introdutório; não trata efeitos aleatórios, heterogeneidade, dependência nem viés de publicação.

## glass1979meta — Glass & Smith (1979), Meta-analysis of research on class size and achievement
- Arquivo/URL: `.../1 Tipos de revisão/Glass-and-Smith.pdf` (EEPA 1(1): 2-16)
- O que foi lido: seletivo, p. 2-10 (introdução, busca, comentário sobre inferência, descrição da base)
- Pontos usados no capítulo:
  - Revisões anteriores "took 'statistical significance' of differences far too seriously" — p. 2
  - 77 estudos, 725 Δ — p. 8
  - Inferência ignorada por duas razões: observações interdependentes ("there is no sensible way to reduce each study to one observation") e ausência de amostragem aleatória — p. 8
  - Só 60% dos Δ favorecem a turma menor; odds de 55 a 45 na faixa típica; revisões narrativas de "a dozen or two studies" produziram confusão — p. 10

## vaessen2014effects — Vaessen et al. (2014), microcrédito e controle das mulheres sobre gastos (Campbell)
- Arquivo/URL: `.../6 Análise de dados/Campbell Systematic Reviews - 2014 - Vaessen ...pdf`
- O que foi lido: seletivo: métodos 2.6 (p. 32-35), resultados 3.4 (p. 52-68), leitura "ingênua" da Tabela 2 (p. 39), limitações 4.2 (p. 82)
- Pontos usados no capítulo:
  - Leitura "ingênua": 15 de 25 estudos com relação positiva e significativa; é preciso avaliar dependência, risco de viés e meta-análise ponderada — p. 39
  - Unidade de análise conferida nos RCTs (EP cluster-robust) — p. 34
  - Dependência: cinco abordagens possíveis; efeitos sintéticos com variância ajustada por r atribuído (0,8 mesmos grupos; 0,2 grupos diferentes; 0,5 intermediário) — p. 34-35
  - Meta-análise só para estudos comparáveis em nível conceitual — p. 53 — "Synthesis through meta-analysis is only possible for studies that can be meaningfully compared"
  - Tratamento como adesão = intenção de tratar; indicadores não dicotomizáveis excluídos — p. 53
  - RCTs separados: SMD = −0,007 (IC −0,041 a 0,027), Q = 2,72, I² = 0% — p. 54
  - Desenhos mais válidos mostram efeitos menores — p. 61
  - Funil com contornos (18 efeitos) sem assimetria aparente — p. 65
  - Egger em meta-regressão com dummy de risco alto; assimetria atribuída ao risco de viés — p. 66
  - Contagem de votos ou MA sem avaliação de risco de viés inflaria significância — p. 82
- Limitações/observações: Egger aplicado a SMD antes de Pustejovsky & Rodgers (2019).

## garcia2017educational — García & Saavedra (2017), CCTs: meta-analysis
- Arquivo/URL: `.../4 Filtragem e controle de qualidade/garcía-saavedra-2017-...pdf` (RER 87(5): 921-965). Número de página no rodapé (conferido na imagem da p. 935).
- O que foi lido: seletivo, p. 931-939
- Pontos usados no capítulo:
  - Melhor estimativa: estudo de maior qualidade; empate, o mais recente; modelo com controles mais completos; subgrupos não sobrepostos combinados por efeito fixo ponderado — p. 933
  - Dependência no tempo (Case 3) — p. 934
  - Duas abordagens: uma estimativa por programa e domínio (maior exposição) em modelo aleatório — p. 935; RVE de Hedges, Tipton & Johnson (2010) — p. 937-938
  - Meta-regressão só em quatro domínios com estimativas suficientes; moderadores com previsão teórica; controle de região, qualidade e publicação; interações não modeladas — p. 938-939

## slough2023external — Slough & Tyson, External validity and meta-analysis
- Arquivo/URL: `.../7 Reportar os achados/ev_ma.pdf` (manuscrito 2022); AJPS 67(2): 440-455, 2023 (metadados conferidos no Crossref)
- O que foi lido: inteiro (texto principal p. 1-29)
- Pontos usados no capítulo:
  - Estudo = setting, contraste e estratégia de mensuração — p. 1-2
  - Target-equivalence; harmonização de contraste e de mensuração — p. 2, 15 (Def. 4 e 5)
  - Sem harmonização, MA pode não achar mecanismo presente ou achar mecanismo ausente — p. 3
  - D (unidades em que o mecanismo opera); CATEs — p. 12
  - Harmonização julgada por validade de constructo, com argumento positivo do analista — p. 16
  - Exemplo GOTV: panfleto um mês ou dois dias antes (contraste); cadastro ou autodeclaração (mensuração) — p. 17; atratividade e momento do panfleto — p. 20-21
  - Teorema 3 (validade externa + harmonização ⇔ target-equivalence) — p. 21; Corolário 1 (harmonizar o controle) — p. 22
  - FE e RE assumem design invariance; usá-los não estabelece validade externa — p. 24-25 — "does not establish whether a mechanism has external validity"
  - Validade interna necessária, não suficiente — p. 26
  - Teste de υ = 0 como teste de harmonização depende de pressupostos estruturais; meta-regressão com diferença de contraste medida — p. 27
  - Validade externa local: meta-analisar só dentro dos subconjuntos — p. 28

## cancela2016explaining — Cancela & Geys (2016), Explaining voter turnout
- Arquivo/URL: `.../5 Extração de dados - decomposição/1-s2.0-S0261379416300956-main.pdf` (Electoral Studies 42: 264-275)
- O que foi lido: seletivo, p. 264-268
- Pontos usados no capítulo:
  - Método: "a blend of 'vote-counting' and 'combined tests' procedures" — p. 265
  - Direção esperada a priori; teste = coeficiente; sucesso, fracasso (não significativo), anomalia; resultado modal: sucesso se mais da metade, "Otherwise, the study's modal outcome is 'failure'"; r = (sucessos − anomalias)/testes — p. 265
  - IC r̄ ± 1,96 s/√n; "explanatory power" se o IC exclui 0; taxa por estudo e por teste — p. 266
  - Só operacionalizações "sufficiently equivalent"; magnitude não considerada — p. 266
- Limitações/observações: o esquema é contagem por significância; "r" não é tamanho de efeito.

## gerring2022democracy — Gerring, Knutsen & Berge (2022), Does democracy matter?
- Arquivo/URL: `.../5 Extração de dados - decomposição/annurev-polisci-060820-060910.pdf` (ARPS 25: 357-375)
- O que foi lido: p. 357-368 (texto extraído por página)
- Pontos usados no capítulo:
  - 1.100 análises, 600 artigos, 30 desfechos — p. 357
  - Sem MA tradicional: difícil padronizar e comparar coeficientes — p. 359
  - Um modelo de referência por análise; base com 607 estudos e 1.181 análises — p. 362
  - "The t-value is not an effect, strictly speaking; it measures the estimated effect relative to the standard error" — p. 364
  - t normativamente ajustado; 22% negativos (Figura 2, 985 análises) — p. 365
  - Classificação "bad/null/good" por ±1,96 com reconhecimento do perigo de limiares; cautela com menos de 10 análises — p. 366
  - Funil exige coeficientes e EP; 11% com |t| entre 1,96 e 2,26; sem acúmulo em 1,65 ou 2,58; 29% não significativos a 10%; 32% com t > 3 — p. 368

## schaefer2025proibicao — Schaefer, Borges & Gomes Filho (2025), A proibição do uso de celulares...
- Arquivo/URL: `.../6 An†lise de dados/FINAL+-+A+PROIBICAO+DO+USO+DOS+CELULARES.pdf` (JPPG 1(2): e97-113). Página impressa = página do PDF + 96.
- O que foi lido: inteiro; p. 104-105 vistas como imagem (Tabela 2 e forest plot)
- Pontos usados no capítulo:
  - g = 0,22; "Embora considerado fraco segundo a literatura, o efeito é consistente em diferentes metodologias e contextos" — p. 97
  - Lei nº 15.100/2025 para a educação básica — p. 98 (e art. 2º citado na p. 108)
  - 21 trabalhos, oito com inferência causal — p. 99
  - PICOC: comparação escolas com e sem restrição; outcome em avaliações padronizadas — p. 100
  - Fisher e Cooper para "consistência e direção" (Figueiredo 2014) — p. 103
  - Três experimentais, quatro seleção em observáveis (DiD), uma meta-análise; sete de oito positivos, seis significativos; Fisher 65,74; Cooper 2,88; g via meta — p. 104
  - Forest plot: 1: 0,06 [0,05; 0,07]; 4: 0,67 [−0,04; 1,38]; 3: −0,01 [−0,05; 0,03]; 5: 0,39 [0,10; 0,68]; 15: 0,61 [0,09; 1,13]; 20: 0,39 [−0,05; 0,83]; 24: 0,44 [0,09; 0,79]; 28: 0,05 [−0,05; 0,15]; Total 0,22 [0,02; 0,42]; "Heterogeneity: χ²₇ = 29.73 (P < .001), I² = 76.5%"; "fraco (conforme critérios da literatura)" com Lima et al. 2022; diferença com Böttger & Zierer atribuída ao ensino superior — p. 105
  - Limitações: quatro dimensões (tipo de banimento, público, foco, tipo de avaliação) — p. 109
  - Referências: Kessel, Hardardottir & Tyrefors (2020) "The impact of banning mobile phones in Swedish secondary schools" — p. 112; Gutiérrez-Puertas et al. (2020) "The effect of cell phones on attention and learning in nursing students" — p. 111

## schaefer_oqfunciona — Schaefer, Borges & Freitas (2025), O que funciona? (preprint OSF)
- Arquivo/URL: texto-base no scratchpad (`fontes/oqf_texto_base_...txt`); páginas do PDF
- O que foi lido: seletivo, p. 22-23 (dimensão substantiva), p. 32-35 (análise), p. 103-107 (Anexos I e J)
- Pontos usados no capítulo:
  - Fisher, Cooper ou Winer "Testes úteis para mensurar a escala, ou tamanho, do efeito da política" — p. 22
  - "Outra estratégia é utilizar valores padronizados dos coeficientes (valor de T)... quanto maior o valor de T, maior a diferença" — p. 23
  - Mesmo resultado do artigo; diferença com Böttger & Zierer pelo ensino superior; "fraco" com Brydges (2019) — p. 33-34
  - Anexo J: `esc_B` para ids 1 (66.266 + 64.216), 4 (16 + 16), 3 (4.686 + 4.685, comentário "The impact of banning mobile phones"), 5 (52 + 425) — p. 104-105; `esc_f` para 15 (25 + 38) e 20 (40 + 40) — p. 105-106; Mann-Whitney "U = 1859.500, Z = −2.151, P = .015", médias 9,83 ± 3,25 e 7,11 ± 2,96, `esc_t(p = 0.015)` com comentário "# t-value", título "The Effect of Cell Phones on Attention" (id 24); id 28 "Informações produzidas a partir de Meta Análise" — p. 106
  - Tabela final: TE 0,059; 0,668; −0,008; 0,388; 0,610; 0,392; 0,440; 0,050; seTE 0,005; 0,363; 0,020; 0,147; 0,263; 0,225; 0,181; 0,050; n 130482; 192; 9371; 477; 63; 160; 124; 9 — p. 107
- Cálculos nossos a partir do Anexo J:
  - REML + HKSJ: 0,216 [0,015; 0,417] (reproduz o publicado); REML Wald: 0,216 [0,050; 0,383]; `test = "adhoc"`: igual ao HKSJ; PM + HKSJ: igual
  - τ² = 0,0366 (Q-profile 0,0055 a 0,2415); τ = 0,191; Q = 29,73 (gl 7); I² (Q, meta) = 76,5% [53,0; 88,2]; I² (τ², metafor) = 96,7%; PI [−0,279; 0,711]
  - Pesos: FE id 1 = 93,0%, id 3 = 5,8%; RE id 1 = 19,7%, id 3 = 19,5%, id 28 = 18,5%
  - FE 0,056 [0,047; 0,066]; DL + HKSJ 0,093 [−0,044; 0,230], τ² 0,004, PI [−0,110; 0,296]; DL Wald 0,093 [0,020; 0,165]
  - Leave-one-out (REML + HKSJ): sem 1: 0,269 [0,032; 0,505]; sem 4: 0,189 [−0,017; 0,394]; sem 3: 0,272 [0,053; 0,490]; sem 5: 0,188 [−0,040; 0,416]; sem 15: 0,172 [−0,027; 0,372], PI [−0,278; 0,623], τ² 0,027; sem 20: 0,202 [−0,027; 0,430]; sem 24: 0,181 [−0,038; 0,400]; sem 28: 0,268 [0,033; 0,502], PI [−0,307; 0,843], τ² 0,046
  - Sem 28 e 24: 0,243 [−0,035; 0,521], PI [−0,382; 0,869], τ² 0,048
  - Id 24: médias/DP g = 0,869 (EP 0,188); `esc_t(p = 0.015)` = 0,4405; p bilateral de Z = 2,151 é 0,0315 e `esc_t` dá 0,3885; substituindo por 0,869: 0,308 [0,036; 0,580], PI [−0,426; 1,041], τ² 0,083
  - z = TE/seTE: 11,80; 1,84; −0,40; 2,64; 2,32; 1,74; 2,43; 1,00 (|z| > 1,96 só ids 1, 5, 15, 24)
  - Sinal 7/8: bilateral 0,0703, unilateral 0,0352; 6/7 bilateral 0,125; Wilson 7/8: 0,529 a 0,978
  - Cooper (fórmula do Quadro 2), N = 8, Np = 7: 2,12
  - Fisher com p bilaterais de z: 183,9 (gl 16), id 1 = 144,6; com p unilaterais: 193,7, id 1 = 146,0
  - Stouffer ponderado √n: 11,66, com id 1 = 92,6% de Σw²; não ponderado 8,26
  - Spearman TE × seTE = 0,905

## schaefer2026analise — script "10 Análise de Dados.R" (pasta 11)
- Arquivo/URL: `.../11 C¢digos R - Atualizado e Consolidado/10 An†lise de Dados.R` (976 linhas)
- O que foi lido: linhas 225-345 e 800-900; conferido que não há chaves de API nas linhas lidas
- Pontos usados no capítulo:
  - Comentário: testes de Rosenthal (1991) quando a heterogeneidade impede MA; consomem p bilateral derivado do T — l. 260-265
  - `teste_fisher`: descarta p NA e p ≤ 0; X² = −2Σ log p; gl 2k — l. 268-276
  - `teste_stouffer`: z = sinal × qnorm(1 − p/2); Σz/√k; p bilateral — l. 278-286
  - `teste_winer`: mesmo z; divide por √Σ peso, peso = gl/(gl − 2) se gl > 2, senão 1; p bilateral — l. 292-302
  - `teste_cooper`: `binom.test` bilateral, exclui sinal 0 — l. 307-315
  - `testes_por_grupo`: aplica tudo para direção ampla e restrita — l. 331-341
  - `sinal_ampla_b2`: 1 → 1; 0 → −1 — l. 832-836; `sinal_restrita_b2`: 1, 0, −1 — l. 838-843
  - `p_b2 <- 2 * pnorm(-abs(t_b2))` — l. 846; gl = n_t + n_c − n_controles − 2 — l. 851
  - `p_b2_restrita` NA quando sinal restrito = 0 — l. 855
  - Aviso |T| > 20 e p = 0 por underflow — l. 872-886; testes gerais — l. 889-895

## schaefer2026codigos — scripts da pasta 8 e codebook de decomposição
- Arquivo/URL: `.../8 Códigos R/1 Simulação tamanho do efeito.R`; `.../8 C¢digos R/quadro_decomposicao_estudos EXEMPLO.xlsx`
- O que foi lido: script inteiro; na planilha, só as linhas com "direcao" (aba b2_quantitativo)
- Pontos usados no capítulo:
  - `pnorm(1)` = 84%: média do grupo 2 no percentil 84 do grupo 1; CLES = `pnorm(d/sqrt(2))` — script da simulação
  - `direcao_am`: "Dummy (1=Positivo; 0=Negativo)", no sentido normativo — aba b2_quantitativo
  - `direcao_re`: "1 se p-valor < 0,05 e efeito positivo; 0 se p-valor ≥ 0,05; -1 se p-valor < 0,05 e efeito negativo" — aba b2_quantitativo

## schaefer2026aula6 — Slides OQF MAPE Aula 6
- Arquivo/URL: `.../9 Slides/OQF_MAPE_Aula_6 An†lise de dados.pdf`
- O que foi lido: p. 31-41 vistas como imagem
- Pontos usados no capítulo:
  - p. 31: "Abordagens quantitativas"; p. 32: Figueiredo et al. como tutorial; p. 33: Quadro 2 (Fisher, Winer, Stouffer, Cooper); p. 34: Harrer et al. (doing-meta.guide); p. 35-36: Gerring et al. e planilha da base; p. 37: Figura 2 (t normativo, linhas em −1,96, 0, 1,96)
  - p. 38: título "What Affects Voter Turnout? A Review Article/Meta-Analysis of Aggregate Research" com link da Cambridge; p. 39: Tabela 1, "704 GOVERNMENT AND OPPOSITION": voto obrigatório com sanções, 32 estudos, 74 modelos, 72 sucessos, 0 fracassos, 2 "no link", 0,97; sem sanções, 21, 54, 52, 0, 2, 0,96
  - p. 40-41: texto como dado
- Limitações/observações: autoria da tabela (Stockemer 2017, Government and Opposition 52(4): 698-722, DOI 10.1017/gov.2016.30) conferida só nos metadados do Crossref; o artigo não foi lido.

## schaefer2026ementa — Ementa do curso
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/Revisão_Sistemática_e_Avaliação_de_Políticas_Públicas___Ementa.pdf`
- O que foi lido: busca por termos e seções das aulas 5 e 6
- Pontos usados no capítulo: materiais da aula 5 incluem "Extração do valor de T" (Gerring et al.) e "Taxa de sucesso dos estudos" (Cancela & Geys) — p. 8; aula 6 indica Harrer et al. cap. 8 e, em meta-regressão, Gerring, Glass & Smith e García & Saavedra — p. 8-9

## brydges2019effect — Brydges (2019), Effect size guidelines in gerontology
- Arquivo/URL: `.../5 Extração de dados - decomposição/Brydges-...rev.pdf`
- O que foi lido: resumo e resultados (p. 1-3)
- Pontos usados no capítulo: diretrizes de Cohen sem base empírica, recomendadas só sem estimativas do campo; g = 0,16 / 0,38 / 0,76 nos percentis 25/50/75 de 2.941 valores — p. 1

## deeks2024analysing — Cochrane Handbook v6.5, cap. 10 (última atualização nov. 2024)
- Arquivo/URL: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10 (HTML baixado e convertido em texto)
- O que foi lido: 10.1-10.3 e 10.10-10.14 inteiros
- Pontos usados no capítulo:
  - "Do not start here!"; diamante engana sem preparação — 10.1
  - Efeito fixo: pressupõe mesmo efeito; aleatório: efeitos diferentes mas relacionados — 10.3.1-10.3.2
  - C62: meta-analisar só se PICO suficientemente similares; controles diferentes enganam — 10.10.1
  - C63: evitar limiares simples; incerteza de I² e τ² com poucos estudos; χ² de baixo poder, P de 0,10; faixas de I² com ressalvas — 10.10.2
  - C69; checar dados (erros e unit-of-analysis causam heterogeneidade); não meta-analisar com direções opostas; post hoc só gera hipóteses — 10.10.3
  - RE dá mais peso relativo a pequenos; não "leva em conta" a heterogeneidade — 10.10.4
  - Sem recomendação universal FE × RE; nunca escolher por teste; com assimetria os dois são problemáticos — 10.10.4.1 — "should never be made on the basis of a statistical test for heterogeneity"
  - RE só estima bem o efeito médio se vieses forem simétricos — 10.10.4.2
  - PI com t(k−1); usar com cinco ou mais estudos e sem assimetria clara — 10.10.4.3
  - PM (Langan 2017) e REML (Langan 2019), nenhum universal; REML padrão no RevMan; Q-profile informativo com cinco ou mais; HKSJ largo demais com poucos, estreito demais com τ² = 0; I² do RevMan = τ²/(τ² + SE²) coincide com o de Q só com DL — 10.10.4.4
  - Dois ou três estudos: HKSJ largo demais, Wald estreito demais; comparar em sensibilidade — 10.10.4.5
  - C67 e teste de diferença entre subgrupos; RE preferível ao FE para comparar — 10.11.3.1
  - MR não com menos de dez estudos — 10.11.4; dez observações por característica — 10.11.5.1; C68 — 10.11.5.2; considerar ajuste com mais de uma ou duas características — 10.11.5.3; viés ecológico — 10.11.5.5; confundimento — 10.11.5.6; observacional, ICEMAN — 10.11.6
  - C71; tabela-resumo de sensibilidade; sensibilidade ≠ subgrupo — 10.14

## mckenzie2024synthesizing — Cochrane Handbook v6.5, cap. 12 (McKenzie & Brennan; atualizado out. 2019)
- Arquivo/URL: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-12
- O que foi lido: 12.1-12.4 inteiros
- Pontos usados no capítulo:
  - Razões legítimas e soluções (Tabela 12.1.a); diversidade vale contra todos os métodos — 12.1
  - Preferíveis, aceitáveis, inaceitáveis; um desfecho por estudo; não escrever só "síntese narrativa" — 12.2
  - Tabela 12.2.a: combinar p responde "effect in at least one study"; sem magnitude; não distingue estudos grandes/pequenos; não rejeitar com poucos estudos pequenos não é ausência de efeito; contagem por direção menos poderosa
  - Resumo de estimativas quando variâncias estão erradas (clusters) — 12.2.1.1
  - Fisher com p unilaterais; conversão; 0,05 se só "P<0,05"; p deve respeitar clusters; relatar o método e sensibilidade à escolha — 12.2.1.2
  - Contagem por direção: sinal, teste de sinal, u/n com Wilson ou Jeffreys; linguagem "a maioria dos estudos" é contagem implícita — 12.2.1.3
  - Contagem por significância inválida; poder tende a zero (Hedges & Vevea 1998); versões de três e dois grupos — 12.2.2.1
  - Regras subjetivas — 12.2.2.2
  - Forest plot sem diamante e ordenado — 12.3.2; albatross — 12.3.4; harvest por direção aceitável, effect direction plot original "requires further development" — 12.3.5
  - Exemplo: 10 de 12, 83% (55% a 95%), P = 0,039, três sem direção excluídos — 12.4.2.3; Fisher com p unilaterais e sensibilidade por risco de viés — 12.4.2.2

## page2024assessing — Cochrane Handbook v6.5, cap. 13 (atualizado ago. 2024)
- Arquivo/URL: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-13
- O que foi lido: 13.3.4-13.4
- Pontos usados no capítulo:
  - Funil com EP em escala invertida; small-study effects; Tabela 13.3.b (não relato, viés, heterogeneidade verdadeira, artefato, acaso); contornos em P = 0,01, 0,05, 0,1 — 13.3.4.2-13.3.4.3
  - Testes só com ≥ 10 estudos; não usar com estudos de tamanho parecido; Egger original não recomendado para OR e SMD — 13.3.4.4
  - Assimetria não diagnostica viés de não relato — 13.3.4.5
  - Comparar FE e RE quando I² > 0; restringir a estudos maiores e mais rigorosos se forem mais típicos da prática; modelos de seleção supõem ausência de outras causas; regressões só com ≥ 10 — 13.3.4.6
  - ROB-ME: baixo, alto, algumas preocupações — 13.3.5
  - C73 — 13.4

## reeves2024including — Cochrane Handbook v6.5, cap. 24 (atualizado out. 2019)
- Arquivo/URL: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-24
- O que foi lido: 24.2.1-24.2.2 e 24.6
- Pontos usados no capítulo:
  - RCT e NRSI elegíveis: "presented and analysed separately" — 24.2.2
  - Estimativas ajustadas que minimizam confundimento; NRSI grande e de má qualidade pode dominar; ICs de NRSI grandes representam menos a incerteza; excluir risco crítico — 24.6.1
  - NRSI com desenhos muito diferentes separados; RCT e NRSI não combinados; RE como padrão — 24.6.2.1
  - Forest plot sem estimativa conjunta como padrão quando não se combina; diagnósticos de heterogeneidade úteis mesmo assim — 24.6.2.3

## page2021prisma — Page et al. (2021), PRISMA 2020
- Arquivo/URL: Europe PMC PMC8005924 (XML integral)
- O que foi lido: Tabela 1, itens 12-27
- Pontos usados no capítulo: textos dos itens 12, 13a-13f, 14, 19, 20a-20d, 21, 22 e 27 conferidos (ex.: 13d "If meta-analysis was performed, describe the model(s), method(s) to identify the presence and extent of statistical heterogeneity")

## campbell2020synthesis — Campbell et al. (2020), SWiM (BMJ 368: l6890)
- Arquivo/URL: Europe PMC PMC7190266 (XML integral; licença CC BY 4.0)
- O que foi lido: introdução, escopo, Tabela 1, explicações dos itens 1, 3, 4, 5, 8, 9
- Pontos usados no capítulo: nove itens (1a/1b a 9); item 1a com teoria da mudança/logic model; expande PRISMA (itens 14 e 21 da versão 2009) e RAMESES; não se aplica a dados qualitativos (ENTREQ, eMERGe)
- Observação: 09-certeza-evidencia-pratica.bib usa a chave campbell2020swim para esta obra.

## inthout2014hartung — IntHout, Ioannidis & Borm (2014)
- Arquivo/URL: Europe PMC PMC4015721 (texto integral)
- O que foi lido: resumo, resultados e conclusões
- Pontos usados no capítulo: HKSJ erro no máximo dobra, DL > 30%; 689 MAs, 25,1% dos significativos por DL não significativos com HKSJ; "extra caution is needed when there are = <5 studies of very unequal sizes" — resumo

## rover2015hartung — Röver, Knapp & Friede (2015)
- Arquivo/URL: Europe PMC PMC4647507 (texto integral)
- O que foi lido: resumo, métodos (eq. 5-11), discussão
- Pontos usados no capítulo: HKSJ excede erro nominal quando EPs variam; q* = max{1, q} (eq. 11) evita intervalo mais curto que o normal; mKH recomendado com poucos estudos de precisão variável; muito conservador com k = 2, problema "effectively unsolved" — resumo, métodos, discussão

## jackson2017hartung — Jackson, Law, Rücker & Schwarzer (2017)
- Arquivo/URL: Europe PMC (PMID 28748567), resumo
- O que foi lido: resumo
- Pontos usados no capítulo: HK pode substituir o método padrão; usar análises convencionais como sensibilidade, com efeitos aleatórios padrão em vez de efeito comum — resumo

## pustejovsky2022meta — Pustejovsky & Tipton (2022), RVE working models
- Arquivo/URL: preprint OSF vyfcj (PDF 39 p., baixado pela API do OSF); resumo no Europe PMC
- O que foi lido: resumo e seção de modelos de trabalho e escolha (p. 10-19 do preprint)
- Pontos usados no capítulo: CHE, eq. 6, τ, ω e ρ constante; "the CHE model will be a first choice as a working model in many applications" — p. 12; escolher o modelo pela estrutura dos dados, não comparando resultados; pré-registrar — p. 19

## pustejovsky2018small — Pustejovsky & Tipton (2018), small-sample CRVE
- Arquivo/URL: arXiv:1601.01981v2 (revisão de nov. 2022)
- O que foi lido: resumo e seção 3.1
- Pontos usados no capítulo: CR2 + Satterthwaite com erro tipo I ≤ nominal "so long as the degrees of freedom are larger than 4 or 5" (Tipton 2015; Bell & McCaffrey 2002); gl dependem de covariáveis, não só do número de clusters — p. 14
- Limitações/observações: Tipton (2015) não lido diretamente.

## pustejovsky2019testing — Pustejovsky & Rodgers (2019)
- Arquivo/URL: Europe PMC (resumo); fórmula e implementação em Harrer et al., 9.2.1.2
- O que foi lido: resumo
- Pontos usados no capítulo: testes convencionais de assimetria com SMD têm erro tipo I inflado; EP modificado ou transformação estabilizadora mantêm erro nominal; 3PSM avaliado — resumo

## stanley2014meta — Stanley & Doucouliagos (2014), PET-PEESE
- Arquivo/URL: Europe PMC (resumo); regra operacional em Harrer et al., 9.2.1.5
- O que foi lido: resumo
- Pontos usados no capítulo: PEESE com menor viés e EQM na maioria dos casos; estimador híbrido condicional PEESE/intercepto de Egger — resumo

## boon2021effect — Boon & Thomson (2021), effect direction plot revisited
- Arquivo/URL: Europe PMC PMC7821279 (texto integral)
- O que foi lido: inteiro
- Pontos usados no capítulo:
  - Significância removida do algoritmo; teste de sinal considerado — resumo e métodos
  - Box 1: mesma direção em todos ou 70% ("a clear majority"); < 70% conflitante ◂▸; setas ▲ ▼ ◂▸; tamanho por n do grupo de intervenção (> 300; 50-300; < 50); cor da linha por risco de viés
  - Conflitantes fora do teste de sinal bilateral; exemplos 9/10 (P = 0,0039), 5 × 1 (P = 0,2188) — resultados
  - Pouco poder; denominador encolhe (exemplo 9/20); evitar "statistically significant"; não usar com suspeita de viés de publicação; cita crítica de Nikolakopoulos (2020) — discussão

## nikolakopoulos2020misuse — Nikolakopoulos (2020), Misuse of the sign test
- Arquivo/URL: Europe PMC (resumo)
- O que foi lido: resumo
- Pontos usados no capítulo: teste de sinal inadequado porque os dados não seguem a binomial que ele emprega — resumo

## harrison2017albatross — Harrison et al. (2017), albatross plot
- Arquivo/URL: Europe PMC PMC5599982 (texto integral)
- O que foi lido: resumo e introdução
- Pontos usados no capítulo: requer p unilateral e n total (ou p bilateral, direção e n); contornos de efeito aproximados; identifica fontes de heterogeneidade — resumo

## ogilvie2008harvest — Ogilvie et al. (2008), harvest plot
- Arquivo/URL: Europe PMC PMC2270283 (texto integral)
- O que foi lido: resumo e métodos
- Pontos usados no capítulo: 85 estudos; três hipóteses concorrentes (gradiente positivo, negativo, nenhum); matriz com seis linhas (dimensões de desigualdade) e três colunas; altura da barra = adequação do desenho; tom = desfecho comportamental ou intermediário; anotação = número de outros critérios metodológicos — métodos

## zaykin2011optimally — Zaykin (2011), weighted Z-test
- Arquivo/URL: PMC3135688 (HTML integral)
- O que foi lido: resumo, métodos e discussão
- Pontos usados no capítulo: Z ponderado (Lipták = Stouffer com pesos); pesos √n comparáveis a Lancaster; p bilaterais "generally inappropriate, because they are oblivious to the effect direction"; conversão bilateral → unilateral — resumo e discussão

## whitlock2005combining — Whitlock (2005)
- Arquivo/URL: Europe PMC (resumo)
- O que foi lido: resumo
- Pontos usados no capítulo: Z ponderado com mais poder e precisão que Fisher e que Z não ponderado — resumo

## fu2011conducting — Fu et al. (2011), AHRQ quantitative synthesis
- Arquivo/URL: https://www.ncbi.nlm.nih.gov/books/NBK49407/ (versão do Methods Guide); metadados JCE no Europe PMC
- O que foi lido: seções sobre heterogeneidade, subgrupos e meta-regressão
- Pontos usados no capítulo: sem mínimo universal; com estudos moderados ou grandes, "at least 6 to 10 studies for a continuous study level variable"; subgrupo "a minimum of 4 studies"; pisos para começar a considerar, não suficientes — seção "Number of studies required for a meta-regression"

## harrer2021doing — Harrer et al., Doing Meta-Analysis with R (versão online, doing-meta.guide)
- Arquivo/URL: https://doing-meta.guide/ (páginas pooling-es, heterogeneity, subgroup, metareg, pub-bias, multilevel-ma baixadas e convertidas em texto). A numeração das seções da versão online corresponde à do livro de 2021 citado em references.bib (não conferida contra o impresso).
- O que foi lido: 4.1.2, 4.2.1, 5.1-5.2, 7.2, 8.3.3.4, 9.2-9.5, 10.1-10.4
- Pontos usados no capítulo:
  - REML para contínuos; PM "may be suboptimal when the sample size of studies varies drastically" (Langan 2019); Knapp-Hartung sensato — 4.1.2.1-4.1.2.2
  - I² = (Q − (K − 1))/Q truncado — 5.1.2; τ na escala do efeito — 5.1.4; I² "not an absolute measure", tende a 100% com estudos grandes; τ² insensível a número e precisão; PI com t(K−1), inteiro de um lado = benefício esperado, PI largo comum — 5.2
  - Ausência de diferença entre subgrupos não é equivalência — 7.2
  - Teste de permutação recomendado antes de relatar meta-regressão — 8.3.3.4
  - Egger com SMD infla falsos positivos; EP modificado; `metabias(..., method.bias = "Pustejovsky")` usa EP corrigido como preditor e inverso da variância como pesos — 9.2.1.2
  - PET-PEESE: regra p < 0,10 e intercepto > 0; EP modificado; desempenho ruim com K < 20 e I² > 80%; rma.uni como sensibilidade — 9.2.1.5
  - PET-PEESE com `lm(TE ~ seTE, weights = w_k)`; "lm uses a multiplicative error model", enquanto funções de meta-análise usam erro aditivo; abordagem "not completely uncontroversial"; PEESE quando o intercepto do PET é maior que zero em teste unilateral com α = 0,05 — 9.2.1.5 (página reconsultada em 15/09/2026, depois do redirecionamento de bookdown.org para doing-meta.guide)
  - Seleção complexa com K ≥ 100; 3PSM aplicável com K = 15-20; corte 0,025 — 9.2.3.1
  - Nenhum método domina; estimativas corrigidas de zero a 0,59 no exemplo; nenhum aceitável com I² ≈ 75% — 9.3
  - Três níveis — 10.1-10.2; CHE com ρ "no more than a guess"; CR2 para 40 estudos ou menos; `rma.mv` + clubSandwich — 10.4.1-10.4.2

## viechtbauer2010conducting — metafor (JSS 2010) e documentação local 5.0.1
- Arquivo/URL: ajuda local de `rma.uni`, `selmodel`, `robust`, `vcalc`, `regtest`; metadados JSS no Crossref e jstatsoft.org (páginas 1-48)
- O que foi lido: seções pertinentes das páginas de ajuda
- Pontos usados no capítulo:
  - `test = "adhoc"`: Knapp-Hartung sem EP ajustado menor que o não ajustado (Jackson et al. 2017, sec. 4.3) — rma.uni, Details
  - `selmodel`: ajuste por ML sobre objeto rma.uni; 3PSM com `steps = c(.025, 1)` e `alternative = "greater"`; "There should be at least one observed p-value within each interval"; resultados "with great caution" — selmodel, Details
  - `robust(..., clubSandwich = TRUE)`: CR2 e gl de Satterthwaite — robust, Details
  - `vcalc(vi, cluster, obs, rho)` — vcalc, Arguments

## schwarzer2026meta — pacote meta 8.5-0
- Arquivo/URL: ajuda local `?meta-package` (DESCRIPTION: 8.5-0, 2026-05-25)
- O que foi lido: seções sobre τ², I², IC do efeito aleatório, correções ad hoc e intervalo de predição
- Pontos usados no capítulo: REML padrão; `method.I2 = "Q"` padrão no meta e metafor usa a fórmula baseada em τ²; `method.random.ci = "classic"` padrão e "HK" opcional; `adhoc.hakn.ci = "se"` (Knapp & Hartung 2003) e "ci" (Jackson et al. 2017); PI padrão com t(k−1)

## ludecke2019esc — pacote esc 0.5.1
- Arquivo/URL: ajuda e código de `esc::esc_B` no R local; DESCRIPTION no CRAN
- O que foi lido: ajuda e corpo da função
- Pontos usados no capítulo: `esc_B` calcula d = b/DP combinado e variância por `esc.vd(es, grp1n, grp2n)`, isto é, só dos n dos grupos, sem o EP do coeficiente — código da função (inspeção nossa)

## kraft2020interpreting — Kraft (2020), Interpreting effect sizes of education interventions
- Arquivo/URL: https://www.matthewakraft.com/s/Kraft-2020-Interpreting-Effect-Sizes-ER.pdf (versão do autor, 47 p.)
- O que foi lido: resumo, seção sobre amostra (p. 12-13) e "New Empirical Benchmarks" (p. 20-21)
- Pontos usados no capítulo:
  - "effects that are small by Cohen's standards are large relative to the impacts of most field-based interventions" — resumo
  - Ensaios pequenos de eficácia e intervenções focalizadas dão efeitos maiores que intervenções universais — p. 13
  - pré-K a 12, testes padronizados: < 0,05 pequeno; 0,05 a < 0,20 médio; ≥ 0,20 grande; 1.942 efeitos de 747 RCTs; mediana 0,10 — p. 21

## Correções em relação à versão anterior do capítulo
- 3PSM: a referência a "K = 15-20" foi conferida em Harrer 9.2.3.1 (antes atribuída a 9.2.3.1.1).
- Mínimos de subgrupo: separados em estimar dentro do nível (≥ 3, plano) e testar diferença (≥ 4 por nível, AHRQ; ~10 por característica, Handbook).
- Pustejovsky & Tipton (2018): citação trocada da nota 2 da versão de 2016 para a p. 14 do arXiv v2 (gl > 4 ou 5).
- Código do Egger com EP modificado corrigido: o EP modificado entra como preditor, com as variâncias verdadeiras como pesos (como `metabias(..., method.bias = "Pustejovsky")`); PET-PEESE via `rma(..., method = "FE")`.
- `selmodel` recebe o próprio ajuste REML (a função reajusta por ML); `qnorm(p1, lower.tail = FALSE)` evita z infinito.
- `sinal_ampla` (0 → −1) está de acordo com o codebook (0 = negativo); o erro relevante é a versão "restrita" dos testes, que só combina resultados significativos.
- Acrescentados: ROB-ME, Jackson et al. (2017), Nikolakopoulos (2020), efeito sintético de Vaessen, peso do id 1 via `esc_B`, deslocamento FE/RE discutido com Handbook 13.3.4.6 e Kraft p. 13, exclusão de NRSI em risco crítico, fórmula de I² do meta e do metafor.
- Chave do SWiM alterada de campbell2020swim para campbell2020synthesis, a mesma dos capítulos 01 e 10.

## Fontes não acessadas ou só indiretamente
- Borenstein et al. (2009), Introduction to Meta-Analysis: não acessado. Pelo Crossref, o capítulo de contagem de votos é o 28 ("Vote Counting – A New Name for an Old Problem", p. 251-255), e o 36 é "Meta-Analysis Methods Based on Direction and p-Values" (p. 325-330). Limitações da contagem de votos citadas via Cochrane cap. 12, que cita Borenstein.
- Rosenthal (1978), "Combining results of independent studies", Psychological Bulletin 85(1): 185-193: só metadados (Crossref). Becker (1994): não acessado. Fórmulas conferidas em Figueiredo et al. (2014), no Handbook (12.2.1.2) e em Zaykin (2011).
- Tipton (2015): só via Pustejovsky & Tipton (2018).
- Stockemer (2017): só a tabela no slide e os metadados.
- Pustejovsky & Rodgers (2019), Stanley & Doucouliagos (2014), Jackson et al. (2017), Whitlock (2005) e Nikolakopoulos (2020): só resumos; detalhes operacionais via Harrer et al. e documentação dos pacotes.
- Valentine et al. (2017), sobre síntese com poucos estudos em políticas públicas: resumo lido, não usado.
