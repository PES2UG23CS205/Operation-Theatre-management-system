import streamlit as st
from datetime import date
from auth import require_auth
from db import get_session, Patient, Surgery

def render():
    require_auth(["Nurse"])  # strict isolation
    st.title("👩‍⚕️ Nurse Station — Patient Status (Today's Surgeries)")

    today = date.today()

    # find unique patient_ids that have a surgery today
    with get_session() as db:
        today_cases = db.query(Surgery).filter(Surgery.date == today).all()
        pt_ids_today = sorted({s.patient_id for s in today_cases})
        if pt_ids_today:
            patients = db.query(Patient).filter(Patient.id.in_(pt_ids_today)).all()
        else:
            patients = []

    if not patients:
        st.info("No patients scheduled for surgery today.")
        return

    for p in patients:
        with st.expander(f"{p.mrn} — {p.first_name} {p.last_name}"):
            current_idx = ["Pre-Operation", "In-Surgery", "Recovery", "Discharged"].index(p.status) if p.status in ["Pre-Operation","In-Surgery","Recovery","Discharged"] else 0
            new = st.selectbox(
                "Status",
                ["Pre-Operation","In-Surgery","Recovery","Discharged"],
                index=current_idx,
                key=f"ps{p.id}",
            )
            if st.button("Save", key=f"pv{p.id}"):
                with get_session() as db:
                    d = db.get(Patient, p.id)
                    d.status = new
                    db.commit()
                st.success("Saved")
