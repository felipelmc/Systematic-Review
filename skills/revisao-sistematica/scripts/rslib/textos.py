"""Textos completos: lista para download, inventário, elegibilidade, relatos, retratações e contato com autores.

USO
    python3 rs.py textos para-baixar [--decisoes incluir,incerto] [--ids ids.csv]
    python3 rs.py textos inventario
    python3 rs.py textos elegibilidade consolidar [--master fichamentos_master.csv --codebook codebook.csv] \
        [--criterios C1,C2,...] [--verificacao verificacao_citacoes.csv]
    python3 rs.py textos ligar-relatos --pares pares.csv [--substituir-manuais]
    python3 rs.py textos retratacoes [--fonte openalex|crossref|ambas] [--ids ids.csv]
    python3 rs.py textos contato-autores --registrar contatos.csv

para-baixar
    Incluídos e incertos da triagem T/A (`02-triagem/triagem_ta_final.csv`) viram
    `03-textos/para_baixar.csv` (`chave,titulo,autores,ano,doi,id_rs`), a planilha que
    `baixar-pdfs-academicos` lê. `incerto` segue para o texto completo porque a triagem
    por título e resumo não pode excluir o que não conseguiu julgar.

inventario
    Para cada texto da lista, localiza o PDF (coluna `arquivo` de `relatorio_pdfs.csv`,
    senão `03-textos/pdfs/<chave>.pdf`) e registra com PyMuPDF páginas, caracteres e se
    há camada de texto; junta o veredito de `verificacao_conteudo.csv`. PDF válido não é
    PDF certo: veredito `suspeito`, `conferir_a_mao` ou `sem_camada_de_texto` precisa de
    olho humano antes de fichar. A coluna `recuperado` (esquema.COLUNAS_INVENTARIO_TEXTOS)
    é o que o PRISMA conta como relatório recuperado: 1 se o PDF existe e o veredito é
    `confere`, ou se a conferência humana em `03-textos/conferencia_pdfs.csv`
    (`chave,recuperado,motivo`) diz 1; 0 nos demais casos (inclusive PDF de outro trabalho
    marcado 0 à mão, que prevalece sobre `confere`).

elegibilidade consolidar
    Lê o master do `fichamento-sistematico` rodado com o codebook de elegibilidade.
    Critérios são as variáveis do codebook cuja `dimensao` fala de critério/elegibilidade
    ou cujo nome é `C1`, `c2_...`, `criterio_...` (ou a lista de `--criterios`), na ordem
    do codebook. Regra: o PRIMEIRO critério que falha vira `criterio_falhou` (com
    evidência e página); sem falha mas com resposta incerta (999, vazio, parcial) ou com
    citação reprovada no gate → `incerto`; tudo atendido → `incluir`. `NA_secao` conta
    como não aplicável. Com várias fichas do mesmo texto, basta uma incluir; senão
    incerto prevalece sobre excluir. O resultado é proposta do LLM (references/ia-validacao.md, seção 4 H).
    A fila para a decisão humana sai de `triagem fila --etapa tc` (03-textos/fila_humana_tc.csv), com a
    mesma regra de proposta (`propostas_elegibilidade`).
    Decisão humana: `triagem override --etapa tc` grava no ledger; aqui a última decisão
    humana de texto completo por `id_rs` (qualquer rodada) prevalece sobre a proposta e
    sobre o gate. Humano `incerto` no texto completo = `aguardando` (esquema.DECISOES_TC_FINAL,
    "awaiting classification", Cochrane 4.4.5): fica fora dos excluídos e dos incluídos.
    Sem master, só as decisões humanas são consolidadas. A pendência de conferência
    (autopiloto) cobre só os textos ainda sem decisão humana; fecha sozinha quando todos
    têm decisão humana e não reabre se o mesmo conjunto de propostas já foi conferido
    (pendência fechada). Sempre avisa se mais de 30% dos incluídos vieram de "outros métodos".

ligar-relatos
    `pares.csv` com colunas `id_rs_a,id_rs_b` (ou `id_rs,id_rs_relacionado`). Relatos
    ligados (união transitiva) recebem o `id_estudo` do relato de menor `id_rs`
    (convenção `esquema.id_estudo_de`: RS0007 -> ES0007, também nos valores vazios). A
    ligação fica em `03-textos/ligacao_relatos.csv`, com o `id_estudo` anterior de cada
    registro, e é aplicada à coluna `id_estudo` de `dados/registros_unicos.csv` (as
    demais colunas não mudam). A lista é acréscimo: as ligações manuais já registradas
    ficam, e as ligações de versão (preprint e publicado) feitas pelo `dedup` sempre ficam
    (`dedup.pares_versao_ligados`; desfazê-las é `dedup --revisar` com `rejeitado`). Com
    `--substituir-manuais`, as manuais antigas saem e valem só as da lista (as de versão
    continuam). O evento `ligacao_relatos` guarda `modo`, `n_pares_versao_dedup`,
    `n_pares_manuais_mantidos` e `n_pares_manuais_descartados`.

retratacoes
    MECIR C48 e Cochrane 4.4.6: para os textos não excluídos no texto completo (sem
    elegibilidade consolidada, os de `para_baixar.csv`; ou `--ids`), consulta
    `is_retracted` no OpenAlex (por DOI ou W id) e os avisos que atualizam o DOI na
    Crossref (`filter=updates:<doi>`, que traz os dados do Retraction Watch). Grava
    `03-textos/retratacoes.csv` e o evento `retratacoes_verificadas`. Retratação,
    retirada ou remoção → `retratado=1` e pendência `retratacao_texto` (G5) em qualquer
    modo, porque é fato externo que muda a elegibilidade; ela fecha quando nenhum texto
    verificado segue retratado e não reabre depois que um humano a fecha, enquanto os
    retratados e o que as fontes dizem deles não mudarem (assinatura `retratados_sha`, sem a
    data da verificação). Expressão de preocupação só avisa. `RS_EMAIL` vai como
    mailto; `OPENALEX_API_KEY` só vai ao OpenAlex (nunca à Crossref). Sem DOI nem W id,
    ou com erro de rede, `retratado` fica vazio: confira à mão.

contato-autores
    MECIR C49, PRISMA 2020 item 9 e PRISMA-S item 6. Valida o CSV
    (`chave,autor_contatado,data,pedido,resposta,dados_recebidos`), grava a versão
    canônica em `03-textos/contato_autores.csv` e registra o evento `contato_autores`.
    `data` em ISO (AAAA-MM-DD); `dados_recebidos` sim|nao|parcial ou vazio (aguardando);
    `resposta` vazia = sem resposta. Nenhum campo pode conter endereço de e-mail.
"""

import datetime as _dt
import json
import os
import re
import time
from pathlib import Path

from . import esquema, estado, normalizar
from . import triagem_lotes as tl
from .handoff import (carregar_unicos, escrever_csv, exigir_raiz, falhar, indexar, ler_csv, ler_linhas, relativo,
                      resolver_caminho, sincronizar_pendencia_unica)

ATOR = "rs.py textos"
ARQ_LIGACAO = esquema.ARQ_LIGACAO_RELATOS
COLUNAS_LIGACAO = ["id_rs", "id_estudo", "id_estudo_anterior", "grupo"]
VEREDITOS_ATENCAO = {"suspeito", "conferir_a_mao", "sem_camada_de_texto"}
VEREDITOS_RECUPERADO = {"confere"}
LIMIAR_OUTROS_METODOS = 0.30
# contratos v1.1 (esquema.py): nomes mantidos aqui como aliases
ARQ_CONFERENCIA_PDFS = esquema.ARQ_CONFERENCIA_PDFS
COLUNAS_CONFERENCIA_PDFS = esquema.COLUNAS_CONFERENCIA_PDFS
ARQ_RETRATACOES = esquema.ARQ_RETRATACOES
COLUNAS_RETRATACOES = esquema.COLUNAS_RETRATACOES
ARQ_CONTATO_AUTORES = esquema.ARQ_CONTATO_AUTORES
COLUNAS_CONTATO_AUTORES = esquema.COLUNAS_CONTATO_AUTORES
TIPO_PENDENCIA_CONFERENCIA = esquema.PENDENCIA_CONFERENCIA_ELEGIBILIDADE_TC
TIPO_PENDENCIA_RETRATACAO = esquema.PENDENCIA_RETRATACAO_TEXTO
DECISAO_AGUARDANDO = esquema.DECISAO_TC_AGUARDANDO
URL_OPENALEX = "https://api.openalex.org"
URL_CROSSREF = "https://api.crossref.org/works"
TIPOS_RETRATACAO = {"retraction", "partial_retraction", "withdrawal", "removal"}
TIPOS_PREOCUPACAO = {"expression_of_concern"}
PAUSA_ENTRE_CONSULTAS = 0.2
_SIM = {"1", "sim", "s", "true", "yes", "y", "x"}
_NAO = {"0", "nao", "n", "false", "no"}
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_dormir = time.sleep  # substituível nos testes


def _hoje():
    """Data da verificação (AAAA-MM-DD); substituível nos testes."""
    return _dt.date.today().isoformat()


def _sim_nao(valor):
    s = normalizar.ascii_fold(valor).lower().strip()
    return True if s in _SIM else (False if s in _NAO else None)


def ler_humana(caminho, obrigatorias=(), alternativas=None):
    """Planilha preenchida por humano (triagem_lotes.ler_tabela_humana): `,` `;` ou tab, BOM, cp1252, xlsx.

    Devolve (colunas, linhas, avisos). Cabeçalho que não bate vira ValueError (código 1); openpyxl ausente
    vira ErroDependencia (código 3).
    """
    try:
        colunas, linhas, info = tl.ler_tabela_humana(caminho, obrigatorias, alternativas)
    except tl.ErroDependencia as e:
        raise ErroDependencia(str(e)) from None
    except tl.ErroUso as e:
        raise ValueError(str(e)) from None
    return colunas, linhas, info["avisos"]


def ler_ids(caminho):
    """id_rs de um arquivo (planilha com coluna id_rs ou um por linha), com os mesmos formatos aceitos."""
    try:
        return tl.ler_ids_arquivo(caminho)
    except tl.ErroDependencia as e:
        raise ErroDependencia(str(e)) from None
    except tl.ErroUso as e:
        raise ValueError(str(e)) from None


def sincronizar_pendencia_sempre(raiz, tipo, etapa, portao, descricao, n, arquivo):
    """Pendência em qualquer modo de autonomia: uma aberta por (tipo, arquivo), com `n` atualizado; n = 0 fecha.

    Delegada a handoff.sincronizar_pendencia_unica(qualquer_modo=True), a mesma regra dos demais comandos.
    """
    return sincronizar_pendencia_unica(raiz, tipo, etapa, descricao, n, portao=portao, arquivo=arquivo, ator_id=ATOR,
                                       motivo_resolvida="resolvida: nenhum caso restante", qualquer_modo=True)


def _ultimo_evento(raiz, evento, filtro=lambda ev: True):
    for ev in reversed(estado.ler_log(raiz)):
        if ev.get("evento") == evento and filtro(ev):
            return ev
    return None


# ---------------------------------------------------------------------------
# PDFs
# ---------------------------------------------------------------------------
class ErroDependencia(RuntimeError):
    """PyMuPDF ausente (código de saída 3)."""


def _pymupdf():
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        try:
            import fitz
            return fitz
        except ImportError as e:
            raise ErroDependencia("PyMuPDF ausente: python3 -m pip install pymupdf") from e


def paginas_pdf(caminho):
    """Texto de cada página (índice 0 = 1ª página do arquivo)."""
    mod = _pymupdf()
    with mod.open(str(caminho)) as doc:
        return [pagina.get_text("text") for pagina in doc]


def analisar_pdf(caminho):
    """n_paginas, n_chars e tem_texto (>= 200 caracteres e >= 50% letras, como no gate de citações)."""
    try:
        paginas = paginas_pdf(caminho)
    except ErroDependencia:
        raise
    except Exception as e:  # noqa: BLE001 - PDF corrompido não derruba o inventário
        return {"n_paginas": 0, "n_chars": 0, "tem_texto": False, "erro": f"{type(e).__name__}: {e}"}
    texto = "".join(paginas)
    nao_espaco = [c for c in texto if not c.isspace()]
    fracao_letras = (sum(c.isalpha() for c in nao_espaco) / len(nao_espaco)) if nao_espaco else 0.0
    return {"n_paginas": len(paginas), "n_chars": len(nao_espaco),
            "tem_texto": len(nao_espaco) >= 200 and fracao_letras >= 0.5, "erro": ""}


def localizar_pdf(raiz, chave, relatorio=None):
    """Caminho do PDF de uma chave: relatorio_pdfs.csv (status ok) e depois 03-textos/pdfs/<chave>.pdf."""
    raiz = Path(raiz)
    relatorio = relatorio if relatorio is not None else indexar(ler_linhas(raiz / esquema.ARQ_RELATORIO_PDFS), "chave")
    candidatos = []
    linha = relatorio.get(chave)
    if linha and linha.get("status", "").strip() in esquema.STATUS_PDF_OK and linha.get("arquivo", "").strip():
        arq = Path(linha["arquivo"].strip())
        candidatos += [arq] if arq.is_absolute() else [raiz / arq, raiz / "03-textos" / arq,
                                                       raiz / "03-textos" / "pdfs" / arq.name]
    candidatos.append(raiz / "03-textos" / "pdfs" / f"{chave}.pdf")
    for c in candidatos:
        if c.is_file():
            return c
    return None


# ---------------------------------------------------------------------------
# para-baixar
# ---------------------------------------------------------------------------
def montar_para_baixar(raiz, decisoes=("incluir", "incerto"), arquivo_ids=None):
    raiz = Path(raiz)
    unicos = carregar_unicos(raiz)
    if arquivo_ids:
        ids = ler_ids(arquivo_ids)
        origem = "ids"
    else:
        ta = raiz / esquema.ARQ_TRIAGEM_TA_FINAL
        if not ta.exists():
            raise FileNotFoundError(f"{esquema.ARQ_TRIAGEM_TA_FINAL} não existe; rode `triagem consolidar` ou use --ids")
        ids = [l["id_rs"] for l in ler_linhas(ta)
               if normalizar.ascii_fold(l.get("decisao_final")).lower() in set(decisoes)]
        origem = "triagem_ta"
    linhas, sem_chave, desconhecidos = [], [], []
    for id_rs in dict.fromkeys(ids):
        reg = unicos.get(id_rs)
        if reg is None:
            desconhecidos.append(id_rs)
        elif not normalizar.texto(reg.get("chave")):
            sem_chave.append(id_rs)
        else:
            linhas.append({"chave": reg["chave"].strip(), "titulo": reg.get("titulo", ""),
                           "autores": reg.get("autores", ""), "ano": reg.get("ano", ""),
                           "doi": normalizar.doi(reg.get("doi")), "id_rs": id_rs})
    if desconhecidos:
        raise ValueError(f"id_rs ausentes de {esquema.ARQ_UNICOS}: {desconhecidos[:10]}")
    if sem_chave:
        raise ValueError(f"{len(sem_chave)} registros sem chave em {esquema.ARQ_UNICOS} (rode `dedup`): {sem_chave[:10]}")
    linhas.sort(key=lambda l: l["id_rs"])
    escrever_csv(raiz / esquema.ARQ_PARA_BAIXAR, esquema.COLUNAS_PARA_BAIXAR, linhas)
    return linhas, origem


def cmd_para_baixar(args):
    comando = "textos para-baixar"
    raiz = exigir_raiz(args, comando)
    if raiz is None:
        return 1
    decisoes = tuple(d.strip() for d in args.decisoes.split(",") if d.strip())
    invalidas = [d for d in decisoes if d not in esquema.DECISOES]
    if invalidas:
        return falhar(comando, f"decisões inválidas: {invalidas}")
    try:
        linhas, origem = montar_para_baixar(raiz, decisoes, resolver_caminho(raiz, args.ids) if args.ids else None)
    except ErroDependencia as e:
        return falhar(comando, str(e), codigo=3)
    except (FileNotFoundError, ValueError) as e:
        return falhar(comando, str(e))
    estado.registrar_evento(raiz, "textos_atualizados", "07_textos_elegibilidade", "script", ATOR,
                            dados={"acao": "para_baixar", "origem": origem, "decisoes": list(decisoes),
                                   "n": len(linhas)},
                            artefatos=[esquema.ARQ_PARA_BAIXAR])
    estado.resumo({
        "comando": comando, "ok": True, "n": len(linhas), "arquivo": esquema.ARQ_PARA_BAIXAR,
        "proximo_passo": ("skill baixar-pdfs-academicos: baixar_pdfs.py batch --planilha 03-textos/para_baixar.csv "
                          "--saida-pdfs 03-textos/pdfs --relatorio 03-textos/relatorio_pdfs.csv; depois "
                          "verificar_conteudo.py e `rs.py textos inventario`"),
    })
    return 0


# ---------------------------------------------------------------------------
# inventario
# ---------------------------------------------------------------------------
def ler_conferencia_pdfs(raiz):
    """{chave: {"recuperado": bool, "motivo": str}} de 03-textos/conferencia_pdfs.csv (vazio se não existir)."""
    caminho = Path(raiz) / ARQ_CONFERENCIA_PDFS
    if not caminho.exists():
        return {}, []
    try:
        _, linhas, avisos = ler_humana(caminho, ["chave", "recuperado"])
    except ValueError as e:
        raise ValueError(f"{e} (use {','.join(COLUNAS_CONFERENCIA_PDFS)})") from None
    conferencia = {}
    for n, linha in enumerate(linhas, start=2):
        chave = linha.get("chave", "").strip()
        if not chave:
            continue
        valor = _sim_nao(linha.get("recuperado"))
        if valor is None:
            raise ValueError(f"{ARQ_CONFERENCIA_PDFS} linha {n} ({chave}): recuperado {linha.get('recuperado')!r} "
                             "inválido (use 1/0 ou sim/nao)")
        motivo = normalizar.texto(linha.get("motivo"))
        if not valor and not motivo:
            avisos.append(f"{ARQ_CONFERENCIA_PDFS}: {chave} marcado não recuperado sem motivo")
        conferencia[chave] = {"recuperado": valor, "motivo": motivo}
    return conferencia, avisos


def montar_inventario(raiz):
    raiz = Path(raiz)
    lista = ler_linhas(raiz / esquema.ARQ_PARA_BAIXAR)
    relatorio = indexar(ler_linhas(raiz / esquema.ARQ_RELATORIO_PDFS), "chave")
    verificacao = indexar(ler_linhas(raiz / esquema.ARQ_VERIFICACAO_CONTEUDO), "chave")
    conferencia, avisos_conferencia = ler_conferencia_pdfs(raiz)
    if not lista:
        por_chave = {r.get("chave"): r["id_rs"] for r in carregar_unicos(raiz).values() if r.get("chave")}
        lista = [{"chave": k, "id_rs": por_chave.get(k, "")} for k in relatorio]
    if not lista:
        raise FileNotFoundError(f"nem {esquema.ARQ_PARA_BAIXAR} nem {esquema.ARQ_RELATORIO_PDFS} existem")
    linhas, erros = [], []
    chaves_lista = set()
    for item in lista:
        chave = item["chave"].strip()
        chaves_lista.add(chave)
        pdf = localizar_pdf(raiz, chave, relatorio)
        info = analisar_pdf(pdf) if pdf else {"n_paginas": "", "n_chars": "", "tem_texto": "", "erro": ""}
        if info.get("erro"):
            erros.append(f"{chave}: {info['erro']}")
        veredito = verificacao.get(chave, {}).get("veredito", "")
        conferido = conferencia.get(chave)
        if pdf and conferido is not None:
            recuperado = conferido["recuperado"]  # conferência humana prevalece sobre o veredito automático
        else:
            recuperado = bool(pdf) and normalizar.ascii_fold(veredito).lower().strip() in VEREDITOS_RECUPERADO
        if conferido and conferido["recuperado"] and not pdf:
            avisos_conferencia.append(f"{chave}: conferido como recuperado, mas o PDF não foi encontrado (recuperado=0)")
        linhas.append({
            "chave": chave, "id_rs": item.get("id_rs", ""), "arquivo": relativo(raiz, pdf) if pdf else "",
            "existe": "1" if pdf else "0", "n_paginas": info["n_paginas"], "n_chars": info["n_chars"],
            "tem_texto": ("1" if info["tem_texto"] else "0") if pdf else "",
            "veredito_conteudo": veredito, "recuperado": "1" if recuperado else "0",
        })
    for chave in sorted(set(conferencia) - chaves_lista):
        avisos_conferencia.append(f"{ARQ_CONFERENCIA_PDFS}: chave {chave} fora da lista de textos (ignorada)")
    linhas.sort(key=lambda l: (l["id_rs"], l["chave"]))
    escrever_csv(raiz / esquema.ARQ_INVENTARIO_TEXTOS, esquema.COLUNAS_INVENTARIO_TEXTOS, linhas)
    return linhas, erros, bool(verificacao), avisos_conferencia


def cmd_inventario(args):
    comando = "textos inventario"
    raiz = exigir_raiz(args, comando)
    if raiz is None:
        return 1
    try:
        linhas, erros, tem_verificacao, avisos_conferencia = montar_inventario(raiz)
    except ErroDependencia as e:
        return falhar(comando, str(e), codigo=3)
    except (FileNotFoundError, ValueError) as e:
        return falhar(comando, str(e))
    n_existe = sum(1 for l in linhas if l["existe"] == "1")
    n_recuperados = sum(1 for l in linhas if l["recuperado"] == "1")
    sem_texto = [l["chave"] for l in linhas if l["existe"] == "1" and l["tem_texto"] != "1"]
    atencao = [l["chave"] for l in linhas if l["veredito_conteudo"] in VEREDITOS_ATENCAO]
    faltando = [l["chave"] for l in linhas if l["existe"] != "1"]
    existe_nao_recuperado = [l["chave"] for l in linhas if l["existe"] == "1" and l["recuperado"] != "1"]
    artefatos = [esquema.ARQ_INVENTARIO_TEXTOS]
    if (raiz / ARQ_CONFERENCIA_PDFS).exists():
        artefatos.append(ARQ_CONFERENCIA_PDFS)
    estado.registrar_evento(raiz, "textos_atualizados", "07_textos_elegibilidade", "script", ATOR,
                            dados={"acao": "inventario", "n": len(linhas), "n_existe": n_existe,
                                   "n_recuperados": n_recuperados, "n_sem_texto": len(sem_texto),
                                   "n_atencao": len(atencao)},
                            artefatos=artefatos)
    avisos = []
    if not tem_verificacao and n_existe:
        avisos.append("verificacao_conteudo.csv ausente: rode verificar_conteudo.py da baixar-pdfs-academicos")
    if existe_nao_recuperado:
        avisos.append(f"{len(existe_nao_recuperado)} PDFs existem mas não contam como recuperados (veredito diferente "
                      f"de confere ou conferência humana 0): confira e registre em {ARQ_CONFERENCIA_PDFS}")
    if sem_texto:
        avisos.append(f"{len(sem_texto)} PDFs sem camada de texto: exigem OCR ou leitura visual")
    avisos += [f"PDF ilegível: {e}" for e in erros] + avisos_conferencia
    estado.resumo({"comando": comando, "ok": True, "n": len(linhas), "n_existe": n_existe,
                   "n_recuperados": n_recuperados, "n_faltando": len(faltando), "faltando": faltando[:20],
                   "sem_texto": sem_texto[:20], "conferir_conteudo": atencao[:20],
                   "existe_nao_recuperado": existe_nao_recuperado[:20],
                   "arquivo": esquema.ARQ_INVENTARIO_TEXTOS, "avisos": avisos})
    return 0


# ---------------------------------------------------------------------------
# elegibilidade consolidar
# ---------------------------------------------------------------------------
_ATENDE = {"sim", "s", "yes", "y", "atende", "cumpre", "passa", "true", "1", "incluir", "ok"}
_FALHA = {"nao", "n", "no", "falha", "false", "0", "exclui", "excluir", "nao_atende", "reprova"}
_NAO_APLICA = {"na_secao", "nao_se_aplica", "nao_aplicavel", "n_a"}
_PAGINA = re.compile(r"\(\s*p{1,2}\.?\s*(\d{1,4})", re.IGNORECASE)


def classificar_resposta(valor):
    """'atende' | 'falha' | 'incerto' | 'nao_aplica' para a resposta de um critério."""
    s = normalizar.ascii_fold(valor).lower().strip()
    if not s or s.startswith("999") or "parcial" in s or "incert" in s or "unclear" in s:
        return "incerto"
    compacto = re.sub(r"[\s-]+", "_", s)
    if compacto in _NAO_APLICA or compacto.startswith("na_secao"):
        return "nao_aplica"
    if compacto.startswith(("nao_atende", "nao_cumpre", "does_not", "not_met")):
        return "falha"
    primeiro = re.split(r"[\s,;:.()—–-]+", s, maxsplit=1)[0]
    if primeiro in _ATENDE:
        return "atende"
    if primeiro in _FALHA:
        return "falha"
    return "incerto"


def detectar_criterios(codebook, explicitos=None):
    """Variáveis-critério na ordem do codebook."""
    variaveis = [l.get("variavel", "").strip() for l in codebook if l.get("variavel", "").strip()]
    if explicitos:
        faltam = [c for c in explicitos if c not in variaveis]
        if faltam:
            raise ValueError(f"critérios ausentes do codebook: {faltam}")
        return [v for v in variaveis if v in set(explicitos)]
    criterios = []
    for l in codebook:
        var = l.get("variavel", "").strip()
        dim = normalizar.ascii_fold(l.get("dimensao")).lower()
        if var and (re.match(r"^(c\d+($|_)|criterio)", var, re.IGNORECASE) or "criterio" in dim or "elegib" in dim):
            criterios.append(var)
    if not criterios:
        raise ValueError("nenhuma variável-critério no codebook (dimensão 'critério/elegibilidade' ou nomes C1, C2...); "
                         "use --criterios")
    return criterios


def _problemas_gate(caminho):
    """(citekey, variavel) com citação reprovada no verify_citacoes.py."""
    if not caminho:
        return set()
    ruins = set()
    for l in ler_linhas(caminho):
        if l.get("status", "OK") not in ("OK", "PDF_TEXTO_NAO_EXTRAIVEL"):
            ruins.add((l.get("citekey", ""), l.get("variavel", "")))
    return ruins


def avaliar_ficha(linha, criterios, gate_ruim=frozenset()):
    """Decisão de uma ficha: dict decisao, criterio_falhou, evidencia, pagina, incertos."""
    chave = linha.get("citekey", "")
    incertos = []
    for crit in criterios:
        classe = classificar_resposta(linha.get(crit, ""))
        evidencia = normalizar.texto(linha.get(f"{crit}__evidencia", ""))
        if classe in ("atende", "falha") and (chave, crit) in gate_ruim:
            classe = "incerto"
            evidencia = f"[citação reprovada no gate] {evidencia}"
        if classe == "falha":
            m = _PAGINA.search(evidencia)
            return {"decisao": "excluir", "criterio_falhou": crit, "evidencia": evidencia,
                    "pagina": m.group(1) if m else "", "incertos": incertos}
        if classe == "incerto":
            incertos.append(crit)
    if incertos:
        return {"decisao": "incerto", "criterio_falhou": "",
                "evidencia": "critérios sem resposta conclusiva: " + ", ".join(incertos), "pagina": "",
                "incertos": incertos}
    return {"decisao": "incluir", "criterio_falhou": "", "evidencia": "", "pagina": "", "incertos": []}


def decisoes_humanas_tc(raiz):
    """Última decisão humana de texto completo por id_rs no ledger (`triagem override --etapa tc`)."""
    ultima = {}
    for linha in tl.ler_decisoes(raiz):
        if linha.get("etapa") == "tc" and linha.get("tipo_ator") == "humano":
            ultima[linha["id_rs"]] = linha
    return ultima


def decisao_final_humana(linha):
    """Humano `incerto` no texto completo é `aguardando` (o ledger não tem esse valor)."""
    return DECISAO_AGUARDANDO if linha.get("decisao") == "incerto" else linha.get("decisao")


def propostas_elegibilidade(raiz, master, codebook, criterios_explicitos=None, verificacao=None, unicos=None):
    """Propostas do LLM por id_rs a partir das fichas, sem decisões humanas e sem gravar nada.

    Devolve (propostas, criterios, desconhecidas, avisos). Usada por `textos elegibilidade consolidar` e
    por `triagem fila --etapa tc`, para as duas aplicarem exatamente a mesma regra.
    """
    raiz = Path(raiz)
    unicos = unicos if unicos is not None else carregar_unicos(raiz)
    por_chave = {r["chave"].strip(): r for r in unicos.values() if r.get("chave", "").strip()}
    _, cb, avisos = ler_humana(codebook, ["variavel"])  # o codebook de elegibilidade é ajustado à mão
    criterios = detectar_criterios(cb, criterios_explicitos)
    try:
        colunas_master, fichas, avisos_master = ler_humana(master, ["citekey"])
    except ValueError as e:
        raise ValueError(f"master sem coluna citekey (gere com consolida.py do fichamento-sistematico): {e}") from None
    avisos += avisos_master
    faltam = [c for c in criterios if c not in colunas_master]
    if faltam:
        raise ValueError(f"critérios ausentes do master: {faltam}")
    gate_ruim = _problemas_gate(verificacao)
    por_texto, desconhecidas, propostas = {}, [], {}
    for ficha in fichas:
        chave = ficha.get("citekey", "").strip()
        if chave not in por_chave:
            desconhecidas.append(chave)
            continue
        por_texto.setdefault(chave, []).append(avaliar_ficha(ficha, criterios, gate_ruim))
    for chave, avaliacoes in por_texto.items():
        escolhida = (next((a for a in avaliacoes if a["decisao"] == "incluir"), None)
                     or next((a for a in avaliacoes if a["decisao"] == "incerto"), None)
                     or avaliacoes[0])
        id_rs = por_chave[chave]["id_rs"]
        propostas[id_rs] = {"id_rs": id_rs, "chave": chave, **escolhida, "origem": "proposta_ia", "proposta": None}
    return propostas, criterios, sorted(set(desconhecidas)), avisos


def consolidar_elegibilidade(raiz, master=None, codebook=None, criterios_explicitos=None, verificacao=None):
    """Propostas das fichas + decisões humanas do ledger. Devolve (linhas, criterios, desconhecidas, avisos).

    Cada linha traz, além das colunas do contrato, `origem` (proposta_ia|humano) e `proposta`.
    """
    raiz = Path(raiz)
    unicos = carregar_unicos(raiz)
    criterios, desconhecidas, avisos = [], [], []
    linhas = {}
    if master is not None:
        linhas, criterios, desconhecidas, avisos = propostas_elegibilidade(raiz, master, codebook, criterios_explicitos,
                                                                          verificacao, unicos)
    for id_rs, humana in decisoes_humanas_tc(raiz).items():
        reg = unicos.get(id_rs)
        if reg is None or not reg.get("chave", "").strip():
            avisos.append(f"decisão humana de texto completo para {id_rs} sem chave em {esquema.ARQ_UNICOS}: ignorada")
            continue
        proposta = linhas.get(id_rs)
        decisao = decisao_final_humana(humana)
        criterio = normalizar.texto(humana.get("criterio_falhou")) if decisao == "excluir" else ""
        if decisao == "excluir" and not criterio and proposta and proposta["decisao"] == "excluir":
            criterio = proposta["criterio_falhou"]
        if decisao == "excluir" and not criterio:
            avisos.append(f"{reg['chave']}: exclusão humana sem critério (motivo do PRISMA fica vazio); "
                          "registre de novo com --criterio")
        confirma = proposta is not None and proposta["decisao"] == decisao and proposta["criterio_falhou"] == criterio
        motivo = normalizar.texto(humana.get("motivo_override") or humana.get("justificativa"))
        evidencia = f"[decisão humana: {humana.get('revisor')}] {motivo}".strip()
        if confirma and proposta.get("evidencia"):
            evidencia += f" | proposta confirmada: {proposta['evidencia']}"
        linhas[id_rs] = {"id_rs": id_rs, "chave": reg["chave"].strip(), "decisao": decisao, "criterio_falhou": criterio,
                         "evidencia": evidencia, "pagina": proposta.get("pagina", "") if confirma else "",
                         "incertos": [], "origem": "humano", "proposta": proposta["decisao"] if proposta else None}
    saida = sorted(linhas.values(), key=lambda l: l["id_rs"])
    escrever_csv(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL, esquema.COLUNAS_ELEGIBILIDADE_FINAL, saida)
    return saida, criterios, desconhecidas, avisos


def fracao_outros_metodos(raiz, ids_incluidos):
    """Fração dos incluídos identificada só por citação/cinzenta/manual (alerta PRISMA-S)."""
    raiz = Path(raiz)
    registros = indexar(ler_linhas(raiz / esquema.ARQ_REGISTROS), "id_registro")
    unicos = carregar_unicos(raiz)
    if not ids_incluidos or not registros:
        return None
    outros = 0
    for id_rs in ids_incluidos:
        ids_reg = [i for i in unicos.get(id_rs, {}).get("ids_registro", "").split("|") if i]
        metodos = {registros[i].get("metodo_identificacao", "") for i in ids_reg if i in registros}
        if metodos and "base" not in metodos:
            outros += 1
    return outros / len(ids_incluidos)


def _pendencia_fechada(est, pid):
    return any(p.get("id") == pid and p.get("status") == "fechada" for p in est.get("pendencias", []))


def cmd_elegibilidade_consolidar(args):
    comando = "textos elegibilidade consolidar"
    raiz = exigir_raiz(args, comando)
    if raiz is None:
        return 1
    if bool(args.master) != bool(args.codebook):
        return falhar(comando, "informe --master e --codebook juntos (ou nenhum dos dois, para consolidar só as "
                               "decisões humanas de texto completo)")
    master = resolver_caminho(raiz, args.master) if args.master else None
    codebook = resolver_caminho(raiz, args.codebook) if args.codebook else None
    for arq in (master, codebook):
        if arq is not None and not arq.exists():
            return falhar(comando, f"arquivo não encontrado: {arq}")
    if master is None and not decisoes_humanas_tc(raiz):
        return falhar(comando, "sem --master/--codebook e sem decisões humanas de texto completo no ledger "
                               "(`triagem override --etapa tc`)")
    explicitos = [c.strip() for c in args.criterios.split(",") if c.strip()] if args.criterios else None
    verificacao = resolver_caminho(raiz, args.verificacao) if args.verificacao else None
    try:
        linhas, criterios, desconhecidas, avisos = consolidar_elegibilidade(raiz, master, codebook, explicitos,
                                                                            verificacao)
    except ErroDependencia as e:
        return falhar(comando, str(e), codigo=3)
    except ValueError as e:
        return falhar(comando, str(e))
    if not linhas:
        return falhar(comando, "nenhuma ficha com citekey correspondente a uma chave do projeto",
                      chaves_desconhecidas=desconhecidas[:20])
    contagem = {d: sum(1 for l in linhas if l["decisao"] == d) for d in esquema.DECISOES}
    n_aguardando = sum(1 for l in linhas if l["decisao"] == DECISAO_AGUARDANDO)
    if n_aguardando:
        contagem[DECISAO_AGUARDANDO] = n_aguardando
    motivos = {}
    for l in linhas:
        if l["criterio_falhou"] and l["decisao"] == "excluir":
            motivos[l["criterio_falhou"]] = motivos.get(l["criterio_falhou"], 0) + 1
    humanas = [l for l in linhas if l["origem"] == "humano"]
    mudadas = [l["chave"] for l in humanas if l["proposta"] and l["proposta"] != l["decisao"]]
    pendentes = sorted(l["id_rs"] for l in linhas if l["origem"] == "proposta_ia")
    if desconhecidas:
        avisos.append(f"{len(desconhecidas)} citekeys do master sem chave no projeto (ignoradas): {desconhecidas[:10]}")
    if contagem["incerto"]:
        avisos.append(f"{contagem['incerto']} textos incertos sem decisão humana: decida com `triagem override --etapa tc` "
                      "(incluir, excluir com --criterio ou aguardando)")
    fracao = fracao_outros_metodos(raiz, [l["id_rs"] for l in linhas if l["decisao"] == "incluir"])
    if fracao is not None and fracao > LIMIAR_OUTROS_METODOS:
        avisos.append(f"{fracao:.0%} dos incluídos vieram só de outros métodos (> 30%): a busca nas bases pode ser fraca")

    sha_pendentes = estado.sha256_texto("\n".join(pendentes))
    anterior = _ultimo_evento(raiz, "textos_atualizados",
                              lambda ev: (ev.get("dados") or {}).get("acao") == "elegibilidade_consolidar")
    dados_ant = (anterior or {}).get("dados") or {}
    est = estado.carregar_estado(raiz)
    abertas = [p for p in estado.pendencias_abertas(est) if p.get("tipo") == TIPO_PENDENCIA_CONFERENCIA
               and (p.get("arquivo") or None) == esquema.ARQ_ELEGIBILIDADE_TC_FINAL]
    pendencia, conferida = None, False
    if pendentes and not abertas and dados_ant.get("pendentes_sha") == sha_pendentes and dados_ant.get("pendencia") \
            and _pendencia_fechada(est, dados_ant["pendencia"]):
        conferida = True  # o mesmo conjunto de propostas já foi conferido: não reabrir
    else:
        # n = propostas que ainda aguardam confirmação humana; n = 0 fecha; n diferente atualiza sem duplicar.
        pendencia = sincronizar_pendencia_unica(
            raiz, TIPO_PENDENCIA_CONFERENCIA, "07_textos_elegibilidade",
            f"conferir {len(pendentes)} decisões de elegibilidade propostas a partir das fichas (humano decide com "
            "`triagem override --etapa tc`; incertos primeiro)",
            len(pendentes), portao="G5", arquivo=esquema.ARQ_ELEGIBILIDADE_TC_FINAL, ator_id=ATOR,
            motivo_resolvida="todos os textos têm decisão humana de texto completo")

    sha_final = estado.sha256_arquivo(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL)
    pendencia_log = pendencia or (dados_ant.get("pendencia") if conferida else None)
    reexecucao = bool(anterior) and dados_ant.get("sha_final") == sha_final \
        and dados_ant.get("pendentes_sha") == sha_pendentes and dados_ant.get("pendencia") == pendencia_log
    if not reexecucao:
        artefatos = [esquema.ARQ_ELEGIBILIDADE_TC_FINAL]
        artefatos += [relativo(raiz, a) for a in (master, codebook) if a is not None]
        estado.registrar_evento(raiz, "textos_atualizados", "07_textos_elegibilidade", "script", ATOR,
                                dados={"acao": "elegibilidade_consolidar", "criterios": criterios, "contagem": contagem,
                                       "motivos": motivos, "proposta_ia": any(l["origem"] == "proposta_ia" or l["proposta"]
                                                                               for l in linhas),
                                       "n_decisoes_humanas": len(humanas), "n_mudadas_por_humano": len(mudadas),
                                       "n_pendentes_conferencia": len(pendentes), "pendentes_sha": sha_pendentes,
                                       "pendencia": pendencia_log, "sha_final": sha_final},
                                artefatos=artefatos)
    acao = ("conferir decisões (G5) antes de seguir" if pendentes
            else "todas as decisões de texto completo são humanas; conferir o G5")
    estado.resumo({"comando": comando, "ok": True, "reexecucao": reexecucao, "n_textos": len(linhas),
                   "contagem": contagem, "motivos_exclusao": motivos, "criterios": criterios,
                   "n_decisoes_humanas": len(humanas), "mudadas_por_humano": mudadas[:20],
                   "n_pendentes_conferencia": len(pendentes), "conferencia_ja_feita": conferida,
                   "fracao_outros_metodos": None if fracao is None else round(fracao, 3),
                   "arquivo": esquema.ARQ_ELEGIBILIDADE_TC_FINAL, "pendencia": pendencia,
                   "acao_humana": acao, "avisos": avisos})
    return 0


# ---------------------------------------------------------------------------
# ligar-relatos
# ---------------------------------------------------------------------------
def _num(id_rs):
    m = re.search(r"\d+", id_rs)
    return (int(m.group()) if m else 0, id_rs)


def ler_pares(caminho):
    grupos = (("id_rs_a", "id_rs_b"), ("id_rs", "id_rs_relacionado"))
    try:
        colunas, linhas, _ = ler_humana(caminho, alternativas=[list(g) for g in grupos])
    except ValueError as e:
        raise ValueError(f"pares.csv precisa das colunas id_rs_a,id_rs_b (ou id_rs,id_rs_relacionado): {e}") from None
    for a, b in grupos:
        if a in colunas and b in colunas:
            return [(l[a].strip().upper(), l[b].strip().upper()) for l in linhas if l[a].strip() and l[b].strip()]
    raise ValueError("pares.csv precisa das colunas id_rs_a,id_rs_b (ou id_rs,id_rs_relacionado)")


def ligar_relatos(raiz, pares):
    raiz = Path(raiz)
    caminho_unicos = raiz / esquema.ARQ_UNICOS
    if not caminho_unicos.exists():
        raise FileNotFoundError(f"{esquema.ARQ_UNICOS} não existe; rode `dedup`")
    colunas, registros = ler_csv(caminho_unicos)
    if "id_estudo" not in colunas or "id_rs" not in colunas:
        raise ValueError(f"{esquema.ARQ_UNICOS} sem colunas id_rs/id_estudo")
    por_id = {r["id_rs"]: r for r in registros}
    faltam = sorted({i for par in pares for i in par if i not in por_id})
    if faltam:
        raise ValueError(f"id_rs inexistentes em pares.csv: {faltam[:10]}")

    anterior = indexar(ler_linhas(raiz / ARQ_LIGACAO), "id_rs")
    # restaura o id_estudo original dos que estavam ligados, para a rodada partir do zero
    for id_rs, lig in anterior.items():
        if id_rs in por_id:
            por_id[id_rs]["id_estudo"] = lig.get("id_estudo_anterior") or esquema.id_estudo_de(id_rs)

    pai = {}

    def achar(x):
        pai.setdefault(x, x)
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    for a, b in pares:
        ra, rb = achar(a), achar(b)
        if ra != rb:
            pai[max(ra, rb, key=_num)] = min(ra, rb, key=_num)
    grupos = {}
    for x in list(pai):
        grupos.setdefault(achar(x), []).append(x)

    ligacao = []
    for raiz_grupo, membros in sorted(grupos.items(), key=lambda kv: _num(kv[0])):
        membros = sorted(membros, key=_num)
        principal = membros[0]
        id_estudo = por_id[principal].get("id_estudo", "").strip() or esquema.id_estudo_de(principal)
        for m in membros:
            ligacao.append({"id_rs": m, "id_estudo": id_estudo,
                            "id_estudo_anterior": por_id[m].get("id_estudo", "").strip() or esquema.id_estudo_de(m),
                            "grupo": "|".join(membros)})
    for lig in ligacao:
        por_id[lig["id_rs"]]["id_estudo"] = lig["id_estudo"]
    escrever_csv(caminho_unicos, colunas, registros)
    escrever_csv(raiz / ARQ_LIGACAO, COLUNAS_LIGACAO, ligacao)
    n_estudos = len({(r.get("id_estudo") or "").strip() or esquema.id_estudo_de(r["id_rs"]) for r in registros})
    return ligacao, len(grupos), n_estudos


def _par_ordenado(a, b):
    return tuple(sorted((a, b), key=_num))


def pares_para_ligar(raiz, recebidos, substituir_manuais=False):
    """Pares que `textos ligar-relatos` aplica: versões ligadas pelo dedup + ligações manuais + lista recebida.

    - Versões (preprint e publicado) ligadas pelo `dedup` (dedup.pares_versao_ligados) sempre ficam: desfazê-las
      é decisão do dedup (`dedup --revisar` com `rejeitado`), não desta lista.
    - Ligações manuais já registradas em 03-textos/ligacao_relatos.csv (os grupos do arquivo menos as versões,
      pela mesma regra do dedup, dedup.pares_preservados) ficam, e a lista recebida é acréscimo.
    - Com `substituir_manuais`, as manuais antigas saem e valem só as da lista recebida (as versões ficam).
    Devolve (pares finais ordenados, info com as contagens de cada origem).
    """
    from . import dedup  # import tardio: dedup importa textos só dentro de função
    raiz = Path(raiz)
    recebidos = {_par_ordenado(a, b) for a, b in recebidos if a and b and a != b}
    versao = {_par_ordenado(a, b) for a, b in dedup.pares_versao_ligados(raiz)}
    ultimo = _ultimo_evento(raiz, "dedup_executado")
    dados = (ultimo or {}).get("dados") or {}
    ids_validos = {l.get("id_rs", "") for l in ler_linhas(raiz / esquema.ARQ_UNICOS)} \
        if (raiz / esquema.ARQ_UNICOS).exists() else None
    brutos, origem, _ = dedup.pares_preservados(raiz, dados.get("ligacao_relatos"), dados.get("ids_rs_aposentados"),
                                                ids_validos)
    manuais = {_par_ordenado(a, b) for a, b in brutos} - versao
    descartados = sorted(manuais - recebidos) if substituir_manuais else []
    mantidos = set() if substituir_manuais else manuais
    finais = sorted(versao | mantidos | recebidos, key=lambda p: (_num(p[0]), _num(p[1])))
    info = {"modo": "substituir_manuais" if substituir_manuais else "acrescimo",
            "n_pares_recebidos": len(recebidos), "n_pares_versao_dedup": len(versao),
            "n_pares_manuais_mantidos": len(mantidos - recebidos), "n_pares_manuais_descartados": len(descartados),
            "pares_manuais_descartados": [list(p) for p in descartados[:50]], "origem_manuais": origem,
            "n_pares_aplicados": len(finais)}
    return finais, info


def cmd_ligar_relatos(args):
    comando = "textos ligar-relatos"
    raiz = exigir_raiz(args, comando)
    if raiz is None:
        return 1
    pares_arq = resolver_caminho(raiz, args.pares)
    if not pares_arq.exists():
        return falhar(comando, f"arquivo não encontrado: {pares_arq}")
    substituir = bool(getattr(args, "substituir_manuais", False))
    try:
        pares = ler_pares(pares_arq)
        faltam = sorted({i for par in pares for i in par}
                        - {l.get("id_rs", "") for l in ler_linhas(raiz / esquema.ARQ_UNICOS)}) \
            if (raiz / esquema.ARQ_UNICOS).exists() else []
        if faltam:
            raise ValueError(f"id_rs inexistentes em pares.csv: {faltam[:10]}")
        finais, info = pares_para_ligar(raiz, pares, substituir)
        ligacao, n_grupos, n_estudos = ligar_relatos(raiz, finais)
    except ErroDependencia as e:
        return falhar(comando, str(e), codigo=3)
    except (FileNotFoundError, ValueError) as e:
        return falhar(comando, str(e))
    avisos = []
    if info["n_pares_manuais_descartados"]:
        avisos.append(f"--substituir-manuais: {info['n_pares_manuais_descartados']} ligações manuais antigas desfeitas "
                      f"(ex.: {', '.join('×'.join(p) for p in info['pares_manuais_descartados'][:5])})")
    if info["n_pares_versao_dedup"]:
        avisos.append(f"{info['n_pares_versao_dedup']} ligações de versão do dedup mantidas (preprint e publicado); para "
                      "desfazer uma, marque o par como rejeitado em `dedup --revisar`")
    estado.registrar_evento(raiz, "ligacao_relatos", "07_textos_elegibilidade", "script", ATOR,
                            dados={"n_pares": len(pares), "n_grupos": n_grupos,
                                   "n_relatos_ligados": len(ligacao), "n_estudos": n_estudos, **info},
                            artefatos=[ARQ_LIGACAO, esquema.ARQ_UNICOS, relativo(raiz, pares_arq)])
    estado.resumo({"comando": comando, "ok": True, "n_pares": len(pares), "n_grupos": n_grupos,
                   "n_relatos_ligados": len(ligacao), "n_estudos_total": n_estudos, **info, "avisos": avisos,
                   "arquivos": [ARQ_LIGACAO, esquema.ARQ_UNICOS]})
    return 0


# ---------------------------------------------------------------------------
# retratacoes
# ---------------------------------------------------------------------------
def criar_sessao_http():
    """Sessão HTTP (requests); isolada para os testes injetarem uma sessão falsa, sem rede."""
    from .busca_openalex import criar_sessao
    return criar_sessao()


def textos_para_retratacoes(raiz, arquivo_ids=None):
    """Itens {id_rs, chave, doi, id_openalex} a verificar e o universo usado."""
    raiz = Path(raiz)
    unicos = carregar_unicos(raiz)
    avisos = []
    if arquivo_ids:
        ids = ler_ids(arquivo_ids)
        universo = "ids"
    elif (raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL).exists():
        ids = [l["id_rs"] for l in ler_linhas(raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL)
               if normalizar.ascii_fold(l.get("decisao")).lower() != "excluir"]
        universo = "tc_nao_excluidos"
    elif (raiz / esquema.ARQ_PARA_BAIXAR).exists():
        ids = [l["id_rs"] for l in ler_linhas(raiz / esquema.ARQ_PARA_BAIXAR) if l.get("id_rs")]
        universo = "para_baixar"
        avisos.append("elegibilidade em texto completo ainda não consolidada: verificados os textos de para_baixar.csv")
    else:
        raise FileNotFoundError(f"nem {esquema.ARQ_ELEGIBILIDADE_TC_FINAL} nem {esquema.ARQ_PARA_BAIXAR} existem; "
                                "use --ids")
    itens, desconhecidos = [], []
    for id_rs in dict.fromkeys(ids):
        reg = unicos.get(id_rs)
        if reg is None:
            desconhecidos.append(id_rs)
            continue
        w = re.search(r"W\d+", reg.get("id_fonte", "") or "") if "openalex" in (reg.get("fontes") or "") else None
        itens.append({"id_rs": id_rs, "chave": (reg.get("chave") or "").strip(), "doi": normalizar.doi(reg.get("doi")),
                      "id_openalex": w.group() if w else ""})
    if desconhecidos:
        raise ValueError(f"id_rs ausentes de {esquema.ARQ_UNICOS}: {desconhecidos[:10]}")
    return itens, universo, avisos


def verificar_retratacoes(itens, fonte="ambas", sessao=None, email=None, api_key=None, tentativas=3):
    """Consulta OpenAlex (is_retracted) e/ou Crossref (avisos `update-to`). Uma linha por item."""
    from .busca_openalex import ClienteOpenAlex, ErroOpenAlex

    sessao = sessao if sessao is not None else criar_sessao_http()
    email = email if email is not None else os.environ.get("RS_EMAIL")
    api_key = api_key if api_key is not None else os.environ.get("OPENALEX_API_KEY")
    espera = lambda s: _dormir(s)  # noqa: E731 - lido na hora, para os testes substituírem _dormir
    openalex = ClienteOpenAlex(sessao=sessao, email=email, api_key=api_key or "", tentativas=tentativas, espera=espera)
    # A chave do OpenAlex nunca vai para a Crossref: cliente separado, sem api_key.
    crossref = ClienteOpenAlex(sessao=sessao, email=email, api_key="", tentativas=tentativas, espera=espera)
    hoje = _hoje()
    linhas = []
    for k, item in enumerate(itens):
        if k:
            _dormir(PAUSA_ENTRE_CONSULTAS)
        doi = item["doi"]
        linha = {"chave": item["chave"], "id_rs": item["id_rs"], "doi": doi, "openalex_is_retracted": "nao_consultado",
                 "crossref_avisos": "nao_consultado", "retratado": "", "status": "", "verificado_em": hoje}
        respostas, falhas, retratado, tipos = 0, 0, False, set()
        if fonte in ("openalex", "ambas"):
            ident = f"doi:{doi}" if doi else item.get("id_openalex")
            if not ident:
                linha["openalex_is_retracted"] = "sem_id"
            else:
                try:
                    obra = openalex.get(f"{URL_OPENALEX}/works/{ident}", {"select": "id,doi,is_retracted"},
                                        aceitar_404=True)
                except ErroOpenAlex as e:
                    linha["openalex_is_retracted"], falhas = f"erro: {str(e)[:120]}", falhas + 1
                else:
                    if obra is None:
                        linha["openalex_is_retracted"] = "nao_encontrado"
                    else:
                        retratado = retratado or obra.get("is_retracted") is True
                        linha["openalex_is_retracted"] = "true" if obra.get("is_retracted") is True else "false"
                        respostas += 1
        if fonte in ("crossref", "ambas"):
            if not doi:
                linha["crossref_avisos"] = "sem_doi"
            else:
                try:
                    dados = crossref.get(URL_CROSSREF, {"filter": f"updates:{doi}", "select": "DOI,update-to",
                                                        "rows": 20})
                except ErroOpenAlex as e:
                    linha["crossref_avisos"], falhas = f"erro: {str(e)[:120]}", falhas + 1
                else:
                    avisos = set()
                    for aviso in (((dados or {}).get("message") or {}).get("items") or []):
                        for atualizacao in aviso.get("update-to") or []:
                            if normalizar.doi(atualizacao.get("DOI")) != doi:
                                continue
                            tipo = re.sub(r"[\s-]+", "_", str(atualizacao.get("type") or "").strip().lower())
                            tipos.add(tipo)
                            avisos.add(f"{tipo}:{normalizar.doi(aviso.get('DOI'))}")
                    linha["crossref_avisos"] = "|".join(sorted(avisos)) or "nenhum"
                    respostas += 1
        retratado = retratado or bool(tipos & TIPOS_RETRATACAO)
        linha["retratado"] = "1" if retratado else ("0" if respostas else "")
        if not doi and (fonte == "crossref" or not item.get("id_openalex")):
            linha["status"] = "sem_doi"
        elif respostas and not falhas:
            linha["status"] = "ok"
        elif respostas:
            linha["status"] = "parcial"
        else:
            linha["status"] = "erro" if falhas else "nao_encontrado"
        linha["_preocupacao"] = bool(tipos & TIPOS_PREOCUPACAO)
        linhas.append(linha)
    return linhas


def pendencia_retratacao_ja_fechada(raiz, retratados, retratados_sha):
    """Id da pendência `retratacao_texto` que um humano fechou sobre os mesmos retratados, ou None.

    handoff.ja_confirmada_por_humano compara o sha256 de retratacoes.csv, que muda a cada execução por causa
    de `verificado_em`; aqui a comparação usa a assinatura dos resultados dos retratados (sem a data), gravada
    no evento `retratacoes_verificadas` que conviveu com a pendência (eventos antigos: a lista `retratados`).
    Só vale se não há pendência aberta do tipo, se a última fechada tem o mesmo n e foi fechada por humano.
    """
    est = estado.carregar_estado(raiz)
    mesmas = [p for p in est.get("pendencias", []) if p.get("tipo") == TIPO_PENDENCIA_RETRATACAO
              and (p.get("arquivo") or None) == ARQ_RETRATACOES]
    if not mesmas or any(p.get("status") != "fechada" for p in mesmas):
        return None
    ultima = mesmas[-1]
    if ultima.get("n") != len(retratados):
        return None
    eventos = estado.ler_log(raiz)
    fechamento = next((ev for ev in reversed(eventos) if ev.get("evento") == "pendencia_fechada"
                       and (ev.get("dados") or {}).get("pendencia") == ultima["id"]), None)
    if not fechamento or (fechamento.get("ator") or {}).get("tipo") != "humano":
        return None
    visto = next((ev.get("dados") or {} for ev in reversed(eventos) if ev.get("evento") == "retratacoes_verificadas"
                  and ultima["id"] in ((ev.get("dados") or {}).get("pendencia"),
                                       (ev.get("dados") or {}).get("pendencia_conferida"))), None)
    if visto is None:
        return None
    if visto.get("retratados_sha"):
        return ultima["id"] if visto["retratados_sha"] == retratados_sha else None
    return ultima["id"] if sorted(visto.get("retratados") or []) == sorted(retratados) else None


def cmd_retratacoes(args):
    comando = "textos retratacoes"
    raiz = exigir_raiz(args, comando)
    if raiz is None:
        return 1
    try:
        itens, universo, avisos = textos_para_retratacoes(raiz, resolver_caminho(raiz, args.ids) if args.ids else None)
    except ErroDependencia as e:
        return falhar(comando, str(e), codigo=3)
    except (FileNotFoundError, ValueError) as e:
        return falhar(comando, str(e))
    if not itens:
        return falhar(comando, "nenhum texto a verificar")
    linhas = verificar_retratacoes(itens, args.fonte, sessao=criar_sessao_http())
    verificados = [l for l in linhas if l["retratado"] in ("0", "1")]
    if not verificados and any(l["status"] == "erro" for l in linhas):
        return falhar(comando, "nenhuma consulta respondeu (rede ou API indisponível); nada foi gravado",
                      erros=sorted({l["openalex_is_retracted"] for l in linhas if l["status"] == "erro"})[:5])
    escrever_csv(raiz / ARQ_RETRATACOES, COLUNAS_RETRATACOES, linhas)
    retratados = [l["chave"] for l in linhas if l["retratado"] == "1"]
    preocupacao = [l["chave"] for l in linhas if l["_preocupacao"]]
    sem_verificacao = [l["chave"] for l in linhas if l["retratado"] == ""]
    resultados = [{k: v for k, v in l.items() if k in COLUNAS_RETRATACOES and k != "verificado_em"} for l in linhas]
    sha_resultados = estado.sha256_texto(json.dumps(resultados, ensure_ascii=False, sort_keys=True))
    # Assinatura estável do que a pendência trata (os retratados e o que as fontes disseram sobre eles), sem a
    # data da verificação: retratacoes.csv muda a cada dia (verificado_em) e não serve para comparar conteúdo.
    retratados_sha = estado.sha256_texto(json.dumps([r for r in resultados if r.get("retratado") == "1"],
                                                    ensure_ascii=False, sort_keys=True))
    anterior = _ultimo_evento(raiz, "retratacoes_verificadas")
    reexecucao = bool(anterior) and (anterior.get("dados") or {}).get("sha_resultados") == sha_resultados
    conferida = pendencia_retratacao_ja_fechada(raiz, retratados, retratados_sha) if retratados else None
    if conferida:
        pendencia = None  # um humano já fechou a pendência sobre exatamente estes retratados: não reabrir
    else:
        pendencia = sincronizar_pendencia_sempre(
            raiz, TIPO_PENDENCIA_RETRATACAO, "07_textos_elegibilidade", "G5",
            f"{len(retratados)} textos retratados ({', '.join(retratados[:10])}): excluir no texto completo com "
            "`triagem override --etapa tc` (retirar da síntese se já extraídos) e relatar",
            len(retratados), ARQ_RETRATACOES)
    if preocupacao:
        avisos.append(f"expressão de preocupação em {len(preocupacao)} textos ({', '.join(preocupacao[:10])}): "
                      "manter, sinalizar e prever análise de sensibilidade")
    if sem_verificacao:
        avisos.append(f"{len(sem_verificacao)} textos sem verificação (sem DOI/W id ou erro): conferir à mão no "
                      "Retraction Watch e no repositório de origem")
    # Toda execução é uma verificação datada (retratações aparecem com o tempo): o evento é sempre registrado.
    estado.registrar_evento(raiz, "retratacoes_verificadas", "07_textos_elegibilidade", "script", ATOR,
                            dados={"fonte": args.fonte, "universo": universo, "n": len(linhas),
                                   "n_verificados": len(verificados), "n_retratados": len(retratados),
                                   "retratados": retratados[:50], "n_expressao_preocupacao": len(preocupacao),
                                   "n_sem_verificacao": len(sem_verificacao), "pendencia": pendencia,
                                   "pendencia_conferida": conferida, "retratados_sha": retratados_sha,
                                   "sha_resultados": sha_resultados, "reexecucao": reexecucao},
                            artefatos=[ARQ_RETRATACOES])
    estado.resumo({"comando": comando, "ok": True, "reexecucao": reexecucao, "fonte": args.fonte,
                   "universo": universo, "n": len(linhas), "n_verificados": len(verificados),
                   "retratados": retratados, "expressao_preocupacao": preocupacao,
                   "sem_verificacao": sem_verificacao[:20], "pendencia": pendencia,
                   "conferencia_ja_feita": bool(conferida), "arquivo": ARQ_RETRATACOES, "avisos": avisos})
    return 0


# ---------------------------------------------------------------------------
# contato-autores
# ---------------------------------------------------------------------------
_DADOS_RECEBIDOS = {"sim": "sim", "s": "sim", "1": "sim", "true": "sim", "yes": "sim",
                    "nao": "nao", "n": "nao", "0": "nao", "false": "nao", "no": "nao",
                    "parcial": "parcial", "parcialmente": "parcial", "": ""}


def validar_contatos(raiz, caminho):
    """Linhas canônicas de contato com autores. ValueError com a lista de problemas."""
    try:
        colunas, linhas, avisos = ler_humana(caminho, COLUNAS_CONTATO_AUTORES)
    except ValueError as e:
        raise ValueError(f"{e} (use {','.join(COLUNAS_CONTATO_AUTORES)})") from None
    extras = [c for c in colunas if c not in COLUNAS_CONTATO_AUTORES]
    if extras:
        avisos.append(f"colunas fora do contrato descartadas da versão canônica: {extras}")
    chaves_projeto = {r["chave"].strip() for r in carregar_unicos(raiz).values() if r.get("chave", "").strip()}
    if not chaves_projeto:
        avisos.append(f"{esquema.ARQ_UNICOS} sem chaves: não deu para conferir as chaves dos contatos")
    erros, saida, vistos = [], [], set()
    for n, linha in enumerate(linhas, start=2):
        valores = {c: normalizar.texto(linha.get(c)) for c in COLUNAS_CONTATO_AUTORES}
        if not any(valores.values()):
            continue
        rotulo = f"linha {n} ({valores['chave'] or 'sem chave'})"
        if not valores["chave"]:
            erros.append(f"{rotulo}: chave vazia")
        elif chaves_projeto and valores["chave"] not in chaves_projeto:
            erros.append(f"{rotulo}: chave não existe no projeto")
        if not valores["autor_contatado"]:
            erros.append(f"{rotulo}: autor_contatado vazio (papel ou nome do autor, sem e-mail)")
        if any(_RE_EMAIL.search(v) for v in valores.values()):
            erros.append(f"{rotulo}: há endereço de e-mail; não guarde e-mails no projeto")
        try:
            _dt.date.fromisoformat(valores["data"])
        except ValueError:
            erros.append(f"{rotulo}: data {valores['data']!r} fora do formato AAAA-MM-DD")
        if not valores["pedido"]:
            erros.append(f"{rotulo}: pedido vazio (texto, dado ou esclarecimento pedido)")
        dados = _DADOS_RECEBIDOS.get(normalizar.ascii_fold(valores["dados_recebidos"]).lower())
        if dados is None:
            erros.append(f"{rotulo}: dados_recebidos {valores['dados_recebidos']!r} (use sim, nao, parcial ou vazio)")
        else:
            valores["dados_recebidos"] = dados
            if dados in ("sim", "parcial") and not valores["resposta"]:
                avisos.append(f"{rotulo}: dados recebidos sem resposta registrada")
        chave_linha = tuple(valores[c] for c in COLUNAS_CONTATO_AUTORES)
        if chave_linha in vistos:
            avisos.append(f"{rotulo}: linha repetida ignorada")
            continue
        vistos.add(chave_linha)
        saida.append(valores)
    if erros:
        raise ValueError("contato com autores inválido:\n  " + "\n  ".join(erros[:30]))
    if not saida:
        raise ValueError("nenhum contato no arquivo")
    saida.sort(key=lambda l: (l["chave"], l["data"], l["autor_contatado"]))
    return saida, avisos


def cmd_contato_autores(args):
    comando = "textos contato-autores"
    raiz = exigir_raiz(args, comando)
    if raiz is None:
        return 1
    origem = resolver_caminho(raiz, args.registrar or ARQ_CONTATO_AUTORES)
    if not origem.exists():
        return falhar(comando, f"arquivo não encontrado: {origem}")
    try:
        linhas, avisos = validar_contatos(raiz, origem)
    except ErroDependencia as e:
        return falhar(comando, str(e), codigo=3)
    except ValueError as e:
        return falhar(comando, str(e))
    escrever_csv(raiz / ARQ_CONTATO_AUTORES, COLUNAS_CONTATO_AUTORES, linhas)
    sha = estado.sha256_arquivo(raiz / ARQ_CONTATO_AUTORES)
    anterior = _ultimo_evento(raiz, "contato_autores")
    reexecucao = bool(anterior) and (anterior.get("dados") or {}).get("sha_contatos") == sha
    por_dados = {k: sum(1 for l in linhas if l["dados_recebidos"] == k) for k in ("sim", "parcial", "nao")}
    por_dados["aguardando"] = sum(1 for l in linhas if l["dados_recebidos"] == "")
    sem_resposta = sorted({l["chave"] for l in linhas if not l["resposta"]})
    dados = {"n_contatos": len(linhas), "n_textos": len({l["chave"] for l in linhas}),
             "n_com_resposta": sum(1 for l in linhas if l["resposta"]), "n_sem_resposta": len(sem_resposta),
             "dados_recebidos": por_dados, "chaves_sem_resposta": sem_resposta[:50], "sha_contatos": sha}
    if not reexecucao:
        artefatos = [ARQ_CONTATO_AUTORES]
        rel_origem = relativo(raiz, origem)
        if rel_origem != ARQ_CONTATO_AUTORES and not Path(rel_origem).is_absolute():
            artefatos.append(rel_origem)
        estado.registrar_evento(raiz, "contato_autores", "07_textos_elegibilidade", "script", ATOR, dados=dados,
                                artefatos=artefatos)
    estado.resumo({"comando": comando, "ok": True, "reexecucao": reexecucao, **{k: v for k, v in dados.items()
                                                                               if k != "sha_contatos"},
                   "arquivo": ARQ_CONTATO_AUTORES, "avisos": avisos})
    return 0


def registrar(subparsers):
    p = subparsers.add_parser("textos", help="textos completos: para-baixar, inventario, elegibilidade, ligar-relatos, "
                                             "retratacoes, contato-autores")
    sub = p.add_subparsers(dest="acao_textos", metavar="<ação>")

    q = sub.add_parser("para-baixar", help="incluídos/incertos da T/A -> 03-textos/para_baixar.csv")
    q.add_argument("--decisoes", default="incluir,incerto", help="decisões finais da T/A que seguem (padrão incluir,incerto)")
    q.add_argument("--ids", default=None, help="CSV com id_rs (projetos parciais, sem triagem consolidada)")
    q.set_defaults(func=cmd_para_baixar)

    q = sub.add_parser("inventario", help="PDFs: páginas, camada de texto e veredito de conteúdo")
    q.set_defaults(func=cmd_inventario)

    q = sub.add_parser("elegibilidade", help="elegibilidade em texto completo")
    sub_e = q.add_subparsers(dest="acao_elegibilidade", metavar="<ação>")
    c = sub_e.add_parser("consolidar", help="fichas + decisões humanas (override tc) -> 03-textos/elegibilidade_tc_final.csv")
    c.add_argument("--master", default=None,
                   help="fichamentos_master.csv do fichamento-sistematico (sem ele: só decisões humanas do ledger)")
    c.add_argument("--codebook", default=None, help="codebook de elegibilidade usado no fichamento (com --master)")
    c.add_argument("--criterios", default=None, help="lista explícita de variáveis-critério, em ordem")
    c.add_argument("--verificacao", default=None, help="verificacao_citacoes.csv do gate (reprovadas viram incerto)")
    c.set_defaults(func=cmd_elegibilidade_consolidar)
    q.set_defaults(func=lambda a, _p=q: (_p.print_help(), 1)[1])

    q = sub.add_parser("ligar-relatos", help="define id_estudo para relatos do mesmo estudo",
                       description="Acrescenta as ligações da lista às já registradas; as ligações de versão feitas "
                                   "pelo dedup (preprint e publicado) sempre ficam.")
    q.add_argument("--pares", required=True, help="CSV com id_rs_a,id_rs_b (acréscimo às ligações existentes)")
    q.add_argument("--substituir-manuais", action="store_true",
                   help="refaz só as ligações manuais: as antigas saem e valem as da lista (as de versão do dedup ficam)")
    q.set_defaults(func=cmd_ligar_relatos)

    q = sub.add_parser("retratacoes", help="retratações dos textos (OpenAlex is_retracted e avisos da Crossref)")
    q.add_argument("--fonte", choices=["openalex", "crossref", "ambas"], default="ambas",
                   help="fonte da consulta (padrão: ambas)")
    q.add_argument("--ids", default=None,
                   help="CSV com id_rs (padrão: não excluídos no texto completo; sem eles, para_baixar.csv)")
    q.set_defaults(func=cmd_retratacoes)

    q = sub.add_parser("contato-autores", help="valida e registra 03-textos/contato_autores.csv (evento contato_autores)")
    q.add_argument("--registrar", default=None,
                   help="CSV chave,autor_contatado,data,pedido,resposta,dados_recebidos (padrão: o arquivo canônico)")
    q.set_defaults(func=cmd_contato_autores)
    p.set_defaults(func=lambda a, _p=p: (_p.print_help(), 1)[1])
