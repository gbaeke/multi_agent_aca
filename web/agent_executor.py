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
from agents import Runner
from agent_factory import create_agent_from_config

# Set up logging
logger = logging.getLogger(__name__)

class WebAgent:
    """Web agent that can answer questions about news topics"""
    
    def __init__(self):
        logger.info("Initializing Web Agent...")
        # loads the .env file (if you have a global environment variable, you can skip this)
        load_dotenv()
        
        api_key = os.environ.get("OPENAI_API_KEY")
        
        if not api_key:
            logger.error("Environment Error: OPENAI_API_KEY is not set")
            raise ValueError("OPENAI_API_KEY is not set in the environment variables")
        
        logger.info("OPENAI_API_KEY found in environment")
        logger.info("Creating web agent from configuration...")
        # Create agents from configuration
        self.web_agent = create_agent_from_config("web")
        logger.info("Web Agent initialized successfully")

    async def invoke(self, question: str) -> str:
        """Invoke the web agent with a question and return the result"""
        logger.info(f"Starting web agent execution with question: {question}")
        
        try:
            logger.info("Running agent with configuration...")
            logger.debug(f"Max turns set to 3 for tool usage")
            
            # Run the agent with proper configuration to ensure tool execution completes
            result = await Runner.run(
                starting_agent=self.web_agent, 
                input=question,
                max_turns=3,  # Allow multiple turns for tool usage
            )
            
            logger.info(f"Agent execution completed. Result type: {type(result)}")
            
            logger.debug("Processing agent result...")
            if hasattr(result, 'final_output_as'):
                final_result = result.final_output_as(str)
                logger.debug("Used final_output_as(str) method")
            elif hasattr(result, 'final_output'):
                final_result = str(result.final_output)
                logger.debug("Used final_output attribute")
            else:
                final_result = str(result)
                logger.debug("Used direct string conversion")
            
            logger.info(f"Final output length: {len(final_result)} characters")
            logger.debug(f"Final output preview: {final_result[:200]}...")
            logger.info("Web agent execution completed successfully")
            return final_result
            
        except Exception as e:
            logger.error(f"Error in web agent execution: {e}")
            logger.debug("Stack trace:", exc_info=True)
            raise


class WebAgentExecutor(AgentExecutor):

    def __init__(self):
        logger.info("Initializing Web Agent Executor...")
        self.agent = WebAgent()
        logger.info("Web Agent Executor initialized successfully")

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        logger.info("Starting Web Agent Executor execution")
        
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
            logger.info("Invoking web agent with query...")
            # call the OpenAI Agent SDK agent with the query from the message
            result = await self.agent.invoke(query)
            # Truncate the result for logging to avoid huge log entries
            truncated_result = result[:100] + "..." if len(result) > 100 else result
            logger.info("Web agent invocation completed")
            logger.info(f"Final Result (truncated): {truncated_result}")
        except Exception as e:
            logger.error(f"Error invoking web agent: {e}")
            raise ServerError(error=InternalError()) from e

        logger.debug("Creating response parts...")
        # create a part to send back to the user
        parts = [Part(root=TextPart(text=result))]

        logger.debug("Adding artifact to task...")
        await updater.add_artifact(parts)
        logger.info("Completing task execution...")
        await updater.complete()
        logger.info("Web Agent Executor execution completed successfully")

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        logger.warning("Cancel operation requested")
        logger.error("Cancel not supported for Web Agent Executor")
        raise Exception("Cancel not supported")
