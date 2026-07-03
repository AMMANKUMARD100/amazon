import logging
from backend.agents.planner_agent import PlannerAgent
from backend.agents.attendance_agent import AttendanceAgent
from backend.agents.assignment_agent import AssignmentAgent
from backend.agents.reminder_agent import ReminderAgent
from backend.agents.faq_agent import FAQAgent
from backend.agents.dashboard_agent import DashboardAgent
from backend.agents.study_agent import StudyAgent
from backend.agents.notification_agent import NotificationAgent

logger = logging.getLogger('activity')

class AgentManager:
    """AgentManager: Central hub coordinating the execution of specialized agents (Google ADK style)."""
    
    def __init__(self, student_id=None):
        self.student_id = student_id
        # Initialize sub-agents
        self.planner_agent = PlannerAgent(student_id)
        self.attendance_agent = AttendanceAgent(student_id)
        self.assignment_agent = AssignmentAgent(student_id)
        self.reminder_agent = ReminderAgent(student_id)
        self.faq_agent = FAQAgent(student_id)
        self.dashboard_agent = DashboardAgent(student_id)
        self.study_agent = StudyAgent(student_id)
        self.notification_agent = NotificationAgent(student_id)

    def execute_agent(self, agent_name, payload=None):
        """Dispatches commands to a target agent and returns normalized structured JSON."""
        if payload is None:
            payload = {}
            
        logger.info(f"AgentManager: Dispatching task to {agent_name} for student_id: {self.student_id}")
        
        try:
            if agent_name == "PlannerAgent":
                return self.planner_agent.run()
                
            elif agent_name == "AttendanceAgent":
                return self.attendance_agent.run()
                
            elif agent_name == "AssignmentAgent":
                return self.assignment_agent.run()
                
            elif agent_name == "ReminderAgent":
                return self.reminder_agent.run()
                
            elif agent_name == "FAQAgent":
                query = payload.get("query", "")
                return self.faq_agent.run(query)
                
            elif agent_name == "DashboardAgent":
                return self.dashboard_agent.run()
                
            elif agent_name == "StudyAgent":
                return self.study_agent.run()
                
            elif agent_name == "NotificationAgent":
                return self.notification_agent.run()
                
            else:
                logger.warning(f"AgentManager: Received request for unrecognized agent: {agent_name}")
                return {"error": "UnknownAgent", "message": f"Agent {agent_name} does not exist."}
                
        except Exception as e:
            logger.error(f"AgentManager: Exception occurred during {agent_name} run: {e}", exc_info=True)
            return {"error": "AgentError", "message": f"Agent execution failed: {str(e)}"}
