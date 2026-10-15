from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.services.task_service import (
    list_tasks,
    get_task,
    add_task,
    update_task,
    complete_task,
    delete_task
)
from backend.services.exceptions import AppError
from backend.middleware.logger import log_activity

tasks_bp = Blueprint('tasks', __name__)

def get_session_student_id():
    """Extracts student_id exclusively from authenticated session, or explicit validated parameter for admin."""
    if not current_user.is_authenticated:
        return None
    if current_user.role == 'Student' and hasattr(current_user, 'student_id') and current_user.student_id:
        return current_user.student_id
    if current_user.role == 'Admin':
        raw_id = request.args.get("student_id") or (request.json.get("student_id") if request.is_json else None)
        if raw_id:
            try:
                sid = int(raw_id)
                # Verify student exists
                from backend.database.connection import execute_query
                row = execute_query("SELECT id FROM students WHERE id = ?;", (sid,), fetch_one=True)
                if row:
                    return row['id']
            except (ValueError, TypeError):
                pass
        return None
    return None

@tasks_bp.errorhandler(AppError)
def handle_app_error(err):
    return jsonify(err.to_dict()), err.status_code

@tasks_bp.route('/', methods=['GET'])
@login_required
def list_student_tasks():
    student_id = get_session_student_id()
    status = request.args.get('status')
    tasks = list_tasks(student_id, status=status)
    return jsonify(tasks), 200

@tasks_bp.route('/', methods=['POST'])
@login_required
def create_student_task():
    student_id = get_session_student_id()
    data = request.get_json() or {}

    task = add_task(
        student_id=student_id,
        title=data.get("title"),
        due_date=data.get("due_date"),
        priority=data.get("priority", "Medium"),
        description=data.get("description", ""),
        subject_id=data.get("subject_id"),
        subject_code=data.get("code")
    )
    log_activity(current_user.id, "CREATE_TASK", f"Created task #{task['id']}", request.remote_addr)
    return jsonify({"message": "Task created successfully.", "task": task}), 201

@tasks_bp.route('/<int:task_id>', methods=['GET'])
@login_required
def get_student_task(task_id):
    student_id = get_session_student_id()
    task = get_task(student_id, task_id)
    return jsonify(task), 200

@tasks_bp.route('/<int:task_id>', methods=['PUT', 'PATCH'])
@login_required
def update_student_task(task_id):
    student_id = get_session_student_id()
    data = request.get_json() or {}
    updated = update_task(student_id, task_id, data)
    log_activity(current_user.id, "UPDATE_TASK", f"Updated task #{task_id}", request.remote_addr)
    return jsonify({"message": "Task updated successfully.", "task": updated}), 200

@tasks_bp.route('/<int:task_id>/complete', methods=['POST', 'PATCH'])
@login_required
def complete_student_task(task_id):
    student_id = get_session_student_id()
    completed = complete_task(student_id, task_id)
    log_activity(current_user.id, "COMPLETE_TASK", f"Completed task #{task_id}", request.remote_addr)
    return jsonify({"message": f"Task '{completed['title']}' marked as Completed.", "task": completed}), 200

@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@login_required
def delete_student_task(task_id):
    student_id = get_session_student_id()
    res = delete_task(student_id, task_id)
    log_activity(current_user.id, "DELETE_TASK", f"Deleted task #{task_id}", request.remote_addr)
    return jsonify(res), 200
