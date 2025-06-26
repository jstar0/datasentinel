"""DataSentinel: auditable synthetic tabular quality and drift experiments."""

from .benchmark import benchmark_payload, write_benchmark
from .drift import (
    apply_thresholds,
    calibrate_thresholds,
    categorical_js,
    classification_summary,
    numeric_psi,
    profile_drift,
)
from .fixture import Dataset, Scenario, create_dataset, make_contract
from .gate import evaluate_gate
from .models import (
    ColumnSpec,
    DriftMetric,
    DriftReport,
    GateDecision,
    TableContract,
    TableSnapshot,
    ValidationIssue,
    ValidationReport,
)
from .sweep import parse_seed_list, seed_sweep_payload, write_sweep
from .validation import issue_code_rate, validate_snapshot

__version__ = "0.1.0"

__all__ = [
    "ColumnSpec",
    "Dataset",
    "DriftMetric",
    "DriftReport",
    "GateDecision",
    "Scenario",
    "TableContract",
    "TableSnapshot",
    "ValidationIssue",
    "ValidationReport",
    "__version__",
    "apply_thresholds",
    "benchmark_payload",
    "calibrate_thresholds",
    "categorical_js",
    "classification_summary",
    "create_dataset",
    "evaluate_gate",
    "issue_code_rate",
    "make_contract",
    "numeric_psi",
    "parse_seed_list",
    "profile_drift",
    "seed_sweep_payload",
    "validate_snapshot",
    "write_benchmark",
    "write_sweep",
]
