# Codebooks

Todos os CSV seguem o esquema do `fichamento-sistematico`: `dimensao,variavel,descricao,prompt,tipo,aplicavel_se`. Não há linha de comentário (os scripts da irmã leem a primeira linha como cabeçalho), por isso a atribuição fica aqui.

- `tipo`: `categorica`, `numerica_int`, `numerica_real` ou `textual` (usado por `concordancia.py`).
- `aplicavel_se`: `<classificador>=<valor1>[,<valor2>]`. A variável à esquerda do `=` é o classificador; seções que não se aplicam ao valor da ficha recebem `NA_secao`.
- Texto entre chaves nos prompts (`{lista fechada de famílias...}`) é placeholder: copie o codebook para `00-protocolo/codebook_v0_<nome>.csv` e substitua todos antes do G2 (`grep -c "{" <arquivo>` = 0).
- `999` = aplicável e ausente no texto; `NA_secao` = não se aplica ao classificador.
- Valores com prefixo `proposta_` são rascunhos de julgamento para decisão humana.

As perguntas das ferramentas são **paráfrases curtas em português** para orientar a extração com trecho e página. Não substituem os documentos oficiais, que devem ser lidos por quem julga e citados no protocolo e no relatório.

| Arquivo | Uso | Classificador | Fonte (paráfrase) |
|---|---|---|---|
| `oqf_decomposicao.csv` | Decomposição OQF: bloco comum + a1/a2/b1/b2, corrigido (direção pelo estimador e `direcao_desejada`, significância separada, estimando, 999 × `NA_secao`, variáveis da caixa de ferramentas) | `tipo_estudo` | Proposta "O que funciona?" (Schaefer, Borges e Freitas, 2025) e seu codebook de decomposição a1/a2/b1/b2, com as correções da especificação metodológica da skill; Cochrane Handbook v6.5, cap. 5 e 6 |
| `escopo_pcc.csv` | Charting de revisão de escopo (PCC) | — | JBI Manual for Evidence Synthesis, cap. 10 (Peters et al.); PRISMA-ScR itens 10-11 |
| `qualitativa.csv` | Extração para síntese temática, best-fit e insumos CERQual | — | Thomas e Harden (2008); Carroll et al. (2013); GRADE-CERQual (Lewin et al., 2018) |
| `rob2.csv` | RoB 2, efeito da atribuição; domínio 1b para cluster | `unidade_randomizacao` | Sterne JAC et al. RoB 2: a revised tool for assessing risk of bias in randomised trials. BMJ 2019;366:l4898; guia de 22/08/2019 (Higgins, Savović, Page, Sterne; riskofbias.info, CC BY-NC-ND 4.0); variante cluster (Cochrane Handbook v6.5, cap. 23) |
| `robins_i.csv` | ROBINS-I V2 (seis domínios, triagem B, variantes A e B do domínio 1) + perguntas para quase-experimentos, com os códigos de resposta oficiais: `Y`, `PY`, `PN`, `N`, `NI`; `WN`/`SN` (não fraco/forte) e `SY`/`WY` (sim forte/fraco) nas perguntas em que o documento oficial os usa; `NA` pelo fluxo | `variante_d1` | ROBINS-I V2, versão de 20/11/2025 (rascunho sujeito a mudança; riskofbias.info); Waddington H et al. Quasi-experimental study designs series, paper 6: risk of bias assessment. J Clin Epidemiol 2017;89:43-52 |
| `epoc.csv` | Critérios EPOC para estudos com grupo controle (9) e ITS (7) | `desenho_epoc` | Cochrane EPOC. Suggested risk of bias criteria for EPOC reviews. EPOC Resources for review authors, 2017 |
| `casp_qualitativo.csv` | CASP para pesquisa qualitativa (10 perguntas) + resumo | — | Critical Appraisal Skills Programme (2024). CASP Qualitative Studies Checklist (CC BY-NC-SA 4.0) |
| `jbi_transversal.csv` | JBI para estudos de prevalência (9 itens) e ferramenta revisada para transversais analíticos (8 perguntas) | `tipo_jbi` | Munn Z et al. Int J Evid Based Healthc 2015;13(3):147-153 (checklist JBI de prevalência); Barker TH et al. JBI Evid Synth 2026;24(3):401-408 (ferramenta revisada) |
| `mmat.csv` | MMAT 2018: triagem S1-S2 e cinco categorias | `categoria_mmat` | Hong QN et al. Mixed Methods Appraisal Tool (MMAT), version 2018, Registration of Copyright #1148552, Canadian Intellectual Property Office |
| `desenho_maryland.csv` | Maryland SMS (método, implementação) e classe de desenho, para elegibilidade e descrição | — | Madaleno M, Waights S (2016). Guide to scoring evidence using the Maryland Scientific Methods Scale (atualização de junho de 2016). What Works Centre for Local Economic Growth; Waddington et al. (2017) |
| `elegibilidade_modelo.csv` | Elegibilidade em texto completo | — | ver references/04-textos-elegibilidade.md |

Instruções de uso: references/05-qualidade.md (ferramentas de RoB e apreciação, códigos de resposta por ferramenta e `rs.py qualidade consolidar`), references/06-decomposicao.md (decomposição, escopo e qualitativa). Codebook v0 de efetividade: bloco comum + b2 de `oqf_decomposicao.csv` (references/01-pergunta-protocolo.md, seção 10).
