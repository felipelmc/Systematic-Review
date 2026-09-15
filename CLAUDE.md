# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A private repository (in Portuguese) that keeps **Claude Code skills for systematic reviews** and a **Quarto book that systematizes methodological protocols** for conducting and appraising systematic reviews, with a focus on public-policy evaluation. The material is inspired by what Prof. Bruno Marques Schaefer made available in his systematic-review course for public policy (MAPE/IESP-UERJ), especially the *O que funciona?* (OQF) proposal, and extended with international evidence-synthesis norms. It is not a course-notes repository anymore: do not reintroduce class notes, syllabus or "the course" framing.

Authority order when sources conflict: international norms (Cochrane, Campbell, JBI, PRISMA, GRADE, CERQual, RAISE) > this base's methodological specification (`livro/metodo/apendice-d-especificacao.qmd`) > the OQF proposal.

## Layout

```
livro/                     Quarto book (publicly published via GitHub Pages)
  _quarto.yml  index.qmd  references.bib  custom.scss
  metodo/                  chapters 01…07, 08a, 08b, 09, 10, 11 + apendice-a…d
  _notas-leitura/          reading notes + _GUIA.md (ignored by Quarto; versioned, never published)
skills/                    versioned copies of the skills (mirror of ~/.claude/skills)
  revisao-sistematica/  baixar-pdfs-academicos/  fichamento-sistematico/  gerar-bibtex/  tirar-cara-de-ia/
dev/revisao-sistematica/   tests/ (pytest + tests/R testthat + e2e), evals/, CONTRATOS.md, README.md
```

## Commands

```bash
cd livro && quarto preview                                   # live preview of the book
cd livro && quarto render                                    # full render → livro/docs/ (build output, gitignored)
python3 -m pytest -q dev/revisao-sistematica/tests           # skill tests, from the repo root (unit + e2e, no network)
python3 -m pytest -q dev/revisao-sistematica/tests/test_dedup.py   # a single test file
Rscript -e 'testthat::test_dir("dev/revisao-sistematica/tests/R")' # R reference-value tests, from the repo root
dev/revisao-sistematica/tests/e2e/rodar.sh                   # end-to-end scenarios only
```

## Skills: two copies, always change both

Skills live in two places: `skills/<name>/` (versioned here) and `~/.claude/skills/<name>/` (what Claude Code loads). They are **independent copies, not symlinks**.

**Every modification to a skill must be applied in both places.** After editing, sync and check:

```bash
rsync -a --delete --exclude __pycache__ --exclude .DS_Store skills/<name>/ ~/.claude/skills/<name>/
diff -rq --exclude=__pycache__ --exclude=.DS_Store skills/<name> ~/.claude/skills/<name>
python3 -m pytest -q dev/revisao-sistematica/tests/test_sincronia_instalacao.py
```

Other rules for the skills:
- `chave.py` (citekey algorithm) is vendored byte-identical in `skills/revisao-sistematica/scripts/rslib/`, `skills/baixar-pdfs-academicos/scripts/`, `skills/gerar-bibtex/scripts/` and `skills/fichamento-sistematico/scripts/`; `test_chave_sync.py` compares the hashes. Edit all four copies together.
- `skills/revisao-sistematica/scripts/rslib/esquema.py` is the single source of column names, paths, enums and events; `dev/revisao-sistematica/CONTRATOS.md` documents the module contracts. Keep CLIs backward compatible and add regression tests for every change.
- Keep tests, evals and dev docs out of the skill folders (the skill folder is what Claude loads).
- The personal `my-voice` command (`~/.claude/commands/my-voice.md`) is not part of this repository; do not add it.
- Clean `__pycache__` from `skills/` after running tests.

## Book

- Chapters must be listed in `livro/_quarto.yml` (`book.chapters`; appendices under `book.appendices`). `lang: pt-BR` renders cross-references as "Seção 9.1" / "Apêndice D".
- Each method chapter has fixed sections with stable ids: `#sec-NN-regras`, `-passos`, `-diretrizes`, `-exemplo`, `-erros`, `-skill`, `-relato`, `-leituras` (some add more). Appendices start with an H1 carrying an id (`# Título {#sec-...}`); the specification is cited as `@sec-especificacao`, `@sec-especificacao-regras`, `-tipos`, `-ia`, `-caixa`, `-contrato`.
- `livro/references.bib` is the single bibliography (one key per work, `sobrenomeAnoPalavra`). Course materials remain citable sources (`schaefer2026aulaN`, `schaefer2026ementa`, `schaefer2026codigos`, `schaefer_oqfunciona`).
- No chapter has executable code chunks: R code is illustrative (```` ```r ````, never ```` ```{r} ````); diagrams use ```` ```{mermaid} ````.
- Writing conventions (see `livro/_notas-leitura/_GUIA.md`): every rule, threshold, number or definition needs a citation `[@key, p. N]`; OQF preprint pages use the printed page number; no em dashes as punctuation; English technical terms in italics on first use; tables for rules, numbered lists for steps; feminine articles before section refs ("na @sec-07-regras"), masculine before the appendix itself ("o @sec-especificacao"); never put a cross-reference inside citation brackets or bracketed text; never hard-code chapter numbers in prose.
- The site is public but the repository is private: `_notas-leitura/` and `skills/` are never rendered or published. Do not name private projects in the book chapters.

## Publishing

`.github/workflows/publish.yml` runs on push to `main` (or manual dispatch): sets up R (knitr/rmarkdown only) and Quarto, renders `livro/`, and deploys `livro/docs/` to the `gh-pages` branch (served at felipelamarca.com/Systematic-Review). Don't commit or hand-edit build output.
