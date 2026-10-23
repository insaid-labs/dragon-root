"""Dragon Radar Dashboard routes."""
import os
import sqlite3
import subprocess

from flask import (
    Blueprint, Response, current_app, g, make_response,
    redirect, render_template, request, url_for,
)

from .session import COOKIE_NAME, deserialize_session, serialize_session

bp = Blueprint("main", __name__)

UPLOAD_DIR = "/var/capsule/uploads"
ADVISORY_PATH = "/var/www/capsule/advisory.txt"

# ---- Shenlong altar (ball #7 + wish bonus) ----------------------------------
# Mission 1 (/altar/summon): ritual tamper (planet/kami_sama/ki) + the root-only
#   "Seal of Ki" -> decrypts ball7.enc (AES, key = altar_sigil).
# Mission 2 (/altar/invoke): gather the 7 balls into the root-owned collection
#   dir -> decrypts bonus.enc (AES, key = the 7 collected flags joined).
# The app runs as www-data and only ever holds the ciphertext.
ALTAR_SEAL_DIR = "/var/www/capsule/seal"
DRAGONBALLS_DIR = "/var/capsule/dragonballs"
ALTAR_MIN_KI = 9000
_EARTH = {"earth", "tierra"}
_KAMI_ALIVE = {"alive", "true", "1", "vivo", "si", "sí", "yes", "revive", "revived"}


def _altar_unseal(seal_name: str, sigil: str):
    """Decrypt a seal with the player-supplied sigil; None if sigil is wrong."""
    path = os.path.join(ALTAR_SEAL_DIR, seal_name)
    if not sigil or not os.path.isfile(path):
        return None
    try:
        proc = subprocess.run(
            ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2",
             "-k", sigil, "-in", path],
            capture_output=True, timeout=5,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    text = proc.stdout.decode("utf-8", "replace").strip()
    # Only a correct key yields a well-formed flag; garbage means wrong sigil.
    if not (text.startswith("CAPSULE{") or text.startswith("THM{")):
        return None
    return text


def _present_balls():
    present = []
    for i in range(1, 8):
        p = os.path.join(DRAGONBALLS_DIR, "dragon_ball_%d.txt" % i)
        try:
            if os.path.isfile(p) and os.path.getsize(p) > 0:
                present.append(i)
        except OSError:
            pass
    return present


def _bonus_key():
    """The bonus is sealed with a key derived from the 7 collected ball flags
    (colon-joined). It is only derivable once ALL 7 are gathered into the
    root-owned collection dir — so the bonus requires root (to populate the dir),
    not the sigil or Burp. www-data cannot assemble it on its own."""
    parts = []
    for i in range(1, 8):
        p = os.path.join(DRAGONBALLS_DIR, "dragon_ball_%d.txt" % i)
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                parts.append(fh.read().strip())
        except OSError:
            return None
    if any(not x for x in parts):
        return None
    return ":".join(parts)


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
    # Public landing page: Bulma's distress message routed over the "old
    # system" (POP3). Plants the port-110 breadcrumb before any auth. An
    # already-authenticated operator is sent straight to the dashboard.
    if g.session.get("authenticated"):
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


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


@bp.route("/altar")
def altar():
    # Public altar page. The summon is gated server-side (see /altar/summon):
    # ritual params + the root-only Seal of Ki. Nothing secret is rendered here.
    return render_template("altar.html")


@bp.route("/altar/status")
def altar_status():
    # Which of the 7 balls are gathered in the collection dir. The altar page
    # polls this to keep the "N/7" counter live as the player copies balls in.
    present = _present_balls()
    return {"present": present, "collected": len(present)}


@bp.route("/altar/summon", methods=["POST"])
def altar_summon():
    f = request.form
    planet = f.get("planet", "").strip().lower()
    kami = f.get("kami_sama", "").strip().lower()
    ki_raw = f.get("ki", "").strip()
    sigil = f.get("sigil", "")

    reasons = []
    if planet not in _EARTH:
        reasons.append(
            "Invocas desde el mundo equivocado. Las Esferas de la TIERRA solo "
            "despiertan a Shenlong en la Tierra; en Namek responde Porunga.")
    if kami not in _KAMI_ALIVE:
        reasons.append(
            "Kami-sama, guardian de las Esferas de la Tierra, ha muerto. Sin el, "
            "las esferas son simples piedras. Devuelvele la vida.")
    try:
        ki = int(ki_raw)
    except ValueError:
        ki = None
        reasons.append("El rastreador no logra leer tu ki. Declara un nivel de poder.")
    if ki is not None and ki <= ALTAR_MIN_KI:
        reasons.append(
            "Tu ki es %d. Shenlong solo despierta ante quien SUPERA los 9000." % ki)

    if reasons:
        return {"status": "denied", "awake": False, "reasons": reasons}

    # Ritual correct -> only the true Seal of Ki (root-only) lifts the seal.
    ball7 = _altar_unseal("ball7.enc", sigil)
    if not ball7:
        return {"status": "denied", "awake": False, "reasons": [
            "Pronuncias el ritual completo... pero el Sello del Ki no es valido. "
            "Solo quien domina el santuario (root) posee el verdadero sello."]}

    return {
        "status": "granted", "awake": True, "ball7": ball7,
        "collected": len(_present_balls()),
        "message": "¡MAS DE 9000! Arrancas la Esfera de 7 Estrellas al guardian del altar.",
    }


@bp.route("/altar/invoke", methods=["POST"])
def altar_invoke():
    # MISSION 2 (the wish): no ritual/sigil/Burp — just gather the 7 balls into
    # the root-owned collection dir and press the button. The bonus is decrypted
    # with the collected-balls key (see _bonus_key), so it needs root to populate
    # the dir, nothing more.
    present = _present_balls()
    if len(present) < 7:
        return {"status": "incomplete", "awake": False, "collected": len(present),
                "present": present,
                "message": ("Shenlong no responde: reune las 7 Esferas del Dragon en "
                            "/var/capsule/dragonballs/ (tienes %d/7)." % len(present))}
    bonus = _altar_unseal("bonus.enc", _bonus_key() or "")
    if not bonus:
        return {"status": "incomplete", "awake": False, "collected": 7, "present": present,
                "message": ("Hay 7 archivos en el altar, pero su poder no es autentico. "
                            "Reune las esferas de verdad.")}
    return {"status": "granted", "awake": True, "bonus": bonus, "collected": 7,
            "message": "Las 7 Esferas brillan al unisono. Shenlong se alza y concede tu deseo."}


@bp.route("/recovery")
def recovery():
    # Public "No More Capsule" decryptor portal. Themed after nomoreransom.org:
    # a player who found the friezacrypt-sealed ball #4 looks up the family by
    # extension here and gets the leaked key + the exact openssl command. The
    # family->key mapping lives client-side in the template (see all.yml note).
    return render_template("recovery.html")


@bp.route("/security/CVE-2024-42069")
def advisory():
    if os.path.exists(ADVISORY_PATH):
        with open(ADVISORY_PATH) as fh:
            return Response(fh.read(), mimetype="text/plain")
    return Response("Advisory not found.", mimetype="text/plain", status=404)


@bp.route("/healthz")
def healthz():
    return {"status": "ok", "service": "dragon-radar"}
