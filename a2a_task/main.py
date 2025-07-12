import logging
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent_executor import CalculatorAgentExecutor

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

    skill = AgentSkill(
        id="calculator",
        name="Calculator",
        description="Calculate the result of a mathematical expression",
        tags=["calculator", "math", "expression"],
        examples=["What is 2 + 2?"],
    )

    capabilities = AgentCapabilities(streaming=True, pushNotifications=True)


    agent_card = AgentCard(
        name="Calculator Agent",
        description="A simple agent that calculates the result of a mathematical expression",
        url="http://Geerts-MacBook-Air-2.local:9996/",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        skills=[skill],
        version="1.0.0",
        capabilities=capabilities,
    )

    request_handler = DefaultRequestHandler(
        agent_executor=CalculatorAgentExecutor(),
        task_store=InMemoryTaskStore()
    )

    server = A2AStarletteApplication(
        http_handler=request_handler,
        agent_card=agent_card,
    )

    uvicorn.run(server.build(), host="0.0.0.0", port=9996)


if __name__ == "__main__":
    main()
