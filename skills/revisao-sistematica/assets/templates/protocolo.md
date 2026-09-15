# Protocolo de revisão sistemática: <X> e <Y> em <contexto>

<!--
Modelo de protocolo da skill revisao-sistematica. Combina PRISMA-P 2015 (números entre colchetes),
os campos do formulário geral de registro do OSF e o formato OQF (pergunta, framework, busca,
elegibilidade, seleção, sistematização, análise).
- Copie para 00-protocolo/protocolo.md. Tudo o que está em 00-protocolo/ (exceto emendas*) é
  congelado por sha256 no portão G2; depois disso, mudança = emenda (00-protocolo/emendas.md +
  `$RS emenda --arquivo ... --motivo ...`).
- Escreva no futuro e como se houvesse estudos para todas as análises; o que não puder ser feito
  vira "Diferenças entre protocolo e revisão".
- Placeholders entre <>. Seção que não se aplica ao tipo: escreva "Não se aplica: <motivo>".
  Nunca apague a seção.
- Sem nomes de pessoas nos arquivos do projeto se ele for público: use papéis.
-->

- **[1a] Tipo:** protocolo de <revisão sistemática mista e sequencial | RS de efetividade | revisão de escopo | ...> (`--tipo <valor>`)
- **Variante:** <nenhuma | rápida: prazo e atalhos combinados no G1, cada um descrito na seção de método que altera (ex.: dupla triagem em ≥ 20% dos resumos e segunda leitura de todos os excluídos; RoB e extração por uma pessoa com verificação integral por outra)>
- **[1b] Atualização de revisão anterior?** <não | sim: referência>
- **Versão:** v1.0 | **Congelado em:** <AAAA-MM-DD, preenchido no G2> | **Idioma dos produtos:** <pt-BR>
- **[2] Registro:** <OSF Registries, Generalized Systematic Review Registration> submetido com esta versão congelada; DOI/URL e data anotados no cabeçalho de `00-protocolo/emendas.md` (editável depois do G2) | **Etapa no momento do registro:** <antes da busca definitiva>
- **[3a] Equipe e papéis:** <papel: revisor_humano_1 (coordenação, triagem), revisor_humano_2 (triagem, extração), revisor_humano_3 (desempate), estatística>
- **[3b] Contribuições:** <CRediT por papel> | **Garantidor:** <papel>
- **[5a-5c] Financiamento e papel do financiador:** <...> | **Conflitos de interesse:** <...>
- **[4] Plano de emendas:** log em `00-protocolo/emendas.md`; toda mudança datada, justificada, com etapa e resultados já conhecidos; versões maiores (v2.0) geram *update* no registro.

## 1. Pergunta e justificativa

**[6] Racional.** <problema de política, decisão que a revisão informa, usuários, uso ex ante ou ex post>

**Revisões existentes e registradas** (busca feita em <AAAA-MM-DD>; detalhes em `00-protocolo/pergunta.md`):

| Fonte consultada | Data | Termos | Revisões achadas | Decisão (não fazer / atualizar / overview / RS nova) e em que esta difere |
|---|---|---|---|---|
| <OSF Registries, PROSPERO, Campbell, Cochrane, Epistemonikos, 3ie, OpenAlex, SciELO, CAPES, IPEA> | | | | |

**[7] Pergunta principal.** <X melhora/reduz Y em P no contexto C, em comparação com Cm?>

- **Escala:** <(1) ampla, de problema | (2) restrita, X sobre Y | (3) X sobre vários Y>
- **Perguntas secundárias:** <mecanismos (M): por quê/como?; moderadores (Z): para quem/onde/quando?; implementação; percepção; custo>
- **Stakeholders consultados:** <órgão ou grupo, quando, o que mudou; ou "não houve envolvimento">
- **Equidade (PROGRESS-Plus):** <fatores escolhidos e hipótese de efeito diferencial com direção; ou "não se aplica: motivo">

## 2. Framework e teoria do programa

**Framework** (<PICOC + CMMO | PCC | PICo | SPIDER | CMO>): PICOC define elegibilidade, blocos de busca e células de efeito; CMMO orienta extração e síntese qualitativa e **não** filtra estudos.

| Elemento | Definição operacional | Inclui | Não inclui | Nó do DAG |
|---|---|---|---|---|
| P (população/unidade) | | | | |
| I (intervenção; componentes e família) | | | | |
| C (comparação) | | | | |
| O (desfechos: ver tabela abaixo) | | | | |
| C (contexto) | | | | |
| M (mecanismos) | | | | |
| Z (moderadores; hipótese e direção) | | | | |

**Teoria do programa:** `00-protocolo/teoria_programa.md` (níveis I→R, I→M→R e completo) e diagrama `00-protocolo/dag_v1.<mmd|R>`, com efeito não intencional por elo, confundidores e colisores a checar, moderadores numa tabela Z à parte (não como setas para o tratamento), ciclos desdobrados no tempo e origem de cada seta (documento, estudo, stakeholder ou "hipótese gerada por IA, não verificada").

**[13] Desfechos** (a coluna `construto_outcome` e `direcao_desejada` serão copiadas para a extração de efeitos; valores aceitos pelos scripts: `aumentar` | `reduzir`):

| construto_outcome | Medidas aceitáveis | Janela | direcao_desejada | Benefício ou dano | Crítico ou importante | Critério de elegibilidade? | Elo da teoria |
|---|---|---|---|---|---|---|---|
| <arrecadacao> | <...> | <6-24 meses> | aumentar | benefício | crítico | não | <I→M→R> |
| <inadimplencia_estrategica> | <...> | <...> | reduzir | dano (incentivo perverso) | importante | não | <elo perverso> |

Regras: ao menos um dano entre os desfechos; até sete críticos ou importantes; conflito entre stakeholders sobre o que é desejável vira dois desfechos, não uma escolha silenciosa.

## 3. Fontes e busca

**[9] Fontes** (sem limite de idioma, data ou tipo na base; limites só com justificativa):

| busca_id | Fonte | Plataforma / acesso | Tipo (base, registro, teses, site, citação, contato) | Cobertura | Formato de exportação | Justificativa |
|---|---|---|---|---|---|---|
| B01 | <Scopus> | <Elsevier> | base | <anos> | <CSV> | <...> |
| B02 | <Web of Science Core Collection> | <Clarivate> | base | | <texto (FN Clarivate)> | |
| B03 | <SciELO Citation Index> | <Web of Science> | base regional | | <TSV> | |
| B04 | <OpenAlex> | <API, `$RS buscar openalex`> | base | | <JSONL> | |
| B05 | <Catálogo de Teses CAPES ou BDTD> | <dados abertos / exportação> | teses | | <CSV> | |
| CZ1 | <IPEA, TCU/CGU, Banco Mundial...> | site | cinzenta | | <PoP CSV ou lista manual> | <N primeiros resultados triados por consulta> |
| SN1 | Busca por citação (para trás e para frente) | OpenAlex (`$RS bola-de-neve`) | citação | | JSONL | sementes = todos os incluídos no texto completo |
| MN1 | <contato com autores e especialistas> | | manual | | <planilha> | |

**[10] Estratégia completa de ao menos uma base** (rascunho testado, colado aqui para ser congelado no G2; as versões executadas ficam em `01-busca/strings/<string_id>.txt`):

```text
<base principal, campo, blocos PT/EN/ES unidos por OR e combinados por AND, limites: nenhum>
```

Tabela de termos por conceito (PT, EN, ES, siglas, nomes de programas e leis): <aqui ou em `00-protocolo/termos_v1.md`>.

**Validação da busca:** revisão por pares PRESS 2015 (checklist `assets/checklists/press.csv`) antes de traduzir para as demais bases; estudos-âncora de validação reunidos **antes** da string e fora da escolha de termos (origem: <estudos incluídos em revisões anteriores, especialistas>), em `00-protocolo/ancoras_validacao.csv`, montado por quem não escreve as strings e lido só pelos scripts; meta: recuperar todas as âncoras indexadas nas bases; recall relativo por base relatado; alerta se mais de 25-30% dos incluídos vierem só de outros métodos. **Atualização:** rodar de novo todas as fontes se a última busca tiver mais de 12 meses na data prevista de publicação. **Log:** PRISMA-S em `01-busca/log_buscas.csv`.

## 4. Elegibilidade

**[8] Características dos estudos:**

| Critério (mesmo id em `02-triagem/prompts/ta_vN.md` e no codebook de elegibilidade `00-protocolo/codebook_elegibilidade.csv`) | Inclui | Exclui | Justificativa |
|---|---|---|---|
| C1 População e contexto (unidade, país, nível de governo, setor, período dos dados) | | | |
| C2 Intervenção estudada como objeto empírico (não só mencionada) | | | |
| C3 Desfecho do protocolo medido ou analisado (falta de dado numérico não exclui) | | | |
| C4 Desenho elegível, com o comparador exigido (pelas características, não pelo rótulo; Maryland SMS só aqui, como elegibilidade de desenho) | | | |
| C5 Estudo primário (revisões e meta-análises NÃO são estudos: vão para bola de neve e validação da busca) | | | |
| C6 Sem retratação (checado no texto completo, no OpenAlex e na Crossref) | | | |

**[8] Características dos relatos:** anos de publicação <de AAAA-MM-DD (marco: ato normativo nº, data, conferido na fonte oficial) até a data da última busca>; idiomas <pt, en, es; justificativa>; status de publicação <qualquer: artigos, teses, dissertações, relatórios, textos para discussão, preprints>.

- Estudos que cobrem só parte da população elegível: <regra>.
- Estudos que não relatam o desfecho de interesse: não são excluídos por isso, salvo <justificativa>.
- Texto não obtido: "não recuperado" no PRISMA, nunca excluído por critério.
- **Funil formal (filtros):** `01-busca/filtros_v1.json`, todos em modo etiquetar, salvo: <nenhum | filtro X em modo excluir, previsto aqui, com amostra de elusão de n ≥ 300 dos etiquetados antes de aplicar e taxa aceitável decidida por humano>.

## 5. Seleção

- **[11a] Gestão dos registros:** `dados/registros.csv` (importação), `dados/registros_unicos.csv` (dedup auditável, pares candidatos revistos por humano), `dados/decisoes.jsonl` (ledger), via `rs.py`.
- **[11b] Triagem de títulos e resumos:** <dois revisores independentes (humanos ou IA validada), árbitro cego, humano decide divergências, inclusive as resolvidas pelo árbitro>; registro sem resumo nunca excluído (vira incerto); incerto segue ao texto completo; critérios versionados em `02-triagem/prompts/ta_vN.md`.
- **Calibração humana:** dupla codificação de ≥ 100 registros ou ≥ 10 incluídos; seguir só com κ ≥ 0,6 e concordância ≥ 75%; senão critérios vN+1.
- **Texto completo:** <dois revisores; LLM só propõe com trecho verbatim e página; humano decide incluir, excluir ou aguardando classificação>; motivos de exclusão pelo primeiro critério que falha; PDF conferido contra a referência (PDF de outro trabalho = não recuperado); ligação de relatos do mesmo estudo antes da extração; retratações checadas.
- **Bola de neve:** rodadas SN1, SN2... sobre os incluídos, re-triadas com a mesma versão dos critérios, até não haver novas inclusões.

## 6. Extração (sistematização)

- **[11c] Piloto:** 2-3 estudos por bloco (a1 quali descritivo, a2 quanti descritivo, b1 quali explicativo, b2 quanti explicativo) ou por tipo de fonte, antes da extração completa (portão G6).
- **[12] Codebook v0:** `00-protocolo/codebook_v0_<familia>.csv` (colunas `dimensao,variavel,descricao,prompt,tipo,aplicavel_se`; ponto de partida em `assets/codebooks/`: `oqf_decomposicao.csv`, `escopo_pcc.csv`, `qualitativa.csv`) e `00-protocolo/codebook_elegibilidade.csv` (de `elegibilidade_modelo.csv`), versão e sha256 congelados no G2.
- **Dupla extração:** dados numéricos de efeito 100% verificados na página do PDF (`verificado_humano`) ou extraídos em dupla com arbitragem; variáveis categóricas com segundo codificador cego em ≥ 20% dos estudos (mínimo 10), exigindo κ ou PABAK ≥ 0,7 e ≥ 80% por variável (senão redefinir e recodificar).
- **Contato com autores** para textos, dados faltantes e dúvidas de elegibilidade: <sim/não; prazo; número de tentativas>; registro em `03-textos/contato_autores.csv` (sem e-mails).
- **Regra de modelo principal** (escrita antes da extração): (1) o modelo que os autores declaram principal; (2) na falta, o de especificação completa pré-especificada; (3) o seguimento mais próximo da janela do desfecho; (4) empate: o primeiro da tabela principal. Nunca o mais significativo.
- **Unidade de análise:** estudo (`id_estudo`) > relato (`id_rs`) > efeito (`id_efeito`); estimando registrado (ITT, LATE, ATT, RDD local, associação); ajuste para conglomerados (tamanho médio e ICC).

## 7. Risco de viés

**[14] Ferramenta por desenho** (qualidade ≠ desenho; julgamento por domínio, com trecho; LLM só rascunha respostas às perguntas-sinalizadoras, humano julga):

| Desenho / bloco | Ferramenta | Codebook de partida (`assets/codebooks/`) | Nível (estudo ou desfecho) | Uso na síntese |
|---|---|---|---|---|
| Ensaio randomizado (b2) | RoB 2 | `rob2.csv` | desfecho | sensibilidade sem risco alto; GRADE |
| Não randomizado, quase-experimento (b2) | ROBINS-I V2 (+ Waddington 2017) | `robins_i.csv` | desfecho | idem |
| Séries temporais interrompidas, antes-depois controlado | EPOC | `epoc.csv` | desfecho | idem |
| Exposição (não intervenção) | ROBINS-E | <sem codebook na skill: montar> | desfecho | idem |
| Qualitativo (a1, b1) | CASP ou JBI QARI | `casp_qualitativo.csv` | estudo | CERQual (limitações metodológicas) |
| Quantitativo descritivo, transversal (a2) | JBI transversal | `jbi_transversal.csv` | estudo | descritor |
| Métodos mistos primário | MMAT | `mmat.csv` | estudo | descritor e CERQual/GRADE |
| Elegibilidade de desenho (não é RoB) | Maryland SMS | `desenho_maryland.csv` | estudo | só critério C4 e descritor |
| Revisões (se o tipo for overview) | AMSTAR 2 ou ROBIS | <sem codebook na skill> | revisão | não se aplica a RS de primários |

**[16] Metavieses:** viés de publicação (funil, Egger e PET-PEESE com erro-padrão modificado para diferenças padronizadas, e seleção 3PSM, só com k ≥ 10); relato seletivo (ROB-ME ou comparação com protocolos/registros dos estudos).

## 8. Síntese

**[15a] Critérios de comparabilidade** (checklist antes de agregar; estudos que não se encaixam vão para a síntese sem meta-análise com método declarado, relatada pelo SWiM, nunca para "síntese narrativa" sem método):

| Dimensão | Agrupa junto quando | Separa quando |
|---|---|---|
| Família de intervenção (`familia_intervencao`) | | |
| Comparador | | |
| Construto do desfecho (`construto_outcome`) | | |
| Janela de medida | | |
| População / unidade | | |
| Estimando | | |
| Desenho | randomizados e não randomizados nunca agregados juntos | |

**[15b] Medida e modelo:** g de Hedges alinhado por `direcao_desejada` (positivo = benéfico), conversões com `formula_id` e `aproximado` (desfechos binários: proporções, efeitos em pontos percentuais de LPM, DiD ou RDD e razão de riscos convertidos a d pelo log OR com a proporção do controle, <aceitos | não aceitos>, aproximados em sensibilidade); efeitos aleatórios REML + HKSJ modificado; τ² com IC (interpretado só com k ≥ 5), I², Q e intervalo de predição; k ≥ 3 estudos para agregar (`--k-min 3`); dependência: <um efeito por estudo pela regra de modelo principal | CHE + RVE CR2, ρ = <0,6>, gl de Satterthwaite < 4 = não confiável>.

**[15c] Heterogeneidade, subgrupos e sensibilidade:** moderadores pré-especificados <lista, com justificativa e direção>; estimativa por subgrupo só com k ≥ 3 por nível e teste de diferença entre subgrupos só com ≥ 4 estudos por nível (abaixo disso, estimativas lado a lado sem teste); meta-regressão ~10 estudos por covariável; intervalo de predição interpretado só com k ≥ 5; sensibilidade: leave-one-out, sem risco alto/crítico, sem conversões aproximadas, seleção 3PSM (k ≥ 10); resultados em risco crítico <na análise principal, com sensibilidade sem eles | fora da análise principal (`--excluir-rob critico`), com sensibilidade com eles>.

**Limiar de relevância e magnitude** (fixados agora; usados em `analise meta --delta` e `caixa --delta --faixas`, que comparam com o g alinhado: δ em unidade natural precisa da conversão para g declarada aqui):

| construto_outcome | δ / SESOI (unidade natural) | δ em g (conversão e DP de referência) | Fonte do δ | Faixas de magnitude (g) | Fonte das faixas (benchmark do campo, não Cohen genérico) |
|---|---|---|---|---|---|
| <arrecadacao> | <2% da arrecadação> | <0,10; DP de referência: ...> | <custo da política, meta legal, literatura> | <trivial:0, pequena:0.1, moderada:0.25, grande:0.5> | <referência> |

**[15d] Sem meta-análise:** SWiM (agrupamento, métrica padronizada, direção pelo estimador, teste de sinal binomial exato, effect direction plot; albatross quando só há p e n). Nunca "sem efeito" por p > 0,05. Testes combinados (Stouffer, Winer, Cooper, Fisher) só como análise secundária com ressalva, sem definir rótulos.

**Síntese qualitativa e integração** (se mista): técnica <síntese temática | framework synthesis | meta-agregação>; temas e juízos humanos; integração sequencial-explicativa (quanti define células e heterogeneidade → quali gera hipóteses → subgrupo/meta-regressão quando k permite → joint display); caixa de ferramentas com as regras abaixo.

**Regras da caixa de ferramentas** (versão `caixa-3`; célula = família de intervenção × construto de desfecho × classe de desenho, com randomizados e não randomizados em linhas separadas e uma linha de painel por família × construto; os limiares marcados como convenção não vêm de norma externa e só mudam por emenda com nova versão da regra):

| Ordem | Condição | Rótulo |
|---|---|---|
| 1 | sem juízo de certeza GRADE | Pendente |
| 2 | certeza muito baixa | Inconclusivo |
| 3 | meta-análise com k ≥ 5 (τ² e intervalo de predição interpretáveis), δ fixado acima, intervalo de predição além de ±δ nos dois lados e achado de moderador ou mecanismo que explica a heterogeneidade, com enunciado e confiança CERQual ≥ baixa (convenção) | Misto |
| 4 | explicação da heterogeneidade alegada e intervalo de predição cruzando ±δ, mas faltando k ≥ 5, δ ou o achado com CERQual ≥ baixa | Inconclusivo |
| 5 | meta-análise com IC que exclui zero e certeza ≥ baixa; sem meta-análise, teste de sinal exato p < 0,05 com ≥ 5 estudos e ≥ 70% na mesma direção (convenção; na prática ≥ 6 estudos) e não só estudos de risco alto | Positivo ou Negativo |
| 6 | δ fixado acima, IC inteiro em [−δ, +δ] e certeza ≥ moderada | Nulo |
| 7 | demais casos | Inconclusivo |

- **Linha de painel** (convenção): um só corpo de evidência, o rótulo dele; corpos com rótulos diferentes, o rótulo do corpo de maior certeza, com o outro anotado; mesma certeza e rótulos diferentes, Inconclusivo (heterogeneidade por desenho); algum corpo pendente, Pendente.

- **Força:** certeza GRADE da célula (alta = forte; moderada = moderada; baixa = fraca; muito baixa = insuficiente).
- **Escala:** faixa de magnitude da tabela acima.
- **Implementação** (convenção): um ponto por critério presente (mais de dois componentes; mais de um nível de governo ou vários atores; nova infraestrutura ou pessoal; barreiras de fidelidade ou adoção em ≥ 2 estudos; tempo até o efeito maior que <prazo>): 0–1 Simples, 2–3 Moderada, ≥ 4 Complexa; confiança CERQual.
- **Mecanismo, moderador, percepção e custo:** enunciados com estudos de suporte e CERQual; custo unitário ou "não reportado".
- **Testes combinados** nunca definem rótulo.

## 9. Certeza e da evidência à prática

- **[17]** GRADE por célula de efeito (indireção inclui contexto institucional, nacional, nível de governo e estimando; sem meta-análise conforme Murad 2017); GRADE-CERQual por achado qualitativo; realista/QCA: enunciado narrativo, sem pseudo-GRADE. Desfechos da tabela de resumo: <lista, escolhida antes de ver resultados>.
- **Corpo não randomizado avaliado com ferramentas diferentes** (ROBINS-I V2 e EPOC na mesma célula): ponto de partida único do GRADE <alta com rebaixamento por risco de viés | baixa>, com justificativa.
- **Da evidência à prática:** EtD simplificado (benefícios e danos, certeza, custo, equidade, viabilidade, transferibilidade ao Brasil); nenhuma recomendação mais forte que a certeza.
- **Fatores de transferibilidade** (3 a 5, priorizados com usuários; cada preocupação contada num só domínio, indireção/relevância ou EtD): <ex.: nível de governo e autonomia fiscal; desigualdade regional; marco legal; implementador>.
- **Contingências:** <menos estudos que k mínimo → SWiM; dados faltantes → contato com autores e análise de sensibilidade; ...>

## 10. Plano de uso de IA

| Etapa | Ferramenta / modelo (versão) | Papel (propõe, decide, prioriza) | Supervisão humana | Validação e limiar | Se falhar |
|---|---|---|---|---|---|
| Sugestão de termos da busca | <modelo> | propõe | especialista confere sentido; teste de contagem e âncoras de desenvolvimento | termo só entra após teste | descartar termo |
| Triagem T/A | <subagentes: modelo> ou <API: modelo A, modelo B de outro provedor, árbitro de terceiro modelo, preferencialmente de outro provedor> | decide com validação | calibração dupla; amostra nova enriquecida (≥ 60 incluídos humanos) | recall ≥ 0,95 com limite inferior do IC ≥ 0,90; κ, PABAK, WSS@95; elusão n ≥ 300 dos excluídos; estabilidade em 5-10% | análise de falsos negativos → critérios vN+1 em amostra nova → regra liberal → IA só prioriza → dupla humana |
| Elegibilidade no texto completo | <modelo> | propõe com trecho e página | humano decide todos | conferência de 100% | — |
| Extração e efeitos | <modelo> | propõe com trecho e página | verificação humana de 100% dos números | gate de citação; plausibilidade | nova extração |
| Risco de viés | <modelo> | rascunha perguntas-sinalizadoras | humano julga domínios | — | — |
| Síntese qualitativa, CERQual, GRADE | <modelo> | rascunha | humano decide temas e juízos | — | — |

Prompts e critérios versionados com sha256 (`02-triagem/prompts/`), parâmetros congelados por rodada; títulos e resumos enviados a provedor externo só com consentimento (modo API); declaração de uso de IA gerada do log (`$RS declaracao-ia`).

## 11. Divulgação, dados e código

- **Produtos:** <artigo no formato OQF | manuscrito PRISMA 2020 | relatório de escopo | policy brief>; diretrizes de relato: <PRISMA 2020 + PRISMA-S; SWiM; ENTREQ; PRISMA-ScR; PRISMA-trAIce>.
- **[PRISMA 2020 item 27] Pacote aberto:** protocolo congelado, emendas, strings e log de buscas, codebooks, decisões, dados extraídos e código em <repositório>.
- **Log de desvios:** `00-protocolo/emendas.md`.
