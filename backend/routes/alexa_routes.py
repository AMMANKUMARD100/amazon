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
    """Deterministic intent parser delegating to unified tool_registry + new services."""
    from backend.tools import execute_tool
    from backend.services.assistant_service import search_web_instant
    from backend.services.universal_qa import answer_question, is_knowledge_question
    from backend.services.meeting_service import (
        parse_meeting_from_utterance, schedule_meeting as svc_schedule_meeting,
        list_meetings, get_upcoming_meetings, check_due_reminders
    )
    from backend.services.strategy_service import (
        generate_exam_strategy, generate_project_strategy,
        generate_idea_suggestions, discuss_and_plan, is_strategy_query
    )
    from backend.services.conversation_state import (
        get_state, set_state, clear_state, update_state_data, build_follow_up_question
    )

    text = utterance.lower().strip()

    # ── 0a. Resume pending multi-turn conversation ──────────────────────────────
    pending = get_state(student_id) if student_id else None
    if pending:
        intent = pending["intent"]
        data = pending["data"]
        needs = data.get("needs", [])

        if needs:
            field = needs[0]
            # Store the user's reply as the missing field value
            update_state_data(student_id, {field: utterance.strip()})
            pending = get_state(student_id)
            data = pending["data"]
            needs = data.get("needs", [])
            # Check if there are still more fields needed
            needs = [n for n in needs if not data.get(n)]
            update_state_data(student_id, {"needs": needs})

        if not needs:
            # All data gathered — execute the pending intent
            clear_state(student_id)
            if intent == "schedule_meeting":
                try:
                    mtg = svc_schedule_meeting(
                        student_id=student_id,
                        title=data.get("title", "Team Meeting"),
                        meeting_date=data.get("meeting_date") or data.get("date", ""),
                        meeting_time=data.get("meeting_time", "10:00"),
                        participants=data.get("participants", ""),
                        location=data.get("location", "")
                    )
                    speech = (f"Meeting '{mtg['title']}' scheduled for {mtg['meeting_date']} "
                              f"at {mtg['meeting_time']}. I'll remind you before it starts.")
                    return {"speech": speech, "card": {"title": "Meeting Scheduled", "content": speech},
                            "action_executed": "schedule_meeting", "tool_result": mtg, "mode": "deterministic_demo"}
                except Exception as e:
                    speech = f"I couldn't schedule the meeting: {str(e)}. Please try again."
                    return {"speech": speech, "card": {"title": "Meeting Error", "content": speech}, "mode": "deterministic_demo"}

            elif intent == "exam_plan":
                subjects_raw = data.get("subjects", "")
                subjects = [s.strip() for s in re.split(r"[,;]+", subjects_raw) if s.strip()]
                days = int(data.get("days", 7))
                daily_hours = float(data.get("daily_hours", 4))
                plan = generate_exam_strategy(subjects, days, daily_hours)
                speech = plan.get("spoken", "Your study plan is ready.")
                return {"speech": speech, "card": {"title": "Exam Study Plan", "content": plan.get("summary", speech)},
                        "action_executed": "exam_plan", "tool_result": plan, "mode": "deterministic_demo"}

            elif intent == "project_plan":
                proj = generate_project_strategy(
                    project_name=data.get("project_name", "My Project"),
                    project_type=data.get("project_type", "generic"),
                    days_available=int(data.get("days", 30)),
                    team_size=int(data.get("team_size", 1))
                )
                speech = proj.get("spoken", "Your project plan is ready.")
                return {"speech": speech, "card": {"title": "Project Strategy", "content": speech},
                        "action_executed": "project_plan", "tool_result": proj, "mode": "deterministic_demo"}
        else:
            # Ask next pending question
            next_field = needs[0]
            q = build_follow_up_question(intent, next_field)
            return {"speech": q, "card": {"title": "More Info Needed", "content": q},
                    "needs_input": next_field, "action_executed": intent, "mode": "deterministic_demo"}

    # ── 0b. Check assistant_service direct facts (cricket, wars, PM, etc.) ──────
    res_direct = search_web_instant(utterance)
    if res_direct and res_direct.get("spoken_summary") and \
       not res_direct.get("spoken_summary", "").startswith("Based on latest references") and \
       len(res_direct.get("spoken_summary", "")) > 10:
        summary = res_direct["spoken_summary"]
        return {
            "speech": summary,
            "card": {"title": utterance[:60], "content": summary},
            "action_executed": "general_knowledge",
            "tool_result": res_direct,
            "mode": "deterministic_demo"
        }

    # ── 1. Complete task ──────────────────────────────────────────────────────────
    complete_match = re.search(r"^(?:complete|finish|mark done|done)\s+(?:task|assignment)?\s*(.+)$", text)
    if complete_match:
        target = complete_match.group(1).strip()
        args = {"task_id": int(target)} if target.isdigit() else {"task_title": target}
        out = execute_tool("complete_task", student_id, args)
        if out["success"]:
            res = out["result"]
            if isinstance(res, dict) and res.get("ambiguity"):
                speech = "Multiple tasks matched: " + ", ".join([f"#{c['id']} ({c['title']})" for c in res["candidates"]]) + ". Please specify by task ID."
                return {"speech": speech, "card": {"title": "Multiple Tasks Found", "content": speech},
                        "action_executed": "complete_task", "tool_result": res, "mode": "deterministic_demo"}
            speech = f"Task '{res['title']}' has been marked as completed."
            return {"speech": speech, "card": {"title": "Task Completed", "content": speech},
                    "action_executed": "complete_task", "tool_result": res, "mode": "deterministic_demo"}
        else:
            msg = out["error"]["message"]
            return {"speech": f"Could not complete task: {msg}", "card": {"title": "Task Notice", "content": msg}, "mode": "deterministic_demo"}

    # ── 2. Add task ───────────────────────────────────────────────────────────────
    add_match = re.search(r"^(?:add task|create task|new assignment|add assignment|remind me to)\s+(.+)$", text)
    if add_match:
        content = add_match.group(1).strip()
        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|tomorrow|today)\b", content)
        due_date = None
        if date_match:
            d_str = date_match.group(1)
            today = datetime.date.today()
            due_date = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d") if d_str == "tomorrow" else \
                       today.strftime("%Y-%m-%d") if d_str == "today" else d_str
        title = re.sub(r"\b(due|on|by)?\s*(\d{4}-\d{2}-\d{2}|tomorrow|today)\b", "", content, flags=re.IGNORECASE).strip()
        if not title:
            title = content
        if not due_date:
            return {"speech": f"What is the due date for '{title}'? Please say tomorrow, today, or a date.",
                    "card": {"title": "Due Date Needed", "content": f"Specify a due date for '{title}'."},
                    "needs_input": "due_date", "action_executed": "add_task", "mode": "deterministic_demo"}
        out = execute_tool("add_task", student_id, {"title": title, "due_date": due_date})
        if out["success"]:
            res = out["result"]
            speech = f"I've added the task '{title}' due on {res['due_date']}."
            return {"speech": speech, "card": {"title": "Task Added", "content": speech},
                    "action_executed": "add_task", "tool_result": res, "mode": "deterministic_demo"}
        else:
            msg = out["error"]["message"]
            return {"speech": f"Sorry, could not save task: {msg}", "card": {"title": "Validation Error", "content": msg}, "mode": "deterministic_demo"}

    # ── 3. Delete task ────────────────────────────────────────────────────────────
    delete_match = re.search(r"^(?:delete|remove)\s+(?:task|assignment)\s*(.+)$", text)
    if delete_match:
        target = delete_match.group(1).strip()
        confirm_match = re.search(r"(?:confirm|token)\s+([a-f0-9]{32})", text)
        confirm_token = confirm_match.group(1) if confirm_match else None
        args = {"confirm_token": confirm_token} if confirm_token else ({"task_id": int(target)} if target.isdigit() else {"task_title": target})
        out = execute_tool("delete_task", student_id, args)
        if out["success"]:
            res = out["result"]
            if isinstance(res, dict) and res.get("pending_confirmation"):
                speech = f"{res['message']} Say 'confirm token {res['confirm_token']}' to proceed."
                return {"speech": speech, "card": {"title": "Confirmation Required", "content": speech},
                        "action_executed": "delete_task", "tool_result": res, "mode": "deterministic_demo"}
            if isinstance(res, dict) and res.get("ambiguity"):
                speech = "Multiple tasks match: " + ", ".join([f"#{c['id']} ({c['title']})" for c in res["candidates"]]) + ". Specify by task ID."
                return {"speech": speech, "card": {"title": "Multiple Tasks Found", "content": speech}, "mode": "deterministic_demo"}
            speech = res.get("message", "Task deleted.")
            return {"speech": speech, "card": {"title": "Delete Task", "content": speech},
                    "action_executed": "delete_task", "tool_result": res, "mode": "deterministic_demo"}
        else:
            msg = out["error"]["message"]
            return {"speech": f"Could not delete task: {msg}", "card": {"title": "Error", "content": msg}, "mode": "deterministic_demo"}

    # ── 4. List tasks ─────────────────────────────────────────────────────────────
    if any(k in text for k in ["task", "assignment", "todo", "homework"]) and any(k in text for k in ["show", "list", "what", "pending", "view"]):
        out = execute_tool("list_tasks", student_id, {"status": "Pending"})
        tasks = out.get("result", []) if out["success"] else []
        if not tasks:
            speech = "You have no pending tasks right now. Great job staying ahead!"
        else:
            items_str = ", ".join([f"{t['title']} (due {t['due_date']})" for t in tasks[:4]])
            speech = f"You have {len(tasks)} pending tasks: {items_str}."
        return {"speech": speech, "card": {"title": "Pending Tasks", "content": speech},
                "action_executed": "list_tasks", "tool_result": tasks, "mode": "deterministic_demo"}

    # ── 5. Check attendance ───────────────────────────────────────────────────────
    if "attendance" in text or "miss class" in text:
        out = execute_tool("get_attendance_summary", student_id, {})
        att = out.get("result", []) if out["success"] else []
        low = [a for a in att if a["percentage"] < 75]
        if low:
            speech = f"Warning: Your attendance in {low[0]['name']} is {low[0]['percentage']}%, below 75%. You need {low[0]['classes_needed_for_75']} more consecutive classes."
        else:
            avg = round(sum(a["percentage"] for a in att) / len(att), 1) if att else 100.0
            speech = f"Your attendance looks great! Overall average is {avg}%, all subjects above 75%."
        return {"speech": speech, "card": {"title": "Attendance Overview", "content": speech},
                "action_executed": "check_attendance", "tool_result": att, "mode": "deterministic_demo"}

    # ── 6. Today's class schedule ─────────────────────────────────────────────────
    if any(k in text for k in ["today", "schedule", "timetable", "class", "lecture"]) and \
       not any(k in text for k in ["schedule meeting", "plan", "study plan"]):
        out = execute_tool("get_today_summary", student_id, {})
        sched = out.get("result", {}) if out["success"] else {}
        classes = sched.get("classes", [])
        if classes:
            c_desc = ", ".join([f"{c['name']} at {c['start_time']} in {c['room']}" for c in classes])
            speech = f"Today ({sched.get('day', 'today')}) you have: {c_desc}."
        else:
            speech = f"You have no scheduled classes for today ({sched.get('day', 'today')})."
        return {"speech": speech, "card": {"title": "Today's Schedule", "content": speech},
                "action_executed": "get_today_schedule", "tool_result": sched, "mode": "deterministic_demo"}

    # ── 7. Open app / website ─────────────────────────────────────────────────────
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
        return {"speech": res["spoken_response"], "card": {"title": f"Opening {res['app']}", "content": res["spoken_response"]},
                "action_executed": "open_app_or_site", "tool_result": res, "mode": "deterministic_demo"}

    # ── 8. NEW: Meeting scheduling ────────────────────────────────────────────────
    meeting_triggers = ["schedule meeting", "book meeting", "set up meeting", "arrange meeting",
                        "plan meeting", "schedule a call", "book a call", "create a meeting",
                        "add meeting", "set meeting"]
    if any(k in text for k in meeting_triggers) or \
       (("meeting" in text or "call" in text) and any(k in text for k in ["schedule", "book", "set", "plan", "create", "add"])):
        parsed = parse_meeting_from_utterance(utterance)
        if parsed.get("needs"):
            # Store partial state and ask for first missing field
            set_state(student_id, "schedule_meeting", parsed)
            first_need = parsed["needs"][0]
            q = build_follow_up_question("schedule_meeting", first_need)
            return {"speech": q, "card": {"title": "Schedule Meeting", "content": q},
                    "needs_input": first_need, "action_executed": "schedule_meeting", "mode": "deterministic_demo"}
        else:
            try:
                mtg = svc_schedule_meeting(
                    student_id=student_id,
                    title=parsed["title"],
                    meeting_date=parsed["meeting_date"],
                    meeting_time=parsed.get("meeting_time", "10:00"),
                    participants=parsed.get("participants", "")
                )
                speech = (f"Meeting '{mtg['title']}' scheduled for {mtg['meeting_date']} "
                          f"at {mtg['meeting_time']}. I'll remind you before it starts.")
                return {"speech": speech, "card": {"title": "Meeting Scheduled", "content": speech},
                        "action_executed": "schedule_meeting", "tool_result": mtg, "mode": "deterministic_demo"}
            except Exception as e:
                speech = f"Couldn't schedule meeting: {str(e)}"
                return {"speech": speech, "card": {"title": "Meeting Error", "content": speech}, "mode": "deterministic_demo"}

    # ── 9. NEW: Show meetings / reminders ─────────────────────────────────────────
    if ("meeting" in text or "meetings" in text) and any(k in text for k in ["show", "list", "my", "upcoming", "today", "reminder", "remind"]):
        try:
            days = 1 if "today" in text else 7
            meetings = get_upcoming_meetings(student_id, days=days)
            reminders = check_due_reminders(student_id)
            if not meetings and not reminders:
                speech = "You have no upcoming meetings in the next week."
            else:
                parts = []
                for mtg in meetings[:3]:
                    parts.append(f"'{mtg['title']}' on {mtg['meeting_date']} at {mtg['meeting_time']}")
                speech = "Upcoming meetings: " + ", ".join(parts) + "." if parts else "No upcoming meetings."
                if reminders:
                    speech = reminders[0] + " " + speech
            return {"speech": speech, "card": {"title": "Your Meetings", "content": speech},
                    "action_executed": "list_meetings", "tool_result": meetings, "mode": "deterministic_demo"}
        except Exception:
            speech = "You have no meetings scheduled. Say 'schedule meeting' to add one."
            return {"speech": speech, "card": {"title": "Meetings", "content": speech}, "mode": "deterministic_demo"}

    # ── 10. NEW: Exam study plan ──────────────────────────────────────────────────
    exam_plan_triggers = ["study plan", "exam plan", "exam schedule", "exam strategy",
                          "plan my exam", "help me study", "study schedule", "prepare for exam",
                          "revision plan", "exam preparation"]
    if any(k in text for k in exam_plan_triggers):
        # Try to extract subjects from the utterance
        subjects = []
        subj_match = re.search(r"(?:for|in|subjects?:?)\s+([a-zA-Z\s,;and]+?)(?:\s+in\s+|\s+with\s+|\s+over\s+|$)", utterance, re.IGNORECASE)
        if subj_match:
            raw_subjs = subj_match.group(1)
            subjects = [s.strip() for s in re.split(r"[,;]|\band\b", raw_subjs) if s.strip() and len(s.strip()) > 1]

        days_match = re.search(r"(\d+)\s*days?", text)
        days = int(days_match.group(1)) if days_match else None

        hours_match = re.search(r"(\d+(?:\.\d+)?)\s*hours?", text)
        daily_hours = float(hours_match.group(1)) if hours_match else None

        if not subjects:
            set_state(student_id, "exam_plan", {"needs": ["subjects", "days", "daily_hours"]})
            return {"speech": "Which subjects do you want to study? Please list them, e.g. Math, Physics, Chemistry.",
                    "card": {"title": "Exam Plan", "content": "Please list your subjects."}, "needs_input": "subjects",
                    "action_executed": "exam_plan", "mode": "deterministic_demo"}
        if not days:
            set_state(student_id, "exam_plan", {"subjects": ", ".join(subjects), "needs": ["days", "daily_hours"]})
            return {"speech": f"Got it — {', '.join(subjects)}. How many days until your exam?",
                    "card": {"title": "Exam Plan", "content": "How many days?"}, "needs_input": "days",
                    "action_executed": "exam_plan", "mode": "deterministic_demo"}

        plan = generate_exam_strategy(subjects, days, daily_hours or 4.0)
        speech = plan.get("spoken", "Your study plan is ready.")
        return {"speech": speech, "card": {"title": "Exam Study Plan", "content": plan.get("summary", speech)},
                "action_executed": "exam_plan", "tool_result": plan, "mode": "deterministic_demo"}

    # ── 11. NEW: Project strategy ─────────────────────────────────────────────────
    project_triggers = ["project plan", "project strategy", "how to build", "how to create",
                        "build a", "create a", "develop a", "project roadmap", "project milestone",
                        "plan a project", "project schedule"]
    if any(k in text for k in project_triggers) and any(k in text for k in ["project", "app", "website", "system", "software", "build", "create", "develop"]):
        # Extract project name and type
        name_match = re.search(r"(?:for|a|an|build|create|develop)\s+([a-zA-Z\s\-]+?)(?:\s+app|\s+website|\s+project|\s+system|$)", utterance, re.IGNORECASE)
        project_name = name_match.group(1).strip().title() if name_match else "My Project"

        ptype = "app"
        if "website" in text or "web" in text:
            ptype = "website"
        elif "machine learning" in text or " ml " in text or "ai model" in text:
            ptype = "ml"

        days_match = re.search(r"(\d+)\s*days?", text)
        days = int(days_match.group(1)) if days_match else 30

        team_match = re.search(r"(\d+)\s*(?:people|person|member|team)", text)
        team_size = int(team_match.group(1)) if team_match else 1

        proj = generate_project_strategy(project_name, ptype, days, team_size)
        speech = proj.get("spoken", "Your project plan is ready.")
        return {"speech": speech, "card": {"title": f"Project Plan: {project_name}", "content": speech},
                "action_executed": "project_plan", "tool_result": proj, "mode": "deterministic_demo"}

    # ── 12. NEW: Idea suggestions / brainstorming ─────────────────────────────────
    idea_triggers = ["give me ideas", "suggest ideas", "ideas for", "brainstorm", "how can i improve",
                     "suggestions for", "tips for", "advice on", "what should i do", "help me with ideas",
                     "recommend", "best way to"]
    if any(k in text for k in idea_triggers):
        topic = re.sub(r"(give me ideas|suggest ideas|ideas for|brainstorm|how can i improve|suggestions for|tips for|advice on|what should i do|help me with ideas|recommend|best way to)\s*", "", text).strip()
        if not topic:
            topic = utterance
        result_idea = generate_idea_suggestions(topic, utterance)
        speech = result_idea.get("spoken", "Here are some suggestions.")
        return {"speech": speech, "card": {"title": f"Ideas: {topic.title()}", "content": "\n".join(result_idea.get("suggestions", []))},
                "action_executed": "idea_suggestions", "tool_result": result_idea, "mode": "deterministic_demo"}

    # ── 13. NEW: Discussion & open problem solving ─────────────────────────────────
    if is_strategy_query(utterance) and not is_knowledge_question(utterance):
        result_disc = discuss_and_plan(utterance)
        speech = result_disc.get("spoken", "Let me help you think through this.")
        content = "\n".join(result_disc.get("framework", result_disc.get("suggestions", [speech])))
        return {"speech": speech, "card": {"title": "Strategy & Planning", "content": content},
                "action_executed": "strategy_advisor", "tool_result": result_disc, "mode": "deterministic_demo"}

    # ── 14. NEW: Universal multi-domain Q&A ───────────────────────────────────────
    if is_knowledge_question(utterance):
        qa_result = answer_question(utterance)
        if qa_result.get("answer"):
            answer = qa_result["answer"]
            return {"speech": answer, "card": {"title": utterance[:60], "content": answer},
                    "action_executed": "universal_qa", "tool_result": qa_result, "mode": "deterministic_demo"}

    # ── 15. Cricket & web search ──────────────────────────────────────────────────
    if any(k in text for k in ["cricket", "match today", "live score", "search for", "google search", "search web"]):
        q = re.sub(r"^(?:search for|search|google search|look up)\s+", "", utterance, flags=re.IGNORECASE).strip()
        res = search_web_instant(q or utterance)
        return {"speech": res["spoken_summary"], "card": {"title": f"Search: {res['query']}", "content": res["spoken_summary"]},
                "action_executed": "search_web_instant", "tool_result": res, "mode": "deterministic_demo"}

    # ── 16. Trip planning ─────────────────────────────────────────────────────────
    if any(k in text for k in ["plan a trip", "plan trip", "travel to", "vacation", "trip to"]):
        from backend.services.assistant_service import plan_trip
        dest_match = re.search(r"(?:to|visit|in)\s+([a-zA-Z\s]+?)(?:\s+for|\s+\d+|\s+days|\.?$)", utterance, re.IGNORECASE)
        dest = dest_match.group(1).strip() if dest_match else "Goa"
        res = plan_trip(destination=dest, days=3)
        return {"speech": res["spoken_response"], "card": {"title": f"Trip Plan: {dest}", "content": res["spoken_response"]},
                "action_executed": "plan_trip", "tool_result": res, "mode": "deterministic_demo"}

    # ── 17. Campus FAQ ────────────────────────────────────────────────────────────
    if any(k in text for k in ["curfew", "hostel", "warden", "campus rule", "mess fee", "library timing", "block c", "block d"]):
        out_faq = execute_tool("search_faq", student_id, {"query": utterance})
        faq_results = out_faq.get("result", []) if out_faq["success"] else []
        if faq_results:
            best = faq_results[0]
            return {"speech": best["answer"], "card": {"title": best["question"], "content": best["answer"]},
                    "action_executed": "search_faq", "tool_result": faq_results, "mode": "deterministic_demo"}

    # ── 18. Final universal Q&A fallback (any remaining question) ─────────────────
    res_web = search_web_instant(utterance)
    if res_web and res_web.get("spoken_summary"):
        return {"speech": res_web["spoken_summary"],
                "card": {"title": utterance[:60], "content": res_web["spoken_summary"]},
                "action_executed": "search_web_instant", "tool_result": res_web, "mode": "deterministic_demo"}

    # Try universal QA one more time without web restriction
    qa_result = answer_question(utterance, allow_web=True)
    if qa_result.get("answer"):
        return {"speech": qa_result["answer"], "card": {"title": utterance[:60], "content": qa_result["answer"]},
                "action_executed": "universal_qa", "tool_result": qa_result, "mode": "deterministic_demo"}

    # ── Default clarification ─────────────────────────────────────────────────────
    speech = ("I can help with questions, schedules, meetings, study plans, project strategies, and more. "
              "Could you please rephrase your request?")
    return {"speech": speech, "card": {"title": "Alexa Assistant", "content": speech},
            "action_executed": "clarify", "mode": "deterministic_demo"}



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

    # If LLM_PROVIDER is configured as 'bedrock', invoke Amazon Bedrock Converse API with strict precision
    from backend.config import Config
    if getattr(Config, 'LLM_PROVIDER', 'demo') == 'bedrock':
        try:
            from backend.llm.agent_loop import AgentLoop
            loop = AgentLoop(student_id=student_id)
            loop_res = loop.run_turn(utterance)
            if loop_res and loop_res.get("speech"):
                speech = loop_res["speech"]
                return jsonify({
                    "speech": speech,
                    "spoken_response": speech,
                    "card": {"title": "Alexa+ Assistant", "content": speech},
                    "action_executed": "bedrock_converse",
                    "tool_result": loop_res.get("tool_calls_executed", []),
                    "data": {"provider": "Amazon Bedrock (Claude 3 Haiku)"},
                    "mode": "bedrock"
                }), 200
        except Exception:
            # Seamless fallback to offline dynamic extractor
            pass

    result = run_deterministic_engine(student_id, utterance)
    # Ensure spoken_response and data fields match frontend expectations
    result["spoken_response"] = result.get("speech", "")
    result["data"] = result.get("tool_result", {})
    return jsonify(result), 200

