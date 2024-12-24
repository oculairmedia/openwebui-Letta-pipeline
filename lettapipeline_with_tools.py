"""
title: Letta Chat Pipeline with OpenWebUI Tools
author: Cline
date: 2024-01-17
version: 2.0
license: MIT
description: A pipeline for processing messages through Letta chat API with OpenWebUI tool support
requirements: pydantic, aiohttp, letta
"""

from typing import List, Union, Generator, Iterator, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
import json
import time
import asyncio
from letta import create_client

class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: Dict[str, Any]

class OpenWebUITool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

class Pipeline:
    class Valves(BaseModel):
        model_config = ConfigDict(protected_namespaces=())
        base_url: str = "http://192.168.50.90:8283"
        agent_id: str = "agent-a3899314-bbb3-4798-b3f4-241923314b8e"
        openwebui_tools: List[OpenWebUITool] = []

    def __init__(self):
        self.name = "Letta Chat with Tools"
        self.valves = self.Valves()
        self.client = create_client(base_url=self.valves.base_url)
        self.tool_results: Dict[str, Any] = {}
        print(f"[STARTUP] Starting {self.name}")
        print(f"[STARTUP] Configuration:")
        print(f"[STARTUP] - base_url: {self.valves.base_url}")
        print(f"[STARTUP] - agent_id: {self.valves.agent_id}")
        print(f"[STARTUP] - tools: {len(self.valves.openwebui_tools)} configured")

    def register_tool(self, tool: OpenWebUITool):
        """Register a new OpenWebUI tool"""
        self.valves.openwebui_tools.append(tool)
        print(f"[INFO] Registered tool: {tool.name}")

    async def execute_tool(self, tool_call: ToolCall) -> Optional[str]:
        """Execute an OpenWebUI tool and return the result"""
        try:
            tool_name = tool_call.function.get("name")
            tool_args = json.loads(tool_call.function.get("arguments", "{}"))
            
            # Find matching tool
            tool = next((t for t in self.valves.openwebui_tools 
                        if t.name == tool_name), None)
            
            if not tool:
                return f"Tool '{tool_name}' not found"

            # Store tool call in results
            self.tool_results[tool_call.id] = {
                "name": tool_name,
                "arguments": tool_args,
                "status": "executing"
            }

            # Here you would implement the actual tool execution
            # For now, we'll simulate tool execution
            await asyncio.sleep(0.5)  # Simulate tool execution time
            
            result = f"Executed {tool_name} with args: {tool_args}"
            self.tool_results[tool_call.id]["status"] = "completed"
            self.tool_results[tool_call.id]["result"] = result
            
            return result
            
        except Exception as e:
            error_msg = f"Error executing tool: {str(e)}"
            print(f"[ERROR] {error_msg}")
            if tool_call.id in self.tool_results:
                self.tool_results[tool_call.id]["status"] = "failed"
                self.tool_results[tool_call.id]["error"] = error_msg
            return error_msg

    def get_response_message(self, agent_id: str, after_time) -> Union[str, None]:
        """Get response message after specified time"""
        try:
            max_attempts = 5
            attempt = 0
            
            while attempt < max_attempts:
                messages = self.client.get_messages(agent_id=agent_id, limit=10)
                
                for msg in reversed(messages):
                    msg_time = msg.created_at.timestamp() if hasattr(msg, 'created_at') else 0
                    
                    if msg_time > after_time:
                        if msg.role == "assistant":
                            # Handle tool calls
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                tool_responses = []
                                for tool_call in msg.tool_calls:
                                    # Check if it's an OpenWebUI tool
                                    if any(t.name == tool_call.function.name 
                                         for t in self.valves.openwebui_tools):
                                        result = asyncio.run(self.execute_tool(tool_call))
                                        if result:
                                            tool_responses.append(result)
                                
                                if tool_responses:
                                    return "\n".join(tool_responses)
                                    
                            # Handle regular messages
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

            # Record time before sending message
            request_time = time.time()
            
            # Send message to agent
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
    
    # Register example tools
    example_tool = OpenWebUITool(
        name="search_web",
        description="Search the web for information",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    )
    pipeline.register_tool(example_tool)
    
    # Send a test message
    response = pipeline.pipe(
        user_message="Search the web for 'Python programming'",
        model_id="default",
        messages=[],
        body={}
    )
    print(f"Agent response: {response}")