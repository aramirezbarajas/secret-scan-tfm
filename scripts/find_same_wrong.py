#!/usr/bin/env python3
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
v1 = json.loads((root / "results/fp_after_llm_v1.json").read_text(encoding="utf-8"))
v2 = json.loads((root / "results/fp_after_llm_v2.json").read_text(encoding="utf-8"))

idx1 = {f"{x['file']}:{x['line']}:{x.get('rule_id')}": x for x in v1}
idx2 = {f"{x['file']}:{x['line']}:{x.get('rule_id')}": x for x in v2}

for key in sorted(set(idx1) & set(idx2)):
    a, b = idx1[key], idx2[key]
    if a.get("ground_truth") in ("F", "X") and a.get("llm_is_real_secret") and b.get("llm_is_real_secret"):
        print(key)
        print(json.dumps(b, ensure_ascii=False, indent=2))
