"""
Strands Data Analyst Assistant - Main Application

This application provides a data analyst assistant powered by Amazon Bedrock and uses 
the Amazon RDS Data API to execute SQL queries against an Aurora Serverless PostgreSQL database.
It leverages Bedrock Agent Core for agent functionality and memory management.
"""

import logging
import json
from uuid import uuid4
import os

# Bedrock Agent Core imports
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands import Agent, tool
from strands_tools import current_time
from strands.models import BedrockModel

# Custom module imports
from src.MemoryHookProvider import MemoryHookProvider
from src.tools import get_tables_information, load_file_content
from src.rds_data_api_utils import run_sql_query
from src.utils import save_raw_query_result, read_messages_by_session, save_agent_interactions
from src.ssm_utils import get_ssm_parameter

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("personal-agent")

# Read memory ID from SSM Parameter Store
try:
    # Read memory ID from SSM
    memory_id = get_ssm_parameter("MEMORY_ID")
    
    # Check if memory ID is empty
    if not memory_id or memory_id.strip() == "":
        error_msg = "Memory ID from SSM is empty. Memory has not been created yet."
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    logger.info(f"Retrieved memory ID from SSM: {memory_id}")
    
    # Initialize Memory Client
    client = MemoryClient(region_name='us-west-2', environment="prod")
    
except Exception as e:
    logger.error(f"Error retrieving memory ID from SSM: {e}")
    raise  # Re-raise the exception to stop execution


# Initialize the Bedrock Agent Core app
app = BedrockAgentCoreApp()

def load_system_prompt():
    """
    Load the system prompt from the instructions.txt file.
    
    This prompt defines the behavior and capabilities of the data analyst assistant.
    If the file is not available, a fallback prompt is used.
    
    Returns:
        str: The system prompt to use for the data analyst assistant
    """
    fallback_prompt = """You are a helpful Data Analyst Assistant who can help with data analysis tasks.
                You can process data, interpret statistics, and provide insights based on data."""
    return load_file_content("instructions.txt", default_content=fallback_prompt)

# Load the system prompt
DATA_ANALYST_SYSTEM_PROMPT = load_system_prompt()

def create_execute_sql_query_tool(user_prompt: str, prompt_uuid: str):
    """
    Create a dynamic SQL query execution tool with session context.
    
    This function creates a tool that can execute SQL queries against the Aurora database
    using the RDS Data API. It also saves query results to DynamoDB for future reference.
    
    Args:
        user_prompt (str): The original user prompt/question
        prompt_uuid (str): Unique identifier for tracking this interaction
        
    Returns:
        function: The configured SQL query execution tool
    """
    @tool
    def execute_sql_query(sql_query: str, description: str) -> str:
        """
        Execute an SQL query against a database and return results for data analysis

        Args:
            sql_query: The SQL query to execute
            description: Concise explanation of the SQL query

        Returns:
            str: JSON string containing the query results or error message
        """
        try:
            # Execute the SQL query using the RDS Data API function
            response_json = json.loads(run_sql_query(sql_query))
            
            # Check if there was an error
            if "error" in response_json:
                return json.dumps(response_json)
            
            # Extract the results
            records_to_return = response_json.get("result", [])
            message = response_json.get("message", "")
            
            # Prepare result object
            if message != "":
                result = {
                    "result": records_to_return,
                    "message": message
                }
            else:
                result = {
                    "result": records_to_return
                }
            
            # Save query results to DynamoDB for future reference
            save_result = save_raw_query_result(
                prompt_uuid,
                user_prompt,
                sql_query,
                description,
                result,
                message
            )
            
            if not save_result["success"]:
                result["saved"] = False
                result["save_error"] = save_result["error"]
                
            return json.dumps(result)
                
        except Exception as e:
            return json.dumps({"error": f"Unexpected error: {str(e)}"})
    
    return execute_sql_query

@app.entrypoint
async def agent_invocation(payload):
    """
    Main handler for agent invocation with streaming response.
    
    This function processes incoming requests, initializes the agent with appropriate tools,
    streams the response back to the client, and saves conversation history.
    
    Expected payload structure:
    {
        "prompt": "Your data analysis question",
        "bedrock_model_id": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "prompt_uuid": "optional-uuid",
        "user_timezone": "US/Pacific",
        "session_id": "optional-session-id",
        "user_id": "optional-user-id",
        "last_turns": "optional-number-of-conversation-turns"
    }
    
    Returns:
        Generator: Yields response chunks for streaming
    """
    try:
        # Extract parameters from payload
        user_message = payload.get("prompt", "No prompt found in input, please guide customer to create a json payload with prompt key")
        bedrock_model_id = payload.get("bedrock_model_id", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
        prompt_uuid = payload.get("prompt_uuid", str(uuid4()))
        user_timezone = payload.get("user_timezone", "US/Pacific")
        session_id = payload.get("session_id", str(uuid4()))
        user_id = payload.get("user_id", "guest")
        last_k_turns = int(payload.get("last_k_turns", 20))
        
        print("Request received: ")
        print(f"Prompt: {user_message}")
        print(f"Prompt UUID: {prompt_uuid}")
        print(f"User Timezone: {user_timezone}")
        print(f"Session ID: {session_id}")
        print(f"User ID: {user_id}")
        print(f"Last K Turns: {last_k_turns}")
        
        # Get conversation history from DynamoDB
        message_history = read_messages_by_session(session_id)
        starting_message_id = len(message_history)
        print(f"Agent Interactions length: {len(message_history)}")
        print(f"Agent Interactions: {message_history}")
        
        # Create Bedrock model instance
        bedrock_model = BedrockModel(model_id=bedrock_model_id)
        
        # Prepare system prompt with user's timezone
        system_prompt = DATA_ANALYST_SYSTEM_PROMPT.replace("{timezone}", user_timezone)
        
        # Create the agent with conversation history, memory hooks, and tools
        agent = Agent(
            #messages=message_history,
            model=bedrock_model,
            system_prompt=system_prompt,
            hooks=[MemoryHookProvider(client, memory_id, user_id, session_id, last_k_turns)],
            tools=[get_tables_information, current_time, create_execute_sql_query_tool(user_message, prompt_uuid)],
            callback_handler=None
        )
        
        # Stream the response to the client
        stream = agent.stream_async(user_message)
        async for event in stream:            
            if "message" in event and "content" in event["message"] and "role" in event["message"] and event["message"]["role"] == "assistant":
                for content_item in event['message']['content']:
                    if "toolUse" in content_item and "input" in content_item["toolUse"] and content_item["toolUse"]['name'] == 'execute_sql_query':
                        yield f" {content_item['toolUse']['input']['description']}.\n\n"
                    elif "toolUse" in content_item and "name" in content_item["toolUse"] and content_item["toolUse"]['name'] == 'get_tables_information':
                        yield "\n\n"
                    elif "toolUse" in content_item and "name" in content_item["toolUse"] and content_item["toolUse"]['name'] == 'current_time':
                        yield "\n\n"
            elif "data" in event:
                yield event['data']
        
        # Save detailed agent interactions after streaming is complete
        save_agent_interactions(session_id, prompt_uuid, starting_message_id, agent.messages)
        
    except Exception as e:
        error_message = f"Error: {str(e)}"
        print(error_message)
        yield error_message

if __name__ == "__main__":
    print("Starting Data Analyst Assistant with Bedrock Agent Core")
    app.run()