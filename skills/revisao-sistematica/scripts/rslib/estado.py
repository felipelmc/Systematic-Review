"""Estado do projeto de revisão: rs_estado.json (cache) + rs_log.jsonl (append-only).

Regras:
- Só este módulo escreve rs_estado.json e rs_log.jsonl; dados/decisoes.jsonl é escrito só por
  triagem_lotes.registrar_decisoes (trava dados/.decisoes.lock), usado também pela triagem via API.
- rs_estado.json é gravado de forma atômica (tmp + rename), com permissão 0666 menos a umask
  (0644 no padrão), igual a um arquivo criado com open(); `escrever_atomico` vale para os demais módulos.
- Cada evento recebe seq monotônico; o log nunca é reescrito.
- Artefatos e tabelas são a fonte de verdade; o estado é cache e pode ser recalculado.

Concorrência entre processos
    O Claude Code costuma disparar comandos em paralelo (ex.: `triagem mesclar` de A e de B).
    Todo escritor de estado e log (registrar_evento, salvar_estado, marcar_etapa, abrir_pendencia,
    fechar_pendencia, registrar_portao) roda dentro de `trava(raiz)`: flock exclusivo em
    <raiz>/.rs.lock (msvcrt.locking no Windows; sem nenhum dos dois, só a trava de thread). A trava é
    reentrante no mesmo processo e thread, então quem já a segura pode chamar as funções de novo.
    Dentro dela o seq é recalculado do log e o estado é relido do disco:
    - quem passa `estado=None` (ou usa abrir/fechar_pendencia e registrar_portao) trabalha sobre a
      versão atual do disco;
    - quem carregou o estado antes (fora da trava), mudou algo e chama salvar_estado ou
      registrar_evento(estado=...) tem suas mudanças mescladas em três vias com o que outro processo
      gravou nesse meio-tempo: a base é a versão lida por carregar_estado (ou a última gravada por
      este objeto). Campo que só este processo mudou fica com o valor dele; campo que só o outro mudou
      fica com o do disco; conflito no mesmo campo, vale quem grava agora. Listas de objetos com `id`
      (pendencias, buscas) são mescladas por id, e listas de valores simples como conjuntos.
"""

import collections
import contextlib
import datetime as _dt
import hashlib
import json
import os
import tempfile
import threading
import time
from pathlib import Path

from . import esquema

try:  # POSIX
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - Windows
    _fcntl = None
try:  # Windows
    import msvcrt as _msvcrt
except ImportError:
    _msvcrt = None

SCHEMA_ESTADO = "rs-estado/1"
ARQ_TRAVA = ".rs.lock"
DICA_ESTADO_CORROMPIDO = ("não edite rs_estado.json à mão; restaure a última versão boa do controle de versão (git) "
                          "ou de uma cópia. O rs_log.jsonl continua sendo a fonte de verdade do histórico")


class ErroProjeto(RuntimeError):
    """Projeto não encontrado ou estado inconsistente."""


def agora():
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def sha256_texto(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Escrita atômica com permissão de arquivo comum
# ---------------------------------------------------------------------------
def _ler_umask():
    """umask do processo (lida uma vez, na importação, quando só há uma thread)."""
    try:
        atual = os.umask(0o022)
        os.umask(atual)
        return atual
    except (AttributeError, OSError):  # pragma: no cover
        return 0o022


_UMASK = _ler_umask()


def modo_arquivo_padrao():
    """Permissão de um arquivo novo criado com open(): 0666 menos a umask (0644 com a umask 022)."""
    return 0o666 & ~_UMASK


def escrever_atomico(caminho, texto, encoding="utf-8", newline=None):
    """Grava `texto` via arquivo temporário na mesma pasta + os.replace, com permissão 0666 menos a umask.

    tempfile.mkstemp cria com 0600; sem o chmod, coautores de uma pasta compartilhada não leem o arquivo.
    `newline=""` grava as quebras de linha como estão no texto (CSV montado pelo módulo csv).
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{caminho.name}.", suffix=".tmp", dir=str(caminho.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline=newline) as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.chmod(tmp, modo_arquivo_padrao())
        except OSError:  # pragma: no cover - sistema de arquivos sem permissões POSIX
            pass
        os.replace(tmp, caminho)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return caminho


# ---------------------------------------------------------------------------
# Trava entre processos (reentrante no mesmo processo e thread)
# ---------------------------------------------------------------------------
_TRAVA_REGISTRO = threading.Lock()
_TRAVAS_THREAD = {}          # caminho da trava -> threading.RLock
_LOCAL = threading.local()   # .ativas: {caminho da trava: [profundidade, arquivo]}


def _travar_arquivo(arquivo, espera_max=None):
    if _fcntl is not None:
        _fcntl.flock(arquivo.fileno(), _fcntl.LOCK_EX)
        return
    if _msvcrt is not None:  # pragma: no cover - Windows
        inicio = time.monotonic()
        while True:
            try:
                arquivo.seek(0)
                _msvcrt.locking(arquivo.fileno(), _msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if espera_max is not None and time.monotonic() - inicio > espera_max:
                    raise
                time.sleep(0.05)


def _destravar_arquivo(arquivo):
    try:
        if _fcntl is not None:
            _fcntl.flock(arquivo.fileno(), _fcntl.LOCK_UN)
        elif _msvcrt is not None:  # pragma: no cover - Windows
            arquivo.seek(0)
            _msvcrt.locking(arquivo.fileno(), _msvcrt.LK_UNLCK, 1)
    except OSError:  # pragma: no cover
        pass


@contextlib.contextmanager
def trava(raiz):
    """Trava exclusiva do projeto em <raiz>/.rs.lock para escrever estado e log.

    Reentrante: dentro de `with trava(raiz)` as funções deste módulo podem ser chamadas de novo
    sem travar a si mesmas. Se o arquivo de trava não puder ser criado (pasta só de leitura), segue
    só com a trava de thread; a escrita que vier depois falha com o erro do próprio sistema.
    """
    raiz = Path(raiz)
    try:
        chave = str(raiz.resolve() / ARQ_TRAVA)
    except OSError:  # pragma: no cover
        chave = str(raiz / ARQ_TRAVA)
    with _TRAVA_REGISTRO:
        trava_thread = _TRAVAS_THREAD.setdefault(chave, threading.RLock())
    with trava_thread:
        ativas = getattr(_LOCAL, "ativas", None)
        if ativas is None:
            ativas = _LOCAL.ativas = {}
        if chave in ativas:
            ativas[chave][0] += 1
            try:
                yield
            finally:
                ativas[chave][0] -= 1
            return
        arquivo = None
        try:
            if raiz.is_dir():
                arquivo = open(chave, "a+b")
        except OSError:
            arquivo = None
        try:
            if arquivo is not None:
                _travar_arquivo(arquivo)
            ativas[chave] = [1, arquivo]
            try:
                yield
            finally:
                del ativas[chave]
                if arquivo is not None:
                    _destravar_arquivo(arquivo)
        finally:
            if arquivo is not None:
                arquivo.close()


# ---------------------------------------------------------------------------
# Base da mescla em três vias (versão do disco que cada objeto de estado conhece)
# ---------------------------------------------------------------------------
_MAX_BASES = 64
_BASES = collections.OrderedDict()   # id(estado) -> (estado, base); a referência forte impede reuso do id
_BASES_TRAVA = threading.Lock()
_AUSENTE = object()


def _guardar_base(estado, texto):
    base = json.loads(texto)
    with _BASES_TRAVA:
        _BASES[id(estado)] = (estado, base)
        _BASES.move_to_end(id(estado))
        while len(_BASES) > _MAX_BASES:
            _BASES.popitem(last=False)


def _base_de(estado):
    with _BASES_TRAVA:
        par = _BASES.get(id(estado))
    return par[1] if par and par[0] is estado else None


def _eh_lista_por_id(*listas):
    """Listas de objetos com `id` textual único em cada lista (pendencias, buscas)."""
    itens = [x for lista in listas if isinstance(lista, list) for x in lista]
    if not itens or not all(isinstance(x, dict) and isinstance(x.get("id"), str) and x.get("id") for x in itens):
        return False
    # ids repetidos (estado antigo corrompido por gravações concorrentes): não mescla por id, para não perder itens
    return all(len({x["id"] for x in lista}) == len(lista) for lista in listas if isinstance(lista, list))


def _eh_lista_simples(*listas):
    for lista in listas:
        if not isinstance(lista, list):
            return False
        for x in lista:
            if isinstance(x, (dict, list)) or isinstance(x, float):
                return False
        if len(set(map(json.dumps, lista))) != len(lista):
            return False
    return True


def _mesclar(base, meu, deles):
    """Valor mesclado em três vias. Dicts e listas de `meu` são alterados no lugar quando possível."""
    if isinstance(meu, dict) and isinstance(deles, dict):
        base_d = base if isinstance(base, dict) else {}
        for k in list(meu) + [k for k in deles if k not in meu]:
            r = _mesclar(base_d.get(k, _AUSENTE), meu.get(k, _AUSENTE), deles.get(k, _AUSENTE))
            if r is _AUSENTE:
                meu.pop(k, None)
            else:
                meu[k] = r
        return meu
    if meu == base:
        return deles
    if deles == base or deles == meu:
        return meu
    if isinstance(meu, list) and isinstance(deles, list):
        base_l = base if isinstance(base, list) else []
        if _eh_lista_por_id(base_l, meu, deles):
            meu[:] = _mesclar_lista_por_id(base_l, meu, deles)
            return meu
        if _eh_lista_simples(base_l, meu, deles):
            ids_base, ids_meu, ids_deles = (list(map(json.dumps, x)) for x in (base_l, meu, deles))
            resultado = [x for x, j in zip(meu, ids_meu) if j in ids_deles or j not in ids_base]
            resultado += [x for x, j in zip(deles, ids_deles) if j not in ids_meu and j not in ids_base]
            meu[:] = resultado
            return meu
    return meu  # conflito no mesmo campo: vale quem grava agora


def _mesclar_lista_por_id(base, meu, deles):
    por_id = lambda lista: {x["id"]: x for x in lista}  # noqa: E731
    b, m, d = por_id(base), por_id(meu), por_id(deles)
    resultado = []
    for item in deles:
        i = item["id"]
        if i in m:
            resultado.append(_mesclar(b.get(i, _AUSENTE), m[i], item))
        elif i not in b or item != b[i]:  # novo do outro processo (ou mudado por ele depois que este apagou)
            resultado.append(item)
    for item in meu:
        i = item["id"]
        if i not in d and (i not in b or item != b[i]):  # novo deste processo (ou mudado aqui depois que o outro apagou)
            resultado.append(item)
    return resultado


# ---------------------------------------------------------------------------
# Projeto e estado
# ---------------------------------------------------------------------------
def encontrar_projeto(inicio=None):
    """Sobe diretórios a partir de `inicio` até achar rs_estado.json. Devolve Path ou None."""
    atual = Path(inicio or os.getcwd()).resolve()
    for pasta in [atual, *atual.parents]:
        if (pasta / esquema.ARQ_ESTADO).exists():
            return pasta
    return None


def exigir_projeto(inicio=None):
    raiz = encontrar_projeto(inicio)
    if raiz is None:
        raise ErroProjeto(
            "Nenhum rs_estado.json encontrado a partir de "
            f"{Path(inicio or os.getcwd()).resolve()}. Rode `rs.py init` ou `rs.py status`."
        )
    return raiz


def estado_inicial(titulo, tipo_revisao="indefinido", idioma="pt-BR", autonomia="checkpoints",
                   triagem="subagentes", parcial=None):
    etapas = {e: {"status": "pendente", "portao": None, "aprovado_por": None, "em": None} for e in esquema.ETAPAS}
    for portao, etapa in esquema.PORTOES.items():
        etapas[etapa]["portao"] = portao
    return {
        "schema": SCHEMA_ESTADO,
        "projeto": {
            "titulo": titulo,
            "pergunta": "",
            "tipo_revisao": tipo_revisao,
            "idioma_produtos": idioma,
            "criado_em": agora(),
            "parcial": parcial,
            "etapas_ignoradas": [],
        },
        "modo": {"autonomia": autonomia, "triagem": triagem, "definido_em": agora()},
        "ambiente": {},
        "papeis": {},
        "preferencias": {},
        "versoes_ativas": {},
        "artefatos": {},
        "etapas": etapas,
        "buscas": [],
        "pendencias": [],
        "contagens_cache": {},
        "ultimo_seq": 0,
    }


def _ler_texto_estado(caminho):
    try:
        with open(caminho, encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError as e:
        raise ErroProjeto(f"{caminho} não é texto UTF-8 válido ({e}): {DICA_ESTADO_CORROMPIDO}") from e


def _interpretar_estado(caminho, texto):
    try:
        estado = json.loads(texto)
    except json.JSONDecodeError as e:
        raise ErroProjeto(f"{caminho} está corrompido (JSON inválido na linha {e.lineno}, coluna {e.colno}: "
                          f"{e.msg}): {DICA_ESTADO_CORROMPIDO}") from e
    if not isinstance(estado, dict):
        raise ErroProjeto(f"{caminho} não contém um objeto JSON: {DICA_ESTADO_CORROMPIDO}")
    return estado


def carregar_estado(raiz):
    caminho = Path(raiz) / esquema.ARQ_ESTADO
    if not caminho.exists():
        raise ErroProjeto(f"{caminho} não existe")
    texto = _ler_texto_estado(caminho)
    estado = _interpretar_estado(caminho, texto)
    if estado.get("schema") != SCHEMA_ESTADO:
        raise ErroProjeto(f"schema de estado inesperado: {estado.get('schema')}")
    _guardar_base(estado, texto)
    return estado


def salvar_estado(raiz, estado):
    """Grava o estado de forma atômica, dentro da trava, mesclando com o que outro processo gravou.

    A mescla só acontece para objetos que vieram de carregar_estado (ou já foram salvos por aqui);
    um dict novo (ex.: estado_inicial) substitui o arquivo inteiro, como antes.
    """
    caminho = Path(raiz) / esquema.ARQ_ESTADO
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with trava(raiz):
        base = _base_de(estado)
        if base is not None and caminho.exists():
            try:
                disco = json.loads(_ler_texto_estado(caminho))
            except (ErroProjeto, ValueError, OSError):
                disco = None  # arquivo ilegível: a versão deste processo o substitui
            if isinstance(disco, dict) and disco != base:
                _mesclar(base, estado, disco)
        texto = json.dumps(estado, ensure_ascii=False, indent=2) + "\n"
        escrever_atomico(caminho, texto)
        _guardar_base(estado, texto)


def _ultimo_seq_do_log(raiz):
    caminho = Path(raiz) / esquema.ARQ_LOG
    if not caminho.exists():
        return 0
    ultimo = 0
    with open(caminho, encoding="utf-8", errors="replace") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                ultimo = max(ultimo, int(json.loads(linha).get("seq", 0)))
            except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
                continue  # linha final truncada por queda: ignorada, nunca reescrita
    return ultimo


def registrar_evento(raiz, evento, etapa, ator_tipo, ator_id, dados=None, artefatos=None,
                     motivo=None, modelo=None, estado=None):
    """Acrescenta um evento ao rs_log.jsonl e atualiza ultimo_seq no estado.

    `artefatos` é uma lista de caminhos relativos à raiz; o sha256 é calculado aqui.
    Se `estado` for passado, ele é atualizado e salvo (mesclado com o disco); senão é carregado
    dentro da trava e salvo. O seq sai do log, dentro da trava: nunca se repete entre processos.
    """
    if evento not in esquema.EVENTOS:
        raise ValueError(f"evento desconhecido: {evento}")
    if ator_tipo not in esquema.TIPOS_ATOR:
        raise ValueError(f"tipo de ator desconhecido: {ator_tipo}")
    raiz = Path(raiz)
    with trava(raiz):
        estado = estado if estado is not None else carregar_estado(raiz)
        seq = max(int(estado.get("ultimo_seq", 0) or 0), _ultimo_seq_do_log(raiz)) + 1
        registros_artefatos = []
        for rel in artefatos or []:
            p = raiz / rel
            registros_artefatos.append({"caminho": str(rel), "sha256": sha256_arquivo(p) if p.exists() else ""})
        linha = {
            "seq": seq,
            "ts": agora(),
            "evento": evento,
            "etapa": etapa,
            "ator": {"tipo": ator_tipo, "id": ator_id, "modelo": modelo},
            "dados": dados or {},
            "artefatos": registros_artefatos,
            "motivo": motivo,
        }
        caminho = raiz / esquema.ARQ_LOG
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        estado["ultimo_seq"] = seq
        salvar_estado(raiz, estado)
    return linha


def ler_log(raiz):
    caminho = Path(raiz) / esquema.ARQ_LOG
    eventos = []
    if not caminho.exists():
        return eventos
    with open(caminho, encoding="utf-8", errors="replace") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                try:
                    eventos.append(json.loads(linha))
                except json.JSONDecodeError:
                    continue
    return eventos


def marcar_etapa(raiz, etapa, status, aprovado_por=None, estado=None):
    if etapa not in esquema.ETAPAS:
        raise ValueError(f"etapa desconhecida: {etapa}")
    if status not in esquema.STATUS_ETAPA:
        raise ValueError(f"status desconhecido: {status}")
    with trava(raiz):
        estado = estado if estado is not None else carregar_estado(raiz)
        registro = estado["etapas"].setdefault(etapa, {"status": "pendente", "portao": None})
        registro["status"] = status
        registro["em"] = agora()
        if aprovado_por is not None:
            registro["aprovado_por"] = aprovado_por
        salvar_estado(raiz, estado)
    return estado


def abrir_pendencia(raiz, tipo, etapa, descricao, portao=None, n=None, arquivo=None, ator_id="script"):
    with trava(raiz):
        estado = carregar_estado(raiz)
        numeros = [int(p["id"][1:]) for p in estado["pendencias"]
                   if str(p.get("id", "")).startswith("P") and str(p.get("id", ""))[1:].isdigit()]
        pid = f"P{(max(numeros) + 1 if numeros else 1):03d}"
        estado["pendencias"].append({
            "id": pid, "tipo": tipo, "etapa": etapa, "portao": portao, "descricao": descricao,
            "n": n, "arquivo": arquivo, "status": "aberta",
        })
        registrar_evento(raiz, "pendencia_aberta", etapa, "script", ator_id,
                         dados={"pendencia": pid, "tipo": tipo, "portao": portao, "descricao": descricao, "n": n},
                         artefatos=[arquivo] if arquivo else None, estado=estado)
    return pid


def fechar_pendencia(raiz, pid, motivo, ator_tipo="humano", ator_id=esquema.PAPEL_HUMANO_PADRAO):
    with trava(raiz):
        estado = carregar_estado(raiz)
        for p in estado["pendencias"]:
            if p["id"] == pid:
                if p["status"] == "fechada":
                    return False
                p["status"] = "fechada"
                registrar_evento(raiz, "pendencia_fechada", p["etapa"], ator_tipo, ator_id,
                                 dados={"pendencia": pid}, motivo=motivo, estado=estado)
                return True
    raise ErroProjeto(f"pendência {pid} não existe")


def pendencias_abertas(estado):
    return [p for p in estado.get("pendencias", []) if p.get("status") == "aberta"]


def registrar_portao(raiz, portao, aprovado_por, criterios=None, ator_tipo="humano", motivo=None):
    """Registra decisão de portão. No autopiloto, aprovado_por='autopiloto' e criterios traz os valores."""
    if portao not in esquema.PORTOES:
        raise ValueError(f"portão desconhecido: {portao}")
    etapa = esquema.PORTOES[portao]
    with trava(raiz):
        estado = carregar_estado(raiz)
        if (estado["modo"]["autonomia"] == "autopiloto" and portao in esquema.PORTOES_SEMPRE_PARAM_AUTOPILOTO
                and ator_tipo != "humano"):
            raise ErroProjeto(f"{portao} exige aprovação humana mesmo no autopiloto")
        estado["etapas"][etapa].update({"status": "concluida", "aprovado_por": aprovado_por, "em": agora()})
        return registrar_evento(raiz, "portao", etapa, ator_tipo, aprovado_por,
                                dados={"portao": portao, "criterios": criterios or {}}, motivo=motivo, estado=estado)


def resumo(dados):
    """Imprime o resumo JSON na última linha do stdout (convenção de todos os subcomandos)."""
    print(json.dumps(dados, ensure_ascii=False, default=str))
