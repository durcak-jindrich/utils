import os
import uuid
from pathlib import Path
import pandas as pd
from rag_memory.config import get_embedding_model, get_pinecone_index, logger

# Path to the data directory relative to this package
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def load_customers_as_strings(file_path: Path) -> list[dict]:
    """Load customers.csv and convert each row to a natural language string and metadata."""
    if not file_path.exists():
        logger.error(f"Customers file not found at {file_path}")
        return []
    
    df = pd.read_csv(file_path)
    documents = []
    
    for _, row in df.iterrows():
        company = str(row["company"]).strip()
        industry = str(row["industry"]).strip()
        contract_value = str(row["contract_value"]).strip()
        renewal_date = str(row["renewal_date"]).strip()
        account_manager = str(row["account_manager"]).strip()
        
        text = (
            f"Company {company} operates in the {industry} industry. "
            f"The account contract value is ${contract_value} with a renewal date of {renewal_date}. "
            f"The assigned account manager is {account_manager}."
        )
        
        metadata = {
            "company": company,
            "industry": industry,
            "contract_value": float(row["contract_value"]) if pd.notnull(row["contract_value"]) else 0.0,
            "renewal_date": renewal_date,
            "account_manager": account_manager,
            "text": text,
            "doc_type": "customer_profile"
        }
        documents.append({"text": text, "metadata": metadata})
        
    return documents


def load_meeting_notes_as_strings(file_path: Path) -> list[dict]:
    """Load meeting_notes.csv and convert each row to a natural language string and metadata."""
    if not file_path.exists():
        logger.error(f"Meeting notes file not found at {file_path}")
        return []
        
    df = pd.read_csv(file_path)
    documents = []
    
    for _, row in df.iterrows():
        date = str(row["date"]).strip()
        company = str(row["company"]).strip()
        attendees = str(row["attendees"]).strip()
        summary = str(row["summary"]).strip()
        action_items = str(row["action_items"]).strip()
        
        text = (
            f"On {date}, a meeting was held regarding company {company}. "
            f"Attendees present: {attendees}. "
            f"Meeting Summary: {summary} "
            f"Action items agreed upon: {action_items}."
        )
        
        metadata = {
            "company": company,
            "date": date,
            "attendees": attendees,
            "summary": summary,
            "action_items": action_items,
            "text": text,
            "doc_type": "meeting_note"
        }
        documents.append({"text": text, "metadata": metadata})
        
    return documents


def run_ingest() -> int:
    """Run ingestion for both CSV files, embed rows, and upsert them to Pinecone."""
    logger.info("Starting data ingestion process...")
    
    customers_file = DATA_DIR / "customers.csv"
    meeting_notes_file = DATA_DIR / "meeting_notes.csv"
    
    # Load and convert all documents
    docs_to_ingest = []
    docs_to_ingest.extend(load_customers_as_strings(customers_file))
    docs_to_ingest.extend(load_meeting_notes_as_strings(meeting_notes_file))
    
    if not docs_to_ingest:
        logger.warning("No documents found to ingest.")
        return 0
        
    logger.info(f"Loaded {len(docs_to_ingest)} documents from CSV files. Generating embeddings...")
    
    # Get embedding model and batch embed all documents
    embedding_model = get_embedding_model()
    texts = [doc["text"] for doc in docs_to_ingest]
    
    # Batch embed all rows in one API call
    embeddings = embedding_model.embed_documents(texts)
    
    # Prepare vectors for Pinecone upsert
    vectors = []
    for i, doc in enumerate(docs_to_ingest):
        doc_id = f"doc_{uuid.uuid4().hex[:8]}_{i}"
        vectors.append((doc_id, embeddings[i], doc["metadata"]))
        
    # Get Pinecone index and upsert to "documents" namespace
    index = get_pinecone_index()
    logger.info(f"Upserting {len(vectors)} vectors to Pinecone 'documents' namespace...")
    
    index.upsert(vectors=vectors, namespace="documents")
    logger.info("Ingestion completed successfully.")
    return len(vectors)


if __name__ == "__main__":
    run_ingest()
