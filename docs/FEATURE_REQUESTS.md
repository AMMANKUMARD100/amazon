# CampusMate AI – Feature Requests: Alexa+ & Model Context Protocol (MCP)

**Project:** CampusMate AI (Intelligent Student Concierge)  
**Hackathon Track:** Alexa+ Track (Amazon Developer Hackathon)  
**Submission Date:** October 2026  

---

## 1. MCP SDK Feature Requests

### 1.1 Native Framework Mounting Middleware (Flask / FastAPI / Django)
* **Problem:** Currently, running FastMCP over streamable HTTP requires spinning up a standalone web server on a separate port or managing complex background threads. This creates cross-origin resource sharing (CORS) hurdles, requires maintaining multiple process runners, and complicates deployment behind single reverse proxies.
* **Proposed Feature:** Introduce native WSGI and ASGI mounting adapters in the Python MCP SDK:
  ```python
  from mcp.server.fastmcp import FastMCP
  from flask import Flask

  app = Flask(__name__)
  mcp = FastMCP("campusmate")
  mcp.mount_to_flask(app, url_prefix="/api/mcp")
  ```
* **Impact:** Drastically lowers friction for existing enterprise and student web applications seeking to expose MCP capabilities without architectural rewrites.

### 1.2 First-Class Authentication & Context Interceptors in Streamable HTTP
* **Problem:** In multi-tenant environments (such as universities where each request must be scoped strictly to the authenticated `student_id`), the standard streamable HTTP transport client lacks an idiomatic hook to inject Bearer tokens, API keys, or tenant context headers into every MCP request.
* **Proposed Feature:** Provide built-in authentication middleware for MCP transports:
  ```python
  mcp = FastMCP("campusmate", auth_provider=BearerTokenAuthProvider(verify_fn=validate_jwt))
  ```
* **Impact:** Eliminates custom parameter workarounds and ensures tenant data isolation at the protocol transport layer.

### 1.3 Out-of-the-Box Tool Schema Exporters for AWS Bedrock & Major Providers
* **Problem:** Developers must write custom boilerplate to convert standard JSON Schema / Pydantic schemas into the specific format demanded by Amazon Bedrock's Converse API (`toolConfig.tools[].toolSpec.inputSchema.json`).
* **Proposed Feature:** Add built-in formatters:
  ```python
  bedrock_tools = mcp.to_bedrock_tool_config()
  ```
* **Impact:** Saves hours of debugging schema mismatches across Amazon Bedrock, Anthropic Claude, and OpenAI tool APIs.

### 1.4 Native Confirmation Token & Voice Safety Primitive
* **Problem:** Destructive operations (e.g. deleting assignments, dropping enrolled courses, wiping calendar slots) require custom two-step confirmation mechanisms to prevent accidental execution in ambient voice environments.
* **Proposed Feature:** Add a `@mcp.tool(destructive=True, confirmation_ttl=300)` decorator parameter that natively emits a standardized `confirmation_token` challenge in the MCP response protocol.
* **Impact:** Standardizes safety across all agentic and voice tool executions.

---

## 2. Alexa+ Feature Requests

### 2.1 Native MCP Client Support inside Alexa Developer Console
* **Problem:** Connecting an Alexa+ Agent Skill to an external MCP server currently requires setting up intermediate webhook relays, AWS Lambda adapter functions, or custom conversational bridges.
* **Proposed Feature:** Allow developers to configure an MCP Endpoint URL (Streamable HTTP with OAuth2/Bearer Auth) directly in the Alexa Developer Console under Skill Tools:
  - Skill Builder $\rightarrow$ Tools $\rightarrow$ Add External Tool Provider $\rightarrow$ Model Context Protocol (MCP).
  - Alexa+ automatically fetches MCP tool definitions via `tools/list` and handles runtime invocations via `tools/call`.
* **Impact:** Enables any developer with an MCP server to launch an Alexa+ voice skill in minutes without writing custom Lambda intent shims.

### 2.2 Ambient Proactive Push Notifications for Smart Speakers
* **Problem:** Proactive alerts (such as low attendance warnings or impending exam clashes) are currently triggered either during active conversation turns or via browser toasts. True ambient voice devices should proactively alert the user when risk thresholds are breached.
* **Proposed Feature:** A streamlined Alexa+ Proactive Notification API that allows an agent to speak an ambient chime and single-sentence reminder (e.g., *"Alexa has a priority alert for your Software Engineering course"*) on registered Echo devices without complex SNS/SQS event bridges.
* **Impact:** Transforms student assistants from reactive responders into genuine autonomous concierges that prevent academic crises.

### 2.3 Direct Multimodal Display Cards for MCP Streamable Data
* **Problem:** Visual smart displays (Echo Show, Fire Tablets) require separate APL (Alexa Presentation Language) templates, decoupling visual output from structured MCP tool returns.
* **Proposed Feature:** Auto-generation of responsive Alexa visual cards and table widgets directly from structured MCP tool JSON returns:
  ```python
  return MCPToolResult(
      data=attendance_list,
      display_hint="progress_ring"  # or "table", "calendar", "timeline"
  )
  ```
* **Impact:** Radically accelerates multimodal development on Echo Show hardware.

### 2.4 Built-in Ambiguity Resolution Loop in Alexa+ Runtime
* **Problem:** When speech matches multiple entities (e.g., *"Mark homework as done"* when there are two homework tasks), developers must manually implement conversational multi-turn disambiguation.
* **Proposed Feature:** An Alexa+ runtime primitive where tools can return an `AmbiguityChallenge` object, prompting Alexa+ to automatically ask: *"Did you mean [Option A] or [Option B]?"* and re-invoking the tool with the resolved choice.
* **Impact:** Makes conversational ambiguity handling seamless and consistent across skills.

---

## 3. Developer Tools & Testing Requests

### 3.1 Interactive CLI Inspector for FastMCP Endpoints
* **Problem:** Testing MCP tools over Streamable HTTP requires writing custom `curl` scripts or test cases.
* **Proposed Feature:** A lightweight terminal UI tool (e.g., `mcp-cli inspect http://127.0.0.1:8000`) that discovers all exposed tools, generates interactive parameter input forms, displays formatted JSON responses, and logs latency.
* **Impact:** Greatly speeds up local tool debugging prior to agent integration.

### 3.2 Mock Alexa+ Audio & Utterance Testing Harness
* **Problem:** Testing voice interactions requires either talking into a physical microphone or manually constructing simulated JSON payloads.
* **Proposed Feature:** A local Python test utility providing simulated Alexa+ voice sessions:
  ```python
  from alexa_plus.testing import VoiceTestClient

  client = VoiceTestClient(mcp_server=my_server)
  response = client.simulate_utterance("Plan my evening")
  assert "Data Structures" in response.speech
  assert response.tool_calls[0].name == "get_today_summary"
  ```
* **Impact:** Allows standard CI/CD pipelines (GitHub Actions, AWS CodePipeline) to unit-test conversational voice turns and MCP tool call sequences without hardware.

### 3.3 Bedrock Converse Tool Debugger & Trace Visualizer
* **Problem:** Debugging multi-turn conversational loops where models choose not to call a tool or pass incorrect arguments requires parsing dense AWS Bedrock logs.
* **Proposed Feature:** A browser-based visual trace tool that graphs the multi-turn exchange: user utterance $\rightarrow$ system prompt $\rightarrow$ model thoughts $\rightarrow$ Bedrock toolUse $\rightarrow$ MCP execution $\rightarrow$ model synthesis.
* **Impact:** Drastically reduces prompt engineering and tool tuning time.
