# A2A Simple Calculator Agent

A basic Agent-to-Agent (A2A) implementation featuring a calculator agent that runs as a web service.

## Files

- `agent_executor.py` - Contains the core agent logic and executor
- `main.py` - Server setup and configuration
- `test_client.py`- Connect to the A2A server and send message
- `requirements.txt` - Python packages 

## Components

### CalculatorAgent
- Simple agent class with an `invoke()` method
- Currently returns placeholder text (not yet implemented)
- Intended to handle mathematical calculations

### CalculatorAgentExecutor
- Extends the A2A `AgentExecutor` base class
- Handles request execution flow:
  - Extracts user input from context
  - Invokes the calculator agent
  - Returns results via event queue
- Implements required `execute()` and `cancel()` methods

### Server Setup
- Creates an `AgentCard` describing the calculator agent's capabilities
- Configures a Starlette-based web server on port 9997
- Registers a "calculator" skill for mathematical expressions
- Sets up request handling with in-memory task storage

## Usage

Install packages with `pip install -r requirements.txt`

1. **Start the agent server:**
   ```bash
   python main.py
   ```
   Agent will be available at `http://localhost:9997/`

2. **Test the agent (in a different terminal):**
   ```bash
   # From the project root directory
   python test_client.py
   ```
   
   **Note:** Update the `BASE_URL` in `test_client.py` from `http://localhost:9998` to `http://localhost:9997` to match the agent's port.

## Status

This is a skeleton implementation. The actual calculator logic needs to be implemented in the `CalculatorAgent.invoke()` method. 