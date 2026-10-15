"""FastMCP Model Context Protocol (MCP) Server for CampusMate AI.

Exposes academic tools for AI concierges, Alexa+ skills, and LLM agents
using the Model Context Protocol (MCP) over streamable-http and stdio transports.
"""

import os
import sys
import secrets
import logging
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.config import Config
from backend.database.connection import execute_query
from backend.tools import execute_tool, tool_registry
from backend.services import schedule_service, attendance_service, task_service, dashboard_service
from mcp.server.fastmcp import FastMCP

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("campusmate.mcp")


def validate_auth_token(token_or_header: Optional[str]) -> bool:
    """Validates authorization token against MCP_AUTH_TOKEN environment variable.

    Supports:
      - 'Bearer <token>'
      - '<token>'
    If MCP_AUTH_TOKEN is not set or empty:
      - If MCP_ALLOW_NO_AUTH=true, allow bypassing for local dev with a warning.
      - Otherwise, default to requiring a token (reject request).
    """
    expected = os.environ.get("MCP_AUTH_TOKEN", "").strip()
    if not expected:
        allow_no_auth = os.environ.get("MCP_ALLOW_NO_AUTH", "").lower() in ("true", "1", "yes")
        if allow_no_auth:
            return True
        return False

    if not token_or_header:
        return False
    header_val = str(token_or_header).strip()
    if header_val.lower().startswith("bearer "):
        token = header_val[7:].strip()
    else:
        token = header_val
    return secrets.compare_digest(token, expected)


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces Bearer token authentication on the MCP HTTP endpoint."""

    async def dispatch(self, request: Request, call_next):
        # Allow preflight CORS OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Enforce on MCP endpoint routes
        if request.url.path.startswith("/mcp"):
            auth_header = request.headers.get("Authorization")
            if not validate_auth_token(auth_header):
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32001,
                            "message": "Unauthorized: Missing, invalid, or mismatched MCP Bearer token."
                        },
                        "id": None
                    },
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"}
                )

        return await call_next(request)


class CampusMateFastMCP(FastMCP):
    """Extended FastMCP application with streamable-http transport and auth middleware support."""

    def streamable_http_app(self):
        """Constructs and returns the underlying Starlette app equipped with auth middleware."""
        app = super().streamable_http_app()
        # Insert auth middleware if not already attached
        has_auth = any(
            getattr(m, "cls", None) == MCPAuthMiddleware or isinstance(m, MCPAuthMiddleware)
            for m in getattr(app, "user_middleware", [])
        )
        if not has_auth:
            app.add_middleware(MCPAuthMiddleware)
        return app

    async def run_streamable_http_async(self) -> None:
        """Run the server using StreamableHTTP transport with auth middleware wired in."""
        import uvicorn

        starlette_app = self.streamable_http_app()

        # Audit auth configuration on startup
        expected = os.environ.get("MCP_AUTH_TOKEN", "").strip()
        allow_no_auth = os.environ.get("MCP_ALLOW_NO_AUTH", "").lower() in ("true", "1", "yes")
        if not expected:
            if allow_no_auth:
                print("WARNING: MCP_AUTH_TOKEN is not set! Running in insecure mode because MCP_ALLOW_NO_AUTH=true.")
            else:
                print("WARNING: MCP_AUTH_TOKEN is not set. All incoming requests will be rejected with 401 unless MCP_AUTH_TOKEN is configured or MCP_ALLOW_NO_AUTH=true is set.")
        else:
            print("INFO: MCP Bearer token authentication active.")

        bound_student = os.environ.get("MCP_STUDENT_ID", "").strip()
        if bound_student:
            print(f"INFO: MCP tool execution strictly bound to student_id={bound_student}.")

        config = uvicorn.Config(
            starlette_app,
            host=self.settings.host,
            port=self.settings.port,
            log_level=self.settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        await server.serve()

    def run(self, transport: str = "streamable-http", **kwargs):
        """Runs the MCP server over requested transport (default: streamable-http)."""
        host = kwargs.get("host", "0.0.0.0")
        port = int(kwargs.get("port", os.environ.get("MCP_PORT", 8080)))

        # Update server settings if present
        if hasattr(self, "settings") and self.settings is not None:
            if hasattr(self.settings, "host"):
                self.settings.host = host
            if hasattr(self.settings, "port"):
                self.settings.port = port

        if transport == "streamable-http":
            import anyio
            return anyio.run(self.run_streamable_http_async)
        return super().run(transport=transport, **kwargs)


# Initialize FastMCP app instance
try:
    mcp_app = CampusMateFastMCP("CampusMate AI", host="0.0.0.0", port=int(os.environ.get("MCP_PORT", 8080)))
except TypeError:
    mcp_app = CampusMateFastMCP("CampusMate AI")


# -------------------------------------------------------------
# Helper validation
# -------------------------------------------------------------

def _validate_student_id(student_id: Any) -> int:
    """Ensures student_id is a valid integer and verifies bound MCP_STUDENT_ID if set."""
    if student_id is None:
        raise ValueError("A valid student_id is required.")
    if isinstance(student_id, str) and student_id.isdigit():
        sid = int(student_id)
    elif isinstance(student_id, int):
        sid = student_id
    else:
        raise ValueError("A valid integer student_id is required.")

    # Bound student check: stop trusting caller student_id blindly
    bound_id = os.environ.get("MCP_STUDENT_ID", "").strip()
    if bound_id:
        try:
            expected_sid = int(bound_id)
            if sid != expected_sid:
                raise PermissionError(
                    f"Access Denied: Tool invocation student_id ({sid}) does not match authenticated student ({expected_sid})."
                )
        except ValueError:
            pass

    return sid



# -------------------------------------------------------------
# 13 Wrapped Tool Registry Tools
# -------------------------------------------------------------

@mcp_app.tool()
def list_tasks(student_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List student assignments and tasks. Optionally filter by status ('Pending' or 'Completed')."""
    sid = _validate_student_id(student_id)
    args: Dict[str, Any] = {}
    if status is not None:
        args["status"] = status
    out = execute_tool("list_tasks", sid, args)
    if not out.get("success"):
        raise ValueError(out.get("error", {}).get("message", "Failed to list tasks"))
    return out["result"]


@mcp_app.tool()
def add_task(
    student_id: int,
    title: str,
    due_date: str,
    priority: str = "Medium",
    description: str = "",
    subject_code: Optional[str] = None
) -> Dict[str, Any]:
    """Add a new assignment or homework task with a validated YYYY-MM-DD due date."""
    sid = _validate_student_id(student_id)
    args: Dict[str, Any] = {
        "title": title,
        "due_date": due_date,
        "priority": priority,
        "description": description
    }
    if subject_code is not None:
        args["subject_code"] = subject_code
    out = execute_tool("add_task", sid, args)
    if not out.get("success"):
        raise ValueError(out.get("error", {}).get("message", "Failed to add task"))
    return out["result"]


@mcp_app.tool()
def update_task(
    student_id: int,
    task_id: Optional[int] = None,
    task_title: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """Update an existing task's title, description, due date, priority, or status."""
    sid = _validate_student_id(student_id)
    args: Dict[str, Any] = {}
    if task_id is not None:
        args["task_id"] = task_id
    if task_title is not None:
        args["task_title"] = task_title
    if title is not None:
        args["title"] = title
    if description is not None:
        args["description"] = description
    if due_date is not None:
        args["due_date"] = due_date
    if priority is not None:
        args["priority"] = priority
    if status is not None:
        args["status"] = status
    out = execute_tool("update_task", sid, args)
    if not out.get("success"):
        raise ValueError(out.get("error", {}).get("message", "Failed to update task"))
    return out["result"]


@mcp_app.tool()
def complete_task(
    student_id: int,
    task_id: Optional[int] = None,
    task_title: Optional[str] = None
) -> Dict[str, Any]:
    """Mark an assignment as completed by task_id or title substring."""
    sid = _validate_student_id(student_id)
    args: Dict[str, Any] = {}
    if task_id is not None:
        args["task_id"] = task_id
    if task_title is not None:
        args["task_title"] = task_title
    out = execute_tool("complete_task", sid, args)
    if not out.get("success"):
        raise ValueError(out.get("error", {}).get("message", "Failed to complete task"))
    return out["result"]


@mcp_app.tool()
def delete_task(
    student_id: int,
    task_id: Optional[int] = None,
    task_title: Optional[str] = None,
    confirm_token: Optional[str] = None
) -> Dict[str, Any]:
    """Permanently delete a task. Destructive: returns a confirmation token if confirm_token is not supplied."""
    sid = _validate_student_id(student_id)
    args: Dict[str, Any] = {}
    if task_id is not None:
        args["task_id"] = task_id
    if task_title is not None:
        args["task_title"] = task_title
    if confirm_token is not None:
        args["confirm_token"] = confirm_token
    out = execute_tool("delete_task", sid, args)
    if not out.get("success"):
        raise ValueError(out.get("error", {}).get("message", "Failed to delete task"))
    return out["result"]


@mcp_app.tool()
def add_exam(
    student_id: int,
    title: str,
    exam_date: str,
    subject_code: Optional[str] = None,
    notes: str = ""
) -> Dict[str, Any]:
    """Record an upcoming exam with title, date (YYYY-MM-DD), and optional subject code and notes."""
    sid = _validate_student_id(student_id)
    args: Dict[str, Any] = {
        "title": title,
        "exam_date": exam_date,
        "notes": notes
    }
    if subject_code is not None:
        args["subject_code"] = subject_code
    out = execute_tool("add_exam", sid, args)
    if not out.get("success"):
        raise ValueError(out.get("error", {}).get("message", "Failed to add exam"))
    return out["result"]


@mcp_app.tool()
def list_exams(student_id: int) -> List[Dict[str, Any]]:
    """List all scheduled exams for the student."""
    sid = _validate_student_id(student_id)
    out = execute_tool("list_exams", sid, {})
    if not out.get("success"):
        raise ValueError(out.get("error", {}).get("message", "Failed to list exams"))
    return out["result"]


@mcp_app.tool()
def set_study_hours(
    student_id: int,
    weekday: Optional[str] = None,
    available_hours: Optional[float] = None,
    preferences: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Set available study hours for a specific weekday (0-12 hours) or multiple weekdays."""
    sid = _validate_student_id(student_id)
    args: Dict[str, Any] = {}
    if weekday is not None:
        args["weekday"] = weekday
    if available_hours is not None:
        args["available_hours"] = available_hours
    if preferences is not None:
        args["preferences"] = preferences
    out = execute_tool("set_study_hours", sid, args)
    if not out.get("success"):
        raise ValueError(out.get("error", {}).get("message", "Failed to set study hours"))
    return out["result"]


@mcp_app.tool()
def generate_study_plan(
    student_id: int,
    daily_hours: Optional[float] = None,
    exam_dates: Optional[Dict[str, str]] = None,
    require_hours: Optional[bool] = None
) -> Dict[str, Any]:
    """Generate a realistic personalized study schedule balancing subjects, difficulty, pending tasks, timetable, and upcoming exams."""
    sid = _validate_student_id(student_id)
    args: Dict[str, Any] = {}
    if daily_hours is not None:
        args["daily_hours"] = daily_hours
    if exam_dates is not None:
        args["exam_dates"] = exam_dates
    if require_hours is not None:
        args["require_hours"] = require_hours
    out = execute_tool("generate_study_plan", sid, args)
    if not out.get("success"):
        raise ValueError(out.get("error", {}).get("message", "Failed to generate study plan"))
    return out["result"]


@mcp_app.tool()
def save_study_plan(
    student_id: int,
    slots: List[Dict[str, Any]],
    confirm_token: Optional[str] = None
) -> Dict[str, Any]:
    """Persist generated study sessions into the student's study calendar. Destructive when replacing existing sessions."""
    sid = _validate_student_id(student_id)
    args: Dict[str, Any] = {"slots": slots}
    if confirm_token is not None:
        args["confirm_token"] = confirm_token
    out = execute_tool("save_study_plan", sid, args)
    if not out.get("success"):
        raise ValueError(out.get("error", {}).get("message", "Failed to save study plan"))
    return out["result"]


@mcp_app.tool()
def get_today_summary(student_id: int) -> Dict[str, Any]:
    """Get today's agenda including lectures, assignments due today/tomorrow, and study sessions."""
    sid = _validate_student_id(student_id)
    out = execute_tool("get_today_summary", sid, {})
    if not out.get("success"):
        raise ValueError(out.get("error", {}).get("message", "Failed to get today summary"))
    return out["result"]


@mcp_app.tool()
def get_attendance_summary(student_id: int) -> List[Dict[str, Any]]:
    """Get attendance percentages, safe cutoffs, and required attendance per enrolled course."""
    sid = _validate_student_id(student_id)
    out = execute_tool("get_attendance_summary", sid, {})
    if not out.get("success"):
        raise ValueError(out.get("error", {}).get("message", "Failed to get attendance summary"))
    return out["result"]


@mcp_app.tool()
def search_faq(student_id: int, query: str) -> List[Dict[str, Any]]:
    """Search campus knowledge base, policies, hostel rules, academic regulations, and library guidelines."""
    sid = _validate_student_id(student_id)
    out = execute_tool("search_faq", sid, {"query": query})
    if not out.get("success"):
        raise ValueError(out.get("error", {}).get("message", "Failed to search FAQ"))
    return out["result"]


# -------------------------------------------------------------
# 4 New Tools
# -------------------------------------------------------------

@mcp_app.tool()
def daily_briefing(student_id: int) -> str:
    """Generate a spoken daily briefing combining today's classes, attendance alerts, and pending assignments."""
    sid = _validate_student_id(student_id)

    today_rem = schedule_service.get_today_reminder(sid)
    att_stats = attendance_service.calculate_attendance(sid)
    pending_tasks = task_service.list_tasks(sid, status="Pending")

    day_name = today_rem.get("day", "Today")
    date_str = today_rem.get("date", "")
    parts = [f"Good day! Here is your daily briefing for {day_name}, {date_str}."]

    # Classes
    classes = today_rem.get("classes", [])
    if classes:
        cls_details = ", ".join([f"{c.get('name', c.get('code', 'Class'))} at {c.get('start_time', '')} in {c.get('room', 'TBD')}" for c in classes])
        parts.append(f"You have {len(classes)} classes scheduled today: {cls_details}.")
    else:
        parts.append("You have no classes scheduled for today.")

    # Due assignments
    assignments_due = today_rem.get("assignments_due", [])
    if assignments_due:
        asg_details = ", ".join([f"{a.get('title', 'Task')} (due {a.get('due_date', '')})" for a in assignments_due])
        parts.append(f"You have {len(assignments_due)} assignments due soon: {asg_details}.")

    # Attendance alerts for < 75%
    low_att = [a for a in att_stats if float(a.get("percentage", 100.0)) < 75.0]
    if low_att:
        att_alerts = ", ".join([f"{a.get('code', '')} at {a.get('percentage')}% (requires {a.get('classes_needed_for_75', 0)} consecutive classes)" for a in low_att])
        parts.append(f"Attendance warning: {att_alerts}.")
    else:
        parts.append("Your attendance is in good standing across all subjects.")

    # Pending tasks
    parts.append(f"You currently have {len(pending_tasks)} pending tasks.")

    return " ".join(parts)


@mcp_app.tool()
def get_dashboard(student_id: int) -> Dict[str, Any]:
    """Retrieve full dashboard summary including overall attendance, pending assignments, study hours, and CGPA."""
    sid = _validate_student_id(student_id)
    return dashboard_service.get_dashboard_summary(sid)


@mcp_app.tool()
def get_timetable(student_id: int) -> List[Dict[str, Any]]:
    """Retrieve the student's complete weekly timetable schedule."""
    sid = _validate_student_id(student_id)
    return schedule_service.get_timetable(sid)


@mcp_app.tool()
def calculate_cgpa(student_id: int, grades: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Calculate current CGPA and projected CGPA based on student record and optional new course grades."""
    sid = _validate_student_id(student_id)

    student = execute_query(
        "SELECT full_name, cgpa, current_semester FROM students WHERE id = ?;",
        (sid,),
        fetch_one=True
    )
    if not student:
        raise ValueError(f"Student with ID {sid} not found.")

    current_cgpa = float(student["cgpa"] if student["cgpa"] is not None else 0.0)
    current_semester = int(student["current_semester"] if student["current_semester"] is not None else 1)

    if not grades:
        return {
            "student_id": sid,
            "student_name": student["full_name"],
            "current_semester": current_semester,
            "current_cgpa": current_cgpa,
            "semester_gpa": current_cgpa,
            "projected_cgpa": current_cgpa,
            "total_credits": 0
        }

    grade_points = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}
    total_credits = 0
    total_grade_points = 0.0

    for item in grades:
        code = item.get("code", "")
        grade = str(item.get("grade", "A")).upper().strip()
        points = grade_points.get(grade, 4.0)

        subject = execute_query(
            "SELECT credits FROM subjects WHERE student_id = ? AND code = ?;",
            (sid, code),
            fetch_one=True
        )
        credits = int(subject["credits"]) if subject else 3
        total_credits += credits
        total_grade_points += (points * credits)

    calculated_gpa = round(total_grade_points / total_credits, 2) if total_credits > 0 else 0.0
    new_cgpa = round((current_cgpa * (current_semester - 1) + calculated_gpa) / current_semester, 2)

    return {
        "student_id": sid,
        "student_name": student["full_name"],
        "current_semester": current_semester,
        "current_cgpa": current_cgpa,
        "semester_gpa": calculated_gpa,
        "projected_cgpa": new_cgpa,
        "total_credits": total_credits
    }


# Map of all registered tools for introspection and test invocation
TOOLS: Dict[str, Any] = {
    "list_tasks": list_tasks,
    "add_task": add_task,
    "update_task": update_task,
    "complete_task": complete_task,
    "delete_task": delete_task,
    "add_exam": add_exam,
    "list_exams": list_exams,
    "set_study_hours": set_study_hours,
    "generate_study_plan": generate_study_plan,
    "save_study_plan": save_study_plan,
    "get_today_summary": get_today_summary,
    "get_attendance_summary": get_attendance_summary,
    "search_faq": search_faq,
    "daily_briefing": daily_briefing,
    "get_dashboard": get_dashboard,
    "get_timetable": get_timetable,
    "calculate_cgpa": calculate_cgpa
}

__all__ = [
    "mcp_app",
    "CampusMateFastMCP",
    "validate_auth_token",
    "TOOLS",
    "list_tasks",
    "add_task",
    "update_task",
    "complete_task",
    "delete_task",
    "add_exam",
    "list_exams",
    "set_study_hours",
    "generate_study_plan",
    "save_study_plan",
    "get_today_summary",
    "get_attendance_summary",
    "search_faq",
    "daily_briefing",
    "get_dashboard",
    "get_timetable",
    "calculate_cgpa"
]

if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", 8080))
    print(f"Starting CampusMate AI FastMCP Server on port {port}...")
    mcp_app.run(transport="streamable-http", host="0.0.0.0", port=port)

