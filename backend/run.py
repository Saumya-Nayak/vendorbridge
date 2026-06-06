"""
VendorBridge — Entry Point
Run with: python run.py
"""
import os
from app import create_app, db
from app.models import User, VendorProfile, PasswordResetToken, ActivityLog  # noqa: F401 — ensures models are registered
from app.models import User, VendorProfile, VendorProfile, PasswordResetToken, ActivityLog
from app.models.quotation import Quotation
app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    with app.app_context():
        # Create tables if they don't exist (dev only — use schema.sql in prod)
        db.create_all()
        print("✅  VendorBridge API is ready.")

    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", 5000)),
        debug=app.config.get("DEBUG", True),
    )