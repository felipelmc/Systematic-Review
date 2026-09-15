# Notas de leitura: Capítulo 11, IA na revisão sistemática

Registro rastreável das fontes lidas para `metodo/11-ia-na-revisao.qmd` (segunda passada, 15 set. 2026, com conferência de todas as fontes da primeira versão). Páginas: nos PDFs do RAISE e dos slides, página impressa = página do PDF; no preprint OQF, página impressa (a do PDF é +1). Fontes web sem paginação são citadas por item ou seção. Trechos literais com no máximo 25 palavras.

## Correções feitas em relação à primeira versão do capítulo

- RAISE 3, Tabela 2: "revisão de linguagem" é **verificação humana** (p. 16), não "aceitável"; agentes para explorar a literatura são "aceitáveis" fora da recuperação formal (p. 11) e, para recuperar citações, "exploratório/suplementar" (p. 12); extração por LLM está na p. 15; agentes de ponta a ponta são "não aceitáveis" (p. 17).
- RAISE 1: a descrição dos três documentos está na p. 9 e os oito papéis na p. 10 (não p. 8).
- PRISMA-trAIce: o texto do artigo diz 14 itens, mas a Tabela 1 e o repositório listam 17 identificadores; os níveis (obrigatório etc.) estão só no repositório.
- REFIS: os humanos leram 110 resumos (120 menos os 10 da interseção), então a IA não excluiu nada sozinha; o erro está na inclusão automática sem leitura, na âncora do κ e nas contagens.
- F1: RAISE 2 p. 34 diz que o F1 pesa igualmente precisão e sensibilidade e ignora verdadeiros negativos (a p. 11 fala, de modo impreciso, em sensibilidade e especificidade).
- SAFE: a condição é "pelo menos o dobro do número estimado de relevantes (RR_T) triados"; a frase "nenhuma regra isolada basta" não foi encontrada no texto e saiu.
- Acrescentados: Khraisha et al. 2024 (RSM), PRISMA 2020 E&E (itens 8, 9 e 11), modelo de texto de protocolo da declaração conjunta, sinais de parada do RAISE 3, cuidados com cache no teste de estabilidade (RAISE 2).

---

## flemyng2025position: Flemyng et al. (2025), Position statement on AI use in evidence synthesis
- Arquivo/URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC12603384/ (texto integral baixado via API do Europe PMC, `PMC12603384/fullTextXML`).
- O que foi lido: inteiro.
- Pontos usados no capítulo:
  - Quatro mensagens do sumário: responsabilidade final do autor, uso condicionado a demonstrar que não compromete rigor, supervisão humana, relato de todo uso que faz ou sugere julgamentos. Trecho: "can use AI and automation as long as they can demonstrate that it will not compromise the methodological rigor or integrity".
  - Tabela 1 (baseada em RAISE versão 2.1): autor "accountable for the content, methods, and findings"; declarar quando a IA "makes or suggests judgements"; itens a) nome, versão, datas; b) finalidade e partes afetadas; c) justificativa, validação, disponibilização de insumos e saídas, passos de verificação; d) interesses; e) limitações e vieses.
  - Ortografia, gramática e estrutura do manuscrito geralmente não precisam ser listadas, conferindo a política do periódico.
  - Uso de IA como decisão de protocolo que pesa contexto, tolerância a risco e mitigações; pode ser preciso pilotar ou calibrar a IA dentro da revisão, com investimento de tempo e habilidade.
  - Modelo genérico de texto para o protocolo ("We will use [AI system/tool/approach name, version, date]...") adaptado em PT no capítulo.
  - Revisões rápidas: revisor único com "an estimated 13% risk of falsely excluding a relevant study"; IA como segundo revisor pode reduzir o risco.
  - Normas éticas e legais: plágio, proveniência, direitos autorais, confidencialidade, privacidade e proteção de dados.
- Limitações/observações: editorial sem paginação na versão PMC; publicado também no CDSR, JBI Evidence Synthesis e Environmental Evidence.

## thomas2026raise1: Thomas et al. (2026), RAISE 1: recommendations for practice (v3, 13 mar. 2026)
- Arquivo/URL: OSF fwaud, "RAISE 1 - recommendations v.3 OSF.pdf" (32 p.; cópia no scratchpad, não no repositório). Citação sugerida no PDF: "Thomas J, Hair K, Noel-Storr, A. et al.".
- O que foi lido: pp. 1-16.
- Pontos usados no capítulo:
  - Consulta por redes dos organizadores com risco de viés de autosseleção — pp. 8-9.
  - Três documentos (RAISE 1, 2 e 3) — p. 9; meta de virar diretriz de consenso — p. 9; recomendações pressupõem infraestrutura e assinaturas não garantidas em países de renda baixa e média — p. 9.
  - Oito papéis no ecossistema — p. 10; IA responsável não compromete honestidade, rigor, transparência, cuidado e responsabilização — p. 10.
  - Metodologistas devem fixar "minimum empirical benchmarks", como "recall thresholds for screening or inter-rater reliability minima for data extraction" — p. 11.
  - Recomendações 1.1 a 1.7 (responsabilidade; crítica às avaliações; justificar uso; IA não é autora; não fabricar; artigos escritos por IA; chatbot não é base de conhecimento) — pp. 13-14.
  - 1.8 (quando declarar), 1.9 (o que relatar, itens a-d), 1.10 (ética, legal e regulatório) — pp. 14-15.
- Limitações/observações: rascunho em consulta; a numeração dos itens de 1.9 (a-d) difere da declaração conjunta (a-e).

## thomas2026raise2: Thomas et al. (2026), RAISE 2: building and evaluating AI tools (v3)
- Arquivo/URL: OSF fwaud, "RAISE 2 - building and evaluating v.3 OSF.pdf" (44 p.).
- O que foi lido: pp. 1-23 e apêndice de métricas pp. 32-38 (seletivo).
- Pontos usados no capítulo:
  - Buscas devem maximizar recall; ganho de precisão não pode custar recall — p. 5.
  - Agentes: relatórios gerados por plataformas agênticas não devem ser tratados como síntese rigorosa nem base de decisões — p. 8.
  - Box 1: escrever prompts para uma tarefa é construir um modelo "(manually) for your particular task" — p. 8.
  - Divisão treino/validação; em prompts de LLM a proporção pode se inverter, com mais dados para validar — p. 9.
  - Classificador de ECR da Cochrane: 99% de recall exigido por usuários independentes dos desenvolvedores; precisão de 8% — pp. 9-10.
  - Modelos generativos "are designed not to" produzir sempre o mesmo resultado — p. 10.
  - Desenvolvimento do prompt num conjunto de treino; nenhum dado dele avalia desempenho; nota d: erro comum de iterar dentro da revisão e relatar com os mesmos registros — p. 11.
  - Llama 2 com 89,7% dos dados de treino em inglês — p. 11.
  - Validação de IA generativa: rodar a mesma entrada várias vezes; alucinação mesmo com a informação presente — pp. 11-12.
  - Tabela 1: padrão de referência com erros afeta as métricas — p. 12.
  - SWAR com protocolo registrado; validar dentro da revisão quando falta evidência generalizável; pode não ser possível colher a eficiência enquanto se avalia — p. 14.
  - Triagem: sensibilidade "possibly reaching 100%" conforme o uso; ninguém avaliou formalmente o impacto de parar numa proporção prevista — p. 16.
  - Extração e RoB: dupla humana ainda erra; não inferioridade; contaminação por revisões abertas no treino; garantir que a informação está no documento antes de pedir a extração — p. 17.
  - Estabilidade: rodar os mesmos dados em condições idênticas e contar mudanças de categoria; cuidado com respostas de cache — pp. 19-20; conferir que fontes citadas existem e contêm o afirmado — p. 20.
  - F1 ignora verdadeiros negativos e pesa igualmente precisão e sensibilidade; F-beta frequentemente preferido — pp. 34-35.
  - Médias fortes (ex.: 98% de recall) mascaram desempenho pior em conjuntos individuais — p. 38.
- Limitações/observações: rascunho em consulta.

## thomas2026raise3: Thomas et al. (2026), RAISE 3: selecting and using AI tools (v3.1)
- Arquivo/URL: OSF fwaud, "RAISE 3 - selecting and using v.3.1 OSF.pdf" (56 p.).
- O que foi lido: pp. 1-31 (estado das ferramentas, Tabelas 1 e 2, seleção e uso, avaliação de adequação, ética).
- Pontos usados no capítulo:
  - LLMs para termos de busca só exploratórios ou suplementares — p. 4; Elicit recuperou "fewer than 40% of relevant articles" contra 94,5% das buscas tradicionais — p. 4.
  - Critérios de parada em vários conjuntos de dados "largely overconfident"; LLMs promissores com prompts bem construídos e poucos exemplos — p. 5.
  - Extração assistida por LLM pode se aproximar da acurácia humana — p. 6; RobotReviewer com 83% das avaliações aceitas — p. 6; LLM em RoB com checagem humana — p. 7.
  - Síntese não é resumo de texto; LLM não avalia combinabilidade, não padroniza, não pondera, não examina heterogeneidade — p. 7.
  - Tradução automática: desenho traduz bem; desfechos e resultados estatísticos, menos — p. 8.
  - Ferramentas de ponta a ponta: caixa-preta, erros se acumulam; síntese por LLM entre estudos deve ser evitada — p. 9.
  - Tabela 1 (cinco categorias) — pp. 9-10.
  - Tabela 2 (fev. 2026): pergunta e rascunho de protocolo por LLM, verificação humana — p. 11; agentes para explorar literatura "Acceptable for use" mas "should not be used as part of any formal evidence retrieval" — p. 11; estratégia por LLM exploratória — p. 12; recuperação de citações por agentes exploratória — p. 12; tradução de sintaxe por LLM verificação humana — p. 13; deduplicação aceitável — p. 13; triagem priorizada e classificadores supervisionados "Need to validate within review", economia mínima para sensibilidade máxima — p. 13; LLM na triagem validar — p. 14; LLM em RoB validar, risco de alucinação — p. 14; LLM em extração qualitativa e quantitativa validar — p. 15; extração de gráficos verificação humana — p. 15; LLM para sintetizar "Not acceptable for use" — pp. 15-16; código verificação humana — pp. 15-16; análise qualitativa validar — p. 16; certeza por modelos de regras aceitável, humanos julgam — p. 16; rascunho de texto exploratório — p. 16; revisão de linguagem verificação humana — p. 16; resumo em linguagem simples e tradução verificação humana — p. 17; agentes de ponta a ponta "Not acceptable for use" — p. 17.
  - Custo de LLMs; melhores funções para pagantes; segurança de dados — p. 19; PRISMA pede justificar automação com avaliação prévia — p. 19; prompts e versão do modelo registrados, controle de versão e changelog, modelos mudam de forma imprevisível — p. 19.
  - Monitorar e auditar saídas, sobretudo em nova versão; documentar lições aprendidas (a-d) — p. 20.
  - Cinco perguntas-chave e critérios de decisão fixados antes — p. 21; prosseguir, prosseguir com mitigações, não prosseguir — p. 22; sinais de parada a-e — p. 22, f-g — p. 23.
  - Ética: ferramenta não transfere responsabilidade; acordos de processamento e termos de treino; carregar texto protegido pode ser reprodução — p. 29; versões pagas com garantia de não uso para treino, cada versão precisa ser avaliada — p. 31.
- Limitações/observações: rascunho; exemplos majoritariamente de saúde.

## holst2025prismatraice: Holst et al. (2025), PRISMA-trAIce
- Arquivo/URL: texto integral via Europe PMC (`PMC12694947/fullTextXML`); README do repositório https://github.com/cqh4046/PRISMA-trAIce (baixado).
- O que foi lido: artigo inteiro (métodos, Tabela 1, fluxograma, limitações) e README inteiro.
- Pontos usados no capítulo:
  - Construído por síntese e adaptação de diretrizes (CONSORT-AI, SPIRIT-AI, TRIPOD-AI etc.), sem Delphi nem reunião de consenso e sem estudo formal com usuários (seção de limitações).
  - Texto diz "It comprises 14 items", mas a Tabela 1 lista T1, A1, I1, M1-M10, R1, R2, D1, D2 (17 identificadores).
  - M6 inclui prompts completos, parâmetros (temperatura, máximo de tokens, top-p) e refinamento; M8 número de revisores, verificação, discrepâncias, calibração; M9 padrão de referência, métricas, análise de erros, piloto; R1 fluxograma distinguindo decisões de IA e humanas.
  - Fluxograma adaptado distingue ferramentas administrativas por regras (deduplicação) de sistemas avaliativos de IA.
  - README: níveis Mandatory, Highly Recommended, Recommended, Optional por item; plano de registro na EQUATOR e Delphi.
- Limitações/observações: não endossado pelo PRISMA; o capítulo 10 cita "14 itens" (harmonizar).

## moher2026prismatraice: Moher et al. (2026), PRISMA-trAIce: A Name Without Endorsement
- Arquivo/URL: texto integral via Europe PMC (`PMC13484942/fullTextXML`).
- O que foi lido: carta inteira.
- Pontos usados no capítulo:
  - Executivo do PRISMA: "we do not endorse it as a PRISMA checklist", porque os desenvolvedores não seguiram os processos da iniciativa.
  - Membros do Executivo lideram orientação de consenso sobre IA, a ser hospedada no site do PRISMA.
- Limitações/observações: orientação oficial ainda não publicada em set. 2026.

## page2021prisma: Page et al. (2021), PRISMA 2020 statement
- Arquivo/URL: PMC8005924; modelo de fluxograma `~/Downloads/zs6h4-osfstorage-archive/10 Materiais complementares/PRISMA_2020_flow_diagram_new_SRs_v1.docx` (texto extraído do XML).
- O que foi lido: itens 8, 9 e 11 da lista; fluxograma inteiro.
- Pontos usados no capítulo:
  - Itens 8, 9 e 11 pedem "if applicable, details of automation tools used in the process".
  - Fluxograma: "Records marked as ineligible by automation tools"; nota: "indicate how many records were excluded by a human and how many were excluded by automation tools".

## page2021explanation: Page et al. (2021), PRISMA 2020 explanation and elaboration
- Arquivo/URL: PMC (HTML salvo no scratchpad, `prisma_ee.txt`).
- O que foi lido: itens 8, 9 e 11 com Box 3.
- Pontos usados no capítulo:
  - Item 8, Box 3: triagem priorizada com eliminação automática tem risco de excluir estudos pela incerteza sobre quando parar.
  - Item 8, elementos com automação: dizer se registros foram excluídos só por avaliação de máquina ou se a máquina conferiu decisões humanas; versão do classificador externo; para classificador interno, software, versão, uso, treino e validação "to understand the risk of missed studies or incorrect classifications"; regras de parada na triagem priorizada.
  - Item 9: como a ferramenta de extração foi usada e treinada e que validação avaliou o risco de extrações incorretas.
  - Item 11: como a ferramenta de RoB foi usada e treinada, com desempenho e validação interna.

## laignelot2026large: Laignelot et al. (2026), J Clin Epidemiol 194:112221
- Arquivo/URL: resumo estruturado via Europe PMC (PMID 41831731). Texto integral bloqueado.
- O que foi lido: resumo (inclusive resumo em linguagem simples).
- Pontos usados no capítulo: busca até 14 jan. 2025; 63 estudos, 52 com métricas, 148 avaliações, 77% GPT; T/A (n = 78) PPA 0,92 (IQR 0,69-0,98) e NPA 0,89 (0,72-0,95); texto completo (n = 20) PPA 0,93 (0,87-1,00) e NPA 0,92 (0,78-0,97); extração acurácia 0,36-1,00, mediana 0,95 (IQR 0,91-0,97; n = 11); RoB 0,44-0,90, mediana 0,62 (IQR 0,53-0,76; n = 6); modelos posteriores ao GPT-4 melhores; integração exige salvaguardas.
- Limitações/observações: só resumo.

## xie2026performance: Xie et al. (2026), J Evid Based Med e70166
- Arquivo/URL: resumo no PubMed (PMID 42499245, formato MEDLINE) e Europe PMC.
- O que foi lido: resumo.
- Pontos usados no capítulo: busca de 1 jan. 2022 a 11 jun. 2026; 18 estudos (2023-2025); T/A sensibilidade 0,92 (IC 0,81-0,96), especificidade 0,94 (0,90-0,97); texto completo 0,99 (0,95-1,00) em ambas; exemplos ou cadeia de raciocínio 0,95 contra 0,86 (p < 0,01); redução de carga de cerca de 50% a 99%.
- Limitações/observações: literatura médica; volume ainda não atribuído.

## khraisha2024can: Khraisha et al. (2024), Research Synthesis Methods 15(4):616-626
- Arquivo/URL: resumo via Europe PMC (PMID 38484744).
- O que foi lido: resumo.
- Pontos usados no capítulo: estudo pré-registrado, "human-out-of-the-loop", com GPT-4 em T/A, texto completo e extração, literatura revisada por pares e cinzenta, vários idiomas; acurácia parecia equivalente à humana, mas os escores caíram em todas as etapas depois de ajustar para acaso e desbalanceamento; em texto completo com prompts altamente confiáveis, desempenho "more robust, reaching 'human-like' levels".
- Limitações/observações: só resumo; números por tarefa não usados.

## lai2026large: Lai et al. (2026), J Clin Epidemiol 197:112383
- Arquivo/URL: resumo via Europe PMC (PMID 42309363).
- O que foi lido: resumo.
- Pontos usados no capítulo: 229 estudos, 440 tarefas; transparência média 0,52 (DP 0,30); protocolo 0,12; detalhes do modelo 0,30; "locking the test set before prompt optimization ... was not reported in 99.8% of tasks".

## lieberum2025large: Lieberum et al. (2025), J Clin Epidemiol 181:111746
- Arquivo/URL: resumo via Europe PMC (PMID 40021099).
- O que foi lido: resumo.
- Pontos usados no capítulo: 37 artigos; 10 de 13 etapas; busca 41%, seleção 38%, extração 30%; 57% estudos de validação; 54% promissor; aplicações plenamente estabelecidas ou validadas faltam.

## fagerberg2026batch: Fagerberg et al. (2026), Cochrane Evid Synth Methods 4(3):e70082
- Arquivo/URL: resumo via Europe PMC (PMID 41982820; PMC13073229).
- O que foi lido: resumo.
- Pontos usados no capítulo: 790 referências (93 relevantes) de uma revisão Cochrane; lotes de 1 a 790; 10 repetições; GPT-5 falhou em lotes ≥ 400; GPT-5 mini e Gemini 2.5 Flash falharam no lote de 790; Gemini 2.5 Flash com sensibilidade baixa no lote 1; GPT-5 mini 0,88 (lote 200) e 0,48 (lote 400); lote 100: Gemini 2.5 Pro sensibilidade 1,00 e GPT-5 especificidade 0,98.

## chelli2024hallucination: Chelli et al. (2024), JMIR 26:e53164
- Arquivo/URL: resumo via Europe PMC e texto PMC11153973.
- O que foi lido: resumo completo.
- Pontos usados no capítulo: 11 revisões, 33 prompts, 471 referências; precisão 9,4%, 13,4%, 0%; recall 11,9% e 13,7% (Bard nenhum); alucinação 39,6% (55/139), 28,6% (34/119), 91,4% (95/104).

## gartlehner2020single: Gartlehner et al. (2020), J Clin Epidemiol 121:20-28
- Arquivo/URL: resumo via Europe PMC (PMID 31972274).
- O que foi lido: resumo.
- Pontos usados no capítulo: 280 participantes, 24.942 decisões; revisor único perdeu 13% (sensibilidade 86,6%; IC 80,6-91,2%); dupla 97,5% (95,1-98,8%).

## cohen2006reducing: Cohen et al. (2006), JAMIA 13(2):206-219
- Arquivo/URL: PMC1447545 (HTML e imagens das equações M4 e M5 no scratchpad).
- O que foi lido: seção de avaliação e resultados.
- Pontos usados no capítulo: WSS = (TN + FN)/N − (1,0 − R) (eq. 4); WSS@95% = (TN + FN)/N − 0,05 (eq. 5); WSS@95% de 10% tratado como limiar razoável de economia relevante.

## callaghan2020statistical: Callaghan & Müller-Hansen (2020), Syst Rev 9:273
- Arquivo/URL: PMC7700715 (texto integral via Europe PMC).
- O que foi lido: resumo, método e resultados.
- Pontos usados no capítulo: teste hipergeométrico da hipótese de recall abaixo da meta ("We reject the null hypothesis that we achieve a recall of less than 95%..."); redução média de trabalho de 17%; heurística de 50 irrelevantes consecutivos poupou 41% em média e errou a meta em 39% dos casos.

## boetje2024safe: Boetje & van de Schoot (2024), Syst Rev 13:81
- Arquivo/URL: PMC10908130 (texto integral via Europe PMC).
- O que foi lido: resumo e descrição das quatro fases.
- Pontos usados no capítulo: fases (amostra aleatória de treino; aprendizado ativo; outro modelo; checagem de qualidade); regra de parada da fase 2 com quatro condições simultâneas: artigos-chave marcados, pelo menos o dobro de RR_T triados, mínimo de 10% triado, nenhum relevante nos últimos (ex.) 50.

## vandeschoot2021open: van de Schoot et al. (2021), Nat Mach Intell 3:125-133
- Arquivo/URL: resumo via OpenAlex.
- O que foi lido: resumo.
- Pontos usados no capítulo: ASReview, software livre de aprendizado ativo para T/A; simulações indicam revisão muito mais eficiente que a manual.

## schroeder2025large: Schroeder, Jaldi & Zhang (2025), arXiv 2501.11840 v1
- Arquivo/URL: https://arxiv.org/abs/2501.11840v1 (e v2 de 29 jul. 2026, título "AI-Assisted Data Extraction for Systematic Reviews in Education").
- O que foi lido: resumos da v1 e da v2.
- Pontos usados no capítulo: 112 estudos de revisão de escopo publicada; 24 variáveis (9 explícitas, 15 categóricas derivadas); 71,17%, 72,14% e 62,43% de concordância com humanos; necessidade de humano no circuito; AIDE gratuito e aberto.

## cao2025automation: Cao et al. (2025), otto-SR (medRxiv)
- Arquivo/URL: API do medRxiv (versões 1 a 4).
- O que foi lido: resumo da v4.
- Pontos usados no capítulo: fase 1 com 32.357 citações de 5 revisões; sensibilidade 96,7% e especificidade 97,9% contra 81,7% e 98,1% humanos; extração 93,1% contra 79,7%; discrepâncias com dupla revisão humana.
- Limitações/observações: preprint; autores do sistema avaliam o sistema.

## lin2026metapipe: Lin & Yeh (2026), meta-pipe (arXiv 2606.28363)
- Arquivo/URL: https://arxiv.org/abs/2606.28363 (v1, 5 abr. 2026).
- O que foi lido: resumo.
- Pontos usados no capítulo: 10 etapas com Claude, Python, R e Quarto; cinco pontos humanos obrigatórios; "No validation data are reported; this is a system description".

## sampaio2024chatgpt: Sampaio et al. (2024), Rev Sociol Polít 32:e008
- Arquivo/URL: SciELO (HTML integral no scratchpad).
- O que foi lido: inteiro.
- Pontos usados no capítulo: Elicit e Consensus "as mais avançadas", Consensus mostra "estado de consenso" para perguntas de sim ou não (seção II.1); alucinação sintaticamente possível e factualmente falsa (seção I); desempenho superior em inglês (seção II.5); registrar nome, versão, data e horário, prompts e logs (seção III.2); tecnologias adaptadas ao Sul Global (resumo e conclusão).

## futterer2026ai: Fütterer et al. (2026), Learn Individ Differ 126:102849
- Arquivo/URL: resumo via OpenAlex; Crossref (fev. 2026). Texto integral não acessado.
- O que foi lido: resumo.
- Pontos usados no capítulo: de 282 ferramentas compiladas, 7 atenderam padrões de qualidade como transparência e acessibilidade.

## clopper1934use, cohen1960coefficient, landis1977measurement, byrt1993bias, chen2009measuring: estatística
- Arquivo/URL: metadados Crossref conferidos em 15 set. 2026; Chen et al. 2009 no PMC2636838 (primeira passada).
- O que foi lido: metadados; resumo de Chen et al.
- Pontos usados no capítulo: IC exato binomial; κ de Cohen; faixas de Landis-Koch; PABAK = 2p_o − 1; κ e PABAK não medem a mesma coisa em baixa prevalência.
- Limitações/observações: fórmulas padrão; os valores numéricos do capítulo foram calculados (ver abaixo).

## belur2021interrater: Belur et al. (2021), Sociol Methods Res 50(2):837-865
- Arquivo/URL: resumo via OpenAlex; indicado nos slides da Aula 5, p. 34.
- O que foi lido: resumo.
- Pontos usados no capítulo: comportamento de codificação muda entre e dentro de indivíduos ao longo do tempo; testes regulares de IRR.

## brasil2018lgpd: Lei 13.709/2018 (LGPD)
- Arquivo/URL: planalto.gov.br.
- O que foi lido: referência normativa, sem análise de artigos.
- Pontos usados no capítulo: marco a observar quando houver dados pessoais.

## schaefer_oqfunciona: Schaefer, Borges & Freitas (2025), proposta OQF
- Arquivo/URL: scratchpad `fontes/oqf_texto_base_schaefer_borges_freitas_2025.txt`.
- O que foi lido: pp. 26-29 impressas.
- Pontos usados no capítulo: Consensus sugerido para achar revisões de políticas parecidas — p. 27 (nota 20); leitura de resumos subjetiva, ao menos duas pesquisadoras e terceira para discordâncias — p. 29; celulares: 741 registros, 19 trabalhos, 2 RS por busca manual usadas para validar — p. 29.

## schaefer2026aula4: Slides Aula 4 (filtragem e controle de qualidade)
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/9 Slides/OQF_MAPE_Aula_4_Filtragem_e_Controle_de_Qualidade.pdf` (52 p.).
- O que foi lido: pp. 30-48 vistas como imagem (texto do pdftotext ilegível por ligaduras).
- Pontos usados no capítulo:
  - String com mecanismos "Construída com auxílio de IA (Claude Sonnet)" — p. 32.
  - Claude gerou strings; DeepSeek V3 validação cruzada; ChatGPT (GPT 5.3) resultado insatisfatório; Consensus em busca exploratória; versões registradas — p. 33.
  - Filtragem IA: Claude 16 de 120; DeepSeek 21; ChatGPT 0; concordância 10; demais em triagem manual, 14 ficaram e 14 em revisão — p. 44.
  - Prompt com papel, pergunta a/b/c/d, "O que você quer" e "O que você não quer" com espaços para exemplo e pedido "diga quantos trabalhos permanecem (a) e quais são eles (b)" — p. 45.
  - 13,3% e 17,5%; interseção "incluídos automaticamente"; "14 incluídos, 14 em revisão" — p. 46.
  - Fluxograma: 186 → 184 → 182 → 181 → 120 (61 excluídos por tipo e método); triagem por IA (3 modelos); triagem manual de 110 resumos + 1 IPEA → 15 incluídos e 14 em dúvida; 81 excluídos; 30 textos completos (15 + 14 + 1); 16 aprovados − 5 excluídos + 9 bola de neve; corpus final 21 — p. 48.
- Limitações/observações: 14 contra 15 incluídos; 111 − 15 − 14 = 82 ≠ 81; os 10 incluídos automaticamente não aparecem na soma dos 30; 16 − 5 + 9 = 20 ≠ 21.

## schaefer2026aula5: Slides Aula 5 (decomposição)
- Arquivo/URL: `.../9 Slides/OQF_MAPE_Aula_5 Decomposição (Data Extraction).pdf`.
- O que foi lido: pp. 30-36 vistas como imagem.
- Pontos usados no capítulo: formulário Tally — p. 32; AIDE com links para site, vídeo e arXiv 2501.11840 — p. 33; validação por IRR (Belur et al.) — p. 34.

## schaefer2026ementa: Ementa do curso
- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/Revisão_Sistemática_e_Avaliação_de_Políticas_Públicas___Ementa.pdf` (14 p.).
- O que foi lido: pp. 6, 13-14.
- Pontos usados no capítulo: seção "Programas, IA e outras questões" com Fütterer et al. (2026), "A IA vai revisar a bibliografia por nós?", Consensus — p. 13; guias de ferramentas de IA — p. 14; "Maryland Scale - Consensus.ai" — p. 6.

## schaefer2026codigos: Scripts e saídas do curso
- Arquivo/URL: `.../11 Códigos R - Atualizado e Consolidado/8 Validação Filtragem - IA_Manual.R` (274 linhas, sem chaves de API); `.../8 C¢digos R/deepseek_text_20260426_06109e.txt`; `.../8 C¢digos R/screening_resultado.xlsx` (inspecionado com pandas).
- O que foi lido: script e texto inteiros; planilha na estrutura e contagens.
- Pontos usados no capítulo:
  - Âncora humana `dec_bruno = as.integer(id_rs %in% ids_confirmados)`, com `ids_confirmados` = `conferencia_manual == "Sim"` na aba "Final" — linhas 33-36 e 45-49.
  - DeepSeek só no subconjunto com sobreposição (comentário) — linhas 50-52; κ de Fleiss só onde os três responderam — linhas 173-176; rótulos de Landis-Koch — linhas 137-146.
  - Saída do DeepSeek: 21 linhas com ID local 1-21, foco a/b/c/d; linhas 15, 17, 18, 19, 20 e 21 marcadas como excluídas e 10, 11 e 16 como "marginal".
  - Saída do Claude: aba "Screening Completo" com 120 linhas (ID, Título, Decisão, Justificativa; 16 INCLUIR e 104 EXCLUIR) e aba "Trabalhos Incluídos" com 16 linhas; sem `id_rs`, versão, data ou prompt.
  - Nenhum arquivo de prompt no arquivo do curso.

## Projeto Legal-Acre (Felipe): `~/Desktop/Legal-Acre/revisao-sistematica/`
- Arquivos: `README.md`; `02-triagem/prompts/v1.md` e `v2.md`; `03-decomposicao/fichamentos/RELATORIO_FICHAMENTO.md`; `03-decomposicao/fichamentos/_consolidado/saidas/RELATORIO_CONCORDANCIA.md` (o caminho `_consolidado/saidas/` na raiz não existe).
- O que foi lido: README, prompts e relatório de fichamento inteiros; relatório de concordância até a tabela por variável e início das divergências.
- Pontos usados no capítulo:
  - 357 artigos; 5 LLMs (gpt-4o, claude-sonnet-4-6, gemini-3.5-flash, deepseek-reasoner, mistral-large-latest); ERRO/SEM_DADOS ignorados na concordância; 120 divergentes lidos por três humanos (60/30/30); 63 unânimes + 68 manuais = 131; README também diz que o mesmo prompt vai "aos três modelos" (README).
  - v1 → v2: "mencionar" → "analisar empiricamente"; distinção VÁLIDO/INVÁLIDO; Loarie et al. (2009) como falso positivo; critérios em sequência "registre qual critério falhou", mas JSON só com `decisao` e `justificativa`; sem opção "incerto"; cabeçalhos de v1 e v2 listam 3 modelos (v1.md, v2.md).
  - Fichamento: 118 textos, 136 fichas; gate 2.683 citações OK, 0 problemas; 37 itens `PDF_TEXTO_NAO_EXTRAIVEL`; 3 PDFs errados; validação cega de 26 textos (25%): valores 80,6%, estrita 72,8%, desenho 22/26 (RELATORIO_FICHAMENTO).
  - Por dimensão: a1 44,4%; por variável: mecanismo_processo 16,7% (N = 12), coeficiente 66,7% (N = 6), valor_coeficiente_padronizado 33,3%, tipo_trabalho κ 0,828 (RELATORIO_CONCORDANCIA).
- Limitações/observações: projeto privado, citado pelo nome dos arquivos, sem entrada BibTeX.

## Projeto BR-Congress-Preferences (Felipe): `~/Desktop/BR-Congress-Preferences/scoping-review/`
- Arquivos: `README.md`; `data/01screening/report.md`; `code/utils_screening.py` (`.env` não aberto; chaves lidas do ambiente).
- O que foi lido: inteiros.
- Pontos usados no capítulo:
  - 2.199 registros; gpt-4o-mini 35 incluídos, claude-haiku-4-5 66; consenso exclui 2.127, inclui 29; árbitro inclui 23, exclui 20; divergência 43/2.199 (2,0%); 52 incluídos; 0 erros; sem revisão humana (report.md).
  - Árbitro gpt-4o vê as duas decisões e justificativas; "Reviewer A" é sempre a decisão do OpenAI (mesmo provedor do árbitro) — linhas 9-15, 176-182, 252-257, 276; NO_DATA só quando título e resumo faltam, e então "Do not include" — linhas 163-166, 270-271; `temperature=0` — linhas 221, 242; fallback por palavra-chave se o JSON falha — linhas 185-202; prompt manda excluir quando um critério falha claramente e só admite Include/Do not include — linhas 119-130.
  - Taxa de inclusão caiu de cerca de 6% a 2,4% ao se afastar dos mais citados (README).
  - Cálculo próprio (tabela 2×2 reconstruída): p_o 0,9804; p_e 0,9550; κ 0,565; PABAK 0,961; concordância positiva 0,574.

## Projeto Pensando-o-Direito (Felipe): `~/Desktop/Pensando-o-Direito/`
- Arquivos: `CLAUDE.md` (252 linhas); `R/filtragem_ia.R` (607 linhas; chaves só do ambiente).
- O que foi lido: CLAUDE.md linhas 1-25 e 150-252; filtragem_ia.R linhas 1-60 e 260-440.
- Pontos usados no capítulo:
  - Revisão sobre segurança pública na Amazônia Legal (l. 7).
  - Eixo 1: nenhuma linha incluída só porque a IA disse INCLUIR; 116 revisadas no tema Proximidade (l. 181).
  - Eixos 3 e 4: 83 casos DUVIDA/ERRO decididos por claude-sonnet-5; se não decidir, EXCLUIR (l. 183); arquivo "validação manual" sem validação manual (l. 185).
  - `temperature` rejeitado com HTTP 400 em claude-sonnet-5 e claude-opus-5 (l. 187).
  - Filtro temático: árbitro de terceira casa e cego "Revisor A/B" (l. 197-198); corte de 140 para 9 (94%), árbitro SIM em 6 de 6, amostra de 12 excluídos com ao menos um falso negativo provável; segunda opinião orientada a recall que não altera a decisão (l. 204).
  - Checagem de sucesso aceitava resposta truncada; 20 de 45 registros sem custo e MMAT (l. 224); PDF digitalizado exige entrada nativa (l. 228); `erro_api` pulado na retomada (l. 236); teto de 250 mil caracteres: 33 de 128 artigos, cinco com menos de 50% (l. 242); instrução antes de documento de ~108 mil tokens, 8 artigos, seis passadas, 29/29 tags ao inverter (l. 243).
  - `filtragem_ia.R`: árbitro nomeia os modelos (l. 269-283); formato inesperado vira DUVIDA (l. 322-328); resumo vazio vira `classificacao_llm = "EXCLUIR"` com `decidido_por = "sem_resumo"` (l. 356-363).

## Plano (PLANO FINAL §1 e §4; Apêndices A, B e C) e CLI da skill
- Arquivo: `/Users/felipelmc/.claude/plans/cara-o-seguinte-jaunty-zebra.md`; `~/Desktop/revisao-sistematica-skill/skills/revisao-sistematica/scripts/rs.py --help` (subcomandos `triagem preparar|mesclar|consolidar|override|api`, `validar amostrar|elusao|calcular|estabilidade`, `declaracao-ia`, `pendencia`).
- Pontos usados: protocolo A a H e regras de extração (Apêndice B); contrato de triagem por subagentes e API (§4); autopiloto com pendências e marca RASCUNHO NÃO VALIDADO (Contexto e §4); `decisoes.jsonl`, eventos, precedência (C2); `mesclar` com checagem de trecho (C3); salvaguardas de subagentes (C5); aviso de envio a terceiros (C7).

## Cálculos próprios (scipy `beta.ppf`, IC 95% bilateral)
- n mínimo com 0 FN: ln(0,025)/ln(0,90) = 35,01 → 36 (LI 0,9026); 35 dá LI 0,89997.
- Tabela do passo D (n = 15 a 200): LI com 0 FN e máximo de FN que ainda aprova (ex.: 50 → 0 FN, LI 0,929; 54 → 1 FN, LI 0,901; 60 → 1 FN, LI 0,911; 85 → 3 FN, LI 0,9003; 200 → 10 FN, LI 0,910).
- 19/20 → LI 0,751; 59/60 → LI 0,911; 49/50 → LI 0,894; 51/52 → LI 0,897.
- Elusão 0/300 → LS 1,222%; × 1.800 = 22; × 3.412 = 42; × 2.127 = 26; recall compatível 100/122 = 0,82 e 52/78 = 0,67.
- 0,025^(1/30) = 0,884; 0,025^(1/21) = 0,839; 0,025^(1/19) = 0,824.
- Relato ilustrativo (640 registros; VP 61, FN 1, FP 81, VN 497): sensibilidade 0,984 (0,913-1,000); especificidade 0,860 (0,829-0,887); precisão 0,430 (0,347-0,515); κ 0,535; PABAK 0,744.
- Teste de renderização: capítulo renderizado em HTML no scratchpad com references.bib + 11-ia-na-revisao.bib; nenhuma citação sem resolução; só avisos esperados de referências cruzadas a outros capítulos.
