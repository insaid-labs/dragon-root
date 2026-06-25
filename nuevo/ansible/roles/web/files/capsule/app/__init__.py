"""Dragon Radar Dashboard — Flask application factory.

Capsule Corporation internal tooling. See config.py for deployment settings.
"""
from flask import Flask

CONFIG_PATH = "/var/www/capsule/config.py"


def create_app():
    app = Flask(__name__)
    app.config.from_pyfile(CONFIG_PATH)

    from .routes import bp
    app.register_blueprint(bp)
    return app
