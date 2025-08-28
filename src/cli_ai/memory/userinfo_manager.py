#!/usr/bin/env python3
"""
UserInfo Manager - Automatic extraction and management of user information.
Replaces manual save_memory function with intelligent conversation analysis.
"""

import json
import sqlite3
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import os

# Import AI for analysis (we'll use the existing AI system)
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class UserInfo:
    """Structured user information data class."""
    category: str  # 'preference', 'fact', 'goal', 'behavior', 'context'
    key: str       # 'favorite_color', 'name', 'job', etc.
    value: str     # 'blue', 'John', 'engineer', etc.
    confidence: float  # 0.0-1.0 confidence in extraction
    source: str    # Where this info came from
    timestamp: datetime
    session_id: str
    
class UserInfoManager:
    """
    Manages structured user information with automatic extraction from conversations.
    Replaces manual save_memory with intelligent conversation analysis.
    """
    
    def __init__(self, db_path: str = "agent_memory.db"):
        self.db_path = db_path
        self.init_user_info_table()
        
    def init_user_info_table(self):
        """Initialize user_info table for structured storage."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                active BOOLEAN DEFAULT 1,
                UNIQUE(category, key) ON CONFLICT REPLACE
            )
        """)
        
        conn.commit()
        conn.close()
        
    async def extract_user_info_from_conversation(self, messages: List[Dict[str, Any]]) -> List[UserInfo]:
        """
        Automatically extract user information from conversation messages.
        This is the key function that replaces manual save_memory.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            List of extracted UserInfo objects
        """
        extracted_info = []
        
        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                source_session_id = msg.get('session_id', 'unknown')
                
                # Extract different types of user information
                # All user info goes to persistent profile regardless of source session
                info_items = await self._analyze_user_content(content, source_session_id)
                extracted_info.extend(info_items)
                
        return extracted_info
    
    async def _analyze_user_content(self, content: str, source_session_id: str = None) -> List[UserInfo]:
        """
        Analyze user message content for personal information using LLM.
        Much more reliable than regex patterns - understands context and nuance.
        
        Args:
            content: User message content to analyze
            source_session_id: Original session (for reference, but user info goes to persistent profile)
        """
        if not content or len(content.strip()) < 3:
            return []
            
        extraction_prompt = f"""You are an expert at extracting structured user information from natural conversation.

Analyze this user message and extract any personal information. Focus on:
- Preferences (foods, activities, interests, likes/dislikes)  
- Facts (name, age, job, location, background)
- Goals (what they want to do/achieve)
- Behaviors (habits, tendencies)

User message: "{content}"

Return ONLY a JSON object with this structure:
{{
  "extractions": [
    {{
      "category": "preference|fact|goal|behavior", 
      "key": "descriptive_key",
      "value": "extracted_value",
      "confidence": 0.0-1.0
    }}
  ]
}}

Guidelines:
- Extract specific, meaningful information only
- For "I like to eat pizza" → category:"preference", key:"favorite_food", value:"pizza"
- For "My name is John" → category:"fact", key:"name", value:"John"  
- For "I want to learn Python" → category:"goal", key:"learning_goal", value:"Python"
- Use confidence 0.9 for explicit statements, 0.7 for implied, 0.5 for uncertain
- Skip vague or unclear information
- Maximum 5 extractions per message

Return empty extractions array if no clear user info found."""

        try:
            # Import the AI client here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from openai import AsyncOpenAI
            from dotenv import load_dotenv
            
            load_dotenv()
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert information extraction system. Return only valid JSON."},
                    {"role": "user", "content": extraction_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1  # Low temperature for consistent extraction
            )
            
            result = json.loads(response.choices[0].message.content)
            extractions = result.get("extractions", [])
            
            # Convert to UserInfo objects
            extracted_info = []
            timestamp = datetime.now()
            
            for extraction in extractions:
                if all(key in extraction for key in ["category", "key", "value", "confidence"]):
                    user_info = UserInfo(
                        category=extraction["category"],
                        key=extraction["key"], 
                        value=extraction["value"],
                        confidence=float(extraction["confidence"]),
                        source="llm_extraction",
                        timestamp=timestamp,
                        session_id="persistent_user_profile"  # Use persistent session ID
                    )
                    extracted_info.append(user_info)
            
            return extracted_info
            
        except Exception as e:
            print(f"[User Info] LLM extraction failed: {e}")
            # Fallback to empty list - don't break the system
            return []
        
        # Personal fact patterns  
        fact_patterns = [
            (r"My name is (\w+)", "fact", "name"),
            (r"I'm (\d+) years old", "fact", "age"),
            (r"I (?:work as|am) (?:a|an)\s*(.+)", "fact", "job"),
            (r"I live in (.+)", "fact", "location"),
            (r"I'm from (.+)", "fact", "origin"),
            (r"I study (.+)", "fact", "education"),
            (r"I have (?:a|an)\s*(.+)", "fact", "possessions"),
        ]
        
        # Goal patterns
        goal_patterns = [
            (r"I want to (.+)", "goal", "wants"),
            (r"I'm trying to (.+)", "goal", "goals"),
            (r"My goal is to (.+)", "goal", "main_goal"),
            (r"I hope to (.+)", "goal", "aspirations"),
            (r"I plan to (.+)", "goal", "plans"),
        ]
        
        # Behavior patterns
        behavior_patterns = [
            (r"I (?:usually|often|always)\s+(.+)", "behavior", "habits"),
            (r"I never (.+)", "behavior", "avoids"),
            (r"I tend to (.+)", "behavior", "tendencies"),
        ]
        
        # Process all pattern types
        all_patterns = [
            (preference_patterns, "preference"),
            (fact_patterns, "fact"), 
            (goal_patterns, "goal"),
            (behavior_patterns, "behavior")
        ]
        
        for pattern_group, default_category in all_patterns:
            for pattern, category, key_template in pattern_group:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    if len(match.groups()) == 1:
                        value = match.group(1).strip()
                        key = key_template
                    elif len(match.groups()) == 2:
                        key = key_template.format(match.group(1).lower())
                        value = match.group(2).strip()
                    else:
                        continue
                        
                    # Clean up extracted value
                    value = self._clean_extracted_value(value)
                    
                    if value and len(value) > 1:  # Valid extraction
                        user_info = UserInfo(
                            category=category,
                            key=key,
                            value=value,
                            confidence=0.8,  # High confidence for pattern matches
                            source=f"conversation_extraction",
                            timestamp=timestamp,
                            session_id=session_id
                        )
                        extracted.append(user_info)
        
        return extracted
    
    def _clean_extracted_value(self, value: str) -> str:
        """Clean and normalize extracted values."""
        # Remove common filler words and clean up
        value = re.sub(r'\b(really|very|quite|pretty|so|too|just|only|actually)\b', '', value, flags=re.IGNORECASE)
        
        # Remove trailing words that indicate end of meaningful content
        value = re.sub(r'\b(and stuff|and things|and all that|etc\.?|and more)\s*$', '', value, flags=re.IGNORECASE)
        
        # Remove common sentence endings
        value = re.sub(r'\b(right now|these days|nowadays|recently|lately)\s*$', '', value, flags=re.IGNORECASE)
        
        # Clean up punctuation and whitespace
        value = re.sub(r'\s+', ' ', value)  # Normalize whitespace
        value = value.strip(' .,!?;:')
        
        # Don't store overly long extractions (probably not user info)
        if len(value) > 100:
            return ""
            
        # Don't store very short extractions that are likely meaningless
        if len(value) < 2:
            return ""
            
        return value
    
    def store_user_info(self, user_info_list: List[UserInfo]) -> int:
        """
        Store extracted user information in database.
        
        Args:
            user_info_list: List of UserInfo objects to store
            
        Returns:
            Number of items successfully stored
        """
        if not user_info_list:
            return 0
            
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        stored_count = 0
        for info in user_info_list:
            try:
                c.execute("""
                    INSERT OR REPLACE INTO user_info 
                    (category, key, value, confidence, source, timestamp, session_id, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    info.category,
                    info.key, 
                    info.value,
                    info.confidence,
                    info.source,
                    info.timestamp.isoformat(),
                    info.session_id
                ))
                stored_count += 1
            except Exception as e:
                print(f"Error storing user info: {e}")
                
        conn.commit()
        conn.close()
        
        return stored_count
    
    def get_user_info(self, category: str = None, key: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve user information from database.
        
        Args:
            category: Filter by category (optional)
            key: Filter by specific key (optional)
            
        Returns:
            List of user info dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        query = "SELECT * FROM user_info WHERE active = 1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
            
        if key:
            query += " AND key = ?"
            params.append(key)
            
        query += " ORDER BY timestamp DESC"
        
        c.execute(query, params)
        results = [dict(row) for row in c.fetchall()]
        
        conn.close()
        return results
    
    def build_user_context(self, query: str = "") -> str:
        """
        Build relevant user context for AI responses.
        This replaces RAG search for user-specific information.
        
        Args:
            query: Current user query to find relevant context
            
        Returns:
            Formatted user context string
        """
        # Get all active user info
        user_info = self.get_user_info()
        
        if not user_info:
            return ""
            
        # Group by category for better organization
        categorized = {}
        for info in user_info:
            category = info['category']
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(info)
        
        # Build formatted context
        context_parts = ["**User Information:**"]
        
        for category, items in categorized.items():
            if items:
                context_parts.append(f"\n{category.title()}s:")
                for item in items[:5]:  # Limit to prevent context bloat
                    key = item['key'].replace('_', ' ').title()
                    value = item['value']
                    context_parts.append(f"- {key}: {value}")
        
        return "\n".join(context_parts)
    
    def cleanup_old_conversations(self, session_ids_to_clean: List[str]) -> int:
        """
        Delete old conversation chunks after user info extraction.
        This is the key function that implements session cleanup.
        
        Args:
            session_ids_to_clean: List of session IDs to remove from vector DB
            
        Returns:
            Number of conversation chunks deleted
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Delete conversation chunks for specified sessions
        deleted_count = 0
        for session_id in session_ids_to_clean:
            c.execute("""
                DELETE FROM memories 
                WHERE metadata LIKE '%"type": "conversation_chunk"%'
                AND metadata LIKE ?
            """, (f'%"session_id": "{session_id}"%',))
            deleted_count += c.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def process_session_for_cleanup(self, session_id: str) -> Tuple[int, int]:
        """
        Extract user info from a session and then clean it up.
        This is the complete workflow replacing save_memory.
        
        Args:
            session_id: Session to process
            
        Returns:
            Tuple of (extracted_info_count, deleted_conversations_count)
        """
        # Get all conversation chunks for this session
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT content, metadata FROM memories 
            WHERE metadata LIKE '%"session_id": "' || ? || '"%'
            AND metadata LIKE '%"type": "conversation_chunk"%'
        """, (session_id,))
        
        conversations = c.fetchall()
        conn.close()
        
        # Extract user info from conversations
        all_extracted = []
        for content, metadata_str in conversations:
            # Parse conversation content to extract messages
            # This is a simplified version - in practice you'd parse the formatted conversation
            messages = self._parse_conversation_content(content, session_id)
            extracted = self.extract_user_info_from_conversation(messages)
            all_extracted.extend(extracted)
        
        # Store extracted user info
        stored_count = self.store_user_info(all_extracted)
        
        # Clean up old conversations
        deleted_count = self.cleanup_old_conversations([session_id])
        
        return stored_count, deleted_count
    
    def _parse_conversation_content(self, content: str, session_id: str) -> List[Dict[str, Any]]:
        """
        Parse formatted conversation content back to message list.
        This is a helper for processing existing conversations.
        """
        messages = []
        
        # Simple regex to extract user messages from formatted conversation
        user_pattern = r'\[[\d:]+\] User: (.+?)(?=\n\[[\d:]+\] Assistant:|\n\n|$)'
        user_matches = re.findall(user_pattern, content, re.DOTALL)
        
        for match in user_matches:
            messages.append({
                'role': 'user',
                'content': match.strip(),
                'session_id': session_id,
                'timestamp': datetime.now()
            })
            
        return messages

def test_user_info_extraction():
    """Test the UserInfo extraction system."""
    print("Testing UserInfo extraction system...")
    
    manager = UserInfoManager()
    
    # Test conversation messages
    test_messages = [
        {
            'role': 'user',
            'content': 'Hi, my name is John and I love pizza on Fridays',
            'session_id': 'test_session',
            'timestamp': datetime.now()
        },
        {
            'role': 'user', 
            'content': 'My favorite color is blue but I actually prefer green now',
            'session_id': 'test_session',
            'timestamp': datetime.now()
        },
        {
            'role': 'user',
            'content': 'I work as a software engineer and I want to learn French',
            'session_id': 'test_session', 
            'timestamp': datetime.now()
        }
    ]
    
    # Extract user info
    extracted = manager.extract_user_info_from_conversation(test_messages)
    
    print(f"Extracted {len(extracted)} pieces of user information:")
    for info in extracted:
        print(f"  {info.category}: {info.key} = {info.value}")
    
    # Store and retrieve
    stored = manager.store_user_info(extracted)
    print(f"Stored {stored} items")
    
    # Test retrieval
    preferences = manager.get_user_info(category='preference')
    print(f"Found {len(preferences)} preferences")
    
    # Test context building
    context = manager.build_user_context()
    print(f"User context:\n{context}")

if __name__ == "__main__":
    test_user_info_extraction()
