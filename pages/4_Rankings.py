# pages/4_Rankings.py
# New Rankings model:
# - Global by default (no group guard)
# - Powered by events where rating is not null
# - Optional tag filter (uses st.session_state["active_tag"])
# - Optional time window (7/30/90/all)
# - Filters: search, category, mashbill style, min rated pours
# - "Open bottle" sets active bottle and sends you to Bottle Page

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from supabase import create_client

from lib.ui import apply_speakeasy_theme, card
from lib.device_token import get_or_create_device_token


# ============================================================
# SETUP
# ============================================================
st.set_page_config(page_title="Rankings", page_icon="🏆", layout="wide")
apply_speakeasy_theme()

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(url, key)

device_token = get_or_create_device_token()
display_name = st.session_state.get("display_name")
active_tag = (st.session_state.get("active_tag") or "").strip() or None


def bottle_label(brand: str | None, expression: str | None) -> str:
    brand = (brand or "").strip()
    expr = (expression or "").strip()
    return f"{brand} - {expr}" if expr else brand


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("## Rankings")
st.sidebar.caption(f"Device: `{device_token[:10]}…`")

if display_name:
    st.sidebar.success(f"You: {display_name}")
else:
    st.sidebar.caption("Browsing is open. Set your drinking name on Welcome to post.")

if active_tag:
    st.sidebar.markdown("### Tag filter")
    st.sidebar.code(active_tag)
    if st.sidebar.button("Clear tag filter"):
        st.session_state["active_tag"] = ""
        st.rerun()


# ============================================================
# UI
# ============================================================
st.title("Rankings 🏆")
st.caption("Statistical summary of rated pours. Global by default. Filter by tag if you want.")
st.divider()

# ============================================================
# CONTROLS
# ============================================================
st.subheader("Controls")

c1, c2, c3, c4 = st.columns([2, 1, 1, 1])

with c1:
    search_text = st.text_input("Search", placeholder="Type brand or expression...")

with c2:
    window_choice = st.selectbox("Time window", ["All time", "Last 7 days", "Last 30 days", "Last 90 days"], index=1)

with c3:
    min_pours = st.number_input("Min rated pours", min_value=1, max_value=100, value=3, step=1)

with c4:
    limit_n = st.number_input("Show top", min_value=10, max_value=200, value=50, step=10)

time_min_iso = None
if window_choice != "All time":
    days = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}[window_choice]
    time_min_iso = _iso(_utc_now() - timedelta(days=days))

# ============================================================
# LOAD EVENTS (rated pours only)
# Note: Supabase query limits can apply. We pull a reasonably large slice.
# If your dataset grows, we’ll move aggregation into SQL/RPC later.
# ============================================================
st.divider()
st.subheader("Loading rated pours")

q = (
    sb.table("events")
    .select("bottle_id, rating, created_at, primary_tag")
    .not_.is_("rating", "null")
)

if time_min_iso:
    q = q.gte("created_at", time_min_iso)

if active_tag:
    q = q.eq("primary_tag", active_tag)

# Pull up to N rows for aggregation. Adjust if needed.
events_rows = (q.limit(10000).execute().data) or []

if not events_rows:
    msg = "No rated pours found."
    if active_tag:
        msg += " Try clearing the tag filter."
    card("Nothing to rank yet", msg)
    st.stop()

events_df = pd.DataFrame(events_rows)

# Defensive cleaning
events_df = events_df[events_df["bottle_id"].notna()]
events_df["rating"] = pd.to_numeric(events_df["rating"], errors="coerce")
events_df = events_df[events_df["rating"].notna()]

if events_df.empty:
    card("Nothing to rank yet", "No valid numeric ratings found.")
    st.stop()

# ============================================================
# LOAD BOTTLES METADATA
# ============================================================
bottle_ids = events_df["bottle_id"].dropna().unique().tolist()

bottles_rows = (
    sb.table("bottles")
    .select("id, brand, expression, category, mashbill_style, proof, distillery, distillery_location, barrel_type")
    .in_("id", bottle_ids)
    .execute()
    .data
) or []

if not bottles_rows:
    card("Missing bottle metadata", "Events exist but bottles could not be loaded.")
    st.stop()

bottles_df = pd.DataFrame(bottles_rows)

# ============================================================
# AGGREGATE
# ============================================================
agg = (
    events_df.groupby("bottle_id", as_index=False)
    .agg(
        avg_rating=("rating", "mean"),
        rating_count=("rating", "size"),
    )
)

df = agg.merge(bottles_df, left_on="bottle_id", right_on="id", how="left")
df["label"] = df.apply(lambda x: bottle_label(x.get("brand"), x.get("expression")), axis=1)

df["avg_rating"] = df["avg_rating"].astype(float)
df["rating_count"] = df["rating_count"].astype(int)

# ============================================================
# FILTERS (metadata-driven)
# ============================================================
st.subheader("Filters")

left, mid, right = st.columns([2, 2, 1])

with left:
    categories = sorted([c for c in df["category"].dropna().unique().tolist() if str(c).strip()])
    category_filter = st.selectbox("Category", ["All"] + categories)

with mid:
    styles = sorted([c for c in df["mashbill_style"].dropna().unique().tolist() if str(c).strip()])
    mashbill_filter = st.selectbox("Mashbill Style", ["All"] + styles)

with right:
    st.caption("Min rated pours is set above.")

f = df.copy()

if search_text.strip():
    s = search_text.strip().lower()
    f = f[f["label"].str.lower().str.contains(s, na=False)]

if category_filter != "All":
    f = f[f["category"] == category_filter]

if mashbill_filter != "All":
    f = f[f["mashbill_style"] == mashbill_filter]

f = f[f["rating_count"] >= int(min_pours)]

# Sort
f = f.sort_values(["avg_rating", "rating_count", "label"], ascending=[False, False, True])

# Limit
f = f.head(int(limit_n))

# ============================================================
# SUMMARY
# ============================================================
st.divider()

summary_left, summary_right, summary_third = st.columns(3)
with summary_left:
    st.metric("Rated bottles (after filters)", str(len(f)))
with summary_right:
    st.metric("Rated pours (window)", str(len(events_df)))
with summary_third:
    st.metric("Tag filter", active_tag or "None")

# ============================================================
# RESULTS
# ============================================================
st.subheader("Leaderboard")

if f.empty:
    st.info("No bottles match your filters.")
    st.stop()

display_cols = [
    "label",
    "avg_rating",
    "rating_count",
    "category",
    "mashbill_style",
    "proof",
    "distillery",
    "distillery_location",
    "barrel_type",
]

display_df = f[display_cols].copy()
display_df["avg_rating"] = display_df["avg_rating"].map(lambda x: f"{x:.2f}")

st.dataframe(display_df, use_container_width=True, hide_index=True)

st.divider()

# ============================================================
# OPEN BOTTLE (jump helper)
# ============================================================
st.subheader("Open a bottle")

label_list = f["label"].tolist()
label_choice = st.selectbox("Choose from current list", label_list)

if st.button("Open Bottle Page", key="open_bottle_btn"):
    row = f[f["label"] == label_choice].iloc[0]
    st.session_state["active_bottle_id"] = row["bottle_id"]
    st.session_state["active_bottle_label"] = row["label"]
    st.success("Active bottle set. Click the Bottle page in the sidebar to view it.")
