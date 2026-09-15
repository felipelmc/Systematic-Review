# Evals da skill revisao-sistematica

Dois conjuntos, rodados com `claude -p` em pastas descartáveis:

- `gatilhos.json`: pedidos que devem acionar a skill (pt, en e um em es) e pedidos que devem ir a uma skill irmã ou a nenhuma skill, com o destino esperado e o critério de aprovação.
- `cenarios.md`: cinco percursos com critérios de aceitação conferidos pelo estado, pelo log e pela transcrição.

Os testes de código ficam em `dev/revisao-sistematica/tests/` (da raiz do repositório: `python3 -m pytest -q dev/revisao-sistematica/tests`); estes evals medem o comportamento do modelo com a skill.

## Antes de rodar

- A skill instalada em `~/.claude/skills/revisao-sistematica` como cópia de `skills/revisao-sistematica` deste repositório, não como link simbólico (instalação em `dev/revisao-sistematica/README.md`). Toda modificação vale para os dois lugares; antes de rodar, confira a sincronia com `python3 -m pytest -q dev/revisao-sistematica/tests/test_sincronia_instalacao.py`, porque uma cópia desatualizada mede outra versão da skill.
- As skills irmãs instaladas da mesma forma (cópia de `skills/<nome>` para `~/.claude/skills/<nome>`), para medir o encaminhamento dos pedidos `N01` a `N05`. Sem elas, o esperado desses itens passa a ser "não aciona revisao-sistematica".
- `jq` e Python 3.10 ou superior.
- Rode fora de qualquer repositório com `CLAUDE.md`, para que instruções de projeto não interfiram. Um `~/.claude/CLAUDE.md` pessoal também interfere: relate se existia.
- Cada chamada gasta tokens. `--max-budget-usd` limita o custo por chamada.

## Gatilhos

Cada pedido roda numa sessão nova, sem Bash, Write nem Edit, porque só interessa qual skill é invocada:

```bash
cd ~/Systematic-Review   # raiz do repositório
RSPY="$PWD/skills/revisao-sistematica/scripts/rs.py" python3 - <<'EOF'
import json, os, subprocess, tempfile

d = json.load(open("dev/revisao-sistematica/evals/gatilhos.json", encoding="utf-8"))
linhas = []
for grupo in ("deve_acionar", "nao_deve_acionar"):
    for item in d[grupo]:
        with tempfile.TemporaryDirectory() as pasta:
            if item.get("preparar"):
                subprocess.run(item["preparar"], shell=True, cwd=pasta, check=True, capture_output=True)
            proc = subprocess.run(
                ["claude", "-p", item["pedido"], "--output-format", "stream-json", "--verbose",
                 "--no-session-persistence", "--max-budget-usd", "0.50", "--disallowedTools", "Bash,Write,Edit"],
                cwd=pasta, capture_output=True, text=True, timeout=900)
        skills = []
        for linha in proc.stdout.splitlines():
            try:
                ev = json.loads(linha)
            except json.JSONDecodeError:
                continue
            if ev.get("type") != "assistant":
                continue
            for bloco in ev.get("message", {}).get("content", []):
                if bloco.get("type") == "tool_use" and bloco.get("name") == "Skill":
                    skills.append(bloco.get("input", {}).get("skill"))
        obtido = skills[0] if skills else "nenhuma"
        if grupo == "deve_acionar":
            regra = "ok" if "revisao-sistematica" in skills else "FALHOU"
        else:  # o que reprova é acionar esta skill; o destino exato é conferido à parte
            regra = "ok" if "revisao-sistematica" not in skills else "FALHOU"
        destino = "igual" if obtido == item["esperado"] else "diferente"
        linhas.append((item["id"], grupo, item["esperado"], obtido, regra, destino,
                       "limítrofe" if item.get("limitrofe") else ""))
print("id\tgrupo\tesperado\tobtido\tregra\tdestino\tnota")
for l in linhas:
    print("\t".join(l))
EOF
```

`regra` responde se a skill foi acionada quando devia (ou não foi, quando não devia); `destino` compara a primeira skill invocada com o esperado, o que importa para N01 a N05.

Leia o resultado com o `criterio_de_aprovacao` do próprio JSON: em `deve_acionar`, pelo menos 12 de P01 a P13; em `nao_deve_acionar`, nenhum item não limítrofe pode invocar `revisao-sistematica`, e pelo menos 4 de N01 a N05 devem ir à irmã esperada. Falhas repetidas em pedidos parecidos pedem ajuste na `description` da `SKILL.md` (limite de 1.024 caracteres), não nas references.

A variação entre execuções é real: para decidir uma mudança na `description`, rode cada pedido pelo menos três vezes e compare taxas.

## Cenários

Cada cenário de `cenarios.md` traz a preparação da pasta, um ou dois turnos e os critérios de aceitação. Rode cada turno assim, dentro da pasta preparada:

```bash
ID=$(uuidgen)
claude -p "<texto do turno 1>" --session-id "$ID" \
  --output-format stream-json --verbose --max-budget-usd 5 \
  --permission-mode bypassPermissions > turno1.jsonl
# conferir os critérios do turno 1 com T=turno1.jsonl
claude -p "<texto do turno 2>" --resume "$ID" \
  --output-format stream-json --verbose --max-budget-usd 5 \
  --permission-mode bypassPermissions > turno2.jsonl
```

`bypassPermissions` só numa pasta descartável e numa máquina sem nada sensível; se preferir aprovar ferramentas, troque por `--allowedTools` com os comandos que o cenário usa (`Bash(python3 *)`, `Bash(cp *)`, `Read`, `Write`, `Edit`, `Glob`, `Grep` e a ferramenta de subagentes, no C2). As funções `bash_cmds`, `skills`, `escritos`, `final` e `portoes` estão no topo de `cenarios.md`; defina-as no shell antes de conferir.

Registre, por cenário: data, versão do Claude Code (`claude --version`), modelo, custo informado na linha `result` da transcrição e cada critério como aprovado, reprovado ou não aplicável (quando o turno opcional não foi rodado). Um critério geral G0 reprovado reprova o cenário inteiro.
