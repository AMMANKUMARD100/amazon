"""
meeting_service.py — Meeting scheduling, reminders, and management.
Supports natural language date/time parsing and stores meetings in SQLite.
"""
import re
import datetime
import logging
from typing import Optional, List, Dict, Any
from backend.database.connection import execute_query
from backend.services.exceptions import ValidationError, NotFoundError, PersistenceError

logger = logging.getLogger('mcp')

# ─────────────────────────────────────────────────────────────────────────────
# DB migration — creates the meetings table if it doesn't exist
# ─────────────────────────────────────────────────────────────────────────────

def ensure_meetings_table():
    """Create meetings table if not exists."""
    execute_query("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            meeting_date TEXT NOT NULL,
            meeting_time TEXT DEFAULT '10:00',
            participants TEXT DEFAULT '',
            location TEXT DEFAULT '',
            status TEXT DEFAULT 'Scheduled',
            reminder_sent INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """, commit=True)


# ─────────────────────────────────────────────────────────────────────────────
# Natural language date/time parser
# ─────────────────────────────────────────────────────────────────────────────

DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6
}

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12
}


def parse_date(text: str) -> Optional[str]:
    """Parse natural language date from text. Returns YYYY-MM-DD or None."""
    text = text.lower().strip()
    today = datetime.date.today()

    # Explicit YYYY-MM-DD
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if m:
        return m.group(0)

    # DD/MM/YYYY or MM/DD/YYYY
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime.date(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # "today"
    if "today" in text:
        return today.strftime("%Y-%m-%d")

    # "tomorrow"
    if "tomorrow" in text:
        return (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    # "day after tomorrow"
    if "day after tomorrow" in text:
        return (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d")

    # "next <weekday>"
    m = re.search(r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", text)
    if m:
        target_day = DAY_MAP[m.group(1)]
        days_ahead = target_day - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        days_ahead += 7  # "next" implies the one after this week
        return (today + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # "<weekday>" (this week)
    m = re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", text)
    if m:
        target_day = DAY_MAP[m.group(1)]
        days_ahead = target_day - today.weekday()
        if days_ahead < 0:
            days_ahead += 7
        return (today + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # "in N days"
    m = re.search(r"in\s+(\d+)\s+days?", text)
    if m:
        return (today + datetime.timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")

    # "<N> <month>" or "<month> <N>"
    m = re.search(r"(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)", text)
    if m:
        day, month_name = int(m.group(1)), MONTH_MAP[m.group(2)]
        year = today.year
        try:
            dt = datetime.date(year, month_name, day)
            if dt < today:
                dt = datetime.date(year + 1, month_name, day)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def parse_time(text: str) -> Optional[str]:
    """Parse time from natural language. Returns HH:MM (24h) or None."""
    text = text.lower().strip()

    # HH:MM am/pm
    m = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?", text)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        meridiem = m.group(3)
        if meridiem == "pm" and h != 12:
            h += 12
        elif meridiem == "am" and h == 12:
            h = 0
        return f"{h:02d}:{mi:02d}"

    # "<N> am/pm"
    m = re.search(r"\b(\d{1,2})\s*(am|pm)\b", text)
    if m:
        h = int(m.group(1))
        meridiem = m.group(2)
        if meridiem == "pm" and h != 12:
            h += 12
        elif meridiem == "am" and h == 12:
            h = 0
        return f"{h:02d}:00"

    # "at N o'clock"
    m = re.search(r"at\s+(\d{1,2})\s*o'?clock", text)
    if m:
        return f"{int(m.group(1)):02d}:00"

    # Named times
    if "morning" in text:
        return "09:00"
    if "noon" in text or "midday" in text:
        return "12:00"
    if "afternoon" in text:
        return "14:00"
    if "evening" in text:
        return "18:00"
    if "night" in text:
        return "20:00"

    return None


# ─────────────────────────────────────────────────────────────────────────────
# CRUD Operations
# ─────────────────────────────────────────────────────────────────────────────

def schedule_meeting(student_id: int, title: str, meeting_date: str,
                     meeting_time: str = "10:00", description: str = "",
                     participants: str = "", location: str = "") -> Dict[str, Any]:
    """Schedule a new meeting."""
    ensure_meetings_table()
    if not student_id:
        raise ValidationError("student_id is required.")
    if not title or not title.strip():
        raise ValidationError("Meeting title is required.")
    if not meeting_date:
        raise ValidationError("Meeting date is required.")

    # Validate date
    try:
        datetime.datetime.strptime(meeting_date, "%Y-%m-%d")
    except ValueError:
        raise ValidationError(f"Invalid date format: {meeting_date}. Use YYYY-MM-DD.")

    row_id = execute_query("""
        INSERT INTO meetings (student_id, title, description, meeting_date, meeting_time, participants, location)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (student_id, title.strip(), description, meeting_date, meeting_time or "10:00",
          participants, location), commit=True)

    if not row_id:
        raise PersistenceError("Failed to save meeting.")

    return {
        "id": row_id,
        "title": title.strip(),
        "meeting_date": meeting_date,
        "meeting_time": meeting_time or "10:00",
        "participants": participants,
        "location": location,
        "description": description,
        "status": "Scheduled"
    }


def list_meetings(student_id: int, from_date: Optional[str] = None,
                  to_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """List meetings for a student, optionally filtered by date range."""
    ensure_meetings_table()
    if not student_id:
        raise ValidationError("student_id is required.")

    if not from_date:
        from_date = datetime.date.today().strftime("%Y-%m-%d")

    query = "SELECT * FROM meetings WHERE student_id = ? AND meeting_date >= ? AND status != 'Cancelled'"
    params = [student_id, from_date]

    if to_date:
        query += " AND meeting_date <= ?"
        params.append(to_date)

    query += " ORDER BY meeting_date ASC, meeting_time ASC;"
    rows = execute_query(query, tuple(params), fetch_all=True)
    return [dict(r) for r in rows] if rows else []


def get_upcoming_meetings(student_id: int, days: int = 7) -> List[Dict[str, Any]]:
    """Get meetings in the next N days."""
    today = datetime.date.today()
    until = (today + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    return list_meetings(student_id, from_date=today.strftime("%Y-%m-%d"), to_date=until)


def cancel_meeting(student_id: int, meeting_id: int) -> Dict[str, Any]:
    """Cancel a meeting."""
    ensure_meetings_table()
    row = execute_query(
        "SELECT * FROM meetings WHERE id = ? AND student_id = ?;",
        (meeting_id, student_id), fetch_one=True
    )
    if not row:
        raise NotFoundError(f"Meeting #{meeting_id} not found.")

    execute_query(
        "UPDATE meetings SET status = 'Cancelled' WHERE id = ?;",
        (meeting_id,), commit=True
    )
    return {"message": f"Meeting '{row['title']}' has been cancelled.", "id": meeting_id}


def get_meeting_reminder_text(meeting: Dict[str, Any]) -> str:
    """Generate a spoken reminder for a meeting."""
    date_obj = datetime.datetime.strptime(meeting['meeting_date'], "%Y-%m-%d").date()
    today = datetime.date.today()
    days_left = (date_obj - today).days

    if days_left == 0:
        when = "today"
    elif days_left == 1:
        when = "tomorrow"
    else:
        when = f"in {days_left} days"

    time_str = meeting.get('meeting_time', '10:00')
    parts = [f"Reminder: You have a meeting '{meeting['title']}' {when} at {time_str}."]
    if meeting.get('participants'):
        parts.append(f"Participants: {meeting['participants']}.")
    if meeting.get('location'):
        parts.append(f"Location: {meeting['location']}.")
    return " ".join(parts)


def check_due_reminders(student_id: int) -> List[str]:
    """Check for meetings today or tomorrow that haven't sent reminders."""
    ensure_meetings_table()
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    rows = execute_query("""
        SELECT * FROM meetings
        WHERE student_id = ? AND status = 'Scheduled' AND reminder_sent = 0
        AND meeting_date IN (?, ?)
        ORDER BY meeting_date ASC;
    """, (student_id, today.strftime("%Y-%m-%d"), tomorrow.strftime("%Y-%m-%d")), fetch_all=True)

    reminders = []
    for row in (rows or []):
        m = dict(row)
        reminders.append(get_meeting_reminder_text(m))
        execute_query("UPDATE meetings SET reminder_sent = 1 WHERE id = ?;", (m['id'],), commit=True)

    return reminders


def parse_meeting_from_utterance(utterance: str) -> Dict[str, Any]:
    """
    Extract meeting details from natural language.
    Returns dict with: title, meeting_date, meeting_time, participants, needs (list of missing fields)
    """
    text = utterance.lower()
    needs = []

    # Extract date
    meeting_date = parse_date(text)
    if not meeting_date:
        needs.append("date")

    # Extract time
    meeting_time = parse_time(text)
    if not meeting_time:
        meeting_time = "10:00"  # Default

    # Extract title — remove known keywords
    title = re.sub(r"\b(schedule|plan|set up|arrange|book|create|add)\b", "", text, flags=re.IGNORECASE)
    title = re.sub(r"\b(a |an |the )?(meeting|call|session|standup|sync|review|discussion)\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\b(on|at|for|with|tomorrow|today|next|this)\b.*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\b\d{1,2}[:/]\d{2}\b.*", "", title)
    title = re.sub(r"\b(am|pm)\b.*", "", title)
    title = re.sub(r"\s+", " ", title).strip(" ,.-")

    # Extract "about <topic>" as title if nothing else
    about_match = re.search(r"\babout\s+(.+?)(?:\s+(?:on|at|for|with)|$)", utterance, re.IGNORECASE)
    if about_match and (not title or len(title) < 3):
        title = about_match.group(1).strip()

    if not title or len(title) < 3:
        title = "Team Meeting"

    # Capitalize
    title = title.title()

    # Extract participants — "with <names>"
    participants = ""
    with_match = re.search(r"\bwith\s+(.+?)(?:\s+on\s+|\s+at\s+|$)", utterance, re.IGNORECASE)
    if with_match:
        participants = with_match.group(1).strip()

    return {
        "title": title,
        "meeting_date": meeting_date,
        "meeting_time": meeting_time,
        "participants": participants,
        "needs": needs
    }
