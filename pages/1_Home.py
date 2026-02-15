import streamlit as st
from supabase import create_client


# ---------- Setup ----------
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(url, key)


# ---------- Session Guard ----------
if "active_group_id" not in st.session_state or "member_id" not in st.session_state:
    st.warning("You must create or join a group first.")
    st.stop()

group_id = st.session_state["active_group_id"]
member_id = st.session_state["member_id"]


def bottle_label(b: dict) -> str:
    brand = b.get("brand") or ""
    expr = b.get("expression")
    return f"{brand} - {expr}" if expr else brand


# ---------- UI ----------
st.title("Viscosity Feed 🥃")
st.subheader(f"Group: {st.session_state.get('group_name')}")
st.divider()


# ---------- Having a Glass ----------
st.subheader("Having a Glass")

bottles = sb.table("bottles").select("id, brand, expression").execute().data
label_to_id = {bottle_label(b): b["id"] for b in bottles}
labels_all = sorted(label_to_id.keys())

search_text = st.text_input("Search bottles", placeholder="Try: Buffalo Trace, Maker's, Four Roses...")

labels = labels_all
if search_text.strip():
    s = search_text.strip().lower()
    labels = [x for x in labels_all if s in x.lower()]

if not labels:
    st.info("No bottles match your search.")
    selected_label = None
else:
    default_label = st.session_state.get("active_bottle_label")
    default_index = labels.index(default_label) if default_label in labels else 0
    selected_label = st.selectbox("Select Bottle", labels, index=default_index)

scouting_report = st.text_input("Scouting Report", placeholder="Quick notes: nose, palate, finish, vibe...")

if st.button("Post Event", key="post_event_btn", disabled=(selected_label is None)):
    sb.table("events").insert(
        {
            "group_id": group_id,
            "member_id": member_id,
            "bottle_id": label_to_id[selected_label],
            "event_type": "having_a_glass",
            "message": scouting_report.strip() if scouting_report.strip() else None,
        }
    ).execute()
    st.success("Posted to feed!")
    st.rerun()

st.divider()


# ---------- Feed ----------
st.subheader("Recent Activity")

events = (
    sb.table("events")
    .select("id, created_at, message, bottle_id, member_id")
    .eq("group_id", group_id)
    .order("created_at", desc=True)
    .limit(30)
    .execute()
    .data
)

if not events:
    st.info("No activity yet.")
    st.stop()

bottle_ids = list({e["bottle_id"] for e in events if e.get("bottle_id")})
member_ids = list({e["member_id"] for e in events if e.get("member_id")})

bottle_rows = (
    sb.table("bottles")
    .select("id, brand, expression")
    .in_("id", bottle_ids)
    .execute()
    .data
)
member_rows = (
    sb.table("group_members")
    .select("id, display_name")
    .in_("id", member_ids)
    .execute()
    .data
)

bottle_by_id = {b["id"]: bottle_label(b) for b in bottle_rows}
member_by_id = {m["id"]: m["display_name"] for m in member_rows}

for e in events:
    name = member_by_id.get(e["member_id"], "Someone")
    btext = bottle_by_id.get(e["bottle_id"], "a bottle")

    st.markdown(f"**{name}** is having a glass of **{btext}**")
    if e.get("message"):
        st.caption(f"Scouting Report: {e['message']}")
    st.caption(e["created_at"])

    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("Review it", key=f"review_it_{e['id']}"):
            st.session_state["active_bottle_id"] = e["bottle_id"]
            st.session_state["active_bottle_label"] = btext
            st.success("Bottle selected. Now click Add Review or Bottles in the sidebar.")
    with c2:
        st.caption("Tip: Add Review is fastest on iPhone.")

    st.divider()
