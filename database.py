
import sqlite3
import json
from typing import List, Dict, Any, Optional

DB_FILE = "agent_memory.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    """Initializes the database with the required tables."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            embedding BLOB,
            metadata TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_memory(content: str, embedding: Optional[bytes] = None, metadata: Optional[Dict[str, Any]] = None):
    """Saves a memory to the database."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO memories (content, embedding, metadata) VALUES (?, ?, ?)",
        (content, embedding, json.dumps(metadata) if metadata else None)
    )
    conn.commit()
    conn.close()

def recall_memories(query_embedding: Optional[bytes] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Recalls memories from the database, optionally performing a semantic search."""
    conn = get_db_connection()
    c = conn.cursor()
    if query_embedding:
        # This is a placeholder for a real vector search.
        # In a real implementation, you would use a vector search library like FAISS or a database with vector support.
        # For now, we'll just return the most recent memories.
        c.execute("SELECT * FROM memories ORDER BY timestamp DESC LIMIT ?", (limit,))
    else:
        c.execute("SELECT * FROM memories ORDER BY timestamp DESC LIMIT ?", (limit,))
    
    memories = [dict(row) for row in c.fetchall()]
    conn.close()
    return memories

if __name__ == "__main__":
    initialize_db()
    print("Database initialized.")
