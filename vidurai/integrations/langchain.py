"""
LangChain Integration for Vidurai
Drop-in replacement for ConversationBufferMemory with intelligent forgetting
"""

from typing import Any, Dict, List
from langchain.memory.chat_memory import BaseChatMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from pydantic import Field
from vidurai import create_memory_system
from loguru import logger

class ViduraiMemory(BaseChatMemory):
    """
    Vidurai memory for LangChain - drop-in replacement for ConversationBufferMemory
    Features:
    - Three-layer memory architecture
    - Strategic forgetting
    - Importance-based recall
    """
    
    memory_key: str = "chat_history"
    input_key: str = "input"
    output_key: str = "output"
    vidurai_memory: Any = Field(default_factory=create_memory_system)
    max_token_limit: int = 2000
    aggressive_forgetting: bool = False  # ✨ NEW: Enable aggressive mode
    
    def __init__(self, aggressive: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.aggressive_forgetting = aggressive
        # ✨ ENHANCED: Create with aggressive forgetting option
        self.vidurai_memory = create_memory_system(
            working_capacity=10,
            episodic_capacity=1000,
            aggressive_forgetting=aggressive
        )
        logger.info(f"Initialized ViduraiMemory for LangChain (aggressive={aggressive})")
    
    @property
    def memory_variables(self) -> List[str]:
        """Return memory variables"""
        return [self.memory_key]
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✨ ENHANCED: Load ONLY important memories for LangChain
        Automatically cleans up forgotten items and filters by importance
        """
        try:
            # Get only important memories (recall already filters by importance > 0.5)
            # recall() now automatically calls _cleanup_forgotten()
            memories = self.vidurai_memory.recall(limit=10)
            
            # If we got nothing, that means everything was forgotten or no memories exist
            if not memories:
                logger.debug("No important memories to load")
                return {self.memory_key: []}
            
            logger.debug(f"Loading {len(memories)} important memories for LangChain")
            
        except Exception as e:
            logger.error(f"Error loading memories: {e}")
            memories = []
        
        # Convert to LangChain message format
        messages = []
        for memory in memories:  # Already filtered to top 10 important
            try:
                content = memory.content if hasattr(memory, 'content') else str(memory)
                
                # Parse message type from content
                if "human:" in content.lower():
                    messages.append(HumanMessage(content=content))
                elif "ai:" in content.lower():
                    messages.append(AIMessage(content=content))
                else:
                    # Default to human message if format unclear
                    messages.append(HumanMessage(content=content))
                    
            except Exception as e:
                logger.warning(f"Error converting memory to message: {e}")
                continue
        
        logger.debug(f"Converted {len(messages)} memories to LangChain messages")
        return {self.memory_key: messages}
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Save context to Vidurai memory"""
        try:
            # Save human input
            human_input = self._get_input_output(inputs, self.input_key)
            if human_input:
                human_text = human_input[0] if isinstance(human_input, list) else human_input
                self.vidurai_memory.remember(
                    f"Human: {human_text}",
                    importance=0.7  # High importance for user input
                )
                logger.debug(f"Saved human input: {human_text[:50]}...")
        except Exception as e:
            logger.error(f"Error saving human input: {e}")
        
        try:
            # Save AI output
            ai_output = self._get_input_output(outputs, self.output_key)
            if ai_output:
                ai_text = ai_output[0] if isinstance(ai_output, list) else ai_output
                self.vidurai_memory.remember(
                    f"AI: {ai_text}",
                    importance=0.6  # Medium-high importance for AI response
                )
                logger.debug(f"Saved AI output: {ai_text[:50]}...")
        except Exception as e:
            logger.error(f"Error saving AI output: {e}")
    
    def clear(self) -> None:
        """Clear all memories"""
        self.vidurai_memory = create_memory_system(
            aggressive_forgetting=self.aggressive_forgetting
        )
        logger.info("Cleared Vidurai memory")
    
    def _get_input_output(
        self, values: Dict[str, Any], key: str
    ) -> List[str]:
        """Extract input/output from values"""
        if key in values:
            value = values[key]
            if isinstance(value, str):
                return [value]
            elif isinstance(value, list):
                return value
        return []


class ViduraiConversationChain:
    """
    Ready-to-use conversation chain with Vidurai memory
    """
    
    @staticmethod
    def create(llm, verbose: bool = False, aggressive: bool = False):
        """
        Create a conversation chain with Vidurai memory
        
        Args:
            llm: LangChain LLM instance
            verbose: Enable verbose output
            aggressive: Enable aggressive forgetting (faster cleanup)
        
        Example:
            from langchain.llms import OpenAI
            from vidurai.integrations.langchain import ViduraiConversationChain
            
            llm = OpenAI(temperature=0.7)
            
            # Standard mode (forget after 30s/2min/5min)
            chain = ViduraiConversationChain.create(llm)
            
            # Aggressive mode (forget after 5s/10s/30s)
            chain = ViduraiConversationChain.create(llm, aggressive=True)
            
            response = chain.predict(input="Hello, my name is Alice")
        """
        from langchain.chains import ConversationChain
        
        # ✨ ENHANCED: Create memory with aggressive option
        memory = ViduraiMemory(aggressive=aggressive)
        chain = ConversationChain(
            llm=llm,
            memory=memory,
            verbose=verbose
        )
        
        logger.info(f"Created ViduraiConversationChain (aggressive={aggressive})")
        return chain