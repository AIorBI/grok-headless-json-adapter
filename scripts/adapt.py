"""Analyze legacy headless skills and emit v0.2.67 structuredOutput adaptations."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any

from json_schema import build_grok_argv, infer_schema_from_contract, schema_to_cli_arg

ADAPTER_SKILL_ROOT = ".grok/skills/adapt-headless-json"
INVOKE_SCRIPT = f"{ADAPTER_SKILL_ROOT}/scripts/invoke_structured.py"

LEGACY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("jq_text_parse", re.compile(r"jq\s+-r\s+['\"]\.text['\"]")),
    ("jq_text_field", re.compile(r"jq\s+.*\.text")),
    ("output_format_json_only", re.compile(r"--output-format\s+json(?!.*--json-schema)")),
    ("markdown_table_extract", re.compile(r"\|\s*[-:]+\s*\|")),
    ("parse_markdown_json", re.compile(r"parse.*markdown|extract.*json.*from.*text", re.I)),
    ("reparse_text_block", re.compile(r"structuredOutput|json-schema", re.I)),
]

LEGACY_BASH = re.compile(
    r"```bash\s*\n.*?grok\s+-p.*?```",
    flags=re.DOTALL | re.IGNORECASE,
)

INVOKE_BLOCK = re.compile(r"```bash\s*\n(python3 .*?invoke_structured\.py.*?)\n```", re.DOTALL)


def detect_legacy_patterns(skill_md: str) -> list[str]:
    """Return labels for legacy headless patterns found in a skill."""
    hits: list[str] = []
    for label, pattern in LEGACY_PATTERNS:
        if label == "reparse_text_block" and pattern.search(skill_md or ""):
            continue
        if pattern.search(skill_md or ""):
            hits.append(label)
    return hits


def extract_output_contract(skill_md: str) -> str:
    """Best-effort extraction of the skill's declared output shape."""
    text = skill_md or ""
    sections = re.split(r"\n##\s+", text)
    for section in sections:
        title = section.split("\n", 1)[0].strip().lower()
        if any(tok in title for tok in ("output", "response", "return", "format", "contract")):
            body = section.split("\n", 1)[1] if "\n" in section else ""
            return body.strip()
    for block in re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL):
        return block.strip()
    return text


def extract_steps_section(skill_md: str) -> str:
    """Return the body of the first ## Steps section, or empty string."""
    text = skill_md or ""
    match = re.search(r"##\s+Steps\s*\n(.*?)(?=\n##\s+|\Z)", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def schema_file_rel(skill_name: str) -> str:
    return f"{ADAPTER_SKILL_ROOT}/schemas/{skill_name}.schema.json"


def resolve_adapter_root(skill_path: Path, explicit: Path | None = None) -> Path:
    """Locate the on-disk adapt-headless-json skill root."""
    if explicit is not None:
        root = explicit.expanduser().resolve()
        if not (root / "SKILL.md").is_file():
            raise ValueError(f"adapter root missing SKILL.md: {root}")
        return root

    resolved = skill_path.expanduser().resolve()
    for parent in [resolved, *resolved.parents]:
        if (parent / "SKILL.md").is_file() and (parent / "scripts" / "adapt.py").is_file():
            return parent

    cwd_candidate = (Path.cwd() / ADAPTER_SKILL_ROOT).resolve()
    if (cwd_candidate / "SKILL.md").is_file():
        return cwd_candidate

    raise ValueError(
        "Cannot find adapt-headless-json adapter root. "
        "Load the adapter under .grok/skills/adapt-headless-json/ or pass --adapter-root."
    )


def adapt_steps_section(steps_md: str, schema: dict[str, Any], *, skill_name: str) -> str:
    """Rewrite legacy headless steps to use structuredOutput while keeping flow."""
    if not steps_md.strip():
        required = ", ".join(schema.get("required", [])) or "see schema"
        return (
            "1. Build the prompt from user input.\n"
            f"2. Run `{INVOKE_SCRIPT}` with `--json-schema`.\n"
            f"3. Use structuredOutput keys: {required}.\n"
            "4. On `structuredOutputError`, retry with a shorter prompt."
        )

    schema_path = schema_file_rel(skill_name)
    wrapper_block = emit_invocation_snippet(
        schema,
        prompt_placeholder="Analyze sentiment for: $INPUT",
        schema_path=f"@{schema_path}",
    )

    adapted = steps_md
    adapted = LEGACY_BASH.sub(f"```bash\n{wrapper_block}\n```", adapted)
    adapted = re.sub(
        r"(?i)parse.*(?:markdown|json|assistant text|\.text).*",
        "Read structuredOutput keys directly from wrapper stdout (no re-parse).",
        adapted,
    )
    adapted = re.sub(
        r"(?i)extract json from markdown.*",
        "structuredOutput is already parsed JSON — use the returned dict keys directly.",
        adapted,
    )
    return adapted.strip()


def emit_invocation_snippet(
    schema: dict[str, Any],
    *,
    prompt_placeholder: str = "YOUR_PROMPT",
    script_rel: str = INVOKE_SCRIPT,
    schema_path: str | None = None,
) -> str:
    """Ready-to-paste invocation using the bundled wrapper."""
    schema_arg = schema_path if schema_path else f"'{schema_to_cli_arg(schema)}'"
    return (
        f"python3 {script_rel} \\\n"
        f'  --prompt "{prompt_placeholder}" \\\n'
        f"  --schema {schema_arg}"
    )


def emit_direct_grok_snippet(schema: dict[str, Any], prompt_placeholder: str = "YOUR_PROMPT") -> str:
    """Shell snippet calling grok directly (no Python wrapper)."""
    argv = build_grok_argv(prompt_placeholder, schema)
    cmd = shlex.join(argv)
    return (
        f"{cmd} | python3 -c \"import json,sys; "
        "print(json.dumps(json.load(sys.stdin)['structuredOutput'], indent=2))\""
    )


def extract_invoke_command(adapted_md: str) -> str:
    """Return the first invoke_structured.py bash block from adapted markdown."""
    match = INVOKE_BLOCK.search(adapted_md or "")
    if not match:
        raise ValueError("no invoke_structured.py command block in adapted skill")
    return re.sub(r"\\\n\s*", " ", match.group(1).strip())


def extract_schema_at_path(adapted_md: str) -> str:
    """Return the @...schema.json path referenced in adapted markdown."""
    match = re.search(r"--schema\s+(@\S+\.schema\.json)", adapted_md or "")
    if not match:
        raise ValueError("no --schema @path in adapted skill")
    return match.group(1)


def adapt_skill(skill_md: str, *, skill_name: str | None = None) -> str:
    """Produce an adapted SKILL.md body that uses structuredOutput directly."""
    contract = extract_output_contract(skill_md)
    schema = infer_schema_from_contract(contract)
    name = skill_name or "adapted-skill"
    schema_json = schema_to_cli_arg(schema)
    schema_rel = schema_file_rel(name)
    wrapper_snippet = emit_invocation_snippet(
        schema,
        prompt_placeholder="Analyze sentiment for: $INPUT",
        schema_path=f"@{schema_rel}",
    )
    direct_snippet = emit_direct_grok_snippet(schema, prompt_placeholder="Analyze sentiment for: $INPUT")
    adapted_steps = adapt_steps_section(extract_steps_section(skill_md), schema, skill_name=name)

    adapted = f"""---
name: {name}
description: >
  Adapted for Grok Build v0.2.67 headless structured JSON. Uses --json-schema and
  reads structuredOutput directly (no jq/.text re-parse).
---

# {name.replace('-', ' ').title()}

This skill was adapted from a legacy `grok -p` + `.text` parse workflow.

## Headless structured invocation (v0.2.67+)

Prefer the bundled wrapper (handles argv + structuredOutput extraction):

```bash
{wrapper_snippet}
```

Direct grok call (equivalent):

```bash
{direct_snippet}
```

## Output contract

Schema lives at `{schema_rel}` (written by `adapt.py --write`).

```json
{schema_json}
```

Consume `structuredOutput` from the JSON response — never re-parse `.text`.

## Steps

{adapted_steps}
"""
    return adapted


def adapt_skill_file(path: str | Path) -> str:
    """Read a skill file and return adapted markdown."""
    text = Path(path).read_text(encoding="utf-8")
    name_match = re.search(r"^name:\s*([^\n]+)", text, flags=re.MULTILINE)
    skill_name = name_match.group(1).strip() if name_match else None
    return adapt_skill(text, skill_name=skill_name)


def write_adapted_artifacts(
    skill_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    adapter_root: str | Path | None = None,
) -> dict[str, Path]:
    """Write adapted SKILL.md and schema under the adapter root schemas/ dir."""
    source = Path(skill_path)
    adapter = resolve_adapter_root(source, Path(adapter_root) if adapter_root else None)
    text = source.read_text(encoding="utf-8")
    name_match = re.search(r"^name:\s*([^\n]+)", text, flags=re.MULTILINE)
    skill_name = (name_match.group(1).strip() if name_match else source.stem).strip()

    contract = extract_output_contract(text)
    schema = infer_schema_from_contract(contract)

    schema_dir = adapter / "schemas"
    schema_dir.mkdir(parents=True, exist_ok=True)
    schema_path = schema_dir / f"{skill_name}.schema.json"
    schema_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")

    out_dir = Path(output_dir) if output_dir else source.parent
    adapted_path = out_dir / f"{source.stem}.adapted.md"
    adapted_path.write_text(adapt_skill(text, skill_name=skill_name), encoding="utf-8")

    return {"adapted": adapted_path, "schema": schema_path, "adapter_root": adapter}


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-root", metavar="PATH", help="Path to adapt-headless-json skill root")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--detect", metavar="SKILL.md", help="List legacy headless patterns")
    group.add_argument("--schema", metavar="SKILL.md", help="Print inferred JSON schema")
    group.add_argument("--adapt", metavar="SKILL.md", help="Print adapted SKILL.md")
    group.add_argument("--write", metavar="SKILL.md", help="Write adapted SKILL + schema under adapter/schemas/")
    args = parser.parse_args(argv)

    skill_path = Path(args.detect or args.schema or args.adapt or args.write)
    text = skill_path.read_text(encoding="utf-8")
    adapter_root = Path(args.adapter_root) if args.adapter_root else None

    if args.detect:
        for label in detect_legacy_patterns(text):
            print(label)
        return 0

    if args.schema:
        contract = extract_output_contract(text)
        schema = infer_schema_from_contract(contract)
        json.dump(schema, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if args.write:
        paths = write_adapted_artifacts(skill_path, adapter_root=adapter_root)
        print(paths["adapted"])
        print(paths["schema"])
        return 0

    sys.stdout.write(adapt_skill_file(skill_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())