"""
title: Advanced Letta Chat Pipeline
author: OpenHands
date: 2024-03-20
version: 3.0
license: MIT
description: Advanced pipeline for processing messages through Letta chat API with advanced features
requirements: pydantic, aiohttp, letta, tenacity, asyncio, aiofiles, prometheus_client
"""

from typing import List, Union, Generator, Iterator, Dict, Any, Optional, Callable
from pydantic import BaseModel, ConfigDict, Field, validator
import json
import time
import os
import asyncio
import aiofiles
from datetime import datetime
from enum import Enum
from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from prometheus_client import Counter, Histogram, start_http_server
from contextlib import asynccontextmanager
from letta import create_client

# Metrics
TOOL_CALLS = Counter('letta_tool_calls_total', 'Number of tool calls', ['tool_name', 'status'])
RESPONSE_TIME = Histogram('letta_response_time_seconds', 'Response time in seconds')
ERROR_COUNT = Counter('letta_errors_total', 'Number of errors', ['type'])

class ToolStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class MessagePriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

class ToolType(str, Enum):
    SYSTEM = "system"
    USER = "user"
    CUSTOM = "custom"
    COMPOSIO = "composio"

class ToolResponse(BaseModel):
    """Enhanced model for tool execution responses"""
    tool_name: str
    tool_id: Optional[str] = None
    tool_type: ToolType = ToolType.CUSTOM
    status: ToolStatus
    result: str
    stdout: Optional[List[str]] = None
    stderr: Optional[List[str]] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    def format_response(self, include_metadata: bool = False) -> str:
        """Format tool response for display with optional metadata"""
        response = [f"Tool '{self.tool_name}' ({self.tool_type.value}) {self.status.value}"]
        if self.tool_id:
            response[0] += f" (ID: {self.tool_id})"
        response.append(f"Result: {self.result}")
        if self.stdout:
            response.append("Output:")
            response.extend(self.stdout)
        if self.stderr:
            response.append("Errors:")
            response.extend(self.stderr)
        if include_metadata and self.metadata:
            response.append("Metadata:")
            for key, value in self.metadata.items():
                response.append(f"  {key}: {value}")
        response.append(f"Execution time: {self.execution_time:.3f}s")
        return "\n".join(response)

class PipelineConfig(BaseModel):
    """Configuration model for the pipeline"""
    base_url: str = Field(default_factory=lambda: os.getenv('LETTA_BASE_URL', 'http://192.168.50.90:8283'))
    agent_id: str = Field(default_factory=lambda: os.getenv('LETTA_AGENT_ID', 'agent-a3899314-bbb3-4798-b3f4-241923314b8e'))
    assistant_message_tool_name: Optional[str] = None
    assistant_message_tool_kwarg: Optional[str] = None
    include_base_tools: bool = True
    max_retries: int = 3
    retry_delay: int = 2
    max_attempts: int = 10
    stream_chunk_size: int = 1
    metrics_port: int = 9090
    enable_metrics: bool = True
    log_directory: str = "logs"
    tool_timeout: float = 30.0
    max_concurrent_tools: int = 5
    enable_caching: bool = True
    cache_ttl: int = 3600

    @validator('log_directory')
    def create_log_directory(cls, v):
        os.makedirs(v, exist_ok=True)
        return v

class ToolCache:
    """Cache for tool responses"""
    def __init__(self, ttl: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl

    def get(self, key: str) -> Optional[ToolResponse]:
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['response']
            del self.cache[key]
        return None

    def set(self, key: str, response: ToolResponse):
        self.cache[key] = {
            'timestamp': time.time(),
            'response': response
        }

    def clear(self):
        self.cache.clear()

def async_retry(retries: int = 3):
    """Decorator for async retry logic"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
            return None
        return wrapper
    return decorator

class Pipeline:
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.name = "Advanced Letta Chat"
        self.config = config or PipelineConfig()
        self.client = self._create_client()
        self.tool_cache = ToolCache(ttl=self.config.cache_ttl) if self.config.enable_caching else None
        self.tool_semaphore = asyncio.Semaphore(self.config.max_concurrent_tools)
        self._initialize_pipeline()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _create_client(self):
        """Create Letta client with retry logic"""
        return create_client(base_url=self.config.base_url)

    def _initialize_pipeline(self):
        """Initialize pipeline with metrics and logging"""
        self._setup_logging()
        if self.config.enable_metrics:
            self._setup_metrics()
        self._log_startup_info()
        self.configure_tools()

    def _setup_metrics(self):
        """Initialize Prometheus metrics server"""
        try:
            start_http_server(self.config.metrics_port)
            print(f"[METRICS] Started Prometheus metrics server on port {self.config.metrics_port}")
        except Exception as e:
            print(f"[ERROR] Failed to start metrics server: {str(e)}")

    async def _log_message(self, level: str, message: str):
        """Async logging to file"""
        timestamp = datetime.now().isoformat()
        log_file = os.path.join(self.config.log_directory, f"pipeline_{datetime.now().strftime('%Y%m%d')}.log")
        async with aiofiles.open(log_file, mode='a') as f:
            await f.write(f"[{timestamp}] {level}: {message}\n")

    def _setup_logging(self):
        """Setup logging directory"""
        os.makedirs(self.config.log_directory, exist_ok=True)

    def _log_startup_info(self):
        """Log startup information"""
        info = [
            f"Starting {self.name}",
            f"Configuration:",
            f"- base_url: {self.config.base_url}",
            f"- agent_id: {self.config.agent_id}",
            f"- message_tool: {self.config.assistant_message_tool_name}",
            f"- metrics_enabled: {self.config.enable_metrics}",
            f"- caching_enabled: {self.config.enable_caching}"
        ]
        for line in info:
            print(f"[STARTUP] {line}")

    @asynccontextmanager
    async def tool_execution_context(self, tool_name: str):
        """Context manager for tool execution with timeout and metrics"""
        start_time = time.time()
        try:
            async with self.tool_semaphore:
                yield
            execution_time = time.time() - start_time
            TOOL_CALLS.labels(tool_name=tool_name, status="success").inc()
            RESPONSE_TIME.observe(execution_time)
        except asyncio.TimeoutError:
            TOOL_CALLS.labels(tool_name=tool_name, status="timeout").inc()
            raise
        except Exception as e:
            TOOL_CALLS.labels(tool_name=tool_name, status="error").inc()
            ERROR_COUNT.labels(type=type(e).__name__).inc()
            raise

    async def process_tool_call(self, tool_call) -> Optional[ToolResponse]:
        """Process a tool call with timeout and caching"""
        if not hasattr(tool_call, 'function'):
            return None

        tool_name = tool_call.function.name
        tool_id = getattr(tool_call, 'id', None)
        
        # Check cache first
        if self.config.enable_caching:
            cache_key = f"{tool_name}:{tool_call.function.arguments}"
            cached_response = self.tool_cache.get(cache_key)
            if cached_response:
                await self._log_message("INFO", f"Cache hit for tool {tool_name}")
                return cached_response

        try:
            async with self.tool_execution_context(tool_name):
                start_time = time.time()
                
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = tool_call.function.arguments

                # Determine tool type
                tool_type = ToolType.SYSTEM if tool_name.startswith("system.") else (
                    ToolType.COMPOSIO if tool_name.startswith("composio.") else ToolType.CUSTOM
                )

                response = ToolResponse(
                    tool_name=tool_name,
                    tool_id=tool_id,
                    tool_type=tool_type,
                    status=ToolStatus.SUCCESS,
                    result=str(args),
                    execution_time=time.time() - start_time,
                    metadata={
                        "agent_id": self.config.agent_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )

                # Cache successful response
                if self.config.enable_caching:
                    self.tool_cache.set(cache_key, response)

                return response

        except asyncio.TimeoutError:
            await self._log_message("ERROR", f"Tool {tool_name} execution timed out")
            return ToolResponse(
                tool_name=tool_name,
                tool_id=tool_id,
                status=ToolStatus.TIMEOUT,
                result="Tool execution timed out"
            )
        except Exception as e:
            await self._log_message("ERROR", f"Error processing tool {tool_name}: {str(e)}")
            return ToolResponse(
                tool_name=tool_name,
                status=ToolStatus.ERROR,
                result=f"Error processing tool call: {str(e)}"
            )

    @async_retry(retries=3)
    async def get_response_message(self, agent_id: str, after_time) -> Union[str, None]:
        """Get response message with enhanced error handling and metrics"""
        try:
            attempt = 0
            while attempt < self.config.max_attempts:
                messages = self.client.get_messages(agent_id=agent_id, limit=10)
                
                for msg in reversed(messages):
                    msg_time = msg.created_at.timestamp() if hasattr(msg, 'created_at') else 0
                    
                    if msg_time > after_time and msg.role == "assistant":
                        # Handle tool calls
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            tool_responses = []
                            for tool_call in msg.tool_calls:
                                tool_response = await self.process_tool_call(tool_call)
                                if tool_response:
                                    tool_responses.append(
                                        tool_response.format_response(include_metadata=True)
                                    )
                            
                            if tool_responses:
                                return "\n\n".join(tool_responses)
                        
                        # Handle tool returns
                        if hasattr(msg, 'tool_return'):
                            return ToolResponse(
                                tool_name="tool_return",
                                tool_id=getattr(msg, 'tool_call_id', None),
                                status=ToolStatus(getattr(msg, 'status', 'success')),
                                result=msg.tool_return,
                                stdout=getattr(msg, 'stdout', None),
                                stderr=getattr(msg, 'stderr', None),
                                execution_time=time.time() - after_time
                            ).format_response(include_metadata=True)
                        
                        # Handle regular messages
                        if hasattr(msg, 'text'):
                            return msg.text
                        elif hasattr(msg, 'message'):
                            return msg.message
                
                attempt += 1
                if attempt < self.config.max_attempts:
                    await asyncio.sleep(self.config.retry_delay)
            
            await self._log_message("WARNING", f"No response received after {attempt} attempts")
            return None
        except Exception as e:
            await self._log_message("ERROR", f"Error getting response message: {str(e)}")
            ERROR_COUNT.labels(type=type(e).__name__).inc()
            return None

    async def pipe(
        self, 
        user_message: str, 
        model_id: str, 
        messages: List[dict], 
        body: dict,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Union[str, Generator, Iterator]:
        """Process messages with priority handling and metrics"""
        if body.get("title", False):
            return self.name

        try:
            with RESPONSE_TIME.time():
                # Clean up payload
                payload = {**body}
                for key in ['user', 'chat_id', 'title']:
                    payload.pop(key, None)

                # Record time before sending message
                request_time = time.time()
                
                # Send message with tool configuration
                response = await self.client.send_message(
                    agent_id=self.config.agent_id,
                    message=user_message,
                    role="user",
                    assistant_message_tool_name=self.config.assistant_message_tool_name,
                    assistant_message_tool_kwarg=self.config.assistant_message_tool_kwarg,
                    priority=priority.value
                )
                
                # Get response after our request time
                response_text = await self.get_response_message(self.config.agent_id, request_time)
                
                if response_text:
                    if payload.get("stream", False):
                        # For streaming, yield in chunks
                        for i in range(0, len(response_text), self.config.stream_chunk_size):
                            yield response_text[i:i + self.config.stream_chunk_size]
                    else:
                        return response_text
                else:
                    return "I apologize, but I couldn't process your message at this time."

        except Exception as e:
            error_msg = self._format_error(e)
            await self._log_message("ERROR", error_msg)
            ERROR_COUNT.labels(type=type(e).__name__).inc()
            return error_msg

    def _format_error(self, error: Exception) -> str:
        """Format error messages with stack trace option"""
        import traceback
        error_type = error.__class__.__name__
        error_msg = str(error)
        if isinstance(error, RetryError):
            return f"Error after retries ({error_type}): {error_msg}"
        return f"Error ({error_type}): {error_msg}\n{traceback.format_exc()}"

    @async_retry(retries=3)
    async def add_tool(self, tool_id: str, tool_type: ToolType = ToolType.CUSTOM) -> bool:
        """Add a tool with type classification"""
        try:
            await self.client.patch(f"/v1/agents/{self.config.agent_id}/add-tool/{tool_id}")
            await self._log_message("INFO", f"Added tool {tool_id} of type {tool_type.value}")
            return True
        except Exception as e:
            await self._log_message("ERROR", f"Failed to add tool {tool_id}: {str(e)}")
            return False

    @async_retry(retries=3)
    async def remove_tool(self, tool_id: str) -> bool:
        """Remove a tool with logging"""
        try:
            await self.client.patch(f"/v1/agents/{self.config.agent_id}/remove-tool/{tool_id}")
            await self._log_message("INFO", f"Removed tool {tool_id}")
            return True
        except Exception as e:
            await self._log_message("ERROR", f"Failed to remove tool {tool_id}: {str(e)}")
            return False

    async def list_tools(self, tool_type: Optional[ToolType] = None) -> List[str]:
        """List tools with optional type filtering"""
        try:
            response = await self.client.get(f"/v1/agents/{self.config.agent_id}/tools")
            tools = getattr(response, 'tools', [])
            if tool_type:
                return [tool.name for tool in tools if getattr(tool, 'tool_type', ToolType.CUSTOM) == tool_type]
            return [tool.name for tool in tools]
        except Exception as e:
            await self._log_message("ERROR", f"Failed to list tools: {str(e)}")
            return []

    async def configure_tools(self):
        """Configure tools with type support"""
        try:
            if self.config.include_base_tools:
                await self.client.post("/v1/tools/add-base-tools")
            
            tools = await self.list_tools()
            await self._log_message("INFO", f"Configured tools: {tools}")
        except Exception as e:
            await self._log_message("ERROR", f"Error configuring tools: {str(e)}")

    async def on_startup(self):
        """Enhanced startup with health check"""
        print(f"on_startup:{__name__}")
        await self._initialize_async()
        await self._health_check()

    async def on_shutdown(self):
        """Enhanced shutdown with cleanup"""
        print(f"on_shutdown:{__name__}")
        await self._cleanup_async()
        if self.tool_cache:
            self.tool_cache.clear()

    async def on_valves_updated(self):
        """Handle valve updates with reconnection"""
        self.client = self._create_client()
        await self._log_message("INFO", f"Updated client with new base_url: {self.config.base_url}")
        await self.configure_tools()

    async def _initialize_async(self):
        """Async initialization with health check"""
        pass

    async def _cleanup_async(self):
        """Async cleanup with logging"""
        pass

    async def _health_check(self):
        """Perform health check of pipeline components"""
        try:
            # Check client connection
            await self.client.get("/health")
            # Check tool availability
            tools = await self.list_tools()
            await self._log_message("INFO", f"Health check passed. Available tools: {len(tools)}")
            return True
        except Exception as e:
            await self._log_message("ERROR", f"Health check failed: {str(e)}")
            return False

# Example usage
if __name__ == "__main__":
    async def main():
        # Create pipeline with custom config
        config = PipelineConfig(
            enable_metrics=True,
            enable_caching=True,
            max_concurrent_tools=10
        )
        pipeline = Pipeline(config)
        
        # Example with tool calls and priority
        test_body = {
            "stream": True,
            "tool_calls": [{
                "name": "test_tool",
                "arguments": {"arg1": "value1"}
            }]
        }
        
        response = await pipeline.pipe(
            user_message="Test message with tool calls",
            model_id="default",
            messages=[],
            body=test_body,
            priority=MessagePriority.HIGH
        )
        
        if isinstance(response, (Generator, Iterator)):
            print("Streaming response:")
            for chunk in response:
                print(chunk, end='')
        else:
            print(f"Direct response: {response}")

    # Run the example
    asyncio.run(main())