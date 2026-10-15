import unittest
from unittest.mock import MagicMock
from backend.llm.provider import LLMResponse, ToolUseCall
from backend.llm.bedrock_provider import BedrockProvider
from backend.llm.demo_provider import DemoProvider
from backend.llm.agent_loop import AgentLoop
from backend.tools import tool_registry


class TestBedrockAndAgentLoop(unittest.TestCase):
    def test_bedrock_tools_formatting(self):
        sample_tools = [{
            "name": "test_tool",
            "description": "A test tool",
            "parameters": {
                "type": "object",
                "properties": {"arg": {"type": "string"}},
                "required": ["arg"]
            }
        }]
        bedrock_formatted = BedrockProvider.format_tools_for_bedrock(sample_tools)
        self.assertEqual(len(bedrock_formatted), 1)
        self.assertIn("toolSpec", bedrock_formatted[0])
        self.assertEqual(bedrock_formatted[0]["toolSpec"]["name"], "test_tool")
        self.assertEqual(bedrock_formatted[0]["toolSpec"]["inputSchema"]["json"], sample_tools[0]["parameters"])

    def test_bedrock_provider_with_mock_client(self):
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"text": "I can help with that."},
                        {
                            "toolUse": {
                                "toolUseId": "call_12345",
                                "name": "list_tasks",
                                "input": {"status": "Pending"}
                            }
                        }
                    ]
                }
            },
            "stopReason": "tool_use",
            "usage": {"inputTokens": 25, "outputTokens": 30}
        }

        provider = BedrockProvider(model_id="anthropic.claude-3-haiku-20240307-v1:0", client=mock_client)
        resp = provider.converse(
            messages=[{"role": "user", "content": [{"text": "Show my tasks"}]}],
            system_prompt="Voice assistant",
            tools=tool_registry.list_tools()
        )

        self.assertEqual(resp.text, "I can help with that.")
        self.assertEqual(len(resp.tool_calls), 1)
        self.assertEqual(resp.tool_calls[0].name, "list_tasks")
        self.assertEqual(resp.tool_calls[0].input, {"status": "Pending"})
        self.assertEqual(resp.stop_reason, "tool_use")
        mock_client.converse.assert_called_once()

    def test_agent_loop_multi_iteration_with_mock_bedrock(self):
        mock_client = MagicMock()
        # Turn 1: Model decides to call list_tasks
        # Turn 2: Model receives list_tasks result and outputs final spoken answer
        mock_client.converse.side_effect = [
            {
                "output": {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "toolUse": {
                                    "toolUseId": "call_abc",
                                    "name": "list_tasks",
                                    "input": {"status": "Pending"}
                                }
                            }
                        ]
                    }
                },
                "stopReason": "tool_use"
            },
            {
                "output": {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"text": "You have 3 pending assignments for this week."}
                        ]
                    }
                },
                "stopReason": "end_turn"
            }
        ]

        provider = BedrockProvider(model_id="anthropic.claude-3-haiku-20240307-v1:0", client=mock_client)
        loop = AgentLoop(student_id=1, provider=provider)
        res = loop.run_turn("What do I have to submit soon?")

        self.assertEqual(res["speech"], "You have 3 pending assignments for this week.")
        self.assertEqual(len(res["tool_calls_executed"]), 1)
        self.assertEqual(res["tool_calls_executed"][0]["tool_name"], "list_tasks")
        self.assertEqual(res["iterations"], 2)
        self.assertEqual(mock_client.converse.call_count, 2)

    def test_agent_loop_max_iteration_safety(self):
        # Model gets stuck in infinite tool loop -> loop must stop at max_iterations (5)
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "call_loop",
                                "name": "get_today_summary",
                                "input": {}
                            }
                        }
                    ]
                }
            },
            "stopReason": "tool_use"
        }

        provider = BedrockProvider(model_id="anthropic.claude-3-haiku-20240307-v1:0", client=mock_client)
        loop = AgentLoop(student_id=1, provider=provider, max_iterations=5)
        res = loop.run_turn("Give me an endless update")

        self.assertEqual(res["iterations"], 5)
        self.assertEqual(mock_client.converse.call_count, 5)

    def test_demo_provider_conversational_turn(self):
        demo = DemoProvider()
        loop = AgentLoop(student_id=1, provider=demo)
        res = loop.run_turn("show pending tasks")

        self.assertTrue(len(res["speech"]) > 0)
        self.assertEqual(len(res["tool_calls_executed"]), 1)
        self.assertEqual(res["tool_calls_executed"][0]["tool_name"], "list_tasks")


if __name__ == '__main__':
    unittest.main()
