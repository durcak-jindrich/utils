# Meeting Summarizer

A LangChain-based multi-step workflow for summarizing meeting notes, extracting action items, and classifying their priority using Groq's LLM (Llama 3).

## Setup

1. **Install Dependencies**:
   If you are in the workspace root, dependencies are managed by `uv`.
   ```bash
   uv sync
   ```

2. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your API keys.
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   - `GROQ_API_KEY`: Your Groq API key (from [Groq Console](https://console.groq.com/)).
   - `LANGCHAIN_API_KEY`: Your LangSmith API key (from [LangSmith](https://smith.langchain.com/)).
   - `LANGCHAIN_TRACING_V2=true`: Enables observability.

## Usage

### Run the main script
You can run the example script to verify the integration:
```bash
cd packages/meeting-summarizer
uv run src/meeting_summarizer/main.py
```

### Run Tests
```bash
cd packages/meeting-summarizer
uv run pytest
```
*Note: The integration test will be skipped unless a valid `GROQ_API_KEY` is provided in the environment or `.env` file.*

## Workflow details

The `MeetingSummarizer` uses LangChain's Expression Language (LCEL) to execute a three-step chain:
1. **Summarize**: Condenses raw meeting notes.
2. **Extract Tasks**: Identifies specific action items from the summary.
3. **Classify Priority**: Assigns High/Medium/Low priority to each task.

All steps are traced in LangSmith if `LANGCHAIN_TRACING_V2` is set to `true`.
