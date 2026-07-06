from crewai import Agent, Task

def create_security_review_task(agent: Agent) -> Task:
    return Task(
        description=(
            "Audit this PR for security flaws (hardcoded secrets, SQL/shell injection, insecure cryptos).\n"
            "PR: {title}\n"
            "Description: {description}\n"
            "Diff:\n{changed_files}\n\n"
            "Expected Output: Brief bulleted list of findings (File, Line, Vulnerability, Risk, and 1-3 lines secure fix). "
            "If clean, write 'No security vulnerabilities identified.'"
        ),
        expected_output="Short list of security issues with brief fixes, or 'No security vulnerabilities identified.'",
        agent=agent
    )

def create_architecture_review_task(agent: Agent) -> Task:
    return Task(
        description=(
            "Audit this PR for architectural issues (layer violations, circular imports, separation of concerns).\n"
            "PR: {title}\n"
            "Description: {description}\n"
            "Diff:\n{changed_files}\n\n"
            "Expected Output: Brief bulleted list of findings (File, Line, Issue, and Refactoring advice). "
            "If clean, write 'No architectural violations identified.'"
        ),
        expected_output="Short list of architectural violations with brief advice, or 'No architectural violations identified.'",
        agent=agent
    )

def create_code_quality_review_task(agent: Agent) -> Task:
    return Task(
        description=(
            "Audit this PR for code quality issues (cognitive complexity, duplicates, style, bad naming).\n"
            "PR: {title}\n"
            "Description: {description}\n"
            "Diff:\n{changed_files}\n\n"
            "Expected Output: Brief bulleted list of findings (File, Line, Smell, and a short code correction). "
            "If clean, write 'No code quality issues identified.'"
        ),
        expected_output="Short list of code quality smells with brief corrections, or 'No code quality issues identified.'",
        agent=agent
    )

def create_documentation_review_task(agent: Agent) -> Task:
    return Task(
        description=(
            "Audit this PR for documentation gaps (missing docstrings on public APIs, missing README updates).\n"
            "PR: {title}\n"
            "Description: {description}\n"
            "Diff:\n{changed_files}\n\n"
            "Expected Output: Brief bulleted list of findings (File, Line, Missing doc, and suggested brief comment). "
            "If clean, write 'No documentation gaps identified.'"
        ),
        expected_output="Short list of doc gaps with brief suggestions, or 'No documentation gaps identified.'",
        agent=agent
    )

def create_lead_review_task(agent: Agent, context_tasks: list) -> Task:
    return Task(
        description=(
            "Consolidate the provided review findings from the Security, Architecture, Code Quality, and Documentation reviews.\n"
            "Output a final Markdown report with:\n"
            "1. **Summary**: 2-3 sentences overview of code quality.\n"
            "2. **Findings Grouped by Severity**: (Critical, Major, Minor, Suggestions). Keep description and suggested fix short.\n"
            "3. **Verdict**: 'Approved', 'Approved with Suggestions', or 'Needs Changes' (if any Critical/Major issues exist).\n"
            "Avoid wordiness and redundant text."
        ),
        expected_output="Consolidated Markdown PR review comment with summary, severity-grouped findings, and verdict.",
        agent=agent,
        context=context_tasks
    )

def create_optimized_review_task(agent: Agent) -> Task:
    """A combined task that runs all reviews in a single LLM execution."""
    return Task(
        description=(
            "Conduct a comprehensive code review of this PR across four areas: Security (secrets/injections), "
            "Architecture (layering/decoupling), Code Quality (smells/complexity), and Documentation (docstrings/README).\n"
            "PR: {title}\n"
            "Description: {description}\n"
            "Diff:\n{changed_files}\n\n"
            "Expected Output: A concise Markdown report containing:\n"
            "1. **Summary**: 2-3 sentences overview of the PR.\n"
            "2. **Findings Grouped by Severity** (Critical, Major, Minor, Suggestions). For each finding, list: File, Line, Issue, Rationale, and a brief Suggested Fix.\n"
            "3. **Verdict**: 'Approved' (no issues), 'Approved with Suggestions' (minor/docs), or 'Needs Changes' (any Critical or Major issues).\n"
            "Keep the output compact, direct, and actionable to save token space."
        ),
        expected_output="Optimized Markdown review comment containing the summary, severity-grouped findings, and verdict.",
        agent=agent
    )
