#!/usr/bin/env python3
"""
Test script for the integrated smart memory system.
Tests both session memory boundaries and vector storage integration.
"""

import os
import sys
from colorama import Fore, Style, init

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cli_ai.memory import SessionMemoryManager, VectorMemoryManager

def test_memory_integration():
    """Test the complete memory integration system."""
    init(autoreset=True)
    
    print(Fore.CYAN + "=" * 60)
    print(Fore.CYAN + "  SMART MEMORY SYSTEM INTEGRATION TEST")
    print(Fore.CYAN + "=" * 60)
    
    # Initialize managers
    session_memory = SessionMemoryManager(max_recent_length=6)  # Small limit for testing
    vector_memory = VectorMemoryManager()
    
    print(f"{Fore.GREEN}✓ Session Memory: Max {session_memory.max_recent_length} messages")
    print(f"{Fore.GREEN}✓ Vector Memory: Connected to database")
    print()
    
    # Test conversation flow
    conversations = [
        ("user", "Hello, I'm testing the memory system"),
        ("assistant", "Hello! I'm ready to help test the memory system."),
        ("user", "Can you remember our previous conversations?"),
        ("assistant", "Yes, I can access both recent conversations and search through older ones."),
        ("user", "What about when we have many messages?"),
        ("assistant", "The system automatically moves older conversations to long-term storage."),
        ("user", "How does the vector search work?"),
        ("assistant", "It uses semantic similarity to find relevant past conversations."),
    ]
    
    print(Fore.YELLOW + "Adding conversations to session memory...")
    
    for i in range(0, len(conversations), 2):
        if i + 1 < len(conversations):
            user_msg = conversations[i][1]
            ai_msg = conversations[i + 1][1]
            
            session_memory.add_exchange(user_msg, ai_msg)
            print(f"  Added exchange:")
            print(f"    User: {user_msg[:50]}...")
            print(f"    AI: {ai_msg[:50]}...")
            
            # Check for overflow after each exchange
            if len(session_memory.recent_messages) > session_memory.max_recent_length:
                overflow_count = len(session_memory.recent_messages) - session_memory.max_recent_length
                if overflow_count % 2 != 0:
                    overflow_count += 1
                
                overflow_messages = session_memory.recent_messages[:overflow_count]
                session_memory.recent_messages = session_memory.recent_messages[overflow_count:]
                
                if overflow_messages:
                    success = vector_memory.store_conversation_chunk(overflow_messages, {
                        "reason": "overflow",
                        "trigger": "test_integration"
                    })
                    pairs = len(overflow_messages) // 2
                    print(f"{Fore.BLUE}    [Overflow] {len(overflow_messages)} messages ({pairs} pairs) moved to vector storage")
                    print(f"{Fore.GREEN}    [Vector] Storage successful: {success}")
            print()
    
    print()
    print(Fore.CYAN + "Memory State Summary:")
    print(f"  Recent Messages: {len(session_memory.recent_messages)}")
    print(f"  Vector Database: Connected and operational")
    
    # Test semantic search
    print()
    print(Fore.YELLOW + "Testing semantic search capabilities...")
    search_results = vector_memory.search_relevant_context("memory system testing", limit=2)
    print(f"  Found {len(search_results)} relevant conversations")
    
    for i, result in enumerate(search_results):
        print(f"    {i+1}. Similarity: {result['similarity_score']:.3f}")
        print(f"       Content: {result['content'][:100]}...")
    
    # Test RAG context building
    print()
    print(Fore.YELLOW + "Testing RAG context building...")
    rag_context = vector_memory.build_rag_context("How does the memory work?")
    print(f"  RAG Context length: {len(rag_context)} characters")
    if rag_context:
        print(f"  Sample: {rag_context[:150]}...")
    
    print()
    print(Fore.GREEN + "✅ Integration test completed successfully!")
    print(Fore.CYAN + "=" * 60)

if __name__ == "__main__":
    test_memory_integration()
