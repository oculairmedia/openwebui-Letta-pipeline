"""
title: Letta Manifold Pipe
author: [Your Name]
author_url: [Your GitHub URL]
funding_url: https://github.com/open-webui
version: 0.1.0
license: MIT
"""
import os
import json
from pydantic import BaseModel, Field
from typing import List, Union, Iterator, Generator
from fastapi import Request
from open_webui.utils.chat import generate_chat_completion
from open_webui.models.users import Users
import urllib3
import base64

# Disable SSL warnings temporarily
urllib3.disable_warnings()

class Pipe:
    class Valves(BaseModel):
        LETTA_BASE_URL: str = Field(
            default=os.getenv("LETTA_BASE_URL", "https://letta.oculair.ca"),
            description="Base URL for Letta API"
        )
        LETTA_AGENT_ID: str = Field(
            default=os.getenv("LETTA_AGENT_ID", ""),
            description="Agent ID for Letta authentication"
        )
        LETTA_PASSWORD: str = Field(
            default=os.getenv("LETTA_PASSWORD", ""),
            description="Password for Letta authentication"
        )
        ENABLE_TOOLS: bool = Field(
            default=True,
            description="Enable Open WebUI tool integration"
        )

    def __init__(self):
        self.id = "letta_ai"
        self.type = "manifold"
        self.name = "Letta: "
        self.valves = self.Valves()
        self.http = urllib3.PoolManager(
            cert_reqs='CERT_NONE',
            headers={
                'X-BARE-PASSWORD': f'password {self.valves.LETTA_PASSWORD}',
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            }
        )

    def pipes(self) -> List[dict]:
        """Fetch available Letta configurations"""
        return [{
            "id": f"letta.{self.valves.LETTA_AGENT_ID}",
            "name": f"Letta Agent {self.valves.LETTA_AGENT_ID[-6:]}",
            "meta": {
                "provider": "letta",
                "agent_id": self.valves.LETTA_AGENT_ID
            }
        }]

    def pipe(self, body: dict, __user__: dict, __request__: Request) -> Union[str, Iterator[str]]:
        """Main processing pipeline with tool support"""
        try:
            # Handle tool execution via Open WebUI
            if body.get("tools") and self.valves.ENABLE_TOOLS:
                user = Users.get_user_by_id(__user__["id"])
                return generate_chat_completion(__request__, body, user)
            
            # Process Letta request
            messages = self._format_messages(body["messages"])
            
            # Only send the last message
            last_message = messages[-1] if messages else {}
            
            # Prepare Letta API payload
            payload = {
                "messages": [last_message],
                "stream_steps": True,
                "stream_tokens": True
            }
            
            print(f"DEBUG: Last message: {json.dumps(last_message, indent=2)}")
            print(f"DEBUG: Full payload: {json.dumps(payload, indent=2)}")

            # Always use streaming
            url = f"{self.valves.LETTA_BASE_URL}/v1/agents/{self.valves.LETTA_AGENT_ID}/messages/stream"
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream',
                'X-BARE-PASSWORD': f'password {self.valves.LETTA_PASSWORD}'
            }
            print(f"DEBUG: URL: {url}")
            print(f"DEBUG: Headers: {headers}")
            print(f"DEBUG: Payload: {payload}")
            
            return self._handle_streaming(url, payload, headers)

        except Exception as e:
            error_message = f"Letta Error: {str(e)}"
            print(f"DEBUG: {error_message}")
            print(f"DEBUG: Exception type: {type(e).__name__}")
            print(f"DEBUG: Exception args: {e.args}")
            return error_message

    def _format_messages(self, messages: list) -> list:
        """Convert Open WebUI format to Letta format"""
        formatted = []
        for msg in messages:
            formatted_msg = {
                "role": "system" if msg["role"] == "system" else "user",
                "text": msg["content"]
            }
            formatted.append(formatted_msg)
        return formatted

    def _handle_streaming(self, url: str, payload: dict, headers: dict) -> Generator:
        """Handle streaming responses"""
        def generator():
            response = None  # Initialize response variable
            try:
                print(f"DEBUG: Sending request to URL: {url}")
                print(f"DEBUG: Headers: {json.dumps(headers, indent=2)}")
                print(f"DEBUG: Payload: {json.dumps(payload, indent=2)}")
                
                response = self.http.request(
                    'POST',
                    url,
                    body=json.dumps(payload),
                    preload_content=False,
                    headers=headers
                )
                
                print(f"DEBUG: Response status: {response.status}")
                print(f"DEBUG: Response headers: {json.dumps(dict(response.headers), indent=2)}")
                
                for chunk in response.stream():
                    decoded_chunk = chunk.decode('utf-8')
                    print(f"DEBUG: Received chunk: {decoded_chunk}")
                    
                    # Parse the chunk and yield relevant information
                    chunks = decoded_chunk.split('\n\n')
                    for chunk in chunks:
                        if chunk.startswith('data: '):
                            try:
                                chunk_data = json.loads(chunk[6:])  # Remove 'data: ' prefix
                                print(f"DEBUG: Parsed chunk data: {json.dumps(chunk_data, indent=2)}")
                                
                                if chunk_data.get('message_type') == 'assistant_message':
                                    message = chunk_data.get('assistant_message', '')
                                    if message:
                                        print(f"DEBUG: Yielding message: {message}")
                                        yield message + "\n"
                                elif chunk_data.get('message_type') == 'usage_statistics':
                                    print("DEBUG: Received usage statistics")
                                else:
                                    print(f"DEBUG: Unhandled message type: {chunk_data.get('message_type')}")
                            except json.JSONDecodeError:
                                print(f"DEBUG: Failed to parse chunk: {chunk}")
                        elif chunk.strip() == 'data: [DONE]':
                            print("DEBUG: Received DONE signal")
                            # We don't need to yield anything for the DONE signal
                            return
                        else:
                            print(f"DEBUG: Unhandled chunk format: {chunk}")
                
                # Signal completion
                print("DEBUG: Signaling completion")
                    
            except Exception as e:
                print(f"DEBUG: Streaming error: {str(e)}")
                yield json.dumps({"type": "chat:error", "data": {"message": f"Error during streaming: {str(e)}"}})
            finally:
                if response is not None:  # Only release if response exists
                    response.release_conn()

        return generator()

    def _parse_response(self, response) -> str:
        """Parse Letta API response"""
        if response.status != 200:
            return f"Error: {response.status} - {response.data.decode()}"
            
        try:
            data = json.loads(response.data.decode())
            return data["choices"][0]["message"]["content"]
        except KeyError:
            return "Error: Invalid response format from Letta"

    async def on_valves_updated(self):
        """Update HTTP client when valves change"""
        self.http = urllib3.PoolManager(
            cert_reqs='CERT_NONE',
            headers={
                'X-BARE-PASSWORD': f'password {self.valves.LETTA_PASSWORD}',
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            }
        )