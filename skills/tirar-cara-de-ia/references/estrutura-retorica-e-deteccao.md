# Estrutura, retórica e detecção (camada independente de idioma)

Este arquivo cobre a camada que mais denuncia a máquina e que independe de
idioma: **como o texto de IA é moldado e argumentado**, e **como a ciência da
detecção raciocina** sobre ele. As listas de palavras estão nos catálogos por
idioma; aqui está o esqueleto.

Dois princípios atravessam tudo:

1. **O vício quase nunca é o recurso — é o uso reflexo e uniforme do recurso.**
   Travessão, regra de três, frase-tópico e hedge são ferramentas legítimas.
   Humanos as usam *seletivamente, para efeito local*; a máquina as usa
   *mecanicamente, em todo lugar*. Por isso o "localizar-e-substituir" fracassa:
   todo conserto abaixo restaura *juízo e variação*, não bane uma forma.
2. **Por que os padrões existem.** A máquina (a) escolhe a continuação mais
   provável, gravitando para a formulação mais banal e "segura"; (b) gera token a
   token sem plano de parágrafo ou de documento; (c) não tem modelo do leitor
   específico, então explica o óbvio e generaliza; (d) foi treinada em corpora
   "na média", produzindo "um grande estilo médio sem originalidade"; (e) foi
   ajustada por preferência humana (RLHF) para ser prestativa, equilibrada e
   inofensiva. Quase todo vício estrutural sai de uma dessas cinco causas.

---

## 1. Padrões estruturais (documento e parágrafo)

### 1.1 O parágrafo-molde (frase-tópico → evidência → mini-resumo)
Todo parágrafo com o mesmo esqueleto interno, terminando numa pequena
recapitulação de si mesmo. A versão macro é a **progressão em 4 tempos**:
enquadramento → expansão paralela → ressalva ("no entanto…") → resolução limpa,
repetida em temas sem relação.
*Conserto:* quebre o molde de propósito — deixe parágrafos terminarem na
evidência, sem resumo; deixe um fazer uma afirmação e outro complicá-la; varie
onde fica a frase-tópico (ou omita-a).

### 1.2 Resumos fractais (um resumo em cada nível)
O texto anuncia o que vai dizer, diz, e recapitula — e repete isso dentro de cada
seção e às vezes de cada parágrafo. O andaime *parece* organização, mas não
acrescenta informação.
*Conserto:* no máximo um resumo, no nível mais alto, e só se o texto for longo o
bastante. Apague "Nesta seção veremos…", "Recapitulando…", "De modo geral…".

### 1.3 Comprimento e ritmo uniformes
Parágrafos e frases todos do mesmo tamanho; a "textura" visual da página é par.
É a face visível da **baixa burstiness** (§3).
*Conserto:* ponha um parágrafo de uma linha ao lado de um denso; siga uma frase
de 40 palavras com uma de três. Edite para *contraste*, não para suavidade média.

### 1.4 Excesso de seções e de formatação
Títulos demais para o conteúdo; negrito reflexo em "**termos-chave**"; bullets
onde cabia prosa; emoji em cabeçalho. A formatação substitui o raciocínio: marca
importância tipograficamente porque não a conquistou retoricamente.
*Conserto:* transforme listas em prosa quando os itens forem uma *cadeia de
raciocínio* (listas servem para itens realmente paralelos). Reserve negrito para
as duas ou três coisas que de fato importam.

### 1.5 "Lista disfarçada de prosa"
Prosa que é secretamente uma lista numerada, costurada com "O primeiro… O
segundo… Por fim…". Os "parágrafos" não se apoiam uns nos outros.
*Conserto:* decida honestamente — se é lista, formate como lista; se é argumento,
reescreva para que cada parágrafo *dependa* do anterior.

### 1.6 Um ponto diluído em muitas palavras
Uma única ideia repetida de dez formas, cada uma numa metáfora nova. Sem modelo
do leitor, a máquina não percebe quando o ponto já foi feito. Volume disfarçado
de desenvolvimento.
*Conserto:* diga o ponto uma vez, com força total, e então *faça algo novo com
ele* — aplique, complique, ache a exceção. Se dá para apagar um parágrafo sem
perder informação, apague.

### 1.7 Adjacência × acúmulo
As frases ficam *lado a lado* sem se relacionar; a segunda re-anuncia a primeira
com outras palavras em vez de desenvolvê-la. Texto humano **acumula** (cada frase
adiciona evidência, passo ou virada); texto de IA **justapõe**.
*Conserto:* para cada frase depois da primeira, pergunte "isto adiciona evidência,
um passo ou uma virada — ou só repete?". Corte as repetições.

### 1.8 Fechamento prematuro / falta de pressão para a frente
Parágrafos "terminam antes do pensamento terminar"; o texto *parece* avançar por
acúmulo, mas não progride. A máquina para num limiar de comprimento, não na
conclusão intelectual.
*Conserto:* faça a última frase de cada parágrafo *dever* algo à próxima.
Pergunte: "o que mudou entre a introdução e a conclusão?" Se nada mudou, a
estrutura é decorativa.

### 1.9 Equilíbrio incessante
Todo subtópico recebe peso e entusiasmo iguais. Cobertura uniforme é o padrão
seguro; autoria genuína é *desigual* porque o interesse genuíno é desigual.
*Conserto:* deixe a seção que você realmente quer correr longa, e a obrigatória,
curta. Assimetria de atenção é digital humana.

---

## 2. Padrões retóricos (além da frase isolada)

Mecanismo de fundo: verdades universais e resoluções arrumadinhas têm a *menor
perda* estatística — são "os tokens mais seguros"; a prosa reproduz "a *forma* da
sabedoria sem o atrito dela". A máquina domina a *mecânica* da eloquência
(paralelismo, antítese, tricolon), mas não tem o *juízo* de saber quando **não**
usá-la.

- **Suspense fabricado ("aqui está o pulo do gato").** "Mas aqui está o
  detalhe…", "E o resultado? …" — promete revelação, entrega banalidade.
  *Conserto:* apague o rufar de tambores e diga o ponto.
- **Inflação de importância.** Assunto rotineiro elevado a marco histórico; tudo
  é "crucial", "transformador". *Conserto:* dimensione a afirmação. Pergunte
  "comparado a quê?" — riscos reais são comparativos e específicos.
- **Vulnerabilidade performática.** Autoconsciência polida e sem risco ("admito
  que eu também errava nisso"). *Conserto:* corte, ou troque por um detalhe real,
  específico e um pouco desabonador (um erro nomeado, um número).
- **"A verdade é simples" / falsa profundidade.** Afirma o óbvio como insight
  ("mudança é a única constante"). *Conserto:* troque o truísmo pela versão
  *não óbvia e contestável* da afirmação. Se ninguém pode discordar, não diz nada.
- **Analogia paternalista ("pense nisto como…").** Andaime explicativo reflexo,
  mesmo para leitor especialista. *Conserto:* calibre ao leitor; mantenha a
  analogia só quando ela faz trabalho explicativo *novo*.
- **Fórmula "apesar dos desafios…".** Levanta o problema e o descarta com
  otimismo. *Conserto:* deixe o problema em aberto se ele estiver; se reverter,
  justifique com razão específica.
- **Rótulos de conceito inventados.** Cola um substantivo abstrato num termo de
  domínio ("o paradoxo da supervisão") e o usa como se fosse terminologia
  estabelecida. *Conserto:* cite o termo real (se existir) ou descreva o fenômeno
  em prosa simples, sem a autoridade fingida.
- **Paralelismo negativo ("não é X — é Y").** O tell mais citado; a máquina pega
  a versão mais explícita e pesada. *Conserto:* no máximo um por texto, para um
  giro real; em geral, afirme o Y direto e apague o "não X".
- **Tricolon / regra de três (e seu empilhamento).** Trios compulsórios ("Rápido.
  Simples. Eficaz."). *Conserto:* quebre a contagem — use dois, ou quatro, ou um.
- **Falsos intervalos ("de X a Y").** Extremos sem espectro real entre eles.
  *Conserto:* nomeie os casos reais ou largue o "de… a…".
- **Fechamento aforístico / virada inspiracional.** Termina numa frase de
  pôster ("no fim, não é o que a IA faz, é o que fazemos com ela"). *Conserto:*
  feche no ponto concreto mais forte; se a última linha caberia num cartão
  motivacional, reescreva.
- **Abertura "imagine um mundo onde…" / pergunta retórica.** *Conserto:* abra num
  fato, cena ou afirmação específica. Troque "O que faz X funcionar? A resposta é
  Y" por "X funciona porque Y".

### 2.1 Metatexto: falar *sobre* o argumento em vez de fazê-lo

Família de vícios com um traço comum: a frase não afirma nada sobre o mundo, ela
comenta o estatuto lógico do que vem a seguir, e muitas vezes já dá nota a si
mesma. É o que sobra quando o modelo sabe a forma de um argumento mas não tem o
argumento. Em texto acadêmico é o vício mais irritante e o mais invisível para
quem escreveu, porque parece organização.

- **Anúncio de estatuto argumentativo.** "Cabem aqui duas objeções", "Duas
  leituras alternativas merecem ser nomeadas", "Uma última observação sobre X",
  "Vale registrar um limite dessa leitura", "Duas checagens fecham a seção".
  *Conserto:* apague a frase e comece pela objeção, pela leitura ou pelo limite.
  Se o parágrafo seguinte não sobrevive sem o anúncio, ele não tinha conteúdo.
- **Autoavaliação embutida (a "nota de rodapé de confiança").** A cauda que
  qualifica a força do próprio argumento antes de apresentá-lo: "…e ambas têm
  resposta empírica parcial", "…e essa parte tem resposta mais limpa", "…que o
  desenho não elimina", "…com uma ressalva sobre a inferência", "…e essa é a
  primeira leitura que os resultados sustentam". *Conserto:* corte a cauda. Se a
  ressalva é real, ela é uma frase própria, com o conteúdo dela; se é só um
  amortecedor, some sem perda.
- **Ponteiro interno reflexo.** "…e é ele que a seção 4 enfrenta", "pelas razões
  que a tabela 2 explicita adiante", "que a literatura invocada adiante tornaria
  o primeiro da lista", "a seção 9 volta a isso". Um mapa por texto é útil; um
  por parágrafo é andaime. *Conserto:* mantenha no máximo o do fim da introdução.
- **Rótulo de tipo de movimento.** "O primeiro obstáculo é conceitual", "o
  contraste é substantivo", "o achado se sustenta em três das quatro variações".
  Nem sempre é vício: vira vício quando o rótulo substitui a informação.
  *Conserto:* troque o rótulo pelo fato ("Três das quatro variações testadas
  reproduzem o resultado").

Teste rápido: sublinhe toda frase cujo sujeito seja o próprio texto ou o próprio
argumento (a objeção, a leitura, o achado, a seção, o desenho, a resposta). Se
mais de uma ou duas por página sobreviverem, o texto está falando de si.

### 2.2 A frase de efeito (aforismo de fecho de parágrafo)

Sentença curta, simétrica e conclusiva, encaixada no fim ou no início de um
parágrafo para soar perspicaz. Costuma ter quiasmo, antítese ou uma inversão
temporal: "Parte do crescimento é tecnológica antes de ser normativa", "Onde o
Estado mede rotineiramente, o deputado tem o que citar", "O nível é subestimado
nas duas pontas; a variação, não", "Entre o silêncio e o dado aparece uma quarta
forma". Passa despercebida como vício porque é *bem escrita*; o problema é que
ela reformula em tom de sabedoria algo que o parágrafo já disse, e o acúmulo dá
ao texto um tom de coluna de jornal.

*Conserto:* diga a mesma coisa em ordem direta e sem simetria, ou apague se for
repetição. Uma por texto, no ponto mais forte, é voz; cinco é tique.

### 2.3 Narrativa de processo no lugar do método

Contar a saga (quantas rodadas, o que se tentou antes, o que se descobriu no
caminho) quando o leitor precisa da versão final que se aplicou. Aparece muito em
metodologia escrita com auxílio de IA, porque o histórico está fresco no
contexto. *Conserto:* descreva o instrumento como ele é hoje. O histórico só
entra quando ele **é** o resultado, e nesse caso vira seção própria com uma tese.

### 2.4 Número solto na prosa

Parágrafo que enfileira seis, oito, dez estatísticas sem que nenhuma delas
organize uma frase. É a forma numérica do "um ponto diluído em muitas palavras"
(§1.6): o leitor não consegue segurar a série de cabeça e nada fica. *Conserto:*
mova os números para tabela e deixe na prosa só os dois ou três que carregam o
argumento, cada um com a leitura ao lado.

### 2.5 O outro extremo: a afirmação truncada

Nem todo defeito é excesso. O contrário aparece quando o texto nomeia sem
definir ("os cinco detectores", "o efeito fixo de tipo"), afirma sem apoio ("o
gênero mudou pouco em duas décadas") ou reporta número sem régua (coeficiente em
log-chances, sem conversão). O leitor não consegue auditar nem dimensionar nada.
*Conserto:* na primeira ocorrência, definir; na afirmação empírica, mostrar o
dado ou declarar que é suposição; no número, dar a escala. Cuidado: expandir é
justamente quando os vícios de §2.1 voltam, porque a tentação é abrir cada
acréscimo com uma moldura. Explicação nova entra como afirmação direta.

---

## 3. Marcadores estatísticos (burstiness e perplexidade) — e por que não mirar neles

### 3.1 Perplexidade
Quão *surpreso* um modelo fica com a próxima palavra — ou seja, quão previsível é
o texto. "Pedi uma taça de vinho ___" → "tinto" é **baixa** perplexidade; "jujuba"
é **alta**. A máquina escolhe continuações prováveis, então sua saída parece
pouco surpreendente. Faixas relatadas: texto de IA ~5–15; texto humano ~30–150+.
*Heurística sem ferramenta:* leia uma frase e tente prever o fim antes de chegar
nele. Se você acerta quase sempre, a perplexidade está baixa — injete uma
palavra inesperada mas exata, um substantivo específico, um verbo mais afiado.

### 3.2 Burstiness (variação)
Variação *entre* frases — em comprimento e em previsibilidade. Humanos alternam
frases curtas e longas; a IA tende ao uniforme.
*Heurística sem ferramenta:* observe a margem direita — os comprimentos variam ou
marcham parelhos? Ponha uma frase de três palavras ao lado de uma longa; varie a
*abertura* das frases (nem toda começando pelo sujeito).

### 3.3 Cuidado crucial: essas métricas são detectores fracos
**Não reescreva mirando essas métricas.** Elas falham: textos humanos famosos (a
Declaração de Independência) pontuam como "IA pura" porque o modelo já os viu; a
escala é relativa ao modelo (o esperado para GPT não vale para Claude); as
probabilidades de token de GPT/Gemini são fechadas; escrita de não nativos é
naturalmente de baixa perplexidade e sofre **falsos positivos >60%**; e o sinal
colapsa abaixo de ~250 palavras ou após ~15–20% de edição humana. Use burstiness
e perplexidade como *autodiagnóstico* de prosa que soa chapada — nunca como alvo
a enganar nem como prova de autoria.

### 3.4 O que a estilometria de fato mede
Estudos recentes distinguem IA de humano com alta acurácia em amostras curtas
usando: distribuição de palavras funcionais, frequência de pontuação (pontos,
vírgulas), razões de comprimento de frase, frequências de classe gramatical e —
revelador — **densidade de nomes próprios e datas** (humanos têm muito mais). A
IA mostra "padronização gramatical" e superusa qualificadores ("significativo",
"notável"). Tradução prática: **especificidade concreta (nomes, números, datas) é
o sinal humano mais forte e o mais difícil de falsificar.**

### 3.5 Confiabilidade dos detectores (chão de realidade)
Avaliações revisadas por pares de Turnitin e Originality acham acurácia geral
~0,61 / 0,69, recall quase nulo em textos híbridos (humano+IA), forte viés por
gênero (Turnitin caiu de 0,86 em humanas para ~0,51 em ciências) e desvantagem
para quem escreve em segunda língua. Veredito: **nenhum é confiável como prova
principal.** Detectores são suplementares; o juízo humano é essencial. Ou seja:
não escreva "para passar no detector" — escreva para carregar ponto de vista e
informação concreta que uma máquina não teria.

---

## 4. Marcadores de coesão e de voz

- **Conectivos explícitos demais.** "No entanto, ademais, portanto, dito isso" —
  relações lógicas declaradas mesmo quando óbvias. A coesão explícita substitui o
  argumento real. *Conserto:* apague conectivos cuja relação já está clara;
  prefira subordinação que carrega sentido ("porque", "embora") a advérbios
  decorativos; deixe alguns saltos implícitos.
- **Excesso de hedge × ausência de hedge, e o par "hedge-e-tranquiliza".** A IA
  acadêmica tende a hedge em excesso ("pode", "poderia") e empilha o movimento
  "ressalva-depois-garante" ("embora os resultados variem, os dados mostram
  consistentemente…"). *Conserto:* faça uma ressalva e sustente-a, ou comprometa-
  se. Corte cadeias redundantes de qualificadores. (Mas veja §6: hedge calibrado
  é convenção *legítima* — o vício é o volume e o par reflexo.)
- **Ausência de posição em primeira pessoa.** Pouco ou nenhum "eu/nós"; poucas
  perguntas genuínas. A máquina não tem "eu" nem interlocutor específico, então
  fica num registro desencarnado e "objetivo". *Conserto:* onde o registro
  permite, assuma uma posição ("eu acho", "na minha experiência", "eu estava
  errado sobre isto") e faça ao leitor uma pergunta aberta de verdade.
- **Falta de especificidade concreta.** Abstração onde caberiam nomes/números/
  datas. "Uma política de compras que fazia sentido para a indústria…" — soa
  específico, não nomeia nada. *Conserto:* troque cada sintagma genérico que
  puder por uma instância real — a empresa, o ano, a cifra, o contraexemplo.
- **Atribuição vaga.** "Estudos mostram", "especialistas concordam", "a pesquisa
  sugere" sem citação, e citações confiantes sem fonte. *Conserto:* nomeie fonte,
  ano e, de preferência, o número — ou apague a afirmação. (É também uma checagem
  de integridade factual, não só de estilo.)
- **"Bagunça ausente" / registro uniforme.** Sem falso começo, digressão,
  redundância ou deslize de registro; tom uniformemente formal ou uniformemente
  animado. *Conserto:* permita uma digressão controlada, um aparte, um momento de
  informalidade dentro da prosa formal. Texto humano revela personalidade na
  *inconsistência*.

---

## 5. Revisão humana de verdade × "des-IA" mecânico

O risco central ao limpar vícios é trocar uma uniformidade (chapado-de-IA) por
outra (supercorrigido e sem voz), ou arrancar estilo legítimo para satisfazer
teorias populares de detecção.

**A armadilha da supercorreção.** O travessão é a fábula de advertência: é um
sinal legítimo, amado por muitos humanos e *anterior* aos LLMs — a IA o usa demais
*porque humanos usam*. Localizar-e-substituir todo travessão (ou todo "no
entanto", ou toda tríade) remove voz e não conserta nada estrutural. O vício
sempre foi *frequência e reflexo*, não o sinal.

**Superfície × substância.**
- *Superfície (piora ou é neutra):* trocar "delve" por "explorar", apagar todo
  travessão, rodar um "humanizador", parafrasear para enganar detector. Preserva
  o esqueleto oco e muitas vezes *introduz* erro — e nem engana o detector (§3.5).
- *Substância (torna o texto humano e melhor):* adicione o que a máquina não
  tem — (1) **especificidade** (dado, data, nome, caso, contraexemplo); (2)
  **posição** (um argumento contestável; primeira pessoa onde couber); (3)
  **reestruturação por acúmulo** (parágrafos que dependem uns dos outros; corte
  de repetição; estrutura assimétrica); (4) **variação** (comprimentos de frase e
  parágrafo); (5) **checagem factual** (afirmações de IA erram com confiança);
  (6) **bagunça controlada** (digressão, aparte, ênfase assimétrica).

**Teste prático.** Leia em voz alta e pergunte: "eu diria mesmo isto — com esta
ênfase, esta especificidade, esta opinião?" Se a frase poderia ter sido escrita
sobre *qualquer* tema por *qualquer* pessoa, é resíduo de IA — reescreva para ser
insubstituível.

---

## 6. Nuance de registro: acadêmico × corporativo

O mesmo traço de superfície pode ser vício de IA num registro e convenção
obrigatória em outro. Arrancar convenção legítima é uma supercorreção comum. A
pergunta que discrimina é sempre: *frequência, especificidade e se o recurso faz
trabalho real.*

### 6.1 Acadêmico
**Convenções legítimas que parecem IA mas NÃO devem ser removidas:**
- **Hedge.** Modalidade cautelosa ("pode", "sugere", "é consistente com") é valor
  central da ciência — marca honestidade epistêmica, não timidez de máquina, *se
  calibrada à evidência*.
- **Sinalização / IMRaD.** "Este artigo argumenta…", "A Seção 3 apresenta…", a
  estrutura Introdução–Métodos–Resultados–Discussão e frases-tópico explícitas
  são *exigências* da disciplina, não resumos fractais.
- **Conectivos formais, nominalização, voz passiva pontual, impessoalidade.**

**O que é de fato vício de IA no acadêmico:**
- Hedge *em excesso* e o par reflexo "ressalva-e-garante" (§4), em vez de hedge
  calibrado.
- **Atribuição vaga** — "estudos mostram" *em vez* de citação real (§4); um campo
  definido pela citação expõe isso na hora.
- **Especificidade genérica** — sem estudo, dataset, figura ou autor nomeado.
- Ausência de posição/voz onde o campo permite; gramática e molde de parágrafo
  padronizados demais.
- *Nota de gênero:* detectores são *piores* em texto científico, porque o estilo
  científico legítimo se sobrepõe ao registro chapado da IA — os falsos positivos
  são maiores justamente aqui. Confie em integridade de citação e especificidade,
  não em "vibe".

### 6.2 Corporativo / técnico
**Convenções legítimas que parecem IA mas NÃO devem ser removidas:**
- **Bullets, sumário executivo, cabeçalhos, estrutura escaneável** — são
  *funcionais* em documento feito para ser lido em diagonal.
- **Paralelismo em listas, verbos de ação, vocabulário de processo**
  ("otimizado", "padronizado") e **hedges comuns** ("em geral", "costuma").
- **Tom formal e consistente** — esperado em muitos gêneros corporativos.

**O que é de fato vício de IA no corporativo:**
- **Inflação de entusiasmo/importância** — "energia de keynote" em tudo; toda
  iniciativa "transformadora".
- **Verbos de negócio vazios e abstração** — "fomentar colaboração", "impulsionar
  inovação", "alavancar sinergias" sem referente concreto.
- **"Não é só X, é Y" e suspense fabricado** como tempero de thought leadership.
- **Registro uniforme + aversão a risco** — nenhuma afirmação polêmica, nenhum
  fracasso nomeado, nenhum número real; especificidade genérica no lugar do
  cliente, da métrica ou do resultado reais.
- **Excesso de seções/formatação** — negrito e bullets fazendo o trabalho que o
  raciocínio deveria fazer.

### 6.3 A regra que atravessa os dois
Uma convenção é legítima quando (a) serve à necessidade real do leitor naquele
gênero e (b) é *específica* e *portadora de sentido*. Vira vício quando é (a)
reflexa e uniforme, (b) genérica e (c) decorativa — importância afirmada por
tipografia ou retórica em vez de conquistada com informação. Edite rumo a
*especificidade e variação*; preserve as convenções de gênero que carregam
sentido.
