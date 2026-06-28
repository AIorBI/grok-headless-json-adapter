"""Emit valid --json-schema values and parse structuredOutput from grok 0.2.67+ responses."""

from __future__ import annotations

import json
import re
from typing import Any


def schema_to_cli_arg(schema: dict[str, Any]) -> str:
    """Compact JSON string suitable for grok --json-schema."""
    return json.dumps(schema, separators=(",", ":"), ensure_ascii=True)


def parse_structured_response(stdout: str) -> dict[str, Any]:
    """Parse grok --output-format json stdout and return structuredOutput.

    Raises ValueError when stdout is not valid JSON, structuredOutput is missing,
    or structuredOutputError is present.
    """
    text = (stdout or "").strip()
    if not text:
        raise ValueError("empty grok stdout")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"grok stdout is not JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("grok stdout JSON must be an object")

    if payload.get("type") == "error":
        raise ValueError(payload.get("message") or "grok error response")

    if payload.get("structuredOutputError"):
        raise ValueError(str(payload["structuredOutputError"]))

    structured = payload.get("structuredOutput")
    if structured is None:
        raise ValueError("structuredOutput is null — model did not produce schema-valid JSON")

    if not isinstance(structured, dict):
        raise ValueError("structuredOutput must be an object")

    return structured


def _normalize_field_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "field"


def _guess_type(field_name: str, description: str = "") -> str:
    blob = f"{field_name} {description}".lower()
    if any(tok in blob for tok in ("count", "score", "confidence", "rating", "number", "amount")):
        return "number"
    if any(tok in blob for tok in ("items", "list", "tags", "bullets", "array")):
        return "array"
    if any(tok in blob for tok in ("enabled", "valid", "success", "flag", "is_")):
        return "boolean"
    return "string"


def infer_schema_from_contract(contract: str) -> dict[str, Any]:
    """Infer a JSON Schema object from skill output-contract prose or examples.

    Recognizes:
    - bullet lists like ``- sentiment: string``
    - JSON examples in fenced blocks
    - lines like ``Return JSON with fields: foo, bar``
    """
    text = contract or ""
    properties: dict[str, Any] = {}
    required: list[str] = []

    for match in re.finditer(
        r"[-*]\s*`?([a-zA-Z_][\w]*)`?\s*:\s*([a-zA-Z\[\]]+)",
        text,
    ):
        name = _normalize_field_name(match.group(1))
        raw_type = match.group(2).lower()
        if raw_type in {"str", "string"}:
            json_type = "string"
        elif raw_type in {"int", "integer", "float", "number", "num"}:
            json_type = "number"
        elif raw_type in {"bool", "boolean"}:
            json_type = "boolean"
        elif raw_type.startswith("list") or raw_type.startswith("array"):
            json_type = "array"
        else:
            json_type = _guess_type(name, raw_type)
        properties[name] = {"type": json_type}
        required.append(name)

    fields_match = re.search(
        r"(?:fields?|keys?|properties)\s*:\s*([a-zA-Z0-9_,\s]+)",
        text,
        flags=re.IGNORECASE,
    )
    if fields_match:
        for raw in fields_match.group(1).split(","):
            name = _normalize_field_name(raw)
            if name and name not in properties:
                properties[name] = {"type": _guess_type(name)}
                required.append(name)

    for block in re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL):
        try:
            example = json.loads(block)
        except json.JSONDecodeError:
            continue
        if not isinstance(example, dict):
            continue
        for key, value in example.items():
            name = _normalize_field_name(str(key))
            if name in properties:
                continue
            if isinstance(value, bool):
                json_type = "boolean"
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                json_type = "number"
            elif isinstance(value, list):
                json_type = "array"
            else:
                json_type = "string"
            properties[name] = {"type": json_type}
            required.append(name)

    if not properties:
        properties = {
            "result": {"type": "string", "description": "Primary structured result"},
        }
        required = ["result"]

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "required": sorted(set(required)),
        "additionalProperties": False,
    }
    return schema


def build_grok_argv(
    prompt: str,
    schema: dict[str, Any],
    *,
    cwd: str | None = None,
    yolo: bool = True,
    verbatim: bool = True,
    max_turns: int = 1,
) -> list[str]:
    """Build argv for ``grok -p ... --json-schema ... --output-format json``."""
    argv = [
        "grok",
        "-p",
        prompt,
        "--json-schema",
        schema_to_cli_arg(schema),
        "--output-format",
        "json",
        "--max-turns",
        str(max_turns),
    ]
    if cwd:
        argv.extend(["--cwd", cwd])
    if yolo:
        argv.append("--yolo")
    if verbatim:
        argv.append("--verbatim")
    return argv