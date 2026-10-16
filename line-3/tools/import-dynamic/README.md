# Import Dynamic

Find dynamic-import call syntax that a static import graph can miss, without
importing or executing the inspected project. Python 3.9+; standard library
only. Run from the workspace root, keeping the sibling Import Budget and Import
Map tools beside this directory.

One command demonstrates it, including a source file with an execution trap:

```sh
python3 -B line-3/tools/import-dynamic/dynamic.py line-3/tools/import-dynamic/examples --json
```

The trial exited 0 and reported three call sites: aliased `load('plugin')` has
`plugin.py` as an exact local source candidate; a package-relative literal has
no matching local file; `__import__(selected_at_runtime)` remains computed.
The `raise RuntimeError` in the example never ran. Do not run the example itself.

For your project, replace the example path with an explicit source root inside
the current workspace. `--strict` exits 1 if any candidate or parse issue is
present; normal reporting exits 0 even with those findings. Collection or
analysis refusal exits 2 and emits a JSON error without partial call results.
`--json` includes source-byte hashes, collection limits and skipped-file counts.
Without it, the command prints one source location and classification per call.
Columns are zero-based AST UTF-8 byte offsets; lines are one-based.

It recognizes `__import__`, `builtins.__import__`, `importlib.import_module` and
explicit import aliases, retaining alias source lines. Literal names can be
matched to exact dotted local source names. Relative `import_module` names
require a literal package argument; builtin relative imports stay unresolved.
Conflicting or unpacked name arguments stay unknown. Module/package collisions
retain both candidate paths and are explicitly ambiguous. Computed targets,
missing context and malformed source remain visible. Every collected file is
parsed independently, including root initializers and colliding source files.

These are **syntactic candidates**, never added graph edges or proof of runtime
importability. Alias collection is file-wide, including nested and conditional
imports, and does not establish order or scope. Every call says
`binding_verified: false`: shadowing and rebinding can make matches false
positives. Other loaders, wrappers, `getattr`, wildcard aliases and generated
code can be missed. Missing local matches do not prove a module is external or
installed. Namespace-only prefixes are not exact source-file matches. Invalid
call arity and runtime argument types are not comprehensively validated.

Import Budget admits all bytes before parsing, with defaults of 1,000 source
files, 262,144 bytes per file, 8,388,608 bytes total, 20,000 directory entries and
depth 64. Override using `--max-files`, `--max-file-bytes`, `--max-total-bytes`,
`--max-entries`, `--max-depth`. Hidden/dependency directories, symlinks and
nonregular files are skipped. These are input bounds, not a sandbox or a CPU,
memory or elapsed-time guarantee. Inspect a stable tree. The supplied source
root controls dotted names; no runtime path, package installation or environment
is consulted. `status: complete` means collection/analysis finished, not that all
imports or execution paths are known.

Checks:

```sh
python3 -B -m unittest discover -s line-3/tools/import-dynamic -v
```

Thirteen behavioral tests passed: aliases, relative targets, computed and
unpacked arguments, collisions, encodings, parse issues, deterministic output,
ignored strings/comments, source hashes, execution traps, collection refusal
and CLI exits. The 27 mapper/collector checks also passed on scratch copies.
A real source-only scan of `shared/import-drift` read 27 files (132,621 bytes),
with zero candidate calls or parse issues. `observed-source.json` preserves that
snapshot manifest; this is an observation of those bytes, not a runtime claim.
No third-party dependency, chain access or coin is needed for source analysis.
