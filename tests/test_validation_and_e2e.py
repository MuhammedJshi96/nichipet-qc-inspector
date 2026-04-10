import pytest
from nichipet_qc_inspector.services.validation_service import validate_inspection_payload
from nichipet_qc_inspector.services.inspection_service import evaluate_inspection
from nichipet_qc_inspector.data.demo_data import build_demo_payload

def test_validation_failure_for_not_exactly_10_measurements():
    payload = build_demo_payload()
    payload["points"][0]["masses_mg"] = [1, 2]
    with pytest.raises(Exception):
        validate_inspection_payload(payload)

def test_validation_failure_for_non_positive_value():
    payload = build_demo_payload()
    payload["points"][0]["masses_mg"][0] = 0
    with pytest.raises(Exception):
        validate_inspection_payload(payload)

def test_full_end_to_end_sample_inspection():
    payload = build_demo_payload()
    validated = validate_inspection_payload(payload)
    result = evaluate_inspection(validated)
    assert len(result.point_results) == 3
    assert result.overall_status == "PASS"
    assert result.non_compliant_conditions is False