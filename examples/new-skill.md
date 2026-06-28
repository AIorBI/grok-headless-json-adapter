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

Schema:

```json
{"type":"object","properties":{"sentiment":{"type":"string"},"confidence":{"type":"number"},"summary":{"type":"string"}},"required":["sentiment","confidence","summary"],"additionalProperties":false}
```

## Steps

1. Capture user text as `$INPUT`.
2. Invoke structured headless grok (v0.2.67+):

```bash
python3 .grok/skills/adapt-headless-json/scripts/invoke_structured.py \
  --prompt "Analyze sentiment for: $INPUT. Return structured fields only." \
  --schema @.grok/skills/adapt-headless-json/examples/sentiment.schema.json
```

3. Read keys directly from stdout JSON (`sentiment`, `confidence`, `summary`) — sourced from `structuredOutput`.
4. On failure, retry with a shorter prompt; do not parse `.text`.