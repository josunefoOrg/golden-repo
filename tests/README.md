# tests

Test suite for repositories generated from this template.

- The CI workflow (`.github/workflows/ci.yml`) runs `pytest` here on every pull request and push to `main`; the `test` job is a required status check for branch protection.
- Install dev dependencies with `pip install -r tools/requirements.txt` (add `pytest` there or to a `requirements-dev.txt` as your project grows).
- Add your tests as `test_*.py` files in this folder. Replace `test_smoke.py` with real tests for your project.

Run locally:

```bash
pytest -q
```
