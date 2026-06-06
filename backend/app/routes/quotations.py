from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.extensions import db
from app.models.user import User
from app.models.rfq import RFQ, RFQVendor
from app.models.quotation import Quotation
from app.models.activity_log import ActivityLog

quotations_bp = Blueprint("quotations", __name__, url_prefix="/api/quotations")


def _log(user_id, action, entity_id=None, description=None):
    try:
        log = ActivityLog(
            user_id=user_id, action=action, entity_type="quotation",
            entity_id=entity_id, description=description,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:500],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


def _quote_dict(q: Quotation) -> dict:
    return {
        "id":              q.id,
        "rfq_id":          q.rfq_id,
        "rfq_title":       q.rfq.title if q.rfq else "—",
        "vendor_id":       q.vendor_id,
        "vendor_company":  q.vendor.company    if q.vendor else "—",
        "vendor_email":    q.vendor.email      if q.vendor else "—",
        "amount":          float(q.amount),
        "notes":           q.notes,
        "attachments_url": q.attachments_url,
        "status":          q.status,
        "submitted_at":    q.submitted_at.isoformat() if q.submitted_at else None,
        "updated_at":      q.updated_at.isoformat()   if q.updated_at   else None,
    }


def _requester():
    return User.query.get(int(get_jwt_identity()))


@quotations_bp.route("", methods=["GET"])
@jwt_required()
def list_quotations():
    user = _requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    rfq_id   = request.args.get("rfq_id",  type=int)
    status_f = request.args.get("status",  "").strip()
    page     = int(request.args.get("page",  1))
    per_page = int(request.args.get("limit", 50))

    if user.role == "vendor":
        query = Quotation.query.filter_by(vendor_id=user.id)
    elif user.role == "procurement_officer":
        owned_rfq_ids = [r.id for r in RFQ.query.filter_by(created_by=user.id).all()]
        query = Quotation.query.filter(Quotation.rfq_id.in_(owned_rfq_ids))
    else:
        query = Quotation.query

    if rfq_id:
        query = query.filter_by(rfq_id=rfq_id)
    if status_f:
        query = query.filter_by(status=status_f)

    total   = query.count()
    results = query.order_by(Quotation.submitted_at.desc()).offset((page-1)*per_page).limit(per_page).all()

    return jsonify({
        "quotations": [_quote_dict(q) for q in results],
        "total": total,
        "page":  page,
        "pages": (total + per_page - 1) // per_page,
    }), 200


@quotations_bp.route("/<int:qid>", methods=["GET"])
@jwt_required()
def get_quotation(qid):
    user = _requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    q = Quotation.query.get(qid)
    if not q:
        return jsonify({"error": "Quotation not found"}), 404

    if user.role == "vendor" and q.vendor_id != user.id:
        return jsonify({"error": "Access denied"}), 403

    if user.role == "procurement_officer":
        rfq = RFQ.query.get(q.rfq_id)
        if rfq and rfq.created_by != user.id:
            return jsonify({"error": "Access denied"}), 403

    return jsonify({"quotation": _quote_dict(q)}), 200


@quotations_bp.route("", methods=["POST"])
@jwt_required()
def submit_quotation():
    user = _requester()
    if not user or user.role != "vendor":
        return jsonify({"error": "Only vendors can submit quotations"}), 403

    data = request.get_json(silent=True) or {}

    rfq_id = data.get("rfq_id")
    amount = data.get("amount")

    if not rfq_id or amount is None:
        return jsonify({"error": "rfq_id and amount are required"}), 400

    rfq = RFQ.query.get(rfq_id)
    if not rfq:
        return jsonify({"error": "RFQ not found"}), 404
    if rfq.status != "open":
        return jsonify({"error": "RFQ is not open for quotations"}), 400

    invited = RFQVendor.query.filter_by(rfq_id=rfq_id, vendor_id=user.id).first()
    if not invited:
        return jsonify({"error": "You are not invited to this RFQ"}), 403

    existing = Quotation.query.filter_by(rfq_id=rfq_id, vendor_id=user.id).first()
    if existing:
        return jsonify({"error": "You have already submitted a quotation for this RFQ"}), 409

    try:
        amount_val = float(amount)
        if amount_val <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Amount must be a positive number"}), 400

    q = Quotation(
        rfq_id          = rfq_id,
        vendor_id       = user.id,
        amount          = amount_val,
        notes           = data.get("notes", "").strip() or None,
        attachments_url = data.get("attachments_url", "").strip() or None,
        status          = "submitted",
    )
    db.session.add(q)

    invited.has_quoted = True

    try:
        db.session.commit()
        _log(user.id, "quotation_submitted", entity_id=q.id,
             description=f"Vendor {user.company} quoted ₹{amount_val} on RFQ {rfq.title}")
        return jsonify({"message": "Quotation submitted", "quotation": _quote_dict(q)}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"submit_quotation error: {e}")
        return jsonify({"error": "Failed to submit quotation"}), 500


@quotations_bp.route("/<int:qid>", methods=["PUT"])
@jwt_required()
def update_quotation(qid):
    user = _requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    q = Quotation.query.get(qid)
    if not q:
        return jsonify({"error": "Quotation not found"}), 404

    if user.role == "vendor":
        if q.vendor_id != user.id:
            return jsonify({"error": "Access denied"}), 403
        if q.status != "submitted":
            return jsonify({"error": "Cannot edit a quotation that is under review or decided"}), 400
    elif user.role not in ("admin",):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json(silent=True) or {}

    if "amount" in data:
        try:
            v = float(data["amount"])
            if v <= 0: raise ValueError
            q.amount = v
        except (TypeError, ValueError):
            return jsonify({"error": "Amount must be a positive number"}), 400

    if "notes"           in data: q.notes           = data["notes"]
    if "attachments_url" in data: q.attachments_url = data["attachments_url"]

    try:
        db.session.commit()
        _log(user.id, "quotation_updated", entity_id=qid)
        return jsonify({"message": "Quotation updated", "quotation": _quote_dict(q)}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"update_quotation error: {e}")
        return jsonify({"error": "Failed to update quotation"}), 500


@quotations_bp.route("/<int:qid>/status", methods=["PATCH"])
@jwt_required()
def change_quotation_status(qid):
    user = _requester()
    if not user or user.role not in ("admin", "procurement_officer", "manager"):
        return jsonify({"error": "Access denied"}), 403

    q = Quotation.query.get(qid)
    if not q:
        return jsonify({"error": "Quotation not found"}), 404

    if user.role == "procurement_officer":
        rfq = RFQ.query.get(q.rfq_id)
        if rfq and rfq.created_by != user.id:
            return jsonify({"error": "Access denied"}), 403

    data       = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip()

    if new_status not in ("submitted", "under_review", "accepted", "rejected"):
        return jsonify({"error": "Invalid status"}), 400

    q.status = new_status

    if new_status == "accepted":
        siblings = Quotation.query.filter(
            Quotation.rfq_id == q.rfq_id,
            Quotation.id     != q.id,
            Quotation.status == "submitted",
        ).all()
        for s in siblings:
            s.status = "rejected"

        rfq = RFQ.query.get(q.rfq_id)
        if rfq:
            rfq.status = "awarded"

    try:
        db.session.commit()
        _log(user.id, f"quotation_{new_status}", entity_id=qid,
             description=f"Quotation {qid} marked {new_status} by {user.email}")
        return jsonify({"message": f"Quotation {new_status}", "quotation": _quote_dict(q)}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"change_quotation_status error: {e}")
        return jsonify({"error": "Failed to update status"}), 500


@quotations_bp.route("/<int:qid>", methods=["DELETE"])
@jwt_required()
def delete_quotation(qid):
    user = _requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    q = Quotation.query.get(qid)
    if not q:
        return jsonify({"error": "Quotation not found"}), 404

    if user.role == "vendor":
        if q.vendor_id != user.id:
            return jsonify({"error": "Access denied"}), 403
        if q.status != "submitted":
            return jsonify({"error": "Cannot withdraw a quotation under review or decided"}), 400

    elif user.role not in ("admin",):
        return jsonify({"error": "Access denied"}), 403

    rv = RFQVendor.query.filter_by(rfq_id=q.rfq_id, vendor_id=q.vendor_id).first()
    if rv:
        rv.has_quoted = False

    try:
        db.session.delete(q)
        db.session.commit()
        _log(user.id, "quotation_deleted", entity_id=qid)
        return jsonify({"message": "Quotation withdrawn"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"delete_quotation error: {e}")
        return jsonify({"error": "Failed to delete quotation"}), 500


@quotations_bp.route("/stats", methods=["GET"])
@jwt_required()
def quotation_stats():
    user = _requester()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    if user.role == "vendor":
        base = Quotation.query.filter_by(vendor_id=user.id)
    elif user.role == "procurement_officer":
        ids  = [r.id for r in RFQ.query.filter_by(created_by=user.id).all()]
        base = Quotation.query.filter(Quotation.rfq_id.in_(ids))
    else:
        base = Quotation.query

    return jsonify({
        "total":        base.count(),
        "submitted":    base.filter(Quotation.status == "submitted").count(),
        "under_review": base.filter(Quotation.status == "under_review").count(),
        "accepted":     base.filter(Quotation.status == "accepted").count(),
        "rejected":     base.filter(Quotation.status == "rejected").count(),
    }), 200