"""Configuração comum do pytest: coloca scripts/ no sys.path e oferece um projeto vazio."""

import json
import sys
from pathlib import Path

import pytest

def _achar_raiz_repo():
    """Sobe diretórios até achar skills/revisao-sistematica (o repo guarda testes em dev/revisao-sistematica/)."""
    for pasta in Path(__file__).resolve().parents:
        if (pasta / "skills" / "revisao-sistematica" / "SKILL.md").exists():
            return pasta
    raise RuntimeError("skills/revisao-sistematica não encontrada acima de " + str(Path(__file__).resolve()))


RAIZ_REPO = _achar_raiz_repo()
DIR_TESTES = Path(__file__).resolve().parent
SKILL = RAIZ_REPO / "skills" / "revisao-sistematica"
SCRIPTS = SKILL / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(SCRIPTS))


def pytest_configure(config):
    config.addinivalue_line("markers", "osf: testes com as exportações reais do repositório OSF do MAPE/IESP-UERJ; exigem RS_OSF_DIR")
    config.addinivalue_line("markers", "e2e: fluxo completo pelo dispatcher real (tests/e2e), sem rede; roda por padrão")


@pytest.fixture
def projeto_vazio(tmp_path):
    """Projeto recém-criado (estado inicial + pastas), sem usar o comando init."""
    from rslib import esquema, estado

    for pasta in esquema.PASTAS_PROJETO:
        (tmp_path / pasta).mkdir(parents=True, exist_ok=True)
    estado.salvar_estado(tmp_path, estado.estado_inicial("Projeto de teste"))
    estado.registrar_evento(tmp_path, "projeto_criado", "00_configuracao", "script", "teste")
    return tmp_path


@pytest.fixture
def fixtures_dir():
    return FIXTURES


def ler_jsonl(caminho):
    with open(caminho, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]
