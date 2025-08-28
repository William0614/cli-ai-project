"""
Vector Memory Manager for Smart Memory Phase 2
Handles overflow storage and RAG retrieval using existing FAISS infrastructure
"""

import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from ..utils import database as db

# Use the same model as the existing system for consistency
MODEL = SentenceTransformer('all-MiniLM-L6-v2')


class VectorMemoryManager:
    """
    Manages long-term conversation storage and retrieval using vector embeddings.
    Integrates with existing FAISS infrastructure for semantic search.
    """
    
    def __init__(self):
        """Initialize vector memory manager."""
        # Ensure database is initialized
        db.initialize_db()
        self.model = MODEL
        
    def _generate_embedding(self, text: str) -> bytes:
        """Generate vector embedding for text content."""
        embedding = self.model.encode(text)
        return embedding.tobytes()
    
    def store_conversation_chunk(
        self, 
        messages: List[Dict[str, Any]], 
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store a chunk of conversation messages in vector database.
        
        Args:
            messages: List of message objects from session memory
            metadata: Additional metadata about the conversation chunk
            
        Returns:
            True if storage successful, False otherwise
        """
        try:
            # Format conversation for storage and embedding
            conversation_text = self._format_conversation_for_embedding(messages)
            
            # Create comprehensive metadata
            chunk_metadata = {
                "type": "conversation_chunk",
                "message_count": len(messages),
                "session_id": messages[0].get("session_id") if messages else None,
                "timestamp": datetime.now().isoformat(),
                "start_time": messages[0].get("timestamp").isoformat() if messages else None,
                "end_time": messages[-1].get("timestamp").isoformat() if messages else None,
                "roles": [msg.get("role") for msg in messages],
                "source": "session_overflow"
            }
            
            # Add any additional metadata
            if metadata:
                chunk_metadata.update(metadata)
            
            # Generate embedding
            embedding = self._generate_embedding(conversation_text)
            
            # Store in database using existing infrastructure
            db.save_memory(conversation_text, embedding, chunk_metadata)
            
            return True
            
        except Exception as e:
            print(f"[Vector Memory] Error storing conversation chunk: {e}")
            return False
    
    def search_relevant_context(
        self, 
        query: str, 
        limit: int = 3,
        min_similarity: float = 0.6,
        temporal_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant past conversations using semantic similarity with temporal precedence.
        Newer conversations get higher priority to handle conflicting information.
        
        Args:
            query: Current user query or conversation context
            limit: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            temporal_weight: Weight given to recency (0-1, higher = more temporal bias)
            
        Returns:
            List of relevant conversation contexts, prioritized by recency
        """
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            
            # Search using existing recall system
            raw_results = db.recall_memories(query_embedding, limit * 3)  # Get extra to apply temporal weighting
            
            # Filter and format results with temporal precedence
            relevant_results = []
            now = datetime.now()
            
            for result in raw_results:
                # Parse metadata
                metadata = json.loads(result.get('metadata', '{}')) if result.get('metadata') else {}
                
                # Only include conversation chunks (not individual memories)
                if metadata.get('type') == 'conversation_chunk':
                    
                    # Calculate base similarity score (placeholder - could enhance with actual cosine similarity)
                    base_similarity = 0.8  # Placeholder
                    
                    # Apply temporal weighting - newer conversations get higher scores
                    temporal_boost = 0
                    try:
                        timestamp_str = result.get('timestamp', '')
                        if timestamp_str:
                            result_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            # Calculate hours since the conversation
                            hours_ago = (now - result_time).total_seconds() / 3600
                            # Apply exponential decay: more recent = higher weight
                            temporal_boost = temporal_weight * (0.9 ** (hours_ago / 24))  # Decay over days
                    except Exception as time_error:
                        print(f"[Vector Memory] Error parsing timestamp: {time_error}")
                    
                    final_similarity = base_similarity + temporal_boost
                    
                    if final_similarity >= min_similarity:
                        formatted_result = {
                            "content": result['content'],
                            "similarity_score": final_similarity,
                            "base_similarity": base_similarity,
                            "temporal_boost": temporal_boost,
                            "metadata": metadata,
                            "timestamp": result.get('timestamp'),
                            "id": result.get('id')
                        }
                        relevant_results.append(formatted_result)
            
            # Sort by final similarity score (semantic + temporal) - newer content wins ties
            relevant_results.sort(key=lambda x: (x['similarity_score'], x['temporal_boost']), reverse=True)
            
            return relevant_results[:limit]
            
        except Exception as e:
            print(f"[Vector Memory] Error searching context: {e}")
            return []
    
    def _format_conversation_for_embedding(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format conversation messages for vector embedding.
        Creates a readable, searchable text representation.
        """
        if not messages:
            return ""
        
        # Extract session info
        session_id = messages[0].get("session_id", "unknown")
        start_time = messages[0].get("timestamp")
        
        formatted_lines = [
            f"Conversation Session: {session_id}",
            f"Time: {start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'unknown'}",
            ""
        ]
        
        # Format each message
        for msg in messages:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))
            timestamp = msg.get("timestamp")
            
            # Clean up content if it's complex
            if isinstance(content, dict):
                content = str(content)
            
            time_str = timestamp.strftime('%H:%M:%S') if timestamp else ""
            formatted_lines.append(f"[{time_str}] {role.title()}: {content}")
        
        return "\n".join(formatted_lines)
    
    def get_conversation_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary of all stored conversations for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Summary information or None if not found
        """
        try:
            # This would require querying the database for specific session
            # For now, return placeholder
            return {
                "session_id": session_id,
                "total_chunks": 0,
                "earliest_timestamp": None,
                "latest_timestamp": None,
                "total_messages": 0
            }
            
        except Exception as e:
            print(f"[Vector Memory] Error getting conversation summary: {e}")
            return None
    
    def build_rag_context(self, current_query: str, session_context: str = "") -> str:
        """
        Build RAG (Retrieval Augmented Generation) context for AI prompts.
        Uses temporal precedence: newer conversations get higher priority.
        
        Args:
            current_query: User's current query
            session_context: Current session context
            
        Returns:
            Formatted context string for AI prompt
        """
        # Search for relevant past conversations using temporal precedence
        relevant_conversations = self.search_relevant_context(
            current_query, 
            limit=2,
            temporal_weight=0.4  # Give significant weight to recency
        )
        
        if not relevant_conversations:
            return ""
        
        # Format for AI context with temporal information
        context_lines = ["**Relevant Past Conversations:**"]
        
        for i, conv in enumerate(relevant_conversations, 1):
            metadata = conv.get('metadata', {})
            timestamp = metadata.get('timestamp', 'unknown time')
            similarity = conv.get('similarity_score', 0)
            temporal_boost = conv.get('temporal_boost', 0)
            
            # Show recency information
            recency_indicator = "(recent)" if temporal_boost > 0.1 else "(older)"
            
            context_lines.append(f"\n{i}. From {timestamp} {recency_indicator} [score: {similarity:.2f}]:")
            # Truncate long conversations for context
            content = conv['content']
            if len(content) > 500:
                content = content[:500] + "..."
            context_lines.append(content)
        
        return "\n".join(context_lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored vector memory."""
        try:
            # Get total conversation chunks
            conn = db.get_db_connection()
            c = conn.cursor()
            c.execute("""
                SELECT COUNT(*) as total, 
                       MIN(timestamp) as earliest,
                       MAX(timestamp) as latest
                FROM memories 
                WHERE metadata LIKE '%conversation_chunk%'
            """)
            result = c.fetchone()
            conn.close()
            
            return {
                "total_conversation_chunks": result['total'] if result else 0,
                "earliest_conversation": result['earliest'] if result else None,
                "latest_conversation": result['latest'] if result else None,
                "faiss_index_size": db.FAISS_INDEX.ntotal if db.FAISS_INDEX else 0
            }
            
        except Exception as e:
            print(f"[Vector Memory] Error getting stats: {e}")
            return {"error": str(e)}


# Testing and example usage
if __name__ == "__main__":
    # Example usage
    vector_manager = VectorMemoryManager()
    
    # Test conversation storage
    test_messages = [
        {
            "role": "user",
            "content": "What's the weather like?",
            "timestamp": datetime.now(),
            "session_id": "test_session",
            "message_id": 1
        },
        {
            "role": "assistant", 
            "content": "I can't check current weather, but I can help you find weather information.",
            "timestamp": datetime.now(),
            "session_id": "test_session",
            "message_id": 2
        }
    ]
    
    # Store test conversation
    success = vector_manager.store_conversation_chunk(test_messages)
    print(f"Storage successful: {success}")
    
    # Test search
    results = vector_manager.search_relevant_context("weather")
    print(f"Search results: {len(results)}")
    
    # Test RAG context building
    rag_context = vector_manager.build_rag_context("How's the weather today?")
    print(f"RAG context: {rag_context[:200]}...")
    
    # Get stats
    stats = vector_manager.get_stats()
    print(f"Vector memory stats: {stats}")
