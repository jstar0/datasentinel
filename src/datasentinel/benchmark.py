"""Benchmark orchestration and hash-bound artifact writers."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from .drift import (
    apply_thresholds,
    calibrate_thresholds,
    classification_summary,
    profile_drift,
)
from .fixture import Dataset, Scenario, create_dataset
from .gate import evaluate_gate
from .validation import validate_snapshot

ROW_FIELDS = (
    "split",
    "case",
    "rowCount",
    "qualityScore",
    "valid",
    "issueCount",
    "issueCodes",
    "expectedIssueCodes",
    "alertedColumns",
    "expectedDriftColumns",
    "driftPrecision",
    "driftRecall",
    "driftF1",
    "gatePassed",
    "expectedGateFail",
)


def _scenario_row(dataset: Dataset, scenario: Scenario, split: str, thresholds: dict[str, float]) -> dict[str, Any]:
    validation = validate_snapshot(scenario.snapshot, dataset.contract)
    drift = apply_thresholds(profile_drift(dataset.reference, scenario.snapshot, dataset.contract), thresholds)
    predicted = {metric.column for metric in drift.alerts}
    expected = set(scenario.expected_drift_columns)
    summary = classification_summary(predicted, expected)
    gate = evaluate_gate(dataset.reference, scenario.snapshot, dataset.contract, thresholds)
    return {
        "split": split,
        "case": scenario.name,
        "rowCount": len(scenario.snapshot.rows),
        "qualityScore": validation.quality_score,
        "valid": validation.valid,
        "issueCount": len(validation.issues),
        "issueCodes": ",".join(sorted(validation.issue_counts())),
        "expectedIssueCodes": ",".join(scenario.expected_issue_codes),
        "alertedColumns": ",".join(sorted(predicted)),
        "expectedDriftColumns": ",".join(sorted(expected)),
        "driftPrecision": summary["precision"],
        "driftRecall": summary["recall"],
        "driftF1": summary["f1"],
        "gatePassed": gate.passed,
        "expectedGateFail": bool(expected or scenario.expected_issue_codes),
        "driftMetrics": [metric.as_dict() for metric in drift.metrics],
        "issues": [issue.as_dict() for issue in validation.issues],
        "gateReasons": list(gate.reasons),
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    predicted: set[str] = set()
    expected: set[str] = set()
    true_positive = false_positive = false_negative = 0
    for row in rows:
        # Names are scoped by case so the pooled score cannot double-count a
        # column merely because it appears in several scenarios.
        case = str(row["case"])
        predicted_case = {f"{case}:{column}" for column in str(row["alertedColumns"]).split(",") if column}
        expected_case = {f"{case}:{column}" for column in str(row["expectedDriftColumns"]).split(",") if column}
        predicted |= predicted_case
        expected |= expected_case
        true_positive += len(predicted_case & expected_case)
        false_positive += len(predicted_case - expected_case)
        false_negative += len(expected_case - predicted_case)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    expected_fail = [row for row in rows if row["expectedGateFail"]]
    detected_fail = [row for row in expected_fail if not row["gatePassed"]]
    clean_cases = [row for row in rows if not row["expectedGateFail"]]
    return {
        "caseCount": len(rows),
        "invalidCaseRate": round(sum(not row["valid"] for row in rows) / len(rows), 8) if rows else 0.0,
        "driftPrecision": round(precision, 8),
        "driftRecall": round(recall, 8),
        "driftF1": round(f1, 8),
        "driftTruePositive": true_positive,
        "driftFalsePositive": false_positive,
        "driftFalseNegative": false_negative,
        "gateDetectionRate": round(len(detected_fail) / len(expected_fail), 8) if expected_fail else 0.0,
        "cleanFalseFailRate": round(sum(not row["gatePassed"] for row in clean_cases) / len(clean_cases), 8)
        if clean_cases
        else 0.0,
    }


def benchmark_payload(seed: int = 17) -> dict[str, Any]:
    """Calibrate on validation scenarios and score held-out scenarios once."""

    dataset = create_dataset(seed)
    validation_profiles = [
        (profile_drift(dataset.reference, scenario.snapshot, dataset.contract), set(scenario.expected_drift_columns))
        for scenario in dataset.validation
    ]
    thresholds = calibrate_thresholds(validation_profiles)
    validation_rows = [_scenario_row(dataset, scenario, "validation", thresholds) for scenario in dataset.validation]
    test_rows = [_scenario_row(dataset, scenario, "test", thresholds) for scenario in dataset.test]
    rows = validation_rows + test_rows
    return {
        "benchmarkVersion": 1,
        "seed": seed,
        "contract": dataset.contract.as_dict(),
        "reference": {"name": dataset.reference.name, "rowCount": len(dataset.reference.rows)},
        "splitCounts": {"validation": len(validation_rows), "test": len(test_rows)},
        "thresholdObjective": "validation_column_drift_f1",
        "thresholds": thresholds,
        "summary": {"validation": _aggregate(validation_rows), "test": _aggregate(test_rows)},
        "rows": rows,
    }


def write_benchmark(output_dir: str | Path, seed: int = 17) -> dict[str, Any]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    payload = benchmark_payload(seed)
    write_text(directory / "benchmark.json", json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_rows_csv(directory / "per_case.csv", payload["rows"])
    write_text(directory / "report.md", markdown_report(payload))
    write_manifest(directory)
    return payload


def write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROW_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in ROW_FIELDS})


def markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# DataSentinel benchmark",
        "",
        "A synthetic tabular contract and distribution-drift benchmark with validation-only calibration.",
        "",
        f"- seed: `{payload['seed']}`",
        f"- reference rows: `{payload['reference']['rowCount']}`",
        f"- thresholds: `{payload['thresholds']}`",
        "",
        "## Held-out test summary",
        "",
        "| measure | value |",
        "|---|---:|",
    ]
    for key, value in payload["summary"]["test"].items():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| split | case | quality | valid | drift F1 | gate |",
            "|---|---|---:|:---:|---:|:---:|",
        ]
    )
    for row in payload["rows"]:
        lines.append(
            f"| {row['split']} | {row['case']} | {row['qualityScore']:.6f} | "
            f"{'yes' if row['valid'] else 'no'} | {row['driftF1']:.6f} | "
            f"{'pass' if row['gatePassed'] else 'fail'} |"
        )
    lines.extend(
        [
            "",
            "Thresholds are selected from labelled validation scenarios; test labels are used only for the final "
            "diagnostic summary. All rows are synthetic, and these metrics are not production quality, privacy, "
            "fairness, or business guarantees.",
            "",
        ]
    )
    return "\n".join(lines)


def write_manifest(directory: Path) -> None:
    manifest = {
        "schemaVersion": 1,
        "files": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path.read_bytes())}
            for path in sorted(directory.glob("*"))
            if path.is_file() and path.name != "manifest.json"
        ],
    }
    write_text(directory / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
