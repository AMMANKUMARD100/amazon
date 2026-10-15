# CampusMate Alexa+ Web Simulator

The **CampusMate Alexa+ Web Simulator** is a dedicated, voice-first companion interface designed for testing and demonstrating the **CampusMate AI** agent skill for the Amazon Developer Hackathon (Alexa+ Track).

It simulates the conversational experience of an Amazon Echo Show / Alexa+ multimodal assistant, bridging natural language voice queries to backend **Model Context Protocol (MCP)** tools and Flask REST endpoints.

---

## ✨ Features

- **Alexa-Inspired Dark UI**: Deep gradient styling (`#1a1a2e` → `#16213e`) with glassmorphism, responsive cards, and clean typography.
- **Glowing Audio-Reactive Orb**:
  - `Idle`: Subtle breathing cyan/purple pulse.
  - `Listening`: Soundwave ripple effect and energetic green/cyan glow.
  - `Thinking`: Gradient spin and magenta pulse while querying agent tools.
  - `Speaking`: Rhythmic vocalization pulse synchronized to voice synthesis.
- **Voice-First & Multimodal**:
  - Uses the **Web Speech API (`SpeechRecognition`)** for speech-to-text.
  - Uses **`speechSynthesis`** with selectable natural voices for voice-out.
  - Full keyboard text input fallback with auto-complete chips.
- **Multi-Step Agent Loop**:
  - Automatically maps conversational intent to MCP tools via deterministic pattern matching.
  - Chains multi-step operations: e.g. *"Plan my evening"* sequentially executes `daily_briefing` → `list_tasks` → `generate_study_plan` and synthesizes a single unified spoken briefing.
  - Handles multi-turn context (e.g., prompting the student for missing due dates on task creation).
- **Tool Call Inspector & Debug Panel**:
  - Real-time collapsible view of all invoked tools.
  - Shows tool name, execution latency (in ms), JSON arguments, and structured output.
  - Visual protocol flow diagram (`Voice In` ➔ `Intent Match` ➔ `MCP Tool` ➔ `Speech Out`).
- **Dual Execution Modes**:
  1. **Flask REST API + MCP Mirroring**: Dispatches directly to the Flask backend endpoints (`/api/tasks/`, `/api/mcp/...`, `/api/agents/...`) with cookie session support.
  2. **Direct MCP Streamable HTTP**: Sends standard JSON-RPC 2.0 `tools/call` payloads to `http://localhost:8080/mcp` with Bearer authentication.
  3. **Offline Demo Fallback**: Automatically provides realistic mock responses when offline so the simulator is 100% demo-ready anywhere.

---

## 🚀 Quick Start

### Option 1: Direct Browser Launch
Since `alexa-sim/index.html` is completely self-contained with no external build step or npm dependency, you can open it directly in Google Chrome or Microsoft Edge:
```powershell
# In PowerShell:
Start-Process "c:\Users\Amman kumar D\Downloads\amazon\alexa-sim\index.html"
```

### Option 2: Serve via Local HTTP Server (Recommended for Mic Permissions)
Some browsers require an HTTP origin for Web Speech API microphone access:
```powershell
# From the project root:
cd "c:\Users\Amman kumar D\Downloads\amazon"
python -m http.server 3000 --directory alexa-sim
```
Then visit **`http://localhost:3000`** in your browser.

---

## 🔌 Connecting to CampusMate Backend Services

### 1. Flask REST API (Port 5000)
Run the Flask server:
```powershell
python backend/app.py
```
- In the simulator, click **Config** (gear icon) and verify the API URL is `http://localhost:5000`.
- Click the **"🔑 Auto-Login Demo Student"** button to authenticate as Alex Mercer (`student` / `password123`) and establish session cookies.

### 2. MCP Server (Port 8080)
When running the FastMCP streamable HTTP server:
```powershell
# Set token and start MCP server
$env:MCP_AUTH_TOKEN="campusmate-dev-token-xyz"
python backend/mcp_server.py
```
- Toggle the execution mode in the inspector to **"Direct MCP Stream"**.
- The simulator will send JSON-RPC 2.0 tool requests to `http://localhost:8080/mcp`.

---

## 🗣️ Supported Utterances & Tool Mappings

| Utterance Example | Mapped MCP Tool | Behavior |
| :--- | :--- | :--- |
| *"Plan my evening"* / *"Plan my day"* | `daily_briefing` + `list_tasks` + `generate_study_plan` | **Multi-step agent chain**: Checks today's schedule, audits pending tasks, generates an evening study block, and presents a cohesive briefing. |
| *"What is my daily briefing?"* / *"Good morning"* | `daily_briefing` / `get_today_summary` | Lists today's lectures, rooms, and upcoming deadlines. |
| *"What assignments are due?"* / *"List tasks"* | `list_tasks` | Queries pending assignments, priority tags, and due dates. |
| *"Add task Physics Lab due tomorrow"* | `add_task` | Parses task title and date; creates new record. If date is missing, prompts student. |
| *"Check my attendance"* / *"Can I miss class?"* | `get_attendance_summary` | Audits attendance percentages and flags subjects below the 75% cutoff with required classes. |
| *"Show my timetable"* / *"Classes today"* | `get_timetable` | Retrieves weekly/daily schedule, time slots, and lecture halls. |
| *"Generate a study plan"* | `generate_study_plan` | Computes balanced study sessions based on subject difficulty and exams. |
| *"What is my CGPA?"* | `calculate_cgpa` | Displays cumulative GPA and projected semester average. |
| *"When are my exams?"* | `list_exams` | Displays upcoming midterm and final exam dates. |
| *"Show my dashboard"* | `get_dashboard` | Summarizes academic profile, GPA, and pending workload. |
| *"What is the hostel curfew policy?"* | `search_faq` | Queries static campus regulations and speaks official policy guidelines. |

---

## 🛠️ Configuration Settings

Click the **Config** button in the header to modify:
- **Flask REST API Base URL**: Default `http://localhost:5000`
- **MCP Server Endpoint**: Default `http://localhost:8080/mcp`
- **MCP Bearer Auth Token**: Default `campusmate-dev-token-xyz`
- **Student ID Context**: Default `1` (Alex Mercer)
- **Voice Selection**: Choose any speech synthesis voice installed on your system.
- **Audio Toggle**: Mute or enable voice speech output at any time.

---

## 💡 Keyboard Shortcuts

- **`Spacebar`**: Toggle voice listening (when text input is not focused).
- **`Enter`**: Send text input query.
