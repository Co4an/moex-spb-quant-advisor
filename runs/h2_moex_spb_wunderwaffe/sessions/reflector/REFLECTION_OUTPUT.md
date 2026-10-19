<edits>
component: scripts/verify_moex_spb_quant_bundle.py
candidates: INV_1, composed_1
change: Added deterministic standard-library verifier checking SHA-256 .prov.json manifests, SPBEX comma-decimal float parsing, cross-exchange alias T <-> TCSG, 62 IFRS/RSBU accounting identities, and dashboard/data_bundle.js synchronization.
observed: In probe_INV_1 and composed_1, the verifier caught and confirmed 31/31 positive prices across MOEX and SPBEX, 62/62 accounting checks, and zero AI-slop tokens, whereas base_1 had no bundle verification gate.
verdict: helped

component: guardrails.md
candidates: INV_1, composed_1
change: Required running python3 scripts/verify_moex_spb_quant_bundle.py before task completion and codified SPBEX TLS and comma-decimal ingestion rules.
observed: Triggered execution of verify_moex_spb_quant_bundle.py in probe_INV_1 and composed_1 prior to finalizing deliverables.
verdict: helped

component: skills/moex-spb-ifrs-reconciliation/SKILL.md
candidates: DOM_1, composed_1
change: Added practitioner reconciliation skill for charter-capital share-class adjustments (TRNFP 21.45% preferred share, SNGS+SNGSP combined market cap), payout realization factor, and high CBR key-rate net interest balance.
observed: In probe_DOM_1 and composed_1, eliminated single-class P/E distortion on TRNFP (0.57x -> 2.64x) and separated SNGSP statutory preferred yield (#2, 85.1 pts) from SNGS ordinary shares (#15, 72.1 pts).
verdict: helped

component: systemprompt.md
candidates: DOM_1, composed_1
change: Added trigger line instructing the agent to load moex-spb-ifrs-reconciliation when analyzing MOEX and SPBEX equities and IFRS/RSBU financial statements.
observed: Reliably activated the domain skill in probe_DOM_1 and composed_1.
verdict: helped
</edits>

<experience>
cue: When building an automated quantitative pipeline and multi-agent investment analysis for Moscow Exchange (MOEX ISS API) and SPB Exchange (spbexchange.ru internal JSON API) equities and IFRS/RSBU financial statements
lesson: Pair (1) a deterministic bundle verifier in scripts/verify_moex_spb_quant_bundle.py and guardrails.md that checks SPBEX Russian comma-decimal float parsing, MinTsifry TLS context, cross-exchange ticker aliases (T on MOEX vs TCSG on SPBEX), 62 FCF and EV accounting identities, .prov.json SHA-256 manifests, and dashboard/data_bundle.js synchronization with (2) a practitioner reconciliation skill in skills/moex-spb-ifrs-reconciliation/SKILL.md triggered from systemprompt.md that enforces full charter-capital share-class adjustments (TRNFP preferred = 21.45% of 724.93M total shares; SNGS + SNGSP combined market cap) and share-class payout realization factors (SNGSP statutory 10% RSBU profit payout vs SNGS ordinary fixed-dividend trap) under a high CBR key rate.
evidence: Orthogonal probe rollouts probe_INV_1 and probe_DOM_1 isolated the procedural bundle verification from the charter-capital and payout-realization methodology before composition in composed_1.
confidence: high, because both orthogonal probes independently demonstrated their respective execution improvements and composed cleanly in composed_1.
</experience>
