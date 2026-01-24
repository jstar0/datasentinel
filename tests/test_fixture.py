from datasentinel import create_dataset, make_contract


def test_fixture_is_deterministic() -> None:
    first = create_dataset(17)
    second = create_dataset(17)
    assert first.reference.as_dict() == second.reference.as_dict()
    assert [case.snapshot.as_dict() for case in first.test] == [case.snapshot.as_dict() for case in second.test]


def test_fixture_changes_with_seed() -> None:
    assert create_dataset(17).reference.as_dict() != create_dataset(29).reference.as_dict()


def test_contract_has_expected_columns() -> None:
    names = [column.name for column in make_contract().columns]
    assert names == ["record_id", "channel", "rating", "text_length", "topic", "created_day", "is_verified"]


def test_mixed_quality_scenario_has_all_expected_issue_families() -> None:
    scenario = create_dataset(17).test[-2]
    assert scenario.name == "test-mixed-quality"
    assert set(scenario.expected_issue_codes) == {
        "duplicate_key",
        "range_violation",
        "category_violation",
        "missing_value",
        "type_mismatch",
    }


def test_scenario_names_are_unique_per_split() -> None:
    dataset = create_dataset()
    assert len({case.name for case in dataset.validation}) == len(dataset.validation)
    assert len({case.name for case in dataset.test}) == len(dataset.test)
