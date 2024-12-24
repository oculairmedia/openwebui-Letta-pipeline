"""
title: Letta Chat Pipeline with OpenWebUI Integration
author: Cline
date: 2024-01-17
version: 3.7
license: MIT
description: A pipeline that sends the complete debug output to Letta
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
        self.name = "Letta Chat with OpenWebUI Integration"
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
                        # Look for send_message tool call
                        if hasattr(msg, 'tool_calls'):
                            for tool_call in msg.tool_calls:
                                if (hasattr(tool_call, 'function') and 
                                    tool_call.function.name == 'send_message'):
                                    try:
                                        args = json.loads(tool_call.function.arguments)
                                        if 'message' in args:
                                            return args['message']
                                    except:
                                        continue
                
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

            # Format the debug output exactly as it appears
            debug_output = f"[DEBUG] outlet - body: {json.dumps(body)}"
            
            # Send as system message with XML tags
            system_message = (
                "Use the following context as your learned knowledge, "
                "inside <context></context> XML tags.\n"
                "<context>\n" +
                debug_output +
                "\n</context>"
            )
            
            print(f"[DEBUG] Sending system message to Letta:\n{system_message}")
            self.client.send_message(
                agent_id=self.valves.agent_id,
                message=system_message,
                role="system"
            )

            # Record time before sending user message
            request_time = time.time()
            
            # Send user message to Letta
            self.client.send_message(
                agent_id=self.valves.agent_id,
                message=user_message,
                role="user"
            )
            
            # Get Letta's response (from send_message tool call)
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
    
    # Example with complete body
    test_body = {
        "model": "lettapipeline_final",
        "messages": [
            {
                "id": "user-msg-id",
                "role": "user",
                "content": "Explain options trading"
            },
            {
                "id": "assistant-msg-id",
                "role": "assistant",
                "content": "Here's an explanation...",
                "sources": [
                    {
                        "source": {
                            "urls": ["https://example.com"],
                            "type": "web_search_results"
                        },
                        "document": ["Options trading information..."]
                    }
                ]
            }
        ]
    }
    
    response = pipeline.pipe(
        user_message="Explain options trading",
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