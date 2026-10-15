"""Chat history REST API endpoints for CampusMate AI.

Exposes endpoints for creating/listing sessions, fetching message history with audit traces,
and deleting sessions, strictly scoped to the authenticated student.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.services.exceptions import AppError, ValidationError
from backend.services.chat_service import (
    create_or_get_session,
    list_sessions,
    get_session_messages,
    delete_session
)
from backend.middleware.security import sanitize_input
from backend.middleware.logger import log_activity

chat_bp = Blueprint('chat', __name__)


def get_session_student_id():
    """Extracts student_id exclusively from authenticated session."""
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


@chat_bp.errorhandler(AppError)
def handle_app_error(err):
    return jsonify(err.to_dict()), err.status_code


@chat_bp.route('/sessions', methods=['GET'])
@login_required
def list_student_sessions():
    """Lists all chat sessions for the logged-in student."""
    student_id = get_session_student_id()
    if not student_id:
        return jsonify({"error": "Unauthorized", "message": "Valid student session required."}), 403

    sessions = list_sessions(student_id)
    return jsonify({"sessions": sessions}), 200


@chat_bp.route('/sessions', methods=['POST'])
@login_required
def create_student_session():
    """Creates a new chat session."""
    student_id = get_session_student_id()
    if not student_id:
        return jsonify({"error": "Unauthorized", "message": "Valid student session required."}), 403

    data = request.get_json() or {}
    title = sanitize_input(data.get("title", "Study Assistant Chat"))
    sess = create_or_get_session(student_id=student_id, title=title)
    return jsonify({"session": sess}), 201


@chat_bp.route('/sessions/<session_id>/messages', methods=['GET'])
@login_required
def get_messages(session_id):
    """Retrieves full conversation messages and tool traces for a session."""
    student_id = get_session_student_id()
    if not student_id:
        return jsonify({"error": "Unauthorized", "message": "Valid student session required."}), 403

    messages = get_session_messages(student_id=student_id, session_id=session_id)
    return jsonify({"session_id": session_id, "messages": messages}), 200


@chat_bp.route('/sessions/<session_id>', methods=['DELETE'])
@login_required
def remove_session(session_id):
    """Deletes a chat session and associated messages."""
    student_id = get_session_student_id()
    if not student_id:
        return jsonify({"error": "Unauthorized", "message": "Valid student session required."}), 403

    res = delete_session(student_id=student_id, session_id=session_id)
    return jsonify(res), 200
