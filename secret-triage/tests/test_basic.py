"""Tests basicos de secret-triage."""

from pathlib import Path

from secret_triage.config import default_config_text, load_config
from secret_triage.gitleaks_io import load_gitleaks_report
from secret_triage.report import render_markdown
from secret_triage.sarif import triaged_to_sarif

FIXTURES = Path(__file__).parent / "fixtures"


def test_default_config_bundled():
    text = default_config_text()
    assert "llama3.1:8b" in text
    cfg = load_config()
    assert cfg["llm"]["model"] == "llama3.1:8b"


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


def test_sarif_export():
    triaged = {
        "findings": [
            {
                "file": "app/config.py",
                "line": 10,
                "rule_id": "generic-api-key",
                "action": "keep",
                "llm_reason": "credencial en runtime",
                "fingerprint": "app/config.py:generic-api-key:10",
            },
            {
                "file": "tests/mock.py",
                "line": 1,
                "action": "dismiss",
            },
        ]
    }
    sarif = triaged_to_sarif(triaged)
    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"][0]["results"]) == 1
