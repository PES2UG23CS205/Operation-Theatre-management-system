import streamlit as st
from db import init_db, get_session, Patient, User
from auth import login_ui, logout_button
from security import touch_activity, hash_password
from datetime import date
import base64, os, secrets, string

def role_sidebar():
    if "auth_user" not in st.session_state:
        with st.sidebar:
            st.info("Please sign in to continue.")
        return

    role = st.session_state.get("role")
    username = st.session_state.get("username")

    with st.sidebar:
        st.markdown("### 🏥 OT Scheduler")
        st.caption(f"Logged in as **{username}** ({role})")

        # Show small, role-specific hints (no navigation to other roles!)
        if role == "Admin":
            st.markdown("- **Admin Tools:** Users, OT Rooms, KPIs, Complaints, Reports")
        elif role == "Scheduler":
            st.markdown("- **Scheduler:** Create/Update/Cancel bookings")
        elif role == "Surgeon":
            st.markdown("- **Surgeon:** My cases & status")
        elif role == "Nurse":
            st.markdown("- **Nurse:** Today’s patient statuses")
        elif role == "Inventory":
            st.markdown("- **Inventory:** Stock & usage")
        elif role == "Patient":
            st.markdown("- **Patient:** Profile, surgeries, issues")

        # Put logout in sidebar (and keep the header one if you like)
        logout_button(key="logout_side")

st.set_page_config(
    page_title="OT Scheduler",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed"  # This will collapse the sidebar by default
)
init_db()
role_sidebar()

# --- Hide Streamlit's default multipage navigator (but keep sidebar itself) ---
st.markdown("""
<style>
/* Hide the auto 'Pages' list in the sidebar */
[data-testid="stSidebarNav"] { display: none !important; }
/* Hide the burger (≡) that opens the pages list on narrow screens */
header [data-testid="baseButton-headerNoPadding"] { display:none !important; }
/* (Optional) hide the 'Manage app' menu */
#MainMenu {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Header bar
with st.container():
    cols = st.columns([6,2])
    with cols[0]:
        st.markdown("<h3 style='margin:0'>🩺 Operation Theatre Scheduler</h3>", unsafe_allow_html=True)
        st.caption("Smart scheduling · Patient-first workflows · Secure by design")
    with cols[1]:
        if "auth_user" in st.session_state:
            logout_button(key="logout_header")

# Helper to ensure unique names across domains

def name_exists_anywhere(first: str, last: str) -> bool:
    full = f"{first} {last}".strip()
    with get_session() as db:
        u = db.query(User).filter(User.full_name == full).first()
        p = db.query(Patient).filter(Patient.first_name == first, Patient.last_name == last).first()
        return bool(u or p)


def random_pwd(n=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(n))

# Main
if "auth_user" not in st.session_state:
    tab1, tab2 = st.tabs(["Sign In", "Patient Register"])  # patients can self-register
    with tab1:
        login_ui()
    with tab2:
        st.subheader("Patient Registration")
        with st.form("patient_reg"):
            c1, c2, c3 = st.columns(3)
            with c1:
                first = st.text_input("First Name", placeholder="Moulya", key="reg_first")
                last = st.text_input("Last Name", placeholder="Rao", key="reg_last")
                dob = st.date_input("Date of Birth", value=date(2001,1,1), key="reg_dob")
                gender = st.selectbox("Gender", ["Female","Male","Other"], key="reg_gender") 
                blood = st.selectbox("Blood Group", ["A+","A-","B+","B-","AB+","AB-","O+","O-"], key="reg_blood")
            with c2:
                phone = st.text_input("Phone", placeholder="9876543210", key="reg_phone")
                email = st.text_input("Email", placeholder="patient@example.com", key="reg_email")
                city = st.text_input("City", placeholder="Bengaluru", key="reg_city")
                state = st.text_input("State", placeholder="Karnataka", key="reg_state")
                pin = st.text_input("PIN Code", placeholder="560100", key="reg_pin")
            with c3:
                address = st.text_area("Address", height=120, key="reg_address")
                emerg_name = st.text_input("Emergency Contact Name", key="reg_emerg_name")
                emerg_phone = st.text_input("Emergency Contact Phone", key="reg_emerg_phone")
                allergies = st.text_area("Allergies", height=80, key="reg_allergies")
                comorb = st.text_area("Comorbidities", height=80, key="reg_comorb")
                photo_file = st.file_uploader("Upload Photo (jpg/png)", type=["jpg","jpeg","png"], key="reg_photo")
                submit = st.form_submit_button("Submit Registration",use_container_width=True)
    

        if submit:
            if not (first and last and phone and email):
                st.error("First name, Last name, Phone and Email are required.")
            elif name_exists_anywhere(first, last):
                st.error("A person with this name already exists in the system. Please add a middle name or variation.")
            else:
                from sqlalchemy import func
                with get_session() as db:
                    max_id = db.query(func.max(Patient.id)).scalar() or 0
                    mrn = f"MRN{1000+max_id+1}"
                    photo_b64 = None
                    if photo_file:
                        photo_b64 = base64.b64encode(photo_file.read()).decode()
                    p = Patient(
                        mrn=mrn, first_name=first, last_name=last, dob=dob, gender=gender,
                        phone=phone, email=email, address=address, city=city, state=state,
                        pin=pin, emergency_contact_name=emerg_name, emergency_contact_phone=emerg_phone,
                        blood_group=blood, allergies=allergies, comorbidities=comorb,
                        photo_base64=photo_b64,
                    )
                    db.add(p)
                    # Create patient login: username=MRN, password=random
                    pwd = random_pwd()
                    db.add(User(full_name=f"{first} {last}", email=email, phone=phone, role="Patient",
                                username=mrn, password_hash=hash_password(pwd).decode()))
                    db.commit()
                    st.success(f"Registration received. Your MRN is {mrn}.")
                    st.info(f"Use these credentials to login: Username: {mrn}  Password: {pwd}")

# =========================
# POST-LOGIN ROUTING (Option A: role-isolated, no sidebar)
# =========================
import os, importlib.util

def _load_module(rel_path: str, name: str):
    base_dir = os.path.dirname(__file__)
    full_path = os.path.join(base_dir, rel_path)
    spec = importlib.util.spec_from_file_location(name, full_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

if "auth_user" in st.session_state:
    role = st.session_state.get("role")
    touch_activity()
    st.success(f"Welcome! You are logged in as {st.session_state.get('username')} ({role})")

    # Call only the page for that role (strict isolation)
    if role == "Admin":
        adminpg = _load_module("pages/1_Admin_Dashboard.py", "admin_dashboard")
        adminpg.render()

    elif role == "Scheduler":
        schedpg = _load_module("pages/2_Scheduler_Calendar.py", "scheduler_calendar")
        schedpg.render()

    elif role == "Surgeon":
        surgpg = _load_module("pages/3_Surgeon_Worklist.py", "surgeon_worklist")
        surgpg.render()

    elif role == "Nurse":
        nursepg = _load_module("pages/4_Nurse_Station.py", "nurse_station")
        nursepg.render()

    elif role == "Inventory":
        invpg = _load_module("pages/5_Inventory_Manager.py", "inventory_manager")
        invpg.render()

    elif role == "Patient":
        ptpg = _load_module("pages/7_Patient_Dashboard.py", "patient_dashboard")
        ptpg.render()
