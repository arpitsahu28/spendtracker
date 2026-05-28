# Spec: Date Filter for Profile Page

## Overview
This feature adds a date-range filter to the profile page so users can narrow
the transaction history, summary stats, and category breakdown to a specific
period. The filter is submitted as a GET form — `start_date` and `end_date`
query parameters — so the URL is bookmarkable and the back button works
naturally. No new routes are needed; the existing `GET /profile` route is
extended to read the optional query params and pass them through to the DB
helpers.

## Depends on
- Step 1: Database setup (`expenses` table must exist)
- Step 3: Login / Logout (session `user_id` must be set)
- Step 4: Profile page UI (template structure already in place)
- Step 5: Backend routes for profile (live DB queries already wired)

## Routes
No new routes. The existing `GET /profile` route is modified to accept
optional `start_date` and `end_date` query parameters.

## Database changes
No schema changes. The existing `expenses` table already has a `date` column
(`TEXT`, format `YYYY-MM-DD`) that supports range filtering with `BETWEEN`.

## Templates
- **Modify:** `templates/profile.html`
  - Add a filter form above the transaction history section with two date
    inputs (`start_date`, `end_date`) and a submit button.
  - Pre-populate the inputs with the current filter values so the user sees
    what is active.
  - Show a "Showing filtered results" notice (or equivalent) when a filter is
    active so users know the stats are not all-time totals.
  - Add a "Clear" link that goes to `/profile` with no query params.

## Files to change
- `database/db.py`
  - `get_expense_stats(user_id, start_date=None, end_date=None)` — add
    optional date-range parameters; when provided, add a `WHERE date BETWEEN ?
    AND ?` clause to the stats queries.
  - `get_expenses_by_user(user_id, start_date=None, end_date=None)` — same
    optional date-range parameters on the existing SELECT.
  - `get_category_breakdown(user_id, start_date=None, end_date=None)` — same
    optional date-range parameters.
- `app.py`
  - `profile()` route — read `start_date` and `end_date` from
    `request.args`; validate that both are valid `YYYY-MM-DD` strings when
    provided (reject malformed values with a 400 or by ignoring them); pass
    them to the three DB helpers; also pass them into the template context so
    the form can be pre-populated.

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
- Date validation in the route must use `datetime.strptime` with `%Y-%m-%d`;
  silently drop an invalid date rather than crashing
- When only one date is supplied (e.g. `start_date` without `end_date`),
  treat the filter as inactive — both must be present to apply
- DB helpers must remain backward-compatible (existing call sites in tests
  that omit the date params must continue to work)
- Stats shown under a filter must reflect only expenses in the filtered range
- The filter form must use `method="get"` and `action="{{ url_for('profile') }}"`

## Definition of done
- [ ] Visiting `/profile` with no query params shows all-time data (no
  regression from Step 5)
- [ ] Submitting a valid `start_date` / `end_date` range filters the
  transaction list to only expenses whose `date` falls within the range
  (inclusive)
- [ ] Summary stats (total spent, transaction count, top category) reflect
  only the filtered expenses when a date range is active
- [ ] Category breakdown reflects only filtered expenses when a date range is
  active
- [ ] The filter inputs are pre-populated with the active filter values after
  submission
- [ ] A "Clear" link is visible when a filter is active and returns the page
  to the unfiltered state
- [ ] Submitting with `start_date` only (no `end_date`) shows all-time data
  (partial filter is ignored)
- [ ] Submitting a malformed date string (e.g. `start_date=not-a-date`) does
  not crash the server — all-time data is shown instead
- [ ] All SQL uses `?` placeholders — no string formatting in queries
