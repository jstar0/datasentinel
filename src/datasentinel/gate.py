"""Combine contract and drift evidence into one admission decision."""

from __future__ import annotations

from .drift import apply_thresholds, profile_drift
from .models import GateDecision, TableContract, TableSnapshot
from .validation import validate_snapshot


def evaluate_gate(
    reference: TableSnapshot,
    candidate: TableSnapshot,
    contract: TableContract,
    thresholds: dict[str, float],
) -> GateDecision:
    """Return a fail-closed decision while preserving all diagnostics."""

    validation = validate_snapshot(candidate, contract)
    drift = apply_thresholds(profile_drift(reference, candidate, contract), thresholds)
    reasons = [
        f"contract:{issue.code}:row={issue.row_index}:column={issue.column}"
        for issue in validation.issues
    ]
    reasons.extend(
        f"drift:{metric.column}:score={metric.score:.8f}:threshold={metric.threshold:.8f}"
        for metric in drift.alerts
    )
    return GateDecision(not reasons, tuple(reasons), validation, drift)
