#!/usr/bin/env bash
# Roda o teste ponta a ponta da skill revisao-sistematica (sem rede, sem API).
#   dev/revisao-sistematica/tests/e2e/rodar.sh              # os três cenários
#   dev/revisao-sistematica/tests/e2e/rodar.sh -k autopiloto
# Partes em R são puladas sem Rscript/metafor. Argumentos extras vão para o pytest.
set -euo pipefail
DIR_E2E="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ_REPO="$(cd "$DIR_E2E/../../../.." && pwd)"
cd "$RAIZ_REPO"
export PYTHONDONTWRITEBYTECODE=1
exec python3 -m pytest -p no:cacheprovider -q "$DIR_E2E/test_fluxo_completo.py" "$@"
