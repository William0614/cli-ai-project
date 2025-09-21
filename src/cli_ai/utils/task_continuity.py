"""
Task Continuity Detection - Determines if a user input is a new task or continuation
"""
import re
from typing import Optional

# Keywords that indicate task continuation (not starting a new task)
CONTINUATION_KEYWORDS = [
    # Direct continuation commands
    "continue", "keep going", "proceed", "next", "more", "go on",
    
    # Progress inquiries
    "what did you find", "what's the result", "show me", "tell me", 
    "what happened", "status", "progress", "where are we",
    
    # Clarification/elaboration
    "yes", "no", "ok", "okay", "sure", "exactly", "right", "correct",
    "that's right", "that's correct", "sounds good",
    
    # Refinement requests
    "also", "and", "but", "however", "instead", "actually", 
    "can you also", "what about", "how about",
    
    # Simple acknowledgments
    "thanks", "thank you", "got it", "understood", "alright"
]

# Contextual references that indicate continuation (referring to current task context)
CONTEXTUAL_REFERENCES = [
    # Referring to items from current task
    "those", "these", "them", "it", "that", "this",
    "the ones", "the files", "the images", "the results",
    "what you found", "what we have", "from before",
    "the same", "the previous", "from earlier"
]

# Keywords that clearly indicate NEW tasks
NEW_TASK_KEYWORDS = [
    # Action verbs that start new tasks
    "sort", "organize", "classify", "group", "categorize", "arrange",
    "find", "search", "look for", "locate", "identify", "analyze",
    "create", "make", "build", "generate", "write", "save",
    "delete", "remove", "move", "copy", "rename", "list",
    "show me the", "what files", "tell me about", "describe",
    
    # Clear task starters
    "can you", "please", "i want you to", "i need you to", "help me",
    
    # Task transitions
    "now", "next", "then", "after that"
]

# Phrases that indicate task transitions (new tasks)
TASK_TRANSITION_PHRASES = [
    "now delete", "now remove", "now create", "now find", "now sort",
    "then delete", "then remove", "then create", "then find", "then sort",
    "help me with something else", "something different", "new task",
    "instead", "actually", "change of plans"
]

def is_task_continuation(user_input: str, current_task_memory: dict) -> bool:
    """
    Determine if the user input is continuing an existing task
    or starting a new one.
    
    Args:
        user_input: The user's input string
        current_task_memory: Current task memory state
        
    Returns:
        True if this is continuing an existing task, False if it's a new task
    """
    if not current_task_memory.get("actions_taken"):
        # No existing task, this must be new
        return False
    
    user_lower = user_input.lower().strip()
    
    # Very short inputs are often continuations
    if len(user_lower) <= 3 and user_lower in ["yes", "no", "ok", "go", "more"]:
        return True
    
    # Check for explicit continuation keywords
    for keyword in CONTINUATION_KEYWORDS:
        if keyword in user_lower:
            return True
    
    # Check for contextual references (e.g., "those files", "delete them")
    # These strongly indicate continuation since they refer to current context
    has_contextual_ref = any(ref in user_lower for ref in CONTEXTUAL_REFERENCES)
    if has_contextual_ref:
        # If it has contextual references, it's very likely a continuation
        # unless it's explicitly starting a completely new task
        explicit_new_task = any(user_lower.startswith(f"help me {keyword}") or 
                               user_lower.startswith(f"can you {keyword}") 
                               for keyword in ["with something", "do something", "start"])
        return not explicit_new_task
    
    # Check for task transition phrases (these override continuation keywords)
    for phrase in TASK_TRANSITION_PHRASES:
        if phrase in user_lower:
            # But if it has contextual references, it might still be continuation
            if has_contextual_ref:
                return True
            return False
    
    # Check for new task indicators
    for keyword in NEW_TASK_KEYWORDS:
        if user_lower.startswith(keyword) or f" {keyword}" in f" {user_lower}":
            # But if it references current context, it's likely continuation
            if has_contextual_ref:
                return True
            return False
    
    # Heuristic: If input is very similar to current task, it's likely continuation
    current_task = current_task_memory.get("original_request", "").lower()
    if current_task and len(current_task) > 10:
        # Simple similarity check - count common words
        current_words = set(re.findall(r'\w+', current_task))
        input_words = set(re.findall(r'\w+', user_lower))
        common_words = current_words.intersection(input_words)
        
        # If more than 30% of words are common, likely continuation
        if len(common_words) / max(len(input_words), 1) > 0.3:
            return True
    
    # If we have an active task and input doesn't clearly start a new one,
    # and it's not very long, assume continuation
    if len(user_lower.split()) <= 5:
        return True
    
    # Default to new task for longer, unclear inputs
    return False


def should_reset_task_memory(user_input: str, current_task_memory: dict) -> bool:
    """
    Decide whether to reset task memory based on user input.
    
    Returns True if task memory should be reset (new task), False otherwise.
    """
    return not is_task_continuation(user_input, current_task_memory)
