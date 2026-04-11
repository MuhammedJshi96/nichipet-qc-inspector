from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

class ReadingPhotoIn(BaseModel):
    file_name: str
    mime_type: str
    image_blob: bytes

class InspectionMetadata(BaseModel):
    inspection_id: str
    created_at: datetime
    operator_name: str
    pipette_serial_number: str
    model_code: str
    comments: str = ""
    mode: str

class InspectionPointInput(BaseModel):
    selected_volume_ul: float
    ac_limit_percent: float
    cv_limit_percent: float
    masses_mg: List[float]
    reading_photos: Dict[int, ReadingPhotoIn] = Field(default_factory=dict)

class InspectionInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    metadata: InspectionMetadata
    checklist: dict
    points: List[InspectionPointInput]
    z_factor: float = 1.0040
    symptoms: List[str] = Field(default_factory=list)

class PointEvaluationResult(BaseModel):
    selected_volume_ul: float
    ac_limit_percent: float
    cv_limit_percent: float
    masses_mg: List[float]
    corrected_volumes_ul: List[float]
    mean_volume_ul: float
    systematic_error_percent: float
    absolute_systematic_error_percent: float
    cv_percent: Optional[float]
    passed: bool
    at_threshold: bool
    unit_warning: bool = False
    has_photo: bool = False
    reading_photos: Dict[int, ReadingPhotoIn] = Field(default_factory=dict)

class InspectionEvaluationResult(BaseModel):
    metadata: InspectionMetadata
    checklist: dict
    points: List[InspectionPointInput]
    z_factor: float
    symptoms: List[str]
    point_results: List[PointEvaluationResult]
    overall_status: str
    final_use_decision: str
    official_decision_available: bool
    non_compliant_conditions: bool
    low_volume_note: Optional[str] = None
    final_reason_summary: List[str] = Field(default_factory=list)
