# pages/1_Home.py
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
from supabase import create_client

from lib.ui import apply_speakeasy_theme, card
from lib.device_token import get_or_create_device_token


# ============================================================
# SETUP
# ============================================================
st.set_page_config(page_title="Home", page_icon="🥃", layout="wide")
apply_speakeasy_theme()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

device_token = get_or_create_device_token()
display_name = (st.session_state.get("display_name") or "").strip() or None
active_tag = (st.session_state.get("active_tag") or "").strip() or None


def bottle_label(b: dict) -> str:
    brand = (b.get("brand") or "").strip()
    expr = (b.get("expression") or "").strip()
    return f"{brand} - {expr}" if expr else brand


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("## Home")
st.sidebar.caption(f"Device: `{device_token[:10]}…`")

if display_name:
    st.sidebar.success(f"You: {display_name}")
else:
    st.sidebar.warning("No drinking name yet")
    st.sidebar.caption("You can browse. Set your name on Welcome to post pours.")

if active_tag:
    st.sidebar.markdown("### Tag filter")
    st.sidebar.code(active_tag)
    if st.sidebar.button("Clear tag filter"):
        st.session_state["active_tag"] = ""
        st.rerun()


# ============================================================
# MAIN
# ============================================================
st.title("Viscosity Feed 🥃")
st.caption("Real bars are private and intentional. This is where people share what’s worth ordering.")
st.divider()

# ============================================================
# POST A POUR (simple, global, no group)
# ============================================================
st.subheader("Having a Glass")

bottles = (sb.table("bottles").select("id, brand, expression").execute().data) or []
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

rating_val = st.slider("Rating", 1, 10, 7)
notes_val = st.text_input("Scouting Report", placeholder="Quick notes: nose, palate, finish, vibe...")

post_disabled = (selected_label is None) or (not display_name)

if not display_name:
    st.info("Set your drinking name on Welcome to post. Browsing is open.")

if st.button("Post Pour", key="post_pour_btn", disabled=post_disabled):
    payload = {
        "bottle_id": label_to_id[selected_label],
        "event_type": "having_a_glass",  # safe with your current check constraint
        "message": notes_val.strip() if notes_val.strip() else None,
        "rating": int(rating_val),
        "primary_tag": active_tag,
        "author_display_name": display_name,
        "author_device_token": device_token,
        "created_at": utc_now_iso(),
    }
    sb.table("events").insert(payload).execute()
    st.success("Posted to feed!")
    st.rerun()

st.divider()

# ============================================================
# GLOBAL FEED (no group filters, no group_members lookups)
# ============================================================
st.subheader("Recent Activity")

q = (
    sb.table("events")
    .select("id, created_at, message, bottle_id, rating, primary_tag, author_display_name")
    .order("created_at", desc=True)
    .limit(50)
)
if active_tag:
    q = q.eq("primary_tag", active_tag)

events = (q.execute().data) or []

if not events:
    card("No activity yet", "Be the first to post a pour.")
    st.stop()

bottle_ids = list({e.get("bottle_id") for e in events if e.get("bottle_id")})
bottle_rows = []
if bottle_ids:
    bottle_rows = (
        sb.table("bottles")
        .select("id, brand, expression")
        .in_("id", bottle_ids)
        .execute()
        .data
    ) or []

bottle_by_id = {b["id"]: bottle_label(b) for b in bottle_rows}

for e in events:
    name = (e.get("author_display_name") or "Someone").strip() or "Someone"
    btext = bottle_by_id.get(e.get("bottle_id"), "a bottle")

    rating = e.get("rating")
    tag = e.get("primary_tag")

    header = f"**{name}** is having a glass of **{btext}**"
    meta_bits = []
    if isinstance(rating, (int, float)):
        meta_bits.append(f"{int(rating)}/10")
    if tag:
        meta_bits.append(tag)
    if meta_bits:
        header += "  \n" + "  ·  ".join([f"`{x}`" if i == 1 else f"**{x}**" for i, x in enumerate(meta_bits)])

    st.markdown(header)

    if e.get("message"):
        st.caption(f"Scouting Report: {e['message']}")
    st.caption(e.get("created_at", ""))

    if st.button("Open bottle", key=f"open_bottle_{e['id']}"):
        st.session_state["active_bottle_id"] = e.get("bottle_id")
        st.session_state["active_bottle_label"] = btext
        st.success("Active bottle set. Click Bottles in the sidebar.")
        st.rerun()

    st.divider()
