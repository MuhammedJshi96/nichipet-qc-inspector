from nichipet_qc_inspector.data.master_data import SYMPTOM_GUIDANCE

def build_guidance(result):
    guidance = []
    if result.overall_status == "PASS":
        return guidance
    if any(not p.passed for p in result.point_results):
        guidance.append("Inspection failed at one or more official points; review cleaning, seals, nozzle cylinder condition, and calibration setup.")
    for symptom in result.symptoms:
        guidance.extend(SYMPTOM_GUIDANCE.get(symptom, []))
    seen = []
    for item in guidance:
        if item not in seen:
            seen.append(item)
    return seen