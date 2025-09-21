import asyncio
import os
import sys
import numpy as np

# Add the project directory to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.cli_ai.agents import memory_system as memory
from src.cli_ai.utils import database as db

async def test_faiss_recall():
    print("--- Initializing Database ---")
    db.initialize_db() # This will also initialize the FAISS index

    print("\n--- Saving Memories ---")
    # Save some diverse memories
    await asyncio.to_thread(memory.save_memory, "The user's favorite color is blue.", {"type": "declarative"})
    await asyncio.to_thread(memory.save_memory, "The capital of France is Paris.", {"type": "declarative"})
    await asyncio.to_thread(memory.save_memory, "I enjoy hiking in the mountains.", {"type": "declarative"})
    await asyncio.to_thread(memory.save_memory, "The user's preferred programming language is Python.", {"type": "declarative"})
    await asyncio.to_thread(memory.save_memory, "The quick brown fox jumps over the lazy dog.", {"type": "declarative"})
    await asyncio.to_thread(memory.save_memory, "My favorite food is pizza.", {"type": "declarative"})
    await asyncio.to_thread(memory.save_memory, "The user is learning about AI agents.", {"type": "declarative"})
    await asyncio.to_thread(memory.save_memory, "The user's cat's name is Whiskers.", {"type": "declarative"})
    await asyncio.to_thread(memory.save_memory, "I like to read science fiction novels.", {"type": "declarative"})
    await asyncio.to_thread(memory.save_memory, "The user is interested in vector databases.", {"type": "declarative"}) # This is the 10th memory

    # This memory is semantically related to an earlier one but is not the most recent
    await asyncio.to_thread(memory.save_memory, "The user loves to explore new hiking trails.", {"type": "declarative"}) # This is the 11th memory

    print("\n--- Recalling Memories ---")

    # Query that should semantically match an older memory ("I enjoy hiking in the mountains.")
    query_hiking = "Tell me about outdoor activities the user enjoys."
    print(f"Query: '{query_hiking}'")
    recalled_hiking = memory.recall_memories(query_hiking, limit=3)
    print("Recalled memories for hiking query:")
    for mem in recalled_hiking:
        print(f"- {mem['content']}")

    print("\n--- Recalling Memories (another query) ---")
    # Query that should semantically match a more recent memory ("The user is interested in vector databases.")
    query_ai = "What is the user studying in AI?"
    print(f"Query: '{query_ai}'")
    recalled_ai = memory.recall_memories(query_ai, limit=3)
    print("Recalled memories for AI query:")
    for mem in recalled_ai:
        print(f"- {mem['content']}")

    print("\n--- Test Complete ---")

if __name__ == "__main__":
    # Clean up previous database for a fresh test
    if os.path.exists(db.DB_FILE):
        os.remove(db.DB_FILE)
        print(f"Removed existing database: {db.DB_FILE}")
    
    asyncio.run(test_faiss_recall())