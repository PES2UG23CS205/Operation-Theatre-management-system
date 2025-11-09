import base64
import streamlit as st
from auth import require_auth
from db import get_session, User, Patient, Surgery
from utils import COMPLAINT_CATEGORIES
from db import Complaint  # import here to avoid circulars

def render():
    require_auth(["Patient"])  # strict isolation
    st.title("🧑‍⚕️ My Health Dashboard")

    # Find the patient by MRN == username
    with get_session() as db:
        me = db.get(User, st.session_state.get("auth_user"))
        patient = db.query(Patient).filter(Patient.mrn == me.username).first() if me else None

    if not patient:
        st.error("Patient record not linked. Please contact hospital desk.")
        return

    # Profile card
    col1, col2 = st.columns([1, 2])
    with col1:
        if patient.photo_base64:
            try:
                st.image(base64.b64decode(patient.photo_base64), caption=f"{patient.first_name} {patient.last_name}")
            except Exception:
                st.info("Photo corrupted / unreadable.")
        else:
            st.info("No photo uploaded.")
    with col2:
        st.markdown(f"**MRN:** {patient.mrn}")
        st.markdown(f"**Name:** {patient.first_name} {patient.last_name}")
        st.markdown(f"**DOB/Gender:** {patient.dob} / {patient.gender}")
        st.markdown(f"**Blood Group:** {patient.blood_group}")
        st.markdown(f"**Allergies:** {patient.allergies or 'None'}")
        st.markdown(f"**Comorbidities:** {patient.comorbidities or 'None'}")
        st.markdown(f"**Status:** {patient.status}")

    st.divider()

    # Upcoming & Past surgeries
    st.subheader("My Surgeries & Visits")
    with get_session() as db:
        my_cases = (
            db.query(Surgery)
            .filter(Surgery.patient_id == patient.id)
            .order_by(Surgery.date.desc(), Surgery.start_time.desc())
            .all()
        )

    if not my_cases:
        st.info("No surgeries found.")
    else:
        for s in my_cases:
            ot_name = s.ot_room.name if s.ot_room else "-"
            with st.expander(f"{s.date} — {s.procedure} ({s.status})"):
                st.markdown(f"**OT:** {ot_name}")
                st.markdown(f"**Time:** {s.start_time} — {s.end_time}")
                st.markdown(f"**Notes:** {s.notes or '-'}")
                if s.post_op_instructions:
                    st.success("**Post-Op Instructions**\n\n" + s.post_op_instructions)

    st.divider()

    # Raise an issue / complaint
    st.subheader("Raise an Issue / Complaint")
    with st.form("complaint"):
        cat = st.selectbox("Category", COMPLAINT_CATEGORIES)
        pri = st.selectbox("Priority", ["Low", "Medium", "High"], index=1)
        msg = st.text_area("Describe your issue")
        submit = st.form_submit_button("Submit Complaint")

    if submit:
        if not msg:
            st.error("Please describe your issue.")
        else:
            with get_session() as db:
                db.add(Complaint(
                    created_by_user_id=me.id,
                    patient_id=patient.id,
                    category=cat,
                    priority=pri,
                    message=msg
                ))
                db.commit()
            st.success("Complaint submitted. Admin will respond here.")

    # View my complaints
    st.subheader("My Complaints & Responses")
    with get_session() as db:
        mine = (
            db.query(Complaint)
            .filter(Complaint.created_by_user_id == me.id)
            .order_by(Complaint.created_at.desc())
            .all()
        )
    if not mine:
        st.info("No complaints yet.")
    else:
        for c in mine:
            with st.expander(f"#{c.id} [{c.status}] {c.category} · Priority {c.priority}"):
                st.write(c.message)
                if c.admin_response:
                    st.info(f"Admin Response: {c.admin_response}")
