"""
conversation_state.py — Multi-turn conversation state manager.
Maintains per-student pending dialog state (missing info, follow-up context).
Uses an in-memory dict (sufficient for demo; replace with Redis for production).
"""
import time
import threading
from typing import Dict, Any, Optional

_lock = threading.Lock()

# In-memory state store: {student_id: {state_data}}
_state: Dict[int, Dict[str, Any]] = {}

# State expires after 10 minutes of inactivity
STATE_TTL = 600


def set_state(student_id: int, intent: str, data: Dict[str, Any]) -> None:
    """Store pending conversation state for a student."""
    with _lock:
        _state[student_id] = {
            "intent": intent,
            "data": data,
            "timestamp": time.time()
        }


def get_state(student_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve conversation state if not expired."""
    with _lock:
        entry = _state.get(student_id)
        if not entry:
            return None
        if time.time() - entry["timestamp"] > STATE_TTL:
            del _state[student_id]
            return None
        return entry


def clear_state(student_id: int) -> None:
    """Clear conversation state for a student."""
    with _lock:
        _state.pop(student_id, None)


def update_state_data(student_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Merge new data into existing state."""
    with _lock:
        entry = _state.get(student_id)
        if not entry:
            return None
        entry["data"].update(updates)
        entry["timestamp"] = time.time()
        return entry


def has_pending_state(student_id: int) -> bool:
    """Check if student has an active pending conversation state."""
    return get_state(student_id) is not None


# ─────────────────────────────────────────────────────────────────────────────
# Question builders — generate prompts for missing information
# ─────────────────────────────────────────────────────────────────────────────

MEETING_QUESTIONS = {
    "date": "What date should I schedule the meeting? (e.g. tomorrow, next Monday, or a specific date)",
    "title": "What is the meeting about? Please give it a title.",
    "participants": "Who will be attending the meeting? (You can say 'skip' if not sure)",
    "location": "Where will the meeting be held? (e.g. Zoom, Office, Room 301, or skip)",
}

EXAM_PLAN_QUESTIONS = {
    "subjects": "Which subjects do you want to study? Please list them separated by commas.",
    "days": "How many days do you have until your exam?",
    "daily_hours": "How many hours can you study each day? (e.g. 4 hours)",
}

PROJECT_PLAN_QUESTIONS = {
    "project_name": "What is the name or description of your project?",
    "project_type": "What type of project is this? (e.g. web app, mobile app, ML model, website)",
    "days": "How many days do you have to complete this project?",
    "team_size": "How many people are working on this? (default: 1)",
}


def build_follow_up_question(intent: str, missing_field: str) -> str:
    """Build the right follow-up question based on intent and missing field."""
    questions = {
        "schedule_meeting": MEETING_QUESTIONS,
        "exam_plan": EXAM_PLAN_QUESTIONS,
        "project_plan": PROJECT_PLAN_QUESTIONS,
    }
    q_map = questions.get(intent, {})
    return q_map.get(missing_field, f"Could you provide the {missing_field}?")
