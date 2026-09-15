# Checklist de 12 seções para rascunhar um codebook do zero

Ponto de partida para a conversa de rascunho de codebook (passo 2 do fluxo em `SKILL.md`,
quando o projeto ainda não tem um). Adaptado de um template genérico de fichamento de
texto único em 12 seções — aqui ele vira um **checklist de dimensões candidatas**, não um
formato de saída fixo: cada seção abaixo é uma pergunta a fazer ao
usuário ("isso vira uma ou mais variáveis extraíveis do seu codebook, ou não é relevante
para a sua revisão?"), não uma seção que toda ficha precisa ter.

Use isto para não esquecer categorias óbvias de informação que revisões de literatura
tipicamente extraem — não para forçar as 12 no codebook final. Um projeto pode usar só 4
dessas dimensões e adicionar 6 completamente específicas do seu tema; outro pode não
precisar de metade delas.

1. **Referência completa** — quase sempre vale a pena ter `titulo`, `autoria`, `ano`, e
   talvez `doi`/`nome_publicacao` como variáveis formais básicas (tipo `textual` ou
   `numerica_int` para ano).
2. **Identificação rápida** — área/subárea, tipo de texto (artigo/capítulo/tese/working
   paper), idioma. Boas candidatas a `categorica`.
3. **Pergunta de pesquisa / objetivo central** — geralmente `textual`.
4. **Argumento / tese central** — o *claim* central do texto, não um resumo do abstract;
   `textual`.
5. **Quadro teórico** — conceitos principais, filiação teórica; `textual`, ou `categorica`
   se o projeto tiver uma tipologia teórica fechada de interesse.
6. **Estratégia metodológica** — tipo de abordagem (quanti/quali/mista/teórica), método
   específico, fonte de dados, N amostral. **Esta é a dimensão mais provável de precisar
   de uma variável classificadora com seções condicionais** (ver `schema_codebook.md`), se
   o corpus mistura desenhos muito diferentes que exigem perguntas de extração distintas.
7. **Principais resultados/achados** — geralmente `textual`, às vezes com uma variável
   numérica separada se houver um efeito/coeficiente central comparável entre os textos.
8. **Limitações reconhecidas pelos autores** — `textual`.
9. **Conexão com a pergunta da revisão** — específico da revisão em curso: em que medida
   este texto responde à pergunta motivadora do projeto. Frequentemente vale a pena ter
   uma variável dedicada a isso, mesmo que o resto do codebook seja enxuto.
10. **Citações/trechos-chave** — não vira uma variável própria no codebook; é o próprio
    mecanismo de ancoragem verbatim que toda variável substantiva já usa.
11. **Notas críticas do codificador** — não é uma variável do codebook; corresponde à seção
    fixa "Notas do codificador" que toda ficha já tem, independente do codebook do projeto.
12. **Palavras-chave para indexação** — opcional, `textual`.

## Perguntas a fazer durante o rascunho

- Qual é a pergunta de pesquisa da revisão? (molda o que entra na dimensão 9 acima, e às
  vezes justifica variáveis totalmente novas fora desta lista.)
- O corpus é metodologicamente homogêneo (todos os textos usam abordagens comparáveis) ou
  heterogêneo (mistura, por exemplo, estudos qualitativos e quantitativos, ou métodos muito
  diferentes entre si)? Só no segundo caso vale considerar uma variável classificadora com
  seções condicionais — não introduza essa complexidade sem necessidade real.
- Existe algum resultado numérico central (coeficiente, efeito, métrica de desempenho) que
  faça sentido comparar entre todos os textos? Se sim, vale uma variável `numerica_real`
  dedicada, com sua unidade/definição bem especificada no `prompt`.
- Alguma variável tem um vocabulário fechado natural (Sim/Não, um conjunto pequeno e
  conhecido de categorias)? Marque como `categorica` — habilita Cohen's κ na validação.
