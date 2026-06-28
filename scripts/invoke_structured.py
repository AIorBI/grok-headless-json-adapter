#!/usr/bin/env python3
"""Invoke grok headless with --json-schema and print structuredOutput JSON."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from json_schema import build_grok_argv, parse_structured_response, schema_to_cli_arg


def invoke_structured(
    prompt: str,
    schema: dict,
    *,
    cwd: str | None = None,
    yolo: bool = True,
    verbatim: bool = True,
    max_turns: int = 1,
    disallow_tools: bool = True,
    grok_bin: str = "grok",
) -> dict:
    argv = build_grok_argv(
        prompt,
        schema,
        cwd=cwd,
        yolo=yolo,
        verbatim=verbatim,
        max_turns=max_turns,
        disallow_tools=disallow_tools,
    )
    argv[0] = grok_bin
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0 and not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or f"grok exited {proc.returncode}")
    return parse_structured_response(proc.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True, help="Headless prompt")
    parser.add_argument("--schema", required=True, help="JSON schema string or @file")
    parser.add_argument("--cwd", default=None, help="Working directory for grok")
    parser.add_argument("--max-turns", type=int, default=1)
    parser.add_argument("--no-yolo", action="store_true")
    parser.add_argument("--no-verbatim", action="store_true")
    parser.add_argument("--grok-bin", default="grok")
    args = parser.parse_args(argv)

    schema_raw = args.schema
    if schema_raw.startswith("@"):
        schema_raw = Path(schema_raw[1:]).read_text(encoding="utf-8")
    schema = json.loads(schema_raw)

    result = invoke_structured(
        args.prompt,
        schema,
        cwd=args.cwd,
        yolo=not args.no_yolo,
        verbatim=not args.no_verbatim,
        max_turns=args.max_turns,
        grok_bin=args.grok_bin,
    )
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())