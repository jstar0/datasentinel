# DataSentinel

DataSentinel is a reproducible, CPU-friendly lab for a practical data-platform
question: can a table be admitted to a downstream workflow when its schema is
valid but its population has silently shifted?

The project combines an explicit column contract with distribution drift and a
single quality-gate decision. It is intentionally small enough to inspect:

- typed, nullable, range, category, and primary-key validation;
- row-level issue evidence instead of one opaque score;
- numeric PSI, categorical Jensen–Shannon divergence, and missingness change;
- validation-only threshold calibration, held-out test cases, and column-level
  precision/recall/F1 for drift alerts;
- deterministic JSON/CSV/Markdown reports plus SHA-256 manifests;
- an explicit clean synthetic fixture with quality corruption and population
  shift cases.

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked --dev
uv run datasentinel benchmark --output-dir outputs/benchmark --seed 17
uv run datasentinel sweep --output-dir outputs/sweep --seeds 17,29,41
```

The benchmark writes `benchmark.json`, `per_case.csv`, `report.md`, and a
`manifest.json` that hashes the other artifacts. The sweep repeats the same
contract over explicit seeds and reports mean/population-σ stability summaries.

## Design

The reference table is clean and is never used as a label-bearing test table.
Validation cases choose thresholds; held-out cases are scored once. The gate
fails on contract errors or calibrated drift alerts, while still returning all
row-level and column-level evidence for inspection. Duplicate keys are counted
separately from ordinary type/range violations so an operator can distinguish a
bad row from a replayed row.

This is an engineering benchmark, not a claim that PSI or Jensen–Shannon
divergence is universally optimal. Thresholds, bins, fixture size, and seed
are part of the artifact contract and must be held constant before comparing
runs.

## Honest boundary

DataSentinel is an independent implementation inspired by general tabular
quality and analytics work. It contains no customer rows, exports,
prompts, model responses, credentials, screenshots, or copied source files.
All values and labels in the benchmark are invented. The results do not imply
production data quality, fairness, privacy, compliance, or business uplift.

## Development

```bash
uv run pytest
uv run --with ruff ruff check src tests
uv lock --check
uv build
```

See [docs/architecture.md](docs/architecture.md) for the data flow.

## License

MIT; see [LICENSE](LICENSE).
