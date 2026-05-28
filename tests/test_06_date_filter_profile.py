"""
Tests for date-range filter on GET /profile (Step 6).

Spec: .claude/specs/06-date-filter-profile.md

Key structural notes:
- get_db() opens DB_PATH (a file), not app.config['DATABASE'].
  Tests patch database.db.DB_PATH to a temp file so every get_db()
  call within a single test hits the same on-disk DB.
- Auth uses email + password (not username).
- "Showing filtered results" text is rendered by profile.html when
  both start_date and end_date are present in the template context.
"""

import os
import tempfile
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
    Yield the Flask app configured for testing with an isolated
    SQLite DB file.  Patches DB_PATH so every get_db() call in both
    app.py and database/db.py hits the same temp file.
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
def seeded_client(client):
    """
    A logged-in test client whose DB contains three expenses spread
    across distinct dates:
      - 2026-01-10  Food         $10.00
      - 2026-03-15  Transport    $50.00
      - 2026-06-20  Bills        $200.00

    The filter range [2026-01-10, 2026-03-15] covers the first two
    expenses only, making assertions deterministic.
    """
    # Register and log in
    client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'password123',
    })
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123',
    })

    # Fetch the user_id from DB, then insert known expenses
    conn = get_db()
    user = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("test@example.com",)
    ).fetchone()
    user_id = user["id"]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [
            (user_id, 10.00,  "Food",      "2026-01-10", "Breakfast"),
            (user_id, 50.00,  "Transport", "2026-03-15", "Bus pass"),
            (user_id, 200.00, "Bills",     "2026-06-20", "Rent"),
        ],
    )
    conn.commit()
    conn.close()

    return client


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #

class TestAuthGuard:
    def test_unauthenticated_profile_redirects_to_login(self, client):
        response = client.get('/profile')
        assert response.status_code == 302, "Expected redirect for unauthenticated user"
        assert '/login' in response.headers['Location'], "Should redirect to /login"

    def test_unauthenticated_profile_with_date_params_redirects_to_login(self, client):
        response = client.get('/profile?start_date=2026-01-01&end_date=2026-03-31')
        assert response.status_code == 302, "Expected redirect even with date params"
        assert '/login' in response.headers['Location'], "Should redirect to /login"


# ------------------------------------------------------------------ #
# Happy path — unfiltered                                             #
# ------------------------------------------------------------------ #

class TestUnfilteredProfile:
    def test_profile_loads_with_200(self, seeded_client):
        response = seeded_client.get('/profile')
        assert response.status_code == 200, "Profile page should return 200"

    def test_unfiltered_shows_all_transactions(self, seeded_client):
        response = seeded_client.get('/profile')
        data = response.data
        # All three descriptions must appear
        assert b'Breakfast' in data, "First expense should appear unfiltered"
        assert b'Bus pass'  in data, "Second expense should appear unfiltered"
        assert b'Rent'      in data, "Third expense should appear unfiltered"

    def test_unfiltered_total_reflects_all_expenses(self, seeded_client):
        response = seeded_client.get('/profile')
        # Total = 10 + 50 + 200 = 260.00
        assert b'$260.00' in response.data, "All-time total should be $260.00"

    def test_unfiltered_transaction_count(self, seeded_client):
        # Three rows — the count stat should show 3
        response = seeded_client.get('/profile')
        assert b'3' in response.data, "Transaction count should be 3 when unfiltered"

    def test_unfiltered_does_not_show_filter_notice(self, seeded_client):
        response = seeded_client.get('/profile')
        assert b'Showing filtered results' not in response.data, \
            "Filter notice must NOT appear when no filter is active"


# ------------------------------------------------------------------ #
# Happy path — valid date range filter                                #
# ------------------------------------------------------------------ #

class TestValidDateFilter:
    """
    Filter: 2026-01-10 to 2026-03-15
    Covers: Food $10 + Transport $50
    Excludes: Bills $200 (2026-06-20)
    """

    def test_filtered_excludes_out_of_range_expense(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=2026-01-10&end_date=2026-03-15'
        )
        assert b'Rent' not in response.data, \
            "Out-of-range expense should be excluded from filtered view"

    def test_filtered_includes_in_range_expenses(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=2026-01-10&end_date=2026-03-15'
        )
        assert b'Breakfast' in response.data, "In-range expense should be shown"
        assert b'Bus pass'  in response.data, "In-range expense should be shown"

    def test_filtered_total_reflects_only_range(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=2026-01-10&end_date=2026-03-15'
        )
        # 10 + 50 = 60.00
        assert b'$60.00' in response.data, "Filtered total should be $60.00"

    def test_filtered_transaction_count_reflects_only_range(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=2026-01-10&end_date=2026-03-15'
        )
        # Two transactions in range; page should NOT show '3'
        assert b'3' not in response.data, \
            "Transaction count of 3 must not appear under filtered view"

    def test_filtered_category_breakdown_excludes_out_of_range(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=2026-01-10&end_date=2026-03-15'
        )
        # Bills category only has the 2026-06-20 expense — must not appear
        assert b'Bills' not in response.data, \
            "Bills category should not appear in filtered breakdown"

    def test_filtered_top_category_is_transport(self, seeded_client):
        # Transport ($50) > Food ($10) within the filter range
        response = seeded_client.get(
            '/profile?start_date=2026-01-10&end_date=2026-03-15'
        )
        assert b'Transport' in response.data, \
            "Top category should be Transport within the filtered range"

    def test_filter_is_inclusive_of_boundary_dates(self, seeded_client):
        # start_date == the exact date of the first expense
        response = seeded_client.get(
            '/profile?start_date=2026-01-10&end_date=2026-01-10'
        )
        assert b'Breakfast' in response.data, "Start-date boundary should be inclusive"
        assert b'Bus pass'  not in response.data, "Expense after boundary should be excluded"


# ------------------------------------------------------------------ #
# Filter state — pre-population and notice                           #
# ------------------------------------------------------------------ #

class TestFilterState:
    def test_active_filter_shows_filter_notice(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=2026-01-10&end_date=2026-03-15'
        )
        assert b'Showing filtered results' in response.data, \
            "Filter notice must appear when both date params are valid"

    def test_active_filter_prepopulates_start_date_input(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=2026-01-10&end_date=2026-03-15'
        )
        assert b'2026-01-10' in response.data, \
            "start_date value should be pre-populated in the response"

    def test_active_filter_prepopulates_end_date_input(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=2026-01-10&end_date=2026-03-15'
        )
        assert b'2026-03-15' in response.data, \
            "end_date value should be pre-populated in the response"

    def test_active_filter_shows_clear_link(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=2026-01-10&end_date=2026-03-15'
        )
        assert b'Clear' in response.data, \
            "Clear link must be visible when filter is active"

    def test_inactive_filter_does_not_prepopulate_dates(self, seeded_client):
        response = seeded_client.get('/profile')
        # The input values should be empty strings, not stray dates
        assert b'value="2026-01-10"' not in response.data, \
            "start_date should not be pre-populated when no filter is active"
        assert b'value="2026-03-15"' not in response.data, \
            "end_date should not be pre-populated when no filter is active"


# ------------------------------------------------------------------ #
# Input isolation — partial filter treated as inactive               #
# ------------------------------------------------------------------ #

class TestPartialFilter:
    def test_start_date_only_shows_all_time_data(self, seeded_client):
        response = seeded_client.get('/profile?start_date=2026-01-10')
        # All three expenses should appear
        assert b'Breakfast' in response.data, "All expenses must show with start_date only"
        assert b'Bus pass'  in response.data, "All expenses must show with start_date only"
        assert b'Rent'      in response.data, "All expenses must show with start_date only"

    def test_start_date_only_no_filter_notice(self, seeded_client):
        response = seeded_client.get('/profile?start_date=2026-01-10')
        assert b'Showing filtered results' not in response.data, \
            "Filter notice must NOT appear when only start_date is supplied"

    def test_end_date_only_shows_all_time_data(self, seeded_client):
        response = seeded_client.get('/profile?end_date=2026-03-15')
        assert b'Breakfast' in response.data, "All expenses must show with end_date only"
        assert b'Bus pass'  in response.data, "All expenses must show with end_date only"
        assert b'Rent'      in response.data, "All expenses must show with end_date only"

    def test_end_date_only_no_filter_notice(self, seeded_client):
        response = seeded_client.get('/profile?end_date=2026-03-15')
        assert b'Showing filtered results' not in response.data, \
            "Filter notice must NOT appear when only end_date is supplied"

    def test_start_date_only_total_is_all_time(self, seeded_client):
        response = seeded_client.get('/profile?start_date=2026-01-10')
        assert b'$260.00' in response.data, \
            "All-time total must be shown when filter is partial"

    def test_end_date_only_total_is_all_time(self, seeded_client):
        response = seeded_client.get('/profile?end_date=2026-03-15')
        assert b'$260.00' in response.data, \
            "All-time total must be shown when filter is partial"


# ------------------------------------------------------------------ #
# Validation — malformed date strings                                 #
# ------------------------------------------------------------------ #

class TestMalformedDates:
    def test_both_malformed_returns_200(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=not-a-date&end_date=also-bad'
        )
        assert response.status_code == 200, \
            "Malformed dates must not crash the server (no 500)"

    def test_both_malformed_shows_all_time_data(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=not-a-date&end_date=also-bad'
        )
        assert b'Breakfast' in response.data, "All expenses shown when dates are malformed"
        assert b'Rent'      in response.data, "All expenses shown when dates are malformed"

    def test_both_malformed_no_filter_notice(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=not-a-date&end_date=also-bad'
        )
        assert b'Showing filtered results' not in response.data, \
            "Filter notice must NOT appear for malformed dates"

    def test_start_malformed_end_valid_shows_all_time(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=not-a-date&end_date=2026-03-15'
        )
        assert response.status_code == 200, "Mixed malformed/valid must not crash"
        assert b'Showing filtered results' not in response.data, \
            "Filter must be ignored when start_date is malformed"

    def test_start_valid_end_malformed_shows_all_time(self, seeded_client):
        response = seeded_client.get(
            '/profile?start_date=2026-01-10&end_date=not-a-date'
        )
        assert response.status_code == 200, "Mixed valid/malformed must not crash"
        assert b'Showing filtered results' not in response.data, \
            "Filter must be ignored when end_date is malformed"

    def test_empty_strings_treated_as_no_filter(self, seeded_client):
        response = seeded_client.get('/profile?start_date=&end_date=')
        assert response.status_code == 200, "Empty date strings must not crash"
        assert b'$260.00' in response.data, \
            "Empty strings must show all-time data"
