"""triagem_api.py — triagem de títulos e resumos via API: dois modelos independentes + árbitro cego.

USO
    # 1) quanto custa? (nenhuma chamada, nenhum pacote ou chave necessários)
    python3 rs.py triagem api --rodada ta_v2 --criterios 02-triagem/prompts/ta_v2.md \\
        --modelo-a claude-haiku-4-5 --modelo-b gpt-4o-mini --arbitro claude-sonnet-5 --estimar

    # 2) teste pequeno, depois a rodada completa (retomável: rode de novo após qualquer queda)
    python3 rs.py triagem api --rodada ta_v2 --criterios 02-triagem/prompts/ta_v2.md \\
        --modelo-a claude-haiku-4-5 --modelo-b gpt-4o-mini --arbitro claude-sonnet-5 --limite 20
    python3 rs.py triagem api ... [--concorrencia 8]

    # 3) modo lote (Batches, ~50% mais barato, assíncrono): cada execução coleta o que
    #    terminou e envia o que falta; repita até `em_andamento` = 0 e `pendentes` = 0
    python3 rs.py triagem api ... --batch

    Depois: `rs.py triagem consolidar --rodada ta_v2` (módulo de lotes) e a validação humana.

O QUE FAZ
    Lê `dados/registros_unicos.csv` (menos os excluídos pelo funil formal com
    `resultado=exclui` e os clusters com a flag `busca_inativa`, de buscas substituídas,
    mesmo quando pedidos em `--ids`), e para cada registro grava em `dados/decisoes.jsonl`, no
    mesmo formato da triagem por subagentes, uma decisão do Revisor A, uma do
    Revisor B e — só quando A e B divergem — uma do árbitro. Cada linha traz
    `tipo_ator=ia_api`, `modelo` e `prompt_sha`. O prompt efetivo de cada papel
    fica congelado em `02-triagem/api/<rodada>/`.

POR QUE ASSIM (correções sobre o script de triagem por API de um projeto anterior, não distribuído)
- Sem resumo -> `incerto` por regra, sem chamada. O script de origem excluía
  ("NO_DATA" virava "Do not include"); registro sem resumo nunca é excluído.
  A linha fica com `revisor=regra`, `tipo_ator=regra`, para não fingir dois revisores.
- Árbitro de terceiro modelo, preferencialmente de outro provedor, e cego. O
  modelo do árbitro deve ser diferente dos dois revisores (senão ele revalidaria a
  própria justificativa). Só há adaptadores anthropic e openai (provedores.py):
  com A e B em provedores diferentes, o árbitro fatalmente repete o provedor de um
  deles; o comando avisa e isso deve constar da declaração de uso de IA. O prompt
  mostra "Revisor A"/"Revisor B" sem nomear modelos, para a decisão não seguir a
  reputação do modelo; a ordem dos dois pareceres é sorteada (de forma
  determinística) por registro, então "Revisor A" no prompt do árbitro não é
  necessariamente o papel A. O árbitro VÊ as duas decisões e justificativas: é
  deliberado (ele resolve a divergência apontando o critério em disputa), e o
  risco de ancoragem é tratado pela instrução de confrontar cada justificativa
  com o texto. Isso deve constar da declaração de uso de IA.
- Instrução depois do texto. O registro vem primeiro e o comando por último na
  mensagem; com a ordem inversa, textos longos fazem o modelo perder o comando.
- Erros re-tentados, nunca pulados. Uma chamada que falha não grava linha
  nenhuma (gravar "erro" faria a retomada pular o registro, que sumiria do
  corpus). Há espera exponencial entre tentativas e uma segunda passada só nos
  que falharam; o que ainda sobrar sai em `pendentes` e o comando termina com
  código 1 para lembrar de rodar de novo.
- `max_tokens`/recusa não são sucesso (ver provedores.py).
- Retomada pela chave (id_rs, rodada, papel): cada decisão é gravada assim que
  chega (append + fsync), então uma queda não perde nem repaga o que já rodou.
  Linha final truncada no JSONL é ignorada na leitura e isolada com uma quebra
  de linha antes do próximo append. A escrita passa pelo mesmo escritor do
  módulo de lotes (`triagem_lotes.registrar_decisoes`, trava `dados/.decisoes.lock`)
  quando ele existe, com um escritor de reserva equivalente; uma trava por
  rodada impede duas execuções simultâneas da API.
- Rodada congelada. Critérios, prompt, modelos e esforço ficam fixos por rodada
  (references/ia-validacao.md, seção 4 B): mudou algo, crie `ta_v3`.
- Divergência padrão = binária (um exclui, o outro inclui ou fica incerto), a
  mesma definição de `triagem consolidar`: incluir × incerto já segue para o
  texto completo e a consolidação não usaria o árbitro. `--divergencia rotulo`
  arbitra qualquer diferença de rótulo (mais caro, útil para análise).
- Trecho que não aparece (com fronteira de palavra) no título ou no resumo é
  descartado da linha, sem invalidar a decisão; a contagem sai no resumo.
- `--estimar` não importa SDK nem faz chamadas: conta caracteres dos prompts
  reais (≈ 4 caracteres por token, VERIFICAR) e usa a tabela de preços de
  provedores.py (VERIFICAR) ou `--precos`. A estimativa entra no log como
  `artefato_versionado` (`dados.tipo = estimativa_custo_api`, `chamadas_api = 0`),
  sem duplicar quando nada mudou; a declaração de IA lista, mas não soma.
- Custo registrado. Cada execução com chamadas grava no evento (`lote_mesclado`,
  `lote_preparado` ou `erro`) `custo_estimado_usd` da execução = tokens informados
  pela API × preço (× desconto de lote), `custo_por_papel` com o custo médio por
  chamada, `custo_estimado_rodada_usd` acumulado e `tabela_precos` usada. Modelo
  sem preço deixa `custo_estimado_usd` nulo (a declaração diz "não registrado").

Códigos de saída: 0 ok (inclusive lote em andamento); 1 erro de uso/dados ou
pendentes após as passadas; 3 pacote/credencial ausente ou recusada.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import esquema, estado, normalizar, provedores
from .importar import buscas as _buscas

try:  # trava de arquivo (Unix). No Windows fica só a trava de thread.
    import fcntl as _fcntl
except ImportError:  # pragma: no cover
    _fcntl = None

ETAPA = "ta"
ETAPA_ESTADO = "06_triagem_ta"
PAPEL_A, PAPEL_B, PAPEL_ARBITRO, PAPEL_REGRA = "A", "B", "arbitro", "regra"
PASTA_API = "02-triagem/api"
ATOR_ID = "triagem_api"
MAX_JUSTIFICATIVA = 600
MAX_PALAVRAS_TRECHO = 25

ESPERA_BASE_SEGUNDOS = 2.0
ESPERA_MAX_SEGUNDOS = 60.0
CHARS_POR_TOKEN = 4.0             # heurística para --estimar (VERIFICAR com count_tokens se o orçamento importar)
TOKENS_SAIDA_ESTIMADOS = 180      # JSON de decisão curto (verificar)
TOKENS_PENSAMENTO_ESTIMADOS = 800  # modelos que pensam por padrão (verificar)
DESCONTO_LOTE = 0.5               # Batches da Anthropic e da OpenAI (verificar)
TAMANHO_MAX_LOTE = 10000

RESUMOS_PLACEHOLDER = {
    "no abstract available", "[no abstract available]", "abstract not available", "no abstract",
    "sem resumo", "resumo nao disponivel", "resumo indisponivel", "sin resumen", "resumen no disponible",
}

_dormir = time.sleep              # substituível nos testes
_TRAVA_THREAD = threading.Lock()


class ErroUso(RuntimeError):
    """Entrada inválida ou rodada inconsistente (exit 1)."""


# ---------------------------------------------------------------------------
# decisoes.jsonl: leitura tolerante e escrita com trava
# ---------------------------------------------------------------------------
def ler_decisoes(caminho):
    """Linhas válidas do JSONL; linha truncada por queda é ignorada (nunca reescrita)."""
    caminho = Path(caminho)
    linhas = []
    if not caminho.exists():
        return linhas
    with open(caminho, encoding="utf-8", errors="replace") as f:
        for bruta in f:
            bruta = bruta.strip()
            if not bruta:
                continue
            try:
                obj = json.loads(bruta)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                linhas.append(obj)
    return linhas


def _escritor_lotes():
    """`triagem_lotes.registrar_decisoes`, se o módulo de lotes estiver instalado.

    Um único escritor do ledger (mesma validação, mesma trava) evita que a triagem
    por subagentes e a por API corram em paralelo sem se excluírem.
    """
    try:
        from . import triagem_lotes
    except ImportError:
        return None
    return getattr(triagem_lotes, "registrar_decisoes", None)


def anexar_decisoes(raiz, linhas):
    """Acrescenta decisões a dados/decisoes.jsonl com trava de thread e de arquivo, e fsync."""
    if not linhas:
        return 0
    with _TRAVA_THREAD:
        escritor = _escritor_lotes()
        if escritor is not None:
            return escritor(raiz, linhas)
        return _anexar_local(Path(raiz) / esquema.ARQ_DECISOES, linhas)


def _anexar_local(caminho, linhas):
    """Escritor de reserva (sem o módulo de lotes), com a MESMA trava `dados/.decisoes.lock`.

    Se o arquivo termina sem quebra de linha (append anterior interrompido), escreve
    uma quebra antes, para a linha nova não colar no fragmento truncado.
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    corpo = b"".join(json.dumps({c: l.get(c) for c in esquema.CAMPOS_DECISAO}, ensure_ascii=False).encode("utf-8")
                     + b"\n" for l in linhas)
    with open(caminho.parent / ".decisoes.lock", "a+") as trava:
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


def indice_decisoes(linhas, rodada, etapa=ETAPA):
    """{(id_rs, papel): linha} da rodada; a última linha por chave vence."""
    indice = {}
    for linha in linhas:
        if linha.get("rodada") == rodada and linha.get("etapa") == etapa and linha.get("id_rs"):
            indice[(linha["id_rs"], linha.get("revisor"))] = linha
    return indice


# ---------------------------------------------------------------------------
# Entradas
# ---------------------------------------------------------------------------
def ler_registros(raiz):
    caminho = Path(raiz) / esquema.ARQ_UNICOS
    if not caminho.exists():
        raise ErroUso(f"{esquema.ARQ_UNICOS} não existe. Rode `rs.py importar` e `rs.py dedup` antes da triagem.")
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)
        faltando = {"id_rs", "titulo", "resumo"} - set(leitor.fieldnames or [])
        if faltando:
            raise ErroUso(f"{esquema.ARQ_UNICOS} sem colunas {sorted(faltando)}")
        registros = [dict(l) for l in leitor if (l.get("id_rs") or "").strip()]
    vistos = set()
    for r in registros:
        if r["id_rs"] in vistos:
            raise ErroUso(f"id_rs duplicado em {esquema.ARQ_UNICOS}: {r['id_rs']}")
        vistos.add(r["id_rs"])
    return registros


def ids_excluidos_filtro(raiz):
    """IDs que o funil formal excluiu (só existe exclusão se prevista no protocolo)."""
    caminho = Path(raiz) / esquema.ARQ_FILTRO_FORMAL
    if not caminho.exists():
        return set()
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return {l["id_rs"] for l in csv.DictReader(f) if (l.get("resultado") or "").strip() == "exclui"}


def ler_ids_arquivo(caminho):
    """Aceita planilha com coluna id_rs (CSV com `,` `;` ou tab, BOM, cp1252, xlsx) ou um id por linha.

    Usa o mesmo leitor de planilhas humanas da triagem por lotes (`triagem_lotes.ler_ids_arquivo`), para que
    uma lista salva pelo Excel com ponto e vírgula não vire uma lista de IDs inválidos; sem o módulo de lotes,
    cai no leitor simples abaixo.
    """
    try:
        from . import triagem_lotes
    except ImportError:  # pragma: no cover - instalação sem o módulo de lotes
        triagem_lotes = None
    if triagem_lotes is not None:
        try:
            return set(triagem_lotes.ler_ids_arquivo(caminho))
        except triagem_lotes.ErroUso as e:
            raise ErroUso(str(e)) from None
    texto = Path(caminho).read_text(encoding="utf-8-sig")
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    if linhas and "id_rs" in [c.strip() for c in linhas[0].split(",")]:
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            return {l["id_rs"].strip() for l in csv.DictReader(f) if (l.get("id_rs") or "").strip()}
    return {l.split(",")[0].strip() for l in linhas}


def sem_resumo(valor):
    """True se não há resumo utilizável (vazio ou marcador de 'sem resumo' da base)."""
    texto = normalizar.texto(valor)
    if not texto:
        return True
    return normalizar.ascii_fold(texto).lower().strip(" .") in RESUMOS_PLACEHOLDER


# Mesmo padrão de triagem_lotes.PADRAO_CRITERIO: os dois modos aceitam os mesmos critérios.
_RE_ID_CRITERIO_C = re.compile(r"\b(C\d{1,2}[A-Z]?)\b")
# Reserva para arquivos que numeram critérios com outra letra (E1, I2...), só no início da linha.
_RE_ID_CRITERIO_LINHA = re.compile(
    r"^\s*(?:[#>*|+\-]+\s*|\d+[.)]\s*)*(?:\*\*|__|\[)?\s*([A-Z]{1,3}\d{1,3}[A-Z]?)(?:\*\*|__|\])?(?=[\s:.)\-–—|*]|$)",
    re.MULTILINE,
)


def extrair_ids_criterios(texto):
    """IDs de critério definidos no arquivo, com a MESMA regra do modo por subagentes.

    Delegar a triagem_lotes.ids_criterios evita que os dois modos aceitem listas diferentes
    (ex.: uma menção "ver C5" no texto contada como definição). Sem o módulo, cai na regra local.
    """
    try:
        from .triagem_lotes import ids_criterios as _ids_criterios_lotes
        return _ids_criterios_lotes(texto)
    except ImportError:
        pass
    for padrao in (_RE_ID_CRITERIO_C, _RE_ID_CRITERIO_LINHA):
        ids = []
        for m in padrao.finditer(texto or ""):
            if m.group(1) not in ids:
                ids.append(m.group(1))
        if ids:
            return ids
    return []


# ---------------------------------------------------------------------------
# Prompts e esquema
# ---------------------------------------------------------------------------
def schema_resposta(ids_criterios):
    """JSON Schema aceito pela saída estruturada dos dois provedores (sem min/max, objetos fechados)."""
    criterio = ({"anyOf": [{"type": "string", "enum": list(ids_criterios)}, {"type": "null"}]}
                if ids_criterios else {"anyOf": [{"type": "string"}, {"type": "null"}]})
    return {
        "type": "object",
        "properties": {
            "decisao": {"type": "string", "enum": list(esquema.DECISOES)},
            "criterio_falhou": criterio,
            "justificativa": {"type": "string"},
            "trecho": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        },
        "required": ["decisao", "criterio_falhou", "justificativa", "trecho"],
        "additionalProperties": False,
    }


_REGRAS_DECISAO = """\
Regras de decisão:
- "incluir": o registro plausivelmente atende a todos os critérios.
- "excluir": o título ou o resumo mostra com clareza que ao menos um critério NÃO é atendido. Informe em "criterio_falhou" o identificador do primeiro critério que falha.
- "incerto": a informação disponível é insuficiente ou ambígua. Entre excluir e incerto, prefira incerto: nesta etapa perder um estudo elegível custa mais do que ler um texto a mais.
- Distinga o estudo que ESTUDA o objeto de um critério daquele que apenas o MENCIONA.
- Decida só com o título, o resumo e os metadados fornecidos; não use conhecimento externo sobre a publicação.
- "trecho": copie literalmente do título ou do resumo um fragmento de até 25 palavras que sustente a decisão, ou null.
- "justificativa": de 1 a 3 frases, em português, citando o critério decisivo."""


def montar_sistema_revisor(criterios):
    return (
        "Você é um revisor independente na etapa de triagem de títulos e resumos de uma revisão sistemática. "
        "Para cada registro, decida se ele segue para a leitura do texto completo aplicando os critérios de "
        "elegibilidade abaixo, exatamente como escritos.\n\n"
        f"<criterios>\n{criterios.strip()}\n</criterios>\n\n{_REGRAS_DECISAO}"
    )


def montar_sistema_arbitro(criterios):
    return (
        "Você é o árbitro de uma triagem de títulos e resumos de uma revisão sistemática. Dois revisores "
        "independentes, identificados só como Revisor A e Revisor B, avaliaram o mesmo registro com os mesmos "
        "critérios e chegaram a decisões diferentes. Não siga o revisor que parece mais confiante nem o que "
        "escreveu mais: confronte cada justificativa com os critérios e com o texto do registro e chegue à sua "
        "própria decisão.\n\n"
        f"<criterios>\n{criterios.strip()}\n</criterios>\n\n{_REGRAS_DECISAO}"
    )


INSTRUCAO_REVISOR = (
    "Releia os critérios de elegibilidade e decida sobre o registro acima. Responda apenas com o objeto JSON "
    "com os campos decisao, criterio_falhou, justificativa e trecho."
)
INSTRUCAO_ARBITRO = (
    "Releia os critérios de elegibilidade, confronte as duas avaliações com o texto do registro acima e dê a "
    "decisão final. Na justificativa, diga em que critério os revisores divergiram. Responda apenas com o "
    "objeto JSON com os campos decisao, criterio_falhou, justificativa e trecho."
)


def montar_registro(reg):
    """Bloco do registro (sem id nem fonte de busca: o modelo não precisa deles)."""
    partes = [f"Título: {normalizar.texto(reg.get('titulo')) or '(sem título)'}"]
    resumo = normalizar.texto(reg.get("resumo"))
    if resumo:
        truncado = str(reg.get("resumo_truncado") or "").strip() in {"1", "true", "True"}
        partes.append(f"Resumo{' (truncado na base de origem)' if truncado else ''}: {resumo}")
    for rotulo, campo in (("Palavras-chave", "palavras_chave"), ("Veículo", "veiculo"), ("Ano", "ano"),
                          ("Tipo de publicação", "tipo_publicacao"), ("Idioma", "idioma")):
        valor = normalizar.texto(reg.get(campo))
        if valor:
            partes.append(f"{rotulo}: {valor}")
    return "<registro>\n" + "\n".join(partes) + "\n</registro>"


def montar_usuario_revisor(reg):
    return f"{montar_registro(reg)}\n\n{INSTRUCAO_REVISOR}"


def _bloco_avaliacao(rotulo, linha):
    return (
        f"<{rotulo}>\nDecisão: {linha.get('decisao')}\n"
        f"Critério que falhou: {linha.get('criterio_falhou') or 'nenhum'}\n"
        f"Justificativa: {linha.get('justificativa') or ''}\n"
        f"Trecho: {linha.get('trecho') or 'nenhum'}\n</{rotulo}>"
    )


def ordem_trocada(rodada, id_rs):
    """Sorteio determinístico da ordem dos pareceres mostrados ao árbitro.

    Sem isso o árbitro veria sempre o mesmo modelo como "Revisor A" e poderia aprender
    um viés de posição. É determinístico para o prompt de cada registro ser reprodutível.
    """
    return random.Random(f"{rodada}:{id_rs}").random() < 0.5


def montar_usuario_arbitro(reg, linha_a, linha_b, trocar=False):
    """Os rótulos 'Revisor A/B' seguem a ordem de exibição, não o papel real (árbitro cego)."""
    primeiro, segundo = (linha_b, linha_a) if trocar else (linha_a, linha_b)
    return (f"{montar_registro(reg)}\n\n{_bloco_avaliacao('revisor_a', primeiro)}\n\n"
            f"{_bloco_avaliacao('revisor_b', segundo)}\n\n{INSTRUCAO_ARBITRO}")


_REGISTRO_MODELO = {"titulo": "{titulo}", "resumo": "{resumo}", "palavras_chave": "{palavras_chave}",
                    "veiculo": "{veiculo}", "ano": "{ano}", "tipo_publicacao": "{tipo_publicacao}",
                    "idioma": "{idioma}"}
_AVALIACAO_MODELO = {"decisao": "{decisao}", "criterio_falhou": "{criterio_falhou}",
                     "justificativa": "{justificativa}", "trecho": "{trecho}"}


def documento_prompt(rodada, papel, sistema, usuario_modelo, schema):
    """Texto congelado do prompt de um papel. Determinístico (sem data): seu sha256 é o prompt_sha."""
    return (
        f"# Prompt da triagem via API — rodada {rodada} — {papel}\n\n"
        f"## Sistema\n\n{sistema}\n\n"
        f"## Mensagem do usuário (modelo; campos vazios são omitidos)\n\n{usuario_modelo}\n\n"
        f"## Esquema de saída\n\n```json\n{json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True)}\n```\n"
    )


# ---------------------------------------------------------------------------
# Validação da resposta
# ---------------------------------------------------------------------------
def validar_resposta(dados, ids_criterios, registro):
    """Normaliza a resposta do modelo ou levanta RespostaInvalida (que será re-tentada).

    Devolve (resposta, trecho_descartado). Trecho que não aparece no título/resumo
    normalizados é descartado (vira null) em vez de invalidar a decisão: é apoio,
    não prova, e a decisão continua auditável pela justificativa.
    """
    if not isinstance(dados, dict):
        raise provedores.RespostaInvalida("resposta não é objeto")
    decisao = str(dados.get("decisao") or "").strip().lower()
    if decisao not in esquema.DECISOES:
        raise provedores.RespostaInvalida(f"decisao inválida: {dados.get('decisao')!r}")
    criterio = dados.get("criterio_falhou")
    criterio = None if criterio is None or str(criterio).strip().lower() in {"", "null", "none", "nenhum"} \
        else str(criterio).strip()
    if criterio is not None and ids_criterios:
        mapa = {c.upper(): c for c in ids_criterios}
        if criterio.upper() not in mapa:
            raise provedores.RespostaInvalida(f"criterio_falhou {criterio!r} não existe nos critérios")
        criterio = mapa[criterio.upper()]
    if decisao == "excluir" and ids_criterios and criterio is None:
        raise provedores.RespostaInvalida("exclusão sem criterio_falhou")
    if decisao == "incluir":
        criterio = None
    justificativa = normalizar.texto(dados.get("justificativa"))[:MAX_JUSTIFICATIVA] or None
    trecho = normalizar.texto(dados.get("trecho")) or None
    descartado = False
    if trecho and not trecho_confere(trecho, registro):
        trecho, descartado = None, True
    return {"decisao": decisao, "criterio_falhou": criterio, "justificativa": justificativa,
            "trecho": trecho}, descartado


def trecho_confere(trecho, registro):
    """Trecho normalizado aparece, com fronteira de palavra, no título OU no resumo (mesma regra dos lotes)."""
    alvo = normalizar.titulo_normalizado(trecho)
    if not alvo or len(str(trecho).split()) > MAX_PALAVRAS_TRECHO * 2:
        return False
    alvo = f" {alvo} "
    return any(alvo in f" {normalizar.titulo_normalizado(registro.get(campo))} " for campo in ("titulo", "resumo"))


def eh_divergente(linha_a, linha_b, modo="binaria"):
    a, b = linha_a.get("decisao"), linha_b.get("decisao")
    if modo == "binaria":
        return (a == "excluir") != (b == "excluir")
    return a != b


# ---------------------------------------------------------------------------
# Contexto de execução
# ---------------------------------------------------------------------------
class Contexto:
    """Tudo que uma rodada precisa, montado uma vez e compartilhado pelas threads."""

    def __init__(self, raiz, args):
        self.raiz = Path(raiz)
        self.args = args
        self.rodada = args.rodada
        if not re.match(r"^[A-Za-z0-9_.-]{1,60}$", self.rodada or ""):
            raise ErroUso("--rodada deve ter só letras, dígitos, _ . - (ex.: ta_v2)")
        self.caminho_decisoes = self.raiz / esquema.ARQ_DECISOES
        self.pasta = self.raiz / PASTA_API / self.rodada

        caminho_criterios = Path(args.criterios)
        if not caminho_criterios.is_absolute() and not caminho_criterios.exists():
            caminho_criterios = self.raiz / args.criterios
        if not caminho_criterios.exists():
            raise ErroUso(f"arquivo de critérios não encontrado: {args.criterios}")
        self.criterios = caminho_criterios.read_text(encoding="utf-8")
        if not self.criterios.strip():
            raise ErroUso("arquivo de critérios vazio")
        self.criterios_rel = _relativo(caminho_criterios, self.raiz)
        self.criterios_sha = estado.sha256_texto(self.criterios)
        self.ids_criterios = extrair_ids_criterios(self.criterios)
        self.schema = schema_resposta(self.ids_criterios)

        self.tabela_precos = dict(provedores.MODELOS_CONHECIDOS)
        if getattr(args, "precos", None):
            self.tabela_precos.update(json.loads(Path(args.precos).read_text(encoding="utf-8")))
        self.especificacoes = {PAPEL_A: args.modelo_a, PAPEL_B: args.modelo_b, PAPEL_ARBITRO: args.arbitro}
        try:
            self.resolvidos = {p: provedores.resolver_modelo(m) for p, m in self.especificacoes.items()}
        except ValueError as e:
            raise ErroUso(str(e)) from None
        self.modelos = {p: r[1] for p, r in self.resolvidos.items()}
        base = {p: provedores.modelo_base(m) for p, m in self.modelos.items()}
        if base[PAPEL_A] == base[PAPEL_B]:
            raise ErroUso("--modelo-a e --modelo-b precisam ser modelos diferentes (revisores independentes)")
        if base[PAPEL_ARBITRO] in (base[PAPEL_A], base[PAPEL_B]):
            raise ErroUso("o árbitro precisa ser um terceiro modelo, diferente dos dois revisores "
                          "(senão revalida a própria justificativa)")
        self.avisos = []
        if self.resolvidos[PAPEL_A][0] == self.resolvidos[PAPEL_B][0]:
            self.avisos.append("modelo-a e modelo-b são do mesmo provedor; revisores de provedores diferentes "
                               "erram de forma menos correlacionada")
        if self.resolvidos[PAPEL_ARBITRO][0] in (self.resolvidos[PAPEL_A][0], self.resolvidos[PAPEL_B][0]):
            self.avisos.append(f"árbitro do mesmo provedor ({self.resolvidos[PAPEL_ARBITRO][0]}) de um revisor: o "
                               "árbitro é um terceiro modelo, preferencialmente de outro provedor (só há adaptadores "
                               "anthropic e openai); declare isso na declaração de uso de IA")
        if not self.ids_criterios:
            self.avisos.append("nenhum id de critério (C1, C2...) encontrado no arquivo; criterio_falhou fica livre")

        self.sistema_revisor = montar_sistema_revisor(self.criterios)
        self.sistema_arbitro = montar_sistema_arbitro(self.criterios)
        self.doc_revisor = documento_prompt(self.rodada, "revisores A e B", self.sistema_revisor,
                                            montar_usuario_revisor(_REGISTRO_MODELO), self.schema)
        self.doc_arbitro = documento_prompt(self.rodada, "árbitro", self.sistema_arbitro,
                                            montar_usuario_arbitro(_REGISTRO_MODELO, _AVALIACAO_MODELO,
                                                                   _AVALIACAO_MODELO), self.schema)
        self.prompt_sha = {"revisor": estado.sha256_texto(self.doc_revisor),
                           "arbitro": estado.sha256_texto(self.doc_arbitro)}

        registros = ler_registros(self.raiz)
        self.excluidos_filtro = ids_excluidos_filtro(self.raiz)
        restritos = ler_ids_arquivo(args.ids) if getattr(args, "ids", None) else None
        self.registros = {}
        self.ids_inativos = []
        for r in registros:
            if restritos is not None and r["id_rs"] not in restritos:
                continue
            if _buscas.cluster_inativo(r):  # só registros de buscas substituídas: fora do conjunto ativo
                self.ids_inativos.append(r["id_rs"])
                continue
            if r["id_rs"] in self.excluidos_filtro:
                continue
            self.registros[r["id_rs"]] = r
        if self.ids_inativos:
            self.avisos.append(f"{len(self.ids_inativos)} registros únicos de buscas substituídas (flag "
                               f"{esquema.FLAG_BUSCA_INATIVA}) ficaram fora da triagem: {self.ids_inativos[:10]}")
        self.n_registros_total = len(registros)
        self.provedores = {}
        self._trava = threading.Lock()
        self.contadores = {"retentativas": 0, "trechos_descartados": 0}
        self.ultimos_erros = {}

    # -- utilidades --------------------------------------------------------
    def contar(self, chave, n=1):
        with self._trava:
            self.contadores[chave] = self.contadores.get(chave, 0) + n

    def sistema_de(self, papel):
        return self.sistema_arbitro if papel == PAPEL_ARBITRO else self.sistema_revisor

    def sha_de(self, papel):
        return self.prompt_sha["arbitro" if papel == PAPEL_ARBITRO else "revisor"]

    def linha_decisao(self, id_rs, papel, resposta, lote):
        return {
            "id_rs": id_rs, "etapa": ETAPA, "rodada": self.rodada, "revisor": papel, "tipo_ator": "ia_api",
            "modelo": self.modelos[papel], "prompt_sha": self.sha_de(papel),
            "decisao": resposta["decisao"], "criterio_falhou": resposta["criterio_falhou"],
            "justificativa": resposta["justificativa"], "trecho": resposta["trecho"], "lote": lote,
            "ts": estado.agora(), "override_de": None, "motivo_override": None,
        }

    def linha_regra(self, id_rs):
        return {
            "id_rs": id_rs, "etapa": ETAPA, "rodada": self.rodada, "revisor": PAPEL_REGRA, "tipo_ator": "regra",
            "modelo": None, "prompt_sha": None, "decisao": "incerto", "criterio_falhou": None,
            "justificativa": "Registro sem resumo: a triagem por API não decide sem resumo; segue como incerto "
                             "(nunca exclusão) para verificação no texto completo.",
            "trecho": None, "lote": "regra_sem_resumo", "ts": estado.agora(),
            "override_de": None, "motivo_override": None,
        }

    def parametros_publicos(self):
        if self.provedores:
            return {p: prov.parametros_publicos() for p, prov in self.provedores.items()}
        return {p: {"provedor": self.resolvidos[p][0], "modelo": m, "esforco": self.args.esforco,
                    "max_tokens": self.args.max_tokens,
                    "temperature": 0 if provedores.aceita_temperature(m) else None}
                for p, m in self.modelos.items()}


def _relativo(caminho, raiz):
    try:
        return str(Path(caminho).resolve().relative_to(Path(raiz).resolve()))
    except ValueError:
        return str(caminho)


# ---------------------------------------------------------------------------
# Congelamento da rodada
# ---------------------------------------------------------------------------
def _checar_congelamento(ctx, indice):
    """Mesma rodada = mesmos critérios, prompts, modelos e esforço. Senão, ErroUso."""
    for papel in (PAPEL_A, PAPEL_B, PAPEL_ARBITRO):
        usados = {l.get("modelo") for (i, p), l in indice.items() if p == papel and l.get("tipo_ator") == "ia_api"}
        usados.discard(None)
        if usados and usados != {ctx.modelos[papel]}:
            raise ErroUso(f"a rodada {ctx.rodada} já tem decisões do papel {papel} com {sorted(usados)}; "
                          f"agora foi pedido {ctx.modelos[papel]}. Rodadas são congeladas: use nova rodada.")
    params = ctx.pasta / "parametros.json"
    if params.exists():
        antigo = json.loads(params.read_text(encoding="utf-8"))
        atual = _parametros_congelados(ctx)
        # o caminho do arquivo de critérios pode mudar (cópia, outra pasta); o conteúdo (sha) não
        diferencas = [k for k in atual if k != "criterios" and antigo.get(k) != atual[k]]
        if diferencas:
            raise ErroUso(f"a rodada {ctx.rodada} foi congelada com outros valores de {diferencas} "
                          f"(critérios/prompt/modelos/esforço). Crie uma nova rodada (ex.: {ctx.rodada}_v2).")


def _parametros_congelados(ctx):
    return {
        "rodada": ctx.rodada, "etapa": ETAPA, "criterios": ctx.criterios_rel, "criterios_sha": ctx.criterios_sha,
        "prompt_sha_revisor": ctx.prompt_sha["revisor"], "prompt_sha_arbitro": ctx.prompt_sha["arbitro"],
        "modelo_a": ctx.modelos[PAPEL_A], "modelo_b": ctx.modelos[PAPEL_B], "arbitro": ctx.modelos[PAPEL_ARBITRO],
        "esforco": ctx.args.esforco,
    }


def _congelar_rodada(ctx):
    """Grava prompts e parâmetros na primeira execução. Devolve lista de artefatos novos."""
    ctx.pasta.mkdir(parents=True, exist_ok=True)
    novos = []
    arquivos = {
        "prompt_revisor.md": ctx.doc_revisor,
        "prompt_arbitro.md": ctx.doc_arbitro,
        "criterios.md": ctx.criterios,
        "parametros.json": json.dumps(_parametros_congelados(ctx), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    }
    for nome, conteudo in arquivos.items():
        destino = ctx.pasta / nome
        if not destino.exists():
            destino.write_text(conteudo, encoding="utf-8")
            novos.append(_relativo(destino, ctx.raiz))
    return novos


class _TravaRodada:
    """Impede duas execuções simultâneas da mesma rodada (chamariam a API em dobro)."""

    def __init__(self, pasta):
        self.caminho = Path(pasta) / ".executando.lock"
        self.arquivo = None

    def __enter__(self):
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.arquivo = open(self.caminho, "a+")
        if _fcntl:
            try:
                _fcntl.flock(self.arquivo.fileno(), _fcntl.LOCK_EX | _fcntl.LOCK_NB)
            except OSError:
                self.arquivo.close()
                raise ErroUso("outra execução desta rodada está em andamento") from None
        return self

    def __exit__(self, *exc):
        if _fcntl:
            _fcntl.flock(self.arquivo.fileno(), _fcntl.LOCK_UN)
        self.arquivo.close()
        return False


# ---------------------------------------------------------------------------
# Planejamento
# ---------------------------------------------------------------------------
def planejar(ctx, indice, limite=None):
    """Decide o que falta: linhas de regra, tarefas A/B e tarefas de árbitro."""
    regra, ab = [], []
    candidatos = []
    for id_rs, reg in ctx.registros.items():
        if (id_rs, PAPEL_REGRA) in indice:
            continue
        if sem_resumo(reg.get("resumo")):
            regra.append(id_rs)
            continue
        faltam = [p for p in (PAPEL_A, PAPEL_B) if (id_rs, p) not in indice]
        if faltam:
            candidatos.append((id_rs, faltam))
    if limite is not None:
        candidatos = candidatos[:max(0, limite)]
    for id_rs, faltam in candidatos:
        ab.extend((id_rs, p) for p in faltam)
    return regra, ab, tarefas_arbitro(ctx, indice)


def tarefas_arbitro(ctx, indice):
    tarefas = []
    for id_rs in ctx.registros:
        a, b = indice.get((id_rs, PAPEL_A)), indice.get((id_rs, PAPEL_B))
        if a and b and (id_rs, PAPEL_ARBITRO) not in indice and eh_divergente(a, b, ctx.args.divergencia):
            tarefas.append((id_rs, PAPEL_ARBITRO))
    return tarefas


def mensagem_usuario(ctx, indice, id_rs, papel):
    reg = ctx.registros[id_rs]
    if papel == PAPEL_ARBITRO:
        return montar_usuario_arbitro(reg, indice[(id_rs, PAPEL_A)], indice[(id_rs, PAPEL_B)],
                                      trocar=ordem_trocada(ctx.rodada, id_rs))
    return montar_usuario_revisor(reg)


# ---------------------------------------------------------------------------
# Execução síncrona
# ---------------------------------------------------------------------------
def _espera(tentativa):
    return min(ESPERA_MAX_SEGUNDOS, ESPERA_BASE_SEGUNDOS * (2 ** (tentativa - 1))) + random.uniform(0, 1)


def _rodar_tarefa(ctx, id_rs, papel, usuario):
    """Uma decisão com re-tentativas. Grava a linha assim que valida; nunca grava falha."""
    prov = ctx.provedores[papel]
    ultimo = None
    for tentativa in range(max(1, ctx.args.tentativas)):
        if tentativa:
            _dormir(_espera(tentativa))
        try:
            dados = prov.decidir(ctx.sistema_de(papel), usuario, ctx.schema)
            resposta, descartado = validar_resposta(dados, ctx.ids_criterios, ctx.registros[id_rs])
        except provedores.ErroFatal:
            raise
        except provedores.ErroRequisicao as exc:
            ultimo = exc
            break
        except Exception as exc:  # noqa: BLE001 - transitório, resposta inválida ou falha desconhecida: repetir
            ultimo = exc
            ctx.contar("retentativas")
            continue
        if descartado:
            ctx.contar("trechos_descartados")
        anexar_decisoes(ctx.raiz, [ctx.linha_decisao(id_rs, papel, resposta, lote="api")])
        return True, None
    return False, f"{type(ultimo).__name__}: {ultimo}"


def _executar_fase(ctx, tarefas_msgs):
    """Roda tarefas em paralelo. Exceções fatais (ou quedas) cancelam o que não começou."""
    novas, falhas = 0, {}
    if not tarefas_msgs:
        return novas, falhas
    executor = ThreadPoolExecutor(max_workers=max(1, ctx.args.concorrencia))
    try:
        futuros = {executor.submit(_rodar_tarefa, ctx, i, p, u): (i, p) for i, p, u in tarefas_msgs}
        for futuro in as_completed(futuros):
            ok, erro = futuro.result()
            if ok:
                novas += 1
            else:
                falhas[futuros[futuro]] = erro
    except BaseException:
        executor.shutdown(wait=True, cancel_futures=True)
        raise
    executor.shutdown(wait=True)
    return novas, falhas


def _executar_com_passadas(ctx, indice, tarefas):
    novas_total = 0
    pendentes = list(tarefas)
    falhas = {}
    for _ in range(max(1, ctx.args.passadas)):
        if not pendentes:
            break
        msgs = [(i, p, mensagem_usuario(ctx, indice, i, p)) for i, p in pendentes]
        novas, falhas = _executar_fase(ctx, msgs)
        novas_total += novas
        pendentes = [t for t in pendentes if t in falhas]
    return novas_total, {t: falhas[t] for t in pendentes}


def rodar_sincrono(ctx, limite):
    indice = indice_decisoes(ler_decisoes(ctx.caminho_decisoes), ctx.rodada)
    regra, ab, _ = planejar(ctx, indice, limite)
    anexar_decisoes(ctx.raiz, [ctx.linha_regra(i) for i in regra])
    novas_ab, falhas_ab = _executar_com_passadas(ctx, indice, ab)

    indice = indice_decisoes(ler_decisoes(ctx.caminho_decisoes), ctx.rodada)
    arb = tarefas_arbitro(ctx, indice)
    novas_arb, falhas_arb = _executar_com_passadas(ctx, indice, arb)
    pendentes = {**falhas_ab, **falhas_arb}
    return {"novas_regra": len(regra), "novas_ab": novas_ab, "novas_arbitro": novas_arb,
            "pendentes": pendentes, "lotes_enviados": [], "lotes_em_andamento": 0}


# ---------------------------------------------------------------------------
# Execução em lote (Batches)
# ---------------------------------------------------------------------------
def _custom_id(id_rs, papel):
    return f"{id_rs}__{papel}"


def _ler_estado_lotes(ctx):
    caminho = ctx.pasta / "lotes_batch.json"
    if not caminho.exists():
        return {"lotes": [], "falhas": {}}
    return json.loads(caminho.read_text(encoding="utf-8"))


def _salvar_estado_lotes(ctx, dados):
    caminho = ctx.pasta / "lotes_batch.json"
    tmp = caminho.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, caminho)


def rodar_lote(ctx, limite):
    """Coleta lotes terminados, grava decisões válidas e envia o que ainda falta."""
    for papel, prov in ctx.provedores.items():
        if not prov.suporta_lote:
            raise ErroUso(f"o provedor de {papel} ({prov.nome}) não suporta --batch")
    registro_lotes = _ler_estado_lotes(ctx)
    falhas = registro_lotes.setdefault("falhas", {})
    indice = indice_decisoes(ler_decisoes(ctx.caminho_decisoes), ctx.rodada)
    novas = {PAPEL_A: 0, PAPEL_B: 0, PAPEL_ARBITRO: 0}
    em_andamento, ocupados = 0, set()

    for lote in registro_lotes["lotes"]:
        if lote["status"] != "em_andamento":
            continue
        papel = lote["papel"]
        if lote["modelo"] != ctx.modelos[papel]:
            raise ErroUso(f"lote {lote['id']} foi enviado com {lote['modelo']}, não com {ctx.modelos[papel]}")
        status, resultados = ctx.provedores[papel].coletar_lote(lote["id"])
        if status != "concluido":
            em_andamento += 1
            ocupados.update(lote["custom_ids"])
            continue
        linhas = []
        for cid in lote["custom_ids"]:
            id_rs = cid.rsplit("__", 1)[0]
            if (id_rs, papel) in indice or id_rs not in ctx.registros:
                continue
            resultado = resultados.get(cid)
            try:
                if not isinstance(resultado, dict):
                    raise resultado if isinstance(resultado, Exception) else provedores.RespostaInvalida("sem resultado")
                resposta, descartado = validar_resposta(resultado, ctx.ids_criterios, ctx.registros[id_rs])
            except Exception as exc:  # noqa: BLE001 - fica pendente e volta no próximo envio
                falhas[cid] = falhas.get(cid, 0) + 1
                ctx.ultimos_erros[cid] = f"{type(exc).__name__}: {exc}"
                continue
            if descartado:
                ctx.contar("trechos_descartados")
            linha = ctx.linha_decisao(id_rs, papel, resposta, lote=lote["id"])
            linhas.append(linha)
            indice[(id_rs, papel)] = linha
            novas[papel] += 1
        anexar_decisoes(ctx.raiz, linhas)
        lote["status"] = "coletado"
        lote["coletado_em"] = estado.agora()
        _salvar_estado_lotes(ctx, registro_lotes)

    indice = indice_decisoes(ler_decisoes(ctx.caminho_decisoes), ctx.rodada)
    regra, ab, arb = planejar(ctx, indice, limite)
    anexar_decisoes(ctx.raiz, [ctx.linha_regra(i) for i in regra])
    esgotados = {}
    por_papel = {}
    for id_rs, papel in ab + arb:
        cid = _custom_id(id_rs, papel)
        if cid in ocupados:
            continue
        if falhas.get(cid, 0) >= ctx.args.tentativas:
            esgotados[(id_rs, papel)] = ctx.ultimos_erros.get(cid, "falhou em todos os envios de lote")
            continue
        por_papel.setdefault(papel, []).append((id_rs, papel))

    enviados = []
    for papel, tarefas in por_papel.items():
        for inicio in range(0, len(tarefas), TAMANHO_MAX_LOTE):
            fatia = tarefas[inicio:inicio + TAMANHO_MAX_LOTE]
            pedidos = [(_custom_id(i, p), ctx.sistema_de(p), mensagem_usuario(ctx, indice, i, p)) for i, p in fatia]
            id_lote = ctx.provedores[papel].enviar_lote(pedidos, ctx.schema)
            registro_lotes["lotes"].append({
                "id": id_lote, "papel": papel, "modelo": ctx.modelos[papel], "status": "em_andamento",
                "enviado_em": estado.agora(), "custom_ids": [c for c, _, _ in pedidos],
            })
            _salvar_estado_lotes(ctx, registro_lotes)
            enviados.append({"id": id_lote, "papel": papel, "n": len(pedidos)})
            em_andamento += 1
    pendentes = dict(esgotados)
    return {"novas_regra": len(regra), "novas_ab": novas[PAPEL_A] + novas[PAPEL_B],
            "novas_arbitro": novas[PAPEL_ARBITRO], "pendentes": pendentes,
            "lotes_enviados": enviados, "lotes_em_andamento": em_andamento}


# ---------------------------------------------------------------------------
# Estimativa de custo
# ---------------------------------------------------------------------------
def estimar(ctx, limite, taxa_divergencia, precos=None):
    """Custo aproximado das chamadas que faltam. Não importa SDK nem chama API."""
    indice = indice_decisoes(ler_decisoes(ctx.caminho_decisoes), ctx.rodada)
    regra, ab, arb = planejar(ctx, indice, limite)
    fator = DESCONTO_LOTE if ctx.args.batch else 1.0
    tabela = dict(getattr(ctx, "tabela_precos", None) or provedores.MODELOS_CONHECIDOS)
    tabela.update(precos or {})
    por_papel = {p: {"modelo": ctx.modelos[p], "chamadas": 0.0, "tokens_entrada": 0.0, "tokens_saida": 0.0}
                 for p in (PAPEL_A, PAPEL_B, PAPEL_ARBITRO)}

    def somar(papel, usuario, peso=1.0):
        item = por_papel[papel]
        saida = TOKENS_SAIDA_ESTIMADOS + (TOKENS_PENSAMENTO_ESTIMADOS if provedores.pensa_por_padrao(ctx.modelos[papel]) else 0)
        item["chamadas"] += peso
        item["tokens_entrada"] += peso * (len(ctx.sistema_de(papel)) + len(usuario)) / CHARS_POR_TOKEN
        item["tokens_saida"] += peso * saida

    pares_novos = set()
    for id_rs, papel in ab:
        somar(papel, montar_usuario_revisor(ctx.registros[id_rs]))
        pares_novos.add(id_rs)
    for id_rs, _ in arb:
        somar(PAPEL_ARBITRO, mensagem_usuario(ctx, indice, id_rs, PAPEL_ARBITRO))
    exemplo = {"decisao": "excluir", "criterio_falhou": "C1", "justificativa": "x" * 300, "trecho": "x" * 120}
    for id_rs in pares_novos:
        usuario = montar_usuario_arbitro(ctx.registros[id_rs], exemplo, exemplo)
        somar(PAPEL_ARBITRO, usuario, peso=taxa_divergencia)

    total, desconhecidos = 0.0, []
    for papel, item in por_papel.items():
        valor = provedores.preco(item["modelo"], tabela)
        if valor is None:
            item["custo_usd"] = None
            if item["chamadas"]:
                desconhecidos.append(item["modelo"])
        else:
            item["custo_usd"] = round(fator * (item["tokens_entrada"] * valor[0] + item["tokens_saida"] * valor[1]) / 1e6, 4)
            total += item["custo_usd"]
        item["chamadas"] = round(item["chamadas"], 1)
        item["tokens_entrada"] = int(item["tokens_entrada"])
        item["tokens_saida"] = int(item["tokens_saida"])
    return {
        "estimativa": True, "rodada": ctx.rodada, "registros_elegiveis": len(ctx.registros),
        "sem_resumo_regra": len(regra), "tarefas_ab": len(ab), "arbitragens_conhecidas": len(arb),
        "taxa_divergencia_suposta": taxa_divergencia, "modo_lote": bool(ctx.args.batch),
        "por_papel": por_papel, "custo_total_usd": round(total, 2),
        "modelos_sem_preco": desconhecidos, "precos_consultados_em": provedores.PRECOS_CONSULTADOS_EM,
        "tabela_precos": provedores.tabela_usada(sorted(set(ctx.modelos.values())), tabela),
        "aviso": "estimativa grosseira (≈4 caracteres/token, saída média suposta, preços a verificar)",
    }


TIPO_ESTIMATIVA = "estimativa_custo_api"


def registrar_estimativa(raiz, ctx, estimativa):
    """Grava a estimativa como `artefato_versionado` sem chamadas; não duplica se nada mudou."""
    assinatura = estado.sha256_texto(json.dumps(estimativa, ensure_ascii=False, sort_keys=True))
    for ev in reversed(estado.ler_log(raiz)):
        dados = ev.get("dados") or {}
        if ev.get("evento") == "artefato_versionado" and dados.get("tipo") == TIPO_ESTIMATIVA \
                and dados.get("rodada") == ctx.rodada:
            if dados.get("assinatura") == assinatura:
                return ev.get("seq"), True
            break
    artefatos = [ctx.criterios_rel] if not Path(ctx.criterios_rel).is_absolute() else []
    linha = estado.registrar_evento(
        raiz, "artefato_versionado", ETAPA_ESTADO, "script", ATOR_ID,
        dados={"tipo": TIPO_ESTIMATIVA, "rodada": ctx.rodada, "chamadas_api": 0, "assinatura": assinatura,
               "modelos": dict(ctx.modelos), "criterios_sha": ctx.criterios_sha, "estimativa": estimativa},
        artefatos=artefatos)
    return linha["seq"], False


def custos_execucao(ctx):
    """Custo estimado desta execução: tokens informados pela API × tabela de preços (× desconto de lote)."""
    fator = DESCONTO_LOTE if ctx.args.batch else 1.0
    por_papel, sem_preco, total = {}, [], 0.0
    for papel, prov in ctx.provedores.items():
        uso = {"chamadas": 0, "tokens_entrada": 0, "tokens_saida": 0, **dict(prov.uso)}
        modelo = ctx.modelos[papel]
        custo = provedores.custo_estimado(modelo, uso["tokens_entrada"], uso["tokens_saida"], ctx.tabela_precos, fator)
        if custo is None and uso["chamadas"]:
            sem_preco.append(modelo)
        por_papel[papel] = {
            "modelo": modelo, **uso,
            "custo_estimado_usd": None if custo is None else round(custo, 6),
            "custo_medio_por_chamada_usd": round(custo / uso["chamadas"], 8) if custo is not None and uso["chamadas"]
            else None,
        }
        total += custo or 0.0
    return {
        "custo_estimado_usd": None if sem_preco else round(total, 6),
        "custo_parcial_usd": round(total, 6) if sem_preco else None,
        "custo_por_papel": por_papel, "modelos_sem_preco": sorted(set(sem_preco)),
        "tabela_precos": provedores.tabela_usada(sorted(set(ctx.modelos.values())), ctx.tabela_precos),
        "precos_consultados_em": provedores.PRECOS_CONSULTADOS_EM, "desconto_lote": fator,
        "chamadas_api": sum(p["chamadas"] for p in por_papel.values()),
    }


def custo_acumulado_rodada(raiz, rodada):
    total = 0.0
    for ev in estado.ler_log(raiz):
        dados = ev.get("dados") or {}
        if (ev.get("ator") or {}).get("id") == ATOR_ID and dados.get("rodada") == rodada \
                and isinstance(dados.get("custo_estimado_usd"), (int, float)):
            total += float(dados["custo_estimado_usd"])
    return total


def _com_custo(raiz, ctx, dados):
    custo = custos_execucao(ctx)
    anterior = custo_acumulado_rodada(raiz, ctx.rodada)
    custo["custo_estimado_rodada_usd"] = round(anterior + (custo["custo_estimado_usd"] or 0.0), 6)
    return {**dados, **custo}


# ---------------------------------------------------------------------------
# Comando
# ---------------------------------------------------------------------------
def executar(args):
    try:
        raiz = estado.exigir_projeto(args.dir)
        ctx = Contexto(raiz, args)
        indice = indice_decisoes(ler_decisoes(ctx.caminho_decisoes), ctx.rodada)
        _checar_congelamento(ctx, indice)
        for aviso in ctx.avisos:
            print(f"aviso: {aviso}", file=sys.stderr)
        if args.estimar:
            estimativa = estimar(ctx, args.limite, args.taxa_divergencia)
            seq, repetida = registrar_estimativa(raiz, ctx, estimativa)
            estado.resumo({**estimativa, "evento_seq": seq, "reexecucao": repetida})
            return 0
    except (estado.ErroProjeto, ErroUso, OSError, json.JSONDecodeError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        estado.resumo({"ok": False, "erro": str(exc)})
        return 1

    try:
        for papel, especificacao in ctx.especificacoes.items():
            ctx.provedores[papel] = provedores.criar_provedor(
                especificacao, max_tokens=args.max_tokens, esforco=args.esforco)
    except provedores.ErroDependencia as exc:
        print(f"erro: {exc}", file=sys.stderr)
        estado.resumo({"ok": False, "erro": str(exc), "dependencia_ausente": True})
        return 3
    except ValueError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        estado.resumo({"ok": False, "erro": str(exc)})
        return 1

    codigo = 0
    erro_fatal = None
    try:
        with _TravaRodada(ctx.pasta):
            artefatos_congelados = _congelar_rodada(ctx)
            if artefatos_congelados:
                estado.registrar_evento(
                    raiz, "artefato_versionado", ETAPA_ESTADO, "script", ATOR_ID,
                    dados={"rodada": ctx.rodada, **_parametros_congelados(ctx),
                           "parametros": ctx.parametros_publicos()},
                    artefatos=artefatos_congelados)
            resultado = rodar_lote(ctx, args.limite) if args.batch else rodar_sincrono(ctx, args.limite)
    except ErroUso as exc:
        print(f"erro: {exc}", file=sys.stderr)
        estado.resumo({"ok": False, "erro": str(exc)})
        return 1
    except provedores.ErroFatal as exc:
        erro_fatal = exc
        codigo = exc.codigo_saida
        resultado = None
    except KeyboardInterrupt:
        # o que já foi gravado fica; o log registra a interrupção (e o custo já gasto) e a retomada continua dali
        estado.registrar_evento(raiz, "erro", ETAPA_ESTADO, "ia_api", ATOR_ID,
                                dados=_com_custo(raiz, ctx, {"rodada": ctx.rodada, "erro": "interrompido pelo usuário; "
                                                                                       "rode de novo para retomar"}),
                                modelo=_rotulo_modelos(ctx))
        raise

    indice = indice_decisoes(ler_decisoes(ctx.caminho_decisoes), ctx.rodada)
    resumo = _com_custo(raiz, ctx, _resumo(ctx, indice, resultado))
    if erro_fatal is not None:
        print(f"erro: {erro_fatal}", file=sys.stderr)
        resumo.update({"ok": False, "erro": str(erro_fatal)})
        estado.registrar_evento(raiz, "erro", ETAPA_ESTADO, "ia_api", ATOR_ID,
                                dados={k: v for k, v in resumo.items() if k not in ("arquivos",)},
                                modelo=_rotulo_modelos(ctx))
        estado.resumo(resumo)
        return codigo

    houve_dados = resultado["novas_regra"] or resultado["novas_ab"] or resultado["novas_arbitro"]
    if houve_dados or resultado["lotes_enviados"]:
        est = estado.carregar_estado(raiz)
        est.setdefault("versoes_ativas", {})["prompt_triagem_api"] = f"{ctx.rodada}:{ctx.prompt_sha['revisor'][:12]}"
        evento = "lote_mesclado" if houve_dados else "lote_preparado"
        estado.registrar_evento(
            raiz, evento, ETAPA_ESTADO, "ia_api", ATOR_ID,
            dados={k: v for k, v in resumo.items() if k not in ("arquivos",)},
            artefatos=[esquema.ARQ_DECISOES], modelo=_rotulo_modelos(ctx), estado=est)
    elif resumo["chamadas_api"]:
        # chamadas pagas sem nenhuma decisão válida: o custo não pode sumir do log
        estado.registrar_evento(
            raiz, "erro", ETAPA_ESTADO, "ia_api", ATOR_ID,
            dados={**{k: v for k, v in resumo.items() if k not in ("arquivos",)},
                   "erro": "chamadas sem decisão válida nesta execução; rode de novo para re-tentar"},
            modelo=_rotulo_modelos(ctx))
    if resultado["pendentes"]:
        print(f"aviso: {len(resultado['pendentes'])} decisão(ões) sem resposta válida após as tentativas; "
              "nada foi pulado: rode o mesmo comando de novo para re-tentar só essas.", file=sys.stderr)
        codigo = 1
    estado.resumo(resumo)
    return codigo


def _rotulo_modelos(ctx):
    return f"A={ctx.modelos[PAPEL_A]};B={ctx.modelos[PAPEL_B]};arbitro={ctx.modelos[PAPEL_ARBITRO]}"


def _resumo(ctx, indice, resultado):
    ids = list(ctx.registros)
    com_a = sum(1 for i in ids if (i, PAPEL_A) in indice)
    com_b = sum(1 for i in ids if (i, PAPEL_B) in indice)
    pares = [(indice[(i, PAPEL_A)], indice[(i, PAPEL_B)], i) for i in ids
             if (i, PAPEL_A) in indice and (i, PAPEL_B) in indice]
    divergentes = [i for a, b, i in pares if eh_divergente(a, b, ctx.args.divergencia)]
    arbitrados = sum(1 for i in divergentes if (i, PAPEL_ARBITRO) in indice)
    regra = sum(1 for i in ids if (i, PAPEL_REGRA) in indice)
    completos = sum(1 for i in ids if (i, PAPEL_REGRA) in indice or (
        (i, PAPEL_A) in indice and (i, PAPEL_B) in indice
        and (not eh_divergente(indice[(i, PAPEL_A)], indice[(i, PAPEL_B)], ctx.args.divergencia)
             or (i, PAPEL_ARBITRO) in indice)))
    resumo = {
        "ok": True, "comando": "triagem api", "rodada": ctx.rodada, "modo": "lote" if ctx.args.batch else "sincrono",
        "modelos": dict(ctx.modelos), "prompt_sha": dict(ctx.prompt_sha), "criterios_sha": ctx.criterios_sha,
        "registros_total": ctx.n_registros_total, "excluidos_filtro_formal": len(ctx.excluidos_filtro),
        "n_inativos_ignorados": len(ctx.ids_inativos),
        "registros_elegiveis": len(ids), "sem_resumo_regra": regra,
        "com_decisao_a": com_a, "com_decisao_b": com_b, "consenso": len(pares) - len(divergentes),
        "divergentes": len(divergentes), "arbitrados": arbitrados, "completos": completos,
        "faltando": len(ids) - completos, "divergencia": ctx.args.divergencia,
        "retentativas": ctx.contadores["retentativas"], "trechos_descartados": ctx.contadores["trechos_descartados"],
        "uso_tokens": {p: dict(prov.uso) for p, prov in ctx.provedores.items()},
        "parametros": ctx.parametros_publicos(),
        "arquivos": {"decisoes": esquema.ARQ_DECISOES, "prompts": _relativo(ctx.pasta, ctx.raiz)},
    }
    if resultado is not None:
        resumo.update({
            "novas": {"regra": resultado["novas_regra"], "revisores": resultado["novas_ab"],
                      "arbitro": resultado["novas_arbitro"]},
            "pendentes": len(resultado["pendentes"]),
            "pendentes_ids": [f"{i}:{p}" for i, p in sorted(resultado["pendentes"])][:200],
            "ultimos_erros": sorted({e for e in resultado["pendentes"].values()})[:10],
            "lotes_enviados": resultado["lotes_enviados"], "lotes_em_andamento": resultado["lotes_em_andamento"],
        })
    if ctx.avisos:
        resumo["avisos"] = list(ctx.avisos)
    return resumo


def _subparsers_triagem(subparsers):
    """Reaproveita o comando `triagem` se outro módulo (triagem_lotes) já o registrou.

    argparse (Python ≥ 3.11) recusa dois add_parser com o mesmo nome; por isso
    procuramos o parser existente e seus subcomandos antes de criar.
    """
    triagem = subparsers.choices.get("triagem")
    if triagem is None:
        triagem = subparsers.add_parser("triagem", help="triagem de títulos e resumos (lotes, API)")
    for acao in triagem._actions:  # noqa: SLF001 - argparse não expõe outra forma
        if isinstance(acao, argparse._SubParsersAction):  # noqa: SLF001
            return acao
    return triagem.add_subparsers(dest="subcomando_triagem", metavar="<subcomando>")


def registrar(subparsers):
    sub = _subparsers_triagem(subparsers)
    p = sub.add_parser(
        "api", help="triagem T/A via API: 2 modelos independentes + árbitro cego (retomável)",
        description="Triagem de títulos e resumos por API com dois revisores de IA e árbitro só nas divergências. "
                    "Grava dados/decisoes.jsonl. Envia títulos e resumos a provedores externos.")
    p.add_argument("--rodada", required=True, help="nome da rodada congelada (ex.: ta_v2)")
    p.add_argument("--criterios", required=True, help="arquivo de critérios (ex.: 02-triagem/prompts/ta_v2.md)")
    p.add_argument("--modelo-a", required=True, help="modelo do Revisor A (ex.: claude-haiku-4-5)")
    p.add_argument("--modelo-b", required=True, help="modelo do Revisor B, de preferência de outro provedor")
    p.add_argument("--arbitro", required=True,
                   help="terceiro modelo, diferente dos revisores e preferencialmente de outro provedor")
    p.add_argument("--concorrencia", type=int, default=8, help="chamadas simultâneas (padrão 8)")
    p.add_argument("--limite", type=int, default=None, help="processa só os N primeiros registros pendentes")
    p.add_argument("--estimar", action="store_true",
                   help="só estima chamadas, tokens e custo; nada é enviado (a estimativa vai para o log)")
    p.add_argument("--batch", action="store_true", help="usa a API de lotes (assíncrona, mais barata)")
    p.add_argument("--ids", default=None, help="restringe a triagem aos id_rs deste arquivo")
    p.add_argument("--tentativas", type=int, default=5, help="tentativas por chamada (padrão 5)")
    p.add_argument("--passadas", type=int, default=2, help="passadas sobre as falhas (padrão 2)")
    p.add_argument("--max-tokens", type=int, default=None, help="teto de tokens de saída (padrão por modelo)")
    p.add_argument("--esforco", choices=["low", "medium", "high", "xhigh", "max"], default=None,
                   help="esforço de raciocínio, para modelos que aceitam (congelado na rodada)")
    p.add_argument("--divergencia", choices=["binaria", "rotulo"], default="binaria",
                   help="binaria (padrão, igual à consolidação): excluir × incluir/incerto; "
                        "rotulo: qualquer diferença de rótulo vai ao árbitro")
    p.add_argument("--taxa-divergencia", type=float, default=0.2,
                   help="fração de divergências suposta em --estimar (padrão 0.2)")
    p.add_argument("--precos", default=None,
                   help='JSON {"modelo": [entrada, saida]} em US$/M tokens (--estimar e custo registrado no log)')
    p.set_defaults(func=executar)
    return p
