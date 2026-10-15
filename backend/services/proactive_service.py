"""Proactive Alert and Summary Service for CampusMate AI.

Provides rule-based proactive intelligence:
1. check_attendance_risk: Identifies courses below 75% or near the danger threshold.
2. check_deadline_conflicts: Detects assignments due within 48 hours or overlapping exams.
3. generate_weekly_summary: Consolidates academic health across tasks, attendance, study, and exams.
4. get_proactive_alerts: Synthesizes all alerts into a priority-ranked list.
"""

import datetime
from typing import Any, Dict, List, Optional

from backend.services.exceptions import ValidationError
from backend.services.attendance_service import calculate_attendance
from backend.services.task_service import list_tasks
from backend.services.exam_service import list_exams
from backend.services.dashboard_service import get_dashboard_summary


def check_attendance_risk(student_id: int) -> List[Dict[str, Any]]:
    """Identifies subjects where attendance is below 75% or approaching danger.
    
    Args:
        student_id: Target student ID.
        
    Returns:
        List of subject risk assessments sorted by severity and percentage.
    """
    if not student_id or not isinstance(student_id, int):
        raise ValidationError("Valid integer student_id is required.")

    stats = calculate_attendance(student_id)
    risks: List[Dict[str, Any]] = []

    for sub in stats:
        pct = sub.get("percentage", 100.0)
        total = sub.get("total_classes", 0)
        needed = sub.get("classes_needed_for_75", 0)
        can_miss = sub.get("classes_can_miss", 0)

        # Critical: Below 75% requirement
        if pct < 75.0:
            risks.append({
                "subject_id": sub.get("subject_id"),
                "code": sub.get("code"),
                "name": sub.get("name"),
                "percentage": pct,
                "status": "Critical",
                "severity": "High",
                "classes_needed_for_75": needed,
                "classes_can_miss": 0,
                "message": (
                    f"Critical attendance alert: {sub.get('code')} ({sub.get('name')}) is at {pct}%, "
                    f"below the required 75%. You must attend {needed} consecutive class(es) to restore eligibility."
                )
            })
        # Approaching danger: 75% <= pct < 80% or can only miss 1 or 0 classes
        elif total > 0 and (pct < 80.0 or can_miss <= 1):
            risks.append({
                "subject_id": sub.get("subject_id"),
                "code": sub.get("code"),
                "name": sub.get("name"),
                "percentage": pct,
                "status": "Warning",
                "severity": "Medium",
                "classes_needed_for_75": 0,
                "classes_can_miss": can_miss,
                "message": (
                    f"Attendance warning: {sub.get('code')} ({sub.get('name')}) is at {pct}%. "
                    f"You can only miss {can_miss} more class before falling below 75%."
                )
            })

    # Sort critical / high severity first, then lowest percentage
    risks.sort(key=lambda r: (0 if r["severity"] == "High" else 1, r["percentage"]))
    return risks


def check_deadline_conflicts(student_id: int) -> List[Dict[str, Any]]:
    """Identifies assignments due within 48 hours and those overlapping with exams.
    
    Args:
        student_id: Target student ID.
        
    Returns:
        List of conflict records sorted by urgency and due date.
    """
    if not student_id or not isinstance(student_id, int):
        raise ValidationError("Valid integer student_id is required.")

    tasks = list_tasks(student_id, status="Pending")
    exams = list_exams(student_id)

    today = datetime.date.today()
    conflicts: List[Dict[str, Any]] = []

    for task in tasks:
        due_str = task.get("due_date")
        if not due_str:
            continue

        try:
            due_date = datetime.date.fromisoformat(due_str)
        except ValueError:
            continue

        days_until_due = (due_date - today).days

        # Check for overlapping exams:
        # An exam is in direct conflict if it takes place within 2 days (48 hours) of the assignment deadline.
        overlapping_exams = []
        for exam in exams:
            exam_str = exam.get("exam_date")
            if not exam_str:
                continue
            try:
                exam_date = datetime.date.fromisoformat(exam_str)
            except ValueError:
                continue

            diff = abs((exam_date - due_date).days)
            if diff <= 2:
                overlapping_exams.append(exam)

        if overlapping_exams:
            for ex in overlapping_exams:
                conflicts.append({
                    "task_id": task.get("id"),
                    "task_title": task.get("title"),
                    "due_date": due_str,
                    "subject_code": task.get("code"),
                    "conflict_type": "exam_overlap",
                    "severity": "High",
                    "exam_id": ex.get("id"),
                    "exam_title": ex.get("title"),
                    "exam_date": ex.get("exam_date"),
                    "message": (
                        f"Deadline conflict: Assignment '{task.get('title')}' is due on {due_str}, "
                        f"overlapping with exam '{ex.get('title')}' on {ex.get('exam_date')}."
                    )
                })
        elif 0 <= days_until_due <= 2:
            # Imminent deadline within 48 hours
            conflicts.append({
                "task_id": task.get("id"),
                "task_title": task.get("title"),
                "due_date": due_str,
                "subject_code": task.get("code"),
                "conflict_type": "urgent_deadline",
                "severity": "High" if task.get("priority") == "High" else "Medium",
                "exam_id": None,
                "exam_title": None,
                "exam_date": None,
                "message": (
                    f"Upcoming deadline: Assignment '{task.get('title')}' is due on {due_str} "
                    f"({'today' if days_until_due == 0 else 'tomorrow' if days_until_due == 1 else 'in 2 days'})."
                )
            })
        elif days_until_due < 0:
            # Overdue task
            conflicts.append({
                "task_id": task.get("id"),
                "task_title": task.get("title"),
                "due_date": due_str,
                "subject_code": task.get("code"),
                "conflict_type": "overdue",
                "severity": "High",
                "exam_id": None,
                "exam_title": None,
                "exam_date": None,
                "message": f"Overdue assignment: '{task.get('title')}' was due on {due_str}."
            })

    # Sort high severity first, then chronologically by due date
    conflicts.sort(key=lambda c: (0 if c["severity"] == "High" else 1, c["due_date"]))
    return conflicts


def generate_weekly_summary(student_id: int) -> Dict[str, Any]:
    """Summarizes weekly performance: tasks completed vs pending, attendance trend, study hours, upcoming exams.
    
    Args:
        student_id: Target student ID.
        
    Returns:
        Structured summary dictionary.
    """
    if not student_id or not isinstance(student_id, int):
        raise ValidationError("Valid integer student_id is required.")

    dashboard = get_dashboard_summary(student_id)
    all_tasks = list_tasks(student_id)
    attendance_stats = calculate_attendance(student_id)
    all_exams = list_exams(student_id)

    today = datetime.date.today()
    week_end = today + datetime.timedelta(days=7)

    # 1. Task metrics
    completed_count = sum(1 for t in all_tasks if t.get("status") == "Completed")
    pending_count = sum(1 for t in all_tasks if t.get("status") == "Pending")
    total_tasks = completed_count + pending_count
    completion_rate = round((completed_count / total_tasks * 100), 1) if total_tasks > 0 else 100.0

    urgent_tasks = []
    for t in all_tasks:
        if t.get("status") == "Pending" and t.get("due_date"):
            try:
                d = datetime.date.fromisoformat(t["due_date"])
                if today <= d <= week_end:
                    urgent_tasks.append(t)
            except ValueError:
                pass

    # 2. Attendance metrics
    at_risk = [sub for sub in attendance_stats if sub.get("percentage", 100.0) < 75.0]
    total_pct = sum(sub.get("percentage", 0) for sub in attendance_stats)
    avg_attendance = round(total_pct / len(attendance_stats), 1) if attendance_stats else 100.0

    # 3. Upcoming exams this week
    upcoming_exams_this_week = []
    for ex in all_exams:
        if ex.get("exam_date"):
            try:
                ed = datetime.date.fromisoformat(ex["exam_date"])
                if today <= ed <= week_end:
                    upcoming_exams_this_week.append(ex)
            except ValueError:
                pass

    study_hours = dashboard.get("scheduled_study_hours", 0.0)

    # Narrative spoken summary
    summary_sentence = (
        f"This week you have completed {completed_count} of {total_tasks} tasks. "
        f"You have {pending_count} pending tasks, {study_hours} scheduled study hours, "
        f"and your overall attendance is at {avg_attendance} percent."
    )
    if at_risk:
        summary_sentence += f" Caution: {len(at_risk)} subject(s) are below 75 percent attendance."

    return {
        "student_id": student_id,
        "student_name": dashboard.get("student_name", "Student"),
        "cgpa": dashboard.get("cgpa", 0.0),
        "tasks": {
            "completed": completed_count,
            "pending": pending_count,
            "total": total_tasks,
            "completion_rate": completion_rate,
            "due_this_week_count": len(urgent_tasks),
            "due_this_week": urgent_tasks
        },
        "attendance": {
            "overall_percentage": avg_attendance,
            "total_subjects": len(attendance_stats),
            "at_risk_count": len(at_risk),
            "at_risk_subjects": [{"code": s.get("code"), "percentage": s.get("percentage")} for s in at_risk]
        },
        "study": {
            "scheduled_hours": study_hours
        },
        "exams": {
            "upcoming_this_week_count": len(upcoming_exams_this_week),
            "upcoming_this_week": upcoming_exams_this_week
        },
        "summary_text": summary_sentence
    }


def get_proactive_alerts(student_id: int) -> List[Dict[str, Any]]:
    """Combines all alerts into a priority-sorted list.
    
    Priority levels:
    - High (Rank 1): Attendance <75%, Exam overlaps, Overdue assignments, Exams <=3 days away.
    - Medium (Rank 2): Attendance 75-80% / low buffer, Tasks due within 48h, Exams <=7 days away.
    - Low (Rank 3): Upcoming general reminders, Study recommendations.
    
    Args:
        student_id: Target student ID.
        
    Returns:
        List of alert dicts sorted by priority_rank ascending.
    """
    if not student_id or not isinstance(student_id, int):
        raise ValidationError("Valid integer student_id is required.")

    alerts: List[Dict[str, Any]] = []
    today = datetime.date.today()

    # 1. Attendance alerts
    attendance_risks = check_attendance_risk(student_id)
    for risk in attendance_risks:
        rank = 1 if risk["severity"] == "High" else 2
        alerts.append({
            "id": f"attendance_{risk['code']}",
            "type": "attendance_risk",
            "priority": risk["severity"],
            "priority_rank": rank,
            "title": f"Attendance Risk: {risk['code']}",
            "message": risk["message"],
            "metadata": {
                "code": risk["code"],
                "percentage": risk["percentage"],
                "status": risk["status"]
            }
        })

    # 2. Deadline conflict alerts
    deadline_conflicts = check_deadline_conflicts(student_id)
    for conf in deadline_conflicts:
        rank = 1 if conf["severity"] == "High" else 2
        alerts.append({
            "id": f"task_{conf['task_id']}_{conf['conflict_type']}",
            "type": conf["conflict_type"],
            "priority": conf["severity"],
            "priority_rank": rank,
            "title": f"{'Exam Conflict' if conf['conflict_type'] == 'exam_overlap' else 'Urgent Deadline' if conf['conflict_type'] == 'urgent_deadline' else 'Overdue Task'}: {conf['task_title']}",
            "message": conf["message"],
            "metadata": {
                "task_id": conf["task_id"],
                "task_title": conf["task_title"],
                "due_date": conf["due_date"],
                "exam_date": conf.get("exam_date")
            }
        })

    # 3. Upcoming exam alerts (exams within next 7 days)
    exams = list_exams(student_id)
    for ex in exams:
        ex_date_str = ex.get("exam_date")
        if not ex_date_str:
            continue
        try:
            ex_date = datetime.date.fromisoformat(ex_date_str)
            days_left = (ex_date - today).days
            if 0 <= days_left <= 7:
                rank = 1 if days_left <= 3 else 2
                severity = "High" if days_left <= 3 else "Medium"
                time_desc = "today" if days_left == 0 else "tomorrow" if days_left == 1 else f"in {days_left} days"
                alerts.append({
                    "id": f"exam_{ex['id']}",
                    "type": "upcoming_exam",
                    "priority": severity,
                    "priority_rank": rank,
                    "title": f"Upcoming Exam: {ex['title']}",
                    "message": f"Exam alert: '{ex['title']}' ({ex.get('code', 'GEN')}) is scheduled for {ex_date_str} ({time_desc}).",
                    "metadata": {
                        "exam_id": ex["id"],
                        "exam_title": ex["title"],
                        "exam_date": ex_date_str,
                        "days_left": days_left
                    }
                })
        except ValueError:
            pass

    # Sort alerts: Rank 1 (High) first, then Rank 2 (Medium), then Rank 3 (Low)
    alerts.sort(key=lambda a: (a["priority_rank"], a["title"]))
    return alerts
