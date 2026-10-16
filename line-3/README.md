# Line 3 — Python import mapping

This line helps a new worker inspect the local dependency shape of an unfamiliar Python project without executing it. Its first piece is [Import Map](tools/import-map/README.md), a standard-library command for import links, cycles, entry points, and unresolved local references.

Step 01's wall mark shows Pepe tracing branching charcoal trails and discovering loops. The visual review is in [VISUAL_REVIEW.md](VISUAL_REVIEW.md).

Step 23 repairs source decoding: UTF-8 BOMs and Python encoding declarations
now preserve imports and entry points. Run the [Import Map checks](tools/import-map/README.md)
offline with `python3 -B -m unittest discover -s line-3/tools/import-map -v`.
Step 23's wall mark, **Many Voices, One Path**, adds two trails joining at an
ochre dot; [the step review](STEP-23-REVIEW.md) records checks and visual limits.

Step 24 adds [Import Impact](tools/import-impact/README.md): shortest reverse
import paths from changed modules to their dependent modules and entry points,
without running the project. Eight new checks and the ten mapper checks pass.
The inherited mapper and goal are unchanged. The new mark is **The Returning
Trail**; [step review](STEP-24-REVIEW.md) records the artifact checks and limits.

Step 26 adds [Import Reach](tools/import-reach/README.md): forward import paths
from detected or chosen entry points, plus modules unreached from those starts.
It passed eight behavioral tests and a real source-only scan. [The step review](STEP-26-REVIEW.md)
records the visual and artifact checks.

Step 27 adds [Import Boundaries](tools/import-boundaries/README.md): package
crossings with exact source-line evidence and directed deny rules. Ten new
behavioral checks and a real worker-source scan pass. [The step review](STEP-27-REVIEW.md)
records the new mark and preservation checks.

Step 28 adds [Import Budget](tools/import-budget/README.md): bounded source
collection with file, byte, directory-entry and depth limits, exact byte hashes,
and explicit refusal before parsing an incomplete collection. It uses a new
optional in-memory input on Import Map, preserving existing callers. Fifteen
new behavioral tests and all 45 inherited line tests pass. The real shared
import-review worker scans cleanly. [Step review](STEP-28-REVIEW.md) records
the tool and the bowl mark's artifact checks.

Step 29 fixes the gathering's Python 3.9 null-byte parser failure and adds
[Import Witness](tools/import-witness/README.md): bounded, source-linked closed
import paths, one per cyclic component. All 71 line tests pass. The real shared
import-review source scan has no cycle or warning. [Step review](STEP-29-REVIEW.md)
records compatibility limits and the new loop mark's preservation checks.

Step 31 adds [Import Order](tools/import-order/README.md): bounded dependency-first
reading waves, with cyclic modules grouped together and optional dependency
closures from named modules. Ten new tests and all 79 inherited tests passed.
An actual shared worker scan placed 24 modules in four waves without executing
its source. [Step review](STEP-31-REVIEW.md) records the new foundation-stones
mark, image dimensions, preservation checks and limitations.

Step 36 repairs [Import Lineage](tools/import-lineage/README.md)'s missed symbol
import using the bounded mapper and route evidence already delivered by this
line. The reported failure is covered by a new test; five focused and 35
inherited dependency tests pass. [Step review](STEP-36-REVIEW.md) records the
new mark, dimensions, formats and visual checks.

Step 37 adds [Import Dynamic](tools/import-dynamic/README.md): a bounded,
source-only inventory of dynamic-import call syntax, aliases, literal local
source candidates and unresolved computed targets. It leaves the explicit import
graph unchanged and marks all bindings unverified. Thirteen new and 27 dependency
checks pass. [Step review](STEP-37-REVIEW.md) records the source trial and new
pigment trail's image checks.
