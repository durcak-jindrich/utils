import argparse
import logging
import os
import sys

import litellm
from crewai import Crew, Process
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, retry_if_exception_type, wait_exponential

from pr_reviewer.agents import (
    get_llm,
    create_security_reviewer,
    create_architecture_reviewer,
    create_code_quality_reviewer,
    create_documentation_reviewer,
    create_lead_reviewer,
)
from pr_reviewer.tasks import (
    create_security_review_task,
    create_architecture_review_task,
    create_code_quality_review_task,
    create_documentation_review_task,
    create_lead_review_task,
    create_optimized_review_task,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def log_retry_attempt(retry_state):
    logger.warning(
        f"Rate limit hit. Retrying in {retry_state.next_action.sleep:.2f} seconds... "
        f"Attempt {retry_state.attempt_number} of 5."
    )

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=15, max=60),
    retry=retry_if_exception_type(litellm.exceptions.RateLimitError),
    before_sleep=log_retry_attempt,
    reraise=True
)
def run_pr_review_workflow(title: str, description: str, changed_files: str) -> str:
    """Executes the CrewAI workflow to review a PR/MR.
    
    Args:
        title: The title of the PR.
        description: The description of the PR.
        changed_files: A formatted string containing files and their diffs.
        
    Returns:
        The consolidated markdown review report.
    """
    logger.info("Setting up CrewAI agents and tasks...")
    
    # 1. Initialize LLM
    llm = get_llm()
    
    # 2. Check if we should run in optimized token-saving mode
    optimized = os.getenv("OPTIMIZED_WORKFLOW", "true").lower() == "true"
    
    if optimized:
        logger.info("Executing OPTIMIZED 1-call review workflow...")
        lead_reviewer = create_lead_reviewer(llm)
        review_task = create_optimized_review_task(lead_reviewer)
        
        crew = Crew(
            agents=[lead_reviewer],
            tasks=[review_task],
            process=Process.sequential,
            verbose=True
        )
    else:
        logger.info("Executing FULL 5-agent sequential review workflow...")
        # Create agents
        security_reviewer = create_security_reviewer(llm)
        architecture_reviewer = create_architecture_reviewer(llm)
        code_quality_reviewer = create_code_quality_reviewer(llm)
        documentation_reviewer = create_documentation_reviewer(llm)
        lead_reviewer = create_lead_reviewer(llm)
        
        # Create tasks
        security_task = create_security_review_task(security_reviewer)
        architecture_task = create_architecture_review_task(architecture_reviewer)
        code_quality_task = create_code_quality_review_task(code_quality_reviewer)
        documentation_task = create_documentation_review_task(documentation_reviewer)
        
        # Lead review consolidates the others
        lead_task = create_lead_review_task(
            agent=lead_reviewer,
            context_tasks=[security_task, architecture_task, code_quality_task, documentation_task]
        )
        
        crew = Crew(
            agents=[
                security_reviewer,
                architecture_reviewer,
                code_quality_reviewer,
                documentation_reviewer,
                lead_reviewer
            ],
            tasks=[
                security_task,
                architecture_task,
                code_quality_task,
                documentation_task,
                lead_task
            ],
            process=Process.sequential,
            verbose=True
        )
    
    # Kickoff workflow
    inputs = {
        "title": title,
        "description": description,
        "changed_files": changed_files
    }
    
    logger.info("Executing review workflow...")
    result = crew.kickoff(inputs=inputs)
    
    logger.info("Review workflow completed successfully.")
    return str(result)

def format_sample_files(files) -> str:
    """Formats changed files for insertion into the LLM prompt."""
    formatted_files = []
    for file in files:
        formatted_files.append(f"### File: {file.filename}\n```diff\n{file.diff}\n```\n")
    return "\n".join(formatted_files)

def main():
    parser = argparse.ArgumentParser(
        description="Automated AI Pull Request Reviewer using CrewAI and Groq/Ollama."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--pr",
        choices=["security", "architecture", "code_quality", "documentation", "clean", "all"],
        help="Run review workflow on one of the flawed sample pull requests."
    )
    group.add_argument(
        "--webhook",
        action="store_true",
        help="Start the FastAPI GitLab webhook receiver server using Uvicorn."
    )
    group.add_argument(
        "--manual",
        action="store_true",
        help="Run manual review. Must provide --title, --description, and --changed-files."
    )
    
    parser.add_argument("--title", help="Title of the manual PR.")
    parser.add_argument("--description", help="Description of the manual PR.")
    parser.add_argument("--changed-files", help="Path to a text file containing the code changes/diffs.")
    parser.add_argument("--port", type=int, default=8000, help="Uvicorn port (default: 8000)")
    parser.add_argument("--host", default="0.0.0.0", help="Uvicorn host (default: 0.0.0.0)")
    
    args = parser.parse_args()
    
    if args.webhook:
        import uvicorn
        logger.info(f"Starting webhook server on {args.host}:{args.port}...")
        uvicorn.run("pr_reviewer.gitlab:app", host=args.host, port=args.port, reload=False)
        return

    if args.manual:
        if not args.title or not args.changed_files:
            parser.error("--manual requires --title and --changed-files")
            
        desc = args.description or ""
        try:
            with open(args.changed_files, "r", encoding="utf-8") as f:
                changes = f.read()
        except Exception as e:
            logger.error(f"Error reading file {args.changed_files}: {e}")
            sys.exit(1)
            
        logger.info(f"Running manual review on: {args.title}")
        report = run_pr_review_workflow(args.title, desc, changes)
        print("\n" + "=" * 40 + " CONSOLIDATED REPORT " + "=" * 40 + "\n")
        print(report)
        print("\n" + "=" * 101 + "\n")
        return

    # Handle sample PRs
    from pr_reviewer.samples import (
        PR_SECURITY,
        PR_ARCHITECTURE,
        PR_CODE_QUALITY,
        PR_DOCUMENTATION,
        PR_CLEAN,
    )
    
    sample_map = {
        "security": PR_SECURITY,
        "architecture": PR_ARCHITECTURE,
        "code_quality": PR_CODE_QUALITY,
        "documentation": PR_DOCUMENTATION,
        "clean": PR_CLEAN
    }
    
    if args.pr == "all":
        logger.info("Running review workflow on ALL sample PRs...")
        for name, pr_sample in sample_map.items():
            print(f"\n==================== RUNNING SAMPLE PR: {name.upper()} ====================")
            changes = format_sample_files(pr_sample.files)
            report = run_pr_review_workflow(pr_sample.title, pr_sample.description, changes)
            print(f"\n==================== REPORT FOR: {name.upper()} ====================")
            print(report)
            print("=" * 80 + "\n")
    else:
        pr_sample = sample_map[args.pr]
        logger.info(f"Running review workflow on sample PR: {args.pr}")
        changes = format_sample_files(pr_sample.files)
        report = run_pr_review_workflow(pr_sample.title, pr_sample.description, changes)
        print("\n" + "=" * 40 + f" CONSOLIDATED REPORT FOR {args.pr.upper()} " + "=" * 40 + "\n")
        print(report)
        print("\n" + "=" * 101 + "\n")

if __name__ == "__main__":
    main()
