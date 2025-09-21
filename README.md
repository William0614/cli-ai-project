# CLI AI Project

An intelligent command-line assistant with advanced ReAct reasoning, vision capabilities, and sophisticated memory management.

## 🚀 Features

### Core AI Capabilities
- **ReAct-Style Reasoning**: Advanced thought-action-observation loops with intelligent task progression  
- **Task Memory System**: Prevents redundant actions and maintains context across multi-step tasks
- **Reflexion Engine**: Self-correcting AI with progress analysis and repetition detection
- **Smart Tool Execution**: Intelligent tool selection with error recovery and validation

### Vision & Image Processing
- **Image Classification**: Multi-model support (VLM, DINOv3)
- **Image Similarity Search**: DINOv3-powered clustering for efficient image sorting
- **Batch Image Processing**: Optimized workflows for organizing large image collections
- **Species/Object Recognition**: Advanced image analysis with detailed descriptions

### Memory & Context Management  
- **Hybrid Memory Architecture**: Combines recent history with vector-based long-term storage
- **Task Continuity Detection**: Intelligent recognition of task continuation vs new tasks
- **User Preference Learning**: Automatically adapts to user patterns and preferences
- **Context-Aware RAG**: Semantic search through conversation history

### System Integration
- **Cross-Platform Support**: macOS, Linux, Windows with OS-specific optimizations
- **Directory Synchronization**: Shared working directory state across all components
- **Voice Input Support**: Speech-to-text with Whisper integration
- **Extensible Tool System**: Modular architecture for adding new capabilities

## Agent Architecture
![CLI AI Agent System Architecture](https://github.com/William0614/cli-ai-project/blob/feat/agent-workspace/assets/cli-ai-agent.png?raw=true)


## 📁 Enhanced Project Structure

```
cli-ai-project/
├── src/cli_ai/              # Main package
│   ├── core/              
│   │   ├── ai_engine.py     # ReAct engine with reflexion
│   │   └── prompts.py
│   ├── agents/            
│   │   ├── memory_system.py # Vector memory with FAISS
│   │   └── user_info.py     # User preference learning
│   ├── tools/              
│   │   ├── executor.py      # Enhanced tool execution engine
│   │   ├── tools.py
│   │   ├── vision/          
│   │   │   ├── similarity.py    # DINOv3 image clustering
│   │   │   └── local_models.py  # Multi-model vision support
│   │   ├── audio/           # Speech processing
│   │   └── system/          # OS and file operations
│   └── utils/               
│       ├── directory_manager.py  # Shared directory state
│       ├── task_continuity.py    # Context-aware task detection
│       ├── task_progress.py      # Progress analysis & loop prevention
│       ├── database.py           # Enhanced vector storage
│       └── os_helpers.py         # Cross-platform compatibility
├── tests/                   
├── main.py                  # Application entry point
└── Configuration files...
```

## 🛠️ Installation

### Prerequisites

- **Python 3.8+** (Python 3.10+ recommended)
- **OpenAI API key**

### Quick Setup

1. **Clone and enter directory:**
   ```bash
   git clone https://github.com/William0614/cli-ai-project.git
   cd cli-ai-project
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Add your OpenAI API key to .env file:
   # OPENAI_API_KEY=your_api_key_here
   ```

4. **Run the application:**
   ```bash
   python main.py
   ```

### Development Installation

```bash
# Install in development mode
pip install -e .

# Install optional dependencies for enhanced features
pip install torch torchvision  # For local vision models
pip install faiss-cpu          # For vector similarity search
```

## 🚀 Usage Examples

### Basic Conversation
```
$ python main.py
> Hello! Can you help me organize my project files?

I'd be happy to help organize your project files! Let me first see what files you have in your current directory...
```

### Advanced Image Sorting
```
> Can you sort the images in assets/images by animal species?

I'll analyze and group your images by species using visual similarity clustering...

Sorted by species:
   - Tigers: img1.jpg, img3.jpg, img7.jpg (3 images)  
   - Deer: img2.jpg, img5.jpg (2 images)
   - Birds: img4.jpg, img6.jpg (2 images)
```

### Voice Input Support
```
# Enable voice input
> \voice
[Transcribes speech and executes command]
```

## 🎯 Key Capabilities

### Smart Task Management
- **Context Preservation**: Remembers context across conversations  
- **Task Continuity**: "Add error handling" → continues previous task
- **Progress Tracking**: Prevents redundant actions and infinite loops
- **Multi-step Workflows**: Handles complex tasks requiring multiple actions

### Advanced Image Processing
- **Species Classification**: Automatically identifies animals in images
- **Visual Similarity Clustering**: Groups related images efficiently  
- **Batch Processing**: Handles large image collections optimally
- **Multiple Vision Models**: VLM, DINOv3,

### Intelligent Memory System
- **Hybrid Architecture**: Recent history + long-term vector storage
- **RAG Integration**: Searches past conversations for relevant context
- **User Preference Learning**: Adapts to your communication style
- **Session Continuity**: Maintains context across program restarts

## 🔧 Configuration

### Environment Variables

```bash
# Core Configuration
OPENAI_API_KEY=your_api_key_here          # Required for vision features
DEBUG_PROMPTS=true                        # Show detailed AI reasoning

# Memory System  
MAX_RECENT_MESSAGES=20                    # Recent memory limit
VECTOR_SEARCH_LIMIT=3                     # RAG search results
MEMORY_DB_PATH=./agent_memory.db          # Memory database location

# Vision Models
USE_OPENAI_VISION=false                   # Use OpenAI vs local models
VISION_MODEL=dinov2                       # Local vision model choice
SIMILARITY_THRESHOLD=0.7                  # Image similarity threshold

# Performance
TOKEN_BUDGET_LIMIT=4000                   # Max context tokens
RESPONSE_TIMEOUT=30                       # Max response time (seconds)
```

### Debug Mode

Enable detailed debugging to see the AI's reasoning process:

```bash
DEBUG_PROMPTS=true python main.py
```

This shows:
- Complete system prompts sent to the AI
- Token usage and optimization
- Task memory and progress analysis  
- Reflexion decision-making process


### Memory Overflow Management
```
Conversation reaches 20 messages →
System: [Moves old messages to vector database]
AI: [Continues with recent context + RAG from vector storage]
```

### Key Optimizations
- **Bounded Memory**: Recent message limit prevents context bloat
- **Smart RAG**: Only retrieves relevant historical context
- **Repetition Detection**: Prevents infinite loops and redundant actions
- **Progressive Task Execution**: Builds efficiently on previous work

### Development Mode
```bash
# Enable development features
DEBUG_PROMPTS=true python main.py

# Monitor system performance
python memory_dashboard.py  # View memory usage statistics
```

### Adding New Tools
```python
# Create new tool in src/cli_ai/tools/
def my_new_tool(arg1: str, arg2: int) -> dict:
    """Tool description for AI understanding"""
    # Implementation
    return {"status": "Success", "result": "..."}

# Register in tools.py
tools_schema.append({
    "name": "my_new_tool",
    "description": "What this tool does",
    "parameters": {...}
})
```


## 📝 License

This project is licensed under the MIT License. See `LICENSE` file for details.

---
