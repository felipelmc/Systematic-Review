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
python3 -m pytest -q dev/revisao-sistematica/tests/test_dedup.py -k preprint   # a single test by name
Rscript -e 'testthat::test_dir("dev/revisao-sistematica/tests/R")' # R reference-value tests, from the repo root
dev/revisao-sistematica/tests/e2e/rodar.sh [-k autopiloto]   # end-to-end scenarios only; extra args go to pytest
```

- Dependencies: `python3 -m pip install -r skills/revisao-sistematica/scripts/requirements.txt` (optional: `requirements-opcional.txt`); R packages `meta metafor esc irr clubSandwich robvis jsonlite`. Without Rscript/metafor the R-dependent tests skip instead of failing.
- Prefix pytest with `PYTHONDONTWRITEBYTECODE=1` (and `-p no:cacheprovider`) to avoid leaving `__pycache__` in `skills/`.
- Tests marked `osf` run the importers against real exports and skip unless `RS_OSF_DIR` is set: `RS_OSF_DIR=<dir> python3 -m pytest -q -m osf dev/revisao-sistematica/tests`. `RS_SKILLS_DIR=~/.claude/skills` points `test_chave_sync.py` at the installed copies.
- `dev/revisao-sistematica/evals/` holds model-behaviour evals (trigger routing, acceptance scenarios) run with `claude -p` in throwaway dirs outside any repo with a CLAUDE.md; they spend tokens, so run them only when asked (see `evals/README.md`).

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

## Architecture of `revisao-sistematica`

Methodological rules flow in one direction: the book's specification (`apendice-d-especificacao.qmd`) → its operational rewrite in `skills/revisao-sistematica/references/` (plus `SKILL.md`) → module contracts in `dev/revisao-sistematica/CONTRATOS.md` → code. On conflict the specification wins over CONTRATOS. A methodological change usually touches the chapter's `#sec-NN-skill` section, the matching reference file and the code together.

- **Dispatcher.** `scripts/rs.py` imports the modules in `MODULOS_COMANDOS`; each exposes `registrar(subparsers)` and sets `func(args) -> int`. A new command means a new `rslib` module added to that list. Missing modules are skipped so the skill degrades partially.
- **Command contract** (CONTRATOS §2): resolve the project root with `estado.exigir_projeto(args.dir)`; the last stdout line is the JSON from `estado.resumo({...})`; commands that change the project call `estado.registrar_evento(...)` listing the artifacts written; reruns are idempotent; joins only by `id_rs`, `id_registro` or `chave`, never by title; CSVs are UTF-8, comma-separated, headers exactly as in `esquema.py`. Exit codes: 0 ok, 1 usage/data error, 2 methodological check failed, 3 missing dependency.
- **Project state.** Each review is a folder with `rs_estado.json` (cache, three-way-merged on save) and `rs_log.jsonl` (append-only event ledger). Every writer goes through `estado.py` under `estado.trava()` (`.rs.lock`) and `estado.escrever_atomico`; never write these files directly.
- **Frozen modules** (CONTRATOS §1): `rs.py`, `esquema.py`, `estado.py`, `chave.py`, `normalizar.py`, `assets/schemas/*.schema.json`. You may add functions, but existing signatures and values must not change. New constants go in a new `# Acréscimos de contrato (vX.Y)` block at the end of `esquema.py`, and the contract round is documented as a new section in CONTRATOS.md. Existing values never change, so old projects stay readable. `test_contratos_v13.py` checks that local constant copies in modules still match `esquema.py`.
- **R bridge.** `scripts/R/*.R` (effects, meta-analysis, SWiM, combined tests) are run only through `rs.py analise …` (`rslib/analise_r.py`), with the project root as the working directory. R never writes state or log; the Python wrapper records `analise_executada`. `RS_RSCRIPT` overrides the Rscript path.
- **Dependencies.** Required: stdlib plus `pandas`, `openpyxl`, `xlrd`, `requests`, `pymupdf`. Everything else (`rapidfuzz`, `pyalex`, `anthropic`, `openai`, `jsonschema`, …) is imported inside `try` and degrades with a warning; `rs.py ambiente` reports what is missing.
- **Code conventions.** Module docstrings are in Portuguese with a `USO` block and the reasons behind decisions. Credentials come only from env vars (`RS_EMAIL`, `OPENALEX_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`); never read `.env` implicitly; no personal paths, emails or real names in code. Tests go in `tests/test_<module>.py` with synthetic fixtures in `tests/fixtures/<module>/`.
- **Sister skills** are joined to the review by the citekey: `<chave>.pdf`, `fichamento_<chave>.md`, the `.bib` entry and the review's records. That is why `chave.py` must stay byte-identical across the four copies.

## Book

- Chapters must be listed in `livro/_quarto.yml` (`book.chapters`; appendices under `book.appendices`). `lang: pt-BR` renders cross-references as "Seção 9.1" / "Apêndice D".
- Each method chapter has fixed sections with stable ids: `#sec-NN-regras`, `-passos`, `-diretrizes`, `-exemplo`, `-erros`, `-skill`, `-relato`, `-leituras` (some add more). Appendices start with an H1 carrying an id (`# Título {#sec-...}`); the specification is cited as `@sec-especificacao`, `@sec-especificacao-regras`, `-tipos`, `-ia`, `-caixa`, `-contrato`.
- `livro/references.bib` is the single bibliography (one key per work, `sobrenomeAnoPalavra`). Course materials remain citable sources (`schaefer2026aulaN`, `schaefer2026ementa`, `schaefer2026codigos`, `schaefer_oqfunciona`).
- No chapter has executable code chunks: R code is illustrative (```` ```r ````, never ```` ```{r} ````); diagrams use ```` ```{mermaid} ````.
- Writing conventions (see `livro/_notas-leitura/_GUIA.md`): every rule, threshold, number or definition needs a citation `[@key, p. N]`; OQF preprint pages use the printed page number; no em dashes as punctuation; English technical terms in italics on first use; tables for rules, numbered lists for steps; feminine articles before section refs ("na @sec-07-regras"), masculine before the appendix itself ("o @sec-especificacao"); never put a cross-reference inside citation brackets or bracketed text; never hard-code chapter numbers in prose.
- Each chapter has a traceability pair in `_notas-leitura/NN-slug.md` (one section per source: what was read, pages, points used) and `NN-slug.bib`. When a chapter gains a source, record it there as well as in `references.bib`.
- `_GUIA.md` was written for the original chapter-drafting round: its content and form rules still apply, but its "Contexto obrigatório" paths, its "Apêndice B do plano" reference and its "método do curso" framing are historical. The authority order at the top of this file prevails.
- The site is public but the repository is private: `_notas-leitura/` and `skills/` are never rendered or published. Do not name private projects in the book chapters.

## Publishing

`.github/workflows/publish.yml` runs on push to `main` (or manual dispatch): sets up R (knitr/rmarkdown only) and Quarto, renders `livro/`, and deploys `livro/docs/` to the `gh-pages` branch (served at felipelamarca.com/Systematic-Review). Don't commit or hand-edit build output.
