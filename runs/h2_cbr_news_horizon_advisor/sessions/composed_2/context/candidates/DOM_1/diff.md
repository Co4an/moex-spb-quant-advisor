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
