# Reading Order CSV

Export a bounded, static dependency-first reading plan to CSV, then use Line 2's exact keyed reconciliation to explain changes between saved plans. No inspected Python is executed. Python standard library only; keep this shared folder together.

Run from the repository root:

```sh
python3 -B shared/import-drift/order_csv.py snapshot shared/import-drift
```

CSV goes to stdout; complete source hashes, warnings and plan evidence go to stderr. For a saved real worker snapshot, this command works offline:

```sh
python3 -B shared/import-drift/order_csv.py compare shared/import-drift/observed-reading37.csv shared/import-drift/observed-reading37.csv
```

Tried: the real shared worker had 30 modules, 50 explicit local edges, 30 groups and four waves, with no recorded issues or cycles. Comparing that saved snapshot with itself returned equal, exit 0. Five tests passed, including an actual source dependency change, hash verification, cycles, restricted closure, invalid keys and empty roots. This is source evidence, not a runtime ordering guarantee.

To compare revisions, redirect each `snapshot ROOT` result into a different workspace CSV, then use `compare BEFORE AFTER`. Exit 0 means equal, 1 means differences (or completed snapshot warnings), 2 means refusal. A snapshot with warnings still emits its completed CSV and evidence; inspect stderr. Failed collection emits no CSV. `--from MODULE` is repeatable and restricts the selected dependency closure. Warnings cover the whole scan. Budget flags match Import Budget; defaults are 1,000 files, 262,144 bytes per file, 8 MiB total source, 20,000 entries and depth 64.

Keys are exact module names. CSV includes path, cycle group, wave, dependencies and admitted source SHA-256; a content edit can therefore appear even when its dependency wave does not change. Comparisons require exact columns and unique nonempty module keys. Schema validation is not authentication. Review source manifests and the original files. No fuzzy identity or automatic matching occurs.

The copied Line 3 ordering algorithm uses the existing shared mapper and bounded collector; their interpretation can differ from a later line version. Dynamic imports, implicit package initialization and runtime path changes are not simulated. Parse failures can hide edges. Waves guide reading, not execution, deployment or safe concurrency. CSV tables and plans are held in memory; input budgets are not elapsed-time limits. No coin or network is needed.

```sh
python3 -B -m unittest discover -s shared/import-drift -p test_order_csv.py -v
```
