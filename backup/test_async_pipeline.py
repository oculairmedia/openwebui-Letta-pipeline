"""
Test script for async Letta pipeline using OpenWebUI's API endpoints
"""

import asyncio
import httpx
import json
import uuid
from typing import Dict, Any

async def test_pipeline():
    # Configuration
    BASE_URL = "http://localhost:54601"  # Using the provided port
    HEADERS = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient(verify=False) as client:
        try:
            # Step 1: Create a new chat
            chat_data = {
                "title": "Test Async Pipeline",
                "model_id": "async_lettapipeline"
            }
            print("\n1. Creating new chat...")
            response = await client.post(f"{BASE_URL}/api/chats", json=chat_data)
            response.raise_for_status()
            chat = response.json()
            chat_id = chat["id"]
            print(f"Chat created with ID: {chat_id}")

            # Step 2: Send a test message
            message = {
                "chat_id": chat_id,
                "message_id": str(uuid.uuid4()),
                "content": "Hello, this is a test message",
                "model": "async_lettapipeline",
                "stream": True
            }
            print("\n2. Sending test message...")
            print(f"Message data: {json.dumps(message, indent=2)}")

            # Using streaming endpoint
            async with client.stream(
                "POST",
                f"{BASE_URL}/api/chat/completions",
                json=message,
                headers=HEADERS
            ) as response:
                print("\n3. Receiving stream response:")
                async for chunk in response.aiter_lines():
                    if chunk:
                        try:
                            event = json.loads(chunk)
                            print(f"\nEvent received: {json.dumps(event, indent=2)}")
                        except json.JSONDecodeError:
                            print(f"Raw chunk: {chunk}")

            # Step 3: Get chat history
            print("\n4. Getting chat history...")
            response = await client.get(f"{BASE_URL}/api/chats/{chat_id}/messages")
            response.raise_for_status()
            messages = response.json()
            print(f"Chat history: {json.dumps(messages, indent=2)}")

        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    print("Starting async pipeline test...")
    asyncio.run(test_pipeline())