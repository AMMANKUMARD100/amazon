import math
import re
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.database.connection import execute_query
from backend.middleware.logger import mcp_logger, log_activity
from backend.middleware.security import sanitize_input, validate_assignment_input

mcp_bp = Blueprint('mcp', __name__)

def get_student_id(data):
    """Helper to extract student_id from payload, session, or query parameters."""
    if current_user.is_authenticated and current_user.is_student():
        return current_user.student_id
    # Fallback for CLI or scripts passing student_id in body or params
    body_id = data.get("student_id") if data else None
    if body_id:
        return int(body_id)
    param_id = request.args.get("student_id")
    if param_id:
        return int(param_id)
    return None

# Tool 1: getAssignments
@mcp_bp.route('/getAssignments', methods=['GET', 'POST'])
def get_assignments():
    """MCP Tool: Retrieves all assignments for a student."""
    mcp_logger.info("Executing MCP Tool: getAssignments")
    data = request.get_json() if request.is_json else {}
    student_id = get_student_id(data)
    
    if not student_id:
        return jsonify({"error": "MissingParameter", "message": "student_id is required."}), 400
        
    query = """
        SELECT a.id, a.subject_id, a.title, a.description, a.due_date, a.status, a.priority, s.code, s.name 
        FROM assignments a 
        JOIN subjects s ON a.subject_id = s.id 
        WHERE a.student_id = ? 
        ORDER BY a.due_date ASC;
    """
    rows = execute_query(query, (student_id,), fetch_all=True)
    return jsonify([dict(row) for row in rows]), 200

# Tool 2: addAssignment
@mcp_bp.route('/addAssignment', methods=['POST'])
def add_assignment():
    """MCP Tool: Adds a new assignment."""
    mcp_logger.info("Executing MCP Tool: addAssignment")
    data = request.get_json() or {}
    
    errors = validate_assignment_input(data)
    if errors:
        return jsonify({"error": "ValidationFailed", "messages": errors}), 400
        
    student_id = get_student_id(data)
    subject_id = data.get("subject_id")
    title = sanitize_input(data.get("title", "")).strip()
    description = sanitize_input(data.get("description", "")).strip()
    due_date = sanitize_input(data.get("due_date", "")).strip()
    priority = sanitize_input(data.get("priority", "Medium")).strip()
    
    if not student_id or not subject_id:
        return jsonify({"error": "MissingParameter", "message": "student_id and subject_id are required."}), 400
        
    query = """
        INSERT INTO assignments (student_id, subject_id, title, description, due_date, status, priority)
        VALUES (?, ?, ?, ?, ?, 'Pending', ?);
    """
    try:
        new_id = execute_query(query, (student_id, subject_id, title, description, due_date, priority), commit=True)
        mcp_logger.info(f"MCP Tool addAssignment created assignment {new_id}")
        return jsonify({"message": "Assignment created successfully.", "id": new_id}), 201
    except Exception as e:
        return jsonify({"error": "DatabaseError", "message": str(e)}), 500

# Tool 3: updateAssignment
@mcp_bp.route('/updateAssignment', methods=['POST', 'PUT'])
def update_assignment():
    """MCP Tool: Updates an existing assignment."""
    mcp_logger.info("Executing MCP Tool: updateAssignment")
    data = request.get_json() or {}
    
    assignment_id = data.get("assignment_id")
    if not assignment_id:
        return jsonify({"error": "MissingParameter", "message": "assignment_id is required."}), 400
        
    # Check if assignment exists
    assignment = execute_query("SELECT id FROM assignments WHERE id = ?;", (assignment_id,), fetch_one=True)
    if not assignment:
        return jsonify({"error": "NotFound", "message": "Assignment not found."}), 404
        
    title = sanitize_input(data.get("title")).strip() if "title" in data else None
    description = sanitize_input(data.get("description")).strip() if "description" in data else None
    due_date = sanitize_input(data.get("due_date")).strip() if "due_date" in data else None
    status = sanitize_input(data.get("status")).strip() if "status" in data else None
    priority = sanitize_input(data.get("priority")).strip() if "priority" in data else None
    
    update_fields = []
    params = []
    
    if title is not None:
        update_fields.append("title = ?")
        params.append(title)
    if description is not None:
        update_fields.append("description = ?")
        params.append(description)
    if due_date is not None:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", due_date):
            return jsonify({"error": "ValidationFailed", "message": "Due date must be in YYYY-MM-DD format."}), 400
        update_fields.append("due_date = ?")
        params.append(due_date)
    if status is not None:
        if status not in ["Pending", "Completed"]:
            return jsonify({"error": "ValidationFailed", "message": "Status must be Pending or Completed."}), 400
        update_fields.append("status = ?")
        params.append(status)
    if priority is not None:
        if priority not in ["High", "Medium", "Low"]:
            return jsonify({"error": "ValidationFailed", "message": "Priority must be High, Medium, or Low."}), 400
        update_fields.append("priority = ?")
        params.append(priority)
        
    if not update_fields:
        return jsonify({"message": "No changes made."}), 200
        
    params.append(assignment_id)
    query = f"UPDATE assignments SET {', '.join(update_fields)} WHERE id = ?;"
    
    try:
        execute_query(query, tuple(params), commit=True)
        mcp_logger.info(f"MCP Tool updateAssignment updated assignment {assignment_id}")
        return jsonify({"message": "Assignment updated successfully."}), 200
    except Exception as e:
        return jsonify({"error": "DatabaseError", "message": str(e)}), 500

# Tool 4: deleteAssignment
@mcp_bp.route('/deleteAssignment', methods=['POST', 'DELETE'])
def delete_assignment():
    """MCP Tool: Deletes an assignment."""
    mcp_logger.info("Executing MCP Tool: deleteAssignment")
    data = request.get_json() if request.is_json else {}
    
    assignment_id = data.get("assignment_id") or request.args.get("assignment_id")
    if not assignment_id:
        return jsonify({"error": "MissingParameter", "message": "assignment_id is required."}), 400
        
    # Check if assignment exists
    assignment = execute_query("SELECT id FROM assignments WHERE id = ?;", (assignment_id,), fetch_one=True)
    if not assignment:
        return jsonify({"error": "NotFound", "message": "Assignment not found."}), 404
        
    try:
        execute_query("DELETE FROM assignments WHERE id = ?;", (assignment_id,), commit=True)
        mcp_logger.info(f"MCP Tool deleteAssignment removed assignment {assignment_id}")
        return jsonify({"message": "Assignment deleted successfully."}), 200
    except Exception as e:
        return jsonify({"error": "DatabaseError", "message": str(e)}), 500

# Tool 5: getAttendance
@mcp_bp.route('/getAttendance', methods=['GET', 'POST'])
def get_attendance():
    """MCP Tool: Retrieves all attendance records for a student."""
    mcp_logger.info("Executing MCP Tool: getAttendance")
    data = request.get_json() if request.is_json else {}
    student_id = get_student_id(data)
    
    if not student_id:
        return jsonify({"error": "MissingParameter", "message": "student_id is required."}), 400
        
    query = """
        SELECT a.id, a.subject_id, a.date, a.status, s.code, s.name 
        FROM attendance a 
        JOIN subjects s ON a.subject_id = s.id 
        WHERE a.student_id = ? 
        ORDER BY a.date DESC;
    """
    rows = execute_query(query, (student_id,), fetch_all=True)
    return jsonify([dict(row) for row in rows]), 200

# Tool 6: calculateAttendance
@mcp_bp.route('/calculateAttendance', methods=['GET', 'POST'])
def calculate_attendance():
    """MCP Tool: Calculates attendance percentage and heuristic stats for subjects."""
    mcp_logger.info("Executing MCP Tool: calculateAttendance")
    data = request.get_json() if request.is_json else {}
    student_id = get_student_id(data)
    
    if not student_id:
        return jsonify({"error": "MissingParameter", "message": "student_id is required."}), 400
        
    # Fetch subjects
    subjects = execute_query("SELECT id, code, name, credits FROM subjects WHERE student_id = ?;", (student_id,), fetch_all=True)
    
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
        total = present + absent  # Excused doesn't count towards denominator
        
        pct = 100.0
        if total > 0:
            pct = round((present / total) * 100, 2)
            
        # Attendance heuristic calculations:
        # P = present, A = absent. Target = 75%.
        # If pct < 75%: x = 3A - P classes needed consecutively.
        # If pct >= 75%: y = floor((P - 3A)/3) classes can be missed.
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
        
    return jsonify(results), 200

# Tool 7: getTimetable
@mcp_bp.route('/getTimetable', methods=['GET', 'POST'])
def get_timetable():
    """MCP Tool: Retrieves the student's timetable schedule."""
    mcp_logger.info("Executing MCP Tool: getTimetable")
    data = request.get_json() if request.is_json else {}
    student_id = get_student_id(data)
    
    if not student_id:
        return jsonify({"error": "MissingParameter", "message": "student_id is required."}), 400
        
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
    return jsonify([dict(row) for row in rows]), 200

# Tool 8: createStudyPlan
@mcp_bp.route('/createStudyPlan', methods=['POST'])
def create_study_plan():
    """MCP Tool: Creates a scheduled study session."""
    mcp_logger.info("Executing MCP Tool: createStudyPlan")
    data = request.get_json() or {}
    
    student_id = get_student_id(data)
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
    try:
        plan_id = execute_query(query, (student_id, subject_id, date, start_time, end_time, topic, status), commit=True)
        mcp_logger.info(f"MCP Tool createStudyPlan created plan {plan_id}")
        return jsonify({"message": "Study plan created successfully.", "id": plan_id}), 201
    except Exception as e:
        return jsonify({"error": "DatabaseError", "message": str(e)}), 500

# Tool 9: calculateCGPA
@mcp_bp.route('/calculateCGPA', methods=['GET', 'POST'])
def calculate_cgpa():
    """MCP Tool: Computes cumulative CGPA based on graded credits."""
    mcp_logger.info("Executing MCP Tool: calculateCGPA")
    data = request.get_json() if request.is_json else {}
    student_id = get_student_id(data)
    
    if not student_id:
        return jsonify({"error": "MissingParameter", "message": "student_id is required."}), 400
        
    # We can fetch subjects and map their difficulties or completion status to mock grades,
    # or calculate based on the student's base CGPA and current progress.
    # To make this real and interactive, let's write a CGPA manager:
    # A student has a base CGPA (saved in students table). Let's load the student profile.
    student = execute_query("SELECT cgpa, current_semester FROM students WHERE id = ?;", (student_id,), fetch_one=True)
    if not student:
        return jsonify({"error": "NotFound", "message": "Student not found."}), 404
        
    # Let's see: user can simulate CGPA calculations by passing a list of subject grades
    # E.g. [{"code": "CS101", "grade": "A"}, {"code": "CS102", "grade": "B"}]
    # Let's map grades to points: A=4.0, B=3.0, C=2.0, D=1.0, F=0.0
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
            
            # Fetch subject credits
            subject = execute_query(
                "SELECT credits FROM subjects WHERE student_id = ? AND code = ?;",
                (student_id, code),
                fetch_one=True
            )
            credits = subject['credits'] if subject else 3
            total_credits += credits
            total_grade_points += (points * credits)
            
        calculated_gpa = round(total_grade_points / total_credits, 2) if total_credits > 0 else 0.0
        
        # New CGPA is average of old base CGPA (assumed to cover past semesters) and new GPA
        new_cgpa = round((current_cgpa * (student['current_semester'] - 1) + calculated_gpa) / student['current_semester'], 2)
        
        return jsonify({
            "current_cgpa": current_cgpa,
            "semester_gpa": calculated_gpa,
            "projected_cgpa": new_cgpa,
            "total_credits": total_credits
        }), 200
        
    # Return current CGPA if no projection is supplied
    return jsonify({
        "current_cgpa": current_cgpa,
        "semester_gpa": current_cgpa,  # Default fallback
        "projected_cgpa": current_cgpa,
        "total_credits": 0
    }), 200

# Tool 10: getDashboard
@mcp_bp.route('/getDashboard', methods=['GET', 'POST'])
def get_dashboard():
    """MCP Tool: Summarizes student analytics data."""
    mcp_logger.info("Executing MCP Tool: getDashboard")
    data = request.get_json() if request.is_json else {}
    student_id = get_student_id(data)
    
    if not student_id:
        return jsonify({"error": "MissingParameter", "message": "student_id is required."}), 400
        
    # Gather counts and statistics:
    # 1. Total assignments count (pending, completed)
    pending_assignments = execute_query(
        "SELECT COUNT(*) FROM assignments WHERE student_id = ? AND status = 'Pending';",
        (student_id,), fetch_one=True
    )[0]
    completed_assignments = execute_query(
        "SELECT COUNT(*) FROM assignments WHERE student_id = ? AND status = 'Completed';",
        (student_id,), fetch_one=True
    )[0]
    
    # 2. Average Attendance Percentage across all subjects
    records = execute_query(
        "SELECT status FROM attendance WHERE student_id = ?;",
        (student_id,), fetch_all=True
    )
    present = sum(1 for r in records if r['status'] == 'Present')
    absent = sum(1 for r in records if r['status'] == 'Absent')
    total_att = present + absent
    overall_attendance = round((present / total_att) * 100, 2) if total_att > 0 else 100.0
    
    # 3. Scheduled study hours for the upcoming week
    study_sessions = execute_query(
        "SELECT date, start_time, end_time FROM study_plans WHERE student_id = ? AND status = 'Scheduled';",
        (student_id,), fetch_all=True
    )
    total_study_minutes = 0
    import datetime
    for session in study_sessions:
        try:
            # simple parser for HH:MM format
            sh, sm = map(int, session['start_time'].split(':'))
            eh, em = map(int, session['end_time'].split(':'))
            diff = (eh * 60 + em) - (sh * 60 + sm)
            if diff > 0:
                total_study_minutes += diff
        except Exception:
            pass
    study_hours = round(total_study_minutes / 60, 1)
    
    # 4. Profile Overview
    student_profile = execute_query(
        "SELECT full_name, matric_number, cgpa FROM students WHERE id = ?;",
        (student_id,), fetch_one=True
    )
    
    return jsonify({
        "student_name": student_profile['full_name'] if student_profile else "Student",
        "matric_number": student_profile['matric_number'] if student_profile else "",
        "cgpa": student_profile['cgpa'] if student_profile else 0.0,
        "pending_assignments": pending_assignments,
        "completed_assignments": completed_assignments,
        "overall_attendance": overall_attendance,
        "scheduled_study_hours": study_hours
    }), 200

# Tool 11: searchFAQ
@mcp_bp.route('/searchFAQ', methods=['GET', 'POST'])
def search_faq():
    """MCP Tool: Searches FAQ entries using keyword matching."""
    mcp_logger.info("Executing MCP Tool: searchFAQ")
    
    import json
    import os
    
    data = request.get_json() if request.is_json else {}
    query_str = (data.get("query") or request.args.get("query") or "").strip().lower()
    
    # Load FAQ list from static JSON file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, 'database', 'faq.json')
    
    faqs = []
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as f:
                faqs = json.load(f)
        except Exception as e:
            mcp_logger.error(f"Error reading faq.json: {e}")
            
    # If JSON read failed or empty, fallback to DB
    if not faqs:
        rows = execute_query("SELECT id, question, answer, category FROM faq;", fetch_all=True)
        faqs = [dict(row) for row in rows]
        
    if not query_str:
        return jsonify(faqs), 200
        
    # Run keyword matching
    matches = []
    for faq in faqs:
        question = faq.get("question", "").lower()
        answer = faq.get("answer", "").lower()
        category = faq.get("category", "").lower()
        
        # Simple match scoring
        score = 0
        words = query_str.split()
        for word in words:
            if word in question:
                score += 3
            if word in answer:
                score += 1
            if word in category:
                score += 2
                
        if score > 0:
            faq_copy = faq.copy()
            faq_copy["match_score"] = score
            matches.append(faq_copy)
            
    # Sort matches by score descending
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    return jsonify(matches), 200

# Tool 12: todayReminder
@mcp_bp.route('/todayReminder', methods=['GET', 'POST'])
def today_reminder():
    """MCP Tool: Gathers classes, due assignments and study plans for today."""
    mcp_logger.info("Executing MCP Tool: todayReminder")
    data = request.get_json() if request.is_json else {}
    student_id = get_student_id(data)
    
    if not student_id:
        return jsonify({"error": "MissingParameter", "message": "student_id is required."}), 400
        
    import datetime
    today = datetime.date.today()
    day_name = today.strftime("%A")  # Monday, Tuesday, etc.
    date_str = today.strftime("%Y-%m-%d")
    
    # 1. Timetable classes for today
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
        "SELECT a.title, a.due_date, a.priority, s.code "
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
    
    return jsonify({
        "date": date_str,
        "day": day_name,
        "classes": [dict(c) for c in classes],
        "assignments_due": [dict(a) for a in assignments],
        "study_sessions": [dict(s) for s in study_sessions]
    }), 200
