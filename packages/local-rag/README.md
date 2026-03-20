# Local-RAG CLI

A simple CLI tool to search and ask questions about your local markdown documentation using RAG (Retrieval-Augmented Generation).

## Features
- **Local Embeddings**: Uses `sentence-transformers` for free, local text embedding.
- **Local Vector Store**: Uses `ChromaDB` for efficient document retrieval.
- **Gemini 1.5 Flash**: Uses Google's Gemini for high-quality answers based on retrieved context.
- **Simple CLI**: Easy ingestion and querying.

## Setup

1. **Install dependencies**:
   ```bash
   cd packages/local-rag
   uv sync
   ```

2. **Configure API Key**:
   Create a `.env` file in `packages/local-rag/` and add your Gemini API key:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

### 1. Ingest Documentation
To index your markdown files:
```bash
uv run local-rag ingest /path/to/your/docs
```
Use `--clear` to reset the database:
```bash
uv run local-rag ingest /path/to/your/docs --clear
```

### 2. Query
Ask a question about your docs:
```bash
uv run local-rag query "How do I setup the project?"
```

## Architecture
1. **Ingestion**: Files are read, split into chunks, and embedded using a local model.
2. **Storage**: Chunks and embeddings are stored in ChromaDB.
3. **Retrieval**: When you ask a question, the query is embedded and the most relevant chunks are retrieved.
4. **Generation**: The retrieved chunks are sent to Gemini 1.5 Flash along with your question to generate a precise answer.
