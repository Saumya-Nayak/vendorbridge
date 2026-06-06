"""
VendorBridge — RFQ (Request for Quotation) Route
Phase 3

Endpoints:
  GET    /api/rfqs                    → list RFQs (role-filtered)
  GET    /api/rfqs/<id>               → single RFQ detail
  POST   /api/rfqs                    → create RFQ (procurement_officer, admin)
  PUT    /api/rfqs/<id>               → update RFQ (owner or admin, draft only)
  PATCH  /api/rfqs/<id>/status        → change status (open/closed/awarded)
  DELETE /api/rfqs/<id>               → delete RFQ (draft only, owner/admin)
  POST   /api/rfqs/<id>/invite        → invite vendors to RFQ (owner/admin)
  DELETE /api/rfqs/<id>/invite/<vid>  → remove vendor invite (owner/admin)
  GET    /api/rfqs/<id>/vendors       → list invited vendors for an RFQ
  GET    /api/rfqs/stats              → quick counts for dashboard

Role rules:
  admin              → full access to everything
  manager            → read-only on all RFQs
  procurement_officer → create/edit/delete their OWN RFQs; see all open RFQs
  vendor             → see ONLY RFQs they are explicitly invited to
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.extensions import db
from app.models.user import User
from app.models.rfq import RFQ, RFQVendor
from app.models.activity_log import ActivityLog
from app.utils.auth_helpers import role_required

rfqs_bp = Blueprint("rfqs", __name__, url_prefix="/api/rfqs")


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _log(user_id, action, entity_id=None, description=None):
    try:
        log = ActivityLog(
            user_id=user_id,
            action=action,
            entity_type="rfq",
            entity_id=entity_id,
            description=description,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:500],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


def _rfq_dict(rfq: "RFQ", include_vendors: bool = False) -> dict:
    """Serialize an RFQ row. Optionally embed invited vendor list."""
    data = {
        "id":           rfq.id,
        "title":        rfq.title,
        "description":  rfq.description,
        "category":     rfq.category,
        "budget":       float(rfq.budget) if rfq.budget else None,
        "deadline":     rfq.deadline.isoformat() if rfq.deadline else None,
        "status":       rfq.status,
        "created_by":   rfq.created_by,
        "creator_name": (
            f"{rfq.creator.first_name} {rfq.creator.last_name}"
            if rfq.creator else "—"
        ),
        "creator_company": rfq.creator.company if rfq.creator else "—",
        "created_at":   rfq.created_at.isoformat() if rfq.created_at else None,
        "updated_at":   rfq.updated_at.isoformat() if rfq.updated_at else None,
        "vendor_count": len(rfq.rfq_vendors),
        "quote_count":  0,   # Phase 4 will fill this
    }
    if include_vendors:
        data["vendors"] = [
            {
                "vendor_id":   rv.vendor_id,
                "company":     rv.vendor.company if rv.vendor else "—",
                "email":       rv.vendor.email   if rv.vendor else "—",
                "invited_at":  rv.invited_at.isoformat() if rv.invited_at else None,
                "has_quoted":  rv.has_quoted,
            }
            for rv in rfq.rfq_vendors
        ]
    return data


def _get_requester() -> "User | None":
    uid = int(get_jwt_identity())
    return User.query.get(uid)


# ─────────────────────────────────────────────────────────────────
# GET /api/rfqs/stats
# ─────────────────────────────────────────────────────────────────

@rfqs_bp.route("/stats", methods=["GET"])
@jwt_required()
def rfq_stats():
    user = _get_requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    if user.role == "vendor":
        # Stats scoped to vendor's invitations
        invited_rfq_ids = [
            rv.rfq_id
            for rv in RFQVendor.query.filter_by(vendor_id=user.id).all()
        ]
        base = RFQ.query.filter(RFQ.id.in_(invited_rfq_ids))
    elif user.role == "procurement_officer":
        base = RFQ.query.filter_by(created_by=user.id)
    else:
        base = RFQ.query

    return jsonify({
        "total":   base.count(),
        "draft":   base.filter(RFQ.status == "draft").count(),
        "open":    base.filter(RFQ.status == "open").count(),
        "closed":  base.filter(RFQ.status == "closed").count(),
        "awarded": base.filter(RFQ.status == "awarded").count(),
    }), 200


# ─────────────────────────────────────────────────────────────────
# GET /api/rfqs  — list
# ─────────────────────────────────────────────────────────────────

@rfqs_bp.route("", methods=["GET"])
@jwt_required()
def list_rfqs():
    user = _get_requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    status_filter   = request.args.get("status",   "").strip()
    category_filter = request.args.get("category", "").strip()
    search          = request.args.get("q",        "").strip()
    page            = int(request.args.get("page",  1))
    per_page        = int(request.args.get("limit", 50))

    # Role-scoped base query
    if user.role == "vendor":
        # Vendor only sees RFQs they were invited to
        invited_ids = [
            rv.rfq_id
            for rv in RFQVendor.query.filter_by(vendor_id=user.id).all()
        ]
        query = RFQ.query.filter(RFQ.id.in_(invited_ids))
    elif user.role == "procurement_officer":
        # PO sees their own + all open RFQs from others
        query = RFQ.query.filter(
            db.or_(RFQ.created_by == user.id, RFQ.status == "open")
        )
    else:
        # admin / manager → all
        query = RFQ.query

    # Filters
    if status_filter:
        query = query.filter(RFQ.status == status_filter)
    if category_filter:
        query = query.filter(RFQ.category == category_filter)
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                RFQ.title.ilike(like),
                RFQ.description.ilike(like),
                RFQ.category.ilike(like),
            )
        )

    total   = query.count()
    results = (
        query.order_by(RFQ.created_at.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
             .all()
    )

    return jsonify({
        "rfqs":  [_rfq_dict(r) for r in results],
        "total": total,
        "page":  page,
        "pages": (total + per_page - 1) // per_page,
    }), 200


# ─────────────────────────────────────────────────────────────────
# GET /api/rfqs/<id>  — detail
# ─────────────────────────────────────────────────────────────────

@rfqs_bp.route("/<int:rfq_id>", methods=["GET"])
@jwt_required()
def get_rfq(rfq_id):
    user = _get_requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    rfq = RFQ.query.get(rfq_id)
    if not rfq:
        return jsonify({"error": "RFQ not found"}), 404

    # Vendor access check
    if user.role == "vendor":
        invited = RFQVendor.query.filter_by(rfq_id=rfq_id, vendor_id=user.id).first()
        if not invited:
            return jsonify({"error": "Access denied"}), 403

    return jsonify({"rfq": _rfq_dict(rfq, include_vendors=True)}), 200


# ─────────────────────────────────────────────────────────────────
# POST /api/rfqs  — create
# ─────────────────────────────────────────────────────────────────

@rfqs_bp.route("", methods=["POST"])
@jwt_required()
def create_rfq():
    user = _get_requester()
    if not user or user.role not in ("procurement_officer", "admin"):
        return jsonify({"error": "Only procurement officers and admins can create RFQs"}), 403

    data = request.get_json(silent=True) or {}

    if not data.get("title", "").strip():
        return jsonify({"error": "Title is required"}), 400

    deadline = None
    if data.get("deadline"):
        try:
            deadline = datetime.fromisoformat(data["deadline"])
        except ValueError:
            return jsonify({"error": "Invalid deadline format. Use ISO 8601."}), 400

    rfq = RFQ(
        title       = data["title"].strip(),
        description = data.get("description", "").strip() or None,
        category    = data.get("category", "").strip() or None,
        budget      = data.get("budget") or None,
        deadline    = deadline,
        status      = data.get("status", "draft"),  # draft | open
        created_by  = user.id,
    )
    db.session.add(rfq)

    try:
        db.session.flush()  # get rfq.id

        # Optionally invite vendors at creation time
        vendor_ids = data.get("vendor_ids", [])
        for vid in vendor_ids:
            vendor = User.query.filter_by(id=vid, role="vendor").first()
            if vendor:
                rv = RFQVendor(rfq_id=rfq.id, vendor_id=vid)
                db.session.add(rv)

        db.session.commit()
        _log(user.id, "rfq_created", entity_id=rfq.id,
             description=f"RFQ created: {rfq.title}")
        return jsonify({"message": "RFQ created", "rfq": _rfq_dict(rfq, include_vendors=True)}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"create_rfq error: {e}")
        return jsonify({"error": "Failed to create RFQ"}), 500


# ─────────────────────────────────────────────────────────────────
# PUT /api/rfqs/<id>  — update
# ─────────────────────────────────────────────────────────────────

@rfqs_bp.route("/<int:rfq_id>", methods=["PUT"])
@jwt_required()
def update_rfq(rfq_id):
    user = _get_requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    rfq = RFQ.query.get(rfq_id)
    if not rfq:
        return jsonify({"error": "RFQ not found"}), 404

    # Permission: owner or admin
    if user.role != "admin" and rfq.created_by != user.id:
        return jsonify({"error": "Access denied"}), 403

    # Can only edit draft RFQs (admin can edit any)
    if user.role != "admin" and rfq.status != "draft":
        return jsonify({"error": "Only draft RFQs can be edited"}), 400

    data = request.get_json(silent=True) or {}

    if "title"       in data: rfq.title       = data["title"].strip()
    if "description" in data: rfq.description = data["description"].strip()
    if "category"    in data: rfq.category    = data["category"].strip()
    if "budget"      in data: rfq.budget      = data["budget"]
    if "deadline"    in data:
        try:
            rfq.deadline = datetime.fromisoformat(data["deadline"]) if data["deadline"] else None
        except ValueError:
            return jsonify({"error": "Invalid deadline format"}), 400

    try:
        db.session.commit()
        _log(user.id, "rfq_updated", entity_id=rfq.id,
             description=f"RFQ updated: {rfq.title}")
        return jsonify({"message": "RFQ updated", "rfq": _rfq_dict(rfq, include_vendors=True)}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"update_rfq error: {e}")
        return jsonify({"error": "Failed to update RFQ"}), 500


# ─────────────────────────────────────────────────────────────────
# PATCH /api/rfqs/<id>/status  — open / close / award
# ─────────────────────────────────────────────────────────────────

@rfqs_bp.route("/<int:rfq_id>/status", methods=["PATCH"])
@jwt_required()
def change_rfq_status(rfq_id):
    user = _get_requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    rfq = RFQ.query.get(rfq_id)
    if not rfq:
        return jsonify({"error": "RFQ not found"}), 404

    if user.role not in ("admin", "procurement_officer") and rfq.created_by != user.id:
        return jsonify({"error": "Access denied"}), 403

    data       = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip()

    valid = ("draft", "open", "closed", "awarded")
    if new_status not in valid:
        return jsonify({"error": f"Invalid status. Use: {', '.join(valid)}"}), 400

    rfq.status = new_status
    try:
        db.session.commit()
        _log(user.id, f"rfq_{new_status}", entity_id=rfq.id,
             description=f"RFQ '{rfq.title}' marked as {new_status}")
        return jsonify({"message": f"RFQ status changed to {new_status}",
                        "rfq": _rfq_dict(rfq)}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"change_rfq_status error: {e}")
        return jsonify({"error": "Failed to update status"}), 500


# ─────────────────────────────────────────────────────────────────
# DELETE /api/rfqs/<id>  — soft delete (draft only)
# ─────────────────────────────────────────────────────────────────

@rfqs_bp.route("/<int:rfq_id>", methods=["DELETE"])
@jwt_required()
def delete_rfq(rfq_id):
    user = _get_requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    rfq = RFQ.query.get(rfq_id)
    if not rfq:
        return jsonify({"error": "RFQ not found"}), 404

    if user.role != "admin" and rfq.created_by != user.id:
        return jsonify({"error": "Access denied"}), 403

    if user.role != "admin" and rfq.status != "draft":
        return jsonify({"error": "Only draft RFQs can be deleted"}), 400

    try:
        db.session.delete(rfq)
        db.session.commit()
        _log(user.id, "rfq_deleted", entity_id=rfq_id,
             description=f"RFQ deleted: {rfq.title}")
        return jsonify({"message": "RFQ deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"delete_rfq error: {e}")
        return jsonify({"error": "Failed to delete RFQ"}), 500


# ─────────────────────────────────────────────────────────────────
# POST /api/rfqs/<id>/invite  — invite vendors
# ─────────────────────────────────────────────────────────────────

@rfqs_bp.route("/<int:rfq_id>/invite", methods=["POST"])
@jwt_required()
def invite_vendors(rfq_id):
    user = _get_requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    rfq = RFQ.query.get(rfq_id)
    if not rfq:
        return jsonify({"error": "RFQ not found"}), 404

    if user.role not in ("admin",) and rfq.created_by != user.id:
        return jsonify({"error": "Access denied"}), 403

    data       = request.get_json(silent=True) or {}
    vendor_ids = data.get("vendor_ids", [])
    if not vendor_ids:
        return jsonify({"error": "vendor_ids list is required"}), 400

    added = []
    for vid in vendor_ids:
        vendor = User.query.filter_by(id=vid, role="vendor").first()
        if not vendor:
            continue
        existing = RFQVendor.query.filter_by(rfq_id=rfq_id, vendor_id=vid).first()
        if not existing:
            rv = RFQVendor(rfq_id=rfq_id, vendor_id=vid)
            db.session.add(rv)
            added.append(vid)

    try:
        db.session.commit()
        _log(user.id, "rfq_vendors_invited", entity_id=rfq_id,
             description=f"Invited vendor IDs: {added} to RFQ {rfq.title}")
        return jsonify({"message": f"{len(added)} vendor(s) invited",
                        "added_ids": added}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"invite_vendors error: {e}")
        return jsonify({"error": "Failed to invite vendors"}), 500


# ─────────────────────────────────────────────────────────────────
# DELETE /api/rfqs/<id>/invite/<vendor_id>  — remove invite
# ─────────────────────────────────────────────────────────────────

@rfqs_bp.route("/<int:rfq_id>/invite/<int:vendor_id>", methods=["DELETE"])
@jwt_required()
def remove_vendor_invite(rfq_id, vendor_id):
    user = _get_requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    rfq = RFQ.query.get(rfq_id)
    if not rfq:
        return jsonify({"error": "RFQ not found"}), 404

    if user.role not in ("admin",) and rfq.created_by != user.id:
        return jsonify({"error": "Access denied"}), 403

    rv = RFQVendor.query.filter_by(rfq_id=rfq_id, vendor_id=vendor_id).first()
    if not rv:
        return jsonify({"error": "Vendor not invited"}), 404

    try:
        db.session.delete(rv)
        db.session.commit()
        _log(user.id, "rfq_vendor_removed", entity_id=rfq_id,
             description=f"Vendor {vendor_id} removed from RFQ {rfq_id}")
        return jsonify({"message": "Vendor invite removed"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"remove_vendor_invite error: {e}")
        return jsonify({"error": "Failed to remove vendor"}), 500


# ─────────────────────────────────────────────────────────────────
# GET /api/rfqs/<id>/vendors  — list invited vendors
# ─────────────────────────────────────────────────────────────────

@rfqs_bp.route("/<int:rfq_id>/vendors", methods=["GET"])
@jwt_required()
def list_rfq_vendors(rfq_id):
    user = _get_requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    rfq = RFQ.query.get(rfq_id)
    if not rfq:
        return jsonify({"error": "RFQ not found"}), 404

    if user.role == "vendor":
        invited = RFQVendor.query.filter_by(rfq_id=rfq_id, vendor_id=user.id).first()
        if not invited:
            return jsonify({"error": "Access denied"}), 403

    vendors = [
        {
            "vendor_id":  rv.vendor_id,
            "company":    rv.vendor.company    if rv.vendor else "—",
            "email":      rv.vendor.email      if rv.vendor else "—",
            "phone":      rv.vendor.phone      if rv.vendor else None,
            "invited_at": rv.invited_at.isoformat() if rv.invited_at else None,
            "has_quoted": rv.has_quoted,
        }
        for rv in rfq.rfq_vendors
    ]

    return jsonify({"vendors": vendors, "total": len(vendors)}), 200