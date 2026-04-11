import math
from nichipet_qc_inspector.models.schemas import (
    InspectionInput,
    InspectionEvaluationResult,
    PointEvaluationResult,
)

def evaluate_inspection(data: InspectionInput) -> InspectionEvaluationResult:
    point_results = []
    reasons = []

    non_compliant = not all(bool(v) for v in data.checklist.values())

    low_volume_note = None
    if data.metadata.model_code == "00-NPX2-2":
        low_volume_note = "Below 0.2 μL, AC and CV depend on skill and sampling condition."
    elif data.metadata.model_code == "00-NPX2-10":
        low_volume_note = "Below 1 μL, AC and CV depend on skill and sampling condition."

    for idx, point in enumerate(data.points, start=1):
        masses = [float(m) for m in point.masses_mg]
        volumes = [m * float(data.z_factor) for m in masses]
        n = len(volumes)
        mean_volume = sum(volumes) / n

        selected_volume = float(point.selected_volume_ul)
        systematic_error = ((mean_volume - selected_volume) / selected_volume) * 100.0
        absolute_systematic_error = abs(systematic_error)

        if n > 1:
            variance = sum((v - mean_volume) ** 2 for v in volumes) / (n - 1)
            cv = (math.sqrt(variance) / mean_volume) * 100.0
        else:
            cv = None

        passed = False
        at_threshold = False
        if data.metadata.mode == "official":
            passed = (absolute_systematic_error <= float(point.ac_limit_percent)) and (cv is not None and cv <= float(point.cv_limit_percent))
            at_threshold = (absolute_systematic_error == float(point.ac_limit_percent)) or (cv == float(point.cv_limit_percent))
        else:
            passed = (absolute_systematic_error <= float(point.ac_limit_percent)) and (cv is not None and cv <= float(point.cv_limit_percent))
            at_threshold = (absolute_systematic_error == float(point.ac_limit_percent)) or (cv == float(point.cv_limit_percent))

        unit_warning = False
        if selected_volume <= 10 and any(m > 1000 for m in masses):
            unit_warning = True
        if selected_volume >= 1000 and any(m < 0.1 for m in masses):
            unit_warning = True

        if not passed:
            cv_text = "N/A" if cv is None else f"{cv:.4f}%"
            reasons.append(
                f"Point {idx} failed: |es|={absolute_systematic_error:.4f}% vs AC {point.ac_limit_percent:.4f}%, "
                f"CV={cv_text} vs limit {point.cv_limit_percent:.4f}%."
            )

        point_results.append(
            PointEvaluationResult(
                selected_volume_ul=selected_volume,
                ac_limit_percent=float(point.ac_limit_percent),
                cv_limit_percent=float(point.cv_limit_percent),
                masses_mg=masses,
                corrected_volumes_ul=volumes,
                mean_volume_ul=mean_volume,
                systematic_error_percent=systematic_error,
                absolute_systematic_error_percent=absolute_systematic_error,
                cv_percent=cv,
                passed=passed,
                at_threshold=at_threshold,
                unit_warning=unit_warning,
                has_photo=bool(point.reading_photos),
                reading_photos=point.reading_photos,
            )
        )

    overall_pass = all(p.passed for p in point_results)

    if data.metadata.mode == "practice":
        overall_status = "PRACTICE / NOT OFFICIAL"
        final_use_decision = "PRACTICE ONLY / NOT OFFICIAL"
        official_available = False
    elif data.metadata.mode == "routine":
        overall_status = "ROUTINE CHECK COMPLETE"
        final_use_decision = "ROUTINE REVIEW ONLY / NOT OFFICIAL"
        official_available = False
    else:
        overall_status = "PASS" if overall_pass else "NEEDS MAINTENANCE / CALIBRATION REVIEW"
        final_use_decision = "GOOD TO USE" if overall_pass else "NEEDS MAINTENANCE / CALIBRATION REVIEW"
        official_available = True

    return InspectionEvaluationResult(
        metadata=data.metadata,
        checklist=data.checklist,
        points=data.points,
        z_factor=float(data.z_factor),
        symptoms=data.symptoms,
        point_results=point_results,
        overall_status=overall_status,
        final_use_decision=final_use_decision,
        official_decision_available=official_available,
        non_compliant_conditions=non_compliant,
        low_volume_note=low_volume_note,
        final_reason_summary=reasons,
    )
