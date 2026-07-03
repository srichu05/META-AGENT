# Mini Meta-Agent Search for Math Word Problems and Automated Multi-Agent Debate System

A comprehensive AI-powered system that uses multiple specialized agents to solve math word problems through collaborative reasoning and RAG (Retrieval-Augmented Generation) technology.

## Features

- **Meta-Agent Architecture**: Coordinates multiple specialized solver agents
- **RAG Implementation**: Uses vector store for retrieving similar problems to enhance solving
- **Multi-Agent Debate**: Agents debate solutions to find the best approach
- **Web Interface**: Modern React-like interface built with vanilla JavaScript
- **Free API Integration**: Supports multiple free LLM APIs (Hugging Face, OpenAI, Groq, Cohere, Anthropic)
- **Persistent Storage**: JSON and CSV databases for problems and solutions
- **Real-time Analysis**: Problem type classification and contextual hints

## 📁 Project Structure

```
Meta_Agent_Math_Debate_System/
├── BACKEND/
│   ├── main.py                 # Main entry point and CLI
│   ├── app.py                  # Flask web application
│   ├── config.py               # Configuration and API keys
│   ├── requirements.txt        # Python dependencies
│   ├── agents/
│   │   ├── math_solver.py      # Individual solver agents
│   │   ├── judge_agent.py      # Solution evaluation agent
│   │   └── retriever_agent.py  # RAG retrieval agent
│   ├── models/
│   │   ├── meta_agent.py       # Main meta-agent coordinator
│   │   └── debate_system.py    # Debate orchestration
│   ├── rag/
│   │   ├── vector_store.py     # Vector storage and similarity search
│   │   ├── embeddings.py       # Text embeddings
│   │   └── retrieval.py        # Document retrieval logic
│   ├── utils/
│   │   ├── api_client.py       # Multi-API client wrapper
│   │   ├── data_processor.py   # Data loading and processing
│   │   └── logger.py           # Logging configuration
│   └── data/
│       ├── math_problems.json  # Sample math problems
│       └── sample_problems.csv # CSV format problems
├── FRONTEND/
│   ├── index.html              # Main web interface
│   ├── style.css               # Styling and responsive design
│   ├── script.js               # Frontend JavaScript logic
│   └── requirements.txt        # Frontend dependencies
├── database/
│   ├── problems.json           # Problem database
│   ├── solutions.csv           # Solutions database
│   └── debate_history.json     # Debate records
└── README.md                   # This file
```

## 🛠️ Installation and Setup

### Prerequisites
- Python 3.8+
- Git

### Step 1: Clone Repository
```bash
git clone <repository-url>
cd Meta_Agent_Math_Debate_System
```

### Step 2: Backend Setup
```bash
cd BACKEND
pip install -r requirements.txt
```

### Step 3: Configure API Keys
Edit `config.py` and add your free API keys:

```python
# Get free API keys from:
# Hugging Face: https://huggingface.co/settings/tokens
# OpenAI: https://platform.openai.com/api-keys
# Groq: https://console.groq.com/keys
# Cohere: https://dashboard.cohere.ai/api-keys
# Anthropic: https://console.anthropic.com/

# Set as environment variables or update config.py directly
HUGGING_FACE_API_KEY = "your_key_here"
OPENAI_API_KEY = "your_key_here"
GROQ_API_KEY = "your_key_here"
COHERE_API_KEY = "your_key_here"
ANTHROPIC_API_KEY = "your_key_here"
```

### Step 4: Run Backend Server
```bash
python main.py --server
# Or for interactive mode:
python main.py --interactive
```

### Step 5: Frontend Setup
```bash
cd ../FRONTEND
# Option 1: Python server
python -m http.server 8000

# Option 2: Direct browser
# Open index.html in your browser

# Option 3: Node.js (if available)
npx live-server
```

## 🚀 Usage

### Web Interface
1. Open `http://localhost:8000` in your browser
2. Choose from tabs: Problem Solver, Agent Debate, Problem Analysis, System Stats
3. Enter math problems and get AI-powered solutions

### Command Line Interface
```bash
# Solve a single problem
python main.py --problem "A store sells apples for $2 per kg. If John buys 5 kg, how much does he pay?"

# Use debate mode
python main.py --problem "Tom has 24 marbles..." --debate --rounds 3

# Analyze problem type
python main.py --problem "Find the area of a circle with radius 5" --analyze

# Interactive mode
python main.py --interactive

# System statistics
python main.py --stats
```

### API Endpoints
- `POST /api/solve` - Solve math problem
- `POST /api/debate` - Run agent debate
- `POST /api/analyze` - Analyze problem
- `GET /api/stats` - System statistics
- `POST /api/similar` - Find similar problems
- `POST /api/add_problem` - Add new problem

## 🎯 Key Components

### Meta-Agent System
- **MetaAgent**: Orchestrates multiple specialized agents
- **MathSolverAgent**: Individual problem-solving agents with different approaches
- **JudgeAgent**: Evaluates and ranks solutions
- **RetrieverAgent**: Handles RAG retrieval of similar problems

### RAG Implementation
- **Vector Store**: Stores problem embeddings for similarity search
- **Embeddings**: Uses free embedding APIs for text vectorization
- **Retrieval**: Finds contextually similar problems to enhance solving

### Multi-Agent Debate
- Agents propose initial solutions
- Multiple rounds of critique and improvement
- Judge selects the best final solution
- Complete debate history tracking

## 🆓 Free APIs Used

The system supports multiple free API tiers:

1. **Hugging Face**: 1000 requests/month free
2. **OpenAI**: $5 free credits for new accounts
3. **Groq**: Generous free tier
4. **Cohere**: 100 API calls/month free
5. **Anthropic**: Free trial credits

## 📊 Problem Types Supported

- Arithmetic problems
- Algebra and equations
- Geometry calculations
- Word problems
- Percentage calculations
- Fractions and decimals
- Time and distance
- Money and cost problems
- Basic probability

## 🔧 Customization

### Adding New Agent Types
Create new agent classes inheriting from base agents:

```python
class CustomMathAgent(MathSolverAgent):
    def _determine_solving_style(self):
        return "custom_approach"
    
    def _create_solving_prompt(self, problem, context):
        return f"Custom prompt for: {problem}"
```

### Extending Problem Types
Add new types in `config.py`:

```python
PROBLEM_TYPES = [
    "arithmetic", "algebra", "geometry", "statistics", "calculus"
]
```

### Custom RAG Sources
Extend the vector store with domain-specific problems:

```python
await retriever_agent.expand_knowledge_base(custom_problems)
```

## 🚨 Troubleshooting

### Common Issues

1. **API Key Errors**
   - Ensure all API keys are correctly set
   - Check rate limits and quotas
   - Verify API key permissions

2. **Import Errors**
   - Install all requirements: `pip install -r requirements.txt`
   - Check Python version compatibility

3. **Frontend Connection Issues**
   - Ensure backend is running on port 5000
   - Check CORS configuration
   - Verify API endpoints are accessible

### Logs
Check logs in the `logs/` directory for detailed error information.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m "Description"`
4. Push to branch: `git push origin feature-name`
5. Submit a Pull Request

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🎓 Educational Use

This system is designed for:
- AI/ML education and research
- Understanding multi-agent systems
- Learning RAG implementation
- Studying collaborative AI problem-solving
- Mathematics education support

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for errors
3. Create an issue on the repository
4. Ensure all API keys are properly configured

---

**Note**: This system is designed for educational purposes and uses free API tiers. For production use, consider upgrading to paid API plans for better performance and reliability.