import pytest

from datasentinel import (
    TableSnapshot,
    apply_thresholds,
    calibrate_thresholds,
    categorical_js,
    classification_summary,
    create_dataset,
    numeric_psi,
    profile_drift,
)


def test_identical_distributions_have_zero_drift() -> None:
    assert numeric_psi([1, 2, 3], [1, 2, 3]) == 0.0
    assert categorical_js(["a", "b"], ["a", "b"]) == 0.0


def test_drift_scores_increase_for_shifted_population() -> None:
    assert numeric_psi([1, 2, 3, 4], [10, 11, 12, 13]) > 0.1
    assert categorical_js(["a"] * 10 + ["b"], ["b"] * 10 + ["a"]) > 0.1


def test_invalid_numeric_arguments_are_rejected() -> None:
    with pytest.raises(ValueError):
        numeric_psi([1], [1], bins=1)


def test_profile_excludes_primary_key_and_tracks_missingness() -> None:
    dataset = create_dataset(17)
    candidate = TableSnapshot.from_rows("candidate", [dict(row) for row in dataset.reference.rows])
    candidate.rows[0]["topic"] = None  # type: ignore[index]
    report = profile_drift(dataset.reference, candidate, dataset.contract)
    assert "record_id" not in {metric.column for metric in report.metrics}
    topic = next(metric for metric in report.metrics if metric.column == "topic")
    assert topic.missingness_delta > 0


def test_threshold_application_marks_only_scores_at_or_above_cutoff() -> None:
    dataset = create_dataset(17)
    report = profile_drift(dataset.reference, dataset.test[1].snapshot, dataset.contract)
    applied = apply_thresholds(report, {"numeric": 0.5, "categorical": 0.05})
    assert {metric.column for metric in applied.alerts} == {"channel"}


def test_calibration_uses_validation_labels() -> None:
    dataset = create_dataset(17)
    reports = [
        (profile_drift(dataset.reference, case.snapshot, dataset.contract), set(case.expected_drift_columns))
        for case in dataset.validation
    ]
    thresholds = calibrate_thresholds(reports)
    assert set(thresholds) == {"numeric", "categorical"}
    assert all(value >= 0 for value in thresholds.values())


def test_classification_summary_is_bounded() -> None:
    summary = classification_summary({"a", "b"}, {"b", "c"})
    assert summary["precision"] == 0.5
    assert summary["recall"] == 0.5
    assert summary["f1"] == 0.5
