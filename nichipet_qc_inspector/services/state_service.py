import streamlit as st

def init_app_state():
    st.session_state.setdefault("official_draft", None)
    st.session_state.setdefault("practice_draft", None)
    st.session_state.setdefault("routine_draft", None)
    st.session_state.setdefault("last_result", None)
    st.session_state.setdefault("inspection_saved", False)
    st.session_state.setdefault("selected_history_id", None)
    st.session_state.setdefault("lang", "en")
    st.session_state.setdefault("operators_seeded", False)
    st.session_state.setdefault("official_reset_nonce", 0)
    st.session_state.setdefault("practice_reset_nonce", 0)
    st.session_state.setdefault("routine_reset_nonce", 0)
    st.session_state.setdefault("nav_override", None)

def store_draft(draft_key, draft):
    st.session_state[draft_key] = draft

def get_draft(draft_key):
    return st.session_state.get(draft_key)

def set_last_result(result):
    st.session_state["last_result"] = result

def get_last_result():
    return st.session_state.get("last_result")

def _clear_widget_keys_for_prefix(prefix: str):
    keys_to_delete = [k for k in st.session_state.keys() if str(k).startswith(prefix)]
    for k in keys_to_delete:
        del st.session_state[k]

def reset_draft(draft_key, mode_key):
    st.session_state[draft_key] = None
    st.session_state["last_result"] = None
    st.session_state[f"{mode_key}_reset_nonce"] = st.session_state.get(f"{mode_key}_reset_nonce", 0) + 1

    widget_prefix_map = {
        "official": "official_draft_",
        "practice": "practice_draft_",
        "routine": "routine_draft_",
    }
    prefix = widget_prefix_map.get(mode_key)
    if prefix:
        _clear_widget_keys_for_prefix(prefix)

def set_selected_history_id(inspection_id):
    st.session_state["selected_history_id"] = inspection_id

def get_selected_history_id():
    return st.session_state.get("selected_history_id")