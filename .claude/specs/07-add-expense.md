# Spec: Add Expense

## Overview
This step implements the "Add Expense" feature, replacing the stub at `GET /expenses/add` with a real form that lets logged-in users record a new expense. A button on the profile page links to this form. On submit, the expense is saved to the database and the user is redirected to their profile. The expenses table already exists in the schema; this step adds the DB helper and route logic only.

## Depends on
- Step 01 (database setup) — expenses table exists
- Step 04/05 (profile page) — profile is where the "Add Expense" button lives
- Step 03 (login/logout) — session-based auth is required

## Routes
- `GET /expenses/add` — render add-expense form — logged-in only
- `POST /expenses/add` — process form submission, insert expense, redirect to profile — logged-in only

## Database changes
No schema changes. The `expenses` table already exists with columns: `id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

Add one new helper to `database/db.py`:
- `create_expense(user_id, amount, category, date, description)` — inserts a row into expenses and returns nothing.

## Templates
- **Create:** `templates/add_expense.html` — form with fields: amount (number, required), category (select, required), date (date, required), description (text, optional)
- **Modify:** `templates/profile.html` — add an "Add Expense" button/link that navigates to `url_for('add_expense')`

## Files to change
- `app.py` — replace `GET /expenses/add` stub with `GET`+`POST` route; import `create_expense`
- `database/db.py` — add `create_expense` helper
- `templates/profile.html` — add "Add Expense" button

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders) — never f-strings in SQL
- Passwords hashed with werkzeug (not applicable here but DB pattern must hold)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Redirect to `/profile` after successful POST — do not re-render the form
- Validate on POST: amount must be a positive number, category must be non-empty, date must be a valid `YYYY-MM-DD` string
- Abort with 401 if user is not logged in (or redirect to login)
- Categories to offer in the select: Food, Transport, Bills, Health, Entertainment, Shopping, Other

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in renders a form with amount, category, date, and description fields
- [ ] Submitting the form with valid data saves the expense and redirects to `/profile`
- [ ] The new expense appears in the transactions list on the profile page
- [ ] Submitting with a missing or invalid amount shows an error message on the form (does not crash)
- [ ] Submitting with a missing category shows an error message on the form
- [ ] The profile page has a visible "Add Expense" button/link that navigates to `/expenses/add`
