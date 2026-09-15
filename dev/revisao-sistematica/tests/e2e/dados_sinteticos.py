"""Corpus sintético do teste ponta a ponta: 21 obras em 3 exportações (WoS, Scopus, OpenAlex).

Cada obra tem a verdade de referência de cada etapa (triagem T/A, elegibilidade, efeitos),
e as funções abaixo escrevem as exportações nos formatos reais das bases, com as
armadilhas que o fluxo precisa tratar:
- duplicatas entre bases com DOI em caixas/prefixos diferentes (W01, W02, W11, W18, W19, W20);
- duplicata sem DOI, só título + ano + sobrenome (W03);
- preprint (W04, DOI 10.31235) e sua versão publicada em duas bases (W05): relatos do mesmo estudo,
  ligados por id_estudo no dedup, nunca fundidos;
- "Part I" × "Part II" do mesmo autor e ano, sem DOI (W06, W07): nunca fundir;
- tese (W08, OpenAlex) e artigo derivado (W09, Scopus): nunca fundir, ligar por id_estudo;
- registro sem resumo (W10), editorial (W13), registro antigo (W14), idioma francês (W15), revisão (W16).
Nomes, periódicos e DOIs são fictícios (prefixo 10.5555).
Também guarda o que humanos escrevem para os portões: codebooks já ajustados (G2), parecer PRESS (G3) e as
avaliações de risco de viés A e B por domínio, com um desacordo para o consenso humano (G7).
"""

import csv
import json
import textwrap

FAMILIA = "Transferência condicionada de renda"
CONSTRUTO = "participacao_escolar"


def obra(k, titulo, autores, ano, bases, ta, resumo, doi="", tipo="article", idioma="en", veiculo="Journal of Development Evidence",
         tc=None, **extra):
    return dict(k=k, titulo=titulo, autores=autores, ano=ano, bases=bases, ta=ta, resumo=resumo, doi=doi, tipo=tipo,
                idioma=idioma, veiculo=veiculo, tc=tc, **extra)


OBRAS = [
    obra("W01", "Conditional cash transfers and school attendance: evidence from a randomized experiment in rural Mexico",
         [("Alves", "Beatriz Costa"), ("Rocha", "Tiago")], 2015, {"wos", "scopus", "openalex"}, "incluir",
         "We evaluate a conditional cash transfer program using a randomized experiment in 120 villages. "
         "Transfers conditional on school attendance increased attendance among children aged 6 to 15.",
         doi="10.5555/rct.2015.001", tc="incluir", desenho="RCT"),
    obra("W02", "Bolsa Familia and school dropout: a difference-in-differences analysis",
         [("Borges", "Carla"), ("Nogueira", "Paulo")], 2017, {"wos", "scopus"}, "incluir",
         "We estimate the effect of the Bolsa Familia conditional cash transfer on school dropout with "
         "difference-in-differences and administrative school census data.",
         doi="10.5555/did.2017.002", tc="incluir", desenho="diferenças em diferenças", veiculo="Revista de Economia Aplicada"),
    obra("W03", "Cash transfers and enrollment in Colombian municipalities",
         [("Castro", "Diego")], 2019, {"wos", "scopus"}, "incluir",
         "Using a municipal panel with fixed effects, we study how a conditional cash transfer program changed "
         "school enrollment in Colombian municipalities.", tc="incluir", desenho="painel com efeitos fixos"),
    obra("W04", "School attendance effects of a conditional cash transfer in Honduras",
         [("Dias", "Elena")], 2020, {"openalex"}, "incluir",
         "A cluster randomized evaluation of a conditional cash transfer shows higher school attendance in Honduras.",
         doi="10.31235/osf.io/abcd1", tipo="preprint", veiculo="SocArXiv", tc="incluir"),
    obra("W05", "School attendance effects of a conditional cash transfer in Honduras",
         [("Dias", "Elena")], 2021, {"scopus", "wos"}, "incluir",
         "A cluster randomized evaluation of a conditional cash transfer shows higher school attendance in Honduras.",
         doi="10.5555/jde.2021.005", tc="incluir"),
    obra("W06", "Conditional transfers and schooling outcomes: Part I",
         [("Esteves", "Fabio")], 2018, {"wos"}, "incluir",
         "Part I develops a conceptual framework on how conditional transfers affect schooling outcomes.",
         tc="excluir_C2"),
    obra("W07", "Conditional transfers and schooling outcomes: Part II",
         [("Esteves", "Fabio")], 2018, {"scopus"}, "excluir_C3",
         "Part II discusses the health outcomes of conditional transfers for adolescents."),
    obra("W08", "Transferências condicionadas de renda e frequência escolar no semiárido",
         [("Souza", "Gabriela")], 2017, {"openalex"}, "incluir",
         "Esta tese avalia o efeito de transferências condicionadas de renda sobre a frequência escolar no semiárido "
         "com regressão descontínua.", tipo="dissertation", idioma="pt", veiculo="Universidade Fictícia do Nordeste",
         tc="incluir"),
    obra("W09", "Transferências condicionadas de renda e frequência escolar no semiárido brasileiro",
         [("Souza", "Gabriela"), ("Lima", "Rui")], 2018, {"scopus"}, "incluir",
         "Avaliamos o efeito de transferências condicionadas de renda sobre a frequência escolar no semiárido "
         "brasileiro com regressão descontínua.", doi="10.5555/rbe.2018.009", idioma="pt",
         veiculo="Revista Brasileira de Economia Fictícia", tc="incluir", desenho="RDD"),
    obra("W10", "Conditional cash transfers and child labor in Nicaragua",
         [("Faria", "Helena")], 2014, {"wos"}, "incerto", "", tc="excluir_C3"),
    obra("W11", "Unconditional cash transfers and learning outcomes in Kenya",
         [("Gomes", "Igor")], 2019, {"scopus", "openalex"}, "divergente",
         "We study unconditional cash transfers and learning outcomes of primary school children in Kenya.",
         doi="10.5555/ken.2019.011"),
    obra("W12", "Health effects of conditional cash transfers on child nutrition",
         [("Hora", "Joana")], 2016, {"openalex"}, "excluir_C3",
         "We estimate the effects of conditional cash transfers on child nutrition and height for age.",
         doi="10.5555/nut.2016.012"),
    obra("W13", "Editorial: the future of social protection research",
         [], 2020, {"wos"}, "excluir_C2",
         "This editorial introduces a special issue and discusses research priorities for social protection.",
         tipo="editorial", grupo="Social Protection Research Network"),
    obra("W14", "School enrollment and family income in Brazil",
         [("Ivo", "Karla")], 1995, {"scopus"}, "excluir_C1",
         "We describe the association between family income and school enrollment in Brazil in the early 1990s."),
    obra("W15", "Transferts monétaires conditionnels et scolarisation au Maroc",
         [("Jardim", "Luc")], 2019, {"openalex"}, "incluir",
         "Nous analysons les transferts monétaires conditionnels et la scolarisation des enfants au Maroc.",
         idioma="fr", veiculo="Revue Fictive du Développement", tc="excluir_C2"),
    obra("W16", "A systematic review of conditional cash transfers and education",
         [("Klein", "Maria")], 2021, {"scopus"}, "excluir_C2",
         "This systematic review summarizes studies of conditional cash transfers and education outcomes.",
         tipo="review"),
    obra("W17", "Microfinance and women's empowerment in Bangladesh",
         [("Lopes", "Nuno")], 2018, {"openalex"}, "excluir_C1",
         "We examine microfinance access and women's empowerment in rural Bangladesh.", doi="10.5555/mfi.2018.017"),
    obra("W18", "Conditional cash transfers and secondary school completion in Peru",
         [("Mendes", "Otavio")], 2020, {"openalex", "wos"}, "incluir",
         "A regression discontinuity design shows that conditional cash transfers raised secondary school completion in Peru.",
         doi="10.5555/per.2020.018", tc="incluir"),
    obra("W19", "Teacher incentives and student achievement in India",
         [("Nunes", "Paula")], 2017, {"scopus", "wos"}, "excluir_C1",
         "We evaluate teacher performance pay and student achievement in Indian public schools.",
         doi="10.5555/ind.2017.019"),
    obra("W20", "Conditional cash transfers, school attendance and gender gaps in Pakistan",
         [("Oliveira", "Quenia")], 2022, {"openalex", "scopus"}, "incluir",
         "We study how conditional cash transfers changed school attendance and gender gaps in Pakistan.",
         doi="10.5555/pak.2022.020", tc="nao_recuperado"),
    obra("W21", "Scholarships for girls and enrollment in Bangladesh",
         [("Pires", "Rafael")], 2013, {"wos"}, "excluir_C1",
         "We evaluate merit scholarships for girls and secondary enrollment in Bangladesh.", doi="10.5555/ban.2013.021"),
]
POR_K = {o["k"]: o for o in OBRAS}

# Bola de neve (OpenAlex falso): obras novas, uma para trás (W22) e uma para frente (W23)
NOVAS_BOLA_DE_NEVE = [
    obra("W22", "Unconditional cash transfers and household consumption in Zambia", [("Quintas", "Sara")], 2016,
         {"openalex"}, "excluir_C1", "We study unconditional cash transfers and household consumption in Zambia.",
         doi="10.5555/zam.2016.022"),
    obra("W23", "Mobile money adoption and remittances in Kenya", [("Ramos", "Tito")], 2021,
         {"openalex"}, "excluir_C1", "We study mobile money adoption and remittances among Kenyan households.",
         doi="10.5555/mob.2021.023"),
]

# Efeitos por estudo (formato de agentes/extrator-efeitos.md): trecho verbatim vai para a página 2 do PDF
EFEITOS = {
    "W01": [dict(desenho="RCT", estimando="ITT", outcome="taxa de frequência escolar", direcao_desejada="aumentar",
                 modelo="Tabela 2, coluna 1", modelo_principal="sim", tipo_estatistica="md_sd",
                 m1="88.0", sd1="10.0", n1="300", m2="85.0", sd2="10.0", n2="300", n_total="600",
                 evidencia="Attendance rate was 88.0 (SD 10.0) in treatment villages and 85.0 (SD 10.0) in control villages",
                 pagina="2")],
    "W02": [dict(desenho="diferenças em diferenças", estimando="ATT", outcome="abandono escolar", direcao_desejada="reduzir",
                 modelo="Tabela 3, coluna 2", modelo_principal="sim", tipo_estatistica="t", t="-4.00", df="798",
                 n1="400", n2="400", p="<0.001", n_total="800",
                 evidencia="The dropout difference-in-differences estimate has t = -4.00 with 798 degrees of freedom",
                 pagina="2"),
            dict(desenho="diferenças em diferenças", estimando="ATT", outcome="abandono escolar", direcao_desejada="reduzir",
                 modelo="Tabela 4, meninas", modelo_principal="nao", subgrupo="meninas", tipo_estatistica="t", t="-3.10",
                 df="398", n1="200", n2="200", n_total="400",
                 evidencia="For girls, t = -3.10 with 398 degrees of freedom", pagina="2")],
    "W03": [dict(desenho="painel com efeitos fixos", estimando="ATE", outcome="matrícula", direcao_desejada="aumentar",
                 modelo="Tabela 2, coluna 3", modelo_principal="sim", tipo_estatistica="beta_sd", beta="0.90", se="0.21",
                 sdy="3.0", n_total="900",
                 evidencia="The enrollment coefficient is 0.90 (SE 0.21) and the control-group standard deviation is 3.0",
                 pagina="2")],
    "W09": [dict(desenho="RDD", estimando="RDD_local", outcome="frequência escolar", direcao_desejada="aumentar",
                 modelo="Tabela 5", modelo_principal="sim", tipo_estatistica="md_sd",
                 m1="86.0", sd1="10.0", n1="400", m2="83.2", sd2="10.0", n2="400", n_total="800",
                 evidencia="Mean attendance was 86.0 (SD 10.0) above the cutoff and 83.2 (SD 10.0) below it", pagina="2")],
}

CRITERIOS_TA = """# Critérios de triagem de títulos e resumos (ta_v1)

Pergunta: transferências condicionadas de renda aumentam a participação escolar de crianças e adolescentes?

Aplique os critérios nesta ordem.

C1 — Intervenção: o estudo avalia um programa de transferência de renda condicionada (à frequência escolar
ou a outra contrapartida). Transferências incondicionais, microcrédito, bolsas por mérito e incentivos a
professores não atendem.

C2 — Tipo de estudo: estudo empírico primário que estima o efeito do programa. Revisões, editoriais e
ensaios teóricos não atendem.

C3 — Desfecho: mede frequência, matrícula, evasão ou conclusão escolar.
"""

CODEBOOK_ELEGIBILIDADE = [
    ["Identificacao", "desenho_resumo", "Desenho em uma frase", "Descreva o desenho.", "textual", ""],
    ["Criterios de elegibilidade", "C1_intervencao", "Transferência condicionada", "Avalia TCR? Sim ou Não.", "categorica", ""],
    ["Criterios de elegibilidade", "C2_desenho", "Estudo empírico primário", "Estima efeito? Sim ou Não.", "categorica", ""],
    ["Criterios de elegibilidade", "C3_outcome", "Desfecho escolar", "Mede participação escolar? Sim ou Não.", "categorica", ""],
]


# ---------------------------------------------------------------------------
# Identificadores por base
# ---------------------------------------------------------------------------
def numero(k):
    return int(k[1:])


def ut(k):
    return f"WOS:{numero(k):015d}"


def eid(k):
    return f"2-s2.0-85{numero(k):09d}"


def wid(k):
    return f"W30000{numero(k):05d}"


def ids_fonte(o):
    return {"wos": ut(o["k"]), "scopus": eid(o["k"]), "openalex": wid(o["k"])}


# ---------------------------------------------------------------------------
# Web of Science (plaintext)
# ---------------------------------------------------------------------------
_DT_WOS = {"article": "Article", "editorial": "Editorial Material", "review": "Review", "preprint": "Article"}
_LA = {"en": "English", "pt": "Portuguese", "fr": "French"}


def _tag(tag, valores):
    linhas = []
    for i, valor in enumerate(valores):
        partes = textwrap.wrap(valor, 70) or [""]
        for j, parte in enumerate(partes):
            prefixo = f"{tag} " if (i == 0 and j == 0) else "   "
            linhas.append(prefixo + parte)
    return linhas


def escrever_wos(caminho, obras):
    linhas = ["FN Clarivate Analytics Web of Science", "VR 1.0"]
    for o in obras:
        linhas.append("PT J")
        if o["autores"]:
            linhas += _tag("AU", [f"{s}, {''.join(p[0] for p in n.split())}" for s, n in o["autores"]])
            linhas += _tag("AF", [f"{s}, {n}" for s, n in o["autores"]])
        else:
            linhas += _tag("CA", [o["grupo"]])
        titulo = o["titulo"]
        linhas += _tag("TI", [titulo])
        linhas += _tag("SO", [o["veiculo"].upper()])
        linhas.append(f"LA {_LA[o['idioma']]}")
        linhas.append(f"DT {_DT_WOS[o['tipo']]}")
        if o["resumo"] and not o.get("wos_sem_resumo"):
            linhas += _tag("AB", [o["resumo"]])
        linhas.append("TC 3")
        linhas.append(f"PY {o['ano']}")
        if o["doi"]:
            linhas.append(f"DI {o['doi'].upper()}")
        linhas.append(f"UT {ut(o['k'])}")
        linhas.append("DA 2026-09-01")
        linhas.append("ER")
        linhas.append("")
    linhas.append("EF")
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Scopus (CSV com BOM)
# ---------------------------------------------------------------------------
COLUNAS_SCOPUS = ["Authors", "Author full names", "Author(s) ID", "Title", "Year", "Source title", "Volume", "Issue",
                  "Art. No.", "Page start", "Page end", "Cited by", "DOI", "Link", "Affiliations", "Abstract",
                  "Author Keywords", "Index Keywords", "Language of Original Document", "Document Type",
                  "Publication Stage", "Source", "EID"]
_DT_SCOPUS = {"article": "Article", "review": "Review", "editorial": "Editorial", "preprint": "Article"}


def escrever_scopus(caminho, obras):
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_SCOPUS)
        w.writeheader()
        for o in obras:
            curtos = "; ".join(f"{s} {''.join(p[0] + '.' for p in n.split())}" for s, n in o["autores"])
            completos = "; ".join(f"{s}, {n} ({57000000000 + numero(o['k']) * 10 + i})"
                                  for i, (s, n) in enumerate(o["autores"]))
            w.writerow({
                "Authors": curtos, "Author full names": completos, "Title": o["titulo"], "Year": o["ano"],
                "Source title": o["veiculo"], "Volume": "12", "Issue": "3", "Page start": "101", "Page end": "130",
                "Cited by": "4", "DOI": o["doi"], "Link": f"https://www.scopus.com/inward/record.uri?eid={eid(o['k'])}",
                "Affiliations": "Universidade Fictícia, Recife, Brazil",
                "Abstract": o["resumo"] or "[No abstract available]", "Author Keywords": "cash transfers; schooling",
                "Language of Original Document": _LA[o["idioma"]], "Document Type": _DT_SCOPUS[o["tipo"]],
                "Publication Stage": "Final", "Source": "Scopus", "EID": eid(o["k"]),
            })


# ---------------------------------------------------------------------------
# OpenAlex (JSONL da API)
# ---------------------------------------------------------------------------
def indice_invertido(texto):
    indice = {}
    for pos, palavra in enumerate(texto.split()):
        indice.setdefault(palavra, []).append(pos)
    return indice or None


def obra_openalex(o, referencias=()):
    return {
        "id": f"https://openalex.org/{wid(o['k'])}",
        "doi": f"https://doi.org/{o['doi'].upper()}" if o["doi"] else None,
        "title": o["titulo"], "display_name": o["titulo"], "publication_year": o["ano"],
        "type": o["tipo"], "language": o["idioma"], "is_retracted": False, "cited_by_count": 7,
        "primary_location": {"landing_page_url": f"https://example.org/{o['k']}", "source": {"display_name": o["veiculo"]}},
        "biblio": {"volume": "5", "issue": "1", "first_page": "1", "last_page": "20"},
        "keywords": [{"display_name": "cash transfers"}],
        "authorships": [{"author": {"display_name": f"{n} {s}"}, "countries": ["BR"],
                         "institutions": [{"display_name": "Universidade Fictícia", "country_code": "BR"}]}
                        for s, n in o["autores"]],
        "abstract_inverted_index": indice_invertido(o["resumo"]),
        "referenced_works": [f"https://openalex.org/{r}" for r in referencias],
    }


def escrever_openalex(caminho, obras):
    with open(caminho, "w", encoding="utf-8") as f:
        for o in obras:
            f.write(json.dumps(obra_openalex(o), ensure_ascii=False) + "\n")


def escrever_exportacoes(pasta):
    """Escreve as três exportações e devolve {base: caminho}."""
    pasta.mkdir(parents=True, exist_ok=True)
    arquivos = {"wos": pasta / "savedrecs.txt", "scopus": pasta / "scopus.csv", "openalex": pasta / "openalex_works.jsonl"}
    escrever_wos(arquivos["wos"], [o for o in OBRAS if "wos" in o["bases"]])
    escrever_scopus(arquivos["scopus"], [o for o in OBRAS if "scopus" in o["bases"]])
    escrever_openalex(arquivos["openalex"], [o for o in OBRAS if "openalex" in o["bases"]])
    return arquivos


# ---------------------------------------------------------------------------
# Protocolo (G2), PRESS (G3) e risco de viés (G7)
# ---------------------------------------------------------------------------
COLUNAS_CODEBOOK = ["dimensao", "variavel", "descricao", "prompt", "tipo", "aplicavel_se"]
# Codebook v0 da família OQF já ajustado pela equipe (sem os {placeholders} do modelo de assets/codebooks/).
CODEBOOK_V0 = [
    ["01_Formal", "titulo", "Título", "Copie o título completo como aparece na primeira página.", "textual", ""],
    ["02_Desenho", "desenho", "Desenho do estudo", "Classifique em: RCT | DiD | RDD | painel | outro.", "categorica", ""],
    ["03_Efeito", "construto_outcome", "Construto do desfecho",
     "Classifique em: participacao_escolar | aprendizagem | outro.", "categorica", ""],
]
PRESS = """# PRESS 2015: estratégia S1 (WoS, Scopus, OpenAlex)

Revisor: revisor_humano_2 (não escreveu a string). Data: 2026-09-02.

| Elemento | Parecer |
|---|---|
| Tradução da pergunta | adequada |
| Operadores booleanos e de proximidade | sem problemas |
| Termos controlados | não se aplica às bases usadas |
| Truncamento e grafia | acrescentar transfer* (feito na v1) |
| Limites e filtros | nenhum na base |
"""
# Risco de viés por resultado: ferramenta e julgamentos por domínio dos avaliadores A e B (formato longo).
# W03 tem um desacordo em D1 (moderado × grave), resolvido por humano no consenso.
ROB = {
    "W01": ("rob2", {"D1": ("baixo", "baixo"), "D2": ("baixo", "baixo"), "D3": ("algumas_preocupacoes", "algumas_preocupacoes"),
                     "D4": ("baixo", "baixo"), "D5": ("baixo", "baixo")}),
    "W02": ("robins_i", {f"D{i}": ("moderado", "moderado") if i == 1 else ("baixo", "baixo") for i in range(1, 7)}),
    "W03": ("robins_i", {f"D{i}": ("moderado", "grave") if i == 1 else ("baixo", "baixo") for i in range(1, 7)}),
    "W09": ("robins_i", {f"D{i}": ("moderado", "moderado") if i in (1, 5) else ("baixo", "baixo") for i in range(1, 7)}),
}
COLUNAS_AVALIACAO_ROB = ["chave", "construto_outcome", "dominio", "julgamento", "trecho", "pagina", "justificativa"]


def escrever_codebooks(pasta):
    """Codebook v0 e codebook de elegibilidade em 00-protocolo/ (o que o G2 exige), sem placeholders."""
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, linhas in (("codebook_v0_oqf.csv", CODEBOOK_V0), ("codebook_elegibilidade.csv", CODEBOOK_ELEGIBILIDADE)):
        with open(pasta / nome, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLUNAS_CODEBOOK)
            w.writerows(linhas)
    return [pasta / "codebook_v0_oqf.csv", pasta / "codebook_elegibilidade.csv"]


def avaliacao_rob(ferramenta, avaliador, chaves):
    """Linhas da avaliação independente `avaliador` (A ou B) da `ferramenta`, com {k da obra: chave}."""
    indice = 0 if avaliador == "A" else 1
    linhas = []
    for k, (ferr, dominios) in ROB.items():
        if ferr != ferramenta:
            continue
        for dominio, julgamentos in dominios.items():
            linhas.append({"chave": chaves[k], "construto_outcome": CONSTRUTO, "dominio": dominio,
                           "julgamento": julgamentos[indice], "trecho": "Estimates are robust to alternative specifications",
                           "pagina": "2", "justificativa": f"avaliador {avaliador}: sinalizadoras do domínio {dominio}"})
    return linhas
