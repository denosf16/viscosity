from __future__ import annotations

from datetime import datetime

import streamlit as st
from supabase import create_client

from lib.storage import public_object_url


# ---------- Setup ----------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------- Session Guard ----------
if "active_group_id" not in st.session_state or "member_id" not in st.session_state:
    st.warning("You must create or join a group first.")
    st.stop()

group_id = st.session_state["active_group_id"]
member_id = st.session_state["member_id"]


def bottle_label(b: dict) -> str:
    brand = b.get("brand") or ""
    expr = b.get("expression")
    return f"{brand} - {expr}" if expr else brand


# ---------- Load bottles (lightweight list) ----------
bottles_list = sb.table("bottles").select("id, brand, expression").execute().data
label_to_id = {bottle_label(b): b["id"] for b in bottles_list}
all_labels = sorted(label_to_id.keys())


# ---------- UI ----------
st.title("Bottles 🍾")
st.caption("Search the global catalog. Select a bottle to view ratings, discussion, and attachments.")

search_text = st.text_input("Search bottles", placeholder="Try: Buffalo Trace, Four Roses, Maker's...")

labels = all_labels
if search_text.strip():
    s = search_text.strip().lower()
    labels = [x for x in all_labels if s in x.lower()]

if not labels:
    st.info("No bottles match your search.")
    st.stop()

default_label = st.session_state.get("active_bottle_label")
default_index = labels.index(default_label) if default_label in labels else 0

selected_label = st.selectbox("Select a bottle", labels, index=default_index)
bottle_id = label_to_id[selected_label]

st.session_state["active_bottle_id"] = bottle_id
st.session_state["active_bottle_label"] = selected_label


# ---------- Load selected bottle details ----------
bottle_rows = (
    sb.table("bottles")
    .select("id, brand, expression, distillery, distillery_location, proof, barrel_type, mashbill_style, category")
    .eq("id", bottle_id)
    .execute()
    .data
)

if not bottle_rows:
    st.error("Selected bottle not found.")
    st.stop()

b = bottle_rows[0]


# ---------- Bottle Detail ----------
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


# ---------- My Rating (editable) ----------
st.subheader("My Rating")

existing_my = (
    sb.table("ratings")
    .select("id, rating, notes, location")
    .eq("group_id", group_id)
    .eq("bottle_id", bottle_id)
    .eq("member_id", member_id)
    .execute()
    .data
)

my_row = existing_my[0] if existing_my else None

default_rating = int(my_row["rating"]) if my_row else 7
default_notes = (my_row.get("notes") or "") if my_row else ""
default_location = (my_row.get("location") or "") if my_row else ""

my_rating = st.slider("Rating (1–10)", 1, 10, default_rating)
my_location = st.text_input("Location (optional)", value=default_location)
my_notes = st.text_area("Notes (optional)", value=default_notes, height=140)

save_clicked = st.button("Save Rating", key="save_rating_btn")

if save_clicked:
    rating_val = int(my_rating)
    loc_val = my_location.strip() if my_location.strip() else None
    notes_val = my_notes.strip() if my_notes.strip() else None
    now_iso = datetime.utcnow().isoformat()

    if my_row:
        sb.table("ratings").update(
            {
                "rating": rating_val,
                "location": loc_val,
                "notes": notes_val,
                "updated_at": now_iso,
            }
        ).eq("id", my_row["id"]).execute()
        st.success("Rating updated!")
    else:
        sb.table("ratings").insert(
            {
                "group_id": group_id,
                "bottle_id": bottle_id,
                "member_id": member_id,
                "rating": rating_val,
                "location": loc_val,
                "notes": notes_val,
            }
        ).execute()
        st.success("Rating saved!")

    st.rerun()

st.divider()


# ---------- Group Rating Stats ----------
st.subheader("Group Rating Stats")

ratings_res = (
    sb.table("ratings")
    .select("rating", count="exact")
    .eq("group_id", group_id)
    .eq("bottle_id", bottle_id)
    .execute()
)

ratings = ratings_res.data or []
count_ratings = ratings_res.count or 0

if count_ratings == 0:
    st.info("No ratings yet for this bottle in this group.")
else:
    avg_rating = sum(r["rating"] for r in ratings) / count_ratings
    st.metric("Avg Rating (Group)", f"{avg_rating:.2f}")
    st.metric("Rating Count (Group)", str(count_ratings))

st.divider()


# ---------- Attachments ----------
st.subheader("Attachments")

media_rows = (
    sb.table("media")
    .select("media_type, storage_bucket, storage_path, created_at")
    .eq("group_id", group_id)
    .eq("bottle_id", bottle_id)
    .order("created_at", desc=True)
    .limit(50)
    .execute()
    .data
)

if not media_rows:
    st.caption("No photos or audio yet for this bottle.")
else:
    for m in media_rows:
        url = public_object_url(SUPABASE_URL, m["storage_bucket"], m["storage_path"])
        if m["media_type"] == "photo":
            st.image(url, caption=m["created_at"], use_container_width=True)
        else:
            st.audio(url)
            st.caption(m["created_at"])

st.divider()


# ---------- Discussion Thread ----------
st.subheader("Discussion")

new_comment = st.text_area(
    "Write a comment",
    placeholder="Drop tasting notes, comparisons, hot takes, whatever...",
    height=120,
)

post_col1, post_col2 = st.columns([1, 3])
with post_col1:
    post_clicked = st.button("Post Comment", key="post_comment_btn")
with post_col2:
    st.caption("Comments are visible to everyone in this group.")

if post_clicked:
    body = (new_comment or "").strip()
    if not body:
        st.error("Comment cannot be blank.")
    else:
        sb.table("comments").insert(
            {
                "group_id": group_id,
                "bottle_id": bottle_id,
                "member_id": member_id,
                "body": body,
                "parent_comment_id": None,
            }
        ).execute()
        st.success("Comment posted!")
        st.rerun()

st.divider()

comments = (
    sb.table("comments")
    .select("id, created_at, body, member_id")
    .eq("group_id", group_id)
    .eq("bottle_id", bottle_id)
    .order("created_at", desc=True)
    .limit(200)
    .execute()
    .data
)

if not comments:
    st.info("No comments yet. Start the conversation.")
    st.stop()

member_ids = list({c["member_id"] for c in comments})
members = (
    sb.table("group_members")
    .select("id, display_name")
    .in_("id", member_ids)
    .execute()
    .data
)
name_by_id = {m["id"]: m["display_name"] for m in members}

st.caption(f"Showing {len(comments)} comments (newest first).")

for c in comments:
    name = name_by_id.get(c["member_id"], "Someone")
    st.markdown(f"**{name}**")
    st.write(c["body"])
    st.caption(c["created_at"])
    st.divider()
