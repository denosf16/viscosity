import streamlit as st
from supabase import create_client

from lib.ui import apply_speakeasy_theme, card
from lib.device_token import get_or_create_device_token
from lib.session import restore_login_if_possible


st.set_page_config(page_title="Welcome", page_icon="🥃", layout="centered")
apply_speakeasy_theme()

# ---------- Supabase ----------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ---------- Device token ----------
device_token = get_or_create_device_token()

# ============================================================
# AUTO-RESTORE SESSION (prefer device_sessions, fallback helper)
# ============================================================
needs_restore = ("active_group_id" not in st.session_state) or ("member_id" not in st.session_state)

# 1) Preferred: device_sessions table keyed by device_token
if needs_restore:
    try:
        session_res = (
            sb.table("device_sessions")
            .select("member_id, group_id")
            .eq("token", device_token)
            .limit(1)
            .execute()
            .data
        )
    except Exception:
        session_res = []

    if session_res:
        member_id = session_res[0]["member_id"]
        group_id = session_res[0]["group_id"]

        group_res = (
            sb.table("groups")
            .select("name")
            .eq("id", group_id)
            .limit(1)
            .execute()
            .data
        )

        member_res = (
            sb.table("group_members")
            .select("display_name")
            .eq("id", member_id)
            .limit(1)
            .execute()
            .data
        )

        if group_res and member_res:
            st.session_state["active_group_id"] = group_id
            st.session_state["group_name"] = group_res[0]["name"]
            st.session_state["member_id"] = member_id
            st.session_state["display_name"] = member_res[0]["display_name"]

            # Touch last_seen_at (best effort)
            try:
                sb.table("device_sessions").update({"last_seen_at": "now()"}).eq(
                    "token", device_token
                ).execute()
            except Exception:
                pass

# 2) Fallback: only if still not set
needs_restore = ("active_group_id" not in st.session_state) or ("member_id" not in st.session_state)
if needs_restore:
    try:
        restore_login_if_possible(sb)
    except Exception:
        pass

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("## Welcome")

if "active_group_id" in st.session_state:
    st.sidebar.markdown("### Active Group")
    st.sidebar.success(st.session_state.get("group_name", "Unknown"))

    display_name = st.session_state.get("display_name")
    member_id = st.session_state.get("member_id")

    if not display_name and member_id:
        try:
            row = (
                sb.table("group_members")
                .select("display_name")
                .eq("id", member_id)
                .limit(1)
                .execute()
                .data
            )
            if row:
                display_name = row[0]["display_name"]
                st.session_state["display_name"] = display_name
        except Exception:
            display_name = None

    st.sidebar.markdown(f"**You:** {display_name or 'Member'}")
else:
    st.sidebar.warning("No group selected yet")
    st.sidebar.caption("Go to Create or Join Group to start.")

# ============================================================
# MAIN
# ============================================================
st.title("Welcome to Viscosity 🥃")
st.caption("A private bourbon and whiskey discussion app for your crew.")
st.divider()

if "active_group_id" in st.session_state:
    st.success(
        f"You are in **{st.session_state.get('group_name', 'Unknown')}** "
        f"as **{st.session_state.get('display_name', 'Member')}**."
    )
else:
    st.info("Create or join a group to get started.")

card(
    "What you can do",
    "- Create or join a group with a join code<br>"
    "- Post when you're having a glass (with a scouting report)<br>"
    "- Rate bottles 1–10 and leave notes<br>"
    "- Upload bottle photos and audio notes<br>"
    "- See rankings inside your group",
)

card(
    "Quick start",
    "1. Open <b>Create or Join Group</b><br>"
    "2. Create a group or enter a join code<br>"
    "3. Go to <b>Home</b> and post your first pour",
)

c1, c2 = st.columns(2)
with c1:
    card(
        "MVP rules",
        "- Join code only (no passwords yet)<br>"
        "- Global bottle catalog<br>"
        "- Group-scoped ratings, comments, events",
    )
with c2:
    card(
        "Coming soon",
        "- True login + private RLS<br>"
        "- Reply threads in discussion<br>"
        "- Push notifications",
    )

st.caption("Built for friends. Weekend MVP.")

