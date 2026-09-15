# Notas de leitura: capítulo 04, Busca da literatura

Notas rastreáveis das fontes usadas em `metodo/04-busca.qmd`. Páginas de PDFs do arquivo do curso seguem a numeração impressa da obra, salvo indicação. Slides: número da página do PDF. Fontes web: seção ou página do documento consultado (acesso em 14-15/09/2026).

Convenção para a proposta OQF (`schaefer_oqfunciona`): o texto-base extraído tem marcadores `--- pNN ---` de página do PDF; a numeração impressa é PDF - 1. Cito a numeração impressa.

---

## rethlefsen2021prismas — Rethlefsen et al. (2021), PRISMA-S

- Arquivo/URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC7839230/ (Systematic Reviews 10:39, DOI 10.1186/s13643-020-01542-z)
- O que foi lido: Tabela 1 (checklist de 16 itens) inteira; explicação dos itens 1, 5, 8, 9, 12, 13, 14; metadados.
- Pontos usados no capítulo:
  - Checklist em 16 itens, em três seções: fontes e métodos (1-7), estratégias (8-13), revisão por pares (14), gestão de registros (15-16). Tabela 1.
  - Item 1: nomear cada base e a plataforma. Trecho: "Name each individual database searched, stating the platform for each."
  - Item 2: busca simultânea em várias bases numa plataforma exige listar todas.
  - Item 4: fontes on-line/impressas navegadas (sites, sumários) e como.
  - Item 5: indicar se referências citadas/citantes foram examinadas e o método; a explicação pede citar os artigos-base.
  - Item 8: estratégias "copied and pasted exactly as run".
  - Item 9: declarar ausência de limites ou descrever limites com justificativa.
  - Item 11: indicar reaproveitamento de estratégias de revisões anteriores.
  - Item 12: métodos de atualização; se a sintaxe mudou, relatar original e atualizada (explicação do item 12).
  - Item 13: data da última busca de cada estratégia.
  - Item 14: descrever revisão por pares da busca; explicação recomenda PRESS.
  - Itens 15 e 16: total de registros por base/fonte; processo e software de deduplicação.
  - Seção inicial: material suplementar deve permitir replicar a busca.
- Limitações/observações: o checklist é CC BY; ainda assim, o capítulo parafraseia.

## mcgowan2016press — McGowan et al. (2016), PRESS 2015 Guideline Statement

- Arquivo/URL: resumo via API OpenAlex (DOI 10.1016/j.jclinepi.2016.01.021); texto completo bloqueado (403 no JCE e na CDA-AMC).
- O que foi lido: resumo completo e metadados (J Clin Epidemiol 75:40-46).
- Pontos usados no capítulo:
  - Seis elementos retidos: tradução da pergunta; operadores booleanos e de proximidade; cabeçalhos de assunto; busca por palavras do texto; ortografia, sintaxe e números de linha; limites e filtros.
  - O sétimo elemento original (tradução para outras bases) foi removido e deixado a critério do buscador.
  - Levantamento com especialistas: revisão por pares depois de preparada a estratégia da base principal (MEDLINE) e antes da tradução para outras bases.
  - Quatro documentos: Evidence-Based Checklist, Recommendations for Librarian Practice, Implementation Strategies, Guideline Assessment Form.
- Limitações/observações: as perguntas detalhadas de cada elemento não foram lidas no original; o capítulo só usa os nomes dos elementos e a recomendação de momento. Registrado em lacunas.

## lefebvre2025searching — Lefebvre et al. (2025), Cochrane Handbook v6.5.1, cap. 4

- Arquivo/URL: https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-04 (última atualização março de 2025)
- O que foi lido: seções 4.1, 4.2.2, 4.3.1.1, 4.3.1.4, 4.3.5, 4.4.1 a 4.4.11 e 4.5 inteiras; 4.6 só títulos (triagem fica no cap. 05).
- Pontos usados no capítulo:
  - 4.2.2: todas as estratégias devem passar por revisão por pares antes de rodar; não é necessário duas pessoas buscarem em paralelo.
  - 4.3.1.1: buscar duas ou mais bases reduz o risco de perder estudos elegíveis; seleção de bases guiada pelo tema.
  - MECIR C19 (obrigatório): planejar com antecedência; não restringir por idioma ou status de publicação; "Removing language restrictions in English language databases is not a good substitute for searching non-English language journals and databases."
  - MECIR C25 (altamente desejável): bases nacionais, regionais e temáticas; LILACS citada como exemplo regional.
  - 4.3.1.4: índices de citação servem para achar estudos semelhantes.
  - MECIR C28 (literatura cinzenta, altamente desejável), C29 (revisões anteriores, altamente desejável), C30 (listas de referências de incluídos e de RS relevantes, obrigatório).
  - 4.4.2: estrutura por conceitos; costuma ser desnecessário buscar todos os elementos da pergunta; comparadores e desfechos são mal descritos em resumos; OR dentro do conceito, AND entre conceitos.
  - MECIR C32: evitar NOT; maximizar sensibilidade com precisão razoável.
  - 4.4.2: para intervenções complexas e saúde pública, opções como buscar só a intervenção, abordagem multi-fios (vários conjuntos de conceitos), buscas iterativas, busca por citação, e usar chatbots como ChatGPT ou Claude para sugerir estruturas.
  - 4.4.3 e Tabela 4.4.a: sensibilidade = a/(a+b); precisão = a/(a+c); leitura de 60-120 resumos por hora (500-1000 em 8 horas).
  - MECIR C33: vocabulário controlado com explosão e termos livres com variantes, siglas, truncamento e proximidade; estratégia é iterativa.
  - 4.4.5: não restringir idioma; restrição de idioma, se justificada, como critério de elegibilidade e não como limite da busca; datas só com justificativa; aplicar faixa de datas mais larga que o período de interesse; não aplicar restrição de formato; preprints são fonte potencial.
  - MECIR C35: justificar restrições de data e formato; datas só quando há restrição de data nos critérios.
  - 4.4.8: PRESS; PRISMA-S item 14; o checklist cobre precisão técnica e interpretação da pergunta.
  - 4.4.9: alertas salvos nas plataformas.
  - 4.4.10 e MECIR C37: rodar de novo todas as fontes se a busca inicial tiver mais de 12 meses (de preferência seis) em relação à publicação; C38 incorporar os estudos novos.
  - 4.4.11: parar quando novos termos não trazem novos relevantes; checar se a busca encontra publicações-chave, mas "It is not enough, however, for the strategy to find only those records" (viés para estudos conhecidos); captura-recaptura e recall relativo; muitas inclusões vindas de busca por citação sugerem que a busca original não foi ótima.
  - 4.5 e MECIR C36: documentar fontes, quando, por quem e com que termos; copiar e colar estratégias exatamente como rodadas, sem redigitar; salvar cópias de páginas web; em buscadores, relatar o número de resultados triados e não o total; narrativa da busca.
- Limitações/observações: foco em ensaios randomizados em saúde; transposição para políticas públicas feita com a guia Campbell.

## lefebvre2024technical — Lefebvre et al. (2024), Technical Supplement ao cap. 4 (v6.5)

- Arquivo/URL: PDF de 121 páginas via https://www.cochrane.org/authors/handbooks-and-manuals/handbook/chapter04-tech-supplonlinepdfv65270924
- O que foi lido: seções 1.1.4 (índices de citação), 1.3.5 (web e Google Scholar), 1.3.6 (ferramentas de citação, trecho), 3.2.3 (mineração de texto, aprendizado de máquina e IA).
- Pontos usados no capítulo:
  - p. 10: Google Scholar limita a 1.000 resultados visíveis e não informa como os seleciona, o que compromete transparência e reprodutibilidade; exportação básica melhorada via Publish or Perish.
  - p. 11: OpenAlex permite busca para frente e para trás; cerca de 250 milhões de trabalhos em junho de 2024; busca para frente não é requisito Cochrane.
  - p. 35: buscadores web; limites de triagem de 100 a 500 resultados já relatados; Google Scholar exige abordagem mais abrangente de triagem.
  - p. 37: citationchaser usa Lens.org.
  - p. 61: mineração de texto ajuda a identificar termos a partir de registros relevantes; não há ferramenta gratuita que automatize a busca em várias bases.
  - p. 63: VOSviewer analisa coocorrência de termos e mostra relações entre temas, útil para montar estratégias de temas complexos (cita Arruda et al. 2022).
  - pp. 64-65: LLMs treinados até certa data; treinados em RS com buscas de má qualidade; ChatGPT pode gerar MeSH incorreto e termos diferentes em momentos diferentes; referências fabricadas ("hallucinations").

## macdonald2024searching — MacDonald et al. (2024), guia Campbell de recuperação de informação

- Arquivo/URL: Europe PMC PMC11386270 (Campbell Systematic Reviews 20(3):e1433, DOI 10.1002/cl2.1433)
- O que foi lido: seções 3.2, 4.2, 4.3, 5.2, 5.3, 6.2-6.10, 9.1-9.2 (inteiras); demais seções só títulos.
- Pontos usados no capítulo:
  - 3.2: literatura de ciências sociais tem menos resumos estruturados e terminologia menos padronizada, exigindo buscas mais sensíveis; processo favorece o Norte Global.
  - 3.2.1: uma base só não é adequada.
  - 4.3.1: literatura cinzenta inclui órgãos governamentais, ONGs, instituições acadêmicas; não há limite fixo de quanto buscar; justificar fontes.
  - 4.3.3: buscadores têm interfaces básicas; restringir a um número pré-definido de resultados (ex.: os primeiros 100) ou parar quando perdem relevância; registrar URL, data, termos e número triado; salvar documentos localmente.
  - 4.3.6: repositórios institucionais úteis para evidência do Sul Global.
  - 5.2: artigos-semente (benchmark) devem ser definidos antes da estratégia, representar a diversidade esperada (disciplina, região, período, desenhos); servem para colher termos e como lista de teste; "Ideally the test set should be retrieved in its entirety across the combined database search results."
  - 5.3.1: atualização se passaram mais de 12 meses (cita MECIR Cochrane); alertas ou reexecução com deduplicação contra o conjunto já triado.
  - 6.3 e 6.10: na maioria das revisões Campbell, dois conceitos principais (população/condição e intervenção); desfecho como terceiro conceito depende da pergunta; evitar muitos conceitos; evitar NOT; considerar proximidade; estratégia substantivamente consistente entre bases e adaptada à sintaxe.
  - 6.4.3: mineração de texto a partir de conjunto de estudos relevantes; ChatGPT e similares "should be used cautiously".
  - 6.5.1: ausência de um termo de qualquer conceito exclui o registro.
  - 6.5.2 e 6.5.3: proximidade dá mais sensibilidade que frase e mais precisão que AND; truncamento e curingas variam por base.
  - 6.5.4: campo Topic da WoS inclui título, resumo e palavras-chave.
  - 6.5.6: evitar comandos de limite das bases; exceção é data; documentar e justificar.
  - 6.8: revisão por pares da busca antes do protocolo ou manuscrito; checklist CC-IRMG.
  - 6.9: regras de parada; recall relativo; saturação em buscas qualitativas.
  - 9.1.1: MECCIR item 3 (citado no guia): buscar múltiplas bases, literatura cinzenta, referências de revisões e incluídos; manter log com data, resultados, base, plataforma e estratégia exata.
  - 9.2: itens de documentação de buscas em sites (nome, URL, data, estratégia, caminho percorrido, filtros, notas, pessoa).

## page2021prisma — Page et al. (2021), PRISMA 2020

- Arquivo/URL: Europe PMC PMC8005924 (BMJ 372:n71)
- O que foi lido: checklist de 27 itens e checklist do resumo.
- Pontos usados no capítulo:
  - Item 6: especificar todas as bases, registros, sites, organizações, listas de referências e outras fontes, com a data da última busca de cada uma.
  - Item 7: estratégias completas de todas as bases, registros e sites, incluindo filtros e limites.
  - Item 16a: resultados da busca e seleção, idealmente com diagrama de fluxo.
  - Resumo, item 4: fontes de informação e data da última busca.

## tricco2018prismascr — Tricco et al. (2018), PRISMA-ScR

- Arquivo/URL: manuscrito aceito em https://eprints.whiterose.ac.uk/id/eprint/136633/ (Ann Intern Med 169(7):467-473)
- O que foi lido: checklist (Apêndice/Tabela), itens 5-9.
- Pontos usados no capítulo:
  - Item 7: descrever todas as fontes (com datas de cobertura, contatos) e a data da busca mais recente.
  - Item 8: estratégia eletrônica completa de pelo menos uma base, com limites, de modo que possa ser repetida.

## hirt2024tarcis — Hirt et al. (2024), TARCiS

- Arquivo/URL: resumo via OpenAlex (BMJ 385:e078384); recomendações via página oficial da Universidade de Basel (https://ub.unibas.ch/en/university-medical-library/tarcis/). Texto do BMJ e medRxiv bloqueados (403).
- O que foi lido: resumo; texto das recomendações 1-10 conforme a página da Universidade de Basel.
- Pontos usados no capítulo:
  - Delphi com 27 especialistas; 10 recomendações e quatro prioridades de pesquisa.
  - Rec. 1: terminologia (busca por citação como termo guarda-chuva; para trás, para frente, cocitados, cocitantes, iterativa; referências-semente).
  - Rec. 2: em temas difíceis de buscar, considerar seriamente busca para trás e para frente como técnicas suplementares.
  - Rec. 3: em temas fáceis com busca muito sensível, não é explicitamente recomendada.
  - Rec. 4: basear em todos os registros incluídos da busca primária.
  - Rec. 5: busca para trás idealmente triando títulos e resumos das referências citadas.
  - Rec. 6: considerar dois índices de citação combinados.
  - Rec. 7: deduplicar antes da triagem.
  - Rec. 8: se encontrar novos elegíveis, considerar nova iteração.
  - Rec. 9: busca por citação isolada não deve ser usada quando se busca completude.
  - Rec. 10: itens de relato (detalhe não lido no original).
- Limitações/observações: recomendação 10 não conferida item a item; o capítulo remete ao PRISMA-S item 5 para o relato.

## hirt2023citation — Hirt et al. (2023), revisão de escopo sobre citation tracking

- Arquivo/URL: resumo via OpenAlex (Research Synthesis Methods 14(3):563-579, DOI 10.1002/jrsm.1635)
- O que foi lido: resumo.
- Pontos usados no capítulo:
  - 47 estudos metodológicos; 96% avaliaram benefício e 96% deles acharam valor agregado; uso de múltiplos índices, iterações e software era raro; terminologia heterogênea.

## bramer2017optimal — Bramer et al. (2017), combinações de bases

- Arquivo/URL: resumo via OpenAlex (Systematic Reviews 6:245)
- O que foi lido: resumo.
- Pontos usados no capítulo:
  - 58 RS publicadas; 1.746 referências relevantes achadas pelas bases e 84 por outros métodos; 16% das incluídas só em uma base; Embase+MEDLINE+WoS Core Collection+Google Scholar teve recall global de 98,3% e 100% em 72% das RS; estimam que 60% das RS publicadas não alcançam 95% de recall.
- Limitações/observações: contexto biomédico; uso no capítulo como referência de ordem de grandeza e do benchmark de 95%, não como norma.

## gusenbauer2020which — Gusenbauer e Haddaway (2020), 28 sistemas de busca

- Arquivo/URL: resumo via OpenAlex (Research Synthesis Methods 11(2):181-217)
- O que foi lido: resumo; e o uso que Lycarião et al. fazem do estudo (pp. 2-3, 7).
- Pontos usados no capítulo:
  - 28 sistemas comparados quanto a precisão, recall e reprodutibilidade de buscas booleanas; só metade recomendável sem ressalvas; Google Scholar inadequado como sistema principal.

## haddaway2015google — Haddaway et al. (2015), Google Scholar e literatura cinzenta

- Arquivo/URL: resumo via OpenAlex (PLoS ONE 10(9):e0138237)
- O que foi lido: resumo.
- Pontos usados no capítulo:
  - Sobreposição moderada/baixa entre WoS e GS com strings semelhantes (10-67%); GS perdeu literatura importante em 5 de 6 estudos de caso; recomendam focar nos primeiros 200 a 300 resultados para cinzenta; não usar GS sozinho.

## boeker2013google — Boeker, Vach e Motschall (2013), GS como substituto

- Arquivo/URL: Europe PMC PMC3840556 (BMC Med Res Methodol 13:131)
- O que foi lido: resumo e seção sobre limitações da interface.
- Pontos usados no capítulo:
  - Campos de busca limitados a 256 caracteres; GS "has no truncation operators"; precisão global de 0,13%; faltam histórico, construtor de busca e exportação em massa.
- Limitações/observações: estudo de 2013; a interface pode ter mudado. O limite atual reportado pelo PoP é de cerca de 250 caracteres.

## harzing2007publish — Harzing, Publish or Perish (manual on-line)

- Arquivo/URL: https://harzing.com/resources/publish-or-perish/manual/about/faq ; https://harzing.com/resources/publish-or-perish/manual/reference/dialogs/preferences-google-scholar ; blog de 10/03/2022 sobre limite de resultados.
- O que foi lido: FAQ (trechos sobre limites, operadores, exportação), preferências do Google Scholar, post de 2022.
- Pontos usados no capítulo:
  - Limites por fonte: Crossref, Google Scholar, OpenAlex, Semantic Scholar e PubMed 1000; Scopus 200; Web of Science 200.
  - Consulta longa demais: o PoP ignora o excedente, empiricamente além de ~250 caracteres.
  - Operadores AND, OR, NOT em maiúsculas.
  - Exportação: BibTeX, EndNote, RIS.
  - Preferências: Google Scholar nunca devolve mais de 1000 resultados e em geral devolve menos; taxa de requisições.
  - PoP 8: menu para restringir o máximo de resultados.
- Limitações/observações: páginas sem data de atualização explícita (exceto o blog).

## openalex2026search — OpenAlex Help Center, Search (e Citations)

- Arquivo/URL: https://help.openalex.org/api/searching/ (atualizada 11/08/2026); https://help.openalex.org/data/works/citations/ (atualizada 08/08/2026); filtros `cites`/`cited_by` via busca na documentação.
- O que foi lido: páginas inteiras (via WebFetch, resumo guiado por perguntas).
- Pontos usados no capítulo:
  - `search` em works cobre título, resumo e texto completo; `.search` como filtro por campo (ex.: `title.search`, `fulltext.search`).
  - AND, OR, NOT em maiúsculas; aspas para frase; `~N` após frase para proximidade; `search.exact` sem stemming; curingas `*` e `?` exigem `search.exact` e pelo menos 3 caracteres antes do curinga.
  - URL limitada a ~4 KB.
  - Resultados ordenados por `relevance_score`.
  - `referenced_works` pode ser mais curto que a lista impressa (referência fora do OpenAlex, falha de correspondência sem DOI); `cites:` retorna quem cita; `cited_by:` retorna quem é citado.
- Limitações/observações: documentação muda com frequência (2025-2026); a WebFetch resume a página. O capítulo recomenda registrar a data da documentação consultada.

## clarivate2026wos — Web of Science Help (Clarivate)

- Arquivo/URL: https://webofscience.zendesk.com/hc/en-us/articles/20016122409105-Search-Operators ; .../25350084904721-Search-Rules ; .../26916258216209-Web-of-Science-Core-Collection-Search-Fields
- O que foi lido: apenas os trechos exibidos pelo buscador (acesso direto bloqueado por 403/Cloudflare).
- Pontos usados no capítulo:
  - Precedência: NEAR/x, SAME, NOT, AND, OR; parênteses para controlar.
  - NEAR/x com distância padrão de 15 palavras.
  - Truncamento à direita exige pelo menos três caracteres antes do curinga.
  - Topic busca título, resumo, palavras-chave do autor e Keywords Plus.
- Limitações/observações: conferido só por trechos; registrado em lacunas. Limites de exportação da WoS não verificados e deixados fora.

## elsevier2026scopus — Scopus Support Center, busca avançada

- Arquivo/URL: https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search
- O que foi lido: página inteira (via WebFetch).
- Pontos usados no capítulo:
  - Precedência: OR, depois W/n e PRE/n, depois AND, depois AND NOT; o Scopus não processa da esquerda para a direita.
  - Aspas retas = frase aproximada (curingas funcionam dentro); chaves = frase exata (curingas viram caracteres literais).
  - Não usar aspas curvas; podem gerar erro de análise da consulta.
  - W/n sem ordem; PRE/n com ordem (confirmado também no trecho do buscador da página "How do I search for a document?").
  - TITLE-ABS-KEY busca título, resumo e palavras-chave.
- Limitações/observações: limites de exportação do Scopus não verificados.

## medeiros2024capesr — capesR (CRAN)

- Arquivo/URL: https://cran.r-project.org/web/packages/capesR/index.html
- O que foi lido: página do pacote.
- Pontos usados no capítulo:
  - Acesso aos dados do Catálogo de Teses e Dissertações da CAPES, anos 1987 a 2022, versão 0.1.0 (19/12/2024); variáveis incluem resumo, área, programa, tipo, idioma.

## ibict2024bdtd — IBICT (2024), nova interface da BDTD

- Arquivo/URL: https://www.gov.br/ibict/pt-br/central-de-conteudos/noticias/2024/janeiro/biblioteca-digital-brasileira-de-teses-e-dissertacoes-bdtd-apresenta-nova-interface-e-funcionalidades-aos-usuarios
- O que foi lido: notícia inteira.
- Pontos usados no capítulo:
  - Cerca de 900 mil teses e dissertações; nova ferramenta de exportação de resultados grandes; busca simples e avançada (31/01/2024).

## szomszor2022overton — Szomszor e Adie (2022), Overton

- Arquivo/URL: resumo via OpenAlex (Quantitative Science Studies 3(3):624-650)
- O que foi lido: resumo.
- Pontos usados no capítulo:
  - Base de documentos de política que registra citações à literatura acadêmica; para saúde, economia, assistência social e meio ambiente há núcleo de documentos com ligações de citação suficientes.

## rada2020epistemonikos — Rada et al. (2020), Epistemonikos

- Arquivo/URL: resumo via OpenAlex (BMC Med Res Methodol 20:286)
- O que foi lido: resumo.
- Pontos usados no capítulo:
  - Triagem de 10 bases; mais de 300 mil RS identificadas em saúde; maior base do tipo.

## haddaway2022citationchaser — Haddaway, Grainger e Gray (2022), citationchaser

- Arquivo/URL: resumo via OpenAlex (Research Synthesis Methods 13(4):533-545)
- O que foi lido: resumo.
- Pontos usados no capítulo:
  - Pacote R e app Shiny para busca por citação para frente e para trás a partir de um conjunto inicial.

## petticrew2006systematic — Petticrew e Roberts (2006), cap. 4

- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/1 Tipos de revisão/guide-of-systematic-reviews-in-social-sciences.pdf`
- O que foi lido: capítulo 4 inteiro (pp. 79-124).
- Pontos usados no capítulo:
  - p. 80: em revisão sobre habitação, só cerca de um terço dos estudos relevantes veio de bases; o restante de contatos, bibliografias e especialistas.
  - p. 82, Box 4.1: termos para avaliações não clínicas de efetividade (quase-experimento, experimento natural, séries temporais interrompidas, antes e depois controlado, avaliação de impacto, descontinuidade de regressão, propensity score).
  - pp. 81-83, Box 4.2: sensibilidade e "specificity", esta definida como proporção de recuperados que são relevantes (equivale a precisão; alerta terminológico). Exemplo: 97/100 relevantes em 200 registros.
  - p. 84: revisão sobre novas estradas triou mais de 23.000 títulos e resumos para chegar a 32 estudos; buscas em ciências sociais tendem a menor especificidade.
  - p. 89: estratégia iterativa de Hawker et al., refinando termos a partir de estudos já achados e do modo como foram indexados.
  - pp. 90-92: literatura cinzenta e bases como PolicyFile (Banco Mundial, RAND).
  - p. 96: GAO como fonte de avaliações de programas federais dos EUA.
  - pp. 98-99: busca por citação ("pearl growing"); pode aumentar em cerca de um quarto as referências; trabalhos recentes demoram a ser citados.
  - pp. 100-101: sem regras rígidas de parada; Chilcott et al. pararam quando rendimento caiu abaixo de 1%, não apropriado para efetividade; checar se a estratégia recupera estudos-chave identificados em revisões existentes; títulos pouco informativos nas ciências sociais.
  - pp. 101-102: nenhuma busca está completa sem as bibliografias de revisões-chave.
  - p. 102: registrar termos, filtros, datas e anos cobertos.
  - pp. 102-103: datas de corte decididas logicamente e declaradas no protocolo; em atualizações, sobrepor período.
  - pp. 112-113, Box 4.11: EconLit, RePEc, Banco Mundial.
  - p. 118: em revisões de educação, 26% dos estudos só por busca manual e 57% só por bases comerciais.
- Limitações/observações: obra de 2006; muitas URLs e bases citadas estão desatualizadas.

## whitehead2016searching — Whitehead e Maude (2016), cap. 4

- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/3 Busca do material/5e-Schneider_2302_Chapter_4_main.pdf` (prova não corrigida da 5ª ed., pp. 53-72)
- O que foi lido: inteiro.
- Pontos usados no capítulo:
  - p. 60: procurar revisões existentes antes de começar; usar buscas posteriores ao período coberto.
  - p. 60: MeSH (NLM) e vocabulário próprio do CINAHL; truncamento amplia a busca; cautela: "cerv*" também traz coluna cervical.
  - pp. 60-61: PICO/T usado "em reverso" para derivar palavras-chave.
  - p. 61: filtros das bases excluem artigos úteis; abordagem passo a passo.
  - pp. 61-62: relatar bases, palavras-chave, período, critérios, MeSH, booleanos, truncamento e filtros.
  - p. 62, Box 4.3: exemplo de histórico de busca com contagens por passo; OR soma, AND restringe.
  - pp. 62-63: busca manual em sumários de periódicos e listas de referências, especialmente para periódicos nacionais ou não anglófonos.
  - p. 63: conferir erros na importação para gerenciadores de referência.
- Limitações/observações: a entrada `whitehead2013searching` de `references.bib` corresponde à 4ª ed. (2013, pp. 35-53). O PDF lido é da 5ª ed. (2016, pp. 53-68 de texto). Criei `whitehead2016searching` no .bib do capítulo; o coordenador decide se substitui a chave antiga.

## lycariao2025comunidade — Lycarião et al. (2025), sistemas de busca das RSL lusófonas

- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/3 Busca do material/93993 (1).pdf` (AtoZ 14:1-11, DOI 10.5380/atoz.v14.93993)
- O que foi lido: inteiro.
- Pontos usados no capítulo:
  - p. 2: escolha dos sistemas não é trivial e requer testes sucessivos (cita Gusenbauer e Haddaway 2020).
  - p. 3: GS avaliado negativamente por Gusenbauer e Haddaway (sem campos para booleanos, relevância concentrada na primeira página); SciELO recupera dados de mais de 1.800 revistas; segundo Melo et al. (2021), pouco mais de 20% da produção dos PPGs de Comunicação e Informação está na WoS.
  - p. 4: busca em 11/11/2021 por "revisão sistemática" em português: WoS 0, SciELO 18, Scopus 37, DOAJ 69 (124).
  - p. 5, Tabela 2: das 49 RSL, DOAJ 32, Scopus 9, SciELO 8, WoS 0.
  - p. 6, Tabela 3: 238 menções a sistemas de busca, média de 4,8 por artigo; WoS a mais usada (24; 10,08%); Scopus 23; Portal de Periódicos CAPES 7; Google Acadêmico 7; BDTD 4; Catálogo CAPES 2.
  - p. 7: DOAJ não permite buscas precisas e replicáveis com booleanos; SciELO e Scopus superiores nesse aspecto; necessidade de sistemas complementares quando a comunidade não está nos "principais".
  - p. 8, nota 9: bases que dão visibilidade à literatura lusófona em Humanidades e não usadas: Redalyc, Dialnet, "Latin Index", Redib, Sumários.org.
- Limitações/observações: o texto (p. 6) cita BRAPCI 5,88% e "SciELO com 5,04", mas a Tabela 3 mostra "SRAPCI" 5,88%, "IBAPCI" 5,04% e SciELO 4,20% (inconsistência interna ou erro de extração). O capítulo não usa esses números. A entrada existente em `references.bib` não tem volume, páginas e DOI.

## vaneck2010software — van Eck e Waltman (2010), VOSviewer

- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/3 Busca do material/s11192-009-0146-3.pdf`
- O que foi lido: seletivo (pp. 523-531 e conclusão).
- Pontos usados no capítulo:
  - p. 524: VOSviewer constrói mapas de autores ou periódicos por cocitação e de palavras-chave por coocorrência.
  - pp. 526-527: visões de rótulo, densidade, densidade de clusters e dispersão.
  - p. 531: similaridade por "association strength" (coocorrências observadas sobre esperadas sob independência).

## aria2017bibliometrix e arruda2022vosviewer

- Arquivo/URL: não lidos diretamente; citados como ferramentas (bibliometrix citado no Anexo I da proposta OQF; Arruda et al. citados pelo Technical Supplement Cochrane, p. 63).
- Pontos usados: existência das ferramentas e uso exploratório.

## aguiar2023mapeando — Aguiar, Soares e Lima (2023)

- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/2 Pergunta de pesquisa.../01_85619.pdf` (CGPC 28:e85619)
- O que foi lido: seletivo (seção de método, pp. 4-6).
- Pontos usados no capítulo:
  - pp. 4-5: busca só na WoS, limitada a Ciência Política e Administração Pública, só artigos de periódicos, só inglês, string única ("policy design*") em título, resumo e palavras-chave; 493 artigos; uma duplicata removida; VOSviewer para redes de citação direta.
- Limitações/observações: usado como exemplo de estratégia simples e suas limitações, não como modelo.

## schaefer_oqfunciona — Schaefer, Borges e Freitas (2025), proposta OQF

- Arquivo/URL: texto-base no scratchpad (preprint OSF aht4j_v1)
- O que foi lido: Tabela 1 (pp. 11-12), "Estratégia de busca" e "Estratégia de avaliação" (pp. 26-29), Anexo D (pp. 53-54), Anexo H (p. 101), Anexo I (p. 102).
- Pontos usados no capítulo:
  - pp. 11-12, Tabela 1: exemplo de string (dois blocos) e bases WoS, Scopus, Google Scholar e Catálogo CAPES; inclusão 2010-2024, português ou inglês.
  - p. 26: termos derivados de X e Y; aspas para expressões, asterisco para radicais; exemplo de string com quatro blocos.
  - pp. 26-27: escolha dos termos por conhecimento do campo, especialistas, outras RS ou tentativa e erro "(que deve ser reportada)"; Consensus para achar revisões; trade-off entre termos amplos e restritos; outras línguas se houver domínio do idioma.
  - p. 27: duas fontes: bases eletrônicas e bola de neve para trás e para frente; problemas das bases pagas e do viés para grandes editoras; notas técnicas, preprints e relatórios; Publish or Perish, IPEA, busca manual; "O essencial é que esses passos sejam reportados."
  - pp. 27-28: WoS e Scopus via Portal CAPES; 1.740 documentos: 400 PoP/Scholar, 87 SciELO, 798 Scopus, 455 WoS; formatos xls, bib, txt; WoS 79 variáveis, PoP 26.
  - p. 28: filtro de ano após 2007 (lançamento do iPhone).
  - p. 29: 19 trabalhos; "A partir de busca manual incluímos mais dois trabalhos em nosso banco, duas RS sobre o tema"; validação: "todos os trabalhos que encontramos estavam nas revisões".
  - pp. 53-54, Anexo D: bases listadas (Google Scholar, WoS SSCI, Scopus, Catálogo CAPES, JSTOR, SSRN, PAIS, WPSA, EconLit, HeinOnline, OECD iLibrary, SciELO, Redalyc, PQDT), com base em verbete da Wikipedia.
  - p. 101, Anexo H: strings por base com resultados: PoP PT 200 e EN 200; SciELO (("celular" OR "smartphone" OR "telefone") AND ("escola" OR "estudante")) 87; WoS 455 e Scopus 798 com restrições de área.
  - p. 102, Anexo I: bibliometrix para análises exploratórias (coocorrência de palavras-chave).

## schaefer2025proibicao — Schaefer, Borges e Gomes Filho (2025), celulares

- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/6 Análise de dados/FINAL+-+A+PROIBICAO+DO+USO+DOS+CELULARES.pdf` (JPPG 1(2):97-113)
- O que foi lido: seletivo (resumo, seções 1-2, trechos de resultados).
- Pontos usados no capítulo:
  - p. 100: PICOC (população estudantes, escolas e redes; intervenção proibição/restrição; contexto global).
  - p. 101, Quadro 1: WoS com bloco extra "(achievement OR learn OR development OR success)" e "student" sem truncamento; Scopus "(achievement OR learn)"; Google Scholar PT e EN (200 resultados); SciELO dois blocos em português; Harzing's Publish or Perish 8.0; acesso via portal institucional; R 4.3.2.
  - p. 102: recorte temporal 2004-2024; idiomas português e inglês; 1.740 documentos; deduplicação 1.517; filtro a partir de 2007 1.430; tipos 1.382; 19 trabalhos + 2 "através de busca por bola de neve através de citações" = 21.
- Limitações/observações: strings do artigo diferem das do Anexo H do preprint (ex.: "learn" vs "learn*"); recorte temporal diverge entre Quadro 1 (2004-2024), filtro (2007) e Tabela 1 do preprint (2010-2024); o preprint descreve os 2 acréscimos como RS, o artigo como bola de neve.

## campbell2024evidence e bottger2024ban

- Arquivo/URL: metadados e resumos via OpenAlex (DOI 10.1177/20556365241270394; DOI 10.3390/educsci14080906). O PDF de Campbell et al. está na pasta 2 do curso, mas não foi lido.
- Pontos usados: Campbell et al. (2024) revisão de escopo com PRISMA-ScR e protocolo no OSF, 22 estudos; Böttger e Zierer (2024) revisão rápida guiada por PRISMA sobre proibição de smartphones. Usados só como fontes de estudos-âncora no exemplo.

## schaefer2026aula3 — Slides Aula 3 (Busca do material)

- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/9 Slides/OQF_MAPE_Aula_3_atualizada.pdf` (28 pp.)
- O que foi lido: inteiro (texto e visual).
- Pontos usados no capítulo:
  - p. 16: protocolo REFIS com descritores PT/EN ("REFIS", "parcelamento tributário", "tax avoidance", "tax planning", "planejamento tributário" etc.) e bases previstas "Scholar, Scielo, Portal de Teses e Dissertações".
  - p. 18: PICOC ("efeitos das causas") vs CMMO ("causas dos efeitos").
  - p. 19: blocos P, I, O com OR dentro e AND entre; truncamento; "Documente todas as versões testadas"; sinônimos PT, EN, ES.
  - p. 20: tabela de termos (P, I, C, O-A) e string trilíngue sobre bioeconomia e desmatamento na Amazônia; a string não contém o bloco C da tabela e termina com AND ("Brazil*”) com aspa de fechamento curva.
  - p. 21: bases por área (Políticas sociais/Educação: WoS, Scopus/EBSCO, PsycINFO/ERIC, Portal CAPES; Saúde: PubMed/MEDLINE, Cochrane, LILACS, SciELO; Meio ambiente: WoS, Scopus/GreenFILE, Environmental Science DB, OpenAlex; Economia/Políticas públicas: EconLit/SSRN, 3ie/Campbell, IPEA/Banco Mundial, CAPES teses).
  - p. 22: literatura cinzenta (Banco Mundial, BID, OCDE, ONU, FAO; IPEA, FGV, institutos estaduais; relatórios de avaliação, TCU, CGU, ministérios; snowballing).
  - p. 23: ferramentas (Zotero, OpenAlex, Publish or Perish, capesR, easyScieloPak, Rayyan/Covidence).
  - p. 26: bibliometria (VOSviewer, Bibliometrix, CiteSpace, OpenAlex API).

## schaefer2026aula4 — Slides Aula 4 (Filtragem e controle de qualidade)

- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/9 Slides/OQF_MAPE_Aula_4_Filtragem_e_Controle_de_Qualidade.pdf` (52 pp.)
- O que foi lido: pp. 20-41 (visual) e pp. 42-52 (visual, para o PRISMA do REFIS).
- Pontos usados no capítulo:
  - p. 21: bases usadas no REFIS: OpenAlex, SciELO/WoS SciELO, WoS, Scopus, "BDTD — Teses e Dissertações CAPES", IPEA.
  - p. 23: vantagens da busca via pacotes R (rastreabilidade, código único, padronização); capesR, openalexR, easyScieloPak.
  - pp. 25-27: critérios; recorte 2001-2025 justificado pela Lei 9.964/2001.
  - p. 31: string simples blocos I + O + C.
  - p. 32: bloco M construído com auxílio de IA (Claude Sonnet).
  - p. 33: construção com IA (Claude, DeepSeek V3, ChatGPT, Consensus); prompt iterativo; documentação de versões.
  - p. 35: string OpenAlex de 26/04/2026 com "PAES", "PAEX", "PERT", "PRT".
  - p. 36: interface web do OpenAlex com essa string: 86 works.
  - p. 37: nova versão, mesma data, sem "PAES", "PAEX", "PERT", "PRT".
  - p. 39: "Resumo das Bases": WoS 3; WoS SciELO 21; SciELO 0; BDTD 158 (filtros área e ano 2000-2024); OpenAlex 4; IPEA 4; Final 190; filtros "Nenhum" nas demais; string da WoS contém "regis" (Topic).
  - p. 48: PRISMA REFIS: 186 registros das bases + 4 IPEA "não incluídos na deduplicação formal"; bola de neve +9; corpus final 21.

## schaefer2026codigos — Scripts R do curso

- Arquivo/URL: `~/Downloads/zs6h4-osfstorage-archive/11 C*digos R - Atualizado e Consolidado/4 Busca trabalhos Capes.R`; `.../5 Junção Base de Dados.R`; `~/Downloads/zs6h4-osfstorage-archive/12 C*digos R - OpenAlex/1 Coleta de Dados OpenAlex API.R`
- O que foi lido: os três scripts inteiros (lidos com mascaramento de possíveis chaves; o script OpenAlex desta pasta tem a opção de chave vazia).
- Pontos usados no capítulo:
  - Script 4: `capesR::download_capes_data` para 2000-2024; filtro por regex sobre o título em minúsculas, termos unidos por `|` sem fronteira de palavra (inclui "tax avoidance", "tax planning", "planejamento tributário"); `distinct(titulo)`; filtro por lista de áreas; exporta `bdtd.xlsx`.
  - Script 5: lê `openalex.csv`, `bdtd.xlsx` (teses), `wos_scielo.txt` (TSV exportado pelo WoS) e `wos.bib` (bibliometrix `convert2df`); esquema de 13 colunas; não há arquivo do IPEA nem de bola de neve.
  - Script 1 OpenAlex: blocos em PT e EN; `oa_fetch(..., count_only = TRUE)` antes de baixar; `distinct(id)`; salva `.rds` completo e `.xlsx` achatado.
  - Pasta `8 Códigos R` (exportações do caso celulares): `scopus.csv` com 798 registros; `Google Scholar Portuguès.csv` e `Google Scholar Inglès.csv` com 200 registros cada (GSRank 1 a 200), `QueryDate` 2025-03-19 21:37 e 21:32; o parâmetro `dq` das URLs mostra a consulta enviada pelo PoP ao Scholar sem parênteses, com OR convertido em `|` e AND em espaço: versão PT com 187 caracteres, EN com 165; `bani*`, `escola*`, `aprend*`, `ban*`, `learn*` enviados literalmente; primeiros resultados em PT são livros sem relação com a pergunta ("Educação escolar: políticas, estrutura e organização"); `savedrecs.txt` começa com `FN Clarivate Analytics Web of Science`.
  - Verificação adicional (feita durante a escrita): a string PT do Quadro 1 tem 252 caracteres na forma do artigo, mas a consulta efetivamente enviada tinha 187, então não houve truncamento pelo limite de ~250 caracteres. A primeira versão do capítulo afirmava o risco; foi corrigida.
- Limitações/observações: nenhuma chave de API reproduzida.

## Outras fontes consultadas sem uso direto

- BR-Congress scoping review (`~/Desktop/BR-Congress-Preferences/scoping-review/code/utils_openalex.py` e README): consulta única `title_and_abstract.search` com três blocos; sem filtros de idioma ou conceito; ruído aceito e tratado na triagem; reconstrução do resumo a partir do índice invertido. Usado apenas como inspiração do passo "contar antes de baixar" e do contrato da skill; não citado como fonte normativa.
- Páginas iniciais verificadas (existência e natureza): 3ie Development Evidence Portal, Overton, Repositório IPEA, Base de Conhecimento da CGU (18.882 documentos na data), EconLit (AEA), IDEAS/RePEc, LILACS (BIREME/OPAS/OMS), Open Knowledge Repository (Banco Mundial), BRAPCI, SciELO Preprints, pesquisa de jurisprudência do TCU. Bloqueadas (403): Epistemonikos, BID, SSRN, DOAJ, OCDE, SciELO search; Enap sem resposta.
