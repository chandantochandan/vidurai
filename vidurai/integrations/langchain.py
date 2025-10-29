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
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vidurai_memory = create_memory_system()
        logger.info("Initialized ViduraiMemory for LangChain")
    
    @property
    def memory_variables(self) -> List[str]:
        """Return memory variables"""
        return [self.memory_key]
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load memory variables for LangChain"""
        # Get relevant memories from Vidurai
        memories = self.vidurai_memory.recall()
        
        # Convert to LangChain message format
        messages = []
        for memory in memories[:10]:  # Limit to most recent relevant
            if "human:" in memory.content.lower():
                messages.append(HumanMessage(content=memory.content))
            elif "ai:" in memory.content.lower():
                messages.append(AIMessage(content=memory.content))
        
        return {self.memory_key: messages}
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Save context to Vidurai memory"""
        # Save human input
        human_input = self._get_input_output(inputs, self.input_key)[0]
        if human_input:
            self.vidurai_memory.remember(
                f"Human: {human_input}",
                importance=0.7
            )
        
        # Save AI output
        ai_output = self._get_input_output(outputs, self.output_key)[0]
        if ai_output:
            self.vidurai_memory.remember(
                f"AI: {ai_output}",
                importance=0.6
            )
    
    def clear(self) -> None:
        """Clear all memories"""
        self.vidurai_memory = create_memory_system()
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
    def create(llm, verbose: bool = False):
        """
        Create a conversation chain with Vidurai memory
        
        Example:
            from langchain.llms import OpenAI
            from vidurai.integrations.langchain import ViduraiConversationChain
            
            llm = OpenAI(temperature=0.7)
            chain = ViduraiConversationChain.create(llm)
            response = chain.predict(input="Hello, my name is Alice")
        """
        from langchain.chains import ConversationChain
        
        memory = ViduraiMemory()
        chain = ConversationChain(
            llm=llm,
            memory=memory,
            verbose=verbose
        )
        
        logger.info("Created ViduraiConversationChain")
        return chain