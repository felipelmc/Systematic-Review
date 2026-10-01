# 08 — Relato: template por tipo, PRISMA do ledger, checklists, declaração de IA, estilo e G9

Etapa 11, fechada no portão **G9**. Para a caixa de ferramentas e `certeza.csv`, leia também references/07b-sintese-qualitativa-integracao.md.

## Sumário

1. Pré-requisitos
2. Template e diretrizes por tipo de revisão
3. Passos com comandos
4. Placeholders: convenção e fonte de cada valor
5. Formato OQF: seção por seção, com itens PRISMA
6. Painel OQF e policy brief
7. Checklists
8. Passe de estilo (opcional, fora da skill)
9. Marca de rascunho
10. Pacote aberto (PRISMA 2020 item 27)
11. O que o G9 exige
12. Armadilhas

`$RS` abrevia `python3 "<pasta da skill>/scripts/rs.py"` (SKILL.md, "Como chamar os comandos"): em cada chamada de Bash, use a função `rs` definida na mesma chamada ou o caminho completo, nunca uma variável `RS`.

## 1. Pré-requisitos

| Item | Como conferir |
|---|---|
| G8 aprovado (ou pendência de revisão humana aberta no autopiloto) | `$RS status` |
| Pendências conhecidas | `$RS pendencia listar` (abertas decidem a marca de rascunho) |
| Caixa final, se o tipo tem caixa | `$RS caixa ...` com `n_pendentes: 0` |
| Quarto instalado (render) | `$RS ambiente` (`quarto: true`); sem Quarto, entregue o `.qmd` e os arquivos gerados |

## 2. Template e diretrizes por tipo de revisão

O tipo está em `projeto.tipo_revisao` (saída de `$RS status`). Templates em `<pasta da skill>/assets/templates/`; checklists em `<pasta da skill>/assets/checklists/`.

| `tipo_revisao` | Template | Diretriz principal | Complementos | `prisma --tipo` (padrão do comando) |
|---|---|---|---|---|
| `efetividade_meta` | `manuscrito_prisma.qmd` | PRISMA 2020 (27 itens + 12 do resumo) | PRISMA-S | `2020` |
| `efetividade_swim` | `manuscrito_prisma.qmd` | PRISMA 2020 | SWiM (itens 13 e 20 relatados pelo SWiM), PRISMA-S | `2020` |
| `oqf_mista_sequencial` | `relatorio_oqf.qmd` | PRISMA 2020 | PRISMA-S; SWiM se alguma célula sem meta-análise; ENTREQ no ramo qualitativo | `2020` |
| `escopo` | `relatorio_escopo.qmd` | PRISMA-ScR (20 + 2 opcionais) | PRISMA-S; estratégia completa de todas as bases | `scr` |
| `mapa_evidencias` | `relatorio_escopo.qmd` | guia Campbell de EGM | PRISMA-S; total de estudos informado à parte da matriz | `scr` |
| `qualitativa` | `manuscrito_prisma.qmd` | ENTREQ | eMERGe (meta-etnografia); PRISMA 2020 para o fluxo | `2020` |
| `realista` | `manuscrito_prisma.qmd` | RAMESES (19 itens; "síntese realista" no título) | PRISMA 2020 para o fluxo | `2020` |
| `metodos_mistos` | `relatorio_oqf.qmd` | PRISMA 2020 | ENTREQ; guia JBI de revisões mistas | `2020` |
| `rapida` ou `projeto.variante = rapida` | template do tipo de origem (`manuscrito_prisma.qmd` se `rapida`) | diretriz do tipo de origem | atalhos declarados como limitação do processo (item 23c) | o do tipo de origem |
| `guarda_chuva` | `manuscrito_prisma.qmd` | PRIOR (27 itens) | sobreposição entre revisões relatada | `2020` |
| qualquer, para gestores | `policy_brief.qmd` (derivado) | — | mesmos números e rótulos do relatório | — |

Sem `--tipo`, `prisma` usa `scr` para `escopo` e `mapa_evidencias` e `2020` nos demais. Regras: extensão não substitui o PRISMA 2020; o fluxograma segue as fontes realmente usadas (o SVG mostra o ramo "outros métodos" quando houve bola de neve, cinzenta ou manual); uso de IA é relatado nos itens 8, 9 e 11 do PRISMA 2020 e na declaração gerada, com o PRISMA-trAIce só como lista de conferência (não declarar conformidade).

## 3. Passos com comandos

1. `$RS status` e `$RS pendencia listar`.
2. Fluxograma: `$RS prisma` (`--tipo 2020|scr` só para trocar o padrão do tipo; `--idioma en` para produtos em inglês). Escreve em `07-relatorio/`: `prisma_contagens.json`, `prisma.mermaid`, `prisma.svg`, `prisma.png` (rasterizado do SVG com pymupdf; falha na conversão vira aviso em `avisos`) e `checklist_prisma.csv`. Saída 2 = invariante quebrada (mensagens `INVARIANTE QUEBRADA` no stderr; inclui `avaliado_nao_recuperado` e `decisoes_de_busca_substituida`): nada é desenhado; corrija o ledger (por exemplo, decida os `incerto` do texto completo) e rode de novo. Campos `NR` saem de etapas sem artefato ou ignoradas (`etapas_nr`). O JSON traz, por ramo, `aguardando_classificacao` (caixa própria no fluxograma) e, no topo, `buscas_inativas` (buscas substituídas, fora de "identificados"), `buscas_truncadas` e `motivos_rascunho`. Busca ativa truncada: aviso, rascunho e "Buscas truncadas: B01" no SVG e no Mermaid (substitua a busca antes do relato; references/02-busca.md, seção 5). Em fontes genéricas (planilha, leitor `generico`), o rótulo por fonte usa a plataforma declarada na busca (`importar --plataforma`) ou o `busca_id`, também na evidência do item 6 do checklist. Pedido "só o PRISMA": `$RS prisma --manual contagens.json [--saida <pasta>]`, com a mesma estrutura de `prisma_contagens.json` (aceita `aguardando_classificacao`).
3. Referências: `$RS incluidos` (escreve `07-relatorio/incluidos.csv`; `--fonte ta` só em projeto parcial de triagem) e `$RS bib` (chama `gerar-bibtex` com a `chave`; `--sem-irma` escreve o `.bib` mínimo). Aviso "chaves do .bib diferem de incluidos.csv" bloqueia o relato até resolver.
4. Caixa final (tipos com caixa): `$RS caixa --master 05-decomposicao/master_caixa.csv --faixas "<faixas do protocolo>"` (sem `master_caixa.csv`, use `fichamentos_master.csv`).
5. Copie o template para o projeto, sem editar o original: `cp "<pasta da skill>/assets/templates/relatorio_oqf.qmd" 07-relatorio/relatorio.qmd` (policy brief: `07-relatorio/policy_brief.qmd`). O template espera, na mesma pasta, `prisma.svg`, `declaracao_uso_ia.md` e `references.bib`, e a caixa em `../06-analise/caixa_ferramentas.md`.
6. Preencha os placeholders pela seção 4. Todo número vem de arquivo gerado; texto livre vem dos autores ou de rascunho aprovado por eles.
7. Checklists (seção 7).
8. Declaração de IA por último, depois de todos os eventos: `$RS declaracao-ia` (escreve `07-relatorio/declaracao_uso_ia.md` a partir do log; nunca editar à mão; `--out` só para outro caminho). A parte narrativa que o log não escreve sai do modelo `assets/templates/declaracao_uso_ia.md`, salvo como `07-relatorio/declaracao_uso_ia_texto.md`, com números copiados do arquivo gerado; o texto curto dele preenche `{{VALIDACAO_TEXTO_CURTO_IA}}` e o arquivo gerado entra no apêndice por include.
9. Render: `quarto render 07-relatorio/relatorio.qmd` (HTML e DOCX; o DOCX só embute `prisma.svg` com `rsvg-convert` instalado; sem ele, troque `prisma.svg` por `prisma.png` na figura do `.qmd` antes do render DOCX). Antes, confira que não sobrou placeholder: `grep -nE '\{\{[A-Z0-9_]+\}\}' 07-relatorio/*.qmd` deve voltar vazio.
10. Passe de estilo, se houver (seção 8), e novo render.
11. Marca de rascunho (seção 9) e G9 (seção 11).

Ao fechar pendências (`$RS pendencia fechar <id> --motivo "..."`), o comando devolve `regenerar`; rode os comandos listados, `$RS caixa` se a pendência era de certeza, e renderize de novo.

## 4. Placeholders: convenção e fonte de cada valor

Nos templates `.qmd`, placeholders são `{{PREFIXO_NOME}}`; comentários `<!-- ... -->` trazem a instrução e o item da diretriz. O prefixo diz de onde vem o valor. Nunca use `<...>` como placeholder em `.qmd`: o Pandoc pode tratá-lo como HTML e apagar o texto.

| Prefixo | Fonte obrigatória | Exemplos de campo |
|---|---|---|
| `{{N_*}}` | `07-relatorio/prisma_contagens.json` | `N_BASES` = `bases.identificados.bases` (e `por_fonte`); `N_DUPLICATAS` = `bases.removidos_antes_triagem.duplicatas`; `N_AUTOMACAO` = `...automacao` (e `automacao_por_filtro`); `N_OUTROS_MOTIVOS`; `N_TRIADOS` = `bases.triados`; `N_EXCLUIDOS_TRIAGEM`; `N_BUSCADOS`; `N_NAO_RECUPERADOS`; `N_AVALIADOS`; `N_EXCLUIDOS_TC` = `excluidos_elegibilidade.total` (e `motivos`); `N_AGUARDANDO_CLASSIFICACAO` = soma de `aguardando_classificacao` dos ramos; `N_OUTROS_METODOS` = `outros_metodos.identificados.*`; `N_ESTUDOS_INCLUIDOS` = `incluidos.estudos`; `N_RELATOS_INCLUIDOS` = `incluidos.relatos` |
| `{{META_*}}` | `06-analise/meta_resumo.json` (grupo da célula) | `META_K` = `k_estudos`; `META_G`, `META_IC` = `resultado.estimativa`, `resultado.ic`; `META_TAU2`, `META_I2`, `META_PI`; `META_SENSIBILIDADE`; `META_VERSAO_METAFOR` = `parametros.pacotes.metafor` |
| `{{SWIM_*}}` | `06-analise/swim_resumo.json` | `n_estudos`, `n_beneficos`, `proporcao_benefica`, `ic_proporcao`, `p_sinal` |
| `{{CAIXA_*}}` | `06-analise/caixa_ferramentas.csv` | `rotulo`, `forca`, `certeza`, `escala`, `pontos_implementacao`, `enunciado`, `estudos`, `regra_versao` |
| `{{CERTEZA_*}}` | `06-analise/certeza.csv` | domínios rebaixados e justificativa |
| `{{BUSCA_*}}` | `01-busca/strings/`, log de buscas, `estado.buscas` (`string_id`, `executada_em`, `n_bruto`, `filtros_na_base`, `plataforma`; substituídas com `ativa: false` e motivo) e `01-busca/recall_ancoras.json` | quadro de strings por base, data da última busca, recall das âncoras |
| `{{PROTOCOLO_*}}` | `00-protocolo/` e `00-protocolo/emendas.md` | PICOC/PCC, registro OSF, δ, faixas, emendas |
| `{{MAPA_*}}` | `fichamentos_master.csv` e tabelas derivadas dele (escopo e mapa de evidências) | matriz intervenção × desfecho, características por fonte |
| `{{VALIDACAO_*}}` | `07-relatorio/declaracao_uso_ia.md` (seção 4) e `07-relatorio/declaracao_uso_ia_texto.md` | recall, IC, κ, PABAK, elusão; `VALIDACAO_TEXTO_CURTO_IA` = texto curto da parte narrativa |
| `{{TEXTO_*}}` | autores (humano decide; o coordenador pode rascunhar) | título, introdução, interpretação, financiamento, conflitos |

Regra: número em `{{TEXTO_*}}` é proibido. Na auditoria, cada `{{N_*}}`, `{{META_*}}`, `{{SWIM_*}}` e `{{CAIXA_*}}` preenchido é reconferido contra o arquivo-fonte.

## 5. Formato OQF: seção por seção, com itens PRISMA 2020

| Seção (`relatorio_oqf.qmd`) | Conteúdo mínimo | Itens |
|---|---|---|
| Título | pergunta X→Y + "revisão sistemática mista e sequencial" | 1 |
| Resumo estruturado | objetivos, critérios, fontes e data da última busca, RoB, síntese, n de estudos e participantes, resultados com IC e certeza, limitações, financiamento, registro | 2 |
| 1 Introdução | X→Y, contexto e marco legal, teoria do programa (DAG), revisões existentes e por que esta, objetivo | 3, 4 |
| 2 Metodologia | protocolo, registro, desvios; quadro PICOC (e CMMO) | 5, 24a–c |
| 2.1 Busca | quadro de strings por base (base, string exata, filtros, data, n), outros métodos, PRISMA-S em apêndice | 6, 7 |
| 2.2 Seleção e elegibilidade | revisores por fase, independência, IA com validação e limiares, fluxo (`prisma.svg`), excluídos limítrofes | 8, 16a, 16b |
| 2.3 Sistematização e análise | extração e verificação, codebook, RoB por desenho, métrica e conversões, comparabilidade, modelo, dependência, SWiM, síntese qualitativa, integração, certeza, regra da caixa com versão | 9–15 |
| 3.1 Efeito | por célula: características e RoB, estimativa com IC, τ², I², PI, sensibilidade, viés de publicação, certeza em cada enunciado | 17–22 |
| 3.2 Mecanismo, 3.3 Moderadores, 3.4 Percepção | enunciados com estudos e CERQual; moderador testado × hipótese | 20c, 22; ENTREQ |
| 3.5 Implementação e custo | rótulo, pontos, CERQual; custo unitário ou "não reportado" | 20a, 22 |
| 4 Da evidência à prática: implicações | caixa (resumo e apêndice completo), EtD-lite, transferibilidade ao Brasil, implicações proporcionais à certeza | 23d |
| 5 Conclusões e limitações | interpretação diante de outras revisões; 5.1 limitações da evidência; 5.2 limitações do processo (idiomas, bases, filtros, IA, relatos não recuperados, análises planejadas e não feitas) | 23a–c |
| Informações adicionais | registro e emendas, financiamento, conflitos, disponibilidade de dados e código, uso de IA | 24–27 |
| Apêndices | caixa completa (include), declaração de IA (include), checklists | — |

Melhorias obrigatórias sobre o formato da proposta OQF: certeza em todo enunciado; rótulo Inconclusivo; limitações do processo separadas; declaração de IA gerada do log; disponibilidade de dados e código com endereço exato.

## 6. Painel OQF e policy brief

Linha do painel = a linha `dimensao = efeito_painel` de `caixa_ferramentas.csv` (uma por família × construto), gerada da mesma tabela do relatório. Ela resume os corpos por classe de desenho pela regra da `caixa-3` (vale o corpo de maior certeza, com o outro anotado na justificativa; empate de certeza com rótulos diferentes = Inconclusivo; references/07b-sintese-qualitativa-integracao.md, seção 10). Os corpos por desenho (linhas `efeito`) ficam no relatório e na ficha do painel; o policy brief usa a linha de painel e cita a divergência quando a `regra_aplicada` é `painel_maior_certeza` ou `painel_empate_desenho`:

| Coluna do painel | Campo | Exibição |
|---|---|---|
| Intervenção | `familia_intervencao` | nome usado no Brasil |
| Resultado | `construto_outcome` | um construto por linha |
| Efeito | linha `efeito_painel`: `rotulo`, `escala`, `certeza`, `k`, `regra_aplicada` | "Inconclusivo · g = ... (IC ...; PI ...) · certeza muito baixa · 8 estudos"; sem faixas, sem magnitude; com corpos divergentes, "randomizados: Positivo (moderada); não randomizados: Inconclusivo (baixa)" na ficha |
| Implementação | linha `implementacao`: `rotulo`, `pontos_implementacao`, `certeza` | rótulo · pontos · CERQual · principal requisito |
| Custo | linha `custo`: `rotulo` | valor com ano e moeda, ou "sem informação" |
| Ficha | data da última busca, países, estudo brasileiro sim/não, `regra_versao`, links | obrigatória |

Proibido: "Neutro", categorias fora da legenda, texto que diverge do rótulo, rótulo sem certeza.

Policy brief (`policy_brief.qmd`), até ~8 páginas: título como pergunta ou mensagem; 3 a 5 mensagens-chave, cada uma com certeza e a frase padronizada; problema e contexto brasileiro (começa pela política); o que foi feito (bases, data, n e desenho dos estudos, países); figura-resumo com a mesma métrica; achados por dimensão com estudos de suporte; implicações proporcionais à certeza e às condições de transferibilidade; limitações; "saber mais" com links da revisão e do pacote. Mesmos números e palavras do relatório.

## 7. Checklists

- PRISMA 2020 e PRISMA-ScR: `$RS prisma` já escreve `07-relatorio/checklist_prisma.csv` (`item,secao,topico,descricao,local_no_relato,status,evidencia_no_projeto`; `status` = `material_disponivel` ou `a_preencher`) a partir de `assets/checklists/prisma2020.csv` ou `prisma_scr.csv`. Preencha `local_no_relato` (seção e página) e troque `status` por `cumprido`, `nao_se_aplica` ou `ausente_justificado`.
- Extensões (`swim.csv`, `prisma_s.csv`, `prisma_traice.csv`, `press.csv`): primeira linha é atribuição comentada (convenções e fontes em `assets/checklists/README.md`, o único README da pasta). Gere a cópia de trabalho:
  ```bash
  python3 - "<pasta da skill>/assets/checklists/swim.csv" 07-relatorio/checklist_swim.csv <<'EOF'
  import csv, sys
  linhas = [l for l in open(sys.argv[1], encoding="utf-8") if not l.startswith("#")]
  with open(sys.argv[2], "w", newline="", encoding="utf-8") as f:
      w = csv.DictWriter(f, fieldnames=["item", "secao", "topico", "descricao", "local_no_relato", "status"])
      w.writeheader()
      for l in csv.DictReader(linhas):
          w.writerow({**l, "local_no_relato": "", "status": "a_preencher"})
  EOF
  ```
- ENTREQ, eMERGe, RAMESES e PRIOR não têm CSV na skill: preencher a partir do documento oficial e declarar no apêndice.
- Nenhum checklist substitui a auditoria: ele prova que o leitor pode julgar, não que a revisão é boa.

## 8. Passe de estilo (opcional, fora da skill)

A skill não faz revisão de linguagem. Se o usuário quiser um passe de estilo, feito por ele ou por uma ferramenta que ele escolher, proteja o relatório assim:

1. Salve a versão pré-estilo: `cp 07-relatorio/relatorio.qmd 07-relatorio/relatorio_pre_estilo.qmd`.
2. O passe não pode alterar números, ICs, rótulos (Positivo, Inconclusivo...), frases padronizadas de certeza, citações `@chave`, YAML, shortcodes `{{< include >}}`, tabelas geradas, blocos de código nem a marca de rascunho; métodos ficam no passado, sem tutorial de método dentro da Metodologia, e adjetivo nunca entra no lugar de número.
3. Confira que nenhum número mudou: `diff <(grep -oE '[0-9]+([.,][0-9]+)?' 07-relatorio/relatorio_pre_estilo.qmd) <(grep -oE '[0-9]+([.,][0-9]+)?' 07-relatorio/relatorio.qmd)` deve voltar vazio; se não, restaure os trechos.
4. Renderize de novo e apague `relatorio_pre_estilo.qmd` só depois do G9.

## 9. Marca de rascunho

Fontes da marca: `$RS status` (`rascunho` com pendências abertas, com a última caixa com células pendentes ou com busca ativa truncada; motivos em `motivos_rascunho`), `$RS prisma` (`rascunho` no JSON, no SVG e no PNG, também com busca truncada), `$RS caixa` (`rascunho`, também com célula pendente ou sem `validado_humano`), `$RS declaracao-ia` (`rascunho` também quando a validação que decide, a última com `finalidade` `validacao` da rodada ativa, ficou abaixo do limiar, ou quando houve IA na triagem sem essa validação; calibração e desenvolvimento reprovados não marcam). Os arquivos gerados carregam a própria marca; o `.qmd` tem `rascunho: true` no YAML, que exibe o aviso "RASCUNHO NÃO VALIDADO" no topo.

Troque para `rascunho: false` só quando, na mesma sessão e nesta ordem, `$RS pendencia listar` devolver `abertas: 0`, `$RS prisma`, `$RS caixa` e `$RS declaracao-ia` devolverem `rascunho: false`, e `caixa` tiver `n_pendentes: 0`. Autopiloto: nunca troque sozinho.

## 10. Pacote aberto (PRISMA 2020 item 27)

| Material | Arquivo do projeto |
|---|---|
| Protocolo e emendas | `00-protocolo/`, `00-protocolo/emendas.md`, eventos `emenda_protocolo` |
| Strings e log de buscas | `01-busca/strings/`, log de buscas; brutos só se a licença da base permitir |
| Registros e decisões | `dados/registros_unicos.csv` (sem resumos se a licença proibir), `dados/decisoes.jsonl`, `02-triagem/triagem_ta_final.csv`, `03-textos/elegibilidade_tc_final.csv` |
| Contagens do fluxo | `07-relatorio/prisma_contagens.json` |
| Codebooks e fichas | codebooks do projeto, `fichamentos_master.csv` |
| Efeitos e conversões | `05-decomposicao/efeitos_extraidos.csv`, `05-decomposicao/verificacao_efeitos.csv`, `06-analise/efeitos.csv` |
| Análises | `06-analise/*.json`, `tabelas/`, `figuras/`, versão do `metafor` |
| Certeza e caixa | `06-analise/certeza.csv`, `06-analise/caixa_ferramentas.csv` (com `regra_versao`) |
| IA | prompts em `02-triagem/prompts/` (hash no log), `02-triagem/validacao/`, `declaracao_uso_ia.md` |
| Estado auditável | `rs_log.jsonl` (sem nomes: só papéis) |

Nunca incluir `.env`, chaves, nomes reais em papéis ou PDFs protegidos.

## 11. O que o G9 exige

`$RS portao G9` sai com código 2 (tipo artefato, barra também o autopiloto) se não houve `prisma` no projeto, se `prisma_contagens.json` foi editado depois dele, se os insumos do fluxo (registros, decisões, inventário, buscas inativas...) ou as pendências abertas mudaram depois do último `prisma`, ou se falta `07-relatorio/declaracao_uso_ia.md`; também com pendência aberta da etapa 11 ou do G9. Os `avisos` (não barram) repetem os alertas de buscas sem data ou com mais de 12 meses, apontam a falta de `07-relatorio/references.bib` e avisam quando a declaração cobre o log só até um `seq` anterior ao último evento relevante. O `seq` coberto vem de `dados.ultimo_seq` do evento `relatorio_gerado` cuja cópia do arquivo (sha256) é a atual; declaração antiga, sem o campo, usa a frase "até o evento seq N" do texto; sem evento que corresponda ao arquivo atual, o aviso diz que a declaração foi escrita à mão ou editada (gere de novo). Não contam os eventos da própria declaração nem reexecuções sem mudança (`dados.reexecucao = true`; o `dedup` repetido sem mudança nem grava evento). `declaracao-ia` só reescreve o arquivo quando o texto muda. Por isso a ordem é `$RS prisma`, `$RS bib` e `$RS declaracao-ia` por último; aviso de declaração atrasada = rode `declaracao-ia` de novo antes de pedir aprovação. Antes de pedir aprovação, confira:

| Checagem | Critério |
|---|---|
| Fluxograma | `$RS prisma` saiu 0 depois da última mudança no ledger (o G9 confere); ramo de outras fontes quando houve; aguardando classificação relatados |
| Consistência numérica | mesmos números em resumo, texto, tabelas, figuras, caixa, painel e brief; placeholders reconferidos (seção 4) |
| Certeza | em todo enunciado de efeito e toda linha da caixa |
| Rótulos | reproduzíveis por `$RS caixa` a partir de `certeza.csv` e dos JSON |
| Heterogeneidade e testes combinados | τ², I² e PI no texto; ressalva junto de qualquer teste combinado |
| Limitações | evidência e processo em subseções separadas |
| Informações adicionais | registro, emendas, financiamento, conflitos, dados e código, IA; links abrem o material |
| Checklists | `checklist_prisma.csv` e extensões com `local_no_relato` preenchido |
| Referências | `$RS bib` sem aviso de chaves divergentes; toda citação resolve |
| Estilo | seção 8 feita, diff de números vazio |
| Placeholders | `grep` da etapa 9 vazio; render sem erro |
| Rascunho | seção 9 |

Checkpoints: mostre o relatório renderizado e a tabela acima; aguarde. `$RS portao G9 --aprovar --por revisor_humano_1 --criterios '{"prisma_ok": true, "placeholders": 0, "checklists": ["prisma2020", "swim"], "rascunho": false}'`. Autopiloto: `$RS portao G9 --aprovar --por autopiloto` abre pendência e o relatório continua com `rascunho: true`.

## 12. Armadilhas

| Armadilha | Prevenção |
|---|---|
| Contagem digitada ou copiada de memória | `{{N_*}}` só de `prisma_contagens.json`; auditoria |
| Filtros automáticos misturados com triagem humana no texto | usar `automacao_por_filtro` e `outros_motivos` do JSON |
| Revisões contadas como estudos incluídos | `N_ESTUDOS_INCLUIDOS` = `incluidos.estudos` (por `id_estudo`) |
| Heterogeneidade só no rodapé do forest plot | τ², I², PI no texto e no resumo |
| Rótulo do painel diferente do texto | painel e brief gerados de `caixa_ferramentas.csv` |
| "Recomendações" mais fortes que a certeza | seção "Da evidência à prática: implicações" |
| Declaração de IA escrita à mão | `$RS declaracao-ia` depois de todos os eventos |
| Estilo que muda número ou rótulo | diff da seção 8 |
| Placeholder `<...>` apagado pelo Pandoc | só `{{PREFIXO_NOME}}` |
| Marca de rascunho removida com pendência aberta | seção 9 |
