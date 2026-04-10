# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A [Quarto](https://quarto.org) book of personal course notes for **Espaço, População e Política** (Space, Population and Politics), a graduate course at IESP-UERJ taught by Prof. Fernando Guarnieri. Notes are written in `.qmd` files and published automatically to GitHub Pages on every push to `main`.

## Build commands

```bash
# Render the full book locally (outputs to docs/)
quarto render

# Preview with live reload
quarto preview

# Render a single file
quarto render aulas/aula-02.qmd
```

CI runs on push to `main` and uses R 4.4 with packages: `knitr`, `rmarkdown`, `ggdag`, `ggplot2`.

## Structure

- `_quarto.yml` — book configuration; **new chapter files must be added here** under the `chapters:` list to appear in the book
- `aulas/` — one `.qmd` file per class session
- `references.bib` — BibTeX bibliography; cited with `@key` syntax in `.qmd` files
- `custom.scss` — custom theme overrides (extends the `cosmo` Quarto theme)
- `index.qmd` — book preface/introduction page
- `docs/` — rendered output (committed by CI, do not edit manually)
- `pdfs/` — reference PDFs for the course (not rendered, just stored)

## Adding a new class note

1. Create `aulas/aula-NN.qmd` with frontmatter `title`, `subtitle` (optional), and `date`.
2. Register it in `_quarto.yml` under the `"Aulas"` part's `chapters:` list.
3. Add any new bibliography entries to `references.bib`.
