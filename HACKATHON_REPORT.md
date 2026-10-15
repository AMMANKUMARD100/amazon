# CampusMate AI – Amazon Developer Hackathon (Alexa+ Track)

## 📌 Project Overview & Origin Attribution

**CampusMate AI** is an intelligent student concierge and academic productivity assistant adapted and enhanced for the **Amazon Developer Hackathon, Alexa+ Track**.

- **Original Base Repository:** [`TechEra007/Capstone-Campusmate-AI`](https://github.com/TechEra007/Capstone-Campusmate-AI)
- **Original License:** MIT License (Copyright (c) 2026 CampusMate AI Contributors)
- **Hackathon Track:** Alexa+ Track (Simulated-Experience Approach)
- **Compliance Statement:** Complies with current official hackathon rules by implementing a **permitted Alexa+ simulated-experience approach** without making unfounded claims of official Amazon device integration or hardware certification.

---

## 🚀 Enhancements & Features Personally Added

The following capabilities were implemented on top of the original repository:

### 1. Conversational Assistant with Alexa+ Simulated Experience
- **Multimodal Conversational Simulator (`/api/alexa/simulate`):** Processes natural-language requests into structured Alexa response cards and speech outputs.
- **Deterministic Heuristic Demo Mode:** Provides 100% offline rule-based intent parsing and tool calling without requiring third-party API keys.
- **Secure Backend LLM Function Calling:** Supports Gemini/OpenAI-compatible APIs with function calling declarations (`list_tasks`, `add_task`, `complete_task`, `check_attendance`, `get_today_schedule`), keeping API credentials strictly isolated on the backend.

### 2. Comprehensive Task Management
- **Full CRUD Support (`/api/tasks/`):** List, add, edit, complete, and delete student tasks.
- **Strict Date Validation:** Validates ISO `YYYY-MM-DD` formats and rejects invalid dates.
- **Verified SQLite Persistence:** Validates that insertions and deletions are committed to SQLite before confirming success to the student.

### 3. Grounded Study Planner (No Invented Dates)
- **Inputs:** Incorporates user-supplied subjects, verified exam dates, daily available study hours (1.0 - 8.0h), and priority weighting.
- **Proximity Sprints:** Dynamically boosts revision weights for exams occurring within 7 to 14 days without hallucinating missing dates.
- **Persistence Verification:** Persists generated study slots in the database only upon explicit user confirmation and returns verified saved counts.

### 4. Agent Concurrency Safety & Execution Trace
- **Mediator Pattern Preservation:** Reuses the existing 8 specialized agents (`PlannerAgent`, `AttendanceAgent`, `AssignmentAgent`, `ReminderAgent`, `FAQAgent`, `DashboardAgent`, `StudyAgent`, `NotificationAgent`) via `AgentManager`.
- **Execution Tracing:** Every conversation interaction reports the exact executed agent/tool and execution mode in its metadata.

### 5. Modern Student Dashboard
- **Multimodal Alexa+ Assistant Simulator:** Integrated directly on the main dashboard with quick prompt chips, speech synthesis, and microphone toggle.
- **Interactive Today's Tasks:** Direct checkbox toggles and trash actions with instant optimistic state synchronization.
- **Real-Time Analytics:** Attendance by subject bar charts, upcoming exam badges, and credit-weighted Pomodoro study progress rings.

### 6. Reliability & Test Suite
- Automated unit test suite expanding from 12 to 15 tests, covering tool execution, intent parsing, date validation, and task persistence.

---

## ⚙️ Configuration & Running the Application

### 1. Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# (Optional) To use an external LLM for conversational tool calling, set:
# export GEMINI_API_KEY="your-api-key"
# If omitted, CampusMate AI automatically runs in Deterministic Demo Mode!

# Run the Flask backend
python backend/app.py
```
Backend will start at: `http://127.0.0.1:5000`

### 2. Running Automated Tests
```bash
python -m unittest discover -s tests
```
*Expected: 15 tests passing (`OK`).*

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Access the student dashboard at: `http://localhost:3000`  
Default student credentials: `student` / `password123`
