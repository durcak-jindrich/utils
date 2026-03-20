import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from .ingest import Ingestor
from .db import ChromaManager
from .ai import AIHandler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

console = Console()

def ingest_docs(args):
    """Ingest markdown documentation into ChromaDB."""
    ingestor = Ingestor()
    db_manager = ChromaManager()
    ai_handler = AIHandler()

    target_path = Path(args.path)
    if not target_path.exists():
        console.print(f"[red]Error: Path {args.path} does not exist.[/red]")
        return

    console.print(f"[blue]Ingesting documents from {target_path}...[/blue]")
    
    docs = []
    if target_path.is_file():
        docs = ingestor.process_file(target_path)
    else:
        docs = ingestor.process_directory(target_path)

    if not docs:
        console.print("[yellow]No markdown documents found or processed.[/yellow]")
        return

    # To avoid re-embedding everything if we're just adding a few files
    # we could implement an incremental check, but for this simple tool
    # we'll just clear and re-index if requested or if it's the first time.
    if args.clear:
        db_manager.clear()

    # Batching to show progress and avoid large single transactions
    batch_size = 50
    with Progress() as progress:
        task = progress.add_task("[cyan]Embedding chunks...", total=len(docs))
        
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i + batch_size]
            contents = [d["content"] for d in batch]
            ids = [d["id"] for d in batch]
            metadatas = [d["metadata"] for d in batch]
            
            embeddings = ai_handler.get_embeddings(contents)
            db_manager.add_chunks(contents, ids, metadatas, embeddings)
            
            progress.update(task, advance=len(batch))

    console.print(f"[green]Successfully ingested {len(docs)} chunks from {target_path} into ChromaDB.[/green]")

def query_docs(args):
    """Query ChromaDB and generate an answer from Gemini."""
    db_manager = ChromaManager()
    ai_handler = AIHandler()

    console.print(f"[blue]Searching for relevant context...[/blue]")
    
    query_embeddings = ai_handler.get_embeddings([args.query])
    results = db_manager.query(query_embeddings, n_results=args.top_k)

    if not results["documents"] or not results["documents"][0]:
        console.print("[yellow]No relevant documents found for your query.[/yellow]")
        return

    # Join results into context
    context = "\n\n".join(results["documents"][0])
    sources = set([meta["source"] for meta in results["metadatas"][0]])

    console.print(f"[blue]Generating answer using Gemini...[/blue]")
    answer = ai_handler.generate_answer(args.query, context)

    console.print(Panel(answer, title="[bold green]Answer[/bold green]", expand=False))
    
    console.print("\n[bold]Sources:[/bold]")
    for src in sources:
        console.print(f"- {src}")

def main():
    parser = argparse.ArgumentParser(description="Local-RAG CLI: Ask questions about your markdown docs.")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest markdown files into ChromaDB")
    ingest_parser.add_argument("path", help="Path to markdown file or directory")
    ingest_parser.add_argument("--clear", action="store_true", help="Clear the database before ingestion")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query your documentation")
    query_parser.add_argument("query", help="The question you want to ask")
    query_parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve")

    args = parser.parse_args()

    if args.command == "ingest":
        ingest_docs(args)
    elif args.command == "query":
        query_docs(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
