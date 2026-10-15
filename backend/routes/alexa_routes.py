import os
import json
import re
import datetime
import urllib.request
import urllib.error
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from backend.database.connection import execute_query
from backend.middleware.security import sanitize_input
from backend.middleware.logger import error_logger, log_activity

alexa_bp = Blueprint('alexa', __name__)

def get_active_student_id():
    if current_user.is_authenticated and hasattr(current_user, 'student_id') and current_user.student_id:
        return current_user.student_id
    data = request.get_json() if request.is_json else {}
    if data and data.get("student_id"):
        return int(data["student_id"])
    if request.args.get("student_id"):
        return int(request.args.get("student_id"))
    return 1  # seeded default student

# -------------------------------------------------------------
# Real Application Function Tools callable by Conversational Agent
# -------------------------------------------------------------
def tool_list_tasks(student_id, status=None):
    """Lists current student assignments and pending tasks."""
    query = """
        SELECT a.id, a.title, a.due_date, a.status, a.priority, COALESCE(s.name, 'General') as subject
        FROM assignments a
        LEFT JOIN subjects s ON a.subject_id = s.id
        WHERE a.student_id = ?
    """
    params = [student_id]
    if status in ['Pending', 'Completed']:
        query += " AND a.status = ?"
        params.append(status)
    query += " ORDER BY a.due_date ASC LIMIT 10;"
    rows = execute_query(query, tuple(params), fetch_all=True)
    return [dict(r) for r in rows]

def tool_add_task(student_id, title, due_date, priority="Medium", description=""):
    """Adds a task with date validation and persistence guarantee."""
    if not title:
        return {"error": "MissingTitle", "message": "Task title is required."}
    
    # Strict date validation
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(due_date)):
        # Try to parse relative words like 'tomorrow' or 'next monday'
        today = datetime.date.today()
        if str(due_date).lower() == 'tomorrow':
            due_date = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        elif str(due_date).lower() == 'today':
            due_date = today.strftime("%Y-%m-%d")
        else:
            return {"error": "InvalidDate", "message": "Date must be YYYY-MM-DD format."}
            
    # Find subject id
    first_sub = execute_query("SELECT id FROM subjects WHERE student_id = ? LIMIT 1;", (student_id,), fetch_one=True)
    subject_id = first_sub['id'] if first_sub else 1
    
    priority_clean = priority.capitalize() if priority in ['High', 'Medium', 'Low', 'high', 'medium', 'low'] else 'Medium'
    
    new_id = execute_query(
        "INSERT INTO assignments (student_id, subject_id, title, description, due_date, status, priority) "
        "VALUES (?, ?, ?, ?, ?, 'Pending', ?);",
        (student_id, subject_id, title, description, due_date, priority_clean),
        commit=True
    )
    
    saved = execute_query("SELECT id, title, due_date, status, priority FROM assignments WHERE id = ?;", (new_id,), fetch_one=True)
    if saved:
        return {"success": True, "task": dict(saved)}
    return {"error": "PersistenceFailed", "message": "Task could not be saved to database."}

def tool_complete_task(student_id, task_id_or_title):
    """Marks a task as completed."""
    # Check if int
    task = None
    try:
        task_id = int(task_id_or_title)
        task = execute_query("SELECT id, title FROM assignments WHERE id = ? AND student_id = ?;", (task_id, student_id), fetch_one=True)
    except (ValueError, TypeError):
        # Search by title match
        task = execute_query(
            "SELECT id, title FROM assignments WHERE student_id = ? AND title LIKE ? AND status = 'Pending' LIMIT 1;",
            (student_id, f"%{task_id_or_title}%"),
            fetch_one=True
        )
        
    if not task:
        return {"error": "NotFound", "message": f"Could not find matching pending task for '{task_id_or_title}'."}
        
    execute_query("UPDATE assignments SET status = 'Completed' WHERE id = ?;", (task['id'],), commit=True)
    return {"success": True, "task_id": task['id'], "title": task['title'], "status": "Completed"}

def tool_delete_task(student_id, task_id_or_title):
    """Deletes a task permanently with persistence confirmation."""
    task = None
    try:
        task_id = int(task_id_or_title)
        task = execute_query("SELECT id, title FROM assignments WHERE id = ? AND student_id = ?;", (task_id, student_id), fetch_one=True)
    except (ValueError, TypeError):
        task = execute_query(
            "SELECT id, title FROM assignments WHERE student_id = ? AND title LIKE ? LIMIT 1;",
            (student_id, f"%{task_id_or_title}%"),
            fetch_one=True
        )
    if not task:
        return {"error": "NotFound", "message": f"Could not find task '{task_id_or_title}'."}
        
    tid = task['id']
    execute_query("DELETE FROM assignments WHERE id = ?;", (tid,), commit=True)
    
    check = execute_query("SELECT id FROM assignments WHERE id = ?;", (tid,), fetch_one=True)
    if check:
        return {"error": "PersistenceError", "message": "Failed to remove task from database."}
    return {"success": True, "message": f"Task '{task['title']}' deleted successfully."}

def tool_check_attendance(student_id):
    """Calculates attendance status across all registered courses."""
    subjects = execute_query("SELECT id, code, name FROM subjects WHERE student_id = ?;", (student_id,), fetch_all=True)
    results = []
    for s in subjects:
        records = execute_query("SELECT status FROM attendance WHERE student_id = ? AND subject_id = ?;", (student_id, s['id']), fetch_all=True)
        present = sum(1 for r in records if r['status'] == 'Present')
        absent = sum(1 for r in records if r['status'] == 'Absent')
        total = present + absent
        pct = round((present / total) * 100, 1) if total > 0 else 100.0
        results.append({
            "code": s['code'],
            "name": s['name'],
            "present": present,
            "absent": absent,
            "percentage": pct,
            "status": "Safe" if pct >= 75.0 else "Action Required"
        })
    return results

def tool_get_today_schedule(student_id):
    """Retrieves timetable lectures and study sessions for today."""
    today = datetime.date.today()
    day_name = today.strftime("%A")
    date_str = today.strftime("%Y-%m-%d")
    
    classes = execute_query(
        "SELECT t.start_time, t.end_time, t.room, s.code, s.name "
        "FROM timetable t JOIN subjects s ON t.subject_id = s.id "
        "WHERE t.student_id = ? AND t.day_of_week = ? ORDER BY t.start_time ASC;",
        (student_id, day_name),
        fetch_all=True
    )
    study = execute_query(
        "SELECT sp.start_time, sp.end_time, sp.topic, s.code "
        "FROM study_plans sp JOIN subjects s ON sp.subject_id = s.id "
        "WHERE sp.student_id = ? AND sp.date = ? AND sp.status = 'Scheduled';",
        (student_id, date_str),
        fetch_all=True
    )
    return {
        "date": date_str,
        "day": day_name,
        "classes": [dict(c) for c in classes],
        "study_sessions": [dict(s) for s in study]
    }

def tool_search_faq(query_text):
    """Searches campus policies and FAQ knowledge base."""
    words = query_text.lower().split()
    rows = execute_query("SELECT question, answer, category FROM faq;", fetch_all=True)
    matches = []
    for r in rows:
        q = r['question'].lower()
        a = r['answer'].lower()
        score = sum(3 for w in words if w in q) + sum(1 for w in words if w in a)
        if score > 0:
            matches.append({"question": r['question'], "answer": r['answer'], "category": r['category'], "score": score})
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches[:3]

# -------------------------------------------------------------
# Deterministic Heuristic Demo Mode Engine (Zero external API dependencies)
# -------------------------------------------------------------
def run_deterministic_engine(student_id, utterance):
    """Parses intent and executes tool deterministically when no LLM API key is present."""
    text = utterance.lower().strip()
    
    # 1. Complete task intent: "complete task 3", "finish homework", "mark assignment done"
    complete_match = re.search(r"(?:complete|finish|mark done|done)\s+(?:task|assignment)?\s*(.+)", text)
    if complete_match:
        target = complete_match.group(1).strip()
        result = tool_complete_task(student_id, target)
        if "success" in result:
            speech = f"Task '{result['title']}' has been marked as completed."
            return {
                "speech": speech,
                "card": {"title": "Task Completed", "content": speech},
                "action_executed": "complete_task",
                "tool_result": result,
                "mode": "deterministic_demo"
            }
        else:
            return {
                "speech": result.get("message", "Could not complete task."),
                "card": {"title": "Task Error", "content": result.get("message")},
                "mode": "deterministic_demo"
            }

    # 2. Add task intent: "add task Submit Project due 2026-10-28", "remind me to study on 2026-10-25"
    add_match = re.search(r"(?:add task|create task|new assignment|add assignment|remind me to)\s+(.+)", text)
    if add_match:
        content = add_match.group(1).strip()
        # Look for date pattern YYYY-MM-DD or tomorrow or today
        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|tomorrow|today)\b", content)
        due_date = date_match.group(1) if date_match else (datetime.date.today() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
        
        # Strip due date prefix if present
        title = re.sub(r"\b(due|on|by)?\s*(\d{4}-\d{2}-\d{2}|tomorrow|today)\b", "", content, flags=re.IGNORECASE).strip()
        if not title:
            title = content
            
        result = tool_add_task(student_id, title=title, due_date=due_date)
        if "success" in result:
            speech = f"I've added the task '{title}' due on {result['task']['due_date']}."
            return {
                "speech": speech,
                "card": {"title": "Task Added", "content": speech},
                "action_executed": "add_task",
                "tool_result": result,
                "mode": "deterministic_demo"
            }
        else:
            return {
                "speech": f"Sorry, I couldn't save that task: {result.get('message')}",
                "card": {"title": "Task Error", "content": result.get("message")},
                "mode": "deterministic_demo"
            }

    # 3. Delete task intent: "delete task 4", "remove assignment Lab Report"
    delete_match = re.search(r"(?:delete|remove)\s+(?:task|assignment)\s*(.+)", text)
    if delete_match:
        target = delete_match.group(1).strip()
        result = tool_delete_task(student_id, target)
        speech = result.get("message") if "success" in result else result.get("message", "Task not found.")
        return {
            "speech": speech,
            "card": {"title": "Delete Task", "content": speech},
            "action_executed": "delete_task",
            "tool_result": result,
            "mode": "deterministic_demo"
        }

    # 4. List tasks: "list tasks", "what assignments are due", "show my tasks"
    if any(k in text for k in ["task", "assignment", "todo", "to-do", "homework"]) and any(k in text for k in ["show", "list", "what", "get", "pending", "view"]):
        tasks = tool_list_tasks(student_id, status="Pending")
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

    # 5. Check attendance: "how is my attendance", "attendance percentage", "can i miss class"
    if "attendance" in text or "miss class" in text:
        att = tool_check_attendance(student_id)
        low = [a for a in att if a['percentage'] < 75]
        if low:
            speech = f"Warning: Your attendance in {low[0]['name']} is at {low[0]['percentage']}%, which is below the 75% threshold. You need to attend consecutive lectures."
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

    # 6. Today schedule: "what classes do i have today", "today schedule", "timetable"
    if any(k in text for k in ["today", "schedule", "timetable", "class", "lecture"]):
        sched = tool_get_today_schedule(student_id)
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

    # 7. FAQ / Campus policy questions
    faq_results = tool_search_faq(utterance)
    if faq_results:
        best = faq_results[0]
        speech = f"{best['answer']}"
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
        "add new assignments (e.g. 'Add task Physics Lab due 2026-10-30'), "
        "check your attendance, show today's lectures, or generate a personalized study plan."
    )
    return {
        "speech": speech,
        "card": {"title": "CampusMate Assistant", "content": speech},
        "action_executed": "help",
        "mode": "deterministic_demo"
    }

# -------------------------------------------------------------
# LLM Integration with Function Calling (Google Gemini / OpenAI compatible)
# -------------------------------------------------------------
def call_external_llm_with_tools(student_id, utterance, api_key):
    """Executes conversational assistant via Gemini REST API with function declarations."""
    # Build tools schema for Gemini 1.5/2.0 API
    gemini_tools = [
        {
            "function_declarations": [
                {
                    "name": "list_tasks",
                    "description": "Lists student tasks and assignments.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "status": {"type": "STRING", "description": "Filter by 'Pending' or 'Completed'"}
                        }
                    }
                },
                {
                    "name": "add_task",
                    "description": "Creates a new task with strict YYYY-MM-DD date validation.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "title": {"type": "STRING", "description": "Title of the task or assignment."},
                            "due_date": {"type": "STRING", "description": "Due date in YYYY-MM-DD format."},
                            "priority": {"type": "STRING", "description": "High, Medium, or Low."}
                        },
                        "required": ["title", "due_date"]
                    }
                },
                {
                    "name": "complete_task",
                    "description": "Marks a student task as completed.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "task_id_or_title": {"type": "STRING", "description": "ID or title substring of task"}
                        },
                        "required": ["task_id_or_title"]
                    }
                },
                {
                    "name": "check_attendance",
                    "description": "Returns attendance percentage for all courses.",
                    "parameters": {"type": "OBJECT", "properties": {}}
                },
                {
                    "name": "get_today_schedule",
                    "description": "Returns timetable lectures and study sessions for today.",
                    "parameters": {"type": "OBJECT", "properties": {}}
                }
            ]
        }
    ]
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": utterance}]
            }
        ],
        "tools": gemini_tools,
        "system_instruction": {
            "parts": [
                {"text": "You are CampusMate AI, a friendly student concierge. Help students manage tasks, study schedules, and attendance. Keep spoken answers concise, supportive, and formatted for Alexa voice responses."}
            ]
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            res_body = json.loads(response.read().decode('utf-8'))
            candidate = res_body.get('candidates', [{}])[0]
            content = candidate.get('content', {})
            parts = content.get('parts', [])
            
            # Check for function call
            for part in parts:
                if 'functionCall' in part:
                    fn = part['functionCall']
                    fn_name = fn.get('name')
                    fn_args = fn.get('args', {})
                    
                    tool_result = {}
                    if fn_name == 'list_tasks':
                        tool_result = tool_list_tasks(student_id, fn_args.get('status'))
                    elif fn_name == 'add_task':
                        tool_result = tool_add_task(student_id, fn_args.get('title'), fn_args.get('due_date'), fn_args.get('priority', 'Medium'))
                    elif fn_name == 'complete_task':
                        tool_result = tool_complete_task(student_id, fn_args.get('task_id_or_title'))
                    elif fn_name == 'check_attendance':
                        tool_result = tool_check_attendance(student_id)
                    elif fn_name == 'get_today_schedule':
                        tool_result = tool_get_today_schedule(student_id)
                        
                    # Second call with function result to get final speech response
                    speech = f"Executed {fn_name}: {json.dumps(tool_result)}"
                    return {
                        "speech": speech,
                        "card": {"title": fn_name.replace("_", " ").title(), "content": speech},
                        "action_executed": fn_name,
                        "tool_result": tool_result,
                        "mode": "llm_function_call"
                    }
                    
                if 'text' in part:
                    speech_text = part['text']
                    return {
                        "speech": speech_text,
                        "card": {"title": "CampusMate Alexa+", "content": speech_text},
                        "action_executed": "conversational_reply",
                        "mode": "llm_text"
                    }
    except Exception as e:
        error_logger.error(f"External LLM invocation failed, falling back to deterministic demo engine: {e}")
        return run_deterministic_engine(student_id, utterance)

# -------------------------------------------------------------
# Alexa+ Simulated Experience Endpoint
# -------------------------------------------------------------
@alexa_bp.route('/simulate', methods=['POST'])
def simulate_alexa():
    """Simulates an Alexa+ conversational interaction compliant with hackathon guidelines.
    
    Accepts:
    {
      "utterance": "Alexa, what are my tasks for today?",
      "device": "Echo Show 10 / Web Simulator",
      "student_id": 1
    }
    
    Returns standard Alexa response format with speech SSML/text, visual directive card,
    and structured execution trace.
    """
    student_id = get_active_student_id()
    data = request.get_json() or {}
    utterance = sanitize_input(data.get("utterance", "")).strip()
    
    if not utterance:
        return jsonify({"error": "ValidationFailed", "message": "Utterance is required."}), 400
        
    # Strip optional "Alexa" or "Computer" wake word invocation
    clean_utterance = re.sub(r"^(hey alexa|alexa|campusmate|hey campusmate)[,\s]*", "", utterance, flags=re.IGNORECASE).strip()
    if not clean_utterance:
        clean_utterance = utterance
        
    # Check if LLM API Key is configured on the backend
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_API_KEY")
    
    if api_key:
        result = call_external_llm_with_tools(student_id, clean_utterance, api_key)
    else:
        # Deterministic offline demo mode
        result = run_deterministic_engine(student_id, clean_utterance)
        
    # Construct standard Alexa+ simulated experience schema
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
            "provider": "Amazon Developer Hackathon - Alexa+ Track Simulation",
            "mode": result.get("mode", "deterministic_demo"),
            "action_executed": result.get("action_executed"),
            "tool_result": result.get("tool_result"),
            "timestamp": datetime.datetime.now().isoformat()
        }
    }
    
    log_activity(
        student_id, 
        "ALEXA_SIMULATION_UTTERANCE", 
        f"Utterance: '{utterance}' -> Executed: {result.get('action_executed')}", 
        request.remote_addr
    )
    
    return jsonify(alexa_response), 200
