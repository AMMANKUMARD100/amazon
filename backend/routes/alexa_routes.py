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
    """Deterministic intent parser delegating to unified tool_registry."""
    from backend.tools import execute_tool, tool_registry
    text = utterance.lower().strip()

    # 1. Complete task intent
    complete_match = re.search(r"^(?:complete|finish|mark done|done)\s+(?:task|assignment)?\s*(.+)$", text)
    if complete_match:
        target = complete_match.group(1).strip()
        args = {"task_id": int(target)} if target.isdigit() else {"task_title": target}
        out = execute_tool("complete_task", student_id, args)
        if out["success"]:
            res = out["result"]
            if isinstance(res, dict) and res.get("ambiguity"):
                speech = "Multiple tasks matched that description: " + ", ".join([f"#{c['id']} ({c['title']})" for c in res["candidates"]]) + ". Please specify by task ID."
                return {
                    "speech": speech,
                    "card": {"title": "Multiple Tasks Found", "content": speech},
                    "action_executed": "complete_task",
                    "tool_result": res,
                    "mode": "deterministic_demo"
                }
            speech = f"Task '{res['title']}' has been marked as completed."
            return {
                "speech": speech,
                "card": {"title": "Task Completed", "content": speech},
                "action_executed": "complete_task",
                "tool_result": res,
                "mode": "deterministic_demo"
            }
        else:
            msg = out["error"]["message"]
            return {
                "speech": f"Could not complete task: {msg}",
                "card": {"title": "Task Notice", "content": msg},
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

        out = execute_tool("add_task", student_id, {"title": title, "due_date": due_date})
        if out["success"]:
            res = out["result"]
            speech = f"I've added the task '{title}' due on {res['due_date']}."
            return {
                "speech": speech,
                "card": {"title": "Task Added", "content": speech},
                "action_executed": "add_task",
                "tool_result": res,
                "mode": "deterministic_demo"
            }
        else:
            msg = out["error"]["message"]
            return {
                "speech": f"Sorry, could not save task: {msg}",
                "card": {"title": "Validation Error", "content": msg},
                "mode": "deterministic_demo"
            }

    # 3. Delete task intent
    delete_match = re.search(r"^(?:delete|remove)\s+(?:task|assignment)\s*(.+)$", text)
    if delete_match:
        target = delete_match.group(1).strip()
        # Check if confirming with a token: e.g. "delete task confirm <token>"
        confirm_token = None
        confirm_match = re.search(r"(?:confirm|token)\s+([a-f0-9]{32})", text)
        if confirm_match:
            confirm_token = confirm_match.group(1)

        args = {"confirm_token": confirm_token} if confirm_token else ({"task_id": int(target)} if target.isdigit() else {"task_title": target})
        out = execute_tool("delete_task", student_id, args)
        if out["success"]:
            res = out["result"]
            if isinstance(res, dict) and res.get("pending_confirmation"):
                speech = f"{res['message']} Say 'confirm token {res['confirm_token']}' to proceed."
                return {
                    "speech": speech,
                    "card": {"title": "Confirmation Required", "content": speech},
                    "action_executed": "delete_task",
                    "tool_result": res,
                    "mode": "deterministic_demo"
                }
            if isinstance(res, dict) and res.get("ambiguity"):
                speech = "Multiple tasks match that title: " + ", ".join([f"#{c['id']} ({c['title']})" for c in res["candidates"]]) + ". Please specify by task ID."
                return {
                    "speech": speech,
                    "card": {"title": "Multiple Tasks Found", "content": speech},
                    "action_executed": "delete_task",
                    "tool_result": res,
                    "mode": "deterministic_demo"
                }
            speech = res.get("message", "Task deleted.")
            return {
                "speech": speech,
                "card": {"title": "Delete Task", "content": speech},
                "action_executed": "delete_task",
                "tool_result": res,
                "mode": "deterministic_demo"
            }
        else:
            msg = out["error"]["message"]
            return {
                "speech": f"Could not delete task: {msg}",
                "card": {"title": "Error", "content": msg},
                "mode": "deterministic_demo"
            }

    # 4. List tasks
    if any(k in text for k in ["task", "assignment", "todo", "homework"]) and any(k in text for k in ["show", "list", "what", "pending", "view"]):
        out = execute_tool("list_tasks", student_id, {"status": "Pending"})
        tasks = out.get("result", []) if out["success"] else []
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
        out = execute_tool("get_attendance_summary", student_id, {})
        att = out.get("result", []) if out["success"] else []
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
        out = execute_tool("get_today_summary", student_id, {})
        sched = out.get("result", {}) if out["success"] else {}
        classes = sched.get("classes", [])
        if classes:
            c_desc = ", ".join([f"{c['name']} at {c['start_time']} in {c['room']}" for c in classes])
            speech = f"For today ({sched.get('day', 'today')}), you have: {c_desc}."
        else:
            speech = f"You have no scheduled classes for today ({sched.get('day', 'today')})."
        return {
            "speech": speech,
            "card": {"title": "Today's Schedule", "content": speech},
            "action_executed": "get_today_schedule",
            "tool_result": sched,
            "mode": "deterministic_demo"
        }

    # 7. FAQ search
    out_faq = execute_tool("search_faq", student_id, {"query": utterance})
    faq_results = out_faq.get("result", []) if out_faq["success"] else []
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
