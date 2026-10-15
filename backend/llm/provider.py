"""Abstract LLM Provider interface for CampusMate AI.

Defines standardized data classes for multi-turn messages, tool calls,
and completions across different LLM backends (Amazon Bedrock, Demo mode).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolUseCall:
    tool_use_id: str
    name: str
    input: Dict[str, Any]


@dataclass
class Message:
    role: str  # 'user' | 'assistant'
    content: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def user_text(cls, text: str) -> 'Message':
        return cls(role="user", content=[{"text": text}])

    @classmethod
    def assistant_text(cls, text: str) -> 'Message':
        return cls(role="assistant", content=[{"text": text}])

    @classmethod
    def user_tool_results(cls, tool_results: List[Dict[str, Any]]) -> 'Message':
        """Creates a user message containing tool results for Bedrock Converse API.
        tool_results: list of {"toolUseId": str, "content": [{"json": ...}], "status": "success"|"error"}
        """
        content = [{"toolResult": r} for r in tool_results]
        return cls(role="user", content=content)


@dataclass
class LLMResponse:
    text: str
    tool_calls: List[ToolUseCall] = field(default_factory=list)
    stop_reason: str = "end_turn"  # 'end_turn' | 'tool_use' | 'max_tokens'
    raw_response: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    @abstractmethod
    def converse(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tools: List[Dict[str, Any]],
        inference_config: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """Invokes the underlying model with messages, system prompt, and tools.
        
        Args:
            messages: List of message dicts in Bedrock converse format:
                      [{"role": "user"|"assistant", "content": [...]}]
            system_prompt: Voice-first persona instructions
            tools: List of tool specifications in Bedrock toolConfig format
            inference_config: Optional dict (maxTokens, temperature, topP)
            
        Returns:
            LLMResponse dataclass
        """
        pass
