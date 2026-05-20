import sqlite3

from flask import Flask, render_template, request, session, redirect, url_for, abort
from werkzeug.security import check_password_hash

from database.db import get_db, init_db, seed_db, create_user, get_user_by_email

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-prod"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name:
            return render_template("register.html", error="Full name is required.")
        if not email or "@" not in email:
            return render_template("register.html", error="A valid email address is required.")
        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters.")

        try:
            user = create_user(name, email, password)
        except sqlite3.IntegrityError:
            return render_template("register.html", error="An account with that email already exists.")

        session["user_id"]   = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("landing"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("login.html", error="Email and password are required.")

        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.")

        session["user_id"]   = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("profile"))

    return render_template("login.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name":         "Demo User",
        "email":        "demo@spendly.com",
        "member_since": "May 2026",
    }

    stats = {
        "total_spent":       "$334.49",
        "transaction_count": 8,
        "top_category":      "Bills",
    }

    transactions = [
        {"date": "May 17, 2026", "description": "Dinner out",             "category": "Food",          "amount": "$22.00"},
        {"date": "May 14, 2026", "description": "Miscellaneous",          "category": "Other",         "amount": "$9.99"},
        {"date": "May 12, 2026", "description": "New shoes",              "category": "Shopping",      "amount": "$80.00"},
        {"date": "May 10, 2026", "description": "Streaming subscription", "category": "Entertainment", "amount": "$15.00"},
        {"date": "May 08, 2026", "description": "Pharmacy",               "category": "Health",        "amount": "$30.00"},
        {"date": "May 05, 2026", "description": "Electricity bill",       "category": "Bills",         "amount": "$120.00"},
        {"date": "May 03, 2026", "description": "Monthly bus pass",       "category": "Transport",     "amount": "$45.00"},
        {"date": "May 01, 2026", "description": "Lunch",                  "category": "Food",          "amount": "$12.50"},
    ]

    categories = [
        {"name": "Bills",         "amount": "$120.00", "percent": 36},
        {"name": "Shopping",      "amount": "$80.00",  "percent": 24},
        {"name": "Transport",     "amount": "$45.00",  "percent": 13},
        {"name": "Food",          "amount": "$34.50",  "percent": 10},
        {"name": "Health",        "amount": "$30.00",  "percent": 9},
        {"name": "Entertainment", "amount": "$15.00",  "percent": 4},
        {"name": "Other",         "amount": "$9.99",   "percent": 3},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
