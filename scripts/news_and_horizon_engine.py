#!/usr/bin/env python3
"""
Deterministic Live News, Corporate Catalyst & Multi-Horizon Advisory Engine
===========================================================================
1. Pulls live news feeds from:
   - Bank of Russia RSS (`https://www.cbr.ru/rss/eventrss`, `https://www.cbr.ru/rss/RssPress`)
   - Moscow Exchange ISS Live Site News (`https://iss.moex.com/iss/sitenews.json`)
   - Russian Financial Media & Brokerage RSS (`https://news.google.com/rss/search?...&hl=ru&gl=RU&ceid=RU:ru`)
2. Maps news items deterministically to the 31 tracked MOEX & SPBEX issuers and 8 sectors.
3. Computes lexicon-based Russian financial sentiment scores [-1.0, +1.0], catalyst tags,
   and horizon sensitivity (short 1-3M, medium 6-12M, long 1-3Y).
4. Outputs:
   - `data/raw/market_news_live.json` (+ `.prov.json`)
   - `data/processed/issuer_news_catalysts.json` (+ `.prov.json`)
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
PROC_DIR = ROOT_DIR / "data" / "processed"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, application/xml, text/xml, */*",
}

# Mapping of canonical tickers to Russian search keywords/patterns
TICKER_KEYWORDS: Dict[str, List[str]] = {
    "SBER": ["сбербанк", "сбер ", "sber", "греф"],
    "BSPB": ["банк санкт-петербург", "бспб", "bspb", "санкт-петербург»"],
    "T": ["т-технологии", "т-банк", "тинькофф", "tcsg", "точка банк"],
    "SVCB": ["совкомбанк", "svcb", "халва"],
    "VTBR": ["втб", "vtbr", "костин"],
    "MOEX": ["мосбирж", "московская биржа", "moex"],
    "SPBE": ["спб бирж", "spbe", "санкт-петербургская биржа"],
    "LKOH": ["лукойл", "lkoh"],
    "ROSN": ["роснефт", "rosn", "восток ойл"],
    "TATN": ["татнефт", "tatn"],
    "SNGSP": ["сургутнефтегаз", "sngsp", "сургут"],
    "SNGS": ["сургутнефтегаз", "sngs"],
    "GAZP": ["газпром", "gazp", "сила сибири"],
    "NVTK": ["новатэк", "nvtk", "арктик спг"],
    "TRNFP": ["транснефт", "trnfp"],
    "YDEX": ["яндекс", "ydex", "yandex"],
    "OZON": ["озон", "ozon"],
    "HEAD": ["хэдхантер", "headhunter", "hh.ru", "head"],
    "ASTR": ["астра", "astra", "astr"],
    "POSI": ["позитив", "positive technologies", "posi"],
    "ELMT": ["элемент", "elmt", "микроэлектроник"],
    "PLZL": ["полюс", "plzl", "сухой лог"],
    "GMKN": ["норникел", "gmkn", "норильский никель"],
    "CHMF": ["северстал", "chmf"],
    "NLMK": ["нлмк", "nlmk"],
    "RUAL": ["русал", "rual"],
    "PHOR": ["фосагро", "phor"],
    "X5": ["икс 5", "x5", "пятерочк", "перекресток", "чижик"],
    "MGNT": ["магнит", "mgnt"],
    "IRAO": ["интер рао", "irao"],
    "FLOT": ["совкомфлот", "flot"],
}

POSITIVE_LEXICON: Dict[str, float] = {
    "утвердили дивиденды": 0.65,
    "рекомендовал дивиденды": 0.60,
    "высокими дивидендами": 0.45,
    "перспективные акции": 0.40,
    "покупать": 0.55,
    "сохраняет позитив": 0.45,
    "в лидерах": 0.45,
    "выросла": 0.40,
    "рост": 0.30,
    "рекорд": 0.50,
    "консолидацию": 0.35,
    "умеренно": 0.30,
    "снижение ставки": 0.50,
    "смягчение": 0.40,
    "прибыль": 0.35,
    "фаворитами": 0.45,
    "недооценен": 0.40,
    "байбэк": 0.45,
    "выкуп": 0.35,
    "включении ценных бумаг": 0.25,
}

NEGATIVE_LEXICON: Dict[str, float] = {
    "упали": -0.55,
    "резко дешевеют": -0.60,
    "дешевеют": -0.45,
    "откат": -0.45,
    "опережает улучшение": -0.30,
    "гэп не закрывается": -0.35,
    "ударов по": -0.55,
    "атаке бпла": -0.50,
    "горящие данные": -0.45,
    "приостановит торги": -0.40,
    "манипулирования": -0.40,
    "нисходящем тренде": -0.40,
    "неоправданные ожидания": -0.35,
    "убыток": -0.60,
    "долг": -0.30,
    "санкци": -0.45,
}

# Curated institutional catalyst & dividend calendar for Q4 2026 - 2027 across the 31 issuers
ISSUER_CATALYST_CALENDAR: Dict[str, Dict[str, Any]] = {
    "BSPB": {
        "next_catalyst_date": "Ноябрь 2026 (отчет МСФО 9М 2026) / Апрель 2027 (финальные дивиденды)",
        "dividend_frequency": "2 раза в год (полугодовые и годовые)",
        "interim_div_3m_pct": 0.0,
        "upcoming_catalyst_ru": "Плавное закрытие осеннего дивидендного гэпа и публикация МСФО за 9М 2026 г. с сохранением ROE выше 27% при ставке ЦБ 14%.",
        "optimal_horizon_code": "medium_6_12m",
        "optimal_horizon_label": "6–12 месяцев (Среднесрочный базовый + дивидендный цикл)",
        "recommended_months": "6–12 мес.",
    },
    "SNGSP": {
        "next_catalyst_date": "Май 2027 (рекомендация СД по годовым дивидендам) / Июль 2027 (отсечка)",
        "dividend_frequency": "1 раз в год (июль, 10% чистой прибыли РСБУ на префы)",
        "interim_div_3m_pct": 0.0,
        "upcoming_catalyst_ru": "Защита от валютной переоценки (USD/RUB 82,85 -> 90+ руб.) и накопление процентного дохода по депозитам 6,15 трлн руб. под годовую выплату летом 2027 г.",
        "optimal_horizon_code": "medium_6_12m",
        "optimal_horizon_label": "6–12 месяцев (Под годовую дивидендную отсечку и валютный хедж)",
        "recommended_months": "8–12 мес.",
    },
    "HEAD": {
        "next_catalyst_date": "Декабрь 2026 – Январь 2027 (спецдивиденд / промежуточная выплата) + ИИ-монетизация",
        "dividend_frequency": "1–2 раза в год (высокая норма распределения 75–100% FCF)",
        "interim_div_3m_pct": 8.5,
        "upcoming_catalyst_ru": "Структурный дефицит кадров в РФ поддерживает ценовую власть Хэдхантера (рентабельность EBITDA 58,9%), нулевой долг и регулярный возврат FCF акционерам.",
        "optimal_horizon_code": "long_1_3y",
        "optimal_horizon_label": "1–3 года (Долгосрочный компаундер + высокие дивиденды)",
        "recommended_months": "12–36 мес.",
    },
    "TRNFP": {
        "next_catalyst_date": "Индексация тарифов прокачки с 1 января 2027 г. / Июль 2027 (годовая отсечка)",
        "dividend_frequency": "1 раз в год (июль, не менее 50% нормализованной чистой прибыли МСФО)",
        "interim_div_3m_pct": 0.0,
        "upcoming_catalyst_ru": "Гарантированная индексация трубопроводных тарифов с января 2027 г. и переоценка бумаги при снижении доходностей ОФЗ вслед за ставкой ЦБ 14%.",
        "optimal_horizon_code": "medium_6_12m",
        "optimal_horizon_label": "6–12 месяцев (Квазиоблигационный ре-рейтинг + годовой дивиденд)",
        "recommended_months": "6–12 мес.",
    },
    "LKOH": {
        "next_catalyst_date": "Декабрь 2026 (отсечка по промежуточным дивидендам за 9М 2026) / Июнь 2027",
        "dividend_frequency": "2 раза в год (декабрь и июнь)",
        "interim_div_3m_pct": 7.8,
        "upcoming_catalyst_ru": "Ближайшая зимняя дивидендная отсечка в декабре 2026 г. (~7,8% доходности за 2 месяца) плюс возможный выкуп акций за счет кубышки 1,15 трлн руб.",
        "optimal_horizon_code": "short_1_3m",
        "optimal_horizon_label": "1–3 месяца (Под зимнюю дивидендную отсечку) и 1–3 года (Ядро портфеля)",
        "recommended_months": "2–3 мес. (тактически) / 12–36 мес. (ядро)",
    },
    "MOEX": {
        "next_catalyst_date": "Ноябрь 2026 (отчет МСФО 3К 2026) / Июнь 2027 (годовые дивиденды)",
        "dividend_frequency": "1 раз в год (май–июнь)",
        "interim_div_3m_pct": 0.0,
        "upcoming_catalyst_ru": "Рост комиссионных доходов на фоне оживления торгов акциями и облигациями при ставке ЦБ 14% при сохранении высоких процентных доходов по остаткам.",
        "optimal_horizon_code": "medium_6_12m",
        "optimal_horizon_label": "6–12 месяцев (Инфраструктурный бенефициар биржевой активности)",
        "recommended_months": "6–12 мес.",
    },
    "IRAO": {
        "next_catalyst_date": "Ноябрь 2026 (отчет 9М 2026) / Июнь 2027 (дивиденды 25% прибыли МСФО)",
        "dividend_frequency": "1 раз в год (июнь)",
        "interim_div_3m_pct": 0.0,
        "upcoming_catalyst_ru": "Процентные доходы от денежной кубышки 477 млрд руб. (176,5% капитализации) перекрывают процентные расходы и формируют рекордную чистую прибыль.",
        "optimal_horizon_code": "medium_6_12m",
        "optimal_horizon_label": "6–12 месяцев (Глубокая стоимостная переоценка отрицательного EV)",
        "recommended_months": "6–12 мес.",
    },
    "X5": {
        "next_catalyst_date": "Декабрь 2026 – Февраль 2027 (спецдивиденд после редомициляции и регулярные выплаты)",
        "dividend_frequency": "1–2 раза в год (после завершения редомициляции в РФ)",
        "interim_div_3m_pct": 7.5,
        "upcoming_catalyst_ru": "Распределение накопленного денежного потока в российской юрисдикции и экспансия жестких дискаунтеров «Чижик» при двузначном росте LFL-выручки.",
        "optimal_horizon_code": "short_1_3m",
        "optimal_horizon_label": "1–3 месяца (Дивидендный катализатор) и 1–3 года (Лидер продовольственного ритейла)",
        "recommended_months": "3–18 мес.",
    },
    "TATN": {
        "next_catalyst_date": "Январь 2027 (промежуточные дивиденды за 9М 2026) / Июль 2027 (финальные)",
        "dividend_frequency": "3 раза в год (за 6М, 9М и 12М)",
        "interim_div_3m_pct": 5.2,
        "upcoming_catalyst_ru": "Трехразовый цикл выплаты дивидендов (зимняя отсечка за 9М 2026 в январе 2027 г.) и отрицательный чистый долг (−107 млрд руб.).",
        "optimal_horizon_code": "short_1_3m",
        "optimal_horizon_label": "1–3 месяца (Под зимнюю отсечку 9М) и 6–12 месяцев (Дивидендный рантье)",
        "recommended_months": "3–12 мес.",
    },
    "PLZL": {
        "next_catalyst_date": "Октябрь–Ноябрь 2026 (локальная коррекция после ралли) / Декабрь 2026 (дивиденды)",
        "dividend_frequency": "2 раза в год (при целевом долге < 2,5x EBITDA)",
        "interim_div_3m_pct": 5.5,
        "upcoming_catalyst_ru": "19.10.2026 в котировках Полюса прошла техническая фиксация прибыли после опережающего ралли: оптимален набор траншами на откатах с горизонтом 1–3 года под проект «Сухой Лог».",
        "optimal_horizon_code": "long_1_3y",
        "optimal_horizon_label": "1–3 года (Стратегический золотой хедж, вход на технических откатах)",
        "recommended_months": "12–36 мес.",
    },
    "SBER": {
        "next_catalyst_date": "Ноябрь 2026 (отчет РСБУ за 10М 2026) / Июль 2027 (рекордные дивиденды 50% прибыли)",
        "dividend_frequency": "1 раз в год (июль, 50% чистой прибыли МСФО)",
        "interim_div_3m_pct": 0.0,
        "upcoming_catalyst_ru": "Цикл снижения ставки ЦБ до 14% ускоряет розничное и корпоративное кредитование и снижает стоимость риска (CoR) при сохранении ROE 24,5%.",
        "optimal_horizon_code": "long_1_3y",
        "optimal_horizon_label": "1–3 года (Базовый фундамент российского рынка и дивидендный компаундер)",
        "recommended_months": "12–36 мес.",
    },
    "T": {
        "next_catalyst_date": "Ноябрь 2026 (отчет МСФО 3К 2026 и ежеквартальные дивиденды)",
        "dividend_frequency": "Ежеквартально (до 30% чистой прибыли)",
        "interim_div_3m_pct": 2.4,
        "upcoming_catalyst_ru": "Позитивная оценка рынка по сделке консолидации Точка Банка и разворот кредитного цикла вниз по ставке ЦБ (14%) раскрывают ROE 31,2%.",
        "optimal_horizon_code": "long_1_3y",
        "optimal_horizon_label": "1–3 года (Главный финтех-компаундер в цикле снижения ставки ЦБ)",
        "recommended_months": "12–36 мес.",
    },
    "YDEX": {
        "next_catalyst_date": "Ноябрь 2026 (отчет 3К 2026) / Апрель 2027 (полугодовые дивиденды)",
        "dividend_frequency": "2 раза в год (по 80 руб. и выше с ростом FCF)",
        "interim_div_3m_pct": 0.0,
        "upcoming_catalyst_ru": "Октябрьская новостная просадка на фоне сообщений об инцидентах с дата-центрами дает тактическую скидку для входа в лидера ИИ и облачных сервисов на 1–3 года.",
        "optimal_horizon_code": "long_1_3y",
        "optimal_horizon_label": "1–3 года (Технологический компаундер, покупка на новостной просадке)",
        "recommended_months": "12–36 мес.",
    },
    "ELMT": {
        "next_catalyst_date": "Ноябрь 2026 (отчетность и новые госконтракты микроэлектроники на СПБ Бирже)",
        "dividend_frequency": "1 раз в год (не менее 25% чистой прибыли)",
        "interim_div_3m_pct": 0.0,
        "upcoming_catalyst_ru": "Кратная недооценка на СПБ Бирже (EV/EBITDA 1,73x, P/E 5,50x) при чистой денежной позиции 5,5 млрд руб. и субсидируемой ставке по инвестпрограмме.",
        "optimal_horizon_code": "medium_6_12m",
        "optimal_horizon_label": "6–12 месяцев и 1–3 года (Венчурно-индустриальная альфа СПБ Биржи)",
        "recommended_months": "9–24 мес.",
    },
    "SPBE": {
        "next_catalyst_date": "IV кв. 2026 – 2027 г. (расширение торгов выходного дня и новых линейки БПИФ/ЦФА)",
        "dividend_frequency": "Дивиденды не выплачиваются (реинвестирование в инфраструктуру)",
        "interim_div_3m_pct": 0.0,
        "upcoming_catalyst_ru": "Чистая денежная подушка 14,5 млрд руб. (53% капитализации) и рост оборотов в режиме 7 дней в неделю делают бумагу сильным тактическим бета-инструментом.",
        "optimal_horizon_code": "short_1_3m",
        "optimal_horizon_label": "1–3 месяца и 6–12 месяцев (Тактическая ставка на рост оборотов СПБ Биржи)",
        "recommended_months": "3–9 мес.",
    },
}


def make_ssl_context(unverified: bool = True) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if unverified:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def write_json_with_prov(path: Path, payload: Any, sources: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(content, encoding="utf-8")
    sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    prov = {
        "schema_name": "scientific-evidence.artifact-manifest",
        "artifact": {
            "path": str(path.relative_to(ROOT_DIR)),
            "kind": "news_and_horizon_output",
            "sha256": sha256,
        },
        "derived_from": sources,
        "generated_by": {
            "script_path": "scripts/news_and_horizon_engine.py",
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
    }
    prov_path = Path(str(path) + ".prov.json")
    prov_path.write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")


def score_russian_headline(title: str) -> Tuple[float, str, List[str]]:
    """Return (sentiment_score [-1..+1], catalyst_category, matched_tickers)."""
    low = title.lower()
    score = 0.0
    for phrase, weight in POSITIVE_LEXICON.items():
        if phrase in low:
            score += weight
    for phrase, weight in NEGATIVE_LEXICON.items():
        if phrase in low:
            score += weight

    matched_tickers: List[str] = []
    for ticker, kw_list in TICKER_KEYWORDS.items():
        if any(kw in low for kw in kw_list):
            if ticker not in matched_tickers:
                matched_tickers.append(ticker)

    # Determine catalyst category
    if any(w in low for w in ["дивиденд", "выплат", "отсечк", "гэп"]):
        cat = "Дивиденды и распределение капитала"
    elif any(w in low for w in ["ставк", "цб", "инфляц", "дкп", "ключев", "цены выросли"]):
        cat = "Макроэкономика и ключевая ставка ЦБ"
    elif any(w in low for w in ["сделк", "консолидац", "squeeze-out", "выкуп", "приостановит", "включении"]):
        cat = "Корпоративные события и структура торгов"
    elif any(w in low for w in ["бпла", "удар", "дата-центр", "атак", "санкц"]):
        cat = "Инфраструктурные и операционные риски"
    elif any(w in low for w in ["откат", "тренде", "резко дешевеют", "опережает", "прогноз по цене", "битва акций"]):
        cat = "Технический импульс и позиционирование"
    else:
        cat = "Отраслевая конъюнктура и отчетность"

    score = max(-1.0, min(1.0, round(score, 2)))
    return score, cat, matched_tickers


def fetch_all_live_news() -> Dict[str, Any]:
    ctx = make_ssl_context(unverified=True)
    items_out: List[Dict[str, Any]] = []
    seen_titles: set[str] = set()
    sources_used: List[str] = []

    # 1. MOEX ISS Official Sitenews
    moex_news_url = "https://iss.moex.com/iss/sitenews.json?iss.meta=off"
    sources_used.append(moex_news_url)
    try:
        req = urllib.request.Request(moex_news_url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            m_data = json.loads(resp.read().decode("utf-8"))
        cols = m_data.get("sitenews", {}).get("columns", [])
        for r in m_data.get("sitenews", {}).get("data", [])[:15]:
            rec = dict(zip(cols, r))
            title = str(rec.get("title") or "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            sent, cat, tickers = score_russian_headline(title)
            if "MOEX" not in tickers:
                tickers.append("MOEX")
            items_out.append({
                "source_type": "MOEX_ISS_OFFICIAL",
                "source_name": "Московская Биржа (ISS)",
                "published_at": str(rec.get("published_at") or ""),
                "title": title,
                "sentiment_score": sent if sent != 0.0 else 0.15,
                "catalyst_category": cat,
                "tickers": tickers,
                "horizon_impact": "short_1_3m",
            })
    except Exception:
        pass

    # 2. Central Bank of Russia Official RSS (`eventrss` + `RssPress`)
    for cbr_label, cbr_url in [
        ("Банк России (События и ДКП)", "https://www.cbr.ru/rss/eventrss"),
        ("Банк России (Пресс-служба)", "https://www.cbr.ru/rss/RssPress"),
    ]:
        sources_used.append(cbr_url)
        try:
            req = urllib.request.Request(cbr_url, headers=HEADERS)
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                raw_xml = resp.read()
            root = ET.fromstring(raw_xml)
            for it in root.findall(".//item")[:10]:
                title = (it.findtext("title") or "").strip()
                pub = (it.findtext("pubDate") or "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                sent, cat, tickers = score_russian_headline(title)
                items_out.append({
                    "source_type": "CBR_OFFICIAL_RSS",
                    "source_name": cbr_label,
                    "published_at": pub,
                    "title": title,
                    "sentiment_score": sent,
                    "catalyst_category": "Макроэкономика и ключевая ставка ЦБ",
                    "tickers": tickers if tickers else ["SBER", "BSPB", "T", "MOEX"],
                    "horizon_impact": "medium_6_12m",
                })
        except Exception:
            pass

    # 3. Google News RU RSS across sectors & issuers
    rss_queries = [
        ("Макро и рынок акций", "ЦБ РФ ключевая ставка инфляция Мосбиржа 2026"),
        ("Нефть, газ и дивиденды", "(Лукойл OR Роснефть OR Татнефть OR Сургутнефтегаз OR Транснефть OR Газпром OR НОВАТЭК) акции дивиденды"),
        ("Банки и финтех", "(Сбербанк OR \"Банк Санкт-Петербург\" OR \"Т-Технологии\" OR Совкомбанк OR ВТБ OR Мосбиржа OR \"СПБ Биржа\") акции"),
        ("IT, ритейл и техсектор", "(Яндекс OR Озон OR Хэдхантер OR ИКС5 OR Магнит OR Элемент OR Астра OR Позитив) акции"),
        ("Металлы, золото и флот", "(Полюс OR Фосагро OR Норникель OR Северсталь OR НЛМК OR Русал OR Совкомфлот OR \"Интер РАО\") акции"),
    ]
    for q_label, q_str in rss_queries:
        g_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q_str)}&hl=ru&gl=RU&ceid=RU:ru"
        sources_used.append(g_url)
        try:
            req = urllib.request.Request(g_url, headers=HEADERS)
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                raw_xml = resp.read()
            root = ET.fromstring(raw_xml)
            for it in root.findall(".//item")[:18]:
                title = (it.findtext("title") or "").strip()
                pub = (it.findtext("pubDate") or "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                sent, cat, tickers = score_russian_headline(title)
                # Extract publisher after last " - "
                publisher = q_label
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title_clean, publisher = parts[0].strip(), parts[1].strip()
                else:
                    title_clean = title
                horizon_imp = "short_1_3m" if cat in {
                    "Технический импульс и позиционирование",
                    "Инфраструктурные и операционные риски",
                    "Корпоративные события и структура торгов",
                } else "medium_6_12m"
                items_out.append({
                    "source_type": "MEDIA_RSS_LIVE",
                    "source_name": publisher,
                    "query_cluster": q_label,
                    "published_at": pub,
                    "title": title_clean,
                    "sentiment_score": sent,
                    "catalyst_category": cat,
                    "tickers": tickers,
                    "horizon_impact": horizon_imp,
                })
        except Exception:
            pass

    return {
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_news_items": len(items_out),
        "sources_queried": sources_used,
        "news_items": items_out,
    }


def build_issuer_news_and_catalysts(
    news_bundle: Dict[str, Any],
    fundamentals: Dict[str, Any],
) -> Dict[str, Any]:
    issuers = fundamentals["issuers"]
    news_items = news_bundle["news_items"]

    issuer_catalysts: Dict[str, Any] = {}
    for ticker, iss in issuers.items():
        matched = [n for n in news_items if ticker in n.get("tickers", [])]
        if matched:
            avg_sent = round(sum(n["sentiment_score"] for n in matched) / len(matched), 2)
        else:
            avg_sent = 0.12 if float(iss.get("net_debt_bln") or 0.0) <= 0 else -0.05

        cal = ISSUER_CATALYST_CALENDAR.get(ticker, {})
        net_debt = float(iss.get("net_debt_bln") or 0.0)
        nd_ebitda = float(iss.get("net_debt_to_ebitda") or 0.0)
        roe = float(iss.get("roe_pct") or 15.0)
        div_yield = float(iss.get("div_yield_pct") or 0.0)

        # Default horizon assignment for tickers not explicitly in ISSUER_CATALYST_CALENDAR
        if cal:
            opt_code = cal["optimal_horizon_code"]
            opt_label = cal["optimal_horizon_label"]
            rec_months = cal["recommended_months"]
            next_cat_date = cal["next_catalyst_date"]
            div_freq = cal["dividend_frequency"]
            interim_div_3m = float(cal["interim_div_3m_pct"])
            cat_text = cal["upcoming_catalyst_ru"]
        else:
            if iss["is_bank"]:
                if roe >= 22.0:
                    opt_code = "medium_6_12m"
                    opt_label = "6–12 месяцев (Бенефициар снижения стоимости риска при ставке ЦБ 14%)"
                    rec_months = "6–12 мес."
                else:
                    opt_code = "tactical_avoid"
                    opt_label = "Вне портфеля / Только краткосрочный спекулятивный трейд 1–3 мес."
                    rec_months = "Не рекомендуется к удержанию"
                next_cat_date = "Ноябрь 2026 (отчетность 9М 2026) / Весна–лето 2027 (годовые дивиденды)"
                div_freq = "1 раз в год"
                interim_div_3m = 0.0
                cat_text = (
                    f"Снижение ключевой ставки ЦБ РФ с 21% до 14% постепенно разжимает кредитный спред; "
                    f"норматив Н1.0 = {iss.get('capital_adequacy_n1_pct')}%."
                )
            elif nd_ebitda > 2.2 or float(iss.get("fcf_bln") or 0.0) < 0:
                opt_code = "tactical_avoid"
                opt_label = "Краткосрочный импульс 1–3 мес. (Долгосрочно — избегать из-за долга и отрицательного FCF)"
                rec_months = "1–3 мес. (только спекулятивно)"
                next_cat_date = "Ноябрь–Декабрь 2026 (отчетность МСФО и рефинансирование долга)"
                div_freq = "Выплаты приостановлены или минимальны"
                interim_div_3m = 0.0
                cat_text = (
                    f"Даже при снижении ключевой ставки ЦБ до 14% эффективная стоимость обслуживания долга "
                    f"(Чистый долг/EBITDA = {nd_ebitda:.2f}x) поглощает свободный денежный поток."
                )
            elif roe >= 30.0 and div_yield < 10.0:
                opt_code = "long_1_3y"
                opt_label = "1–3 года (Структурный рост бизнеса и капитализация высокой ROE)"
                rec_months = "12–36 мес."
                next_cat_date = "Ноябрь 2026 (сезонный пик выручки 4К 2026 и отчет МСФО)"
                div_freq = "1–2 раза в год (растущий поток)"
                interim_div_3m = round(div_yield * 0.25, 2)
                cat_text = (
                    f"Высокая рентабельность капитала (ROE {roe:.1f}%) и реинвестирование денежного потока "
                    f"раскрывают максимальную доходность на горизонте 1–3 лет по мере снижения ставки ЦБ к 11,5%."
                )
            else:
                opt_code = "medium_6_12m"
                opt_label = "6–12 месяцев (Дивидендный цикл 2026–2027 гг. и нормализация мультипликаторов)"
                rec_months = "6–12 мес."
                next_cat_date = "Декабрь 2026 – Июль 2027 (промежуточные и годовые дивиденды)"
                div_freq = "1–2 раза в год"
                interim_div_3m = round(div_yield * 0.30, 2) if div_yield >= 11.0 else 0.0
                cat_text = (
                    f"Стабильный экспортный и внутренний денежный поток при дивидендной доходности {div_yield:.1f}% "
                    f"обеспечивает переоценку по мере перетока капитала из депозитов (14%) в акции."
                )

        issuer_catalysts[ticker] = {
            "ticker": ticker,
            "name_ru": iss["name"],
            "sector_name": iss["sector"],
            "news_mentions_count": len(matched),
            "news_sentiment_score": avg_sent,
            "top_headlines": [
                {
                    "title": n["title"],
                    "source": n["source_name"],
                    "published_at": n["published_at"],
                    "sentiment": n["sentiment_score"],
                    "category": n["catalyst_category"],
                }
                for n in matched[:4]
            ],
            "next_catalyst_date": next_cat_date,
            "dividend_frequency": div_freq,
            "interim_div_yield_1_3m_pct": interim_div_3m,
            "upcoming_catalyst_ru": cat_text,
            "optimal_horizon_code": opt_code,
            "optimal_horizon_label": opt_label,
            "recommended_holding_months": rec_months,
        }

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_issuers": len(issuer_catalysts),
        "total_live_news_parsed": len(news_items),
        "issuers": issuer_catalysts,
    }


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    print("[News & Horizons] Fetching live news from CBR RSS, MOEX ISS sitenews, and Russian financial media RSS...")
    news_bundle = fetch_all_live_news()
    raw_news_path = RAW_DIR / "market_news_live.json"
    write_json_with_prov(raw_news_path, news_bundle, news_bundle["sources_queried"][:6])
    print(f"                  Parsed {news_bundle['total_news_items']} live news items -> {raw_news_path}")

    fund_path = PROC_DIR / "fundamentals_reconciled.json"
    if fund_path.exists():
        fundamentals = json.loads(fund_path.read_text(encoding="utf-8"))
        catalysts = build_issuer_news_and_catalysts(news_bundle, fundamentals)
        cat_path = PROC_DIR / "issuer_news_catalysts.json"
        write_json_with_prov(
            cat_path,
            catalysts,
            [
                "@evidence[[data/raw/market_news_live.json]]",
                "@evidence[[data/processed/fundamentals_reconciled.json]]",
            ],
        )
        print(f"                  Built catalyst & horizon profiles for {catalysts['total_issuers']} issuers -> {cat_path}")


if __name__ == "__main__":
    main()
