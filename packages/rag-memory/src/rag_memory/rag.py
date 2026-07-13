from rag_memory.config import get_embedding_model, get_pinecone_index, get_bm25_encoder, get_cross_encoder, logger


def query_documents(query: str, company_filter: str = None) -> str:
    """Perform hybrid search (dense + sparse) on Pinecone index, rerank results with a local CrossEncoder, and return top 5 chunks.
    
    This illustrates:
    1. Sparse retrieval: BM25 keyword matching representation.
    2. Dense retrieval: Semantic similarity representation.
    3. Hybrid combination: Querying both dense and sparse representations.
    4. Reranking: Recalculating query-document relevance using a deep learning CrossEncoder model on a larger candidate pool.
    """
    logger.info(f"RAG query started: '{query}' (company_filter={company_filter})")
    
    # 1. Generate dense query embedding
    embedding_model = get_embedding_model()
    dense_vector = embedding_model.embed_query(query)
    
    # 2. Generate sparse query vector
    bm25 = get_bm25_encoder()
    sparse_vector = bm25.encode_queries(query)
    
    # 3. Retrieve a larger candidate pool (top 15) using Pinecone hybrid query
    index = get_pinecone_index()
    filter_dict = {"company": company_filter} if company_filter else None
    
    logger.info("Executing Pinecone hybrid query (dense + sparse)...")
    try:
        results = index.query(
            vector=dense_vector,
            sparse_vector=sparse_vector,
            top_k=15,  # Retrieve more candidates for reranking
            namespace="documents",
            filter=filter_dict,
            include_metadata=True
        )
    except Exception as e:
        logger.error(f"Error querying documents namespace in Pinecone: {e}")
        return ""

    matches = results.get("matches", [])
    if not matches:
        logger.info("No matching documents found in hybrid search.")
        return ""
        
    logger.info(f"Hybrid search retrieved {len(matches)} initial candidates.")

    # Extract text content and build pairs for reranking
    candidates = []
    for match in matches:
        metadata = match.get("metadata", {})
        text = metadata.get("text", "")
        if text:
            candidates.append({"text": text, "metadata": metadata, "initial_score": match.get("score")})
            
    if not candidates:
        return ""
        
    # 4. Rerank candidates using local Cross-Encoder
    logger.info("Applying local CrossEncoder reranking model to candidates...")
    cross_encoder = get_cross_encoder()
    
    # Build query-document pairs
    pairs = [(query, cand["text"]) for cand in candidates]
    
    # Compute similarity scores
    try:
        rerank_scores = cross_encoder.predict(pairs)
        # Assign new scores to candidates
        for idx, score in enumerate(rerank_scores):
            candidates[idx]["rerank_score"] = float(score)
            
        # Sort by rerank score descending
        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        # Log comparison of top scores for transparency
        logger.info("Reranking completed. Sample scores:")
        for i, cand in enumerate(candidates[:3]):
            initial_score = cand.get("initial_score")
            init_score_str = f"{initial_score:.4f}" if initial_score is not None else "N/A"
            logger.info(f"  Rank {i+1}: Rerank Score = {cand['rerank_score']:.4f} | Initial Hybrid Score = {init_score_str} | Content: {cand['text'][:60]}...")
            
    except Exception as e:
        logger.error(f"Failed to rerank candidates: {e}. Falling back to hybrid search ranking.")
        # Fallback to initial ordering if reranking fails
        pass

    # Select the top 5 chunks
    top_candidates = candidates[:5]
    
    chunks = [cand["text"] for cand in top_candidates]
    combined_context = "\n\n".join(chunks)
    logger.info(f"Returned top {len(chunks)} chunks after hybrid search + reranking.")
    return combined_context
