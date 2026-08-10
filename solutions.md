# Solutions - UsaHack

Each bug below shows: the exploit, why it works, and the fix. Try to solve each
challenge yourself before reading the answer.

---

## 1. SQL injection on `/search`

Try:
```
/search?q=' OR 1=1 --
```
This returns **every** product, because the query becomes:

```sql
SELECT * FROM products WHERE name LIKE '%' OR 1=1 --%'
```

The `--` comments out the rest of the line, and `OR 1=1` is always true.

**Why:** user input is concatenated straight into the SQL string (in `app.py`,
`search()`).

**Fix (parameterized queries - NEVER build SQL with user input):**

```python
rows = conn.execute(
    "SELECT * FROM products WHERE name LIKE ?",
    (f"%{q}%",),
).fetchall()
```

---

## 2. SQL injection on `/login` (mission: log in without a password)

In the username field, enter:

```
admin' OR '1'='1
```

with anything in the password field. The query becomes:

```sql
SELECT * FROM users WHERE username = 'admin' OR '1'='1' AND password = '...'
```

`'1'='1'` short-circuits to true, so the query returns admin's row.

**Why:** raw string concatenation again - plus passwords are stored in plaintext.
Take a peek at the database:

```
sqlite3 shop.db
SELECT * FROM users;
```

**Fix:** parameterized query + store password hashes only (never the plaintext):

```python
from werkzeug.security import check_password_hash
row = conn.execute(
    "SELECT * FROM users WHERE username = ?", (username,)
).fetchone()
if row and check_password_hash(row["password_hash"], password):
    ...
```

---

## 3. IDOR on `/profile` (mission: steal everyone's secret... well, one step at a time)

Visit:
```
/profile?id=2
/profile?id=3
```
There's no login check at all - you can view any user by guessing their id. This is
an Insecure Direct Object Reference (IDOR).

**Why:** the route trusts the `id` parameter and never verifies the requester.

**Fix:** only ever show the profile of the currently authenticated user; never
accept an arbitrary id from the client:

```python
user_id = get_current_logged_in_user_id()
row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
```

---

## 4. Stored XSS on `/comments` (mission: make it run `alert(1)`)

Post a comment with the body:

```html
<script>alert('pwned')</script>
```

It's stored in the DB and rendered back unescaped on `/comments`, so the script
runs in **every visitor's browser**. This is stored (persistent) XSS - the most
dangerous kind, because the payload lives on the server.

**Why:** comment text is written into the HTML without escaping.

**Fix:** never insert raw user data into HTML. Let the template engine escape it:

```html
<li><strong>{{ comment.author }}</strong>: {{ comment.body }}</li>
```

(Jinja auto-escapes `{{ ... }}` by default. The app deliberately bypasses it.)

---

## 5. Client-side price manipulation (mission: laptop for $0.01)

Open your browser's dev tools (F12), go to the Products page, and edit the hidden
form field before clicking "Buy now":

```html
<input type="hidden" name="price" value="0.01">
```

The total charged shows $0.01.

**Why:** the price is sent by the **client** and the server trusts it. A client can
always send whatever it wants - hidden fields and disabled buttons stop nobody.

**Fix:** compute the price server-side from the product id:

```python
row = conn.execute("SELECT price FROM products WHERE id = ?", (product_id,)).fetchone()
total = row["price"]
```

---

## 6. Path traversal on `/files`

Try:
```
/files?name=../../usahack/app.py
```
You can read the application source. On a normal server you would point higher,
e.g. `../../../../etc/passwd`. The server joins your filename onto the `docs`
folder and reads whatever results.

**Why:** user-controlled filename with no validation.

**Fix:** resolve the path and verify it stays inside `docs`:

```python
from pathlib import Path
docs_dir = Path(__file__).resolve().parent / "docs"
target = (docs_dir / name).resolve()
if not target.is_relative_to(docs_dir):
    abort(403)
```

---

## 7. Forgeable admin cookie (mission: get into the admin panel)

Log in as anyone (e.g. `alice` / `password123`), open dev tools (F12) -> Application
-> Cookies, and change the `user` cookie to `admin`. Refresh `/admin` - welcome to
the panel, where all the flags are.

**Why:** the app decides "you're an admin" by trusting a client-set cookie that
isn't signed or verified server-side.

**Fix:** use a server-side session signed with a real secret. In Flask:

```python
from flask import session
app.secret_key = os.environ["SECRET_KEY"]  # long random value, kept secret
session["role"] = "admin"                  # set on the server at login
```

---

## Summary of the fixes

1. Use parameterized SQL queries (`?` placeholders) - everywhere.
2. Hash passwords (`werkzeug.security`), never store plaintext.
3. Don't trust client input - validate ids, prices, and filenames server-side.
4. Escape output in templates (use `{{ }}`, never `|safe` on user data).
5. Use server-side signed sessions for auth, not forgeable cookies.
6. Enforce access control on every protected route, not just the button.

These are the same bugs behind most real-world breaches. Fixing all of them in this
tiny app is a complete OWASP Top 10 crash course.
