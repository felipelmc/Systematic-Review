# Organização e triagem de títulos e resumos (etapas 5 e 6, portão G4)

Leia também `references/ia-validacao.md` antes de usar qualquer decisão de IA para excluir.

## Sumário

1. Entradas, saídas e regras gerais
2. Importar exportações
3. Deduplicar e revisar candidatos
4. Funil formal que etiqueta
5. Critérios de triagem e rodadas
6. Triagem por subagentes, onda a onda
7. Árbitro, consolidação, fila humana e override
8. Triagem via API (consentimento e `--estimar`)
9. Portão G4
10. Armadilhas e o que registrar

`$RS` abrevia `python3 "<pasta da skill>/scripts/rs.py"` (SKILL.md, "Como chamar os comandos"): em cada chamada de Bash, use a função `rs` definida na mesma chamada ou o caminho completo, nunca uma variável `RS`. Rode todo comando na raiz do projeto e comece cada sessão com `$RS status`.

## 1. Entradas, saídas e regras gerais

| Passo | Lê | Escreve |
|---|---|---|
| `importar` | exportação da base | `01-busca/brutos/`, `dados/registros.csv`, `dados/registros_flags.csv` (retratado pelo OpenAlex) |
| `dedup` | `dados/registros.csv`, `registros_flags.csv` | `dados/registros_unicos.csv` (`id_rs`, `chave`, `id_estudo`, `flags`), `01-busca/dedup_pares.csv` |
| `filtrar` | `registros_unicos.csv` + JSON (+ âncoras) | `02-triagem/filtro_formal.csv`, `02-triagem/filtro_formal_contagens.json`, `01-busca/recall_ancoras.json`, planilha e métricas de elusão |
| `triagem preparar/mesclar` | critérios + registros | `02-triagem/lotes/<rodada>/<revisor>/`, `dados/decisoes.jsonl` |
| `triagem consolidar` | `decisoes.jsonl` | `02-triagem/triagem_ta_final.csv`, `02-triagem/fila_humana_<rodada>.csv`, `versoes_ativas.rodada_ta` no estado |

- Só `rs.py` escreve `rs_estado.json`, `rs_log.jsonl`, `dados/decisoes.jsonl` e `dados/registros*.csv`.
- Junções só por `id_registro`, `id_rs` ou `chave`. Nunca por título.
- Registro sem resumo nunca é excluído por filtro nem por IA: vira `incerto` e segue ao texto completo.
- `incerto` conta como "segue" (recall primeiro).

## 2. Importar exportações

1. Formato desconhecido: `$RS importar --arquivo <arquivo> --simular` (não exige projeto; mostra a detecção e uma amostra).
2. Um comando por arquivo exportado: `$RS importar --arquivo <arquivo> --busca-id B01 [--estrutura PICOC] --string-id S-base-v1 --executada-em AAAA-MM-DD --n-base N [--filtros-na-base "..."] [--plataforma "..."]` (metadados PRISMA-S: references/02-busca.md, seção 3, passo 9).
   - Prefixo do `--busca-id` define o método: `B` base, `SN` citação, `CZ` cinzenta, `MN` manual (ou `--metodo`).
   - Base que exporta em partes (WoS, 1.000 por arquivo): mesmo `--busca-id` para todas as partes.
   - Leitor forçado: `--fonte wos|scopus|openalex|scielo|pop|zotero|ris|capes|bdtd|generico`. Planilha arbitrária: `--mapa mapa.json` (chaves = colunas de `registros.csv`, valores = colunas do arquivo, por exemplo `{"colunas": {"titulo": "Title", "resumo": "Abstract", "ano": "Year", "doi": "DOI", "autores": "Authors"}}`).
   - Busca superada (string corrigida depois das âncoras ou do PRESS): `--substituir <busca_id_antiga> --motivo "..."`. A antiga fica inativa, sem apagar linhas, e sai de `dedup`, `filtrar`, amostras e PRISMA.
3. Confira `n_importados` contra `--n-base` e o N do log de buscas (PRISMA-S item 15). Diferença sem explicação: pare e pergunte ao usuário.
4. Não importe o mesmo arquivo em duas buscas; `--permitir-repetido` só com justificativa (infla "identificados" no PRISMA).
5. Leia os `avisos`: registros do OpenAlex com `is_retracted` (`n_retratados`) ficam em `dados/registros_flags.csv`, o `dedup` os marca com a flag `retratado` e a checagem de retratações da etapa 7 os confere; resumos do Publish or Perish chegam com `resumo_truncado=1`.

## 3. Deduplicar e revisar candidatos

`$RS dedup` (limiares padrão `--limiar-auto 95 --limiar-candidato 85`; mude só com justificativa no protocolo).

| Regra em `dedup_pares.csv` | Decisão do script | O que fazer |
|---|---|---|
| `R1_doi`, `R2_id_fonte`, `R3_titulo_exato` | `auto` | Nada |
| `R4_fuzzy_auto` | `auto` | Humano confere a lista; fusão errada: copie a linha do par para a planilha de revisão com `decisao=rejeitado` |
| `versao` (preprint ou working paper ↔ versão publicada), escore ≥ limiar-auto, mesmo sobrenome e anos presentes | `ligado` (`decidido_por=script`) | **Nunca funde.** Os dois registros ficam com `id_rs` próprios e o mesmo `id_estudo` em `registros_unicos.csv` e em `03-textos/ligacao_relatos.csv`; cada relato segue sozinho para a triagem (em economia, as versões costumam diferir em amostra e estimativas). Humano confere; ligação errada: `decisao=rejeitado` na planilha de revisão (desfaz a ligação na mesma execução) |
| `versao` sem os requisitos da ligação automática, ou que juntaria dois publicados no mesmo estudo (`ligaria_dois_publicados_no_estudo`) | `candidato` (a ligação) | Humano decide: `ligado` (ou `confirmado`, gravado como `ligado`) liga os relatos; `rejeitado` separa. Num par de versão, nenhuma decisão funde |
| `R5_candidato` | `candidato` | 100% decididos por humano |
| `rejeitado` com `decidido_por=regra` (tese ↔ artigo, Part I/II, numerais) | nunca funde | Ligar relatos na etapa 7 (`textos ligar-relatos`), não fundir; `confirmado` ou `ligado` num par tese ↔ artigo é recusado com aviso |

Projeto antigo, em que preprint e publicado estavam fundidos num cluster: o próximo `dedup` separa o cluster, o `id_rs` antigo fica com um dos relatos, o outro ganha id novo, os dois são ligados e o resumo avisa "RSxxxx (novo) reúne registros que estavam em RSyyyy": trie o id novo (na mesma rodada, com `--ids`). Ligações feitas à mão com `textos ligar-relatos` são preservadas pelo `dedup`. Sem mudança nos arquivos, sem decisão humana nova e com os mesmos parâmetros, o `dedup` não grava evento novo (`reexecucao: true`, `evento_registrado: false`).

Revisão de candidatos (quando o resumo mostra `candidatos_pendentes > 0`):

1. Monte a planilha com títulos para o humano (as colunas extras são ignoradas na leitura):

```bash
python3 - <<'EOF'
import csv
reg = {l["id_registro"]: l for l in csv.DictReader(open("dados/registros.csv", encoding="utf-8-sig"))}
pares = [p for p in csv.DictReader(open("01-busca/dedup_pares.csv", encoding="utf-8-sig"))
         if p["decisao"] == "candidato" and "resolvido_transitivamente" not in p["motivo"]]
for p in pares:
    p["titulo_a"], p["titulo_b"] = reg[p["id_a"]]["titulo"], reg[p["id_b"]]["titulo"]
w = csv.DictWriter(open("01-busca/dedup_revisao_v1.csv", "w", newline="", encoding="utf-8"), fieldnames=list(pares[0]))
w.writeheader(); w.writerows(pares)
EOF
```

2. Humano preenche `decisao` (`confirmado`, `rejeitado` ou, só em par de regra `versao`, `ligado`), `decidido_por` (papel, nunca nome) e `motivo`. Linhas deixadas como `candidato` ficam separadas. Linhas `ligado` do próprio script, copiadas de `dedup_pares.csv`, são ignoradas.
3. `$RS dedup --revisar 01-busca/dedup_revisao_v1.csv --por revisor_humano_1`. Quem decidiu é obrigatório: `decidido_por` preenchido em cada decisão ou `--por` (vazio, `script` ou `regra` em `--por` são recusados); sem nenhum dos dois, código 1 e nada é gravado. A `proxima_acao` do `status` sugere o `--revisar`; acrescente o `--por` se a planilha não tiver `decidido_por`.
4. Repita até `candidatos_pendentes = 0`. Avisos `confirmação recusada` indicam tese × artigo: vão para ligação de relatos. Linhas com `decisao=candidato` e `resolvido_transitivamente` no `motivo` já ficaram no mesmo cluster por outras arestas e não contam: o resumo traz `candidatos_pendentes` (o n da pendência) e `candidatos_resolvidos_transitivamente`, e a soma dos dois é o `candidato` de `pares_por_decisao`.
5. No autopiloto, o `dedup` abre a pendência `dedup_candidatos`; ela fecha sozinha quando zeram os candidatos. Não decida candidatos pelo usuário.
6. Buscas substituídas: o resumo traz `buscas_inativas`, `n_registros_inativos` e `n_unicos_inativos`. Cluster que só tem registros de buscas inativas fica em `registros_unicos.csv` com a flag `busca_inativa` (trilha de auditoria) e fora do conjunto ativo. `filtrar`, `triagem preparar`, `triagem api`, `validar amostrar`/`elusao`/`estabilidade`, `bola-de-neve` e `prisma` já os ignoram (inclusive quando pedidos em `--ids`); os resumos trazem `n_inativos_ignorados`. Rode `dedup` logo depois de `importar --substituir`: sem a flag, o `prisma` ainda tira esses clusters do fluxo, mas avisa que falta o `dedup`. Registro da busca nova com o mesmo DOI ou id da fonte de um cluster inativo vira id novo: há um aviso por cluster só quando o id antigo já tinha decisão de triagem (trie o id novo); sem decisão a herdar, sai um aviso agregado com a contagem.

Registrar: limiares, backend de similaridade (`backend_similaridade`), `duplicatas_removidas_por_tipo`, nº de pares revisados e por quem, buscas substituídas e motivo (PRISMA-S item 16).

## 4. Funil formal que etiqueta

1. `01-busca/filtros_v1.json` vem da etapa de busca (copiado de `assets/templates/filtros_v1.json` e ajustado ao protocolo; tipos de filtro: `ano` com `min`/`max`; `tipo` e `idioma` com `aceitar` ou `recusar`; `dicionario` com `dicionario`, `grupos`, `campos`, `modo`) e foi congelado no G3. Nova versão = novo arquivo; mudança no congelado = emenda.
2. Âncoras: as de validação em `00-protocolo/ancoras_validacao.csv` (congeladas no G2, montadas por quem não escreve as strings; o coordenador não abre) e as de desenvolvimento em `01-busca/ancoras_desenvolvimento.csv`, ambas no modelo `assets/templates/ancoras.csv` (references/02-busca.md, seção 7).
3. `$RS filtrar --config 01-busca/filtros_v1.json --ancoras 00-protocolo/ancoras_validacao.csv` (grava também `01-busca/recall_ancoras.json`; o resumo traz `n_inativos_ignorados` quando há buscas substituídas).

| Situação | Regra |
|---|---|
| Padrão | `"modo": "etiquetar"`: quem falha segue para a triagem com etiqueta |
| `"modo": "excluir"` | Só com `"previsto_no_protocolo": true`; senão exit 2 |
| Excluir por dicionário | Exige também `"validacao_elusao"`; se ela aponta para o `*_metricas.json` de `--calcular-elusao`, o filtro precisa constar nele com o mesmo dicionário, grupos e campos (senão exit 2); texto livre é aceito com aviso de que não foi verificado |
| Excluir por idioma, ou tipo que atinja tese, dissertação, relatório, evento, preprint, livro ou capítulo | Exige `"justificativa"` (relatada como limitação) |
| Campo ausente, sem resumo ou resumo truncado | `sem_dado`: o registro segue |
| Âncora excluída | Exit 2: corrija o filtro ou volte a `etiquetar` |

**Elusão do dicionário** (só se o protocolo prevê excluir por dicionário):

1. Com os filtros em modo `etiquetar`: `$RS filtrar --config 01-busca/filtros_v1.json --amostra-elusao 300 --semente 7` sorteia até 300 registros etiquetados pelos filtros de dicionário (todos, se houver menos) e grava a planilha cega `02-triagem/validacao/elusao_<versao>_cega.xlsx` (sem etiqueta nem termo) e `elusao_<versao>_desenho.json`. Repetir com os mesmos parâmetros não sorteia de novo; parâmetros diferentes para a mesma versão saem com código 1.
2. Um humano (dois, se o protocolo pedir) preenche `decisao_h1` (e `decisao_h2`, `decisao_consenso`); vazio = não revisado.
3. `$RS filtrar --calcular-elusao 02-triagem/validacao/elusao_<versao>_cega.xlsx` grava `elusao_<versao>_metricas.json` (taxa conservadora, com incluir ou incerto como relevante perdido, e taxa estrita, ambas com IC de Clopper-Pearson, e relevantes perdidos estimados), registra `validacao_calculada` com `finalidade` `elusao` e preenche `validacao_elusao` na configuração, se ela estiver no projeto e não congelada. Congelada (caso normal, depois do G3): o resumo traz o trecho a acrescentar; acrescente-o e registre `$RS emenda --arquivo 01-busca/filtros_v1.json --motivo "..."`, ou crie `filtros_v2.json` com a exclusão.
4. Não há limiar automático para a taxa: a decisão de trocar para `excluir` é humana, com o número à vista e `previsto_no_protocolo`. Na dúvida, não exclua: filtros existem para ordenar a fila.

Registrar: config e sha (vão para o log), contagens por filtro de `filtro_formal_contagens.json` (caixa "automação" do PRISMA 2020 item 16a só quando houver exclusão).

## 5. Critérios de triagem e rodadas

1. Copie `assets/templates/criterios_triagem.md` para `02-triagem/prompts/ta_v1.md` e preencha com o usuário a partir do protocolo congelado (G2): critérios C1…Cn na ordem de aplicação, estudar × mencionar com exemplos, sem resumo → incerto.
2. Convenção: rodada = nome do arquivo sem extensão (`ta_v1.md` → rodada `ta_v1`). O `status` segue essa convenção. A rodada que vale para o PRISMA e o G4 é a da última consolidação (`versoes_ativas.rodada_ta`, gravada por `triagem consolidar`); rodadas `*_estab` nunca são consolidadas nem recebem override; a calibração sem IA usa rodada própria (`calib_v1`, references/ia-validacao.md).
3. Uma rodada congela o sha dos critérios: mudou uma palavra, crie `ta_v2.md` e rodada `ta_v2`. Critério novo ou mudado depois do G2 é emenda: `$RS emenda --arquivo 00-protocolo/protocolo.md --motivo "..."`.
4. Antes de triar o corpus: calibração humana (A), conjunto de desenvolvimento (B) e plano de validação (C–G) como em `references/ia-validacao.md`.

## 6. Triagem por subagentes, onda a onda

Padrão até ~1.500 registros (ou ~800 com dupla triagem); acima disso, proponha o modo API (seção 8).

1. Prepare os lotes de cada revisor de IA (embaralhamento distinto por revisor):
   `$RS triagem preparar --etapa ta --rodada ta_vN --revisor A --criterios 02-triagem/prompts/ta_vN.md [--tamanho 25] [--semente 7]`
   e o mesmo com `--revisor B`. Use `--ids <csv com id_rs>` para restringir (conjunto de desenvolvimento, bola de neve).
2. Do resumo JSON use só `lotes_pendentes` (pares `lote`/`resposta`), `criterios` e `agente_prompt`. Não abra lotes nem respostas.
3. Onda: até 4 subagentes em paralelo, cada um com UM lote. Prompt = conteúdo de `agentes/triador-ta.md` com `{CRITERIOS}`, `{LOTE}` e `{RESPOSTA}` trocados pelos caminhos absolutos. Se puder escolher modelos, use modelos diferentes para A e B e anote o identificador exato de cada um.
4. Cada subagente devolve uma linha (`OK lote_NNN: ...` ou `FALHA lote_NNN: ...`). A linha não prova nada.
5. Depois de cada onda:
   - `$RS triagem mesclar --rodada ta_vN --revisor A --modelo <id-do-modelo>` (e B). Exit 1 com `rejeitados` é esperado quando algum lote falhou na validação. A `proxima_acao` do resumo segue a ordem do `status`: lotes pendentes de algum revisor → `triagem mesclar` desse revisor; divergências entre A e B sem árbitro → `triagem preparar --revisor arbitro --apenas-divergentes` (em `proxima_acao_detalhe.alternativa`, a regra liberal, só se o protocolo a previu); senão `triagem consolidar`.
   - Lote rejeitado (IDs faltando, extras ou duplicados; enum inválido; critério inexistente; exclusão sem critério; trecho que não está no título/resumo; exclusão de registro sem resumo): despache um subagente NOVO para o mesmo lote. Nunca corrija a resposta à mão.
   - `$RS status`.
6. Repita até `lotes_pendentes` vazio para A e B.

| Parâmetro | Valor | Por quê |
|---|---|---|
| `--tamanho` | 20–30 (padrão 25; árbitro 20) | Sensibilidade cai com lotes grandes; tamanho é congelado com o prompt |
| Subagentes por onda | ≤ 4 | Controle de falhas e custo |
| Rejeição repetida (≥ 2) do mesmo lote | Reporte ao usuário com os `erros` do resumo | Pode ser critério ambíguo ou registro problemático |

## 7. Árbitro, consolidação, fila humana e override

1. Com A e B completos: `$RS triagem preparar --etapa ta --rodada ta_vN --revisor arbitro --criterios 02-triagem/prompts/ta_vN.md --apenas-divergentes`. Exit 1 com "não há divergências" = nada a arbitrar. O `status` já pede este passo: com lotes não mesclados nos manifestos, a `proxima_acao` é `triagem mesclar --revisor X`; com divergências de A e B com parecer de IA e sem árbitro, é o `preparar` do árbitro (alternativa: `consolidar --regra liberal`, se o protocolo previu). Dupla humana e modo API vão direto ao `consolidar`.
2. Despache `agentes/arbitro-cego.md` (mesmos placeholders) com um terceiro modelo, diferente de A e B e preferencialmente de outro provedor; `$RS triagem mesclar --rodada ta_vN --revisor arbitro --modelo <id>`.
3. `$RS triagem consolidar --rodada ta_vN --regra consenso` (ou `--regra liberal` se a validação exigir; a mesma regra vai para `validar`). Rodadas `*_estab` são recusadas. O consolidar grava `versoes_ativas.rodada_ta` = a última `--rodada` e o resumo traz `rodada_ativa`, `fila_humana`, `motivos_fila` e `arbitradas_na_fila`.

| Situação | Resultado em `triagem_ta_final.csv` | Fila humana (`motivo_fila`) |
|---|---|---|
| Override humano | decisão humana (`decidido_por=humano`) | não |
| A e B concordam | consenso; incluir × incerto = `incerto` | não |
| Divergem, com árbitro (`consenso`) | decisão do árbitro (vale para o fluxo) | sim (`arbitrada`): conflito de IA vai a humano (validação F), que confirma ou corrige por override |
| Divergem, sem árbitro (`consenso`) | `incerto` | sim (`divergencia`) |
| Divergem (`liberal`) | segue (`incluir`/`incerto`) | sim (`divergencia_regra_liberal`) |
| Exclusão não humana de registro sem resumo | rebaixada a `incerto` | não |

4. Fila: humano preenche `decisao_humana`, `criterio_humano` (obrigatório em exclusões) e `motivo_humano` em `02-triagem/fila_humana_ta_vN.csv`, inclusive nas linhas `arbitrada` (pode repetir a decisão do árbitro; comece pelas arbitradas com `excluir`); depois
   `$RS triagem override --fila 02-triagem/fila_humana_ta_vN.csv --por revisor_humano_1` e `$RS triagem consolidar --rodada ta_vN`. A fila (e a pendência `fila_humana_triagem` no autopiloto) só zera quando toda linha tiver override.

| Regra da fila e do override | Operação |
|---|---|
| Formato da planilha | a fila pode voltar do Excel em CSV com vírgula, ponto e vírgula ou tabulação (com ou sem BOM; UTF-8, UTF-16 ou cp1252, este com aviso) ou em `.xlsx`; nomes de coluna sem diferença de caixa. Cabeçalho sem `id_rs` e `decisao_humana` sai com código 1 e não altera nenhum arquivo. `openpyxl` ausente com `.xlsx`: código 3 |
| Fila preservada | `triagem consolidar` lê a fila antes de gravar: se há linhas preenchidas que o ledger ainda não tem como override equivalente, a fila não é regravada (`fila_preservada: true`, `linhas_fila_nao_aplicadas` e a `proxima_acao` com `override --fila`). Nenhuma decisão humana se perde por reconsolidar antes de aplicar |
| Critério obrigatório | exclusão humana (fila ou `--id`) exige critério, conferido contra os IDs da rodada: `ids_criterios` dos manifestos dos lotes ou `02-triagem/api/<rodada>/criterios.md`. `C2` vale como apelido único de `c2_...` e é gravado com o nome canônico. Inclusão com critério é recusada. Rodada sem nenhuma fonte de critérios (ex.: planilha de dupla humana): `--criterios 02-triagem/prompts/ta_vN.md` |
| Tudo ou nada | uma linha com erro (critério ausente ou inexistente, decisão inválida) faz a fila inteira não gravar nada; o erro lista todas as linhas |
| Roteamento | a fila da T/A (`fila_humana_<rodada>.csv`) não é aceita com `--etapa tc`, e a do texto completo (`03-textos/fila_humana_tc.csv`) exige `--etapa tc` |
| Buscas substituídas | clusters `busca_inativa` saem do `triagem_ta_final.csv`, da fila e de `sem_decisao` (`n_inativos_ignorados` no resumo e no evento) |

5. Override pontual: `$RS triagem override --id RS0042 --decisao incluir --motivo "..." --por revisor_humano_1`; exclusão: `$RS triagem override --id RS0042 --decisao excluir --criterio C2 --motivo "..." --por revisor_humano_1`. Sem `--rodada`, vale a rodada ativa (numa consolidação de várias rodadas, a última em que o registro tem decisão); `*_estab` é recusada. `--por` padrão: `revisor_humano_1`.
6. Quem codifica a amostra de validação às cegas não pode ter visto os pareceres da IA: codifique a validação antes de resolver a fila, ou use outras pessoas.
7. Avisos do `consolidar`: `sem_decisao > 0` (lotes faltando), `revisor_unico` (triagem dupla incompleta). Resolva antes do G4.
8. Bola de neve (etapa 7): re-triagem na MESMA rodada e critérios, com `--ids` só dos novos `id_rs`; depois `consolidar` da mesma rodada.

## 8. Triagem via API (consentimento e `--estimar`)

Proponha acima de ~1.500 registros. O modo envia título, resumo, palavras-chave, veículo, ano, tipo e idioma de cada registro a provedores externos.

1. **Consentimento.** Diga ao usuário o que é enviado, a quais provedores, que os termos de uso podem permitir treino e o custo estimado. Só siga com "sim" explícito. Registre: plano de IA do protocolo antes do G2; depois do G2, atualize o protocolo e rode `$RS emenda --arquivo 00-protocolo/protocolo.md --motivo "triagem via API: envio de títulos e resumos a <provedores>, autorizado pelo usuário"`.
2. **Modo:** `$RS init --triagem api` (na raiz, sem `--titulo`; registra `modo_definido`).
3. **Ambiente:** `$RS ambiente` (`modo_api_possivel`, `chaves_api`). Chaves só por variável de ambiente (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`); pacotes `anthropic`/`openai` de `scripts/requirements-opcional.txt`. Nunca leia `.env`.
4. **Estimar (sem chamadas):**
   `$RS triagem api --rodada ta_vN --criterios 02-triagem/prompts/ta_vN.md --modelo-a <modelo> --modelo-b <modelo> --arbitro <modelo> --estimar [--batch] [--taxa-divergencia 0.2] [--precos precos.json]`
   Mostre `custo_total_usd`, `por_papel`, `sem_resumo_regra`, `modelos_sem_preco` e `precos_consultados_em` (tabela a verificar na documentação do provedor). A estimativa vai para o log (`artefato_versionado` com `tipo=estimativa_custo_api`; o resumo traz `evento_seq`) e a declaração de IA a lista à parte, sem somar ao custo.
5. **Piloto:** mesmo comando sem `--estimar`, com `--limite 20` (e o mesmo `--precos`, que também calcula o custo registrado). Confira `pendentes`, `ultimos_erros`, `trechos_descartados`.
6. **Rodada:** repita o comando sem `--limite` (retoma pela chave `id_rs`+rodada+papel; nada é pago duas vezes). Exit 1 com `pendentes > 0`: rode de novo o mesmo comando. Exit 3: pacote ou chave ausente. `--batch`: repita até `lotes_em_andamento = 0` e `pendentes = 0`. Cada execução com chamadas registra no evento `custo_estimado_usd`, `custo_por_papel` (com custo médio por chamada), `custo_estimado_rodada_usd`, `tabela_precos` e `modelos_sem_preco`; é o que `declaracao-ia` soma.
7. `$RS triagem consolidar --rodada ta_vN` e passos 4–8 da seção 7.

| Regra | Aplicação |
|---|---|
| A ≠ B | Obrigatório; prefira provedores diferentes (aviso se iguais) |
| Árbitro | Terceiro modelo, diferente de A e B (o script recusa) e preferencialmente de outro provedor (só há adaptadores `anthropic` e `openai`: com dois provedores, declare a limitação); vê "Revisor A/B" sem nome de modelo |
| Rodada congelada | Critérios, prompts, modelos e `--esforco` ficam em `02-triagem/api/<rodada>/parametros.json`; mudou algo, nova rodada |
| Sem resumo | Linha `revisor=regra`, `incerto`, sem chamada |
| `--divergencia` | `binaria` (padrão, igual à consolidação); `rotulo` só para análise |
| `temperature` | Omitido automaticamente onde o modelo rejeita (família Claude 5, Opus ≥ 4.7) |

## 9. Portão G4

O script bloqueia a aprovação (exit 2) se: falta `02-triagem/triagem_ta_final.csv` (artefato); não há validação com `finalidade` `validacao` calculada para a rodada ativa (`validacao`; calibração, desenvolvimento, elusão e estabilidade nunca contam, mesmo calculadas depois); a última validação dessa rodada não atende (recall ≥ 0,95 com limite inferior ≥ 0,90; limiar); contagens de organização/triagem não fecham (artefato); há pendência aberta da etapa 06 ou do G4. Evento antigo sem `finalidade` ou sem `rodada` conta como validação, com aviso em `avisos`.

Antes de pedir aprovação, mostre ao usuário: registros importados por busca, duplicatas por tipo, candidatos revisados, filtros e contagens, rodada e regra, divergências e fila resolvida, métricas da validação com IC, elusão, estabilidade e riscos.

- Checkpoints: `$RS portao G4 --aprovar --por revisor_humano_1 --criterios 02-triagem/validacao/ta_vN/amostraNN_metricas.json` (o JSON do `validar calcular`, sem digitar números).
- Autopiloto: `--por autopiloto`; validação ausente vira pendência, limiar não atingido barra; abre `revisao_humana_portao`.
- Validação reprovada: leia `motivo_reprovacao` no resumo de `validar calcular`. `desempenho_ia` (há falsos negativos): remédios da seção 4 E de references/ia-validacao.md. `humanos` (a dupla humana discordou): consenso e recalibração, não critérios novos para a IA. `largura_ic` (0 falsos negativos, só o limite inferior do IC falhou): não revise critérios; o resumo traz `incluidos_humanos_necessarios` (36) e `incluidos_ia_nao_sorteados` e sugere nova amostra enriquecida da mesma rodada (`validar amostrar ... --semente <outra> --enriquecer-incluidos N`) ou `validar elusao`.
- Revisão pequena (menos de 36 incluídos humanos possíveis, ou `incluidos_ia_nao_sorteados` abaixo de 36): limiar inalcançável; siga o remédio 5 (dupla humana completa) e só um humano aprova com `$RS portao G4 --aprovar --por revisor_humano_1 --forcar --motivo "..."`. O `status` aponta esse caminho.
- Variante rápida com `atalho_rapida` aprovado no G1: dupla humana em ≥ 20%, κ e segunda leitura de todos os excluídos pela IA substituem o recall ≥ 0,95 (references/tipos-de-revisao.md, seção 6; references/00-configuracao-estado.md, seção 4).
- Reprovar: `$RS portao G4 --reprovar --por revisor_humano_1 --motivo "..."` (descongela os critérios).
- Aprovar congela `02-triagem/prompts/*.md`.

## 10. Armadilhas e o que registrar

| Armadilha | Defesa |
|---|---|
| Amostra de calibração ou desenvolvimento sorteada como validação | `validar amostrar --finalidade calibracao` (ou `desenvolvimento`): só `validacao` da rodada ativa decide o G4 |
| Override numa rodada que não é a consolidada | Sem `--rodada` vale a rodada ativa; confira `rodadas` no resumo |
| Mudar critérios dentro da rodada | `preparar` recusa; crie `ta_vN+1` |
| Confiar na linha do subagente | Só `mesclar` confirma |
| Excluir registro sem resumo | `mesclar` rejeita; consolidação rebaixa a `incerto` |
| Divergência arbitrada sem olho humano | Entra na fila (`motivo_fila=arbitrada`) até override |
| Dicionário que exclui sem elusão | `filtrar` recusa (exit 2); amostra com `--amostra-elusao` |
| Busca substituída triada | `preparar`, `triagem api`, `validar` e `consolidar` já tiram os clusters `busca_inativa` (seção 3, passo 6) |
| Resposta do subagente corrigida à mão | Proibido: novo subagente |
| Fila salva pelo Excel com ponto e vírgula | Aceita pelo `override`; `consolidar` não regrava fila com decisões não aplicadas |
| Exclusão humana sem critério | `override` recusa; motivo do PRISMA nunca fica vazio |
| Preprint e versão publicada fundidos | `dedup` liga os relatos (`ligado`, mesmo `id_estudo`) em vez de fundir |
| Reprovação por IC largo tratada como falha da IA | `motivo_reprovacao = largura_ic`: ampliar a amostra ou remédio 5, não critérios vN+1 |

Relato (PRISMA 2020 item 8; item 16a; PRISMA-S itens 15 e 16; MECIR C39 e C41): fontes e N por busca; regras e software de deduplicação com pares revisados; filtros e modo; número de revisores por registro, independência, modelos e versão dos critérios; regra de consolidação e resolução de conflitos; validação da IA (com os números do `validar calcular`); exclusões por automação separadas das humanas.
