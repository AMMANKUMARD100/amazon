"""Chat and Conversation History Service for CampusMate AI.

Manages multi-turn conversation sessions, message persistence,
tenant-isolated history retrieval, and audit traces for student actions.
"""

import json
import uuid
from typing import Any, Dict, List, Optional
from backend.database.connection import execute_query
from backend.services.exceptions import ValidationError, NotFoundError, PersistenceError


def create_or_get_session(student_id: int, session_id: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves an existing chat session or creates a new one for the student."""
    if not student_id:
        raise ValidationError("student_id is required.")

    if session_id:
        row = execute_query(
            "SELECT id, student_id, title, created_at, updated_at FROM chat_sessions WHERE id = ? AND student_id = ?;",
            (session_id, student_id),
            fetch_one=True
        )
        if row:
            return dict(row)
        # If specific session_id was requested but belongs to someone else or doesn't exist
        # We enforce student isolation
        row_other = execute_query("SELECT id FROM chat_sessions WHERE id = ?;", (session_id,), fetch_one=True)
        if row_other:
            raise NotFoundError("Chat session not found or access denied.")

    # Generate new session
    new_id = str(uuid.uuid4())
    session_title = (title or "Study Assistant Chat").strip()
    execute_query(
        "INSERT INTO chat_sessions (id, student_id, title) VALUES (?, ?, ?);",
        (new_id, student_id, session_title),
        commit=True
    )
    saved = execute_query(
        "SELECT id, student_id, title, created_at, updated_at FROM chat_sessions WHERE id = ? AND student_id = ?;",
        (new_id, student_id),
        fetch_one=True
    )
    if not saved:
        raise PersistenceError("Failed to create chat session.")
    return dict(saved)


def list_sessions(student_id: int) -> List[Dict[str, Any]]:
    """Lists all chat sessions for a student ordered by most recently updated."""
    if not student_id:
        raise ValidationError("student_id is required.")

    rows = execute_query(
        "SELECT id, student_id, title, created_at, updated_at FROM chat_sessions WHERE student_id = ? ORDER BY updated_at DESC;",
        (student_id,),
        fetch_all=True
    )
    return [dict(r) for r in rows]


def get_session_messages(student_id: int, session_id: str) -> List[Dict[str, Any]]:
    """Gets message history for a specific session scoped strictly to student_id."""
    if not student_id or not session_id:
        raise ValidationError("student_id and session_id are required.")

    # Verify session ownership
    sess = execute_query(
        "SELECT id FROM chat_sessions WHERE id = ? AND student_id = ?;",
        (session_id, student_id),
        fetch_one=True
    )
    if not sess:
        raise NotFoundError("Chat session not found or access denied.")

    rows = execute_query(
        """SELECT id, session_id, student_id, role, content, action_executed, tool_trace, created_at
           FROM chat_messages
           WHERE session_id = ? AND student_id = ?
           ORDER BY id ASC;""",
        (session_id, student_id),
        fetch_all=True
    )

    results = []
    for r in rows:
        d = dict(r)
        if d.get("tool_trace"):
            try:
                d["tool_trace"] = json.loads(d["tool_trace"])
            except Exception:
                pass
        results.append(d)
    return results


def append_message(
    student_id: int,
    session_id: str,
    role: str,
    content: str,
    action_executed: Optional[str] = None,
    tool_trace: Optional[Any] = None
) -> Dict[str, Any]:
    """Persists a new message to the session."""
    if not student_id or not session_id:
        raise ValidationError("student_id and session_id are required.")
    if role not in ['user', 'assistant']:
        raise ValidationError("Role must be 'user' or 'assistant'.")
    if not content or not isinstance(content, str):
        raise ValidationError("Message content is required.")

    # Verify session ownership
    sess = execute_query(
        "SELECT id FROM chat_sessions WHERE id = ? AND student_id = ?;",
        (session_id, student_id),
        fetch_one=True
    )
    if not sess:
        raise NotFoundError("Chat session not found.")

    trace_json = json.dumps(tool_trace) if tool_trace is not None else None

    msg_id = execute_query(
        """INSERT INTO chat_messages (session_id, student_id, role, content, action_executed, tool_trace)
           VALUES (?, ?, ?, ?, ?, ?);""",
        (session_id, student_id, role, content.strip(), action_executed, trace_json),
        commit=True
    )

    # Touch session updated_at
    execute_query(
        "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ? AND student_id = ?;",
        (session_id, student_id),
        commit=True
    )

    saved = execute_query(
        "SELECT id, session_id, student_id, role, content, action_executed, tool_trace, created_at FROM chat_messages WHERE id = ?;",
        (msg_id,),
        fetch_one=True
    )
    if not saved:
        raise PersistenceError("Failed to persist message.")

    res = dict(saved)
    if res.get("tool_trace"):
        try:
            res["tool_trace"] = json.loads(res["tool_trace"])
        except Exception:
            pass
    return res


def delete_session(student_id: int, session_id: str) -> Dict[str, Any]:
    """Deletes a chat session and its messages (CASCADE)."""
    if not student_id or not session_id:
        raise ValidationError("student_id and session_id are required.")

    sess = execute_query(
        "SELECT id FROM chat_sessions WHERE id = ? AND student_id = ?;",
        (session_id, student_id),
        fetch_one=True
    )
    if not sess:
        raise NotFoundError("Chat session not found.")

    execute_query("DELETE FROM chat_messages WHERE session_id = ? AND student_id = ?;", (session_id, student_id), commit=True)
    execute_query("DELETE FROM chat_sessions WHERE id = ? AND student_id = ?;", (session_id, student_id), commit=True)

    return {"message": "Chat session deleted successfully.", "session_id": session_id}
