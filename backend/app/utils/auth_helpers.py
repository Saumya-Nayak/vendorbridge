"""
VendorBridge — Auth Helpers
JWT decorators + activity logging
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app import db


# ------------------------------------------------------------------ #
#  Role-based access decorator
# ------------------------------------------------------------------ #
def roles_required(*allowed_roles):
    """
    Decorator that ensures:
      1. A valid JWT is present
      2. The authenticated user has one of the allowed roles

    Usage:
        @roles_required("admin", "manager")
        def my_view(): ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()

            from app.models.user import User
            user = User.query.get(int(user_id))

            if not user or not user.is_active:
                return jsonify({"success": False, "message": "User not found or inactive."}), 404

            if user.role not in allowed_roles:
                return jsonify({
                    "success": False,
                    "message": f"Access denied. Required role(s): {', '.join(allowed_roles)}.",
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user():
    """Return the User object for the authenticated JWT identity."""
    from app.models.user import User
    user_id = get_jwt_identity()
    return User.query.get(int(user_id)) if user_id else None


# ------------------------------------------------------------------ #
#  Activity logger
# ------------------------------------------------------------------ #
def log_activity(
    user_id,
    action: str,
    entity_type: str = None,
    entity_id: int = None,
    description: str = None,
    request=None,
):
    """
    Write a row to activity_logs.
    Safe to call inside any request context — silently swallows errors
    so auth flows are never broken by logging failures.
    """
    try:
        from app.models.activity_log import ActivityLog  # imported lazily to avoid circular import

        ip_address = None
        user_agent = None

        if request is not None:
            ip_address = request.remote_addr
            user_agent = (request.headers.get("User-Agent") or "")[:500]

        log = ActivityLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        # Logging must never crash the main request
        db.session.rollback()