"""Chaves de citação Sobrenome+Ano compartilhadas entre as skills de revisão.

Este arquivo é vendorizado IDÊNTICO (mesmo sha256) em:
  - revisao-sistematica/scripts/rslib/chave.py
  - baixar-pdfs-academicos/scripts/chave.py
  - gerar-bibtex/scripts/chave.py
  - fichamento-sistematico/scripts/chave.py
Um teste de sincronia compara os hashes. Não edite uma cópia só.

Por que existe: a versão anterior partia a lista de autores em [;,] e pegava o
último token, o que gerava chaves erradas para formatos comuns de exportação
("Weihs M." -> "M2025"; listas do OpenAlex separadas por "|" -> sobrenome do
último autor; "João da Silva Filho" -> "Filho").

Algoritmo (ALGORITMO_CHAVE = "2"):
  1. primeiro_autor(): separa a lista pelo primeiro separador presente, na
     ordem "|", ";", " and "; sem nenhum deles, aplica a regra da vírgula, que
     distingue "Sobrenome, Nome[, Sobrenome, Nome]" de listas de nomes completos
     ("JF de Oliveira, JC Libâneo"; "Weihs M., Rahman A.").
  2. sobrenome(): texto antes da vírgula; senão remove iniciais finais
     ("Weihs M.") ou iniciais do começo ("JF de Oliveira"); senão último token,
     pulando sufixos (Jr, Filho, Neto...).
  3. normalizar(): ASCII, remove partículas minúsculas iniciais (de, da, van...),
     junta em CamelCase, só [A-Za-z0-9]; vazio -> "Anon".
  4. ano: primeiro número de 4 dígitos entre 1500 e 2099; senão "sd".
  5. sufixo de colisão: a..z, aa, ab, ... (determinístico dado o conjunto usado).

Uso:
    from chave import gerar_chave, chave_valida
    usadas = set()
    k = gerar_chave(titulo, autores, ano, usadas); usadas.add(k)
"""

import re
import unicodedata

ALGORITMO_CHAVE = "2"

_PARTICULAS = {
    "de", "da", "do", "dos", "das", "del", "della", "delle", "di", "du",
    "van", "von", "der", "den", "le", "la", "ter", "ten", "e", "y", "af", "zu",
}
_SUFIXOS = {"jr", "junior", "filho", "neto", "sobrinho", "sr", "ii", "iii", "iv"}
_INICIAIS = re.compile(r"^(?:[A-Z]\.?-?){1,3}$")
_PARENTESES = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_ANO = re.compile(r"(1[5-9]\d{2}|20\d{2})")
_CHAVE_VALIDA = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,60}$")


def _vazio(valor):
    if valor is None:
        return True
    if isinstance(valor, float) and valor != valor:  # NaN sem depender de pandas
        return True
    return str(valor).strip() == "" or str(valor).strip().lower() in {"nan", "none", "null"}


def _ascii(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def _eh_iniciais(token):
    return bool(_INICIAIS.match(token.strip(",")))


def _lista_com_and(s):
    """" and " separa autores (estilo BibTeX) só quando as partes parecem nomes de pessoas.

    Evita partir nomes institucionais como "Organisation for Economic Co-operation and Development".
    """
    partes = re.split(r"\s+and\s+", s, flags=re.IGNORECASE)
    if len(partes) < 2:
        return False
    return "," in partes[0] or all(len(p.split()) <= 3 for p in partes)


def primeiro_autor(autores):
    """Devolve o primeiro autor de uma lista em qualquer formato comum de exportação."""
    if _vazio(autores):
        return ""
    s = _PARENTESES.sub(" ", str(autores)).strip()
    for sep in ("|", ";"):
        if sep in s:
            return s.split(sep)[0].strip()
    if _lista_com_and(s):
        return re.split(r"\s+and\s+", s, flags=re.IGNORECASE)[0].strip()
    if "," not in s:
        return s
    partes = [p.strip() for p in s.split(",") if p.strip()]
    if not partes:
        return ""
    tokens0 = partes[0].split()
    # Estilo PoP/Scholar: começa com iniciais ("JF de Oliveira, JC Libâneo").
    if tokens0 and _eh_iniciais(tokens0[0]) and len(tokens0) > 1:
        return partes[0]
    # Estilo Scopus antigo: termina com iniciais ("Weihs M., Rahman A.").
    if len(tokens0) > 1 and _eh_iniciais(tokens0[-1]):
        return partes[0]
    # Um só autor "Sobrenome, Nome" ou lista "Sobrenome, Nome, Sobrenome, Nome".
    if len(partes) == 1:
        return partes[0]
    sobrenome_primeiro = (
        len(tokens0) == 1
        or tokens0[0].lower() in _PARTICULAS
        or len(partes[1].split()) == 1
    )
    if sobrenome_primeiro:
        return f"{partes[0]}, {partes[1]}"
    # Lista de nomes completos separados por vírgula ("João Silva, Maria Souza").
    return partes[0]


def sobrenome(autor):
    """Extrai o sobrenome de um único autor (texto livre, sem normalizar)."""
    if _vazio(autor):
        return ""
    a = _PARENTESES.sub(" ", str(autor)).strip()
    if "," in a:
        return a.split(",")[0].strip()
    tokens = a.split()
    if not tokens:
        return ""
    if len(tokens) == 1:
        return tokens[0]
    if _eh_iniciais(tokens[-1]):
        while len(tokens) > 1 and _eh_iniciais(tokens[-1]):
            tokens.pop()
        return " ".join(tokens)
    if _eh_iniciais(tokens[0]):
        while len(tokens) > 1 and _eh_iniciais(tokens[0]):
            tokens.pop(0)
        return " ".join(tokens)
    ultimo = len(tokens) - 1
    if _ascii(tokens[ultimo]).lower().strip(".") in _SUFIXOS and ultimo > 0:
        ultimo -= 1
    return tokens[ultimo]


def normalizar(texto):
    """ASCII, sem partículas iniciais minúsculas, CamelCase, só alfanuméricos."""
    if _vazio(texto):
        return "Anon"
    tokens = [t for t in re.split(r"[\s\-]+", _ascii(str(texto))) if t]
    while len(tokens) > 1 and tokens[0] in _PARTICULAS:
        tokens.pop(0)
    partes = []
    for t in tokens:
        t = re.sub(r"[^A-Za-z0-9]", "", t)
        if not t:
            continue
        if t.isupper() and len(t) > 1:
            t = t.capitalize()
        partes.append(t[0].upper() + t[1:])
    resultado = "".join(partes)[:40]
    return resultado or "Anon"


def ano_texto(ano):
    if _vazio(ano):
        return "sd"
    m = _ANO.search(str(ano))
    return m.group(1) if m else "sd"


def _sufixos():
    letras = "abcdefghijklmnopqrstuvwxyz"
    for a in letras:
        yield a
    for a in letras:
        for b in letras:
            yield a + b


def gerar_chave(titulo, autores, ano, usadas):
    """Chave Sobrenome+Ano única em relação a `usadas` (o chamador adiciona a chave ao conjunto).

    `titulo` é aceito por compatibilidade com a assinatura antiga; não entra na chave.
    """
    base = normalizar(sobrenome(primeiro_autor(autores))) + ano_texto(ano)
    if base not in usadas:
        return base
    for s in _sufixos():
        candidata = base + s
        if candidata not in usadas:
            return candidata
    raise ValueError(f"colisões demais para a chave {base}")


def chave_valida(chave):
    """True se a chave serve como nome de arquivo e citekey (rejeita URLs, IDs do OpenAlex etc.)."""
    return not _vazio(chave) and bool(_CHAVE_VALIDA.match(str(chave).strip()))


def lista_autores(autores):
    """Lista de autores individuais, para formatar o campo author do BibTeX."""
    if _vazio(autores):
        return []
    s = _PARENTESES.sub(" ", str(autores)).strip()
    for sep in ("|", ";"):
        if sep in s:
            return [p.strip() for p in s.split(sep) if p.strip()]
    if _lista_com_and(s):
        return [p.strip() for p in re.split(r"\s+and\s+", s, flags=re.IGNORECASE) if p.strip()]
    if "," not in s:
        return [s]
    partes = [p.strip() for p in s.split(",") if p.strip()]
    tokens0 = partes[0].split()
    estilo_nome_completo = (
        (tokens0 and _eh_iniciais(tokens0[0]) and len(tokens0) > 1)
        or (len(tokens0) > 1 and _eh_iniciais(tokens0[-1]))
    )
    if len(partes) == 1:
        return partes
    if not estilo_nome_completo:
        sobrenome_primeiro = (
            len(tokens0) == 1 or tokens0[0].lower() in _PARTICULAS or len(partes[1].split()) == 1
        )
        if sobrenome_primeiro and len(partes) % 2 == 0:
            return [f"{partes[i]}, {partes[i + 1]}" for i in range(0, len(partes), 2)]
        if sobrenome_primeiro:
            return [f"{partes[0]}, {partes[1]}"] + partes[2:]
    return partes
