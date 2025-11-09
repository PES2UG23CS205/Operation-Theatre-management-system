# utils.py
from db import Surgery

def has_conflict(
    db,
    ot_room_id,
    date,
    start_time,
    end_time,
    surgeon_id=None,
    anesthetist_id=None,
    nurse_id=None,
    exclude_id=None
):
    """
    Checks for slot conflicts BEFORE creating/updating a surgery.
    Returns True if conflict exists.
    """

    q = db.query(Surgery).filter(Surgery.date == date)

    if exclude_id:
        q = q.filter(Surgery.id != exclude_id)

    cases = q.all()

    for c in cases:
        # OT room conflict
        if c.ot_room_id == ot_room_id:
            if not (end_time <= c.start_time or start_time >= c.end_time):
                return True

        # Surgeon conflict
        if surgeon_id and c.surgeon_id == surgeon_id:
            if not (end_time <= c.start_time or start_time >= c.end_time):
                return True

        # Anesthetist conflict
        if anesthetist_id and c.anesthetist_id == anesthetist_id:
            if not (end_time <= c.start_time or start_time >= c.end_time):
                return True

        # Nurse conflict
        if nurse_id and c.nurse_id == nurse_id:
            if not (end_time <= c.start_time or start_time >= c.end_time):
                return True

    return False
