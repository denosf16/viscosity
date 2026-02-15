import random
import string

import streamlit as st
from supabase import create_client


# ---------- Setup ----------
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(url, key)


def generate_join_code(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


st.title("Create or Join Group 🥃")
st.divider()

tab1, tab2 = st.tabs(["Create Group", "Join Group"])

# ============================================================
# CREATE GROUP
# ============================================================
with tab1:
    st.subheader("Create a New Group")

    group_name = st.text_input("Group Name")
    display_name = st.text_input("Your Display Name", key="create_display_name")

    if st.button("Create Group"):
        if not group_name.strip():
            st.error("Group name required.")
            st.stop()

        if not display_name.strip():
            st.error("Display name required.")
            st.stop()

        # Generate unique join code
        join_code = generate_join_code()

        # Insert group
        group_res = (
            sb.table("groups")
            .insert({"name": group_name.strip(), "join_code": join_code})
            .execute()
            .data
        )

        if not group_res:
            st.error("Failed to create group.")
            st.stop()

        group_id = group_res[0]["id"]

        # Insert creator as member
        member_res = (
            sb.table("group_members")
            .insert(
                {
                    "group_id": group_id,
                    "display_name": display_name.strip(),
                }
            )
            .execute()
            .data
        )

        if not member_res:
            st.error("Failed to join group.")
            st.stop()

        member_id = member_res[0]["id"]

        # Set session
        st.session_state["active_group_id"] = group_id
        st.session_state["group_name"] = group_name.strip()
        st.session_state["member_id"] = member_id
        st.session_state["display_name"] = display_name.strip()

        st.success(f"Group created! Join Code: {join_code}")
        st.rerun()


# ============================================================
# JOIN GROUP
# ============================================================
with tab2:
    st.subheader("Join Existing Group")

    join_code_input = st.text_input("Join Code")
    display_name_join = st.text_input("Your Display Name", key="join_display_name")

    if st.button("Join Group"):
        if not join_code_input.strip():
            st.error("Join code required.")
            st.stop()

        if not display_name_join.strip():
            st.error("Display name required.")
            st.stop()

        group_res = (
            sb.table("groups")
            .select("*")
            .eq("join_code", join_code_input.strip().upper())
            .execute()
            .data
        )

        if not group_res:
            st.error("Invalid join code.")
            st.stop()

        group = group_res[0]
        group_id = group["id"]

        # Check if display name already exists in group
        existing_member = (
            sb.table("group_members")
            .select("*")
            .eq("group_id", group_id)
            .eq("display_name", display_name_join.strip())
            .execute()
            .data
        )

        if existing_member:
            member_id = existing_member[0]["id"]
        else:
            member_res = (
                sb.table("group_members")
                .insert(
                    {
                        "group_id": group_id,
                        "display_name": display_name_join.strip(),
                    }
                )
                .execute()
                .data
            )
            member_id = member_res[0]["id"]

        st.session_state["active_group_id"] = group_id
        st.session_state["group_name"] = group["name"]
        st.session_state["member_id"] = member_id
        st.session_state["display_name"] = display_name_join.strip()

        st.success("Joined successfully!")
        st.rerun()
