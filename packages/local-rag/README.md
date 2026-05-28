# Local-RAG CLI

A simple CLI tool to search and ask questions about your local markdown documentation using RAG (Retrieval-Augmented Generation).

This package is part of the `utils-workspace`.

## Setup

1. **Install dependencies**:
   From the **root** of the `utils` workspace, run:
   ```bash
   uv sync
   ```

2. **Configure API Key**:
   Create a `.env` file in this directory (`packages/local-rag/`) and add your Gemini API key:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

Run commands from the **root** of the workspace. Use the `--directory` (or `-C`) flag to ensure the local `.env` is loaded.

### 1. Ingest Documentation
```bash
uv run --directory packages/local-rag local-rag ingest /path/to/your/docs
```

### 2. Query
```bash
uv run --directory packages/local-rag local-rag query "How do I setup the project?"
```

## Architecture
1. **Ingestion**: Files are read, split into chunks, and embedded using a local model.
2. **Storage**: Chunks and embeddings are stored in ChromaDB.
3. **Retrieval**: When you ask a question, the query is embedded and the most relevant chunks are retrieved.
4. **Generation**: The retrieved chunks are sent to Gemini 1.5 Flash along with your question to generate a precise answer.
