import streamlit as st
from pyairtable import Api

st.set_page_config(page_title="Join by Code", page_icon="🎫", layout="wide")

AIRTABLE_CONFIG = {
    "base_id": "applJyRTlJLvUEDJs",
    "api_key": "patJHZQyID8nmSaxh.1bcf08f100bd723fd85d67eff8534a19f951b75883d0e0ae4cc49743a9fb3131",
}

def api(): return Api(AIRTABLE_CONFIG["api_key"])
def t(name): return api().table(AIRTABLE_CONFIG["base_id"], name)

def navbar():
    c1, c2, c3, c4 = st.columns([1,1,1,1])
    with c1: st.page_link("app.py", label="🏠 Ana Sayfa")
    with c2: st.page_link("pages/events.py", label="🗓️ Events")
    with c3: st.page_link("pages/join_by_code.py", label="🎫 Koda Katıl")
    with c4: st.page_link("pages/profile.py", label="👤 Profil")
    st.markdown("---")

def get_user_id():
    if "current_user_id" not in st.session_state:
        st.session_state.current_user_id = 2000
    return int(st.session_state.current_user_id)

def ensure_event_by_code(code: int):
    """Fetch a single event by its numeric {id} code (returns Airtable row)."""
    try:
        rows = t("events").all(formula=f"{{id}} = {int(code)}", max_records=1)
        return rows[0] if rows else None
    except Exception:
        return None

def already_joined(participant_id: int, event_numeric_id: int) -> bool:
    """Check if a row exists in event_participants for this user & event."""
    try:
        formula = f"AND({{participant_id}} = {int(participant_id)}, {{event_id}} = {int(event_numeric_id)})"
        rows = t("event_participants").all(formula=formula, max_records=1)
        return len(rows) > 0
    except Exception:
        return False

def create_participant_notification_from_row(event_row: dict, participant_id: int):
    """Insert participant_notifications for event start."""
    f = event_row.get("fields", {})
    if f.get("id") is None:
        return
    payload = {
        "participant_id": int(participant_id),
        "event_id": int(f["id"]),
        "type": "event_start",
        "message": f"{f.get('name','Etkinlik')} Başlıyor !!",
        "notify_date": f.get("start_date", ""),
        "is_active": True,
        "created_by": f.get("host_id"),
    }
    try:
        t("participant_notifications").create(payload)
    except Exception as e:
        # non-fatal for flow
        st.warning(f"Bildirim oluşturulamadı: {e}")

# ---------- NEW: upsert agenda_items on join by code ----------
def _upsert_agenda_item_for_event_row(event_row: dict, participant_id: int):
    """
    Ensure an agenda_items row exists for this participant & event.
    Uses the event Airtable row directly; includes event_id.
    """
    try:
        f = event_row.get("fields", {}) if event_row else {}
        eid = f.get("id")
        if eid is None:
            return

        # Check existing agenda item for (participant_id, event_id)
        formula = f"AND({{participant_id}} = {int(participant_id)}, {{event_id}} = {int(eid)})"
        existing = t("agenda_items").all(formula=formula, max_records=1)

        payload = {
            "participant_id": int(participant_id),
            "event_id": int(eid),
            "name": f.get("name","") or "Etkinlik",
            "start_date": f.get("start_date",""),
            "end_date": f.get("end_date",""),
        }
        if f.get("description"):      payload["description"] = f["description"]
        if f.get("type"):             payload["type"] = f["type"]
        if f.get("location_name"):    payload["location"] = f["location_name"]
        if f.get("detailed_address"): payload["detailed_address"] = f["detailed_address"]

        if existing:
            t("agenda_items").update(existing[0]["id"], payload)
        else:
            t("agenda_items").create(payload)

    except Exception as e:
        st.warning(f"Agenda güncellenemedi: {e}")

def redirect_to_event_app(ev_row: dict):
    """Set session context and go to event_app page."""
    f = ev_row.get("fields", {})
    st.session_state.selected_event_record_id = ev_row["id"]
    st.session_state.selected_event_numeric_id = f.get("id")
    st.switch_page("pages/event_app.py")

def main():
    st.title("🎫 Koda Katıl")
    navbar()

    # user id
    current_id = get_user_id()
    new_id = st.sidebar.number_input("User ID", value=int(current_id), step=1, format="%d")
    st.session_state.current_user_id = int(new_id)
    participant_id = int(new_id)

    code = st.text_input("Etkinlik Kodu (numeric `events.id`)", placeholder="Örn: 1024")

    if st.button("Devam", type="primary"):
        if not code or not code.isdigit():
            st.error("Lütfen geçerli bir sayısal kod girin.")
            return

        ev = ensure_event_by_code(int(code))
        if not ev:
            st.error("Etkinlik bulunamadı.")
            return

        f = ev.get("fields", {})
        event_numeric_id = f.get("id")
        if event_numeric_id is None:
            st.error("Etkinlik numarası bulunamadı (events.id).")
            return

        # If already joined -> inform and redirect
        if already_joined(participant_id, int(event_numeric_id)):
            # Even if already joined, make sure agenda item exists for this event
            _upsert_agenda_item_for_event_row(ev, participant_id)
            st.info("Bu etkinliğe zaten katıldın, yönlendiriliyorsun…")
            redirect_to_event_app(ev)
            return

        # Auto-join + notification + agenda upsert + redirect
        try:
            # Create participation
            t("event_participants").create({
                "participant_id": participant_id,
                "event_id": int(event_numeric_id),
            })
            # Create notification
            create_participant_notification_from_row(ev, participant_id)
            # NEW: Upsert into agenda_items (with event_id)
            _upsert_agenda_item_for_event_row(ev, participant_id)

            st.success("Etkinliğe katıldın! Yönlendiriliyorsun…")
            redirect_to_event_app(ev)
        except Exception as e:
            st.error(f"Katılım oluşturulurken hata: {e}")

if __name__ == "__main__":
    main()
