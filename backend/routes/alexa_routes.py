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

    # 7. Open App / Website
    if any(k in text for k in ["open youtube", "open google", "open spotify", "launch", "open website", "open app"]):
        from backend.services.assistant_service import open_app_or_site
        target = "google"
        query = None
        if "youtube" in text:
            target = "youtube"
            m = re.search(r"(?:search for|search|play|for)\s+(.+)$", utterance, re.IGNORECASE)
            if m:
                query = m.group(1).strip()
        elif "spotify" in text:
            target = "spotify"
        elif "calculator" in text:
            target = "calculator"
        elif "google" in text:
            target = "google"
            m = re.search(r"(?:search for|search|for)\s+(.+)$", utterance, re.IGNORECASE)
            if m:
                query = m.group(1).strip()

        res = open_app_or_site(target=target, query=query)
        return {
            "speech": res["spoken_response"],
            "card": {"title": f"Opening {res['app']}", "content": res["spoken_response"]},
            "action_executed": "open_app_or_site",
            "tool_result": res,
            "mode": "deterministic_demo"
        }

    # 8. Web Search & Cricket Matches
    if any(k in text for k in ["cricket", "match today", "live score", "search for", "google search", "search web"]):
        from backend.services.assistant_service import search_web_instant
        q = re.sub(r"^(?:search for|search|google search|look up)\s+", "", utterance, flags=re.IGNORECASE).strip()
        res = search_web_instant(q or utterance)
        return {
            "speech": res["spoken_summary"],
            "card": {"title": f"Search: {res['query']}", "content": res["spoken_summary"]},
            "action_executed": "search_web_instant",
            "tool_result": res,
            "mode": "deterministic_demo"
        }

    # 9. Plan a Trip
    if any(k in text for k in ["plan a trip", "plan trip", "travel to", "vacation", "trip to"]):
        from backend.services.assistant_service import plan_trip
        dest_match = re.search(r"(?:to|visit|in)\s+([a-zA-Z\s]+?)(?:\s+for|\s+\d+|\s+days|\.|$)", utterance, re.IGNORECASE)
        dest = dest_match.group(1).strip() if dest_match else "Goa"
        res = plan_trip(destination=dest, days=3)
        return {
            "speech": res["spoken_response"],
            "card": {"title": f"Trip Plan: {dest}", "content": res["spoken_response"]},
            "action_executed": "plan_trip",
            "tool_result": res,
            "mode": "deterministic_demo"
        }

    # 10. Meetings & Reminders
    if any(k in text for k in ["schedule meeting", "meeting", "remind me today", "my meetings"]):
        from backend.services.assistant_service import schedule_meeting, get_today_meeting_reminder
        if any(k in text for k in ["remind me today", "today's meeting", "my meetings"]):
            res = get_today_meeting_reminder(student_id)
            return {
                "speech": res["spoken_reminder"],
                "card": {"title": "Today's Meetings", "content": res["spoken_reminder"]},
                "action_executed": "get_today_meeting_reminder",
                "tool_result": res,
                "mode": "deterministic_demo"
            }
        else:
            res = schedule_meeting(student_id=student_id, title="Project Sync", date="today", time="3:00 PM")
            return {
                "speech": res["spoken_confirmation"],
                "card": {"title": "Meeting Scheduled", "content": res["spoken_confirmation"]},
                "action_executed": "schedule_meeting",
                "tool_result": res,
                "mode": "deterministic_demo"
            }

    # 11. FAQ search (Only for specific campus policies)
    if any(k in text for k in ["curfew", "hostel", "warden", "campus rule", "mess fee", "library timing", "block c", "block d"]):
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

    # 12. General Knowledge & Universal Web Search (e.g. "king of chemicals", "who discovered gravity", science facts)
    from backend.services.assistant_service import search_web_instant
    res_web = search_web_instant(utterance)
    if res_web and res_web.get("spoken_summary"):
        return {
            "speech": res_web["spoken_summary"],
            "card": {"title": f"Answer: {utterance}", "content": res_web["spoken_summary"]},
            "action_executed": "search_web_instant",
            "tool_result": res_web,
            "mode": "deterministic_demo"
        }

    # Default fallback - Safety measure if query was unclear
    speech = "I didn't quite catch that. Could you please repeat your question again?"
    return {
        "speech": speech,
        "card": {"title": "Alexa Assistant", "content": speech},
        "action_executed": "clarify",
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

    from backend.config import Config
    from backend.llm.agent_loop import AgentLoop
    from backend.services.chat_service import create_or_get_session, append_message, get_session_messages

    # Multi-turn session resolution
    req_session_id = data.get("session_id")
    try:
        chat_sess = create_or_get_session(student_id=student_id, session_id=req_session_id)
        current_session_id = chat_sess["id"]
    except Exception:
        current_session_id = None

    # Load stored history if session exists and history not explicitly provided
    history = data.get("history")
    if history is None and current_session_id:
        stored_msgs = get_session_messages(student_id, current_session_id)
        # Convert stored messages to format expected by agent loop
        history = []
        for sm in stored_msgs:
            history.append({
                "role": sm["role"],
                "content": [{"text": sm["content"]}]
            })

    # Execute conversational agent turn
    loop = AgentLoop(student_id=student_id)
    executed_traces = []

    try:
        loop_result = loop.run_turn(clean_utterance, conversation_history=history or [])
        speech = loop_result.get("speech") or "I've processed your request."
        executed = loop_result.get("tool_calls_executed", [])
        last_tool = executed[-1]["tool_name"] if executed else "conversational_reply"
        last_tool_res = executed[-1]["output"] if executed else None
        executed_traces = executed

        sim_mode = "bedrock" if loop_result.get("provider") == "BedrockProvider" else "deterministic_demo"
        result = {
            "speech": speech,
            "card": {"title": "CampusMate Assistant", "content": speech},
            "action_executed": last_tool,
            "tool_result": last_tool_res,
            "mode": sim_mode,
            "history": loop_result.get("messages")
        }
    except Exception as e:
        # Fallback to deterministic demo engine if LLM provider fails
        result = run_deterministic_engine(student_id, clean_utterance)

    # Persist user utterance and assistant reply to chat history
    if current_session_id:
        try:
            append_message(student_id=student_id, session_id=current_session_id, role="user", content=utterance)
            append_message(
                student_id=student_id,
                session_id=current_session_id,
                role="assistant",
                content=result.get("speech", ""),
                action_executed=result.get("action_executed"),
                tool_trace=executed_traces
            )
        except Exception as pe:
            pass

    alexa_response = {
        "version": "1.0",
        "sessionAttributes": {
            "student_id": student_id,
            "session_id": current_session_id,
            "last_utterance": utterance,
            "history": result.get("history")
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
            "session_id": current_session_id,
            "mode": result.get("mode", "deterministic_demo"),
            "action_executed": result.get("action_executed"),
            "tool_result": result.get("tool_result"),
            "tool_traces": executed_traces,
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


@alexa_bp.route('/intent', methods=['POST'])
def handle_direct_intent():
    """Direct intent resolution for Alexa+ Simulator without requiring prior cookie login."""
    data = request.get_json() or {}
    utterance = sanitize_input(data.get("utterance", "")).strip()
    if not utterance:
        return jsonify({"error": "ValidationFailed", "message": "Utterance is required."}), 400

    student_id = 1
    if current_user.is_authenticated and hasattr(current_user, 'student_id') and current_user.student_id:
        student_id = current_user.student_id

    # Handle Calls (e.g. "call papa")
    clean_low = utterance.lower()
    if clean_low.startswith("call ") or " call " in clean_low:
        m = re.search(r"call\s+([a-zA-Z\s]+)", utterance, re.IGNORECASE)
        contact = m.group(1).strip() if m else "Contact"
        speech = f"Searching for '{contact}' in your contacts. Dialing {contact} now."
        return jsonify({
            "speech": speech,
            "spoken_response": speech,
            "card": {"title": f"Calling {contact}", "content": speech},
            "action_executed": "call_contact",
            "tool_result": {"contact": contact, "status": "dialing", "url": f"tel:{contact}"},
            "data": {"contact": contact, "url": f"tel:{contact}"}
        }), 200

    # Handle WhatsApp message (e.g. "open whatsapp in chrome browser and send message to mummy go to chennai")
    if "whatsapp" in clean_low and ("send message" in clean_low or "message" in clean_low):
        contact_match = re.search(r"(?:to|contact)\s+([a-zA-Z]+)", utterance, re.IGNORECASE)
        contact = contact_match.group(1).strip() if contact_match else "Mummy"
        msg_match = re.search(r"(?:message|saying|text)\s+(?:to\s+[a-zA-Z]+\s+)?(.+)$", utterance, re.IGNORECASE)
        msg_text = msg_match.group(1).strip() if msg_match else "Hello"
        import urllib.parse
        encoded_msg = urllib.parse.quote(msg_text)
        wa_url = f"https://web.whatsapp.com/send?text={encoded_msg}"
        import webbrowser
        try:
            webbrowser.open(wa_url)
        except Exception:
            pass
        speech = f"Opening WhatsApp in Chrome to send message '{msg_text}' to {contact}."
        return jsonify({
            "speech": speech,
            "spoken_response": speech,
            "card": {"title": f"WhatsApp: {contact}", "content": f"Message: {msg_text}"},
            "action_executed": "send_whatsapp",
            "tool_result": {"contact": contact, "message": msg_text, "url": wa_url},
            "data": {"contact": contact, "url": wa_url}
        }), 200

    result = run_deterministic_engine(student_id, utterance)
    # Ensure spoken_response and data fields match frontend expectations
    result["spoken_response"] = result.get("speech", "")
    result["data"] = result.get("tool_result", {})
    return jsonify(result), 200

