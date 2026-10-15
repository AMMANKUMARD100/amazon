"""Deterministic Demo Provider for CampusMate AI.

Used as fallback when LLM_PROVIDER=demo or when no AWS credentials are configured.
Simulates tool calling matching the user intent deterministically.
"""

import re
import datetime
from typing import Any, Dict, List, Optional
from backend.llm.provider import LLMProvider, LLMResponse, ToolUseCall


class DemoProvider(LLMProvider):
    """Deterministic simulated model that maps user utterances to tool calls."""

    def converse(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tools: List[Dict[str, Any]],
        inference_config: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        # Check if last message was a tool result
        last_msg = messages[-1] if messages else {}
        if last_msg.get("role") == "user":
            content = last_msg.get("content", [])
            has_tool_result = any("toolResult" in c for c in content)
            if has_tool_result:
                # Format a natural language voice response from the tool results
                for c in content:
                    tr = c.get("toolResult", {})
                    data = tr.get("content", [{}])[0].get("json", {})
                    # Render friendly speech
                    if isinstance(data, dict):
                        if data.get("success") is False:
                            err_msg = data.get("error", {}).get("message", "An error occurred.")
                            return LLMResponse(text=f"I couldn't complete that request: {err_msg}", stop_reason="end_turn")
                        res = data.get("result", {})
                        if isinstance(res, dict):
                            if res.get("pending_confirmation"):
                                return LLMResponse(
                                    text=f"{res.get('message')} Please say 'confirm token {res.get('confirm_token')}' to proceed.",
                                    stop_reason="end_turn"
                                )
                            if res.get("ambiguity"):
                                return LLMResponse(
                                    text="Multiple items match that title. Please specify by ID.",
                                    stop_reason="end_turn"
                                )
                            if "message" in res:
                                return LLMResponse(text=res["message"], stop_reason="end_turn")
                            if "title" in res and "due_date" in res:
                                return LLMResponse(text=f"Task '{res['title']}' is due on {res['due_date']}.", stop_reason="end_turn")
                        elif isinstance(res, list):
                            if len(res) == 0:
                                return LLMResponse(text="You have no items right now.", stop_reason="end_turn")
                            # Check if attendance list
                            if len(res) > 0 and isinstance(res[0], dict) and "percentage" in res[0]:
                                low = [a for a in res if a.get('percentage', 100) < 75]
                                if low:
                                    return LLMResponse(
                                        text=f"Warning: Your attendance in {low[0]['name']} is at {low[0]['percentage']}%, which is below 75%. You need to attend {low[0]['classes_needed_for_75']} consecutive classes.",
                                        stop_reason="end_turn"
                                    )
                                else:
                                    avg = round(sum(a.get('percentage', 0) for a in res) / len(res), 1)
                                    return LLMResponse(
                                        text=f"Your overall attendance is looking strong at an average of {avg}%. All subjects are above 75%.",
                                        stop_reason="end_turn"
                                    )
                            # Check if tasks list
                            if len(res) > 0 and isinstance(res[0], dict) and "title" in res[0]:
                                items_str = ", ".join([f"{t['title']} (due {t.get('due_date', '')})" for t in res[:4]])
                                return LLMResponse(text=f"You have {len(res)} pending tasks: {items_str}.", stop_reason="end_turn")
                            return LLMResponse(text=f"You have {len(res)} items found.", stop_reason="end_turn")
                return LLMResponse(text="Done! Is there anything else you need help with?", stop_reason="end_turn")

        # Otherwise inspect user text to produce an intent / tool call
        text = ""
        for c in last_msg.get("content", []):
            if "text" in c:
                text += c["text"] + " "
        text = text.lower().strip()

        # 1. Complete Task
        complete_match = re.search(r"^(?:complete|finish|mark done|done)\s+(?:task|assignment)?\s*(.+)$", text)
        if complete_match:
            target = complete_match.group(1).strip()
            args = {"task_id": int(target)} if target.isdigit() else {"task_title": target}
            return LLMResponse(
                text="",
                tool_calls=[ToolUseCall(tool_use_id="demo_call_complete", name="complete_task", input=args)],
                stop_reason="tool_use"
            )

        # 2. Add Task
        add_match = re.search(r"^(?:add task|create task|new assignment|add assignment|remind me to)\s+(.+)$", text)
        if add_match:
            content = add_match.group(1).strip()
            date_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|tomorrow|today)\b", content)
            due_date = None
            if date_match:
                d_str = date_match.group(1)
                today = datetime.date.today()
                if d_str == 'tomorrow':
                    due_date = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                elif d_str == 'today':
                    due_date = today.strftime("%Y-%m-%d")
                else:
                    due_date = d_str

            title = re.sub(r"\b(due|on|by)?\s*(\d{4}-\d{2}-\d{2}|tomorrow|today)\b", "", content, flags=re.IGNORECASE).strip()
            if not title:
                title = content

            if not due_date:
                return LLMResponse(
                    text=f"What is the due date for '{title}'? Please specify it in YYYY-MM-DD format.",
                    stop_reason="end_turn"
                )

            return LLMResponse(
                text="",
                tool_calls=[ToolUseCall(tool_use_id="demo_call_add", name="add_task", input={"title": title, "due_date": due_date})],
                stop_reason="tool_use"
            )

        # 3. Delete Task
        delete_match = re.search(r"^(?:delete|remove)\s+(?:task|assignment)\s*(.+)$", text)
        if delete_match:
            target = delete_match.group(1).strip()
            confirm_token = None
            confirm_match = re.search(r"(?:confirm|token)\s+([a-f0-9]{32})", text)
            if confirm_match:
                confirm_token = confirm_match.group(1)

            args = {"confirm_token": confirm_token} if confirm_token else ({"task_id": int(target)} if target.isdigit() else {"task_title": target})
            return LLMResponse(
                text="",
                tool_calls=[ToolUseCall(tool_use_id="demo_call_del", name="delete_task", input=args)],
                stop_reason="tool_use"
            )

        # 4. List Tasks
        if any(k in text for k in ["task", "assignment", "todo", "homework"]) and any(k in text for k in ["show", "list", "what", "pending", "view"]):
            return LLMResponse(
                text="",
                tool_calls=[ToolUseCall(tool_use_id="demo_call_list", name="list_tasks", input={"status": "Pending"})],
                stop_reason="tool_use"
            )

        # 5. Check attendance
        if "attendance" in text or "miss class" in text:
            return LLMResponse(
                text="",
                tool_calls=[ToolUseCall(tool_use_id="demo_call_att", name="get_attendance_summary", input={})],
                stop_reason="tool_use"
            )

        # 6. Today schedule
        if any(k in text for k in ["today", "schedule", "timetable", "class", "lecture"]):
            return LLMResponse(
                text="",
                tool_calls=[ToolUseCall(tool_use_id="demo_call_today", name="get_today_summary", input={})],
                stop_reason="tool_use"
            )

        # 7. FAQ search
        if any(k in text for k in ["policy", "library", "hostel", "rules", "wifi", "exam rule"]):
            return LLMResponse(
                text="",
                tool_calls=[ToolUseCall(tool_use_id="demo_call_faq", name="search_faq", input={"query": text})],
                stop_reason="tool_use"
            )

        # Fallback general speech
        return LLMResponse(
            text="I am your CampusMate AI student assistant. You can ask me to manage your tasks, check attendance, review today's lectures, or generate study plans.",
            stop_reason="end_turn"
        )
