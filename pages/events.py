import streamlit as st
from pyairtable import Api
from datetime import datetime

st.set_page_config(page_title="Events", page_icon="🗓️", layout="wide")

AIRTABLE_CONFIG = {
    "base_id": "applJyRTlJLvUEDJs",
    "api_key": "patJHZQyID8nmSaxh.1bcf08f100bd723fd85d67eff8534a19f951b75883d0e0ae4cc49743a9fb3131",
}

def api(): return Api(AIRTABLE_CONFIG["api_key"])
def t(name): return api().table(AIRTABLE_CONFIG["base_id"], name)

def parse_iso(s):
    try:
        s = (s or "").replace("Z", "").replace("+00:00", "")
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None)
    except Exception:
        return None

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

def user_participation_sets(user_id: int):
    """Return (rec_id_set, numeric_id_set) for events the user already joined."""
    recs = t("event_participants").all(formula=f"{{participant_id}} = {user_id}")
    rec_ids, numeric_ids = set(), set()
    for r in recs:
        val = r.get("fields", {}).get("event_id")
        items = val if isinstance(val, list) else [val]
        for v in items:
            if isinstance(v, str) and v.lower().startswith("rec"):
                rec_ids.add(v)
            elif isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
                numeric_ids.add(int(v))
    return rec_ids, numeric_ids

def load_upcoming_visible_events():
    # Only visible + start_date in the future
    formula = "AND({is_visible} = 1, IS_AFTER({start_date}, NOW()))"
    # IMPORTANT: pyairtable wants sort as list[str]
    rows = t("events").all(formula=formula, sort=["start_date"])
    events = []
    for r in rows:
        f = r.get("fields", {})
        events.append({
            "record_id": r["id"],
            "numeric_id": f.get("id"),
            "name": f.get("name",""),
            "description": f.get("description",""),
            "type": f.get("type",""),
            "location_name": f.get("location_name",""),
            "detailed_address": f.get("detailed_address",""),
            "start_date": f.get("start_date",""),
            "end_date": f.get("end_date",""),
        })
    # Extra client-side safety
    events.sort(key=lambda e: parse_iso(e.get("end_date")) or datetime.max)
    return events

def render_event_card(ev, user_id, already_numeric_ids, already_rec_ids):
    # Hide if user already participating
    if (ev.get("numeric_id") and ev["numeric_id"] in already_numeric_ids) or (ev.get("record_id") in already_rec_ids):
        return

    with st.container():
        st.markdown("---")
        c1, c2 = st.columns([3,1])
        with c1:
            st.markdown(f"### {ev['name']}")
            if ev.get("description"): st.caption(ev["description"])
            if ev.get("location_name"): st.write(f"**Mekan:** {ev['location_name']}")
            if ev.get("detailed_address"): st.write(f"**Adres:** {ev['detailed_address']}")
            sd = parse_iso(ev.get("start_date")); ed = parse_iso(ev.get("end_date"))
            if sd: st.write(f"**Başlangıç:** {sd.strftime('%d/%m/%Y %H:%M')}")
            if ed: st.write(f"**Bitiş:** {ed.strftime('%d/%m/%Y %H:%M')}")
        with c2:
            if st.button("Evente Katıl", key=f"join_{ev['record_id']}", use_container_width=True):
                try:
                    payload = {
                        "participant_id": int(user_id),
                        # prefer numeric id; fallback to record id if that's what your schema expects
                        "event_id": int(ev["numeric_id"]) if ev.get("numeric_id") is not None else ev["record_id"],
                    }
                    t("event_participants").create(payload)
                    st.success("Etkinliğe katıldın!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Katılım oluşturulurken hata: {e}")

def main():
    st.title("🗓️ Yaklaşan Etkinlikler")
    navbar()

    # Let user confirm/change id here, too
    current_id = get_user_id()
    new_id = st.sidebar.number_input("User ID", value=int(current_id), step=1, format="%d")
    st.session_state.current_user_id = int(new_id)
    user_id = int(new_id)

    already_rec_ids, already_numeric_ids = user_participation_sets(user_id)
    upcoming = load_upcoming_visible_events()

    if not upcoming:
        st.info("Yakında bir etkinlik görünmüyor.")
        return

    shown = 0
    for ev in upcoming:
        # Only show if not already participating
        if (ev.get("numeric_id") in already_numeric_ids) or (ev.get("record_id") in already_rec_ids):
            continue
        render_event_card(ev, user_id, already_numeric_ids, already_rec_ids)
        shown += 1

    if shown == 0:
        st.info("Katılabileceğin yeni bir etkinlik yok gibi görünüyor. 🌿")

if __name__ == "__main__":
    main()
