#!/usr/bin/env python

"""
Memory Management System for Agent Conversations

This module provides functionality for managing conversation memory in agent-based systems,
particularly focused on customer support interactions. It includes:

- Memory initialization and management
- Session handling and tracking
- Conversation history storage and retrieval
- Agent creation with memory persistence

The system uses AWS Bedrock's MemoryClient for storing conversation data and supports
features like:
- Creating and checking memory collections
- Generating unique session IDs
- Loading recent conversation history
- Storing new conversation messages
- Managing memory across multiple sessions

Dependencies:
    - datetime
    - json  
    - logging
    - os
    - bedrock_agentcore.memory

Example:
    memory = create_memory_if_not_exists(
        memory_client,
        name="CustomerSupportAgentMemory",
        description="Memory for customer support conversations"
    )
    
    agent = create_personal_agent()
"""

import datetime
import json
import logging
import os

from bedrock_agentcore.memory import MemoryClient
from botocore.exceptions import ClientError
from strands import tool


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


region = os.getenv('AWS_REGION', 'us-west-2')
memory_client = MemoryClient(region_name=region)



def list_memories(memory_client: MemoryClient):
    """
    List all memories in the memory client by printing their ARN and ID.
    
    Args:
        memory_client: The MemoryClient instance to use
        
    Returns:
        None
    """
    return [ memory for memory in memory_client.list_memories() ]


def create_memory_if_not_exists(memory_client: MemoryClient, name: str, description: str):
    """
    Create a new memory if one with the given name doesn't already exist.
    
    Args:
        memory_client: The MemoryClient instance to use
        memory_name: Name for the memory
        memory_description: Description for the memory
        
    Returns:
        dict: Existing or newly created memory object, None if creation fails
    """
    # # Check if memory already exists
    # existing_memory = check_memory_exists(memory_client, name)
    # if existing_memory:
    #     return existing_memory
    
    # Create new memory if it doesn't exist
    try:
        memory = memory_client.create_memory(
            name = name,
            description = description
        )
        logger.info(f"Created new memory {memory_name} with ID: {memory.get('id')}")
        logger.info(f"Memory:\n{json.dumps(memory, indent=2)}")

        return memory
    except Exception as e:
        logger.error(f"Error creating memory: {str(e)}")
        return None


def create_event(memory_client: MemoryClient, memory_id: str, actor_id: str, session_id: str, messages):
    """
    Create a new event in the memory store.
    
    Args:
        memory_client: The MemoryClient instance to use
        memory_id (str): ID of the memory to create event in
        actor_id (str): Identifier of the actor (agent or end-user) 
        session_id (str): Unique ID for a particular conversation
        messages (list): List of tuples containing (message_content, role) pairs to store
        
    Returns:
        dict: Created event object containing event details
    """
    return memory_client.create_event(
        memory_id = memory_id,
        actor_id = actor_id,
        session_id = session_id,
        messages = messages,
    )


def list_events(memory_client: MemoryClient, memory_id: str, actor_id: str, session_id: str):
    """
    List events from the memory store for a specific memory, actor and session.
    
    Args:
        memory_client: The MemoryClient instance to use
        memory_id (str): ID of the memory to list events from
        actor_id (str): Identifier of the actor (agent or end-user)
        session_id (str): Unique ID for a particular conversation
        
    Returns:
        list: List of conversation events, limited to 5 most recent results
    """
    conversations = memory_client.list_events(
        memory_id = memory_id,
        actor_id = actor_id,
        session_id = session_id,
        max_results = 5,
    )
    return conversations


SAMPLE_CONVERSATION_HISTORY = [
    ("Hi, I'm having trouble with my order #12345", "USER"),
    ("I'm sorry to hear that. Let me look up your order.", "ASSISTANT"),
    ("lookup_order(order_id='12345')", "TOOL"),
    ("I see your order was shipped 3 days ago. What specific issue are you experiencing?", "ASSISTANT"),
    ("Actually, before that - I also want to change my email address", "USER"),
    (
        "Of course! I can help with both. Let's start with updating your email. What's your new email?",
        "ASSISTANT",
    ),
    ("newemail@example.com", "USER"),
    ("update_customer_email(old='old@example.com', new='newemail@example.com')", "TOOL"),
    ("Email updated successfully! Now, about your order issue?", "ASSISTANT"),
    ("The package arrived damaged", "USER"),
]

memory = create_memory_if_not_exists(
    memory_client,
    name = "CustomerSupportAgentMemory",
    description = "Memory for customer support conversations",
)


def main():
    USER_ID = "User84"
    SESSION_ID = f"OrderSupport-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    # List current memories
    print('-' * 80)
    for memory in list_memories(memory_client):
        memory_id = memory.get('id')
        print(f"Memory ID: {memory_id}")
        print(f"Memory Arn: {memory.get('arn')}")
        print(f"Memory Status: {memory.get('status')}")
        print(f"Memory created: {memory.get('createdAt')}")
        print('-' * 80)
        
    # Create an event
    create_event(memory_client, memory_id, USER_ID, SESSION_ID, SAMPLE_CONVERSATION_HISTORY)

    # Describe event just created
    conversations = list_events(memory_client, memory_id, USER_ID, SESSION_ID)
    print(json.dumps(conversations, indent=2, default=str))

if __name__ == '__main__':
    main()
