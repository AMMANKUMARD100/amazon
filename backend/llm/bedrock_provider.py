"""Amazon Bedrock Converse API Provider for CampusMate AI.

Implements native Converse API integration with boto3 bedrock-runtime.
Translates CampusMate ToolDefinition schemas to Bedrock toolConfig format,
and extracts text/toolUse content from Bedrock Converse responses.
"""

import os
from typing import Any, Dict, List, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from backend.llm.provider import LLMProvider, LLMResponse, ToolUseCall


class BedrockProvider(LLMProvider):
    def __init__(
        self,
        model_id: Optional[str] = None,
        region_name: Optional[str] = None,
        client: Optional[Any] = None
    ):
        self.model_id = model_id or os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        self.region_name = region_name or os.environ.get("AWS_REGION", "us-east-1")
        if client is not None:
            self.client = client
        else:
            self.client = boto3.client("bedrock-runtime", region_name=self.region_name)

    @staticmethod
    def format_tools_for_bedrock(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Converts ToolDefinition dicts to Bedrock Converse toolConfig format.
        
        Bedrock schema format:
        {
            "toolSpec": {
                "name": str,
                "description": str,
                "inputSchema": {
                    "json": { ...json_schema... }
                }
            }
        }
        """
        bedrock_tools = []
        for t in tools:
            bedrock_tools.append({
                "toolSpec": {
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": {
                        "json": t["parameters"]
                    }
                }
            })
        return bedrock_tools

    def converse(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tools: List[Dict[str, Any]],
        inference_config: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """Calls Bedrock client.converse()."""
        bedrock_tools = self.format_tools_for_bedrock(tools)

        params: Dict[str, Any] = {
            "modelId": self.model_id,
            "messages": messages,
            "system": [{"text": system_prompt}]
        }

        if bedrock_tools:
            params["toolConfig"] = {
                "tools": bedrock_tools
            }

        cfg = {
            "maxTokens": 512,
            "temperature": 0.2
        }
        if inference_config:
            cfg.update(inference_config)
        params["inferenceConfig"] = cfg

        try:
            resp = self.client.converse(**params)
        except (BotoCoreError, ClientError) as err:
            raise RuntimeError(f"Amazon Bedrock Converse API invocation failed: {str(err)}") from err

        output = resp.get("output", {})
        message = output.get("message", {})
        content_blocks = message.get("content", [])
        stop_reason = resp.get("stopReason", "end_turn")

        text_pieces = []
        tool_calls = []

        for block in content_blocks:
            if "text" in block:
                text_pieces.append(block["text"])
            elif "toolUse" in block:
                tu = block["toolUse"]
                tool_calls.append(ToolUseCall(
                    tool_use_id=tu.get("toolUseId", ""),
                    name=tu.get("name", ""),
                    input=tu.get("input", {})
                ))

        return LLMResponse(
            text=" ".join(text_pieces).strip(),
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            raw_response=resp
        )
