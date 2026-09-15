"""Normalização compartilhada de campos bibliográficos (DOI, título, idioma, tipo, autores).

Usado por importadores, dedup, filtros e handoffs. Funções puras, sem pandas.
"""

import html
import re
import unicodedata

from . import chave as _chave


def vazio(valor):
    if valor is None:
        return True
    if isinstance(valor, float) and valor != valor:
        return True
    return str(valor).strip() == "" or str(valor).strip().lower() in {"nan", "none", "null", "na", "n/a"}


def texto(valor):
    """String limpa (sem HTML, espaços colapsados) ou ''."""
    if vazio(valor):
        return ""
    s = html.unescape(str(valor))
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def ascii_fold(valor):
    return unicodedata.normalize("NFKD", texto(valor)).encode("ascii", "ignore").decode("ascii")


_DOI_PREFIXO = re.compile(r"^(?:https?://)?(?:dx\.)?(?:doi\.org/|doi:\s*)", re.IGNORECASE)
_DOI_VALIDO = re.compile(r"^10\.\d{4,9}/\S+$")


def doi(valor):
    """DOI minúsculo sem prefixo de URL; '' se não parecer DOI."""
    s = texto(valor)
    if not s:
        return ""
    s = _DOI_PREFIXO.sub("", s).strip().rstrip(".;,").lower()
    return s if _DOI_VALIDO.match(s) else ""


def titulo_normalizado(valor):
    """Para comparação: sem HTML, ASCII, minúsculo, sem pontuação, espaços colapsados."""
    s = ascii_fold(valor).lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def titulo_principal(valor):
    """Parte do título antes de ':' (ou ' - '), normalizada."""
    s = texto(valor)
    s = re.split(r":|\s[-–]\s", s, maxsplit=1)[0]
    return titulo_normalizado(s)


_NUMERAIS_PARTE = re.compile(r"\b(part|parte|vol|volume|study|estudo)\s*([ivxlc]+|\d+)\b", re.IGNORECASE)


def marcador_parte(valor):
    """Retorna marcadores de parte/volume ('part ii', 'estudo 2') para impedir fusões indevidas."""
    return sorted({f"{m.group(1).lower()} {m.group(2).lower()}" for m in _NUMERAIS_PARTE.finditer(ascii_fold(valor))})


_MAPA_IDIOMA = {
    "pt": "pt", "por": "pt", "portugues": "pt", "portuguese": "pt", "portugues brasil": "pt", "portugues (brasil)": "pt",
    "en": "en", "eng": "en", "english": "en", "ingles": "en",
    "es": "es", "spa": "es", "spanish": "es", "espanhol": "es", "espanol": "es", "castellano": "es",
    "fr": "fr", "fre": "fr", "fra": "fr", "french": "fr", "frances": "fr",
    "de": "de", "ger": "de", "deu": "de", "german": "de", "alemao": "de",
    "it": "it", "ita": "it", "italian": "it", "italiano": "it",
    "pl": "pl", "pol": "pl", "polish": "pl", "polones": "pl",
    "zh": "zh", "chi": "zh", "chinese": "zh", "ru": "ru", "rus": "ru", "russian": "ru",
    "ja": "ja", "japanese": "ja", "ko": "ko", "korean": "ko", "nl": "nl", "dutch": "nl",
}


def idioma(valor):
    """Código ISO 639-1; primeiro idioma quando há vários ('Português, Inglês' -> 'pt'); '' se desconhecido."""
    s = ascii_fold(valor).lower()
    if not s:
        return ""
    primeiro = re.split(r"[;,/|]", s)[0].strip()
    return _MAPA_IDIOMA.get(primeiro, _MAPA_IDIOMA.get(primeiro.split(" ")[0], ""))


_MAPA_TIPO = [
    (r"retract|errat|correction|corrigend", "errata"),
    (r"editorial|letter|comment|note\b|nota\b|news", "editorial"),
    (r"preprint|posted.content|working.paper|discussion.paper|ssrn", "preprint"),
    (r"review|revis(a|ã)o", "revisao"),
    (r"tese|doutorado|phd|doctoral", "tese"),
    (r"disserta|mestrado|master|profissionalizante", "dissertacao"),
    (r"thesis", "tese"),
    (r"chapter|cap(i|í)tulo|book.chapter|incollection", "capitulo"),
    (r"^book$|livro|monograph", "livro"),
    (r"proceeding|conference|congress|anais|evento|meeting|paper.presented", "evento"),
    (r"report|relat(o|ó)rio|technical|nota t(e|é)cnica|policy brief|texto para discuss", "relatorio"),
    (r"article|artigo|research.article|journal|early access", "artigo"),
]


def tipo_publicacao(valor):
    """Mapeia o tipo de documento da fonte para esquema.TIPOS_PUBLICACAO ('outro' se não reconhecido)."""
    s = ascii_fold(valor).lower()
    if not s:
        return "outro"
    for padrao, tipo in _MAPA_TIPO:
        if re.search(padrao, s):
            return tipo
    return "outro"


def autores_canonicos(valor):
    """Lista de autores no formato canônico 'Sobrenome, Nomes | Sobrenome, Nomes'."""
    itens = _chave.lista_autores(valor)
    saida = []
    for a in itens:
        a = texto(a)
        if not a:
            continue
        if "," in a:
            sob, nomes = a.split(",", 1)
            saida.append(f"{sob.strip()}, {nomes.strip()}".strip(", "))
        else:
            sob = _chave.sobrenome(a)
            resto = " ".join(a.replace(sob, "", 1).split()) if sob else ""
            saida.append(f"{sob}, {resto}".strip(", ") if sob else a)
    return " | ".join(saida)


def sobrenome_primeiro_autor(valor):
    return _chave.sobrenome(_chave.primeiro_autor(valor))


def ano(valor):
    """Ano inteiro como string ('2019') ou ''."""
    t = _chave.ano_texto(valor)
    return "" if t == "sd" else t
