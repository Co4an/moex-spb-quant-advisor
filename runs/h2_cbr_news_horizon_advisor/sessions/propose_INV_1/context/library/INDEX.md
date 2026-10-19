# Continual Improvement Library Index (Domain: `russian_equities_quant_automation`)

Inspect relevant entries on demand. Each entry folder contains:
- `EXPERIENCE.md`: applicable situation (`cue`), transferable operation (`lesson`), and component edit verdicts.
- `harness/`: complete adopted executable harness tree available to copy/adapt into `context/harness/`.

## `entry_001_moex_spb_wunderwaffe` (Task: `moex_spb_wunderwaffe`)
- **Modified Components**: `guardrails.md`, `scripts/verify_moex_spb_quant_bundle.py`, `skills/moex-spb-ifrs-reconciliation/SKILL.md`, `systemprompt.md`
- **Cue**: When building an automated quantitative pipeline and multi-agent investment analysis for Moscow Exchange (MOEX ISS API) and SPB Exchange (spbexchange.ru internal JSON API) equities and IFRS/RSBU financial statements
- **Lesson**: Pair (1) a deterministic bundle verifier in scripts/verify_moex_spb_quant_bundle.py and guardrails.md that checks SPBEX Russian comma-decimal float parsing, MinTsifry TLS context, cross-exchange ticker aliases (T on MOEX vs TCSG on SPBEX), 62 FCF and EV accounting identities, .prov.json SHA-256 manifests, and dashboard/data_bundle.js synchronization with (2) a practitioner reconciliation skill in skills/moex-spb-ifrs-reconciliation/SKILL.md triggered from systemprompt.md that enforces full charter-capital share-class adjustments (TRNFP preferred = 21.45% of 724.93M total shares; SNGS + SNGSP combined market cap) and share-class payout realization factors (SNGSP statutory 10% RSBU profit payout vs SNGS ordinary fixed-dividend trap) under a high CBR key rate.
- **Confidence**: high, because both orthogonal probes independently demonstrated their respective execution improvements and composed cleanly in composed_1.
