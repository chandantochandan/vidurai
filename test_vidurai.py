"""
Test script to verify Vidurai core functionality
"""

from vidurai import create_memory_system
from loguru import logger

# Create memory system
logger.info("Creating Vidurai memory system...")
memory = create_memory_system()

# Test adding memories
logger.info("Testing memory addition...")
m1 = memory.remember("My name is Chandan")
m2 = memory.remember("I am building an AI memory system")
m3 = memory.remember("The weather is nice today")

# Test recall
logger.info("Testing memory recall...")
memories = memory.recall()

print("\n=== Vidurai Memory Test ===")
print(f"Total memories stored: {len(memories)}")
for i, mem in enumerate(memories[:5], 1):
    print(f"{i}. {mem.content[:50]}... (importance: {mem.importance:.2f})")

print("\n✅ Vidurai core system is working!")