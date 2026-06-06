"""
VendorBridge — Activity Log Model
(Full implementation in Phase 10)
"""
from datetime import datetime
from app import db


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id          = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    user_id     = db.Column(db.Integer,     db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action      = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(100), nullable=True)
    entity_id   = db.Column(db.Integer,     nullable=True)
    description = db.Column(db.Text,        nullable=True)
    ip_address  = db.Column(db.String(50),  nullable=True)
    user_agent  = db.Column(db.String(500), nullable=True)
    created_at  = db.Column(db.DateTime,    nullable=False, default=datetime.utcnow)

    user = db.relationship("User", foreign_keys=[user_id])

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "user_id":     self.user_id,
            "action":      self.action,
            "entity_type": self.entity_type,
            "entity_id":   self.entity_id,
            "description": self.description,
            "ip_address":  self.ip_address,
            "created_at":  self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<ActivityLog {self.action} user={self.user_id}>"