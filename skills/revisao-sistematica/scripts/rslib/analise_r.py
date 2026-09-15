"""Comandos Python que rodam os scripts R da síntese quantitativa e registram o que produziram.

USO
    python3 rs.py analise efeitos    [--in 05-decomposicao/efeitos_extraidos.csv] [--out 06-analise/efeitos.csv]
                                     [--delta 0.1]
    python3 rs.py analise meta       [--in 06-analise/efeitos.csv] [--out-dir 06-analise]
                                     [--grupo construto_outcome] [--moderadores x,y] [--k-min 3]
                                     [--dependencia um_por_estudo|che] [--rho 0.6] [--delta 0.1]
                                     [--separar-desenho sim|nao] [--excluir-rob nenhum|critico]
    python3 rs.py analise swim       [--in 06-analise/efeitos.csv] [--out-dir 06-analise] [--grupo ...]
                                     [--limiar-consistencia 0.7] [--nivel 0.95] [--separar-desenho sim|nao]
                                     [--excluir-rob nenhum|critico]
    python3 rs.py analise combinados [--in 06-analise/efeitos.csv] [--out-dir 06-analise] [--grupo ...]
                                     [--separar-desenho sim|nao] [--excluir-rob nenhum|critico]
    Qualquer outro argumento do script R: --r-arg=--nome=valor (repetível).

O que faz
    Chama `Rscript scripts/R/<script>.R --chave=valor ...` com a raiz do projeto como
    diretório de trabalho (os caminhos gravados nos JSONs do R ficam relativos à raiz),
    repassa o stdout do R (a ressalva dos testes combinados, por exemplo) e devolve o
    código de saída do próprio R: 0 ok; 1 erro de dados; 2 checagem metodológica (ex.:
    estudo com vários efeitos sem modelo principal); 3 dependência ausente.
    Em `analise efeitos`, avisa se `verificar-efeitos` ainda não rodou ou deixou linhas não aptas ao G7; em
    projeto parcial sem PDFs, avisa em vez disso que os números não foram verificados contra os PDFs (declarar
    no relato), sem sugerir `verificar-efeitos`.
    Quando o R grava saídas (código 0 ou 2), registra `analise_executada` com a entrada
    e os artefatos gerados (efeitos.csv, meta_resumo.json, tabelas e figuras), para
    que PRISMA, caixa e declaração de IA remetam a arquivos com hash no log.

Por que um wrapper e não chamar o Rscript direto
    Os scripts R não escrevem no estado do projeto (só o Python escreve em rs_log.jsonl,
    ver scripts/R/_cli.R). Sem este comando a síntese ficaria fora do ledger. Os padrões
    de caminho vêm de esquema.py (ARQ_EFEITOS_EXTRAIDOS → ARQ_EFEITOS_CALCULADOS;
    ARQ_META_RESUMO; ARQ_SWIM_RESUMO), os mesmos que `rs.py caixa` lê.

Dependências
    Sem Rscript no PATH (ou com RS_RSCRIPT apontando para um executável inexistente)
    sai com 3 e a instrução de instalação. Pacote R ausente (metafor, clubSandwich,
    jsonlite) é detectado pelo próprio script R, que sai com 3; aqui o resumo ganha o
    comando install.packages correspondente. Sem R a skill degrada: sem síntese
    quantitativa, mas síntese qualitativa, caixa (com certeza.csv) e PRISMA seguem.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import esquema, estado
from .handoff import exigir_raiz, falhar, ler_linhas, relativo, resolver_caminho, sim
from .triagem_lotes import subparsers_do_comando

ATOR = "rs.py analise"
ETAPA = "10_sintese"
DIR_R = Path(__file__).resolve().parents[1] / "R"
TIMEOUT_R = 3600
ARQ_TESTES_COMBINADOS = "06-analise/testes_combinados.json"

# nome do subcomando -> (script, entrada padrão, opções {flag: (dest, ajuda)}, pacotes exigidos)
COMANDOS = {
    "efeitos": ("efeitos.R", esquema.ARQ_EFEITOS_EXTRAIDOS, ["jsonlite"]),
    "meta": ("meta.R", esquema.ARQ_EFEITOS_CALCULADOS, ["jsonlite", "metafor"]),
    "swim": ("swim.R", esquema.ARQ_EFEITOS_CALCULADOS, ["jsonlite"]),
    "combinados": ("testes_combinados.R", esquema.ARQ_EFEITOS_CALCULADOS, ["jsonlite"]),
}
OPCAO_EXCLUIR_ROB = ("--excluir-rob", "critico tira rob_geral crítico da análise principal (vai para sensibilidade); "
                                      "padrão do R: nenhum")
OPCOES_GRUPO = [
    ("--grupo", "colunas de agrupamento separadas por vírgula (padrão do R: construto_outcome)"),
    ("--separar-desenho", "sim (padrão do R) separa randomizados e não randomizados; nao agrega juntos"),
]
OPCOES = {
    "efeitos": [("--delta", "SESOI só descritivo (padrão do R: 0.1)")],
    "meta": OPCOES_GRUPO + [
        ("--moderadores", "moderadores separados por vírgula"),
        ("--k-min", "k mínimo de estudos para agregar (padrão 3)"),
        ("--dependencia", "um_por_estudo (padrão) ou che"),
        ("--rho", "correlação suposta no CHE (padrão 0.6)"),
        ("--delta", "δ/SESOI fixado no protocolo (sem ele, equivalência fica nula)"),
        OPCAO_EXCLUIR_ROB,
    ],
    "swim": OPCOES_GRUPO + [
        ("--limiar-consistencia", "fração para a direção de estudos com vários efeitos (padrão 0.7)"),
        ("--nivel", "nível do IC da proporção benéfica (padrão 0.95)"),
        OPCAO_EXCLUIR_ROB,
    ],
    "combinados": OPCOES_GRUPO + [OPCAO_EXCLUIR_ROB],
}
INSTRUCAO_R = ("instale o R (https://cran.r-project.org) e os pacotes: "
               "Rscript -e 'install.packages(c(\"jsonlite\", \"metafor\", \"clubSandwich\", \"meta\", \"esc\"))'. "
               "Sem R: sem síntese quantitativa (quali, caixa com certeza.csv e PRISMA seguem).")


def localizar_rscript():
    """Caminho do Rscript ou None. RS_RSCRIPT tem precedência (instalações fora do PATH e testes)."""
    indicado = os.environ.get("RS_RSCRIPT")
    if indicado:
        caminho = shutil.which(indicado) or (indicado if Path(indicado).is_file() else None)
        return caminho if caminho and os.access(caminho, os.X_OK) else None
    return shutil.which("Rscript")


def _ultima_linha_json(texto):
    for linha in reversed([l for l in (texto or "").splitlines() if l.strip()]):
        try:
            valor = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if isinstance(valor, dict):
            return valor
    return None


def _caminho_para_r(raiz, valor):
    """Caminho passado ao R: relativo à raiz quando o arquivo está no projeto (o R roda com cwd = raiz)."""
    p = resolver_caminho(raiz, valor)
    rel = relativo(raiz, p)
    return rel if not Path(rel).is_absolute() else str(p)


def _artefatos(raiz, resumo_r, entrada):
    """Arquivos citados no resumo do R que existem, relativos à raiz (sem repetição, entrada primeiro)."""
    candidatos = [entrada]
    for chave in ("saida", "resumo_json", "tabela", "tabela_estudos"):
        valor = resumo_r.get(chave)
        if isinstance(valor, str) and valor:
            candidatos.append(valor)
    figuras = resumo_r.get("figuras") or []
    candidatos += [f for f in (figuras if isinstance(figuras, list) else [figuras]) if isinstance(f, str)]
    saida = []
    for c in candidatos:
        p = Path(c) if Path(c).is_absolute() else Path(raiz) / c
        rel = relativo(raiz, p)
        if p.is_file() and rel not in saida:
            saida.append(rel)
    return saida


def _pacotes_ausentes(resumo_r, pacotes_exigidos):
    ausentes = (resumo_r or {}).get("pacotes_ausentes")
    if isinstance(ausentes, list) and ausentes:
        return [str(p) for p in ausentes]
    erro = str((resumo_r or {}).get("erro") or "")
    achados = [p for p in pacotes_exigidos + ["clubSandwich"] if p in erro]
    return achados or list(pacotes_exigidos)


def _avisos_verificacao(raiz, nome, entrada=None):
    """Aviso (não bloqueio) quando a síntese roda antes de os efeitos estarem aptos ao G7.

    Em projeto parcial sem PDFs (efeitos_verificar.projeto_parcial_sem_pdfs) o aviso não manda rodar
    `verificar-efeitos`: diz que os números não foram verificados contra PDFs e que isso vai para o relato.
    """
    if nome != "efeitos":
        return []
    from .efeitos_verificar import aviso_sem_pdfs, projeto_parcial_sem_pdfs  # import tardio (pymupdf opcional)

    if projeto_parcial_sem_pdfs(raiz):
        caminho = Path(entrada) if entrada and Path(entrada).is_absolute() else Path(raiz) / (
            entrada or esquema.ARQ_EFEITOS_EXTRAIDOS)
        return [aviso_sem_pdfs(ler_linhas(caminho))]
    linhas = ler_linhas(Path(raiz) / esquema.ARQ_VERIFICACAO_EFEITOS)
    if not linhas:
        return ["analise verificar-efeitos ainda não rodou: números não conferidos na página do PDF (G7)"]
    nao_aptos = [l.get("id_efeito", "") for l in linhas if not sim(l.get("apto_g7"))]
    if nao_aptos:
        return [f"{len(nao_aptos)} efeitos não aptos ao G7 em {esquema.ARQ_VERIFICACAO_EFEITOS}: "
                "a síntese é rascunho até a verificação humana"]
    return []


def executar_r(args):
    nome = args.acao_r
    comando = f"analise {nome}"
    script, entrada_padrao, pacotes = COMANDOS[nome]
    raiz = exigir_raiz(args, comando)
    if raiz is None:
        return 1
    rscript = localizar_rscript()
    if rscript is None:
        return falhar(comando, "Rscript não encontrado no PATH (ou RS_RSCRIPT inválido)", codigo=3,
                      instrucao=INSTRUCAO_R)
    arquivo_script = DIR_R / script
    if not arquivo_script.is_file():
        return falhar(comando, f"script R ausente na skill: {arquivo_script}", codigo=3)

    entrada = _caminho_para_r(raiz, args.entrada or entrada_padrao)
    if not (Path(entrada) if Path(entrada).is_absolute() else raiz / entrada).is_file():
        dica = "rode `analise preparar-efeitos`" if nome == "efeitos" else "rode `analise efeitos`"
        return falhar(comando, f"entrada não encontrada: {entrada} ({dica})")
    argv = [rscript, "--vanilla", str(arquivo_script), f"--in={entrada}"]
    if nome == "efeitos":
        saida = _caminho_para_r(raiz, args.saida or esquema.ARQ_EFEITOS_CALCULADOS)
        argv.append(f"--out={saida}")
    else:
        saida = _caminho_para_r(raiz, args.out_dir or str(Path(esquema.ARQ_META_RESUMO).parent))
        argv.append(f"--out-dir={saida}")
    for flag, _ in OPCOES[nome]:
        valor = getattr(args, flag.lstrip("-").replace("-", "_"))
        if valor is not None:
            argv.append(f"{flag}={valor}")
    for extra in args.r_arg or []:
        if not extra.startswith("--"):
            return falhar(comando, f"--r-arg deve ter a forma --nome=valor (recebido {extra!r})")
        argv.append(extra)

    try:
        proc = subprocess.run(argv, cwd=str(raiz), capture_output=True, text=True, timeout=TIMEOUT_R)
    except subprocess.TimeoutExpired:
        return falhar(comando, f"{script} passou de {TIMEOUT_R} s", codigo=1)
    except OSError as e:
        return falhar(comando, f"não consegui executar o Rscript: {e}", codigo=3, instrucao=INSTRUCAO_R)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    linhas_stdout = [l for l in proc.stdout.splitlines() if l.strip()]
    resumo_r = _ultima_linha_json(proc.stdout)
    for linha in linhas_stdout[:-1] if resumo_r is not None else linhas_stdout:
        print(linha)  # ressalvas e mensagens do R ficam antes do resumo JSON deste comando
    codigo = proc.returncode

    if resumo_r is None:
        return falhar(comando, f"{script} terminou sem resumo JSON (código {codigo}); ver stderr",
                      codigo=codigo if codigo in (1, 2, 3) else 1, codigo_r=codigo)
    if codigo == 3:
        ausentes = _pacotes_ausentes(resumo_r, pacotes)
        instrucao = "Rscript -e 'install.packages(c(" + ", ".join(f'"{p}"' for p in ausentes) + "))'"
        return falhar(comando, resumo_r.get("erro") or "dependência R ausente", codigo=3, codigo_r=codigo,
                      pacotes_ausentes=ausentes, instrucao=instrucao)

    artefatos = _artefatos(raiz, resumo_r, entrada) if codigo in (0, 2) else []
    avisos = _avisos_verificacao(raiz, nome, entrada)
    if codigo in (0, 2):
        anterior = next((e for e in reversed(estado.ler_log(raiz)) if e.get("evento") == "analise_executada"
                         and (e.get("dados") or {}).get("script") == script), None)
        sha_entrada = estado.sha256_arquivo(Path(entrada) if Path(entrada).is_absolute() else raiz / entrada)
        reexecucao = bool(anterior) and (anterior["dados"].get("argumentos") == argv[3:]
                                         and anterior["dados"].get("sha_entrada") == sha_entrada)
        resumo_log = {k: v for k, v in resumo_r.items() if k not in ("figuras", "ressalva")}
        estado.registrar_evento(
            raiz, "analise_executada", ETAPA, "script", ATOR,
            dados={"comando": comando, "script": script, "argumentos": argv[3:], "codigo_saida": codigo,
                   "sha_entrada": sha_entrada, "reexecucao": reexecucao, "resumo_r": resumo_log},
            artefatos=artefatos)
    proximo = {"efeitos": "rs.py analise meta (ou analise swim sem meta-análise)",
               "meta": "rs.py analise swim; certeza.csv (GRADE) e rs.py caixa",
               "swim": "certeza.csv (GRADE) e rs.py caixa",
               "combinados": "análise secundária: nunca define rótulos da caixa"}[nome]
    estado.resumo({"comando": comando, "ok": codigo == 0, "codigo_r": codigo, "script": script,
                   "entrada": entrada, "arquivos": artefatos[1:] if artefatos else [], "resumo_r": resumo_r,
                   "avisos": avisos, "proximo_passo": proximo if codigo == 0 else resumo_r.get("erro")})
    return codigo


def registrar(subparsers):
    """Acrescenta efeitos/meta/swim/combinados ao comando `analise` criado por efeitos_verificar."""
    sub = subparsers_do_comando(subparsers, "analise",
                                "dados de efeito e síntese: preparar-efeitos, verificar-efeitos, efeitos, meta, swim, "
                                "combinados")
    ajudas = {
        "efeitos": "efeitos.R: estatísticas extraídas -> g de Hedges alinhado (06-analise/efeitos.csv)",
        "meta": "meta.R: meta-análise REML + HKSJ por grupo comparável (06-analise/meta_resumo.json)",
        "swim": "swim.R: SWiM, teste de sinal por direção e gráficos (06-analise/swim_resumo.json)",
        "combinados": "testes_combinados.R: Stouffer, Winer, Cooper e Fisher (secundários, com ressalva)",
    }
    for nome, (script, entrada_padrao, _) in COMANDOS.items():
        p = sub.add_parser(nome, help=ajudas[nome], description=ajudas[nome])
        p.add_argument("--in", dest="entrada", default=None, help=f"CSV de entrada (padrão {entrada_padrao})")
        if nome == "efeitos":
            p.add_argument("--out", dest="saida", default=None,
                           help=f"CSV de saída (padrão {esquema.ARQ_EFEITOS_CALCULADOS})")
        else:
            p.add_argument("--out-dir", default=None, help="pasta de saída (padrão 06-analise)")
        for flag, ajuda in OPCOES[nome]:
            p.add_argument(flag, default=None, help=ajuda)
        p.add_argument("--r-arg", action="append", default=None, metavar="--NOME=VALOR",
                       help="argumento extra repassado ao script R (repetível)")
        p.set_defaults(func=executar_r, acao_r=nome)
