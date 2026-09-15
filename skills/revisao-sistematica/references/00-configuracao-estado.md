# Configuração, estado, modos, portões e retomada

Prefixo dos comandos: `$RS` abrevia `python3 "<pasta da skill>/scripts/rs.py"` (SKILL.md, "Como chamar os comandos"): em cada chamada de Bash, use a função `rs` definida na mesma chamada ou o caminho completo, nunca uma variável `RS`. `--dir <pasta>` é opção do comando raiz e vem ANTES do subcomando (`$RS --dir revisao init ...`); sem ela, os comandos procuram `rs_estado.json` subindo a partir da pasta atual.

## Sumário

1. Regras do estado
2. Criar ou adotar um projeto
3. Modos de autonomia
4. Portões G1-G9: checagens, critérios automáticos e pendências
5. Pendências e marca de rascunho
6. Status e retomada
7. Projetos parciais
8. Ambiente e degradação
9. Emendas e artefatos congelados
10. Armadilhas e o que registrar

## 1. Regras do estado

| Regra | Operação |
|---|---|
| Fonte de verdade | `rs_log.jsonl` (append-only) e as tabelas em disco. `rs_estado.json` é cache: `status` recalcula as etapas a partir do log de portões e dos artefatos |
| Quem escreve | Só `rs.py` escreve `rs_estado.json`, `rs_log.jsonl`, `dados/decisoes.jsonl`, `dados/registros*.csv`. Ler esses arquivos é permitido; editar, nunca |
| Concorrência | Todo escritor de estado e log roda sob a trava `<raiz>/.rs.lock` (flock; no Windows, msvcrt): o `seq` é recalculado do log e o estado é relido dentro da trava, com mescla das mudanças de processos concorrentes. Dois `rs.py` do mesmo projeto em chamadas de Bash paralelas (ex.: `triagem mesclar` de A e de B) são seguros. `status` acusa `seq_repetido_no_log` se um log antigo (de antes da trava) tiver `seq` duplicado |
| Estado corrompido | `rs_estado.json` ilegível (JSON quebrado, codificação errada) sai com código 1 e resumo JSON, sem traceback: não edite à mão; restaure a última versão boa do controle de versão (git) ou de uma cópia. `rs_log.jsonl` continua a fonte de verdade do histórico |
| Permissões | Arquivos gravados de forma atômica pelo estado, pelo `prisma`, pela declaração de IA, por `importar` (`registros.csv`, `registros_flags.csv`), `dedup`, `filtrar`, `triagem` e `validar` saem com a permissão padrão (0666 menos a umask, em geral 0644), legíveis por coautores numa pasta compartilhada. |
| Toda sessão | Começa com `$RS status`; repita depois de cada onda de subagentes ou comando longo |
| Saída dos comandos | Última linha do stdout = JSON. Códigos: 0 ok; 1 uso/dados; 2 checagem metodológica falhou; 3 dependência ausente |
| Papéis, não nomes | `--por revisor_humano_1`, `revisor_humano_2`, `autopiloto`. Nunca nome real, e-mail ou chave |

## 2. Criar ou adotar um projeto

**O que perguntar ao usuário antes do `init`** (uma mensagem, com o padrão sugerido):

| Decisão | Opções | Padrão | Flag |
|---|---|---|---|
| Pasta do projeto | caminho novo ou pasta atual; nunca dentro de outro projeto | pasta nova com nome curto | `$RS --dir <pasta> init` |
| Título provisório | frase X → Y | — | `--titulo` (obrigatório só para criar; num projeto existente pode ser omitido) |
| Tipo de revisão | ver references/tipos-de-revisao.md | `indefinido` até o G1 | `--tipo` |
| Revisão rápida | variante do tipo de origem (references/tipos-de-revisao.md, seção 6) | sem variante | `--variante rapida` (grava `projeto.variante`) |
| Idioma dos produtos | pt-BR, en, es... | pt-BR | `--idioma` |
| Autonomia | `checkpoints` ou `autopiloto` (seção 3) | `checkpoints` | `--autonomia` |
| Triagem | `subagentes` ou `api` (acima de ~1.500 registros, ou ~800 com dupla triagem; envia títulos e resumos a provedores externos: exige consentimento) | `subagentes` | `--triagem` |
| Escopo | completo ou parcial (seção 7) | completo | `--parcial` (`triagem`, `meta` ou `prisma`) |

**Passos**

1. `$RS status`. Sem projeto na pasta, o `status` procura `rs_estado.json` em subpastas (até 2 níveis): com `projetos_em_subpastas` não vazio, a `proxima_acao` é `$RS --dir "<subpasta>" status` (outras em `alternativas`); retome esse projeto e não crie outro. Com vários projetos, `projetos` lista cada um com `dir`, `titulo`, `tipo_revisao`, `etapa_atual`, `ultimo_evento_em` e `n_pendencias_abertas`, do mais recente ao mais antigo; a `proxima_acao` sugere o mais recente, repete a lista na `descricao` e vem com `exige_humano: true`: pergunte ao usuário qual retomar. Sem projeto e sem artefatos: siga para o passo 2. Sem projeto mas com `artefatos_encontrados`: passo 3.
2. `$RS --dir <pasta> init --titulo "<título>" --tipo <tipo|indefinido> [--variante rapida] --idioma pt-BR --autonomia checkpoints --triagem subagentes` (acrescente `--sem-r` se o usuário não usará R). Sem `--titulo` a criação sai com código 1. O `init` cria as pastas, o estado, o evento `projeto_criado` e roda `ambiente`. É idempotente: repetido, só cria pastas que faltam.
3. Adotar artefatos existentes: `$RS --dir <pasta> init --titulo "<título>" --adotar`. Só os artefatos canônicos (`dados/registros.csv`, `02-triagem/triagem_ta_final.csv`, `03-textos/relatorio_pdfs.csv` etc.) entram no estado com sha256; nada é movido. Execute uma a uma as `sugestoes` do resumo (em geral `$RS importar --arquivo "<exportação>" --busca-id B01`, cópias de `relatorio_pdfs.csv`/`verificacao_conteudo.csv` para `03-textos/`), perguntando antes ao usuário o que cada exportação é. Exportações são reconhecidas pelo cabeçalho (ex.: CSV do OpenAlex com `authorships.*` ou `display_name` + `publication_year`; JSON/JSONL com `"id": "https://openalex.org/W..."`); arquivos que a própria skill escreve (`registros*.csv`, `log_buscas.csv`, `exploracao_*.csv`, `fila_humana_*`, `rob_*`...), codebooks (cabeçalho `dimensao,variavel,descricao,prompt`) e arquivos de dentro de outro projeto nunca são sugeridos como exportação.
4. `$RS status` e siga `proxima_acao` (com `--dir`, a `proxima_acao` de `init` e de `portao` e todo comando `$RS ...` que o `status` sugere, em `proxima_acao`, `inconsistencias` e `alertas`, já trazem o `--dir`).

`init` recusa: pasta com artefatos da skill sem `--adotar`; pasta dentro de outro projeto (use `--dir` para outra pasta); pasta que contém projeto em subpasta, com ou sem `--adotar` (o resumo aponta `$RS --dir "<subpasta>" status`).

**Layout e nomes que o `status` reconhece**

| Caminho | Uso | Detectado por `status` como |
|---|---|---|
| `00-protocolo/pergunta.md` | ficha da pergunta, RS existentes, busca exploratória | evidência de 01_pergunta |
| `00-protocolo/teoria_programa.md`, `dag_v1.mmd` (nome com teoria, dag, framework, picoc, cmmo, pcc, spider ou mudanca) | teoria do programa e framework | 02_teoria_framework em andamento |
| `00-protocolo/protocolo.md` (nome começando por `protocolo`) | protocolo | 03_protocolo; libera sugestão do G2 |
| `00-protocolo/emendas.md` | log de emendas (nunca congelado) | — |
| `01-busca/strings/`, `01-busca/brutos/` | strings versionadas; exportações sem edição | 04_busca |
| `02-triagem/prompts/ta_vN.md` | critérios de triagem versionados | 06_triagem_ta (maior N) |

## 3. Modos de autonomia

| | `checkpoints` (padrão) | `autopiloto` |
|---|---|---|
| G1 e G2 | param; humano aprova | param; humano aprova (o script recusa `--por autopiloto` com código 2) |
| G3-G9 | param; mostre ao usuário números, arquivos, riscos e pendências; só humano aprova (não humano → código 2) | aplique os critérios automáticos da seção 4; se atendidos, `--por autopiloto` (ator `ia_coordenador`); o script abre a pendência `revisao_humana_portao` |
| Validações humanas (amostras, conferências, verificação de efeitos, juízos de certeza) | aparecem no resumo do comando; o coordenador para e pede ao usuário | viram pendências (abertas pelos próprios comandos ou por `pendencia abrir`); o fluxo segue |
| Produtos | finais quando os portões estão aprovados | relatório, PRISMA, caixa e declaração de IA saem com `RASCUNHO NÃO VALIDADO` enquanto houver pendência aberta |
| Pendência aberta da etapa atual | bloqueia `proxima_acao` e a aprovação humana do portão | não bloqueia o fluxo: a tarefa humana da etapa vem com `exige_humano: true`, `pendencia`, e `alternativa`/`acao_seguinte` com o próximo passo que não depende dela (ex.: `filtrar` ou a triagem enquanto os pares do dedup aguardam revisão); sem `alternativa` quando o portão da etapa tem bloqueio `artefato` ou `limiar` (ex.: G4 abaixo do limiar), porque o autopiloto não passaria dele |

Mudar de modo num projeto existente (registra `modo_definido`): `$RS init --autonomia autopiloto` (ou `--triagem api`; `--tipo` e `--variante` também, só antes do G1). `--titulo` pode ser omitido; um título diferente do registrado é ignorado com aviso.

## 4. Portões G1-G9

Comando: `$RS portao G# --aprovar --por <papel> --criterios '<json>'` ou `--criterios arquivo.json`. Reprovar: `$RS portao G# --reprovar --por <papel> --motivo "..."` (desfaz o congelamento feito por aquele portão). Dispensar uma etapa que o tipo de revisão não tem: `$RS portao G# --nao-se-aplica --por <papel> --motivo "..."` (abaixo).

**Bloqueios e avisos.** Checagens falham com código 2 e lista `bloqueios`, cada um com `tipo`, `detalhe` e, às vezes, `n` e `acao` (`verificar`). Tipos `artefato` e `limiar` são duros: barram também a aprovação `--por autopiloto`. Tipos `validacao`, `verificacao`, `certeza` e `pendencia` dependem de humano: barram a aprovação humana; no autopiloto viram a pendência `revisao_humana_portao`, com os bloqueios na descrição. Só humano segue com `--forcar --motivo "..."` (fica no log). O resumo traz também `avisos` (não barram; vão para `criterios.checagens_script.avisos` no log): mostre-os ao usuário.

**Critérios sugeridos pelo `status`.** A `proxima_acao` do portão nunca inventa valores: onde o número depende de conferência, o comando traz um placeholder fora de aspas, como `<valor de 01-busca/recall_ancoras.json>`, `<press: true só com revisão humana registrada>` ou `<sensibilidade da validação seq N>`, e a `descricao` traz o valor lido do arquivo quando existe. Troque cada `<...>` pelo valor conferido; colado sem trocar, o JSON é inválido e o `portao` sai com código 1. G1 e G2 usam `<pergunta aprovada pelo usuário, entre aspas>`, os caminhos reais do protocolo e do codebook e `<parecer do revisor metodológico, entre aspas>`; os demais portões seguem a coluna "`--criterios` recomendado" abaixo.

| Portão | Checagem do script (`bloqueio`, tipo) | Autopiloto aprova quando (conferido pelo coordenador) | Vira pendência (depende de humano) | `--criterios` recomendado |
|---|---|---|---|---|
| G1 pergunta e tipo | `pergunta` e `tipo_revisao` diferente de `indefinido`, nos critérios ou no estado (artefato); `tipo_revisao` e `variante` inválidos saem com código 1 | nunca (sempre humano) | — | `{"pergunta": "...", "tipo_revisao": "...", "variante": "rapida" (só se for), "atalho_rapida": true (só se o protocolo da variante rápida usar a triagem com dupla parcial), "escala": 2, "rs_existentes": "decisão", "comparabilidade": "incerta", "equipe": 2}`; grava pergunta, tipo e variante no estado |
| G2 protocolo | `00-protocolo/protocolo*` existe; `00-protocolo/codebook_v0*.csv` existe; codebook de elegibilidade existe (`00-protocolo/codebook_elegibilidade*.csv` ou, em projeto antigo, `03-textos/codebook_elegibilidade*.csv`); nenhum placeholder `<...>` ou `{...}` no protocolo nem `{...}` nos codebooks (todos artefato). Não contam como placeholder: comentários HTML, blocos e trechos de código, matemática, autolinks (`<https://...>`), tags HTML comuns, atributos do Quarto (`{#sec-x}`, `{.classe}`), JSON e LaTeX. Aviso sem `00-protocolo/revisao_metodologica*` | nunca (sempre humano) | — | `{"protocolo": "00-protocolo/protocolo.md", "codebook_v0": "00-protocolo/codebook_v0_<familia>.csv", "revisor_metodologico": "sem CRÍTICO", "registro": "<DOI OSF ou pendente>"}`; congela `00-protocolo/*` exceto `emenda*` |
| G3 busca | alguma busca ativa, exportação em `01-busca/brutos` ou `registros.csv` (artefato); nenhuma busca ativa com `truncada = true` (limiar: o autopiloto é barrado; humano só segue com `--forcar --motivo`); PRESS registrado em `01-busca/press_*.md` ou pendência `revisao_press` aberta (artefato); avisos (não barram) sem `01-busca/recall_ancoras.json`, com recall combinado < 1 (lista as âncoras de `combinado.perdidas`) ou com recall calculado sobre outro `registros_unicos.csv`; aviso de busca sem data ou com mais de 12 meses aparece no `status` | toda fonte do protocolo tem linha em `01-busca/log_buscas.csv` e foi importada com metadados PRISMA-S; `n_importado` coerente com `n_base`; `01-busca/recall_ancoras.json` com todas as âncoras de validação indexadas recuperadas (`combinado.perdidas` vazio) | PRESS por humano: no autopiloto, a pendência `revisao_press` (a `proxima_acao` a pede antes do G3); `revisao_humana_portao` | `{"recall_ancoras": 1.0, "ancoras_indexadas": 12, "press": true, "log_prisma_s": "01-busca/log_buscas.csv", "fontes": 6}`; congela `01-busca/strings/**` e `01-busca/filtros_*.json` |
| G4 triagem T/A | `triagem_ta_final.csv` existe (artefato); validação com `finalidade` `validacao` da rodada ativa (`versoes_ativas.rodada_ta`) calculada (validacao) e dentro dos limiares, recall ≥ 0,95 com LI ≥ 0,90 (limiar); contagens de dedup, filtro e triagem fecham (artefato). Calibração, desenvolvimento, elusão e estabilidade nunca decidem. Variante rápida (`projeto.variante = rapida` e `atalho_rapida` verdadeiro nos critérios do G1): também vale a validação com `dados.atalho_rapida = true`, que dispensa recall ≥ 0,95 e exige dupla humana em ≥ 20% (`fracao_dupla_humana`, ou `n_dupla_humana`/`n_populacao`; abaixo disso, limiar), κ calculado (`kappa_humanos`) e segunda leitura humana de todos os excluídos pela IA (`segunda_leitura_excluidos = true`, ou `n_excluidos_relidos >= n_excluidos_ia`), com aviso para declarar o atalho como limitação. Sem o critério no G1, vale a regra geral, com aviso | consolidação feita; amostra de validação preparada e, se já calculada, `atende_limiares` true; amostra de elusão preparada; estabilidade 5-10% rodada | `dedup_candidatos`, `fila_humana_triagem` (inclui divergências arbitradas), `validacao_humana`, `calibracao_reprovada`, `validacao_triagem_reprovada` | o JSON de métricas de `validar calcular`; atalho: `{"atalho_rapida": true, "fracao_dupla_humana": <fração>, "kappa_humanos": <κ>, "segunda_leitura_excluidos": <true só se todos foram relidos>}`; congela `02-triagem/prompts/*.md` |
| G5 texto completo | `elegibilidade_tc_final.csv` existe; todas as invariantes do PRISMA fecham, inclusive `avaliado_nao_recuperado` e `decisoes_de_busca_substituida` (artefato); `incerto` sem decisão humana quebra a invariante; aviso com relatórios `aguardando` | inventário rodado; relatos ligados; `textos retratacoes` rodado; bola de neve rodada e re-triada até uma rodada sem novas inclusões; fração de "outros métodos" ≤ 30% ou diagnosticada | `conferencia_elegibilidade_tc` (fecha sozinha quando todos os textos têm decisão humana); `retratacao_texto` (qualquer modo); PDFs `suspeito`/`conferir_a_mao`/`sem_camada_de_texto` (manual `conferencia_pdfs`) | `07-relatorio/prisma_contagens.json` ou `{"incluidos": 21, "estudos": 19, "aguardando": 1, "rodadas_bola_de_neve": 2, "fracao_outros_metodos": 0.18}` |
| G6 piloto de extração | evento `extracao_consolidada` (de `analise preparar-efeitos`) ou `05-decomposicao/**/*fichamentos_master*.csv` (artefato) | 2-3 estudos por bloco fichados; gate de citações do fichamento aprovado; mudança no codebook v0 registrada como emenda | revisão humana do piloto (manual `revisao_piloto`) | `{"estudos_piloto": 8, "codebook": "00-protocolo/codebook_v0_oqf.csv", "emenda": "E00N"}` |
| G7 extração e RoB | com `05-decomposicao/efeitos_extraidos.csv`: `verificar-efeitos` rodado depois da última mudança do arquivo (artefato, `acao: verificar`); nenhum trecho fora da página nem erro de plausibilidade (artefato); todas as linhas com `apto_g7 = 1` (verificacao). Fora de `escopo` e `mapa_evidencias` (`esquema.TIPOS_SEM_ROB`), por ferramenta: último `rob_consolidado` de `qualidade consolidar --consenso` (artefato; também quando a fase 1 da ferramenta rodou sem a fase 2 ou ela aparece em `04-qualidade/resultados_avaliados.csv` sem consolidação); nenhum arquivo citado nele alterado ou ausente (artefato: consolide de novo; `04-qualidade/rob_geral.csv` pela última consolidação e, para as outras ferramentas, pelas linhas delas); `todos_validados_humano = true` (validacao); todo resultado avaliado (`resultados_avaliados.csv` ou, sem ele, `chave` × `construto_outcome` de `efeitos_extraidos.csv`) com `rob_geral` (artefato). Avisos (não barram): nenhum `05-decomposicao/**/concordancia.csv` fora do piloto, ou variáveis sinalizadas nele sem pendência `concordancia_extracao` fechada para o arquivo | `verificar-efeitos` com código 0; concordância das categóricas calculada; `qualidade consolidar` fase 1 rodada (fila de desacordos) | `verificacao_humana_efeitos` (100% dos números; fecha sozinha quando todas as linhas ficam aptas, ver seção 5); `consenso_rob` (aberta pela fase 1 no autopiloto; fecha com a fase 2); manual `concordancia_extracao` (segundo codificador cego em ≥ 20%, mín. 10; κ ou PABAK ≥ 0,7 e ≥ 80%; fechá-la registra a arbitragem) | `{"efeitos": 42, "verificados_humano": 42, "kappa_min": 0.74, "rob_geral": "04-qualidade/rob_geral.csv", "rob_todos_validados_humano": true}` |
| G8 síntese e certeza | nenhuma linha de `06-analise/caixa_ferramentas.csv` com `status_rotulo` diferente de `definido` (certeza); em `oqf_mista_sequencial`, a caixa existe (artefato); `06-analise/certeza.csv` existe (artefato), salvo em `escopo`, `mapa_evidencias` e `realista` sem caixa; toda célula de efeito da caixa tem linha de certeza na mesma família, construto e classe de desenho (certeza); aviso para grupo de `meta_resumo.json` com `status` `dependencia_nao_resolvida` ou `erro_ajuste`; com a etapa 09 ignorada (projeto parcial `meta`), aviso quando o último `analise efeitos` conta `n_nao_verificados_humano > 0` (sem esse evento, as linhas calculadas de `06-analise/efeitos.csv` sem `verificado_humano`) | `analise meta`/`swim` com código 0 (código 2 só com o bloqueio explicado e resolvido); `caixa` gerada; revisor metodológico do G8 sem CRÍTICO | `certeza_caixa` (fecha sozinha quando todas as células ficam definidas) e juízos GRADE/CERQual (manual `certeza_humana`) | `{"grupos_meta": 3, "celulas": 6, "pendentes": 0, "regra_versao": "caixa-3"}` |
| G9 relato | `prisma_gerado` existe, `prisma_contagens.json` não foi editado, insumos (inclusive buscas truncadas) e pendências abertas iguais aos atuais (artefato); `07-relatorio/declaracao_uso_ia.md` existe (artefato); avisos (não barram) de buscas sem data ou com mais de 12 meses, sem `07-relatorio/references.bib` e com declaração que cobre o log só até um `seq` anterior ao último evento relevante. O `seq` coberto vem de `dados.ultimo_seq` do evento `relatorio_gerado` cujo sha256 do arquivo é o atual (declaração antiga, sem o campo: a frase "até o evento seq N" do texto); sem evento correspondente, o aviso é de declaração "escrita à mão ou editada". Não contam os eventos da própria declaração nem reexecuções com `dados.reexecucao = true` | `prisma` com código 0; `declaracao-ia` gerada depois do último evento; checklists preenchidos; `bib` sem chaves divergentes | as que restarem (produtos seguem como rascunho) | `{"prisma": "07-relatorio/prisma_contagens.json", "declaracao_ia": true, "checklists": ["prisma2020", "prisma_s"]}` |

Pendência aberta com a etapa ou o portão do G# sempre entra como bloqueio `pendencia`.

Notas sobre os portões:

- **G3 e busca truncada.** `buscar openalex --max-paginas` (ou importação com `truncada`) marca a busca: o `status` alerta `busca_truncada` e marca rascunho, o `prisma` sai como rascunho com "Buscas truncadas: B01" no SVG e no Mermaid, e o G3 bloqueia. Rode a busca inteira com um `busca_id` novo e `--substituir` a truncada (references/02-busca.md, seção 5): busca feita pela API do OpenAlex se refaz com `buscar openalex` (a `proxima_acao` e o alerta trazem o comando com a mesma `--query`, `--campo`, `--filtro` e `--string-id` do estado; troque `<novo busca_id>`); `importar --arquivo <exportação completa> --substituir` só para exportações manuais.
- **G4 pela variante rápida.** O caminho do atalho lê do evento `validacao_calculada` os campos `atalho_rapida`, `fracao_dupla_humana` (ou `n_dupla_humana`/`n_populacao`), `kappa_humanos` e `segunda_leitura_excluidos` (ou `n_excluidos_relidos`/`n_excluidos_ia`). `validar calcular` grava esses campos quando o projeto é variante rápida e a amostra foi sorteada com `validar amostrar --atalho-rapida` (ou calculada com `--atalho-rapida`); a segunda leitura humana dos excluídos pela IA é registrada com `validar segunda-leitura --rodada <r> --planilha <planilha codificada>` e entra no evento quando `validar calcular` roda de novo. O resumo do `calcular` sai com código 2 e diz o que falta (dupla abaixo de 20%, κ indefinido, excluídos sem releitura). Passo a passo em references/tipos-de-revisao.md, seção 6.
- **G4 em revisão pequena.** Validação reprovada só pela largura do IC (0 falsos negativos e menos incluídos humanos do que o limite inferior de 0,90 exige, 36) tem `motivo_reprovacao = largura_ic`: amplie a amostra enriquecida ou a elusão; se a rodada não tem incluídos pela IA suficientes, o limiar é inalcançável e o caminho é o remédio 5 com `--forcar --motivo` humano (references/ia-validacao.md, seção 4 D e E). A `proxima_acao` do `status` escolhe o remédio pelo `motivo_reprovacao` da validação: `largura_ic` → `validar amostrar ... --semente <outra semente> --enriquecer-incluidos N` (alternativa `validar elusao`), nunca revisar critérios, ou o remédio 5 com `--forcar` quando as métricas dizem que a rodada não tem incluídos pela IA suficientes; `humanos` → consenso e recalibração da dupla; `desempenho_ia` → falsos negativos e critérios vN+1. Validação antiga, sem o campo, com menos de 36 incluídos humanos e nenhum falso negativo → remédio 5.
- **G7 e RoB.** Uma consolidação por ferramenta (`qualidade consolidar --ferramenta rob2`, `robins_i`...), em qualquer ordem: o G7 lê o último `rob_consolidado` de cada ferramenta, exige `todos_validados_humano` em cada um e confere que todo resultado avaliado tem `rob_geral` (references/05-qualidade.md, seção 7).

No autopiloto: se falha um item da coluna "Autopiloto aprova quando", NÃO aprove; resolva e repita. Itens da coluna "Vira pendência" não impedem: confira em `$RS pendencia listar` que cada um está aberto (os comandos abrem os seus; os manuais, abra você) e aprove com `--por autopiloto`.

**Etapa que não se aplica ao tipo.** `$RS portao G7 --nao-se-aplica --por revisor_humano_1 --motivo "revisão de escopo: sem risco de viés"` só vale para os portões de `esquema.PORTOES_OPCIONAIS_POR_TIPO` (hoje: `escopo` G7 e G8; `mapa_evidencias` G6, G7 e G8; `realista` G4) e depois do G1 aprovado (senão código 2); sem `--motivo`, ou com o portão já aprovado, código 1 (reprove antes). Registra `etapa_nao_aplicavel`, põe a etapa em `projeto.etapas_ignoradas` e o `status` passa a mostrá-la `ignorada` com `fonte: nao_se_aplica`. Em checkpoints só humano dispensa; no autopiloto `--por autopiloto` abre `revisao_humana_portao`. Aprovar ou reprovar depois devolve a etapa ao fluxo (`reverte_nao_se_aplica` no log). Quando o tipo permite, a `proxima_acao` do `status` traz o comando em `alternativa`. Para outros tipos e portões não há dispensa: faça o que o tipo pede e aprove declarando nos critérios o que não se aplica (references/tipos-de-revisao.md, seção 5). Pendência manual: `$RS pendencia abrir --tipo revisao_press --etapa 04_busca --portao G3 --descricao "PRESS da estratégia Scopus por revisor humano" [--n 1] [--arquivo 01-busca/strings/S-scopus-v2.txt]`. Etapas válidas: `00_configuracao`, `01_pergunta`, `02_teoria_framework`, `03_protocolo`, `04_busca`, `05_organizacao`, `06_triagem_ta`, `07_textos_elegibilidade`, `08_piloto_extracao`, `09_extracao_rob`, `10_sintese`, `11_relato`.

**O que mostrar ao usuário num portão (checkpoints):** números do resumo JSON (sem digitar contagens), arquivos a conferir, riscos e desvios, pendências abertas, o comando exato de aprovação. Aguarde "aprovo" explícito antes de rodar `portao`.

## 5. Pendências e marca de rascunho

| Comando que abre | Modo | `tipo` | Como resolver |
|---|---|---|---|
| `dedup` | autopiloto | `dedup_candidatos` | humano marca `confirmado`, `rejeitado` ou (só em par de versão) `ligado` em `01-busca/dedup_pares.csv`, com `decidido_por`; `$RS dedup --revisar 01-busca/dedup_pares.csv --por revisor_humano_1` (sem `decidido_por` nem `--por`, código 1) fecha sozinho quando zera |
| `triagem consolidar` | autopiloto | `fila_humana_triagem` | humano preenche `decisao_humana` (e `criterio_humano` nas exclusões) na fila (divergências sem árbitro e também as arbitradas, `motivo_fila=arbitrada`); `$RS triagem override --fila 02-triagem/fila_humana_<rodada>.csv --por revisor_humano_1`; depois `$RS triagem consolidar --rodada <rodada>` fecha quando a fila zera. Fila com linhas preenchidas e ainda não aplicadas não é regravada (`fila_preservada: true`) |
| `validar amostrar` / `validar elusao` | autopiloto | `validacao_humana` | dupla humana codifica a planilha cega; `$RS validar calcular --planilha <xlsx ou csv>` fecha |
| `validar calcular` (validação abaixo do limiar) | autopiloto | `validacao_triagem_reprovada` | depende de `motivo_reprovacao`: `desempenho_ia` → análise de falsos negativos e critérios vN+1 em amostra nova; `humanos` → consenso e recalibração da dupla; `largura_ic` → amostra enriquecida maior ou elusão, ou remédio 5 se o limiar for inalcançável (a descrição da pendência diz qual). A pendência é do arquivo de métricas reprovado e não fecha com a validação nova: humano fecha com `pendencia fechar` citando a validação que atendeu |
| `validar calcular` (calibração abaixo do limiar) | autopiloto | `calibracao_reprovada` | critérios vN+1 e nova calibração em registros novos; fecha com `pendencia fechar` |
| `textos elegibilidade consolidar` | autopiloto | `conferencia_elegibilidade_tc` | humanos decidem com `triagem override --etapa tc`; reexecutar `consolidar` fecha sozinho quando todos os textos têm decisão humana |
| `textos retratacoes` | qualquer | `retratacao_texto` | excluir o retratado com `triagem override --etapa tc`; reexecutar `retratacoes` fecha quando nenhum texto verificado segue retratado. Fechada por humano, não reabre enquanto o conjunto de retratados e o que as fontes dizem deles não mudarem (`retratados_sha`, sem a data da verificação); conjunto diferente, mesmo com o mesmo `n`, reabre |
| `analise verificar-efeitos` | autopiloto | `verificacao_humana_efeitos` | humano marca `verificado_humano`; reexecute `verificar-efeitos`: o `n` acompanha as linhas não aptas (a pendência é substituída, sem duplicar) e ela fecha sozinha quando `pode_seguir_g7` fica true |
| `qualidade consolidar --a --b` (fase 1) | autopiloto | `consenso_rob` | humanos resolvem os desacordos em `04-qualidade/rob_<ferramenta>_consenso.csv` (`julgamento_consenso`, `justificativa`, `resolvido_por` humano); `$RS qualidade consolidar --ferramenta <f> --consenso 04-qualidade/rob_<f>_consenso.csv [--por revisor_humano_1]` fecha (references/05-qualidade.md, seção 5) |
| manual (`pendencia abrir`) | autopiloto | `revisao_press` | revisor humano faz o PRESS e registra `01-busca/press_<string_id>.md`; `pendencia fechar`. Aberta, ela satisfaz a checagem de PRESS do G3 no autopiloto |
| manual (`pendencia abrir`) | qualquer | `concordancia_extracao` | humano arbitra as variáveis sinalizadas em `05-decomposicao/concordancia/concordancia.csv` (ou redefine e recodifica); fechada com `--arquivo` desse CSV, silencia o aviso do G7 |
| `caixa` | autopiloto | `certeza_caixa` | humano completa `06-analise/certeza.csv` (com `validado_humano`); reexecute `caixa`: o `n` acompanha as células não definidas e a pendência fecha sozinha com `n_pendentes` = 0 (antes de decidir a marca de rascunho) |
| `portao G3..G9 --por autopiloto` ou `--nao-se-aplica --por autopiloto` | autopiloto | `revisao_humana_portao` | humano revisa o portão; `pendencia fechar` |

Regra comum (handoff.sincronizar_pendencia_unica): cada comando mantém no máximo uma pendência aberta por tipo e arquivo; se o número de casos muda, a antiga é fechada pelo script e outra é aberta com `[substitui Pxxx]`; com zero casos, o próprio comando fecha a pendência, em qualquer modo; um humano que fechou a pendência sobre o mesmo conteúdo não a vê reaberta. Criar pendência nova continua restrito à coluna "Modo".

Listar: `$RS pendencia listar [--todas] [--portao G4]`. Fechar: `$RS pendencia fechar P003 --motivo "..." --por revisor_humano_1`. Só humano fecha (`--ator-tipo` diferente de `humano` sai com código 2): rode `fechar` apenas depois de o usuário confirmar, na conversa, que a validação foi feita. Ao fechar a última, o resumo traz `regenerar` (ex.: `$RS prisma`, `$RS declaracao-ia`): rode todos. `status` mostra `"rascunho": true` e os `motivos_rascunho` enquanto houver pendência aberta, a última `caixa` tiver células pendentes ou houver busca ativa truncada.

## 6. Status e retomada

Campos do `$RS status`: `projeto` (inclui `tipo_revisao`, `variante`, `parcial`), `modo`, `etapa_atual`, `etapas` (status `pendente|em_andamento|concluida|ignorada`, portão, evidências, `fonte` = `artefatos|log_portao|projeto_parcial|nao_se_aplica|estado`, com `motivo` quando dispensada), `pendencias`, `inconsistencias`, `alertas` (por busca ativa: `busca_truncada`, `busca_desatualizada` com `dias` ou `busca_sem_data`; não bloqueiam o `status`), `contagens` (inclui `buscas_inativas`), `rascunho`, `motivos_rascunho`, `proxima_acao` (`tipo` = `comando|tarefa|portao|pendencia|skill|corrigir|fim`, `comando` com placeholders `<...>` onde há valor a conferir, `exige_humano`, `alternativa` com o `--nao-se-aplica` quando o tipo permite dispensar o portão, e, conforme o caso, `alternativas`, `pendencia`, `acao_seguinte`, `motivo_reprovacao`, `buscas_truncadas`, `rascunho`, `motivos_rascunho` e `portoes_forcados`). Chamado com `--dir`, todo comando `$RS ...` sugerido já traz o `--dir`. Sem projeto na pasta: `projeto: null`, `projetos_em_subpastas`, `projetos` (título, etapa atual e último evento de cada um), `artefatos_encontrados` e a `proxima_acao` com `--dir` (seção 2).

`tipo: fim` só quando todas as etapas estão concluídas ou ignoradas, não há pendência aberta nem motivo de rascunho e nenhum G8 aprovado com `--forcar` continua com bloqueio. Caso contrário (ex.: projeto parcial `meta` com o G8 forçado e a caixa com célula pendente), a ação é `tarefa` na etapa seguinte à última aprovada (`11_relato`), com `rascunho: true`, `motivos_rascunho`, `portoes_forcados`, `exige_humano: true` e o comando do que falta (ex.: `caixa --master <master>`), quando há um.

A `proxima_acao` segue a ordem do trabalho: na busca, sem PRESS registrado, pede o PRESS (checkpoints: tarefa humana; autopiloto: `pendencia abrir --tipo revisao_press`) e, com busca truncada, `buscar openalex ... --substituir <truncada>` (busca feita pela API, com a consulta do estado) ou `importar --arquivo <exportação completa> --substituir <truncada>` (exportação manual); na organização, com pares candidatos, `dedup --revisar 01-busca/dedup_pares.csv --por revisor_humano_1` (`exige_humano`); na triagem por subagentes, antes do `consolidar`, pede `triagem mesclar` dos lotes não mesclados e, com divergências de A e B sem árbitro, `triagem preparar --revisor arbitro --apenas-divergentes` (alternativa: `--regra liberal`, se o protocolo previu); dupla humana e modo API vão direto ao `consolidar`.

| Alerta | Causa | Ação |
|---|---|---|
| `busca_truncada` | busca ativa com `truncada = true` (ex.: `buscar openalex --max-paginas`) | rodar a busca inteira com um `busca_id` novo e `--substituir` a truncada, pelo `comando` do alerta (`buscar openalex` para busca da API, `importar` para exportação); o G3 bloqueia e o PRISMA sai como rascunho enquanto ela estiver ativa |
| `busca_sem_data` | exportação importada sem `--executada-em` (ou data ilegível); calado quando a etapa 04 está ignorada (projeto parcial) | `$RS importar --arquivo <mesmo arquivo> --busca-id <id> --executada-em AAAA-MM-DD` (completa a busca sem acrescentar linhas) |
| `busca_desatualizada` | busca ativa executada há mais de 12 meses | atualizar a busca antes de publicar (references/02-busca.md, seção 11) |

| Inconsistência | Causa provável | Ação |
|---|---|---|
| `artefato_congelado_alterado` / `_ausente` | arquivo congelado mudou ou sumiu | seção 9 (emenda) ou restaurar a versão |
| `contagens_nao_fecham` | tabelas desalinhadas (registro fora do dedup, triagem de ID desconhecido) | rodar o comando sugerido (`dedup`, `triagem consolidar`, `prisma`) e investigar antes do portão |
| `estado_atras_do_log` (aviso) | queda entre gravar log e estado | nada; o próximo comando atualiza |
| `seq_repetido_no_log` (aviso) | log gravado por versões sem trava, com comandos em paralelo | avisar o usuário; não reescrever o log (é append-only); os comandos novos seguem com `seq` único |
| `log_atras_do_estado` (erro) | log truncado | parar e avisar o usuário; não reconstruir à mão |
| `portao_sem_evento` | estado editado à mão | avisar; reaprovar o portão pelo comando |
| `portao_fora_de_ordem` | portão aprovado antes do anterior | aprovar ou reprovar os portões anteriores |

**Retomar depois de interrupção**

| Onde parou | O que fazer |
|---|---|
| Qualquer ponto | `$RS status`; nunca deduza da conversa anterior |
| Onda de subagentes de triagem | `$RS triagem mesclar --rodada <r> --revisor <revisor>` (A, B, arbitro) para cada revisor; lotes sem resposta válida seguem pendentes: despache subagente NOVO |
| `triagem api` | repita exatamente o mesmo comando (retoma por `(id_rs, rodada, papel)`); com `--batch`, repita até `em_andamento` e `pendentes` = 0 |
| `buscar openalex` com erro | repita com o mesmo `--busca-id` e a mesma consulta (nada foi gravado); consulta diferente exige id novo |
| `importar` | repita o mesmo comando; linhas já gravadas não duplicam e o estado é recomposto (`recuperado`); `--substituir` já aplicado volta com `ja_aplicada` |
| `dedup`, `filtrar`, `prisma`, `caixa` | idempotentes: repita |

## 7. Projetos parciais

| Pedido | `init` | Etapas mantidas (as demais ficam `ignorada`) | Caminho |
|---|---|---|---|
| "só a triagem" | `--parcial triagem` | 00, 05, 06 | `importar` → `dedup` (opcional) → critérios em `02-triagem/prompts/ta_v1.md` → `triagem ...` → `validar` → G4 |
| "só a meta-análise" | `--parcial meta` | 00, 10 | CSV do usuário no formato de `agentes/extrator-efeitos.md` em `05-decomposicao/efeitos/` (ou `--entrada <csv>`) → `analise preparar-efeitos` (sem `registros_unicos.csv` a `chave` não é conferida contra o projeto) → `analise efeitos` → `analise meta` ou `analise swim` → GRADE humano em `06-analise/certeza.csv` (o G8 exige o arquivo) → G8. Sem PDFs, veja o quadro abaixo |
| "só o PRISMA" com projeto | `--parcial prisma` | 00, 11 | `prisma` (etapas sem artefato saem NR; `--tipo` padrão `scr` para escopo e mapa, senão `2020`) |
| "só o PRISMA" sem projeto | nenhum | — | `$RS prisma --manual contagens.json --saida <pasta>` (mesma estrutura de `prisma_contagens.json`; o que faltar sai NR) |
| "só as strings de busca" | nenhum (se o usuário não quiser projeto) | — | seguir references/02-busca.md; `$RS buscar openalex --query "..." --contar` funciona sem projeto |
| "baixar PDFs", "fichar", "gerar .bib" | nenhum | — | skill irmã correspondente |

Diga ao usuário, no início, que num projeto parcial as etapas anteriores não foram auditadas pela skill e aparecem como NR.

**"Só a meta-análise" com a planilha do usuário, sem PDFs.** O contrato de efeitos pede trecho e página na fonte, mas aqui a fonte é o que o usuário entregou:

| Coluna ou passo | O que fazer |
|---|---|
| `evidencia` | aponte a fonte do usuário de onde o número veio, sem inventar trecho: "planilha efeitos_usuario.csv, linha 12" ou "Silva 2019, Tabela 3, col. 2 (informado pelo usuário)" |
| `pagina` | vazia, ou a página informada pelo usuário |
| `verificado_humano` | `sim` só se o usuário declarar, na conversa, que conferiu os números contra a fonte dele; senão vazio (o resumo de `analise efeitos` conta `n_nao_verificados_humano`) |
| `analise verificar-efeitos` | não rode: sem PDFs, todas as linhas saem `PDF_NAO_ENCONTRADO` (código 2). A etapa 09 está ignorada no projeto parcial e o G7 não é exigido. Com a etapa 09 ignorada e nenhum PDF em `03-textos/pdfs` nem em `relatorio_pdfs.csv`, `analise preparar-efeitos` devolve `proximo_passo: rs.py analise efeitos` (com `sem_pdfs: true` e `n_nao_verificados_humano`) e `analise efeitos` avisa que os números não foram verificados contra os PDFs e devem ser declarados no relato, em vez de mandar rodar `verificar-efeitos` |
| Certeza | o G8 exige `06-analise/certeza.csv` com o GRADE humano de cada célula |
| `caixa` | opcional em efetividade; só rode se o usuário pedir. Sem `fichamentos_master.csv` com as variáveis `impl_*`, a linha de implementação sai "Não avaliada" (`pendente`) mesmo com linha CERQual em `certeza.csv`, e o G8 bloqueia (tipo certeza): o custo se resolve com uma linha `custo` com enunciado (ex.: "Não reportado nos dados do usuário") em `certeza.csv`, mas a implementação não; a aprovação é humana, com `--forcar --motivo` declarando a lacuna, e o `status` segue com `rascunho` por causa da caixa (a `proxima_acao` depois do G8 forçado é `tarefa` com os motivos de rascunho, não `fim`; seção 6) |
| `verificado_humano` vazio no G8 | com a etapa 09 ignorada, o G8 avisa quantos efeitos calculados ninguém conferiu (`n_nao_verificados_humano` do último `analise efeitos`): confirme com o usuário e declare no relato |
| Relato | declare que os dados de efeito vieram do usuário, que a skill não os verificou contra os PDFs e quantas linhas o usuário declarou ter conferido; trate isso como limitação do processo (PRISMA 2020 item 23c) |

## 8. Ambiente e degradação

`$RS ambiente [--sem-r]` grava o diagnóstico no estado e sai com 3 se falta pacote Python obrigatório. O campo `instalar` traz os comandos; mostre-os e peça autorização antes de instalar. Dependências: `python3 -m pip install -r "<pasta da skill>/scripts/requirements.txt"` (opcionais em `requirements-opcional.txt`); R: `install.packages(c("meta","metafor","esc","irr","clubSandwich","robvis","jsonlite"))`. Rscript fora do PATH: variável `RS_RSCRIPT`.

| Ausente | Efeito | Como seguir |
|---|---|---|
| pandas, openpyxl, xlrd, requests, pymupdf | comandos falham (código 3) | instalar; sem alternativa |
| rapidfuzz | dedup fuzzy com difflib (mais lento; escores um pouco diferentes, backend no log) | seguir |
| pyalex, bibtexparser, rispy, jsonschema | parsers e validadores próprios | seguir |
| anthropic / openai ou chave | sem `triagem api` | triagem por subagentes |
| R (Rscript) | nenhum `analise efeitos/meta/swim/combinados` (código 3) | síntese qualitativa, `caixa` com `certeza.csv` e `prisma` seguem; avisar que não haverá síntese quantitativa |
| metafor | sem `analise meta` (código 3) | `analise efeitos`, `swim`, `combinados` e `caixa` seguem |
| clubSandwich | sem `--dependencia che` | um efeito por estudo |
| Quarto | sem render dos relatórios `.qmd` | entregar Markdown |
| Skill irmã | `baixar-pdfs-academicos`: checklist manual de PDFs; `fichamento-sistematico`: extração inline mínima; `gerar-bibtex`: `$RS bib --sem-irma`; `tirar-cara-de-ia`: revisão de estilo manual | usar o fallback e registrar |

Credenciais só por variável de ambiente, lidas como booleanos: `RS_EMAIL` (fila educada do OpenAlex), `OPENALEX_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`. Nunca leia `.env`, nunca escreva valores em arquivo ou log. Preferência pessoal de estilo do usuário é só preferência: registre-a em `00-protocolo/pergunta.md` (seção "Preferências"), nunca como regra da skill.

## 9. Emendas e artefatos congelados

| Congela | O quê | Mudança depois |
|---|---|---|
| Aprovação do G2 | todo arquivo presente em `00-protocolo/` naquele momento (só o nível da pasta), exceto nomes começando por `emenda` | emenda |
| Aprovação do G3 | `01-busca/strings/**` (strings, tabela de termos, histórico de desenvolvimento) e `01-busca/filtros_*.json` | emenda; string nova depois do G3 = busca nova com `importar --substituir` e emenda |
| Aprovação do G4 | `02-triagem/prompts/*.md` | emenda; critério novo de fato = nova rodada `ta_vN+1` |
| Reprovação de um portão | descongela o que ele congelou | não é emenda |

Arquivos criados depois do portão não ficam congelados; `emenda` recusa arquivo não congelado (código 1).

**Passos de uma emenda**

1. Pare e mostre ao usuário: o que muda, por quê, em que etapa a revisão está e o que já se sabe dos resultados. Mudança motivada pelo efeito sobre os resultados é proibida.
2. Com aprovação, escreva a entrada em `00-protocolo/emendas.md` (modelo `assets/templates/emendas.md`).
3. Altere o arquivo congelado.
4. `$RS emenda --arquivo 00-protocolo/protocolo.md --motivo "E002: <resumo>" --por revisor_humano_1` (evento `emenda_protocolo`, versão do artefato +1).
5. Refaça o que a emenda atinge (re-triagem com nova rodada, re-extração, reanálise) e apresente resultados com e sem a mudança quando possível.
6. Versão maior (critério, desfecho, análise): lembrar o usuário do *update* no registro OSF.

`status` com `artefato_congelado_alterado` põe a emenda como `proxima_acao`; não siga adiante antes de emendar ou restaurar.

## 10. Armadilhas e o que registrar

| Armadilha | Evite assim |
|---|---|
| Aprovar portão com `--por revisor_humano_1` sem aprovação real do usuário | Só rode `portao` depois do "aprovo" explícito; no autopiloto use `--por autopiloto` |
| Fechar pendência "porque o fluxo precisa" | Só com confirmação humana; senão o produto fica rascunho, e está certo |
| `--forcar` para passar de limiar | Só humano, com motivo escrito; informe que a declaração de IA e o log mostrarão o forçamento |
| Rodar `init` de novo para "consertar" estado | `init` num projeto existente só muda modo; problemas de estado se resolvem com os comandos da etapa |
| Esquecer `--dir` antes do subcomando | `$RS --dir <pasta> <comando>` |
| Rodar `status` ou `init` na pasta-mãe de um projeto | seguir `projetos_em_subpastas` e `$RS --dir "<subpasta>" status`; nunca `init --adotar` por cima |
| Colar a `proxima_acao` com `<...>` sem trocar | cada placeholder vira o valor conferido no arquivo que ele cita; `"press": true` só com PRESS humano registrado |
| Definir `RS="python3 ..."` e rodar `$RS status` | falha no zsh; use a função `rs` na mesma chamada ou o caminho completo |
| Contagem digitada em relatório ou critério | Copie do JSON dos comandos |

Registre sempre: decisões do usuário sobre modo, tipo e escopo (no G1 e em `00-protocolo/pergunta.md`); motivo de todo `--forcar`, reprovação e emenda; fallback usado quando faltar dependência ou skill irmã.
