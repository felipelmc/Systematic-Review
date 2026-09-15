"""rs.py importar — converte uma exportação bibliográfica para dados/registros.csv.

USO
    rs.py importar --arquivo savedrecs.txt --busca-id B01
    rs.py importar --arquivo scopus.csv --busca-id B02 --estrutura PICOC
    rs.py importar --arquivo PoPCites.csv --busca-id CZ1              # método 'cinzenta' inferido do prefixo
    rs.py importar --arquivo planilha.xlsx --busca-id MN1 --mapa mapa.json
    rs.py importar --arquivo wos_scielo.txt --busca-id B03 --fonte scielo
    rs.py importar --arquivo desconhecido.csv --simular               # só detecta e mostra amostra, sem projeto

    # metadados PRISMA-S de uma exportação manual (gravados em estado["buscas"] e no evento busca_registrada)
    rs.py importar --arquivo scopus.csv --busca-id B02 --string-id S-scopus-v2 --executada-em 2025-03-20 \
        --n-base 812 --filtros-na-base "DOCTYPE(ar) AND PUBYEAR > 1999" --plataforma "Scopus (Elsevier)"

    # nova versão da string depois do teste de âncoras: a busca antiga fica inativa, sem apagar linhas
    rs.py importar --arquivo scopus_v3.csv --busca-id B06 --substituir B02 --motivo "âncora A07 perdida na v2"

    # uso programático (ex.: `rs.py buscar openalex` após gravar o JSONL bruto)
    from rslib.importar.cli import importar_arquivo
    resumo = importar_arquivo(raiz, "01-busca/brutos/B05.jsonl", "B05", fonte="openalex")

O que faz, nesta ordem:
1. Detecta o formato por assinatura (detectar.py) ou usa --fonte/--mapa.
2. Converte cada registro para esquema.COLUNAS_REGISTROS com a mesma
   normalização para todas as fontes (generico.montar_registro).
3. Guarda o arquivo bruto em 01-busca/brutos/ (se ainda não estiver lá). Os
   brutos são imutáveis: um arquivo diferente com o mesmo nome ganha sufixo com
   o hash, e um bruto alterado depois de importado é recusado.
4. Acrescenta as linhas a dados/registros.csv com id_registro
   "<busca_id>-<n:05d>", contínuo dentro da busca (uma busca pode ter vários
   arquivos, ex.: WoS exporta 1.000 registros por arquivo). Escrita atômica.
5. Flags da fonte que não cabem nas colunas (hoje: `is_retracted` do OpenAlex ->
   `retratado`) vão para dados/registros_flags.csv (importar/flags.py).
6. Atualiza estado["buscas"] e registra o evento `importacao` com os artefatos.
7. Com metadados PRISMA-S, grava-os na busca e registra `busca_registrada`; com
   --substituir, desativa a busca antiga e registra `busca_substituida`.

METADADOS PRISMA-S (itens 1, 8, 9, 13 e 15)
    --string-id (versão da string, ex.: S-scopus-v2; se existir
    01-busca/strings/<string_id>.txt ele entra como artefato do evento),
    --executada-em AAAA-MM-DD (data em que a busca rodou na base), --n-base (número
    de resultados que a base informou; comparado com o total importado),
    --filtros-na-base (limites aplicados na interface) e --plataforma. Buscas são
    imutáveis: um campo já registrado com outro valor é recusado (exit 1). A única
    exceção é `executada_em` lido do próprio arquivo (data de exportação do WoS/PoP),
    que a data declarada substitui com aviso. Repetir a importação do mesmo arquivo
    só com os metadados completa a busca sem acrescentar linhas.

    Buscas criadas por `rs.py buscar openalex` (têm `n_api` no estado): o número que a
    base informou é o `n_api` (meta.count da API), e `n_bruto` é o número de obras
    baixadas (menor que n_api numa busca truncada por --max-paginas). Nelas, --n-base é
    conferido com `n_api`: igual, é aceito sem gravar nada; diferente, é recusado com a
    explicação (não se usa --n-base para "corrigir" o total da API; uma nova execução
    se registra com `buscar openalex --busca-id <novo> --substituir <antigo> --motivo`).

BUSCA SUBSTITUÍDA (--substituir <busca_id_antiga> --motivo "...")
    Para quando o teste de âncoras ou o PRESS obriga a corrigir uma string já
    importada. A busca antiga recebe `ativa: false` (esquema.CAMPO_BUSCA_ATIVA),
    `substituida_por`, `substituida_em` e `motivo_substituicao`; a nova recebe
    `substitui`. As linhas da antiga continuam em registros.csv (registro imutável e
    trilha de auditoria), mas `dedup` e `prisma` as ignoram, e `importar`,
    `buscar openalex` e `bola-de-neve` recusam a busca inativa. O motivo é
    obrigatório e vai para o log (evento `busca_substituida`). A substituição só é
    aplicada depois que a nova importação deu certo. Rode `rs.py dedup` em seguida.

Idempotência: o par (busca_id, arquivo bruto) identifica uma importação. Rodar
de novo com o mesmo arquivo não acrescenta linhas nem eventos. Se as linhas
existem mas o estado não sabe delas (queda entre gravar a tabela e o estado), o
estado e o evento são recompostos a partir da tabela (dados.recuperado=true).
O mesmo arquivo em outra busca é recusado (inflaria "identificados" no PRISMA),
salvo com --permitir-repetido.

`linha_origem` é a posição do registro no arquivo (1 = primeiro registro, sem
contar cabeçalho), inclusive quando registros vazios são descartados.

Códigos de saída: 0 ok; 1 erro de uso/dados; 3 dependência ausente (xlrd/openpyxl).
"""

import csv
import datetime as _dt
import io
import json
import os
import re
import shutil
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .. import esquema, estado
from . import buscas as _buscas
from . import capes_bdtd, detectar, generico, openalex, pop, scielo, scopus, wos, zotero_ris
from . import flags as _flags
from .detectar import ErroImportacao

DIR_BRUTOS = "01-busca/brutos"  # uma das esquema.PASTAS_PROJETO
METODOS = ["base", "citacao", "cinzenta", "manual"]
_METODO_POR_PREFIXO = _buscas.METODO_POR_PREFIXO
_RE_BUSCA = _buscas.RE_BUSCA_ID  # mesma regra usada por buscar openalex e bola-de-neve
ETAPA = "05_organizacao"
ETAPA_BUSCA = "04_busca"
ATOR = "rs.py importar"
CAMPOS_PRISMA_S = ("string_id", "executada_em", "n_bruto", "filtros_na_base", "plataforma")

_WOS = {"wos_txt", "wos_tsv", "wos_tabela", "wos_bib", "wos_xls"}
FORMATOS_ACEITOS = {
    "wos": _WOS,
    "scielo": _WOS | {"scielo_csv"},
    "scopus": {"scopus_csv", "ris"},
    "openalex": {"openalex_csv", "openalex_json"},
    "pop": {"pop_csv"},
    "zotero": {"zotero_csv", "ris", "bibtex"},
    "ris": {"ris"},
    "capes": {"capes_csv", "capesr"},
    "bdtd": {"bdtd_csv", "bdtd_json"},
    "generico": {"generico", "bibtex"},
}
_NAO_TABULARES = {"wos_txt", "wos_tsv", "wos_bib", "ris", "bibtex", "openalex_json", "bdtd_json", "json_desconhecido"}


def _ler_scopus(caminho, formato, forcada):
    if formato == "ris":
        return zotero_ris.ler_ris(caminho, fonte_forcada=forcada or "scopus")
    return scopus.ler(caminho, formato, forcada)


def _ler_generico(caminho, formato, forcada):
    if formato == "bibtex":
        return generico.ler_bibtex(caminho, fonte=forcada or "generico")
    return generico.ler(caminho, mapa=None, fonte=forcada)


LEITORES = {
    "wos": wos.ler,
    "scielo": scielo.ler,
    "scopus": _ler_scopus,
    "openalex": openalex.ler,
    "pop": pop.ler,
    "zotero": zotero_ris.ler_zotero,
    "ris": zotero_ris.ler_ris,
    "capes": capes_bdtd.ler_capes,
    "bdtd": capes_bdtd.ler_bdtd,
    "generico": _ler_generico,
}


@dataclass
class Conversao:
    deteccao: detectar.Deteccao
    familia: str
    registros: list
    n_lidos: int
    n_descartados: int
    avisos: list = field(default_factory=list)
    data_busca: str = None
    # linha_origem (str) -> [(flag, origem)], ex.: {"3": [("retratado", "openalex:is_retracted")]}
    flags: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Conversão (sem projeto)
# ---------------------------------------------------------------------------
def carregar_mapa(caminho):
    try:
        with open(caminho, encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise ErroImportacao(f"mapa não encontrado: {caminho}") from e
    except json.JSONDecodeError as e:
        raise ErroImportacao(f"mapa não é JSON válido ({caminho}): {e}") from e


def converter(caminho, fonte="auto", mapa=None):
    """Detecta, lê e normaliza um arquivo. Não toca em projeto nenhum."""
    caminho = Path(caminho)
    fonte = fonte or "auto"
    if fonte != "auto" and fonte not in detectar.FAMILIAS:
        raise ErroImportacao(f"--fonte desconhecida: {fonte}. Use auto ou {', '.join(detectar.FAMILIAS)}")
    det = detectar.detectar(caminho)
    forcada = None if fonte == "auto" else fonte

    if mapa is not None:
        if det.formato in _NAO_TABULARES:
            raise ErroImportacao(f"--mapa só vale para CSV/planilha; o arquivo foi detectado como {det.formato}")
        familia = forcada or "generico"
        leitura = generico.ler(caminho, mapa=mapa, fonte=forcada)
        det = detectar.Deteccao(familia, "generico", f"mapa de colunas (--mapa); assinatura detectada: {det.formato}")
    else:
        familia = forcada or det.familia
        if det.formato == "json_desconhecido":
            raise ErroImportacao("JSON sem assinatura conhecida (esperado OpenAlex ou BDTD); "
                                 "converta para CSV e use --mapa")
        if det.formato not in FORMATOS_ACEITOS[familia]:
            if familia == "generico" and det.formato not in _NAO_TABULARES:
                leitura = generico.ler(caminho, mapa=None, fonte="generico")
            else:
                raise ErroImportacao(f"--fonte {familia} não lê este arquivo: detectado {det.formato} "
                                     f"({det.motivo}). Rode sem --fonte ou use --mapa.")
        else:
            leitura = LEITORES[familia](caminho, det.formato, forcada)

    registros, descartados, flags = [], 0, {}
    for ordem, bruto in enumerate(leitura.registros, 1):
        reg = generico.montar_registro(bruto)
        if generico.registro_vazio(reg):
            descartados += 1
            continue
        reg["fonte"] = bruto.get("fonte") or familia
        reg["linha_origem"] = str(ordem)
        registros.append(reg)
        if bruto.get("_retratado"):
            flags[str(ordem)] = [(_flags.FLAG_RETRATADO, f"{reg['fonte']}:is_retracted")]
    avisos = list(leitura.avisos)
    if descartados:
        avisos.append(f"{descartados} linha(s) sem título, DOI nem id da fonte foram descartadas")
    if not registros:
        raise ErroImportacao(f"nenhum registro reconhecido em {caminho.name} (formato {det.formato})")
    return Conversao(det, familia, registros, len(leitura.registros), descartados, avisos, leitura.data_busca, flags)


# ---------------------------------------------------------------------------
# Projeto: brutos, registros.csv e estado
# ---------------------------------------------------------------------------
def _rel(raiz, caminho):
    return Path(os.path.relpath(Path(caminho).resolve(), Path(raiz).resolve())).as_posix()


def guardar_bruto(raiz, origem, sha):
    """Caminho relativo do bruto dentro de 01-busca/brutos/, copiando se preciso. Devolve (rel, copiado)."""
    raiz = Path(raiz).resolve()
    origem = Path(origem).resolve()
    brutos = raiz / DIR_BRUTOS
    brutos.mkdir(parents=True, exist_ok=True)
    if brutos in origem.parents:
        return _rel(raiz, origem), False
    tamanho = origem.stat().st_size
    for existente in sorted(p for p in brutos.rglob("*") if p.is_file()):
        if existente.stat().st_size == tamanho and estado.sha256_arquivo(existente) == sha:
            return _rel(raiz, existente), False
    alvo = brutos / origem.name
    if alvo.exists():
        alvo = brutos / f"{origem.stem}_{sha[:8]}{origem.suffix}"
    shutil.copy2(origem, alvo)
    return _rel(raiz, alvo), True


def ler_registros(raiz):
    """Linhas atuais de dados/registros.csv (lista de dicts); confere o cabeçalho."""
    caminho = Path(raiz) / esquema.ARQ_REGISTROS
    if not caminho.exists() or caminho.stat().st_size == 0:
        return []
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        leitor = csv.reader(f)
        cabecalho = next(leitor, None)
        if cabecalho != esquema.COLUNAS_REGISTROS:
            raise ErroImportacao(f"{esquema.ARQ_REGISTROS} com cabeçalho diferente de esquema.COLUNAS_REGISTROS; "
                                 "não foi alterado. Corrija ou mova o arquivo antes de importar.")
        return [dict(zip(cabecalho, linha)) for linha in leitor if linha]


def gravar_registros(raiz, novos):
    """Acrescenta linhas a registros.csv de forma atômica (cópia + novas linhas + rename).

    Via estado.escrever_atomico: o arquivo sai com permissão 0666 menos a umask (mkstemp criava 0600 e
    coautores de uma pasta compartilhada não liam registros.csv).
    """
    caminho = Path(raiz) / esquema.ARQ_REGISTROS
    buffer = io.StringIO()
    existe = caminho.exists() and caminho.stat().st_size > 0
    if existe:
        with open(caminho, encoding="utf-8", newline="") as entrada:
            conteudo = entrada.read()
        buffer.write(conteudo)
        if not conteudo.endswith("\n"):
            buffer.write("\n")
    escritor = csv.DictWriter(buffer, fieldnames=esquema.COLUNAS_REGISTROS, lineterminator="\n")
    if not existe:
        escritor.writeheader()
    escritor.writerows(novos)
    estado.escrever_atomico(caminho, buffer.getvalue(), newline="")


def _proximo_numero(linhas, busca_id):
    numeros = []
    for l in linhas:
        if l.get("busca_id") == busca_id:
            m = re.search(r"-(\d+)$", l.get("id_registro", ""))
            if m:
                numeros.append(int(m.group(1)))
    return max(numeros) + 1 if numeros else 1


def _busca_no_estado(est, busca_id):
    return next((b for b in est.get("buscas", []) if b.get("id") == busca_id), None)


# ---------------------------------------------------------------------------
# Metadados PRISMA-S e substituição de buscas
# ---------------------------------------------------------------------------
def normalizar_metadados(string_id=None, executada_em=None, n_base=None, filtros_na_base=None, plataforma=None,
                         hoje=None):
    """Valida os metadados declarados e devolve {campo_do_estado: valor} só com os informados."""
    meta = {}
    if string_id is not None:
        s = str(string_id).strip()
        if not s or re.search(r"\s", s):
            raise ErroImportacao(f"--string-id inválido: {string_id!r} (sem espaços; ex.: S-scopus-v2)")
        meta["string_id"] = s
    if executada_em is not None:
        s = str(executada_em).strip()
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
                raise ValueError(s)
            data = _dt.date.fromisoformat(s)
        except ValueError:
            raise ErroImportacao(f"--executada-em inválido: {executada_em!r} (use AAAA-MM-DD)") from None
        hoje = hoje or _dt.date.today()
        if data > hoje + _dt.timedelta(days=1):  # 1 dia de folga para fuso horário
            raise ErroImportacao(f"--executada-em {s} está no futuro")
        meta["executada_em"] = s
    if n_base is not None:
        if isinstance(n_base, bool) or not isinstance(n_base, int) or n_base < 0:
            raise ErroImportacao(f"--n-base inválido: {n_base!r} (inteiro >= 0 informado pela base)")
        meta["n_bruto"] = n_base
    for nome, valor, opcao in (("filtros_na_base", filtros_na_base, "--filtros-na-base"),
                               ("plataforma", plataforma, "--plataforma")):
        if valor is not None:
            s = str(valor).strip()
            if not s:
                raise ErroImportacao(f"{opcao} vazio")
            meta[nome] = s
    return meta


def busca_da_api_openalex(busca):
    """Busca gravada por `rs.py buscar openalex` (tem `n_api`, o total informado pela API)."""
    return isinstance(busca, dict) and "n_api" in busca


def _como_registrar_nova_execucao(busca, busca_id):
    if busca_da_api_openalex(busca):
        return (f"rode `rs.py buscar openalex --busca-id <novo id> --query ... --substituir {busca_id} "
                "--motivo \"...\"`")
    return f"importe a nova exportação com outro --busca-id e --substituir {busca_id} --motivo \"...\""


def _conciliar_n_base_openalex(busca, busca_id, meta, avisos):
    """Em buscas do `buscar openalex`, --n-base é conferido com n_api (total da API), não com n_bruto (baixadas).

    Tira `n_bruto` de `meta`. Igual a n_api: aceito sem gravar. n_api ausente: grava n_api. Diferente: recusa.
    Devolve o dict de conferência para o resumo (ou None se não se aplica).
    """
    if "n_bruto" not in meta or not busca_da_api_openalex(busca):
        return None
    n_base = meta.pop("n_bruto")
    n_api, n_bruto = busca.get("n_api"), busca.get("n_bruto")
    if n_api is None:
        meta["n_api"] = n_base
        return {"n_base": n_base, "n_api": None, "confere": None, "gravado_em": "n_api"}
    if n_api == n_base:
        avisos.append(f"busca {busca_id}: --n-base {n_base} confere com o total informado pela API do OpenAlex "
                      f"(n_api); nada a gravar")
        return {"n_base": n_base, "n_api": n_api, "confere": True}
    truncada = " (busca truncada por --max-paginas)" if busca.get("truncada") else ""
    raise ErroImportacao(
        f"busca {busca_id} foi executada por `rs.py buscar openalex`: a API informou n_api={n_api} resultados e "
        f"foram baixadas n_bruto={n_bruto} obras{truncada}. --n-base {n_base} difere de n_api. Nessas buscas o "
        "número da base já vem da API: rode sem --n-base (ou com --n-base igual a n_api). Se a base informou outro "
        f"total numa nova execução, registre-a como nova busca: {_como_registrar_nova_execucao(busca, busca_id)}")


def _checar_conflitos_metadados(busca, busca_id, meta):
    """Antes de gravar qualquer coisa: campo já registrado com outro valor é recusado."""
    for campo, valor in meta.items():
        atual = (busca or {}).get(campo)
        if atual in (None, "") or atual == valor:
            continue
        if campo == "executada_em" and busca.get("executada_em_origem") != "declarada":
            continue  # data lida do arquivo (ou gravada sem declaração): a declarada vale, com aviso
        raise ErroImportacao(
            f"busca {busca_id}: {campo} já registrado como {atual!r}, recebido {valor!r}. Buscas são imutáveis; "
            f"para registrar outra execução, {_como_registrar_nova_execucao(busca, busca_id)}")


def _aplicar_metadados(b, meta, avisos):
    """Grava os metadados na busca. Devolve a lista de campos que mudaram."""
    mudou = []
    for campo, valor in meta.items():
        atual = b.get(campo)
        if atual == valor:
            if campo == "executada_em" and b.get("executada_em_origem") != "declarada":
                b["executada_em_origem"] = "declarada"
            continue
        if atual not in (None, ""):
            avisos.append(f"busca {b['id']}: executada_em {atual} (lido do arquivo) substituído pela data "
                          f"declarada {valor}")
        b[campo] = valor
        if campo == "executada_em":
            b["executada_em_origem"] = "declarada"
        mudou.append(campo)
    return mudou


def _checar_n_bruto(b, avisos):
    declarado, n_total = b.get("n_bruto"), b.get("n_importado")
    if isinstance(declarado, int) and not isinstance(declarado, bool) and isinstance(n_total, int) \
            and declarado != n_total:
        avisos.append(f"busca {b['id']}: a base informou {declarado} resultados e há {n_total} importados; "
                      "confira se falta exportar algum arquivo")


def _checar_substituicao(est, linhas, busca_id, substituir, motivo):
    if substituir is None:
        if motivo:
            raise ErroImportacao("--motivo só vale junto com --substituir")
        return
    _buscas.validar_busca_id(substituir, "--substituir")
    if substituir == busca_id:
        raise ErroImportacao("--substituir aponta para a própria busca")
    if not (motivo or "").strip():
        raise ErroImportacao("--substituir exige --motivo (vai para o log e para o relato PRISMA-S)")
    antiga = _busca_no_estado(est, substituir)
    if antiga is None and not any(l.get("busca_id") == substituir for l in linhas):
        raise ErroImportacao(f"--substituir {substituir}: busca inexistente no estado e em {esquema.ARQ_REGISTROS}")
    if antiga is not None and not _buscas.busca_ativa(antiga) and antiga.get("substituida_por") != busca_id:
        raise ErroImportacao(f"--substituir {substituir}: {_buscas.descrever_inativa(est, substituir)}")


def _substituir_busca(raiz, est, busca_id, substituir, motivo, linhas_total, avisos):
    """Desativa a busca antiga (sem apagar linhas) e registra busca_substituida. None se já estava feito."""
    linhas_antigas = [l for l in linhas_total if l.get("busca_id") == substituir]
    antiga = _busca_no_estado(est, substituir)
    if antiga is None:  # projeto adotado: a busca só existe em registros.csv
        fontes = Counter(l.get("fonte") for l in linhas_antigas if l.get("fonte"))
        antiga = {"id": substituir, "fonte": fontes.most_common(1)[0][0] if fontes else "desconhecida",
                  "string_id": None, "executada_em": None, "n_bruto": None, "filtros_na_base": None,
                  "arquivo": None, "sha256": None, "importada": bool(linhas_antigas),
                  "n_importado": len(linhas_antigas)}
        est.setdefault("buscas", []).append(antiga)
    if not _buscas.busca_ativa(antiga):
        return None
    nova = _busca_no_estado(est, busca_id)
    motivo = motivo.strip()
    antiga.update({esquema.CAMPO_BUSCA_ATIVA: False, "substituida_por": busca_id,
                   "substituida_em": estado.agora(), "motivo_substituicao": motivo})
    nova[esquema.CAMPO_BUSCA_ATIVA] = True
    nova["substitui"] = sorted(set(nova.get("substitui") or []) | {substituir})
    if antiga.get("fonte") and nova.get("fonte") and antiga["fonte"] != nova["fonte"]:
        avisos.append(f"a busca substituída {substituir} era {antiga['fonte']} e a nova {busca_id} é {nova['fonte']}")
    dados = {"busca_id_antiga": substituir, "busca_id_nova": busca_id,
             "fonte_antiga": antiga.get("fonte"), "fonte_nova": nova.get("fonte"),
             "string_id_antiga": antiga.get("string_id"), "string_id_nova": nova.get("string_id"),
             "n_registros_antiga": len(linhas_antigas), "n_registros_nova": nova.get("n_importado"),
             "linhas_preservadas_em": esquema.ARQ_REGISTROS}
    estado.registrar_evento(raiz, "busca_substituida", ETAPA_BUSCA, "script", ATOR, dados=dados, motivo=motivo,
                            estado=est)
    if (Path(raiz) / esquema.ARQ_UNICOS).exists():
        avisos.append(f"rode `rs.py dedup` para tirar os registros de {substituir} do conjunto ativo")
    return dados


def checar_substituicao(raiz, busca_id, substituir, motivo):
    """Validação de `--substituir`/`--motivo` antes de gravar ou chamar API (usada também por `buscar openalex`)."""
    raiz = Path(raiz)
    _checar_substituicao(estado.carregar_estado(raiz), ler_registros(raiz), busca_id, substituir, motivo)


def aplicar_substituicao(raiz, busca_id, substituir, motivo, avisos):
    """Desativa `substituir` em favor de `busca_id` (já registrada no estado) com o evento busca_substituida.

    Mesma semântica de `importar --substituir`; devolve os dados do evento, ou {"ja_aplicada": True, ...}.
    """
    raiz = Path(raiz)
    est = estado.carregar_estado(raiz)
    if _busca_no_estado(est, busca_id) is None:
        raise ErroImportacao(f"--substituir: a busca nova {busca_id} ainda não está registrada no estado")
    dados = _substituir_busca(raiz, est, busca_id, substituir, motivo, ler_registros(raiz), avisos)
    if dados is None:
        return {"busca_id_antiga": substituir, "busca_id_nova": busca_id, "ja_aplicada": True}
    return dados


def _artefatos_string(raiz, string_id):
    if not string_id:
        return []
    return [f"01-busca/strings/{string_id}{ext}" for ext in (".txt", ".md")
            if (Path(raiz) / "01-busca" / "strings" / f"{string_id}{ext}").is_file()]


def _registrar_busca_declarada(raiz, est, b, mudou, rel):
    dados = {"id": b["id"], "fonte": b.get("fonte"), "metodo": b.get("metodo_identificacao"),
             **{c: b.get(c) for c in CAMPOS_PRISMA_S},
             "n_importado": b.get("n_importado"), "arquivo": rel, "campos_declarados": mudou, "origem": "importar"}
    if busca_da_api_openalex(b):
        dados["n_api"] = b.get("n_api")
    estado.registrar_evento(raiz, "busca_registrada", ETAPA_BUSCA, "script", ATOR, dados=dados,
                            artefatos=[rel] + _artefatos_string(raiz, b.get("string_id")), estado=est)


def _flags_por_id(conv, ids_por_linha):
    itens = []
    for linha, lista in sorted(conv.flags.items(), key=lambda kv: int(kv[0])):
        rid = ids_por_linha.get(linha)
        if rid:
            itens.extend({"id_registro": rid, "flag": flag, "origem": origem} for flag, origem in lista)
    return itens


def _atualizar_busca(est, busca_id, fonte, conv, rel, sha, n_arquivo, n_total, metodo, estrutura,
                     ids, ts, avisos, meta=None):
    buscas = est.setdefault("buscas", [])
    b = _busca_no_estado(est, busca_id)
    if b is None:
        b = {"id": busca_id, "fonte": fonte, "string_id": None, "executada_em": None, "n_bruto": None,
             "filtros_na_base": None, "arquivo": rel, "sha256": sha, "importada": True,
             esquema.CAMPO_BUSCA_ATIVA: True}
        buscas.append(b)
    else:
        if b.get("fonte") and b["fonte"] != fonte:
            avisos.append(f"busca {busca_id} registrada com fonte {b['fonte']}, mas o arquivo é {fonte}")
        b["fonte"] = b.get("fonte") or fonte
        if not b.get("arquivo"):
            b["arquivo"], b["sha256"] = rel, sha
        b["importada"] = True
    mudou = _aplicar_metadados(b, meta or {}, avisos)
    if not b.get("executada_em") and conv is not None and conv.data_busca:
        b["executada_em"] = conv.data_busca
        b["executada_em_origem"] = "arquivo"
    b["metodo_identificacao"] = metodo
    if estrutura:
        b["estrutura"] = estrutura
    b.setdefault("arquivos", []).append({
        "arquivo": rel, "sha256": sha, "formato": conv.deteccao.formato if conv else None,
        "n_registros": n_arquivo, "ids": f"{ids[0]}..{ids[-1]}" if ids else "", "importado_em": ts,
    })
    b["n_importado"] = n_total
    _checar_n_bruto(b, avisos)
    return b, mudou


def validar_busca_id(busca_id):
    _buscas.validar_busca_id(busca_id)


def metodo_padrao(busca_id):
    prefixo = re.match(r"^[A-Z]+", busca_id).group(0)
    return _METODO_POR_PREFIXO.get(prefixo, "base")


def importar_arquivo(raiz, arquivo, busca_id, fonte="auto", mapa=None, metodo=None, estrutura="",
                     permitir_repetido=False, metadados=None, substituir=None, motivo=None):
    """Importa um arquivo para o projeto em `raiz`. Devolve o dict de resumo (também usado no stdout).

    `metadados`: dict já validado por `normalizar_metadados` (string_id, executada_em, n_bruto,
    filtros_na_base, plataforma). `substituir`/`motivo`: desativa a busca antiga depois da importação.
    """
    raiz = Path(raiz).resolve()
    validar_busca_id(busca_id)
    if metodo is not None and metodo not in METODOS:
        raise ErroImportacao(f"--metodo inválido: {metodo}. Use {', '.join(METODOS)}")
    arquivo = Path(arquivo)
    if not arquivo.is_file():
        raise ErroImportacao(f"arquivo não encontrado: {arquivo}")
    meta = dict(metadados or {})
    estrutura = (estrutura or "").strip()
    sha = estado.sha256_arquivo(arquivo)
    est = estado.carregar_estado(raiz)
    busca = _busca_no_estado(est, busca_id)
    if busca is not None and not _buscas.busca_ativa(busca):
        raise ErroImportacao(_buscas.descrever_inativa(est, busca_id))
    avisos_meta = []
    conferencia_n_base = _conciliar_n_base_openalex(busca, busca_id, meta, avisos_meta)
    _checar_conflitos_metadados(busca, busca_id, meta)
    metodo = metodo or (busca or {}).get("metodo_identificacao") or metodo_padrao(busca_id)
    estrutura = estrutura or (busca or {}).get("estrutura") or ""

    linhas = ler_registros(raiz)
    _checar_substituicao(est, linhas, busca_id, substituir, motivo)
    conv = converter(arquivo, fonte=fonte, mapa=mapa)
    rel, _copiado = guardar_bruto(raiz, arquivo, sha)

    da_busca = [l for l in linhas if l.get("busca_id") == busca_id and l.get("arquivo_origem") == rel]
    outras = sorted({l["busca_id"] for l in linhas if l.get("arquivo_origem") == rel and l.get("busca_id") != busca_id})
    registrados = [a for a in (busca or {}).get("arquivos", []) if a.get("arquivo") == rel]
    avisos = list(conv.avisos) + avisos_meta
    base_resumo = {
        "comando": "importar", "ok": True, "busca_id": busca_id, "formato": conv.deteccao.formato,
        "deteccao": conv.deteccao.motivo, "arquivo": rel, "sha256": sha, "metodo": metodo,
        "estrutura": estrutura, "registros": esquema.ARQ_REGISTROS,
    }

    if registrados and all(a.get("sha256") != sha for a in registrados):
        raise ErroImportacao(f"{rel} mudou depois de importado na busca {busca_id} (sha256 diferente). "
                             "Brutos são imutáveis: salve a nova exportação com outro nome.")

    if da_busca:
        ids = [l["id_registro"] for l in da_busca]
        fontes = Counter(l["fonte"] for l in da_busca)
        resumo = dict(base_resumo, fonte=fontes.most_common(1)[0][0], n_lidos=conv.n_lidos,
                      n_importados=0, n_ja_existentes=len(da_busca), id_primeiro=ids[0], id_ultimo=ids[-1],
                      total_registros=len(linhas), reexecucao=True, avisos=avisos)
        ids_por_linha = {l.get("linha_origem"): l["id_registro"] for l in da_busca}
        flags_novas = _flags.acrescentar(raiz, _flags_por_id(conv, ids_por_linha))
        resumo["n_retratados"] = len(conv.flags)
        artefatos_imp = [esquema.ARQ_REGISTROS, rel] + ([_flags.ARQ_REGISTROS_FLAGS] if flags_novas else [])
        if registrados:
            # Reexecução: nada de dados novos, salvo flags que faltavam (projeto importado antes da tabela
            # de flags) e metadados PRISMA-S declarados agora.
            b = busca
            if flags_novas:
                estado.registrar_evento(raiz, "importacao", ETAPA, "script", ATOR, estado=est,
                                        dados=dict(_dados_evento(resumo, dict(fontes)), reexecucao=True,
                                                   flags_acrescentadas=len(flags_novas)),
                                        artefatos=artefatos_imp)
            mudou = _aplicar_metadados(b, meta, avisos)
            if meta:
                _checar_n_bruto(b, avisos)
        else:
            # Linhas gravadas sem estado/evento (queda no meio): recompõe sem duplicar linhas.
            n_total = sum(1 for l in linhas if l.get("busca_id") == busca_id)
            ts = da_busca[0].get("importado_em") or estado.agora()
            b, mudou = _atualizar_busca(est, busca_id, resumo["fonte"], conv, rel, sha, len(da_busca), n_total,
                                        metodo, estrutura, ids, ts, avisos, meta)
            estado.registrar_evento(
                raiz, "importacao", ETAPA, "script", ATOR, estado=est,
                dados=dict(_dados_evento(resumo, dict(fontes)), recuperado=True),
                artefatos=artefatos_imp,
            )
            resumo["recuperado"] = True
        linhas_total = linhas
    else:
        if outras and not permitir_repetido:
            raise ErroImportacao(f"{rel} já foi importado na(s) busca(s) {', '.join(outras)}. Importar de novo em "
                                 f"{busca_id} duplicaria registros identificados; use --permitir-repetido se for "
                                 "intencional.")

        ts = estado.agora()
        inicio = _proximo_numero(linhas, busca_id)
        novos = []
        for i, reg in enumerate(conv.registros):
            linha = {c: "" for c in esquema.COLUNAS_REGISTROS}
            linha.update(reg)
            linha.update({
                "id_registro": f"{busca_id}-{inicio + i:05d}",
                "busca_id": busca_id,
                "metodo_identificacao": metodo,
                "arquivo_origem": rel,
                "estrutura": estrutura,
                "importado_em": ts,
            })
            novos.append(linha)
        gravar_registros(raiz, novos)
        flags_itens = _flags_por_id(conv, {l["linha_origem"]: l["id_registro"] for l in novos})
        flags_novas = _flags.acrescentar(raiz, flags_itens)

        ids = [l["id_registro"] for l in novos]
        fontes = Counter(l["fonte"] for l in novos)
        fonte_busca = fontes.most_common(1)[0][0]
        n_total = sum(1 for l in linhas if l.get("busca_id") == busca_id) + len(novos)
        b, mudou = _atualizar_busca(est, busca_id, fonte_busca, conv, rel, sha, len(novos), n_total, metodo,
                                    estrutura, ids, ts, avisos, meta)
        resumo = dict(
            base_resumo, fonte=fonte_busca, fontes=dict(fontes), n_lidos=conv.n_lidos, n_importados=len(novos),
            n_descartados=conv.n_descartados,
            n_sem_resumo=sum(1 for l in novos if not l["resumo"]),
            n_resumo_truncado=sum(1 for l in novos if l["resumo_truncado"] == "1"),
            n_sem_doi=sum(1 for l in novos if not l["doi"]),
            n_retratados=len(flags_itens),
            id_primeiro=ids[0], id_ultimo=ids[-1], n_busca=n_total, total_registros=len(linhas) + len(novos),
            reexecucao=False, avisos=avisos,
        )
        dados_ev = _dados_evento(resumo, dict(fontes))
        if flags_itens:
            dados_ev["ids_retratados"] = sorted({i["id_registro"] for i in flags_itens
                                                 if i["flag"] == _flags.FLAG_RETRATADO})
        estado.registrar_evento(raiz, "importacao", ETAPA, "script", ATOR, estado=est, dados=dados_ev,
                                artefatos=[esquema.ARQ_REGISTROS, rel]
                                + ([_flags.ARQ_REGISTROS_FLAGS] if flags_novas else []))
        linhas_total = linhas + novos

    resumo["busca_registrada"] = False
    if mudou:
        _registrar_busca_declarada(raiz, est, b, mudou, rel)
        resumo["busca_registrada"] = True
        resumo["metadados_declarados"] = {c: b.get(c) for c in mudou}
    elif meta and b is not None and b.get("executada_em_origem") == "declarada":
        estado.salvar_estado(raiz, est)  # só marcou a origem da data (mesmo valor): estado é cache
    if conferencia_n_base is not None:
        resumo["n_base_openalex"] = conferencia_n_base
    resumo["substituicao"] = None
    if substituir:
        resumo["substituicao"] = _substituir_busca(raiz, est, busca_id, substituir, motivo, linhas_total, avisos)
        if resumo["substituicao"] is None:
            resumo["substituicao"] = {"busca_id_antiga": substituir, "busca_id_nova": busca_id, "ja_aplicada": True}
    return resumo


def _dados_evento(resumo, fontes):
    chaves = ["busca_id", "formato", "deteccao", "arquivo", "sha256", "metodo", "estrutura", "n_lidos",
              "n_importados", "n_descartados", "n_ja_existentes", "n_retratados", "id_primeiro", "id_ultimo",
              "avisos"]
    dados = {k: resumo[k] for k in chaves if k in resumo}
    dados["fontes"] = fontes
    return dados


# ---------------------------------------------------------------------------
# Linha de comando
# ---------------------------------------------------------------------------
def simular(arquivo, fonte="auto", mapa=None, n_amostra=3):
    conv = converter(arquivo, fonte=fonte, mapa=mapa)
    amostra = [{k: r[k] for k in ("titulo", "autores", "ano", "doi", "tipo_publicacao", "idioma", "fonte")}
               for r in conv.registros[:n_amostra]]
    return {
        "comando": "importar", "ok": True, "simulacao": True, "arquivo": str(arquivo),
        "familia": conv.familia, "formato": conv.deteccao.formato, "deteccao": conv.deteccao.motivo,
        "n_lidos": conv.n_lidos, "n_validos": len(conv.registros), "n_descartados": conv.n_descartados,
        "fontes": dict(Counter(r["fonte"] for r in conv.registros)),
        "n_sem_resumo": sum(1 for r in conv.registros if not r["resumo"]),
        "n_retratados": len(conv.flags),
        "amostra": amostra, "avisos": conv.avisos,
    }


def executar(args):
    try:
        mapa = carregar_mapa(args.mapa) if args.mapa else None
        if args.simular:
            resumo = simular(args.arquivo, fonte=args.fonte, mapa=mapa)
            print(f"Formato: {resumo['formato']} ({resumo['deteccao']}); {resumo['n_validos']} registros válidos "
                  f"de {resumo['n_lidos']} lidos. Nada foi gravado.")
            estado.resumo(resumo)
            return 0
        if not args.busca_id:
            raise ErroImportacao("--busca-id é obrigatório (ex.: B01); só --simular dispensa")
        meta = normalizar_metadados(
            string_id=getattr(args, "string_id", None), executada_em=getattr(args, "executada_em", None),
            n_base=getattr(args, "n_base", None), filtros_na_base=getattr(args, "filtros_na_base", None),
            plataforma=getattr(args, "plataforma", None))
        raiz = estado.exigir_projeto(args.dir)
        resumo = importar_arquivo(raiz, args.arquivo, args.busca_id, fonte=args.fonte, mapa=mapa,
                                  metodo=args.metodo, estrutura=args.estrutura,
                                  permitir_repetido=args.permitir_repetido, metadados=meta,
                                  substituir=getattr(args, "substituir", None), motivo=getattr(args, "motivo", None))
    except ErroImportacao as e:
        print(f"ERRO: {e}", file=sys.stderr)
        estado.resumo({"comando": "importar", "ok": False, "erro": str(e)})
        return e.codigo
    except estado.ErroProjeto as e:
        print(f"ERRO: {e}", file=sys.stderr)
        estado.resumo({"comando": "importar", "ok": False, "erro": str(e)})
        return 1

    if resumo.get("reexecucao") and not resumo.get("recuperado"):
        print(f"{resumo['arquivo']} já importado na busca {resumo['busca_id']} "
              f"({resumo['id_primeiro']}..{resumo['id_ultimo']}); nenhuma linha acrescentada.")
    else:
        print(f"Formato: {resumo['formato']} ({resumo['deteccao']})")
        print(f"Busca {resumo['busca_id']}: {resumo.get('n_importados', 0)} registros importados "
              f"({resumo['id_primeiro']}..{resumo['id_ultimo']}) de {resumo['arquivo']}")
    if resumo.get("busca_registrada"):
        print(f"Metadados PRISMA-S gravados na busca {resumo['busca_id']}: "
              + ", ".join(f"{k}={v}" for k, v in resumo["metadados_declarados"].items()))
    sub = resumo.get("substituicao")
    if sub and not sub.get("ja_aplicada"):
        print(f"Busca {sub['busca_id_antiga']} substituída por {sub['busca_id_nova']} "
              f"({sub['n_registros_antiga']} linhas preservadas em {esquema.ARQ_REGISTROS}, fora do conjunto ativo)")
    for aviso in resumo.get("avisos", []):
        print(f"AVISO: {aviso}")
    estado.resumo(resumo)
    return 0


def registrar(subparsers):
    p = subparsers.add_parser(
        "importar",
        help="importa exportação (WoS, Scopus, OpenAlex, SciELO, PoP/Scholar, Zotero, RIS, CAPES, BDTD, genérico)",
        description="Converte uma exportação para dados/registros.csv, guarda o bruto em 01-busca/brutos/ "
                    "e registra a busca e o evento de importação. Formato detectado por assinatura.",
    )
    p.add_argument("--arquivo", required=True, help="arquivo exportado da base")
    p.add_argument("--busca-id", default=None, help="id da busca: B01, B02... (bases), SN1 (bola de neve), CZ1 (cinzenta), MN1 (manual)")
    p.add_argument("--fonte", default="auto", choices=["auto", *detectar.FAMILIAS],
                   help="força a família do leitor (padrão: detecção automática)")
    p.add_argument("--mapa", default=None, help="JSON com mapeamento de colunas para o leitor genérico")
    p.add_argument("--metodo", default=None, choices=METODOS,
                   help="método de identificação (padrão: pelo prefixo do id; B -> base, SN -> citacao, CZ -> cinzenta, MN -> manual)")
    p.add_argument("--estrutura", default="", help="bloco/estratégia de busca (ex.: PICOC, CMMO)")
    p.add_argument("--permitir-repetido", action="store_true",
                   help="aceita importar em outra busca um arquivo já importado")
    p.add_argument("--simular", action="store_true", help="só detecta e converte, sem gravar (não exige projeto)")
    g = p.add_argument_group("metadados PRISMA-S (gravados em estado.buscas e no evento busca_registrada)")
    g.add_argument("--string-id", default=None, help="versão da string executada (ex.: S-scopus-v2)")
    g.add_argument("--executada-em", default=None, metavar="AAAA-MM-DD", help="data em que a busca rodou na base")
    g.add_argument("--n-base", type=int, default=None, metavar="N",
                   help="número de resultados informado pela base (comparado com o total importado; em buscas "
                        "criadas por `buscar openalex`, conferido com n_api, o total informado pela API)")
    g.add_argument("--filtros-na-base", default=None, help="limites/filtros aplicados na interface da base")
    g.add_argument("--plataforma", default=None, help="plataforma/interface (ex.: Web of Science Core Collection)")
    s = p.add_argument_group("substituição de busca")
    s.add_argument("--substituir", default=None, metavar="BUSCA_ID_ANTIGA",
                   help="marca a busca antiga como inativa (ativa=false) sem apagar suas linhas")
    s.add_argument("--motivo", default=None, help="obrigatório com --substituir (vai para o log)")
    p.set_defaults(func=executar)
    return p
