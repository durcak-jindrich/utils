# Build Your First Local AI Agent: A Practical Introduction with Free Tools

This package demonstrates how to build a ReAct (Reasoning and Acting) agent using LangChain, Groq, and Anthropic.

## Prerequisites

- [uv](https://github.com/astral-sh/uv) installed
- Groq API Key (from [console.groq.com](https://console.groq.com/))
- Anthropic API Key (from [console.anthropic.com](https://console.anthropic.com/))

## Setup

1. Clone the repository and navigate to this directory:
   ```bash
   cd packages/ai-agent-tutorial
   ```

2. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

3. Add your API keys to the `.env` file:
   ```env
   GROQ_API_KEY=gsk_...
   ANTHROPIC_API_KEY=sk-ant-...
   ```

4. Install dependencies:
   ```bash
   uv sync
   ```

## Running the Agent

You can run the agent with either Groq or Anthropic.

### Using Groq (Free/Low cost)
```bash
uv run python src/ai_agent_tutorial/agent.py "latest developments in AI agents 2025" groq
```

### Using Anthropic Claude (Haiku)
```bash
uv run python src/ai_agent_tutorial/agent.py "latest developments in AI agents 2025" anthropic
```

## How it Works

The agent uses the **ReAct** pattern:
1. **Reason**: The model thinks about what it needs to do.
2. **Act**: It calls a tool (e.g., Search or Save to File).
3. **Observe**: It sees the result of the tool call.
4. **Repeat**: It continues until the task is complete.

Explicit logging is enabled so you can see every step of this loop in your terminal.

## Comparison

- **Groq (Llama 3.3 70B)**: Extremely fast inference, great for quick iterations.
- **Anthropic (Claude 3 Haiku)**: Very high reasoning quality for its size, often more reliable in following complex instructions.
