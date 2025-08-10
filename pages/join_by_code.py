import streamlit as st
from pyairtable import Api
from datetime import datetime

st.set_page_config(page_title="Kod ile Etkinliğe Katıl", page_icon="🎫", layout="centered")

AIRTABLE_CONFIG = {
    "base_id": "applJyRTlJLvUEDJs",
    "api_key": "patJHZQyID8nmSaxh.1bcf08f100bd723fd85d67eff8534a19f951b75883d0e0ae4cc49743a9fb3131",
}

def get_airtable_api():
    return Api(AIRTABLE_CONFIG["api_key"])

def get_airtable_table(table_name: str):
    return get_airtable_api().table(AIRTABLE_CONFIG["base_id"], table_name)

def _parse_iso(v):
    try:
        if isinstance(v, str):
            v = v.replace("Z", "").replace("+00:00", "")
            dt = datetime.fromisoformat(v)
        else:
            dt = v
        if dt and getattr(dt, "tzinfo", None) is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        return None

def _safe_formula_value(val):
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val).replace('"', '\\"')
    return f'"{s}"'

st.title("🎫 Kod ile Etkinliğe Katıl")

user_id = st.session_state.get("participant_user_id", 2000)
st.write(f"**User ID:** {user_id}")

event_code = st.text_input("Etkinlik Kodu (events tablosu 'id' veya record ID - rec...)")

if st.button("Kaydol", type="primary", use_container_width=True):
    code = event_code.strip()
    if not code:
        st.error("Lütfen bir etkinlik kodu girin.")
        st.stop()

    events_tbl = get_airtable_table("events")
    parts_tbl  = get_airtable_table("event_participants")  # numeric event_id table

    # ---------- Resolve event by rec... or numeric/string {id} ----------
    event_rec = None
    numeric_event_id = None

    if code.lower().startswith("rec"):
        try:
            event_rec = events_tbl.get(code)
            numeric_event_id = event_rec.get("fields", {}).get("id")  # your numeric id
        except Exception:
            event_rec = None

    if event_rec is None:
        candidates = []
        # try numeric
        try:
            numeric_event_id = int(code)
            candidates = events_tbl.all(formula=f"{{id}} = {numeric_event_id}", max_records=1)
        except ValueError:
            # try string equality on {id} as fallback
            candidates = events_tbl.all(formula=f"{{id}} = {_safe_formula_value(code)}", max_records=1)
        if candidates:
            event_rec = candidates[0]

    if event_rec is None or numeric_event_id is None:
        st.error("Geçersiz etkinlik kodu. Lütfen kontrol edin.")
        st.stop()

    f = event_rec.get("fields", {})

    # ---------- end_date must be in the future ----------
    end_dt = _parse_iso(f.get("end_date"))
    if not end_dt:
        st.error("Etkinliğin bitiş tarihi bulunamadı. Lütfen organizatörle iletişime geçin.")
        st.stop()
    if end_dt <= datetime.now():
        st.error("Bu etkinlik sona ermiş. Kayıt yapılamaz.")
        st.stop()

    # ---------- uniqueness: participant_id + numeric event_id ----------
    uniq_formula = (
        f"AND("
        f"{{participant_id}} = {_safe_formula_value(user_id)}, "
        f"{{event_id}} = {numeric_event_id}"
        f")"
    )
    try:
        existing = parts_tbl.all(formula=uniq_formula, max_records=1)
    except Exception as e:
        st.error(f"Kayıt kontrolünde hata: {e}")
        st.stop()

    if existing:
        st.error("Zaten bu etkinliğe kayıtlısınız.")
        st.stop()

    # ---------- create registration (numeric event_id) ----------
    try:
        parts_tbl.create({
            "participant_id": user_id,
            "event_id": numeric_event_id,   # plain integer
        })
        st.success("Kaydın alındı! Ana sayfaya yönlendiriliyorsun…")
        st.switch_page("app.py")  # back to home
    except Exception as e:
        st.error(f"Kayıt sırasında hata: {e}")
