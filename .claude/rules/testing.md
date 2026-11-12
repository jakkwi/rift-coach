---
paths:
  - "tests/**"
  - "src/**/*.py"
---
# Testing

- pytest. Tests mirror modules: `src/rift_coach/x.py` -> `tests/test_x.py`.
- No live League Client, Data Dragon or Claude calls in tests: use `tests/fixtures/` and fakes.
- Every bug fix comes with a test that fails before the fix.
- Run `ruff check . && pytest -q` before every commit.
