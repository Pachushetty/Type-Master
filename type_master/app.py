from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import random
import sqlite3
import io
import csv
import webbrowser
from threading import Timer
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "development-secret-key")
DB = "typing_master.db"

PASSAGES = {
    "Easy": [
        "the quick brown fox jumps over the lazy dog",
        "practice makes perfect when you work hard",
        "the sun rises in the east every day",
        "reading books helps you learn new things",
        "life is short so enjoy every moment"
    ],
    "Medium": [
        "python is a great programming language used by millions of developers",
        "technology makes our life easier and more comfortable every single day",
        "a journey of a thousand miles begins with a single small step forward",
        "learning to type fast is a very useful skill in the modern digital world",
        "every expert was once a beginner who never gave up on their goals"
    ],
    "Hard": [
        "success is not final failure is not fatal it is the courage to continue",
        "the more that you read the more things you will know and understand",
        "hard work and dedication will always lead you to success in life",
        "the best way to predict your future is to create it yourself today",
        "consistent practice improves speed accuracy confidence and concentration"
    ],
    "Expert": [
        "Debugging, testing, and documenting code are essential skills for professional developers.",
        "In 2026, modern applications combine security, performance, accessibility, and thoughtful design.",
        "A focused learner can transform mistakes into useful feedback and steadily improve over time.",
        "Fast typing is valuable, but accuracy, punctuation, consistency, and clear communication matter too.",
        "Python, JavaScript, databases, APIs, Git, and cloud platforms form a powerful modern development toolkit."
    ]
}

CHALLENGES = ["Normal Test", "Accuracy Challenge", "Speed Challenge"]


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT NOT NULL,
        wpm INTEGER NOT NULL,
        raw_wpm INTEGER NOT NULL,
        accuracy INTEGER NOT NULL,
        errors INTEGER NOT NULL,
        correct_chars INTEGER NOT NULL,
        total_chars INTEGER NOT NULL,
        duration INTEGER NOT NULL,
        time_limit INTEGER NOT NULL,
        difficulty TEXT NOT NULL,
        challenge TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("index.html", username=session.get("username"))


@app.route("/get_passage")
def get_passage():
    difficulty = request.args.get("difficulty", "Medium")
    if difficulty not in PASSAGES:
        difficulty = "Medium"
    return jsonify({"passage": random.choice(PASSAGES[difficulty]), "difficulty": difficulty})


@app.post("/api/register")
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if len(username) < 3 or len(password) < 4:
        return jsonify({"ok": False, "message": "Username must be 3+ characters and password 4+ characters."}), 400
    conn = db()
    try:
        cur = conn.execute("INSERT INTO users(username,password,created_at) VALUES(?,?,?)",
                           (username, generate_password_hash(password), datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        session["user_id"] = cur.lastrowid
        session["username"] = username
        return jsonify({"ok": True, "username": username})
    except sqlite3.IntegrityError:
        return jsonify({"ok": False, "message": "Username already exists."}), 409
    finally:
        conn.close()


@app.post("/api/login")
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"ok": False, "message": "Invalid username or password."}), 401
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return jsonify({"ok": True, "username": user["username"]})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/me")
def me():
    if not session.get("user_id"):
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "username": session["username"]})


@app.post("/api/results")
def save_result():
    data = request.get_json() or {}
    required = ["wpm", "raw_wpm", "accuracy", "errors", "correct_chars", "total_chars", "duration", "time_limit", "difficulty", "challenge"]
    if any(k not in data for k in required):
        return jsonify({"ok": False, "message": "Incomplete result."}), 400
    username = session.get("username", "Guest")
    user_id = session.get("user_id")
    conn = db()
    conn.execute("""INSERT INTO results
        (user_id,username,wpm,raw_wpm,accuracy,errors,correct_chars,total_chars,duration,time_limit,difficulty,challenge,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (user_id, username, int(data["wpm"]), int(data["raw_wpm"]), int(data["accuracy"]), int(data["errors"]),
         int(data["correct_chars"]), int(data["total_chars"]), int(data["duration"]), int(data["time_limit"]),
         data["difficulty"], data["challenge"], datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.get("/api/dashboard")
def dashboard():
    # Dashboard is private: only the currently logged-in user's data is returned.
    if not session.get("user_id"):
        return jsonify({"ok": False, "message": "Login required to access your dashboard."}), 401

    user_id = session["user_id"]
    username = session["username"]
    conn = db()
    rows = conn.execute(
        "SELECT * FROM results WHERE user_id=? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()

    results = [dict(r) for r in rows]
    best = max(results, key=lambda x: x["wpm"], default=None)
    avg_wpm = round(sum(r["wpm"] for r in results) / len(results)) if results else 0
    avg_acc = round(sum(r["accuracy"] for r in results) / len(results)) if results else 0
    streak = calculate_streak(results)

    return jsonify({
        "ok": True,
        "username": username,
        "best": best,
        "avg_wpm": avg_wpm,
        "avg_accuracy": avg_acc,
        "tests": len(results),
        "streak": streak,
        "history": results[:20]
    })


@app.get("/api/leaderboard")
def leaderboard():
    # Public leaderboard contains only registered users, never Guest/private history.
    conn = db()
    rows = conn.execute("""
        SELECT r.* FROM results r
        INNER JOIN users u ON u.id = r.user_id
        WHERE r.user_id IS NOT NULL
        ORDER BY r.wpm DESC, r.accuracy DESC, r.id ASC
        LIMIT 10
    """).fetchall()
    conn.close()
    return jsonify({"leaderboard": [dict(r) for r in rows]})

def calculate_streak(results):
    dates = {r["created_at"][:10] for r in results}
    if not dates:
        return 0
    today = date.today()
    if today.isoformat() not in dates and (today - timedelta(days=1)).isoformat() not in dates:
        return 0
    current = today if today.isoformat() in dates else today - timedelta(days=1)
    streak = 0
    while current.isoformat() in dates:
        streak += 1
        current -= timedelta(days=1)
    return streak


@app.get("/export")
def export_results():
    if not session.get("user_id"):
        return jsonify({"ok": False, "message": "Login required to export your results."}), 401
    username = session["username"]
    user_id = session["user_id"]
    conn = db()
    if user_id:
        rows = conn.execute("SELECT * FROM results WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM results WHERE username='Guest' ORDER BY id DESC").fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "WPM", "Raw WPM", "Accuracy", "Errors", "Correct Characters", "Total Characters", "Duration", "Time Limit", "Difficulty", "Challenge"])
    for r in rows:
        writer.writerow([r["created_at"], r["wpm"], r["raw_wpm"], r["accuracy"], r["errors"], r["correct_chars"], r["total_chars"], r["duration"], r["time_limit"], r["difficulty"], r["challenge"]])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True,
                     download_name=f"type-master-{username}.csv")


init_db()

if __name__ == "__main__":
    Timer(1.5, lambda: webbrowser.open_new("http://127.0.0.1:5000/")).start()
    app.run(debug=True, use_reloader=False)
