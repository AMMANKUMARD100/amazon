# CampusMate AI – Product Feedback: Alexa+ & Model Context Protocol (MCP)

**Project:** CampusMate AI  
**Hackathon Track:** Alexa+ Track (Amazon Developer Hackathon)  
**SDK Versions Tested:** `mcp` Python SDK v1.29.0, FastMCP, `boto3` v1.34+ (Amazon Bedrock Converse API)  
**Date:** October 2026  

---

## 1. Overall Experience

Building CampusMate AI using the Model Context Protocol (MCP) and the Alexa+ developer primitives has been a transformative experience. Moving from traditional rigid voice intents to an open, standardized agentic tool interface allowed us to bridge our backend academic services directly with modern foundation models without writing dozens of brittle slot-filling handlers.

* **Rating:** 4.5 / 5.0
* **Developer Velocity:** Rapid once FastMCP patterns were understood. Tool registration went from hours of custom boilerplate to concise declarative Python functions.
* **Key Highlight:** The clean separation between tool execution (FastMCP / SQLite) and conversational reasoning (Amazon Bedrock Converse / Alexa+).
* **[FILL IN - Team Impression]:** *[FILL IN: Add personal team remarks, onboarding speed, and sentiment from the hackathon experience]*

---

## 2. MCP SDK (Python v1.29.0)

The Python MCP SDK v1.29.0 introduced `FastMCP`, which dramatically simplifies setting up tools, resources, and prompts.

### Observations:
- **FastMCP Ergonomics:** The `@mcp.tool()` decorator pattern is intuitive and Pythonic. It automatically extracts JSON schemas from Python type annotations, docstrings, and Pydantic models.
- **Async vs Sync Event Loops:** FastMCP leans heavily on `asyncio`. When integrating with traditional synchronous WSGI web frameworks like Flask, developers must carefully manage event loops (e.g., using `asyncio.run()` or running FastMCP in a dedicated background thread) to avoid blocking main application workers.
- **Schema Strictness:** In v1.29.0, tool schema validation is stringent. Any mismatch in required fields or extra parameters triggers validation errors before the handler runs, which prevents malformed LLM tool invocations from corrupting backend state.
- **[FILL IN - SDK Usability]:** *[FILL IN: Note any specific SDK nuances encountered when configuring server timeouts or custom decorators]*

---

## 3. Streamable HTTP Transport

The evolution toward Streamable HTTP (MCP spec 2025-11-25+) represents a significant leap over older Server-Sent Events (SSE) and stdio transports.

### Observations:
- **Network Simplicity:** Unlike `stdio` (which is restricted to local sub-processes) and raw SSE (which had quirks with HTTP/2 proxies and bidirectional requests), Streamable HTTP operates cleanly over standard web infrastructure.
- **Connection Lifecycle:** Low overhead for long-polling and streaming intermediate responses. Allows the client to receive streaming status while multi-step tools execute.
- **Port Management:** In a microservices or monorepo setup (e.g. Flask on port 5000 and FastMCP on port 8000), managing multiple network ports during local development can introduce CORS and firewall hurdles. A native ASGI/WSGI adapter to mount FastMCP directly into an existing web application would be a major enhancement.
- **[FILL IN - Transport Metrics]:** *[FILL IN: Record measured latency overhead for streamable-http versus standard REST endpoints]*

---

## 4. Agent Skill Definition

Defining skills as collections of MCP tools rather than isolated Alexa intent schemas fundamentally changes voice architecture.

### Observations:
- **Declarative vs Procedural:** Instead of programming dialog models, utterance training datasets, and complex slot confirmation flows in the Alexa Developer Console, the LLM reads JSON Schema tool definitions and orchestrates multi-step execution autonomously.
- **Destructive Action Safety:** Voice interactions have higher risks of accidental execution. We found it essential to design a two-phase confirmation protocol (returning `confirm_token` on destructive operations like `delete_task` or calendar overwrites) that the agent must re-verify. Standardizing this pattern in the Agent Skill Definition spec would benefit the entire voice ecosystem.
- **Ambiguity Handling:** When a user says *"Complete lab"*, and there are three labs, the tool must return an ambiguity descriptor (`candidates: [...]`). The agent smoothly handles this by prompting the user for clarity.
- **[FILL IN - Voice Modality]:** *[FILL IN: Describe experience with voice-to-tool argument extraction accuracy]*

---

## 5. Documentation Quality

- **What Was Clear:**
  - FastMCP getting-started examples and tool decoration tutorials.
  - Core JSON schema structure for MCP messages and tool specifications.
  - Amazon Bedrock Converse API request/response specifications for toolConfig and toolResult blocks.
- **What Was Missing / Hard to Find:**
  - Official, comprehensive end-to-end reference architecture showing Alexa+ consuming an external FastMCP streamable-http server.
  - Production security blueprints for securing MCP servers over HTTP with Bearer tokens or OAuth2 authentication.
  - Troubleshooting guides for common Windows development quirks (e.g. event loop policies, path separators).
- **[FILL IN - Documentation Suggestions]:** *[FILL IN: Mention specific guides or tutorials your team felt were missing]*

---

## 6. What Worked Well

1. **FastMCP Declarative Tools:** Defining tools with typed signatures enabled rapid conversion of our 13 internal services into standardized MCP capabilities within hours.
2. **Bedrock Converse API Synergy:** Amazon Bedrock's native support for toolConfig allowed seamless translation between MCP tool definitions and Bedrock model invocations.
3. **Multi-Step Orchestration:** The model reliably executed complex requests involving 2 to 3 chained tool calls (e.g., timetable $\rightarrow$ assignments $\rightarrow$ study planner) without lost context or hallucinated parameters.
4. **Offline Heuristic Fallback:** When internet connectivity or AWS credentials were unavailable, our local fallback provider preserved full functionality, proving the resilience of the architecture.
5. **[FILL IN - Additional Win]:** *[FILL IN: Highlight another successful feature or developer milestone]*

---

## 7. What Could Be Better

1. **Integrated Auth in MCP Transports:** FastMCP's streamable-http transport currently lacks built-in middleware for standard HTTP Authorization headers (Bearer JWT tokens). We had to implement custom request validation wrappers.
2. **Unified WSGI/ASGI Mounting:** Providing a simple `mcp.mount_to_flask(app, url_prefix='/mcp')` or FastAPI router would eliminate the need to run multiple servers on distinct ports during development.
3. **Voice-Specific Schema Extensions:** In voice applications, field prompts (e.g., *"What is the due date?"*) and voice pronunciation hints should ideally be declared directly within the tool schema so the voice agent can prompt naturally when required parameters are omitted.
4. **Live Tool Inspector in Alexa Developer Tools:** A built-in graphical inspector in the Alexa developer console showing live MCP payload traces, connection heartbeats, and schema validation errors.
5. **[FILL IN - Critical Improvement]:** *[FILL IN: Add any other blocker or friction point your team encountered]*
