# Probe Rollout Trajectory (probe_INV_1)

1. Verified `cbr_macro_live.json` (`key_rate_pct = 14.0%`, effective `27.07.2026`, `USD/RUB = 82.8504`).
2. Verified `market_news_live.json` (`120` live news items from CBR RSS, MOEX ISS, and Russian business media RSS) and `issuer_news_catalysts.json` (`31` issuers with 3-horizon roadmaps).
3. Executed `python3 scripts/verify_moex_spb_quant_bundle.py` -> `STATUS: PASSED (0 errors)`.
4. Confirmed 3-horizon advisory structure (`short_1_3m`, `medium_6_12m`, `long_1_3y`) across all 31 equities and 4 portfolios.
