"""
VendorBridge — Auth Routes
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/forgot-password
POST /api/auth/reset-password
GET  /api/auth/me
"""
import re
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)

from app import db
from app.models.user import User, PasswordResetToken
from app.models.vendor import VendorProfile
from app.utils.auth_helpers import log_activity
from app.utils.email_helper import send_reset_email

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #
GST_RE = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^[6-9]\d{9}$")


def _err(msg: str, code: int = 400):
    return jsonify({"success": False, "message": msg}), code


def _ok(data: dict, msg: str = "OK", code: int = 200):
    return jsonify({"success": True, "message": msg, **data}), code


# ------------------------------------------------------------------ #
#  POST /api/auth/register
# ------------------------------------------------------------------ #
@auth_bp.route("/register", methods=["POST"])
def register():
    body = request.get_json(silent=True) or {}

    # --- Required fields ---
    first_name = (body.get("first_name") or "").strip()
    last_name  = (body.get("last_name")  or "").strip()
    email      = (body.get("email")      or "").strip().lower()
    company    = (body.get("company")    or "").strip()
    role       = (body.get("role")       or "").strip()
    password   = body.get("password", "")

    if not all([first_name, last_name, email, company, role, password]):
        return _err("All required fields must be provided.")

    # --- Validate email ---
    if not EMAIL_RE.match(email):
        return _err("Enter a valid email address.")

    # --- Validate role ---
    valid_roles = {"procurement_officer", "vendor", "manager", "admin"}
    if role not in valid_roles:
        return _err(f"Invalid role. Choose from: {', '.join(valid_roles)}.")

    # --- Validate password ---
    if len(password) < 8:
        return _err("Password must be at least 8 characters.")

    # --- Validate phone (optional) ---
    phone = (body.get("phone") or "").strip() or None
    if phone and not PHONE_RE.match(phone.replace(" ", "")):
        return _err("Enter a valid 10-digit phone number.")

    # --- Check duplicate email ---
    if User.query.filter_by(email=email).first():
        return _err("An account with this email already exists.", 409)

    # --- Create user ---
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        company=company,
        role=role,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # get user.id before commit

    # --- Vendor profile ---
    if role == "vendor":
        gst_raw = (body.get("gst_number") or "").strip().upper() or None
        if gst_raw and not GST_RE.match(gst_raw):
            db.session.rollback()
            return _err("Enter a valid 15-character GST number.")

        profile = VendorProfile(
            user_id=user.id,
            gst_number=gst_raw,
            vendor_category=(body.get("vendor_category") or "").strip() or None,
        )
        db.session.add(profile)

    db.session.commit()

    log_activity(
        user_id=user.id,
        action="user_registered",
        entity_type="user",
        entity_id=user.id,
        description=f"New {role} account created for {email}",
        request=request,
    )

    return _ok({"user": user.to_dict()}, "Account created successfully.", 201)


# ------------------------------------------------------------------ #
#  POST /api/auth/login
# ------------------------------------------------------------------ #
@auth_bp.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}

    email    = (body.get("email")    or "").strip().lower()
    password = body.get("password", "")
    remember = bool(body.get("remember", False))

    if not email or not password:
        return _err("Email and password are required.")

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return _err("Invalid email or password.", 401)

    if not user.is_active:
        return _err("Your account has been deactivated. Contact support.", 403)

    # Token expiry: 7 days if remember-me, else 1 day
    expires = timedelta(days=7 if remember else 1)
    access_token  = create_access_token(identity=str(user.id), expires_delta=expires)
    refresh_token = create_refresh_token(identity=str(user.id))

    # Update last login
    user.last_login_at = datetime.utcnow()
    db.session.commit()

    log_activity(
        user_id=user.id,
        action="user_login",
        entity_type="user",
        entity_id=user.id,
        description=f"Login from {request.remote_addr}",
        request=request,
    )

    return _ok(
        {
            "token":         access_token,
            "refresh_token": refresh_token,
            "user":          user.to_dict(),
        },
        "Logged in successfully.",
    )


# ------------------------------------------------------------------ #
#  POST /api/auth/logout  (client just drops the token; log it)
# ------------------------------------------------------------------ #
@auth_bp.route("/logout", methods=["POST"])
@jwt_required(optional=True)
def logout():
    user_id = get_jwt_identity()
    if user_id:
        log_activity(
            user_id=int(user_id),
            action="user_logout",
            entity_type="user",
            entity_id=int(user_id),
            description="User logged out",
            request=request,
        )
    return _ok({}, "Logged out successfully.")


# ------------------------------------------------------------------ #
#  GET /api/auth/me
# ------------------------------------------------------------------ #
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user or not user.is_active:
        return _err("User not found or inactive.", 404)
    return _ok({"user": user.to_dict()})


# ------------------------------------------------------------------ #
#  POST /api/auth/forgot-password
# ------------------------------------------------------------------ #
@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    body  = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()

    if not email or not EMAIL_RE.match(email):
        return _err("Enter a valid email address.")

    user = User.query.filter_by(email=email).first()

    # Always return success to prevent email enumeration
    if user and user.is_active:
        # Invalidate old tokens
        PasswordResetToken.query.filter_by(user_id=user.id, used=False).delete()

        token = secrets.token_urlsafe(48)
        prt = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.session.add(prt)
        db.session.commit()

        reset_url = f"{current_app.config.get('FRONTEND_URL', 'http://localhost:5500')}/frontend/pages/reset-password.html?token={token}"

        try:
            send_reset_email(user.email, user.full_name, reset_url)
        except Exception as exc:
            current_app.logger.error(f"Reset email failed for {email}: {exc}")

        log_activity(
            user_id=user.id,
            action="password_reset_requested",
            entity_type="user",
            entity_id=user.id,
            description=f"Password reset requested from {request.remote_addr}",
            request=request,
        )

    return _ok({}, "If that email exists, reset instructions have been sent.")


# ------------------------------------------------------------------ #
#  POST /api/auth/reset-password
# ------------------------------------------------------------------ #
@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    body     = request.get_json(silent=True) or {}
    token    = (body.get("token")    or "").strip()
    password = body.get("password",  "")

    if not token or not password:
        return _err("Token and new password are required.")

    if len(password) < 8:
        return _err("Password must be at least 8 characters.")

    prt = PasswordResetToken.query.filter_by(token=token).first()
    if not prt or not prt.is_valid:
        return _err("This reset link is invalid or has expired.", 400)

    user = User.query.get(prt.user_id)
    if not user or not user.is_active:
        return _err("User not found.", 404)

    user.set_password(password)
    prt.used = True
    db.session.commit()

    log_activity(
        user_id=user.id,
        action="password_reset_completed",
        entity_type="user",
        entity_id=user.id,
        description="Password was reset successfully",
        request=request,
    )

    return _ok({}, "Password updated successfully. You can now log in.")


# ------------------------------------------------------------------ #
#  POST /api/auth/refresh
# ------------------------------------------------------------------ #
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id      = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    return _ok({"token": access_token}, "Token refreshed.")