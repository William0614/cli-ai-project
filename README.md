# CLI AI Project

An intelligent command-line assistant with vision capabilities, speech-to-text, and advanced AI reasoning.

## 🚀 Features

- **AI-Powered Command Execution**: Intelligent parsing and execution of natural language commands
- **Vision Capabilities**: Image analysis and classification using OpenAI Vision API or local models
- **Speech-to-Text**: Voice input support with Whisper
- **Memory System**: Conversation history and context retention
- **Tool Integration**: Extensible tool system for various capabilities
- **Debug Features**: Optional prompt debugging with token counting

## 📁 Project Structure

```
cli-ai-project/
├── src/cli_ai/              # Main package
│   ├── core/                # Core AI logic
│   │   ├── ai_engine.py     # Main AI reasoning engine
│   │   └── prompts.py       # System prompts and templates
│   ├── agents/              # Specialized agents
│   │   ├── terminal_bench_agent.py  # Terminal benchmark integration
│   │   └── memory_system.py # Memory management
│   ├── tools/               # Tool implementations
│   │   ├── executor.py      # Tool execution engine
│   │   ├── tools.py         # Core tools registry
│   │   ├── vision/          # Vision-related tools
│   │   │   ├── image_classifier.py  # Image classification
│   │   │   ├── similarity.py        # Image similarity search
│   │   │   └── local_models.py      # Local model support
│   │   ├── audio/           # Audio processing tools
│   │   │   └── speech_to_text.py    # Speech recognition
│   │   └── system/          # System-level tools
│   └── utils/               # Utilities and helpers
│       ├── database.py      # Database operations
│       ├── os_helpers.py    # OS detection and helpers
│       └── spinner.py       # UI utilities
├── tests/                   # Test files
├── docs/                    # Documentation
├── assets/                  # Images, audio samples, screenshots
├── examples/                # Usage examples
├── scripts/                 # Build/deployment scripts
├── main.py                  # Application entry point
├── setup.py                 # Package installation
├── requirements.txt         # Dependencies
└── .env.example            # Environment configuration template
```

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- OpenAI API key (optional, for vision features)

### Setup

1. **Clone the repository:**
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
   # Edit .env with your API keys and preferences
   ```

4. **Install the package (optional):**
   ```bash
   pip install -e .
   ```

## 🚀 Usage

### Basic Usage

```bash
python main.py
```

### With Debug Features

```bash
DEBUG_PROMPTS=true python main.py
```

### Voice Input

The application supports voice input through speech-to-text. Simply speak your commands when prompted.

### Vision Features

Describe images or find similar images in your directories:
```
"What's in this image: path/to/image.jpg"
"Find images similar to path/to/reference.jpg"
```

## 🔧 Configuration

### Environment Variables

- `DEBUG_PROMPTS`: Enable detailed prompt debugging (default: false)
- `USE_OPENAI_VISION`: Use OpenAI Vision API vs local models (default: false)
- `OPENAI_API_KEY`: Your OpenAI API key
- `LOCAL_API_URL`: Local model server URL
- `LOCAL_MODEL_NAME`: Local model name

### Debug Features

When `DEBUG_PROMPTS=true`, the application will display:
- Complete system prompts sent to the LLM
- Token counts for optimization
- Detailed reasoning steps

## 📊 Performance

The project includes comprehensive token counting and optimization features:
- Accurate token measurement using tiktoken
- Prompt optimization guidance
- Memory usage tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.
