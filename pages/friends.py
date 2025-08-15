import streamlit as st
from pyairtable import Api

st.set_page_config(page_title="Arkadaşlarım", page_icon="👥", layout="wide")

AIRTABLE_CONFIG = {
    "base_id": "applJyRTlJLvUEDJs",
    "api_key": "patJHZQyID8nmSaxh.1bcf08f100bd723fd85d67eff8534a19f951b75883d0e0ae4cc49743a9fb3131",
}

FRIENDS_TABLE = "friends"       # adding_user_id (int), added_user_id (int), is_active (bool)
PARTICIPANTS_TABLE = "participants"

def api(): return Api(AIRTABLE_CONFIG["api_key"])
def t(name): return api().table(AIRTABLE_CONFIG["base_id"], name)

def navbar():
    c1, c2, c3, c4, c5 = st.columns([1,1,1,1,1])
    with c1: st.page_link("app.py", label="🏠 Ana Sayfa")
    with c2: st.page_link("pages/events.py", label="🗓️ Events")
    with c3: st.page_link("pages/join_by_code.py", label="🎫 Koda Katıl")
    with c4:
        # Force “Profile” to your own profile on click
        if st.button("👤 Profil", use_container_width=True):
            st.session_state["allow_profile_view_other"] = False
            st.session_state["profile_view_user_id"] = None
            st.switch_page("pages/profile.py")
    with c5: st.page_link("pages/add_friend.py", label="👥 Arkadaş Ekle")
    st.markdown("---")

def current_user_id() -> int:
    if "current_user_id" not in st.session_state:
        st.session_state.current_user_id = 2000
    return int(st.session_state.current_user_id)

def fetch_active_friend_rows_for_user(user_id: int):
    """Rows where user is part of friendship and is_active=1."""
    try:
        formula = (
            f"AND("
            f"OR({{adding_user_id}} = {int(user_id)}, {{added_user_id}} = {int(user_id)}),"
            f"{{is_active}} = 1"
            f")"
        )
        return t(FRIENDS_TABLE).all(formula=formula)
    except Exception:
        return []

def friend_id_from_row(row: dict, user_id: int) -> int | None:
    f = row.get("fields", {})
    a = f.get("adding_user_id")
    b = f.get("added_user_id")
    if a is None or b is None:
        return None
    return int(b) if int(a) == int(user_id) else int(a)

def fetch_participant_display(friend_user_id: int):
    """Simple display info for a participant."""
    try:
        recs = t(PARTICIPANTS_TABLE).all(formula=f"{{id}} = {int(friend_user_id)}", max_records=1)
        if not recs:
            return {"name": f"Kullanıcı {friend_user_id}", "avatar_url": "", "bio": ""}
        f = recs[0].get("fields", {})
        name = f.get("name") or f.get("username") or f"Kullanıcı {friend_user_id}"
        return {"name": name, "avatar_url": f.get("avatar_url") or "", "bio": f.get("description") or f.get("bio") or ""}
    except Exception:
        return {"name": f"Kullanıcı {friend_user_id}", "avatar_url": "", "bio": ""}

def main():
    navbar()
    st.title("👥 Arkadaşlarım")

    user_id = current_user_id()  # ALWAYS your own friends; never others'
    rows = fetch_active_friend_rows_for_user(user_id)

    # Build friend list with grouped record_ids (some users may have multiple rows)
    friends_map = {}  # friend_id -> {"friend_id": x, "record_ids": [rec...]}
    for r in rows:
        fr_id = friend_id_from_row(r, user_id)
        if fr_id is None:
            continue
        if fr_id not in friends_map:
            friends_map[fr_id] = {"friend_id": fr_id, "record_ids": []}
        friends_map[fr_id]["record_ids"].append(r.get("id"))

    friends_list = list(friends_map.values())
    if not friends_list:
        st.info("Aktif arkadaşın yok. 'Arkadaş Ekle' sayfasından ekleyebilirsin.")
        st.stop()

    st.caption("Arkadaş listenden profillere gidebilir veya arkadaşlığı sonlandırabilirsin (Uygula ile).")
    to_unfriend_ids = set()

    for chunk_start in range(0, len(friends_list), 3):
        cols = st.columns(3)
        for idx in range(3):
            i = chunk_start + idx
            if i >= len(friends_list):
                break
            item = friends_list[i]
            friend_user_id = int(item["friend_id"])
            info = fetch_participant_display(friend_user_id)

            with cols[idx]:
                box = st.container(border=True)
                with box:
                    left, right = st.columns([1, 2])
                    with left:
                        if info["avatar_url"]:
                            st.image(info["avatar_url"], width=64)
                        else:
                            st.markdown("<div style='font-size:48px;line-height:1;'>🧑</div>", unsafe_allow_html=True)
                    with right:
                        st.markdown(f"**{info['name']}**")
                        if info.get("bio"): st.caption(info["bio"])

                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("Profili Gör", key=f"view_{friend_user_id}", use_container_width=True):
                            # Allow a one-time view of another user's profile
                            st.session_state["profile_view_user_id"] = friend_user_id
                            st.session_state["allow_profile_view_other"] = True
                            st.switch_page("pages/profile.py")
                    with b2:
                        mark = st.checkbox("Kaldır", key=f"rm_{friend_user_id}")
                        if mark:
                            to_unfriend_ids.add(friend_user_id)

    st.markdown("---")
    if st.button("Uygula", type="primary"):
        if not to_unfriend_ids:
            st.info("Kaldırılacak arkadaş seçilmedi.")
        else:
            errors = 0
            for fid in to_unfriend_ids:
                rec_ids = friends_map.get(fid, {}).get("record_ids", [])
                for rid in rec_ids:
                    try:
                        t(FRIENDS_TABLE).update(rid, {"is_active": False})
                    except Exception:
                        errors += 1
            if errors == 0:
                st.success("Seçilen arkadaşlıklar kaldırıldı (pasif yapıldı).")
            else:
                st.warning(f"Bazı kayıtlar güncellenemedi. Hata sayısı: {errors}")
            st.rerun()

if __name__ == "__main__":
    main()
