# 06 Decomposição e extração de efeitos

Instrução operacional das etapas 8 (piloto, portão G6) e 9 (extração, portão G7, em paralelo com o risco de viés de references/05-qualidade.md). `$RS` abrevia `python3 "<pasta da skill>/scripts/rs.py"` (SKILL.md, "Como chamar os comandos"): em cada chamada de Bash, use a função `rs` definida na mesma chamada ou o caminho completo, nunca uma variável `RS`.

## Sumário

1. Unidades e regras
2. O que vem do protocolo e o que perguntar
3. Codebook por tipo de revisão e arquivos
4. Antes de extrair
5. Piloto (G6)
6. Decomposição completa
7. Efeitos: extrator, colunas, preparar e verificar
8. Enriquecer efeitos e master (família, `rob_geral`)
9. Validação das categóricas (κ, PABAK)
10. Portão G7 (parte extração) e autopiloto
11. Armadilhas
12. O que registrar e relatar

## 1. Unidades e regras

| Nível | Identificador | Onde | Regra |
|---|---|---|---|
| Estudo | `id_estudo` (RS0007 → ES0007) | `dados/registros_unicos.csv`, efeitos | Unidade de síntese; relatos ligados compartilham o id; nunca contar duas vezes |
| Relato | `id_rs`, `chave` (= `citekey`) | fichas, PDFs | Fonte da informação; uma ficha por relato × desenho |
| Ficha | `ficha_id` (`<chave>` ou `<chave>#<tipo_estudo>`) | `fichamentos_master.csv` | Uma por desenho; estudo que combina a2 e b2 explicitamente gera duas |
| Efeito | `id_efeito` (`<chave>-E01`) | `05-decomposicao/efeitos_extraidos.csv` | Uma linha por estudo × outcome × modelo × subgrupo (× momento); todas as estimativas elegíveis, com a principal marcada |

| Regra | Operação |
|---|---|
| Revisões, meta-análises, simulações sem dados próprios | Nunca são estudo: sem ficha de decomposição, sem efeitos (vão para a bola de neve) |
| Modelo principal | Declarado pelos autores; senão o usado na interpretação; senão a regra do protocolo. Critério em `b2_criterio_modelo_principal` |
| Direção | Sinal da estimativa pontual relativo a `direcao_desejada` do protocolo. Significância em variável separada. Nunca "sem efeito" por p > 0,05 |
| Estimando | `ATE`, `ITT`, `LATE`, `ATT`, `RDD_local`, `associacao`, `outro`, com trecho |
| Ausência | `999` = aplicável e ausente no texto; `NA_secao` = bloco que não se aplica ao `tipo_estudo`; nunca 0, "não" ou vazio silencioso |
| Âncora | Toda resposta com trecho literal e página. Fichas: página impressa + `offset_pagina`. CSV de efeitos: índice da página no PDF |
| Piloto | 2 a 3 estudos por bloco a1/a2/b1/b2 presente, antes da rodada completa |
| Números de efeito | 100% conferidos por humano na página (`verificado_humano`) |
| Categóricas | 2º codificador cego em ≥ 20% dos textos (mínimo 10); κ ou PABAK ≥ 0,7 e concordância ≥ 80% por variável |

## 2. O que vem do protocolo e o que perguntar

Tudo congelado no G2 em `00-protocolo/` (o G2 congela só o nível da pasta). Mudança depois: `$RS emenda --arquivo 00-protocolo/codebook_v0_oqf.csv --motivo "..."` e descrição em `00-protocolo/emendas.md`.

| Item | Pergunte ao usuário | Onde entra |
|---|---|---|
| Famílias de intervenção (lista fechada, com definição) | "Quais tipos de intervenção viram linhas da caixa?" | prompt de `familia_intervencao` |
| Construtos de outcome e `direcao_desejada` de cada um (por contexto) | "Emprego aumenta; inadimplência reduz?" | `construto_outcome`, `b2_direcao_estimativa_principal`, entrada `outcomes` do extrator |
| Regra do modelo principal | "Na falta de declaração dos autores, qual especificação vale?" | `b2_modelo_principal`, entrada `regra_modelo_principal` do extrator |
| Prazo de "tempo longo até o efeito" | "A partir de quantos anos?" | `impl_tempo_longo` |
| Segundo codificador | "Humano (preferência da skill, references/ia-validacao.md, seção 5) ou subagente novo?" Subagente só mede consistência entre agentes, não acurácia: relate assim e faça um humano arbitrar todas as divergências | seção 9 |
| Verificação dos números | "Conferência humana de 100% (padrão) ou dupla extração com arbitragem?" | seção 7 |
| Contato com autores | "Quem escreve e em quanto tempo desistimos?" | Notas das fichas e G7 |

## 3. Codebook por tipo de revisão e arquivos

| Tipo (`--tipo` do init) | Codebook em `assets/codebooks/` | Classificador | Efeitos |
|---|---|---|---|
| `oqf_mista_sequencial`, `metodos_mistos` | `oqf_decomposicao.csv` (bloco comum + a1/a2/b1/b2) | `tipo_estudo` | sim, dos b2 |
| `efetividade_meta`, `efetividade_swim` | `oqf_decomposicao.csv` só com o bloco comum (`aplicavel_se` vazio) e o bloco b2 (`aplicavel_se = tipo_estudo=b2`), salvo como `00-protocolo/codebook_v0_efetividade.csv` (trecho em references/01-pergunta-protocolo.md, seção 10, passo 7) | `tipo_estudo` (só b2) | sim |
| `escopo`, `mapa_evidencias` | `escopo_pcc.csv` (charting; sem RoB) | nenhum | não |
| `qualitativa`, `realista` | `qualitativa.csv` (achados verbatim, candidatos a CMOC, insumos CERQual) | nenhum | não |

```bash
cp "<pasta da skill>/assets/codebooks/oqf_decomposicao.csv" 00-protocolo/codebook_v0_oqf.csv
grep -c "{" 00-protocolo/codebook_v0_oqf.csv   # tem de dar 0 antes do G2 (placeholders substituídos)
```

As variáveis `familia_intervencao`, `construto_outcome`, `impl_componentes`, `impl_multinivel`, `impl_infraestrutura`, `impl_barreiras_fidelidade`, `impl_tempo_longo`, `mecanismo_id`, `moderador_id`, `percepcao_id`, `custo_id` e `custo_unitario` são lidas por `rs.py caixa` pelo mapa `assets/mapas/caixa_ferramentas_mapa.csv`: não renomeie nem mova para blocos condicionais.

| Caminho | Conteúdo |
|---|---|
| `05-decomposicao/piloto/fichas/` e `_validacao/` | fichas do piloto e da recodificação cega |
| `05-decomposicao/piloto_fichamentos_master.csv` | master do piloto (no nível da pasta, que o `status` enxerga; o nome com `fichamentos_master` é o que o G6 procura) |
| `05-decomposicao/fichas/` e `_validacao/` | fichas da rodada completa |
| `05-decomposicao/verificacao_citacoes.csv`, `fichamentos_master.csv`/`.xlsx` | gate e base mestre |
| `05-decomposicao/amostra_validacao.csv`, `concordancia/` | validação das categóricas |
| `05-decomposicao/efeitos/<chave>.csv` | saída do extrator de efeitos (fonte que se corrige) |
| `05-decomposicao/efeitos_extraidos.csv`, `verificacao_efeitos.csv`, `efeitos_preparacao_avisos.csv` | saídas de `analise preparar-efeitos` (esquema + colunas extras) e `verificar-efeitos` |
| `05-decomposicao/efeitos_para_sintese.csv`, `master_caixa.csv` | junções da seção 8 |

`FS` = pasta `scripts` da skill `fichamento-sistematico` (`<pasta da skill>/../fichamento-sistematico/scripts`; se não existir, o `caminho` gravado por `$RS ambiente` em `rs_estado.json`, chave `ambiente.skills_irmas`). Sem a irmã: subagentes escrevem as fichas no mesmo formato, mas não há gate de citação nem concordância automática; declare a limitação e marque os produtos como rascunho.

## 4. Antes de extrair

1. `$RS status`: G5 aprovado; etapa atual `08_piloto_extracao`.
2. **Relatos do mesmo estudo** (artigo, tese, relatório): liste pares em `03-textos/pares_relatos.csv` (`id_rs_a,id_rs_b`) e rode `$RS textos ligar-relatos --pares 03-textos/pares_relatos.csv`. A lista é acréscimo às ligações já feitas (as de versão do `dedup` sempre ficam); para desfazer ligações manuais, rode com `--substituir-manuais` e a lista das que continuam (references/04-textos-elegibilidade.md, seção 8). Fiche o relato mais completo; dos demais, só complementos (nas Notas) e efeitos que não estejam no principal.
3. **PDF certo**: em `03-textos/inventario_textos.csv`, `veredito_conteudo` igual a `suspeito`, `conferir_a_mao` ou `sem_camada_de_texto` exige olho humano antes de fichar.
4. **Convenção normativa**: cole este parágrafo (preenchido) no prompt de cada fichador, depois de `INSTRUCOES_FICHADOR.md` da irmã:
   > Convenções deste projeto: `999` = aplicável e ausente no texto; `NA_secao` = variável de bloco a1/a2/b1/b2 que não se aplica ao `tipo_estudo` da ficha; nunca use 0, "não" ou "sem efeito" para ausência. Direção do efeito = sinal da estimativa pontual relativo à direção desejada do protocolo ({construto → aumentar ou reduzir}), nunca a significância, que vai em variável separada. Não crie mecanismos, moderadores ou percepções que os autores não relatam. Números de efeito não entram na ficha: vão para o CSV do extrator de efeitos.

## 5. Piloto (G6)

1. **Escolha** 2 a 3 textos por bloco presente (pelo resumo e pela elegibilidade; bloco com menos textos: todos). Se o fichador classificar em outro bloco, troque o texto.
2. **Fichamento** pela skill `fichamento-sistematico` (um PDF por subagente, até 3 em paralelo): codebook `00-protocolo/codebook_v0_oqf.csv`, classificador `tipo_estudo`, parágrafo da seção 4, saída `05-decomposicao/piloto/fichas`. Depois de cada ficha e no fim:
   ```bash
   python3 "$FS/verify_citacoes.py" --fichas 05-decomposicao/piloto/fichas --pdfs 03-textos/pdfs \
     --out 05-decomposicao/piloto/verificacao_citacoes.csv
   ```
   Saída 1 = ficha reprovada → subagente NOVO para o mesmo PDF.
3. **Segundo extrator cego** para todos os textos do piloto (subagente novo, sem mencionar a ficha existente) em `05-decomposicao/piloto/fichas/_validacao`, com o mesmo gate.
4. **Consolidar e comparar**:
   ```bash
   python3 "$FS/consolida.py" --fichas 05-decomposicao/piloto/fichas --codebook 00-protocolo/codebook_v0_oqf.csv \
     --out-csv 05-decomposicao/piloto_fichamentos_master.csv --out-xlsx 05-decomposicao/piloto_fichamentos_master.xlsx
   python3 -c "import pandas as p; d=p.read_csv('05-decomposicao/piloto_fichamentos_master.csv', dtype=str); \
     d[['citekey']].drop_duplicates().to_csv('05-decomposicao/piloto/amostra.csv', index=False)"
   python3 "$FS/concordancia.py" --original 05-decomposicao/piloto/fichas --validacao 05-decomposicao/piloto/fichas/_validacao \
     --codebook 00-protocolo/codebook_v0_oqf.csv --amostra 05-decomposicao/piloto/amostra.csv --out-dir 05-decomposicao/piloto/concordancia
   ```
5. **Efeitos do piloto** (textos b2): seção 7, passos 1 a 3, com `--master 05-decomposicao/piloto_fichamentos_master.csv` (o `preparar-efeitos` registra `extracao_consolidada`).
6. **Revisão humana de todas as fichas do piloto** contra os PDFs, anotando: fronteira a1/a2 ambígua, categorias sobrepostas, variável com `999` demais, prompt que induz inferência, direção lida pela significância, colunas de efeito mal usadas.
7. **Ajuste** o codebook e registre `$RS emenda --arquivo 00-protocolo/codebook_v0_oqf.csv --motivo "piloto G6: <mudanças>"`. Mudança grande: repita o piloto com textos novos.
8. **Portão**:
   ```bash
   $RS portao G6 --aprovar --por revisor_humano_1 --criterios '{"estudos_piloto": 9, "por_bloco": {"a1": 2, "a2": 2, "b1": 2, "b2": 3},
     "gate_problemas": 0, "fichas_revisadas_humano": 9, "alteracoes_codebook": 4, "emenda": "E00N",
     "modelo_subagentes": "<modelo>", "codebook": "00-protocolo/codebook_v0_oqf.csv"}'
   ```
   O script só exige o piloto consolidado (evento `extracao_consolidada` ou um `05-decomposicao/**/*fichamentos_master*.csv`; senão código 2, tipo artefato, que barra também o autopiloto); não checa o conteúdo: confirme cada critério antes. No autopiloto, abra a pendência da revisão humana antes de aprovar como `autopiloto`: `$RS pendencia abrir --tipo revisao_piloto --etapa 08_piloto_extracao --portao G6 --n 9 --arquivo 05-decomposicao/piloto_fichamentos_master.csv --descricao "conferir fichas do piloto contra os PDFs"`. Mapa de evidências sem piloto de extração: `portao G6 --nao-se-aplica` (references/00-configuracao-estado.md, seção 4).

## 6. Decomposição completa

1. Fichamento de todos os incluídos em `05-decomposicao/fichas` (mesmos parâmetros do piloto; as fichas do piloto podem ser refeitas com o codebook emendado).
2. Gate no diretório inteiro até 0 problemas (`PDF_TEXTO_NAO_EXTRAIVEL` vira conferência visual):
   ```bash
   python3 "$FS/verify_citacoes.py" --fichas 05-decomposicao/fichas --pdfs 03-textos/pdfs --out 05-decomposicao/verificacao_citacoes.csv
   ```
   O gate só confere evidências `"trecho" (p. N)`; resposta substantiva com evidência sem aspas passa em silêncio. Na revisão humana, filtre no master as colunas `*__evidencia` sem aspas.
3. Consolidação (a mensagem final precisa dizer que todas as fichas têm todas as variáveis):
   ```bash
   python3 "$FS/consolida.py" --fichas 05-decomposicao/fichas --codebook 00-protocolo/codebook_v0_oqf.csv \
     --out-csv 05-decomposicao/fichamentos_master.csv --out-xlsx 05-decomposicao/fichamentos_master.xlsx
   ```
4. Coerências a conferir no master: `mecanismo_id` = Não ⇔ `mecanismo_tipo_evidencia` = `nao_discutido`; `het_metodo` = `nenhum` ⇔ `het_pre_especificada` = `nao_se_aplica`; `tipo_estudo` = `999` (revisão ou texto sem dados) → volta à elegibilidade, não fica na base.

## 7. Efeitos: extrator, colunas, preparar e verificar

**Despacho.** Um subagente por texto b2 (até 3 em paralelo) com `agentes/extrator-efeitos.md`, entradas `chave`, `pdf`, `ficha_id` (da ficha b2), `saida` = `05-decomposicao/efeitos/<chave>.csv`, `outcomes` com `direcao_desejada` e `regra_modelo_principal`. O prompt do agente já traz as convenções da tabela abaixo, que são as de `scripts/R/efeitos.R` (`formula_id` em `assets/mapas/conversoes_efeito.csv`).

| `tipo_estatistica` | Colunas a preencher | Observação |
|---|---|---|
| `md_sd` | `m1`, `sd1`, `n1` (tratamento); `m2`, `sd2`, `n2` (comparação) | DP, nunca EP |
| `t` | `t` + `n1`, `n2` (ou `df`/`n_total`) | sem n por grupo divide ao meio (`t_ind_n_total`, `aproximado = 1`) |
| `f1` | `f`, `n1`, `n2` e fonte de sinal (`m1`/`m2`, `beta` ou `t`) | sem sinal não calcula |
| `beta_sd` | `beta`, `se` (ou `ci_lo`/`ci_hi`), `sdy` (DP de Y no controle ou linha de base), `n1`/`n2` ou `df` | `estimando` ITT, LATE, RDD_local ou ATT gera aviso: analisar separado |
| `or` | `or_`, `ci_lo`/`ci_hi` na escala OR (ou `se` de ln OR), `n_total` | |
| `r` / `parcial_r` | `r` com `n1`, `n2` (`r_d`, usa p1 = n1/N) ou só `n_total` (`r_d_n_total`, p1 = 0,5, aproximado); parcial: `r` (ou `t` do coeficiente focal), `n_total` e a coluna extra `m_preditores` (preditores com o focal, sem intercepto) | parcial = aproximado; com `m_preditores`, `parcial_r_d` do cap. 07 (r_p = t/√(t² + n − m − 1), Var = (1 − r_p²)²/(n − m)); sem ela, `parcial_r_d_gl` pelo `df` residual, com aviso |
| `p_n` | `p` exato bilateral, `n1`/`n2`, sinal em `t`, `beta` ou `m1`/`m2` | aproximado; "p < 0,05" distorce |
| `g`, `d` | valor em `beta` (ou nas colunas extras `g`/`d`), `se` ou `ci_lo`/`ci_hi`, `n1`/`n2` | `g_informado`/`d_informado`; a coluna extra prevalece sobre `beta` |
| `mann_whitney` | **z do teste em `t`**, com o sinal de tratamento − comparação conferido nas medianas ou médias; ou `p` + sinal em `beta`/`m1`/`m2`; `n1`, `n2` (ou `n_total`) | `mann_whitney_z`: r = z/√N e depois r → d; nunca t; aproximado |
| `mediana_iqr` | medianas em `m1`/`m2`, `n1`, `n2` e os quartis nas colunas extras `q1_1`, `q3_1` (tratamento), `q1_2`, `q3_2` (comparação); sem quartis, IQR (q3 − q1) em `sd1`/`sd2` | com quartis, Wan et al. 2014 (`mediana_iqr_wan`); só com IQR, média ≈ mediana e DP ≈ IQR/1,35 (`mediana_iqr_aprox`); ambos aproximados |
| `dif_prop` (desfecho binário: matrícula, evasão, emprego formal) | proporções por grupo: colunas extras `p1` (tratamento) e `p0` (comparação), com `n1`, `n2`; ou efeito em pontos percentuais de LPM, DiD ou RDD: `efeito_pp` e `se_pp` (EP do efeito em pp; sem ele, IC95 do efeito em pp em `ci_lo`/`ci_hi`, ou `n1`/`n2`), com `p0` do controle | d pelo log OR (Chinn 2000): ln OR = logit(p1) − logit(p0), d = ln OR·√3/π. Proporções brutas com `n1`/`n2` e desenho que não é de regressão: `dif_prop_contagens` (exato, variância pelas contagens da tabela 2×2). Efeito em pp, `se_pp`, ou desenho/modelo/estimando LPM, DiD ou RDD: `dif_prop_lpm` (p1 = p0 + efeito_pp/100; Var(ln OR) = (se_pp/100)²/[p1(1 − p1)]², método delta com p0 fixo; aproximado). Proporções sempre entre 0 e 1 (`0.42`, nunca `42`); sem `p0` no texto, deixe vazio e anote a dúvida: não invente |
| `rr` | razão de riscos em `or_`, IC95 na escala da razão em `ci_lo`/`ci_hi` (ou `se` = EP de ln RR), `p0` do controle | OR = RR·(1 − p0)/(1 − RR·p0) (Zhang e Yu 1998), EP(ln OR) = EP(ln RR)/(1 − RR·p0), depois d pelo log OR (`rr_logit`, sempre aproximado). RR·p0 ≥ 1 é impossível e sai sem cálculo. Razão de chances continua em `or` |

| Coluna | Convenção |
|---|---|
| `cluster`, `icc` | `cluster` = **tamanho médio do cluster (número)**, não o nome da unidade (que vai em `b2_nivel_atribuicao_cluster`); `icc` em [0, 1]. Com os dois, a variância derivada de n é multiplicada por 1 + (m − 1)·ICC; EP informado é presumido ajustado |
| `direcao_desejada` | `aumentar` ou `reduzir`, do protocolo, em TODA linha (sem ela `preparar-efeitos` recusa o lote). Sinal copiado como impresso quando o texto já orienta a estatística como tratamento − comparação; se o texto a orienta como comparação − tratamento (t de "controle vs. tratamento", indicador do grupo de comparação), o extrator troca o sinal e declara em `duvidas`, e a conferência humana confere esse sinal na página. Nunca se inverte pela direção desejada: `efeitos.R` inverte em `reduzir` e `yi > 0` passa a ser benéfico |
| `modelo_principal` | `sim` em exatamente uma linha de amostra inteira por `id_estudo` × `construto_outcome`; demais `nao`. Estudo com várias linhas sem um único principal faz `analise meta` sair com código 2 |
| `subgrupo` | vazio = amostra inteira; subgrupos entram com EP qualquer que seja o p |
| `desenho` | estratégia de identificação com o nome do desenho. Randomizados: `RCT`, `ECR`, `randomizado`, `aleatorizado`, "experimento de campo". Não randomizados: `DiD`, `pareamento`, `RDD`, `painel`...; negação e prefixos são tratados ("não randomizado", "sem aleatorização", "quase-experimental", "pseudo-randomizado" → não randomizado; "efeitos aleatórios" e "amostra aleatória" não contam como atribuição). Vazio fica vazio (`preparar-efeitos` só preenche pelo master com uma variável de desenho, como `b2_estrategia_identificacao`, nunca pelo `tipo_estudo`) e o R agrupa como `desenho_nao_informado`. Revisão só com o tipo explícito ("revisão sistemática", "meta-análise", "scoping review", "overview"...): "revisão de prontuários" e "chart review" são estudos primários |
| momento, comparação | sem coluna própria: no `outcome` (`nota_mat_12m`) ou em `modelo` |
| `pagina` | índice da página no PDF (1 = primeira do arquivo) |
| colunas extras numéricas | depois de `verificado_humano`, nesta ordem: `q1_1`, `q3_1`, `q1_2`, `q3_2`, `m_preditores`, `p0`, `p1`, `efeito_pp`, `se_pp` (ao fim mesmo vazias); colunas pedidas pelo coordenador (ex.: `familia_intervencao`, moderadores) vão depois de `se_pp`. Com `tipo_estatistica` vazio, `efeitos.R` infere `dif_prop` quando há `p0` e `p1` ou `efeito_pp` |

**Comandos.**

1. `$RS analise preparar-efeitos --master 05-decomposicao/fichamentos_master.csv --codebook 00-protocolo/codebook_v0_oqf.csv`. Grava `05-decomposicao/efeitos_extraidos.csv` com as colunas do esquema seguidas das colunas extras das entradas (minúsculas, na ordem em que aparecem: quartis, `m_preditores`, `g`/`d`, `familia_intervencao`, moderadores; as numéricas estão em `esquema.COLUNAS_EFEITOS_EXTRAS_NUMERICAS`) e registra `extracao_consolidada`; o resumo traz `colunas_extras` e `n_desenho_vazio`. Saída 1 não grava nada e lista em `05-decomposicao/efeitos_preparacao_avisos.csv` os erros (chave inválida ou fora de `registros_unicos.csv`, `id_efeito` duplicado, `tipo_estatistica` inválido, `direcao_desejada` ausente, revisão como estudo). A vírgula decimal é normalizada também nas colunas binárias. Avisos (modelo principal ambíguo, estimando fora da lista, dados insuficientes para o tipo, `desenho` vazio ou master sem variável de desenho) não bloqueiam, mas são resolvidos antes do G7.
2. `$RS analise verificar-efeitos` → `05-decomposicao/verificacao_efeitos.csv` com `status_trecho` (`OK`, `NAO_ENCONTRADA`, `PAGINA_ERRADA`, `SEM_TRECHO`, `SEM_PAGINA`, `PDF_NAO_ENCONTRADO`, `PDF_TEXTO_NAO_EXTRAIVEL`), `erros`, `alertas`, `g_aproximado`, `p_calculado`, `apto_g7`. Saída 2 = trecho falhou ou erro de plausibilidade (DP ≤ 0, n1 + n2 > N, p incoerente com t/df, IC que não contém a estimativa, OR ≤ 0, |r| > 1, `m_preditores` não inteiro ou n − m − 1 ≤ 0; nos binários: `p0`/`p1` em percentual ou fora de (0, 1), p0 + efeito_pp/100 fora de (0, 1), |efeito_pp| > 100, `se_pp` ≤ 0, p1 − p0 incoerente com `efeito_pp` além do arredondamento, RR·p0 ≥ 1; alerta para `parcial_r` sem `m_preditores` ou com `df` diferente de n − m − 1). Mudar uma coluna binária de uma linha verificada derruba `verificado_humano`, como qualquer dado do efeito. Use `--sem-irma` só se o gate da irmã falhar.
3. **Correção** sempre no CSV de origem `05-decomposicao/efeitos/<chave>.csv` (humano conferindo a página ou subagente NOVO); depois repita os passos 1 e 2. Alerta |g| > 2: conferir EP lido como DP, unidade, sinal.
4. **Verificação humana de 100%**: para cada linha, abrir a página, conferir cada número, sinal, DP × EP, n, estimando, subgrupo e modelo principal; marcar `verificado_humano = sim` em `05-decomposicao/efeitos_extraidos.csv`. Reprocessar preserva a marca (e as colunas extras) quando os dados não mudaram; se mudaram, a marca cai com aviso. PDF sem camada de texto: conferência visual obrigatória.
5. Repita `$RS analise verificar-efeitos` até `pode_seguir_g7: true` e `n_nao_aptos_g7: 0`. Toda mudança em `efeitos_extraidos.csv` (inclusive a marca humana) exige rodar `verificar-efeitos` de novo: o G7 compara o sha do arquivo com o citado no último `efeitos_verificados`.

## 8. Enriquecer efeitos e master (família, `rob_geral`)

`preparar-efeitos` preserva colunas extras, mas o `rob_geral` só existe depois da consolidação do RoB (`qualidade consolidar` fase 2, references/05-qualidade.md, seção 5), por resultado (`chave` × `construto_outcome`), em `04-qualidade/rob_geral.csv` (`chave,id_estudo,construto_outcome,ferramenta,rob_geral,validado_humano`), e a família vem do master. Não há comando que junte o RoB consolidado aos efeitos: rode este bloco depois da fase 2 e **de novo a cada `preparar-efeitos` ou nova consolidação**. Ele não altera `efeitos_extraidos.csv` (o G7 compara o sha desse arquivo): grava `05-decomposicao/efeitos_para_sintese.csv`, a entrada única da síntese quantitativa (references/07a-sintese-quantitativa.md), e `05-decomposicao/master_caixa.csv`, com o pior `rob_geral` de cada estudo para a caixa. Só entram as ferramentas de risco de viés (RoB 2, ROBINS-I, EPOC); a preocupação metodológica das checklists alimenta o CERQual, não os efeitos.

```bash
python3 - <<'PY'
import os
import pandas as pd
ler = lambda p: pd.read_csv(p, dtype=str, keep_default_na=False)
ef = ler("05-decomposicao/efeitos_extraidos.csv")
ef = ef.drop(columns=[c for c in ("familia_intervencao", "rob_geral") if c in ef])  # fontes: master e rob_geral.csv
master = ler("05-decomposicao/fichamentos_master.csv")
arq = "04-qualidade/rob_geral.csv"
rob = ler(arq) if os.path.exists(arq) else pd.DataFrame(columns=["chave", "construto_outcome", "ferramenta", "rob_geral", "validado_humano"])
rob = rob[rob["ferramenta"].isin(["rob2", "robins_i", "epoc"])]
nao_validados = rob[rob["validado_humano"] != "1"]
rob = rob[["chave", "construto_outcome", "rob_geral"]]
ordem = {"baixo_exceto_confundimento": 0, "baixo": 0, "algumas_preocupacoes": 1, "moderado": 1,
         "alto": 2, "grave": 2, "critico": 3}
assert rob["rob_geral"].isin(list(ordem)).all(), "rob_geral fora do vocabulário"
assert not rob.duplicated(["chave", "construto_outcome"]).any(), "resultado com dois julgamentos (duas ferramentas?)"
fam = master[["citekey", "familia_intervencao"]].drop_duplicates().rename(columns={"citekey": "chave"})
assert not fam.duplicated("chave").any(), "texto com mais de uma família: resolver antes"
out = ef.merge(fam, on="chave", how="left").merge(rob, on=["chave", "construto_outcome"], how="left")
assert len(out) == len(ef)
out.to_csv("05-decomposicao/efeitos_para_sintese.csv", index=False)
pior = (rob.assign(n=rob["rob_geral"].map(ordem)).sort_values("n").groupby("chave").tail(1)
        [["chave", "rob_geral"]].rename(columns={"chave": "citekey"}))
master.drop(columns=["rob_geral"], errors="ignore").merge(pior, on="citekey", how="left").to_csv(
    "05-decomposicao/master_caixa.csv", index=False)
print("efeitos sem rob_geral:", int((out["rob_geral"].fillna("") == "").sum()), "de", len(out),
      "| resultados de RoB sem validado_humano = 1:", len(nao_validados))
PY
$RS analise efeitos --in 05-decomposicao/efeitos_para_sintese.csv
```

No resumo de `analise efeitos`, exija `formulas_sem_mapa: []`, `n_sem_direcao: 0` e `n_rejeitados_revisao: 0`; confira cada `n_g_maior_2`; `n_aproximados` entra na sensibilidade; em `por_formula`, `parcial_r_d_gl` indica correlação parcial sem `m_preditores` (volte ao texto e preencha a coluna), `mediana_iqr_aprox` medianas sem quartis, `dif_prop_lpm` e `rr_logit` conversões binárias aproximadas (vão para a sensibilidade sem aproximados) e `dif_prop_contagens` proporções brutas. A caixa usa `--master 05-decomposicao/master_caixa.csv` (pior `rob_geral` do estudo, conservador). Meta-análise e SWiM leem `06-analise/efeitos.csv`, que agora carrega `rob_geral` (sensibilidade sem risco alto, `--excluir-rob critico` em `meta`, `swim` e `combinados`, `so_risco_alto` do SWiM) e `familia_intervencao` (`--grupo familia_intervencao,construto_outcome`). Sem RoB (escopo, qualitativa), o bloco só junta a família.

## 9. Validação das categóricas (κ, PABAK)

1. **Amostra** de textos, estratificada por `tipo_estudo`, com fração F = máx(0,20; 10/N) (N = textos no master; F ≤ 1) e semente registrada:
   ```bash
   python3 "$FS/amostrar_validacao.py" --consolidado 05-decomposicao/fichamentos_master.csv --classificador tipo_estudo \
     --fracao 0.2 --semente 20260915 --min-por-estrato 2 --out 05-decomposicao/amostra_validacao.csv
   ```
2. **Recodificação cega**: segundo codificador por texto, de preferência humano (no mesmo formato de ficha), sem ver a ficha existente; subagente novo só se o protocolo aceitar, com a concordância relatada como consistência entre agentes e todas as divergências arbitradas por humano (references/ia-validacao.md, seção 5). Saída em `05-decomposicao/fichas/_validacao/`, com gate.
3. **Concordância** (sinônimos opcionais: JSON `{"variavel": {"alias": "canonico"}}` com chaves em minúsculas e sem acento):
   ```bash
   python3 "$FS/concordancia.py" --original 05-decomposicao/fichas --validacao 05-decomposicao/fichas/_validacao \
     --codebook 00-protocolo/codebook_v0_oqf.csv --amostra 05-decomposicao/amostra_validacao.csv \
     --out-dir 05-decomposicao/concordancia [--sinonimos 05-decomposicao/sinonimos.json]
   ```
   Saídas: `concordancia.csv` (κ, `pabak`, `concordancia_valores`, `sinalizada`, `motivo_sinalizacao` por variável) e `RELATORIO_CONCORDANCIA.md`.

| Resultado | Tipo | Ação |
|---|---|---|
| κ ou PABAK ≥ 0,7 e concordância ≥ 80% | categórica | aceita; divergências pontuais → arbitragem humana, versão "como extraída" guardada |
| Sinalizada | categórica | redefinir o prompt (emenda), refazer as fichas de TODOS os textos com o codebook emendado, gate, nova amostra |
| Sinalizada | textual (Jaccard) | humano arbitra os textos divergentes; não obriga recodificar tudo |
| Divergência | numérica da ficha | conferir na página |
| Concordância de desenho baixa | `tipo_estudo` | reescrever o critério a1/a2 no prompt e reclassificar |
| Amostra < 10 textos | — | o relatório avisa instabilidade: amplie a amostra ou declare a limitação |

Em extrações longas, repita uma checagem menor (5 textos) no meio, porque a codificação deriva. Recomendado: humano audita também 3 a 5 fichas concordantes.

## 10. Portão G7 (parte extração) e autopiloto

G7 é um portão só, para extração e RoB: aprove uma vez, com um JSON que junte os critérios abaixo aos de RoB (references/05-qualidade.md). Parte extração: gate de citação com 0 problemas; master completo; nenhuma categórica sinalizada depois da recodificação; divergências arbitradas; `pode_seguir_g7: true` em `verificar-efeitos`; avisos de `preparar-efeitos` resolvidos; resumo de `analise efeitos` conferido; contatos com autores registrados (`textos contato-autores`).

Com `efeitos_extraidos.csv` presente, o `portao G7` sai com código 2 se: `verificar-efeitos` não rodou depois da última mudança do arquivo (artefato; a `proxima_acao` do `status` sugere o comando); há trecho fora da página ou erro de plausibilidade (artefato, barra também o autopiloto); há linha com `apto_g7` diferente de 1 (verificacao: barra a aprovação humana, vira pendência no autopiloto). Na parte RoB, fora de escopo e mapa, bloqueia sem `rob_consolidado` de cada ferramenta usada, com arquivo citado nele alterado, sem `todos_validados_humano` ou com resultado avaliado sem `rob_geral` (`04-qualidade/resultados_avaliados.csv` ou, sem ele, cada `chave` × `construto_outcome` de `efeitos_extraidos.csv`; references/05-qualidade.md, seção 7). Sobre a concordância das categóricas, só avisa: sem nenhum `05-decomposicao/**/concordancia.csv` fora do piloto, ou com variáveis sinalizadas (bloco `por_variavel` do CSV da irmã) sem pendência `concordancia_extracao` fechada para aquele arquivo. O gate das fichas não é conferido: confira antes. Pendência aberta da etapa 09 ou do G7 bloqueia a aprovação humana (código 2) até ser fechada.

```bash
$RS portao G7 --aprovar --por revisor_humano_1 --criterios '{"fichas": 42, "gate_problemas": 0,
  "concordancia": {"amostra_textos": 10, "variaveis_sinalizadas_finais": 0, "arquivo": "05-decomposicao/concordancia/concordancia.csv"},
  "efeitos": 57, "verificados_humano": 57, "kappa_min": 0.74, "pode_seguir_g7": true, "efeitos_aproximados": 6,
  "autores_contatados": 3, "autores_responderam": 1, "modelo_subagentes": "<modelo>"}'
```

No autopiloto, `analise verificar-efeitos` abre sozinho a pendência `verificacao_humana_efeitos`; a cada reexecução o `n` acompanha as linhas não aptas (a pendência é substituída, sem duplicar) e, com `pode_seguir_g7: true`, o próprio comando a fecha, em qualquer modo. Abra as demais:

```bash
$RS pendencia abrir --tipo concordancia_extracao --etapa 09_extracao_rob --portao G7 --n 12 \
  --arquivo 05-decomposicao/concordancia/concordancia.csv --descricao "arbitrar divergências da recodificação cega"
```

A arbitragem registrada é essa pendência fechada por humano com o mesmo `--arquivo` (`$RS pendencia fechar P00N --motivo "variáveis sinalizadas redefinidas e recodificadas" --por revisor_humano_1`): é o que silencia o aviso de variáveis sinalizadas no G7.

Ao fechar (`$RS pendencia fechar P00N --motivo "..." --por revisor_humano_1`), regenere a seção 8 e a síntese.

## 11. Armadilhas

| Armadilha | Como evitar |
|---|---|
| "Sem efeito" porque p > 0,05 | Direção pelo estimador; `b2_significancia_05` separada |
| Meta-análise ou revisão entrando como estudo | Não fichar; `preparar-efeitos` recusa; volta à bola de neve |
| Mesmo número extraído do artigo e da tese | Ligar relatos antes; uma linha principal por estudo × construto |
| EP lido como DP | Tabela com parênteses sem rótulo → `se`; alerta de g acima de 2 em valor absoluto |
| F, p ou Mann-Whitney sem fonte de sinal | Sinal de `m1`/`m2`, `beta` ou `t`, com trecho |
| p do Mann-Whitney convertido como t | `mann_whitney` com z em `t` |
| g e d ao mesmo tempo em `beta` e em `g` | Um lugar só; a coluna extra `g`/`d` prevalece |
| `cluster` com o nome da unidade | Número médio por cluster; unidade na ficha |
| `desenho` "sorteio" sem a raiz certa, ou vazio | Escreva "RCT (sorteio)"; não randomizados pelo nome do desenho; vazio vira `desenho_nao_informado` |
| 999 somado ou lido como número | 999 só na ficha; no CSV de efeitos, célula vazia |
| Codebook herdado sem adaptar | nenhum `{placeholder}` no G2; revisão no piloto |
| Validar pela média geral | Limiar por variável; recodificar a variável que falha |
| Corrigir `efeitos_extraidos.csv` à mão | Corrigir o CSV de origem; o consolidado é regenerado (só `verificado_humano` é marcado nele) |
| Juntar `rob_geral` só por `chave` | RoB é por resultado: `chave` × `construto_outcome` (seção 8, de `04-qualidade/rob_geral.csv`) |
| Proporção em percentual (`42`) ou efeito em proporção (`0.032`) nos binários | `p0`/`p1` entre 0 e 1; `efeito_pp` em pontos percentuais; `verificar-efeitos` recusa o resto |
| `p0` inventado para converter um efeito em pp | Sem `p0` no texto, a linha fica sem cálculo e a dúvida vai aos autores |
| Paginação misturada | Fichas: impressa + offset; efeitos: índice do PDF |

## 12. O que registrar e relatar

Registre: versão e hash do codebook (G2 e emendas); modelo e data dos subagentes; textos do piloto e mudanças; amostra, semente e resultado da concordância por variável; arbitragens; quantos efeitos verificados por humano; conversões aproximadas; contatos com autores.

| Norma | Item | Exigência |
|---|---|---|
| PRISMA 2020 | 9 | Quantos extraíram, independência, confirmação com autores, automação |
| PRISMA 2020 | 10a, 10b | Outcomes e resultados buscados, regra de escolha; demais variáveis e pressupostos sobre ausência |
| PRISMA 2020 | 12, 13b | Medida de efeito; preparação dos dados e conversões (`formula_id`) |
| PRISMA 2020 | 17, 19, 27 | Características dos estudos; estatísticas e estimativas com precisão; formulários, dados e código disponíveis |
| PRISMA-ScR | 10, 11 | Processo de charting (calibrado, independente) e variáveis |
| MECIR | C42–C51; C61, C66, C70 | Relatos por estudo, formulário pilotado, dupla extração de desfechos, dados mais detalhados, erratas, dados não publicados, conferência de magnitude e direção; escalas no mesmo sentido; grupos múltiplos; clusters |
| MAER-Net | 2.1, 2.2 | Fórmulas de transformação; dois codificadores com concordância |
| PRISMA-trAIce e RAISE | uso de IA | `$RS declaracao-ia`; o uso dos fichadores e do extrator entra pelos critérios de G6 e G7 |
