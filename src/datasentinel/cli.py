from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import write_benchmark
from .sweep import parse_seed_list, write_sweep


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="datasentinel",
        description="Run reproducible tabular contract and drift experiments.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    benchmark = subparsers.add_parser("benchmark", help="Calibrate and score the synthetic benchmark")
    benchmark.add_argument("--seed", type=int, default=17)
    benchmark.add_argument("--output-dir", type=Path, default=Path("outputs/benchmark"))
    sweep = subparsers.add_parser("sweep", help="Repeat the benchmark over explicit seeds")
    sweep.add_argument("--seeds", default="17,29,41")
    sweep.add_argument("--output-dir", type=Path, default=Path("outputs/sweep"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "benchmark":
        payload = write_benchmark(args.output_dir, args.seed)
    else:
        payload = write_sweep(args.output_dir, parse_seed_list(args.seeds))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
