"""
title: Letta Chat Pipeline (Development Version)
author: Cline
date: 2024-01-17
version: 1.0
license: MIT
description: A pipeline for processing messages through Letta chat API
requirements: pydantic, urllib3
"""

from typing import List, Union, Generator, Iterator
from pydantic import BaseModel, ConfigDict
import json
import time
import os
from datetime import datetime
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL verification warnings
urllib3.disable_warnings(InsecureRequestWarning)

# Create a connection pool with SSL verification disabled
def create_http():
    return urllib3.PoolManager(
        cert_reqs='CERT_NONE',
        assert_hostname=False,
        retries=urllib3.Retry(3)
    )

class Pipeline:
    class Valves(BaseModel):
        model_config = ConfigDict(protected_namespaces=())
        base_url: str = "https://100.93.254.12:8444"
        agent_id: str = "agent-379f4ef2-c678-4305-b69d-ac15986046c2"

    def __init__(self):
        self.name = "Letta Chat"
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
            
            # Create HTTP client
            http = create_http()
            
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
                encoded_data = json.dumps(data).encode('utf-8')
                response = http.request(
                    'POST',
                    f"{self.valves.base_url}/v1/agents/{self.valves.agent_id}/messages",
                    body=encoded_data,
                    headers={'Content-Type': 'application/json'}
                )
                response_data = response.data.decode('utf-8')
                print(f"[DEBUG] Send response: {response_data}")
                
                if response.status != 200:
                    error_msg = f"Failed to send message: {response_data}"
                    print(f"[ERROR] {error_msg}")
                    return error_msg
                
                # Try to get response from the initial response
                try:
                    initial_response = json.loads(response_data)
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
                time.sleep(1)
                
                try:
                    messages_response = http.request(
                        'GET',
                        f"{self.valves.base_url}/v1/agents/{self.valves.agent_id}/messages",
                        fields={'limit': '10'}
                    )
                    messages_data = messages_response.data.decode('utf-8')
                    print(f"[DEBUG] Messages response: {messages_data}")
                    
                    if messages_response.status == 200:
                        messages = json.loads(messages_response.data.decode('utf-8'))
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
            finally:
                http.clear()

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
