"""OpenAlex: CSV da interface web e JSON/JSONL da API (works).

USO
    rs.py importar --arquivo openalex.csv --busca-id B04
    rs.py importar --arquivo 01-busca/brutos/B05_openalex.jsonl --busca-id B05

    # uso programático (ex.: `rs.py buscar openalex` depois de gravar o JSONL bruto)
    from rslib.importar import openalex
    brutos = [openalex.bruto_de_work(w) for w in works]

Decisões:
- O resumo da API vem como índice invertido ({palavra: [posições]}); é
  reconstruído ordenando as posições. Se o objeto já trouxer `abstract`
  (CSV da web ou JSON achatado), ele é usado como está.
- `id_fonte` = W-id curto (W4412006287), igual entre CSV e API, para o R2 do dedup.
- CSV da web: listas separadas por "|" (autores, países, instituições). Também
  aceita a tabela achatada com `authorships.N.author.display_name`.
- Palavras-chave: só `keywords` quando existem. `primary_topic`/`concepts` são
  rótulos atribuídos por classificador do OpenAlex, não termos dos autores, e
  gerariam acertos espúrios nos filtros por dicionário.
- Tipo "dissertation" do OpenAlex cobre teses de doutorado e dissertações; vai
  para `tese` (sentido do inglês), com o original em `tipo_publicacao_orig`.
- Registros com `is_retracted` verdadeiro geram aviso para a etapa de retratações e
  a flag `retratado` em dados/registros_flags.csv (importar/flags.py), que o dedup
  propaga para registros_unicos.flags. O campo não é mais descartado.
"""

import json
import re

from .detectar import Colunas, Leitura, ler_json_objetos, ler_tabela
from .generico import dividir, paginas_de, unicos


def reconstruir_resumo(indice):
    """Índice invertido do OpenAlex -> texto. Aceita dict ou string JSON; vazio -> ''."""
    if not indice:
        return ""
    if isinstance(indice, str):
        try:
            indice = json.loads(indice)
        except json.JSONDecodeError:
            return ""
    if not isinstance(indice, dict):
        return ""
    posicoes = {}
    for palavra, lista in indice.items():
        for pos in lista or []:
            try:
                posicoes[int(pos)] = palavra
            except (TypeError, ValueError):
                continue
    return " ".join(posicoes[p] for p in sorted(posicoes))


def id_curto(valor):
    m = re.search(r"(W\d+)\s*$", str(valor or ""))
    return m.group(1) if m else ""


def _verdadeiro(valor):
    return str(valor).strip().lower() in {"true", "1", "yes", "sim"}


def bruto_de_work(w):
    """Objeto work da API (ou JSON achatado com as mesmas chaves) -> dict intermediário."""
    autorias = w.get("authorships") or []
    autores, paises, instituicoes = [], [], []
    for a in autorias:
        a = a or {}
        nome = ((a.get("author") or {}).get("display_name")) or a.get("raw_author_name")
        if nome:
            autores.append(nome)
        paises.extend(a.get("countries") or [])
        for inst in a.get("institutions") or []:
            inst = inst or {}
            if inst.get("display_name"):
                instituicoes.append(inst["display_name"])
            if inst.get("country_code") and not a.get("countries"):
                paises.append(inst["country_code"])
    if not autores:  # JSON achatado (authorships.0.author.display_name, ...)
        numeradas = sorted((int(m.group(1)), k) for k in w
                           if (m := re.fullmatch(r"authorships\.(\d+)\.author\.display_name", str(k))))
        autores = [str(w[k]).strip() for _, k in numeradas if w.get(k)]
    local = w.get("primary_location") or {}
    fonte_local = local.get("source") or {}
    biblio = w.get("biblio") or {}
    palavras = []
    for k in w.get("keywords") or []:
        if isinstance(k, dict):
            palavras.append(k.get("display_name") or k.get("keyword") or "")
        elif isinstance(k, str):
            palavras.append(k)
    resumo = w.get("abstract") or reconstruir_resumo(w.get("abstract_inverted_index"))
    doi = w.get("doi") or (w.get("ids") or {}).get("doi")
    return {
        "fonte": "openalex",
        "id_fonte": id_curto(w.get("id") or (w.get("ids") or {}).get("openalex")),
        "doi": doi,
        "titulo": w.get("display_name") or w.get("title"),
        "autores": autores,
        "ano": w.get("publication_year") or w.get("publication_date"),
        "tipo_publicacao_orig": w.get("type") or w.get("type_crossref"),
        "idioma": w.get("language"),
        "veiculo": (fonte_local.get("display_name") or w.get("primary_location.source.display_name")
                    or (w.get("host_venue") or {}).get("display_name")),
        "volume": biblio.get("volume"),
        "numero": biblio.get("issue"),
        "paginas": paginas_de(biblio.get("first_page"), biblio.get("last_page")),
        "resumo": resumo,
        "palavras_chave": [p for p in palavras if p],
        "pais_afiliacao": unicos([str(p) for p in paises if p]),
        "instituicao": unicos(instituicoes),
        "url": local.get("landing_page_url") or doi or w.get("id"),
        "citado_por": w.get("cited_by_count"),
        "_retratado": bool(w.get("is_retracted")),
    }


def bruto_de_linha_csv(linha, colunas):
    def c(*nomes):
        return colunas.valor(linha, *nomes)

    autores = dividir(c("authorships.author.display_name"), ["|"])
    if not autores:
        numeradas = sorted(
            (int(m.group(1)), col) for col in colunas.cabecalho
            if (m := re.fullmatch(r"authorships\.(\d+)\.author\.display_name", col))
        )
        autores = [str(linha.get(col, "")).strip() for _, col in numeradas if str(linha.get(col, "")).strip()]
    resumo = c("abstract") or reconstruir_resumo(c("abstract_inverted_index"))
    return {
        "fonte": "openalex",
        "id_fonte": id_curto(c("id")),
        "doi": c("doi"),
        "titulo": c("display_name", "title"),
        "autores": autores,
        "ano": c("publication_year", "publication_date"),
        "tipo_publicacao_orig": c("type", "type_crossref"),
        "idioma": c("language"),
        "veiculo": c("primary_location.source.display_name", "host_venue.display_name"),
        "volume": c("biblio.volume"),
        "numero": c("biblio.issue"),
        "paginas": paginas_de(c("biblio.first_page"), c("biblio.last_page")),
        "resumo": resumo,
        "palavras_chave": dividir(c("keywords.display_name"), ["|"]),
        "pais_afiliacao": unicos(dividir(c("authorships.countries"), ["|", ","])),
        "instituicao": unicos(dividir(c("authorships.institutions.display_name"), ["|"])),
        "url": c("primary_location.landing_page_url") or c("doi") or c("id"),
        "citado_por": c("cited_by_count"),
        "_retratado": _verdadeiro(c("is_retracted")),
    }


def ler(caminho, formato, fonte_forcada=None):
    avisos = []
    if formato == "openalex_json":
        registros = [bruto_de_work(w) for w in ler_json_objetos(caminho, avisos)]
    else:
        cabecalho, linhas = ler_tabela(caminho, avisos=avisos)
        colunas = Colunas(cabecalho)
        registros = [bruto_de_linha_csv(l, colunas) for l in linhas]
    # `_retratado` fica no dict intermediário: cli.converter o transforma na flag `retratado`
    # (dados/registros_flags.csv), que o dedup leva a registros_unicos.flags.
    retratados = sum(1 for r in registros if r.get("_retratado"))
    if retratados:
        avisos.append(f"{retratados} registro(s) marcados como retratados pelo OpenAlex (is_retracted); "
                      "confira na etapa de retratações")
    if fonte_forcada:
        for r in registros:
            r["fonte"] = fonte_forcada
    return Leitura(registros, avisos)
