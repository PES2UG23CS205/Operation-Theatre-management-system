import streamlit as st
from auth import require_auth
from db import get_session, Surgery
from utils import generate_post_op_instructions

def render():
    require_auth(["Surgeon"])  # strict isolation

    st.title("🧑‍⚕️ Surgeon — My Cases")

    # If login set user_id in session, we filter by it. Otherwise show nothing/all as fallback.
    surgeon_id = st.session_state.get("user_id")

    with get_session() as db:
        q = db.query(Surgery).order_by(Surgery.date, Surgery.start_time)
        if surgeon_id:
            q = q.filter(Surgery.surgeon_id == surgeon_id)
        cases = q.all()

    if not cases:
        st.info("No assigned cases yet.")
        return

    for s in cases:
        header = f"#{s.id} {s.date} {s.procedure}"
        if s.ot_room:
            header += f" @ {s.ot_room.name}"
        with st.expander(header):
            st.write(f"Patient: {s.patient.first_name} {s.patient.last_name} (MRN {s.patient.mrn})")
            st.write(f"Status: {s.status}")
            new = st.selectbox(
                "Update Status",
                ["Scheduled", "In-Progress", "Completed", "Cancelled"],
                index=["Scheduled", "In-Progress", "Completed", "Cancelled"].index(s.status),
                key=f"st{s.id}"
            )
            if st.button("Save", key=f"sv{s.id}"):
                with get_session() as db:
                    d = db.get(Surgery, s.id)
                    d.status = new
                    # Auto-generate post-op instructions when completed
                    if new == "Completed" and not getattr(d, "post_op_instructions", None):
                        d.post_op_instructions = generate_post_op_instructions(d.procedure)
                    db.commit()
                st.success("Saved")
