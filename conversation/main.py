import chainlit as cl
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin
from semantic_kernel import Kernel
from dotenv import load_dotenv
import sys
import os

# Redirect stderr to suppress runtime errors
class NullWriter:
    def write(self, txt): pass
    def flush(self): pass

sys.stderr = NullWriter()

load_dotenv()

# Configuration from environment variables
MCP_PLUGIN_URL = os.getenv("MCP_PLUGIN_URL", "http://localhost:8080/mcp")
AGENT_NAME = os.getenv("AGENT_NAME", "ContosoAssistant")
AGENT_INSTRUCTIONS = os.getenv("AGENT_INSTRUCTIONS", """Only answer from the knowledge of your tools. Do not answer beyond that knowledge. Stick to Contoso. Help the user with Contoso projects. When asked about a project, use your rag tool.
                     When the user asks for more information about tech in the project, use the web tool to research the tech.
                     Never use the web tool to find information about the project. Only use rag for that.
                     You need to use the web tool multiple times if there is more than one tech in the project.""")

# Chainlit handlers
@cl.on_chat_start
async def on_chat_start():
    # Create the Semantic Kernel
    kernel = Kernel()
    
    # Add AI service to kernel
    ai_service = OpenAIChatCompletion(ai_model_id="gpt-4o")
    kernel.add_service(ai_service)
    
    # Create the MCP plugin
    mcp_plugin = MCPStreamableHttpPlugin(
        name="web_and_rag", 
        url=MCP_PLUGIN_URL, 
        load_tools=True
    )
    
    # Initialize the plugin connection
    await mcp_plugin.__aenter__()
    
    # Add MCP plugin to kernel
    kernel.add_plugin(mcp_plugin, plugin_name="web_and_rag")
    
    # Add Chainlit filter to visualize function calls as steps
    sk_filter = cl.SemanticKernelFilter(kernel=kernel)
    
    agent = ChatCompletionAgent(
        service=ai_service,
        name=AGENT_NAME,
        instructions=AGENT_INSTRUCTIONS,
        kernel=kernel,
    )
    
    # Store in session
    cl.user_session.set("agent", agent)
    cl.user_session.set("thread", None)
    cl.user_session.set("mcp_plugin", mcp_plugin)


@cl.on_message
async def on_message(message: cl.Message):
    try:
        agent = cl.user_session.get("agent")
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
    try:
        # Clean up the MCP plugin connection
        mcp_plugin = cl.user_session.get("mcp_plugin")
        if mcp_plugin:
            await mcp_plugin.__aexit__(None, None, None)
    except:
        # Ignore any cleanup errors
        pass


if __name__ == "__main__":
    # run via: chainlit run this_file.py -w
    pass
