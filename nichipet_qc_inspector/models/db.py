from datetime import datetime
import json

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

DATABASE_URL = "sqlite:///nichipet_qc_inspector.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PipetteModel(Base):
    __tablename__ = "pipette_models"

    id = Column(Integer, primary_key=True)
    model_code = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    min_volume_ul = Column(Float, nullable=True)
    max_volume_ul = Column(Float, nullable=True)
    config_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    @property
    def config(self):
        if not self.config_json:
            return {}
        try:
            return json.loads(self.config_json)
        except Exception:
            return {}


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True)
    inspection_id = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    operator_name = Column(String(200), nullable=True)
    pipette_serial_number = Column(String(100), nullable=False)
    model_code = Column(String(100), nullable=False)
    comments = Column(Text, nullable=True)
    mode = Column(String(50), nullable=False)

    z_factor = Column(Float, nullable=False, default=1.0)
    overall_status = Column(String(100), nullable=False)
    official_decision_available = Column(Boolean, nullable=False, default=True)
    non_compliant_conditions = Column(Text, nullable=True)
    low_volume_note = Column(Text, nullable=True)

    points = relationship(
        "InspectionPoint",
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
    checklist_items = relationship(
        "ChecklistItem",
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
    symptom_logs = relationship(
        "SymptomLog",
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
    generated_reports = relationship(
        "GeneratedReport",
        back_populates="inspection",
        cascade="all, delete-orphan",
    )


class InspectionPoint(Base):
    __tablename__ = "inspection_points"

    id = Column(Integer, primary_key=True)
    inspection_id_fk = Column(Integer, ForeignKey("inspections.id"), nullable=False)

    point_order = Column(Integer, nullable=False)
    selected_volume_ul = Column(Float, nullable=False)
    ac_limit_percent = Column(Float, nullable=False)
    cv_limit_percent = Column(Float, nullable=False)
    mean_volume_ul = Column(Float, nullable=True)
    systematic_error_percent = Column(Float, nullable=True)
    absolute_systematic_error_percent = Column(Float, nullable=True)
    cv_percent = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=False, default=False)
    at_threshold = Column(Boolean, nullable=False, default=False)
    unit_warning = Column(Boolean, nullable=False, default=False)

    inspection = relationship("Inspection", back_populates="points")
    measurements = relationship(
        "Measurement",
        back_populates="inspection_point",
        cascade="all, delete-orphan",
    )


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True)
    inspection_point_id = Column(Integer, ForeignKey("inspection_points.id"), nullable=False)

    replicate_no = Column(Integer, nullable=False)
    mass_mg = Column(Float, nullable=False)
    corrected_volume_ul = Column(Float, nullable=False)

    inspection_point = relationship("InspectionPoint", back_populates="measurements")
    photo = relationship(
        "ReadingPhoto",
        back_populates="measurement",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ReadingPhoto(Base):
    __tablename__ = "reading_photos"

    id = Column(Integer, primary_key=True)
    measurement_id = Column(Integer, ForeignKey("measurements.id"), nullable=False, unique=True)

    file_name = Column(String(255), nullable=True)
    mime_type = Column(String(100), nullable=True)
    image_blob = Column(LargeBinary, nullable=False)

    measurement = relationship("Measurement", back_populates="photo")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True)
    inspection_id_fk = Column(Integer, ForeignKey("inspections.id"), nullable=False)

    item_key = Column(String(100), nullable=False)
    item_value = Column(Boolean, nullable=False, default=False)

    inspection = relationship("Inspection", back_populates="checklist_items")


class SymptomLog(Base):
    __tablename__ = "symptom_logs"

    id = Column(Integer, primary_key=True)
    inspection_id_fk = Column(Integer, ForeignKey("inspections.id"), nullable=False)

    symptom_key = Column(String(200), nullable=False)

    inspection = relationship("Inspection", back_populates="symptom_logs")


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True)
    inspection_id_fk = Column(Integer, ForeignKey("inspections.id"), nullable=False)

    report_type = Column(String(50), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    inspection = relationship("Inspection", back_populates="generated_reports")


class Operator(Base):
    __tablename__ = "operators"

    id = Column(Integer, primary_key=True)
    operator_name = Column(String(200), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AppUser(Base):
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


def get_session_factory():
    return SessionLocal


def create_database():
    Base.metadata.create_all(bind=engine)
