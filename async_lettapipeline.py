"""
title: Async Letta Chat Pipeline
author: Cline (async adaptation)
date: 2024-01-18
version: 1.0
license: MIT
description: An asynchronous pipeline for processing messages through Letta chat API
requirements: pydantic, httpx
"""

from typing import List, Union, AsyncGenerator
from pydantic import BaseModel, ConfigDict
import json
import time
import httpx
from datetime import datetime

class Pipeline:
    class Valves(BaseModel):
        model_config = ConfigDict(protected_namespaces=())
        base_url: str = "https://100.93.254.12:8444"
        agent_id: str = "agent-379f4ef2-c678-4305-b69d-ac15986046c2"

    def __init__(self):
        self.name = "Async Letta Chat"
        self.valves = self.Valves()
        self.client = None
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

    async def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, AsyncGenerator]:
        """Process messages through the pipeline asynchronously"""
        if body.get("title", False):
            return self.name

        try:
            # Clean up payload
            payload = {**body}
            for key in ['user', 'chat_id', 'title']:
                payload.pop(key, None)

            # Record time before sending message
            request_time = time.time()

            async with httpx.AsyncClient(verify=False) as client:
                try:
                    # Send message
                    data = {
                        "messages": [
                            {
                                "text": user_message,
                                "role": "user"
                            }
                        ]
                    }

                    response = await client.post(
                        f"{self.valves.base_url}/v1/agents/{self.valves.agent_id}/messages",
                        json=data,
                        headers={'Content-Type': 'application/json'}
                    )
                    response_data = response.text
                    print(f"[DEBUG] Send response: {response_data}")

                    if response.status_code != 200:
                        error_msg = f"Failed to send message: {response_data}"
                        print(f"[ERROR] {error_msg}")
                        return error_msg

                    # Try to get response from the initial response
                    try:
                        initial_response = response.json()
                        for msg in initial_response.get('messages', []):
                            if msg.get('message_type') == 'tool_call_message':
                                tool_call = msg.get('tool_call', {})
                                if tool_call.get('name') == 'send_message':
                                    args = json.loads(tool_call.get('arguments', '{}'))
                                    content = args.get('message', '')
                                    if content:
                                        return content
                    except:
                        pass

                    # If no response in initial message, wait and try again
                    await asyncio.sleep(1)

                    try:
                        messages_response = await client.get(
                            f"{self.valves.base_url}/v1/agents/{self.valves.agent_id}/messages",
                            params={'limit': '10'}
                        )
                        messages_data = messages_response.text
                        print(f"[DEBUG] Messages response: {messages_data}")

                        if messages_response.status_code == 200:
                            messages = messages_response.json()
                            if isinstance(messages, list) and messages:
                                for msg in reversed(messages):
                                    if msg.get('message_type') == 'tool_call_message':
                                        tool_call = msg.get('tool_call', {})
                                        if tool_call.get('name') == 'send_message':
                                            try:
                                                args = json.loads(tool_call.get('arguments', '{}'))
                                                content = args.get('message', '')
                                                if content:
                                                    return content
                                            except:
                                                continue
                    except Exception as e:
                        print(f"[ERROR] Error getting messages: {e}")

                    return "I apologize, but I couldn't process your message at this time."

                except Exception as e:
                    error_msg = f"Error communicating with agent: {str(e)}"
                    print(f"[ERROR] {error_msg}")
                    return error_msg

    async def on_startup(self):
        """Initialize on startup"""
        pass

    async def on_shutdown(self):
        """Cleanup on shutdown"""
        pass

    async def on_valves_updated(self):
        """Handle valve updates"""
        pass