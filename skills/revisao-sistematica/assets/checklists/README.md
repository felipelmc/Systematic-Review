# Checklists de relato e de revisão da busca

Este é o único README desta pasta e vale para todos os checklists. Todos os CSV têm as colunas `item,secao,topico,descricao`, com paráfrases curtas em português. Consulte sempre o documento original para o texto integral e a explicação de cada item.

## Arquivos sem linha de comentário (lidos por `rs.py prisma`)

`scripts/rslib/prisma.py` lê estes dois arquivos com um leitor CSV simples e usa a primeira linha como cabeçalho; por isso eles não têm linha de atribuição e a atribuição fica aqui. Um teste compara cada arquivo com a lista embutida no script: não acrescente linha de comentário.

| Arquivo | Diretriz | Fonte |
|---|---|---|
| `prisma2020.csv` | PRISMA 2020, 27 itens (com subitens) | Page MJ, McKenzie JE, Bossuyt PM, et al. The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. BMJ 2021;372:n71 (CC BY 4.0) |
| `prisma_scr.csv` | PRISMA-ScR, 20 itens essenciais e 2 opcionais (12 e 16) | Tricco AC, Lillie E, Zarin W, et al. PRISMA Extension for Scoping Reviews (PRISMA-ScR): checklist and explanation. Annals of Internal Medicine 2018;169(7):467-473 |

## Arquivos com atribuição na primeira linha comentada

Os demais CSV desta pasta começam com uma linha `# ...` de atribuição (com a referência completa); o cabeçalho está na linha 2. Para ler, descarte as linhas iniciadas por `#` (ex.: `pandas.read_csv(..., comment="#")` ou filtrando as linhas antes do `csv.DictReader`).

| Arquivo | Diretriz | Fonte | Onde a skill usa |
|---|---|---|---|
| `prisma_s.csv` | PRISMA-S, 16 itens do relato da busca | Rethlefsen ML, Kirtley S, Waffenschmidt S, et al. PRISMA-S. Systematic Reviews 2021;10:39 (CC BY 4.0) | references/02-busca.md, seção 9 (colunas do log de buscas) |
| `press.csv` | PRESS 2015, revisão por pares da estratégia de busca (seis elementos, com subitens) | McGowan J, Sampson M, Salzwedel DM, Cogo E, Foerster V, Lefebvre C. PRESS 2015 Guideline Statement. Journal of Clinical Epidemiology 2016;75:40-46 | references/02-busca.md, seção 8 |
| `swim.csv` | SWiM, 9 itens (1a e 1b separados) | Campbell M, McKenzie JE, Sowden A, et al. Synthesis without meta-analysis (SWiM) in systematic reviews: reporting guideline. BMJ 2020;368:l6890 | references/07a-sintese-quantitativa.md, seção 10; references/08-relato.md, seção 7 |
| `prisma_traice.csv` | PRISMA-trAIce, 17 itens do relato de uso de IA (proposta sem endosso do PRISMA) | Holst D, Moenck K, Koch J, Schmedemann O, Schüppstuhl T. JMIR AI 2025;4:e80247 | references/ia-validacao.md, seção 7 |

## Uso no projeto

- `rs.py prisma` gera `07-relatorio/checklist_prisma.csv` (PRISMA 2020 ou PRISMA-ScR; sem `--tipo`, o padrão é `scr` para escopo e mapa de evidências e `2020` nos demais tipos) com as colunas extras `local_no_relato`, `status` e `evidencia_no_projeto`.
- Para as extensões, copie o CSV para `07-relatorio/checklist_<nome>.csv` sem a linha de atribuição e acrescente `local_no_relato` e `status` (trecho pronto em references/08-relato.md, seção 7).
- ENTREQ, eMERGe, RAMESES e PRIOR não têm CSV na skill: preencha a partir do documento oficial.
