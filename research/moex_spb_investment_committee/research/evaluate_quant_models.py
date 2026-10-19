#!/usr/bin/env python3
# @evidence[[sources.json#S1]]
# @evidence[[sources.json#S3]]
# @evidence[[sources.json#S6]]
# @evidence[[sources.json#S7]]
# @evidence[[sources.json#S8]]
from __future__ import annotations
import json
import math
import pathlib

def compute_incumbent_utility(folder: pathlib.Path) -> dict:
    abl = json.loads((folder / "inputs" / "strategy_ablations.json").read_text(encoding="utf-8"))
    val = json.loads((folder / "inputs" / "quant_valuation_matrix.json").read_text(encoding="utf-8"))
    inc = abl["variants"][0]
    return {
        "combined_score": float(inc["composite_utility_score"]),
        "expected_12m_return_pct": float(inc["expected_12m_return_pct"]),
        "avg_div_yield_pct": float(inc["avg_div_yield_pct"]),
        "issuers_count": int(val["issuers_count"]),
    }

if __name__ == "__main__":
    base = pathlib.Path(__file__).resolve().parent.parent
    print(json.dumps(compute_incumbent_utility(base), ensure_ascii=False))
