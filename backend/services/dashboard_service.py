from backend.database.connection import execute_query
from backend.services.exceptions import ValidationError

def get_dashboard_summary(student_id):
    """Calculates dashboard metrics and student academic standings."""
    if not student_id:
        raise ValidationError("student_id is required.")

    # 1. Total assignments count
    pending_assignments = execute_query(
        "SELECT COUNT(*) FROM assignments WHERE student_id = ? AND status = 'Pending';",
        (student_id,), fetch_one=True
    )[0]
    completed_assignments = execute_query(
        "SELECT COUNT(*) FROM assignments WHERE student_id = ? AND status = 'Completed';",
        (student_id,), fetch_one=True
    )[0]

    # 2. Overall attendance percentage
    records = execute_query(
        "SELECT status FROM attendance WHERE student_id = ?;",
        (student_id,), fetch_all=True
    )
    present = sum(1 for r in records if r['status'] == 'Present')
    absent = sum(1 for r in records if r['status'] == 'Absent')
    total_att = present + absent
    overall_attendance = round((present / total_att) * 100, 2) if total_att > 0 else 100.0

    # 3. Scheduled study hours
    study_sessions = execute_query(
        "SELECT date, start_time, end_time FROM study_plans WHERE student_id = ? AND status = 'Scheduled';",
        (student_id,), fetch_all=True
    )
    total_study_minutes = 0
    for session in study_sessions:
        try:
            sh, sm = map(int, session['start_time'].split(':'))
            eh, em = map(int, session['end_time'].split(':'))
            diff = (eh * 60 + em) - (sh * 60 + sm)
            if diff > 0:
                total_study_minutes += diff
        except Exception:
            pass
    study_hours = round(total_study_minutes / 60, 1)

    # 4. Profile overview
    student_profile = execute_query(
        "SELECT full_name, matric_number, cgpa FROM students WHERE id = ?;",
        (student_id,), fetch_one=True
    )

    return {
        "student_name": student_profile['full_name'] if student_profile else "Student",
        "matric_number": student_profile['matric_number'] if student_profile else "",
        "cgpa": student_profile['cgpa'] if student_profile else 0.0,
        "pending_assignments": pending_assignments,
        "completed_assignments": completed_assignments,
        "overall_attendance": overall_attendance,
        "scheduled_study_hours": study_hours
    }
