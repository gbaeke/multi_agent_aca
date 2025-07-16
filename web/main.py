import logging
import os
import uvicorn
from urllib.parse import urlparse
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent_executor import WebAgentExecutor

# Configuration from environment variables
WEB_A2A_BASE_URL = os.getenv("WEB_A2A_BASE_URL", "http://localhost:9999")


def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:     %(message)s'
    )

    # Suppress Azure SDK logs - only show warnings and errors
    logging.getLogger('azure').setLevel(logging.WARNING)
    logging.getLogger('azure.ai').setLevel(logging.WARNING)
    logging.getLogger('azure.identity').setLevel(logging.WARNING)
    logging.getLogger('azure.core').setLevel(logging.WARNING)

    # Suppress other verbose libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

    # Keep your application logs visible
    logging.getLogger('agent_executor').setLevel(logging.INFO)

    # Parse URL to extract port
    parsed_url = urlparse(WEB_A2A_BASE_URL)
    port = parsed_url.port or 9999  # Default to 9999 if no port specified

    skill = AgentSkill(
        id="web_search",
        name="Web Search",
        description="Search the web for information",
        tags=["web", "search", "information"],
        examples=["What happened in the world last week?"],
    )

    agent_card = AgentCard(
        name="Web Search Agent",
        description="A simple agent that searches the web for information",
        url=WEB_A2A_BASE_URL + ("/" if not WEB_A2A_BASE_URL.endswith("/") else ""),
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        skills=[skill],
        version="1.0.0",
        capabilities=AgentCapabilities(),
    )

    request_handler = DefaultRequestHandler(
        agent_executor=WebAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        http_handler=request_handler,
        agent_card=agent_card,
    )

    logging.info(f"Starting Web A2A server at {WEB_A2A_BASE_URL}")
    uvicorn.run(server.build(), host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
