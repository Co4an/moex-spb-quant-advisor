<edits>
component: scripts/verify_moex_spb_quant_bundle.py
candidates: INV_1, INV_2, composed_1, composed_2
change: Expanded the deterministic verification script to validate all 8 core JSON artifacts (`cbr_macro_live.json`, `market_news_live.json`, `issuer_news_catalysts.json`, etc.), reject hardcoded 19.0% CBR key-rate priors, verify >= 25 live news items, and enforce 3-horizon (`short_1_3m`, `medium_6_12m`, `long_1_3y`) advisory schemas across all 31 issuers.
observed: In probe_INV_1 and composed_1 trajectories, running `verify_moex_spb_quant_bundle.py` caught stale macro assumptions and verified 13 SHA-256 provenance manifests plus 3-horizon structures with 0 errors.
verdict: helped

component: guardrails.md
candidates: INV_1, INV_2, composed_1, composed_2
change: Added mandatory pre-delivery execution of `verify_moex_spb_quant_bundle.py` with live CBR key-rate and 3-horizon advisory checks.
observed: Enforced deterministic verification of live macro and news catalyst bundles before deliverable generation in composed_1.
verdict: confounded

component: skills/moex-spb-ifrs-reconciliation/SKILL.md
candidates: DOM_1, DOM_2, composed_1, composed_2
change: Added Practitioner Rules 5, 6, and 7 covering live CBR key-rate trajectory and FX synchronization from `cbr.ru`, live corporate news catalyst vs structural deterioration classification, and 3-tier investment horizon stratification (`1-3M` tactical, `6-12M` base, `1-3Y` strategic compounders).
observed: In probe_DOM_1 and composed_1, the solver stratified all 31 issuers and 4 model portfolios across 1-3M, 6-12M, and 1-3Y horizons and integrated live CBR 14.00% rate and 120 news items into the valuation model.
verdict: helped
</edits>

<experience>
cue: When building or updating a quantitative equity valuation and investment advisory pipeline where macroeconomic rates, FX, corporate news catalysts, and investment horizons affect target prices and portfolio recommendations.
lesson: In `skills/moex-spb-ifrs-reconciliation/SKILL.md` and `scripts/verify_moex_spb_quant_bundle.py`, never hardcode static macro rate priors (such as an outdated CBR key rate); always parse the live central bank rate table (`cbr.ru/hd_base/KeyRate/`) and live news feeds (`MOEX ISS`, `CBR RSS`, media RSS), stratify recommendations into three explicit horizons (`1-3M` tactical entry zones & dividend cutoffs, `6-12M` base annual cycle, `1-3Y` ROE compounders), and enforce an automated verifier check that rejects stale macro rates and missing horizon fields.
evidence: Rests on `scripts/verify_moex_spb_quant_bundle.py` (`helped` in `probe_INV_1` and `composed_1`) and `skills/moex-spb-ifrs-reconciliation/SKILL.md` (`helped` in `probe_DOM_1` and `composed_1`), where replacing the static 19% rate prior with live `14.00%` CBR parsing and 3-horizon stratification eliminated macro staleness across all 31 issuers.
confidence: high, because both isolated probe runs (`probe_INV_1`, `probe_DOM_1`) and the composed rollout (`composed_1`) deterministically verified all 8 artifacts and 31 3-horizon issuer profiles with 0 errors.
</experience>
