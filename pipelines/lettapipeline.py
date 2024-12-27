"""
title: Setta Chat Pipeline (Development Version)
author: OpenHands
date: 2024-03-17
version: 1.0
license: MIT
description: A streaming-enabled pipeline for OpenWebUI using Letta chat API
requirements: pydantic, aiohttp, letta
"""

from typing import List, Union, Generator, Iterator, AsyncGenerator
from pydantic import BaseModel, ConfigDict
import json
import time
from letta import create_client

class Pipeline:
    class Valves(BaseModel):
        model_config = ConfigDict(protected_namespaces=())
        base_url: str = "http://192.168.50.90:8283"
        agent_id: str = "agent-ca9c4ba8-554f-4e48-bef4-784822a909c4"

    def __init__(self):
        self.name = "Setta Chat"
        self.valves = self.Valves()
        self.client = create_client(base_url=self.valves.base_url)
        print(f"[STARTUP] Starting {self.name}")
        print(f"[STARTUP] Configuration:")
        print(f"[STARTUP] - base_url: {self.valves.base_url}")
        print(f"[STARTUP] - agent_id: {self.valves.agent_id}")

    async def get_response_message(self, agent_id: str, after_time) -> Union[str, None]:
        """Get response message after specified time"""
        try:
            max_attempts = 5
            attempt = 0
            
            while attempt < max_attempts:
                messages = await self.client.get_messages(agent_id=agent_id, limit=10)
                
                for msg in reversed(messages):
                    msg_time = msg.created_at.timestamp() if hasattr(msg, 'created_at') else 0
                    
                    if msg_time > after_time and msg.role == "assistant":
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tool_call in msg.tool_calls:
                                if (hasattr(tool_call, 'function') and 
                                    tool_call.function.name == 'send_message'):
                                    args = json.loads(tool_call.function.arguments)
                                    if 'message' in args:
                                        return args['message']
                        elif hasattr(msg, 'text'):
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

    async def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> Union[str, AsyncGenerator]:
        """Process messages through the pipeline"""
        if body.get("title", False):
            return self.name

        try:
            # Get the last user message
            user_message = messages[-1]["content"] if messages else ""
            
            # Record time before sending message
            request_time = time.time()
            
            # Send message to agent
            response = await self.client.send_message(
                agent_id=self.valves.agent_id,
                message=user_message,
                role="user"
            )
            
            # Get response after our request time
            response_text = await self.get_response_message(self.valves.agent_id, request_time)
            
            if response_text:
                if body.get("stream", False):
                    # For streaming, yield each character
                    for char in response_text:
                        yield {
                            "id": f"{model_id}-{time.time()}-{hash(char)}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model_id,
                            "choices": [{
                                "index": 0,
                                "delta": {
                                    "content": char
                                },
                                "logprobs": None,
                                "finish_reason": None
                            }]
                        }
                    # Send final chunk with finish_reason
                    yield {
                        "id": f"{model_id}-{time.time()}-final",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model_id,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "logprobs": None,
                            "finish_reason": "stop"
                        }]
                    }
                else:
                    # For non-streaming, return response in OpenAI format
                    return {
                        "id": f"{model_id}-{time.time()}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": model_id,
                        "choices": [{
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response_text
                            },
                            "logprobs": None,
                            "finish_reason": "stop"
                        }]
                    }
            else:
                return {
                    "id": f"{model_id}-{time.time()}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model_id,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "I apologize, but I couldn't process your message at this time."
                        },
                        "logprobs": None,
                        "finish_reason": "stop"
                    }]
                }
                
        except Exception as e:
            error_msg = f"Error communicating with agent: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return {
                "id": f"{model_id}-{time.time()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_id,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": error_msg
                    },
                    "logprobs": None,
                    "finish_reason": "stop"
                }]
            }

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
    import asyncio
    
    async def main():
        pipeline = Pipeline()
        
        # Test non-streaming message
        response = await pipeline.pipe(
            user_message="Hello! How are you?",
            model_id="lettapipeline",
            messages=[{"role": "user", "content": "Hello! How are you?"}],
            body={"stream": False}
        )
        print(f"Non-streaming response: {response}")
        
        # Test streaming message
        async for chunk in pipeline.pipe(
            user_message="Tell me a joke",
            model_id="lettapipeline",
            messages=[{"role": "user", "content": "Tell me a joke"}],
            body={"stream": True}
        ):
            print(f"Streaming chunk: {chunk}")
    
    asyncio.run(main())
