"""WSGI entrypoint for gunicorn:  gunicorn wsgi:app"""
import sys

sys.path.insert(0, "/var/www/capsule")

from app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    # Dev only; production is served by gunicorn behind nginx.
    app.run(host="127.0.0.1", port=8000)
