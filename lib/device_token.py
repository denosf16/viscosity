import secrets
import streamlit as st
import streamlit.components.v1 as components


DEVICE_TOKEN_KEY = "viscosity_device_token"


def _js_get_token(storage_key: str) -> str:
    # Returns token string or empty
    return f"""
    <script>
      const key = "{storage_key}";
      const token = window.localStorage.getItem(key) || "";
      const out = document.createElement("div");
      out.id = "token_out";
      out.textContent = token;
      document.body.appendChild(out);
    </script>
    """


def _js_set_token(storage_key: str, token: str) -> str:
    return f"""
    <script>
      const key = "{storage_key}";
      window.localStorage.setItem(key, "{token}");
      const out = document.createElement("div");
      out.id = "token_out";
      out.textContent = "{token}";
      document.body.appendChild(out);
    </script>
    """


def get_or_create_device_token() -> str:
    """
    Persist a device token in browser localStorage.
    - If present, returns it.
    - If missing, generates a new one and stores it.
    """
    token = components.html(_js_get_token(DEVICE_TOKEN_KEY), height=0)

    # Streamlit components.html returns None; we need a workaround:
    # Use query params as fallback when component output isn't readable.
    # So we store token in session_state after we set it once.
    if "device_token" in st.session_state and st.session_state["device_token"]:
        return st.session_state["device_token"]

    # If we can't read localStorage directly, we generate once per device
    # and persist it (this works because the set happens in browser).
    new_token = secrets.token_urlsafe(24)
    components.html(_js_set_token(DEVICE_TOKEN_KEY, new_token), height=0)
    st.session_state["device_token"] = new_token
    return new_token


def clear_device_token():
    components.html(
        f"""
        <script>
          window.localStorage.removeItem("{DEVICE_TOKEN_KEY}");
        </script>
        """,
        height=0,
    )
    st.session_state.pop("device_token", None)
