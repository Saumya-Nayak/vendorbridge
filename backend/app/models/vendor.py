from app.extensions import db
from datetime import datetime


class VendorProfile(db.Model):
    __tablename__ = "vendor_profiles"
    __table_args__ = {"extend_existing": True}

    id               = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    user_id          = db.Column(db.Integer,       db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    gst_number       = db.Column(db.String(20),    nullable=True)
    vendor_category  = db.Column(db.String(100),   nullable=True)
    rating           = db.Column(db.Numeric(3, 2), default=0.00)
    total_orders     = db.Column(db.Integer,       default=0)
    status           = db.Column(
        db.Enum("pending", "approved", "suspended", name="vendor_status"),
        nullable=False,
        default="pending",
    )
    created_at       = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("vendor_profile", uselist=False, lazy="joined"))

    def __repr__(self):
        return f"<VendorProfile user_id={self.user_id} status={self.status}>"

    def to_dict(self):
        return {
            "id":              self.id,
            "user_id":         self.user_id,
            "gst_number":      self.gst_number,
            "vendor_category": self.vendor_category,
            "rating":          float(self.rating or 0),
            "total_orders":    self.total_orders or 0,
            "status":          self.status,
            "created_at":      self.created_at.isoformat() if self.created_at else None,
            "updated_at":      self.updated_at.isoformat() if self.updated_at else None,
        }