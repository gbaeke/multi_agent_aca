import os
import logging
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.ai.agents.models import ListSortOrder
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.utils import new_agent_text_message
from a2a.server.tasks import TaskUpdater
from a2a.utils.errors import ServerError
from a2a.types import (
    InternalError,
    Part,
    TextPart,
)

# Set up logger
logger = logging.getLogger(__name__)

class RAGAgent:
    """RAG agent that can answer questions about project information"""

    def __init__(self):
        logger.info("Initializing RAG Agent...")
        load_dotenv()
        
        endpoint = os.getenv("FOUNDRY_PROJECT")
        agent_id = os.getenv("ASSISTANT_ID")
        client_id = os.getenv("CLIENT_ID")

        if not endpoint:
            logger.error("Environment Error: FOUNDRY_PROJECT is not set")
            raise EnvironmentError("FOUNDRY_PROJECT is not set in the environment or .env file.")
        if not agent_id:
            logger.error("Environment Error: ASSISTANT_ID is not set")
            raise EnvironmentError("ASSISTANT_ID is not set in the environment or .env file.")

        # Use ManagedIdentityCredential if CLIENT_ID is set, otherwise use DefaultAzureCredential
        if client_id:
            logger.info(f"Using ManagedIdentityCredential with client ID: {client_id}")
            credential = ManagedIdentityCredential(client_id=client_id)
        else:
            logger.info("Using DefaultAzureCredential")
            credential = DefaultAzureCredential()

        logger.info(f"Connecting to Azure AI Project: {endpoint}")
        self.project = AIProjectClient(
            credential=credential,
            endpoint=endpoint)

        logger.info(f"Getting agent with ID: {agent_id}")
        self.agent = self.project.agents.get_agent(agent_id)
        logger.info("RAG Agent initialized successfully")

    async def invoke(self, question: str) -> str:
        """Invoke the RAG agent with a question and return the result"""
        logger.info(f"Starting RAG agent execution with question: {question}")
        
        try:
            logger.debug("Creating new thread...")
            thread = self.project.agents.threads.create()
            logger.info(f"Thread created successfully, ID: {thread.id}")

            logger.debug("Creating user message in thread...")
            message = self.project.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content=question
            )
            logger.debug("Message created successfully")

            logger.info("Starting agent run and processing...")
            run = self.project.agents.runs.create_and_process(
                thread_id=thread.id,
                agent_id=self.agent.id)

            if run.status == "failed":
                error_msg = f"Run failed: {run.last_error}"
                logger.error(f"Agent run failed: {error_msg}")
                raise Exception(error_msg)
            else:
                logger.debug("Retrieving messages from thread...")
                messages = list(self.project.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING))

                if messages:
                    last_message = messages[-1]
                    if last_message.text_messages:
                        result = last_message.text_messages[-1].text.value
                        logger.info("RAG agent execution completed successfully")
                        logger.debug(f"Result length: {len(result)} characters")
                        return result
                
                logger.warning("No response received from agent")
                return "No response received from agent"
                
        except Exception as e:
            logger.error(f"Error in RAG agent execution: {e}")
            logger.debug("Stack trace:", exc_info=True)
            raise


class RagAgentExecutor(AgentExecutor):

    def __init__(self):
        logger.info("Initializing RAG Agent Executor...")
        self.agent = RAGAgent()
        logger.info("RAG Agent Executor initialized successfully")

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        logger.info("Starting RAG Agent Executor execution")
        
        if not context.task_id or not context.context_id:
            logger.error("Validation Error: RequestContext missing task_id or context_id")
            raise ValueError("RequestContext must have task_id and context_id")
        if not context.message:
            logger.error("Validation Error: RequestContext missing message")
            raise ValueError("RequestContext must have a message")

        logger.info(f"Task ID: {context.task_id}, Context ID: {context.context_id}")
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)

        if not context.current_task:
            logger.debug("Submitting new task...")
            await updater.submit()
        
        logger.info("Starting work on task...")
        await updater.start_work()

        query = context.get_user_input()
        logger.info(f"User Query: {query}")
        
        try:
            logger.info("Invoking RAG agent with query...")
            # call the RAG agent with the query from the message
            result = await self.agent.invoke(query)
            logger.info("RAG agent invocation completed")
            logger.info(f"Final Result: {result}")
        except Exception as e:
            logger.error(f"Error invoking RAG agent: {e}")
            raise ServerError(error=InternalError()) from e

        logger.debug("Creating response parts...")
        # create a part to send back to the user
        parts = [Part(root=TextPart(text=result))]

        logger.debug("Adding artifact to task...")
        await updater.add_artifact(parts)
        logger.info("Completing task execution...")
        await updater.complete()
        logger.info("RAG Agent Executor execution completed successfully")

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        logger.warning("Cancel operation requested")
        logger.error("Cancel not supported for RAG Agent Executor")
        raise Exception("Cancel not supported")

