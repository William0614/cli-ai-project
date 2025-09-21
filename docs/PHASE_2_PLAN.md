# Phase 2: Vector Database Integration for Overflow Storage and RAG

## Objective
Integrate overflow conversations into the existing vector database system for semantic search and retrieval.

## Current State
✅ **Phase 1 Complete**: Session memory with bounded 20-message limit working
✅ **Overflow working**: Conversations moved in pairs preserving integrity
✅ **Format optimized**: Clean readable message format

## Phase 2 Goals

### 1. **Vector Storage Integration**
- Connect overflow messages to existing FAISS vector database
- Store conversations with semantic embeddings
- Maintain conversation metadata (timestamps, session IDs, context)

### 2. **RAG (Retrieval Augmented Generation)**
- Search vector database for relevant past conversations
- Inject relevant context into AI prompts
- Smart filtering to avoid noise and irrelevant results

### 3. **Seamless Integration**
- No interruption to current conversation flow
- Automatic background storage and retrieval
- Performance optimization for search speed

## Implementation Plan

### Step 1: Connect Overflow to Vector Database
```python
# In main.py, replace TODO comments with actual vector storage
if overflow_messages:
    conversation_text = session_memory.format_conversation_for_storage(overflow_messages)
    # NEW: Store in vector database
    vector_memory.store_conversation_chunk(overflow_messages, metadata)
```

### Step 2: Create Vector Memory Manager
```python
class VectorMemoryManager:
    def store_conversation_chunk(self, messages, metadata)
    def search_relevant_context(self, query, limit=3)
    def get_conversation_summary(self, session_id)
```

### Step 3: Integrate RAG into AI Context
```python
# In ai_engine.py, enhance context building
relevant_context = vector_memory.search_relevant_context(user_query)
enhanced_prompt = system_prompt + recent_history + relevant_context
```

## Expected Benefits
- **Cross-session learning**: AI remembers relevant past conversations
- **Intelligent context**: Only relevant past context, not noise
- **Persistent knowledge**: Important insights preserved across sessions
- **Smart search**: Semantic similarity, not just keyword matching

## Files to Modify
- `src/cli_ai/memory/vector_manager.py` (new)
- `main.py` (integrate vector storage)
- `src/cli_ai/core/ai_engine.py` (RAG integration)
- `src/cli_ai/memory/__init__.py` (export new components)

Ready to start implementation?
