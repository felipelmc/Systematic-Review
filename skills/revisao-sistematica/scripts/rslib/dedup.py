"""Deduplicação auditável: dados/registros.csv -> dados/registros_unicos.csv + 01-busca/dedup_pares.csv.

USO
    python3 rs.py dedup [--limiar-auto 95] [--limiar-candidato 85]
    python3 rs.py dedup --revisar 01-busca/dedup_pares.csv --por revisor_humano_1 [--tipo-ator humano]

POR QUE ASSIM
    O funil de exemplo do REFIS deduplicava só por DOI exato ou, na falta dele, por título
    limpo, sem cruzar DOI com título e sem trilha de auditoria; em projetos
    anteriores isso deixou passar pares preprint/publicado que humanos acharam
    depois. Aqui cada par avaliado vira uma linha de `dedup_pares.csv` com a
    regra, o escore e a decisão, e só as regras de alta precisão fundem sozinhas.

REGRAS (references/03-organizacao-triagem.md; Apêndice D da base de conhecimento,
"Identificadores e deduplicação" e item 3; ordem de precedência por par)
    R1_doi            DOI normalizado igual -> auto (inclui título traduzido com o mesmo DOI).
    R2_id_fonte       mesmo identificador da fonte (UT, EID, W..., PID) -> auto.
    versao            exatamente um lado é preprint ou working paper (prefixo de DOI
                      em esquema.PREFIXOS_PREPRINT ou tipo "preprint"), título
                      parecido e anos compatíveis -> NUNCA funde. São relatos
                      diferentes do mesmo estudo (em economia as versões costumam
                      diferir em amostra e estimativas): com escore >= limiar-auto e
                      mesmo sobrenome a decisão é `ligado` (os dois registros ficam
                      com id_rs próprios e recebem o mesmo id_estudo); senão
                      candidato a ligação. Cada relato segue para a triagem por conta
                      própria (a triagem continua sendo por relato).
    R3_titulo_exato   título normalizado igual + |Δano| <= 1 + sobrenome igual ou
                      ausente -> auto.
    R4_fuzzy_auto     similaridade >= limiar-auto + mesmo sobrenome + sem conflito de DOI -> auto.
    R5_candidato      similaridade entre os limiares, ou >= limiar-auto com conflito
                      (DOI diferente, sobrenome diferente/ausente, ano ausente) -> candidato.

    Bloqueios que nunca fundem (decisão "rejeitado", decidido_por "regra"):
      - tese/dissertação <-> artigo (ou outro tipo definido): são relatos
        diferentes do mesmo estudo e se ligam por `id_estudo` no texto completo;
      - títulos com marcadores de parte/volume/estudo diferentes ("Part I" x
        "Part II") ou que diferem em numerais.

    Blocagem: pares só são comparados se compartilham DOI, id da fonte, os 4
    primeiros caracteres do título (sem artigos iniciais) ou o sobrenome do
    primeiro autor; depois exige-se |Δano| <= 1 (<= 3 para versões).

CLUSTERS
    União (union-find) das arestas auto/confirmado, das mais fortes para as mais
    fracas. Uma aresta não é aplicada se juntaria no mesmo cluster uma tese e um
    artigo, os dois lados de um par rejeitado, ou dois DOIs publicados diferentes;
    nesses casos ela vira candidato com o motivo registrado (arestas R1 e
    confirmações humanas ignoram só o conflito de DOI).

IDS E CHAVES
    `id_rs` (RS0001...) é append-only: um cluster herda o id do cluster antigo com
    que mais se sobrepõe; ids absorvidos são aposentados e nunca reutilizados (o
    maior id emitido fica no log). `chave` (chave.gerar_chave) é gerada uma vez e
    preservada; o conjunto de chaves já emitidas, inclusive de ids aposentados,
    entra em `usadas`. `id_estudo` começa como `esquema.id_estudo_de(id_rs)`
    (RS0007 -> ES0007) e é preservado se já existir: a ligação de relatos
    (`textos ligar-relatos`) o altera e um novo dedup não pode desfazê-la.

LIGAÇÃO AUTOMÁTICA DE VERSÕES (preprint/working paper <-> publicado)
    Arestas `ligado` unem clusters (não registros) num mesmo estudo. A ligação
    automática não junta dois clusters publicados no mesmo estudo nem os dois lados
    de um par de versão rejeitado por humano; nesses casos vira candidato com o
    motivo. O resultado vai para `03-textos/ligacao_relatos.csv` e para a coluna
    `id_estudo` pela MESMA função de `textos ligar-relatos` (textos.ligar_relatos:
    o grupo recebe o id_estudo do relato de menor id_rs). As ligações que já estavam
    no arquivo e não vieram do dedup (as de `textos ligar-relatos`) são preservadas:
    se o arquivo não mudou desde o último dedup, valem os pares preservados gravados
    no evento dedup_executado (`dados.ligacao_relatos`); se mudou, os grupos do
    arquivo contam como ligações humanas, menos os pares que o último dedup ligou como
    versão. Uma ligação de versão rejeitada depois (`--revisar` com decisao=rejeitado)
    é desfeita na mesma execução.
    `pares_versao_ligados(raiz)` devolve os pares id_rs ligados por versão, para quem
    precisar reaplicá-los (ex.: uma nova rodada de `textos ligar-relatos`).

MESCLAGEM
    Representante = não preprint, depois prioridade de fonte
    (esquema.PRIORIDADE_FONTES), depois id_registro. Campos vêm do representante,
    completados pelos demais na mesma ordem; resumo = o mais longo não truncado;
    citado_por = máximo; palavras-chave e estrutura = união.

DECISÕES HUMANAS
    `--revisar` lê um CSV com id_a, id_b, decisao (confirmado|rejeitado|ligado)
    [, decidido_por, motivo] — em geral o próprio dedup_pares.csv editado —,
    registra as decisões novas no log (evento dedup_revisado, que é a fonte de
    verdade delas) e refaz os clusters. Quem decidiu é obrigatório: a coluna
    decidido_por preenchida ou `--por <papel>` (ex.: --por revisor_humano_1,
    esquema.PAPEL_HUMANO_PADRAO); sem nenhum dos dois o comando recusa. Num par de
    regra `versao`, `confirmado` e `ligado` significam ligar os relatos (nunca
    fundir); `ligado` só vale para pares de versão (outros relatos do mesmo estudo
    se ligam em `textos ligar-relatos`). Candidatos pendentes abrem uma pendência
    no autopiloto ou aparecem no resumo em checkpoints.

IDS ABSORVIDOS DEPOIS DA TRIAGEM
    Uma fusão aplicada depois da triagem aposenta ids que já têm decisão no ledger,
    em triagem_ta_final.csv e, às vezes, em elegibilidade_tc_final.csv. O dedup não
    mexe nessas decisões: registra `n_absorvidos` e `n_absorvidos_com_triagem` no
    evento e avisa para rodar `filtrar`, `triagem consolidar` e, se for o caso,
    `textos elegibilidade consolidar` antes do `prisma`. `mapa_absorvidos(raiz)` e
    `chaves_absorvidas(raiz)` dão o destino de cada id ou chave aposentado (cadeia
    seguida, todos os eventos dedup_executado); a consolidação leva a decisão ao
    registro que absorveu, e o PRISMA acusa ids absorvidos ainda presentes nos
    arquivos finais (references/03-organizacao-triagem.md, seção 3).

CANDIDATOS PENDENTES
    Um candidato cujo par já ficou no mesmo cluster (ou estudo, em versões) por outras
    arestas continua com decisao=candidato em dedup_pares.csv, com a marca
    `resolvido_transitivamente` no motivo, e não conta como pendente. O resumo e o log
    trazem `candidatos_pendentes` (os que pedem revisão; é o n da pendência
    dedup_candidatos) e `candidatos_resolvidos_transitivamente`; quem conta pelo arquivo
    usa `contar_candidatos_pendentes(raiz)`.

REEXECUÇÃO
    Sem mudança em registros_unicos.csv, dedup_pares.csv e ligacao_relatos.csv, sem
    decisão humana nova e com os mesmos parâmetros do último dedup_executado, o
    comando não grava outro evento (resumo com `reexecucao: true`), para não encher
    o log nem desatualizar a declaração de uso de IA.

    Similaridade: rapidfuzz.fuzz.ratio se instalado; senão difflib (mais lento,
    escores ligeiramente diferentes; o backend usado vai para o log).

BUSCAS SUBSTITUÍDAS (estado["buscas"][i]["ativa"] == false; `importar --substituir`)
    Os registros dessas buscas continuam em registros.csv, mas o dedup os ignora:
    não entram em pares, clusters nem contagens (`n_registros` conta só os ativos;
    `n_registros_inativos` vai para o log). Consequências, nesta ordem:
      - um cluster antigo com membros ativos e inativos perde os inativos e mantém
        o id_rs (o casamento de ids usa só os membros ativos, então nenhum id_rs que
        continua é reatribuído);
      - um cluster antigo que só tinha registros inativos NÃO é apagado nem
        aposentado: a linha fica em registros_unicos.csv exatamente como estava
        (id_rs, chave, id_estudo, ids_registro, metadados), com a flag
        `busca_inativa` acrescentada. Ela fica fora do conjunto ativo: `filtrar` e
        `bola-de-neve` a ignoram e `prisma`/triagem devem ignorá-la. Decisões de
        triagem já tomadas sobre esse id_rs continuam resolvíveis no ledger;
      - um registro da busca nova igual a um cluster inativo vira cluster novo
        (id_rs novo) e precisa ser triado. Quando o DOI ou o id da fonte coincide com
        um cluster inativo que já tinha decisão de triagem (dados/decisoes.jsonl), há um
        aviso por cluster (a decisão não é herdada); sem decisão a herdar, um só aviso
        agregado com a contagem e exemplos;
      - decisões humanas (dedup_revisado) que envolvem registros inativos ficam no
        log e não são aplicadas;
      - o id_rs de um cluster inativo nunca é reutilizado (entra no maior id emitido).

FLAGS DA FONTE
    `dados/registros_flags.csv` (gravado pelo importador; ver importar/flags.py)
    marca registros por id_registro. Hoje a flag é `retratado` (OpenAlex
    `is_retracted`): um cluster com ao menos um membro marcado recebe `retratado`,
    além da detecção por texto no título/tipo. Outras flags da tabela são
    acrescentadas em ordem alfabética.
"""

import csv
import difflib
import io
import re
import sys
from pathlib import Path

from . import chave as _chave
from . import esquema, estado, normalizar
from .handoff import sincronizar_pendencia_unica
from .importar import buscas as _buscas
from .importar import flags as _flags

try:  # opcional: acelera e padroniza o escore; sem ele cai para difflib
    from rapidfuzz import fuzz as _fuzz
    BACKEND_FUZZY = "rapidfuzz"
except ImportError:  # pragma: no cover - depende do ambiente
    _fuzz = None
    BACKEND_FUZZY = "difflib"

ETAPA = "05_organizacao"
TIPO_PENDENCIA = "dedup_candidatos"
TIPOS_TESE = {"tese", "dissertacao"}
TIPOS_INDEFINIDOS = {"", "outro"}
_ARTIGOS_INICIAIS = {"the", "a", "an", "o", "os", "as", "um", "uma", "el", "la", "los", "las", "le", "les", "un", "una"}
_ID_RS = re.compile(r"^RS(\d+)$")
# Romanos de uma letra ficam de fora ("I", "V", "X" também são palavras); "Part I" já
# é coberto por normalizar.marcador_parte.
_ROMANOS = {"ii", "iii", "iv", "vi", "vii", "viii", "ix", "xi", "xii"}
# Ordem de aplicação das arestas na união: regras mais confiáveis primeiro (versões não fundem).
_ORDEM_ARESTAS = {"R1_doi": 0, "R2_id_fonte": 1, "confirmado": 2, "R3_titulo_exato": 4, "R4_fuzzy_auto": 5}
# Decisão de par de versão (preprint/WP <-> publicado): relatos ligados por id_estudo, sem fusão.
# Em esquema.py desde a v1.3 (DECISAO_LIGADO dentro de DECISOES_DEDUP); nomes antigos mantidos como aliases.
DECISAO_LIGADO = esquema.DECISAO_LIGADO
DECISOES_PARES = list(dict.fromkeys(list(esquema.DECISOES_DEDUP) + [DECISAO_LIGADO]))
MOTIVO_VERSAO_LIGADA = esquema.MOTIVO_VERSAO_LIGADA  # motivo exato da ligação automática (candidatos acrescentam as faltas)
MARCA_RESOLVIDO = esquema.MARCA_RESOLVIDO_TRANSITIVAMENTE
DECISOES_HUMANAS = {"confirmado", "rejeitado", DECISAO_LIGADO}
AUTORES_AUTOMATICOS = {"", "script", "regra"}
PAPEL_HUMANO_PADRAO = esquema.PAPEL_HUMANO_PADRAO
FLAG_BUSCA_INATIVA = esquema.FLAG_BUSCA_INATIVA
_ORDEM_FLAGS = ["sem_resumo", "preprint", "retratado", "autores_ambiguos"]


class ErroDedup(RuntimeError):
    """Erro de uso ou de dados (código de saída 1)."""


# ---------------------------------------------------------------------------
# E/S de CSV (UTF-8, vírgula, cabeçalho exato; escrita atômica)
# ---------------------------------------------------------------------------
def ler_csv(caminho):
    """Lê CSV como lista de dicts de strings. Aceita BOM, que planilhas costumam inserir."""
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)
        linhas = [{k: (v if v is not None else "") for k, v in linha.items() if k is not None} for linha in leitor]
        return list(leitor.fieldnames or []), linhas


def _texto_csv(colunas, linhas):
    buf = io.StringIO()
    escritor = csv.DictWriter(buf, fieldnames=colunas, extrasaction="ignore", lineterminator="\n")
    escritor.writeheader()
    for linha in linhas:
        escritor.writerow({c: linha.get(c, "") for c in colunas})
    return buf.getvalue()


def escrever_csv(caminho, colunas, linhas):
    """Grava de forma atômica e só se o conteúdo mudou. Devolve True se escreveu.

    Comparar o texto antes de gravar mantém o sha256 dos artefatos estável em
    reexecuções, o que é o que `status` usa para detectar alterações.
    """
    caminho = Path(caminho)
    novo = _texto_csv(colunas, linhas)
    if caminho.exists() and caminho.read_bytes() == novo.encode("utf-8"):
        return False
    estado.escrever_atomico(caminho, novo, newline="")  # 0666 menos a umask (coautores leem a pasta compartilhada)
    return True


# ---------------------------------------------------------------------------
# Atributos derivados de cada registro
# ---------------------------------------------------------------------------
def similaridade(a, b):
    """Escore 0–100 entre títulos já normalizados."""
    if not a or not b:
        return 0.0
    if a == b:
        return 100.0
    if _fuzz is not None:
        return round(float(_fuzz.ratio(a, b)), 1)
    return round(difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() * 100, 1)


def _sobrenome_norm(linha):
    sob = normalizar.texto(linha.get("primeiro_autor_sobrenome")) or normalizar.sobrenome_primeiro_autor(linha.get("autores"))
    if not sob:
        return ""
    n = _chave.normalizar(sob)
    return "" if n == "Anon" else n.lower()


def eh_preprint(tipo, doi):
    return tipo == "preprint" or any(doi.startswith(p + "/") for p in esquema.PREFIXOS_PREPRINT)


def _numerais(tokens):
    return sorted(t for t in tokens if t.isdigit() or t in _ROMANOS)


class Info:
    """Registro com os campos de comparação pré-calculados (evita renormalizar em cada par)."""

    __slots__ = ("idx", "id", "linha", "doi", "chave_idf", "tn", "tokens", "ano", "sob", "tipo",
                 "preprint", "tese", "tipo_definido", "partes", "numerais", "prioridade", "bloco_titulo")

    def __init__(self, idx, linha):
        self.idx = idx
        self.linha = linha
        self.id = linha["id_registro"]
        self.doi = normalizar.doi(linha.get("doi"))
        idf = normalizar.texto(linha.get("id_fonte")).lower()
        fonte = normalizar.texto(linha.get("fonte")).lower()
        # Ids só numéricos (ex.: CAPES) podem coincidir entre fontes; nesses casos a fonte entra na chave.
        self.chave_idf = "" if not idf else (f"{fonte}:{idf}" if idf.isdigit() else idf)
        self.tn = normalizar.titulo_normalizado(linha.get("titulo"))
        self.tokens = self.tn.split()
        ano = normalizar.ano(linha.get("ano"))
        self.ano = int(ano) if ano else None
        self.sob = _sobrenome_norm(linha)
        self.tipo = normalizar.texto(linha.get("tipo_publicacao")).lower()
        self.preprint = eh_preprint(self.tipo, self.doi)
        self.tese = self.tipo in TIPOS_TESE
        self.tipo_definido = self.tipo not in TIPOS_INDEFINIDOS
        self.partes = normalizar.marcador_parte(linha.get("titulo"))
        self.numerais = _numerais(self.tokens)
        try:
            self.prioridade = esquema.PRIORIDADE_FONTES.index(fonte)
        except ValueError:
            self.prioridade = len(esquema.PRIORIDADE_FONTES)
        tokens = list(self.tokens)
        while len(tokens) > 1 and tokens[0] in _ARTIGOS_INICIAIS:
            tokens.pop(0)
        self.bloco_titulo = "".join(tokens)[:4]


def _tese_x_artigo(a, b):
    return (a.tese and b.tipo_definido and not b.tese) or (b.tese and a.tipo_definido and not a.tese)


# ---------------------------------------------------------------------------
# Pares
# ---------------------------------------------------------------------------
JANELA_ANOS = 1
JANELA_ANOS_VERSAO = 3


def pares_candidatos(infos):
    """Pares (i, j) que compartilham uma chave de bloco.

    Blocos por DOI e id da fonte comparam todos os membros (R1/R2 não dependem do
    ano). Blocos por início do título e por sobrenome só comparam registros com
    |Δano| <= 1, ou <= 3 quando exatamente um é preprint; registros sem ano são
    comparados com todos do bloco. Sem essa janela, sobrenomes comuns (Silva,
    Santos) geram blocos quadráticos que tornam o fallback difflib inviável.
    """
    blocos = {}
    for info in infos:
        chaves = []
        if info.doi:
            chaves.append(("doi", info.doi))
        if info.chave_idf:
            chaves.append(("idf", info.chave_idf))
        if len(info.bloco_titulo) >= 4:
            chaves.append(("t4", info.bloco_titulo))
        if info.sob:
            chaves.append(("sob", info.sob))
        for k in chaves:
            blocos.setdefault(k, []).append(info.idx)
    pares = set()

    def somar(i, j):
        pares.add((i, j) if i < j else (j, i))

    for (tipo_bloco, _), membros in blocos.items():
        if len(membros) < 2:
            continue
        if tipo_bloco in ("doi", "idf"):
            for p, i in enumerate(membros):
                for j in membros[p + 1:]:
                    somar(i, j)
            continue
        sem_ano = [m for m in membros if infos[m].ano is None]
        com_ano = sorted((m for m in membros if infos[m].ano is not None), key=lambda m: infos[m].ano)
        for p, i in enumerate(sem_ano):
            for j in sem_ano[p + 1:] + com_ano:
                somar(i, j)
        for p, i in enumerate(com_ano):
            a = infos[i]
            for j in com_ano[p + 1:]:
                b = infos[j]
                delta = b.ano - a.ano
                if delta > JANELA_ANOS_VERSAO:
                    break
                if delta <= JANELA_ANOS or a.preprint != b.preprint:
                    somar(i, j)
    return sorted(pares)


def _linha_par(a, b, regra, score, decisao, decidido_por, motivo):
    if b.id < a.id:
        a, b = b, a
    return {
        "id_a": a.id, "id_b": b.id, "regra": regra, "score": f"{score:.1f}",
        "ano_a": a.ano or "", "ano_b": b.ano or "", "sobrenome_a": a.sob, "sobrenome_b": b.sob,
        "doi_a": a.doi, "doi_b": b.doi, "decisao": decisao, "decidido_por": decidido_por, "motivo": motivo,
    }


def classificar_par(a, b, limiar_auto, limiar_candidato):
    """Aplica R1–R5/versão e os bloqueios a um par. Devolve a linha de dedup_pares ou None."""
    bloqueio = "tese_artigo_nunca_funde" if _tese_x_artigo(a, b) else ""
    mesmo_doi = bool(a.doi) and a.doi == b.doi
    mesmo_idf = bool(a.chave_idf) and a.chave_idf == b.chave_idf
    if not (mesmo_doi or mesmo_idf):
        # Poda barata: a razão de similaridade nunca passa de 2·min/(la+lb).
        la, lb = len(a.tn), len(b.tn)
        if not la or not lb or 200.0 * min(la, lb) / (la + lb) < limiar_candidato:
            return None
    score = similaridade(a.tn, b.tn)

    if mesmo_doi:
        regra, decisao, motivo = "R1_doi", "auto", "doi_igual"
    elif mesmo_idf:
        regra, decisao, motivo = "R2_id_fonte", "auto", "id_fonte_igual"
    else:
        if score < limiar_candidato:
            return None
        if not bloqueio and (a.partes != b.partes or a.numerais != b.numerais):
            bloqueio = "marcador_parte_ou_numeral_diferente"
        mesmo_sob = bool(a.sob) and a.sob == b.sob
        anos = a.ano is not None and b.ano is not None
        conflito_doi = bool(a.doi and b.doi and a.doi != b.doi)
        if a.preprint != b.preprint:
            pre, pub = (a, b) if a.preprint else (b, a)
            if anos and not (-1 <= pub.ano - pre.ano <= 3):
                return None
            regra = "versao"
            if score >= limiar_auto and mesmo_sob and anos:
                decisao, motivo = DECISAO_LIGADO, MOTIVO_VERSAO_LIGADA
            else:
                faltas = [m for m, ok in (("escore_abaixo_do_auto", score >= limiar_auto),
                                          ("sobrenome_diferente_ou_ausente", mesmo_sob),
                                          ("ano_ausente", anos)) if not ok]
                decisao, motivo = "candidato", "preprint_publicado;" + ",".join(faltas)
        else:
            if anos and abs(a.ano - b.ano) > 1:
                return None
            sob_compativel = mesmo_sob or not a.sob or not b.sob
            if a.tn == b.tn and len(a.tokens) >= 3 and anos and sob_compativel:
                regra, decisao, motivo = "R3_titulo_exato", "auto", "titulo_igual"
            elif score >= limiar_auto and anos and mesmo_sob and not conflito_doi:
                regra, decisao, motivo = "R4_fuzzy_auto", "auto", "titulo_similar"
            else:
                faltas = []
                if score < limiar_auto:
                    faltas.append("escore_entre_limiares")
                if a.tn == b.tn and len(a.tokens) < 3:
                    faltas.append("titulo_curto")
                if not anos:
                    faltas.append("ano_ausente")
                if conflito_doi:
                    faltas.append("doi_diferente")
                if not mesmo_sob:
                    faltas.append("sobrenome_diferente_ou_ausente")
                regra, decisao, motivo = "R5_candidato", "candidato", ",".join(faltas) or "revisar"
    if bloqueio:
        return _linha_par(a, b, regra, score, "rejeitado", "regra", bloqueio)
    return _linha_par(a, b, regra, score, decisao, "script", motivo)


def gerar_pares(infos, limiar_auto, limiar_candidato):
    pares = {}
    for i, j in pares_candidatos(infos):
        linha = classificar_par(infos[i], infos[j], limiar_auto, limiar_candidato)
        if linha:
            pares[(linha["id_a"], linha["id_b"])] = linha
    return pares


# ---------------------------------------------------------------------------
# Decisões humanas
# ---------------------------------------------------------------------------
def decisoes_do_log(raiz):
    """Decisões humanas vigentes, reconstruídas dos eventos dedup_revisado (a última vence)."""
    vigentes = {}
    for ev in estado.ler_log(raiz):
        if ev.get("evento") != "dedup_revisado":
            continue
        for d in (ev.get("dados") or {}).get("decisoes", []):
            a, b = sorted([d["id_a"], d["id_b"]])
            vigentes[(a, b)] = {"decisao": d["decisao"], "decidido_por": d.get("decidido_por") or "",
                                "motivo": d.get("motivo") or ""}
    return vigentes


def ler_revisao(caminho, ids_validos, por_padrao=None):
    """Lê o CSV de revisão. Linhas com decisão auto/candidato/vazia são ignoradas (não decididas).

    Quem decidiu vem de `decidido_por` (valores de script/regra não contam) ou de `por_padrao`
    (`--por`); decisão sem nenhum dos dois é recusada, para não atribuir um papel humano sem
    declaração explícita.
    """
    cabecalho, linhas = ler_csv(caminho)
    faltando = {"id_a", "id_b", "decisao"} - set(cabecalho)
    if faltando:
        raise ErroDedup(f"{caminho}: colunas ausentes {sorted(faltando)}")
    por_padrao = normalizar.texto(por_padrao)
    decisoes, sem_autor = {}, []
    for n, linha in enumerate(linhas, start=2):
        decisao = normalizar.texto(linha.get("decisao")).lower()
        quem = normalizar.texto(linha.get("decidido_por"))
        if decisao not in DECISOES_HUMANAS:
            if decisao and decisao not in DECISOES_PARES:
                raise ErroDedup(f"{caminho}:{n}: decisão inválida '{decisao}' (use confirmado|rejeitado|ligado)")
            continue
        if decisao == "rejeitado" and quem == "regra":
            continue  # bloqueio automático copiado do próprio dedup_pares.csv, não é decisão humana
        if decisao == DECISAO_LIGADO and quem in {"", "script"} and normalizar.texto(linha.get("regra")) == "versao" \
                and normalizar.texto(linha.get("motivo")) == MOTIVO_VERSAO_LIGADA:
            continue  # ligação automática de versão copiada do próprio dedup_pares.csv (o script só grava este motivo)
        a, b = normalizar.texto(linha.get("id_a")), normalizar.texto(linha.get("id_b"))
        for i in (a, b):
            if i not in ids_validos:
                raise ErroDedup(f"{caminho}:{n}: id_registro desconhecido '{i}'")
        if a == b:
            raise ErroDedup(f"{caminho}:{n}: par com o mesmo registro nos dois lados")
        a, b = sorted([a, b])
        if quem in AUTORES_AUTOMATICOS:
            quem = por_padrao
        if not quem:
            sem_autor.append(n)
            continue
        decisoes[(a, b)] = {"decisao": decisao, "decidido_por": quem, "motivo": normalizar.texto(linha.get("motivo"))}
    if sem_autor:
        linhas_txt = ", ".join(map(str, sem_autor[:10])) + ("..." if len(sem_autor) > 10 else "")
        raise ErroDedup(f"{caminho}: {len(sem_autor)} decisão(ões) sem quem decidiu (linhas {linhas_txt}). Preencha a "
                        f"coluna decidido_por ou rode com --por <papel> (ex.: --por {PAPEL_HUMANO_PADRAO}); "
                        "nada foi gravado")
    return decisoes


def _mesma_decisao(registrada, lida):
    """Decisão lida da planilha igual à vigente no log.

    O dedup regrava um `confirmado` humano de par de versão como `ligado` (mesmo efeito); reler a planilha
    regravada não pode virar decisão nova.
    """
    return registrada == lida or (registrada == "confirmado" and lida == DECISAO_LIGADO)


def aplicar_decisoes(pares, humanas, infos_por_id):
    """Sobrepõe decisões humanas às automáticas. Devolve avisos de confirmações recusadas.

    Em pares de versão, `confirmado` e `ligado` viram `ligado` (relatos do mesmo estudo, sem fusão).
    """
    avisos = []
    for (a, b), d in sorted(humanas.items()):
        linha = pares.get((a, b))
        if linha is None:  # par indicado por humano que o algoritmo não gerou
            ia, ib = infos_por_id[a], infos_por_id[b]
            regra = "versao" if ia.preprint != ib.preprint else "R5_candidato"
            linha = _linha_par(ia, ib, regra, similaridade(ia.tn, ib.tn), "candidato", "script",
                               "par_indicado_na_revisao")
            if _tese_x_artigo(ia, ib):
                linha.update(decisao="rejeitado", decidido_por="regra", motivo="tese_artigo_nunca_funde")
            pares[(a, b)] = linha
        decisao = d["decisao"]
        versao = linha["regra"] == "versao"
        if decisao == DECISAO_LIGADO and not versao:
            avisos.append(f"{a}~{b}: decisão 'ligado' ignorada (só vale para pares de versão preprint/publicado); "
                          "ligue outros relatos do mesmo estudo com `rs.py textos ligar-relatos`")
            continue
        if decisao in {"confirmado", DECISAO_LIGADO} and linha["decidido_por"] == "regra":
            avisos.append(f"{a}~{b}: confirmação recusada ({linha['motivo']}); ligue relatos por id_estudo "
                          "(`rs.py textos ligar-relatos`)")
            continue
        if versao and decisao == "confirmado":
            decisao = DECISAO_LIGADO  # versões nunca fundem: confirmar = ligar os relatos
        linha.update(decisao=decisao, decidido_por=d["decidido_por"],
                     motivo=d["motivo"] or f"revisao_humana;{linha['motivo']}")
    return avisos


# ---------------------------------------------------------------------------
# Clusters
# ---------------------------------------------------------------------------
class _Cluster:
    __slots__ = ("membros", "dois", "tem_tese", "tem_nao_tese")

    def __init__(self, info):
        self.membros = {info.id}
        self.dois = {info.doi} if info.doi and not info.preprint else set()
        self.tem_tese = info.tese
        self.tem_nao_tese = info.tipo_definido and not info.tese


def agrupar(infos, pares):
    """Union-find com restrições. Altera linhas de pares bloqueadas; devolve (clusters, avisos)."""
    pai = {i.id: i.id for i in infos}
    grupos = {i.id: _Cluster(i) for i in infos}
    proibidos = {}
    for (a, b), linha in pares.items():
        if linha["decisao"] == "rejeitado":
            proibidos.setdefault(a, set()).add(b)
            proibidos.setdefault(b, set()).add(a)

    def achar(x):
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    arestas = []
    for chave_par, linha in pares.items():
        if linha["decisao"] == "auto":
            arestas.append((_ORDEM_ARESTAS[linha["regra"]], chave_par))
        elif linha["decisao"] == "confirmado":
            arestas.append((_ORDEM_ARESTAS["confirmado"], chave_par))
    avisos = []
    for _, (a, b) in sorted(arestas):
        linha = pares[(a, b)]
        ra, rb = achar(a), achar(b)
        if ra == rb:
            continue
        x, y = grupos[ra], grupos[rb]
        motivo = ""
        if (x.tem_tese and y.tem_nao_tese) or (y.tem_tese and x.tem_nao_tese):
            motivo = "juntaria_tese_e_artigo_no_cluster"
        elif any(proibidos.get(m, set()) & y.membros for m in x.membros):
            motivo = "juntaria_par_rejeitado_no_cluster"
        elif linha["regra"] != "R1_doi" and linha["decisao"] != "confirmado" and len(x.dois | y.dois) > 1:
            motivo = "conflito_doi_no_cluster"
        if motivo:
            if linha["decisao"] == "confirmado":
                avisos.append(f"{a}~{b}: confirmação não aplicada ({motivo})")
                linha["motivo"] = f"nao_aplicado:{motivo};{linha['motivo']}"
            else:
                linha.update(decisao="candidato", decidido_por="script", motivo=f"{motivo};{linha['motivo']}")
            continue
        pai[rb] = ra
        x.membros |= y.membros
        x.dois |= y.dois
        x.tem_tese = x.tem_tese or y.tem_tese
        x.tem_nao_tese = x.tem_nao_tese or y.tem_nao_tese
        del grupos[rb]
    clusters = {}
    for info in infos:
        clusters.setdefault(achar(info.id), []).append(info)
    lista = [sorted(m, key=lambda i: i.id) for m in clusters.values()]
    lista.sort(key=lambda m: m[0].id)
    return lista, avisos, achar


def ligar_versoes(infos, pares, achar):
    """União das arestas `ligado` entre clusters (relatos do mesmo estudo, sem fusão).

    Altera linhas de pares bloqueadas; devolve (estudo_de: raiz do cluster -> raiz do estudo, arestas
    aplicadas [(raiz_a, raiz_b)], avisos). A ligação automática (decidido_por script) não junta dois clusters
    publicados no mesmo estudo; nenhuma ligação junta os dois lados de um par de versão rejeitado por humano.
    """
    publicados = {}
    for info in infos:
        r = achar(info.id)
        publicados[r] = publicados.get(r, 0) or (0 if info.preprint else 1)
    pai = {r: r for r in publicados}
    n_pub = dict(publicados)
    membros = {r: {r} for r in publicados}

    def estudo(x):
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    proibidos = {}
    for (a, b), linha in pares.items():
        if linha["regra"] == "versao" and linha["decisao"] == "rejeitado" and linha["decidido_por"] != "regra":
            ra, rb = achar(a), achar(b)
            proibidos.setdefault(ra, set()).add(rb)
            proibidos.setdefault(rb, set()).add(ra)
    arestas = sorted(((linha["decidido_por"] in AUTORES_AUTOMATICOS, chave_par) for chave_par, linha in pares.items()
                      if linha["decisao"] == DECISAO_LIGADO))
    aplicadas, avisos = [], []
    for automatica, (a, b) in arestas:  # humanas primeiro
        linha = pares[(a, b)]
        ra, rb = achar(a), achar(b)
        if ra == rb:
            continue  # fundidos por outra regra (mesmo DOI, mesmo id da fonte)
        ea, eb = estudo(ra), estudo(rb)
        if ea == eb:
            continue
        motivo = ""
        if any(proibidos.get(m, set()) & membros[eb] for m in membros[ea]):
            motivo = "juntaria_versao_rejeitada_no_estudo"
        elif automatica and n_pub[ea] + n_pub[eb] > 1:
            motivo = "ligaria_dois_publicados_no_estudo"
        if motivo:
            if automatica:
                linha.update(decisao="candidato", decidido_por="script", motivo=f"{motivo};{linha['motivo']}")
            else:
                avisos.append(f"{a}~{b}: ligação não aplicada ({motivo})")
                linha["motivo"] = f"nao_aplicado:{motivo};{linha['motivo']}"
            continue
        pai[eb] = ea
        n_pub[ea] += n_pub[eb]
        membros[ea] |= membros.pop(eb)
        aplicadas.append((ra, rb))
    return {r: estudo(r) for r in publicados}, aplicadas, avisos


# ---------------------------------------------------------------------------
# Mesclagem e ids estáveis
# ---------------------------------------------------------------------------
def _ordenar_membros(membros):
    return sorted(membros, key=lambda i: (i.preprint, i.prioridade, i.id))


def _primeiro(ordem, campo):
    for info in ordem:
        v = normalizar.texto(info.linha.get(campo))
        if v:
            return v
    return ""


def _uniao(ordem, campo, separador_leitura, separador_escrita):
    vistos, saida = set(), []
    for info in ordem:
        for parte in re.split(separador_leitura, normalizar.texto(info.linha.get(campo))):
            parte = parte.strip()
            if parte and parte.lower() not in vistos:
                vistos.add(parte.lower())
                saida.append(parte)
    return separador_escrita.join(saida)


def regras_por_cluster(pares, achar):
    """Regras das arestas efetivamente aplicadas, agrupadas pela raiz do cluster."""
    regras = {}
    for (a, b), linha in pares.items():
        if linha["decisao"] in {"auto", "confirmado"} and achar(a) == achar(b) \
                and not linha["motivo"].startswith("nao_aplicado:"):
            regras.setdefault(achar(a), set()).add("confirmado" if linha["decisao"] == "confirmado" else linha["regra"])
    return regras


def _tipo_duplicata(membros, regras):
    """versao > fuzzy (R4 ou confirmação humana de candidato) > exato (R1–R3)."""
    if len(membros) == 1:
        return "unico"
    if "versao" in regras:
        return "versao"
    if regras & {"R4_fuzzy_auto", "confirmado"}:
        return "fuzzy"
    return "exato"


def mesclar(membros, tipo_duplicata, limiar_titulo_alt=85.0, flags_registro=None):
    """Linha de registros_unicos (sem id_rs/id_estudo/chave) a partir dos registros de um cluster.

    `flags_registro`: {id_registro: {flag}} de dados/registros_flags.csv (ex.: retratado pela fonte).
    """
    ordem = _ordenar_membros(membros)
    rep = ordem[0]
    linha = {c: "" for c in esquema.COLUNAS_UNICOS}
    campos_bibliograficos = esquema.COLUNAS_UNICOS[esquema.COLUNAS_UNICOS.index("flags") + 1:]
    campos_individuais = [c for c in campos_bibliograficos
                          if c not in {"autores", "primeiro_autor_sobrenome", "n_autores", "veiculo", "volume",
                                       "numero", "paginas", "resumo", "resumo_truncado", "palavras_chave",
                                       "citado_por", "estrutura", "metodo_identificacao", "titulo_alt"}]
    for campo in campos_individuais:
        linha[campo] = _primeiro(ordem, campo)
    linha["doi"] = next((i.doi for i in ordem if i.doi and not i.preprint), "") or next((i.doi for i in ordem if i.doi), "")
    # Campos que precisam vir juntos do mesmo registro para não misturar citações.
    for grupo in (("autores", "primeiro_autor_sobrenome", "n_autores"), ("veiculo", "volume", "numero", "paginas")):
        origem = next((i for i in ordem if normalizar.texto(i.linha.get(grupo[0]))), None)
        for campo in grupo:
            linha[campo] = normalizar.texto(origem.linha.get(campo)) if origem else ""
    if not linha["primeiro_autor_sobrenome"] and linha["autores"]:
        linha["primeiro_autor_sobrenome"] = normalizar.sobrenome_primeiro_autor(linha["autores"])
    resumos = [i for i in ordem if normalizar.texto(i.linha.get("resumo"))]
    if resumos:
        melhor = min(resumos, key=lambda i: (normalizar.texto(i.linha.get("resumo_truncado")) == "1",
                                             -len(normalizar.texto(i.linha.get("resumo")))))
        linha["resumo"] = normalizar.texto(melhor.linha.get("resumo"))
        linha["resumo_truncado"] = "1" if normalizar.texto(melhor.linha.get("resumo_truncado")) == "1" else "0"
    citacoes = [int(float(v)) for v in (normalizar.texto(i.linha.get("citado_por")) for i in ordem)
                if re.fullmatch(r"\d+(\.0+)?", v)]
    linha["citado_por"] = str(max(citacoes)) if citacoes else ""
    linha["palavras_chave"] = _uniao(ordem, "palavras_chave", r";", "; ")
    linha["estrutura"] = _uniao(ordem, "estrutura", r"\|", "|")
    metodos = [normalizar.texto(i.linha.get("metodo_identificacao")) for i in ordem]
    # No PRISMA, um registro achado em base e por outro método conta no ramo das bases.
    linha["metodo_identificacao"] = "base" if "base" in metodos else next((m for m in metodos if m), "")
    linha["titulo_alt"] = normalizar.texto(rep.linha.get("titulo_alt"))
    if not linha["titulo_alt"]:
        # Só guarda como alternativo um título de fato diferente (tradução, título antigo),
        # não variações de pontuação do mesmo título.
        linha["titulo_alt"] = next((normalizar.texto(i.linha.get("titulo")) for i in ordem[1:]
                                    if i.tn and similaridade(i.tn, rep.tn) < limiar_titulo_alt), "")
    fontes = []
    for info in sorted(ordem, key=lambda i: (i.prioridade, i.id)):
        f = normalizar.texto(info.linha.get("fonte")).lower()
        if f and f not in fontes:
            fontes.append(f)
    linha["ids_registro"] = "|".join(m.id for m in sorted(membros, key=lambda i: i.id))
    linha["fontes"] = "|".join(fontes)
    linha["n_fontes"] = str(len(fontes))
    linha["tipo_duplicata"] = tipo_duplicata
    flags = []
    da_fonte = set()
    for info in ordem:
        da_fonte |= set((flags_registro or {}).get(info.id, ()))
    if not linha["resumo"]:
        flags.append("sem_resumo")
    if rep.preprint:
        flags.append("preprint")
    if _flags.FLAG_RETRATADO in da_fonte or any(
            re.search(r"retract|retrata", normalizar.ascii_fold(i.linha.get(c)).lower())
            for i in ordem for c in ("titulo", "tipo_publicacao_orig")):
        flags.append("retratado")
    sobrenomes = {i.sob for i in ordem if i.sob}
    if not rep.sob or len(sobrenomes) > 1:
        flags.append("autores_ambiguos")
    flags += sorted(f for f in da_fonte if f not in _ORDEM_FLAGS and f != FLAG_BUSCA_INATIVA)
    linha["flags"] = "|".join(flags)
    return linha


def _num_id(id_rs):
    m = _ID_RS.match(id_rs or "")
    return int(m.group(1)) if m else None


def historico_ids(raiz):
    """Maior id_rs já emitido e chaves de ids aposentados ou inativos, lidos dos eventos dedup_executado."""
    maior, chaves = 0, set()
    for ev in estado.ler_log(raiz):
        if ev.get("evento") != "dedup_executado":
            continue
        dados = ev.get("dados") or {}
        maior = max(maior, int(dados.get("ultimo_id_rs_num") or 0))
        for info in (dados.get("ids_rs_aposentados") or {}).values():
            if info.get("chave"):
                chaves.add(info["chave"])
        chaves.update(c for c in (dados.get("chaves_inativas") or []) if c)
    return maior, chaves


def atribuir_ids(clusters, antigos, maior_historico):
    """Casa clusters novos com linhas antigas de registros_unicos para manter id_rs/chave/id_estudo.

    Devolve (lista de (membros, linha_antiga|None, id_rs)), aposentados {id_rs: {...}}, maior número.
    """
    dono = {}
    for linha in antigos:
        for rid in normalizar.texto(linha.get("ids_registro")).split("|"):
            if rid:
                dono[rid] = linha["id_rs"]
    por_id = {l["id_rs"]: l for l in antigos}
    sobreposicoes = []
    for ci, membros in enumerate(clusters):
        contagem = {}
        for m in membros:
            if m.id in dono:
                contagem[dono[m.id]] = contagem.get(dono[m.id], 0) + 1
        for id_rs, n in contagem.items():
            sobreposicoes.append((-n, _num_id(id_rs) or 0, ci, id_rs))
    atribuido_cluster, usados_antigos = {}, set()
    for _, _, ci, id_rs in sorted(sobreposicoes):
        if ci in atribuido_cluster or id_rs in usados_antigos:
            continue
        atribuido_cluster[ci] = id_rs
        usados_antigos.add(id_rs)
    maior = max([maior_historico] + [n for n in (_num_id(l["id_rs"]) for l in antigos) if n])
    saida = []
    for ci, membros in enumerate(clusters):
        if ci in atribuido_cluster:
            id_rs = atribuido_cluster[ci]
            saida.append((membros, por_id[id_rs], id_rs))
        else:
            maior += 1
            saida.append((membros, None, f"RS{maior:04d}"))
    aposentados = {}
    novo_de = {}
    for membros, _, id_rs in saida:
        for m in membros:
            novo_de[m.id] = id_rs
    for linha in antigos:
        if linha["id_rs"] in usados_antigos:
            continue
        destino = next((novo_de[r] for r in normalizar.texto(linha.get("ids_registro")).split("|") if r in novo_de), "")
        aposentados[linha["id_rs"]] = {"absorvido_por": destino, "chave": normalizar.texto(linha.get("chave"))}
    return saida, aposentados, maior


# ---------------------------------------------------------------------------
# Comando
# ---------------------------------------------------------------------------
def _resolver(caminho, raiz):
    p = Path(caminho)
    if p.is_absolute() or p.exists():
        return p
    return Path(raiz) / p


def carregar_registros(raiz):
    caminho = Path(raiz) / esquema.ARQ_REGISTROS
    if not caminho.exists():
        raise ErroDedup(f"{esquema.ARQ_REGISTROS} não existe; rode `rs.py importar` antes")
    cabecalho, linhas = ler_csv(caminho)
    faltando = [c for c in esquema.COLUNAS_REGISTROS if c not in cabecalho]
    if faltando:
        raise ErroDedup(f"{esquema.ARQ_REGISTROS}: colunas ausentes {faltando}")
    vistos = set()
    for linha in linhas:
        rid = linha["id_registro"] = normalizar.texto(linha.get("id_registro"))
        if not rid:
            raise ErroDedup(f"{esquema.ARQ_REGISTROS}: linha sem id_registro")
        if rid in vistos:
            raise ErroDedup(f"{esquema.ARQ_REGISTROS}: id_registro duplicado {rid}")
        vistos.add(rid)
    return linhas


def _ids_da_linha(linha):
    return [r for r in normalizar.texto(linha.get("ids_registro")).split("|") if r]


def separar_inativos(antigos, ids_ativos, ids_inativos):
    """Divide linhas antigas de registros_unicos em (ativas, só com registros de buscas inativas)."""
    ativas, inativas = [], []
    for linha in antigos:
        ids = _ids_da_linha(linha)
        if ids and not any(r in ids_ativos for r in ids) and any(r in ids_inativos for r in ids):
            inativas.append(linha)
        else:
            ativas.append(linha)
    return ativas, inativas


def linha_inativa(antiga):
    """Linha antiga preservada como estava, só com a flag busca_inativa (idempotente)."""
    linha = {c: antiga.get(c, "") or "" for c in esquema.COLUNAS_UNICOS}
    flags = _buscas.flags_de(linha)
    if FLAG_BUSCA_INATIVA not in flags:
        flags.append(FLAG_BUSCA_INATIVA)
    linha["flags"] = "|".join(flags)
    return linha


def deduplicar(raiz, limiar_auto=95.0, limiar_candidato=85.0, humanas=None):
    """Núcleo sem efeitos colaterais no log: calcula pares, clusters e linhas de registros_unicos."""
    todas = carregar_registros(raiz)
    buscas_inativas = _buscas.inativas_do_projeto(raiz)
    ids_inativos = {l["id_registro"] for l in todas if l.get("busca_id") in buscas_inativas}
    linhas = [l for l in todas if l["id_registro"] not in ids_inativos]
    flags_registro = _flags.ler(raiz)
    infos = [Info(i, linha) for i, linha in enumerate(sorted(linhas, key=lambda l: l["id_registro"]))]
    infos_por_id = {i.id: i for i in infos}
    pares = gerar_pares(infos, limiar_auto, limiar_candidato)
    humanas_ativas = {k: v for k, v in (humanas or {}).items() if k[0] in infos_por_id and k[1] in infos_por_id}
    avisos = aplicar_decisoes(pares, humanas_ativas, infos_por_id)
    clusters, avisos_cluster, achar = agrupar(infos, pares)
    avisos += avisos_cluster
    estudo_de, arestas_versao, avisos_versao = ligar_versoes(infos, pares, achar)
    avisos += avisos_versao
    regras = regras_por_cluster(pares, achar)

    caminho_unicos = Path(raiz) / esquema.ARQ_UNICOS
    antigos = []
    if caminho_unicos.exists():
        cab, antigos = ler_csv(caminho_unicos)
        if not {"id_rs", "ids_registro"} <= set(cab):
            raise ErroDedup(f"{esquema.ARQ_UNICOS}: sem colunas id_rs/ids_registro; não dá para manter ids estáveis")
        antigos = [l for l in antigos if _num_id(l.get("id_rs"))]
    antigos_ativos, antigos_inativos = separar_inativos(antigos, set(infos_por_id), ids_inativos)
    maior_hist, chaves_hist = historico_ids(raiz)
    maior_hist = max([maior_hist] + [_num_id(l["id_rs"]) for l in antigos_inativos])
    atribuicoes, aposentados, maior = atribuir_ids(clusters, antigos_ativos, maior_hist)

    usadas = set(chaves_hist) | {normalizar.texto(l.get("chave")) for l in antigos if normalizar.texto(l.get("chave"))}
    usadas |= {i["chave"] for i in aposentados.values() if i["chave"]}
    saida = []
    pendentes_chave = []
    novos_ids = set()
    for membros, antiga, id_rs in atribuicoes:
        linha = mesclar(membros, _tipo_duplicata(membros, regras.get(achar(membros[0].id), set())), limiar_candidato,
                        flags_registro)
        linha["id_rs"] = id_rs
        linha["id_estudo"] = (normalizar.texto(antiga.get("id_estudo")) if antiga else "") or esquema.id_estudo_de(id_rs)
        chave_antiga = normalizar.texto(antiga.get("chave")) if antiga else ""
        if _chave.chave_valida(chave_antiga):
            linha["chave"] = chave_antiga
        else:
            pendentes_chave.append(linha)
        if antiga is None:
            novos_ids.add(id_rs)
        saida.append(linha)
    for linha in sorted(pendentes_chave, key=lambda l: _num_id(l["id_rs"])):
        k = _chave.gerar_chave(linha["titulo"], linha["autores"], linha["ano"], usadas)
        usadas.add(k)
        linha["chave"] = k
    inativas = [linha_inativa(l) for l in antigos_inativos]
    avisos += _avisos_equivalentes_inativos([l for l in saida if l["id_rs"] in novos_ids], inativas,
                                            ids_com_decisao_de_triagem(raiz))
    avisos += _avisos_relatos_separados(atribuicoes, antigos_ativos)
    saida += inativas
    saida.sort(key=lambda l: _num_id(l["id_rs"]))

    id_rs_da_raiz = {achar(membros[0].id): id_rs for membros, _, id_rs in atribuicoes}
    pares_versao = sorted({tuple(sorted((id_rs_da_raiz[ra], id_rs_da_raiz[rb]), key=_num_id))
                           for ra, rb in arestas_versao})

    def resolvido(a, b, p):
        ra, rb = achar(a), achar(b)
        return ra == rb or (p["regra"] == "versao" and estudo_de[ra] == estudo_de[rb])

    pendentes = [p for (a, b), p in pares.items() if p["decisao"] == "candidato" and not resolvido(a, b, p)]
    for (a, b), p in pares.items():
        if p["decisao"] == "candidato" and resolvido(a, b, p) and MARCA_RESOLVIDO not in p["motivo"]:
            p["motivo"] = f"{p['motivo']};{MARCA_RESOLVIDO}"
    linhas_pares = [pares[k] for k in sorted(pares)]
    return {
        "registros": infos, "unicos": saida, "pares": linhas_pares, "pendentes": pendentes,
        "avisos": avisos, "aposentados": aposentados, "maior": maior,
        "buscas_inativas": sorted(buscas_inativas), "n_registros_inativos": len(ids_inativos),
        "ids_rs_inativos": [l["id_rs"] for l in sorted(inativas, key=lambda l: _num_id(l["id_rs"]))],
        "chaves_inativas": sorted({l["chave"] for l in inativas if l.get("chave")}),
        "pares_versao": [list(p) for p in pares_versao],
    }


def _avisos_relatos_separados(atribuicoes, antigos_ativos):
    """Clusters novos com registros que antes estavam num cluster que continua (ex.: versão que deixou de fundir)."""
    dono = {}
    for linha in antigos_ativos:
        for rid in _ids_da_linha(linha):
            dono[rid] = linha["id_rs"]
    mantidos = {id_rs for _, antiga, id_rs in atribuicoes if antiga is not None}
    avisos = []
    for membros, antiga, id_rs in atribuicoes:
        if antiga is not None:
            continue
        origem = sorted({dono[m.id] for m in membros if dono.get(m.id) in mantidos}, key=_num_id)
        if origem:
            avisos.append(f"{id_rs} (novo) reúne registros que estavam em {', '.join(origem)}: é outro relato; "
                          "decisões de triagem não são herdadas, trie o novo id")
    return avisos


def ids_com_decisao_de_triagem(raiz):
    """id_rs com alguma decisão em dados/decisoes.jsonl (T/A ou texto completo); vazio sem ledger."""
    caminho = Path(raiz) / esquema.ARQ_DECISOES
    if not caminho.is_file():
        return set()
    from . import triagem_lotes  # import tardio: só quando há ledger
    return {l["id_rs"] for l in triagem_lotes.ler_decisoes(raiz) if l.get("etapa") in ("ta", "tc")}


def _avisos_equivalentes_inativos(novas, inativas, com_decisao=frozenset()):
    """Clusters novos cujo DOI ou id da fonte coincide com um cluster inativo (triagem não é herdada).

    Um aviso por cluster só quando o cluster inativo já tinha decisão de triagem (há o que refazer no id novo);
    os demais equivalentes viram um resumo agregado, para uma substituição de busca antes da triagem não
    encher a saída de avisos sem ação.
    """
    if not inativas:
        return []
    indice = {}
    for l in inativas:
        for chave in (("doi", normalizar.doi(l.get("doi"))), ("id_fonte", normalizar.texto(l.get("id_fonte")).lower())):
            if chave[1]:
                indice.setdefault(chave, l["id_rs"])
    avisos, sem_decisao = [], []
    for l in novas:
        for chave in (("doi", normalizar.doi(l.get("doi"))), ("id_fonte", normalizar.texto(l.get("id_fonte")).lower())):
            if chave[1] and chave in indice:
                antigo = indice[chave]
                if antigo in com_decisao:
                    avisos.append(f"{l['id_rs']} (novo) tem o mesmo {chave[0]} de {antigo}, cluster de busca "
                                  "substituída com decisão de triagem: decisões não são herdadas; trie o novo id")
                else:
                    sem_decisao.append((l["id_rs"], antigo))
                break
    if sem_decisao:
        exemplos = ", ".join(f"{novo}~{antigo}" for novo, antigo in sem_decisao[:5])
        avisos.append(f"{len(sem_decisao)} clusters novos equivalem (DOI ou id da fonte) a clusters de buscas "
                      f"substituídas sem decisão de triagem ({exemplos}{', ...' if len(sem_decisao) > 5 else ''}): "
                      "nada a herdar; os ids novos seguem para a triagem")
    return avisos


def candidatos_pendentes(pares):
    """Linhas de dedup_pares com decisao candidato ainda não resolvidas (sem a marca resolvido_transitivamente)."""
    return [p for p in pares if normalizar.texto(p.get("decisao")) == "candidato"
            and MARCA_RESOLVIDO not in normalizar.texto(p.get("motivo"))]


def contar_candidatos_pendentes(raiz):
    """Candidatos de duplicata que ainda pedem revisão humana, lidos de 01-busca/dedup_pares.csv.

    É a contagem do resumo do `dedup` e da pendência `dedup_candidatos`; contar só decisao == candidato inclui os
    pares já resolvidos por transitividade (marca resolvido_transitivamente no motivo) e dá um número maior.
    """
    caminho = Path(raiz) / esquema.ARQ_DEDUP_PARES
    if not caminho.is_file():
        return 0
    return len(candidatos_pendentes(ler_csv(caminho)[1]))


def unicos_ativos(unicos):
    """Linhas de registros_unicos que pertencem ao conjunto ativo (sem a flag busca_inativa)."""
    return [u for u in unicos if not _buscas.cluster_inativo(u)]


def _contar(itens, campo):
    contagem = {}
    for item in itens:
        contagem[item[campo]] = contagem.get(item[campo], 0) + 1
    return dict(sorted(contagem.items()))


def _sincronizar_pendencia(raiz, n_pendentes):
    """Autopiloto abre pendência se há candidatos; n diferente atualiza sem duplicar; zero fecha (qualquer modo)."""
    return sincronizar_pendencia_unica(
        raiz, TIPO_PENDENCIA, ETAPA,
        f"{n_pendentes} pares candidatos de duplicata aguardando revisão (rs.py dedup --revisar {esquema.ARQ_DEDUP_PARES})",
        n_pendentes, arquivo=esquema.ARQ_DEDUP_PARES, ator_id="dedup",
        motivo_resolvida="sem candidatos de duplicata pendentes", qualquer_arquivo_ao_fechar=True)


def _ultimo_dedup(raiz):
    """Último evento dedup_executado do log (ou None)."""
    for ev in reversed(estado.ler_log(raiz)):
        if ev.get("evento") == "dedup_executado":
            return ev
    return None


def _sha(caminho):
    return estado.sha256_arquivo(caminho) if Path(caminho).is_file() else ""


def _seguir_aposentados(id_rs, aposentados):
    vistos = set()
    while id_rs in (aposentados or {}) and id_rs not in vistos:
        vistos.add(id_rs)
        id_rs = (aposentados[id_rs] or {}).get("absorvido_por") or ""
    return id_rs


def _aposentados_do_log(raiz):
    """{id_rs aposentado: {absorvido_por, chave}} somando todos os eventos dedup_executado (cada um só traz os
    ids aposentados naquela execução)."""
    aposentados = {}
    for ev in estado.ler_log(raiz):
        if ev.get("evento") == "dedup_executado":
            aposentados.update((ev.get("dados") or {}).get("ids_rs_aposentados") or {})
    return aposentados


def mapa_absorvidos(raiz, ids_vigentes=None):
    """{id_rs aposentado: id_rs que o absorveu hoje}, com a cadeia de absorções seguida até o fim.

    Um id aposentado por fusão depois da triagem ainda pode ter decisões no ledger e nos arquivos finais; quem
    consolida (triagem, elegibilidade) usa este mapa para levar a decisão ao registro que o absorveu, e o PRISMA,
    para dizer o que rodar de novo. Com `ids_vigentes`, destino fora do conjunto vira "" (a decisão não tem para
    onde ir). Sem evento dedup_executado com aposentados, devolve {} e nada muda.
    """
    aposentados = _aposentados_do_log(raiz)
    mapa = {}
    for velho in aposentados:
        destino = _seguir_aposentados(velho, aposentados)
        mapa[velho] = destino if (ids_vigentes is None or destino in ids_vigentes) else ""
    return mapa


def chaves_absorvidas(raiz, ids_vigentes=None):
    """{chave de id aposentado: id_rs que o absorveu hoje} (mesma regra de `mapa_absorvidos`).

    Fichas de texto completo são indexadas pela chave: a ficha de um relato absorvido passa a valer para o
    registro que o absorveu."""
    aposentados = _aposentados_do_log(raiz)
    mapa = mapa_absorvidos(raiz, ids_vigentes)
    return {normalizar.texto((info or {}).get("chave")): mapa[velho]
            for velho, info in aposentados.items() if normalizar.texto((info or {}).get("chave"))}


def pares_preservados(raiz, info_anterior=None, aposentados=None, ids_validos=None):
    """Pares id_rs de 03-textos/ligacao_relatos.csv que não vieram do dedup (ligações humanas).

    Se o arquivo está como o último dedup o deixou (sha256 igual ao de `dados.ligacao_relatos`), valem os
    pares preservados gravados naquele evento; senão (arquivo regravado por `textos ligar-relatos` ou à mão),
    os grupos do arquivo contam, menos os pares que o último dedup ligou como versão (quem os repetiu na lista
    de `textos ligar-relatos` não os torna humanos: rejeitar a versão no dedup continua desfazendo a ligação).
    Ids aposentados seguem para quem os absorveu; ids fora de `ids_validos` saem. Devolve (pares ordenados,
    origem: sem_arquivo|log|arquivo, n de pares de versão encontrados no arquivo regravado).
    """
    caminho = Path(raiz) / esquema.ARQ_LIGACAO_RELATOS
    n_versao_no_arquivo = 0
    if not caminho.is_file():
        return [], "sem_arquivo", 0
    if info_anterior and info_anterior.get("sha256") == _sha(caminho):
        brutos, origem = [tuple(p) for p in info_anterior.get("pares_preservados") or [] if len(p) == 2], "log"
    else:
        brutos, origem = set(), "arquivo"
        for linha in ler_csv(caminho)[1]:
            grupo = [i.strip() for i in (linha.get("grupo") or "").split("|") if i.strip()]
            if len(grupo) < 2:
                continue
            brutos.update((grupo[0], m) for m in grupo[1:])
        automaticos = {tuple(sorted(p)) for p in (info_anterior or {}).get("pares_versao") or [] if len(p) == 2}
        n_versao_no_arquivo = sum(1 for p in brutos if tuple(sorted(p)) in automaticos)
        brutos = [p for p in sorted(brutos) if tuple(sorted(p)) not in automaticos]
    pares = set()
    for a, b in brutos:
        a, b = _seguir_aposentados(a, aposentados), _seguir_aposentados(b, aposentados)
        if a and b and a != b and (ids_validos is None or (a in ids_validos and b in ids_validos)):
            pares.add(tuple(sorted((a, b), key=lambda x: (_num_id(x) or 0, x))))
    return sorted(pares, key=lambda p: ((_num_id(p[0]) or 0), (_num_id(p[1]) or 0))), origem, n_versao_no_arquivo


def sincronizar_ligacao_relatos(raiz, pares_versao, info_anterior=None, aposentados=None, ids_validos=None):
    """Aplica as ligações de versão a ligacao_relatos.csv e a id_estudo, reutilizando textos.ligar_relatos.

    Sem ligação de versão agora, nem no último dedup, nem no arquivo, o arquivo (se houver) fica como está.
    """
    caminho = Path(raiz) / esquema.ARQ_LIGACAO_RELATOS
    preservados, origem, n_versao_no_arquivo = pares_preservados(raiz, info_anterior, aposentados, ids_validos)
    arquivo_intacto = bool(info_anterior) and info_anterior.get("sha256") == _sha(caminho)
    versao_anterior = (info_anterior or {}).get("pares_versao") or [] if arquivo_intacto else []
    versao = sorted({tuple(p) for p in pares_versao})
    info = {"pares_versao": [list(p) for p in versao], "pares_preservados": [list(p) for p in preservados],
            "origem_preservados": origem, "aplicado": False, "n_grupos": None, "n_estudos": None, "aviso": None}
    if versao or versao_anterior or n_versao_no_arquivo:
        from . import textos  # import tardio: textos importa triagem_lotes, desnecessário no dedup comum
        try:
            _, n_grupos, n_estudos = textos.ligar_relatos(raiz, sorted(set(preservados) | set(versao)))
            info.update(aplicado=True, n_grupos=n_grupos, n_estudos=n_estudos)
        except (ValueError, FileNotFoundError) as e:
            info["aviso"] = f"ligação de relatos não aplicada: {e}"
    info["sha256"] = _sha(caminho)
    return info


def pares_versao_ligados(raiz):
    """Pares (id_rs_a, id_rs_b) ligados como versões do mesmo estudo em 01-busca/dedup_pares.csv.

    Para quem precisa reaplicar a ligação automática (ex.: uma nova rodada de `textos ligar-relatos`,
    que reconstrói ligacao_relatos.csv só com os pares que recebe).
    """
    raiz = Path(raiz)
    if not (raiz / esquema.ARQ_DEDUP_PARES).is_file() or not (raiz / esquema.ARQ_UNICOS).is_file():
        return []
    dono = {}
    for u in ler_csv(raiz / esquema.ARQ_UNICOS)[1]:
        for rid in _ids_da_linha(u):
            dono[rid] = u.get("id_rs", "")
    pares = set()
    for p in ler_csv(raiz / esquema.ARQ_DEDUP_PARES)[1]:
        if p.get("regra") == "versao" and p.get("decisao") == DECISAO_LIGADO \
                and not normalizar.texto(p.get("motivo")).startswith("nao_aplicado:"):
            a, b = dono.get(p.get("id_a")), dono.get(p.get("id_b"))
            if a and b and a != b:
                pares.add(tuple(sorted((a, b), key=lambda x: (_num_id(x) or 0, x))))
    return sorted(pares)


def _reexecucao(ultimo, raiz, artefatos, parametros):
    """True se o último dedup_executado já cobre exatamente estes arquivos e parâmetros."""
    if not ultimo:
        return False
    dados = ultimo.get("dados") or {}
    if any(dados.get(k) != v for k, v in parametros.items()):
        return False
    citados = {a.get("caminho"): a.get("sha256") for a in ultimo.get("artefatos") or []}
    return set(citados) == set(artefatos) and all(citados[a] == _sha(Path(raiz) / a) for a in artefatos)


def executar(args):
    try:
        raiz = estado.exigir_projeto(args.dir)
        if not (0 < args.limiar_candidato <= args.limiar_auto <= 100):
            raise ErroDedup("limiares inválidos: exige 0 < --limiar-candidato <= --limiar-auto <= 100")
        por = normalizar.texto(args.por)
        if args.por is not None and por in AUTORES_AUTOMATICOS:
            raise ErroDedup(f"--por inválido: {args.por!r} (use o papel de quem decidiu, ex.: {PAPEL_HUMANO_PADRAO})")
        humanas = decisoes_do_log(raiz)
        novas = {}
        if args.revisar:
            caminho = _resolver(args.revisar, raiz)
            if not caminho.exists():
                raise ErroDedup(f"arquivo de revisão não encontrado: {args.revisar}")
            ids = {l["id_registro"] for l in carregar_registros(raiz)}
            lidas = ler_revisao(caminho, ids, por)
            novas = {k: v for k, v in lidas.items()
                     if not _mesma_decisao(humanas.get(k, {}).get("decisao"), v["decisao"])}
            if novas:
                artefato = []
                try:
                    artefato = [str(caminho.resolve().relative_to(Path(raiz).resolve()))]
                except ValueError:
                    pass
                ator = por or "|".join(sorted({d["decidido_por"] for d in novas.values()}))
                estado.registrar_evento(
                    raiz, "dedup_revisado", ETAPA, args.tipo_ator, ator,
                    dados={"n_decisoes": len(novas),
                           "decisoes": [{"id_a": a, "id_b": b, **d} for (a, b), d in sorted(novas.items())]},
                    artefatos=artefato)
                humanas.update(novas)
        ultimo = _ultimo_dedup(raiz)
        r = deduplicar(raiz, args.limiar_auto, args.limiar_candidato, humanas)
    except (estado.ErroProjeto, ErroDedup) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1

    saidas = [esquema.ARQ_UNICOS, esquema.ARQ_DEDUP_PARES, esquema.ARQ_LIGACAO_RELATOS]
    sha_antes = {a: _sha(raiz / a) for a in saidas}
    escrever_csv(raiz / esquema.ARQ_UNICOS, esquema.COLUNAS_UNICOS, r["unicos"])
    escrever_csv(raiz / esquema.ARQ_DEDUP_PARES, esquema.COLUNAS_DEDUP_PARES, r["pares"])
    info_anterior = ((ultimo or {}).get("dados") or {}).get("ligacao_relatos")
    ligacao = sincronizar_ligacao_relatos(raiz, r["pares_versao"], info_anterior, r["aposentados"],
                                          {u["id_rs"] for u in r["unicos"]})
    if ligacao["aviso"]:
        r["avisos"].append(ligacao["aviso"])
    sem_mudancas = sha_antes == {a: _sha(raiz / a) for a in saidas}
    # Fusão depois da triagem: as decisões dos ids absorvidos ficam no ledger e nos arquivos finais até a próxima
    # consolidação, que as leva ao registro que absorveu (triagem_lotes.fundir_absorvidos).
    absorvidos_com_triagem = sorted(set(r["aposentados"]) & ids_com_decisao_de_triagem(raiz),
                                    key=lambda i: (_num_id(i) or 0, i))
    if absorvidos_com_triagem:
        r["avisos"].append(
            f"{len(absorvidos_com_triagem)} ids absorvidos nesta execução já tinham decisão de triagem "
            f"(ex.: {', '.join(absorvidos_com_triagem[:5])}): rode `filtrar`, `triagem consolidar` e, se houver "
            "decisão de texto completo, `textos elegibilidade consolidar` antes do `prisma`; a decisão vai ao "
            "registro que absorveu (references/03-organizacao-triagem.md, seção 3)")

    ativos = unicos_ativos(r["unicos"])
    removidas = {}
    for u in ativos:
        n = len(u["ids_registro"].split("|")) - 1
        if n:
            removidas[u["tipo_duplicata"]] = removidas.get(u["tipo_duplicata"], 0) + n
    por_regra = {}
    for p in r["pares"]:
        por_regra.setdefault(p["regra"], {}).setdefault(p["decisao"], 0)
        por_regra[p["regra"]][p["decisao"]] += 1
    n_reg, n_uni = len(r["registros"]), len(ativos)
    n_resolvidos = sum(1 for p in r["pares"] if p["decisao"] == "candidato") - len(r["pendentes"])
    n_retratados = sum(1 for u in ativos if "retratado" in _buscas.flags_de(u))
    n_estudos = len({(u.get("id_estudo") or esquema.id_estudo_de(u["id_rs"]))
                     for u in unicos_ativos(ler_csv(raiz / esquema.ARQ_UNICOS)[1])})
    parametros = {"limiar_auto": args.limiar_auto, "limiar_candidato": args.limiar_candidato,
                  "backend_similaridade": BACKEND_FUZZY, "n_decisoes_humanas": len(humanas)}
    dados = {
        "n_registros": n_reg, "n_unicos": n_uni, "duplicatas_removidas": n_reg - n_uni,
        "duplicatas_removidas_por_tipo": dict(sorted(removidas.items())),
        "pares_por_regra": por_regra, "candidatos_pendentes": len(r["pendentes"]),
        "candidatos_resolvidos_transitivamente": n_resolvidos,
        **parametros,
        "ultimo_id_rs_num": r["maior"], "ids_rs_aposentados": r["aposentados"],
        "n_absorvidos": len(r["aposentados"]), "n_absorvidos_com_triagem": len(absorvidos_com_triagem),
        "buscas_inativas": r["buscas_inativas"], "n_registros_inativos": r["n_registros_inativos"],
        "n_unicos_inativos": len(r["ids_rs_inativos"]), "ids_rs_inativos": r["ids_rs_inativos"],
        "chaves_inativas": r["chaves_inativas"], "n_retratados": n_retratados,
        "n_versoes_ligadas": len(r["pares_versao"]), "n_estudos": n_estudos,
        "ligacao_relatos": {k: ligacao[k] for k in ("pares_versao", "pares_preservados", "origem_preservados",
                                                     "aplicado", "sha256")},
        "avisos": r["avisos"], "sem_mudancas": sem_mudancas,
    }
    artefatos = [esquema.ARQ_REGISTROS, esquema.ARQ_UNICOS, esquema.ARQ_DEDUP_PARES]
    if (raiz / _flags.ARQ_REGISTROS_FLAGS).exists():
        artefatos.append(_flags.ARQ_REGISTROS_FLAGS)
    if (raiz / esquema.ARQ_LIGACAO_RELATOS).exists():
        artefatos.append(esquema.ARQ_LIGACAO_RELATOS)
    # Reexecução idempotente: sem mudança nas saídas, sem decisão humana nova e com os mesmos insumos e
    # parâmetros do último dedup_executado, não grava outro evento (o log e a declaração de IA não mudam).
    reexecucao = sem_mudancas and not novas and _reexecucao(ultimo, raiz, artefatos, parametros)
    if not reexecucao:
        estado.registrar_evento(raiz, "dedup_executado", ETAPA, "script", "dedup", dados=dados, artefatos=artefatos)
    pendencia = _sincronizar_pendencia(raiz, len(r["pendentes"]))

    print(f"dedup: {n_reg} registros -> {n_uni} únicos ({n_reg - n_uni} duplicatas; backend {BACKEND_FUZZY})")
    if r["pares_versao"]:
        print(f"{len(r['pares_versao'])} par(es) preprint/publicado ligados como relatos do mesmo estudo "
              f"(id_estudo comum; ver {esquema.ARQ_LIGACAO_RELATOS}); cada relato segue para a triagem")
    if r["buscas_inativas"]:
        print(f"buscas substituídas ignoradas: {', '.join(r['buscas_inativas'])} ({r['n_registros_inativos']} "
              f"registros; {len(r['ids_rs_inativos'])} ids RS marcados {FLAG_BUSCA_INATIVA})")
    for aviso in r["avisos"]:
        print(f"aviso: {aviso}")
    if r["pendentes"]:
        extra = (f"; mais {n_resolvidos} com decisao=candidato já resolvidos por transitividade, marcados "
                 f"{MARCA_RESOLVIDO} no motivo" if n_resolvidos else "")
        print(f"{len(r['pendentes'])} pares candidatos aguardam revisão em {esquema.ARQ_DEDUP_PARES} "
              f"(preencha decisao=confirmado|rejeitado e rode "
              f"`rs.py dedup --revisar {esquema.ARQ_DEDUP_PARES} --por {PAPEL_HUMANO_PADRAO}`{extra})")
    if reexecucao:
        print("nada mudou desde o último dedup: nenhum evento novo no log")
    arquivos = [esquema.ARQ_UNICOS, esquema.ARQ_DEDUP_PARES]
    if (raiz / esquema.ARQ_LIGACAO_RELATOS).exists():
        arquivos.append(esquema.ARQ_LIGACAO_RELATOS)
    estado.resumo({
        "comando": "dedup", "n_registros": n_reg, "n_unicos": n_uni, "duplicatas_removidas": n_reg - n_uni,
        "duplicatas_removidas_por_tipo": dados["duplicatas_removidas_por_tipo"],
        "pares_por_decisao": _contar(r["pares"], "decisao"), "candidatos_pendentes": len(r["pendentes"]),
        "candidatos_resolvidos_transitivamente": n_resolvidos,
        "decisoes_novas": len(novas), "pendencia": pendencia, "avisos": len(r["avisos"]),
        "n_absorvidos": len(r["aposentados"]), "n_absorvidos_com_triagem": len(absorvidos_com_triagem),
        "buscas_inativas": r["buscas_inativas"], "n_registros_inativos": r["n_registros_inativos"],
        "n_unicos_inativos": len(r["ids_rs_inativos"]), "n_retratados": n_retratados,
        "n_versoes_ligadas": len(r["pares_versao"]), "n_estudos": n_estudos,
        "sem_mudancas": sem_mudancas, "reexecucao": reexecucao, "evento_registrado": not reexecucao,
        "backend_similaridade": BACKEND_FUZZY, "arquivos": arquivos,
    })
    return 0


def registrar(subparsers):
    p = subparsers.add_parser(
        "dedup", help="deduplica registros.csv (R1–R5) em registros_unicos.csv com auditoria de pares; liga versões "
                      "preprint/publicado por id_estudo",
        description="Deduplica dados/registros.csv em dados/registros_unicos.csv (ids RS estáveis) e grava "
                    "01-busca/dedup_pares.csv. Preprint/working paper e versão publicada não se fundem: ficam "
                    "com id_rs próprios e o mesmo id_estudo (03-textos/ligacao_relatos.csv). Com --revisar, "
                    "aplica decisões humanas (decidido_por na planilha ou --por) e refaz os clusters. Regras: "
                    "references/03-organizacao-triagem.md e Apêndice D da base de conhecimento.")
    p.add_argument("--limiar-auto", type=float, default=95.0,
                   help="similaridade de título (0–100) para fusão automática R4 e ligação automática de versões "
                        "(padrão 95)")
    p.add_argument("--limiar-candidato", type=float, default=85.0,
                   help="similaridade mínima para registrar par candidato R5 (padrão 85)")
    p.add_argument("--revisar", metavar="PARES_CSV",
                   help="CSV com id_a,id_b,decisao (confirmado|rejeitado|ligado)[,decidido_por,motivo]; exige "
                        "decidido_por preenchido ou --por")
    p.add_argument("--por", default=None,
                   help=f"papel de quem decidiu na revisão (ex.: {PAPEL_HUMANO_PADRAO}); obrigatório com --revisar "
                        "quando a coluna decidido_por estiver vazia")
    p.add_argument("--tipo-ator", default="humano", choices=esquema.TIPOS_ATOR,
                   help="tipo de ator das decisões de --revisar (padrão humano)")
    p.set_defaults(func=executar)
