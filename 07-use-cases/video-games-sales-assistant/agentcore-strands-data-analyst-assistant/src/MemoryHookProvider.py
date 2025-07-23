"""
Memory Hook Provider for Bedrock Agent Core

This module provides a hook provider for Bedrock Agent Core that manages conversation
memory. It handles loading recent conversation history when the agent starts and
saving new messages as they are added to the conversation.

The MemoryHookProvider class integrates with the Bedrock Agent Core memory system
to provide persistent conversation history across sessions.
"""

import logging

from strands.hooks.events import AgentInitializedEvent, MessageAddedEvent
from strands.hooks.registry import HookProvider, HookRegistry
from bedrock_agentcore.memory import MemoryClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("personal-agent")

class MemoryHookProvider(HookProvider):
    """
    Hook provider for managing conversation memory in Bedrock Agent Core.
    
    This class provides hooks for loading conversation history when the agent
    initializes and saving messages as they are added to the conversation.
    
    Attributes:
        memory_client: Client for interacting with Bedrock Agent Core memory
        memory_id: ID of the memory resource
        actor_id: ID of the user/actor
        session_id: ID of the current conversation session
        last_k_turns: Number of conversation turns to retrieve from history
    """
    
    def __init__(self, memory_client: MemoryClient, memory_id: str, actor_id: str, session_id: str, last_k_turns: int = 20):
        """
        Initialize the memory hook provider.
        
        Args:
            memory_client: Client for interacting with Bedrock Agent Core memory
            memory_id: ID of the memory resource
            actor_id: ID of the user/actor
            session_id: ID of the current conversation session
            last_k_turns: Number of conversation turns to retrieve from history (default: 20)
        """
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.actor_id = actor_id
        self.session_id = session_id
        self.last_k_turns = last_k_turns
    
    def on_agent_initialized(self, event: AgentInitializedEvent):
        """
        Load recent conversation history when agent starts.
        
        This method retrieves the specified number of conversation turns from memory
        and adds them to the agent's system prompt as context.
        
        Args:
            event: Agent initialization event
        """
        try:
            # Load the specified number of conversation turns from memory
            print("************ last_k_turns *********")
            print(self.last_k_turns)
            recent_turns = self.memory_client.get_last_k_turns(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=self.session_id,
                k=self.last_k_turns
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
                print("******************************")
                print(recent_turns)
                event.agent.system_prompt += f"\n\nRecent conversation:\n{context}"
                logger.info(f"✅ Loaded {len(recent_turns)} conversation turns")
                print("******************************")
                
        except Exception as e:
            logger.error(f"Memory load error: {e}")
    
    def on_message_added(self, event: MessageAddedEvent):
        """
        Store messages in memory as they are added to the conversation.
        
        This method saves each new message to the Bedrock Agent Core memory system
        for future reference.
        
        Args:
            event: Message added event
        """
        messages = event.agent.messages
        print("------------|||||||||||||")
        print(messages)

        try:
            last_message = messages[-1]
            
            # Check if the message has the expected structure
            if "role" in last_message and "content" in last_message and last_message["content"]:
                role = last_message["role"]
                
                # Look for text content or specific toolResult content
                content_to_save = None
                
                for content_item in last_message["content"]:
                    # Check for regular text content
                    if "text" in content_item:
                        content_to_save = content_item["text"]
                        break
                    
                    # Check for toolResult with get_tables_information
                    elif "toolResult" in content_item:
                        tool_result = content_item["toolResult"]
                        if ("content" in tool_result and 
                            tool_result["content"] and 
                            "text" in tool_result["content"][0]):
                            
                            tool_text = tool_result["content"][0]["text"]
                            # Check if it contains the specific toolUsed marker
                            if "'toolUsed': 'get_tables_information'" in tool_text:
                                content_to_save = tool_text
                                break
                
                if content_to_save:
                    print("/////////////////////////")
                    print(content_to_save)
                    print("----")
                    print(role)
                    print("/////////////////////////")

                    self.memory_client.save_conversation(
                        memory_id=self.memory_id,
                        actor_id=self.actor_id,
                        session_id=self.session_id,
                        messages=[(content_to_save, role)]
                    )
                    print("------------||||||||||||| SAVED")
                else:
                    print("------------||||||||||||| NOT SAVED")
            else:
                print("------------||||||||||||| INVALID MESSAGE STRUCTURE")
        except Exception as e:
            logger.error(f"Memory save error: {e}")
    
    def register_hooks(self, registry: HookRegistry):
        """
        Register memory hooks with the hook registry.
        
        Args:
            registry: Hook registry to register with
        """
        # Register memory hooks
        registry.add_callback(MessageAddedEvent, self.on_message_added)
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)