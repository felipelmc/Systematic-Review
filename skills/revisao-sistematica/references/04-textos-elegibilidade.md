# Textos completos e elegibilidade (etapa 7, portão G5)

Leia também `references/ia-validacao.md` (passo H: o LLM propõe, o humano decide).

## Sumário

1. Entradas, saídas e ordem
2. Lista para baixar e handoff para `baixar-pdfs-academicos`
3. Inventário e verificação de conteúdo
4. Não recuperados e contato com autores
5. Retratações
6. Elegibilidade via `fichamento-sistematico`
7. Decisão humana e consolidação
8. Ligação de relatos
9. Bola de neve e re-triagem
10. Portão G5, armadilhas e relato

`$RS` abrevia `python3 "<pasta da skill>/scripts/rs.py"` (SKILL.md, "Como chamar os comandos"): em cada chamada de Bash, use a função `rs` definida na mesma chamada ou o caminho completo, nunca uma variável `RS`. Rode na raiz do projeto; `$RS status` no início e depois de cada onda de subagentes.

## 1. Entradas, saídas e ordem

| Passo | Comando ou skill | Produz |
|---|---|---|
| Lista | `$RS textos para-baixar` | `03-textos/para_baixar.csv` (`chave,titulo,autores,ano,doi,id_rs`) |
| PDFs | skill `baixar-pdfs-academicos` | `03-textos/pdfs/<chave>.pdf`, `03-textos/relatorio_pdfs.csv`, `03-textos/verificacao_conteudo.csv` |
| Inventário | `$RS textos inventario` (+ conferência humana em `03-textos/conferencia_pdfs.csv`) | `03-textos/inventario_textos.csv` (coluna `recuperado`, que o PRISMA conta) |
| Contato com autores | `$RS textos contato-autores --registrar <csv>` | `03-textos/contato_autores.csv`, evento `contato_autores` |
| Retratações | `$RS textos retratacoes` | `03-textos/retratacoes.csv`, evento `retratacoes_verificadas` |
| Elegibilidade | skill `fichamento-sistematico` + `$RS textos elegibilidade consolidar` | `03-textos/elegibilidade_tc_final.csv` |
| Decisão humana | `$RS triagem fila --etapa tc` → humanos preenchem → `$RS triagem override --fila 03-textos/fila_humana_tc.csv --etapa tc` → `textos elegibilidade consolidar` de novo | `03-textos/fila_humana_tc.csv` (evento `fila_gerada`), ledger, `elegibilidade_tc_final.csv` |
| Relatos | `$RS textos ligar-relatos` | `03-textos/ligacao_relatos.csv`, `id_estudo` |
| Bola de neve | `$RS bola-de-neve` → `dedup` → re-triagem | `01-busca/bola_de_neve/`, novos `id_rs` |

Junção sempre por `chave` (PDF, ficha, `.bib`) ou `id_rs`. `$RS ambiente` lista em `irmas_ausentes` as skills irmãs que faltam.

## 2. Lista para baixar e handoff para `baixar-pdfs-academicos`

1. `$RS textos para-baixar` (padrão `--decisoes incluir,incerto`; projeto parcial sem triagem: `--ids <csv com id_rs>`).
2. Invoque a skill `baixar-pdfs-academicos` com a planilha do projeto. Se rodar os scripts dela direto, `IRMA` é a pasta da irmã (procure em `<pasta da skill>/../baixar-pdfs-academicos`, depois `~/.claude/skills/baixar-pdfs-academicos`, depois `<pasta do projeto do Claude Code>/.claude/skills/baixar-pdfs-academicos`):

```bash
python3 "$IRMA/scripts/baixar_pdfs.py" batch --planilha 03-textos/para_baixar.csv --col-chave chave \
  --saida-pdfs 03-textos/pdfs --relatorio 03-textos/relatorio_pdfs.csv --email "$RS_EMAIL"
python3 "$IRMA/scripts/verificar_conteudo.py" --pdfs 03-textos/pdfs --relatorio 03-textos/relatorio_pdfs.csv
```

| Regra | Aplicação |
|---|---|
| E-mail | Só por `RS_EMAIL` (ou `PDF_DOWNLOADER_EMAIL`); sem ele, pergunte uma vez e não grave em arquivo |
| Sci-Hub | Esta skill não oferece; nunca passe `--scihub-dois` |
| Rodadas seguintes (bola de neve) | Regere a lista e acrescente `--apenas-pendentes` |
| Sobraram `nao_encontrado` | Ofereça os agentes de busca web da irmã; aplique com `python3 "$IRMA/scripts/mesclar_achados_agentes.py" --relatorio 03-textos/relatorio_pdfs.csv --achados 03-textos/achados_agentes.json --saida-pdfs 03-textos/pdfs` e rode `verificar_conteudo.py` de novo |
| Irmã ausente | Baixe à mão para `03-textos/pdfs/<chave>.pdf` e escreva `03-textos/relatorio_pdfs.csv` com as colunas `chave,titulo,autores,ano,doi,status,fonte,url,versao,motivo,arquivo` (`status` = `ok` ou `nao_encontrado`); confira título e autor de cada PDF à mão |

## 3. Inventário e verificação de conteúdo

`$RS textos inventario` → leia `n_recuperados`, `n_faltando`, `faltando`, `sem_texto`, `conferir_conteudo`, `existe_nao_recuperado`, `avisos`.

`recuperado` (coluna do inventário, que o PRISMA conta como relatório recuperado) = 1 quando o PDF existe e o veredito é `confere`, ou quando a conferência humana em `03-textos/conferencia_pdfs.csv` (`chave,recuperado,motivo`) diz 1; 0 nos demais casos. A conferência humana prevalece sobre o veredito. Relatório com `recuperado = 0` e decisão no texto completo quebra a invariante `avaliado_nao_recuperado` (G5 e `prisma` saem com 2).

| Situação | Ação |
|---|---|
| `veredito_conteudo = confere` | Segue |
| `suspeito` ou `conferir_a_mao` | Humano abre o PDF e confere título e autores antes de fichar; confere → linha `<chave>,1,"conferido por revisor_humano_1"` em `conferencia_pdfs.csv` e `textos inventario` de novo |
| `sem_camada_de_texto` ou `tem_texto = 0` | Leitura visual pelo subagente (páginas como imagem) e conferência humana (mesma linha em `conferencia_pdfs.csv`); o gate marcará `PDF_TEXTO_NAO_EXTRAIVEL` |
| `existe = 0` e `status = nao_encontrado` | Não recuperado (seção 4) |
| `existe = 0` e `status = ok` | Arquivo movido: recoloque em `03-textos/pdfs/<chave>.pdf` |
| PDF de outro trabalho | Mova para `03-textos/pdfs_descartados/`; busque a cópia certa (agentes, autor). Achou: salve como `<chave>.pdf`, rode `verificar_conteudo.py` e `textos inventario`. Não achou: linha `<chave>,0,"PDF de outro trabalho descartado"` em `conferencia_pdfs.csv` e `textos inventario` de novo; o relatório passa a "não recuperado" no PRISMA, mesmo com `status = ok` no relatório da irmã |

PDF válido não é PDF certo: nada é fichado antes desta conferência.

## 4. Não recuperados e contato com autores

- Todo relato buscado e não obtido fica `nao_encontrado` no relatório (ou `recuperado = 0` no inventário): é "relatos não recuperados" no PRISMA, nunca exclusão.
- Contate autores para: texto não localizado, dado essencial ausente, dúvida de elegibilidade que o texto não resolve, suspeita de relatos do mesmo estudo.
- Mantenha uma planilha de trabalho (ex.: `03-textos/contatos_trabalho.csv`) com as colunas do contrato `chave,autor_contatado,data,pedido,resposta,dados_recebidos` e registre-a a cada atualização: `$RS textos contato-autores --registrar 03-textos/contatos_trabalho.csv`. O comando valida (chave do projeto, `data` AAAA-MM-DD, `pedido` preenchido, `dados_recebidos` = `sim`, `nao`, `parcial` ou vazio = aguardando), recusa qualquer endereço de e-mail (código 1), grava a versão canônica em `03-textos/contato_autores.csv` e registra o evento `contato_autores` (lido no relato). Uma linha por contato. Canal, tentativas e motivo não têm coluna: escreva-os em `pedido` (ex.: "texto completo; e-mail; 2ª tentativa") ou deixe-os como colunas extras da planilha de trabalho, que o comando descarta da versão canônica com aviso. Prazo e número de tentativas vêm do protocolo.
- Mensagem mínima: quem são os revisores e a revisão (título e registro do protocolo); a referência completa; o pedido exato (texto, tabela, esclarecimento); prazo; como os dados serão usados e citados.
- Sem resposta até o G5: o relato segue não recuperado; dúvida de elegibilidade que o texto não resolve vira `aguardando` (aguardando classificação, Cochrane Handbook sec. 4.4.5) por decisão humana (seção 7). `aguardando` tem caixa própria no PRISMA e fica fora de incluídos e excluídos; `incerto` sem decisão humana continua impedindo o PRISMA.

## 5. Retratações

Quando: depois de `textos para-baixar` (todos os candidatos), de novo sobre os não excluídos antes do G5 e a cada rodada de bola de neve. Retratações aparecem com o tempo: toda execução é uma verificação datada.

1. `$RS textos retratacoes [--fonte openalex|crossref|ambas] [--ids <csv com id_rs>]` (padrão `ambas`; sem `--ids`, os textos não excluídos em `elegibilidade_tc_final.csv` ou, antes dela, os de `para_baixar.csv`). Consulta `is_retracted` no OpenAlex (por DOI ou id W) e os avisos que atualizam o DOI na Crossref (`filter=updates:<doi>`, que traz os dados do Retraction Watch). `RS_EMAIL` vai como mailto; `OPENALEX_API_KEY` só ao OpenAlex. Sem nenhuma resposta (rede), sai com código 1 e não grava.
2. Leia `retratados`, `expressao_preocupacao`, `sem_verificacao` e `avisos`. O arquivo `03-textos/retratacoes.csv` tem `chave,id_rs,doi,openalex_is_retracted,crossref_avisos,retratado,status,verificado_em` (`retratado` = 1, 0 ou vazio quando não deu para verificar; `status` = `ok`, `parcial`, `sem_doi`, `erro`, `nao_encontrado`).
3. Retratado (retratação, retirada ou remoção): o comando abre a pendência `retratacao_texto` (G5) em qualquer modo; decida com `triagem override --etapa tc` (seção 7) e rode `retratacoes` de novo, o que a fecha quando nenhum texto verificado segue retratado. Se um humano fechou a pendência (ex.: texto mantido com justificativa), ela não reabre nas verificações seguintes enquanto os mesmos textos seguirem retratados com as mesmas informações das fontes (assinatura `retratados_sha`, que ignora a data da verificação; o resumo traz `pendencia_conferida` e `conferencia_ja_feita`); um conjunto diferente de retratados, mesmo com o mesmo número, reabre.
4. O `importar` já guarda o `is_retracted` do OpenAlex em `dados/registros_flags.csv` e o `dedup` marca a flag `retratado`; o comando acima confere de novo e acrescenta a Crossref.

| Achado | Decisão | Registro |
|---|---|---|
| `retratado = 1` (`retraction`, `partial_retraction`, `withdrawal` ou `removal` na Crossref, ou `openalex_is_retracted = true`) | Excluir no texto completo; motivo = primeiro critério que falha na ordem (`c6_nao_retratado` se nenhum anterior falhar). Já extraído: retirar da síntese e relatar | `retratacoes.csv`; override `tc` (seção 7) |
| Correção ou errata (`correction:` em `crossref_avisos`) | Manter; extrair dos dados corrigidos | Nota na ficha |
| Expressão de preocupação (`expressao_preocupacao` no resumo) | Manter, sinalizar e prever sensibilidade sem o estudo | Relato e plano de síntese |
| `retratado` vazio (`status` `sem_doi`, `erro` ou `nao_encontrado`) | Não verificado: conferir por título no CSV aberto do Retraction Watch (Crossref) e no repositório de origem (teses, relatórios); não há comando para registrar essa conferência manual | Anote o resultado em `03-textos/retratacoes_conferencia_manual.csv` (`chave,fonte,resultado,verificado_em`) e no relato; `retratacoes.csv` é regravado a cada execução |
| Divergência OpenAlex × Crossref | Vale o aviso publicado; abra o DOI do aviso | Descrever no relato |

Normas: Cochrane Handbook, cap. 4, sec. 4.4.6 e MECIR C48 (examinar retratações e erratas).

## 6. Elegibilidade via `fichamento-sistematico`

1. O codebook de elegibilidade é parte do protocolo: `00-protocolo/codebook_elegibilidade.csv`, copiado de `assets/codebooks/elegibilidade_modelo.csv` e ajustado com o usuário antes do G2 (congelado com o protocolo; references/01-pergunta-protocolo.md, seção 10). Troque os `{...}` dos prompts e mantenha a ordem dos critérios do protocolo. Critério de desenho previsto no protocolo (ex.: SMS mínimo) entra nele, copiando `criterio_sms_minimo` e as variáveis `sms_*` de `assets/codebooks/desenho_maryland.csv`. Projeto antigo com o codebook em `03-textos/`: mova-o para `00-protocolo/` só por emenda.

| Regra do codebook | Por quê |
|---|---|
| Variáveis-critério com nome `c<n>_...` na dimensão `Criterios de elegibilidade` | `consolidar` detecta critério pelo nome ou pela dimensão; toda variável dessa dimensão vira critério |
| Demais variáveis em outras dimensões (`Identificacao`, `Ligacao de relatos`), sem nome `c<n>` | Não viram critério |
| Pergunta redigida para `Sim` = atende | A primeira palavra da resposta decide: `Sim` atende, `Não` falha, `999`/`parcial`/vazio = incerto |
| Ordem das linhas = ordem de aplicação | O primeiro `Não` vira `criterio_falhou` e motivo no PRISMA |
| Sem `aplicavel_se` | Uma ficha por texto |
| Mudança depois do G2 | Emenda (`$RS emenda --arquivo 00-protocolo/codebook_elegibilidade.csv --motivo "..."`) e refichar os afetados |

2. Invoque a skill `fichamento-sistematico` com: codebook `00-protocolo/codebook_elegibilidade.csv`; fichas em `03-textos/fichas_elegibilidade/`; PDFs pelo `03-textos/relatorio_pdfs.csv` (status ok, conferidos na seção 3); metadados de cada chave (título, autores, ano) de `para_baixar.csv` para a variável `texto_confere`. Um PDF por subagente, até 3 em paralelo, leitura em faixas de até 20 páginas cobrindo o documento inteiro. `citekey` = `chave`.
3. Gate e consolidação da irmã (`FICHA` = pasta da `fichamento-sistematico`, mesma ordem de busca da seção 2):

```bash
python3 "$FICHA/scripts/verify_citacoes.py" --ficha 03-textos/fichas_elegibilidade/fichamento_<chave>.md --pdf 03-textos/pdfs/<chave>.pdf
python3 "$FICHA/scripts/verify_citacoes.py" --fichas 03-textos/fichas_elegibilidade --pdfs 03-textos/pdfs \
  --out 03-textos/fichas_elegibilidade/verificacao_citacoes.csv
python3 "$FICHA/scripts/consolida.py" --fichas 03-textos/fichas_elegibilidade --codebook 00-protocolo/codebook_elegibilidade.csv \
  --out-csv 03-textos/fichas_elegibilidade/fichamentos_master.csv
```

   Ficha reprovada no gate (status diferente de `OK` e de `PDF_TEXTO_NAO_EXTRAIVEL`): refichar com subagente novo.
4. Proposta do LLM:
   `$RS textos elegibilidade consolidar --master 03-textos/fichas_elegibilidade/fichamentos_master.csv --codebook 00-protocolo/codebook_elegibilidade.csv --verificacao 03-textos/fichas_elegibilidade/verificacao_citacoes.csv`
   Leia `contagem`, `motivos_exclusao`, `n_decisoes_humanas`, `n_pendentes_conferencia`, `fracao_outros_metodos` e `avisos`. Várias fichas do mesmo texto: basta uma incluir. No autopiloto abre a pendência `conferencia_elegibilidade_tc`, que cobre só os textos ainda sem decisão humana. Confira também a coluna `texto_confere` do master: `Não` = PDF de outro trabalho (volte à seção 3); `parcial` = outra versão do trabalho (busque a versão de referência ou ligue relatos).
5. Irmã ausente: humanos (ou subagentes no mesmo formato de ficha) preenchem um CSV com `citekey`, `<criterio>` e `<criterio>__evidencia` para cada critério; rode o passo 4 sem `--verificacao`.

## 7. Decisão humana e consolidação

Duas pessoas decidem cada relato de forma independente (MECIR C39); a proposta do LLM, com trecho e página, é apoio. A decisão humana entra pelo ledger e prevalece sobre a proposta e sobre o gate na reconsolidação.

1. Gere a fila dos textos ainda sem decisão humana: `$RS triagem fila --etapa tc` (sem `--master`, lê as propostas de `03-textos/elegibilidade_tc_final.csv`; com `--master <fichamentos_master.csv> --codebook 00-protocolo/codebook_elegibilidade.csv [--verificacao <verificacao_citacoes.csv>] [--criterios ...]`, calcula as propostas das fichas pela mesma regra de `textos elegibilidade consolidar`). Grava `03-textos/fila_humana_tc.csv` com `id_rs, chave, proposta, criterio_proposto, evidencia, pagina, decisao_humana, criterio_humano, motivo`, incertos primeiro, sem os textos que já têm decisão humana e sem clusters `busca_inativa`, e registra `fila_gerada` (idempotente pelo sha). Recusa regravar uma fila com linhas preenchidas e ainda não aplicadas. Leia `n_com_decisao_humana`, `n_inativos_ignorados` e `avisos`.
2. Independência (MECIR C39): cada revisor trabalha numa cópia da fila (ex.: `03-textos/fila_humana_tc_h1.csv` e `_h2.csv`), sem ver a do outro; o consenso (ou o terceiro revisor) vai para a fila canônica: `decisao_humana` (`incluir`, `excluir` ou `aguardando`, em 100% das linhas), `criterio_humano` (obrigatório nas exclusões: a variável-critério do codebook que falha primeiro na ordem, ou o apelido `C<n>`; vazio em `incluir` e `aguardando`) e `motivo` no formato `"trecho" (p. N)` (em `aguardando`, o motivo da espera). A planilha pode voltar do Excel com ponto e vírgula, em UTF-16 ou cp1252, ou em `.xlsx`.
3. Ledger: `$RS triagem override --fila 03-textos/fila_humana_tc.csv --etapa tc --por revisor_humano_1`. O critério é conferido contra as variáveis-critério do último `textos elegibilidade consolidar`, da última `triagem fila --etapa tc` e de `00-protocolo/codebook_elegibilidade.csv` (sem nenhuma dessas fontes, `--criterios <codebook.csv ou criterios.md>`); `C6` vira `c6_nao_retratado`. Uma linha inválida faz a fila inteira não gravar nada, com a lista dos erros. A fila da T/A não é aceita com `--etapa tc`, nem a do texto completo sem ela. Decisão pontual: `$RS triagem override --etapa tc --id RS0042 --decisao excluir --criterio c6_nao_retratado --motivo "retratado (retratacoes.csv)" --por revisor_humano_1`; `--decisao aguardando` só existe com `--etapa tc` e não leva `--criterio`. Sem `--rodada`, a rodada do texto completo é `tc`.
4. Reconsolide com o mesmo comando do passo 4 da seção 6 (com ou sem `--verificacao`; sem as fichas, `$RS textos elegibilidade consolidar` sem `--master` consolida só as decisões humanas). A última decisão humana de texto completo por `id_rs` prevalece; `evidencia` começa com `[decisão humana: <papel>]`. Leia `n_decisoes_humanas`, `mudadas_por_humano`, `n_pendentes_conferencia` (textos ainda só com proposta) e `conferencia_ja_feita`. No autopiloto, `conferencia_elegibilidade_tc` acompanha `n_pendentes_conferencia` a cada reconsolidação (a pendência é substituída com o `n` novo, sem duplicar) e fecha sozinha quando ele chega a 0.
5. Exija `contagem.incerto = 0` e `n_pendentes_conferencia = 0` antes do G5. Faltando decisões, rode `$RS triagem fila --etapa tc` de novo (a fila nova só traz os textos ainda sem decisão humana) e repita os passos 2 a 4.
6. Dúvida que nem humanos nem autores resolvem: `aguardando` (aguardando classificação), relatado no PRISMA na caixa própria e no texto como limitação. O G5 avisa quantos relatórios estão aguardando.

## 8. Ligação de relatos

1. Candidatos: pares `rejeitado` por regra em `01-busca/dedup_pares.csv` (`motivo` com `tese_artigo_nunca_funde` ou `marcador_parte_ou_numeral_diferente`); fichas com `outros_relatos_mesmo_estudo`, mesma `fonte_dados_amostra` ou mesmo `registro_financiamento`; mesmos autores, local e período.
2. Humano decide. Compare autores, local, período, amostra, fonte de dados e financiamento (Cochrane Handbook, cap. 5, sec. 5.2.1); contate autores se persistir dúvida.
3. `03-textos/pares_relatos.csv` com `id_rs_a,id_rs_b` (colunas extras `relato_primario,justificativa` recomendadas) e `$RS textos ligar-relatos --pares 03-textos/pares_relatos.csv`. A lista é acréscimo: as ligações manuais já registradas em `03-textos/ligacao_relatos.csv` ficam, e as ligações de versão que o `dedup` fez (`01-busca/dedup_pares.csv` com `regra = versao` e `decisao = ligado`) sempre ficam, estejam ou não na lista. Para desfazer uma ligação manual, rode com `--substituir-manuais` e a lista completa das manuais que continuam (lista vazia desfaz todas as manuais); as de versão ficam mesmo assim. Para desfazer uma ligação de versão, marque o par como `rejeitado` em `$RS dedup --revisar 01-busca/dedup_pares.csv --por revisor_humano_1`. Leia no resumo `modo` (`acrescimo` ou `substituir_manuais`), `n_pares_versao_dedup`, `n_pares_manuais_mantidos`, `n_pares_manuais_descartados` e `avisos`; os mesmos campos vão para o evento `ligacao_relatos`.

4. Relatos ligados continuam relatos incluídos (não são exclusão); o PRISMA conta estudos por `id_estudo`. O dedup posterior preserva as ligações humanas.
5. Preprint ou working paper e versão publicada chegam ligados desde a deduplicação (references/03-organizacao-triagem.md, seção 3): são dois relatos do mesmo estudo, cada um triado e lido; na extração, fiche o relato mais completo (em geral o publicado) e registre do outro só o que ele acrescenta (amostra, estimativas diferentes), com o mesmo `id_estudo`.

## 9. Bola de neve e re-triagem

1. Sementes: incluídos no texto completo (padrão). Revisões excluídas como não primárias entram por `--ids` com um CSV de `id_rs`, numa rodada SN própria (a próxima livre, ex.: `SN3`; troque o prefixo no passo 4). `--rodada` segue a regra de `--busca-id` (`SN1` vale; `sn1` e `SN1a` saem com código 1 antes da API).
2. `$RS bola-de-neve --direcao ambas --rodada SN1 [--ids <csv>]` (variáveis `RS_EMAIL` e, se houver, `OPENALEX_API_KEY`). Leia `n_nao_resolvidas` (buscar à mão e importar com `--busca-id` SN seguinte e `--metodo citacao`), `n_encontrados`, `n_ja_no_corpus`, `n_gravados`. Não use `--max-paginas-citacoes` na rodada final (marca incompleta).
3. `$RS dedup` e revisão de candidatos.
4. IDs novos (só registros vindos desta rodada):

```bash
python3 -c "import csv; n=[l['id_rs'] for l in csv.DictReader(open('dados/registros_unicos.csv', encoding='utf-8-sig')) if all(r.startswith('SN1-') for r in l['ids_registro'].split('|'))]; open('02-triagem/ids_SN1.csv','w').write('id_rs\n'+''.join(i+'\n' for i in n)); print(len(n))"
```

5. Re-triagem com a MESMA rodada e os mesmos critérios congelados: `$RS triagem preparar --etapa ta --rodada ta_vN --revisor A --criterios 02-triagem/prompts/ta_vN.md --ids 02-triagem/ids_SN1.csv` (e B, árbitro, `mesclar`) ou `$RS triagem api --rodada ta_vN ... --ids 02-triagem/ids_SN1.csv`; depois `$RS triagem consolidar --rodada ta_vN`.
6. Seções 2 a 7 para os novos (`para-baixar`, irmã com `--apenas-pendentes`, inventário, retratações, fichas, fila nova).
7. Nova rodada (SN2) só com os novos incluídos até não haver inclusões novas.
8. Aviso de `fracao_outros_metodos > 0,30`: busca nas bases possivelmente fraca; discuta com o usuário e registre.

## 10. Portão G5, armadilhas e relato

Pré-checagem: `$RS prisma` (exit 2 = contagens não fecham; a mensagem diz qual invariante). O G5 bloqueia (código 2) se falta `elegibilidade_tc_final.csv`, se alguma invariante quebra (inclusive `avaliado_nao_recuperado`, relatório com `recuperado = 0` e decisão, e `decisoes_de_busca_substituida`, decisão sobre registro de busca substituída) ou se há pendência aberta da etapa 07 ou do G5 (`conferencia_elegibilidade_tc`, `retratacao_texto`, manuais). `aguardando` não bloqueia: vira aviso.

Mostre ao usuário antes: buscados, não recuperados (com motivos), avaliados, excluídos por motivo, aguardando classificação, incluídos (relatos e estudos), decisões humanas que mudaram a proposta (`mudadas_por_humano`), retratações, relatos ligados, rodadas de bola de neve, contatos e respostas (resumo de `textos contato-autores`).

- Checkpoints: `$RS portao G5 --aprovar --por revisor_humano_1 --criterios 07-relatorio/prisma_contagens.json`.
- Autopiloto: `--por autopiloto`; conferência humana pendente vira pendência e os produtos saem como rascunho.

| Armadilha | Defesa |
|---|---|
| PDF de outro trabalho | `verificar_conteudo.py` + inventário antes de fichar |
| `incerto` no texto completo | 100% com decisão humana (`incluir`, `excluir` ou `aguardando`) antes do G5 |
| Excluir por falta de dados de desfecho utilizáveis | Proibido (MECIR C40); contatar autores |
| Revisão contada como estudo | `c5_estudo_primario` = Não; vai para a bola de neve |
| Relato secundário excluído | Ligar relatos, não excluir |
| PDF suspeito conferido e não registrado | `conferencia_pdfs.csv` com `recuperado = 1`; senão `avaliado_nao_recuperado` quebra |
| Bola de neve com critérios novos | Mesma rodada e sha dos critérios |
| Não recuperado contado como excluído | `status=nao_encontrado` no relatório ou `recuperado = 0` em `conferencia_pdfs.csv` |

Relato: PRISMA 2020 itens 8 (revisores e independência no texto completo, automação), 9 (contato com investigadores), 16a (fluxo com não recuperados e motivos) e 16b (excluídos que pareceriam elegíveis, com motivo); PRISMA-S itens 5 (busca de citações) e 6 (contatos); MECIR C39, C40, C42, C48 e C49.
