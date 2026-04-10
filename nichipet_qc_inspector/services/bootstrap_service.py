import json
from nichipet_qc_inspector.models.db import PipetteModel
from nichipet_qc_inspector.data.master_data import NICHIPET_MODELS

def seed_models(session):
    existing_codes = {row.model_code for row in session.query(PipetteModel).all()}
    inserted = False

    for item in NICHIPET_MODELS:
        if item["model_code"] in existing_codes:
            continue
        session.add(
            PipetteModel(
                model_code=item["model_code"],
                display_name=item["display_name"],
                min_volume_ul=item["volume_range_ul"][0],
                max_volume_ul=item["volume_range_ul"][1],
                config_json=json.dumps(item, ensure_ascii=False),
            )
        )
        inserted = True

    if inserted:
        session.commit()