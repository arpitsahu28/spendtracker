"""
Tests for the Add Expense feature (Step 7).

Spec: .claude/specs/07-add-expense.md

Routes under test:
  GET  /expenses/add  — render form (auth required)
  POST /expenses/add  — validate + insert expense, redirect to /profile (auth required)

Structural notes:
- get_db() opens DB_PATH (a file path), not app.config['DATABASE'].
  Tests patch database.db.DB_PATH to a temp file so every get_db()
  call hits the same isolated on-disk DB.
- Auth uses email + password (not username).
- Registration requires name, email, password fields.
- Unauthenticated access redirects to /login (302), not 401.
"""

import pytest
import database.db as db_module
from app import app as flask_app
from database.db import init_db, get_db


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def app(tmp_path):
    """
    Flask app configured for testing with an isolated SQLite DB file.
    Patches DB_PATH so every get_db() call hits the same temp file.
    """
    db_file = str(tmp_path / "test_spendly.db")
    original_path = db_module.DB_PATH
    db_module.DB_PATH = db_file

    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })

    with flask_app.app_context():
        init_db()
        yield flask_app

    db_module.DB_PATH = original_path


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Test client already logged in as a freshly registered user."""
    client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'password123',
    })
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123',
    })
    return client


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #

class TestAuthGuard:
    def test_unauthenticated_get_redirects_to_login(self, client):
        response = client.get('/expenses/add')
        assert response.status_code == 302, "Unauthenticated GET should redirect"
        assert '/login' in response.headers['Location'], \
            "Redirect target must be /login"

    def test_unauthenticated_post_redirects_to_login(self, client):
        response = client.post('/expenses/add', data={
            'amount': '25.00',
            'category': 'Food',
            'date': '2026-05-01',
            'description': 'Lunch',
        })
        assert response.status_code == 302, "Unauthenticated POST should redirect"
        assert '/login' in response.headers['Location'], \
            "Redirect target must be /login"


# ------------------------------------------------------------------ #
# GET — form rendering                                                #
# ------------------------------------------------------------------ #

class TestGetForm:
    def test_get_returns_200(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert response.status_code == 200, "Authenticated GET should return 200"

    def test_get_renders_amount_field(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert b'amount' in response.data, \
            "Form must contain an amount field"

    def test_get_renders_category_field(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert b'category' in response.data, \
            "Form must contain a category field"

    def test_get_renders_date_field(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert b'date' in response.data, \
            "Form must contain a date field"

    def test_get_renders_description_field(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert b'description' in response.data, \
            "Form must contain a description field"

    def test_get_renders_expected_categories(self, auth_client):
        response = auth_client.get('/expenses/add')
        data = response.data
        for category in [b'Food', b'Transport', b'Bills', b'Health',
                         b'Entertainment', b'Shopping', b'Other']:
            assert category in data, f"Category option {category!r} must appear in form"

    def test_get_renders_form_tag(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert b'<form' in response.data, "Response must contain a <form> element"


# ------------------------------------------------------------------ #
# Happy path POST                                                     #
# ------------------------------------------------------------------ #

class TestHappyPathPost:
    def test_valid_post_redirects_to_profile(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '42.50',
            'category': 'Food',
            'date': '2026-05-20',
            'description': 'Grocery run',
        })
        assert response.status_code == 302, "Valid POST should redirect"
        assert '/profile' in response.headers['Location'], \
            "Redirect target must be /profile"

    def test_valid_post_saves_expense_to_db(self, auth_client):
        auth_client.post('/expenses/add', data={
            'amount': '99.00',
            'category': 'Bills',
            'date': '2026-05-15',
            'description': 'Internet bill',
        })
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM expenses WHERE description = ?", ("Internet bill",)
        ).fetchone()
        conn.close()
        assert row is not None, "Expense record must exist in the DB after POST"
        assert float(row["amount"]) == 99.00, "Saved amount must match submitted value"
        assert row["category"] == "Bills", "Saved category must match submitted value"
        assert row["date"] == "2026-05-15", "Saved date must match submitted value"

    def test_valid_post_appears_on_profile_page(self, auth_client):
        auth_client.post('/expenses/add', data={
            'amount': '18.75',
            'category': 'Transport',
            'date': '2026-05-22',
            'description': 'Bus ticket to downtown',
        })
        profile_response = auth_client.get('/profile')
        assert b'Bus ticket to downtown' in profile_response.data, \
            "New expense description must appear on the profile page"

    def test_valid_post_without_description_succeeds(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '10.00',
            'category': 'Other',
            'date': '2026-05-01',
            'description': '',
        })
        assert response.status_code == 302, \
            "POST without optional description should still succeed"
        assert '/profile' in response.headers['Location']

    def test_valid_post_saves_correct_user_id(self, auth_client):
        auth_client.post('/expenses/add', data={
            'amount': '55.00',
            'category': 'Health',
            'date': '2026-05-10',
            'description': 'Doctor visit',
        })
        conn = get_db()
        user = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("test@example.com",)
        ).fetchone()
        expense = conn.execute(
            "SELECT user_id FROM expenses WHERE description = ?", ("Doctor visit",)
        ).fetchone()
        conn.close()
        assert expense is not None, "Expense must be saved"
        assert expense["user_id"] == user["id"], \
            "Expense must be linked to the correct user"


# ------------------------------------------------------------------ #
# Profile page — Add Expense link                                     #
# ------------------------------------------------------------------ #

class TestProfileAddExpenseLink:
    def test_profile_has_link_to_add_expense(self, auth_client):
        response = auth_client.get('/profile')
        assert b'/expenses/add' in response.data, \
            "Profile page must contain a link to /expenses/add"


# ------------------------------------------------------------------ #
# Validation — invalid amount                                         #
# ------------------------------------------------------------------ #

class TestAmountValidation:
    @pytest.mark.parametrize("bad_amount", [
        "",          # empty
        "0",         # zero
        "-5.00",     # negative
        "abc",       # non-numeric
        "0.00",      # explicit zero as float string
        " ",         # whitespace only
    ])
    def test_invalid_amount_returns_200(self, auth_client, bad_amount):
        response = auth_client.post('/expenses/add', data={
            'amount': bad_amount,
            'category': 'Food',
            'date': '2026-05-01',
            'description': 'Test',
        })
        assert response.status_code == 200, \
            f"Invalid amount {bad_amount!r} should re-render the form (200), not redirect"

    @pytest.mark.parametrize("bad_amount", [
        "",
        "0",
        "-5.00",
        "abc",
        "0.00",
        " ",
    ])
    def test_invalid_amount_shows_error_message(self, auth_client, bad_amount):
        response = auth_client.post('/expenses/add', data={
            'amount': bad_amount,
            'category': 'Food',
            'date': '2026-05-01',
            'description': 'Test',
        })
        assert b'error' in response.data.lower() or b'Error' in response.data or \
               b'positive' in response.data or b'required' in response.data or \
               b'invalid' in response.data.lower(), \
            f"An error message must appear for invalid amount {bad_amount!r}"

    @pytest.mark.parametrize("bad_amount", [
        "",
        "0",
        "-5.00",
        "abc",
    ])
    def test_invalid_amount_does_not_save_to_db(self, auth_client, bad_amount):
        initial_count_response = get_db()
        before = initial_count_response.execute(
            "SELECT COUNT(*) FROM expenses"
        ).fetchone()[0]
        initial_count_response.close()

        auth_client.post('/expenses/add', data={
            'amount': bad_amount,
            'category': 'Food',
            'date': '2026-05-01',
            'description': 'Should not be saved',
        })

        conn = get_db()
        after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()
        assert after == before, \
            f"No expense should be inserted for invalid amount {bad_amount!r}"


# ------------------------------------------------------------------ #
# Validation — missing category                                       #
# ------------------------------------------------------------------ #

class TestCategoryValidation:
    def test_empty_category_returns_200(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '20.00',
            'category': '',
            'date': '2026-05-01',
            'description': 'Test',
        })
        assert response.status_code == 200, \
            "Missing category should re-render the form (200)"

    def test_empty_category_shows_error_message(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '20.00',
            'category': '',
            'date': '2026-05-01',
            'description': 'Test',
        })
        data = response.data
        assert (b'error' in data.lower() or b'category' in data.lower() or
                b'required' in data.lower()), \
            "An error message must appear when category is missing"

    def test_empty_category_does_not_save_to_db(self, auth_client):
        conn = get_db()
        before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        auth_client.post('/expenses/add', data={
            'amount': '20.00',
            'category': '',
            'date': '2026-05-01',
            'description': 'Should not be saved',
        })

        conn = get_db()
        after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()
        assert after == before, "No expense should be inserted when category is missing"


# ------------------------------------------------------------------ #
# Validation — missing / invalid date                                 #
# ------------------------------------------------------------------ #

class TestDateValidation:
    @pytest.mark.parametrize("bad_date", [
        "",           # empty
        "not-a-date", # non-date string
        "2026/05/01", # wrong format (slashes)
        "01-05-2026", # wrong order
    ])
    def test_invalid_date_returns_200(self, auth_client, bad_date):
        response = auth_client.post('/expenses/add', data={
            'amount': '20.00',
            'category': 'Food',
            'date': bad_date,
            'description': 'Test',
        })
        assert response.status_code == 200, \
            f"Invalid date {bad_date!r} should re-render the form (200)"

    @pytest.mark.parametrize("bad_date", [
        "",
        "not-a-date",
        "2026/05/01",
        "01-05-2026",
    ])
    def test_invalid_date_shows_error_message(self, auth_client, bad_date):
        response = auth_client.post('/expenses/add', data={
            'amount': '20.00',
            'category': 'Food',
            'date': bad_date,
            'description': 'Test',
        })
        data = response.data
        assert (b'error' in data.lower() or b'date' in data.lower() or
                b'valid' in data.lower() or b'required' in data.lower()), \
            f"An error message must appear for invalid date {bad_date!r}"

    @pytest.mark.parametrize("bad_date", [
        "",
        "not-a-date",
    ])
    def test_invalid_date_does_not_save_to_db(self, auth_client, bad_date):
        conn = get_db()
        before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        auth_client.post('/expenses/add', data={
            'amount': '20.00',
            'category': 'Food',
            'date': bad_date,
            'description': 'Should not be saved',
        })

        conn = get_db()
        after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()
        assert after == before, \
            f"No expense should be inserted for invalid date {bad_date!r}"
