"""
Smart Memory Architecture - Session Memory Manager
Phase 1: Bounded session memory with automatic overflow management

This module replaces the unlimited history growth with a bounded session memory
that maintains the last N messages and handles overflow to vector storage.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import json


class SessionMemoryManager:
    """Manages recent conversation history with bounded memory and overflow handling."""
    
    def __init__(self, max_recent_length: int = 20):
        """
        Initialize session memory manager.
        
        Args:
            max_recent_length: Maximum number of recent messages to keep in memory
        """
        self.recent_messages: List[Dict[str, Any]] = []
        self.max_recent_length = max_recent_length
        self.session_id = self._generate_session_id()
        self.message_count = 0
        
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def add_exchange(
        self, 
        user_msg: str, 
        ai_msg: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Add a user-AI message exchange to recent memory.
        
        Args:
            user_msg: User's message content
            ai_msg: AI's response content (can be string or dict for complex responses)
            metadata: Optional metadata for the exchange
            
        Returns:
            List of overflow messages if overflow occurred, None otherwise
        """
        current_time = datetime.now()
        
        # Create standardized message format - compatible with existing system
        user_message = {
            "role": "user",
            "content": user_msg,
            "timestamp": current_time,
            "message_id": self.message_count,
            "session_id": self.session_id,
            "metadata": metadata or {}
        }
        
        ai_message = {
            "role": "assistant", 
            "content": ai_msg,  # Keep original format (string or dict)
            "timestamp": current_time,
            "message_id": self.message_count + 1,
            "session_id": self.session_id,
            "metadata": metadata or {}
        }
        
        # Add messages to recent memory
        self.recent_messages.extend([user_message, ai_message])
        self.message_count += 2
        
        # Check for overflow - handle in pairs to maintain conversation integrity
        overflow_messages = None
        if len(self.recent_messages) > self.max_recent_length:
            # Calculate how many messages to overflow
            overflow_count = len(self.recent_messages) - self.max_recent_length
            
            # Ensure we overflow in pairs (user + assistant)
            # If overflow_count is odd, round up to next even number
            if overflow_count % 2 != 0:
                overflow_count += 1
            
            # Don't overflow more than available messages
            overflow_count = min(overflow_count, len(self.recent_messages))
            
            # Extract overflow messages (oldest pairs)
            overflow_messages = self.recent_messages[:overflow_count]
            
            # Keep only recent messages
            self.recent_messages = self.recent_messages[overflow_count:]
            
            print(f"[Smart Memory] Overflow: {overflow_count} messages ({overflow_count//2} conversation pairs) moved to vector storage")
            
            # Ensure we don't break conversation boundaries
            overflow_messages = self._ensure_conversation_boundary(overflow_messages)
            
        return overflow_messages
    
    def add_single_message(
        self, 
        role: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Add a single message (for cases like error messages, system responses).
        
        Args:
            role: Message role ("user", "assistant", "system")
            content: Message content
            metadata: Optional metadata
            
        Returns:
            List of overflow messages if overflow occurred, None otherwise
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(),
            "message_id": self.message_count,
            "session_id": self.session_id,
            "metadata": metadata or {}
        }
        
        self.recent_messages.append(message)
        self.message_count += 1
        
        # Check for overflow - maintain pairs for single messages too
        overflow_messages = None
        if len(self.recent_messages) > self.max_recent_length:
            overflow_count = len(self.recent_messages) - self.max_recent_length
            
            # For single message additions, we might break pairs
            # Try to overflow in pairs when possible, but allow single overflow if needed
            if overflow_count == 1 and len(self.recent_messages) > 1:
                # Check if we can overflow one more to maintain pairs
                if len(self.recent_messages) > self.max_recent_length + 1:
                    overflow_count = 2  # Overflow a pair
                # If not, just overflow the single message
                
            overflow_messages = self.recent_messages[:overflow_count]
            self.recent_messages = self.recent_messages[overflow_count:]
            
            pair_count = overflow_count // 2
            single_count = overflow_count % 2
            print(f"[Smart Memory] Overflow: {overflow_count} messages ({pair_count} pairs + {single_count} single) moved to vector storage")
    
    def _normalize_content(self, content: Any) -> str:
        """
        Convert complex content formats to clean string format.
        Handles the current system's mixed content types.
        """
        if isinstance(content, str):
            return content
        
        elif isinstance(content, dict):
            # Handle complex action responses from current system
            if "thought" in content and "observation" in content:
                thought = content.get("thought", "")
                action = content.get("action", "")
                args = content.get("args", {})
                observation = content.get("observation", "")
                
                # Format as readable action response
                return f"Thought: {thought}\nAction: {action}({args})\nObservation: {observation}"
            
            elif "thought" in content:
                return f"Thought: {content['thought']}"
            
            else:
                # Fallback for other dict formats
                return str(content)
        
        else:
            return str(content)
    
    def _normalize_role(self, role: str) -> str:
        """Convert role names to standard OpenAI format."""
        role_mapping = {
            "AI": "assistant",
            "ai": "assistant", 
            "user": "user",
            "assistant": "assistant",
            "system": "system"
        }
        return role_mapping.get(role, "assistant")
    
    def add_legacy_message(self, message: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Add a message from the current legacy system format.
        Converts to optimal format automatically.
        """
        normalized_message = {
            "role": self._normalize_role(message.get("role", "assistant")),
            "content": self._normalize_content(message.get("content", "")),
            "timestamp": datetime.now(),
            "message_id": self.message_count,
            "session_id": self.session_id,
            "metadata": {
                "source": "legacy_conversion",
                "original_role": message.get("role"),
                "original_format": type(message.get("content")).__name__
            }
        }
        
        self.recent_messages.append(normalized_message)
        self.message_count += 1
        
        # Check for overflow
        overflow_messages = None
        if len(self.recent_messages) > self.max_recent_length:
            overflow_count = len(self.recent_messages) - self.max_recent_length
            
            # Try to overflow in pairs when possible
            if overflow_count % 2 != 0 and len(self.recent_messages) > overflow_count:
                overflow_count += 1
            
            overflow_messages = self.recent_messages[:overflow_count]
            self.recent_messages = self.recent_messages[overflow_count:]
            
            pair_count = overflow_count // 2
            single_count = overflow_count % 2
            print(f"[Smart Memory] Legacy overflow: {overflow_count} messages ({pair_count} pairs + {single_count} single)")
            
            # Ensure conversation boundaries
            overflow_messages = self._ensure_conversation_boundary(overflow_messages)
            
        return overflow_messages
        """Check if the message list ends with a complete user-assistant pair."""
        if len(messages) < 2:
            return False
        
        # Check if last two messages are user -> assistant
        return (messages[-2]["role"] == "user" and 
                messages[-1]["role"] == "assistant")
    
    def _ensure_conversation_boundary(self, overflow_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ensure overflow doesn't break conversation pairs.
        If overflow ends with incomplete pair, move the orphaned message back to recent.
        """
        if not overflow_messages:
            return overflow_messages
            
        # If overflow ends with a user message (no assistant response), move it back
        if overflow_messages[-1]["role"] == "user":
            orphaned_message = overflow_messages.pop()
            self.recent_messages.insert(0, orphaned_message)
            print(f"[Smart Memory] Moved orphaned user message back to recent memory")
            
        return overflow_messages
    
    def get_recent_messages(self) -> List[Dict[str, Any]]:
        """Get all recent messages in chronological order."""
        return self.recent_messages.copy()
    
    def get_recent_messages_for_ai(self) -> List[Dict[str, Any]]:
        """
        Get recent messages formatted for AI context.
        Returns only role and content for clean AI input.
        """
        return [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in self.recent_messages
        ]
    
    def get_latest_user_message(self) -> Optional[str]:
        """Get the most recent user message content."""
        for message in reversed(self.recent_messages):
            if message["role"] == "user":
                return message["content"]
        return None
    
    def add_action_response(
        self, 
        user_request: str,
        thought: str, 
        action: str, 
        args: Dict[str, Any], 
        observation: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Add an action-based response (for tool usage) in optimal format.
        Converts complex action data to readable conversation format.
        """
        # Format action response as readable content
        action_content = f"Thought: {thought}\nAction: {action}({args})\nResult: {observation}"
        
        return self.add_exchange(user_request, action_content, metadata)
    
    def get_recent_messages_legacy_format(self) -> List[Dict[str, Any]]:
        """
        Get recent messages in the old format for backward compatibility.
        Only use during transition period.
        """
        legacy_messages = []
        for msg in self.recent_messages:
            legacy_msg = {
                "role": "AI" if msg["role"] == "assistant" else msg["role"],
                "content": msg["content"]
            }
            legacy_messages.append(legacy_msg)
        return legacy_messages
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary statistics about the current conversation."""
        user_messages = len([m for m in self.recent_messages if m["role"] == "user"])
        ai_messages = len([m for m in self.recent_messages if m["role"] == "assistant"])
        
        return {
            "session_id": self.session_id,
            "total_messages": len(self.recent_messages),
            "user_messages": user_messages,
            "ai_messages": ai_messages,
            "message_count": self.message_count,
            "session_start": self.recent_messages[0]["timestamp"] if self.recent_messages else None,
            "last_activity": self.recent_messages[-1]["timestamp"] if self.recent_messages else None
        }
    
    def clear_session(self) -> List[Dict[str, Any]]:
        """
        Clear current session and return all messages for storage.
        Useful for session end or manual reset.
        """
        all_messages = self.recent_messages.copy()
        self.recent_messages = []
        self.session_id = self._generate_session_id()
        self.message_count = 0
        
        return all_messages
    
    def format_conversation_for_storage(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format conversation messages for vector storage.
        Creates a readable conversation format for semantic search.
        """
        conversation_text = f"Session: {self.session_id}\n"
        conversation_text += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for msg in messages:
            role = msg["role"].title()
            content = msg["content"]
            timestamp = msg["timestamp"].strftime('%H:%M:%S')
            
            # Handle complex content (like action responses)
            if isinstance(content, dict):
                if "thought" in content:
                    content = f"Thought: {content['thought']}"
                elif "observation" in content:
                    content = f"Action result: {content['observation']}"
                else:
                    content = str(content)
            
            conversation_text += f"[{timestamp}] {role}: {content}\n"
        
        return conversation_text
    
    def debug_info(self) -> Dict[str, Any]:
        """Get debug information about memory state."""
        # Calculate memory usage without datetime objects
        messages_for_size = []
        for msg in self.recent_messages:
            msg_copy = msg.copy()
            msg_copy["timestamp"] = msg_copy["timestamp"].isoformat()
            messages_for_size.append(msg_copy)
        
        return {
            "session_id": self.session_id,
            "recent_message_count": len(self.recent_messages),
            "max_recent_length": self.max_recent_length,
            "total_message_count": self.message_count,
            "memory_usage_mb": len(json.dumps(messages_for_size)) / (1024 * 1024),
            "oldest_message": self.recent_messages[0]["timestamp"].isoformat() if self.recent_messages else None,
            "newest_message": self.recent_messages[-1]["timestamp"].isoformat() if self.recent_messages else None
        }


# Testing and example usage
if __name__ == "__main__":
    # Example usage
    session = SessionMemoryManager(max_recent_length=6)  # Small limit for testing
    
    # Simulate conversation
    print("=== Testing Session Memory Manager ===")
    
    # Add several exchanges
    for i in range(4):
        user_msg = f"Test user message {i+1}"
        ai_msg = f"Test AI response {i+1}"
        
        overflow = session.add_exchange(user_msg, ai_msg)
        
        if overflow:
            print(f"Overflow occurred: {len(overflow)} messages")
            formatted = session.format_conversation_for_storage(overflow)
            print("Overflow content:")
            print(formatted[:200] + "..." if len(formatted) > 200 else formatted)
    
    print(f"\nCurrent session summary: {session.get_conversation_summary()}")
    print(f"Recent messages for AI: {len(session.get_recent_messages_for_ai())}")
    print(f"Debug info: {session.debug_info()}")
