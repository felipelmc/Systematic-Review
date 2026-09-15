"""As skills versionadas em `skills/` e as instaladas em `~/.claude/skills` devem ser idênticas.

Por que existe: o repositório guarda cópias independentes das skills, e a regra do projeto
(CLAUDE.md) é aplicar toda modificação nos dois lugares. Este teste acusa a divergência
arquivo a arquivo (sha256), ignorando caches e metadados do sistema. Sem a pasta instalada
(ex.: outra máquina ou CI), o teste é pulado. `RS_INSTALADAS_DIR` troca o diretório.
"""

import hashlib
import os
from pathlib import Path

import pytest

from conftest import RAIZ_REPO

DIR_REPO = RAIZ_REPO / "skills"
DIR_INSTALADAS = Path(os.environ.get("RS_INSTALADAS_DIR") or Path.home() / ".claude" / "skills")
SKILLS = sorted(p.name for p in DIR_REPO.iterdir() if (p / "SKILL.md").exists())
IGNORAR = {"__pycache__", ".DS_Store", ".pytest_cache"}


def _arquivos(raiz):
    saida = {}
    for arq in raiz.rglob("*"):
        if arq.is_file() and not (set(arq.relative_to(raiz).parts) & IGNORAR) and not arq.suffix == ".pyc":
            saida[str(arq.relative_to(raiz))] = hashlib.sha256(arq.read_bytes()).hexdigest()
    return saida


@pytest.mark.parametrize("skill", SKILLS)
def test_skill_instalada_igual_a_versionada(skill):
    instalada = DIR_INSTALADAS / skill
    if not instalada.exists():
        pytest.skip(f"{instalada} não existe nesta máquina")
    assert not instalada.is_symlink(), f"{instalada} deve ser cópia real, não link (regra do CLAUDE.md)"
    repo, inst = _arquivos(DIR_REPO / skill), _arquivos(instalada)
    so_repo = sorted(set(repo) - set(inst))
    so_inst = sorted(set(inst) - set(repo))
    diferentes = sorted(k for k in set(repo) & set(inst) if repo[k] != inst[k])
    assert not (so_repo or so_inst or diferentes), (
        f"{skill}: só no repositório {so_repo[:10]}; só instalada {so_inst[:10]}; diferentes {diferentes[:10]}. "
        f"Sincronize: rsync -a --delete --exclude __pycache__ --exclude .DS_Store skills/{skill}/ ~/.claude/skills/{skill}/"
    )
