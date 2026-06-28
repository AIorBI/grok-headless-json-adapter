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
- This repo loaded under `.grok/skills/adapt-headless-json/` including its `schemas/` directory (see README.md)

## Workflow

### 1. Analyze the target skill

Read the skill's `SKILL.md` (or pasted content). Identify:

- Shell snippets using `grok -p` without `--json-schema`
- `jq` on `.text` or manual markdown/JSON extraction
- Implicit output contracts (bullets, example JSON blocks, "Return JSON with fields: ...")

```bash
python3 .grok/skills/adapt-headless-json/scripts/adapt.py --detect path/to/SKILL.md
```

### 2. Infer schema

```bash
python3 .grok/skills/adapt-headless-json/scripts/adapt.py --schema path/to/SKILL.md
```

Edit the schema if needed — it must match what downstream steps consume.

### 3. Produce adapted skill + schema (preferred)

`--write` emits the adapted markdown **and** writes the schema to the adapter's canonical location:

```
.grok/skills/adapt-headless-json/schemas/<skill-name>.schema.json
```

```bash
python3 .grok/skills/adapt-headless-json/scripts/adapt.py --write path/to/SKILL.md
```

Outputs:

- `path/to/SKILL.adapted.md` — refactored skill with `@.grok/skills/adapt-headless-json/schemas/...` paths
- `.grok/skills/adapt-headless-json/schemas/<skill-name>.schema.json` — inferred schema (required for `@` paths in the adapted file)

Preview only (no files written):

```bash
python3 .grok/skills/adapt-headless-json/scripts/adapt.py --adapt path/to/SKILL.md
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

Preferred wrapper (uses the schema file written by `--write`):

```bash
python3 .grok/skills/adapt-headless-json/scripts/invoke_structured.py \
  --prompt "..." \
  --schema @.grok/skills/adapt-headless-json/schemas/<skill-name>.schema.json
```

### 5. Verify

Run the **exact** wrapper command from the produced `*.adapted.md` twice. Both runs must return non-empty `structuredOutput` whose keys match the schema `required` list.

```bash
python3 .grok/skills/adapt-headless-json/scripts/invoke_structured.py \
  --prompt "test prompt" \
  --schema @.grok/skills/adapt-headless-json/schemas/sentiment-extract.schema.json
```

## Helper scripts (this repo)

| Script | Purpose |
|--------|---------|
| `scripts/json_schema.py` | `infer_schema_from_contract`, `schema_to_cli_arg`, `parse_structured_response`, `build_grok_argv` |
| `scripts/adapt.py` | `detect_legacy_patterns`, `adapt_skill`, `--write` for adapted SKILL + schema |
| `scripts/invoke_structured.py` | Shell grok with schema; print `structuredOutput` JSON |

## Adaptation rules

1. **Schema first** — derive from the skill's output contract; tighten types where obvious.
2. **Replace parse steps** — delete jq/markdown extraction; read `structuredOutput` keys.
3. **Keep agent orchestration** — only change headless I/O, not vault/MCP/business logic.
4. **Use `--verbatim`** when the model adds preamble before JSON (common without it).
5. **Always `--write`** so the `@.grok/skills/adapt-headless-json/schemas/...` path exists on disk.

## Example

See `examples/old-skill.md` (legacy) and `examples/new-skill.md` (adapted sentiment extractor). Shipped schema: `schemas/sentiment-extract.schema.json`.