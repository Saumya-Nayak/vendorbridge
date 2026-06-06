from app.extensions import db
from datetime import datetime


class Quotation(db.Model):
    __tablename__ = "quotations"
    __table_args__ = (
        db.UniqueConstraint("rfq_id", "vendor_id", name="uq_quotation_rfq_vendor"),
    )

    id              = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    rfq_id          = db.Column(db.Integer,       db.ForeignKey("rfqs.id",  ondelete="CASCADE"), nullable=False)
    vendor_id       = db.Column(db.Integer,       db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount          = db.Column(db.Numeric(14,2),  nullable=False)
    notes           = db.Column(db.Text,           nullable=True)
    attachments_url = db.Column(db.String(500),    nullable=True)
    status          = db.Column(
        db.Enum("submitted", "under_review", "accepted", "rejected", name="quotation_status"),
        nullable=False,
        default="submitted",
    )
    submitted_at    = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    rfq    = db.relationship("RFQ",  foreign_keys=[rfq_id],    backref=db.backref("quotations", lazy="dynamic"))
    vendor = db.relationship("User", foreign_keys=[vendor_id], lazy="joined")

    def __repr__(self):
        return f"<Quotation rfq={self.rfq_id} vendor={self.vendor_id} status={self.status}>"