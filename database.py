
import sqlite3
import json
import numpy as np
import faiss
from typing import List, Dict, Any, Optional

DB_FILE = "agent_memory.db"
FAISS_INDEX = None  # Global FAISS index
EMBEDDING_DIM = 384  # Dimension of 'all-MiniLM-L6-v2' embeddings

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    """Initializes the database with the required tables and loads/builds the FAISS index."""
    global FAISS_INDEX
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

    # Load existing embeddings and build FAISS index
    c.execute("SELECT id, embedding FROM memories WHERE embedding IS NOT NULL")
    rows = c.fetchall()
    
    if rows:
        # Filter out rows with None embeddings and convert to numpy array
        valid_embeddings = []
        valid_ids = []
        for row in rows:
            if row['embedding'] is not None:
                try:
                    embedding_array = np.frombuffer(row['embedding'], dtype=np.float32)
                    if embedding_array.shape[0] == EMBEDDING_DIM:
                        valid_embeddings.append(embedding_array)
                        valid_ids.append(row['id'])
                    else:
                        print(f"Warning: Embedding for ID {row['id']} has incorrect dimension {embedding_array.shape[0]}. Expected {EMBEDDING_DIM}. Skipping.")
                except ValueError as e:
                    print(f"Warning: Could not convert embedding for ID {row['id']} to numpy array: {e}. Skipping.")
        
        if valid_embeddings:
            embeddings_matrix = np.array(valid_embeddings).astype('float32')
            FAISS_INDEX = faiss.IndexFlatL2(EMBEDDING_DIM)
            FAISS_INDEX.add(embeddings_matrix)
            # Store mapping from FAISS index to SQLite ID
            FAISS_INDEX.sqlite_ids = valid_ids
            print(f"FAISS index built with {FAISS_INDEX.ntotal} embeddings.")
        else:
            FAISS_INDEX = faiss.IndexFlatL2(EMBEDDING_DIM)
            FAISS_INDEX.sqlite_ids = []
            print("No valid embeddings found to build FAISS index. Initializing empty index.")
    else:
        FAISS_INDEX = faiss.IndexFlatL2(EMBEDDING_DIM)
        FAISS_INDEX.sqlite_ids = []
        print("No existing memories. Initializing empty FAISS index.")
    
    conn.close()

def save_memory(content: str, embedding: Optional[bytes] = None, metadata: Optional[Dict[str, Any]] = None):
    """Saves a memory to the database and adds its embedding to the FAISS index."""
    global FAISS_INDEX
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO memories (content, embedding, metadata) VALUES (?, ?, ?)",
        (content, embedding, json.dumps(metadata) if metadata else None)
    )
    memory_id = c.lastrowid
    conn.commit()
    conn.close()

    if embedding is not None and FAISS_INDEX is not None:
        try:
            embedding_array = np.frombuffer(embedding, dtype=np.float32).reshape(1, -1)
            if embedding_array.shape[1] == EMBEDDING_DIM:
                FAISS_INDEX.add(embedding_array)
                FAISS_INDEX.sqlite_ids.append(memory_id)
            else:
                print(f"Warning: New embedding for ID {memory_id} has incorrect dimension {embedding_array.shape[1]}. Expected {EMBEDDING_DIM}. Not added to FAISS index.")
        except ValueError as e:
            print(f"Warning: Could not convert new embedding for ID {memory_id} to numpy array: {e}. Not added to FAISS index.")


def recall_memories(query_embedding: Optional[bytes] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Recalls memories from the database using FAISS for semantic search."""
    global FAISS_INDEX
    conn = get_db_connection()
    memories = []

    if query_embedding is not None and FAISS_INDEX is not None and FAISS_INDEX.ntotal > 0:
        try:
            query_vector = np.frombuffer(query_embedding, dtype=np.float32).reshape(1, -1)
            if query_vector.shape[1] != EMBEDDING_DIM:
                print(f"Error: Query embedding dimension {query_vector.shape[1]} does not match FAISS index dimension {EMBEDDING_DIM}.")
                return []

            # Perform FAISS search
            distances, faiss_indices = FAISS_INDEX.search(query_vector, limit)
            
            # Retrieve memories from SQLite based on FAISS results
            # faiss_indices can contain -1 if not enough results are found
            sqlite_ids_to_fetch = [FAISS_INDEX.sqlite_ids[idx] for idx in faiss_indices[0] if idx != -1]
            
            if sqlite_ids_to_fetch:
                # Use a parameterized query to fetch multiple IDs
                placeholders = ','.join('?' * len(sqlite_ids_to_fetch))
                c = conn.cursor()
                c.execute(f"SELECT * FROM memories WHERE id IN ({placeholders}) ORDER BY timestamp DESC", sqlite_ids_to_fetch)
                memories = [dict(row) for row in c.fetchall()]
                # Sort memories by their original FAISS search order for relevance
                # Create a mapping from sqlite_id to memory dict for efficient sorting
                memory_map = {m['id']: m for m in memories}
                sorted_memories = []
                for faiss_idx in faiss_indices[0]:
                    if faiss_idx != -1:
                        sqlite_id = FAISS_INDEX.sqlite_ids[faiss_idx]
                        if sqlite_id in memory_map:
                            sorted_memories.append(memory_map[sqlite_id])
                memories = sorted_memories
            else:
                print("FAISS search returned no valid results.")
        except Exception as e:
            print(f"Error during FAISS search or retrieval: {e}")
            # Fallback to recent memories if FAISS fails
            c = conn.cursor()
            c.execute("SELECT * FROM memories ORDER BY timestamp DESC LIMIT ?", (limit,))
            memories = [dict(row) for row in c.fetchall()]
    else:
        # If no query embedding or FAISS index not ready, fallback to recent memories
        c = conn.cursor()
        c.execute("SELECT * FROM memories ORDER BY timestamp DESC LIMIT ?", (limit,))
        memories = [dict(row) for row in c.fetchall()]
    
    conn.close()
    return memories

if __name__ == "__main__":
    initialize_db()
    print("Database initialized.")
    # Example usage (requires memory_system to generate embeddings)
    # from memory_system import save_memory, recall_memories
    # save_memory("The user's name is Jane Doe.", {"type": "declarative"})
    # save_memory("The user likes to read sci-fi books.", {"type": "declarative"})
    # recalled = recall_memories(query_embedding=b'some_embedding_bytes', limit=2)
    # print(recalled)

