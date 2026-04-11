from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from nichipet_qc_inspector.models.db import Base

class AppUser(Base):
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)