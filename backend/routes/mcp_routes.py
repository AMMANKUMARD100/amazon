from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.services.exceptions import AppError
from backend.services.task_service import list_tasks, add_task, update_task, delete_task
from backend.services.attendance_service import get_raw_attendance, calculate_attendance
from backend.services.schedule_service import get_timetable, get_today_reminder
from backend.services.planner_service import generate_study_plan
from backend.services.dashboard_service import get_dashboard_summary
from backend.services.faq_service import search_faq
from backend.middleware.logger import mcp_logger
from backend.middleware.security import sanitize_input, validate_assignment_input
from backend.database.connection import execute_query

mcp_bp = Blueprint('mcp', __name__)

def get_session_student_id():
    """Extracts student_id exclusively from authenticated session."""
    if not current_user.is_authenticated:
        return None
    if current_user.role == 'Student' and hasattr(current_user, 'student_id') and current_user.student_id:
        return current_user.student_id
    if current_user.role == 'Admin':
        return current_user.student_id or 1
    return None

@mcp_bp.errorhandler(AppError)
def handle_app_error(err):
    return jsonify(err.to_dict()), err.status_code

# Tool 1: getAssignments
@mcp_bp.route('/getAssignments', methods=['GET', 'POST'])
@login_required
def get_assignments():
    mcp_logger.info("Executing MCP Tool: getAssignments")
    student_id = get_session_student_id()
    tasks = list_tasks(student_id)
    return jsonify(tasks), 200

# Tool 2: addAssignment
@mcp_bp.route('/addAssignment', methods=['POST'])
@login_required
def mcp_add_assignment():
    mcp_logger.info("Executing MCP Tool: addAssignment")
    student_id = get_session_student_id()
    data = request.get_json() or {}

    errors = validate_assignment_input(data)
    if errors:
        return jsonify({"error": "ValidationFailed", "messages": errors}), 400

    task = add_task(
        student_id=student_id,
        title=data.get("title"),
        due_date=data.get("due_date"),
        priority=data.get("priority", "Medium"),
        description=data.get("description", ""),
        subject_id=data.get("subject_id")
    )
    return jsonify({"message": "Assignment created successfully.", "id": task["id"]}), 201

# Tool 3: updateAssignment
@mcp_bp.route('/updateAssignment', methods=['POST', 'PUT'])
@login_required
def mcp_update_assignment():
    mcp_logger.info("Executing MCP Tool: updateAssignment")
    student_id = get_session_student_id()
    data = request.get_json() or {}
    assignment_id = data.get("assignment_id")
    if not assignment_id:
        return jsonify({"error": "MissingParameter", "message": "assignment_id is required."}), 400

    update_task(student_id, assignment_id, data)
    return jsonify({"message": "Assignment updated successfully."}), 200

# Tool 4: deleteAssignment
@mcp_bp.route('/deleteAssignment', methods=['POST', 'DELETE'])
@login_required
def mcp_delete_assignment():
    mcp_logger.info("Executing MCP Tool: deleteAssignment")
    student_id = get_session_student_id()
    data = request.get_json() if request.is_json else {}
    assignment_id = data.get("assignment_id") or request.args.get("assignment_id")
    if not assignment_id:
        return jsonify({"error": "MissingParameter", "message": "assignment_id is required."}), 400

    res = delete_task(student_id, int(assignment_id))
    return jsonify(res), 200

# Tool 5: getAttendance
@mcp_bp.route('/getAttendance', methods=['GET', 'POST'])
@login_required
def mcp_get_attendance():
    mcp_logger.info("Executing MCP Tool: getAttendance")
    student_id = get_session_student_id()
    records = get_raw_attendance(student_id)
    return jsonify(records), 200

# Tool 6: calculateAttendance
@mcp_bp.route('/calculateAttendance', methods=['GET', 'POST'])
@login_required
def mcp_calculate_attendance():
    mcp_logger.info("Executing MCP Tool: calculateAttendance")
    student_id = get_session_student_id()
    stats = calculate_attendance(student_id)
    return jsonify(stats), 200

# Tool 7: getTimetable
@mcp_bp.route('/getTimetable', methods=['GET', 'POST'])
@login_required
def mcp_get_timetable():
    mcp_logger.info("Executing MCP Tool: getTimetable")
    student_id = get_session_student_id()
    timetable = get_timetable(student_id)
    return jsonify(timetable), 200

# Tool 8: createStudyPlan
@mcp_bp.route('/createStudyPlan', methods=['POST'])
@login_required
def mcp_create_study_plan():
    mcp_logger.info("Executing MCP Tool: createStudyPlan")
    student_id = get_session_student_id()
    data = request.get_json() or {}

    subject_id = data.get("subject_id")
    date = sanitize_input(data.get("date", "")).strip()
    start_time = sanitize_input(data.get("start_time", "")).strip()
    end_time = sanitize_input(data.get("end_time", "")).strip()
    topic = sanitize_input(data.get("topic", "")).strip()
    status = sanitize_input(data.get("status", "Scheduled")).strip()

    if not all([student_id, subject_id, date, start_time, end_time, topic]):
        return jsonify({"error": "MissingParameter", "message": "All fields are required to create a study plan."}), 400

    query = """
        INSERT INTO study_plans (student_id, subject_id, date, start_time, end_time, topic, status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    plan_id = execute_query(query, (student_id, subject_id, date, start_time, end_time, topic, status), commit=True)
    return jsonify({"message": "Study plan created successfully.", "id": plan_id}), 201

# Tool 9: calculateCGPA
@mcp_bp.route('/calculateCGPA', methods=['GET', 'POST'])
@login_required
def mcp_calculate_cgpa():
    mcp_logger.info("Executing MCP Tool: calculateCGPA")
    student_id = get_session_student_id()
    data = request.get_json() if request.is_json else {}

    student = execute_query("SELECT cgpa, current_semester FROM students WHERE id = ?;", (student_id,), fetch_one=True)
    if not student:
        return jsonify({"error": "NotFound", "message": "Student not found."}), 404

    grade_points = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}
    post_grades = data.get("grades", [])
    current_cgpa = student['cgpa']

    if post_grades:
        total_credits = 0
        total_grade_points = 0
        for item in post_grades:
            code = item.get("code")
            grade = item.get("grade", "A").upper()
            points = grade_points.get(grade, 4.0)

            subject = execute_query(
                "SELECT credits FROM subjects WHERE student_id = ? AND code = ?;",
                (student_id, code),
                fetch_one=True
            )
            credits = subject['credits'] if subject else 3
            total_credits += credits
            total_grade_points += (points * credits)

        calculated_gpa = round(total_grade_points / total_credits, 2) if total_credits > 0 else 0.0
        new_cgpa = round((current_cgpa * (student['current_semester'] - 1) + calculated_gpa) / student['current_semester'], 2)

        return jsonify({
            "current_cgpa": current_cgpa,
            "semester_gpa": calculated_gpa,
            "projected_cgpa": new_cgpa,
            "total_credits": total_credits
        }), 200

    return jsonify({
        "current_cgpa": current_cgpa,
        "semester_gpa": current_cgpa,
        "projected_cgpa": current_cgpa,
        "total_credits": 0
    }), 200

# Tool 10: getDashboard
@mcp_bp.route('/getDashboard', methods=['GET', 'POST'])
@login_required
def mcp_get_dashboard():
    mcp_logger.info("Executing MCP Tool: getDashboard")
    student_id = get_session_student_id()
    summary = get_dashboard_summary(student_id)
    return jsonify(summary), 200

# Tool 11: searchFAQ
@mcp_bp.route('/searchFAQ', methods=['GET', 'POST'])
def mcp_search_faq():
    mcp_logger.info("Executing MCP Tool: searchFAQ")
    data = request.get_json() if request.is_json else {}
    query_str = (data.get("query") or request.args.get("query") or "").strip()
    results = search_faq(query_str)
    return jsonify(results), 200

# Tool 12: todayReminder
@mcp_bp.route('/todayReminder', methods=['GET', 'POST'])
@login_required
def mcp_today_reminder():
    mcp_logger.info("Executing MCP Tool: todayReminder")
    student_id = get_session_student_id()
    reminder = get_today_reminder(student_id)
    return jsonify(reminder), 200
