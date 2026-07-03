import datetime
from backend.agents.base_agent import BaseAgent
from backend.database.connection import execute_query

class NotificationAgent(BaseAgent):
    """NotificationAgent: Periodically monitors academic boundaries and queues alert records."""
    
    def run(self):
        """Scans database states and inserts necessary system notifications. Returns a summary of findings."""
        # 1. Fetch data through MCP tools
        attendance = self.call_mcp_tool("calculateAttendance", method="POST")
        assignments = self.call_mcp_tool("getAssignments", method="POST")
        
        alerts_queued = 0
        notifications_list = []
        
        # Avoid creating duplicate warnings for the same day
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        
        # 2. Check for low attendance (Alerts)
        if attendance:
            for item in attendance:
                pct = item["percentage"]
                if pct < 75.0:
                    code = item["code"]
                    title = f"Low Attendance Warning: {code}"
                    msg = f"Your attendance in {code} is at {pct}%. You need to attend {item['classes_needed_for_75']} consecutive classes to reach 75%."
                    notifications_list.append({"title": title, "message": msg, "type": "Alert"})
                    
        # 3. Check for upcoming assignments due in <= 2 days (Reminders)
        if assignments:
            today = datetime.date.today()
            for a in assignments:
                if a["status"] == "Pending":
                    due_date_str = a["due_date"]
                    try:
                        due_date = datetime.datetime.strptime(due_date_str, "%Y-%m-%d").date()
                        days_left = (due_date - today).days
                        if 0 <= days_left <= 2:
                            code = a.get("code", "Course")
                            title = f"Upcoming Deadline: {a['title']}"
                            msg = f"The assignment for {code} is due in {days_left} days ({a['due_date']}). Status: Pending."
                            notifications_list.append({"title": title, "message": msg, "type": "Reminder"})
                    except Exception:
                        pass
                        
        # 4. Insert notifications into DB (safe parameterized query)
        # Verify if similar notification was already created today to avoid duplicates
        for note in notifications_list:
            # Check for existing warning today
            existing = execute_query(
                "SELECT id FROM notifications WHERE student_id = ? AND title = ? AND DATE(created_at) = ?;",
                (self.student_id, note["title"], today_str),
                fetch_one=True
            )
            if not existing:
                try:
                    execute_query(
                        "INSERT INTO notifications (student_id, title, message, type, is_read) VALUES (?, ?, ?, ?, 0);",
                        (self.student_id, note["title"], note["message"], note["type"]),
                        commit=True
                    )
                    alerts_queued += 1
                except Exception as e:
                    # Ignore db errors during notification queues
                    pass
                    
        return {
            "success": True,
            "checked_at": today_str,
            "alerts_queued": alerts_queued,
            "found_notifications": len(notifications_list)
        }
