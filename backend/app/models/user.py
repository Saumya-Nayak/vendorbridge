# backend/app/models/user.py
# VendorBridge — User & VendorProfile models

from app.extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    first_name    = db.Column(db.String(100),  nullable=False)
    last_name     = db.Column(db.String(100),  nullable=False)
    email         = db.Column(db.String(255),  nullable=False, unique=True)
    phone         = db.Column(db.String(20),   default=None)
    company       = db.Column(db.String(255),  nullable=False)
    role          = db.Column(
                        db.Enum('procurement_officer', 'vendor', 'manager', 'admin'),
                        nullable=False, default='procurement_officer'
                    )
    password_hash = db.Column(db.String(255),  nullable=False)
    is_active     = db.Column(db.SmallInteger, nullable=False, default=1)
    is_verified   = db.Column(db.SmallInteger, nullable=False, default=0)
    avatar_url    = db.Column(db.String(500),  default=None)
    last_login_at = db.Column(db.DateTime,     default=None)
    created_at    = db.Column(db.DateTime,     nullable=False, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime,     nullable=False, default=datetime.utcnow,
                              onupdate=datetime.utcnow)

   

    # ── Password helpers ──────────────────────────────────────────
    def set_password(self, password: str) -> None:
        """Hash and store the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True if the plaintext password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    # ── Serialiser ────────────────────────────────────────────────
    def to_dict(self):
        return {
            'id':          self.id,
            'first_name':  self.first_name,
            'last_name':   self.last_name,
            'email':       self.email,
            'phone':       self.phone,
            'company':     self.company,
            'role':        self.role,
            'is_active':   bool(self.is_active),
            'is_verified': bool(self.is_verified),
            'avatar_url':  self.avatar_url,
        }

    def __repr__(self):
        return f'<User {self.email}>'





class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id         = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    user_id    = db.Column(db.Integer,      db.ForeignKey('users.id', ondelete='CASCADE'),
                           nullable=False)
    token      = db.Column(db.String(255),  nullable=False, unique=True)
    expires_at = db.Column(db.DateTime,     nullable=False)
    used       = db.Column(db.SmallInteger, nullable=False, default=0)
    created_at = db.Column(db.DateTime,     nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<PasswordResetToken user_id={self.user_id}>'