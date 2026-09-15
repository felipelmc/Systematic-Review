# Armadilhas: erros que invalidam revisões e como a skill os bloqueia

Para cada uma das dez armadilhas da especificação metodológica: o sintoma, a checagem automática que existe de fato nos scripts (comando e comportamento), a checagem humana que continua obrigatória e a lacuna que nenhum script cobre. No fim, lições gerais de projetos reais. `$RS` abrevia `python3 "<pasta da skill>/scripts/rs.py"` (SKILL.md, "Como chamar os comandos"): em cada chamada de Bash, use a função `rs` definida na mesma chamada ou o caminho completo, nunca uma variável `RS`. Códigos de saída: 1 uso/dados, 2 checagem metodológica, 3 dependência.

## Sumário

1. Filtros que perdem registros
2. Busca fraca
3. Duplicatas e confusão estudo/relato
4. Decisões de LLM não validadas
5. Extração alucinada ou errada
6. Contagem de votos por significância
7. Efeitos dependentes e dupla contagem
8. Conversões ou sinais errados
9. Agregação de evidência não comparável e heterogeneidade oculta
10. Funil e relato não reprodutíveis
11. Lições gerais

## 1. Filtros que perdem registros

Sintoma: dicionário ou regex exclui estudos relevantes; "sem" casa com SEM, "ols" com "bolsa"; registro sem resumo some; idioma ou tipo de documento derruba literatura cinzenta.

- **Automática.** `$RS filtrar --config 01-busca/filtros_v1.json --ancoras 00-protocolo/ancoras_validacao.csv`: modo padrão `etiquetar`; `excluir` sem `"previsto_no_protocolo": true` → saída 2; dicionário em `excluir` exige `validacao_elusao`, conferida contra o `*_metricas.json` de `filtrar --calcular-elusao` (assinatura do filtro; diferente → saída 2); `filtrar --amostra-elusao N --semente S` sorteia a planilha cega dos etiquetados; idioma em `excluir`, ou tipo que atinja tese, dissertação, relatório, evento, preprint, livro ou capítulo, exige `justificativa`; termos com fronteira de palavra e acentos dobrados, siglas sensíveis a caixa; campo ausente = `sem_dado` (segue); registro sem resumo nunca excluído por filtro textual; âncora excluída → saída 2 com as saídas gravadas para auditoria. Na triagem, `triagem mesclar` rejeita exclusão de registro sem resumo e `triagem consolidar` rebaixa para `incerto` qualquer exclusão não humana desses registros.
- **Humana.** Ler `02-triagem/filtro_formal_contagens.json` por filtro; codificar a amostra de elusão e decidir se a taxa permite excluir; revisar etiquetas com humano.
- **Lacuna.** Não há limiar automático para a taxa de elusão (a decisão é humana); âncoras não encontradas no corpus são só relatadas (problema da busca, item 2).

## 2. Busca fraca

Sintoma: strings só em inglês, sem bases lusófonas nem cinzenta; estudos-âncora ausentes; muitos incluídos vindos só de bola de neve; busca velha na publicação.

- **Automática.** `$RS buscar openalex --query "..." --contar` (e `--listar N`) testa strings sem importar; `$RS importar` (com `--string-id --executada-em --n-base --filtros-na-base --plataforma`), `buscar` e `bola-de-neve` registram string, data, `n_bruto`, filtros e plataforma em `estado.buscas` (base do PRISMA-S); `importar --substituir` tira do fluxo a busca superada, sem apagar linhas; `$RS filtrar --ancoras` calcula o recall relativo combinado, por busca e por base (`01-busca/recall_ancoras.json`, IC de Clopper-Pearson); `$RS status` alerta buscas sem data ou com mais de 12 meses (o G9 repete como aviso); `$RS bola-de-neve` grava `metodo_identificacao = citacao` (ramo "outros métodos" do PRISMA); `$RS textos elegibilidade consolidar` avisa quando mais de 30% dos incluídos vieram só de outros métodos; `$RS portao G3` bloqueia sem busca ativa, sem PRESS registrado (`01-busca/press_*.md` ou pendência `revisao_press`) e com busca ativa truncada (`--max-paginas`; o `status` e o `prisma` também a marcam como rascunho), avisa sem `recall_ancoras.json` ou com recall combinado < 1 (listando as âncoras não achadas) e congela strings e filtros; `buscar openalex --substituir` troca a busca de teste pela completa.
- **Humana.** PRESS 2015 por um segundo especialista (`assets/checklists/press.csv`); conjunto de estudos-âncora montado independentemente das strings, com `indexada_em` conferido; blocos PT/EN/ES; SciELO, CAPES/BDTD e cinzenta; decisão de atualizar a busca.
- **Lacuna.** O recall das âncoras no G3 só gera aviso (não bloqueia), mesmo quando o protocolo fixa um limiar; o G3 confere que o PRESS existe, não o que ele diz, e não compara o sha dos filtros com o protocolo (`previsto_no_protocolo` é autodeclarado): leve os números aos critérios do portão. `log_buscas.csv` continua manual.

## 3. Duplicatas e confusão estudo/relato

Sintoma: preprint e versão publicada contados duas vezes; tese e artigo fundidos ou tratados como estudos independentes; "Part I" e "Part II" fundidos; revisão contada como estudo.

- **Automática.** `$RS dedup`: R1 DOI, R2 id da fonte, R3 título exato, R4 fuzzy ≥ 95 com mesmo sobrenome (auto), R5 candidato; preprint ou working paper ↔ publicado nunca funde: vira `ligado` (relatos com `id_rs` próprios e o mesmo `id_estudo`, em `03-textos/ligacao_relatos.csv`) ou candidato a ligação, e clusters antigos fundidos são separados com aviso; tese ↔ artigo e títulos que diferem em parte/numeral nunca fundem; auditoria em `01-busca/dedup_pares.csv`; candidatos pendentes deixam a etapa 05 incompleta no `$RS status` (pendência no autopiloto); flag `retratado` quando título ou tipo indicam retratação ou quando o OpenAlex marcou `is_retracted` na importação (`dados/registros_flags.csv`). `$RS textos retratacoes` consulta OpenAlex e Crossref (dados do Retraction Watch) e abre a pendência `retratacao_texto` em qualquer modo. `$RS textos ligar-relatos --pares <csv>` define `id_estudo`; `$RS prisma` conta estudos por `id_estudo` e relatos por `id_rs`; `preparar-efeitos` recusa revisões e meta-análises e `efeitos.R` as marca `rejeitado_revisao`.
- **Humana.** Decidir candidatos com `$RS dedup --revisar 01-busca/dedup_pares.csv --por revisor_humano_1` (sem `decidido_por` nem `--por`, o comando recusa); conferir as ligações de versão; ligar relatos do mesmo estudo no texto completo, com a lista completa de pares (inclusive os de versão do `dedup`); decidir o que fazer com os retratados; verificar sobreposição entre revisões usadas na bola de neve e os primários.
- **Lacuna.** Textos sem DOI nem id do OpenAlex (teses, relatórios) ficam sem verificação de retratação (`retratado` vazio): conferência manual.

## 4. Decisões de LLM não validadas

Sintoma: triagem por IA aceita sem amostra humana; recall desconhecido; exclusões unânimes nunca vistas; prompt mudado no meio.

- **Automática.** `$RS triagem mesclar` valida schema, conjunto exato de IDs, enums, critério existente no arquivo de critérios e trecho contido no título/resumo (inválido → `rejeitados/` e novo subagente); lotes e respostas carregam `criterios_sha`, e `triagem preparar` recusa outra versão dos critérios dentro da mesma rodada. `$RS validar amostrar --finalidade calibracao|desenvolvimento|validacao` gera planilha cega (com `--excluir-ids` para amostra nova e `--sem-ia` para a calibração só humana); `$RS validar calcular` calcula κ, PABAK, sensibilidade, especificidade e IC de Clopper-Pearson com reponderação, trata "não revisado" como NA e sai com 2 se `atende_limiares` for falso (recall ≥ 0,95 com limite inferior ≥ 0,90; calibração: κ humano ≥ 0,6, ≥ 75% e tamanho); `$RS validar elusao` e `$RS validar estabilidade`. `$RS portao G4` só aceita a validação com `finalidade` `validacao` da rodada ativa e bloqueia sem ela ou abaixo do limiar; G4 congela `02-triagem/prompts/*.md`. `triagem consolidar` põe na fila humana também as divergências resolvidas pelo árbitro e não regrava uma fila com decisões humanas ainda não aplicadas (`fila_preservada`); a fila e as planilhas humanas são lidas com vírgula, ponto e vírgula ou tabulação e em `.xlsx`; `triagem override` exige critério válido em toda exclusão humana (T/A e texto completo). `validar calcular` classifica `motivo_reprovacao` (`largura_ic`, `humanos`, `desempenho_ia`) e, em revisão pequena, aponta a amostra maior ou o remédio 5 em vez de critérios novos. `$RS triagem api`: sem resumo → `incerto` sem chamada, árbitro de terceiro modelo (preferencialmente de outro provedor) com revisores anônimos, erros re-tentados, `max_tokens` não conta como sucesso, custo registrado no log. `$RS declaracao-ia` marca rascunho com IA na triagem sem a validação que decide ou com ela abaixo do limiar. No texto completo, `triagem fila --etapa tc` gera a fila humana e `textos elegibilidade consolidar` grava a proposta de IA e aplica as decisões humanas de `triagem override --etapa tc`, que prevalecem.
- **Humana.** Calibração dupla antes da rodada; dupla codificação da amostra enriquecida para ≥ 60 incluídos; análise dos falsos negativos antes de critérios vN+1; conferência humana de todas as decisões de texto completo.
- **Lacuna.** No autopiloto o G4 pode ser aprovado sem validação (vira pendência); os produtos saem como rascunho até ela ser fechada por humano. Não há comando para o remédio "IA só prioriza com critério de parada" (references/ia-validacao.md, E4). No atalho da variante rápida, o G4 confere a fração em dupla humana, o κ e a segunda leitura dos excluídos gravados por `validar calcular` e `validar segunda-leitura`, não a qualidade da releitura.

## 5. Extração alucinada ou errada

Sintoma: número que não está no PDF; erro-padrão lido como desvio-padrão; ficha do PDF errado; categóricas codificadas de modo inconsistente.

- **Automática.** `$RS textos inventario`: páginas, camada de texto e veredito de conteúdo (`suspeito`, `conferir_a_mao`, `sem_camada_de_texto` exigem olho humano). Gate de citações do `fichamento-sistematico` (trecho na página) e `concordancia.py` (sinaliza variáveis com κ e PABAK < 0,7 ou < 80%). `$RS analise verificar-efeitos`: trecho verbatim na página indicada, plausibilidade (DP > 0, n1 + n2 ≤ N, p coerente com t/df ou F, IC ordenado contendo a estimativa, OR > 0, |r| ≤ 1, ICC em [0, 1]), alerta de |g| > 2; saída 2 com trecho não encontrado ou erro; `pode_seguir_g7` só com `verificado_humano` em todos. `preparar-efeitos` descarta a verificação humana se os dados do efeito mudaram. `$RS portao G7` bloqueia com efeitos não verificados depois da última mudança, trecho fora da página, erro de plausibilidade ou `apto_g7 = 0`, e (fora de escopo e mapa) sem RoB consolidado e validado por humano em cada ferramenta, com seus arquivos alterados ou com resultado avaliado sem `rob_geral`; avisa sem concordância da extração calculada ou com variáveis sinalizadas sem arbitragem. `efeitos.R` repete o alerta |g| > 2. Nos desfechos binários, `verificar-efeitos` recusa proporção em percentual, `p0 + efeito_pp/100` fora de (0, 1) e RR·p0 ≥ 1.
- **Humana.** Conferir 100% dos números na página (ou dupla extração com arbitragem); segundo codificador cego em ≥ 20% das fichas (mínimo 10); piloto de 2–3 estudos por bloco antes do G6.
- **Lacuna.** Um trecho verdadeiro pode sustentar número digitado errado em outra coluna: a conferência humana é por número, não por trecho. A concordância das categóricas só gera aviso no G7. Sem `04-qualidade/resultados_avaliados.csv`, o G7 só sabe quais resultados precisam de `rob_geral` pelos efeitos extraídos: numa revisão sem efeitos (qualitativa), escreva a lista.

## 6. Contagem de votos por significância

Sintoma: "6 de 8 estudos significativos"; "sem efeito" porque p > 0,05; "taxa de sucesso"; testes combinados como prova de consistência ou de tamanho.

- **Automática.** `efeitos.R` alinha o sinal por `direcao_desejada`; `swim.R` define a direção pelo estimador pontual e aplica teste de sinal binomial exato por direção; `testes_combinados.R` imprime a ressalva obrigatória e rotula Fisher como não direcional; `$RS caixa` ignora testes combinados e só dá Positivo/Negativo sem meta-análise com ≥ 5 estudos, ≥ 70% numa direção, p < 0,05, não só risco alto e certeza ≥ baixa.
- **Humana.** Redação por direção e IC; revisor metodológico (item S09) no G8; auditoria do texto no G9.
- **Lacuna.** Nenhum script lê a prosa do relatório.

## 7. Efeitos dependentes e dupla contagem

Sintoma: vários modelos do mesmo estudo tratados como independentes; relatos do mesmo estudo somados; meta-análise incluída ao lado dos seus primários.

- **Automática.** `meta.R` e `testes_combinados.R` saem com 2 (`status: dependencia_nao_resolvida`, `estudos_com_varios_efeitos`) quando um estudo tem vários efeitos sem um único `modelo_principal`; `swim.R` dá um voto por estudo; `preparar-efeitos` avisa modelos principais ausentes ou múltiplos; `--dependencia che` usa CHE + CR2 e marca `rve_confiavel` falso com gl < 4; o estudo é o `id_estudo` da ligação de relatos.
- **Humana.** Regra de modelo principal no protocolo, aplicada sem ver resultados; escolha de CHE e ρ antes da análise.
- **Lacuna.** Relatos do mesmo estudo não ligados continuam como estudos diferentes.

## 8. Conversões ou sinais errados

Sintoma: g com sinal trocado para desfechos em que "menos é melhor"; p de Mann-Whitney convertido como t; coeficiente de estimando local tratado como ATE; variância de cluster subestimada.

- **Automática.** `preparar-efeitos` recusa `direcao_desejada` fora de `aumentar|reduzir` e `tipo_estatistica` fora da lista; `efeitos.R` registra `formula_id`, `aproximado` e `sinal_alinhado` por linha, deixa fora da síntese linhas `sem_direcao`, não calcula F sem fonte de sinal, converte Mann-Whitney por z (r = z/√N), medianas com quartis por Wan et al., avisa estimandos ITT/LATE/ATT/RDD local e cluster sem ICC, e informa `formulas_sem_mapa` contra `assets/mapas/conversoes_efeito.csv`; `meta.R` roda a sensibilidade sem aproximados.
- **Humana.** Conferir as linhas `invertido` e todo aviso em `06-analise/efeitos.csv`; decidir se estimandos diferentes vão para células separadas.
- **Lacuna.** O script confia no sinal copiado do artigo; sinal errado na extração só aparece na conferência humana.

## 9. Agregação de evidência não comparável e heterogeneidade oculta

Sintoma: ensino básico e superior na mesma média; randomizados com não randomizados; I² no rodapé e "efeito consistente" no resumo; funil com 6 estudos.

- **Automática.** `meta.R`, `swim.R` e `combinados` separam randomizados e não randomizados por padrão; `meta.R` avisa estimandos diferentes, desenhos misturados e vários outcomes (`comparabilidade.avisos`), exige k ≥ `--k-min` (padrão 3), marca `tau2_interpretavel` (k ≥ 5), calcula PI, só roda funil/Egger/PET-PEESE/3PSM com k ≥ 10, subgrupo com k ≥ 3 por nível e meta-regressão com ~10 estudos por covariável. `$RS caixa` (`caixa-3`) só dá Misto com k ≥ 5, δ, PI além de ±δ e achado de moderador ou mecanismo com `explica_heterogeneidade` e CERQual ≥ baixa (senão, Inconclusivo), Nulo só com δ, IC em ±δ e certeza ≥ moderada, e resume os corpos por desenho numa linha de painel (maior certeza; empate = Inconclusivo).
- **Humana.** Checklist de comparabilidade por estudo (família, comparador, construto e janela, população, estimando, desenho); julgamento GRADE de inconsistência e indireção; linguagem guiada por τ e PI.
- **Lacuna.** Nenhum script julga se famílias, comparadores ou populações são comparáveis. A exclusão de não randomizados em risco crítico da análise principal (`--excluir-rob critico` em `analise meta`, `swim` e `combinados`) só vale se o protocolo a previu; nenhum script confere essa previsão.

## 10. Funil e relato não reprodutíveis

Sintoma: contagens digitadas que não fecham; protocolo alterado sem registro; declaração de IA escrita à mão; rótulo sem regra nem certeza.

- **Automática.** `$RS prisma` calcula do ledger e sai com 2 se as invariantes não fecham (sem desenhar), com NR para etapas ausentes e marca de rascunho com pendências; `$RS status` lista inconsistências (artefato congelado alterado ou ausente, contagens que não fecham, estado atrás do log, portão sem evento no log, portões fora de ordem); G2 congela `00-protocolo/` e mudança exige `$RS emenda --arquivo ... --motivo ...`; `$RS declaracao-ia` sai do log com hash; `$RS caixa` grava `regra_versao`, `fontes` e `assinatura` por linha, deixa Pendente a célula sem certeza e rascunho a linha sem `validado_humano`; `$RS portao G8` bloqueia com célula não definida, sem `06-analise/certeza.csv` (ou com célula de efeito sem linha de certeza) e, em OQF, sem caixa, e `$RS portao G9` sem PRISMA atualizado ou sem declaração de IA; o G2 bloqueia sem codebook v0, sem codebook de elegibilidade e com placeholders; todo escritor de estado e log usa trava entre processos (`seq` único mesmo com comandos em paralelo) e o `status` acusa `seq_repetido_no_log`; `analise_executada` registra entrada com hash e argumentos; `$RS pendencia fechar` só aceita ator humano.
- **Humana.** `00-protocolo/emendas.md` com cada desvio; checklists preenchidos com local no relato; reconferência dos números copiados para o `.qmd`.
- **Lacuna.** Fora do tipo OQF, o G8 não exige a caixa; o G9 só avisa (não bloqueia) sem `.bib` ou com declaração de IA anterior ao último evento relevante do log (conferida por `dados.ultimo_seq` do evento da declaração): o coordenador resolve os avisos antes de pedir aprovação.

## 11. Lições gerais

| Erro observado em projetos reais | Regra | Onde a skill ajuda |
|---|---|---|
| Junção de tabelas por título (várias linhas perdidas) | juntar só por `id_rs`, `id_registro` ou `chave` | todos os scripts; handoffs por `chave` |
| Critérios ou prompt mudados no meio da rodada | nova rodada vN+1; nunca sobrescrever saídas | `criterios_sha` nos lotes; G4 congela prompts |
| "Mencionar" X confundido com "analisar" X | critérios com exemplos VÁLIDO/INVÁLIDO | `agentes/triador-ta.md` |
| Instrução antes de texto longo na API | instrução depois do texto | `triagem api` |
| Texto completo truncado perde resultados | leitura em faixas de até 20 páginas, cobertura registrada | prompts dos agentes (`faixas_lidas`) |
| Parâmetro rejeitado pelo modelo derruba a rodada | omitir `temperature` onde não é aceito | `provedores.py` |
| PDF escaneado ou PDF de outro artigo | inventário e verificação de conteúdo antes de fichar | `textos inventario`; `verificacao_conteudo.csv` |
| Decisões unânimes da IA nunca checadas | amostra estratificada e elusão | `validar amostrar`, `validar elusao` |
| Contagens do funil não persistidas | ledger append-only e PRISMA calculado | `dados/decisoes.jsonl`, `prisma` |
| "Não revisado" contado como excluído no κ | NA fora das contas | `validar calcular` |
| Resumo de subagente tomado como prova | só `mesclar`, gates e checagens confirmam | `$RS status` depois de cada onda |
| Edição manual de `rs_estado.json`, `rs_log.jsonl` ou `decisoes.jsonl` | proibido | `status` detecta portão sem evento e log atrás do estado; estado corrompido sai com código 1 e a dica de restaurar do git |
| Comandos do mesmo projeto em paralelo perdendo eventos e pendências | trava entre processos em todo escritor | `.rs.lock`; `seq_repetido_no_log` no `status` |
| Fila humana salva pelo Excel com ponto e vírgula e regravada vazia | ler `;`, tab e `.xlsx`; nunca regravar fila com decisões não aplicadas | `triagem override`, `triagem consolidar` (`fila_preservada`) |
| `status` na pasta-mãe criando projeto por cima do existente | procurar projeto em subpastas | `projetos_em_subpastas`; `init` recusa |
| `$RS` definido como variável e falhando no zsh | função `rs` ou caminho completo | SKILL.md, "Como chamar os comandos" |
| Autopiloto aprovando pergunta ou protocolo | G1 e G2 sempre humanos | `portao` sai com 2 |
| Marca de rascunho removida com pendência aberta | só com `pendencia listar` vazio e produtos regenerados | `rascunho` e `motivos_rascunho` em `status`; `rascunho` em `prisma`, `caixa`, `declaracao-ia`; G9 compara as pendências com as do último `prisma` |
| Faixa de magnitude ou δ escolhidos depois dos dados | fixar no protocolo | `meta.R` registra `delta_fonte`; `caixa --faixas` |
| Chaves de API em código ou arquivos do projeto | só variáveis de ambiente; estado guarda booleanos | `ambiente`; nunca ler `.env` |
