import streamlit as st
from pyairtable import Api
from datetime import datetime

# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(page_title="Participant Home", page_icon="🧭", layout="wide")

# -----------------------------
# Airtable configuration
# -----------------------------
AIRTABLE_CONFIG = {
    "base_id": "applJyRTlJLvUEDJs",
    "api_key": "patJHZQyID8nmSaxh.1bcf08f100bd723fd85d67eff8534a19f951b75883d0e0ae4cc49743a9fb3131",
}

def get_airtable_api():
    return Api(AIRTABLE_CONFIG["api_key"])

def get_airtable_table(table_name: str):
    api = get_airtable_api()
    return api.table(AIRTABLE_CONFIG["base_id"], table_name)

# -----------------------------
# Utilities
# -----------------------------
def _parse_iso(dt_val):
    """Return naive datetime from ISO string or pass-through if already datetime."""
    try:
        if isinstance(dt_val, str):
            s = dt_val.replace("Z", "").replace("+00:00", "")
            dt = datetime.fromisoformat(s)
        else:
            dt = dt_val
        if dt and getattr(dt, "tzinfo", None) is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        return None

def _safe_formula_value(val):
    """Wrap strings in quotes for Airtable formula; leave numbers/plain as-is."""
    if isinstance(val, (int, float)):
        return str(val)
    # escape double quotes
    s = str(val).replace('"', r'\"')
    return f'"{s}"'

# -----------------------------
# Data access
# -----------------------------
def get_participant_events(user_id):
    """
    Read event_participants where participant_id == user_id.
    Join to events by numeric {id} OR by record id (rec...), then sort by start_date ASC.
    """
    try:
        att_table = get_airtable_table("event_participants")
        formula = f"{{participant_id}} = {_safe_formula_value(user_id)}"
        attendances = att_table.all(formula=formula)

        rec_ids = []        # event record IDs like recxxxx
        numeric_ids = []    # events.{id} numeric

        for rec in attendances:
            ev = rec.get("fields", {}).get("event_id")
            # handle list / scalar / str / number
            values = ev if isinstance(ev, list) else [ev]
            for v in values:
                if isinstance(v, str) and v.lower().startswith("rec"):
                    rec_ids.append(v)
                elif isinstance(v, (int, float)):
                    numeric_ids.append(int(v))
                elif isinstance(v, str) and v.isdigit():
                    numeric_ids.append(int(v))

        events = []
        ev_table = get_airtable_table("events")

        # 1) fetch by record ids
        for rid in rec_ids:
            try:
                er = ev_table.get(rid)
                f = er.get("fields", {})
                events.append({
                    "record_id": er["id"],
                    "name": f.get("name", ""),
                    "description": f.get("description", ""),
                    "type": f.get("type", ""),
                    "location_name": f.get("location_name", ""),
                    "detailed_address": f.get("detailed_address", ""),
                    "start_date": f.get("start_date", ""),
                    "end_date": f.get("end_date", ""),
                    "is_visible": f.get("is_visible", False),
                    "host_id": f.get("host_id", ""),
                    "capacity": f.get("capacity", 0),
                })
            except Exception:
                continue

        # 2) fetch by numeric {id}
        for n in numeric_ids:
            try:
                rows = ev_table.all(formula=f"{{id}} = {n}", max_records=1)
                if rows:
                    er = rows[0]
                    f = er.get("fields", {})
                    events.append({
                        "record_id": er["id"],
                        "name": f.get("name", ""),
                        "description": f.get("description", ""),
                        "type": f.get("type", ""),
                        "location_name": f.get("location_name", ""),
                        "detailed_address": f.get("detailed_address", ""),
                        "start_date": f.get("start_date", ""),
                        "end_date": f.get("end_date", ""),
                        "is_visible": f.get("is_visible", False),
                        "host_id": f.get("host_id", ""),
                        "capacity": f.get("capacity", 0),
                    })
            except Exception:
                continue

        # sort by start_date ASC
        def keyfn(ev):
            dt = _parse_iso(ev.get("start_date"))
            return dt or datetime.max
        events.sort(key=keyfn)
        return events

    except Exception as e:
        st.error(f"Etkinlikler yüklenirken hata oluştu: {e}")
        return []


# -----------------------------
# UI helpers
# -----------------------------
def render_event_card(ev):
    with st.container():
        st.markdown("---")
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"### {ev['name']}")
            st.markdown(f"**Tür:** {ev.get('type','')}")
            st.markdown(f"**Mekan:** {ev.get('location_name','')}")
            st.markdown(f"**Adres:** {ev.get('detailed_address','')}")
            try:
                sd = _parse_iso(ev["start_date"])
                ed = _parse_iso(ev["end_date"])
                if sd: st.markdown(f"**Başlangıç:** {sd.strftime('%d/%m/%Y %H:%M')}")
                if ed: st.markdown(f"**Bitiş:** {ed.strftime('%d/%m/%Y %H:%M')}")
            except Exception:
                st.markdown(f"**Başlangıç:** {ev.get('start_date','')}")
                st.markdown(f"**Bitiş:** {ev.get('end_date','')}")
        with c2:
            st.markdown(f"**Host ID:** {ev.get('host_id','')}")
            st.markdown(f"**Kapasite:** {ev.get('capacity',0)}")
            st.markdown(f"**Event Kayıt ID:** {ev.get('record_id','')}")

# -----------------------------
# Page
# -----------------------------
def main():
    st.title("🏠 Ana Sayfa (Katılımcı)")

    # Persist current user id (like host_id in host app)
    if "current_user_id" not in st.session_state:
        st.session_state.current_user_id = 2000

    user_id = st.sidebar.number_input(
        "User ID",
        min_value=1000, max_value=9999,
        value=st.session_state.current_user_id,
        help="Kullanıcı kimliğinizi değiştirerek test edebilirsiniz.",
        key="user_id_input",
    )
    st.session_state.current_user_id = user_id

    # Top actions
    top = st.container()
    with top:
        c1, c2 = st.columns([1, 3])
        with c1:
            if st.button("🎫 Kod ile Etkinliğe Katıl", type="primary", use_container_width=True):
                st.session_state.participant_user_id = user_id
                st.switch_page("pages/join_by_code.py")
        with c2:
            st.info("🗓️ **My Agenda** — Buradan takvim görünümüne gidecek (henüz bağlanmadı).")

    st.markdown("---")

    # Section: Your events (from event_attendance)
    st.header("🎟️ Etkinliklerin")
    my_events = get_participant_events(user_id)
    if my_events:
        for ev in my_events:
            render_event_card(ev)
    else:
        st.info("Henüz kayıtlı bir etkinliğin yok.")

    st.markdown("---")

    # Section: Friends are attending (empty for now)
    st.header("👥 Arkadaşlarının Katıldığı Etkinlikler")
    st.caption("Bu bölüm daha sonra doldurulacak.")
    st.empty()

    st.markdown("---")

    # Section: Events You May Like (empty for now)
    st.header("⭐ Hoşuna Gidebilecek Etkinlikler")
    st.caption("Öneri motoru eklenecek.")
    st.empty()

    st.markdown("---")

    # Section: Challenges & Achievements (empty for now)
    st.header("🏆 Challenges & Achievements")
    st.caption("Oyunlaştırma bileşenleri burada gösterilecek.")
    st.empty()

    st.markdown("---")
    if st.button("🔄 Yenile", type="secondary", use_container_width=True):
        st.rerun()

if __name__ == "__main__":
    main()
