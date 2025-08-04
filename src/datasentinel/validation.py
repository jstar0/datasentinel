"""Contract validation with row-level evidence."""

from __future__ import annotations

from typing import Any

from .models import TableContract, TableSnapshot, ValidationIssue, ValidationReport


def validate_snapshot(snapshot: TableSnapshot, contract: TableContract) -> ValidationReport:
    """Validate values, extras, and primary-key uniqueness in stable order."""

    column_map = contract.column_map
    issues: list[ValidationIssue] = []
    seen_keys: dict[Any, int] = {}
    duplicate_rows = 0
    unknown_columns: set[str] = set()

    for row_index, row in enumerate(snapshot.rows):
        for column in contract.columns:
            result = column.validate(row.get(column.name))
            if result is not None:
                code, message = result
                issues.append(ValidationIssue(row_index, column.name, code, message))
        extras = sorted(set(row) - set(column_map))
        for extra in extras:
            unknown_columns.add(extra)
            issues.append(
                ValidationIssue(row_index, extra, "unknown_column", f"{extra} is not declared in the contract")
            )
        key = row.get(contract.primary_key)
        if key is None or type(key) is not int:
            continue
        if key in seen_keys:
            duplicate_rows += 1
            issues.append(
                ValidationIssue(
                    row_index,
                    contract.primary_key,
                    "duplicate_key",
                    f"{contract.primary_key} repeats row {seen_keys[key]}",
                )
            )
        else:
            seen_keys[key] = row_index

    return ValidationReport(
        snapshot_name=snapshot.name,
        row_count=len(snapshot.rows),
        checked_cells=len(snapshot.rows) * len(contract.columns),
        issues=tuple(issues),
        duplicate_rows=duplicate_rows,
        unknown_columns=tuple(sorted(unknown_columns)),
    )


def issue_code_rate(report: ValidationReport, code: str) -> float:
    """Return the fraction of rows carrying at least one issue of ``code``."""

    if report.row_count == 0:
        return 0.0
    rows = {issue.row_index for issue in report.issues if issue.code == code and issue.row_index is not None}
    return round(len(rows) / report.row_count, 8)
