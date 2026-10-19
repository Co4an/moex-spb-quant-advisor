#!/usr/bin/env python3
"""
Deterministic Quantitative Valuation, Sector Z-Score Normalization,
Live CBR Rate Cycle (14.0%), News Catalyst Integration & Multi-Horizon
Portfolio Optimization Engine for MOEX & SPBEX.

Zero LLM calls: 100% mathematical & financial-engineering calculations.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import pathlib
import statistics
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
DASHBOARD_DIR = ROOT_DIR / "dashboard"


def clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def write_json_with_prov(
    path: pathlib.Path,
    payload: Any,
    derived_from: List[str],
    script_rel: str = "scripts/quant_sector_engine.py",
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(content, encoding="utf-8")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    prov = {
        "schema_name": "scientific-evidence.artifact-manifest",
        "artifact": {
            "path": str(path.relative_to(ROOT_DIR)),
            "kind": "quant_valuation_output",
            "sha256": digest,
        },
        "derived_from": derived_from,
        "generated_by": {
            "script_path": script_rel,
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
    }
    prov_path = path.with_suffix(path.suffix + ".prov.json")
    prov_path.write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")
    return digest


def compute_issuer_scores_and_valuations(
    issuers_map: Dict[str, Dict[str, Any]],
    catalysts_map: Dict[str, Dict[str, Any]],
    cbr_key_rate_pct: float = 14.0,
    ofz_yield_pct: float = 13.4,
) -> Dict[str, Dict[str, Any]]:
    """
    Compute 5-factor scores, 3-scenario intrinsic values (Bear: CBR 16.0%, Base: Live CBR 14.0%, Bull: CBR 11.5%),
    and 3-horizon investment advisory targets (1-3M tactical, 6-12M base, 1-3Y strategic) for all 31 issuers.
    """
    scored: Dict[str, Dict[str, Any]] = {}

    # Cost of equity baseline in RUB: OFZ 10Y yield (~13.4% at RGBI 111.73 & CBR 14.0%) + ERP (5.4%) = 18.8%
    base_coe = (ofz_yield_pct + 5.4) / 100.0

    for ticker, rec in issuers_map.items():
        is_bank = rec["is_bank"]
        price = float(rec["price_rub"] or 0.0)
        pe = rec.get("pe_ratio")
        ev_ebitda = rec.get("ev_ebitda")
        pbv = rec.get("pbv_ratio")
        roe = float(rec.get("roe_pct") or 0.0)
        roic = float(rec.get("roic_pct") or 0.0)
        div_y = float(rec.get("div_yield_pct") or 0.0)
        fcf_y = float(rec.get("fcf_yield_pct") or 0.0)
        nd_ebitda = float(rec.get("net_debt_to_ebitda") or 0.0)
        net_cash_mcap = float(rec.get("net_cash_to_mcap_pct") or 0.0)
        rev_g = float(rec.get("revenue_growth_yoy_pct") or 0.0)
        ebitda_m = float(rec.get("ebitda_margin_pct") or 0.0)
        vol_ann = float(rec.get("volatility_ann_pct") or 30.0)

        cat_info = catalysts_map.get(ticker, {})
        news_sent = float(cat_info.get("news_sentiment_score") or 0.0)
        news_count = int(cat_info.get("news_mentions_count") or 0)
        interim_div_3m = float(cat_info.get("interim_div_yield_1_3m_pct") or 0.0)

        # Share-class payout realization factor (differentiates SNGSP statutory payout vs SNGS ordinary trap,
        # and IRAO 25% cap vs LKOH/HEAD 80-100% FCF distribution)
        if ticker == "SNGS":
            payout_realization = 0.42  # Ordinary shares do not participate in cash-pile interest distribution
        elif ticker == "IRAO":
            payout_realization = 0.74  # 25% payout cap + rising power-generation CAPEX
        elif ticker == "SPBE":
            payout_realization = 0.76  # Cash retained for exchange infrastructure growth
        else:
            payout_realization = 1.0

        # 1. Valuation Score (0..100)
        if is_bank:
            justified_pbv = max(0.38, (roe / 100.0 - 0.06) / (base_coe - 0.06))
            actual_pbv = float(pbv or 1.0)
            pbv_discount = (justified_pbv / actual_pbv - 1.0) * 100.0
            pe_score = clamp(100.0 - ((float(pe or 6.0) - 2.3) * 11.2), 15.0, 96.0)
            pbv_score = clamp(54.0 + pbv_discount * 0.82, 15.0, 96.0)
            score_val = round(0.55 * pe_score + 0.45 * pbv_score, 1)
        else:
            eff_ev = float(ev_ebitda if ev_ebitda is not None else 5.0)
            eff_pe = float(pe if (pe is not None and pe > 0) else 14.0)
            fair_ev_mult = clamp(3.75 + max(0.0, rev_g) * 0.085 + max(0.0, roic - 14.0) * 0.045, 3.2, 7.8)
            ev_score = clamp(64.0 + (fair_ev_mult - eff_ev) * 12.2, 10.0, 96.0)
            pe_score = clamp(94.0 - (eff_pe - 3.3) * 6.0, 10.0, 96.0)
            score_val = round((0.60 * ev_score + 0.40 * pe_score) * (0.75 + 0.25 * payout_realization), 1)

        # 2. Cash & Dividend Yield Score vs 13.4% OFZ / 14.0% Key Rate (0..100)
        effective_cash_yield = 0.68 * div_y + 0.32 * max(0.0, fcf_y * payout_realization)
        score_yield = round(clamp(26.0 + (effective_cash_yield / ofz_yield_pct) * 52.0, 8.0, 97.0), 1)

        # 3. CBR Rate Cycle (14.0%) Immunity & Balance Sheet Fortress Score (0..100)
        # Corporate floating debt still costs KS + 2.5..3.5% = 16.5-17.5% at 14% key rate!
        if is_bank:
            n1 = float(rec.get("capital_adequacy_n1_pct") or 11.5)
            nim = float(rec.get("nim_pct") or 5.0)
            cor = float(rec.get("cost_of_risk_pct") or 1.5)
            score_rate = round(
                clamp(38.0 + (n1 - 9.5) * 4.6 + (nim - 3.0) * 4.2 - cor * 2.8, 15.0, 95.0),
                1,
            )
        else:
            if nd_ebitda <= 0:
                cash_bonus = min(35.0, math.sqrt(max(0.0, net_cash_mcap * payout_realization)) * 3.35)
                score_rate = round(clamp(61.0 + cash_bonus, 58.0, 98.0), 1)
            else:
                flt_pen = (float(rec.get("floating_debt_share_pct") or 25.0) / 100.0) * 13.5
                score_rate = round(clamp(72.0 - nd_ebitda * 16.0 - flt_pen, 10.0, 75.0), 1)

        # 4. Business Quality, Margin & Growth Score (0..100)
        score_qual = round(
            clamp(
                22.0
                + min(31.0, roe * 0.82)
                + min(23.0, ebitda_m * 0.40)
                + clamp(rev_g * 0.82, -10.0, 22.0),
                15.0,
                97.0,
            ),
            1,
        )

        # 5. Momentum, Cross-Exchange Liquidity & Live News Catalyst Score (0..100)
        ret_90d = float(rec.get("return_90d_pct") or 0.0)
        ytd_ret = float(rec.get("ytd_2026_return_pct") or 0.0)
        turnover_mln = float(rec.get("total_turnover_mln_rub") or 1.0)
        liq_bonus = min(23.0, math.log10(max(1.0, turnover_mln)) * 5.8)
        dual_bonus = 5.0 if len(rec.get("exchanges_traded", [])) >= 2 else 2.5
        news_catalyst_adj = clamp(news_sent * 11.0 + (3.5 if interim_div_3m >= 4.0 else 0.0), -9.0, 11.0)
        score_mom = round(
            clamp(41.0 + ret_90d * 0.58 + ytd_ret * 0.22 + liq_bonus + dual_bonus + news_catalyst_adj, 15.0, 95.0),
            1,
        )

        # Composite Multi-Factor Score (0..100)
        composite_score = round(
            0.25 * score_val
            + 0.25 * score_yield
            + 0.25 * score_rate
            + 0.15 * score_qual
            + 0.10 * score_mom,
            1,
        )

        # 3-Scenario Intrinsic Valuation Model anchored at Live CBR 14.0%
        # Base: Live CBR 14.0% (gradual transition toward 12.0-12.5%)
        # Bull: Accelerated Easing to 11.5%
        # Bear: Pro-inflationary Shock / Pause-Hike to 16.0%
        if is_bank:
            target_pbv_base = clamp((roe / 100.0 - 0.055) / (base_coe - 0.055), 0.42, 1.85)
            actual_pbv = float(pbv or 1.0)
            mult_upside = (target_pbv_base / actual_pbv - 1.0) * 100.0
            div_re_rating = (div_y - 10.8) * 1.25
            raw_upside_base_pct = 0.60 * mult_upside + 0.40 * div_re_rating
        else:
            target_ev_mult = clamp(3.55 + max(0.0, rev_g) * 0.08 + max(0.0, roic - 14.0) * 0.04, 3.0, 7.6)
            eff_ev = float(ev_ebitda if ev_ebitda is not None else 5.0)
            ev_upside = (target_ev_mult / max(1.25, eff_ev) - 1.0) * 100.0
            realized_cash_yield = (
                div_y * 0.65
                + max(0.0, fcf_y) * 0.35
                + min(80.0, max(0.0, net_cash_mcap)) * 0.085 * payout_realization
            )
            fcf_target_upside = (realized_cash_yield / 12.8 - 1.0) * 31.0
            raw_upside_base_pct = (0.52 * ev_upside + 0.48 * fcf_target_upside) * payout_realization

        if raw_upside_base_pct >= 0:
            upside_base_pct = round(48.0 * math.tanh(raw_upside_base_pct / 52.0), 1)
        else:
            upside_base_pct = round(25.0 * math.tanh(raw_upside_base_pct / 28.0), 1)

        # Bull scenario (Key Rate cut to 11.5%, ERP compression)
        rate_beta = 1.25 if nd_ebitda > 1.0 else (0.95 if not is_bank else 1.15)
        upside_bull_pct = round(upside_base_pct + 17.5 * rate_beta, 1)
        # Bear scenario (Key Rate hike back to 16.0%, ruble & credit stress)
        bear_drop = 11.5 if net_cash_mcap > 20.0 else (25.0 if nd_ebitda > 1.5 else 17.5)
        upside_bear_pct = round(upside_base_pct - bear_drop, 1)

        prec = 4 if price < 5 else 2
        fair_price_base = round(price * (1.0 + upside_base_pct / 100.0), prec)
        fair_price_bull = round(price * (1.0 + upside_bull_pct / 100.0), prec)
        fair_price_bear = round(price * (1.0 + upside_bear_pct / 100.0), prec)
        expected_12m_total_return_pct = round(upside_base_pct + div_y, 1)

        # Deterministic Recommendation Tier
        if composite_score >= 73.5 and expected_12m_total_return_pct >= 32.0:
            recommendation = "ТОП-ИДЕЯ (ПОКУПАТЬ)"
            tier_code = "TOP_BUY"
        elif composite_score >= 65.0 and expected_12m_total_return_pct >= 22.0:
            recommendation = "ПОКУПАТЬ"
            tier_code = "BUY"
        elif composite_score >= 51.0:
            recommendation = "ДЕРЖАТЬ"
            tier_code = "HOLD"
        else:
            recommendation = "ИЗБЕГАТЬ"
            tier_code = "AVOID"

        # =========================================================================
        # Multi-Horizon Investment Advisor Calculations (1-3M, 6-12M, 1-3Y)
        # =========================================================================
        # 1) Short-Term Tactical Horizon (1-3 Months: Q4 2026 - Q1 2027)
        # Accounts for winter dividend cutoffs, technical pullback alerts (e.g. PLZL Oct 19),
        # and news catalysts.
        if ticker == "PLZL":
            # Oct 19 news: profit-taking pullback after gold rally -> accumulate on dip
            entry_lo = round(price * 0.935, prec)
            entry_hi = round(price * 0.985, prec)
            tactical_upside_1_3m_pct = round(upside_base_pct * 0.28 + interim_div_3m * 0.45, 1)
            tactical_stance = "Набирать траншами на техническом откате"
        elif interim_div_3m >= 4.5:
            # Strong winter dividend cutoff catalyst (LKOH, HEAD, X5, TATN)
            entry_lo = round(price * 0.975, prec)
            entry_hi = round(price * 1.01, prec)
            tactical_upside_1_3m_pct = round(upside_base_pct * 0.34 + interim_div_3m * 0.65, 1)
            tactical_stance = f"Активно покупать под зимнюю отсечку (ДД ~{interim_div_3m:.1f}%)"
        elif tier_code == "AVOID":
            entry_lo = round(price * 0.85, prec)
            entry_hi = round(price * 0.90, prec)
            tactical_upside_1_3m_pct = round(min(2.5, upside_base_pct * 0.35 + news_sent * 4.0), 1)
            tactical_stance = "Избегать / Сокращать на локальных отскоках"
        elif news_sent < -0.15 and tier_code in {"TOP_BUY", "BUY"}:
            # High-quality stock on temporary news dip (e.g. YDEX, BSPB post-gap)
            entry_lo = round(price * 0.955, prec)
            entry_hi = round(price * 0.995, prec)
            tactical_upside_1_3m_pct = round(upside_base_pct * 0.32 + 2.5, 1)
            tactical_stance = "Тактический подбор на новостной / дивидендной просадке"
        else:
            entry_lo = round(price * 0.965, prec)
            entry_hi = round(price * 1.005, prec)
            tactical_upside_1_3m_pct = round(upside_base_pct * 0.30 + news_sent * 3.0, 1)
            tactical_stance = (
                "Плановый набор в базовое ядро" if tier_code in {"TOP_BUY", "BUY"} else "Удерживать / Нейтрально"
            )

        target_1_3m_rub = round(price * (1.0 + tactical_upside_1_3m_pct / 100.0), prec)
        total_ret_1_3m_pct = round(tactical_upside_1_3m_pct + interim_div_3m, 1)
        stop_review_rub = round(price * (1.0 - clamp(vol_ann / 310.0, 0.075, 0.135)), prec)

        # 2) Long-Term Strategic Horizon (1-3 Years: 2026-2029)
        # Models earnings/book value compounding + terminal CBR key rate normalization toward 9.5-10.0%
        payout_est = clamp(div_y / max(4.0, (100.0 / float(pe)) if (pe and pe > 0) else 15.0), 0.0, 0.90)
        retained_roe_annual = max(0.02, (roe / 100.0) * (1.0 - payout_est * 0.65))
        compounding_2y_extra = ((1.0 + min(0.22, retained_roe_annual)) ** 2 - 1.0) * 100.0
        if tier_code == "AVOID":
            compounding_2y_extra = max(-10.0, compounding_2y_extra * 0.35 - 8.0)

        upside_3y_price_pct = round(upside_bull_pct * 0.85 + compounding_2y_extra, 1)
        target_1_3y_rub = round(price * (1.0 + upside_3y_price_pct / 100.0), prec)
        cum_div_3y_pct = round(div_y * 3.15 * payout_realization, 1)
        cum_total_ret_3y_pct = round(upside_3y_price_pct + cum_div_3y_pct, 1)
        cagr_3y_pct = round(((max(0.2, 1.0 + cum_total_ret_3y_pct / 100.0) ** (1.0 / 3.0)) - 1.0) * 100.0, 1)

        if roe >= 24.0 and tier_code in {"TOP_BUY", "BUY"}:
            long_stance = "Стратегический компаундер (Удерживать 1–3 года)"
        elif div_y >= 13.5 and tier_code in {"TOP_BUY", "BUY"}:
            long_stance = "Дивидендный фундамент и защита капитала (1–3 года)"
        elif tier_code == "HOLD":
            long_stance = "Циклический актив (Пересмотр через 6–12 мес.)"
        else:
            long_stance = "Структурный аутсайдер (Не для долгосрочного портфеля)"

        horizons_matrix = {
            "short_1_3m": {
                "horizon_label": "1–3 месяца (Тактический / Под отсечки и новости)",
                "entry_zone_rub": [entry_lo, entry_hi],
                "entry_zone_str": f"{entry_lo}–{entry_hi}",
                "target_price_rub": target_1_3m_rub,
                "price_upside_pct": tactical_upside_1_3m_pct,
                "interim_div_yield_pct": interim_div_3m,
                "expected_total_return_pct": total_ret_1_3m_pct,
                "stop_review_rub": stop_review_rub,
                "stance": tactical_stance,
            },
            "medium_6_12m": {
                "horizon_label": "6–12 месяцев (Базовый / Годовой дивидендный цикл и ставка ЦБ 14% → 12%)",
                "target_price_rub": fair_price_base,
                "price_upside_pct": upside_base_pct,
                "expected_div_yield_pct": div_y,
                "expected_total_return_pct": expected_12m_total_return_pct,
                "stance": recommendation,
            },
            "long_1_3y": {
                "horizon_label": "1–3 года (Стратегический / Капитализация ROE и ставка ЦБ → 9,5–10%)",
                "target_price_3y_rub": target_1_3y_rub,
                "price_upside_3y_pct": upside_3y_price_pct,
                "cumulative_div_yield_3y_pct": cum_div_3y_pct,
                "cumulative_total_return_3y_pct": cum_total_ret_3y_pct,
                "expected_cagr_3y_pct": cagr_3y_pct,
                "stance": long_stance,
            },
        }

        enriched = dict(rec)
        enriched.update({
            "score_valuation": score_val,
            "score_yield": score_yield,
            "score_rate_immunity": score_rate,
            "score_quality": score_qual,
            "score_momentum_liquidity": score_mom,
            "composite_score": composite_score,
            "fair_price_base_rub": fair_price_base,
            "fair_price_bull_rub": fair_price_bull,
            "fair_price_bear_rub": fair_price_bear,
            "upside_base_pct": upside_base_pct,
            "upside_bull_pct": upside_bull_pct,
            "upside_bear_pct": upside_bear_pct,
            "expected_12m_total_return_pct": expected_12m_total_return_pct,
            "recommendation": recommendation,
            "tier_code": tier_code,
            # News & Horizon Advisor Fields
            "news_mentions_count": news_count,
            "news_sentiment_score": news_sent,
            "top_headlines": cat_info.get("top_headlines", []),
            "next_catalyst_date": cat_info.get("next_catalyst_date", "IV кв. 2026 – I полугодие 2027 г."),
            "dividend_frequency": cat_info.get("dividend_frequency", "1–2 раза в год"),
            "interim_div_yield_1_3m_pct": interim_div_3m,
            "upcoming_catalyst_ru": cat_info.get("upcoming_catalyst_ru", ""),
            "optimal_horizon_code": cat_info.get("optimal_horizon_code", "medium_6_12m"),
            "optimal_horizon_label": cat_info.get("optimal_horizon_label", "6–12 месяцев"),
            "recommended_holding_months": cat_info.get("recommended_holding_months", "6–12 мес."),
            "horizons": horizons_matrix,
        })
        scored[ticker] = enriched

    # Compute Within-Sector Z-Scores & Ranks
    by_sector: Dict[str, List[Dict[str, Any]]] = {}
    for item in scored.values():
        by_sector.setdefault(item["sector"], []).append(item)

    for sec_name, members in by_sector.items():
        members.sort(key=lambda x: x["composite_score"], reverse=True)
        scores = [m["composite_score"] for m in members]
        mean_s = statistics.mean(scores)
        std_s = statistics.stdev(scores) if len(scores) > 1 else 5.0
        for idx, m in enumerate(members, start=1):
            z = (m["composite_score"] - mean_s) / max(std_s, 1.0)
            m["sector_rank"] = f"{idx}/{len(members)}"
            m["sector_z_score"] = round(z, 2)

    # Global rank across all 31 equities
    all_sorted = sorted(
        scored.values(),
        key=lambda x: (x["composite_score"], x["expected_12m_total_return_pct"]),
        reverse=True,
    )
    for rank_i, item in enumerate(all_sorted, start=1):
        item["global_rank"] = rank_i

    return {item["ticker"]: item for item in all_sorted}


def compute_sector_aggregates(scored_issuers: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_sector: Dict[str, List[Dict[str, Any]]] = {}
    for rec in scored_issuers.values():
        by_sector.setdefault(rec["sector"], []).append(rec)

    sector_rows: List[Dict[str, Any]] = []
    for sec_name, items in by_sector.items():
        total_mcap = sum(float(x["consolidated_mcap_bln_rub"] or 0.0) for x in items)
        total_rev = sum(float(x["revenue_bln"] or 0.0) for x in items)
        total_ebitda = sum(float(x["ebitda_bln"] or 0.0) for x in items)
        total_ni = sum(float(x["net_income_bln"] or 0.0) for x in items)
        total_fcf = sum(float(x["fcf_bln"] or 0.0) for x in items)
        total_net_debt = sum(float(x["net_debt_bln"] or 0.0) for x in items)

        pes = [float(x["pe_ratio"]) for x in items if x.get("pe_ratio") and x["pe_ratio"] > 0]
        evs = [float(x["ev_ebitda"]) for x in items if x.get("ev_ebitda") and x["ev_ebitda"] > 0]
        divs = [float(x["div_yield_pct"]) for x in items]
        roes = [float(x["roe_pct"]) for x in items]
        scores = [float(x["composite_score"]) for x in items]
        tot_rets = [float(x["expected_12m_total_return_pct"]) for x in items]
        cagrs_3y = [float(x["horizons"]["long_1_3y"]["expected_cagr_3y_pct"]) for x in items]

        best_pick = max(items, key=lambda x: (x["composite_score"], x["expected_12m_total_return_pct"]))
        avoid_pick = min(items, key=lambda x: x["composite_score"])

        avg_score = round(statistics.mean(scores), 1)
        if avg_score >= 67.5:
            sec_stance = "ПЕРЕВЕС (Фаворит рынка)"
        elif avg_score >= 62.0:
            sec_stance = "НЕЙТРАЛЬНО / ТОЧЕЧНЫЙ ОТБОР"
        else:
            sec_stance = "НЕДОВЕС (Высокая чувствительность к долгу)"

        sector_rows.append({
            "sector": sec_name,
            "companies_count": len(items),
            "tickers": [x["ticker"] for x in items],
            "total_mcap_bln_rub": round(total_mcap, 1),
            "total_revenue_bln_rub": round(total_rev, 1),
            "total_ebitda_bln_rub": round(total_ebitda, 1),
            "total_net_income_bln_rub": round(total_ni, 1),
            "total_fcf_bln_rub": round(total_fcf, 1),
            "total_net_debt_bln_rub": round(total_net_debt, 1),
            "median_pe": round(statistics.median(pes), 2) if pes else None,
            "median_ev_ebitda": round(statistics.median(evs), 2) if evs else None,
            "avg_div_yield_pct": round(statistics.mean(divs), 2),
            "avg_roe_pct": round(statistics.mean(roes), 1),
            "avg_composite_score": avg_score,
            "avg_expected_12m_return_pct": round(statistics.mean(tot_rets), 1),
            "avg_expected_3y_cagr_pct": round(statistics.mean(cagrs_3y), 1),
            "top_pick_ticker": best_pick["ticker"],
            "top_pick_name": best_pick["short_name"],
            "top_pick_score": best_pick["composite_score"],
            "top_pick_return_pct": best_pick["expected_12m_total_return_pct"],
            "top_pick_horizon": best_pick["recommended_holding_months"],
            "laggard_ticker": avoid_pick["ticker"],
            "sector_stance": sec_stance,
        })

    sector_rows.sort(key=lambda x: x["avg_composite_score"], reverse=True)
    return sector_rows


def build_optimal_portfolios(
    scored_issuers: Dict[str, Dict[str, Any]],
    exchange_snapshot: Dict[str, Any],
    base_capital_rub: float = 1_000_000.0,
) -> Dict[str, Any]:
    """Construct 4 institutional model portfolios across MOEX & SPBEX with exact lot allocation and multi-horizon roadmaps."""
    etfs = exchange_snapshot.get("spbex_etf_benchmarks", {})
    cbr_rate = float(exchange_snapshot.get("macro_market_pulse", {}).get("cbr_key_rate_pct") or 14.0)
    mm_yield = round(cbr_rate - 0.25, 2)  # ~13.75% money market yield at 14.0% CBR key rate
    tmon_price = float(etfs.get("TMON@", {}).get("price") or 148.48)
    tgld_price = float(etfs.get("TGLD@", {}).get("price") or 11.67)

    portfolio_specs: List[Dict[str, Any]] = [
        {
            "id": "core_alpha",
            "name": "Флагманский: Ядро Альфа + Денежные кубышки (MOEX + SPBEX)",
            "target_investor": "Оптимальное сочетание фундаментальной недооценки, денежных подушек (Net Cash) и дивидендов при ставке ЦБ 14%",
            "risk_level": "Умеренный (Sharpe-оптимизированный)",
            "recommended_horizon": "6–18 месяцев (Базовое ядро с ребалансировкой раз в квартал под дивидендные отсечки)",
            "rebalance_schedule": "Декабрь 2026 (зимние дивиденды LKOH/HEAD/X5) → Май–Июль 2027 (годовой дивидендный сезон)",
            "positions": [
                {"ticker": "BSPB", "weight_pct": 15.0, "exchange": "MOEX", "role": "Лидер рейтинга: P/E 2,09x, Н1.0 = 19,8%, ДД 21,2%"},
                {"ticker": "SNGSP", "weight_pct": 15.0, "exchange": "MOEX / SPBEX", "role": "Валютно-депозитная кубышка 6,15 трлн руб. с уставным дивидендом 21,1%"},
                {"ticker": "TRNFP", "weight_pct": 13.0, "exchange": "MOEX / SPBEX", "role": "Тарифная монополия с полным уставным P/E 2,64x и ДД 17,7%"},
                {"ticker": "LKOH", "weight_pct": 12.0, "exchange": "MOEX / SPBEX", "role": "Экспортёр с чистым кэшем 1,15 трлн руб. и декабрьской отсечкой (~7,8%)"},
                {"ticker": "HEAD", "weight_pct": 11.0, "exchange": "MOEX / SPBEX", "role": "IT-монополия с рентабельностью EBITDA 58,9%, нулевым долгом и ДД 17,0%"},
                {"ticker": "MOEX", "weight_pct": 10.0, "exchange": "MOEX / SPBEX", "role": "Инфраструктурный бенефициар роста оборотов при ставке ЦБ 14% (ROE 36,9%)"},
                {"ticker": "IRAO", "weight_pct": 9.0, "exchange": "MOEX / SPBEX", "role": "Денежная кубышка 477 млрд руб. (176,5% капитализации), отрицательный EV"},
                {"ticker": "X5", "weight_pct": 9.0, "exchange": "MOEX / SPBEX", "role": "Лидер продуктового ритейла после редомициляции (P/E 4,62x, спецдивиденд)"},
                {"ticker": "TMON@", "weight_pct": 6.0, "exchange": "SPBEX / MOEX", "role": f"Ликвидный резерв денежного рынка под ~{mm_yield}% годовых для докупки на откатах", "is_etf": True, "price_rub": tmon_price, "div_yield_pct": mm_yield, "expected_12m_total_return_pct": mm_yield, "expected_1_3m_return_pct": round(mm_yield / 4.0, 2), "expected_3y_cagr_pct": 11.5, "recommended_holding_months": "1–6 мес. (кэш-буфер)"},
            ],
        },
        {
            "id": "dividend_rentier",
            "name": "Дивидендный рантье (Максимальный денежный поток при ставке ЦБ 14%)",
            "target_investor": "Инвесторы, формирующие регулярный пассивный поток дивидендов существенно выше ставок по банковским вкладам (13–14%)",
            "risk_level": "Консервативно-доходный",
            "recommended_horizon": "3–12 месяцев (Захват зимнего дивидендного сезона дек. 2026 – янв. 2027 и летнего сезона май – июль 2027)",
            "rebalance_schedule": "Ротация части прибыли из зимних отсечек (LKOH, TATN, X5, HEAD) в весенне-летние годовые выплаты (SNGSP, TRNFP, BSPB, SBER)",
            "positions": [
                {"ticker": "BSPB", "weight_pct": 17.0, "exchange": "MOEX", "role": "Рекордная достаточность капитала Н1.0 = 19,8% и полугодовые/годовые дивиденды ~21,2%"},
                {"ticker": "SNGSP", "weight_pct": 18.0, "exchange": "MOEX / SPBEX", "role": "Уставные 10% чистой прибыли РСБУ от валютно-процентной кубышки"},
                {"ticker": "TRNFP", "weight_pct": 15.0, "exchange": "MOEX / SPBEX", "role": "Квазиоблигационный денежный поток с индексацией тарифов с 1 января"},
                {"ticker": "LKOH", "weight_pct": 15.0, "exchange": "MOEX / SPBEX", "role": "Двукратные выплаты из FCF (ближайшая отсечка в декабре 2026 г.)"},
                {"ticker": "HEAD", "weight_pct": 12.0, "exchange": "MOEX / SPBEX", "role": "Высокая конверсия выручки в дивиденды без капитальных затрат"},
                {"ticker": "TATN", "weight_pct": 11.0, "exchange": "MOEX / SPBEX", "role": "Трёхкратные дивиденды (за 6М, 9М и 12М) и чистый кэш 107 млрд руб."},
                {"ticker": "X5", "weight_pct": 12.0, "exchange": "MOEX / SPBEX", "role": "Распределение накопленного кэша после редомициляции + регулярный дивиденд"},
            ],
        },
        {
            "id": "tech_spb_growth",
            "name": "Технологический рост и СПБ-альфа (Бенефициары цикла снижения ставки ЦБ 14% → 11,5%)",
            "target_investor": "Ориентация на максимальный прирост капитала на горизонте 1–3 лет за счет ИИ, финтеха и эксклюзивных бумаг СПБ Биржи",
            "risk_level": "Повышенный (Рост и венчурно-индустриальная альфа)",
            "recommended_horizon": "1–3 года (Стратегическое удержание под полное раскрытие ROE и снижение ставки ЦБ к 10–11,5%)",
            "rebalance_schedule": "Полугодовая ребалансировка; использование новостных просадок (YDEX, OZON) для наращивания долей",
            "positions": [
                {"ticker": "HEAD", "weight_pct": 19.0, "exchange": "MOEX / SPBEX", "role": "Рентабельность EBITDA 58,9%, ROE 89,7% и дивидендный поток ~17%"},
                {"ticker": "MOEX", "weight_pct": 18.0, "exchange": "MOEX / SPBEX", "role": "Рост комиссионных оборотов фондового и срочного рынков при ставке 14%"},
                {"ticker": "YDEX", "weight_pct": 16.0, "exchange": "MOEX / SPBEX", "role": "Флагман ИИ и облачных сервисов (покупка на октябрьской новостной просадке)"},
                {"ticker": "ELMT", "weight_pct": 14.0, "exchange": "SPBEX / MOEX", "role": "Первичный листинг СПБ Биржи: лидер микроэлектроники по P/E 5,50x и EV/EBITDA 1,73x"},
                {"ticker": "T", "weight_pct": 13.0, "exchange": "SPBEX (TCSG) / MOEX", "role": "Финтех-экосистема с ROE 31,2% и синергией от консолидации Точка Банка"},
                {"ticker": "OZON", "weight_pct": 11.0, "exchange": "SPBEX / MOEX", "role": "Высокая ликвидность на СПБ Бирже и взрывной рост финтех-вертикали Ozon Банка"},
                {"ticker": "SPBE", "weight_pct": 9.0, "exchange": "SPBEX", "role": "ПАО «СПБ Биржа»: чистый кэш 14,5 млрд руб. (53% капитализации) и торги 7 дней в неделю"},
            ],
        },
        {
            "id": "fx_commodity_shield",
            "name": "Валютный и сырьевой щит (Защита от ослабления рубля с 82,85 к 92–98 руб./долл.)",
            "target_investor": "Хеджирование валютных и геополитических рисков через золото, удобрения, нефть и морской танкерный флот",
            "risk_level": "Умеренно-защитный (Валютный хедж)",
            "recommended_horizon": "6–24 месяца (Хеджирование валютного курса и сырьевого суперцикла)",
            "rebalance_schedule": "Покупка Полюса (PLZL) траншами на технических откатах (сигнал 19.10.2026); удержание SNGSP и LKOH через дивидендные отсечки",
            "positions": [
                {"ticker": "SNGSP", "weight_pct": 20.0, "exchange": "MOEX / SPBEX", "role": "Прямая переоценка валютной кубышки 6,15 трлн руб. в дивидендную базу"},
                {"ticker": "LKOH", "weight_pct": 18.0, "exchange": "MOEX / SPBEX", "role": "Нефтяной экспортёр с чистым валютным кэшем 1,15 трлн руб."},
                {"ticker": "PLZL", "weight_pct": 16.0, "exchange": "MOEX / SPBEX", "role": "Золотодобытчик №1 с маржой EBITDA 68,5% (набор на октябрьской коррекции)"},
                {"ticker": "TATN", "weight_pct": 14.0, "exchange": "MOEX / SPBEX", "role": "Высокая глубина нефтепереработки и трёхкратные дивиденды"},
                {"ticker": "FLOT", "weight_pct": 12.0, "exchange": "MOEX / SPBEX", "role": "Долларовый танкерный фрахт с чистым кэшем и ДД 15,9%"},
                {"ticker": "PHOR", "weight_pct": 11.0, "exchange": "MOEX / SPBEX", "role": "Экспортёр фосфорных удобрений с ROE 48,1% и FCF 109 млрд руб."},
                {"ticker": "TGLD@", "weight_pct": 9.0, "exchange": "SPBEX / MOEX", "role": "Биржевое золото в рублях на СПБ Бирже без корпоративного риска", "is_etf": True, "price_rub": tgld_price, "div_yield_pct": 0.0, "expected_12m_total_return_pct": 23.5, "expected_1_3m_return_pct": 5.8, "expected_3y_cagr_pct": 17.5, "recommended_holding_months": "12–36 мес. (золотой буфер)"},
            ],
        },
    ]

    built_portfolios: List[Dict[str, Any]] = []
    for p_spec in portfolio_specs:
        enriched_pos: List[Dict[str, Any]] = []
        w_ret_12m = 0.0
        w_ret_1_3m = 0.0
        w_cagr_3y = 0.0
        w_div = 0.0
        w_score = 0.0
        w_pe_num = 0.0
        w_pe_den = 0.0

        for pos in p_spec["positions"]:
            t = pos["ticker"]
            w = float(pos["weight_pct"]) / 100.0
            alloc_rub = round(base_capital_rub * w, 2)

            if pos.get("is_etf"):
                price = float(pos["price_rub"])
                lot_size = 1
                lot_cost = price
                lots = int(alloc_rub // lot_cost) if lot_cost > 0 else 0
                div_y = float(pos.get("div_yield_pct", 0.0))
                tot_ret_12m = float(pos.get("expected_12m_total_return_pct", mm_yield))
                ret_1_3m = float(pos.get("expected_1_3m_return_pct", 3.5))
                cagr_3y = float(pos.get("expected_3y_cagr_pct", 12.0))
                rec_months = str(pos.get("recommended_holding_months", "1–6 мес."))
                score = 78.0
                name = "БПИФ Т-Капитал Денежный рынок" if t == "TMON@" else "БПИФ Т-Капитал Золото"
                sector = "Ликвидность / Биржевые фонды"
            else:
                rec = scored_issuers[t]
                price = float(rec["price_rub"])
                lot_size = int(rec["lot_size"])
                lot_cost = float(rec["lot_cost_rub"])
                lots = int(alloc_rub // lot_cost) if lot_cost > 0 else 0
                div_y = float(rec["div_yield_pct"])
                tot_ret_12m = float(rec["expected_12m_total_return_pct"])
                ret_1_3m = float(rec["horizons"]["short_1_3m"]["expected_total_return_pct"])
                cagr_3y = float(rec["horizons"]["long_1_3y"]["expected_cagr_3y_pct"])
                rec_months = str(rec.get("recommended_holding_months", "6–12 мес."))
                score = float(rec["composite_score"])
                name = rec["short_name"]
                sector = rec["sector"]
                if rec.get("pe_ratio") and rec["pe_ratio"] > 0:
                    w_pe_num += w
                    w_pe_den += w / float(rec["pe_ratio"])

            w_ret_12m += w * tot_ret_12m
            w_ret_1_3m += w * ret_1_3m
            w_cagr_3y += w * cagr_3y
            w_div += w * div_y
            w_score += w * score

            enriched_pos.append({
                "ticker": t,
                "name": name,
                "sector": sector,
                "exchange": pos["exchange"],
                "weight_pct": pos["weight_pct"],
                "target_allocation_rub": alloc_rub,
                "price_rub": price,
                "lot_size": lot_size,
                "lot_cost_rub": round(lot_cost, 2),
                "recommended_lots_per_1m": lots,
                "actual_invested_rub": round(lots * lot_cost, 2),
                "div_yield_pct": round(div_y, 2),
                "expected_div_cashflow_rub": round(alloc_rub * div_y / 100.0, 0),
                "expected_1_3m_return_pct": round(ret_1_3m, 1),
                "expected_12m_return_pct": round(tot_ret_12m, 1),
                "expected_3y_cagr_pct": round(cagr_3y, 1),
                "recommended_holding_months": rec_months,
                "composite_score": round(score, 1),
                "role": pos["role"],
            })

        harmonic_pe = round(w_pe_num / w_pe_den, 2) if w_pe_den > 0 else 4.8
        built_portfolios.append({
            "id": p_spec["id"],
            "name": p_spec["name"],
            "target_investor": p_spec["target_investor"],
            "risk_level": p_spec["risk_level"],
            "recommended_horizon": p_spec["recommended_horizon"],
            "rebalance_schedule": p_spec["rebalance_schedule"],
            "base_capital_rub": base_capital_rub,
            "expected_1_3m_total_return_pct": round(w_ret_1_3m, 2),
            "expected_12m_total_return_pct": round(w_ret_12m, 2),
            "expected_3y_cagr_pct": round(w_cagr_3y, 2),
            "expected_portfolio_div_yield_pct": round(w_div, 2),
            "expected_annual_div_rub_per_1m": round(base_capital_rub * w_div / 100.0, 0),
            "weighted_composite_score": round(w_score, 1),
            "harmonic_pe_ratio": harmonic_pe,
            "positions": enriched_pos,
        })

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cbr_key_rate_pct": cbr_rate,
        "base_capital_rub": base_capital_rub,
        "portfolios": built_portfolios,
    }


def compute_strategy_ablations(
    scored_issuers: Dict[str, Dict[str, Any]],
    ofz_yield_pct: float = 13.4,
) -> Dict[str, Any]:
    """
    Controlled Baselines & Single-Factor Ablations for Sova Heavy Algorithmic Core verification.
    Compares the Full 5-Factor Rate- & News-Adjusted Wunderwaffe (at Live CBR 14.0%) against 6 baselines/ablations.
    """
    items = list(scored_issuers.values())

    def eval_basket(selected: List[Dict[str, Any]], label: str, kind: str, description: str) -> Dict[str, Any]:
        ret = statistics.mean(x["expected_12m_total_return_pct"] for x in selected)
        ret_3m = statistics.mean(x["horizons"]["short_1_3m"]["expected_total_return_pct"] for x in selected)
        cagr_3y = statistics.mean(x["horizons"]["long_1_3y"]["expected_cagr_3y_pct"] for x in selected)
        div_y = statistics.mean(x["div_yield_pct"] for x in selected)
        fcf_y = statistics.mean(x["fcf_yield_pct"] for x in selected)
        vol = statistics.mean(x["volatility_ann_pct"] for x in selected)
        rate_imm = statistics.mean(x["score_rate_immunity"] for x in selected)
        # Risk-adjusted excess return over live OFZ 13.4% yield (Composite Utility Metric)
        sharpe_proxy = (ret - ofz_yield_pct) / max(vol, 15.0) * 100.0
        composite_utility = round(0.50 * ret + 0.30 * sharpe_proxy + 0.20 * (rate_imm * 0.35), 2)
        return {
            "id": label,
            "kind": kind,
            "description": description,
            "tickers": [x["ticker"] for x in selected],
            "expected_1_3m_return_pct": round(ret_3m, 2),
            "expected_12m_return_pct": round(ret, 2),
            "expected_3y_cagr_pct": round(cagr_3y, 2),
            "avg_div_yield_pct": round(div_y, 2),
            "avg_fcf_yield_pct": round(fcf_y, 2),
            "avg_volatility_pct": round(vol, 2),
            "avg_rate_immunity_score": round(rate_imm, 1),
            "sharpe_excess_proxy": round(sharpe_proxy, 2),
            "composite_utility_score": composite_utility,
        }

    # 1. Incumbent: Top-8 by Full 5-Factor Rate- & News-Adjusted Score (Live CBR 14.0%)
    top8_full = sorted(items, key=lambda x: x["composite_score"], reverse=True)[:8]
    incumbent = eval_basket(
        top8_full,
        "incumbent_5factor_rate_adjusted",
        "incumbent",
        "Полная 5-факторная модель с живой ставкой ЦБ 14,0%, поправкой на уставный капитал, новостными катализаторами и 3 горизонтами (MOEX + SPBEX)",
    )

    # 2. Baseline 1: Equal-Weight Universe (All 31 equities)
    b_equal = eval_basket(
        items,
        "baseline_equal_weight_universe",
        "baseline",
        "Равновзвешенный индекс всех 31 эмитентов без факторного и новостного отбора",
    )

    # 3. Baseline 2: Market-Cap Top-8 (Passive Index Heavyweights)
    top8_mcap = sorted(items, key=lambda x: x["consolidated_mcap_bln_rub"], reverse=True)[:8]
    b_mcap = eval_basket(
        top8_mcap,
        "baseline_mcap_top8",
        "baseline",
        "Пассивный портфель 8 крупнейших компаний по капитализации (вкл. Газпром и Роснефть)",
    )

    # 4. Ablation 1: Remove Rate-Immunity Factor (Rate-Blind Valuation + Yield only)
    top8_no_rate = sorted(
        items,
        key=lambda x: 0.45 * x["score_valuation"] + 0.35 * x["score_yield"] + 0.20 * x["score_quality"],
        reverse=True,
    )[:8]
    a_no_rate = eval_basket(
        top8_no_rate,
        "ablation_no_rate_immunity",
        "ablation",
        "Абляция без фактора процентного баланса (игнорирование долговой нагрузки и денежных кубышек)",
    )

    # 5. Ablation 2: Naive Multiples Only (Raw P/E without Quality or FCF check)
    valid_pe = [x for x in items if x.get("pe_ratio") and x["pe_ratio"] > 0]
    top8_naive_pe = sorted(valid_pe, key=lambda x: x["pe_ratio"])[:8]
    a_naive_pe = eval_basket(
        top8_naive_pe,
        "ablation_naive_pe_only",
        "ablation",
        "Абляция только по минимальному P/E (попадание в долговые ловушки и неликвидные обыкновенные акции)",
    )

    # 6. Ablation 3: MOEX-Only (Excluding SPBEX primary/alpha opportunities)
    moex_only_pool = [
        x for x in items if x["primary_exchange"] == "MOEX" and x["ticker"] not in {"OZON", "ELMT", "SPBE"}
    ]
    top8_moex_only = sorted(moex_only_pool, key=lambda x: x["composite_score"], reverse=True)[:8]
    a_moex_only = eval_basket(
        top8_moex_only,
        "ablation_moex_only_no_spbex",
        "ablation",
        "Абляция без эмитентов и кросс-ликвидности СПБ Биржи (исключение ELMT, SPBE, OZON)",
    )

    # 7. Ablation 4: News- & Catalyst-Blind Selection (Ignoring interim cutoffs and news sentiment)
    top8_no_news = sorted(
        items,
        key=lambda x: 0.50 * x["score_quality"] + 0.50 * (100.0 - x["volatility_ann_pct"]),
        reverse=True,
    )[:8]
    a_no_news = eval_basket(
        top8_no_news,
        "ablation_no_news_and_catalysts",
        "ablation",
        "Абляция без учета новостного сентимента, календаря зимних отсечек и горизонтов инвестирования",
    )

    all_variants = [incumbent, b_equal, b_mcap, a_no_rate, a_naive_pe, a_moex_only, a_no_news]
    for v in all_variants:
        v["delta_vs_incumbent"] = round(v["composite_utility_score"] - incumbent["composite_utility_score"], 2)

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cbr_key_rate_pct": 14.0,
        "ofz_yield_pct": ofz_yield_pct,
        "incumbent_id": incumbent["id"],
        "incumbent_score": incumbent["composite_utility_score"],
        "variants": all_variants,
    }


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    fund_path = PROCESSED_DIR / "fundamentals_reconciled.json"
    exch_path = RAW_DIR / "exchange_merged_snapshot.json"
    cat_path = PROCESSED_DIR / "issuer_news_catalysts.json"
    news_path = RAW_DIR / "market_news_live.json"

    fund_data = json.loads(fund_path.read_text(encoding="utf-8"))
    exch_data = json.loads(exch_path.read_text(encoding="utf-8"))
    cat_data = json.loads(cat_path.read_text(encoding="utf-8")) if cat_path.exists() else {"issuers": {}}
    news_data = json.loads(news_path.read_text(encoding="utf-8")) if news_path.exists() else {"news_items": []}

    cbr_rate = float(
        exch_data.get("macro_market_pulse", {}).get("cbr_key_rate_pct")
        or fund_data.get("cbr_key_rate_assumption_pct")
        or 14.0
    )
    ofz_yield = 13.4  # Implied 10Y OFZ yield at RGBI = 111.73 & CBR Key Rate = 14.0%

    scored_issuers = compute_issuer_scores_and_valuations(
        fund_data["issuers"],
        cat_data.get("issuers", {}),
        cbr_key_rate_pct=cbr_rate,
        ofz_yield_pct=ofz_yield,
    )
    sector_agg = compute_sector_aggregates(scored_issuers)
    portfolios_data = build_optimal_portfolios(scored_issuers, exch_data)
    ablations_data = compute_strategy_ablations(scored_issuers, ofz_yield_pct=ofz_yield)

    # Save processed JSON artifacts with SHA-256 provenance manifests
    val_matrix_payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cbr_key_rate_pct": cbr_rate,
        "cbr_scenario_rates_pct": exch_data.get("macro_market_pulse", {}).get(
            "cbr_scenario_rates_pct",
            {"bear_hawkish": 16.0, "base_live_cbr": 14.0, "bull_easing": 11.5},
        ),
        "ofz_benchmark_yield_pct": ofz_yield,
        "issuers_count": len(scored_issuers),
        "top_picks": [
            x["ticker"] for x in scored_issuers.values() if x["tier_code"] in {"TOP_BUY", "BUY"}
        ],
        "avoid_list": [
            x["ticker"] for x in scored_issuers.values() if x["tier_code"] == "AVOID"
        ],
        "issuers": scored_issuers,
    }
    write_json_with_prov(
        PROCESSED_DIR / "quant_valuation_matrix.json",
        val_matrix_payload,
        [
            "@evidence[[data/processed/fundamentals_reconciled.json]]",
            "@evidence[[data/processed/issuer_news_catalysts.json]]",
        ],
    )

    write_json_with_prov(
        PROCESSED_DIR / "sector_aggregates.json",
        {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "sectors": sector_agg},
        ["@evidence[[data/processed/quant_valuation_matrix.json]]"],
    )

    write_json_with_prov(
        PROCESSED_DIR / "optimal_portfolios.json",
        portfolios_data,
        [
            "@evidence[[data/processed/quant_valuation_matrix.json]]",
            "@evidence[[data/raw/exchange_merged_snapshot.json]]",
        ],
    )

    write_json_with_prov(
        PROCESSED_DIR / "strategy_ablations.json",
        ablations_data,
        ["@evidence[[data/processed/quant_valuation_matrix.json]]"],
    )

    # Build standalone JS payload for dashboard/index.html so it works without CORS even on file://
    dashboard_bundle = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "macro_pulse": exch_data["macro_market_pulse"],
        "sector_indices": exch_data["sector_indices"],
        "spbex_etfs": exch_data["spbex_etf_benchmarks"],
        "cbr_key_rate_pct": cbr_rate,
        "ofz_yield_pct": ofz_yield,
        "sectors": sector_agg,
        "issuers": list(scored_issuers.values()),
        "portfolios": portfolios_data["portfolios"],
        "ablations": ablations_data["variants"],
        "live_news": news_data.get("news_items", [])[:45],
    }
    js_path = DASHBOARD_DIR / "data_bundle.js"
    js_content = "window.WUNDERWAFFE_DATA = " + json.dumps(dashboard_bundle, ensure_ascii=False, indent=2) + ";\n"
    js_path.write_text(js_content, encoding="utf-8")

    top5 = list(scored_issuers.values())[:5]
    print(
        f"[OK] Computed 5-factor scores, news catalysts & 3-horizon valuations (CBR Key Rate = {cbr_rate:.2f}%) "
        f"for {len(scored_issuers)} issuers across {len(sector_agg)} sectors."
    )
    print("     Top 5 Quantitative Picks:")
    for item in top5:
        h = item["horizons"]
        print(
            f"       #{item['global_rank']} {item['ticker']:6s} ({item['short_name']:14s}) | "
            f"Score={item['composite_score']:4.1f} | Price={item['price_rub']} | "
            f"1-3M: +{h['short_1_3m']['expected_total_return_pct']}% | "
            f"6-12M: +{item['expected_12m_total_return_pct']}% | "
            f"3Y CAGR: +{h['long_1_3y']['expected_cagr_3y_pct']}%/yr | "
            f"Horizon: {item['recommended_holding_months']}"
        )


if __name__ == "__main__":
    main()
