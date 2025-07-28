#!/usr/bin/env python

"""
Personal Assistant Agent with Memory and Web Search

Demonstrates Amazon Bedrock AgentCore Memory integration with a personal assistant
that can search the web and maintain conversation history across sessions.

Features:
- Persistent conversation memory using Bedrock AgentCore Memory
- Web search capabilities via DuckDuckGo
- Memory hooks for loading/storing conversation history
- Session-based memory management

Acknowledgments - code has been adapted from:
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-getting-started.html
- https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/04-AgentCore-memory/01-short-term-memory/01-single-agent/with-strands-agent/personal-agent.ipynb
"""

import datetime
import logging
import os

from basic_memory import create_memory_if_none_exist, list_memories
from bedrock_agentcore.memory import MemoryClient
from strands import Agent, tool
from strands.hooks import AgentInitializedEvent, HookProvider, HookRegistry, MessageAddedEvent


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


region = os.getenv('AWS_REGION', 'us-west-2')
memory_client = MemoryClient(region_name=region)


@tool
def websearch(keywords: str, region: str = "us-en", max_results: int = 5) -> str:
    """Search the web for current information using DuckDuckGo.
    
    Args:
        keywords: Search query terms
        region: Search region (us-en, uk-en, etc.)
        max_results: Maximum number of results to return
        
    Returns:
        Search results or error message
    """
    try:
        results = DDGS().text(keywords, region=region, max_results=max_results)
        return results if results else "No results found."
    except RatelimitException:
        return "Rate limit reached. Please try again later."
    except DDGSException as e:
        return f"Search error: {e}"
    except Exception as e:
        return f"Search error: {str(e)}"


def create_memory_if_none_exist(memory_client: MemoryClient, name: str, description: str, event_expiry: int):
    """
    Create a new memory collection, if none exist.
    Otherwise return the first memory from list_memories()
    
    Args:
        memory_client: The MemoryClient instance to use
        name (str): Name for the memory
        description (str): Description for the memory
        event_expiry (int): Retention period for short-term memory. This can be upto 365 days.
        
    Returns:
        dict: Created memory object, None if creation fails
    """
    memories = list_memories(memory_client)
    if len(memories):
        return memories[0]  # For demo purposes, we assume that the only memory is the correct one.

    try:
        memory = memory_client.create_memory_and_wait(
            name=name,
            strategies=[],  # No strategies for short term memory
            description=description,
            event_expiry=event_expiry,
        )
        logger.info(f"Created new memory {name} with ID: {memory.get('id')}")
        logger.info(f"Memory:\n{json.dumps(memory, indent=2)}")
        return memory
    except Exception as e:
        # Show any errors during memory creation
        logger.error(f"❌ ERROR creating memory: {e}")
        import traceback
        traceback.print_exc()
        # Cleanup on error - delete the memory if it was partially created
        if memory_id:
            try:
                client.delete_memory_and_wait(memory_id=memory_id)
                logger.info(f"Cleaned up memory: {memory_id}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up memory: {cleanup_error}")
        return None


class MemoryHookProvider(HookProvider):
    """Hook provider for managing conversation memory with Bedrock AgentCore Memory.
    
    Loads conversation history on agent initialization and stores new messages
    as they are added to maintain context across sessions.
    
    Args:
        memory_client: Bedrock AgentCore Memory client
        memory_id: Memory collection identifier
        actor_id: User/agent identifier
        session_id: Current session identifier
    """

    def __init__(self, memory_client: MemoryClient, memory_id: str, actor_id: str, session_id: str):
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.actor_id = actor_id
        self.session_id = session_id
    
    def on_agent_initialized(self, event: AgentInitializedEvent):
        """Load last 5 conversation turns and add to agent context."""
        try:
            # Load the last 5 conversation turns from memory
            recent_turns = self.memory_client.get_last_k_turns(
                memory_id = self.memory_id,
                actor_id = self.actor_id,
                session_id = self.session_id,
                k = 5
            )
            
            if recent_turns:
                # Format conversation history for context
                context_messages = []
                for turn in recent_turns:
                    for message in turn:
                        role = message['role']
                        content = message['content']['text']
                        context_messages.append(f"{role}: {content}")
                
                context = "\n".join(context_messages)
                # Add context to agent's system prompt.
                event.agent.system_prompt += f"\n\nRecent conversation:\n{context}"
                logger.info(f"✅ Loaded {len(recent_turns)} conversation turns")
                
        except Exception as e:
            logger.error(f"Memory load error: {e}")
    
    def on_message_added(self, event: MessageAddedEvent):
        """Store new message in memory."""
        messages = event.agent.messages
        try:
            self.memory_client.create_event(
                memory_id = self.memory_id,
                actor_id = self.actor_id,
                session_id = self.session_id,
                messages = [ (messages[-1]["content"][0]["text"], messages[-1]["role"]) ]
            )
        except Exception as e:
            logger.error(f"Memory save error: {e}")
    
    def register_hooks(self, registry: HookRegistry):
        # Register memory hooks
        registry.add_callback(MessageAddedEvent, self.on_message_added)
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)


def create_personal_agent(memory_client: MemoryClient, memory_id: str, actor_id: str, session_id: str):
    """Create personal assistant agent with memory persistence and web search capability.
    
    Args:
        memory_client: Bedrock AgentCore Memory client
        memory_id: Memory collection identifier
        actor_id: User identifier
        session_id: Session identifier
        
    Returns:
        Configured Agent instance
    """
    agent = Agent(
        name="PersonalAssistant",
        system_prompt=f"""You are a helpful personal assistant with web search capabilities.
        
        You can help with:
        - General questions and information lookup
        - Web searches for current information
        - Personal task management
        
        When you need current information, use the websearch function.
        Today's date: {datetime.datetime.today().strftime('%Y-%m-%d')}
        Be friendly and professional.
        """,
        hooks = [ MemoryHookProvider(memory_client, memory_id, actor_id, session_id) ],
        tools = [ websearch ],
    )
    return agent


# Setup
ACTOR_ID = "User123"
SESSION_ID = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')

# Create memory
memory = create_memory_if_none_exist(
    memory_client,
    name = "PersonalAgentMemory",
    description = "Short-term memory for personal agent",
    event_expiry = 30 # Retention period for short-term memory. This can be upto 365 days.
)
memory_id = memory.get('id')

# Create agent
agent = create_personal_agent(memory_client, memory_id, ACTOR_ID, SESSION_ID)
logger.info("✅ Personal agent created with memory and web search")


def step_01_conversation():
    """Demonstrate initial conversation with memory storage."""
    # Test conversation with memory
    print("=== First Conversation ===")
    print(f"User: My name is Alex and I'm interested in learning about AI.")
    print(f"Agent: ", end="")
    agent("My name is Alex and I'm interested in learning about AI.")

    print(f"User: Can you search for the latest AI trends in 2025?")
    print(f"Agent: ", end="")
    agent("Can you search for the latest AI trends in 2025?")

    print(f"User: I'm particularly interested in machine learning applications.")
    print(f"Agent: ", end="")
    agent("I'm particularly interested in machine learning applications.")


def step_02_test_memory_continuity():
    """Test memory continuity across agent instances."""
    # Create new agent instance (simulates user returning)
    print("=== User Returns - New Session ===")
    new_agent = create_personal_agent(memory_client, memory_id, ACTOR_ID, SESSION_ID)

    # Test memory continuity
    print(f"User: What was my name again?")
    print(f"Agent: ", end="")
    new_agent("What was my name again?")

    print(f"User: Can you search for more information about machine learning?")
    print(f"Agent: ", end="")
    new_agent("Can you search for more information about machine learning?")


def step_03_view_stored_memory():
    """Display stored conversation history from memory."""
    # Check what's stored in memory
    print("=== Memory Contents ===")
    recent_turns = memory_client.get_last_k_turns(
        memory_id=memory_id,
        actor_id=ACTOR_ID,
        session_id=SESSION_ID,
        k=3 # Adjust k to see more or fewer turns
    )

    for i, turn in enumerate(recent_turns, 1):
        print(f"Turn {i}:")
        for message in turn:
            role = message['role']
            content = message['content']['text'][:100] + "..." if len(message['content']['text']) > 100 else message['content']['text']
            print(f"  {role}: {content}")
        print()


def main():
    step_01_conversation()
    step_02_test_memory_continuity()
    step_03_view_stored_memory()


if __name__ == '__main__':
    main()
