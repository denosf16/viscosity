# pages/2_Tags.py
import re

import streamlit as st
from supabase import create_client

from lib.ui import apply_speakeasy_theme, card
from lib.device_token import get_or_create_device_token


# ============================================================
# SETUP
# ============================================================
st.set_page_config(page_title="Tags", page_icon="🏷️", layout="wide")
apply_speakeasy_theme()

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(url, key)

device_token = get_or_create_device_token()
display_name = st.session_state.get("display_name")


# ============================================================
# HELPERS
# ============================================================
def _normalize_tag(x: str) -> str:
    """
    Tags are light, fun, and consistent.
    - Trim
    - Collapse whitespace
    - Remove weird punctuation
    - Uppercase for a premium "label" feel
    """
    x = (x or "").strip()
    x = re.sub(r"\s+", " ", x)
    x = re.sub(r"[^A-Za-z0-9 _-]", "", x)
    x = x.replace(" ", "_")
    x = x.strip("_-")
    return x.upper()


def _set_active_tag(tag: str) -> None:
    st.session_state["active_tag"] = tag or ""


def _get_active_tag() -> str:
    return (st.session_state.get("active_tag") or "").strip()


def _fetch_popular_tags(limit: int = 12) -> list[str]:
    """
    Best-effort popularity.
    If events.primary_tag exists, we can query it directly.
    If not, return a tasteful default list.
    """
    defaults = ["ACTION", "VEGAS_TRIP", "SPEAKEASY", "BUDGET_HEAT", "DATE_NIGHT", "NEW_BOTTLE", "RYES", "BOURBON", "FINISH_FWD", "CIGAR"]

    try:
        rows = (
            sb.table("events")
            .select("primary_tag")
            .not_.is_("primary_tag", "null")
            .limit(500)
            .execute()
            .data
        ) or []
        tags = [r.get("primary_tag") for r in rows if r.get("primary_tag")]
        tags = [_normalize_tag(t) for t in tags if str(t).strip()]
        if not tags:
            return defaults[:limit]

        # simple frequency count without importing Counter
        freq = {}
        for t in tags:
            freq[t] = freq.get(t, 0) + 1
        tags_sorted = sorted(freq.keys(), key=lambda k: (-freq[k], k))
        return tags_sorted[:limit]
    except Exception:
        return defaults[:limit]


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("## Tags")
st.sidebar.caption(f"Device: `{device_token[:10]}…`")

if display_name:
    st.sidebar.success(f"You: {display_name}")
else:
    st.sidebar.warning("No drinking name yet")
    st.sidebar.caption("You can browse tags and the feed. Set your name on Welcome to post.")


# ============================================================
# MAIN
# ============================================================
st.title("Tags 🏷️")
st.caption("Tags are the vibe. They organize context, not access.")
st.divider()

active_tag = _get_active_tag()

# Current selection
if active_tag:
    card("Active tag filter", f"`{active_tag}` is currently filtering the Home feed.")
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("Clear filter"):
            _set_active_tag("")
            st.success("Tag filter cleared.")
            st.rerun()
    with c2:
        st.caption("Go back to Home to see the global feed without a tag filter.")
else:
    card("No active tag filter", "You are seeing the full feed. Pick a tag below to focus the room.")

st.divider()

# Popular tags
st.subheader("Popular tags")

popular = _fetch_popular_tags(limit=12)
if not popular:
    st.info("No tags found yet.")
else:
    cols = st.columns(4)
    for i, t in enumerate(popular):
        with cols[i % 4]:
            if st.button(t, key=f"tag_btn_{t}"):
                _set_active_tag(t)
                st.success(f"Filtering feed by {t}")
                st.rerun()

st.divider()

# Create tag
st.subheader("Create a new tag")

new_tag_raw = st.text_input(
    "New tag",
    placeholder="Examples: ACTION, VEGAS_TRIP, CIGAR, DATE_NIGHT",
)

new_tag = _normalize_tag(new_tag_raw)

if new_tag_raw and not new_tag:
    st.error("Tag must contain letters or numbers.")

c1, c2 = st.columns([1, 2])
with c1:
    if st.button("Use this tag", disabled=(not new_tag)):
        _set_active_tag(new_tag)
        st.success(f"Filtering feed by {new_tag}")
        st.rerun()

with c2:
    st.caption("Tags are free-text for now. Later we can add follow lists and moderation tools.")
