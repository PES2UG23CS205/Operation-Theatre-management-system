from datetime import time
from db import Surgery

COMPLAINT_CATEGORIES = [
    "Surgeon Related",
    "Nursing Related",
    "Treatment Quality",
    "Delay / Scheduling",
    "Inventory / Equipment",
]

def times_overlap(s1_start: time, s1_end: time, s2_start: time, s2_end: time) -> bool:
    return (s1_start < s2_end) and (s2_start < s1_end)

def has_conflict(session, *, ot_room_id, date, start_time, end_time,
                 surgeon_id=None, anesthetist_id=None, nurse_id=None, exclude_id=None):
    q = session.query(Surgery).filter(Surgery.date == date)
    if exclude_id:
        q = q.filter(Surgery.id != exclude_id)
    for s in q.all():
        same_room = s.ot_room_id == ot_room_id
        staff_overlap = any([
            (surgeon_id and s.surgeon_id == surgeon_id),
            (anesthetist_id and s.anesthetist_id == anesthetist_id),
            (nurse_id and s.nurse_id == nurse_id),
        ])
        if (same_room or staff_overlap) and times_overlap(start_time, end_time, s.start_time, s.end_time):
            return True
    return False

# Simple rule-based generator for post-op suggestions
PROCEDURE_HINTS = {
    "Append": "Walk short distances, avoid heavy lifting for 2 weeks, keep incision clean and dry.",
    "Chole": "Low-fat diet for 1-2 weeks, monitor for shoulder-tip pain, deep breathing exercises.",
    "Hernia": "Use abdominal binder if advised, no straining, cough support technique.",
}

def generate_post_op_instructions(procedure: str) -> str:
    text = "General: Hydrate well, take pain meds as prescribed, watch for fever >38°C, redness, discharge, or severe pain."
    for key, hint in PROCEDURE_HINTS.items():
        if key.lower() in procedure.lower():
            return f"{text}\nSpecific: {hint}"
    return text
