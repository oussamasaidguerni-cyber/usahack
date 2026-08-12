# UsaHack - a deliberately vulnerable web app to learn the OWASP Top 10

A small, intentionally insecure Flask app for practicing web exploitation and
secure-coding fixes. You attack it, you fix it, and you learn both sides of the fence.

## Is it safe?

- **Runs only on your own laptop.** By default it binds to `127.0.0.1`, so nothing
  on your network or the internet can reach it. It talks only to itself.
- **It never touches anything outside this folder.** The "secret" files, the
  database, the "admin" panel - all of it is fake, inside `usahack/`.
- **Two rules to stay safe:**
  1. Do NOT expose it to your network/internet on a machine you care about.
  2. Only interact with it through your browser. Never point its tricks at sites
     or systems you don't own.

If you ever want to run it publicly for others to practice, host it in the cloud
(Oracle Cloud free tier, Render, Railway, a cheap VPS) - never on your main machine.

## What's broken (on purpose)

| Page | Vulnerability | OWASP mapping |
|------|---------------|---------------|
| `/search` | SQL injection + reflected XSS | A03 / A03 |
| `/login` | SQL injection + plaintext passwords + no rate limiting (brute-forceable) | A07 / A02 |
| `/profile?id=N` | IDOR (insecure object reference) | A01 |
| `/comments` | Stored XSS (second-order SQLi too) | A03 |
| `/checkout` | Client-side price manipulation | A04 |
| `/files?name=` | Path traversal | A01 |
| `/admin` | Forgeable auth cookie (broken access control) | A01 |
| `/server` | Command injection | A03 |
| `/ssti` | Server-side template injection (Jinja) | A03 |
| `/settings` | CSRF (state-changing GET, no token) | A01 |
| `/score` | Track your found flags (11 total) | - |

Full walkthrough and fixes: [solutions.md](solutions.md)

## Run it (easy mode, Linux/macOS)

In a terminal inside this folder, run:

```
./run.sh
```

That's it. It sets up the environment for you, starts the server, and **auto-restarts
it if it ever crashes**. Open `http://127.0.0.1:5000`. Stop it with `Ctrl+C`.

Want it to keep running even after you close the terminal/VS Code?

```
./run.sh bg      # start in background (survives closing the terminal)
./run.sh stop    # stop the background server
```

Logs go to `server.log`.

## Run it (VS Code / Windows)

1. Open this folder in VS Code.
2. Open a terminal (`` Ctrl+` ``) and create a virtual environment:
   ```
   python3 -m venv venv
   ```
3. Activate it:
   - Linux/macOS: `source venv/bin/activate`
   - Windows: `venv\Scripts\activate`
4. Install the single dependency:
   ```
   pip install -r requirements.txt
   ```
5. Run it:
   ```
   python app.py
   ```
6. Open `http://127.0.0.1:5000` in your browser.

VS Code tip: after step 3, set the interpreter (`Ctrl+Shift+P` -> "Python: Select
Interpreter" -> `./venv/bin/python`) so the debugger works too. You can then press
`F5` to run with breakpoints - handy for tracing how each exploit works.

## The challenges

1. Steal every user's `secret` (the `FLAG-...` values).
2. Log in as someone without knowing their password.
3. Read a file outside the `docs` folder.
4. Buy the laptop for $0.01.
5. Make the comments page run `alert(1)`.
6. Get into the admin panel without being admin.
7. Run `whoami` on the server via the ping tool.
8. Make the greeting page render `7*7` as `49`.
9. Brute-force dave's password (nothing locks you out).
10. Change admin's email without logging in as admin.

Track what you've found on the `/score` page (11 flags total).

Start with the Search page. It's the friendliest.

## Stack

- Python 3 + Flask (only dependency)
- SQLite (built into Python - no database server needed)
- Runs fine on low-end hardware

## Disclaimer

This project is for authorized education only. Exploiting systems you do not own
is illegal in most jurisdictions. Use this to learn so you can build and defend
better - not to attack.
