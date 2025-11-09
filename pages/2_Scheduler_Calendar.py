import streamlit as st
from auth import require_auth
from db import get_session, Patient, User, OTRoom, Surgery
from utils import has_conflict
from datetime import date, time
from sqlalchemy.orm import joinedload
import pandas as pd


def render():
    require_auth(["Scheduler"])
    st.title("📅 Scheduler — Book OT Slots")

    # Load base data
    with get_session() as db:
        patients = db.query(Patient).all()
        surgeons = db.query(User).filter(User.role == "Surgeon", User.is_active == True).all()
        nurses = db.query(User).filter(User.role == "Nurse", User.is_active == True).all()
        anesth = db.query(User).filter(User.role == "Scheduler", User.is_active == True).all()
        rooms = db.query(OTRoom).filter(OTRoom.is_active == True).all()

    left, right = st.columns([2, 1])

    # ---------------- LEFT SIDE — FORM ----------------
    with left:
        st.subheader("Create / Update / Cancel Surgery")

        with st.form("surg_form"):
            mode = st.selectbox("Mode", ["Create", "Update", "Cancel"])

            patient_sel = st.selectbox(
                "Patient", [f"{p.id}:{p.mrn} — {p.first_name} {p.last_name}" for p in patients]
            )

            room_sel = st.selectbox(
                "OT Room", [f"{r.id}:{r.room_code} — {r.name}" for r in rooms]
            )

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
            an_sel = st.selectbox("Anesthetist", an_opts)

            surg_id = None
            if mode == "Update":
                surg_id = st.number_input("Enter Surgery ID to Update", min_value=1, step=1)
            elif mode == "Cancel":
                surg_id = st.number_input("Enter Surgery ID to Cancel", min_value=1, step=1)

            notes = st.text_area("Notes")

            save = st.form_submit_button("Submit")

        # ---------------- FORM SUBMISSION HANDLING ----------------
        if save:
            pid = int(patient_sel.split(":")[0])
            rid = int(room_sel.split(":")[0])
            sid = int(surgeon_sel.split(":")[0])
            nid = int(nurse_sel.split(":")[0])
            aid = int(an_sel.split(":")[0]) if an_sel != "None" else None

            with get_session() as db:

                # CREATE
                if mode == "Create":
                    if has_conflict(
                        db,
                        ot_room_id=rid,
                        date=dt,
                        start_time=stime,
                        end_time=etime,
                        surgeon_id=sid,
                        anesthetist_id=aid,
                        nurse_id=nid,
                    ):
                        st.error("Conflict: room or staff already booked in that time.")
                    else:
                        new_s = Surgery(
                            patient_id=pid,
                            ot_room_id=rid,
                            date=dt,
                            start_time=stime,
                            end_time=etime,
                            procedure=proc,
                            surgeon_id=sid,
                            nurse_id=nid,
                            anesthetist_id=aid,
                            notes=notes,
                        )
                        db.add(new_s)
                        db.commit()
                        st.success("✅ Surgery created successfully!")

                # UPDATE
                elif mode == "Update":
                    s = db.get(Surgery, int(surg_id)) if surg_id else None
                    if not s:
                        st.error("Invalid surgery ID.")
                    else:
                        if has_conflict(
                            db,
                            ot_room_id=rid,
                            date=dt,
                            start_time=stime,
                            end_time=etime,
                            surgeon_id=sid,
                            anesthetist_id=aid,
                            nurse_id=nid,
                            exclude_id=s.id,
                        ):
                            st.error("Conflict detected.")
                        else:
                            s.patient_id = pid
                            s.ot_room_id = rid
                            s.date = dt
                            s.start_time = stime
                            s.end_time = etime
                            s.procedure = proc
                            s.surgeon_id = sid
                            s.nurse_id = nid
                            s.anesthetist_id = aid
                            s.notes = notes
                            db.commit()
                            st.success("✅ Surgery updated successfully!")

                # CANCEL
                elif mode == "Cancel":
                    s = db.get(Surgery, int(surg_id)) if surg_id else None
                    if not s:
                        st.error("Invalid surgery ID.")
                    else:
                        s.status = "Cancelled"
                        db.commit()
                        st.warning("⚠️ Surgery cancelled.")


    # ---------------- RIGHT SIDE — CALENDAR VIEW ----------------
    # ✅ FIX: define selected_date safely
    if "dt" in locals():
        selected_date = dt
    else:
        selected_date = date.today()

    # ✅ RIGHT SIDE — OT ROOM AVAILABILITY
    with right:
        st.subheader("📊 OT Room Availability")

        selected_date = dt   # ✅ USE selected date from the form

        import pandas as pd
        from sqlalchemy.orm import joinedload

        # Time slots
        time_slots = [
            ("09:00", "10:00"),
            ("10:00", "11:00"),
            ("11:00", "12:00"),
            ("12:00", "13:00"),
            ("14:00", "15:00"),
            ("15:00", "16:00"),
        ]
        slot_labels = [f"{s}-{e}" for s, e in time_slots]

        # Empty grid
        df = pd.DataFrame(index=[room.name for room in rooms], columns=slot_labels)
        df[:] = "—"

        # Load surgeries for selected date
        with get_session() as db:
            cases = (
                db.query(Surgery)
                .options(joinedload(Surgery.ot_room))
                .filter(Surgery.date == selected_date)
                .filter(Surgery.status != "Cancelled")
                .all()
            )

        # Populate grid
        for surg in cases:
            start = surg.start_time.strftime("%H:%M")
            end = surg.end_time.strftime("%H:%M")
            slot = f"{start}-{end}"

            if slot in df.columns:
                df.loc[surg.ot_room.name, slot] = surg.procedure

        st.dataframe(df, use_container_width=True)
