from pathlib import Path

from datasentinel import benchmark_payload, write_benchmark


def test_benchmark_has_clean_calibration_boundary() -> None:
    payload = benchmark_payload(17)
    assert payload["thresholdObjective"] == "validation_column_drift_f1"
    assert payload["summary"]["test"]["driftF1"] == 1.0
    assert payload["summary"]["test"]["cleanFalseFailRate"] == 0.0
    assert payload["summary"]["test"]["gateDetectionRate"] == 1.0


def test_benchmark_rows_keep_issue_and_drift_evidence() -> None:
    rows = benchmark_payload(17)["rows"]
    mixed = next(row for row in rows if row["case"] == "test-mixed-quality")
    assert mixed["valid"] is False
    assert "duplicate_key" in mixed["issueCodes"]
    assert mixed["alertedColumns"] == "channel,rating"
    assert mixed["gatePassed"] is False


def test_benchmark_writer_emits_four_artifacts(tmp_path: Path) -> None:
    write_benchmark(tmp_path, 17)
    assert {path.name for path in tmp_path.iterdir()} == {
        "benchmark.json",
        "per_case.csv",
        "report.md",
        "manifest.json",
    }
    assert "DataSentinel benchmark" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_benchmark_writer_is_byte_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_benchmark(first, 29)
    write_benchmark(second, 29)
    for name in ("benchmark.json", "per_case.csv", "report.md", "manifest.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
