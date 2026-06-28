---
name: sentiment-extract
description: >
  Extract sentiment via Grok Build v0.2.67 headless structured JSON (--json-schema,
  structuredOutput). No jq/.text re-parse.
---

# Sentiment Extract (structured)

## Output contract

```json
{"sentiment":"positive","confidence":0.9,"summary":"User is happy"}
```

Schema file: `.grok/skills/adapt-headless-json/schemas/sentiment-extract.schema.json`

## Steps

1. Capture user text as `$INPUT`.
2. Run structured headless grok (v0.2.67+):

```bash
python3 .grok/skills/adapt-headless-json/scripts/invoke_structured.py \
  --prompt "Analyze sentiment for: $INPUT" \
  --schema @.grok/skills/adapt-headless-json/schemas/sentiment-extract.schema.json
```

3. Read `sentiment`, `confidence`, and `summary` directly from structuredOutput stdout (no re-parse).
4. Use `sentiment`, `confidence`, and `summary` in downstream logic.