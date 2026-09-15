"""Teste ponta a ponta: uma revisão inteira pelo dispatcher real (`python3 rs.py ...` em processos novos).

Por que existe: cada módulo passa nos próprios testes, mas as costuras (nomes de colunas,
enums, caminhos, formato dos JSONs, eventos do log) só aparecem quando a saída de um
comando vira a entrada do seguinte. Aqui nada é chamado por dentro: cada passo roda
`rs.py` num processo novo, confere o código de saída e o resumo JSON da última linha do
stdout, e o que um humano, um subagente ou uma skill irmã faria é simulado escrevendo
os arquivos no formato que eles escrevem (respostas de lote, planilha codificada,
relatorio_pdfs.csv, master de fichas, CSVs do extrator de efeitos, certeza.csv).

Cenários
    test_fluxo_completo_checkpoints  a) init, G2 sem codebooks bloqueado, 3 exportações, G3 sem PRESS
                                     bloqueado, dedup, filtrar; b) triagem por lotes com divergência e lote
                                     inválido, fila humana, validação, G4; c) textos, inventário,
                                     elegibilidade, ligação de relatos (a lista não desfaz a versão do
                                     dedup), bola de neve com OpenAlex falso e re-triagem; d) efeitos, G7
                                     sem RoB bloqueado, `qualidade consolidar` (RoB 2 e ROBINS-I em dupla,
                                     desacordo resolvido por humano), R (efeitos, meta, swim, combinados)
                                     e caixa; e) PRISMA, declaração de IA, incluídos, .bib, status;
                                     g) replay do log.
    test_autopiloto_rascunho_e_pendencias  f) G1/G2 recusados sem humano, busca truncada do OpenAlex que
                                     bloqueia o G3 e é refeita pelo comando que o status sugere, PRESS
                                     como pendência, validação humana como pendência, marca de rascunho
                                     em PRISMA, caixa e declaração, e remoção da marca depois de fechar
                                     as pendências.
    test_variante_rapida_atalho_do_g4  h) variante rápida com `atalho_rapida` no G1: dupla humana em 20%,
                                     G4 bloqueado sem a segunda leitura dos excluídos, `validar
                                     segunda-leitura` e G4 aprovado pelo atalho, sem --forcar.

Sem rede (bola de neve usa RS_TESTE_OPENALEX_RESPOSTAS) e sem API. Partes em R são puladas sem
Rscript/metafor. Rodar só este arquivo: tests/e2e/rodar.sh.
"""

import csv
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import pytest

import dados_sinteticos as ds
from conftest import SCRIPTS, SKILL

pytestmark = pytest.mark.e2e

RS = SCRIPTS / "rs.py"
RSCRIPT = shutil.which("Rscript")
VARIAVEIS_PROIBIDAS = ("RS_EMAIL", "OPENALEX_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "RS_RSCRIPT",
                       "CLAUDE_SKILL_DIR", "CLAUDE_PROJECT_DIR")


@lru_cache(maxsize=None)
def r_com(*pacotes):
    if RSCRIPT is None:
        return False
    expr = "cat(all(vapply(c(" + ",".join(f'"{p}"' for p in pacotes) + "), requireNamespace, logical(1), quietly=TRUE)))"
    proc = subprocess.run([RSCRIPT, "-e", expr], capture_output=True, text=True, timeout=120)
    return proc.stdout.strip().endswith("TRUE")


# ---------------------------------------------------------------------------
# Projeto e dispatcher
# ---------------------------------------------------------------------------
class Projeto:
    def __init__(self, raiz, tmp):
        self.raiz = Path(raiz)
        self.tmp = Path(tmp)
        self.env = {k: v for k, v in os.environ.items() if k not in VARIAVEIS_PROIBIDAS}
        self.env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        self.historico = []

    def rs(self, *args, codigo=0):
        """Roda `python3 rs.py --dir <raiz> ...`; confere o código e devolve o resumo JSON da última linha."""
        argv = [sys.executable, str(RS), "--dir", str(self.raiz), *map(str, args)]
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=1800, env=self.env, cwd=self.tmp)
        linhas = [l for l in proc.stdout.splitlines() if l.strip()]
        contexto = f"rs.py {' '.join(map(str, args))}\n--- stdout ---\n{proc.stdout[-3000:]}\n--- stderr ---\n{proc.stderr[-3000:]}"
        assert linhas, "sem stdout\n" + contexto
        try:
            resumo = json.loads(linhas[-1])
        except json.JSONDecodeError:
            pytest.fail("última linha do stdout não é JSON\n" + contexto)
        assert proc.returncode == codigo, f"código {proc.returncode} (esperado {codigo})\n" + contexto
        self.historico.append((args, proc.returncode))
        return resumo

    def caminho(self, rel):
        return self.raiz / rel

    def ler_csv(self, rel):
        with open(self.caminho(rel), encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def escrever_csv(self, rel, colunas, linhas, bom=False):
        caminho = self.caminho(rel)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=colunas, extrasaction="ignore")
            w.writeheader()
            for l in linhas:
                w.writerow({c: l.get(c, "") for c in colunas})
        return caminho

    def ler_json(self, rel):
        return json.loads(self.caminho(rel).read_text(encoding="utf-8"))

    def log(self):
        with open(self.caminho("rs_log.jsonl"), encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    def eventos(self, nome):
        return [e for e in self.log() if e["evento"] == nome]

    def obras_por_id_rs(self, obras):
        """{k da obra: linha de registros_unicos} pelo id da fonte (UT, EID, W) — o teste conhece a verdade."""
        registros = self.ler_csv("dados/registros.csv")
        unicos = self.ler_csv("dados/registros_unicos.csv")
        dono = {rid: u for u in unicos for rid in u["ids_registro"].split("|")}
        saida = {}
        for o in obras:
            ids = set(ds.ids_fonte(o).values())
            rids = [r["id_registro"] for r in registros if r["id_fonte"] in ids]
            if rids:
                saida[o["k"]] = dono[rids[0]]
        return saida


# ---------------------------------------------------------------------------
# Simulações (subagentes, humanos e skills irmãs escrevem arquivos; só rs.py escreve o estado)
# ---------------------------------------------------------------------------
def decisao_revisor(o, revisor):
    """Decisão do subagente para a obra (verdade de referência + divergência plantada em W11)."""
    ta = o["ta"]
    if ta == "divergente":
        return ("incluir", None) if revisor == "A" else ("excluir", "C1")
    if ta.startswith("excluir"):
        return "excluir", ta.split("_")[1]
    return ta, None


def resposta_lote(lote, obra_de_id, revisor):
    decisoes = []
    for reg in lote["registros"]:
        o = obra_de_id[reg["id_rs"]]
        decisao, criterio = decisao_revisor(o, revisor)
        trecho = None if reg["sem_resumo"] and decisao == "incerto" else " ".join(reg["titulo"].split()[:5])
        decisoes.append({"id_rs": reg["id_rs"], "decisao": decisao, "criterio_falhou": criterio,
                         "justificativa": f"Revisor {revisor}: aplicado {criterio or 'todos os critérios'} ao título e resumo.",
                         "trecho": trecho})
    return {"lote_id": lote["lote_id"], "rodada": lote["rodada"], "revisor": lote["revisor"],
            "criterios_sha": lote["criterios_sha"], "decisoes": decisoes}


def escrever_respostas(proj, resumo_preparar, obra_de_id, revisor, estragar=None):
    """Um 'subagente' por lote pendente: lê o lote e escreve só o arquivo de resposta."""
    escritos = []
    for item in resumo_preparar["lotes_pendentes"]:
        lote = json.loads(Path(item["lote"]).read_text(encoding="utf-8"))
        resposta = resposta_lote(lote, obra_de_id, revisor)
        if estragar and lote["lote_id"] == estragar:
            resposta["decisoes"][0]["trecho"] = "trecho inventado que não está no resumo"
            resposta["decisoes"].pop()
        Path(item["resposta"]).write_text(json.dumps(resposta, ensure_ascii=False, indent=2), encoding="utf-8")
        escritos.append(lote["lote_id"])
    return escritos


def criar_pdf(caminho, paginas):
    pymupdf = pytest.importorskip("pymupdf")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for texto in paginas:
        doc.new_page().insert_textbox(pymupdf.Rect(50, 50, 550, 800), texto, fontsize=11)
    doc.save(str(caminho))
    doc.close()


def paginas_pdf(o):
    autores = "; ".join(f"{n} {s}" for s, n in o["autores"]) or o.get("grupo", "")
    efeitos = " ".join(e["evidencia"] + "." for e in ds.EFEITOS.get(o["k"], []))
    return [
        f"{o['titulo']}\n\n{autores}\n\nAbstract. {o['resumo'] or 'This study analyses administrative records.'} "
        "The program transferred cash to poor households conditional on school enrollment and attendance.",
        "Results. " + (efeitos or "We report descriptive statistics for the main outcomes of interest.")
        + " Estimates are robust to alternative specifications and to clustering standard errors by municipality.",
        "References. Fictional Author (2010). A fictional reference used only for testing purposes. "
        "Another Fictional Author (2012). Methods for program evaluation in fictional settings.",
    ]


def planilha_codificada(caminho, obra_de_id, discordancia):
    """Humanos (um ou dois) codificam às cegas a planilha xlsx da validação (mais consenso na discordância)."""
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(caminho)
    ws = wb["codificacao"]
    cab = [c.value for c in ws[1]]
    col = {nome: i + 1 for i, nome in enumerate(cab)}
    assert not {"decisao_ia", "justificativa", "trecho", "estrato", "peso"} & set(cab), cab  # planilha cega
    for linha in range(2, ws.max_row + 1):
        id_rs = ws.cell(row=linha, column=col["id_rs"]).value
        o = obra_de_id[id_rs]
        ref = {"divergente": "excluir"}.get(o["ta"], o["ta"].split("_")[0])
        h1 = h2 = ref
        if o["k"] == discordancia:
            h1, h2 = "incerto", ref
            ws.cell(row=linha, column=col["decisao_consenso"]).value = ref
        ws.cell(row=linha, column=col["decisao_h1"]).value = h1
        if "decisao_h2" in col:  # a segunda leitura dos excluídos pode ter um só codificador
            ws.cell(row=linha, column=col["decisao_h2"]).value = h2
    wb.save(caminho)


# ---------------------------------------------------------------------------
# Replay do log
# ---------------------------------------------------------------------------
def conferir_replay(proj):
    """Todo evento valida no schema; seq estritamente crescente; sha256 citados batem com os arquivos.

    Para cada artefato vale o evento MAIS RECENTE que o cita: arquivos que mudam (tabelas
    regravadas, planilha preenchida por humanos) precisam ser citados de novo por quem os
    muda. rs_log.jsonl citado (declaração de IA) é conferido contra o prefixo do log anterior
    ao evento, porque o hash é calculado antes de o próprio evento ser acrescentado.
    """
    schema = json.loads((SKILL / "assets" / "schemas" / "evento.schema.json").read_text(encoding="utf-8"))
    bruto = proj.caminho("rs_log.jsonl").read_bytes()
    linhas_bytes = [l for l in bruto.splitlines(keepends=True) if l.strip()]
    eventos = [json.loads(l) for l in linhas_bytes]
    try:
        import jsonschema
        validador = jsonschema.Draft202012Validator(schema)
        for ev in eventos:
            erros = [e.message for e in validador.iter_errors(ev)]
            assert not erros, (ev["seq"], ev["evento"], erros)
    except ImportError:  # validação manual mínima
        for ev in eventos:
            assert set(schema["required"]) <= set(ev) and set(ev) <= set(schema["properties"]), ev
            assert ev["evento"] in schema["properties"]["evento"]["enum"], ev
    seqs = [ev["seq"] for ev in eventos]
    assert all(b > a for a, b in zip(seqs, seqs[1:])), seqs
    assert seqs[0] == 1 and json.loads(proj.caminho("rs_estado.json").read_text())["ultimo_seq"] == seqs[-1]

    ultimo = {}
    for i, ev in enumerate(eventos):
        for art in ev.get("artefatos") or []:
            ultimo[art["caminho"]] = (i, ev, art)
    divergentes = []
    for caminho, (i, ev, art) in sorted(ultimo.items()):
        p = Path(caminho) if Path(caminho).is_absolute() else proj.raiz / caminho
        if caminho == "rs_log.jsonl":
            atual = hashlib.sha256(b"".join(linhas_bytes[:i])).hexdigest()
        elif p.is_file():
            atual = hashlib.sha256(p.read_bytes()).hexdigest()
        else:
            continue  # arquivo que não existe mais (ex.: resposta de lote movida para rejeitados/)
        if art["sha256"] != atual:
            divergentes.append(f"seq {ev['seq']} {ev['evento']}: {caminho}")
    assert not divergentes, "artefatos alterados sem evento que os cite:\n" + "\n".join(divergentes)
    return eventos


# ---------------------------------------------------------------------------
# Cenário principal (checkpoints)
# ---------------------------------------------------------------------------
def test_fluxo_completo_checkpoints(tmp_path):
    pytest.importorskip("pymupdf")
    pytest.importorskip("openpyxl")
    proj = Projeto(tmp_path / "revisao", tmp_path)

    # ===== a) init, protocolo, exportações, importação, dedup, funil ======================
    r = proj.rs("init", "--titulo", "Transferências condicionadas e participação escolar", "--tipo",
                "oqf_mista_sequencial", "--autonomia", "checkpoints", "--triagem", "subagentes")
    assert r["criado"] is True and r["modo"] == "checkpoints"
    assert proj.rs("init", "--titulo", "Transferências condicionadas e participação escolar")["ja_existia"] is True
    st = proj.rs("status")
    assert st["etapa_atual"] == "01_pergunta" and st["proxima_acao"]["portao"] == "G1" and st["inconsistencias"] == []

    proj.rs("portao", "G1", "--aprovar", "--por", "autopiloto", codigo=2)  # checkpoints: só humano
    proj.rs("portao", "G1", "--aprovar", "--por", "revisor_humano_1", "--criterios",
            json.dumps({"pergunta": "TCR aumentam a participação escolar?", "tipo_revisao": "oqf_mista_sequencial"}))
    (proj.caminho("00-protocolo/teoria_programa.md")).write_text("# Teoria do programa\n\nTCR -> custo de oportunidade.\n",
                                                                 encoding="utf-8")
    (proj.caminho("00-protocolo/protocolo.md")).write_text("# Protocolo\n\nCritérios C1-C3; RoB; plano de síntese.\n",
                                                           encoding="utf-8")
    g2 = proj.rs("portao", "G2", "--aprovar", "--por", "revisor_humano_1", codigo=2)  # sem codebooks
    detalhes = " | ".join(b["detalhe"] for b in g2["bloqueios"])
    assert {b["tipo"] for b in g2["bloqueios"]} == {"artefato"}
    assert "codebook v0 ausente" in detalhes and "codebook de elegibilidade ausente" in detalhes
    ds.escrever_codebooks(proj.caminho("00-protocolo"))
    g2 = proj.rs("portao", "G2", "--aprovar", "--por", "revisor_humano_1")
    assert {"00-protocolo/protocolo.md", "00-protocolo/codebook_v0_oqf.csv",
            "00-protocolo/codebook_elegibilidade.csv"} <= set(g2["congelados"])
    assert any("revisor metodológico" in a for a in g2["avisos"])

    exportacoes = ds.escrever_exportacoes(tmp_path / "exportacoes")
    n_por_base = {}
    for busca, base in (("B01", "wos"), ("B02", "scopus"), ("B03", "openalex")):
        r = proj.rs("importar", "--arquivo", exportacoes[base], "--busca-id", busca)
        assert r["fonte"] == base and r["reexecucao"] is False
        n_por_base[base] = r["n_importados"]
    assert n_por_base == {"wos": 10, "scopus": 11, "openalex": 9}
    r = proj.rs("importar", "--arquivo", exportacoes["wos"], "--busca-id", "B01")  # idempotente
    assert r["reexecucao"] is True and r["n_importados"] == 0
    assert len(proj.ler_csv("dados/registros.csv")) == 30
    g3 = proj.rs("portao", "G3", "--aprovar", "--por", "revisor_humano_1", "--criterios", '{"press": true}', codigo=2)
    assert [b["tipo"] for b in g3["bloqueios"]] == ["artefato"] and "PRESS não registrado" in g3["bloqueios"][0]["detalhe"]
    proj.caminho("01-busca/press_S1.md").write_text(ds.PRESS, encoding="utf-8")  # PRESS por humano que não fez a string
    g3 = proj.rs("portao", "G3", "--aprovar", "--por", "revisor_humano_1", "--criterios", '{"press": true}')
    assert g3["bloqueios"] == [] and any("recall_ancoras.json" in a for a in g3["avisos"])

    r = proj.rs("dedup")
    assert (r["n_registros"], r["n_unicos"], r["candidatos_pendentes"]) == (30, 21, 0)
    assert r["duplicatas_removidas_por_tipo"] == {"exato": 9}
    assert r["pares_por_decisao"].get("rejeitado") == 2 and r["pares_por_decisao"].get("ligado") == 2
    assert (r["n_versoes_ligadas"], r["n_estudos"]) == (1, 20)
    r = proj.rs("dedup")
    assert r["sem_mudancas"] is True and r["reexecucao"] is True and r["evento_registrado"] is False
    assert len(proj.eventos("dedup_executado")) == 1                     # reexecução não enche o log
    mapa = proj.obras_por_id_rs(ds.OBRAS)
    # preprint (W04) e publicado (W05): relatos distintos do mesmo estudo, nunca fundidos
    assert mapa["W04"]["id_rs"] != mapa["W05"]["id_rs"] and mapa["W05"]["tipo_duplicata"] == "exato"
    assert mapa["W04"]["id_estudo"] == mapa["W05"]["id_estudo"] == "ES" + min(mapa["W04"]["id_rs"], mapa["W05"]["id_rs"])[2:]
    assert "preprint" in mapa["W04"]["flags"] and "preprint" not in mapa["W05"]["flags"]
    assert mapa["W05"]["doi"] == "10.5555/jde.2021.005"
    assert mapa["W06"]["id_rs"] != mapa["W07"]["id_rs"]                   # Part I × Part II
    assert mapa["W08"]["id_rs"] != mapa["W09"]["id_rs"]                   # tese × artigo
    assert mapa["W08"]["tipo_publicacao"] == "tese"
    assert mapa["W03"]["tipo_duplicata"] == "exato" and "sem_resumo" in mapa["W10"]["flags"]
    assert all(u["id_estudo"] == "ES" + u["id_rs"][2:] for k, u in mapa.items() if k not in ("W04", "W05"))
    pares = {(p["id_a"], p["id_b"]): p for p in proj.ler_csv("01-busca/dedup_pares.csv")}
    assert {p["motivo"] for p in pares.values() if p["decisao"] == "rejeitado"} == \
        {"tese_artigo_nunca_funde", "marcador_parte_ou_numeral_diferente"}
    assert {p["regra"] for p in pares.values() if p["decisao"] == "ligado"} == {"versao"}
    assert {l["id_rs"] for l in proj.ler_csv("03-textos/ligacao_relatos.csv")} == {mapa["W04"]["id_rs"], mapa["W05"]["id_rs"]}
    obra_de_id = {u["id_rs"]: ds.POR_K[k] for k, u in mapa.items()}

    filtros = {"versao": "filtros_v1", "filtros": [
        {"nome": "ano", "tipo": "ano", "min": 2000},
        {"nome": "tipo", "tipo": "tipo", "recusar": ["editorial", "errata"]},
        {"nome": "idioma", "tipo": "idioma", "aceitar": ["pt", "en", "es"]},
        {"nome": "metodo", "tipo": "dicionario", "dicionario": "metodo_pt_en_es",
         "grupos": ["experimental", "quantitativo", "causalidade"]},
    ]}
    proj.caminho("01-busca/filtros_v1.json").write_text(json.dumps(filtros, indent=2), encoding="utf-8")
    proj.escrever_csv("01-busca/ancoras.csv", ["id", "doi", "titulo", "ano"], [
        {"id": "ANC1", "doi": "https://doi.org/10.5555/RCT.2015.001"},
        {"id": "ANC2", "titulo": "Cash transfers and enrollment in Colombian municipalities", "ano": "2019"},
        {"id": "ANC3", "titulo": "Um estudo-âncora que a busca não achou", "ano": "2020"}])
    excluir = dict(filtros, filtros=[dict(filtros["filtros"][0], modo="excluir")])
    proj.caminho("01-busca/filtros_excluir.json").write_text(json.dumps(excluir), encoding="utf-8")
    proj.rs("filtrar", "--config", "01-busca/filtros_excluir.json", codigo=2)  # excluir sem previsão no protocolo
    r = proj.rs("filtrar", "--config", "01-busca/filtros_v1.json", "--ancoras", "01-busca/ancoras.csv")
    assert (r["n_entrada"], r["n_saida"], r["n_excluidos"]) == (21, 21, 0)
    assert r["por_filtro"]["ano"]["etiqueta"] == 1 and r["por_filtro"]["tipo"]["etiqueta"] == 1
    assert r["por_filtro"]["idioma"]["etiqueta"] == 1
    assert r["ancoras"]["excluida"] == 0 and r["ancoras"]["nao_encontrada"] == 1
    assert sum(r["ancoras"][s] for s in ("mantida", "etiquetada")) == 2
    formal = proj.ler_csv("02-triagem/filtro_formal.csv")
    assert {l["resultado"] for l in formal} <= {"passa", "etiqueta", "sem_dado"}
    assert any(l["id_rs"] == mapa["W14"]["id_rs"] and l["filtro"] == "ano" and l["resultado"] == "etiqueta" for l in formal)

    # ===== b) triagem por lotes, fila humana, validação, G4 =================================
    proj.caminho("02-triagem/prompts/ta_v1.md").write_text(ds.CRITERIOS_TA, encoding="utf-8")
    base_triagem = ["--etapa", "ta", "--rodada", "ta_v1", "--criterios", "02-triagem/prompts/ta_v1.md", "--tamanho", "11"]
    prep = {rev: proj.rs("triagem", "preparar", *base_triagem, "--revisor", rev) for rev in ("A", "B")}
    assert prep["A"]["n_registros"] == 21 and prep["A"]["n_lotes"] == 2 and prep["B"]["n_lotes"] == 2
    assert proj.rs("triagem", "preparar", *base_triagem, "--revisor", "A")["reexecucao"] is True
    lote_sem_resumo = [json.loads(Path(l["lote"]).read_text()) for l in prep["A"]["lotes_pendentes"]]
    assert any(reg["sem_resumo"] for lote in lote_sem_resumo for reg in lote["registros"])
    assert all("autores" not in reg for lote in lote_sem_resumo for reg in lote["registros"])

    escrever_respostas(proj, prep["A"], obra_de_id, "A")
    r = proj.rs("triagem", "mesclar", "--rodada", "ta_v1", "--revisor", "A", "--modelo", "claude-subagente-teste")
    assert len(r["mesclados"]) == 2 and r["lotes_pendentes"] == []
    escrever_respostas(proj, prep["B"], obra_de_id, "B", estragar="lote_002")
    r = proj.rs("triagem", "mesclar", "--rodada", "ta_v1", "--revisor", "B", "--modelo", "claude-subagente-teste", codigo=1)
    assert [x["lote"] for x in r["rejeitados"]] == ["lote_002"] and len(r["mesclados"]) == 1
    erros = " ".join(r["rejeitados"][0]["erros"])
    assert "trecho não encontrado" in erros or "IDs faltando" in erros
    assert proj.eventos("lote_rejeitado") and not Path(prep["B"]["lotes_pendentes"][1]["resposta"]).exists()
    escrever_respostas(proj, {"lotes_pendentes": [l for l in prep["B"]["lotes_pendentes"] if "lote_002" in l["lote"]]},
                       obra_de_id, "B")  # novo subagente para o lote rejeitado
    r = proj.rs("triagem", "mesclar", "--rodada", "ta_v1", "--revisor", "B", "--modelo", "claude-subagente-teste")
    assert [x["lote"] for x in r["mesclados"]] == ["lote_002"] and r["lotes_pendentes"] == []

    r = proj.rs("triagem", "consolidar", "--rodada", "ta_v1")
    assert r["n"] == 21 and r["divergentes"] == 1 and r["fila_humana"] == 1 and r["pendencia"] is None
    assert r["contagens"] == {"incluir": 11, "incerto": 2, "excluir": 8}
    fila_rel = r["fila"]
    fila = proj.ler_csv(fila_rel)
    assert [l["id_rs"] for l in fila] == [mapa["W11"]["id_rs"]] and "A=incluir" in fila[0]["pareceres"]
    fila[0].update(decisao_humana="excluir", criterio_humano="C1", motivo_humano="transferência incondicional")
    proj.escrever_csv(fila_rel, list(fila[0].keys()), fila)
    r = proj.rs("triagem", "override", "--fila", fila_rel, "--por", "revisor_humano_1")
    assert r["registrados"] == 1
    r = proj.rs("triagem", "consolidar", "--rodada", "ta_v1")
    assert r["fila_humana"] == 0 and r["contagens"] == {"incluir": 11, "incerto": 1, "excluir": 9}
    final = {l["id_rs"]: l for l in proj.ler_csv("02-triagem/triagem_ta_final.csv")}
    assert final[mapa["W11"]["id_rs"]]["decidido_por"] == "humano"
    assert final[mapa["W10"]["id_rs"]]["decisao_final"] == "incerto"  # sem resumo nunca é excluído
    st = proj.rs("status")  # chamado com --dir: os comandos sugeridos também levam o --dir
    assert st["proxima_acao"]["comando"].startswith(f'$RS --dir "{proj.raiz}" validar amostrar')
    assert st["inconsistencias"] == []

    r = proj.rs("validar", "amostrar", "--etapa", "ta", "--rodada", "ta_v1", "--n", "21", "--semente", "11",
                "--enriquecer-incluidos", "60")
    assert r["n_amostra"] == 21 and r["pendencia"] is None
    planilha_codificada(proj.caminho(r["planilha"]), obra_de_id, discordancia="W16")
    v = proj.rs("validar", "calcular", "--planilha", r["planilha"], codigo=2)  # revisão pequena: IC do recall < 0,90
    assert v["sensibilidade"] == 1.0 and v["atende_limiares"] is False and v["n_falsos_negativos"] == 0
    assert v["kappa_humanos"] > 0.8 and v["sensibilidade_ic"][0] < 0.9
    assert v["especificidade"] == pytest.approx(8 / 9)
    g4 = proj.rs("portao", "G4", "--aprovar", "--por", "revisor_humano_1", codigo=2)
    assert {b["tipo"] for b in g4["bloqueios"]} == {"limiar"}
    g4 = proj.rs("portao", "G4", "--aprovar", "--por", "revisor_humano_1", "--forcar", "--motivo",
                 "revisão pequena: todos os incluídos na amostra; IC do recall relatado como limitação")
    assert g4["forcado"] is True and g4["congelados"] == ["02-triagem/prompts/ta_v1.md"]

    # ===== c) textos, elegibilidade, relatos, bola de neve ===================================
    r = proj.rs("textos", "para-baixar")
    assert r["n"] == 12
    para_baixar = proj.ler_csv("03-textos/para_baixar.csv")
    chave_de = {l["id_rs"]: l["chave"] for l in para_baixar}
    k_de_chave = {chave_de[mapa[k]["id_rs"]]: k for k in mapa if mapa[k]["id_rs"] in chave_de}
    relatorio = []
    for linha in para_baixar:
        o = ds.POR_K[k_de_chave[linha["chave"]]]
        base = {c: linha[c] for c in ("chave", "titulo", "autores", "ano", "doi")}
        if o["tc"] == "nao_recuperado":
            relatorio.append(dict(base, status="nao_encontrado", motivo="sem versão de acesso aberto encontrada"))
            continue
        pdf = proj.caminho(f"03-textos/pdfs/{linha['chave']}.pdf")
        criar_pdf(pdf, paginas_pdf(o))
        relatorio.append(dict(base, status="ja_existia" if o["k"] == "W03" else "ok", fonte="unpaywall",
                              url=f"https://example.org/{o['k']}.pdf", versao="publicada", arquivo=str(pdf)))
    proj.escrever_csv("03-textos/relatorio_pdfs.csv", ["chave", "titulo", "autores", "ano", "doi", "status", "fonte", "url",
                                                        "versao", "motivo", "arquivo"], relatorio, bom=True)
    proj.escrever_csv("03-textos/verificacao_conteudo.csv", ["chave", "titulo", "veredito", "cobertura_titulo",
                                                              "autor_encontrado"],
                      [dict(l, veredito="confere", cobertura_titulo="1.0", autor_encontrado="True")
                       for l in relatorio if l["status"] != "nao_encontrado"], bom=True)
    r = proj.rs("textos", "inventario")
    assert (r["n"], r["n_existe"], r["n_faltando"]) == (12, 11, 1)
    assert r["faltando"] == [chave_de[mapa["W20"]["id_rs"]]] and r["sem_texto"] == []

    master_eleg = []
    for linha in relatorio:
        if linha["status"] == "nao_encontrado":
            continue
        o = ds.POR_K[k_de_chave[linha["chave"]]]
        falha = o["tc"].split("_")[1] if o["tc"].startswith("excluir") else None
        ficha = {"ficha_id": linha["chave"], "citekey": linha["chave"], "n_fichas_do_texto": "1",
                 "desenho_resumo": o.get("desenho", "não informado"), "pdf_path": f"pdfs/{linha['chave']}.pdf",
                 "paginacao": "arquivo", "offset_pagina": "0", "agente_fichador": "fichador", "data_fichamento": "2026-09-10"}
        for crit in ("C1_intervencao", "C2_desenho", "C3_outcome"):
            nao = falha and crit.startswith(falha)
            ficha[crit] = "Não" if nao else "Sim"
            ficha[crit + "__evidencia"] = f"\"{o['titulo'][:40]}\" (p. {2 if nao else 1})"
        master_eleg.append(ficha)
    proj.escrever_csv("03-textos/fichamentos_elegibilidade_master.csv", list(master_eleg[0].keys()), master_eleg)
    proj.escrever_csv("03-textos/codebook_elegibilidade.csv", ["dimensao", "variavel", "descricao", "prompt", "tipo",
                                                                "aplicavel_se"],
                      [dict(zip(["dimensao", "variavel", "descricao", "prompt", "tipo", "aplicavel_se"], l))
                       for l in ds.CODEBOOK_ELEGIBILIDADE])
    r = proj.rs("textos", "elegibilidade", "consolidar", "--master", "03-textos/fichamentos_elegibilidade_master.csv",
                "--codebook", "03-textos/codebook_elegibilidade.csv")
    assert r["contagem"] == {"incluir": 8, "excluir": 3, "incerto": 0}
    assert r["motivos_exclusao"] == {"C2_desenho": 2, "C3_outcome": 1} and r["pendencia"] is None

    tese, artigo = mapa["W08"]["id_rs"], mapa["W09"]["id_rs"]
    preprint, publicado = mapa["W04"]["id_rs"], mapa["W05"]["id_rs"]
    # a lista traz só a tese × artigo: é acréscimo, e a ligação de versão feita pelo dedup continua
    proj.escrever_csv("03-textos/pares_relatos.csv", ["id_rs_a", "id_rs_b"], [{"id_rs_a": artigo, "id_rs_b": tese}])
    r = proj.rs("textos", "ligar-relatos", "--pares", "03-textos/pares_relatos.csv")
    assert r["n_grupos"] == 2 and r["n_relatos_ligados"] == 4 and r["n_estudos_total"] == 19
    assert (r["modo"], r["n_pares_versao_dedup"], r["n_pares_recebidos"]) == ("acrescimo", 1, 1)
    assert {l["id_rs"]: l["id_estudo"] for l in proj.ler_csv("dados/registros_unicos.csv")}[preprint] == \
        "ES" + min(preprint, publicado)[2:]
    estudo_ligado = "ES" + min(tese, artigo)[2:]
    estudo_versao = "ES" + min(preprint, publicado)[2:]

    obras_falsas = {ds.wid(k): ds.obra_openalex(ds.POR_K[k], referencias=[ds.wid("W12"), ds.wid("W22")] if k == "W01" else [])
                    for k in ("W01", "W04", "W08", "W18", "W12")}
    for k in ("W02", "W03", "W05", "W09"):  # sementes sem W id no corpus: resolvidas por DOI ou título + ano
        obras_falsas[f"W40000{ds.numero(k):05d}"] = dict(ds.obra_openalex(ds.POR_K[k]), id=f"https://openalex.org/W40000{ds.numero(k):05d}")
    for o in ds.NOVAS_BOLA_DE_NEVE:
        obras_falsas[ds.wid(o["k"])] = ds.obra_openalex(o)
    respostas = tmp_path / "openalex_falso.json"
    respostas.write_text(json.dumps({"obras": obras_falsas, "citacoes": {ds.wid("W01"): [ds.wid("W23")]}},
                                    ensure_ascii=False), encoding="utf-8")
    proj.env["RS_TESTE_OPENALEX_RESPOSTAS"] = str(respostas)
    r = proj.rs("bola-de-neve", "--direcao", "ambas", "--rodada", "SN1")
    del proj.env["RS_TESTE_OPENALEX_RESPOSTAS"]
    assert (r["n_sementes"], r["n_nao_resolvidas"]) == (8, 0)
    assert (r["n_encontrados"], r["n_ja_no_corpus"], r["n_gravados"]) == (3, 1, 2)
    sementes = {s["id_rs"]: s["metodo_resolucao"] for s in proj.ler_csv("01-busca/bola_de_neve/SN1_sementes.csv")}
    assert sementes[mapa["W01"]["id_rs"]] == "id_fonte" and sementes[mapa["W02"]["id_rs"]] == "doi"
    assert sementes[mapa["W03"]["id_rs"]] == "titulo_ano"
    registros_sn = [l for l in proj.ler_csv("dados/registros.csv") if l["busca_id"] == "SN1"]
    assert len(registros_sn) == 2 and {l["metodo_identificacao"] for l in registros_sn} == {"citacao"}

    r = proj.rs("dedup")
    assert (r["n_registros"], r["n_unicos"], r["candidatos_pendentes"]) == (32, 23, 0)
    mapa2 = proj.obras_por_id_rs(ds.OBRAS + ds.NOVAS_BOLA_DE_NEVE)
    assert all(mapa2[k]["id_rs"] == mapa[k]["id_rs"] for k in mapa)                  # ids estáveis
    assert mapa2["W08"]["id_estudo"] == mapa2["W09"]["id_estudo"] == estudo_ligado    # ligação sobrevive ao dedup
    assert mapa2["W04"]["id_estudo"] == mapa2["W05"]["id_estudo"] == estudo_versao
    novos = [mapa2[o["k"]]["id_rs"] for o in ds.NOVAS_BOLA_DE_NEVE]
    for o in ds.NOVAS_BOLA_DE_NEVE:
        obra_de_id[mapa2[o["k"]]["id_rs"]] = o
    proj.escrever_csv("02-triagem/ids_SN1.csv", ["id_rs"], [{"id_rs": i} for i in novos])
    for rev in ("A", "B"):  # re-triagem com a MESMA versão dos critérios
        p = proj.rs("triagem", "preparar", *base_triagem, "--revisor", rev, "--ids", "02-triagem/ids_SN1.csv")
        assert p["lotes_novos"] == 1 and p["registros_novos"] == 2
        escrever_respostas(proj, p, obra_de_id, rev)
        proj.rs("triagem", "mesclar", "--rodada", "ta_v1", "--revisor", rev, "--modelo", "claude-subagente-teste")
    r = proj.rs("triagem", "consolidar", "--rodada", "ta_v1")
    assert r["n"] == 23 and r["contagens"] == {"incluir": 11, "incerto": 1, "excluir": 11} and r["sem_decisao"] == 0
    proj.rs("portao", "G5", "--aprovar", "--por", "revisor_humano_1")

    # ===== d) efeitos, síntese em R, certeza e caixa ==========================================
    chaves = {k: mapa2[k]["chave"] for k in ds.EFEITOS}
    cab_extrator = ("id_efeito,ficha_id,chave,id_estudo,desenho,estimando,outcome,construto_outcome,direcao_desejada,modelo,"
                    "modelo_principal,subgrupo,tipo_estatistica,m1,sd1,n1,m2,sd2,n2,t,df,f,beta,se,sdy,or_,ci_lo,ci_hi,r,p,"
                    "n_total,cluster,icc,evidencia,pagina,verificado_humano").split(",")
    for k, linhas in ds.EFEITOS.items():
        proj.escrever_csv(f"05-decomposicao/efeitos/{chaves[k]}.csv", cab_extrator,
                          [dict(l, ficha_id=chaves[k], chave=chaves[k], construto_outcome=ds.CONSTRUTO) for l in linhas])
    g6 = proj.rs("portao", "G6", "--aprovar", "--por", "revisor_humano_1", codigo=2)  # CSVs soltos não são piloto
    assert "piloto de extração não consolidado" in g6["bloqueios"][0]["detalhe"]
    r = proj.rs("analise", "preparar-efeitos")
    assert (r["n_efeitos"], r["n_estudos"], r["n_avisos"]) == (5, 4, 0)
    proj.rs("portao", "G6", "--aprovar", "--por", "revisor_humano_1")  # extracao_consolidada registrada
    extraidos = proj.ler_csv("05-decomposicao/efeitos_extraidos.csv")
    assert {l["id_estudo"] for l in extraidos if l["chave"] == chaves["W09"]} == {estudo_ligado}
    r = proj.rs("analise", "verificar-efeitos")
    assert r["status_trecho"] == {"OK": 5} and r["erros_plausibilidade"] == [] and r["pode_seguir_g7"] is False
    for l in extraidos:  # humano confere 100% dos números na página do PDF
        l["verificado_humano"] = "sim"
    proj.escrever_csv("05-decomposicao/efeitos_extraidos.csv", list(extraidos[0].keys()), extraidos)
    r = proj.rs("analise", "verificar-efeitos")
    assert r["pode_seguir_g7"] is True and r["n_nao_aptos_g7"] == 0
    r = proj.rs("analise", "preparar-efeitos")  # reprocessar não apaga a verificação humana
    assert {l["verificado_humano"] for l in proj.ler_csv("05-decomposicao/efeitos_extraidos.csv")} == {"sim"}
    proj.rs("analise", "verificar-efeitos")

    g7 = proj.rs("portao", "G7", "--aprovar", "--por", "revisor_humano_1", codigo=2)  # efeitos ok, RoB não consolidado
    assert [b["tipo"] for b in g7["bloqueios"]] == ["artefato"] and "rob_consolidado" in g7["bloqueios"][0]["detalhe"]
    proj.escrever_csv("04-qualidade/resultados_avaliados.csv",
                      ["chave", "id_estudo", "construto_outcome", "resultado", "ferramenta", "classificador"],
                      [dict(chave=chaves[k], id_estudo=mapa2[k]["id_estudo"], construto_outcome=ds.CONSTRUTO,
                            resultado=ds.EFEITOS[k][0]["modelo"], ferramenta=ferr, classificador="b1")
                       for k, (ferr, _) in ds.ROB.items()])
    for ferramenta in ("rob2", "robins_i"):
        for avaliador in ("A", "B"):
            proj.escrever_csv(f"04-qualidade/rob_{ferramenta}_{avaliador}.csv", ds.COLUNAS_AVALIACAO_ROB,
                              ds.avaliacao_rob(ferramenta, avaliador, chaves))
    dupla = ["--avaliador-a", "revisor_humano_1", "--avaliador-b", "revisor_humano_2"]
    r = proj.rs("qualidade", "consolidar", "--ferramenta", "rob2", "--a", "04-qualidade/rob_rob2_A.csv",
                "--b", "04-qualidade/rob_rob2_B.csv", *dupla)
    assert (r["n_resultados"], r["n_desacordos"], r["n_pendentes"]) == (1, 0, 0)
    r = proj.rs("qualidade", "consolidar", "--ferramenta", "rob2", "--consenso", "04-qualidade/rob_rob2_consenso.csv")
    assert r["rob_geral"] == {"algumas_preocupacoes": 1} and r["n_validados_humano"] == 1
    g7 = proj.rs("portao", "G7", "--aprovar", "--por", "revisor_humano_1", codigo=2)  # falta a outra ferramenta
    detalhes = " | ".join(b["detalhe"] for b in g7["bloqueios"])
    assert "sem consolidação do RoB: robins_i" in detalhes and "3 resultados avaliados" in detalhes
    r = proj.rs("qualidade", "consolidar", "--ferramenta", "robins_i", "--a", "04-qualidade/rob_robins_i_A.csv",
                "--b", "04-qualidade/rob_robins_i_B.csv", *dupla)
    assert (r["n_resultados"], r["n_desacordos"], r["n_pendentes"], r["pendencia"]) == (3, 1, 1, None)
    consenso_rel = "04-qualidade/rob_robins_i_consenso.csv"
    r = proj.rs("qualidade", "consolidar", "--ferramenta", "robins_i", "--consenso", consenso_rel, codigo=2)
    rob_geral_rel = "04-qualidade/rob_geral.csv"
    assert r["n_problemas"] == 1 and not any(l["ferramenta"] == "robins_i" for l in proj.ler_csv(rob_geral_rel))
    g7 = proj.rs("portao", "G7", "--aprovar", "--por", "revisor_humano_1", codigo=2)
    assert any("robins_i: fase 1 feita" in b["detalhe"] for b in g7["bloqueios"])
    consenso = proj.ler_csv(consenso_rel)
    for linha in consenso:  # reunião de consenso: humano decide o desacordo de D1 (resolvido_por vem de --por)
        if not linha["julgamento_consenso"]:
            linha.update(julgamento_consenso="grave", justificativa="renda familiar não controlada: confundimento grave")
    proj.escrever_csv(consenso_rel, list(consenso[0].keys()), consenso)
    r = proj.rs("qualidade", "consolidar", "--ferramenta", "robins_i", "--consenso", consenso_rel, "--por", "revisor_humano_1")
    assert r["rob_geral"] == {"moderado": 2, "grave": 1} and r["n_resolvido_por_preenchido"] == 1
    geral = proj.ler_csv(rob_geral_rel)
    assert len(geral) == 4 and {l["validado_humano"] for l in geral} == {"1"}
    assert {l["chave"]: l["rob_geral"] for l in geral}[chaves["W03"]] == "grave"
    g7 = proj.rs("portao", "G7", "--aprovar", "--por", "revisor_humano_1")
    assert g7["bloqueios"] == [] and any("concordância da extração" in a for a in g7["avisos"])

    tem_r = r_com("jsonlite", "metafor")
    if tem_r:
        r = proj.rs("analise", "efeitos")
        assert r["resumo_r"]["n_calculados"] == 5 and r["resumo_r"]["n_invertidos"] == 2
        assert r["resumo_r"]["formulas_sem_mapa"] == [] and r["arquivos"] == ["06-analise/efeitos.csv"]
        r = proj.rs("analise", "meta")
        assert (r["resumo_r"]["n_meta_ajustadas"], r["resumo_r"]["n_k_insuficiente"]) == (1, 1)
        meta = proj.ler_json("06-analise/meta_resumo.json")
        grupos = {g["classe_desenho"]: g for g in meta["grupos"]}
        assert grupos["nao_randomizado"]["k_estudos"] == 3 and grupos["nao_randomizado"]["status"] == "meta_ajustada"
        assert grupos["nao_randomizado"]["n_descartados_nao_principais"] == 1
        assert grupos["randomizado"]["status"] == "k_insuficiente"
        assert grupos["nao_randomizado"]["resultado"]["ic_inf"] > 0
        proj.rs("analise", "swim")
        r = proj.rs("analise", "combinados")
        assert "06-analise/testes_combinados.json" in r["arquivos"]
    else:  # sem R: a caixa segue só com certeza.csv (degradação documentada)
        proj.rs("analise", "meta", codigo=3 if RSCRIPT is None else 1)

    proj.escrever_csv("06-analise/certeza.csv", ["familia_intervencao", "construto_outcome", "dimensao", "classe_desenho",
                                                  "certeza", "abordagem", "enunciado", "estudos", "justificativa"], [
        dict(familia_intervencao=ds.FAMILIA, construto_outcome=ds.CONSTRUTO, dimensao="efeito",
             classe_desenho="nao_randomizado", certeza="baixa", abordagem="GRADE",
             justificativa="não randomizados partem de certeza baixa"),
        dict(familia_intervencao=ds.FAMILIA, construto_outcome=ds.CONSTRUTO, dimensao="efeito",
             classe_desenho="randomizado", certeza="moderada", abordagem="GRADE", justificativa="um ECR; imprecisão"),
        dict(familia_intervencao=ds.FAMILIA, dimensao="implementacao", certeza="moderada", abordagem="CERQual",
             enunciado="Exige coordenação entre educação e assistência social",
             estudos=f"{chaves['W01']}|{chaves['W02']}"),
    ])
    proj.escrever_csv("05-decomposicao/fichamentos_master.csv",
                      ["ficha_id", "citekey", "familia_intervencao", "impl_componentes", "impl_multinivel",
                       "impl_infraestrutura", "impl_barreiras_fidelidade", "impl_tempo_longo", "mecanismo_id",
                       "moderador_id", "percepcao_id", "custo_id", "rob_geral"],
                      [dict(ficha_id=c, citekey=c, familia_intervencao=ds.FAMILIA, impl_componentes="Não",
                            impl_multinivel="Sim" if k in ("W01", "W02") else "Não", impl_infraestrutura="Não",
                            impl_barreiras_fidelidade="Não", impl_tempo_longo="Não", mecanismo_id="Não",
                            moderador_id="Não", percepcao_id="Não", custo_id="Não", rob_geral="moderado")
                       for k, c in chaves.items()])
    r = proj.rs("caixa", "--master", "05-decomposicao/fichamentos_master.csv", "--faixas", "pequena:0,moderada:0.2,grande:0.5")
    assert r["n_pendentes"] == 0 and r["rascunho"] is False and r["pendencia"] is None
    caixa = proj.ler_csv("06-analise/caixa_ferramentas.csv")
    assert all(l["fontes"].strip() and re.fullmatch(r"[0-9a-f]{64}", l["assinatura"]) for l in caixa)
    efeito = {l["classe_desenho"]: l for l in caixa if l["dimensao"] == "efeito"}
    assert set(efeito) == {"nao_randomizado", "randomizado"}
    assert efeito["randomizado"]["certeza"] == "moderada" and "certeza.csv:linha 3" in efeito["randomizado"]["fontes"]
    assert "certeza.csv:linha 2" in efeito["nao_randomizado"]["fontes"]
    if tem_r:
        nr, rct = efeito["nao_randomizado"], efeito["randomizado"]
        assert (nr["rotulo"], nr["regra_aplicada"], nr["forca"], nr["k"]) == ("Positivo", "positivo_ic", "fraca", "3")
        assert nr["familia_intervencao"] == ds.FAMILIA and nr["escala"] == "moderada"
        i_nr = next(i for i, g in enumerate(meta["grupos"]) if g["classe_desenho"] == "nao_randomizado")
        assert f"meta_resumo.json#grupos[{i_nr}]" in nr["fontes"] and "swim_resumo.json#grupos[" in nr["fontes"]
        assert (rct["rotulo"], rct["regra_aplicada"]) == ("Inconclusivo", "inconclusivo_sinal")
        assert "testes_combinados" not in " ".join(l["fontes"] for l in caixa)
    else:
        assert {l["rotulo"] for l in efeito.values()} == {"Inconclusivo"}
    impl = [l for l in caixa if l["dimensao"] == "implementacao"]
    assert [(l["rotulo"], l["status_rotulo"], l["pontos_implementacao"]) for l in impl] == [("Simples", "definido", "1")]
    assert ("custo", "Não reportado") in {(l["dimensao"], l["rotulo"]) for l in caixa}
    proj.rs("portao", "G8", "--aprovar", "--por", "revisor_humano_1")

    # ===== e) relato ==========================================================================
    g9 = proj.rs("portao", "G9", "--aprovar", "--por", "revisor_humano_1", codigo=2)  # sem PRISMA nem declaração
    assert {b["tipo"] for b in g9["bloqueios"]} == {"artefato"} and len(g9["bloqueios"]) == 2
    r = proj.rs("prisma")
    assert r["rascunho"] is False and r["incluidos"] == {"estudos": 6, "relatos": 8}
    assert r["tipo"] == "2020" and "07-relatorio/prisma.png" in r["arquivos"]  # PNG para DOCX sem rsvg-convert
    contagens = proj.ler_json("07-relatorio/prisma_contagens.json")
    assert all(i["ok"] is not False for i in contagens["invariantes"])
    b, o = contagens["bases"], contagens["outros_metodos"]
    assert b["identificados"]["bases"] == 30 and b["identificados"]["por_fonte"] == {"wos": 10, "scopus": 11, "openalex": 9}
    assert b["removidos_antes_triagem"]["duplicatas"] == 9 and b["removidos_antes_triagem"]["automacao"] == 0
    assert (b["a_triar"], b["triados"], b["excluidos_triagem"], b["buscados"]) == (21, 21, 9, 12)
    assert (b["nao_recuperados"], b["avaliados"], b["incluidos_relatos"]) == (1, 11, 8)
    assert b["excluidos_elegibilidade"] == {"total": 3, "motivos": {"C2_desenho": 2, "C3_outcome": 1}}
    assert o["identificados"]["busca_citacoes"] == 2 and (o["triados"], o["excluidos_triagem"], o["buscados"]) == (2, 2, 0)
    svg = proj.caminho("07-relatorio/prisma.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and "(n = 30)" in svg and "RASCUNHO" not in svg
    import xml.etree.ElementTree as ET
    ET.fromstring(svg)
    assert proj.caminho("07-relatorio/prisma.mermaid").read_text(encoding="utf-8").startswith("flowchart TD")
    assert len(proj.ler_csv("07-relatorio/checklist_prisma.csv")) >= 27
    assert proj.rs("prisma")["reexecucao"] is True

    r = proj.rs("declaracao-ia")
    declaracao = proj.caminho("07-relatorio/declaracao_uso_ia.md").read_text(encoding="utf-8")
    assert "claude-subagente-teste" in r["modelos"] and r["n_validacoes"] == 1
    assert "validações abaixo dos limiares" in declaracao and r["rascunho"] is True  # G4 forçado: segue declarado
    assert "revisão pequena" in declaracao and "02-triagem/prompts/ta_v1.md" in declaracao

    r = proj.rs("incluidos")
    incluidos = proj.ler_csv("07-relatorio/incluidos.csv")
    assert r["n_incluidos"] == 8 and r["fonte"] == "tc" and {l["chave"] for l in incluidos} >= set(chaves.values())
    r = proj.rs("bib")
    bib = proj.caminho("07-relatorio/references.bib").read_text(encoding="utf-8")
    assert r["n_entradas"] == 8 and r["via"] in ("gerar-bibtex", "fallback")
    assert not [a for a in r["avisos"] if "diferem" in a]
    assert sorted(re.findall(r"@\w+\{([^,]+),", bib)) == sorted(l["chave"] for l in incluidos)
    assert re.search(r"@phdthesis\{" + re.escape(mapa2["W08"]["chave"]) + ",", bib)
    proj.rs("portao", "G9", "--aprovar", "--por", "revisor_humano_1")

    st = proj.rs("status")
    assert st["inconsistencias"] == [], st["inconsistencias"]
    assert st["etapa_atual"] is None and st["pendencias"] == [] and st["proxima_acao"]["tipo"] == "fim"
    assert st["contagens"]["incluidos"] == {"estudos": 6, "relatos": 8}

    # ===== g) replay ==========================================================================
    eventos = conferir_replay(proj)
    nomes = {e["evento"] for e in eventos}
    assert {"projeto_criado", "importacao", "dedup_executado", "filtro_formal", "lote_preparado", "lote_mesclado",
            "lote_rejeitado", "decisao_override", "triagem_consolidada", "validacao_calculada", "portao",
            "textos_atualizados", "ligacao_relatos", "busca_registrada", "extracao_consolidada", "efeitos_verificados",
            "caixa_gerada", "prisma_gerado", "relatorio_gerado", "rob_consolidado", "fila_gerada"} <= nomes
    if tem_r:
        assert [e["dados"]["script"] for e in proj.eventos("analise_executada")] == \
            ["efeitos.R", "meta.R", "swim.R", "testes_combinados.R"]


# ---------------------------------------------------------------------------
# Autopiloto
# ---------------------------------------------------------------------------
def test_autopiloto_rascunho_e_pendencias(tmp_path):
    pytest.importorskip("openpyxl")
    proj = Projeto(tmp_path / "auto", tmp_path)
    marca = "RASCUNHO NÃO VALIDADO"
    proj.rs("init", "--titulo", "Revisão no autopiloto", "--tipo", "efetividade_swim", "--autonomia", "autopiloto", "--sem-r")
    for g in ("G1", "G2"):  # sempre humanos, mesmo no autopiloto
        r = proj.rs("portao", g, "--aprovar", "--por", "autopiloto", codigo=2)
        assert "exige aprovação humana" in r["detalhe"]
    proj.rs("portao", "G1", "--aprovar", "--por", "revisor_humano_1", "--criterios",
            json.dumps({"pergunta": "TCR aumentam a participação escolar?", "tipo_revisao": "efetividade_swim"}))
    proj.caminho("00-protocolo/protocolo.md").write_text("# Protocolo\n", encoding="utf-8")
    ds.escrever_codebooks(proj.caminho("00-protocolo"))
    proj.rs("portao", "G2", "--aprovar", "--por", "revisor_humano_1")

    # 40 obras: 38 relevantes, 2 fora do escopo (amostra de validação grande o bastante para o limiar)
    obras = []
    for i in range(1, 41):
        relevante = i <= 38
        titulo = (f"Conditional cash transfers and school attendance in region {i}" if relevante
                  else f"Microfinance and household savings in district {i}")
        resumo = (f"We evaluate a conditional cash transfer program and school attendance of children in region {i}."
                  if relevante else f"We study microfinance access and household savings in district {i}.")
        obras.append(ds.obra(f"W{100 + i}", titulo, [(f"Autor{i:02d}", "Ana")], 2000 + (i % 20), {"openalex"},
                             "incluir" if relevante else "excluir_C1", resumo, doi=f"10.5555/auto.{i:03d}"))
    arquivo = tmp_path / "openalex_auto.jsonl"
    ds.escrever_openalex(arquivo, obras)
    proj.rs("importar", "--arquivo", arquivo, "--busca-id", "B01")

    # Busca pela API do OpenAlex (falsa) que baixa menos obras do que a contagem informada: truncada.
    repetida = tmp_path / "openalex_repetida.json"
    repetida.write_text(json.dumps({"obras": {"W101": ds.obra_openalex(obras[0]), "W102": ds.obra_openalex(obras[0])}}),
                        encoding="utf-8")
    proj.env["RS_TESTE_OPENALEX_RESPOSTAS"] = str(repetida)
    r = proj.rs("buscar", "openalex", "--busca-id", "B02", "--query", "conditional cash transfer", "--string-id", "S-oa-v1")
    assert (r["n_api"], r["n_bruto"]) == (2, 1) and any("busca truncada" in a for a in r["avisos"])
    st = proj.rs("status")
    assert [a["busca"] for a in st["alertas"] if a["tipo"] == "busca_truncada"] == ["B02"] and st["rascunho"] is True
    g3 = proj.rs("portao", "G3", "--aprovar", "--por", "autopiloto", codigo=2)
    assert {b["tipo"] for b in g3["bloqueios"]} == {"limiar", "artefato"}  # busca truncada e PRESS ausente
    comando = st["proxima_acao"]["comando"]
    assert comando.startswith(f'$RS --dir "{proj.raiz}" buscar openalex --busca-id <novo busca_id> ')
    assert "--substituir B02" in comando and "importar" not in comando
    completa = tmp_path / "openalex_completa.json"
    completa.write_text(json.dumps({"obras": {ds.wid(o["k"]): ds.obra_openalex(o) for o in obras[:2]}}), encoding="utf-8")
    proj.env["RS_TESTE_OPENALEX_RESPOSTAS"] = str(completa)
    r = proj.rs(*shlex.split(comando.replace("<novo busca_id>", "B03"))[3:])  # o comando sugerido, sem "$RS --dir <raiz>"
    del proj.env["RS_TESTE_OPENALEX_RESPOSTAS"]
    assert r["substituicao"] and r["n_bruto"] == 2 and not any("truncada" in a for a in r["avisos"])
    st = proj.rs("status")
    assert not [a for a in st["alertas"] if a["tipo"] == "busca_truncada"]
    assert "pendencia abrir --tipo revisao_press" in st["proxima_acao"]["comando"]  # autopiloto: PRESS como pendência
    pendencia_press = proj.rs("pendencia", "abrir", "--tipo", "revisao_press", "--etapa", "04_busca", "--portao", "G3",
                              "--descricao", "PRESS de S-oa-v1 por revisor humano")["pendencia"]
    pendencia_g3 = proj.rs("portao", "G3", "--aprovar", "--por", "autopiloto")["pendencia_aberta"]
    assert pendencia_g3
    r = proj.rs("dedup")
    assert r["n_unicos"] == 40 and r["buscas_inativas"] == ["B02"]
    proj.caminho("01-busca/press_S-oa-v1.md").write_text(ds.PRESS, encoding="utf-8")
    for pid, motivo in ((pendencia_press, "PRESS registrado em 01-busca/press_S-oa-v1.md"),
                        (pendencia_g3, "revisor conferiu a busca completa e o PRESS")):
        assert proj.rs("pendencia", "fechar", pid, "--motivo", motivo, "--por", "revisor_humano_1")["fechada"] is True
    mapa = proj.obras_por_id_rs(obras)
    obra_de_id = {u["id_rs"]: next(o for o in obras if o["k"] == k) for k, u in mapa.items()}

    proj.caminho("02-triagem/prompts/ta_v1.md").write_text(ds.CRITERIOS_TA, encoding="utf-8")
    base = ["--etapa", "ta", "--rodada", "ta_v1", "--criterios", "02-triagem/prompts/ta_v1.md", "--tamanho", "20"]
    for rev in ("A", "B"):
        p = proj.rs("triagem", "preparar", *base, "--revisor", rev)
        escrever_respostas(proj, p, obra_de_id, rev)
        proj.rs("triagem", "mesclar", "--rodada", "ta_v1", "--revisor", rev, "--modelo", "claude-subagente-teste")
    r = proj.rs("triagem", "consolidar", "--rodada", "ta_v1")
    assert r["contagens"] == {"incluir": 38, "excluir": 2} and r["pendencia"] is None

    r = proj.rs("validar", "amostrar", "--etapa", "ta", "--rodada", "ta_v1", "--n", "40", "--semente", "3")
    pendencia_validacao = r["pendencia"]
    assert pendencia_validacao and r["n_amostra"] == 40
    abertas = proj.rs("pendencia", "listar")["pendencias"]
    assert [(p["id"], p["tipo"], p["portao"]) for p in abertas] == [(pendencia_validacao, "validacao_humana", "G4")]

    proj.escrever_csv("06-analise/certeza.csv", ["familia_intervencao", "construto_outcome", "dimensao", "certeza",
                                                  "abordagem", "enunciado"], [
        dict(familia_intervencao=ds.FAMILIA, construto_outcome=ds.CONSTRUTO, dimensao="efeito", certeza="baixa",
             abordagem="GRADE"),
        dict(familia_intervencao=ds.FAMILIA, dimensao="implementacao", certeza="moderada", abordagem="CERQual",
             enunciado="Implementação simples"),
    ])
    proj.escrever_csv("05-decomposicao/fichamentos_master.csv",
                      ["ficha_id", "citekey", "familia_intervencao", "impl_componentes", "impl_multinivel",
                       "impl_infraestrutura", "impl_barreiras_fidelidade", "impl_tempo_longo"],
                      [dict(ficha_id="X", citekey=mapa["W101"]["chave"], familia_intervencao=ds.FAMILIA,
                            impl_componentes="Não", impl_multinivel="Não", impl_infraestrutura="Não",
                            impl_barreiras_fidelidade="Não", impl_tempo_longo="Não")])

    def produtos(esperado_rascunho):
        r_prisma = proj.rs("prisma")
        r_caixa = proj.rs("caixa", "--master", "05-decomposicao/fichamentos_master.csv")
        r_decl = proj.rs("declaracao-ia")
        svg = proj.caminho("07-relatorio/prisma.svg").read_text(encoding="utf-8")
        mermaid = proj.caminho("07-relatorio/prisma.mermaid").read_text(encoding="utf-8")
        md_caixa = proj.caminho("06-analise/caixa_ferramentas.md").read_text(encoding="utf-8")
        md_decl = proj.caminho("07-relatorio/declaracao_uso_ia.md").read_text(encoding="utf-8")
        assert r_caixa["n_pendentes"] == 0
        for nome, resumo, texto in (("prisma.svg", r_prisma, svg), ("prisma.mermaid", r_prisma, mermaid),
                                    ("caixa", r_caixa, md_caixa), ("declaracao", r_decl, md_decl)):
            assert resumo["rascunho"] is esperado_rascunho, (nome, resumo)
            assert (marca in texto) is esperado_rascunho, nome

    produtos(esperado_rascunho=True)

    wb_path = proj.caminho(r["planilha"])
    planilha_codificada(wb_path, obra_de_id, discordancia=None)
    v = proj.rs("validar", "calcular", "--planilha", r["planilha"])
    assert v["atende_limiares"] is True and v["sensibilidade_ic"][0] >= 0.90
    assert pendencia_validacao not in [p["id"] for p in proj.rs("pendencia", "listar")["pendencias"]]
    g4 = proj.rs("portao", "G4", "--aprovar", "--por", "autopiloto")
    pendencia_portao = g4["pendencia_aberta"]
    assert pendencia_portao
    produtos(esperado_rascunho=True)  # aprovação automática do G4 ainda precisa de humano

    r = proj.rs("pendencia", "fechar", pendencia_portao, "--motivo", "revisor conferiu a validação e o G4",
                "--por", "revisor_humano_1")
    assert r["fechada"] is True and r["abertas_restantes"] == 0
    assert "$RS prisma" in r["regenerar"] and "$RS declaracao-ia" in r["regenerar"]
    proj.rs("pendencia", "fechar", pendencia_portao, "--motivo", "de novo", "--ator-tipo", "script", codigo=2)
    produtos(esperado_rascunho=False)

    st = proj.rs("status")
    assert st["pendencias"] == [] and st["rascunho"] is False
    conferir_replay(proj)


# ---------------------------------------------------------------------------
# Variante rápida: atalho da triagem no G4
# ---------------------------------------------------------------------------
def test_variante_rapida_atalho_do_g4(tmp_path):
    pytest.importorskip("openpyxl")
    proj = Projeto(tmp_path / "rapida", tmp_path)
    proj.rs("init", "--titulo", "Revisão rápida para o demandante", "--tipo", "efetividade_swim", "--variante", "rapida",
            "--autonomia", "checkpoints", "--sem-r")
    proj.rs("portao", "G1", "--aprovar", "--por", "revisor_humano_1", "--criterios", json.dumps({
        "pergunta": "TCR aumentam a participação escolar?", "tipo_revisao": "efetividade_swim", "variante": "rapida",
        "atalho_rapida": True, "atalhos": ["triagem com dupla humana em 20% e segunda leitura de todos os excluídos"]}))
    proj.caminho("00-protocolo/protocolo.md").write_text("# Protocolo da revisão rápida\n\nAtalho da triagem: dupla "
                                                         "humana em 20% e segunda leitura dos excluídos.\n", encoding="utf-8")
    ds.escrever_codebooks(proj.caminho("00-protocolo"))
    proj.rs("portao", "G2", "--aprovar", "--por", "revisor_humano_1")

    obras = []
    for i in range(1, 31):  # 24 relevantes, 6 fora do escopo
        relevante = i <= 24
        titulo = (f"Conditional cash transfers and school attendance in province {i}" if relevante
                  else f"Microfinance and household savings in county {i}")
        resumo = (f"We evaluate a conditional cash transfer program and school attendance in province {i}."
                  if relevante else f"We study microfinance access and household savings in county {i}.")
        obras.append(ds.obra(f"W{200 + i}", titulo, [(f"Autora{i:02d}", "Bia")], 2001 + (i % 20), {"openalex"},
                             "incluir" if relevante else "excluir_C1", resumo, doi=f"10.5555/rapida.{i:03d}"))
    arquivo = tmp_path / "openalex_rapida.jsonl"
    ds.escrever_openalex(arquivo, obras)
    proj.rs("importar", "--arquivo", arquivo, "--busca-id", "B01")
    assert proj.rs("dedup")["n_unicos"] == 30
    proj.caminho("01-busca/press_S1.md").write_text(ds.PRESS, encoding="utf-8")
    proj.rs("portao", "G3", "--aprovar", "--por", "revisor_humano_1")
    mapa = proj.obras_por_id_rs(obras)
    obra_de_id = {u["id_rs"]: next(o for o in obras if o["k"] == k) for k, u in mapa.items()}

    proj.caminho("02-triagem/prompts/ta_v1.md").write_text(ds.CRITERIOS_TA, encoding="utf-8")
    base = ["--etapa", "ta", "--rodada", "ta_v1", "--criterios", "02-triagem/prompts/ta_v1.md", "--tamanho", "15"]
    for rev in ("A", "B"):
        p = proj.rs("triagem", "preparar", *base, "--revisor", rev)
        escrever_respostas(proj, p, obra_de_id, rev)
        proj.rs("triagem", "mesclar", "--rodada", "ta_v1", "--revisor", rev, "--modelo", "claude-subagente-teste")
    assert proj.rs("triagem", "consolidar", "--rodada", "ta_v1")["contagens"] == {"incluir": 24, "excluir": 6}

    # dupla humana cega em 20% da rodada (6 de 30), com excluídos pela IA na amostra para o κ
    r = proj.rs("validar", "amostrar", "--etapa", "ta", "--rodada", "ta_v1", "--n", "4", "--elusao", "2", "--semente", "5",
                "--atalho-rapida")
    assert r["n_amostra"] >= 6
    planilha_codificada(proj.caminho(r["planilha"]), obra_de_id, discordancia=None)
    v = proj.rs("validar", "calcular", "--planilha", r["planilha"], codigo=2)  # falta reler todos os excluídos
    assert v["criterios_atalho_rapida"]["segunda_leitura_excluidos"]["atende"] is False
    assert v["criterios_atalho_rapida"]["fracao_dupla_humana"]["atende"] is True
    g4 = proj.rs("portao", "G4", "--aprovar", "--por", "revisor_humano_1", codigo=2)
    assert {b["tipo"] for b in g4["bloqueios"]} == {"validacao"}
    assert "segunda leitura" in " ".join(b["detalhe"] for b in g4["bloqueios"])
    st = proj.rs("status")
    assert "validar segunda-leitura" in st["proxima_acao"]["comando"] and st["proxima_acao"]["exige_humano"] is True

    # segunda leitura humana de todos os excluídos pela IA
    e = proj.rs("validar", "elusao", "--etapa", "ta", "--rodada", "ta_v1", "--n", "6", "--semente", "9")
    planilha_codificada(proj.caminho(e["planilha"]), obra_de_id, discordancia=None)
    s = proj.rs("validar", "segunda-leitura", "--rodada", "ta_v1", "--planilha", e["planilha"])
    assert s["segunda_leitura_excluidos"] is True
    v = proj.rs("validar", "calcular", "--planilha", r["planilha"])
    assert v["criterios_atalho_rapida"]["segunda_leitura_excluidos"]["atende"] is True
    g4 = proj.rs("portao", "G4", "--aprovar", "--por", "revisor_humano_1")
    assert g4["forcado"] is False and g4["bloqueios"] == []
    assert any("atalho da variante rápida" in a for a in g4["avisos"])
    conferir_replay(proj)
