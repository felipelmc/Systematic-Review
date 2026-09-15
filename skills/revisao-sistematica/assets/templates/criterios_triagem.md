<!--
COMO USAR ESTE MODELO (apague este bloco inteiro antes de salvar)
1. Copie para 02-triagem/prompts/ta_v1.md (a versão sobe a cada mudança: ta_v2.md, ta_v3.md...).
2. Troque todo texto entre chaves {assim} pelo conteúdo do protocolo congelado no G2.
3. Mantenha os identificadores de critério no formato C + número, em ordem de aplicação,
   no início do cabeçalho de cada critério, como nas seções abaixo: os scripts leem daqui a
   lista de critérios válidos para o campo criterio_falhou, só das linhas que começam pelo
   identificador (menções no meio do texto, como "ver C5", não entram).
4. Exemplos VÁLIDO/INVÁLIDO saem do conjunto de desenvolvimento (calibração), nunca da
   amostra de validação.
5. Depois de usado numa rodada, este arquivo não muda: qualquer alteração, mesmo de uma
   palavra, vira nova versão e nova rodada.
-->

# Critérios de triagem de títulos e resumos: {título curto da revisão}

| Campo | Valor |
|---|---|
| Versão | ta_v{N} |
| Data | {AAAA-MM-DD} |
| Protocolo de referência | {00-protocolo/protocolo.md, versão e data do G2} |
| Mudanças em relação à versão anterior | {"primeira versão" ou lista objetiva do que mudou e por quê} |
| Motivo da nova versão | {calibração humana abaixo do limiar / falsos negativos analisados / emenda ao protocolo} |

## Pergunta da revisão

{Pergunta no formato do protocolo, por exemplo PICOC: população, intervenção, comparação, desfechos e contexto; ou PCC em revisão de escopo.}

## Como decidir

Você decide apenas com o título, o resumo e os metadados do registro. Aplique os critérios **na ordem numerada abaixo**:

1. No primeiro critério que o título ou o resumo mostram **com clareza** que não é atendido, pare. A decisão é `excluir`, e o critério que falhou é o identificador desse critério.
2. Se todos os critérios são atendidos ou plausivelmente atendidos, a decisão é `incluir`.
3. Se o título e o resumo não bastam para saber se algum critério é atendido, a decisão é `incerto`. Informe o critério em dúvida, se houver um.

Regras que valem para todos os critérios:

- **Na dúvida, não exclua.** Entre `excluir` e `incerto`, escolha `incerto`: nesta etapa, perder um estudo elegível custa mais do que ler um texto completo a mais.
- **Sem resumo, `incerto`.** Registro sem resumo nunca é excluído. Só é `incluir` se o próprio título mostrar, sem margem, que todos os critérios são atendidos.
- **Resumo truncado.** Decida pelo que existe; se a parte que falta seria decisiva, `incerto`.
- **Idioma não é critério.** Registros em português, inglês, espanhol ou outro idioma são avaliados pelo conteúdo.
- **Não use conhecimento externo** sobre autores, periódicos ou o estudo.

## Estudar não é mencionar

Um critério sobre população, intervenção, exposição ou desfecho só é atendido quando isso é **objeto da análise** do estudo: a política ou o programa é o tratamento, a exposição ou o foco central; o desfecho é medido ou analisado. Não basta aparecer como contexto, motivação, recomendação na conclusão ou referência a outro trabalho.

- VÁLIDO: "Avaliamos o efeito de {intervenção} sobre {desfecho} com dados de {fonte e período}."
- VÁLIDO: "Entrevistamos gestores sobre a implementação de {intervenção} em {contexto}."
- INVÁLIDO: "Medimos {desfecho} e concluímos que políticas como {intervenção} poderiam ajudar."
- INVÁLIDO: "Num contexto marcado por {intervenção}, analisamos {outro tema}."
- INVÁLIDO: "Revisamos a literatura sobre {intervenção}" (revisão não é estudo primário; ver C5).

## Critérios, na ordem de aplicação

### C1. População e contexto

- **Pergunta:** o estudo analisa {população ou unidade: municípios, escolas, contribuintes...} em {contexto: país, nível de governo, setor}?
- **Atende quando:** {definição operacional}.
- **Não atende quando:** {definição operacional; por exemplo, outro país sem comparação com o contexto do protocolo}.
- VÁLIDO: "{trecho curto do conjunto de desenvolvimento}"
- INVÁLIDO: "{trecho curto do conjunto de desenvolvimento}"
- **Na dúvida** (contexto não informado no resumo): `incerto`.

### C2. Intervenção estudada

- **Pergunta:** {a intervenção ou política} é estudada como objeto empírico (tratamento, exposição ou foco central)?
- **Atende quando:** {programas, leis ou ações que contam; sinônimos e siglas relevantes}.
- **Não atende quando:** a intervenção só é mencionada; ou é outra intervenção, como {exemplo de intervenção vizinha que não conta}.
- VÁLIDO: "{trecho}"
- INVÁLIDO: "{trecho}"
- **Na dúvida:** `incerto`.

### C3. Desfecho

- **Pergunta:** o estudo mede ou analisa {desfechos do protocolo} ou {mecanismos, implementação, percepções ou custos ligados a eles, se o protocolo os aceitar}?
- **Atende quando:** {lista de desfechos e medidas aceitas}.
- **Não atende quando:** {desfechos fora do protocolo; discussão só normativa do tema}.
- VÁLIDO: "{trecho}"
- INVÁLIDO: "{trecho}"
- **Na dúvida:** `incerto`. Não exclua porque o resumo não traz números: dados de desfecho utilizáveis não são critério de triagem. Não exclua porque o resumo não cita o desfecho do protocolo: resumos costumam listar só os resultados principais; exclua por este critério só quando o estudo claramente trata de outro fenômeno.

### C4. Desenho

- **Pergunta:** o desenho está entre os aceitos pelo protocolo, com o comparador exigido: {desenhos aceitos, por exemplo experimentos, quase-experimentos com grupo de comparação, estudos qualitativos com entrevistas}?
- **Atende quando:** {definição pelas características do desenho (formação dos grupos, nível de atribuição), não pelo rótulo que os autores dão}.
- **Não atende quando:** {desenhos excluídos no protocolo}. Se o registro é revisão, meta-análise, editorial ou ensaio sem dados próprios, não use este critério: aplique C5.
- VÁLIDO: "{trecho}"
- INVÁLIDO: "{trecho}"
- **Na dúvida** (método não descrito no resumo): `incerto`.

### C5. Estudo primário

- **Pergunta:** é um estudo primário com análise própria de dados?
- **Atende quando:** o estudo produz ou analisa dados próprios {quantitativos, qualitativos ou ambos, conforme o protocolo}.
- **Não atende quando:** revisão de literatura, revisão sistemática, meta-análise, editorial, ensaio teórico ou normativo sem dados, {outros tipos excluídos no protocolo}. Em revisões e meta-análises, escreva na justificativa "revisão: usar na bola de neve".
- VÁLIDO: "{trecho}"
- INVÁLIDO: "{trecho}"
- **Na dúvida:** `incerto`.

{Apague esta observação. Os identificadores C1 a C5 seguem a tabela de elegibilidade do protocolo (`assets/templates/protocolo.md`, seção 4) e o codebook de elegibilidade (`c1_populacao_contexto` a `c6_nao_retratado`). C6 (sem retratação) é conferido no texto completo, no OpenAlex e na Crossref, e não entra nesta triagem. Se o protocolo tiver outro critério, acrescente uma seção no mesmo formato com o identificador que ele tem no protocolo; se não tiver algum destes, apague a seção e mantenha a numeração do protocolo.}

## O que não é critério nesta etapa

- Acesso ao texto completo, idioma, tipo de periódico ou reputação dos autores.
- Qualidade metodológica ou risco de viés (avaliados depois, com ferramenta própria).
- Significância estatística ou direção do resultado.
- Presença de dados de desfecho utilizáveis no resumo.

## Casos de calibração

{Três a seis casos resolvidos na calibração humana, cada um com: título resumido; decisão (incluir, excluir ou incerto); critério decisivo (identificador do critério ou nenhum); uma frase explicando a decisão. Use só registros do conjunto de desenvolvimento.}
