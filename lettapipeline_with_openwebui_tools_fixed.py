"""
title: Letta Chat Pipeline with OpenWebUI Tools Integration (Fixed Message Channel)
author: Cline
date: 2024-01-17
version: 2.1
license: MIT
description: A pipeline that integrates OpenWebUI tools with Letta, with improved message handling
requirements: pydantic, aiohttp, letta
"""

from typing import List, Union, Generator, Iterator, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
import json
import time
import asyncio
from letta import create_client

class Pipeline:
    class Valves(BaseModel):
        model_config = ConfigDict(protected_namespaces=())
        base_url: str = "http://192.168.50.90:8283"
        agent_id: str = "agent-a3899314-bbb3-4798-b3f4-241923314b8e"

    def __init__(self):
        self.name = "Letta Chat with OpenWebUI Tools"
        self.valves = self.Valves()
        self.client = create_client(base_url=self.valves.base_url)
        print(f"[STARTUP] Starting {self.name}")
        print(f"[STARTUP] Configuration:")
        print(f"[STARTUP] - base_url: {self.valves.base_url}")
        print(f"[STARTUP] - agent_id: {self.valves.agent_id}")

    def get_response_message(self, agent_id: str, after_time) -> Union[str, None]:
        """Get response message after specified time"""
        try:
            max_attempts = 5
            attempt = 0
            
            while attempt < max_attempts:
                messages = self.client.get_messages(agent_id=agent_id, limit=10)
                
                for msg in reversed(messages):
                    msg_time = msg.created_at.timestamp() if hasattr(msg, 'created_at') else 0
                    
                    if msg_time > after_time and msg.role == "assistant":
                        if hasattr(msg, 'text'):
                            return msg.text
                        elif hasattr(msg, 'message'):
                            return msg.message
                
                attempt += 1
                if attempt < max_attempts:
                    time.sleep(1)
            
            return None
        except Exception as e:
            print(f"[ERROR] Error getting response message: {str(e)}")
            return None

    def format_tool_result(self, tool_name: str, result: Any) -> str:
        """Format a single tool result into a clear message"""
        try:
            if isinstance(result, str):
                try:
                    # Try to parse as JSON if it's a string
                    data = json.loads(result)
                    return f"Tool '{tool_name}' returned:\n{json.dumps(data, indent=2)}\n"
                except json.JSONDecodeError:
                    # If not JSON, return as is
                    return f"Tool '{tool_name}' returned: {result}\n"
            elif isinstance(result, (dict, list)):
                return f"Tool '{tool_name}' returned:\n{json.dumps(result, indent=2)}\n"
            else:
                return f"Tool '{tool_name}' returned: {str(result)}\n"
        except Exception as e:
            print(f"[WARNING] Error formatting tool result: {str(e)}")
            return f"Tool '{tool_name}' returned a result (format error)\n"

    def process_tool_results(self, messages: List[dict], tool_results: Dict) -> Optional[str]:
        """Process and format all tool results from the conversation"""
        if not messages or not tool_results:
            return None

        formatted_results = []
        
        # Track processed tool calls to avoid duplicates
        processed_tools = set()

        # Process messages in reverse to get the most recent tool calls first
        for msg in reversed(messages):
            if msg.get('role') == 'assistant' and 'tool_calls' in msg:
                for tool_call in msg['tool_calls']:
                    if 'function' in tool_call:
                        tool_id = tool_call.get('id')
                        tool_name = tool_call['function'].get('name', 'unknown_tool')
                        
                        # Only process each tool once
                        tool_key = f"{tool_id}_{tool_name}"
                        if tool_key in processed_tools:
                            continue
                        processed_tools.add(tool_key)

                        # Get tool result if available
                        if tool_id and tool_id in tool_results:
                            result = tool_results[tool_id]
                            formatted_result = self.format_tool_result(tool_name, result)
                            formatted_results.append(formatted_result)

        if formatted_results:
            return "Here are the results from the tools:\n\n" + "\n".join(formatted_results)
        return None

    def stream_response(self, response: str) -> Generator[str, None, None]:
        """Stream a response one character at a time with proper timing"""
        for char in response:
            yield char
            # Small delay to prevent overwhelming the channel
            time.sleep(0.001)

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """Process messages through the pipeline"""
        if body.get("title", False):
            return self.name

        try:
            # Clean up payload
            payload = {**body}
            for key in ['user', 'chat_id', 'title']:
                payload.pop(key, None)

            # Get tool results from the body
            tool_results = body.get('tool_results', {})
            
            # Process tool results if available
            tool_info = self.process_tool_results(messages, tool_results)
            if tool_info:
                print(f"[DEBUG] Sending tool results to Letta:\n{tool_info}")
                # Send tool results as system message
                self.client.send_message(
                    agent_id=self.valves.agent_id,
                    message=tool_info,
                    role="system"
                )

            # Record time before sending user message
            request_time = time.time()
            
            # Send user message to agent
            self.client.send_message(
                agent_id=self.valves.agent_id,
                message=user_message,
                role="user"
            )
            
            # Get response after our request time
            response_text = self.get_response_message(self.valves.agent_id, request_time)
            
            if response_text:
                if payload.get("stream", False):
                    # Use the streaming generator with proper timing
                    return self.stream_response(response_text)
                else:
                    return response_text
            else:
                return "I apologize, but I couldn't process your message at this time."

        except Exception as e:
            error_msg = f"Error communicating with agent: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return error_msg

    async def inlet(self, body: dict, user: dict) -> dict:
        """Process incoming request before sending to agent"""
        print(f"[DEBUG] inlet - body: {body}")
        return body

    async def outlet(self, body: dict, user: dict) -> dict:
        """Process response after receiving from agent"""
        print(f"[DEBUG] outlet - body: {body}")
        return body

    async def on_startup(self):
        """Initialize on startup"""
        print(f"on_startup:{__name__}")
        pass

    async def on_shutdown(self):
        """Cleanup on shutdown"""
        print(f"on_shutdown:{__name__}")
        pass

    async def on_valves_updated(self):
        """Handle valve updates"""
        self.client = create_client(base_url=self.valves.base_url)
        print(f"[INFO] Updated client with new base_url: {self.valves.base_url}")

# Example usage
if __name__ == "__main__":
    pipeline = Pipeline()
    
    # Example with tool results
    test_body = {
        "tool_results": {
            "call_abc123": {
                "status": "OK",
                "message": "Weather data retrieved",
                "time": "2024-01-17 09:36:12 AM UTC+0000"
            }
        },
        "messages": [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_abc123",
                        "function": {
                            "name": "get_weather",
                            "arguments": "{\"location\": \"Eindhoven\"}"
                        }
                    }
                ]
            }
        ]
    }
    
    response = pipeline.pipe(
        user_message="How's the weather?",
        model_id="default",
        messages=test_body["messages"],
        body=test_body
    )
    
    if isinstance(response, (Generator, Iterator)):
        print("Streaming response:")
        for chunk in response:
            print(chunk, end='', flush=True)
        print()
    else:
        print(f"Agent response: {response}")