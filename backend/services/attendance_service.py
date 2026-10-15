import math
from backend.database.connection import execute_query
from backend.services.exceptions import ValidationError

def get_raw_attendance(student_id):
    """Retrieves all raw attendance records for a student."""
    if not student_id:
        raise ValidationError("student_id is required.")
    query = """
        SELECT a.id, a.subject_id, a.date, a.status, s.code, s.name 
        FROM attendance a 
        JOIN subjects s ON a.subject_id = s.id 
        WHERE a.student_id = ? 
        ORDER BY a.date DESC;
    """
    rows = execute_query(query, (student_id,), fetch_all=True)
    return [dict(r) for r in rows]

def calculate_attendance(student_id):
    """Calculates attendance stats, percentage, and 75% target heuristic for all subjects."""
    if not student_id:
        raise ValidationError("student_id is required.")

    subjects = execute_query(
        "SELECT id, code, name, credits FROM subjects WHERE student_id = ?;",
        (student_id,),
        fetch_all=True
    )

    results = []
    for sub in subjects:
        sub_id = sub['id']
        records = execute_query(
            "SELECT status FROM attendance WHERE student_id = ? AND subject_id = ?;",
            (student_id, sub_id),
            fetch_all=True
        )

        present = sum(1 for r in records if r['status'] == 'Present')
        absent = sum(1 for r in records if r['status'] == 'Absent')
        excused = sum(1 for r in records if r['status'] == 'Excused')
        total = present + absent

        pct = 100.0
        if total > 0:
            pct = round((present / total) * 100, 2)

        classes_needed = 0
        classes_can_miss = 0

        if pct < 75.0:
            classes_needed = max(0, 3 * absent - present)
        else:
            classes_can_miss = max(0, math.floor((present - 3 * absent) / 3))

        results.append({
            "subject_id": sub_id,
            "code": sub['code'],
            "name": sub['name'],
            "credits": sub['credits'],
            "present": present,
            "absent": absent,
            "excused": excused,
            "total_classes": total,
            "percentage": pct,
            "status": "Good" if pct >= 75.0 else "Low",
            "classes_needed_for_75": classes_needed,
            "classes_can_miss": classes_can_miss
        })

    return results
