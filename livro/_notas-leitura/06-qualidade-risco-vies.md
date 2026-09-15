# Notas de leitura: 06-qualidade-risco-vies

Notas refeitas em 15/09/2026 a partir de nova leitura das fontes (textos extraídos com `pdftotext -layout`, slides vistos como imagem, páginas web baixadas e convertidas em texto; arquivos temporários no scratchpad da sessão, fora do repositório). Convenções: "p." = página impressa do documento; na proposta OQF uso a página impressa no rodapé (= marcador `--- pN ---` do texto-base menos 1); slides e ementa pela página do PDF; Handbook Cochrane por seção; Waddington et al. pela paginação do manuscrito aceito. Trechos entre aspas são literais (≤ 25 palavras). Downloads da web foram conferidos por hash contra cópias já existentes no scratchpad quando havia (ROBINS-I V2, Waddington, EPOC, CASP, MMAT, Nutley, PRISMA-ScR: hashes idênticos).

## madaleno2016guide — Madaleno & Waights (2016), Guide to scoring evidence using the Maryland SMS
- Arquivo: `~/Downloads/zs6h4-osfstorage-archive/4 Filtragem e controle de qualidade/16-06-28_Scoring_Guide.pdf` (43 pág. PDF; página impressa = PDF − 2; número no cabeçalho de cada página).
- O que foi lido: inteiro (introdução, cap. 2 a 7, apêndices 1 a 3).
- Pontos usados no capítulo:
  - SMS ordena avaliações de 1 a 5 pela "robustness of the method used and the quality of its implementation"; robustez = lidar com viés de seleção. p. 1.
  - Pontuar "is not an exact science and often involves a degree of judgement". p. 1.
  - Conclusões dependem do balanço da evidência; improvável que uma nota mude a conclusão. p. 2.
  - Muitas avaliações patrocinadas por governos "do not use credible strategies to assess the causal impact". p. 3.
  - Seleção pode viesar para cima (firmas ambiciosas) ou para baixo (firmas com problemas). p. 3-4.
  - Versão "adjusted" de Sherman et al. (1998). p. 4, nota 1.
  - Box 1: níveis 1-5 (parafraseados); nota: "a little stricter than the original scale" para separar 3, 4 e 5. p. 5.
  - RCT: (5,5) se randomização bem-sucedida, atrito tratado, sem contaminação; (5,4) um critério gravemente violado; (5,3) dois ou mais. p. 7. Exemplo Doyle (5,3). p. 9.
  - Métodos SMS 4 "need to make the case" de que a variação é aleatória. p. 10.
  - IV (4,4) se relevante, exógeno, excluível; inválido: "Scored as per underlying method" (transversal 2; DiD 3). p. 11. Exemplo Nishimura (4,2). p. 12-13.
  - RDD (4,4) se descontinuidade nítida ou método fuzzy, só tratamento muda no limiar, sem manipulação; tabela repete o exemplo "cross section with invalid IV" (inconsistência). p. 13-14.
  - "We define SMS 3 methods to be the minimum standard for our reviews." p. 18.
  - DiD (3,3) tendência comum crível + período conhecido; (3,2) se um falha. p. 19. Exemplo Valentin & Jensen (3,2). p. 20.
  - Painel FE: texto anuncia "two main criteria" e lista três (inconsistência); FE (3,3) com três critérios; FD (3,3) com dois. p. 21.
  - Box 2: "fixed effects" em corte transversal = controles; transversal com controles tem máximo 2. p. 23.
  - PSM: transversal máx. 2 (variáveis relevantes, suporte comum); com DiD/painel máx. 3. p. 23-24.
  - Regressão transversal (2,2)/(2,1). p. 26. Antes-depois: tabela do texto "2, 2 if inadequate control variables" p. 27; apêndice "2, 1" p. 31 (inconsistência).
  - Additionality (efeitos declarados) e impact modelling não pontuáveis. p. 28-29, 32.
  - Apêndice 1 (quick scoring). p. 30-32. MPH (4,3)/(4,2). p. 31, 34. Heckman/CF: 4 com IV válido; 3 com DiD/painel; 2 transversal. p. 31, 36-37. Arellano-Bond (3,3)/(3,2). p. 30, 39.
- Limitações/observações: references.bib tem `madaleno2015guide` ("Guide to scoring methods...", 2015), versão citada na ementa; o arquivo lido é a atualização de junho de 2016. A página do guia no site (acima) confirma a data de 29/06/2015 e a atualização de junho de 2016.

## whatworksgrowth2015sms — What Works Growth (2015), página "The Maryland Scientific Methods Scale (SMS)"
- URL: https://whatworksgrowth.org/resource-library/the-maryland-scientific-methods-scale-sms/ (baixada em 15/09/2026); também https://whatworksgrowth.org/resource-library/guide-to-scoring-the-evidence/
- O que foi lido: página inteira (níveis 1-5 e nota) e página do guia.
- Pontos usados no capítulo:
  - Triagem por relevância, geografia, idioma e métodos (avaliações do Reino Unido e OCDE, sem limite temporal); depois triagem por robustez com a SMS.
  - "We shortlist all those impact evaluations that could potentially score 3 or above on the SMS."
- Limitações/observações: página institucional sem paginação.

## thomas2003children — Thomas et al. (2003), Children and healthy eating (EPPI-Centre)
- Arquivo: `.../4 Filtragem e controle de qualidade/FinalReport-webV2.pdf` (páginas impressas no rodapé).
- O que foi lido: sumário; seções 2.5 a 2.7 (p. 20-25); cap. 4 inteiro (p. 48-54); início do cap. 5 (p. 55-56).
- Pontos usados no capítulo:
  - Quatro critérios "core" (dados pré para todos, dados pós, relato de todos os desfechos, grupo equivalente) → "sound"/"not sound". p. 21.
  - Os critérios não distinguem randomizados de não randomizados nem "quality of method and quality of reporting"; categorias adicionais; julgamento final alto/médio/não sólido. p. 21.
  - Procedimentos por dois revisores independentes, desacordos por discussão. p. 22.
  - Estudos de visões: 12 critérios (5 de relato, 4 de confiabilidade/validade, 3 de enraizamento na perspectiva das crianças). p. 23-24.
  - Qualidade não deveria excluir estudos "unnecessarily"; três objetivos; categoria 2 (lacunas de relato) na meta-análise com sensibilidade; categoria 3 fora. p. 49.
  - 14 alta, 14 média, 5 não sólidos; 22 seguiram para a síntese. p. 48-50.
  - Nenhum estudo de visões atendeu os 12 critérios. p. 48, 54.
- Limitações/observações: a entrada `thomas2003children` em references.bib é incompleta (misc, "others"); não editada. Na p. 54, "Three studies" seguido de quatro nomes (erro menor, não usado).

## kopittke2021funciona — Kopittke & Ramos (2021), homicídios no Brasil (RAP 55(2):414-437)
- Arquivo: `.../4 Filtragem e controle de qualidade/download.pdf` (página impressa no rodapé de cada página).
- O que foi lido: resumo; seções 1 (parte), 2 (p. 418-421), 3.1-3.3 (p. 422-425), Quadro 4.
- Pontos usados no capítulo:
  - Inclusão e síntese segundo o Relatório Maryland, com auxílio de Madaleno e Waights (2015); discordâncias resolvidas pelo coordenador. p. 418.
  - Desenho experimental ou quase-experimental "atingindo pelo menos o nível 3 da Escala Maryland"; publicados ou não (artigos, teses, dissertações, relatórios), qualquer língua. p. 419.
  - Quadro 1 (Sherman et al. 1997): nível 2 inclui antes-depois "com grupo não equivalente"; nível 4 = requisitos do 3 com número de unidades "bastante elevado". p. 421.
  - Módulos positivos/negativos/sem impacto com p < 0,1, lido como probabilidade de 90% de os resultados "se repetirem em outras situações". p. 421.
  - Quadro 2: "funciona" = pelo menos 2 avaliações de nível 3 com testes de significância. p. 422.
  - Figura 1: 195 selecionados para análise metodológica; excluídos 75 (níveis 1 e 2), 15 (outros desfechos), 64 (não eram avaliação de impacto); 41 incluídos. p. 423.
  - Tabela 1: 27 artigos, 11 dissertações/teses, 3 relatórios; nível 4 = 5 e nível 3 = 35 (soma 40 de 41); área dos autores: economia 38; texto diz 86 módulos, tabela soma 85. p. 423-424.
- Limitações/observações: sem avaliação de risco de viés por domínio. Resumo diz 13.352 rastreados e o texto 13.353 (p. 422). A tabela imprime 94% para 38/41 (= 93%); no capítulo usei a contagem.

## garcia2017educational — García & Saavedra (2017), meta-análise de TCR (RER 87(5):921-965)
- Arquivo: `.../4 Filtragem e controle de qualidade/garc°a-saavedra-2017-...pdf` (número de página no rodapé; mapeamento conferido página a página com `pdftotext -f/-l`).
- O que foi lido: p. 928-934 (elegibilidade, qualidade, estimativas), p. 939, 941, 948 (resultados sobre qualidade).
- Pontos usados no capítulo:
  - "Must use a treatment-comparison research design"; pré-pós de um grupo não elegível. p. 929.
  - Qualidade pelo WWC 2.1: atende, atende com ressalvas, não atende. p. 929.
  - Exemplo: atrito global de 20% admite até 4 p.p. de atrito diferencial. p. 931.
  - Equivalência de linha de base < 0,25 DP; quase-experimentos no máximo "com ressalvas"; condições do RDD (integridade da variável de corte com teste de densidade, atrito, continuidade de covariáveis, forma funcional e banda). p. 932.
  - Distribuição: 43% atendem, 24% com ressalvas, 33% não atendem; melhor estimativa escolhida do estudo de maior qualidade. p. 933.
  - Investigadores codificaram qualidade de forma independente; unânimes exceto em duas instâncias. p. 934.
  - Resultados robustos à exclusão dos estudos de menor qualidade (Fig. S1). p. 939, 941.
  - Qualidade não associada às estimativas na meta-regressão. p. 948.
- Limitações/observações: padrão educacional dos EUA; limiares valem como exemplo de pré-especificação.

## petticrew2006systematic — Petticrew & Roberts (2006), Systematic Reviews in the Social Sciences
- Arquivo: `~/Downloads/zs6h4-osfstorage-archive/1 Tipos de revis*/guide-of-systematic-reviews-in-social-sciences.pdf` (página impressa no cabeçalho). Metadados conferidos na página de créditos (Blackwell, Malden MA, 2006, ISBN 978-1-4051-2111-8) e DOI 10.1002/9780470754887 por content negotiation.
- O que foi lido: seção 3.1 (p. 57-61); cap. 5 inteiro (p. 125-157).
- Pontos usados no capítulo:
  - Box 3.1, hierarquia de sete níveis. p. 58. Propósito original "is often forgotten"; hierarquia para efetividade. p. 58.
  - Tipologias em vez de hierarquias; relatos positivos por lealdade a quem presta o serviço. p. 59. Tabela 3.1 (pergunta × desenho). p. 60.
  - ECR pequeno, mal desenhado ou com perdas não deve ficar acima de estudos bem conduzidos. p. 60.
  - Vieses inflam efeitos (Iron Law de Rossi); argumento contra vote counting. p. 126.
  - Contatar autores "avoids confusing inadequate reporting with a poor-quality study"; relato ≠ qualidade metodológica (Huwiler-Müntener). p. 127.
  - Peso narrativo e análise de sensibilidade; Woolf e erro tipo II. p. 128.
  - Ferramentas "off-the-shelf" clínicas e duplo-cego impossível. p. 128-129.
  - Jüni et al.: 25 escalas, 17 ECR, resultados "very different (even opposite)". p. 129.
  - Hierarquia "is not the same as critical appraisal"; útil para adequação. p. 129-130.
  - Pesos quantitativos por escore "are not usually empirically based". p. 132.
  - Cluster RCT (Box 5.2, Puffer et al.). p. 133-134. Deeks et al.: 194 ferramentas, seis úteis. p. 134.
  - SMS em revisões Campbell de crime, com taxa de resposta, atrito e validade da medida. p. 135.
  - Box 5.5 (EPOC antigo para ITS): ≥ 20 pontos pré com ARIMA ou ≥ 3 pré/pós; completude 80-100%; ≥ 90% de concordância ou kappa ≥ 0,8. p. 139-140.
  - Qualitativa: sem consenso sobre "the best" método; 18 perguntas de Spencer et al.; checklists como transparência, não atalho. p. 151-153.
  - Schulz et al.: ocultação inadequada exagera OR em 41%; sem duplo-cego, 17%. p. 154.
  - Revisões sem apreciação crítica "should not be considered reliable". p. 157.
- Limitações/observações: livro de 2006; critérios EPOC citados estão superados pela versão de 2017.

## schaefer_oqfunciona — Schaefer, Borges & Freitas (2025), proposta O que funciona? (preprint OSF aht4j_v1)
- Arquivo: texto-base no scratchpad (`fontes/oqf_texto_base_schaefer_borges_freitas_2025.txt`).
- O que foi lido: trechos sobre tipos de RS e hierarquia (p. 12, 17), decomposição e validade interna (p. 20), estratégia de avaliação (p. 28), Anexo A (p. 45, título; conteúdo em imagem) e Anexo G (variável de hierarquia, p. 89).
- Pontos usados no capítulo:
  - Nota 10: tipos de RS diferem pela presença de "critérios de elegibilidade focados na qualidade da evidência"; remete ao Anexo A e ao guia do What Works Growth. p. 12.
  - Nota 13: nível mais alto RS e RCT; intermediário quase-experimentais, coorte e caso-controle; mais fraco pré e pós, estudos de caso e opiniões. p. 17.
  - Variável "que mensura o grau de validade interna do trabalho (hierarquia de evidências)" em estudos quantitativos. p. 20.
  - Avaliação para selecionar trabalhos com "características de qualidade mínimas". p. 28.
  - Anexo G, `hieraquia_evidencias`: 0 estudos de caso e opiniões; 1 comparações pré e pós-teste; 2 "estudos de caso controlados"; 3 coorte; 4 quase-experimentais; 5 RCT; 6 RS; "Não considerar" em qualitativas-interpretativistas. p. 89.
- Limitações/observações: outros capítulos citam a mesma variável como p. 90 (página do PDF); aqui uso a página impressa (p. 89). O Anexo A está em imagem.

## schaefer2025proibicao — Schaefer, Borges & Gomes Filho (2025), proibição de celulares (JPPG 1(2):97-113)
- Arquivo: `~/Downloads/zs6h4-osfstorage-archive/6 An†lise de dados/FINAL+-+A+PROIBICAO+DO+USO+DOS+CELULARES.pdf` (página no rodapé).
- O que foi lido: p. 102-105 (seleção, sistematização, efeito) e p. 109 (limitações).
- Pontos usados no capítulo:
  - "appraisal" para selecionar trabalhos com "características mínimas de qualidade"; triagem incluiu estudos empíricos revisados por pares, foco explícito e "descrição metodológica mínima"; 19 + 2 por bola de neve = 21. p. 102.
  - Variáveis metodológicas: "desenho de pesquisa, estratégia de identificação, validade interna". p. 103.
  - "experimental em três casos, seleção em observáveis em quatro casos (diferença em diferenças) e meta-análise em um"; 7 de 8 positivos, 6 significativos; Fisher 65,74; Cooper 2,88; g = 0,22. p. 104.
  - Comparação com a meta-análise de Böttger & Zierer (2024). p. 105.
  - Limitações: heterogeneidade em tipo de banimento, público, foco e "tipo de avaliação (incluindo provas padronizadas, testes aplicados pelos professores"; parte da variabilidade pode decorrer de "diferenças de desenho e implementação". p. 109.
- Limitações/observações: nenhuma avaliação de risco de viés por estudo.

## Slides do curso — Aula 4 (p. 42-52) e Aula 5 (p. 17-30) (schaefer2026aula4, schaefer2026aula5)
- Arquivos: `.../9 Slides/OQF_MAPE_Aula_4_Filtragem_e_Controle_de_Qualidade.pdf`; `.../9 Slides/OQF_MAPE_Aula_5 Decomposição (Data Extraction).pdf` (vistos como imagem; página = PDF).
- Pontos usados no capítulo:
  - Aula 4 p. 43: funil com "Tipos de estudos aceitos" b2, a1, b1, a2; critérios definidos a priori.
  - Aula 4 p. 44-46: triagem por IA no REFIS (Claude 16 de 120; DeepSeek 21; concordância 10). Não usado neste capítulo (tema do cap. 05 e 11).
  - Aula 4 p. 48: fluxo PRISMA do REFIS até corpus final de 21 (as caixas não fecham: 110 resumos + 1 IPEA vs 120 após filtros; 16 − 5 + 9 = 20). Só o total 21 foi usado.
  - Aula 4 p. 49: "Protocolos de adequação metodológica": RoB 2, ROBINS-I, CASP. Aula 5 p. 19: os mesmos mais MMAT. Sem regra de uso nem limiar.
  - Aula 4 p. 50 e Aula 5 p. 26: Quadro 1, tipologia 2 × 2.
  - Aula 5 p. 20: Box 2, hierarquias (Bagshaw & Bellomo 2008, níveis I-V; Petticrew & Roberts 2003, 1-7). Aula 5 p. 21: Box 4, matriz de evidências.
  - Aula 5 p. 27-30: definições de a1, b1, a2 (descritivo, "sem necessariamente estimar efeitos causais") e b2 (RCT, regressão descontínua, DiD, seleção em observáveis).

## schaefer2026ementa — Ementa do curso (2026.1)
- Arquivo: `~/Downloads/zs6h4-osfstorage-archive/Revisão_Sistemática_e_Avaliação_de_Políticas_Públicas___Ementa.pdf`.
- O que foi lido: p. 1 (apresentação) e p. 6 (Aula 4).
- Pontos usados no capítulo: Aula 4 "Filtragem e controle de qualidade": leituras obrigatórias Madaleno & Waights (2015) e Thomas et al. (2003, cap. 2 e 4); complementares Nutley et al. (2013), Al Noman et al. (2024), Daly et al. (2007); exemplos Kopittke & Ramos e García & Saavedra; tarefa "Definição de critérios de qualidade para seleção dos trabalhos". p. 6.

## schaefer2026codigos — arquivos de decomposição do curso (REFIS)
- Arquivos: `~/Downloads/zs6h4-osfstorage-archive/8 Códigos R/quadro_decomposicao_estudos EXEMPLO.xlsx`; `.../8 Códigos R/base_decomposição.xlsx` (lidos com openpyxl).
- Pontos usados no capítulo:
  - Aba `b2_quantitativo`: `estrategia_identificacao` com categorias que incluem `event_study`, `synthetic_control`, `selecao_observaveis`; variáveis com "Tipo de contribuição" = Qualidade: `controle_id`, `n_controles`, `controle_temporal`, `controle_espacial`, `teste_falsificacao` (placebo/falsificação).
  - Aba `b1_qualitativo_expl`: `selecao_casos` ("Qualidade do desenho"), `mecanismo_identificado` ("Qualidade analítica"), `limitacoes` ("Qualidade").
  - Aba `a2_descritivo`: `fonte_dados`, `amostragem` (probabilística; não probabilística; censitária; conveniência).
  - `base_decomposição.xlsx`, aba `Final`: 20 registros; `tipo_publicacao` com grafias variadas: DISSERTAÇÃO 9, Dissertação 1, dissertation 1 (11 dissertações), TESE 1, Nota técnica 1, Monografia 1, artigos 6; `dec` 15 Sim e 5 Não; nenhuma variável de risco de viés.

## Script da prática do Felipe — `~/Desktop/Pensando-o-Direito/R/extracao_dados.R` (lógica do MMAT simplificado)
- O que foi lido: cabeçalho (l. 1-20), constantes e comentário sobre truncamento (l. 76-90), prompt de sistema e início do formulário (l. 128-160), campo 7 (l. 228-252), checagem de completude (l. 338-356). Nenhum segredo lido ou reproduzido.
- Pontos usados no capítulo:
  - Formulário "inspirado no MMAT 2018"; validação humana do formulário artigo a artigo. l. 1-19.
  - Prompt de sistema: avaliação "segundo o Mixed Methods Appraisal Tool (MMAT, versão 2018), seguindo exatamente os critérios e a lógica de aplicabilidade tipológica fornecidos". l. 133-138.
  - Campo 7 "AVALIAÇÃO DE ADEQUAÇÃO METODOLÓGICA (inspirada no MMAT, versão simplificada)": uma pergunta Sim/Não/Parcialmente + justificativa de até três frases, julgada pelo tipo a1/a2/b1/b2. l. 233-251.
  - Com 6000 tokens, "5 de 13 artigos de um tema vieram truncados", perdendo custo e MMAT; checagem do último campo. l. 79-83, 343-348.
- Limitações/observações: usado como caso de erro comum (item global com rótulo MMAT; julgamento por LLM) e de boa prática (checagem de completude).

## boutron2024considering — Cochrane Handbook v6.5, cap. 7 (Boutron et al., atualizado ago. 2022)
- URL: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-07 (HTML baixado e convertido em texto).
- O que foi lido: 7.1-7.1.2, 7.3-7.7, 7.8.5-7.8.6, quadros MECIR.
- Pontos usados no capítulo:
  - Viés = erro sistemático; ≠ imprecisão; ≠ validade externa. 7.1, 7.1.1.
  - Escalas de qualidade: escalas diferentes → conclusões opostas (Jüni 1999); escore somado difícil de interpretar; avaliação "typically specific to a particular result". 7.1.2.
  - MECIR C52 (obrigatório): avaliar resultados da SoF, RoB 2 para ECR. Box 7.1.a.
  - Contatar investigadores com perguntas abertas (exemplo: "What process did you use to assign each participant to an intervention?"). 7.3.1.
  - "independently by at least two people"; regra de desacordo prévia; expertise; treinamento padronizado; piloto "Three to six papers"; não recomenda kappa. 7.3.2. MECIR C53, C54, C55 (obrigatórios).
  - Ferramentas de aprendizado de máquina: confiabilidade no julgamento "slight to moderate" conforme o domínio (Gates 2018). 7.3.2.
  - Tabelas completas disponíveis; forest plot com julgamentos; barras por informação estatística, não por número de estudos. 7.4.
  - MECIR C56 (altamente desejável). 7.5. C57 (altamente desejável) e C58 (obrigatório). 7.6.1.
  - Quatro estratégias (restringir; estratificar; narrativa, desencorajada quando riscos variam; ajuste bayesiano, não encorajado); ponderação por risco não recomendada; ausência de diferença entre estratos ≠ ausência de viés; estratégia descrita no protocolo. 7.6.2.
  - Conflito não financeiro: "an institutional relationship pertinent to the intervention tested" como indício. 7.8.5. MECIR C59 (altamente desejável). 7.8.6.

## higgins2024assessing — Cochrane Handbook v6.5, cap. 8, RoB 2 (atualizado out. 2019)
- URL: .../handbook/current/chapter-08 (HTML convertido).
- O que foi lido: 8.1-8.2.4, 8.4.3-8.5.3.
- Pontos usados no capítulo:
  - RoB 2 avalia um resultado; variantes cluster e crossover no cap. 23. 8.1.
  - Selecionar resultados sem olhar o julgamento provável; foco nos da SoF. 8.2.1.
  - Efeito da atribuição × adesão, especificado no protocolo. 8.2.2.
  - Cinco domínios obrigatórios, "no additional domains"; respostas Y/PY/PN/N/NI; uso restrito de NI; algoritmos propõem julgamento; "risk of material bias"; direção opcional, não chutar; kappa (se calculado) juntando Y/PY e N/PN. 8.2.3, Tabela 8.2.a.
  - Julgamento geral (Tabela 8.2.b). 8.2.4.
  - "no sensible threshold for 'small enough'"; tradição < 5% pequeno, > 20% grande. 8.5.2. Julgamento pelo mecanismo e diferenças entre grupos. 8.5.3.

## higgins2024including — Cochrane Handbook v6.5, cap. 23 (atualizado out. 2019)
- URL: .../handbook/current/chapter-23 (HTML convertido).
- O que foi lido: 23.1.2 e 23.1.3.
- Pontos usados no capítulo:
  - Viés de identificação/recrutamento quando indivíduos entram após alocação dos clusters; domínio específico; desequilíbrio entre participantes sinaliza; poucos clusters → desequilíbrios ao acaso não indicam viés; variante só considera efeito da atribuição. 23.1.2, Tabela 23.1.a.
  - Análise individual sem considerar agrupamento → precisão inadequadamente alta. 23.1.3.

## sterne2024assessing — Cochrane Handbook v6.5, cap. 25, ROBINS-I versão 1 (atualizado out. 2019)
- URL: .../handbook/current/chapter-25 (HTML convertido).
- O que foi lido: 25.3-25.3.5, 25.5 e 25.6 (com Tabelas 25.5.a e 25.6.a).
- Pontos usados no capítulo:
  - Sete domínios e categorias baixo/moderado/grave/crítico da versão 1. 25.3.4-25.3.5.
  - Antes-depois não controlado inclui ITS; uma medida pré e uma pós por participante "will usually be judged to be at serious or critical risk"; eventos externos, pontos pré suficientes, ponto de interrupção escolhido para maximizar efeito, antecipação da política como contaminação do período pré, mudanças administrativas na medida. 25.5.
  - CBA: DiD é "a common analysis of CBA studies"; tendências diferentes, regressão à média, seleção em surveys repetidos. 25.6.

## sterne2025robinsi e riskofbias2025robinsiv2 — ROBINS-I V2 (20 nov. 2025) e página oficial
- URLs: https://www.riskofbias.info/welcome/robins-i-v2 (página baixada em 15/09/2026); PDF oficial pelo link do Google Drive da página (49 p.; hash idêntico à cópia anterior do scratchpad).
- O que foi lido: página inteira; PDF p. 1-20 (esboço, considerações preliminares, avaliação de confundidores, domínio 1 variante A) e p. 45-49 (domínio 6 e julgamento geral); busca textual no documento inteiro por "instrument", "difference", "regression discontinuity", "interrupted" (sem ocorrências de desenhos quase-experimentais).
- Pontos usados no capítulo:
  - Página: V2 revisada postada em 20/11/2025, "still a draft version and is subject to change"; mudanças: algoritmos, respostas "strong/weak", triagem (parte B), queda do domínio de desvios, renumeração dos domínios.
  - Escopo: um resultado de estudo não randomizado; documento "for follow-up (cohort) studies". p. 1, 3.
  - "risk of material bias"; confundidores pré-especificados; target trial; considerações preliminares acordadas antes. p. 3.
  - Seis domínios; sem domínio de desvios (tratado no domínio 1, variante B). p. 3.
  - Julgamentos e interpretação; crítico: "should generally be excluded from evidence syntheses"; algoritmos podem ser sobrepostos; "transparency and reasonableness rather than mechanistic adherence". p. 4.
  - P1 e nota 1: confundidores no nível da pergunta; não trata modificação de efeito. p. 6.
  - Especificar o resultado numérico (ex.: tabela, figura). p. 7.
  - Parte B: B2 (confundimento suficiente sem controle) ou B3 (medida inadequada) → crítico. p. 9.
  - Fontes de informação incluem "'Grey literature' (e.g. unpublished thesis)"; máximo de informação. p. 13.
  - Q1.3 (controle de variáveis pós-intervenção: mediadores, colisores) e Q1.4 (controles negativos). p. 19.
  - Julgamento geral: pior domínio; vários moderados → grave; vários graves → crítico. p. 48-49.

## waddington2017quasi — Waddington et al. (2017), Quasi-experimental study designs series, paper 6
- URL: manuscrito aceito em https://researchonline.lshtm.ac.uk/id/eprint/4647481/ (25 p.; título do manuscrito "Risk of bias assessment in credible quasi-experimental studies"). Metadados da versão publicada conferidos na Crossref (J Clin Epidemiol 89:43-52; oito autores).
- O que foi lido: manuscrito inteiro.
- Pontos usados no capítulo:
  - Quase-experimentos críveis: DiD, IV, ITS, experimentos naturais, RDD. p. 2.
  - "As-if randomized" (NE, IV, RD/ITS) × não randomizados; DiD/FE ajustam só não observáveis invariantes no tempo na unidade de análise; diferença simples/PSM só observáveis. p. 5-7.
  - Falhas de implementação rebaixam abaixo da categoria a priori. p. 7-8. Figura 1 (fluxo de classificação). p. 8.
  - Figura 2: pressupostos por desenho. p. 10.
  - Revisão de ferramentas: critérios insuficientes para confundimento e relato; Sterne et al. (2014) foca ajuste por observáveis. p. 11-13 (Tabela 2, p. 12).
  - Cegamento de avaliadores e analistas "usually is feasible, though seldom used". p. 16.
  - Viés de seleção do resultado provável em avaliações retrospectivas; plano de análise ajuda. p. 16-17.
  - Avaliação por múltiplos revisores e confiabilidade entre avaliadores. p. 17.
  - Perguntas específicas para IV, RDD e DiD. p. 18. Nota 21 (Schochet et al. 2010: quatro valores únicos abaixo e acima do corte). p. 18.
  - Usos: critério de inclusão ou moderador; não ponderar por escores. p. 19. Nota 22: ausência de informação como exclusão deve estar nos critérios. p. 19.

## epoc2017suggested — Cochrane EPOC (2017), Suggested risk of bias criteria
- URL: https://epoc.cochrane.org/sites/epoc.cochrane.org/files/uploads/Resources-for-authors2017/suggested_risk_of_bias_criteria_for_epoc_reviews.pdf (4 p.).
- O que foi lido: inteiro.
- Pontos usados no capítulo:
  - Nove critérios para ECR, não randomizados e CBA; não randomizados e CBA "High risk" em sequência; CBA "High risk" em ocultação. p. 1-2.
  - Dados incompletos: baixo risco se proporção semelhante ou menor que o efeito; "Do not assume 100% follow up unless stated explicitly". p. 2 (e p. 4 para ITS).
  - Sete critérios para ITS; ITS com teste t simples sem considerar tendência "should not be included in the review unless reanalysis is possible"; sazonalidade como outro risco. p. 3-4.

## higgins2024robinse — Higgins et al. (2024), ROBINS-E (Environ Int 186:108602)
- URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC11098530/ (HTML convertido); metadados conferidos na Crossref.
- O que foi lido: resumo; seções 3 (visão geral), 5 (domínios) e 6 (julgamento geral).
- Pontos usados no capítulo:
  - Julgamentos baixo, algumas preocupações, alto, muito alto; direção do viés; ameaça às conclusões. sec. 3.
  - Sete domínios (confundimento; medida da exposição; seleção; intervenções pós-exposição; dados faltantes; medida do desfecho; resultado relatado). sec. 5.
  - Geral por padrão = domínio de maior risco, com possibilidade de sobreposição. sec. 6.

## casp2024qualitative — CASP (2024), Qualitative Studies Checklist
- URL: https://casp-uk.net/casp-checklists/CASP-checklist-qualitative-2024.pdf (6 p.).
- O que foi lido: inteiro.
- Pontos usados no capítulo:
  - "never make assumptions about what the researchers have done"; muitos "Can't tell" → interpretar com cautela. p. 1.
  - Dez perguntas (Seção A validade, B resultados, C utilidade local); Yes/No/Can't tell. p. 2-4.
  - Resumo final: positivos, negativos, desconhecidos. p. 5.

## jbi2024qualitative — JBI (2024), Checklist for Qualitative Research
- URL: https://jbi.global/sites/default/files/2026-05/2024_Checklist_for_Qualitative_Research_1.docx (listado em https://jbi.global/critical-appraisal-tools; baixado com user agent de navegador e convertido com `textutil`).
- O que foi lido: inteiro.
- Pontos usados no capítulo: dez itens (congruências, localização cultural/teórica do pesquisador, influência do pesquisador, vozes dos participantes, ética, conclusões dos dados); campo "Overall appraisal: Include / Exclude / Seek further info"; respostas Yes/No/Unclear.
- Limitações/observações: a ferramenta recomenda citar Porritt et al., "Systematic reviews of qualitative evidence" (JBI Manual 2024); os metadados Crossref do DOI 10.46658/JBIMES-24-02 trazem outra lista de autores (Lockwood et al.). Para não errar a autoria, citei a própria ferramenta (@misc).

## munn2015methodological — Munn et al. (2015) e JBI Checklist for Prevalence Studies
- URL: https://jbi.global/sites/default/files/2026-05/Checklist_for_Prevalence_Studies.docx; metadados do artigo conferidos na Crossref.
- O que foi lido: checklist inteiro (itens e início das explicações).
- Pontos usados no capítulo: nove itens; respostas Yes/No/Unclear/Not applicable; citação recomendada Munn et al. 2015.

## barker2026revised — Barker et al. (2026), JBI tool for analytical cross-sectional studies
- URL: https://jbi.global/sites/default/files/2026-05/Assessment%20of%20Risk%20of%20Bias%20for%20Analytical%20Cross-sectional%20Studies%202026.docx; metadados conferidos na Crossref (JBI Evid Synth 24(3):401-408).
- O que foi lido: ferramenta inteira com explicações das oito perguntas.
- Pontos usados no capítulo:
  - Oito perguntas; categorias validade interna (com domínio de viés), validade de conclusão estatística (Q7) e completude do relato (Q8); julgamento no nível do estudo, do desfecho ou do resultado.
  - Introdução: artigos incluídos devem passar por "rigorous appraisal by two critical appraisers".
- Limitações/observações: a página do JBI lista também uma ferramenta revisada para quase-experimentos (Barker et al. 2024, conforme o próprio arquivo); não usada, porque a especificação do projeto indica ROBINS-I/EPOC para esses desenhos.

## hong2018mmatguide e hong2018mmat — MMAT 2018
- URL: http://mixedmethodsappraisaltoolpublic.pbworks.com/w/file/fetch/127916259/MMAT_2018_criteria-manual_2018-08-01_ENG.pdf (11 p.; página no rodapé); artigo conferido na Crossref (Educ Inf 34(4):285-291).
- O que foi lido: guia inteiro (p. 1-10).
- Pontos usados no capítulo:
  - Para revisões de estudos mistos; só estudos empíricos; duas perguntas de triagem; ao menos dois revisores independentes; "Can't tell" pode levar a relatos companheiros ou contato; "It is discouraged to calculate an overall score"; "Excluding studies with low methodological quality is usually discouraged". p. 1.
  - Checklist com cinco categorias e cinco critérios cada. p. 2.
  - Dados completos: sem ponto de corte; literatura de 80% a 95%; combinar na equipe e aplicar uniformemente. p. 4 (repetido p. 5).
  - Critério 5.5: qualidade de cada componente; "the overall quality of a mixed methods study cannot exceed the quality of its weakest component". p. 7.

## shea2017amstar — Shea et al. (2017), AMSTAR 2 (BMJ 358:j4008)
- URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC5833365/ (HTML convertido).
- O que foi lido: resumo e seções com Box 1, Box 2 e recomendação sobre escore.
- Pontos usados no capítulo: 16 itens; "not intended to generate an overall score"; Box 1, sete domínios críticos (itens 2, 4, 7, 9, 11, 13, 15); Box 2, confiança alta/moderada/baixa/criticamente baixa, esquema "advisory"; "We strongly recommend that individual item ratings are not combined to create an overall score".

## whiting2016robis — Whiting et al. (2016), ROBIS (J Clin Epidemiol 69:225-234)
- URL: PubMed 26092286 (resumo via E-utilities).
- O que foi lido: resumo.
- Pontos usados no capítulo: três fases (relevância opcional; quatro domínios; julgamento do risco); público inclui autores de overviews.
- Limitações/observações: texto completo não lido; só a estrutura foi usada.

## mcguinness2021robvis — McGuinness & Higgins (2021), robvis
- Fontes: metadados na Crossref; README da versão de desenvolvimento (https://raw.githubusercontent.com/mcguinlu/robvis/master/README.md e DESCRIPTION, versão 0.3.0.900); teste local do pacote instalado (robvis 0.3.1, R 4.5.2) em 15/09/2026.
- Pontos usados no capítulo:
  - `rob_traffic_light(data, tool, colour, psize, quiet)` e `rob_summary(data, tool, overall = FALSE, weighted = TRUE, ...)` (argumentos lidos no pacote instalado).
  - `rob_tools()` na 0.3.1: ROB2, ROBINS-I, QUADAS-2, ROB1, ROBINS-I Online; semáforo com `tool = "Generic"` falha (erro "object 'trafficlightplot' not found").
  - README da 0.3.0.900: ROB2, ROB2-Cluster (só semáforo), ROBINS-I, ROBINS-E, QUADAS-2, QUIPS, Generic.
  - Legenda do semáforo ROBINS-I: "D2: Bias due to selection of participants", "D3: Bias in classif..." (ordem da versão 1).
  - `rob_summary()` sem coluna de pesos falha ("Likely that a column detailing weights for each study is missing").

## schunemann2019grade — Schünemann et al. (2019), GRADE guidelines 18
- URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC6692166/ (HTML convertido); metadados na Crossref.
- O que foi lido: seção sobre certeza inicial e Figura 4 com nota.
- Pontos usados no capítulo: sem ROBINS-I, NRS começa em baixa; com ROBINS-I, começa alta e "will generally lead to rating down by at least two levels to low or very low certainty".

## nutley2013counts — Nutley, Powell & Davies (2013), What counts as good evidence?
- URL: https://media.nesta.org.uk/documents/What-Counts-as-Good-Evidence-WEB.pdf (40 p.).
- O que foi lido: capa, sumário e seções 3 a 5 (p. 10-19).
- Pontos usados no capítulo:
  - Box 2 (Bagshaw & Bellomo níveis I-V; Petticrew & Roberts 2003, 1-7) = fonte do slide Aula 5 p. 20; status das RS varia. p. 10.
  - Cinco críticas às hierarquias. p. 11. GRADE: começa pelo desenho e ajusta por limitações, inconsistência, indireção, imprecisão, viés de relato. p. 11-12.
  - Observacionais bem conduzidos subestimados. p. 12. Filtro por hierarquia desperdiça evidência (Pawson: "wasteful of useful evidence"); teoria do programa; recomendação. p. 13-14.
  - Box 3: desafios em política social (poucos experimentos, cegamento difícil). p. 15. Matriz (Box 4) = slide Aula 5 p. 21; RCT inadequado para metade das oito perguntas. p. 15-16.
  - EPPI-Centre "weights of evidence" em três dimensões. p. 16.
- Limitações/observações: texto de provocação. A entrada em references.bib não tem editora (Alliance for Useful Evidence/Nesta, Londres); não editada.

## daly2007hierarchy — Daly et al. (2007), hierarquia para pesquisa qualitativa (J Clin Epidemiol 60(1):43-49)
- URL: PubMed 17161753 (resumo via E-utilities).
- O que foi lido: resumo.
- Pontos usados no capítulo: quatro níveis (estudos de caso único, menos prováveis de produzir boa evidência para a prática; descritivos; conceituais; generalizáveis, melhor evidência).
- Limitações/observações: texto completo não acessado; só a estrutura dos níveis foi usada.

## page2021prisma — Page et al. (2021), PRISMA 2020
- Arquivo: `~/Downloads/zs6h4-osfstorage-archive/10 Materiais complementares/PRISMA_2020_checklist (1).docx` (convertido com `textutil`); metadados na Crossref.
- O que foi lido: checklist inteiro.
- Pontos usados no capítulo: itens 11 (ferramentas, revisores, independência, automação), 13e, 13f, 14, 15, 18, 20a, 20d, 22, 23b, 24c, 27.

## tricco2018prisma — Tricco et al. (2018), PRISMA-ScR
- URL: https://www.prisma-statement.org/s/PRISMA-ScR-Fillable-Checklist_11Sept2019.pdf.
- O que foi lido: itens 12 e 16 do checklist.
- Pontos usados no capítulo: item 12 ("If done, provide a rationale for conducting a critical appraisal..."); item 16 ("If done, present data on critical appraisal...").

## brasil2000lei9964 — Lei nº 9.964/2000 (Refis)
- URL: https://www.planalto.gov.br/ccivil_03/leis/l9964.htm (baixada em 15/09/2026).
- O que foi lido: ementa e art. 2º.
- Pontos usados no capítulo: art. 2º, "O ingresso no Refis dar-se-á por opção da pessoa jurídica".

## Repositório da skill (consulta para alinhar a seção "Na skill")
- Arquivos: `~/Desktop/revisao-sistematica-skill/skills/revisao-sistematica/SKILL.md` (tabela de etapas, l. 45-58), `scripts/rslib/projeto.py` (l. 640-652), `scripts/rslib/triagem_lotes.py` (l. 70-85), `scripts/rslib/ambiente.py` (l. 53).
- Pontos usados: etapa "9 Extração e RoB" com `references/05-qualidade.md`, `agentes/avaliador-rob.md`, portão G7; `robvis` tratado como dependência opcional. A descrição no capítulo segue o plano (Apêndices B e C) e não depende desses detalhes de implementação.

## Fontes consultadas e não usadas, ou não acessadas
- Al Noman et al. (2024), leitura complementar da Aula 4 (`alnoman2024simplifying`): não lida.
- ROBIS e Daly et al.: só resumos.
- Guia completo do RoB 2 em riskofbias.info (perguntas-sinalizadoras literais): não lido; usei o cap. 8 do Handbook.
- Variante ROBINS-I V2 para outros desenhos (ITS, CBA): não existe no site na data de acesso; o documento V2 cobre só estudos de seguimento.
- Nenhuma fonte com perguntas-sinalizadoras próprias para controle sintético, event study, QCA ou rastreamento de processos.
- JBI checklist para evidência textual (política) e para quase-experimentos: baixados e lidos parcialmente, não usados.
