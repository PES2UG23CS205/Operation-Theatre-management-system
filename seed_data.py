from db import init_db, get_session, User, Patient, OTRoom, InventoryItem, Surgery
from security import hash_password
from datetime import date, time

init_db()

with get_session() as db:
    # Admin (unique full_name enforced on User)
    if not db.query(User).filter(User.username=="admin").first():
        db.add(User(full_name="System Admin", email="admin@hospital.local", phone="9999900000",
                    role="Admin", username="admin", password_hash=hash_password("Admin@123").decode()))

    # Staff
    staff = [
        ("Scheduler","Anita Sharma","anita.sharma@hosp.in","9876500001","anita"),
        ("Surgeon","Dr. Karan Mehta","karan.mehta@hosp.in","9876500002","karan"),
        ("Surgeon","Dr. Rithika Iyer","rithika.iyer@hosp.in","9876500003","rithika"),
        ("Surgeon","Dr. Adyanth S","adyanth.s@hosp.in","9876500004","adyanth"),
        ("Nurse","Cheshta Rao","cheshta.rao@hosp.in","9876500005","cheshta"),
        ("Nurse","Jaya N","jaya.n@hosp.in","9876500006","jaya"),
        ("Inventory","Moulya K","moulya.k@hosp.in","9876500007","moulya"),
        ("Scheduler","Shubha Ashok","shubha.ashok@hosp.in","9876500008","shubha"),
        ("Inventory","Karthik R S","karthik.rs@hosp.in","9876500009","karthik"),
        ("Nurse","Hiren M P","hiren.mp@hosp.in","9876500010","hiren"),
        ("Surgeon","Dr. Prashant Radder","prashant.r@hosp.in","9876500011","prashant"),
        ("Surgeon","Dr. Chitra M","chitra.m@hosp.in","9876500012","chitra"),
        ("Scheduler","Ankita Shetty","ankita.shetty@hosp.in","9876500013","ankita"),
        ("Inventory","Rohan Verma","rohan.verma@hosp.in","9876500014","rohan"),
        ("Nurse","Sneha Kulkarni","sneha.k@hosp.in","9876500015","sneha"),
        ("Surgeon","Dr. Nandhi Kesavan","nandhi.k@hosp.in","9876500016","nandhi"),
        ("Scheduler","Arjun Rao","arjun.rao@hosp.in","9876500017","arjun"),
        ("Nurse","Priya Singh","priya.s@hosp.in","9876500018","priya"),
        ("Inventory","Varun Gupta","varun.g@hosp.in","9876500019","varun"),
        ("Surgeon","Dr. Hema Krishnan","hema.k@hosp.in","9876500020","hema"),
    ]
    for role, name, email, phone, uname in staff:
        if not db.query(User).filter(User.username==uname).first():
            db.add(User(full_name=name, email=email, phone=phone, role=role, username=uname,
                        password_hash=hash_password(uname.capitalize()+"@123").decode()))

    # Keep existing rooms/items/patients from Part 1 (only create if missing)
    rooms = [("OT-1","OT Alpha","2F"),("OT-2","OT Beta","2F"),("OT-3","OT Gamma","3F"),("OT-4","OT Delta","3F")]
    for code, name, floor in rooms:
        from db import OTRoom
        if not db.query(OTRoom).filter(OTRoom.room_code==code).first():
            db.add(OTRoom(room_code=code, name=name, floor=floor))

    if not db.query(Surgery).first():
        db.add(Surgery(patient_id=1, ot_room_id=1, date=date.today(), start_time=time(9,0), end_time=time(10,0),
                       procedure="Appendectomy", surgeon_id=2, nurse_id=5, notes="NPO after midnight"))

    db.commit()

print("Seed complete. Admin login -> username: admin, password: Admin@123")