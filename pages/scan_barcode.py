import streamlit as st
from pyairtable import Api

st.set_page_config(page_title="Barkod Tara", page_icon="📷", layout="wide")

AIRTABLE_CONFIG = {
    "base_id": "applJyRTlJLvUEDJs",
    "api_key": "patJHZQyID8nmSaxh.1bcf08f100bd723fd85d67eff8534a19f951b75883d0e0ae4cc49743a9fb3131",
}
def api(): return Api(AIRTABLE_CONFIG["api_key"])
def t(name): return api().table(AIRTABLE_CONFIG["base_id"], name)

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

def try_decode_pyzbar(img_bytes) -> str | None:
    """Try to decode QR/Barcode using pyzbar if available; else return None."""
    try:
        from PIL import Image
        from pyzbar.pyzbar import decode
        im = Image.open(img_bytes) if hasattr(img_bytes, "read") else Image.open(io.BytesIO(img_bytes))
        res = decode(im)
        if not res:
            return None
        return res[0].data.decode("utf-8", errors="ignore")
    except Exception:
        return None

def main():
    navbar()
    st.title("📷 Barkod Tara")

    current_id = get_current_user_id()
    st.caption(f"Mevcut kullanıcı: {current_id}")

    img = st.camera_input("Arkadaşının barkodunu/QR'ını kameraya göster")
    decoded = None

    if img is not None:
        st.info("Görüntü alındı. Çözümleme deneniyor…")
        decoded = try_decode_pyzbar(img)
        if decoded:
            st.success(f"Çözümlenen metin: {decoded}")
        else:
            st.warning("Otomatik çözümleme başarısız. Aşağıya gördüğünüz ID'yi elle girebilirsiniz.")

    manual = st.text_input("Gördüğünüz kullanıcı ID'sini yazın", placeholder="Örn: 2001")
    if st.button("Devam", type="primary"):
        candidate = (decoded or "").strip() if decoded else manual.strip()
        if not candidate or not candidate.isdigit():
            st.error("Geçerli sayısal bir kullanıcı ID'si bulunamadı.")
            return
        # Prefill add_friend page
        st.session_state["prefill_friend_id"] = candidate
        st.switch_page("pages/add_friend.py")

if __name__ == "__main__":
    main()
