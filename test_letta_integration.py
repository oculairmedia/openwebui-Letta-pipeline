import asyncio
import os
import json
import urllib3
from dotenv import load_dotenv
from letta_openwebuifunction import Pipe

# Load environment variables first
load_dotenv()

# Validate configuration before tests
def validate_config():
    """Validate required environment variables"""
    required_vars = [
        'LETTA_BASE_URL',
        'LETTA_AGENT_ID',
        'LETTA_PASSWORD'
    ]
    
    missing_vars = [var for var in required_vars if var not in os.environ]
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

async def test_letta_integration():
    print("Starting Letta integration test...")
    
    # Load environment variables from specific path
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)
    validate_config()
    
    # Print loaded environment variables
    print("\nLoaded Environment Variables:")
    print(f"- LETTA_BASE_URL: {os.getenv('LETTA_BASE_URL')}")
    print(f"- LETTA_AGENT_ID: {os.getenv('LETTA_AGENT_ID')}")
    print(f"- LETTA_PASSWORD: {os.getenv('LETTA_PASSWORD')}")
    
    # Set environment variables explicitly
    os.environ['LETTA_BASE_URL'] = os.getenv('LETTA_BASE_URL')
    os.environ['LETTA_AGENT_ID'] = os.getenv('LETTA_AGENT_ID')
    os.environ['LETTA_PASSWORD'] = os.getenv('LETTA_PASSWORD')
    
    # Initialize pipeline with explicit configuration
    pipe = Pipe()
    pipe.valves.LETTA_BASE_URL = os.getenv('LETTA_BASE_URL')
    pipe.valves.LETTA_AGENT_ID = os.getenv('LETTA_AGENT_ID')
    pipe.valves.LETTA_PASSWORD = os.getenv('LETTA_PASSWORD')
    
    # Verify configuration
    print("\nConfiguration:")
    print(f"- Base URL: {pipe.valves.LETTA_BASE_URL}")
    print(f"- Agent ID: {pipe.valves.LETTA_AGENT_ID}")
    print(f"- Password: {'*' * len(pipe.valves.LETTA_PASSWORD)}")
    print(f"DEBUG: Actual password: {pipe.valves.LETTA_PASSWORD}")
    
    # Test message in Letta format
    test_message = {
        "role": "user",
        "content": "Hello Letta, this is a test message"
    }
    
    # Create test body
    test_body = {
        "chat_id": "test-chat-123",
        "message_id": "test-message-456",
        "messages": [test_message],
        "stream_steps": True,
        "stream_tokens": True
    }
    
    # Create test user
    test_user = {
        "id": "test-user-001",
        "name": "Test User"
    }
    
    print("\nTesting message processing...")
    try:
        # Process message through pipe
        result = pipe.pipe(
            body=test_body,
            __user__=test_user,
            __request__=None
        )
        
        # Process streaming response
        if hasattr(result, '__iter__'):
            for chunk in result:
                print(f"Received chunk: {chunk}")
        else:
            print(f"Received response: {result}")
            
        print("\n✅ Message processing test completed successfully")
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_letta_integration())