import os
import sqlite3
import subprocess
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "shop.db"

app = Flask(__name__)
app.config["FLAG"] = "FLAG-ssti-jinja-renders-your-input"

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))


def page(title, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - UsaHack</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 820px; margin: 0 auto; padding: 1rem; background: #f6f7fb; }}
  nav a {{ margin-right: .8rem; }}
  input {{ padding: .4rem; margin: .2rem 0; border: 1px solid #ccc; border-radius: 4px; }}
  button {{ padding: .4rem .8rem; cursor: pointer; }}
  .err {{ color: #b00; }}
  .card {{ background: #fff; border: 1px solid #ddd; padding: .8rem; border-radius: 8px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; }}
  th, td {{ border: 1px solid #ddd; padding: .4rem; text-align: left; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ background: #fff; border: 1px solid #ddd; padding: .5rem; margin: .3rem 0; border-radius: 6px; }}
</style>
</head>
<body>
<nav>
  <a href="/">Home</a>
  <a href="/products">Products</a>
  <a href="/search">Search</a>
  <a href="/comments">Comments</a>
  <a href="/login">Login</a>
  <a href="/files?name=about.txt">Files</a>
  <a href="/server">Server</a>
  <a href="/ssti">Greeting</a>
  <a href="/settings">Settings</a>
  <a href="/score">Score</a>
  <a href="/admin">Admin</a>
</nav>
{body}
</body>
</html>"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def seed():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT,
            secret TEXT
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT,
            body TEXT
        );
        CREATE TABLE IF NOT EXISTS flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            claimed INTEGER DEFAULT 0
        );
        """
    )
    if conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 0:
        conn.executemany(
            "INSERT INTO users (username, password, email, secret) VALUES (?, ?, ?, ?)",
            [
                ("alice", "password123", "alice@shop.test", "FLAG-alice-writes-passwords-on-sticky-notes"),
                ("bob", "correcthorse", "bob@shop.test", "FLAG-bob-reuses-passwords-everywhere"),
                ("dave", "letmein", "dave@shop.test", "FLAG-no-rate-limiting-means-i-get-bruted"),
                ("admin", "admin123", "admin@shop.test", "FLAG-admin-thinks-default-creds-are-fine"),
            ],
        )
    if conn.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"] == 0:
        conn.execute("INSERT INTO products (name, price) VALUES ('USB cable', 12.99)")
        conn.execute("INSERT INTO products (name, price) VALUES ('Laptop', 899.00)")
        conn.execute("INSERT INTO products (name, price) VALUES ('Wireless mouse', 24.50)")
    if conn.execute("SELECT COUNT(*) AS n FROM flags").fetchone()["n"] == 0:
        conn.executemany(
            "INSERT INTO flags (name, claimed) VALUES (?, 0)",
            [
                ("SQLi: search returns every product",),
                ("Login bypass (SQLi on auth)",),
                ("IDOR: read someone else's profile",),
                ("Stored XSS in comments",),
                ("Client-side price manipulation",),
                ("Path traversal out of docs",),
                ("Forged admin cookie",),
                ("Command injection on /server",),
                ("SSTI on /ssti",),
                ("Brute-force dave's password",),
                ("CSRF: change admin's email",),
            ],
        )
    conn.commit()
    conn.close()


seed()


@app.route("/")
def home():
    body = """
    <h2>Welcome to UsaHack</h2>
    <p>This is a deliberately vulnerable web app built to practice the OWASP Top 10.
    Nothing here is real: no payments, no accounts, no tracking.</p>
    <h3>Your missions</h3>
    <ol>
      <li>Steal every user's <code>secret</code> (the FLAG-... values).</li>
      <li>Log in as someone without knowing their password.</li>
      <li>Read a file outside the <code>docs</code> folder.</li>
      <li>Buy the laptop for $0.01.</li>
      <li>Make the comments page run <code>alert(1)</code>.</li>
      <li>Get into the admin panel without being admin.</li>
      <li>Run <code>whoami</code> on the server via the ping tool.</li>
      <li>Make the greeting page render <code>7*7</code> as <code>49</code>.</li>
      <li>Brute-force dave's password (nothing locks you out).</li>
      <li>Change admin's email without logging in as admin.</li>
    </ol>
    <p>Track your progress on the <a href="/score">Score</a> page.
    Answers and the secure fixes are in <code>solutions.md</code>.</p>
    """
    return page("Home", body)


@app.route("/search")
def search():
    q = request.args.get("q", "")
    conn = get_db()
    rows = conn.execute(f"SELECT * FROM products WHERE name LIKE '%{q}%'").fetchall()
    conn.close()
    items = "".join(
        f"<li>{row['name']} - ${row['price']:.2f}</li>" for row in rows
    ) or "<li>No products found.</li>"
    body = f"""
    <h2>Search</h2>
    <form method="get" action="/search">
      <input type="text" name="q" placeholder="Search products" value="{q}">
      <button type="submit">Search</button>
    </form>
    <ul>{items}</ul>
    """
    return page("Search", body)


@app.route("/products")
def products():
    conn = get_db()
    rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    cards = "".join(
        f"""
        <div class="card">
          <h3>{row['name']}</h3>
          <p>Price: ${row['price']:.2f}</p>
          <form method="post" action="/checkout">
            <input type="hidden" name="item" value="{row['name']}">
            <input type="hidden" name="price" value="{row['price']}">
            <button type="submit">Buy now</button>
          </form>
        </div>
        """
        for row in rows
    )
    return page("Products", f"<h2>Products</h2><div class='grid'>{cards}</div>")


@app.route("/checkout", methods=["POST"])
def checkout():
    item = request.form.get("item", "Mystery item")
    price = request.form.get("price", "0")
    try:
        price = float(price)
    except ValueError:
        price = 0.0
    body = f"""
    <h2>Order placed!</h2>
    <p>You bought: {item}</p>
    <p>Total charged: ${price:.2f}</p>
    """
    return page("Checkout", body)


@app.route("/comments")
def comments():
    conn = get_db()
    rows = conn.execute("SELECT * FROM comments").fetchall()
    conn.close()
    items = "".join(
        f"<li><strong>{row['author']}:</strong> {row['body']}</li>" for row in rows
    ) or "<li>No comments yet.</li>"
    body = f"""
    <h2>Comments</h2>
    <ul>{items}</ul>
    <form method="post" action="/comment">
      <input type="text" name="author" placeholder="Your name">
      <input type="text" name="body" placeholder="Say something">
      <button type="submit">Post</button>
    </form>
    """
    return page("Comments", body)


@app.route("/comment", methods=["POST"])
def comment():
    author = request.form.get("author", "anonymous")
    body = request.form.get("body", "")
    conn = get_db()
    conn.execute(f"INSERT INTO comments (author, body) VALUES ('{author}', '{body}')")
    conn.commit()
    conn.close()
    return redirect(url_for("comments"))


@app.route("/profile")
def profile():
    user_id = request.args.get("id", "1")
    conn = get_db()
    row = conn.execute(f"SELECT * FROM users WHERE id = {user_id}").fetchone()
    conn.close()
    if row is None:
        return page("Profile", "<p>User not found.</p>"), 404
    body = f"""
    <h2>Profile</h2>
    <p><strong>Name:</strong> {row['username']}</p>
    <p><strong>Email:</strong> {row['email']}</p>
    """
    return page("Profile", body)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = get_db()
        row = conn.execute(
            f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        ).fetchone()
        conn.close()
        if row:
            resp = redirect(url_for("profile", id=row["id"]))
            resp.set_cookie("user", row["username"])
            return resp
        error = "<p class='err'>Invalid credentials.</p>"
    body = f"""
    <h2>Login</h2>
    {error}
    <form method="post" action="/login">
      <input type="text" name="username" placeholder="Username">
      <input type="password" name="password" placeholder="Password">
      <button type="submit">Log in</button>
    </form>
    """
    return page("Login", body)


@app.route("/files")
def files():
    name = request.args.get("name", "about.txt")
    target = BASE_DIR / "docs" / name
    try:
        content = target.read_text()
    except Exception:
        content = "File not found or unreadable."
    return page("Files", f"<h2>{name}</h2><pre>{content}</pre>")


@app.route("/admin")
def admin():
    user = request.cookies.get("user")
    if user != "admin":
        return page("Admin", "<p>Access denied - this area is for admins only.</p>"), 403
    conn = get_db()
    rows = conn.execute("SELECT id, username, email, secret FROM users").fetchall()
    conn.close()
    rows_html = "".join(
        f"<tr><td>{row['id']}</td><td>{row['username']}</td><td>{row['email']}</td><td>{row['secret']}</td></tr>"
        for row in rows
    )
    return page(
        "Admin",
        f"<h2>Admin panel</h2><table><tr><th>ID</th><th>Username</th><th>Email</th><th>Secret</th></tr>{rows_html}</table>",
    )


@app.route("/server", methods=["GET", "POST"])
def server():
    output = ""
    if request.method == "POST":
        host = request.form.get("host", "")
        try:
            result = subprocess.run(
                f"ping -c 1 {host}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = result.stdout + result.stderr
        except Exception as exc:
            output = str(exc)
    body = f"""
    <h2>Server status</h2>
    <p>Check if a host is up from the server's point of view.</p>
    <form method="post" action="/server">
      <input type="text" name="host" placeholder="8.8.8.8">
      <button type="submit">Ping</button>
    </form>
    <pre>{output}</pre>
    """
    return page("Server", body)


@app.route("/ssti", methods=["GET", "POST"])
def ssti():
    rendered = ""
    if request.method == "POST":
        name = request.form.get("name", "")
        rendered = render_template_string(f"Hello {name}!")
    body = f"""
    <h2>Greeting</h2>
    <form method="post" action="/ssti">
      <input type="text" name="name" placeholder="Your name">
      <button type="submit">Greet</button>
    </form>
    <p>{rendered}</p>
    """
    return page("SSTI", body)


@app.route("/settings", methods=["GET", "POST"])
def settings():
    user = request.cookies.get("user")
    if not user:
        return page("Settings", "<p>Log in first (try <a href='/login'>/login</a>).</p>"), 401
    conn = get_db()
    flag = ""
    if request.method == "POST" or request.args.get("email"):
        email = request.form.get("email") or request.args.get("email", "")
        conn.execute(f"UPDATE users SET email = '{email}' WHERE username = '{user}'")
        conn.commit()
    row = conn.execute("SELECT email FROM users WHERE username = ?", (user,)).fetchone()
    conn.close()
    if user == "admin" and row["email"] == "hacked@usahack.test":
        flag = "<p class='err'>FLAG-csrf-you-changed-admins-email</p>"
    body = f"""
    <h2>Account settings</h2>
    <p>Signed in as <strong>{user}</strong> - current email: {row['email']}</p>
    <form method="post" action="/settings">
      <input type="text" name="email" value="{row['email']}">
      <button type="submit">Update email</button>
    </form>
    <p>Note: this update has no CSRF token. Anyone who can make your browser send it can change your email.</p>
    {flag}
    """
    return page("Settings", body)


@app.route("/score", methods=["GET", "POST"])
def score():
    conn = get_db()
    if request.method == "POST":
        fid = request.form.get("flag_id", type=int)
        if fid is not None:
            conn.execute("UPDATE flags SET claimed = 1 - claimed WHERE id = ?", (fid,))
            conn.commit()
    rows = conn.execute("SELECT * FROM flags").fetchall()
    conn.close()
    claimed = sum(1 for r in rows if r["claimed"])
    items = "".join(
        f"""
        <li>{r['name']}
          <form method="post" action="/score">
            <input type="hidden" name="flag_id" value="{r['id']}">
            <button type="submit">{'Unmark' if r['claimed'] else 'Mark found'}</button>
          </form>
        </li>
        """
        for r in rows
    )
    body = f"""
    <h2>Your score</h2>
    <p>{claimed} / {len(rows)} flags</p>
    <ul>{items}</ul>
    """
    return page("Score", body)


if __name__ == "__main__":
    if HOST != "127.0.0.1":
        print("WARNING: you are exposing an intentionally vulnerable app to the network!")
        print("Do NOT run this against anything you do not own.")
    app.run(host=HOST, port=PORT, debug=False)
