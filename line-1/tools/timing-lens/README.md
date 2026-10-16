# Timing Lens

Explain one saved public HTTP probe's latency and compare its recorded total
with an explicit inclusive millisecond budget. Python 3.10+ standard library
only, with the delivered sibling `failure-map/failure_map.py` retained.
No installation, network request, retry or file write occurs in this tool.

From the repository root, one command demonstrates it offline on a **real
swarm observation**:

```sh
python3 -B line-1/tools/timing-lens/timing_lens.py line-1/tools/timing-lens/observed-live.json --max-ms 500
```

When tried, this prints `within-budget`, `source_ok: true`, a 183.144 ms probe
total, a 141.801 ms connection-through-headers interval, a 41.343 ms unattributed
remainder, and 51.991 ms of wrapper overhead. The raw capture and reproducible
analysis are saved beside this README. The anonymous GET to
`https://api.imd.fun/launches` returned HTTP 200 and passed strict JSON checking;
this historical success does not establish current health. No body is retained.
The original capture command was:

```sh
python3 -B line-1/tools/deadline-sentry/deadline_sentry.py --deadline 8 https://api.imd.fun/launches --timeout 5 --max-bytes 262144 --max-redirects 0 --json
```

The probe's `headers_ms` starts before connection setup and ends after header
receipt. It includes connection/DNS/TLS, request transmission and header
waiting; it cannot isolate any of these or server processing. The tool sums
these separate per-hop intervals and subtracts them from the probe total only
when all are present. The remainder includes setup outside those intervals,
body reads, JSON checks, cleanup and any failed interval with no headers. It
is **not** a body download measurement. The difference between wrapper and
probe totals includes worker startup, communication and supervisor overhead.
Neither wall-clock timestamp subtraction nor guesses about network phases are
used. Every timing includes pointers into the original input document.

`--max-ms` is required, finite and between zero and 86,400,000 ms. It applies
only to `probe.elapsed_ms` (or direct `elapsed_ms`), including failed probes.
Exit **0** means that recorded total meets the budget, even if `source_ok` is
false. Exit **1** means `over-budget`, `unknown` (missing total), or `unobserved`
(no completed worker report). It does not certify HTTP health. Exit **2** means
invalid arguments, evidence or path. Missing breakdown fields stay visible in
`missing`; they do not invalidate an otherwise known total-budget comparison.
A killed worker's elapsed time is never treated as a response latency.

Durations must be finite nonnegative JSON numbers at most one day. Booleans,
strings, impossible sums and contradictory source health are refused. Rounded
interval sums may exceed the total by at most 0.0005 ms per summand plus total;
wrapper subtraction permits 0.001 ms. Such tiny negative differences clamp to
zero and the tolerance is reported. Budget comparisons use the recorded total
exactly, with no added tolerance. There are at most eleven hops.

The inherited loader accepts only regular UTF-8 JSON files within the current
workspace, at most 1 MiB; it rejects duplicate keys and nonfinite numbers. The
lens validates fields used here, not the complete producer schema. Saved timing
claims are unauthenticated, and one sample cannot establish uptime, throughput,
a bottleneck or root cause. Concurrent replacement of input files is outside
its containment guarantee. No environment, secrets, wallets, payments or coin
are needed. The sibling loader is the only runtime project dependency.

All **14 offline behavioral tests passed**, covering inclusive budgets,
missing evidence, failed-but-fast probes, watchdogs, rounding, contradictory
intervals, provenance, invalid numbers, retained real evidence and CLI exits:

```sh
python3 -B -m unittest discover -s line-1/tools/timing-lens -v
```
