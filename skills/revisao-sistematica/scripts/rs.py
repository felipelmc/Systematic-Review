#!/usr/bin/env python3
"""rs.py — dispatcher único da skill revisao-sistematica.

USO
    python3 "${CLAUDE_SKILL_DIR}/scripts/rs.py" <comando> [subcomando] [opções]
    python3 rs.py --help
    python3 rs.py status

Cada módulo em rslib/ que oferece comandos expõe `registrar(subparsers)`, que
adiciona seus subparsers e define `func` (recebe args, devolve código de saída).
Todo comando imprime um resumo JSON na última linha do stdout e registra um
evento em rs_log.jsonl quando altera o projeto.

Códigos de saída: 0 ok; 1 erro de uso/dados; 2 checagem metodológica falhou
(ex.: estudo-âncora excluído, invariante do PRISMA); 3 dependência ausente.
"""

import argparse
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Ordem de exibição no --help. Módulos ausentes são ignorados (a skill funciona parcialmente).
MODULOS_COMANDOS = [
    "rslib.projeto",         # init, status, ambiente, portao, pendencia
    "rslib.importar.cli",    # importar
    "rslib.busca_openalex",  # buscar openalex
    "rslib.dedup",           # dedup
    "rslib.filtrar",         # filtrar
    "rslib.triagem_lotes",   # triagem preparar|mesclar|consolidar
    "rslib.triagem_api",     # triagem api
    "rslib.validacao",       # validar amostrar|calcular|elusao
    "rslib.bola_de_neve",    # bola-de-neve
    "rslib.textos",          # textos para-baixar|inventario|elegibilidade
    "rslib.qualidade",       # qualidade consolidar (RoB: concordância, consenso, rob_geral)
    "rslib.efeitos_verificar",  # analise preparar-efeitos|verificar-efeitos
    "rslib.analise_r",       # analise efeitos|meta|swim|combinados (scripts R)
    "rslib.caixa",           # caixa
    "rslib.prisma",          # prisma
    "rslib.declaracao_ia",   # declaracao-ia
    "rslib.handoff",         # bib, incluidos
]


def construir_parser():
    parser = argparse.ArgumentParser(
        prog="rs.py",
        description="Revisão sistemática de ponta a ponta: estado auditável, busca, triagem, síntese e relato.",
    )
    parser.add_argument("--dir", default=None, help="raiz do projeto (padrão: procura rs_estado.json subindo diretórios)")
    sub = parser.add_subparsers(dest="comando", metavar="<comando>")
    carregados, ausentes = [], []
    for nome in MODULOS_COMANDOS:
        try:
            modulo = importlib.import_module(nome)
        except ModuleNotFoundError as e:
            if e.name and (e.name == nome or nome.startswith(e.name)):
                ausentes.append(nome)
                continue
            raise
        if hasattr(modulo, "registrar"):
            modulo.registrar(sub)
            carregados.append(nome)
    parser.set_defaults(_modulos_ausentes=ausentes)
    return parser


def main(argv=None):
    parser = construir_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
