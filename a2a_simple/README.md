# A2A Simple Calculator Agent

A basic Agent-to-Agent (A2A) implementation featuring a calculator agent that runs as a web service.

## Files

- `agent_executor.py` - Contains the core agent logic and executor
- `main.py` - Server setup and configuration

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

```bash
python main.py
```

Agent will be available at `http://localhost:9997/`

## Status

This is a skeleton implementation. The actual calculator logic needs to be implemented in the `CalculatorAgent.invoke()` method. 