import os
import sqlite3

from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'spendly.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def create_user(name, email, password):
    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    user = conn.execute(
        "SELECT id, name FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return user


def get_user_by_email(email):
    conn = get_db()
    user = conn.execute(
        "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return user


def get_expense_stats(user_id, start_date=None, end_date=None):
    date_filter = "AND date BETWEEN ? AND ?" if (start_date and end_date) else ""
    base_params = (user_id, start_date, end_date) if (start_date and end_date) else (user_id,)
    conn = get_db()
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS transaction_count,
               COALESCE(SUM(amount), 0) AS total_amount
        FROM expenses WHERE user_id = ? {date_filter}
        """,
        base_params,
    ).fetchone()
    top = conn.execute(
        f"""
        SELECT category FROM expenses WHERE user_id = ? {date_filter}
        GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1
        """,
        base_params,
    ).fetchone()
    conn.close()
    return {
        "total_spent":       f"${row['total_amount']:.2f}",
        "transaction_count": row["transaction_count"],
        "top_category":      top["category"] if top else "N/A",
    }


def get_expenses_by_user(user_id, start_date=None, end_date=None):
    from datetime import datetime
    date_filter = "AND date BETWEEN ? AND ?" if (start_date and end_date) else ""
    base_params = (user_id, start_date, end_date) if (start_date and end_date) else (user_id,)
    conn = get_db()
    rows = conn.execute(
        f"""
        SELECT date, description, category,
               printf('$%.2f', amount) AS amount
        FROM expenses WHERE user_id = ? {date_filter}
        ORDER BY date DESC
        """,
        base_params,
    ).fetchall()
    conn.close()
    return [
        {
            "date":        datetime.strptime(r["date"], "%Y-%m-%d").strftime("%b %d, %Y"),
            "description": r["description"],
            "category":    r["category"],
            "amount":      r["amount"],
        }
        for r in rows
    ]


def get_category_breakdown(user_id, start_date=None, end_date=None):
    date_filter = "AND date BETWEEN ? AND ?" if (start_date and end_date) else ""
    base_params = (user_id, start_date, end_date) if (start_date and end_date) else (user_id,)
    conn = get_db()
    rows = conn.execute(
        f"""
        SELECT category AS name, SUM(amount) AS raw_amount
        FROM expenses WHERE user_id = ? {date_filter}
        GROUP BY category ORDER BY raw_amount DESC
        """,
        base_params,
    ).fetchall()
    conn.close()
    if not rows:
        return []
    total = sum(r["raw_amount"] for r in rows)
    return [
        {
            "name":    r["name"],
            "amount":  f"${r['raw_amount']:.2f}",
            "percent": round(r["raw_amount"] / total * 100),
        }
        for r in rows
    ]


def get_monthly_spend(user_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT month, total FROM (
            SELECT strftime('%Y-%m', date) AS month, SUM(amount) AS total
            FROM expenses WHERE user_id = ?
            GROUP BY month ORDER BY month DESC LIMIT 12
        ) ORDER BY month ASC
    """, (user_id,)).fetchall()
    conn.close()
    return [{"month": r["month"], "total": round(r["total"], 2)} for r in rows]


def seed_db():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count > 0:
        conn.close()
        return

    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    expenses = [
        (user_id, 12.50,  "Food",          "2026-05-01", "Lunch"),
        (user_id, 45.00,  "Transport",     "2026-05-03", "Monthly bus pass"),
        (user_id, 120.00, "Bills",         "2026-05-05", "Electricity bill"),
        (user_id, 30.00,  "Health",        "2026-05-08", "Pharmacy"),
        (user_id, 15.00,  "Entertainment", "2026-05-10", "Streaming subscription"),
        (user_id, 80.00,  "Shopping",      "2026-05-12", "New shoes"),
        (user_id, 9.99,   "Other",         "2026-05-14", "Miscellaneous"),
        (user_id, 22.00,  "Food",          "2026-05-17", "Dinner out"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()
