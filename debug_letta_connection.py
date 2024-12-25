"""
Debug script to test Letta connection and message handling
"""

from letta import create_client
from letta.schemas.agent import AgentState, AgentType
from letta.schemas.memory import Memory
from letta.schemas.llm_config import LLMConfig
from letta.schemas.embedding_config import EmbeddingConfig
import json
import time
import uuid

def test_letta_connection(base_url="http://192.168.50.90:8283"):
    print(f"\n=== Testing Letta Connection ===")
    try:
        # Create client
        print(f"Creating client with base_url: {base_url}")
        client = create_client(base_url=base_url)
        
        # Create agent
        print("\nCreating test agent...")
        agent_state = AgentState(
            id=str(uuid.uuid4()),
            name="test_agent",
            system="You are a helpful assistant.",
            agent_type=AgentType.chat_only_agent,
            llm_config=LLMConfig(
                model="gpt-3.5-turbo",
                temperature=0.7,
                max_tokens=1000
            ),
            embedding_config=EmbeddingConfig(
                model="text-embedding-ada-002"
            ),
            memory=Memory(
                type="default",
                max_messages=100
            ),
            tools=[],
            sources=[],
            tags=[]
        )
        agent = client.create_agent(agent_state)
        print(f"Agent created with ID: {agent.id}")
        
        # Test connection by sending a simple message
        print("\nTesting connection by sending a test message...")
        response = client.send_message(
            agent_id=agent.id,
            message="Test connection",
            role="system"
        )
        print(f"Response received: {response}")
        
        return client, agent
    except Exception as e:
        print(f"Error connecting to Letta: {str(e)}")
        return None, None

def test_message_flow(client, agent):
    print(f"\n=== Testing Message Flow ===")
    try:
        # 1. Send system message with test context
        print("\n1. Sending system message with test context...")
        test_context = (
            "Use the following context as your learned knowledge, "
            "inside <context></context> XML tags. "
            "<context> "
            "<source>"
            "<source_id>https://test.com</source_id>"
            "<source_context>This is a test context message.</source_context>"
            "</source> "
            "</context>"
        )
        system_response = client.send_message(
            agent_id=agent.id,
            message=test_context,
            role="system"
        )
        print("System message sent successfully")
        print(f"Response: {system_response}")
        
        # 2. Send user message
        print("\n2. Sending user message...")
        request_time = time.time()
        user_response = client.send_message(
            agent_id=agent.id,
            message="This is a test message. Please acknowledge receipt.",
            role="user"
        )
        print("User message sent successfully")
        print(f"Response: {user_response}")
        
        # 3. Get messages to check flow
        print("\n3. Getting recent messages...")
        max_attempts = 5
        attempt = 0
        while attempt < max_attempts:
            messages = client.get_messages(agent_id=agent.id, limit=10)
            print(f"\nAttempt {attempt + 1}/{max_attempts}")
            
            for msg in messages:
                print(f"\nMessage:")
                print(f"Role: {msg.role}")
                if hasattr(msg, 'text'):
                    print(f"Text: {msg.text}")
                if hasattr(msg, 'tool_calls'):
                    print("Tool Calls:")
                    for tool_call in msg.tool_calls:
                        if hasattr(tool_call, 'function'):
                            print(f"- Function: {tool_call.function.name}")
                            print(f"  Arguments: {tool_call.function.arguments}")
            
            attempt += 1
            if attempt < max_attempts:
                print("Waiting for more messages...")
                time.sleep(2)
        
        return True
    except Exception as e:
        print(f"Error testing message flow: {str(e)}")
        return False

def main():
    # Test connection
    client, agent = test_letta_connection()
    if not client or not agent:
        print("Failed to connect to Letta")
        return
    
    # Test message flow
    success = test_message_flow(client, agent)
    if success:
        print("\n=== Test completed successfully ===")
    else:
        print("\n=== Test failed ===")

if __name__ == "__main__":
    main()