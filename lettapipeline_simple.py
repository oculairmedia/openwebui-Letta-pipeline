"""
title: Letta Chat Pipeline (Simple Version)
author: OpenHands
date: 2024-03-20
version: 1.0
license: MIT
description: A simple pipeline for processing messages through Letta chat API following OpenWebUI patterns
requirements: pydantic, aiohttp, letta
"""

from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
import os
import json
import time
from letta import create_client

class Pipeline:
    class Valves(BaseModel):
        base_url: str = os.getenv('LETTA_BASE_URL', 'http://192.168.50.90:8283')
        agent_id: str = os.getenv('LETTA_AGENT_ID', 'agent-a3899314-bbb3-4798-b3f4-241923314b8e')

    def __init__(self):
        self.name = "Letta Chat"
        self.valves = self.Valves()
        self.client = create_client(base_url=self.valves.base_url)
        print(f"[STARTUP] Starting {self.name}")
        print(f"[STARTUP] Configuration:")
        print(f"[STARTUP] - base_url: {self.valves.base_url}")
        print(f"[STARTUP] - agent_id: {self.valves.agent_id}")
        
        # Create agent if it doesn't exist
        try:
            from letta.schemas.agent import AgentState, AgentType
            from letta.schemas.memory import Memory
            from letta.schemas.llm_config import LLMConfig
            from letta.schemas.embedding_config import EmbeddingConfig
            from letta.schemas.block import Block
            
            agent_state = AgentState(
                id=self.valves.agent_id,
                name="test_agent",
                system="You are a helpful assistant.",
                agent_type=AgentType.chat_only_agent,
                llm_config=LLMConfig(
                    model="gpt-3.5-turbo",
                    model_endpoint_type="openai",
                    context_window=4096,
                    model_endpoint="https://api.openai.com/v1"
                ),
                embedding_config=EmbeddingConfig(
                    embedding_endpoint_type="openai",
                    embedding_model="text-embedding-ada-002",
                    embedding_dim=1536,
                    embedding_endpoint="https://api.openai.com/v1"
                ),
                memory=Memory(
                    blocks=[Block(
                        value="Initial memory block",
                        label="memory",
                        id="block-12345678"
                    )]
                ),
                tools=[],
                sources=[Source(
                    id="source-12345678",
                    name="test_source",
                    embedding_config=EmbeddingConfig(
                        embedding_endpoint_type="openai",
                        embedding_model="text-embedding-ada-002",
                        embedding_dim=1536,
                        embedding_endpoint="https://api.openai.com/v1"
                    )
                )],
                tags=[]
            )
            agent = self.client.create_agent(agent_state)
            print(f"[STARTUP] Created agent with ID: {agent.id}")
        except Exception as e:
            print(f"[ERROR] Failed to create agent: {str(e)}")

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
                        # Handle tool calls
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            tool_responses = []
                            for tool_call in msg.tool_calls:
                                if hasattr(tool_call, 'function'):
                                    args = json.loads(tool_call.function.arguments)
                                    tool_responses.append(
                                        f"Tool {tool_call.function.name} called with args: {args}"
                                    )
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
            try:
                response = self.client.send_message(
                    agent_id=self.valves.agent_id,
                    message=user_message,
                    role="user"
                )
            except Exception as e:
                error_msg = f"Failed to send message: {str(e)}"
                print(f"[ERROR] {error_msg}")
                return error_msg
            
            # Get response after our request time
            response_text = self.get_response_message(self.valves.agent_id, request_time)
            
            if response_text:
                if payload.get("stream", False):
                    # For streaming, convert to list first
                    chars = list(response_text)
                    return chars
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