#!/usr/bin/env python3
"""
verificar_conteudo.py — confere se os PDFs baixados por baixar_pdfs.py são
mesmo o texto esperado (não só "é um PDF válido", mas "é o PDF certo").

Extrai o texto das primeiras páginas de cada PDF e confere se palavras do
título e o sobrenome do autor aparecem nele. Roda depois de baixar_pdfs.py,
sobre o mesmo relatório e a mesma pasta de PDFs — pode ser reexecutado a
qualquer momento, inclusive sobre PDFs baixados por outro meio.

Uso:
    python3 verificar_conteudo.py --pdfs ./pdfs --relatorio relatorio_pdfs.csv

O sobrenome procurado no PDF sai de scripts/chave.py (`primeiro_autor` + `sobrenome`),
o mesmo código que gera a chave do arquivo. A versão anterior pegava o último token do
primeiro pedaço antes de ";" ou ",", o que procurava "m" em "Weihs M." e "filho" em
"João da Silva Filho" — e dava `autor_encontrado` falso ou trivialmente verdadeiro.
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

# chave.py mora ao lado deste script; o caminho explícito permite importar este módulo
# de fora da pasta (testes, outras skills). Sem bytecode para não sujar a pasta da skill.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chave  # noqa: E402

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

STOPWORDS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "em", "um", "uma", "e", "ou",
    "para", "com", "no", "na", "nos", "nas", "por", "sobre", "entre", "que",
    "the", "of", "and", "in", "on", "for", "to", "an", "is", "are", "from", "as",
}


def normalizar(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9\s]", " ", t)


def palavras_chave(titulo, minimo=5):
    palavras = [p for p in normalizar(titulo).split() if len(p) > 3 and p not in STOPWORDS]
    return palavras[:max(minimo, len(palavras))]


def extrair_texto_pdf(caminho, paginas=4):
    if fitz is None:
        return None
    try:
        doc = fitz.open(caminho)
        texto = "".join(doc[i].get_text() for i in range(min(paginas, len(doc))))
        doc.close()
        return texto
    except Exception:
        return None


def sobrenome_autor(autores):
    """Sobrenome do primeiro autor, normalizado para busca no texto do PDF.

    Devolve None quando não há autor utilizável. Sobrenomes compostos ("Shahidul
    Islam", "de Oliveira") saem com espaços simples; a comparação em
    `veredito_conteudo` colapsa os espaços do texto do PDF para casar quebras de linha.
    """
    if not autores or (isinstance(autores, float) and pd.isna(autores)):
        return None
    sob = chave.sobrenome(chave.primeiro_autor(autores))
    sob = " ".join(normalizar(sob).split())
    return sob or None


def veredito_conteudo(titulo, autores, texto):
    if texto is None or len(texto.strip()) < 200:
        return {"veredito": "sem_camada_de_texto", "cobertura_titulo": None, "autor_encontrado": None}

    texto_norm = normalizar(texto)
    palavras = palavras_chave(titulo)
    cobertura = (sum(1 for p in palavras if p in texto_norm) / len(palavras)) if palavras else None

    sobrenome = sobrenome_autor(autores)
    autor_ok = (sobrenome in " ".join(texto_norm.split())) if sobrenome else None

    if cobertura is not None and cobertura >= 0.6:
        veredito = "confere"
    elif cobertura is not None and cobertura >= 0.3 and autor_ok:
        veredito = "confere"
    elif autor_ok:
        veredito = "conferir_a_mao"
    else:
        veredito = "suspeito"

    return {
        "veredito": veredito,
        "cobertura_titulo": round(cobertura, 2) if cobertura is not None else None,
        "autor_encontrado": autor_ok,
    }


def main():
    p = argparse.ArgumentParser(description="Confere se os PDFs baixados são o texto certo.")
    p.add_argument("--pdfs", required=True, help="pasta com os PDFs baixados")
    p.add_argument("--relatorio", required=True, help="relatorio_pdfs.csv produzido por baixar_pdfs.py")
    p.add_argument("--saida", help="default: verificacao_conteudo.csv ao lado do relatório")
    args = p.parse_args()

    if fitz is None:
        print("AVISO: PyMuPDF ('pymupdf') não está instalado. Rode:")
        print("  pip3 install -r requirements.txt")
        return

    pdfs_dir = Path(args.pdfs)
    df = pd.read_csv(args.relatorio, dtype=str)
    saida = Path(args.saida) if args.saida else Path(args.relatorio).with_name("verificacao_conteudo.csv")

    linhas = []
    for _, row in df.iterrows():
        if row.get("status") not in ("ok", "ja_existia", "scihub_ok"):
            continue
        caminho = pdfs_dir / f"{row['chave']}.pdf"
        if not caminho.exists():
            continue
        texto = extrair_texto_pdf(caminho)
        resultado = veredito_conteudo(row.get("titulo", ""), row.get("autores", ""), texto)
        linhas.append({"chave": row["chave"], "titulo": row.get("titulo", ""), **resultado})
        print(f"  [{resultado['veredito']}] {row['chave']}")

    saida_df = pd.DataFrame(linhas)
    saida_df.to_csv(saida, index=False, encoding="utf-8-sig")

    print()
    print(f"Verificados: {len(linhas)} PDFs")
    if not saida_df.empty:
        print(saida_df["veredito"].value_counts().to_string())
    print(f"Relatório: {saida}")


if __name__ == "__main__":
    main()
