import os
import re
import json
import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.database.connection import execute_query
from backend.middleware.security import sanitize_input
from backend.middleware.logger import log_activity, mcp_logger

tasks_bp = Blueprint('tasks', __name__)

def get_active_student_id():
    if current_user.is_authenticated and hasattr(current_user, 'student_id') and current_user.student_id:
        return current_user.student_id
    if current_user.is_authenticated and hasattr(current_user, 'role') and current_user.role == 'Admin':
        return request.args.get("student_id") or (request.json.get("student_id") if request.is_json else None) or 1
    # Fallback to request body or query parameter for testing/CLI
    data = request.get_json() if request.is_json else {}
    if data and data.get("student_id"):
        return int(data["student_id"])
    if request.args.get("student_id"):
        return int(request.args.get("student_id"))
    return 1  # Default seeded student ID for offline/demo operation

def validate_iso_date(date_str):
    """Validates YYYY-MM-DD date and returns datetime.date object or None."""
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return None
    try:
        y, m, d = map(int, date_str.split("-"))
        return datetime.date(y, m, d)
    except ValueError:
        return None

@tasks_bp.route('/', methods=['GET'])
def list_tasks():
    """List all tasks/assignments for the student with optional status filtering."""
    student_id = get_active_student_id()
    status = request.args.get('status')
    
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
    return jsonify([dict(r) for r in rows]), 200

@tasks_bp.route('/', methods=['POST'])
def add_task():
    """Create a new task with strict input and date validation."""
    student_id = get_active_student_id()
    data = request.get_json() or {}
    
    title = sanitize_input(data.get("title", "")).strip()
    description = sanitize_input(data.get("description", "")).strip()
    due_date_raw = sanitize_input(data.get("due_date", "")).strip()
    priority = sanitize_input(data.get("priority", "Medium")).capitalize().strip()
    subject_code = sanitize_input(data.get("code", "")).strip()
    subject_id = data.get("subject_id")
    
    if not title:
        return jsonify({"error": "ValidationFailed", "message": "Task title is required."}), 400
        
    parsed_date = validate_iso_date(due_date_raw)
    if not parsed_date:
        return jsonify({
            "error": "ValidationFailed", 
            "message": "Invalid date format. Expected valid YYYY-MM-DD (e.g. 2026-10-25)."
        }), 400
        
    if priority not in ['High', 'Medium', 'Low']:
        priority = 'Medium'
        
    # Resolve subject_id if not explicitly provided
    if not subject_id:
        if subject_code:
            sub = execute_query(
                "SELECT id FROM subjects WHERE student_id = ? AND code = ?;",
                (student_id, subject_code),
                fetch_one=True
            )
            subject_id = sub['id'] if sub else None
            
        if not subject_id:
            # Fall back to first student subject or create a General subject if none exists
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
    try:
        new_id = execute_query(
            insert_query,
            (student_id, subject_id, title, description, parsed_date.strftime("%Y-%m-%d"), priority),
            commit=True
        )
        # Verify persistence immediately
        saved = execute_query("SELECT id, title, due_date, status, priority FROM assignments WHERE id = ?;", (new_id,), fetch_one=True)
        if not saved:
            return jsonify({"error": "PersistenceError", "message": "Failed to persist task in database."}), 500
            
        mcp_logger.info(f"Task created successfully ID={new_id} for student_id={student_id}")
        return jsonify({
            "message": "Task created successfully.",
            "task": dict(saved)
        }), 201
    except Exception as e:
        return jsonify({"error": "DatabaseError", "message": str(e)}), 500

@tasks_bp.route('/<int:task_id>', methods=['PUT', 'PATCH'])
def update_task(task_id):
    """Edit an existing task (title, description, due_date, priority, status)."""
    student_id = get_active_student_id()
    data = request.get_json() or {}
    
    existing = execute_query(
        "SELECT id FROM assignments WHERE id = ? AND student_id = ?;",
        (task_id, student_id),
        fetch_one=True
    )
    if not existing:
        return jsonify({"error": "NotFound", "message": f"Task #{task_id} not found."}), 404
        
    updates = []
    params = []
    
    if "title" in data:
        title = sanitize_input(data["title"]).strip()
        if not title:
            return jsonify({"error": "ValidationFailed", "message": "Title cannot be empty."}), 400
        updates.append("title = ?")
        params.append(title)
        
    if "description" in data:
        updates.append("description = ?")
        params.append(sanitize_input(data["description"]).strip())
        
    if "due_date" in data:
        parsed_date = validate_iso_date(data["due_date"])
        if not parsed_date:
            return jsonify({"error": "ValidationFailed", "message": "Invalid due_date. Format must be YYYY-MM-DD."}), 400
        updates.append("due_date = ?")
        params.append(parsed_date.strftime("%Y-%m-%d"))
        
    if "status" in data:
        status = sanitize_input(data["status"]).capitalize().strip()
        if status not in ['Pending', 'Completed']:
            return jsonify({"error": "ValidationFailed", "message": "Status must be 'Pending' or 'Completed'."}), 400
        updates.append("status = ?")
        params.append(status)
        
    if "priority" in data:
        priority = sanitize_input(data["priority"]).capitalize().strip()
        if priority not in ['High', 'Medium', 'Low']:
            return jsonify({"error": "ValidationFailed", "message": "Priority must be 'High', 'Medium', or 'Low'."}), 400
        updates.append("priority = ?")
        params.append(priority)
        
    if not updates:
        return jsonify({"message": "No changes requested."}), 200
        
    params.append(task_id)
    sql = f"UPDATE assignments SET {', '.join(updates)} WHERE id = ?;"
    execute_query(sql, tuple(params), commit=True)
    
    updated = execute_query(
        "SELECT id, title, description, due_date, status, priority FROM assignments WHERE id = ?;",
        (task_id,),
        fetch_one=True
    )
    return jsonify({"message": "Task updated successfully.", "task": dict(updated)}), 200

@tasks_bp.route('/<int:task_id>/complete', methods=['POST', 'PATCH'])
def complete_task(task_id):
    """Mark a task as completed."""
    student_id = get_active_student_id()
    existing = execute_query(
        "SELECT id, title, status FROM assignments WHERE id = ? AND student_id = ?;",
        (task_id, student_id),
        fetch_one=True
    )
    if not existing:
        return jsonify({"error": "NotFound", "message": f"Task #{task_id} not found."}), 404
        
    execute_query("UPDATE assignments SET status = 'Completed' WHERE id = ?;", (task_id,), commit=True)
    return jsonify({
        "message": f"Task '{existing['title']}' marked as Completed.",
        "task_id": task_id,
        "status": "Completed"
    }), 200

@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Permanently delete a task with verified persistence check."""
    student_id = get_active_student_id()
    existing = execute_query(
        "SELECT id, title FROM assignments WHERE id = ? AND student_id = ?;",
        (task_id, student_id),
        fetch_one=True
    )
    if not existing:
        return jsonify({"error": "NotFound", "message": f"Task #{task_id} not found."}), 404
        
    execute_query("DELETE FROM assignments WHERE id = ?;", (task_id,), commit=True)
    
    # Confirm deletion
    check = execute_query("SELECT id FROM assignments WHERE id = ?;", (task_id,), fetch_one=True)
    if check:
        return jsonify({"error": "PersistenceError", "message": "Failed to remove task from database."}), 500
        
    return jsonify({
        "message": f"Task '{existing['title']}' deleted successfully.",
        "task_id": task_id
    }), 200
