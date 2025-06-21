# DataSentinel design decisions and limits

DataSentinel is a synthetic tabular contract and drift experiment, not a production data-observability service.

## Decisions embodied in the implementation

1. **Contract validation emits row-level evidence.** Types, ranges, categories, unknown columns, and duplicate primary keys are checked before the quality gate. Rejected alternative: a single pass/fail count with no diagnosable rows.
2. **Primary keys are excluded from drift metrics.** Keys describe identity rather than population behavior. Rejected alternative: treat a new identifier distribution as operational drift.
3. **Thresholds are calibrated on validation scenarios only.** Test scenarios consume frozen thresholds. Rejected alternative: tune thresholds against test labels and report that score as generalization.
4. **Numeric PSI and categorical JS are separate metric families.** Rejected alternative: coerce category codes to numbers and create false ordinal distance.
5. **The gate is fail-closed for contract issues and reports drift separately.** Rejected alternative: silently accept malformed rows because aggregate drift happens to look normal.

## Known weaknesses

1. **All tables, labels, shifts, and expected outcomes are synthetic fixtures.**
2. **PSI/JS thresholds are fixture-calibrated and not production alert policy.**
3. **There is no streaming ingestion, schema registry, lineage, privacy control, or persistent incident workflow.**
4. **Distribution metrics can miss joint-feature, temporal, semantic, and label drift.**
5. **The contract does not represent nested structures, evolving schemas, or real database constraints.**
6. **A fail gate cannot repair bad data or establish root cause.**
7. **Seed sweeps prove repeatability of this fixture, not detection performance on customer data.**

## Interview-safe description

Describe DataSentinel as a reproducible synthetic lab for row-level table contracts and validation-only calibrated drift gates.
