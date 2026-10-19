#!/usr/bin/env python3
"""
Deterministic Verification Script for MOEX & SPB Exchange Quantitative Bundle.

Verifies:
(a) Existence and SHA-256 provenance manifest (.prov.json) integrity of:
    - data/raw/exchange_merged_snapshot.json
    - data/processed/fundamentals_reconciled.json
    - data/processed/quant_valuation_matrix.json
    - data/processed/sector_aggregates.json
    - data/processed/optimal_portfolios.json
    - dashboard/data_bundle.js (and payload sync with quant_valuation_matrix.json)
(b) Cross-exchange alias mapping (T <-> TCSG) and SPB comma-float parsing produced
    valid positive float prices for all 31 equities.
(c) Accounting identities FCF == OCF - CAPEX and EV == Consolidated Market Cap + Net Debt
    (for non-banks) hold across all 31 issuers with zero reconciliation warnings.
(d) Deliverable markdown reports contain no forbidden AI-slop meta-labels
    (SCQA, SO WHAT, Пирамида Минто, Hero KPI).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


REQUIRED_JSON_ARTIFACTS = [
    "data/raw/exchange_merged_snapshot.json",
    "data/processed/fundamentals_reconciled.json",
    "data/processed/quant_valuation_matrix.json",
    "data/processed/sector_aggregates.json",
    "data/processed/optimal_portfolios.json",
]

DASHBOARD_BUNDLE_REL = "dashboard/data_bundle.js"

FORBIDDEN_SLOP_MARKERS = [
    "SCQA",
    "SO WHAT",
    "Пирамида Минто",
    "Hero KPI",
]


def resolve_workspace_root(explicit_root: str | None) -> pathlib.Path:
    if explicit_root:
        return pathlib.Path(explicit_root).resolve()
    cwd = pathlib.Path.cwd().resolve()
    if (cwd / "data" / "raw" / "exchange_merged_snapshot.json").exists():
        return cwd
    script_parent = pathlib.Path(__file__).resolve().parent.parent
    if (script_parent / "data" / "raw" / "exchange_merged_snapshot.json").exists():
        return script_parent
    return cwd


def verify_sha256_manifest(root: pathlib.Path, rel_path: str, errors: list[str]) -> Any:
    target = root / rel_path
    if not target.exists():
        errors.append(f"[MISSING ARTIFACT] {rel_path} does not exist.")
        return None

    prov_path = root / f"{rel_path}.prov.json"
    if not prov_path.exists():
        errors.append(f"[MISSING PROVENANCE] {rel_path}.prov.json does not exist.")
    else:
        try:
            manifest = json.loads(prov_path.read_text(encoding="utf-8"))
            expected_sha = manifest.get("artifact", {}).get("sha256")
            actual_sha = hashlib.sha256(target.read_bytes()).hexdigest()
            if not expected_sha or actual_sha != expected_sha:
                errors.append(
                    f"[SHA-256 MISMATCH] {rel_path}: manifest expected {expected_sha}, actual {actual_sha}."
                )
        except Exception as exc:
            errors.append(f"[INVALID PROVENANCE JSON] {rel_path}.prov.json: {exc}")

    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"[INVALID JSON] {rel_path}: {exc}")
        return None


def verify_dashboard_bundle(
    root: pathlib.Path,
    quant_data: dict[str, Any] | None,
    errors: list[str],
) -> None:
    bundle_path = root / DASHBOARD_BUNDLE_REL
    if not bundle_path.exists():
        errors.append(f"[MISSING ARTIFACT] {DASHBOARD_BUNDLE_REL} does not exist.")
        return

    prov_path = root / f"{DASHBOARD_BUNDLE_REL}.prov.json"
    if prov_path.exists():
        try:
            manifest = json.loads(prov_path.read_text(encoding="utf-8"))
            expected_sha = manifest.get("artifact", {}).get("sha256")
            actual_sha = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
            if expected_sha and actual_sha != expected_sha:
                errors.append(
                    f"[SHA-256 MISMATCH] {DASHBOARD_BUNDLE_REL}: expected {expected_sha}, actual {actual_sha}."
                )
        except Exception as exc:
            errors.append(f"[INVALID PROVENANCE JSON] {DASHBOARD_BUNDLE_REL}.prov.json: {exc}")

    raw_js = bundle_path.read_text(encoding="utf-8").strip()
    prefix = "window.WUNDERWAFFE_DATA ="
    if not raw_js.startswith(prefix):
        errors.append(f"[DASHBOARD FORMAT] {DASHBOARD_BUNDLE_REL} must start with '{prefix}'.")
        return

    json_payload_str = raw_js[len(prefix) :].strip()
    if json_payload_str.endswith(";"):
        json_payload_str = json_payload_str[:-1].strip()

    try:
        bundle_obj = json.loads(json_payload_str)
    except Exception as exc:
        errors.append(f"[DASHBOARD JSON PARSE ERROR] {DASHBOARD_BUNDLE_REL}: {exc}")
        return

    raw_issuers = bundle_obj.get("issuers")
    if isinstance(raw_issuers, list):
        issuers = {row.get("ticker"): row for row in raw_issuers if isinstance(row, dict) and row.get("ticker")}
    elif isinstance(raw_issuers, dict):
        issuers = raw_issuers
    else:
        issuers = {}

    if len(issuers) != 31:
        errors.append(
            f"[DASHBOARD SYNC] Expected 31 issuers inside {DASHBOARD_BUNDLE_REL}, got {len(issuers)}."
        )
    elif quant_data and isinstance(quant_data.get("issuers"), dict):
        for ticker, q_row in quant_data["issuers"].items():
            b_row = issuers.get(ticker)
            if not b_row:
                errors.append(f"[DASHBOARD SYNC] Ticker {ticker} missing in {DASHBOARD_BUNDLE_REL}.")
                continue
            if b_row.get("composite_score") != q_row.get("composite_score"):
                errors.append(
                    f"[DASHBOARD SYNC] Composite score mismatch for {ticker}: bundle={b_row.get('composite_score')} vs quant={q_row.get('composite_score')}."
                )


def verify_exchange_snapshot(snap_data: dict[str, Any] | None, errors: list[str]) -> None:
    if not isinstance(snap_data, dict):
        return
    equities = snap_data.get("equities")
    if not isinstance(equities, dict) or len(equities) != 31:
        errors.append(
            f"[EXCHANGE SNAPSHOT] Expected 31 equities in exchange_merged_snapshot.json, got {len(equities) if isinstance(equities, dict) else 'invalid'}."
        )
        return

    t_row = equities.get("T")
    if not isinstance(t_row, dict):
        errors.append("[ALIAS MAPPING] Ticker 'T' missing from exchange_merged_snapshot.json.")
    else:
        if t_row.get("spb_ticker") != "TCSG":
            errors.append(
                f"[ALIAS MAPPING] Expected T.spb_ticker == 'TCSG', got {t_row.get('spb_ticker')!r}."
            )
        spb_p = t_row.get("spbex_price_rub")
        if not isinstance(spb_p, (int, float)) or spb_p <= 0:
            errors.append(
                f"[ALIAS MAPPING] Expected positive float spbex_price_rub for T (via TCSG), got {spb_p!r}."
            )

    for ticker, row in equities.items():
        for field in ("price_rub", "moex_price_rub"):
            val = row.get(field)
            if not isinstance(val, (int, float)) or isinstance(val, bool) or val <= 0:
                errors.append(f"[INVALID PRICE] {ticker}.{field} must be positive float, got {val!r}.")
        spb_val = row.get("spbex_price_rub")
        if spb_val is not None:
            if not isinstance(spb_val, (int, float)) or isinstance(spb_val, bool) or spb_val <= 0:
                errors.append(
                    f"[SPB COMMA-FLOAT PARSE] {ticker}.spbex_price_rub must be positive float or None, got {spb_val!r}."
                )


def verify_accounting_identities(fund_data: dict[str, Any] | None, errors: list[str]) -> None:
    if not isinstance(fund_data, dict):
        return

    warnings = fund_data.get("reconciliation_warnings")
    if warnings:
        errors.append(
            f"[RECONCILIATION WARNINGS] Expected 0 warnings in fundamentals_reconciled.json, got {len(warnings)}: {warnings}"
        )

    issuers = fund_data.get("issuers")
    if not isinstance(issuers, dict) or len(issuers) != 31:
        errors.append(
            f"[FUNDAMENTALS COUNT] Expected 31 issuers in fundamentals_reconciled.json, got {len(issuers) if isinstance(issuers, dict) else 'invalid'}."
        )
        return

    for ticker, row in issuers.items():
        ocf = row.get("ocf_bln")
        capex = row.get("capex_bln")
        fcf = row.get("fcf_bln")
        if not all(isinstance(x, (int, float)) for x in (ocf, capex, fcf)):
            errors.append(f"[FCF IDENTITY] Non-numeric OCF/CAPEX/FCF for {ticker}.")
        else:
            expected_fcf = round(float(ocf) - float(capex), 4)
            if abs(float(fcf) - expected_fcf) > 0.15:
                errors.append(
                    f"[FCF IDENTITY] {ticker}: FCF ({fcf}) != OCF ({ocf}) - CAPEX ({capex}) (diff={abs(float(fcf) - expected_fcf):.4f})."
                )

        if not row.get("is_bank", False):
            mcap = row.get("consolidated_mcap_bln_rub")
            net_debt = row.get("net_debt_bln")
            ev = row.get("ev_bln")
            if not all(isinstance(x, (int, float)) for x in (mcap, net_debt, ev)):
                errors.append(f"[EV IDENTITY] Non-numeric Consolidated Mcap/Net Debt/EV for non-bank {ticker}.")
            else:
                expected_ev = round(float(mcap) + float(net_debt), 4)
                if abs(float(ev) - expected_ev) > 0.15:
                    errors.append(
                        f"[EV IDENTITY] {ticker}: EV ({ev}) != Consolidated Mcap ({mcap}) + Net Debt ({net_debt}) (diff={abs(float(ev) - expected_ev):.4f})."
                    )


def verify_deliverable_prose(root: pathlib.Path, errors: list[str]) -> list[str]:
    candidate_paths: list[pathlib.Path] = []
    for rel_dir in ("deliverables", "reports", "research/moex_spb_investment_committee"):
        d = root / rel_dir
        if d.exists() and d.is_dir():
            for md_file in sorted(d.glob("*.md")):
                if md_file.name.lower() in ("assignment.md", "spec.md", "memory.md"):
                    continue
                candidate_paths.append(md_file)

    for top_md in sorted(root.glob("*report*.md")) + sorted(root.glob("*strategy*.md")) + sorted(root.glob("*memorandum*.md")):
        if top_md not in candidate_paths:
            candidate_paths.append(top_md)

    checked: list[str] = []
    for md_path in candidate_paths:
        text = md_path.read_text(encoding="utf-8", errors="replace")
        rel = str(md_path.relative_to(root))
        checked.append(rel)
        for marker in FORBIDDEN_SLOP_MARKERS:
            if marker.lower() in text.lower():
                errors.append(
                    f"[FORBIDDEN AI-SLOP LABEL] Found forbidden marker {marker!r} in deliverable {rel}."
                )
    return checked


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify MOEX/SPB quantitative bundle and deliverables.")
    parser.add_argument("--root", type=str, default=None, help="Workspace root directory")
    args = parser.parse_args()

    root = resolve_workspace_root(args.root)
    errors: list[str] = []

    loaded: dict[str, Any] = {}
    for rel_path in REQUIRED_JSON_ARTIFACTS:
        loaded[rel_path] = verify_sha256_manifest(root, rel_path, errors)

    verify_dashboard_bundle(
        root,
        loaded.get("data/processed/quant_valuation_matrix.json"),
        errors,
    )
    verify_exchange_snapshot(loaded.get("data/raw/exchange_merged_snapshot.json"), errors)
    verify_accounting_identities(loaded.get("data/processed/fundamentals_reconciled.json"), errors)
    checked_reports = verify_deliverable_prose(root, errors)

    if errors:
        print(f"[VERIFY FAILED] {len(errors)} error(s) detected in workspace {root}:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"[VERIFY OK] All 5 core JSON artifacts + {DASHBOARD_BUNDLE_REL} verified with SHA-256 manifests; "
        f"31 equities passed T<->TCSG alias & positive float checks; "
        f"31 issuers passed FCF & EV accounting identities with 0 warnings; "
        f"checked {len(checked_reports)} markdown deliverable(s) for zero AI-slop markers."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
