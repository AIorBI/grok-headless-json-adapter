---
name: adapt-headless-json
description: >
  Adapt Grok skills from legacy headless `.text` / jq parsing to Grok Build v0.2.67+
  structured JSON (`--json-schema`, `structuredOutput`). Use for "/adapt-headless-json",
  "adapt skills", "headless json", "structuredOutput", "migrate skill to json-schema",
  or when refactoring skills to use headless structured output.
argument-hint: path to skill SKILL.md or pasted legacy skill content
user-invocable: true
---

# Adapt Headless JSON Skill (v0.2.67+)

Migrate project skills from legacy `grok -p ... | jq -r '.text'` workflows to **headless structured JSON** introduced in Grok Build **0.2.67**.

## When to use

- A skill shells `grok -p` and re-parses `.text`, markdown tables, or fenced JSON.
- You want token-efficient, schema-constrained outputs via `--json-schema`.
- You need a repeatable adaptation pass the TUI agent can run on any skill file.

## Prerequisites

- Grok Build **0.2.67+** (`grok --version`)
- This repo loaded under `.grok/skills/adapt-headless-json/` (see README.md)

## Workflow

### 1. Analyze the target skill

Read the skill's `SKILL.md` (or pasted content). Identify:

- Shell snippets using `grok -p` without `--json-schema`
- `jq` on `.text` or manual markdown/JSON extraction
- Implicit output contracts (bullets, example JSON blocks, "Return JSON with fields: ...")

Run the detector (pure, no side effects):

```bash
python3 .grok/skills/adapt-headless-json/scripts/adapt.py --detect path/to/SKILL.md
```

### 2. Infer schema

Extract the output contract section and infer a JSON Schema:

```bash
python3 .grok/skills/adapt-headless-json/scripts/adapt.py --schema path/to/SKILL.md
```

Edit the schema if needed — it must match what downstream steps consume.

### 3. Produce adapted skill

Generate a refactored `SKILL.md` that:

- Replaces jq/.text parsing with `structuredOutput`
- Documents the `--json-schema` value
- Uses the bundled wrapper for invocations

```bash
python3 .grok/skills/adapt-headless-json/scripts/adapt.py --adapt path/to/SKILL.md > path/to/SKILL.adapted.md
```

Review the diff. Merge orchestration steps the adapter preserved; keep project-specific MCP/tool guidance.

### 4. Wire invocation sites

Every adapted headless call must use:

```bash
grok -p "..." \
  --json-schema '<schema>' \
  --output-format json \
  --verbatim \
  --yolo
```

**Consume `structuredOutput` directly** — never re-parse `.text`.

Preferred wrapper (same argv, parses response):

```bash
python3 .grok/skills/adapt-headless-json/scripts/invoke_structured.py \
  --prompt "..." \
  --schema '{"type":"object","properties":{...},"required":[...]}'
```

### 5. Verify

Run the adapted wrapper twice on a representative prompt. Both runs must return non-empty `structuredOutput` whose keys match the schema `required` list.

```bash
python3 .grok/skills/adapt-headless-json/scripts/invoke_structured.py \
  --prompt "test prompt" \
  --schema @.grok/skills/adapt-headless-json/examples/sentiment.schema.json
```

## Helper scripts (this repo)

| Script | Purpose |
|--------|---------|
| `scripts/json_schema.py` | `infer_schema_from_contract`, `schema_to_cli_arg`, `parse_structured_response`, `build_grok_argv` |
| `scripts/adapt.py` | `detect_legacy_patterns`, `adapt_skill`, CLI for detect/schema/adapt |
| `scripts/invoke_structured.py` | Shell grok with schema; print `structuredOutput` JSON |

## Adaptation rules

1. **Schema first** — derive from the skill's output contract; tighten types where obvious.
2. **Replace parse steps** — delete jq/markdown extraction; read `structuredOutput` keys.
3. **Keep agent orchestration** — only change headless I/O, not vault/MCP/business logic.
4. **Use `--verbatim`** when the model adds preamble before JSON (common without it).
5. **Document the schema** inline in the adapted skill for future edits.

## Example

See `examples/old-skill.md` (legacy) and `examples/new-skill.md` (adapted sentiment extractor).