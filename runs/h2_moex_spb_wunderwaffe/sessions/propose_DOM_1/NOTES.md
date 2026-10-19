<notes>
### DOM Proposal (`propose_DOM_1`): Russian Equity & IFRS/RSBU Practitioner Reconciliation (`moex-spb-ifrs-reconciliation`)

1. **Trajectory Motivation (`base_1` Step 2 — DOM Methodological Distortion):**
   - In `base_1`, naive single-class `ISSUECAPITALIZATION` from `MOEX ISS` distorted `P/E` and `EV/EBITDA` for issuers where only preferred shares trade (`TRNFP`, representing 21.45% of 724.93M total charter shares) or where dual share classes (`SNGS` + `SNGSP`, `TATN` + `TATNP`, `SBER` + `SBERP`) split corporate equity.
   - Without a share-class payout realization factor (`Payout_Quality`), `SNGS` ordinary shares (fixed ~0.90 RUB dividend trap) could receive the same valuation and cash-pile score as `SNGSP` preferred shares (entitled by corporate charter to 10% of RSBU net profit, ~40.5% of total dividends), and capped-payout cash piles (`IRAO` at 25% of IFRS net income) were not distinguished from 80–100% FCF distributors (`LKOH`, `HEAD`).

2. **Changes Made to `context/harness/`:**
   - Created `context/harness/skills/moex-spb-ifrs-reconciliation/SKILL.md` encoding checkable practitioner rules and verified workspace facts for:
     (a) **Charter-Capital Multi-Class Share Adjustment:** Full-entity market cap reconstruction for `TRNFP` (`21.45%` of `724.93M` total shares), `SNGS` + `SNGSP`, `TATN` + `TATNP`, `SBER` + `SBERP`, and `MTLR` + `MTLRP`.
     (b) **Share-Class Payout Realization Factor (`Payout_Quality`):** Explicit separation between `SNGSP` (`0.90` realization via statutory 10% RSBU net profit charter clause) and `SNGS` (`<= 0.25` ordinary dividend trap), plus differentiation of `IRAO` (`25%` cap) vs `LKOH`/`HEAD`/`SBER`/`BSPB` (`75–100%` FCF / `50%` IFRS payout).
     (c) **High CBR Key-Rate Net Interest Balance:** Rewarding net-cash interest earners (`Net Debt < 0`) and penalizing floating-rate leverage (`Net Debt / EBITDA > 1.8x`) under the 15–16%+ key rate regime.
     (d) **SPB Exchange (`SPBEX`) Alpha & Benchmark Integration:** Incorporating `SPBE`, `ELMT`, and `OZON` alongside cross-venue spread/volume reconciliation (`T` vs `TCSG`) and risk-free money-market (`LQDT` / `TMON@`) and gold (`TGLD@`) hurdle benchmarks.
   - Updated `context/harness/systemprompt.md` with the exact skill trigger line:
     `When analyzing or reconciling MOEX and SPBEX equities and IFRS/RSBU financial statements, load the \`moex-spb-ifrs-reconciliation\` skill.`
</notes>
