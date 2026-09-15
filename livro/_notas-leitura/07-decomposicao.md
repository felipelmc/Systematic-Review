# Notas de leitura: 07-decomposicao (Decomposição dos estudos, extração de dados)

Convenções:

- Proposta OQF (`schaefer_oqfunciona`): páginas pela numeração do PDF, que é a dos marcadores `--- pNN ---` do texto-base no scratchpad; a numeração impressa no rodapé é a do PDF menos 1. Os capítulos 05, 08a e 11 usam a mesma convenção (Anexo J em p. 104-107).
- Slides: número da página do PDF do deck (vistos como imagem, inteiros no caso da Aula 5).
- CLEAR, Hedström, Kaidesoja, Dalkin, Cintron, Brydges, Gerring, Cancela e Geys, Bia: numeração impressa, que coincide com a do periódico ou do material (no CLEAR, PDF = impressa).
- Cochrane Handbook: seções e caixas MECIR conferidas no HTML dos capítulos 5, 6 e 10 (v6.5), baixado em 15/09/2026 e convertido em texto.
- Kraft (2020): páginas da versão do autor (47 p.).
- "Cálculo nosso": contas refeitas em R (pacote `esc` 0,5.1 e fórmulas) e Python no scratchpad.
- Esta versão do capítulo substitui um rascunho anterior da mesma etapa; todas as fontes abaixo foram relidas nesta sessão, e os números do rascunho foram reconferidos.

---

## li2024collecting — Li, Higgins e Deeks (2024), Cochrane Handbook v6.5, cap. 5 "Collecting data"
- Arquivo/URL: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-05
- O que foi lido: capítulo inteiro (5.1 a 5.7), com as caixas MECIR.
- Pontos usados no capítulo:
  - Erros de extração raramente detectados; recomenda mais de um extrator — sec. 5.5.2 — "errors that occur at the data extraction stage are rarely detected by peer reviewers, editors, or users of systematic reviews"
  - 20 de 34 revisões com erros (Jones 2005); mínimo de 7 de 27 com erros substanciais em DMP (Gøtzsche 2007); dupla independente com menos erros que única com verificação (Buscemi 2006) — sec. 5.5.2
  - Estudo, não relato, como unidade — sec. 5.2.1 — "studies rather than reports of studies are the principal unit of interest"
  - C42 (obrigatório) reunir relatos — Box 5.2.b
  - C43 formulário pilotado (obrigatório) — Box 5.4.a; C44 descrever estudos (obrigatório) — Box 5.3.a; C45 (altamente desejável) e C46 (obrigatório) dupla extração — Box 5.5.a; C47 dados mais detalhados (obrigatório) — Box 5.3.c; C48 erratas (obrigatório) — Box 5.2.a; C49 dados não publicados (altamente desejável) — Box 5.2.c; C50 braços elegíveis (obrigatório) — Box 5.3.b; C51 conferência de magnitude e direção (obrigatório)
  - Contato com investigadores: perguntas abertas para descrições, formulário curto para números, tentar outros autores — sec. 5.2.3
  - Resultados múltiplos: hierarquia de medidas, efeito mediano ou média; decisões posteriores relatadas como mudanças de protocolo — sec. 5.3.6
  - Formulário: título da revisão, quem preenche e data; perguntas fechadas com "other, specify"; não pedir resumo em texto não codificado; opções "not applicable", "not reported", "cannot tell"; registrar o dado bruto (citação) e onde foi encontrado; coletar desfechos no formato reportado; testar com várias pessoas em alguns artigos; conferir exatidão; mudanças podem exigir revisitar — sec. 5.4.3 — "Include ‘not applicable’, ‘not reported’ and ‘cannot tell’ options as needed."
  - Treinamento inicial e periódico; algoritmo para itens em vários locais — sec. 5.5.3
  - Múltiplos relatos: duas estratégias; identificar a fonte principal — sec. 5.5.4
  - Desacordos: discussão, terceiro, autores, relatar; manter dado "as extracted"; κ não é rotina — sec. 5.5.5
  - Figuras: software de digitalização — sec. 5.5.8
  - Suspeita de má conduta: "awaiting assessment" — sec. 5.5.10
  - O que relatar sobre extração — sec. 5.5.11
  - Proveniência, conversões por computador — sec. 5.7
- Limitações/observações: foco em saúde; capítulo "last updated October 2019" dentro da v6.5. Sem número mínimo de estudos no piloto.

## higgins2024choosing — Higgins, Li e Deeks (eds.) (2024), Cochrane Handbook v6.5, cap. 6
- Arquivo/URL: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06 (fórmulas aparecem como imagens; valores tirados do texto)
- O que foi lido: 6.2.1, 6.2.9, 6.3, 6.3.1, 6.5.1.2, 6.5.2 (introdução), 6.5.2.3, 6.5.2.5, 6.5.2.7, 6.5.2.9.
- Pontos usados no capítulo:
  - C70 *clusters* e pareamento (obrigatório) — 6.2.1; C66 grupos múltiplos (obrigatório) — 6.2.9
  - Estudos não randomizados: estimativas ajustadas geralmente preferíveis; registrar variáveis de ajuste — 6.3
  - IC → EP com 3,92 (3,29; 5,15) — 6.3.1
  - SMD supõe que diferenças de DP refletem escalas; Hedges' g com DP combinado supondo DP semelhantes; Glass Δ com DP do comparador — 6.5.1.2
  - Multiplicar por −1, sem alterar o DP, e relatar; C61 (obrigatório) — 6.5.1.2, Box 6.5.a
  - "A particularly misleading error is to misinterpret a SE as a SD" — 6.5.2
  - p → t com gl N−2; "P<0.05" usar 0,05 (conservador); NS não resolve; EP = |DM|/t; com menos de 60 por grupo, IC deveria usar t — 6.5.2.3
  - IQR ≈ 1,35 DP só com n grande e distribuição próxima da normal; com assimetria não é possível; Wan estende com n — 6.5.2.5
  - Imputação de DP: aceitável para pequena proporção; não se a maioria falta; em SMD, DP maior enviesa para ausência de efeito — 6.5.2.7
  - Mediana no lugar da média só se simétrica; Wan para média a partir de quartis, com melhor desempenho em simulação (Weir 2018) — 6.5.2.9
- Limitações/observações: a caixa MECIR C61 está no Box 6.5.a.

## deeks2024analysing — Deeks et al. (eds.) (2024), Cochrane Handbook v6.5, cap. 10
- Arquivo/URL: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10
- O que foi lido: sec. 10.6.
- Pontos usados no capítulo:
  - OR → SMD (Chinn 2000), supondo distribuição logística e mesma variabilidade; EP multiplicado por √3/π = 0,5513 — sec. 10.6
- Limitações/observações: leitura seletiva.

## page2021prisma — Page et al. (2021), PRISMA 2020
- Arquivo/URL: Europe PMC PMC8005924, XML (BMJ 372:n71)
- O que foi lido: Tabela 1 (checklist), itens 9 a 13 e 17 a 20, 27.
- Pontos usados no capítulo: item 9 — "Specify the methods used to collect data from reports, including how many reviewers collected data from each report, whether they worked independently"; itens 10a, 10b, 12, 13b, 17, 19, 27.
- Limitações/observações: nenhuma.

## tricco2018prisma — Tricco et al. (2018), PRISMA-ScR
- Arquivo/URL: https://www.prisma-statement.org/s/PRISMA-ScR-Fillable-Checklist_11Sept2019.pdf; metadados no Crossref (28 autores)
- O que foi lido: checklist inteiro.
- Pontos usados no capítulo: item 10 (charting com "calibrated forms or forms that have been tested by the team before their use", independente ou em dupla, confirmação com investigadores); item 11 (variáveis, pressupostos e simplificações); item 15 (características de cada fonte com citações); item 17 (dados de cada fonte).
- Limitações/observações: o capítulo 04 usa a chave `tricco2018prismascr` para a mesma obra.

## havranek2020reporting — Havránek et al. (2020), Reporting guidelines for meta-analysis in economics (MAER-Net)
- Arquivo/URL: versão aceita na Deutsche Nationalbibliothek, https://d-nb.info/1268844314/34 (7 p.); metadados no Crossref (JES 34(3):469-475)
- O que foi lido: inteiro.
- Pontos usados no capítulo:
  - Definição precisa do tamanho de efeito e fórmulas de transformação; como os efeitos se tornam comparáveis — sec. 2.1
  - Dois ou mais revisores codificam e informam medida de concordância; codificar efeito, EP e gl (ou n); para meta-regressão, tipo de modelo, dummies de variáveis teoricamente relevantes omitidas, contexto, tipo de dado, formas alternativas de medida antes da conversão, ano, tipo de publicação, estudo/base de origem — sec. 2.2 — "Two or more reviewers should code the relevant research and disclose a measure of their agreement."
  - Compromisso: um segundo revisor pode conferir aleatoriamente uma proporção substancial se o protocolo for explícito e justificado — sec. 3
- Limitações/observações: as diretrizes não trazem fórmulas de correlação parcial; a fórmula veio do `metafor`. Paginação da versão aceita não coincide com a publicada; citado por seção.

## chinn2000simple — Chinn (2000), A simple method for converting an odds ratio to effect size
- Arquivo/URL: metadados conferidos na API da Crossref (DOI 10.1002/1097-0258(20001130)19:22<3127::AID-SIM784>3.0.CO;2-M) em 15/09/2026; regra resumida em @deeks2024analysing, sec. 10.6.
- O que foi lido: metadados e a descrição do método no Handbook (sec. 10.6); o texto integral não foi acessado.
- Pontos usados no capítulo:
  - ln(OR) → d multiplicando por √3/π, supondo variável latente logística com a mesma variabilidade nos grupos (via Handbook, sec. 10.6); base das linhas `dif_prop_contagens`, `dif_prop_lpm` e `rr_logit`.
- Limitações/observações: a variância pelo método delta com p0 fixo (`dif_prop_lpm`, `rr_logit`) é cálculo nosso, conferido contra `metafor::escalc("OR")` (vi = 1/ai + 1/bi + 1/ci + 1/di; teste local com metafor 5.0.1, 40/100 e 30/100: yi = 0,4418, vi = 0,0893) e contra os valores de referência dos testes da skill.

## zhang1998whats — Zhang e Yu (1998), What's the relative risk?
- Arquivo/URL: metadados conferidos na API da Crossref e no PubMed (E-utilities, PMID 9832001) em 15/09/2026: JAMA 280(19):1690-1691.
- O que foi lido: metadados e a fórmula de correção, reproduzida numericamente.
- Pontos usados no capítulo:
  - RR = OR/[(1 − P0) + P0 × OR]; invertida, OR = RR(1 − P0)/(1 − RR × P0), que depende do risco no controle; conferência: RR 1,25 com P0 = 0,40 dá OR = 1,5, e a fórmula devolve RR = 1,25 (cálculo nosso).
- Limitações/observações: com RR ajustado por covariáveis e P0 bruto, a conversão é aproximada; a linha sai com `aproximado = 1`.

## wilson2023practical — Wilson (2023), Practical Meta-Analysis Effect Size Calculator (Campbell)
- Arquivo/URL: página do calculador com as equações, https://www.campbellcollaboration.org/calculator/ (versão 2023.11.27), em cópia HTML salva no scratchpad pelo verificador anterior e reconvertida em texto nesta sessão (a URL /calculator/equations devolveu 403 hoje)
- O que foi lido: seções 1.1 a 1.3, 1.9 a 1.12, 1.26 a 1.28, 1.31, 1.33, 3.1.
- Pontos usados no capítulo:
  - 1.1: d, s_pooled, v_d, j = 1 − 3/(4(n1+n2−2)−1), g, v_g
  - 1.2: s = se·√n; 1.3: s_pooled a partir do DP da amostra total
  - 1.9: d = t√((n1+n2)/(n1n2)); 1.11: p suposto bilateral, t = |qt(p/2, df)|; 1.12: F com 1 gl no numerador
  - 1.26: r ponto-bisserial → d com n diferentes; variância canônica
  - 1.31: coeficiente não padronizado de dummy de tratamento; s_pooled a partir de s_y; "unsuitable for a regression coefficient associated with a scaled independent variable"; método pelo EP de B preferido porque "accounts for the covariates"
  - 1.33: logit d = B·√3/π, v_d = se_B²·3/π²
  - 3.1: z de Fisher, v = 1/(n−3)
- Limitações/observações: em 1.31, a variância aparece como v_d = (d·B/se_B)², dimensionalmente incoerente; a forma que preserva o t do coeficiente é (d·se_B/B)² = (se_B/s)², adotada no capítulo e registrada como observação. Em 1.12, a fórmula para n iguais aparece como √(F/N), quando deveria ser 2√(F/N); não usada.

## ludecke2019esc — Lüdecke (2019), pacote R esc 0.5.1
- Arquivo/URL: https://CRAN.R-project.org/package=esc (DESCRIPTION); código das funções impresso no R local
- O que foi lido: DESCRIPTION; código de `esc_B`, `esc_f`, `esc_t`.
- Pontos usados no capítulo:
  - Implementa o calculador de Wilson em R — DESCRIPTION
  - `esc_B` usa o DP combinado a partir do DP total (fórmula 1.31) — código
  - `esc_f` chama `esc_t(t = sqrt(f))`; `esc_t` com p usa `qt(p/2, df, lower.tail = F)`, sempre positivo — código
  - Recalculados (cálculo nosso): id 1 g = 0,0593; id 3 −0,0088; id 4 0,6680 (se 0,3638; com B/DP, 0,6401); id 5 0,3889; id 15 0,6109; id 20 0,3924; id 24 com p = 0,015: 0,4405 (t = 2,467); com p bilateral de z (0,0315): 0,3885; via r = z/√N e eq. 1.26: 0,3914; tratando z como t: 0,3840; pelas médias e DP: 0,8690 (t implícito 4,868); se ± fosse EP: DP ≈ 25,8 e 23,1, g = 0,110
  - O EP de `esc_B` para o id 4 (0,3638) não multiplica a variância por J²
- Limitações/observações: nenhuma.

## wan2014estimating — Wan, Wang, Liu e Tong (2014)
- Arquivo/URL: https://arxiv.org/pdf/1407.8038 (PDF igual ao publicado no BMC, "Page N of 13")
- O que foi lido: resumo e seções do cenário C2 e C3 (p. 5-6), Tabela 2.
- Pontos usados no capítulo:
  - Média ≈ (q1 + m + q3)/3 — p. 6, eq. 14
  - DP ≈ (q3 − q1)/η(n); para n grande η(n) ≈ 2Φ⁻¹((0,75n − 0,125)/(n + 0,25)) — p. 6, eq. 15-16
  - Converge para 1,34898, o estimador da Cochrane (eq. 17); com n pequeno, o método é mais preciso — p. 6
- Limitações/observações: simulações não lidas em detalhe.

## aloe2012effect e viechtbauer2026metafor — Aloe e Becker (2012); documentação e código de `metafor::escalc`
- Arquivo/URL: https://wviechtb.github.io/metafor/reference/escalc.html; https://raw.githubusercontent.com/wviechtb/metafor/master/R/escalc.r (DESCRIPTION: versão 5.1-18); metadados de Aloe e Becker no Crossref
- O que foi lido: seção "Partial and Semi-Partial Correlations" da documentação; linhas 1649-1745 do código.
- Pontos usados no capítulo:
  - Aloe e Becker (2012), Aloe e Thompson (2013) e Aloe (2014) descrevem correlações parciais e semiparciais para sintetizar coeficientes de regressão; `mi` = número total de preditores, contando o focal e não o intercepto; sinal vem do t — documentação
  - r = t/√(t² + n − m − 1) — código, l. 1668
  - Variância de grande amostra (1 − r²)²/(n − m) — código, l. 1727; ZPCOR com variância 1/(n − m − 2) — l. 1741
- Limitações/observações: texto integral de Aloe e Becker não lido; a entrada é citada como a obra descrita pela documentação. A tabela de conversões da skill usa (1 − r²)²/(n − m) com a coluna `m_preditores` (`parcial_r_d`) e, sem ela, (1 − r²)²/df residual (`parcial_r_d_gl`), que difere por uma unidade no denominador.

## fielperes2026effect — Fiel Peres (2026), Effect sizes for nonparametric tests
- Arquivo/URL: Europe PMC PMC12701665 (XML); metadados no Crossref (Biochem Med 36(1):5-16)
- O que foi lido: seção do teste de Mann-Whitney e referências.
- Pontos usados no capítulo: r a partir do z do Mann-Whitney, r = z/√N, N = n1 + n2 (Eq. 2, citando Fritz et al. 2012) — "requires only the values of z and N"
- Limitações/observações: revisão didática; usada só para a fórmula.

## kraft2020interpreting — Kraft (2020), Interpreting Effect Sizes of Education Interventions
- Arquivo/URL: versão do autor (47 p.), cópia salva no scratchpad pelo verificador anterior; original em https://www.matthewakraft.com/s/Kraft-2020-Interpreting-Effect-Sizes-ER.pdf
- O que foi lido: p. 1, 3, 9-11, 14-15, 17-18, 21.
- Pontos usados no capítulo:
  - Cohen: "recommended for use only when no better basis for estimating the [effect size] index is available" — p. 3
  - Correlacionais maiores que causais — p. 9-10
  - Testes do pesquisador 2 a 4 vezes maiores; desfechos de curto prazo, próximos e imediatos maiores — p. 10-11
  - DP de agregados ou ganhos: 1,5 a 3 vezes maiores — p. 14; DP do controle preferível sem linha de base; amostras homogêneas inflam — p. 15
  - Retorno por dólar e custo total; custos não monetários (tempo dos educadores) — p. 17; escalabilidade — p. 18
  - Benchmarks preK–12: < 0,05 pequeno; 0,05 a < 0,20 médio; ≥ 0,20 grande; 1.942 efeitos de 747 RCTs; mediana 0,10 — p. 21
- Limitações/observações: paginação da versão do autor; benchmarks detalhados no 08a.

## byrt1993bias — Byrt, Bishop e Carlin (1993)
- Arquivo/URL: resumo via Europe PMC (PMID 8501467)
- O que foi lido: resumo.
- Pontos usados no capítulo: κ afetado por viés e prevalência — "it can be misleading to report kappa values alone"
- Limitações/observações: definição do PABAK fica no capítulo 05.

## li2019randomized — Li et al. (2019), ensaio sobre abordagens de extração
- Arquivo/URL: resumo via Europe PMC (PMID 31302205)
- O que foi lido: resumo estruturado.
- Pontos usados no capítulo: cruzado com 26 pares; erros 17% (DAA + verificação), 16% (verificação simples), 15% (independente); independente 46 minutos mais lenta por artigo que DAA; "Independent abstraction may only be necessary for complex data items."
- Limitações/observações: só o resumo.

## buchter2020development — Büchter, Weise e Pieper (2020)
- Arquivo/URL: resumo via Europe PMC (DOI 10.1186/s12874-020-01143-3)
- O que foi lido: resumo.
- Pontos usados no capítulo: 25 documentos; piloto em amostra de estudos (18/25); extração por pelo menos duas pessoas (17/25).
- Limitações/observações: sem número mínimo para o piloto.

## belur2021interrater — Belur, Tompson, Thornton e Simon (2018/2021)
- Arquivo/URL: resumo via OpenAlex; metadados no Crossref (SMR 50(2):837-865); indicado nos slides da Aula 5, p. 34
- O que foi lido: resumo.
- Pontos usados no capítulo: comportamento de codificação muda entre e dentro de indivíduos ao longo do tempo; recomenda testes regulares de IRR e intra-avaliador nas etapas de triagem e codificação — "coding behavior changes both between and within individuals over time"
- Limitações/observações: artigo com acesso aberto híbrido, não lido integralmente.

## hedstrom2010causal — Hedström e Ylikoski (2010), Causal Mechanisms in the Social Sciences
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/5 Extração de dados - decomposição/HEDSTROM Mecanismos  causais.pdf`
- O que foi lido: inteiro (p. 49-67).
- Pontos usados no capítulo:
  - Explicações devem detalhar "the cogs and wheels of the causal process" — p. 50
  - Quatro ideias comuns: mecanismo de algo; causal; estrutura (variável interveniente "misses an important point"); hierarquia — p. 50-52
  - Esquema de mecanismo = explicação "how-possible"; evidência empírica torna o mecanismo plausível; checagem separa explicação de "storytelling" — p. 52-53
  - Mecanismos ajudam inferência e extrapolação; não são "magic bullet"; discriminar entre mecanismos; para evitar narrativa preguiçosa, esquema explícito e pressupostos com evidência — p. 54
  - "The crucial question is what kind of access a certain piece of evidence provides to the causal process" — p. 58
- Limitações/observações: foco na sociologia analítica; seções sobre simulação (p. 62-64) não usadas.

## kaidesoja2021three — Kaidesoja (2021), Three concepts of causal mechanism in the social sciences
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/5 Extração de dados - decomposição/Kaidesoja_Three_Concepts_of_Causal_Mechanism.pdf` (versão do autor, p. 15-33); registro bibliográfico no portal da Universidade de Helsinque
- O que foi lido: inteiro.
- Pontos usados no capítulo:
  - Três conceitos — p. 15
  - Elaboração: variável de teste que torna espúria, modera ou medeia — p. 17
  - Conceito 2: modelos estruturais, DAG, invariância e modularidade, desenhos que imitam experimentos — p. 18-22
  - Conceito 3: métodos plurais (análise narrativa, process tracing, comparative process tracing, simulação) — p. 23-24
  - Confiança maior quando o mecanismo é confirmado por métodos e dados independentes — p. 27-28
  - "they should be kept separate to avoid unnecessary conceptual confusions" — p. 29
- Limitações/observações: versão aceita; registro confirma p. 15-33.

## dalkin2015whats — Dalkin et al. (2015), What's in a mechanism?
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/5 Extração de dados - decomposição/s13012-015-0237-x.pdf`
- O que foi lido: inteiro (7 p.).
- Pontos usados no capítulo:
  - CCTV: reduz crime, quando reduz, por convencer potenciais infratores do risco de detecção — p. 1-2
  - Chen: mecanismos mediadores e moderadores — p. 2
  - Pawson e Tilley: recursos + raciocínio — p. 3
  - M(Resources) + C → M(Reasoning) = O; "identifying the reasoning avoids the issue of conflating programme strategy (resource) with mechanism" — p. 4
  - Registro de cuidados paliativos, trajetória imprevisível, ansiedade, menos registros — p. 5
  - "dimmer switch" — p. 5-6 (não usado nesta versão)
- Limitações/observações: exemplo de saúde.

## cintron2022heterogeneous — Cintron et al. (2022), Heterogeneous treatment effects in social policy studies
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/5 Extração de dados - decomposição/1-s2.0-S1047279722000667-main.pdf`
- O que foi lido: inteiro, com apêndices.
- Pontos usados no capítulo:
  - 55 artigos de 2019; um excluído por relatar só efeitos simulados; 54 analisados — p. 79, 81
  - 24 (44%) com HTE; 15 (63%) a priori; 17 (71%) só estratificação; 5 (21%) interação; 2 (8%) ambos; nenhum algoritmo — p. 79, 81
  - Tabela 1: estratificação descreve e fornece resultados para testes em revisões futuras; interação testa; algoritmos exploratórios com validação cruzada — p. 80
  - Desenhos: DiD 12, antes-depois 9, regressão 7, painel FE 6, VI 3, PSM 1, stepped wedge 1, controle sintético 1, CITS 1 — p. 81
  - "null results should be routinely reported for all a priori specified groups"; resultados com incerteza incorporáveis em revisões; qualitativa ajuda a identificar fontes — p. 82
  - Formulário de extração de HTE (Tabela A.1) — p. 83
- Limitações/observações: periódicos de alto impacto de 2019, foco em saúde. A amostra inclui um estudo sobre Bolsa Família (Tabela A.2), não usado.

## zidar2017tax — Zidar (2015, rev. 2017), Tax Cuts for Whom?
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/5 Extração de dados - decomposição/w21035.pdf`
- O que foi lido: resumo e introdução (p. 1-2), conforme a instrução.
- Pontos usados no capítulo: variação regional da distribuição de renda combinada a mudanças federais para testar efeitos heterogêneos; relação positiva com emprego vem sobretudo de cortes para grupos de menor renda; "the effect of tax cuts for the top 10% on employment growth is small" — resumo, p. 1-2.
- Limitações/observações: há versão publicada (JPE) não consultada.

## castro2024avaliacao — Castro, Costa e Finamor (2024), Avaliação de Impacto (FGV EESP CLEAR)
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/5 Extração de dados - decomposição/avaliacao_impacto.pdf`
- O que foi lido: seletivo: forma de citação (p. 2), introdução e sumário (p. 3-6), módulo I (p. 7-9), módulo II (p. 11-15, 22-24), módulo III (p. 29-30, 35-38), módulo IV (p. 45-48, 52-57), módulo V (p. 67-72).
- Pontos usados no capítulo:
  - Aleatorização: independência; diferença de médias = ATT = ATE — p. 12; teste de balanceamento — p. 15
  - Cumprimento parcial e encorajamento: LATE dos compliers com monotonicidade, Wald e MQ2E; ITT pela forma reduzida, "particularmente interessante para a discussão em políticas públicas" — p. 22-24
  - RDD: janela (viés × variância) — p. 35; continuidade e manipulação, teste de densidade — p. 36; continuidade de outras variáveis, janelas, polinômios, placebos — p. 37; efeito local; fuzzy como instrumento — p. 38
  - DiD: H1 e H2 não testáveis; pré-tendências — p. 48; controles e cortes transversais com mudanças de composição — p. 52-53; adoção sequencial e estimadores alternativos — p. 53; inferência com cluster — p. 54
  - Controle sintético: pesos, efeito por período, permutação, ajuste pré-tratamento perfeito e muitos períodos — p. 54-57
  - Pareamento: covariáveis pré-intervenção — p. 67; independência condicional e suporte comum — p. 68; ATT e ATE — p. 69; placebos — p. 71-72; trimming leva a LATE — p. 72
- Limitações/observações: material didático com exemplos fictícios; não tem módulo sobre painel com efeitos fixos (a linha da tabela usa a H1 do DiD).

## keele2015statistics — Keele (2015), The Statistics of Causal Inference
- Arquivo/URL: resumo via OpenAlex (texto fechado); Anexo G da proposta OQF (p. 89) remete a ele
- O que foi lido: resumo.
- Pontos usados no capítulo: foco nas hipóteses de identificação necessárias para interpretação causal — resumo.
- Limitações/observações: artigo não lido; uso mínimo.

## gerring2022democracy — Gerring, Knutsen e Berge (2022), Does Democracy Matter?
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/5 Extração de dados - decomposição/annurev-polisci-060820-060910.pdf`
- O que foi lido: seletivo: p. 357-368 (base de dados, codificação, t, heterogeneidade, viés de limiar).
- Pontos usados no capítulo:
  - Análise = estudo × desfecho × indicador; log e mesma medida de outra base são testes de robustez — p. 362
  - Modelo de referência: primeira especificação ou declaração explícita; "When left implicit, we make a judgment call based on how authors present their results" — p. 362
  - Direção, significância e t; 210 observações recodificadas por segundo autor, 82% replicados (atingibilidade) — p. 363
  - "The t-value is not an effect, strictly speaking" — p. 364
  - t normativamente ajustado; cerca de 15% das análises com classificação discutível; desfechos codificados conforme contexto (fecundidade, impostos, subsídios); t imprecisos (coeficiente e EP com um dígito) removidos da figura — p. 365
  - Cautela com menos de 10 análises — p. 366; 60 análises descartadas por só coeficientes e estrelas — p. 367 (nota da Tabela 3)
- Limitações/observações: uso analítico da distribuição de t no 08a.

## cancela2016explaining — Cancela e Geys (2016), Explaining voter turnout
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/5 Extração de dados - decomposição/1-s2.0-S0261379416300956-main.pdf`
- O que foi lido: seletivo: p. 264-267 (introdução, seção 2 e início da seção 3).
- Pontos usados no capítulo:
  - Direção esperada definida a priori; cada coeficiente é um teste; sucesso, fracasso ou anomalia; resultado modal do estudo — p. 265
  - Taxas por estudo e por teste; estudos com vários modelos pesam mais por teste; operacionalizações tratadas como equivalentes; magnitude não considerada — p. 266
- Limitações/observações: análise da taxa de sucesso no 08a.

## bia2026health — Bia et al. (2026), Health policies in long-term care facilities (protocolo JBI de evidência textual)
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/5 Extração de dados - decomposição/1-s2.0-S2215016126000154-main.pdf`
- O que foi lido: seletivo: p. 1-6.
- Pontos usados no capítulo: extração de tipo de texto, população representada, contexto, posição declarada, conclusões com trechos ilustrativos e notas do revisor; dois revisores independentes e terceiro para desacordos — p. 5; "Effect measure not applicable" — p. 4 (não usado).
- Limitações/observações: a entrada de references.bib tem "and others".

## brydges2019effect — Brydges (2019), Effect size guidelines in gerontology
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/5 Extração de dados - decomposição/Brydges-Innovation-in-Aging-2019_Effect-size-guidelines-etc-in-gerontology rev.pdf`
- O que foi lido: inteiro.
- Pontos usados no capítulo:
  - Cohen: d = 0,20; 0,50; 0,80 e r = 0,10; 0,30; 0,50; não baseados em estimativas quantitativas e só recomendados sem estimativas do campo — p. 1-2
  - Valores absolutos dos efeitos negativos usados na distribuição — p. 3
  - 4.049 efeitos de 88 meta-análises; g = 0,16; 0,38; 0,76 — p. 1, 3-4
- Limitações/observações: detalhes dos benchmarks no 08a.

## schaefer_oqfunciona — Schaefer, Borges e Freitas (2025), proposta OQF (preprint)
- Arquivo/URL: texto-base no scratchpad (`fontes/oqf_texto_base_schaefer_borges_freitas_2025.txt`)
- O que foi lido: PDF p. 20-35, Anexo G (p. 60-101) e Anexo J (p. 104-107).
- Pontos usados no capítulo:
  - Caixa de ferramentas (Tabela 3) — p. 20-21
  - "as linhas representam os estudos (e/ou os modelos) revisados"; PICOC, estratégia, amostra, controles; hierarquia de evidências — p. 21
  - Mecanismos: mencionam, testam ou identificam — p. 23; t como valor padronizado ("quanto maior o valor de T, maior a diferença") — p. 23
  - Mediação (Delegacias da Mulher), subconjuntos (Luz para Todos), métodos qualitativos; moderadores como fatores de contexto — p. 24
  - Duas RS incluídas por busca manual — p. 30; 71 variáveis de 21 trabalhos; 11 quantitativos, 6 qualitativos, 2 mistos, 2 revisões — p. 31-32; mecanismos e moderadores em 5 (3 quanti, 1 misto, 1 revisão), custos em 6; codificação exige conhecimento do campo — p. 32
  - Estratégias: 3 experimentais, 4 seleção em observáveis (diferenças em diferenças), 1 meta-análise; g do coeficiente do modelo principal, n e DP da VD — p. 33
  - Anexo G: pares _id + trecho, sem página — p. 60-101; estratégia "ver Keele (2015)" — p. 89; hierarquia 0 a 6 com 6 = RS — p. 90; "Ano das eleições analisadas" — p. 91; direção ampla (dummy) — p. 92; direção restrita (1/0/−1) — p. 93
  - Anexo J: esc_B (ids 1, 4, 3, 5), esc_f (15, 20), esc_t(p = 0,015) para Mann-Whitney com trecho de médias, U, Z e P (24), meta-análise (28) — p. 104-106; data frame com n = 192 (id 4), 160 (id 20), 9 (id 28) — p. 107
- Limitações/observações: recálculos na nota do `esc`.

## schaefer2026aula5 — Schaefer (2026), slides Aula 5 "Extração de dados, decomposição"
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/9 Slides/OQF_MAPE_Aula_5 Decomposição (Data Extraction).pdf`
- O que foi lido: inteiro (36 p.), visualmente.
- Pontos usados no capítulo:
  - Pergunta REFIS com quatro desfechos — p. 6
  - Fluxograma REFIS: 16 aprovados − 5 excluídos (4 não respondiam + 1 não localizado) + 9 bola de neve; corpus final 21 — p. 8 (a conta dá 20)
  - O que extrair: formais, metodológicas, substantivas — p. 10
  - Quadro 2 WhatsApp, adaptado de Sampaio e Figueiredo Filho (2019), com "Recorte Temporal: Ano das eleições analisadas" e "Resultados" como única substantiva — p. 11
  - Quadro 3 de Juliano et al., com decisão final manter/excluir — p. 14
  - Does Democracy Matter e planilha suplementar com vários modelos por estudo — p. 15-16
  - Protocolos de adequação (RoB 2, ROBINS-I, CASP, MMAT), hierarquias e matriz de Petticrew e Roberts — p. 19-21 (não usados)
  - Tabela 5, toolkit dos celulares — p. 24
  - Quadro 1 tipos de estudo — p. 26; definições a1 — p. 27; b1 — p. 28; a2 — p. 29; b2 (inclui mediação, efeitos heterogêneos e subgrupos) — p. 30
  - Tally — p. 32; AIDE — p. 33; validação com Belur et al. — p. 34
- Limitações/observações: o mapa dimensão × tipo está na Aula 6.

## schaefer2026aula6 — Schaefer (2026), slides Aula 6 "Análise de dados"
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/9 Slides/OQF_MAPE_Aula_6 Análise de dados.pdf`
- O que foi lido: texto das p. 37-39 e 49-52; p. 37-39 e 51 vistas como imagem.
- Pontos usados no capítulo:
  - Exemplo 5, meta-análise de comparecimento em Government and Opposition — p. 38; tabela com 32 estudos, 74 modelos, 72 sucessos, 0 fracassos, 2 "no link", taxa 0,97 (voto obrigatório com sanções) — p. 39
  - Mapa: Contexto (todos), Efeito (b2), Mecanismos (a1, b1, b2), Moderadores (a1, b1, b2), Percepções/Implementação (a1, a2, b1), Custos (a2, b1, b2) — p. 51
- Limitações/observações: autoria da meta-análise da p. 38 não aparece no slide; o capítulo não a nomeia.

## schaefer2026codigos — codebook do curso, base de decomposição do REFIS e script de simulação
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/8 C¢digos R/quadro_decomposicao_estudos EXEMPLO.xlsx` (5 abas); `8 Códigos R/base_decomposição.xlsx` (2 abas); `8 Códigos R/1 Simulação tamanho do efeito.R`
- O que foi lido: todas as abas via pandas; script inteiro.
- Pontos usados no capítulo:
  - Aba comum: id_rs, titulo, primeiro_autor, universidade, n_autores, ano, tipo_publicacao, idioma, nome_publicacao, doi, base, palavras_chave, resumo, problema
  - a1: duracao_campo "codifique como 999 (sem informação) e longitudinal = 0"; processo_causal; condicoes_ativacao; custo_id; citacao_ilustrativa
  - a2: cobertura_percentual "Contínua (0-100) ou Categórica (99 = universal; 88 = majoritaria; 50 = parcial; 25 = residual; 999 = sem info)"; perfis com "Não reportado"
  - b1: consistencia e cobertura "999 se não aplicável"; condições "Não se aplica"; mecanismo_identificado com a regra "padrão comparativo (ex.: 'toda vez que X, Y') é diferente de mecanismo (ex.: 'X ativa Z que produz Y porque...')"; evidencias_mecanismo (rastro_processual; relato_atores; sequencia_eventos; analise_contrafactual; comparacao_entre_casos)
  - b2: estrategia_identificacao (RCT; DID; RD; VI; painel_FE; PSM; event_study; synthetic_control; IV_2SLS; selecao_observaveis; sem_estrategia); direcao_am "Direção no sentido normativo"; direcao_re "1 se p-valor < 0,05 e efeito positivo; 0 se p-valor ≥ 0,05; -1 se p-valor < 0,05 e efeito negativo"; coeficiente/erro_padrao/t_valor/desvio_y "ou 999"; hedges_g com atalho g ≈ t × √(1/n₁ + 1/n₂); moderador_id "termo de interação significativo, análise de subgrupos com testes de diferença, ou efeitos heterogêneos reportados separadamente"; percepcao_id; implementacao_id; custo_id; modelo_principal
  - base_decomposição, aba Final: 20 trabalhos; 15 "Sim" e 5 "Não"; bases Teses/Dissertações 9, Bola de neve 4, WoS 2, OpenAlex 2, SciELO 2, IPEA 1; observações das recusas (três "Não testa diretamente o parcelamento...", um parcelamento espontâneo "além disso, não é possível extrair os resultados", um "Não encontrado"); resumos dos ids 1, 4, 45, 77, 106, 193 usados na tabela do REFIS (outros lidos: 2, 3, 87, 100, 107, 191, 192 sem resumo, 197, 199)
  - Script: esc_mean_sd com médias 50 e 60 (d = −1) e gráfico "(d = 1)"; segundo exemplo com DP 30 e 50, n 50 e 100 (cálculo nosso: DP combinado 44,39, d = 0,180; com DP do controle, 0,160)
- Limitações/observações: a aba "Trabalhos - Traços comuns" da base tem 29 linhas com coluna de conferência manual (INCLUIR/EXCLUIR); a base pode ser versão intermediária.

## schaefer2019whatsapp e juliano2023mudanca — quadros de extração dos slides
- Arquivo/URL: vistos nos slides da Aula 5 (p. 11 e 14); artigos não lidos.
- O que foi lido: só os quadros reproduzidos.
- Pontos usados no capítulo: estrutura dos quadros (ver schaefer2026aula5).
- Limitações/observações: artigos originais não consultados.

## legalacre2026fichamento — prática do projeto de bioeconomia (Legal-Acre)
- Arquivo/URL: `~/Desktop/Legal-Acre/revisao-sistematica/03-decomposicao/quadro_decomposicao.csv`, `PROMPT_FICHAMENTO.md`, `fichamentos/RELATORIO_FICHAMENTO.md`, `fichamentos/_consolidado/saidas/RELATORIO_CONCORDANCIA.md`
- O que foi lido: codebook (70 variáveis) e prompt inteiros; relatório de fichamento inteiro; relatório de concordância (resumo, desenho, dimensões e variáveis selecionadas).
- Pontos usados no capítulo:
  - 999 = ausente no texto; NA_secao = seção não aplicável; múltiplos desenhos → múltiplas fichas; paginação impressa com offset; gate de citações; validação de 25% — PROMPT_FICHAMENTO.md, regras 1-7 e passo 4
  - tipo_trabalho "exclusivamente na estratégia metodológica descrita na seção de métodos do estudo, não no tema"; mecanismo "não infira mecanismos não discutidos pelos autores/as"; estrategia_identificao inclui "Revisão Sistemática; Meta-análise"; direcao_efeito_restrita com "Nulo (não significativo ao nível reportado pelos autores/as)"; valor_coeficiente_padronizado "(T, Z, ou outro)"; modelo_principal com critério auxiliar — quadro_decomposicao.csv
  - 118 textos, 136 fichas, 18 com mais de uma; 3 PDFs errados; gate 2.683 citações OK; κ tipo_trabalho 0,83; 4 divergências de desenho, todas sobre quantos e quais desenhos (fronteira a1/a2); recomendação de critério explícito a1 × a2 — RELATORIO_FICHAMENTO.md, §1-4
  - Concordância de valores 80,6% (716); estrita 72,8%; desenho 22/26; a1 44,4%; mecanismo_processo 16,7% (12); valor_coeficiente_padronizado 33,3% (6), com Carrilho2022 = 999 vs "Cohen's d = 0.32"; coeficiente 66,7% (6) — RELATORIO_CONCORDANCIA.md
- Limitações/observações: documentação interna não publicada; a validação foi entre dois agentes de IA. O coordenador decide se a citação a um projeto interno fica no livro público.

## fichamento-sistematico (skill) e revisao-sistematica (skill em construção)
- Arquivo/URL: `~/.claude/skills/fichamento-sistematico/SKILL.md`, `references/schema_codebook.md`, trecho de `references/INSTRUCOES_FICHADOR.md`; `~/.claude/skills/revisao-sistematica/SKILL.md` (tabela de etapas), `agentes/extrator-efeitos.md`, `assets/mapas/conversoes_efeito.csv`, cabeçalho de `scripts/rslib/efeitos_verificar.py`, `rs.py analise --help`
- O que foi lido: SKILL.md e schema inteiros da irmã; trechos citados da skill nova.
- Pontos usados no capítulo:
  - Colunas do codebook; classificadora detectada por aplicavel_se; NA_secao; sinalização abaixo de 80% ou, se categórica, com κ e PABAK abaixo de 0,7; skill não decide divergências — fichamento-sistematico
  - Fichador cita a numeração impressa com offset_pagina — INSTRUCOES_FICHADOR.md, regra 4
  - Etapa 8 piloto 2-3 por bloco (G6); etapa 9 extração e RoB (G7) — SKILL.md
  - extrator-efeitos: lê o PDF inteiro em faixas de até 20 páginas; não converte nem interpreta significância; `pagina` = índice do PDF; `sdy` = DP do comparador ou da linha de base; enums de estimando e tipo_estatistica — agentes/extrator-efeitos.md
  - preparar-efeitos recusa revisões; verificar-efeitos confere trecho, plausibilidade (inclusive |g| > 2) e exige verificado_humano para o G7 — efeitos_verificar.py
  - formula_id: md_sd, t_ind, t_ind_n_total, f1_ind, beta_sd, or_logit, r_d, r_d_n_total, parcial_r_d, parcial_r_d_gl, p_n_t, g_informado, d_informado, mann_whitney_z, mediana_iqr_wan, mediana_iqr_aprox, de_cluster — conversoes_efeito.csv (versão v1.1)
- Limitações/observações: as diferenças antes registradas entre o capítulo e a tabela da skill foram alinhadas na skill (contratos v1.1): (i) `mann_whitney_z` usa r = z/√N seguido de r → d; (ii) `mediana_iqr_wan` só com quartis, e IQR/1,35 virou `mediana_iqr_aprox`; (iii) `parcial_r_d` usa n − m − 1 e (1 − r²)²/(n − m) com `m_preditores`, e a rota pelo df residual virou `parcial_r_d_gl`; (iv) r → d só com N virou `r_d_n_total` (p1 = 0,5, cálculo nosso a partir da eq. 1.26 de Wilson). Continuam duas convenções de paginação (fichas impressa, efeitos índice do PDF).

## Plano (Apêndices A, B e C) — especificação metodológica do projeto
- Arquivo/URL: `/Users/felipelmc/.claude/plans/cara-o-seguinte-jaunty-zebra.md`
- O que foi lido: PLANO FINAL §1 e §4; Apêndices A, B e C.
- Pontos usados no capítulo: hierarquia estudo > relato > efeito; direção pelo estimador pontual relativa a direcao_desejada, significância separada; tabela de conversões com formula_id e aproximados; estimandos ITT/LATE/RDD; RS nunca como estudo primário; piloto 2-3 por bloco; 100% dos números verificados; ≥ 20% (mín. 10), κ/PABAK ≥ 0,7 e ≥ 80%; alerta |g| > 2; G6 e G7; codebook oqf_decomposicao.csv; extrator-efeitos; efeitos.R.
- Limitações/observações: sem chave bibliográfica; citado como "especificação metodológica do projeto" ou "(E)".

---

## Fontes indicadas e não acessadas

- Borenstein, Hedges, Higgins e Rothstein (2009), Introduction to Meta-Analysis, cap. 7: o PDF oficial (meta-analysis.com) e a amostra de capítulo (meta-analysis-workshops.com) devolveram 403 ou página HTML; cópias em sites não autorizados não foram usadas. Substituído por Wilson, Cochrane 6 e 10 e Harrer.
- Campbell effect size calculator, página /calculator/equations: 403 nesta sessão; usada a cópia HTML da página do calculador (mesma versão 2023.11.27) salva pelo verificador anterior no scratchpad, que contém as equações.
- MAER-Net sobre correlações parciais: Havránek et al. (2020) foi lido, mas não trata de fórmulas de correlação parcial; Stanley, Doucouliagos e Havránek (2024) sobre viés de correlações parciais não foi acessado.
- Keele (2015): texto integral fechado; só o resumo.
- Fritz, Morris e Richler (2012): não acessado; fórmula tomada de Fiel Peres (2026).
- JBI Manual, cap. 10, sec. 10.2.9.2 (piloto de extração em 2 ou 3 fontes): só o sumário da página foi acessível (Confluence com conteúdo bloqueado para acesso anônimo); o capítulo remete ao @sec-03-regras, que cita a recomendação.
- Artigos originais do WhatsApp (Schaefer et al. 2019) e de Juliano et al. (2023): não lidos; usados só os quadros dos slides.
- Estudos do Anexo J e do REFIS: só os trechos transcritos no Anexo J e os resumos da base.
