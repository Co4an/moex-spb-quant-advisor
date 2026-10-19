# Rollout Workspace `base_2`

## Trajectory Notes
# Base Rollout 1 Trajectory Diagnosis (Iteration 2)

## Observed Failure Modes in Iteration 1 Base Harness
1. **Static Macro Prior (19.0% CBR Key Rate) vs Live Central Bank Reality (14.00% on cbr.ru)**:
   - Iteration 1 hardcoded `cbr_key_rate_pct = 19.0` from historical memory instead of querying `https://www.cbr.ru/hd_base/KeyRate/` and `https://www.cbr.ru/scripts/XML_daily.asp`.
   - Live HTML parsing of `cbr.ru/hd_base/KeyRate/` reveals 712 daily observations since 2024: the key rate peaked at `21,00%` on `28.10.2024` and was cut 10 times through 2025–2026 down to `14,00%` (effective since `27.07.2026`, `-700 bps` cumulative easing), while official USD/RUB is `82,8504`.
2. **Absence of Live News & Catalyst Feeds**:
   - Without parsing `iss.moex.com/iss/sitenews.json`, `cbr.ru/rss/eventrss`, and Russian financial media RSS (`news.google.com/rss/search`), the advisor missed critical October 2026 tactical signals: e.g., profit-taking pullback on `PLZL` (19.10.2026), post-dividend gap digestion on `BSPB` (06.10.2026), positive M&A assessment of Tochka Bank consolidation for `T` (`Т-Технологии`), and data-center news dip on `YDEX` (12.10.2026).
3. **Single 12M Horizon Instead of 3-Tier Investment Horizon Matrix**:
   - Retail and institutional investors require explicit holding-period guidance across three distinct windows:
     - `short_1_3m` (1–3 months: winter dividend cutoffs for `LKOH`, `HEAD`, `X5`, `TATN` + entry corridors and stop-review levels),
     - `medium_6_12m` (6–12 months: full 2026 annual dividend season in May–July 2027 + multiple re-rating at CBR 14.0% -> 12.0%),
     - `long_1_3y` (1–3 years: ROE compounding and terminal rate normalization toward 9.5–10.0%).


## Produced Deliverables
_No deliverables produced._

