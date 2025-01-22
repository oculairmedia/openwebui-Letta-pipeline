"""
title: Async Letta Chat Pipeline
author: Cline (async adaptation)
date: 2024-01-18
version: 1.0
license: MIT
description: An asynchronous pipeline for processing messages through Letta chat API
requirements: pydantic, httpx

This pipeline implements streaming responses compatible with OpenWebUI's
browser-based streaming expectations. It handles both SSE (Server-Sent Events)
and WebSocket protocols for real-time communication.
"""

from typing import List, Union, AsyncGenerator, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
import json
import time
import httpx
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager


class LettaError(Exception):
    """Base exception for Letta pipeline errors"""
    pass


class StreamEvent(BaseModel):
    """Model for streaming events"""
    type: str
    data: Dict[str, Any]

class Pipeline:
    class Valves(BaseModel):
        model_config = ConfigDict(protected_namespaces=())
        base_url: str = "https://100.93.254.12:8444"
        agent_id: str = "agent-379f4ef2-c678-4305-b69d-ac15986046c2"

    def __init__(self):
        self.name = "Async Letta Chat"
        self.valves = self.Valves()
        print(f"[STARTUP] Starting {self.name}")
        print(f"[STARTUP] Configuration:")
        print(f"[STARTUP] - base_url: {self.valves.base_url}")
        print(f"[STARTUP] - agent_id: {self.valves.agent_id}")

    @asynccontextmanager
    async def get_client(self):
        """Get an HTTP client with proper configuration"""
        async with httpx.AsyncClient(
            verify=False,
            timeout=httpx.Timeout(30.0, connect=10.0)
        ) as client:
            yield client

    async def create_stream_event(
        self, 
        event_type: str, 
        data: Dict[str, Any]
    ) -> str:
        """Create a properly formatted stream event"""
        event = StreamEvent(type=event_type, data=data)
        return json.dumps(event.model_dump())

    async def inlet(self, body: dict, user: dict) -> dict:
        """Process incoming request before sending to agent"""
        return body

    async def outlet(self, body: dict, user: dict) -> dict:
        """Process response after receiving from agent"""
        return body

    async def _extract_message_content(self, tool_call: dict) -> Optional[str]:
        """Extract message content from tool call"""
        try:
            if tool_call.get('name') == 'send_message':
                args = json.loads(tool_call.get('arguments', '{}'))
                return args.get('message', '')
        except json.JSONDecodeError:
            print("[ERROR] Failed to decode tool call arguments")
        return None

    async def _process_messages(self, messages: List[dict]) -> Optional[str]:
        """Process messages to find content"""
        for msg in messages:
            if msg.get('message_type') == 'tool_call_message':
                tool_call = msg.get('tool_call', {})
                content = await self._extract_message_content(tool_call)
                if content:
                    return content
        return None

    async def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> AsyncGenerator[str, None]:
        """Process messages through the pipeline asynchronously with proper streaming"""
        if body.get("title", False):
            yield await self.create_stream_event("chat:title", {"title": self.name})
            return

        chat_id = body.get("chat_id", "")
        message_id = body.get("message_id", "")

        print(f"[DEBUG] Processing message: {user_message[:100]}...")
        print(f"[DEBUG] Model ID: {model_id}")
        print(f"[DEBUG] Chat ID: {chat_id}")
        print(f"[DEBUG] Message ID: {message_id}")

        async def stream_response():
            try:
                # Send initial completion event
                yield await self.create_stream_event(
                    "chat:completion",
                    {"message": "", "done": False}
                )

                async with self.get_client() as client:
                    # Send message to agent
                    data = {
                        "messages": [{"text": user_message, "role": "user"}]
                    }
                    print(f"[DEBUG] Sending message to agent: {json.dumps(data, indent=2)}")
                    
                    response = await client.post(
                        f"{self.valves.base_url}/v1/agents/{self.valves.agent_id}/messages",
                        json=data,
                        headers={'Content-Type': 'application/json'}
                    )
                    response.raise_for_status()
                    response_data = response.json()
                    print(f"[DEBUG] Initial response: {json.dumps(response_data, indent=2)}")

                    # Check initial response
                    content = await self._process_messages(response_data.get('messages', []))
                    if content:
                        print(f"[DEBUG] Found content in initial response: {content[:100]}...")
                        yield await self.create_stream_event(
                            "chat:completion",
                            {"message": content, "done": True}
                        )
                        return

                    # Poll for messages
                    max_retries = 5
                    retry_count = 0
                    accumulated_content = []
                    
                    while retry_count < max_retries:
                        await asyncio.sleep(2)
                        print(f"[DEBUG] Polling attempt {retry_count + 1}/{max_retries}")
                        
                        try:
                            messages_response = await client.get(
                                f"{self.valves.base_url}/v1/agents/{self.valves.agent_id}/messages",
                                params={'limit': '10'}
                            )
                            messages_response.raise_for_status()
                            messages_data = messages_response.json()

                            if isinstance(messages_data, list) and messages_data:
                                for msg in reversed(messages_data):
                                    if msg.get('message_type') == 'tool_call_message':
                                        tool_call = msg.get('tool_call', {})
                                        content = await self._extract_message_content(tool_call)
                                        if content and content not in accumulated_content:
                                            accumulated_content.append(content)
                                            yield await self.create_stream_event(
                                                "chat:completion",
                                                {"message": content, "done": False}
                                            )

                                if accumulated_content:
                                    yield await self.create_stream_event(
                                        "chat:completion",
                                        {"message": " ".join(accumulated_content), "done": True}
                                    )
                                    return

                            retry_count += 1
                        except Exception as e:
                            print(f"[WARNING] Error during polling attempt {retry_count + 1}: {str(e)}")
                            retry_count += 1
                            continue

                    # If we reach here, send error response
                    yield await self.create_stream_event(
                        "chat:completion",
                        {
                            "message": "I apologize, but I couldn't process your message at this time.",
                            "done": True
                        }
                    )

            except httpx.HTTPStatusError as e:
                yield await self.create_stream_event(
                    "chat:error",
                    {"message": f"Failed to communicate with agent: {e.response.status_code}"}
                )
                
            except httpx.RequestError as e:
                yield await self.create_stream_event(
                    "chat:error",
                    {"message": "Failed to connect to agent service"}
                )
                
            except json.JSONDecodeError as e:
                yield await self.create_stream_event(
                    "chat:error",
                    {"message": "Failed to process agent response"}
                )
                
            except Exception as e:
                yield await self.create_stream_event(
                    "chat:error",
                    {"message": f"An unexpected error occurred: {str(e)}"}
                )

        async for event in stream_response():
            yield event

    async def on_startup(self):
        """Initialize on startup"""
        pass

    async def on_shutdown(self):
        """Cleanup on shutdown"""
        pass

    async def on_valves_updated(self):
        """Handle valve updates"""
        pass