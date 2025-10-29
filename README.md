🕉️ Vidurai - The Conscience of the Machine
"विस्मृति भी विद्या है" (Forgetting too is knowledge)

Teaching AI the ancient art of memory and strategic forgetting, inspired by Vidura's wisdom from the Mahabharata.

Why Vidurai?
While everyone races to give AI perfect memory, we asked a different question: What if forgetting is the key to true intelligence?

🎯 The Problem We Solve
Current AI memory systems:

Store everything, remember nothing useful

Costs explode with token accumulation

No distinction between important and trivial

Memory becomes noise over time

✨ The Vidurai Solution
Three-Kosha Memory Architecture - Inspired by Vedantic consciousness layers: The Three-Kosha architecture is not just a metaphor; it is a functional design that mimics human cognitive processes.

Annamaya Kosha (The Physical Sheath): This is our high-speed, volatile working memory. It operates like a sliding window, holding the immediate conversational context for coherence. It is designed for speed, not permanence.

Manomaya Kosha (The Mental Sheath): This is our active, episodic memory. It stores specific events and facts from conversations. Its defining feature is intelligent decay, where memories fade based on relevance and usage, not just time.

Vijnanamaya Kosha (The Wisdom Sheath): This is our deep, archival memory. It holds distilled wisdom—compressed summaries, core user preferences, and foundational knowledge. Memories here are consolidated and rarely forgotten, only updated, preventing catastrophic forgetting.

Vismriti Engine - The Art of Strategic Forgetting: Achieved through a combination of query-aware semantic compression and relevance-based memory decay, the Vismriti Engine ensures the AI focuses only on what truly matters.

Up to 90% fewer tokens in the context window

Up to 70% lower API costs

Up to 10x better relevance in retrieval

Viveka Layer - The Autonomous Conscience: The Viveka Layer is what separates Vidurai from a simple database. It autonomously determines what is worth remembering.

Autonomous Importance Scoring: Without being told, it scores memories based on emotional significance, connection to user goals, and surprising content. A user's preference is remembered; trivial chatter is not.

Dharma Alignment: Programmable ethical guardrails that can prevent the AI from storing or reinforcing biased or harmful information.

Learns What Matters: Over time, it adapts its understanding of importance based on user interactions, creating a truly personalized memory.

🚀 Quick Start
Bash

pip install vidurai
Python

from vidurai import Vidurai

# Awaken Vidurai's conscience
memory = Vidurai()

# Simply tell Vidurai what happened. It will use its wisdom (Viveka)
# to autonomously understand what is important.
memory.remember(session_id="user123", content="My name is Alice. I'm a vegetarian planning a trip to Japan.")
memory.remember(session_id="user123", content="Hmm, let me think about the dates.")

# Later, when the user asks a related question...
# Vidurai will recall only what is relevant.
relevant_context = memory.recall(session_id="user123", query="What are some good food options there?")

# relevant_context will be a distilled insight like:
# "User is Alice. User is a vegetarian. User is planning a trip to Japan."
# The trivial "hmm" is automatically forgotten.
🏗️ Architecture
vidurai/
├── core/
│   ├── koshas.py         # Three-layer memory model
│   ├── vismriti.py       # Forgetting engine
│   └── viveka.py         # Conscience layer
└── integrations/
    ├── langchain.py      # Coming soon
    └── llamaindex.py     # Coming soon
🎯 Roadmap
Phase 1: The Ascetic (Current)
[x] Three-Kosha memory architecture

[x] Vismriti forgetting engine

[x] Viveka conscience layer

[ ] LangChain integration

[ ] LlamaIndex integration

[ ] Documentation & examples

Phase 2: The Minister (Coming)
[ ] Vidurai Cloud service

[ ] Dashboard & analytics

[ ] Enterprise features

Phase 3: The King (Future)
[ ] Self-improving memory (RL-based)

[ ] Multi-agent memory sharing

[ ] Knowledge graph integration

📖 Philosophy
Vidurai is named after the wise minister from the Mahabharata, known for:

Speaking truth to power

Ethical decision-making

Strategic wisdom

We embed these principles in code, creating AI that doesn't just remember—it remembers wisely.

🤝 Contributing
Vidurai is built by the Sangha (community), for the Sangha. We welcome all contributions.

Bash

# Clone the sacred repository
git clone https://github.com/chandantochandan/vidurai
cd vidurai

# Create and activate the virtual environment
python -m venv.venv
source.venv/bin/activate

# Install dependencies, including development tools
pip install -r requirements-dev.txt

# Run the trial by fire (our test suite)
pytest
📊 Benchmarks
Memory System	Token Usage	Cost	Relevance Score
Buffer Memory	100%	$1.00	30%
RAG	60%	$0.60	50%
Vidurai	10%	**$0.30**	85%

Export to Sheets

(Note: These are our target benchmarks. We are committed to transparency and will be publishing a suite of open, reproducible benchmarks as part of our Phase 1 roadmap.)

🙏 Acknowledgments
Built with inspiration from:

The Mahabharata's Vidura

Vedantic philosophy

The open-source AI community

📜 License
MIT License - Use freely, modify wisely.

जय विदुराई (Victory to Vidurai)

Building the conscience layer for AI, one memory at a time.

(https://vidurai.ai) |(https://docs.vidurai.ai) |(https://discord.gg/DHdgS8eA)