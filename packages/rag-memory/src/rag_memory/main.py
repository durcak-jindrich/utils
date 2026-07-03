import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from rag_memory.config import logger
from rag_memory.ingest import run_ingest
from rag_memory.agent import run_agent
from rag_memory.session_store import (
    active_sessions,
    get_stale_sessions,
    remove_session,
)
from rag_memory.memory import save_session_summary


# Background task to monitor and clean up stale sessions
async def stale_session_monitor(interval_seconds: float = 300.0, stale_threshold_seconds: float = 1800.0):
    """Periodically check for stale sessions, summarize them, and remove them from memory."""
    logger.info(f"Stale session monitor started (interval: {interval_seconds}s, threshold: {stale_threshold_seconds}s).")
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            logger.info("Running stale sessions check...")
            
            stale_ids = get_stale_sessions(stale_threshold_seconds)
            for session_id in stale_ids:
                session_data = active_sessions.get(session_id)
                if not session_data:
                    continue
                
                user_id = session_data["user_id"]
                history = session_data["messages"]
                
                logger.info(f"Session '{session_id}' is stale. Saving summary and removing...")
                try:
                    # Summarize session
                    save_session_summary(user_id, session_id, history)
                except Exception as e:
                    logger.error(f"Error summarizing stale session {session_id}: {e}")
                
                # Always remove session from active store
                remove_session(session_id)
                logger.info(f"Removed stale session '{session_id}' from memory.")
                
        except asyncio.CancelledError:
            logger.info("Stale session monitor cancelled.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in stale session monitor: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the monitor task on startup
    monitor_task = asyncio.create_task(stale_session_monitor())
    yield
    # Cancel the monitor task on shutdown
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="RAG Memory Demo API",
    description="A FastAPI app showcasing Retrieval-Augmented Generation with episodic conversation memory.",
    version="0.1.0",
    lifespan=lifespan
)


# Input request schemas
class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str


@app.post("/ingest")
def ingest_data():
    """Trigger ingestion of local customer and meeting notes CSV data into Pinecone."""
    try:
        count = run_ingest()
        return {"status": "success", "message": f"Successfully ingested {count} documents."}
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    """Send a message to the RAG memory agent and receive an answer."""
    try:
        answer = run_agent(
            user_id=request.user_id,
            session_id=request.session_id,
            message=request.message
        )
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Chat execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


def start():
    """Start the FastAPI application using uvicorn."""
    import uvicorn
    logger.info("Starting rag-memory FastAPI server...")
    uvicorn.run("rag_memory.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
