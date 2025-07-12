from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.utils import new_agent_text_message
from a2a.server.tasks import TaskUpdater
from a2a.utils.errors import ServerError
from dotenv import load_dotenv
import os
import logging
from a2a.types import (
    InternalError,
    Part,
    TextPart,
)

# Set up logging
logger = logging.getLogger(__name__)

class CalculatorAgent:
    """Calculator agent that can answer questions about news topics"""
    
    def __init__(self):
        logger.info("Initializing Calculator Agent...")

    async def invoke(self, question: str) -> str:
        """Invoke the web agent with a question and return the result"""
        logger.info(f"Starting web agent execution with question: {question}")
        return "I did not do anything"


class CalculatorAgentExecutor(AgentExecutor):

    def __init__(self):
        logger.info("Initializing Calculator Agent Executor...")
        self.agent = CalculatorAgent()
        logger.info("Calculator Agent Executor initialized successfully")

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        logger.info("Starting Calculator Agent Executor execution")

        message_text = context.get_user_input()  # helper method to extract the user input from the context
        logger.info(f"Message text: {message_text}")

        # invoke the agent with the user input
        # TODO: use the agent to calculate the result
        result = await self.agent.invoke(message_text)

        await event_queue.enqueue_event(new_agent_text_message(result))
        
        

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        logger.warning("Cancel operation requested")
        logger.error("Cancel not supported for Calculator Agent Executor")
        raise Exception("Cancel not supported")
