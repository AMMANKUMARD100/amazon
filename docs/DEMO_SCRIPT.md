# CampusMate AI – Video Demo Script (2:30)

**Project:** CampusMate AI – Intelligent Student Concierge (Amazon Developer Hackathon - Alexa+ Track)  
**Total Target Duration:** 2 minutes 30 seconds (150 seconds)  
**Pacing Strategy:** Strongest moment first. Demonstrate multi-step agentic voice orchestration within the first 30 seconds, then uncover the underlying FastMCP server, proactive alerts, Amazon Bedrock integration, and architecture.

---

## Timeline & Scene Breakdown

### `[0:00 – 0:15]` The Hook: Multi-Step Voice Command
* **What to Show:** Full screen of the **Alexa+ Web Simulator** in the browser. The mic button pulses, showing audio activity. The student user is already logged in as `student` (Alex Mercer).
* **What to Click / Speak:** Click the **Microphone** icon. Speak clearly into the mic:  
  `"Alexa, plan my evening."`
* **What to Say (Narration):**  
  *"Students are overwhelmed by scattered campus apps. Here is CampusMate AI running on Alexa+ with the Model Context Protocol. Watch what happens when I give a single, natural voice command: 'Alexa, plan my evening.'"*
* **System Action:** Web Speech API captures speech, turns on audio wave visualizer, and dispatches the utterance to the conversational agent loop.

---

### `[0:15 – 0:30]` The Magic: Multi-Step Agentic Orchestration
* **What to Show:** The Alexa+ Web Simulator response appears. Alexa speaks back through browser audio synthesis:  
  *Speech:* `"You have no more classes today. I found a High-priority assignment due tomorrow, so I have scheduled a 2-hour study block for Data Structures from 6:00 PM to 8:00 PM."*  
  Simultaneously, the **MCP Live Inspector Drawer** on the right side of the screen lights up, displaying sequential tool executions.
* **What to Click / Speak:** Presenter gestures towards the tool trace list expanding in the UI.
* **What to Say (Narration):**  
  *"In a single conversational turn, the agent didn't just give a canned answer. It orchestrated three distinct MCP tools: first checking today's timetable, discovering an upcoming assignment due tomorrow, and generating an optimized study session."*

---

### `[0:30 – 0:45]` Under the Hood: FastMCP Streamable-HTTP Execution
* **What to Show:** Zoom into the **MCP Live Inspector Drawer**. Expand the raw JSON blocks showing tool call payload:  
  `get_today_summary` $\rightarrow$ `list_tasks(status='Pending')` $\rightarrow$ `generate_study_plan(daily_hours=2)`.  
  Show the HTTP stream status: `200 OK via Streamable-HTTP (MCP spec 2025-11-25+)`.
* **What to Click / Speak:** Click on the `generate_study_plan` payload in the drawer to preview input parameters and output JSON slots.
* **What to Say (Narration):**  
  *"Underneath, our FastMCP server is running over modern streamable HTTP. Each tool invocation strictly validates JSON schemas, enforces student data boundaries, and streams results directly into the LLM context without hallucination."*

---

### `[0:45 – 1:00]` Proactive Alert: Attendance Crisis Detection
* **What to Show:** Alexa+ Simulator presents a red-accented **Proactive Alert Card**:  
  `"⚠️ Attendance Risk Detected: CS105 Software Engineering is at 50% (5/10 classes attended). You must attend 10 consecutive classes to clear the 75% threshold."`
* **What to Click / Speak:** Speak into mic:  
  `"Alexa, check my attendance standing."`
* **What to Say (Narration):**  
  *"CampusMate AI doesn't wait for students to fail. It actively calculates attendance percentages and safe cutoffs. When attendance drops below university thresholds, Alexa delivers an urgent, voice-ready intervention."*

---

### `[1:00 – 1:15]` Student Action: Responding to Voice Prompts
* **What to Show:** The Alexa output updates with clear next steps:  
  *Speech:* `"Your overall attendance average is 76%, but Software Engineering is in the danger zone at 50%. Would you like me to prioritize CS105 in your study schedule?"*  
  A quick-reply badge appears: `[Yes, prioritize CS105]`.
* **What to Click / Speak:** Click the quick-reply badge or speak:  
  `"Yes, prioritize it."`
* **What to Say (Narration):**  
  *"Notice the conversational voice tone: concise, spoken sentences with zero markdown or robotic JSON jargon, perfectly tuned for smart speakers and Echo Show displays."*

---

### `[1:15 – 1:30]` Safe Destructive Actions: Confirmation Tokens
* **What to Show:** Alexa+ Simulator prompt for task cleanup:  
  *Utterance:* `"Alexa, delete task 1."`  
  Alexa responds:  
  *Speech:* `"Deleting task 'Complete Lab 3' cannot be undone. To proceed, please confirm with token 4f9e8a."*  
  Screen shows visual confirmation card with token `4f9e8a` and a 5-minute countdown timer.
* **What to Click / Speak:** Speak:  
  `"Confirm token 4f9e8a."`
* **What to Say (Narration):**  
  *"Voice safety is critical. Destructive operations like deleting assignments or overwriting calendars require short-lived, single-use confirmation tokens. The action is securely completed only upon explicit confirmation."*

---

### `[1:30 – 1:45]` The Power of Amazon Bedrock Converse API
* **What to Show:** Switch terminal or split view to show the Flask backend console log output:  
  `[BedrockProvider] Invoking Converse API modelId=anthropic.claude-3-haiku-20240307-v1:0`  
  `[BedrockProvider] toolUse detected -> complete_task -> toolResult appended`
* **What to Click / Speak:** Highlight the `BedrockProvider` terminal logs and latency metrics (~420ms turn time).
* **What to Say (Narration):**  
  *"Our agent uses Amazon Bedrock's native Converse API with Claude 3 Haiku. Bedrock seamlessly handles structured tool calling, returning structured toolUse requests that our MCP registry executes deterministically against SQLite."*

---

### `[1:45 – 2:00]` Zero-Dependency Offline Fallback
* **What to Show:** In the terminal or configuration, demonstrate toggling `LLM_PROVIDER=demo`. Trigger a voice query:  
  `"Alexa, what are campus library hours?"`  
  Response arrives instantly from the local `search_faq` index:  
  *Speech:* `"Central Library is in Block C and is open 8:00 AM to 10:00 PM on weekdays."*
* **What to Click / Speak:** Show the FAQ query matching without external internet calls.
* **What to Say (Narration):**  
  *"Even if external cloud APIs are unavailable, CampusMate AI gracefully falls back to local heuristic engines and static indices, guaranteeing that students are never locked out of their schedules."*

---

### `[2:00 – 2:15]` Complete Student Concierge: React Dashboard Sync
* **What to Show:** Switch to the main React Student Portal at `http://localhost:3000`. Show that the study session scheduled via Alexa voice earlier (`Data Structures 6:00 PM - 8:00 PM`) is already live on the interactive calendar and dashboard metrics.
* **What to Click / Speak:** Click **Study Planner** tab, showing the saved calendar session with subject color badges.
* **What to Say (Narration):**  
  *"Everything stays completely synchronized across interfaces. Voice actions made through Alexa+ instantly reflect on the student's React portal and mobile-responsive dashboard."*

---

### `[2:15 – 2:30]` Wrap Up & Architectural Vision
* **What to Show:** Full screen of the **System Architecture Diagram** from the project README. Display links to GitHub repository and submission documentation.
* **What to Click / Speak:** Pan over the architecture diagram highlighting Echo / Simulator $\rightarrow$ Bedrock $\rightarrow$ FastMCP $\rightarrow$ Unified Tool Registry.
* **What to Say (Narration):**  
  *"CampusMate AI brings standard Model Context Protocol, Amazon Bedrock, and Alexa+ together into an ambient student concierge that keeps university students organized, on track, and stress-free. Thank you!"*
* **Visual Ending:** Title card with project link:  
  `CampusMate AI – Built for Amazon Developer Hackathon (Alexa+ Track)`
