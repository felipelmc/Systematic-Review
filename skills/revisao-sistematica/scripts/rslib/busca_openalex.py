"""Busca na API do OpenAlex com registro auditável (PRISMA-S) e importação para o esquema.

USO
    python3 rs.py buscar openalex --busca-id B05 --query '"conditional cash" AND school' \
        [--filtro "publication_year:2000-2025,type:article"] \
        [--campo title_and_abstract|title|abstract|fulltext|search|title_and_abstract.search.exact|title.search.exact|abstract.search.exact] \
        [--string-id S-oa-v1] [--estrutura PICOC] [--max-paginas N] [--contar | --listar N] \
        [--substituir B02 --motivo "string v2 depois do teste de âncoras"]

    --contar   só consulta `meta.count` (uma requisição) e não grava nada; serve para
               calibrar strings na etapa de pergunta/busca, com ou sem projeto.
    --listar N grava as N primeiras obras (na ordem devolvida pela API) em
               `00-protocolo/exploracao_<busca_id>.csv` (posicao, id_openalex, titulo,
               ano, doi, citado_por), sem importar nem registrar busca. Com projeto,
               registra só um evento `artefato_versionado`; sem projeto, grava em
               `<--dir ou pasta atual>/00-protocolo/`. Serve para a busca exploratória
               (colher termos, conferir se estudos conhecidos aparecem) sem inflar o
               PRISMA. Recusa sobrescrever um arquivo congelado no G2.

    --busca-id segue a MESMA regra do `rs.py importar` (letras maiúsculas + número:
    B05, SN1), conferida antes de qualquer chamada à API; buscas substituídas
    (`ativa: false`) são recusadas.

    --substituir <busca_id_antiga> --motivo "..." tem a mesma semântica de
    `rs.py importar --substituir`: validado antes de chamar a API (id, busca existente
    e ainda ativa, motivo obrigatório) e aplicado só depois que a busca nova foi gravada
    e registrada. A antiga recebe `ativa: false` sem perder linhas e o log recebe
    `busca_substituida`; rode `rs.py dedup` em seguida. Não vale com --contar/--listar.

CAMPOS DE BUSCA (--campo)
    title_and_abstract (padrão), title, abstract, fulltext -> filtro `<campo>.search`:
        a API aplica stemming e remove palavras vazias ("schools" casa "school").
        NÃO aceita curinga: `school*` devolve HTTP 400, inclusive dentro de frase
        entre aspas.
    title_and_abstract.search.exact, title.search.exact, abstract.search.exact ->
        filtro exato, sem stemming. Use quando a string tiver curinga (`transfer*`)
        ou quando a frase precisar casar palavra por palavra ("cash transfer" sem
        virar "cash transfers"/"transferring"). Sem stemming, liste as variantes ou
        use o curinga; conte com --contar e compare com o campo padrão antes de
        congelar a string.
    search -> parâmetro `search` (título, resumo e texto completo; aceita vírgula).
    Em HTTP 400 com `*` na string e campo sem `.exact`, a mensagem de erro sugere o
    campo exato.

O que faz
    1. Pagina a API com cursor (200 por página), re-tentando cada página com espera
       crescente em erros de rede, 429 e 5xx (respeita Retry-After). Diferente do
       script de origem, que refazia a paginação inteira, aqui a retomada é por página:
       o cursor permite continuar de onde parou sem duplicar obras.
    2. Grava o JSONL bruto em `01-busca/brutos/<busca_id>_openalex.jsonl` e os
       parâmetros exatos da consulta (sem a chave de API) em
       `01-busca/brutos/<busca_id>_openalex.consulta.json`, para o log PRISMA-S.
    3. Importa: se o importador do projeto (`rs.py importar`, módulo
       `rslib.importar.cli`) estiver instalado, delega a ele pelo contrato de linha de
       comando; senão usa a conversão própria deste módulo (`obra_para_registro`).
    4. Registra a busca em `estado["buscas"]` e o evento `busca_registrada`. No estado,
       `n_api` é o total informado pela API (o "número da base" do PRISMA-S) e
       `n_bruto` o número de obras baixadas. O resumo traz `busca_registrada: true`
       quando o evento existe (gravado agora ou numa execução anterior do mesmo JSONL).

Por que o filtro `<campo>.search` e não o parâmetro `search`: o filtro por título e
resumo reproduz o recorte usado nas bases por assinatura (TITLE-ABS), enquanto
`search` também varre texto completo. Vírgulas separam filtros na API, então uma
string com vírgula no modo filtro é recusada (use `--campo search`).
Filtros repetidos com a mesma chave são concatenados pela API sem o AND; por isso
a string inteira vai num único filtro de busca.

Credenciais: `RS_EMAIL` vira `mailto` (fila educada) e `OPENALEX_API_KEY` vira
`api_key`; ambas só por variável de ambiente e nunca gravadas em disco.

Só para testes: com `RS_TESTE_OPENALEX_RESPOSTAS=<arquivo.json>`, `criar_sessao()` devolve
uma sessão falsa que responde a partir desse arquivo, sem rede (formato em
`SessaoArquivoOpenAlex`). É o ponto de injeção do teste ponta a ponta, que roda
`rs.py bola-de-neve` num processo novo e não pode trocar funções por monkeypatch. O
comando avisa no stderr quando ela está ativa; nunca use numa revisão real.

Idempotência: um `busca_id` é imutável. Rodar de novo com a mesma consulta reusa o
JSONL já gravado (sem rede) e não duplica registros; com consulta diferente, o
comando recusa e pede um novo id.
"""

import argparse
import contextlib
import importlib
import io
import json
import os
import re
import sys
import time
from pathlib import Path

from . import esquema, estado, normalizar
from .handoff import escrever_csv, escrever_texto, falhar, ler_csv
from .importar import buscas as _buscas
from .importar import flags as _flags
from .importar.detectar import ErroImportacao

URL_BASE = "https://api.openalex.org"
POR_PAGINA = 200
LOTE_IDS = 50  # obras por requisição no filtro ids.openalex (limite da API para OR é 100)
CAMPOS_SELECT = [
    "id", "doi", "title", "display_name", "publication_year", "publication_date", "type", "language",
    "primary_location", "authorships", "abstract_inverted_index", "cited_by_count", "biblio",
    "keywords", "referenced_works", "ids", "is_retracted",
]
CAMPOS_BUSCA_EXATOS = ["title_and_abstract.search.exact", "title.search.exact", "abstract.search.exact"]
CAMPOS_BUSCA = ["title_and_abstract", "title", "abstract", "fulltext", "search"] + CAMPOS_BUSCA_EXATOS
CAMPOS_LISTAR = ["id", "display_name", "title", "publication_year", "doi", "cited_by_count"]
COLUNAS_EXPLORACAO = ["posicao", "id_openalex", "titulo", "ano", "doi", "citado_por"]
MODULO_IMPORTADOR = "rslib.importar.cli"
ATOR = "rs.py buscar openalex"


class ErroOpenAlex(RuntimeError):
    """Falha definitiva numa chamada à API (depois das re-tentativas ou erro 4xx)."""


# ---------------------------------------------------------------------------
# Cliente HTTP
# ---------------------------------------------------------------------------
VAR_TESTE_RESPOSTAS = "RS_TESTE_OPENALEX_RESPOSTAS"


class _RespostaArquivo:
    def __init__(self, status_code, dados):
        self.status_code = status_code
        self.headers = {}
        self._dados = dados
        self.text = json.dumps(dados, ensure_ascii=False)

    def json(self):
        return self._dados


class SessaoArquivoOpenAlex:
    """Sessão falsa (SÓ PARA TESTES) que responde à API de obras a partir de um JSON local.

    Formato do arquivo: {"obras": {"W1": {obra do OpenAlex, com referenced_works se houver}},
    "citacoes": {"W1": ["W9", ...]}}. Rotas: works/W.. e works/doi:.. (404 se não houver);
    filter cites:W, ids.openalex:W|W, *.search / *.search.exact (+ publication_year) ou search → lista.
    """

    falsa = True

    def __init__(self, caminho):
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        self.obras = {id_curto(k): v for k, v in (dados.get("obras") or {}).items()}
        self.citacoes = {id_curto(k): [id_curto(w) for w in v] for k, v in (dados.get("citacoes") or {}).items()}
        self.headers = {}
        self.chamadas = []
        print(f"[aviso] {VAR_TESTE_RESPOSTAS} ativo: respostas do OpenAlex lidas de {caminho} (só para testes)",
              file=sys.stderr)

    def get(self, url, params=None, timeout=None):
        params = params or {}
        self.chamadas.append((url, dict(params)))
        rota = url.split("api.openalex.org/", 1)[-1]
        if rota.startswith("works/"):
            ident = rota[len("works/"):]
            if ident.lower().startswith("doi:"):
                doi = normalizar.doi(ident[4:])
                obra = next((o for o in self.obras.values() if doi and normalizar.doi(o.get("doi")) == doi), None)
            else:
                obra = self.obras.get(id_curto(ident))
            return _RespostaArquivo(200, obra) if obra else _RespostaArquivo(404, {"error": "not found"})
        filtro = params.get("filter") or ""
        if filtro.startswith("cites:"):
            resultados = [self.obras[w] for w in self.citacoes.get(id_curto(filtro.split(":", 1)[1]), [])
                          if w in self.obras]
        elif filtro.startswith("ids.openalex:"):
            resultados = [self.obras[i] for i in map(id_curto, filtro.split(":", 1)[1].split("|")) if i in self.obras]
        elif ".search:" in filtro or ".search.exact:" in filtro or params.get("search"):
            ano = re.search(r"publication_year:(\d{4})", filtro)
            resultados = [o for o in self.obras.values() if not ano or str(o.get("publication_year")) == ano.group(1)]
        else:
            resultados = []
        return _RespostaArquivo(200, {"meta": {"count": len(resultados), "next_cursor": None}, "results": resultados})


def criar_sessao():
    """Sessão requests; separada numa função para os testes substituírem por uma falsa.

    Com RS_TESTE_OPENALEX_RESPOSTAS definido, devolve SessaoArquivoOpenAlex (testes em processo novo).
    """
    if os.environ.get(VAR_TESTE_RESPOSTAS):
        return SessaoArquivoOpenAlex(os.environ[VAR_TESTE_RESPOSTAS])
    import requests
    s = requests.Session()
    s.headers["User-Agent"] = "revisao-sistematica-skill (+https://openalex.org)"
    return s


class ClienteOpenAlex:
    """Cliente mínimo da API de obras com re-tentativa por requisição.

    `sessao` precisa ter `.get(url, params=..., timeout=...)` devolvendo um objeto
    com `status_code`, `headers` e `.json()`. `espera` é injetável para testes.
    """

    def __init__(self, sessao=None, email=None, api_key=None, tentativas=5, pausa=2.0, timeout=60,
                 espera=None):
        self.sessao = sessao if sessao is not None else criar_sessao()
        self.email = email if email is not None else os.environ.get("RS_EMAIL")
        self.api_key = api_key if api_key is not None else os.environ.get("OPENALEX_API_KEY")
        self.tentativas = tentativas
        self.pausa = pausa
        self.timeout = timeout
        self.espera = espera if espera is not None else (lambda segundos: time.sleep(segundos))
        self.n_requisicoes = 0

    def _params(self, params):
        p = {k: v for k, v in (params or {}).items() if v is not None}
        if self.email:
            p["mailto"] = self.email
        if self.api_key:
            p["api_key"] = self.api_key
        return p

    def get(self, caminho, params=None, aceitar_404=False):
        url = caminho if caminho.startswith("http") else f"{URL_BASE}/{caminho.lstrip('/')}"
        ultimo = None
        for tentativa in range(1, self.tentativas + 1):
            self.n_requisicoes += 1
            try:
                resp = self.sessao.get(url, params=self._params(params), timeout=self.timeout)
            except OSError as e:  # requests.RequestException herda de OSError: queda de rede, timeout
                ultimo = f"{type(e).__name__}: {e}"
                self._esperar(tentativa, None)
                continue
            codigo = int(getattr(resp, "status_code", 0))
            if codigo == 200:
                return resp.json()
            if codigo == 404 and aceitar_404:
                return None
            if codigo == 429 or codigo >= 500:
                ultimo = f"HTTP {codigo}"
                self._esperar(tentativa, (getattr(resp, "headers", None) or {}).get("Retry-After"))
                continue
            try:
                detalhe = resp.json()
            except Exception:  # noqa: BLE001
                detalhe = getattr(resp, "text", "")
            raise ErroOpenAlex(f"HTTP {codigo} em {url}: {str(detalhe)[:300]}")
        raise ErroOpenAlex(f"falha após {self.tentativas} tentativas em {url}: {ultimo}")

    def _esperar(self, tentativa, retry_after):
        if tentativa >= self.tentativas:
            return
        try:
            segundos = float(retry_after) if retry_after is not None else self.pausa * tentativa
        except ValueError:
            segundos = self.pausa * tentativa
        self.espera(min(segundos, 120.0))

    def contar(self, filtro=None, busca=None):
        dados = self.get("works", {"filter": filtro, "search": busca, "per-page": 1, "select": "id"})
        return int((dados or {}).get("meta", {}).get("count") or 0)

    def paginar(self, filtro=None, busca=None, select=None, por_pagina=POR_PAGINA, max_paginas=None):
        """Gera páginas (lista de obras) pelo cursor; devolve também meta.count na 1ª página."""
        cursor = "*"
        pagina = 0
        while cursor:
            dados = self.get("works", {
                "filter": filtro, "search": busca, "per-page": por_pagina, "cursor": cursor,
                "select": ",".join(select or CAMPOS_SELECT),
            }) or {}
            obras = dados.get("results") or []
            pagina += 1
            yield dados.get("meta", {}), obras
            cursor = (dados.get("meta") or {}).get("next_cursor")
            if not obras or (max_paginas is not None and pagina >= max_paginas):
                break

    def obra(self, identificador, select=None):
        """Uma obra por W id, URL do OpenAlex ou `doi:10.x/...`; None se não existir."""
        ident = str(identificador).strip()
        if ident.startswith("https://openalex.org/"):
            ident = ident.rsplit("/", 1)[-1]
        return self.get(f"works/{ident}", {"select": ",".join(select or CAMPOS_SELECT)}, aceitar_404=True)

    def obras_por_ids(self, ids, select=None):
        """Metadados de várias obras (em lotes) pelo filtro ids.openalex."""
        ids = [id_curto(i) for i in ids if id_curto(i)]
        saida = []
        for inicio in range(0, len(ids), LOTE_IDS):
            lote = ids[inicio:inicio + LOTE_IDS]
            for _, obras in self.paginar(filtro="ids.openalex:" + "|".join(lote), select=select,
                                         por_pagina=LOTE_IDS):
                saida.extend(obras)
        return saida


def id_curto(valor):
    """'https://openalex.org/W123' -> 'W123'; '' se não for um W id."""
    s = str(valor or "").strip().rsplit("/", 1)[-1]
    return s.upper() if re.fullmatch(r"[Ww]\d+", s) else ""


# ---------------------------------------------------------------------------
# Conversão de obras (porta de reconstruct_abstract e flatten_works)
# ---------------------------------------------------------------------------
def reconstruir_resumo(indice_invertido):
    """Reconstrói o resumo a partir do índice invertido do OpenAlex ('' se ausente)."""
    if not isinstance(indice_invertido, dict) or not indice_invertido:
        return ""
    posicoes = {}
    for palavra, lista in indice_invertido.items():
        for pos in lista or []:
            posicoes[int(pos)] = palavra
    return " ".join(posicoes[p] for p in sorted(posicoes))


def _dict(valor):
    return valor if isinstance(valor, dict) else {}


def obra_para_registro(obra, busca_id, linha, arquivo_origem, metodo="base", estrutura="", importado_em=None):
    """Achata uma obra do OpenAlex numa linha de `esquema.COLUNAS_REGISTROS`."""
    local = _dict(obra.get("primary_location"))
    fonte = _dict(local.get("source"))
    biblio = _dict(obra.get("biblio"))
    nomes, paises, instituicoes = [], [], []
    for autoria in obra.get("authorships") or []:
        autoria = _dict(autoria)
        nome = normalizar.texto(_dict(autoria.get("author")).get("display_name") or autoria.get("raw_author_name"))
        if nome:
            nomes.append(nome)
        for pais in autoria.get("countries") or []:
            if pais and pais not in paises:
                paises.append(pais)
        for inst in autoria.get("institutions") or []:
            nome_inst = normalizar.texto(_dict(inst).get("display_name"))
            if nome_inst and nome_inst not in instituicoes:
                instituicoes.append(nome_inst)
    autores_brutos = " | ".join(n.replace("|", " ") for n in nomes)
    paginas = "-".join(p for p in [str(biblio.get("first_page") or ""), str(biblio.get("last_page") or "")] if p)
    palavras = [normalizar.texto(_dict(k).get("display_name") if isinstance(k, dict) else k)
                for k in (obra.get("keywords") or [])]
    doi = normalizar.doi(obra.get("doi"))
    return {
        "id_registro": f"{busca_id}-{int(linha):05d}",
        "busca_id": busca_id,
        "fonte": "openalex",
        "metodo_identificacao": metodo,
        "arquivo_origem": arquivo_origem,
        "linha_origem": str(linha),
        "id_fonte": id_curto(obra.get("id")),
        "doi": doi,
        "titulo": normalizar.texto(obra.get("title") or obra.get("display_name")),
        "titulo_alt": "",
        # autores_canonicos pode deixar espaço duplo ao retirar o sobrenome do meio do nome
        "autores": re.sub(r"\s{2,}", " ", normalizar.autores_canonicos(autores_brutos)) if autores_brutos else "",
        "primeiro_autor_sobrenome": normalizar.sobrenome_primeiro_autor(autores_brutos) if autores_brutos else "",
        "n_autores": str(len(nomes)),
        "ano": normalizar.ano(obra.get("publication_year")),
        "tipo_publicacao_orig": normalizar.texto(obra.get("type")),
        # "dissertation" do OpenAlex cobre teses e dissertações: vai para `tese`, como no importador
        "tipo_publicacao": "tese" if obra.get("type") == "dissertation" else normalizar.tipo_publicacao(obra.get("type")),
        "idioma": normalizar.idioma(obra.get("language")),
        "veiculo": normalizar.texto(fonte.get("display_name")),
        "volume": normalizar.texto(biblio.get("volume")),
        "numero": normalizar.texto(biblio.get("issue")),
        "paginas": paginas,
        "resumo": normalizar.texto(reconstruir_resumo(obra.get("abstract_inverted_index"))),
        "resumo_truncado": "0",
        "palavras_chave": "; ".join(p for p in palavras if p),
        "pais_afiliacao": "; ".join(paises),
        "instituicao": "; ".join(instituicoes[:5]),
        "url": normalizar.texto(local.get("landing_page_url")) or (f"https://doi.org/{doi}" if doi else ""),
        "citado_por": str(obra.get("cited_by_count") or 0),
        "estrutura": estrutura or "",
        "importado_em": importado_em or estado.agora(),
    }


def ler_jsonl(caminho):
    obras = []
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                try:
                    obras.append(json.loads(linha))
                except json.JSONDecodeError:
                    continue  # linha final truncada por queda: ignorada
    return obras


def escrever_jsonl(caminho, obras):
    escrever_texto(caminho, "".join(json.dumps(o, ensure_ascii=False, sort_keys=True) + "\n" for o in obras))


# ---------------------------------------------------------------------------
# Importação (delegada ao importador do projeto, ou própria)
# ---------------------------------------------------------------------------
def acrescentar_registros(raiz, linhas):
    """Acrescenta linhas a dados/registros.csv sem duplicar id_registro. Devolve n novos."""
    caminho = Path(raiz) / esquema.ARQ_REGISTROS
    existentes = []
    if caminho.exists():
        colunas, existentes = ler_csv(caminho)
        if colunas != esquema.COLUNAS_REGISTROS:
            raise ValueError(f"cabeçalho inesperado em {esquema.ARQ_REGISTROS}; não vou reescrever o arquivo")
    vistos = {l["id_registro"] for l in existentes}
    novos = [l for l in linhas if l["id_registro"] not in vistos]
    if novos or not caminho.exists():
        escrever_csv(caminho, esquema.COLUNAS_REGISTROS, existentes + novos)
    return len(novos)


def _importar_proprio(raiz, arquivo_rel, busca_id, metodo, estrutura):
    obras = ler_jsonl(Path(raiz) / arquivo_rel)
    agora = estado.agora()
    linhas = [obra_para_registro(o, busca_id, i, arquivo_rel, metodo, estrutura, agora)
              for i, o in enumerate(obras, start=1)]
    n_novos = acrescentar_registros(raiz, linhas)
    # is_retracted não cabe em registros.csv: vai para dados/registros_flags.csv, como no importador
    flags_novas = _flags.acrescentar(raiz, [
        {"id_registro": l["id_registro"], "flag": _flags.FLAG_RETRATADO, "origem": "openalex:is_retracted"}
        for l, o in zip(linhas, obras) if o.get("is_retracted")])
    if n_novos or flags_novas:
        artefatos = [arquivo_rel, esquema.ARQ_REGISTROS] + ([_flags.ARQ_REGISTROS_FLAGS] if flags_novas else [])
        estado.registrar_evento(raiz, "importacao", "05_organizacao", "script", "rs.py importar (openalex interno)",
                                dados={"busca_id": busca_id, "fonte": "openalex", "metodo": metodo,
                                       "n_linhas": len(linhas), "n_novos": n_novos,
                                       "n_retratados": len(flags_novas)},
                                artefatos=artefatos)
    return {"via": "interno", "n_linhas": len(linhas), "n_novos": n_novos}


def importar_jsonl(raiz, arquivo_rel, busca_id, metodo="base", estrutura="", usar_importador=True):
    """Importa o JSONL pelo comando `importar` (contrato A2) ou pela conversão interna.

    A delegação usa só o contrato público (`registrar(subparsers)` + flags de
    `rs.py importar`), para não depender de nomes internos do importador. Se o
    módulo não existir ou as flags não baterem, cai na conversão interna com aviso;
    se o importador existir e recusar os dados, o erro dele é devolvido.
    """
    raiz = Path(raiz)
    if usar_importador:
        try:
            modulo = importlib.import_module(MODULO_IMPORTADOR)
        except ImportError:
            modulo = None
        if modulo is not None and hasattr(modulo, "registrar"):
            parser = argparse.ArgumentParser(prog="rs.py", add_help=False)
            parser.add_argument("--dir", default=None)
            sub = parser.add_subparsers(dest="comando")
            modulo.registrar(sub)
            argv = ["--dir", str(raiz), "importar", "--arquivo", str(raiz / arquivo_rel), "--busca-id", busca_id,
                    "--fonte", "openalex", "--metodo", metodo]
            if estrutura:
                argv += ["--estrutura", estrutura]
            saida, erros = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erros):
                    args = parser.parse_args(argv)
                    codigo = int(args.func(args) or 0)
            except SystemExit:
                print("[aviso] `importar` não aceitou as flags do contrato; usando conversão interna",
                      file=sys.stderr)
            else:
                resumo_imp = _ultima_linha_json(saida.getvalue())
                if codigo != 0:
                    raise ValueError(f"importador recusou {arquivo_rel} (código {codigo}): "
                                     f"{erros.getvalue().strip()[-300:]} {resumo_imp}")
                return {"via": "importar", "resumo_importador": resumo_imp}
    return _importar_proprio(raiz, arquivo_rel, busca_id, metodo, estrutura)


def _ultima_linha_json(texto):
    for linha in reversed([l for l in texto.splitlines() if l.strip()]):
        try:
            return json.loads(linha)
        except json.JSONDecodeError:
            continue
    return {}


def registrar_busca(raiz, registro):
    """Upsert por id em estado['buscas'] (o importador pode ter criado a entrada antes)."""
    est = estado.carregar_estado(raiz)
    for b in est["buscas"]:
        if b.get("id") == registro["id"]:
            b.update({k: v for k, v in registro.items() if v is not None})
            break
    else:
        est["buscas"].append(dict(registro, **{esquema.CAMPO_BUSCA_ATIVA: registro.get(esquema.CAMPO_BUSCA_ATIVA, True)}))
    estado.salvar_estado(raiz, est)
    return est


def busca_registrada(raiz, busca_id):
    try:
        est = estado.carregar_estado(raiz)
    except estado.ErroProjeto:
        return None
    return next((b for b in est.get("buscas", []) if b.get("id") == busca_id), None)


def evento_busca_registrada(raiz, busca_id, arquivo_rel, sha):
    """Último evento busca_registrada deste comando para a busca e o JSONL com este sha256 (ou None)."""
    for ev in reversed(estado.ler_log(raiz)):
        if ev.get("evento") != "busca_registrada" or (ev.get("dados") or {}).get("id") != busca_id:
            continue
        if (ev.get("ator") or {}).get("id") != ATOR:
            continue
        if any(a.get("caminho") == arquivo_rel and a.get("sha256") == sha for a in ev.get("artefatos") or []):
            return ev
    return None


# ---------------------------------------------------------------------------
# Comando buscar openalex
# ---------------------------------------------------------------------------
def montar_consulta(query, campo="title_and_abstract", filtro=None):
    """Devolve (filtro, busca) para a API, validando vírgulas no modo filtro."""
    query = (query or "").strip()
    extra = (filtro or "").strip().strip(",")
    if not query and not extra:
        raise ValueError("informe --query e/ou --filtro")
    if campo == "search":
        return (extra or None), (query or None)
    if campo not in CAMPOS_BUSCA:
        raise ValueError(f"--campo inválido: {campo} (use {', '.join(CAMPOS_BUSCA)})")
    if "," in query:
        raise ValueError("a string tem vírgula, que a API lê como separador de filtros; "
                         "remova-a ou use --campo search")
    prefixo = campo if campo in CAMPOS_BUSCA_EXATOS else f"{campo}.search"
    partes = [f"{prefixo}:{query}"] if query else []
    if extra:
        partes.append(extra)
    return ",".join(partes), None


def dica_erro(mensagem, query, campo):
    """Acrescenta ao erro 400 a sugestão do campo exato quando a string tem curinga."""
    if "HTTP 400" in str(mensagem) and "*" in (query or "") and campo not in CAMPOS_BUSCA_EXATOS:
        sugestao = f"{campo}.search.exact" if f"{campo}.search.exact" in CAMPOS_BUSCA_EXATOS \
            else "title_and_abstract.search.exact"
        return (f"{mensagem} | dica: o campo {campo} não aceita curinga (*); use --campo {sugestao}")
    return str(mensagem)


def _validar_busca_id(busca_id):
    """Mesma regra do `rs.py importar`; devolve a mensagem de erro ou None."""
    try:
        _buscas.validar_busca_id(busca_id)
    except ErroImportacao as e:
        return str(e)
    return None


def listar_exploracao(cliente, filtro, busca, n):
    """As n primeiras obras (ordem da API) como linhas de COLUNAS_EXPLORACAO; devolve (linhas, n_api)."""
    linhas, vistos, n_api = [], set(), None
    for meta, pagina in cliente.paginar(filtro=filtro, busca=busca, select=CAMPOS_LISTAR,
                                        por_pagina=min(n, POR_PAGINA)):
        if n_api is None:
            n_api = int((meta or {}).get("count") or 0)
        for obra in pagina:
            wid = id_curto(obra.get("id"))
            if not wid or wid in vistos:
                continue
            vistos.add(wid)
            linhas.append({"posicao": str(len(linhas) + 1), "id_openalex": wid,
                           "titulo": normalizar.texto(obra.get("display_name") or obra.get("title")),
                           "ano": normalizar.ano(obra.get("publication_year")), "doi": normalizar.doi(obra.get("doi")),
                           "citado_por": str(obra.get("cited_by_count") or 0)})
            if len(linhas) >= n:
                return linhas, n_api
    return linhas, n_api


def cmd_listar(args, cliente, filtro, busca):
    comando = "buscar openalex"
    if args.listar < 1:
        return falhar(comando, "--listar exige N >= 1")
    erro = _validar_busca_id(args.busca_id)
    if erro:
        return falhar(comando, erro)
    raiz = estado.encontrar_projeto(args.dir)
    com_projeto = raiz is not None
    raiz = raiz or Path(args.dir or os.getcwd()).resolve()
    rel = f"00-protocolo/exploracao_{args.busca_id}.csv"
    if com_projeto:
        info = (estado.carregar_estado(raiz).get("artefatos") or {}).get(rel) or {}
        if isinstance(info, dict) and info.get("congelado_em"):
            return falhar(comando, f"{rel} foi congelado em {info['congelado_em']}; use outro --busca-id para "
                                   "uma nova exploração")
    try:
        linhas, n_api = listar_exploracao(cliente, filtro, busca, args.listar)
    except ErroOpenAlex as e:
        return falhar(comando, dica_erro(e, args.query, args.campo))
    escrever_csv(raiz / rel, COLUNAS_EXPLORACAO, linhas)
    if com_projeto:
        estado.registrar_evento(raiz, "artefato_versionado", "03_protocolo", "script", ATOR,
                                dados={"tipo": "exploracao_openalex", "busca_id": args.busca_id, "filter": filtro,
                                       "search": busca, "campo": args.campo, "query": args.query, "n_api": n_api,
                                       "n_listadas": len(linhas), "importado": False},
                                artefatos=[rel])
    estado.resumo({"comando": comando, "ok": True, "listar": True, "busca_id": args.busca_id, "n_api": n_api,
                   "n_listadas": len(linhas), "arquivo": rel if com_projeto else str(raiz / rel),
                   "com_projeto": com_projeto, "filtro": filtro, "search": busca, "importado": False,
                   "busca_registrada": False})
    return 0


def cmd_buscar_openalex(args):
    comando = "buscar openalex"
    try:
        filtro, busca = montar_consulta(args.query, args.campo, args.filtro)
    except ValueError as e:
        return falhar(comando, str(e))
    listar = getattr(args, "listar", None)
    substituir, motivo = getattr(args, "substituir", None), getattr(args, "motivo", None)
    if listar is not None and args.contar:
        return falhar(comando, "--listar e --contar são alternativos")
    if (substituir or motivo) and (listar is not None or args.contar):
        return falhar(comando, "--substituir/--motivo só valem na busca completa (sem --contar e sem --listar)")
    if listar is None and not args.contar:
        # validação antes de qualquer chamada à API (antes: um id que o importador recusa gravava o JSONL)
        erro = _validar_busca_id(args.busca_id)
        if erro:
            return falhar(comando, erro)
    cliente = ClienteOpenAlex(sessao=criar_sessao())

    if listar is not None:
        return cmd_listar(args, cliente, filtro, busca)

    if args.contar:
        try:
            n = cliente.contar(filtro=filtro, busca=busca)
        except ErroOpenAlex as e:
            return falhar(comando, dica_erro(e, args.query, args.campo))
        estado.resumo({"comando": comando, "ok": True, "contar": True, "n": n, "filtro": filtro, "search": busca,
                       "mailto": bool(cliente.email), "api_key": bool(cliente.api_key)})
        return 0

    try:
        raiz = estado.exigir_projeto(args.dir)
    except estado.ErroProjeto as e:
        return falhar(comando, str(e))

    arq_jsonl = f"01-busca/brutos/{args.busca_id}_openalex.jsonl"
    arq_consulta = f"01-busca/brutos/{args.busca_id}_openalex.consulta.json"
    consulta = {"endpoint": f"{URL_BASE}/works", "filter": filtro, "search": busca, "campo": args.campo,
                "query": args.query, "filtro_extra": args.filtro, "select": CAMPOS_SELECT,
                "per_page": args.por_pagina, "max_paginas": args.max_paginas}
    anterior = busca_registrada(raiz, args.busca_id)
    if anterior is not None and not _buscas.busca_ativa(anterior):
        return falhar(comando, _buscas.descrever_inativa(estado.carregar_estado(raiz), args.busca_id))
    if substituir or motivo:
        # mesma validação do `rs.py importar --substituir`, antes de qualquer chamada à API
        from .importar import cli as _cli_importar
        try:
            _cli_importar.checar_substituicao(raiz, args.busca_id, substituir, motivo)
        except ErroImportacao as e:
            return falhar(comando, str(e))
    reexecucao = (raiz / arq_jsonl).exists()
    if reexecucao:
        consulta_antiga = {}
        if (raiz / arq_consulta).exists():
            consulta_antiga = json.loads((raiz / arq_consulta).read_text(encoding="utf-8"))
        if (consulta_antiga.get("filter"), consulta_antiga.get("search")) != (filtro, busca):
            return falhar(comando, f"a busca {args.busca_id} já foi executada com outra consulta; "
                                   "buscas são imutáveis: use um novo --busca-id")
        obras = ler_jsonl(raiz / arq_jsonl)
        n_api = consulta_antiga.get("n_api")
        truncada = bool(consulta_antiga.get("truncada"))
    else:
        obras, n_api = [], None
        vistos = set()
        try:
            for meta, pagina in cliente.paginar(filtro=filtro, busca=busca, por_pagina=args.por_pagina,
                                                max_paginas=args.max_paginas):
                if n_api is None:
                    n_api = int(meta.get("count") or 0)
                for obra in pagina:
                    wid = id_curto(obra.get("id"))
                    if wid and wid not in vistos:  # a API pode repetir obra entre páginas
                        vistos.add(wid)
                        obras.append(obra)
        except ErroOpenAlex as e:
            mensagem = dica_erro(e, args.query, args.campo)
            estado.registrar_evento(raiz, "erro", "04_busca", "script", ATOR,
                                    dados={"busca_id": args.busca_id, "erro": mensagem, "n_parcial": len(obras)})
            return falhar(comando, f"{mensagem} (nada foi gravado; rode de novo)")
        truncada = n_api is not None and len(obras) < n_api
        consulta.update({"executada_em": estado.agora(), "n_api": n_api, "n_obtido": len(obras),
                         "truncada": truncada, "mailto_usado": bool(cliente.email)})
        escrever_jsonl(raiz / arq_jsonl, obras)
        escrever_texto(raiz / arq_consulta, json.dumps(consulta, ensure_ascii=False, indent=2) + "\n")

    try:
        imp = importar_jsonl(raiz, arq_jsonl, args.busca_id, "base", args.estrutura or "",
                             usar_importador=not args.sem_importador)
    except ValueError as e:
        return falhar(comando, str(e))

    sha = estado.sha256_arquivo(raiz / arq_jsonl)
    registro = {
        "id": args.busca_id, "fonte": "openalex", "string_id": args.string_id,
        "executada_em": (json.loads((raiz / arq_consulta).read_text(encoding="utf-8")).get("executada_em")),
        "n_bruto": len(obras), "filtros_na_base": args.filtro or None, "arquivo": arq_jsonl, "sha256": sha,
        "importada": True, "query": args.query, "campo": args.campo, "n_api": n_api, "truncada": truncada,
    }
    ev_anterior = evento_busca_registrada(raiz, args.busca_id, arq_jsonl, sha) \
        if anterior is not None and anterior.get("sha256") == sha else None
    est = registrar_busca(raiz, registro)
    if ev_anterior is None:
        ev_busca = estado.registrar_evento(raiz, "busca_registrada", "04_busca", "script", ATOR,
                                           dados={k: registro[k] for k in ("id", "fonte", "string_id", "n_bruto",
                                                                           "n_api", "truncada", "campo", "query")},
                                           artefatos=[arq_jsonl, arq_consulta], estado=est)
    else:
        ev_busca = ev_anterior
    # O resumo do importador interno diz busca_registrada=false (ele não recebeu metadados PRISMA-S); o valor que
    # vale é o deste comando, que gravou (ou já tinha gravado) o evento busca_registrada.
    if isinstance(imp.get("resumo_importador"), dict):
        imp["resumo_importador"]["busca_registrada"] = True
    avisos = []
    substituicao = None
    if substituir:
        from .importar import cli as _cli_importar
        try:
            substituicao = _cli_importar.aplicar_substituicao(raiz, args.busca_id, substituir, motivo, avisos)
        except ErroImportacao as e:
            return falhar(comando, str(e))
    if truncada:
        avisos.append(f"busca truncada: {len(obras)} de {n_api} obras (--max-paginas); não serve para o PRISMA")
    if not cliente.email and not reexecucao:
        avisos.append("RS_EMAIL não definido: a API atende mais devagar fora da fila educada")
    estado.resumo({"comando": comando, "ok": True, "busca_id": args.busca_id, "n_api": n_api, "n_bruto": len(obras),
                   "reexecucao": reexecucao, "busca_registrada": True, "evento_busca_registrada_seq": ev_busca["seq"],
                   "busca_registrada_agora": ev_anterior is None, "substituicao": substituicao,
                   "importacao": imp, "arquivos": [arq_jsonl, arq_consulta],
                   "avisos": avisos, "proximo_passo": "rs.py dedup"})
    return 0


def registrar(subparsers):
    p = subparsers.add_parser("buscar", help="busca em APIs bibliográficas (OpenAlex)")
    sub = p.add_subparsers(dest="fonte_busca", metavar="<fonte>")
    q = sub.add_parser("openalex", help="busca paginada no OpenAlex, grava JSONL bruto e importa")
    q.add_argument("--busca-id", help="id da busca no log (ex.: B05); mesma regra do `rs.py importar`")
    q.add_argument("--query", default="", help="string booleana (aspas, OR, AND, NOT)")
    q.add_argument("--filtro", default=None, help='filtros extras da API, ex.: "publication_year:2000-2025,type:article"')
    q.add_argument("--campo", choices=CAMPOS_BUSCA, default="title_and_abstract",
                   help="onde procurar a string (padrão: título e resumo, com stemming e sem curinga); "
                        "*.search.exact = sem stemming, aceita curinga (*) e frase exata")
    q.add_argument("--string-id", default=None, help="versão da string no protocolo (ex.: S-oa-v1)")
    q.add_argument("--estrutura", default="", help="bloco/estratégia registrada na coluna estrutura")
    q.add_argument("--por-pagina", type=int, default=POR_PAGINA)
    q.add_argument("--max-paginas", type=int, default=None, help="só para testes de string; marca a busca como truncada")
    q.add_argument("--contar", action="store_true", help="só conta os resultados, sem gravar")
    q.add_argument("--listar", type=int, default=None, metavar="N",
                   help="grava as N primeiras obras em 00-protocolo/exploracao_<busca_id>.csv, sem importar "
                        "nem registrar busca (com ou sem projeto)")
    q.add_argument("--sem-importador", action="store_true", help="usar a conversão interna em vez de `rs.py importar`")
    q.add_argument("--substituir", default=None, metavar="BUSCA_ID_ANTIGA",
                   help="marca a busca antiga como inativa (ativa=false) sem apagar suas linhas, como em "
                        "`rs.py importar --substituir`; exige --motivo")
    q.add_argument("--motivo", default=None, help="obrigatório com --substituir (vai para o log)")
    q.set_defaults(func=cmd_buscar_openalex)
    p.set_defaults(func=lambda a, _p=p: (_p.print_help(), 1)[1])
