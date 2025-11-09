import streamlit as st
from auth import require_auth
from db import get_session, User, OTRoom, Complaint, Surgery, Patient
from security import hash_password
import pandas as pd

def render():
    require_auth(["Admin"])
    st.title("🛡️ Admin Supervision Dashboard")

    # ── Staff management
    left, right = st.columns(2)
    with left:
        st.subheader("Create / Manage Staff Accounts")
        with st.form("create_user"):
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            role = st.selectbox("Role", ["Scheduler", "Surgeon", "Nurse", "Inventory", "Admin"])
            username = st.text_input("Username")
            password = st.text_input("Temp Password", type="password")
            create = st.form_submit_button("Create / Update User")

        if create:
            if not (full_name and email and role and username and password):
                st.error("All fields are required.")
            else:
                # prevent name clash with existing user or patient (first + last)
                parts = full_name.strip().split()
                first = parts[0]
                last = parts[-1] if len(parts) > 1 else ""

                with get_session() as db:
                    name_taken_user = db.query(User).filter(User.full_name == full_name).first()
                    name_taken_patient = db.query(Patient).filter(
                        Patient.first_name == first, Patient.last_name == last
                    ).first()

                    if name_taken_user or name_taken_patient:
                        st.error("Name already used by someone in the system. Use a unique full name.")
                    else:
                        u = db.query(User).filter(User.username == username).first()
                        if u:
                            u.full_name, u.email, u.phone, u.role = full_name, email, phone, role
                            u.password_hash = hash_password(password).decode()
                            st.success("User updated.")
                        else:
                            db.add(User(
                                full_name=full_name, email=email, phone=phone, role=role,
                                username=username, password_hash=hash_password(password).decode()
                            ))
                            st.success("User created.")
                        db.commit()

    with right:
        st.subheader("Enable / Disable / Remove Users")
        with get_session() as db:
            users = db.query(User).filter(User.role != "Patient").all()
        if users:
            sel = st.selectbox("Select User", [f"{u.id} — {u.username} ({u.role})" for u in users])
            uid = int(sel.split(" — ")[0]) if sel else None
            c1, c2, c3 = st.columns(3)
            if c1.button("Disable", use_container_width=True):
                with get_session() as db:
                    u = db.get(User, uid); 
                    if u: u.is_active = False; db.commit()
                st.success("User disabled.")
            if c2.button("Enable", use_container_width=True):
                with get_session() as db:
                    u = db.get(User, uid); 
                    if u: u.is_active = True; db.commit()
                st.success("User enabled.")
            if c3.button("Remove", type="primary", use_container_width=True):
                with get_session() as db:
                    u = db.get(User, uid)
                    if u: db.delete(u); db.commit()
                st.warning("User removed.")
        else:
            st.info("No staff users yet.")

    st.divider()

    # ── OT Rooms
    st.subheader("Operation Theatres (Rooms)")
    with get_session() as db:
        rooms = db.query(OTRoom).all()
    col1, col2 = st.columns([2, 1])
    with col1:
        if rooms:
            st.table({
                "ID": [r.id for r in rooms],
                "Code": [r.room_code for r in rooms],
                "Name": [r.name for r in rooms],
                "Floor": [r.floor for r in rooms],
                "Active": [r.is_active for r in rooms],
            })
        else:
            st.info("No OT rooms yet.")
    with col2:
        with st.form("add_room"):
            code = st.text_input("Room Code", placeholder="OT-1")
            name = st.text_input("Display Name", placeholder="OT Alpha")
            floor = st.text_input("Floor", placeholder="2F")
            add = st.form_submit_button("Add / Update Room")
        if add:
            if not code:
                st.error("Room Code is required.")
            else:
                with get_session() as db:
                    r = db.query(OTRoom).filter(OTRoom.room_code == code).first()
                    if r:
                        r.name, r.floor = name, floor
                    else:
                        db.add(OTRoom(room_code=code, name=name, floor=floor))
                    db.commit()
                st.success("Saved room.")

    st.divider()

    # ── Operational KPIs
    st.subheader("Operational Overview")
    with get_session() as db:
        surgeries = db.query(Surgery).all()

    if surgeries:
        rows = []
        for s in surgeries:
            rows.append({
                "OT": s.ot_room.name if s.ot_room else None,
                "Date": s.date,
                "Status": s.status,
                "Procedure": s.procedure,
                "Surgeon": s.surgeon.full_name if s.surgeon else None
            })
        df = pd.DataFrame(rows)

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total Surgeries", len(df))
            st.bar_chart(df.groupby("OT").size())
        with c2:
            st.metric("Completed", int((df["Status"] == "Completed").sum()))
            st.bar_chart(df.groupby("Status").size())
    else:
        st.info("No surgeries to analyze yet.")

    st.divider()

    # ── Issues / Complaints
    st.subheader("Issue / Complaint Queue")
    with get_session() as db:
        issues = db.query(Complaint).order_by(Complaint.created_at.desc()).all()
    if not issues:
        st.success("No open issues.")
    else:
        for c in issues:
            with st.expander(f"#{c.id} [{c.status}] {c.category} · Priority {c.priority}"):
                st.write(c.message)
                if getattr(c, "admin_response", None):
                    st.info(f"Admin Response: {c.admin_response}")
                status_opts = ["Open", "In-Review", "Resolved"]
                new_status = st.selectbox(
                    "Status", status_opts, index=status_opts.index(c.status), key=f"st{c.id}"
                )
                resp = st.text_area("Reply", value=c.admin_response or "", key=f"rp{c.id}")
                if st.button("Save", key=f"sv{c.id}"):
                    with get_session() as db:
                        d = db.get(Complaint, c.id)
                        d.status = new_status
                        d.admin_response = resp
                        db.commit()
                    st.success("Saved")

    # ── Reports & Export
    st.subheader("Reports & Analytics")
    with get_session() as db:
        all_surg = db.query(Surgery).all()
    if not all_surg:
        st.info("No surgeries yet.")
    else:
        import pandas as pd
        data = [{
            "ID": x.id,
            "Date": x.date,
            "Start": x.start_time,
            "End": x.end_time,
            "Procedure": x.procedure,
            "OT": x.ot_room.name if x.ot_room else None,
            "Status": x.status,
            "Surgeon": x.surgeon.full_name if x.surgeon else None,
        } for x in all_surg]
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode()
        st.download_button("Download CSV", csv, file_name="ot_report.csv", mime="text/csv")
