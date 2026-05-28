import sqlite3

from flask import Flask, render_template, request, session, redirect, url_for, abort
from werkzeug.security import check_password_hash

from database.db import (
    get_db, init_db, seed_db, create_user, get_user_by_email,
    get_user_by_id, create_expense, get_expense_stats, get_expenses_by_user,
    get_category_breakdown, get_monthly_spend,
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

    start_date = None
    end_date   = None
    try:
        s = request.args.get("start_date", "").strip()
        e = request.args.get("end_date", "").strip()
        if s and e:
            datetime.strptime(s, "%Y-%m-%d")
            datetime.strptime(e, "%Y-%m-%d")
            start_date = s
            end_date   = e
    except ValueError:
        pass

    stats        = get_expense_stats(session["user_id"], start_date, end_date)
    transactions = get_expenses_by_user(session["user_id"], start_date, end_date)
    categories   = get_category_breakdown(session["user_id"], start_date, end_date)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        start_date=start_date,
        end_date=end_date,
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    from datetime import datetime
    user_id = session["user_id"]

    stats = get_expense_stats(user_id)
    categories = get_category_breakdown(user_id)
    transactions = get_expenses_by_user(user_id)[:5]

    monthly_raw = get_monthly_spend(user_id)
    monthly_labels = [datetime.strptime(m["month"], "%Y-%m").strftime("%b '%y") for m in monthly_raw]
    monthly_data = [m["total"] for m in monthly_raw]
    avg_monthly = round(sum(monthly_data) / len(monthly_data), 2) if monthly_data else 0

    return render_template(
        "analytics.html",
        stats=stats,
        categories=categories,
        transactions=transactions,
        monthly_labels=monthly_labels,
        monthly_data=monthly_data,
        avg_monthly=f"${avg_monthly:.2f}",
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":
        from datetime import datetime as dt
        amount_str  = request.form.get("amount", "").strip()
        category    = request.form.get("category", "").strip()
        date_str    = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            return render_template("add_expense.html", error="Amount must be a positive number.")

        if not category:
            return render_template("add_expense.html", error="Category is required.")

        try:
            dt.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return render_template("add_expense.html", error="Date must be a valid date.")

        create_expense(session["user_id"], amount, category, date_str, description or None)
        return redirect(url_for("profile"))

    return render_template("add_expense.html")


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
