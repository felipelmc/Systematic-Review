# Tipos de revisão: árvore de escolha e matriz

Leia antes de propor o tipo ao usuário (etapa 1) e sempre que o pedido for ambíguo ("revisão narrativa", "revisão da literatura"). O tipo escolhido vai para `init --tipo <valor>` (provisório; `--variante rapida` para revisão rápida) e é fixado no G1 por `portao G1 --aprovar --por revisor_humano_1 --criterios '{"pergunta": "...", "tipo_revisao": "<valor>"}'`. `$RS` abrevia `python3 "<pasta da skill>/scripts/rs.py"` (SKILL.md, "Como chamar os comandos"): em cada chamada de Bash, use a função `rs` definida na mesma chamada ou o caminho completo, nunca uma variável `RS`.

## Sumário

1. Regras de uso
2. Árvore de escolha (perguntas em ordem)
3. Matriz A: pergunta, busca, triagem, risco de viés, codebook
4. Matriz B: síntese, certeza, relato, portões e suporte na v1
5. Etapas e portões que não se aplicam a cada tipo
6. Variante rápida
7. O que não é revisão sistemática
8. Títulos por tipo
9. Armadilhas

## 1. Regras de uso

| Regra | Operação |
|---|---|
| Tipo ≠ técnica | O tipo (nível médio) vai no título e define busca, avaliação e relato; a técnica (meta-análise, SWiM, síntese temática, QCA) vai nos métodos. "Meta-análise" é sempre técnica |
| Valores aceitos | Só os de `esquema.TIPOS_REVISAO`: `efetividade_meta`, `efetividade_swim`, `oqf_mista_sequencial`, `escopo`, `mapa_evidencias`, `qualitativa`, `realista`, `metodos_mistos`, `rapida`, `guarda_chuva`. Antes do G1 pode ficar `indefinido`, mas o G1 não aprova com `indefinido` nem sem pergunta (código 2). Variante: só `rapida` (`--variante`; seção 6) |
| Mudar o tipo | Antes do G1: `$RS init --tipo <novo>` (sem `--titulo`). Depois do G1, `init` só avisa e não muda; registre a emenda em `00-protocolo/emendas.md` e reaprove o G1 com o novo `tipo_revisao` nos critérios |
| Efeito com comparabilidade incerta | Escolha `efetividade_swim` ou `oqf_mista_sequencial` e escreva no protocolo as duas rotas (com e sem meta-análise); a decisão final sai do checklist de comparabilidade na síntese |
| Tipos só reconhecidos na v1 | `mapa_evidencias`, `realista`, `guarda_chuva` e QCA dentro de `metodos_mistos`: a skill orienta, mas avise o usuário de que não há comandos dedicados (EGM interativo, iteração realista, CCA, QCA computacional) |

## 2. Árvore de escolha

Faça as perguntas nesta ordem e registre as respostas em `00-protocolo/pergunta.md`.

| Passo | Pergunta ao usuário | Resposta → decisão | `--tipo` |
|---|---|---|---|
| 1 | Qual decisão a revisão vai informar e quem vai usar? Há uma pergunta clara (X e ao menos um Y)? | Não → refine antes de qualquer busca; tema amplo demais → considere escopo ou mapa | `indefinido` até decidir |
| 2 | Existe RS recente e de qualidade com a mesma pergunta, publicada ou registrada em andamento? (como checar: leia também references/01-pergunta-protocolo.md) | Sim, boa e atual → não duplicar: divulgar, mudar o ângulo ou fazer overview. Desatualizada ou enviesada → atualizar ou RS nova justificada | — |
| 3 | A unidade de análise serão revisões? A pergunta é mais ampla que as RS e os dados estão nelas? | Sim → overview | `guarda_chuva` |
| 4 | O objetivo é mapear o que existe e as lacunas? | Produto = matriz intervenção × resultado para priorizar pesquisa → mapa; senão → escopo | `mapa_evidencias` / `escopo` |
| 5 | O objetivo é saber se e quanto uma intervenção funciona? | Também como, para quem, onde, implementação, percepção e custo → OQF. Só efeito: estudos provavelmente comparáveis → meta; não ou incerto → SWiM | `oqf_mista_sequencial` / `efetividade_meta` / `efetividade_swim` |
| 6 | O objetivo são significados, experiências ou percepções? | Síntese de evidências qualitativas | `qualitativa` |
| 7 | O objetivo são mecanismos e contextos? | Refinar teoria de programa (CMO) → realista; configurações de condições → métodos mistos com QCA | `realista` / `metodos_mistos` |
| 8 | O objetivo é avaliar a literatura contra critérios (revisão crítica ou metodológica)? | Sem valor próprio na v1: se for mapear métodos, use `escopo` e declare; senão explique o limite | `escopo` ou nenhum |
| 9 | A decisão precisa sair em semanas ou poucos meses, com demandante definido? | Sim → variante rápida do tipo escolhido acima, com atalhos declarados já no G1 | tipo de origem + `--variante rapida` (seção 6) |
| 10 | Há equipe (≥ 2 pessoas, uma com método e estatística) e horas suficientes? (referência: mediana de ~1.100 horas por meta-análise; 9 a 12 meses de uma pessoa em tempo integral) | Não → reduzir escopo, variante rápida declarada ou outro produto | — |

Escala da pergunta: (1) ampla, de problema ("o que funciona para Y?") → mapa, escopo ou uma RS por família de intervenção; (2) X sobre Y e (3) X sobre vários Y → OQF ou efetividade.

## 3. Matriz A: pergunta, busca, triagem, risco de viés, codebook

| Tipo (`--tipo`) | Framework | Busca | Triagem | Qualidade / risco de viés | Família de codebook (`assets/codebooks/`) |
|---|---|---|---|---|---|
| Efetividade com meta-análise (`efetividade_meta`) | PICO ou PICOC | Abrangente: ≥ 2 bases, base regional, teses, cinzenta, citações | Dupla e independente (humana ou IA validada) | Por domínio, ferramenta por desenho (RoB 2, ROBINS-I V2, EPOC) | `oqf_decomposicao.csv` só com o bloco comum e o b2, como `00-protocolo/codebook_v0_efetividade.csv` (references/01-pergunta-protocolo.md, seção 10, passo 7); efeitos com números verificados por `agentes/extrator-efeitos.md` |
| Efetividade sem meta-análise (`efetividade_swim`) | PICO ou PICOC | Idem | Idem | Idem | Idem, direção pelo estimador |
| OQF mista e sequencial (`oqf_mista_sequencial`) | PICOC + CMMO + DAG (X, Y, M, Z) | Abrangente; blocos de X e Y em PT/EN/ES; bases internacionais e brasileiras | ≥ 2 revisores + desempate | Por bloco: b2 RoB 2/ROBINS-I; a1/b1 CASP ou JBI QARI; a2 JBI transversal; mistos MMAT | Decomposição formal, metodológica e substantiva com classificador `tipo_estudo` (a1/a2/b1/b2) |
| Escopo (`escopo`) | PCC | Exaustiva, com cinzenta | Piloto de 25 registros com concordância ≥ 75% antes de começar | Não obrigatória; se usada, prevista no protocolo com finalidade | *Charting* PCC padronizado e pilotado |
| Mapa de evidências e lacunas (`mapa_evidencias`) | PICOS; linhas e colunas = intervenções × resultados | Sistemática; abrir as RS incluídas para achar estudos | Critérios explícitos | Recomendada, não obrigatória (pode ser só das RS) | Framework do mapa pilotado com 20-30 estudos; sem direção nem tamanho de efeito |
| Síntese qualitativa (`qualitativa`) | PICo, SPIDER ou PerSPEcTiF | Agregativa: abrangente; interpretativa: amostragem teórica | Dupla | CASP ou JBI QARI | Achados com trechos (codebook qualitativo) |
| Realista (`realista`) | CMO / CMOC | Intencional e iterativa, buscas dirigidas até saturação; admite material que não é estudo | Por relevância para a teoria | Relevância e rigor para a teoria | Configurações contexto-mecanismo-resultado |
| Métodos mistos, incl. QCA (`metodos_mistos`) | Pergunta geral + subperguntas quanti e quali | Abrangente para os dois tipos; atenção a relatos "irmãos" | Dupla | Por desenho de cada estudo (MMAT para mistos primários) | Blocos quanti e quali; condições calibradas (QCA) |
| Rápida (`rapida`) | PICOS definido com usuários, limitado | Bases principais + 1-2 especializadas; PRESS de ao menos uma estratégia | Piloto 30-50 resumos; dupla em ≥ 20% e segunda leitura de todos os excluídos | Um avaliador com verificação integral por outro | Conjunto mínimo de itens |
| Guarda-chuva / overview (`guarda_chuva`) | Pergunta mais ampla que a das RS | Revisões como unidade; definir o que conta como RS | Dupla; gerir sobreposição na seleção | AMSTAR 2 ou ROBIS | Dados das RS + matriz de citação dos primários |

## 4. Matriz B: síntese, certeza, relato, portões e suporte

| `--tipo` | Síntese (comandos) | Certeza | Relato (`$RS prisma`) | Portões mínimos | Na v1 |
|---|---|---|---|---|---|
| `efetividade_meta` | Checklist de comparabilidade; `analise efeitos` → `analise meta` | GRADE por desfecho | PRISMA 2020 (`prisma`) + PRISMA-S | G1-G9 | Suportado |
| `efetividade_swim` | `analise efeitos` → `analise swim` | GRADE (sem MA: Murad 2017) | PRISMA 2020 + SWiM | G1-G9 | Suportado |
| `oqf_mista_sequencial` | Quanti (`analise meta` ou `analise swim`) → mecanismos e moderadores → implementação, percepção, custo (`agentes/sintetizador-quali.md`) → integração → `caixa` | GRADE por célula de efeito; CERQual por achado | PRISMA 2020 + SWiM + ENTREQ, formato de artigo OQF | G1-G9 | Suportado |
| `escopo` | Mapeamento descritivo em tabelas e gráficos; sem meta-análise | Não se aplica | PRISMA-ScR (`prisma` usa `scr` por padrão) | G1-G6, G9; G7 e G8 dispensáveis com `--nao-se-aplica` | Suportado |
| `mapa_evidencias` | Distribuição de estudos pelas células; não resume o que a evidência diz | Não se aplica | Orientação Campbell para EGM; fluxo com `prisma` (padrão `scr`) como aproximação declarada | G1-G5, G9; G6, G7 e G8 dispensáveis com `--nao-se-aplica` | Reconhecido (EGM interativo na v2) |
| `qualitativa` | Meta-agregação, síntese temática ou meta-etnografia (`agentes/sintetizador-quali.md`) | GRADE-CERQual (juízos humanos) | ENTREQ; eMERGe se meta-etnografia | G1-G9 | Suportado |
| `realista` | Teoria refinada em CMOCs (humano dono da teoria) | Enunciado narrativo, sem pseudo-GRADE | RAMESES I | G1, G2, G8, G9 obrigatórios; G3, G5-G7 adaptados à iteração; G4 dispensável com `--nao-se-aplica` | Reconhecido (iteração completa na v2) |
| `metodos_mistos` | Convergente ou sequencial; QCA com calibração humana | GRADE e CERQual por componente; QCA narrativo | PRISMA 2020 + ENTREQ | G1-G9 + calibração QCA como decisão humana | Mistos suportados; QCA computacional na v2 |
| `rapida` (ou `--variante rapida`) | A do tipo de origem; meta-análise só com estudos semelhantes | GRADE por um avaliador com verificação | Relato do tipo de origem, com atalhos declarados | Os do tipo de origem; a variante não dispensa portões, mas o G4 aceita o atalho de dupla humana parcial quando `atalho_rapida` foi aprovado no G1 (seção 6) | Suportado como variante |
| `guarda_chuva` | Resumo das RS sem contar duas vezes o mesmo estudo; CCA | GRADE por desfecho | PRIOR | G1-G9 (G7 inclui AMSTAR 2/ROBIS e sobreposição) | Reconhecido (CCA na v2) |

## 5. Etapas e portões que não se aplicam a cada tipo

Duas formas de lidar com uma etapa que o tipo dispensa:

1. **Portão dispensável pelo tipo** (`esquema.PORTOES_OPCIONAIS_POR_TIPO`: `escopo` G7 e G8; `mapa_evidencias` G6, G7 e G8; `realista` G4): depois do G1 aprovado, `$RS portao G8 --nao-se-aplica --por revisor_humano_1 --motivo "revisão de escopo: sem síntese de efeito, certeza nem caixa"`. A etapa fica `ignorada` no `status` (`fonte: nao_se_aplica`), o evento `etapa_nao_aplicavel` vai para o log e o portão deixa de ser exigido na ordem. Em checkpoints só humano dispensa; no autopiloto `--por autopiloto` abre `revisao_humana_portao`. Se a etapa voltar a existir, aprove ou reprove o portão normalmente. Use a dispensa quando a etapa inteira não existe no tipo; quando parte dela existe (ex.: o *charting* completo de um escopo no G7, sem RoB), aprove o portão com os critérios da parte que existe.
2. **Demais tipos e portões**: não há dispensa no script (tentar sai com código 2). Faça o que o tipo pede naquela etapa (ou nada), escreva "Não se aplica: <motivo>" na seção do protocolo e aprove o portão declarando isso nos critérios, por exemplo `$RS portao G8 --aprovar --por revisor_humano_1 --criterios '{"nao_se_aplica": "meta-análise e caixa (revisão qualitativa)", "produto": "síntese temática com CERQual"}'`. As checagens do portão continuam valendo (ex.: o G8 bloqueia se houver `caixa_ferramentas.csv` com célula não definida).

| `--tipo` | Não se aplica ou muda | Onde isso aparece |
|---|---|---|
| `efetividade_meta`, `efetividade_swim` | Síntese qualitativa e `caixa` (opcionais) | G8 |
| `oqf_mista_sequencial` | Nada; todas as etapas | — |
| `escopo` | Risco de viés (G7 só extração, ou `--nao-se-aplica` se o *charting* fechou no G6); `analise efeitos/meta/swim`, certeza e `caixa` (G8 `--nao-se-aplica` ou mapeamento descritivo); recomendações de política | G7, G8, relato |
| `mapa_evidencias` | Piloto de extração (G6), direção e tamanho de efeito na extração (G7); certeza; `caixa` (G8); os três dispensáveis | G6, G7, G8 |
| `qualitativa` | `analise efeitos/meta/swim`, verificação de efeitos, GRADE | G7, G8 |
| `realista` | Fluxo linear a priori; triagem por critérios fixos (vira relevância para a teoria; G4 dispensável); GRADE | G3-G7 adaptados; relatar iterações |
| `metodos_mistos` | QCA sem comando: tabela-verdade e calibração fora da skill, registradas | G8 |
| `rapida` ou variante rápida | Etapas cortadas pelos atalhos combinados no G1 (sem dispensa automática de portão; no G4, caminho próprio do atalho de triagem) | Todos os portões afetados; atalhos escritos no protocolo antes do G2 (os decididos depois, em `00-protocolo/emendas.md`) |
| `guarda_chuva` | Estudos primários como unidade; `analise meta` sobre efeitos de estudos sobrepostos | G5, G7, G8 |

## 6. Variante rápida

A revisão rápida é variante de um tipo de origem, guardada em `projeto.variante` sem trocar `tipo_revisao`:

1. `$RS init --titulo "..." --tipo efetividade_swim --variante rapida` (num projeto existente, antes do G1: `$RS init --variante rapida`).
2. Aprove o G1 com o tipo de origem, a variante e os atalhos: `$RS portao G1 --aprovar --por revisor_humano_1 --criterios '{"pergunta": "...", "tipo_revisao": "efetividade_swim", "variante": "rapida", "atalho_rapida": true, "atalhos": ["triagem simples com dupla humana em 20% e segunda leitura de todos os excluídos", "sem busca de teses"], "prazo": "8 semanas"}'` (variante diferente de `rapida` sai com código 1). `atalho_rapida: true` só quando o protocolo usa a triagem com dupla humana parcial: é o que habilita o caminho do atalho no G4.
3. Siga a matriz do tipo de origem em todas as etapas, exceto nos atalhos. A variante não dispensa portões: todo atalho que corta uma etapa é aprovado no portão com o desvio declarado nos critérios. A exceção é o G4 (passo 5).
4. Escreva cada atalho combinado no G1 no próprio protocolo, na seção do método que ele altera, antes do G2: atalho planejado é método do protocolo, não emenda. Só atalho decidido depois do G2 vira entrada em `00-protocolo/emendas.md` (tipo B ou C, com a etapa e o que já se sabia dos resultados). Declare todos no relato como limitação do processo (PRISMA 2020 item 23c). Atalhos comuns e o que custam (Cochrane Rapid Reviews Methods Group): dupla triagem de ≥ 20% dos resumos com uma pessoa no restante e segunda leitura de todos os excluídos; RoB, extração e GRADE por uma pessoa com verificação integral por outra; PRESS de ao menos a estratégia principal.
5. **G4 pelo atalho da triagem.** Com `projeto.variante = rapida` e `atalho_rapida` verdadeiro na última aprovação do G1, o G4 aceita, no lugar do recall ≥ 0,95 com LI ≥ 0,90, uma validação (`finalidade validacao`) marcada com `atalho_rapida = true` que tenha: dupla humana em ≥ 20% dos registros (`fracao_dupla_humana`, ou `n_dupla_humana`/`n_populacao`; abaixo de 20%, bloqueio de limiar), κ da dupla calculado (`kappa_humanos`) e segunda leitura humana de todos os excluídos pela IA (`segunda_leitura_excluidos = true`, ou `n_excluidos_relidos >= n_excluidos_ia`). O portão avisa para declarar o atalho como limitação do processo (PRISMA 2020 item 23c). Sem `atalho_rapida` no G1, vale a regra geral, com aviso.

   Os campos saem de `validar`, nesta ordem, com a rodada da IA já mesclada (e consolidada):

   | Passo | Comando | O que grava |
   |---|---|---|
   | Dupla humana em ≥ 20% | `$RS validar amostrar --etapa ta --rodada ta_vN --n <≥ 20% dos registros da rodada> --semente <s> --atalho-rapida` (dois codificadores, às cegas) | desenho com `atalho_rapida: true`; aviso se `--n` não chega a 20% ou se o projeto não é variante rápida |
   | κ e fração | `$RS validar calcular --planilha 02-triagem/validacao/ta_vN/amostraNN_cega.xlsx` (desenho sorteado sem a flag: acrescente `--atalho-rapida`) | no `validacao_calculada`: `atalho_rapida`, `fracao_dupla_humana` (registros com dois códigos humanos ÷ registros ativos da rodada), `n_dupla_humana`, `n_populacao`, `kappa_humanos`, `n_excluidos_ia`, `n_excluidos_relidos`, `segunda_leitura_excluidos`; código 2 enquanto faltar algum requisito, com a `proxima_acao` do que falta |
   | Segunda leitura dos excluídos | sorteie o restante com `$RS validar elusao --etapa ta --rodada ta_vN --n <n_excluidos_ia> --semente <s>` (ou use uma planilha própria com `id_rs` e `decisao_humana`), releia e registre: `$RS validar segunda-leitura --rodada ta_vN --planilha <planilha codificada>` (repita com outras partes: as leituras acumulam) | `02-triagem/validacao/ta_vN/segunda_leitura.json`; `segunda_leitura_resgatados.csv` com os excluídos que a leitura manda seguir; `validacao_calculada` com `tipo segunda_leitura` e finalidade `elusao` (não decide o G4). Os excluídos já codificados na amostra da dupla contam como relidos |
   | Resgatados | `$RS triagem override --fila 02-triagem/validacao/ta_vN/segunda_leitura_resgatados.csv --rodada ta_vN` e `$RS triagem consolidar --rodada ta_vN` | overrides humanos (os resgatados seguem ao texto completo) |
   | Fechar | `$RS validar calcular --planilha <a mesma da dupla>` de novo | o evento passa a trazer `segunda_leitura_excluidos: true`; código 0 com os três requisitos atendidos |

   Depois peça a aprovação humana do G4 com os valores do evento: `$RS portao G4 --aprovar --por revisor_humano_1 --criterios '{"atalho_rapida": true, "fracao_dupla_humana": <valor>, "kappa_humanos": <valor>, "segunda_leitura_excluidos": true}'`. A planilha da segunda leitura pode voltar do Excel em CSV (vírgula, ponto e vírgula ou tabulação; UTF-8, UTF-16 ou cp1252) ou `.xlsx`.

O valor `rapida` em `--tipo` continua aceito por compatibilidade, mas perde o tipo de origem: prefira `--variante`.

## 7. O que não é revisão sistemática

Um trabalho só é tratado como RS se tiver: pergunta e objetivos claros; critérios em protocolo antes da busca; busca documentada em ≥ 2 bases; triagem e seleção; avaliação dos estudos incluídos (exceto escopo e mapa, que se nomeiam como tais); síntese dos dados extraídos; relato transparente.

| Pedido | Resposta da skill |
|---|---|
| "Revisão narrativa" ou "revisão da literatura" | Pergunte o que o usuário quer: resumo de especialista (não abrir projeto; não chamar de RS) ou "o que a evidência diz" (seguir a árvore) |
| Só bibliometria | Não é RS: use como exploração da busca ou parte de uma revisão de escopo; nunca como filtro de inclusão |
| "Resumo de literatura por IA" | Não é RS: sem protocolo nem busca reproduzível. Ofereça RS (ou escopo) com IA dentro de etapas validadas |
| Busca numa base só, sem avaliação | No máximo "revisão sistematizada": declarar a limitação no título ou completar as etapas |
| Meta-análise sem busca sistemática | Embutir a meta-análise numa RS |

## 8. Títulos por tipo

| `--tipo` | Formato |
|---|---|
| `efetividade_meta`, `efetividade_swim` | [Intervenção] para [melhorar/reduzir] [resultado] em [população] em [local]: uma revisão sistemática (com meta-análise) |
| `oqf_mista_sequencial` | Pergunta X → Y? + subtítulo "evidências de uma revisão sistemática mista e sequencial" |
| `escopo` | [Conceito] em [população] em [contexto]: uma revisão de escopo (não formular como pergunta) |
| `mapa_evidencias` | [Intervenção] para [população/problema]: um mapa de evidências e lacunas |
| `qualitativa` | [Experiências/significados] de [fenômeno] em [contexto]: síntese de evidências qualitativas |
| `realista` | [Intervenção] para [resultado]: revisão realista |
| `rapida` | [Tema]: revisão rápida (tipo de origem no subtítulo) |
| `guarda_chuva` | [Tema]: overview de revisões sistemáticas |

## 9. Armadilhas

| Armadilha | Consequência | Como a skill evita |
|---|---|---|
| Revisão de escopo para responder "funciona?" | Sem risco de viés nem achado-resumo | Passos 4 e 5 da árvore; escopo não gera recomendação |
| RS e meta-análises contadas como estudos primários | Dupla contagem | Critério C5 (estudo primário) no protocolo; revisões viram sementes da bola de neve e fonte de âncoras; se forem a unidade, o tipo é `guarda_chuva` |
| Decidir "com meta-análise" sem rota alternativa | Plano quebra quando os estudos não são comparáveis | Protocolo com as duas rotas; `analise meta --k-min 3` |
| `rapida` sem atalhos declarados, ou como tipo em vez de variante | Não é possível avaliar o que foi cortado nem saber o tipo de origem | Seção 6 (`--variante rapida` e `atalhos` no G1) |
| Nomear pela técnica ("análise temática da literatura") | Leitor não sabe que busca e avaliação esperar | Tipo no título, técnica nos métodos |
| OQF tratada como método misto convergente do JBI | Integração sem regra | Regras de integração e da caixa escritas no protocolo |
