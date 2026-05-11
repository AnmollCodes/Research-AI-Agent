
<div align="center">

# 🧠 ISEA v2.1 PRO
### Introspective Self-Evolving Autonomous Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Powered-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js-black.svg)](https://nextjs.org/)
[![Gemini](https://img.shields.io/badge/AI-Gemini%202.0-red.svg)](https://ai.google.dev/)
[![Status](https://img.shields.io/badge/Status-Active%20Development-success.svg)]()

<p align="center">
  <strong>Decides. Acts. Reflects. Evolves.</strong><br>
  A production-grade autonomous system that moves beyond simple prompting to demonstrate <br>
  <strong>graph-based reasoning, self-correction, human-in-the-loop control, and multi-modal intelligence.</strong>
</p>

[Report Bug](https://github.com/AnmollCodes/Research-AI-Agent/issues) • [Request Feature](https://github.com/AnmollCodes/Research-AI-Agent/issues) • [View Changelog](#-version-changelog)

</div>

---

## 🚀 The Paradigm Shift

Most AI projects today follow a linear path:  
`Prompt` → `LLM` → `Response`

**ISEA v2.0 breaks this mold.** It is designed to answer a deeper engineering question:
> _"How do we build an AI that can decide WHAT to do, evaluate its OWN performance, and improve WITHOUT human intervention?"_

This is **not a chatbot**. It is a **Reasoning Engine**.

---

## ⚡ What Makes This Unique?

| Feature | Typical Chatbot | 🧠 ISEA Agent |
|:---|:---:|:---:|
| **Control Flow** | Linear Script | **Dynamic Graph (DAG)** |
| **Tool Usage** | Hardcoded / Forced | **Decision-Driven** |
| **Logic** | "Always Answer" | **"Think, Plan, Execute"** |
| **Self-Correction** | ❌ None | **✅ Post-Run Reflection** |
| **Visibility** | Black Box | **✅ Live Neural Visualization** |
| **Safety** | ❌ None | **✅ Human-in-the-Loop Gate** |

---

## 🏗️ Architecture & Neural Flow

The system operates on a stateful graph where each node represents a distinct cognitive function.

```mermaid
graph TD
    User(User Input) --> Router{Router Node}
    Router -->|Simple Query| Chat(Chat Node)
    Router -->|Complex Request| Planner(Planner Node)
    Router -->|Explainability| Explain(Meta Node)
    
    Planner --> Executor{Executor Loop}
    Executor -->|Need Tool| Tools(Tool Node)
    Tools --> Executor
    Executor -->|Step Complete| Executor
    Executor -->|Plan Finished| Reporter(Reporter Node)
    
    Chat --> Validator{Validator Loop}
    Reporter --> Validator
    
    Validator -->|Pass| Final(Final Response)
    Validator -->|Fail / Improve| Reflector(Self-Reflection)
    Reflector -->|Update Strategy| Router
```

### 🧠 Core Nodes
1. **Router**: analyzing intent (Research vs. Chat vs. Explanation).
2. **Planner**: Decomposes complex goals into executable steps.
3. **Executor**: The "Agent" that uses tools (Search, Math, Code) to solve steps.
4. **Validator**: Critiques the output for accuracy and safety.
5. **Human Gate**: Intercepts sensitive actions (like saving files) for approval.

---

## 🎨 Immersive Visualization

We believe AI reasoning shouldn't be hidden. ISEA features a **cyberpunk-inspired dashboard** that exposes the agent's "brain" in real-time.

### 🖥️ Dashboard Features
- **Live Graph State**: Watch nodes light up as the agent "thinks".
- **Real-Time Telemetry**: Monitor token usage, latency, and context window.
- **Thought Stream**: See the raw internal monologue and decision paths.
- **Glassmorphism Spec**: Built with modern Tailwind + Framer Motion for a premium feel.

---

## 🛠️ Technology Stack

### Backend Impl.
- **Core Logic**: Python 3.10+
- **Orchestration**: LangGraph, LangChain
- **Intelligence**: Google Gemini 2.0 Flash / OpenAI GPT-4o
- **Search**: Tavily AI Search

### Frontend Impl.
- **Framework**: Next.js 15 (App Router)
- **Styling**: TailwindCSS v4 + Glassmorphism
- **Animations**: Framer Motion
- **3D Elements**: Three.js / React Three Fiber

---

## 🚦 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- API Keys: Google Gemini (or OpenAI), Tavily

### Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/AnmollCodes/Research-AI-Agent.git
   cd Research-AI-Agent
   ```

2. **Backend Setup**
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

4. **Environment Variables**
   Create a `.env` file in the root:
   ```env
   GOOGLE_API_KEY=your_key_here
   TAVILY_API_KEY=your_key_here
   ```

5. **Run the System**
   ```bash
   # Terminal 1 (Backend)
   python api.py
   
   # Terminal 2 (Frontend)
   cd frontend
   npm run dev
   ```

Access the dashboard at `http://localhost:3000`.

---

## ✨ v2.1 Latest Enhancements & Features

### 🆕 New in v2.1
- **Gemini 2.0 Flash Integration**: Upgraded to `gemini-2.0-flash-lite` for optimized performance (30 RPM free tier vs 15 RPM)
- **Enhanced Router Logic**: Improved intent classification with support for 4 distinct modes:
  - 📊 **research**: Deep analysis, reports, and complex multi-step queries
  - ⚡ **quick**: Simple Q&A, conversational responses, quick facts
  - 🤔 **explain**: Architecture & system explanations
  - 🎯 **action**: Real-world operations (email, calendar, Slack integration)

### 🔧 Core Improvements
- **Self-Reflection Engine**: Post-execution validation and strategy refinement
- **Human-in-Loop Validation**: Critical actions require human approval before execution
- **User Preference Learning**: `user_prefs.json` for personalized behavior adaptation
- **Real-Time Graph Visualization**: Live neural state visualization with cyberpunk aesthetic
- **Comprehensive Logging**: Full action trails and decision paths for debugging

### 🧪 Testing & Quality
- **Multi-Model Testing**: Support for both Gemini and GPT-4o backends
- **API Integration Tests**: Comprehensive test suites for all major components
- **Quota Management**: Intelligent rate limiting and quota monitoring
- **Debug Utilities**: Advanced diagnostic tools for troubleshooting

### 📱 Frontend Enhancements
- **Glassmorphism UI**: Modern design with TailwindCSS v4
- **Real-Time Telemetry**: Live token usage, latency, and context window monitoring
- **3D Background**: React Three Fiber integration for immersive experience
- **Responsive Dashboard**: Full mobile and desktop support

### 🔌 Integration Capabilities
- **Tavily AI Search**: Advanced web search and research capabilities
- **Zapier Integration**: Connect with 6,000+ apps for automation
- **FastAPI Backend**: RESTful API for programmatic access
- **Custom Tool Extension**: Easy framework to add new tools

---

## 📋 Version Changelog

### v2.1 (Current) - May 2026
- ✅ Upgraded to Gemini 2.0 Flash with lite variant for better rate limits
- ✅ Enhanced intent routing with mode-based logic
- ✅ Improved self-reflection and validation pipeline
- ✅ Better error handling and quota management
- ✅ User preference system integration
- ✅ Comprehensive documentation updates
- ✅ Multi-test framework for verification

### v2.0 - December 2025
- Graph-based reasoning engine with DAG architecture
- Dynamic tool usage and decision-driven execution
- Self-correction and reflection capabilities
- Live neural visualization dashboard
- Human-in-the-loop approval gates
- Initial Tavily AI integration
- FastAPI REST interface

---

## 🔮 Roadmap & Future Vision

- [ ] **Long-Term Memory**: Vector database integration (Pinecone/Chroma) for persistent context.
- [ ] **Multi-Modal Support**: Image analysis and generation nodes.
- [ ] **Swarm Mode**: Coordination between multiple specialized sub-agents.
- [ ] **Voice Interface**: Real-time voice interaction layer.
- [ ] **Advanced Analytics**: Performance dashboard with usage insights.
- [ ] **Knowledge Graph**: Ontology-based reasoning and relationship mapping.

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

<div align="center">

### Built with ❤️ and 🧠 by Anmol Agarwal

[LinkedIn](https://www.linkedin.com/in/anmol-agarwal25) • [Twitter](https://twitter.com/AgarwalA25) • [GitHub](https://github.com/AnmollCodes)

</div>
