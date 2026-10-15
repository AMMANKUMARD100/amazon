# CampusMate AI – Amazon Developer Hackathon 2026 (Alexa+ Track)

## 📌 Project Overview & Origin Attribution

**CampusMate AI** is an intelligent student concierge and academic productivity assistant adapted and enhanced for the **Amazon Developer Hackathon 2026, Alexa+ Track**.

- **Repository:** [`AMMANKUMARD100/amazon`](https://github.com/AMMANKUMARD100/amazon.git)
- **Original Base Repository:** [`TechEra007/Capstone-Campusmate-AI`](https://github.com/TechEra007/Capstone-Campusmate-AI)
- **Original License:** MIT License (Copyright (c) 2026 CampusMate AI Contributors)
- **Hackathon Track:** Alexa+ Track
- **Simulation Disclaimer:** Implements an **Alexa+-style simulation plus an MCP-style tool registry and Amazon Bedrock agent loop**. This project simulates an Alexa+ assistant experience through structured card directives and voice responses. It does not claim official Amazon device certification or hardware integration.

---

## 🚀 Enhancements & Features Personally Added

The application was systematically re-architected across 6 progressive engineering stages:

### 1. Robust Security & Domain Service Layer (Stage 1)
- **Strict Session Authentication (`@login_required`):** Secured all task, exam, alexa, and mcp endpoints. Removed fallback logic that defaulted unauthenticated or admin requests to student ID 1. All student access is strictly scoped to the active session.
- **Dedicated Domain Services (`backend/services/`):** Replaced in-process HTTP self-calls with typed domain service modules (`task_service`, `exam_service`, `planner_service`, `attendance_service`, `schedule_service`, `dashboard_service`, `faq_service`, `chat_service`).
- **Typed Error Hierarchy:** Replaced silent `None` failures with typed exceptions (`ValidationError`, `NotFoundError`, `PersistenceError`, `AuthorizationError`).

### 2. Honest Data Model & Exam Persistence (Stage 2)
- **Non-Destructive Database Migrations:** Made `assignments.subject_id` nullable and added `created_at`/`updated_at`. Cleaned up mock `GEN` subjects without data loss.
- **Dedicated `exams` & `study_preferences` Tables:** Real database persistence for course exams and student daily available study hours (`0.0` - `12.0` hours).
- **Grounded Planner Engine:** Uses stored exams, difficulty ratings, pending tasks, and timetable clash avoidance. Hard boundary: will never schedule study sessions after an exam date. When inputs are missing, returns structured `needs_input` rather than inventing dates.

### 3. Unified Tool Registry (Stage 3)
- **Centralized Registry (`backend/tools/registry.py`):** Declares all 13 application capabilities with strict JSON schemas (`additionalProperties: False`):
  - `list_tasks`, `add_task`, `update_task`, `complete_task`, `delete_task`
  - `add_exam`, `list_exams`, `set_study_hours`
  - `generate_study_plan`, `save_study_plan`
  - `get_today_summary`, `get_attendance_summary`, `search_faq`
- **Ambiguity Detection:** Substring name matches that produce multiple candidate hits return ambiguity choices rather than acting destructively on the first result.
- **Short-Lived Confirmation Tokens:** Destructive actions (`delete_task`, `save_study_plan` when replacing existing sessions) generate a single-use confirmation token that must be verified before execution.

### 4. Real Agent Loop with Amazon Bedrock (Stage 4)
- **Amazon Bedrock Converse API (`backend/llm/bedrock_provider.py`):** Direct boto3 client calling the native Bedrock Converse API (`client.converse()`), converting tool registry schemas into Bedrock `toolConfig` format.
- **Multi-Iteration Tool Calling Loop (`backend/llm/agent_loop.py`):** Feeds tool execution results back to the model, capped at 5 iterations.
- **Voice-First System Persona:** Directs concise, natural, 1-2 sentence spoken responses free of markdown and raw JSON.
- **Deterministic Demo Provider (`backend/llm/demo_provider.py`):** 100% offline fallback when running without AWS credentials (`LLM_PROVIDER=demo`).

### 5. Multi-Turn Conversation History & Audit Traces (Stage 5)
- **Persistent Tables (`chat_sessions` & `chat_messages`):** Multi-turn history saved per student with strict cross-tenant isolation.
- **Audit Traces:** Every assistant response logs executed tool names, inputs, and results.
- **Interactive UI Panel:** Expandable "What the assistant did (Trace)" accordion inside `AlexaSimulator.jsx` lets students inspect real agent tool executions.

### 6. Dynamic Student Dashboard (Stage 6)
- **Real-Time Data Integration:** Replaced hardcoded exam counters with live queries from the `exams` table.
- **Instant Reactive Sync:** Executing voice actions or quick adds in the simulator automatically triggers dashboard metrics refresh.

---

## ⚙️ Configuration & Environment Variables

Create a `.env` file in the project root:

```env
FLASK_APP=backend/app.py
FLASK_ENV=development
SECRET_KEY=dev_secret_key_change_in_production_123456
DATABASE_PATH=backend/database/campusmate.db
PORT=5000
FRONTEND_URL=http://localhost:3000

# LLM Configuration (Amazon Bedrock)
LLM_PROVIDER=demo # Set to 'bedrock' to use Amazon Bedrock Converse API
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
AWS_REGION=us-east-1

# Required only if LLM_PROVIDER=bedrock:
# AWS_ACCESS_KEY_ID=your_access_key
# AWS_SECRET_ACCESS_KEY=your_secret_key
# AWS_SESSION_TOKEN=optional_session_token
```

---

## 🧪 Automated Test Suite

Run the full unit test suite from the repository root:

```bash
python -m unittest discover -s tests
```

### Test Coverage Highlights (40 Passing Tests):
- `test_security_isolation.py`: 401 unauthenticated enforcement and cross-student data boundaries.
- `test_stage2_data_model.py`: Exam CRUD, study preference boundaries, planner clash avoidance, and `needs_input` handling.
- `test_tool_registry.py`: Schema validation, rejection of extra arguments, duplicate name ambiguity, and confirmation tokens.
- `test_bedrock_and_agent_loop.py`: Bedrock Converse toolConfig conversion, mocked Converse multi-turn tool loops, iteration safety limits, and demo fallback.
- `test_stage5_chat_history.py`: Multi-turn session persistence, student isolation on message history, and audit traces.
- `test_alexa_and_tasks.py`: Task CRUD, deterministic Alexa simulation, and preference grounding.
- `test_mcp.py` & `test_agents.py`: Service-backed agent and MCP tool calculations.

---

## 🚀 Running the Application

### 1. Backend Server
```bash
# Install backend dependencies
pip install -r requirements.txt

# Run Flask backend
python backend/app.py
```
Backend API will be live at `http://127.0.0.1:5000`.

### 2. Frontend Development Server
```bash
cd frontend
npm install
npm run dev
```
Access the student portal at `http://localhost:3000`.  
**Demo Student Credentials:** `student` / `password123`  
**Demo Admin Credentials:** `admin` / `adminpassword123`
