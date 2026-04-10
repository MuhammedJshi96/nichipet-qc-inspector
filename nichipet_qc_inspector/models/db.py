from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

DB_PATH = Path("nichipet_qc_inspector.db")
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

_engine = None
_SessionLocal = None

def get_engine(db_url: str = DATABASE_URL):
    global _engine
    if _engine is None:
        _engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            future=True,
        )
    return _engine

def get_session_factory(db_url: str = DATABASE_URL):
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine(db_url)
        _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return _SessionLocal

class PipetteModel(Base):
    __tablename__ = "pipette_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_code = Column(String(64), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    min_volume_ul = Column(Float, nullable=False)
    max_volume_ul = Column(Float, nullable=False)
    config_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Operator(Base):
    __tablename__ = "operators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operator_name = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    operator_name = Column(String(255), nullable=False)
    pipette_serial_number = Column(String(32), nullable=False, index=True)
    model_code = Column(String(64), nullable=False, index=True)
    comments = Column(String(2000), nullable=True)
    mode = Column(String(32), nullable=False, index=True)
    z_factor = Column(Float, nullable=False, default=1.0040)
    overall_status = Column(String(64), nullable=False, index=True)
    official_decision_available = Column(Boolean, nullable=False, default=False)
    non_compliant_conditions = Column(Boolean, nullable=False, default=False)
    low_volume_note = Column(String(500), nullable=True)

    points = relationship("InspectionPoint", back_populates="inspection", cascade="all, delete-orphan")
    checklist_items = relationship("ChecklistItem", back_populates="inspection", cascade="all, delete-orphan")
    symptom_logs = relationship("SymptomLog", back_populates="inspection", cascade="all, delete-orphan")
    reports = relationship("GeneratedReport", back_populates="inspection", cascade="all, delete-orphan")

class InspectionPoint(Base):
    __tablename__ = "inspection_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id_fk = Column(Integer, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    point_order = Column(Integer, nullable=False)
    selected_volume_ul = Column(Float, nullable=False)
    ac_limit_percent = Column(Float, nullable=False)
    cv_limit_percent = Column(Float, nullable=False)
    mean_volume_ul = Column(Float, nullable=False)
    systematic_error_percent = Column(Float, nullable=False)
    absolute_systematic_error_percent = Column(Float, nullable=False)
    cv_percent = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=False, default=False)
    at_threshold = Column(Boolean, nullable=False, default=False)
    unit_warning = Column(Boolean, nullable=False, default=False)

    inspection = relationship("Inspection", back_populates="points")
    measurements = relationship("Measurement", back_populates="inspection_point", cascade="all, delete-orphan")

class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_point_id = Column(Integer, ForeignKey("inspection_points.id", ondelete="CASCADE"), nullable=False, index=True)
    replicate_no = Column(Integer, nullable=False)
    mass_mg = Column(Float, nullable=False)
    corrected_volume_ul = Column(Float, nullable=False)

    inspection_point = relationship("InspectionPoint", back_populates="measurements")
    photo = relationship("ReadingPhoto", back_populates="measurement", cascade="all, delete-orphan", uselist=False)

class ReadingPhoto(Base):
    __tablename__ = "reading_photos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    measurement_id = Column(Integer, ForeignKey("measurements.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    image_blob = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    measurement = relationship("Measurement", back_populates="photo")

class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id_fk = Column(Integer, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    item_key = Column(String(100), nullable=False)
    item_value = Column(Boolean, nullable=False)

    inspection = relationship("Inspection", back_populates="checklist_items")

class SymptomLog(Base):
    __tablename__ = "symptom_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id_fk = Column(Integer, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    symptom_key = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    inspection = relationship("Inspection", back_populates="symptom_logs")

class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id_fk = Column(Integer, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    report_type = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    inspection = relationship("Inspection", back_populates="reports")

def create_database(db_url: str = DATABASE_URL):
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    return engine