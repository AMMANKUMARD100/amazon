import datetime
import re
from backend.database.connection import execute_query
from backend.services.exceptions import ValidationError, PersistenceError
from backend.services.task_service import list_tasks
from backend.services.exam_service import list_exams, get_study_preferences
from backend.services.schedule_service import get_timetable

WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def generate_study_plan(student_id, preferences=None):
    """Generates study schedule using stored exams, preferences, subjects.difficulty, priorities, and pending tasks.
    
    Returns:
      dict with:
        - success: bool
        - study_plan: list of scheduled sessions
        - unscheduled_hours: float
        - needs_input: list of missing elements (if any)
    """
    if not student_id:
        raise ValidationError("student_id is required.")

    if preferences is None:
        preferences = {}

    today = datetime.date.today()

    # 1. Load subjects with real difficulty
    raw_subjects = execute_query(
        "SELECT id as subject_id, code, name, credits, difficulty FROM subjects WHERE student_id = ?;",
        (student_id,),
        fetch_all=True
    )
    if not raw_subjects:
        return {
            "success": False,
            "needs_input": ["subjects"],
            "message": "No registered subjects found. Please register your subjects first."
        }
    subjects = [dict(s) for s in raw_subjects]

    # 2. Load stored exams and preferences
    stored_exams = list_exams(student_id)
    exam_by_code = {}
    for ex in stored_exams:
        if ex.get('code') and ex['code'] != 'GEN':
            exam_by_code[ex['code']] = ex['exam_date']

    # Merge with preferences overrides if user passed any
    user_exams = preferences.get("exam_dates", {})
    for k, v in user_exams.items():
        exam_by_code[k] = v

    stored_prefs = get_study_preferences(student_id)
    # Check if we have hours specified either in preferences table or in payload
    default_daily = preferences.get("daily_hours")

    # If neither stored preferences nor daily_hours provided:
    # If preferences dict has explicit 'require_hours' or empty without stored prefs and preferences explicitly requested, return needs_input
    if preferences.get("require_hours") and not stored_prefs and not default_daily:
        return {
            "success": False,
            "needs_input": ["available_hours"],
            "message": "Missing study hours. Please provide daily available study hours or set weekday preferences."
        }
    if not default_daily:
        default_daily = 3.0

    # Determine hours per weekday
    weekday_hours = {}
    for day in WEEKDAYS:
        if day in stored_prefs:
            weekday_hours[day] = stored_prefs[day]
        elif default_daily is not None:
            weekday_hours[day] = float(default_daily)
        else:
            weekday_hours[day] = 3.0

    # 3. Load Timetable to avoid class conflicts
    timetable_entries = get_timetable(student_id)
    busy_slots = {}  # day_name -> list of (start_min, end_min)
    for t in timetable_entries:
        d = t['day_of_week']
        try:
            sh, sm = map(int, t['start_time'].split(':'))
            eh, em = map(int, t['end_time'].split(':'))
            busy_slots.setdefault(d, []).append((sh * 60 + sm, eh * 60 + em))
        except Exception:
            pass

    # 4. Load pending tasks
    pending_assignments = list_tasks(student_id, status="Pending")

    # 5. Evaluate subject study weights using subjects.difficulty
    user_priorities = preferences.get("priorities", {})
    subject_weights = {}

    for sub in subjects:
        code = sub['code']
        sub_id = sub['subject_id']
        diff = sub.get('difficulty', 'Medium')

        # Difficulty weighting: Hard=4, Medium=2, Easy=1
        if diff == 'Hard':
            base_weight = 4
        elif diff == 'Medium':
            base_weight = 2
        else:
            base_weight = 1

        # Priority boost
        pri = user_priorities.get(code, "").capitalize()
        if pri == "High":
            base_weight += 2
        elif pri == "Low":
            base_weight = max(1, base_weight - 1)

        # Exam date checks
        exam_date_obj = None
        days_to_exam = None
        if code in exam_by_code:
            try:
                exam_date_obj = datetime.datetime.strptime(exam_by_code[code], "%Y-%m-%d").date()
                if exam_date_obj >= today:
                    days_to_exam = (exam_date_obj - today).days
                    if days_to_exam <= 7:
                        base_weight += 4  # Front-load before exam
                    elif days_to_exam <= 14:
                        base_weight += 2
            except (ValueError, TypeError):
                pass

        subject_weights[sub_id] = {
            "code": code,
            "name": sub['name'],
            "difficulty": diff,
            "weight": base_weight,
            "exam_date_obj": exam_date_obj,
            "days_to_exam": days_to_exam
        }

    # Urgent assignments boost (due <= 3 days)
    for a in pending_assignments:
        if a.get('due_date'):
            try:
                ad = datetime.datetime.strptime(a['due_date'], "%Y-%m-%d").date()
                days_left = (ad - today).days
                if 0 <= days_left <= 3 and a.get('subject_id') in subject_weights:
                    subject_weights[a['subject_id']]['weight'] += 2
                    subject_weights[a['subject_id']]['urgent_task'] = a.get('title')
            except Exception:
                pass

    # Sort subjects: high priority / hard difficulty first
    sorted_subjects = sorted(
        subject_weights.values(),
        key=lambda x: (x['days_to_exam'] if x['days_to_exam'] is not None else 999, -x['weight'])
    )

    # 6. Build schedule across next 7 days respecting limits, no session after exam, and timetable clash avoidance
    scheduled_slots = []
    total_requested_hours = 0.0
    total_scheduled_hours = 0.0

    standard_candidate_times = [
        ("16:00", "17:30"),
        ("18:00", "19:30"),
        ("20:00", "21:30"),
        ("21:45", "23:15")
    ]

    for day_offset in range(1, 8):
        current_day = today + datetime.timedelta(days=day_offset)
        day_str = current_day.strftime("%Y-%m-%d")
        day_name = current_day.strftime("%A")

        avail_hours = weekday_hours.get(day_name, 3.0)
        total_requested_hours += avail_hours
        day_scheduled_minutes = 0
        max_minutes = int(avail_hours * 60)

        busy = busy_slots.get(day_name, [])

        for start_str, end_str in standard_candidate_times:
            if day_scheduled_minutes + 90 > max_minutes:
                break

            sh, sm = map(int, start_str.split(':'))
            eh, em = map(int, end_str.split(':'))
            slot_start = sh * 60 + sm
            slot_end = eh * 60 + em

            # Check timetable conflict
            conflict = False
            for b_start, b_end in busy:
                if not (slot_end <= b_start or slot_start >= b_end):
                    conflict = True
                    break
            if conflict:
                continue

            # Pick suitable subject: must not be after its exam date!
            chosen_sub = None
            for s in sorted_subjects:
                if s['exam_date_obj'] and current_day > s['exam_date_obj']:
                    # Rule: No session after the subject's exam date!
                    continue
                chosen_sub = s
                break

            if not chosen_sub:
                continue

            topic = "Review core concepts & practice exercises"
            if chosen_sub.get("urgent_task"):
                topic = f"Assignment preparation: {chosen_sub['urgent_task']}"
            elif chosen_sub.get("days_to_exam") is not None and chosen_sub["days_to_exam"] <= 7:
                topic = f"Intensive Exam Revision ({chosen_sub['code']})"

            scheduled_slots.append({
                "subject_id": chosen_sub.get("subject_id"),
                "code": chosen_sub["code"],
                "name": chosen_sub["name"],
                "date": day_str,
                "start_time": start_str,
                "end_time": end_str,
                "topic": topic,
                "status": "Scheduled"
            })
            day_scheduled_minutes += 90
            total_scheduled_hours += 1.5

    unscheduled_hours = max(0.0, round(total_requested_hours - total_scheduled_hours, 1))

    return {
        "success": True,
        "weekly_slots_allocated": len(scheduled_slots),
        "scheduled_hours": total_scheduled_hours,
        "unscheduled_hours": unscheduled_hours,
        "study_plan": scheduled_slots,
        "details": subject_weights
    }

def save_study_slots(student_id, slots):
    """Saves study plan slots in one transaction, verifying persistence."""
    if not student_id:
        raise ValidationError("student_id is required.")
    if not slots or not isinstance(slots, list):
        raise ValidationError("No study slots provided to save.")

    saved_count = 0
    for slot in slots:
        sub_code = slot.get("code")
        slot_date = slot.get("date")
        start_time = slot.get("start_time")
        end_time = slot.get("end_time")
        topic = slot.get("topic", "Self-study session")

        if not slot_date or not re.match(r"^\d{4}-\d{2}-\d{2}$", slot_date):
            continue

        sub_row = execute_query(
            "SELECT id FROM subjects WHERE student_id = ? AND code = ?;",
            (student_id, sub_code),
            fetch_one=True
        )
        sub_id = sub_row['id'] if sub_row else None

        new_pid = execute_query(
            """INSERT INTO study_plans (student_id, subject_id, date, start_time, end_time, topic, status)
               VALUES (?, ?, ?, ?, ?, ?, 'Scheduled');""",
            (student_id, sub_id, slot_date, start_time, end_time, topic),
            commit=True
        )
        verify = execute_query("SELECT id FROM study_plans WHERE id = ? AND student_id = ?;", (new_pid, student_id), fetch_one=True)
        if verify:
            saved_count += 1

    if saved_count == 0:
        raise PersistenceError("No valid study sessions could be persisted to database.")

    return saved_count
