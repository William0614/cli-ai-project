"""
Simple Repetition Detection - Prevents infinite loops while letting LLM handle task completion
"""

def analyze_task_progress(task_memory: dict, latest_action: dict, latest_result: dict) -> dict:
    """
    Simple repetition detection to prevent infinite loops.
    Let the LLM handle all task completion logic.
    
    Returns:
        {
            'should_continue': bool,
            'reason': str
        }
    """
    actions_taken = task_memory.get("actions_taken", [])
    actions_count = len(actions_taken)
    
    # No actions yet - let LLM start
    if actions_count == 0:
        return {'should_continue': True, 'reason': 'Ready to start task'}
    
    # Safety valve: prevent extremely long task chains
    if actions_count > 25:
        return {
            'should_continue': False,
            'reason': f'Task has taken {actions_count} actions. Time to wrap up and provide results.'
        }
    
    # Check for exact repetition (same tool + same args multiple times)
    if actions_count >= 3 and latest_action:
        latest_tool = latest_action.get("tool")
        latest_args = latest_action.get("args", {})
        
        # Count how many times this exact tool+args combo has been used recently
        recent_actions = actions_taken[-4:]  # Look at last 4 actions
        exact_matches = 0
        
        for action in recent_actions:
            if (action.get("tool") == latest_tool and 
                action.get("args", {}) == latest_args and
                action.get("result", {}).get("status") == "Success"):
                exact_matches += 1
        
        # If we've done the exact same successful action 3+ times recently
        if exact_matches >= 3:
            return {
                'should_continue': False,
                'reason': f'Detected {exact_matches} repetitions of {latest_tool}. Stopping to prevent infinite loop.'
            }
    
    # Check for excessive directory listing (common stuck pattern)
    if actions_count >= 5:
        recent_actions = actions_taken[-5:]
        list_directory_count = sum(1 for a in recent_actions if a.get("tool") == "list_directory")
        
        if list_directory_count >= 4:
            return {
                'should_continue': False,
                'reason': 'Too much directory listing without taking action. Time to proceed with the task.'
            }
    
    # Default: let the LLM continue with its reasoning
    return {'should_continue': True, 'reason': 'Continue normally'}
