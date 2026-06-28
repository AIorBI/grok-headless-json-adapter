# grok-headless-json-adapter

Loadable Grok Build skill repo for adapting project skills to **v0.2.67** headless structured JSON (`--json-schema`, `structuredOutput`).

## Requirements

- Grok Build **0.2.67+** (`grok --version`)
- Python 3.9+ (stdlib only for helpers/tests)

## Load into your project

Pick one:

### Copy (simplest)

```bash
git clone https://github.com/AIorBI/grok-headless-json-adapter.git /tmp/grok-headless-json-adapter
mkdir -p .grok/skills/adapt-headless-json
cp -R /tmp/grok-headless-json-adapter/{SKILL.md,scripts,examples} .grok/skills/adapt-headless-json/
```

### Submodule

```bash
git submodule add https://github.com/AIorBI/grok-headless-json-adapter.git .grok/skills/adapt-headless-json
```

### Verify load

```bash
grok inspect | grep -i adapt-headless-json
ls .grok/skills/adapt-headless-json/SKILL.md
```

The skill description should mention **adapt skills**, **headless json**, and **structuredOutput**.

## Use from Grok Build TUI

- Slash: `/adapt-headless-json path/to/SKILL.md`
- Or ask: "Adapt this skill to headless structured JSON using the adapter"

The agent runs `scripts/adapt.py` and `scripts/invoke_structured.py` from `.grok/skills/adapt-headless-json/`.

## Headless structured invocation (0.2.67)

```bash
grok -p "Your prompt" \
  --json-schema '{"type":"object","properties":{"result":{"type":"string"}},"required":["result"]}' \
  --output-format json \
  --verbatim \
  --yolo
```

Read **`structuredOutput`** from the JSON response — do not re-parse `.text`.

### Wrapper

```bash
python3 .grok/skills/adapt-headless-json/scripts/invoke_structured.py \
  --prompt "Analyze sentiment for: great day" \
  --schema @.grok/skills/adapt-headless-json/examples/sentiment.schema.json
```

## Example usage

| File | Role |
|------|------|
| `examples/old-skill.md` | Legacy `grok -p` + `jq .text` pattern |
| `examples/new-skill.md` | Adapted skill using `structuredOutput` |
| `examples/sentiment.schema.json` | Schema for the example |

Adapt the sample:

```bash
python3 .grok/skills/adapt-headless-json/scripts/adapt.py --adapt examples/old-skill.md
python3 .grok/skills/adapt-headless-json/scripts/adapt.py --detect examples/old-skill.md
python3 .grok/skills/adapt-headless-json/scripts/adapt.py --schema examples/old-skill.md
```

## Tests

```bash
python3 -m pytest tests/ -q
```

## Layout

```
SKILL.md                 # TUI-discoverable adapter skill
scripts/
  json_schema.py         # schema emit + structuredOutput parse
  adapt.py               # legacy skill analysis + adaptation
  invoke_structured.py   # grok invocation wrapper
examples/                # before/after sample skills
tests/                   # unit tests (no grok binary required)
```