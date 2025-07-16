# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os
from pathlib import Path

from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin
from semantic_kernel.core_plugins.time_plugin import TimePlugin

from dotenv import load_dotenv

load_dotenv()


async def main():
    # 1. Create the agent   
    async with (
        MCPStreamableHttpPlugin(
            name="web_and_rag", 
            url="http://localhost:8080/mcp", 
            load_tools=True) as mcp_plugin,
        ):
        agent = ChatCompletionAgent(
            service=OpenAIChatCompletion(ai_model_id="gpt-4o"),
            name="ContosoAssistant",
            instructions="Help the user with Contoso projects by using the web_and_rag plugin.",
            plugins=[mcp_plugin],
        )

        # 2. Create a thread to hold the conversation
        # If no thread is provided, a new thread will be
        # created and returned with the initial response
        thread: ChatHistoryAgentThread | None = None
        while True:
            user_input = input("User: ")
            if user_input.lower() == "exit":
                break
            # 3. Invoke the agent for a response
            response = await agent.get_response(messages=user_input, thread=thread)
            print(f"# {response.name}: {response} ")
            thread = response.thread

        # 4. Cleanup: Clear the thread
        await thread.delete() if thread else None




if __name__ == "__main__":
    asyncio.run(main())