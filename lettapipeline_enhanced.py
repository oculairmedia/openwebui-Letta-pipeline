"""
title: Enhanced Letta Chat Pipeline
author: OpenHands
date: 2024-03-20
version: 2.0
license: MIT
description: An enhanced pipeline for processing messages through Letta chat API with improved tool handling
requirements: pydantic, aiohttp, letta, tenacity
"""

from typing import List, Union, Generator, Iterator, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field
import json
import time
import os
from enum import Enum
from tenacity import retry, stop_after_attempt, wait_exponential
from letta import create_client

class ToolStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"

class ToolResponse(BaseModel):
    """Model for tool execution responses"""
    tool_name: str
    tool_id: Optional[str] = None
    status: ToolStatus
    result: str
    stdout: Optional[List[str]] = None
    stderr: Optional[List[str]] = None

    def format_response(self) -> str:
        """Format tool response for display"""
        response = [f"Tool '{self.tool_name}' {self.status.value}"]
        if self.tool_id:
            response[0] += f" (ID: {self.tool_id})"
        response.append(f"Result: {self.result}")
        if self.stdout:
            response.append("Output:")
            response.extend(self.stdout)
        if self.stderr:
            response.append("Errors:")
            response.extend(self.stderr)
        return "\n".join(response)

class Pipeline:
    class Valves(BaseModel):
        model_config = ConfigDict(protected_namespaces=())
        base_url: str = Field(default_factory=lambda: os.getenv('LETTA_BASE_URL', 'http://192.168.50.90:8283'))
        agent_id: str = Field(default_factory=lambda: os.getenv('LETTA_AGENT_ID', 'agent-a3899314-bbb3-4798-b3f4-241923314b8e'))
        assistant_message_tool_name: Optional[str] = None
        assistant_message_tool_kwarg: Optional[str] = None
        include_base_tools: bool = True
        max_retries: int = 3
        retry_delay: int = 2
        max_attempts: int = 10
        stream_chunk_size: int = 1

    def __init__(self):
        self.name = "Enhanced Letta Chat"
        self.valves = self.Valves()
        self.client = self._create_client()
        self._initialize_pipeline()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _create_client(self):
        """Create Letta client with retry logic"""
        return create_client(base_url=self.valves.base_url)

    def _initialize_pipeline(self):
        """Initialize pipeline configuration"""
        print(f"[STARTUP] Starting {self.name}")
        print(f"[STARTUP] Configuration:")
        print(f"[STARTUP] - base_url: {self.valves.base_url}")
        print(f"[STARTUP] - agent_id: {self.valves.agent_id}")
        print(f"[STARTUP] - message_tool: {self.valves.assistant_message_tool_name}")
        
        # Configure tools
        self.configure_tools()

    def configure_tools(self):
        """Configure tools for the agent"""
        try:
            # Add base tools if needed
            if self.valves.include_base_tools:
                self.client.post("/v1/tools/add-base-tools")
            
            # Get current tools
            tools = self.list_tools()
            print(f"[STARTUP] Available tools: {tools}")
        except Exception as e:
            print(f"[ERROR] Error configuring tools: {str(e)}")

    def process_tool_call(self, tool_call) -> Optional[ToolResponse]:
        """Process a tool call and return formatted response"""
        try:
            if not hasattr(tool_call, 'function'):
                return None

            tool_name = tool_call.function.name
            tool_id = getattr(tool_call, 'id', None)
            
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                args = tool_call.function.arguments

            return ToolResponse(
                tool_name=tool_name,
                tool_id=tool_id,
                status=ToolStatus.SUCCESS,
                result=str(args),
                stdout=None,
                stderr=None
            )
        except Exception as e:
            return ToolResponse(
                tool_name=getattr(tool_call, 'function', {}).get('name', 'unknown'),
                status=ToolStatus.ERROR,
                result=f"Error processing tool call: {str(e)}"
            )

    def get_response_message(self, agent_id: str, after_time) -> Union[str, None]:
        """Get response message after specified time with enhanced tool handling"""
        try:
            attempt = 0
            while attempt < self.valves.max_attempts:
                messages = self.client.get_messages(agent_id=agent_id, limit=10)
                
                for msg in reversed(messages):
                    msg_time = msg.created_at.timestamp() if hasattr(msg, 'created_at') else 0
                    
                    if msg_time > after_time and msg.role == "assistant":
                        # Handle tool calls
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            tool_responses = []
                            for tool_call in msg.tool_calls:
                                tool_response = self.process_tool_call(tool_call)
                                if tool_response:
                                    tool_responses.append(tool_response.format_response())
                            
                            if tool_responses:
                                return "\n\n".join(tool_responses)
                        
                        # Handle tool returns
                        if hasattr(msg, 'tool_return'):
                            return ToolResponse(
                                tool_name="tool_return",
                                tool_id=getattr(msg, 'tool_call_id', None),
                                status=ToolStatus(getattr(msg, 'status', 'success')),
                                result=msg.tool_return,
                                stdout=getattr(msg, 'stdout', None),
                                stderr=getattr(msg, 'stderr', None)
                            ).format_response()
                        
                        # Handle regular messages
                        if hasattr(msg, 'text'):
                            return msg.text
                        elif hasattr(msg, 'message'):
                            return msg.message
                
                attempt += 1
                if attempt < self.valves.max_attempts:
                    time.sleep(self.valves.retry_delay)
            
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
        """Process messages through the pipeline with enhanced error handling"""
        if body.get("title", False):
            return self.name

        try:
            # Clean up payload
            payload = {**body}
            for key in ['user', 'chat_id', 'title']:
                payload.pop(key, None)

            # Record time before sending message
            request_time = time.time()
            
            # Send message with tool configuration
            response = self.client.send_message(
                agent_id=self.valves.agent_id,
                message=user_message,
                role="user",
                assistant_message_tool_name=self.valves.assistant_message_tool_name,
                assistant_message_tool_kwarg=self.valves.assistant_message_tool_kwarg
            )
            
            # Get response after our request time
            response_text = self.get_response_message(self.valves.agent_id, request_time)
            
            if response_text:
                if payload.get("stream", False):
                    # For streaming, yield in chunks
                    for i in range(0, len(response_text), self.valves.stream_chunk_size):
                        yield response_text[i:i + self.valves.stream_chunk_size]
                else:
                    return response_text
            else:
                return "I apologize, but I couldn't process your message at this time."

        except Exception as e:
            error_msg = self._format_error(e)
            print(f"[ERROR] {error_msg}")
            return error_msg

    def _format_error(self, error: Exception) -> str:
        """Format error messages with details"""
        error_type = error.__class__.__name__
        error_msg = str(error)
        return f"Error ({error_type}): {error_msg}"

    async def add_tool(self, tool_id: str) -> bool:
        """Add a tool to the agent"""
        try:
            await self.client.patch(f"/v1/agents/{self.valves.agent_id}/add-tool/{tool_id}")
            print(f"[INFO] Successfully added tool {tool_id}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to add tool {tool_id}: {str(e)}")
            return False

    async def remove_tool(self, tool_id: str) -> bool:
        """Remove a tool from the agent"""
        try:
            await self.client.patch(f"/v1/agents/{self.valves.agent_id}/remove-tool/{tool_id}")
            print(f"[INFO] Successfully removed tool {tool_id}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to remove tool {tool_id}: {str(e)}")
            return False

    def list_tools(self) -> List[str]:
        """List all tools available to the agent"""
        try:
            response = self.client.get(f"/v1/agents/{self.valves.agent_id}/tools")
            tools = getattr(response, 'tools', [])
            return [tool.name for tool in tools]
        except Exception as e:
            print(f"[ERROR] Failed to list tools: {str(e)}")
            return []

    async def on_startup(self):
        """Initialize on startup"""
        print(f"on_startup:{__name__}")
        await self._initialize_async()

    async def on_shutdown(self):
        """Cleanup on shutdown"""
        print(f"on_shutdown:{__name__}")
        await self._cleanup_async()

    async def on_valves_updated(self):
        """Handle valve updates"""
        self.client = self._create_client()
        print(f"[INFO] Updated client with new base_url: {self.valves.base_url}")
        await self.configure_tools()

    async def _initialize_async(self):
        """Async initialization tasks"""
        pass

    async def _cleanup_async(self):
        """Async cleanup tasks"""
        pass

# Example usage
if __name__ == "__main__":
    pipeline = Pipeline()
    
    # Example with tool calls
    test_body = {
        "stream": True,
        "tool_calls": [{
            "name": "test_tool",
            "arguments": {"arg1": "value1"}
        }]
    }
    
    response = pipeline.pipe(
        user_message="Test message with tool calls",
        model_id="default",
        messages=[],
        body=test_body
    )
    
    if isinstance(response, (Generator, Iterator)):
        print("Streaming response:")
        for chunk in response:
            print(chunk, end='')
    else:
        print(f"Direct response: {response}")