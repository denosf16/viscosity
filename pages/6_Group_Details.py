import streamlit as st
from supabase import create_client


# ---------- Setup ----------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# ---------- Session Guard ----------
if "active_group_id" not in st.session_state:
    st.warning("No active group. Create or join a group first.")
    st.stop()

group_id = st.session_state["active_group_id"]

st.title("Group Details 👥")

# ---------- Group Info ----------
group_rows = (
    sb.table("groups")
    .select("id, name, join_code, created_at")
    .eq("id", group_id)
    .limit(1)
    .execute()
    .data
)

if not group_rows:
    st.error("Group not found.")
    st.stop()

g = group_rows[0]

st.subheader(g["name"])
st.caption(f"Created: {g.get('created_at')}")

st.markdown("### Join Code")
st.code(g["join_code"], language="text")
st.caption("Friends can use this join code in Create or Join Group.")

st.divider()

# ---------- Members ----------
st.markdown("### Members")

members = (
    sb.table("group_members")
    .select("display_name, created_at")
    .eq("group_id", group_id)
    .order("created_at", desc=False)
    .execute()
    .data
)

if not members:
    st.info("No members found.")
else:
    for m in members:
        st.write(f"- {m['display_name']}")
