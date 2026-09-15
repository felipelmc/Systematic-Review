# Fontes, endpoints e workarounds

Referência para `scripts/baixar_pdfs.py`. Todas as fontes são gratuitas e não exigem autenticação, exceto onde indicado.

## Cascata com DOI (nessa ordem)

| Ordem | Fonte | Endpoint | Auth | O que extrai |
|---|---|---|---|---|
| 1 | Unpaywall | `https://api.unpaywall.org/v2/{doi}?email={email}` | e-mail na query (polite pool) | `best_oa_location.url_for_pdf` — **nunca** o campo `url` (é a landing page HTML) |
| 2 | Semantic Scholar | `https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf` | nenhuma | `openAccessPdf.url` |
| 3 | OpenAlex | `https://api.openalex.org/works/doi:{doi}?mailto={email}` | nenhuma (mailto cortês) | itera todos os `locations[].pdf_url`, depois `open_access.oa_url` |
| 4 | CORE | `https://api.core.ac.uk/v3/search/works?q=doi:"{doi}"` | opcional: `Authorization: Bearer {CORE_API_KEY}` (sem key funciona, rate limit menor) | `results[].downloadUrl` |
| 5 | Padrões por editora | ver tabela abaixo | nenhuma | construído a partir do prefixo do DOI |
| 6 | HAL | `https://api.hal.science/search?q=doiId_s:"{doi}"&fl=halId_s,title_s,fileMain_s&rows=5` | nenhuma, mas requer `User-Agent: Wget/1.21.1` + `verify=False` | `fileMain_s` |
| 7 | Wayback Machine (CDX) | `https://web.archive.org/cdx/search/cdx?url={url}&filter=mimetype:application/pdf&output=json` | nenhuma | primeiro snapshot com mimetype PDF — usar a **CDX API**, não a "availability" simples, que só enxerga a landing page |
| 8 | Landing page (fallback genérico) | segue `https://doi.org/{doi}` e minera o HTML final | nenhuma | `<meta citation_pdf_url>`, `<a href=*.pdf>`, `<object data>`, `<iframe>`, `<embed>` — desce 1 nível só, nunca recursivo |

## Cascata sem DOI (busca por título, ~12 primeiras palavras)

| Fonte | Endpoint | Retorna |
|---|---|---|
| Semantic Scholar (match) | `.../paper/search/match?query={titulo}&fields=title,openAccessPdf,externalIds` | DOI e/ou PDF direto — usar `/search/match`, não `/search` simples (o pool anônimo do `/search` rejeita a maioria das requisições) |
| OpenAlex (busca por título) | `https://api.openalex.org/works?filter=title.search:{titulo}` | DOI e/ou PDF direto |
| BDTD (teses/dissertações BR) | `https://bdtd.ibict.br/vufind/api/v1/search?lookfor={titulo}&type=Title&limit=3` | usa `type=Title` (não `AllFields`, que trata os termos do título como OR e devolve ruído) |

Todo resultado de busca por título é conferido contra o título original (`titulo_parece_igual`, similaridade ≥0.75) antes de ser aceito — evita pegar o paper errado.

## Sci-Hub (opt-in, nunca automático)

Mirrors tentados em ordem: `sci-hub.st`, `sci-hub.ru`, `sci-hub.se`. Extrai a URL do PDF do HTML (`citation_pdf_url` → `<object data>` → padrão `/storage/*.pdf`), detecta captcha (`"captcha" in html and "article" not in html`) e pula o mirror nesse caso. Usa headers de navegador real, não o User-Agent "honesto" das outras fontes — o Sci-Hub bloqueia UAs que se identificam como script.

**Só é chamado se o agente já obteve confirmação explícita do usuário no chat** — não existe flag que dispare isso silenciosamente por padrão.

## Etapa 8: agentes paralelos de busca web (opcional, oferecida — não script)

Para o que sobrar `nao_encontrado` depois da cascata + Sci-Hub. Diferente de tudo
acima, não é uma fonte programática fixa — é orquestração: um agente Claude Code
`general-purpose` por lote de ~6-8 papers, com WebSearch/WebFetch/Bash, procurando o
que a cascata estruturalmente não alcança (a cascata só sabe falar com APIs/padrões de
URL fixos; não navega um site de universidade procurando a página de publicações de um
professor, por exemplo). Ver `SKILL.md`, etapa 8, para o texto exato das instruções
dadas a cada agente.

Categorias onde isso tende a funcionar melhor que a cascata (complementa, não repete, a
lista de "casos sem solução programática" abaixo):
- **Página pessoal de autor/laboratório** — muito comum em ciência da computação/ML
  (ex. conferências ACM/ACL: autores quase sempre auto-hospedam o PDF do camera-ready).
- **Repositório institucional fora dos que a cascata já cobre** (HAL e BDTD estão na
  cascata; DiVA, OPUS, DASH, VU Research Portal, HEAL-Link, SSOAR, EconStor e outros
  não estão) — teses e artigos auto-arquivados.
- **Servidor de preprint** (OSF, SSRN) além do arXiv, que a cascata já cobre via
  Unpaywall/OpenAlex na maioria dos casos.
- **DOI que na verdade não é um manuscrito** — pré-registro sem resultados, entrada de
  dataset/replicação, errata — a cascata só sabe dizer "não achei PDF"; um agente
  consegue checar os metadados (ex. API do OSF) e reportar isso como o que é: nada pra
  achar, não uma falha de busca. Vira `status=nao_e_manuscrito` (ver `mesclar_achados_agentes.py`).

O merge de volta pro relatório é feito por `scripts/mesclar_achados_agentes.py` — nunca
à mão, porque a tentação de copiar o PDF de uma chave parecida pra outra (dois registros
com o mesmo título, DOIs diferentes) é real e já causou um erro real numa sessão
anterior. O script se recusa a sobrescrever qualquer chave que já esteja `ok`,
`ja_existia`, `scihub_ok` ou `nao_e_manuscrito` — só mexe em `nao_encontrado`.

## Workarounds por editora (`try_publisher_patterns`, por prefixo de DOI)

| Prefixo | Editora | Padrão de URL |
|---|---|---|
| `10.1371/` | PLOS | `https://journals.plos.org/{journal_slug}/article/file?id={doi}&type=printable` |
| `10.3390/` | MDPI | 1º tenta `mdpi.com/{suffix}/pdf`; se falhar, tenta o CDN direto `mdpi-res.com/d_attachment/{journal}/{journal}-{vol}-{art}/article_deploy/{journal}-{vol}-{art}.pdf` (bypassa o Cloudflare que costuma bloquear `/pdf` direto) |
| `10.159X/` | SciELO | resolve o DOI, extrai o PID (`S\d{4}-...`) da URL final, tenta `sci_pdf&pid={pid}&lng={en,pt,es}` nessa ordem |
| `10.3389/` | Frontiers | `https://www.frontiersin.org/articles/{doi}/pdf` |
| `10.1073/` | PNAS | `https://www.pnas.org/doi/pdf/{doi}` |
| `10.12952/` | Elementa (UCPress) | `https://online.ucpress.edu/elementa/article-pdf/{id}` |
| `zenodo` no DOI | Zenodo | extrai o `record_id` (`zenodo\.(\d+)`), consulta `https://zenodo.org/api/records/{id}`, itera `files[]` por `.pdf` |

Para adicionar uma nova editora: acrescente um `if dl.startswith("10.xxxx/")` em `try_publisher_patterns` (`scripts/baixar_pdfs.py`), seguindo o mesmo padrão das existentes.

## Casos sem solução programática conhecida

Categorias que já apareceram nos dois protocolos de origem — quando um paper cai numa delas, marque como pendência de checagem manual em vez de insistir automaticamente:

- **Paywall definitivo sem versão OA**: Elsevier e Emerald na maioria dos casos — sem entrada no Unpaywall/OpenAlex/S2/CORE e sem PDF acessível via editora.
- **Gold OA bloqueado para acesso programático**: alguns artigos ScienceDirect/UCPress retornam 403 mesmo sendo formalmente open access — só acessível manualmente pelo navegador.
- **Repositórios com login institucional**: bitstreams que exigem autenticação (ex. teses com embargo parcial).
- **DNS quebrado**: alguns repositórios universitários (ex. subdomínios `*.brage.unit.no`) ficam fora do ar — o Wayback é a única chance, e nem sempre tem snapshot.
- **Certificado autoassinado**: alguns repositórios (ex. Kent Academic Repository) usam certificados que o Python rejeita por padrão — `fetch()` já tenta `verify=False` como segunda tentativa automática quando a primeira falha por erro de SSL.
- **Arquivo suplementar, não o texto principal**: DOIs com sufixo `.s002`/`.s003` costumam apontar para dados suplementares em ZIP, não o PDF do artigo — checar se existe um DOI "principal" do trabalho, diferente do DOI do material suplementar.
- **Registro Zenodo/repositório privado ou restrito**: a API responde, mas os arquivos não estão publicamente acessíveis.

## Geração de chave (nome de arquivo)

A chave de cada paper é derivada do conteúdo (sobrenome do primeiro autor + ano; ou do próprio DOI quando não há autor/ano disponível) — nunca da posição na planilha, então reordenar linhas não confunde o script. Isso também é o que garante idempotência: pedir o mesmo paper de novo gera a mesma chave e bate no mesmo arquivo (`ja_existia`).

O algoritmo mora em `scripts/chave.py`, cópia idêntica (mesmo sha256) da usada por `gerar-bibtex`, `fichamento-sistematico` e `revisao-sistematica` — não edite só uma cópia. Ele reconhece listas de autores separadas por `|`, `;`, ` and ` ou vírgula, remove iniciais (`Weihs M.` → `Weihs`), sufixos (`Filho`, `Jr`) e partículas iniciais (`van Eck` → `Eck`), usa `Anon` sem autor e `sd` sem ano, e desempata com `a`…`z`, `aa`, `ab`…. Uma chave vinda da planilha (`chave`/`citekey`/`bib_key`) só é aceita se for válida como nome de arquivo e citekey; senão o script avisa e gera outra.

**Limitação conhecida**: dois papers diferentes do mesmo primeiro autor no mesmo ano, sem uma coluna `chave`/`--chave` explícita, colidem na mesma chave (`Silva2023`, `Silva2023a`, ...) — no modo `batch` a dedup dentro da própria planilha evita a colisão automaticamente; no modo `single`, chamado avulso mais de uma vez para autores/anos coincidentes, pode ser necessário passar `--chave` manualmente para desambiguar.

**Importante**: esse sufixo `a`/`b`/... é *só* anticolisão de nome de arquivo — o
`gerar_chave` não sabe e não checa se as duas linhas são o mesmo trabalho. Isso é
justamente o que `avisar_titulos_duplicados` (chamado no início de `main_batch`, antes
de processar qualquer linha) tenta cobrir: avisa quando duas linhas da planilha de
entrada têm título idêntico ou quase idêntico, o que é comum quando a planilha vem de
uma API tipo OpenAlex — pode ser o mesmo trabalho indexado duas vezes, ou um par
preprint/versão publicada com DOIs diferentes. O aviso não bloqueia nada (às vezes as
duas versões são mesmo o que se quer); só existe pra não passar batido — ver a etapa 8
acima para por que isso importa na hora de mesclar achados de agente de volta ao
relatório.
