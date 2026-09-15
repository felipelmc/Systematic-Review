"""Handoffs com as skills irmãs e utilitários de tabela do grupo de comandos B3.

USO
    python3 rs.py incluidos [--fonte auto|tc|ta]
    python3 rs.py bib [--fonte auto|tc|ta] [--out 07-relatorio/references.bib] [--sem-irma]

`incluidos` escreve `07-relatorio/incluidos.csv` (colunas `esquema.COLUNAS_INCLUIDOS`)
a partir das decisões finais: por padrão a elegibilidade em texto completo
(`03-textos/elegibilidade_tc_final.csv`); `--fonte ta` usa a triagem de título e
resumo, o que só faz sentido em projetos parciais ("só a triagem").

`bib` garante o `incluidos.csv` e entrega a planilha à skill irmã `gerar-bibtex`
(com `--col-chave chave`, para que a citekey seja a mesma dos PDFs e das fichas).
Se a irmã não estiver instalada ou falhar, escreve um `.bib` mínimo com a própria
`chave` como citekey. Em qualquer caminho, confere se as chaves do `.bib` batem com
as do `incluidos.csv` e avisa se não baterem.

Por que os utilitários de CSV moram aqui: todos os comandos do grupo B3 trocam
tabelas com outras etapas e com as irmãs; ler e escrever sempre do mesmo jeito
(UTF-8, vírgula, cabeçalho exato, escrita atômica) evita arquivos meio escritos
quando um comando é interrompido e diferenças de formato entre módulos.

Por que as pendências passam por `sincronizar_pendencia_unica` (ou `abrir_pendencia_unica` /
`fechar_se_resolvida`): rodar de novo um comando não pode empilhar pendências iguais, reabrir o
que um humano já resolveu sobre o mesmo arquivo nem deixar aberta uma pendência cuja condição
sumiu. O `n` muda por fechar-e-reabrir (o log guarda as duas versões). Todos os comandos que
abrem pendência por contagem usam estas funções: textos (conferencia_elegibilidade_tc,
retratacao_texto), analise verificar-efeitos (verificacao_humana_efeitos), caixa (certeza_caixa),
dedup (dedup_candidatos), triagem consolidar e validar (via triagem_lotes.sincronizar_pendencia).
A criação depende do modo (só autopiloto, salvo `qualquer_modo=True`); atualizar o `n` de uma
pendência já aberta e fechar a que perdeu a condição valem em qualquer modo, porque o projeto
pode ter passado do autopiloto para checkpoints com pendências abertas.

Por que a descoberta de irmãs segue uma ordem fixa: a skill pode rodar como pasta
solta, como plugin ou dentro de um projeto; a ordem
`${CLAUDE_SKILL_DIR}/../<nome>` → pasta vizinha desta skill → `~/.claude/skills/<nome>`
→ `${CLAUDE_PROJECT_DIR}/.claude/skills/<nome>` é a mesma de `rs.py ambiente` (references/00-configuracao-estado.md, seção 8).
"""

import csv
import io
import os
import re
import subprocess
import sys
from pathlib import Path

from . import esquema, estado, normalizar

DIR_SKILL = Path(__file__).resolve().parents[2]
DIR_ASSETS = DIR_SKILL / "assets"

ARQ_BIB = esquema.ARQ_BIB
ATOR = "rs.py handoff"


# ---------------------------------------------------------------------------
# Utilitários de tabela compartilhados
# ---------------------------------------------------------------------------
def ler_csv(caminho):
    """Lê um CSV UTF-8 (tolera BOM) e devolve (colunas, linhas como dicts de str)."""
    caminho = Path(caminho)
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)
        colunas = [c.strip() for c in (leitor.fieldnames or [])]
        linhas = []
        for linha in leitor:
            linhas.append({(k or "").strip(): ("" if v is None else str(v)) for k, v in linha.items()
                           if k is not None})
    return colunas, linhas


def ler_linhas(caminho):
    """Atalho: só as linhas de um CSV, ou [] se o arquivo não existir."""
    caminho = Path(caminho)
    if not caminho.exists():
        return []
    return ler_csv(caminho)[1]


def escrever_csv(caminho, colunas, linhas):
    """Escreve CSV com cabeçalho exato, de forma atômica (tmp + rename).

    Campos ausentes viram '' e campos extras são ignorados, para que um dict com
    colunas a mais nunca mude o cabeçalho contratado.
    """
    buffer = io.StringIO(newline="")
    escritor = csv.DictWriter(buffer, fieldnames=list(colunas), extrasaction="ignore", lineterminator="\n")
    escritor.writeheader()
    for linha in linhas:
        escritor.writerow({c: _celula(linha.get(c, "")) for c in colunas})
    # estado.escrever_atomico: tmp + os.replace com permissão 0666 menos a umask (mkstemp sozinho deixaria 0600).
    estado.escrever_atomico(caminho, buffer.getvalue(), newline="")


def escrever_texto(caminho, texto):
    """Escrita atômica de arquivo de texto (Markdown, BibTeX, JSONL), com a permissão padrão do estado."""
    estado.escrever_atomico(caminho, texto, newline="")


def _celula(valor):
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, float) and valor != valor:
        return ""
    return valor


def relativo(raiz, caminho):
    """Caminho relativo à raiz quando possível (é o que vai para o log e o estado)."""
    caminho = Path(caminho)
    try:
        return str(caminho.resolve().relative_to(Path(raiz).resolve()))
    except ValueError:
        return str(caminho)


def resolver_caminho(raiz, caminho):
    """Resolve um caminho dado na linha de comando: absoluto, relativo ao cwd ou à raiz."""
    p = Path(caminho)
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    return Path(raiz) / p


def indexar(linhas, campo):
    """Dict campo -> linha (a última vence), ignorando valores vazios."""
    return {linha[campo]: linha for linha in linhas if linha.get(campo, "").strip()}


def carregar_unicos(raiz):
    """registros_unicos.csv indexado por id_rs (dict vazio se ainda não houver dedup)."""
    return indexar(ler_linhas(Path(raiz) / esquema.ARQ_UNICOS), "id_rs")


def exigir_raiz(args, comando):
    """Resolve a raiz do projeto ou imprime o erro e o resumo; devolve Path ou None."""
    try:
        return estado.exigir_projeto(getattr(args, "dir", None))
    except estado.ErroProjeto as e:
        print(f"[erro] {e}", file=sys.stderr)
        estado.resumo({"comando": comando, "ok": False, "erro": str(e)})
        return None


def falhar(comando, mensagem, codigo=1, **extra):
    """Imprime erro no stderr e resumo JSON no stdout; devolve o código de saída."""
    print(f"[erro] {mensagem}", file=sys.stderr)
    estado.resumo({"comando": comando, "ok": False, "erro": mensagem, **extra})
    return codigo


def _mesma_pendencia(p, tipo, arquivo):
    return p.get("tipo") == tipo and (p.get("arquivo") or None) == (arquivo or None)


def _sha_na_abertura(eventos, pid, arquivo):
    """sha256 do `arquivo` gravado no evento pendencia_aberta de `pid` (None se não houver)."""
    for ev in eventos:
        if ev.get("evento") == "pendencia_aberta" and (ev.get("dados") or {}).get("pendencia") == pid:
            return next((a.get("sha256") or None for a in ev.get("artefatos") or [] if a.get("caminho") == arquivo), None)
    return None


def _ator_do_fechamento(eventos, pid):
    for ev in reversed(eventos):
        if ev.get("evento") == "pendencia_fechada" and (ev.get("dados") or {}).get("pendencia") == pid:
            return (ev.get("ator") or {}).get("tipo")
    return None


def ja_confirmada_por_humano(raiz, est, tipo, arquivo, n):
    """True se a última pendência (tipo, arquivo) foi fechada por humano, com o mesmo `n`, e o arquivo não mudou.

    É o que impede reabrir, a cada reexecução do comando, uma pendência que o humano já
    resolveu sobre exatamente o mesmo conteúdo (o sha256 do arquivo fica no evento de abertura).
    Sem `arquivo` não há como comparar conteúdo: devolve False (reabrir é o lado seguro).
    """
    if not arquivo:
        return False
    fechadas = [p for p in est.get("pendencias", []) if _mesma_pendencia(p, tipo, arquivo) and p.get("status") == "fechada"]
    if not fechadas or fechadas[-1].get("n") != n:
        return False
    eventos = estado.ler_log(raiz)
    if _ator_do_fechamento(eventos, fechadas[-1]["id"]) != "humano":
        return False
    sha = _sha_na_abertura(eventos, fechadas[-1]["id"], arquivo)
    caminho = Path(raiz) / arquivo
    return bool(sha) and caminho.is_file() and estado.sha256_arquivo(caminho) == sha


def abrir_pendencia_unica(raiz, tipo, etapa, descricao, portao=None, n=None, arquivo=None, ator_id=ATOR,
                          qualquer_modo=False):
    """Abre pendência (por padrão só no autopiloto) e mantém no máximo uma aberta por (tipo, arquivo).

    No modo checkpoints a necessidade de ação humana aparece no resumo e o
    coordenador para no portão; no autopiloto ela vira pendência (references/00-configuracao-estado.md, seção 5; RAISE).
    `qualquer_modo=True` abre também em checkpoints (fato externo, como retratação).

    - Já existe aberta com o mesmo `n` (ou `n` None): devolve o id existente, sem evento novo
      (em qualquer modo).
    - Já existe aberta com outro `n`: fecha a antiga (ator script, motivo com o n anterior e o novo)
      e abre outra com a descrição nova e " [substitui Pxxx]"; estado.py não atualiza pendência
      no lugar, e assim o log guarda as duas versões. Vale em qualquer modo: atualizar não é criar.
    - Duplicatas abertas do mesmo (tipo, arquivo), herdadas de versões antigas, são fechadas.
    - Nenhuma aberta, fora do autopiloto e sem `qualquer_modo`: não abre (None).
    - A última igual foi fechada por humano com o mesmo `n` e o arquivo não mudou: não reabre (None).

    Devolve o id da pendência aberta (nova ou existente) ou None.
    """
    est = estado.carregar_estado(raiz)
    abertas = [p for p in estado.pendencias_abertas(est) if _mesma_pendencia(p, tipo, arquivo)]
    if abertas:
        atual = abertas[0]
        for extra in abertas[1:]:
            estado.fechar_pendencia(raiz, extra["id"], f"duplicada de {atual['id']} (mesmo tipo e arquivo)",
                                    ator_tipo="script", ator_id=ator_id)
        if n is None or atual.get("n") == n:
            return atual["id"]
        estado.fechar_pendencia(raiz, atual["id"], f"atualizada automaticamente: n {atual.get('n')} -> {n}",
                                ator_tipo="script", ator_id=ator_id)
        descricao = f"{descricao} [substitui {atual['id']}]"
    elif not qualquer_modo and est.get("modo", {}).get("autonomia") != "autopiloto":
        return None
    elif ja_confirmada_por_humano(raiz, est, tipo, arquivo, n):
        return None
    return estado.abrir_pendencia(raiz, tipo, etapa, descricao, portao=portao, n=n, arquivo=arquivo,
                                  ator_id=ator_id)


def fechar_se_resolvida(raiz, tipo, arquivo=None, motivo=None, ator_id=ATOR, qualquer_arquivo=False):
    """Fecha (ator `script`) as pendências abertas de (tipo, arquivo) quando a condição que as abriu sumiu.

    O comando que abriu a pendência a chama ao ser reexecutado e encontrar zero itens pendentes
    (ex.: `apto_g7` em todas as linhas, nenhuma célula da caixa sem certeza). Só deve ser chamada
    quando a condição é verificável nos artefatos (marcas humanas já gravadas), nunca para
    "dar baixa" numa conferência que ninguém fez. Vale em qualquer modo, porque uma pendência
    aberta no autopiloto continua aberta se o projeto passar para checkpoints.
    Idempotente: sem pendência aberta, não registra nada. Devolve a lista de ids fechados.
    """
    est = estado.carregar_estado(raiz)
    fechadas = []
    for p in estado.pendencias_abertas(est):
        if p.get("tipo") != tipo or (not qualquer_arquivo and (p.get("arquivo") or None) != (arquivo or None)):
            continue
        if estado.fechar_pendencia(raiz, p["id"], motivo or "condição resolvida: nada pendente ao reexecutar o comando",
                                   ator_tipo="script", ator_id=ator_id):
            fechadas.append(p["id"])
    return fechadas


def sincronizar_pendencia_unica(raiz, tipo, etapa, descricao, n, portao=None, arquivo=None, ator_id=ATOR,
                                motivo_resolvida=None, qualquer_modo=False, qualquer_arquivo_ao_fechar=False):
    """Atalho para os comandos: n > 0 abre/atualiza (abrir_pendencia_unica); n == 0 fecha (fechar_se_resolvida).

    `qualquer_arquivo_ao_fechar=True` fecha as do mesmo tipo mesmo com outro `arquivo` (pendências
    herdadas de versões que gravavam outro caminho). Devolve o id da pendência aberta ou None.
    """
    if n:
        return abrir_pendencia_unica(raiz, tipo, etapa, descricao, portao=portao, n=n, arquivo=arquivo, ator_id=ator_id,
                                     qualquer_modo=qualquer_modo)
    fechar_se_resolvida(raiz, tipo, arquivo=arquivo, motivo=motivo_resolvida, ator_id=ator_id,
                        qualquer_arquivo=qualquer_arquivo_ao_fechar)
    return None


def sim(valor):
    """Interpreta marcações humanas de confirmação ('sim', '1', 'true', 'x', 'verificado')."""
    s = normalizar.ascii_fold(valor).lower().strip()
    return s in {"sim", "s", "1", "true", "yes", "y", "x", "verificado", "ok"}


# ---------------------------------------------------------------------------
# Descoberta das skills irmãs
# ---------------------------------------------------------------------------
def candidatos_skill_irma(nome):
    candidatos = []
    if os.environ.get("CLAUDE_SKILL_DIR"):
        candidatos.append(Path(os.environ["CLAUDE_SKILL_DIR"]).parent / nome)
    candidatos.append(DIR_SKILL.parent / nome)
    candidatos.append(Path.home() / ".claude" / "skills" / nome)
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        candidatos.append(Path(os.environ["CLAUDE_PROJECT_DIR"]) / ".claude" / "skills" / nome)
    return candidatos


def localizar_skill_irma(nome, arquivo_exigido=None):
    """Pasta da skill irmã `nome` (ou None). `arquivo_exigido` é relativo à pasta da irmã."""
    for pasta in candidatos_skill_irma(nome):
        if not pasta.is_dir():
            continue
        if arquivo_exigido and not (pasta / arquivo_exigido).exists():
            continue
        return pasta.resolve()
    return None


# ---------------------------------------------------------------------------
# incluidos.csv
# ---------------------------------------------------------------------------
def decisoes_incluidas(raiz, fonte="auto"):
    """Lista de id_rs incluídos e a fonte usada ('tc' ou 'ta')."""
    raiz = Path(raiz)
    arq_tc = raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL
    arq_ta = raiz / esquema.ARQ_TRIAGEM_TA_FINAL
    if fonte in ("auto", "tc") and arq_tc.exists():
        ids = [l["id_rs"] for l in ler_linhas(arq_tc) if normalizar.ascii_fold(l.get("decisao")).lower() == "incluir"]
        return ids, "tc"
    if fonte == "tc":
        raise FileNotFoundError(f"{esquema.ARQ_ELEGIBILIDADE_TC_FINAL} não existe; rode `textos elegibilidade consolidar`")
    if fonte == "ta" and arq_ta.exists():
        ids = [l["id_rs"] for l in ler_linhas(arq_ta)
               if normalizar.ascii_fold(l.get("decisao_final")).lower() == "incluir"]
        return ids, "ta"
    if fonte == "ta":
        raise FileNotFoundError(f"{esquema.ARQ_TRIAGEM_TA_FINAL} não existe; rode `triagem consolidar`")
    raise FileNotFoundError(
        f"{esquema.ARQ_ELEGIBILIDADE_TC_FINAL} não existe. Rode `textos elegibilidade consolidar` "
        "ou, num projeto parcial de triagem, use `--fonte ta`.")


def montar_incluidos(raiz, fonte="auto"):
    """Escreve 07-relatorio/incluidos.csv e devolve (linhas, fonte_usada, sem_chave)."""
    raiz = Path(raiz)
    ids, fonte_usada = decisoes_incluidas(raiz, fonte)
    unicos = carregar_unicos(raiz)
    linhas, sem_chave, desconhecidos = [], [], []
    for id_rs in dict.fromkeys(ids):
        reg = unicos.get(id_rs)
        if reg is None:
            desconhecidos.append(id_rs)
            continue
        if not normalizar.texto(reg.get("chave")):
            sem_chave.append(id_rs)
            continue
        linhas.append({
            "chave": reg["chave"].strip(),
            "titulo": reg.get("titulo", ""),
            "autores": reg.get("autores", ""),
            "ano": reg.get("ano", ""),
            "doi": normalizar.doi(reg.get("doi")),
            "tipo_publicacao": reg.get("tipo_publicacao", ""),
            "nome_publicacao": reg.get("veiculo", ""),
        })
    if desconhecidos:
        raise ValueError(f"id_rs incluídos ausentes de {esquema.ARQ_UNICOS}: {desconhecidos[:10]}")
    linhas.sort(key=lambda l: l["chave"])
    escrever_csv(raiz / esquema.ARQ_INCLUIDOS, esquema.COLUNAS_INCLUIDOS, linhas)
    return linhas, fonte_usada, sem_chave


# ---------------------------------------------------------------------------
# .bib mínimo (fallback sem gerar-bibtex)
# ---------------------------------------------------------------------------
_TIPO_BIB = {
    "artigo": ("article", "journal"), "revisao": ("article", "journal"),
    "editorial": ("article", "journal"), "errata": ("article", "journal"),
    "capitulo": ("incollection", "booktitle"), "livro": ("book", "publisher"),
    "tese": ("phdthesis", "school"), "dissertacao": ("mastersthesis", "school"),
    "evento": ("inproceedings", "booktitle"), "relatorio": ("techreport", "institution"),
    "preprint": ("misc", "howpublished"), "outro": ("misc", "howpublished"),
}


def _bib_texto(valor):
    return normalizar.texto(valor).replace("{", "").replace("}", "")


def entrada_bib_minima(linha):
    """Entrada BibTeX com a `chave` do projeto; campos só quando existem."""
    tipo, campo_veiculo = _TIPO_BIB.get(linha.get("tipo_publicacao", ""), ("misc", "howpublished"))
    partes = [f"@{tipo}{{{linha['chave']},"]
    if normalizar.texto(linha.get("titulo")):
        partes.append(f"  title = {{{_bib_texto(linha['titulo'])}}},")
    autores = [a.strip() for a in str(linha.get("autores", "")).split("|") if a.strip()]
    if autores:
        protegidos = ["{" + _bib_texto(a) + "}" if re.search(r"\sand\s", a, re.I) else _bib_texto(a) for a in autores]
        partes.append(f"  author = {{{' and '.join(protegidos)}}},")
    ano = normalizar.ano(linha.get("ano"))
    if ano:
        partes.append(f"  year = {{{ano}}},")
    if normalizar.texto(linha.get("nome_publicacao")):
        partes.append(f"  {campo_veiculo} = {{{_bib_texto(linha['nome_publicacao'])}}},")
    doi = normalizar.doi(linha.get("doi"))
    if doi:
        partes.append(f"  doi = {{{doi}}},")
    partes.append("}")
    return "\n".join(partes)


def chaves_do_bib(texto):
    return re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", texto)


def gerar_bib(raiz, linhas, saida, usar_irma=True):
    """Gera o .bib pela irmã (se houver) ou pelo fallback. Devolve (via, avisos)."""
    raiz = Path(raiz)
    saida = Path(saida)
    avisos = []
    via = "fallback"
    pasta = localizar_skill_irma("gerar-bibtex", "scripts/gerar_bib.py") if usar_irma else None
    if pasta is not None and linhas:
        cmd = [sys.executable, str(pasta / "scripts" / "gerar_bib.py"),
               "--planilha", str(raiz / esquema.ARQ_INCLUIDOS), "--out", str(saida), "--col-chave", "chave"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if proc.returncode == 0 and saida.exists():
                via = "gerar-bibtex"
            else:
                avisos.append(f"gerar-bibtex falhou (código {proc.returncode}); usando .bib mínimo: "
                              f"{(proc.stderr or proc.stdout).strip()[-300:]}")
        except (OSError, subprocess.TimeoutExpired) as e:
            avisos.append(f"gerar-bibtex não pôde rodar ({e}); usando .bib mínimo")
    elif usar_irma:
        avisos.append("skill gerar-bibtex não encontrada; usando .bib mínimo com a chave do projeto")
    if via == "fallback":
        escrever_texto(saida, "\n\n".join(entrada_bib_minima(l) for l in linhas) + ("\n" if linhas else ""))
    esperadas = {l["chave"] for l in linhas}
    obtidas = set(chaves_do_bib(saida.read_text(encoding="utf-8")))
    if esperadas != obtidas:
        avisos.append(f"chaves do .bib diferem de incluidos.csv: faltam {sorted(esperadas - obtidas)[:10]}, "
                      f"sobram {sorted(obtidas - esperadas)[:10]}")
    return via, avisos


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------
def cmd_incluidos(args):
    raiz = exigir_raiz(args, "incluidos")
    if raiz is None:
        return 1
    try:
        linhas, fonte_usada, sem_chave = montar_incluidos(raiz, args.fonte)
    except (FileNotFoundError, ValueError) as e:
        return falhar("incluidos", str(e))
    if sem_chave:
        return falhar("incluidos", f"{len(sem_chave)} incluídos sem `chave` em {esquema.ARQ_UNICOS}; rode `dedup`",
                      ids=sem_chave[:20])
    estado.registrar_evento(raiz, "relatorio_gerado", "11_relato", "script", ATOR,
                            dados={"produto": "incluidos", "fonte": fonte_usada, "n": len(linhas)},
                            artefatos=[esquema.ARQ_INCLUIDOS])
    avisos = [] if fonte_usada == "tc" else ["incluídos derivados da triagem T/A (projeto parcial)"]
    estado.resumo({"comando": "incluidos", "ok": True, "n_incluidos": len(linhas), "fonte": fonte_usada,
                   "arquivo": esquema.ARQ_INCLUIDOS, "avisos": avisos})
    return 0


def cmd_bib(args):
    raiz = exigir_raiz(args, "bib")
    if raiz is None:
        return 1
    try:
        linhas, fonte_usada, sem_chave = montar_incluidos(raiz, args.fonte)
    except (FileNotFoundError, ValueError) as e:
        return falhar("bib", str(e))
    if sem_chave:
        return falhar("bib", f"{len(sem_chave)} incluídos sem `chave`; rode `dedup`", ids=sem_chave[:20])
    saida = resolver_caminho(raiz, args.out)
    via, avisos = gerar_bib(raiz, linhas, saida, usar_irma=not args.sem_irma)
    rel = relativo(raiz, saida)
    estado.registrar_evento(raiz, "relatorio_gerado", "11_relato", "script", ATOR,
                            dados={"produto": "bib", "via": via, "fonte": fonte_usada, "n": len(linhas)},
                            artefatos=[esquema.ARQ_INCLUIDOS, rel])
    estado.resumo({"comando": "bib", "ok": True, "n_entradas": len(linhas), "via": via, "fonte": fonte_usada,
                   "arquivos": [esquema.ARQ_INCLUIDOS, rel], "avisos": avisos})
    return 0


def registrar(subparsers):
    p = subparsers.add_parser("incluidos", help="escreve 07-relatorio/incluidos.csv (handoff para gerar-bibtex)")
    p.add_argument("--fonte", choices=["auto", "tc", "ta"], default="auto",
                   help="decisões usadas: elegibilidade em texto completo (padrão) ou triagem T/A")
    p.set_defaults(func=cmd_incluidos)

    p = subparsers.add_parser("bib", help="gera o .bib dos incluídos (gerar-bibtex ou fallback mínimo)")
    p.add_argument("--fonte", choices=["auto", "tc", "ta"], default="auto")
    p.add_argument("--out", default=ARQ_BIB, help=f"arquivo .bib (padrão {ARQ_BIB})")
    p.add_argument("--sem-irma", action="store_true", help="não chamar gerar-bibtex; escrever o .bib mínimo")
    p.set_defaults(func=cmd_bib)
