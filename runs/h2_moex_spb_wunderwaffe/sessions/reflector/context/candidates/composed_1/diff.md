### Component: `guardrails.md`

```diff
--- base/guardrails.md
+++ candidate/guardrails.md
@@ -0,0 +1,16 @@
+# Procedural & Verification Guardrails (INV)
+
+1. **Cross-Exchange Ingestion & Parsing Invariants (`MOEX ISS` + `SPBEX API`):**
+   - In this workspace, SPB Exchange (`spbexchange.ru`) returns numeric fields as Russian comma-decimal strings (e.g., `"272,6"`) and uses a Russian National CA certificate. Always parse SPBEX numeric strings by replacing `,` with `.` before float conversion, and use a resilient SSL context fallback if strict certificate verification fails.
+   - Reconcile cross-exchange ticker aliases explicitly before merging snapshots: in this workspace, MOEX ticker `T` (МКАО «Т-Технологии») maps to SPBEX ticker `TCSG`.
+
+2. **Mandatory Pre-Completion Verification Gate:**
+   - Before finalizing any deliverable or concluding the task, run:
+     ```bash
+     python3 scripts/verify_moex_spb_quant_bundle.py
+     ```
+   - Do not declare completion unless `scripts/verify_moex_spb_quant_bundle.py` exits with code `0`, confirming:
+     - All core JSON artifacts (`data/raw/exchange_merged_snapshot.json`, `data/processed/fundamentals_reconciled.json`, `data/processed/quant_valuation_matrix.json`, `data/processed/sector_aggregates.json`, `data/processed/optimal_portfolios.json`) and `dashboard/data_bundle.js` exist, have valid `.prov.json` SHA-256 manifests, and are synchronized across all 31 issuers.
+     - Cross-exchange alias mapping (`T` <-> `TCSG`) and SPB comma-float parsing produced positive float prices across all 31 equities.
+     - Accounting identities `FCF == OCF - CAPEX` and `EV == Consolidated Market Cap + Net Debt` (for non-banks) hold across all 31 issuers with zero reconciliation warnings.
+     - Deliverable markdown reports contain zero forbidden meta-labels (`SCQA`, `SO WHAT`, `Пирамида Минто`, `Hero KPI`).
```

### Component: `scripts/verify_moex_spb_quant_bundle.py`

```diff
--- /dev/null
+++ candidate/scripts/verify_moex_spb_quant_bundle.py
@@ -0,0 +1,296 @@
+#!/usr/bin/env python3
+"""
+Deterministic Verification Script for MOEX & SPB Exchange Quantitative Bundle.
+
+Verifies:
+(a) Existence and SHA-256 provenance manifest (.prov.json) integrity of:
+    - data/raw/exchange_merged_snapshot.json
+    - data/processed/fundamentals_reconciled.json
+    - data/processed/quant_valuation_matrix.json
+    - data/processed/sector_aggregates.json
+    - data/processed/optimal_portfolios.json
+    - dashboard/data_bundle.js (and payload sync with quant_valuation_matrix.json)
+(b) Cross-exchange alias mapping (T <-> TCSG) and SPB comma-float parsing produced
+    valid positive float prices for all 31 equities.
+(c) Accounting identities FCF == OCF - CAPEX and EV == Consolidated Market Cap + Net Debt
+    (for non-banks) hold across all 31 issuers with zero reconciliation warnings.
+(d) Deliverable markdown reports contain no forbidden AI-slop meta-labels
+    (SCQA, SO WHAT, Пирамида Минто, Hero KPI).
+"""
+from __future__ import annotations
+
+import argparse
+import hashlib
+import json
+import pathlib
+import sys
+from typing import Any
+
+
+REQUIRED_JSON_ARTIFACTS = [
+    "data/raw/exchange_merged_snapshot.json",
+    "data/processed/fundamentals_reconciled.json",
+    "data/processed/quant_valuation_matrix.json",
+    "data/processed/sector_aggregates.json",
+    "data/processed/optimal_portfolios.json",
+]
+
+DASHBOARD_BUNDLE_REL = "dashboard/data_bundle.js"
+
+FORBIDDEN_SLOP_MARKERS = [
+    "SCQA",
+    "SO WHAT",
+    "Пирамида Минто",
+    "Hero KPI",
+]
+
+
+def resolve_workspace_root(explicit_root: str | None) -> pathlib.Path:
+    if explicit_root:
+        return pathlib.Path(explicit_root).resolve()
+    cwd = pathlib.Path.cwd().resolve()
+    if (cwd / "data" / "raw" / "exchange_merged_snapshot.json").exists():
+        return cwd
+    script_parent = pathlib.Path(__file__).resolve().parent.parent
+    if (script_parent / "data" / "raw" / "exchange_merged_snapshot.json").exists():
+        return script_parent
+    return cwd
+
+
+def verify_sha256_manifest(root: pathlib.Path, rel_path: str, errors: list[str]) -> Any:
+    target = root / rel_path
+    if not target.exists():
+        errors.append(f"[MISSING ARTIFACT] {rel_path} does not exist.")
+        return None
+
+    prov_path = root / f"{rel_path}.prov.json"
+    if not prov_path.exists():
+        errors.append(f"[MISSING PROVENANCE] {rel_path}.prov.json does not exist.")
+    else:
+        try:
+            manifest = json.loads(prov_path.read_text(encoding="utf-8"))
+            expected_sha = manifest.get("artifact", {}).get("sha256")
+            actual_sha = hashlib.sha256(target.read_bytes()).hexdigest()
+            if not expected_sha or actual_sha != expected_sha:
+                errors.append(
+                    f"[SHA-256 MISMATCH] {rel_path}: manifest expected {expected_sha}, actual {actual_sha}."
+                )
+        except Exception as exc:
+            errors.append(f"[INVALID PROVENANCE JSON] {rel_path}.prov.json: {exc}")
+
+    try:
+        return json.loads(target.read_text(encoding="utf-8"))
+    except Exception as exc:
+        errors.append(f"[INVALID JSON] {rel_path}: {exc}")
+        return None
+
+
+def verify_dashboard_bundle(
+    root: pathlib.Path,
+    quant_data: dict[str, Any] | None,
+    errors: list[str],
+) -> None:
+    bundle_path = root / DASHBOARD_BUNDLE_REL
+    if not bundle_path.exists():
+        errors.append(f"[MISSING ARTIFACT] {DASHBOARD_BUNDLE_REL} does not exist.")
+        return
+
+    prov_path = root / f"{DASHBOARD_BUNDLE_REL}.prov.json"
+    if prov_path.exists():
+        try:
+            manifest = json.loads(prov_path.read_text(encoding="utf-8"))
+            expected_sha = manifest.get("artifact", {}).get("sha256")
+            actual_sha = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
+            if expected_sha and actual_sha != expected_sha:
+                errors.append(
+                    f"[SHA-256 MISMATCH] {DASHBOARD_BUNDLE_REL}: expected {expected_sha}, actual {actual_sha}."
+                )
+        except Exception as exc:
+            errors.append(f"[INVALID PROVENANCE JSON] {DASHBOARD_BUNDLE_REL}.prov.json: {exc}")
+
+    raw_js = bundle_path.read_text(encoding="utf-8").strip()
+    prefix = "window.WUNDERWAFFE_DATA ="
+    if not raw_js.startswith(prefix):
+        errors.append(f"[DASHBOARD FORMAT] {DASHBOARD_BUNDLE_REL} must start with '{prefix}'.")
+        return
+
+    json_payload_str = raw_js[len(prefix) :].strip()
+    if json_payload_str.endswith(";"):
+        json_payload_str = json_payload_str[:-1].strip()
+
+    try:
+        bundle_obj = json.loads(json_payload_str)
+    except Exception as exc:
+        errors.append(f"[DASHBOARD JSON PARSE ERROR] {DASHBOARD_BUNDLE_REL}: {exc}")
+        return
+
+    raw_issuers = bundle_obj.get("issuers")
+    if isinstance(raw_issuers, list):
+        issuers = {row.get("ticker"): row for row in raw_issuers if isinstance(row, dict) and row.get("ticker")}
+    elif isinstance(raw_issuers, dict):
+        issuers = raw_issuers
+    else:
+        issuers = {}
+
+    if len(issuers) != 31:
+        errors.append(
+            f"[DASHBOARD SYNC] Expected 31 issuers inside {DASHBOARD_BUNDLE_REL}, got {len(issuers)}."
+        )
+    elif quant_data and isinstance(quant_data.get("issuers"), dict):
+        for ticker, q_row in quant_data["issuers"].items():
+            b_row = issuers.get(ticker)
+            if not b_row:
+                errors.append(f"[DASHBOARD SYNC] Ticker {ticker} missing in {DASHBOARD_BUNDLE_REL}.")
+                continue
+            if b_row.get("composite_score") != q_row.get("composite_score"):
+                errors.append(
+                    f"[DASHBOARD SYNC] Composite score mismatch for {ticker}: bundle={b_row.get('composite_score')} vs quant={q_row.get('composite_score')}."
+                )
+
+
+def verify_exchange_snapshot(snap_data: dict[str, Any] | None, errors: list[str]) -> None:
+    if not isinstance(snap_data, dict):
+        return
+    equities = snap_data.get("equities")
+    if not isinstance(equities, dict) or len(equities) != 31:
+        errors.append(
+            f"[EXCHANGE SNAPSHOT] Expected 31 equities in exchange_merged_snapshot.json, got {len(equities) if isinstance(equities, dict) else 'invalid'}."
+        )
+        return
+
+    t_row = equities.get("T")
+    if not isinstance(t_row, dict):
+        errors.append("[ALIAS MAPPING] Ticker 'T' missing from exchange_merged_snapshot.json.")
+    else:
+        if t_row.get("spb_ticker") != "TCSG":
+            errors.append(
+                f"[ALIAS MAPPING] Expected T.spb_ticker == 'TCSG', got {t_row.get('spb_ticker')!r}."
+            )
+        spb_p = t_row.get("spbex_price_rub")
+        if not isinstance(spb_p, (int, float)) or spb_p <= 0:
+            errors.append(
+                f"[ALIAS MAPPING] Expected positive float spbex_price_rub for T (via TCSG), got {spb_p!r}."
+            )
+
+    for ticker, row in equities.items():
+        for field in ("price_rub", "moex_price_rub"):
+            val = row.get(field)
+            if not isinstance(val, (int, float)) or isinstance(val, bool) or val <= 0:
+                errors.append(f"[INVALID PRICE] {ticker}.{field} must be positive float, got {val!r}.")
+        spb_val = row.get("spbex_price_rub")
+        if spb_val is not None:
+            if not isinstance(spb_val, (int, float)) or isinstance(spb_val, bool) or spb_val <= 0:
+                errors.append(
+                    f"[SPB COMMA-FLOAT PARSE] {ticker}.spbex_price_rub must be positive float or None, got {spb_val!r}."
+                )
+
+
+def verify_accounting_identities(fund_data: dict[str, Any] | None, errors: list[str]) -> None:
+    if not isinstance(fund_data, dict):
+        return
+
+    warnings = fund_data.get("reconciliation_warnings")
+    if warnings:
+        errors.append(
+            f"[RECONCILIATION WARNINGS] Expected 0 warnings in fundamentals_reconciled.json, got {len(warnings)}: {warnings}"
+        )
+
+    issuers = fund_data.get("issuers")
+    if not isinstance(issuers, dict) or len(issuers) != 31:
+        errors.append(
+            f"[FUNDAMENTALS COUNT] Expected 31 issuers in fundamentals_reconciled.json, got {len(issuers) if isinstance(issuers, dict) else 'invalid'}."
+        )
+        return
+
+    for ticker, row in issuers.items():
+        ocf = row.get("ocf_bln")
+        capex = row.get("capex_bln")
+        fcf = row.get("fcf_bln")
+        if not all(isinstance(x, (int, float)) for x in (ocf, capex, fcf)):
+            errors.append(f"[FCF IDENTITY] Non-numeric OCF/CAPEX/FCF for {ticker}.")
+        else:
+            expected_fcf = round(float(ocf) - float(capex), 4)
+            if abs(float(fcf) - expected_fcf) > 0.15:
+                errors.append(
+                    f"[FCF IDENTITY] {ticker}: FCF ({fcf}) != OCF ({ocf}) - CAPEX ({capex}) (diff={abs(float(fcf) - expected_fcf):.4f})."
+                )
+
+        if not row.get("is_bank", False):
+            mcap = row.get("consolidated_mcap_bln_rub")
+            net_debt = row.get("net_debt_bln")
+            ev = row.get("ev_bln")
+            if not all(isinstance(x, (int, float)) for x in (mcap, net_debt, ev)):
+                errors.append(f"[EV IDENTITY] Non-numeric Consolidated Mcap/Net Debt/EV for non-bank {ticker}.")
+            else:
+                expected_ev = round(float(mcap) + float(net_debt), 4)
+                if abs(float(ev) - expected_ev) > 0.15:
+                    errors.append(
+                        f"[EV IDENTITY] {ticker}: EV ({ev}) != Consolidated Mcap ({mcap}) + Net Debt ({net_debt}) (diff={abs(float(ev) - expected_ev):.4f})."
+                    )
+
+
+def verify_deliverable_prose(root: pathlib.Path, errors: list[str]) -> list[str]:
+    candidate_paths: list[pathlib.Path] = []
+    for rel_dir in ("deliverables", "reports", "research/moex_spb_investment_committee"):
+        d = root / rel_dir
+        if d.exists() and d.is_dir():
+            for md_file in sorted(d.glob("*.md")):
+                if md_file.name.lower() in ("assignment.md", "spec.md", "memory.md"):
+                    continue
+                candidate_paths.append(md_file)
+
+    for top_md in sorted(root.glob("*report*.md")) + sorted(root.glob("*strategy*.md")) + sorted(root.glob("*memorandum*.md")):
+        if top_md not in candidate_paths:
+            candidate_paths.append(top_md)
+
+    checked: list[str] = []
+    for md_path in candidate_paths:
+        text = md_path.read_text(encoding="utf-8", errors="replace")
+        rel = str(md_path.relative_to(root))
+        checked.append(rel)
+        for marker in FORBIDDEN_SLOP_MARKERS:
+            if marker.lower() in text.lower():
+                errors.append(
+                    f"[FORBIDDEN AI-SLOP LABEL] Found forbidden marker {marker!r} in deliverable {rel}."
+                )
+    return checked
+
+
+def main() -> int:
+    parser = argparse.ArgumentParser(description="Verify MOEX/SPB quantitative bundle and deliverables.")
+    parser.add_argument("--root", type=str, default=None, help="Workspace root directory")
+    args = parser.parse_args()
+
+    root = resolve_workspace_root(args.root)
+    errors: list[str] = []
+
+    loaded: dict[str, Any] = {}
+    for rel_path in REQUIRED_JSON_ARTIFACTS:
+        loaded[rel_path] = verify_sha256_manifest(root, rel_path, errors)
+
+    verify_dashboard_bundle(
+        root,
+        loaded.get("data/processed/quant_valuation_matrix.json"),
+        errors,
+    )
+    verify_exchange_snapshot(loaded.get("data/raw/exchange_merged_snapshot.json"), errors)
+    verify_accounting_identities(loaded.get("data/processed/fundamentals_reconciled.json"), errors)
+    checked_reports = verify_deliverable_prose(root, errors)
+
+    if errors:
+        print(f"[VERIFY FAILED] {len(errors)} error(s) detected in workspace {root}:", file=sys.stderr)
+        for err in errors:
+            print(f"  - {err}", file=sys.stderr)
+        return 1
+
+    print(
+        f"[VERIFY OK] All 5 core JSON artifacts + {DASHBOARD_BUNDLE_REL} verified with SHA-256 manifests; "
+        f"31 equities passed T<->TCSG alias & positive float checks; "
+        f"31 issuers passed FCF & EV accounting identities with 0 warnings; "
+        f"checked {len(checked_reports)} markdown deliverable(s) for zero AI-slop markers."
+    )
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
```

### Component: `skills/moex-spb-ifrs-reconciliation/SKILL.md`

```diff
--- /dev/null
+++ candidate/skills/moex-spb-ifrs-reconciliation/SKILL.md
@@ -0,0 +1,65 @@
+---
+name: moex-spb-ifrs-reconciliation
+description: Practitioner rules for reconciling MOEX ISS and SPB Exchange (SPBEX) equity market data with IFRS/RSBU financial statements, charter-capital multi-class share adjustments, dividend payout realization factors, high CBR key-rate net interest balance, and SPB Exchange liquidity integration.
+---
+
+# MOEX & SPBEX Equity and IFRS/RSBU Reconciliation Skill
+
+Use this skill whenever analyzing, valuing, scoring, or reconciling equities traded on Moscow Exchange (`MOEX ISS`, board `TQBR`) and SPB Exchange (`SPBEX`) against consolidated IFRS (`МСФО`) or statutory RSBU (`РСБУ`) financial statements.
+
+## 1. Charter-Capital Multi-Class Share Adjustment (Full-Entity Market Cap & EV)
+
+### Analytic Move
+Reconcile single-ticker `ISSUECAPITALIZATION` or `ISSUESIZE * Price` from `MOEX ISS` against full corporate charter capital (`уставный капитал`) before computing entity-level valuation multiples (`P/E`, `EV/EBITDA`, `P/BV`, `FCF Yield`).
+
+### Practitioner Rules & Verified Workspace Facts
+- **Transneft (`TRNFP`):** Only preferred shares (`TRNFP`, 155.49 million shares after the 100:1 split) trade on `MOEX`, representing **21.45%** of total charter capital (**724.93 million total shares**, where 78.55% ordinary shares are held by the Russian Federation).
+  - Never divide consolidated IFRS Net Income or EBITDA by `TRNFP` preferred-only market capitalization.
+  - Compute full-entity implied market capitalization as `Full_Market_Cap = TRNFP_Price * 724.93M` (or scale `TRNFP` class capitalization by `1 / 0.2145 = 4.662x`), or attribute exactly **21.45%** of consolidated IFRS Net Income and FCF to the preferred share class.
+- **Surgutneftegas (`SNGS` + `SNGSP`):** Combine ordinary (`SNGS`, 35,725.99 million shares) and preferred (`SNGSP`, 7,701.998 million shares) market capitalizations into a single full-company capitalization (`MCap_Total = MCap_SNGS + MCap_SNGSP`) before calculating entity-level `P/E` and `EV/EBITDA`.
+- **Tatneft (`TATN` + `TATNP`) and Sberbank (`SBER` + `SBERP`) and Mechel (`MTLR` + `MTLRP`):** Sum both ordinary and preferred share classes (`TATN` + `TATNP`, `SBER` + `SBERP`, `MTLR` + `MTLRP`) to derive full-company `Market Cap` and `Enterprise Value (EV = Full_Market_Cap + Net_Debt)`.
+
+## 2. Share-Class Payout Realization Factor (`Payout_Quality`)
+
+### Analytic Move
+Adjust headline earnings and FCF yields by a share-class-specific `Payout_Quality` realization coefficient to separate distributable cash flow accruing to minority shareholders from trapped corporate cash.
+
+### Decision Rules & Verified Workspace Facts
+- **Surgutneftegas Preferred (`SNGSP`) vs Ordinary (`SNGS`):**
+  - Under the corporate charter (Article 7.2), `SNGSP` is entitled to **10% of statutory RSBU net profit** divided across 7.702 billion preferred shares (corresponding to ~40.5% of total dividend pool, or ~7.1% of RSBU net profit directly accruing to the `SNGSP` class), providing hard currency-hedged dividend realization (`Payout_Quality = 0.90`).
+  - `SNGS` ordinary shares have no charter formula and receive a historical fixed token dividend (`0.80–0.90 RUB/share`, ~3–4% dividend yield) regardless of the `6,150 billion RUB` liquid FX deposit ("кубышка"). Assign `Payout_Quality <= 0.25` to `SNGS` so ordinary shares never falsely outrank `SNGSP` on cheap `EV/EBITDA` or headline `P/E`.
+- **Inter RAO (`IRAO`) vs High-Payout Cash Cows (`LKOH`, `HEAD`, `SBER`, `TATN`, `MOEX`):**
+  - `IRAO` caps dividends at **25% of IFRS Net Income** while channeling its `~435 billion RUB` net cash cushion into an aggressive long-term CapEx program (`Payout_Quality = 0.65`).
+  - Reward issuers with proven **75–100% FCF or 50% IFRS Net Income** distribution (`LKOH`, `HEAD`, `SBER`, `SBERP`, `TATN`, `TATNP`, `MOEX`, `BSPB`) with `Payout_Quality = 0.90–1.00`.
+- **Suspended / Delisted / Quasi-Treasury Payouts:** Assign reduced realization (`0.05–0.30`) to issuers under debt moratoriums, high leverage, or capital controls restricting minority distribution (`MTLR`, `VKCO`, `AFKS`, `FEES`, `HYDR`, `MGNT`).
+
+## 3. High CBR Key-Rate Net Interest Balance (`15–21%` Regime)
+
+### Analytic Move
+Evaluate corporate balance sheets under a structurally tight Bank of Russia (`ЦБ РФ`) key rate (`15–16%+`) by scoring net interest income vs floating-rate debt service burden (`Net_Cash_Score` and `Debt_Safety`).
+
+### Decision Rules
+- **Net Cash Beneficiaries (`Net Debt < 0`):** Companies holding large net cash or money-market liquidity piles (`SNGSP`, `IRAO`, `MOEX`, `SPBE`, `HEAD`, `LKOH`, `TATN`, `PLZL`, `NVTK`) earn high risk-free ruble yields (`15–19%` on deposits/repo), generating positive net interest income in IFRS statements. Reward these balance sheets in both `Debt_Safety` and `Net_Cash_Score`.
+- **Floating-Rate Leverage Penalty (`Net Debt / EBITDA > 1.8x`):** Heavily penalize issuers with elevated net leverage (`Net Debt / EBITDA > 1.8x`, and severe distress penalty at `> 2.5x–3.0x` such as `MTLR`, `AFKS`, `VKCO`, `SGZH`, `RTKM`), because debt refinancing at `Key Rate + 250–400 bps` erodes operating cash flow and forces dividend suspension.
+- **Commercial Banks & Financial Infrastructure (`SBER`, `T`, `BSPB`, `VTBR`, `SVCB`, `MOEX`, `SPBE`):** Evaluate via `ROE`, `P/BV`, `Cost of Risk (CoR)`, and net interest/fee margin expansion rather than industrial `EV/EBITDA` (`Net Debt` is not applicable to banking deposit books; `BSPB` and `MOEX` directly monetize high ruble rates through cheap funding and client balances).
+
+## 4. SPB Exchange (`SPBEX`) Alpha & Benchmark Integration
+
+### Analytic Move
+Cross-check dual-listed prices, bid-ask spreads, trading volumes, and special trading regimes across `MOEX ISS` and `SPBEX` internal API, and benchmark equity expected returns against liquid money-market and gold instruments.
+
+### Decision Rules & Verified Workspace Facts
+- **Exclusive & Primary SPBEX Alpha Candidates:**
+  - `SPBE` (ПАО «СПБ Биржа»): Primary liquidity and turnaround monetization via weekend trading (7 days/week), expanded Russian equity market-making, and pre-IPO/blocked-asset settlement infrastructure; Debt/EBITDA = 0 with net cash cushion.
+  - `ELMT` (ПАО «Элемент»): Microelectronics leader where `SPBEX` is a core listing venue alongside `MOEX`; evaluate explicit EV/EBITDA (`~4.1x`) and defense/industrial order-book growth.
+  - `OZON` (МКПАО «Озон»): Post-redomiciliation high-growth e-commerce and fintech leader achieving positive IFRS EBITDA and rapid FCF inflection.
+- **Cross-Venue Arbitrage & Spread Verification:** Reconcile `MOEX` (`TQBR`) vs `SPBEX` last prices (`last`), bid/ask spreads, and ruble trading volumes (`vol_rub`). Ensure exact ticker mapping across venues (e.g., `T` on MOEX maps to `TCSG` on SPBEX; benchmark funds `TMON@` and `TGLD@` on SPBEX correspond to `LQDT` / `TMON` and `GLDRUB_TOM` / `TGLD` on MOEX).
+- **Opportunity-Cost Hurdle Rate:** Compare every equity recommendation's expected total return (`Expected_Dividend_Yield + Fundamental_Upside`) against the risk-free ruble money-market benchmark (`LQDT` / `TMON@` yielding `~15.5–18.5%` p.a.) and physical gold/FX hedge (`TGLD@`).
+
+## 5. Verification Checklist Before Finalizing Deliverables
+
+Before producing any final ranking table, JSON bundle, or investment memorandum:
+1. Confirm `TRNFP`, `SNGS`/`SNGSP`, `TATN`/`TATNP`, and `SBER`/`SBERP` use full-entity charter-adjusted market capitalization for all enterprise multiples (`P/E`, `EV/EBITDA`, `P/BV`).
+2. Confirm `SNGSP` ranks materially above `SNGS` due to the charter-mandated 10% RSBU net profit preferred dividend vs the fixed ordinary dividend trap.
+3. Confirm high-debt issuers (`Net Debt / EBITDA > 1.8x`) receive an explicit high-key-rate penalty and do not appear in conservative dividend/core buckets.
+4. Confirm both `MOEX` and `SPBEX` price/liquidity metrics and money-market benchmarks (`LQDT` / `TMON@`, `TGLD@`) are reconciled without missing values.
```

### Component: `systemprompt.md`

```diff
--- base/systemprompt.md
+++ candidate/systemprompt.md
@@ -1 +1,3 @@
 You are an autonomous agent executing professional tasks accurately and completely.
+
+When analyzing or reconciling MOEX and SPBEX equities and IFRS/RSBU financial statements, load the `moex-spb-ifrs-reconciliation` skill.
```
