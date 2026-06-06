# backend/app/routes/dashboard.py
# VendorBridge — Phase 3: Dashboard API
# Imports db from extensions (not from 'app') to avoid circular imports

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db              # ← fixed import
from datetime import datetime
from sqlalchemy import text

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


# ── Helper: current user ──────────────────────────────────────────
def current_user():
    from app.models.user import User       # local import — safe here
    uid = get_jwt_identity()
    return User.query.get(int(uid))


# ══════════════════════════════════════════════════════════════════
#  GET /api/dashboard/kpis
# ══════════════════════════════════════════════════════════════════
@dashboard_bp.route('/kpis', methods=['GET'])
@jwt_required()
def kpis():
    user = current_user()
    role = user.role if user else 'procurement_officer'

    try:
        po_count = db.session.execute(
            text("SELECT COUNT(*) FROM purchase_orders WHERE status IN ('approved','processing','sent')")
        ).scalar() or 0

        po_this_week = db.session.execute(
            text("""
                SELECT COUNT(*) FROM purchase_orders
                WHERE status IN ('approved','processing','sent')
                  AND created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            """)
        ).scalar() or 0

        vendor_count = db.session.execute(
            text("SELECT COUNT(*) FROM vendor_profiles WHERE status = 'approved'")
        ).scalar() or 0

        vendor_this_month = db.session.execute(
            text("""
                SELECT COUNT(*) FROM vendor_profiles
                WHERE status = 'approved'
                  AND created_at >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
            """)
        ).scalar() or 0

        if role in ('manager', 'admin'):
            approval_count = db.session.execute(
                text("SELECT COUNT(*) FROM approvals WHERE status = 'pending'")
            ).scalar() or 0
        else:
            approval_count = db.session.execute(
                text("""
                    SELECT COUNT(*) FROM approvals a
                    JOIN rfqs r ON a.rfq_id = r.id
                    WHERE a.status = 'pending' AND r.created_by = :uid
                """),
                {'uid': user.id}
            ).scalar() or 0

        monthly_spend = db.session.execute(
            text("""
                SELECT COALESCE(SUM(total_amount), 0) FROM purchase_orders
                WHERE status IN ('approved','paid','sent')
                  AND MONTH(created_at) = MONTH(CURDATE())
                  AND YEAR(created_at)  = YEAR(CURDATE())
            """)
        ).scalar() or 0

        last_month_spend = db.session.execute(
            text("""
                SELECT COALESCE(SUM(total_amount), 0) FROM purchase_orders
                WHERE status IN ('approved','paid','sent')
                  AND MONTH(created_at) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
                  AND YEAR(created_at)  = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
            """)
        ).scalar() or 0

        spend_change_pct = 0
        if last_month_spend > 0:
            spend_change_pct = round(((monthly_spend - last_month_spend) / last_month_spend) * 100, 1)

        return jsonify({
            'kpis': {
                'active_pos':        int(po_count),
                'active_pos_change': f'+{po_this_week} this week',
                'active_pos_trend':  'up' if po_this_week >= 0 else 'down',
                'approved_vendors':  int(vendor_count),
                'vendors_change':    f'+{vendor_this_month} this month',
                'vendors_trend':     'up' if vendor_this_month >= 0 else 'neu',
                'pending_approvals': int(approval_count),
                'approvals_change':  'awaiting action',
                'approvals_trend':   'neu' if approval_count == 0 else 'up',
                'monthly_spend':     float(monthly_spend),
                'spend_change':      f'{spend_change_pct:+.1f}% vs last month',
                'spend_trend':       'up' if spend_change_pct >= 0 else 'down',
            }
        }), 200

    except Exception as e:
        return jsonify({
            'kpis': {
                'active_pos': 0,        'active_pos_change': '—', 'active_pos_trend': 'neu',
                'approved_vendors': 0,  'vendors_change': '—',    'vendors_trend': 'neu',
                'pending_approvals': 0, 'approvals_change': '—',  'approvals_trend': 'neu',
                'monthly_spend': 0,     'spend_change': '—',      'spend_trend': 'neu',
            },
            'warning': str(e)
        }), 200


# ══════════════════════════════════════════════════════════════════
#  GET /api/dashboard/recent-pos
# ══════════════════════════════════════════════════════════════════
@dashboard_bp.route('/recent-pos', methods=['GET'])
@jwt_required()
def recent_pos():
    user = current_user()
    role = user.role if user else 'procurement_officer'

    try:
        if role == 'vendor':
            vp = db.session.execute(
                text("SELECT id FROM vendor_profiles WHERE user_id = :uid"),
                {'uid': user.id}
            ).fetchone()
            if not vp:
                return jsonify({'purchase_orders': []}), 200
            rows = db.session.execute(text("""
                SELECT po.po_number, :vname AS vendor_name,
                       po.total_amount, po.created_at, po.status
                FROM purchase_orders po
                WHERE po.vendor_id = :vid
                ORDER BY po.created_at DESC LIMIT 5
            """), {'vid': vp[0], 'vname': user.company}).mappings().all()
        else:
            rows = db.session.execute(text("""
                SELECT po.po_number, u.company AS vendor_name,
                       po.total_amount, po.created_at, po.status
                FROM purchase_orders po
                JOIN vendor_profiles vp ON po.vendor_id = vp.id
                JOIN users u ON vp.user_id = u.id
                ORDER BY po.created_at DESC LIMIT 5
            """)).mappings().all()

        pos = [{
            'po_number':   r['po_number'],
            'vendor_name': r['vendor_name'],
            'total_amount': float(r['total_amount']),
            'created_at':  r['created_at'].isoformat() if hasattr(r['created_at'], 'isoformat') else str(r['created_at']),
            'status':      r['status'],
        } for r in rows]

        return jsonify({'purchase_orders': pos}), 200

    except Exception as e:
        return jsonify({'purchase_orders': [], 'warning': str(e)}), 200


# ══════════════════════════════════════════════════════════════════
#  GET /api/dashboard/pending-approvals
# ══════════════════════════════════════════════════════════════════
@dashboard_bp.route('/pending-approvals', methods=['GET'])
@jwt_required()
def pending_approvals():
    user = current_user()
    role = user.role if user else 'procurement_officer'

    try:
        params = {} if role in ('manager', 'admin') else {'uid': user.id}
        where  = "" if role in ('manager', 'admin') else "AND r.created_by = :uid"

        rows = db.session.execute(text(f"""
            SELECT a.id,
                   CONCAT('RFQ-', LPAD(r.id,4,'0'), ' — ', r.title) AS title,
                   'RFQ' AS type,
                   CONCAT(u.first_name,' ',u.last_name) AS submitted_by,
                   a.created_at
            FROM approvals a
            JOIN rfqs r ON a.rfq_id = r.id
            JOIN users u ON r.created_by = u.id
            WHERE a.status = 'pending' {where}
            ORDER BY a.created_at DESC LIMIT 5
        """), params).mappings().all()

        now = datetime.utcnow()
        approvals = []
        for r in rows:
            delta = now - r['created_at'].replace(tzinfo=None)
            h = int(delta.total_seconds() / 3600)
            approvals.append({
                'id':           r['id'],
                'title':        r['title'],
                'type':         r['type'],
                'submitted_by': r['submitted_by'],
                'time':         f'{h}h ago' if h < 24 else f'{h//24}d ago',
            })

        return jsonify({'approvals': approvals}), 200

    except Exception as e:
        return jsonify({'approvals': [], 'warning': str(e)}), 200


# ══════════════════════════════════════════════════════════════════
#  GET /api/dashboard/active-rfqs
# ══════════════════════════════════════════════════════════════════
@dashboard_bp.route('/active-rfqs', methods=['GET'])
@jwt_required()
def active_rfqs():
    user = current_user()
    role = user.role if user else 'procurement_officer'

    try:
        if role == 'vendor':
            rows = db.session.execute(text("""
                SELECT r.id, r.title, r.status, r.deadline, COUNT(q.id) AS quotes
                FROM rfqs r
                LEFT JOIN quotations q ON q.rfq_id = r.id
                JOIN rfq_vendors rv ON rv.rfq_id = r.id
                JOIN vendor_profiles vp ON vp.id = rv.vendor_id AND vp.user_id = :uid
                WHERE r.status IN ('open','closing','draft')
                GROUP BY r.id ORDER BY r.created_at DESC LIMIT 5
            """), {'uid': user.id}).mappings().all()
        else:
            rows = db.session.execute(text("""
                SELECT r.id, r.title, r.status, r.deadline, COUNT(q.id) AS quotes
                FROM rfqs r
                LEFT JOIN quotations q ON q.rfq_id = r.id
                WHERE r.status IN ('open','closing','draft')
                GROUP BY r.id ORDER BY r.created_at DESC LIMIT 5
            """)).mappings().all()

        rfqs = [{
            'id':       r['id'],
            'title':    r['title'],
            'status':   r['status'],
            'deadline': r['deadline'].strftime('%b %d, %Y') if hasattr(r['deadline'], 'strftime') else str(r['deadline']),
            'quotes':   int(r['quotes']),
        } for r in rows]

        return jsonify({'rfqs': rfqs}), 200

    except Exception as e:
        return jsonify({'rfqs': [], 'warning': str(e)}), 200


# ══════════════════════════════════════════════════════════════════
#  POST /api/dashboard/approvals/<id>/<action>
# ══════════════════════════════════════════════════════════════════
@dashboard_bp.route('/approvals/<int:approval_id>/<action>', methods=['POST'])
@jwt_required()
def quick_approval(approval_id, action):
    if action not in ('approve', 'reject'):
        return jsonify({'error': 'Invalid action'}), 400

    user = current_user()
    if user.role not in ('manager', 'admin'):
        return jsonify({'error': 'Insufficient permissions'}), 403

    try:
        status = 'approved' if action == 'approve' else 'rejected'
        db.session.execute(
            text("UPDATE approvals SET status=:s, reviewed_by=:uid, reviewed_at=NOW() WHERE id=:id"),
            {'s': status, 'uid': user.id, 'id': approval_id}
        )
        db.session.commit()
        return jsonify({'message': f'Approval {status}'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500