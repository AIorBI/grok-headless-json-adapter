import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from adapt import adapt_skill, detect_legacy_patterns, emit_invocation_snippet  # noqa: E402


OLD_SKILL = Path(__file__).resolve().parents[1] / "examples" / "old-skill.md"


def test_detect_legacy_patterns_on_example():
    text = OLD_SKILL.read_text(encoding="utf-8")
    hits = detect_legacy_patterns(text)
    assert "jq_text_parse" in hits
    assert "output_format_json_only" in hits


def test_adapt_skill_mentions_structured_output():
    text = OLD_SKILL.read_text(encoding="utf-8")
    adapted = adapt_skill(text, skill_name="sentiment-extract")
    assert "structuredOutput" in adapted
    assert "--json-schema" in adapted
    assert "jq" not in adapted.lower() or "never re-parse" in adapted.lower()


def test_emit_invocation_snippet_uses_wrapper():
    schema = {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}
    snippet = emit_invocation_snippet(schema)
    assert "invoke_structured.py" in snippet
    assert "--schema" in snippet