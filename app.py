import os, re, json, sqlite3, secrets, hashlib, hmac, time
from datetime import timedelta
from functools import wraps
from urllib.parse import urlparse, parse_qs, unquote
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

APP_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.environ.get("Q7VPN_DB_PATH", os.path.join(APP_DIR, "q7vpn.sqlite3"))
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE-ME-before-deploy-" + secrets.token_hex(16))
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1") != "0",
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
    MAX_CONTENT_LENGTH=1 * 1024 * 1024,
)
csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["300 per hour"], storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"))

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            phone TEXT NOT NULL,
            security_question TEXT NOT NULL,
            security_answer_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS security_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            category TEXT NOT NULL,
            detail TEXT NOT NULL,
            ip_hash TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS nodes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            uri TEXT NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(user_id, uri),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""")

def log_event(category, detail):
    ip = get_remote_address() or "unknown"
    ip_hash = hashlib.sha256((os.environ.get("IP_HASH_SALT", "change-this-salt") + ip).encode()).hexdigest()[:24]
    with db() as con:
        con.execute("INSERT INTO security_events(created_at,category,detail,ip_hash) VALUES(?,?,?,?)",
                    (int(time.time()), category, detail[:180], ip_hash))

def logged_in(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth"))
        return f(*args, **kwargs)
    return inner

def parse_node(uri):
    uri = uri.strip()
    if uri.startswith("vless://"):
        try:
            u = urlparse(uri)
            if not u.hostname or not (u.port or 443): return None
            name = unquote(u.fragment) if u.fragment else u.hostname
            return {"uri": uri, "name": name[:120], "type": "VLESS", "host": u.hostname, "port": u.port or 443}
        except Exception:
            return None
    if uri.startswith("ss://"):
        try:
            body = uri[5:].split("#", 1)[0]
            name = unquote(uri.split("#", 1)[1]) if "#" in uri else "Shadowsocks 节点"
            # SS formats vary; preserve URI and validate basic shape without decoding secrets into logs.
            if "@" not in body and len(body) < 12: return None
            return {"uri": uri, "name": name[:120], "type": "SS", "host": "", "port": ""}
        except Exception:
            return None
    return None

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("auth"))

@app.route("/auth", methods=["GET", "POST"])
@limiter.limit("12 per minute", methods=["POST"])
def auth():
    if request.method == "POST":
        mode = request.form.get("mode", "login")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
            flash("用户名需为 3–32 位字母、数字、点、下划线或短横线。", "error")
            return render_template("auth.html", mode=mode)
        if mode == "register":
            phone = request.form.get("phone", "").strip()
            question = request.form.get("question", "").strip()
            answer = request.form.get("answer", "").strip()
            if len(password) < 10:
                flash("密码至少 10 位，建议使用独立且随机的密码。", "error")
            elif not re.fullmatch(r"[+0-9 ()-]{7,24}", phone):
                flash("请输入有效格式的手机号。当前版本不会发送短信。", "error")
            elif not question or len(answer) < 2:
                flash("请选择安全问题并填写答案。", "error")
            else:
                try:
                    with db() as con:
                        con.execute("INSERT INTO users(username,password_hash,phone,security_question,security_answer_hash,created_at) VALUES(?,?,?,?,?,?)",
                                    (username, generate_password_hash(password), phone,
                                     question[:160], generate_password_hash(answer.casefold()), int(time.time())))
                    log_event("account", "新账户注册")
                    flash("注册成功，请登录。", "success")
                    return render_template("auth.html", mode="login")
                except sqlite3.IntegrityError:
                    flash("注册未完成：该用户名可能已被使用。", "error")
        elif mode == "login":
            with db() as con:
                user = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session.permanent = True
                log_event("auth", "登录成功")
                return redirect(url_for("dashboard"))
            log_event("auth", "登录失败")
            flash("用户名或密码错误。", "error")
        else:
            flash("不支持的操作。", "error")
    return render_template("auth.html", mode=request.args.get("mode", "login"))

@app.route("/recover", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def recover():
    question = None
    if request.method == "POST":
        step = request.form.get("step", "lookup")
        username = request.form.get("username", "").strip()
        phone = request.form.get("phone", "").strip()
        if step == "lookup":
            with db() as con:
                user = con.execute("SELECT username,phone,security_question FROM users WHERE username=? AND phone=?", (username, phone)).fetchone()
            if user:
                question = user["security_question"]
                session["recover_user"] = username
                flash("请回答注册时设置的安全问题。", "success")
            else:
                flash("信息不匹配或账户不存在。", "error")
        elif step == "reset":
            answer = request.form.get("answer", "").strip().casefold()
            new_password = request.form.get("new_password", "")
            uname = session.get("recover_user")
            with db() as con:
                user = con.execute("SELECT * FROM users WHERE username=?", (uname,)).fetchone() if uname else None
                if user and check_password_hash(user["security_answer_hash"], answer) and len(new_password) >= 10:
                    con.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_password), user["id"]))
                    session.pop("recover_user", None)
                    log_event("account", "密码重置")
                    flash("密码已重置，请重新登录。", "success")
                    return redirect(url_for("auth"))
                question = user["security_question"] if user else None
                flash("验证失败，或新密码不足 10 位。", "error")
    return render_template("recover.html", question=question)

@app.route("/logout", methods=["POST"])
@logged_in
def logout():
    session.clear()
    return redirect(url_for("auth"))

@app.route("/dashboard")
@logged_in
def dashboard():
    with db() as con:
        nodes = con.execute("SELECT id,uri,name FROM nodes WHERE user_id=? ORDER BY id DESC", (session["user_id"],)).fetchall()
    return render_template("dashboard.html", nodes=nodes, username=session.get("username"))

@app.post("/api/nodes/import")
@logged_in
@limiter.limit("20 per minute")
def import_nodes():
    text = request.form.get("text", "")
    added = duplicate = invalid = 0
    with db() as con:
        for line in text.splitlines()[:3000]:
            line = line.strip()
            if not line or line.startswith("#"): continue
            item = parse_node(line)
            if not item:
                invalid += 1
                continue
            try:
                con.execute("INSERT INTO nodes(user_id,uri,name) VALUES(?,?,?)", (session["user_id"], item["uri"], item["name"]))
                added += 1
            except sqlite3.IntegrityError:
                duplicate += 1
    return jsonify(added=added, duplicate=duplicate, invalid=invalid)

@app.post("/api/nodes/<int:node_id>/delete")
@logged_in
def delete_node(node_id):
    with db() as con:
        con.execute("DELETE FROM nodes WHERE id=? AND user_id=?", (node_id, session["user_id"]))
    return jsonify(ok=True)

@app.get("/api/nodes/export")
@logged_in
def export_nodes():
    from flask import Response
    with db() as con:
        rows = con.execute("SELECT uri FROM nodes WHERE user_id=? ORDER BY id", (session["user_id"],)).fetchall()
    return Response("\n".join(r["uri"] for r in rows) + ("\n" if rows else ""),
                    mimetype="text/plain; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=q7vpn-nodes.txt"})

@app.route("/security")
@logged_in
def security():
    with db() as con:
        events = con.execute("SELECT created_at,category,detail,ip_hash FROM security_events ORDER BY id DESC LIMIT 40").fetchall()
        node_count = con.execute("SELECT COUNT(*) AS c FROM nodes WHERE user_id=?", (session["user_id"],)).fetchone()["c"]
        user_count = con.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    return render_template("security.html", events=events, node_count=node_count, user_count=user_count)

@app.get("/health")
def health():
    return jsonify(status="ok", app="Q7vpn", version="3.0")

@app.errorhandler(413)
def too_large(_):
    return "上传内容过大（上限 1 MB）。", 413

init_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
