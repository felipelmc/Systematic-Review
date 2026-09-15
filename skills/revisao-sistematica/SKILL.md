---
name: revisao-sistematica
description: >-
  Conduz revisões sistemáticas de ponta a ponta (efetividade com ou sem meta-análise, avaliação de políticas no formato OQF misto e sequencial, escopo, qualitativa, rápida) com estado auditável e retomável: pergunta e teoria do programa (PICOC/CMMO, DAG), protocolo, strings por base, importação e deduplicação (WoS, Scopus, SciELO, OpenAlex, CAPES/BDTD, Scholar), funil com contagens, triagem por subagentes ou API com validação humana (recall, kappa), textos completos, bola de neve, risco de viés, extração, meta-análise e SWiM em R, GRADE/CERQual, caixa de ferramentas e PRISMA calculado. Use quando pedirem para "fazer/continuar uma revisão sistemática", "montar o protocolo", "triar títulos e resumos", "deduplicar as bases", "gerar o PRISMA", "rodar a meta-análise", "avaliar uma política com revisão sistemática", ou "systematic review", "scoping review", "abstract screening", "PRISMA flow diagram". Delega PDFs a baixar-pdfs-academicos, extração a fichamento-sistematico e .bib a gerar-bibtex.
license: MIT (código) e CC BY 4.0 (textos e modelos); ver LICENSE.txt
compatibility: Python >= 3.10; R >= 4.2 opcional (meta-análise); Quarto opcional
---

# Revisão sistemática de ponta a ponta

Esta skill conduz uma revisão sistemática (RS) inteira ou só uma etapa, sempre com o mesmo projeto em disco, um log de eventos append-only e portões de decisão humana. O método combina as normas internacionais (Cochrane, Campbell/MECCIR, JBI, PRISMA 2020 e extensões, GRADE, CERQual, RAISE) com a proposta "O que funciona?" (OQF) de avaliação de políticas públicas por RS mista e sequencial.

## Regras invioláveis

1. **Comece toda sessão com `rs status`** e volte a rodá-lo depois de cada onda de subagentes. Nunca deduza o estado da conversa. Projeto em subpasta: `rs --dir "<subpasta>" status` (sem projeto na pasta atual, o `status` lista `projetos_em_subpastas` e `projetos`, com título, etapa atual e último evento, e sugere o mais recente; com mais de um, pergunte ao usuário; nunca rode `init` por cima). Chamado com `--dir`, o `status` já devolve os comandos sugeridos com o `--dir`.
2. **Nunca edite à mão** `rs_estado.json`, `rs_log.jsonl`, `dados/decisoes.jsonl` ou `dados/registros*.csv`. Só `rs.py` escreve neles, com trava entre processos (`.rs.lock` na raiz): comandos em chamadas de Bash paralelas (ex.: `triagem mesclar` de A e de B) não perdem eventos nem pendências. Estado corrompido sai com código 1 e a dica de restaurar do controle de versão.
3. **Protocolo antes da busca.** Critérios, ferramentas de risco de viés, codebook v0, codebook de elegibilidade, plano de síntese e plano de uso de IA são congelados no G2. Mudança depois disso é emenda registrada com `rs emenda --arquivo <arquivo> --motivo "..."`.
4. **Humano é responsável** (RAISE). G1 e G2 exigem aprovação humana em qualquer modo. Nos outros portões, o autopiloto segue, mas abre pendências e marca os produtos com "RASCUNHO NÃO VALIDADO" até que sejam fechadas.
5. **Nada por título.** Junções só por `id_rs`, `id_registro` ou `chave`.
6. **Filtros etiquetam, não excluem**, salvo previsão no protocolo com amostra de elusão. Registro sem resumo nunca é excluído por filtro textual nem por LLM (vira `incerto`).
7. **Direção do efeito pelo estimador**, não pela significância. Nunca escreva "sem efeito" porque p > 0,05. Testes combinados (Fisher, Stouffer, Winer, Cooper) são secundários e nunca definem rótulos.
8. **Estudo ≠ relato ≠ efeito.** Revisões e meta-análises não entram como estudos primários. Preprint e versão publicada são relatos ligados do mesmo estudo, nunca fundidos.
9. **Resumo de subagente não é prova.** Só `mesclar`, os gates de citação e as checagens dos scripts confirmam que um trabalho foi feito.
10. **Contagens nunca são digitadas.** PRISMA, métricas e declaração de IA saem dos arquivos. Na `proxima_acao` e nos exemplos, `<...>` é placeholder: troque pelo valor conferido no arquivo indicado (colado sem trocar, o JSON é inválido e o comando falha).

## Como chamar os comandos (bash e zsh)

Cada chamada de Bash abre um shell novo. Em cada chamada, defina a função e use-a na mesma linha, ou escreva o caminho completo:

```bash
rs() { python3 "${CLAUDE_SKILL_DIR}/scripts/rs.py" "$@"; }; rs status   # onde estou, pendências, próxima ação
python3 "${CLAUDE_SKILL_DIR}/scripts/rs.py" --help                      # todos os comandos
```

Nas instruções desta skill, `rs` é essa função. Nas references, nos agentes, nos templates e na `proxima_acao` do `status`, `$RS` é a mesma abreviação: troque por `rs` (com a função definida na chamada) ou pelo caminho completo. Não crie uma variável `RS="python3 ..."`: no zsh (padrão do macOS), `$RS status` com espaços dentro da variável falha. `${CLAUDE_SKILL_DIR}` só é substituído neste arquivo; onde as references escrevem `<pasta da skill>`, use o caminho que aparece acima. `--dir <pasta>` vem antes do subcomando.

Dependências: `python3 -m pip install -r "${CLAUDE_SKILL_DIR}/scripts/requirements.txt"` (opcionais em `requirements-opcional.txt`). R: `install.packages(c("meta","metafor","esc","irr","clubSandwich","robvis","jsonlite"))`. `rs ambiente` diz o que falta e como a skill degrada.

## Início de um projeto

1. Rode `rs status`. Se já existir projeto (nesta pasta ou em subpasta), siga a `proxima_acao`.
2. Se não existir, converse com o usuário e decida: tipo de revisão provisório (e se é revisão rápida), pasta, idioma dos produtos, modo de autonomia (`checkpoints` por padrão ou `autopiloto`), modo de triagem (`subagentes` por padrão; `api` para corpora grandes). Então: `rs --dir "<pasta>" init --titulo "..." --tipo <tipo> [--variante rapida] --autonomia <modo> --triagem <modo>`. Num projeto existente, `init` sem `--titulo` só muda modo (e tipo ou variante antes do G1). `init` recusa pasta dentro de outro projeto e pasta que já contém projeto em subpasta.
3. Leia [references/00-configuracao-estado.md](references/00-configuracao-estado.md) e [references/tipos-de-revisao.md](references/tipos-de-revisao.md) antes de propor o tipo de revisão.

## Etapas, portões e onde está cada instrução

| Etapa | O que acontece | Leia | Comandos e skills | Portão |
|---|---|---|---|---|
| 1 Pergunta e tipo | X, Y, M, Z; escala da pergunta; RS existentes; título-modelo; tipo de revisão | [01-pergunta-protocolo](references/01-pergunta-protocolo.md), [tipos-de-revisao](references/tipos-de-revisao.md) | `buscar openalex --contar` e `--listar N` (exploração, sem importar) | **G1** humano |
| 2 Teoria e framework | teoria do programa, DAG com incentivos perversos, PICOC + CMMO (ou PCC, SPIDER...) | [01-pergunta-protocolo](references/01-pergunta-protocolo.md) | DAG em Mermaid (`00-protocolo/dag_v1.mmd`) ou arquivo dagitty em `00-protocolo/` (não há script de DAG) | — |
| 3 Protocolo | template, critérios a priori (C1...C6), codebook de elegibilidade, RoB por desenho, codebook v0, plano de síntese e de IA, âncoras de validação, registro OSF; revisor metodológico | [01-pergunta-protocolo](references/01-pergunta-protocolo.md) | `assets/templates/protocolo.md`, `assets/codebooks/`, [agentes/revisor-metodologico.md](agentes/revisor-metodologico.md) | **G2** humano |
| 4 Busca | strings por base PT/EN/ES, PRESS, estudos-âncora e recall, APIs e exportações manuais com metadados PRISMA-S, log PRISMA-S | [02-busca](references/02-busca.md) | `buscar openalex` (campos `*.search.exact`; `--substituir`), `importar --string-id --executada-em --n-base` (`--substituir`), `dedup`, `filtrar --ancoras` | **G3** |
| 5 Organização | importação, dedup auditável (preprint e publicado ligados como relatos), funil que etiqueta, elusão do dicionário | [03-organizacao-triagem](references/03-organizacao-triagem.md) | `importar`, `dedup` (`--revisar --por`), `filtrar` (`--amostra-elusao`, `--calcular-elusao`) | — |
| 6 Triagem T/A | critérios vN, calibração humana, desenvolvimento, rodada completa, fila humana, validação (recall, κ, PABAK), elusão, estabilidade | [03-organizacao-triagem](references/03-organizacao-triagem.md), [ia-validacao](references/ia-validacao.md) | `triagem preparar/mesclar/consolidar/override` ou `triagem api`; `validar amostrar/elusao/calcular/estabilidade` com `--finalidade` | **G4** |
| 7 Textos e elegibilidade | PDFs, inventário e conferência, contato com autores, retratações, elegibilidade com decisão humana (inclui `aguardando`), ligação de relatos, bola de neve | [04-textos-elegibilidade](references/04-textos-elegibilidade.md) | `textos para-baixar/inventario/contato-autores/retratacoes/elegibilidade consolidar/ligar-relatos`, `triagem fila --etapa tc` e `triagem override --fila --etapa tc`, `bola-de-neve`; **baixar-pdfs-academicos**; **fichamento-sistematico** com codebook de elegibilidade | **G5** |
| 8 Piloto de extração | 2 a 3 estudos por bloco (a1/a2/b1/b2) | [06-decomposicao](references/06-decomposicao.md) | **fichamento-sistematico**; `analise preparar-efeitos` nos b2 do piloto | **G6** |
| 9 Extração e RoB | decomposição, efeitos com trecho e página (inclusive desfechos binários), risco de viés por domínio em dupla, consenso e `rob_geral` | [05-qualidade](references/05-qualidade.md), [06-decomposicao](references/06-decomposicao.md) | **fichamento-sistematico**; [agentes/extrator-efeitos.md](agentes/extrator-efeitos.md); [agentes/avaliador-rob.md](agentes/avaliador-rob.md); `analise preparar-efeitos`, `analise verificar-efeitos`, `qualidade consolidar` (fase 1 `--a --b`; fase 2 `--consenso`) | **G7** |
| 10 Síntese e certeza | comparabilidade; meta-análise ou SWiM; síntese qualitativa; integração; GRADE/CERQual; caixa de ferramentas (`caixa-3`, com linha de painel) | [07a-sintese-quantitativa](references/07a-sintese-quantitativa.md), [07b-sintese-qualitativa-integracao](references/07b-sintese-qualitativa-integracao.md) | `analise efeitos`, `analise meta`, `analise swim` (`--excluir-rob critico` nos dois, se previsto; `analise combinados` só como secundária); `06-analise/certeza.csv`; `caixa`; [agentes/sintetizador-quali.md](agentes/sintetizador-quali.md) | **G8** |
| 11 Relato | template por tipo, PRISMA do ledger (SVG e PNG), checklists, declaração de IA, .bib, revisão de estilo | [08-relato](references/08-relato.md) | `prisma`, `bib`, `declaracao-ia` (por último), `incluidos`; **gerar-bibtex**; **tirar-cara-de-ia** | **G9** |

Portão aprovado ou reprovado: `rs portao G4 --aprovar --por revisor_humano_1 --criterios '{...}'`. Os portões G1-G9 têm checagens de artefato e limiar (código 2, lista `bloqueios` e `avisos`; tabela completa em [00-configuracao-estado](references/00-configuracao-estado.md), seção 4). Em resumo: G2 exige protocolo, `00-protocolo/codebook_v0*.csv` e codebook de elegibilidade sem placeholders; G3 exige PRESS registrado (`01-busca/press_*.md` ou pendência `revisao_press`) e nenhuma busca ativa truncada; G4 exige a validação da rodada ativa (ou, na variante rápida com `atalho_rapida` no G1, o atalho de dupla humana em ≥ 20%); G7 exige efeitos verificados e, salvo escopo e mapa, `rob_consolidado` validado por humano em cada ferramenta, com `rob_geral` para todo resultado avaliado; G8 exige `06-analise/certeza.csv` com uma linha por célula de efeito e, em OQF, a caixa; G9 exige PRISMA atual e declaração de IA. Etapa que o tipo dispensa (escopo G7-G8, mapa G6-G8, realista G4): `rs portao G8 --nao-se-aplica --por revisor_humano_1 --motivo "..."`. Pendências: `rs pendencia listar` e `rs pendencia fechar P003 --motivo "..."`.

## Modos de autonomia

- **checkpoints** (padrão): pare em cada portão, mostre ao usuário o resumo (números, arquivos, riscos) e só siga com aprovação explícita.
- **autopiloto**: pare só em G1 e G2. Nos demais portões, aplique os critérios automáticos de [references/00-configuracao-estado.md](references/00-configuracao-estado.md); o que depende de humano (PRESS, codificar amostra de validação, conferir incluídos, verificar dados de efeito, consenso de RoB, assinar rótulos) vira pendência (os comandos abrem as suas; para outras, `rs pendencia abrir --tipo ... --etapa ... --descricao ...`), e relatório, PRISMA e declaração de IA saem com "RASCUNHO NÃO VALIDADO". Tarefa humana que já tem pendência aberta vem no `status` com `exige_humano: true` e, em `alternativa`, o próximo passo que não depende dela: siga por ele e peça a tarefa ao usuário. Ao fechar pendências, regenere os produtos que dependem delas.

## Pedidos parciais

| Pedido | Caminho |
|---|---|
| "só a triagem" (planilha/exportação qualquer) | `init --parcial triagem` → `importar` → `dedup` → critérios em `02-triagem/prompts/ta_v1.md` → `triagem preparar/mesclar/consolidar` ou `triagem api` → `validar amostrar/calcular` → G4 (revisão pequena, com menos de 36 incluídos humanos possíveis: remédio 5 e `--forcar --motivo` humano) |
| "só as strings de busca" | ler [02-busca](references/02-busca.md) (seção 13); `buscar openalex --contar` funciona sem projeto; não criar projeto se o usuário não quiser |
| "só o PRISMA" | com projeto (`init --parcial prisma`): `prisma` a partir do ledger (etapas ignoradas saem como NR); sem projeto: `prisma --manual contagens.json --saida <pasta>` |
| "só a meta-análise" (CSV com médias/DP, t/df, coeficiente/EP ou proporções), sem PDFs | `init --parcial meta` → CSV no formato de [agentes/extrator-efeitos.md](agentes/extrator-efeitos.md), com `evidencia` apontando a fonte do usuário (arquivo, tabela, linha) e `verificado_humano = sim` só se o usuário declarar que conferiu os números nela → `analise preparar-efeitos --entrada <csv>` → `analise efeitos` → `analise meta` (ou `analise swim`) → GRADE humano em `06-analise/certeza.csv` → G8 (`caixa` só se pedida: sem master, a linha de implementação fica pendente e o G8 exige `--forcar` humano). Não rode `verificar-efeitos` (sem PDFs, sai `PDF_NAO_ENCONTRADO`; a etapa 9 está ignorada): `preparar-efeitos` já aponta `analise efeitos` e os dois resumos avisam quantas linhas não têm `verificado_humano`. O relato diz que os números não foram verificados contra os PDFs pela skill ([00-configuracao-estado](references/00-configuracao-estado.md), seção 7) |
| "baixar PDFs", "fichar", "gerar .bib" | delegue direto à skill irmã correspondente, sem abrir projeto |

## Subagentes

- Triagem T/A: `triagem preparar` gera lotes de 20 a 30 registros por revisor; lance no máximo 4 subagentes por onda com o prompt de [agentes/triador-ta.md](agentes/triador-ta.md) (árbitro: [agentes/arbitro-cego.md](agentes/arbitro-cego.md), com um terceiro modelo, preferencialmente de outro provedor). Cada subagente lê critérios e lote, escreve só `lote_NNN.resposta.json` e devolve uma linha. Depois: `triagem mesclar`. Lote rejeitado vai para um subagente NOVO. Com A e B mesclados, o resumo do `mesclar` e o `status` sugerem o árbitro nas divergências antes do `consolidar`. Divergências arbitradas também vão à fila humana.
- Leitura de texto completo (elegibilidade, RoB, extração, efeitos): um PDF por subagente, até 3 em paralelo, leitura em faixas de até 20 páginas cobrindo o documento inteiro.
- O coordenador não abre lotes, respostas nem PDFs; trabalha com os resumos JSON dos scripts.
- Acima de ~1.500 registros (ou 800 com dupla triagem), proponha o modo API (`triagem api --estimar` mostra custo e tempo sem chamar a API e registra a estimativa no log; o modo API envia títulos e resumos a provedores externos: peça consentimento).
- Planilhas que humanos preenchem (filas, listas de IDs, planilhas de validação e de elusão, âncoras, codebooks) podem voltar em CSV com vírgula, ponto e vírgula ou tabulação (UTF-8, UTF-16 ou cp1252 do Excel) ou em `.xlsx`: todos os comandos usam o mesmo leitor.
- Variante rápida com `atalho_rapida` no G1: `validar amostrar --atalho-rapida` (dupla em ≥ 20%), `validar calcular`, `validar segunda-leitura` dos excluídos pela IA e `validar calcular` de novo gravam os campos que o G4 lê (references/tipos-de-revisao.md, seção 6).

## Skills irmãs

| Skill | Entrada que esta skill prepara | Volta | Junção |
|---|---|---|---|
| baixar-pdfs-academicos | `03-textos/para_baixar.csv` (`chave,titulo,autores,ano,doi,id_rs`), saída em `03-textos/pdfs` e `03-textos/relatorio_pdfs.csv` | `relatorio_pdfs.csv`, `verificacao_conteudo.csv` | `chave` |
| fichamento-sistematico | codebooks de `assets/codebooks/` copiados para `00-protocolo/` e congelados no G2 (elegibilidade, RoB, decomposição OQF com classificador `tipo_estudo`) | fichas, `fichamentos_master.csv`, gate de citações, concordância | `citekey == chave` |
| gerar-bibtex | `07-relatorio/incluidos.csv` | `references.bib` | `chave` |
| tirar-cara-de-ia | relatório `.qmd` | texto revisado | — |

Se uma irmã não estiver instalada (`rs ambiente` informa), use o fallback descrito na referência da etapa. Preferências pessoais de estilo do usuário (por exemplo, uma skill ou comando de voz própria) entram só como preferência registrada no estado.

## Referências

- [00-configuracao-estado.md](references/00-configuracao-estado.md): init, modos, checagens dos portões, pendências, retomada, projetos parciais.
- [tipos-de-revisao.md](references/tipos-de-revisao.md): matriz de tipos, árvore de escolha e variante rápida.
- [01-pergunta-protocolo.md](references/01-pergunta-protocolo.md), [02-busca.md](references/02-busca.md), [03-organizacao-triagem.md](references/03-organizacao-triagem.md), [04-textos-elegibilidade.md](references/04-textos-elegibilidade.md), [05-qualidade.md](references/05-qualidade.md), [06-decomposicao.md](references/06-decomposicao.md), [07a-sintese-quantitativa.md](references/07a-sintese-quantitativa.md), [07b-sintese-qualitativa-integracao.md](references/07b-sintese-qualitativa-integracao.md), [08-relato.md](references/08-relato.md).
- [ia-validacao.md](references/ia-validacao.md): protocolo de validação de LLMs e declaração de uso de IA.
- [armadilhas.md](references/armadilhas.md): erros que invalidam revisões e como a skill os bloqueia.
- Fundamentação das regras: Apêndice D da base de conhecimento (especificação metodológica) e as normas citadas em cada reference.

## Limitações conhecidas

- Revisão realista iterativa completa, QCA computacional, mapas de evidências interativos, overviews com matriz de sobreposição e bibliometria avançada são orientados pelas referências, mas não têm comandos dedicados nesta versão.
- Bases por assinatura (WoS, Scopus) dependem de exportação manual pelo usuário; a skill importa os arquivos.
- Métricas de validação só existem depois que humanos codificam as amostras; sem isso, os produtos permanecem como rascunho.
- Sem comando nesta versão (contorno na referência da etapa): `log_buscas.csv` (manual); junção de `04-qualidade/rob_geral.csv` aos efeitos (bloco de references/06-decomposicao.md, seção 8); remédio "IA só prioriza com critério de parada". O recall das âncoras no G3 só gera aviso, e o sha dos filtros não é comparado ao protocolo.
- A concordância da extração só gera aviso no G7 (o RoB é conferido: último `rob_consolidado` de cada ferramenta com `todos_validados_humano` e `rob_geral` para todo resultado avaliado). O G9 só avisa (não bloqueia) sem `.bib` ou com declaração de IA atrás do log.
