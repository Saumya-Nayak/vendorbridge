"""
VendorBridge — Vendors Route
Phase 2: Full vendor CRUD, status management, role-based access

Endpoints:
  GET    /api/vendors                  → list all vendors (all roles except vendor)
  GET    /api/vendors/<id>             → get single vendor detail
  POST   /api/vendors                  → create vendor (admin only)
  PATCH  /api/vendors/<id>/status      → approve / suspend (admin only)
  PUT    /api/vendors/<id>             → update vendor profile (admin only)
  DELETE /api/vendors/<id>             → soft-delete / deactivate (admin only)
  GET    /api/vendors/me               → vendor sees their own profile (vendor role)
  PUT    /api/vendors/me               → vendor updates their own profile
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from app.extensions import db
from app.models.user import User
from app.models.vendor import VendorProfile
from app.utils.auth_helpers import roles_required
from app.models.activity_log import ActivityLog


vendors_bp = Blueprint("vendors", __name__, url_prefix="/api/vendors")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _vendor_dict(user, profile):
    """Serialize a vendor user + profile into a flat dict for the frontend."""
    return {
        "id":              user.id,
        "first_name":      user.first_name,
        "last_name":       user.last_name,
        "full_name":       f"{user.first_name} {user.last_name}",
        "email":           user.email,
        "phone":           user.phone,
        "company":         user.company,
        "avatar_url":      user.avatar_url,
        "is_active":       bool(user.is_active),
        "is_verified":     bool(user.is_verified),
        "created_at":      user.created_at.isoformat() if user.created_at else None,
        # vendor_profile fields (None-safe)
        "vendor_category": profile.vendor_category if profile else None,
        "gst_number":      profile.gst_number      if profile else None,
        "rating":          float(profile.rating)   if profile else 0.0,
        "total_orders":    profile.total_orders     if profile else 0,
        "status":          profile.status           if profile else "pending",
    }


def _log(user_id, action, entity_type="vendor", entity_id=None, description=None):
    """Helper to write an activity log entry."""
    try:
        log = ActivityLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:500],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


# ── GET /api/vendors/me  (vendor's own profile) ───────────────────────────────

@vendors_bp.route("/me", methods=["GET"])
@jwt_required()
def get_my_profile():
    """Vendor sees their own profile."""
    current_id = int(get_jwt_identity())
    user = User.query.get(current_id)

    if not user or user.role != "vendor":
        return jsonify({"error": "Not a vendor account"}), 403

    profile = VendorProfile.query.filter_by(user_id=user.id).first()
    return jsonify({"vendor": _vendor_dict(user, profile)}), 200


# ── PUT /api/vendors/me  (vendor updates own profile) ─────────────────────────

@vendors_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_my_profile():
    """Vendor updates their own contact & business info."""
    current_id = int(get_jwt_identity())
    user = User.query.get(current_id)

    if not user or user.role != "vendor":
        return jsonify({"error": "Not a vendor account"}), 403

    data = request.get_json(silent=True) or {}

    # Updatable user fields
    if "phone"   in data: user.phone   = data["phone"]
    if "company" in data: user.company = data["company"]

    # Updatable profile fields
    profile = VendorProfile.query.filter_by(user_id=user.id).first()
    if not profile:
        profile = VendorProfile(user_id=user.id)
        db.session.add(profile)

    if "vendor_category" in data: profile.vendor_category = data["vendor_category"]
    if "gst_number"      in data: profile.gst_number      = data["gst_number"]

    try:
        db.session.commit()
        _log(current_id, "vendor_profile_updated", entity_id=user.id,
             description=f"{user.company} updated their profile")
        return jsonify({"message": "Profile updated", "vendor": _vendor_dict(user, profile)}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"update_my_profile error: {e}")
        return jsonify({"error": "Failed to update profile"}), 500


# ── GET /api/vendors  (list all vendors) ─────────────────────────────────────

@vendors_bp.route("", methods=["GET"])
@jwt_required()
def list_vendors():
    """
    Returns all vendor users with their profile.
    Accessible by: admin, manager, procurement_officer
    Vendors are redirected by the frontend to /me.
    """
    current_id = int(get_jwt_identity())
    requester  = User.query.get(current_id)

    if not requester or requester.role not in ("admin", "manager", "procurement_officer"):
        return jsonify({"error": "Access denied"}), 403

    # Query params
    status_filter   = request.args.get("status",   "").strip()
    category_filter = request.args.get("category", "").strip()
    search          = request.args.get("q",        "").strip()
    page            = int(request.args.get("page",  1))
    per_page        = int(request.args.get("limit", 50))  # frontend paginates client-side

    # Base query — join vendor_profiles
    query = (
        db.session.query(User, VendorProfile)
        .outerjoin(VendorProfile, User.id == VendorProfile.user_id)
        .filter(User.role == "vendor", User.is_active == 1)
    )

    if status_filter:
        query = query.filter(VendorProfile.status == status_filter)

    if category_filter:
        query = query.filter(VendorProfile.vendor_category == category_filter)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                User.company.ilike(like),
                User.email.ilike(like),
                VendorProfile.vendor_category.ilike(like),
            )
        )

    total   = query.count()
    results = query.offset((page - 1) * per_page).limit(per_page).all()

    vendors_list = [_vendor_dict(u, p) for u, p in results]

    return jsonify({
        "vendors": vendors_list,
        "total":   total,
        "page":    page,
        "pages":   (total + per_page - 1) // per_page,
    }), 200


# ── GET /api/vendors/<id>  (single vendor detail) ─────────────────────────────

@vendors_bp.route("/<int:vendor_id>", methods=["GET"])
@jwt_required()
def get_vendor(vendor_id):
    current_id = int(get_jwt_identity())
    requester  = User.query.get(current_id)

    if not requester:
        return jsonify({"error": "Unauthorized"}), 401

    # Vendor can only fetch their own record
    if requester.role == "vendor" and requester.id != vendor_id:
        return jsonify({"error": "Access denied"}), 403

    user    = User.query.filter_by(id=vendor_id, role="vendor").first()
    if not user:
        return jsonify({"error": "Vendor not found"}), 404

    profile = VendorProfile.query.filter_by(user_id=vendor_id).first()
    return jsonify({"vendor": _vendor_dict(user, profile)}), 200


# ── POST /api/vendors  (admin creates vendor) ─────────────────────────────────

@vendors_bp.route("", methods=["POST"])
@jwt_required()
@roles_required("admin")
def create_vendor():
    """
    Admin creates a vendor account directly (bypasses normal registration flow).
    Expects JSON: first_name, last_name, email, company, password,
                  phone?, vendor_category?, gst_number?
    """
    data = request.get_json(silent=True) or {}
    current_id = int(get_jwt_identity())

    required = ["first_name", "last_name", "email", "company", "password"]
    missing  = [f for f in required if not data.get(f, "").strip()]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    if User.query.filter_by(email=data["email"].lower().strip()).first():
        return jsonify({"error": "Email already registered"}), 409

    from werkzeug.security import generate_password_hash
    new_user = User(
        first_name    = data["first_name"].strip(),
        last_name     = data["last_name"].strip(),
        email         = data["email"].lower().strip(),
        company       = data["company"].strip(),
        phone         = data.get("phone", "").strip() or None,
        role          = "vendor",
        password_hash = generate_password_hash(data["password"]),
        is_active     = 1,
        is_verified   = 1,   # admin-created accounts are auto-verified
    )
    db.session.add(new_user)
    db.session.flush()  # get new_user.id

    profile = VendorProfile(
        user_id         = new_user.id,
        vendor_category = data.get("vendor_category") or None,
        gst_number      = data.get("gst_number", "").strip() or None,
        status          = "approved",  # admin-created → auto-approved
        rating          = 0.00,
        total_orders    = 0,
    )
    db.session.add(profile)

    try:
        db.session.commit()
        _log(current_id, "vendor_created", entity_id=new_user.id,
             description=f"Admin created vendor: {new_user.company}")
        return jsonify({
            "message": "Vendor created successfully",
            "vendor":  _vendor_dict(new_user, profile),
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"create_vendor error: {e}")
        return jsonify({"error": "Failed to create vendor"}), 500


# ── PATCH /api/vendors/<id>/status  (approve / suspend) ──────────────────────

@vendors_bp.route("/<int:vendor_id>/status", methods=["PATCH"])
@jwt_required()
@roles_required("admin")
def change_vendor_status(vendor_id):
    """
    Admin approves, suspends or re-activates a vendor.
    Body: { "status": "approved" | "pending" | "suspended" }
    """
    data       = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip()
    current_id = int(get_jwt_identity())

    if new_status not in ("approved", "pending", "suspended"):
        return jsonify({"error": "Invalid status. Use: approved, pending, suspended"}), 400

    user = User.query.filter_by(id=vendor_id, role="vendor").first()
    if not user:
        return jsonify({"error": "Vendor not found"}), 404

    profile = VendorProfile.query.filter_by(user_id=vendor_id).first()
    if not profile:
        # Create profile if missing (edge case)
        profile = VendorProfile(user_id=vendor_id, status=new_status)
        db.session.add(profile)
    else:
        old_status     = profile.status
        profile.status = new_status

        # Deactivate user account on suspend
        if new_status == "suspended":
            user.is_active = 0
        elif new_status == "approved" and old_status == "suspended":
            user.is_active = 1

    try:
        db.session.commit()
        _log(current_id, f"vendor_{new_status}", entity_id=vendor_id,
             description=f"Vendor {user.company} status changed to {new_status}")
        return jsonify({
            "message": f"Vendor {new_status} successfully",
            "vendor":  _vendor_dict(user, profile),
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"change_vendor_status error: {e}")
        return jsonify({"error": "Failed to update status"}), 500


# ── PUT /api/vendors/<id>  (admin edits vendor details) ──────────────────────

@vendors_bp.route("/<int:vendor_id>", methods=["PUT"])
@jwt_required()
@roles_required("admin")
def update_vendor(vendor_id):
    """Admin updates any vendor field."""
    data       = request.get_json(silent=True) or {}
    current_id = int(get_jwt_identity())

    user = User.query.filter_by(id=vendor_id, role="vendor").first()
    if not user:
        return jsonify({"error": "Vendor not found"}), 404

    profile = VendorProfile.query.filter_by(user_id=vendor_id).first()
    if not profile:
        profile = VendorProfile(user_id=vendor_id)
        db.session.add(profile)

    # User fields
    for field in ("first_name", "last_name", "email", "phone", "company"):
        if field in data:
            setattr(user, field, data[field].strip())

    # Profile fields
    for field in ("vendor_category", "gst_number", "status"):
        if field in data:
            setattr(profile, field, data[field])

    try:
        db.session.commit()
        _log(current_id, "vendor_updated", entity_id=vendor_id,
             description=f"Admin updated vendor: {user.company}")
        return jsonify({"message": "Vendor updated", "vendor": _vendor_dict(user, profile)}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"update_vendor error: {e}")
        return jsonify({"error": "Failed to update vendor"}), 500


# ── DELETE /api/vendors/<id>  (soft-delete) ───────────────────────────────────

@vendors_bp.route("/<int:vendor_id>", methods=["DELETE"])
@jwt_required()
@roles_required("admin")
def delete_vendor(vendor_id):
    """Soft-delete: sets is_active = 0. Data is preserved."""
    current_id = int(get_jwt_identity())

    user = User.query.filter_by(id=vendor_id, role="vendor").first()
    if not user:
        return jsonify({"error": "Vendor not found"}), 404

    user.is_active = 0
    profile = VendorProfile.query.filter_by(user_id=vendor_id).first()
    if profile:
        profile.status = "suspended"

    try:
        db.session.commit()
        _log(current_id, "vendor_deleted", entity_id=vendor_id,
             description=f"Vendor {user.company} deactivated")
        return jsonify({"message": "Vendor deactivated"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"delete_vendor error: {e}")
        return jsonify({"error": "Failed to deactivate vendor"}), 500


# ── GET /api/vendors/stats  (dashboard counts) ────────────────────────────────

@vendors_bp.route("/stats", methods=["GET"])
@jwt_required()
def vendor_stats():
    """Quick stats for dashboard cards."""
    current_id = int(get_jwt_identity())
    requester  = User.query.get(current_id)

    if not requester or requester.role not in ("admin", "manager", "procurement_officer"):
        return jsonify({"error": "Access denied"}), 403

    total     = db.session.query(User).filter_by(role="vendor", is_active=1).count()
    approved  = db.session.query(VendorProfile).filter_by(status="approved").count()
    pending   = db.session.query(VendorProfile).filter_by(status="pending").count()
    suspended = db.session.query(VendorProfile).filter_by(status="suspended").count()

    return jsonify({
        "total":     total,
        "approved":  approved,
        "pending":   pending,
        "suspended": suspended,
    }), 200