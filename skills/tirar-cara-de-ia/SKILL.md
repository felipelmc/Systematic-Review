---
name: tirar-cara-de-ia
description: >-
  Revisa um texto para remover os "vícios de linguagem de IA" — o fraseamento,
  o vocabulário, as construções sintáticas, a pontuação e os padrões de
  estrutura e retórica que fazem um texto soar como se tivesse sido gerado por
  ChatGPT, Claude, Gemini e afins. Use SEMPRE que o usuário pedir para "tirar a
  cara de IA", "deixar mais humano/natural", "revisar meu texto", "não parecer
  escrito por IA", "humanizar", "soar como eu escrevi", ou quando ele entregar
  um documento (e-mail, relatório, artigo, ensaio, proposta, post, tese) para
  revisão final de estilo — mesmo que não diga explicitamente "IA". Cobre
  português, inglês e espanhol, com foco em textos acadêmicos e
  profissionais/corporativos. Não use para revisão de gramática/ortografia
  pura, nem para gerar texto novo do zero.
---

# Tirar a cara de IA

## O que esta skill faz e por que ela existe

Modelos de linguagem foram treinados para produzir prosa "segura, média e
agradável a todos". O efeito colateral é um sotaque reconhecível: certas
palavras, transições, construções de frase e hábitos de estrutura aparecem com
frequência muito acima da escrita humana. Leitores atentos — bancas, editores,
revisores, clientes, colegas — captam esse sotaque na hora e ele corrói a
credibilidade do texto, dando impressão de preguiça ou de que o autor não
pensou de fato sobre o assunto.

Para revisar bem, ajuda entender **por que** a máquina escreve assim. Quase
todos os vícios saem de cinco causas:

1. **Ela escolhe a continuação mais provável** — logo, gravita para a formulação
   mais banal e "segura", o clichê que minimiza risco.
2. **Ela gera palavra por palavra, sem plano** — não há arquitetura pensada de
   parágrafo ou de documento; a estrutura vira um molde repetido.
3. **Ela não tem um modelo do leitor específico** — não sabe o que precisa ser
   explicado ou provado, então explica o óbvio e generaliza.
4. **Ela foi treinada em corpora "na média"** — o resultado é um "estilo médio
   sem dono", sem idiossincrasia.
5. **O ajuste por preferência humana (RLHF) premia** tom prestativo, equilibrado
   e inofensivo — daí o entusiasmo constante, o hedge, a positividade.

Entender isso muda a revisão: o objetivo **não é passar um localizador-e-
substituidor numa lista de palavras proibidas**. Isso produz um texto igualmente
artificial, só que mancando: sinônimos esquisitos, frases contorcidas para fugir
de um travessão. O objetivo é devolver ao texto o que a máquina estruturalmente
não tem — **especificidade, posicionamento, variação de ritmo e uma estrutura em
que uma ideia puxa a próxima** — preservando o sentido e a voz do autor.

### A regra de ouro

**O vício quase nunca é o recurso isolado — é o uso reflexo, uniforme e denso do
recurso.** Um travessão, um "além disso", uma tríade, um hedge: tudo isso existe
na boa escrita humana. O que denuncia a IA é a *frequência*, a *simetria* e o
*acúmulo* de vários desses padrões ao mesmo tempo, somados à ausência de
informação concreta. Por isso, ao revisar:

- **Preserve o sentido e a intenção.** Mude a forma, não o conteúdo. Se remover
  um vício exigir alterar um dado, uma afirmação ou uma conclusão, **pare e
  pergunte** — nunca invente para preencher o buraco (ver "Integridade factual").
- **Preserve a voz.** "Humanizar" não é "amaciar". Se o autor é ferino, direto
  ou informal, mantenha isso. O alvo é o sotaque de máquina, não a
  personalidade do autor.
- **Não cace palavras cegamente.** A ocorrência única de quase todos os termos
  dos catálogos é legítima. Só aja quando houver padrão.

## Fluxo de trabalho

Siga esta ordem. A maioria dos erros de revisão vem de "consertar" frase por
frase sem enxergar o texto inteiro.

1. **Leia o texto todo primeiro.** Identifique (a) a voz que o autor busca
   (acadêmica formal? direta-corporativa?), (b) o argumento central que você vai
   proteger e (c) o idioma — para consultar o catálogo certo.

2. **Diagnostique por camadas, não frase a frase.** Percorra o texto marcando os
   vícios em duas camadas: a **estrutural/retórica** (parágrafos-molde, resumos
   repetidos, "não é X, é Y", tríades, perguntas retóricas, falso equilíbrio) e a
   **lexical/superficial** (palavras de vitrine, conectores de enchimento,
   pontuação). Um texto com cara de IA quase sempre tem vários vícios se
   reforçando.

3. **Ataque a camada estrutural primeiro.** Um parágrafo-molde ou um "não é X, é
   Y" entrega muito mais que a palavra "ademais". Se você só troca palavras, o
   texto continua com esqueleto de máquina. Consulte
   `references/estrutura-retorica-e-deteccao.md` para essa camada.

4. **Corte antes de substituir.** Boa parte dos vícios é enfeite: adjetivo
   vazio, advérbio de intensidade, transição que não conecta nada, frase que
   repete a anterior com outras palavras. Na dúvida, delete. Texto humano bom é
   mais enxuto, não mais floreado. Em relatório/proposta, **encurtar já remove
   metade da cara de IA** (esse tipo de texto costuma perder 30–40% sem perder
   conteúdo).

5. **Cheque o extremo oposto: a afirmação truncada.** Nem todo defeito é
   excesso. Termo nomeado e nunca definido, afirmação empírica sem apoio, número
   reportado sem escala de leitura: o leitor não consegue auditar nem dimensionar.
   Ao preencher essas lacunas, cuidado para não reintroduzir metatexto — a
   tentação é abrir cada acréscimo com "vale explicitar que". Explicação nova
   entra como afirmação direta.

6. **Especifique.** Onde a IA generaliza ("diversos fatores", "de forma
   significativa", "especialistas apontam"), a escrita humana crível dá o
   número, o nome, a data, o exemplo concreto. Especificidade é o sinal humano
   mais forte e o mais difícil de a máquina falsificar. Se o texto original não
   traz essa especificidade, **sinalize a lacuna ao autor** — não invente.

7. **Restaure o ritmo (burstiness).** O tique mais profundo da IA é a *baixa
   variação*: frases de comprimento parecido, todo parágrafo com a mesma
   arquitetura. Alterne frases curtas e longas de propósito; deixe uma frase
   curta bater sozinha; varie a abertura das frases (nem toda frase começando
   pelo sujeito). Um teste sem ferramenta: se você consegue prever o fim de quase
   toda frase antes de chegar nele, o texto está previsível demais.

8. **Reintroduza posicionamento e "textura humana".** Onde o gênero permitir,
   recupere um ponto de vista que alguém poderia contestar, um "eu"/"nós", uma
   ressalva honesta, até uma pequena digressão. Texto humano revela
   personalidade justamente na assimetria e na imperfeição controlada.

9. **Releia em voz (mental).** A pergunta final: "uma pessoa dizendo isto a um
   colega inteligente escolheria estas palavras, com esta ênfase, esta opinião e
   esta especificidade?" Se a frase poderia ter sido escrita sobre *qualquer*
   tema por *qualquer* pessoa, é resíduo de IA — reescreva para ser
   insubstituível.

## Revisão de superfície × revisão de verdade

Não confunda as duas. A revisão de superfície (trocar "delve" por "explorar",
apagar todo travessão, rodar um "humanizador") preserva o esqueleto oco e muitas
vezes introduz erros — e nem engana detector. A revisão de verdade adiciona o
que a máquina não tem:

- **Especificidade** — dados, datas, nomes, casos, contraexemplos reais.
- **Posicionamento** — um argumento contestável; primeira pessoa onde o registro
  permite.
- **Reestruturação por acúmulo** — fazer cada parágrafo *depender* do anterior
  (afirmação → objeção → resposta; causa → consequência), cortando repetição.
- **Variação** — misturar comprimentos de frase e de parágrafo.
- **Checagem factual** — verificar toda estatística, citação e afirmação.
- **Textura controlada** — uma digressão, um aparte, uma ênfase assimétrica.

## Guardrails: não troque um artificialismo por outro

- **O travessão não é o vilão.** Ele é um sinal fraco e ambíguo: a IA o usa
  demais *porque humanos o usam*. Banir travessão em massa remove voz e não
  conserta nada estrutural. Reduza a frequência mecânica; não extermine o recurso.
- **Não deixe o texto pior para fugir de um vício.** Um sinônimo raro e torto
  ("paramountly significant", "de singular complexidade") chama mais atenção que
  a palavra comum que você evitava.
- **Respeite as convenções do registro.** Formalidade, voz passiva pontual,
  hedge calibrado e sinalização estrutural são *legítimos* em texto acadêmico;
  bullets, sumário executivo e verbos de processo são *legítimos* em texto
  corporativo. O alvo é o *clichê de IA*, não a formalidade. Uma convenção é
  legítima quando serve ao leitor **e** é específica e funcional; vira vício
  quando é reflexa, genérica e decorativa. Ver a seção de registro em
  `references/estrutura-retorica-e-deteccao.md`.
- **Não invente conteúdo** para tapar uma generalização — sinalize a lacuna.

## Integridade factual (inegociável)

Remover vícios é mudar a forma. Sempre que a forma estiver colada a uma possível
falta de conteúdo — "estudos mostram" sem fonte, um número sem origem, uma
citação sem referência —, **não preencha por conta própria**. Sinalize
explicitamente ao autor ("aqui você diz 'a literatura aponta' sem citar qual —
recomendo nomear a fonte"). Inventar referência ou dado é o pior desfecho
possível, sobretudo em texto acadêmico (risco de fabricação e de acusação de
má conduta).

## Como entregar o resultado

Salvo pedido diferente do usuário, entregue:

- **O texto revisado**, pronto para usar (num arquivo, se o original era um
  arquivo; senão, no corpo da resposta). Se o usuário quiser acompanhar as
  mudanças, ofereça uma versão com marcas ou um antes/depois dos trechos-chave.
- **Um resumo curto das mudanças por categoria** — não um diff linha a linha,
  mas o suficiente para o autor aprender a não repetir os vícios.
- **As lacunas de conteúdo sinalizadas** (integridade factual acima), separadas
  do resto para o autor decidir.

Se possível, calibre a "força" da revisão com o usuário: uma passada leve (só os
vícios gritantes, mexendo pouco) ou uma reescrita mais funda (reestruturando
parágrafos). Na dúvida, faça a leve e ofereça a funda.

## Os vícios de maior impacto (aja primeiro nestes)

Estes padrões independem de idioma e são os que mais denunciam a máquina. As
listas exaustivas por idioma estão nos arquivos de referência; a camada
estrutural detalhada está em `references/estrutura-retorica-e-deteccao.md`.

1. **Paralelismo negativo — "não é X, é Y".** A construção-assinatura nº 1.
   "Não se trata apenas de velocidade — trata-se de eficiência." Apague o
   andaime e diga o Y direto. No máximo uma por texto, para um giro real.
2. **Regra de três (tríades) automática.** "Claro, conciso e convincente."
   Quebre: use um, dois ou quatro itens; corte adjetivos que só fecham a tríade.
3. **Pergunta retórica + resposta curta.** "O resultado? Impressionante."
   Transforme em afirmação.
4. **Metatexto: falar sobre o argumento em vez de fazê-lo.** "Cabem aqui duas
   objeções, e ambas têm resposta empírica parcial", "Duas leituras alternativas
   merecem ser nomeadas", "Vale registrar um limite dessa leitura", "e essa parte
   tem resposta mais limpa". A frase não afirma nada sobre o mundo: comenta o
   estatuto lógico do que vem e ainda dá nota a si mesma. Apague a moldura e
   comece pela objeção, pela ressalva, pelo limite. Detalhes em
   `references/estrutura-retorica-e-deteccao.md` §2.1.
5. **Frase de efeito.** Aforismo curto e simétrico no fim ou no início do
   parágrafo, para soar perspicaz: "Parte do crescimento é tecnológica antes de
   ser normativa", "O nível é subestimado nas duas pontas; a variação, não".
   Passa despercebida porque é bem escrita, mas costuma repetir o que o parágrafo
   já disse. Diga em ordem direta, sem simetria, ou apague. §2.2.
6. **Parágrafo-molde e resumos repetidos.** Toda seção com a mesma arquitetura
   (frase-tópico → exemplo → mini-conclusão) e recapitulações em cada nível.
   Varie a estrutura; deixe no máximo um resumo, no nível mais alto.
7. **Transições de enchimento.** "Além disso", "Vale ressaltar que", "É
   importante notar que", "Moreover", "It's worth noting that". Apague e cheque
   se a ligação continua clara — quase sempre continua.
8. **Adjetivo/advérbio vazio e palavra-hype.** "robusto", "inovador", "de forma
   significativa"; "seamless", "delve", "leverage". Substitua por substância
   concreta ou apague.
9. **Falso equilíbrio / "apesar dos desafios".** Levanta um problema só para
   descartá-lo com otimismo. Deixe o problema em aberto se ele estiver em aberto.
10. **Vago no lugar do específico.** "diversos", "especialistas apontam", "cada
   vez mais", "in today's fast-paced world". Insira o dado concreto ou reformule.
11. **Fechamento sinalizado e "virada inspiracional".** "Em conclusão", "In
   conclusion", frase final de cartão motivacional. Feche no ponto concreto mais
   forte; se a última linha caberia num pôster, reescreva.
12. **Pontuação como tique e formatação em excesso.** Travessão como conector
    universal, ponto-e-vírgula forçado, lista para tudo, negrito no início de
    cada item, emoji como marcador. Reduza e varie.
13. **Tom neutro sem dono.** Ausência de posicionamento, positividade constante,
    gramática perfeita demais. Onde o gênero permitir, recupere a voz e o ponto
    de vista do autor.

## Arquivos de referência

Consulte o arquivo do idioma do texto (se misturar idiomas, consulte os dois) e,
sempre, o de estrutura/retórica — porque a camada estrutural é a que mais
entrega e a que independe de idioma.

- `references/portugues.md` — catálogo em português: léxico (adjetivos,
  substantivos, verbos, advérbios, coringas de vagueza), conectores, construções
  sintáticas, frases-molde, pontuação, tom, e notas para texto acadêmico e
  corporativo, com antes/depois.
- `references/ingles.md` — catálogo em inglês: "AI tells" lexicais, frases-
  clichê, construções (negative parallelism, "from X to Y", etc.), pontuação,
  achados empíricos de detecção (estudos de frequência, "delve", etc.).
- `references/espanol.md` — catálogo em espanhol, com os tics reais do idioma
  (não traduções do inglês) e marcação dos que são calcos do inglês.
- `references/estrutura-retorica-e-deteccao.md` — a camada independente de
  idioma: padrões estruturais e retóricos (incluindo §2.1 metatexto, §2.2 frase
  de efeito, §2.3 narrativa de processo, §2.4 número solto e §2.5 afirmação
  truncada), os conceitos de *burstiness* e
  *perplexidade* (com heurísticas sem ferramenta), a (baixa) confiabilidade dos
  detectores, e a nuance de registro acadêmico × corporativo — o que é convenção
  legítima e não deve ser removido.
