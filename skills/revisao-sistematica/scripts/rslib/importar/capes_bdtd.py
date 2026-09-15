"""Teses e dissertações brasileiras: CAPES (dados abertos e capesR) e BDTD (CSV e API VuFind).

USO
    rs.py importar --arquivo catalogo_teses_2023.csv --busca-id B07      # dados abertos CAPES (; e latin-1)
    rs.py importar --arquivo bdtd.xlsx --busca-id B07                    # tabela do capesR
    rs.py importar --arquivo bdtd_export.csv --busca-id B08              # exportação da BDTD
    rs.py importar --arquivo bdtd_api.json --busca-id B08                # resposta da API VuFind

Decisões:
- O "bdtd.xlsx" dos scripts de exemplo do REFIS é saída do pacote R capesR (colunas
  ano_base, ies, autoria...): a detecção olha colunas, não o nome, e rotula CAPES.
- Tipo: "Mestrado"/"Mestrado Profissional"/"DISSERTAÇÃO" -> dissertacao;
  "Doutorado"/"TESE" -> tese (via normalizar). BDTD API: masterThesis/doctoralThesis.
- Nomes em maiúsculas ("MANOEL DOS SANTOS E SILVA") são convertidos para
  "Manoel dos Santos e Silva" antes de inverter para "Silva, Manoel dos Santos e",
  para o dedup e a chave de citação não dependerem de caixa.
- Programa de pós-graduação vai para `veiculo` e a IES para `instituicao`
  (mesmo papel que periódico e afiliação têm nos artigos).
- CAPES cobre só programas brasileiros: `pais_afiliacao` = "Brazil" (grafia das
  bases internacionais, para os filtros por país casarem entre fontes).
- `id_fonte`: CAPES:<ID_ADD_PRODUCAO_INTELECTUAL> nos dados abertos; BDTD:<id> na
  API. O capesR e o CSV da BDTD não trazem identificador estável: vazio.
- Ano: DT_TITULACAO (defesa) quando existe; senão AN_BASE.
"""

from .detectar import Colunas, Leitura, ler_json_objetos, ler_tabela
from .generico import dividir, nome_proprio

_GRAUS_BDTD = {"masterthesis": "dissertacao", "doctoralthesis": "tese", "bachelorthesis": "outro",
               "article": "artigo", "book": "livro", "bookpart": "capitulo", "report": "relatorio"}
_IDIOMA_3 = {"por": "pt", "eng": "en", "spa": "es", "fre": "fr", "fra": "fr", "ger": "de", "deu": "de", "ita": "it"}


def bruto_dados_abertos(linha, colunas):
    def c(*nomes):
        return colunas.valor(linha, *nomes)

    id_capes = c("ID_ADD_PRODUCAO_INTELECTUAL", "ID_PRODUCAO_INTELECTUAL")
    return {
        "fonte": "capes",
        "id_fonte": f"CAPES:{id_capes}" if id_capes else "",
        "titulo": c("NM_PRODUCAO"),
        "autores": [nome_proprio(c("NM_DISCENTE", "NM_AUTOR"))],
        "ano": c("DT_TITULACAO") or c("AN_BASE"),
        "tipo_publicacao_orig": c("NM_GRAU_ACADEMICO", "NM_SUBTIPO_PRODUCAO", "NM_GRAU_TITULACAO"),
        "idioma": c("NM_IDIOMA", "DS_IDIOMA"),
        "veiculo": nome_proprio(c("NM_PROGRAMA")),
        "resumo": c("DS_RESUMO") or c("DS_ABSTRACT"),
        "palavras_chave": dividir(c("DS_PALAVRA_CHAVE"), [";"]),
        "pais_afiliacao": "Brazil",
        "instituicao": nome_proprio(c("NM_ENTIDADE_ENSINO", "NM_IES")),
        "url": c("DS_URL_TEXTO_COMPLETO"),
    }


def bruto_capesr(linha, colunas):
    def c(*nomes):
        return colunas.valor(linha, *nomes)

    return {
        "fonte": "capes",
        "id_fonte": "",
        "titulo": c("titulo"),
        "autores": [nome_proprio(c("autoria"))],
        "ano": c("ano_base"),
        "tipo_publicacao_orig": c("tipo"),
        "idioma": c("idioma"),
        "veiculo": nome_proprio(c("nome_programa")),
        "resumo": c("resumo"),
        "palavras_chave": dividir(c("palavras_chave"), [";"]),
        "pais_afiliacao": "Brazil",
        "instituicao": nome_proprio(c("ies")),
        "url": c("url", "link"),
    }


def bruto_bdtd_csv(linha, colunas):
    def c(*nomes):
        return colunas.valor(linha, *nomes)

    return {
        "fonte": "bdtd",
        "id_fonte": "",
        "titulo": c("Título", "Titulo", "Title"),
        "titulo_alt": [c("Título em inglês", "Título alternativo")],
        "autores": dividir(c("Autor(a)", "Autor", "Autores"), [";"]),
        "ano": c("Ano de defesa", "Data de defesa", "Ano"),
        "tipo_publicacao_orig": c("Tipo de documento", "Tipo", "Grau"),
        "idioma": c("Idioma"),
        "veiculo": c("Programa de Pós-Graduação da instituição de defesa", "Programa de Pós-Graduação", "Programa"),
        "resumo": c("Resumo em Português", "Resumo português", "Resumo") or c("Resumo em inglês", "Abstract"),
        "palavras_chave": [c("Assuntos em português", "Assuntos"), c("Assuntos em inglês")],
        "pais_afiliacao": c("País da instituição de defesa", "País"),
        "instituicao": c("Instituição de defesa", "Instituição"),
        "url": c("Link de acesso", "URL", "Link"),
    }


def bruto_bdtd_api(registro):
    autores = registro.get("authors") or {}
    primarios = autores.get("primary") or {}
    nomes = list(primarios) if isinstance(primarios, (dict, list)) else [primarios]
    formatos = registro.get("formats") or []
    formato = formatos[0] if formatos else ""
    idiomas = registro.get("languages") or []
    idioma = idiomas[0] if idiomas else ""
    urls = registro.get("urls") or []
    url = urls[0].get("url", "") if urls and isinstance(urls[0], dict) else (urls[0] if urls else "")
    assuntos = []
    for s in registro.get("subjects") or []:
        assuntos.extend(s if isinstance(s, list) else [s])
    resumo = registro.get("summary") or registro.get("abstract") or ""
    if isinstance(resumo, list):
        resumo = resumo[0] if resumo else ""
    datas = registro.get("publicationDates") or []
    bruto = {
        "fonte": "bdtd",
        "id_fonte": f"BDTD:{registro['id']}" if registro.get("id") else "",
        "titulo": registro.get("title"),
        "autores": [nome_proprio(n) for n in nomes if n],
        "ano": datas[0] if datas else "",
        "tipo_publicacao_orig": formato,
        "idioma": _IDIOMA_3.get(str(idioma).lower(), idioma),
        "resumo": resumo,
        "palavras_chave": [str(a) for a in assuntos if a],
        "pais_afiliacao": "Brazil",
        "instituicao": (registro.get("institutions") or [""])[0] if isinstance(registro.get("institutions"), list) else "",
        "url": url,
    }
    grau = _GRAUS_BDTD.get(str(formato).replace(" ", "").lower())
    if grau:
        bruto["tipo_hint"] = grau
    return bruto


def ler_capes(caminho, formato, fonte_forcada=None):
    avisos = []
    cabecalho, linhas = ler_tabela(caminho, avisos=avisos)
    colunas = Colunas(cabecalho)
    montar = bruto_capesr if formato == "capesr" else bruto_dados_abertos
    registros = [montar(l, colunas) for l in linhas]
    if fonte_forcada:
        for r in registros:
            r["fonte"] = fonte_forcada
    return Leitura(registros, avisos)


def ler_bdtd(caminho, formato, fonte_forcada=None):
    avisos = []
    if formato == "bdtd_json":
        registros = [bruto_bdtd_api(r) for r in ler_json_objetos(caminho, avisos)]
    else:
        cabecalho, linhas = ler_tabela(caminho, avisos=avisos)
        colunas = Colunas(cabecalho)
        registros = [bruto_bdtd_csv(l, colunas) for l in linhas]
    if fonte_forcada:
        for r in registros:
            r["fonte"] = fonte_forcada
    return Leitura(registros, avisos)
