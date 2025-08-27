
import json
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from ..utils import database as db

MODEL = SentenceTransformer('all-MiniLM-L6-v2')

def _generate_embedding(text: str) -> bytes:
    """Generates a vector embedding for a given text."""
    embedding = MODEL.encode(text)
    return embedding.tobytes()

def save_memory(content: str, metadata: Optional[Dict[str, Any]] = None):
    """Saves a memory to the system."""
    embedding = _generate_embedding(content)
    db.save_memory(content, embedding, metadata)

def recall_memories(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Recalls memories from the system based on a query."""
    query_embedding = _generate_embedding(query)
    memories = db.recall_memories(query_embedding, limit)
    # In a real implementation, the database would handle the similarity search.
    # For now, we're just returning the most recent memories.
    return memories

if __name__ == "__main__":
    db.initialize_db()
    save_memory("The user's name is John Doe.", {"type": "declarative"})
    save_memory("The user likes to play chess.", {"type": "declarative"})
    recalled_memories = recall_memories("What is the user's name?")
    print(recalled_memories)
