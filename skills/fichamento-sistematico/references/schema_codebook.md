# Schema do codebook

O codebook de um projeto é um CSV com uma linha por variável extraída. 4 colunas são
obrigatórias; 2 são opcionais e só precisam existir se o projeto realmente usar o que
elas habilitam.

| Coluna | Obrigatória | Default se vazia/ausente | Descrição |
|---|---|---|---|
| `dimensao` | sim | — | Agrupamento temático da variável — vira o título de seção (`## <dimensao>`) na ficha. |
| `variavel` | sim | — | Nome em snake_case, sem espaços/acentos — é a chave de parsing usada por todos os scripts. |
| `descricao` | sim | — | Rótulo curto e legível da variável. |
| `prompt` | sim | — | Instrução de extração dada ao agente-fichador para esta variável especificamente. |
| `tipo` | não | `textual` | `categorica` \| `numerica_int` \| `numerica_real` \| `textual` — usada só por `concordancia.py`, para escolher a regra de comparação na validação. |
| `aplicavel_se` | não | vazio = sempre aplicável | `"<variavel_classificadora>=<valor1>[,<valor2>...]"` — ver "Seções condicionais" abaixo. |

## Caso simples (a maioria dos projetos novos)

Nenhuma linha preenche `aplicavel_se`: todas as variáveis sempre se aplicam a todo texto,
sempre **uma ficha por texto**, nunca `NA_secao`, e o relatório de concordância nunca tem
uma seção de "concordância de desenho". É o caminho recomendado ao rascunhar um codebook do
zero — só vale introduzir seções condicionais se o corpus tiver heterogeneidade real de
desenho/tipo de estudo que justifique variáveis diferentes por subgrupo.

```csv
dimensao,variavel,descricao,prompt,tipo,aplicavel_se
Identificacao,titulo,Título,"Extraia o título completo do trabalho.",textual,
Identificacao,ano,Ano de publicação,"Extraia o ano de publicação.",numerica_int,
Metodo,familia_metodo,Família de método,"Classifique em: <categorias do projeto>...",categorica,
Metodo,corpus_fonte,Corpus/fonte de dados,"Descreva a fonte dos dados analisados.",textual,
Resultados,principal_achado,Principal achado,"Resuma o achado central em 1-2 frases.",textual,
```

As colunas `tipo`/`aplicavel_se` podem até ser omitidas inteiramente do CSV (nem precisam
existir como cabeçalho) — os scripts tratam a ausência da coluna exatamente como uma coluna
vazia.

## Seções condicionais (projetos com múltiplos desenhos/tipos de estudo)

Quando o corpus mistura tipos de estudo que exigem variáveis diferentes (ex. estudo
qualitativo vs. quantitativo causal), declare uma variável **classificadora** (ela mesma uma
linha comum do codebook, sem `aplicavel_se`) e use `aplicavel_se` nas variáveis que só fazem
sentido para um valor específico dela:

```csv
dimensao,variavel,descricao,prompt,tipo,aplicavel_se
Metodologia,tipo_estudo,Tipo de desenho do estudo,"Classifique em: qualitativo | quantitativo.",categorica,
Secao qualitativa,mecanismo_processo,Mecanismo/processo identificado,"...",textual,tipo_estudo=qualitativo
Secao quantitativa,estimador,Estimador usado,"...",categorica,tipo_estudo=quantitativo
Secao quantitativa,coeficiente,Coeficiente estimado,"...",numerica_real,tipo_estudo=quantitativo
```

A variável classificadora (`tipo_estudo` acima) é detectada **automaticamente** pelos scripts
— é qualquer variável que aparece à esquerda de algum `=` em `aplicavel_se` no codebook. Não
existe uma segunda coluna "isto é classificador"; um único mecanismo cobre os dois papéis.

Com classificador declarado:
- Um texto cujo desenho se encaixa em só um valor gera **uma ficha**; um texto que combina
  explicitamente dois valores gera **uma ficha por valor** (`ficha_id = <citekey>#<valor>`).
- As variáveis de seções não aplicadas ao(s) valor(es) do texto ficam `NA_secao`.
- `consolida.py` transforma a variável classificadora numa coluna de cabeçalho própria (não um
  par `<var>/<var>__evidencia`) no `fichamentos_master.csv`.
- `concordancia.py` calcula e reporta uma seção extra de "concordância de desenho" (os dois
  codificadores atribuíram os mesmos valores ao mesmo texto?), além da concordância variável a
  variável normal.
- `amostrar_validacao.py --classificador <nome>` estratifica a amostra de validação por
  valor/combinação de valores.

## Recomendações práticas de `tipo`

- Marque como `categorica` toda variável de vocabulário fechado (Sim/Não, uma classificação
  entre poucas opções, a própria variável classificadora) — permite calcular Cohen's κ e
  PABAK na validação (sinalização quando nem κ nem PABAK chegam a 0,7).
- Marque como `numerica_int`/`numerica_real` contagens, anos, coeficientes, erros-padrão — a
  comparação usa tolerância (arredondamento para inteiras, 1% relativo para reais) em vez de
  igualdade exata de string.
- Deixe como `textual` (ou omita `tipo`) qualquer variável de resposta livre/descritiva — a
  validação usa similaridade de Jaccard, que dá crédito parcial a reformulações do mesmo
  conteúdo.
- Uma categórica que aceita **combinações** (ex. "matching + variável instrumental") ainda deve
  ser marcada `categorica`; se o projeto tiver sinônimos conhecidos entre rótulos (ex. "DiD" e
  "diferenças em diferenças" devem contar como iguais), forneça um arquivo `--sinonimos` para
  `concordancia.py` — ver o cabeçalho desse script.
