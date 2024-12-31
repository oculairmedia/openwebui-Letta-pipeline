"""
Test script for Letta pipelines
"""

import asyncio
import json
from typing import Optional, Dict, Any
from lettapipeline_simple import Pipeline

class PipelineTester:
    def __init__(self):
        self.pipeline = Pipeline()
        
    async def test_basic_message(self) -> bool:
        """Test basic message sending and receiving"""
        print("\n=== Testing Basic Message ===")
        try:
            response = self.pipeline.pipe(
                user_message="Hello, this is a test message",
                model_id="default",
                messages=[],
                body={"stream": False}
            )
            print(f"Response: {response}")
            return isinstance(response, str) and len(response) > 0
        except Exception as e:
            print(f"Error in basic message test: {str(e)}")
            return False

    async def test_streaming(self) -> bool:
        """Test streaming responses"""
        print("\n=== Testing Streaming ===")
        try:
            response = self.pipeline.pipe(
                user_message="Generate a long response to test streaming",
                model_id="default",
                messages=[],
                body={"stream": True}
            )
            
            if isinstance(response, str):
                # Error message
                print(response)
                return False
            
            chunks = []
            for chunk in response:
                chunks.append(chunk)
                print(chunk, end='', flush=True)
            
            return len(chunks) > 0
        except Exception as e:
            print(f"Error in streaming test: {str(e)}")
            return False

    async def test_tool_call(self) -> bool:
        """Test tool call handling"""
        print("\n=== Testing Tool Call ===")
        try:
            response = self.pipeline.pipe(
                user_message="Use a tool to help with this task",
                model_id="default",
                messages=[],
                body={
                    "stream": False,
                    "tool_calls": [{
                        "name": "test_tool",
                        "arguments": {"arg1": "value1"}
                    }]
                }
            )
            print(f"Response: {response}")
            if isinstance(response, str):
                return "tool" in response.lower()
            return False
        except Exception as e:
            print(f"Error in tool call test: {str(e)}")
            return False

    async def test_error_handling(self) -> bool:
        """Test error handling"""
        print("\n=== Testing Error Handling ===")
        try:
            # Test with invalid agent_id
            old_agent_id = self.pipeline.valves.agent_id
            self.pipeline.valves.agent_id = "invalid_agent_id"
            
            response = self.pipeline.pipe(
                user_message="This should trigger an error",
                model_id="default",
                messages=[],
                body={"stream": False}
            )
            
            # Restore valid agent_id
            self.pipeline.valves.agent_id = old_agent_id
            
            print(f"Response: {response}")
            if isinstance(response, str):
                return "error" in response.lower() or "failed" in response.lower()
            return False
        except Exception as e:
            print(f"Error in error handling test: {str(e)}")
            return False

    async def test_message_history(self) -> bool:
        """Test message history handling"""
        print("\n=== Testing Message History ===")
        try:
            messages = [
                {"role": "user", "content": "Previous message 1"},
                {"role": "assistant", "content": "Previous response 1"},
                {"role": "user", "content": "Previous message 2"}
            ]
            
            response = self.pipeline.pipe(
                user_message="Reference the previous messages",
                model_id="default",
                messages=messages,
                body={"stream": False}
            )
            print(f"Response: {response}")
            if isinstance(response, str):
                if "error" in response.lower() or "failed" in response.lower():
                    return False
                return len(response) > 0
            return False
        except Exception as e:
            print(f"Error in message history test: {str(e)}")
            return False

    @staticmethod
    async def _async_generator(gen):
        """Convert a regular generator to an async generator"""
        for item in gen:
            yield item

    async def run_all_tests(self):
        """Run all tests and report results"""
        tests = [
            ("Basic Message", self.test_basic_message),
            ("Streaming", self.test_streaming),
            ("Tool Call", self.test_tool_call),
            ("Error Handling", self.test_error_handling),
            ("Message History", self.test_message_history)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                success = await test_func()
                results.append((test_name, success))
            except Exception as e:
                print(f"Error running {test_name}: {str(e)}")
                results.append((test_name, False))
        
        print("\n=== Test Results ===")
        all_passed = True
        for test_name, success in results:
            status = "PASSED" if success else "FAILED"
            print(f"{test_name}: {status}")
            all_passed = all_passed and success
        
        print(f"\nOverall Status: {'PASSED' if all_passed else 'FAILED'}")
        return all_passed

async def main():
    tester = PipelineTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())