# backend/app/__init__.py
# VendorBridge — Flask Application Factory (circular-import-safe)

from flask import Flask
from flask_cors import CORS
from app.extensions import db, jwt   # ← single source of truth for db & jwt


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)

    # ------------------------------------------------------------------ #
    #  Config
    # ------------------------------------------------------------------ #
    from app.config import config_map
    app.config.from_object(config_map[config_name])

    # ------------------------------------------------------------------ #
    #  Extensions  (init with app AFTER config is loaded)
    # ------------------------------------------------------------------ #
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ------------------------------------------------------------------ #
    #  JWT error handlers
    # ------------------------------------------------------------------ #
    @jwt.unauthorized_loader
    def missing_token(reason):
        return {"success": False, "message": "Authorization token missing."}, 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return {"success": False, "message": "Invalid or malformed token."}, 422

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_data):
        return {"success": False, "message": "Token has expired. Please log in again."}, 401

    # ------------------------------------------------------------------ #
    #  Blueprints  (imported INSIDE create_app — after extensions are set up)
    # ------------------------------------------------------------------ #
    from app.routes.auth      import auth_bp
    from app.routes.dashboard import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    from app.routes.vendors import vendors_bp
    app.register_blueprint(vendors_bp)
    from app.routes.quotations import quotations_bp
    app.register_blueprint(quotations_bp)
    # Health check
    @app.route("/api/health")
    def health():
        return {"status": "ok", "service": "VendorBridge API"}

    return app