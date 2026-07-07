"""Tests basicos de secret-triage."""

from pathlib import Path

from secret_triage.gitleaks_io import load_gitleaks_report
from secret_triage.report import render_markdown

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_gitleaks_report():
    findings = load_gitleaks_report(FIXTURES / "sample_gitleaks.json")
    assert len(findings) == 1
    assert findings[0]["rule_id"] == "generic-api-key"
    assert "mock_secrets" in findings[0]["file"]


def test_render_markdown():
    triaged = {
        "source_report": "gitleaks.json",
        "model": "llama3.1:8b",
        "prompt_version": "v2",
        "summary": {"total": 1, "dismissed": 1, "kept": 0},
        "findings": [
            {
                "file": "tests/fixtures/mock_secrets.py",
                "line": 19,
                "rule_id": "generic-api-key",
                "action": "dismiss",
                "llm_reason": "MOCK en ruta fixtures",
            }
        ],
    }
    md = render_markdown(triaged)
    assert "secret-triage" in md
    assert "Descartados" in md
