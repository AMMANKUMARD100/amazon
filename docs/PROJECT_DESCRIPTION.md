# CampusMate AI – Project Description

## The Problem: The Modern Campus Chaos

Every semester, university students face an exhausting operational burden. Academic life is fragmented across disconnected systems: a legacy learning management system for assignments, a separate university portal for attendance tracking, printed or PDF timetables for class schedules, siloed campus policy PDFs for hostel and library regulations, and generic calendar apps that have no awareness of academic context. 

When a student asks fundamental questions—*"Can I safely miss tomorrow's 9:00 AM lecture to finish my operating systems project?", "How many hours must I study tonight to prepare for Friday's algorithms exam without falling behind on coursework?",* or *"What is my exact attendance standing in Software Engineering?"*—they are forced to manually cross-reference three portals, calculate percentages by hand, and guess their study allocations. The result is chronic stress, missed deadlines, surprise attendance shortfalls leading to exam debarment, and burnout. Students do not need another dashboard full of numbers; they need an proactive, context-aware, voice-first intelligent academic concierge.

---

## What Existed Before the Hackathon

Prior to the Amazon Developer Hackathon, CampusMate AI existed as an offline-first academic management prototype with:
- **Core Flask & SQLite Backend:** A relational database housing students, courses, attendance logs, assignments, exam records, study plans, and timetable schedules.
- **8 Heuristic / Rule-Based Agents:** Dedicated domain agents coordinated by a central `AgentManager` orchestrator (PlannerAgent, AttendanceAgent, AssignmentAgent, ReminderAgent, FAQAgent, DashboardAgent, StudyAgent, NotificationAgent).
- **REST API Tool Layer:** A unified `tool_registry` exposing 13 deterministic endpoints with JSON schema validation, parameter constraints, and short-lived confirmation tokens for destructive operations.
- **Web Frontend & CLI:** A standard React 18 single-page application styled with Tailwind CSS, alongside an interactive terminal client (`cli.py`).
- **Security & Infrastructure:** Defensive HTTP headers (CSP, nosniff, DENY), rate limiting, session-based role authentication, Docker Compose configurations, and a 40+ unit test suite.

While functional, interaction was entirely manual: students had to navigate visual tables, fill out forms, and mentally synthesize insights across tabs.

---

## What Was Added During the Hackathon

During the Amazon Developer Hackathon (Alexa+ Track), CampusMate AI was transformed into an autonomous, voice-first agentic ecosystem:

1. **FastMCP Server (Phase 1):** Implemented an open Model Context Protocol server using the modern `mcp` SDK (v1.29.0) with streamable-http transport adhering to MCP spec 2025-11-25+. Wrapped all 13 existing concierge tools and engineered an intelligent composite `daily_briefing` tool that aggregates morning timetables, urgent deadlines, and attendance advisories into an actionable summary.
2. **Alexa+ Web Simulator (Phase 2):** Developed a real-time conversational voice portal leveraging the Web Speech API (speech recognition and synthesis) with standard Alexa-compliant JSON response cards, audio visualizers, and a live MCP tool call inspection drawer.
3. **VoiceAgent Multi-Step Orchestrator (Phase 3):** Built an autonomous multi-turn reasoning engine capable of chaining disparate tools in a single breath (e.g., inspecting timetable $\rightarrow$ auditing assignment deadlines $\rightarrow$ generating balanced study slots $\rightarrow$ confirming calendar save). Added automated proactive alerts for attendance drop risks ($<75\%$) and impending exam clashes.
4. **Amazon Bedrock Converse Integration (Phase 4):** Integrated Amazon Bedrock Converse API (`anthropic.claude-3-haiku-20240307-v1:0` and Sonnet) with native tool calling, strict schema translation, multi-turn message history preservation, and deterministic fallback for offline resilience.

---

## System Architecture

```text
+-----------------------------------------------------------------------------------+
|                            VOICE & CLIENT SURFACES                                |
|  Echo Devices / Alexa+ Voice Skill  <--->  React Alexa+ Simulator (Web Speech API)|
+------------------------------------------+----------------------------------------+
                                           | Spoken Utterance / Audio Input
                                           v
+-----------------------------------------------------------------------------------+
|                        ALEXA+ AGENT ORCHESTRATION LAYER                           |
|  - Multi-Turn Conversation Memory        - Proactive Risk Engine (Attendance/Exam)|
|  - Amazon Bedrock Converse API           - VoiceAgent Multi-Step Intent Resolver  |
|    (Claude 3 Haiku / Sonnet via boto3)   - Deterministic Fallback Engine          |
+------------------------------------------+----------------------------------------+
                                           | MCP Tool Invocations (Streamable HTTP)
                                           v
+-----------------------------------------------------------------------------------+
|                   MODEL CONTEXT PROTOCOL (MCP) SERVER                             |
|  FastMCP Server (Spec 2025-11-25+) on Streamable-HTTP Transport                   |
|  Exposed Tools:                                                                   |
|   - list_tasks              - complete_task           - set_study_hours           |
|   - add_task                - delete_task (tokenized) - generate_study_plan       |
|   - update_task             - add_exam / list_exams   - save_study_plan           |
|   - get_today_summary       - get_attendance_summary  - search_faq                |
|   - daily_briefing [NEW]                                                          |
+------------------------------------------+----------------------------------------+
                                           | Direct Tool Handler Dispatch
                                           v
+-----------------------------------------------------------------------------------+
|                       CORE APPLICATION & DATA BOUNDARY                            |
|  Flask REST Engine  <--->  Unified Tool Registry  <--->  SQLite Academic Database |
+-----------------------------------------------------------------------------------+
```

---

## Alexa+ Track Fit & Innovation

CampusMate AI exemplifies the future of ambient, voice-first intelligent assistance:
- **Standardized MCP Server:** Leverages standard Model Context Protocol over streamable HTTP, making university services immediately discoverable and callable by Alexa+ without custom brittle connectors.
- **Voice-First Design:** Spoken responses are engineered strictly for audio consumption (1–2 concise sentences without markdown, raw JSON, or visual fluff), ensuring natural delivery on smart speakers and smart displays.
- **Agentic Multi-Step Reasoning:** Moves beyond rigid intent slots. When a student commands *"Plan my evening,"* the agent autonomously checks classes, detects an urgent assignment, verifies study availability, and produces a concrete study block.
- **Built-in Safety:** Destructive operations (e.g., deleting tasks, overriding schedules) enforce conversational confirmation tokens, preventing accidental data loss in voice environments.

---

## Tech Stack

- **Backend & AI:** Python 3.14, Flask, FastMCP (`mcp` v1.29.0), Amazon Bedrock Converse API (`boto3`), SQLite.
- **Frontend & Voice:** React 18, Vite, Tailwind CSS, Web Speech API (SpeechRecognition + SpeechSynthesis), Lucide Icons.
- **Security & Operations:** Flask-Login, Werkzeug, JWT, Docker & Docker Compose.
