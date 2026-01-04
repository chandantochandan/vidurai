---
sidebar_position: 3
---

# Quick Start

Get started with Vidurai in 5 minutes - choose the path that fits your workflow.

## 🚀 Choose Your Path

### **Option A: VS Code Extension** (Fastest)
Perfect if you want a ready-to-use solution with zero configuration:

1. Install from [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=vidurai.vidurai)
2. Click "Capture Context" in the sidebar
3. One-click export to any AI coding assistant

**Done!** No coding required. [Learn more →](https://vidurai.ai)

---

### **Option B: Vidurai SDK** (This Guide)
Perfect for custom integrations, Jupyter notebooks, or Python workflows.

Continue reading below for SDK setup and usage.

---

## Step 1: Install & Initialize
```python
from vidurai import Vidurai

# Create a Vidurai instance
memory = Vidurai(
    api_key="your-api-key",  # Optional for local use
    user_id="user-123"
)
```

## Step 2: Store Memories
```python
# Store a user preference
memory.remember(
    session_id="user-123",
    content="User prefers morning meetings and is vegetarian",
    category="preference"
)

# Store a conversation
memory.remember(
    session_id="user-123",
    content="User is planning a trip to Japan in March",
    category="conversation"
)

# Trivial information (will be automatically deprioritized)
memory.remember(
    session_id="user-123",
    content="Hmm, let me think about that",
    category="conversation"
)
```

## Step 3: Retrieve Relevant Memories
```python
# Query for relevant context
memories = memory.recall(
    session_id="user-123",
    query="What restaurants should I visit?",
    limit=5
)

# Print retrieved memories
for m in memories:
    print(f"Relevance: {m.score:.2f} - {m.content}")
```

**Output:**
```
Relevance: 0.92 - User is planning a trip to Japan in March
Relevance: 0.87 - User prefers morning meetings and is vegetarian
# Note: "Hmm, let me think" is automatically filtered out
```

## Step 4: Use with Your AI Agent

### Example with OpenAI
```python
from vidurai import Vidurai
from openai import OpenAI

class MemoryBot:
    def __init__(self):
        self.vidurai = Vidurai(user_id="user-123")
        self.openai = OpenAI()
    
    def chat(self, user_message: str) -> str:
        # Retrieve relevant memories
        memories = self.vidurai.recall(
            session_id="user-123",
            query=user_message,
            limit=5
        )
        
        # Build context from memories
        context = "\n".join([m.content for m in memories])
        
        # Create system prompt with context
        system_prompt = f"""You are a wise assistant with memory.
        
Here's what you remember about the user:
{context}

Use this context to provide personalized responses."""
        
        # Get AI response
        response = self.openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        
        # Store this interaction
        self.vidurai.remember(
            session_id="user-123",
            content=f"User: {user_message}\nAssistant: {response.choices[0].message.content}",
            category="conversation"
        )
        
        return response.choices[0].message.content

# Use the bot
bot = MemoryBot()
response = bot.chat("What vegetarian restaurants should I try in Tokyo?")
print(response)
```

## Step 5: Manage Memory

### Update Memories
```python
# Update an existing memory
memory.update(
    memory_id="mem_123",
    content="User is now vegan (upgraded from vegetarian)"
)
```

### Delete Memories
```python
# Delete specific memory
memory.forget(memory_id="mem_123")

# Delete all memories for a user
memory.forget_all(session_id="user-123")
```

### Search Memories
```python
# Search by category
preferences = memory.search(
    session_id="user-123",
    category="preference"
)

# Search by date range
from datetime import datetime, timedelta

recent = memory.search(
    session_id="user-123",
    after=datetime.now() - timedelta(days=7)
)
```

## Complete Example

Here's a complete chatbot with Vidurai memory:
```python
from vidurai import Vidurai
from openai import OpenAI

class WiseAssistant:
    """An AI assistant with persistent memory"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.vidurai = Vidurai(user_id=user_id)
        self.openai = OpenAI()
    
    def chat(self, message: str) -> str:
        """Process a user message with memory"""
        
        # Retrieve relevant context
        memories = self.vidurai.recall(
            session_id=self.user_id,
            query=message,
            limit=5
        )
        
        # Build context
        context = "\n".join([
            f"- {m.content}" 
            for m in memories
        ])
        
        # Generate response
        response = self.openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a wise assistant. Context:\n{context}"
                },
                {"role": "user", "content": message}
            ]
        )
        
        assistant_reply = response.choices[0].message.content
        
        # Store the interaction
        self.vidurai.remember(
            session_id=self.user_id,
            content=f"Q: {message}\nA: {assistant_reply}",
            category="conversation"
        )
        
        return assistant_reply
    
    def summarize_memories(self) -> str:
        """Get a summary of what the assistant knows"""
        
        all_memories = self.vidurai.search(
            session_id=self.user_id,
            limit=100
        )
        
        return f"I remember {len(all_memories)} things about you."

# Usage
assistant = WiseAssistant(user_id="alice")

# First conversation
print(assistant.chat("My name is Alice and I love hiking"))
# Response: "Nice to meet you, Alice! Hiking is wonderful..."

# Later conversation (even in a new session)
print(assistant.chat("What outdoor activities should I try?"))
# Response: "Given your love for hiking, you might enjoy..."

# Check memory
print(assistant.summarize_memories())
# Output: "I remember 2 things about you."
```

## Next Steps

- [Configuration](./configuration) - Customize memory behavior
- [Best Practices](./best-practices) - Build production-ready systems
- [API Reference](./api-reference) - Full API documentation

## Need Help?

- Join our [Discord community](https://discord.gg/DHdgS8eA)
- Check [GitHub Issues](https://github.com/chandantochandan/vidurai/issues)
- Read the [FAQ](./faq)

---

**जय विदुराई** (Victory to Vidurai)