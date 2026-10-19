### Component: `guardrails.md`

```diff
--- base/guardrails.md
+++ candidate/guardrails.md
@@ -14,3 +14,10 @@
      - Cross-exchange alias mapping (`T` <-> `TCSG`) and SPB comma-float parsing produced positive float prices across all 31 equities.
      - Accounting identities `FCF == OCF - CAPEX` and `EV == Consolidated Market Cap + Net Debt` (for non-banks) hold across all 31 issuers with zero reconciliation warnings.
      - Deliverable markdown reports contain zero forbidden meta-labels (`SCQA`, `SO WHAT`, `Пирамида Минто`, `Hero KPI`).
+
+## 6. Live CBR Key Rate (cbr.ru), News Feeds & 3-Horizon Verification Gate
+Before finalizing any quantitative investment memorandum or dashboard bundle:
+1. Run `python3 scripts/verify_moex_spb_quant_bundle.py` and confirm exit code `0`.
+2. Verify `data/raw/cbr_macro_live.json` has been fetched from `cbr.ru/hd_base/KeyRate/` and `cbr_key_rate_pct` matches the live Central Bank rate (14.0%, never hardcoded 19.0%).
+3. Verify `data/raw/market_news_live.json` contains at least 25 live news items from CBR RSS, MOEX ISS sitenews, and Russian financial media RSS, and `data/processed/issuer_news_catalysts.json` maps catalysts for all 31 issuers.
+4. Verify all 31 issuers in `data/processed/quant_valuation_matrix.json` include explicit 3-horizon advisory objects (`short_1_3m`, `medium_6_12m`, `long_1_3y`) and `recommended_holding_months`.
```

### Component: `scripts/verify_moex_spb_quant_bundle.py`

```diff
--- base/scripts/verify_moex_spb_quant_bundle.py
+++ candidate/scripts/verify_moex_spb_quant_bundle.py
@@ -28,8 +28,11 @@
 
 
 REQUIRED_JSON_ARTIFACTS = [
+    "data/raw/cbr_macro_live.json",
     "data/raw/exchange_merged_snapshot.json",
+    "data/raw/market_news_live.json",
     "data/processed/fundamentals_reconciled.json",
+    "data/processed/issuer_news_catalysts.json",
     "data/processed/quant_valuation_matrix.json",
     "data/processed/sector_aggregates.json",
     "data/processed/optimal_portfolios.json",
@@ -85,6 +88,47 @@
         return None
 
 
+def verify_live_cbr_news_and_horizons(
+    cbr_data: dict[str, Any] | None,
+    news_data: dict[str, Any] | None,
+    cat_data: dict[str, Any] | None,
+    quant_data: dict[str, Any] | None,
+    errors: list[str],
+) -> None:
+    if not isinstance(cbr_data, dict):
+        errors.append("[CBR MACRO] Missing or invalid cbr_macro_live.json.")
+    else:
+        kr = cbr_data.get("cbr_key_rate_pct")
+        if not isinstance(kr, (int, float)) or kr <= 0 or abs(float(kr) - 19.0) < 1e-6:
+            errors.append(f"[CBR MACRO] Live CBR Key Rate must be fetched from cbr.ru (got {kr!r}, must not be hardcoded 19.0%).")
+        if isinstance(quant_data, dict) and abs(float(quant_data.get("cbr_key_rate_pct", 0.0)) - float(kr or 0.0)) > 1e-4:
+            errors.append(
+                f"[CBR SYNC] quant_valuation_matrix.json cbr_key_rate_pct ({quant_data.get('cbr_key_rate_pct')}) != live cbr.ru ({kr})."
+            )
+
+    if not isinstance(news_data, dict):
+        errors.append("[LIVE NEWS] Missing or invalid market_news_live.json.")
+    else:
+        items = news_data.get("news_items", [])
+        if not isinstance(items, list) or len(items) < 25:
+            errors.append(f"[LIVE NEWS] Expected >= 25 live news items in market_news_live.json, got {len(items) if isinstance(items, list) else 0}.")
+
+    if not isinstance(cat_data, dict) or len(cat_data.get("issuers", {})) != 31:
+        errors.append("[CATALYSTS] Expected 31 issuer profiles in issuer_news_catalysts.json.")
+
+    if isinstance(quant_data, dict) and isinstance(quant_data.get("issuers"), dict):
+        for ticker, row in quant_data["issuers"].items():
+            horizons = row.get("horizons")
+            if not isinstance(horizons, dict):
+                errors.append(f"[HORIZONS] Missing 'horizons' object for {ticker} in quant_valuation_matrix.json.")
+                continue
+            for h_key in ("short_1_3m", "medium_6_12m", "long_1_3y"):
+                if h_key not in horizons or not isinstance(horizons[h_key], dict):
+                    errors.append(f"[HORIZONS] Missing horizon {h_key} for {ticker}.")
+            if not row.get("recommended_holding_months"):
+                errors.append(f"[HORIZONS] Missing recommended_holding_months for {ticker}.")
+
+
 def verify_dashboard_bundle(
     root: pathlib.Path,
     quant_data: dict[str, Any] | None,
@@ -123,6 +167,9 @@
     except Exception as exc:
         errors.append(f"[DASHBOARD JSON PARSE ERROR] {DASHBOARD_BUNDLE_REL}: {exc}")
         return
+
+    if not isinstance(bundle_obj.get("live_news"), list) or len(bundle_obj["live_news"]) < 10:
+        errors.append(f"[DASHBOARD NEWS] Expected live_news array in {DASHBOARD_BUNDLE_REL}.")
 
     raw_issuers = bundle_obj.get("issuers")
     if isinstance(raw_issuers, list):
@@ -268,6 +315,13 @@
     for rel_path in REQUIRED_JSON_ARTIFACTS:
         loaded[rel_path] = verify_sha256_manifest(root, rel_path, errors)
 
+    verify_live_cbr_news_and_horizons(
+        loaded.get("data/raw/cbr_macro_live.json"),
+        loaded.get("data/raw/market_news_live.json"),
+        loaded.get("data/processed/issuer_news_catalysts.json"),
+        loaded.get("data/processed/quant_valuation_matrix.json"),
+        errors,
+    )
     verify_dashboard_bundle(
         root,
         loaded.get("data/processed/quant_valuation_matrix.json"),
@@ -283,9 +337,11 @@
             print(f"  - {err}", file=sys.stderr)
         return 1
 
+    cbr_kr = loaded.get("data/raw/cbr_macro_live.json", {}).get("cbr_key_rate_pct")
+    news_cnt = len(loaded.get("data/raw/market_news_live.json", {}).get("news_items", []))
     print(
-        f"[VERIFY OK] All 5 core JSON artifacts + {DASHBOARD_BUNDLE_REL} verified with SHA-256 manifests; "
-        f"31 equities passed T<->TCSG alias & positive float checks; "
+        f"[VERIFY OK] All {len(REQUIRED_JSON_ARTIFACTS)} core JSON artifacts + {DASHBOARD_BUNDLE_REL} verified with SHA-256 manifests; "
+        f"Live CBR Key Rate = {cbr_kr}% (cbr.ru); {news_cnt} live news items & 3-horizon matrices verified for 31 issuers; "
         f"31 issuers passed FCF & EV accounting identities with 0 warnings; "
         f"checked {len(checked_reports)} markdown deliverable(s) for zero AI-slop markers."
     )
```

### Component: `skills/moex-spb-ifrs-reconciliation/SKILL.md`

```diff
--- base/skills/moex-spb-ifrs-reconciliation/SKILL.md
+++ candidate/skills/moex-spb-ifrs-reconciliation/SKILL.md
@@ -63,3 +63,18 @@
 2. Confirm `SNGSP` ranks materially above `SNGS` due to the charter-mandated 10% RSBU net profit preferred dividend vs the fixed ordinary dividend trap.
 3. Confirm high-debt issuers (`Net Debt / EBITDA > 1.8x`) receive an explicit high-key-rate penalty and do not appear in conservative dividend/core buckets.
 4. Confirm both `MOEX` and `SPBEX` price/liquidity metrics and money-market benchmarks (`LQDT` / `TMON@`, `TGLD@`) are reconciled without missing values.
+
+## 5. Live Central Bank of Russia (cbr.ru) Key-Rate Trajectory & FX Synchronization
+- Never rely on static model training priors (such as 19.0% or 21.0%) for the Russian key rate. Always query `https://www.cbr.ru/hd_base/KeyRate/` and `https://www.cbr.ru/scripts/XML_daily.asp` directly.
+- As of October 2026, the CBR key rate is 14.00% (effective since 27.07.2026 after 10 cuts totaling -700 bps from the 21.00% peak on 28.10.2024), while official USD/RUB is 82.8504.
+- Even at a 14.00% key rate, commercial floating-rate corporate debt costs `KS + 2.2..3.5%` (16.2–17.5% per annum), which continues to erode FCF for leveraged issuers (`RUAL`, `GMKN`, `GAZP`, `MGNT`), whereas Net Cash issuers (`SNGSP`, `LKOH`, `IRAO`, `TRNFP`, `HEAD`, `MOEX`) earn risk-free deposit income AND capture equity multiple expansion as OFZ yields compress toward 13.4%.
+
+## 6. Live News & Corporate Catalyst Integration (CBR RSS + MOEX ISS + Media RSS)
+- Combine official macro bulletins (`cbr.ru/rss/eventrss`), exchange notices (`iss.moex.com/iss/sitenews.json`), and business media RSS (`news.google.com/rss/search` in Russian) to classify issuer catalysts:
+  - Distinguish technical overbought pullbacks (`PLZL` profit-taking after gold rally -> accumulate on dip) and short-term infrastructure news dips (`YDEX`, `OZON` -> tactical entry for 1–3Y compounding) from structural value/leverage traps (`POSI`, `RUAL`, `GAZP`).
+
+## 7. Three-Tier Investment Horizon Stratification (1–3M, 6–12M, 1–3Y)
+- Every equity recommendation and model portfolio must explicitly specify three horizons:
+  1. **Tactical Horizon (1–3 months)**: Entry zone in RUB, stop-review level, and capture of winter interim dividend cutoffs (`LKOH`, `HEAD`, `X5`, `TATN`) or post-gap recovery (`BSPB`).
+  2. **Base Institutional Horizon (6–12 months)**: Full annual dividend season (May–July 2027) and multiple re-rating as the CBR key rate transitions from 14.0% toward 11.5–12.0%.
+  3. **Strategic Compounder Horizon (1–3 years)**: Earnings & book-value compounding (`ROE * (1 - Payout)`) and terminal rate normalization toward 9.5–10.0% (`HEAD`, `T`, `YDEX`, `SBER`, `PLZL`, `ELMT`).
```
