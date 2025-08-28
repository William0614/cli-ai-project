"""
Smart Memory System for CLI AI Agent

Provides intelligent memory management with:
- SessionMemoryManager: Bounded recent message storage with overflow handling
- VectorMemoryManager: FAISS-based semantic search and long-term storage
- UserInfoManager: Automatic extraction and management of user information

This hybrid architecture maintains recent context while providing semantic search
capabilities and intelligent user profile building from natural conversation.
"""

from .session_manager import SessionMemoryManager
from .vector_manager import VectorMemoryManager
from .userinfo_manager import UserInfoManager

__all__ = ["SessionMemoryManager", "VectorMemoryManager", "UserInfoManager"]

__version__ = "2.0.0"
