"""provedores.py — adaptadores de modelos de linguagem para a triagem via API.

USO (dentro da skill; não é um comando)
    from rslib import provedores
    prov = provedores.criar_provedor("claude-haiku-4-5")       # ou "gpt-4o-mini", "openai:gpt-5-mini"
    dados = prov.decidir(sistema, usuario, schema)              # dict já validado como JSON

Interface única: `Provedor.decidir(sistema, usuario, schema) -> dict`. A triagem
não sabe qual empresa está do outro lado; só recebe um dict ou uma exceção
classificada. Isso permite testar toda a orquestração com um provedor falso
(registrado em `FABRICAS`) sem rede, sem chave e sem pacote instalado.

POR QUE AS REGRAS ABAIXO
- Sucesso só com parada natural. `stop_reason == "max_tokens"` (Anthropic) ou
  `finish_reason == "length"` (OpenAI) devolvem JSON cortado que às vezes ainda
  "parece" válido; já custou registros sem campos em projetos anteriores. Recusa
  também não é decisão. Esses casos viram `RespostaInvalida` e são re-tentados.
- Só blocos de texto são lidos. Modelos que pensam antes de responder devolvem
  um bloco `thinking` antes do `text`; ler `content[0]` pega o bloco errado.
- `temperature` é omitido para a família Claude 5 (Opus 5, Sonnet 5, Fable,
  Mythos) e para Opus ≥ 4.7: esses modelos devolvem HTTP 400 se o campo vier,
  mesmo com valor válido. Nos modelos que aceitam, usamos 0 para estabilidade.
- Modelos que pensam por padrão gastam tokens de pensamento dentro de
  `max_tokens`; com teto baixo a resposta volta vazia e truncada. Por isso o
  teto padrão deles é alto.
- Saída estruturada (json_schema) nos dois provedores: o esquema restringe
  `decisao` e `criterio_falhou` a enums, o que elimina a análise por palavras-
  chave do script de origem (que transformava "EXCLUDE" solto em exclusão).
- Credenciais só por variável de ambiente (ANTHROPIC_API_KEY, OPENAI_API_KEY).
  Nunca lemos `.env`. Pacote ou chave ausente -> `ErroDependencia` (exit 3).
- Erros HTTP são classificados: credencial/permissão/modelo inexistente abortam
  a rodada (repetir só gastaria tempo); 400 não se repete na mesma passada; 429,
  5xx e rede são transitórios e re-tentados pelo chamador.

TABELA DE MODELOS E PREÇOS
`MODELOS_CONHECIDOS` guarda preços em US$ por milhão de tokens. São constantes
para a estimativa de custo (`--estimar`) e para o custo estimado de cada execução
(tokens informados pela API × preço, gravado no log com a tabela usada), copiadas
da documentação pública em `PRECOS_CONSULTADOS_EM`; VERIFICAR antes de orçar um
projeto real. Modelo fora da tabela funciona normalmente, só fica sem custo
estimado (ou use `--precos` na triagem).

PROVEDORES DISPONÍVEIS
Só há adaptadores `anthropic` e `openai` (mais os falsos dos testes, via `FABRICAS`).
Por isso o árbitro da triagem é um terceiro MODELO, preferencialmente de outro
provedor: com os revisores A e B em provedores diferentes, o árbitro repete um
deles, e isso deve constar da declaração de uso de IA.
"""

from __future__ import annotations

import io
import json
import os
import re
import threading

# ---------------------------------------------------------------------------
# Constantes (VERIFICAR: preços e IDs mudam; conferir na documentação oficial)
# ---------------------------------------------------------------------------
PRECOS_CONSULTADOS_EM = "2026-06 (verificar)"

# modelo -> (provedor, US$/M tokens de entrada, US$/M tokens de saída)  [verificar]
MODELOS_CONHECIDOS = {
    "claude-fable-5-1": ("anthropic", 10.00, 50.00),
    "claude-fable-5": ("anthropic", 10.00, 50.00),
    "claude-opus-5": ("anthropic", 5.00, 25.00),
    "claude-opus-4-8": ("anthropic", 5.00, 25.00),
    "claude-opus-4-7": ("anthropic", 5.00, 25.00),
    "claude-opus-4-6": ("anthropic", 5.00, 25.00),
    "claude-sonnet-5": ("anthropic", 2.00, 10.00),
    "claude-sonnet-4-6": ("anthropic", 3.00, 15.00),
    "claude-haiku-4-5": ("anthropic", 1.00, 5.00),
    "gpt-5": ("openai", 1.25, 10.00),
    "gpt-5-mini": ("openai", 0.25, 2.00),
    "gpt-4.1": ("openai", 2.00, 8.00),
    "gpt-4.1-mini": ("openai", 0.40, 1.60),
    "gpt-4o": ("openai", 2.50, 10.00),
    "gpt-4o-mini": ("openai", 0.15, 0.60),
}

MAX_TOKENS_PADRAO = 2048            # modelos que respondem sem pensar
MAX_TOKENS_PADRAO_PENSANTE = 16000  # pensamento + resposta cabem no mesmo teto (verificar)
TIMEOUT_SEGUNDOS = 180
RETENTATIVAS_SDK = 2                # além das nossas; o SDK já trata 429/5xx curtos

ENV_ANTHROPIC = "ANTHROPIC_API_KEY"
ENV_ANTHROPIC_TOKEN = "ANTHROPIC_AUTH_TOKEN"
ENV_OPENAI = "OPENAI_API_KEY"


# ---------------------------------------------------------------------------
# Exceções classificadas
# ---------------------------------------------------------------------------
class ErroProvedor(Exception):
    """Base das falhas de provedor."""


class ErroDependencia(ErroProvedor):
    """Pacote ou credencial ausente. O comando deve sair com código 3."""


class ErroFatal(ErroProvedor):
    """Falha que se repetiria em toda chamada (credencial inválida, modelo inexistente)."""

    def __init__(self, mensagem, codigo_saida=1):
        super().__init__(mensagem)
        self.codigo_saida = codigo_saida


class ErroRequisicao(ErroProvedor):
    """Requisição rejeitada (400/413/422): repetir igual não adianta nesta passada."""


class ErroTransitorio(ErroProvedor):
    """429, 5xx, timeout, rede: vale re-tentar com espera."""


class RespostaInvalida(ErroProvedor):
    """A API respondeu, mas não com uma decisão utilizável (truncada, recusa, JSON inválido)."""


def classificar_excecao(exc):
    """Converte exceções dos SDKs (ou de clientes falsos) em exceções classificadas.

    Usa só `status_code`, presente nos erros HTTP dos dois SDKs, para não depender
    de importar o pacote (e para funcionar com clientes falsos nos testes).
    """
    if isinstance(exc, ErroProvedor):
        return exc
    status = getattr(exc, "status_code", None)
    if status is None:
        resposta = getattr(exc, "response", None)
        status = getattr(resposta, "status_code", None)
    mensagem = f"{type(exc).__name__}: {exc}"
    if status in (401, 403):
        return ErroFatal(f"credencial recusada pelo provedor ({status}). {mensagem}", codigo_saida=3)
    if status == 404:
        return ErroFatal(f"modelo ou endpoint inexistente (404). {mensagem}", codigo_saida=1)
    if status in (400, 413, 422):
        return ErroRequisicao(mensagem)
    return ErroTransitorio(mensagem)


# ---------------------------------------------------------------------------
# Regras por modelo
# ---------------------------------------------------------------------------
_RE_CLAUDE = re.compile(r"^claude-(opus|sonnet|haiku|fable|mythos)-(\d+)(?:-(\d{1,2}))?(?:-\d{8})?$")
_RE_SUFIXO_DATA = re.compile(r"(-\d{8}|-\d{4}-\d{2}-\d{2})$")


def modelo_base(modelo):
    """ID sem sufixo de data (claude-haiku-4-5-20251001 -> claude-haiku-4-5)."""
    return _RE_SUFIXO_DATA.sub("", modelo or "")


def _versao_claude(modelo):
    m = _RE_CLAUDE.match(modelo or "")
    if not m:
        return None
    return m.group(1), int(m.group(2)), int(m.group(3) or 0)


def aceita_temperature(modelo):
    """True se é seguro enviar `temperature` para este modelo.

    Claude: família 5 (e Fable/Mythos) e Opus/Sonnet ≥ 4.7 rejeitam o campo.
    Modelos Claude com nome desconhecido: omitir (omitir nunca dá 400).
    OpenAI: só a linha gpt-4*/gpt-3.5 aceita temperature arbitrária; modelos de
    raciocínio (o1/o3/o4, gpt-5*) só aceitam o valor padrão.
    """
    modelo = modelo or ""
    if modelo.startswith("claude-"):
        versao = _versao_claude(modelo)
        if versao is None:
            return modelo.startswith("claude-3")
        familia, maior, menor = versao
        if familia in ("fable", "mythos") or maior >= 5:
            return False
        if familia in ("opus", "sonnet") and (maior, menor) >= (4, 7):
            return False
        return True
    return bool(re.match(r"^(gpt-4|gpt-3\.5)", modelo))


def pensa_por_padrao(modelo):
    """True se o modelo gasta tokens de pensamento/raciocínio sem pedirmos."""
    modelo = modelo or ""
    if modelo.startswith("claude-"):
        versao = _versao_claude(modelo)
        return bool(versao) and (versao[0] in ("fable", "mythos") or versao[1] >= 5)
    return bool(re.match(r"^(o\d|gpt-5)", modelo))


def custo_estimado(modelo, tokens_entrada, tokens_saida, tabela=None, desconto=1.0):
    """US$ estimados para os tokens informados (preço por milhão × desconto) ou None sem preço."""
    valor = preco(modelo, tabela)
    if valor is None:
        return None
    return desconto * (float(tokens_entrada or 0) * valor[0] + float(tokens_saida or 0) * valor[1]) / 1e6


def tabela_usada(modelos, tabela=None):
    """{modelo: {"entrada": US$/M, "saida": US$/M}} dos modelos com preço conhecido (vai para o log)."""
    saida = {}
    for modelo in modelos:
        valor = preco(modelo, tabela)
        if valor is not None:
            saida[modelo] = {"entrada": valor[0], "saida": valor[1]}
    return saida


def preco(modelo, tabela=None):
    """(entrada, saída) em US$/M tokens ou None se desconhecido."""
    tabela = tabela if tabela is not None else MODELOS_CONHECIDOS
    info = tabela.get(modelo) or tabela.get(modelo_base(modelo))
    if info is None:
        return None
    if isinstance(info, dict):
        return float(info["entrada"]), float(info["saida"])
    if len(info) == 3:
        return float(info[1]), float(info[2])
    return float(info[0]), float(info[1])


# ---------------------------------------------------------------------------
# Utilidades de resposta
# ---------------------------------------------------------------------------
def _campo(obj, nome, padrao=None):
    """Lê atributo de objeto do SDK ou chave de dict (resultados de lote chegam como dict)."""
    if obj is None:
        return padrao
    if isinstance(obj, dict):
        return obj.get(nome, padrao)
    return getattr(obj, nome, padrao)


def extrair_json(texto):
    """Dict a partir do texto do modelo; tolera cercas de código. Sem heurística por palavra-chave."""
    if texto is None or not str(texto).strip():
        raise RespostaInvalida("resposta sem texto")
    limpo = re.sub(r"```(?:json)?", "", str(texto)).strip()
    try:
        dados = json.loads(limpo)
    except json.JSONDecodeError:
        inicio, fim = limpo.find("{"), limpo.rfind("}")
        if inicio < 0 or fim <= inicio:
            raise RespostaInvalida(f"JSON inválido: {limpo[:120]!r}") from None
        try:
            dados = json.loads(limpo[inicio:fim + 1])
        except json.JSONDecodeError:
            raise RespostaInvalida(f"JSON inválido: {limpo[:120]!r}") from None
    if not isinstance(dados, dict):
        raise RespostaInvalida("JSON não é um objeto")
    return dados


def _importar(nome_pacote):
    """Importa o SDK sob demanda (isolado para os testes simularem pacote ausente)."""
    import importlib
    return importlib.import_module(nome_pacote)


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------
class Provedor:
    """Interface mínima. Subclasses implementam `decidir`; lotes são opcionais."""

    nome = "base"
    suporta_lote = False

    def __init__(self, modelo, max_tokens=None, esforco=None):
        self.modelo = modelo
        self.max_tokens = max_tokens or (MAX_TOKENS_PADRAO_PENSANTE if pensa_por_padrao(modelo) else MAX_TOKENS_PADRAO)
        self.esforco = esforco
        self._trava_uso = threading.Lock()
        self.uso = {"chamadas": 0, "tokens_entrada": 0, "tokens_saida": 0}

    @property
    def temperature(self):
        return 0 if aceita_temperature(self.modelo) else None

    def parametros_publicos(self):
        """Parâmetros que entram no log de auditoria (nunca credenciais)."""
        return {"provedor": self.nome, "modelo": self.modelo, "max_tokens": self.max_tokens,
                "temperature": self.temperature, "esforco": self.esforco}

    def _somar_uso(self, entrada, saida):
        with self._trava_uso:
            self.uso["chamadas"] += 1
            self.uso["tokens_entrada"] += int(entrada or 0)
            self.uso["tokens_saida"] += int(saida or 0)

    def decidir(self, sistema, usuario, schema):  # pragma: no cover - interface
        raise NotImplementedError

    def enviar_lote(self, pedidos, schema):  # pragma: no cover - interface
        """`pedidos`: lista de (custom_id, sistema, usuario). Devolve o id do lote."""
        raise NotImplementedError(f"{self.nome} não suporta lotes")

    def coletar_lote(self, id_lote):  # pragma: no cover - interface
        """Devolve (status, resultados): status 'em_andamento' ou 'concluido';
        resultados mapeia custom_id -> dict (sucesso) ou Exception."""
        raise NotImplementedError(f"{self.nome} não suporta lotes")


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------
class ProvedorAnthropic(Provedor):
    nome = "anthropic"
    suporta_lote = True

    def __init__(self, modelo, max_tokens=None, esforco=None, cliente=None):
        super().__init__(modelo, max_tokens=max_tokens, esforco=esforco)
        if cliente is None:
            try:
                sdk = _importar("anthropic")
            except ImportError:
                raise ErroDependencia(
                    "pacote `anthropic` não instalado. Instale com `python3 -m pip install anthropic` "
                    "ou use a triagem por subagentes (`rs.py triagem preparar`).") from None
            if not (os.environ.get(ENV_ANTHROPIC) or os.environ.get(ENV_ANTHROPIC_TOKEN)):
                raise ErroDependencia(
                    f"variável de ambiente {ENV_ANTHROPIC} ausente. Exporte a chave no shell "
                    f"(export {ENV_ANTHROPIC}=...) antes de rodar; a skill não lê arquivos .env.")
            cliente = sdk.Anthropic(max_retries=RETENTATIVAS_SDK, timeout=TIMEOUT_SEGUNDOS)
        self.cliente = cliente

    def parametros(self, sistema, usuario, schema):
        """Corpo da requisição. Público para os testes conferirem o que é enviado."""
        output_config = {"format": {"type": "json_schema", "schema": schema}}
        if self.esforco:
            output_config["effort"] = self.esforco
        corpo = {
            "model": self.modelo,
            "max_tokens": self.max_tokens,
            "system": sistema,
            "messages": [{"role": "user", "content": usuario}],
            "output_config": output_config,
        }
        if self.temperature is not None:
            corpo["temperature"] = self.temperature
        return corpo

    def interpretar(self, mensagem):
        """Valida parada e extrai o JSON só dos blocos de texto."""
        parada = _campo(mensagem, "stop_reason")
        uso = _campo(mensagem, "usage")
        self._somar_uso(_campo(uso, "input_tokens", 0), _campo(uso, "output_tokens", 0))
        if parada == "max_tokens":
            raise RespostaInvalida(f"resposta truncada (stop_reason=max_tokens, max_tokens={self.max_tokens})")
        if parada == "refusal":
            raise RespostaInvalida("modelo recusou responder (stop_reason=refusal)")
        if parada not in ("end_turn", "stop_sequence"):
            raise RespostaInvalida(f"stop_reason inesperado: {parada!r}")
        blocos = _campo(mensagem, "content", []) or []
        texto = "".join(_campo(b, "text", "") or "" for b in blocos if _campo(b, "type") == "text")
        return extrair_json(texto)

    def decidir(self, sistema, usuario, schema):
        try:
            mensagem = self.cliente.messages.create(**self.parametros(sistema, usuario, schema))
        except Exception as exc:  # noqa: BLE001 - classificada abaixo
            raise classificar_excecao(exc) from exc
        return self.interpretar(mensagem)

    def enviar_lote(self, pedidos, schema):
        requisicoes = [{"custom_id": cid, "params": self.parametros(s, u, schema)} for cid, s, u in pedidos]
        try:
            lote = self.cliente.messages.batches.create(requests=requisicoes)
        except Exception as exc:  # noqa: BLE001
            raise classificar_excecao(exc) from exc
        return _campo(lote, "id")

    def coletar_lote(self, id_lote):
        try:
            lote = self.cliente.messages.batches.retrieve(id_lote)
            if _campo(lote, "processing_status") != "ended":
                return "em_andamento", {}
            itens = list(self.cliente.messages.batches.results(id_lote))
        except Exception as exc:  # noqa: BLE001
            raise classificar_excecao(exc) from exc
        resultados = {}
        for item in itens:
            cid = _campo(item, "custom_id")
            resultado = _campo(item, "result")
            if _campo(resultado, "type") == "succeeded":
                try:
                    resultados[cid] = self.interpretar(_campo(resultado, "message"))
                except RespostaInvalida as exc:
                    resultados[cid] = exc
            else:
                resultados[cid] = ErroTransitorio(f"item do lote terminou como {_campo(resultado, 'type')!r}")
        return "concluido", resultados


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------
class ProvedorOpenAI(Provedor):
    nome = "openai"
    suporta_lote = True
    ENDPOINT = "/v1/chat/completions"

    def __init__(self, modelo, max_tokens=None, esforco=None, cliente=None):
        super().__init__(modelo, max_tokens=max_tokens, esforco=esforco)
        if cliente is None:
            try:
                sdk = _importar("openai")
            except ImportError:
                raise ErroDependencia(
                    "pacote `openai` não instalado. Instale com `python3 -m pip install openai` "
                    "ou escolha modelos de outro provedor.") from None
            if not os.environ.get(ENV_OPENAI):
                raise ErroDependencia(
                    f"variável de ambiente {ENV_OPENAI} ausente. Exporte a chave no shell "
                    f"(export {ENV_OPENAI}=...) antes de rodar; a skill não lê arquivos .env.")
            cliente = sdk.OpenAI(max_retries=RETENTATIVAS_SDK, timeout=TIMEOUT_SEGUNDOS)
        self.cliente = cliente

    def parametros(self, sistema, usuario, schema):
        corpo = {
            "model": self.modelo,
            "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "decisao_triagem", "strict": True, "schema": schema}},
            "max_completion_tokens": self.max_tokens,
        }
        if self.temperature is not None:
            corpo["temperature"] = self.temperature
        if self.esforco and pensa_por_padrao(self.modelo):
            corpo["reasoning_effort"] = self.esforco
        return corpo

    def interpretar(self, resposta):
        uso = _campo(resposta, "usage")
        self._somar_uso(_campo(uso, "prompt_tokens", 0), _campo(uso, "completion_tokens", 0))
        escolhas = _campo(resposta, "choices", []) or []
        if not escolhas:
            raise RespostaInvalida("resposta sem choices")
        escolha = escolhas[0]
        fim = _campo(escolha, "finish_reason")
        mensagem = _campo(escolha, "message")
        if fim == "length":
            raise RespostaInvalida(f"resposta truncada (finish_reason=length, max_completion_tokens={self.max_tokens})")
        if fim == "content_filter":
            raise RespostaInvalida("resposta bloqueada por filtro de conteúdo")
        if _campo(mensagem, "refusal"):
            raise RespostaInvalida(f"modelo recusou responder: {_campo(mensagem, 'refusal')}")
        if fim not in ("stop", None):
            raise RespostaInvalida(f"finish_reason inesperado: {fim!r}")
        return extrair_json(_campo(mensagem, "content"))

    def decidir(self, sistema, usuario, schema):
        try:
            resposta = self.cliente.chat.completions.create(**self.parametros(sistema, usuario, schema))
        except Exception as exc:  # noqa: BLE001
            raise classificar_excecao(exc) from exc
        return self.interpretar(resposta)

    def enviar_lote(self, pedidos, schema):
        linhas = [json.dumps({"custom_id": cid, "method": "POST", "url": self.ENDPOINT,
                              "body": self.parametros(s, u, schema)}, ensure_ascii=False)
                  for cid, s, u in pedidos]
        conteudo = ("\n".join(linhas) + "\n").encode("utf-8")
        try:
            arquivo = self.cliente.files.create(file=("triagem_lote.jsonl", io.BytesIO(conteudo)), purpose="batch")
            lote = self.cliente.batches.create(input_file_id=_campo(arquivo, "id"), endpoint=self.ENDPOINT,
                                               completion_window="24h")
        except Exception as exc:  # noqa: BLE001
            raise classificar_excecao(exc) from exc
        return _campo(lote, "id")

    def coletar_lote(self, id_lote):
        try:
            lote = self.cliente.batches.retrieve(id_lote)
            status = _campo(lote, "status")
            if status in ("validating", "in_progress", "finalizing", "cancelling"):
                return "em_andamento", {}
            textos = []
            for campo in ("output_file_id", "error_file_id"):
                fid = _campo(lote, campo)
                if fid:
                    textos.append(self.cliente.files.content(fid).text)
        except Exception as exc:  # noqa: BLE001
            raise classificar_excecao(exc) from exc
        resultados = {}
        for texto in textos:
            for linha in texto.splitlines():
                if not linha.strip():
                    continue
                try:
                    item = json.loads(linha)
                except json.JSONDecodeError:
                    continue
                cid = item.get("custom_id")
                resposta = item.get("response") or {}
                if resposta.get("status_code") == 200 and resposta.get("body"):
                    try:
                        resultados[cid] = self.interpretar(resposta["body"])
                    except RespostaInvalida as exc:
                        resultados[cid] = exc
                else:
                    resultados[cid] = ErroTransitorio(f"item do lote falhou: {item.get('error') or resposta.get('status_code')}")
        return "concluido", resultados


# ---------------------------------------------------------------------------
# Fábrica
# ---------------------------------------------------------------------------
FABRICAS = {"anthropic": ProvedorAnthropic, "openai": ProvedorOpenAI}


def resolver_modelo(especificacao):
    """'claude-x' -> ('anthropic', 'claude-x'); 'gpt-4o' -> ('openai', ...); 'prov:modelo' explícito."""
    especificacao = (especificacao or "").strip()
    if not especificacao:
        raise ValueError("modelo vazio")
    if ":" in especificacao:
        nome, modelo = especificacao.split(":", 1)
        return nome.strip().lower(), modelo.strip()
    if especificacao.startswith("claude-"):
        return "anthropic", especificacao
    if re.match(r"^(gpt-|o\d|chatgpt-)", especificacao):
        return "openai", especificacao
    info = MODELOS_CONHECIDOS.get(especificacao)
    if info:
        return info[0], especificacao
    raise ValueError(f"não sei qual provedor atende {especificacao!r}; use a forma provedor:modelo "
                     f"(provedores: {', '.join(sorted(FABRICAS))})")


def criar_provedor(especificacao, **opcoes):
    """Instancia o provedor do modelo. Levanta ValueError (uso) ou ErroDependencia (exit 3)."""
    nome, modelo = resolver_modelo(especificacao)
    fabrica = FABRICAS.get(nome)
    if fabrica is None:
        raise ValueError(f"provedor desconhecido: {nome!r} (disponíveis: {', '.join(sorted(FABRICAS))})")
    return fabrica(modelo, **opcoes)
