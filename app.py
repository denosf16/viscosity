import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Viscosity", page_icon="🥃", layout="centered")

st.title("Viscosity 🥃")
st.caption("Weekend MVP: groups, bottles, ratings, comments, feed")

# ---------- Supabase ----------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ---------- Active Group Indicator ----------
if "active_group_id" in st.session_state:
    st.sidebar.markdown("### Active Group")
    st.sidebar.success(st.session_state.get("group_name", "Unknown"))

    # Prefer session display_name, otherwise fetch from DB once
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
    st.sidebar.warning("No group selected")

st.info("Use the sidebar to navigate.")
