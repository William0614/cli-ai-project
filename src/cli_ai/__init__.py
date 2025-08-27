"""CLI AI Project - Command-line assistant with vision capabilities."""

__version__ = "0.1.0"

from .core.ai_engine import think, reflexion, speak_text_openai, classify_intent
from .tools.executor import execute_tool

__all__ = [
    "think",
    "reflexion", 
    "speak_text_openai",
    "classify_intent",
    "execute_tool"
]

__all__ = [
    "think",
    "reflexion", 
    "speak_text_openai",
    "classify_intent",
    "execute_tool"
]
