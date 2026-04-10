from nichipet_qc_inspector.services.calculation_service import (
    mass_to_volume,
    mean_volume,
    systematic_error_percent,
    cv_percent,
)
from nichipet_qc_inspector.services.decision_service import point_passes, overall_status
from nichipet_qc_inspector.models.schemas import PointResultSchema

def test_mass_to_volume_conversion():
    assert mass_to_volume(100, 1.0040) == 100.4

def test_mean_calculation():
    assert round(mean_volume([1, 2, 3, 4]), 6) == 2.5

def test_systematic_error_calculation():
    assert round(systematic_error_percent(100.4, 100), 6) == 0.4

def test_cv_calculation():
    assert cv_percent([100, 101, 99, 100, 100, 101, 99, 100, 100, 100]) > 0

def test_pass_fail_threshold_logic():
    passed, at_threshold = point_passes(0.8, 0.3, 0.8, 0.3)
    assert passed is True
    assert at_threshold is True

def test_borderline_equality_case():
    passed, _ = point_passes(1.0, 0.5, 1.0, 0.5)
    assert passed is True

def test_overall_pass_fail_aggregation():
    p1 = PointResultSchema(
        selected_volume_ul=1,
        ac_limit_percent=1,
        cv_limit_percent=1,
        masses_mg=[1] * 10,
        corrected_volumes_ul=[1] * 10,
        mean_volume_ul=1,
        systematic_error_percent=0,
        absolute_systematic_error_percent=0,
        cv_percent=0,
        passed=True,
        at_threshold=False,
    )
    p2 = PointResultSchema(
        selected_volume_ul=1,
        ac_limit_percent=1,
        cv_limit_percent=1,
        masses_mg=[1] * 10,
        corrected_volumes_ul=[1] * 10,
        mean_volume_ul=1,
        systematic_error_percent=0,
        absolute_systematic_error_percent=0,
        cv_percent=0,
        passed=False,
        at_threshold=False,
    )
    status, official = overall_status([p1, p2], "official")
    assert status == "NEEDS MAINTENANCE / CALIBRATION REVIEW"
    assert official is True