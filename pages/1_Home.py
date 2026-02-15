# pages/1_Home.py
# "Room" page (read-only):
# - Global feed (no posting)
# - Respects active tag filter (from Tags page)
# - Each item has "Open bottle" to jump into Bottle page

from __future__ import annotations

import streamlit as st
from supabase import create_client

from lib.ui import apply_speakeasy_theme, card
from lib.device_token import get_or_create_device_token


# ============================================================
# SETUP
# ============================================================
st.set_page_config(page_title="Room", page_icon="🥃", layout="wide")
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


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("## Room")
st.sidebar.caption(f"Device: `{device_token[:10]}…`")

if display_name:
    st.sidebar.success(f"You: {display_name}")
else:
    st.sidebar.caption("Browsing is open. Set your drinking name on Welcome to post pours.")

if active_tag:
    st.sidebar.markdown("### Tag filter")
    st.sidebar.code(active_tag)
    if st.sidebar.button("Clear tag filter"):
        st.session_state["active_tag"] = ""
        st.rerun()
else:
    st.sidebar.caption("No tag filter active.")


# ============================================================
# MAIN
# ============================================================
st.title("The Room 🥃")
st.caption("Overhear what people are ordering. Click into a bottle when something catches your eye.")
st.divider()

# ============================================================
# GLOBAL FEED
# ============================================================
controls_left, controls_right = st.columns([2, 1])
with controls_left:
    st.subheader("Recent pours")
with controls_right:
    limit_n = st.number_input("Show", min_value=10, max_value=200, value=50, step=10)

q = (
    sb.table("events")
    .select("id, created_at, message, bottle_id, rating, location, primary_tag, author_display_name")
    .order("created_at", desc=True)
    .limit(int(limit_n))
)
if active_tag:
    q = q.eq("primary_tag", active_tag)

events = (q.execute().data) or []

if not events:
    msg = "No activity yet."
    if active_tag:
        msg += " Try clearing the tag filter."
    card("Nothing pouring yet", msg)
    st.stop()

# Resolve bottle labels in one fetch
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
    loc = e.get("location")
    msg = e.get("message")

    header = f"**{name}**  ·  **{btext}**"
    if isinstance(rating, (int, float)):
        header += f"  ·  **{int(rating)}/10**"
    if tag:
        header += f"  ·  `{tag}`"
    if loc:
        header += f"  ·  {loc}"

    st.markdown(header)

    if msg:
        st.write(msg)

    st.caption(e.get("created_at", ""))

    if st.button("Open bottle", key=f"open_bottle_{e['id']}"):
        st.session_state["active_bottle_id"] = e.get("bottle_id")
        st.session_state["active_bottle_label"] = btext
        st.success("Active bottle set. Click Bottles in the sidebar.")
        st.rerun()

    st.divider()
