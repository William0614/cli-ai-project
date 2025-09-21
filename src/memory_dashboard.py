#!/usr/bin/env python3
"""
Memory Dashboard - Web UI for visualizing AI memory system
Shows user profile, sessions, vector storage, and memory statistics
"""

from flask import Flask, render_template, jsonify
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any
import os

app = Flask(__name__)

class MemoryDashboard:
    def __init__(self, db_path: str = "agent_memory.db"):
        self.db_path = db_path
    
    def get_user_profile(self) -> Dict[str, List[Dict]]:
        """Get all user information grouped by category."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT category, key, value, confidence, timestamp, source
            FROM user_info 
            WHERE session_id = 'persistent_user_profile' AND active = 1
            ORDER BY category, timestamp DESC
        """)
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Group by category
        profile = {}
        for item in results:
            category = item['category']
            if category not in profile:
                profile[category] = []
            profile[category].append(item)
        
        return profile
    
    def get_session_history(self) -> List[Dict]:
        """Get all stored memory chunks - these are conversation sessions."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT id, content, metadata, timestamp
            FROM memories 
            ORDER BY timestamp DESC
        """)
        
        memories = []
        for row in cursor.fetchall():
            memory = dict(row)
            # Parse metadata to extract session info
            try:
                metadata = json.loads(memory['metadata'] or '{}')
                memory['metadata_parsed'] = metadata
                memory['session_id'] = metadata.get('session_id', f"memory_{memory['id']}")
                memory['reason'] = metadata.get('reason', 'stored')
            except:
                memory['metadata_parsed'] = {}
                memory['session_id'] = f"memory_{memory['id']}"
                memory['reason'] = 'unknown'
            memories.append(memory)
        
        conn.close()
        return memories
    
    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Get detailed content for a specific memory/session."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # If it's a memory ID, get that specific memory
        if session_id.startswith('memory_'):
            memory_id = session_id.replace('memory_', '')
            cursor = conn.execute("""
                SELECT content, metadata, timestamp
                FROM memories 
                WHERE id = ?
            """, (memory_id,))
        else:
            # Try to find by session_id in metadata
            cursor = conn.execute("""
                SELECT content, metadata, timestamp
                FROM memories 
                WHERE metadata LIKE ?
            """, (f'%{session_id}%',))
        
        messages = []
        for row in cursor.fetchall():
            content = row['content']
            timestamp = row['timestamp']
            
            # Try to parse the content as structured conversation
            try:
                # Content might be structured conversation data
                if content.startswith('Conversation:'):
                    # Extract conversation pairs
                    lines = content.split('\n')
                    current_role = None
                    current_content = []
                    
                    for line in lines[1:]:  # Skip "Conversation:" line
                        if line.startswith('user:') or line.startswith('User:'):
                            if current_role and current_content:
                                messages.append({
                                    'role': current_role,
                                    'content': '\n'.join(current_content),
                                    'timestamp': timestamp
                                })
                                current_content = []
                            current_role = 'user'
                            current_content = [line[5:].strip()]  # Remove "user:" prefix
                        elif line.startswith('assistant:') or line.startswith('Assistant:') or line.startswith('Jarvis:'):
                            if current_role and current_content:
                                messages.append({
                                    'role': current_role,
                                    'content': '\n'.join(current_content),
                                    'timestamp': timestamp
                                })
                                current_content = []
                            current_role = 'assistant'
                            # Remove prefix
                            for prefix in ['assistant:', 'Assistant:', 'Jarvis:']:
                                if line.startswith(prefix):
                                    current_content = [line[len(prefix):].strip()]
                                    break
                        else:
                            current_content.append(line)
                    
                    # Add final message
                    if current_role and current_content:
                        messages.append({
                            'role': current_role,
                            'content': '\n'.join(current_content),
                            'timestamp': timestamp
                        })
                else:
                    # Single content block
                    messages.append({
                        'role': 'system',
                        'content': content,
                        'timestamp': timestamp
                    })
            except:
                # Fallback: treat as single message
                messages.append({
                    'role': 'system',
                    'content': content,
                    'timestamp': timestamp
                })
        
        conn.close()
        return messages
    
    def get_vector_stats(self) -> Dict:
        """Get vector database statistics from memories table."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Get total memories with embeddings
        cursor = conn.execute("SELECT COUNT(*) as total FROM memories WHERE embedding IS NOT NULL")
        total_embeddings = cursor.fetchone()['total']
        
        # Get memories by reason/type
        cursor = conn.execute("""
            SELECT 
                CASE 
                    WHEN metadata LIKE '%overflow%' THEN 'overflow'
                    WHEN metadata LIKE '%exit%' THEN 'session_end'
                    WHEN metadata LIKE '%flush%' THEN 'manual_flush'
                    ELSE 'other'
                END as type,
                COUNT(*) as count
            FROM memories 
            GROUP BY type
            ORDER BY count DESC
        """)
        
        by_type = [dict(row) for row in cursor.fetchall()]
        
        # Get recent memories
        cursor = conn.execute("""
            SELECT content, metadata, timestamp
            FROM memories 
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        
        recent = []
        for row in cursor.fetchall():
            item = dict(row)
            # Truncate content for display
            content = item['content']
            if len(content) > 100:
                content = content[:100] + "..."
            item['content'] = content
            recent.append(item)
        
        conn.close()
        
        return {
            'total_embeddings': total_embeddings,
            'by_type': by_type,
            'recent': recent
        }
    
    def get_memory_stats(self) -> Dict:
        """Get overall memory system statistics."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        stats = {}
        
        # User info stats
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_user_info,
                COUNT(DISTINCT category) as categories,
                AVG(confidence) as avg_confidence
            FROM user_info WHERE active = 1
        """)
        stats['user_info'] = dict(cursor.fetchone())
        
        # Memory stats (conversations stored as memories)
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_memories,
                MIN(timestamp) as first_memory,
                MAX(timestamp) as last_memory,
                AVG(LENGTH(content)) as avg_content_length
            FROM memories
        """)
        stats['memories'] = dict(cursor.fetchone())
        
        # Vector stats (memories with embeddings)
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_embeddings,
                COUNT(*) * 100.0 / (SELECT COUNT(*) FROM memories) as embedding_percentage
            FROM memories WHERE embedding IS NOT NULL
        """)
        stats['vectors'] = dict(cursor.fetchone())
        
        conn.close()
        return stats

dashboard = MemoryDashboard()

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/user-profile')
def api_user_profile():
    """API endpoint for user profile data."""
    return jsonify(dashboard.get_user_profile())

@app.route('/api/sessions')
def api_sessions():
    """API endpoint for session history."""
    return jsonify(dashboard.get_session_history())

@app.route('/api/session/<session_id>')
def api_session_messages(session_id):
    """API endpoint for messages in a specific session."""
    return jsonify(dashboard.get_session_messages(session_id))

@app.route('/api/vector-stats')
def api_vector_stats():
    """API endpoint for vector database statistics."""
    return jsonify(dashboard.get_vector_stats())

@app.route('/api/memory-stats')
def api_memory_stats():
    """API endpoint for overall memory statistics."""
    return jsonify(dashboard.get_memory_stats())

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("🚀 Memory Dashboard starting...")
    print("📊 View your AI's memory at: http://localhost:5001")
    print("📁 Database:", os.path.abspath(dashboard.db_path))
    
    app.run(debug=True, host='0.0.0.0', port=5001)
