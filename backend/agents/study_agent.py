from backend.agents.base_agent import BaseAgent

class StudyAgent(BaseAgent):
    """StudyAgent: Examines courses and study plans to construct custom study habits advice."""
    
    def run(self):
        """Generates customized academic recommendations. Returns structured JSON."""
        subjects = self.call_mcp_tool("calculateAttendance", method="POST")
        dashboard = self.call_mcp_tool("getDashboard", method="POST")
        
        if not subjects:
            return {"recommendations": [], "techniques": []}
            
        recommendations = []
        
        # Heuristics:
        # 1. Evaluate general hours
        scheduled_hours = dashboard.get("scheduled_study_hours", 0) if dashboard else 0
        if scheduled_hours < 8:
            recommendations.append({
                "category": "Schedule Volume",
                "priority": "High",
                "message": (
                    f"You have scheduled only {scheduled_hours} hours of study this week. "
                    "We recommend scheduling at least 12-15 hours to maintain high academic progress."
                )
            })
            
        # 2. Evaluate course difficulty and attendance risks
        for sub in subjects:
            code = sub["code"]
            name = sub["name"]
            pct = sub["percentage"]
            credits = sub.get("credits", 3)
            
            # Identify courses with low attendance
            if pct < 75.0:
                recommendations.append({
                    "category": "Academic Recovery",
                    "priority": "Critical",
                    "message": (
                        f"Priority focus needed on {code} ({name}) due to low attendance ({pct}%). "
                        "Add at least 3-4 hours of revision sessions for this course this week."
                    )
                })
                
            # Identify high credit / high difficulty courses
            if credits >= 4:
                recommendations.append({
                    "category": "Rigorous Course Focus",
                    "priority": "Medium",
                    "message": (
                        f"{code} is a 4-credit course and has high structural complexity. "
                        "Ensure you schedule regular active recall exercises (flashcards or practice exams)."
                    )
                })
                
        # If things look perfect, add standard positive reinforcement
        if not recommendations:
            recommendations.append({
                "category": "Performance Status",
                "priority": "Low",
                "message": "Excellent work! Your weekly schedule and attendance look well balanced. Keep it up."
            })
            
        # Recommended techniques
        techniques = [
            {
                "name": "Pomodoro Technique",
                "description": "Study for 25 minutes, then take a 5-minute break. Repeat 4 times, then take a longer break.",
                "best_for": "Beating procrastination on difficult assignments."
            },
            {
                "name": "Active Recall & Spaced Repetition",
                "description": "Test yourself on key concepts instead of re-reading. Space reviews over 1, 3, and 7 days.",
                "best_for": "Preparing for midterms and math-heavy courses."
            },
            {
                "name": "Feynman Technique",
                "description": "Explain a topic to a hypothetical beginner in simple terms. Identify gaps in your explanation.",
                "best_for": "Understanding complex theoretical algorithms."
            }
        ]
        
        return {
            "scheduled_hours": scheduled_hours,
            "recommendations": recommendations,
            "techniques": techniques
        }
