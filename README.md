# Systematic-Review

Skills do [Claude Code](https://claude.com/claude-code) para revisões sistemáticas e um livro que sistematiza protocolos metodológicos para conduzi-las e avaliá-las, com foco em avaliação de políticas públicas.

Estas anotações são inspiradas em tudo o que o professor Bruno Marques Schaefer disponibilizou no curso de revisão sistemática para políticas públicas, por iniciativa do MAPE (Laboratório de Monitoramento e Avaliação de Políticas e Eleições do IESP-UERJ), em especial a proposta metodológica *O que funciona?* (Schaefer, Borges e Freitas, 2025). Sobre essa base, o livro incorpora as normas internacionais de síntese de evidências (Cochrane, Campbell, JBI, PRISMA, GRADE, GRADE-CERQual, RAISE).

Livro publicado: <https://felipelamarca.com/Systematic-Review/>

## Estrutura

```
livro/                     livro Quarto "Revisão sistemática de ponta a ponta"
  metodo/                  12 capítulos (tipos de revisão → IA na revisão) e apêndices A–D
  _notas-leitura/          notas de leitura rastreáveis e guia de escrita (não publicadas)
  references.bib           bibliografia única
skills/                    cópia versionada das skills (espelho de ~/.claude/skills)
  revisao-sistematica/     conduz uma revisão de ponta a ponta com estado auditável e portões humanos
  baixar-pdfs-academicos/  textos completos por fontes legítimas em cascata
  fichamento-sistematico/  extração em lote dirigida por codebook, com gate de citação e concordância
  gerar-bibtex/            .bib a partir de planilhas de papers
dev/revisao-sistematica/   testes (pytest e testthat), evals e contratos de desenvolvimento da skill principal
```

## Uso

**Livro.** `cd livro && quarto preview` (ou `quarto render`). O CI renderiza e publica no GitHub Pages a cada push na `main`.

**Skills.** Ficam instaladas como cópias em `~/.claude/skills/<nome>`. Para instalar ou atualizar uma skill a partir deste repositório:

```bash
rsync -a --delete --exclude __pycache__ --exclude .DS_Store skills/<nome>/ ~/.claude/skills/<nome>/
```

Toda modificação numa skill deve ser feita nos dois lugares (aqui e em `~/.claude/skills`). O teste `dev/revisao-sistematica/tests/test_sincronia_instalacao.py` acusa divergências.

Dependências da `revisao-sistematica`: `python3 -m pip install -r skills/revisao-sistematica/scripts/requirements.txt` (opcionais em `requirements-opcional.txt`); para a síntese quantitativa, `Rscript -e 'install.packages(c("meta","metafor","esc","irr","clubSandwich","robvis","jsonlite"))'`.

**Testes** (a partir da raiz):

```bash
python3 -m pytest -q dev/revisao-sistematica/tests
Rscript -e 'testthat::test_dir("dev/revisao-sistematica/tests/R")'
```

Detalhes da skill principal em `dev/revisao-sistematica/README.md` e `dev/revisao-sistematica/CONTRATOS.md`.

## Licenças

Código sob MIT (`LICENSE`). Textos, prompts de agentes, modelos, codebooks e checklists da skill sob CC BY 4.0 (`skills/revisao-sistematica/LICENSE.txt`, `dev/revisao-sistematica/LICENSE-CONTENT`).
