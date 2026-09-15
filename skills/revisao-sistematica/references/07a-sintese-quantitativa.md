# 07a — Síntese quantitativa: comparabilidade, meta-análise, SWiM e testes combinados

Etapa 10 (parte quantitativa), fechada no portão **G8** junto com a parte qualitativa, a certeza e a caixa de ferramentas (leia também references/07b-sintese-qualitativa-integracao.md).

## Sumário

1. Entradas, saídas e pré-requisitos
2. Checklist de comparabilidade
3. Decisão por célula: meta-análise, SWiM ou só tabela
4. Números mínimos de estudos
5. Passos com comandos
6. Dependência de efeitos
7. Leitura do `meta_resumo.json`
8. Viés por resultados faltantes
9. Sensibilidade
10. SWiM e `swim_resumo.json`
11. Testes combinados (só secundários)
12. O que perguntar ao usuário
13. O que o G8 exige da parte quantitativa
14. Armadilhas e o que registrar

`$RS` abrevia `python3 "<pasta da skill>/scripts/rs.py"` (SKILL.md, "Como chamar os comandos"): em cada chamada de Bash, use a função `rs` definida na mesma chamada ou o caminho completo, nunca uma variável `RS`. Códigos de saída de todos os comandos: 0 ok; 1 erro de uso/dados; 2 checagem metodológica falhou; 3 dependência ausente (R ou pacote).

## 1. Entradas, saídas e pré-requisitos

| Item | Onde | Como conferir | Se falhar |
|---|---|---|---|
| G7 aprovado | log | `$RS status` → `etapas.09_extracao_rob.status = concluida` | voltar à etapa 9 (extração e RoB) |
| Efeitos verificados na página | `05-decomposicao/verificacao_efeitos.csv` | `$RS analise verificar-efeitos` → `pode_seguir_g7: true`; `analise efeitos` avisa se há `apto_g7` falso | síntese sai como rascunho; abrir pendência no autopiloto |
| `direcao_desejada` em toda linha | `05-decomposicao/efeitos_extraidos.csv` | `preparar-efeitos` recusa linha sem `aumentar`/`reduzir` | corrigir o CSV do extrator e rodar de novo |
| Regra de modelo principal | protocolo | avisos em `05-decomposicao/efeitos_preparacao_avisos.csv` (campo `modelo_principal`) | marcar pela regra do protocolo ou planejar CHE |
| δ (SESOI) e faixas de magnitude | protocolo congelado no G2 | ler o plano de síntese | perguntar ao usuário e registrar com `$RS emenda` |
| R com `metafor` (e `clubSandwich` para CHE) | ambiente | `$RS ambiente` | sem `metafor`: só SWiM; sem R: sem síntese quantitativa (quali, caixa com `certeza.csv` e PRISMA seguem) |

Saídas (todas em `06-analise/`, cada execução registra `analise_executada` no log): `efeitos.csv`, `meta_resumo.json`, `swim_resumo.json`, `testes_combinados.json`, `tabelas/` (`meta_grupos.csv`, `loo_<grupo>.csv`, `swim_direcao.csv`, `testes_combinados*.csv`) e `figuras/` (`forest_<grupo>.png|pdf`, `funil_<grupo>.png`, `direcao_efeito.png|pdf`, `albatross_<grupo>.png`).

## 2. Checklist de comparabilidade (antes de qualquer modelo)

Responder por estudo, numa tabela manual `06-analise/tabelas/comparabilidade.csv` (nenhum script a lê; vai para o apêndice e para o revisor metodológico). Norma: Cochrane Handbook v6.5 cap. 10 (MECIR C62) e cap. 24.

| Dimensão | Pergunta por estudo | Checagem automática existente | Decisão humana |
|---|---|---|---|
| Família de intervenção | mesmo mecanismo e intensidade comparável? | nenhuma; agrupar com `--grupo familia_intervencao,construto_outcome` | definir famílias no protocolo |
| Comparador | o controle recebe o mesmo (nada, versão fraca, outra política)? | nenhuma | separar células se diferir |
| Construto e janela do desfecho | mesmo construto, mesma medida, mesma distância temporal? | `meta.R` avisa "vários outcomes no mesmo construto" em `comparabilidade.avisos` | separar construtos ou justificar |
| População e cenário | dentro do PICOC? populações que o protocolo separa? | nenhuma | células separadas (ex.: educação básica × superior) |
| Estimando | ATE, ITT, LATE, ATT, RDD_local? | `efeitos.R` avisa estimando local em `beta_sd`; `meta.R` avisa "estimandos diferentes" | analisar em separado ou em sensibilidade |
| Desenho | randomizado × não randomizado | `meta.R`, `swim.R` e `combinados` separam por padrão; campo `classe_desenho` do grupo = `randomizado`, `nao_randomizado` ou `desenho_nao_informado` | nunca `--separar-desenho nao` na análise principal |
| Tipo de documento | estudo primário? | `preparar-efeitos` recusa revisão/meta-análise; `efeitos.R` marca `formula_id = rejeitado_revisao`; `meta/swim/combinados` excluem | revisão vai para a bola de neve |
| Risco de viés crítico (não randomizados) | ROBINS-I crítico? | `analise meta --excluir-rob critico` tira da análise principal as linhas com `rob_geral` crítico (exige a coluna; a análise com elas vira `sensibilidade.com_rob_critico`) | se o protocolo prevê: use `--excluir-rob critico` em `analise meta`, `analise swim` e `analise combinados` (mesmo contrato: a escolha do efeito, da direção ou do p do estudo vem antes da exclusão; a análise com os críticos fica em `sensibilidade.com_rob_critico`); o estudo continua incluído na revisão |

`desenho_nao_informado` é uma classe à parte: preencha `desenho` em `efeitos_extraidos.csv` antes de analisar.

## 3. Decisão por célula

Célula = família de intervenção × construto de desfecho × classe de desenho.

| Situação da célula | Caminho | Comando |
|---|---|---|
| k ≥ 3 estudos com `yi`/`vi` calculados, comparáveis, um efeito por estudo ou dependência modelada | meta-análise REML + HKSJ modificado **e** SWiM (a caixa usa a meta-análise quando `k ≥ --k-min`) | `analise meta` + `analise swim` |
| k < 3, EP não confiável (cluster ignorado), métricas não conversíveis | SWiM: direção pelo estimador, teste de sinal, effect direction plot | `analise swim` |
| só p e n com direção | SWiM (albatross plot sai sozinho) e, se previsto no protocolo, testes combinados | `analise swim`; `analise combinados` |
| só direção | SWiM | `analise swim` |
| nenhum dado de direção | tabela estruturada; rótulo final Inconclusivo | — |

Nomeie o método no relato. "Síntese narrativa" sem método não é aceitável (Cochrane Handbook v6.5 cap. 12).

## 4. Números mínimos de estudos

| Análise | Mínimo | Como o script aplica |
|---|---|---|
| Agregar | k ≥ 3 | `--k-min 3` (padrão); grupo abaixo sai `status: k_insuficiente`. O script aceita `--k-min 2`: não use sem emenda |
| Interpretar τ², IC de τ², I² e intervalo de predição (PI) | k ≥ 5 | `resultado.tau2_interpretavel` (false com k < 5); abaixo disso relate, não interprete. A regra Misto da `caixa` (`caixa-3`) exige k ≥ 5 e `tau2_interpretavel` diferente de false; com explicação alegada e k < 5, a célula sai Inconclusivo (`inconclusivo_misto_nao_sustentado`) |
| Estimativa dentro de subgrupo | k ≥ 3 por nível | `moderadores.individuais.<m>.motivo = "subgrupo exige k >= 3 por nível"` |
| Teste de diferença entre subgrupos | ≥ 4 estudos por nível e ~10 por característica | não checado: abaixo disso, estimativas lado a lado sem teste |
| Meta-regressão contínua | ~10 estudos por covariável | `motivo = "meta-regressão exige ~10 estudos por covariável"`; modelo conjunto exige 10 × gl |
| Funil, Egger, PET-PEESE, 3PSM | k ≥ 10 | `vies_publicacao.executado = false` com k < 10 |
| CHE + RVE confiável | gl de Satterthwaite ≥ 4 | `resultado.rve_confiavel`, `resultado.aviso_rve` |
| Rótulo sem meta-análise | ≥ 5 estudos, ≥ 70% numa direção, p < 0,05, não só risco alto (convenção da especificação, declarada no protocolo com a versão da regra) | `swim_resumo.json` → `insumos_regra_caixa`; decisão em `$RS caixa`. O teste de sinal é exato e bilateral: p < 0,05 exige na prática ≥ 6 estudos na mesma direção (6/6; 5/5 dá p = 0,0625; 8/9 é o primeiro com um discordante) |

## 5. Passos com comandos

1. `$RS status`. Confirme G7 e leia `proxima_acao`.
2. Consolidar e verificar (se ainda não feito no G7): `$RS analise preparar-efeitos --master <fichamentos_master.csv> --codebook <codebook.csv>` e `$RS analise verificar-efeitos`.
3. **Família e `rob_geral`**: a entrada da síntese é `05-decomposicao/efeitos_para_sintese.csv`, gerada pelo bloco da seção 8 de references/06-decomposicao.md (família do master por `chave`; `rob_geral` de `04-qualidade/rob_geral.csv`, gravado por `qualidade consolidar` na fase 2, por `chave` × `construto_outcome`, porque o RoB é por resultado), que também grava `05-decomposicao/master_caixa.csv` para a caixa. `preparar-efeitos` preserva colunas extras do extrator (quartis, `g`/`d`, moderadores) e `efeitos.R` as leva a `06-analise/efeitos.csv`, mas o RoB consolidado não tem comando de junção: refaça o bloco a cada `preparar-efeitos`. Sem esse arquivo não há `rob_geral`: `sensibilidade.sem_alto_risco` fica sem dado, `so_risco_alto` do SWiM sai nulo e `--excluir-rob critico` sai com 1. Com uma só família e sem RoB por resultado, pode seguir com `efeitos_extraidos.csv` (a caixa herda a família única de `certeza.csv`), declarando a lacuna.
4. Tamanho de efeito: `$RS analise efeitos --in 05-decomposicao/efeitos_para_sintese.csv` (ou sem `--in`, padrão `05-decomposicao/efeitos_extraidos.csv`). Leia `resumo_r`:

   | Campo | Ação obrigatória |
   |---|---|
   | `n_rejeitados_revisao` > 0 | confirmar que são revisões; nunca reincluir |
   | `n_sem_calculo` > 0 | ler `aviso` em `06-analise/efeitos.csv`; completar dados ou deixar fora com motivo |
   | `n_sem_direcao` > 0 | linha fica fora da síntese até declarar `direcao_desejada` |
   | `n_g_maior_2` > 0 | reconferir na página (EP lido como DP, unidade, sinal) |
   | `n_aproximados` > 0 | sensibilidade sem aproximados é obrigatória no relato |
   | `formulas_sem_mapa` não vazio | parar: fórmula sem linha em `assets/mapas/conversoes_efeito.csv` |
   | `n_nao_verificados_humano` > 0 | síntese é rascunho |
   | `n_invertidos` | conferir: `yi > 0` sempre = benéfico depois do alinhamento |
   | `por_formula` com `dif_prop_lpm` ou `rr_logit` | desfechos binários convertidos a d pelo log OR com `p0` (Chinn 2000; RR por Zhang e Yu 1998): aproximados, entram na sensibilidade sem aproximados; efeitos de RDD e LATE são locais (analisar separado ou em sensibilidade) |

5. Meta-análise: `$RS analise meta --grupo familia_intervencao,construto_outcome --delta <δ do protocolo> [--excluir-rob critico] [--moderadores m1,m2] [--k-min 3] [--dependencia um_por_estudo|che] [--rho 0.6]`. Saída 2 = algum grupo com `status: dependencia_nao_resolvida` (seção 6). `--excluir-rob critico` sem a coluna `rob_geral`, ou com valor diferente de `nenhum`/`critico`, sai com 1.
6. SWiM, sempre: `$RS analise swim --grupo familia_intervencao,construto_outcome [--excluir-rob critico] [--limiar-consistencia 0.7] [--nivel 0.95]` (com `--excluir-rob critico` se a meta-análise usou a flag, para as duas análises principais terem o mesmo conjunto).
7. Testes combinados, só se o protocolo previu: `$RS analise combinados --grupo familia_intervencao,construto_outcome [--excluir-rob critico]` (seção 11).
8. Ler os JSON (seções 7 a 10), preencher a tabela de sensibilidade e seguir para certeza e caixa (references/07b-sintese-qualitativa-integracao.md).
9. `$RS status` depois de cada rodada. Reexecutar com a mesma entrada e os mesmos argumentos registra `reexecucao: true`, sem duplicar dados.

Outros argumentos do R passam por `--r-arg --nome=valor` (repetível). Use só para opções que existem nos scripts R.

## 6. Dependência de efeitos

| Situação | Ação | Onde conferir |
|---|---|---|
| Um efeito por estudo | padrão `--dependencia um_por_estudo` | `n_descartados_nao_principais` |
| Estudo com vários efeitos e exatamente um `modelo_principal = sim` na célula | o script usa o principal | idem |
| Vários efeitos sem principal único | `status: dependencia_nao_resolvida`, `estudos_com_varios_efeitos`, saída 2. Marque o principal pela regra do protocolo (nunca pelo resultado) ou use CHE | `meta_resumo.json` |
| A pergunta exige todos os efeitos (vários desfechos, momentos, subgrupos) | `--dependencia che --rho 0.6`: `rma.mv` estudo/efeito + CR2 (Satterthwaite) | `resultado.rve_confiavel`, `aviso_rve`, `sensibilidade.rho` (ρ = 0,2; 0,5; 0,8) |
| Relatos do mesmo estudo | `id_estudo` vem de `$RS textos ligar-relatos`; sem ele o estudo é a `chave` | coluna `id_estudo` de `efeitos.csv` |

Regras: escolher o modelo de dependência antes de ver resultados; não comparar CHE e um-por-estudo para escolher; gl < 4 = inferência não confiável (reportar, não usar para rótulo sem ressalva). No CHE, o viés de publicação usa efeitos agregados por estudo.

## 7. Leitura do `meta_resumo.json`

Topo: `parametros` (grupo, separar_desenho, dependencia, rho, k_min, delta, `delta_fonte`, `excluir_rob`, moderadores, versão do `metafor`), `linhas_excluidas` (`rejeitado_revisao`, `sem_efeito_calculado`, `sem_direcao`), `n_excluidos_rob_critico`, `contrato_campos` (definição de `ic_dentro_delta` e `pi_cobre_beneficio_e_dano`), `ressalvas`, `grupos[]`. `tabelas/meta_grupos.csv` traz `n_excluidos_rob_critico` por grupo.

| Campo do grupo | Leitura |
|---|---|
| `grupo`, `familia_intervencao`, `construto_outcome`, `classe_desenho` | identidade da célula (a caixa junta por família + construto + classe, sem acento e sem caixa) |
| `status` | `meta_ajustada`, `k_insuficiente`, `dependencia_nao_resolvida` ou `erro_ajuste` (ver `motivo`) |
| `comparabilidade.avisos` | todo aviso precisa de resposta escrita no checklist |
| `k_estudos`, `k_efeitos`, `estudos` | k para as regras da seção 4; `estudos` = chaves |
| `resultado.modelo` | "efeitos aleatórios REML + HKSJ modificado (metafor test='adhoc')" ou CHE |
| `resultado.estimativa`, `ep`, `ic`, `p`, `gl` | g de Hedges alinhado (positivo = benéfico), IC com t de k − 1 gl |
| `resultado.tau2`, `tau2_ic`, `tau`, `I2`, `I2_ic`, `Q`, `Q_gl`, `Q_p` | heterogeneidade; interprete por τ e PI na escala do efeito, não por faixas de I² |
| `resultado.pi` (`ip_inf`, `ip_sup`), `pi_gl` | PI com t de k − 2 gl; só com k ≥ 3; interpretar só com `tau2_interpretavel` |
| `resultado.ic_exclui_zero`, `direcao` | insumo, não rótulo |
| `resultado.pi_cobre_beneficio_e_dano`, `pi_referencia` | com `--delta` > 0: PI vai de ≤ −δ a ≥ +δ (`pi_referencia = delta`, o mesmo critério da regra Misto da caixa); sem δ: PI cruza zero (`pi_referencia = zero`); `null` sem PI |
| `resultado.ic_dentro_delta` | `true` se −δ ≤ IC inferior e IC superior ≤ δ (limites inclusivos, igual à regra Nulo da caixa); `null` sem `--delta`: equivalência não se decide depois de ver os dados |
| `excluidos_rob_critico` | com `--excluir-rob critico`: `n_linhas`, `estudos`, `n_sem_rob_geral`, `nota` |
| `sensibilidade.*` | seção 9 |
| `vies_publicacao.*` | seção 8 |
| `moderadores.individuais.<m>` | `executado`, `motivo`, `QM`, `QM_p` (teste formal), `R2`, `coeficientes`, `subgrupos[]`; `moderadores.conjunto` |

Uma frase por célula no relato: k, estimativa (IC 95%), τ², τ, I², PI, estudos, risco de viés. Direção pelo estimador; nunca "sem efeito" porque p > 0,05.

## 8. Viés por resultados faltantes

| k | O que o script faz | O que relatar |
|---|---|---|
| < 10 | `vies_publicacao.executado = false` | "Com menos de dez estudos, não testamos assimetria." |
| ≥ 10 | `funil` (figura), `egger` (estatística, p, estimativa-limite, `preditor`), `pet_peese` (`variante`, `metodo`, `preditor`, `gl`, intercepto, EP, t e p do PET e do PEESE, `pet_p_unilateral`, `escolhido`, `estimativa_corrigida`, `regra`), `selecao_3psm` (`estimavel`, `lrt_p`, `avisos`) | estimativas como faixa de sensibilidade, nunca como estimativa principal |

Preditor de precisão (`vies_publicacao.preditor_precisao`, com `nota_preditor`): quando todos os estudos do grupo têm `n1` e `n2`, Egger e PET-PEESE usam o EP modificado √((n1+n2)/(n1·n2)) de Pustejovsky e Rodgers (`ep_modificado_smd`), que não depende do próprio g; os pesos continuam 1/vi. Se algum estudo não tem `n1`/`n2`, o script volta ao EP de g (`sei`), que infla o erro tipo I com SMD: leia com cautela e diga isso no relato. O PET-PEESE usa a variante WLS de Stanley e Doucouliagos (2014): `lm(yi ~ EP)` (PET) e `lm(yi ~ EP²)` (PEESE) ponderados por 1/vi, com erro multiplicativo (os EP dos coeficientes são escalados pela variância residual) e teste t com k − 2 gl (`gl`, `pet_t` no JSON); não é `rma(method = "FE")`, que fixa a escala em 1 e usa z, e as duas variantes podem divergir perto do corte. Quem reproduzir à parte usa a mesma variante. A regra segue os mesmos autores: PEESE só quando o intercepto do PET é positivo (benéfico, porque `yi` está alinhado) e tem p unilateral < 0,05 (`pet_p_unilateral`; equivale a p bilateral < 0,10 no sentido benéfico); intercepto negativo, mesmo com p bilateral < 0,10, fica com o PET. Em qualquer caso, dê peso ao julgamento humano ROB-ME (Cochrane Handbook v6.5 cap. 13), que alimenta o domínio "viés de publicação" do GRADE.

## 9. Sensibilidade

| Análise | Sai automaticamente? | Onde | Exigência |
|---|---|---|---|
| Leave-one-out | sim (k ≥ 3) | `sensibilidade.leave_one_out` (`estudos_que_mudam_conclusao`), `tabelas/loo_<grupo>.csv` | listar estudos que mudam a conclusão |
| Sem conversões aproximadas | sim, se houver `aproximado = 1` | `sensibilidade.sem_aproximados` | obrigatória quando `n_aproximados > 0` |
| Sem risco de viés alto/crítico | só se `efeitos.csv` tiver `rob_geral` (passo 3) | `sensibilidade.sem_alto_risco` | obrigatória; sem a coluna, `motivo = "coluna rob_geral ausente"` é lacuna a registrar |
| Com os críticos | só com `--excluir-rob critico` (`meta`, `swim`, `combinados`) | `sensibilidade.com_rob_critico` em cada grupo do JSON (meta: `resumo_curto`, `n_incluidos`) | relatar ao lado da principal sem críticos |
| ρ no CHE | sim com `--dependencia che` | `sensibilidade.rho` | relatar a faixa |
| Randomizados e não randomizados juntos | só com `--separar-desenho nao` e `--out-dir` separado | JSON próprio | nunca como análise principal |
| Outro estimador de τ², IC de Wald | não (não há opção nos scripts) | — | se o protocolo previu, declarar como não executado (limitação) ou rodar à parte com `metafor` sobre `06-analise/efeitos.csv` e arquivar o script em `06-analise/` |

Cada sensibilidade que sai com `executado: false` e `motivo: "k restante (...) < k-min"` é relatada como não informativa.

## 10. SWiM e `swim_resumo.json`

Regras do script: direção pelo estimador pontual alinhado; um voto por estudo (principal; sem ele, ≥ `--limiar-consistencia` dos efeitos numa direção, senão "misto" e fora do teste); teste de sinal binomial exato bilateral com IC de Clopper-Pearson.

| Campo do grupo | Leitura |
|---|---|
| `k_estudos` | estudos no grupo |
| `n_estudos` | estudos com direção definida (entram no teste) |
| `n_beneficos`, `n_danosos`, `n_mistos`, `n_nulos`, `n_sem_direcao` | contagem por direção |
| `proporcao_benefica`, `ic_proporcao`, `p_sinal` | resultado do teste de sinal |
| `so_risco_alto` | `null` sem `rob_geral`; `true` bloqueia Positivo/Negativo na caixa (o `rob_geral` do estudo é o do modelo principal) |
| `excluidos_rob_critico`, `sensibilidade.com_rob_critico` | com `--excluir-rob critico`: estudos críticos tirados depois de decidida a direção e a contagem com eles; no topo, `parametros.excluir_rob` e `n_excluidos_rob_critico`; `tabelas/swim_direcao.csv` com `excluido_rob_critico` |
| `insumos_regra_caixa` | `atinge_k`, `atinge_proporcao_benefica`, `atinge_proporcao_danosa`, `p_menor_005` (não é rótulo) |
| `estudos`, `albatross` | chaves; figura quando há só p e n |

Figuras: `figuras/direcao_efeito.png|pdf` (linhas = estudos, colunas = grupos, cor = risco de viés; com `--excluir-rob critico`, só a análise principal). Redação: "7 de 8 estudos com estimativa na direção benéfica (88%; IC 95% ...; teste de sinal p = ...)". Nunca "7 estudos significativos". Relato pelos 9 itens do SWiM: `assets/checklists/swim.csv`.

## 11. Testes combinados (só secundários)

Use só quando o protocolo previu e não há estimativas com EP para meta-analisar. Um p por estudo: sem principal único, `status: dependencia_nao_resolvida` e saída 2.

| Teste em `testes_combinados.json` | O que responde | Campos |
|---|---|---|
| `stouffer_ponderado` | evidência na direção declarada, pesos √n | `Z`, `p_unilateral`, `k`, `k_sem_n` |
| `winer` | idem com t e gl > 2 | `Z`, `p_unilateral`, `k_t_reconstruido`, `k_excluidos_gl` |
| `cooper_teste_de_sinal` | proporção benéfica ≠ 0,5 | `proporcao_benefica`, `ic`, `p_bilateral` |
| `fisher_nao_direcional` | algum estudo com efeito em qualquer direção | `X2`, `gl`, `p`, `rotulo` |

Com `--excluir-rob critico`, o p de cada estudo é escolhido antes da exclusão, os testes com os críticos ficam em `sensibilidade.com_rob_critico` e `tabelas/testes_combinados_estudos.csv` marca `excluido_rob_critico`. A ressalva impressa pelo script (também em `ressalva` no JSON) vai inteira no texto, junto do resultado. Os testes nunca definem rótulo: `$RS caixa` os ignora. Nunca descreva como "escala" ou "tamanho" do efeito nem como "consistência".

## 12. O que perguntar ao usuário

- δ (menor efeito de interesse) e faixas de magnitude do campo, se o protocolo não fixou: sem δ não há rótulo Nulo; sem faixas a escala sai "faixas não declaradas". Registrar por emenda.
- Regra de modelo principal para cada estudo com várias estimativas, ou se prefere CHE (e qual ρ).
- Moderadores pré-especificados (com direção esperada) e populações que viram células separadas.
- Se os testes combinados estão no protocolo; se não, não rodar.
- Como tratar não randomizados em risco crítico e estudos com cluster sem ICC.

## 13. O que o G8 exige da parte quantitativa

`$RS portao G8` sai com código 2 se alguma linha de `06-analise/caixa_ferramentas.csv` tem `status_rotulo` diferente de `definido` (tipo certeza), se falta `06-analise/certeza.csv` (artefato; salvo escopo, mapa e realista sem caixa), se alguma célula de efeito da caixa não tem linha de certeza (certeza), se falta a caixa numa revisão `oqf_mista_sequencial` (artefato) ou se há pendência aberta da etapa 10 ou do G8, e avisa (sem bloquear) grupos de `meta_resumo.json` com `status` `dependencia_nao_resolvida` ou `erro_ajuste` e, quando a etapa 09 está ignorada (projeto parcial `meta`, sem G7), efeitos calculados sem `verificado_humano` (`n_nao_verificados_humano` do último `analise efeitos`). As condições abaixo **não** são checadas pelo script e o coordenador as confere antes de pedir a aprovação:

- checklist de comparabilidade respondido; nenhum grupo misturando desenhos;
- `formulas_sem_mapa` vazio; `n_g_maior_2` conferido; linhas sem direção justificadas;
- nenhum grupo `dependencia_nao_resolvida` nem `erro_ajuste` sem explicação;
- k mínimos da seção 4 respeitados; τ²/PI interpretados só com k ≥ 5; viés de publicação só com k ≥ 10;
- sensibilidades da seção 9 relatadas (ou lacuna declarada);
- testes combinados, se houver, com ressalva e fora dos rótulos;
- `agentes/revisor-metodologico.md` rodado com `{PORTAO}=G8` e `{SAIDA}=06-analise/revisao_metodologica_g8.md`; `grep -c '^### R[0-9]* \[CRITICO\]' 06-analise/revisao_metodologica_g8.md` = 0 ou cada crítico resolvido.

Checkpoints: mostre ao usuário células, k, estimativas, PI, sensibilidades e avisos; aguarde. Aprovação: `$RS portao G8 --aprovar --por revisor_humano_1 --criterios '{"grupos_meta": N, "dependencia_nao_resolvida": 0, "k_min": 3, "revisor_metodologico_criticos": 0}'`. Autopiloto: `$RS portao G8 --aprovar --por autopiloto` abre pendência `revisao_humana_portao`; produtos saem com "RASCUNHO NÃO VALIDADO".

## 14. Armadilhas e o que registrar

| Armadilha | Prevenção |
|---|---|
| Revisão ou meta-análise como estudo | bloqueada em `preparar-efeitos` e `efeitos.R`; conferir `n_rejeitados_revisao` |
| Randomizados com não randomizados | padrão separa; não usar `--separar-desenho nao` na principal |
| Escolher o modelo principal depois de ver resultados | regra do protocolo; divergência vira emenda |
| I² como heterogeneidade absoluta; "consistente" com PI cruzando zero | relatar τ e PI; linguagem guiada pelo PI |
| Estimativa "corrigida" por viés de publicação como principal | só sensibilidade |
| Faixa de magnitude escolhida depois | faixas no protocolo e em `$RS caixa --faixas` |
| `rob_geral` e família ausentes da entrada da síntese | passo 3 (junção da seção 8 de references/06-decomposicao.md) |
| Não randomizados críticos na análise principal sem previsão | `--excluir-rob critico` só se o protocolo previu; senão, só sensibilidade |
| SWiM com críticos e meta-análise sem eles | a mesma flag nas duas análises principais |
| PET-PEESE refeito à parte com `rma(method = "FE")` | a variante do script é WLS com t e k − 2 gl; declare a variante |

Registrar no relato (PRISMA 2020): item 12 (métrica: g alinhado), 13a (regra de agrupamento e checklist), 13b (conversões com `formula_id`, aproximados), 13c (tabelas e figuras), 13d (modelo, estimador, IC, PI, dependência, `metafor` com versão de `parametros.pacotes`), 13e (moderadores e teste), 13f (sensibilidades), 14 (ROB-ME e limiar k ≥ 10), 19, 20a–20d, 21; SWiM 1–9 quando houver síntese sem meta-análise.
