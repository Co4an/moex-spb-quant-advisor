#!/usr/bin/env python3
"""
Master Deterministic Automation Orchestrator (`run_pipeline.py`).

Executes all non-AI deterministic layers in sequence:
1. `scripts/moex_spb_collector.py` — Live MOEX ISS API + SPB Exchange API market data & 2026 daily candles
2. `scripts/financial_statement_parser.py` — Raw CSV/HTML/JSON IFRS & RSBU report parser + accounting identity reconciler
3. `scripts/quant_sector_engine.py` — Sector Z-scores, 5-factor scoring, 3-scenario intrinsic valuation & portfolio optimizer
4. Verifies SHA-256 provenance manifests (.prov.json) before handing off the frozen quantitative bundle
   to the Multi-Agent Investment Committee (Sova + Harness²).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import time

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent


def run_step(step_num: int, total: int, title: str, script_rel: str) -> None:
    print(f"\n=== [ШАГ {step_num}/{total}] {title} ({script_rel}) ===")
    t0 = time.time()
    res = subprocess.run([sys.executable, str(ROOT_DIR / script_rel)], cwd=str(ROOT_DIR), check=True)
    dt_sec = round(time.time() - t0, 2)
    print(f"    Завершено успешно за {dt_sec} сек. (код {res.returncode})")


def verify_provenance_chain() -> int:
    prov_files = sorted((ROOT_DIR / "data").rglob("*.prov.json"))
    verified = 0
    for pf in prov_files:
        manifest = json.loads(pf.read_text(encoding="utf-8"))
        art_rel = manifest["artifact"]["path"]
        expected_sha = manifest["artifact"]["sha256"]
        art_path = ROOT_DIR / art_rel
        actual_sha = hashlib.sha256(art_path.read_bytes()).hexdigest()
        if actual_sha != expected_sha:
            raise RuntimeError(f"SHA-256 mismatch for {art_rel}: expected {expected_sha}, got {actual_sha}")
        verified += 1
    return verified


def main() -> None:
    t_start = time.time()
    run_step(1, 4, "Парсинг живой ключевой ставки ЦБ РФ (cbr.ru), котировок Мосбиржи (MOEX ISS) и СПБ Биржи", "scripts/moex_spb_collector.py")
    run_step(2, 4, "Парсинг отчётностей МСФО/РСБУ и сверка 62 балансовых тождеств", "scripts/financial_statement_parser.py")
    run_step(3, 4, "Парсинг живых новостей ЦБ РФ, Мосбиржи и СМИ, оценка сентимента и 3 горизонтов инвестирования", "scripts/news_and_horizon_engine.py")
    run_step(4, 4, "Количественная оценка секторов, Z-скоринг, 3 горизонта и оптимизация портфелей", "scripts/quant_sector_engine.py")

    verified_count = verify_provenance_chain()
    total_sec = round(time.time() - t_start, 2)
    print(
        f"\n[ГОТОВО] Детерминированное ядро выполнено за {total_sec} сек. "
        f"Проверено {verified_count} SHA-256 манифестов (.prov.json). "
        f"Пакет данных готов для дашборда и мультиагентного комитета Сова + Harness²."
    )


if __name__ == "__main__":
    main()
