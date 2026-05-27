import sqlite3

from flask import Flask, render_template, request, session, redirect, url_for, abort
from werkzeug.security import check_password_hash

from database.db import (
    get_db, init_db, seed_db, create_user, get_user_by_email,
    get_user_by_id, get_expense_stats, get_expenses_by_user, get_category_breakdown,
)

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

    from datetime import datetime
    db_user = get_user_by_id(session["user_id"])
    if db_user is None:
        abort(404)
    member_since = datetime.fromisoformat(db_user["created_at"]).strftime("%b %Y")
    user = {
        "name":         db_user["name"],
        "email":        db_user["email"],
        "member_since": member_since,
    }
    stats = get_expense_stats(session["user_id"])

    transactions = get_expenses_by_user(session["user_id"])

    categories = get_category_breakdown(session["user_id"])

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
