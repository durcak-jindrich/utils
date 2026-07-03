from rag_memory.config import (
    get_embedding_model,
    get_pinecone_index,
    GROQ_API_KEY,
    PINECONE_API_KEY,
    is_placeholder,
    logger,
)


def summarize_conversation(history: list) -> str:
    """Summarize the conversation history list into a single paragraph via Groq."""
    if not history:
        return ""

    # Format history into a readable transcript
    formatted_lines = []
    for msg in history:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        formatted_lines.append(f"{role}: {content}")
    history_text = "\n".join(formatted_lines)

    # Fallback to mock summary if Groq key is a placeholder
    if is_placeholder(GROQ_API_KEY):
        logger.info("[Mock LLM] Summarizing history.")
        # Create a deterministic mock summary that includes some content from history for verification
        last_user_content = ""
        for m in reversed(history):
            if m.get("role") == "user":
                last_user_content = m.get("content", "")
                break
        
        summary = (
            f"Conversation Summary: The user discussed various issues. "
            f"The latest topic of interest was: '{last_user_content}'."
        )
        return summary

    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage, SystemMessage

        chat = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name="llama-3.3-70b-versatile",
            temperature=0.0
        )

        system_prompt = (
            "You are a professional assistant. Write a concise, one-paragraph summary of the following conversation history. "
            "Highlight key decisions, context, topics, user preferences, and action items. "
            "Do not include any greeting or conversational filler. Output only the summary paragraph."
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Conversation History:\n{history_text}")
        ]

        response = chat.invoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.error(f"Error in summarize_conversation via Groq: {e}")
        # Return a simple fallback summary
        last_msg = history[-1].get("content", "") if history else ""
        return f"System fallback summary: User and assistant discussed: {last_msg}."


def save_session_summary(user_id: str, session_id: str, history: list) -> str:
    """Summarize conversation via Groq, embed summary, and upsert to namespace memory with session_id."""
    if not history:
        logger.warning(f"Empty history for session {session_id}. Skipping summary.")
        return ""

    logger.info(f"Generating summary for session {session_id}...")
    summary_text = summarize_conversation(history)
    if not summary_text:
        return ""

    logger.info(f"Embedding summary for session {session_id}...")
    embedding_model = get_embedding_model()
    vector = embedding_model.embed_query(summary_text)

    # Namespace: memory
    # Vector ID: session_id (overwrites on repeat calls, preventing duplicates)
    metadata = {
        "user_id": user_id,
        "session_id": session_id,
        "text": summary_text,
        "doc_type": "memory"
    }

    index = get_pinecone_index()
    logger.info(f"Upserting session memory for {session_id} to namespace 'memory'...")
    index.upsert(
        vectors=[(session_id, vector, metadata)],
        namespace="memory"
    )
    logger.info(f"Successfully saved session summary for {session_id}.")
    return summary_text


def get_relevant_memory(user_id: str, query: str) -> str:
    """Query namespace memory filtered by user_id, returns top 3 results above threshold or empty string."""
    logger.info(f"Retrieving relevant memory for user {user_id}...")
    embedding_model = get_embedding_model()
    query_vector = embedding_model.embed_query(query)

    index = get_pinecone_index()
    try:
        results = index.query(
            vector=query_vector,
            top_k=3,
            namespace="memory",
            filter={"user_id": user_id},
            include_metadata=True
        )
    except Exception as e:
        logger.error(f"Error querying memory namespace: {e}")
        return ""

    matches = results.get("matches", [])
    if not matches:
        logger.info(f"No previous memories found for user {user_id}.")
        return ""

    # Filter by similarity score threshold to avoid retrieving irrelevant past turns
    # In mock mode, deterministic embeddings of different texts have low similarity, so we bypass it.
    is_mock = is_placeholder(PINECONE_API_KEY)
    threshold = 0.0 if is_mock else 0.70
    memories = []
    for match in matches:
        score = match.get("score", 0.0)
        # Cosine similarity thresholding
        if score < threshold:
            logger.info(f"Discarding memory match {match.get('id')} due to low similarity score: {score:.4f}")
            continue
            
        metadata = match.get("metadata", {})
        text = metadata.get("text", "")
        if text:
            memories.append(text)

    if not memories:
        if not is_mock:
            logger.info(f"No memories passed the similarity threshold ({threshold}) for user {user_id}.")
        return ""

    combined_memory = "\n\n".join(memories)
    logger.info(f"Retrieved {len(memories)} memory snippets for user {user_id} above threshold.")
    return combined_memory
