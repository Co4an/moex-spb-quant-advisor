# scientific-evidence (Sova x AI-Scientist-v3 Provenance Contract)

This directory holds the machine-checkable evidence trail for quantitative claims, calculation scripts, charts, and tables.

## Grammar
- Inline reference token: `@evidence[[TARGET]]` or `@evidence[[TARGET#LOCATOR]]`
- Generated artifact sidecar: `<artifact>.prov.json` (`schema_name: "scientific-evidence.artifact-manifest"`)
- Central JSONL ledger: `scientific-evidence/ledger.jsonl`
- Verification report: `scientific-evidence/verification-report.json`

## Reference States
- `resolved`: target exists and locator semantics (such as `sources.json#S1` or JSON dot-paths) were verified.
- `anchored`: target file/URI exists, locator kept opaque.
- `dangling`: target file or locator does not exist or hash check failed.
