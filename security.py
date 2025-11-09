import bcrypt
from datetime import datetime, timedelta
import streamlit as st

SESSION_TIMEOUT_MIN = 15


def hash_password(plain: str) -> bytes:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt())


def check_password(plain: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed)
    except Exception:
        return False


def touch_activity():
    st.session_state["last_activity"] = datetime.utcnow()


def enforce_inactivity_logout():
    now = datetime.utcnow()
    last = st.session_state.get("last_activity", now)
    if now - last > timedelta(minutes=SESSION_TIMEOUT_MIN):
        for k in ["auth_user", "role", "username", "last_activity"]:
            st.session_state.pop(k, None)
        st.warning("You were logged out due to inactivity (15 min). Please sign in again.")
        st.stop()