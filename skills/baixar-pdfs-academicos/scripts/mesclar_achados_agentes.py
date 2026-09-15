#!/usr/bin/env python3
"""
mesclar_achados_agentes.py — aplica ao relatório de download os resultados de uma
busca feita por agentes Claude Code em paralelo (ver SKILL.md, etapa 8): quando a
cascata automática de baixar_pdfs.py + o Sci-Hub opcional ainda deixam papers como
`nao_encontrado`, agentes com busca web tentam achar cópias legítimas hospedadas fora
do alcance da cascata — página pessoal de autor, repositório institucional, servidor
de preprint, etc. Este script aplica os achados desses agentes de volta ao mesmo CSV
que baixar_pdfs.py produz, com o mesmo formato/colunas, para o resto do fluxo
(--apenas-pendentes, verificar_conteudo.py, resumir()) continuar funcionando igual.

**Nunca sobrescreve uma linha cujo status já é "resolvido"** (ok, ja_existia,
scihub_ok, nao_e_manuscrito) — só mexe em linhas que ainda estão `nao_encontrado`.
Isso existe porque copiar o PDF de um registro "parecido" para satisfazer outro é
exatamente o tipo de erro que motivou este script: dois registros com o mesmo título
mas DOIs diferentes (ex. um par preprint/versão publicada, ou uma linha duplicada por
engano na indexação de origem — ver `avisar_titulos_duplicados` em baixar_pdfs.py) NÃO
são automaticamente "o mesmo achado". Cada `chave` só vira `ok` quando ela mesma,
especificamente, foi verificada — nunca por herança de uma chave vizinha.

Entrada esperada em --achados (arquivo JSON, lista de objetos, um por paper que o(s)
agente(s) tentaram resolver — inclua tanto os achados quanto os não-achados, para que
o `motivo` de cada um fique registrado):

    [
      {"chave": "Autor2020", "encontrado": true,
       "url": "https://autor.edu/~fulano/papers/autor2020.pdf",
       "fonte": "agente_busca_web", "versao": "preprint", "motivo": ""},

      {"chave": "Outro2021", "encontrado": false,
       "motivo": "Nenhuma cópia legítima encontrada (página do autor, repositório "
                  "institucional, preprint) além do que a cascata automática já tentou."},

      {"chave": "Terceiro2026", "encontrado": false, "nao_e_manuscrito": true,
       "motivo": "DOI aponta para um pré-registro OSF sem resultados ainda — não é "
                  "um manuscrito completo, não há PDF para achar."}
    ]

Campos:
  chave        (obrigatório) — deve bater com uma linha já `nao_encontrado` no relatório.
  encontrado   (obrigatório) — true/false.
  url          fonte do achado, se encontrado=true.
  fonte        default "agente_busca_web" se omitido e encontrado=true.
  versao       "preprint" só quando houver evidência real (rótulo explícito
               "preprint"/"forthcoming" na própria fonte, ou o DOI/URL do achado é
               claramente diferente do DOI do registro/editora) — não adivinhe;
               deixe em branco/omita quando não tiver certeza.
  motivo       texto livre — sempre útil, encontrado ou não.
  nao_e_manuscrito  true quando o identificador do registro não aponta pra um
               manuscrito completo (pré-registro sem resultados, entrada de dataset,
               errata/correção) — vira status="nao_e_manuscrito" em vez de
               "nao_encontrado", pra não ficar pendurado como se fosse falha de busca.

Uso:
    python3 mesclar_achados_agentes.py \\
        --relatorio caminho/relatorio_pdfs.csv \\
        --achados caminho/achados.json \\
        --saida-pdfs caminho/pdfs
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

COLUNAS_RELATORIO = [
    "chave", "titulo", "autores", "ano", "doi",
    "status", "fonte", "url", "versao", "motivo", "arquivo",
]

# Espelha o allow-list de --apenas-pendentes em baixar_pdfs.py — mantenha os dois em
# sincronia se esse conjunto de status "resolvidos" mudar num dos dois lugares.
STATUS_JA_RESOLVIDO = ("ok", "ja_existia", "scihub_ok", "nao_e_manuscrito")

FONTE_PADRAO = "agente_busca_web"


def carregar_relatorio(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        sys.exit(f"ERRO: relatório não encontrado em {caminho}")
    df = pd.read_csv(caminho, dtype=str).fillna("")
    if "chave" not in df.columns:
        sys.exit("ERRO: relatório não tem coluna 'chave'.")
    for c in COLUNAS_RELATORIO:
        if c not in df.columns:
            df[c] = ""
    return df.set_index("chave", drop=False)


def aplicar_achados(df: pd.DataFrame, achados: list, saida_pdfs: Path) -> dict:
    """Retorna contadores {atualizadas, notas_adicionadas, nao_manuscrito, ignoradas}."""
    contadores = {"atualizadas": 0, "notas_adicionadas": 0, "nao_manuscrito": 0, "ignoradas": 0}

    for achado in achados:
        chave = str(achado.get("chave", "")).strip()
        if not chave:
            print("  ⚠ achado sem 'chave', ignorado.")
            continue
        if chave not in df.index:
            print(f"  ⚠ {chave}: não existe no relatório, ignorado.")
            contadores["ignoradas"] += 1
            continue

        status_atual = df.at[chave, "status"]
        if status_atual in STATUS_JA_RESOLVIDO:
            print(f"  ⏭  {chave}: já é status={status_atual!r}, não mexi (proteção contra "
                  "sobrescrever um achado já verificado).")
            contadores["ignoradas"] += 1
            continue

        motivo = str(achado.get("motivo", "") or "")

        if achado.get("nao_e_manuscrito"):
            df.at[chave, "status"] = "nao_e_manuscrito"
            df.at[chave, "motivo"] = motivo
            contadores["nao_manuscrito"] += 1
            print(f"  ○ {chave}: nao_e_manuscrito — {motivo[:80]}")
            continue

        if not achado.get("encontrado"):
            if motivo:
                df.at[chave, "motivo"] = motivo
                contadores["notas_adicionadas"] += 1
                print(f"  ·  {chave}: segue nao_encontrado, nota adicionada — {motivo[:80]}")
            continue

        arquivo = saida_pdfs / f"{chave}.pdf"
        if not arquivo.exists():
            print(f"  ⚠ {chave}: achado marcado encontrado=true mas {arquivo} não existe "
                  "no disco — não marquei ok (o agente disse que baixou, mas o arquivo não "
                  "está lá; confira antes de tentar de novo).")
            contadores["ignoradas"] += 1
            continue

        df.at[chave, "status"] = "ok"
        df.at[chave, "fonte"] = str(achado.get("fonte") or FONTE_PADRAO)
        df.at[chave, "url"] = str(achado.get("url", ""))
        df.at[chave, "versao"] = str(achado.get("versao", ""))
        df.at[chave, "motivo"] = motivo
        df.at[chave, "arquivo"] = str(arquivo)
        contadores["atualizadas"] += 1
        print(f"  [ok] {chave}: {df.at[chave, 'fonte']}"
              + (f" (versao=preprint)" if df.at[chave, "versao"] == "preprint" else ""))

    return contadores


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--relatorio", required=True)
    p.add_argument("--achados", required=True, help="arquivo JSON com a lista de achados")
    p.add_argument("--saida-pdfs", required=True, help="pasta onde os PDFs já foram salvos")
    args = p.parse_args(argv)

    relatorio_path = Path(args.relatorio)
    saida_pdfs = Path(args.saida_pdfs)

    df = carregar_relatorio(relatorio_path)
    achados = json.loads(Path(args.achados).read_text(encoding="utf-8"))
    if not isinstance(achados, list):
        sys.exit("ERRO: --achados deve ser uma lista JSON de objetos.")

    contadores = aplicar_achados(df, achados, saida_pdfs)

    df[COLUNAS_RELATORIO].to_csv(relatorio_path, index=False, encoding="utf-8-sig")

    print()
    print(f"Atualizadas para ok: {contadores['atualizadas']}")
    print(f"Notas adicionadas (seguem nao_encontrado): {contadores['notas_adicionadas']}")
    print(f"Marcadas nao_e_manuscrito: {contadores['nao_manuscrito']}")
    print(f"Ignoradas (já resolvidas, chave desconhecida, ou arquivo ausente): {contadores['ignoradas']}")
    print(f"\nRelatório atualizado: {relatorio_path}")


if __name__ == "__main__":
    main()
