#!/usr/bin/env python3
"""
FastMCP Server with Web and RAG tools
"""

import asyncio
import logging
import os
import uuid
from typing import Any

import httpx
from fastmcp import FastMCP
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    TextPart,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP("Multi-Agent Tools Server")

PUBLIC_AGENT_CARD_PATH = "/.well-known/agent.json"

# Configuration from environment variables
WEB_A2A_BASE_URL = os.getenv("WEB_A2A_BASE_URL", "http://localhost:9999")
RAG_A2A_BASE_URL = os.getenv("RAG_A2A_BASE_URL", "http://localhost:9998")
MCP_PORT = os.getenv("MCP_PORT", 8080)

# Shared HTTP client with proper connection management
_http_client = None

async def get_http_client():
    """Get or create a shared HTTP client with proper connection management."""
    global _http_client
    if _http_client is None:
        # Configure client with connection limits and timeout
        timeout = httpx.Timeout(200.0, read=200.0, write=30.0, connect=10.0)
        limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        _http_client = httpx.AsyncClient(timeout=timeout, limits=limits)
    return _http_client

async def cleanup_http_client():
    """Cleanup the shared HTTP client."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


async def _send_a2a_message(query: str, base_url: str) -> str:
    """
    Send a message to an A2A agent and return the response.
    
    Args:
        query: The message/query to send to the agent
        base_url: The base URL of the A2A agent (e.g., "http://localhost:9999")
        
    Returns:
        Response from the A2A agent as a string
        
    Raises:
        Exception: If the A2A communication fails
    """
    try:
        # Use the shared HTTP client
        httpx_client = await get_http_client()
        
        try:
            # Initialize A2ACardResolver for the specified agent
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=base_url,
            )

            # Get the agent card
            logger.info(f"Fetching agent card from A2A server at {base_url}")
            agent_card = await resolver.get_agent_card()
            logger.info("Successfully fetched agent card")

        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to A2A agent at {base_url}: {e}")
            raise Exception(f"Cannot connect to A2A agent at {base_url}. Make sure the agent is running.")
        except httpx.TimeoutException as e:
            logger.error(f"Timeout while fetching agent card from {base_url}: {e}")
            raise Exception(f"Timeout connecting to A2A agent at {base_url}")
        except Exception as e:
            logger.error(f"Error fetching agent card: {e}")
            raise Exception(f"Failed to fetch agent card: {str(e)}")

        try:
            # Create A2A client
            client = A2AClient(
                httpx_client=httpx_client, 
                agent_card=agent_card
            )

            # Create message payload
            message_payload = Message(
                role=Role.user,
                messageId=str(uuid.uuid4()),
                parts=[Part(root=TextPart(text=query))],
            )
            
            # Create request
            request = SendMessageRequest(
                id=str(uuid.uuid4()),
                params=MessageSendParams(
                    message=message_payload,
                ),
            )

            logger.info(f"Sending message to A2A agent at {base_url}")
            response = await client.send_message(request)
            
        except httpx.TimeoutException as e:
            logger.error(f"Timeout while sending message to A2A agent: {e}")
            raise Exception("A2A agent response timeout. The operation may be taking longer than expected.")
        except Exception as e:
            logger.error(f"Error sending message to A2A agent: {e}")
            raise Exception(f"Failed to send message to A2A agent: {str(e)}")

        try:
            # Parse response
            response_dict = response.model_dump()
            
            # Check for result structure
            if "result" not in response_dict:
                logger.error("Response missing 'result' field")
                raise Exception("Invalid response format: missing 'result' field")
            
            result = response_dict["result"]
            
            # Check for artifacts
            if "artifacts" not in result or not result["artifacts"]:
                logger.error("Response missing 'artifacts' field or artifacts is empty")
                raise Exception("No artifacts found in A2A agent response")
            
            # Extract artifact
            artifact = result["artifacts"][0]
            
            # Check for parts
            if not artifact.get("parts") or len(artifact["parts"]) == 0:
                logger.error("Artifact missing 'parts' or parts is empty")
                raise Exception("No content parts found in A2A agent response")
            
            # Extract text from first part
            first_part = artifact["parts"][0]
            text_content = first_part.get("text", "")
            
            if not text_content:
                logger.warning("First part has no text content")
                return "No text content received from A2A agent"
            
            logger.info(f"Successfully extracted {len(text_content)} characters from A2A response")
            return text_content
            
        except KeyError as e:
            logger.error(f"Missing expected field in response: {e}")
            raise Exception(f"Invalid response structure: missing field {str(e)}")
        except (TypeError, IndexError) as e:
            logger.error(f"Error parsing response structure: {e}")
            raise Exception(f"Failed to parse A2A agent response: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            raise Exception(f"Failed to process A2A agent response: {str(e)}")
            
    except Exception as e:
        # Re-raise with context if this is already a handled exception
        if "A2A" in str(e) or "agent" in str(e).lower():
            raise
        # Otherwise, wrap with generic A2A error context
        logger.error(f"Unexpected error in A2A communication: {e}")
        raise Exception(f"A2A communication failed: {str(e)}")


@mcp.tool()
async def web_tool(query: str) -> str:
    """
    Perform a web search for the given query.
    
    Args:
        query: The search query to perform
        
    Returns:
        Search results as a string
    """
    logger.info(f"Web tool called with query: {query}")
    logger.info(f"Using web A2A agent at: {WEB_A2A_BASE_URL}")
    
    try:
        return await _send_a2a_message(query, WEB_A2A_BASE_URL)
    except Exception as e:
        logger.error(f"Error performing web search: {e}")
        return f"Error performing web search: {str(e)}"


@mcp.tool()
async def rag_tool(question: str) -> str:
    """
    Answer questions about Contoso projects using RAG.
    
    Args:
        question: The question to answer using RAG
        
    Returns:
        Answer as a string
    """
    logger.info(f"RAG tool called with question: {question}")
    logger.info(f"Using RAG A2A agent at: {RAG_A2A_BASE_URL}")
    
    try:
        return await _send_a2a_message(question, RAG_A2A_BASE_URL)
    except Exception as e:
        logger.error(f"Error performing RAG query: {e}")
        return f"Error performing RAG query: {str(e)}"


def main():
    """Main entry point for the FastMCP server"""
    logger.info("Starting FastMCP server...")
    logger.info(f"Web A2A agent configured at: {WEB_A2A_BASE_URL}")
    logger.info(f"RAG A2A agent configured at: {RAG_A2A_BASE_URL}")
    
    async def cleanup_on_shutdown():
        """Cleanup resources on shutdown"""
        logger.info("Shutting down and cleaning up resources...")
        await cleanup_http_client()
    
    # Set up cleanup for graceful shutdown
    import signal
    import atexit
    
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, cleaning up...")
        asyncio.create_task(cleanup_on_shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(lambda: asyncio.run(cleanup_on_shutdown()))
    
    try:
        # Run the server with HTTP transport (not stdio)
        # Note: Timeout configuration should be done on the client side
        mcp.run(transport="streamable-http", host="localhost", port=MCP_PORT)
    finally:
        # Ensure cleanup happens
        asyncio.run(cleanup_on_shutdown())


if __name__ == "__main__":
    main()
