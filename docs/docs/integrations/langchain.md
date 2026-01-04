---
sidebar_position: 1
---

# LangChain Integration

🔗 Vidurai seamlessly integrates with [LangChain](https://langchain.com), providing intelligent memory management for your LangChain applications.

## Overview

The LangChain integration provides:

- **ViduraiMemory** - Drop-in replacement for ConversationBufferMemory
- **Three-Layer Architecture** - Working, Episodic, and Semantic memory
- **Strategic Forgetting** - Automatic removal of less important context
- **Cost Optimization** - 30-50% token reduction (varies by workload and RL agent maturity)

## Installation
```bash
pip install vidurai[langchain]
```

This installs Vidurai with LangChain support.

## Quick Start

### Basic Usage
```python
from langchain.llms import OpenAI
from vidurai.integrations.langchain import ViduraiConversationChain

# Create LLM
llm = OpenAI(temperature=0.7, openai_api_key="your-key")

# Create conversation chain with Vidurai memory
chain = ViduraiConversationChain.create(llm)

# Have a conversation
response = chain.predict(input="Hi, my name is Alice")
print(response)

response = chain.predict(input="What's my name?")
print(response)  # Remembers: "Your name is Alice"
```

### Using ViduraiMemory Directly
```python
from langchain.llms import OpenAI
from langchain.chains import ConversationChain
from vidurai.integrations.langchain import ViduraiMemory

# Create Vidurai memory
memory = ViduraiMemory()

# Create conversation chain
llm = OpenAI(temperature=0.7)
chain = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)

# Use the chain
chain.predict(input="I'm building an AI application")
chain.predict(input="It uses LangChain and Vidurai")
chain.predict(input="What am I building?")
```

## Use Cases

### Customer Support Chatbot
```python
from vidurai.integrations.langchain import ViduraiConversationChain
from langchain.llms import OpenAI

llm = OpenAI(temperature=0.7, openai_api_key="your-key")
chatbot = ViduraiConversationChain.create(llm)

# Long conversation with automatic forgetting
chatbot.predict(input="Hi, my name is Sarah")
chatbot.predict(input="I have an issue with order #12345")
chatbot.predict(input="It was supposed to arrive yesterday")
chatbot.predict(input="The weather is nice today")  # Low importance
chatbot.predict(input="Can you help track my order?")

# Vidurai keeps: name, order issue
# Vidurai forgets: weather small talk
```

### Multi-User Application
```python
from vidurai.integrations.langchain import ViduraiMemory

class ChatService:
    def __init__(self):
        self.user_memories = {}
    
    def get_memory(self, user_id: str):
        if user_id not in self.user_memories:
            self.user_memories[user_id] = ViduraiMemory()
        return self.user_memories[user_id]
    
    def chat(self, user_id: str, message: str):
        memory = self.get_memory(user_id)
        # Each user has isolated memory
        memory.save_context(
            {"input": message},
            {"output": "AI response"}
        )

service = ChatService()
service.chat("user_1", "I love Python")
service.chat("user_2", "I prefer JavaScript")
# Memories are completely isolated
```

## Configuration

### Memory Capacity
```python
from vidurai import create_memory_system
from vidurai.integrations.langchain import ViduraiMemory

# Custom memory configuration
memory = ViduraiMemory()
memory.vidurai_memory = create_memory_system(
    working_capacity=15,      # Keep 15 recent items
    episodic_capacity=500,    # Store up to 500 items
    aggressive_forgetting=True  # More aggressive cleanup
)
```

### Importance Scoring

Vidurai automatically assigns importance scores:
- **Human messages**: 0.7 (high importance)
- **AI responses**: 0.6 (medium-high importance)
- **System messages**: 0.5 (medium importance)

Less important memories are forgotten over time.

## API Reference

### ViduraiMemory

**Class**: `vidurai.integrations.langchain.ViduraiMemory`

Drop-in replacement for LangChain's ConversationBufferMemory with intelligent forgetting.

**Attributes:**
- `memory_key` (str): Key for storing chat history (default: "chat_history")
- `input_key` (str): Key for input messages (default: "input")
- `output_key` (str): Key for output messages (default: "output")
- `vidurai_memory`: Underlying Vidurai memory system

**Methods:**

#### `load_memory_variables(inputs: Dict) -> Dict`
Load relevant memories for the current context.

#### `save_context(inputs: Dict, outputs: Dict) -> None`
Save conversation context to memory with automatic importance scoring.

#### `clear() -> None`
Clear all memories and reset the system.

### ViduraiConversationChain

**Class**: `vidurai.integrations.langchain.ViduraiConversationChain`

Helper class for creating conversation chains with Vidurai memory.

**Methods:**

#### `create(llm, verbose: bool = False) -> ConversationChain`
Create a LangChain ConversationChain with Vidurai memory.

**Parameters:**
- `llm`: LangChain LLM instance
- `verbose` (bool): Enable verbose output

**Returns:**
- ConversationChain with ViduraiMemory

## Performance & Cost Savings

### Token Reduction
```
Standard ConversationBufferMemory:
- 100 messages × 500 tokens = 50,000 tokens per request

ViduraiMemory:
- 10 messages × 500 tokens = 5,000 tokens per request

Result: 30-50% token reduction (varies by workload and RL agent maturity)
```

### Cost Savings Example
```
At $0.03 per 1K tokens (GPT-4):
- Standard: $1.50 per request
- Vidurai: $0.95 per request (36.6% reduction)
- Savings: $0.55 per request

For 10,000 users daily:
- Daily savings: $5,500
- Monthly savings: $165,000

Note: Actual savings vary by workload and RL agent maturity.
At scale with COST_FOCUSED profile, savings approach $16,182/day.
```

## Comparison with Standard Memory

| Feature | ConversationBufferMemory | ViduraiMemory |
|---------|-------------------------|---------------|
| Memory capacity | Unlimited (grows forever) | Intelligent limits |
| Token usage | High (all history) | Low (relevant only) |
| Forgetting | Never | Strategic |
| Cost | High for long conversations | 30-50% lower (36.6%+ average) |
| Response speed | Slower (more context) | Faster (less context) |
| Focus | May lose focus | Maintains relevance |

## Best Practices

### 1. Set Appropriate Capacity
```python
# For short conversations (customer support)
memory = create_memory_system(working_capacity=10)

# For long-running agents
memory = create_memory_system(working_capacity=20)

# For archival applications
memory = create_memory_system(episodic_capacity=10000)
```

### 2. Use Importance Scoring
```python
# High importance - never forget
memory.remember("User's email: alice@example.com", importance=0.95)

# Medium importance - keep for a while
memory.remember("User prefers email notifications", importance=0.7)

# Low importance - forget soon
memory.remember("User checked weather", importance=0.3)
```

### 3. Clear Memory When Appropriate
```python
# Start fresh conversation
memory.clear()

# Or reset for new user session
if session_ended:
    memory.clear()
```

## Troubleshooting

### Issue: Memories not being recalled

**Solution:** Check importance scores. Very low importance items are forgotten quickly.
```python
# Increase importance for critical information
memory.remember("Important data", importance=0.9)
```

### Issue: Too much being remembered

**Solution:** Enable aggressive forgetting or reduce capacity.
```python
memory = create_memory_system(
    working_capacity=5,  # Smaller capacity
    aggressive_forgetting=True
)
```

### Issue: Context not persisting across sessions

**Solution:** Use episodic memory for longer-term storage.
```python
memory = create_memory_system(
    episodic_capacity=1000  # More long-term storage
)
```

## Next Steps

- **GitHub**: [View source code](https://github.com/chandantochandan/vidurai)
- **PyPI**: [Install package](https://pypi.org/project/vidurai/)
- **Examples**: See code examples throughout this page

## Support

- **Discord**: [Join our community](https://discord.gg/DHdgS8eA)
- **GitHub**: [Report issues](https://github.com/chandantochandan/vidurai/issues)
- **Documentation**: [docs.vidurai.ai](https://docs.vidurai.ai)

---

**विस्मृति भी विद्या है** *(Forgetting too is knowledge)*