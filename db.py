from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, Date, Time, DateTime,
    ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DB_PATH, exist_ok=True)
DB_URL = f"sqlite:///{os.path.join(DB_PATH, 'ot_scheduler.db')}"

engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ---------- Models ----------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(100), nullable=False, unique=True)  # enforce unique staff name
    email = Column(String(120), unique=True, nullable=False)
    phone = Column(String(20))
    role = Column(String(30), nullable=False)  # Admin, Scheduler, Surgeon, Nurse, Inventory, Patient
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    mrn = Column(String(20), unique=True, nullable=False)
    first_name = Column(String(60), nullable=False)
    last_name = Column(String(60), nullable=False)
    dob = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    phone = Column(String(20), unique=True)
    email = Column(String(120), unique=True)
    address = Column(Text)
    city = Column(String(60))
    state = Column(String(60))
    pin = Column(String(10))
    emergency_contact_name = Column(String(100))
    emergency_contact_phone = Column(String(20))
    blood_group = Column(String(5))
    allergies = Column(Text)
    comorbidities = Column(Text)
    guardian_consent_required = Column(Boolean, default=False)
    consent_form_path = Column(String(255))
    status = Column(String(30), default="Pre-Operation")
    photo_base64 = Column(Text)


class OTRoom(Base):
    __tablename__ = "ot_rooms"
    id = Column(Integer, primary_key=True)
    room_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(80), nullable=False)
    floor = Column(String(10))
    is_active = Column(Boolean, default=True)


class Surgery(Base):
    __tablename__ = "surgeries"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ot_room_id = Column(Integer, ForeignKey("ot_rooms.id"), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    procedure = Column(String(200), nullable=False)
    status = Column(String(30), default="Scheduled")
    surgeon_id = Column(Integer, ForeignKey("users.id"))
    anesthetist_id = Column(Integer, ForeignKey("users.id"))
    nurse_id = Column(Integer, ForeignKey("users.id"))
    notes = Column(Text)
    post_op_instructions = Column(Text)  # NEW: AI-generated text

    patient = relationship("Patient")
    ot_room = relationship("OTRoom")
    surgeon = relationship("User", foreign_keys=[surgeon_id])
    anesthetist = relationship("User", foreign_keys=[anesthetist_id])
    nurse = relationship("User", foreign_keys=[nurse_id])


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    sku = Column(String(40), unique=True, nullable=False)
    category = Column(String(60), nullable=False)
    stock_qty = Column(Integer, default=0)
    threshold = Column(Integer, default=5)
    unit = Column(String(20), default="pcs")


class SurgeryInventoryUsage(Base):
    __tablename__ = "surgery_inventory_usage"
    id = Column(Integer, primary_key=True)
    surgery_id = Column(Integer, ForeignKey("surgeries.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    qty_used = Column(Integer, default=0)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(80), nullable=False)
    details = Column(Text)
    ip = Column(String(50))


class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))  # patient or staff user id
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)  # optional link
    category = Column(String(50), nullable=False)  # Surgeon Related / Nursing Related / Treatment Quality / Delay / Inventory
    priority = Column(String(20), default="Medium")  # Low/Medium/High
    message = Column(Text, nullable=False)
    status = Column(String(20), default="Open")  # Open/In-Review/Resolved
    admin_response = Column(Text)
    responded_at = Column(DateTime)


from sqlalchemy import inspect

def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()

