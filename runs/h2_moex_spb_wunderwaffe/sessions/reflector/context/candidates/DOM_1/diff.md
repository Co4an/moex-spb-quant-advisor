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
