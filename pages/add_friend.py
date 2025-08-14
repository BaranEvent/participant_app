import io
import streamlit as st
from pyairtable import Api

st.set_page_config(page_title="Arkadaş Ekle", page_icon="👥", layout="wide")

# ---------- Airtable ----------
AIRTABLE_CONFIG = {
    "base_id": "applJyRTlJLvUEDJs",
    "api_key": "patJHZQyID8nmSaxh.1bcf08f100bd723fd85d67eff8534a19f951b75883d0e0ae4cc49743a9fb3131",
}
def api(): return Api(AIRTABLE_CONFIG["api_key"])
def t(name): return api().table(AIRTABLE_CONFIG["base_id"], name)

FRIENDS_TABLE = "friends"  # columns: adding_user_id (int), added_user_id (int), is_active (bool)

# ---------- Navbar ----------
def navbar():
    c1, c2, c3, c4, c5 = st.columns([1,1,1,1,1])
    with c1: st.page_link("app.py", label="🏠 Ana Sayfa")
    with c2: st.page_link("pages/events.py", label="🗓️ Events")
    with c3: st.page_link("pages/join_by_code.py", label="🎫 Koda Katıl")
    with c4: st.page_link("pages/profile.py", label="👤 Profil")
    with c5: st.page_link("pages/add_friend.py", label="👥 Arkadaş Ekle")
    st.markdown("---")

def get_current_user_id() -> int:
    if "current_user_id" not in st.session_state:
        st.session_state.current_user_id = 2000
    return int(st.session_state.current_user_id)

def participant_exists(user_id: int) -> bool:
    try:
        rows = t("participants").all(formula=f"{{id}} = {int(user_id)}", max_records=1)
        return len(rows) > 0
    except Exception:
        return False

def already_friends(a: int, b: int) -> bool:
    formula = (
        f"OR("
        f"AND({{adding_user_id}} = {a}, {{added_user_id}} = {b}),"
        f"AND({{adding_user_id}} = {b}, {{added_user_id}} = {a})"
        f")"
    )
    try:
        rows = t(FRIENDS_TABLE).all(formula=formula, max_records=1)
        return len(rows) > 0
    except Exception:
        return False

# ---- QR helpers (requires `qrcode` and `Pillow`)
def _make_qr_png_bytes(text: str) -> bytes | None:
    try:
        import qrcode
        img = qrcode.make(text)  # uses PIL under the hood
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None

def main():
    navbar()
    st.title("👥 Arkadaş Ekle")

    # Current user
    current_id = get_current_user_id()
    new_id = st.sidebar.number_input("User ID", value=int(current_id), step=1, format="%d")
    st.session_state.current_user_id = int(new_id)
    current_id = int(new_id)

    st.write(f"**Mevcut Kullanıcı ID:** `{current_id}`")

    friend_txt = st.text_input("Arkadaşının Kullanıcı ID'si", placeholder="Örn: 2001")
    add_clicked = st.button("Arkadaş Ekle", type="primary", use_container_width=True)

    if add_clicked:
        if not friend_txt or not friend_txt.isdigit():
            st.error("Lütfen geçerli sayısal bir kullanıcı ID'si girin.")
            return
        friend_id = int(friend_txt)
        if friend_id == current_id:
            st.error("Kendinizi ekleyemezsiniz.")
            return
        if not participant_exists(friend_id):
            st.error("Bu ID ile bir katılımcı bulunamadı (participants.id).")
            return
        if already_friends(current_id, friend_id):
            st.info("Zaten arkadaşsınız. 🌿")
            return
        try:
            t(FRIENDS_TABLE).create({
                "adding_user_id": int(current_id),
                "added_user_id": int(friend_id),
                "is_active": True,
            })
            st.success("Arkadaş eklendi! 🎉")
        except Exception as e:
            st.error(f"Kayıt sırasında hata: {e}")

    st.markdown("---")

    # =======================
    # Barcode / QR actions
    # =======================
    b1, b2 = st.columns(2)
    with b1:
        if st.button("📷 Barkod Tara", use_container_width=True):
            st.switch_page("pages/scan_barcode.py")

    with b2:
        show_qr = st.button("🧾 Barkodumu Göster", use_container_width=True)
        if show_qr:
            qr_bytes = _make_qr_png_bytes(str(current_id))
            with st.expander("Kullanıcı Barkodum (QR)"):
                st.code(str(current_id), language="text")
                if qr_bytes:
                    st.image(qr_bytes, caption="Bu QR kod user_id'inizi içerir.", use_column_width=False)
                else:
                    st.warning("QR kod üretilemedi. `qrcode` ve `Pillow` kurulu mu?")
                    st.caption("Gerekli bağımlılıklar: qrcode[pil], Pillow")

if __name__ == "__main__":
    main()
