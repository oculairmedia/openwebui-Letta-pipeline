"""
title: Letta Chat Pipeline with OpenWebUI Tools Integration
author: Cline
date: 2024-01-17
version: 2.0
license: MIT
description: A pipeline that integrates any OpenWebUI tool results with Letta
requirements: pydantic, aiohttp, letta
"""

from typing import List, Union, Generator, Iterator, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
import json
import time
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

    def format_tool_results(self, tool_name: str, result: Any) -> str:
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

    async def inlet(self, body: dict, user: dict) -> dict:
        """Process incoming request before sending to agent"""
        print(f"[DEBUG] inlet - body: {body}")
        return body

    async def outlet(self, body: dict, user: dict) -> dict:
        """Process response after receiving from agent"""
        print(f"[DEBUG] outlet - body: {body}")
        return body

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

            # Extract tool results from the message history
            tool_results = []
            for msg in messages:
                if msg.get('role') == 'assistant' and 'tool_calls' in msg:
                    for tool_call in msg['tool_calls']:
                        if 'function' in tool_call:
                            tool_name = tool_call['function'].get('name', 'unknown_tool')
                            # Check if we have a result for this tool call
                            tool_id = tool_call.get('id')
                            if tool_id and 'tool_results' in body and tool_id in body['tool_results']:
                                result = body['tool_results'][tool_id]
                                tool_results.append(self.format_tool_results(tool_name, result))

            # If we have tool results, send them to Letta
            if tool_results:
                tool_info = "Here are the results from the tools:\n\n" + "\n".join(tool_results)
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
            response = self.client.send_message(
                agent_id=self.valves.agent_id,
                message=user_message,
                role="user"
            )
            
            # Get response after our request time
            response_text = self.get_response_message(self.valves.agent_id, request_time)
            
            if response_text:
                if payload.get("stream", False):
                    # For streaming, yield each character
                    for char in response_text:
                        yield char
                else:
                    return response_text
            else:
                return "I apologize, but I couldn't process your message at this time."

        except Exception as e:
            error_msg = f"Error communicating with agent: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return error_msg

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
    print(f"Agent response: {response}")