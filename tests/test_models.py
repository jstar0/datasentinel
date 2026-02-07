import pytest

from datasentinel import ColumnSpec, TableContract, TableSnapshot


def test_column_spec_accepts_valid_value_and_rejects_first_rule() -> None:
    spec = ColumnSpec("rating", "number", min_value=1, max_value=5)
    assert spec.validate(4.5) is None
    assert spec.validate(0.5) == ("range_violation", "rating is below 1")


def test_boolean_is_not_an_integer() -> None:
    assert ColumnSpec("count", "integer").validate(True)[0] == "type_mismatch"


def test_nullable_and_allowed_values() -> None:
    assert ColumnSpec("tag", "string", nullable=True).validate(None) is None
    assert ColumnSpec("tag", "string", allowed_values=("a",)).validate("b")[0] == "category_violation"


def test_contract_requires_unique_columns_and_primary_key() -> None:
    with pytest.raises(ValueError):
        TableContract((ColumnSpec("id", "integer"), ColumnSpec("id", "integer")), "id")
    with pytest.raises(ValueError):
        TableContract((ColumnSpec("id", "integer"),), "missing")


def test_snapshot_copies_rows_and_exposes_column_values() -> None:
    source = [{"id": 1}, {"id": 2}]
    snapshot = TableSnapshot.from_rows("demo", source)
    source[0]["id"] = 99
    assert snapshot.values("id") == (1, 2)
    assert snapshot.as_dict()["rowCount"] == 2
