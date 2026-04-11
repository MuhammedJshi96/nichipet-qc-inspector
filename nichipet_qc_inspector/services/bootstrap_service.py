import json

from nichipet_qc_inspector.models.db import PipetteModel
from nichipet_qc_inspector.data.master_data import NICHIPET_MODELS
from nichipet_qc_inspector.repositories.user_repository import UserRepository
from nichipet_qc_inspector.services.auth_service import hash_password


def seed_models(session):
    existing_codes = {row.model_code for row in session.query(PipetteModel).all()}
    inserted = False

    for item in NICHIPET_MODELS:
        if item["model_code"] in existing_codes:
            continue

        volume_range = item.get("volume_range_ul") or [None, None]
        min_volume = volume_range[0] if len(volume_range) > 0 else None
        max_volume = volume_range[1] if len(volume_range) > 1 else None

        session.add(
            PipetteModel(
                model_code=item["model_code"],
                display_name=item["display_name"],
                min_volume_ul=min_volume,
                max_volume_ul=max_volume,
                config_json=json.dumps(item, ensure_ascii=False),
            )
        )
        inserted = True

    if inserted:
        session.commit()

    seed_default_admin(session)


def seed_default_admin(session):
    user_repo = UserRepository(session)
    existing = user_repo.get_by_username("admin")
    if existing is None:
        user_repo.create_user(
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin",
            is_active=True,
        )
