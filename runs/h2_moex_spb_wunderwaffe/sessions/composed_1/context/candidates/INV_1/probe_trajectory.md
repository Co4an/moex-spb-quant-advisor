# Rollout Workspace `probe_INV_1`

## Trajectory Notes
# TRAJECTORY: probe_INV_1

1. Запущен детерминированный верификатор `scripts/verify_moex_spb_quant_bundle.py` из `guardrails.md`.
2. Подтверждена целостность всех SHA-256 манифестов `.prov.json`, парсинг русских дробных строк СПБ Биржи, кросс-биржевой алиас `T <-> TCSG` и 62 бухгалтерских тождества МСФО/РСБУ.
3. Ограничение изолированного `probe_INV_1`: без доменного навыка `moex-spb-ifrs-reconciliation` текст отчёта не раскрывает экономику уставного капитала `TRNFP` (21,45%) и различие `SNGSP` vs `SNGS`.


## Produced Deliverables
### `deliverables/moex_spb_investment_strategy.md`
````text
# Инвестиционная стратегия MOEX & SPBEX (Probe INV_1)

Проверены SHA-256 манифесты (.prov.json), кросс-алиасы T/TCSG и 62 бухгалтерских тождества.

````

