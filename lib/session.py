from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Any

import streamlit as st

from lib.device_token import get_or_create_device_token


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def restore_login_if_possible(sb: Any) -> None:
    """
    Restores st.session_state from device_sessions using the device_token.
    No cookies. No extra dependencies.
    """
    # Already logged in this run
    if st.session_state.get("active_group_id") and st.session_state.get("member_id"):
        return

    token = get_or_create_device_token()

    session_res = (
        sb.table("device_sessions")
        .select("member_id, group_id")
        .eq("token", token)
        .limit(1)
        .execute()
        .data
    )

    if not session_res:
        return

    member_id = session_res[0]["member_id"]
    group_id = session_res[0]["group_id"]

    group_res = (
        sb.table("groups")
        .select("name")
        .eq("id", group_id)
        .limit(1)
        .execute()
        .data
    )

    member_res = (
        sb.table("group_members")
        .select("display_name")
        .eq("id", member_id)
        .limit(1)
        .execute()
        .data
    )

    if not group_res or not member_res:
        return

    st.session_state["active_group_id"] = group_id
    st.session_state["group_name"] = group_res[0]["name"]
    st.session_state["member_id"] = member_id
    st.session_state["display_name"] = member_res[0]["display_name"]

    # Touch last_seen_at (use an ISO timestamp, not "now()")
    try:
        sb.table("device_sessions").update(
            {"last_seen_at": _utc_now_iso()}
        ).eq("token", token).execute()
    except Exception:
        pass


def save_device_session(sb: Any, group_id: str, member_id: str) -> None:
    """
    Upserts device_sessions for this device_token so the next visit auto-restores.
    Call this after create/join.
    """
    token = get_or_create_device_token()

    payload = {
        "token": token,
        "group_id": group_id,
        "member_id": member_id,
        "last_seen_at": _utc_now_iso(),
    }

    # If you have a unique constraint on token, upsert is ideal.
    # Some Supabase Python versions support upsert(...). If not, fallback.
    try:
        sb.table("device_sessions").upsert(payload).execute()
        return
    except Exception:
        pass

    existing = (
        sb.table("device_sessions")
        .select("token")
        .eq("token", token)
        .limit(1)
        .execute()
        .data
    )

    if existing:
        sb.table("device_sessions").update(payload).eq("token", token).execute()
    else:
        sb.table("device_sessions").insert(payload).execute()
