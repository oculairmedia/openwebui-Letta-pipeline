"""
title: Letta Chat Pipeline with OpenWebUI Web Search Integration
author: Cline
date: 2024-01-17
version: 2.0
license: MIT
description: A pipeline that integrates OpenWebUI's web search results with Letta
requirements: pydantic, aiohttp, letta
"""

from typing import List, Union, Generator, Iterator, Dict, Any
from pydantic import BaseModel, ConfigDict
import json
import time
from letta import create_client

class SearchResult(BaseModel):
    description: str = ""
    source: str
    title: str
    score: float

class Pipeline:
    class Valves(BaseModel):
        model_config = ConfigDict(protected_namespaces=())
        base_url: str = "http://192.168.50.90:8283"
        agent_id: str = "agent-a3899314-bbb3-4798-b3f4-241923314b8e"

    def __init__(self):
        self.name = "Letta Chat with OpenWebUI Tools"
        self.valves = self.Valves()
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
                
                for msg in reversed(messages):
                    msg_time = msg.created_at.timestamp() if hasattr(msg, 'created_at') else 0
                    
                    if msg_time > after_time and msg.role == "assistant":
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

    def format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results into a clear message for Letta"""
        if not results:
            return "No search results found."
        
        formatted_msg = "Here are the relevant search results:\n\n"
        
        for idx, result in enumerate(results, 1):
            # Convert dict to SearchResult model for validation
            try:
                search_result = SearchResult(**result)
                formatted_msg += f"{idx}. {search_result.title}\n"
                if search_result.description:
                    formatted_msg += f"Description: {search_result.description}\n"
                formatted_msg += f"Source: {search_result.source}\n\n"
            except Exception as e:
                print(f"[WARNING] Error formatting search result: {str(e)}")
                continue
        
        return formatted_msg

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

            # Extract search results if present
            search_results = []
            if 'search_results' in body:
                search_results = body['search_results']
            
            # If we have search results, format and send them to Letta
            if search_results:
                search_info = self.format_search_results(search_results)
                print(f"[DEBUG] Sending search results to Letta:\n{search_info}")
                
                # Send search results as system message
                self.client.send_message(
                    agent_id=self.valves.agent_id,
                    message=search_info,
                    role="system"
                )

            # Record time before sending user message
            request_time = time.time()
            
            # Send user message to agent
            response = self.client.send_message(
                agent_id=self.valves.agent_id,
                message=user_message,
                role="user"
            )
            
            # Get response after our request time
            response_text = self.get_response_message(self.valves.agent_id, request_time)
            
            if response_text:
                if payload.get("stream", False):
                    # For streaming, yield each character
                    for char in response_text:
                        yield char
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
    
    # Example with search results
    test_body = {
        "search_results": [
            {
                "title": "Weather for Eindhoven, Netherlands",
                "description": "Current weather in Eindhoven and forecast for today, tomorrow, and next 14 days",
                "source": "https://www.timeanddate.com/weather/netherlands/eindhoven",
                "score": 0.997
            }
        ]
    }
    
    response = pipeline.pipe(
        user_message="What's the weather in Eindhoven?",
        model_id="default",
        messages=[],
        body=test_body
    )
    print(f"Agent response: {response}")