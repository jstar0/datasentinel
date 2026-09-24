# Contributing to DataSentinel

Contributions should keep the fixture deterministic, the contract rules
explicit, and the report reproducible from a recorded seed. Add a focused test
for every new validation rule or drift metric. Do not add customer rows,
identifiers, screenshots, credentials, private prompts, or generated exports.

Before opening a change, run:

```bash
uv run pytest
uv run --with ruff ruff check src tests
uv lock --check
uv build
```
