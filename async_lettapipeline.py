"""
title: Async Letta Chat Pipeline
author: Cline (async adaptation)
date: 2024-01-18
version: 1.0
license: MIT
description: An asynchronous pipeline for processing messages through Letta chat API
requirements: pydantic, httpx
"""

from typing import List, Union, AsyncGenerator, Optional
from pydantic import BaseModel, ConfigDict
import json
import time
import httpx
import asyncio
from datetime import datetime


class LettaError(Exception):
    """Base exception for Letta pipeline errors"""
    pass


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
    ) -> str:
        """Process messages through the pipeline asynchronously"""
        if body.get("title", False):
            return self.name

        # Clean up payload
        payload = {**body}
        for key in ['user', 'chat_id', 'title']:
            payload.pop(key, None)

        async with httpx.AsyncClient(verify=False) as client:
            try:
                # Send initial message
                data = {
                    "messages": [{"text": user_message, "role": "user"}]
                }
                response = await client.post(
                    f"{self.valves.base_url}/v1/agents/{self.valves.agent_id}/messages",
                    json=data,
                    headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()
                response_data = response.json()
                
                # Check initial response
                content = await self._process_messages(response_data.get('messages', []))
                if content:
                    return content

                # Wait and try to get response from messages endpoint
                await asyncio.sleep(1)
                
                messages_response = await client.get(
                    f"{self.valves.base_url}/v1/agents/{self.valves.agent_id}/messages",
                    params={'limit': '10'}
                )
                messages_response.raise_for_status()
                messages_data = messages_response.json()

                if isinstance(messages_data, list) and messages_data:
                    content = await self._process_messages(reversed(messages_data))
                    if content:
                        return content

                return "I apologize, but I couldn't process your message at this time."

            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP error occurred: {str(e)}"
                print(f"[ERROR] {error_msg}")
                return f"Failed to communicate with agent: {e.response.status_code}"
                
            except httpx.RequestError as e:
                error_msg = f"Request error occurred: {str(e)}"
                print(f"[ERROR] {error_msg}")
                return "Failed to connect to agent service"
                
            except json.JSONDecodeError as e:
                error_msg = f"JSON decode error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                return "Failed to process agent response"
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                print(f"[ERROR] {error_msg}")
                return "An unexpected error occurred"

    async def on_startup(self):
        """Initialize on startup"""
        pass

    async def on_shutdown(self):
        """Cleanup on shutdown"""
        pass

    async def on_valves_updated(self):
        """Handle valve updates"""
        pass