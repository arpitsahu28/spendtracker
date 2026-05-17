# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app
python3 app.py                  # starts dev server on http://localhost:5001

# Run all tests
pytest

# Run a single test file
pytest tests/test_auth.py

# Run a single test by name
pytest -k "test_login"
```

## Architecture

**Entry point:** `app.py` — all Flask routes are defined here. Routes return either `render_template(...)` for full pages or plain strings for unimplemented stubs.

**Database layer:** `database/db.py` is the sole place for SQLite access. It exposes three functions:
- `get_db()` — returns a connection with `row_factory` and foreign keys enabled
- `init_db()` — creates tables using `CREATE TABLE IF NOT EXISTS`
- `seed_db()` — inserts sample dev data

The SQLite file (`expense_tracker.db`) is gitignored and lives at the project root when created.

**Templates** use Jinja2 inheritance — all pages extend `templates/base.html`, which provides the navbar, footer, and links to `static/css/style.css` and `static/js/main.js`. The app name is **Spendly**.

**Unimplemented routes** currently return placeholder strings. The project is structured as a step-by-step tutorial — logout (Step 3), profile (Step 4), and expense CRUD (Steps 7–9) are not yet built.
