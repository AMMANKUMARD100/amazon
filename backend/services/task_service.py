import re
import datetime
from backend.database.connection import execute_query
from backend.services.exceptions import ValidationError, NotFoundError, PersistenceError

def validate_date(date_str):
    """Validates YYYY-MM-DD date and returns parsed datetime.date object."""
    if not date_str or not isinstance(date_str, str):
        raise ValidationError("Due date is required and must be a string in YYYY-MM-DD format.")
    date_str = date_str.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValidationError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD.")
    try:
        y, m, d = map(int, date_str.split("-"))
        return datetime.date(y, m, d)
    except ValueError:
        raise ValidationError(f"Date '{date_str}' is not a valid calendar date.")

def list_tasks(student_id, status=None):
    """Lists tasks for a specific student."""
    if not student_id:
        raise ValidationError("student_id is required.")

    query = """
        SELECT a.id, a.subject_id, a.title, a.description, a.due_date, a.status, a.priority,
               COALESCE(s.code, 'GEN') as code, COALESCE(s.name, 'General') as subject_name
        FROM assignments a
        LEFT JOIN subjects s ON a.subject_id = s.id
        WHERE a.student_id = ?
    """
    params = [student_id]
    if status in ['Pending', 'Completed']:
        query += " AND a.status = ?"
        params.append(status)

    query += " ORDER BY a.due_date ASC, a.id DESC;"
    rows = execute_query(query, tuple(params), fetch_all=True)
    return [dict(r) for r in rows]

def get_task(student_id, task_id):
    """Gets a specific task belonging to student."""
    if not student_id or not task_id:
        raise ValidationError("student_id and task_id are required.")

    row = execute_query(
        """SELECT a.id, a.subject_id, a.title, a.description, a.due_date, a.status, a.priority,
                  COALESCE(s.code, 'GEN') as code, COALESCE(s.name, 'General') as subject_name
           FROM assignments a
           LEFT JOIN subjects s ON a.subject_id = s.id
           WHERE a.id = ? AND a.student_id = ?;""",
        (task_id, student_id),
        fetch_one=True
    )
    if not row:
        raise NotFoundError(f"Task #{task_id} not found.")
    return dict(row)

def add_task(student_id, title, due_date, priority="Medium", description="", subject_id=None, subject_code=None):
    """Creates a new task for the student."""
    if not student_id:
        raise ValidationError("student_id is required.")
    if not title or not isinstance(title, str) or not title.strip():
        raise ValidationError("Task title is required.")

    title_clean = title.strip()
    desc_clean = (description or "").strip()
    parsed_date = validate_date(due_date)
    date_str = parsed_date.strftime("%Y-%m-%d")

    pri = (priority or "Medium").capitalize().strip()
    if pri not in ['High', 'Medium', 'Low']:
        pri = 'Medium'

    # Resolve subject_id
    if not subject_id and subject_code:
        sub = execute_query(
            "SELECT id FROM subjects WHERE student_id = ? AND code = ?;",
            (student_id, subject_code.strip()),
            fetch_one=True
        )
        if sub:
            subject_id = sub['id']

    if not subject_id:
        first_sub = execute_query("SELECT id FROM subjects WHERE student_id = ? LIMIT 1;", (student_id,), fetch_one=True)
        if first_sub:
            subject_id = first_sub['id']
        else:
            subject_id = execute_query(
                "INSERT INTO subjects (student_id, code, name, credits, difficulty) VALUES (?, 'GEN', 'General Studies', 3, 'Medium');",
                (student_id,),
                commit=True
            )

    insert_query = """
        INSERT INTO assignments (student_id, subject_id, title, description, due_date, status, priority)
        VALUES (?, ?, ?, ?, ?, 'Pending', ?);
    """
    new_id = execute_query(
        insert_query,
        (student_id, subject_id, title_clean, desc_clean, date_str, pri),
        commit=True
    )

    saved = execute_query("SELECT id FROM assignments WHERE id = ? AND student_id = ?;", (new_id, student_id), fetch_one=True)
    if not saved:
        raise PersistenceError("Task could not be persisted in database.")

    return get_task(student_id, new_id)

def update_task(student_id, task_id, updates_dict):
    """Updates fields on an existing task."""
    get_task(student_id, task_id)  # raises NotFoundError if missing

    fields = []
    params = []

    if "title" in updates_dict:
        t = (updates_dict["title"] or "").strip()
        if not t:
            raise ValidationError("Task title cannot be empty.")
        fields.append("title = ?")
        params.append(t)

    if "description" in updates_dict:
        fields.append("description = ?")
        params.append((updates_dict["description"] or "").strip())

    if "due_date" in updates_dict:
        parsed = validate_date(updates_dict["due_date"])
        fields.append("due_date = ?")
        params.append(parsed.strftime("%Y-%m-%d"))

    if "status" in updates_dict:
        st = (updates_dict["status"] or "").capitalize().strip()
        if st not in ['Pending', 'Completed']:
            raise ValidationError("Status must be 'Pending' or 'Completed'.")
        fields.append("status = ?")
        params.append(st)

    if "priority" in updates_dict:
        pr = (updates_dict["priority"] or "").capitalize().strip()
        if pr not in ['High', 'Medium', 'Low']:
            raise ValidationError("Priority must be 'High', 'Medium', or 'Low'.")
        fields.append("priority = ?")
        params.append(pr)

    if not fields:
        return get_task(student_id, task_id)

    params.extend([task_id, student_id])
    sql = f"UPDATE assignments SET {', '.join(fields)} WHERE id = ? AND student_id = ?;"
    execute_query(sql, tuple(params), commit=True)

    return get_task(student_id, task_id)

def complete_task(student_id, task_id):
    """Marks task as completed."""
    get_task(student_id, task_id)
    execute_query("UPDATE assignments SET status = 'Completed' WHERE id = ? AND student_id = ?;", (task_id, student_id), commit=True)
    return get_task(student_id, task_id)

def delete_task(student_id, task_id):
    """Deletes task permanently."""
    existing = get_task(student_id, task_id)
    execute_query("DELETE FROM assignments WHERE id = ? AND student_id = ?;", (task_id, student_id), commit=True)
    check = execute_query("SELECT id FROM assignments WHERE id = ?;", (task_id,), fetch_one=True)
    if check:
        raise PersistenceError("Failed to delete task from database.")
    return {"message": f"Task '{existing['title']}' deleted successfully.", "task_id": task_id}
