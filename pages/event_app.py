import json
import streamlit as st
from pyairtable import Api
from datetime import datetime, date

st.set_page_config(page_title="Etkinlik Uygulaması", page_icon="📱", layout="wide")

AIRTABLE_CONFIG = {
    "base_id": "applJyRTlJLvUEDJs",
    "api_key": "patJHZQyID8nmSaxh.1bcf08f100bd723fd85d67eff8534a19f951b75883d0e0ae4cc49743a9fb3131",
}

def api(): return Api(AIRTABLE_CONFIG["api_key"])
def t(name): return api().table(AIRTABLE_CONFIG["base_id"], name)

# -------- utils
def parse_iso(s):
    try:
        s = (s or "").replace("Z","").replace("+00:00","")
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None)
    except Exception:
        return None

def norm(s: str) -> str:
    """Normalize type labels to compare robustly (supports TR/EN)."""
    if not s: return ""
    repl = str(s).strip().lower()
    repl = (repl
            .replace("ç","c").replace("ğ","g").replace("ı","i").replace("ö","o")
            .replace("ş","s").replace("ü","u"))
    return repl

def load_options(s):
    if not s: return []
    if isinstance(s, list): return s
    try:
        return json.loads(s)
    except Exception:
        try:
            return json.loads(str(s).replace("'", '"'))
        except Exception:
            # last-resort: comma split
            return [x.strip() for x in str(s).split(",") if x.strip()]

# -------- context
event_rec = st.session_state.get("selected_event_record_id")
event_num = st.session_state.get("selected_event_numeric_id")
participant_id = int(st.session_state.get("current_user_id", 2000))

if not event_rec:
    st.page_link("app.py", label="⬅️ Ana sayfa")
    st.error("Etkinlik bulunamadı."); st.stop()

# -------- event details
ev = t("events").get(event_rec)
f = ev.get("fields", {})
event = {
    "record_id": ev["id"],
    "numeric_id": f.get("id"),
    "name": f.get("name",""),
    "description": f.get("description",""),
    "start_date": f.get("start_date",""),
    "end_date": f.get("end_date",""),
}
st.markdown(f"## {event['name']}")
if event["description"]: st.write(event["description"])
sd, ed = parse_iso(event["start_date"]), parse_iso(event["end_date"])
if sd: st.caption(f"Başlangıç: {sd.strftime('%d/%m/%Y %H:%M')}")
if ed: st.caption(f"Bitiş: {ed.strftime('%d/%m/%Y %H:%M')}")
st.page_link("app.py", label="⬅️ Ana sayfa")
st.markdown("---")

numeric_id = event.get("numeric_id") or event_num
if not numeric_id:
    st.info("Event numeric id bulunamadı."); st.stop()

# -------- feature gate (feature_id=1 & is_active=1)
feat_formula = f"AND({{event_id}} = {int(numeric_id)}, {{feature_id}} = 1, {{is_active}} = 1)"
if not t("event_features").all(formula=feat_formula, max_records=1):
    st.info("Bu etkinlikte kayıt formu özelliği aktif değil."); st.stop()

# -------- form schema (ordered)
rows = t("registration_form").all(formula=f"{{event_id}} = {int(numeric_id)}")
schema = []
for r in rows:
    rf = r.get("fields", {})
    schema.append({
        "record_id": r["id"],
        "id": int(rf.get("id")) if rf.get("id") is not None else None,
        "name": rf.get("name",""),
        "type": (rf.get("type") or "").strip(),
        "is_required": bool(rf.get("is_required", False)),
        "possible_answers": rf.get("possible_answers"),
        "rank": int(rf.get("rank")) if rf.get("rank") is not None else 999999,
    })
schema.sort(key=lambda x: x["rank"])
if not schema:
    st.info("Bu etkinlik için kayıt formu tanımlı değil."); st.stop()

form_ids = [s["id"] for s in schema if s["id"] is not None]

# -------- completion check via answers (no event_id in answers)
if form_ids:
    ors = ",".join([f"{{registration_form_id}} = {i}" for i in form_ids])
    ans_formula = f"AND({{participant_id}} = {int(participant_id)}, OR({ors}))"
    existing = t("registration_form_answers").all(formula=ans_formula)
    if existing and len(existing) >= len(schema):
        st.success("Giriş Formu Dolduruldu ✅"); st.stop()

# -------- render dynamic form (proper widgets; save as string later)
st.subheader("📝 Giriş Formu")
with st.form("dyn_form"):
    values = {}
    for q in schema:
        qid = q["id"]; qname = q["name"] or f"Soru {q['id']}"
        qtype_raw = q["type"]; qtype = norm(qtype_raw)
        required = q["is_required"]; key = f"q_{qid}"
        opts = load_options(q.get("possible_answers"))

        # map many possible labels to the right widget
        # text
        if qtype in {"yazi", "text", "metin", "string"}:
            v = st.text_input(qname, key=key); answer = str(v or "")

        # integer / number
        elif qtype in {"sayi", "number", "int", "integer", "whole_number"}:
            # Streamlit needs a numeric default; 0 is acceptable
            v = st.number_input(qname, step=1, format="%d", key=key)
            answer = str(v)

        # float / decimal
        elif qtype in {"virgullu sayi", "float", "decimal", "double", "number_decimal"}:
            v = st.number_input(qname, step=0.01, key=key)
            answer = str(v)

        # date (calendar)
        elif qtype in {"tarih", "date"}:
            d = st.date_input(qname, key=key)
            answer = d.isoformat() if d else ""

        # datetime
        elif qtype in {"saat ve tarih", "datetime", "timestamp", "date_time"}:
            try:
                dt = st.datetime_input(qname, key=key)  # Streamlit ≥1.31
                answer = dt.isoformat() if dt else ""
            except Exception:
                # fallback: date + text time
                col1, col2 = st.columns([2,1])
                with col1: d = st.date_input(qname, key=key+"_d")
                with col2: tm = st.text_input("Saat (HH:MM)", key=key+"_t", placeholder="09:30")
                answer = f"{d.isoformat()}T{tm}:00" if d and tm else ""

        # boolean
        elif qtype in {"dogru yanlis", "boolean", "bool", "true_false", "checkbox"}:
            b = st.checkbox(qname, key=key); answer = "true" if b else "false"

        # single choice
        elif qtype in {"coktan secmeli", "single_choice", "select", "dropdown", "radio", "choice"}:
            choice = st.radio(qname, options=opts or [], key=key)
            answer = str(choice or "")

        # multiple choice
        elif qtype in {"coktan secmeli coklu cevap", "multi_choice", "multiple_choice", "multiselect", "checkbox_group"}:
            mult = st.multiselect(qname, options=opts or [], key=key)
            answer = json.dumps(mult, ensure_ascii=False)

        else:
            # fallback to text
            v = st.text_input(qname, key=key); answer = str(v or "")

        values[qid] = (required, answer)

    submitted = st.form_submit_button("Gönder", type="primary")

if submitted:
    # validate requireds (allow "false" and "0")
    missing = []
    for qid, (req, val) in values.items():
        if req and (val is None or (str(val).strip() == "")):
            missing.append(qid)
    if missing:
        st.error("Lütfen zorunlu alanları doldurun."); st.stop()

    ans_tbl = t("registration_form_answers")
    try:
        for fid in form_ids:
            _, val = values[fid]
            ans_tbl.create({
                "registration_form_id": int(fid),
                "participant_id": int(participant_id),
                "answer": str(val),  # store as string
            })
        st.success("Cevapların kaydedildi. Teşekkürler!")
        st.rerun()
    except Exception as e:
        st.error(f"Kayıt sırasında hata: {e}")
