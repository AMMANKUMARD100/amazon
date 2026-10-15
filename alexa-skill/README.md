# CampusMate AI – Alexa+ Agent Skill Architecture

This document explains how **CampusMate AI** maps to Amazon's **Alexa+ Agent Framework** and the **Alexa Skills Kit (ASK)**, evolving traditional voice skills into an autonomous, tool-calling academic concierge.

---

## 🌟 The Paradigm Shift: Classic Alexa Skills vs. Alexa+ Agent Skills

| Dimension | Classic Alexa Skills (ASK 2.0) | Alexa+ Agent Skills (CampusMate AI) |
| :--- | :--- | :--- |
| **Interaction Model** | Rigid Intent ➔ Slot ➔ Lambda mapping | Goal-oriented LLM orchestration with reasoning |
| **Execution Flow** | Single intent executed per turn | **Multi-step autonomous tool chaining** (e.g. *Plan my evening*) |
| **Capability Registry** | Hardcoded intent handlers in code | **Unified MCP Tool Registry** exposing JSON schemas |
| **Multi-turn Context** | Manual session attribute book-keeping | Dynamic conversational memory and ambiguity resolution |
| **Destructive Actions** | Inflexible slot confirmation dialogs | Cryptographic confirmation tokens (`create_confirmation_token`) |
| **Integration Protocol** | Proprietary ASK request/response envelopes | **Model Context Protocol (MCP)** / Streamable HTTP standard |

---

## 🏛️ System Architecture

```
       ┌────────────────────────────────────────────────────────┐
       │                 User Spoken Utterance                  │
       │           "Alexa, plan my evening for me"              │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │             Alexa+ Conversational Engine               │
       │       (LLM Agent Loop / Claude 3 Haiku on Bedrock)     │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 │    Autonomous Agent Reasoning   │
                 │   Evaluates Goals & Tool Need   │
                 └────────────────┬────────────────┘
                                  │
           ┌──────────────────────┼──────────────────────┐
           │                      │                      │
           ▼                      ▼                      ▼
    Step 1: Agenda         Step 2: Tasks          Step 3: Planner
   ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
   │daily_briefing │      │  list_tasks   │      │generate_study_│
   │               │      │               │      │     plan      │
   └───────┬───────┘      └───────┬───────┘      └───────┬───────┘
           │                      │                      │
           └──────────────────────┼──────────────────────┘
                                  │
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │             CampusMate Unified Tool Registry           │
       │               (backend/tools/registry.py)              │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │                  SQLite Database Layer                 │
       │    (Timetable, Courses, Attendance, Tasks, Exams)      │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │             Spoken Natural Voice Synthesis             │
       │   "Here is your evening plan: You've finished your     │
       │   classes. You have 2 assignments due, and I have      │
       │   scheduled study blocks for Data Structures and DBMS." │
       └────────────────────────────────────────────────────────┘
```

---

## 🗺️ Intent & Tool Mapping Matrix

CampusMate AI exposes **13 high-impact academic tools** registered in `backend/tools/registry.py` and reflected in `alexa-skill/skill.json`:

| Skill Intent | Sample Utterances | Mapped MCP Tool | Tool Arguments | Spoken Voice Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `DailyBriefingIntent` | *"What's my daily briefing?"*, *"Good morning"*, *"What do I have today?"* | `daily_briefing` / `get_today_summary` | `{ student_id: int }` | Briefs the student in 1-2 spoken sentences with today's lectures, classroom locations, and urgent deadlines. |
| `ListTasksIntent` | *"What assignments are due?"*, *"List my tasks"*, *"What homework do I have?"* | `list_tasks` | `{ student_id: int, status: "Pending" }` | Summarizes urgent and pending assignments, high-priority tags, and due dates. |
| `AddTaskIntent` | *"Add task Data Structures lab due tomorrow"*, *"Remind me to submit project"* | `add_task` | `{ student_id: int, title: str, due_date: YYYY-MM-DD, priority: str }` | Parses title and due date. **If date is omitted, prompts the student naturally** without inventing deadlines. |
| `CompleteTaskIntent` | *"Mark task 3 done"*, *"Complete assignment Algorithms homework"* | `complete_task` | `{ student_id: int, task_id?: int, task_title?: str }` | Marks assignment completed. Disambiguates if multiple match by returning candidate IDs. |
| `DeleteTaskIntent` | *"Delete task 2"*, *"Remove assignment 5"* | `delete_task` | `{ student_id: int, task_id?: int, confirm_token?: str }` | **Destructive operation**: Issues a 5-minute confirmation token and prompts *"Are you sure? Say 'confirm token <token>' to proceed."* |
| `GetAttendanceIntent` | *"How is my attendance?"*, *"Can I skip class today?"*, *"Am I safe in attendance?"* | `get_attendance_summary` | `{ student_id: int }` | Audits attendance percentages against university 75% cutoff and warns if attendance is in danger. |
| `GetScheduleIntent` | *"What's my timetable?"*, *"What classes do I have on Friday?"* | `get_timetable` | `{ student_id: int, day?: str }` | Retrieves scheduled lectures, start/end times, and room assignments. |
| `GenerateStudyPlanIntent`| *"Generate a study plan"*, *"Create a study schedule for 3 hours"* | `generate_study_plan` | `{ student_id: int, daily_hours: float }` | Generates balanced study slots factoring in course credits, difficulty ratings, and upcoming exams. |
| `PlanMyDayIntent` | *"Plan my evening"*, *"Plan my day"*, *"What should I focus on tonight?"* | `daily_briefing` + `list_tasks` + `generate_study_plan` | Multi-step agent chain | Sequences multiple tools: checks today's schedule, audits pending tasks, generates an evening study block, and returns a unified synthesis. |
| `CalculateCGPAIntent` | *"What is my CGPA?"*, *"Show my grade point average"* | `calculate_cgpa` | `{ student_id: int }` | Calculates credit-weighted GPA and projected performance. |
| `ListExamsIntent` | *"When are my exams?"*, *"Upcoming test schedule"* | `list_exams` | `{ student_id: int }` | Lists scheduled midterm and final exam dates with subject codes. |
| `SearchFAQIntent` | *"What is the hostel curfew policy?"*, *"Library hours"* | `search_faq` | `{ query: str }` | Searches local campus policies and academic guidelines, speaking the authoritative answer. |

---

## 🛡️ Non-Negotiable Voice UX & Safety Rules

1. **Voice-First Brevity (P0)**:
   Spoken responses are strictly 1–2 natural sentences. Long lists, raw markdown, asterisks, bullet points, and raw JSON payloads are never spoken.
2. **Zero Hallucination of Dates or Requirements (P0)**:
   The agent **never** invents deadlines, test dates, or subject names. If a required argument (such as a due date) is missing, it initiates a follow-up turn to ask the user.
3. **Ambiguity Resolution**:
   When a user refers to an assignment by a generic name (e.g., *"Finish lab"*), the tool registry resolves candidates and asks the student to confirm by ID (e.g., *“Multiple tasks match: #1 Physics Lab and #3 DBMS Lab. Which one?”*).
4. **Short-Lived Confirmation Tokens**:
   Destructive actions (`delete_task`, `save_study_plan` when overwriting active sessions) issue a cryptographic 32-character hex token valid for 5 minutes (`_PENDING_CONFIRMATIONS`).

---

## 🚀 Deployment Guide to Alexa Developer Console

### Step 1: Install ASK CLI
Ensure the Alexa Skills Kit CLI is installed:
```powershell
npm install -g ask-cli
ask configure
```

### Step 2: Deploy Skill Manifest & Interaction Model
Deploy `alexa-skill/skill.json` to your Amazon Developer account:
```bash
# From the project root:
ask deploy --target skill-manifest
ask deploy --target model
```

### Step 3: Configure Endpoint Target
1. In the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask), select **CampusMate AI**.
2. Navigate to **Build ➔ Endpoint**.
3. Select **AWS Lambda ARN** and provide your deployed Lambda ARN:
   ```
   arn:aws:lambda:us-east-1:123456789012:function:campusmate-alexa-agent
   ```
   Or select **HTTPS** for local testing via an SSL tunnel (e.g., ngrok pointing to port 5000 `/api/alexa/simulate`).

### Step 4: Account Linking (OAuth 2.0 / Bearer Token)
1. Navigate to **Tools ➔ Account Linking**.
2. Enable **Do you allow users to create an account or link to an existing account?**.
3. Set Authorization Grant Type to **Auth Code Grant**.
4. Configure your campus authentication endpoint (pointing to `/api/auth/login`).
5. In every incoming Alexa request, `event.context.System.user.accessToken` will supply the authenticated student ID.

---

## 🧪 Testing with the Web Simulator

Before deploying to physical Echo hardware, use the included **CampusMate Alexa+ Simulator**:

```bash
# Serve or open the web simulator in any browser:
python -m http.server 3001 --directory alexa-sim
```


The simulator features:
- **SpeechRecognition & SpeechSynthesis**: Real voice-in / voice-out testing with customizable synthetic voices.
- **Audio-Reactive Glowing Orb**: Animated idle, listening, thinking, and speaking states.
- **Collapsible Tool Call Inspector**: Real-time display of JSON-RPC tool parameters and latency.
- **Multi-Step Planner Simulation**: Live demonstration of chained tool execution.
