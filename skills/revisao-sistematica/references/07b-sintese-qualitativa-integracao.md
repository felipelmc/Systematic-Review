# 07b — Síntese qualitativa, integração, certeza e caixa de ferramentas

Etapa 10 (parte qualitativa, integração, GRADE/CERQual, caixa e EtD), fechada no portão **G8**.

## Sumário

1. Entradas, saídas e divisão de trabalho
2. Escolha do método qualitativo
3. Quem decide o quê
4. Síntese temática e best-fit com o subagente `sintetizador-quali`
5. Meta-etnografia, realista e QCA
6. Integração sequencial-explicativa e joint display
7. Certeza GRADE por célula de efeito
8. Confiança CERQual por achado; CMOC e QCA sem níveis
9. Formato exato de `06-analise/certeza.csv`
10. `$RS caixa`: regras `caixa-3`, painel, entradas e leitura
11. Da evidência à prática: EtD-lite, transferibilidade, implicações
12. O que o G8 exige e o que perguntar
13. Armadilhas e o que registrar

`$RS` abrevia `python3 "<pasta da skill>/scripts/rs.py"` (SKILL.md, "Como chamar os comandos"): em cada chamada de Bash, use a função `rs` definida na mesma chamada ou o caminho completo, nunca uma variável `RS`.

## 1. Entradas, saídas e divisão de trabalho

Entradas: `fichamentos_master.csv` do `fichamento-sistematico` (colunas `ficha_id`, `citekey`, classificador como `tipo_estudo` se houver, e pares `<variavel>` / `<variavel>__evidencia` com trecho e página); `06-analise/meta_resumo.json` e `swim_resumo.json` (parte quantitativa); protocolo com método qualitativo por pergunta, quadro a priori (teoria do programa/DAG), δ, faixas de magnitude, regra da caixa com versão e ordem, fatores de transferibilidade.

| Arquivo | Quem escreve | Script lê? |
|---|---|---|
| `06-analise/quali/quadro_apriori.md` | coordenador a partir do DAG; humano aprova | não |
| `06-analise/quali/<tema>_codigos.csv` e `<tema>_temas.md` | subagente `agentes/sintetizador-quali.md` | não (conferência na seção 4) |
| `06-analise/joint_display.csv` | coordenador + humano | não |
| `06-analise/certeza.csv` | humano; LLM só rascunha com `validado_humano` vazio (a linha sai `rascunho` na caixa) | `$RS caixa` |
| `06-analise/caixa_ferramentas.csv` e `.md` | `$RS caixa` | relatório (include) |
| `06-analise/etd.md` | humano, com rascunho do coordenador | não |

## 2. Escolha do método qualitativo

| Pergunta ou situação | Método | Produto | Não usar quando | Relato | Suporte na skill |
|---|---|---|---|---|---|
| Barreiras, facilitadores, visões de atores sobre política definida | síntese temática | temas descritivos e analíticos | objetivo é teoria nova de literatura interpretativa ampla | ENTREQ | `sintetizador-quali` |
| Já há teoria do programa/DAG (padrão OQF) | best-fit framework synthesis | quadro revisado + temas livres | não há quadro plausível | ENTREQ | `sintetizador-quali` com `{QUADRO}` |
| Gerar conceitos novos de literatura interpretativa | meta-etnografia | traduções recíproca/refutacional, linha de argumento | integrar quali e quanti ao mesmo tempo; equipe sem experiência | eMERGe | só orientação (seção 5) |
| Contar categorias a priori em muitos documentos | análise de conteúdo dedutiva | frequências com exemplos | frequência lida como importância | livro de códigos + confiabilidade | codebook no `fichamento-sistematico` |
| Intervenção complexa dependente de contexto | síntese realista | CMOCs e teoria refinada | interesse é só o efeito médio | RAMESES | orientação; iterativa completa fora da v1 |
| Heterogeneidade entre intervenções complexas com variação no desfecho | QCA como síntese | configurações suficientes | < 10 estudos com > 2–3 condições; desfecho sem variação | padrões de QCA | orientação; QCA computacional fora da v1 |
| Avaliação de política no formato OQF | integração sequencial-explicativa | caixa com rótulos rastreáveis | não há síntese de efeito que gere enigmas | PRISMA 2020 + SWiM + ENTREQ | seções 6–10 |

## 3. Quem decide o quê

| Tarefa | LLM/subagente pode | Decisão humana |
|---|---|---|
| Codificação linha a linha | propor códigos com trecho verbatim, `ficha_id` e página | auditar amostra, fundir códigos, fixar temas descritivos |
| Temas analíticos | listar candidatos marcados "PROPOSTO" | formular, revisar em ciclos, aprovar |
| CMOCs | extrair trechos candidatos a C, M, O | retrodução, formulação e status |
| Calibração de QCA | levantar distribuições e âncoras candidatas | fixar âncoras e rubrica com justificativas |
| GRADE e CERQual | organizar evidência por domínio/componente com trechos | julgar, com duas pessoas, e assinar `certeza.csv` |
| Rótulos da caixa | rodar `$RS caixa` | revisar exceções e aprovar o G8 |

## 4. Síntese temática e best-fit com o `sintetizador-quali`

1. `$RS status`. Confirme o master consolidado e o gate de citações do `fichamento-sistematico` aprovado.
2. Liste os temas (um por dimensão da caixa ou pergunta) e as colunas do master de cada um. No codebook `oqf_decomposicao`: mecanismo = `mecanismo_id`, `mecanismo_tipo_evidencia`, `mecanismo_descricao`; moderador = `moderador_id`, `moderador_descricao`, `het_metodo`, `het_pre_especificada` (e `equidade_progress_plus` para a lente de equidade); percepção = `percepcao_id`, `percepcao_descricao`; implementação = `impl_*`, `implementacao_descricao`; custo = `custo_id`, `custo_unitario`; efeitos não intencionais = `efeitos_nao_intencionais`; estudos a1 = `a1_categorias_emergentes`, `a1_citacao_ilustrativa`. Cada uma tem o par `<variavel>__evidencia`. Confira no codebook do projeto, que pode ter sido ajustado.
3. Best-fit: escreva `06-analise/quali/quadro_apriori.md` com um conceito por nó do DAG (id `Q01`..., definição, quando aplicar, quando não aplicar). Humano aprova antes da codificação.
4. Liste `ficha_id` de revisões e meta-análises (por `tipo_publicacao`, desenho ou nota do fichador): elas não sustentam achado.
5. Despache um subagente NOVO por tema (até 3 em paralelo) com `agentes/sintetizador-quali.md`, preenchendo `{MASTER}`, `{CODEBOOK}`, `{TEMA}`, `{VARIAVEIS}`, `{QUADRO}` (ou `nenhum`), `{EXCLUIR_FICHAS}`, `{SAIDA_CODIGOS}`, `{SAIDA_TEMAS}`. O coordenador não abre o master nem as saídas além da conferência abaixo.
6. Conferência (não há comando dedicado): rode e só aceite com zero problemas; saída rejeitada vai para um subagente novo.
   ```bash
   python3 - "<master>" "06-analise/quali/<tema>_codigos.csv" "06-analise/quali/<tema>_temas.md" <<'EOF'
   import csv, re, sys, unicodedata
   norm = lambda s: re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip().lower()
   master = {l["ficha_id"]: l for l in csv.DictReader(open(sys.argv[1], encoding="utf-8-sig"))}
   leitor = csv.DictReader(open(sys.argv[2], encoding="utf-8")); cod = list(leitor)
   cab = "id_codigo,ficha_id,chave,variavel,trecho,pagina,codigo,tipo_codigo,conceito_quadro,tema_descritivo,observacao".split(",")
   prob = [] if leitor.fieldnames == cab and cod else ["cabeçalho diferente do contrato ou CSV vazio"]
   for c in cod:
       l = master.get(c["ficha_id"])
       if l is None: prob.append(f"{c['id_codigo']}: ficha_id inexistente"); continue
       if c["chave"] != l.get("citekey"): prob.append(f"{c['id_codigo']}: chave != citekey")
       fonte = norm(l.get(c["variavel"] + "__evidencia", "")) + " " + norm(l.get(c["variavel"], ""))
       if norm(c["trecho"]) not in fonte: prob.append(f"{c['id_codigo']}: trecho não está na célula do master")
       if c["tipo_codigo"] not in ("quadro", "livre"): prob.append(f"{c['id_codigo']}: tipo_codigo inválido")
   ids = {c["id_codigo"] for c in cod}
   citados = set(re.findall(r"\bK\d{3,}\b", open(sys.argv[3], encoding="utf-8").read()))
   prob += [f"temas cita código inexistente: {i}" for i in sorted(citados - ids)]
   print("\n".join(prob) or "ok")
   EOF
   ```
7. Auditoria humana: um segundo codificador revisa às cegas ≥ 20% dos códigos (mínimo 10); divergências por consenso; registre a concordância. Humano funde códigos, fixa temas descritivos e formula os temas analíticos, movendo-os da seção "PROPOSTOS" para "Aprovados" em `<tema>_temas.md` com papel (`revisor_humano_1`) e data.
8. Teste a síntese: casos negativos e achados refutacionais; comparação com o quadro (o que faltou, o que foi acrescentado); sensibilidade retirando estudos de pior qualidade.
9. Reescreva cada achado como enunciado portátil (amostra, fonte, tempo, comparação, magnitude quando houver) e leve à seção 8.

## 5. Meta-etnografia, realista e QCA

| Método | Passos mínimos | Limite na skill |
|---|---|---|
| Meta-etnografia (eMERGe) | escolher tema; selecionar e ler estudos; extrair interpretações dos autores (trecho e página); relacionar estudos; traduzir (recíproca, refutacional); sintetizar em linha de argumento; relatar as 7 fases | subagente só extrai trechos; tradução e síntese humanas |
| Realista (RAMESES) | mapa de teorias incluindo rivais (incentivos perversos do DAG); busca iterativa documentada; relevância e rigor por trecho; CMOC `M(recurso) + C → M(raciocínio) = O`; recomendações "em circunstâncias como A, tente B"; cada ciclo de teoria vira emenda (`$RS emenda`) | iterativa completa fora da v1: declarar o limite no relato |
| QCA | tabela de dados (estudo = caso); calibração com âncoras externas; tabela verdade; contradições resolvidas antes de minimizar; necessidade antes de suficiência; soluções conservadora e parcimoniosa; presença e ausência do desfecho em separado; robustez | sem comando; calibração é portão humano; computacional fora da v1 |

Limiares de QCA: 10 a 50 casos; com < 10 estudos, no máximo 2–3 condições; desfecho calibrado por magnitude do efeito, nunca por significância; consistência de suficiência ≥ 0,80 (piso 0,75, justificado); necessidade com consistência > 0,90 e cobertura alta; PRI próximo da consistência (< 0,5 = inconsistência séria); interpretar termos com cobertura > 0,5.

## 6. Integração sequencial-explicativa e joint display

1. A síntese quantitativa define células e enigmas: heterogeneidade alta, PI largo, estudos discrepantes, direções opostas.
2. A síntese qualitativa gera hipóteses (temas analíticos, CMOCs) e enunciados próprios (percepção, implementação, custo).
3. Teste quando k permite: moderador codificado a partir da síntese qualitativa **antes** de olhar o efeito por subgrupo, acrescentado como coluna a `05-decomposicao/efeitos_para_sintese.csv` (references/06-decomposicao.md, seção 8) por junção pela `chave` (ou `chave` × `construto_outcome`, se o moderador for por resultado), `$RS analise efeitos --in` nesse arquivo e `$RS analise meta --grupo familia_intervencao,construto_outcome --moderadores <coluna>`. Leia `moderadores.individuais.<coluna>` (`executado`, `motivo`, `QM_p`, `subgrupos`). Estimativa por nível exige k ≥ 3; teste de diferença, ≥ 4 por nível e ~10 por característica.
4. Sem estudos suficientes: fica "hipótese", com a confiança CERQual do achado que a originou e a lacuna registrada.
5. Feche em `06-analise/joint_display.csv` com cabeçalho `hipotese_id,origem,evidencia_quali,estudos_quali,confianca_cerqual,evidencia_quanti,estudos_quanti,k_por_nivel,teste_ou_motivo,resultado,ajuste,consequencia_caixa` (`ajuste` = confirmacao|expansao|discordancia) e responda às cinco perguntas-guia do JBI: as sínteses se apoiam ou se contradizem? o quali explica por que funciona ou não? explica diferenças de direção e tamanho? o que do quanti o quali não explorou? o que do quali o quanti não testou?

## 7. Certeza GRADE por célula de efeito

Unidade: família × construto × classe de desenho (randomizados e não randomizados em corpos separados). Duas pessoas independentes, consenso, justificativa escrita por rebaixamento/elevação (MECIR C74, C75).

| Ponto de partida | Regra |
|---|---|
| Ensaios randomizados | alta |
| Não randomizados com ROBINS-I | alta, em geral rebaixados dois níveis (confundimento, seleção); não rebaixar exige justificativa detalhada |
| Não randomizados sem ROBINS-I (inclusive só Maryland ou hierarquia de desenho) | baixa; não rebaixar de novo por confundidores desconhecidos |
| Corpo não randomizado com ferramentas diferentes (ex.: RDD com ROBINS-I e DiD agregado com EPOC na mesma célula) | um único ponto de partida para a célula, declarado no protocolo e registrado em `justificativa`; nunca "alta" para uns estudos e "baixa" para outros no mesmo juízo |

| Domínio | Grave quando | Insumo da skill |
|---|---|---|
| Risco de viés | peso da estimativa vem de estudos com limitação decisiva | `rob_geral`; `sensibilidade.sem_alto_risco` |
| Inconsistência | estimativas muito diferentes, ICs sem sobreposição, PI largo sem explicação | `tau`, `I2`, `pi` (k ≥ 5); `pi_cobre_beneficio_e_dano` |
| Indireção | população, intervenção, comparador, desfecho, janela, **contexto institucional/nacional, nível de governo, implementador, estimando** diferem da pergunta | checklist de comparabilidade; fatores de transferibilidade |
| Imprecisão | IC cruza zero ou δ; amostra total abaixo do tamanho ótimo de informação (OIS; com α = 0,05 e poder de 80%, n total ≈ 4 × (1,96 + 0,84)² / d²: d = 0,2 → ~790; os ~400 da regra de bolso do GRADE para contínuos só detectam d ≈ 0,28) | `ic`, `ic_dentro_delta`, n dos estudos |
| Viés de publicação | só estudos pequenos positivos; busca pouco abrangente; k ≥ 10 com assimetria | `vies_publicacao`, julgamento ROB-ME |

Um nível por domínio grave, dois por muito grave, até três no total; elevação (efeito grande, dose-resposta, confundimento contrário) em geral só para não randomizados. Sem meta-análise: julgar entre estudos (imprecisão pela soma de participantes e ICs individuais; inconsistência pela variação de direção e magnitude; viés de publicação sem teste). Moderador testado: credibilidade pelo ICEMAN; baixa ou muito baixa = "hipótese" na caixa, e cada nível testado vira linha de efeito com seu GRADE.

## 8. Confiança CERQual por achado; CMOC e QCA sem níveis

| Componente | Preocupação típica | Análogo GRADE |
|---|---|---|
| Limitações metodológicas | limitação que afeta este achado; estudo fraco que fornece a maior parte dos dados | risco de viés |
| Coerência | dados contraditórios ou ambíguos; explicações concorrentes não exploradas | — |
| Adequação dos dados | dados finos ou poucos estudos para achado amplo | imprecisão |
| Relevância | indireta, parcial ou incerta em relação ao contexto da pergunta | indireção |

Regras: resumo explícito do achado antes do julgamento; todo achado começa em alta; rebaixar pelo menos um nível por preocupação séria; várias pequenas/moderadas podem somar um; sem pontuação numérica; não rebaixar duas vezes pela mesma preocupação; duas pessoas; registrar Evidence Profile e tabela SoQF.

CMOC e soluções de QCA não recebem nível GRADE nem CERQual. Enunciado narrativo com campos fixos: CMOC = formulação, estudos por elo e tipo de dado, relevância e rigor por fonte, evidência contrária, status (inicial|refinada|testada); QCA = configuração, consistência e cobertura com limiar prévio, cobertura da solução e casos não explicados, sensibilidade a calibrações alternativas, risco de viés dos casos, rubrica de calibração.

## 9. Formato exato de `06-analise/certeza.csv`

CSV UTF-8, vírgula, uma linha por juízo. `$RS caixa` lê com cabeçalho livre, mas use exatamente:

`familia_intervencao,construto_outcome,dimensao,classe_desenho,certeza,abordagem,enunciado,estudos,justificativa,delta,moderador_explica,explica_heterogeneidade,validado_humano`

| Coluna | Valores aceitos pelo `rslib/caixa.py` | Regra |
|---|---|---|
| `familia_intervencao` | texto | igual (sem acento/caixa) ao `familia_intervencao` dos JSON do R e do master |
| `construto_outcome` | texto | obrigatório em `efeito`; vazio em `implementacao` (avaliada por família); opcional nos achados |
| `dimensao` | `efeito`, `implementacao`, `mecanismo`, `moderador`, `percepcao`, `custo` | acentos são dobrados |
| `classe_desenho` | `randomizado`, `nao_randomizado` (aliases `rct`, `ecr`, `nrs`, `nrsi`); vazio | vazio vale para todas as classes da célula, com aviso: declare uma linha por classe |
| `certeza` | `alta`, `moderada`, `baixa`, `muito_baixa` (também `muito baixa`, `high`, `moderate`, `low`, `very low`) | vazio ou inválido → rótulo Pendente |
| `abordagem` | `GRADE` (efeito), `CERQual` (demais) | copiada para `abordagem_certeza` |
| `enunciado` | texto | obrigatório em mecanismo, moderador, percepção e custo (senão Pendente); opcional em implementação |
| `estudos` | chaves separadas por barra vertical ou ponto e vírgula | as mesmas `chave`/`citekey` do projeto |
| `justificativa` | texto | domínios rebaixados e motivo; vai para a caixa |
| `delta` | número (ponto ou vírgula) | só `efeito`; prevalece sobre `--delta` |
| `moderador_explica` | `sim`, `s`, `1`, `true`, `pre_especificado`, `quali`, `qualitativo` | só na linha de `efeito`: declara que a célula alega explicação da heterogeneidade. Sozinho não sustenta Misto (seção 10); com PI cruzando e sem os requisitos, a célula sai Inconclusivo |
| `explica_heterogeneidade` | `sim`, `s`, `1`, `true` | só em linhas de `moderador` ou `mecanismo`: marca o achado que explica a heterogeneidade do efeito. Vale para a célula de mesma família, com `construto_outcome` igual ou vazio (achado da família) e `classe_desenho` igual ou vazia; entre várias, a de maior CERQual com enunciado. Exigida para Misto, com enunciado e `certeza` (CERQual) ≥ baixa; também alega explicação por si |
| `validado_humano` | `sim`, `s`, `1`, `true` | se a coluna existe e a linha de certeza não está marcada, toda linha da caixa que ela sustenta, em qualquer dimensão (efeito, implementação, mecanismo, moderador, percepção, custo), sai `status_rotulo = rascunho` (conta em `n_pendentes` e em `n_rascunho`, e bloqueia o G8). Sem a coluna, nada muda: use-a sempre |

Na mesma célula e classe vale a última linha. Exemplo:

```csv
familia_intervencao,construto_outcome,dimensao,classe_desenho,certeza,abordagem,enunciado,estudos,justificativa,delta,moderador_explica,explica_heterogeneidade,validado_humano
Restrição de celulares,desempenho,efeito,nao_randomizado,baixa,GRADE,,Silva2019|Costa2018|Lima2021|Reis2020|Melo2022,partiu de baixa; inconsistência não grave,0.1,sim,,sim
Restrição de celulares,,implementacao,,moderada,CERQual,Exige guarda dos aparelhos e regras claras,Silva2019|Costa2018,adequação: dois estudos,,,,sim
Restrição de celulares,desempenho,moderador,,baixa,CERQual,Em escolas com regra aplicada pela direção o efeito é maior que onde cada professor decide,Silva2019|Reis2020,dois estudos; coerência moderada,,,sim,sim
Restrição de celulares,desempenho,mecanismo,,baixa,CERQual,Em salas com acesso ao aparelho a retirada reduz interrupções e sustenta a atenção,Silva2019,um estudo primário,,,,sim
```

## 10. `$RS caixa`: regras `caixa-3`, painel, entradas e leitura

`$RS caixa [--master <fichamentos_master.csv>] [--efeitos 06-analise/meta_resumo.json] [--swim 06-analise/swim_resumo.json] [--certeza 06-analise/certeza.csv] [--mapa <mapa>] [--delta δ] [--faixas "<faixas do protocolo, ex.: trivial:0,pequena:0.1,moderada:0.25,grande:0.5>"] [--k-min 3]`. Sem flag, lê os três arquivos padrão de `06-analise/` se existirem; `--master` só é usado se passado (sem ele, ou com master sem as variáveis `impl_*` do mapa, implementação sai "Não avaliada" com `status_rotulo = pendente` mesmo havendo linha CERQual de implementação em `certeza.csv`, o que bloqueia o G8; custo sai "Pendente", salvo linha `custo` com enunciado em `certeza.csv`; projeto só de meta-análise: references/00-configuracao-estado.md, seção 7); passe `05-decomposicao/master_caixa.csv` quando existir (master com o pior `rob_geral` de cada estudo), senão o `fichamentos_master.csv`. Faixas e δ vêm do protocolo, nunca escolhidos depois.

Rótulo de efeito (`regra_versao = caixa-3`), nesta ordem (célula = família × construto × classe de desenho):

| Ordem | Condição | Rótulo (`regra_aplicada`) |
|---|---|---|
| 1 | sem certeza GRADE na célula | Pendente (`sem_certeza`) |
| 2 | estimativas não alinhadas | Pendente (`sinal_nao_alinhado`) |
| 3 | certeza muito baixa | Inconclusivo (`certeza_muito_baixa`) |
| 4 | meta-análise com k ≥ `--k-min`; a célula alega explicação (`moderador_explica` na linha de efeito ou achado com `explica_heterogeneidade`); PI além de ±δ nos dois lados (sem δ: PI cruza zero); e todos os requisitos: k ≥ 5 com `tau2_interpretavel` diferente de false, δ declarado, achado de moderador ou mecanismo com `explica_heterogeneidade = sim`, enunciado e CERQual ≥ baixa | Misto (`misto_pi_moderador`); o achado entra em `fontes`, e sem `validado_humano` rebaixa o Misto a rascunho |
| 5 | como a 4 (explicação alegada e PI cruzando), mas falta algum requisito | Inconclusivo (`inconclusivo_misto_nao_sustentado`), com a lista do que falta na justificativa |
| 6 | meta-análise: IC > 0 (ou < 0) e certeza ≥ baixa | Positivo (Negativo) |
| 7 | meta-análise: δ declarado, IC inteiro em [−δ, +δ] e certeza ≥ moderada | Nulo |
| 8 | meta-análise: demais casos | Inconclusivo (`inconclusivo_ma`) |
| 9 | sem meta-análise: teste de sinal p < 0,05, ≥ 5 estudos, ≥ 70% numa direção, não só risco alto, certeza ≥ baixa | Positivo (Negativo) |
| 10 | demais casos | Inconclusivo |

Sem explicação alegada, a célula com PI largo segue para Positivo, Negativo, Nulo ou Inconclusivo como em qualquer outra. Força = certeza (alta = forte, moderada = moderada, baixa = fraca, muito baixa = insuficiente). Escala = faixa de `--faixas` pela estimativa. Testes combinados são ignorados mesmo que apareçam nos JSON. Misto sem meta-análise não existe nesta versão.

Cautela que o script não aplica sozinho: o teste de sinal é binomial exato bilateral, e com ele p < 0,05 exige ao menos 6 estudos todos na mesma direção (5 de 5 dá p = 0,0625; 8 de 9 é o menor com um discordante): o "≥ 5 estudos" da regra nunca decide sozinho, e o protocolo deve declarar isso.

**Linha de painel.** Para cada família × construto, a caixa acrescenta uma linha `dimensao = efeito_painel` (`celula_id` "`<família> × <construto> [painel]`") que resume os corpos de evidência (uma linha de efeito por classe de desenho) para o painel e o policy brief:

| Situação dos corpos | Rótulo do painel (`regra_aplicada`) |
|---|---|
| algum corpo pendente | Pendente (`painel_pendente`) |
| um só corpo | o rótulo dele (`painel_corpo_unico`) |
| corpos com o mesmo rótulo | esse rótulo, com a maior certeza (`painel_mesmo_rotulo`) |
| rótulos diferentes | o rótulo do corpo de maior certeza, com o outro anotado na justificativa (`painel_maior_certeza`) |
| rótulos diferentes com a mesma certeza | Inconclusivo por heterogeneidade por desenho (`painel_empate_desenho`) |

A linha de painel sai `rascunho` se algum corpo estiver em rascunho e conta em `n_pendentes` como qualquer linha não definida. A regra do painel é convenção da especificação (declare-a no protocolo com a versão da regra); os corpos por desenho continuam no relatório.

Implementação (por família, variáveis do master via `assets/mapas/caixa_ferramentas_mapa.csv`): 1 ponto por critério presente (`impl_componentes`, `impl_multinivel`, `impl_infraestrutura`, `impl_barreiras_fidelidade` em ≥ 2 estudos, `impl_tempo_longo`; valor = primeiro token em `sim|s|1|yes|true`) → 0–1 Simples, 2–3 Moderada, ≥ 4 Complexa; sem linha CERQual de implementação o rótulo fica Pendente (proposto em `rotulo_proposto`). Achados: um enunciado por linha de `certeza.csv`; estudo com `mecanismo_id`/`moderador_id`/`percepcao_id`/`custo_id` = sim sem enunciado gera linha Pendente; custo sem dado = "Não reportado". Risco alto vem de `rob_geral` do master, com os valores da linha `rob` do mapa: `alto`, `muito_alto`, `critico`, `grave`, `serio`, `high`, `critical`, `serious` (o primeiro token da célula é comparado; os mesmos de references/05-qualidade.md, seção 4). Códigos de ausência (`999`, `NA_secao`, `não`, `NA`) não contam como achado nem como custo preenchido. Junção do master sempre por `citekey`.

Leitura do resumo JSON: `n_linhas`, `rotulos_efeito`, `rotulos_painel`, `n_pendentes` (linhas com `status_rotulo` ≠ `definido`, isto é, `pendente` ou `rascunho`), `n_rascunho` (linhas sem `validado_humano`), `rascunho`, `regra_versao`, `avisos` (família herdada ou ausente, classe desconhecida, certeza sem classe, dois grupos na mesma célula) e `pendencia` (só no autopiloto; em checkpoints é `null` e o coordenador para no G8). O evento `caixa_gerada` guarda os mesmos números (com `regra_versao` e `rotulos_painel`), e o `status` marca `rascunho` (com `motivos_rascunho`) enquanto a última caixa tiver `n_pendentes > 0`. A pendência `certeza_caixa` acompanha `n_pendentes` a cada reexecução (substituída, sem duplicar) e fecha sozinha quando `n_pendentes: 0`; o comando a fecha antes de decidir a marca de rascunho, então o `.md` sai sem a marca se não restar outra pendência. Cada linha de `caixa_ferramentas.csv` tem `fontes` (`meta_resumo.json#grupos[i]`, `certeza.csv:linha n`, colunas do master) e `assinatura` sha256. O `.md` leva "RASCUNHO NÃO VALIDADO" se houver linha pendente ou pendência aberta. Toda mudança em `certeza.csv` exige rodar `$RS caixa` de novo.

## 11. Da evidência à prática: EtD-lite, transferibilidade, implicações

Escreva `06-analise/etd.md` por célula principal com os critérios e a fonte de cada um: prioridade do problema (introdução); efeitos desejáveis e indesejáveis, inclusive perversos do DAG (caixa, efeito e escala); certeza (GRADE); valores e aceitabilidade (percepção, CERQual); balanço (juízo explícito); recursos e custo-efetividade (linha custo; "não reportado"); equidade (moderadores com ICEMAN/CERQual; PROGRESS-Plus); viabilidade (implementação); **transferibilidade ao Brasil**.

Transferibilidade (TRANSFER): 3 a 5 fatores priorizados no protocolo com usuários (ex.: nível de governo e autonomia fiscal, desigualdade regional, marco legal e discricionariedade das redes, fatores de suporte, implementador); tabela estudos × fatores; preocupação por fator (nenhuma, pequena, moderada, séria). Registre em que domínio cada preocupação foi contada: se já rebaixou indireção ou relevância, não rebaixa de novo no EtD.

| Certeza do efeito principal | Transferibilidade | Implicação admissível |
|---|---|---|
| alta ou moderada | sem preocupação séria | opção favorecida, com condições de implementação e monitoramento |
| alta ou moderada | preocupação moderada ou séria | condicional aos fatores; piloto ou implementação restrita |
| baixa | qualquer | condicional, só com avaliação de impacto ou piloto; dizer o que mudaria a conclusão |
| muito baixa | qualquer | nenhuma implicação de adoção por efetividade; implicações de pesquisa e de desenho de avaliação |

Frases por certeza (efeito médio): alta "X aumenta/reduz Y"; moderada "X provavelmente aumenta/reduz Y"; baixa "X pode aumentar/reduzir Y"; muito baixa "A evidência é muito incerta sobre o efeito de X em Y". Trivial ou nenhum: "... resulta em pouca ou nenhuma diferença", só com rótulo Nulo. Nunca "não tem efeito" com IC que inclui zero. A seção se chama "Da evidência à prática: implicações"; "força" na caixa é força da evidência, não da recomendação.

## 12. O que o G8 exige e o que perguntar

`$RS portao G8` sai com código 2 se alguma linha de `caixa_ferramentas.csv` (inclusive as de painel) tem `status_rotulo` diferente de `definido` (pendente ou rascunho; tipo certeza, que no autopiloto vira pendência); se falta `06-analise/certeza.csv` (artefato; dispensado em `escopo`, `mapa_evidencias` e `realista` sem caixa); se alguma célula de efeito da caixa não tem linha de certeza com a mesma família, construto e classe de desenho (certeza); se a revisão é `oqf_mista_sequencial` e não há caixa (artefato); ou se há pendência aberta da etapa 10 ou do G8; avisa grupos da meta-análise sem ajuste válido. Em checkpoints, `$RS caixa` não abre pendência. O resto é conferido por você; antes de pedir aprovação, confira e mostre ao usuário:

- método qualitativo nomeado; conferência da seção 4 com "ok" em todos os temas; auditoria humana registrada; temas analíticos e CMOCs aprovados por humano;
- joint display preenchido; hipóteses não testadas marcadas como hipótese;
- `certeza.csv` completo e com `validado_humano = sim` em todas as linhas (todas as dimensões); justificativa em todo rebaixamento;
- `$RS caixa` com `n_pendentes: 0` e `n_rascunho: 0`, sem `avisos` sem resposta; rótulos Misto/Nulo conferidos contra as condições (`ic_dentro_delta` e `pi_cobre_beneficio_e_dano` do `meta_resumo.json` usam o mesmo critério da caixa); cada `inconclusivo_misto_nao_sustentado` explicado (ou os requisitos completados); linhas `efeito_painel` conferidas contra os corpos por desenho;
- `etd.md` com transferibilidade e implicações proporcionais à certeza;
- `agentes/revisor-metodologico.md` com `{PORTAO}=G8` e `{SAIDA}=06-analise/revisao_metodologica_g8.md`, incluindo em `{ARQUIVOS}` os JSON do R, `certeza.csv`, `caixa_ferramentas.csv`, `joint_display.csv`, `etd.md` e os `<tema>_temas.md`; nenhum `### Rnn [CRITICO]` sem resolução.

Perguntar: quem são os dois julgadores de GRADE/CERQual (papéis); qual a ordem de rótulos e a regra do painel declaradas no protocolo (as do script são as da seção 10, versão `caixa-3`; se o protocolo diferir, registrar emenda ou divergência); fatores de transferibilidade e contexto de uso; se hipóteses qualitativas justificam nova extração de efeitos por subgrupo.

Aprovar: `$RS portao G8 --aprovar --por revisor_humano_1 --criterios '{"caixa_n_pendentes": 0, "regra_versao": "caixa-3", "certeza_validada": true, "revisor_metodologico_criticos": 0}'`. Autopiloto: `$RS portao G8 --aprovar --por autopiloto` abre pendência de revisão humana; juízos de certeza pendentes ficam como pendência (`$RS pendencia abrir --tipo certeza_humana --etapa 10_sintese --portao G8 --descricao "..."` se o script não abriu) e caixa e relatório saem como rascunho. Ao fechar (`$RS pendencia fechar <id> --motivo "..."`), rode `$RS caixa` e regenere os produtos do relato.

## 13. Armadilhas e o que registrar

| Armadilha | Prevenção |
|---|---|
| Frequências, nuvens de palavras ou resumo estudo a estudo chamados de síntese | nomear método; temas com rastreabilidade |
| Revisão como estudo de suporte | `{EXCLUIR_FICHAS}`; conferir `estudos` da caixa |
| Enunciado sem estudo rastreável | só entra com `ficha_id`/chave e trecho |
| LLM produzindo temas analíticos ou CMOCs finais | seção "PROPOSTOS" até aprovação humana |
| Magnitude ou significância como "força" | escala = faixa; força = GRADE |
| "Sem efeito" por não significância | Nulo só com δ, IC em ±δ e certeza ≥ moderada |
| Misto com k = 3 ou 4, sem δ ou com moderador sem confiança própria | `caixa-3` devolve Inconclusivo (`inconclusivo_misto_nao_sustentado`) |
| Painel com dois rótulos para a mesma família × construto | linha `efeito_painel`: vale o corpo de maior certeza; empate = Inconclusivo |
| Nível GRADE para CMOC ou QCA | enunciado narrativo |
| Contar indireção de contexto duas vezes | registrar domínio de cada fator |
| Implicação mais forte que a certeza | tabela da seção 11 |

Registrar: PRISMA 2020 itens 13d e 20 (síntese qualitativa e integração), 15 e 22 (GRADE e CERQual por achado, tabela SoF e SoQF), 23a–23d (interpretação, limitações da evidência e do processo, implicações); SWiM 6 e 8; ENTREQ (método, quem codificou, derivação de temas); eMERGe ou RAMESES quando aplicável; versão da regra (`regra_versao = caixa-3`), ordem dos rótulos e regra do painel.
