import json
import os
import time

MEMORY_FILE = "agent_memory.json"

def _load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    return []

def _save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=2)

def save_memory(fact: str) -> dict:
    """Saves a fact to the agent's long-term memory."""
    memory = _load_memory()
    memory.append({"fact": fact, "timestamp": time.time()})
    _save_memory(memory)
    return {"status": "success", "message": "Fact saved to memory."}

def recall_memory(query: str) -> dict:
    """Recalls relevant facts from the agent's long-term memory based on a query."""
    memory = _load_memory()
    # For a simple implementation, just return all facts that contain the query string
    # In a more advanced system, this would involve vector embeddings and similarity search
    relevant_facts = [item["fact"] for item in memory if query.lower() in item["fact"].lower()]
    if relevant_facts:
        return {"status": "success", "facts": relevant_facts}
    return {"status": "not_found", "message": "No relevant facts found in memory."}