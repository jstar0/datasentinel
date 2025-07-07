"""Deterministic synthetic tables used by the benchmark and tests."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from .models import ColumnSpec, TableContract, TableSnapshot

CHANNELS = ("email", "mobile", "partner")
TOPICS = ("product", "service", "support", "billing")


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    snapshot: TableSnapshot
    expected_drift_columns: tuple[str, ...]
    expected_issue_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Dataset:
    contract: TableContract
    reference: TableSnapshot
    validation: tuple[Scenario, ...]
    test: tuple[Scenario, ...]


def make_contract() -> TableContract:
    """Return the public fixture contract."""

    return TableContract(
        primary_key="record_id",
        columns=(
            ColumnSpec("record_id", "integer"),
            ColumnSpec("channel", "string", allowed_values=CHANNELS),
            ColumnSpec("rating", "number", min_value=1.0, max_value=5.0),
            ColumnSpec("text_length", "integer", min_value=1.0, max_value=240.0),
            ColumnSpec("topic", "string", allowed_values=TOPICS),
            ColumnSpec("created_day", "integer", min_value=1.0, max_value=31.0),
            ColumnSpec("is_verified", "boolean"),
        ),
    )


def _reference_rows(seed: int, count: int = 240) -> list[dict[str, Any]]:
    if count < 1:
        raise ValueError("count must be positive")
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    for index in range(count):
        rating = round(max(1.0, min(5.0, rng.gauss(3.65, 0.48))), 2)
        text_length = max(1, min(240, int(round(rng.gauss(82.0, 22.0)))))
        rows.append(
            {
                "record_id": 10_000 + index,
                "channel": rng.choices(CHANNELS, weights=(0.56, 0.29, 0.15), k=1)[0],
                "rating": rating,
                "text_length": text_length,
                "topic": rng.choice(TOPICS),
                "created_day": rng.randint(1, 30),
                "is_verified": rng.random() < 0.64,
            }
        )
    return rows


def _copy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def _scenario_rows(
    reference: list[dict[str, Any]], profile: str, seed: int
) -> tuple[list[dict[str, Any]], tuple[str, ...], tuple[str, ...]]:
    rows = _copy_rows(reference)
    rng = random.Random(seed * 31 + len(profile))
    drift: set[str] = set()
    issues: set[str] = set()
    if profile == "clean":
        return rows, (), ()
    if profile in {"channel_shift", "mixed_quality"}:
        # Change a large, deterministic slice rather than drawing a hidden
        # sample, making the intended population shift easy to inspect.
        for index, row in enumerate(rows):
            if index % 4 in (0, 1):
                row["channel"] = "partner"
        drift.add("channel")
    if profile in {"rating_shift", "mixed_quality"}:
        for index, row in enumerate(rows):
            if index % 3 != 0:
                row["rating"] = round(min(5.0, float(row["rating"]) + 0.72), 2)
        drift.add("rating")
    if profile == "text_length_shift":
        for row in rows:
            row["text_length"] = min(240, int(round(float(row["text_length"]) * 1.55)))
        drift.add("text_length")
    if profile == "mixed_quality":
        # These mutations are deliberately sparse and independently
        # inspectable. They never use client rows or identifiers.
        rows[7]["record_id"] = rows[6]["record_id"]
        rows[13]["rating"] = 6.4
        rows[21]["channel"] = "unknown"
        rows[29]["text_length"] = -3
        rows[37]["topic"] = None
        rows[45]["is_verified"] = "yes"
        rows[53].pop("channel")
        issues.update({"duplicate_key", "range_violation", "category_violation", "missing_value", "type_mismatch"})
    elif profile == "sparse_missingness":
        for index in range(0, len(rows), 11):
            rows[index]["topic"] = None
        drift.add("topic")
        issues.add("missing_value")
    elif profile == "randomized_channel_shift":
        indexes = list(range(len(rows)))
        rng.shuffle(indexes)
        for index in indexes[: len(rows) // 2]:
            rows[index]["channel"] = "partner"
        drift.add("channel")
    elif profile not in {"channel_shift", "rating_shift", "text_length_shift"}:
        raise ValueError(f"unknown fixture profile: {profile}")
    return rows, tuple(sorted(drift)), tuple(sorted(issues))


def create_dataset(seed: int = 17) -> Dataset:
    """Build a reference plus validation/test scenarios for one seed."""

    reference_rows = _reference_rows(seed)
    reference = TableSnapshot.from_rows("reference", reference_rows)

    def scenario(name: str, profile: str, offset: int) -> Scenario:
        rows, drift, issues = _scenario_rows(reference_rows, profile, seed + offset)
        return Scenario(name, TableSnapshot.from_rows(name, rows), drift, issues)

    validation = (
        scenario("validation-clean", "clean", 1),
        scenario("validation-channel-shift", "channel_shift", 2),
        scenario("validation-rating-shift", "rating_shift", 3),
        scenario("validation-mixed-quality", "mixed_quality", 4),
    )
    test = (
        scenario("test-clean", "clean", 11),
        scenario("test-channel-shift", "randomized_channel_shift", 12),
        scenario("test-rating-shift", "rating_shift", 13),
        scenario("test-mixed-quality", "mixed_quality", 14),
        scenario("test-text-length-shift", "text_length_shift", 15),
    )
    return Dataset(make_contract(), reference, validation, test)
