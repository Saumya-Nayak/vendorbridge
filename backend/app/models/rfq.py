"""
VendorBridge — RFQ Model + RFQVendor join table
Phase 3
"""

from app.extensions import db
from datetime import datetime


class RFQ(db.Model):
    __tablename__ = "rfqs"

    id          = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    title       = db.Column(db.String(255),   nullable=False)
    description = db.Column(db.Text,          nullable=True)
    category    = db.Column(db.String(100),   nullable=True)
    budget      = db.Column(db.Numeric(14,2), nullable=True)
    deadline    = db.Column(db.DateTime,      nullable=True)
    status      = db.Column(
        db.Enum("draft", "open", "closed", "awarded", name="rfq_status"),
        nullable=False,
        default="draft",
    )
    created_by  = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator     = db.relationship("User",      foreign_keys=[created_by], backref=db.backref("rfqs", lazy="dynamic"))
    rfq_vendors = db.relationship("RFQVendor", backref="rfq", lazy="joined", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RFQ id={self.id} title={self.title!r} status={self.status}>"


class RFQVendor(db.Model):
    """Join table — which vendors are invited to which RFQ."""
    __tablename__ = "rfq_vendors"
    __table_args__ = (
        db.UniqueConstraint("rfq_id", "vendor_id", name="uq_rfq_vendor"),
    )

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rfq_id     = db.Column(db.Integer, db.ForeignKey("rfqs.id",  ondelete="CASCADE"), nullable=False)
    vendor_id  = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    has_quoted = db.Column(db.Boolean, default=False, nullable=False)  # updated in Phase 4
    invited_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationship to vendor user
    vendor = db.relationship("User", foreign_keys=[vendor_id], lazy="joined")

    def __repr__(self):
        return f"<RFQVendor rfq={self.rfq_id} vendor={self.vendor_id}>"