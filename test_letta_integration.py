import asyncio
import os
from dotenv import load_dotenv
from async_lettapipeline import Pipeline

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
    
    # Load environment variables
    load_dotenv()
    validate_config()
    
    # Initialize pipeline with environment variables
    pipeline = Pipeline()
    pipeline.valves.base_url = os.getenv('LETTA_BASE_URL')
    pipeline.valves.agent_id = os.getenv('LETTA_AGENT_ID')
    pipeline.valves.lettapass = os.getenv('LETTA_PASSWORD')
    
    # Verify valves were set correctly
    print("\nConfiguration:")
    print(f"- Base URL: {pipeline.valves.base_url}")
    print(f"- Agent ID: {pipeline.valves.agent_id}")
    print(f"- Password: {'*' * len(pipeline.valves.lettapass)}")
    
    # Test message
    test_message = "Hello Letta, this is a test message"
    
    # Create test body
    test_body = {
        "chat_id": "test-chat-123",
        "message_id": "test-message-456"
    }
    
    print("\nTesting message processing...")
    try:
        # Process message through pipeline
        async for event in pipeline.pipe(
            user_message=test_message,
            model_id="test-model",
            messages=[],
            body=test_body
        ):
            print(f"Received event: {event}")
            
        print("\n✅ Message processing test completed successfully")
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_letta_integration())