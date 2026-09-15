# Pergunta, teoria do programa e protocolo (etapas 1-3, portões G1 e G2)

Prefixo: `$RS` abrevia `python3 "<pasta da skill>/scripts/rs.py"` (SKILL.md, "Como chamar os comandos"): em cada chamada de Bash, use a função `rs` definida na mesma chamada ou o caminho completo, nunca uma variável `RS`. G1 e G2 são humanos em qualquer modo: o script recusa `--por autopiloto` com código 2. Para escolher o tipo, leia também references/tipos-de-revisao.md.

## Sumário

1. Arquivos da etapa
2. Entrevista inicial
3. X, Y, M, Z e escala da pergunta
4. Checagem de revisões existentes e registradas
5. Mapeamento preliminar (contagens)
6. Portão G1
7. Teoria do programa e DAG com incentivos perversos
8. Framework por tipo
9. Desfechos e `direcao_desejada`
10. Protocolo: passo a passo
11. Revisor metodológico
12. Registro no OSF
13. Portão G2
14. Armadilhas e o que registrar

## 1. Arquivos da etapa

| Arquivo | Conteúdo | Congela |
|---|---|---|
| `00-protocolo/pergunta.md` | ficha da pergunta (X, Y, M, Z, escala, usuários, decisão), revisões existentes, contagens exploratórias, preferências do usuário | G2 |
| `00-protocolo/exploracao_<EXn>.csv` | listas exploratórias do OpenAlex (`buscar openalex --listar`), sem importar | G2 |
| `00-protocolo/teoria_programa.md` | narrativa, tabelas por elo, papéis das variáveis, tabela Z | G2 |
| `00-protocolo/dag_v1.mmd` (ou `dag_v1.R` com `dagitty`) | diagrama versionado (a skill não tem script de DAG: Mermaid renderiza no Quarto; o `.R` roda à parte) | G2 |
| `00-protocolo/protocolo.md` | copiado de `assets/templates/protocolo.md` | G2 |
| `00-protocolo/codebook_v0_<familia>.csv` | codebook v0 (e de RoB, se ajustado); obrigatório no G2 | G2 |
| `00-protocolo/codebook_elegibilidade.csv` | codebook de elegibilidade em texto completo (critérios C1...Cn do protocolo, inclusive o de desenho, ex.: `criterio_sms_minimo`); obrigatório no G2 | G2 |
| `00-protocolo/ancoras_validacao.csv` | âncoras de validação da busca, montadas por quem não escreve as strings (modelo `assets/templates/ancoras.csv`) | G2 |
| `00-protocolo/revisao_metodologica_g2.md` | relatório do revisor metodológico | G2 |
| `00-protocolo/emendas.md` | log de emendas e cabeçalho com o registro OSF (modelo `assets/templates/emendas.md`) | nunca |

Nomes com `teoria`, `dag`, `framework`, `picoc`, `cmmo`, `pcc` ou `spider` fazem o `status` marcar a etapa 02 em andamento; `protocolo*` libera a sugestão do G2.

## 2. Entrevista inicial

Pergunte em blocos curtos; registre as respostas em `00-protocolo/pergunta.md` com data.

| Tema | Pergunta ao usuário | Por quê |
|---|---|---|
| Decisão e uso | Que decisão a revisão vai informar? Quem vai usar? Formulação (ex ante) ou avaliação (ex post)? | define tipo, desfechos e produto |
| Intervenção (X) | Qual programa ou família de programas? Quais componentes? Nome, lei ou ato de criação? | X no nível do programa, não da política inteira |
| Resultados (Y) | Quais resultados importam para os usuários? Que dano a intervenção pode causar? | desfechos críticos, danos e direção |
| Mecanismos (M) | Por que e como deveria funcionar? | hipóteses para teoria e extração |
| Moderadores (Z) | Para quem, onde e quando funcionaria melhor ou pior? Desigualdades importam? | tabela Z e PROGRESS-Plus |
| População e contexto | Unidade (pessoa, escola, empresa, município)? País, nível federativo, período? | elegibilidade e estimandos |
| Recorte | Há marco legal ou de criação? Idiomas? | recorte justificado |
| RS conhecidas | Conhece revisões ou estudos-chave sobre isso? | checagem e âncoras |
| Recursos | Prazo, equipe (≥ 2 pessoas, alguém com estatística), acesso a WoS/Scopus, R instalado? | variante rápida, bases, meta-análise |
| Stakeholders | Gestores, órgãos de controle ou beneficiários podem comentar pergunta e desfechos? | teoria e protocolo |
| IA | Aceita enviar títulos e resumos a provedores externos (modo API)? | plano de IA |

## 3. X, Y, M, Z e escala da pergunta

| Regra | Operação |
|---|---|
| X e Y antes de qualquer busca definitiva | X = intervenção (variável independente); Y = resultado. M e Z podem começar como hipóteses |
| X no nível do programa | Política inteira ("o problema central") → pergunta de escala (1). Rótulo não define intervenção: descreva componentes (o que, por quem, como, onde, quando, quanto) |
| Escala (1) ampla, de problema | "O que funciona para Y?" → mapa, escopo ou uma RS por família de intervenção |
| Escala (2) X sobre Y | uma célula principal; OQF ou efetividade |
| Escala (3) X sobre vários Y | uma célula por `construto_outcome`, com direção e janela por desfecho |
| Unidades diferentes | Unidade da empresa e do ente federado = duas PICO de síntese, não uma |
| Sem pergunta clara | Não comece a revisão; refine |

Frase-modelo para a ficha: "X [melhora/reduz] Y em P no contexto C, em comparação com Cm?"

## 4. Checagem de revisões existentes e registradas

Busca exploratória NUNCA entra no ledger: nesta etapa não rode `importar` nem `buscar openalex` sem `--contar` ou `--listar` (inflaria os identificados do PRISMA).

1. Contagem no OpenAlex (não exige projeto): `$RS buscar openalex --query '("systematic review" OR "scoping review" OR "meta-analysis" OR "revisão sistemática" OR "revisión sistemática") AND (<termos de X>)' --contar`. Variante: `--query '<termos de X>' --filtro 'type:review' --contar`. Vírgula na string é recusada; retire-a.
2. Listar títulos sem importar: `$RS buscar openalex --busca-id EX1 --query '("systematic review" OR "scoping review" OR "meta-analysis") AND (<termos de X>)' --listar 50`. Grava `00-protocolo/exploracao_EX1.csv` (`posicao,id_openalex,titulo,ano,doi,citado_por`), não registra busca e, com projeto, só registra `artefato_versionado`; sem projeto, grava em `<--dir ou pasta atual>/00-protocolo/`. `--busca-id` segue a regra do `importar` (`EX1`, `EX2`...: um id por lista; arquivo congelado no G2 é recusado). O resumo traz `n_api` (total na API) e `n_listadas`.
3. Nas interfaces web (registre data e termos): OSF Registries; PROSPERO (só temas de saúde); Campbell Library; Cochrane Library; Epistemonikos (saúde); 3ie Development Evidence Portal; SciELO com "revisão sistemática"; Catálogo de Teses CAPES/BDTD; repositório do IPEA. Ferramentas de IA (Consensus e similares) só sugerem: confira cada registro na fonte.
4. Para cada revisão achada, registre em `00-protocolo/pergunta.md`: referência, pergunta, data da última busca, n de estudos, se avaliou risco de viés, bases brasileiras, sobreposição com a sua pergunta.
5. Decida:

| Achado | Decisão |
|---|---|
| RS recente, boa, mesma pergunta | Não duplicar: mudar ângulo (população, contexto, desfecho) e justificar, ou divulgar a existente |
| RS boa e desatualizada | Atualizar (buscar com sobreposição de datas) |
| RS enviesada ou frágil (sem RoB, busca fraca, sem bases brasileiras) | RS nova, com a fragilidade no racional |
| RS registrada em andamento | Checar o escopo registrado antes de seguir |
| Pergunta mais ampla que as RS e dados nelas | Overview (`guarda_chuva`) |
| Muitos primários fora das RS | RS de estudos primários |
| Poucos ou nenhum estudo | Revisão ainda pode documentar ausência de evidência (declarar como objetivo) |

As revisões achadas servem para o racional, para as âncoras de validação (seus estudos incluídos, conferidos contra os critérios) e como sementes da bola de neve. Nunca entram como estudos.

## 5. Mapeamento preliminar (contagens)

Estime volume e mistura de desenhos com contagens, sem gravar nada:

- `$RS buscar openalex --query '(<termos de X>) AND (<termos de Y>)' --contar`
- `$RS buscar openalex --query '(<termos de X>) AND ("difference-in-differences" OR "randomized" OR "quasi-experimental" OR "regression discontinuity")' --contar`
- `$RS buscar openalex --query '(<termos de X>) AND (interview OR interviews OR "focus group" OR qualitative)' --contar` (o campo padrão tem stemming e recusa curinga com HTTP 400; para `interview*`, use `--campo title_and_abstract.search.exact`, sem stemming, e compare as duas contagens)

Registre as contagens com data em `00-protocolo/pergunta.md`. Volume muito alto → reavaliar escala; muito baixo → documentar e considerar ampliar X ou contexto.

## 6. Portão G1

Mostre ao usuário: pergunta (X, Y, M, Z, escala), tipo e variante (com a justificativa frente às alternativas próximas), revisões existentes e decisão, expectativa de comparabilidade, equipe e prazo, título provisório. Com "aprovo" explícito:

`$RS portao G1 --aprovar --por revisor_humano_1 --criterios '{"pergunta": "<frase>", "tipo_revisao": "<valor de --tipo>", "escala": 2, "rs_existentes": "2 revisões; RS nova porque <motivo>", "comparabilidade": "incerta: prever MA e SWiM", "equipe": 3, "prazo": "<meses>"}'` (revisão rápida: acrescente `"variante": "rapida"`, os `"atalhos"` e, se o protocolo usar a triagem com dupla humana parcial e segunda leitura dos excluídos, `"atalho_rapida": true`, que habilita esse caminho no G4; references/tipos-de-revisao.md, seção 6). Na `proxima_acao` do `status`, o G1 vem com `<pergunta aprovada pelo usuário, entre aspas>`: troque pelo texto aprovado.

O G1 grava `pergunta`, `tipo_revisao` e `variante` no estado. Sem `pergunta` ou com `tipo_revisao` `indefinido` (nos critérios ou no estado), o portão sai com código 2; tipo ou variante inválidos, com código 1. Mudança depois: emenda e novo G1 com os critérios atualizados (depois do G1, `init --tipo` só avisa e não muda o estado).

## 7. Teoria do programa e DAG com incentivos perversos

**Passos**

1. Levante teoria existente: legislação, documentos de monitoramento, modelos lógicos publicados, revisões, stakeholders.
2. Nível 1 (I → R) para cada desfecho, com a frase "se [atividade], então [produto], o que leva a [resultado], desde que [hipótese]".
3. Nível 2 (I → M → R) com os mecanismos candidatos.
4. Nível 3 (completo): mediadores, mecanismos latentes, confundidores e colisores plausíveis e, para cada elo, o efeito não intencional.
5. Classifique aspectos simples, complicados (várias agências ou níveis; cadeias simultâneas ou alternativas) e complexos (retroalimentação, resultados emergentes).
6. Valide com stakeholders; divergências viram teorias rivais, não consenso forçado.
7. Salve `teoria_programa.md` e `dag_v1.mmd` com data e versão.

**Tabela por elo** (obrigatória em `teoria_programa.md`):

| Elo | Efeito pretendido | Efeito não intencional possível | Direção desejada | Onde seria medido | Origem (documento, estudo, stakeholder, "IA não verificada") |
|---|---|---|---|---|---|

**Papéis e consequência**

| Papel | No DAG | Na extração | Na síntese |
|---|---|---|---|
| Confundidor (causa X e Y) | setas para X e Y | como o estudo lida (desenho, ajuste) | domínio de confundimento do RoB |
| Colisor (efeito comum) | setas chegando | restrições de amostra e seleção | alerta de viés de seleção; nunca "controlar" |
| Mediador | X → M → Y | modelo ajusta por M? (efeito direto × total) | não agregar diretos com totais; alimenta "mecanismo" |
| Moderador (Z) | FORA do grafo, tabela Z com hipótese e direção | efeitos por subgrupo | subgrupo ou meta-regressão pré-especificados; explica rótulo Misto |
| Mecanismo latente | nó raramente medido | trecho verbatim | síntese qualitativa |
| Incentivo perverso | aresta tracejada | desfecho adverso com direção própria | célula de efeito própria; entra no rótulo Negativo |

Regras do grafo: sem ciclos (recorrência desdobrada no tempo: `refis_t1 --> expectativa --> inadimplencia --> refis_t2`); seta não diz sinal nem interação; figura e grafo declarado precisam coincidir (confira arestas desenhadas contra a lista).

Convenção Mermaid (renderiza em Quarto):

```text
flowchart LR
  X[intervencao] --> M1[mecanismo] --> Y1[desfecho_beneficio]
  X -.-> P1[incentivo_perverso] -.-> Y2[desfecho_dano]
  C[confundidor] --> X
  C --> Y1
  classDef perverso stroke-dasharray: 5 5
  class P1,Y2 perverso
```

**IA para rascunhar a teoria:** procure antes modelos existentes; cada nó e seta com etiqueta de origem; peça explicitamente teorias rivais e efeitos não intencionais por elo; a versão congelada é decisão humana; registre modelo, data e prompt em `teoria_programa.md`.

## 8. Framework por tipo

| `--tipo` | Framework | Regra |
|---|---|---|
| `oqf_mista_sequencial` | PICOC + CMMO + DAG | PICOC filtra, define blocos de busca e células; CMMO orienta extração e perguntas qualitativas, NUNCA filtra |
| `efetividade_meta`, `efetividade_swim` | PICO ou PICOC | comparador explícito |
| `escopo`, `mapa_evidencias` | PCC | sem desfecho obrigatório |
| `qualitativa` | PICo, SPIDER ou PerSPEcTiF | fenômeno de interesse no lugar de intervenção |
| `realista` | CMO / CMOC | teoria refinada iterativamente; o humano é dono da teoria |
| exposição não atribuída pelo gestor | PECO | etiologia e risco |

Na tabela do framework, cada elemento aponta para um nó do DAG. Contexto no CMMO = condições em que o mecanismo opera (crise fiscal, capacidade administrativa, nível federativo), nunca a própria intervenção.

## 9. Desfechos e `direcao_desejada`

| Regra | Operação |
|---|---|
| Nome do construto | `construto_outcome` em snake_case estável (é o `--grupo` padrão de `analise meta`/`swim` e a chave de `06-analise/certeza.csv` e da caixa) |
| Família da intervenção | `familia_intervencao` em snake_case estável (usada em `--grupo familia_intervencao,construto_outcome`) |
| Direção | `direcao_desejada` = `aumentar` ou `reduzir`, por desfecho, antes da extração. `analise preparar-efeitos` recusa linha sem um desses valores, e no `efeitos.R` linha sem direção fica fora da síntese |
| Danos | ao menos um dano; incentivos perversos do DAG entram como desfechos adversos com direção própria |
| Prioridade | críticos e importantes (até 7 no resumo); declarar se algum é critério de elegibilidade (raramente deve ser) |
| Conflito entre stakeholders | dois desfechos distintos com direções distintas, nunca escolha silenciosa |
| Equidade | fatores PROGRESS-Plus plausíveis pela teoria, hipótese de efeito diferencial com direção, campos no codebook, análise pré-especificada |

Nunca escreva "sem efeito" por p > 0,05: direção vem do estimador pontual relativo a `direcao_desejada`.

## 10. Protocolo: passo a passo

1. `cp "<pasta da skill>/assets/templates/protocolo.md" 00-protocolo/protocolo.md` e `cp "<pasta da skill>/assets/templates/emendas.md" 00-protocolo/emendas.md`.
2. Preencha as seções 1-2 com a ficha da pergunta, o framework e a tabela de desfechos (seções 3, 7 e 9 desta referência).
3. Fontes e estratégia: lista de fontes com `busca_id` previsto e rascunho testado da string da base principal colado na seção 3 do protocolo (leia também references/02-busca.md).
4. Âncoras de validação: um subagente ou pessoa que NÃO escreve as strings extrai os estudos incluídos das revisões achadas, confere contra os critérios e grava `00-protocolo/ancoras_validacao.csv` (colunas do modelo `assets/templates/ancoras.csv`). O coordenador não abre esse arquivo; só `filtrar --ancoras` o lê.
5. Elegibilidade:

| Item | Regra |
|---|---|
| IDs | C1...Cn na ordem de aplicação, os mesmos em `assets/templates/protocolo.md` (seção 4), em `02-triagem/prompts/ta_vN.md` (de `assets/templates/criterios_triagem.md`; os IDs válidos são os que abrem uma linha, como `### C1.` ou `- C2:`, e menções no texto como "ver C5" não contam; o `triagem mesclar` rejeita `criterio_falhou` fora deles) e no codebook de elegibilidade, copiado de `assets/codebooks/elegibilidade_modelo.csv` para `00-protocolo/codebook_elegibilidade.csv` antes do G2. Numeração dos modelos: C1 população e contexto (`c1_populacao_contexto`), C2 intervenção estudada (`c2_intervencao_estudada`), C3 desfecho (`c3_desfecho`), C4 desenho elegível (`c4_desenho_elegivel`), C5 estudo primário (`c5_estudo_primario`; revisões vão para bola de neve e âncoras), C6 sem retratação (`c6_nao_retratado`, conferido só no texto completo, com `textos retratacoes`; não entra em `ta_vN.md`). Critério de desenho próprio (ex.: `criterio_sms_minimo` e `sms_*` de `desenho_maryland.csv`) entra na posição que o protocolo der, com o mesmo ID nos três arquivos. Na exclusão humana, `triagem override` exige o critério e o confere contra esses IDs (`C4` é aceito como apelido de `c4_desenho_elegivel`) |
| Recorte temporal | limite inferior = marco (ato normativo com número e data conferidos na fonte oficial, surgimento da tecnologia ou fim da busca da revisão atualizada); superior = data da busca; declarar se vale para publicação, dados ou ambos; igual em todas as bases |
| Idiomas | pt, en, es por padrão em políticas brasileiras; menos que isso exige justificativa e vira limitação |
| Status de publicação | sem restrição (teses, relatórios, preprints); fator de impacto e "texto inacessível" não são critérios (não recuperado ≠ excluído) |
| Desenho | pelas características (formação dos grupos, nível de atribuição); Maryland SMS só como elegibilidade de desenho |
| Revisões | critério de estudo primário: RS e meta-análises vão para bola de neve e âncoras |
| Funil formal | filtros etiquetam; exclusão só se descrita aqui, com amostra de elusão (`assets/templates/filtros_v1.json`; `filtrar --amostra-elusao`, references/03-organizacao-triagem.md, seção 4) |

6. Seleção: revisores por fase, independência, desempate, calibração (≥ 100 registros ou ≥ 10 incluídos, κ ≥ 0,6 e ≥ 75%), texto completo com decisão humana.
7. Codebook v0 (o G2 bloqueia sem `00-protocolo/codebook_v0*.csv`): `ls "<pasta da skill>/assets/codebooks/"`; copie o de partida para `00-protocolo/codebook_v0_<familia>.csv`. Cabeçalho exato `dimensao,variavel,descricao,prompt,tipo,aplicavel_se`; `tipo` em `categorica|numerica_int|numerica_real|textual`; `aplicavel_se` como `tipo_estudo=b2`. Cada desfecho, mecanismo, moderador, dano e fator de equidade do DAG precisa de variável; substitua os `{placeholders}` dos prompts pelo protocolo (o G2 bloqueia com `{...}` restante).

| `--tipo` | Codebook de partida | Arquivo no projeto |
|---|---|---|
| `oqf_mista_sequencial`, `metodos_mistos` | `oqf_decomposicao.csv` inteiro (bloco comum + a1/a2/b1/b2, classificador `tipo_estudo`) | `codebook_v0_oqf.csv` |
| `efetividade_meta`, `efetividade_swim` (e a variante rápida delas) | `oqf_decomposicao.csv` só com o bloco comum (`aplicavel_se` vazio, inclusive `tipo_estudo`, `familia_intervencao`, `construto_outcome` e as variáveis da caixa) e o bloco b2 (`aplicavel_se = tipo_estudo=b2`); os números de efeito vão para `agentes/extrator-efeitos.md`, não para a ficha | `codebook_v0_efetividade.csv` (trecho abaixo) |
| `escopo`, `mapa_evidencias` | `escopo_pcc.csv` | `codebook_v0_escopo.csv` |
| `qualitativa`, `realista` | `qualitativa.csv` | `codebook_v0_qualitativa.csv` |

```bash
python3 - "<pasta da skill>/assets/codebooks/oqf_decomposicao.csv" 00-protocolo/codebook_v0_efetividade.csv <<'EOF'
import csv, sys
with open(sys.argv[1], encoding="utf-8", newline="") as f:
    leitor = csv.DictReader(f); linhas = [l for l in leitor if l["aplicavel_se"] in ("", "tipo_estudo=b2")]
with open(sys.argv[2], "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=leitor.fieldnames); w.writeheader(); w.writerows(linhas)
print(len(linhas), "variáveis em", sys.argv[2])
EOF
```
8. Risco de viés: preencha a tabela ferramenta × desenho do modelo (RoB 2 `rob2.csv`, ROBINS-I `robins_i.csv`, EPOC `epoc.csv`, CASP `casp_qualitativo.csv`, JBI transversal `jbi_transversal.csv`, MMAT `mmat.csv`), nível e uso na síntese (sensibilidade, estratificação, GRADE; nunca exclusão automática por nota).
9. Plano de síntese:

| Item | O que fixar | Como os comandos usam |
|---|---|---|
| Comparabilidade | família de intervenção, comparador, construto, janela, população, estimando; randomizados separados de não randomizados | `--grupo familia_intervencao,construto_outcome`; `--separar-desenho sim` (padrão) |
| Modelo principal | regra hierárquica (declarado pelos autores → especificação completa → janela mais próxima → primeiro da tabela); nunca o mais significativo | coluna `modelo_principal`; estudo com vários efeitos sem principal bloqueia o grupo (código 2) |
| k mínimo e dependência | k ≥ 3; um efeito por estudo ou CHE + RVE com ρ | `analise meta --k-min 3 --dependencia um_por_estudo` (ou `che --rho 0.6`) |
| δ (SESOI) por desfecho | valor, unidade e fonte (custo, meta legal, literatura do campo); os comandos comparam δ com o g alinhado, então δ em unidade natural (pontos percentuais de frequência, R$) é convertido para g pelo DP de referência declarado, com a conversão escrita no protocolo | `analise meta --delta <δ em g>`; `caixa --delta <δ em g>`; sem δ não existe rótulo Nulo |
| Rótulos da caixa | versão da regra (`caixa-3`), ordem de aplicação e limiares próprios da especificação (Misto só com k ≥ 5, δ e achado explicativo com CERQual ≥ baixa; ≥ 5 estudos e ≥ 70% sem meta-análise; pontos de implementação) declarados como convenção; regra da linha de painel quando randomizados e não randomizados divergem (vale o corpo de maior certeza; empate = Inconclusivo) | `caixa` (`regra_versao`, linhas `efeito_painel`); references/07b-sintese-qualitativa-integracao.md, seção 10 |
| Desfechos binários | proporções por grupo, efeitos em pontos percentuais (LPM, DiD, RDD) ou razão de riscos entram por conversão a d via log OR, com `p0` do controle; conversões de modelos com ajuste são aproximadas e vão para a sensibilidade | `tipo_estatistica` `dif_prop` ou `rr` (references/06-decomposicao.md, seção 7) |
| Faixas de magnitude | limites e fonte do campo (não Cohen genérico) | `caixa --faixas "trivial:0,pequena:0.1,moderada:0.25,grande:0.5"` |
| Rota sem meta-análise | SWiM, teste de sinal, limiar de consistência 0,7 | `analise swim` |
| Testes combinados | só secundários, com ressalva | `analise combinados`; nunca definem rótulo |
| Qualitativo e integração | técnica, juízos humanos, regras da caixa | `agentes/sintetizador-quali.md`, `caixa` |
| Certeza | GRADE por célula, CERQual por achado, desfechos da tabela de resumo | `06-analise/certeza.csv` |

10. Plano de IA (tabela do modelo): por etapa, modelo, papel, supervisão, validação e contingência. Limiares vinculantes da triagem: recall ≥ 0,95 com limite inferior do IC ≥ 0,90; amostra enriquecida para ≥ 60 incluídos humanos; elusão n ≥ 300 (ou todos os excluídos); estabilidade em 5-10%. Extração: 100% dos números verificados; categóricas κ ou PABAK ≥ 0,7 e ≥ 80% em ≥ 20% (mín. 10).
11. Contingências (poucos estudos, dados faltantes, base inacessível) e pacote aberto (PRISMA 2020 item 27).
12. Revisor metodológico (seção 11), correções, e só então G2.

## 11. Revisor metodológico

Antes de levar o G2 ao usuário, lance UM subagente com o prompt de `agentes/revisor-metodologico.md`, preenchendo os placeholders do próprio prompt com `{PORTAO}` = G2, a pasta `00-protocolo/` como entrada e `00-protocolo/revisao_metodologica_g2.md` como saída. Confira que o arquivo existe (a linha de retorno do subagente não é prova). Perguntas que ele deve cobrir: critério que depende de resultado; strings incoerentes com exclusões; base sem string ou data; recorte e idiomas sem justificativa; nenhum dano entre desfechos; qual modelo extrair de um estudo com dez; o que agrega com o quê; o que é efeito relevante e nulo; onde a IA decide sozinha; o que acontece com menos estudos que o previsto. Todo problema CRÍTICO é corrigido no protocolo ou respondido por escrito no relatório antes do G2; os demais vão ao usuário no resumo do portão.

## 12. Registro no OSF

1. Registro recomendado em OSF Registries, formulário "Generalized Systematic Review Registration" (65 campos mapeados ao PRISMA 2020; "não se aplica" justificado). PROSPERO só para desfechos de saúde e não aceita escopo; escopo pelo JBI: OSF ou Figshare; revisão Campbell: registro de título na própria Campbell.
2. Declare a etapa no momento do registro (antes da busca definitiva; registro feito depois é útil, mas não é pré-registro).
3. Anexe a versão congelada no G2 (o mesmo arquivo cujo sha256 está no estado).
4. Anote DOI/URL e data no cabeçalho de `00-protocolo/emendas.md` (editável depois do G2). O registro OSF não se edita: mudanças maiores viram *update* com justificativa.
5. Submissão e contas são do usuário: a skill prepara o texto dos campos, não submete.

## 13. Portão G2

O G2 exige (mostrar ao usuário item a item):

- `00-protocolo/protocolo.md` sem placeholders `<...>` pendentes, com seção "Não se aplica: motivo" onde couber;
- pergunta, framework, DAG versionado com incentivos perversos, tabela de desfechos com `direcao_desejada` e ao menos um dano;
- critérios C1...Cn justificados; recorte com marco conferido; idiomas justificados;
- fontes com `busca_id`, rascunho de string testado, método de validação (PRESS, âncoras de validação já gravadas);
- codebook v0 e `00-protocolo/codebook_elegibilidade.csv` no cabeçalho exato; ferramenta de RoB por desenho;
- plano de síntese com comparabilidade, modelo principal, k, dependência, δ e faixas; plano de certeza; plano de IA com limiares;
- relatório do revisor metodológico sem CRÍTICO aberto;
- plano de registro OSF.

Com "aprovo" explícito: `$RS portao G2 --aprovar --por revisor_humano_1 --criterios '{"protocolo": "00-protocolo/protocolo.md", "codebook_v0": "00-protocolo/codebook_v0_<familia>.csv", "revisor_metodologico": "sem CRÍTICO", "registro": "pendente"}'`. O resumo lista `congelados` e `avisos`. O script sai com código 2 (tipo artefato) sem `00-protocolo/protocolo*`, sem `00-protocolo/codebook_v0*.csv`, sem codebook de elegibilidade (`00-protocolo/codebook_elegibilidade*.csv`; em projeto antigo, `03-textos/codebook_elegibilidade*.csv`) e com placeholders: `<...>` ou `{...}` no protocolo, `{...}` nos codebooks. Comentários HTML, blocos e trechos de código, matemática, autolinks, tags HTML comuns, atributos do Quarto (`{#sec-x}`, `{.classe}`), JSON e LaTeX não contam; "Não se aplica: motivo" sem os sinais resolve um campo que não se aplica. O bloqueio lista o arquivo e exemplos. Avisa sem `00-protocolo/revisao_metodologica*`; o resto da lista acima é conferido por você. Depois do G2: toda mudança nesses arquivos é emenda (leia também references/00-configuracao-estado.md, seção 9).

## 14. Armadilhas e o que registrar

| Armadilha | Consequência | Evite |
|---|---|---|
| Revisões achadas só no fim | Racional fraco; revisões viram "estudos" | Seção 4 antes do G1 |
| Busca exploratória importada | PRISMA inflado | Só `buscar openalex --contar` e `--listar` |
| Moderador como seta para o tratamento | Moderação confundida com confundimento | Tabela Z |
| Teoria só com o caminho pretendido | Danos nunca buscados; rótulo Positivo sem ver perversos | Tabela por elo |
| "Direção positiva" sem referência | Sinais trocados (falência "positiva") | `direcao_desejada` por desfecho |
| CMMO como filtro | Estudo de impacto sem mecanismo excluído | PICOC filtra |
| Recorte com lei errada ou três recortes | Emenda obrigatória, bases incoerentes | Conferir o ato na fonte oficial; um recorte só |
| Excluir cinzenta ou por fator de impacto | Viés de publicação | Status sem restrição |
| δ e faixas definidos depois | "Efeito fraco conforme a literatura" sem base | Tabela de δ no protocolo |
| Âncoras escolhidas por quem escreve as strings | Validação circular | Arquivo montado por terceiro e lido só pelo script |
| Aprovar G1/G2 sem "aprovo" do usuário | Portão humano falsificado | Esperar confirmação explícita |

Registre: data, fontes e termos de toda busca exploratória; decisões do usuário e suas razões; origem de cada seta da teoria; uso de IA (modelo, data, prompt) na teoria e no rascunho do protocolo; problemas do revisor metodológico e como foram tratados.
