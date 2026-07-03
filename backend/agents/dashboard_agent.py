from backend.agents.base_agent import BaseAgent

class DashboardAgent(BaseAgent):
    """DashboardAgent: Formats raw data into structured chart-ready configurations for React visualization."""
    
    def run(self):
        """Prepares dashboard structures. Returns structured JSON."""
        summary = self.call_mcp_tool("getDashboard", method="POST")
        attendance_detail = self.call_mcp_tool("calculateAttendance", method="POST")
        
        if not summary:
            return {"error": "DashboardQueryFailed", "message": "Failed to retrieve student dashboard summaries."}
            
        # 1. Structure Attendance chart data
        # Labels: Subject Codes, Dataset: Attendance Percentages
        att_labels = []
        att_values = []
        att_colors = []  # Red if low (<75), Blue if good
        
        if attendance_detail:
            for item in attendance_detail:
                att_labels.append(item["code"])
                att_values.append(item["percentage"])
                att_colors.append("#ef4444" if item["percentage"] < 75.0 else "#3b82f6")
                
        # 2. Structure Assignment completion chart data
        assignment_chart = {
            "labels": ["Pending", "Completed"],
            "data": [
                summary.get("pending_assignments", 0),
                summary.get("completed_assignments", 0)
            ],
            "colors": ["#f59e0b", "#10b981"]  # Amber, Emerald
        }
        
        # 3. Structure Study Hours target details
        # Target = 15 hours per week
        weekly_target = 15.0
        scheduled = summary.get("scheduled_study_hours", 0.0)
        study_completion_pct = min(100.0, round((scheduled / weekly_target) * 100, 1)) if weekly_target > 0 else 100.0
        
        study_progress = {
            "weekly_target": weekly_target,
            "scheduled_hours": scheduled,
            "completion_percentage": study_completion_pct,
            "labels": ["Scheduled Hours", "Remaining Target"],
            "data": [scheduled, max(0.0, weekly_target - scheduled)],
            "colors": ["#6366f1", "#e5e7eb"]  # Indigo, Light Gray
        }
        
        return {
            "student_name": summary.get("student_name"),
            "matric_number": summary.get("matric_number"),
            "cgpa": summary.get("cgpa"),
            "metrics": {
                "overall_attendance": summary.get("overall_attendance"),
                "pending_assignments": summary.get("pending_assignments"),
                "completed_assignments": summary.get("completed_assignments"),
                "scheduled_study_hours": summary.get("scheduled_study_hours")
            },
            "charts": {
                "attendance": {
                    "labels": att_labels,
                    "data": att_values,
                    "colors": att_colors
                },
                "assignments": assignment_chart,
                "study_progress": study_progress
            }
        }
