#!/usr/bin/env python3
"""
Simple MCP Connection Test Script
Use this to test MCP server connectivity in container apps environment
"""

import asyncio
import os
import sys
import logging
from fastmcp import Client

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_mcp_connection():
    """Test MCP server connection with detailed diagnostics."""
    
    # Get MCP server URL from environment or command line
    mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:7777/mcp")
    if len(sys.argv) > 1:
        mcp_url = sys.argv[1]
    
    logger.info(f"Testing MCP connection to: {mcp_url}")
    
    try:
        # Configure headers for HTTPS requests
        headers = {}
        if mcp_url.startswith("https://"):
            headers = {
                "User-Agent": "FastMCP-Test-Client/1.0",
                "Accept": "application/json, text/event-stream"
            }
        
        # Create client with timeout
        client = Client(
            mcp_url,
            timeout=30.0,
            headers=headers if headers else None
        )
        
        logger.info("Created MCP client, attempting connection...")
        
        async with client:
            logger.info("Connected successfully!")
            
            # Test ping
            logger.info("Testing ping...")
            await client.ping()
            logger.info("✅ Ping successful")
            
            # List available tools
            logger.info("Listing available tools...")
            tools = await client.list_tools()
            logger.info(f"✅ Found {len(tools.tools)} tools: {[tool.name for tool in tools.tools]}")
            
            # Test a simple tool call if available
            if tools.tools:
                tool_name = tools.tools[0].name
                logger.info(f"Testing tool call: {tool_name}")
                try:
                    # Try with minimal parameters
                    result = await client.call_tool(tool_name, {})
                    logger.info(f"✅ Tool call successful: {result}")
                except Exception as e:
                    logger.warning(f"⚠️ Tool call failed (expected for some tools): {e}")
            
            logger.info("🎉 All tests passed!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        
        # Additional diagnostics for common issues
        if "400" in str(e):
            logger.error("🔍 400 error suggests:")
            logger.error("  - URL path might be incorrect (should end with /mcp)")
            logger.error("  - Server might not be running")
            logger.error("  - Request format might be incompatible")
        elif "timeout" in str(e).lower():
            logger.error("🔍 Timeout suggests:")
            logger.error("  - Server is not responding")
            logger.error("  - Network connectivity issues")
            logger.error("  - Server is overloaded")
        elif "connection" in str(e).lower():
            logger.error("🔍 Connection error suggests:")
            logger.error("  - Server is not running")
            logger.error("  - Incorrect URL or port")
            logger.error("  - Network routing issues")
        
        return False

async def main():
    """Main test function."""
    print("🔧 MCP Connection Diagnostic Tool")
    print("=" * 50)
    
    success = await test_mcp_connection()
    
    if success:
        print("\n✅ All tests passed - MCP server is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed - check the logs above for details")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 