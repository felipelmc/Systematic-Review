---
name: fichamento-sistematico
description: >-
  Fichamento acadêmico em LOTE, dirigido por codebook, para revisões
  sistemáticas ou de escopo: cada variável é extraída com ancoragem verbatim
  obrigatória (citação exata + página), verificada por um gate de citação
  programático e consolidada numa planilha única (1 linha por ficha). Inclui
  recodificação cega por um segundo agente numa amostra de validação e
  concordância inter-codificador (%, kappa de Cohen e PABAK, sinalizando
  variáveis abaixo do limiar) para indicar o que precisa de arbitragem humana.
  Sem codebook no projeto, conduz uma conversa curta para rascunhá-lo. Use
  sempre que o usuário pedir para "fichar o corpus/a lista de papers da minha
  revisão", "extrair os dados dos textos incluídos", "rodar o data
  charting/data extraction da revisão sistemática/de escopo", "validar o
  fichamento com um segundo codificador", "calcular a concordância entre
  codificadores" ou "gerar o codebook da minha revisão". Codebook configurável
  por projeto e pipeline de qualidade auditável.
---

# Fichamento sistemático em lote, com validação multi-agente

Ficha o corpus inteiro de uma revisão de literatura (sistemática ou de escopo) a partir de
um codebook (existente ou a desenhar em conjunto com o usuário), com ancoragem verbatim
obrigatória, um gate de citação 100% programático, consolidação numa tabela mestre, e uma
etapa de validação por recodificação cega + concordância inter-codificador — a mesma
mecânica já testada em produção na revisão sistemática de bioeconomia/desmatamento (118
textos, 136 fichas, gate em 0 problemas, 80,6% de concordância de valores na validação).

## Como funciona

Um **coordenador** (você, o agente principal ao ser invocado) monta o codebook e os
metadados de cada texto, instancia **subagentes fichadores** via **Agent tool** — um por
PDF, em **contexto limpo**, em lotes de **no máximo 3 em paralelo** — e roda os scripts de
apoio (`scripts/`) entre as etapas. Os subagentes nunca veem fichamentos anteriores nem uns
dos outros; a única "inteligência" fica na leitura do PDF e na aplicação do codebook.

## Fluxo de trabalho

### 1. Detectar a fonte de PDFs

Procure `<projeto>/**/relatorio_pdfs.csv` (é o formato produzido pela skill
`baixar-pdfs-academicos`). Se existir: filtre linhas com `status` em
`{ok, ja_existia, scihub_ok}`, use a coluna `chave` como base do `citekey` e `arquivo` como
caminho do PDF. Diga ao usuário quantos textos estão prontos vs. pendentes e confirme esse
conjunto como escopo do fichamento antes de prosseguir.

Se não existir esse relatório, pergunte ao usuário onde estão os PDFs e como identificar
cada um (uma lista de citekeys, ou os próprios nomes de arquivo) — não assuma um formato.
Se for preciso criar citekeys a partir de autor e ano, use `gerar_chave` de
`scripts/chave.py` (o mesmo arquivo, idêntico, de `baixar-pdfs-academicos` e
`gerar-bibtex`), para que ficha, PDF e entrada do `.bib` tenham o mesmo nome:
```bash
PYTHONPATH="${CLAUDE_SKILL_DIR}/scripts" python3 -B -c "from chave import gerar_chave; print(gerar_chave('', 'Silva, João; Souza, Maria', 2020, set()))"
```

### 2. Detectar ou rascunhar o codebook

Procure um CSV no projeto com colunas `dimensao,variavel,descricao,prompt` (mais,
opcionalmente, `tipo,aplicavel_se` — ver [references/schema_codebook.md](references/schema_codebook.md)).

- **Se existir**: valide que tem as 4 colunas obrigatórias e siga.
- **Se não existir**: conduza uma conversa curta com o usuário usando
  [references/checklist_codebook_12_secoes.md](references/checklist_codebook_12_secoes.md)
  como ponto de partida — pergunte qual a pergunta de pesquisa da revisão, quais dimensões
  do checklist viram variáveis extraíveis, se o corpus tem heterogeneidade de desenho que
  realmente justifique uma variável classificadora com seções condicionais (só introduza
  esse conceito se o usuário sinalizar essa necessidade — não empurre a complexidade por
  padrão), e o `tipo` de cada variável (`categorica`/`numerica_int`/`numerica_real`/
  `textual`). Escreva o CSV resultante em algum lugar razoável do projeto (ex.
  `<projeto>/.../codebook.csv`) e confirme com o usuário antes de seguir para o fichamento.

### 3. Fichamento em lote

Para cada PDF pendente, monte o input do subagente: `citekey`, caminho do PDF, e a lista
completa de dimensões/variáveis do codebook (nome, descrição, prompt), copiada do arquivo do
projeto. Instancie **lotes de até 3 subagentes fichadores em paralelo via Agent tool**, cada
um em contexto limpo, com o prompt = conteúdo de
[references/INSTRUCOES_FICHADOR.md](references/INSTRUCOES_FICHADOR.md) + essa lista de
variáveis injetada + (se o codebook declarar uma convenção normativa própria) o parágrafo
correspondente. Cada subagente grava `fichamento_<citekey>[#<valor>].md` no diretório de
fichamentos do projeto e devolve ao coordenador só um resumo curto (caminho da(s) ficha(s),
valor do classificador se houver, offset de página, contagem de `999`/`NA_secao`,
pendências) — nunca o conteúdo integral.

### 4. Gate de citação, ficha a ficha

Depois de **cada** ficha entregue:
```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/verify_citacoes.py" \
  --ficha <caminho da ficha> --pdf <caminho do PDF>
```
Se algum status vier diferente de `OK` (exceto `PDF_TEXTO_NAO_EXTRAIVEL` — aceite essa
exceção, mas sinalize o texto para checagem visual humana depois), **reenvie o mesmo PDF a
um subagente novo** (contexto limpo) — nunca corrija a ficha no mesmo contexto que a
produziu. Ao final de cada lote, rode o gate no diretório inteiro para confirmar 0
problemas antes de seguir:
```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/verify_citacoes.py" \
  --fichas <dir fichamentos> --pdfs <dir pdfs> --out <dir>/verificacao_citacoes.csv
```

### 5. Consolidação

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/consolida.py" \
  --fichas <dir fichamentos> --codebook <codebook.csv> \
  --out-csv <dir>/fichamentos_master.csv --out-xlsx <dir>/fichamentos_master.xlsx
```

### 6. Amostragem de validação

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/amostrar_validacao.py" \
  --consolidado <dir>/fichamentos_master.csv \
  [--classificador <nome, só se o codebook usar seções condicionais>] \
  --fracao 0.25 --semente <escolha uma e reuse sempre neste projeto> \
  --out <dir>/amostra_validacao.csv
```
Reporte ao usuário quantos textos entraram na amostra (e a distribuição por estrato, se
houver classificador).

### 7. Recodificação cega (segunda leva)

Para cada `citekey` da amostra: um **subagente novo**, contexto limpo, mesmo prompt do
passo 3, **sem qualquer acesso à ficha original** (não mencione que já existe uma ficha
para este texto) — grava em `<dir fichamentos>/_validacao/fichamento_<citekey>[...].md`.
Rode o gate de citação também sobre essas fichas, com a mesma disciplina de resubmissão.

### 8. Concordância

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/concordancia.py" \
  --original <dir fichamentos> --validacao <dir fichamentos>/_validacao \
  --codebook <codebook.csv> --amostra <dir>/amostra_validacao.csv \
  --out-dir <dir>/saidas
```
Para cada variável categórica, o script reporta Cohen's κ e **PABAK** (κ ajustado para
prevalência e viés, útil quando uma categoria domina e o κ fica artificialmente baixo). Uma
variável é **sinalizada** quando a concordância de valores fica abaixo de 80% ou, se
categórica, quando nem κ nem PABAK chegam a 0,7 (limiares de validação de extração
categórica em revisões sistemáticas). Variável sinalizada pede redefinição no codebook e
recodificação, não só arbitragem caso a caso. Com menos de 10 textos na amostra, o
relatório avisa que as estimativas são instáveis.

### 9. Relatório final ao usuário

Resuma: nº de textos/fichas, resultado do gate (0 problemas ou não, quantos
`PDF_TEXTO_NAO_EXTRAIVEL`), concordância de valores vs. estrita (e de desenho, se houver
classificador), quais variáveis ficaram abaixo de 80% ou, se categóricas, com κ e PABAK
abaixo de 0,7 (já listadas em `RELATORIO_CONCORDANCIA.md`) e quais textos específicos
divergem. Apresente isso como
**pendência para arbitragem humana** — a skill nunca decide sozinha qual codificação está
certa quando os dois lados divergem.

## Referências

- [references/schema_codebook.md](references/schema_codebook.md) — as 6 colunas do
  codebook, com exemplo do caso simples e do caso com seções condicionais.
- [references/checklist_codebook_12_secoes.md](references/checklist_codebook_12_secoes.md) —
  ponto de partida para o rascunho assistido de codebook (passo 2).
- [references/INSTRUCOES_FICHADOR.md](references/INSTRUCOES_FICHADOR.md) — o prompt
  canônico injetado em cada subagente fichador (passos 3 e 7).
- [assets/codebook_exemplo_smoke.csv](assets/codebook_exemplo_smoke.csv) — codebook mínimo
  para teste ponta-a-ponta da skill.

## Limitações conhecidas

- O parser das fichas é baseado em regex e depende estritamente do formato de linha
  `- **var** — resposta: ... — evidência: "..." (p. N)` — um subagente que fugir desse
  formato quebra silenciosamente o parsing downstream (campo fica vazio, não gera erro).
  Confira o resumo que cada subagente devolve antes de seguir para o próximo lote.
- Variáveis textuais abertas (mecanismo, interpretação, descrição de processo) tendem a ter
  concordância mais baixa na validação por natureza — dois codificadores descrevendo o
  mesmo achado com palavras diferentes reduz legitimamente o Jaccard. Isso é esperado, não
  necessariamente um erro de fichamento.
- Uma fronteira de classificação difícil no classificador (quando o codebook usa seções
  condicionais) tende a ser a maior fonte de divergência entre concordância "de valores" e
  "estrita" — vale a pena, se a taxa vier baixa, revisar o critério de classificação no
  `prompt` dessa variável no codebook, não só arbitrar os casos individualmente.
