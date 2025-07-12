from agents import Agent, AgentHooks, Runner, function_tool
from dotenv import load_dotenv
import os
import asyncio
from typing import AsyncGenerator, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

@function_tool
def get_current_date() -> str:
    """Get the current date."""
    return f"The current date is {datetime.now().strftime('%Y-%m-%d')}"

load_dotenv()

api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables")


class StreamEventType(Enum):
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    RESPONSE = "response"
    ERROR = "error"


@dataclass
class StreamEvent:
    """Represents a streaming event from the agent execution"""
    event_type: StreamEventType
    data: Dict[str, Any]
    timestamp: float


class StreamingAgentHooks(AgentHooks):
    """Hooks that capture events and stream them via an async queue"""
    
    def __init__(self):
        self.event_queue = asyncio.Queue()
        super().__init__()
    
    async def _emit_event(self, event_type: StreamEventType, data: Dict[str, Any]):
        """Emit an event to the stream"""
        import time
        event = StreamEvent(
            event_type=event_type,
            data=data,
            timestamp=time.time()
        )
        await self.event_queue.put(event)
    
    def on_start(self, context, agent):
        # Create a task to emit the event since this is a sync method
        asyncio.create_task(self._emit_event(
            StreamEventType.AGENT_START,
            {"agent_name": agent.name, "message": f"Agent '{agent.name}' is starting..."}
        ))
        return super().on_start(context, agent)
    
    def on_tool_start(self, context, agent, tool):
        asyncio.create_task(self._emit_event(
            StreamEventType.TOOL_START,
            {
                "agent_name": agent.name,
                "tool_name": tool.name,
                "message": f"Tool '{tool.name}' is starting for agent '{agent.name}'"
            }
        ))
        return super().on_tool_start(context, agent, tool)
    
    def on_tool_end(self, context, agent, tool, result):
        asyncio.create_task(self._emit_event(
            StreamEventType.TOOL_END,
            {
                "agent_name": agent.name,
                "tool_name": tool.name,
                "message": f"Tool '{tool.name}' completed for agent '{agent.name}'"
            }
        ))
        return super().on_tool_end(context, agent, tool, result)
    
    def on_end(self, context, agent, result):
        asyncio.create_task(self._emit_event(
            StreamEventType.AGENT_END,
            {
                "agent_name": agent.name,
                "message": f"Agent '{agent.name}' has completed"
            }
        ))
        return super().on_end(context, agent, result)


class StreamingAgent:
    """A wrapper around the OpenAI Agent that provides both streaming and non-streaming interfaces"""
    
    def __init__(
        self,
        name: str = "StreamingAgent",
        instructions: str = "You are a calculator assistant. Respond in a friendly and informative manner.",
        model: str = "gpt-4o-mini",
        tools: list[function_tool] = [get_current_date]
    ):
        """
        Initialize the StreamingAgent.
        
        Args:
            name: Name of the agent
            instructions: Instructions for the agent
            model: Model to use (default: gpt-4o-mini)
            tools: List of tools to give the agent (default: empty list)
        """
        self.streaming_hooks = StreamingAgentHooks()
        self.agent = Agent(
            name=name,
            instructions=instructions,
            model=model,
            tools=tools or [],
            hooks=self.streaming_hooks
        )
    
    async def invoke_stream(self, query: str) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream both hook events and agent response from a single function call.
        
        Args:
            query: The input query for the agent
            
        Yields:
            StreamEvent: Events containing hook data and final response
        """
        # Create a task to run the agent
        agent_task = asyncio.create_task(Runner.run(self.agent, query))
        
        # Stream events as they come in
        events_finished = False
        
        try:
            while not events_finished:
                try:
                    # Wait for either an event or the agent to complete
                    done, pending = await asyncio.wait(
                        [
                            asyncio.create_task(self.streaming_hooks.event_queue.get()),
                            agent_task
                        ],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Check if we got an event
                    if not agent_task.done():
                        # We got an event
                        event_task = next(iter(done))
                        if hasattr(event_task, 'result'):
                            event = event_task.result()
                            yield event
                    else:
                        # Agent completed, get the result
                        result = agent_task.result()
                        
                        # Emit the final response event
                        import time
                        response_event = StreamEvent(
                            event_type=StreamEventType.RESPONSE,
                            data={
                                "message": "Agent response ready",
                                "response": str(result.final_output) if hasattr(result, 'final_output') else str(result)
                            },
                            timestamp=time.time()
                        )
                        yield response_event
                        
                        # Check for any remaining events in the queue
                        while not self.streaming_hooks.event_queue.empty():
                            try:
                                event = self.streaming_hooks.event_queue.get_nowait()
                                yield event
                            except asyncio.QueueEmpty:
                                break
                        
                        events_finished = True
                        
                except asyncio.QueueEmpty:
                    # No events available, continue waiting
                    continue
                    
        except Exception as e:
            # Emit error event
            import time
            error_event = StreamEvent(
                event_type=StreamEventType.ERROR,
                data={"error": str(e)},
                timestamp=time.time()
            )
            yield error_event
            raise
    
    async def invoke(self, query: str) -> str:
        """
        Invoke the agent with a query and return just the final response.
        
        Args:
            query: The input query for the agent
            
        Returns:
            str: The final response from the agent
        """
        result = await Runner.run(self.agent, query)
        return str(result.final_output) if hasattr(result, 'final_output') else str(result)


if __name__ == "__main__":
    async def main():
        question = "What is the current date?"
        print(f"Question: {question}")
        
        # Demo the StreamingAgent class
        agent = StreamingAgent(name="DemoAgent")
        
        print("\n--- Streaming Demo (invoke_stream) ---")
        async for event in agent.invoke_stream(question):
            if event.event_type == StreamEventType.RESPONSE:
                print(f"🎯 Final Response: {event.data['response']}")
            else:
                print(f"📡 Event [{event.event_type.value}]: {event.data.get('message', '')}")
        
        print("\n--- Non-Streaming Demo (invoke) ---")
        response = await agent.invoke(question)
        print(f"Agent Response: {response}")


    asyncio.run(main())
