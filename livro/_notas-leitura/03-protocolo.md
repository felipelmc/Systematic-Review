# Notas de leitura: capítulo 03, Protocolo, pré-registro e emendas

Convenções: páginas de slides = número da página do PDF; páginas da proposta OQF = marcadores de página do PDF do preprint (`--- pN ---` no texto-base extraído), que ficam 1 ou 2 à frente da numeração impressa no rodapé; páginas de livros e artigos = numeração impressa. Trechos literais têm até 25 palavras.

## schaefer_oqfunciona — Schaefer, Borges & Freitas (2025), O que funciona? (preprint OSF aht4j_v1)
- Arquivo/URL: texto-base extraído em scratchpad/fontes/oqf_texto_base_schaefer_borges_freitas_2025.txt (não copiado para o repo)
- O que foi lido: p. 8-13 (definição de RS, dimensões, tabela 1), p. 26-30 (protocolo, pré-registro, busca, filtros e avaliação do caso celulares), p. 49-54 (Anexo C)
- Pontos usados no capítulo:
  - "Sistemático" vem do protocolo ex ante para cada etapa — p. 8-9 — "O 'sistemático' na RS provém da adoção de um protocolo ex ante para cada uma dessas etapas"
  - Benefícios: menos viés na escolha dos trabalhos e mais transparência — p. 9
  - Planejamento = pergunta + protocolo (termos, bases, critérios, extração, análise) — p. 10
  - Avaliação por mais de uma pesquisadora — p. 11 — "é necessário que seja realizada, ou validada, por mais de uma pesquisadora"
  - Tabela 1 (passos) com exemplo de filtro "publicados entre 2010 a 2024", português ou inglês, revisados por pares — p. 12-13
  - Pré-registro no OSF como alternativa para transparência, citando Campbell et al. 2021; nota 18 remete ao Anexo C — p. 27
  - PICOC do caso celulares — p. 27
  - Busca por revisões de políticas parecidas (bases, Consensus) e domínio de idiomas — p. 28 — "desde que tenha domínio suficiente no idioma para interpretar corretamente o uso dos termos e os estudos"
  - Literatura cinzenta (IPEA), Portal CAPES — p. 28
  - Filtro temporal pós-2007 (iPhone) "seguindo a literatura" (Campbell et al., 2024) — p. 29
  - Duas pesquisadoras + terceira parte; revisões prévias incluídas por busca manual e usadas para validar; expansão para ensino superior — p. 30 — "expandimos a análise ao incluir trabalhos sobre o ensino superior"
  - Anexo C = template JBI (2025) de manuscrito de revisão de escopo, PCC, "Justify date range and any language limitation", frase-padrão de busca preliminar por revisões — p. 49-54
- Limitações/observações: o Anexo C é template de escopo (PCC), sem campos de risco de viés, medida de efeito ou meta-análise; usado no capítulo como nota "curso e normas".

## schaefer2026aula2 — Schaefer (2026), Aula 2: Definição do protocolo inicial (slides)
- Arquivo/URL: ~/Downloads/zs6h4-osfstorage-archive/9 Slides/OQF MAPE Aula 2.pdf (44 p.)
- O que foi lido: inteiro via pdftotext; p. 34-42 vistas como imagem
- Pontos usados no capítulo:
  - Definição de RS com protocolo ex ante — p. 5 (repetido p. 6)
  - Checklist: links PRISMA e PRISMA-ScR — p. 36
  - Pré-registro: "Ferramentas de pré-registro" com link osf.io/registries/discover — p. 39
  - Exemplo celulares: PICOC (p. 41) e quadro de strings com "Tempo: 2004-2024; Idioma: Português e Inglês" — p. 42
- Limitações/observações: slides com pouco texto; conteúdo sobre protocolo é esquemático.

## schaefer2026aula4 — Schaefer (2026), Aula 4: Filtragem e controle de qualidade (slides, caso REFIS)
- Arquivo/URL: ~/Downloads/zs6h4-osfstorage-archive/9 Slides/OQF_MAPE_Aula_4_Filtragem_e_Controle_de_Qualidade.pdf (52 p.)
- O que foi lido: inteiro via pdftotext, com mapeamento página a página
- Pontos usados no capítulo:
  - Busca exploratória verifica se existem RS, estudos, bases e se a pergunta é respondível — p. 7
  - "O REFIS (Lei 9.964/2000) é o primeiro programa federal de refinanciamento tributário — marco temporal desta RS." — p. 8
  - PICOC REFIS: contexto "Brasil, 2001–2025" — p. 16
  - Pré-registro e protocolo: OSF; PROSPERO "Para revisões sistemáticas de saúde" — p. 19
  - Bases: OpenAlex, SciELO/WoS SciELO, WoS, Scopus, BDTD, IPEA — p. 21
  - Critérios de inclusão (empíricos, REFIS, Brasil, CHS aplicadas, 2001–2025, pt/en/es) — p. 25
  - Critérios de exclusão (normativos, jurisprudência, planejamento tributário sem foco em REFIS, fora do Brasil, antes de 2001) — p. 26
  - Recorte 2001-2025: "o REFIS federal foi criado pela Lei n.º 9.964/2001" — p. 27
  - Protocolo ex ante: pergunta e objetivos, bases e descritores, critérios a priori, estratégia de síntese, pré-registro OSF — p. 29
  - Strings com IA; "Todas as versões testadas registradas para rastreabilidade" — p. 33
  - OpenAlex — 26/04/2026 — p. 35
  - Quadro final: sem Scopus; WoS SciELO inclui "planejamento tributário"; BDTD inclui "tax planning", "planejamento tributário" e filtro "ano (2000 até 2024)" — p. 39
  - Triagem por IA: Claude 16 de 120, DeepSeek 21, interseção 10 — p. 44-46
  - RoB 2, ROBINS-I, CASP como "protocolos de adequação metodológica" — p. 49
- Limitações/observações: inconsistência 2000 (p. 8) vs 2001 (p. 27) no ano da lei; confirmado na fonte oficial que a lei é de 10/04/2000.

## schaefer2026protocolo — Script "3 Protocolo ex ante.R" (curso, pasta 11)
- Arquivo/URL: ~/Downloads/zs6h4-osfstorage-archive/11 C¢digos R - Atualizado e Consolidado/3 Protocolo ex ante.R
- O que foi lido: inteiro (sem chaves de API no arquivo)
- Pontos usados no capítulo:
  - Sete etapas: [1] pergunta com 4 desfechos; [2] PICOC e CMO (mecanismos + e -); [3] descritores PT/EN/ES e bases OpenAlex, Scielo, WoS, Scopus, BDTD, IPEA; [4] inclusão/exclusão, recorte 2001–2025, áreas CHS aplicadas; [5] leitura de títulos e resumos; [6] sistematização (formais, metodológicas, substantivas, resultados, mecanismos); [7] "Meta-análise para sistematização dos efeitos" e "Análise temática para sistematização dos mecanismos"
  - Ausências: registro, emendas, revisores/desempate, RoB, medida de efeito, regra de modelo, critérios de síntese, certeza, plano de IA
- Limitações/observações: o script só gera a figura-tabela do protocolo (DiagrammeR).

## schaefer2026analise — Script "10 Análise de Dados.R" (curso, pasta 11)
- Arquivo/URL: ~/Downloads/zs6h4-osfstorage-archive/11 C¢digos R - Atualizado e Consolidado/10 An†lise de Dados.R (977 linhas)
- O que foi lido: busca dirigida (grep) por pacotes e funções de meta-análise; cabeçalho e bibliotecas
- Pontos usados no capítulo:
  - Carrega tidyverse, openxlsx, tidytext, ggwordcloud, igraph, ggraph, stopwords, here; implementa Fisher (l. 267), Stouffer (l. 277), Winer (l. 288) e Cooper; nenhuma ocorrência de meta, metafor, metagen, rma( ou forest
- Limitações/observações: leitura seletiva, só para verificar a ausência de meta-análise prometida no protocolo.

## schaefer2025proibicao — Schaefer, Borges & Gomes Filho (2025), celulares nas escolas (JPPG)
- Arquivo/URL: ~/Downloads/zs6h4-osfstorage-archive/6 An†lise de dados/FINAL+-+A+PROIBICAO+DO+USO+DOS+CELULARES.pdf
- O que foi lido: p. 97-102 (introdução e método), p. 105 (resultado da meta-análise), p. 109 (limitações)
- Pontos usados no capítulo:
  - PICOC (população estudantes, escolas e redes; intervenção proibição/restrição; comparação com/sem; desfecho desempenho em avaliações padronizadas; contexto global) — p. 100
  - Quadro 1: "Recorte temporal 2004-2024"; "Idioma Português e Inglês" — p. 102
  - Filtro temporal "a partir de 2007, ano do lançamento do Iphone"; triagem incluiu "estudos empíricos revisados por pares" — p. 102
  - Efeito 0,22 "fraco (conforme critérios da literatura)"; difere de Böttger & Zierer porque "não restringimos a coleta a trabalhos sobre o ensino básico" — p. 105
  - Limitações: heterogeneidade em tipo de banimento, público, foco da intervenção, tipo de avaliação — p. 109
- Limitações/observações: não há menção a registro de protocolo.

## carrerarivera2022howto — Carrera-Rivera et al. (2022), How-to conduct a SLR (MethodsX)
- Arquivo/URL: ~/Downloads/zs6h4-osfstorage-archive/2 Pergunta de pesquisa e estruturação do protocolo/1-s2.0-S2215016122002746-main.pdf
- O que foi lido: inteiro (incluindo o checklist do Apêndice A, p. 11, visto como imagem)
- Pontos usados no capítulo:
  - Protocolo como primeiro passo, registro das atividades, opinião de pares, replicabilidade — p. 2 — "Obtaining opinions from peers while developing the protocol, is encouraged"
  - Critérios definidos antes "although these can be adjusted later, if necessary" — p. 3
  - Tabela 4: período (desde que a tecnologia surgiu ou desde revisão anterior), idioma, exclusão de literatura cinzenta, fator de impacto/quartil, acessibilidade — p. 4
  - Formulário de extração pode ser atualizado, mas com cautela (consome tempo) — p. 5
  - Nota de corte na avaliação de qualidade — p. 6 — "A cut-off score should be defined to filter those articles that do not pass the QA."
  - Relatório deve apresentar o protocolo — p. 10
- Limitações/observações: guia de computação; o checklist não tem registro nem plano de emendas; critérios de fator de impacto, cinzenta e acessibilidade usados como contraexemplo.

## campbell2024evidence — Campbell et al. (2024), Evidence for and against banning mobile phones in schools (scoping review)
- Arquivo/URL: ~/Downloads/zs6h4-osfstorage-archive/2 Pergunta de pesquisa e estruturação do protocolo/campbell-et-al-2024-evidence-for-and-against-banning-mobile-phones-in-schools-a-scoping-review.pdf
- O que foi lido: seletivo (resumo, introdução sobre ondas de proibição, método, tabela 2 parcial, síntese, limitações)
- Pontos usados no capítulo:
  - Pré-registro do protocolo no OSF mencionado no resumo — p. 243
  - Primeira onda de proibições (celulares e pagers) no fim dos anos 1980 e início dos 1990 na América do Norte — p. 244
  - Tabela 1: período "2007a to 2023", nota "2007 was the launch of the first iPhone"; idioma inglês — p. 246
  - "The data extraction and synthesis plan were preregistered with the Open Science Framework" (osf.io/aqgfp) — p. 246
  - Buscas "between September 19 to 20, 2021 and were updated May 20 to 22, 2023" — p. 246
  - 22 incluídos; "12 were unpublished" — p. 247
  - Tabela 2 inclui Aloteibi (2022), participantes professores do secundário (N = 248) — p. 248
  - Síntese narrativa "in line with our OSF registration" — p. 251
  - Inclusão de não publicados reconhecida como limitação — p. 257
- Limitações/observações: revisão de escopo; usada como contraponto (comparação registro × artigo).

## campbell2021evidenceosf — Registro OSF aqgfp (Campbell et al., 2021)
- Arquivo/URL: https://osf.io/aqgfp (lido via API: https://api.osf.io/v2/registrations/aqgfp/)
- O que foi lido: metadados e respostas registradas (registration_responses); contribuidores
- Pontos usados no capítulo:
  - date_registered 2021-09-21T07:10; template "OSF Preregistration"; q8 "Registration prior to creation of data"
  - "We will limit our search to studies published in English between 2007 and 2021."
  - Exclusão: "Studies that examine mobile phone related outcomes in subjects other than school students (e.g., parents and/or teachers) will be excluded."
  - Síntese qualitativa planejada; contato com autores com 2 lembretes a cada 10 dias
- Limitações/observações: fuso horário do registro (UTC) não altera a conclusão de que o registro é posterior ao término das buscas relatadas (20/09/2021). Contribuidores no OSF: 8 (Adrian Kelly, coautor do artigo, não consta).

## petticrew2006systematic — Petticrew & Roberts (2006), Systematic Reviews in the Social Sciences
- Arquivo/URL: ~/Downloads/zs6h4-osfstorage-archive/1 Tipos de revisão/guide-of-systematic-reviews-in-social-sciences.pdf (354 p.; página impressa = página do PDF − 18)
- O que foi lido: capítulo 2 (p. 27-56), capítulo 3 (p. 57-74, até 3.5), apêndice 1 (p. 284-286)
- Pontos usados no capítulo:
  - Box 2.2: quando uma nova RS não é apropriada (já existe boa RS, alguém já está fazendo, pergunta vaga/ampla, recursos) — p. 29
  - Box 2.3: perguntas definidas com usuários; usuários comentam protocolos — p. 29-30
  - Tokenismo; ser claro sobre o que é negociável — p. 31 — "efforts to involve users can easily slip into tokenism unless fully thought through"
  - "Never start a systematic review until a clear question (or clear questions) can be framed." — p. 35
  - Começar por RS existentes; atualizar; escrever aos autores — p. 36-38; bases (DARE, Cochrane, Campbell C2-RIPE, REEL) — p. 37
  - PICOC para revisões sociais — p. 44
  - 2.9 Protocolos; Silagy et al.: "68 percent of the protocols they examined had undergone major change" — p. 44-45
  - Mudanças não por "right" answers — p. 45
  - Scoping review pode refinar a pergunta — p. 48
  - Allen & Olkin: média 1.139 h, mediana 1.110 h, amplitude 216-2.518 h (37 meta-análises) — p. 49
  - "draw up a detailed protocol, and have it reviewed" — p. 52
  - Quase-experimentos como melhor evidência disponível; não excluir não controlados a priori sem estudos controlados; "base metal remains base metal" — p. 63-66
  - Apêndice 1: Step 2 steering group aconselha sobre protocolo; Step 3 "Write a protocol and have it reviewed" — p. 285
- Limitações/observações: livro de 2006; exemplos e bases citados estão desatualizados; usado para princípios.

## schaefer2026ementa — Ementa 2026.1
- Arquivo/URL: ~/Downloads/zs6h4-osfstorage-archive/Revisão_Sistemática_e_Avaliação_de_Políticas_Públicas___Ementa.pdf
- O que foi lido: inteiro
- Pontos usados no capítulo:
  - Aula 2 "Definição do protocolo inicial": problema, teoria do programa, frameworks e check-lists; tarefa "Definição do protocolo"; materiais "Pré-registro", "Check-list" — p. 3-4
  - Aula 4 tarefa "Definição de critérios de qualidade para seleção dos trabalhos" — p. 6
  - Avaliação final no formato OQF — p. 13
- Limitações/observações: usada só como contexto.

## moher2015prismap — Moher et al. (2015), PRISMA-P 2015 statement
- Arquivo/URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC4320440/ (baixado e parseado)
- O que foi lido: Background, tabela 1 (PROSPERO × PRISMA-P), tabela 3 (checklist completo) e nota
- Pontos usados no capítulo:
  - "17 numbered items (26 including sub-items)" — tabela 3
  - Item 1a, 1b, 2 ("If registered, provide the name of the registry (e.g., PROSPERO) and registration number"), 3a-5c, 6, 7, 8 (características de estudo e de relato), 9, 10 ("draft of search strategy to be used for at least one electronic database"), 11a-11c, 12, 13, 14 ("state how this information will be used in data synthesis"), 15a-d, 16, 17
  - Item 4: "If the protocol represents an amendment ... identify as such and list changes; otherwise, state plan for documenting important protocol amendments"
  - Nota: "Amendments to a review protocol should be tracked and dated."
  - Background: protocolo reduz arbitrariedade e permite ao leitor identificar desvios "and whether they bias the interpretation of a review results and conclusions"
  - PROSPERO: registro de intenção de RS "with health-related outcomes"; 22 itens obrigatórios e 18 opcionais; lançado em fevereiro de 2011 — tabela 1 e Background
- Limitações/observações: o documento de explicação e elaboração (Shamseer et al., BMJ 2015;350:g7647) não foi acessado (paywall/bloqueio); não citado.

## page2021prisma — Page et al. (2021), PRISMA 2020 statement
- Arquivo/URL: ~/Downloads/zs6h4-osfstorage-archive/10 Materiais complementares/PRISMA_2020_checklist (1).docx e PRISMA_2020_flow_diagram_new_SRs_v1.docx (python-docx / XML)
- O que foi lido: checklist completo (27 itens) e texto do fluxograma
- Pontos usados no capítulo:
  - Item 5, 6 (data da última busca por fonte), 7, 8, 9, 10a ("Specify whether all results that were compatible with each outcome domain in each study were sought ... and if not, the methods used to decide which results to collect"), 11, 12, 13a, 14, 15, 16b, 23c, 24a, 24b, 24c ("Describe and explain any amendments to information provided at registration or in the protocol"), 27
  - Fluxograma: "Records marked as ineligible by automation tools", "Reports not retrieved"; nota sobre separar exclusões humanas e automáticas
- Limitações/observações: CC BY 4.0.

## lasserson2024starting — Lasserson, Thomas & Higgins, Cochrane Handbook v6.5, cap. 1
- Arquivo/URL: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-01 (baixado e parseado)
- O que foi lido: capítulo inteiro (1.1-1.6)
- Pontos usados no capítulo:
  - 1.3: equipe; "Cochrane will not publish a review that is proposed to be undertaken by a single person"; expertise de tema e de método, incluindo estatística
  - 1.3.1-1.3.2: mapear stakeholders; grupos consultivos; incluir vulneráveis e marginalizados
  - 1.5: juízos "should be made as far as possible in ways that do not depend on the findings of the studies included in the review"
  - 1.5: benefícios do protocolo publicado (menos viés dos autores, transparência, menos duplicação, revisão por pares dos métodos, planejamento)
  - 1.5: conhecimento prévio inevitável → metodologistas não especialistas na equipe
  - MECIR C19 (busca sem restrição de idioma/status; tirar filtro de idioma em bases inglesas não substitui buscar outras línguas), C20 (RoB), C21 (síntese), C22 (subgrupos "restrict these in number, and provide rationale for each"), C23 (GRADE; desfechos do SoF escolhidos sem olhar magnitude)
  - 1.5: mudanças "should not be made based on how they affect the outcome"; decisões post hoc "highly susceptible to bias"
- Limitações/observações: citação indicada na página: "last updated August 2021", versão 6.5, Cochrane 2024.

## cumpston2026reporting — Cumpston, Lasserson, Flemyng & Page, Cochrane Handbook v6.5, cap. III
- Arquivo/URL: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-iii (baixado e parseado)
- O que foi lido: III.1-III.3.4.7 e III.3.8 (seletivo)
- Pontos usados no capítulo:
  - III.2: protocolo como registro público; métodos no futuro e "as if a suitably large number of studies will be identified"
  - III.3.4.1: "Authors should describe and explain all amendments to the prespecified methods in the Differences between protocol and review section"
  - III.3.4.2: desenhos por características, não rótulos; não excluir por desfecho não relatado; subconjunto da população
  - III.3.4.3: ao menos um benefício e um dano; agrupamento de medidas e janelas de tempo
  - III.3.4.5: regra de decisão para multiplicidade; medidas específicas de desenhos não randomizados (ITS: nível e inclinação); comparações replicáveis ("PICO for each synthesis"); subgrupos definidos antes ou depois dos resultados; GRADE com limiares e diferença minimamente importante
  - III.3.4.7: relatar envolvimento de consumidores e outros stakeholders; "If review authors did not involve consumers or other stakeholders, this should be stated."
- Limitações/observações: a página cita "last updated July 2026", "version 6.5. Cochrane, 2026"; mantida a citação conforme a página.

## vandenakker2023increasing — van den Akker et al. (2023), Generalized systematic review registration form
- Arquivo/URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC10514995/ (baixado e parseado)
- O que foi lido: inteiro (Background, Instructions, GSRRF-1 a GSRRF-65); apêndice PROSPERO só folheado
- Pontos usados no capítulo:
  - PROSPERO "directly excludes all systematic reviews without health outcomes, systematic reviews that are non-interventional, scoping reviews, evidence maps, and qualitative systematic reviews" — Background
  - Formulário aplicável a qualquer disciplina e tipo de revisão; fallback para formulários especializados — Abstract
  - No OSF todos os itens são obrigatórios; indicar não aplicável com razão — Instructions
  - Desvios transparentes, contingências, registros atualizados — Instructions
  - 65 itens; GSRRF-6 (etapas, com pilotos e "Prereg update"), GSRRF-7 ("only registrations in earlier stages count as preregistrations"), GSRRF-10 (revisões existentes), GSRRF-21-32 (busca), GSRRF-33/34 (triagem humano/computador; campos cegados), GSRRF-44 (extração humano/computador), GSRRF-57 (critérios de inferência, "a minimal effect size of interest")
- Limitações/observações: artigo de 2023; o número de usos citado (68 até maio de 2023) não foi usado.

## cos2026registration — Center for Open Science, OSF Support: Welcome to Registrations & Preregistrations!
- Arquivo/URL: https://help.osf.io/article/158-create-a-preregistration (redireciona para article/330-welcome-to-registrations)
- O que foi lido: página inteira (WebFetch + curl para conferência literal)
- Pontos usados no capítulo:
  - Passos de criação; aprovação pelos admins em 48 h, depois automática "unless submitted to a Community-run Registry"
  - "You can embargo it for up to four years."
  - Update: "The changes should be implemented only to reflect events outside your control or include unexpected anomalies."; justificativa obrigatória; alterar ao menos um campo; "Files cannot be added or removed during a registration update at this time."
  - 13 templates, incluindo Generalized Systematic Review, OSF Preregistration, Open-Ended, Qualitative Preregistration, Secondary Data
- Limitações/observações: página de ajuda sem data; conteúdo pode mudar.

## aloe2024campbell — Aloe et al. (2024), Campbell Standards (MECCIR atualizado)
- Arquivo/URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC11456310/ (baixado e parseado)
- O que foi lido: inteiro (introdução, desenvolvimento, implementação, tabela 1 com as sete seções)
- Pontos usados no capítulo:
  - Itens "mandatory for a new protocol or review to be published in Campbell Systematic Reviews"
  - Seção 1: interesse dos interessados; equidade; efeitos adversos; "Text describing a priori registration of protocol should be included. Deviations ... should be justified"
  - Seção 2(l): período e escopo geográfico
  - Seção 3: buscar literatura cinzenta
  - Seção 4: automação "describe how, which software, including any validation"
  - Seção 5: piloto da codificação; ferramenta de avaliação crítica justificada
  - Seção 6: justificar medida e modelo; REML como bom padrão; dependência; "vote counting is never an accepted method of synthesis" para dados quantitativos de efetividade
  - Seção 7: magnitude em relação à população; exemplo de anos de aprendizagem; não interpretar pela significância
- Limitações/observações: o artigo diz "35 items", mas a contagem das letras na tabela dá 34 (6+6+3+3+5+7+4); o capítulo não cita o número.

## pollock2024scoping — Pollock et al. (2024), JBI Manual, cap. 10 Scoping reviews
- Arquivo/URL: https://jbi-global.atlassian.net/wiki/spaces/MANUAL/pages/355862497 (texto obtido pela API do Confluence)
- O que foi lido: 10.2.2 (protocolo), 10.2.7.1 (piloto de seleção), 10.2.9.2 (piloto de extração)
- Pontos usados no capítulo:
  - Protocolo a priori é requisito do método JBI; reduz decisões ad hoc; desvios justificados — 10.2.2
  - "Currently, PROSPERO does not accept scoping reviews to be registered"; alternativas OSF e FigShare; publicar protocolo não é requisito — 10.2.2
  - Piloto: 25 títulos/resumos; iniciar com ≥ 75% de concordância — 10.2.7.1
  - Piloto de extração: dois a três itens por tipo de fonte — 10.2.9.2
- Limitações/observações: DOI na página (JBIMES-24-06) diverge do Crossref (JBIMES-24-09 resolve para este capítulo); ano "20XX" na citação sugerida.

## campbell2026submit — Campbell Collaboration, How to submit a proposal
- Arquivo/URL: https://www.campbellcollaboration.org/development/how-to-submit-a-proposal/
- O que foi lido: página inteira (WebFetch)
- Pontos usados no capítulo:
  - Três estágios: registro de título, protocolo, revisão/EGM; primeiro passo é o Title Registration Form (PICO), em consulta com stakeholders
- Limitações/observações: prazos entre título e protocolo não constam na página; não usados.

## brasil2000lei9964 — Lei nº 9.964, de 10 de abril de 2000 (Refis)
- Arquivo/URL: https://www.planalto.gov.br/ccivil_03/leis/l9964.htm
- O que foi lido: cabeçalho e art. 1º
- Pontos usados no capítulo:
  - "LEI Nº 9.964, DE 10 DE ABRIL DE 2000"; "Institui o Programa de Recuperação Fiscal – Refis"
- Limitações/observações: também conferida a Lei nº 15.100, de 13 de janeiro de 2025 (celulares), não citada no capítulo.
