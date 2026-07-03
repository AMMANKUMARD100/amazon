from backend.agents.base_agent import BaseAgent

class ReminderAgent(BaseAgent):
    """ReminderAgent: Aggregates schedule items for today and constructs brief reminder text outputs."""
    
    def run(self):
        """Fetches and processes today's schedule items. Returns structured JSON."""
        data = self.call_mcp_tool("todayReminder", method="POST")
        
        if not data:
            return {"date": "", "day": "", "reminders": []}
            
        reminders = []
        
        # 1. Process Timetable classes
        for c in data.get("classes", []):
            reminders.append({
                "type": "Class",
                "time": f"{c['start_time']} - {c['end_time']}",
                "title": f"Attend lecture for {c['code']} ({c['name']})",
                "detail": f"Location: Room {c['room']}"
            })
            
        # 2. Process Study plans
        for s in data.get("study_sessions", []):
            reminders.append({
                "type": "Study",
                "time": f"{s['start_time']} - {s['end_time']}",
                "title": f"Study session: {s['code']}",
                "detail": f"Topic: {s['topic']}"
            })
            
        # 3. Process Assignments due today or tomorrow
        for a in data.get("assignments_due", []):
            due_label = "today" if a['due_date'] == data['date'] else "tomorrow"
            reminders.append({
                "type": "Assignment",
                "time": "All Day",
                "title": f"Assignment due {due_label}: {a['code']} - {a['title']}",
                "detail": f"Priority: {a['priority']}"
            })
            
        return {
            "date": data.get("date"),
            "day": data.get("day"),
            "reminders": reminders,
            "counts": {
                "classes": len(data.get("classes", [])),
                "study": len(data.get("study_sessions", [])),
                "assignments": len(data.get("assignments_due", []))
            }
        }
