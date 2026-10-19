# TRAJECTORY: composed_1 (Unified INV_1 + DOM_1 Rollout)

1. Загружен предметный навык `skills/moex-spb-ifrs-reconciliation/SKILL.md` (`DOM_1`), обеспечивший полную сверку уставного капитала по привилегированным акциям `TRNFP` (21,45% от 724,93 млн акций), объединение капитализации `SNGS + SNGSP` (926,14 млрд руб.), разделение выплат через `payout_realization` (`SNGSP` 21,09% ДД против `SNGS` 5,28% ДД) и учёт чистого процентного дохода при ставке ЦБ 19%.
2. Выполнен детерминированный верификатор `scripts/verify_moex_spb_quant_bundle.py` (`INV_1`), подтвердивший SHA-256 манифесты `.prov.json`, парсинг русских дробных строк СПБ Биржи, алиас `T <-> TCSG`, 62 бухгалтерских тождества МСФО/РСБУ и синхронизацию `dashboard/data_bundle.js`.
3. Итоговый отчёт записан в `deliverables/moex_spb_investment_strategy.md` без единого маркера ИИ-шаблонов.
