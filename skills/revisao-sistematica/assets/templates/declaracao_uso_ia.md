<!--
COMO USAR ESTE MODELO (apague este bloco antes de publicar)
1. Rode `rs.py declaracao-ia`: ele gera 07-relatorio/declaracao_uso_ia.md a partir do log
   (modelos, datas, parâmetros, papéis, prompts com sha256, validações, portões, custo,
   pendências). Este modelo é a parte narrativa que o log não sabe escrever; salve a cópia
   preenchida como 07-relatorio/declaracao_uso_ia_texto.md.
2. Nenhum número é digitado de memória: copie de 07-relatorio/declaracao_uso_ia.md, de
   02-triagem/validacao/<rodada>/*_metricas.json, estabilidade.json e dos resumos JSON dos
   comandos. Onde o log diz "não registrado", escreva "não registrado".
3. Texto entre chaves {assim} é para preencher; seções que não se aplicam dizem "Não se aplica".
4. Itens entre parênteses remetem ao PRISMA-trAIce (proposta sem endosso do PRISMA), ao
   PRISMA 2020 e ao RAISE 1; confira com assets/checklists/prisma_traice.csv.
-->

{Se `declaracao_uso_ia.md` gerado estiver marcado como RASCUNHO NÃO VALIDADO, a primeira linha desta declaração é: **RASCUNHO NÃO VALIDADO**, seguida da lista de pendências abertas copiada da seção 6 do arquivo gerado.}

# Declaração de uso de inteligência artificial: {título da revisão}

## Texto curto para o manuscrito

Usamos {modelo A, versão} e {modelo B, versão}, acessados por {subagentes do ambiente de desenvolvimento / API de {provedores}} entre {data inicial} e {data final}, para {tarefas: triagem de títulos e resumos; proposta de elegibilidade em texto completo; rascunho de extração; rascunho de respostas às perguntas-sinalizadoras de risco de viés}. {Descrever o que a IA decidiu e o que só propôs.} Os modelos não foram usados para {buscar referências, sintetizar resultados, avaliar a certeza da evidência, redigir conclusões}. Critérios e prompts versionados com sha256, saídas, código e métricas de validação estão em {repositório ou material suplementar}. {Resumo da validação com números e IC copiados das métricas.} Títulos, resumos {e PDFs} foram enviados a {provedores} sob termos que {permitem / não permitem} uso para treino; {nenhum dado pessoal foi processado}. Os autores {não têm / têm: descrever} interesses nas ferramentas. Limitações: {idioma, tamanho da validação, mudança de versão dos modelos}. Todas as decisões finais de inclusão, os juízos de risco de viés e de certeza e a síntese foram feitos por pessoas, que assumem integral responsabilidade pelo conteúdo.

## 1. Ferramentas, versões e acesso (PRISMA-trAIce M2; RAISE 1 rec. 1.9)

| Ferramenta ou modelo | Versão exata | Desenvolvedor ou provedor | Acesso | Primeiro e último uso | Parâmetros |
|---|---|---|---|---|---|
| {copiar da seção 1 do arquivo gerado} | | | {subagente / API / lote assíncrono} | | {esforço, teto de tokens; temperatura quando enviada} |

## 2. Finalidade e papel por etapa (M3; RAISE 1 rec. 1.8; I1)

| Etapa | Tarefa exata | Papel da IA (propõe, prioriza, decide) | Quem decide | Por que usar IA nesta tarefa |
|---|---|---|---|---|
| Triagem de títulos e resumos | {decisão incluir/excluir/incerto por registro, com critério e trecho} | {decide após validação / só propõe} | {humanos: incluídos, incertos, conflitos} | {volume, ganho esperado, evidência prévia} |
| Texto completo | {proposta com trecho e página} | propõe | duas pessoas | |
| Extração | | | | |
| Risco de viés | | rascunha | humano | |

## 3. Protocolo e desvios (M1)

- Plano de IA registrado em: {protocolo, versão e data do G2; registro OSF}.
- Desvios e emendas: {copiar das emendas registradas no log; "nenhum" se não houver}.

## 4. Entradas, saídas e prompts (M4, M5, M6)

- Dados enviados por registro: {título, resumo, palavras-chave, veículo, ano, tipo, idioma; trechos ou PDFs no texto completo}. Nenhum treino ou ajuste fino {ou descrever}.
- Formato da saída: JSON por registro com `decisao`, `criterio_falhou`, `justificativa`, `trecho`; respostas validadas por programa (esquema, identificadores, categorias, trecho literal); inválidas refeitas, nunca corrigidas à mão.
- Pós-processamento: {regra de consolidação `consenso` com árbitro cego / `liberal`; sem resumo = incerto; exclusão sem resumo rebaixada a incerto}.
- Prompts e critérios: {arquivos e sha256 copiados da seção 3 do arquivo gerado}; versões anteriores e o motivo de cada mudança em {local}.

## 5. Interação humano-IA (M8; PRISMA 2020 item 8)

- Revisores humanos: {número e papéis, sem nomes nos arquivos do projeto}; independência: {como}.
- Verificação: {fila humana com todas as divergências, inclusive as resolvidas pelo árbitro (override humano em cada uma); leitura de todos os incluídos e incertos; elusão; decisão humana de todo texto completo, com "aguardando classificação" quando cabível; conferência de 100% dos números extraídos}.
- Resolução de discrepâncias: {consenso, terceiro revisor, override registrado com motivo}.
- Treinamento e calibração: {calibração dupla com n, κ e concordância copiados das métricas da amostra de finalidade `calibracao`; conjunto de desenvolvimento (finalidade `desenvolvimento`) separado da validação}.

## 6. Avaliação de desempenho (M9, R2; PRISMA 2020 item 8)

| Medida | Valor (IC 95%) | Fonte no projeto |
|---|---|---|
| Padrão de referência | {dupla humana cega com consenso} | planilha da amostra |
| Amostra de validação | {n; incluídos humanos; enriquecimento; reponderação; IDs de calibração e desenvolvimento excluídos do quadro} | `amostraNN_desenho.json` (finalidade `validacao` da rodada ativa: a que decide o G4) |
| Sensibilidade (recall) | {valor (LI–LS)} | `amostraNN_metricas.json` |
| Especificidade, precisão, VPN | | idem |
| κ e PABAK (IA × humanos) | | idem |
| WSS | | idem |
| Limiar pré-especificado e resultado | recall ≥ 0,95 com limite inferior ≥ 0,90: {atende / não atende} | idem |
| Elusão | {n lidos; taxa; incluídos perdidos estimados e limite superior} | `elusaoNN_metricas.json` |
| Estabilidade | {% reexecutado; concordância; mudanças de seguimento} | `estabilidade.json` |
| Calibração e desenvolvimento (histórico) | {κ humano da calibração; métricas das versões de desenvolvimento, que não decidem} | seção de histórico do arquivo gerado |
| Extração categórica | {variáveis; κ ou PABAK; concordância; sinalizadas} | relatório de concordância do fichamento |
| Números de efeito verificados | {n verificados / n extraídos} | `05-decomposicao/verificacao_efeitos.csv` |

Análise de erros: {causas dos falsos negativos e o que mudou na versão seguinte}. Se o limiar não foi atingido: {remédio adotado e por quê; se inalcançável pelo número de incluídos, dizer isso com o limite inferior máximo possível}.

## 7. Seleção: decisões de IA e de humanos (R1; PRISMA 2020 item 16a)

{Quantos registros foram excluídos por IA validada, quantos por humanos, quantos por filtro automático previsto no protocolo; copiar de 07-relatorio/prisma_contagens.json e de triagem_ta_final.csv (`decidido_por`).}

## 8. Governança de dados, direitos e ética (M10; RAISE 1 rec. 1.10)

- Provedores e termos: {uso para treino, retenção, localização dos dados}.
- Consentimento para o modo API: {data e registro no protocolo ou emenda}.
- Direitos autorais dos textos enviados: {acesso aberto / licença / não enviados}.
- Dados pessoais e LGPD: {não houve / base legal e medidas}.

## 9. Interesses e financiamento (RAISE 1 rec. 1.9)

{Relação dos autores com desenvolvedores ou provedores; custo de API registrado (copiar do arquivo gerado, que soma o custo estimado de cada execução da `triagem api` pela tabela de preços registrada e lista à parte as estimativas de `--estimar`) e quem pagou.}

## 10. Limitações e impacto (D1)

{Validação feita em {idiomas}; recall por idioma quando houver volume; modelos comerciais podem mudar sem aviso; concordância entre agentes mede consistência e não acurácia; falhas técnicas e como foram tratadas; efeito provável nos achados.}

## 11. Responsabilidade humana (RAISE 1 rec. 1.1)

As ferramentas de IA foram usadas como apoio, sob supervisão humana, nos papéis descritos acima. Critérios, protocolo, decisões finais de elegibilidade, juízos de risco de viés e de certeza, rótulos da caixa de ferramentas, síntese e conclusões são responsabilidade dos autores, que conferiram as saídas conforme os portões e as validações registradas.
