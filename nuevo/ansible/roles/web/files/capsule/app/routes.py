"""Dragon Radar Dashboard routes."""
import os
import sqlite3

from flask import (
    Blueprint, Response, current_app, g, make_response,
    redirect, render_template, request, url_for,
)

from .session import COOKIE_NAME, deserialize_session, serialize_session

bp = Blueprint("main", __name__)

UPLOAD_DIR = "/var/capsule/uploads"
ADVISORY_PATH = "/var/www/capsule/advisory.txt"


def _db():
    con = sqlite3.connect(current_app.config["DB_PATH"])
    con.row_factory = sqlite3.Row
    return con


def check_credentials(username: str, password: str) -> bool:
    con = _db()
    row = con.execute(
        "SELECT password FROM users WHERE username = ?", (username,)
    ).fetchone()
    con.close()
    return row is not None and row["password"] == password


@bp.before_app_request
def load_radar_session():
    """Rehydrate the session from the radar_session cookie on every request.

    This is the CVE-2024-42069 sink: untrusted pickle, deserialized with no
    signature check. Triggered for ANY route as soon as the cookie is present.
    """
    g.session = {}
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return
    try:
        g.session = deserialize_session(cookie)
    except Exception:
        g.session = {}
    # A well-formed session is a dict; anything else (e.g. the int an exploit
    # payload leaves behind) is treated as unauthenticated.
    if not isinstance(g.session, dict):
        g.session = {}


@bp.route("/")
def index():
    if g.session.get("authenticated"):
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if check_credentials(username, password):
            resp = make_response(redirect(url_for("main.dashboard")))
            token = serialize_session({
                "user": username,
                "role": "field-tester",
                "authenticated": True,
            })
            resp.set_cookie(COOKIE_NAME, token)
            return resp
        error = "Invalid credentials. Power level too low."
    status = 401 if error else 200
    return render_template("login.html", error=error), status


@bp.route("/dashboard")
def dashboard():
    if not g.session.get("authenticated"):
        return redirect(url_for("main.login"))
    cfg = current_app.config
    return render_template(
        "dashboard.html",
        user=g.session.get("user", "guest"),
        role=g.session.get("role", "guest"),
        app_version=cfg["APP_VERSION"],
        fixed_version=cfg["APP_FIXED_VERSION"],
        build_date=cfg["APP_BUILD_DATE"],
        paradox_date=cfg["APP_PARADOX_DATE"],
    )


@bp.route("/api/upload", methods=["POST"])
def upload():
    if not g.session.get("authenticated"):
        return {"error": "authentication required"}, 401
    f = request.files.get("file")
    if not f or not f.filename:
        return {"error": "no file provided"}, 400
    safe = os.path.basename(f.filename)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    f.save(os.path.join(UPLOAD_DIR, safe))
    return {"status": "queued", "file": safe, "note": "processed by radar timer"}


@bp.route("/security/CVE-2024-42069")
def advisory():
    if os.path.exists(ADVISORY_PATH):
        with open(ADVISORY_PATH) as fh:
            return Response(fh.read(), mimetype="text/plain")
    return Response("Advisory not found.", mimetype="text/plain", status=404)


@bp.route("/healthz")
def healthz():
    return {"status": "ok", "service": "dragon-radar"}
