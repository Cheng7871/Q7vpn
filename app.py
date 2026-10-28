from flask import Flask, render_template, request, jsonify
from urllib.parse import urlparse, parse_qs, unquote
import base64, json, re, uuid

app = Flask(__name__)
MAX_NODES = 2000

def b64decode_nopad(s):
    s = s.strip()
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode()).decode("utf-8", errors="replace")

def parse_ss(uri):
    raw = uri[5:]
    name = ""
    if "#" in raw:
        raw, frag = raw.split("#", 1)
        name = unquote(frag)
    try:
        decoded = b64decode_nopad(raw) if "@" not in raw else raw
        if "@" not in decoded:
            return None
        userinfo, server = decoded.rsplit("@", 1)
        method, password = userinfo.split(":", 1)
        host, port = server.rsplit(":", 1)
        return {"id": str(uuid.uuid4()), "type":"SS", "name":name or host,
                "host":host, "port":int(port), "method":method,
                "uri":uri.strip()}
    except Exception:
        return None

def parse_vless(uri):
    try:
        u = urlparse(uri)
        qs = parse_qs(u.query)
        name = unquote(u.fragment) if u.fragment else (u.hostname or "VLESS")
        return {"id":str(uuid.uuid4()), "type":"VLESS", "name":name,
                "host":u.hostname or "", "port":u.port or 443,
                "uuid":unquote(u.username or ""),
                "security":qs.get("security",[""])[0],
                "network":qs.get("type",[""])[0],
                "uri":uri.strip()}
    except Exception:
        return None

def parse_uri(uri):
    uri = uri.strip()
    if uri.lower().startswith("ss://"):
        return parse_ss(uri)
    if uri.lower().startswith("vless://"):
        return parse_vless(uri)
    return None

@app.route("/")
def index():
    return render_template("index.html")

@app.post("/api/import")
def import_nodes():
    text = request.form.get("text","")
    nodes=[]
    for line in text.splitlines():
        item=parse_uri(line.strip())
        if item:
            nodes.append(item)
        if len(nodes)>=MAX_NODES:
            break
    return jsonify(nodes=nodes, count=len(nodes))

@app.post("/api/parse")
def parse_one():
    item=parse_uri(request.json.get("uri",""))
    if not item:
        return jsonify(error="不支持的节点格式，目前支持 SS / VLESS"), 400
    return jsonify(item)

@app.get("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
