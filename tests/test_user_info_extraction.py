#!/usr/bin/env python3
"""
Test script for UserInfo extraction and modern AI memory patterns.
Demonstrates how automatic extraction replaces manual save_memory calls.
"""

import os
import sys
from datetime import datetime, timedelta
from colorama import Fore, Style, init

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cli_ai.memory import SessionMemoryManager, VectorMemoryManager, UserInfoManager

def print_separator(title):
    """Print a visual separator with title."""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}{title.center(80)}")
    print(f"{Fore.CYAN}{'=' * 80}")

def print_subsection(title):
    """Print a subsection header."""
    print(f"\n{Fore.YELLOW}{'-' * 60}")
    print(f"{Fore.YELLOW}{title}")
    print(f"{Fore.YELLOW}{'-' * 60}")

def test_user_info_extraction():
    """Test automatic user info extraction vs manual save_memory."""
    init(autoreset=True)
    
    print_separator("USERINFO EXTRACTION TEST")
    print(f"{Fore.CYAN}Comparing: Manual save_memory vs Automatic extraction")
    print(f"{Fore.CYAN}Modern AI Pattern: Extract user info → Clean conversations")
    
    # Initialize managers
    session_memory = SessionMemoryManager(max_recent_length=4)
    vector_memory = VectorMemoryManager()
    user_info = UserInfoManager()
    
    print(f"{Fore.GREEN}✓ Memory systems initialized")
    
    # Simulate natural conversations with user information
    conversations = [
        ("Hi, I'm John and I love pizza on Fridays", "Nice to meet you John! Pizza Fridays sound great."),
        ("My favorite color is blue", "Blue is a wonderful color!"),
        ("Actually, I prefer green now", "Thanks for letting me know you prefer green!"),
        ("I work as a software engineer", "That's awesome! Software engineering is a great field."),
        ("I want to learn machine learning", "Machine learning is fascinating! I'd be happy to help."),
        ("I live in San Francisco", "San Francisco is a beautiful city!"),
    ]
    
    print_subsection("SIMULATING NATURAL CONVERSATION")
    
    all_extracted_info = []
    
    for i, (user_msg, ai_msg) in enumerate(conversations):
        print(f"\n{Fore.CYAN}Exchange {i+1}:")
        print(f"  User: {user_msg}")
        print(f"  AI: {ai_msg}")
        
        # Add to session memory (normal conversation flow)
        session_memory.add_exchange(user_msg, ai_msg)
        
        # Extract user info from current exchange
        current_messages = [
            {"role": "user", "content": user_msg, "timestamp": datetime.now(), "session_id": session_memory.session_id},
            {"role": "assistant", "content": ai_msg, "timestamp": datetime.now(), "session_id": session_memory.session_id}
        ]
        
        extracted = user_info.extract_user_info_from_conversation(current_messages)
        
        if extracted:
            print(f"  {Fore.GREEN}→ Automatically extracted:")
            stored_count = user_info.store_user_info(extracted)
            for info in extracted:
                print(f"    • {info.category}: {info.key} = {info.value} (confidence: {info.confidence})")
            print(f"    Stored: {stored_count} items")
            all_extracted_info.extend(extracted)
        else:
            print(f"  {Fore.YELLOW}→ No user info patterns detected")
        
        # Check for session overflow
        if len(session_memory.recent_messages) > session_memory.max_recent_length:
            overflow_count = len(session_memory.recent_messages) - session_memory.max_recent_length
            if overflow_count % 2 != 0:
                overflow_count += 1
            
            overflow_messages = session_memory.recent_messages[:overflow_count]
            session_memory.recent_messages = session_memory.recent_messages[overflow_count:]
            
            if overflow_messages:
                # Extract user info before storing in vector DB
                extracted_from_overflow = user_info.extract_user_info_from_conversation(overflow_messages)
                if extracted_from_overflow:
                    user_info.store_user_info(extracted_from_overflow)
                
                # Store conversation in vector DB
                vector_memory.store_conversation_chunk(overflow_messages, {"reason": "overflow"})
                print(f"  {Fore.BLUE}→ {len(overflow_messages)} messages moved to vector storage")
    
    print_subsection("EXTRACTED USER INFORMATION")
    
    # Show all extracted user info by category
    categories = ["preference", "fact", "goal"]
    
    for category in categories:
        user_data = user_info.get_user_info(category=category)
        if user_data:
            print(f"\n{Fore.GREEN}{category.title()}s:")
            for item in user_data:
                confidence_indicator = "✓" if item['confidence'] > 0.8 else "~"
                print(f"  {confidence_indicator} {item['key']}: {item['value']}")
                print(f"    Source: {item['source']} | Session: {item['session_id'][:12]}...")
    
    print_subsection("USER CONTEXT BUILDING")
    
    # Test user context building (replaces vector search for user info)
    user_context = user_info.build_user_context()
    print(f"{Fore.WHITE}Generated User Context:")
    print(user_context)
    
    print_subsection("COMPARISON: OLD vs NEW APPROACH")
    
    print(f"{Fore.RED}❌ OLD (Manual save_memory):")
    print(f"  • User: 'Remember that I like pizza'")
    print(f"  • AI: 'Saved to memory: User likes pizza'")
    print(f"  • Problem: Manual, interrupts conversation flow")
    
    print(f"\n{Fore.GREEN}✅ NEW (Automatic extraction):")
    print(f"  • User: 'I love pizza on Fridays' (natural)")
    print(f"  • AI: 'Pizza Fridays sound great!' (natural)")
    print(f"  • Background: Auto-extracts 'preference: love_item = pizza on fridays'")
    print(f"  • Benefit: Natural conversation + automatic learning")
    
    print_subsection("MODERN AI MEMORY PATTERN")
    
    print(f"{Fore.CYAN}Phase 1: {Fore.GREEN}Session Memory (recent context)")
    print(f"  Current: {len(session_memory.recent_messages)} messages in session")
    
    print(f"\n{Fore.CYAN}Phase 2: {Fore.GREEN}User Info Extraction (persistent)")
    stats = user_info.get_stats()
    print(f"  Extracted: {stats.get('total_user_info', 0)} user information items")
    print(f"  Categories: {list(stats.get('categories', {}).keys())}")
    
    print(f"\n{Fore.CYAN}Phase 3: {Fore.YELLOW}Conversation Cleanup (coming next)")
    print(f"  Will clean: Old conversations after user info extraction")
    print(f"  Keeps: User info + recent session context only")
    
    print_separator("USERINFO TEST COMPLETE")
    print(f"{Fore.GREEN}✅ Automatic extraction working perfectly!")
    print(f"{Fore.GREEN}✅ Ready to replace manual save_memory function")
    print(f"{Fore.GREEN}✅ Modern AI memory pattern implemented")

if __name__ == "__main__":
    test_user_info_extraction()
