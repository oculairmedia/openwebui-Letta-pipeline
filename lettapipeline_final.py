"""
title: Letta Chat Pipeline with OpenWebUI Integration
author: Cline
date: 2024-01-17
version: 3.3
license: MIT
description: A pipeline that properly integrates OpenWebUI information with Letta using XML context format
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

    def format_source_content(self, source: Dict[str, Any]) -> str:
        """Format source content into XML context format"""
        try:
            source_elements = []
            
            # Add source information
            if 'source' in source:
                src_info = source['source']
                source_elements.append("<source>")
                
                # Add source URL if available
                if 'urls' in src_info and src_info['urls']:
                    source_elements.append(f"<source_id>{src_info['urls'][0]}</source_id>")
                
                # Add source content
                if 'document' in source:
                    source_content = []
                    if isinstance(source['document'], list):
                        source_content.extend(str(doc).replace('\xa0', ' ').strip() 
                                           for doc in source['document'] if doc)
                    else:
                        source_content.append(str(source['document']).replace('\xa0', ' ').strip())
                    
                    if source_content:
                        source_elements.append("<source_context>")
                        source_elements.append("\n".join(source_content))
                        source_elements.append("</source_context>")
                
                source_elements.append("</source>")
            
            return "\n".join(source_elements)
        except Exception as e:
            print(f"[WARNING] Error formatting source content: {str(e)}")
            return ""

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

            # Process messages to extract sources
            source_contents = []
            
            for msg in messages:
                # Handle assistant messages with sources
                if msg.get('role') == 'assistant' and 'sources' in msg:
                    for source in msg['sources']:
                        source_content = self.format_source_content(source)
                        if source_content:
                            source_contents.append(source_content)

            # Send context to Letta if available
            if source_contents:
                # Format as XML context
                context_text = (
                    "Use the following context as your learned knowledge, "
                    "inside <context></context> XML tags.\n"
                    "<context>\n" +
                    "\n".join(source_contents) +
                    "\n</context>"
                )
                print(f"[DEBUG] Sending context to Letta:\n{context_text}")
                self.client.send_message(
                    agent_id=self.valves.agent_id,
                    message=context_text,
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
    
    # Example with sources
    test_body = {
        "messages": [
            {
                "role": "assistant",
                "sources": [
                    {
                        "source": {
                            "urls": ["https://www.whitehouse.gov"],
                            "type": "web_search_results"
                        },
                        "document": ["Joe Biden is the current president of the United States"],
                        "metadata": [
                            {
                                "title": "White House Official Website",
                                "description": "Current administration information"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    response = pipeline.pipe(
        user_message="Who is the current president of the United States?",
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