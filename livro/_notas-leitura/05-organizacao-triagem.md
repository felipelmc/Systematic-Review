# Notas de leitura: 05-organizacao-triagem

Capítulo: "Organização dos registros, deduplicação e triagem". Notas refeitas em 15/09/2026, com releitura das fontes e reprodução própria dos dados do curso em R (scripts de conferência no scratchpad da sessão, fora do repositório).

Convenções de página:
- Proposta OQF (`schaefer_oqfunciona`): numeração impressa no rodapé = página do PDF − 1 (marcadores `--- pN ---` do texto-base). Mesma convenção dos caps. 01 e 04.
- Slides: número da página do PDF (Aula 4 tem 52 páginas; conferido visualmente, página a página).
- Petticrew e Roberts: página do livro = página do PDF − 18.
- Thomas et al. (2003): numeração impressa do relatório (página do PDF − 6 no cap. 2 e 3).
- Belur et al. (2021): páginas da versão aceita depositada na UCL Discovery (25 p.), não do periódico.

---

## page2021prisma — Page et al. (2021), PRISMA 2020 statement
- Arquivo/URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC8005924/ (BMJ 2021;372:n71); modelo do fluxograma em `~/Downloads/zs6h4-osfstorage-archive/10 Materiais complementares/PRISMA_2020_flow_diagram_new_SRs_v1.docx`
- O que foi lido: checklist (tabela 1), Box 1 (glossário), resumo das mudanças em relação a 2009; texto do .docx do fluxograma
- Pontos usados no capítulo:
  - Item 8: métodos de seleção com número de revisores por registro e por relato, independência e automação — tabela 1 — "including how many reviewers screened each record and each report retrieved, whether they worked independently"
  - Itens 16a e 16b; 24c; 27 — tabela 1
  - Box 1: registro, relato (inclui preprint, dissertação, relatório governamental) e estudo; registros do mesmo relato são duplicatas; relatos "merely similar" são únicos
  - Caixas do modelo (bases e registros): identificados (bases, registros); removidos antes da triagem (duplicatas, marcados como inelegíveis por automação, outros motivos); triados; excluídos; buscados; não recuperados; avaliados; excluídos com motivos; estudos incluídos; relatos dos estudos incluídos — .docx
  - Nota ** do modelo: se houve automação, indicar quantos registros foram excluídos por humano e quantos por ferramenta — .docx
- Limitações/observações: o .docx do curso é o modelo só com bases e registros.

## page2021explanation — Page et al. (2021), PRISMA 2020 E&E
- Arquivo/URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC8005925/ (BMJ 2021;372:n160)
- O que foi lido: item 8 (com Box 3), itens 16a e 16b
- Pontos usados no capítulo:
  - Box 3: triagem única tem risco maior de perder estudos; dupla vai da checagem integral à conferência de amostra ou de todos os excluídos; priorização com eliminação automática tem risco pela incerteza de quando parar
  - Item 8: relatar se registros foram excluídos só por máquina; classificador que elimina antes da triagem vai como "Records marked as ineligible by automation tools"; relatar validação e risco de estudos perdidos; tradução e contato com investigadores
  - Item 16a (elementos essenciais): registros excluídos antes da triagem (duplicatas, classificadores), triados, excluídos, relatos buscados e não recuperáveis, excluídos com motivos principais, estudos e relatos incluídos; indicar exclusões humanas vs automação
  - Item 16b: citar estudos que atendem a maior parte dos critérios e foram excluídos
- Limitações/observações: exemplos de saúde.

## rethlefsen2022prisma — Rethlefsen & Page (2022), perguntas sobre o fluxograma
- Arquivo/URL: Europe PMC, PMC9014944 (J Med Libr Assoc 110(2):253–257; doi 10.5195/jmla.2022.1449)
- O que foi lido: inteiro
- Pontos usados no capítulo:
  - "Reports not retrieved": todos os relatos que não se conseguiu obter, qualquer que seja o motivo (acervo, sem resposta, link quebrado)
  - Diferença entre estudos incluídos e relatos dos estudos incluídos; exemplo de 50 relatos avaliados, 40 excluídos e 8 estudos, sem dizer que dois tinham dois relatos
  - Outros métodos: boa prática é contar todos os registros identificados em cada fonte; se não for viável, relatar o que for
  - (não usado) Google e Google Scholar limitados a 1.000 registros por busca; busca por citação pode ir na coluna 1 ou 2
- Limitações/observações: não trata de onde entram filtros por metadado.

## rethlefsen2021prismas — Rethlefsen et al. (2021), PRISMA-S
- Arquivo/URL: Europe PMC, PMC7839230 (Syst Rev 10:39)
- O que foi lido: checklist e explicação dos itens 15 e 16
- Pontos usados no capítulo:
  - Item 15: total de registros por base e outra fonte
  - Item 16: "Describe the processes and any software used to deduplicate records from multiple database searches and other information sources."

## lefebvre2025searching — Lefebvre et al. (2025), Cochrane Handbook v6.5.1, cap. 4
- Arquivo/URL: https://training.cochrane.org/handbook/current/chapter-04 (capítulo atualizado em março de 2025; cópia de texto da página)
- O que foi lido: 4.4.5, 4.4.6, 4.5 (parte final), 4.6.1 a 4.6.6
- Pontos usados no capítulo:
  - 4.6.1 e C42: estudos, não relatos, são a unidade; "It is wrong to consider multiple reports of the same study as if they are multiple studies"; relatos secundários não se descartam; justificar o primário
  - 4.6.2: critérios para ligar relatos (identificadores, autores, local, detalhes da intervenção, participantes, datas e duração); "detective work"; contatar autores
  - 4.6.3: processo típico; "authors should generally be over-inclusive at this stage"; estudos com dados incompletos em "studies awaiting classification"
  - 4.6.4 e C39: duas pessoas independentes decidem a elegibilidade; T/A em dupla desejável, aceitável uma pessoa; TC em dupla essencial; um critério falho basta; avaliar em ordem de importância e usar o primeiro "no" como motivo; piloto com "six to eight articles"; especialista e não especialista; discussão, arbitragem, "awaiting assessment"
  - C40: não excluir estudos só porque os dados de desfecho não foram reportados de forma utilizável
  - C41: documentar decisões de todos os registros; contagem basta para exclusões de T/A; excluídos listados são os que o leitor esperaria ver
  - 4.6.5: lista de excluídos breve, com motivo principal
  - 4.6.6.1: Covidence e EPPI-Reviewer são "Cochrane-preferred tools"
  - 4.6.6.2: automação reduz a triagem manual em pelo menos 30% e possivelmente mais de 90%, com perda de até 5% de sensibilidade; eliminação automática por aprendizado ativo não recomendada "at the time of writing in mid-2023"; LLMs sem avaliações suficientes em meados de 2023 (este último não usado)
  - 4.4.5 e C35: data só com critério de elegibilidade, por exemplo intervenção disponível só depois de certa data; faixa de datas mais larga porque a versão eletrônica pode ter data anterior; formato não se restringe; comentários podem trazer alerta de retratação; idioma não lido vai para "studies awaiting classification"
  - 4.4.6 e C48: examinar retratações e erratas de novos e já incluídos; publicações podem ter correções, retratações ou expressões de preocupação; "Cochrane holds a policy for managing potentially problematic studies"
- Limitações/observações: manual de intervenções em saúde, aplicado por analogia.

## li2024collecting — Li, Higgins & Deeks (2024), Cochrane Handbook v6.5, cap. 5
- Arquivo/URL: https://training.cochrane.org/handbook/current/chapter-05 (capítulo atualizado em outubro de 2019)
- O que foi lido: 5.2 e 5.2.1; tabela 5.2.a
- Pontos usados no capítulo:
  - Um relato pode descrever mais de um estudo; "it should never be assumed" que há um relato por estudo — 5.2.1
  - Critérios de ligação incluem identificadores de financiamento, local, datas e duração — 5.2.1
  - Resumos de congresso podem gerar dupla contagem se não ligados — tabela 5.2.a (não usado diretamente)

## doi2025handbook — DOI Foundation (2025), DOI Handbook
- Arquivo/URL: https://www.doi.org/doi-handbook/DOIHandbook_2025.pdf (publicação de setembro de 2025)
- O que foi lido: seção 4.3.4 (pp. 37–38)
- Pontos usados no capítulo:
  - Equivalência de DOIs ignora a caixa só no bloco latino básico (A–Z); "10.26321/Á.GUTIÉRREZ…" e "10.26321/á.gutiérrez…" não são equivalentes

## Crossref REST API (verificação empírica, sem entrada .bib)
- URL: https://api.crossref.org (consultas em 15/09/2026)
- Pontos usados:
  - Prefixos: 10.31235, 10.31219 e 10.31222 = Center for Open Science; 10.2139 = Elsevier (SSRN); 10.1101 = Cold Spring Harbor Laboratory (37.213 `journal-article` associados ao prefixo, ex. 10.1101/gr.1239303 da *Genome Research*); 10.21203 = Research Square; 10.20944 = MDPI; 10.48550 = DataCite (arXiv); 10.1590 = FapUNIFESP (SciELO), com 5.082 `posted-content` e 498.011 `journal-article`
  - Par verificado: 10.1590/scielopreprints.5840 ("Indisciplina e repetência escolar: os meandros de uma relação", `posted-content`/preprint, 2023, autores Silva Neto e Silva) com `is-preprint-of` → 10.1590/s1678-4634202652289357por (`journal-article`, *Educação e Pesquisa*, v. 52, 2026, mesmos autores); o registro do artigo tem `relation` vazio
  - DOI retratado 10.1177/1758835919874651: `updated-by` com `type: retraction`, fontes `retraction-watch` e `publisher`; `filter=updates:` devolve o aviso 10.1177/17588359211061903
  - `filter=relation.type:is-preprint-of`: 838.332 registros

## gartlehner2020single — Gartlehner et al. (2020)
- Arquivo/URL: resumo via Europe PMC (doi 10.1016/j.jclinepi.2020.01.005)
- O que foi lido: resumo estruturado
- Pontos usados no capítulo:
  - ECR na plataforma Cochrane Crowd: 280 participantes, 24.942 decisões, 2.000 resumos
  - Triagem única perdeu 13% (sensibilidade 86,6%; IC 95% 80,6–91,2); dupla perdeu 3% (97,5%; IC 95% 95,1–98,8); especificidades 79,2% e 68,7%
  - Triagem única não atende ao padrão esperado; pode servir a revisões rápidas
- Limitações/observações: voluntários de crowd; texto completo não acessado.

## mckeown2021considerations — McKeown & Mir (2021)
- Arquivo/URL: texto completo via Europe PMC (PMC7827976)
- O que foi lido: inteiro
- Pontos usados no capítulo:
  - 3.130 referências (Ovid: MEDLINE 895, Embase 1.672, PsycINFO 449, CENTRAL 114); padrão-ouro manual com 1.238 duplicatas e 1.892 únicas
  - Tabela 3 (acurácia/sensibilidade/especificidade): Ovid 0,97/0,93/1,00; EndNote X9 0,76/0,57/0,89; Mendeley 0,93/0,84/0,99; Zotero 0,80/0,52/0,99; Covidence 0,96/0,90/1,00; Rayyan 0,97/0,96/0,97
  - Falsos positivos: 0 (Ovid), 208 (EndNote), 17 (Mendeley), 20 (Zotero), 2 (Covidence), 52 (Rayyan); pesquisa primária entre eles: 85/208 EndNote, 4/17 Mendeley, 11/20 Zotero, 16/52 Rayyan, 0 Covidence
  - Resumo de congresso e artigo do mesmo estudo não foram tratados como duplicatas
  - Mesclagem em lote no EndNote: "We do not recommend this approach"
  - Limitação: só registros exportados do Ovid
- Limitações/observações: domínio de saúde.

## borissov2022reducing — Borissov et al. (2022), Deduklick
- Arquivo/URL: texto completo via Europe PMC (PMC9382798)
- O que foi lido: resumo, métodos de validação, tabelas 2 e 3
- Pontos usados no capítulo:
  - Normalização, escore de similaridade e regras de especialistas sobre título, autores, periódico, DOI, ano, número, volume e páginas; oito conjuntos
  - Recall médio 99,51% e precisão 100,00% vs 88,65% e 99,95% na deduplicação manual com EndNote
- Limitações/observações: autores ligados à ferramenta (Risklick); o padrão-ouro foi construído com o próprio Deduklick em limiar baixo mais validação manual, o que pode favorecê-lo.

## byrt1993bias — Byrt, Bishop & Carlin (1993)
- Arquivo/URL: resumo via Europe PMC
- O que foi lido: resumo
- Pontos usados no capítulo:
  - Kappa é afetado por viés entre observadores e pela distribuição entre categorias; "it can be misleading to report kappa values alone"
- Limitações/observações: fórmula do PABAK conferida em Chen et al. (2009).

## chen2009measuring — Chen et al. (2009)
- Arquivo/URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC2636838/
- O que foi lido: resumo, tabela 1 e métodos estatísticos
- Pontos usados no capítulo:
  - κ = (I_o − I_e)/(1 − I_e); PABAK = 2I_o − 1
  - Tabela 1: Landis et al. "Provide arbitrarily the range of kappa value to the degree of agreement"

## hallgren2012computing — Hallgren (2012)
- Arquivo/URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC3402032/
- O que foi lido: seções sobre kappa, prevalência e viés, variantes para 3+ codificadores, interpretação
- Pontos usados no capítulo:
  - Faixas de Landis e Koch (0,0–0,2 leve; 0,21–0,40 razoável; 0,41–0,60 moderada; 0,61–0,80 substancial; 0,81–1,0 quase perfeita); "the use of these qualitative cutoffs is debated"
  - Krippendorff: descontar conclusões abaixo de 0,67, tentativas entre 0,67 e 0,80
  - Problema de prevalência baixa o κ; problema de viés o infla; nenhuma variante corrige os dois
  - Fleiss (1971) para amostras diferentes de codificadores por sujeito, inadequado para desenho cruzado; Light (1971): média dos κ por par em desenho cruzado

## mchugh2012interrater — McHugh (2012)
- Arquivo/URL: Europe PMC, PMC3900052 (Biochem Med 22(3):276–282)
- O que foi lido: resumo e seção de interpretação
- Pontos usados no capítulo:
  - A interpretação usual (que a autora atribui a Cohen, com as mesmas faixas) "may be too lenient for health related studies"
  - "any kappa below 0.60 indicates inadequate agreement"; muitos textos recomendam 80% de concordância como mínimo
- Limitações/observações: a autora atribui as faixas a Cohen, não a Landis e Koch.

## landis1977measurement — Landis & Koch (1977)
- Arquivo/URL: não acessado (JSTOR); metadados via Europe PMC e Crossref
- O que foi lido: resumo
- Pontos usados no capítulo: só como origem dos rótulos, com as faixas conferidas em Hallgren (2012) e no script do curso.

## belur2021interrater — Belur, Tompson, Thornton & Simon (2021)
- Arquivo/URL: versão aceita em https://discovery.ucl.ac.uk/10052482/ (PDF "Accepted version of paper July 2018", 25 p.); metadados do periódico na Crossref (Sociol Methods Res 50(2):837–865)
- O que foi lido: inteiro (texto; tabelas não vêm no manuscrito)
- Pontos usados no capítulo:
  - De 100 sínteses de prevenção ao crime, 49 mencionavam concordância; 31 sem estatística; 16 com percentual (em geral 80% como aceitável); 3 com κ; 34 sem número de codificadores; 17 sem dizer como resolveram desacordos — p. 7
  - Três testes com cerca de 100 registros cada, no início, no meio e no fim da triagem — p. 10
  - Criação da categoria "include – maybe/for further discussion" — p. 11; de "Exclude (but relevant for background information)" — p. 12
  - Concordância de 86,8% (1º teste) e 89,2% (2º); decisões de reunião não escritas geraram confusão — p. 12; 95,2% no 3º — p. 13
  - κ caiu de 0,43 para 0,31 enquanto a concordância subia, por codificação assimétrica (quase tudo exclusão) — p. 14
  - Codificadores ficaram mais rígidos ao saber que teriam de buscar e ler os incluídos — p. 16 — "when made aware that they would have to source and read all the included studies they became more stringent"
  - Importância de trilha de auditoria — p. 21
- Limitações/observações: indicado no slide da Aula 5 (p. 34). Páginas são da versão aceita.

## ouzzani2016rayyan — Ouzzani et al. (2016)
- Arquivo/URL: resumo via Europe PMC (PMC5139140)
- O que foi lido: resumo
- Pontos usados no capítulo: aplicativo web gratuito para triagem de títulos e resumos, com sugestões de um modelo de predição e comparação de decisões entre revisores.

## vandeschoot2021open — van de Schoot et al. (2021), ASReview
- Arquivo/URL: https://www.nature.com/articles/s42256-020-00287-7
- O que foi lido: resumo, ciclo de aprendizado ativo, métricas e resultados da simulação
- Pontos usados no capítulo:
  - Ciclo: um registro por vez, rótulo do usuário treina novo modelo, até critério de parada definido pelo usuário
  - WSS: redução percentual de registros a triar em relação à ordem aleatória, a um nível de recall; WSS@95 médio de 83% (67% a 92%) em quatro conjuntos

## crossref2023retraction — Hendricks et al. (2023), anúncio Crossref e Retraction Watch
- Arquivo/URL: https://www.crossref.org/blog/news-crossref-and-retraction-watch/ (doi 10.13003/c23rw1d9)
- O que foi lido: inteiro
- Pontos usados no capítulo: base do Retraction Watch adquirida pela Crossref e aberta; 14 mil retratações na Crossref, 43 mil no Retraction Watch, cerca de 50 mil ao todo; dados via Labs API e repositório git (edição de 10/10/2024).

## crossref2025retractionwatch — Crossref, documentação "Retraction Watch"
- Arquivo/URL: https://www.crossref.org/documentation/retrieve-metadata/retraction-watch/ (atualizada em 19/01/2025)
- O que foi lido: inteira
- Pontos usados no capítulo:
  - Retratações no campo `update-to` da API REST, com `source` `publisher` ou `retraction-watch`; consulta `filter=update-type:retraction`
  - CSV em repositório git atualizado a cada dia útil; colunas incluem OriginalPaperDOI e RetractionNature (Retraction, Correction, Expression of concern, Reinstatement)

## petticrew2006systematic — Petticrew & Roberts (2006)
- Arquivo: `~/Downloads/zs6h4-osfstorage-archive/1 Tipos de revisão/guide-of-systematic-reviews-in-social-sciences.pdf`
- O que foi lido: cap. 4, pp. 83–84 (sensibilidade e especificidade nas ciências sociais), p. 104 (4.16, gestão de referências), pp. 118–121 (triagem); Box 7.x sobre publicação múltipla (p. 234)
- Pontos usados no capítulo:
  - Resumos estruturados e palavras-chave menos comuns nas ciências sociais; informação metodológica pior relatada; buscas de baixa especificidade — pp. 83–84
  - Software bibliográfico ajuda a achar duplicatas, "but more importantly" permite rastrear cada referência — p. 104
  - Dois revisores como boa prática; segundo revisor numa amostra, "perhaps 10 percent"; irrelevantes óbvios por um revisor com amostra dos excluídos conferida — p. 120 — "no babies are being accidentally thrown out with the bathwater"
  - Excluídos não devem ser apagados — p. 120
  - Texto completo por duas pessoas independentes; alguns periódicos pedem kappa — p. 121
- Limitações/observações: livro de 2006.

## thomas2003children — Thomas et al. (2003), EPPI-Centre
- Arquivo: `~/Downloads/zs6h4-osfstorage-archive/4 Filtragem e controle de qualidade/FinalReport-webV2.pdf`
- O que foi lido: sumário; cap. 2 (2.1–2.4, pp. 17–20); 3.1 e figura 3.1 (pp. 27–28); Apêndice A (pp. 133–134); folha de créditos
- Pontos usados no capítulo:
  - (não usado) Restrição a inglês por falta de recursos de tradução — p. 18
  - "Methodological filters for study design were not used, as these reduce the sensitivity of searches" — p. 19
  - Rodadas de exclusão A escopo, B tipo de estudo, C local, D idioma — pp. 133–134
  - Fluxo: 9.947 citações; 1.735 duplicatas; 7.574 excluídas por seis critérios (4.907; 706; 603; 872; 467; 19); 72 de busca manual; 710 potencialmente relevantes; 46 não obtidas a tempo; 664 lidas; 392 excluídas (45; 111; 24; 134; 76; 2); 272 relatos de 193 estudos — p. 27 e fig. 3.1 (p. 28)
  - O texto diz 660 relatos obtidos (94%); a figura, 664 — p. 27 vs p. 28
- Limitações/observações: a entrada de references.bib está incompleta; sugestão no .bib do capítulo.

## schaefer_oqfunciona — Schaefer, Borges & Freitas (2025), preprint OQF
- Arquivo: texto integral no scratchpad (`fontes/oqf_texto_base_schaefer_borges_freitas_2025.txt`)
- O que foi lido: pp. 10–13, 26–30 e Anexo F (pp. 58–59), numeração impressa
- Pontos usados no capítulo:
  - Avaliação "mais subjetiva", realizada ou validada por mais de uma pesquisadora — p. 10
  - Tabela 1 com o exemplo dos celulares: inclusão de artigos revisados por pares de 2010 a 2024, em português ou inglês — pp. 11–12
  - 1.740 documentos (400 PoP, 87 SciELO, 798 Scopus, 455 WoS); WoS com 79 variáveis e PoP com 26; empilhamento no R; duplicatas → 1.517; ano após 2007 (iPhone) → 1.430; tipo → 1.382 — p. 28
  - Dicionário de metodologia (quem não mencionou termos de método no resumo foi excluído) → 790 — pp. 28–29
  - Dicionário substantivo → 741; pelo menos duas pesquisadoras e terceira para desacordos; motivos de exclusão; 19 trabalhos; duas RS por busca manual; "todos os trabalhos que encontramos estavam nas revisões" — p. 29
  - Anexo F: termos de método em EN e PT (inclui "OLS", "causa") — pp. 58–59
- Limitações/observações: não diz quantas pessoas leram os resumos.

## schaefer2025proibicao — Schaefer, Borges & Gomes Filho (2025), celulares (JPPG)
- Arquivo: `~/Downloads/zs6h4-osfstorage-archive/6 An†lise de dados/FINAL+-+A+PROIBICAO+DO+USO+DOS+CELULARES.pdf`
- O que foi lido: pp. 100–103
- Pontos usados no capítulo:
  - Quadro 1: recorte 2004–2024; português e inglês — pp. 101–102
  - 1.740 documentos; três etapas: 1.517, 1.430 (a partir de 2007, iPhone), 1.382 — p. 102
  - Critérios da triagem; 19 trabalhos + 2 por "bola de neve através de citações" = 21 — p. 102
  - Nota 6: estudo sobre celular e direção excluído por não tratar de desempenho escolar — p. 102

## schaefer2026aula4 — Schaefer (2026), slides da Aula 4
- Arquivo: `~/Downloads/zs6h4-osfstorage-archive/9 Slides/OQF_MAPE_Aula_4_Filtragem_e_Controle_de_Qualidade.pdf` (52 p.)
- O que foi lido: inteiro, visualmente (pp. 1–52)
- Pontos usados no capítulo:
  - REFIS (Lei 9.964/2000) como marco — p. 8; recorte 2001–2025 com "Lei n.º 9.964/2001" — p. 27 (e PICOC "Brasil, 2001–2025", p. 16)
  - Rayyan e Covidence para triagem colaborativa — p. 22; rastreabilidade e reprodutibilidade da busca por pacotes — p. 23
  - Critérios de inclusão — p. 25; exclusão (normativos, só jurisprudência, planejamento tributário sem REFIS, fora do Brasil, antes de 2001) — p. 26
  - Resumo das bases: WoS 3, WoS SciELO 21, SciELO 0, BDTD 158, OpenAlex 4, IPEA 4, total 190 — p. 39
  - Funil: Identificação → Triagem (duplicatas, idioma, período) → "Elegibilidade" = leitura de título e resumo → Incluídos; ferramenta de triagem "R" — p. 43
  - IA: Claude 16 de 120; DeepSeek 21; ChatGPT 0 ("não identificou resumos"); concordância 10; "Demais: triagem manual — 14 ficaram, 14 em revisão" — p. 44
  - Prompt com "O que você quer" e "O que você não quer", campos "Exemplo" vazios e pedido "diga quantos trabalhos permanecem (a) e quais são eles (b)" — p. 45
  - "Concordância (Claude ∩ DeepSeek): 10 trabalhos — incluídos automaticamente"; "14 incluídos, 14 em revisão" — p. 46
  - Fluxograma: 186 + IPEA 4 "não incluídos na deduplicação formal"; 184; 182; 181; 120 (61 por tipo e método); caixa de IA; "110 resumos + 1 IPEA → 15 incluídos · 14 em dúvida", 81 excluídos; 30 textos completos (15 + 14 + 1 IPEA); bola de neve +9; "16 aprovados − 5 excluídos + 9 novos"; "4 não respondiam + 1 não localizado"; corpus final 21 — p. 48

## schaefer2026aula5 — Schaefer (2026), slides da Aula 5
- Arquivo: `~/Downloads/zs6h4-osfstorage-archive/9 Slides/OQF_MAPE_Aula_5 Decomposição (Data Extraction).pdf`
- O que foi lido: pp. 30–36, visualmente
- Pontos usados no capítulo: p. 34, "Validação", indica Belur et al. (doi 10.1177/0049124118799372). As demais páginas (b2, Tally, AIDE) são de extração.

## schaefer2026codigos — Schaefer (2026), códigos R e dados do REFIS
- Arquivos: `11 Códigos R - Atualizado e Consolidado/5 Junção Base de Dados.R` e `8 Validação Filtragem - IA_Manual.R`; `11 C¢digos R - Atualizado e Consolidado/6 Filtragem inicial.R`, `7 Filtragem Metodol¢gica Substantiva.R`, `9 PRISMA.R`; dados em `8 C¢digos R/` (`rs_dados_brutos.xlsx`, `rs_dados_limpos.xlsx`, `rs_dados_verificar.xlsx`, `rs_dados_verificar2.xlsx`, `rs_dados_verificar3.xlsx`, `screening_resultado.xlsx`, `deepseek_text_20260426_06109e.txt`)
- O que foi lido: scripts inteiros; dados reproduzidos em R com a lógica dos scripts (dicionário copiado do script 6, `dictionary()` trocado por `list()`)
- Pontos usados no capítulo:
  - Script 5: 13 colunas; `autores` calculado e descartado no `select`; `palavras_chave` do OpenAlex = `primary_topic.display_name`; BDTD com `palavras_chave = NA`, `n_autores = 1`, `pais = "Brasil"` e `doi = NA`; IPEA fora da junção
  - Script 6: dedup por DOI em minúsculas sem prefixo, senão título sem pontuação, `distinct` mantém a primeira ocorrência; `ano >= 2001`; lista fechada de idiomas (comentário: remove "POLONES" "por precaução"); tipos a excluir incluem "other" e "report"; dicionário aplicado a resumo, título e palavras-chave, com termos e texto sem pontuação e alternância por substring (`str_detect`); campo vazio vira 0; filtro `metodo == 1`
  - Script 7: `id_rs = row_number()` após os filtros ("para joins por posição"); junção de Claude e DeepSeek por título normalizado; consenso "Ambas incluem / Ambas excluem / Divergência / Sem par"
  - Script 8: âncora humana = `id_rs` na lista confirmada, resto 0; `irr::kappa2` por par e `kappam.fleiss` nas linhas completas com três avaliadores; rótulos (pior que o acaso < 0; leve < 0,20; razoável < 0,40; moderado < 0,60; substancial < 0,80; quase perfeito)
  - Script 9: números digitados em DiagrammeR e em metagear (a versão metagear põe 120 como "title and abstract screened" e 64 excluídos por ano, idioma, tipo e método)
  - Reprodução (R, 15/09/2026): 186 registros (Teses/Dissertações 158, SciELO 21, OpenAlex 4, WoS 3); 168 sem DOI; 0 sem resumo; 158 sem palavras-chave; dedup remove 2 (WoS "BONETTI BB", DOI `…ID40757`, título em caixa alta × OpenAlex "Brigitti Brunocilla Bonetti", `…id40757`; OpenAlex × BDTD "A renúncia dos benefícios…", 2020); ano: 2 teses de 2000 sobre planejamento tributário; idioma: 1 "POLONES" com título e resumo em português; tipo: 0; dicionário: 120 passam (lista idêntica a `rs_dados_limpos.xlsx`), 61 excluídos (54 teses, 6 SciELO, 1 WoS)
  - "sem" como substring em 46 dos 181; como palavra isolada em 19; só dentro de palavras em 27; 17 passam só por "sem"; "ols" em 10 (7 registros contêm "bolsa"; 3 com "ols" como palavra; contextos "tools", "controls", "desembolsado", "pols"); "causa" em 10 ("causados", "causar", "causa jurídica"); "cause" em "because"
  - Com fronteira de palavra passam 98; com siglas (sem, ols, rct, rdd, hlm, pca, 2sls, qca) só em maiúsculas, 94; ignorando sigla em texto todo em maiúsculas, 90
  - 99 dos 181 resumos inteiramente em maiúsculas (96 teses, 3 WoS); os 11 registros com "SEM" em maiúsculas estão todos entre eles
  - 13 dos 61 excluídos têm REFIS, parcelamento, recuperação fiscal ou tax installment no título, entre eles "TAX INSTALLMENT IN BRAZIL: WHO BENEFITS?" (WoS, 2023), "A INFLUÊNCIA DO REFIS 2009 NA INADIMPLÊNCIA…" (2014) e "EFICÁCIA DO REFIS NA RECUPERAÇÃO DA DÍVIDA ATIVA NO MUNICÍPIO DE FORTALEZA" (2020)
  - Claude: 120 linhas, 16 INCLUIR e 104 EXCLUIR; DeepSeek: 21 linhas, 6 marcadas no campo foco como excluídas (IDs 15, 17–21)
  - 4 linhas do DeepSeek não casam por título: ID 3 (título sem o final "DURANTE O PERÍODO 2013/2018"), ID 4 ("POLÍCIAS" no lugar de "POLÍTICAS"), ID 17 (sem subtítulo), ID 21 (truncado com reticências); IDs 3 e 4 eram inclusões
  - Consenso: 103 sem par, 10 ambas incluem, 4 ambas excluem, 3 divergências
  - `rs_dados_verificar.xlsx`: `conferencia_manual` igual ao consenso (10 INCLUIR, 4 EXCLUIR, NA no resto); `rs_dados_verificar2.xlsx`: acrescenta 3 DÚVIDA (divergências) e 7 EXCLUIR (sem par); `rs_dados_verificar3.xlsx`: 28 registros, 14 INCLUIR (os 10 do consenso e 4 sem par) e 14 DÚVIDA (3 divergências e 11 sem par), com 13 dos 14 em DÚVIDA excluídos pelo Claude
- Limitações/observações: `rs_dados_verificacao_manual.xlsx`, usado no script 8, não está no arquivo; kappas do curso não reproduzidos. Script antigo com chave de API não foi aberto.

## brasil2000lei9964 — Lei nº 9.964/2000
- URL: https://www.planalto.gov.br/ccivil_03/leis/l9964.htm
- Pontos usados: "LEI Nº 9.964, DE 10 DE ABRIL DE 2000", conversão da MPv nº 2.004-6, institui o Refis.

## Projeto Legal-Acre (sem entrada .bib)
- Arquivos: `~/Desktop/Legal-Acre/revisao-sistematica/README.md`; `02-triagem/prompts/v1.md`; `02-triagem/prompts/v2.md`; contagens de `output/RS_triagem_v2.xlsx` e `RS_consolidado.xlsx` (só a coluna `concordancia`)
- O que foi lido: README e prompts inteiros
- Pontos usados no capítulo:
  - Quatro filtros sequenciais antes da triagem (deduplicação, ano ≥ 2005, tipo, menção a metodologia) — README
  - Critérios em sequência, exclusão no primeiro que falha, "registre qual critério falhou"; resposta JSON só com "decisao" e "justificativa" — v1 e v2
  - v1 → v2: 3A de "mencionar" para "analisar empiricamente"; caso Loarie et al. (2009) — v1, "Por que foi substituído"; VÁLIDO/INVÁLIDO — v2
  - Cabeçalho da v2: "Critérios 1, 2 e 3B — sem alteração", mas o 3B passou de "deve mencionar" para "deve avaliar" desfechos; cabeçalho lista GPT-4o, Claude Sonnet 4.6 e Gemini 2.5 Pro, enquanto o README fala em cinco modelos
  - Critério 2 aceita "meta-análise, revisão sistemática quantitativa"
  - 357 de entrada; concordância: 174 UNANIME_EXCLUIR, 120 DIVERGENTE, 63 UNANIME_INCLUIR; divergentes lidos por um revisor cada (60, 30, 30); 131 incluídos (63 + 68); duplicata código 91 = 90 achada pela flag — README e planilhas
- Limitações/observações: `.env` e notebook não abertos.

## Projeto BR-Congress-Preferences (sem entrada .bib)
- Arquivos: `~/Desktop/BR-Congress-Preferences/scoping-review/README.md`; `code/utils_screening.py`
- O que foi lido: inteiros (sem abrir `.env`)
- Pontos usados no capítulo:
  - 5 dos 35 PDFs baixados eram o mesmo estudo sob dois registros OpenAlex — README
  - Resposta JSON só com "decision" e "justification"; `NO_DATA` só quando título e resumo faltam, e aí a decisão final é "Do not include"; sem opção de incerto; prompt "intentionally narrow"; fallback por palavra-chave ("EXCLUDE" no texto) quando o JSON falha; árbitro `gpt-4o`, do mesmo provedor do revisor A, recebe as duas decisões e justificativas — utils_screening.py
  - 2.202 recuperados, 2.199 triados, 52 incluídos, 2,0% de divergência, sem etapa humana — README (não usado diretamente)

## Projeto Pensando-o-Direito (sem entrada .bib)
- Arquivo: `~/Desktop/Pensando-o-Direito/CLAUDE.md`
- O que foi lido: inteiro
- Pontos usados no capítulo:
  - 13 pares de duplicatas entre temas: 127 trabalhos distintos, não 140; documentos chegaram a divergir ("4 pares / 136")
  - Funil por eixo: dedup (DOI normalizado, título quando falta DOI) → corte de ano → menção a metodologia no resumo (dicionário PT/EN/ES)
  - Eixos 3 e 4: DUVIDA/ERRO decididos por `claude-sonnet-5`; se ele não decide, vira EXCLUIR; planilhas "validação manual" sem validação manual
  - (não usados) filtro temático cortou de 140 para 9; `erro_api` no log faria artigo sumir na retomada; match de título estrito para recuperar DOI
- Limitações/observações: scripts R e `.env` não abertos.

## Skill `revisao-sistematica` (repositório em desenvolvimento, sem entrada .bib)
- Arquivos: `~/Desktop/revisao-sistematica-skill/skills/revisao-sistematica/scripts/rs.py --help` e subcomandos; cabeçalho de `rslib/dedup.py`; trechos de `rslib/filtrar.py` e `rslib/prisma.py`; `rslib/esquema.py` (PREFIXOS_PREPRINT)
- Pontos usados no capítulo: nomes de comandos e opções (`importar`, `dedup` com limiares 95/85 e `--revisar`, `filtrar --config --ancoras`, `triagem preparar|mesclar|consolidar|override|api`, `validar amostrar|elusao|calcular|estabilidade`, `textos para-baixar|inventario|elegibilidade|ligar-relatos`, `prisma --manual`, `init --parcial triagem`); regras R1–R5, versão, bloqueios e janela de ano (1, ou 3 quando um lado é preprint); filtros "etiquetar" por padrão e `sem_dado` para campo ausente; PRISMA com filtros excluídos na caixa de automação e quebra por filtro.
- Limitações/observações: `PREFIXOS_PREPRINT` inclui 10.1101 (que também tem artigos de periódico) e não inclui 10.1590 (SciELO Preprints); codebooks e templates ainda não existem.

## Plano (Apêndices A, B e C)
- Arquivo: `/Users/felipelmc/.claude/plans/cara-o-seguinte-jaunty-zebra.md`
- O que foi lido: PLANO FINAL §1–§4; Apêndices A, B e C
- Pontos usados no capítulo: esquema e proveniência, R1–R5, versões, bloqueios, `dedup_pares.csv` (C3); `decisoes.jsonl` e precedência (C2); invariantes (C2); filtros que etiquetam, exclusão só com protocolo e elusão, sem resumo nunca excluído (B §1, C3); estudo > relato > efeito e RS fora como estudo primário (B §3); limiares de calibração, recall e elusão (B, Validação de IA); G4, G5 e portões moles; subagentes e modo API (§4).
