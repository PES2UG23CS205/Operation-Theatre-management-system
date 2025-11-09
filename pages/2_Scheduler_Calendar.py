import streamlit as st
from auth import require_auth
from db import get_session, Patient, User, OTRoom, Surgery
from utils import has_conflict
from datetime import date, time

def render():
    require_auth(["Scheduler"])  # strict isolation
    st.title("📅 Scheduler — Book OT Slots")

    with get_session() as db:
        patients = db.query(Patient).all()
        surgeons = db.query(User).filter(User.role == "Surgeon", User.is_active == True).all()
        nurses = db.query(User).filter(User.role == "Nurse", User.is_active == True).all()
        anesth = db.query(User).filter(User.role == "Scheduler", User.is_active == True).all()  # placeholder
        rooms = db.query(OTRoom).filter(OTRoom.is_active == True).all()

    left, right = st.columns([2, 1])
    with left:
        st.subheader("Create / Update / Cancel Surgery")
        with st.form("surg_form"):
            mode = st.selectbox("Mode", ["Create", "Update", "Cancel"])
            patient_sel = st.selectbox("Patient", [f"{p.id}:{p.mrn} — {p.first_name} {p.last_name}" for p in patients])
            room_sel = st.selectbox("OT Room", [f"{r.id}:{r.room_code} — {r.name}" for r in rooms])
            dt = st.date_input("Date", value=date.today())
            c1, c2 = st.columns(2)
            with c1:
                stime = st.time_input("Start Time", value=time(9, 0))
            with c2:
                etime = st.time_input("End Time", value=time(10, 0))
            proc = st.text_input("Procedure", placeholder="Laparoscopic Appendectomy")
            surgeon_sel = st.selectbox("Surgeon", [f"{u.id}:{u.full_name}" for u in surgeons])
            nurse_sel = st.selectbox("Nurse", [f"{u.id}:{u.full_name}" for u in nurses])
            an_opts = ["None"] + [f"{u.id}:{u.full_name}" for u in anesth]
            an_sel = st.selectbox("Anesthetist (placeholder)", an_opts)

            # For update / cancel, ask for Surgery ID inside the form
            surg_id = None
            if mode in ("Update", "Cancel"):
                surg_id = st.number_input("Surgery ID", min_value=1)

            notes = st.text_area("Notes")
            save = st.form_submit_button("Submit", use_container_width=True)

        if save:
            pid = int(patient_sel.split(":")[0])
            rid = int(room_sel.split(":")[0])
            sid = int(surgeon_sel.split(":")[0])
            nid = int(nurse_sel.split(":")[0])
            aid = int(an_sel.split(":")[0]) if an_sel != "None" else None

            with get_session() as db:
                if mode == "Create":
                    if has_conflict(
                        db, ot_room_id=rid, date=dt, start_time=stime, end_time=etime,
                        surgeon_id=sid, anesthetist_id=aid, nurse_id=nid
                    ):
                        st.error("Conflict: room or staff already booked in that time.")
                    else:
                        s = Surgery(
                            patient_id=pid, ot_room_id=rid, date=dt, start_time=stime, end_time=etime,
                            procedure=proc, surgeon_id=sid, nurse_id=nid, anesthetist_id=aid, notes=notes
                        )
                        db.add(s); db.commit()
                        st.success("Surgery scheduled.")

                elif mode == "Update":
                    s = db.get(Surgery, int(surg_id)) if surg_id else None
                    if not s:
                        st.error("Invalid surgery id.")
                    else:
                        if has_conflict(
                            db, ot_room_id=rid, date=dt, start_time=stime, end_time=etime,
                            surgeon_id=sid, anesthetist_id=aid, nurse_id=nid, exclude_id=s.id
                        ):
                            st.error("Conflict detected.")
                        else:
                            s.patient_id, s.ot_room_id = pid, rid
                            s.date, s.start_time, s.end_time = dt, stime, etime
                            s.procedure, s.surgeon_id = proc, sid
                            s.nurse_id, s.anesthetist_id, s.notes = nid, aid, notes
                            db.commit()
                            st.success("Surgery updated.")

                else:  # Cancel
                    s = db.get(Surgery, int(surg_id)) if surg_id else None
                    if s:
                        s.status = "Cancelled"; db.commit()
                        st.warning("Surgery cancelled.")
                    else:
                        st.error("Invalid surgery id.")

    with right:
        st.subheader("Today & Upcoming")
        with get_session() as db:
            upcoming = db.query(Surgery)\
                         .order_by(Surgery.date, Surgery.start_time).all()
        for s in upcoming[:15]:
            st.write(f"**#{s.id}** {s.date} {s.start_time}-{s.end_time} · {s.procedure} · {s.ot_room.name if s.ot_room else ''}")
