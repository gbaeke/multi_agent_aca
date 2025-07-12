# Project overview

Multi-agent with three agents:

- a main conversation agent: users talk to this main agent via a web UI protected with Entra ID
- a rag agent: an Azure AI Foundry Agent in Semantic Kernel (over A2A); uses files knowledge source
- a web agent: an OpenAI Agents SDK Agent (over A2A); uses OpenAI web search

The main conversation agent uses tools that then use the appropriate agent:
- rag tool: calls the rag agent using A2A
- web tool: calls the web agent using A2A

What are some other ways to do this:
- everything in process: e.g. define the three agents in code running in the same process; agents as tools as supported in several frameworks
- using Agent PaaS: e.g. define the three agents in Azure AI Foundry and use **connected agents** (this is similar to other solutions like AWS Bedrock Agents, Copilot Studio); this is also agents as tool
- agents as microservices: every agent runs in its own process over the network; use a protocol like A2A to standardize interactions; starting agent likely uses these agents as tools as well; you can use any framework here

Interesting resources:
- Protocol validator: https://a2aprotocol.ai/a2a-protocol-validator
