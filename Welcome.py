import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Welcome", page_icon="🥃", layout="centered")

# ---------- Supabase ----------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

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
