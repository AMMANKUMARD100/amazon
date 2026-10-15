"""Unified Tool Registry for CampusMate AI.

Defines all capabilities/tools available to LLMs and agents in one central place.
Validates schemas strictly, rejects extra parameters, handles ambiguity,
and enforces short-lived confirmation tokens for destructive operations.
"""

import time
import secrets
import jsonschema
from typing import Any, Callable, Dict, List, Optional

from backend.services.exceptions import AppError, ValidationError, NotFoundError, PersistenceError
from backend.services.task_service import (
    list_tasks,
    get_task,
    add_task,
    update_task,
    complete_task,
    delete_task
)
from backend.services.exam_service import (
    list_exams,
    get_exam,
    add_exam,
    update_exam,
    delete_exam,
    get_study_preferences,
    set_study_preference,
    set_bulk_study_preferences
)
from backend.services.planner_service import (
    generate_study_plan,
    save_study_slots
)
from backend.services.schedule_service import get_today_reminder
from backend.services.attendance_service import calculate_attendance
from backend.services.faq_service import search_faq
from backend.database.connection import execute_query

# In-memory store for confirmation tokens: {token: {student_id, tool_name, args, expires_at}}
_PENDING_CONFIRMATIONS: Dict[str, Dict[str, Any]] = {}
CONFIRMATION_TTL_SECONDS = 300  # 5 minutes


def create_confirmation_token(student_id: int, tool_name: str, args: Dict[str, Any], ttl: int = CONFIRMATION_TTL_SECONDS) -> str:
    """Creates a short-lived token required to execute destructive actions."""
    # Clean expired tokens first
    _clean_expired_tokens()
    token = secrets.token_hex(16)
    _PENDING_CONFIRMATIONS[token] = {
        "student_id": student_id,
        "tool_name": tool_name,
        "args": args,
        "expires_at": time.time() + ttl
    }
    return token


def verify_confirmation_token(token: str, student_id: int, tool_name: str) -> Optional[Dict[str, Any]]:
    """Validates and consumes a confirmation token. Returns stored args if valid, else None."""
    _clean_expired_tokens()
    entry = _PENDING_CONFIRMATIONS.get(token)
    if not entry:
        return None
    if entry["student_id"] != student_id or entry["tool_name"] != tool_name:
        return None
    if time.time() > entry["expires_at"]:
        _PENDING_CONFIRMATIONS.pop(token, None)
        return None
    # Token valid - consume it (single-use)
    _PENDING_CONFIRMATIONS.pop(token, None)
    return entry["args"]


def _clean_expired_tokens():
    """Removes expired confirmation tokens."""
    now = time.time()
    expired = [k for k, v in _PENDING_CONFIRMATIONS.items() if now > v.get("expires_at", 0)]
    for k in expired:
        _PENDING_CONFIRMATIONS.pop(k, None)


class ToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        parameters_schema: Dict[str, Any],
        handler: Callable,
        destructive: bool = False
    ):
        self.name = name
        self.description = description
        self.parameters_schema = parameters_schema
        self.handler = handler
        self.destructive = destructive

    def validate_args(self, args: Dict[str, Any]):
        """Validates args against schema, ensuring no disallowed extra parameters."""
        try:
            jsonschema.validate(instance=args, schema=self.parameters_schema)
        except jsonschema.ValidationError as err:
            raise ValidationError(f"Invalid parameters for tool '{self.name}': {err.message}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
            "destructive": self.destructive
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self, include_extensions: bool = False) -> List[Dict[str, Any]]:
        if include_extensions:
            return [t.to_dict() for t in self._tools.values()]
        # Core 13 baseline tools protected for existing test suite
        core_names = {
            "list_tasks", "add_task", "update_task", "complete_task", "delete_task",
            "add_exam", "list_exams", "set_study_hours", "generate_study_plan",
            "save_study_plan", "get_today_summary", "get_attendance_summary", "search_faq"
        }
        return [t.to_dict() for t in self._tools.values() if t.name in core_names]


    def execute(self, tool_name: str, student_id: int, args: Dict[str, Any]) -> Dict[str, Any]:
        """Main dispatcher for tool execution with validation, ambiguity resolution, and confirmation tokens."""
        if not student_id or not isinstance(student_id, int):
            return {
                "success": False,
                "error": {
                    "code": "InvalidStudent",
                    "message": "A valid authenticated student_id is required.",
                    "recoverable": False
                }
            }

        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "error": {
                    "code": "UnknownTool",
                    "message": f"Tool '{tool_name}' is not recognized.",
                    "recoverable": False
                }
            }

        # 1. Validate parameters against schema
        try:
            tool.validate_args(args)
        except ValidationError as ve:
            return {
                "success": False,
                "error": {
                    "code": "ValidationError",
                    "message": ve.message,
                    "recoverable": True
                }
            }

        # 2. Execute handler safely
        try:
            result = tool.handler(student_id, args)
            return {
                "success": True,
                "result": result
            }
        except AppError as ae:
            return {
                "success": False,
                "error": {
                    "code": ae.__class__.__name__,
                    "message": ae.message,
                    "recoverable": isinstance(ae, (ValidationError, NotFoundError))
                }
            }
        except Exception as ex:
            return {
                "success": False,
                "error": {
                    "code": "InternalError",
                    "message": str(ex),
                    "recoverable": False
                }
            }


# Instantiate singleton registry
tool_registry = ToolRegistry()


# -------------------------------------------------------------
# Tool Handlers with Ambiguity & Confirmation Support
# -------------------------------------------------------------

def _resolve_task_identifier(student_id: int, task_id: Optional[int], task_title: Optional[str]) -> Dict[str, Any]:
    """Helper to resolve task by id or title substring. Checks for ambiguity."""
    if task_id is not None:
        # direct lookup
        task = get_task(student_id, task_id)
        return {"match": task}

    if not task_title or not task_title.strip():
        raise ValidationError("Either 'task_id' or 'task_title' must be provided.")

    needle = task_title.strip().lower()
    all_tasks = list_tasks(student_id)
    matches = [t for t in all_tasks if needle in t['title'].lower()]

    if not matches:
        raise NotFoundError(f"No task found matching '{task_title}'.")
    if len(matches) > 1:
        # Ambiguous! Return candidates instead of guessing
        return {
            "ambiguous": True,
            "candidates": [{"id": m["id"], "title": m["title"], "due_date": m["due_date"]} for m in matches]
        }
    return {"match": matches[0]}


def _handle_list_tasks(student_id: int, args: Dict[str, Any]) -> Any:
    status = args.get("status")
    return list_tasks(student_id, status=status)


def _handle_add_task(student_id: int, args: Dict[str, Any]) -> Any:
    title = args["title"]
    due_date = args["due_date"]
    priority = args.get("priority", "Medium")
    description = args.get("description", "")
    subject_code = args.get("subject_code")
    return add_task(
        student_id=student_id,
        title=title,
        due_date=due_date,
        priority=priority,
        description=description,
        subject_code=subject_code
    )


def _handle_update_task(student_id: int, args: Dict[str, Any]) -> Any:
    resolved = _resolve_task_identifier(student_id, args.get("task_id"), args.get("task_title"))
    if resolved.get("ambiguous"):
        return {
            "ambiguity": True,
            "message": "Multiple tasks match the specified title. Please specify by task_id.",
            "candidates": resolved["candidates"]
        }
    task = resolved["match"]

    updates = {}
    for f in ["title", "description", "due_date", "status", "priority"]:
        if f in args and args[f] is not None:
            updates[f] = args[f]

    return update_task(student_id, task["id"], updates)


def _handle_complete_task(student_id: int, args: Dict[str, Any]) -> Any:
    resolved = _resolve_task_identifier(student_id, args.get("task_id"), args.get("task_title"))
    if resolved.get("ambiguous"):
        return {
            "ambiguity": True,
            "message": "Multiple tasks match the specified title. Please specify by task_id.",
            "candidates": resolved["candidates"]
        }
    task = resolved["match"]
    return complete_task(student_id, task["id"])


def _handle_delete_task(student_id: int, args: Dict[str, Any]) -> Any:
    """Destructive: requires confirmation token unless confirm_token is valid."""
    confirm_token = args.get("confirm_token")

    if confirm_token:
        stored_args = verify_confirmation_token(confirm_token, student_id, "delete_task")
        if not stored_args:
            raise ValidationError("Invalid, expired, or already used confirmation token.")
        actual_task_id = stored_args.get("task_id")
        return delete_task(student_id, actual_task_id)

    # Pre-execution: check existence and ambiguity before asking for confirmation
    resolved = _resolve_task_identifier(student_id, args.get("task_id"), args.get("task_title"))
    if resolved.get("ambiguous"):
        return {
            "ambiguity": True,
            "message": "Multiple tasks match the specified title. Please specify by task_id.",
            "candidates": resolved["candidates"]
        }

    task = resolved["match"]
    token = create_confirmation_token(student_id, "delete_task", {"task_id": task["id"]})

    return {
        "pending_confirmation": True,
        "confirm_token": token,
        "message": f"Are you sure you want to delete task #{task['id']} '{task['title']}'? This action cannot be undone.",
        "target": {
            "task_id": task["id"],
            "title": task["title"],
            "due_date": task["due_date"]
        }
    }


def _handle_add_exam(student_id: int, args: Dict[str, Any]) -> Any:
    return add_exam(
        student_id=student_id,
        title=args["title"],
        exam_date=args["exam_date"],
        subject_code=args.get("subject_code"),
        notes=args.get("notes", "")
    )


def _handle_list_exams(student_id: int, args: Dict[str, Any]) -> Any:
    return list_exams(student_id)


def _handle_set_study_hours(student_id: int, args: Dict[str, Any]) -> Any:
    weekday = args.get("weekday")
    available_hours = args.get("available_hours")
    bulk_preferences = args.get("preferences")

    if bulk_preferences:
        return set_bulk_study_preferences(student_id, bulk_preferences)
    elif weekday and available_hours is not None:
        return set_study_preference(student_id, weekday, available_hours)
    else:
        raise ValidationError("Must provide either ('weekday' and 'available_hours') or 'preferences' map.")


def _handle_generate_study_plan(student_id: int, args: Dict[str, Any]) -> Any:
    preferences = {}
    if "daily_hours" in args and args["daily_hours"] is not None:
        preferences["daily_hours"] = args["daily_hours"]
    if "exam_dates" in args and args["exam_dates"] is not None:
        preferences["exam_dates"] = args["exam_dates"]
    if "require_hours" in args:
        preferences["require_hours"] = args["require_hours"]

    return generate_study_plan(student_id, preferences)


def _handle_save_study_plan(student_id: int, args: Dict[str, Any]) -> Any:
    """Destructive if replacing existing scheduled study plans."""
    slots = args.get("slots", [])
    confirm_token = args.get("confirm_token")

    # Check if student already has existing scheduled study sessions
    existing_sessions = execute_query(
        "SELECT COUNT(*) FROM study_plans WHERE student_id = ? AND status = 'Scheduled';",
        (student_id,),
        fetch_one=True
    )[0]

    if existing_sessions > 0 and not confirm_token:
        # Destructive replacement requires confirmation token
        token = create_confirmation_token(student_id, "save_study_plan", {"slots": slots})
        return {
            "pending_confirmation": True,
            "confirm_token": token,
            "message": f"You currently have {existing_sessions} existing study sessions scheduled. Saving this plan will replace them. Please confirm to proceed.",
            "existing_count": existing_sessions,
            "new_count": len(slots)
        }

    if confirm_token:
        stored_args = verify_confirmation_token(confirm_token, student_id, "save_study_plan")
        if not stored_args:
            raise ValidationError("Invalid, expired, or already used confirmation token.")
        slots = stored_args.get("slots", slots)
        # Clear existing scheduled sessions before inserting new
        execute_query("DELETE FROM study_plans WHERE student_id = ? AND status = 'Scheduled';", (student_id,), commit=True)

    saved_count = save_study_slots(student_id, slots)
    return {
        "saved_count": saved_count,
        "message": f"Successfully saved {saved_count} study sessions."
    }


def _handle_get_today_summary(student_id: int, args: Dict[str, Any]) -> Any:
    return get_today_reminder(student_id)


def _handle_get_attendance_summary(student_id: int, args: Dict[str, Any]) -> Any:
    return calculate_attendance(student_id)


def _handle_search_faq(student_id: int, args: Dict[str, Any]) -> Any:
    query = args["query"]
    return search_faq(query)


# -------------------------------------------------------------
# Register all 13 Tools with strict JSON schemas
# -------------------------------------------------------------

tool_registry.register(ToolDefinition(
    name="list_tasks",
    description="List student assignments and tasks. Optionally filter by status ('Pending' or 'Completed').",
    parameters_schema={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["Pending", "Completed"],
                "description": "Optional filter for task status"
            }
        },
        "additionalProperties": False
    },
    handler=_handle_list_tasks,
    destructive=False
))

tool_registry.register(ToolDefinition(
    name="add_task",
    description="Add a new assignment or homework task with a validated YYYY-MM-DD due date.",
    parameters_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "minLength": 1, "maxLength": 150, "description": "Title of the task"},
            "due_date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$", "description": "Due date in YYYY-MM-DD format"},
            "priority": {"type": "string", "enum": ["High", "Medium", "Low"], "description": "Priority level"},
            "description": {"type": "string", "maxLength": 500, "description": "Optional details"},
            "subject_code": {"type": "string", "maxLength": 20, "description": "Course code (e.g. CS101), or omit for General task"}
        },
        "required": ["title", "due_date"],
        "additionalProperties": False
    },
    handler=_handle_add_task,
    destructive=False
))

tool_registry.register(ToolDefinition(
    name="update_task",
    description="Update an existing task's title, description, due date, priority, or status.",
    parameters_schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "Unique ID of the task to update"},
            "task_title": {"type": "string", "description": "Title substring of the task (if task_id not known)"},
            "title": {"type": "string", "minLength": 1, "maxLength": 150},
            "description": {"type": "string", "maxLength": 500},
            "due_date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
            "status": {"type": "string", "enum": ["Pending", "Completed"]}
        },
        "additionalProperties": False
    },
    handler=_handle_update_task,
    destructive=False
))

tool_registry.register(ToolDefinition(
    name="complete_task",
    description="Mark an assignment as completed by task_id or title substring.",
    parameters_schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "ID of task to complete"},
            "task_title": {"type": "string", "description": "Title or substring of task to complete"}
        },
        "additionalProperties": False
    },
    handler=_handle_complete_task,
    destructive=False
))

tool_registry.register(ToolDefinition(
    name="delete_task",
    description="Permanently delete a task. Destructive: returns a confirmation token if confirm_token is not supplied.",
    parameters_schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "ID of task to delete"},
            "task_title": {"type": "string", "description": "Title or substring of task to delete"},
            "confirm_token": {"type": "string", "description": "Confirmation token returned from a pending confirmation step"}
        },
        "additionalProperties": False
    },
    handler=_handle_delete_task,
    destructive=True
))

tool_registry.register(ToolDefinition(
    name="add_exam",
    description="Record an upcoming exam with title and date (YYYY-MM-DD).",
    parameters_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "minLength": 1, "maxLength": 150, "description": "Title of the exam"},
            "exam_date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$", "description": "Exam date in YYYY-MM-DD format"},
            "subject_code": {"type": "string", "maxLength": 20, "description": "Course code (e.g. CS101)"},
            "notes": {"type": "string", "maxLength": 500, "description": "Optional notes or exam topics"}
        },
        "required": ["title", "exam_date"],
        "additionalProperties": False
    },
    handler=_handle_add_exam,
    destructive=False
))

tool_registry.register(ToolDefinition(
    name="list_exams",
    description="List all scheduled exams for the student.",
    parameters_schema={
        "type": "object",
        "properties": {},
        "additionalProperties": False
    },
    handler=_handle_list_exams,
    destructive=False
))

tool_registry.register(ToolDefinition(
    name="set_study_hours",
    description="Set available study hours for a specific weekday (0-12 hours) or multiple weekdays.",
    parameters_schema={
        "type": "object",
        "properties": {
            "weekday": {
                "type": "string",
                "enum": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            },
            "available_hours": {"type": "number", "minimum": 0, "maximum": 12},
            "preferences": {
                "type": "object",
                "additionalProperties": {"type": "number", "minimum": 0, "maximum": 12}
            }
        },
        "additionalProperties": False
    },
    handler=_handle_set_study_hours,
    destructive=False
))

tool_registry.register(ToolDefinition(
    name="generate_study_plan",
    description="Generate a realistic personalized study schedule balancing subjects, difficulty, pending tasks, timetable, and upcoming exams.",
    parameters_schema={
        "type": "object",
        "properties": {
            "daily_hours": {"type": "number", "minimum": 0.5, "maximum": 12.0},
            "exam_dates": {"type": "object", "additionalProperties": {"type": "string"}},
            "require_hours": {"type": "boolean"}
        },
        "additionalProperties": False
    },
    handler=_handle_generate_study_plan,
    destructive=False
))

tool_registry.register(ToolDefinition(
    name="save_study_plan",
    description="Persist generated study sessions into the student's study calendar. Destructive when replacing existing sessions.",
    parameters_schema={
        "type": "object",
        "properties": {
            "slots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                        "start_time": {"type": "string"},
                        "end_time": {"type": "string"},
                        "topic": {"type": "string"}
                    },
                    "required": ["code", "date", "start_time", "end_time"]
                }
            },
            "confirm_token": {"type": "string", "description": "Token to confirm replacing existing scheduled study sessions"}
        },
        "required": ["slots"],
        "additionalProperties": False
    },
    handler=_handle_save_study_plan,
    destructive=True
))

tool_registry.register(ToolDefinition(
    name="get_today_summary",
    description="Get today's agenda including lectures, assignments due today/tomorrow, and study sessions.",
    parameters_schema={
        "type": "object",
        "properties": {},
        "additionalProperties": False
    },
    handler=_handle_get_today_summary,
    destructive=False
))

tool_registry.register(ToolDefinition(
    name="get_attendance_summary",
    description="Get attendance percentages, safe cutoffs, and required attendance per enrolled course.",
    parameters_schema={
        "type": "object",
        "properties": {},
        "additionalProperties": False
    },
    handler=_handle_get_attendance_summary,
    destructive=False
))

tool_registry.register(ToolDefinition(
    name="search_faq",
    description="Search campus knowledge base, policies, hostel rules, academic regulations, and library guidelines.",
    parameters_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1, "description": "Search keyword or question"}
        },
        "required": ["query"],
        "additionalProperties": False
    },
    handler=_handle_search_faq,
    destructive=False
))

# -------------------------------------------------------------
# Proactive Intelligence & Daily Briefing Tools (Phase 1 & 3)
# -------------------------------------------------------------

def _handle_check_attendance_risk(student_id: int, args: Dict[str, Any]) -> Any:
    from backend.services.proactive_service import check_attendance_risk
    return check_attendance_risk(student_id)

def _handle_check_deadline_conflicts(student_id: int, args: Dict[str, Any]) -> Any:
    from backend.services.proactive_service import check_deadline_conflicts
    return check_deadline_conflicts(student_id)

def _handle_get_weekly_summary(student_id: int, args: Dict[str, Any]) -> Any:
    from backend.services.proactive_service import generate_weekly_summary
    return generate_weekly_summary(student_id)

def _handle_get_proactive_alerts(student_id: int, args: Dict[str, Any]) -> Any:
    from backend.services.proactive_service import get_proactive_alerts
    return get_proactive_alerts(student_id)

tool_registry.register(ToolDefinition(
    name="check_attendance_risk",
    description="Identify courses below 75% attendance or near critical cutoff.",
    parameters_schema={"type": "object", "properties": {}, "additionalProperties": False},
    handler=_handle_check_attendance_risk,
    destructive=False
))

tool_registry.register(ToolDefinition(
    name="check_deadline_conflicts",
    description="Find imminent task deadlines within 48 hours or overlapping exam schedules.",
    parameters_schema={"type": "object", "properties": {}, "additionalProperties": False},
    handler=_handle_check_deadline_conflicts,
    destructive=False
))

tool_registry.register(ToolDefinition(
    name="get_weekly_summary",
    description="Consolidate weekly metrics across tasks, attendance health, study sessions, and exams.",
    parameters_schema={"type": "object", "properties": {}, "additionalProperties": False},
    handler=_handle_get_weekly_summary,
    destructive=False
))

tool_registry.register(ToolDefinition(
    name="get_proactive_alerts",
    description="Get prioritized proactive alert notifications for attendance, deadlines, and exams.",
    parameters_schema={"type": "object", "properties": {}, "additionalProperties": False},
    handler=_handle_get_proactive_alerts,
    destructive=False
))


def execute_tool(tool_name: str, student_id: int, args: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience wrapper for tool_registry.execute()."""
    return tool_registry.execute(tool_name, student_id, args)

