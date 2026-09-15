#!/usr/bin/env python3
"""
baixar_pdfs.py — baixa PDFs acadêmicos a partir de DOI, título ou planilha.

Tenta, em cascata, fontes de acesso aberto legítimas (Unpaywall, Semantic
Scholar, OpenAlex, CORE, padrões por editora, HAL, Wayback Machine, e por
fim minerar a landing page do próprio DOI). Sci-Hub é opt-in: só é usado se
o chamador passar --scihub-dois (batch) ou --tentar-scihub (single) — o
script nunca decide sozinho tentar Sci-Hub.

Uso:
    python3 baixar_pdfs.py batch --planilha papers.xlsx --saida-pdfs ./pdfs
    python3 baixar_pdfs.py single --doi 10.1371/journal.pone.0000308 --saida-pdfs ./pdfs

Ver references/fontes.md (na pasta da skill) para detalhes de cada fonte.

Chaves (nome do PDF): `gerar_chave` vem de scripts/chave.py, arquivo vendorizado
idêntico nas skills de revisão (gerar-bibtex, fichamento-sistematico,
revisao-sistematica), para que a mesma planilha produza o mesmo `<chave>.pdf`, a mesma
ficha e a mesma entrada do .bib. A coluna de chave existente é reaproveitada só se
passar em `chave_valida`; senão há aviso e a chave é regenerada. Os aliases dessa
coluna não incluem `id`/`key` porque exportações do Zotero (`Key`) e do OpenAlex (`id`)
virariam nomes de arquivo como `https___openalex.org_W123.pdf`.
"""
import argparse
import os
import re
import sys
import time
import unicodedata
import urllib.parse
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import requests
import urllib3

# chave.py mora ao lado deste script; o caminho explícito permite importar este módulo
# de fora da pasta (testes, outras skills). Sem bytecode para não sujar a pasta da skill.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chave import chave_valida, gerar_chave  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==== Configuração ====

MIN_PDF_SIZE = 1000
TIMEOUT_API = (10, 20)
TIMEOUT_PDF = (10, 45)
TIMEOUT_SCIHUB = (10, 60)
PAUSA_ENTRE_FONTES = 0.4

EMAIL = os.environ.get("PDF_DOWNLOADER_EMAIL", "")
CORE_API_KEY = os.environ.get("CORE_API_KEY", "")

SESSAO = requests.Session()
SESSAO.headers.update({"User-Agent": "Mozilla/5.0 (academic paper downloader)"})

COLUNAS_RELATORIO = [
    "chave", "titulo", "autores", "ano", "doi",
    "status", "fonte", "url", "versao", "motivo", "arquivo",
]


# ==== Validação de PDF ====

def is_valid_pdf(caminho: Path) -> bool:
    """%PDF no início + %%EOF perto do fim (bytes crus) + tamanho mínimo."""
    if not caminho.exists():
        return False
    tamanho = caminho.stat().st_size
    if tamanho < MIN_PDF_SIZE:
        return False
    with open(caminho, "rb") as f:
        if f.read(4) != b"%PDF":
            return False
        f.seek(max(0, tamanho - 2048))
        fim = f.read()
    return b"%%EOF" in fim


def save_if_pdf(conteudo: bytes, destino: Path) -> bool:
    if not conteudo or len(conteudo) < MIN_PDF_SIZE or conteudo[:4] != b"%PDF":
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(conteudo)
    return is_valid_pdf(destino)  # reconfirma no disco (pega truncamento)


# ==== HTTP ====

def fetch(url, timeout=TIMEOUT_PDF, headers=None):
    """GET tolerante: nunca levanta exceção, um retry relaxando SSL."""
    if not url:
        return None
    try:
        r = SESSAO.get(url, timeout=timeout, allow_redirects=True, headers=headers)
        if r.status_code == 200:
            return r.content
        return None
    except requests.exceptions.SSLError:
        try:
            r = SESSAO.get(url, timeout=timeout, allow_redirects=True, verify=False, headers=headers)
            if r.status_code == 200:
                return r.content
        except Exception:
            return None
        return None
    except Exception:
        return None


def fetch_json(url, headers=None, timeout=TIMEOUT_API):
    try:
        r = SESSAO.get(url, timeout=timeout, headers=headers)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None


# ==== Comparação de título / chaves ====

def normalizar_titulo(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def titulo_parece_igual(a, b, limiar=0.75):
    if not a or not b:
        return False
    return SequenceMatcher(None, normalizar_titulo(a), normalizar_titulo(b)).ratio() >= limiar


def avisar_titulos_duplicados(titulos, limiar=0.9, limite_par_a_par=500):
    """Avisa (não bloqueia) sobre linhas da planilha de entrada com título igual ou
    quase igual ao de outra linha. Não é raro numa planilha vinda de APIs como o
    OpenAlex: o mesmo trabalho pode aparecer duas vezes (indexação duplicada), ou duas
    linhas podem ser um par preprint/versão publicada do mesmo paper com DOIs
    diferentes. `gerar_chave()` só evita colisão de NOME DE ARQUIVO (sufixo a/b/...) —
    não tem nenhuma noção de que duas linhas podem ser o mesmo trabalho, então este
    aviso é a única checagem que existe. Não impede o download dos dois; só avisa,
    porque às vezes o usuário realmente quer ambas as versões."""
    normalizados = [(i, normalizar_titulo(t)) for i, t in enumerate(titulos)
                     if pd.notna(t) and str(t).strip()]

    # Passo 1: título idêntico após normalizar (case/acento/pontuação) — O(n), sempre roda.
    por_titulo = {}
    for i, tn in normalizados:
        por_titulo.setdefault(tn, []).append(i)
    avisadas = set()
    for indices in por_titulo.values():
        if len(indices) > 1:
            linhas = [idx + 1 for idx in indices]
            print(f"  ⚠ linhas {linhas} têm o MESMO título (após normalizar) — confira se "
                  "não é o mesmo paper contado duas vezes antes de tratar os PDFs como "
                  "achados independentes.")
            avisadas.update(indices)

    # Passo 2: título quase-igual (SequenceMatcher) — O(n²), só roda numa planilha de
    # tamanho razoável; esta skill normalmente processa a lista já filtrada de uma
    # revisão (dezenas/centenas de linhas), não o corpus bruto de uma busca.
    restantes = [(i, t) for i, t in normalizados if i not in avisadas]
    if len(restantes) > limite_par_a_par:
        print(f"  (pulei a checagem de título quase-igual: {len(restantes)} linhas > limite "
              f"de {limite_par_a_par} — só a checagem de título idêntico rodou acima)")
        return
    for a in range(len(restantes)):
        i, ti = restantes[a]
        for b in range(a + 1, len(restantes)):
            j, tj = restantes[b]
            if SequenceMatcher(None, ti, tj).ratio() >= limiar:
                print(f"  ⚠ linhas {i + 1} e {j + 1} têm título quase igual — confira se não "
                      "é o mesmo paper (ex. um par preprint/versão publicada) antes de tratar "
                      "os PDFs como achados independentes.")


def limpar_doi(doi):
    if doi is None or (isinstance(doi, float) and pd.isna(doi)):
        return None
    doi = str(doi).strip()
    if not doi or doi.lower() == "nan":
        return None
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    return doi.strip().lower() or None


# `gerar_chave(titulo, autores, ano, usadas)` vem de chave.py (importado no topo), com a
# mesma assinatura da antiga função local, que partia autores em [;,] e pegava o último
# token ("Weihs M." -> "M2025") e gerava sufixo "{" depois de "z".


def chave_de_doi(doi):
    """Fallback para modo single sem título/autor: chave determinística a partir do DOI
    (mesmo DOI -> mesma chave sempre, para que reexecutar reconheça 'já existia')."""
    return re.sub(r"[^A-Za-z0-9]+", "_", doi).strip("_")[-40:]


# ==== Fallback genérico: seguir o DOI e minerar a landing page ====

def resolver_doi(doi):
    try:
        r = SESSAO.get(f"https://doi.org/{doi}", timeout=TIMEOUT_API, allow_redirects=True)
        return r.url
    except Exception:
        return None


def _absolutizar(url, base):
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        p = urllib.parse.urlparse(base)
        return f"{p.scheme}://{p.netloc}{url}"
    if not url.startswith("http"):
        return urllib.parse.urljoin(base, url)
    return url


def extrair_links_pdf(html, base_url):
    padroes = [
        r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
        r'<a[^>]+href=["\']([^"\']+\.pdf[^"\']*)["\']',
        r'<object[^>]+data=["\']([^"\']+\.pdf[^"\']*)["\']',
        r'<iframe[^>]+src=["\']([^"\']+\.pdf[^"\']*)["\']',
        r'<embed[^>]+src=["\']([^"\']+\.pdf[^"\']*)["\']',
    ]
    achados, vistos = [], set()
    for p in padroes:
        for m in re.finditer(p, html, re.IGNORECASE):
            u = _absolutizar(m.group(1), base_url)
            if u not in vistos:
                vistos.add(u)
                achados.append(u)
    return achados


def minerar_pdf_de_pagina(url):
    """Baixa `url`; se já for PDF retorna ela mesma, senão minera até 5 links de PDF na página (1 nível só)."""
    conteudo = fetch(url)
    if not conteudo:
        return None
    if conteudo[:4] == b"%PDF":
        return url
    if len(conteudo) > 5_000_000:
        return None
    try:
        html = conteudo.decode("utf-8", errors="ignore")
    except Exception:
        return None
    for candidata in extrair_links_pdf(html, url)[:5]:
        c = fetch(candidata)
        if c and c[:4] == b"%PDF":
            return candidata
    return None


# ==== Fontes com DOI: agregadores de metadados ====

def try_unpaywall(doi):
    data = fetch_json(f"https://api.unpaywall.org/v2/{doi}?email={EMAIL}")
    if not data:
        return None
    return (data.get("best_oa_location") or {}).get("url_for_pdf")


def try_semantic_scholar(doi):
    data = fetch_json(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf")
    if not data:
        return None
    return (data.get("openAccessPdf") or {}).get("url")


def try_openalex(doi):
    doi_enc = urllib.parse.quote(doi, safe="")
    data = fetch_json(f"https://api.openalex.org/works/doi:{doi_enc}?mailto={EMAIL}")
    if not data:
        return None
    for loc in data.get("locations") or []:
        if loc.get("pdf_url"):
            return loc["pdf_url"]
    return (data.get("open_access") or {}).get("oa_url")


def try_core(doi):
    q = urllib.parse.quote(f'doi:"{doi}"')
    headers = {"Authorization": f"Bearer {CORE_API_KEY}"} if CORE_API_KEY else None
    data = fetch_json(f"https://api.core.ac.uk/v3/search/works?q={q}&limit=3", headers=headers)
    if not data:
        return None
    for item in data.get("results") or []:
        if item.get("downloadUrl"):
            return item["downloadUrl"]
    return None


# ==== Fontes com DOI: padrões por editora ====

PLOS_JOURNALS = {
    "journal.pone": "plosone", "journal.pntd": "plosntds", "journal.pmed": "plosmedicine",
    "journal.pbio": "plosbiology", "journal.pcbi": "ploscompbiol",
    "journal.pgen": "plosgenetics", "journal.ppat": "plospathogens",
}


def try_scielo(doi):
    final = resolver_doi(doi)
    if not final:
        return None
    m = re.search(r"pid=(S[\w-]+)", final) or re.search(r"(S\d{4}-\d{3,}[\w-]*)", final)
    if not m:
        return None
    pid = m.group(1)
    for lng in ("en", "pt", "es"):
        candidata = f"https://www.scielo.br/scielo.php?script=sci_pdf&pid={pid}&lng={lng}&nrm=iso"
        conteudo = fetch(candidata)
        if conteudo and conteudo[:4] == b"%PDF":
            return candidata
    return None


def _try_mdpi(sufixo):
    candidata = f"https://www.mdpi.com/{sufixo}/pdf"
    conteudo = fetch(candidata)
    if conteudo and conteudo[:4] == b"%PDF":
        return candidata
    # Cloudflare costuma bloquear /pdf; o CDN direto às vezes funciona mesmo assim
    partes = sufixo.split("/")
    if len(partes) >= 3:
        journal, vol, art = partes[0], partes[1], partes[2]
        art = art.zfill(4) if art.isdigit() else art
        return (
            f"https://mdpi-res.com/d_attachment/{journal}/{journal}-{vol}-{art}/"
            f"article_deploy/{journal}-{vol}-{art}.pdf"
        )
    return None


def try_zenodo(doi):
    m = re.search(r"zenodo\.(\d+)", doi)
    if not m:
        return None
    data = fetch_json(f"https://zenodo.org/api/records/{m.group(1)}")
    if not data:
        return None
    for f in data.get("files") or []:
        nome = (f.get("key") or f.get("filename") or "").lower()
        if nome.endswith(".pdf"):
            links = f.get("links") or {}
            return links.get("self") or links.get("download")
    return None


def try_publisher_patterns(doi):
    dl = doi.lower()
    if dl.startswith("10.1371/"):
        suf = doi[len("10.1371/"):]
        slug = PLOS_JOURNALS.get(suf.split(".")[0], "plosone")
        return f"https://journals.plos.org/{slug}/article/file?id={doi}&type=printable"
    if dl.startswith("10.3390/"):
        return _try_mdpi(doi[len("10.3390/"):])
    if dl.startswith("10.159"):
        return try_scielo(doi)
    if dl.startswith("10.3389/"):
        return f"https://www.frontiersin.org/articles/{doi}/pdf"
    if dl.startswith("10.1073/"):
        return f"https://www.pnas.org/doi/pdf/{doi}"
    if dl.startswith("10.12952/"):
        return f"https://online.ucpress.edu/elementa/article-pdf/{doi.split('/')[-1]}"
    if "zenodo" in dl:
        return try_zenodo(doi)
    return None


# ==== Fontes com DOI: repositórios e arquivo ====

def try_hal(doi):
    """HAL usa o sistema anti-bot Anubis; User-Agent Wget bypassa."""
    url = f'https://api.hal.science/search?q=doiId_s:"{doi}"&fl=halId_s,title_s,fileMain_s&rows=5'
    try:
        r = requests.get(url, headers={"User-Agent": "Wget/1.21.1"}, verify=False, timeout=TIMEOUT_API)
        if r.status_code != 200:
            return None
        for doc in r.json().get("response", {}).get("docs", []):
            if doc.get("fileMain_s"):
                return doc["fileMain_s"]
    except Exception:
        pass
    return None


def wayback_cdx(url):
    cdx_url = (
        "https://web.archive.org/cdx/search/cdx"
        f"?url={urllib.parse.quote(url, safe='')}"
        "&filter=mimetype:application/pdf&output=json&limit=5"
    )
    try:
        r = requests.get(cdx_url, timeout=TIMEOUT_API)
        if r.status_code != 200:
            return None
        linhas = r.json()
        if len(linhas) < 2:
            return None
        header = linhas[0]
        idx_ts = header.index("timestamp") if "timestamp" in header else 1
        idx_orig = header.index("original") if "original" in header else 2
        timestamp, original = linhas[1][idx_ts], linhas[1][idx_orig]
        return f"https://web.archive.org/web/{timestamp}/{original}"
    except Exception:
        return None


def try_wayback(doi):
    final = resolver_doi(doi)
    return wayback_cdx(final) if final else None


def try_landing_page(doi):
    final = resolver_doi(doi)
    return minerar_pdf_de_pagina(final) if final else None


CASCATA_COM_DOI = [
    ("unpaywall", try_unpaywall),
    ("semantic_scholar", try_semantic_scholar),
    ("openalex", try_openalex),
    ("core", try_core),
    ("editora", try_publisher_patterns),
    ("hal", try_hal),
    ("wayback", try_wayback),
    ("landing_page", try_landing_page),
]


# ==== Fontes sem DOI: busca por título ====
# Cada função retorna (doi_encontrado, url_pdf_direta) — qualquer um dos dois pode ser None.

def try_semantic_scholar_titulo(titulo):
    q = urllib.parse.quote(titulo[:200])
    url = f"https://api.semanticscholar.org/graph/v1/paper/search/match?query={q}&fields=title,openAccessPdf,externalIds"
    data = fetch_json(url)
    if not data or not data.get("data"):
        return None, None
    paper = data["data"][0]
    if not titulo_parece_igual(titulo, paper.get("title", "")):
        return None, None
    doi = (paper.get("externalIds") or {}).get("DOI")
    pdf = (paper.get("openAccessPdf") or {}).get("url")
    return (doi.lower() if doi else None), pdf


def try_openalex_titulo(titulo):
    q = urllib.parse.quote(titulo[:200])
    url = f"https://api.openalex.org/works?filter=title.search:{q}&per_page=1&mailto={EMAIL}"
    data = fetch_json(url)
    if not data or not data.get("results"):
        return None, None
    w = data["results"][0]
    if not titulo_parece_igual(titulo, w.get("title", "") or w.get("display_name", "")):
        return None, None
    doi = w.get("doi")
    if doi:
        doi = doi.replace("https://doi.org/", "").lower()
    pdf = None
    for loc in w.get("locations") or []:
        if loc.get("pdf_url"):
            pdf = loc["pdf_url"]
            break
    return doi, pdf


def try_bdtd_titulo(titulo):
    termo = " ".join(titulo.split()[:12])
    url = f"https://bdtd.ibict.br/vufind/api/v1/search?lookfor={urllib.parse.quote(termo)}&type=Title&limit=3"
    data = fetch_json(url)
    if not data:
        return None, None
    for registro in data.get("records") or []:
        if not titulo_parece_igual(titulo, registro.get("title", "")):
            continue
        for u in registro.get("urls") or []:
            handle = u.get("url")
            if handle:
                pdf = minerar_pdf_de_pagina(handle)
                if pdf:
                    return None, pdf
    return None, None


CASCATA_SEM_DOI = [
    ("semantic_scholar_titulo", try_semantic_scholar_titulo),
    ("openalex_titulo", try_openalex_titulo),
    ("bdtd_titulo", try_bdtd_titulo),
]


# ==== Sci-Hub (opt-in — só é chamado se autorizado explicitamente) ====

SCIHUB_MIRRORS = ["https://sci-hub.st", "https://sci-hub.ru", "https://sci-hub.se"]
SCIHUB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8",
}


def _extrair_pdf_scihub(html, mirror):
    padroes = [
        r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
        r'<object[^>]+data=["\']([^"\']+\.pdf[^"\']*)["\']',
        r'["\'](/storage/[^"\']+\.pdf)["\']',
    ]
    for p in padroes:
        m = re.search(p, html, re.IGNORECASE)
        if m:
            return _absolutizar(m.group(1), mirror)
    return None


def try_scihub(doi):
    for mirror in SCIHUB_MIRRORS:
        try:
            r = requests.get(f"{mirror}/{doi}", headers=SCIHUB_HEADERS, timeout=(10, 30))
        except Exception:
            continue
        if r.status_code != 200:
            continue
        html = r.text
        if "captcha" in html.lower() and "article" not in html.lower():
            continue
        url = _extrair_pdf_scihub(html, mirror)
        if url:
            return url
        time.sleep(0.5)
    return None


# ==== Relatório ====

def carregar_relatorio_anterior(caminho: Path):
    if not caminho.exists():
        return None
    try:
        df = pd.read_csv(caminho, dtype=str)
        return df.set_index("chave") if "chave" in df.columns else None
    except Exception:
        return None


def escrever_relatorio(linhas, caminho: Path):
    df = pd.DataFrame(linhas)
    for c in COLUNAS_RELATORIO:
        if c not in df.columns:
            df[c] = ""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df[COLUNAS_RELATORIO].to_csv(caminho, index=False, encoding="utf-8-sig")


def resumir(df):
    if df.empty:
        return "Nenhum paper processado."
    partes = [f"Total: {len(df)} papers"]
    for status, n in df["status"].value_counts().items():
        partes.append(f"  {status}: {n}")
    por_fonte = df[df["status"].isin(["ok", "scihub_ok"])]["fonte"].value_counts()
    if not por_fonte.empty:
        partes.append("Por fonte:")
        for fonte, n in por_fonte.items():
            partes.append(f"  {fonte}: {n}")
    return "\n".join(partes)


def herdar_proveniencia(resultado, resultados_anteriores):
    """Se status=ja_existia, herda fonte/url/motivo da execução anterior (mesma chave)
    em vez de zerar — a proveniência de quem baixou o PDF não deve se perder num rerun."""
    anterior_linha = resultados_anteriores.get(resultado["chave"])
    if resultado["status"] == "ja_existia" and anterior_linha:
        for campo in ("fonte", "url", "motivo"):
            if not resultado.get(campo) and anterior_linha.get(campo):
                resultado[campo] = anterior_linha[campo]
    return resultado


# ==== Orquestração: baixar 1 paper ====

def baixar_paper(chave, titulo, autores, ano, doi, saida_pdfs: Path, scihub_dois: set):
    destino = saida_pdfs / f"{chave}.pdf"
    base = {"chave": chave, "titulo": titulo, "autores": autores or "", "ano": ano or "", "doi": doi or ""}

    if is_valid_pdf(destino):
        return {**base, "status": "ja_existia", "fonte": "", "url": "", "motivo": "", "arquivo": str(destino)}
    if destino.exists():
        destino.unlink()

    doi_atual = doi
    pdf_direto = None

    if not doi_atual:
        for _nome, fn in CASCATA_SEM_DOI:
            try:
                doi_achado, pdf_achado = fn(titulo)
            except Exception:
                doi_achado, pdf_achado = None, None
            time.sleep(PAUSA_ENTRE_FONTES)
            if pdf_achado:
                pdf_direto = pdf_achado
                break
            if doi_achado:
                doi_atual = doi_achado
                break

    if pdf_direto:
        conteudo = fetch(pdf_direto)
        if conteudo and save_if_pdf(conteudo, destino):
            return {**base, "doi": doi_atual or "", "status": "ok", "fonte": "busca_por_titulo",
                    "url": pdf_direto, "motivo": "", "arquivo": str(destino)}

    if doi_atual:
        for nome, fn in CASCATA_COM_DOI:
            try:
                url = fn(doi_atual)
            except Exception:
                url = None
            time.sleep(PAUSA_ENTRE_FONTES)
            if url:
                conteudo = fetch(url)
                if conteudo and save_if_pdf(conteudo, destino):
                    return {**base, "doi": doi_atual, "status": "ok", "fonte": nome,
                            "url": url, "motivo": "", "arquivo": str(destino)}

        if doi_atual in scihub_dois:
            url = try_scihub(doi_atual)
            if url:
                conteudo = fetch(url, timeout=TIMEOUT_SCIHUB, headers=SCIHUB_HEADERS)
                if conteudo and save_if_pdf(conteudo, destino):
                    return {**base, "doi": doi_atual, "status": "scihub_ok", "fonte": "scihub",
                            "url": url, "motivo": "", "arquivo": str(destino)}
            return {**base, "doi": doi_atual, "status": "nao_encontrado", "fonte": "",
                    "url": "", "motivo": "sci-hub tentado sem sucesso", "arquivo": ""}

        return {**base, "doi": doi_atual, "status": "nao_encontrado", "fonte": "",
                "url": "", "motivo": "sem versão de acesso aberto encontrada", "arquivo": ""}

    return {**base, "status": "nao_encontrado", "fonte": "", "url": "",
            "motivo": "sem DOI e sem versão OA encontrada por título", "arquivo": ""}


# ==== Modo batch ====

ALIASES_COLUNA = {
    "titulo": ["titulo", "título", "title"],
    "doi": ["doi", "doi_limpo"],
    "autor": ["autor", "autores", "primeiro_autor", "author", "authors"],
    "ano": ["ano", "year"],
    "chave": ["chave", "citekey", "bib_key"],
}


def detectar_coluna(df, aliases):
    cols_norm = {normalizar_titulo(c): c for c in df.columns}
    for alias in aliases:
        if normalizar_titulo(alias) in cols_norm:
            return cols_norm[normalizar_titulo(alias)]
    return None


def main_batch(args):
    caminho = Path(args.planilha)
    df = pd.read_csv(caminho) if caminho.suffix.lower() == ".csv" else pd.read_excel(caminho)

    col_titulo = args.col_titulo or detectar_coluna(df, ALIASES_COLUNA["titulo"])
    col_doi = args.col_doi or detectar_coluna(df, ALIASES_COLUNA["doi"])
    col_autor = args.col_autor or detectar_coluna(df, ALIASES_COLUNA["autor"])
    col_ano = args.col_ano or detectar_coluna(df, ALIASES_COLUNA["ano"])
    col_chave = args.col_chave or detectar_coluna(df, ALIASES_COLUNA["chave"])

    if not col_titulo:
        print(f"ERRO: não encontrei coluna de título. Colunas disponíveis: {list(df.columns)}")
        print("Use --col-titulo NOME para indicar manualmente.")
        sys.exit(1)

    avisar_titulos_duplicados(df[col_titulo])

    saida_pdfs = Path(args.saida_pdfs) if args.saida_pdfs else caminho.parent / "pdfs"
    saida_pdfs.mkdir(parents=True, exist_ok=True)
    relatorio_path = Path(args.relatorio) if args.relatorio else saida_pdfs.parent / "relatorio_pdfs.csv"

    anterior = carregar_relatorio_anterior(relatorio_path)
    scihub_dois = {d.strip().lower() for d in args.scihub_dois.split(",") if d.strip()} if args.scihub_dois else set()

    # resultados começa com tudo que já estava no relatório anterior, para que uma
    # rodada parcial (--limite, ou uma planilha menor) nunca apague dados de rodadas
    # anteriores — só sobrescreve as chaves realmente retocadas nesta execução.
    resultados = {}
    if anterior is not None:
        for chave_ant, linha in anterior.iterrows():
            d = linha.to_dict()
            d["chave"] = chave_ant
            resultados[chave_ant] = d

    # Chaves válidas já presentes na coluna de chave entram antes de gerar qualquer chave nova:
    # senão a chave gerada para uma linha anterior colide com a chave gravada numa linha posterior
    # e dois papers disputam o mesmo <chave>.pdf. Não herda do relatório anterior.
    chaves_usadas, processados = set(), 0
    if col_chave:
        chaves_usadas = {str(v).strip() for v in df[col_chave] if pd.notna(v) and chave_valida(v)}
    for _, row in df.iterrows():
        if args.limite and processados >= args.limite:
            break
        if not col_titulo or pd.isna(row[col_titulo]):
            continue
        titulo = str(row[col_titulo]).strip()
        if not titulo:
            continue

        doi = limpar_doi(row[col_doi]) if col_doi else None
        autores = str(row[col_autor]).strip() if col_autor and pd.notna(row[col_autor]) else None
        ano = row[col_ano] if col_ano and pd.notna(row[col_ano]) else None

        chave_existente = row[col_chave] if col_chave and pd.notna(row[col_chave]) else None
        if chave_existente is not None and chave_valida(chave_existente):
            chave = str(chave_existente).strip()
        else:
            if chave_existente is not None and str(chave_existente).strip():
                print(f"  ⚠ chave inválida {str(chave_existente).strip()!r} (coluna {col_chave}) "
                      "— gerando uma nova a partir de autor e ano.")
            chave = gerar_chave(titulo, autores, ano, chaves_usadas)
        chaves_usadas.add(chave)

        if args.apenas_pendentes and chave in resultados:
            if resultados[chave].get("status") in ("ok", "ja_existia", "scihub_ok", "nao_e_manuscrito"):
                continue  # já está em `resultados` (herdado do relatório anterior); não reprocessa

        resultado = herdar_proveniencia(
            baixar_paper(chave, titulo, autores, ano, doi, saida_pdfs, scihub_dois), resultados
        )
        resultados[chave] = resultado
        processados += 1
        print(f"  [{resultado['status']}] {chave}: {titulo[:70]}")

        if processados % 10 == 0:
            escrever_relatorio(list(resultados.values()), relatorio_path)

    escrever_relatorio(list(resultados.values()), relatorio_path)
    print()
    print(resumir(pd.DataFrame(list(resultados.values()))))
    print(f"\nRelatório: {relatorio_path}")


# ==== Modo single ====

def main_single(args):
    saida_pdfs = Path(args.saida_pdfs or "./pdfs")
    saida_pdfs.mkdir(parents=True, exist_ok=True)
    relatorio_path = Path(args.relatorio) if args.relatorio else saida_pdfs.parent / "relatorio_pdfs.csv"

    doi = limpar_doi(args.doi) if args.doi else None
    titulo = args.titulo or ""
    autores = args.autor
    ano = args.ano

    anterior = carregar_relatorio_anterior(relatorio_path)
    resultados = {}
    if anterior is not None:
        for chave_ant, linha in anterior.iterrows():
            d = linha.to_dict()
            d["chave"] = chave_ant
            resultados[chave_ant] = d

    # Chave sempre determinística a partir do próprio DOI/título (não do relatório
    # anterior) — assim, pedir o mesmo paper de novo bate no mesmo arquivo e vira
    # "já existia" em vez de gerar uma cópia com sufixo novo. Dois papers diferentes
    # do mesmo autor/ano sem --chave explícita podem colidir; nesse caso, passe --chave.
    chave_arg = (args.chave or "").strip()
    if chave_arg and not chave_valida(chave_arg):
        print(f"Aviso: --chave {chave_arg!r} não serve como nome de arquivo/citekey "
              "(use letras, dígitos, _ ou -, começando por letra) — gerando uma nova.")
        chave_arg = ""
    if chave_arg:
        chave = chave_arg
    elif titulo:
        chave = gerar_chave(titulo, autores, ano, set())
    elif doi:
        chave = chave_de_doi(doi)
    else:
        chave = gerar_chave("sem_titulo", autores, ano, set())

    scihub_dois = {doi} if (args.tentar_scihub and doi) else set()

    resultado = herdar_proveniencia(
        baixar_paper(chave, titulo, autores, ano, doi, saida_pdfs, scihub_dois), resultados
    )
    resultados[chave] = resultado
    escrever_relatorio(list(resultados.values()), relatorio_path)

    print(resumir(pd.DataFrame([resultado])))
    if resultado["status"] in ("ok", "scihub_ok", "ja_existia"):
        print(f"Arquivo: {resultado['arquivo']}")
    print(f"Relatório: {relatorio_path}")


# ==== CLI ====

def parse_args():
    p = argparse.ArgumentParser(description="Baixa PDFs acadêmicos a partir de DOI, título ou planilha.")
    sub = p.add_subparsers(dest="comando", required=True)

    b = sub.add_parser("batch", help="baixa PDFs para todos os papers de uma planilha")
    b.add_argument("--planilha", required=True)
    b.add_argument("--col-titulo")
    b.add_argument("--col-doi")
    b.add_argument("--col-autor")
    b.add_argument("--col-ano")
    b.add_argument("--col-chave")
    b.add_argument("--saida-pdfs")
    b.add_argument("--relatorio")
    b.add_argument("--email")
    b.add_argument("--scihub-dois", default="", help="lista de DOIs separados por vírgula, só após confirmação do usuário")
    b.add_argument("--apenas-pendentes", action="store_true")
    b.add_argument("--limite", type=int)

    s = sub.add_parser("single", help="baixa 1 PDF a partir de DOI ou título")
    s.add_argument("--doi")
    s.add_argument("--titulo")
    s.add_argument("--autor")
    s.add_argument("--ano")
    s.add_argument("--chave")
    s.add_argument("--saida-pdfs", default="./pdfs")
    s.add_argument("--relatorio")
    s.add_argument("--email")
    s.add_argument("--tentar-scihub", action="store_true", help="só após confirmação explícita do usuário")

    return p.parse_args()


def main():
    global EMAIL
    args = parse_args()

    if getattr(args, "email", None):
        EMAIL = args.email
    if not EMAIL:
        print("Aviso: nenhum e-mail definido (--email ou $PDF_DOWNLOADER_EMAIL). "
              "Unpaywall funciona melhor com um e-mail real de contato.")
        EMAIL = "anonimo@example.com"
    SESSAO.headers["User-Agent"] = f"Mozilla/5.0 (academic paper downloader; contact {EMAIL})"

    if args.comando == "batch":
        main_batch(args)
    else:
        if not args.doi and not args.titulo:
            print("ERRO: informe --doi ou --titulo")
            sys.exit(1)
        main_single(args)


if __name__ == "__main__":
    main()
