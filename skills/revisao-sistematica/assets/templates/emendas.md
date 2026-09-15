# Log de emendas ao protocolo

<!--
Como usar este arquivo
- Copie para 00-protocolo/emendas.md ANTES do G2. Arquivos de 00-protocolo/ cujo nome começa
  com "emenda" não são congelados no G2: este log continua editável depois do congelamento.
- Uma entrada por decisão, na ordem em que foram tomadas. Nunca apague entradas antigas.
- Escreva a entrada ANTES de alterar o artefato congelado. Depois de alterar, rode
  `$RS emenda --arquivo <arquivo alterado> --motivo "E00N: <resumo>" --por <papel>`
  e copie para a entrada o campo `versao` devolvido pelo comando.
- Contingência já prevista no protocolo não é emenda: registre só que foi acionada (tipo A).
- Esta é a fonte da seção "Diferenças entre protocolo e revisão" (PRISMA 2020 item 24c).
- Placeholders entre <>. Nada de nomes de pessoas: use papéis (revisor_humano_1...).
-->

Projeto: <título do projeto>
Protocolo congelado: v1.0 em <AAAA-MM-DD> (portão G2) | Registro: <OSF DOI/URL ou "não registrado">

## Resumo

| id | data | versão | seção afetada | tipo | etapa no momento | reexecução exigida |
|---|---|---|---|---|---|---|
| E001 | <AAAA-MM-DD> | v1.0 → v1.1 | <PRISMA-P 8, critério de população> | <A/B/C/D/E> | <antes da busca> | <nenhuma / re-triagem / re-extração / reanálise> |

Tipos: A contingência prevista acionada · B emenda antes da triagem · C emenda depois de ver dados ·
D método planejado não executado · E correção de erro ou incoerência.

## E001

- **Data da decisão:** <AAAA-MM-DD>
- **Versão:** <v1.0> → <v1.1> (v1.x = correção sem efeito sobre decisões; v2.0 = mudança de critério, desfecho ou análise)
- **Arquivo(s) alterado(s):** <00-protocolo/protocolo.md; 02-triagem/prompts/ta_v1.md>
- **Seção / item:** <PRISMA-P item; seção do protocolo>
- **Texto anterior:** "<trecho exato>"
- **Texto novo:** "<trecho exato>"
- **Tipo e motivo:** <A-E>; <circunstância imprevista, inviabilidade, erro, contingência>
- **Etapa da revisão no momento:** <antes da busca | após a busca | após a triagem | após a extração | após a análise>
- **Resultados já conhecidos quando se decidiu:** <nada | contagens do funil | efeitos de n estudos> (a decisão não pode ter sido motivada pelo efeito sobre os resultados)
- **Impacto:** <registros/estudos afetados; se exige re-triagem, re-extração ou reanálise>
- **Ação:** <o que foi refeito; se o resultado será apresentado com e sem a mudança>
- **Aprovado por:** <papel humano>
- **Registro atualizado:** <id do update no OSF ou "não se aplica">
- **Evento no log:** `emenda_protocolo`; versão do artefato <n> (campo `versao` da saída de `$RS emenda`)
