import streamlit as st

SPEAKEASY_CSS = """
<style>
/* ---- Layout breathing room ---- */
.block-container {
  padding-top: 2rem;
  padding-bottom: 2.5rem;
  max-width: 980px;
}

/* ---- Typography ---- */
h1, h2, h3, h4 {
  letter-spacing: 0.2px;
}

.stCaption, .stMarkdown p {
  color: rgba(242, 239, 234, 0.86);
}

/* ---- Sidebar polish ---- */
section[data-testid="stSidebar"] {
  background: #121416;
  border-right: 1px solid rgba(255,255,255,0.06);
}

/* ---- Buttons ---- */
.stButton > button {
  border-radius: 12px;
  padding: 0.55rem 0.9rem;
  font-weight: 650;
  border: 1px solid rgba(255,255,255,0.10);
  box-shadow: 0 8px 18px rgba(0,0,0,0.25);
}

.stButton > button:hover {
  border: 1px solid rgba(201,138,58,0.55);
  box-shadow: 0 10px 22px rgba(0,0,0,0.35);
}

/* ---- Inputs ---- */
input, textarea {
  border-radius: 12px !important;
}

/* ---- “Card” container ---- */
.v-card {
  background: rgba(21, 24, 27, 0.92);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 10px 22px rgba(0,0,0,0.35);
  margin-bottom: 14px;
}

.v-card-title {
  font-size: 1.05rem;
  font-weight: 750;
  color: #F2EFEA;
  margin-bottom: 6px;
}

.v-muted {
  color: rgba(242, 239, 234, 0.74);
}
</style>
"""

def apply_speakeasy_theme() -> None:
    """Call once at the top of each page."""
    st.markdown(SPEAKEASY_CSS, unsafe_allow_html=True)

def card(title: str, body_md: str) -> None:
    """Simple reusable card."""
    st.markdown(
        f"""
        <div class="v-card">
          <div class="v-card-title">{title}</div>
          <div class="v-muted">{body_md}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
