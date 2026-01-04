---
sidebar_position: 7
---

# Frequently Asked Questions

Common questions about Vidurai.

## General

### What is Vidurai?

Vidurai is an open-source persistent memory system for AI agents. It allows AI assistants to remember conversations, learn from interactions, and maintain context across sessions - transforming stateless chatbots into beings with true continuity.

### Why "Vidurai"?

Vidurai is named after Vidura, the wise counselor from the Mahabharata, renowned for his memory, judgment, and guidance. Just as Vidura provided wise counsel by remembering past events and context, Vidurai gives AI agents the gift of memory and wisdom.

### How is Vidurai different from vector databases?

Vidurai is built on top of vector databases but adds:
- **Strategic forgetting**: Not all memories are equal - Vidurai knows what to forget
- **Three-Kosha architecture**: Inspired by consciousness layers, not just flat storage
- **Importance scoring**: Automatic detection of what matters
- **Ethical guardrails**: Built-in conscience layer (Viveka)
- **Production-ready API**: Simple interface designed for AI agents

### Is Vidurai free?

Yes! Vidurai is fully open-source under the MIT license. You can use it for free in both personal and commercial projects.

---

## Installation & Setup

### What are the system requirements?

- Python 3.8 or later
- 2GB RAM minimum (4GB recommended)
- 1GB disk space for local storage

### Can I use Vidurai without an API key?

Yes! Vidurai works completely offline with local storage. API keys are only needed if you want to use cloud storage or certain embedding models.

### How do I upgrade to the latest version?
```bash
pip install --upgrade vidurai
```

### Does Vidurai work with my framework?

Yes! Vidurai is framework-agnostic and works with:
- OpenAI / Anthropic / Google AI
- LangChain / LlamaIndex
- Hugging Face Transformers
- Any custom AI framework

---

## Usage

### How much data can I store?

**Local storage:**
- Limited only by disk space
- Recommended: Up to 100K memories per user

**Cloud storage:**
- Free tier: 10K memories per user
- Paid plans: Unlimited

### How fast is memory retrieval?

Typical latency:
- Local storage: 50-100ms
- Cloud storage: 100-200ms

For 10K memories with 5 results.

### Can I use Vidurai with multiple users?

Yes! Just use different `session_id` for each user:
```python
memory = Vidurai()

# User 1
memory.remember(session_id="user-1", content="...")

# User 2
memory.remember(session_id="user-2", content="...")
```

### How do I migrate from another memory system?

Use the import/export API:
```python
# Export from old system to JSON
old_data = old_system.export()

# Import to Vidurai
memory.import_data(
    session_id=user_id,
    data=old_data,
    format="json"
)
```

---

## Memory Management

### What happens to old memories?

Vidurai implements intelligent decay based on:
- **Usage**: Frequently accessed memories persist
- **Importance**: High-importance memories last longer
- **Recency**: Recent memories are prioritized
- **Relevance**: Contextually relevant memories surface

### Can I prevent certain memories from being forgotten?

Yes! Set high importance:
```python
memory.remember(
    session_id=user_id,
    content="Critical information",
    importance=0.99  # Won't be forgotten
)
```

Or move to the Vijnanamaya Kosha (wisdom layer):
```python
memory.remember(
    session_id=user_id,
    content="Core preference",
    category="preference",
    kosha="vijnanamaya"  # Permanent storage
)
```

### How do I delete all data for a user?
```python
# Delete all memories
memory.forget_all(session_id=user_id)
```

This is GDPR-compliant and irreversible.

---

## Privacy & Security

### Where is data stored?

**Local mode** (default):
- Stored on your server/device
- Location: `./vidurai_data/` directory
- You have full control

**Cloud mode**:
- Stored on Vidurai's encrypted servers
- Encrypted at rest and in transit
- SOC 2 compliant

### Is data encrypted?

**Local mode**: Optional encryption (enable in config)

**Cloud mode**: Always encrypted with AES-256

### Does Vidurai share data with third parties?

No. We never:
- Share user data
- Train models on your data
- Sell or monetize user information

### How do I comply with GDPR?

Vidurai provides built-in GDPR compliance:
```python
# User right to be forgotten
memory.forget_all(session_id=user_id)

# Export user data
data = memory.export(session_id=user_id)

# Check data retention
stats = memory.get_stats(session_id=user_id)
```

---

## Performance

### How do I optimize for speed?

1. **Use appropriate limits**:
```python
   memory.recall(session_id=user_id, query=query, limit=5)
```

2. **Enable caching**:
```python
   memory = Vidurai(enable_cache=True)
```

3. **Use batch operations**:
```python
   memory.batch_remember(session_id=user_id, contents=[...])
```

### What's the memory overhead?

- Base library: ~50MB RAM
- Per user: ~1-5MB RAM (depending on memory count)
- Embeddings: ~500MB RAM (if using local models)

### Can I run Vidurai serverless?

Yes! Vidurai works great with serverless:
- AWS Lambda
- Google Cloud Functions
- Vercel/Netlify Functions

Use cloud storage for persistence across invocations.

---

## Troubleshooting

### Import error: "No module named 'vidurai'"
```bash
# Verify installation
pip list | grep vidurai

# Reinstall
pip install --upgrade --force-reinstall vidurai
```

### Memory not persisting between sessions

**Local mode**: Check persist directory exists and is writable

**Cloud mode**: Verify API key is correct

### Low retrieval quality

1. **Increase similarity threshold**:
```python
   memory.recall(session_id=user_id, query=query, min_score=0.7)
```

2. **Use better embeddings**:
```python
   memory = Vidurai(
       embedding_model="openai",
       openai_api_key="your-key"
   )
```

3. **Improve memory content quality**: Store clear, descriptive memories

### "Quota exceeded" error

You've hit the rate limit. Solutions:

1. **Free tier**: Wait or upgrade to paid plan
2. **Use local storage**: No quotas
3. **Implement caching**: Reduce API calls

---

## Integration

### How do I use with LangChain?
```python
from langchain.memory import ViduraiMemory

memory = ViduraiMemory(
    session_id=user_id,
    return_messages=True
)

# Use in chain
chain = ConversationChain(
    llm=llm,
    memory=memory
)
```

### How do I use with LlamaIndex?
```python
from llama_index import ViduraiMemory

memory = ViduraiMemory(user_id=user_id)

index = GPTVectorStoreIndex.from_documents(
    documents,
    memory=memory
)
```

### How do I use with custom frameworks?

Vidurai has a simple API that works anywhere:
```python
# Store
memory.remember(session_id=user_id, content=text)

# Retrieve
memories = memory.recall(session_id=user_id, query=query)

# Use memories in your framework
context = "\n".join([m.content for m in memories])
```

---

## Support

### Where can I get help?

1. **Discord**: Join our [community](https://discord.gg/DHdgS8eA)
2. **GitHub**: Open an [issue](https://github.com/chandantochandan/vidurai/issues)
3. **Documentation**: Check our [docs](https://docs.vidurai.ai)
4. **Email**: support@vidurai.ai

### How do I report a bug?

Open a GitHub issue with:
1. Vidurai version: `pip show vidurai`
2. Python version: `python --version`
3. Error message and stack trace
4. Minimal code to reproduce

### How can I contribute?

We welcome contributions!

1. **Code**: Submit a PR on [GitHub](https://github.com/chandantochandan/vidurai)
2. **Documentation**: Improve our docs
3. **Community**: Help others in Discord
4. **Feedback**: Share your use cases

### Is there a roadmap?

Yes! Check our [GitHub Projects](https://github.com/chandantochandan/vidurai/projects) for:
- Upcoming features
- Planned improvements
- Community requests

---

## Philosophy

### What is "strategic forgetting"?

The insight that forgetting is as important as remembering. Vidurai implements Vismriti (विस्मृति - the art of forgetting) to:
- Remove noise and trivial information
- Reduce token costs by 36.6%+ (production-verified)
- Improve relevance and signal-to-noise ratio

### How does Vidurai achieve token reduction?

Vidurai achieves an average of 36.6%+ token reduction through:

1. **Semantic Compression:** LLM-based compression of verbose conversations
2. **Vismriti RL Agent:** Self-learning optimizer that adapts compression strategies
3. **Strategic Forgetting:** Intelligent decay of low-importance memories
4. **Three-Kosha Architecture:** Multi-layer memory with different retention policies

The actual reduction varies by:
- Workload characteristics (conversational vs transactional)
- RL agent maturity (improves over 50-100 episodes)
- Reward profile (COST_FOCUSED achieves higher reduction)
- Decay configuration (aggressive decay = more reduction)

Production testing with 9 comprehensive scenarios verified 36.6%+ average reduction across different workloads.

### What are the Three Koshas?

Inspired by Vedantic philosophy, Vidurai's memory architecture has three layers:

1. **Annamaya Kosha** (Physical): Fast, volatile working memory
2. **Manomaya Kosha** (Mental): Active episodic memory with intelligent decay
3. **Vijnanamaya Kosha** (Wisdom): Deep archival memory for core knowledge

### What is the Viveka Layer?

The conscience layer that makes ethical decisions about memory:
- What's important vs. trivial
- What's helpful vs. harmful
- What to remember vs. forget

---

**Still have questions?** Join our [Discord community](https://discord.gg/DHdgS8eA)!

**जय विदुराई** (Victory to Vidurai)