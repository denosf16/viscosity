import streamlit as st
from supabase import create_client

from lib.device_token import get_or_create_device_token
from lib.session import restore_login_if_possible

st.set_page_config(page_title="Welcome", page_icon="🥃", layout="centered")

# ---------- Supabase ----------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ---------- Device token ----------
device_token = get_or_create_device_token()

# ============================================================
# AUTO-RESTORE SESSION (prefer device_sessions, fallback restore helper)
# ============================================================

# 1) Preferred: device_sessions table keyed by device_token
if ("active_group_id" not in st.session_state) or ("member_id" not in st.session_state):
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

            # Touch last_seen_at
            sb.table("device_sessions").update({"last_seen_at": "now()"}).eq(
                "token", device_token
            ).execute()

# 2) Fallback: whatever restore_login_if_possible does (only if still not set)
if ("active_group_id" not in st.session_state) or ("member_id" not in st.session_state):
    try:
        restore_login_if_possible(sb)
    except Exception:
        pass

# ---------- Sidebar identity ----------
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

# ---------- Main content ----------
st.title("Welcome to Viscosity 🥃")
st.caption("A private bourbon and whiskey discussion app for your crew.")

st.divider()

# Top-of-page status (matches the device_sessions behavior)
if "active_group_id" in st.session_state:
    st.success(
        f"You are in **{st.session_state['group_name']}** "
        f"as **{st.session_state.get('display_name', 'Member')}**."
    )
else:
    st.info("Create or join a group to get started.")

st.markdown(
    """
### What you can do
- Create or join a group with a join code
- Post when you're having a glass (with a scouting report)
- Rate bottles 1–10 and leave notes
- Upload bottle photos and audio notes
- See rankings inside your group

### Quick start
1. Open **Create or Join Group**
2. Create a group or enter a join code
3. Go to **Home** and post your first pour
"""
)

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.markdown("### MVP rules")
    st.write("- Join code only (no passwords yet)")
    st.write("- Global bottle catalog")
    st.write("- Group-scoped ratings, comments, events")
with c2:
    st.markdown("### Coming soon")
    st.write("- True login + private RLS")
    st.write("- Reply threads in discussion")
    st.write("- Push notifications")

st.divider()
st.caption("Built for friends. Weekend MVP.")
