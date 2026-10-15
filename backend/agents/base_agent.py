from backend.services.attendance_service import calculate_attendance, get_raw_attendance
from backend.services.task_service import list_tasks, add_task, update_task, delete_task
from backend.services.schedule_service import get_timetable, get_today_reminder
from backend.services.planner_service import generate_study_plan
from backend.services.dashboard_service import get_dashboard_summary
from backend.services.faq_service import search_faq
from backend.services.exceptions import ValidationError

class BaseAgent:
    """Base Agent class providing direct in-process access to domain services.
    Agents never make HTTP requests or test_client calls to their own server.
    """
    def __init__(self, student_id=None):
        self.student_id = student_id

    def call_mcp_tool(self, tool_name, method='POST', payload=None):
        """Dispatches tool calls directly to domain services in-process."""
        if payload is None:
            payload = {}

        student_id = payload.get("student_id") or self.student_id

        if tool_name == "calculateAttendance":
            if not student_id:
                raise ValidationError("student_id is required.")
            return calculate_attendance(student_id)

        elif tool_name == "getAttendance":
            if not student_id:
                raise ValidationError("student_id is required.")
            return get_raw_attendance(student_id)

        elif tool_name == "getAssignments":
            if not student_id:
                raise ValidationError("student_id is required.")
            return list_tasks(student_id)

        elif tool_name == "getTimetable":
            if not student_id:
                raise ValidationError("student_id is required.")
            return get_timetable(student_id)

        elif tool_name == "todayReminder":
            if not student_id:
                raise ValidationError("student_id is required.")
            return get_today_reminder(student_id)

        elif tool_name == "getDashboard":
            if not student_id:
                raise ValidationError("student_id is required.")
            return get_dashboard_summary(student_id)

        elif tool_name == "searchFAQ":
            query = payload.get("query", "")
            return search_faq(query)

        elif tool_name == "createStudyPlan":
            # Direct forward to service if needed
            return generate_study_plan(student_id, payload)

        raise ValidationError(f"Unknown MCP Tool: {tool_name}")
