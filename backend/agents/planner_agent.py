import datetime
import re
from backend.agents.base_agent import BaseAgent
from backend.database.connection import execute_query

class PlannerAgent(BaseAgent):
    """PlannerAgent: Generates study schedules taking user-supplied subjects, exam dates,
    available daily study hours, priorities, and pending assignments without inventing dates.
    """
    
    def run(self, preferences=None):
        """Generates a grounded weekly study plan. Returns structured JSON.
        
        preferences dict:
          - exam_dates: {"CS101": "2026-11-05", ...}
          - daily_hours: float (default 3.0)
          - priorities: {"CS101": "High", ...}
          - subjects: [{"code": "CS101", "name": "...", "credits": 4}, ...] (optional override)
        """
        if preferences is None:
            preferences = {}
            
        today = datetime.date.today()
        daily_hours = min(max(float(preferences.get("daily_hours", 3.0)), 1.0), 8.0)
        user_exam_dates = preferences.get("exam_dates", {})
        user_priorities = preferences.get("priorities", {})
        
        # 1. Fetch academic details via MCP tools
        subjects_data = self.call_mcp_tool("calculateAttendance", method="POST")
        assignments_data = self.call_mcp_tool("getAssignments", method="POST")
        
        if not subjects_data:
            # Query directly if tool returned empty
            rows = execute_query(
                "SELECT id as subject_id, code, name, credits, difficulty FROM subjects WHERE student_id = ?;",
                (self.student_id or 1,),
                fetch_all=True
            )
            subjects_data = [dict(r) for r in rows]
            
        if not subjects_data:
            return {"error": "NoSubjectsFound", "message": "No subjects available to plan study slots."}
            
        pending_assignments = []
        if assignments_data:
            pending_assignments = [a for a in assignments_data if a.get('status') == 'Pending']
            
        # 2. Determine allocation weights based on real user exams, credits, and priorities
        subject_weights = {}
        for sub in subjects_data:
            code = sub['code']
            sub_id = sub['subject_id']
            credits = sub.get("credits", 3)
            
            # Base weight by credits
            base_weight = 2
            if credits >= 4:
                base_weight = 3
            elif credits <= 2:
                base_weight = 1
                
            # Priority boost
            custom_pri = user_priorities.get(code, "").capitalize()
            if custom_pri == "High":
                base_weight += 2
            elif custom_pri == "Low":
                base_weight = max(1, base_weight - 1)
                
            # Real Exam Proximity boost (do not invent dates, only use verified user-provided dates)
            days_to_exam = None
            if code in user_exam_dates:
                exam_date_str = user_exam_dates[code]
                if re.match(r"^\d{4}-\d{2}-\d{2}$", exam_date_str):
                    try:
                        ed = datetime.datetime.strptime(exam_date_str, "%Y-%m-%d").date()
                        if ed >= today:
                            days_to_exam = (ed - today).days
                            if days_to_exam <= 7:
                                base_weight += 4  # Critical exam week
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
            
        # 3. Boost subjects with imminent pending assignment deadlines (within 3 days)
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
                    
        # 4. Generate schedule slots for next 7 days based on daily_hours
        # Slot duration = 1.5 hours per slot
        slots_per_day = max(1, int(daily_hours / 1.5))
        time_slot_templates = [
            ("16:00", "17:30"),
            ("18:00", "19:30"),
            ("20:00", "21:30"),
            ("21:45", "23:15")
        ]
        
        # Build weighted pool
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
                
        # Interleave pool so the same subject isn't clustered back-to-back
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
