# Spec: Login and Logout

## Overview
Implement login and logout so registered users can authenticate into Spendly
and end their session. This step wires the existing `login.html` form to a
`POST /login` route that verifies credentials against the hashed password in
the `users` table, sets the Flask session on success, and redirects. It also
converts the `/logout` stub into a working route that clears the session and
redirects to the landing page. This completes the core auth flow started in
Step 02 and is a prerequisite for all protected routes.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`)
- Step 02 — Registration (`create_user`, `session['user_id']` / `session['user_name']` convention)

## Routes
- `GET /login` — render login form — public (already implemented as stub)
- `POST /login` — validate credentials, set session, redirect — public
- `GET /logout` — clear session, redirect to landing — public (stub exists, needs implementation)

## Database changes
No new tables or columns. Uses the existing `users` table.

A new DB helper `get_user_by_email(email)` must be added to `database/db.py`
to look up a user by email and return their `id`, `name`, and `password_hash`
for credential verification. No SQL in the route.

## Templates
- **Modify:** `templates/login.html` — ensure the form `action` uses
  `url_for('login')` (not a hardcoded path), method is `POST`, and a
  `{% if error %}` block surfaces validation/auth errors inline.

## Files to change
- `app.py` — convert `GET /login` to handle both GET and POST; add validation
  and credential-check logic using `get_user_by_email`; implement `GET /logout`
  to clear session and redirect
- `database/db.py` — add `get_user_by_email(email)` helper
- `templates/login.html` — fix form action to use `url_for('login')`, add
  error display block if not already present

## Files to create
None.

## New dependencies
No new pip packages. Uses:
- `werkzeug.security.check_password_hash` (already installed via werkzeug)
- `flask.session`, `flask.redirect`, `flask.url_for`, `flask.request`
  (all part of Flask, already in requirements)

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders) — never f-strings in SQL
- Passwords verified with `werkzeug.security.check_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic lives in `database/db.py` — route must not contain raw SQL
- On invalid email or wrong password, re-render the form with a generic error
  message ("Invalid email or password") — do not distinguish between the two
  to avoid user enumeration
- After successful login, set `session['user_id']` and `session['user_name']`,
  then redirect to `/` (landing) until the dashboard exists
- Logout must call `session.clear()` and redirect to `url_for('landing')`
- Use `abort(405)` for unexpected methods; form re-render with `error=` for
  auth failures

## Definition of done
- [ ] Submitting valid credentials sets `session['user_id']` and redirects to `/`
- [ ] Wrong password shows "Invalid email or password" inline — no 500
- [ ] Unknown email shows "Invalid email or password" inline — no 500
- [ ] Empty email or password shows a validation error on the form
- [ ] `GET /logout` clears the session and redirects to the landing page
- [ ] After logout, `session['user_id']` is no longer set
- [ ] Form `action` uses `url_for('login')`, not a hardcoded path
- [ ] `GET /login` still renders the empty form as before
- [ ] No raw SQL in `app.py` — all queries go through `database/db.py`
