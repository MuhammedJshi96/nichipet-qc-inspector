from nichipet_qc_inspector.services.calculation_service import threshold_equal

def point_passes(systematic_error_abs: float, cv, ac_limit: float, cv_limit: float, replicate_count: int):
    failure_reasons = []

    pass_error = systematic_error_abs <= ac_limit or threshold_equal(systematic_error_abs, ac_limit)
    if not pass_error:
        failure_reasons.append(
            f"Accuracy out of limit: |systematic error| {systematic_error_abs:.4f}% > AC limit {ac_limit:.4f}%."
        )

    if replicate_count >= 2:
        pass_cv = cv <= cv_limit or threshold_equal(cv, cv_limit)
        if not pass_cv:
            failure_reasons.append(
                f"Precision out of limit: CV {cv:.4f}% > CV limit {cv_limit:.4f}%."
            )
    else:
        pass_cv = True

    at_threshold = threshold_equal(systematic_error_abs, ac_limit) or (
        cv is not None and threshold_equal(cv, cv_limit)
    )

    return pass_error and pass_cv, at_threshold, failure_reasons

def overall_status(point_results, mode: str):
    all_pass = all(p.passed for p in point_results)
    if mode == "practice":
        return "PRACTICE / NOT OFFICIAL", False
    if mode == "routine":
        return ("GOOD TO USE", True) if all_pass else ("NEEDS MAINTENANCE", True)
    return ("GOOD TO USE", True) if all_pass else ("NEEDS MAINTENANCE", True)