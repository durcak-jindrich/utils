from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from rag_memory.config import GROQ_API_KEY, is_placeholder, logger
from rag_memory.session_store import init_session, update_session
from rag_memory.memory import get_relevant_memory, save_session_summary
from rag_memory.rag import query_documents


def run_agent(user_id: str, session_id: str, message: str) -> str:
    """Run the agent chain for a message.
    
    1. Retrieves memory context.
    2. Retrieves document context.
    3. Injects both into system prompt.
    4. Invokes ChatGroq (llama-3.3-70b-versatile).
    5. Saves assistant response.
    6. Triggers save_session_summary after every 5 user messages.
    """
    logger.info(f"Running agent for session {session_id}, user {user_id}...")
    
    # 1. Initialize or fetch current session
    session = init_session(session_id, user_id)
    
    # 2. Retrieve past memory & documents context
    past_memory = get_relevant_memory(user_id, message)
    doc_context = query_documents(message)
    
    # 3. Add current user message to session store
    update_session(session_id, {"role": "user", "content": message}, user_id)
    
    # 4. Generate answer
    if is_placeholder(GROQ_API_KEY):
        logger.info("[Mock LLM] Generating response.")
        # Return a mock response containing retrieved context/memory for verification in tests
        response_text = (
            f"Mock response for session {session_id}. "
            f"Retrieved memory: '{past_memory}'. "
            f"Retrieved document context: '{doc_context}'."
        )
    else:
        try:
            from langchain_groq import ChatGroq
            
            chat = ChatGroq(
                api_key=GROQ_API_KEY,
                model_name="llama-3.3-70b-versatile",
                temperature=0.7
            )
            
            system_content = (
                "You are an expert sales and account representative assistant.\n"
                "You help manage client accounts and meetings. Answer the user's questions "
                "based on the relevant historical memory and document context provided below.\n\n"
                "=== RELEVANT PAST MEMORY ===\n"
                f"{past_memory if past_memory else 'No previous memory available.'}\n\n"
                "=== RELEVANT DOCUMENT CONTEXT ===\n"
                f"{doc_context if doc_context else 'No document context available.'}\n\n"
                "Answer the user's prompt directly, concisely, and professionally. If the context does not contain the answer, "
                "state that it is not in the logs but do your best to assist."
            )
            
            # Reconstruct conversation history from store (except the last message which we add manually)
            messages = [SystemMessage(content=system_content)]
            for msg in session["messages"][:-1]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))
                    
            messages.append(HumanMessage(content=message))
            
            response = chat.invoke(messages)
            response_text = response.content.strip()
        except Exception as e:
            logger.error(f"Error in ChatGroq chain: {e}")
            response_text = f"Error generating response. Retrieved context size: {len(doc_context)} chars."
            
    # 5. Save assistant response to session store
    update_session(session_id, {"role": "assistant", "content": response_text}, user_id)
    
    # 6. Trigger summary after every 5 user messages
    history = session["messages"]
    user_msgs = [m for m in history if m["role"] == "user"]
    if len(user_msgs) > 0 and len(user_msgs) % 5 == 0:
        logger.info(f"Session {session_id} has reached {len(user_msgs)} user messages. Triggering session summary...")
        save_session_summary(user_id, session_id, history)
        
    return response_text
