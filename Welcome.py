# Welcome.py
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
from supabase import create_client

from lib.ui import apply_speakeasy_theme, card
from lib.device_token import get_or_create_device_token


# ============================================================
# SETUP
# ============================================================
st.set_page_config(page_title="Welcome", page_icon="🥃", layout="centered")
apply_speakeasy_theme()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

device_token = get_or_create_device_token()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# IDENTITY RESTORE (device_sessions -> display_name)
# ============================================================
if "display_name" not in st.session_state or not (st.session_state.get("display_name") or "").strip():
    try:
        rows = (
            sb.table("device_sessions")
            .select("display_name")
            .eq("token", device_token)
            .limit(1)
            .execute()
            .data
        ) or []
        if rows and (rows[0].get("display_name") or "").strip():
            st.session_state["display_name"] = rows[0]["display_name"].strip()

            # best-effort touch
            try:
                sb.table("device_sessions").update(
                    {"last_seen_at": utc_now_iso()}
                ).eq("token", device_token).execute()
            except Exception:
                pass
    except Exception:
        pass


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("## Welcome")
st.sidebar.caption(f"Device token: `{device_token[:10]}…`")

display_name = (st.session_state.get("display_name") or "").strip() or None
if display_name:
    st.sidebar.success(f"You: {display_name}")
else:
    st.sidebar.warning("No drinking name yet")


# ============================================================
# MAIN
# ============================================================
st.title("Welcome to Viscosity 🥃")
st.caption("Real bars are private and intentional. This is where people share what’s worth ordering.")
st.divider()

# ------------------------------------------------------------
# SET YOUR DRINKING NAME
# ------------------------------------------------------------
st.subheader("Set your drinking name")

name_input = st.text_input(
    "Drinking name",
    value=display_name or "",
    placeholder="Example: Sandman, OakKing, BarrelBandit",
)

save_disabled = not name_input.strip()

if st.button("Save name", disabled=save_disabled):
    clean = name_input.strip()

    st.session_state["display_name"] = clean

    # Upsert device_sessions row keyed by token
    # Note: requires device_sessions.display_name to exist (you added this)
    try:
        existing = (
            sb.table("device_sessions")
            .select("id")
            .eq("token", device_token)
            .limit(1)
            .execute()
            .data
        ) or []

        if existing:
            sb.table("device_sessions").update(
                {"display_name": clean, "last_seen_at": utc_now_iso()}
            ).eq("token", device_token).execute()
        else:
            sb.table("device_sessions").insert(
                {"token": device_token, "display_name": clean, "last_seen_at": utc_now_iso()}
            ).execute()
    except Exception:
        # Even if Supabase write fails, keep local session value
        pass

    st.success("Name saved.")
    st.rerun()

st.divider()

# ------------------------------------------------------------
# WHAT THIS IS
# ------------------------------------------------------------
card(
    "The idea",
    "Walk into a good bar, overhear what’s worth ordering, and leave a note for the next person.<br>"
    "No accounts. No joining. Just pours, tags, and taste history.",
)

card(
    "How it works",
    "1. Set your drinking name (above)<br>"
    "2. Go to <b>Bottles</b> and drop a pour (rating + notes)<br>"
    "3. Use <b>Tags</b> to filter the vibe<br>"
    "4. Check <b>Rankings</b> for the statistical summary",
)

c1, c2 = st.columns(2)
with c1:
    card(
        "What’s live",
        "- Global bottle catalog<br>"
        "- Pours with ratings and notes<br>"
        "- Tag filters<br>"
        "- Rankings from pours",
    )
with c2:
    card(
        "Later",
        "- Attachments (photos, audio)<br>"
        "- Better discovery (trending bottles)<br>"
        "- More stats (time windows, tag leaderboards)",
    )

st.caption("Built like a bar board. Premium by voice, not by gates.")
