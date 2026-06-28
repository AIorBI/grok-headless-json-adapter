import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from json_schema import (  # noqa: E402
    build_grok_argv,
    infer_schema_from_contract,
    parse_structured_response,
    schema_to_cli_arg,
)


def test_schema_to_cli_arg_compact():
    schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    assert schema_to_cli_arg(schema) == '{"type":"object","properties":{"a":{"type":"string"}}}'


def test_infer_schema_from_bullets():
    contract = """
    - sentiment: string
    - confidence: number
    - summary: string
    """
    schema = infer_schema_from_contract(contract)
    assert schema["properties"]["sentiment"]["type"] == "string"
    assert schema["properties"]["confidence"]["type"] == "number"
    assert set(schema["required"]) == {"sentiment", "confidence", "summary"}


def test_infer_schema_from_json_example():
    contract = '```json\n{"foo": 1, "bar": true}\n```'
    schema = infer_schema_from_contract(contract)
    assert schema["properties"]["foo"]["type"] == "number"
    assert schema["properties"]["bar"]["type"] == "boolean"


def test_parse_structured_response_success():
    stdout = json.dumps(
        {
            "text": '{"answer":4}',
            "structuredOutput": {"answer": 4, "confidence": 1.0},
            "stopReason": "EndTurn",
        }
    )
    assert parse_structured_response(stdout) == {"answer": 4, "confidence": 1.0}


def test_parse_structured_response_error():
    stdout = json.dumps({"structuredOutput": None, "structuredOutputError": "bad json"})
    try:
        parse_structured_response(stdout)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "bad json" in str(exc)


def test_build_grok_argv_includes_json_schema():
    schema = {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}
    argv = build_grok_argv("hi", schema, cwd="/tmp/proj")
    assert argv[0] == "grok"
    assert "--json-schema" in argv
    idx = argv.index("--json-schema")
    assert json.loads(argv[idx + 1]) == schema
    assert "--output-format" in argv
    assert argv[argv.index("--output-format") + 1] == "json"
    assert "--cwd" in argv
    assert argv[argv.index("--cwd") + 1] == "/tmp/proj"
    assert "--yolo" in argv
    assert "--verbatim" in argv