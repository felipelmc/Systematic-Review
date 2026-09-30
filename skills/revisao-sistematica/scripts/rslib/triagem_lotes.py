"""Triagem por lotes para subagentes (modo padrão) e ledger de decisões da triagem.

USO
    rs.py triagem preparar --etapa ta --rodada ta_v2 --revisor A \\
        --criterios 02-triagem/prompts/ta_v2.md [--tamanho 25] [--semente 7] \\
        [--ids ids.csv] [--apenas-divergentes]
    rs.py triagem mesclar --rodada ta_v2 --revisor A [--modelo nome] [--tipo-ator ia_subagente]
    rs.py triagem consolidar --rodada ta_v2 [--rodada ta_v2_sn1] [--regra consenso|liberal]
    rs.py triagem override --id RS0042 --decisao incluir --motivo "..." [--rodada ta_v2] [--por revisor_humano_1]
    rs.py triagem override --id RS0042 --decisao excluir --criterio C2 --motivo "..." [--criterios arquivo]
    rs.py triagem override --fila 02-triagem/fila_humana_ta_v2.csv [--por revisor_humano_1]
    rs.py triagem fila --etapa tc [--master fichamentos_master.csv --codebook codebook.csv] [--verificacao ...]
    rs.py triagem override --fila 03-textos/fila_humana_tc.csv --etapa tc [--por revisor_humano_1]
    rs.py triagem override --etapa tc --id RS0042 --decisao excluir --criterio c2_intervencao_estudada --motivo "..."
    rs.py triagem override --etapa tc --id RS0042 --decisao aguardando --motivo "autores não responderam"

FLUXO
    1. `preparar` divide os registros elegíveis (registros_unicos.csv menos o que o funil
       formal excluiu e menos os clusters com a flag `busca_inativa`, que só têm registros de
       buscas substituídas; também com `--ids`) em lotes JSON por revisor, com embaralhamento
       próprio de cada revisor, em 02-triagem/lotes/<rodada>/<revisor>/lote_NNN.json, e um manifesto.
    2. O coordenador despacha um subagente por lote (agentes/triador-ta.md), que escreve
       lote_NNN.resposta.json e devolve uma linha. O resumo do subagente nunca é prova.
    3. `mesclar` valida cada resposta (schema, conjunto exato de IDs, enums, critério
       existente no arquivo de critérios, trecho verbatim do título/resumo) e grava as
       decisões em dados/decisoes.jsonl. Resposta inválida vai para rejeitados/ e o lote
       volta a ficar pendente (despachar novo subagente). A `proxima_acao` do resumo segue a
       ordem do `status` (`proxima_acao_rodada`): lotes pendentes → `mesclar`; divergências de IA
       sem árbitro → `preparar --revisor arbitro --apenas-divergentes` (alternativa: regra liberal);
       senão `consolidar`. Os IDs de critério (`ids_criterios`) são os que abrem linhas (cabeçalhos
       `### C1.`, itens `- C2:`); menções no texto ("ver C5") não entram.
    4. Com A e B mesclados, `preparar --revisor arbitro --apenas-divergentes` gera lotes
       só com as divergências, com os pareceres anonimizados (agentes/arbitro-cego.md).
    5. `consolidar` aplica a precedência override humano > árbitro > consenso e escreve
       02-triagem/triagem_ta_final.csv e a fila humana; `override` registra decisões humanas.

RODADA ATIVA E FILA HUMANA
    - `consolidar` grava em rs_estado.json `versoes_ativas.rodada_ta` (esquema.VERSAO_ATIVA_RODADA_TA;
      `rodada_<etapa>` nas outras etapas) = a rodada de maior prioridade da consolidação (a última
      `--rodada`). É a rodada que vale para o PRISMA e para o G4. `preparar` só preenche a chave
      quando ela ainda não existe. Rodadas de estabilidade (`*_estab` ou a `rodada_reexecucao` de
      um desenho de estabilidade) nunca são consolidadas nem recebem override.
    - Toda divergência vai à fila humana, inclusive a resolvida pelo árbitro (references/ia-validacao.md,
      seção 4 F: conflitos do LLM vão a humano). A decisão do árbitro vale para o fluxo, mas a linha entra na
      fila com `motivo_fila=arbitrada` e fica pendente até um override humano (que pode repetir a
      decisão do árbitro). `motivo_fila`: divergencia | divergencia_regra_liberal | arbitrada.
    - Clusters `busca_inativa` (buscas substituídas) saem do arquivo final e da fila (`n_inativos_ignorados`).
    - Ids absorvidos por um dedup depois da triagem (dedup.mapa_absorvidos) não ficam no arquivo final: a
      decisão vai ao registro que absorveu (`fundir_absorvidos`). Precedência: override > decisão de IA;
      depois incluir > incerto > excluir (recall primeiro, como a regra liberal); no empate fica a do
      registro que absorveu; sem decisão nele, herda a do absorvido; destino fora do conjunto ativo, a
      decisão cai. Cada divergência vira aviso e vai ao evento (`absorvidos_dedup`); para decidir outra
      coisa, `triagem override --id <registro que absorveu>`.
    - A fila é do humano: se ela tem linhas preenchidas (decisao_humana, criterio_humano ou motivo) ainda
      não aplicadas no ledger, `consolidar` NÃO a regrava (avisa e manda aplicar com `override --fila`);
      cabeçalho sem `id_rs` e `decisao_humana` aborta o comando sem tocar em nada.
    - Planilhas preenchidas por humanos (fila, listas de IDs, arquivo de critérios) são lidas pelo leitor único
      de planilhas.py (`ler_tabela_humana`, mantido aqui como alias): CSV com vírgula, ponto e vírgula ou
      tabulação (detectado pelo cabeçalho e por csv.Sniffer), com ou sem BOM, UTF-8, UTF-16 ou cp1252 (Excel
      pt-BR), ou xlsx. As escritas comparam bytes (a fila anterior pode estar em cp1252) e `consolidar` só grava
      depois de ler e conferir tudo.

OVERRIDE E CRITÉRIOS
    - Exclusão humana (T/A e texto completo, avulsa ou na fila) exige critério, conferido contra os IDs de
      critério da rodada: `ids_criterios` do manifesto dos lotes, `02-triagem/api/<rodada>/criterios.md`
      e, no texto completo, as variáveis-critério do codebook de elegibilidade (último `textos elegibilidade
      consolidar`, última `triagem fila --etapa tc` e `00-protocolo/codebook_elegibilidade.csv`). `--criterios` informa o arquivo quando a
      rodada não tem nenhuma dessas fontes. `C2` é aceito como apelido único de `c2_...`, gravado com o
      nome canônico. Inclusão não leva critério. Um erro em qualquer linha da fila não grava nada.
    - Papel padrão de `--por`: esquema.PAPEL_HUMANO_PADRAO (o mesmo de portão, pendência e dedup).

FILA DO TEXTO COMPLETO (`triagem fila --etapa tc`)
    Gera esquema.ARQ_FILA_HUMANA_TC com as propostas de elegibilidade ainda sem decisão humana (incertos
    primeiro): com `--master/--codebook`, calculadas das fichas pela mesma regra de `textos elegibilidade
    consolidar`; sem eles, lidas de 03-textos/elegibilidade_tc_final.csv. Colunas: id_rs, chave, proposta,
    criterio_proposto, evidencia, pagina, decisao_humana, criterio_humano, motivo. Evento `fila_gerada`.
    Recusa regravar uma fila com decisões preenchidas e ainda não aplicadas. Aplicar:
    `triagem override --fila 03-textos/fila_humana_tc.csv --etapa tc`, depois `textos elegibilidade consolidar`.
    - `override` sem `--rodada` usa a rodada ativa; se a última consolidação juntou várias rodadas,
      usa a última delas em que o registro tem decisão. Sem rodada ativa, a rodada mais recente do
      ledger (fora as de estabilidade). Em `--etapa tc` sem rodada nenhuma, usa `tc`.
    - Texto completo: `--decisao aguardando` (esquema.DECISOES_TC_FINAL, "awaiting
      classification", Cochrane 4.4.5) é gravado no ledger como `incerto` de humano (o schema do
      ledger é congelado); `textos elegibilidade consolidar` lê incerto humano em `tc` como
      `aguardando`.

POR QUE ASSIM
    - Joins só por id_rs: a junção por título falhou em projetos anteriores.
    - dados/decisoes.jsonl é append-only e "a última linha por (id_rs, etapa, rodada,
      revisor) vence": refazer um lote não apaga a história, só a supera. O modo API
      (triagem_api.py) escreve pelo mesmo `registrar_decisoes`, com trava de arquivo.
    - Registro sem resumo nunca é excluído por IA (references/ia-validacao.md): `mesclar` rejeita a
      exclusão e `consolidar` rebaixa para `incerto` qualquer exclusão não humana que
      tenha escapado. `incerto` segue para o texto completo.
    - Validar o trecho contra o título/resumo normalizados impede justificativas
      apoiadas em texto inventado, a falha mais barata de detectar.
"""

import argparse
import csv
import io
import json
import os
import random
import re
import sys
import threading
from collections import Counter, defaultdict
from pathlib import Path

from . import esquema, estado, normalizar
from . import planilhas as _planilhas
from .handoff import sincronizar_pendencia_unica
from .importar import buscas as _buscas

REVISOR_ARBITRO = "arbitro"
DECISOES_POSITIVAS = {"incluir", "incerto"}
MOTIVO_FILA_ARBITRADA = "arbitrada"
DECISAO_AGUARDANDO = esquema.DECISAO_TC_AGUARDANDO   # só no texto completo; gravada no ledger como `incerto` humano
SUFIXO_ESTABILIDADE = "_estab"
RODADA_TC_PADRAO = "tc"
PADRAO_ID_RS = re.compile(r"^RS[0-9]{4,}$")
PADRAO_NOME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,60}$")
PADRAO_CRITERIO = re.compile(r"\b(C\d{1,2}[A-Z]?)\b")
PADRAO_CRITERIO_C_COMPLETO = re.compile(r"C\d{1,2}[A-Z]?")
# Reserva para critérios numerados com outra letra (I1, E2...), só quando abrem a linha.
PADRAO_CRITERIO_LINHA = re.compile(
    r"^\s*(?:[#>*|+\-]+\s*|\d+[.)]\s*)*(?:\*\*|__|\[)?\s*([A-Z]{1,3}\d{1,3}[A-Z]?)(?:\*\*|__|\])?(?=[\s:.)\-–—|*]|$)",
    re.MULTILINE,
)
MAX_JUSTIFICATIVA_LOTE = 400
MAX_JUSTIFICATIVA_LEDGER = 600
MAX_PALAVRAS_TRECHO = 25
TAMANHO_PADRAO = 25
TAMANHO_PADRAO_ARBITRO = 20
LOTE_CAMPOS_RESPOSTA = ["lote_id", "rodada", "revisor", "criterios_sha", "decisoes"]
DECISAO_CAMPOS_RESPOSTA = ["id_rs", "decisao", "criterio_falhou", "justificativa", "trecho"]
COLUNAS_FILA_HUMANA = [
    "id_rs", "titulo", "resumo", "ano", "veiculo", "motivo_fila", "pareceres",
    "decisao_humana", "criterio_humano", "motivo_humano",
]
# Fila do texto completo (esquema.ARQ_FILA_HUMANA_TC); colunas em esquema.py desde a v1.3 (alias).
COLUNAS_FILA_HUMANA_TC = esquema.COLUNAS_FILA_HUMANA_TC
COLUNAS_OBRIGATORIAS_FILA = ["id_rs", "decisao_humana"]
CAMPOS_HUMANOS_FILA = ("decisao_humana", "criterio_humano", "motivo_humano", "motivo")
# Convenção das references (01-pergunta-protocolo, 04-textos-elegibilidade); em esquema.py desde a v1.3 (alias).
ARQ_CODEBOOK_ELEGIBILIDADE = esquema.ARQ_CODEBOOK_ELEGIBILIDADE
DELIMITADORES_HUMANOS = _planilhas.DELIMITADORES_HUMANOS
DECISOES_VALIDAS_OVERRIDE = frozenset(esquema.DECISOES) | {esquema.DECISAO_TC_AGUARDANDO}
ORDEM_PROPOSTA_TC = {"incerto": 0, "excluir": 1, "incluir": 2}

ETAPA_PROJETO = {
    "ta": "06_triagem_ta",
    "tc": "07_textos_elegibilidade",
    "qualidade": "09_extracao_rob",
    "dedup": "05_organizacao",
}
PORTAO_ETAPA = {"ta": "G4", "tc": "G5", "qualidade": "G7", "dedup": None}

DIR_SKILL = Path(__file__).resolve().parents[2]
AGENTE_TRIADOR = DIR_SKILL / "agentes" / "triador-ta.md"
AGENTE_ARBITRO = DIR_SKILL / "agentes" / "arbitro-cego.md"
SCHEMA_LOTE = DIR_SKILL / "assets" / "schemas" / "lote_resposta.schema.json"


# Exceções e leitor de planilhas humanas moram em planilhas.py (um leitor só para a skill); nomes mantidos.
ErroUso = _planilhas.ErroUso
ErroDependencia = _planilhas.ErroDependencia
ler_tabela_humana = _planilhas.ler_tabela_humana
_decodificar = _planilhas.decodificar
_celula_texto = _planilhas.celula_texto
_limpar_coluna = _planilhas.limpar_coluna


# ---------------------------------------------------------------------------
# Utilidades de arquivo
# ---------------------------------------------------------------------------
def escrever_atomico(caminho, conteudo):
    """Grava texto via arquivo temporário + rename (estado.escrever_atomico: permissão 0666 menos a umask)."""
    estado.escrever_atomico(caminho, conteudo, newline="")


def escrever_json(caminho, objeto):
    escrever_atomico(caminho, json.dumps(objeto, ensure_ascii=False, indent=2) + "\n")


def texto_csv(colunas, linhas):
    buffer = io.StringIO()
    escritor = csv.DictWriter(buffer, fieldnames=colunas, extrasaction="ignore", lineterminator="\n")
    escritor.writeheader()
    for linha in linhas:
        escritor.writerow({c: ("" if linha.get(c) is None else linha.get(c)) for c in colunas})
    return buffer.getvalue()


def escrever_csv(caminho, colunas, linhas):
    """CSV UTF-8 com cabeçalho exato; conteúdo só é trocado se mudou (preserva mtime e hash).

    A comparação é por bytes: o arquivo anterior pode ter voltado do Excel em cp1252 ou UTF-16 (a fila
    humana), e lê-lo como UTF-8 derrubava o comando depois de outras escritas.
    """
    novo = texto_csv(colunas, linhas)
    caminho = Path(caminho)
    if caminho.is_file() and caminho.read_bytes() == novo.encode("utf-8"):
        return False
    escrever_atomico(caminho, novo)
    return True


def ler_csv(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def relativo(raiz, caminho):
    """Caminho relativo à raiz (POSIX) quando estiver dentro do projeto; senão absoluto."""
    caminho = Path(caminho).resolve()
    try:
        return caminho.relative_to(Path(raiz).resolve()).as_posix()
    except ValueError:
        return str(caminho)


def resolver(raiz, caminho):
    p = Path(caminho)
    return p if p.is_absolute() else Path(raiz) / p


def sha_opcional(caminho):
    caminho = Path(caminho)
    return estado.sha256_arquivo(caminho) if caminho.exists() else ""


try:  # POSIX; no Windows fica sem trava de arquivo (a escrita é uma chamada só)
    import fcntl as _fcntl
except ImportError:  # pragma: no cover
    _fcntl = None
_TRAVA_THREAD = threading.Lock()


# ---------------------------------------------------------------------------
# Ledger de decisões (dados/decisoes.jsonl)
# ---------------------------------------------------------------------------
def chave_decisao(linha):
    """Chave de vigência: a última linha com a mesma chave substitui as anteriores."""
    return (linha["id_rs"], linha["etapa"], linha["rodada"], linha["revisor"])


def eh_override(linha):
    """Override humano = linha de humano com motivo_override preenchido (comando `override`)."""
    return linha.get("tipo_ator") == "humano" and not normalizar.vazio(linha.get("motivo_override"))


def positiva(decisao):
    """`incerto` conta como incluir para seguir ao texto completo (recall primeiro)."""
    return decisao in DECISOES_POSITIVAS


def nova_decisao(id_rs, etapa, rodada, revisor, tipo_ator, decisao, **extras):
    """Monta uma linha completa do ledger (todos os CAMPOS_DECISAO, ausentes = None).

    A justificativa é cortada em 600 caracteres (limite do schema) em vez de rejeitar a
    decisão inteira: o texto é auxiliar, a decisão e o trecho são o que se audita.
    """
    linha = {c: None for c in esquema.CAMPOS_DECISAO}
    linha.update({"id_rs": id_rs, "etapa": etapa, "rodada": rodada, "revisor": revisor,
                  "tipo_ator": tipo_ator, "decisao": decisao, "ts": estado.agora()})
    desconhecidos = set(extras) - set(esquema.CAMPOS_DECISAO)
    if desconhecidos:
        raise ValueError(f"campos desconhecidos na decisão: {sorted(desconhecidos)}")
    linha.update(extras)
    just = linha.get("justificativa")
    if isinstance(just, str) and len(just) > MAX_JUSTIFICATIVA_LEDGER:
        linha["justificativa"] = just[: MAX_JUSTIFICATIVA_LEDGER - 1] + "…"
    return linha


def validar_decisao(linha):
    """Lista de erros de uma linha do ledger contra assets/schemas/decisao.schema.json."""
    erros = []
    if not isinstance(linha, dict):
        return ["linha não é objeto"]
    extras = set(linha) - set(esquema.CAMPOS_DECISAO)
    if extras:
        erros.append(f"campos extras: {sorted(extras)}")
    for campo in ("id_rs", "etapa", "rodada", "revisor", "tipo_ator", "decisao", "ts"):
        if not isinstance(linha.get(campo), str) or not linha.get(campo):
            erros.append(f"{campo} obrigatório")
    for campo in esquema.CAMPOS_DECISAO:
        valor = linha.get(campo)
        if valor is not None and not isinstance(valor, str):
            erros.append(f"{campo} deve ser texto ou null")
    if isinstance(linha.get("id_rs"), str) and not PADRAO_ID_RS.match(linha["id_rs"]):
        erros.append(f"id_rs inválido: {linha['id_rs']}")
    if linha.get("etapa") not in esquema.ETAPAS_DECISAO:
        erros.append(f"etapa inválida: {linha.get('etapa')}")
    if linha.get("tipo_ator") not in esquema.TIPOS_ATOR:
        erros.append(f"tipo_ator inválido: {linha.get('tipo_ator')}")
    if linha.get("decisao") not in esquema.DECISOES:
        erros.append(f"decisao inválida: {linha.get('decisao')}")
    just = linha.get("justificativa")
    if isinstance(just, str) and len(just) > MAX_JUSTIFICATIVA_LEDGER:
        erros.append("justificativa acima de 600 caracteres")
    return erros


def registrar_decisoes(raiz, linhas):
    """Acrescenta decisões a dados/decisoes.jsonl (append-only, com trava). Devolve o nº gravado.

    Valida todas as linhas antes de gravar qualquer uma (tudo ou nada). Se a última linha
    do arquivo ficou truncada por uma queda, começa numa linha nova: a truncada continua
    ignorada na leitura e nunca é reescrita.
    """
    linhas = list(linhas)
    for i, linha in enumerate(linhas):
        completa = {c: linha.get(c) for c in esquema.CAMPOS_DECISAO}
        erros = validar_decisao({**completa, **linha})
        if erros:
            raise ValueError(f"decisão {i} inválida: {'; '.join(erros)}")
    if not linhas:
        return 0
    caminho = Path(raiz) / esquema.ARQ_DECISOES
    caminho.parent.mkdir(parents=True, exist_ok=True)
    corpo = b"".join(
        json.dumps({c: linha.get(c) for c in esquema.CAMPOS_DECISAO}, ensure_ascii=False).encode("utf-8") + b"\n"
        for linha in linhas)
    # Trava em dados/.decisoes.lock (flock + trava de thread), a mesma do escritor de reserva de
    # triagem_api.py: escritores concorrentes se excluem mutuamente.
    with _TRAVA_THREAD, open(caminho.parent / ".decisoes.lock", "a+") as trava:
        if _fcntl:
            _fcntl.flock(trava.fileno(), _fcntl.LOCK_EX)
        try:
            with open(caminho, "a+b") as f:
                f.seek(0, os.SEEK_END)
                if f.tell() > 0:
                    f.seek(-1, os.SEEK_END)
                    if f.read(1) != b"\n":
                        corpo = b"\n" + corpo
                f.seek(0, os.SEEK_END)
                f.write(corpo)
                f.flush()
                os.fsync(f.fileno())
        finally:
            if _fcntl:
                _fcntl.flock(trava.fileno(), _fcntl.LOCK_UN)
    return len(linhas)


def ler_decisoes(raiz):
    """Todas as linhas válidas do ledger, na ordem do arquivo (linhas truncadas ignoradas)."""
    caminho = Path(raiz) / esquema.ARQ_DECISOES
    linhas = []
    if not caminho.exists():
        return linhas
    with open(caminho, encoding="utf-8") as f:
        for texto in f:
            texto = texto.strip()
            if not texto:
                continue
            try:
                linha = json.loads(texto)
            except json.JSONDecodeError:
                continue
            if isinstance(linha, dict) and all(linha.get(c) for c in ("id_rs", "etapa", "rodada", "revisor", "decisao")):
                linhas.append(linha)
    return linhas


def decisoes_vigentes(linhas, etapa=None, rodadas=None):
    """Última linha por (id_rs, etapa, rodada, revisor), na ordem da sua última aparição."""
    rodadas = set(rodadas) if rodadas else None
    ultima = {}
    for ordem, linha in enumerate(linhas):
        if etapa and linha.get("etapa") != etapa:
            continue
        if rodadas is not None and linha.get("rodada") not in rodadas:
            continue
        ultima[chave_decisao(linha)] = (ordem, linha)
    return [linha for _, linha in sorted(ultima.values(), key=lambda par: par[0])]


def _unir_criterios(linhas):
    vistos = []
    for linha in linhas:
        c = linha.get("criterio_falhou")
        if c and c not in vistos:
            vistos.append(c)
    return "|".join(vistos) or None


def consolidar_decisoes(vigentes, regra="consenso", usar_overrides=True, sem_resumo=frozenset()):
    """Decisão final por id_rs para UMA rodada. Função pura, reutilizada pela validação.

    Precedência: override humano > árbitro > consenso dos revisores primários.
    - Divergência = revisores primários discordam quanto a seguir (incluir/incerto) ou não.
      incluir × incerto não é divergência: os dois seguem ao texto completo, então uma linha
      de árbitro para esse caso (o modo API pode chamá-lo) é ignorada e o final é `incerto`;
      assim o árbitro nunca exclui um registro que nenhum revisor excluiu.
    - Linhas com tipo_ator `regra` (sem resumo → incerto no modo API) decidem só quando não
      há revisor primário para o registro.
    - Regra `consenso`: divergência sem árbitro nem override fica `incerto` e vai à fila humana.
    - Divergência resolvida pelo árbitro também vai à fila (`motivo_fila=arbitrada`): a decisão
      do árbitro vale para o fluxo, mas fica pendente de conferência humana (references/ia-validacao.md, 4 F).
    - Regra `liberal` (references/ia-validacao.md, 4 E): basta um primário incluir/incerto; o árbitro não é usado
      para excluir, mas a divergência continua na fila humana para conferência.
    - Exclusão não humana de registro sem resumo vira `incerto` (nunca excluir sem resumo).
    Com `usar_overrides=False` obtém-se a decisão "só IA", que é o que a validação mede.
    """
    if regra not in ("consenso", "liberal"):
        raise ValueError(f"regra desconhecida: {regra}")
    grupos = defaultdict(lambda: {"primarias": {}, "arbitro": None, "overrides": []})
    for linha in vigentes:
        grupo = grupos[linha["id_rs"]]
        if eh_override(linha):
            grupo["overrides"].append(linha)
        elif linha["revisor"] == REVISOR_ARBITRO:
            grupo["arbitro"] = linha
        else:
            grupo["primarias"][linha["revisor"]] = linha

    resultado = {}
    for id_rs, grupo in grupos.items():
        todas_primarias = [grupo["primarias"][r] for r in sorted(grupo["primarias"])]
        # Linhas de regra (ex.: "sem resumo → incerto" do modo API) só decidem quando não há revisor.
        primarias = [p for p in todas_primarias if p.get("tipo_ator") != "regra"]
        linhas_regra = [p for p in todas_primarias if p.get("tipo_ator") == "regra"]
        decisoes = [p["decisao"] for p in primarias]
        # Divergência que muda o fluxo: um revisor manda ao texto completo e outro exclui.
        # incluir × incerto não diverge (os dois seguem), e o árbitro não decide esses casos.
        divergente = len({positiva(d) for d in decisoes}) > 1
        arbitro = grupo["arbitro"]
        override = grupo["overrides"][-1] if (usar_overrides and grupo["overrides"]) else None
        na_fila = False
        motivo_fila = None
        criterio = None
        if override is not None:
            final, por, criterio = override["decisao"], "humano", override.get("criterio_falhou")
        elif not primarias and linhas_regra:
            final, por, criterio = linhas_regra[-1]["decisao"], "regra", linhas_regra[-1].get("criterio_falhou")
        elif not primarias and arbitro is None:
            continue  # só havia overrides e eles foram ignorados
        elif divergente and regra == "liberal":
            final = "incluir" if "incluir" in decisoes else "incerto"
            por, na_fila, motivo_fila = "regra_liberal", True, "divergencia_regra_liberal"
        elif divergente and arbitro is not None:
            final, por, criterio = arbitro["decisao"], "arbitro", arbitro.get("criterio_falhou")
            na_fila, motivo_fila = True, MOTIVO_FILA_ARBITRADA  # conflito do LLM: conferência humana (F)
        elif divergente:
            final, por, na_fila, motivo_fila = "incerto", "pendente_humano", True, "divergencia"
        elif not primarias:
            final, por, criterio = arbitro["decisao"], "arbitro", arbitro.get("criterio_falhou")
        elif len(primarias) == 1:
            final, por, criterio = decisoes[0], "revisor_unico", primarias[0].get("criterio_falhou")
        else:
            if all(d == "excluir" for d in decisoes):
                final, criterio = "excluir", _unir_criterios(primarias)
            elif all(d == "incluir" for d in decisoes):
                final = "incluir"
            else:
                final = "incerto"
            por = "consenso"
        if final == "excluir" and por != "humano" and id_rs in sem_resumo:
            final, por = "incerto", "regra_sem_resumo"
        if final != "excluir" and por != "humano":
            criterio = None if final == "incluir" else criterio
        revisado_humano = override is not None or any(p.get("tipo_ator") == "humano" for p in primarias)
        resultado[id_rs] = {
            "id_rs": id_rs,
            "decisao_final": final,
            "decidido_por": por,
            "criterio_falhou": criterio,
            "divergente": int(divergente),
            "revisado_humano": int(revisado_humano),
            "na_fila": na_fila,
            "motivo_fila": motivo_fila,
            "primarias": {p["revisor"]: p for p in primarias},
            "arbitro": arbitro,
            "override": override,
        }
    return resultado


ORDEM_INCLUSIVA = {"excluir": 0, "incerto": 1, "incluir": 2}


def _forca_decisao(res):
    """Chave de precedência na fusão de absorvidos: override primeiro, depois a decisão mais inclusiva."""
    return (res.get("decidido_por") == "humano", ORDEM_INCLUSIVA.get(res.get("decisao_final"), -1))


def fundir_absorvidos(final, mapa):
    """Leva as decisões de ids absorvidos pelo dedup ao registro que os absorveu. Função pura.

    `final` é {id_rs: resultado de consolidar_decisoes}; `mapa`, {id aposentado: id que absorveu ou ""}
    (dedup.mapa_absorvidos). A decisão do absorvido só substitui a do registro que absorveu se for mais forte
    (`_forca_decisao`: override > IA, depois incluir > incerto > excluir): assim o resultado não depende de
    qual id o dedup manteve (o de menor número) e nada que a triagem mandou ao texto completo se perde. Sem
    decisão no registro que absorveu, ele herda a do absorvido; destino vazio, a decisão cai.
    Devolve (final, relatos) com um relato por id absorvido encontrado: {absorvido, destino, decisao_absorvido,
    decisao_destino, resultado} (resultado: herdada|mantida|substituida|descartada).
    """
    relatos = []
    for velho in sorted(i for i in list(final) if i in mapa):
        res = final.pop(velho)
        destino = mapa[velho]
        relato = {"absorvido": velho, "destino": destino, "decisao_absorvido": res["decisao_final"],
                  "decisao_destino": None, "resultado": "descartada"}
        if destino:
            atual = final.get(destino)
            relato["decisao_destino"] = atual["decisao_final"] if atual else None
            if atual is None or _forca_decisao(res) > _forca_decisao(atual):
                final[destino] = {**res, "id_rs": destino}
                relato["resultado"] = "herdada" if atual is None else "substituida"
            else:
                relato["resultado"] = "mantida"
        relatos.append(relato)
    return final, relatos


# ---------------------------------------------------------------------------
# Registros e critérios
# ---------------------------------------------------------------------------
def ler_unicos(raiz, obrigatorio=True):
    caminho = Path(raiz) / esquema.ARQ_UNICOS
    if not caminho.exists():
        if obrigatorio:
            raise ErroUso(f"{esquema.ARQ_UNICOS} não existe; rode `rs.py dedup` antes da triagem")
        return {}
    return {linha["id_rs"]: linha for linha in ler_csv(caminho) if linha.get("id_rs")}


RESUMOS_PLACEHOLDER = {
    "no abstract available", "no abstract", "abstract not available", "abstract unavailable",
    "sem resumo", "resumo nao disponivel", "resumo indisponivel", "sin resumen", "resumen no disponible",
}


def resumo_ausente(valor):
    """Vazio ou marcador de ausência ("[No abstract available]"): o registro conta como sem resumo.

    Sem isso, o marcador passaria por resumo e poderia até servir de "trecho" para excluir.
    """
    if normalizar.vazio(valor):
        return True
    return normalizar.ascii_fold(valor).lower().strip(" .[]()") in RESUMOS_PLACEHOLDER


def ids_sem_resumo(unicos):
    return frozenset(i for i, r in unicos.items() if resumo_ausente(r.get("resumo")))


def ids_inativos(unicos):
    """id_rs de clusters com a flag busca_inativa (só registros de buscas substituídas; fora do conjunto ativo)."""
    return frozenset(i for i, r in unicos.items() if _buscas.cluster_inativo(r))


def ids_excluidos_funil(raiz):
    """IDs que algum filtro formal excluiu (modo `excluir` previsto no protocolo)."""
    caminho = Path(raiz) / esquema.ARQ_FILTRO_FORMAL
    if not caminho.exists():
        return set()
    return {l["id_rs"] for l in ler_csv(caminho) if (l.get("resultado") or "").strip() == "exclui"}


def ids_criterios(texto):
    """IDs de critério definidos no arquivo, em ordem: C1, C2, C3A...

    Vale, nesta ordem, o primeiro conjunto não vazio:
    1. IDs `C<n>` que abrem uma linha (cabeçalho `### C1.`, item `- C2:`, `**C3**`, célula `| C4 |`): são as
       definições. Menções no meio do texto ("ver C5", "C6 é conferido no texto completo") não contam, para
       que a ordem e o conjunto de `ids_criterios` do manifesto sejam os dos critérios do arquivo;
    2. sem nenhuma definição em início de linha, `C<n>` em qualquer lugar (arquivos em prosa corrida);
    3. sem nenhum `C<n>`, IDs de outra letra que abrem linhas (I1, E2).
    Para arquivos sem menções soltas, dá os mesmos IDs de triagem_api.extrair_ids_criterios.
    """
    texto = texto or ""
    definidos = []
    for m in PADRAO_CRITERIO_LINHA.finditer(texto):
        if PADRAO_CRITERIO_C_COMPLETO.fullmatch(m.group(1)) and m.group(1) not in definidos:
            definidos.append(m.group(1))
    if definidos:
        return definidos
    for padrao in (PADRAO_CRITERIO, PADRAO_CRITERIO_LINHA):
        vistos = []
        for m in padrao.finditer(texto):
            if m.group(1) not in vistos:
                vistos.append(m.group(1))
        if vistos:
            return vistos
    return []


def ler_ids_arquivo(caminho):
    """Lista de id_rs de um CSV com coluna id_rs ou de um texto com um ID por linha."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise ErroUso(f"arquivo de IDs não existe: {caminho}")
    try:  # planilha com coluna id_rs (qualquer delimitador, BOM, xlsx)
        _, linhas, _ = ler_tabela_humana(caminho, ["id_rs"])
        ids = [l["id_rs"].strip().upper() for l in linhas if (l.get("id_rs") or "").strip()]
    except ErroDependencia:
        raise
    except ErroUso:
        if caminho.suffix.lower() in (".xlsx", ".xlsm"):
            raise
        texto, _ = _decodificar(caminho.read_bytes())
        ids = [re.split(r"[,;\t]", l.strip().lstrip("﻿"))[0].strip().upper()
               for l in texto.splitlines() if l.strip()]
    invalidos = [i for i in ids if not PADRAO_ID_RS.match(i)]
    if invalidos:
        raise ErroUso(f"IDs inválidos em {caminho}: {invalidos[:5]}")
    return list(dict.fromkeys(ids))


def _ids_de_arquivo_criterios(raiz, caminho):
    """IDs de um arquivo de critérios (Markdown/texto: C1, C2...) ou de um codebook (csv/xlsx: variáveis-critério)."""
    caminho = resolver(raiz, caminho)
    if not caminho.is_file():
        raise ErroUso(f"arquivo de critérios não existe: {caminho}")
    if caminho.suffix.lower() in (".csv", ".tsv", ".xlsx", ".xlsm"):
        from .textos import detectar_criterios  # import tardio: textos importa este módulo
        _, linhas, _ = ler_tabela_humana(caminho, ["variavel"])
        try:
            return detectar_criterios(linhas)
        except ValueError as e:
            raise ErroUso(f"{caminho.name}: {e}") from None
    return ids_criterios(_planilhas.ler_texto_humano(caminho)[0])


def ids_criterios_validos(raiz, etapa, rodadas=(), arquivo=None):
    """IDs de critério aceitos num override e de onde vieram: (ids, fontes).

    Com `arquivo` (flag --criterios), só ele. Senão, a união, em ordem, de: no texto completo, as
    variáveis-critério do último `textos elegibilidade consolidar`, da última `triagem fila --etapa tc` e do
    codebook de elegibilidade do protocolo; em qualquer etapa, `ids_criterios` dos manifestos das rodadas e o `criterios.md` congelado
    pela triagem via API; só sem nenhuma dessas, o arquivo de `versoes_ativas.criterios_<etapa>`.
    """
    raiz = Path(raiz)
    if arquivo:
        return _ids_de_arquivo_criterios(raiz, arquivo), [relativo(raiz, resolver(raiz, arquivo))]
    ids, fontes = [], []

    def somar(lista, fonte):
        if lista:
            ids.extend(i for i in lista if i not in ids)
            fontes.append(fonte)

    if etapa == "tc":
        ev = _ultimo_evento(raiz, "textos_atualizados",
                            lambda e: (e.get("dados") or {}).get("acao") == "elegibilidade_consolidar"
                            and (e.get("dados") or {}).get("criterios"))
        if ev:
            somar(list(ev["dados"]["criterios"]), f"rs_log.jsonl seq {ev.get('seq')} (textos elegibilidade consolidar)")
        ev = _ultimo_evento(raiz, "fila_gerada", lambda e: (e.get("dados") or {}).get("etapa") == "tc"
                            and (e.get("dados") or {}).get("criterios"))
        if ev:
            somar(list(ev["dados"]["criterios"]), f"rs_log.jsonl seq {ev.get('seq')} (triagem fila --etapa tc)")
        if (raiz / ARQ_CODEBOOK_ELEGIBILIDADE).is_file():
            somar(_ids_de_arquivo_criterios(raiz, ARQ_CODEBOOK_ELEGIBILIDADE), ARQ_CODEBOOK_ELEGIBILIDADE)
    for rodada in dict.fromkeys(r for r in rodadas if r):
        for manifesto in manifestos_da_rodada(raiz, rodada):
            somar(manifesto.get("ids_criterios") or [],
                  relativo(raiz, caminho_manifesto(raiz, rodada, manifesto.get("revisor", ""))))
        congelado = raiz / "02-triagem" / "api" / rodada / "criterios.md"
        if congelado.is_file():
            somar(ids_criterios(congelado.read_text(encoding="utf-8")), relativo(raiz, congelado))
    if not ids:
        ativo = (estado.carregar_estado(raiz).get("versoes_ativas") or {}).get(f"criterios_{etapa}")
        if ativo and resolver(raiz, ativo).is_file():
            somar(_ids_de_arquivo_criterios(raiz, ativo), ativo)
    return ids, fontes


def canonizar_criterio(valor, validos):
    """Nome canônico do critério em `validos`, ou None: exato, sem caixa, ou `C2` como apelido único de `c2_...`."""
    v = (valor or "").strip()
    if not v:
        return None
    if v in validos:
        return v
    mesma_caixa = [c for c in validos if c.lower() == v.lower()]
    if len(mesma_caixa) == 1:
        return mesma_caixa[0]
    if re.fullmatch(r"[A-Za-z]{1,3}\d{1,3}[A-Za-z]?", v):
        prefixo = [c for c in validos if re.match(rf"{re.escape(v)}(?:_|$)", c, re.IGNORECASE)]
        if len(prefixo) == 1:
            return prefixo[0]
    return None


def _validar_nome(valor, rotulo):
    if not PADRAO_NOME.match(valor or ""):
        raise ErroUso(f"{rotulo} inválido: {valor!r} (use letras, números, _ . -)")


def _texto_normalizado(valor):
    return f" {normalizar.titulo_normalizado(valor)} "


def trecho_confere(trecho, registro):
    """True se o trecho (normalizado) aparece com fronteira de palavra no título ou no resumo."""
    alvo = normalizar.titulo_normalizado(trecho)
    if not alvo:
        return False
    alvo = f" {alvo} "
    return alvo in _texto_normalizado(registro.get("titulo")) or alvo in _texto_normalizado(registro.get("resumo"))


# ---------------------------------------------------------------------------
# Lotes
# ---------------------------------------------------------------------------
def pasta_lotes(raiz, rodada, revisor):
    return Path(raiz) / "02-triagem" / "lotes" / rodada / revisor


def caminho_manifesto(raiz, rodada, revisor):
    return pasta_lotes(raiz, rodada, revisor) / "manifesto.json"


def ler_manifesto(raiz, rodada, revisor):
    caminho = caminho_manifesto(raiz, rodada, revisor)
    if not caminho.exists():
        return None
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def manifestos_da_rodada(raiz, rodada):
    pasta = Path(raiz) / "02-triagem" / "lotes" / rodada
    saida = []
    if pasta.exists():
        for arq in sorted(pasta.glob("*/manifesto.json")):
            with open(arq, encoding="utf-8") as f:
                saida.append(json.load(f))
    return saida


def _registro_para_lote(registro):
    """Só o que a triagem T/A precisa; autores ficam de fora para reduzir viés de prestígio."""
    resumo = "" if resumo_ausente(registro.get("resumo")) else normalizar.texto(registro.get("resumo"))
    return {
        "id_rs": registro["id_rs"],
        "titulo": normalizar.texto(registro.get("titulo")),
        "resumo": resumo,
        "sem_resumo": not resumo,
        "resumo_truncado": str(registro.get("resumo_truncado") or "0").strip() == "1",
        "palavras_chave": normalizar.texto(registro.get("palavras_chave")),
        "ano": normalizar.texto(registro.get("ano")),
        "tipo_publicacao": normalizar.texto(registro.get("tipo_publicacao")),
        "idioma": normalizar.texto(registro.get("idioma")),
        "veiculo": normalizar.texto(registro.get("veiculo")),
    }


def _pareceres_anonimos(resultado, rng):
    """Pareceres dos primários sem nome de revisor nem modelo, em ordem sorteada por registro.

    A ordem sorteada evita que o árbitro aprenda que "o primeiro" é sempre o mais liberal.
    """
    primarias = list(resultado["primarias"].values())
    rng.shuffle(primarias)
    return [
        {
            "rotulo": f"Revisor {i + 1}",
            "decisao": p["decisao"],
            "criterio_falhou": p.get("criterio_falhou"),
            "justificativa": p.get("justificativa"),
            "trecho": p.get("trecho"),
        }
        for i, p in enumerate(primarias)
    ]


def ids_divergentes(raiz, etapa, rodada):
    vig = decisoes_vigentes(ler_decisoes(raiz), etapa, [rodada])
    res = consolidar_decisoes(vig, regra="consenso", usar_overrides=False)
    return {i for i, r in res.items() if r["divergente"]}, res


def preparar_lotes(raiz, etapa, rodada, revisor, criterios, tamanho=None, semente=7, ids=None,
                   apenas_divergentes=False):
    """Cria (ou completa, append-only) os lotes de um revisor numa rodada. Devolve o resumo.

    Reexecutar com as mesmas entradas não cria nada novo. Registros que surgirem depois
    (ex.: bola de neve re-triada com os mesmos critérios) entram em lotes novos numerados
    em sequência, sem mexer nos existentes.
    """
    raiz = Path(raiz)
    _validar_nome(rodada, "rodada")
    _validar_nome(revisor, "revisor")
    if etapa not in esquema.ETAPAS_DECISAO:
        raise ErroUso(f"etapa inválida: {etapa}")
    if apenas_divergentes and revisor != REVISOR_ARBITRO:
        raise ErroUso("--apenas-divergentes é para o árbitro: use --revisor arbitro")
    if revisor == REVISOR_ARBITRO and not apenas_divergentes:
        raise ErroUso("o árbitro só recebe divergências: use --apenas-divergentes")
    if revisor == "regra":
        raise ErroUso("'regra' é reservado para decisões automáticas (ex.: sem resumo no modo API)")
    caminho_criterios = resolver(raiz, criterios)
    if not caminho_criterios.exists():
        raise ErroUso(f"arquivo de critérios não existe: {criterios}")
    avisos = []
    bruto = caminho_criterios.read_bytes()
    try:  # UTF-8 exato primeiro: o sha dos critérios em rodadas já preparadas não muda
        texto_criterios = bruto.decode("utf-8")
    except UnicodeDecodeError:
        texto_criterios, codificacao = _planilhas.decodificar(bruto)
        avisos.append(_planilhas.aviso_codificacao(caminho_criterios.name, codificacao)
                      or f"{caminho_criterios.name}: lido como {codificacao}")
    criterios_sha = estado.sha256_arquivo(caminho_criterios) if avisos else estado.sha256_texto(texto_criterios)
    lista_criterios = ids_criterios(texto_criterios)
    if not lista_criterios:
        raise ErroUso("nenhum critério identificado (C1, C2... ou I1, E2 no início da linha) no arquivo de critérios; "
                      "nomeie cada critério para que `mesclar` possa conferir criterio_falhou")
    if Path(relativo(raiz, caminho_criterios)).is_absolute():
        avisos.append("arquivo de critérios fora do projeto: copie-o para 02-triagem/prompts/ para arquivar a versão")
    for outro in manifestos_da_rodada(raiz, rodada):
        if outro["criterios_sha"] != criterios_sha:
            raise ErroUso(
                f"a rodada {rodada} já usa outra versão dos critérios (revisor {outro['revisor']}); "
                "critérios congelados não mudam dentro de uma rodada: crie uma rodada nova")
        if outro["etapa"] != etapa:
            raise ErroUso(f"a rodada {rodada} é da etapa {outro['etapa']}, não {etapa}")

    unicos = ler_unicos(raiz)
    excluidos = ids_excluidos_funil(raiz)
    inativos = ids_inativos(unicos)
    if ids is not None:
        desconhecidos = [i for i in ids if i not in unicos]
        if desconhecidos:
            raise ErroUso(f"IDs ausentes de {esquema.ARQ_UNICOS}: {desconhecidos[:5]}")
        pedidos_inativos = [i for i in ids if i in inativos]
        populacao = [i for i in ids if i not in excluidos and i not in inativos]
        n_funil = sum(1 for i in ids if i in excluidos and i not in inativos)
        if n_funil:
            avisos.append(f"{n_funil} IDs pedidos foram excluídos pelo funil formal e ficaram de fora")
        if pedidos_inativos:
            avisos.append(f"{len(pedidos_inativos)} IDs pedidos são de buscas substituídas (flag "
                          f"{esquema.FLAG_BUSCA_INATIVA}) e ficaram de fora: {pedidos_inativos[:10]}")
    else:
        populacao = sorted(i for i in unicos if i not in excluidos and i not in inativos)
        if inativos:
            avisos.append(f"{len(inativos)} registros únicos de buscas substituídas (flag {esquema.FLAG_BUSCA_INATIVA}) "
                          "ficaram fora da triagem")
    n_inativos_ignorados = len(inativos if ids is None else [i for i in ids if i in inativos])
    resultados_div = {}
    if apenas_divergentes:
        divergentes, resultados_div = ids_divergentes(raiz, etapa, rodada)
        populacao = [i for i in populacao if i in divergentes]

    manifesto = ler_manifesto(raiz, rodada, revisor)
    novo_manifesto = manifesto is None
    if manifesto is None:
        manifesto = {
            "versao": 1, "etapa": etapa, "rodada": rodada, "revisor": revisor,
            "criterios_arquivo": relativo(raiz, caminho_criterios), "criterios_sha": criterios_sha,
            "ids_criterios": lista_criterios, "semente": semente, "apenas_divergentes": apenas_divergentes,
            "agente_prompt_sha": sha_opcional(AGENTE_ARBITRO if apenas_divergentes else AGENTE_TRIADOR),
            "criado_em": estado.agora(), "lotes": [],
        }
    elif manifesto["criterios_sha"] != criterios_sha:
        raise ErroUso(f"os critérios mudaram desde que a rodada {rodada} foi preparada; crie uma rodada nova")
    alocados = {i for lote in manifesto["lotes"] for i in lote["ids"]}
    novos = [i for i in populacao if i not in alocados]
    tamanho = tamanho or (TAMANHO_PADRAO_ARBITRO if revisor == REVISOR_ARBITRO else TAMANHO_PADRAO)
    if tamanho < 1:
        raise ErroUso("--tamanho deve ser ≥ 1")

    pasta = pasta_lotes(raiz, rodada, revisor)
    lotes_novos = []
    if novos:
        n_existentes = len(manifesto["lotes"])
        rng = random.Random(f"{semente}:{rodada}:{revisor}:{n_existentes}")
        rng.shuffle(novos)
        for inicio in range(0, len(novos), tamanho):
            numero = len(manifesto["lotes"]) + 1
            lote_id = f"lote_{numero:03d}"
            ids_lote = novos[inicio:inicio + tamanho]
            arquivo = pasta / f"{lote_id}.json"
            resposta = pasta / f"{lote_id}.resposta.json"
            registros = []
            for i in ids_lote:
                item = _registro_para_lote(unicos[i])
                if apenas_divergentes:
                    item["pareceres"] = _pareceres_anonimos(resultados_div[i], rng)
                registros.append(item)
            conteudo = {
                "lote_id": lote_id, "etapa": etapa, "rodada": rodada, "revisor": revisor,
                "papel": "arbitro" if apenas_divergentes else "triador",
                "criterios_arquivo": manifesto["criterios_arquivo"], "criterios_sha": criterios_sha,
                "ids_criterios": lista_criterios,
                "arquivo_resposta": relativo(raiz, resposta),
                "modelo_resposta": {
                    "lote_id": lote_id, "rodada": rodada, "revisor": revisor, "criterios_sha": criterios_sha,
                    "decisoes": [{"id_rs": "RS0000", "decisao": "incluir|excluir|incerto",
                                  "criterio_falhou": "C1 ou null", "justificativa": "até 400 caracteres",
                                  "trecho": "cópia literal do título ou resumo (até 25 palavras) ou null"}],
                },
                "n_registros": len(registros),
                "registros": registros,
            }
            escrever_json(arquivo, conteudo)
            manifesto["lotes"].append({
                "lote_id": lote_id, "arquivo": relativo(raiz, arquivo), "resposta": relativo(raiz, resposta),
                "ids": ids_lote, "tamanho": tamanho, "status": "pendente", "mesclado_sha": None,
                "mesclado_em": None, "rejeicoes": 0,
            })
            lotes_novos.append(lote_id)
        manifesto["atualizado_em"] = estado.agora()
        escrever_json(caminho_manifesto(raiz, rodada, revisor), manifesto)
    elif novo_manifesto:
        raise ErroUso("nenhum registro a triar com esses parâmetros"
                      + (" (não há divergências nesta rodada)" if apenas_divergentes else ""))

    pendentes = [l for l in manifesto["lotes"] if l["status"] != "mesclado"]
    return {
        "manifesto": manifesto,
        "lotes_novos": lotes_novos,
        "registros_novos": len(novos),
        "pendentes": pendentes,
        "avisos": avisos,
        "n_inativos_ignorados": n_inativos_ignorados,
    }


# ---------------------------------------------------------------------------
# Validação de respostas de lote
# ---------------------------------------------------------------------------
def validar_resposta(resposta, lote, ids_validos_criterio):
    """Lista de erros de uma resposta de subagente em relação ao lote que ele recebeu.

    Checa, nesta ordem: forma do schema; identidade do lote (lote_id, rodada, revisor,
    criterios_sha); cada decisão (ID do lote, enum, critério existente, coerência
    decisão × critério, justificativa, trecho verbatim, sem resumo nunca excluir);
    e o conjunto de IDs (faltando, extras, duplicados).
    """
    erros = []
    if not isinstance(resposta, dict):
        return ["a resposta não é um objeto JSON"]
    for campo in LOTE_CAMPOS_RESPOSTA:
        if campo not in resposta:
            erros.append(f"campo obrigatório ausente: {campo}")
    extras = set(resposta) - set(LOTE_CAMPOS_RESPOSTA)
    if extras:
        erros.append(f"campos não permitidos: {sorted(extras)}")
    for campo in ("lote_id", "rodada", "revisor", "criterios_sha"):
        if campo in resposta and resposta[campo] != lote[campo]:
            erros.append(f"{campo} = {resposta[campo]!r}, esperado {lote[campo]!r}")
    decisoes = resposta.get("decisoes")
    if not isinstance(decisoes, list) or not decisoes:
        erros.append("decisoes deve ser uma lista não vazia")
        return erros

    registros = {r["id_rs"]: r for r in lote["registros"]}
    contagem = Counter()
    for i, d in enumerate(decisoes):
        rotulo = f"decisoes[{i}]"
        if not isinstance(d, dict):
            erros.append(f"{rotulo}: não é objeto")
            continue
        faltam = [c for c in DECISAO_CAMPOS_RESPOSTA if c not in d]
        if faltam:
            erros.append(f"{rotulo}: campos ausentes {faltam}")
        sobram = set(d) - set(DECISAO_CAMPOS_RESPOSTA)
        if sobram:
            erros.append(f"{rotulo}: campos não permitidos {sorted(sobram)}")
        id_rs = d.get("id_rs")
        if not isinstance(id_rs, str) or not PADRAO_ID_RS.match(id_rs):
            erros.append(f"{rotulo}: id_rs inválido {id_rs!r}")
            continue
        rotulo = f"{rotulo} ({id_rs})"
        contagem[id_rs] += 1
        registro = registros.get(id_rs)
        if registro is None:
            erros.append(f"{rotulo}: ID extra, não pertence ao lote")
            continue
        decisao = d.get("decisao")
        if decisao not in esquema.DECISOES:
            erros.append(f"{rotulo}: decisao inválida {decisao!r} (use incluir, excluir ou incerto)")
            continue
        criterio = d.get("criterio_falhou")
        if criterio is not None and not isinstance(criterio, str):
            erros.append(f"{rotulo}: criterio_falhou deve ser texto ou null")
            criterio = None
        if isinstance(criterio, str) and criterio.strip() == "":
            criterio = None
        if criterio is not None and criterio not in ids_validos_criterio:
            erros.append(f"{rotulo}: critério {criterio!r} não existe no arquivo de critérios {ids_validos_criterio}")
        if decisao == "excluir" and criterio is None:
            erros.append(f"{rotulo}: exclusão sem criterio_falhou")
        if decisao == "incluir" and criterio is not None:
            erros.append(f"{rotulo}: inclusão não pode ter criterio_falhou")
        just = d.get("justificativa")
        if not isinstance(just, str) or not just.strip():
            erros.append(f"{rotulo}: justificativa vazia")
        elif len(just) > MAX_JUSTIFICATIVA_LOTE:
            erros.append(f"{rotulo}: justificativa com {len(just)} caracteres (máx. {MAX_JUSTIFICATIVA_LOTE})")
        trecho = d.get("trecho")
        if trecho is not None and not isinstance(trecho, str):
            erros.append(f"{rotulo}: trecho deve ser texto ou null")
            trecho = None
        if isinstance(trecho, str) and not trecho.strip():
            trecho = None
        if registro.get("sem_resumo") and decisao == "excluir":
            erros.append(f"{rotulo}: registro sem resumo não pode ser excluído (use incerto)")
        if trecho is None:
            if decisao in ("incluir", "excluir") and not registro.get("sem_resumo"):
                erros.append(f"{rotulo}: {decisao} exige trecho verbatim do título ou resumo")
        else:
            if len(trecho.split()) > MAX_PALAVRAS_TRECHO:
                erros.append(f"{rotulo}: trecho com mais de {MAX_PALAVRAS_TRECHO} palavras")
            if not trecho_confere(trecho, registro):
                erros.append(f"{rotulo}: trecho não encontrado no título/resumo: {trecho[:80]!r}")
    duplicados = sorted(i for i, n in contagem.items() if n > 1)
    if duplicados:
        erros.append(f"IDs duplicados: {duplicados}")
    faltando = sorted(set(registros) - set(contagem))
    if faltando:
        erros.append(f"IDs faltando: {faltando}")
    if not erros:
        erros.extend(_validar_com_jsonschema(resposta))
    return erros


def _validar_com_jsonschema(resposta):
    """Conferência cruzada com o schema oficial quando jsonschema está instalado (opcional)."""
    try:
        import jsonschema
    except ImportError:
        return []
    if not SCHEMA_LOTE.exists():
        return []
    with open(SCHEMA_LOTE, encoding="utf-8") as f:
        schema = json.load(f)
    validador = jsonschema.Draft202012Validator(schema)
    return [f"schema: {e.message}" for e in validador.iter_errors(resposta)]


# ---------------------------------------------------------------------------
# Pendências (só no autopiloto)
# ---------------------------------------------------------------------------
def sincronizar_pendencia(raiz, tipo, etapa, portao, descricao, n, arquivo, ator_id):
    """Mantém uma pendência aberta por (tipo, arquivo) refletindo `n` (regra de handoff.sincronizar_pendencia_unica).

    Só o autopiloto abre pendência nova (em checkpoints o portão humano cobre a mesma verificação);
    n diferente substitui a aberta sem duplicar e n = 0 fecha, em qualquer modo. Não reabre o que um
    humano fechou com o mesmo n sobre o mesmo conteúdo do arquivo.
    """
    return sincronizar_pendencia_unica(raiz, tipo, etapa, descricao, n, portao=portao, arquivo=arquivo,
                                       ator_id=ator_id, motivo_resolvida="resolvida")


def _ultimo_evento(raiz, evento, filtro):
    for ev in reversed(estado.ler_log(raiz)):
        if ev.get("evento") == evento and filtro(ev):
            return ev
    return None


# ---------------------------------------------------------------------------
# Rodada ativa e rodadas de estabilidade
# ---------------------------------------------------------------------------
def chave_rodada_ativa(etapa):
    """Chave de versoes_ativas com a rodada que vale para a etapa (T/A: esquema.VERSAO_ATIVA_RODADA_TA)."""
    return esquema.VERSAO_ATIVA_RODADA_TA if etapa == "ta" else f"rodada_{etapa}"


def rodada_ativa(raiz, etapa="ta", est=None):
    est = est if est is not None else estado.carregar_estado(raiz)
    return (est.get("versoes_ativas") or {}).get(chave_rodada_ativa(etapa))


def rodadas_estabilidade(raiz):
    """Nomes de rodadas de reexecução: sufixo `_estab` e `rodada_reexecucao` dos desenhos de estabilidade."""
    nomes = set()
    pasta = Path(raiz) / "02-triagem" / "validacao"
    if pasta.exists():
        for arq in pasta.glob("*/estabilidade_desenho.json"):
            try:
                with open(arq, encoding="utf-8") as f:
                    nome = (json.load(f).get("parametros") or {}).get("rodada_reexecucao")
            except (OSError, json.JSONDecodeError):
                continue
            if nome:
                nomes.add(nome)
    return nomes


def eh_rodada_estabilidade(rodada, estab=frozenset()):
    return bool(rodada) and (str(rodada).endswith(SUFIXO_ESTABILIDADE) or rodada in estab)


def rodadas_da_ultima_consolidacao(raiz, etapa):
    """Rodadas (em ordem de prioridade) da última `triagem consolidar` da etapa, ou []."""
    ev = _ultimo_evento(raiz, "triagem_consolidada", lambda e: (e.get("dados") or {}).get("etapa", "ta") == etapa)
    return list((ev or {}).get("dados", {}).get("rodadas") or [])


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------
def cmd_preparar(args):
    raiz = estado.exigir_projeto(args.dir)
    ids = ler_ids_arquivo(resolver(raiz, args.ids)) if args.ids else None
    r = preparar_lotes(raiz, args.etapa, args.rodada, args.revisor, args.criterios, args.tamanho,
                       args.semente, ids=ids, apenas_divergentes=args.apenas_divergentes)
    manifesto = r["manifesto"]
    rel_manifesto = relativo(raiz, caminho_manifesto(raiz, args.rodada, args.revisor))
    if r["lotes_novos"]:
        est = estado.carregar_estado(raiz)
        chave_versao = f"criterios_{args.etapa}"
        est["versoes_ativas"][chave_versao] = manifesto["criterios_arquivo"]
        # A rodada ativa é de `consolidar`; aqui só se preenche a lacuna (nunca com estabilidade).
        if not est["versoes_ativas"].get(chave_rodada_ativa(args.etapa)) \
                and not eh_rodada_estabilidade(args.rodada, rodadas_estabilidade(raiz)):
            est["versoes_ativas"][chave_rodada_ativa(args.etapa)] = args.rodada
        etapa_projeto = ETAPA_PROJETO[args.etapa]
        if est["etapas"].get(etapa_projeto, {}).get("status") == "pendente":
            est["etapas"][etapa_projeto]["status"] = "em_andamento"
            est["etapas"][etapa_projeto]["em"] = estado.agora()
        estado.registrar_evento(
            raiz, "lote_preparado", etapa_projeto, "script", "triagem_lotes",
            dados={"rodada": args.rodada, "etapa": args.etapa, "revisor": args.revisor,
                   "lotes_novos": r["lotes_novos"], "registros_novos": r["registros_novos"],
                   "tamanho": manifesto["lotes"][-1]["tamanho"], "semente": args.semente,
                   "criterios_sha": manifesto["criterios_sha"], "apenas_divergentes": args.apenas_divergentes},
            artefatos=[manifesto["criterios_arquivo"], rel_manifesto], estado=est)
    for aviso in r["avisos"]:
        print(f"aviso: {aviso}", file=sys.stderr)
    agente = AGENTE_ARBITRO if args.apenas_divergentes else AGENTE_TRIADOR
    estado.resumo({
        "comando": "triagem preparar", "ok": True, "reexecucao": not r["lotes_novos"],
        "rodada": args.rodada, "etapa": args.etapa, "revisor": args.revisor,
        "n_lotes": len(manifesto["lotes"]), "lotes_novos": len(r["lotes_novos"]),
        "registros_novos": r["registros_novos"],
        "n_registros": sum(len(l["ids"]) for l in manifesto["lotes"]),
        "criterios": str(resolver(raiz, manifesto["criterios_arquivo"])),
        "agente_prompt": str(agente),
        "lotes_pendentes": [
            {"lote": str(resolver(raiz, l["arquivo"])), "resposta": str(resolver(raiz, l["resposta"]))}
            for l in r["pendentes"]
        ],
        "manifesto": rel_manifesto, "n_inativos_ignorados": r["n_inativos_ignorados"], "avisos": r["avisos"],
    })
    return 0


def mesclar_rodada(raiz, rodada, revisor, modelo=None, tipo_ator="ia_subagente", apenas_lote=None):
    """Valida e grava as respostas disponíveis de um revisor. Devolve o relatório por lote."""
    raiz = Path(raiz)
    manifesto = ler_manifesto(raiz, rodada, revisor)
    if manifesto is None:
        raise ErroUso(f"rodada {rodada} não tem lotes do revisor {revisor}; rode `triagem preparar`")
    if tipo_ator not in esquema.TIPOS_ATOR:
        raise ErroUso(f"tipo de ator inválido: {tipo_ator}")
    if sha_opcional(resolver(raiz, manifesto["criterios_arquivo"])) not in ("", manifesto["criterios_sha"]):
        print("aviso: o arquivo de critérios mudou depois do preparo; a validação usa a versão congelada "
              "no manifesto", file=sys.stderr)
    etapa_projeto = ETAPA_PROJETO[manifesto["etapa"]]
    relatorio = {"mesclados": [], "rejeitados": [], "pendentes": [], "ja_mesclados": []}
    rel_manifesto = relativo(raiz, caminho_manifesto(raiz, rodada, revisor))

    def gravar_manifesto():
        # Gravado ANTES do evento, que cita o manifesto: assim o sha256 no log é o do arquivo
        # que ficou em disco (o replay do log confere) e uma queda entre os dois passos não
        # deixa o ledger à frente do manifesto.
        manifesto["atualizado_em"] = estado.agora()
        escrever_json(caminho_manifesto(raiz, rodada, revisor), manifesto)
    for info in manifesto["lotes"]:
        if apenas_lote and info["lote_id"] != apenas_lote:
            continue
        caminho_resposta = resolver(raiz, info["resposta"])
        if not caminho_resposta.exists():
            (relatorio["ja_mesclados"] if info["status"] == "mesclado" else relatorio["pendentes"]).append(info["lote_id"])
            continue
        bruto = caminho_resposta.read_bytes()
        sha = estado.sha256_arquivo(caminho_resposta)
        if info.get("mesclado_sha") == sha:
            relatorio["ja_mesclados"].append(info["lote_id"])
            continue
        with open(resolver(raiz, info["arquivo"]), encoding="utf-8") as f:
            lote = json.load(f)
        try:
            resposta = json.loads(bruto.decode("utf-8-sig"))
            erros = validar_resposta(resposta, lote, manifesto["ids_criterios"])
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            resposta, erros = None, [f"JSON malformado: {e}"]
        if erros:
            pasta_rej = caminho_resposta.parent / "rejeitados"
            carimbo = estado.agora().replace(":", "").replace("-", "")
            destino = pasta_rej / f"{info['lote_id']}.resposta.{carimbo}.json"
            pasta_rej.mkdir(parents=True, exist_ok=True)
            os.replace(caminho_resposta, destino)
            escrever_json(pasta_rej / f"{info['lote_id']}.erros.{carimbo}.json", {"lote_id": info["lote_id"], "erros": erros})
            info["status"] = "rejeitado"
            info["rejeicoes"] = int(info.get("rejeicoes") or 0) + 1
            gravar_manifesto()
            estado.registrar_evento(
                raiz, "lote_rejeitado", etapa_projeto, "script", "triagem_lotes", modelo=modelo,
                dados={"rodada": rodada, "revisor": revisor, "lote": info["lote_id"], "n_erros": len(erros),
                       "erros": erros[:20], "rejeicoes": info["rejeicoes"]},
                artefatos=[relativo(raiz, destino), rel_manifesto])
            relatorio["rejeitados"].append({"lote": info["lote_id"], "n_erros": len(erros), "erros": erros[:5],
                                            "rejeitado_em": relativo(raiz, destino)})
            continue
        linhas = []
        for d in resposta["decisoes"]:
            criterio = d.get("criterio_falhou") or None
            trecho = d.get("trecho") if isinstance(d.get("trecho"), str) and d["trecho"].strip() else None
            linhas.append(nova_decisao(
                d["id_rs"], manifesto["etapa"], rodada, revisor, tipo_ator, d["decisao"],
                modelo=modelo, prompt_sha=manifesto["criterios_sha"], criterio_falhou=criterio,
                justificativa=d["justificativa"], trecho=trecho, lote=info["lote_id"]))
        registrar_decisoes(raiz, linhas)
        info.update({"status": "mesclado", "mesclado_sha": sha, "mesclado_em": estado.agora()})
        gravar_manifesto()
        contagens = dict(Counter(l["decisao"] for l in linhas))
        estado.registrar_evento(
            raiz, "lote_mesclado", etapa_projeto, tipo_ator, f"revisor_{revisor}", modelo=modelo,
            dados={"rodada": rodada, "revisor": revisor, "lote": info["lote_id"], "n_decisoes": len(linhas),
                   "contagens": contagens, "resposta_sha": sha, "prompt_sha": manifesto["criterios_sha"]},
            artefatos=[info["resposta"], esquema.ARQ_DECISOES, rel_manifesto])
        relatorio["mesclados"].append({"lote": info["lote_id"], "n_decisoes": len(linhas), "contagens": contagens})
    relatorio["manifesto"] = manifesto
    return relatorio


def proxima_acao_rodada(raiz, rodada, revisor=None):
    """Próximo passo de uma rodada de lotes, na mesma ordem do `status`. Devolve dict com `texto` e `comando`
    e, conforme o caso, `alternativa`, `lotes_pendentes` (por revisor) e `n_divergentes_sem_arbitro`.

    1. lotes não mesclados (os do `revisor` pedido primeiro): despachar e mesclar;
    2. divergências entre revisores com parecer de IA, sem árbitro nem override: lotes do árbitro cego
       (alternativa: consolidar com a regra liberal, só se o protocolo a previu);
    3. senão, consolidar.
    """
    raiz = Path(raiz)
    manifestos = {m.get("revisor"): m for m in manifestos_da_rodada(raiz, rodada) if m.get("revisor")}
    pendentes = {r: sum(1 for l in m.get("lotes") or [] if l.get("status") != "mesclado") for r, m in manifestos.items()}
    pendentes = {r: n for r, n in pendentes.items() if n}
    if pendentes:
        alvo = revisor if revisor in pendentes else sorted(pendentes)[0]
        return {"texto": f"despachar novo subagente para cada lote rejeitado ou pendente do revisor {alvo} "
                         f"({pendentes[alvo]}) e mesclar de novo",
                "comando": f"triagem mesclar --rodada {rodada} --revisor {alvo}", "lotes_pendentes": pendentes}
    etapa = next((m.get("etapa") for m in manifestos.values() if m.get("etapa")), "ta")
    resultado = consolidar_decisoes(decisoes_vigentes(ler_decisoes(raiz), etapa, [rodada]), "consenso", True)
    revisores = {r for res in resultado.values() for r in res["primarias"]}
    sem_arbitro = sorted(i for i, res in resultado.items()
                         if res["divergente"] and res["arbitro"] is None and res["override"] is None
                         and any(p.get("tipo_ator") != "humano" for p in res["primarias"].values()))
    consolidar = f"triagem consolidar --rodada {rodada}" + ("" if etapa == "ta" else f" --etapa {etapa}")
    if len(revisores) >= 2 and sem_arbitro:
        criterios = next((m.get("criterios_arquivo") for m in manifestos.values() if m.get("criterios_arquivo")),
                         f"02-triagem/prompts/{rodada}.md")
        return {"texto": f"{len(sem_arbitro)} divergências entre {' e '.join(sorted(revisores))} sem árbitro: prepare "
                         "os lotes do árbitro cego antes de consolidar (references/03-organizacao-triagem.md, seção 7)",
                "comando": f"triagem preparar --etapa {etapa} --rodada {rodada} --revisor {REVISOR_ARBITRO} "
                           f"--apenas-divergentes --criterios {criterios}",
                "alternativa": f"{consolidar} --regra liberal (só se o protocolo previu a regra liberal; as "
                               "divergências vão à fila humana)",
                "n_divergentes_sem_arbitro": len(sem_arbitro)}
    return {"texto": "todos os lotes mesclados, sem divergência à espera de árbitro", "comando": consolidar}


def cmd_mesclar(args):
    raiz = estado.exigir_projeto(args.dir)
    _validar_nome(args.rodada, "rodada")
    _validar_nome(args.revisor, "revisor")
    rel = mesclar_rodada(raiz, args.rodada, args.revisor, args.modelo, args.tipo_ator, args.lote)
    manifesto = rel.pop("manifesto")
    pendentes = [l for l in manifesto["lotes"] if l["status"] != "mesclado"]
    proxima = proxima_acao_rodada(raiz, args.rodada, args.revisor)
    estado.resumo({
        "comando": "triagem mesclar", "ok": not rel["rejeitados"],
        "reexecucao": not rel["mesclados"] and not rel["rejeitados"],
        "rodada": args.rodada, "revisor": args.revisor,
        "mesclados": rel["mesclados"], "rejeitados": rel["rejeitados"],
        "ja_mesclados": len(rel["ja_mesclados"]),
        "lotes_pendentes": [
            {"lote": str(resolver(raiz, l["arquivo"])), "resposta": str(resolver(raiz, l["resposta"]))}
            for l in pendentes
        ],
        "proxima_acao": proxima["comando"],
        "proxima_acao_detalhe": proxima,
    })
    return 1 if rel["rejeitados"] else 0


def _descrever_parecer(linha):
    crit = f" [{linha['criterio_falhou']}]" if linha.get("criterio_falhou") else ""
    just = f": {linha['justificativa']}" if linha.get("justificativa") else ""
    return f"{linha['revisor']}={linha['decisao']}{crit}{just}"


def cmd_consolidar(args):
    raiz = estado.exigir_projeto(args.dir)
    rodadas = list(dict.fromkeys(args.rodada))
    estab = rodadas_estabilidade(raiz)
    for r in rodadas:
        _validar_nome(r, "rodada")
        if eh_rodada_estabilidade(r, estab):
            raise ErroUso(f"{r} é rodada de estabilidade (reexecução): ela só é comparada por `validar estabilidade` "
                          "e não pode virar a decisão final nem a rodada ativa")
    todas = ler_decisoes(raiz)
    unicos = ler_unicos(raiz, obrigatorio=False)
    sem_resumo = ids_sem_resumo(unicos)
    avisos = []
    if not unicos:
        avisos.append(f"{esquema.ARQ_UNICOS} ausente: regra 'sem resumo → incerto' não pôde ser conferida")
    nome_fila = "+".join(rodadas)
    rel_fila = f"02-triagem/fila_humana_{nome_fila}.csv"
    caminho_fila = raiz / rel_fila
    # A fila existente é lida (e validada) antes de gravar qualquer coisa: cabeçalho quebrado aborta aqui.
    fila_anterior = []
    if caminho_fila.exists():
        _, fila_anterior, info_fila = ler_tabela_humana(caminho_fila, COLUNAS_OBRIGATORIAS_FILA, rotulo=rel_fila)
        avisos.extend(info_fila["avisos"])
    final = {}
    for rodada in rodadas:
        vig = decisoes_vigentes(todas, args.etapa, [rodada])
        if not vig:
            raise ErroUso(f"nenhuma decisão da etapa {args.etapa} na rodada {rodada}")
        for id_rs, res in consolidar_decisoes(vig, args.regra, True, sem_resumo).items():
            final[id_rs] = res  # rodada posterior na lista prevalece
    # Ids absorvidos por um dedup depois da triagem: a decisão vai ao registro que absorveu (antes do funil e dos
    # inativos, que então valem para o destino).
    from . import dedup  # import tardio: evita ciclo (dedup importa triagem_lotes sob demanda)
    final, fundidos = fundir_absorvidos(final, dedup.mapa_absorvidos(raiz, set(unicos) or None))
    if fundidos:
        divergentes = [f for f in fundidos if f["decisao_destino"] not in (None, f["decisao_absorvido"])]
        exemplos = "; ".join(f"{f['absorvido']}→{f['destino'] or '(sem destino)'}: {f['decisao_absorvido']} × "
                             f"{f['decisao_destino']} = {f['resultado']}" for f in divergentes[:10])
        avisos.append(f"{len(fundidos)} ids absorvidos pelo dedup tinham decisão e saíram do arquivo final "
                      f"({dict(sorted(Counter(f['resultado'] for f in fundidos).items()))}); decisões diferentes da do registro que "
                      f"absorveu: {len(divergentes)}" + (f" ({exemplos})" if exemplos else ""))
    excluidos_funil = ids_excluidos_funil(raiz)
    em_funil = sorted(set(final) & excluidos_funil)
    if em_funil:
        # Excluído por automação não é "triado" no PRISMA: sai do arquivo final para não contar duas vezes.
        for id_rs in em_funil:
            del final[id_rs]
        avisos.append(f"{len(em_funil)} IDs com decisão foram excluídos pelo funil formal e saíram do arquivo final")
    inativos = ids_inativos(unicos)
    em_inativos = sorted(set(final) & inativos)
    if em_inativos:
        # Clusters só com registros de buscas substituídas estão fora do fluxo (PRISMA, validação e fila).
        for id_rs in em_inativos:
            del final[id_rs]
        avisos.append(f"{len(em_inativos)} IDs de buscas substituídas (flag {esquema.FLAG_BUSCA_INATIVA}) saíram do "
                      f"arquivo final e da fila: {em_inativos[:10]}")
    um_revisor = sum(1 for r in final.values() if r["decidido_por"] == "revisor_unico")
    if um_revisor:
        avisos.append(f"{um_revisor} IDs têm só um revisor primário (triagem dupla incompleta)")
    esperados = set(unicos) - excluidos_funil - inativos if unicos else set()
    sem_decisao = sorted(esperados - set(final))
    if sem_decisao:
        avisos.append(f"{len(sem_decisao)} registros elegíveis ainda sem decisão nesta(s) rodada(s)")

    linhas_final = [{c: final[i][c] for c in esquema.COLUNAS_TRIAGEM_FINAL} for i in sorted(final)]
    if args.etapa == "ta":
        rel_final = esquema.ARQ_TRIAGEM_TA_FINAL
    else:
        rel_final = f"02-triagem/triagem_{args.etapa}_final.csv"
        if args.etapa == "tc":
            avisos.append(f"{rel_final} é auxiliar: o PRISMA e o G5 leem {esquema.ARQ_ELEGIBILIDADE_TC_FINAL}; "
                          "registre decisões humanas com `triagem override --etapa tc` e rode "
                          "`textos elegibilidade consolidar`")

    # Todas as leituras e contas antes de qualquer escrita: um erro aqui não deixa o final regravado sem evento.
    preenchido = {}
    for linha in fila_anterior:
        if any((linha.get(c) or "").strip() for c in CAMPOS_HUMANOS_FILA):
            preenchido[(linha.get("id_rs") or "").strip().upper()] = linha
    nao_aplicadas = linhas_fila_nao_aplicadas(fila_anterior, todas, args.etapa, rodadas)
    fila = []
    for id_rs in sorted(final):
        res = final[id_rs]
        if not res["na_fila"]:
            continue
        reg = unicos.get(id_rs, {})
        pareceres = " || ".join(_descrever_parecer(p) for p in res["primarias"].values())
        if res["arbitro"] is not None:
            pareceres += " || " + _descrever_parecer(res["arbitro"])
        anterior = preenchido.get(id_rs, {})
        fila.append({
            "id_rs": id_rs, "titulo": reg.get("titulo", ""), "resumo": reg.get("resumo", ""),
            "ano": reg.get("ano", ""), "veiculo": reg.get("veiculo", ""),
            "motivo_fila": res.get("motivo_fila") or "divergencia",
            "pareceres": pareceres,
            "decisao_humana": anterior.get("decisao_humana", ""),
            "criterio_humano": anterior.get("criterio_humano", ""),
            "motivo_humano": anterior.get("motivo_humano", ""),
        })
    fila_preservada = bool(nao_aplicadas)
    escrever_csv(raiz / rel_final, esquema.COLUNAS_TRIAGEM_FINAL, linhas_final)
    if fila_preservada:
        # A fila é do humano: com decisões preenchidas e ainda não aplicadas, nunca é regravada.
        avisos.append(f"{rel_fila} tem {len(nao_aplicadas)} linhas preenchidas ainda não aplicadas "
                      f"({nao_aplicadas[:10]}): o arquivo não foi regravado; aplique com "
                      f"`triagem override --fila {rel_fila}` e consolide de novo")
    else:
        escrever_csv(caminho_fila, COLUNAS_FILA_HUMANA, fila)

    contagens = dict(Counter(r["decisao_final"] for r in final.values()))
    por = dict(Counter(r["decidido_por"] for r in final.values()))
    motivos_fila = dict(Counter(l["motivo_fila"] for l in fila))
    n_arbitradas = motivos_fila.get(MOTIVO_FILA_ARBITRADA, 0)
    sha_final, sha_fila = sha_opcional(raiz / rel_final), sha_opcional(caminho_fila)
    anterior = _ultimo_evento(raiz, "triagem_consolidada",
                              lambda ev: ev["dados"].get("arquivo") == rel_final)
    reexecucao = bool(anterior) and anterior["dados"].get("sha_final") == sha_final \
        and anterior["dados"].get("sha_fila") == sha_fila and anterior["dados"].get("rodadas") == rodadas
    etapa_projeto = ETAPA_PROJETO[args.etapa]
    # Rodada ativa = a de maior prioridade (a última da lista), a que vale para o PRISMA e o G4.
    rodada_consolidada = rodadas[-1]
    est = estado.carregar_estado(raiz)
    chave_ativa = chave_rodada_ativa(args.etapa)
    mudou_ativa = est["versoes_ativas"].get(chave_ativa) != rodada_consolidada
    est["versoes_ativas"][chave_ativa] = rodada_consolidada
    if not reexecucao:
        estado.registrar_evento(
            raiz, "triagem_consolidada", etapa_projeto, "script", "triagem_lotes",
            dados={"rodadas": rodadas, "etapa": args.etapa, "regra": args.regra, "n": len(final),
                   "contagens": contagens, "decidido_por": por,
                   "divergentes": sum(r["divergente"] for r in final.values()),
                   "fila_humana": len(fila), "motivos_fila": motivos_fila, "arbitradas_na_fila": n_arbitradas,
                   "sem_decisao": len(sem_decisao), "rodada_ativa": rodada_consolidada,
                   "n_inativos_ignorados": len(em_inativos), "fila_preservada": fila_preservada,
                   "n_absorvidos_dedup": len(fundidos), "absorvidos_dedup": fundidos[:200],
                   "arquivo": rel_final, "sha_final": sha_final, "sha_fila": sha_fila},
            artefatos=[rel_final, rel_fila], estado=est)
    elif mudou_ativa:
        estado.salvar_estado(raiz, est)
    descricao = f"resolver {len(fila)} divergências da triagem ({nome_fila}) com `triagem override --fila {rel_fila}`"
    if n_arbitradas:
        descricao += f" ({n_arbitradas} arbitradas: conferir a decisão do árbitro e registrá-la como humana)"
    pendencia = sincronizar_pendencia(
        raiz, "fila_humana_triagem", etapa_projeto, PORTAO_ETAPA[args.etapa], descricao,
        len(fila), rel_fila, "triagem_lotes")
    for aviso in avisos:
        print(f"aviso: {aviso}", file=sys.stderr)
    estado.resumo({
        "comando": "triagem consolidar", "ok": True, "reexecucao": reexecucao,
        "rodadas": rodadas, "regra": args.regra, "n": len(final), "contagens": contagens,
        "decidido_por": por, "divergentes": sum(r["divergente"] for r in final.values()),
        "fila_humana": len(fila), "motivos_fila": motivos_fila, "arbitradas_na_fila": n_arbitradas,
        "sem_decisao": len(sem_decisao), "pendencia": pendencia, "n_inativos_ignorados": len(em_inativos),
        "n_absorvidos_dedup": len(fundidos),
        "fila_preservada": fila_preservada, "linhas_fila_nao_aplicadas": nao_aplicadas[:50],
        "rodada_ativa": rodada_consolidada, "arquivo": rel_final, "fila": rel_fila, "avisos": avisos,
        "proxima_acao": (f"triagem override --fila {rel_fila} (decisões humanas preenchidas) e consolidar de novo"
                         if fila_preservada else None),
    })
    return 0


def _rodada_mais_recente(linhas, etapa, estab=frozenset()):
    for linha in reversed(linhas):
        if linha.get("etapa") == etapa and not eh_rodada_estabilidade(linha.get("rodada"), estab):
            return linha["rodada"]
    return None


def rodada_padrao_override(raiz, etapa, id_rs, todas, estab, est=None):
    """Rodada de um override sem `--rodada`: a ativa (ou, na consolidação de várias rodadas, a última
    em que o registro tem decisão); sem rodada ativa, a mais recente do ledger; em `tc`, `tc`."""
    ativa = rodada_ativa(raiz, etapa, est)
    if eh_rodada_estabilidade(ativa, estab):
        ativa = None
    candidatas = []
    if ativa:
        consolidadas = [r for r in rodadas_da_ultima_consolidacao(raiz, etapa)
                        if not eh_rodada_estabilidade(r, estab)]
        candidatas = consolidadas if ativa in consolidadas else [ativa]
    if candidatas:
        com_decisao = [r for r in candidatas
                       if any(l["id_rs"] == id_rs and l.get("etapa") == etapa and l["rodada"] == r for l in todas)]
        return (com_decisao or candidatas)[-1]
    return _rodada_mais_recente(todas, etapa, estab) or (RODADA_TC_PADRAO if etapa == "tc" else None)


def normalizar_decisao_humana(valor):
    """incluir|excluir|incerto|aguardando a partir do que o humano escreveu (caixa e acento livres); "" se vazio."""
    return normalizar.ascii_fold(valor or "").strip().lower()


def _criterio_equivale(escrito, gravado):
    escrito, gravado = (escrito or "").strip(), (gravado or "").strip()
    if not escrito:
        return True
    return bool(gravado) and (escrito.lower() == gravado.lower()
                              or bool(re.match(rf"{re.escape(escrito)}(?:_|$)", gravado, re.IGNORECASE)))


def linhas_fila_nao_aplicadas(linhas, todas, etapa, rodadas=None):
    """id_rs das linhas de uma fila com conteúdo humano que o ledger ainda não tem como override equivalente.

    Linha com decisão, critério ou motivo preenchido conta como aplicada só se a última decisão humana
    (override) do registro na etapa (nas `rodadas`, se dadas) tem a mesma decisão e critério equivalente.
    """
    rodadas = set(rodadas) if rodadas else None
    humanas = {}
    for linha in todas:
        if linha.get("etapa") == etapa and eh_override(linha) and (rodadas is None or linha.get("rodada") in rodadas):
            humanas[linha["id_rs"]] = linha
    pendentes = []
    for linha in linhas:
        if not any((linha.get(c) or "").strip() for c in CAMPOS_HUMANOS_FILA):
            continue
        id_rs = (linha.get("id_rs") or "").strip().upper()
        dec = normalizar_decisao_humana(linha.get("decisao_humana"))
        dec = "incerto" if dec == DECISAO_AGUARDANDO else dec
        h = humanas.get(id_rs)
        if not (dec and h and h.get("decisao") == dec and _criterio_equivale(linha.get("criterio_humano"),
                                                                              h.get("criterio_falhou"))):
            pendentes.append(id_rs or "(sem id_rs)")
    return pendentes


def _tipo_de_fila(colunas):
    """'tc' (fila do texto completo), 'ta' (fila da consolidação) ou None pelo cabeçalho."""
    presentes = {c.lower() for c in colunas}
    if {"proposta", "criterio_proposto"} <= presentes:
        return "tc"
    if {"motivo_fila", "pareceres"} & presentes:
        return "ta"
    return None


def cmd_override(args):
    raiz = estado.exigir_projeto(args.dir)
    _validar_nome(args.por, "--por")
    todas = ler_decisoes(raiz)
    unicos = ler_unicos(raiz, obrigatorio=False)
    estab = rodadas_estabilidade(raiz)
    est = estado.carregar_estado(raiz)
    if args.rodada and eh_rodada_estabilidade(args.rodada, estab):
        raise ErroUso(f"{args.rodada} é rodada de estabilidade: override vai para a rodada ativa "
                      f"({rodada_ativa(raiz, args.etapa, est) or 'consolide a rodada principal antes'})")
    pedidos, erros, avisos = [], [], []
    if args.fila:
        caminho = resolver(raiz, args.fila)
        if not caminho.exists():
            raise ErroUso(f"fila não existe: {args.fila}")
        m = re.match(r"fila_humana_(.+)\.(?:csv|tsv|txt|xlsx|xlsm)$", caminho.name, re.IGNORECASE)
        rodadas_fila = m.group(1).split("+") if m else []
        if any(eh_rodada_estabilidade(r, estab) for r in rodadas_fila):
            raise ErroUso(f"a fila {caminho.name} é de rodada de estabilidade; overrides só em rodadas consolidáveis")
        colunas, linhas, info = ler_tabela_humana(caminho, COLUNAS_OBRIGATORIAS_FILA)
        avisos.extend(info["avisos"])
        tipo = _tipo_de_fila(colunas)
        if tipo == "tc" and args.etapa != "tc":
            raise ErroUso(f"{caminho.name} é a fila do texto completo (colunas proposta/criterio_proposto): use --etapa tc")
        if tipo == "ta" and args.etapa == "tc":
            raise ErroUso(f"{caminho.name} é a fila da triagem de títulos e resumos: rode sem --etapa tc")
        for numero, linha in zip(info["numeros"], linhas):
            dec = normalizar_decisao_humana(linha.get("decisao_humana"))
            if not dec:
                continue
            id_rs = (linha.get("id_rs") or "").strip().upper()
            # Numa fila de várias rodadas, o override vai para a última rodada em que o ID tem decisão.
            com_decisao = [r for r in rodadas_fila
                           if any(l["id_rs"] == id_rs and l["rodada"] == r for l in todas)]
            rodada_fila = (com_decisao or rodadas_fila or [None])[-1]
            motivo = (linha.get("motivo_humano") or linha.get("motivo") or "").strip()
            pedidos.append({"id_rs": id_rs, "decisao": dec,
                            "criterio": (linha.get("criterio_humano") or "").strip() or None,
                            "motivo": motivo or "resolução da fila humana",
                            "rodada": args.rodada or rodada_fila, "rotulo": f"{caminho.name} linha {numero} ({id_rs})"})
        if not pedidos:
            raise ErroUso("nenhuma linha da fila tem decisao_humana preenchida")
    else:
        if not (args.id and args.decisao and args.motivo):
            raise ErroUso("informe --id, --decisao e --motivo (ou --fila)")
        pedidos.append({"id_rs": args.id.strip().upper(), "decisao": args.decisao,
                        "criterio": (args.criterio or "").strip() or None,
                        "motivo": args.motivo, "rodada": args.rodada, "rotulo": args.id})
    validas = sorted(DECISOES_VALIDAS_OVERRIDE)
    for p in pedidos:
        rotulo = p["rotulo"]
        if not PADRAO_ID_RS.match(p["id_rs"]):
            erros.append(f"{rotulo}: id_rs inválido")
            continue
        if unicos and p["id_rs"] not in unicos:
            erros.append(f"{rotulo}: {p['id_rs']} não existe em {esquema.ARQ_UNICOS}")
            continue
        if p["decisao"] not in DECISOES_VALIDAS_OVERRIDE:
            erros.append(f"{rotulo}: decisão inválida {p['decisao']!r} (use {', '.join(validas)})")
            continue
        if p["decisao"] == DECISAO_AGUARDANDO:
            if args.etapa != "tc":
                erros.append(f"{rotulo}: `aguardando` (aguardando classificação) só existe no texto completo: "
                             "use --etapa tc")
                continue
            if p["criterio"]:
                erros.append(f"{rotulo}: `aguardando` não tem critério que falhou")
                continue
            # O schema do ledger é congelado: aguardando = incerto de humano no tc (lido assim por `textos`).
            p["decisao"] = "incerto"
        if p["decisao"] == "incluir" and p["criterio"]:
            erros.append(f"{rotulo}: inclusão não tem critério que falhou (apague o critério {p['criterio']!r})")
            continue
        if p["decisao"] == "excluir" and not p["criterio"]:
            campo = "criterio_humano" if args.fila else "--criterio"
            erros.append(f"{rotulo}: exclusão exige {campo} (o critério que falhou é o motivo relatado no PRISMA)")
            continue
        rodada = p["rodada"] or rodada_padrao_override(raiz, args.etapa, p["id_rs"], todas, estab, est)
        if not rodada:
            raise ErroUso("não há rodada com decisões nesta etapa; informe --rodada")
        _validar_nome(rodada, "rodada")
        if eh_rodada_estabilidade(rodada, estab):
            raise ErroUso(f"{rodada} é rodada de estabilidade: não recebe override")
        p["rodada"] = rodada
    if not erros:
        com_criterio = [p for p in pedidos if p["criterio"]]
        if com_criterio:
            validos, fontes = ids_criterios_validos(raiz, args.etapa, [p["rodada"] for p in com_criterio],
                                                    args.criterios)
            if not validos:
                raise ErroUso(
                    f"não achei os IDs de critério da etapa {args.etapa} (rodadas "
                    f"{sorted({p['rodada'] for p in com_criterio})}: sem lotes, sem 02-triagem/api/<rodada>/criterios.md"
                    + (f", sem codebook de elegibilidade ({ARQ_CODEBOOK_ELEGIBILIDADE}) nem `textos elegibilidade "
                       "consolidar`" if args.etapa == "tc" else "")
                    + "); informe --criterios <arquivo de critérios ou codebook> para conferir o critério")
            for p in com_criterio:
                canonico = canonizar_criterio(p["criterio"], validos)
                if canonico is None:
                    erros.append(f"{p['rotulo']}: critério {p['criterio']!r} não existe entre os IDs válidos "
                                 f"({', '.join(validos)}; fonte: {'; '.join(fontes)})")
                elif canonico != p["criterio"]:
                    p["criterio"] = canonico
    if erros:
        raise ErroUso("override não registrado (nenhuma linha gravada):\n  " + "\n  ".join(erros[:30])
                      + (f"\n  ... e mais {len(erros) - 30}" if len(erros) > 30 else ""))
    novas, ignorados = [], []
    for p in pedidos:
        rodada = p["rodada"]
        vig = decisoes_vigentes(todas, args.etapa, [rodada])
        atual = next((l for l in reversed(vig) if l["id_rs"] == p["id_rs"] and l["revisor"] == args.por
                      and eh_override(l)), None)
        if atual and atual["decisao"] == p["decisao"] and atual.get("motivo_override") == p["motivo"] \
                and atual.get("criterio_falhou") == p["criterio"]:
            ignorados.append(p["id_rs"])
            continue
        sem_override = consolidar_decisoes([l for l in vig if l["id_rs"] == p["id_rs"]], "consenso", False,
                                           ids_sem_resumo(unicos)).get(p["id_rs"])
        override_de = f"{sem_override['decisao_final']}:{sem_override['decidido_por']}" if sem_override else None
        novas.append(nova_decisao(
            p["id_rs"], args.etapa, rodada, args.por, "humano", p["decisao"],
            criterio_falhou=p["criterio"], justificativa=p["motivo"], override_de=override_de,
            motivo_override=p["motivo"]))
    registrar_decisoes(raiz, novas)
    if novas:
        estado.registrar_evento(
            raiz, "decisao_override", ETAPA_PROJETO[args.etapa], "humano", args.por,
            dados={"n": len(novas), "overrides": [
                {"id_rs": l["id_rs"], "rodada": l["rodada"], "decisao": l["decisao"], "override_de": l["override_de"]}
                for l in novas[:200]]},
            motivo=novas[0]["motivo_override"] if len(novas) == 1 else "resolução da fila humana",
            artefatos=[esquema.ARQ_DECISOES])
    rodadas = sorted({l["rodada"] for l in novas})
    if args.etapa == "tc":
        proxima = "textos elegibilidade consolidar (aplica as decisões humanas de texto completo)" if novas else None
    else:
        consolidadas = rodadas_da_ultima_consolidacao(raiz, args.etapa)
        alvo = consolidadas if consolidadas and set(rodadas) <= set(consolidadas) else rodadas
        proxima = f"triagem consolidar --rodada {' --rodada '.join(alvo)}" if rodadas else None
    for aviso in avisos:
        print(f"aviso: {aviso}", file=sys.stderr)
    estado.resumo({
        "comando": "triagem override", "ok": True, "reexecucao": not novas, "registrados": len(novas),
        "ja_registrados": len(ignorados), "rodadas": rodadas, "por": args.por, "proxima_acao": proxima,
        "avisos": avisos,
    })
    return 0


def montar_fila_tc(raiz, master=None, codebook=None, criterios_explicitos=None, verificacao=None):
    """Linhas da fila humana do texto completo (propostas ainda sem decisão humana) e metadados. Não grava nada."""
    from . import textos  # import tardio: textos importa este módulo

    raiz = Path(raiz)
    unicos = ler_unicos(raiz, obrigatorio=False)
    humanas = textos.decisoes_humanas_tc(raiz)
    avisos, criterios = [], []
    if master is not None:
        try:
            propostas, criterios, desconhecidas, avisos_prop = textos.propostas_elegibilidade(
                raiz, resolver(raiz, master), resolver(raiz, codebook), criterios_explicitos,
                resolver(raiz, verificacao) if verificacao else None, unicos=textos.carregar_unicos(raiz))
        except textos.ErroDependencia as e:
            raise ErroDependencia(str(e)) from None
        except ValueError as e:
            raise ErroUso(str(e)) from None
        avisos += avisos_prop
        if desconhecidas:
            avisos.append(f"{len(desconhecidas)} citekeys do master sem chave no projeto (ignoradas): {desconhecidas[:10]}")
        fonte = relativo(raiz, resolver(raiz, master))
        candidatas = [{"id_rs": p["id_rs"], "chave": p["chave"], "proposta": p["decisao"],
                       "criterio_proposto": p["criterio_falhou"], "evidencia": p["evidencia"], "pagina": p["pagina"]}
                      for p in propostas.values()]
    else:
        caminho = raiz / esquema.ARQ_ELEGIBILIDADE_TC_FINAL
        if not caminho.exists():
            raise ErroUso(f"{esquema.ARQ_ELEGIBILIDADE_TC_FINAL} não existe: passe --master e --codebook (fichas de "
                          "elegibilidade) ou rode `textos elegibilidade consolidar --master ... --codebook ...` antes")
        fonte = esquema.ARQ_ELEGIBILIDADE_TC_FINAL
        ev = _ultimo_evento(raiz, "textos_atualizados",
                            lambda e: (e.get("dados") or {}).get("acao") == "elegibilidade_consolidar")
        criterios = list(((ev or {}).get("dados") or {}).get("criterios") or [])
        candidatas = [{"id_rs": l.get("id_rs", "").strip(), "chave": l.get("chave", ""), "proposta": l.get("decisao", ""),
                       "criterio_proposto": l.get("criterio_falhou", ""), "evidencia": l.get("evidencia", ""),
                       "pagina": l.get("pagina", "")}
                      for l in ler_csv(caminho)
                      if l.get("decisao") in esquema.DECISOES and not (l.get("evidencia") or "").startswith("[decisão humana")]
    inativos = ids_inativos(unicos)
    fila, n_humanas, ignorados_inativos = [], 0, []
    for c in candidatas:
        if c["id_rs"] in humanas:
            n_humanas += 1
            continue
        if c["id_rs"] in inativos:
            ignorados_inativos.append(c["id_rs"])
            continue
        fila.append({**c, "criterio_proposto": c["criterio_proposto"] if c["proposta"] == "excluir" else "",
                     "decisao_humana": "", "criterio_humano": "", "motivo": ""})
    if ignorados_inativos:
        avisos.append(f"{len(ignorados_inativos)} textos de buscas substituídas (flag {esquema.FLAG_BUSCA_INATIVA}) "
                      f"ficaram fora da fila: {ignorados_inativos[:10]}")
    fila.sort(key=lambda l: (ORDEM_PROPOSTA_TC.get(l["proposta"], 3), l["id_rs"]))
    return fila, {"fonte": fonte, "criterios": criterios, "n_com_decisao_humana": n_humanas,
                  "n_inativos_ignorados": len(ignorados_inativos), "avisos": avisos}


def cmd_fila(args):
    raiz = estado.exigir_projeto(args.dir)
    if args.etapa != "tc":  # a fila da T/A sai de `triagem consolidar`
        raise ErroUso("`triagem fila` gera a fila do texto completo (--etapa tc); a da T/A sai de `triagem consolidar`")
    if bool(args.master) != bool(args.codebook):
        raise ErroUso("informe --master e --codebook juntos (ou nenhum dos dois, para usar "
                      f"{esquema.ARQ_ELEGIBILIDADE_TC_FINAL})")
    rel = esquema.ARQ_FILA_HUMANA_TC
    caminho = raiz / rel
    todas = ler_decisoes(raiz)
    if caminho.exists():
        _, anteriores, _ = ler_tabela_humana(caminho, COLUNAS_OBRIGATORIAS_FILA, rotulo=rel)
        nao_aplicadas = linhas_fila_nao_aplicadas(anteriores, todas, "tc")
        if nao_aplicadas:
            raise ErroUso(f"{rel} tem {len(nao_aplicadas)} linhas preenchidas ainda não aplicadas ({nao_aplicadas[:10]}); "
                          f"a fila não foi regravada. Aplique com `triagem override --fila {rel} --etapa tc` "
                          "(ou mova o arquivo para outro nome) e gere a fila de novo")
    explicitos = [c.strip() for c in args.criterios.split(",") if c.strip()] if args.criterios else None
    fila, meta = montar_fila_tc(raiz, args.master, args.codebook, explicitos, args.verificacao)
    escrever_csv(caminho, COLUNAS_FILA_HUMANA_TC, fila)
    sha_fila = sha_opcional(caminho)
    propostas = dict(Counter(l["proposta"] for l in fila))
    anterior = _ultimo_evento(raiz, "fila_gerada", lambda ev: (ev.get("dados") or {}).get("arquivo") == rel)
    reexecucao = bool(anterior) and anterior["dados"].get("sha_fila") == sha_fila
    if not reexecucao:
        artefatos = [rel]
        for extra in (args.master, args.codebook, args.verificacao):
            if extra and not Path(relativo(raiz, resolver(raiz, extra))).is_absolute():
                artefatos.append(relativo(raiz, resolver(raiz, extra)))
        estado.registrar_evento(
            raiz, "fila_gerada", ETAPA_PROJETO["tc"], "script", "triagem_lotes",
            dados={"etapa": "tc", "arquivo": rel, "n": len(fila), "propostas": propostas, "fonte": meta["fonte"],
                   "criterios": meta["criterios"], "n_com_decisao_humana": meta["n_com_decisao_humana"],
                   "n_inativos_ignorados": meta["n_inativos_ignorados"], "sha_fila": sha_fila},
            artefatos=artefatos)
    for aviso in meta["avisos"]:
        print(f"aviso: {aviso}", file=sys.stderr)
    ids_validos = meta["criterios"] or ids_criterios_validos(raiz, "tc")[0]
    if fila:
        proxima = (f"humano preenche {rel}: decisao_humana (incluir, excluir ou aguardando), criterio_humano nas "
                   f"exclusões ({', '.join(ids_validos) if ids_validos else 'variáveis-critério do codebook'}) e motivo; "
                   f"depois `triagem override --fila {rel} --etapa tc` e `textos elegibilidade consolidar`")
    else:
        proxima = "todos os textos já têm decisão humana: `textos elegibilidade consolidar` e conferir o G5"
    estado.resumo({
        "comando": "triagem fila", "ok": True, "reexecucao": reexecucao, "etapa": "tc", "arquivo": rel,
        "n": len(fila), "propostas": propostas, "fonte": meta["fonte"], "criterios": ids_validos,
        "n_com_decisao_humana": meta["n_com_decisao_humana"], "n_inativos_ignorados": meta["n_inativos_ignorados"],
        "avisos": meta["avisos"], "proxima_acao": proxima,
    })
    return 0


# ---------------------------------------------------------------------------
# Registro no dispatcher
# ---------------------------------------------------------------------------
def subparsers_do_comando(subparsers, nome, ajuda):
    """Devolve os subcomandos de `nome`, criando o comando só se ainda não existir.

    `triagem` é compartilhado com triagem_api.py (`triagem api`); argparse ≥ 3.11 recusa
    registrar o mesmo nome duas vezes, então quem chega depois reaproveita o existente.
    """
    existente = subparsers._name_parser_map.get(nome)
    if existente is not None:
        for acao in existente._actions:
            if isinstance(acao, argparse._SubParsersAction):
                return acao
        return existente.add_subparsers(dest="subcomando", metavar="<subcomando>")
    parser = subparsers.add_parser(nome, help=ajuda, description=ajuda)

    def _ajuda(args, _parser=parser):
        _parser.print_help()
        return 1

    parser.set_defaults(func=_ajuda)
    return parser.add_subparsers(dest="subcomando", metavar="<subcomando>")


def _protegido(funcao):
    """Converte erros de uso/dados em código 1 com resumo JSON, sem traceback para o usuário."""

    def executar(args):
        try:
            return funcao(args)
        except ErroDependencia as e:
            print(f"erro: {e}", file=sys.stderr)
            estado.resumo({"comando": f"triagem {getattr(args, 'subcomando', '')}".strip(), "ok": False, "erro": str(e),
                           "dependencia_ausente": True})
            return 3
        except (ErroUso, estado.ErroProjeto, ValueError) as e:
            print(f"erro: {e}", file=sys.stderr)
            estado.resumo({"comando": f"triagem {getattr(args, 'subcomando', '')}".strip(), "ok": False, "erro": str(e)})
            return 1

    return executar


def registrar(subparsers):
    sub = subparsers_do_comando(subparsers, "triagem", "triagem de títulos/resumos por lotes, API e consolidação")

    p = sub.add_parser("preparar", help="cria lotes JSON por revisor para subagentes")
    p.add_argument("--etapa", default="ta", choices=esquema.ETAPAS_DECISAO)
    p.add_argument("--rodada", required=True, help="nome da rodada, ex.: ta_v2 (congela a versão dos critérios)")
    p.add_argument("--revisor", required=True, help="A, B, ... ou arbitro")
    p.add_argument("--criterios", required=True, help="arquivo de critérios versionado, ex.: 02-triagem/prompts/ta_v2.md")
    p.add_argument("--tamanho", type=int, default=None, help="registros por lote (padrão 25; árbitro 20)")
    p.add_argument("--semente", type=int, default=7)
    p.add_argument("--ids", default=None, help="CSV com coluna id_rs ou texto com um ID por linha")
    p.add_argument("--apenas-divergentes", action="store_true", help="só divergências da rodada (lotes do árbitro)")
    p.set_defaults(func=_protegido(cmd_preparar))

    p = sub.add_parser("mesclar", help="valida respostas de lote e grava dados/decisoes.jsonl")
    p.add_argument("--rodada", required=True)
    p.add_argument("--revisor", required=True)
    p.add_argument("--modelo", default=None, help="modelo do subagente (vai para o ledger e a declaração de IA)")
    p.add_argument("--tipo-ator", default="ia_subagente", choices=esquema.TIPOS_ATOR)
    p.add_argument("--lote", default=None, help="mesclar só este lote (ex.: lote_003)")
    p.set_defaults(func=_protegido(cmd_mesclar))

    p = sub.add_parser("consolidar", help="decisão final por registro e fila humana")
    p.add_argument("--rodada", required=True, action="append", help="repita para juntar rodadas (a última prevalece)")
    p.add_argument("--regra", default="consenso", choices=["consenso", "liberal"])
    p.add_argument("--etapa", default="ta", choices=esquema.ETAPAS_DECISAO)
    p.set_defaults(func=_protegido(cmd_consolidar))

    p = sub.add_parser("override", help="decisão humana que prevalece sobre IA (um ID ou a fila preenchida)")
    p.add_argument("--id", default=None)
    p.add_argument("--decisao", default=None, choices=esquema.DECISOES + [DECISAO_AGUARDANDO],
                   help="incluir|excluir|incerto; `aguardando` só com --etapa tc (aguardando classificação)")
    p.add_argument("--criterio", default=None,
                   help="critério que falhou: obrigatório em exclusões e conferido contra os IDs da rodada/codebook")
    p.add_argument("--criterios", default=None,
                   help="arquivo de critérios (.md) ou codebook (.csv/.xlsx) para conferir o critério, quando a rodada "
                        "não tem lotes, criterios.md da API nem codebook de elegibilidade")
    p.add_argument("--motivo", default=None)
    p.add_argument("--fila", default=None,
                   help="fila preenchida (csv com , ; ou tab, ou xlsx): fila_humana_<rodada>.csv ou, com --etapa tc, "
                        f"{esquema.ARQ_FILA_HUMANA_TC}")
    p.add_argument("--rodada", default=None,
                   help="padrão: rodada ativa (versoes_ativas); sem ela, a mais recente do ledger; nunca *_estab")
    p.add_argument("--etapa", default="ta", choices=esquema.ETAPAS_DECISAO)
    p.add_argument("--por", default=esquema.PAPEL_HUMANO_PADRAO,
                   help=f"id de papel do humano (padrão {esquema.PAPEL_HUMANO_PADRAO}; nunca nome real)")
    p.set_defaults(func=_protegido(cmd_override))

    p = sub.add_parser("fila", help=f"fila humana do texto completo ({esquema.ARQ_FILA_HUMANA_TC}) com as propostas "
                                    "de elegibilidade ainda sem decisão humana")
    p.add_argument("--etapa", default="tc", choices=["tc"],
                   help="tc (a fila da triagem de títulos e resumos sai de `triagem consolidar`)")
    p.add_argument("--master", default=None,
                   help="fichamentos_master.csv das fichas de elegibilidade (sem ele: 03-textos/elegibilidade_tc_final.csv)")
    p.add_argument("--codebook", default=None, help="codebook de elegibilidade usado nas fichas (com --master)")
    p.add_argument("--verificacao", default=None, help="verificacao_citacoes.csv do gate (reprovadas viram incerto)")
    p.add_argument("--criterios", default=None,
                   help="lista explícita de variáveis-critério, em ordem (com --master; como em textos elegibilidade)")
    p.set_defaults(func=_protegido(cmd_fila))
