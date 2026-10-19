<notes>
Upgraded `scripts/verify_moex_spb_quant_bundle.py` and `guardrails.md` along the INV dimension to verify all 8 core JSON artifacts (`cbr_macro_live.json`, `market_news_live.json`, `issuer_news_catalysts.json`, etc.), reject hardcoded 19.0% CBR key rate priors in favor of live `cbr.ru` parsing (14.0%), verify >= 25 live news items, and enforce 3-horizon (`short_1_3m`, `medium_6_12m`, `long_1_3y`) advisory schemas across all 31 issuers.
</notes>
