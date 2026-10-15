import datetime
from backend.database.connection import execute_query
from backend.services.exceptions import ValidationError

def get_timetable(student_id):
    """Retrieves weekly timetable entries for student."""
    if not student_id:
        raise ValidationError("student_id is required.")

    query = """
        SELECT t.id, t.day_of_week, t.start_time, t.end_time, t.room, s.code, s.name 
        FROM timetable t 
        JOIN subjects s ON t.subject_id = s.id 
        WHERE t.student_id = ? 
        ORDER BY 
            CASE t.day_of_week 
                WHEN 'Monday' THEN 1 
                WHEN 'Tuesday' THEN 2 
                WHEN 'Wednesday' THEN 3 
                WHEN 'Thursday' THEN 4 
                WHEN 'Friday' THEN 5 
                WHEN 'Saturday' THEN 6 
                WHEN 'Sunday' THEN 7 
            END, t.start_time ASC;
    """
    rows = execute_query(query, (student_id,), fetch_all=True)
    return [dict(r) for r in rows]

def get_today_reminder(student_id):
    """Gathers classes, due assignments, and study plans for today."""
    if not student_id:
        raise ValidationError("student_id is required.")

    today = datetime.date.today()
    day_name = today.strftime("%A")
    date_str = today.strftime("%Y-%m-%d")

    # 1. Classes for today
    classes = execute_query(
        "SELECT t.start_time, t.end_time, t.room, s.code, s.name "
        "FROM timetable t JOIN subjects s ON t.subject_id = s.id "
        "WHERE t.student_id = ? AND t.day_of_week = ? "
        "ORDER BY t.start_time ASC;",
        (student_id, day_name),
        fetch_all=True
    )

    # 2. Assignments due today or tomorrow
    tomorrow_str = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    assignments = execute_query(
        "SELECT a.id, a.title, a.due_date, a.priority, s.code "
        "FROM assignments a JOIN subjects s ON a.subject_id = s.id "
        "WHERE a.student_id = ? AND a.status = 'Pending' AND (a.due_date = ? OR a.due_date = ?);",
        (student_id, date_str, tomorrow_str),
        fetch_all=True
    )

    # 3. Scheduled study plans for today
    study_sessions = execute_query(
        "SELECT sp.start_time, sp.end_time, sp.topic, s.code "
        "FROM study_plans sp JOIN subjects s ON sp.subject_id = s.id "
        "WHERE sp.student_id = ? AND sp.date = ? AND sp.status = 'Scheduled';",
        (student_id, date_str),
        fetch_all=True
    )

    return {
        "date": date_str,
        "day": day_name,
        "classes": [dict(c) for c in classes],
        "assignments_due": [dict(a) for a in assignments],
        "study_sessions": [dict(s) for s in study_sessions]
    }
