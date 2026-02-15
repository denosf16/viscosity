from __future__ import annotations

from datetime import datetime

import streamlit as st
from supabase import create_client

from lib.storage import guess_mime_type, make_storage_path, public_object_url


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


# ---------- UI ----------
st.title("Add Review ✍️")
st.caption("Fast flow for adding or updating your rating and notes, with optional photo/audio attachments.")

# ---------- Bottle picker (search + select) ----------
bottles = sb.table("bottles").select("id, brand, expression").execute().data
label_to_id = {bottle_label(b): b["id"] for b in bottles}
all_labels = sorted(label_to_id.keys())

search_text = st.text_input("Search bottles", placeholder="Type brand or expression...")

labels = all_labels
if search_text.strip():
    s = search_text.strip().lower()
    labels = [x for x in all_labels if s in x.lower()]

if not labels:
    st.info("No bottles match your search.")
    st.stop()

default_label = st.session_state.get("active_bottle_label")
default_index = labels.index(default_label) if default_label in labels else 0

selected_label = st.selectbox("Bottle", labels, index=default_index)
bottle_id = label_to_id[selected_label]

st.session_state["active_bottle_id"] = bottle_id
st.session_state["active_bottle_label"] = selected_label

st.divider()

# ---------- Load existing rating ----------
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

st.subheader("Your Review")

rating_val = st.slider("Rating (1–10)", 1, 10, default_rating)
location_val = st.text_input("Location (optional)", value=default_location)
notes_val = st.text_area("Notes (optional)", value=default_notes, height=180)

save_clicked = st.button("Save Review", key="save_review_btn")

if save_clicked:
    loc = location_val.strip() if location_val.strip() else None
    notes = notes_val.strip() if notes_val.strip() else None
    now_iso = datetime.utcnow().isoformat()

    if my_row:
        sb.table("ratings").update(
            {
                "rating": int(rating_val),
                "location": loc,
                "notes": notes,
                "updated_at": now_iso,
            }
        ).eq("id", my_row["id"]).execute()
        st.success("Review updated!")
    else:
        sb.table("ratings").insert(
            {
                "group_id": group_id,
                "bottle_id": bottle_id,
                "member_id": member_id,
                "rating": int(rating_val),
                "location": loc,
                "notes": notes,
            }
        ).execute()
        st.success("Review saved!")

    st.rerun()

# Refresh rating row after save so uploads can link to rating_id
my_row_refresh = (
    sb.table("ratings")
    .select("id")
    .eq("group_id", group_id)
    .eq("bottle_id", bottle_id)
    .eq("member_id", member_id)
    .execute()
    .data
)
rating_id = my_row_refresh[0]["id"] if my_row_refresh else None

st.divider()

# ---------- Uploads ----------
st.subheader("Attachments")

if not rating_id:
    st.info("Save your review first to attach photo or audio.")
    st.stop()

photo_file = st.file_uploader(
    "Upload a bottle photo (optional)",
    type=["jpg", "jpeg", "png", "webp"],
    key="photo_uploader",
)
audio_file = st.file_uploader(
    "Upload an audio note (optional)",
    type=["m4a", "mp3", "wav", "aac"],
    key="audio_uploader",
)

c1, c2 = st.columns(2)
with c1:
    upload_photo = st.button("Upload Photo", key="upload_photo_btn", disabled=(photo_file is None))
with c2:
    upload_audio = st.button("Upload Audio", key="upload_audio_btn", disabled=(audio_file is None))


def _upload_and_record(uploaded_file, media_type: str, bucket: str) -> str:
    filename = uploaded_file.name
    content_type = guess_mime_type(filename)
    storage_path = make_storage_path(
        group_id=group_id,
        bottle_id=bottle_id,
        member_id=member_id,
        media_type=media_type,
        filename=filename,
    )

    data_bytes = uploaded_file.getvalue()

    sb.storage.from_(bucket).upload(
        path=storage_path,
        file=data_bytes,
        file_options={"content-type": content_type, "upsert": "false"},
    )

    sb.table("media").insert(
        {
            "group_id": group_id,
            "bottle_id": bottle_id,
            "rating_id": rating_id,
            "comment_id": None,
            "member_id": member_id,
            "media_type": media_type,
            "storage_bucket": bucket,
            "storage_path": storage_path,
        }
    ).execute()

    return storage_path


if upload_photo and photo_file is not None:
    try:
        _upload_and_record(photo_file, media_type="photo", bucket="bottle_photos")
        st.success("Photo uploaded!")
        st.rerun()
    except Exception as e:
        st.error(f"Photo upload failed: {e}")

if upload_audio and audio_file is not None:
    try:
        _upload_and_record(audio_file, media_type="audio", bucket="review_audio")
        st.success("Audio uploaded!")
        st.rerun()
    except Exception as e:
        st.error(f"Audio upload failed: {e}")

st.divider()

# ---------- Show my attachments for this rating ----------
st.subheader("My Attachments (this bottle)")

media_rows = (
    sb.table("media")
    .select("id, media_type, storage_bucket, storage_path, created_at")
    .eq("group_id", group_id)
    .eq("bottle_id", bottle_id)
    .eq("rating_id", rating_id)
    .order("created_at", desc=True)
    .execute()
    .data
)

if not media_rows:
    st.caption("No attachments yet.")
else:
    for m in media_rows:
        url = public_object_url(SUPABASE_URL, m["storage_bucket"], m["storage_path"])
        if m["media_type"] == "photo":
            st.image(url, caption=m["created_at"], use_container_width=True)
        else:
            st.audio(url)
            st.caption(m["created_at"])
