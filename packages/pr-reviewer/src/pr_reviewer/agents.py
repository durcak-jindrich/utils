import os
import logging
import litellm
from crewai import Agent, LLM
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_llm() -> LLM:
    """Configures and returns the LLM based on environment variables.
    
    Supports Groq, Ollama, OpenAI, etc.
    """
    litellm.num_retries = 5
    litellm.max_retries = 5

    # Cross-compatibility helper for Gemini API key
    if os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")

    model_name = os.getenv("LLM_MODEL", "gemini/gemini-1.5-flash")
    base_url = os.getenv("LLM_BASE_URL", None)
    
    logger.info(f"Initializing LLM with model: {model_name} (Base URL: {base_url})")
    
    llm_args = {
        "model": model_name,
        "temperature": 0.1,
        "max_retries": 5,
    }
    
    if base_url:
        llm_args["base_url"] = base_url
        
    return LLM(**llm_args)

def create_security_reviewer(llm: LLM) -> Agent:
    return Agent(
        role="Security Reviewer",
        goal="Identify security vulnerabilities, hardcoded secrets, injection risks, cryptographic weaknesses, and insecure dependencies in code diffs.",
        backstory=(
            "An expert cybersecurity analyst specializing in static application security testing (SAST) and secure code reviews. "
            "You check git diffs for exposed API keys, credentials, SQL injection, XSS, insecure hash functions, and other OWASP Top 10 vulnerabilities. "
            "Be precise and point to the exact file and lines, and provide secure code fixes."
        ),
        verbose=True,
        llm=llm
    )

def create_architecture_reviewer(llm: LLM) -> Agent:
    return Agent(
        role="Architecture Reviewer",
        goal="Identify design, layering, naming conventions, circular dependencies, modular boundaries, and design pattern violations in code diffs.",
        backstory=(
            "A veteran software architect who enforces clean code architecture, Separation of Concerns, SOLID principles, and clean layering. "
            "You prevent database logic from leaking into controllers, prevent domain models from importing network/infrastructure packages directly, "
            "and catch circular dependencies. You explain the architectural risk and enforce clean decoupling."
        ),
        verbose=True,
        llm=llm
    )

def create_code_quality_reviewer(llm: LLM) -> Agent:
    return Agent(
        role="Code Quality Reviewer",
        goal="Detect code smells, cognitive complexity, code duplication, poor naming, performance bottlenecks, and Python best-practice violations in code diffs.",
        backstory=(
            "A meticulous developer obsessed with clean code, refactoring, DRY, KISS, and YAGNI. "
            "You identify overly complex nested conditionals, giant functions, redundant operations, inefficient loops, and naming inconsistencies. "
            "You suggest concrete refactored code snippets that improve readability and performance."
        ),
        verbose=True,
        llm=llm
    )

def create_documentation_reviewer(llm: LLM) -> Agent:
    return Agent(
        role="Documentation Reviewer",
        goal="Verify code comments, docstrings, public API documentation, README changes, and changelog updates in code diffs.",
        backstory=(
            "A developer advocate and technical writer who champions documentation as a first-class citizen. "
            "You make sure all new public functions, classes, and APIs have clear PEP-257 docstrings with parameter descriptions. "
            "You ensure that if new configuration or CLI flags are added, the README is updated, and comments describe the 'why' rather than the 'what'."
        ),
        verbose=True,
        llm=llm
    )

def create_lead_reviewer(llm: LLM) -> Agent:
    return Agent(
        role="Lead Reviewer",
        goal="Consolidate the findings from all specialized reviewer agents into a single structured, high-quality, non-redundant review report, grouped by severity (Critical, Major, Minor, Suggestions).",
        backstory=(
            "An empathetic engineering manager and team lead. Your job is to take the raw feedback from the Security, Architecture, Code Quality, "
            "and Documentation reviewers, resolve any conflicting or duplicate feedback, assign correct severities, compile a summary, "
            "and present the final feedback as a clear, polite, actionable markdown report. "
            "Your final verdict (Approved, Approved with Suggestions, Needs Changes) must be professional, supportive, and constructive."
        ),
        verbose=True,
        llm=llm
    )
