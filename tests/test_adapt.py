import json
import re
import shlex
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from adapt import (  # noqa: E402
    ADAPTER_SKILL_ROOT,
    INVOKE_SCRIPT,
    adapt_skill,
    detect_legacy_patterns,
    emit_direct_grok_snippet,
    emit_invocation_snippet,
    extract_invoke_command,
    extract_output_contract,
    extract_schema_at_path,
    extract_steps_section,
    schema_file_rel,
    write_adapted_artifacts,
)
from json_schema import infer_schema_from_contract  # noqa: E402

OLD_SKILL = Path(__file__).resolve().parents[1] / "examples" / "old-skill.md"
REPO_ROOT = Path(__file__).resolve().parents[1]
SHIPPED_SCHEMA = REPO_ROOT / "schemas" / "sentiment-extract.schema.json"


def test_detect_legacy_patterns_on_example():
    text = OLD_SKILL.read_text(encoding="utf-8")
    hits = detect_legacy_patterns(text)
    assert "jq_text_parse" in hits
    assert "output_format_json_only" in hits


def test_schema_fidelity_matches_original_contract():
    text = OLD_SKILL.read_text(encoding="utf-8")
    contract = extract_output_contract(text)
    schema = infer_schema_from_contract(contract)
    assert set(schema["required"]) == {"sentiment", "confidence", "summary"}
    assert "summary_example" not in schema["properties"]


def test_adapt_preserves_original_steps():
    text = OLD_SKILL.read_text(encoding="utf-8")
    adapted = adapt_skill(text, skill_name="sentiment-extract")
    original_steps = extract_steps_section(text)
    assert "Capture user text as `$INPUT`" in adapted
    assert "downstream logic" in adapted
    assert original_steps.splitlines()[0] in adapted


def test_emit_invocation_snippet_uses_project_path():
    schema = {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}
    snippet = emit_invocation_snippet(
        schema,
        schema_path="@.grok/skills/adapt-headless-json/schemas/x.schema.json",
    )
    assert INVOKE_SCRIPT in snippet
    assert ADAPTER_SKILL_ROOT in snippet
    assert snippet.startswith("python3 .grok/skills/")


def test_emit_direct_grok_snippet_is_valid_shell():
    schema = {
        "type": "object",
        "properties": {"sentiment": {"type": "string"}},
        "required": ["sentiment"],
    }
    snippet = emit_direct_grok_snippet(schema, prompt_placeholder="test prompt")
    assert snippet.startswith("grok ")
    assert "--json-schema" in snippet
    assert "test prompt" in snippet
    grok_part = snippet.split("|", 1)[0].strip()
    argv = shlex.split(grok_part)
    assert argv[0] == "grok"
    assert "-p" in argv
    assert "--json-schema" in argv


def test_adapted_output_references_adapter_schemas_dir():
    text = OLD_SKILL.read_text(encoding="utf-8")
    adapted = adapt_skill(text, skill_name="sentiment-extract")
    assert schema_file_rel("sentiment-extract") in adapted
    assert "--schema @.grok/skills/adapt-headless-json/schemas/sentiment-extract.schema.json" in adapted
    assert "jq -r '.text'" not in adapted


def test_write_adapted_artifacts_places_schema_in_adapter_root():
    target = REPO_ROOT / "examples" / "_write_target.md"
    target.write_text(OLD_SKILL.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        paths = write_adapted_artifacts(target, adapter_root=REPO_ROOT)
        expected_schema = REPO_ROOT / "schemas" / "sentiment-extract.schema.json"
        assert paths["schema"] == expected_schema
        assert expected_schema.is_file()
        adapted = paths["adapted"].read_text(encoding="utf-8")
        at_path = extract_schema_at_path(adapted)
        assert at_path == "@.grok/skills/adapt-headless-json/schemas/sentiment-extract.schema.json"
        # --write lands schema in adapter/schemas/ (maps to @path after load)
        assert paths["schema"].resolve() == expected_schema.resolve()
    finally:
        target.unlink(missing_ok=True)
        (REPO_ROOT / "examples" / "_write_target.adapted.md").unlink(missing_ok=True)


def test_extract_invoke_command_from_adapted():
    text = OLD_SKILL.read_text(encoding="utf-8")
    adapted = adapt_skill(text, skill_name="sentiment-extract")
    cmd = extract_invoke_command(adapted)
    assert "invoke_structured.py" in cmd
    assert "@.grok/skills/adapt-headless-json/schemas/sentiment-extract.schema.json" in cmd


def test_shipped_schema_exists_for_example():
    assert SHIPPED_SCHEMA.is_file()
    schema = json.loads(SHIPPED_SCHEMA.read_text(encoding="utf-8"))
    assert set(schema["required"]) == {"sentiment", "confidence", "summary"}


def test_adapt_skill_mentions_structured_output():
    text = OLD_SKILL.read_text(encoding="utf-8")
    adapted = adapt_skill(text, skill_name="sentiment-extract")
    assert "structuredOutput" in adapted
    assert "--json-schema" in adapted
    assert re.search(r"never re-parse.*\.text", adapted, re.I)