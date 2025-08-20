"""Distribution drift profiles and validation-only threshold calibration."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

import numpy as np

from .models import NUMERIC_KINDS, DriftMetric, DriftReport, TableContract, TableSnapshot


def _missing_rate(values: Iterable[Any]) -> float:
    values_tuple = tuple(values)
    if not values_tuple:
        return 0.0
    return sum(value is None for value in values_tuple) / len(values_tuple)


def _numbers(values: Iterable[Any]) -> np.ndarray:
    numbers = [float(value) for value in values if type(value) in (int, float) and math.isfinite(float(value))]
    return np.asarray(numbers, dtype=float)


def numeric_psi(reference: Iterable[Any], candidate: Iterable[Any], bins: int = 10) -> float:
    """Compute population-stability index using reference-derived quantile bins."""

    if bins < 2:
        raise ValueError("bins must be at least 2")
    ref = _numbers(reference)
    cand = _numbers(candidate)
    if ref.size == 0 or cand.size == 0:
        return 0.0
    quantiles = np.quantile(ref, np.linspace(0.0, 1.0, bins + 1))
    edges = np.unique(quantiles)
    if edges.size < 3:
        center = float(ref.mean())
        spread = max(abs(center) * 0.05, 1.0)
        edges = np.asarray([-np.inf, center - spread, center + spread, np.inf], dtype=float)
    else:
        edges = edges.astype(float, copy=True)
        edges[0] = -np.inf
        edges[-1] = np.inf
    ref_counts = np.histogram(ref, bins=edges)[0].astype(float)
    cand_counts = np.histogram(cand, bins=edges)[0].astype(float)
    epsilon = 1e-6
    ref_share = (ref_counts + epsilon) / (ref_counts.sum() + epsilon * len(ref_counts))
    cand_share = (cand_counts + epsilon) / (cand_counts.sum() + epsilon * len(cand_counts))
    value = float(np.sum((cand_share - ref_share) * np.log(cand_share / ref_share)))
    return round(max(0.0, value), 8)


def categorical_js(reference: Iterable[Any], candidate: Iterable[Any]) -> float:
    """Compute Jensen–Shannon divergence over the observed non-null support."""

    ref_values = [value for value in reference if value is not None]
    cand_values = [value for value in candidate if value is not None]
    if not ref_values or not cand_values:
        return 0.0
    support = sorted({repr(value) for value in (*ref_values, *cand_values)})
    ref_counts = np.asarray([sum(repr(value) == key for value in ref_values) for key in support], dtype=float)
    cand_counts = np.asarray([sum(repr(value) == key for value in cand_values) for key in support], dtype=float)
    epsilon = 1e-9
    ref_prob = (ref_counts + epsilon) / (ref_counts.sum() + epsilon * len(support))
    cand_prob = (cand_counts + epsilon) / (cand_counts.sum() + epsilon * len(support))
    midpoint = 0.5 * (ref_prob + cand_prob)
    value = 0.5 * float(np.sum(ref_prob * np.log(ref_prob / midpoint))) + 0.5 * float(
        np.sum(cand_prob * np.log(cand_prob / midpoint))
    )
    return round(max(0.0, value), 8)


def profile_drift(reference: TableSnapshot, candidate: TableSnapshot, contract: TableContract) -> DriftReport:
    """Profile every non-key contract column against the reference snapshot."""

    metrics: list[DriftMetric] = []
    for column in contract.columns:
        if column.name == contract.primary_key:
            continue
        reference_values = reference.values(column.name)
        candidate_values = candidate.values(column.name)
        distribution = (
            numeric_psi(reference_values, candidate_values)
            if column.kind in NUMERIC_KINDS
            else categorical_js(reference_values, candidate_values)
        )
        missing_delta = round(abs(_missing_rate(reference_values) - _missing_rate(candidate_values)), 8)
        metrics.append(
            DriftMetric(
                column=column.name,
                kind="numeric" if column.kind in NUMERIC_KINDS else "categorical",
                distribution_score=distribution,
                missingness_delta=missing_delta,
                score=round(max(distribution, missing_delta), 8),
            )
        )
    return DriftReport(reference.name, candidate.name, tuple(metrics))


def apply_thresholds(report: DriftReport, thresholds: dict[str, float]) -> DriftReport:
    """Attach kind-specific thresholds and alert flags to a drift report."""

    metrics = []
    for metric in report.metrics:
        if metric.kind not in thresholds:
            raise ValueError(f"missing threshold for {metric.kind}")
        threshold = float(thresholds[metric.kind])
        if threshold < 0:
            raise ValueError("thresholds must be non-negative")
        metrics.append(metric.with_threshold(round(threshold, 8)))
    return DriftReport(report.reference_name, report.candidate_name, tuple(metrics))


def classification_summary(predicted: set[str], expected: set[str]) -> dict[str, float | int]:
    """Return a bounded set-level precision/recall/F1 summary."""

    true_positive = len(predicted & expected)
    false_positive = len(predicted - expected)
    false_negative = len(expected - predicted)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 8),
        "recall": round(recall, 8),
        "f1": round(f1, 8),
        "truePositive": true_positive,
        "falsePositive": false_positive,
        "falseNegative": false_negative,
    }


def calibrate_thresholds(
    reports: Iterable[tuple[DriftReport, set[str]]],
    kinds: tuple[str, ...] = ("numeric", "categorical"),
) -> dict[str, float]:
    """Choose thresholds using labelled validation scenarios only."""

    observations = tuple(reports)
    if not observations:
        raise ValueError("at least one validation report is required")
    thresholds: dict[str, float] = {}
    for kind in kinds:
        metrics = [metric for report, _expected in observations for metric in report.metrics if metric.kind == kind]
        candidates = sorted({0.0, *(metric.score for metric in metrics), *(metric.score + 1e-8 for metric in metrics)})
        best: tuple[float, float] | None = None
        for threshold in candidates:
            predicted: set[str] = set()
            expected: set[str] = set()
            for report, labels in observations:
                kind_columns = {metric.column for metric in report.metrics if metric.kind == kind}
                predicted.update(
                    f"{report.candidate_name}:{metric.column}"
                    for metric in report.metrics
                    if metric.kind == kind and metric.score >= threshold
                )
                expected.update(
                    f"{report.candidate_name}:{column}" for column in labels if column in kind_columns
                )
            score = float(classification_summary(predicted, expected)["f1"])
            candidate = (score, float(threshold))
            if best is None or candidate[0] > best[0] or (candidate[0] == best[0] and candidate[1] > best[1]):
                best = candidate
        thresholds[kind] = round(best[1] if best is not None else 0.0, 8)
    return thresholds
