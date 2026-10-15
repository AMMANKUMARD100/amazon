"""Agent loop orchestrator for multi-turn conversational tool execution.

Manages the LLM interaction loop:
1. Feeds conversation messages and tool schemas to LLMProvider.
2. If LLM requests tool_use, executes registered tool via unified tool_registry.
3. Formats tool result into Bedrock Converse-compliant toolResult format.
4. Appends to history and re-invokes LLM up to MAX_ITERATIONS (5) turns.
5. Returns final voice-ready response and execution trace.
"""

import os
from typing import Any, Dict, List, Optional

from backend.llm.provider import LLMProvider, LLMResponse, ToolUseCall
from backend.llm.bedrock_provider import BedrockProvider
from backend.llm.demo_provider import DemoProvider
from backend.tools import tool_registry, execute_tool

SYSTEM_PROMPT_VOICE_FIRST = (
    "You are CampusMate AI, a friendly, concise voice-first student assistant for Amazon Developer Hackathon. "
    "Follow these non-negotiable rules:\n"
    "1. Speak naturally in 1-2 short, spoken sentences. Avoid markdown, asterisks, bullet points, and raw JSON.\n"
    "2. Never invent dates, deadlines, subjects, or exam schedules. If a date is missing, politely ask the student.\n"
    "3. Use the provided tools to view or modify tasks, exams, schedule, attendance, and study plans.\n"
    "4. For destructive operations like deleting tasks or replacing existing study plans, explain what needs confirmation and provide the confirmation token.\n"
    "5. When multiple items match a request, list the candidates and ask the student to pick by ID."
)

MAX_ITERATIONS = 5


def get_llm_provider() -> LLMProvider:
    """Factory creating LLMProvider based on configuration and environment."""
    provider_name = os.environ.get("LLM_PROVIDER", "demo").lower().strip()
    if provider_name == "bedrock":
        try:
            return BedrockProvider()
        except Exception as e:
            # Fall back to demo provider if credentials missing
            return DemoProvider()
    return DemoProvider()


class AgentLoop:
    def __init__(
        self,
        student_id: int,
        provider: Optional[LLMProvider] = None,
        system_prompt: str = SYSTEM_PROMPT_VOICE_FIRST,
        max_iterations: int = MAX_ITERATIONS
    ):
        self.student_id = student_id
        self.provider = provider or get_llm_provider()
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations

    def run_turn(self, utterance: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Runs one conversational turn with automatic multi-iteration tool calling loop.
        
        Args:
            utterance: User's spoken/text query
            conversation_history: List of preceding Bedrock converse messages
            
        Returns:
            dict containing:
              - speech: Final spoken response
              - tool_calls_executed: List of tools called with results
              - messages: Updated message history
              - iterations: Number of model iterations
        """
        messages = list(conversation_history) if conversation_history else []
        messages.append({
            "role": "user",
            "content": [{"text": utterance}]
        })

        tools = tool_registry.list_tools()
        executed_calls: List[Dict[str, Any]] = []

        iteration = 0
        final_text = ""

        while iteration < self.max_iterations:
            iteration += 1

            # Call provider
            response: LLMResponse = self.provider.converse(
                messages=messages,
                system_prompt=self.system_prompt,
                tools=tools
            )

            # If model returned text, record it
            if response.text:
                final_text = response.text

            # If no tool calls requested, we are done
            if not response.tool_calls:
                # Append assistant final response to message history
                messages.append({
                    "role": "assistant",
                    "content": [{"text": response.text}]
                })
                break

            # Process tool calls
            # 1. Build assistant message block containing toolUse blocks
            assistant_content: List[Dict[str, Any]] = []
            if response.text:
                assistant_content.append({"text": response.text})

            for tc in response.tool_calls:
                assistant_content.append({
                    "toolUse": {
                        "toolUseId": tc.tool_use_id,
                        "name": tc.name,
                        "input": tc.input
                    }
                })
            messages.append({
                "role": "assistant",
                "content": assistant_content
            })

            # 2. Execute each tool via tool_registry and collect toolResult blocks
            tool_results_content: List[Dict[str, Any]] = []
            for tc in response.tool_calls:
                exec_res = execute_tool(tc.name, self.student_id, tc.input)
                executed_calls.append({
                    "tool_name": tc.name,
                    "input": tc.input,
                    "output": exec_res
                })

                status = "success" if exec_res.get("success") else "error"
                tool_results_content.append({
                    "toolResult": {
                        "toolUseId": tc.tool_use_id,
                        "content": [{"json": exec_res}],
                        "status": status
                    }
                })

            # 3. Append tool results as user message back to the model
            messages.append({
                "role": "user",
                "content": tool_results_content
            })

        return {
            "speech": final_text,
            "tool_calls_executed": executed_calls,
            "messages": messages,
            "iterations": iteration,
            "provider": self.provider.__class__.__name__
        }


def run_agent_turn(student_id: int, utterance: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Convenience functional interface."""
    loop = AgentLoop(student_id=student_id)
    return loop.run_turn(utterance=utterance, conversation_history=history)
