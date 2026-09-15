# 05 Qualidade e risco de viés

Instrução operacional da parte de risco de viés (RoB) da etapa 9 (extração e RoB em paralelo, portão G7). `$RS` abrevia `python3 "<pasta da skill>/scripts/rs.py"` (SKILL.md, "Como chamar os comandos"): em cada chamada de Bash, use a função `rs` definida na mesma chamada ou o caminho completo, nunca uma variável `RS`.

## Sumário

1. Regras que não se negociam
2. Decisões do protocolo (G2) e o que perguntar
3. Ferramenta por desenho e por bloco
4. Vocabulário dos julgamentos
5. Passo a passo com comandos
6. Uso na síntese, no GRADE e no CERQual
7. Portão G7 (parte RoB) e autopiloto
8. Armadilhas
9. O que registrar e relatar

## 1. Regras que não se negociam

| Regra | Operação |
|---|---|
| Desenho não é risco de viés | Maryland SMS e hierarquias só entram como critério de elegibilidade de desenho (no protocolo) e como descritor. RoB é julgado por domínio, com a ferramenta do desenho |
| Julga-se o resultado, não o estudo | Uma avaliação por resultado da tabela de síntese (construto × modelo principal). Dois construtos do mesmo estudo = duas avaliações |
| Nada de escore somado | Nem para CASP, JBI ou MMAT. O resumo é um julgamento com justificativa |
| IA só rascunha | O subagente `avaliador-rob` responde perguntas-sinalizadoras com trecho e página e marca julgamentos como `proposta_*`. Quem julga são dois humanos |
| Dupla independente | Avaliadores A e B, com regra de desacordo definida antes (MECIR C53); consenso ou terceiro avaliador |
| Todo julgamento tem fonte | Trecho com página, relato companheiro ou correspondência com autores (MECIR C54, C55) |
| Ausência de informação não é viés | Sem informação → `SI`/`NPD`/`I` e pedido aos autores; nunca "não" por falta de relato |
| Uso pré-especificado | Excluir por RoB só se estiver no protocolo (ex.: resultado crítico no ROBINS-I fora da síntese) |

## 2. Decisões do protocolo (G2) e o que perguntar

Tudo abaixo fica em `00-protocolo/` antes do G2 (o G2 congela só os arquivos do nível `00-protocolo/`, não subpastas). Mudança depois é emenda: `$RS emenda --arquivo 00-protocolo/<arquivo> --motivo "..."`.

| Decisão | Pergunte ao usuário | Padrão da skill |
|---|---|---|
| Desenhos elegíveis | "Para as perguntas de efeito, exige grupo de comparação (SMS ≥ 3)?" e qual versão da SMS | SMS ajustada (guia What Works Growth 2016), mínimo 3 só se o usuário quiser; declarar a versão |
| Ferramenta e versão por desenho | Confirmar a tabela da seção 3 | RoB 2 (22/08/2019); ROBINS-I V2 (rascunho de 20/11/2025); EPOC (2017); CASP qualitativo (2024); JBI prevalência e JBI transversal analítico revisado; MMAT 2018 |
| Fronteira ROBINS-I V2 × EPOC | "DiD com municípios/escolas agregados vai para EPOC?" | DiD com unidades agregadas e ITS → EPOC; painel de indivíduos → ROBINS-I V2 |
| Efeito de interesse | "Interessa o efeito de ofertar a política (atribuição) ou de aderir?" | Atribuição (intenção de tratar) |
| Confundidores importantes | Lista única no nível da pergunta, derivada do DAG | Obrigatória para ROBINS-I (variável `confundidores_controlados`) |
| Resultados avaliados | Construtos da síntese × modelo principal | Os mesmos da caixa de ferramentas |
| Avaliadores | Papéis (`revisor_humano_1`, `revisor_humano_2`, terceiro) e se B vê o rascunho da IA | A e B veem respostas e trechos do rascunho, sem as colunas `*_proposto`/`*_proposta` |
| Uso na síntese | Restringir, estratificar, sensibilidade, excluir crítico? | Todos na análise primária, estratificada por classe de desenho; sensibilidade sem alto/grave/crítico; crítico fora da análise principal (`--excluir-rob critico` em `analise meta`, `analise swim` e `analise combinados`) só se o usuário aprovar no protocolo |
| `rob_geral` para EPOC | EPOC não tem julgamento geral | Pior critério com incerto = moderado (seção 5, passo 8), declarado no protocolo com os critérios ignorados no geral (`--ignorar-no-geral`) |

Cópia dos codebooks para o protocolo (substitua todo `{placeholder}` dos prompts antes do G2):

```bash
for f in rob2 robins_i epoc casp_qualitativo jbi_transversal mmat desenho_maryland; do
  cp "<pasta da skill>/assets/codebooks/$f.csv" "00-protocolo/codebook_v0_$f.csv"; done
grep -l "{" 00-protocolo/codebook_v0_*.csv   # tem de sair vazio antes do G2
```

Apague as ferramentas que o protocolo não usa. Atribuição e versões oficiais: `assets/codebooks/README.md`.

## 3. Ferramenta por desenho e por bloco

A variável `b2_estrategia_identificacao` do master da decomposição (codebook OQF) decide a ferramenta de cada resultado b2.

| Bloco / desenho do resultado | Ferramenta | Codebook (classificador) |
|---|---|---|
| b2 `experimento_aleatorizado_individual`, `encorajamento_ou_cumprimento_parcial` | RoB 2, 5 domínios | `rob2.csv` (`unidade_randomizacao=individual`) |
| b2 `experimento_aleatorizado_cluster` | RoB 2 com domínio 1b de recrutamento | `rob2.csv` (`unidade_randomizacao=cluster`) |
| b2 `regressao_descontinua`, `variavel_instrumental`, `experimento_natural`, `pareamento`, `painel_efeitos_fixos` e DiD com painel de indivíduos, `regressao_com_controles` | ROBINS-I V2, 6 domínios + perguntas de Waddington et al. (2017) no domínio 1 | `robins_i.csv` (`variante_d1=a` intenção de tratar; `b` por protocolo) |
| b2 `diferencas_em_diferencas`/`_escalonado` com unidades agregadas, `controle_sintetico` | Critérios EPOC para estudos com grupo controle (9) | `epoc.csv` (`desenho_epoc=grupo_controle`) |
| b2 `serie_temporal_interrompida` | Critérios EPOC para ITS (7) | `epoc.csv` (`desenho_epoc=its`) |
| b2 `antes_depois` (uma medida por período) | Em geral fora por SMS < 3; se elegível, ROBINS-I V2 (tende a grave ou crítico) | `robins_i.csv` |
| a1, b1 (qualitativos) | CASP qualitativo (10 perguntas) | `casp_qualitativo.csv` |
| a2 com proporção/cobertura | JBI prevalência (9 itens) | `jbi_transversal.csv` (`tipo_jbi=prevalencia`) |
| a2 com associação | JBI transversal analítico revisado (8 perguntas) | `jbi_transversal.csv` (`tipo_jbi=analitico`) |
| Estudo primário misto | MMAT 2018, categoria 5 + categoria de cada componente | `mmat.csv` (uma ficha por categoria) |
| Descritor ou elegibilidade de desenho (qualquer b2) | Maryland SMS (método, implementação) e classe de Waddington | `desenho_maryland.csv` |
| Exposição não deliberada (ROBINS-E), revisões (AMSTAR 2, ROBIS) | Sem codebook nesta versão | Criar no mesmo esquema, por emenda |

Regras de fronteira: um estudo com resultados de desenhos diferentes tem uma avaliação por resultado, cada uma na sua ferramenta. Controle sintético e event study não têm perguntas próprias em nenhuma ferramenta: use a estrutura EPOC ou ROBINS-I, registre em `justificativa` e declare a limitação. Se o protocolo adotar MMAT para todos os estudos, as categorias 1 e 4 substituem CASP e JBI. SMS como critério de elegibilidade vai no codebook de elegibilidade do protocolo, `00-protocolo/codebook_elegibilidade.csv`, congelado no G2 (copie `criterio_sms_minimo` e as variáveis `sms_*`); leia também references/04-textos-elegibilidade.md, seção 6.

## 4. Vocabulário dos julgamentos

Respostas do rascunho (fichas), com os códigos que `agentes/avaliador-rob.md` e os codebooks usam:

| Ferramenta | Sim | Não | Sem informação | Não se aplica |
|---|---|---|---|---|
| RoB 2 | `S`, `PS` | `N`, `PN` | `SI` | `NA` (pelo fluxo) |
| ROBINS-I V2 (códigos oficiais da versão de 20/11/2025) | `Y`, `PY`; nas perguntas que o prompt oferece, `SY` (sim forte) e `WY` (sim fraco) | `N`, `PN`; nas perguntas que o prompt oferece, `WN` (não fraco: o problema provavelmente não é substancial) e `SN` (não forte: provavelmente substancial) | `NI` | `NA` (pelo fluxo) |
| CASP qualitativo, MMAT | `S` | `N` | `NPD` (não é possível dizer) | — |
| JBI | `S` | `N` | `I` (incerto) | `NA` |

No ROBINS-I, `WN` × `SN` e `WY` × `SY` levam a julgamentos diferentes (ex.: 1.1, 1.2, 1.3, 3.1, 4.6, 4.9 e 4.10 com WN/SN; 2.3, 2.4 e 5.3 com SY/WY): a escolha é pelo tamanho provável do problema, justificada nas Notas. Não misture os códigos do RoB 2 (`S`, `PS`, `SI`) no ROBINS-I. Julgamentos propostos sempre com prefixo `proposta_`.

Arquivos humanos (sem prefixo; valores exatos, que `meta.R`, `swim.R` e `rs.py caixa` leem em `rob_geral`):

| Ferramenta | Por domínio (D1…Dk) | `rob_geral` | Algoritmo de referência |
|---|---|---|---|
| RoB 2 | `baixo`, `algumas_preocupacoes`, `alto` | idem | baixo se todos baixos; algumas preocupações se ≥ 1 e nenhum alto; alto se algum alto ou preocupações em vários domínios |
| ROBINS-I V2 | D1: `baixo_exceto_confundimento`, `moderado`, `grave`, `critico`; D2–D6: `baixo`, `moderado`, `grave`, `critico` | `baixo_exceto_confundimento`, `moderado`, `grave`, `critico` | pior domínio; vários moderados → grave; vários graves → crítico; B2 ou B3 = S/PS → crítico |
| EPOC | `baixo`, `alto`, `incerto` por critério | `baixo`, `moderado`, `alto` | convenção a declarar: ignore sequência e ocultação quando forem alto por definição (CBA); `alto` se linha de base, dados incompletos, contaminação, relato seletivo ou (ITS) independência de outras mudanças for alto; `moderado` se algum desses for incerto |
| CASP, JBI, MMAT | respostas por item | não se aplica; use `preocupacao_metodologica`: `nenhuma_ou_muito_pequena`, `menores`, `moderadas`, `graves` | julgamento, não soma; insumo do CERQual |

Valores de `rob_geral` tratados como risco alto (os mesmos da linha `rob` de `assets/mapas/caixa_ferramentas_mapa.csv`, lidos por `rs.py caixa`, e reconhecidos por `meta.R` e `swim.R`): `alto`, `muito_alto`, `critico`, `grave`, `serio`, `high`, `critical`, `serious`. `--excluir-rob critico` de `analise meta`, `analise swim` e `analise combinados` tira só `critico`/`critical`. Não invente outros rótulos.

## 5. Passo a passo com comandos

`FS` = pasta `scripts` da skill `fichamento-sistematico` (`<pasta da skill>/../fichamento-sistematico/scripts`; se não existir, o `caminho` que `$RS ambiente` grava em `rs_estado.json`, chave `ambiente.skills_irmas`).

1. **Pré-requisitos.** `$RS status` (etapa 09, G6 aprovado); `05-decomposicao/fichamentos_master.csv` com `tipo_estudo`, `b2_estrategia_identificacao` e `b2_modelo_principal` (references/06-decomposicao.md).
2. **Lista de resultados a avaliar.** Escreva `04-qualidade/resultados_avaliados.csv` com `chave,id_estudo,construto_outcome,resultado,ferramenta,classificador` (ex.: `Silva2020,ES0012,desempenho,Tabela 3 col. 4,robins_i,a`). `resultado` vem de `b2_modelo_principal`; `ferramenta` da seção 3; qualitativos e a2 entram com `construto_outcome` vazio. Todo resultado que alimenta a caixa ou a meta-análise tem de estar aqui (MECIR C52). O G7 exige `rob_geral` para cada linha deste arquivo (e, sem ele, para cada `chave` × `construto_outcome` de `efeitos_extraidos.csv`; seção 7).
3. **Rascunho por IA (opcional, registrado no protocolo).** Um subagente por PDF × ferramenta, até 3 em paralelo, com `agentes/avaliador-rob.md` e placeholders preenchidos: `{PDF}=03-textos/pdfs/<chave>.pdf`, `{N_PAGINAS}` (páginas do PDF), `{DATA}` (AAAA-MM-DD), `{CHAVE}`, `{FERRAMENTA}`, `{CODEBOOK}=00-protocolo/codebook_v0_<ferramenta>.csv`, `{RESULTADOS}` (linhas da lista do passo 2 para essa chave), `{CONFUNDIDORES}`, `{SAIDA_DIR}=04-qualidade/<ferramenta>/fichas`, `{AGENTE_ID}`. Não abra as fichas: use a linha de retorno e os scripts.
4. **Gate de citação** (sai 1 se houver problema; `PDF_TEXTO_NAO_EXTRAIVEL` vira conferência visual humana):
   ```bash
   python3 "$FS/verify_citacoes.py" --fichas 04-qualidade/rob2/fichas --pdfs 03-textos/pdfs \
     --out 04-qualidade/rob2/verificacao_citacoes.csv
   ```
   O gate só confere evidências no formato `"trecho" (p. N)` e ignora em silêncio respostas sem trecho. Rode também a checagem de trecho obrigatório (sai 1 se faltar):
   ```bash
   python3 - 04-qualidade/rob2/fichas <<'PY'
   import glob, re, sys
   ok = {"999", "NA_secao", "NA", "SI", "NI", "NPD", "I"}
   ruins = []
   for f in sorted(glob.glob(sys.argv[1] + "/fichamento_*.md")):
       for l in open(f, encoding="utf-8"):
           m = re.match(r"\s*[-*]\s*\*\*(\w+)\*\*\s*—\s*resposta:\s*(.*?)\s*—\s*evid[eê]ncia:\s*(.*)$", l)
           if not m or re.search(r"_propost[oa]$", m.group(1)):
               continue
           resp, ev = (m.group(2).split() or ["999"])[0], m.group(3)
           if resp in ok or resp.startswith("proposta_") or ev.startswith("(metadados"):
               continue
           if not re.search(r'"[^"]+"\s*\(pp?\.?\s*\d', ev):
               ruins.append(f"{f}: {m.group(1)}")
   print("\n".join(ruins) or "ok")
   sys.exit(1 if ruins else 0)
   PY
   ```
   Ficha reprovada vai para um subagente NOVO (nunca corrigir no mesmo contexto).
5. **Consolidar o rascunho** (a mensagem final lista variáveis faltantes; ficha incompleta volta ao passo 3):
   ```bash
   python3 "$FS/consolida.py" --fichas 04-qualidade/rob2/fichas --codebook 00-protocolo/codebook_v0_rob2.csv \
     --out-csv 04-qualidade/rob2/rascunho_master.csv --out-xlsx 04-qualidade/rob2/rascunho_master.xlsx
   python3 -c "import pandas as p; d=p.read_csv('04-qualidade/rob2/rascunho_master.csv', dtype=str); \
     d[[c for c in d if 'propost' not in c]].to_excel('04-qualidade/rob2/rascunho_para_avaliadores.xlsx', index=False)"
   ```
6. **Avaliação independente.** A e B preenchem, sem ver um ao outro, `04-qualidade/rob_<ferramenta>_A.csv` e `_B.csv` (RoB 2, ROBINS-I, EPOC) ou `04-qualidade/apreciacao_<ferramenta>_A.csv`/`_B.csv` (CASP, JBI, MMAT). `qualidade consolidar` aceita três formatos (CSV com vírgula, ponto e vírgula ou tabulação, UTF-8 ou cp1252, ou `.xlsx`):

   | Formato | Colunas |
   |---|---|
   | largo | `chave,id_estudo,construto_outcome,resultado,D1,...,Dk,rob_geral,justificativa,fonte` (checklists: `Q1,...,Qk,preocupacao_metodologica,justificativa,fonte`) |
   | longo | `chave,construto_outcome,dominio,julgamento,trecho,pagina[,id_estudo,justificativa]`, uma linha por domínio |
   | master | `fichamentos_master.csv` da irmã: RoB 2 e ROBINS-I leem `dN_julgamento[_proposto]` e `geral_julgamento[_proposto]`; EPOC e checklists leem as variáveis do codebook; trecho e página saem de `<variavel>__evidencia`; o sufixo de `ficha_id` (`Chave#sufixo`) vira `construto_outcome` |

   Valores com prefixo `proposta_` são aceitos, mas o avaliador daquele arquivo passa a contar como IA. Algoritmo = proposta; sobrepor exige justificativa. Lacuna de relato → e-mail aos autores registrado em `fonte`.
7. **Concordância e fila de desacordos (fase 1).**
   ```bash
   $RS qualidade consolidar --ferramenta rob2 --a 04-qualidade/rob_rob2_A.csv --b 04-qualidade/rob_rob2_B.csv \
     --avaliador-a revisor_humano_1 --avaliador-b revisor_humano_2 [--codebook 00-protocolo/codebook_v0_rob2.csv]
   ```
   A e B precisam cobrir os mesmos resultados e domínios, e todo valor precisa estar no vocabulário da seção 4 (acentos, caixa e inglês são normalizados); senão, código 1 com a lista. O comando grava `04-qualidade/rob_<ferramenta>_concordancia.csv` (por domínio: `n`, `n_desacordos`, proporção de concordância, κ de Cohen, PABAK com k = níveis da escala; `sinalizado` com Po < 0,80 ou κ e PABAK < 0,70, que descreve confiabilidade e não substitui o consenso) e `04-qualidade/rob_<ferramenta>_consenso.csv`, uma linha por resultado × domínio com `chave,id_estudo,construto_outcome,ferramenta,dominio,julgamento_a,julgamento_b,julgamento_consenso,justificativa,trecho,pagina,resolvido_por`. Onde A e B concordam, `julgamento_consenso` já vem preenchido com `resolvido_por = concordancia:<A>+<B>`; nos desacordos fica vazio (a fila humana). No RoB 2, ROBINS-I e EPOC o geral de A e B entra só na concordância (o geral do consenso sai do algoritmo, na fase 2); nas checklists, a linha `dominio = geral` (preocupação metodológica) entra no consenso. Evento `fila_gerada`; no autopiloto, pendência `consenso_rob` com n = desacordos sem resolução humana. Reexecutar não apaga resolução humana (se A ou B mudou naquela linha, a resolução cai com aviso). Avaliadores sem papel humano geram aviso: concordância com eles não valida nada.
8. **Consenso humano e `rob_geral` (fase 2).** Reunião A+B (terceiro se previsto) preenche, em cada desacordo, `julgamento_consenso`, `justificativa` e `resolvido_por` com papel humano (ex.: `revisor_humano_1`). Depois:
   ```bash
   $RS qualidade consolidar --ferramenta rob2 --consenso 04-qualidade/rob_rob2_consenso.csv [--por revisor_humano_1] [--ignorar-no-geral D1,D2]
   ```
   `--por` preenche `resolvido_por` onde ele está vazio e o consenso foi editado (papel não humano é recusado). Faltando consenso válido ou resolução humana em algum desacordo: código 2, lista das linhas, pendência atualizada e nada gravado em `rob_geral`. Com tudo resolvido, o comando aplica o algoritmo ao consenso e grava `04-qualidade/rob_geral.csv` (`chave,id_estudo,construto_outcome,ferramenta,rob_geral,validado_humano`, trocando só as linhas da ferramenta):

   | Ferramenta | `rob_geral` |
   |---|---|
   | RoB 2 | pior domínio (baixo < algumas_preocupacoes < alto); aviso com algumas preocupações em ≥ 2 domínios e nenhum alto (a ferramenta permite julgar alto: decisão humana) |
   | ROBINS-I V2 | pior domínio (baixo_exceto_confundimento < moderado < grave < critico); aviso do julgamento aditivo (vários moderados → grave; vários graves → crítico) |
   | EPOC | pior critério, com incerto = moderado (convenção declarada no protocolo); `--ignorar-no-geral` tira critérios do algoritmo (ex.: sequência e ocultação, altos por definição em antes-depois controlado) |
   | CASP, JBI, MMAT | a linha `dominio = geral` do consenso (preocupação metodológica, sem soma de itens) |

   Uma linha `dominio = geral` com `julgamento_consenso`, `resolvido_por` humano e justificativa sobrepõe o algoritmo, só para um nível igual ou mais grave que o pior domínio. `validado_humano = 1` quando todas as linhas do resultado foram resolvidas por humano ou concordadas por A e B com ao menos um avaliador humano. Registra `rob_consolidado` (consenso, `rob_geral.csv` e concordância como artefatos; `n_desacordos`, `n_validados_humano`, `todos_validados_humano`, `rob_geral`, `regra_geral`, `resolvido_por`), fecha a pendência `consenso_rob` e não grava evento novo se nada mudou. Leia `n_validados_humano` e os avisos: resultado com `validado_humano = 0` não serve ao G7 (o portão bloqueia enquanto `todos_validados_humano` não for verdadeiro na última consolidação da ferramenta). Rode uma consolidação por ferramenta, em qualquer ordem; mudou A, B ou o consenso depois, repita as fases.
9. **Visualização.** RoB 2: `robvis` (0.3.1) exige rótulos em inglês e colunas `Study, D1..D5, Overall, Weight`; o consenso é longo (um domínio por linha), então pivote antes:
   ```r
   library(robvis)
   cons <- read.csv("04-qualidade/rob_rob2_consenso.csv", stringsAsFactors = FALSE)
   geral <- subset(read.csv("04-qualidade/rob_geral.csv", stringsAsFactors = FALSE), ferramenta == "rob2")
   cons <- subset(cons, dominio %in% paste0("D", 1:5))
   largo <- reshape(cons[, c("chave", "construto_outcome", "dominio", "julgamento_consenso")],
                    idvar = c("chave", "construto_outcome"), timevar = "dominio", direction = "wide")
   names(largo) <- sub("^julgamento_consenso\\.", "", names(largo))
   d <- merge(largo, geral[, c("chave", "construto_outcome", "rob_geral")], by = c("chave", "construto_outcome"))
   m <- c(baixo = "Low", algumas_preocupacoes = "Some concerns", alto = "High")
   rv <- data.frame(Study = paste(d$chave, d$construto_outcome), D1 = m[d$D1], D2 = m[d$D2], D3 = m[d$D3],
                    D4 = m[d$D4], D5 = m[d$D5], Overall = m[d$rob_geral], Weight = 1, row.names = NULL)
   ggplot2::ggsave("06-analise/figuras/rob2_semaforo.png", rob_traffic_light(rv, tool = "ROB2"), width = 8, height = 5)
   ggplot2::ggsave("06-analise/figuras/rob2_resumo.png", rob_summary(rv, tool = "ROB2", weighted = FALSE), width = 8, height = 3)
   ```
   Em ensaio por cluster o domínio 1b (`D1b`) fica fora do gráfico do `robvis`: relate-o numa tabela. ROBINS-I V2: NÃO use `tool = "ROBINS-I"` (rótulos e ordem da versão 1); faça tabela. EPOC, CASP, JBI, MMAT: tabela.
10. **Levar `rob_geral` à síntese.** A junção de `04-qualidade/rob_geral.csv` com os efeitos e com o master da caixa não tem comando: siga o passo "Enriquecer efeitos" de references/06-decomposicao.md, seção 8, que lê esse arquivo por `chave` × `construto_outcome`.

## 6. Uso na síntese, no GRADE e no CERQual

| Uso | Como |
|---|---|
| Análise primária | Todos os resultados elegíveis, separados por classe de desenho (`analise meta` e `analise swim` já separam randomizados e não randomizados) |
| Sensibilidade | `meta.R` roda `sensibilidade.sem_alto_risco` quando a coluna `rob_geral` está no arquivo de entrada; com `--excluir-rob critico`, a análise com os críticos vira `sensibilidade.com_rob_critico` |
| Estratificação | `$RS analise meta --in 06-analise/efeitos.csv --moderadores rob_geral` só com k ≥ 3 por nível; ausência de diferença não prova ausência de viés |
| Exclusão pré-especificada | Crítico (ROBINS-I): `$RS analise meta --excluir-rob critico ...`, `$RS analise swim --excluir-rob critico ...` e `$RS analise combinados --excluir-rob critico ...` (exigem a coluna `rob_geral`, senão código 1). A regra é a mesma nos três: o modelo principal (meta), a direção do estudo (SWiM) ou o p por estudo (combinados) é escolhido antes, e só depois o estudo crítico sai da análise principal; a análise com ele fica em `sensibilidade.com_rob_critico`. Os JSON trazem `parametros.excluir_rob`, `n_excluidos_rob_critico` e, por grupo, `excluidos_rob_critico`; `swim_direcao.csv` e `testes_combinados_estudos.csv` ganham a coluna `excluido_rob_critico`, e o effect direction plot e o albatross mostram só a análise principal. ITS com teste t sem reanálise ou outra regra do protocolo: filtre a entrada à mão (`pandas`: `d[~cond]` → `06-analise/efeitos_sem_<regra>.csv`) e rode `--in` nesse arquivo. Não altere `03-textos/elegibilidade_tc_final.csv`: o estudo continua incluído na revisão |
| Caixa de ferramentas | "Positivo/Negativo" sem meta-análise exige que os estudos não sejam só de risco alto (`rs.py caixa --master 05-decomposicao/master_caixa.csv`) |
| GRADE | Domínio "risco de viés" por célula em `06-analise/certeza.csv`; com ROBINS-I, não randomizados partem de certeza alta e em geral caem ao menos dois níveis |
| CERQual | `preocupacao_metodologica` dos estudos de suporte alimenta o componente de limitações metodológicas |
| Proibido | Ponderar por escore de qualidade; excluir por "baixa qualidade" sem previsão |

## 7. Portão G7 (parte RoB) e autopiloto

G7 é um portão só, para extração e RoB: aprove uma vez, com um JSON que junte os critérios abaixo aos da extração (references/06-decomposicao.md). Parte RoB: todo resultado de `resultados_avaliados.csv` com linha em `04-qualidade/rob_geral.csv` e `validado_humano = 1`; A e B completos; gate de citação com 0 problemas; checagem de trecho obrigatório `ok`; concordância por domínio em `rob_<ferramenta>_concordancia.csv`; exclusões pré-especificadas listadas.

```bash
$RS portao G7 --aprovar --por revisor_humano_1 --criterios '{"rob_geral": "04-qualidade/rob_geral.csv", "rob_resultados_avaliados": 18, "rob_todos_validados_humano": true,
  "rob_gate_problemas": 0, "rob_concordancia": "04-qualidade/rob_rob2_concordancia.csv", "rob_excluidos_sintese": 1,
  "rob_rascunho_ia": {"agente": "agentes/avaliador-rob.md", "modelo": "<modelo>", "codebooks": ["00-protocolo/codebook_v0_rob2.csv"]}}'
```

O `portao G7` confere, na parte RoB, fora de `escopo` e `mapa_evidencias`, cada ferramenta pelo seu último evento `rob_consolidado`:

| Checagem | Tipo de bloqueio |
|---|---|
| nenhum `rob_consolidado`; fase 1 (`fila_gerada` da fila `consenso_rob`) de uma ferramenta sem a fase 2; ferramenta citada em `resultados_avaliados.csv` sem consolidação | artefato (barra também o autopiloto) |
| arquivo citado no último `rob_consolidado` da ferramenta (consenso, concordância) mudou ou sumiu; `rob_geral.csv` diferente do que a última consolidação gravou (as linhas das outras ferramentas são conferidas pela contagem, distribuição e `validado_humano` registradas no evento de cada uma) | artefato: consolide de novo |
| resultado avaliado sem linha com `rob_geral` em `04-qualidade/rob_geral.csv`: vale `04-qualidade/resultados_avaliados.csv` (por `chave`, `construto_outcome` e `ferramenta`, acentos e caixa ignorados; `construto_outcome` vazio casa com qualquer outcome da mesma chave) e, sem ele, cada `chave` × `construto_outcome` de `05-decomposicao/efeitos_extraidos.csv` | artefato |
| último `rob_consolidado` da ferramenta sem `todos_validados_humano = true` (concordância só entre avaliadores não humanos, ou consolidação antiga sem o campo) | validacao: barra a aprovação humana; vira pendência no autopiloto |

O gate e a checagem de trecho das fichas continuam conferência sua. A `proxima_acao` do `status` na etapa 09 traz o comando da fase que falta (`qualidade consolidar --ferramenta <f> --consenso ... --por revisor_humano_1`, ou a fase 1 com `<avaliação A>` e `<avaliação B>`). Pendência aberta da etapa 09 ou do G7 bloqueia a aprovação humana (código 2) até ser fechada. No autopiloto, a fase 1 abre `consenso_rob` com os desacordos; julgamentos humanos que faltam por outro motivo viram pendência manual antes de aprovar como `autopiloto`:

```bash
$RS pendencia abrir --tipo rob_humano --etapa 09_extracao_rob --portao G7 --n 18 \
  --arquivo 04-qualidade/resultados_avaliados.csv --descricao "A, B e consenso de RoB por resultado"
```

Os produtos seguem com "RASCUNHO NÃO VALIDADO" até a pendência fechar (`consenso_rob` fecha com a fase 2; as manuais, com `$RS pendencia fechar P00N --motivo "consenso concluído" --por revisor_humano_1`); depois refaça a junção de references/06-decomposicao.md, seção 8, e regenere `analise efeitos`, `analise meta`, `analise swim` e `caixa`.

## 8. Armadilhas

| Armadilha | Como evitar |
|---|---|
| Hierarquia 0–6 ou SMS usada como "qualidade" | SMS só como elegibilidade e descritor; RoB por domínio |
| DiD classificado como seleção em observáveis | Classe `diferenciacao` (Waddington); perguntas de tendências prévias em `qe_testes_pressupostos` |
| Avaliar o estudo inteiro | Uma linha por resultado em `resultados_avaliados.csv` |
| `S` sem trecho passa no gate | Checagem de trecho obrigatório do passo 4 |
| Resposta truncada do subagente | `consolida.py` lista variáveis faltantes; ficha incompleta é refeita |
| Punir falta de duplo-cego em política social | Pergunte se quem MEDIU sabia a alocação; registros administrativos objetivos tendem a `PN` |
| Rótulo fora do vocabulário (`serious`, `muito alto` com espaço) | Use os valores da seção 4; `qualidade consolidar` normaliza acentos, caixa e inglês e recusa o resto (código 1) |
| `S`/`PS`/`SI` do RoB 2 no ROBINS-I V2 | Códigos oficiais `Y`, `PY`, `PN`, `N`, `NI`, `WN`/`SN`, `SY`/`WY` (seção 4) |
| Consenso digitado sem registrar quem resolveu | `resolvido_por` humano em todo desacordo (ou `--por`); a fase 2 recusa sem ele |
| ROBINS-I V2 no modelo ROBINS-I do `robvis` | Tabela própria |
| Misturar SMS original e ajustada | Declarar a versão; `desenho_maryland.csv` segue a ajustada |
| Nota técnica do gestor rebaixada automaticamente | Registrar `vinculo_institucional` (codebook OQF) e julgar pelo desenho |
| Revisão ou meta-análise avaliada como estudo | Fora da síntese primária; AMSTAR 2/ROBIS só em overview |

## 9. O que registrar e relatar

Registre: ferramenta e versão por desenho; hash dos codebooks (congelados no G2, emendas no log); modelo e data do rascunho por IA; avaliadores por papel; julgamentos de A, B e consenso (`rob_<ferramenta>_consenso.csv`, evento `rob_consolidado`); concordância e desacordos por domínio (`rob_<ferramenta>_concordancia.csv`) e como foram resolvidos (`resolvido_por`); contatos com autores; exclusões pré-especificadas; figuras e tabelas.

| Norma | Item | O que a revisão mostra |
|---|---|---|
| PRISMA 2020 | 11 | Ferramentas, quantos avaliadores, independência, automação (rascunho por IA) |
| PRISMA 2020 | 13e, 13f, 20d | Estratificação e sensibilidade por RoB e seus resultados |
| PRISMA 2020 | 18, 20a | RoB de cada estudo incluído e dos estudos de cada síntese (semáforo ou tabela) |
| PRISMA 2020 | 15, 22 | Certeza com o domínio de risco de viés |
| PRISMA 2020 | 23b, 24c, 27 | Limitações da evidência; emendas (troca de ferramenta ou versão); formulários publicados |
| PRISMA-ScR | 12, 16 | Apreciação crítica só se feita, com justificativa e resultados |
| MECIR | C52–C55 (obrigatórios); C56–C58 e C60 | RoB de ao menos um resultado por estudo (C52); dupla independente (C53); justificativa e fonte (C54, C55); resultados da tabela-resumo avaliados (C56); resumo por desfecho (C57); uso na síntese (C58); conflitos de interesse dos estudos (C60) |
| PRISMA-trAIce e RAISE | uso de IA | `$RS declaracao-ia` gera a declaração do log; o uso do `avaliador-rob` entra pelos critérios do G7 |
