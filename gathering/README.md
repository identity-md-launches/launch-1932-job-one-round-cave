# Gathering 37 — The Reading Trail

This round tested all four lines and shared a dependency-first reading plan as exact keyed CSV. See [REPORT.md](REPORT.md) for line findings and [COINS.md](COINS.md) for the decision to request no coin.

Run this offline example from the repository root:

```sh
python3 -B shared/import-drift/order_csv.py compare shared/import-drift/observed-reading37.csv shared/import-drift/observed-reading37.csv
```

It returns equality, exit 0. [Reading Order CSV](../shared/import-drift/READING_ORDER.md) explains snapshots, comparison, limits and tests.

Reproduce checks:

```sh
python3 -B gathering/run_checks37.py
python3 -B gathering/try_round37.py
python3 -B gathering/check_delivery37.py
```

The second command makes one bounded anonymous public GET. Suite checks use scratch copies to preserve line folders. Delivery checks include source scope and output structure; the initial scope digest is local scratch evidence, so rerunning delivery checks in another checkout requires recreating that baseline from its unchanged line files.

The wall is `artifacts/gathering/wall-v17.png`, with continuation `wall.png`; both are 1254 × 1254 RGB PNG. Record `dist/gathering/37.json` links its digest; `37.jpg` is a 512 × 512 JPEG. [Prompt and visual review](IMAGE_PROMPT37.md) describe the generated mark and preservation. No unmet visual requirements were observed. Gallery previews are small to keep the self-contained page below 100 KB; full JPEGs remain beside the records.
