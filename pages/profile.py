import streamlit as st
from pyairtable import Api
from datetime import datetime

st.set_page_config(page_title="Profil", page_icon="👤", layout="wide")

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
    return f"\"{str(val).replace('\"', '\\\"')}\""

def render_navbar():
    with st.container():
        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            st.page_link("app.py", label="🏠 Ana Sayfa")
        with c2:
            st.page_link("pages/join_by_code.py", label="🎫 Koda Katıl")
        with c3:
            st.page_link("pages/profile.py", label="👤 Profil")
        st.markdown("---")

def get_profile(user_id):
    """Read from 'participants' table: show name + description (no numeric id shown)."""
    try:
        tbl = get_airtable_table("participants")
        recs = tbl.all(formula=f"{{id}} = {user_id}", max_records=1)
        if not recs:
            recs = tbl.all(formula=f"{{id}} = {_safe_formula_value(user_id)}", max_records=1)
        if recs:
            f = recs[0].get("fields", {})
            return {
                "display_name": f.get("name") or f.get("username") or "",
                "description": f.get("description") or f.get("bio") or "",
                "avatar_url": (f.get("avatar_url") or ""),
            }
    except Exception:
        pass
    return {"display_name": "", "description": "", "avatar_url": ""}

def get_user_events(user_id):
    """Read event_participants for this user, then fetch events by numeric {id}."""
    try:
        parts = get_airtable_table("event_participants")
        events_tbl = get_airtable_table("events")
        rows = parts.all(formula=f"{{participant_id}} = {user_id}")
        event_ids = []
        for r in rows:
            ev = r.get("fields", {}).get("event_id")
            vals = ev if isinstance(ev, list) else [ev]
            for v in vals:
                if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
                    event_ids.append(int(v))
        events = []
        for eid in event_ids:
            recs = events_tbl.all(formula=f"{{id}} = {eid}", max_records=1)
            if recs:
                er = recs[0]; f = er.get("fields", {})
                events.append({
                    "name": f.get("name",""),
                    "start_date": f.get("start_date",""),
                    "end_date": f.get("end_date",""),
                    "location_name": f.get("location_name",""),
                })
        events.sort(key=lambda e: _parse_iso(e.get("start_date")) or datetime.max)
        return events
    except Exception:
        return []

def grid_events(events, cols=3):
    if not events:
        st.info("Henüz etkinlik yok.")
        return
    for i in range(0, len(events), cols):
        cols_list = st.columns(cols)
        for j, col in enumerate(cols_list):
            idx = i + j
            if idx >= len(events): break
            ev = events[idx]
            with col:
                st.container(border=True)
                st.markdown(f"**{ev['name']}**")
                sd = _parse_iso(ev.get("start_date"))
                ed = _parse_iso(ev.get("end_date"))
                if sd: st.caption(sd.strftime("%d/%m/%Y %H:%M"))
                if ed: st.caption(f"— {ed.strftime('%d/%m/%Y %H:%M')}")
                if ev.get("location_name"):
                    st.caption(ev["location_name"])

def main():
    user_id = st.session_state.get("current_user_id") or st.session_state.get("participant_user_id") or 2000
    render_navbar()

    prof = get_profile(user_id)
    display_name = prof["display_name"] or "Kullanıcı"
    description  = prof["description"]

    st.markdown("## 👤 Profil")
    header = st.container()
    with header:
        a, b = st.columns([1,3])
        with a:
            if prof["avatar_url"]:
                st.image(prof["avatar_url"], width=120)
            else:
                st.markdown("<div style='font-size:80px;line-height:1;'>🧑</div>", unsafe_allow_html=True)
        with b:
            st.markdown(f"### {display_name}")
            sub_a, sub_b, sub_c, sub_d = st.columns([1,1,1,1])
            events = get_user_events(user_id)
            with sub_a: st.metric("Etkinlik", len(events))
            with sub_b: st.metric("Takipçi", 0)
            with sub_c: st.metric("Takip", 0)
            with sub_d: st.button("Profili Düzenle", use_container_width=True, disabled=True)
            if description:
                st.caption(description)

    st.markdown("---")

    st.subheader("🏆 Başarılar")
    st.caption("Başarı rozetleri burada görünecek (yakında).")
    chip_row = st.columns(6)
    for i in range(6):
        with chip_row[i]:
            st.button(f"Rozet {i+1}", disabled=True, use_container_width=True)

    st.markdown("---")

    # Tabs: Events, Photos/Videos, Saved
    tab_events, tab_media, tab_saved = st.tabs(["🗂️ Etkinlikler", "📷 Fotoğraf/Videolar", "🔖 Kaydedilenler"])
    with tab_events:
        grid_events(events)
    with tab_media:
        st.info("Fotoğraf ve videolar yakında.")
    with tab_saved:
        st.info("Kaydedilenler yakında.")

if __name__ == "__main__":
    main()
