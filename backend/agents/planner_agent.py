import datetime
from backend.agents.base_agent import BaseAgent

class PlannerAgent(BaseAgent):
    """PlannerAgent: Rule-based study scheduler allocating slots by difficulty and assignment deadlines."""
    
    def run(self):
        """Generates a weekly study plan. Returns structured JSON."""
        # 1. Fetch academic details via MCP tools
        subjects_data = self.call_mcp_tool("calculateAttendance", method="POST")
        assignments_data = self.call_mcp_tool("getAssignments", method="POST")
        
        if not subjects_data:
            return {"error": "NoSubjectsFound", "message": "No subjects available to plan study slots."}
            
        pending_assignments = []
        if assignments_data:
            pending_assignments = [a for a in assignments_data if a['status'] == 'Pending']
            
        # 2. Determine study allocation weights based on difficulty
        # Hard = 4 slots, Medium = 2 slots, Easy = 1 slot per week
        slots_needed = {}
        for sub in subjects_data:
            code = sub['code']
            sub_id = sub['subject_id']
            # Find difficulty
            # We fetch difficulty by matching subjects data. Since calculateAttendance returns credits,
            # let's assume we map credits or look up subjects database info via MCP.
            # To be precise, let's fetch subjects using a simple query inside MCP or standard calculation.
            # In calculateAttendance, we have subject_id and code. Let's find difficulty.
            # Wait, calculateAttendance has difficulty? No, it has credits.
            # Let's map difficulty using credit weight: 4 credits -> Hard (4 slots), 3 credits -> Medium (2 slots).
            # Alternatively, we can assume a difficulty scale: credits >= 4 is Hard, credits == 3 is Medium, credits < 3 is Easy.
            credits = sub.get("credits", 3)
            difficulty = "Medium"
            if credits >= 4:
                difficulty = "Hard"
            elif credits < 3:
                difficulty = "Easy"
                
            slots_needed[sub_id] = {
                "code": code,
                "name": sub['name'],
                "count": 4 if difficulty == "Hard" else (2 if difficulty == "Medium" else 1),
                "difficulty": difficulty
            }
            
        # 3. Boost slots for subjects with tight assignment deadlines (due in <= 3 days)
        today = datetime.date.today()
        for assign in pending_assignments:
            due_date_str = assign['due_date']
            try:
                due_date = datetime.datetime.strptime(due_date_str, "%Y-%m-%d").date()
                days_left = (due_date - today).days
                if 0 <= days_left <= 3:
                    sub_id = assign['subject_id']
                    if sub_id in slots_needed:
                        slots_needed[sub_id]['count'] += 2  # Add 2 emergency slots
                        slots_needed[sub_id]['urgent_assignment'] = assign['title']
            except Exception:
                pass
                
        # 4. Generate schedule slots for the next 7 days (starting tomorrow)
        study_plan = []
        days_to_plan = 7
        available_days = [(today + datetime.timedelta(days=i)) for i in range(1, days_to_plan + 1)]
        
        # Standard study times: 17:00-19:00 and 20:00-22:00
        time_slots = [
            ("17:00", "18:30"),
            ("20:00", "21:30")
        ]
        
        # Flatten slots needed into a pool
        slot_pool = []
        for sub_id, info in slots_needed.items():
            for _ in range(info['count']):
                topic = "Practice problems"
                if info.get("urgent_assignment"):
                    topic = f"Work on assignment: {info['urgent_assignment']}"
                elif info['difficulty'] == "Hard":
                    topic = "Deep review of core concepts and formulas"
                else:
                    topic = "Review notes and textbook readings"
                
                slot_pool.append({
                    "subject_id": sub_id,
                    "code": info['code'],
                    "name": info['name'],
                    "topic": topic
                })
                
        # Distribute pool items across available days & times
        slot_idx = 0
        pool_len = len(slot_pool)
        
        for day in available_days:
            if slot_idx >= pool_len:
                break
                
            day_str = day.strftime("%Y-%m-%d")
            day_name = day.strftime("%A")
            
            # Skip Saturday/Sunday nights if user wants (we will allow weekends but less slots)
            active_time_slots = time_slots if day_name not in ["Saturday", "Sunday"] else [("10:00", "11:30")]
            
            for start, end in active_time_slots:
                if slot_idx >= pool_len:
                    break
                    
                allocated = slot_pool[slot_idx]
                study_plan.append({
                    "subject_id": allocated["subject_id"],
                    "code": allocated["code"],
                    "name": allocated["name"],
                    "date": day_str,
                    "start_time": start,
                    "end_time": end,
                    "topic": allocated["topic"],
                    "status": "Scheduled"
                })
                slot_idx += 1
                
        return {
            "success": True,
            "weekly_slots_allocated": len(study_plan),
            "study_plan": study_plan,
            "details": slots_needed
        }
