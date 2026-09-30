# Contratos de construção da skill `revisao-sistematica`

Documento interno para quem implementa os scripts. As regras metodológicas vinculantes estão na especificação metodológica (Apêndice D da base de conhecimento) e reescritas, na forma operacional, em `skills/revisao-sistematica/references/`; os detalhes de engenharia vinham de um documento de trabalho não distribuído. Em conflito, vale: especificação metodológica > este documento. As seções 1 a 4 registram a divisão original do trabalho; as seções 5 e 6, os acréscimos de contrato das rodadas v1.1 e v1.2.

## 1. Já existe e está congelado (não reescrever; pode acrescentar funções sem mudar as existentes)

| Arquivo | Conteúdo |
|---|---|
| `skills/revisao-sistematica/scripts/rs.py` | dispatcher: importa `MODULOS_COMANDOS`; cada módulo expõe `registrar(subparsers)` e define `func(args) -> int` |
| `scripts/rslib/esquema.py` | colunas, caminhos do projeto, enums (eventos, etapas, portões, decisões, tipos de revisão), `MARCA_RASCUNHO` |
| `scripts/rslib/estado.py` | `encontrar_projeto`, `exigir_projeto`, `estado_inicial`, `carregar_estado`, `salvar_estado` (atômico), `registrar_evento`, `ler_log`, `marcar_etapa`, `abrir_pendencia`, `fechar_pendencia`, `pendencias_abertas`, `registrar_portao`, `resumo`, `sha256_arquivo`, `sha256_texto`, `agora` |
| `scripts/rslib/chave.py` | citekey v2 (`gerar_chave`, `chave_valida`, `primeiro_autor`, `sobrenome`, `lista_autores`) — vendorizado idêntico nas skills irmãs |
| `scripts/rslib/normalizar.py` | `vazio`, `texto`, `ascii_fold`, `doi`, `titulo_normalizado`, `titulo_principal`, `marcador_parte`, `idioma`, `tipo_publicacao`, `autores_canonicos`, `sobrenome_primeiro_autor`, `ano` |
| `assets/schemas/*.schema.json` | estado, evento, decisao, lote_resposta |
| `tests/conftest.py` | põe `scripts/` no path; fixture `projeto_vazio`, `fixtures_dir`; helper `ler_jsonl` |
| `tests/fixtures/chaves_golden.csv` | tabela ouro das chaves |

Se precisar de mudança num arquivo congelado, NÃO edite: descreva a necessidade no seu relatório final.

## 2. Convenções para todo comando

- Python ≥ 3.10, só stdlib + `pandas`, `openpyxl`, `xlrd`, `requests`, `pymupdf` como obrigatórios. Opcionais (importar dentro de try e degradar com aviso): `rapidfuzz`, `pyalex`, `anthropic`, `openai`, `jsonschema`, `bibtexparser`, `rispy`.
- `--dir` herdado do parser raiz; resolver a raiz com `estado.exigir_projeto(args.dir)` (exceto `init`, `status` e comandos parciais que aceitam arquivos soltos).
- Última linha do stdout: `estado.resumo({...})` com contagens e caminhos.
- Todo comando que altera o projeto chama `estado.registrar_evento(...)` com os artefatos escritos.
- Idempotência: rodar de novo com as mesmas entradas não duplica linhas nem eventos de dados (pode registrar um evento de reexecução).
- Joins sempre por `id_rs`, `id_registro` ou `chave`. Nunca por título.
- CSV: UTF-8, separador vírgula, cabeçalho exatamente como em `esquema.py`. Excel só como saída para humanos.
- Códigos de saída: 0 ok; 1 erro de uso/dados; 2 checagem metodológica falhou; 3 dependência ausente.
- Docstring do módulo em português com bloco `USO` e o porquê das decisões.
- Sem caminhos pessoais, e-mails, chaves de API ou nomes reais no código. Credenciais só por ambiente: `RS_EMAIL`, `OPENALEX_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`. Nunca ler `.env` implicitamente.
- Testes em `tests/test_<modulo>.py` (pytest), com fixtures sintéticas em `tests/fixtures/<modulo>/`. Dados reais do repositório OSF do material do MAPE/IESP-UERJ só em testes marcados `@pytest.mark.osf` e pulados sem `RS_OSF_DIR`.

## 3. Donos de arquivos e especificação por agente

### A1 — Skills irmãs + chave
Arquivos: `~/.claude/skills/baixar-pdfs-academicos/**`, `~/.claude/skills/gerar-bibtex/**`, `~/.claude/skills/fichamento-sistematico/**`, `tests/test_chave_sync.py`.
- Copiar `scripts/rslib/chave.py` byte a byte para `scripts/chave.py` de cada irmã; substituir `gerar_chave` locais por `from chave import gerar_chave` (mantendo a assinatura); `verificar_conteudo.sobrenome_autor` e `gerar_bib.formatar_autores` passam a usar `chave`.
- Aliases de chave sem `id` nem `key` (`["chave","citekey","bib_key"]`); chave existente inválida (`chave_valida` falso) → aviso e regeneração.
- Remover referência a `fichamento-academico` (SKILL.md e `references/checklist_codebook_12_secoes.md`).
- Trocar `~/.claude/skills/<x>/` por `${CLAUDE_SKILL_DIR}/` nos SKILL.md; `description` de cada irmã ≤ 1.024 caracteres preservando gatilhos principais.
- `fichamento-sistematico/scripts/concordancia.py`: acrescentar PABAK por variável categórica e sinalizar variáveis abaixo de κ/PABAK 0,7 ou 80% (sem mudar colunas existentes; só acrescentar).
- Remover `__pycache__` e `.DS_Store` das irmãs.
- Teste de sincronia: sha256 das 4 cópias iguais; smoke test de cada script irmão com `--help` e com um CSV mínimo.

### A2 — Importadores
Arquivos: `scripts/rslib/importar/{detectar,wos,scopus,openalex,scielo,pop,zotero_ris,capes_bdtd,generico,cli}.py`, `tests/test_importar.py`, `tests/fixtures/importar/`.
- `rs.py importar --arquivo F --busca-id B03 [--fonte auto|wos|...] [--mapa mapa.json] [--metodo base|citacao|cinzenta|manual] [--estrutura PICOC]`: detecta formato por assinatura (`importar/detectar.py`), converte para `esquema.COLUNAS_REGISTROS`, acrescenta a `dados/registros.csv` (sem duplicar `id_registro` em reimportação do mesmo arquivo/hash), copia o bruto para `01-busca/brutos/` se não estiver lá, registra busca em `estado["buscas"]` e evento `importacao`.
- Formatos: WoS plaintext, WoS/SciELO TSV, WoS BibTeX, WoS xls, Scopus CSV, OpenAlex CSV (web) e JSON/JSONL (API), Publish or Perish CSV, SciELO CSV do portal, Zotero CSV, RIS, CAPES Catálogo (dados abertos CSV/xlsx), BDTD, genérico com mapa.
- Usar `normalizar.*` para doi, título, idioma, tipo, autores canônicos e ano; abstract invertido do OpenAlex reconstruído; `resumo_truncado=1` para reticências do PoP.
- Testes com mini-exportações sintéticas (5–10 registros cada) cobrindo BOM, CRLF, linhas de continuação, chaves aninhadas, autores com `|`, pares com vírgula e reticências. Teste `osf` opcional com contagens das exportações reais do repositório OSF do material do MAPE/IESP-UERJ.

### A3 — Dedup e funil formal
Arquivos: `scripts/rslib/dedup.py`, `scripts/rslib/filtrar.py`, `assets/dicionarios/metodo_pt_en_es.csv`, `tests/test_dedup.py`, `tests/test_filtrar.py`, fixtures.
- `rs.py dedup [--limiar-auto 95] [--limiar-candidato 85] [--revisar pares.csv]`: lê `registros.csv`, gera/atualiza `registros_unicos.csv` (ids `RS0001` append-only e estáveis entre execuções; `chave` via `chave.gerar_chave` com conjunto de chaves existentes preservado) e `01-busca/dedup_pares.csv`, conforme regras R1–R5, versão preprint↔publicado, bloqueio de Part I/II, tese↔artigo nunca funde. `--revisar` aplica decisões humanas (confirmado/rejeitado) e refaz clusters. Mesclagem por prioridade de fonte (`esquema.PRIORIDADE_FONTES`). Candidatos pendentes geram pendência (autopiloto) ou aparecem no resumo (checkpoints). Rapidfuzz opcional com fallback difflib.
- `rs.py filtrar --config 01-busca/filtros_v1.json [--ancoras ancoras.csv]`: filtros sequenciais declarados (ano, tipo, idioma, dicionário) com modo `etiquetar` (padrão) ou `excluir` (só com `"previsto_no_protocolo": true`); casamento com fronteira de palavra, acentos dobrados, `*` truncamento, siglas sensíveis a caixa; campo ausente → `sem_dado` (mantém); registros sem resumo nunca excluídos por filtro textual; escreve `02-triagem/filtro_formal.csv` e contagens; âncora (por DOI ou título normalizado + ano) excluída → exit 2.
- Dicionário de métodos PT/EN/ES (colunas `termo,idioma,grupo,sensivel_caixa`) reconstruído a partir do Anexo F da proposta OQF e do script de filtragem do REFIS, corrigido (SEM, OLS, PCA, RCT como siglas sensíveis a caixa).
- Testes: pares plantados (DOI com prefixo/caixa, acentos, preprint↔publicado, título traduzido com mesmo DOI, Part I/II, tese↔artigo), estabilidade de ids, `\b` (SEM/sem, ols/bolsa, refis/Refiscalizar), âncora.

### A4 — Projeto, ambiente, status e PRISMA
Arquivos: `scripts/rslib/projeto.py`, `scripts/rslib/ambiente.py`, `scripts/rslib/prisma.py`, `assets/templates/prisma2020.svg.tmpl` (se usar template), `tests/test_projeto.py`, `tests/test_prisma.py`.
- `rs.py init --titulo T [--tipo ...] [--autonomia checkpoints|autopiloto] [--triagem subagentes|api] [--parcial triagem|meta|prisma] [--adotar]`: cria pastas e estado, evento `projeto_criado`, roda `ambiente`.
- `rs.py ambiente`: Python e pacotes (obrigatórios/opcionais), R e pacotes (`meta, metafor, esc, irr, clubSandwich, robvis`), Quarto, chaves de API como booleanos (variáveis de ambiente), skills irmãs (`${CLAUDE_SKILL_DIR}/../<nome>`, `~/.claude/skills/<nome>`, `${CLAUDE_PROJECT_DIR}/.claude/skills/<nome>`); grava em `estado["ambiente"]`.
- `rs.py status`: sem projeto, procura artefatos conhecidos e sugere `init --adotar`; com projeto, recalcula status das etapas a partir dos artefatos, lista pendências abertas, inconsistências (hash de artefato congelado alterado, contagens que não fecham) e `proxima_acao` (comando exato ou portão). Saída JSON.
- `rs.py portao G4 --aprovar|--reprovar --por <papel> [--criterios json] [--motivo]` e `rs.py pendencia listar|fechar P003 --motivo`.
- `rs.py prisma [--tipo 2020|scr] [--manual contagens.json]`: calcula contagens (references/08-relato.md e invariantes do Apêndice D) a partir de `registros.csv`, `registros_unicos.csv`, `filtro_formal.csv`, `triagem_ta_final.csv`, `relatorio_pdfs.csv`, `elegibilidade_tc_final.csv`, com ramos bases/registros e outros métodos; invariantes abortam com exit 2; "NR" para etapas ignoradas; escreve `07-relatorio/prisma_contagens.json`, `prisma.mermaid`, `prisma.svg` (sem dependências externas) e `checklist_prisma.csv` (27 itens a partir de `assets/checklists/prisma2020.csv` se existir; senão lista embutida). Marca `RASCUNHO NÃO VALIDADO` no SVG quando há pendências abertas.
- Testes: init idempotente, status com pendências, invariantes quebradas → exit 2, SVG gerado, "NR" em projeto parcial.

### A5 — R: efeitos, meta-análise, SWiM, testes combinados
Arquivos: `scripts/R/{_cli.R,efeitos.R,meta.R,swim.R,testes_combinados.R}`, `assets/mapas/conversoes_efeito.csv`, `tests/R/test_*.R`, `tests/test_r_smoke.py`.
- Especificação em references/06-decomposicao.md e 07a-sintese-quantitativa.md (conversões, meta-análise, SWiM, testes combinados) e no Apêndice D da base de conhecimento (itens 2 a 7). `_cli.R` sem optparse (`--chave=valor`), resumo JSON via jsonlite na última linha.
- `efeitos.R --in efeitos_extraidos.csv --out efeitos.csv [--delta 0.1]`: calcula `yi, vi, sei` (g de Hedges padrão), `formula_id`, `aproximado`, alinhamento de sinal por `direcao_desejada`, avisos; rejeita linhas de revisões/meta-análises como estudo; alerta |g| > 2.
- `meta.R --in efeitos.csv --out-dir 06-analise [--grupo construto_outcome] [--moderadores x,y] [--k-min 3]`: checa k; um efeito por estudo ou `rma.mv` + CR2 se `--dependencia che`; REML + HKSJ (modificado), τ² com IC, I², Q, intervalo de predição; forest (PNG/PDF); funil/Egger/PET-PEESE e `selmodel` 3PSM só com k ≥ 10; leave-one-out; sensibilidade sem aproximados e sem alto risco (coluna `rob_geral` se houver); JSON de resumo por grupo.
- `swim.R`: teste de sinal binomial exato por direção, proporção benéfica com IC, effect direction plot, albatross plot quando só há p e n.
- `testes_combinados.R`: Stouffer ponderado com p unilateral na direção declarada, Winer com t e df > 2, Cooper = teste de sinal, Fisher rotulado não direcional; um p por estudo; imprime a ressalva obrigatória.
- Fórmulas re-derivadas das fontes (Borenstein, Cochrane, metafor/esc); não copiar os scripts em R do material do MAPE/IESP-UERJ.
- Testes testthat com valores de referência (d a partir de médias/DP; g de t; OR→d; conversão coeficiente/DP), dataset conhecido do metafor (`dat.bcg` ou `dat.normand1999`) para `meta.R`; `skip_if_not_installed`.

### B1 — Triagem por lotes e validação
Arquivos: `scripts/rslib/triagem_lotes.py`, `scripts/rslib/validacao.py`, `agentes/triador-ta.md`, `agentes/arbitro-cego.md`, `tests/test_triagem_lotes.py`, `tests/test_validacao.py`.
- `rs.py triagem preparar --etapa ta --rodada ta_v2 --revisor A --criterios 02-triagem/prompts/ta_v2.md [--tamanho 25] [--semente 7] [--ids arquivo] [--apenas-divergentes]`; `mesclar --rodada ta_v2 --revisor A [--modelo nome]` (valida `lote_resposta.schema.json`, conjunto de IDs, enums, critério existente no arquivo de critérios, `trecho` ⊂ título/resumo normalizados; inválido → evento `lote_rejeitado` e arquivo em `rejeitados/`); `consolidar --rodada ta_v2 [--regra liberal|consenso]` (precedência override humano > árbitro > consenso; `incerto` conta como incluir para seguir ao texto completo; divergências → fila humana `02-triagem/fila_humana_<rodada>.csv` e pendência no autopiloto) e `override --id RS0042 --decisao incluir --motivo`. Escreve `dados/decisoes.jsonl` via funções deste módulo (append-only, última linha por chave vence).
- `rs.py validar amostrar --etapa ta --rodada ta_v2 --n 100 --semente S [--enriquecer-incluidos 60] [--elusao 300]` (planilha cega xlsx sem colunas de IA, ordem embaralhada; registra desenho da amostra e pesos) e `calcular --planilha amostra_codificada.xlsx` (κ Cohen/Fleiss, PABAK, % concordância, sensibilidade/especificidade/precisão/VPN com IC Clopper-Pearson, WSS@95, estimativa de perdidos pela elusão, reponderação; "não revisado" = NA fora; limiares de references/ia-validacao.md → `atende_limiares` true/false; em falha, lista falsos negativos). `estabilidade --rodada ... --amostra 0.1`. Evento `validacao_calculada`.
- `agentes/triador-ta.md` e `agentes/arbitro-cego.md`: prompts para subagentes (ler critérios, depois lote; reler critérios antes de decidir; estudar vs mencionar; sem resumo → incerto; escrever só o arquivo de resposta; devolver uma linha).
- Testes: IDs faltando/extras/duplicados, enum inválido, JSON malformado, trecho inventado, precedência, κ = scikit-learn, PABAK, IC, NA.

### B2 — Triagem via API
Arquivos: `scripts/rslib/triagem_api.py`, `scripts/rslib/provedores.py`, `tests/test_triagem_api.py`.
- `rs.py triagem api --rodada ta_v2 --criterios ... --modelo-a ... --modelo-b ... --arbitro ... [--concorrencia 8] [--limite N] [--estimar] [--batch]`: porta a lógica de triagem por API de um projeto anterior de revisão de escopo (`utils_screening.py` e `01screening.py`, não distribuídos) com as correções da especificação (sem resumo → incerto; árbitro de terceiro provedor com "Revisor A/B"; instrução depois do texto; erros re-tentados, nunca pulados; retomada por `(id_rs, rodada, papel)`; linha final truncada tolerada; lock no JSONL). Grava em `dados/decisoes.jsonl` no mesmo formato do B1 (`tipo_ator: ia_api`, `modelo`, `prompt_sha`).
- `provedores.py`: interface `Provedor.decidir(sistema, usuario, schema) -> dict`; Anthropic (sem `temperature` para modelos Claude 5/Opus ≥ 4.7; saída estruturada; ler só blocos de texto; checar `stop_reason`) e OpenAI (`response_format` json_schema); tabela de modelos e preços como constantes marcadas "verificar"; `--estimar` sem chamadas; falta de pacote/chave → exit 3 com instrução.
- Testes com provedor falso: queda no meio e retomada, erro re-tentado, árbitro só em divergência, `max_tokens` não é sucesso, sem `temperature` em Claude 5.

### B3 — Busca OpenAlex, bola de neve, textos, handoffs, efeitos, caixa, declaração de IA
Arquivos: `scripts/rslib/{busca_openalex,bola_de_neve,textos,handoff,efeitos_verificar,caixa,declaracao_ia}.py`, `agentes/extrator-efeitos.md`, `assets/mapas/caixa_ferramentas_mapa.csv`, testes correspondentes.
- `rs.py buscar openalex --busca-id B05 --query "..." [--filtro ...] [--string-id S-oa-v1] [--contar]`: porta `utils_openalex.py` (fetch paginado, abstract invertido, flatten); grava JSONL bruto em `01-busca/brutos/` e chama o importador OpenAlex (A2) se disponível; `RS_EMAIL` como mailto; `--contar` só conta.
- `rs.py bola-de-neve --direcao tras|frente|ambas --rodada SN1 [--ids incluidos.csv]`: resolve W ids por DOI (fallback título ≥ 95 + ano), referências e citações, grava registros `metodo=citacao`, sugere `dedup` e re-triagem.
- `rs.py textos para-baixar` (incluídos/incertos da T/A → `para_baixar.csv`), `textos inventario` (pymupdf: páginas, camada de texto; junta `verificacao_conteudo.csv`), `textos elegibilidade consolidar --master fichamentos_master.csv --codebook ...` (primeiro critério que falha vira motivo), `textos ligar-relatos --pares pares.csv` (define `id_estudo`).
- `rs.py bib` / `rs.py incluidos`: `07-relatorio/incluidos.csv`; se `gerar-bibtex` ausente, escreve `.bib` mínimo com `chave`.
- `rs.py analise preparar-efeitos` (junta `efeitos_extraidos.csv` do agente extrator com metadados e codebook) e `verificar-efeitos` (trecho verbatim na página via `fichamento-sistematico/scripts/verify_citacoes.py` se existir, senão verificação própria com pymupdf; plausibilidade: DP > 0, n_t + n_c ≤ N, p coerente com t/df, |g| > 2; `verificado_humano` obrigatório para seguir ao G7).
- `rs.py caixa --master ... --efeitos 06-analise/meta_resumo.json --certeza 06-analise/certeza.csv --mapa assets/mapas/caixa_ferramentas_mapa.csv`: monta a tabela da caixa de ferramentas com as regras de rótulo de references/07b-sintese-qualitativa-integracao.md (Positivo/Negativo/Nulo/Inconclusivo/Misto; força via GRADE; implementação por pontos) e `fontes` por célula; nunca usa testes combinados para rótulo; célula sem certeza → rótulo pendente.
- `rs.py declaracao-ia`: gera `07-relatorio/declaracao_uso_ia.md` a partir do log (modelos, datas, papéis por etapa, prompts com hash, validação com métricas e limiares, elusão, pendências e marca de rascunho).
- `agentes/extrator-efeitos.md`: prompt do subagente que lê o PDF inteiro em faixas ≤ 20 páginas e escreve linhas de efeito com trecho e página.
- Testes com fixtures sintéticas (incluindo PDF gerado com pymupdf).

## 4. Relatório final de cada agente
Arquivos criados/alterados; comandos implementados; resultado de `python3 -m pytest -q tests/<seus testes>` (colar o resumo); desvios da especificação e por quê; necessidades de mudança em arquivos congelados.

## 5. Contratos v1.1

Acréscimos compatíveis feitos depois da primeira rodada de construção. Nenhum valor existente mudou: as constantes novas moram em `scripts/rslib/esquema.py` (bloco "Acréscimos de contrato (v1.1)") e os módulos que as definiam passaram a importá-las de lá, mantendo os nomes antigos como aliases (`textos.ARQ_RETRATACOES`, `flags.ARQ_REGISTROS_FLAGS`, `prisma.ARQ_SVG`...). O teste `tests/test_nucleo.py::test_regressao_contratos_v11_em_esquema_e_modulos_importam_de_la` confere valores e origem.

### 5.1 Constantes novas em `esquema.py`

| Constante | Valor | Quem escreve / lê |
|---|---|---|
| `FINALIDADES_VALIDACAO` | `calibracao, desenvolvimento, validacao, elusao, estabilidade` | `validar` grava em `validacao_calculada.dados.finalidade`; G4 e `declaracao-ia` leem |
| `VERSAO_ATIVA_RODADA_TA` | `rodada_ta` (em `versoes_ativas`; `rodada_<etapa>` fora da T/A) | `triagem consolidar` grava; G4, `status`, `prisma`, `override` leem |
| `DECISOES_TC_FINAL`, `DECISAO_TC_AGUARDANDO` | `incluir, excluir, aguardando` | `textos elegibilidade consolidar` grava; `prisma` e G5 leem |
| `DECISAO_LEDGER_AGUARDANDO_TC` | `incerto` | convenção do ledger: `incerto` humano na etapa `tc` = aguardando |
| `CAMPO_BUSCA_ATIVA` | `ativa` (em `estado.buscas[i]`; ausente = ativa) | `importar --substituir` grava `false` |
| `FLAG_BUSCA_INATIVA` | `busca_inativa` (em `registros_unicos.flags`) | `dedup` grava; `filtrar`, `triagem preparar`, `triagem api`, `validar`, `bola-de-neve`, `prisma` ignoram |
| `FLAG_RETRATADO` | `retratado` | importador (flag da fonte) e `dedup` |
| `ARQ_REGISTROS_FLAGS`, `COLUNAS_REGISTROS_FLAGS` | `dados/registros_flags.csv`: `id_registro, flag, origem, registrado_em` | `importar`/`buscar openalex` acrescentam (append-only); `dedup` lê |
| `ARQ_RECALL_ANCORAS` | `01-busca/recall_ancoras.json` | `filtrar --ancoras` grava; G3 avisa |
| `DIR_STRINGS` | `01-busca/strings` | congelado no G3 |
| `ARQ_CONFERENCIA_PDFS`, `COLUNAS_CONFERENCIA_PDFS` | `03-textos/conferencia_pdfs.csv`: `chave, recuperado, motivo` | humano escreve; `textos inventario` lê (prevalece em `recuperado`) |
| `ARQ_RETRATACOES`, `COLUNAS_RETRATACOES` | `03-textos/retratacoes.csv`: `chave, id_rs, doi, openalex_is_retracted, crossref_avisos, retratado, status, verificado_em` | `textos retratacoes` |
| `ARQ_CONTATO_AUTORES`, `COLUNAS_CONTATO_AUTORES` | `03-textos/contato_autores.csv`: `chave, autor_contatado, data, pedido, resposta, dados_recebidos` | `textos contato-autores --registrar` |
| `DIR_VALIDACAO`, `SUFIXO_PLANILHA_CEGA`, `SUFIXO_DESENHO`, `SUFIXO_METRICAS`, `ARQ_DESENHO_ESTABILIDADE` | `02-triagem/validacao`, `_cega.xlsx`, `_desenho.json`, `_metricas.json`, `estabilidade_desenho.json` | `validar` (`<DIR>/<rodada>/amostraNN_*`) e `filtrar` (`<DIR>/elusao_<versao>_*`) |
| `ARQ_PRISMA_MERMAID`, `ARQ_PRISMA_SVG`, `ARQ_PRISMA_PNG`, `ARQ_CHECKLIST_PRISMA` | `07-relatorio/prisma.mermaid`, `.svg`, `.png`, `checklist_prisma.csv` | `prisma` (com `ARQ_PRISMA_CONTAGENS`) |
| `PORTOES_OPCIONAIS_POR_TIPO` | escopo: G7, G8; mapa_evidencias: G6, G7, G8; realista: G4 | `portao --nao-se-aplica` |
| `VARIANTES_REVISAO` | `rapida` | `init --variante`, critério `variante` do G1; grava `projeto.variante` |
| `PENDENCIA_*` | `conferencia_elegibilidade_tc`, `retratacao_texto`, `verificacao_humana_efeitos`, `certeza_caixa`, `calibracao_reprovada`, `validacao_triagem_reprovada` | tipos de pendência abertos por comandos |
| `COLUNAS_EFEITOS_EXTRAS_NUMERICAS` | `q1_1, q3_1, q1_2, q3_2, g, d, m_preditores` | colunas extras de `efeitos_extraidos.csv` lidas por `efeitos.R` |
| `EVENTOS` (acréscimos) | `busca_substituida`, `retratacoes_verificadas`, `contato_autores`, `etapa_nao_aplicavel` | ver 5.3 |

### 5.2 Schemas

- `estado.schema.json`: `projeto.variante` (`rapida` ou null); `buscas[]` declara os campos PRISMA-S (`string_id`, `executada_em`, `executada_em_origem` = `arquivo|declarada`, `n_bruto`, `n_importado`, `filtros_na_base`, `plataforma`, `metodo_identificacao`, `estrutura`, `arquivos`) e os de substituição (`ativa` booleano, `substituida_por`, `substituida_em`, `motivo_substituicao`, `substitui`). Sem `additionalProperties: false`, então estados antigos continuam válidos.
- `decisao.schema.json`: o enum continua `incluir|excluir|incerto`. Convenção documentada no próprio schema: `incerto` com `tipo_ator = humano` na etapa `tc` significa "aguardando classificação" (`triagem override --etapa tc --decisao aguardando` grava assim e `textos elegibilidade consolidar` lê assim).
- `evento.schema.json`: enum de eventos com os quatro acréscimos.

### 5.3 Flags e artefatos novos por módulo

| Módulo | Flags / subcomandos | Artefatos e eventos |
|---|---|---|
| `projeto.py` | `init --variante rapida`; `init` sem `--titulo` num projeto existente; `portao GN --nao-se-aplica --por --motivo` (só portões de `PORTOES_OPCIONAIS_POR_TIPO`, depois do G1) | evento `etapa_nao_aplicavel`; resumo de `portao` com `avisos` e bloqueios tipados (`artefato`/`limiar` barram o autopiloto; `validacao`/`verificacao`/`certeza`/`pendencia` viram pendência no autopiloto); `status` com `alertas` (`busca_desatualizada`, `busca_sem_data`), `motivos_rascunho`, `contagens.buscas_inativas`, fonte `nao_se_aplica` e `proxima_acao.alternativa` |
| `projeto.py` (portões) | G1 pergunta e tipo; G2 protocolo (aviso sem revisor metodológico); G3 busca e congelamento de `01-busca/strings/**` e `filtros_*.json`, com **avisos** sem `recall_ancoras.json`, com recall combinado < 1 (lista `combinado.perdidas`) ou calculado sobre outro `registros_unicos.csv`; G4 validação `finalidade=validacao` da rodada ativa; G5 invariantes; G6 piloto; G7 verificação de efeitos atual; G8 caixa definida; G9 PRISMA atual e declaração de IA, com **avisos** sem `07-relatorio/references.bib` e com declaração que cobre o log só até um `seq` anterior ao último evento que não é da própria declaração | `criterios.checagens_script` no evento `portao` guarda bloqueios forçados e avisos |
| `prisma.py` | `--tipo` padrão `scr` para escopo/mapa, `2020` nos demais | `07-relatorio/prisma.png`; `prisma_contagens.json` com `aguardando_classificacao`, `buscas_inativas`, insumos `inventario_textos.csv` e `estado.buscas_inativas`; invariantes `avaliado_nao_recuperado` e `decisoes_de_busca_substituida`; clusters `busca_inativa` saem do fluxo com aviso informativo (sem a flag, o aviso pede `dedup`) |
| `importar/cli.py` | `--string-id`, `--executada-em`, `--n-base`, `--filtros-na-base`, `--plataforma`, `--substituir <busca_id> --motivo` | `estado.buscas[i]` com PRISMA-S e `ativa`; eventos `busca_registrada` (origem `importar`) e `busca_substituida`; `dados/registros_flags.csv` |
| `importar/buscas.py`, `importar/flags.py` | helpers `validar_busca_id`, `busca_ativa`, `inativas`, `cluster_inativo`; `flags.ler`/`acrescentar` | regra única de `busca_id` (`^[A-Z]{1,4}\d{1,4}$`) |
| `dedup.py` | (sem flag nova) | clusters só com registros inativos preservados com `busca_inativa`; `dedup.unicos_ativos()`; evento com `buscas_inativas`, `n_unicos_inativos`, `ids_rs_inativos`, `n_retratados` |
| `busca_openalex.py` | `--campo *.search.exact`; `--listar N` | `00-protocolo/exploracao_<busca_id>.csv`; recusa busca substituída |
| `filtrar.py` | `--ancoras` (coluna opcional `indexada_em`); `--amostra-elusao N --semente S`; `--calcular-elusao PLANILHA [--desenho]` | `01-busca/recall_ancoras.json` (`combinado`, `combinado_todos_metodos`, `por_busca`, `por_base`, `perdidas`, `unicos_sha256`); `02-triagem/validacao/elusao_<versao>_{cega.xlsx,desenho.json,metricas.json}`; `validacao_calculada` com `finalidade=elusao`, `tipo=elusao_filtro` |
| `bola_de_neve.py` | `--rodada` com a regra de `busca_id` | corpus conhecido e sementes padrão sem buscas inativas |
| `triagem_lotes.py` | `override --decisao aguardando` (só `--etapa tc`); `--rodada` padrão = rodada ativa; recusa rodadas `*_estab` | `versoes_ativas.rodada_ta`; fila humana com `motivo_fila` (`divergencia`, `divergencia_regra_liberal`, `arbitrada`); `preparar` ignora clusters `busca_inativa` (inclusive em `--ids`) e informa `n_inativos_ignorados` |
| `triagem_api.py`, `provedores.py` | `--precos` também para o custo registrado; `--estimar` registrado | eventos com `custo_estimado_usd`, `custo_por_papel`, `tabela_precos`, `chamadas_api`; clusters `busca_inativa` não vão à API (resumo `n_inativos_ignorados`) |
| `validacao.py` | `amostrar --finalidade --excluir-ids --ids --sem-ia --criterios`; `elusao`, `calcular`, `estabilidade --finalidade` | `validacao_calculada.dados.finalidade` e `sem_ia`; desenho com `populacao_rodada`, `n_excluidos_quadro`, `n_inativos_ignorados` (clusters `busca_inativa` fora do quadro e dos pesos, também na estabilidade); pendências `calibracao_reprovada` e `validacao_triagem_reprovada` |
| `textos.py` | `textos retratacoes [--fonte openalex\|crossref\|ambas] [--ids]`; `textos contato-autores --registrar`; `elegibilidade consolidar` com `--master/--codebook` opcionais | `inventario_textos.recuperado`; `03-textos/conferencia_pdfs.csv`, `retratacoes.csv`, `contato_autores.csv`; eventos `retratacoes_verificadas`, `contato_autores`; pendências `conferencia_elegibilidade_tc` (n = propostas ainda sem decisão humana) e `retratacao_texto` (qualquer modo) |
| `efeitos_verificar.py` | (sem flag nova) | `efeitos_extraidos.csv` = esquema + colunas extras; plausibilidade de quartis e de `m_preditores`; pendência `verificacao_humana_efeitos` com n = linhas não aptas |
| `caixa.py` | (sem flag nova) | `validado_humano` rebaixa a `rascunho` em todas as dimensões; `caixa_gerada.dados.n_pendentes` e `n_rascunho`; pendência `certeza_caixa` com n = células não definidas |
| `declaracao_ia.py` | (sem flag nova) | marca de rascunho só pela validação que decide; custo por evento; texto traz "até o evento seq N" (lido pelo aviso do G9) |
| `scripts/R/efeitos.R` | (sem flag nova) | `formula_id` novos: `r_d_n_total`, `mediana_iqr_aprox`, `parcial_r_d_gl`; `mediana_iqr_wan` só com quartis; `parcial_r_d` com `m_preditores` (r_p = t/√(t² + n − m − 1), Var = (1 − r_p²)²/(n − m)); `mann_whitney_z` por r = z/√N |
| `scripts/R/meta.R` | `--excluir-rob=nenhum\|critico` (e `analise meta --excluir-rob`) | `meta_resumo.json`: `contrato_campos`, `pi_referencia`, `excluidos_rob_critico`, `sensibilidade.com_rob_critico`, `vies_publicacao.preditor_precisao`; `pet_peese` com `pet_p_unilateral` e regra condicional (PEESE só com intercepto do PET > 0 e p unilateral < 0,05) |
| `scripts/R/_cli.R` | (sem flag nova) | `classe_desenho` trata negação e quase-experimentos; `eh_revisao` exige o tipo de revisão |

### 5.4 Pendências: uma regra só

Todo comando que abre pendência a partir de uma contagem usa `handoff.sincronizar_pendencia_unica(raiz, tipo, etapa, descricao, n, portao, arquivo, ator_id, motivo_resolvida, qualquer_modo=False, qualquer_arquivo_ao_fechar=False)`:

- `n > 0` e nenhuma aberta: abre só no autopiloto (ou em qualquer modo com `qualquer_modo=True`, caso de `retratacao_texto`); não reabre o que um humano fechou com o mesmo `n` sobre o mesmo conteúdo do `arquivo`.
- `n > 0` e já aberta com outro `n`: fecha a antiga (ator `script`, motivo `n X -> Y`) e abre a nova com `[substitui Pxxx]`, em qualquer modo; nunca duplica.
- `n == 0`: fecha as abertas de (tipo, arquivo) em qualquer modo (ator `script`, `motivo_resolvida`).

Usuários: `textos` (`conferencia_elegibilidade_tc`, `retratacao_texto`), `analise verificar-efeitos` (`verificacao_humana_efeitos`), `caixa` (`certeza_caixa`, fechada antes de decidir a marca de rascunho), `dedup` (`dedup_candidatos`), `triagem consolidar` e `validar` (via `triagem_lotes.sincronizar_pendencia`). Pendências manuais (`pendencia abrir`) e de revisão de portão continuam em `projeto.py`. O teste `tests/test_handoff.py::test_regressao_comandos_usam_a_sincronizacao_do_handoff` impede chamadas diretas a `estado.abrir_pendencia` fora desses módulos.

## 6. Contratos v1.2

Acréscimos da rodada v1.2, compatíveis com projetos v1.1: nenhum valor existente de `esquema.py` mudou e nenhum schema JSON foi editado nesta rodada. As regras metodológicas que motivaram cada acréscimo estão nas references (SKILL.md e `skills/revisao-sistematica/references/`) e no Apêndice D da base de conhecimento; o que segue é o contrato entre módulos.

### 6.1 Constantes

Em `scripts/rslib/esquema.py`, bloco "Acréscimos de contrato (v1.2)":

| Constante | Valor | Quem escreve / lê |
|---|---|---|
| `CAMPO_BUSCA_TRUNCADA` | `truncada` (em `estado.buscas[i]`) | `buscar openalex --max-paginas` grava; `status` (alerta `busca_truncada`, rascunho), G3 (bloqueio limiar) e `prisma` (aviso, rascunho, insumos) leem |
| `DIR_QUALIDADE` | `04-qualidade` | `qualidade consolidar` |
| `PADRAO_ROB_CONSENSO`, `COLUNAS_ROB_CONSENSO` | `04-qualidade/rob_{ferramenta}_consenso.csv`: `chave, id_estudo, construto_outcome, ferramenta, dominio, julgamento_a, julgamento_b, julgamento_consenso, justificativa, trecho, pagina, resolvido_por` | `qualidade consolidar` fase 1 grava; humano resolve; fase 2 lê |
| `ARQ_ROB_GERAL`, `COLUNAS_ROB_GERAL` | `04-qualidade/rob_geral.csv`: `chave, id_estudo, construto_outcome, ferramenta, rob_geral, validado_humano` | `qualidade consolidar` fase 2 grava (troca só as linhas da ferramenta); junção manual com os efeitos (references/06-decomposicao.md, seção 8) |
| `TIPOS_SEM_ROB` | `escopo`, `mapa_evidencias` | G7 não exige `rob_consolidado` nesses tipos |
| `ARQ_FILA_HUMANA_TC` | `03-textos/fila_humana_tc.csv` | `triagem fila --etapa tc` grava; `triagem override --fila --etapa tc` lê |
| `PAPEL_HUMANO_PADRAO` | `revisor_humano_1` | padrão de `--por` em `portao`, `pendencia fechar`, `emenda`, `triagem override`, sugestões de `dedup --revisar`, `qualidade consolidar` e `proxima_acao` |
| `REF_REGRAS` | `references/ (ver SKILL.md) e Apêndice D da base de conhecimento` | mensagens que citam a origem das regras (nunca documentos internos não distribuídos) |
| `EVENTOS` (acréscimos) | `rob_consolidado`, `fila_gerada` | ver 6.3 |

Constantes que eram locais na v1.2 e foram promovidas a `esquema.py` na v1.3, com os mesmos valores (seção 7.1). `dedup.py`, `triagem_lotes.py` e `efeitos_verificar.py` já importam de lá (aliases); `projeto.py`, `qualidade.py` e `caixa.py` ainda definem as suas cópias, e `tests/test_contratos_v13.py` confere que os valores coincidem:

| Módulo | Constante local | Valor |
|---|---|---|
| `projeto.py` | `PENDENCIA_PRESS`, `PENDENCIA_CONCORDANCIA` | `revisao_press`, `concordancia_extracao` |
| `projeto.py` | `TIPOS_SEM_CERTEZA` | `escopo`, `mapa_evidencias`, `realista` |
| `projeto.py` | `CRITERIO_ATALHO_RAPIDA`, `FRACAO_MINIMA_DUPLA_RAPIDA` | `atalho_rapida`, `0.20`; campos lidos do evento: `fracao_dupla_humana`, `n_dupla_humana`, `n_populacao`, `kappa_humanos`, `segunda_leitura_excluidos`, `n_excluidos_ia`, `n_excluidos_relidos` |
| `projeto.py` | `MIN_INCLUIDOS_LIMIAR_ALCANCAVEL` | `36` |
| `triagem_lotes.py` | `COLUNAS_FILA_HUMANA_TC`, `ARQ_CODEBOOK_ELEGIBILIDADE` | `id_rs, chave, proposta, criterio_proposto, evidencia, pagina, decisao_humana, criterio_humano, motivo`; `00-protocolo/codebook_elegibilidade.csv` |
| `qualidade.py` | `PENDENCIA_CONSENSO_ROB`, `PADRAO_CONCORDANCIA` | `consenso_rob`; `04-qualidade/rob_{ferramenta}_concordancia.csv` |
| `efeitos_verificar.py` | `COLUNAS_EFEITOS_BINARIOS` | `p0, p1, efeito_pp, se_pp` (acrescentar a `COLUNAS_EFEITOS_EXTRAS_NUMERICAS`) |
| `caixa.py` | `DIMENSAO_PAINEL`, `REGRA_VERSAO` | `efeito_painel`, `caixa-3` |
| `dedup.py` | `DECISAO_LIGADO`, `DECISOES_PARES`, `MOTIVO_VERSAO_LIGADA` | `ligado` (na v1.3, também em `esquema.DECISOES_DEDUP`), `preprint_publicado` |

O comentário de `tipo_estatistica` em `COLUNAS_EFEITOS_EXTRAIDOS` passou a citar `dif_prop` e `rr` na v1.3.

### 6.2 Estado, trava e escrita

- `estado.trava(raiz)`: gerenciador de contexto reentrante no mesmo processo e thread, com `fcntl.flock` em `<raiz>/.rs.lock` (`msvcrt.locking` no Windows; sem nenhum dos dois, só a trava de thread). Usado por `registrar_evento`, `salvar_estado`, `marcar_etapa`, `abrir_pendencia`, `fechar_pendencia` e `registrar_portao`. Dentro da trava o `seq` é recalculado do log; `abrir_pendencia`, `fechar_pendencia` e `registrar_portao` recarregam o estado. Assinaturas mantidas.
- `salvar_estado` faz mescla em três vias com o disco: base = o que `carregar_estado` leu (ou o último save do mesmo objeto; registro limitado a 64 objetos); cada lado fica com o que só ele mudou; em conflito, vale quem grava agora; listas de objetos com `id` (`pendencias`, `buscas`) mesclam por id, listas simples como conjuntos. Dict novo (`estado_inicial`) substitui o arquivo.
- `carregar_estado`: `JSONDecodeError` e `UnicodeDecodeError` viram `ErroProjeto` com `DICA_ESTADO_CORROMPIDO`; `status`, `prisma`, `ambiente` e `declaracao-ia` saem com código 1 e resumo JSON.
- `estado.escrever_atomico(caminho, texto, encoding="utf-8", newline=None)` e `estado.modo_arquivo_padrao()`: chmod 0666 menos a umask antes do `os.replace`. Usado por `rs_estado.json`, saídas do `prisma` e declaração de IA e, desde a v1.3, por `dedup.escrever_csv`, `triagem_lotes.escrever_atomico` (e `escrever_csv`/`escrever_json`), `filtrar._gravar_atomico`, `importar/cli.gravar_registros` e `importar/flags.acrescentar`. Ainda com `mkstemp` 0600: `handoff.escrever_csv/escrever_texto` (usados por `textos`, `caixa`, `qualidade`, `bola_de_neve`, `busca_openalex` e `efeitos_verificar`).
- `status` acusa `seq_repetido_no_log` (aviso).

### 6.3 Flags, artefatos e eventos por módulo

| Módulo | Flags / subcomandos | Artefatos, resumos e eventos |
|---|---|---|
| `projeto.py` (`status`, `init`) | `status` sem projeto procura `rs_estado.json` em subpastas (até 2 níveis); `init` recusa pasta que contém projeto em subpasta (com ou sem `--adotar`) | resumo `projetos_em_subpastas`, `proxima_acao` `$RS --dir "<subpasta>" status` com `alternativas`; `detectar_artefatos` não entra em subpasta que é projeto e nunca sugere arquivos que a skill escreve; `_cheirar` reconhece OpenAlex CSV pelo cabeçalho (`authorships.*` ou `display_name` + `publication_year`, com `,`, `;` ou tab), JSON/JSONL pelo `"id": "https://openalex.org/W..."`, e classifica cabeçalho de codebook como `codebook`; com `--dir`, a `proxima_acao` de `init` e `portao` inclui o `--dir`; alertas `busca_truncada` (novo) e `busca_sem_data` calado com `04_busca` ignorada; `motivos_rascunho` com buscas truncadas |
| `projeto.py` (`proxima_acao`) | — | placeholders fora de aspas (`<pergunta aprovada pelo usuário, entre aspas>`, `<valor de 01-busca/recall_ancoras.json>`, `<press: true só com revisão humana registrada>`, `<sensibilidade da validação seq N>`); antes do G3 pede PRESS (`pendencia abrir --tipo revisao_press` no autopiloto) e `importar --substituir` com busca truncada; antes do `consolidar` (subagentes) pede `triagem mesclar` de lotes não mesclados e `triagem preparar --revisor arbitro --apenas-divergentes` com divergências de IA sem árbitro (alternativa `--regra liberal`); validação sem falsos negativos e < 36 incluídos humanos aponta remédio 5 e `--forcar --motivo` |
| `projeto.py` (portões) | — | G2: `00-protocolo/protocolo*`, `00-protocolo/codebook_v0*.csv`, codebook de elegibilidade (`00-protocolo/` ou `03-textos/codebook_elegibilidade*.csv`), sem placeholders `<...>`/`{...}` no protocolo nem `{...}` nos codebooks (artefato; ignora comentários HTML, código, matemática, autolinks, tags HTML comuns, `{#sec}`/`{.classe}`, JSON e LaTeX). G3: busca truncada ativa (limiar); PRESS em `01-busca/press_*.md` ou pendência `revisao_press` aberta (artefato); aviso de recall mantido. G4: atalho da variante rápida (`projeto.variante = rapida` + `atalho_rapida` no G1 + validação com `dados.atalho_rapida = true`: dupla ≥ 20% (limiar), `kappa_humanos` e segunda leitura (validacao), sem exigir recall; sem o critério no G1, regra geral com aviso). G7: fora de `TIPOS_SEM_ROB`, evento `rob_consolidado` e sha dos artefatos citados (artefato; na v1.3, por ferramenta, com `todos_validados_humano` e cobertura dos resultados avaliados, seção 7.3); avisos sem `05-decomposicao/**/concordancia.csv` fora do piloto ou com variáveis sinalizadas (bloco `por_variavel`) sem pendência `concordancia_extracao` fechada para o arquivo. G8: caixa obrigatória em `oqf_mista_sequencial` (artefato); `06-analise/certeza.csv` obrigatório fora de `TIPOS_SEM_CERTEZA` sem caixa (artefato); toda célula `efeito` da caixa com linha de certeza por família, construto e classe (certeza). G9: seq coberto por `dados.ultimo_seq` do `relatorio_gerado` cujo sha256 é o atual (fallback: frase do texto; sem evento: aviso "escrita à mão ou editada"); ignora eventos com `dados.reexecucao = true` |
| `prisma.py` | — | helpers `busca_truncada`, `buscas_truncadas`, `rotulo_fonte`, `marcar_rascunho`; aviso, `rascunho`, `buscas_truncadas` e `motivos_rascunho` no resumo, no JSON e no evento `prisma_gerado`; "Buscas truncadas: B01" no SVG e no Mermaid; lista nos insumos e no hash; fonte genérica rotulada pela plataforma declarada ou pelo `busca_id` (também no item 6 do checklist) |
| `declaracao_ia.py` | — | `relatorio_gerado.dados.ultimo_seq`; só reescreve o arquivo quando o texto muda |
| `dedup.py` | `--revisar` exige `decidido_por` na planilha ou `--por` (padrão `None`; vazio, `script` e `regra` recusados; código 1 sem gravar); decisão `ligado` | regra `versao` nunca funde: `ligado` (`decidido_por=script`) ou candidato (`ligaria_dois_publicados_no_estudo`); ligação entre clusters por `textos.ligar_relatos`; ligações humanas de `03-textos/ligacao_relatos.csv` preservadas (pares em `dedup_executado.dados.ligacao_relatos`); clusters antigos fundidos separados com aviso; `dedup.pares_versao_ligados(raiz)`; sem mudança, sem decisão nova e com os mesmos parâmetros não grava `dedup_executado` (resumo `reexecucao`, `evento_registrado`) |
| `importar/cli.py` | `--n-base` em busca de `buscar openalex` conferido com `n_api` | igual: aceito sem gravar (aviso, `n_base_openalex`); `n_api` nulo: grava; diferente: código 1; `busca_registrada` do importar leva `n_api`; `cli.checar_substituicao`, `cli.aplicar_substituicao` |
| `busca_openalex.py` | `--substituir BUSCA_ID_ANTIGA --motivo` (recusado com `--contar`/`--listar`) | validação antes da API; substituição aplicada depois de importar e registrar (`busca_substituida`, `ja_aplicada` na reexecução, também com `--sem-importador`); resumo `busca_registrada: true`, `evento_busca_registrada_seq`, `busca_registrada_agora` |
| `triagem_lotes.py` | `triagem fila --etapa tc [--master --codebook --verificacao --criterios]`; `override --criterios <md\|csv\|xlsx>`; `--por` padrão `revisor_humano_1` | `ler_tabela_humana(caminho, obrigatorias, alternativas, aba)` (na v1.3, em `planilhas.py`, com alias aqui) (`,` `;` tab, BOM, UTF-8/UTF-16/cp1252, xlsx; openpyxl ausente = código 3); `consolidar` valida a fila antes de gravar e a preserva (`fila_preservada`, `linhas_fila_nao_aplicadas`); exclusão humana exige critério conferido (manifestos, `02-triagem/api/<rodada>/criterios.md`, variáveis-critério do TC), apelido `C2` → canônico, inclusão com critério recusada, fila tudo ou nada, roteamento T/A × TC pelo cabeçalho; `consolidar` tira `busca_inativa` do final, da fila e de `sem_decisao` (`n_inativos_ignorados` no resumo e em `triagem_consolidada`); evento `fila_gerada` (TC, idempotente pelo sha) |
| `validacao.py` | — | `motivo_reprovacao` (`largura_ic`, `humanos`, `desempenho_ia`) no resumo e em `validacao_calculada`; `incluidos_humanos_necessarios`, `incluidos_ia_nao_sorteados`; descrição da pendência `validacao_triagem_reprovada` por motivo; `n_inativos_no_desenho` com aviso em `amostrar`, `elusao`, `estabilidade` e `calcular`; planilha e listas de IDs por `ler_tabela_humana`. Na v1.3, grava os campos do atalho da variante rápida e ganha `validar segunda-leitura` (seção 7.3) |
| `textos.py` | — | `retratacoes`: `retratados_sha` (resultados dos retratados sem `verificado_em`) e `pendencia_conferida` no evento; `conferencia_ja_feita` no resumo; pendência fechada por humano não reabre com o mesmo conjunto; `propostas_elegibilidade()` pura, usada por `elegibilidade consolidar` e `triagem fila`; leitura humana (codebook, master, `conferencia_pdfs.csv`, contatos, pares, `--ids`) por `ler_tabela_humana`. Na v1.3, `textos ligar-relatos` mescla a lista com as ligações de versão do dedup e as manuais já registradas (seção 7.3) |
| `qualidade.py` (novo) | `qualidade consolidar --ferramenta {rob2,robins_i,epoc,casp_qualitativo,jbi_transversal,mmat}`; fase 1 `--a --b [--avaliador-a --avaliador-b --codebook]`; fase 2 `--consenso [--por --ignorar-no-geral]` | entradas longo, largo ou master (CSV `,` `;` tab ou xlsx); `rob_<f>_concordancia.csv` (Po, κ, PABAK com k níveis, `sinalizado`); `rob_<f>_consenso.csv`; `fila_gerada` (fila `consenso_rob`, sem evento novo em reexecução idêntica) e pendência `consenso_rob` via `sincronizar_pendencia_unica`; fase 2: código 2 sem consenso/resolução humana; `rob_geral.csv` (RoB 2 e ROBINS-I pelo pior domínio, EPOC pelo pior critério com incerto = moderado, checklists pela linha geral; sobreposição humana só para agravar; `validado_humano`); evento `rob_consolidado` com `ferramenta`, `arquivo_consenso`, `arquivo_geral`, `arquivo_concordancia`, `n_resultados`, `n_desacordos`, `n_validados_humano`, `todos_validados_humano`, `rob_geral`, `regra_geral`, `resolvido_por`, `concordancia` (artefatos: consenso, `rob_geral.csv`, concordância; sem evento novo se nada mudou) |
| `efeitos_verificar.py` | — | `tipo_estatistica` `dif_prop` e `rr`; colunas extras `p0, p1, efeito_pp, se_pp` (normalização da vírgula, impressão do efeito); plausibilidade: proporção fora de (0, 1) ou em percentual, `p0 + efeito_pp/100` fora de (0, 1), `abs(efeito_pp) > 100`, `se_pp <= 0`, `p1 − p0` incoerente com `efeito_pp`, RR·p0 ≥ 1 |
| `caixa.py` | — | `REGRA_VERSAO = caixa-3`; Misto só com k ≥ 5 (e `tau2_interpretavel` diferente de false), δ, PI além de ±δ e linha de certeza de moderador ou mecanismo (`explica_heterogeneidade = sim`, mesma família, outcome da célula ou vazio, classe compatível) com enunciado e CERQual ≥ baixa; explicação alegada sem requisito → Inconclusivo (`inconclusivo_misto_nao_sustentado`); `achado_explicativo()`; coluna opcional `explica_heterogeneidade` em `certeza.csv`; linha `dimensao = efeito_painel` por família × construto (`painel_efeito()`: `painel_pendente`, `painel_corpo_unico`, `painel_mesmo_rotulo`, `painel_maior_certeza`, `painel_empate_desenho`), contada em `n_pendentes`; `rotulos_painel` no resumo e em `caixa_gerada` |
| `scripts/R/efeitos.R` | — | `formula_id` `dif_prop_contagens` (p1, p0, n1, n2, desenho que não é de regressão; exato), `dif_prop_lpm` (efeito_pp + p0 com `se_pp`, IC do efeito em pp ou desenho/modelo/estimando LPM, DiD, RDD; aproximado), `rr_logit` (RR em `or_`, IC na escala da razão, p0; OR = RR(1 − p0)/(1 − RR·p0); EP(ln OR) = EP(ln RR)/(1 − RR·p0); aproximado); d = ln(OR)·√3/π; inferência de `dif_prop` com `tipo_estatistica` vazio; linhas novas em `assets/mapas/conversoes_efeito.csv` |
| `scripts/R/meta.R` | — | `pet_peese.variante` ("WLS (Stanley & Doucouliagos 2014)"), `metodo`, `gl`, `pet_t`, `peese_t` (lm ponderado por 1/vi, EP escalado, t com k − 2 gl); regra condicional mantida |
| `scripts/R/swim.R`, `scripts/R/testes_combinados.R` | `--excluir-rob=nenhum\|critico` (e `analise swim/combinados --excluir-rob`) | mesma regra do `meta.R`: direção (SWiM) ou p por estudo (combinados) escolhidos antes da exclusão; por grupo `excluidos_rob_critico` e `sensibilidade.com_rob_critico`; no topo `parametros.excluir_rob` e `n_excluidos_rob_critico`; `swim_direcao.csv` e `testes_combinados_estudos.csv` com `excluido_rob_critico`; figuras só com a análise principal |
| `scripts/R/_cli.R` | — | `eh_rob_critico`, `OPCOES_EXCLUIR_ROB`, `cli_excluir_rob()` compartilhados |
| `analise_r.py` | repassa `--excluir-rob` para `swim` e `combinados` | — |
| `assets/codebooks/robins_i.csv`, `agentes/avaliador-rob.md` | — | códigos oficiais do ROBINS-I V2 (20/11/2025): `Y, PY, PN, N, NI`; `WN/SN` e `SY/WY` onde o documento os usa; `NA` pelo fluxo; teste garante que as propostas dos codebooks cabem no vocabulário de `qualidade consolidar` |

### 6.4 Pendências novas

| Tipo | Quem abre | Quem fecha |
|---|---|---|
| `consenso_rob` | `qualidade consolidar` fase 1 (autopiloto; `n` = desacordos sem resolução humana) | a fase 2 com tudo resolvido (qualquer modo) |
| `revisao_press` | manual (`pendencia abrir`); pedida pela `proxima_acao` no autopiloto | humano; aberta, satisfaz a checagem de PRESS do G3 |
| `concordancia_extracao` | manual | humano; fechada com o `arquivo` do `concordancia.csv`, silencia o aviso de variáveis sinalizadas do G7 |

A regra única da seção 5.4 continua valendo para as pendências abertas por comandos.

### 6.5 Testes afetados

`tests/e2e/test_fluxo_completo.py` acompanha os portões novos (feito na v1.3, seção 7.5): grava `00-protocolo/codebook_v0_oqf.csv` e `00-protocolo/codebook_elegibilidade.csv` (`dados_sinteticos.escrever_codebooks`) antes de cada `portao G2`, `01-busca/press_<string_id>.md` antes do `portao G3` e roda `qualidade consolidar` (fases 1 e 2, RoB 2 e ROBINS-I) antes do `portao G7`. O ramo de trava do Windows (`msvcrt`) não foi exercitado em Windows.

## 7. Contratos v1.3

Acréscimos compatíveis com projetos v1.2. Nenhuma CLI existente mudou de forma incompatível; os schemas JSON não foram editados (os campos novos moram em `dados`, que é objeto livre). O único valor existente alterado em `esquema.py` é `DECISOES_DEDUP`, que ganhou `ligado` no fim (o `dedup` já gravava esse valor desde a v1.2).

### 7.1 Constantes novas em `esquema.py` (bloco "Acréscimos de contrato (v1.3)")

| Constante | Valor | Quem escreve / lê |
|---|---|---|
| `DECISOES_DEDUP` (acréscimo), `DECISAO_LIGADO`, `MOTIVO_VERSAO_LIGADA` | `... , ligado`; `ligado`; `preprint_publicado` | `dedup` (aliases `dedup.DECISAO_LIGADO`, `DECISOES_PARES`, `MOTIVO_VERSAO_LIGADA`) |
| `MARCA_RESOLVIDO_TRANSITIVAMENTE` | `resolvido_transitivamente` (sufixo em `dedup_pares.motivo`) | `dedup` grava; `dedup.contar_candidatos_pendentes` e `candidatos_pendentes` leem |
| `COLUNAS_FILA_HUMANA_TC`, `ARQ_CODEBOOK_ELEGIBILIDADE` | colunas da fila do texto completo; `00-protocolo/codebook_elegibilidade.csv` | `triagem fila`, `triagem override` (aliases em `triagem_lotes`) |
| `PENDENCIA_PRESS`, `PENDENCIA_CONCORDANCIA`, `PENDENCIA_CONSENSO_ROB` | `revisao_press`, `concordancia_extracao`, `consenso_rob` | `projeto.py`, `qualidade.py` (nomes antigos como aliases lidos de `esquema.py`) |
| `PADRAO_CONCORDANCIA_ROB` (alias `PADRAO_CONCORDANCIA`) | `04-qualidade/rob_{ferramenta}_concordancia.csv` | `qualidade consolidar` |
| `TIPOS_SEM_CERTEZA`, `MIN_INCLUIDOS_LIMIAR_ALCANCAVEL` | `escopo, mapa_evidencias, realista`; `36` | G8 e `proxima_acao` do G4 (`projeto.py`) |
| `CRITERIO_ATALHO_RAPIDA`, `FRACAO_MINIMA_DUPLA_RAPIDA`, `CAMPOS_ATALHO_RAPIDA` | `atalho_rapida`; `0.20`; `atalho_rapida, fracao_dupla_humana, n_dupla_humana, n_populacao, kappa_humanos, segunda_leitura_excluidos, n_excluidos_ia, n_excluidos_relidos` | `validar calcular` grava em `validacao_calculada.dados`; G4 lê |
| `ARQ_SEGUNDA_LEITURA`, `TIPO_SEGUNDA_LEITURA` | `segunda_leitura.json` (em `02-triagem/validacao/<rodada>/`); `segunda_leitura` | `validar segunda-leitura` grava; `validar calcular` lê |
| `COLUNAS_EFEITOS_BINARIOS` | `p0, p1, efeito_pp, se_pp` (fora de `COLUNAS_EFEITOS_EXTRAS_NUMERICAS`, que não mudou) | `efeitos_verificar` (alias), `efeitos.R` |
| `DIMENSAO_PAINEL`, `REGRA_VERSAO_CAIXA` | `efeito_painel`, `caixa-3` | `caixa.py` (cópias locais `DIMENSAO_PAINEL`, `REGRA_VERSAO`) |
| `CAMPO_ULTIMO_SEQ_RELATORIO` | `ultimo_seq` | `relatorio_gerado.dados` (declaração de IA), G9 |

### 7.2 Leitor único de planilhas humanas: `scripts/rslib/planilhas.py` (novo)

- `ler_tabela_humana(caminho, obrigatorias=(), alternativas=None, aba=None, rotulo=None) -> (colunas, linhas, info)`: xlsx/xlsm (openpyxl) ou texto com `,`, `;` ou tab (pelo cabeçalho; desempate por `csv.Sniffer`), UTF-8 com ou sem BOM, UTF-16 com BOM ou sem BOM (bytes nulos alternados), cp1252 (com aviso em `info["avisos"]`); `.xls` recusado. `info`: `formato`, `delimitador`, `codificacao`, `numeros` (linha de cada registro), `avisos`.
- `ler_meta_xlsx(caminho, aba="_meta")`, `ler_texto_humano(caminho) -> (texto, codificacao, avisos)`, `decodificar(bytes)`, `aviso_codificacao`, `celula_texto`, `limpar_coluna`.
- Exceções `ErroUso` (código 1) e `ErroDependencia(ErroUso)` (openpyxl ausente, código 3). `triagem_lotes.ErroUso`, `triagem_lotes.ErroDependencia` e `triagem_lotes.ler_tabela_humana` são os mesmos objetos (aliases), então `textos.py` e `validacao.py` seguem iguais.
- Usuários: `triagem override --fila`, `triagem consolidar` e `triagem fila` (fila existente), `--ids`/`--excluir-ids`, arquivo de critérios (`preparar`, `override --criterios`), `validar calcular` e `validar segunda-leitura`, `filtrar --calcular-elusao` (planilha e aba `_meta`) e `filtrar --ancoras`, e as leituras humanas de `textos`.

### 7.3 Flags, artefatos e eventos por módulo

| Módulo | Flags / subcomandos | Artefatos, resumos e eventos |
|---|---|---|
| `triagem_lotes.py` | — | `escrever_csv` compara bytes (a fila anterior pode estar em cp1252/UTF-16) e `consolidar` só grava o final e a fila depois de ler e conferir tudo; `proxima_acao_rodada(raiz, rodada, revisor)` e, no resumo do `mesclar`, `proxima_acao` (comando) e `proxima_acao_detalhe` (`texto`, `comando`, `alternativa`, `lotes_pendentes`, `n_divergentes_sem_arbitro`) na ordem do `status`: lotes pendentes → `mesclar`; divergências com IA sem árbitro → `preparar --revisor arbitro --apenas-divergentes` (alternativa `--regra liberal`); senão `consolidar`; `ids_criterios` usa primeiro os `C<n>` que abrem linhas (cabeçalhos, itens, células), depois `C<n>` em qualquer lugar e, por fim, outras letras em início de linha; critérios em cp1252 aceitos com aviso (sha do arquivo) |
| `validacao.py` | `amostrar --atalho-rapida` (finalidade validacao, `--codificadores` ≥ 2; grava `atalho_rapida` no desenho e em `parametros`); `calcular --atalho-rapida`; `segunda-leitura --planilha P [--planilha P2] [--rodada R] [--etapa ta] [--regra consenso]` | com `projeto.variante = rapida` e desenho (ou flag) do atalho, `validacao_calculada.dados` traz `CAMPOS_ATALHO_RAPIDA` e `atalho_rapida_atende`; `metricas.atalho_rapida` com `criterios`, `ids_faltam_reler`, `n_relidos_na_amostra`, `ids_relidos_na_amostra`, `segunda_leitura` e sha; código 2 e `validacao_triagem_reprovada` enquanto faltar dupla ≥ 20%, κ ou a releitura (recall não é exigido nesse caminho); `motivo_reprovacao` segue no evento. `segunda-leitura`: `02-triagem/validacao/<rodada>/segunda_leitura.json` (leituras acumulam; `ids_relidos` são os das planilhas), `segunda_leitura_resgatados.csv` (colunas da fila T/A, `motivo_fila = segunda_leitura`, para `triagem override --fila --rodada`), evento `validacao_calculada` com `tipo = segunda_leitura`, `finalidade = elusao`, sem `atende_limiares` nem `atalho_rapida` (nunca decide o G4); excluídos = decisão só IA da rodada fora inativos e funil; os já codificados na amostra do último atalho contam como relidos |
| `filtrar.py` | — | âncoras e planilha de elusão por `planilhas.py` (xlsx ou CSV em qualquer delimitador/codificação); `indexada_em` com id de busca substituída segue `substituida_por` até a busca ativa, com aviso sugerindo o nome da base; openpyxl ausente = código 3 |
| `dedup.py` | — | aviso por cluster novo equivalente a cluster inativo só se o id inativo tem decisão de triagem (`ids_com_decisao_de_triagem`); os demais num aviso agregado; `candidatos_resolvidos_transitivamente` no resumo e em `dedup_executado`; `candidatos_pendentes(pares)` e `contar_candidatos_pendentes(raiz)` (a contagem da pendência `dedup_candidatos`; contar só `decisao == candidato` inclui os resolvidos) |
| `efeitos_verificar.py` | — | `projeto_parcial_sem_pdfs(raiz)` (etapa 09 ignorada em projeto parcial, sem PDF em `03-textos/pdfs` nem em `relatorio_pdfs.csv`) e `aviso_sem_pdfs(linhas)`; nesse caso `preparar-efeitos` devolve `proximo_passo: rs.py analise efeitos`, `sem_pdfs`, `n_nao_verificados_humano` e `avisos` (também em `extracao_consolidada`) |
| `analise_r.py` | — | em `analise efeitos`, no projeto parcial sem PDFs, o aviso diz que os números não foram verificados contra os PDFs (declarar no relato) em vez de mandar rodar `verificar-efeitos` |
| `importar/cli.py`, `importar/flags.py` | — | `registros.csv` e `registros_flags.csv` por `estado.escrever_atomico` (0666 menos a umask) |
| `handoff.py` | — | `escrever_csv` e `escrever_texto` por `estado.escrever_atomico` (0666 menos a umask; conteúdo e quebras de linha iguais): valem para todos os módulos que os importam (`textos`, `qualidade`, `caixa`, `efeitos_verificar`...) |
| `textos.py` | `ligar-relatos --substituir-manuais` | a lista de `--pares` é acréscimo: `pares_para_ligar(raiz, recebidos, substituir_manuais)` aplica versões do dedup (`dedup.pares_versao_ligados`, sempre) ∪ manuais já registradas (`dedup.pares_preservados` com o último `dedup_executado`; saem com `--substituir-manuais`) ∪ recebidas; `textos.ligar_relatos(raiz, pares)` continua reconstruindo com a lista que recebe (o `dedup` o chama com a lista completa); resumo e evento `ligacao_relatos` com `modo` (`acrescimo`\|`substituir_manuais`), `n_pares_recebidos`, `n_pares_versao_dedup`, `n_pares_manuais_mantidos`, `n_pares_manuais_descartados`, `pares_manuais_descartados`, `origem_manuais`, `n_pares_aplicados`; id inexistente na lista: código 1 antes de gravar |
| `qualidade.py` | — | `PENDENCIA_CONSENSO_ROB` e `PADRAO_CONCORDANCIA` lidos de `esquema.py` (aliases) |
| `projeto.py` (G7) | — | `checar_rob` por ferramenta (`ultimos_rob_por_ferramenta(eventos)`; eventos antigos sem `dados.ferramenta` na chave `None`): artefato sem `rob_consolidado`, com `fila_gerada` (fila `consenso_rob`) de ferramenta sem fase 2, com ferramenta de `resultados_avaliados.csv` sem consolidação, com arquivo citado alterado (o `rob_geral.csv` pelo último evento que o gravou; para as demais ferramentas, `n_resultados`, a distribuição `rob_geral` e `n_validados_humano` do evento contra as linhas delas) e com resultado sem `rob_geral` (`resultados_exigidos_rob(raiz)`: `04-qualidade/resultados_avaliados.csv` por chave × construto × ferramenta, com `construto_outcome` vazio casando com qualquer outcome da chave; sem ele, chave × construto de `efeitos_extraidos.csv`); validacao sem `todos_validados_humano = true`. Bloqueios trazem `comando` (fase 1 ou 2), usado pela `proxima_acao` da etapa 09 (no autopiloto, só os duros viram tarefa) |
| `projeto.py` (G4, G8) | — | G4: validação reprovada com `atalho_rapida` aprovado no G1 e sem os campos do atalho → aviso e `proxima_acao` `validar calcular --planilha <p> --atalho-rapida` (alternativa `--forcar` humano); atalho com campos incompletos → `validar segunda-leitura` ou `validar amostrar --atalho-rapida`. G8: com a etapa 09 ignorada, `avisos_efeitos_nao_verificados` (`resumo_r.n_nao_verificados_humano` do último `analise_executada` do `efeitos.R`; sem ele, linhas calculadas de `06-analise/efeitos.csv` sem `verificado_humano`) |
| `projeto.py` (`status`, `proxima_acao`) | — | `com_dir(valor, dir)` põe `--dir "<dir>"` em todo `$RS ...` de `proxima_acao`, `inconsistencias` e `alertas` quando o `status` recebeu `--dir`; sem projeto, `projetos` (`resumo_subprojeto`: `dir`, `titulo`, `tipo_revisao`, `etapa_atual`, `ultimo_evento_em`, `ultimo_evento`, `n_pendencias_abertas`, ou `erro`), do mais recente ao mais antigo, `proxima_acao` com o mais recente e `exige_humano` com mais de um (`projetos_em_subpastas` continua a lista ordenada de nomes); busca truncada: `comando_refazer_busca(busca)` (`buscar openalex --busca-id <novo busca_id> --query ... [--campo --filtro --string-id] --substituir <antiga> --motivo ...` para busca da API, `_busca_da_api_openalex`: fonte `openalex` com `query` ou JSONL `*_openalex.jsonl`; `importar --substituir` nas demais), também em `alertas[].comando` e `proxima_acao.buscas_truncadas`; `dedup --revisar ... --por revisor_humano_1` com `exige_humano`; `_candidatos_dedup_pendentes` usa `dedup.contar_candidatos_pendentes`; autopiloto: `tarefa` com pendência aberta da etapa ou do portão ganha `exige_humano`, `pendencia`, `alternativa` ("seguir sem esperar...") e `acao_seguinte` (`filtrar` na etapa 05 sem funil; senão a ação da próxima etapa não concluída que não seja tarefa humana com pendência; nenhuma quando o portão da etapa atual tem bloqueio `artefato` ou `limiar`); a `alternativa` de `--nao-se-aplica` vai para `alternativas` quando já há uma; todas as etapas concluídas sem pendência, mas com `motivos_rascunho` ou G8 aprovado com `--forcar` e bloqueio vigente (`_portoes_forcados_vigentes`) → `tarefa` na etapa seguinte à última aprovada, com `rascunho`, `motivos_rascunho`, `portoes_forcados`, `exige_humano` e o comando do que falta (`caixa --master <master>` ou o de refazer a busca), em vez de `fim`; G4 reprovado: `_acao_validacao_reprovada` por `motivo_reprovacao` (`largura_ic` → `validar amostrar ... --enriquecer-incluidos` com alternativa `validar elusao`, ou remédio 5 quando `validacao.plano_reprovacao` sobre o `*_metricas.json` do evento dá `incluidos_ia_nao_sorteados` < necessários; `humanos` → consenso; demais → falsos negativos e vN+1; evento sem o campo com < 36 incluídos e 0 falsos negativos → remédio 5) |
| `assets/templates/ancoras.csv` | — | `indexada_em` de exemplo com nomes de base (`openalex\|scopus\|wos`) |

### 7.4 Pendente para os donos de outros módulos

- `triagem_api.extrair_ids_criterios` mantém a regra antiga (C<n> em qualquer lugar): num arquivo com menções como "ver C5" antes dos cabeçalhos, os modos API e subagentes dão listas diferentes; delegar a `triagem_lotes.ids_criterios`.
- `caixa.py` pode trocar as cópias locais pelas constantes de 7.1 (`projeto.py` e `qualidade.py` já leem de `esquema.py`).
- `ARQ_RESULTADOS_AVALIADOS = "04-qualidade/resultados_avaliados.csv"` continua local em `projeto.py` (lido de `esquema.py` se for promovido).

### 7.5 Testes ponta a ponta

`tests/e2e/test_fluxo_completo.py` tem três cenários, todos pelo dispatcher real: checkpoints (G2 sem codebooks bloqueado; G3 sem PRESS bloqueado; `status --dir` com `--dir` nos comandos; `ligar-relatos` sem o par de versão mantém a ligação do dedup; G7 sem `rob_consolidado` bloqueado, RoB 2 e ROBINS-I em dupla com desacordo resolvido por humano e G7 bloqueado até consolidar as duas ferramentas); autopiloto (busca do OpenAlex falsa que devolve menos obras que a contagem, G3 bloqueado por truncada e PRESS, a busca refeita pelo comando exato da `proxima_acao`, PRESS como pendência); e variante rápida (`amostrar --atalho-rapida` em 20% da rodada, G4 bloqueado sem a segunda leitura, `validar elusao` + `validar segunda-leitura`, G4 aprovado sem `--forcar` com aviso do atalho). `dados_sinteticos.py` ganhou `CODEBOOK_V0`, `PRESS`, `ROB`, `escrever_codebooks` e `avaliacao_rob`.

## 8. Contratos v1.4

Acréscimos compatíveis com projetos v1.3. Nenhuma CLI mudou de forma incompatível, nenhum schema JSON foi editado (os campos novos moram em `dados`) e `esquema.py` não mudou: as invariantes novas do PRISMA são nomes em `projeto.INVARIANTE_ETAPA`, e as constantes novas ficam nos módulos.

### 8.1 Ids absorvidos por dedup depois da triagem

| Módulo | Flags / subcomandos | Artefatos, resumos e eventos |
|---|---|---|
| `dedup.py` | — | `mapa_absorvidos(raiz, ids_vigentes=None)` → {id aposentado: id que absorveu hoje, cadeia seguida; "" se o destino não está em `ids_vigentes`}, somando `ids_rs_aposentados` de todos os `dedup_executado`; `chaves_absorvidas(raiz, ids_vigentes=None)` → {chave aposentada: id destino}. `dedup_executado` e o resumo ganham `n_absorvidos` e `n_absorvidos_com_triagem`; com absorvidos já triados, aviso com a ordem de reexecução (`filtrar`, `triagem consolidar`, `textos elegibilidade consolidar`, `prisma`) |
| `triagem_lotes.py` | — | `ORDEM_INCLUSIVA` e `fundir_absorvidos(final, mapa)` (pura; devolve `(final, relatos)`), chamada em `consolidar` antes das remoções de funil e inativos: override > IA, depois incluir > incerto > excluir; empate fica o destino; destino sem decisão herda; destino vazio, a decisão cai. `triagem_consolidada` ganha `n_absorvidos_dedup` e `absorvidos_dedup` (até 200 relatos `{absorvido, destino, decisao_absorvido, decisao_destino, resultado}`, resultado `herdada\|mantida\|substituida\|descartada`); o resumo, `n_absorvidos_dedup`; aviso com as divergências |
| `textos.py` | — | `propostas_elegibilidade`: ficha de chave absorvida passa ao registro que absorveu (regra existente: um incluir basta, senão incerto), com aviso; `consolidar_elegibilidade`: decisão humana de id absorvido vai ao destino, salvo se ele tiver decisão humana própria (que prevalece), com aviso |
| `prisma.py` | — | ids absorvidos ainda nos arquivos finais: linhas de filtro ignoradas com aviso ("rode `filtrar`"); falhas novas `triagem_ids_absorvidos` e `elegibilidade_ids_absorvidos` (com exemplos `RSxxxx→RSyyyy` e o comando), no lugar de `triagem_ids_desconhecidos`, `filtro_ids_desconhecidos` e `elegibilidade_fora_dos_buscados` para esses ids |
| `projeto.py` | — | `INVARIANTE_ETAPA` ganha `triagem_ids_absorvidos` (06) e `elegibilidade_ids_absorvidos` (07) |

### 8.2 Caixa de ferramentas: subcélulas

| Módulo | Flags / subcomandos | Artefatos, resumos e eventos |
|---|---|---|
| `caixa.py` | — | `REGRA_AGREGACAO = subcelulas-1` (`REGRA_VERSAO` segue `caixa-3`); `COLUNAS_CERTEZA` (contrato de `certeza.csv`); `colunas_de_subcelula()` e `agregar_subcelulas()`: linhas de efeito da mesma família × construto × classe que diferem numa coluna fora do contrato (ex.: `comparador_tipo`, `celula_alvo`) são subcélulas, cada uma avaliada pelas regras `caixa-3` e agregadas como o painel (`subcelulas_pendente`, `subcelulas_mesmo_rotulo`, `subcelulas_maior_certeza`, `subcelulas_empate`; status pendente > rascunho > definido; certeza e força da subcélula escolhida, a primeira do arquivo no empate; `estudos` = união; `fontes` = todas as `certeza.csv:linha n`; justificativa "agregação subcelulas-1 (<regra>): …" com cada subcélula); linhas sem coluna distinta (duplicatas) mantêm a última, com aviso; célula com uma linha sai idêntica; implementação com várias linhas: maior CERQual (a última no empate), rascunho se alguma não validada, todas em `fontes` e na justificativa, com aviso; `regra_agregacao` e `n_celulas_agregadas` no resumo e em `caixa_gerada` (acréscimo; `n_pendentes` e a pendência `certeza_caixa` inalterados); linha extra no cabeçalho do `.md` só quando há célula agregada |

### 8.3 Declaração de uso de IA orientada a dados

- `rs.py declaracao-ia`: gera `07-relatorio/declaracao_uso_ia.md` a partir do log (modelos, datas, papéis por etapa, prompts com hash, validação com métricas e limiares, elusão, pendências com a descrição da abertura e notas sobre as citadas já fechadas, declaração de responsabilidade montada dos dados e marca de rascunho).

| Módulo | Flags / subcomandos | Artefatos, resumos e eventos |
|---|---|---|
| `declaracao_ia.py` | — | `coletar` devolve também `aberturas` (primeiro `pendencia_aberta` por id), `fechamentos` (último `pendencia_fechada`), `sucessoras` (`sucessoras_de_pendencias`: "[substitui Pxxx]" no fim da descrição da nova ou "substituída por Pxxx" no motivo do fechamento da antiga; só entre pendências do mesmo `tipo`; a primeira ligação no log vale), `decisoes_portao` (última `portao`/`etapa_nao_aplicavel` por portão), `rob` (último `rob_consolidado` por ferramenta), `ultimos` (`efeitos_verificados`, `caixa_gerada`) e `certeza` (`ler_certezas`: `certeza*.csv` da pasta de `ARQ_CERTEZA`, sem subpastas; linhas sem `sim(validado_humano)`; arquivo sem a coluna segue `caixa._validado` e não marca rascunho). Seção 6: frase de abertura; colunas `Id \| Tipo \| Etapa \| Portão \| Aberta em \| Descrição (como registrada na abertura) \| N`; `Aberta em` = `aaaa-mm-dd (seq n)`; nota `[Pxxx: fechada em d (seq n); substituída por A → B, fechada em d \| aberta]` para cada citada fechada (pula a própria, as abertas e a citada cuja cadeia chega à pendência). Seção 7: sem pendência aberta, portão sem confirmação, marca `validado_humano`/`todos_validados_humano` faltando, caixa pendente, efeito não apto nem problema de validação da triagem, sai o texto anterior byte a byte; senão, abertura com a exceção, lista (efeitos com `n_nao_aptos > 0`, RoB por ferramenta, certeza por arquivo com sha256, caixa com `n_pendentes > 0`, portões aprovados por não humano com `revisao_humana_portao` aberta ou sem fechamento humano posterior, validação da triagem, demais pendências abertas por etapa com `ROTULO_ETAPA`), portões confirmados depois por humano, validações humanas completas e a frase final. Motivo de rascunho novo "juízos de IA sem validação humana (seção 7)", que também torna `rascunho` verdadeiro no resumo e no evento; `relatorio_gerado.artefatos` inclui os `certeza*.csv`. A frase "até o evento seq N" (lida por `projeto._RE_SEQ_DECLARACAO`) não mudou. |
