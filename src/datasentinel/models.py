"""Immutable public models for DataSentinel."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

NUMERIC_KINDS = frozenset({"integer", "number"})
SUPPORTED_KINDS = frozenset({"integer", "number", "string", "boolean"})


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    """A small, explicit schema rule for one column."""

    name: str
    kind: str
    nullable: bool = False
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("column name must not be empty")
        if self.kind not in SUPPORTED_KINDS:
            raise ValueError(f"unsupported column kind: {self.kind}")
        if self.kind not in NUMERIC_KINDS and (self.min_value is not None or self.max_value is not None):
            raise ValueError("min_value/max_value require a numeric column")
        if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
            raise ValueError("min_value cannot exceed max_value")

    def validate(self, value: Any) -> tuple[str, str] | None:
        """Return ``(code, message)`` for the first violation, if any."""

        if value is None:
            return None if self.nullable else ("missing_value", f"{self.name} is required")
        if self.kind == "integer":
            valid_type = type(value) is int
        elif self.kind == "number":
            valid_type = type(value) in (int, float) and math.isfinite(float(value))
        elif self.kind == "string":
            valid_type = isinstance(value, str)
        else:
            valid_type = type(value) is bool
        if not valid_type:
            return ("type_mismatch", f"{self.name} expected {self.kind}")
        if self.kind in NUMERIC_KINDS:
            numeric = float(value)
            if self.min_value is not None and numeric < self.min_value:
                return ("range_violation", f"{self.name} is below {self.min_value:g}")
            if self.max_value is not None and numeric > self.max_value:
                return ("range_violation", f"{self.name} is above {self.max_value:g}")
        if self.allowed_values and value not in self.allowed_values:
            return ("category_violation", f"{self.name} is not in the allowed category set")
        return None


@dataclass(frozen=True, slots=True)
class TableContract:
    """Schema and primary-key rules for a tabular snapshot."""

    columns: tuple[ColumnSpec, ...]
    primary_key: str
    allow_extra_columns: bool = False

    def __post_init__(self) -> None:
        names = [column.name for column in self.columns]
        if not names or len(set(names)) != len(names):
            raise ValueError("contract columns must be non-empty and unique")
        if self.primary_key not in names:
            raise ValueError("primary_key must name a contract column")

    @property
    def column_map(self) -> dict[str, ColumnSpec]:
        return {column.name: column for column in self.columns}

    def as_dict(self) -> dict[str, Any]:
        return {
            "primaryKey": self.primary_key,
            "allowExtraColumns": self.allow_extra_columns,
            "columns": [
                {
                    "name": column.name,
                    "kind": column.kind,
                    "nullable": column.nullable,
                    "min": column.min_value,
                    "max": column.max_value,
                    "allowed": list(column.allowed_values),
                }
                for column in self.columns
            ],
        }


@dataclass(frozen=True, slots=True)
class TableSnapshot:
    """A named, ordered table made of row mappings."""

    name: str
    rows: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_rows(cls, name: str, rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...]) -> "TableSnapshot":
        if not name or not name.strip():
            raise ValueError("snapshot name must not be empty")
        normalized = tuple(dict(row) for row in rows)
        return cls(name=name, rows=normalized)

    def values(self, column: str) -> tuple[Any, ...]:
        return tuple(row.get(column) for row in self.rows)

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "rowCount": len(self.rows), "rows": [dict(row) for row in self.rows]}


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    row_index: int | None
    column: str
    code: str
    message: str
    severity: str = "error"

    def as_dict(self) -> dict[str, Any]:
        return {
            "rowIndex": self.row_index,
            "column": self.column,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True, slots=True)
class ValidationReport:
    snapshot_name: str
    row_count: int
    checked_cells: int
    issues: tuple[ValidationIssue, ...]
    duplicate_rows: int
    unknown_columns: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.issues

    @property
    def invalid_cells(self) -> int:
        return len({(issue.row_index, issue.column) for issue in self.issues})

    @property
    def quality_score(self) -> float:
        if self.checked_cells == 0:
            return 1.0
        return round(max(0.0, 1.0 - self.invalid_cells / self.checked_cells), 8)

    def issue_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.code] = counts.get(issue.code, 0) + 1
        return dict(sorted(counts.items()))

    def as_dict(self) -> dict[str, Any]:
        return {
            "snapshot": self.snapshot_name,
            "rowCount": self.row_count,
            "checkedCells": self.checked_cells,
            "invalidCells": self.invalid_cells,
            "qualityScore": self.quality_score,
            "valid": self.valid,
            "duplicateRows": self.duplicate_rows,
            "unknownColumns": list(self.unknown_columns),
            "issueCounts": self.issue_counts(),
            "issues": [issue.as_dict() for issue in self.issues],
        }


@dataclass(frozen=True, slots=True)
class DriftMetric:
    column: str
    kind: str
    distribution_score: float
    missingness_delta: float
    score: float
    threshold: float | None = None
    alerted: bool = False

    def with_threshold(self, threshold: float) -> "DriftMetric":
        return DriftMetric(
            column=self.column,
            kind=self.kind,
            distribution_score=self.distribution_score,
            missingness_delta=self.missingness_delta,
            score=self.score,
            threshold=threshold,
            alerted=self.score >= threshold,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "kind": self.kind,
            "distributionScore": self.distribution_score,
            "missingnessDelta": self.missingness_delta,
            "score": self.score,
            "threshold": self.threshold,
            "alerted": self.alerted,
        }


@dataclass(frozen=True, slots=True)
class DriftReport:
    reference_name: str
    candidate_name: str
    metrics: tuple[DriftMetric, ...]

    @property
    def alerts(self) -> tuple[DriftMetric, ...]:
        return tuple(metric for metric in self.metrics if metric.alerted)

    def as_dict(self) -> dict[str, Any]:
        return {
            "reference": self.reference_name,
            "candidate": self.candidate_name,
            "alertCount": len(self.alerts),
            "metrics": [metric.as_dict() for metric in self.metrics],
        }


@dataclass(frozen=True, slots=True)
class GateDecision:
    passed: bool
    reasons: tuple[str, ...]
    validation: ValidationReport
    drift: DriftReport

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reasons": list(self.reasons),
            "validation": self.validation.as_dict(),
            "drift": self.drift.as_dict(),
        }
