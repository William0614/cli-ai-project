
import json
import os
import time
from typing import List, Dict, Any, Optional

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

def recall_memory(query: str = "", memory_type: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """Recalls relevant facts from the agent's long-term memory based on a query and optional type/limit."""
    memory = _load_memory()
    
    # Start with all memory, then filter
    filtered_memory = memory

    # 1. Filter by memory_type if provided
    if memory_type:
        filtered_memory = [item for item in filtered_memory if item.get("type") == memory_type]

    # 2. If a query is provided, it's a search for relevant facts, not conversation history
    if query:
        # If memory_type wasn't specified, default to searching 'fact' type for queries
        if not memory_type:
            fact_memory = [item for item in memory if item.get("type") == "fact"]
        else:
            fact_memory = filtered_memory # Use the already filtered memory if type was specified
        
        # Perform the relevance search on the appropriate memory slice
        relevant_facts = [item["fact"] for item in fact_memory if query.lower() in item["fact"].lower()]
    else:
        # If no query, just return the (potentially type-filtered) memory
        relevant_facts = [item["fact"] for item in filtered_memory]


    # 3. Apply limit, typically for conversation history (most recent first)
    # This should be applied after filtering and searching
    if limit is not None:
        # Sort by timestamp descending to get the most recent items
        sorted_memory = sorted(filtered_memory, key=lambda x: x.get("timestamp", 0), reverse=True)
        relevant_facts = [item["fact"] for item in sorted_memory[:limit]]


    if relevant_facts:
        return {"status": "success", "facts": relevant_facts}
    return {"status": "not_found", "message": "No relevant facts found in memory."}
