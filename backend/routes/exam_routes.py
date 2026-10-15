from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.services.exam_service import (
    list_exams,
    get_exam,
    add_exam,
    update_exam,
    delete_exam,
    get_study_preferences,
    set_study_preference,
    set_bulk_study_preferences
)
from backend.services.exceptions import AppError
from backend.middleware.logger import log_activity

exam_bp = Blueprint('exams', __name__)

def get_session_student_id():
    """Extracts student_id exclusively from authenticated session, or validated admin param."""
    if not current_user.is_authenticated:
        return None
    if current_user.role == 'Student' and hasattr(current_user, 'student_id') and current_user.student_id:
        return current_user.student_id
    if current_user.role == 'Admin':
        raw_id = request.args.get("student_id") or (request.json.get("student_id") if request.is_json else None)
        if raw_id:
            try:
                sid = int(raw_id)
                from backend.database.connection import execute_query
                row = execute_query("SELECT id FROM students WHERE id = ?;", (sid,), fetch_one=True)
                if row:
                    return row['id']
            except (ValueError, TypeError):
                pass
        return None
    return None

@exam_bp.errorhandler(AppError)
def handle_app_error(err):
    return jsonify(err.to_dict()), err.status_code

@exam_bp.route('/', methods=['GET'])
@login_required
def list_student_exams():
    student_id = get_session_student_id()
    exams = list_exams(student_id)
    return jsonify(exams), 200

@exam_bp.route('/', methods=['POST'])
@login_required
def create_student_exam():
    student_id = get_session_student_id()
    data = request.get_json() or {}
    exam = add_exam(
        student_id=student_id,
        title=data.get("title"),
        exam_date=data.get("exam_date"),
        subject_id=data.get("subject_id"),
        subject_code=data.get("code"),
        notes=data.get("notes", "")
    )
    log_activity(current_user.id, "CREATE_EXAM", f"Created exam #{exam['id']}", request.remote_addr)
    return jsonify({"message": "Exam created successfully.", "exam": exam}), 201

@exam_bp.route('/<int:exam_id>', methods=['GET'])
@login_required
def get_student_exam(exam_id):
    student_id = get_session_student_id()
    exam = get_exam(student_id, exam_id)
    return jsonify(exam), 200

@exam_bp.route('/<int:exam_id>', methods=['PUT', 'PATCH'])
@login_required
def update_student_exam(exam_id):
    student_id = get_session_student_id()
    data = request.get_json() or {}
    updated = update_exam(student_id, exam_id, data)
    log_activity(current_user.id, "UPDATE_EXAM", f"Updated exam #{exam_id}", request.remote_addr)
    return jsonify({"message": "Exam updated successfully.", "exam": updated}), 200

@exam_bp.route('/<int:exam_id>', methods=['DELETE'])
@login_required
def delete_student_exam(exam_id):
    student_id = get_session_student_id()
    res = delete_exam(student_id, exam_id)
    log_activity(current_user.id, "DELETE_EXAM", f"Deleted exam #{exam_id}", request.remote_addr)
    return jsonify(res), 200

# -------------------------------------------------------------
# Study Preferences Routes
# -------------------------------------------------------------
@exam_bp.route('/preferences', methods=['GET'])
@login_required
def get_preferences():
    student_id = get_session_student_id()
    prefs = get_study_preferences(student_id)
    return jsonify(prefs), 200

@exam_bp.route('/preferences', methods=['POST', 'PUT'])
@login_required
def save_preferences():
    student_id = get_session_student_id()
    data = request.get_json() or {}
    if "weekday" in data and "available_hours" in data:
        res = set_study_preference(student_id, data["weekday"], data["available_hours"])
        return jsonify(res), 200
    else:
        res = set_bulk_study_preferences(student_id, data)
        return jsonify(res), 200
