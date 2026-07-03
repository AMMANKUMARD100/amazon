from backend.agents.base_agent import BaseAgent

class AttendanceAgent(BaseAgent):
    """AttendanceAgent: Analyzes attendance stats, highlighting risks and calculating classes required/missable."""
    
    def run(self):
        """Processes attendance numbers. Returns structured JSON analysis."""
        attendance_stats = self.call_mcp_tool("calculateAttendance", method="POST")
        
        if not attendance_stats:
            return {"error": "NoAttendanceRecords", "message": "No attendance records found for this student."}
            
        summary = {
            "total_subjects": len(attendance_stats),
            "at_risk_subjects": 0,
            "overall_present": 0,
            "overall_total": 0,
            "overall_percentage": 0.0,
            "details": []
        }
        
        for subject in attendance_stats:
            present = subject["present"]
            absent = subject["absent"]
            total = subject["total_classes"]
            pct = subject["percentage"]
            
            summary["overall_present"] += present
            summary["overall_total"] += total
            
            # Advice synthesis
            advice = ""
            if pct < 75.0:
                summary["at_risk_subjects"] += 1
                classes_needed = subject["classes_needed_for_75"]
                advice = (
                    f"Warning: Attendance is below 75%. You must attend the next {classes_needed} consecutive "
                    f"classes to recover eligibility."
                )
            else:
                classes_can_miss = subject["classes_can_miss"]
                if classes_can_miss > 0:
                    advice = f"Safe: You are above 75%. You can afford to miss up to {classes_can_miss} classes."
                else:
                    advice = "Borderline: You are at 75%. Do not miss any upcoming classes."
                    
            subject_summary = subject.copy()
            subject_summary["advice"] = advice
            summary["details"].append(subject_summary)
            
        if summary["overall_total"] > 0:
            summary["overall_percentage"] = round((summary["overall_present"] / summary["overall_total"]) * 100, 2)
        else:
            summary["overall_percentage"] = 100.0
            
        # Overall status warning
        summary["status"] = "Good" if summary["overall_percentage"] >= 75.0 else "Needs Improvement"
        if summary["at_risk_subjects"] > 0:
            summary["status"] = "Academic Risk"
            
        return summary
