# pages/3_Rankings.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from supabase import create_client

from lib.device_token import get_or_create_device_token
from lib.ui import apply_speakeasy_theme, card


# ============================================================
# SETUP
# ============================================================
st.set_page_config(page_title="Rankings", page_icon="🏆", layout="wide")
apply_speakeasy_theme()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

device_token = get_or_create_device_token()
display_name = (st.session_state.get("display_name") or "").strip() or None


def bottle_label(brand: str | None, expression: str | None) -> str:
    brand = (brand or "").strip()
    expr = (expression or "").strip()
    return f"{brand} - {expr}" if expr else brand


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _reset_filters():
    # Keep scope as-is; reset everything else to sane defaults.
    st.session_state["rk_search_text"] = ""
    st.session_state["rk_window_choice"] = "All time"
    st.session_state["rk_min_pours"] = 1
    st.session_state["rk_limit_n"] = 50
    st.session_state["rk_category_filter"] = "All"
    st.session_state["rk_mashbill_filter"] = "All"


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("## Rankings")
st.sidebar.caption(f"Device: `{device_token[:10]}…`")

if display_name:
    st.sidebar.success(f"You: {display_name}")
else:
    st.sidebar.caption("Browsing is open. Set your drinking name on Welcome to post pours.")


# ============================================================
# UI
# ============================================================
st.title("Rankings 🏆")
st.caption("A statistical summary of rated pours. Global by default.")
st.divider()


# ============================================================
# CONTROLS
# ============================================================
st.subheader("Controls")

c0, c1, c2, c3, c4, c5 = st.columns([1.2, 2.2, 1.2, 1.2, 1.1, 1.2])

with c0:
    scope = st.radio(
        "Scope",
        ["Global", "My Stats"],
        horizontal=True,
        index=0,
        key="rk_scope",
        help="My Stats ranks only your pours on this device.",
    )

with c1:
    search_text = st.text_input(
        "Search",
        placeholder="Type brand or expression...",
        key="rk_search_text",
    )

with c2:
    window_choice = st.selectbox(
        "Time window",
        ["All time", "Last 7 days", "Last 30 days", "Last 90 days"],
        index=0,  # <-- SANE DEFAULT
        key="rk_window_choice",
    )

with c3:
    min_pours = st.number_input(
        "Min rated pours",
        min_value=1,
        max_value=100,
        value=1,  # <-- SANE DEFAULT
        step=1,
        key="rk_min_pours",
    )

with c4:
    limit_n = st.number_input(
        "Show top",
        min_value=10,
        max_value=200,
        value=50,
        step=10,
        key="rk_limit_n",
    )

with c5:
    st.caption("")
    if st.button("Reset filters", key="rk_reset_btn"):
        _reset_filters()
        st.rerun()


# Guardrail: My Stats requires identity (otherwise it's empty and confusing)
if scope == "My Stats" and not display_name:
    card(
        "Set your drinking name",
        "My Stats is tied to your device identity.<br>"
        "Go to <b>Welcome</b> and set your drinking name, then come back.",
    )
    st.stop()


time_min_iso = None
if window_choice != "All time":
    days = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}[window_choice]
    time_min_iso = _iso(_utc_now() - timedelta(days=days))


# ============================================================
# LOAD EVENTS (rated pours only)
# ============================================================
q = (
    sb.table("events")
    .select("bottle_id, rating, created_at, author_device_token")
    .not_.is_("rating", "null")
)

if scope == "My Stats":
    q = q.eq("author_device_token", device_token)

if time_min_iso:
    q = q.gte("created_at", time_min_iso)

events_rows = (q.limit(10000).execute().data) or []

if not events_rows:
    who = "you" if scope == "My Stats" else "anyone"
    card("Nothing to rank yet", f"No rated pours found for {who} in this time window.")
    st.stop()

events_df = pd.DataFrame(events_rows)
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
# MORE FILTERS (tucked away)
# ============================================================
with st.expander("More filters", expanded=False):
    f1, f2 = st.columns([1, 1])

    with f1:
        categories = sorted([c for c in df["category"].dropna().unique().tolist() if str(c).strip()])
        category_filter = st.selectbox(
            "Category",
            ["All"] + categories,
            key="rk_category_filter",
        )

    with f2:
        styles = sorted([c for c in df["mashbill_style"].dropna().unique().tolist() if str(c).strip()])
        mashbill_filter = st.selectbox(
            "Mashbill Style",
            ["All"] + styles,
            key="rk_mashbill_filter",
        )


# ============================================================
# APPLY FILTERS
# ============================================================
f = df.copy()

if (search_text or "").strip():
    s = search_text.strip().lower()
    f = f[f["label"].str.lower().str.contains(s, na=False)]

category_filter = st.session_state.get("rk_category_filter", "All")
mashbill_filter = st.session_state.get("rk_mashbill_filter", "All")

if category_filter != "All":
    f = f[f["category"] == category_filter]

if mashbill_filter != "All":
    f = f[f["mashbill_style"] == mashbill_filter]

f = f[f["rating_count"] >= int(min_pours)]

# Sort and limit
f = f.sort_values(["avg_rating", "rating_count", "label"], ascending=[False, False, True]).head(int(limit_n))


# ============================================================
# SUMMARY
# ============================================================
st.divider()

summary_left, summary_right, summary_third = st.columns([1, 1, 2])
with summary_left:
    st.metric("Rated bottles", str(len(f)))
with summary_right:
    st.metric("Rated pours", str(len(events_df)))
with summary_third:
    scope_label = "Global" if scope == "Global" else f"My Stats ({display_name})"
    st.caption(f"Scope: **{scope_label}**")

# If empty because of filters, give the user a way out
if f.empty:
    card(
        "Nothing matches your filters",
        "Try lowering <b>Min rated pours</b> to 1, switching to <b>All time</b>, or hit <b>Reset filters</b>.",
    )
    st.stop()


# ============================================================
# LEADERBOARD (with per-row Open)
# ============================================================
st.subheader("Leaderboard")

# Keep it bar-vibe: top cards (buttons per row), then the full table below.
top_cards_n = min(25, len(f))

for i in range(top_cards_n):
    row = f.iloc[i]
    label = row["label"]
    avg_rating = float(row["avg_rating"])
    rating_count = int(row["rating_count"])

    meta_bits = []
    if str(row.get("category") or "").strip():
        meta_bits.append(str(row.get("category")))
    if str(row.get("mashbill_style") or "").strip():
        meta_bits.append(str(row.get("mashbill_style")))
    proof_val = row.get("proof")
    if proof_val is not None and str(proof_val).strip():
        meta_bits.append(f"Proof {proof_val}")

    meta = " · ".join(meta_bits) if meta_bits else "—"

    left, right = st.columns([6, 1])
    with left:
        st.markdown(f"**{i+1}. {label}**")
        st.caption(f"Board Avg: {avg_rating:.2f}  |  Rated pours: {rating_count}  |  {meta}")
    with right:
        if st.button("Open", key=f"rk_open_{row['bottle_id']}"):
            st.session_state["active_bottle_id"] = row["bottle_id"]
            st.session_state["active_bottle_label"] = label
            st.success("Active bottle set. Click Bottles in the sidebar.")
            st.rerun()

    st.divider()

# Full table (for power users)
st.subheader("Full table")

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
display_df["avg_rating"] = display_df["avg_rating"].map(lambda x: f"{float(x):.2f}")

st.dataframe(display_df, use_container_width=True, hide_index=True)
