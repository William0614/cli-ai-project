#!/usr/bin/env python3
"""
Test script for temporal precedence in memory system.
Tests how the system handles conflicting information over time.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from colorama import Fore, Style, init

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cli_ai.memory import SessionMemoryManager, VectorMemoryManager

def test_temporal_precedence():
    """Test temporal precedence with conflicting preferences."""
    init(autoreset=True)
    
    print(Fore.CYAN + "=" * 60)
    print(Fore.CYAN + "  TEMPORAL PRECEDENCE TEST")
    print(Fore.CYAN + "=" * 60)
    
    # Initialize managers
    session_memory = SessionMemoryManager(max_recent_length=6)
    vector_memory = VectorMemoryManager()
    
    print(f"{Fore.GREEN}✓ Session Memory: Max {session_memory.max_recent_length} messages")
    print(f"{Fore.GREEN}✓ Vector Memory: Connected with temporal precedence")
    print()
    
    # Simulate older preference
    print(Fore.YELLOW + "Simulating OLDER conversation (I like Friday)...")
    older_time = datetime.now() - timedelta(days=1)  # Yesterday
    older_messages = [
        {"role": "user", "content": "I love Fridays the most", "timestamp": older_time, "session_id": "old_session"},
        {"role": "assistant", "content": "Great to know you love Fridays! I'll remember that.", "timestamp": older_time, "session_id": "old_session"}
    ]
    
    success = vector_memory.store_conversation_chunk(older_messages, {
        "reason": "test",
        "trigger": "temporal_test_old"
    })
    print(f"  {Fore.GREEN if success else Fore.RED}Stored older preference: {success}")
    
    # Wait a moment to ensure timestamp difference
    time.sleep(2)
    
    # Simulate newer preference  
    print(Fore.YELLOW + "Simulating NEWER conversation (I like Sunday)...")
    newer_time = datetime.now()  # Now
    newer_messages = [
        {"role": "user", "content": "Actually, I prefer Sundays now", "timestamp": newer_time, "session_id": "new_session"},
        {"role": "assistant", "content": "Thanks for the update! I'll remember you prefer Sundays.", "timestamp": newer_time, "session_id": "new_session"}
    ]
    
    success = vector_memory.store_conversation_chunk(newer_messages, {
        "reason": "test", 
        "trigger": "temporal_test_new"
    })
    print(f"  {Fore.GREEN if success else Fore.RED}Stored newer preference: {success}")
    print()
    
    # Test search prioritization
    print(Fore.YELLOW + "Testing temporal precedence in search...")
    search_results = vector_memory.search_relevant_context(
        "what day do I like?", 
        limit=3,
        temporal_weight=0.5  # Strong temporal weighting
    )
    
    print(f"  Found {len(search_results)} results:")
    for i, result in enumerate(search_results):
        similarity = result['similarity_score']
        base_sim = result['base_similarity'] 
        temporal_boost = result['temporal_boost']
        content_preview = result['content'][:80] + "..." if len(result['content']) > 80 else result['content']
        
        print(f"    {i+1}. Score: {similarity:.3f} (base: {base_sim:.3f} + temporal: {temporal_boost:.3f})")
        print(f"       Content: {content_preview}")
        print()
    
    # Test RAG context building
    print(Fore.YELLOW + "Testing RAG context building...")
    rag_context = vector_memory.build_rag_context("what day do I prefer?")
    print(f"  RAG Context:")
    print(f"  {rag_context}")
    
    print()
    print(Fore.GREEN + "✅ Temporal precedence test completed!")
    print(Fore.CYAN + "Expected: Newer 'Sunday' preference should rank higher than older 'Friday'")
    print(Fore.CYAN + "=" * 60)

if __name__ == "__main__":
    test_temporal_precedence()
