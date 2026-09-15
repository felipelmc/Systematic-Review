# Validação do uso de IA e declaração (RAISE, PRISMA-trAIce)

Protocolo vinculante de validação de modelos de linguagem na triagem, no texto completo, na extração e no risco de viés, e como declarar o uso.

## Sumário

1. Papel permitido da IA por etapa
2. O que o protocolo fixa antes de ver dados
3. Convenções de rodadas, conjuntos e planilhas
4. Protocolo A–H da triagem, com comandos
5. Extração e risco de viés
6. Dados enviados a terceiros
7. Declaração de uso de IA e PRISMA-trAIce
8. Pendências, portões e armadilhas

`$RS` abrevia `python3 "<pasta da skill>/scripts/rs.py"` (SKILL.md, "Como chamar os comandos"): em cada chamada de Bash, use a função `rs` definida na mesma chamada ou o caminho completo, nunca uma variável `RS`. Rode na raiz do projeto.

## 1. Papel permitido da IA por etapa

Classificação do RAISE 3 (ferramentas por tarefa) aplicada nesta skill:

| Etapa | IA pode | Quem decide |
|---|---|---|
| Pergunta, protocolo, strings | Rascunhar e sugerir sinônimos | Humano (G1, G2); string com PRESS e recall de âncoras |
| Deduplicação | Regras auditáveis (`dedup`) | Humano decide candidatos R5 |
| Triagem de títulos e resumos | Decidir só depois de validada (A–D); antes disso, só propor | Humano: incluídos, incertos, conflitos, elusão |
| Texto completo | Propor com trecho literal e página (H) | Humano sempre |
| Extração | Rascunhar com âncora verbatim; números 100% conferidos | Humano confere |
| Risco de viés | Rascunhar respostas às perguntas-sinalizadoras com trecho | Juízo por domínio e global humano |
| Síntese entre estudos, GRADE, CERQual, temas analíticos, CMOCs, calibração QCA | Não | Humano |
| Execução de ponta a ponta sem portões | Não aceitável | Nenhum uso |

## 2. O que o protocolo fixa antes de ver dados

No plano de IA do protocolo (congelado no G2): etapas com IA e papel; ferramentas e modelos candidatos; modo (subagentes ou API) e provedores; tamanho de lote; regra do ensemble (`consenso` com árbitro de terceiro modelo, preferencialmente de outro provedor, ou `liberal`); limiares abaixo; tamanho da calibração, do conjunto de desenvolvimento e da validação; plano de elusão e estabilidade; dados enviados a terceiros; plano de declaração. Mudar limiar depois de ver resultado é proibido; só por emenda datada antes da nova validação (`$RS emenda --arquivo 00-protocolo/protocolo.md --motivo "..."`).

| Limiar | Valor | Onde o script confere |
|---|---|---|
| Calibração humana | κ ≥ 0,6 e concordância ≥ 75% (binária), com ≥ 100 registros ou ≥ 10 incluídos humanos | `validar calcular` de amostra `calibracao`: `criterios.kappa_humanos`, `criterios.concordancia_humanos`, `criterios.tamanho_calibracao` |
| Validação da triagem | recall ≥ 0,95 e limite inferior do IC 95% ≥ 0,90 | amostra `validacao` da rodada ativa: `criterios.recall`, `criterios.recall_ic_inferior`, `atende_limiares` |
| Incluídos humanos na validação | ≥ 60 (ou todos os disponíveis, relatando o IC) | aviso de `n_incluidos_humanos` |
| Elusão | n ≥ 300 excluídos pela IA ou todos | aviso; sem limiar vinculante |
| Estabilidade | reexecutar 5–10% | aviso fora da faixa; sem limiar |
| Extração categórica | κ ou PABAK ≥ 0,7 e concordância ≥ 80% por variável | `concordancia.py` da irmã (`sinalizada`) |
| Efeitos numéricos | 100% com trecho verificado na página e `verificado_humano` | `analise verificar-efeitos` (`pode_seguir_g7`) |

## 3. Convenções de rodadas, conjuntos e planilhas

- Rodada = nome do arquivo de critérios: `02-triagem/prompts/ta_vN.md` → rodada `ta_vN`. Modo API: a rodada congela também modelos, prompts e esforço. A calibração só humana usa rodada própria (`calib_v1`, `calib_v2`...), porque ainda não há decisões de IA.
- Finalidade de cada amostra (`--finalidade`, gravada no desenho e em `validacao_calculada.dados.finalidade`): `calibracao` (A), `desenvolvimento` (B) ou `validacao` (C; padrão de `validar amostrar`); `elusao` (F; padrão de `validar elusao`); `estabilidade` (G; padrão de `validar estabilidade`). `validar calcular` herda a finalidade do desenho (informar outra é erro, código 1). Só a última validação com finalidade `validacao` da rodada ativa (`versoes_ativas.rodada_ta`, gravada por `triagem consolidar`) decide o G4 e a marca de rascunho da declaração de IA; as demais ficam como histórico, calculadas antes ou depois.
- Conjunto de desenvolvimento: registros usados para calibrar critérios e ajustar o prompt. Nunca medem desempenho.
- Amostra nova: `validar amostrar` e `validar elusao` excluem sozinhos os `id_rs` já sorteados em amostras anteriores da MESMA rodada. Entre rodadas ou finalidades (calibração em `calib_v1`, validação em `ta_v3`), passe `--excluir-ids` com a lista dos já usados; eles saem do quadro amostral e da população dos pesos (`n_excluidos_quadro` no desenho). `--ids` restringe o quadro. Lista de IDs de desenhos (só leitura; o primeiro argumento é um padrão glob):

```bash
python3 - "02-triagem/validacao/*/*_desenho.json" 02-triagem/validacao/ids_usados.csv <<'EOF'
import glob, json, sys
ids = {i["id_rs"] for d in glob.glob(sys.argv[1]) for i in json.load(open(d, encoding="utf-8")).get("amostra", [])}
open(sys.argv[2], "w", encoding="utf-8").write("id_rs\n" + "".join(f"{i}\n" for i in sorted(ids)))
print(len(ids), "IDs em", sys.argv[2])
EOF
```

  Numa revisão com busca substituída não é preciso listar os inativos: `validar` tira do quadro e da população os clusters `busca_inativa` (`n_inativos_ignorados` no desenho e no resumo).
- Arquivos em `02-triagem/validacao/<rodada>/`: `amostraNN_cega.xlsx` (sem colunas de IA, ordem embaralhada), `amostraNN_desenho.json` (estratos, pesos, `finalidade`, `sem_ia`, `populacao_rodada`; não vai aos codificadores), `amostraNN_metricas.json`, `amostraNN_falsos_negativos.csv`; `elusaoNN_*`; `estabilidade*.json`.
- Planilha: cada codificador preenche só `decisao_hK` (e `criterio_hK` nas exclusões) sem ver a do outro; discordâncias vão para `decisao_consenso`. Vazio ou `nao_revisado` = NA, fora das métricas. `validar calcular` aceita a planilha em `.xlsx` ou em CSV (vírgula, ponto e vírgula ou tabulação; UTF-8, UTF-16 ou cp1252), desde que tenha `id_rs` e ao menos uma coluna `decisao_*` (em CSV a aba `_meta` se perde: passe `--desenho <amostraNN_desenho.json>`); listas de IDs (`--ids`, `--excluir-ids`) também. `openpyxl` ausente com `.xlsx`: código 3. A leitura é a mesma de todas as planilhas humanas da skill (filas da triagem, `filtrar --calcular-elusao`, âncoras).
- Variante rápida (references/tipos-de-revisao.md, seção 6): `validar amostrar --atalho-rapida` marca a amostra da dupla humana; `validar calcular` grava no `validacao_calculada` os campos do atalho (`atalho_rapida`, `fracao_dupla_humana`, `n_dupla_humana`, `n_populacao`, `kappa_humanos`, `n_excluidos_ia`, `n_excluidos_relidos`, `segunda_leitura_excluidos`) e sai com código 2 enquanto faltar dupla ≥ 20%, κ ou a releitura de todos os excluídos pela IA; `validar segunda-leitura --rodada <r> --planilha <planilha>` registra a releitura (`segunda_leitura.json`, `segunda_leitura_resgatados.csv` para `triagem override --fila`, evento com finalidade `elusao` que não decide o G4).
- Desenho antigo e buscas substituídas: repetir `amostrar`, `elusao` ou `estabilidade` com os mesmos parâmetros reaproveita o desenho. Se ele tem IDs que hoje são `busca_inativa`, o comando avisa (`n_inativos_no_desenho`) e orienta sortear amostra nova com outra `--semente` (na estabilidade, arquive `estabilidade_desenho.json` antes de trocar a semente); `calcular` também avisa.
- Toda amostra usa `--semente` explícita, registrada no log.

## 4. Protocolo A–H da triagem, com comandos

### A. Calibração humana dos critérios

1. Dimensione para ≥ 100 registros e ≥ 10 incluídos esperados e sorteie, sem IA, de `registros_unicos.csv` menos o que o funil formal excluiu:
   `$RS validar amostrar --etapa ta --rodada calib_v1 --finalidade calibracao --sem-ia --n 150 --semente 11 --criterios 02-triagem/prompts/ta_v1.md` (clusters de buscas substituídas ficam de fora sozinhos)
2. Dois humanos codificam às cegas; `$RS validar calcular --planilha 02-triagem/validacao/calib_v1/amostra01_cega.xlsx`. Critérios: `kappa_humanos` (≥ 0,6), `concordancia_humanos` (≥ 75%) e `tamanho_calibracao` (≥ 100 registros ou ≥ 10 incluídos humanos); métricas da IA não existem aqui. Código 2 se não atende; no autopiloto, pendência `calibracao_reprovada`.

| Resultado | Ação |
|---|---|
| κ ≥ 0,6, ≥ 75% e tamanho atendido | Critérios estáveis; siga para B |
| κ ou concordância abaixo | Discutir cada divergência; critérios `ta_v2.md`; nova calibração em registros NOVOS: `ids_usados.csv` da seção 3 e `validar amostrar --rodada calib_v2 --finalidade calibracao --sem-ia ... --excluir-ids 02-triagem/validacao/ids_usados.csv --criterios 02-triagem/prompts/ta_v2.md` |
| Tamanho não atendido (< 10 incluídos humanos com < 100 registros) | Amplie antes de concluir: nova amostra de calibração maior, em rodada nova, com os mesmos codificadores |

Mudança substantiva de critério depois do G2 é emenda ao protocolo. A pendência `calibracao_reprovada` é fechada por humano (`pendencia fechar`) depois da nova calibração.

### B. Desenvolvimento e congelamento do prompt

1. Conjunto de desenvolvimento = os registros da calibração, já codificados por humanos (acrescente outros só se precisar): rode o trecho da seção 3 com os argumentos `"02-triagem/validacao/calib_v*/*_desenho.json" 02-triagem/validacao/dev_ids.csv`.
2. IA nesse conjunto: `$RS triagem preparar --etapa ta --rodada ta_v1 --revisor A --criterios 02-triagem/prompts/ta_v1.md --ids 02-triagem/validacao/dev_ids.csv` (e B, árbitro), subagentes, `mesclar`. Modo API: `$RS triagem api --rodada ta_v1 ... --ids 02-triagem/validacao/dev_ids.csv`.
3. Registre o conjunto como amostra de desenvolvimento da rodada e reaproveite os códigos humanos: `$RS validar amostrar --etapa ta --rodada ta_v1 --finalidade desenvolvimento --ids 02-triagem/validacao/dev_ids.csv --n <nº de IDs> --semente 11`, depois `$RS validar calcular --planilha 02-triagem/validacao/calib_v1/amostra01_cega.xlsx --desenho 02-triagem/validacao/ta_v1/amostra01_desenho.json` (com várias calibrações, repita `--planilha`). Reprovar aqui é o esperado enquanto o prompt evolui: não abre pendência nem marca a declaração como rascunho.
4. Ajuste o texto dos critérios (exemplos VÁLIDO/INVÁLIDO, esclarecimentos) só com esse conjunto. Cada versão é arquivo e rodada novos (`ta_v2.md`, `ta_v2`): repita os passos 2 e 3 na rodada nova, com o mesmo `dev_ids.csv` e as mesmas planilhas.
5. Congelada a versão `ta_vN`: arquivo de critérios (sha em cada lote e decisão), modelo exato em `mesclar --modelo`, tamanho de lote; no modo API, `02-triagem/api/ta_vN/parametros.json`. Qualquer mudança posterior, mesmo de uma palavra, é `ta_vN+1` e nova validação.

### C. Validação em amostra nova

1. Rodada completa com a versão congelada, na mesma rodada: `$RS triagem preparar --etapa ta --rodada ta_vN --revisor A --criterios 02-triagem/prompts/ta_vN.md` (sem `--ids`, acrescenta só o que falta; clusters de busca substituída ficam de fora sozinhos), B, árbitro, `mesclar`, `$RS triagem consolidar --rodada ta_vN --regra consenso` (grava a rodada ativa). Corpus grande e custo alto: rode antes um subconjunto sorteado com `--ids`, valide e só depois complete.
2. Amostra, fora dos IDs de calibração e desenvolvimento (`ids_usados.csv` da seção 3, gerado agora): `$RS validar amostrar --etapa ta --rodada ta_vN --n 100 --semente 12 --enriquecer-incluidos 60 --excluir-ids 02-triagem/validacao/ids_usados.csv [--regra liberal]` (finalidade `validacao` é o padrão; a regra tem de ser a da consolidação). O desenho estratifica pela decisão da IA e repondera.
3. Dupla humana cega (sem ter visto pareceres da IA desses registros); terceiro revisor preenche `decisao_consenso`.
4. `$RS validar calcular --planilha 02-triagem/validacao/ta_vN/amostraNN_cega.xlsx`.
5. Relate: `sensibilidade` e `sensibilidade_ic`, `especificidade`, `precisao`, `vpn`, `kappa_ia`, `pabak_ia`, `wss`, `n_incluidos_humanos`, `ponderado`, `matriz` e métricas `por_revisor` (em `amostraNN_metricas.json`).

### D. Limiar e tamanho amostral

Aprova só com recall ≥ 0,95 E limite inferior (Clopper-Pearson) ≥ 0,90.

| Incluídos humanos na validação | Máximo de falsos negativos que ainda aprova |
|---|---|
| < 36 | Nenhum resultado aprova (limiar inalcançável) |
| 36–53 | 0 |
| 54–69 | 1 |
| 70–84 | 2 |
| 85–99 | 3 |
| 100–113 | 4 |
| 114–126 | 5 |
| 127–140 | 6 |
| 141–159 | 7 |
| 160–179 | 8 |
| 180–199 | 9 |
| 200–219 | 10 |

Planeje pela pergunta "quantos incluídos humanos consigo reunir?". Com menos de 36 possíveis, a IA não ganha autonomia para excluir: vá direto ao remédio 5 e use a IA como terceira leitura.

**Revisões pequenas e reprovação só pela largura do IC.** `validar calcular` grava `motivo_reprovacao` no resumo e no evento:

| `motivo_reprovacao` | Quando | O que fazer |
|---|---|---|
| `largura_ic` | 0 falsos negativos e o único critério não atendido é o limite inferior do IC do recall (poucos incluídos humanos) | Não revise os critérios. O resumo traz `incluidos_humanos_necessarios` (36) e `incluidos_ia_nao_sorteados`. Se há incluídos pela IA suficientes, amplie a validação com amostra nova da mesma rodada (`$RS validar amostrar --etapa ta --rodada ta_vN --n <n> --semente <outra> --enriquecer-incluidos <alvo>`; os IDs já sorteados ficam de fora sozinhos) ou meça os perdidos com `validar elusao`. Se não há (limiar inalcançável), remédio 5 e aprovação humana do G4 com `$RS portao G4 --aprovar --por revisor_humano_1 --forcar --motivo "..."` |
| `humanos` | só critérios de concordância humana falharam | A IA não é o problema: consenso das discordâncias em `decisao_consenso` e, se seguir baixa, recalibração (A) |
| `desempenho_ia` | há falsos negativos ou outros critérios da IA falharam | Remédios da seção E, em ordem |

A descrição da pendência `validacao_triagem_reprovada` segue o motivo, e a `proxima_acao` do `status` também: com `largura_ic`, sugere `validar amostrar ... --enriquecer-incluidos <alvo>` com outra semente (alternativa `validar elusao`) e só vai ao remédio 5 com `--forcar` quando as métricas mostram que a rodada não tem incluídos pela IA suficientes; com `humanos`, o consenso da dupla; com `desempenho_ia`, os falsos negativos e critérios vN+1. Validação calculada por versão antiga, sem `motivo_reprovacao`, sem falsos negativos e com menos de 36 incluídos humanos: remédio 5.

### E. Remédios, em ordem (os remédios 2 a 4 voltam a C e D com amostra nova)

1. **Falsos negativos:** leia `amostraNN_falsos_negativos.csv` e classifique a causa (critério ambíguo, resumo sem a informação, mencionar × estudar, idioma, formato). Os analisados viram dados de desenvolvimento.
2. **Critérios `ta_vN+1`:** junte ao desenvolvimento todos os IDs já sorteados na rodada anterior (trecho da seção 3 com os argumentos `"02-triagem/validacao/ta_vN/*_desenho.json" 02-triagem/validacao/dev_ids_vN+1.csv`). Depois: `preparar --rodada ta_vN+1 --ids 02-triagem/validacao/dev_ids_vN+1.csv` (A, B), `mesclar`, `validar amostrar --rodada ta_vN+1 --finalidade desenvolvimento --ids 02-triagem/validacao/dev_ids_vN+1.csv --n <nº de IDs> --semente <s>`, `validar calcular` com todas as planilhas anteriores (`--planilha` repetido) e `--desenho` da amostra nova; então rodada completa e passo C com `--excluir-ids` de todos os já usados. A pendência `validacao_triagem_reprovada` da validação antiga não fecha sozinha: com a nova validação aprovada, feche-a com `pendencia fechar` citando o arquivo de métricas novo.
3. **Regra liberal:** `$RS triagem consolidar --rodada ta_vN --regra liberal` e nova amostra com `--regra liberal --excluir-ids 02-triagem/validacao/ids_usados.csv`. Sobe o recall, cai a economia; divergências vão todas à fila humana.
4. **IA só prioriza:** humanos leem na ordem sugerida pela IA com critério de parada estatístico pré-registrado. Não implementado nesta versão (não há comando para ordenar a fila pela IA nem teste de parada): declare o critério no protocolo, ordene a leitura à mão e registre-a como decisões humanas (remédio 5); se não for viável, vá direto ao remédio 5.
5. **Dupla humana completa:** `$RS validar amostrar --etapa ta --rodada ta_vN --n <nº de registros> --semente <s>` (finalidade `validacao`; entram todos os não sorteados antes); humanos codificam em dupla; `$RS validar calcular` da planilha (relatar como estudo dentro da revisão; planilha devolvida em CSV não tem a aba `_meta`: passe `--desenho 02-triagem/validacao/ta_vN/amostraNN_desenho.json`). Não há comando que transforme planilhas de validação em decisões humanas: converta em overrides, com o trecho abaixo, todas as decisões humanas duplas feitas com a versão final dos critérios (planilhas de desenvolvimento, validação e completa; amostra com um só codificador precisa de segunda leitura em `decisao_consenso`). Passe as planilhas **codificadas** (`.xlsx` ou CSV com vírgula, ponto e vírgula ou tabulação, UTF-8 ou cp1252), não as `_cega.xlsx` em branco que ficaram na pasta quando os humanos devolveram CSV:

```bash
python3 - 02-triagem/validacao/ta_vN/dupla_humana_fila.csv <planilhas codificadas: .xlsx ou .csv> <<'EOF'
import csv, io, sys
SAIDA, decisoes, vistos = sys.argv[1], {}, set()
def ler(p):
    if p.lower().endswith(".xlsx"):
        from openpyxl import load_workbook
        return load_workbook(p, read_only=True, data_only=True)["codificacao"].iter_rows(values_only=True)
    bruto = open(p, "rb").read()
    try: texto = bruto.decode("utf-8-sig")
    except UnicodeDecodeError: texto = bruto.decode("cp1252")
    return csv.reader(io.StringIO(texto), delimiter=csv.Sniffer().sniff(texto.splitlines()[0], ";,\t").delimiter)
for p in sys.argv[2:]:
    linhas = iter(ler(p))
    cab = [str(c or "").strip().lower() for c in next(linhas)]
    for v in linhas:
        r = dict(zip(cab, ("" if x is None else str(x).strip().lower() for x in v)))
        if not r.get("id_rs"): continue
        i = r["id_rs"].upper(); vistos.add(i)
        h1, h2 = r.get("decisao_h1", ""), r.get("decisao_h2", "")
        dec = r.get("decisao_consenso") or (h1 if h1 == h2 else "")
        if dec in ("incluir", "excluir", "incerto"):
            crit = (r.get("criterio_consenso") or r.get("criterio_h1") or r.get("criterio_h2") or "").upper() if dec == "excluir" else ""
            decisoes[i] = {"id_rs": i, "decisao_humana": dec, "criterio_humano": crit, "motivo_humano": f"dupla humana ({p})"}
faltam = sorted(vistos - set(decisoes))
if faltam: sys.exit(f"{len(faltam)} sem decisão humana dupla (discordância sem consenso, NA ou um codificador): {faltam[:20]}")
sem_crit = sorted(i for i, d in decisoes.items() if d["decisao_humana"] == "excluir" and not d["criterio_humano"])
if sem_crit: sys.exit(f"{len(sem_crit)} exclusões sem criterio_h1/criterio_h2 (o override recusa exclusão sem critério): {sem_crit[:20]}")
w = csv.DictWriter(open(SAIDA, "w", newline="", encoding="utf-8"), fieldnames=["id_rs", "decisao_humana", "criterio_humano", "motivo_humano"])
w.writeheader(); w.writerows(decisoes[i] for i in sorted(decisoes))
print(len(decisoes), "decisões humanas em", SAIDA)
EOF
```

   Os codificadores preenchem `criterio_h1`/`criterio_h2` (ou `criterio_consenso`) em toda exclusão: `triagem override` recusa exclusão sem critério e confere o critério contra os IDs da rodada; o trecho acima para antes de gravar se faltar algum. Depois: `$RS triagem override --fila 02-triagem/validacao/ta_vN/dupla_humana_fila.csv --rodada ta_vN --por revisor_humano_1 [--criterios 02-triagem/prompts/ta_vN.md]` (passe `--rodada`: o nome do arquivo não segue `fila_humana_<rodada>.csv`, e sem ela vale a rodada ativa; `--criterios` quando a rodada não tem lotes nem `02-triagem/api/<rodada>/criterios.md`; uma linha inválida faz a fila inteira não gravar nada) e `$RS triagem consolidar --rodada ta_vN`. O G4 fica bloqueado pelo limiar da IA: só um humano aprova, com `--forcar --motivo "triagem por dupla humana completa; IA como terceira leitura"`.

### F. Elusão depois da rodada completa

1. `$RS validar elusao --etapa ta --rodada ta_vN --n 300 --semente 13` (finalidade `elusao`; um codificador por padrão; `--codificadores 2` se o protocolo pedir; `--excluir-ids` para tirar IDs usados em outra finalidade).
2. Humano lê às cegas; `$RS validar calcular --planilha 02-triagem/validacao/ta_vN/elusao01_cega.xlsx`.
3. Relate `elusao` (taxa com IC) e `perdidos_estimados` com o limite superior de `metricas.elusao.perdidos_ic`, não só a estimativa pontual. Com 0 incluídos em 300 lidos, o limite superior da taxa é 1,22%.
4. Incluído encontrado: `$RS triagem override --id <RS> --decisao incluir --motivo "achado na elusão (elusao01)" --por revisor_humano_1` (rodada ativa), análise de causa e, conforme a estimativa de perdidos, ampliar a leitura dos excluídos ou voltar a E.
5. Toda inclusão e todo incerto da IA vão ao texto completo (leitura humana); conflitos entre modelos vão a humano: `triagem consolidar` já põe na fila as divergências resolvidas pelo árbitro (`motivo_fila=arbitrada`).

### G. Estabilidade

1. `$RS validar estabilidade --etapa ta --rodada ta_vN --amostra 0.1 --semente 7` → prepara lotes na rodada `ta_vN_estab` com os mesmos critérios. Despache subagentes NOVOS e `$RS triagem mesclar --rodada ta_vN_estab --revisor A --modelo <id>` (e B). Modo API: `$RS triagem api --rodada ta_vN_estab --criterios 02-triagem/prompts/ta_vN.md --modelo-a <mesmo> --modelo-b <mesmo> --arbitro <mesmo> --ids 02-triagem/validacao/ta_vN/estabilidade_ids.csv`.
2. Repita o mesmo comando `validar estabilidade` para calcular. Relate por revisor `concordancia_binaria`, `kappa_binario`, `mudancas_de_seguimento`.
3. Registros que mudaram entre seguir e excluir (lista `mudancas` em `estabilidade.json`): um humano decide (override na rodada ativa; `ta_vN_estab` é recusada). Oscilação alta sinaliza critério frágil: volte a E.

### H. Texto completo

O LLM propõe elegibilidade com critério, trecho literal e página verificados pelo gate de citações; duas pessoas decidem cada relato e o motivo registrado é o humano: `triagem fila --etapa tc` gera `03-textos/fila_humana_tc.csv` e `triagem override --fila 03-textos/fila_humana_tc.csv --etapa tc` aplica (`incluir`, `excluir` com critério obrigatório, ou `aguardando`). `textos elegibilidade consolidar` aplica a decisão humana sobre a proposta; o G5 não aprova com `incerto` sem decisão humana e, no autopiloto, a pendência `conferencia_elegibilidade_tc` fica aberta até todo texto ter decisão humana (references/04-textos-elegibilidade.md, seção 7). Documentos longos: leitura em faixas de até 20 páginas cobrindo o texto inteiro; no modo API, instrução depois do documento.

## 5. Extração e risco de viés

| Dado | Regra | Comando ou arquivo |
|---|---|---|
| Números de efeito | 100% conferidos na página, ou dupla extração com arbitragem | `$RS analise verificar-efeitos`; humano marca `verificado_humano` em `05-decomposicao/efeitos_extraidos.csv`; seguir só com `pode_seguir_g7 = true` |
| Categóricas | Segundo codificador cego em ≥ 20% dos estudos (mínimo 10) | Irmã `fichamento-sistematico`: `amostrar_validacao.py --consolidado <master> --fracao <max(0,2; 10/N)> --semente <s> --out <amostra.csv> [--classificador tipo_estudo]` e `concordancia.py --original <fichas> --validacao <fichas>/_validacao --codebook <codebook> --amostra <amostra.csv> --out-dir <saidas>` |
| Variável sinalizada (κ e PABAK < 0,7, ou < 80%) | Redefinir no codebook e recodificar TODOS os estudos | Nova versão do codebook |
| Textuais abertas | Trecho literal obrigatório; divergências lidas por humano | Gate de citações |
| Piloto | 2–3 estudos por bloco a1, a2, b1, b2 antes da rodada | G6 |
| Risco de viés | LLM rascunha respostas às perguntas-sinalizadoras com trecho e página; juízo humano | `agentes/avaliador-rob.md` |

Segundo codificador de preferência humano. Se for um subagente, a concordância mede consistência entre agentes, não acurácia: relate assim e faça um humano arbitrar todas as divergências. Quem confere lê o trecho antes da resposta sugerida.

## 6. Dados enviados a terceiros

| Situação | Regra |
|---|---|
| Modo subagentes | Textos processados pelo provedor da sessão; declarar |
| Modo API | Consentimento explícito do usuário antes; registrar no plano de IA (ou emenda); declarar provedores e termos de uso |
| PDFs protegidos por direitos autorais | Conferir termos e direitos antes de enviar a serviços em nuvem |
| Dados pessoais (entrevistas, microdados) | Não enviar sem base legal (LGPD) e aprovação do usuário |
| Credenciais | Só variáveis de ambiente; nunca em arquivo, log ou `.env` lido implicitamente |

## 7. Declaração de uso de IA e PRISMA-trAIce

1. `$RS declaracao-ia` → `07-relatorio/declaracao_uso_ia.md`, gerado do log: modelos, tipos de ator, datas, parâmetros, papéis por etapa, prompts e critérios com sha256, a validação que decide com métricas e limiares (e o histórico de calibração e desenvolvimento), elusão, estabilidade, portões, custo registrado (`custo_estimado_usd` dos eventos da `triagem api`; eventos só com tokens são calculados pela tabela de preços; estimativas de `--estimar` listadas à parte), pendências e marca `RASCUNHO NÃO VALIDADO`. Os subagentes de fichamento, RoB e extração não geram eventos com modelo: registre o modelo nos critérios de G6 e G7, e complete a parte narrativa.
2. Complete a parte narrativa com `assets/templates/declaracao_uso_ia.md` em `07-relatorio/declaracao_uso_ia_texto.md`: justificativa, o que a IA não fez, interação humano-IA, governança de dados, interesses, limitações, responsabilidade. Números vêm dos JSONs e do arquivo gerado; nunca digitados.
3. Lista de conferência: copie `assets/checklists/prisma_traice.csv` para `07-relatorio/checklist_prisma_traice.csv` sem a linha de atribuição (`#`), acrescente `local_no_relato,status` e preencha (trecho em references/08-relato.md, seção 7; convenções em `assets/checklists/README.md`). PRISMA-trAIce é proposta sem endosso do PRISMA: use junto dos itens 8, 9 e 11 do PRISMA 2020 e das recomendações 1.8 a 1.10 do RAISE 1.
4. Depois de fechar pendências, regenere: `$RS declaracao-ia` (e `$RS prisma`).
5. A marca de rascunho aparece com pendências abertas, com a validação que decide (a última com `finalidade` `validacao` da rodada ativa) abaixo do limiar, ou com IA na triagem sem essa validação. Calibração e desenvolvimento reprovados não marcam: a declaração os lista como histórico. Evento antigo sem `finalidade` conta como validação (salvo elusão e estabilidade). Nunca apague a marca à mão.

Declarar sempre que a IA fez ou sugeriu julgamento sobre elegibilidade, risco de viés, extração, síntese, certeza ou resumos em linguagem simples (RAISE 1, rec. 1.8): nome, versão, datas, finalidade, justificativa com validação, prompts e saídas disponíveis, interesses, limitações e impacto (rec. 1.9). Uso só para ortografia e gramática em geral não precisa ser listado, salvo política do periódico.

## 8. Pendências, portões e armadilhas

| Pendência (autopiloto) | Aberta por | Fecha |
|---|---|---|
| `validacao_humana` | `validar amostrar`/`elusao` | Sozinha, quando `validar calcular` roda a planilha |
| `calibracao_reprovada` | `validar calcular` de amostra `calibracao` abaixo dos limiares | Humano, depois da nova calibração: `$RS pendencia fechar <id> --motivo "..."` |
| `validacao_triagem_reprovada` | `validar calcular` de amostra `validacao` com `atende_limiares=false` (desenvolvimento reprovado não abre); a descrição segue `motivo_reprovacao` | Humano, depois da validação nova que atende (ou do remédio 5 com o G4 forçado): `$RS pendencia fechar <id> --motivo "..."` |
| `fila_humana_triagem` | `triagem consolidar` com fila (inclui divergências arbitradas) | Sozinha, quando a fila zera |
| `revisao_humana_portao` | aprovação com `--por autopiloto` | Humano, depois de conferir |

Só humano fecha pendência; ao fechar, regenere os produtos indicados em `regenerar`.

| Armadilha | Defesa |
|---|---|
| Ajustar o prompt e medir nos mesmos registros | Desenvolvimento com `--finalidade desenvolvimento`; validação com `--excluir-ids` dos usados |
| Amostra sorteada com a finalidade errada | Confira `finalidade` no resumo de `validar amostrar`; o G4 só lê `validacao` da rodada ativa e divergir no `calcular` é erro |
| Validar com a regra errada | `--regra` igual em `consolidar` e `validar amostrar` |
| "Não revisado" como exclusão | Deixe vazio ou `nao_revisado` (NA) |
| Concordância bruta alta como prova | Relate κ, PABAK e recall com IC |
| Validar só em inglês numa revisão trilíngue | Relate recall por idioma quando houver volume em PT e ES |
| Codificador que viu pareceres da IA | Planilha cega e pessoas que não resolveram a fila desses registros |
| Baixar limiar depois do resultado | Proibido; emenda datada antes da nova validação |
| Consenso entre dois modelos tratado como validação | Consenso não mede recall |
| Reprovação por IC largo tratada como falha da IA | `motivo_reprovacao = largura_ic`: amostra maior ou remédio 5, nunca critérios vN+1 por isso |
| Decisão oscilante mantida como exclusão | Humano decide (G) |
