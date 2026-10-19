<notes>
## Scoped INV Proposal (`propose_INV_1`)

### 1. Created `context/harness/scripts/verify_moex_spb_quant_bundle.py`
- **Trajectory Motivation (`base_1_trajectory.md`, Step 2 — Инженерно-процедурная проблема INV):** In `base_1`, ingesting quotes from MOEX ISS and SPB Exchange exposed three recurring procedural failure modes: (1) SPB Exchange returns numeric values as strings with Russian decimal commas and uses a Russian National CA certificate, (2) cross-exchange ticker aliases (`T` on MOEX vs. `TCSG` on SPBEX) fail naive 1-to-1 ticker joins, and (3) without an automated bundle verifier, downstream tables (`quant_valuation_matrix.json`, `fundamentals_reconciled.json`, `sector_aggregates.json`, `optimal_portfolios.json`), `.prov.json` SHA-256 manifests, and `dashboard/data_bundle.js` can drift out of sync or leak forbidden meta-labels into markdown deliverables.
- **What it does:** Provides a zero-dependency Python standard-library verifier (`scripts/verify_moex_spb_quant_bundle.py`) that deterministically checks:
  - **(a)** Existence, JSON validity, `.prov.json` SHA-256 cryptographic manifest integrity, and 31-issuer composite score synchronization across `data/raw/exchange_merged_snapshot.json`, `data/processed/fundamentals_reconciled.json`, `data/processed/quant_valuation_matrix.json`, `data/processed/sector_aggregates.json`, `data/processed/optimal_portfolios.json`, and `dashboard/data_bundle.js`.
  - **(b)** Cross-exchange alias mapping (`T` <-> `TCSG`) and SPB comma-float parsing across all 31 equities (`price_rub > 0`, `moex_price_rub > 0`, and positive float `spbex_price_rub`).
  - **(c)** Accounting identities `FCF == OCF - CAPEX` (within 0.15 bln RUB rounding tolerance) for all 31 issuers and `EV == Consolidated Market Cap + Net Debt` for all non-bank issuers, plus zero `reconciliation_warnings`.
  - **(d)** Absence of forbidden AI-slop labels (`SCQA`, `SO WHAT`, `Пирамида Минто`, `Hero KPI`) in deliverable markdown reports.

### 2. Updated `context/harness/guardrails.md`
- **Trajectory Motivation (`base_1_trajectory.md`, Step 2):** Codified the workspace-specific ingestion facts (`T` <-> `TCSG` alias, SPBEX comma-decimal strings, SSL fallback) and added a mandatory pre-completion verification gate requiring `python3 scripts/verify_moex_spb_quant_bundle.py` to exit `0` before finalizing any deliverable. Contains zero Jinja template braces.
</notes>
