# DataSentinel architecture

DataSentinel has four deliberately separated layers:

1. `models.py` defines immutable contracts, snapshots, issues, drift metrics,
   and gate decisions. It contains no random generation or file I/O.
2. `fixture.py` creates a clean reference table and labelled validation/test
   scenarios from an explicit seed. The scenarios are synthetic and expose the
   expected shift columns only to the benchmark evaluator.
3. `validation.py` checks each row against the contract and returns evidence;
   `drift.py` profiles distributions against the reference. `gate.py` combines
   both signals without hiding either report.
4. `benchmark.py` calibrates thresholds on validation scenarios, evaluates
   held-out scenarios, and writes hash-bound artifacts. `sweep.py` repeats the
   same path for explicit seeds.

The primary key is excluded from distribution drift so a harmless identifier
renumbering cannot dominate the population profile. Missingness is measured for
every profiled column and contributes to the alert score. Numeric drift uses
reference-derived quantile bins; categorical drift uses a fixed sorted support
and an epsilon-stabilized Jensen–Shannon calculation.

No layer calls a network service or reads an external file. A future adapter
may load a table, but it must convert it into `TableSnapshot` and preserve the
same validation, threshold, and evidence contract.
