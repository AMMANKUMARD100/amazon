import datetime
import re
from backend.database.connection import execute_query
from backend.services.exceptions import ValidationError, PersistenceError
from backend.services.attendance_service import calculate_attendance
from backend.services.task_service import list_tasks

def generate_study_plan(student_id, preferences=None):
    """Generates study schedule using user preferences, subjects, exam dates, daily hours, and tasks."""
    if not student_id:
        raise ValidationError("student_id is required.")

    if preferences is None:
        preferences = {}

    today = datetime.date.today()
    daily_hours = min(max(float(preferences.get("daily_hours", 3.0)), 1.0), 8.0)
    user_exam_dates = preferences.get("exam_dates", {})
    user_priorities = preferences.get("priorities", {})

    subjects_data = calculate_attendance(student_id)
    if not subjects_data:
        rows = execute_query(
            "SELECT id as subject_id, code, name, credits, difficulty FROM subjects WHERE student_id = ?;",
            (student_id,),
            fetch_all=True
        )
        subjects_data = [dict(r) for r in rows]

    if not subjects_data:
        raise ValidationError("No subjects available to plan study slots.")

    pending_assignments = list_tasks(student_id, status="Pending")

    subject_weights = {}
    for sub in subjects_data:
        code = sub['code']
        sub_id = sub['subject_id']
        credits = sub.get("credits", 3)

        base_weight = 2
        if credits >= 4:
            base_weight = 3
        elif credits <= 2:
            base_weight = 1

        custom_pri = user_priorities.get(code, "").capitalize()
        if custom_pri == "High":
            base_weight += 2
        elif custom_pri == "Low":
            base_weight = max(1, base_weight - 1)

        days_to_exam = None
        if code in user_exam_dates:
            exam_date_str = user_exam_dates[code]
            if re.match(r"^\d{4}-\d{2}-\d{2}$", str(exam_date_str)):
                try:
                    ed = datetime.datetime.strptime(exam_date_str, "%Y-%m-%d").date()
                    if ed >= today:
                        days_to_exam = (ed - today).days
                        if days_to_exam <= 7:
                            base_weight += 4
                        elif days_to_exam <= 14:
                            base_weight += 2
                except ValueError:
                    pass

        subject_weights[sub_id] = {
            "code": code,
            "name": sub['name'],
            "weight": base_weight,
            "days_to_exam": days_to_exam,
            "exam_date": user_exam_dates.get(code)
        }

    for assign in pending_assignments:
        due_date_str = assign.get('due_date')
        if due_date_str:
            try:
                due_date = datetime.datetime.strptime(due_date_str, "%Y-%m-%d").date()
                days_left = (due_date - today).days
                if 0 <= days_left <= 3:
                    sub_id = assign.get('subject_id')
                    if sub_id in subject_weights:
                        subject_weights[sub_id]['weight'] += 2
                        subject_weights[sub_id]['urgent_task'] = assign.get('title')
            except Exception:
                pass

    slots_per_day = max(1, int(daily_hours / 1.5))
    time_slot_templates = [
        ("16:00", "17:30"),
        ("18:00", "19:30"),
        ("20:00", "21:30"),
        ("21:45", "23:15")
    ]

    pool = []
    for sub_id, info in subject_weights.items():
        for _ in range(info['weight']):
            topic = "Core concept review and practice exercises"
            if info.get("urgent_task"):
                topic = f"Assignment preparation: {info['urgent_task']}"
            elif info.get("days_to_exam") is not None and info["days_to_exam"] <= 7:
                topic = f"Intensive Exam Revision (Exam in {info['days_to_exam']} days)"
            elif info.get("days_to_exam") is not None:
                topic = f"Exam preparation topic sprint ({info['exam_date']})"

            pool.append({
                "subject_id": sub_id,
                "code": info['code'],
                "name": info['name'],
                "topic": topic
            })

    scheduled_slots = []
    pool_idx = 0
    total_pool = len(pool)

    if total_pool > 0:
        for day_offset in range(1, 8):
            day = today + datetime.timedelta(days=day_offset)
            day_str = day.strftime("%Y-%m-%d")

            for slot_num in range(slots_per_day):
                template = time_slot_templates[slot_num % len(time_slot_templates)]
                selected = pool[pool_idx % total_pool]
                pool_idx += 1

                scheduled_slots.append({
                    "subject_id": selected["subject_id"],
                    "code": selected["code"],
                    "name": selected["name"],
                    "date": day_str,
                    "start_time": template[0],
                    "end_time": template[1],
                    "topic": selected["topic"],
                    "status": "Scheduled"
                })

    return {
        "success": True,
        "weekly_slots_allocated": len(scheduled_slots),
        "daily_target_hours": daily_hours,
        "study_plan": scheduled_slots,
        "subject_weights": subject_weights
    }

def save_study_slots(student_id, slots):
    """Saves study plan slots with validation and transaction persistence check."""
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
        if not sub_row:
            sub_row = execute_query("SELECT id FROM subjects WHERE student_id = ? LIMIT 1;", (student_id,), fetch_one=True)

        if sub_row:
            sub_id = sub_row["id"]
            new_pid = execute_query(
                "INSERT INTO study_plans (student_id, subject_id, date, start_time, end_time, topic, status) "
                "VALUES (?, ?, ?, ?, ?, ?, 'Scheduled');",
                (student_id, sub_id, slot_date, start_time, end_time, topic),
                commit=True
            )
            verify = execute_query("SELECT id FROM study_plans WHERE id = ? AND student_id = ?;", (new_pid, student_id), fetch_one=True)
            if verify:
                saved_count += 1

    if saved_count == 0:
        raise PersistenceError("No valid study sessions could be persisted to database.")

    return saved_count
