# lib/device_token.py
import secrets
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components


DEVICE_TOKEN_KEY = "viscosity_device_token"
URL_PARAM_KEY = "t"


def _js_set_local_storage(storage_key: str, token: str) -> str:
    # Best effort write. Streamlit cannot reliably read it back.
    safe_token = token.replace('"', "")
    return f"""
    <script>
      try {{
        window.localStorage.setItem("{storage_key}", "{safe_token}");
      }} catch (e) {{}}
    </script>
    """


def _get_query_param(key: str) -> Optional[str]:
    # Streamlit API compatibility across versions
    try:
        qp = st.query_params
        val = qp.get(key)
        if isinstance(val, list):
            val = val[0] if val else None
        return val
    except Exception:
        try:
            qp = st.experimental_get_query_params()
            val = qp.get(key, [None])[0]
            return val
        except Exception:
            return None


def _set_query_param(key: str, value: str) -> None:
    # Streamlit API compatibility across versions
    try:
        st.query_params[key] = value
    except Exception:
        try:
            st.experimental_set_query_params(**{key: value})
        except Exception:
            pass


def get_or_create_device_token(force_new: bool = False) -> str:
    """
    Stable device token without relying on cookie libraries.
    Approach:
      1) Prefer URL query param ?t=... (readable from Python and persists across refresh)
      2) If missing, generate a new token, write it into URL query params
      3) Best-effort also write into localStorage (write-only, not relied on)

    This guarantees token stability for:
      - hard refresh
      - new tab
      - returning later via browser history/bookmark

    If you want to rotate token for testing, pass force_new=True.
    """
    if not force_new:
        existing = _get_query_param(URL_PARAM_KEY)
        if existing:
            st.session_state["device_token"] = existing
            return existing

        existing_ss = st.session_state.get("device_token")
        if existing_ss:
            _set_query_param(URL_PARAM_KEY, existing_ss)
            return existing_ss

    token = secrets.token_urlsafe(24)
    st.session_state["device_token"] = token
    _set_query_param(URL_PARAM_KEY, token)

    # Best effort: write to localStorage too (not required for correctness)
    components.html(_js_set_local_storage(DEVICE_TOKEN_KEY, token), height=0)

    return token


def clear_device_token() -> None:
    """
    Clears session token and removes the URL param.
    Best-effort clears localStorage too.
    """
    st.session_state.pop("device_token", None)
    _set_query_param(URL_PARAM_KEY, "")

    components.html(
        f"""
        <script>
          try {{
            window.localStorage.removeItem("{DEVICE_TOKEN_KEY}");
          }} catch (e) {{}}
        </script>
        """,
        height=0,
    )
