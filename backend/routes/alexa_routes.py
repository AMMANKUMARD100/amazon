import re
import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.services.exceptions import AppError, ValidationError
from backend.services.task_service import list_tasks, add_task, complete_task, delete_task
from backend.services.attendance_service import calculate_attendance
from backend.services.schedule_service import get_today_reminder
from backend.services.faq_service import search_faq
from backend.middleware.security import sanitize_input
from backend.middleware.logger import log_activity

alexa_bp = Blueprint('alexa', __name__)

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
                from backend.database.connection import execute_query
                row = execute_query("SELECT id FROM students WHERE id = ?;", (sid,), fetch_one=True)
                if row:
                    return row['id']
            except (ValueError, TypeError):
                pass
        return None
    return None

@alexa_bp.errorhandler(AppError)
def handle_app_error(err):
    return jsonify(err.to_dict()), err.status_code

def run_deterministic_engine(student_id, utterance):
    """Deterministic intent parser delegating directly to domain services."""
    text = utterance.lower().strip()

    # 1. Complete task intent
    complete_match = re.search(r"^(?:complete|finish|mark done|done)\s+(?:task|assignment)?\s*(.+)$", text)
    if complete_match:
        target = complete_match.group(1).strip()
        # Find candidate tasks
        tasks = list_tasks(student_id, status="Pending")
        matched = None
        if target.isdigit():
            tid = int(target)
            matched = next((t for t in tasks if t['id'] == tid), None)
        else:
            matched = next((t for t in tasks if target in t['title'].lower()), None)

        if matched:
            res = complete_task(student_id, matched['id'])
            speech = f"Task '{res['title']}' has been marked as completed."
            return {
                "speech": speech,
                "card": {"title": "Task Completed", "content": speech},
                "action_executed": "complete_task",
                "tool_result": res,
                "mode": "deterministic_demo"
            }
        else:
            return {
                "speech": f"Could not find matching pending task for '{target}'.",
                "card": {"title": "Task Notice", "content": f"Task '{target}' not found."},
                "mode": "deterministic_demo"
            }

    # 2. Add task intent
    add_match = re.search(r"^(?:add task|create task|new assignment|add assignment|remind me to)\s+(.+)$", text)
    if add_match:
        content = add_match.group(1).strip()
        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|tomorrow|today)\b", content)
        due_date = None
        if date_match:
            d_str = date_match.group(1)
            today = datetime.date.today()
            if d_str == 'tomorrow':
                due_date = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            elif d_str == 'today':
                due_date = today.strftime("%Y-%m-%d")
            else:
                due_date = d_str

        title = re.sub(r"\b(due|on|by)?\s*(\d{4}-\d{2}-\d{2}|tomorrow|today)\b", "", content, flags=re.IGNORECASE).strip()
        if not title:
            title = content

        if not due_date:
            # Under P0 rules: Missing due date => ask, never invent one
            return {
                "speech": f"What is the due date for '{title}'? Please provide it in YYYY-MM-DD format.",
                "card": {"title": "Due Date Needed", "content": f"Please specify a due date for '{title}'."},
                "needs_input": "due_date",
                "action_executed": "add_task",
                "mode": "deterministic_demo"
            }

        try:
            res = add_task(student_id, title=title, due_date=due_date)
            speech = f"I've added the task '{title}' due on {res['due_date']}."
            return {
                "speech": speech,
                "card": {"title": "Task Added", "content": speech},
                "action_executed": "add_task",
                "tool_result": res,
                "mode": "deterministic_demo"
            }
        except AppError as e:
            return {
                "speech": f"Sorry, could not save task: {e.message}",
                "card": {"title": "Validation Error", "content": e.message},
                "mode": "deterministic_demo"
            }

    # 3. Delete task intent
    delete_match = re.search(r"^(?:delete|remove)\s+(?:task|assignment)\s*(.+)$", text)
    if delete_match:
        target = delete_match.group(1).strip()
        tasks = list_tasks(student_id)
        matched = None
        if target.isdigit():
            tid = int(target)
            matched = next((t for t in tasks if t['id'] == tid), None)
        else:
            matched = next((t for t in tasks if target in t['title'].lower()), None)

        if matched:
            res = delete_task(student_id, matched['id'])
            speech = res["message"]
            return {
                "speech": speech,
                "card": {"title": "Delete Task", "content": speech},
                "action_executed": "delete_task",
                "tool_result": res,
                "mode": "deterministic_demo"
            }
        else:
            return {
                "speech": f"Could not find task '{target}'.",
                "card": {"title": "Not Found", "content": f"Task '{target}' not found."},
                "mode": "deterministic_demo"
            }

    # 4. List tasks
    if any(k in text for k in ["task", "assignment", "todo", "homework"]) and any(k in text for k in ["show", "list", "what", "pending", "view"]):
        tasks = list_tasks(student_id, status="Pending")
        if not tasks:
            speech = "You have no pending tasks right now. Great job staying ahead!"
        else:
            items_str = ", ".join([f"{t['title']} (due {t['due_date']})" for t in tasks[:4]])
            speech = f"You have {len(tasks)} pending tasks: {items_str}."
        return {
            "speech": speech,
            "card": {"title": "Pending Tasks", "content": speech},
            "action_executed": "list_tasks",
            "tool_result": tasks,
            "mode": "deterministic_demo"
        }

    # 5. Check attendance
    if "attendance" in text or "miss class" in text:
        att = calculate_attendance(student_id)
        low = [a for a in att if a['percentage'] < 75]
        if low:
            speech = f"Warning: Your attendance in {low[0]['name']} is at {low[0]['percentage']}%, which is below 75%. You need to attend {low[0]['classes_needed_for_75']} consecutive classes."
        else:
            avg = round(sum(a['percentage'] for a in att) / len(att), 1) if att else 100.0
            speech = f"Your overall attendance is looking strong at an average of {avg}%. All subjects are above 75%."
        return {
            "speech": speech,
            "card": {"title": "Attendance Overview", "content": speech},
            "action_executed": "check_attendance",
            "tool_result": att,
            "mode": "deterministic_demo"
        }

    # 6. Today schedule
    if any(k in text for k in ["today", "schedule", "timetable", "class", "lecture"]):
        sched = get_today_reminder(student_id)
        classes = sched["classes"]
        if classes:
            c_desc = ", ".join([f"{c['name']} at {c['start_time']} in {c['room']}" for c in classes])
            speech = f"For today ({sched['day']}), you have: {c_desc}."
        else:
            speech = f"You have no scheduled classes for today ({sched['day']})."
        return {
            "speech": speech,
            "card": {"title": "Today's Schedule", "content": speech},
            "action_executed": "get_today_schedule",
            "tool_result": sched,
            "mode": "deterministic_demo"
        }

    # 7. FAQ search
    faq_results = search_faq(utterance)
    if faq_results:
        best = faq_results[0]
        speech = best['answer']
        return {
            "speech": speech,
            "card": {"title": best['question'], "content": speech},
            "action_executed": "search_faq",
            "tool_result": faq_results,
            "mode": "deterministic_demo"
        }

    # Default fallback
    speech = (
        "I am your CampusMate AI assistant. You can ask me to list your tasks, "
        "add new assignments with a due date, check your attendance, "
        "show today's lectures, or generate a personalized study plan."
    )
    return {
        "speech": speech,
        "card": {"title": "CampusMate Assistant", "content": speech},
        "action_executed": "help",
        "mode": "deterministic_demo"
    }

@alexa_bp.route('/simulate', methods=['POST'])
@login_required
def simulate_alexa():
    """Simulates Alexa+-style conversational interaction scoped to authenticated student."""
    student_id = get_session_student_id()
    data = request.get_json() or {}
    utterance = sanitize_input(data.get("utterance", "")).strip()

    if not utterance:
        return jsonify({"error": "ValidationFailed", "message": "Utterance is required."}), 400

    clean_utterance = re.sub(r"^(hey alexa|alexa|campusmate|hey campusmate)[,\s]*", "", utterance, flags=re.IGNORECASE).strip()
    if not clean_utterance:
        clean_utterance = utterance

    result = run_deterministic_engine(student_id, clean_utterance)

    alexa_response = {
        "version": "1.0",
        "sessionAttributes": {
            "student_id": student_id,
            "last_utterance": utterance
        },
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": result.get("speech", "")
            },
            "card": {
                "type": "Standard",
                "title": result.get("card", {}).get("title", "CampusMate AI"),
                "text": result.get("card", {}).get("content", result.get("speech", ""))
            },
            "shouldEndSession": False
        },
        "simulation": {
            "provider": "CampusMate Alexa+-style simulation",
            "mode": result.get("mode", "deterministic_demo"),
            "action_executed": result.get("action_executed"),
            "tool_result": result.get("tool_result"),
            "needs_input": result.get("needs_input"),
            "timestamp": datetime.datetime.now().isoformat()
        }
    }

    log_activity(
        current_user.id,
        "ALEXA_SIMULATION_UTTERANCE",
        f"Utterance: '{utterance}' -> Executed: {result.get('action_executed')}",
        request.remote_addr
    )

    return jsonify(alexa_response), 200
