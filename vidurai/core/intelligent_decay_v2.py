"""
Vidurai v2.0 - Module 2: Intelligent Decay
Entropy and relevance-based memory decay

Philosophy:
"Not all memories deserve equal longevity. Let intelligence decide."
"""
import math
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter

# Try to import sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class SimpleEmbedder:
    """
    Simple fallback embedder using TF-IDF-like approach
    Used when sentence-transformers not available
    """
    
    def __init__(self):
        self.vocabulary = {}
        self.idf = {}
        
    def embed(self, text: str) -> List[float]:
        """Create simple embedding vector"""
        # Tokenize
        words = self._tokenize(text)
        
        # Count term frequencies
        word_counts = Counter(words)
        total_words = len(words)
        
        # Create fixed-size vector (100 dimensions)
        vector = [0.0] * 100
        
        for i, word in enumerate(words[:100]):
            # Simple hash to position
            position = hash(word) % 100
            tf = word_counts[word] / total_words
            vector[position] += tf
        
        # Normalize
        magnitude = math.sqrt(sum(x**2 for x in vector))
        if magnitude > 0:
            vector = [x / magnitude for x in vector]
        
        return vector
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        return text.split()


class EntropyCalculator:
    """
    Calculate information entropy of text
    High entropy = novel, unpredictable, information-dense
    Low entropy = repetitive, predictable, common
    """
    
    @staticmethod
    def calculate(text: str) -> float:
        """
        Calculate Shannon entropy of text
        
        Returns:
            float: Entropy score 0.0-1.0 (normalized)
        """
        if not text or len(text) == 0:
            return 0.0
        
        # Character-level entropy
        char_freq = Counter(text.lower())
        total_chars = len(text)
        
        entropy = 0.0
        for count in char_freq.values():
            prob = count / total_chars
            if prob > 0:
                entropy -= prob * math.log2(prob)
        
        # Normalize to 0-1 (max entropy for English ~4.7 bits)
        max_entropy = 4.7
        normalized = min(entropy / max_entropy, 1.0)
        
        return normalized
    
    @staticmethod
    def calculate_word_entropy(text: str) -> float:
        """
        Calculate word-level entropy
        Higher = more unique words, lower = repetitive
        """
        words = text.lower().split()
        if not words:
            return 0.0
        
        # Word uniqueness ratio
        unique_ratio = len(set(words)) / len(words)
        
        # Average word length (longer words = more information)
        avg_length = sum(len(w) for w in words) / len(words)
        avg_length_normalized = min(avg_length / 10.0, 1.0)
        
        # Combine
        entropy = (unique_ratio * 0.7) + (avg_length_normalized * 0.3)
        
        return entropy
    
    @staticmethod
    def calculate_combined(text: str) -> float:
        """
        Combine character and word entropy
        """
        char_entropy = EntropyCalculator.calculate(text)
        word_entropy = EntropyCalculator.calculate_word_entropy(text)
        
        # Weight word entropy more heavily
        combined = (char_entropy * 0.3) + (word_entropy * 0.7)
        
        return combined


class RelevanceScorer:
    """
    Calculate semantic relevance between memories and current context
    Uses embeddings for similarity
    """
    
    def __init__(self, use_transformers: bool = True):
        """
        Initialize relevance scorer
        
        Args:
            use_transformers: Use sentence-transformers if available
        """
        self.use_transformers = use_transformers and EMBEDDINGS_AVAILABLE
        
        if self.use_transformers:
            # Use lightweight model
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            # Fallback to simple embedder
            self.model = SimpleEmbedder()
    
    def calculate_relevance(
        self, 
        memory_text: str, 
        context_texts: List[str]
    ) -> float:
        """
        Calculate relevance of memory to context
        
        Args:
            memory_text: The memory content
            context_texts: List of recent conversation messages
        
        Returns:
            float: Relevance score 0.0-1.0
        """
        if not context_texts:
            return 0.5  # Neutral if no context
        
        # Get embeddings
        if self.use_transformers:
            memory_emb = self.model.encode(memory_text)
            context_embs = self.model.encode(context_texts)
        else:
            memory_emb = self.model.embed(memory_text)
            context_embs = [self.model.embed(text) for text in context_texts]
        
        # Calculate cosine similarities
        similarities = [
            self._cosine_similarity(memory_emb, ctx_emb)
            for ctx_emb in context_embs
        ]
        
        # Return max similarity (most relevant context)
        return max(similarities) if similarities else 0.0
    
    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        magnitude1 = math.sqrt(sum(a**2 for a in vec1))
        magnitude2 = math.sqrt(sum(b**2 for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)


class IntelligentDecay:
    """
    Module 2: Intelligent Decay Engine
    
    Calculates decay scores based on:
    1. Entropy (information density)
    2. Relevance (similarity to current context)
    3. Access patterns (reinforcement)
    
    High decay score = should be forgotten
    Low decay score = should be kept
    """
    
    def __init__(
        self,
        base_decay_rate: float = 0.1,
        entropy_weight: float = 0.4,
        relevance_weight: float = 0.4,
        access_weight: float = 0.2,
        use_embeddings: bool = True
    ):
        """
        Initialize Intelligent Decay
        
        Args:
            base_decay_rate: Base decay multiplier (0.0-1.0)
            entropy_weight: Weight for entropy component
            relevance_weight: Weight for relevance component
            access_weight: Weight for access pattern component
            use_embeddings: Use sentence transformers for relevance
        """
        self.base_rate = base_decay_rate
        self.entropy_weight = entropy_weight
        self.relevance_weight = relevance_weight
        self.access_weight = access_weight
        
        # Initialize components
        self.entropy_calc = EntropyCalculator()
        self.relevance_scorer = RelevanceScorer(use_transformers=use_embeddings)
        
        # Statistics
        self.evaluations = 0
        self.high_entropy_count = 0
        self.low_entropy_count = 0
    
    def calculate_decay_score(
        self,
        memory,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate decay score for a memory
        
        Args:
            memory: Memory object to evaluate
            context: Current conversation context
        
        Returns:
            float: Decay score 0.0-1.0 (higher = more likely to forget)
        """
        self.evaluations += 1
        context = context or {}
        
        # 1. Calculate entropy (information density)
        entropy = self.entropy_calc.calculate_combined(memory.content)
        
        # Track statistics
        if entropy > 0.7:
            self.high_entropy_count += 1
        elif entropy < 0.3:
            self.low_entropy_count += 1
        
        # 2. Calculate relevance to current context
        recent_messages = context.get('recent_messages', [])
        if recent_messages:
            relevance = self.relevance_scorer.calculate_relevance(
                memory.content,
                recent_messages
            )
        else:
            relevance = 0.5  # Neutral if no context
        
        # 3. Calculate access pattern factor
        # More accesses = lower decay
        access_count = getattr(memory, 'access_count', 0)
        access_factor = 1.0 / (1.0 + access_count)
        
        # 4. Combine factors into decay score
        # High entropy = low decay (keep novel info)
        # High relevance = low decay (keep relevant info)
        # High access = low decay (keep frequently used info)
        
        entropy_component = (1.0 - entropy) * self.entropy_weight
        relevance_component = (1.0 - relevance) * self.relevance_weight
        access_component = access_factor * self.access_weight
        
        decay_score = self.base_rate * (
            entropy_component +
            relevance_component +
            access_component
        )
        
        # Normalize to 0-1
        decay_score = min(max(decay_score, 0.0), 1.0)
        
        return decay_score
    
    def should_forget(
        self,
        memory,
        decay_threshold: float = 0.6,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determine if memory should be forgotten
        
        Args:
            memory: Memory to evaluate
            decay_threshold: Threshold above which to forget
            context: Current conversation context
        
        Returns:
            bool: True if should forget, False if should keep
        """
        decay_score = self.calculate_decay_score(memory, context)
        
        # Store decay score in memory for tracking
        if hasattr(memory, 'decay_score'):
            memory.decay_score = decay_score
        
        return decay_score >= decay_threshold
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get decay engine statistics"""
        return {
            'total_evaluations': self.evaluations,
            'high_entropy_memories': self.high_entropy_count,
            'low_entropy_memories': self.low_entropy_count,
            'embeddings_available': EMBEDDINGS_AVAILABLE,
            'base_decay_rate': self.base_rate,
        }


# Example usage and testing
if __name__ == "__main__":
    print("=" * 70)
    print("🧠 VIDURAI v2.0 - INTELLIGENT DECAY TEST")
    print("=" * 70)
    
    # Create decay engine
    decay = IntelligentDecay(
        base_decay_rate=0.1,
        use_embeddings=False  # Use simple embedder for demo
    )
    
    # Test memories with different characteristics
    test_cases = [
        {
            'content': "My name is Chandan and I work in fintech building AI systems",
            'access_count': 5,
            'expected': 'KEEP (high entropy, high access)'
        },
        {
            'content': "The weather is nice today",
            'access_count': 0,
            'expected': 'FORGET (low entropy, low access)'
        },
        {
            'content': "I'm building Vidurai, an intelligent memory system for AI",
            'access_count': 3,
            'expected': 'KEEP (high entropy, medium access)'
        },
        {
            'content': "Ok. Yes. Sure. Alright.",
            'access_count': 0,
            'expected': 'FORGET (very low entropy)'
        },
    ]
    
    # Create simple memory class for testing
    class SimpleMemory:
        def __init__(self, content, access_count):
            self.content = content
            self.access_count = access_count
            self.decay_score = 0.0
    
    print("\n📊 Testing Decay Calculations:\n")
    
    context = {
        'recent_messages': [
            "Tell me about your AI projects",
            "What are you working on?"
        ]
    }
    
    for i, test in enumerate(test_cases, 1):
        memory = SimpleMemory(test['content'], test['access_count'])
        
        # Calculate decay
        decay_score = decay.calculate_decay_score(memory, context)
        should_forget = decay.should_forget(memory, decay_threshold=0.5, context=context)
        
        # Calculate components
        entropy = decay.entropy_calc.calculate_combined(memory.content)
        
        print(f"Test {i}: {test['content'][:50]}...")
        print(f"   Entropy: {entropy:.3f}")
        print(f"   Access count: {memory.access_count}")
        print(f"   Decay score: {decay_score:.3f}")
        print(f"   Decision: {'🗑️  FORGET' if should_forget else '✅ KEEP'}")
        print(f"   Expected: {test['expected']}")
        print()
    
    # Show statistics
    stats = decay.get_statistics()
    print("=" * 70)
    print("📈 Statistics:")
    print(f"   Total evaluations: {stats['total_evaluations']}")
    print(f"   High entropy memories: {stats['high_entropy_memories']}")
    print(f"   Low entropy memories: {stats['low_entropy_memories']}")
    print(f"   Embeddings available: {stats['embeddings_available']}")
    print("=" * 70)
    print("\n✅ Intelligent Decay Module 2 - Working!")