# revisao-sistematica

Skill do [Claude Code](https://claude.com/claude-code) que conduz revisões sistemáticas de ponta a ponta: pergunta e teoria do programa, protocolo, busca, deduplicação, triagem com validação humana, textos completos, risco de viés, extração, meta-análise ou síntese sem meta-análise, síntese qualitativa, certeza da evidência, caixa de ferramentas no formato OQF e relato PRISMA.

*English summary: a Claude Code skill for end-to-end systematic reviews with an auditable, resumable project state, human gates aligned with RAISE and PRISMA-trAIce, Python tooling for search, deduplication and screening, and R (metafor/meta) for meta-analysis and SWiM. Instructions are in Brazilian Portuguese; it also triggers on English requests.*

## O que ela faz

- Mantém cada revisão num projeto em disco com `rs_estado.json` (cache) e `rs_log.jsonl` (log append-only). Qualquer sessão retoma de onde parou com `rs.py status`.
- Importa exportações de Web of Science, Scopus, OpenAlex (CSV e API), SciELO, Publish or Perish/Google Scholar, Zotero, RIS, Catálogo de Teses da CAPES e BDTD num esquema único, e deduplica com auditoria de cada par (DOI, id da fonte, título exato, fuzzy, preprint e versão publicada).
- Aplica o funil formal etiquetando os registros em vez de excluí-los. Exclusão só acontece se o protocolo previr, com amostra de elusão.
- Faz a triagem de títulos e resumos com subagentes do Claude Code (padrão) ou via API (dois modelos e um árbitro cego). A decisão da IA é validada contra humanos (sensibilidade com IC, κ, PABAK, elusão) antes de ser usada em escala.
- Integra-se com as skills irmãs para PDFs (`baixar-pdfs-academicos`), extração ancorada em citações verbatim (`fichamento-sistematico`) e referências (`gerar-bibtex`).
- Calcula tamanhos de efeito com fórmula e pressupostos declarados. Roda meta-análise de efeitos aleatórios (REML + Hartung-Knapp, intervalo de predição, dependência com CHE + RVE) ou SWiM (teste de sinal por direção). Os testes combinados só aparecem como análise secundária, com ressalva.
- Monta a caixa de ferramentas do formato OQF (efeito, força, mecanismo, moderador, implementação, percepção, custo) com regras de rótulo explícitas e as fontes de cada célula.
- Gera o fluxograma PRISMA 2020 e o checklist a partir dos dados, com invariantes que impedem números que não fecham, e a declaração de uso de IA a partir do log.

## Portões de decisão

| Portão | Etapa | No modo checkpoints | No autopiloto |
|---|---|---|---|
| G1 | pergunta e tipo de revisão | humano aprova | humano aprova |
| G2 | protocolo congelado | humano aprova | humano aprova |
| G3 | estratégia de busca (PRESS, estudos-âncora) | humano aprova | critérios automáticos + pendência |
| G4 | validação da triagem por IA | humano aprova | critérios automáticos + pendência |
| G5 | lista final de incluídos | humano aprova | pendência |
| G6 | piloto de extração | humano aprova | pendência |
| G7 | dados de efeito verificados e risco de viés consolidado em dupla | humano aprova | pendência |
| G8 | síntese, certeza e rótulos | humano aprova | pendência |
| G9 | relatório e declaração de IA | humano aprova | pendência |

No autopiloto, relatório, PRISMA, caixa de ferramentas e declaração de IA saem marcados como **RASCUNHO NÃO VALIDADO** enquanto houver pendências abertas.

Os portões também conferem artefatos: o G2 exige protocolo, codebook v0 e codebook de elegibilidade sem placeholders; o G3, PRESS registrado e nenhuma busca truncada; o G4, a validação da rodada ativa; o G7, efeitos verificados e o risco de viés consolidado; o G8, os juízos de certeza de cada célula; o G9, PRISMA atual e declaração de IA.

## Instalação

Na raiz do repositório, as skills ficam em `skills/<nome>`; a instalação é uma cópia para `~/.claude/skills/<nome>`, não um link simbólico:

```bash
git clone URL_DO_REPOSITORIO ~/Systematic-Review
cd ~/Systematic-Review
mkdir -p ~/.claude/skills
rsync -a --delete --exclude __pycache__ --exclude .DS_Store skills/revisao-sistematica/ ~/.claude/skills/revisao-sistematica/
python3 -m pip install -r skills/revisao-sistematica/scripts/requirements.txt
python3 -m pip install -r skills/revisao-sistematica/scripts/requirements-opcional.txt  # opcional
Rscript -e 'install.packages(c("meta","metafor","esc","irr","clubSandwich","robvis","jsonlite"))'  # opcional, síntese quantitativa
```

As duas cópias são independentes: `skills/revisao-sistematica` é a versionada e `~/.claude/skills/revisao-sistematica` é a que o Claude Code carrega. Toda modificação vale para os dois lugares: edite em `skills/`, repita o `rsync` e rode `python3 -m pytest -q dev/revisao-sistematica/tests/test_sincronia_instalacao.py`, que compara as cópias arquivo a arquivo e falha se a instalada for link simbólico. Para instalar só num projeto, copie para `.claude/skills/` dentro dele. A pasta da skill não depende de nada fora dela (testes, evals e documentação de desenvolvimento ficam em `dev/revisao-sistematica/`). Se o `pip` recusar a instalação por ser um Python gerenciado pelo sistema (PEP 668), crie um ambiente virtual e rode os comandos com o `python3` dele.

Requisitos: Python 3.10 ou superior. R 4.2 ou superior (com metafor recente) é opcional e só é necessário para a síntese quantitativa. Quarto é opcional, para renderizar o relatório. `python3 ~/.claude/skills/revisao-sistematica/scripts/rs.py ambiente` mostra o que falta e como a skill degrada.

As skills irmãs (`baixar-pdfs-academicos`, `fichamento-sistematico`, `gerar-bibtex`, `tirar-cara-de-ia`) ficam em `skills/<nome>` neste repositório, são instaladas da mesma forma (cópia para `~/.claude/skills/<nome>`) e são opcionais. Sem elas, a skill usa fallbacks mais simples, descritos nas referências de cada etapa, e `rs.py ambiente` lista as ausentes.

## Uso

No Claude Code, basta pedir: "quero fazer uma revisão sistemática sobre ...", "continuar minha revisão", "só a triagem desta planilha", "rodar a meta-análise destes efeitos". A skill decide a etapa pelo `status` do projeto.

Os scripts também funcionam direto no terminal, a partir da pasta da revisão (nunca de dentro do repositório da skill). Uma função funciona no bash e no zsh; uma variável `RS="python3 ..."` seguida de `$RS status` falha no zsh. Nas referências e na `proxima_acao` do `status`, `$RS` é só abreviação desse comando:

```bash
rs() { python3 ~/.claude/skills/revisao-sistematica/scripts/rs.py "$@"; }
mkdir -p ~/revisoes/celulares && cd ~/revisoes/celulares
rs init --titulo "Proibição de celulares e desempenho escolar" --tipo oqf_mista_sequencial
rs importar --arquivo ~/Downloads/savedrecs.txt --busca-id B01 --executada-em 2026-09-01
rs importar --arquivo ~/Downloads/scopus.csv --busca-id B02 --executada-em 2026-09-01
rs dedup
cp ~/.claude/skills/revisao-sistematica/assets/templates/filtros_v1.json 01-busca/filtros_v1.json   # ajuste ao protocolo
rs filtrar --config 01-busca/filtros_v1.json --ancoras 00-protocolo/ancoras_validacao.csv
rs triagem preparar --rodada ta_v1 --revisor A --criterios 02-triagem/prompts/ta_v1.md             # critérios C1, C2... escritos antes
rs status
```

Veja `rs --help` e `rs <comando> --help`. Projeto numa subpasta: `rs --dir "<subpasta>" status` (sem projeto na pasta atual, o `status` lista os que achar em subpastas).

## Estrutura de um projeto

```
00-protocolo/        pergunta, teoria do programa, protocolo congelado, emendas
01-busca/            strings, exportações brutas, log de buscas, pares da deduplicação, bola de neve
02-triagem/          critérios versionados, lotes, validação, filas humanas, decisões consolidadas
03-textos/           PDFs, verificação de conteúdo, elegibilidade, ligação de relatos
04-qualidade/        risco de viés: avaliações A e B, consenso por domínio, concordância, rob_geral.csv
05-decomposicao/     codebook, fichas, efeitos extraídos e verificados
06-analise/          efeitos calculados, meta-análise/SWiM, certeza, caixa de ferramentas, figuras
07-relatorio/        PRISMA, checklists, declaração de IA, incluídos, referências, relatório
dados/               registros importados, registros únicos, decisões (JSONL)
rs_estado.json       estado (cache)
rs_log.jsonl         log de eventos append-only
```

## Novidades da versão 1.2

- **Estado seguro com comandos em paralelo.** Todo escritor de estado e log usa uma trava entre processos (`.rs.lock`), com `seq` único e mescla das mudanças; estado corrompido sai com código 1 e a dica de restaurar do controle de versão.
- **Retomada mais segura.** `status` acha projetos em subpastas e sugere `--dir`; `init` recusa criar projeto por cima de outro; a `proxima_acao` usa placeholders `<...>` onde há valor a conferir, em vez de números inventados.
- **Portões mais exigentes.** G2 (codebooks e placeholders), G3 (PRESS e busca truncada), G7 (risco de viés consolidado), G8 (certeza por célula e caixa obrigatória em OQF) e G9 (declaração de IA conferida pelo evento). Busca truncada marca o PRISMA como rascunho.
- **Risco de viés em dupla.** `qualidade consolidar` calcula a concordância de A e B por domínio (κ e PABAK), gera a fila de desacordos, valida o consenso humano e grava `rob_geral` pelo algoritmo de cada ferramenta (RoB 2, ROBINS-I V2 com os códigos oficiais, EPOC, CASP, JBI, MMAT).
- **Planilhas humanas do Excel.** Filas, listas de IDs e planilhas de validação aceitam ponto e vírgula, tabulação, UTF-16, cp1252 e `.xlsx`; a fila humana nunca é regravada com decisões ainda não aplicadas; exclusão humana exige critério válido.
- **Texto completo.** `triagem fila --etapa tc` gera a fila humana da elegibilidade; retratações conferidas por humano não reabrem a pendência.
- **Deduplicação.** Preprint ou working paper e versão publicada viram relatos ligados do mesmo estudo, sem fusão; `dedup --revisar` exige quem decidiu.
- **Busca.** `buscar openalex --substituir`; `--n-base` conferido com o total da API do OpenAlex.
- **Validação em revisões pequenas.** `validar calcular` distingue reprovação por IC largo (amostra maior ou dupla humana) de falha da IA.
- **Síntese.** Desfechos binários (proporções, efeitos em pontos percentuais de LPM, DiD ou RDD, razão de riscos) convertidos a g pelo log OR; `--excluir-rob critico` também no SWiM e nos testes combinados; PET-PEESE na variante WLS documentada; caixa de ferramentas `caixa-3` (Misto só com k ≥ 5, δ e achado explicativo com confiança própria) com linha de painel por família × construto.
- **Variante rápida.** O G4 tem caminho próprio para a triagem com dupla humana parcial quando o atalho é aprovado no G1.

Os contratos de dados desta versão estão em `dev/revisao-sistematica/CONTRATOS.md`, seção 6.

## Privacidade e custos

- O modo de triagem via API envia títulos e resumos a provedores externos (Anthropic, OpenAI). Use-o só com consentimento. `triagem api --estimar` mostra custo e tempo sem fazer chamadas.
- Chaves e e-mail vêm só de variáveis de ambiente (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENALEX_API_KEY`, `RS_EMAIL`). O estado registra apenas se cada chave existe.
- A skill não contém nem aciona fontes de acesso ilegal a artigos.

## Limitações

- Revisão realista iterativa, QCA computacional, mapas de evidências interativos e overviews com matriz de sobreposição são orientados pelas referências, mas não têm comandos dedicados nesta versão.
- Web of Science e Scopus dependem de exportação manual. A skill importa os arquivos.
- As métricas de validação dependem de humanos codificarem as amostras. Sem isso, os produtos permanecem como rascunho.
- Os preços e identificadores de modelos em `provedores.py` devem ser conferidos antes de orçar um projeto real.

## Método e créditos

O método combina o Cochrane Handbook, o Campbell MECCIR, o JBI Manual, PRISMA 2020 e extensões (PRISMA-S, PRISMA-ScR, PRISMA-trAIce), SWiM, GRADE, GRADE-CERQual, RAMESES e a declaração RAISE com a proposta de avaliação de políticas públicas por revisão sistemática mista e sequencial:

> Schaefer, B. M., Borges, T. P., & Freitas, C. B. B. M. de (2025). *O que funciona? Proposta metodológica para avaliação de políticas públicas através de revisão sistemática*. OSF Preprints. https://osf.io/preprints/osf/aht4j_v1

O fluxograma e o checklist seguem o modelo PRISMA 2020 (Page et al., 2021, *BMJ* 372:n71, CC BY 4.0).

## Desenvolvimento

Rode a partir da raiz do repositório:

```bash
python3 -m pytest -q dev/revisao-sistematica/tests                    # unidade + ponta a ponta (sem rede)
Rscript -e 'testthat::test_dir("dev/revisao-sistematica/tests/R")'    # scripts R
RS_OSF_DIR=/caminho/para/arquivo python3 -m pytest -q -m osf dev/revisao-sistematica/tests   # importadores contra exportações reais (opcional)
```

`dev/revisao-sistematica/CONTRATOS.md` descreve os contratos de dados e a divisão dos módulos. `dev/revisao-sistematica/evals/` traz os pedidos de acionamento e os cenários de aceitação para testar a skill com `claude -p` (ver `dev/revisao-sistematica/evals/README.md`).

## Licenças

Código sob MIT (`LICENSE`, na raiz do repositório). Referências, prompts de agentes, modelos, codebooks, checklists e documentação sob CC BY 4.0 (`dev/revisao-sistematica/LICENSE-CONTENT`). A pasta da skill leva as duas licenças em `skills/revisao-sistematica/LICENSE.txt`, para quem a copia sozinha. Vale uma ressalva: as ferramentas de terceiros parafraseadas nos checklists e codebooks (RoB 2, CASP, MMAT e outras) seguem os termos dos seus autores, listados em `LICENSE-CONTENT` e nos READMEs de `assets/`. As dependências instaladas pelo `pip` e pelo R têm licenças próprias e não são redistribuídas aqui (por exemplo, PyMuPDF é AGPL-3.0).
