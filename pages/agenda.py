import streamlit as st
from pyairtable import Api
from datetime import datetime, timedelta, date, time
import calendar

st.set_page_config(page_title="My Agenda", page_icon="🗓️", layout="wide")

# ---------- Airtable ----------
AIRTABLE_CONFIG = {
    "base_id": "applJyRTlJLvUEDJs",
    "api_key": "patJHZQyID8nmSaxh.1bcf08f100bd723fd85d67eff8534a19f951b75883d0e0ae4cc49743a9fb3131",
}
TABLE_NAME = "agenda_items"          # change to "event_items" if you renamed it
TABLE_NOTES = "agenda_item_notes"    # fields: id (auto), agenda_item_id (number), note (long text), rank (number)

def get_airtable_api(): return Api(AIRTABLE_CONFIG["api_key"])
def get_airtable_table(name: str): return get_airtable_api().table(AIRTABLE_CONFIG["base_id"], name)

# ---------- Utils ----------
def _parse_iso(v):
    try:
        if isinstance(v, str):
            v = v.replace("Z","").replace("+00:00","")
            out = datetime.fromisoformat(v)
        else:
            out = v
        if out and getattr(out, "tzinfo", None) is not None:
            out = out.replace(tzinfo=None)
        return out
    except Exception:
        return None

def _safe_formula_value(val):
    if isinstance(val, (int, float)): return str(val)
    return f"\"{str(val).replace('\"','\\\"')}\""

def overlaps_window(s, e, win_s, win_e):
    s = s or e
    e = e or s
    if not s and not e: return False
    return (s <= win_e) and (e >= win_s)

def render_navbar():
    with st.container():
        c1, c2, c3, c4 = st.columns([1,1,1,1])
        with c1: st.page_link("app.py", label="🏠 Ana Sayfa")
        with c2: st.page_link("pages/join_by_code.py", label="🎫 Koda Katıl")
        with c3: st.page_link("pages/profile.py", label="👤 Profil")
        with c4: st.page_link("pages/agenda.py", label="🗓️ My Agenda")
        st.markdown("---")

# ---------- Data (only from agenda_items / event_items) ----------
def get_user_items(user_id: int):
    try:
        tbl = get_airtable_table(TABLE_NAME)
    except Exception:
        return []
    recs = tbl.all(formula=f"{{participant_id}} = {_safe_formula_value(user_id)}")
    items = []
    for r in recs:
        f = r.get("fields", {})
        items.append({
            "record_id": r.get("id"),           # Airtable record id
            "numeric_id": f.get("id"),          # <-- IMPORTANT: your numeric AutoNumber field on agenda_items
            "key": f"item_{r.get('id')}",
            "title": f.get("name",""),
            "description": f.get("description",""),
            "type": f.get("type",""),
            "location": f.get("location",""),
            "detailed_address": f.get("detailed_address",""),
            "start": _parse_iso(f.get("start_date")),
            "end": _parse_iso(f.get("end_date")),
            "notify": bool(f.get("notify", False)),
            "minutes_to_notify": f.get("minutes_to_notify"),
        })
    return items

def find_overlapping(items, win_start: datetime, win_end: datetime):
    return [it for it in items if overlaps_window(it.get("start"), it.get("end"), win_start, win_end)]

# ---------- Notes helpers ----------
def fetch_numeric_id_for_record(record_id: str) -> int | None:
    """Get the agenda item's numeric 'id' field (AutoNumber) using its record_id."""
    try:
        rec = get_airtable_table(TABLE_NAME).get(record_id)
        return rec.get("fields", {}).get("id")  # numeric
    except Exception:
        return None

def load_notes_for_agenda_numeric_id(agenda_numeric_id: int):
    """Return list of notes for agenda item (sorted by rank asc)."""
    try:
        tbl = get_airtable_table(TABLE_NOTES)
        recs = tbl.all(formula=f"{{agenda_item_id}} = {int(agenda_numeric_id)}")
        notes = []
        for r in recs:
            f = r.get("fields", {})
            notes.append({
                "record_id": r.get("id"),
                "note": f.get("note",""),
                "rank": int(f.get("rank", 0) or 0),
            })
        notes.sort(key=lambda x: x["rank"])
        return notes
    except Exception:
        return []

def ensure_notes_state(state_key_prefix: str, agenda_numeric_id: int):
    """Load notes into session once per agenda item; keep editable state."""
    loaded_key = f"{state_key_prefix}_loaded_for"
    list_key = f"{state_key_prefix}_list"

    if st.session_state.get(loaded_key) != agenda_numeric_id:
        notes = load_notes_for_agenda_numeric_id(agenda_numeric_id)
        st.session_state[list_key] = notes if notes else [{"record_id": None, "note": "", "rank": 1}]
        st.session_state[loaded_key] = agenda_numeric_id

def render_notes_editor(state_key_prefix: str, allow_add: bool = True):
    """Editable list of notes stored in session. Returns current list."""
    list_key = f"{state_key_prefix}_list"
    notes = st.session_state.get(list_key, [{"record_id": None, "note": "", "rank": 1}])

    st.subheader("📝 Notlar")
    for i in range(len(notes)):
        row = notes[i]
        c1, c2 = st.columns([4,1])
        row["note"] = c1.text_area(f"Not {i+1}", value=row.get("note",""), key=f"{state_key_prefix}_note_{i}", height=80)
        row["rank"] = int(c2.number_input("Sıra", min_value=0, step=1,
                                          value=int(row.get("rank", i+1)),
                                          key=f"{state_key_prefix}_rank_{i}"))
        # soft delete button (immediate remove from UI)
        del_col = st.columns([1,5])[0]
        if del_col.button("Sil", key=f"{state_key_prefix}_del_{i}"):
            notes.pop(i)
            st.session_state[list_key] = notes if notes else [{"record_id": None, "note": "", "rank": 1}]
            st.experimental_rerun()

        st.markdown("---")

    if allow_add and st.button("➕ Yeni Not Ekle", key=f"{state_key_prefix}_add"):
        notes.append({"record_id": None, "note": "", "rank": (max([n.get('rank',0) or 0 for n in notes]) + 1) if notes else 1})
        st.session_state[list_key] = notes
        st.experimental_rerun()

    st.session_state[list_key] = notes
    return notes

def save_notes_for_agenda_numeric_id(agenda_numeric_id: int, notes: list[dict]):
    """Upsert notes: update when record_id exists; create otherwise. Skip empty notes."""
    tbl = get_airtable_table(TABLE_NOTES)
    for n in notes:
        text = (n.get("note") or "").strip()
        if not text:
            continue
        payload = {
            "agenda_item_id": int(agenda_numeric_id),
            "note": text,
            "rank": int(n.get("rank", 0) or 0),
        }
        if n.get("record_id"):
            try:
                tbl.update(n["record_id"], payload)
            except Exception as e:
                st.warning(f"Not güncellenemedi: {e}")
        else:
            try:
                rec = tbl.create(payload)
                n["record_id"] = rec.get("id")
            except Exception as e:
                st.warning(f"Not oluşturulamadı: {e}")

# ---------- Selection helpers ----------
def set_selection(start_dt: datetime, end_dt: datetime, focus_key: str|None=None):
    st.session_state["_agenda_selected"] = {
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "focus": focus_key,
    }

def get_selection():
    sel = st.session_state.get("_agenda_selected")
    if not sel: return None
    return {
        "start": _parse_iso(sel["start"]),
        "end": _parse_iso(sel["end"]),
        "focus": sel.get("focus"),
    }

# ---------- Editor (edit existing; create if empty) ----------
def render_editor(user_id: int, items):
    sel = get_selection()
    if not sel:
        return

    win_start, win_end, focus_key = sel["start"], sel["end"], sel["focus"]
    st.markdown("### ✏️ Kayıt Düzenle / Oluştur")
    st.caption(f"Seçilen aralık: {win_start.strftime('%d/%m/%Y %H:%M')} — {win_end.strftime('%d/%m/%Y %H:%M')}")

    overlapping = find_overlapping(items, win_start, win_end)

    # ============ EDIT path (at least one item in that slot) ============
    if overlapping:
        # pick which record to edit
        default_idx = 0
        if focus_key:
            for idx, it in enumerate(overlapping):
                if it["key"] == focus_key:
                    default_idx = idx
                    break
        labels = [f"{it['title'] or '(Adsız)'} • {it['start'].strftime('%d/%m %H:%M')}" for it in overlapping]
        pick = st.selectbox("Düzenlenecek kayıt", labels, index=default_idx, key="ed_pick")
        picked_item = overlapping[labels.index(pick)]

        # hydrate editor state
        if st.session_state.get("ed_state_for") != picked_item["key"]:
            st.session_state["ed_name"]    = picked_item["title"]
            st.session_state["ed_type"]    = picked_item.get("type","")
            st.session_state["ed_sd"]      = picked_item["start"].date()
            st.session_state["ed_ed"]      = picked_item["end"].date()
            st.session_state["ed_st"]      = picked_item["start"].time()
            st.session_state["ed_et"]      = picked_item["end"].time()
            st.session_state["ed_loc"]     = picked_item.get("location","")
            st.session_state["ed_addr"]    = picked_item.get("detailed_address","")
            st.session_state["ed_desc"]    = picked_item.get("description","")
            st.session_state["ed_notify"]  = bool(picked_item.get("notify"))
            st.session_state["ed_minutes"] = int(picked_item.get("minutes_to_notify") or 30)
            st.session_state["ed_state_for"] = picked_item["key"]

            # load notes for this agenda numeric id (fetch if missing)
            numeric_id = picked_item.get("numeric_id")
            if numeric_id is None:
                numeric_id = fetch_numeric_id_for_record(picked_item["record_id"])
            if numeric_id is not None:
                ensure_notes_state("edit_notes", int(numeric_id))
                st.session_state["edit_notes_numeric_id"] = int(numeric_id)
            else:
                st.warning("Bu kayıt için 'id' (numeric) alanı bulunamadı. Notlar bağlanamayacak.")

        # inputs
        c1, c2 = st.columns([2,1])
        st.session_state["ed_name"] = c1.text_input("Ad (zorunlu)*", value=st.session_state["ed_name"])
        st.session_state["ed_type"] = c2.text_input("Tür (opsiyonel)", value=st.session_state["ed_type"])

        d1, d2 = st.columns(2)
        st.session_state["ed_sd"] = d1.date_input("Başlangıç Tarihi*", value=st.session_state["ed_sd"])
        st.session_state["ed_ed"] = d2.date_input("Bitiş Tarihi*", value=st.session_state["ed_ed"])

        t1, t2 = st.columns(2)
        st.session_state["ed_st"] = t1.time_input("Başlangıç Saati", value=st.session_state["ed_st"])
        st.session_state["ed_et"] = t2.time_input("Bitiş Saati", value=st.session_state["ed_et"])

        l1, l2 = st.columns(2)
        st.session_state["ed_loc"]  = l1.text_input("Konum (opsiyonel)", value=st.session_state["ed_loc"])
        st.session_state["ed_addr"] = l2.text_input("Detaylı Adres (opsiyonel)", value=st.session_state["ed_addr"])

        st.session_state["ed_desc"] = st.text_area("Açıklama / Not (opsiyonel)", value=st.session_state["ed_desc"], height=80)

        n1, n2 = st.columns([1,1])
        st.session_state["ed_notify"] = n1.checkbox("Hatırlat", value=st.session_state["ed_notify"])
        st.session_state["ed_minutes"] = n2.number_input(
            "Kaç dakika önce?", min_value=0, step=5,
            value=int(st.session_state["ed_minutes"]),
            disabled=not st.session_state["ed_notify"]
        )

        # ----- Notes editor (edit mode) -----
        numeric_id_for_notes = st.session_state.get("edit_notes_numeric_id")
        if numeric_id_for_notes is not None:
            notes_now = render_notes_editor("edit_notes", allow_add=True)
        else:
            notes_now = []

        b1, b2, b3 = st.columns([1,1,1])
        save_clicked   = b1.button("Kaydet", type="primary")
        delete_clicked = b2.button("Sil")
        cancel_clicked = b3.button("Vazgeç")

        if cancel_clicked:
            st.session_state.pop("_agenda_selected", None)
            st.session_state["ed_state_for"] = None
            st.experimental_rerun()

        if delete_clicked:
            try:
                get_airtable_table(TABLE_NAME).delete(picked_item["record_id"])
                st.success("Kayıt silindi.")
                st.session_state.pop("_agenda_selected", None)
                st.session_state["ed_state_for"] = None
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Silinemedi: {e}")

        if save_clicked:
            name = st.session_state["ed_name"]
            if not name:
                st.error("Lütfen bir ad girin.")
                return
            start_dt = datetime.combine(st.session_state["ed_sd"], st.session_state["ed_st"])
            end_dt   = datetime.combine(st.session_state["ed_ed"], st.session_state["ed_et"])
            if end_dt < start_dt:
                st.error("Bitiş tarihi başlangıçtan önce olamaz.")
                return

            payload = {
                "participant_id": int(user_id),
                "name": name,
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat(),
            }
            if st.session_state["ed_desc"]:  payload["description"] = st.session_state["ed_desc"]
            if st.session_state["ed_type"]:  payload["type"] = st.session_state["ed_type"]
            if st.session_state["ed_loc"]:   payload["location"] = st.session_state["ed_loc"]
            if st.session_state["ed_addr"]:  payload["detailed_address"] = st.session_state["ed_addr"]
            if st.session_state["ed_notify"]:
                payload["notify"] = True
                payload["minutes_to_notify"] = int(st.session_state["ed_minutes"])
            else:
                payload["notify"] = False
                payload["minutes_to_notify"] = None

            try:
                # 1) Update agenda item
                tbl = get_airtable_table(TABLE_NAME)
                tbl.update(picked_item["record_id"], payload)

                # 2) Re-fetch to get numeric id
                numeric_id = fetch_numeric_id_for_record(picked_item["record_id"])
                if numeric_id is None:
                    st.warning("Güncellendi fakat 'id' alanı bulunamadı; notlar bağlanmadı.")
                else:
                    # 3) Upsert notes
                    save_notes_for_agenda_numeric_id(int(numeric_id), notes_now)

                st.success("Kayıt güncellendi.")
                st.session_state.pop("_agenda_selected", None)
                st.session_state["ed_state_for"] = None
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Kaydedilemedi: {e}")

        return  # edit path ends here

    # ============ CREATE path (slot empty) ============
    st.info("Bu aralıkta kayıt yok. Yeni kayıt oluşturabilirsiniz.")

    # seed create state once
    if "create_state_init" not in st.session_state:
        st.session_state["create_name"] = ""
        st.session_state["create_type"] = ""
        st.session_state["create_sd"] = win_start.date()
        st.session_state["create_ed"] = win_end.date()
        st.session_state["create_st"] = win_start.time()
        st.session_state["create_et"] = win_end.time()
        st.session_state["create_loc"] = ""
        st.session_state["create_addr"] = ""
        st.session_state["create_desc"] = ""
        st.session_state["create_notify"] = False
        st.session_state["create_minutes"] = 30
        st.session_state["create_state_init"] = True
        # notes for creation
        st.session_state["create_notes_list"] = [{"record_id": None, "note": "", "rank": 1}]

    # inputs
    c1, c2 = st.columns([2,1])
    st.session_state["create_name"] = c1.text_input("Ad (zorunlu)*", value=st.session_state["create_name"])
    st.session_state["create_type"] = c2.text_input("Tür (opsiyonel)", value=st.session_state["create_type"])

    d1, d2 = st.columns(2)
    st.session_state["create_sd"] = d1.date_input("Başlangıç Tarihi*", value=st.session_state["create_sd"])
    st.session_state["create_ed"] = d2.date_input("Bitiş Tarihi*", value=st.session_state["create_ed"])

    t1, t2 = st.columns(2)
    st.session_state["create_st"] = t1.time_input("Başlangıç Saati", value=st.session_state["create_st"])
    st.session_state["create_et"] = t2.time_input("Bitiş Saati", value=st.session_state["create_et"])

    l1, l2 = st.columns(2)
    st.session_state["create_loc"]  = l1.text_input("Konum (opsiyonel)", value=st.session_state["create_loc"])
    st.session_state["create_addr"] = l2.text_input("Detaylı Adres (opsiyonel)", value=st.session_state["create_addr"])

    st.session_state["create_desc"] = st.text_area("Açıklama / Not (opsiyonel)", value=st.session_state["create_desc"], height=80)

    n1, n2 = st.columns([1,1])
    st.session_state["create_notify"] = n1.checkbox("Hatırlat", value=st.session_state["create_notify"])
    st.session_state["create_minutes"] = n2.number_input(
        "Kaç dakika önce?", min_value=0, step=5,
        value=int(st.session_state["create_minutes"]),
        disabled=not st.session_state["create_notify"]
    )

    # ----- Notes editor (create) -----
    st.divider()
    st.subheader("📝 Notlar")
    create_notes = st.session_state.get("create_notes_list", [{"record_id": None, "note": "", "rank": 1}])
    for i in range(len(create_notes)):
        row = create_notes[i]
        c1n, c2n = st.columns([4,1])
        row["note"] = c1n.text_area(f"Not {i+1}", value=row.get("note",""), key=f"create_note_{i}", height=80)
        row["rank"] = int(c2n.number_input("Sıra", min_value=0, step=1,
                                           value=int(row.get("rank", i+1)),
                                           key=f"create_rank_{i}"))
        if st.columns([1,5])[0].button("Sil", key=f"create_del_{i}"):
            create_notes.pop(i)
            st.session_state["create_notes_list"] = create_notes if create_notes else [{"record_id": None, "note": "", "rank": 1}]
            st.experimental_rerun()
        st.markdown("---")

    if st.button("➕ Yeni Not Ekle", key="create_add_note"):
        create_notes.append({"record_id": None, "note": "", "rank": (max([n.get('rank',0) or 0 for n in create_notes]) + 1) if create_notes else 1})
        st.session_state["create_notes_list"] = create_notes
        st.experimental_rerun()

    st.session_state["create_notes_list"] = create_notes

    # actions
    save_new = st.button("Kaydet", type="primary")
    cancel_new = st.button("Vazgeç")

    if cancel_new:
        st.session_state.pop("_agenda_selected", None)
        st.session_state.pop("create_state_init", None)
        st.session_state.pop("create_notes_list", None)
        st.experimental_rerun()

    if save_new:
        name = st.session_state["create_name"]
        if not name:
            st.error("Lütfen bir ad girin.")
            return
        start_dt = datetime.combine(st.session_state["create_sd"], st.session_state["create_st"])
        end_dt   = datetime.combine(st.session_state["create_ed"], st.session_state["create_et"])
        if end_dt < start_dt:
            st.error("Bitiş tarihi başlangıçtan önce olamaz.")
            return

        payload = {
            "participant_id": int(user_id),
            "name": name,
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
        }
        if st.session_state["create_desc"]:  payload["description"] = st.session_state["create_desc"]
        if st.session_state["create_type"]:  payload["type"] = st.session_state["create_type"]
        if st.session_state["create_loc"]:   payload["location"] = st.session_state["create_loc"]
        if st.session_state["create_addr"]:  payload["detailed_address"] = st.session_state["create_addr"]
        if st.session_state["create_notify"]:
            payload["notify"] = True
            payload["minutes_to_notify"] = int(st.session_state["create_minutes"])
        else:
            payload["notify"] = False
            payload["minutes_to_notify"] = None

        try:
            # 1) create agenda item
            tbl = get_airtable_table(TABLE_NAME)
            rec = tbl.create(payload)
            record_id = rec.get("id")

            # 2) fetch numeric id
            numeric_id = fetch_numeric_id_for_record(record_id)
            if numeric_id is None:
                st.warning("Oluşturuldu fakat 'id' alanı bulunamadı; notlar bağlanmadı.")
            else:
                # 3) upsert notes (creation path -> these are all new rows)
                save_notes_for_agenda_numeric_id(int(numeric_id), st.session_state.get("create_notes_list", []))

            st.success("Kayıt oluşturuldu.")
            st.session_state.pop("_agenda_selected", None)
            st.session_state.pop("create_state_init", None)
            st.session_state.pop("create_notes_list", None)
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Kaydedilemedi: {e}")

# ---------- Views (clickable) ----------
def monthly_view(user_id: int, items, base_dt: date):
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(base_dt.year, base_dt.month)

    st.subheader(f"{calendar.month_name[base_dt.month].upper()} {base_dt.year}")

    hdr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    cols = st.columns(7)
    for i, h in enumerate(hdr):
        with cols[i]:
            st.markdown(f"**{h}**")

    for week in month_days:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                in_month = (day.month == base_dt.month)
                box = st.container(border=True)
                with box:
                    style = "" if in_month else "opacity:0.35;"
                    left, right = st.columns([1,1])
                    with left:
                        st.markdown(f"<div style='{style}'>**{day.day}**</div>", unsafe_allow_html=True)
                    with right:
                        if st.button("Seç", key=f"pick_day_{day.isoformat()}"):
                            set_selection(datetime.combine(day, time.min), datetime.combine(day, time.max))
                            st.experimental_rerun()

                    day_start = datetime.combine(day, time.min)
                    day_end   = datetime.combine(day, time.max)
                    day_items = [it for it in items if overlaps_window(it.get("start"), it.get("end"), day_start, day_end)]
                    for it in day_items[:6]:
                        time_str = ""
                        if it.get("start"): time_str += it["start"].strftime("%H:%M")
                        if it.get("end"):   time_str += f"–{it['end'].strftime('%H:%M')}"
                        label = f"• {it['title']}"
                        if time_str: label += f" ({time_str})"
                        if st.button(label, key=f"open_{it['key']}_{day.isoformat()}"):
                            set_selection(it.get("start") or day_start, it.get("end") or day_end, it["key"])
                            st.experimental_rerun()
                    if len(day_items) > 6:
                        st.caption(f"+{len(day_items)-6} daha")

def weekly_hourly_view(user_id: int, items, base_dt: date):
    week_start = base_dt - timedelta(days=base_dt.weekday())
    days = [week_start + timedelta(days=i) for i in range(7)]
    day_names = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

    st.subheader(f"Hafta: {week_start.strftime('%d %b %Y')} – {(week_start + timedelta(days=6)).strftime('%d %b %Y')}")

    cols = st.columns(8)
    with cols[0]: st.write("")
    for i, d in enumerate(days, start=1):
        with cols[i]:
            st.markdown(f"**{day_names[i-1]} {d.strftime('%d/%m')}**")

    for hh in range(24):
        row = st.columns(8)
        with row[0]:
            st.markdown(f"**{hh:02d}:00**")
        for di, d in enumerate(days, start=1):
            slot_s = datetime.combine(d, time(hour=hh, minute=0))
            slot_e = slot_s + timedelta(hours=1) - timedelta(seconds=1)

            overlap = [it for it in items if overlaps_window(it.get("start"), it.get("end"), slot_s, slot_e)]
            label = (overlap[0]['title'][:12] + "…") if overlap else "Ekle"

            if row[di].button(label, key=f"slot_{d.isoformat()}_{hh}"):
                focus_key = overlap[0]["key"] if overlap else None
                set_selection(slot_s, slot_e, focus_key)
                st.experimental_rerun()

# ---------- Page ----------
def main():
    render_navbar()
    st.title("🗓️ My Agenda")

    user_id = int(st.session_state.get("current_user_id") or st.session_state.get("participant_user_id") or 2000)

    view_mode = st.radio("Görünüm", ["Günlük (Ay)", "Saatlik (Hafta)"], horizontal=True)
    base_date = st.date_input("Tarih", value=date.today())

    items = get_user_items(user_id)

    # Editor (appears when a cell/day is clicked)
    render_editor(user_id, items)
    st.markdown("---")

    if view_mode == "Günlük (Ay)":
        monthly_view(user_id, items, base_date)
    else:
        weekly_hourly_view(user_id, items, base_date)

if __name__ == "__main__":
    main()
