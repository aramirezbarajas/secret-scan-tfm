"""Exportacion SARIF 2.1.0 desde triaged.json."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def _result_level(action: str) -> str:
    return "error" if action == "keep" else "note"


def triaged_to_sarif(triaged: dict[str, Any], tool_version: str = "0.1.0") -> dict[str, Any]:
    """Genera SARIF con hallazgos action=keep como resultados activos."""
    findings = triaged.get("findings", [])
    results = []
    for f in findings:
        action = f.get("action", "keep")
        if action != "keep":
            continue
        file_path = f.get("file", "")
        line = int(f.get("line") or 1)
        results.append(
            {
                "ruleId": f.get("rule_id") or "secret-triage",
                "level": _result_level(action),
                "message": {
                    "text": f.get("llm_reason") or "Posible secreto real (LLM)",
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": file_path},
                            "region": {"startLine": line, "endLine": line},
                        }
                    }
                ],
                "properties": {
                    "fingerprint": f.get("fingerprint"),
                    "llm_confidence": f.get("llm_confidence"),
                    "gitleaks_match": f.get("match"),
                },
            }
        )

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "secret-triage",
                        "version": tool_version,
                        "informationUri": "https://github.com/aramirezbarajas/secret-scan-tfm",
                        "rules": [
                            {
                                "id": "secret-triage/llm-real-secret",
                                "name": "LLM classified as real secret",
                                "shortDescription": {"text": "Hallazgo Gitleaks mantenido tras triaje LLM"},
                            }
                        ],
                    }
                },
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "endTimeUtc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    }
                ],
                "results": results,
            }
        ],
    }


def write_sarif(triaged: dict[str, Any], output_path: str, tool_version: str = "0.1.0") -> int:
    sarif = triaged_to_sarif(triaged, tool_version=tool_version)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(sarif, handle, indent=2, ensure_ascii=False)
    return len(sarif["runs"][0]["results"])
