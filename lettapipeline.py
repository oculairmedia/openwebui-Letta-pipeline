"""
title: Letta Chat Pipeline (Development Version)
author: Cline
date: 2024-01-17
version: 1.0
license: MIT
description: A pipeline for processing messages through Letta chat API
requirements: pydantic, aiohttp, letta
"""

from typing import List, Union, Generator, Iterator
from pydantic import BaseModel, ConfigDict
import json
import time
import os
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
        
        # Disable SSL verification warnings since we're using a self-signed cert
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Patch the session to disable SSL verification
        import requests
        requests.packages.urllib3.disable_warnings()
        session = requests.Session()
        session.verify = False
        
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
                if not messages:
                    print("[DEBUG] No messages received")
                    attempt += 1
                    if attempt < max_attempts:
                        time.sleep(1)
                    continue

                print(f"[DEBUG] Got {len(messages)} messages")
                
                # Convert messages to list if it's not already
                if not isinstance(messages, list):
                    messages = [messages]
                
                for msg in reversed(messages):
                    # Debug message attributes
                    print(f"[DEBUG] Message attributes: {dir(msg)}")
                    
                    # Get message time safely
                    msg_time = getattr(msg, 'created_at', None)
                    if msg_time and hasattr(msg_time, 'timestamp'):
                        msg_time = msg_time.timestamp()
                    else:
                        msg_time = 0
                    
                    # Get message role safely
                    msg_role = getattr(msg, 'role', None)
                    
                    if msg_time > after_time and msg_role == "assistant":
                        # Try to get content from various attributes
                        if hasattr(msg, 'content'):
                            return msg.content
                        elif hasattr(msg, 'text'):
                            return msg.text
                        elif hasattr(msg, 'message'):
                            return msg.message
                        
                        # Check for tool calls
                        tool_calls = getattr(msg, 'tool_calls', None)
                        if tool_calls:
                            for tool_call in tool_calls:
                                if hasattr(tool_call, 'function'):
                                    func = tool_call.function
                                    if getattr(func, 'name', '') == 'send_message':
                                        try:
                                            args = json.loads(func.arguments)
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

    async def inlet(self, body: dict, user: dict) -> dict:
        """Process incoming request before sending to agent"""
        print(f"[DEBUG] inlet - body: {body}")
        return body

    async def outlet(self, body: dict, user: dict) -> dict:
        """Process response after receiving from agent"""
        print(f"[DEBUG] outlet - body: {body}")
        return body

    async def _send_message(self, session, user_message: str):
        """Send a message to the agent using aiohttp"""
        data = {
            "message": user_message,
            "role": "user"
        }
        async with session.post(
            f"{self.valves.base_url}/v1/agents/{self.valves.agent_id}/messages",
            json=data
        ) as response:
            return await response.json()

    async def _get_messages(self, session, limit: int = 10):
        """Get messages from the agent using aiohttp"""
        async with session.get(
            f"{self.valves.base_url}/v1/agents/{self.valves.agent_id}/messages",
            params={"limit": limit}
        ) as response:
            return await response.json()

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
            
            # Return response
            return response_text

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
    
    # Send a test message
    response = pipeline.pipe(
        user_message="Hello! How are you?",
        model_id="default",
        messages=[],
        body={}
    )
    print(f"Agent response: {response}")
