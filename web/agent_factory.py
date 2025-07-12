import json
import os
from typing import Coroutine, List
import redis
from pathlib import Path
import jsonschema
from agents import Agent, AgentHooks, RunContextWrapper
from tools import all_tools


class MyAgentHooks(AgentHooks):
    def on_start(self, context, agent):
        print(f"\033[92m🚀 Starting agent: {agent.name}\033[0m")
        return super().on_start(context, agent)
    
    def on_tool_start(self, context, agent, tool):
        print(f"\033[93m🔧 Tool starting: {tool.name} from {agent.name}\033[0m")
        return super().on_tool_start(context, agent, tool)
    
    def on_tool_end(self, context, agent, tool, result):
        print(f"\033[94m✅ Tool completed: {tool.name} from {agent.name}\033[0m")
        print(f"\033[94m📄 Tool result type: {type(result)}\033[0m")
        return super().on_tool_end(context, agent, tool, result)
    
    def on_end(self, context, agent, result):
        print(f"\033[95m🏁 Agent completed: {agent.name}\033[0m")
        print(f"\033[95m📋 Final result type: {type(result)}\033[0m")
        return super().on_end(context, agent, result)


def _load_agent_schema() -> dict:
    """
    Load the agent configuration schema.
    
    Returns:
        dict: JSON schema for agent configuration
        
    Raises:
        FileNotFoundError: When schema file is not found
        ValueError: When schema JSON is invalid
    """
    schema_file = Path(__file__).parent / "configs" / "agent_config_schema.json"
    
    try:
        with open(schema_file, 'r') as f:
            schema = json.load(f)
        return schema
    except FileNotFoundError:
        raise FileNotFoundError(f"Agent configuration schema file {schema_file} not found")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in schema file {schema_file}: {e}")


def _validate_agent_config(config: dict, agent_name: str) -> dict:
    """
    Validate agent configuration against the schema.
    
    Args:
        config: Agent configuration to validate
        agent_name: Name of the agent (for error messages)
        
    Returns:
        dict: Validated configuration (same as input)
        
    Raises:
        ValueError: When configuration doesn't match schema
    """
    try:
        schema = _load_agent_schema()
        jsonschema.validate(config, schema)
        return config
    except jsonschema.ValidationError as e:
        raise ValueError(f"Configuration validation failed for agent '{agent_name}': {e.message}")
    except Exception as e:
        raise ValueError(f"Schema validation error for agent '{agent_name}': {e}")


def get_agent_config(agent_name: str) -> dict:
    """
    Retrieves agent configuration from either file or Redis based on USE_REDIS environment variable.
    
    Args:
        agent_name: Name of the agent (used to find the corresponding configuration)
        
    Returns:
        dict: Agent configuration
        
    Raises:
        FileNotFoundError: When config file is not found (file mode)
        redis.ConnectionError: When Redis connection fails (Redis mode)
        ValueError: When JSON is invalid or config is not found in Redis
        EnvironmentError: When USE_REDIS environment variable has invalid value
    """
    use_redis = os.getenv('USE_REDIS', 'False').lower()
    
    if use_redis not in ['true', 'false']:
        raise EnvironmentError(f"USE_REDIS environment variable must be 'True' or 'False', got: {use_redis}")
    
    use_redis = use_redis == 'true'
    
    if use_redis:
        config = _get_config_from_redis(agent_name)
    else:
        config = _get_config_from_file(agent_name)
    
    # Validate configuration against schema
    return _validate_agent_config(config, agent_name)


def _get_config_from_file(agent_name: str) -> dict:
    """
    Retrieves agent configuration from JSON file.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        dict: Agent configuration
        
    Raises:
        FileNotFoundError: When config file is not found
        ValueError: When JSON is invalid
    """
    config_file = f"configs/{agent_name}.json"
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file {config_file} not found")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file {config_file}: {e}")


def _get_config_from_redis(agent_name: str) -> dict:
    """
    Retrieves agent configuration from Redis.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        dict: Agent configuration
        
    Raises:
        redis.ConnectionError: When Redis connection fails
        ValueError: When config is not found in Redis or JSON is invalid
    """
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()  # Test connection
    except redis.ConnectionError as e:
        raise redis.ConnectionError(f"Could not connect to Redis at localhost:6379: {e}")
    
    key = f"agent|{agent_name}"
    
    try:
        config_json = r.get(key)
        if config_json is None:
            raise ValueError(f"Configuration for agent '{agent_name}' not found in Redis (key: {key})")
        
        config = json.loads(config_json)
        return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in Redis configuration for agent '{agent_name}': {e}")
    except Exception as e:
        raise ValueError(f"Error retrieving configuration from Redis for agent '{agent_name}': {e}")


def create_agent_from_config(agent_name: str, agents_as_tools: dict = {}, agent_handoffs: List[Agent] = []) -> Agent:
    """
    Creates an agent from a configuration (either file or Redis based on USE_REDIS env var).
    
    Args:
        agent_name: Name of the agent (used to find the corresponding configuration)
        agents_as_tools: Optional dict of Agent instances to use as tools
        
    Returns:
        Agent: Configured agent instance
        
    Raises:
        FileNotFoundError: When config file is not found (file mode)
        redis.ConnectionError: When Redis connection fails (Redis mode)
        ValueError: When JSON is invalid, config not found, or tool not found
        EnvironmentError: When USE_REDIS environment variable has invalid value
    """
    try:
        config = get_agent_config(agent_name)
    except (FileNotFoundError, redis.ConnectionError, ValueError, EnvironmentError) as e:
        # Re-raise with more context
        raise type(e)(f"Failed to load configuration for agent '{agent_name}': {e}")
    
    # Extract required fields with defaults
    name = config.get("name", agent_name)
    instructions = config.get("instructions", "You are a helpful assistant.")
    model = config.get("model", "gpt-4o-mini")
    tools = config.get("tools", [])

    # Build tool list from all_tools
    tool_list = []
    for tool in tools:
        if tool in all_tools:
            tool_list.append(all_tools[tool])
        else:
            raise ValueError(f"Tool '{tool}' not found in all_tools for agent '{agent_name}'")
    
    # Add agents as tools
    for agent_name_as_tool, agent_info in agents_as_tools.items():
        try:
            tool_list.append(agent_info["agent"].as_tool(
                tool_name=agent_name_as_tool,
                tool_description=agent_info["description"]
            ))
        except KeyError as e:
            raise ValueError(f"Invalid agent_as_tool configuration for '{agent_name_as_tool}': missing {e}")
        except Exception as e:
            raise ValueError(f"Failed to add agent '{agent_name_as_tool}' as tool: {e}")

    try:
        return Agent(
            name=name,
            instructions=instructions,
            model=model,
            tools=tool_list,
            hooks=MyAgentHooks(),
            handoffs=agent_handoffs
        )
    except Exception as e:
        raise ValueError(f"Failed to create agent '{agent_name}': {e}") 