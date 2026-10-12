"""Smart Campus Analytics: Flask backend (SQLite, session login, admin and staff roles)."""
import csv
import hashlib
import io
import os
import re
import secrets
import sqlite3
import time
from datetime import timedelta
from functools import wraps
from ai_engine import predict

from flask import (Flask, Response, abort, g, jsonify, redirect,
                   render_template, request, session)
from werkzeug.security import check_password_hash, generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE, "campus.db"))


def _secret():
    key = os.environ.get("SECRET_KEY")
    if key:
        return key
    path = os.path.join(BASE, ".secret_key")
    if not os.path.exists(path):
        with open(path, "w") as fh:
            fh.write(secrets.token_hex(32))
        os.chmod(path, 0o600)
    with open(path) as fh:
        return fh.read().strip()


app = Flask(__name__)
app.config.update(
    SECRET_KEY=_secret(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=1 << 20,
)

DEPARTMENTS = ["CSE", "ECE", "EEE", "MECH", "CIVIL"]
ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,24}$")
USER_RE = re.compile(r"^[a-z0-9._-]{3,32}$")
MIN_PASSWORD = 10

# table -> field -> (min, max, type)
TABLES = {
    "academic": {"cgpa": (0, 10, "float"), "backlogs": (0, 50, "int")},
    "attendance": {"overall_pct": (0, 100, "float")},
    "lms": {"login_score": (0, 100, "float"), "assignment_pct": (0, 100, "float")},
    "engagement": {"events": (0, 1000, "int"), "clubs": (0, 100, "int"),
                   "hackathons": (0, 100, "int"), "certifications": (0, 100, "int")},
    "placement": {"aptitude": (0, 100, "float"), "coding": (0, 100, "float"),
                  "mock_interview": (0, 100, "float")},
    "skills": {"technical": (0, 100, "float"), "soft": (0, 100, "float")},
    "feedback": {"satisfaction": (1, 5, "float"), "faculty": (1, 5, "float")},
}
WEIGHTS = {"acad": 30, "att": 20, "lms": 12, "plc": 15, "skl": 10, "eng": 8, "fb": 5}
LABELS = {"acad": "Academic", "att": "Attendance", "lms": "LMS activity",
          "plc": "Placement readiness", "skl": "Skills", "eng": "Engagement", "fb": "Feedback"}
SEGMENTS = {
    "a": ["Strong academics, low placement readiness",
          "Offer aptitude and coding bootcamps, mock interviews and company-specific drives."],
    "b": ["Attendance or backlog concern",
          "Mentor meeting and a backlog clearing plan."],
    "c": ["Low engagement",
          "Invite to clubs, hackathons and certification tracks; check LMS access problems first."],
    "d": ["Placement ready",
          "Route to top recruiters and advanced coding practice."],
    "e": ["Steady performers", "Monitor each term; offer optional skill workshops."],
    "u": ["Insufficient data", "Complete the missing records so a segment can be assigned."],
}
MIN_WEIGHT_FOR_SCORE = 60  # a score needs at least this much of the 100 weight present


# ---------------------------------------------------------------- database
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    with open(os.path.join(BASE, "schema.sql")) as fh:
        conn.executescript(fh.read())
    conn.close()


init_db()

SELECT_ALL = """
SELECT s.id, s.department, s.year, a.cgpa, a.backlogs, t.overall_pct,
       l.login_score, l.assignment_pct, e.events, e.clubs, e.hackathons, e.certifications,
       p.aptitude, p.coding, p.mock_interview, k.technical, k.soft, f.satisfaction, f.faculty
FROM students s
LEFT JOIN academic a ON a.student_id = s.id
LEFT JOIN attendance t ON t.student_id = s.id
LEFT JOIN lms l ON l.student_id = s.id
LEFT JOIN engagement e ON e.student_id = s.id
LEFT JOIN placement p ON p.student_id = s.id
LEFT JOIN skills k ON k.student_id = s.id
LEFT JOIN feedback f ON f.student_id = s.id
"""
RAW_FIELDS = [f for t in TABLES.values() for f in t]


# ---------------------------------------------------------------- scoring
def _cl(x):
    return max(0.0, min(100.0, x))


def compute(r):
    def has(*keys):
        return all(r[k] is not None for k in keys)

    idx = {}
    if has("cgpa", "backlogs"):
        idx["acad"] = _cl(r["cgpa"] * 10 - r["backlogs"] * 8)
    if has("overall_pct"):
        idx["att"] = _cl(r["overall_pct"])
    if has("login_score", "assignment_pct"):
        idx["lms"] = (r["login_score"] + r["assignment_pct"]) / 2
    if has("aptitude", "coding", "mock_interview"):
        idx["plc"] = (r["aptitude"] + r["coding"] + r["mock_interview"]) / 3
    if has("technical", "soft"):
        idx["skl"] = (r["technical"] + r["soft"]) / 2
    if has("events", "clubs", "hackathons", "certifications"):
        idx["eng"] = _cl(r["events"] * 10 + r["clubs"] * 15
                         + r["hackathons"] * 20 + r["certifications"] * 15)
    if has("satisfaction", "faculty"):
        idx["fb"] = (r["satisfaction"] + r["faculty"]) / 2 * 20

    part = {k: WEIGHTS[k] * v / 100 for k, v in idx.items()}
    loss = {k: WEIGHTS[k] - part[k] for k in part}
    wsum = sum(WEIGHTS[k] for k in idx)
    score = round(100 * sum(part.values()) / wsum, 1) if wsum >= MIN_WEIGHT_FOR_SCORE else None
    level = "Unrated" if score is None else "High" if score < 52 else "Medium" if score < 64 else "Low"

    acad_risk = bool((has("cgpa", "backlogs") and (r["cgpa"] < 6 or r["backlogs"] >= 2))
                     or (has("overall_pct") and r["overall_pct"] < 75))
    plc_risk = "plc" in idx and idx["plc"] < 50

    if all(k in idx for k in ("acad", "att", "lms", "plc", "eng")):
        if idx["acad"] >= 70 and idx["plc"] < 55:
            seg = "a"
        elif idx["att"] < 75 or r["backlogs"] >= 2:
            seg = "b"
        elif idx["lms"] < 55 and idx["eng"] < 40:
            seg = "c"
        elif idx["plc"] >= 65 and idx["acad"] >= 65:
            seg = "d"
        else:
            seg = "e"
    else:
        seg = "u"

    return {
        "id": r["id"], "dept": r["department"], "year": r["year"],
        "raw": {f: r[f] for f in RAW_FIELDS},
        "idx": {k: round(v, 1) for k, v in idx.items()},
        "part": {k: round(v, 2) for k, v in part.items()},
        "loss": {k: round(v, 2) for k, v in loss.items()},
        "score": score, "level": level, "acadRisk": acad_risk, "plcRisk": plc_risk,
        "seg": seg, "top": sorted(loss, key=lambda k: -loss[k])[:3],
        "missing": [k for k in WEIGHTS if k not in idx],
        "ai": predict(idx),
        "risk_reasons": (["CGPA below 6"] if has("cgpa", "backlogs") and r["cgpa"] < 6 else [])
            + (["Two or more backlogs"] if has("cgpa", "backlogs") and r["backlogs"] >= 2 else [])
            + (["Attendance below 75%"] if has("overall_pct") and r["overall_pct"] < 75 else [])
            + (["Placement readiness below 50/100"] if plc_risk else []),
    }


# ---------------------------------------------------------------- auth, CSRF, headers
FAILS = {}
DUMMY_HASH = generate_password_hash("not-a-real-password")


@app.before_request
def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        row = db().execute("SELECT id, username, full_name, role, active, department, student_id, password_hash FROM users WHERE id = ?",
                           (uid,)).fetchone()
        if row and row["active"] and session.get("credential") == hashlib.sha256(row["password_hash"].encode()).hexdigest():
            g.user = row
        else:
            session.clear()
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
        if not secrets.compare_digest(sent.encode(), session["csrf"].encode()):
            abort(400)


@app.after_request
def headers(resp):
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    if request.path.startswith("/api/") or request.path in ("/", "/login"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.errorhandler(403)
@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(413)
def http_error(err):
    if request.path.startswith("/api/"):
        return jsonify(error=err.name), err.code
    return render_template("error.html", code=err.code, name=err.name), err.code


def need(admin=False):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not g.user:
                if request.path.startswith("/api/"):
                    return jsonify(error="Sign in required"), 401
                return redirect("/login")
            if admin and g.user["role"] != "admin":
                return jsonify(error="Administrator only"), 403
            return fn(*a, **kw)
        return wrapper
    return deco


def audit(action, detail=""):
    who = g.user["username"] if g.get("user") else "anonymous"
    db().execute("INSERT INTO audit_log(username, action, detail) VALUES (?,?,?)", (who, action, detail))
    db().commit()


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect("/")
    error = None
    if request.method == "POST":
        ip = request.remote_addr or "unknown"
        now = time.time()
        FAILS[ip] = [t for t in FAILS.get(ip, []) if now - t < 300]
        if len(FAILS[ip]) >= 5:
            error = "Too many failed attempts. Try again in a few minutes."
        else:
            row = db().execute("SELECT * FROM users WHERE username = ?",
                               (request.form.get("username", "").strip().lower(),)).fetchone()
            ok = check_password_hash(row["password_hash"] if row else DUMMY_HASH,
                                     request.form.get("password", ""))
            if row and ok and row["active"]:
                session.clear()
                session.permanent = True
                session["uid"] = row["id"]
                session["credential"] = hashlib.sha256(row["password_hash"].encode()).hexdigest()
                session["csrf"] = secrets.token_hex(16)
                g.user = row
                audit("login")
                return redirect("/")
            FAILS[ip].append(now)
            error = "Invalid username or password."
    return render_template("login.html", csrf=session["csrf"], error=error)


@app.route("/logout", methods=["POST"])
def logout():
    if g.user:
        audit("logout")
    session.clear()
    return redirect("/login")


# ---------------------------------------------------------------- pages
@app.route("/")
@need()
def index():
    return render_template("dashboard.html", user=g.user, csrf=session["csrf"])


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/healthz")
def healthz():
    return jsonify(status="ok")


# ---------------------------------------------------------------- data API
@app.route("/api/meta")
@need()
def api_meta():
    return jsonify(user={"username": g.user["username"], "name": g.user["full_name"], "role": g.user["role"], "department": g.user["department"], "student_id": g.user["student_id"]},
                   departments=DEPARTMENTS, fields={t: {f: list(v) for f, v in fs.items()} for t, fs in TABLES.items()},
                   weights=WEIGHTS, labels=LABELS, segments=SEGMENTS)


@app.route("/api/students")
@need()
def api_students():
    rows = scoped_rows()
    return jsonify([compute(r) for r in rows])


def scope():
    if g.user["role"] == "faculty":
        return " WHERE s.department = ?", [g.user["department"]]
    if g.user["role"] == "student":
        return " WHERE s.id = ?", [g.user["student_id"] or ""]
    return "", []


def scoped_rows():
    where, args = scope()
    return db().execute(SELECT_ALL + where + " ORDER BY s.id", args).fetchall()


def _student_row(sid):
    where, args = scope()
    return db().execute(SELECT_ALL + where + (" AND" if where else " WHERE") + " s.id = ?", args + [sid]).fetchone()


@app.route("/api/students", methods=["POST"])
@need(admin=True)
def api_add_student():
    d = body()
    sid, dept = str(d.get("id", "")).strip(), d.get("department")
    try:
        year = int(d.get("year"))
    except (TypeError, ValueError):
        year = 0
    if not ID_RE.match(sid) or dept not in DEPARTMENTS or year not in (1, 2, 3, 4):
        return jsonify(error="Check ID (3-24 letters, digits, - or _), department and year."), 400
    try:
        db().execute("INSERT INTO students(id, department, year) VALUES (?,?,?)", (sid, dept, year))
        db().commit()
    except sqlite3.IntegrityError:
        return jsonify(error="That student ID already exists."), 409
    audit("add_student", sid)
    return jsonify(ok=True), 201


@app.route("/api/students/<sid>", methods=["DELETE"])
@need(admin=True)
def api_delete_student(sid):
    cur = db().execute("DELETE FROM students WHERE id = ?", (sid,))
    db().commit()
    if not cur.rowcount:
        return jsonify(error="Student not found."), 404
    audit("delete_student", sid)
    return jsonify(ok=True)


def _parse(table, data):
    out = {}
    for field, (lo, hi, kind) in TABLES[table].items():
        try:
            v = float(data.get(field))
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be a number")
        if v != v or not lo <= v <= hi:
            raise ValueError(f"{field} must be between {lo} and {hi}")
        if kind == "int":
            if v != int(v):
                raise ValueError(f"{field} must be a whole number")
            v = int(v)
        out[field] = v
    return out


@app.route("/api/students/<sid>/<table>", methods=["POST"])
@need()
def api_update(sid, table):
    if g.user["role"] == "student":
        return jsonify(error="Students have read-only access to academic records."), 403
    if table not in TABLES:
        return jsonify(error="Unknown table."), 404
    if not _student_row(sid):
        return jsonify(error="Student not found."), 404
    try:
        vals = _parse(table, body())
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    cols = list(vals)
    sql = (f"INSERT INTO {table}(student_id,{','.join(cols)}) VALUES (?,{','.join('?' * len(cols))}) "
           f"ON CONFLICT(student_id) DO UPDATE SET {','.join(c + '=excluded.' + c for c in cols)},"
           "updated_at=CURRENT_TIMESTAMP")
    db().execute(sql, [sid] + [vals[c] for c in cols])
    db().commit()
    audit("update_" + table, sid)
    return jsonify(ok=True)


def _cell(v):
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s


@app.route("/export.csv")
@need()
def export_csv():
    rows = [compute(r) for r in scoped_rows()]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["student_id", "department", "year", "score", "risk_level", "academic_flag",
                "placement_flag", "segment"] + RAW_FIELDS)
    for s in rows:
        w.writerow([_cell(x) for x in [s["id"], s["dept"], s["year"], s["score"], s["level"],
                                       int(s["acadRisk"]), int(s["plcRisk"]), SEGMENTS[s["seg"]][0]]
                    + [s["raw"][f] for f in RAW_FIELDS]])
    audit("export_csv")
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=student-success.csv"})


# ---------------------------------------------------------------- admin API
@app.route("/api/users")
@need(admin=True)
def api_users():
    rows = db().execute("SELECT id, username, full_name, role, active, department, student_id, created_at FROM users ORDER BY id").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/users", methods=["POST"])
@need(admin=True)
def api_add_user():
    d = body()
    username, name, role = str(d.get("username", "")).strip().lower(), str(d.get("full_name", "")).strip(), d.get("role")
    pw = str(d.get("password", ""))
    if not USER_RE.match(username) or not 1 <= len(name) <= 80 or role not in ("admin", "faculty", "student"):
        return jsonify(error="Check username (3-32 of a-z 0-9 . _ -), full name and role."), 400
    if len(pw) < MIN_PASSWORD:
        return jsonify(error=f"Password must be at least {MIN_PASSWORD} characters."), 400
    dept = d.get("department") if role == "faculty" else None
    sid = str(d.get("student_id", "")).strip() if role == "student" else None
    if role == "faculty" and dept not in DEPARTMENTS:
        return jsonify(error="Choose a department for faculty."), 400
    if role == "student" and not db().execute("SELECT id FROM students WHERE id=?", (sid,)).fetchone():
        return jsonify(error="Enter an existing student ID for student access."), 400
    try:
        db().execute("INSERT INTO users(username, password_hash, full_name, role, department, student_id) VALUES (?,?,?,?,?,?)",
                     (username, generate_password_hash(pw), name, role, dept, sid))
        db().commit()
    except sqlite3.IntegrityError:
        return jsonify(error="That username is taken."), 409
    audit("add_user", f"{username} ({role})")
    return jsonify(ok=True), 201


@app.route("/api/users/<int:uid>", methods=["PATCH"])
@need(admin=True)
def api_patch_user(uid):
    d = body()
    row = db().execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()
    if not row:
        return jsonify(error="User not found."), 404
    if "active" in d:
        if uid == g.user["id"]:
            return jsonify(error="You cannot disable your own account."), 400
        db().execute("UPDATE users SET active = ? WHERE id = ?", (1 if d["active"] else 0, uid))
        audit("set_active", f"{row['username']}={1 if d['active'] else 0}")
    if "password" in d:
        pw = str(d["password"])
        if len(pw) < MIN_PASSWORD:
            return jsonify(error=f"Password must be at least {MIN_PASSWORD} characters."), 400
        db().execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(pw), uid))
        audit("reset_password", row["username"])
    db().commit()
    return jsonify(ok=True)


@app.route("/api/audit")
@need(admin=True)
def api_audit():
    rows = db().execute("SELECT at, username, action, detail FROM audit_log ORDER BY id DESC LIMIT 100").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/password", methods=["POST"])
@need()
def password_change():
    d = body()
    row = db().execute("SELECT password_hash FROM users WHERE id=?", (g.user["id"],)).fetchone()
    if not check_password_hash(row["password_hash"], str(d.get("current", ""))):
        return jsonify(error="Current password is incorrect."), 400
    pw = str(d.get("password", ""))
    if len(pw) < MIN_PASSWORD:
        return jsonify(error="Use at least 10 characters."), 400
    hashed = generate_password_hash(pw)
    db().execute("UPDATE users SET password_hash=? WHERE id=?", (hashed, g.user["id"]))
    db().commit()
    session["credential"] = hashlib.sha256(hashed.encode()).hexdigest()
    audit("change_password")
    return jsonify(ok=True)


@app.route("/api/students/<sid>/interventions", methods=["GET", "POST"])
@need()
def interventions(sid):
    if not _student_row(sid):
        return jsonify(error="Student not found."), 404
    if request.method == "POST":
        if g.user["role"] == "student":
            return jsonify(error="Faculty or Admin access required."), 403
        d = body()
        action, status = str(d.get("action", "")).strip(), d.get("status", "Open")
        if not 1 <= len(action) <= 1000 or status not in ("Open", "In progress", "Completed"):
            return jsonify(error="Enter an action and a valid status."), 400
        if d.get("id"):
            cur = db().execute("UPDATE interventions SET action=?,status=? WHERE id=? AND student_id=?",
                               (action, status, d["id"], sid))
            if not cur.rowcount:
                return jsonify(error="Action not found."), 404
        else:
            db().execute("INSERT INTO interventions(student_id,action,status,created_by) VALUES(?,?,?,?)",
                         (sid, action, status, g.user["username"]))
        db().commit()
        audit("intervention", sid)
    rows = db().execute("SELECT * FROM interventions WHERE student_id=? ORDER BY id DESC", (sid,)).fetchall()
    return jsonify([dict(r) for r in rows])


import sys
from integration import register
register(app, sys.modules[__name__])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
