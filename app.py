import streamlit as st

st.set_page_config(page_title="Viscosity", page_icon="🥃", layout="centered")

# Route users to the Welcome page so they never land on "app"
st.switch_page("pages/0_Welcome.py")
