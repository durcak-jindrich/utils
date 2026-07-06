import os
import logging
import httpx
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)

class GitLabClient:
    """A client to interact with the GitLab REST API.
    
    Used to retrieve Merge Request diffs and post review comments.
    """
    
    def __init__(self, base_url: Optional[str] = None, private_token: Optional[str] = None):
        self.base_url = (base_url or os.getenv("GITLAB_URL", "https://gitlab.com")).rstrip("/")
        self.token = private_token or os.getenv("GITLAB_PRIVATE_TOKEN", "")
        self.headers = {
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json"
        }
        
    def get_merge_request_changes(self, project_id: int, mr_iid: int) -> Dict[str, Any]:
        """Retrieves changes (diffs and file metadata) for a specific Merge Request.
        
        GitLab API: GET /projects/:id/merge_requests/:merge_request_iid/changes
        """
        url = f"{self.base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
        logger.info(f"Retrieving GitLab MR changes from: {url}")
        
        # If no token is provided, we log a warning and return mock data for dry-run
        if not self.token or "mock-token" in self.token:
            logger.warning("No valid GitLab private token provided. Returning dry-run mock response.")
            return self._get_mock_changes(project_id, mr_iid)
            
        try:
            with httpx.Client(headers=self.headers) as client:
                response = client.get(url, timeout=30.0)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GitLab API error retrieving MR changes: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error connecting to GitLab API: {e}")
            raise

    def post_merge_request_comment(self, project_id: int, mr_iid: int, body: str) -> Dict[str, Any]:
        """Posts a note/comment directly on the GitLab Merge Request.
        
        GitLab API: POST /projects/:id/merge_requests/:merge_request_iid/notes
        """
        url = f"{self.base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
        logger.info(f"Posting review comment to GitLab MR: {url}")
        
        if not self.token or "mock-token" in self.token:
            logger.warning("No valid GitLab private token provided. Dry-run: print comment to logs.")
            print("\n=== MOCK GITLAB COMMENT POSTED ===")
            print(body)
            print("==================================\n")
            return {"id": 12345, "body": body, "noteable_type": "MergeRequest", "noteable_iid": mr_iid}
            
        try:
            payload = {"body": body}
            with httpx.Client(headers=self.headers) as client:
                response = client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GitLab API error posting comment: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error posting comment to GitLab: {e}")
            raise

    def _get_mock_changes(self, project_id: int, mr_iid: int) -> Dict[str, Any]:
        """Returns mock diff data for local testing and validation when token is missing."""
        # We can dynamically pull from our samples package or return a default mock
        from pr_reviewer.samples import PR_SECURITY
        
        changes = []
        for file in PR_SECURITY.files:
            changes.append({
                "old_path": file.filename,
                "new_path": file.filename,
                "diff": file.diff,
                "new_file": True,
                "renamed_file": False,
                "deleted_file": False
            })
            
        return {
            "id": mr_iid,
            "iid": mr_iid,
            "project_id": project_id,
            "title": PR_SECURITY.title,
            "description": PR_SECURITY.description,
            "changes": changes
        }

# Webhook Server instance
app = FastAPI(
    title="GitLab AI PR Reviewer Webhook",
    description="Receives GitLab Merge Request webhooks and schedules automated AI reviews.",
    version="0.1.0"
)

# In-memory execution database for tracking review statuses in webhook
webhook_jobs = {}

def execute_review_in_background(project_id: int, mr_iid: int, title: str, description: str, changes: list):
    """Orchestrates the CrewAI workflow in the background and posts the comment."""
    from pr_reviewer.main import run_pr_review_workflow
    
    job_key = f"{project_id}-{mr_iid}"
    webhook_jobs[job_key] = "RUNNING"
    logger.info(f"Starting background review workflow for MR {project_id}!{mr_iid}")
    
    try:
        # Formats the diff list for the LLM
        formatted_files = []
        for file_change in changes:
            filepath = file_change.get("new_path") or file_change.get("old_path")
            diff = file_change.get("diff", "")
            formatted_files.append(f"### File: {filepath}\n```diff\n{diff}\n```\n")
        
        changed_files_str = "\n".join(formatted_files)
        
        # Run CrewAI
        report_markdown = run_pr_review_workflow(
            title=title,
            description=description or "",
            changed_files=changed_files_str
        )
        
        # Post back to GitLab
        client = GitLabClient()
        client.post_merge_request_comment(project_id, mr_iid, report_markdown)
        webhook_jobs[job_key] = "COMPLETED"
        logger.info(f"Successfully completed review for MR {project_id}!{mr_iid}")
        
    except Exception as e:
        webhook_jobs[job_key] = f"FAILED: {str(e)}"
        logger.error(f"Failed background review workflow for MR {project_id}!{mr_iid}: {e}", exc_info=True)

@app.post("/webhook/gitlab")
async def handle_gitlab_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_gitlab_token: Optional[str] = Header(None)
):
    """Processes incoming GitLab Merge Request webhooks."""
    # Validate secret token if configured
    expected_token = os.getenv("WEBHOOK_SECRET")
    if expected_token and x_gitlab_token != expected_token:
        logger.warning("Unauthorized GitLab webhook token header received.")
        raise HTTPException(status_code=401, detail="Invalid webhook token secret")
        
    payload = await request.json()
    
    # Check object kind - must be a merge request
    object_kind = payload.get("object_kind")
    if object_kind != "merge_request":
        return {"status": "ignored", "reason": f"Unsupported object_kind: {object_kind}"}
        
    attributes = payload.get("object_attributes", {})
    action = attributes.get("action")
    
    # We only review on open, reopen, or update (new commit)
    if action not in ["open", "reopen", "update"]:
        return {"status": "ignored", "reason": f"Unsupported MR action: {action}"}
        
    project_id = attributes.get("target_project_id")
    mr_iid = attributes.get("iid")
    title = attributes.get("title")
    description = attributes.get("description", "")
    
    logger.info(f"Received Merge Request webhook for project {project_id} MR !{mr_iid}: {title}")
    
    # Fetch changes from GitLab API
    client = GitLabClient()
    try:
        changes_data = client.get_merge_request_changes(project_id, mr_iid)
        changes_list = changes_data.get("changes", [])
    except Exception as e:
        logger.error(f"Error fetching changes for project {project_id} MR !{mr_iid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch Merge Request changes from GitLab")
        
    # Queue review workflow execution in the background
    background_tasks.add_task(
        execute_review_in_background,
        project_id=project_id,
        mr_iid=mr_iid,
        title=title,
        description=description,
        changes=changes_list
    )
    
    return {
        "status": "queued",
        "project_id": project_id,
        "merge_request_iid": mr_iid,
        "message": "AI PR review workflow has been queued."
    }

@app.get("/webhook/status/{project_id}/{mr_iid}")
def get_job_status(project_id: int, mr_iid: int):
    """Retrieves status of background review job."""
    job_key = f"{project_id}-{mr_iid}"
    status = webhook_jobs.get(job_key, "NOT_FOUND")
    return {"project_id": project_id, "merge_request_iid": mr_iid, "status": status}
