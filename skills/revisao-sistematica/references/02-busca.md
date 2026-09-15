# Busca: strings, fontes, validação e log (etapa 4, portão G3)

Prefixo: `$RS` abrevia `python3 "<pasta da skill>/scripts/rs.py"` (SKILL.md, "Como chamar os comandos"): em cada chamada de Bash, use a função `rs` definida na mesma chamada ou o caminho completo, nunca uma variável `RS`. Pré-condição: protocolo aprovado no G2 (a busca definitiva nunca começa antes). Exceção: pedido "só as strings" (seção 13).

## Sumário

1. Arquivos e identificadores
2. Regras da estratégia
3. Passo a passo
4. Sintaxe por base e formatos que o importador reconhece
5. OpenAlex pela skill
6. Literatura cinzenta brasileira e outros métodos
7. Estudos-âncora e recall relativo
8. Revisão por pares (PRESS 2015)
9. Log PRISMA-S
10. Bola de neve e alerta de outros métodos
11. Atualização e alertas
12. Portão G3
13. Pedido parcial "só as strings"
14. Armadilhas

## 1. Arquivos e identificadores

| Arquivo | Conteúdo |
|---|---|
| `00-protocolo/ancoras_validacao.csv` | âncoras de validação (congeladas no G2; o coordenador não abre) |
| `01-busca/ancoras_desenvolvimento.csv` | âncoras de desenvolvimento (modelo `assets/templates/ancoras.csv`) |
| `01-busca/strings/termos_vN.md` | tabela de termos: uma linha por conceito, colunas PT, EN, ES, siglas, programas e leis |
| `01-busca/strings/desenvolvimento.csv` | `versao,base,data,mudanca,motivo,n,ancoras_dev_recuperadas` (uma linha por versão testada) |
| `01-busca/strings/<string_id>.txt` | string exatamente como executada, copiada do histórico da base (ex.: `S-scopus-v2.txt`) |
| `01-busca/press_<string_id>.md` | relatório PRESS (seção 8) |
| `01-busca/log_buscas.csv` | log PRISMA-S (modelo `assets/templates/log_buscas.csv`; nenhum comando o escreve) |
| `01-busca/brutos/` | exportações sem edição (o `importar` copia para cá e recusa bruto alterado) |
| `01-busca/cinzenta/<busca_id>/` | cópias locais dos documentos de sites (páginas somem) |
| `01-busca/filtros_v1.json` | funil formal (modelo `assets/templates/filtros_v1.json`), usado aqui para o recall e na etapa 5 |
| `01-busca/recall_ancoras.json` | recall relativo das âncoras, gerado por `filtrar --ancoras` (seção 7) |

O G3 congela `01-busca/strings/**` e `01-busca/filtros_*.json`: depois dele, mudar string ou filtro é emenda.

`--busca-id` precisa casar com `^[A-Z]{1,4}\d{1,4}$` (a mesma regra vale em `importar`, `buscar openalex` e `bola-de-neve`, conferida antes de qualquer chamada à API); o prefixo define `metodo_identificacao` (e o ramo do PRISMA): `B01...` bases e registros (`base`); `SN1...` busca por citação (`citacao`); `CZ1...` sites, repositórios, Google Scholar (`cinzenta`); `MN1...` contato com autores e listas manuais (`manual`); outros prefixos contam como `base`, salvo `--metodo`. Um id por execução de uma estratégia numa fonte; partes da mesma exportação (WoS exporta 1.000 por arquivo) usam o mesmo id. Busca é imutável: nova execução ou nova string = novo id; a busca superada sai do fluxo com `importar --substituir` ou `buscar openalex --substituir` (seção 3, passo 13).

## 2. Regras da estratégia

| Decisão | Regra padrão | Exceção (justificar no protocolo ou emenda e testar com âncoras) |
|---|---|---|
| Conceitos | P ou contexto AND I; comparador quase nunca | incluir O só se as âncoras de desenvolvimento mostrarem que o bloco não derruba estudos |
| Pergunta mista (efeito + mecanismo, percepção, implementação) | dois fios unidos por OR: P AND I AND O; P AND I AND termos de percepção/implementação | pergunta só de efeito |
| Termos no bloco | sinônimos, grafias, siglas, nomes de programas e leis em PT, EN e ES, unidos por OR; termos de desenho a partir de `assets/dicionarios/metodo_pt_en_es.csv` (grupos `causalidade`, `experimental`, `quantitativo`, `qualitativo`, `misto`) quando pertinentes | — |
| NOT | não usar | só com teste registrado mostrando que nenhuma âncora sai |
| Frases e proximidade | aspas para expressões fixas; proximidade quando a ordem varia | base sem proximidade: frase ou AND |
| Truncamento | radical longo o bastante, testado; nunca onde a base não aceita | escrever variantes |
| Siglas ambíguas | só amarradas ao tema por proximidade ou AND | sigla exclusiva do tema |
| Campos | título, resumo e palavras-chave | texto completo só com justificativa e teste de precisão |
| Idioma, data, tipo, área da base | sem limites na base; idioma e tipo se aplicam na triagem; marco temporal: buscar a partir de data anterior ao marco | justificar e registrar em `limites` do log |
| Fontes | ≥ 2 bases + base regional (SciELO) + teses (CAPES ou BDTD) + cinzenta pertinente + citações | revisão rápida: combinadas no G1 |
| Google Scholar | nunca fonte principal; via Publish or Perish, com número triado por consulta fixado antes | — |
| IA para termos | sugere sinônimos, traduções e estrutura; cada termo passa por verificação de sentido, contagem e âncoras de desenvolvimento; nunca é fonte de registros | — |
| Parada da iteração | quando novos termos não trazem relevantes e retirar termos passa a perder relevantes | — |

## 3. Passo a passo

1. `$RS status` (etapa atual `04_busca`). Releia no protocolo: conceitos, critérios, fontes com `busca_id`, rascunho de string.
2. Âncoras: confirme que `00-protocolo/ancoras_validacao.csv` existe (sem abrir). Monte `01-busca/ancoras_desenvolvimento.csv` com estudos já conhecidos e da busca exploratória; para cada âncora, verifique por título ou DOI em cada base prevista e anote `indexada_em` com o nome das bases separados por `|` (`openalex|scopus|wos`), ou `nenhuma`. Use o nome da base, não o `busca_id`: o id muda quando a busca é substituída (busca de teste com `--max-paginas`, string corrigida) e o arquivo de validação fica congelado desde o G2. A verificação de indexação das âncoras de validação é feita pelo mesmo terceiro que as montou.
3. Tabela de termos `01-busca/strings/termos_v1.md` (PT, EN, ES).
4. Base principal, v1 = P AND I. Rode, anote a contagem e as âncoras de desenvolvimento recuperadas em `desenvolvimento.csv`; examine uma amostra dos resultados para achar ruído (siglas, truncamentos amplos) e termos ausentes; itere até a regra de parada. No OpenAlex, conte com `$RS buscar openalex --query '<string>' --contar` e veja uma amostra com `--busca-id EXn --listar 50` (seção 5), sem importar.
5. PRESS da estratégia da base principal ANTES de traduzir (seção 8). O G3 bloqueia sem `01-busca/press_*.md` ou sem a pendência `revisao_press` aberta, e a `proxima_acao` do `status` pede o PRESS antes do G3. Checkpoints: pare e peça ao usuário quem revisa; o revisor registra `01-busca/press_<string_id>.md`. Autopiloto: `$RS pendencia abrir --tipo revisao_press --etapa 04_busca --portao G3 --descricao "PRESS de <string_id> por revisor humano" --arquivo 01-busca/strings/<string_id>.txt` e siga.
6. Traduza para cada base mantendo a lógica (seção 4); salve cada string em `01-busca/strings/<string_id>.txt`; conte antes de exportar e compare com versões anteriores (salto sem mudança na string = erro de digitação ou mudança na interface).
7. Bases por assinatura (WoS, Scopus): o usuário executa e exporta; passe a ele a string exata, o campo, o formato de exportação da seção 4 e a instrução "exporte todos os registros com resumo; não edite o arquivo". Peça também a data de execução, a contagem exibida pela base, a plataforma, os limites aplicados na interface e a string copiada do histórico da base.
8. Formato desconhecido: `$RS importar --arquivo <arquivo> --simular` (não grava; mostra a detecção e uma amostra). Planilha sem assinatura: `--fonte generico` (apelidos) ou `--mapa mapa.json`.
9. Importação, com os metadados PRISMA-S: `$RS importar --arquivo <arquivo> --busca-id B01 --estrutura PICOC --string-id S-scopus-v2 --executada-em 2026-03-20 --n-base 812 --filtros-na-base "nenhum" --plataforma "Scopus (Elsevier)"`. Os metadados vão para `estado.buscas` e para o evento `busca_registrada` (se `01-busca/strings/<string_id>.txt` existir, ele entra como artefato). Anote do resumo: `formato`, `n_importados`, `n_busca`, `sha256`, `n_sem_resumo`, `n_retratados`, `busca_registrada`, `metadados_declarados`, `avisos` (inclusive a diferença entre `--n-base` e o importado). Mesmo arquivo em outro id é recusado (código 1); bruto alterado depois de importado é recusado; metadado já registrado com outro valor é recusado (código 1). Esqueceu um metadado: repita o mesmo comando com ele (completa a busca sem acrescentar linhas). Em busca criada por `buscar openalex`, `--n-base` é conferido com `n_api` (o total que a API informou), não com `n_bruto` (o baixado): igual, é aceito sem gravar nada (aviso e `n_base_openalex` no resumo); `n_api` nulo, o valor é gravado; diferente, código 1 com a explicação de `n_api`, `n_bruto` e truncagem. Em geral não é preciso passar `--n-base` numa busca do OpenAlex.
10. OpenAlex: `$RS buscar openalex --busca-id B04 --query '<string>' --string-id S-oa-v1 --estrutura PICOC` (seção 5). O resumo traz `busca_registrada: true`, `evento_busca_registrada_seq` e `busca_registrada_agora` (false numa reexecução que reaproveitou o evento).
11. Literatura cinzenta e outros métodos (seção 6).
12. Validação por âncoras, na pasta da revisão: `$RS dedup`; se ainda não existir, `cp "<pasta da skill>/assets/templates/filtros_v1.json" 01-busca/filtros_v1.json` e ajuste ao protocolo (tudo em modo `etiquetar`); então `$RS filtrar --config 01-busca/filtros_v1.json --ancoras 00-protocolo/ancoras_validacao.csv` e leia o recall (seção 7).
13. Âncora indexada e não recuperada → diagnosticar o bloco ou termo, corrigir a string (nova versão em `01-busca/strings/`; emenda se a estratégia estava no protocolo), executar de novo com id novo e importar a nova exportação substituindo a antiga: `$RS importar --arquivo <exportação nova> --busca-id B06 --string-id S-scopus-v3 --executada-em AAAA-MM-DD --n-base N --substituir B02 --motivo "âncora A07 perdida na v2"`. No OpenAlex, num comando só: `$RS buscar openalex --busca-id B07 --query '<string nova>' --string-id S-oa-v2 --substituir B04 --motivo "âncora A07 perdida na v1"` (a validação da substituição roda antes de qualquer chamada à API; a substituição só é aplicada depois que a busca nova foi importada e registrada; reexecutar volta com `ja_aplicada`; vale também com `--sem-importador`; `--contar` e `--listar` recusam `--substituir`). Numa busca já baixada, `$RS importar --arquivo 01-busca/brutos/B07_openalex.jsonl --busca-id B07 --substituir B04 --motivo "..."` só aplica a substituição. A busca antiga fica com `ativa: false`, `substituida_por` e `motivo_substituicao` e o log ganha `busca_substituida`; suas linhas continuam em `dados/registros.csv`, mas `dedup` (flag `busca_inativa`), `filtrar`, o recall, o `status` e o `prisma` a ignoram, e `importar`, `buscar` e `bola-de-neve` a recusam. Rode `dedup` e o passo 12 de novo. Faça isso antes do G3.
14. Preencha uma linha de `01-busca/log_buscas.csv` por execução definitiva, inclusive as com zero resultados e as substituídas (seção 9). Contagens vêm do resumo dos comandos e da base, nunca estimadas.
15. `$RS status` (confira `alertas` de busca sem data) e portão G3 (seção 12).

## 4. Sintaxe por base e formatos que o importador reconhece

Confira a ajuda da interface na data da busca e anote a data da documentação consultada em `observacoes` do log.

| Fonte | Campo | Frase e proximidade | Truncamento | Exporte como | Detectado como (`formato`) |
|---|---|---|---|---|---|
| Web of Science Core Collection (Clarivate) | `TS=` | aspas; `NEAR/x` (padrão 15) | `*` com ≥ 3 caracteres antes | Texto sem formatação, registro completo (`savedrecs.txt`); ou delimitado por tabulação; ou BibTeX; ou Excel | `wos_txt` / `wos_tsv` / `wos_bib` / `wos_xls` |
| SciELO Citation Index (plataforma WoS) | `TS=` | sintaxe WoS | sintaxe WoS | texto ou tabulação da plataforma WoS; relatar "SciELO Citation Index, plataforma Web of Science" | `wos_txt`/`wos_tsv`; registros `UT SCIELO:` entram como `fonte=scielo` (ou force `--fonte scielo`) |
| SciELO (search.scielo.org) | conferir ajuda | conferir | conferir | CSV do portal (sem resumo, DOI e tipo: ficam sem dado) | `scielo_csv` |
| Scopus (Elsevier) | `TITLE-ABS-KEY()` | aspas retas = frase aproximada; `{}` = exata; `W/n`, `PRE/n` | `*` (literal dentro de `{}`) | CSV com resumo, palavras-chave e "Author full names"; ou RIS | `scopus_csv` / `ris` (com `DB  - Scopus`) |
| OpenAlex | `title_and_abstract.search` (padrão da skill) | aspas; `"a b"~N`; `NEAR` NÃO é operador | curinga só no campo exato (seção 5) | JSONL pela skill; CSV da interface web | `openalex_json` / `openalex_csv` |
| Google Scholar via Publish or Perish | registro inteiro | aspas; sem proximidade | não existe (escrever variantes); consulta > ~250 caracteres é cortada | CSV do PoP (resumo é trecho: `resumo_truncado=1`); guarde a consulta efetivamente enviada | `pop_csv` |
| Catálogo de Teses CAPES (dados abertos) | filtrar título e resumo localmente, com fronteira de palavra | — | — | CSV dos dados abertos (`;`, latin-1 aceitos) ou tabela do `capesR`; relatar "Catálogo de Teses e Dissertações da CAPES", nunca "BDTD"; conferir a cobertura real de anos | `capes_csv` / `capesr` |
| BDTD (IBICT) | busca avançada | conferir ajuda | conferir | CSV da exportação ou JSON da API VuFind | `bdtd_csv` / `bdtd_json` |
| Portal de Periódicos CAPES | não é base: relatar a base acessada | da base | da base | da base | da base |
| EconLit, SSRN, RePEc, LILACS, PubMed | conforme ajuda (vocabulário controlado onde houver) | conforme ajuda | conforme ajuda | RIS ou BibTeX | `ris` / `bibtex` |
| Zotero (listas manuais, sites salvos) | — | — | — | CSV do Zotero ou RIS | `zotero_csv` / `ris` |
| Planilha própria (cinzenta, contatos) | — | — | — | CSV/XLSX com `titulo, autores, ano, doi, resumo, url, tipo, veiculo` | `generico` (apelidos) ou `--mapa` |

`--mapa mapa.json`: `{"fonte": "generico", "planilha": "Plan1", "separador_autores": ";", "colunas": {"titulo": "Title", "autores": "Authors", "ano": "Year", "doi": "DOI", "resumo": "Abstract", "palavras_chave": ["Author Keywords", "Keywords"]}}` (chaves = colunas de `dados/registros.csv`).

## 5. OpenAlex pela skill

| Situação | Comando ou regra |
|---|---|
| Contar (sem projeto) | `$RS buscar openalex --query '<string>' --contar` |
| Ver os primeiros resultados sem importar | `$RS buscar openalex --busca-id EX2 --query '<string>' --listar 50` → `00-protocolo/exploracao_EX2.csv` (não registra busca; ids `EXn` para não confundir com buscas) |
| Coletar e importar | `$RS buscar openalex --busca-id B04 --query '<string>' --string-id S-oa-v1 [--estrutura PICOC]`; grava `01-busca/brutos/B04_openalex.jsonl` e `B04_openalex.consulta.json` e registra `busca_registrada` |
| Campo | padrão `title_and_abstract` (equivale a TITLE-ABS, com stemming); `--campo title`, `abstract`; `--campo search` inclui texto completo: só com justificativa; `--campo title_and_abstract.search.exact` (e `title.search.exact`, `abstract.search.exact`): sem stemming, aceita curinga e frase palavra por palavra |
| Vírgula na string | recusada (a API usa vírgula como separador de filtros): retire-a; `--campo search` aceita, mas muda o campo |
| Truncamento | `*` e `?` no campo padrão dão erro HTTP 400 (inclusive dentro de frase entre aspas; a mensagem de erro sugere o campo exato). Use `$RS buscar openalex --busca-id B04 --campo title_and_abstract.search.exact --query 'amnest* AND tax*' --string-id S-oa-v1`. Sem stemming, liste as variantes que o curinga não cobre; compare com `--contar` nos dois campos antes de congelar a string. Nunca misture na mesma busca termos com e sem stemming sem registrar. A API muda: confira o comportamento dos campos exatos com `--contar` na data da busca |
| Proximidade | `"termo1 termo2"~N`; operadores AND, OR, NOT em maiúsculas |
| Filtros da API | `--filtro "publication_year:2000-2026,type:article"` só se previsto como limite (registrar em `limites`) |
| String longa | URL tem limite (~4 KB): divida em buscas com ids distintos e registre as duas |
| `--max-paginas N` | só para testar; marca `truncada` e não serve para o PRISMA. Enquanto a busca truncada estiver ativa: alerta `busca_truncada` e rascunho no `status`; o G3 bloqueia (tipo limiar; só humano segue com `--forcar --motivo`); o `prisma` avisa, sai como rascunho e mostra "Buscas truncadas: B04" no SVG e no Mermaid (a lista entra nos insumos, então trocar a busca invalida o PRISMA aprovado no G9). Saída: rode a busca inteira com id novo e `--substituir` a truncada; o `status` (em `proxima_acao` e no `comando` do alerta) já sugere `buscar openalex --busca-id <novo busca_id> --query '<a mesma>' --campo ... --string-id ... --substituir B04 --motivo "..."` com a consulta registrada no estado (troque `<novo busca_id>`); `importar --substituir` fica para exportações manuais |
| Reexecução | mesmo id e mesma consulta: reusa o JSONL sem rede; consulta diferente com o mesmo id é recusada; busca substituída (`ativa: false`) é recusada |
| String corrigida depois do teste de âncoras, ou busca truncada | id novo e `buscar openalex --busca-id <id novo> --query '...' --substituir <id antigo> --motivo "..."`; bruto já baixado: `importar --arquivo 01-busca/brutos/<id>_openalex.jsonl --busca-id <id> --substituir <id antigo> --motivo "..."` (seção 3, passo 13) |
| `--n-base` em busca do OpenAlex | conferido com `n_api` (seção 3, passo 9); não use o número de registros baixados |
| Credenciais | `RS_EMAIL` (fila educada, recomendada) e `OPENALEX_API_KEY` por variável de ambiente |

## 6. Literatura cinzenta brasileira e outros métodos

| Fonte | Tipo | `--busca-id` | Como executar e registrar |
|---|---|---|---|
| Repositório do IPEA | instituto federal | `CZ1` | termos simplificados, coleções percorridas, data, N triado; lista em planilha → `importar --fonte generico` |
| TCU e CGU (repositório da CGU) | controle e auditoria | `CZ2` | idem, com o tipo de documento pesquisado |
| Ministérios, institutos estaduais, Enap e escolas de governo, repositórios universitários | governo, teses, relatórios | `CZ3...` | URL da seção, caminho de navegação, cópia local em `01-busca/cinzenta/<id>/` |
| FGV e outros think tanks | institutos | `CZ...` | idem |
| Banco Mundial (Open Knowledge Repository), BID, OCDE, ONU, FAO | organismos internacionais | `CZ...` | string e filtros da interface |
| 3ie Development Evidence Portal | avaliações de impacto e revisões | `CZ...` | string e filtros |
| Overton | documentos de política | `CZ...` | string, filtros, data |
| OSF Preprints e registros | não publicados e em andamento | `CZ...` | termos e data |
| Google Scholar via Publish or Perish | buscador | `CZ...` | uma consulta curta por idioma; N máximo fixado antes (ex.: 200) e relatado como "triados", não como total |
| Redalyc, Dialnet, Redib, Sumários.org, DOAJ | produção latino-americana e lusófona | `B..` se houver exportação com string; `CZ..` se navegação | registrar a limitação de sintaxe booleana |
| Contato com autores e especialistas | outro método | `MN1` | depois das buscas iniciais, com a lista do que já foi achado; registrar quem (papel), quando e o que rendeu |

Para cada site registre em `log_buscas.csv`: fonte, URL, data, termos e limites, `caminho_navegacao` (menus, busca interna), filtros pré-definidos, `n_triado_corte`, `executado_por`.

## 7. Estudos-âncora e recall relativo

| Grupo | Origem | Uso permitido |
|---|---|---|
| Desenvolvimento (`01-busca/ancoras_desenvolvimento.csv`) | estudos já conhecidos, busca exploratória | colher termos; testar versões intermediárias |
| Validação (`00-protocolo/ancoras_validacao.csv`) | estudos incluídos em revisões anteriores, indicados por especialistas ou achados por citação independente, conferidos contra os critérios | só o teste final; quem escolhe termos não lê seus títulos e resumos |

Colunas do modelo: `id,grupo,doi,titulo,ano,primeiro_autor,origem,elegibilidade_conferida_por,indexada_em,observacao`. `filtrar` casa por DOI normalizado ou título normalizado + ano (usa `id` como rótulo); apague as linhas `EX*`. `indexada_em`: nomes de fonte das buscas (`openalex|scopus|wos`, o recomendado) ou ids de busca (`B01|B02`), separados por `|`, `;` ou `,`; vazio ou `nenhuma` = âncora não indexada em nenhuma base (fica fora dos denominadores). O nome da base sobrevive a substituições; um id de busca substituída conta como a busca que a substituiu (`substituida_por` no estado), com aviso sugerindo o nome da base. O arquivo pode voltar do Excel (CSV com vírgula, ponto e vírgula ou tabulação; UTF-8, UTF-16 ou cp1252) ou em `.xlsx`.

Depois de cada importação (e de toda substituição), com `dedup` rodado: `$RS filtrar --config 01-busca/filtros_v1.json --ancoras 00-protocolo/ancoras_validacao.csv`. Código 2 = âncora excluída por filtro (troque o filtro para etiquetar). O resumo mostra `ancoras` por situação (`mantida`, `etiquetada`, `excluida`, `nao_encontrada`, `sem_chave_de_casamento`) e `recall_ancoras` compacto; o detalhe fica em `01-busca/recall_ancoras.json` (só ids de âncoras e de buscas, nunca títulos; o coordenador pode ler):

| Campo | Conteúdo |
|---|---|
| `combinado` | R_comb: âncoras achadas por pelo menos uma busca ativa de método `base`, sobre as indexadas; `n_ancoras`, `n_encontradas`, `recall`, `ic95` (Clopper-Pearson), `perdidas` |
| `combinado_todos_metodos` | idem, contando citação, cinzenta e manual |
| `por_busca` | R_b de cada busca ativa; com `indexada_em`, o denominador só tem as âncoras indexadas naquela busca ou fonte |
| `por_base` | R por item declarado em `indexada_em` (só com a coluna) |
| `nao_indexadas`, `avisos` | âncoras sem indexação declarada; `indexada_em` sem busca correspondente; âncora achada fora do declarado |

Âncoras de desenvolvimento servem para versões intermediárias conferidas na interface da base (anote em `desenvolvimento.csv`). Se rodar `filtrar --ancoras 01-busca/ancoras_desenvolvimento.csv`, rode depois de novo com o arquivo de validação: `recall_ancoras.json` guarda só a última execução (`ancoras_arquivo` diz qual).

| Resultado | Leitura | Ação |
|---|---|---|
| `combinado.perdidas` vazio | meta atingida | seguir |
| Âncora indexada e perdida | problema de estratégia | achar o bloco ou termo que a derrubou; corrigir; nova busca com `importar --substituir` ou `buscar openalex --substituir` (seção 3, passo 13) |
| `por_busca.<id>.recall` baixo com `combinado` alto | tradução ruim naquela base | revisar a tradução daquela base |
| Âncora em `nao_indexadas` | problema de fonte | considerar fonte adicional; relatar |

Referência de ordem de grandeza, não limiar: 95% de recall (nenhum código de saída depende dele; o G3 só avisa quando o arquivo falta, quando o recall combinado é menor que 1 ou quando foi calculado sobre outro `registros_unicos.csv`: leve os números aos critérios do portão). Relate R_comb e R_b com IC no material suplementar.

## 8. Revisão por pares (PRESS 2015)

1. Quando: estratégia da base principal pronta, antes de traduzir para as demais.
2. Quem: pessoa com experiência em busca que não escreveu a string (humano). Um subagente pode pré-revisar, mas não substitui: no autopiloto fica a pendência `revisao_press`.
3. Como: checklist `assets/checklists/press.csv` (primeira linha é atribuição; cabeçalho na linha 2; leitura em `assets/checklists/README.md`). Entregue ao revisor a pergunta, o framework, a tabela de termos, a string e as contagens por linha. Seis elementos: tradução da pergunta; operadores booleanos e de proximidade; vocabulário controlado (itens 3.x só em bases que o têm); texto livre; ortografia, sintaxe e linhas; limites e filtros.
4. Registre em `01-busca/press_<string_id>.md`: item | resposta (sim, não, não se aplica) | comentário | mudança feita; papel do revisor e data. Toda mudança gera nova versão da string.
5. Preencha `press_revisor` e `press_data` no log de cada busca derivada.
6. O G3 confere só a existência: `01-busca/press_*.md` ou a pendência `revisao_press` aberta (autopiloto). O conteúdo do relatório é conferência sua.

## 9. Log PRISMA-S

`01-busca/log_buscas.csv`: uma linha por execução. Checklist em `assets/checklists/prisma_s.csv` (primeira linha é atribuição).

| Item PRISMA-S | Colunas do log |
|---|---|
| 1 Nome da base e plataforma | `fonte`, `plataforma` (`importar --plataforma`) |
| 2 Busca multibase | `bases_na_plataforma` |
| 3 Registros de estudos | `tipo_fonte=registro` |
| 4 Recursos on-line e navegação | `tipo_fonte=site`, `url_interface`, `caminho_navegacao`, `n_triado_corte` |
| 5 Busca por citações | `metodo=citacao`, `sementes`, `indice_citacao` |
| 6 Contatos | `tipo_fonte=contato` (`metodo=manual`) |
| 7 Outros métodos | `tipo_fonte=outro` |
| 8 Estratégias completas | `string_id` (`importar --string-id`), `arquivo_string` |
| 9 Limites e restrições | `limites` (`importar --filtros-na-base`), `justificativa_limites` |
| 10 Filtros de busca publicados | `filtro_publicado` |
| 11 Trabalhos anteriores | `origem_estrategia` |
| 12 Atualizações | `atualizacao_de`; busca substituída: `observacoes` = "substituída por <id>: <motivo>" |
| 13 Datas das buscas | `data_execucao` (`importar --executada-em`) |
| 14 Revisão por pares | `press_revisor`, `press_data` |
| 15 Total de registros | `n_resultados_base` (`importar --n-base`), `n_exportado`, `n_importado` (do resumo do `importar`), `arquivo_bruto`, `sha256_bruto` |
| 16 Deduplicação | não fica no log: relatar pelo evento `dedup_executado` e `01-busca/dedup_pares.csv` |

`metodo` segue o `--metodo` do importador (`base|citacao|cinzenta|manual`). `executado_por` e `press_revisor` são papéis. O estado guarda, para toda busca (`importar` com as flags PRISMA-S, `buscar openalex`, `bola-de-neve`), `string_id`, `executada_em` (com `executada_em_origem` = `arquivo` ou `declarada`), `n_bruto`, `filtros_na_base`, `plataforma` e, nas substituídas, `ativa: false`, `substituida_por`, `substituida_em` e `motivo_substituicao`. Nenhum comando escreve `log_buscas.csv`: copie esses valores do estado e dos resumos e preencha à mão as demais colunas.

## 10. Bola de neve e alerta de outros métodos

Acontece na etapa 7, depois da elegibilidade em texto completo:

1. `$RS bola-de-neve --direcao ambas --rodada SN1` (sementes = incluídos no texto completo; `--ids <csv com id_rs>` para rodadas seguintes sobre os novos incluídos). Revisões achadas na busca entram como sementes, nunca como estudos.
2. `$RS dedup`, triagem T/A dos novos registros com a MESMA versão dos critérios, texto completo.
3. Nova rodada (`SN2`...) enquanto houver novos incluídos; registre cada rodada no log com `sementes` e `indice_citacao=OpenAlex`.
4. `textos elegibilidade consolidar` avisa quando mais de 30% dos incluídos vieram só de outros métodos. Acima de 25-30%: verifique se esses estudos estão indexados nas bases e que termos usam; se a string falhou, emenda e reexecução.

## 11. Atualização e alertas

| Situação | Ação |
|---|---|
| Última busca com mais de 12 meses (de preferência 6) na data prevista de publicação | reexecutar todas as fontes com novos ids (`B11`, `B12`...), `atualizacao_de` apontando o id original; as buscas antigas continuam ativas (atualização não é substituição) e a sobreposição sai no `dedup`; triar o que for novo |
| Não dá para incorporar a tempo | relatar estudos novos como "aguardando classificação" |
| Alertas salvos nas plataformas | registrar plataforma e string do alerta em `observacoes`; resultados entram como nova busca |
| Sintaxe mudou entre execuções | relatar a original e a nova (PRISMA-S item 12) |

`$RS status` lista em `alertas` as buscas ativas com mais de 12 meses (`busca_desatualizada`, com `dias`) e as sem data (`busca_sem_data`: complete com `importar --executada-em`); o G9 repete os mesmos alertas como `avisos`. Nenhum dos dois bloqueia: a decisão de atualizar é humana.

## 12. Portão G3

O G3 exige (mostrar ao usuário em checkpoints; conferir no autopiloto):

- linha no log para toda fonte do protocolo, inclusive as com zero resultados, e nenhuma fonte prevista sem execução (senão emenda);
- `n_importado` coerente com `n_exportado` e com `--n-base` (diferença explicada: corte de 1.000 do Scholar, registros vazios descartados, exportação em partes);
- nenhuma busca `truncada` (bloqueio do script); toda busca ativa com `string_id` e `executada_em` (nenhum `alertas` do `status`);
- buscas superadas substituídas (`contagens.buscas_inativas` do `status`), com motivo;
- strings exatas em `01-busca/strings/`, PRESS registrado (ou pendência `revisao_press` no autopiloto);
- recall das âncoras de validação em `01-busca/recall_ancoras.json`: `combinado` e `por_busca`, com diagnóstico de cada perdida;
- estratégias coerentes com as exclusões do protocolo (termos de algo excluído geram ruído previsível);
- datas de execução com menos de 12 meses.

Comando (após "aprovo" em checkpoints): `$RS portao G3 --aprovar --por revisor_humano_1 --criterios '{"fontes": 7, "recall_ancoras": 1.0, "ancoras_indexadas": 12, "press": true, "log_prisma_s": "01-busca/log_buscas.csv", "recall_arquivo": "01-busca/recall_ancoras.json"}'`, com os números conferidos nos arquivos. A `proxima_acao` do `status` traz `"recall_ancoras": <valor de 01-busca/recall_ancoras.json>` e `"press": <press: true só com revisão humana registrada>`, com o recall lido na `descricao`: troque os placeholders, nunca os copie. Autopiloto: `--por autopiloto` com os mesmos critérios.

O script barra (código 2) se: não houver busca ativa, bruto ou `registros.csv` (artefato); houver busca ativa truncada (limiar: barra também o autopiloto; humano só com `--forcar --motivo`); não houver PRESS registrado, isto é, nenhum `01-busca/press_*.md` nem pendência `revisao_press` aberta (artefato). Sobre o recall ele só avisa (em `avisos`): sem `01-busca/recall_ancoras.json`, com `combinado.recall` < 1 (lista `combinado.perdidas`) ou com o recall calculado sobre outra versão de `registros_unicos.csv` (rode `filtrar --ancoras` de novo). O conteúdo do PRESS, a indexação das âncoras, o log PRISMA-S e a comparação dos filtros com o protocolo não são conferidos (a lista acima é sua). Ao aprovar, congela `01-busca/strings/**` e `01-busca/filtros_*.json`.

## 13. Pedido parcial "só as strings"

Sem projeto (a menos que o usuário peça): entrevista curta de X, Y, contexto e idiomas (leia também references/01-pergunta-protocolo.md, seção 2); tabela de termos PT/EN/ES; blocos da seção 2; tradução por base da seção 4; contagens com `$RS buscar openalex --query '...' --contar`; entregue strings por base, formato de exportação, a lista de verificações do PRESS e o aviso de que a validação por âncoras e o log PRISMA-S ficam a cargo do usuário.

## 14. Armadilhas

| Armadilha | Consequência | Evite |
|---|---|---|
| Uma base, um idioma | produção lusófona invisível | SciELO, teses e repositórios brasileiros como componentes |
| Strings não equivalentes entre bases | sensibilidade diferente por base | tradução a partir da mesma tabela de termos; PRESS antes de traduzir |
| Blocos demais (desfecho, país) | estudos que não citam o conceito no resumo somem | testar cada bloco com âncoras de desenvolvimento; fio sem o bloco |
| NOT e filtros de área | exclusão silenciosa | não usar; se usar, testar e registrar |
| Truncamento curto (`ban*`, `class*`) ou onde não existe | ruído ou termo que não funciona | variantes por extenso; conferir amostra |
| String redigitada ou reescrita pela ferramenta | não reprodutível | copiar do histórico; guardar a consulta enviada (PoP) |
| Âncoras usadas para escolher termos | validação circular | dois arquivos; o de validação só para o script |
| Validação invertida (achados estão nas revisões?) | não mede recall | recall das âncoras de validação |
| Outros métodos fora do ledger | PRISMA sem lastro, duplicatas | todo registro entra por `importar` ou `bola-de-neve` com `busca_id` |
| Busca exploratória importada | identificados inflados | só `--contar` e `--listar` |
| String corrigida importada ao lado da antiga | identificados inflados; recall calculado com a busca errada | `importar --substituir <id antigo> --motivo "..."` (ou `buscar openalex --substituir`) |
| Busca de teste (`--max-paginas`) deixada ativa | identificados subcontados; G3 bloqueado e PRISMA em rascunho | rodar a busca inteira com id novo e `--substituir` a truncada |
| Copiar `"press": true` da `proxima_acao` sem PRESS feito | log registra uma revisão por pares que não houve | `press_<string_id>.md` do revisor humano (ou pendência `revisao_press`) antes do G3 |
| Exportação manual sem data nem string | PRISMA-S incompleto; alerta `busca_sem_data` | `importar --string-id --executada-em --n-base --filtros-na-base --plataforma` |
| Portal CAPES ou "BDTD" relatado no lugar da base real | leitor procura na fonte errada | relatar base e plataforma efetivas |
| Lista de estudos gerada por chatbot | referências inventadas | IA nunca é fonte de registros |
| Bibliometria como filtro | exclusão sem critério | só exploratória |
