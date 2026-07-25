from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    diagnoses = relationship("DiagnosticHistory", back_populates="user")


class DiagnosticHistory(Base):
    __tablename__ = "diagnostic_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    predicted_disease = Column(String, nullable=False)
    severity_score = Column(Float, nullable=False)
    humidity_at_time = Column(Float, nullable=False)
    leaf_wetness_at_time = Column(Float, nullable=False)
    is_physically_sound = Column(Boolean, default=True)
    ai_explanation = Column(Text, nullable=True)
    gradcam_image_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="diagnoses")