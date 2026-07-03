from rag_memory.config import get_embedding_model, get_pinecone_index, logger


def query_documents(query: str, company_filter: str = None) -> str:
    """Embed query, search Pinecone namespace 'documents' with optional company metadata filter, return top 5 chunks."""
    logger.info(f"Querying documents for: '{query}' (company_filter={company_filter})")
    
    embedding_model = get_embedding_model()
    query_vector = embedding_model.embed_query(query)

    index = get_pinecone_index()
    
    # Set up filter if company_filter is provided
    filter_dict = {"company": company_filter} if company_filter else None

    try:
        results = index.query(
            vector=query_vector,
            top_k=5,
            namespace="documents",
            filter=filter_dict,
            include_metadata=True
        )
    except Exception as e:
        logger.error(f"Error querying documents namespace in Pinecone: {e}")
        return ""

    matches = results.get("matches", [])
    if not matches:
        logger.info("No matching documents found.")
        return ""

    chunks = []
    for match in matches:
        metadata = match.get("metadata", {})
        text = metadata.get("text", "")
        if text:
            chunks.append(text)

    if not chunks:
        return ""

    combined_context = "\n\n".join(chunks)
    logger.info(f"Retrieved {len(chunks)} relevant document chunks.")
    return combined_context
