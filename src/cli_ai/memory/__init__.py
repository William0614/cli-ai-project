"""
Smart Memory Architecture Package

This package implements a hybrid memory system combining:
1. Session Memory Manager - Bounded recent conversation history
2. Vector Memory Manager - Semantic search of overflow conversations  
3. User Preference Manager - Learned user patterns and preferences
4. Context Assembly Engine - Intelligent context building for AI

Architecture: AI Context = System Prompt + Recent History (20) + RAG from Vector DB + User Preferences
"""

from .session_manager import SessionMemoryManager
from .vector_manager import VectorMemoryManager

__all__ = [
    "SessionMemoryManager",
    "VectorMemoryManager"
]

__version__ = "2.0.0"
