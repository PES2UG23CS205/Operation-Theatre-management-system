import streamlit as st
from db import get_session, User, AuditLog
from security import check_password, touch_activity, enforce_inactivity_logout

ROLES = ["Admin", "Scheduler", "Surgeon", "Nurse", "Inventory", "Patient"]


def log_action(user_id, action, details=""):
    with get_session() as db:
        db.add(AuditLog(user_id=user_id, action=action, details=details))
        db.commit()


def login_ui():
    enforce_inactivity_logout()
    st.title("🏥 OT Scheduler — Secure Sign In")
    st.caption("Role-based access · Audit logging · 2 clicks to your dashboard")
    username = st.text_input("Username", placeholder="e.g., MRN1001 or admin", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Sign In", use_container_width=True, key="login_btn"):
        with get_session() as db:
            user = db.query(User).filter(User.username == username, User.is_active == True).first()
            if user and check_password(password, user.password_hash.encode() if isinstance(user.password_hash, str) else user.password_hash):
                st.session_state["auth_user"] = user.id
                st.session_state["role"] = user.role
                st.session_state["username"] = user.username
                touch_activity()
                log_action(user.id, "login", f"{user.username} logged in")
                st.success("Welcome! Redirecting to your dashboard…")
                st.rerun()
            else:
                st.error("Invalid credentials or inactive account.")


def logout_button(key="logout_btn"):
    if st.button("Logout", type="secondary", key=key):
        uid = st.session_state.get("auth_user")
        if uid:
            log_action(uid, "logout", "User logged out")
        for k in ["auth_user", "role", "username", "last_activity"]:
            st.session_state.pop(k, None)
        st.rerun()


def require_auth(roles=None):
    enforce_inactivity_logout()
    if "auth_user" not in st.session_state:
        st.stop()
    if roles and st.session_state.get("role") not in roles:
        st.error("You do not have permission to view this page.")
        st.stop()