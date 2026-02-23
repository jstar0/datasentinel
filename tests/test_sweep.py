import pytest

from datasentinel import parse_seed_list, seed_sweep_payload


def test_parse_seed_list_rejects_duplicates_and_blanks() -> None:
    assert parse_seed_list("17, 29,41") == (17, 29, 41)
    with pytest.raises(ValueError):
        parse_seed_list("17,17")
    with pytest.raises(ValueError):
        parse_seed_list("17,")


def test_sweep_has_one_run_per_seed_and_aggregate() -> None:
    payload = seed_sweep_payload((17, 29, 41))
    assert payload["seeds"] == [17, 29, 41]
    assert len(payload["runs"]) == 3
    assert set(payload["aggregate"]) == {
        "driftF1",
        "driftPrecision",
        "driftRecall",
        "gateDetectionRate",
        "cleanFalseFailRate",
    }


def test_sweep_is_deterministic() -> None:
    assert seed_sweep_payload((17, 29, 41)) == seed_sweep_payload((17, 29, 41))


def test_sweep_rejects_empty_or_boolean_seed() -> None:
    with pytest.raises(ValueError):
        seed_sweep_payload(())
    with pytest.raises(ValueError):
        seed_sweep_payload((True,))
