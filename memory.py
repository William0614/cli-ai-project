
import json
import os
import time
from typing import List, Dict, Any, Optional
from semantic_search import semantic_search_facts

MEMORY_FILE = "agent_memory.json"

def _load_memory() -> List[Dict[str, Any]]:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    return []

def _save_memory(memory: List[Dict[str, Any]]):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=2)

def save_memory(fact: str, memory_type: str = "fact") -> Dict[str, str]:
    """Saves a fact to the agent's long-term memory with a specified type."""
    memory = _load_memory()
    memory.append({"fact": fact, "timestamp": time.time(), "type": memory_type})
    _save_memory(memory)
    return {"status": "success", "message": "Fact saved to memory."}

async def recall_memory(query: str = "", memory_type: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """Recalls relevant facts from the agent's long-term memory based on a query and optional type/limit."""
    memory = _load_memory()

    # If a query is provided and no memory_type is specified, default to 'fact'
    if query and not memory_type:
        memory_type = "fact"

    filtered_memory = memory
    if memory_type:
        filtered_memory = [item for item in filtered_memory if item.get("type") == memory_type]

    all_facts = [item["fact"] for item in filtered_memory]

    if query:
        relevant_facts = await semantic_search_facts(query, all_facts)
    else:
        relevant_facts = all_facts

    if limit is not None:
        relevant_facts = relevant_facts[-limit:]

    if relevant_facts:
        return {"status": "success", "facts": relevant_facts}
    return {"status": "not_found", "message": "No relevant facts found in memory."}
