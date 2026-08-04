# Contributing

1. Create a focused branch from `main`.
2. Install development dependencies with `python -m pip install -e ".[dev]"`.
3. Add tests for every format, safety rule, or failure path changed.
4. Run `ruff check .` and `pytest`.
5. Do not add extension-only renaming as a conversion method.
6. Do not weaken atomic-write, archive-validation, overwrite-confirmation, or recycle-bin behavior.

Pull requests should explain the user-visible behavior, data-loss risks, dependencies, and validation performed.
