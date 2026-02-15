import streamlit as st
from supabase import create_client

# Cookie manager (Streamlit component)
from streamlit_cookies_manager import EncryptedCookieManager


def get_cookie_manager():
    # You must set a password in Streamlit Cloud secrets for encryption
    # COOKIE_PASSWORD should be a long random string
    cookies = EncryptedCookieManager(
        prefix="viscosity_",
        password=st.secrets["COOKIE_PASSWORD"],
    )
    if not cookies.ready():
        st.stop()
    return cookies


def save_login(cookies, *, group_id: str, group_name: str, member_id: str, display_name: str):
    cookies["active_group_id"] = group_id
    cookies["group_name"] = group_name
    cookies["member_id"] = member_id
    cookies["display_name"] = display_name
    cookies.save()


def clear_login(cookies):
    for k in ["active_group_id", "group_name", "member_id", "display_name"]:
        if k in cookies:
            del cookies[k]
    cookies.save()


def restore_login_if_possible(sb):
    # If session already set, do nothing
    if "active_group_id" in st.session_state and "member_id" in st.session_state:
        return

    cookies = get_cookie_manager()

    group_id = cookies.get("active_group_id")
    member_id = cookies.get("member_id")
    group_name = cookies.get("group_name")
    display_name = cookies.get("display_name")

    if not group_id or not member_id:
        return

    # Validate the member still exists and belongs to the group
    res = (
        sb.table("group_members")
        .select("id, group_id, display_name")
        .eq("id", member_id)
        .limit(1)
        .execute()
        .data
    )
    if not res:
        clear_login(cookies)
        return

    row = res[0]
    if row["group_id"] != group_id:
        clear_login(cookies)
        return

    st.session_state["active_group_id"] = group_id
    st.session_state["member_id"] = member_id
    st.session_state["group_name"] = group_name or "Group"
    st.session_state["display_name"] = display_name or row.get("display_name") or "Member"
