# Guia comum para os capítulos da parte "Método: revisão sistemática de ponta a ponta"

Este guia vale para todos os agentes que escrevem capítulos em `metodo/` e notas em `_notas-leitura/`.

## Para que servem os capítulos

Eles são a base de conhecimento de uma skill do Claude Code (`revisao-sistematica`) que conduz revisões sistemáticas de ponta a ponta. São lidos por dois públicos: (i) o Felipe (pós-graduando em ciência política, IESP-UERJ) e outros pesquisadores que vão estudar o método; (ii) quem destilar os capítulos em instruções operacionais da skill. Por isso cada capítulo precisa ser uma **referência operacional confiável**: regras de decisão explícitas, limiares, passos, exemplos e armadilhas, com as fontes citadas.

O método tem três camadas, nesta ordem de autoridade quando houver conflito:
1. **Normas internacionais** (Cochrane Handbook v6.5, Campbell MECCIR, JBI Manual, PRISMA 2020 e extensões, RAISE, GRADE, CERQual, SWiM, RAMESES etc.).
2. **Especificação metodológica do plano** (Apêndice B do plano; ver abaixo), que corrige fragilidades do método do curso.
3. **Método do curso** (Prof. Bruno Schaefer, MAPE/IESP-UERJ; proposta "O que funciona?" — OQF), que é a âncora didática e o formato de avaliação de políticas públicas (revisão mista e sequencial + caixa de ferramentas).

Quando o curso divergir das normas, apresente o que o curso faz, explique a limitação e diga o que fazer (sem desqualificar o curso; o tom é de aprimoramento).

## Contexto obrigatório (ler antes de escrever)

- Plano aprovado: `/Users/felipelmc/.claude/plans/cara-o-seguinte-jaunty-zebra.md`. Leia **PLANO FINAL §1 e §4**, **Apêndice A** (achados: método OQF, pipeline R do professor, prática do Felipe, slides e ementa, inventário das leituras, benchmark) e **Apêndice B** (especificação metodológica vinculante). O Apêndice C é útil para o item "mapeamento para a skill".
- Texto integral da proposta OQF (Schaefer, Borges & Freitas 2025, preprint OSF `aht4j_v1`, chave `schaefer_oqfunciona`): `/private/tmp/claude-501/-Users-felipelmc-Desktop-Systematic-Review/4285e83e-35af-49c4-9828-c676789f6eb9/scratchpad/fontes/oqf_texto_base_schaefer_borges_freitas_2025.txt` (não copiar para o repositório).
- Arquivo do curso: `~/Downloads/zs6h4-osfstorage-archive/`. As pastas têm nomes com caracteres corrompidos e aparecem duplicadas (`8 C¢digos R` e `8 Códigos R`, `6 An†lise de dados` e `6 Análise de dados`); use `ls` e globs. Slides em `9 Slides/` (pouco texto extraível: use `pdftotext -layout` e depois veja as páginas com a ferramenta Read e o parâmetro `pages`, no máximo 20 por chamada). Ementa na raiz do arquivo.
- PDFs: extraia com `pdftotext -layout "<arquivo>" - | less`-equivalente (imprima no stdout) ou leia páginas com Read. Para livros/relatórios longos, leia o sumário e depois só os capítulos pertinentes (declare quais leu).
- Web: use WebSearch/WebFetch para normas e fontes que não estão no arquivo. Prefira fontes primárias (sites oficiais, artigos). Se uma página bloquear (403/captcha), procure espelho oficial (PMC, site da organização, OSF).

## Regras de conteúdo

1. **Nada sem fonte.** Toda regra, limiar, número, definição ou recomendação precisa de citação `[@chave]` (com página quando for do arquivo: `[@chave, p. 12]`). Se não conseguir verificar, não inclua.
2. **Números e limiares conferidos na fonte** (ex.: κ ≥ 0,6; recall ≥ 0,95; k ≥ 10 para funil). Não confie na memória.
3. **Paráfrase.** Citações literais só quando a formulação importa, com no máximo 25 palavras cada e poucas por fonte. Nunca reproduza tabelas inteiras de artigos protegidos; resuma. Normas com licença aberta (ex.: PRISMA CC BY) podem ser reproduzidas com atribuição, mas prefira resumir e linkar.
4. **Exemplos trabalhados** com os casos do curso: proibição de celulares nas escolas (Schaefer, Borges & Gomes Filho 2025, chave `schaefer2025proibicao`) e REFIS (pipeline R do professor). Quando o exemplo do curso tiver erro (ver Apêndice A: contagens PRISMA que não fecham, Winer com z, Fisher sem direção, dicionário sem fronteira de palavra etc.), use-o como caso de "erro comum".
5. **Brasil e lusofonia**: sempre que pertinente, inclua bases, instituições e literatura cinzenta brasileiras (CAPES, BDTD, SciELO, IPEA, TCU, CGU, Enap) e exemplos de políticas brasileiras.
6. **Não invente chaves nem referências.** Reaproveite as chaves já existentes em `references.bib` (lista abaixo). Para fontes novas, crie entradas BibTeX completas e verificadas (autores, ano, título, veículo, volume, páginas, DOI/URL) no arquivo `_notas-leitura/NN-slug.bib` do seu capítulo. Formato de chave: `sobrenomeAnoPalavra` em minúsculas, sem acentos (ex.: `higgins2024cochrane`, `page2021prisma`). Não edite `references.bib` nem `_quarto.yml` (o coordenador consolida).

Chaves já existentes: xiao2019guidance dacombe2018systematic haddaway2014policy figueiredo2014meta sutton2019meeting grant2009typology orourke2007historical grizenti2024revisao pawson2005realist vaessen2014effects juliano2023mudanca schaefer2019whatsapp dakerwhite2015blame glass1979meta kopittke2021funciona fisher2023school klenowski2010empirical rogers2008programme peters2025develop gustafsson2018point cordoba2023teoria aguiar2023mapeando carrerarivera2022howto whitehead2013searching lycariao2025comunidade aria2017bibliometrix arruda2022vosviewer vaneck2010software madaleno2015guide thomas2003children nutley2013counts alnoman2024simplifying daly2007hierarchy keele2015statistics harrer2021doing ludwig2011mechanism hedstrom2010causal dalkin2015whats cintron2022heterogeneous jin2024policy hunter2014transforming gerring2022democracy garcia2017educational brydges2019effect bia2026health dixonwoods2006systematic vantwist2023smart thomas2008methods kahwati2016using elsherif2024using santos2019bolsafamilia schaefer_oqfunciona fonseca2023agenda small2011conduct bamberger2012introduction batista2017mais schaefer2025proibicao andrade2024sinteses sousa2019sinteses vieira2020traduzir silva2022politicas hjort2021research toma2024understanding andrade2020traducao mehmood2023training baron2018brief faria2005politica faria2022movimento

(Confira no `references.bib` se a entrada existente corresponde mesmo à obra que você cita.)

## Estrutura fixa de cada capítulo

Arquivo `metodo/NN-slug.qmd`:

```
---
title: "Título do capítulo"
---

(parágrafo de abertura: para que serve esta etapa e que decisões ela exige)

## Decisões e regras {#sec-NN-regras}
(tabelas com regras de decisão e limiares; quando usar o quê)

## Passo a passo {#sec-NN-passos}

## O que as diretrizes exigem {#sec-NN-diretrizes}
(itens de PRISMA 2020/-S/-ScR/-trAIce, MECCIR, JBI etc. pertinentes, citados pelo número do item)

## Exemplo trabalhado {#sec-NN-exemplo}
(celulares e/ou REFIS; mostrar o que foi feito e o que deveria ser feito)

## Erros comuns e como evitá-los {#sec-NN-erros}

## Na skill `revisao-sistematica` {#sec-NN-skill}
(quais comandos `rs.py`, templates, codebooks e portões G1–G9 operam esta etapa, conforme o plano; a skill está em construção, então descreva o contrato planejado sem inventar detalhes além do plano)

## Como relatar {#sec-NN-relato}
(texto mínimo que o relatório/artigo deve conter sobre esta etapa, com exemplo de redação)

## Leituras {#sec-NN-leituras}
(normas primeiro, depois leituras do curso, com uma linha sobre para que serve cada uma)
```

Pode acrescentar seções específicas entre "Decisões e regras" e "Passo a passo" quando o tema exigir (ex.: fórmulas de conversão de efeito). Use callouts do Quarto com parcimônia: `::: {.callout-important}` para regras invioláveis, `::: {.callout-warning}` para armadilhas, `::: {.callout-note}` para diferenças entre o curso e as normas.

## Regras de forma

- Português do Brasil. Prosa clara e direta, com termos técnicos em inglês em itálico na primeira ocorrência (ex.: *risk of bias*).
- Tabelas para regras e comparações; listas numeradas para passos; parágrafos para explicação. Evite listas de tópicos soltos para argumentação.
- Não use travessão (—) como pontuação de frase; use vírgulas, parênteses ou dois-pontos. Evite chavões de IA ("crucial", "fundamental", "robusto", "não apenas X, mas também Y", "vale destacar que", "desempenha um papel", tríades artificiais, frases de efeito no fim de parágrafo).
- Fórmulas em LaTeX (`$...$`, `$$...$$`). Código R/Python apenas ilustrativo, em blocos não executáveis: ```` ```r ```` (nunca ```` ```{r} ````).
- Referências cruzadas entre capítulos com `@sec-NN-...` só para seções que você sabe que existem pelo guia (as âncoras padrão acima existem em todos os capítulos: ex. `@sec-06-regras`).
- Tamanho-alvo: 4.000 a 8.000 palavras por capítulo (capítulos 08a e 11 podem chegar a 10.000). Densidade acima de extensão.

## Notas de leitura (rastreabilidade)

Arquivo `_notas-leitura/NN-slug.md`, uma seção por fonte lida:

```
## chave — Autor (ano), título curto
- Arquivo/URL:
- O que foi lido: (inteiro | páginas X–Y | capítulos)
- Pontos usados no capítulo:
  - (afirmação resumida) — p. N — trecho ≤ 25 palavras, se houver
- Limitações/observações:
```

## Numeração dos capítulos

01-fundamentos-tipos · 02-pergunta-teoria · 03-protocolo · 04-busca · 05-organizacao-triagem · 06-qualidade-risco-vies · 07-decomposicao · 08a-sintese-quantitativa · 08b-sintese-qualitativa-integracao · 09-certeza-evidencia-pratica · 10-relato-divulgacao · 11-ia-na-revisao

Evite repetir o conteúdo central de outro capítulo; faça a ponte com uma frase e a referência cruzada (ex.: "a validação da triagem por IA está no @sec-11-regras").
