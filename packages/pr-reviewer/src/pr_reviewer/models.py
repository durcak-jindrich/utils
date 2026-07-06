from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class ReviewFinding(BaseModel):
    file_path: str = Field(..., description="The path of the file containing the issue.")
    line_number: Optional[str] = Field(None, description="The line number or line range (e.g. '12' or '12-15') where the issue occurs.")
    severity: Literal["Critical", "Major", "Minor", "Suggestions"] = Field(
        ..., 
        description="Severity: 'Critical' (vulnerabilities/secrets), 'Major' (architecture/severe bugs), 'Minor' (code smells/minor issues), 'Suggestions' (docs/readability)."
    )
    issue: str = Field(..., description="A concise explanation of the issue.")
    recommendation: str = Field(..., description="A specific code recommendation or action to resolve the issue.")
    rationale: Optional[str] = Field(None, description="Why this change is necessary (reference to OWASP, clean architecture, DRY, etc.).")

class ConsolidatedReviewReport(BaseModel):
    summary: str = Field(..., description="A high-level engineering summary of the review findings and overall code quality.")
    findings: List[ReviewFinding] = Field(default_factory=list, description="List of all detected issues categorized by severity.")
    verdict: Literal["Approved", "Approved with Suggestions", "Needs Changes"] = Field(
        ..., 
        description="The final verdict on the pull request. 'Approved' if no issues; 'Approved with Suggestions' if minor/suggestions; 'Needs Changes' if any Critical or Major issues exist."
    )

# GitLab Integration Webhook payload models
class GitLabUser(BaseModel):
    name: str
    username: str

class GitLabObjectAttributes(BaseModel):
    id: int
    iid: int
    target_branch: str
    source_branch: str
    source_project_id: int
    target_project_id: int
    title: str
    description: Optional[str] = None
    state: str
    url: str
    action: str

class GitLabWebhookPayload(BaseModel):
    object_kind: str
    user: GitLabUser
    project: dict
    object_attributes: GitLabObjectAttributes
