from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.utils import (
    new_agent_text_message,
    new_task,
)

from a2a.server.tasks import TaskUpdater
from a2a.utils.errors import ServerError
from dotenv import load_dotenv
import os
import logging
from a2a.types import (
    InternalError,
    Part,
    TextPart,
    TaskState,
)
from agent import StreamingAgent, StreamEventType

import asyncio

# Set up logging
logger = logging.getLogger(__name__)


class CalculatorAgentExecutor(AgentExecutor):

    def __init__(self):
        logger.info("Initializing Calculator Agent Executor...")
        self.agent = StreamingAgent(name="CalculatorAgent")
        logger.info("Calculator Agent Executor initialized successfully")

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        logger.info("Starting Calculator Agent Executor execution")

        message_text = context.get_user_input()  # helper method to extract the user input from the context
        logger.info(f"Message text: {message_text}")

        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.contextId)

        async for event in self.agent.invoke_stream(message_text):
            if event.event_type == StreamEventType.RESPONSE:
                # send the result as an artifact
                await updater.add_artifact(
                    [Part(root=TextPart(text=event.data['response']))],
                    name='calculator_result',
                )

                await updater.complete()
                
            else:
                await updater.update_status(
                TaskState.working,
                new_agent_text_message(
                    event.data.get('message', ''),
                    task.contextId,
                    task.id,
                ),
            )

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        logger.warning("Cancel operation requested")
        logger.error("Cancel not supported for Calculator Agent Executor")
        raise Exception("Cancel not supported")
