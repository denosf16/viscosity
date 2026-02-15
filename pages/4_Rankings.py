import pandas as pd
import streamlit as st
from supabase import create_client


# ---------- Setup ----------
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(url, key)


# ---------- Session Guard ----------
if "active_group_id" not in st.session_state or "member_id" not in st.session_state:
    st.warning("You must create or join a group first.")
    st.stop()

group_id = st.session_state["active_group_id"]


def bottle_label(brand: str | None, expression: str | None) -> str:
    brand = (brand or "").strip()
    expr = (expression or "").strip()
    return f"{brand} - {expr}" if expr else brand


# ---------- UI ----------
st.title("Rankings 🏆")
st.caption("Group rankings based on average rating with minimum review filters.")

# ---------- Load data ----------
ratings_rows = (
    sb.table("ratings")
    .select("bottle_id, rating")
    .eq("group_id", group_id)
    .execute()
    .data
)

if not ratings_rows:
    st.info("No ratings yet in this group. Go rate a bottle first.")
    st.stop()

bottle_ids = list({r["bottle_id"] for r in ratings_rows})

bottles_rows = (
    sb.table("bottles")
    .select("id, brand, expression, category, mashbill_style, proof, distillery, distillery_location, barrel_type")
    .in_("id", bottle_ids)
    .execute()
    .data
)

# ---------- Aggregate in Python ----------
ratings_df = pd.DataFrame(ratings_rows)
bottles_df = pd.DataFrame(bottles_rows)

agg = (
    ratings_df.groupby("bottle_id", as_index=False)
    .agg(avg_rating=("rating", "mean"), rating_count=("rating", "size"))
)

df = agg.merge(bottles_df, left_on="bottle_id", right_on="id", how="left")

df["label"] = df.apply(lambda x: bottle_label(x.get("brand"), x.get("expression")), axis=1)

# Clean types
df["avg_rating"] = df["avg_rating"].astype(float)
df["rating_count"] = df["rating_count"].astype(int)

# ---------- Controls ----------
st.subheader("Filters")

left, mid, right = st.columns([2, 2, 1])

with left:
    search_text = st.text_input("Search", placeholder="Type brand or expression...")

with mid:
    categories = sorted([c for c in df["category"].dropna().unique().tolist() if str(c).strip()])
    category_filter = st.selectbox("Category", ["All"] + categories)

with right:
    min_reviews = st.number_input("Min reviews", min_value=1, max_value=50, value=1, step=1)

styles = sorted([c for c in df["mashbill_style"].dropna().unique().tolist() if str(c).strip()])
mashbill_filter = st.selectbox("Mashbill Style", ["All"] + styles)

# Apply filters
f = df.copy()

if search_text.strip():
    s = search_text.strip().lower()
    f = f[f["label"].str.lower().str.contains(s, na=False)]

if category_filter != "All":
    f = f[f["category"] == category_filter]

if mashbill_filter != "All":
    f = f[f["mashbill_style"] == mashbill_filter]

f = f[f["rating_count"] >= int(min_reviews)]

# Sorting
f = f.sort_values(["avg_rating", "rating_count", "label"], ascending=[False, False, True])

# ---------- Summary ----------
st.divider()

summary_left, summary_right = st.columns(2)
with summary_left:
    st.metric("Rated bottles (after filters)", str(len(f)))
with summary_right:
    st.metric("Total ratings (group)", str(len(ratings_df)))

# ---------- Results ----------
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

# ---------- Quick open in Bottles page ----------
st.subheader("Open a bottle")

label_choice = st.selectbox("Choose from current filtered list", f["label"].tolist())

if st.button("Set as active bottle", key="set_active_bottle_btn"):
    row = f[f["label"] == label_choice].iloc[0]
    st.session_state["active_bottle_id"] = row["bottle_id"]
    st.session_state["active_bottle_label"] = row["label"]
    st.success("Active bottle set. Click the Bottles page in the sidebar to view it.")
