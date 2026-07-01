See @README.md for the purpose and for examples of this library.

- Programming language: python with strict typechecking
- No external dependencies
- Run tests:
  - `run-tests` (fast, only for the current python version)
  - `run-tests-all-pyversions` (slow, for all supported python versions)

## Static typing

- The codebase is fully statically typed and must type-check cleanly under
  **pyright in strict mode**. Configuration lives in `pyrightconfig.json`
  (`typeCheckingMode: "strict"`, targeting the oldest supported Python, 3.9).
- Type-check with: `run-typecheck` (runs `pyright` from the project root).
  It must report **0 errors** for both `src` and `tests`.
- Keep new code strictly typed: annotate all public functions and avoid
  implicit `Any`. Any intentional escape hatch (e.g. a deprecated stdlib call)
  must be a narrowly-scoped `# pyright: ignore[<rule>]` with a comment
  explaining why.
- The package ships a PEP 561 `py.typed` marker (`src/py.typed`) so that type
  checkers treat `shell` as typed for downstream consumers. It is included in
  the distribution via `package_data` in `setup.py` and `MANIFEST.in`; keep
  those in sync if the packaging layout changes.
