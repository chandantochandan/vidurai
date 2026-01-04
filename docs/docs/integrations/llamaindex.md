---
sidebar_position: 2
---

# LlamaIndex Integration

Integrate Vidurai with LlamaIndex for enhanced memory-aware AI applications.

## Installation

```bash
pip install vidurai llama-index
```

## Basic Integration

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from vidurai import Vidurai

# Initialize Vidurai
memory = Vidurai()

# Load documents
documents = SimpleDirectoryReader('data').load_data()
index = VectorStoreIndex.from_documents(documents)

# Query with memory context
query = "What are the main features?"

# Get relevant context from Vidurai
context = memory.recall(query, limit=5)
context_str = "\n".join([m['content'] for m in context])

# Query with enhanced context
response = index.as_query_engine().query(
    f"Context: {context_str}\n\nQuestion: {query}"
)

# Store the interaction
memory.store(f"Q: {query}\nA: {response}", importance=0.7)
```

## Chat Engine Integration

```python
from llama_index.core.chat_engine import SimpleChatEngine
from vidurai import Vidurai

class MemoryAwareChatEngine:
    def __init__(self, index):
        self.engine = index.as_chat_engine()
        self.memory = Vidurai()

    def chat(self, message: str) -> str:
        # Get memory context
        context = self.memory.recall(message, limit=3)

        # Add context to message
        if context:
            context_str = "Previous relevant context:\n"
            context_str += "\n".join([m['content'] for m in context])
            enhanced_message = f"{context_str}\n\nCurrent message: {message}"
        else:
            enhanced_message = message

        # Get response
        response = self.engine.chat(enhanced_message)

        # Store interaction
        self.memory.store(
            f"User: {message}\nAssistant: {response}",
            importance=0.7
        )

        return response

# Usage
documents = SimpleDirectoryReader('data').load_data()
index = VectorStoreIndex.from_documents(documents)
chat_engine = MemoryAwareChatEngine(index)

response = chat_engine.chat("Tell me about the architecture")
```

## Agent Integration

```python
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from vidurai import Vidurai

memory = Vidurai()

def remember(text: str) -> str:
    """Store information in long-term memory"""
    memory.store(text, importance=0.8)
    return f"Stored: {text}"

def recall_memory(query: str) -> str:
    """Retrieve relevant information from memory"""
    results = memory.recall(query, limit=5)
    if not results:
        return "No relevant memories found"
    return "\n".join([r['content'] for r in results])

# Create tools
tools = [
    FunctionTool.from_defaults(fn=remember),
    FunctionTool.from_defaults(fn=recall_memory),
]

# Create agent
agent = ReActAgent.from_tools(tools, verbose=True)

# Use agent
response = agent.chat("Remember that the user prefers Python 3.11")
response = agent.chat("What Python version does the user prefer?")
```

## Response Synthesis with Memory

```python
from llama_index.core.response_synthesizers import get_response_synthesizer
from vidurai import Vidurai

memory = Vidurai()

def synthesize_with_memory(query: str, nodes) -> str:
    # Get memory context
    context = memory.recall(query, limit=3)

    # Prepare synthesizer
    synthesizer = get_response_synthesizer(
        response_mode="tree_summarize"
    )

    # Add memory context to nodes
    if context:
        from llama_index.core.schema import TextNode
        context_nodes = [
            TextNode(text=m['content'])
            for m in context
        ]
        nodes = context_nodes + nodes

    # Synthesize response
    response = synthesizer.synthesize(query, nodes)

    # Store result
    memory.store(f"Q: {query}\nA: {response}", importance=0.7)

    return response
```

## Best Practices

1. **Store query-response pairs**
   ```python
   memory.store(f"Q: {query}\nA: {response}", importance=0.7)
   ```

2. **Use semantic recall**
   ```python
   # Better than storing full conversation
   context = memory.recall(current_query, limit=5)
   ```

3. **Importance-based storage**
   ```python
   # Critical information
   memory.store(user_preference, importance=0.9)

   # Casual conversation
   memory.store(small_talk, importance=0.3)
   ```

4. **Periodic cleanup**
   ```python
   # Clear low-importance memories periodically
   memory.clear_below_threshold(0.3)
   ```

## Example: Document QA with Memory

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from vidurai import Vidurai

class MemoryAwareQA:
    def __init__(self, data_dir: str):
        self.memory = Vidurai()
        documents = SimpleDirectoryReader(data_dir).load_data()
        self.index = VectorStoreIndex.from_documents(documents)
        self.query_engine = self.index.as_query_engine()

    def ask(self, question: str) -> dict:
        # Check memory first
        memory_results = self.memory.recall(question, limit=3)

        if memory_results and memory_results[0]['importance'] > 0.8:
            # Use cached answer for high-confidence memories
            return {
                'answer': memory_results[0]['content'],
                'source': 'memory',
                'confidence': memory_results[0]['importance']
            }

        # Query documents
        response = self.query_engine.query(question)

        # Store for future use
        self.memory.store(
            f"Q: {question}\nA: {response}",
            importance=0.7
        )

        return {
            'answer': str(response),
            'source': 'documents',
            'confidence': 0.7
        }

# Usage
qa = MemoryAwareQA('docs/')
result = qa.ask("What is the three-kosha architecture?")
print(f"Answer: {result['answer']}")
print(f"Source: {result['source']}")
```

See [LangChain Integration](./langchain.md) for comparison and [Custom Integration](./custom-integration.md) for building your own.
