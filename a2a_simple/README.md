# A2A Simple Calculator Agent

A basic Agent-to-Agent (A2A) implementation featuring a calculator agent that runs as a web service.

🤫 It's not actually a calculator, it just pretends to be...

## Files

- `agent_executor.py` - Contains the core agent logic and executor
- `main.py` - Server setup and configuration
- `test_client.py`- Connect to the A2A server and send message
- `requirements.txt` - Python packages 

## Components

### CalculatorAgent
- Simple agent class with an `invoke()` method
- Currently returns placeholder text (calculator not yet implemented - on purpose 😊)
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

### Check Agent Card

Use `ngrok http 9997`(install ngrok if needed) and use the provided https adress with the A2A Protocol Validator at https://a2aprotocol.ai/a2a-protocol-validator.

⚠️ You can also use https://github.com/a2aproject/a2a-inspector on your local machine to connect to the agent, check the Agent Card, exchange messages and view the raw JSON-RPC payloads.

## Status

This is a skeleton implementation. The actual calculator logic needs to be implemented in the `CalculatorAgent.invoke()` method. 