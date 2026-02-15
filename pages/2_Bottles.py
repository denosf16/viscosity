# pages/2_Bottle.py
from __future__ import annotations

import re
from datetime import datetime, timezone

import streamlit as st
from supabase import create_client

from lib.ui import apply_speakeasy_theme, card
from lib.device_token import get_or_create_device_token


# ============================================================
# SETUP
# ============================================================
st.set_page_config(page_title="Bottle", page_icon="🥃", layout="wide")
apply_speakeasy_theme()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

device_token = get_or_create_device_token()
display_name = (st.session_state.get("display_name") or "").strip() or None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(s: str | None) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _norm_key(s: str | None) -> str:
    return _clean_text(s).lower()


def bottle_label(b: dict) -> str:
    brand = _clean_text(b.get("brand"))
    expr = _clean_text(b.get("expression"))
    return f"{brand} - {expr}" if expr else brand


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("## Bottle")
st.sidebar.caption(f"Device: `{device_token[:10]}…`")

if display_name:
    st.sidebar.success(f"You: {display_name}")
else:
    st.sidebar.warning("Set your drinking name on Welcome to interact")


# ============================================================
# MAIN
# ============================================================
st.title("Bottle Page 🥃")
st.caption("Search the catalog, drop a pour, and build the board.")
st.divider()

# ---------- Load bottles for picker ----------
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
# ADD NEW BOTTLE (requires drinking name)
# ============================================================
with st.expander("Add a new bottle", expanded=False):
    if not display_name:
        st.info("Set your drinking name on Welcome to add bottles.")
    else:
        st.caption("Keep it simple: brand required, expression optional. We prevent duplicates.")
        nb1, nb2 = st.columns([2, 2])

        with nb1:
            new_brand = st.text_input("Brand (required)", key="new_bottle_brand")
            new_expression = st.text_input("Expression (optional)", key="new_bottle_expression")

        with nb2:
            new_category = st.text_input("Category (optional)", key="new_bottle_category")
            new_proof = st.number_input("Proof (optional)", min_value=0.0, max_value=200.0, value=0.0, step=0.5)

        nb3, nb4 = st.columns([2, 2])
        with nb3:
            new_distillery = st.text_input("Distillery (optional)", key="new_bottle_distillery")
            new_location = st.text_input("Distillery Location (optional)", key="new_bottle_distillery_location")
        with nb4:
            new_barrel = st.text_input("Barrel Type (optional)", key="new_bottle_barrel_type")
            new_mashbill = st.text_input("Mashbill Style (optional)", key="new_bottle_mashbill_style")

        add_clicked = st.button("Add bottle", key="add_bottle_btn", disabled=(not _clean_text(new_brand)))

        if add_clicked:
            brand_clean = _clean_text(new_brand)
            expr_clean = _clean_text(new_expression)

            # ---------- Duplicate check (case-insensitive) ----------
            # Pull candidates by brand (cheap) then compare normalized keys in Python
            try:
                candidates = (
                    sb.table("bottles")
                    .select("id, brand, expression")
                    .ilike("brand", brand_clean)
                    .limit(50)
                    .execute()
                    .data
                ) or []
            except Exception:
                candidates = []

            target_brand_k = _norm_key(brand_clean)
            target_expr_k = _norm_key(expr_clean)  # empty => ""

            match = None
            for c in candidates:
                if _norm_key(c.get("brand")) != target_brand_k:
                    continue
                c_expr_k = _norm_key(c.get("expression"))
                if c_expr_k == target_expr_k:
                    match = c
                    break

            if match:
                # Use existing
                existing_label = bottle_label(match)
                st.session_state["active_bottle_id"] = match["id"]
                st.session_state["active_bottle_label"] = existing_label
                st.success(f"Already exists. Opened: {existing_label}")
                st.rerun()

            # ---------- Lightweight "possible matches" ----------
            possible = []
            for c in candidates:
                # same brand (normalized) but different expression, or brand contains overlap
                if target_brand_k in _norm_key(c.get("brand")) or _norm_key(c.get("brand")) in target_brand_k:
                    possible.append(c)

            if possible and not expr_clean:
                st.warning("Possible matches found. If one of these is what you meant, use it instead of creating a duplicate.")
                for c in possible[:5]:
                    plabel = bottle_label(c)
                    if st.button(f"Use existing: {plabel}", key=f"use_existing_{c['id']}"):
                        st.session_state["active_bottle_id"] = c["id"]
                        st.session_state["active_bottle_label"] = plabel
                        st.rerun()

            # ---------- Insert new bottle ----------
            payload = {
                "brand": brand_clean,
                "expression": expr_clean if expr_clean else None,
                "category": _clean_text(new_category) or None,
                "proof": float(new_proof) if float(new_proof) > 0 else None,
                "distillery": _clean_text(new_distillery) or None,
                "distillery_location": _clean_text(new_location) or None,
                "barrel_type": _clean_text(new_barrel) or None,
                "mashbill_style": _clean_text(new_mashbill) or None,
                # optional columns you might have:
                # "created_by_device_token": device_token,
                # "created_by_display_name": display_name,
            }

            try:
                res = sb.table("bottles").insert(payload).execute().data or []
                if not res:
                    st.error("Bottle insert returned no rows.")
                    st.stop()

                new_id = res[0]["id"]
                new_label = bottle_label(res[0])

                st.session_state["active_bottle_id"] = new_id
                st.session_state["active_bottle_label"] = new_label

                st.success(f"Added: {new_label}")
                st.rerun()

            except Exception as e:
                st.error(f"Add bottle failed: {e}")

st.divider()

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
# DROP A POUR (requires drinking name)
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
        "event_type": "having_a_glass",
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
