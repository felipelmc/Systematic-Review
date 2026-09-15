---
name: baixar-pdfs-academicos
description: >-
  Baixa PDFs de artigos, capítulos e teses acadêmicos a partir de DOI, título
  ou uma planilha de revisão de literatura/sistemática, tentando em cascata
  fontes legítimas — Unpaywall, OpenAlex, Semantic Scholar, CORE, Crossref,
  padrões de editora (PLOS, MDPI, SciELO), HAL, BDTD e Wayback Machine — antes
  de perguntar ao usuário, em chat, se pode tentar Sci-Hub para o que sobrar
  paywalled (nunca sem perguntar). Para o restante, oferece agentes em
  paralelo buscando cópias legítimas (página de autor, repositório
  institucional, preprint). Use sempre que o usuário pedir para "baixar os
  PDFs desses papers", "conseguir o texto completo de", "buscar esse
  artigo/DOI", "baixar essa tese/dissertação", "rodar o script de download de
  papers", "coletar os PDFs da revisão sistemática/bibliografia", "checar
  quais artigos ainda faltam baixar", ou entregar uma planilha com
  título/autor/DOI pedindo os arquivos. Cobre planilha XLSX/CSV e pedido de 1
  paper, com verificação opcional de que o PDF é o texto certo.
---

# Baixar PDFs acadêmicos

Baixa PDFs de artigos, capítulos e teses acadêmicas a partir de DOI, título ou de uma planilha inteira (revisão sistemática/de escopo), tentando em cascata fontes de acesso aberto legítimas antes de considerar o Sci-Hub como último recurso — e só com autorização explícita do usuário, a cada uso.

## Como funciona

Um único script (`scripts/baixar_pdfs.py`) cobre dois modos:

- **`single`** — 1 paper por vez, a partir de um DOI ou de um título, direto na conversa.
- **`batch`** — uma planilha inteira (XLSX ou CSV), 1 linha por trabalho.

Um segundo script opcional (`scripts/verificar_conteudo.py`) confere, depois do download, se o PDF é mesmo o texto certo — extrai texto das primeiras páginas e checa se título e autor aparecem nele. Isso pega o pior erro possível numa revisão de literatura: um PDF válido, mas do artigo errado (ex. baixou o PDF de outra referência citada na página).

Para o que sobrar depois da cascata + Sci-Hub, existe uma terceira camada — não é mais script, é orquestração: agentes Claude Code em paralelo, com busca web, procurando cópias legítimas que a cascata automática não alcança (página pessoal de autor, repositório institucional, servidor de preprint). Um terceiro script (`scripts/mesclar_achados_agentes.py`) aplica os achados desses agentes de volta ao mesmo relatório CSV, com segurança contra sobrescrever um achado já verificado.

## Fluxo de trabalho

1. **Detectar o modo.** Usuário anexou/mencionou uma planilha, ou pediu para baixar os PDFs de uma lista/revisão inteira → `batch`. Usuário colou um DOI ou o título de 1 paper isolado → `single`. Em caso de dúvida, pergunte.

2. **Garantir as dependências**, uma vez por ambiente:
   ```bash
   python3 -c "import fitz, pandas, requests" || pip3 install -r "${CLAUDE_SKILL_DIR}/scripts/requirements.txt"
   ```

3. **Resolver o e-mail** usado nas chamadas de API (a Unpaywall exige um e-mail de identificação, por convenção do "polite pool"). Use o e-mail do usuário se já disponível no contexto da sessão. Senão, pergunte uma vez e sugira exportar `PDF_DOWNLOADER_EMAIL` para não perguntar de novo em sessões futuras.

4. **Rodar o script — sempre sem Sci-Hub na primeira passada.** Resolva os caminhos (`--saida-pdfs`, `--relatorio`, `--planilha`) relativos ao **diretório do projeto atual**, não à pasta da skill. O script em si é sempre invocado por caminho absoluto:

   ```bash
   # Modo batch
   python3 "${CLAUDE_SKILL_DIR}/scripts/baixar_pdfs.py" batch \
     --planilha caminho/para/planilha.xlsx \
     --saida-pdfs caminho/para/pdfs \
     --relatorio caminho/para/relatorio_pdfs.csv \
     --email usuario@exemplo.com

   # Modo single
   python3 "${CLAUDE_SKILL_DIR}/scripts/baixar_pdfs.py" single \
     --doi 10.xxxx/yyyy \
     --saida-pdfs caminho/para/pdfs \
     --email usuario@exemplo.com
   ```

   O script já detecta colunas comuns (`titulo/título/title`, `doi/doi_limpo`, `autor/autores/primeiro_autor`, `ano/year`, `chave/citekey/bib_key`). Se a planilha usar nomes diferentes, passe `--col-titulo`/`--col-doi`/`--col-autor`/`--col-ano`/`--col-chave` explicitamente. Colunas `id`/`Key` (OpenAlex, Zotero) nunca são usadas como chave. Uma chave existente só é reaproveitada se for válida como nome de arquivo e citekey (letras, dígitos, `_` ou `-`, começando por letra); senão o script avisa e gera outra com `scripts/chave.py`, o mesmo algoritmo Sobrenome+Ano de `gerar-bibtex` e `fichamento-sistematico`.

5. **Ler e resumir o relatório em português.** O script já imprime um resumo ao final (total, por status, por fonte) — reproduza isso para o usuário. Consulte [references/fontes.md](references/fontes.md) se precisar explicar de onde veio um PDF específico, por que uma fonte não funcionou, ou se o paper já cai numa categoria conhecida sem solução.

6. **Rodar a verificação de conteúdo quando fizer sentido** — recomendado sempre que os PDFs forem usados depois para fichamento/extração de dados; dispensável para uma checagem rápida:
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/verificar_conteudo.py" \
     --pdfs caminho/para/pdfs --relatorio caminho/para/relatorio_pdfs.csv
   ```
   Destaque separadamente, com título e motivo, qualquer linha com veredito `suspeito`, `sem_camada_de_texto` ou `conferir_a_mao` — são casos que precisam de checagem manual antes de confiar no conteúdo.

7. **Perguntar sobre Sci-Hub — uma vez, agregado, ao final, nunca por padrão.** Depois da cascata legítima (e só depois), se sobrarem papers com `status=nao_encontrado` **e DOI conhecido**, pare e pergunte ao usuário, por exemplo:

   > "Sobraram N papers paywalled depois de tentar todas as fontes legítimas: [lista com título/ano]. Quer que eu tente o Sci-Hub para eles?"

   Nunca decida sozinho, nunca pergunte paper por paper. Papers **sem DOI** não vão para o Sci-Hub — sinalize isso à parte. Só com confirmação explícita ("sim", "pode tentar", etc.), rode de novo passando só os DOIs confirmados:
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/baixar_pdfs.py" batch \
     --planilha ... --saida-pdfs ... --relatorio ... \
     --apenas-pendentes --scihub-dois "10.xxxx/a,10.xxxx/b"
   ```
   (modo single: `--tentar-scihub`, sem precisar de lista, já que é 1 DOI só.)

8. **Oferecer agentes paralelos de busca web para o que sobrar — não é automático, mas também não precisa da mesma confirmação obrigatória do Sci-Hub** (aqui não há questão legal/ética, só custo de tempo e tokens). Depois do resumo do relatório (etapa 5) e da decisão sobre Sci-Hub (etapa 7, aceita ou recusada), se ainda sobrarem papers `status=nao_encontrado` (com ou sem DOI — esta etapa não é DOI-gated como o Sci-Hub), ofereça isso como próximo passo em vez de simplesmente parar ou de rodar sem avisar.

   Se o usuário topar (ou já tiver pedido "baixa mais"/"tenta de outro jeito"/algo do tipo), divida os pendentes em lotes de ~6-8 papers e dispare um agente `general-purpose` por lote, em paralelo (para listas grandes, rode em ondas em vez de disparar dezenas de agentes de uma vez). Cada agente recebe título/autores/ano/DOI de cada paper do seu lote e as instruções:
   - **Não tentar Sci-Hub de novo** — isso já foi decidido na etapa 7.
   - Procurar cópias hospedadas legitimamente: página pessoal do autor/instituição, repositório institucional (DiVA, OPUS, DASH, VU Research Portal, HEAL-Link, SSOAR, EconStor, ...), servidor de preprint (SSRN, OSF, arXiv, HAL), série de working papers, autoarquivo ACL/ACM.
   - Verificar que título/autor batem antes de aceitar — nunca forçar um match errado.
   - Baixar o PDF encontrado direto para `{saida-pdfs}/{chave}.pdf` (mesma convenção que `baixar_pdfs.py` já usa) via curl/wget.
   - **Reportar de volta estruturado, não em prosa**: para cada paper do lote, `{chave, encontrado, url, versao, motivo}` — `versao` só vira `"preprint"` quando há evidência real (rótulo explícito "preprint"/"forthcoming" na fonte, ou o DOI/URL do achado é claramente diferente do DOI do registro/editora); sem evidência, deixar em branco, nunca adivinhar.
   - **Proibido**: copiar o PDF de uma chave *diferente* pra satisfazer esta, mesmo que pareça o mesmo paper — se o registro específico não foi verificado de forma independente, reportar `encontrado: false` e colocar a nota sobre o registro-irmão em `motivo`. Isso é regra, não sugestão — é exatamente o erro que motivou essa etapa existir.
   - Se o identificador do registro resolver para algo que não é um manuscrito completo (um pré-registro sem resultados ainda, uma entrada de dataset/dados de replicação, uma errata/correção), reportar isso explicitamente (`nao_e_manuscrito: true`, `motivo` explicando) em vez de um "não encontrado" genérico.

   Depois que os agentes voltarem, monte um JSON com os achados de todos os lotes (ver formato completo no docstring de `scripts/mesclar_achados_agentes.py`) e aplique:
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/mesclar_achados_agentes.py" \
     --relatorio caminho/para/relatorio_pdfs.csv \
     --achados caminho/para/achados.json \
     --saida-pdfs caminho/para/pdfs
   ```
   Depois de mesclar, rode `verificar_conteudo.py` de novo (etapa 6) — ele já pega os novos `status=ok` automaticamente, sem precisar de nenhum flag extra.

## Referências

- [references/fontes.md](references/fontes.md) — tabela de todas as fontes/endpoints, workarounds por editora (PLOS, MDPI, SciELO, HAL, Zenodo etc.) e categorias de caso conhecidas sem solução programática. Consulte antes de insistir num paper que já falhou por um motivo documentado ali, ou ao estender o script com uma nova fonte.
- [assets/planilha_exemplo.csv](assets/planilha_exemplo.csv) — formato mínimo de planilha aceito pelo modo batch.

## Limitações conhecidas

- Nenhuma fonte legítima cobre 100% dos casos — paywalls definitivos (ex. Elsevier sem versão OA) e repositórios com login institucional continuam sem solução programática; ver `references/fontes.md`.
- A verificação de conteúdo depende de o PDF ter camada de texto extraível — PDFs escaneados sem OCR aparecem como `sem_camada_de_texto` e precisam de checagem visual humana.
- Sci-Hub é opt-in com confirmação obrigatória do usuário — não existe flag que pule essa pergunta.
- Os agentes de busca web (etapa 8) não são onipotentes — casos de paywall definitivo sem nenhuma versão autoarquivada em lugar nenhum continuam sem solução, e cada lote leva alguns minutos e gasta tokens de verdade; ofereça a etapa, não presuma que vai resolver tudo.
