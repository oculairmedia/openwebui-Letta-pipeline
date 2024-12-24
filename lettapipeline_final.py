"""
title: Letta Chat Pipeline with OpenWebUI Tool Integration
author: Cline
date: 2024-01-17
version: 3.0
license: MIT
description: A pipeline that properly integrates OpenWebUI tool results with Letta via system messages
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

    def stream_response(self, response: str) -> Generator[str, None, None]:
        """Stream a response one character at a time"""
        for char in response:
            yield char
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

            # Extract context and tool results from messages
            context_messages = []
            
            for msg in messages:
                # Handle system messages (context)
                if msg.get('role') == 'system':
                    context = msg.get('content', '')
                    if context:
                        context_messages.append(context)
                
                # Handle assistant messages with tool calls and results
                elif msg.get('role') == 'assistant' and 'tool_calls' in msg:
                    for tool_call in msg['tool_calls']:
                        if 'function' in tool_call:
                            tool_id = tool_call.get('id')
                            tool_name = tool_call['function'].get('name', 'unknown_tool')
                            
                            # Get tool result if available
                            if tool_id and 'tool_results' in body and tool_id in body['tool_results']:
                                result = body['tool_results'][tool_id]
                                # Format tool result as system message
                                tool_msg = f"Tool '{tool_name}' result:\n"
                                if isinstance(result, str):
                                    try:
                                        # Try to parse JSON
                                        data = json.loads(result)
                                        tool_msg += json.dumps(data, indent=2)
                                    except json.JSONDecodeError:
                                        tool_msg += result
                                else:
                                    tool_msg += json.dumps(result, indent=2)
                                context_messages.append(tool_msg)

            # Send all context messages to Letta
            if context_messages:
                context_text = "\n\n".join(context_messages)
                print(f"[DEBUG] Sending context to Letta:\n{context_text}")
                self.client.send_message(
                    agent_id=self.valves.agent_id,
                    message=context_text,
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
    
    # Example with context and tool results
    test_body = {
        "tool_results": {
            "call_abc123": {
                "status": "OK",
                "message": "Current temperature is 15°C",
                "time": "2024-01-17 09:36:12 AM UTC+0000"
            }
        },
        "messages": [
            {
                "role": "system",
                "content": "Retrieved weather data for Eindhoven"
            },
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