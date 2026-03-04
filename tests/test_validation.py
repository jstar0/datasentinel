from datasentinel import TableSnapshot, create_dataset, issue_code_rate, validate_snapshot


def test_clean_reference_passes_contract() -> None:
    dataset = create_dataset(17)
    report = validate_snapshot(dataset.reference, dataset.contract)
    assert report.valid
    assert report.quality_score == 1.0
    assert report.issue_counts() == {}


def test_mixed_quality_report_is_actionable() -> None:
    dataset = create_dataset(17)
    report = validate_snapshot(dataset.test[-2].snapshot, dataset.contract)
    assert not report.valid
    assert report.duplicate_rows == 1
    assert report.issue_counts() == {
        "category_violation": 1,
        "duplicate_key": 1,
        "missing_value": 2,
        "range_violation": 2,
        "type_mismatch": 1,
    }
    assert issue_code_rate(report, "missing_value") == round(2 / 240, 8)


def test_unknown_column_and_missing_required_column_are_distinct() -> None:
    dataset = create_dataset(17)
    row = dict(dataset.reference.rows[0])
    row.pop("channel")
    row["unexpected"] = 1
    report = validate_snapshot(TableSnapshot.from_rows("bad", [row]), dataset.contract)
    assert report.unknown_columns == ("unexpected",)
    assert {issue.code for issue in report.issues} == {"missing_value", "unknown_column"}


def test_empty_snapshot_has_no_invalid_cells() -> None:
    dataset = create_dataset(17)
    report = validate_snapshot(TableSnapshot.from_rows("empty", []), dataset.contract)
    assert report.valid
    assert report.quality_score == 1.0
