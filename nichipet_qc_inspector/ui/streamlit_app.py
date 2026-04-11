from datetime import datetime
from pathlib import Path
import base64
import pandas as pd
import streamlit as st
from sqlalchemy.exc import IntegrityError

from nichipet_qc_inspector.models.db import get_session_factory, create_database
from nichipet_qc_inspector.repositories.user_repository import UserRepository
from nichipet_qc_inspector.repositories.inspection_repository import InspectionRepository
from nichipet_qc_inspector.services.auth_service import authenticate_user, hash_password, verify_password
from nichipet_qc_inspector.services.bootstrap_service import seed_models
from nichipet_qc_inspector.services.master_data_service import get_models
from nichipet_qc_inspector.services.validation_service import validate_inspection_payload
from nichipet_qc_inspector.services.inspection_service import evaluate_inspection
from nichipet_qc_inspector.services.report_service import export_html, export_pdf, export_csv
from nichipet_qc_inspector.data.master_data import HELP_NOTES, TROUBLESHOOTING_GUIDANCE
from nichipet_qc_inspector.data.demo_data import DEMO_DATASETS
from nichipet_qc_inspector.services.state_service import (
    init_app_state,
    store_draft,
    get_draft,
    set_last_result,
    get_last_result,
    reset_draft,
    set_selected_history_id,
    get_selected_history_id,
)

PIPETTE_NUMBERS = [f"#{i}" for i in range(1, 26)]
SYMPTOM_OPTIONS = [
    "tip cannot be ejected",
    "fails to aspirate liquid",
    "leaks from tip",
    "push button stiff",
]

LANG_TEXT = {
    "en": {
        "dashboard": "Dashboard",
        "official": "Official Inspection",
        "practice": "Practice / Troubleshooting",
        "routine": "Routine Check",
        "results": "Results",
        "history": "History",
        "settings": "Settings",
        "operator": "Operator",
        "add_operator": "Add operator",
        "delete_operator": "Delete operator",
        "language": "Language",
        "reset": "Reset form",
        "show_results": "Show results",
        "save": "Save inspection to SQLite",
    },
    "ja": {
        "dashboard": "ダッシュボード",
        "official": "公式点検",
        "practice": "練習 / トラブルシュート",
        "routine": "日常チェック",
        "results": "結果",
        "history": "履歴",
        "settings": "設定",
        "operator": "作業者",
        "add_operator": "作業者追加",
        "delete_operator": "作業者削除",
        "language": "言語",
        "reset": "リセット",
        "show_results": "結果を表示",
        "save": "SQLiteに保存",
    },
}

CHECKLIST_LABELS = {
    "distilled_water_confirmed": "Distilled water confirmed",
    "premium_tip_confirmed": "Premium Tip confirmed",
    "balance_calibrated_confirmed": "Balance calibrated confirmed",
    "temperature_equilibration_confirmed": "2–3 hour temperature equilibration confirmed",
    "room_temperature_confirmed": "Room temperature 20–25°C confirmed",
    "no_direct_airflow_confirmed": "No direct airflow confirmed",
    "vessel_with_lid_confirmed": "Vessel with lid prepared confirmed",
}


def get_saved_row_status(repo, row):
    demo_detected = (
        row.overall_status == "DEMO / NOT FOR OFFICIAL USE"
        or str(row.inspection_id).startswith("DEMO-")
        or "demo" in str(getattr(row, "comments", "") or "").lower()
    )
    if demo_detected:
        return ("DEMO", "demo")

    if row.mode == "routine":
        record = repo.get_inspection(row.id)
        if record:
            result = build_history_result(record)
            all_pass = all(getattr(p, "passed", False) for p in result.point_results)
            if all_pass:
                return ("ROUTINE PASS", "pass")
            return ("ROUTINE FAIL", "fail")
        return ("ROUTINE FAIL", "fail")

    if row.mode == "official":
        if row.overall_status == "PASS":
            return ("PASS", "pass")
        return ("FAIL", "fail")

    return ("NON-OFFICIAL", "neutral")


def render_status_pill(label, pill_type):
    class_map = {
        "pass": "pill-pass",
        "fail": "pill-fail",
        "neutral": "pill-neutral",
        "demo": "pill-demo",
    }
    return f"<span class='status-pill {class_map.get(pill_type, 'pill-neutral')}'>{label}</span>"


def get_current_role():
    return st.session_state.get("role", "")


def is_admin():
    return get_current_role() == "admin"


def logout():
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.rerun()

def ensure_auth_state():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "username" not in st.session_state:
        st.session_state["username"] = ""
    if "role" not in st.session_state:
        st.session_state["role"] = ""


def login_user(user):
    st.session_state["logged_in"] = True
    st.session_state["username"] = user.username
    st.session_state["role"] = user.role


def render_login(user_repo):
    st.markdown("## Login")
    st.warning("Welcome to Pipetteman QC Site")

    with st.container(border=True):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", type="primary", use_container_width=True):
            user_in_db = user_repo.get_by_username(username.strip()) if username.strip() else None

            if user_in_db is None:
                st.error("DEBUG: username not found")
                return

            st.write("DEBUG username:", user_in_db.username)
            st.write("DEBUG active:", user_in_db.is_active)
            st.write("DEBUG hash:", user_in_db.password_hash)
            st.write("DEBUG verify:", verify_password(password, user_in_db.password_hash))

            user, error = authenticate_user(user_repo, username, password)
            if error:
                st.error(error)
            else:
                st.session_state["logged_in"] = True
                st.session_state["username"] = user.username
                st.session_state["role"] = user.role
                st.rerun()
def t(key):
    lang = st.session_state.get("lang", "en")
    return LANG_TEXT.get(lang, LANG_TEXT["en"]).get(key, key)


def set_page(page_name: str):
    st.session_state["nav_override"] = page_name


def make_new_inspection_id(mode: str, is_demo: bool = False) -> str:
    prefix = "DEMO" if is_demo else mode.upper()
    return f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"


def load_logo_base64():
    for candidate in ["Picture1.jpg", "picture1.jpg", "assets/Picture1.jpg"]:
        p = Path(candidate)
        if p.exists():
            return base64.b64encode(p.read_bytes()).decode("utf-8")
    return None


def inject_css():
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(180deg, #f4f8fb 0%, #ffffff 35%, #f9fbfc 100%); }
        .block-container { padding-top: 2.0rem; padding-bottom: 1.5rem; max-width: 1320px; }
        .brand-wrap {
            display:flex; align-items:center; justify-content:space-between; gap:18px; width:100%;
            margin-top:1.1rem; margin-bottom:1rem; padding:14px 18px; border-radius:0;
            background:linear-gradient(90deg, #ffffff 0%, #f1f8f4 45%, #eef7fb 100%);
            border:1px solid rgba(30,111,67,0.14); box-shadow:0 8px 24px rgba(26,71,42,0.08);
            cursor:default !important;
        }
        .brand-left { display:flex; align-items:center; gap:16px; }
        .brand-logo { width:58px; height:58px; object-fit:contain; border-radius:0; background:white; padding:4px; border:1px solid rgba(0,0,0,0.06); }
        .brand-title { font-size:1.45rem; font-weight:800; color:#163b2d; margin:0; line-height:1.1; }
        .brand-sub { font-size:0.88rem; color:#55786a; margin-top:4px; }
        .brand-credit { font-size:0.82rem; color:#516c61; text-align:right; line-height:1.35; }
        .section-card { background:transparent; border:none; box-shadow:none; padding:0; margin-bottom:0.9rem; cursor:default !important; }

        .metric-grid { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:12px; margin:8px 0 14px 0; }
        .metric-card {
            background:linear-gradient(135deg, #ffffff 0%, #f4fbf7 100%);
            border:1px solid rgba(17,92,55,0.10); border-radius:12px; padding:12px 14px;
            box-shadow:0 6px 16px rgba(17,92,55,0.05); cursor:default !important;
        }
        .metric-label { font-size:0.76rem; text-transform:uppercase; letter-spacing:0.04em; color:#668173; margin-bottom:4px; }
        .metric-value { font-size:1.12rem; font-weight:800; color:#14372a; word-break:break-word; }

        .status-pill {
            display:inline-block; padding:0.24rem 0.65rem; border-radius:999px; font-size:0.74rem;
            font-weight:800; letter-spacing:0.02em; cursor:default !important;
        }
        .pill-pass { background:#e8f7ef; color:#0f7b4b; border:1px solid rgba(15,123,75,0.16); }
        .pill-fail { background:#fdecec; color:#b42318; border:1px solid rgba(180,35,24,0.16); }
        .pill-neutral { background:#fff6dd; color:#7a5d00; border:1px solid rgba(122,93,0,0.16); }
        .pill-demo { background:#f3e8ff; color:#6b21a8; border:1px solid rgba(107,33,168,0.16); }

        .point-title { font-size:1.04rem; font-weight:800; color:#18392d; margin-bottom:8px; }
        .manual-box {
            background:linear-gradient(135deg, #f8fffb 0%, #edf7f1 100%);
            border-left:4px solid #2c8b57; border-radius:10px; padding:11px 13px; margin:10px 0 14px 0; color:#244837;
        }
        .small-banner {
            display:inline-block; padding:5px 10px; border-radius:999px; font-size:0.78rem; font-weight:700;
            background:#e8f4ed; color:#195a39; border:1px solid rgba(25,90,57,0.10); margin-bottom:8px;
        }

        .compact-grid {
            display: grid;
            grid-template-columns: minmax(52px, 70px) minmax(140px, 2fr) minmax(120px, 1.2fr) minmax(60px, 90px) minmax(70px, 110px) minmax(95px, 130px) minmax(72px, 88px) minmax(72px, 88px);
            gap: 8px;
            align-items: center;
        }

        .compact-head, .compact-row {
            padding: 8px 10px;
            border-radius: 10px;
        }

        @media (max-width: 900px) {
            .compact-head { display: none; }
            .compact-grid { grid-template-columns: 1fr; }
            .compact-row {
                display: grid;
                gap: 8px;
            }
            .compact-row > div {
                display: flex;
                justify-content: space-between;
                gap: 12px;
                align-items: center;
                min-width: 0;
            }
            .compact-row > div::before {
                content: attr(data-label);
                font-weight: 700;
                color: #6c8478;
                flex: 0 0 auto;
            }
        }

        .thumb-card {
            border:1px solid rgba(15,79,56,0.10); border-radius:10px; padding:8px; background:white; margin-bottom:10px;
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stMarkdownContainer"],
        div[data-testid="stVerticalBlock"],
        div[data-testid="stHorizontalBlock"],
        div[data-testid="stMetric"],
        table, thead, tbody, tr, td, th, ul, ol, li, p, span, label {
            cursor:default !important;
        }
        
        .stDataFrame div { cursor:default !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_brand_header():
    logo_b64 = load_logo_base64()
    logo_html = f"<img class='brand-logo' src='data:image/jpeg;base64,{logo_b64}' alt='Lab logo' />" if logo_b64 else ""
    st.markdown(
        f"""
        <div class="brand-wrap">
            <div class="brand-left">
                {logo_html}
                <div>
                    <div class="brand-title">Nichipet QC Inspector</div>
                    <div class="brand-sub">Laboratory inspection and calibration review workspace</div>
                </div>
            </div>
            <div class="brand-credit">
                <strong>Created by</strong><br>
                Muhammed Al-Jeshi
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def default_draft(model_code, mode, point_specs, replicate_count):
    return {
        "metadata": {
            "inspection_id": make_new_inspection_id(mode, False),
            "created_at": datetime.now(),
            "operator_name": "",
            "pipette_serial_number": "#1",
            "model_code": model_code,
            "comments": "",
            "mode": mode,
            "is_demo": False,
        },
        "checklist": {
            "distilled_water_confirmed": True,
            "premium_tip_confirmed": True,
            "balance_calibrated_confirmed": True,
            "temperature_equilibration_confirmed": True,
            "room_temperature_confirmed": True,
            "no_direct_airflow_confirmed": True,
            "vessel_with_lid_confirmed": True,
        },
        "z_factor": 1.0040,
        "symptoms": [],
        "replicate_count": replicate_count,
        "points": [
            {
                "selected_volume_ul": p.selected_volume_ul,
                "ac_limit_percent": p.ac_limit_percent,
                "cv_limit_percent": p.cv_limit_percent,
                "masses_mg": [""] * replicate_count,
                "reading_photos": {},
            }
            for p in point_specs
        ],
    }


def resize_points_for_replicates(points, replicate_count):
    for point in points:
        current = list(point.get("masses_mg", []))
        point["masses_mg"] = (current[:replicate_count] + [""] * replicate_count)[:replicate_count]
        photos = point.get("reading_photos", {})
        point["reading_photos"] = {k: v for k, v in photos.items() if k <= replicate_count}


def ensure_draft(draft_key, model_code, mode, point_specs, replicate_count):
    draft = get_draft(draft_key)
    if draft is None:
        draft = default_draft(model_code, mode, point_specs, replicate_count)

    draft["metadata"]["model_code"] = model_code
    draft["metadata"]["mode"] = mode
    draft["replicate_count"] = replicate_count

    if len(draft["points"]) != len(point_specs):
        draft["points"] = default_draft(model_code, mode, point_specs, replicate_count)["points"]

    for idx, spec in enumerate(point_specs):
        draft["points"][idx]["selected_volume_ul"] = spec.selected_volume_ul
        draft["points"][idx]["ac_limit_percent"] = spec.ac_limit_percent
        draft["points"][idx]["cv_limit_percent"] = spec.cv_limit_percent
        draft["points"][idx].setdefault("reading_photos", {})

    resize_points_for_replicates(draft["points"], replicate_count)
    store_draft(draft_key, draft)
    return draft


def normalize_photo(photo):
    if photo is None:
        return None

    if isinstance(photo, dict):
        filename = photo.get("filename") or photo.get("name")
        image_blob = photo.get("image_blob") or photo.get("imageblob")
        mime_type = photo.get("mime_type") or photo.get("mimetype") or "image/jpeg"
        return {
            "filename": filename,
            "name": filename,
            "image_blob": image_blob,
            "imageblob": image_blob,
            "mime_type": mime_type,
            "mimetype": mime_type,
        }

    filename = getattr(photo, "filename", None) or getattr(photo, "name", None)
    image_blob = getattr(photo, "image_blob", None) or getattr(photo, "imageblob", None)
    mime_type = getattr(photo, "mime_type", None) or getattr(photo, "mimetype", None) or "image/jpeg"

    return {
        "filename": filename,
        "name": filename,
        "image_blob": image_blob,
        "imageblob": image_blob,
        "mime_type": mime_type,
        "mimetype": mime_type,
    }


def build_history_result(record):
    class Obj:
        pass

    result = Obj()
    result.metadata = Obj()
    result.metadata.inspection_id = record.inspection_id
    result.metadata.created_at = record.created_at
    result.metadata.operator_name = record.operator_name
    result.metadata.pipette_serial_number = record.pipette_serial_number
    result.metadata.model_code = record.model_code
    result.metadata.comments = record.comments or ""
    result.metadata.mode = record.mode

    demo_detected = (
        record.overall_status == "DEMO / NOT FOR OFFICIAL USE"
        or str(record.inspection_id).startswith("DEMO-")
        or "demo" in str(record.comments or "").lower()
    )
    result.metadata.is_demo = demo_detected

    result.z_factor = record.z_factor
    result.overall_status = record.overall_status
    result.final_use_decision = "GOOD TO USE" if record.overall_status == "PASS" else record.overall_status
    if demo_detected:
        result.overall_status = "DEMO / NOT FOR OFFICIAL USE"
        result.final_use_decision = "DEMO / NOT FOR OFFICIAL USE"
    elif record.overall_status == "PASS":
        result.final_use_decision = "GOOD TO USE"
    else:
        result.final_use_decision = record.overall_status

    result.official_decision_available = False if demo_detected else record.official_decision_available
    result.non_compliant_conditions = record.non_compliant_conditions
    result.low_volume_note = record.low_volume_note
    result.symptoms = [s.symptom_key for s in sorted(record.symptom_logs, key=lambda x: x.id)]
    result.checklist = {c.item_key: c.item_value for c in sorted(record.checklist_items, key=lambda x: x.id)}
    result.final_reason_summary = []

    point_results = []
    for point in sorted(record.points, key=lambda x: x.point_order):
        p = Obj()
        p.selected_volume_ul = point.selected_volume_ul
        p.ac_limit_percent = point.ac_limit_percent
        p.cv_limit_percent = point.cv_limit_percent
        p.mean_volume_ul = point.mean_volume_ul
        p.systematic_error_percent = point.systematic_error_percent
        p.absolute_systematic_error_percent = point.absolute_systematic_error_percent
        p.cv_percent = point.cv_percent
        p.passed = point.passed
        p.at_threshold = point.at_threshold
        p.unit_warning = point.unit_warning
        p.masses_mg = []
        p.corrected_volumes_ul = []
        p.reading_photos = {}
        for m in sorted(point.measurements, key=lambda x: x.replicate_no):
            p.masses_mg.append(m.mass_mg)
            p.corrected_volumes_ul.append(m.corrected_volume_ul)
            if m.photo:
                p.reading_photos[m.replicate_no] = normalize_photo(m.photo)
        point_results.append(p)
    result.point_results = point_results
    return result


def apply_demo_dataset(draft, selected_model, dataset_key):
    dataset = DEMO_DATASETS[dataset_key]
    if dataset["model_code"] != selected_model.model_code:
        return draft, False

    draft["metadata"]["is_demo"] = True
    draft["metadata"]["inspection_id"] = make_new_inspection_id(draft["metadata"]["mode"], True)
    draft["metadata"]["comments"] = "Demo dataset loaded — not for official use."
    draft["z_factor"] = dataset["z_factor"]

    for idx, point_masses in enumerate(dataset["points"]):
        if idx < len(draft["points"]):
            draft["points"][idx]["masses_mg"] = [str(x) for x in point_masses]
            draft["points"][idx]["reading_photos"] = {}
    return draft, True


def build_payload_from_draft(draft):
    payload = {
        "metadata": draft["metadata"],
        "checklist": draft["checklist"],
        "z_factor": draft["z_factor"],
        "symptoms": draft["symptoms"],
        "points": [],
    }
    for p in draft["points"]:
        payload["points"].append(
            {
                "selected_volume_ul": p["selected_volume_ul"],
                "ac_limit_percent": p["ac_limit_percent"],
                "cv_limit_percent": p["cv_limit_percent"],
                "masses_mg": [float(x) for x in p["masses_mg"]],
                "reading_photos": p["reading_photos"],
            }
        )
    return payload


def calculate_and_show(draft):
    validated = validate_inspection_payload(build_payload_from_draft(draft))
    result = evaluate_inspection(validated)

    if getattr(validated.metadata, "is_demo", False):
        result.metadata.is_demo = True
        result.metadata.inspection_id = validated.metadata.inspection_id
        result.metadata.comments = validated.metadata.comments
        result.overall_status = "DEMO / NOT FOR OFFICIAL USE"
        result.final_use_decision = "DEMO / NOT FOR OFFICIAL USE"
        result.official_decision_available = False

    set_last_result(result)
    set_page(t("results"))
    st.rerun()


def decision_pill_html(result):
    if getattr(result.metadata, "is_demo", False) or result.overall_status == "DEMO / NOT FOR OFFICIAL USE":
        return "<span class='status-pill pill-demo'>DEMO / NOT FOR OFFICIAL USE</span>"

    if result.metadata.mode == "routine":
        all_pass = all(getattr(p, "passed", False) for p in result.point_results)
        if all_pass:
            return "<span class='status-pill pill-pass'>PASS</span>"
        return "<span class='status-pill pill-fail'>FAIL</span>"

    if result.metadata.mode == "official":
        if result.overall_status == "PASS":
            return "<span class='status-pill pill-pass'>PASS</span>"
        return "<span class='status-pill pill-fail'>FAIL</span>"

    return "<span class='status-pill pill-neutral'>NON-OFFICIAL</span>"


def history_status_pill(repo, row):
    status_label, status_type = get_saved_row_status(repo, row)
    return render_status_pill(status_label, status_type)


def render_history(repo):
    st.subheader(t("history"))
    rows = repo.list_inspections()
    if not rows:
        st.info("No saved inspections.")
        return

    st.markdown(
        "<div class='compact-head compact-grid'><div>DB ID</div><div>Inspection ID</div><div>Operator</div><div>Pipette</div><div>Mode</div><div>Status</div><div>Open</div><div>Delete</div></div>",
        unsafe_allow_html=True,
    )

    for row in rows:
        cols = st.columns([0.7, 2.4, 1.6, 0.8, 0.8, 1.2, 1.0, 1.0])
        cols[0].markdown(str(row.id))
        cols[1].markdown(str(row.inspection_id))
        cols[2].markdown(str(row.operator_name or "-"))
        cols[3].markdown(str(row.pipette_serial_number))
        cols[4].markdown(str(row.mode))
        cols[5].markdown(history_status_pill(repo, row), unsafe_allow_html=True)

        if cols[6].button("Open", key=f"open_{row.id}", use_container_width=True):
            set_selected_history_id(row.id)
            set_page(t("history"))
            st.rerun()

        if is_admin():
            if cols[7].button("Delete", key=f"delete_{row.id}", use_container_width=True):
                repo.delete_inspection(row.id)
                if get_selected_history_id() == row.id:
                    set_selected_history_id(None)
                st.success(f"Deleted inspection DB ID {row.id}")
                st.rerun()
        else:
            cols[7].markdown("-")

    selected_id = get_selected_history_id()
    if selected_id:
        record = repo.get_inspection(selected_id)
        if record:
            st.markdown("### Saved inspection review")
            render_results_block(build_history_result(record), repo=None, allow_save=False)

def render_results_block(result, repo=None, allow_save=True):
    if not result:
        st.info("No current result.")
        return

    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Inspection ID</div>
                <div class="metric-value">{result.metadata.inspection_id}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Model</div>
                <div class="metric-value">{result.metadata.model_code}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Pipette number</div>
                <div class="metric-value">{result.metadata.pipette_serial_number}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Decision</div>
                <div class="metric-value">{decision_pill_html(result)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if getattr(result.metadata, "comments", ""):
        st.markdown("### Comment")
        st.info(result.metadata.comments)

    if getattr(result.metadata, "is_demo", False):
        st.warning("This result was generated from a demo dataset. It must not be used for official inspection release.")

    if getattr(result, "low_volume_note", None):
        st.warning(result.low_volume_note)

    if getattr(result, "noncompliant_conditions", None):
        st.warning("Checklist has non-compliant conditions.")

    for idx, p in enumerate(result.point_results, start=1):
        st.markdown(
            f'<div class="point-title">Point {idx} — Vs {p.selected_volume_ul} μL</div>',
            unsafe_allow_html=True,
        )

        stddev_ul = None
        if getattr(p, "corrected_volumes_ul", None) and len(p.corrected_volumes_ul) > 1:
            stddev_ul = pd.Series(p.corrected_volumes_ul, dtype="float64").std(ddof=1)

        #Latest Edit#
        #Start#
        mean_text = f"{p.mean_volume_ul:.4f} μL" if p.mean_volume_ul is not None else "N/A"
        std_text = f"{stddev_ul:.4f} μL" if stddev_ul is not None else "N/A"
        se_text = f"{p.systematic_error_percent:.4f}" if p.systematic_error_percent is not None else "N/A"
        abs_se_text = f"{p.absolute_systematic_error_percent:.4f}" if p.absolute_systematic_error_percent is not None else "N/A"
        cv_text = f"{p.cv_percent:.4f}" if p.cv_percent is not None else "N/A"
        ac_limit_text = f"{p.ac_limit_percent:.4f}" if p.ac_limit_percent is not None else "N/A"
        cv_limit_text = f"{p.cv_limit_percent:.4f}" if p.cv_limit_percent is not None else "N/A"

        metric_sections = st.columns(3)

        with metric_sections[0]:
            with st.container(border=True):
                st.markdown("#### Volume")
                a, b = st.columns(2)
                a.metric("Mean", mean_text)
                b.metric("Std Dev", std_text)

        with metric_sections[1]:
            with st.container(border=True):
                st.markdown("#### Accuracy")
                a, b, c = st.columns(3)
                a.metric("SE%", se_text)
                b.metric("|SE|%", abs_se_text)
                c.metric("AC limit", ac_limit_text)
                st.caption("Accuracy is judged by systematic error against the AC limit.")

        with metric_sections[2]:
            with st.container(border=True):
                st.markdown("#### Precision")
                a, b = st.columns(2)
                a.metric("CV%", cv_text)
                b.metric("CV limit", cv_limit_text)
                st.caption("Precision is judged by CV against the CV limit.")
        #END#

        point_pill = (
            '<span class="status-pill pill-pass">PASS</span>'
            if p.passed
            else '<span class="status-pill pill-fail">FAIL</span>'
        )
        st.markdown(f"Point result: {point_pill}", unsafe_allow_html=True)

        df = pd.DataFrame(
            {
                "Replicate": list(range(1, len(p.masses_mg) + 1)),
                "Mass (mg)": p.masses_mg,
                "Corrected volume (μL)": [round(v, 4) for v in p.corrected_volumes_ul],
                "Photo": ["Yes" if i + 1 in p.reading_photos else "No" for i in range(len(p.masses_mg))],
            }
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

        photo_items = sorted(p.reading_photos.items(), key=lambda x: x[0])
        if photo_items:
            st.markdown("Uploaded reading photos")
            photo_cols = st.columns(4)
            for i, (rep_no, photo_raw) in enumerate(photo_items):
                photo = normalize_photo(photo_raw)
                with photo_cols[i % 4]:
                    st.markdown(
                        f'<div class="thumb-card"><strong>Replicate {rep_no}</strong></div>',
                        unsafe_allow_html=True,
                    )
                    if photo and photo.get("image_blob") is not None:
                        caption_text = photo.get("filename") or photo.get("name") or f"Replicate {rep_no}"
                        st.image(photo.get("image_blob"), caption=caption_text, use_container_width=True)
                    else:
                        st.info(f"No preview available for replicate {rep_no}.")
        if getattr(p, "unit_warning", False):
            st.warning("Possible unit issue detected for this point.")

    if getattr(result, "symptoms", None):
        st.markdown("### Troubleshooting guidance")
        shown = set()
        for symptom in result.symptoms:
            if symptom in shown:
                continue
            shown.add(symptom)
            st.markdown(f"**{symptom}**")
            for line in TROUBLESHOOTING_GUIDANCE.get(symptom, []):
                st.write(f"- {line}")

    html_path = export_html(result)
    pdf_path = export_pdf(result)
    csv_path = export_csv(result)

    if allow_save and repo is not None:
        c1, c2, c3, c4 = st.columns(4)

        inspection_id = result.metadata.inspection_id
        saved_key = f"saved_once_{inspection_id}"
        just_saved_key = f"just_saved_{inspection_id}"

        current_active_id = st.session_state.get("active_result_id")
        if current_active_id != inspection_id:
            st.session_state["active_result_id"] = inspection_id
            st.session_state.pop("save_success_message", None)
            st.session_state.pop("save_error_message", None)

        already_saved = st.session_state.get(saved_key, False)
        just_saved = st.session_state.get(just_saved_key, False)

        if already_saved:
            st.info("This result has already been saved to SQLite.")

        button_slot = c1.empty()

        if already_saved:
            button_slot.success("Saved to SQLite")
        else:
            if button_slot.button(t("save"), use_container_width=True):
                try:
                    saved = repo.save_inspection(result)
                    st.session_state[saved_key] = True
                    st.session_state[just_saved_key] = True
                    st.session_state["save_success_message"] = f"Saved successfully: {saved.inspection_id}"
                    st.session_state["active_result_id"] = inspection_id
                    set_page(t("results"))
                    st.rerun()
                except IntegrityError:
                    repo.session.rollback()
                    st.session_state["save_error_message"] = "Save failed."
                    set_page(t("results"))
                    st.rerun()

        if just_saved:
            msg = st.session_state.get("save_success_message")
            if msg:
                st.success(msg)
            st.session_state[just_saved_key] = False
            st.session_state.pop("save_success_message", None)

        err = st.session_state.pop("save_error_message", None)
        if err:
            st.error(err)

        c2.download_button(
            "Download HTML",
            data=html_path.read_text(encoding="utf-8"),
            file_name=html_path.name,
            mime="text/html",
            use_container_width=True,
        )
        c3.download_button(
            "Download PDF",
            data=pdf_path.read_bytes(),
            file_name=pdf_path.name,
            mime="application/pdf",
            use_container_width=True,
        )
        c4.download_button(
            "Download CSV",
            data=csv_path.read_text(encoding="utf-8"),
            file_name=csv_path.name,
            mime="text/csv",
            use_container_width=True,
        )
    else:
        c1, c2, c3 = st.columns(3)
        c1.download_button(
            "Download HTML",
            data=html_path.read_text(encoding="utf-8"),
            file_name=html_path.name,
            mime="text/html",
            use_container_width=True,
        )
        c2.download_button(
            "Download PDF",
            data=pdf_path.read_bytes(),
            file_name=pdf_path.name,
            mime="application/pdf",
            use_container_width=True,
        )
        c3.download_button(
            "Download CSV",
            data=csv_path.read_text(encoding="utf-8"),
            file_name=csv_path.name,
            mime="text/csv",
            use_container_width=True,
        )
        
def render_user_management(user_repo, repo):
    st.markdown("### User management")

    with st.container(border=True):
        st.markdown("#### Add new user")
        c1, c2, c3, c4 = st.columns([1.6, 1.4, 1.0, 1.2])
        new_username = c1.text_input("Username", key="new_user_username")
        new_password = c2.text_input("Temporary password", type="password", key="new_user_password")
        new_role = c3.selectbox("Role", ["user", "admin"], key="new_user_role")
        create_operator = c4.checkbox("Add to operators", value=True, key="new_user_add_operator")

        if st.button("Create user", type="primary", use_container_width=True):
            username = new_username.strip()
            password = new_password.strip()
            if not username or not password:
                st.error("Username and password are required.")
            elif user_repo.get_by_username(username) is not None:
                st.error("This username already exists.")
            else:
                user = user_repo.create_user(
                    username=username,
                    password_hash=hash_password(password),
                    role=new_role,
                    is_active=True,
                )
                if create_operator:
                    existing_operator_names = {op.operator_name for op in repo.list_operators()}
                    if username not in existing_operator_names:
                        repo.add_operator(username)
                st.success(f"User '{user.username}' created successfully.")
                st.rerun()

    st.markdown("### Existing users")
    users = user_repo.list_users()

    if not users:
        st.info("No users yet.")
        return

    user_rows = []
    for u in users:
        user_rows.append(
            {
                "ID": u.id,
                "Username": u.username,
                "Role": u.role,
                "Active": "Yes" if u.is_active else "No",
                "Created": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "-",
            }
        )

    st.dataframe(pd.DataFrame(user_rows), use_container_width=True, hide_index=True)

    st.markdown("### Manage selected user")

    user_options = {f"{u.username} (ID {u.id})": u for u in users}

    selected_label = st.selectbox(
        "Select user",
        list(user_options.keys()),
        key="manage_selected_user",
    )
    selected_user = user_options[selected_label]

    with st.form(f"user_mgmt_form_{selected_user.id}"):
        c1, c2 = st.columns(2)
        new_role_value = c1.selectbox(
            "Change role",
            ["user", "admin"],
            index=0 if selected_user.role == "user" else 1,
            key=f"edit_role_{selected_user.id}",
        )
        new_password_value = c2.text_input(
            "New password (optional)",
            type="password",
            key=f"edit_password_{selected_user.id}",
        )

        c3, c4, c5, c6 = st.columns(4)
        update_role_clicked = c3.form_submit_button("Update role", use_container_width=True)
        toggle_active_clicked = c4.form_submit_button(
            "Activate" if not selected_user.is_active else "Deactivate",
            use_container_width=True,
        )
        delete_user_clicked = c5.form_submit_button("Delete user", use_container_width=True)
        update_password_clicked = c6.form_submit_button("Update password", use_container_width=True)

    if update_role_clicked:
        user_repo.update_role(selected_user.id, new_role_value)
        st.success(f"Role updated for {selected_user.username}.")
        st.rerun()

    if toggle_active_clicked:
        if selected_user.username == st.session_state.get("username") and selected_user.is_active:
            st.error("You cannot deactivate your own logged-in account.")
        else:
            user_repo.set_active(selected_user.id, not selected_user.is_active)
            st.success(f"Active status updated for {selected_user.username}.")
            st.rerun()

    if delete_user_clicked:
        if selected_user.username == st.session_state.get("username"):
            st.error("You cannot delete your own logged-in account.")
        else:
            user_repo.delete_user(selected_user.id)
            st.success(f"Deleted user: {selected_user.username}")
            st.rerun()

    if update_password_clicked:
        if not new_password_value.strip():
            st.error("Please enter a new password.")
        else:
            user_repo.update_password(
                selected_user.id,
                hash_password(new_password_value.strip())
            )
            st.success(f"Password updated for {selected_user.username}.")
            st.rerun()


def render_settings(repo, user_repo):
    st.subheader(t("settings"))

    st.session_state["lang"] = st.selectbox(
        t("language"),
        ["en", "ja"],
        index=["en", "ja"].index(st.session_state.get("lang", "en")),
    )

    if not is_admin():
        st.info("Normal users can only change language settings.")
        return

    st.markdown("### Operator")
    c1, c2 = st.columns([2, 1])
    newop = c1.text_input("New operator name", key="settings_new_operator")

    if c2.button(t("add_operator")) and newop.strip():
        repo.add_operator(newop.strip())
        set_page(t("settings"))
        st.success("Operator saved.")
        st.rerun()

    operators = repo.list_operators()

    if operators:
        labels = {f"{op.operator_name} (ID {op.id})": op.id for op in operators}
        selected = st.selectbox(
            "Saved operators",
            list(labels.keys()),
            key="settings_saved_operator",
        )

        if st.button(t("delete_operator")):
            repo.delete_operator(labels[selected])
            set_page(t("settings"))
            st.success("Operator deleted.")
            st.rerun()
    else:
        st.info("No saved operators yet.")

    render_user_management(user_repo, repo)

def render_mode_page(repo, mode_key, draft_key, official_mode=False, routine_mode=False):
    reset_nonce = st.session_state.get(f"{mode_key}_reset_nonce", 0)
    key_prefix = f"{draft_key}_{reset_nonce}"

    st.subheader(t(mode_key if mode_key != "practice" else "practice"))

    models = get_models()
    selected_name = st.selectbox("Pipette model", [m.display_name for m in models], key=f"{key_prefix}_model")
    selected_model = next(m for m in models if m.display_name == selected_name)

    if official_mode:
        point_specs = selected_model.test_points
        replicate_count = 10
    elif routine_mode:
        point_specs = [selected_model.test_points[-1]]
        replicate_count = st.selectbox("Replicates (routine mode)", [3, 5, 10], index=1, key=f"{key_prefix}_reps")
    else:
        point_specs = selected_model.test_points
        replicate_count = st.selectbox("Replicates per point (practice mode)", [3, 5, 10], index=2, key=f"{key_prefix}_reps")

    draft = ensure_draft(draft_key, selected_model.model_code, mode_key, point_specs, replicate_count)

    if official_mode:
        st.markdown(
            '<div class="small-banner">Official mode uses exactly 10 replicates per point</div>',
            unsafe_allow_html=True
        )

        demo_cols = st.columns(4)

        if demo_cols[0].button("Load Demo PASS", key=f"{key_prefix}_demo_pass"):
            draft, ok = apply_demo_dataset(draft, selected_model, "official_pass_100uL")
            if ok:
                store_draft(draft_key, draft)
                st.success("Loaded PASS demo dataset.")
                st.rerun()
            else:
                st.warning("Demo dataset matches only model 00-NPX2-100.")

        if demo_cols[1].button("Load Demo FAIL", key=f"{key_prefix}_demo_fail"):
            draft, ok = apply_demo_dataset(draft, selected_model, "official_fail_100uL")
            if ok:
                store_draft(draft_key, draft)
                st.success("Loaded FAIL demo dataset.")
                st.rerun()
            else:
                st.warning("Demo dataset matches only model 00-NPX2-100.")

        if demo_cols[2].button("Load PASS + Show", key=f"{key_prefix}_demo_pass_show"):
            draft, ok = apply_demo_dataset(draft, selected_model, "official_pass_100uL")
            if ok:
                store_draft(draft_key, draft)
                calculate_and_show(draft)
            else:
                st.warning("Demo dataset matches only model 00-NPX2-100.")

        if demo_cols[3].button("Load FAIL + Show", key=f"{key_prefix}_demo_fail_show"):
            draft, ok = apply_demo_dataset(draft, selected_model, "official_fail_100uL")
            if ok:
                store_draft(draft_key, draft)
                calculate_and_show(draft)
            else:
                st.warning("Demo dataset matches only model 00-NPX2-100.")
    else:
        st.markdown(
            '<div class="small-banner">Non-official mode: replicate count is configurable</div>',
            unsafe_allow_html=True
        )

    if st.button(t("reset"), key=f"{key_prefix}_reset"):
        reset_draft(draft_key, mode_key)
        st.rerun()

    operators = [op.operator_name for op in repo.list_operators()]
    operator_options = [""] + operators

    c1, c2, c3, c4 = st.columns(4)
    current_operator = draft["metadata"]["operator_name"]
    draft["metadata"]["operator_name"] = c1.selectbox(
        t("operator"),
        operator_options,
        index=operator_options.index(current_operator) if current_operator in operator_options else 0,
        key=f"{key_prefix}_operator",
    )
    draft["metadata"]["inspection_id"] = c2.text_input("Inspection ID", value=draft["metadata"]["inspection_id"], key=f"{key_prefix}_id")
    draft["metadata"]["pipette_serial_number"] = c3.selectbox("Pipette number", PIPETTE_NUMBERS, index=PIPETTE_NUMBERS.index(draft["metadata"]["pipette_serial_number"]), key=f"{key_prefix}_pipette")
    draft["z_factor"] = c4.number_input("Z factor", min_value=1.0000, max_value=1.0100, value=float(draft["z_factor"]), step=0.0001, format="%.4f", key=f"{key_prefix}_z")

    draft["metadata"]["comments"] = st.text_input("Comments", value=draft["metadata"]["comments"], key=f"{key_prefix}_comments")
    if draft["metadata"].get("is_demo", False):
        st.warning("Demo dataset is active for this form. Saved output will be marked as DEMO / NOT FOR OFFICIAL USE.")

    st.markdown("### Checklist")
    checklist_cols = st.columns(2)
    for idx, k in enumerate(draft["checklist"].keys()):
        with checklist_cols[idx % 2]:
            draft["checklist"][k] = st.checkbox(CHECKLIST_LABELS.get(k, k), value=bool(draft["checklist"][k]), key=f"{key_prefix}_{k}")

    st.markdown("### Measurements")
    labels = ["Lowest point", "Middle point", "Highest point"][:len(point_specs)]
    tabs = st.tabs(labels) if len(point_specs) > 1 else [st.container()]

    for idx, spec in enumerate(point_specs):
        target = tabs[idx] if len(point_specs) > 1 else tabs[0]
        with target:
            st.markdown(f"<div class='point-title'>Point {idx+1} — Vs = {spec.selected_volume_ul} μL</div>", unsafe_allow_html=True)
            stats_cols = st.columns(3)
            stats_cols[0].metric("AC limit", f"{spec.ac_limit_percent}%")
            stats_cols[1].metric("CV limit", f"{spec.cv_limit_percent}%")
            stats_cols[2].metric("Replicates", str(replicate_count))

            rows = []
            entry_cols = st.columns(4)
            for i in range(replicate_count):
                with entry_cols[i % 4]:
                    mass_value = st.text_input(
                        f"Mass {i+1} (mg)",
                        value=str(draft["points"][idx]["masses_mg"][i]) if draft["points"][idx]["masses_mg"][i] != "" else "",
                        key=f"{key_prefix}_p{idx}_m{i}",
                    )
                    draft["points"][idx]["masses_mg"][i] = mass_value
                    try:
                        vi = float(mass_value) * float(draft["z_factor"]) if str(mass_value).strip() else None
                    except Exception:
                        vi = None
                    uploaded = st.file_uploader(f"Photo {i+1}", type=["png", "jpg", "jpeg"], key=f"{key_prefix}_p{idx}_ph{i}")
                    if uploaded is not None:
                        draft["points"][idx]["reading_photos"][i + 1] = {
                            "file_name": uploaded.name,
                            "mime_type": uploaded.type,
                            "image_blob": uploaded.getvalue(),
                        }
                    rows.append(
                        {
                            "Replicate": i + 1,
                            "Mass (mg)": mass_value,
                            "Vi (μL)": "" if vi is None else round(vi, 4),
                            "Photo": "Yes" if (i + 1) in draft["points"][idx]["reading_photos"] else "No",
                        }
                    )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    draft["symptoms"] = st.multiselect("Optional symptoms", SYMPTOM_OPTIONS, default=draft["symptoms"], key=f"{key_prefix}_symptoms")
    st.markdown('<div class="manual-box"><strong>Method notes</strong><br>' + "<br>".join(f"• {note}" for note in HELP_NOTES) + "</div>", unsafe_allow_html=True)

    store_draft(draft_key, draft)

    if st.button(t("show_results"), key=f"{key_prefix}_calc", type="primary", use_container_width=True):
        calculate_and_show(draft)


def render_results(repo):
    result = get_last_result()

    if not result:
        st.info("No current result.")
        return

    current_id = getattr(result.metadata, "inspection_id", None)
    if st.session_state.get("active_result_id") != current_id:
        st.session_state["active_result_id"] = current_id
        for key in ("saved_success_message", "save_error_message", "just_saved_key", "saved_key"):
            st.session_state.pop(key, None)

    render_results_block(result, repo=repo, allow_save=True)

def render_dashboard(repo):
    rows = repo.list_inspections()
    latest = {}
    for r in rows:
        prev = latest.get(r.pipette_serial_number)
        if prev is None or (r.created_at, r.id) > (prev.created_at, prev.id):
            latest[r.pipette_serial_number] = r

    st.subheader(t("dashboard"))
    st.markdown(
        "<div class='compact-head compact-grid'><div>Pipette</div><div>Inspection ID</div><div>Operator</div><div>Mode</div><div>Status</div><div>Created</div><div></div><div></div></div>",
        unsafe_allow_html=True,
    )

    for pipette in PIPETTE_NUMBERS:
        row = latest.get(pipette)
        if row is None:
            st.markdown(
                f"<div class='compact-row compact-grid'><div><strong>{pipette}</strong></div><div>-</div><div>-</div><div>-</div><div><span class='status-pill pill-neutral'>NO INSPECTION</span></div><div>-</div><div></div><div></div></div>",
                unsafe_allow_html=True,
            )
        else:
            status_label, status_type = get_saved_row_status(repo, row)
            status_html = render_status_pill(status_label, status_type)
            st.markdown(
                f"<div class='compact-row compact-grid'><div><strong>{pipette}</strong></div><div>{row.inspection_id}</div><div>{row.operator_name or '-'}</div><div>{row.mode}</div><div>{status_html}</div><div>{row.created_at.strftime('%Y-%m-%d %H:%M:%S')}</div><div></div><div></div></div>",
                unsafe_allow_html=True,
            )


def render_history(repo):
    st.subheader(t("history"))
    rows = repo.list_inspections()
    if not rows:
        st.info("No saved inspections.")
        return

    st.markdown("<div class='compact-head compact-grid'><div>DB ID</div><div>Inspection ID</div><div>Operator</div><div>Pipette</div><div>Mode</div><div>Status</div><div>Open</div><div>Delete</div></div>", unsafe_allow_html=True)

    for row in rows:
        cols = st.columns([0.7, 2.4, 1.6, 0.8, 0.8, 1.2, 1.0, 1.0])
        cols[0].markdown(str(row.id))
        cols[1].markdown(str(row.inspection_id))
        cols[2].markdown(str(row.operator_name or "-"))
        cols[3].markdown(str(row.pipette_serial_number))
        cols[4].markdown(str(row.mode))
        cols[5].markdown(history_status_pill(repo, row), unsafe_allow_html=True)

        if cols[6].button("Open", key=f"open_{row.id}", use_container_width=True):
            set_selected_history_id(row.id)
            set_page(t("history"))
            st.rerun()

        if is_admin():
            if cols[7].button("Delete", key=f"delete_{row.id}", use_container_width=True):
                repo.delete_inspection(row.id)
                if get_selected_history_id() == row.id:
                    set_selected_history_id(None)
                st.success(f"Deleted inspection DB ID {row.id}")
                st.rerun()
        else:
            cols[7].markdown("-")

    selected_id = get_selected_history_id()
    if selected_id:
        record = repo.get_inspection(selected_id)
        if record:
            st.markdown("### Saved inspection review")
            render_results_block(build_history_result(record), repo=None, allow_save=False)


def run_app():
    st.set_page_config(page_title="Nichipet QC Inspector", page_icon="🧪", layout="wide")
    init_app_state()
    inject_css()

    st.markdown(
        """
        <style>
        .result-metric-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(180px, 1fr));
            gap: 12px;
            margin: 10px 0 14px 0;
        }
        .result-metric-card {
            background: linear-gradient(135deg, #ffffff 0%, #f8fbfc 100%);
            border: 1px solid rgba(15, 79, 56, 0.10);
            border-radius: 14px;
            padding: 14px 16px;
            box-shadow: 0 6px 16px rgba(0,0,0,0.04);
        }
        .result-metric-card.green {
            background: linear-gradient(135deg, #f6fcf8 0%, #edf8f1 100%);
        }
        .result-metric-card.red {
            background: linear-gradient(135deg, #fff8f8 0%, #fff0f0 100%);
        }
        .result-metric-card.gold {
            background: linear-gradient(135deg, #fffdf6 0%, #fff8e8 100%);
        }
        .result-metric-title {
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #6a7f75;
            margin-bottom: 10px;
            font-weight: 800;
        }
        .result-metric-pair {
            display: flex;
            justify-content: space-between;
            gap: 14px;
        }
        .result-metric-item {
            flex: 1;
        }
        .result-metric-item .label {
            font-size: 0.76rem;
            color: #6c8478;
            margin-bottom: 4px;
        }
        .result-metric-item .value {
            font-size: 1.75rem;
            font-weight: 800;
            color: #17392b;
            line-height: 1.05;
        }
        .result-metric-item .value.small {
            font-size: 1.45rem;
        }
        .metric-decision-card {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 88px;
        }
        .status-pill.lg {
            font-size: 0.92rem;
            padding: 0.45rem 1rem;
            min-width: 84px;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    create_database()
    ensure_auth_state()

    session_factory = get_session_factory()
    with session_factory() as session:
        seed_models(session)
        repo = InspectionRepository(session)
        user_repo = UserRepository(session)

        if not st.session_state["logged_in"]:
            render_brand_header()
            render_login(user_repo)
            return

        render_brand_header()

        base_pages = [
            t("dashboard"),
            t("official"),
            t("practice"),
            t("routine"),
            t("results"),
            t("settings"),
        ]
        pages = base_pages + [t("history")] if is_admin() else base_pages

        if "nav_radio" not in st.session_state or st.session_state["nav_radio"] not in pages:
            st.session_state["nav_radio"] = t("dashboard")

        nav_override = st.session_state.pop("nav_override", None)
        if nav_override in pages:
            st.session_state["nav_radio"] = nav_override

        st.sidebar.markdown(f"**User:** {st.session_state.get('username', '-')}")
        st.sidebar.markdown(f"**Role:** {st.session_state.get('role', '-')}")

        if st.sidebar.button("Logout"):
            logout()

        st.sidebar.radio("Navigation", pages, key="nav_radio")
        page = st.session_state["nav_radio"]

        if page == t("dashboard"):
            render_dashboard(repo)
        elif page == t("official"):
            render_mode_page(repo, "official", "official_draft", official_mode=True)
        elif page == t("practice"):
            render_mode_page(repo, "practice", "practice_draft", official_mode=False)
        elif page == t("routine"):
            render_mode_page(repo, "routine", "routine_draft", routine_mode=True)
        elif page == t("results"):
            render_results(repo)
        elif page == t("history"):
            if is_admin():
                render_history(repo)
            else:
                st.error("You do not have permission to access History.")
        elif page == t("settings"):
            render_settings(repo, user_repo)
