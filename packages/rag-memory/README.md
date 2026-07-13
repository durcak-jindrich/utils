# RAG Memory Demo

A FastAPI application demonstrating Retrieval-Augmented Generation (RAG) with episodic conversation memory. It allows agents to retrieve company profiles and meeting notes, maintain active chat history, summarize discussions every 5 user messages, and save episodic summaries to a Pinecone memory namespace. A background task runs periodically to summarize and remove stale sessions (>30 minutes of inactivity).

This package is part of the `utils-workspace` monorepo.

## Features

1. **In-Memory Session Store**: Maintains session history, last activity timestamps, and tracks message count.
2. **FastAPI Endpoints**:
   - `POST /ingest`: Loads customer data and meeting notes from CSV files, fits a local BM25Encoder, generates both dense and sparse embeddings, and batch-upserts them to Pinecone (under namespace `documents`).
   - `POST /chat`: Accepts chat messages, queries relevant documents using hybrid search and reranking, queries episodic memory, and returns the response.
3. **Sparse-Dense Hybrid Search**:
   - **Dense Retrieval**: Captures overall semantic context and synonyms via OpenAI/Pinecone/local deterministic mock embeddings.
   - **Sparse Retrieval**: Uses a local BM25Encoder (from `pinecone-text`) to capture exact keyword matches (e.g. names, IDs, specific terms).
   - The system queries both models simultaneously to fetch the top 15 candidates.
4. **Local CrossEncoder Reranking**:
   - Retrieves the top 15 documents from the hybrid search and passes them to a local, open-source `sentence-transformers` Cross-Encoder model (`cross-encoder/ms-marco-MiniLM-L-6-v2`).
   - The cross-encoder evaluates the deep query-document interaction and scores candidates. The top 5 candidates are returned to the LLM.
5. **Episodic Memory System**:
   - Periodic summarization every 5 user messages.
   - Background monitor checks for sessions idle for >30 minutes, summarizes final details, saves to Pinecone namespace `memory`, and purges them.
   - Summaries are indexed and searchable, allowing future conversations to pull previous session contexts.
6. **Mock Mode Fallbacks**: Auto-detects placeholder keys and runs fully in-memory with deterministic local embeddings, mock BM25 indexing, and a mock overlap-based CrossEncoder reranker, enabling tests and dry-runs to execute instantly offline.

## Setup

1. **Install dependencies**:
   Run the following from the monorepo root to synchronize dependencies:
   ```bash
   uv sync
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in `packages/rag-memory/` (or copy `.env.example` to `.env`) and supply your API keys:
   ```env
   PINECONE_API_KEY=your_pinecone_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   PINECONE_INDEX_NAME=rag-memory-demo
   ```

   *Note: If no API keys are provided (or placeholder strings are left), the app automatically falls back to Mock mode for both Pinecone and LLM, enabling local dry-runs.*

3. **Pinecone Index Configuration**:
   If running in production, create a serverless index in your Pinecone console with:
   - **Dimension**: `1536`
   - **Metric**: `cosine`
   - **Name**: `rag-memory-demo`

## Running the Application

All commands must be executed from the **root** of the monorepo workspace.

### 1. Ingest Data
To ingest the sample customer profile and meeting note CSV datasets:
```bash
uv run --directory packages/rag-memory python -m rag_memory.ingest
```

### 2. Start the Server
Start the FastAPI server:
```bash
uv run --directory packages/rag-memory rag-memory-server
```
The server will start at `http://0.0.0.0:8000`.

### 3. API Usage

- **POST `/ingest`**:
  ```bash
  curl -X POST http://localhost:8000/ingest
  ```

- **POST `/chat`**:
  ```bash
  curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -d '{"user_id": "rep_001", "session_id": "session_001", "message": "What is the status of the Acme Corp renewal?"}'
  ```

## Running Tests

To run the integration tests:
```bash
uv run pytest packages/rag-memory/tests/
```
