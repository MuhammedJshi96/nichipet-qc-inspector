from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from nichipet_qc_inspector.models.db import (
    Inspection,
    InspectionPoint,
    Measurement,
    ChecklistItem,
    SymptomLog,
    GeneratedReport,
    Operator,
    ReadingPhoto,
)

class InspectionRepository:
    def __init__(self, session):
        self.session = session

    def inspection_id_exists(self, inspection_id: str) -> bool:
        return self.session.query(Inspection).filter(Inspection.inspection_id == inspection_id).first() is not None

    def build_unique_inspection_id(self, base_id: str) -> str:
        if not self.inspection_id_exists(base_id):
            return base_id
        suffix = 2
        while True:
            candidate = f"{base_id}-{suffix}"
            if not self.inspection_id_exists(candidate):
                return candidate
            suffix += 1

    def save_inspection(self, result):
        requested_id = result.metadata.inspection_id
        unique_id = self.build_unique_inspection_id(requested_id)

        overall_status = result.overall_status
        if getattr(result.metadata, "is_demo", False):
            overall_status = "DEMO / NOT FOR OFFICIAL USE"

        inspection = Inspection(
            inspection_id=unique_id,
            created_at=result.metadata.created_at,
            operator_name=result.metadata.operator_name,
            pipette_serial_number=result.metadata.pipette_serial_number,
            model_code=result.metadata.model_code,
            comments=result.metadata.comments,
            mode=result.metadata.mode,
            z_factor=result.z_factor,
            overall_status=overall_status,
            official_decision_available=(False if getattr(result.metadata, "is_demo", False) else result.official_decision_available),
            non_compliant_conditions=result.non_compliant_conditions,
            low_volume_note=result.low_volume_note,
        )

        try:
            self.session.add(inspection)
            self.session.flush()

            for idx, point in enumerate(result.point_results, start=1):
                db_point = InspectionPoint(
                    inspection_id_fk=inspection.id,
                    point_order=idx,
                    selected_volume_ul=point.selected_volume_ul,
                    ac_limit_percent=point.ac_limit_percent,
                    cv_limit_percent=point.cv_limit_percent,
                    mean_volume_ul=point.mean_volume_ul,
                    systematic_error_percent=point.systematic_error_percent,
                    absolute_systematic_error_percent=point.absolute_systematic_error_percent,
                    cv_percent=point.cv_percent,
                    passed=point.passed,
                    at_threshold=point.at_threshold,
                    unit_warning=point.unit_warning,
                )
                self.session.add(db_point)
                self.session.flush()

                for rep, (mass, vol) in enumerate(zip(point.masses_mg, point.corrected_volumes_ul), start=1):
                    measurement = Measurement(
                        inspection_point_id=db_point.id,
                        replicate_no=rep,
                        mass_mg=mass,
                        corrected_volume_ul=vol,
                    )
                    self.session.add(measurement)
                    self.session.flush()

                    photo = point.reading_photos.get(rep) if point.reading_photos else None
                    if photo:
                        self.session.add(
                            ReadingPhoto(
                                measurement_id=measurement.id,
                                file_name=photo.file_name if hasattr(photo, "file_name") else photo.get("file_name"),
                                mime_type=photo.mime_type if hasattr(photo, "mime_type") else photo.get("mime_type"),
                                image_blob=photo.image_blob if hasattr(photo, "image_blob") else photo.get("image_blob"),
                            )
                        )

            for key, value in result.checklist.items():
                self.session.add(
                    ChecklistItem(
                        inspection_id_fk=inspection.id,
                        item_key=key,
                        item_value=bool(value),
                    )
                )

            for symptom in result.symptoms:
                self.session.add(
                    SymptomLog(
                        inspection_id_fk=inspection.id,
                        symptom_key=symptom,
                    )
                )

            self.session.commit()
            self.session.refresh(inspection)
            return inspection

        except IntegrityError:
            self.session.rollback()
            raise

    def list_inspections(self):
        return (
            self.session.query(Inspection)
            .order_by(Inspection.created_at.desc(), Inspection.id.desc())
            .all()
        )

    def get_inspection(self, inspection_pk):
        return (
            self.session.query(Inspection)
            .options(
                joinedload(Inspection.points)
                .joinedload(InspectionPoint.measurements)
                .joinedload(Measurement.photo),
                joinedload(Inspection.checklist_items),
                joinedload(Inspection.symptom_logs),
            )
            .filter(Inspection.id == inspection_pk)
            .first()
        )

    def delete_inspection(self, inspection_pk):
        record = self.get_inspection(inspection_pk)
        if not record:
            return False
        self.session.delete(record)
        self.session.commit()
        return True

    def list_operators(self):
        return self.session.query(Operator).order_by(Operator.operator_name.asc()).all()

    def add_operator(self, name: str):
        name = (name or "").strip()
        if not name:
            return None
        existing = self.session.query(Operator).filter(Operator.operator_name == name).first()
        if existing:
            return existing
        op = Operator(operator_name=name)
        self.session.add(op)
        self.session.commit()
        self.session.refresh(op)
        return op

    def delete_operator(self, operator_id: int):
        op = self.session.query(Operator).filter(Operator.id == operator_id).first()
        if not op:
            return False
        self.session.delete(op)
        self.session.commit()
        return True