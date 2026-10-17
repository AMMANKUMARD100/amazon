"""VoiceAgent Orchestrator for CampusMate AI.

Handles multi-step voice requests by chaining existing services
into single coherent spoken responses. No LLM required — uses
deterministic keyword/intent matching.
"""

import os
import re
import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.services.task_service import list_tasks
from backend.services.attendance_service import calculate_attendance
from backend.services.schedule_service import get_today_reminder, get_timetable
from backend.services.dashboard_service import get_dashboard_summary
from backend.services.planner_service import generate_study_plan
from backend.services.faq_service import search_faq
from backend.services.exam_service import list_exams
from backend.services.proactive_service import (
    check_attendance_risk,
    check_deadline_conflicts,
    generate_weekly_summary,
    get_proactive_alerts
)


class VoiceAgent:
    """Orchestrates multi-step voice requests by chaining existing services."""

    # Intent patterns: (regex_pattern, intent_name, priority)
    INTENT_PATTERNS: List[Tuple[str, str, int]] = [
        (r"\b(open youtube|open google|open spotify|open app|open website|open calculator|open browser|launch|open chrome)\b", "open_app", 15),
        (r"\b(cricket|match today|live score|score of|search for|google search|search web|search the internet|look up|who won)\b", "web_search", 14),
        (r"\b(plan a trip|plan trip|travel to|vacation|visit goa|trip to|tour plan|itinerary)\b", "plan_trip", 13),
        (r"\b(schedule meeting|schedule a meeting|book meeting|set meeting|remind me today|meeting reminder|my meetings|upcoming meetings|do i have any meeting)\b", "meeting", 12),
        (r"\b(plan my evening|plan my day|plan tonight)\b", "plan_day", 10),
        (r"\b(how am i doing|how('?s| is) my progress|my status|academic status)\b", "status_check", 9),
        (r"\b(am i at risk|risk|danger|warning)\b", "risk_check", 8),
        (r"\b(what should i study|study suggestion|what to study)\b", "study_suggestion", 7),
        (r"\b(full briefing|complete briefing|morning briefing|daily briefing|good morning|what'?s up)\b", "daily_briefing", 6),
        (r"\b(weekly summary|week summary|this week|weekly report)\b", "weekly_summary", 5),
        (r"\b(alert|notification|proactive)\b", "alerts", 4),
        (r"\b(attendance)\b", "attendance", 3),
        (r"\b(assignment|task|homework|pending)\b", "tasks", 2),
        (r"\b(schedule|timetable|class|lecture)\b", "schedule", 1),
        (r"\b(exam|midterm|final)\b", "exams", 1),
        (r"\b(study plan|study schedule)\b", "study_plan", 1),
        (r"\b(dashboard|overview)\b", "dashboard", 1),
        (r"\b(cgpa|gpa|grade)\b", "cgpa", 1),
        (r"\b(faq|question|policy|hostel|library|rule)\b", "faq", 0),
    ]

    def handle_request(self, student_id: int, utterance: str) -> Dict[str, Any]:
        """Process a voice utterance and return a structured response.

        Args:
            student_id: Authenticated student ID.
            utterance: Raw voice input text.

        Returns:
            Dict with:
                spoken_response: Natural language response for TTS
                tool_calls: List of {tool, args, result} for each service called
                data: Structured data for UI display
                intent: Matched intent name
        """
        if not utterance or not utterance.strip():
            return {
                "spoken_response": "I didn't catch that. Could you repeat your question?",
                "tool_calls": [],
                "data": {},
                "intent": "unknown"
            }

        intent = self._match_intent(utterance.lower().strip())

        handlers = {
            "open_app": self._handle_open_app,
            "web_search": self._handle_web_search,
            "plan_trip": self._handle_plan_trip,
            "meeting": self._handle_meeting,
            "plan_day": self._handle_plan_day,
            "status_check": self._handle_status_check,
            "risk_check": self._handle_risk_check,
            "study_suggestion": self._handle_study_suggestion,
            "daily_briefing": self._handle_daily_briefing,
            "weekly_summary": self._handle_weekly_summary,
            "alerts": self._handle_alerts,
            "attendance": self._handle_attendance,
            "tasks": self._handle_tasks,
            "schedule": self._handle_schedule,
            "exams": self._handle_exams,
            "study_plan": self._handle_study_plan,
            "dashboard": self._handle_dashboard,
            "cgpa": self._handle_cgpa,
            "faq": self._handle_faq,
        }

        handler = handlers.get(intent)
        if handler:
            try:
                result = handler(student_id, utterance)
                result["intent"] = intent
                return result
            except Exception as e:
                return {
                    "spoken_response": f"I encountered an error processing your request: {str(e)}",
                    "tool_calls": [],
                    "data": {"error": str(e)},
                    "intent": intent
                }

        # Dynamic fallback for general requests: check if it's an app opening, search, or query
        clean_utt = utterance.lower().strip()
        if any(w in clean_utt for w in ["open ", "launch ", "go to "]):
            return self._handle_open_app(student_id, utterance)
        if any(w in clean_utt for w in ["search ", "who is ", "what is ", "where is ", "when is ", "cricket ", "match "]):
            return self._handle_web_search(student_id, utterance)

        return {
            "spoken_response": "I'm your Alexa+ personal assistant. You can ask me to schedule meetings, remind you today, open YouTube or Google, search live cricket scores, or plan a trip!",
            "tool_calls": [],
            "data": {},
            "intent": "unknown"
        }

    def _match_intent(self, text: str) -> str:
        """Match utterance to an intent using regex patterns."""
        best_match = ("unknown", -1)
        for pattern, intent, priority in self.INTENT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                if priority > best_match[1]:
                    best_match = (intent, priority)
        return best_match[0]

    def _invoke_tool(self, tool_name: str, student_id: int, args: Dict[str, Any], direct_fn) -> Any:
        """Invokes a tool directly or optionally via MCP client if USE_MCP_CLIENT is set."""
        use_mcp = os.environ.get("USE_MCP_CLIENT", "").lower() in ("true", "1", "yes")
        if use_mcp:
            try:
                from backend.mcp_client import mcp_client
                mcp_args = dict(args)
                mcp_args["student_id"] = student_id
                return mcp_client.call_tool(tool_name, mcp_args)
            except Exception:
                # Graceful fallback to direct service function
                return direct_fn()
        return direct_fn()

    def _handle_plan_day(self, student_id: int, utterance: str) -> Dict[str, Any]:
        """Multi-step: today's schedule + pending tasks + study plan."""
        tool_calls = []

        # Step 1: Today's reminder
        today_data = self._invoke_tool("get_today_reminder", student_id, {}, lambda: get_today_reminder(student_id))
        tool_calls.append({"tool": "get_today_reminder", "args": {}, "result": today_data})

        # Step 2: Pending tasks
        pending = self._invoke_tool("list_tasks", student_id, {"status": "Pending"}, lambda: list_tasks(student_id, status="Pending"))
        tool_calls.append({"tool": "list_tasks", "args": {"status": "Pending"}, "result": pending})

        # Step 3: Study plan
        study_data = self._invoke_tool("generate_study_plan", student_id, {}, lambda: generate_study_plan(student_id, {}))
        tool_calls.append({"tool": "generate_study_plan", "args": {}, "result": study_data})


        # Build spoken response
        parts = []
        classes = today_data.get("classes", [])
        if classes:
            remaining = [c for c in classes if c.get("end_time", "23:59") > datetime.datetime.now().strftime("%H:%M")]
            if remaining:
                parts.append(f"You have {len(remaining)} classes remaining today.")
            else:
                parts.append("All your classes for today are done.")
        else:
            parts.append("No classes scheduled today.")

        if pending:
            high_pri = [t for t in pending if t.get("priority") == "High"]
            parts.append(f"You have {len(pending)} pending tasks" +
                        (f", {len(high_pri)} are high priority." if high_pri else "."))
        else:
            parts.append("You're all caught up on tasks.")

        sessions = study_data.get("sessions", study_data.get("slots", []))
        if sessions:
            parts.append(f"I've prepared a study plan with {len(sessions)} sessions for you.")
        else:
            parts.append("No study sessions to schedule right now.")

        return {
            "spoken_response": " ".join(parts),
            "tool_calls": tool_calls,
            "data": {
                "today": today_data,
                "pending_tasks": pending,
                "study_plan": study_data
            }
        }

    def _handle_status_check(self, student_id: int, utterance: str) -> Dict[str, Any]:
        """Multi-step: dashboard + attendance overview."""
        tool_calls = []

        dashboard = get_dashboard_summary(student_id)
        tool_calls.append({"tool": "get_dashboard_summary", "args": {}, "result": dashboard})

        att_stats = calculate_attendance(student_id)
        tool_calls.append({"tool": "calculate_attendance", "args": {}, "result": att_stats})

        name = dashboard.get("student_name", "there")
        cgpa = dashboard.get("cgpa", 0.0)
        pending = dashboard.get("pending_assignments", 0)
        att_pct = dashboard.get("overall_attendance", 100.0)
        study_hrs = dashboard.get("scheduled_study_hours", 0)

        low_subjects = [s for s in att_stats if s.get("percentage", 100) < 75]

        spoken = (
            f"Here's your status, {name}. "
            f"Your CGPA is {cgpa}. "
            f"You have {pending} pending assignments and your overall attendance is {att_pct}%. "
            f"You have {study_hrs} hours of study scheduled."
        )
        if low_subjects:
            codes = ", ".join(s.get("code", "?") for s in low_subjects)
            spoken += f" Watch out: {codes} {'is' if len(low_subjects) == 1 else 'are'} below 75% attendance."

        return {
            "spoken_response": spoken,
            "tool_calls": tool_calls,
            "data": {"dashboard": dashboard, "attendance": att_stats}
        }

    def _handle_risk_check(self, student_id: int, utterance: str) -> Dict[str, Any]:
        """Check attendance risk + overdue tasks."""
        tool_calls = []

        att_risks = check_attendance_risk(student_id)
        tool_calls.append({"tool": "check_attendance_risk", "args": {}, "result": att_risks})

        deadline_issues = check_deadline_conflicts(student_id)
        tool_calls.append({"tool": "check_deadline_conflicts", "args": {}, "result": deadline_issues})

        parts = []
        if att_risks:
            parts.append(f"You have {len(att_risks)} attendance risk{'s' if len(att_risks) != 1 else ''}.")
            for r in att_risks[:3]:
                parts.append(r["message"])
        else:
            parts.append("Your attendance is healthy across all subjects.")

        if deadline_issues:
            overdue = [d for d in deadline_issues if d["conflict_type"] == "overdue"]
            urgent = [d for d in deadline_issues if d["conflict_type"] == "urgent_deadline"]
            conflicts = [d for d in deadline_issues if d["conflict_type"] == "exam_overlap"]

            if overdue:
                parts.append(f"{len(overdue)} assignment{'s are' if len(overdue) != 1 else ' is'} overdue.")
            if urgent:
                parts.append(f"{len(urgent)} assignment{'s are' if len(urgent) != 1 else ' is'} due within 48 hours.")
            if conflicts:
                parts.append(f"{len(conflicts)} deadline{'s conflict' if len(conflicts) != 1 else ' conflicts'} with exams.")
        else:
            parts.append("No deadline conflicts detected.")

        return {
            "spoken_response": " ".join(parts),
            "tool_calls": tool_calls,
            "data": {"attendance_risks": att_risks, "deadline_conflicts": deadline_issues}
        }

    def _handle_study_suggestion(self, student_id: int, utterance: str) -> Dict[str, Any]:
        """Suggest what to study based on exams + study plan."""
        tool_calls = []

        exams = list_exams(student_id)
        tool_calls.append({"tool": "list_exams", "args": {}, "result": exams})

        study_data = generate_study_plan(student_id, {})
        tool_calls.append({"tool": "generate_study_plan", "args": {}, "result": study_data})

        parts = []
        today = datetime.date.today()
        upcoming = []
        for ex in exams:
            try:
                ed = datetime.date.fromisoformat(ex.get("exam_date", ""))
                if ed >= today:
                    upcoming.append((ex, (ed - today).days))
            except ValueError:
                pass

        upcoming.sort(key=lambda x: x[1])

        if upcoming:
            nearest = upcoming[0]
            parts.append(f"Your nearest exam is '{nearest[0]['title']}' in {nearest[1]} days.")
            parts.append(f"I'd recommend focusing on that first.")
        else:
            parts.append("No upcoming exams found.")

        sessions = study_data.get("sessions", study_data.get("slots", []))
        if sessions:
            parts.append(f"I've generated {len(sessions)} study sessions to help you prepare.")

        return {
            "spoken_response": " ".join(parts),
            "tool_calls": tool_calls,
            "data": {"exams": exams, "study_plan": study_data}
        }

    def _handle_daily_briefing(self, student_id: int, utterance: str) -> Dict[str, Any]:
        """Full daily briefing combining multiple services."""
        tool_calls = []

        today_data = get_today_reminder(student_id)
        tool_calls.append({"tool": "get_today_reminder", "args": {}, "result": today_data})

        att_stats = calculate_attendance(student_id)
        tool_calls.append({"tool": "calculate_attendance", "args": {}, "result": att_stats})

        pending = list_tasks(student_id, status="Pending")
        tool_calls.append({"tool": "list_tasks", "args": {"status": "Pending"}, "result": pending})

        day = today_data.get("day", "Today")
        date_str = today_data.get("date", "")
        parts = [f"Good day! Here's your briefing for {day}, {date_str}."]

        classes = today_data.get("classes", [])
        if classes:
            parts.append(f"You have {len(classes)} classes today.")
        else:
            parts.append("No classes today.")

        due = today_data.get("assignments_due", [])
        if due:
            parts.append(f"{len(due)} assignments due soon.")

        low = [a for a in att_stats if a.get("percentage", 100) < 75]
        if low:
            codes = ", ".join(a.get("code", "") for a in low)
            parts.append(f"Attendance warning for {codes}.")
        else:
            parts.append("Attendance is good across all subjects.")

        parts.append(f"You have {len(pending)} pending tasks.")

        return {
            "spoken_response": " ".join(parts),
            "tool_calls": tool_calls,
            "data": {
                "today": today_data,
                "attendance": att_stats,
                "pending_tasks": pending
            }
        }

    def _handle_weekly_summary(self, student_id: int, utterance: str) -> Dict[str, Any]:
        summary = generate_weekly_summary(student_id)
        return {
            "spoken_response": summary.get("summary_text", "Weekly summary generated."),
            "tool_calls": [{"tool": "generate_weekly_summary", "args": {}, "result": summary}],
            "data": summary
        }

    def _handle_alerts(self, student_id: int, utterance: str) -> Dict[str, Any]:
        alerts = get_proactive_alerts(student_id)
        if alerts:
            top = alerts[:3]
            spoken = f"You have {len(alerts)} alerts. " + " ".join(a["message"] for a in top)
        else:
            spoken = "No alerts at this time. You're in good shape!"
        return {
            "spoken_response": spoken,
            "tool_calls": [{"tool": "get_proactive_alerts", "args": {}, "result": alerts}],
            "data": {"alerts": alerts}
        }

    def _handle_attendance(self, student_id: int, utterance: str) -> Dict[str, Any]:
        stats = calculate_attendance(student_id)
        if stats:
            summaries = []
            for s in stats:
                summaries.append(f"{s.get('code', '?')}: {s.get('percentage', 0)}%")
            spoken = "Here's your attendance. " + ", ".join(summaries) + "."
        else:
            spoken = "No attendance records found."
        return {
            "spoken_response": spoken,
            "tool_calls": [{"tool": "calculate_attendance", "args": {}, "result": stats}],
            "data": {"attendance": stats}
        }

    def _handle_tasks(self, student_id: int, utterance: str) -> Dict[str, Any]:
        tasks = list_tasks(student_id, status="Pending")
        if tasks:
            spoken = f"You have {len(tasks)} pending tasks. "
            for t in tasks[:3]:
                spoken += f"{t.get('title', 'Task')} due {t.get('due_date', 'unknown')}. "
            if len(tasks) > 3:
                spoken += f"And {len(tasks) - 3} more."
        else:
            spoken = "You have no pending tasks. Great job!"
        return {
            "spoken_response": spoken,
            "tool_calls": [{"tool": "list_tasks", "args": {"status": "Pending"}, "result": tasks}],
            "data": {"tasks": tasks}
        }

    def _handle_schedule(self, student_id: int, utterance: str) -> Dict[str, Any]:
        timetable = get_timetable(student_id)
        today = datetime.date.today().strftime("%A")
        today_classes = [c for c in timetable if c.get("day_of_week") == today]
        if today_classes:
            spoken = f"Today you have {len(today_classes)} classes. "
            for c in today_classes:
                spoken += f"{c.get('name', c.get('code', 'Class'))} at {c.get('start_time', '')} in room {c.get('room', 'TBD')}. "
        else:
            spoken = "No classes scheduled for today."
        return {
            "spoken_response": spoken,
            "tool_calls": [{"tool": "get_timetable", "args": {}, "result": timetable}],
            "data": {"timetable": timetable, "today_classes": today_classes}
        }

    def _handle_exams(self, student_id: int, utterance: str) -> Dict[str, Any]:
        exams = list_exams(student_id)
        if exams:
            spoken = f"You have {len(exams)} exams scheduled. "
            for ex in exams[:3]:
                spoken += f"{ex.get('title', 'Exam')} on {ex.get('exam_date', '')}. "
        else:
            spoken = "No exams scheduled."
        return {
            "spoken_response": spoken,
            "tool_calls": [{"tool": "list_exams", "args": {}, "result": exams}],
            "data": {"exams": exams}
        }

    def _handle_study_plan(self, student_id: int, utterance: str) -> Dict[str, Any]:
        plan = generate_study_plan(student_id, {})
        sessions = plan.get("sessions", plan.get("slots", []))
        if sessions:
            spoken = f"I've generated a study plan with {len(sessions)} sessions."
        else:
            spoken = "I've created a study plan for you."
        return {
            "spoken_response": spoken,
            "tool_calls": [{"tool": "generate_study_plan", "args": {}, "result": plan}],
            "data": {"study_plan": plan}
        }

    def _handle_dashboard(self, student_id: int, utterance: str) -> Dict[str, Any]:
        dashboard = get_dashboard_summary(student_id)
        name = dashboard.get("student_name", "Student")
        spoken = (
            f"Dashboard for {name}: "
            f"CGPA {dashboard.get('cgpa', 0)}, "
            f"{dashboard.get('pending_assignments', 0)} pending assignments, "
            f"{dashboard.get('overall_attendance', 0)}% attendance, "
            f"{dashboard.get('scheduled_study_hours', 0)} study hours scheduled."
        )
        return {
            "spoken_response": spoken,
            "tool_calls": [{"tool": "get_dashboard_summary", "args": {}, "result": dashboard}],
            "data": {"dashboard": dashboard}
        }

    def _handle_cgpa(self, student_id: int, utterance: str) -> Dict[str, Any]:
        from backend.database.connection import execute_query
        student = execute_query(
            "SELECT full_name, cgpa, current_semester FROM students WHERE id = ?;",
            (student_id,), fetch_one=True
        )
        if student:
            cgpa = student.get("cgpa", 0.0)
            spoken = f"Your current CGPA is {cgpa}."
        else:
            cgpa = 0.0
            spoken = "I couldn't find your CGPA records."
        return {
            "spoken_response": spoken,
            "tool_calls": [{"tool": "calculate_cgpa", "args": {}, "result": {"cgpa": cgpa}}],
            "data": {"cgpa": cgpa}
        }

    def _handle_faq(self, student_id: int, utterance: str) -> Dict[str, Any]:
        # Extract query from utterance
        query = utterance.strip()
        for prefix in ["faq ", "question about ", "tell me about ", "what is the ", "what are the "]:
            if query.lower().startswith(prefix):
                query = query[len(prefix):]
                break

        results = search_faq(query)
        if results:
            spoken = results[0].get("answer", "I found some information but couldn't format it.")
            if len(results) > 1:
                spoken += f" I also found {len(results) - 1} more related results."
        else:
            spoken = "I couldn't find information about that in our knowledge base."
        return {
            "spoken_response": spoken,
            "tool_calls": [{"tool": "search_faq", "args": {"query": query}, "result": results}],
            "data": {"faq_results": results}
        }

    # -------------------------------------------------------------
    # Personal Assistant Feature Handlers (Alexa+)
    # -------------------------------------------------------------

    def _handle_open_app(self, student_id: int, utterance: str) -> Dict[str, Any]:
        from backend.services.assistant_service import open_app_or_site
        text = utterance.lower().strip()
        # Extract target app
        target = "google"
        query = None

        if "youtube" in text:
            target = "youtube"
            m = re.search(r"(?:search|play|for)\s+(.+)$", text)
            if m:
                query = m.group(1).strip()
        elif "spotify" in text:
            target = "spotify"
        elif "google" in text:
            target = "google"
            m = re.search(r"(?:search|for)\s+(.+)$", text)
            if m:
                query = m.group(1).strip()
        elif "calculator" in text:
            target = "calculator"
        else:
            # Try to grab whatever follows "open"
            m = re.search(r"(?:open|launch|go to)\s+([a-zA-Z0-9\.\_\-]+)", text)
            if m:
                target = m.group(1).strip()

        res = open_app_or_site(target=target, query=query)
        return {
            "spoken_response": res.get("spoken_response", f"Opening {target} for you."),
            "tool_calls": [{"tool": "open_app_or_site", "args": {"target": target, "query": query}, "result": res}],
            "data": res
        }

    def _handle_web_search(self, student_id: int, utterance: str) -> Dict[str, Any]:
        from backend.services.assistant_service import search_web_instant
        text = utterance.strip()
        # Clean query prefixes
        query = re.sub(r"^(?:alexa\s+|please\s+)?(?:search for|search|google search|look up|what is|who is|where is|tell me about)\s+", "", text, flags=re.IGNORECASE).strip()
        if not query:
            query = text

        res = search_web_instant(query=query)
        return {
            "spoken_response": res.get("spoken_summary", f"Here are the search results for {query}."),
            "tool_calls": [{"tool": "search_web_instant", "args": {"query": query}, "result": res}],
            "data": res
        }

    def _handle_plan_trip(self, student_id: int, utterance: str) -> Dict[str, Any]:
        from backend.services.assistant_service import plan_trip
        text = utterance.strip()
        # Extract destination
        dest_match = re.search(r"(?:to|for|visit|in)\s+([a-zA-Z\s]+?)(?:\s+for|\s+\d+|\s+days|\s+trip|\.|$)", text, re.IGNORECASE)
        dest = dest_match.group(1).strip() if dest_match else "Goa"
        
        # Extract days
        days_match = re.search(r"(\d+)\s*(?:day|days)", text, re.IGNORECASE)
        days = int(days_match.group(1)) if days_match else 3

        res = plan_trip(destination=dest, days=days)
        return {
            "spoken_response": res.get("spoken_response", f"Here is your {days}-day plan for {dest}."),
            "tool_calls": [{"tool": "plan_trip", "args": {"destination": dest, "days": days}, "result": res}],
            "data": res
        }

    def _handle_meeting(self, student_id: int, utterance: str) -> Dict[str, Any]:
        from backend.services.assistant_service import schedule_meeting, list_meetings, get_today_meeting_reminder
        text = utterance.lower().strip()

        # Check if user is asking for meeting reminders or listing meetings
        if any(k in text for k in ["remind me today", "today's meeting", "what meeting", "do i have any meeting", "my meetings", "upcoming meetings"]):
            res = get_today_meeting_reminder(student_id)
            return {
                "spoken_response": res.get("spoken_reminder"),
                "tool_calls": [{"tool": "get_today_meeting_reminder", "args": {}, "result": res}],
                "data": res
            }

        # Otherwise: scheduling a meeting
        # Extract title
        title_match = re.search(r"(?:schedule|book|set)?\s*(?:a\s+)?meeting\s+(?:with|about|called|for)?\s*(.+?)(?:\s+(?:at|on|tomorrow|today|\d{1,2}:|\d{4}-)|$)", utterance, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "Discussion"
        if not title:
            title = "Project Sync"

        # Extract time
        time_match = re.search(r"(\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b)", utterance, re.IGNORECASE)
        meeting_time = time_match.group(1).upper() if time_match else "3:00 PM"

        # Extract date
        meeting_date = "today"
        if "tomorrow" in text:
            meeting_date = "tomorrow"
        else:
            date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", utterance)
            if date_match:
                meeting_date = date_match.group(1)

        res = schedule_meeting(student_id=student_id, title=title, date=meeting_date, time=meeting_time)
        return {
            "spoken_response": res.get("spoken_confirmation", f"Scheduled meeting '{title}' for {meeting_date} at {meeting_time}."),
            "tool_calls": [{"tool": "schedule_meeting", "args": {"title": title, "date": meeting_date, "time": meeting_time}, "result": res}],
            "data": res
        }



# Module-level singleton
voice_agent = VoiceAgent()


def handle_voice_request(student_id: int, utterance: str) -> Dict[str, Any]:
    """Convenience function wrapping VoiceAgent.handle_request."""
    return voice_agent.handle_request(student_id, utterance)
