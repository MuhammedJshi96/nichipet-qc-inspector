from nichipet_qc_inspector.models.schemas import InspectionInput

def validate_inspection_payload(payload: dict) -> InspectionInput:
    if "points" not in payload or not payload["points"]:
        raise ValueError("At least one inspection point is required.")

    mode = payload.get("metadata", {}).get("mode", "")
    if mode == "official" and len(payload["points"]) != 3:
        raise ValueError("Official Inspection Mode requires exactly 3 official test points.")

    for idx, point in enumerate(payload["points"], start=1):
        masses = point.get("masses_mg", [])
        if mode == "official":
            if len(masses) != 10:
                raise ValueError(f"Point {idx}: Official mode requires exactly 10 measurements.")
        else:
            if len(masses) < 3:
                raise ValueError(f"Point {idx}: At least 3 measurements are required in non-official modes.")

        for rep, value in enumerate(masses, start=1):
            try:
                numeric_value = float(value)
            except Exception:
                raise ValueError(f"Point {idx}, replicate {rep}: numeric value required.")
            if numeric_value <= 0:
                raise ValueError(f"Point {idx}, replicate {rep}: value must be > 0.")

        if float(point["selected_volume_ul"]) <= 0:
            raise ValueError(f"Point {idx}: selected volume must be > 0.")
        if float(point["ac_limit_percent"]) <= 0 or float(point["cv_limit_percent"]) <= 0:
            raise ValueError(f"Point {idx}: AC and CV limits must be > 0.")

    return InspectionInput.model_validate(payload)