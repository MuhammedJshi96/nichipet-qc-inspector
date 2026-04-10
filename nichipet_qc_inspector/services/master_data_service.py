from dataclasses import dataclass, field
from typing import List, Optional
from nichipet_qc_inspector.data.master_data import NICHIPET_MODELS

@dataclass
class TestPoint:
    selected_volume_ul: float
    ac_limit_percent: float
    cv_limit_percent: float

@dataclass
class PipetteModelSpec:
    model_code: str
    display_name: str
    volume_range_ul: list[float]
    test_points: List[TestPoint] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

def _to_spec(item: dict) -> PipetteModelSpec:
    return PipetteModelSpec(
        model_code=item["model_code"],
        display_name=item["display_name"],
        volume_range_ul=item["volume_range_ul"],
        test_points=[
            TestPoint(
                selected_volume_ul=tp["selected_volume_ul"],
                ac_limit_percent=tp["ac_limit_percent"],
                cv_limit_percent=tp["cv_limit_percent"],
            )
            for tp in item["test_points"]
        ],
        notes=item.get("notes", []),
    )

def get_models():
    return [_to_spec(item) for item in NICHIPET_MODELS]

def get_model(model_code: str) -> Optional[PipetteModelSpec]:
    for item in NICHIPET_MODELS:
        if item["model_code"] == model_code:
            return _to_spec(item)
    return None