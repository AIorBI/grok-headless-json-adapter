---
name: sentiment-extract
description: Extract sentiment from user text via headless grok (legacy .text parse).
---

# Sentiment Extract (legacy)

## Output contract

Return JSON with fields: sentiment, confidence, summary

Example:

```json
{"sentiment": "positive", "confidence": 0.9, "summary": "User is happy"}
```

## Steps

1. Capture user text as `$INPUT`.
2. Run headless grok and parse the assistant text:

```bash
RESULT=$(grok -p "Analyze sentiment for: $INPUT" --output-format json --yolo | jq -r '.text')
```

3. Extract JSON from markdown fences or the first `{...}` block in `$RESULT`.
4. Use `sentiment`, `confidence`, and `summary` in downstream logic.