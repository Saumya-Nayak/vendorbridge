# backend/app/extensions.py
# VendorBridge — shared extension instances
# Import from here instead of from 'app' to avoid circular imports

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

db  = SQLAlchemy()
jwt = JWTManager()