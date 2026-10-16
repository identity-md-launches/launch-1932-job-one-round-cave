# CSV Multiplicity

Compare two CSVs as exact full-row multisets within explicit keys. This gives
useful evidence when a key occurs more than once: how many copies of each
complete row value exist before and after, how many equal copies both sides
contain, and the surplus on each side. Every logical record occurrence is
listed. No individual occurrences are paired and no updates are inferred.

From the repository root, with Python 3.9+ and no dependencies or network:

```sh
python3 -B line-2/tools/csv-multiplicity/multiplicity.py line-2/tools/csv-multiplicity/demo-before.csv line-2/tools/csv-multiplicity/demo-after.csv --key item --key location --format text
```

Observed: five records on each side, three retained copies, two before-surplus
copies and two after-surplus copies, across four key groups. `flint/north`
is duplicated: quantity `2` occurs twice before and once after, `3` occurs
once on both sides, and `4` occurs only after. The tool reports these counts
without choosing which quantity-`2` occurrence survived or claiming a `2`
became a `4`. The changed header order is accepted. **Exit 1 is expected.**

Exit 0 means equal complete-row multisets; exit 1 means different
multiplicities; exit 2 means invalid input or command options. Equal multisets
can still have duplicate or empty keys: exit 0 never certifies stable identity,
unique keys, data correctness, or safety to delete rows. Repeat `--key` for a
composite key. Omit `--format text` for structured `csv-multiplicity/v1` JSON.
Reports go to stdout; input errors go to stderr. The tool writes no files.

For a gate that also requires every key to be non-ambiguous, add
`--fail-on-ambiguous`. It returns exit 1 if either side has a duplicate key or
an empty key component, even when the complete-row multisets are equal. This
does not change the report; it makes the safety decision explicit to a shell
caller.

For each variant, `retained_copies = min(before_count, after_count)`. The two
surpluses are the excess counts over that minimum. Summary totals obey:

```text
before_records = retained_copies + before_surplus_copies
after_records  = retained_copies + after_surplus_copies
```

These are row-value counts, not proof that any physical record persisted.
`before_records` and `after_records` within each variant list **all** its
occurrences; the tool never selects a subset as retained. Records are numbered
from 2 after the header; quoted multiline values occupy one logical record.
Groups include singleton and one-sided keys, so totals cover the entire input.
`duplicate_key_groups` counts keys repeated on either side;
`empty_key_groups` counts keys with any exactly empty component. These counts
can overlap. Whitespace-only keys are literal nonempty strings.

Both files must have exactly the same column names. Header order is ignored;
missing or extra columns reject the comparison with an explicit schema error,
preventing a partial-row equality claim. All columns participate, including
keys; there is no ignore option. Column names, key groups and row variants
have deterministic lexical ordering. Record occurrence lists preserve their
input order. Changing row order changes those record references, not counts.

Values remain exact strings: case, spaces, numeric spellings and Unicode are
not normalized. Empty key components are grouped literally and flagged, not
treated as known identities. JSON and text escape control characters. Output
is data for review, not executable code or a patch plan.

The retained real ZTO-first/IMD-second observation CSV also works offline:

```sh
python3 -B line-2/tools/csv-multiplicity/multiplicity.py shared/token-read-plan/observed.csv shared/token-read-plan/observed.csv --key token_address --format text
```

Observed: six historical observations retained, two duplicate key groups,
zero surplus copies, exit 0. Each token has three different observed fields,
so `token_address` groups them but does not identify individual observations.
This verifies comparison of retained data, not current balances, supply or a
fresh chain observation. The file is an optional example; the tool itself only
depends on its committed sibling reader.

Run the checks:

```sh
python3 -B -m unittest discover -s line-2/tools/csv-multiplicity -p 'test_*.py' -v
```

All 15 behavioral tests passed, including reordered duplicate rows and headers,
unequal multiplicities, conflicting full rows, one-sided keys, composite and
empty keys, exact strings, BOM and multiline CSV, schema rejection, malformed
input, inherited limits and path boundaries, safe text, deterministic order,
CLI statuses, unchanged input bytes, and 40 seeded conservation/reversal cases.
Temporary test fixtures remain under `test/scratch/`.

Uses `../csv-reconcile/reconcile.py` for its bounded workspace reader. Keep
both folders together. Inputs are strict UTF-8 CSV with optional BOM,
distinct nonempty headers, at most 16 MiB and 100,000 data records per file,
and resolved paths inside the current working directory. Both complete inputs
and reports are held in memory; these limits are not memory, CPU or output
budgets. Reports may exceed input size. Run against stable files: concurrent
modification is not detected. No network, environment variables, wallets,
keys, secrets or transactions are used.
