import chainlit as cl
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function
from semantic_kernel.functions.kernel_arguments import KernelArguments
from fastmcp import Client
from dotenv import load_dotenv
import sys
import os
import logging

load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global MCP client - shared across all sessions
_global_mcp_client = None
_mcp_connection_error = None


async def get_mcp_client():
    """Get the global MCP client, initializing it if needed."""
    global _global_mcp_client, _mcp_connection_error
    
    if _global_mcp_client is None and _mcp_connection_error is None:
        try:
            logger.info(f"Initializing global MCP client for {MCP_SERVER_URL}")
            
            # Create client with timeout configuration for container apps
            _global_mcp_client = Client(
                MCP_SERVER_URL,
                timeout=60.0,  # Increased timeout for container apps
                
            )
            logger.debug("Global MCP client instance created")
            
            # Test the connection immediately
            async with _global_mcp_client:
                await _global_mcp_client.ping()
                logger.info("MCP client connection test successful")
                
        except Exception as e:
            logger.warning(f"Failed to create MCP client for {MCP_SERVER_URL}: {e}")
            _mcp_connection_error = str(e)
            _global_mcp_client = None
    
    return _global_mcp_client


async def cleanup_mcp_client():
    """Cleanup the global MCP client."""
    global _global_mcp_client
    if _global_mcp_client:
        try:
            # FastMCP client cleanup is handled by context manager
            logger.info("Global MCP client cleanup")
        except Exception as e:
            logger.warning(f"Error during MCP client cleanup: {e}")
        finally:
            _global_mcp_client = None


# MCP Tools Plugin Class
class MCPToolsPlugin:
    """Plugin containing RAG and web search tools via global MCP client."""
    
    @kernel_function(
        description="Search for information about Contoso projects using RAG (Retrieval Augmented Generation)",
        name="rag_search"
    )
    async def rag_search(self, query: str) -> str:
        """
        Search for Contoso project information using RAG via MCP.
        
        Args:
            query: The search query about Contoso projects
            
        Returns:
            Information about Contoso projects from RAG
        """
        logger.debug(f"RAG search called with query: {query}")
        
        mcp_client = await get_mcp_client()
        if mcp_client is None:
            return f"RAG tool unavailable: {_mcp_connection_error or 'MCP server not connected'}"
        
        try:
            # Use context manager for MCP operations
            async with mcp_client:
                result = await mcp_client.call_tool("rag_tool", {"question": query})
                return result.data if hasattr(result, 'data') else str(result)
        except Exception as e:
            logger.error(f"Error calling RAG tool via MCP: {e}")
            return f"Error accessing RAG tool: {str(e)}"

    @kernel_function(
        description="Search the web for current information about technologies, frameworks, or general topics",
        name="web_search"
    )
    async def web_search(self, query: str) -> str:
        """
        Search the web for current information via MCP.
        
        Args:
            query: The search query for web search
            
        Returns:
            Web search results and information
        """
        logger.debug(f"Web search called with query: {query}")
        
        mcp_client = await get_mcp_client()
        if mcp_client is None:
            return f"Web search tool unavailable: {_mcp_connection_error or 'MCP server not connected'}"
        
        try:
            # Use context manager for MCP operations
            async with mcp_client:
                result = await mcp_client.call_tool("web_tool", {"query": query})
                return result.data if hasattr(result, 'data') else str(result)
        except Exception as e:
            logger.error(f"Error calling web tool via MCP: {e}")
            return f"Error accessing web search tool: {str(e)}"

# Configuration from environment variables
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:7777/mcp")
AGENT_NAME = os.getenv("AGENT_NAME", "ContosoAssistant")
AGENT_INSTRUCTIONS = os.getenv("AGENT_INSTRUCTIONS", """You are ContosoAssistant, a helpful AI assistant for Contoso projects. 

You have access to two important tools:
1. **rag_search**: Use this to search for information about Contoso projects, documentation, and internal knowledge
2. **web_search**: Use this to search for current information about technologies, frameworks, or general topics

Guidelines:
- For questions about Contoso projects, always use the rag_tool first
- For questions about technologies, frameworks, or current trends, use the web_tool
- If a user asks about both Contoso projects AND external technologies, use both tools appropriately
- Always use the tools when relevant rather than relying only on your training data""")

# Chainlit handlers
@cl.on_chat_start
async def on_chat_start():
    try:
        # Create the Semantic Kernel
        kernel = Kernel()
        
        # Add AI service to kernel
        ai_service = OpenAIChatCompletion(ai_model_id="gpt-4o")
        kernel.add_service(ai_service)
        logger.debug("Kernel and AI service initialized successfully")
        
        # Add MCP tools plugin to kernel (uses global client)
        tools_plugin = MCPToolsPlugin()
        kernel.add_plugin(tools_plugin, plugin_name="mcp_tools")
        logger.debug("MCP tools plugin added to kernel")
        
        # Initialize global MCP client if not already done
        mcp_client = await get_mcp_client()
        
    except Exception as e:
        logger.error(f"Failed to create kernel or AI service: {str(e)}")
        await cl.Message(
            content=f"❌ Failed to initialize core services: {str(e)}\n\n🔄 Please check your OpenAI API configuration and refresh the page."
        ).send()
        return
    
    # Add Chainlit filter to visualize function calls as steps
    sk_filter = cl.SemanticKernelFilter(kernel=kernel)
    
    try:
        # Verify kernel is properly initialized
        if kernel is None:
            raise Exception("Kernel is None - cannot create agent")
        
        agent = ChatCompletionAgent(
            service=ai_service,
            name=AGENT_NAME,
            instructions=AGENT_INSTRUCTIONS,
            kernel=kernel,
        )
        logger.debug(f"Chat session initialized for agent: {AGENT_NAME}")
        
        # Store in session
        cl.user_session.set("agent", agent)
        cl.user_session.set("thread", None)
        
        # Send welcome message with status
        welcome_msg = "🤖 Chat agent is ready!"
        if mcp_client is None:
            welcome_msg += f"\n⚠️ Note: MCP tools are currently unavailable - basic chat functionality only."
            if _mcp_connection_error:
                welcome_msg += f"\n   Error: {_mcp_connection_error}"
        else:
            welcome_msg += f"\n🔗 MCP tools configured for server: {MCP_SERVER_URL}"
            welcome_msg += "\n✅ RAG and web search tools are available!"
        await cl.Message(content=welcome_msg).send()
        
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        # Store None values to indicate failure
        cl.user_session.set("agent", None)
        cl.user_session.set("thread", None)
        
        # Send error message to user
        await cl.Message(
            content=f"❌ Failed to initialize chat agent: {str(e)}\n\n🔄 Please refresh the page and try again."
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    try:
        agent = cl.user_session.get("agent")
        
        # Check if agent was successfully created
        if agent is None:
            await cl.Message(
                content="❌ Sorry, the chat agent is not available. There was an error during initialization. Please refresh the page and try again."
            ).send()
            return
        
        thread = cl.user_session.get("thread")
        
        # Get response from agent
        response = await agent.get_response(messages=message.content, thread=thread)
        
        # Update thread
        cl.user_session.set("thread", response.thread)
        
        # Send response
        await cl.Message(content=str(response)).send()
        
    except Exception as e:
        await cl.Message(content=f"Sorry, I encountered an error: {str(e)}").send()


@cl.on_chat_end
async def on_chat_end():
    logger.debug("Chat session ended")


if __name__ == "__main__":
    # run via: chainlit run this_file.py -w
    
    # Setup graceful shutdown for global MCP client
    import atexit
    import signal
    import asyncio
    
    def cleanup_handler():
        """Cleanup handler for application shutdown."""
        try:
            asyncio.run(cleanup_mcp_client())
        except Exception as e:
            logger.warning(f"Error during application cleanup: {e}")
    
    # Register cleanup handlers
    atexit.register(cleanup_handler)
    signal.signal(signal.SIGTERM, lambda sig, frame: cleanup_handler())
    signal.signal(signal.SIGINT, lambda sig, frame: cleanup_handler())
