# Spec: Backend Routes for Profile Page

## Overview
This feature replaces the hardcoded data in the `/profile` route with real database queries. The profile page UI (built in Step 4) already accepts `user`, `stats`, `transactions`, and `categories` context variables — this step wires those variables to live SQLite data for the logged-in user. New helper functions are added to `database/db.py` and the route in `app.py` is updated to call them.

## Depends on
- Step 1: Database setup (`users` and `expenses` tables must exist)
- Step 2: Registration (users must be creatable)
- Step 3: Login + Logout (session `user_id` must be set on login)
- Step 4: Profile page UI (template already built and expecting these context shapes)

## Routes
- `GET /profile` — existing route; no URL change — logged-in only. Replace hardcoded data with live DB queries.

No new routes needed.

## Database changes
No schema changes. The existing `users` and `expenses` tables are sufficient.

## Templates
- **Modify:** `templates/profile.html` — update `member_since` display if the format changes (DB stores ISO datetime; format it for display). No structural changes required if the template already uses `user.member_since`, `stats.*`, `transactions`, and `categories` variables.

## Files to change
- `database/db.py` — add four new helper functions:
  - `get_user_by_id(user_id)` — returns `id, name, email, created_at` for a given user id
  - `get_expenses_by_user(user_id)` — returns all expenses for the user ordered by `date DESC`, each row as `date, description, category, amount`
  - `get_expense_stats(user_id)` — returns a dict with `total_spent` (sum of amount), `transaction_count` (count), and `top_category` (category with highest total amount)
  - `get_category_breakdown(user_id)` — returns a list of `{name, amount, percent}` dicts, one per category, sorted by amount descending; percent is each category's share of total spend rounded to the nearest integer
- `app.py` — update the `profile()` route to:
  - Call `get_user_by_id(session["user_id"])` and `abort(404)` if not found
  - Call `get_expense_stats(user_id)` and `get_expenses_by_user(user_id)` and `get_category_breakdown(user_id)`
  - Format `created_at` (ISO datetime string from DB) into a human-readable `member_since` string (e.g. "May 2026") before passing to the template
  - Pass real data dicts to `render_template("profile.html", ...)`
  - Remove all hardcoded demo data

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
- Parameterised queries only — never f-strings in SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All DB logic stays in `database/db.py` — the route function only calls helpers and passes results to the template
- `get_expense_stats` must handle users with zero expenses gracefully (return zeros/None, not crash)
- `get_category_breakdown` percents must sum to 100 for users with expenses; return an empty list for users with none
- Format amounts as dollar strings (`"$12.50"`) inside the DB helpers so the template receives the same shape as the hardcoded data did
- Format dates for the transactions list as `"Mon DD, YYYY"` (e.g. `"May 01, 2026"`) inside the helper so the template is unchanged

## Definition of done
- [ ] Logging in as the seeded demo user and visiting `/profile` shows the demo user's real name and email (not "Demo User" / "demo@spendly.com" hardcoded strings)
- [ ] The transaction history table shows rows pulled from the `expenses` table, not hardcoded Python lists
- [ ] Summary stats (total spent, transaction count, top category) reflect the actual expenses in the DB
- [ ] Category breakdown reflects actual per-category totals from the DB
- [ ] Visiting `/profile` as a new user with zero expenses does not crash — the page renders with zero-state values
- [ ] Visiting `/profile` without a session redirects to `/login`
- [ ] No hardcoded demo data remains in `app.py`'s `profile()` route
- [ ] All SQL in `database/db.py` uses `?` placeholders — no string formatting
