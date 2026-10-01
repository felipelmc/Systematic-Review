"""Diagnóstico do ambiente: Python, pacotes, R, Quarto, chaves de API e skills irmãs.

USO
    python3 rs.py ambiente            # imprime o diagnóstico; com projeto, grava em estado["ambiente"]
    python3 rs.py ambiente --sem-r    # pula a checagem do R (mais rápida)

Por que existe
    A skill é híbrida (Python + R) e degrada de forma prevista quando falta algo
    (references/00-configuracao-estado.md, seção 8): sem rapidfuzz o dedup usa difflib; sem metafor não há
    meta-análise, mas SWiM, caixa e PRISMA seguem; sem R não há síntese quantitativa.
    Saber isso no começo evita descobrir no meio da síntese que o caminho não existe.

Decisões
    - Pacotes Python são checados com importlib.util.find_spec (não importa nada pesado).
    - Chaves de API entram no estado só como booleanos: o valor nunca é lido para além de
      "está definida?" e nunca é gravado. `.env` não é lido.
    - Skills irmãs são procuradas nesta ordem:
      ${CLAUDE_SKILL_DIR}/../<nome> → ~/.claude/skills/<nome> → ${CLAUDE_PROJECT_DIR}/.claude/skills/<nome>.
      Guardamos o rótulo do local, não só o caminho, para o estado não depender da máquina.
    - Chamadas externas (Rscript, quarto) têm timeout e nunca derrubam o comando.
    - Gravar no estado passa pela trava do projeto (estado.registrar_evento); estado corrompido sai com
      código 1 e a dica de restauração, sem traceback.
"""

import importlib.metadata
import importlib.util
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import estado

PACOTES_OBRIGATORIOS = {  # nome de distribuição -> nome de import
    "pandas": "pandas", "openpyxl": "openpyxl", "xlrd": "xlrd", "requests": "requests", "pymupdf": "fitz",
}
PACOTES_OPCIONAIS = {
    "rapidfuzz": ("rapidfuzz", "dedup fuzzy cai para difflib (mais lento)"),
    "pyalex": ("pyalex", "busca OpenAlex usa requests direto"),
    "anthropic": ("anthropic", "sem modo de triagem via API da Anthropic (subagentes seguem)"),
    "openai": ("openai", "sem modo de triagem via API da OpenAI (subagentes seguem)"),
    "jsonschema": ("jsonschema", "validação de schemas usa o validador manual"),
    "bibtexparser": ("bibtexparser", "importação BibTeX usa o mini-parser"),
    "rispy": ("rispy", "importação RIS usa o mini-parser"),
}
PACOTES_R = {
    "meta": "meta-análise (forest/funil) indisponível",
    "metafor": "sem meta-análise; SWiM, testes combinados e caixa seguem",
    "esc": "conversões de efeito dependem só das fórmulas próprias",
    "irr": "concordância em R indisponível (Python cobre κ)",
    "clubSandwich": "sem RVE/CR2 para efeitos dependentes",
    "robvis": "sem gráficos de risco de viés",
    "jsonlite": "scripts R não conseguem imprimir o resumo JSON",
}
VARIAVEIS_CHAVES = ["RS_EMAIL", "OPENALEX_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
SKILLS_IRMAS = {
    "baixar-pdfs-academicos": "sem download em cascata: usar checklist manual de PDFs",
    "fichamento-sistematico": "sem fichamento em lote: usar protocolo mínimo de extração inline",
    "gerar-bibtex": "usar `rs.py bib` (bib mínimo com chave)",
}
PY_MINIMO = (3, 10)


def _versao_distribuicao(nome):
    try:
        return importlib.metadata.version(nome)
    except importlib.metadata.PackageNotFoundError:
        return None


def verificar_python():
    obrigatorios, opcionais, faltando, faltando_opc = {}, {}, [], []
    for dist, mod in PACOTES_OBRIGATORIOS.items():
        presente = importlib.util.find_spec(mod) is not None
        obrigatorios[dist] = _versao_distribuicao(dist) or ("presente" if presente else None)
        if not presente:
            faltando.append(dist)
    for dist, (mod, efeito) in PACOTES_OPCIONAIS.items():
        presente = importlib.util.find_spec(mod) is not None
        opcionais[dist] = _versao_distribuicao(dist) or ("presente" if presente else None)
        if not presente:
            faltando_opc.append({"pacote": dist, "efeito": efeito})
    return {
        "versao": platform.python_version(),
        "ok": sys.version_info[:2] >= PY_MINIMO,
        "pacotes_obrigatorios": obrigatorios,
        "pacotes_opcionais": opcionais,
        "faltando_obrigatorios": faltando,
        "faltando_opcionais": faltando_opc,
    }


def _rodar(cmd, timeout):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)


def verificar_r(timeout=60):
    rscript = shutil.which("Rscript")
    if not rscript:
        return {"disponivel": False, "versao": None, "pacotes": {}, "faltando": list(PACOTES_R),
                "efeito": "sem R: sem síntese quantitativa (quali, caixa e PRISMA seguem)"}
    codigo, saida = _rodar([rscript, "--version"], timeout=20)
    m = re.search(r"version (\d+\.\d+\.\d+)", saida or "")
    versao = m.group(1) if m else None
    lista = ", ".join(f'"{p}"' for p in PACOTES_R)
    expr = (f"for (p in c({lista})) cat(p, '=', if (requireNamespace(p, quietly = TRUE)) "
            "as.character(utils::packageVersion(p)) else '', '\\n', sep = '')")
    codigo, saida = _rodar([rscript, "--vanilla", "-e", expr], timeout=timeout)
    pacotes = {}
    for linha in (saida or "").splitlines():
        if "=" in linha:
            nome, _, ver = linha.partition("=")
            if nome.strip() in PACOTES_R:
                pacotes[nome.strip()] = ver.strip() or None
    if codigo != 0 and not pacotes:
        return {"disponivel": True, "versao": versao, "pacotes": {}, "faltando": list(PACOTES_R),
                "erro": "não consegui listar os pacotes R", "efeito": None}
    faltando = [p for p in PACOTES_R if not pacotes.get(p)]
    return {"disponivel": True, "versao": versao, "pacotes": pacotes, "faltando": faltando,
            "efeitos_faltando": {p: PACOTES_R[p] for p in faltando}}


def verificar_quarto():
    quarto = shutil.which("quarto")
    if not quarto:
        return {"disponivel": False, "versao": None}
    codigo, saida = _rodar([quarto, "--version"], timeout=20)
    return {"disponivel": codigo == 0, "versao": (saida or "").strip().splitlines()[0] if codigo == 0 and saida else None}


def verificar_chaves():
    """Só booleanos: nunca ler, imprimir ou gravar o valor de uma credencial."""
    return {nome: bool(os.environ.get(nome, "").strip()) for nome in VARIAVEIS_CHAVES}


def dir_skill():
    """Pasta da skill: ${CLAUDE_SKILL_DIR} se definida; senão deduzida deste arquivo."""
    env = os.environ.get("CLAUDE_SKILL_DIR")
    return Path(env) if env else Path(__file__).resolve().parents[2]


def locais_irmas(nome):
    locais = [("skill_dir_vizinha", dir_skill().parent / nome),
              ("usuario", Path.home() / ".claude" / "skills" / nome)]
    projeto = os.environ.get("CLAUDE_PROJECT_DIR")
    if projeto:
        locais.append(("projeto", Path(projeto) / ".claude" / "skills" / nome))
    return locais


def verificar_irmas():
    resultado = {}
    for nome, fallback in SKILLS_IRMAS.items():
        achada = None
        for rotulo, caminho in locais_irmas(nome):
            if (caminho / "SKILL.md").is_file():
                # "~" no lugar da home: o estado pode ir para um pacote público de dados/código.
                achada = {"instalada": True, "local": rotulo,
                          "caminho": str(caminho).replace(str(Path.home()), "~", 1)}
                break
        resultado[nome] = achada or {"instalada": False, "local": None, "caminho": None, "fallback": fallback}
    return resultado


def verificar(incluir_r=True):
    """Diagnóstico completo (dict serializável)."""
    py = verificar_python()
    r = verificar_r() if incluir_r else {"disponivel": None, "pulado": True}
    diag = {
        "verificado_em": estado.agora(),
        "sistema": platform.system(),
        "python": py,
        "r": r,
        "quarto": verificar_quarto(),
        "chaves_api": verificar_chaves(),
        "skills_irmas": verificar_irmas(),
    }
    diag["resumo"] = {
        "python_ok": py["ok"] and not py["faltando_obrigatorios"],
        "faltando_python": py["faltando_obrigatorios"],
        "faltando_python_opcional": [f["pacote"] for f in py["faltando_opcionais"]],
        "r_disponivel": r.get("disponivel"),
        "faltando_r": r.get("faltando", []),
        "quarto": diag["quarto"]["disponivel"],
        "irmas_ausentes": [n for n, v in diag["skills_irmas"].items() if not v["instalada"]],
        "modo_api_possivel": bool(py["pacotes_opcionais"].get("anthropic") or py["pacotes_opcionais"].get("openai"))
        and (diag["chaves_api"]["ANTHROPIC_API_KEY"] or diag["chaves_api"]["OPENAI_API_KEY"]),
    }
    return diag


def instrucoes(diag):
    """Comandos sugeridos para instalar o que falta (mostrados, nunca executados)."""
    cmds = []
    res = diag["resumo"]
    faltam_py = res["faltando_python"] + res["faltando_python_opcional"]
    if faltam_py:
        cmds.append("python3 -m pip install " + " ".join(faltam_py))
    if res["faltando_r"] and diag["r"].get("disponivel"):
        cmds.append("Rscript -e 'install.packages(c(" + ", ".join(f'\"{p}\"' for p in res["faltando_r"]) + "))'")
    return cmds


def gravar_no_estado(raiz, diag, estado_projeto=None):
    """Grava o diagnóstico em estado["ambiente"] e registra `ambiente_verificado`."""
    est = estado_projeto if estado_projeto is not None else estado.carregar_estado(raiz)
    est["ambiente"] = diag
    return estado.registrar_evento(raiz, "ambiente_verificado", "00_configuracao", "script", "ambiente",
                                   dados={"resumo": diag["resumo"]}, estado=est)


def comando(args):
    diag = verificar(incluir_r=not args.sem_r)
    raiz = estado.encontrar_projeto(args.dir)
    if raiz:
        try:
            gravar_no_estado(raiz, diag)
        except estado.ErroProjeto as e:
            print(f"erro: {e}", file=sys.stderr)
            estado.resumo({"ok": False, "erro": "estado_invalido", "detalhe": str(e)})
            return 1
    res = diag["resumo"]
    for aviso in diag["python"]["faltando_opcionais"]:
        print(f"opcional ausente: {aviso['pacote']} — {aviso['efeito']}")
    for nome, v in diag["skills_irmas"].items():
        if not v["instalada"]:
            print(f"skill irmã ausente: {nome} — {v['fallback']}")
    estado.resumo({"ok": res["python_ok"], "gravado_no_projeto": bool(raiz), **res,
                   "chaves_api": diag["chaves_api"], "instalar": instrucoes(diag)})
    return 0 if res["python_ok"] else 3


def registrar(subparsers):
    """Registrado por rslib.projeto (o dispatcher só importa projeto)."""
    p = subparsers.add_parser("ambiente", help="verifica Python, pacotes, R, Quarto, chaves (booleanos) e skills irmãs",
                              description="Diagnóstico do ambiente; com projeto, grava em rs_estado.json.")
    p.add_argument("--sem-r", action="store_true", help="não checar R e pacotes R")
    p.set_defaults(func=comando)
