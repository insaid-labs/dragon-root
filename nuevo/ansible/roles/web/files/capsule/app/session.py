"""Session management module.

  Dragon Radar Dashboard stores authenticated session state client-side in the
  ``radar_session`` cookie. The value is base64(pickle(session_dict)).

  !!  SECURITY (CVE-2024-42069 / CWE-502)  !!
  The cookie is deserialized with ``pickle.loads`` on every request WITHOUT any
  integrity verification — no HMAC, no signing key. An attacker who can set the
  cookie can therefore execute arbitrary code during deserialization.

  The fixed 2.4.2 release (not deployed here) replaces this with itsdangerous-
  signed JSON tokens. See app/session_fixed.py.example for the patched design.
"""
import base64
import pickle

COOKIE_NAME = "radar_session"


def serialize_session(data: dict) -> str:
    """Pack a session dict into the cookie value."""
    return base64.b64encode(pickle.dumps(data)).decode("utf-8")


def deserialize_session(cookie_value: str):
    """Unpack the cookie value back into a session object.

    VULNERABLE: pickle.loads on untrusted input. Do not do this.
    """
    raw = base64.b64decode(cookie_value)
    return pickle.loads(raw)  # noqa: S301  (intentionally vulnerable)
