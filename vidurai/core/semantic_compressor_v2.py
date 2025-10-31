"""
Vidurai v2.0 - Module 1: Semantic Compression
Compresses verbose conversation history into dense summaries

Philosophy:
"Transform many words into few, without losing wisdom"
"""
import time
import re
from typing import List, Optional, Dict, Any
from datetime import datetime

# Relative import since we're in vidurai/core/
from .data_structures_v2 import (
    Memory, CompressedMemory, Message, CompressionWindow,
    CompressionResult, estimate_tokens, calculate_compression_ratio,
    MemoryType
)


class LLMClient:
    """
    Abstract LLM client for compression
    Supports OpenAI and Anthropic
    """
    
    def __init__(self, provider: str = "openai", api_key: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider.lower()
        self.api_key = api_key
        
        # Set default models
        if model:
            self.model = model
        elif self.provider == "openai":
            self.model = "gpt-3.5-turbo"
        elif self.provider == "anthropic":
            self.model = "claude-3-haiku-20240307"
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        self._client = None
    
    def _get_client(self):
        """Lazy load the actual API client"""
        if self._client:
            return self._client
        
        if self.provider == "openai":
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("OpenAI package not installed. Run: pip install openai")
        
        elif self.provider == "anthropic":
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("Anthropic package not installed. Run: pip install anthropic")
        
        return self._client
    
    def compress(self, text: str, system_prompt: str = "") -> str:
        """
        Compress text using LLM
        """
        client = self._get_client()
        
        if self.provider == "openai":
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": text})
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=500
            )
            return response.choices[0].message.content
        
        elif self.provider == "anthropic":
            response = client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                system=system_prompt if system_prompt else "You are a helpful assistant.",
                messages=[{"role": "user", "content": text}]
            )
            return response.content[0].text
        
        return ""


class SemanticCompressor:
    """
    Module 1: Semantic Compression
    
    Transforms verbose conversation history into dense summaries
    
    Example:
        Input (5 messages, 200 tokens):
            "Hi, my name is Chandan"
            "I'm from India"
            "I live in Delhi"
            "I work in fintech"
            "I'm building Vidurai"
        
        Output (1 summary, 40 tokens):
            "User: Chandan from Delhi, India. Works in fintech, building Vidurai."
        
        Token Savings: 80% (160 tokens saved)
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        compression_threshold: int = 10,
        min_tokens_to_compress: int = 100,
        target_compression_ratio: float = 0.75  # Aim for 75% reduction
    ):
        """
        Initialize Semantic Compressor
        
        Args:
            llm_client: LLM client for summarization (OpenAI or Anthropic)
            compression_threshold: Number of messages before compression triggers
            min_tokens_to_compress: Minimum tokens needed to bother compressing
            target_compression_ratio: Target percentage of tokens to save
        """
        self.llm_client = llm_client
        self.compression_threshold = compression_threshold
        self.min_tokens_to_compress = min_tokens_to_compress
        self.target_compression_ratio = target_compression_ratio
        
        # Statistics
        self.total_compressions = 0
        self.total_tokens_saved = 0
        self.compression_history = []
    
    def should_compress(self, messages: List[Message]) -> bool:
        """
        Determine if compression should be triggered
        
        Criteria:
        1. Enough messages (>= threshold)
        2. Enough tokens (>= min_tokens)
        3. Messages are old enough (not recent conversation)
        """
        if len(messages) < self.compression_threshold:
            return False
        
        total_tokens = sum(msg.tokens or estimate_tokens(msg.content) for msg in messages)
        if total_tokens < self.min_tokens_to_compress:
            return False
        
        return True
    
    def detect_compressible_window(
        self,
        messages: List[Message],
        keep_recent: int = 5
    ) -> Optional[CompressionWindow]:
        """
        Detect a window of messages that can be compressed
        
        Strategy: Keep the most recent N messages untouched, compress the rest
        
        Args:
            messages: All messages in working memory
            keep_recent: Number of recent messages to keep uncompressed
        
        Returns:
            CompressionWindow or None if no compression needed
        """
        # Need enough messages to make compression worthwhile
        if len(messages) <= keep_recent:
            return None
        
        # Identify the compressible window (all except recent N)
        compressible = messages[:-keep_recent]
        
        # Calculate total tokens in compressible window
        total_tokens = sum(
            msg.tokens or estimate_tokens(msg.content) 
            for msg in compressible
        )
        
        # Check if compressible window meets thresholds
        if len(compressible) < self.compression_threshold:
            return None
            
        if total_tokens < self.min_tokens_to_compress:
            return None
        
        window = CompressionWindow(
            messages=compressible,
            start_index=0,
            end_index=len(compressible),
            total_tokens=total_tokens
        )
        
        return window
    
    def _build_compression_prompt(self, window: CompressionWindow) -> tuple:
        """
        Build the prompt for LLM compression
        
        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = """You are an expert at extracting and summarizing key information from conversations.

Your task: Compress the conversation below into a concise summary that preserves all important facts.

Guidelines:
1. Extract key facts about the user (name, location, work, projects, preferences)
2. Keep first-person perspective for user facts ("User: Chandan from Delhi")
3. Be extremely concise - aim for 75% reduction in length
4. Preserve proper nouns, numbers, and specific details
5. Group related information together
6. Omit pleasantries and filler

Output format:
- Start with "Summary: "
- Use bullet points for multiple facts
- Max 3-5 sentences total"""

        # Build conversation text
        conversation = window.to_text()
        
        user_prompt = f"""Compress this conversation:

{conversation}

Provide a concise summary that preserves all important information."""

        return system_prompt, user_prompt
    
    def _extract_facts(self, summary: str) -> List[Dict[str, str]]:
        """
        Extract structured facts from the summary
        
        Example:
            Input: "User: Chandan from Delhi, India. Works in fintech, building Vidurai."
            Output: [
                {"entity": "user", "attribute": "name", "value": "Chandan"},
                {"entity": "user", "attribute": "location", "value": "Delhi, India"},
                {"entity": "user", "attribute": "work", "value": "fintech"},
                {"entity": "user", "attribute": "project", "value": "Vidurai"}
            ]
        """
        facts = []
        
        # Simple pattern matching (can be enhanced with NLP)
        patterns = [
            (r"name is (\w+)", "name"),
            (r"from ([^,\.]+)", "location"),
            (r"live in ([^,\.]+)", "location"),
            (r"work in ([^,\.]+)", "work"),
            (r"building ([^,\.]+)", "project"),
            (r"studying ([^,\.]+)", "education"),
        ]
        
        summary_lower = summary.lower()
        
        for pattern, attribute in patterns:
            matches = re.findall(pattern, summary_lower)
            for match in matches:
                facts.append({
                    "entity": "user",
                    "attribute": attribute,
                    "value": match.strip()
                })
        
        return facts
    
    def compress_window(
        self,
        window: CompressionWindow,
        importance: float = 0.6
    ) -> CompressionResult:
        """
        Compress a window of messages into a summary
        
        Args:
            window: The compression window
            importance: Importance score for the compressed memory
        
        Returns:
            CompressionResult with compressed memory or error
        """
        start_time = time.time()
        
        try:
            # Check if we have an LLM client
            if not self.llm_client:
                return CompressionResult(
                    success=False,
                    error="No LLM client configured",
                    processing_time=time.time() - start_time
                )
            
            # Build compression prompt
            system_prompt, user_prompt = self._build_compression_prompt(window)
            
            # Call LLM
            summary = self.llm_client.compress(user_prompt, system_prompt)
            
            if not summary:
                return CompressionResult(
                    success=False,
                    error="LLM returned empty response",
                    processing_time=time.time() - start_time
                )
            
            # Extract facts
            facts = self._extract_facts(summary)
            
            # Calculate token counts
            compressed_tokens = estimate_tokens(summary)
            original_tokens = window.total_tokens
            tokens_saved = original_tokens - compressed_tokens
            compression_ratio = calculate_compression_ratio(original_tokens, compressed_tokens)
            
            # Create compressed memory
            compressed_memory = CompressedMemory(
                content=summary,
                importance=importance,
                original_memories=[msg.message_id for msg in window.messages],
                original_count=window.message_count,
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                compression_ratio=compression_ratio,
                facts=facts
            )
            
            # Update statistics
            self.total_compressions += 1
            self.total_tokens_saved += tokens_saved
            self.compression_history.append({
                'timestamp': datetime.now(),
                'original_tokens': original_tokens,
                'compressed_tokens': compressed_tokens,
                'ratio': compression_ratio
            })
            
            processing_time = time.time() - start_time
            
            return CompressionResult(
                success=True,
                compressed_memory=compressed_memory,
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                tokens_saved=tokens_saved,
                compression_ratio=compression_ratio,
                processing_time=processing_time
            )
        
        except Exception as e:
            return CompressionResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get compression statistics
        """
        if not self.compression_history:
            return {
                'total_compressions': 0,
                'total_tokens_saved': 0,
                'average_compression_ratio': 0.0,
                'average_processing_time': 0.0
            }
        
        avg_ratio = sum(h['ratio'] for h in self.compression_history) / len(self.compression_history)
        
        return {
            'total_compressions': self.total_compressions,
            'total_tokens_saved': self.total_tokens_saved,
            'average_compression_ratio': avg_ratio,
            'compression_history': self.compression_history[-10:]  # Last 10
        }


class MockLLMClient:
    """
    Mock LLM client for testing without API calls
    Generates deterministic summaries
    """
    
    def __init__(self):
        self.provider = "mock"
        self.model = "mock-model"
    
    def compress(self, text: str, system_prompt: str = "") -> str:
        """
        Generate a mock summary
        Strategy: Extract key nouns and proper nouns
        """
        # Simple extraction
        lines = text.split('\n')
        facts = []
        
        for line in lines:
            # Extract proper nouns and key phrases
            if 'name is' in line.lower():
                name = line.split('name is')[-1].strip().rstrip('.')
                facts.append(f"Name: {name}")
            elif 'from' in line.lower() and 'USER:' in line:
                location = line.split('from')[-1].strip().rstrip('.')
                facts.append(f"From: {location}")
            elif 'work' in line.lower() or 'building' in line.lower():
                facts.append(line.split(':')[-1].strip())
        
        if facts:
            summary = "Summary: " + " | ".join(facts[:5])
        else:
            # Generic compression - just take first few words
            words = text.split()[:20]
            summary = f"Summary: {' '.join(words)}..."
        
        return summary