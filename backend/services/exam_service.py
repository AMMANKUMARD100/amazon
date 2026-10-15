import re
import datetime
from backend.database.connection import execute_query
from backend.services.exceptions import ValidationError, NotFoundError, PersistenceError

def validate_date(date_str):
    """Validates YYYY-MM-DD date and returns parsed datetime.date object."""
    if not date_str or not isinstance(date_str, str):
        raise ValidationError("Exam date is required and must be in YYYY-MM-DD format.")
    date_str = date_str.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValidationError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD.")
    try:
        y, m, d = map(int, date_str.split("-"))
        return datetime.date(y, m, d)
    except ValueError:
        raise ValidationError(f"Date '{date_str}' is not a valid calendar date.")

def list_exams(student_id):
    """Lists all scheduled exams for a student."""
    if not student_id:
        raise ValidationError("student_id is required.")
    query = """
        SELECT e.id, e.student_id, e.subject_id, e.title, e.exam_date, e.notes, e.created_at,
               COALESCE(s.code, 'GEN') as code, COALESCE(s.name, 'General') as subject_name
        FROM exams e
        LEFT JOIN subjects s ON e.subject_id = s.id
        WHERE e.student_id = ?
        ORDER BY e.exam_date ASC, e.id ASC;
    """
    rows = execute_query(query, (student_id,), fetch_all=True)
    return [dict(r) for r in rows]

def get_exam(student_id, exam_id):
    """Gets an exam by ID for a specific student."""
    if not student_id or not exam_id:
        raise ValidationError("student_id and exam_id are required.")
    row = execute_query(
        """SELECT e.id, e.student_id, e.subject_id, e.title, e.exam_date, e.notes, e.created_at,
                  COALESCE(s.code, 'GEN') as code, COALESCE(s.name, 'General') as subject_name
           FROM exams e
           LEFT JOIN subjects s ON e.subject_id = s.id
           WHERE e.id = ? AND e.student_id = ?;""",
        (exam_id, student_id),
        fetch_one=True
    )
    if not row:
        raise NotFoundError(f"Exam #{exam_id} not found.")
    return dict(row)

def add_exam(student_id, title, exam_date, subject_id=None, subject_code=None, notes=""):
    """Adds a new exam for the student."""
    if not student_id:
        raise ValidationError("student_id is required.")
    if not title or not isinstance(title, str) or not title.strip():
        raise ValidationError("Exam title is required.")

    parsed_date = validate_date(exam_date)
    date_str = parsed_date.strftime("%Y-%m-%d")

    # Resolve subject_id if subject_code provided
    if not subject_id and subject_code:
        sub = execute_query(
            "SELECT id FROM subjects WHERE student_id = ? AND (code = ? OR name = ?);",
            (student_id, subject_code.strip(), subject_code.strip()),
            fetch_one=True
        )
        if sub:
            subject_id = sub['id']

    new_id = execute_query(
        """INSERT INTO exams (student_id, subject_id, title, exam_date, notes)
           VALUES (?, ?, ?, ?, ?);""",
        (student_id, subject_id, title.strip(), date_str, (notes or "").strip()),
        commit=True
    )

    saved = execute_query("SELECT id FROM exams WHERE id = ? AND student_id = ?;", (new_id, student_id), fetch_one=True)
    if not saved:
        raise PersistenceError("Exam record could not be persisted in database.")

    return get_exam(student_id, new_id)

def update_exam(student_id, exam_id, updates_dict):
    """Updates an existing exam."""
    get_exam(student_id, exam_id)
    fields = []
    params = []

    if "title" in updates_dict:
        t = (updates_dict["title"] or "").strip()
        if not t:
            raise ValidationError("Exam title cannot be empty.")
        fields.append("title = ?")
        params.append(t)

    if "exam_date" in updates_dict:
        parsed = validate_date(updates_dict["exam_date"])
        fields.append("exam_date = ?")
        params.append(parsed.strftime("%Y-%m-%d"))

    if "notes" in updates_dict:
        fields.append("notes = ?")
        params.append((updates_dict["notes"] or "").strip())

    if "subject_id" in updates_dict:
        fields.append("subject_id = ?")
        params.append(updates_dict["subject_id"])

    if not fields:
        return get_exam(student_id, exam_id)

    params.extend([exam_id, student_id])
    sql = f"UPDATE exams SET {', '.join(fields)} WHERE id = ? AND student_id = ?;"
    execute_query(sql, tuple(params), commit=True)
    return get_exam(student_id, exam_id)

def delete_exam(student_id, exam_id):
    """Deletes an exam."""
    existing = get_exam(student_id, exam_id)
    execute_query("DELETE FROM exams WHERE id = ? AND student_id = ?;", (exam_id, student_id), commit=True)
    check = execute_query("SELECT id FROM exams WHERE id = ?;", (exam_id,), fetch_one=True)
    if check:
        raise PersistenceError("Failed to delete exam from database.")
    return {"message": f"Exam '{existing['title']}' deleted successfully.", "exam_id": exam_id}

# -------------------------------------------------------------
# Study Preferences Services
# -------------------------------------------------------------
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def get_study_preferences(student_id):
    """Gets weekly study preferences (available hours per weekday) for student."""
    if not student_id:
        raise ValidationError("student_id is required.")
    rows = execute_query(
        "SELECT weekday, available_hours FROM study_preferences WHERE student_id = ?;",
        (student_id,),
        fetch_all=True
    )
    prefs = {r['weekday']: r['available_hours'] for r in rows}
    return prefs

def set_study_preference(student_id, weekday, available_hours):
    """Sets available study hours for a specific weekday."""
    if not student_id:
        raise ValidationError("student_id is required.")
    day = (weekday or "").capitalize().strip()
    if day not in WEEKDAYS:
        raise ValidationError(f"Invalid weekday '{weekday}'. Must be one of {', '.join(WEEKDAYS)}.")
    try:
        hours = float(available_hours)
    except (ValueError, TypeError):
        raise ValidationError("available_hours must be a valid number.")

    if hours < 0.0 or hours > 12.0:
        raise ValidationError("available_hours must be between 0.0 and 12.0.")

    execute_query(
        """INSERT INTO study_preferences (student_id, weekday, available_hours)
           VALUES (?, ?, ?)
           ON CONFLICT(student_id, weekday) DO UPDATE SET available_hours = excluded.available_hours;""",
        (student_id, day, hours),
        commit=True
    )
    return {"weekday": day, "available_hours": hours}

def set_bulk_study_preferences(student_id, prefs_dict):
    """Sets weekly study preferences in bulk (e.g. {'Monday': 3.0, ...})."""
    if not student_id:
        raise ValidationError("student_id is required.")
    if not isinstance(prefs_dict, dict):
        raise ValidationError("preferences must be a dictionary of weekday to hours.")

    saved = {}
    for day, hrs in prefs_dict.items():
        res = set_study_preference(student_id, day, hrs)
        saved[res["weekday"]] = res["available_hours"]
    return saved
