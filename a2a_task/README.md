# A2A Task Calculator Agent

An advanced Agent-to-Agent (A2A) implementation featuring a streaming calculator agent with OpenAI integration that runs as a web service.

## Files

- `agent_executor.py` - Contains the core agent executor with streaming support
- `agent.py` - Advanced streaming agent with OpenAI integration and tools
- `main.py` - Server setup and configuration
- `test_client.py` - Connect to the A2A server and send messages

## Components

### StreamingAgent
- Advanced agent class with OpenAI integration using `gpt-4o-mini` model
- Supports both streaming (`invoke_stream()`) and non-streaming (`invoke()`) interfaces
- Includes built-in tools like `get_current_date()`
- Features comprehensive event streaming with hooks for monitoring execution

### StreamingAgentHooks
- Custom hooks that capture and stream execution events
- Provides real-time visibility into agent operations (start, tool usage, completion)
- Emits structured events via async queue for monitoring

### CalculatorAgentExecutor
- Extends the A2A `AgentExecutor` base class with streaming capabilities
- Handles request execution flow with real-time status updates
- Processes streaming events and artifacts from the agent
- Implements required `execute()` and `cancel()` methods

### Server Setup
- Creates an `AgentCard` describing the calculator agent's capabilities
- Configures a Starlette-based web server on port 9996
- Registers a "calculator" skill for mathematical expressions
- Supports streaming and push notifications
- Sets up comprehensive logging with Azure SDK suppression

## Usage

**Prerequisites:** Set up your OpenAI API key in environment variables:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or create a `.env` file:
```
OPENAI_API_KEY=your-api-key-here
```

Install packages with `pip install -r requirements.txt`

1. **Start the agent server:**
   ```bash
   python main.py
   ```
   Agent will be available at `http://localhost:9996/`

2. **Test the agent (in a different terminal):**
   ```bash
   python test_client.py
   ```
   
   The client will connect to the server and send a test calculation request.

## Features

- **Streaming Support**: Real-time event streaming during agent execution
- **OpenAI Integration**: Powered by GPT-4o-mini for intelligent responses
- **Tool Integration**: Extensible tool system (includes date functionality)
- **Comprehensive Logging**: Detailed logging with configurable levels
- **Event Monitoring**: Hook system for tracking agent execution stages
- **Error Handling**: Robust error handling and status reporting

## Status

This is a fully functional implementation with OpenAI integration and streaming capabilities. The agent can handle mathematical calculations (not really, just what LLMs do with math) and provides real-time feedback during execution. 