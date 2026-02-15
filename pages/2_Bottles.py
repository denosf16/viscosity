# pages/3_Bottles.py
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
from supabase import create_client

from lib.ui import apply_speakeasy_theme, card
from lib.device_token import get_or_create_device_token


# ============================================================
# SETUP
# ============================================================
st.set_page_config(page_title="Bottle", page_icon="🍾", layout="wide")
apply_speakeasy_theme()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

device_token = get_or_create_device_token()
display_name = (st.session_state.get("display_name") or "").strip() or None


def bottle_label(b: dict) -> str:
    brand = (b.get("brand") or "").strip()
    expr = (b.get("expression") or "").strip()
    return f"{brand} - {expr}" if expr else brand


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("## Bottle")
st.sidebar.caption(f"Device: `{device_token[:10]}…`")

if display_name:
    st.sidebar.success(f"You: {display_name}")
else:
    st.sidebar.warning("No drinking name yet")
    st.sidebar.caption("You can browse. Set your name on Welcome to post pours.")


# ============================================================
# BOTTLE PICKER
# ============================================================
st.title("Bottle Page 🍾")
st.caption("Search the catalog, see recent pours, and add your own.")
st.divider()

bottles_list = (sb.table("bottles").select("id, brand, expression").execute().data) or []
label_to_id = {bottle_label(b): b["id"] for b in bottles_list}
all_labels = sorted(label_to_id.keys())

search_text = st.text_input("Search bottles", placeholder="Try: Buffalo Trace, Four Roses, Maker's...")

labels = all_labels
if search_text.strip():
    s = search_text.strip().lower()
    labels = [x for x in all_labels if s in x.lower()]

if not labels:
    card("No matches", "No bottles match your search.")
    st.stop()

default_label = st.session_state.get("active_bottle_label")
default_index = labels.index(default_label) if default_label in labels else 0

selected_label = st.selectbox("Select a bottle", labels, index=default_index)
bottle_id = label_to_id[selected_label]

st.session_state["active_bottle_id"] = bottle_id
st.session_state["active_bottle_label"] = selected_label


# ============================================================
# BOTTLE DETAILS
# ============================================================
bottle_rows = (
    sb.table("bottles")
    .select("id, brand, expression, distillery, distillery_location, proof, barrel_type, mashbill_style, category")
    .eq("id", bottle_id)
    .limit(1)
    .execute()
    .data
)

if not bottle_rows:
    st.error("Selected bottle not found.")
    st.stop()

b = bottle_rows[0]

st.subheader(selected_label)

meta_cols = st.columns(2)
with meta_cols[0]:
    st.write("Distillery:", b.get("distillery") or "N/A")
    st.write("Location:", b.get("distillery_location") or "N/A")
    st.write("Category:", b.get("category") or "N/A")
with meta_cols[1]:
    st.write("Proof:", b.get("proof") if b.get("proof") is not None else "N/A")
    st.write("Barrel Type:", b.get("barrel_type") or "N/A")
    st.write("Mashbill Style:", b.get("mashbill_style") or "N/A")

st.divider()


# ============================================================
# DROP A POUR (rating per post)
# ============================================================
st.subheader("Drop a Pour")

if not display_name:
    st.info("Set your drinking name on Welcome to post pours. Browsing is open.")

c1, c2 = st.columns([1, 2])
with c1:
    rating_val = st.slider("Rating", 1, 10, 7)
with c2:
    location_val = st.text_input("Location (optional)", placeholder="Bar name, city, couch, etc.")

notes_val = st.text_area(
    "Notes (optional)",
    placeholder="Nose, palate, finish, comparisons, vibe.",
    height=130,
)

post_disabled = not display_name

if st.button("Post Pour", disabled=post_disabled, key="post_pour_bottle_btn"):
    payload = {
        "event_type": "having_a_glass",  # safe with current constraint
        "bottle_id": bottle_id,
        "message": notes_val.strip() if notes_val.strip() else None,
        "rating": int(rating_val),
        "location": location_val.strip() if location_val.strip() else None,
        "author_display_name": display_name,
        "author_device_token": device_token,
        "created_at": utc_now_iso(),
    }
    sb.table("events").insert(payload).execute()
    st.success("Pour posted.")
    st.rerun()

st.divider()


# ============================================================
# RECENT POURS FOR THIS BOTTLE
# ============================================================
st.subheader("Recent Pours")

events = (
    sb.table("events")
    .select("id, created_at, message, rating, location, author_display_name")
    .eq("bottle_id", bottle_id)
    .order("created_at", desc=True)
    .limit(50)
    .execute()
    .data
) or []

if not events:
    card("No pours yet", "Be the first to post a pour for this bottle.")
    st.stop()

ratings = [e.get("rating") for e in events if isinstance(e.get("rating"), (int, float))]
if ratings:
    avg_rating = sum(ratings) / len(ratings)
    m1, m2, m3 = st.columns(3)
    m1.metric("Avg rating", f"{avg_rating:.2f}")
    m2.metric("Pour count", str(len(events)))
    m3.metric("Rated pours", str(len(ratings)))
    st.divider()

for e in events:
    name = (e.get("author_display_name") or "Someone").strip() or "Someone"
    rating = e.get("rating")
    loc = e.get("location")
    msg = e.get("message")

    header = f"**{name}**"
    bits = []
    if isinstance(rating, (int, float)):
        bits.append(f"{int(rating)}/10")
    if loc:
        bits.append(loc)

    if bits:
        header += "  ·  " + "  ·  ".join([f"**{bits[0]}**"] + [f"`{x}`" for x in bits[1:]])

    st.markdown(header)
    if msg:
        st.write(msg)
    st.caption(e.get("created_at", ""))
    st.divider()
