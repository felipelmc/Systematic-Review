---
name: gerar-bibtex
description: >-
  Gera um arquivo .bib (BibTeX) a partir de uma planilha de papers (XLSX/CSV) —
  título, autor(es), ano, DOI, tipo de publicação, periódico/veículo. Detecta
  automaticamente os nomes de coluna mais comuns nos projetos do usuário
  (titulo/título/title, autor/autores/primeiro_autor, ano/year, doi/doi_limpo,
  tipo/tipo_publicacao, nome_publicacao/journal). Reaproveita a coluna de chave
  já existente (chave/citekey/bib_key), se a planilha vier de
  baixar-pdfs-academicos ou fichamento-sistematico, para que as entradas do
  .bib batam com os nomes de arquivo de PDFs e fichas já gerados; senão gera a
  chave Sobrenome+Ano do zero. Use sempre que o usuário pedir para "gerar o
  .bib da minha revisão/lista de papers", "criar as referências em BibTeX",
  "exportar a bibliografia para o LaTeX/Overleaf", ou entregar uma planilha de
  papers pedindo o arquivo de referências.
---

# Gerar .bib a partir de uma planilha de papers

Script único e determinístico — sem orquestração de agentes. Lê uma planilha de papers e
escreve um `.bib` correspondente, uma entrada por linha da planilha.

## Como usar

1. **Encontre a planilha mais completa do projeto** (ex. `RS_consolidado.xlsx`,
   `included_papers.xlsx`) — a que tem título/autor/ano/DOI e, se possível,
   tipo de publicação e periódico. **Não** use `relatorio_pdfs.csv` da skill
   `baixar-pdfs-academicos` como fonte principal — ele não tem journal/tipo, só serve
   como fonte da coluna de chave (`chave`) se for o único lugar onde ela existe.

2. **Rode o script:**
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/gerar_bib.py" \
     --planilha caminho/para/planilha.xlsx \
     --out caminho/para/references.bib
   ```
   Se as colunas não tiverem os nomes usuais, passe `--col-titulo`/`--col-autor`/
   `--col-ano`/`--col-doi`/`--col-tipo`/`--col-journal`/`--col-chave` explicitamente —
   o script imprime as colunas disponíveis se não conseguir detectar o título sozinho.

3. **Garanta dependências**, uma vez por ambiente:
   ```bash
   python3 -c "import pandas, openpyxl" || pip3 install -r "${CLAUDE_SKILL_DIR}/scripts/requirements.txt"
   ```

4. **Reporte o resumo** que o script já imprime (nº de entradas, por tipo, avisos de
   papers sem DOI/ano) ao usuário.

## Coerência de chave entre as três skills

Se a planilha já passou por `baixar-pdfs-academicos` (tem coluna `chave`) ou por
`fichamento-sistematico` (tem coluna `citekey` no consolidado), o script reaproveita
essa coluna — a entrada do `.bib` fica com o mesmo nome do PDF/ficha já gerados
(`Piwowar2007.pdf`, `fichamento_Piwowar2007.md`, `@article{Piwowar2007,...}`). Sem
coluna de chave, gera uma nova pelo mesmo algoritmo Sobrenome+Ano das outras skills —
não é uma reimplementação parecida, é o mesmo arquivo `scripts/chave.py`, copiado
idêntico (mesmo sha256) em `baixar-pdfs-academicos`, `fichamento-sistematico` e
`revisao-sistematica`. Não edite só uma cópia.

- Colunas `id`/`Key` (OpenAlex, Zotero) nunca são usadas como chave.
- Uma chave existente inválida como citekey (URL, espaços, começa com dígito) gera um
  aviso e é substituída por uma nova; o resumo final informa quantas foram regeneradas.
- O campo `author` separa autores com a mesma lógica da chave (`|`, `;`, ` and ` ou
  vírgula), e nomes institucionais com " and " vão entre chaves.
