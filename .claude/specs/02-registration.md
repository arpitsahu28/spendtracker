# Spec: Registration

## Overview
Implement user registration so new visitors can create a Spendly account.
This step wires the existing `register.html` form to a `POST /register` route
that validates input, hashes the password, inserts the user into the `users`
table, and redirects on success. It is the first step in the auth flow and a
prerequisite for login, logout, and all logged-in features.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`)

## Routes
- `GET /register` — render registration form — public (already implemented as stub)
- `POST /register` — handle form submission, create user, redirect — public

## Database changes
No new tables or columns. Uses the existing `users` table:
- `name` TEXT NOT NULL
- `email` TEXT UNIQUE NOT NULL
- `password_hash` TEXT NOT NULL

A new DB helper `create_user(name, email, password)` must be added to
`database/db.py` to keep SQL out of the route.

## Templates
- **Modify:** `templates/register.html` — form already exists; ensure the
  `action` attribute uses `url_for('register')` (not a hardcoded path), and
  that the `{% if error %}` block is in place to surface validation errors.

## Files to change
- `app.py` — convert `GET /register` to handle both GET and POST; add
  validation logic and call `create_user`; flash-redirect on success
- `database/db.py` — add `create_user(name, email, password)` helper
- `templates/register.html` — fix hardcoded `/register` action to use
  `url_for('register')`

## Files to create
None.

## New dependencies
No new pip packages. Uses:
- `werkzeug.security.generate_password_hash` (already installed)
- `flask.session` for setting the session after registration
- `flask.redirect`, `flask.url_for`, `flask.request`, `flask.abort`
  (all part of Flask, already in requirements)

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders) — never f-strings in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic lives in `database/db.py` — route must not contain raw SQL
- On duplicate email, catch `sqlite3.IntegrityError` and re-render the form
  with a user-friendly error message (do not let the 500 bubble up)
- After successful registration, set `session['user_id']` and
  `session['user_name']`, then redirect to `/` (landing) until the dashboard
  exists
- Use `abort(400)` for truly malformed requests; use form re-render with
  `error=` for user-fixable validation failures
- Validate server-side: name non-empty, valid email format (basic check),
  password minimum 8 characters — do not rely solely on HTML `required`

## Definition of done
- [ ] Submitting the form with valid data creates a new row in `users`
- [ ] Password is stored as a hash, never plaintext
- [ ] Duplicate email shows an inline error on the form, not a 500
- [ ] Short password (< 8 chars) shows a validation error on the form
- [ ] Empty name or email shows a validation error on the form
- [ ] Successful registration sets `session['user_id']` and redirects
- [ ] Form `action` uses `url_for('register')`, not a hardcoded path
- [ ] `GET /register` still renders the empty form as before
