from backend.agents.base_agent import BaseAgent
from backend.services.planner_service import generate_study_plan
from backend.services.exceptions import ValidationError

class PlannerAgent(BaseAgent):
    """PlannerAgent: Generates study schedules taking user-supplied subjects, exam dates,
    available daily study hours, priorities, and pending assignments without inventing dates.
    Delegates directly to planner_service.
    """
    def run(self, preferences=None):
        if not self.student_id:
            raise ValidationError("PlannerAgent requires a valid student_id.")
        return generate_study_plan(self.student_id, preferences)
