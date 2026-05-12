"""
SkyYield Info Server
Deploy to Railway → get a permanent URL forever.
Edit your script info from any browser at /admin (password protected).
"""

from flask import Flask, jsonify, request, render_template_string, redirect, session
import json, os, datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "changeme-set-in-railway-env")

# Password to access /admin — set in Railway environment variables
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "skyyield123")

# ─────────────────────────────────────────────────────────────
# Persistent data  (stored in a JSON file so it survives restarts)
# ─────────────────────────────────────────────────────────────
DATA_FILE = "info.json"

DEFAULT_DATA = {
    "title":        "Sky Yield",
    "version":      "2.0.0",
    "author":       "YourName",
    "description":  "Radar, tracking & zoom tool.\nMacOS-style UI.",
    "discord":      "discord.gg/yourlink",
    "credits":      "Made by YourName",
    "status":       "✅ Online",
    "last_updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    "changelog": [
        "v2.0.0 — Full macOS UI rewrite",
        "v1.5.0 — Added zoom bar",
        "v1.0.0 — Initial release",
    ],
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return DEFAULT_DATA.copy()

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

# ─────────────────────────────────────────────────────────────
# Public API  (called by Roblox)
# ─────────────────────────────────────────────────────────────
@app.route("/info")
def get_info():
    return jsonify(load_data())

@app.route("/ping")
def ping():
    return jsonify({"ok": True})

# ─────────────────────────────────────────────────────────────
# Admin panel  (your browser)
# ─────────────────────────────────────────────────────────────
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SkyYield Admin</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', Helvetica, sans-serif;
    background: #1c1c1e; color: #f5f5f7; min-height: 100vh;
  }
  .topbar {
    background: #2c2c2e; padding: 0 24px; height: 52px;
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 1px solid #3a3a3c;
  }
  .topbar-title { font-size: 15px; font-weight: 700; color: #fff; }
  .topbar-sub   { font-size: 11px; color: #636366; margin-left: 10px; }
  .dot { display:inline-block; width:8px; height:8px; border-radius:50%;
         background:#30d158; margin-right:6px; }
  .container { max-width: 640px; margin: 32px auto; padding: 0 16px 60px; }
  .section { margin-bottom: 28px; }
  .section-title {
    font-size: 10px; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: #636366;
    border-bottom: 1px solid #3a3a3c;
    padding-bottom: 8px; margin-bottom: 14px;
  }
  label { display:block; font-size:12px; color:#98989a; margin-bottom:5px; margin-top:12px; }
  input[type=text], input[type=password], textarea {
    width: 100%; background: #2c2c2e; border: 1px solid #3a3a3c;
    border-radius: 8px; color: #f5f5f7; padding: 10px 12px;
    font-size: 13px; font-family: inherit; outline: none;
    transition: border-color .15s;
  }
  input:focus, textarea:focus { border-color: #0a84ff; }
  textarea { resize: vertical; line-height: 1.5; }
  .btn {
    display: inline-block; background: #0a84ff; color: #fff;
    border: none; border-radius: 8px; padding: 11px 24px;
    font-size: 14px; font-weight: 600; cursor: pointer;
    font-family: inherit; margin-top: 20px;
    transition: background .15s;
  }
  .btn:hover { background: #0066cc; }
  .btn-danger { background: #ff453a; }
  .btn-danger:hover { background: #cc2a1f; }
  .flash {
    background: #1a3a1a; border: 1px solid #30d158;
    color: #30d158; border-radius: 8px; padding: 10px 14px;
    font-size: 13px; margin-bottom: 20px;
  }
  .flash.error { background:#3a1a1a; border-color:#ff453a; color:#ff453a; }
  .login-wrap {
    max-width: 360px; margin: 80px auto; background: #2c2c2e;
    border-radius: 14px; padding: 32px; border: 1px solid #3a3a3c;
  }
  .login-title { font-size:20px; font-weight:700; margin-bottom:24px; }
  .url-badge {
    background: #2c2c2e; border: 1px solid #3a3a3c; border-radius: 8px;
    padding: 10px 14px; font-size: 12px; color: #636366; word-break:break-all;
    margin-bottom: 20px;
  }
  .url-badge span { color: #0a84ff; }
</style>
</head>
<body>

{% if not logged_in %}
<div class="login-wrap">
  <div class="login-title">SkyYield Admin</div>
  {% if error %}<div class="flash error">{{ error }}</div>{% endif %}
  <form method="POST" action="/admin/login">
    <label>Password</label>
    <input type="password" name="password" autofocus placeholder="Enter admin password">
    <button class="btn" style="width:100%;margin-top:16px">Sign In</button>
  </form>
</div>

{% else %}
<div class="topbar">
  <div>
    <span class="topbar-title">SkyYield Admin</span>
    <span class="topbar-sub">Info Panel Editor</span>
  </div>
  <div style="display:flex;align-items:center;gap:16px">
    <span style="font-size:12px;color:#636366"><span class="dot"></span>Server online</span>
    <a href="/admin/logout" style="font-size:12px;color:#ff453a;text-decoration:none">Sign out</a>
  </div>
</div>

<div class="container">
  <div class="url-badge">
    Roblox URL → <span>{{ request.host_url }}info</span>
  </div>

  {% if saved %}<div class="flash">✓ Saved & published successfully</div>{% endif %}

  <form method="POST" action="/admin/save">
    <div class="section">
      <div class="section-title">Basic Info</div>
      <label>Title</label>
      <input type="text" name="title" value="{{ d.title }}">
      <label>Version</label>
      <input type="text" name="version" value="{{ d.version }}">
      <label>Author</label>
      <input type="text" name="author" value="{{ d.author }}">
      <label>Status</label>
      <input type="text" name="status" value="{{ d.status }}">
    </div>

    <div class="section">
      <div class="section-title">Details</div>
      <label>Description</label>
      <textarea name="description" rows="4">{{ d.description }}</textarea>
      <label>Discord</label>
      <input type="text" name="discord" value="{{ d.discord }}">
      <label>Credits</label>
      <input type="text" name="credits" value="{{ d.credits }}">
    </div>

    <div class="section">
      <div class="section-title">Changelog  <span style="font-weight:400;text-transform:none;letter-spacing:0">(one entry per line)</span></div>
      <textarea name="changelog" rows="7">{{ d.changelog | join('\\n') }}</textarea>
    </div>

    <button class="btn" type="submit">Save & Publish</button>
  </form>
</div>
{% endif %}

</body>
</html>
"""

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return render_template_string(ADMIN_HTML, logged_in=False, error=None)
    return render_template_string(ADMIN_HTML,
        logged_in=True, d=load_data(), saved=request.args.get("saved"), request=request)

@app.route("/admin/login", methods=["POST"])
def admin_login():
    if request.form.get("password") == ADMIN_PASSWORD:
        session["admin"] = True
        return redirect("/admin")
    return render_template_string(ADMIN_HTML,
        logged_in=False, error="Wrong password")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/admin")

@app.route("/admin/save", methods=["POST"])
def admin_save():
    if not session.get("admin"):
        return redirect("/admin")
    f = request.form
    changelog = [l.strip() for l in f.get("changelog","").splitlines() if l.strip()]
    data = {
        "title":        f.get("title","").strip(),
        "version":      f.get("version","").strip(),
        "author":       f.get("author","").strip(),
        "status":       f.get("status","").strip(),
        "description":  f.get("description","").strip(),
        "discord":      f.get("discord","").strip(),
        "credits":      f.get("credits","").strip(),
        "changelog":    changelog,
        "last_updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }
    save_data(data)
    return redirect("/admin?saved=1")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
