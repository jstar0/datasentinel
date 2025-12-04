from pathlib import Path

from datasentinel.cli import main


def test_cli_benchmark_and_sweep(tmp_path: Path, capsys) -> None:
    assert main(["benchmark", "--seed", "17", "--output-dir", str(tmp_path / "benchmark")]) == 0
    assert main(["sweep", "--seeds", "17,29", "--output-dir", str(tmp_path / "sweep")]) == 0
    output = capsys.readouterr().out
    assert '"benchmarkVersion": 1' in output
    assert '"sweepVersion": 1' in output
