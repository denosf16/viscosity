import streamlit as st

st.set_page_config(page_title="Viscosity", page_icon="🥃", layout="centered")

st.title("Viscosity 🥃")
st.caption("Weekend MVP: groups, bottles, ratings, comments, feed")

# ---------- Active Group Indicator ----------
if "active_group_id" in st.session_state:
    st.sidebar.markdown("### Active Group")
    st.sidebar.success(st.session_state.get("group_name", "Unknown"))

    display_name = st.session_state.get("display_name", "Member")
    st.sidebar.markdown(f"**You:** {display_name}")
else:
    st.sidebar.warning("No group selected")

st.info("Use the sidebar to navigate.")
