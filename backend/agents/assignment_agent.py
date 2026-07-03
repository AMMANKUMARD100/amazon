import datetime
from backend.agents.base_agent import BaseAgent

class AssignmentAgent(BaseAgent):
    """AssignmentAgent: Evaluates academic tasks, categories urgency, and sorts by deadline proximity."""
    
    def run(self):
        """Processes all assignments. Returns structured JSON analysis."""
        assignments = self.call_mcp_tool("getAssignments", method="POST")
        
        if not assignments:
            return {"count": 0, "overdue": [], "urgent": [], "pending": [], "completed": []}
            
        today = datetime.date.today()
        
        groups = {
            "count": len(assignments),
            "overdue": [],
            "urgent": [],  # due in 0-2 days
            "pending": [], # due in > 2 days
            "completed": []
        }
        
        for a in assignments:
            status = a.get("status")
            if status == "Completed":
                groups["completed"].append(a)
                continue
                
            due_date_str = a.get("due_date")
            try:
                due_date = datetime.datetime.strptime(due_date_str, "%Y-%m-%d").date()
                days_left = (due_date - today).days
                
                a_copy = a.copy()
                a_copy["days_left"] = days_left
                
                if days_left < 0:
                    groups["overdue"].append(a_copy)
                elif days_left <= 2:
                    groups["urgent"].append(a_copy)
                else:
                    groups["pending"].append(a_copy)
            except Exception:
                groups["pending"].append(a)
                
        # Sort each list by days left / due date
        groups["overdue"].sort(key=lambda x: x.get("days_left", 0))
        groups["urgent"].sort(key=lambda x: x.get("days_left", 0))
        groups["pending"].sort(key=lambda x: x.get("days_left", 999))
        
        # Formulate study recommendations based on priorities
        focus_list = []
        for a in groups["overdue"]:
            focus_list.append(f"[OVERDUE] {a['code']} - {a['title']} (Was due: {a['due_date']})")
        for a in groups["urgent"]:
            focus_list.append(f"[URGENT] {a['code']} - {a['title']} (Due in {a['days_left']} days)")
        for a in groups["pending"]:
            if a.get("priority") == "High":
                focus_list.append(f"[HIGH PRIORITY] {a['code']} - {a['title']} (Due: {a['due_date']})")
                
        groups["focus_list"] = focus_list
        return groups
