#!/usr/bin/env python

"""
Memory Management System for Agent Conversations

This module demonstrates basic memory management functionality using Amazon Bedrock AgentCore Memory.
It provides examples of:

- Creating and listing memory collections
- Creating conversation events with message history
- Retrieving conversation events from memory
- Managing customer support conversation scenarios

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
"""

import datetime
import json
import logging
import os

from bedrock_agentcore.memory import MemoryClient


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
    List all memories in the memory client.
    
    Args:
        memory_client: The MemoryClient instance to use
        
    Returns:
        list: List of memory objects
    """
    return [memory for memory in memory_client.list_memories()]


def create_memory_if_none_exist(memory_client: MemoryClient, name: str, description: str):
    """
    Create a new memory collection, if none exist.
    Otherwise return the first memory from list_memories()
    
    Args:
        memory_client: The MemoryClient instance to use
        name: Name for the memory
        description: Description for the memory
        
    Returns:
        dict: Created memory object, None if creation fails
    """
    memories = list_memories(memory_client)
    if len(memories):
        return memories[0]  # For demo purposes, we assume that the only memory is the correct one.

    try:
        memory = memory_client.create_memory(
            name=name,
            description=description
        )
        logger.info(f"Created new memory {name} with ID: {memory.get('id')}")
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
        memory_id: ID of the memory to create event in
        actor_id: Identifier of the actor (agent or end-user) 
        session_id: Unique ID for a particular conversation
        messages: List of tuples containing (message_content, role) pairs to store
        
    Returns:
        dict: Created event object containing event details
    """
    return memory_client.create_event(
        memory_id=memory_id,
        actor_id=actor_id,
        session_id=session_id,
        messages=messages,
    )


def list_events(memory_client: MemoryClient, memory_id: str, actor_id: str, session_id: str):
    """
    List events from the memory store for a specific memory, actor and session.
    
    Args:
        memory_client: The MemoryClient instance to use
        memory_id: ID of the memory to list events from
        actor_id: Identifier of the actor (agent or end-user)
        session_id: Unique ID for a particular conversation
        
    Returns:
        list: List of conversation events, limited to 5 most recent results
    """
    conversations = memory_client.list_events(
        memory_id=memory_id,
        actor_id=actor_id,
        session_id=session_id,
        max_results=5,
    )
    return conversations


SAMPLE_CONVERSATION_HISTORY = [
    ("Hi, I'm having trouble with my order #12345", "USER"),
    ("I'm sorry to hear that. Let me look up your order.", "ASSISTANT"),
    ("lookup_order(order_id='12345')", "TOOL"),
    ("I see your order was shipped 3 days ago. What specific issue are you experiencing?", "ASSISTANT"),
    ("The package arrived damaged", "USER"),
]

memory = create_memory_if_none_exist(
    memory_client,
    name="CustomerSupportAgentMemory",
    description="Memory for customer support conversations",
)


def main():
    USER_ID = "User84"
    SESSION_ID = f"OrderSupport-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # List current memories
    print('-' * 80)
    memories = list_memories(memory_client)
    for mem in memories:
        memory_id = mem.get('id')
        print(f"Memory ID: {memory_id}")
        print(f"Memory Arn: {mem.get('arn')}")
        print(f"Memory Status: {mem.get('status')}")
        print(f"Memory created: {mem.get('createdAt')}")
        print('-' * 80)
        
    # Create an event
    create_event(memory_client, memory_id, USER_ID, SESSION_ID, SAMPLE_CONVERSATION_HISTORY)

    # Describe event just created
    conversations = list_events(memory_client, memory_id, USER_ID, SESSION_ID)
    print(json.dumps(conversations, indent=2, default=str))


if __name__ == '__main__':
    main()
