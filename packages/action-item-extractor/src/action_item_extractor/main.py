import os
import json
import logging
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ValidationError
from google import genai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Pydantic model for Action Items
class ActionItem(BaseModel):
    owner: str = Field(..., description="The person responsible for the task")
    task: str = Field(..., description="A concise description of what needs to be done")
    deadline: str = Field(..., description="When the task should be completed (e.g., 'Friday', 'EOD today')")
    priority: Literal['high', 'medium', 'low'] = Field(..., description="The priority level of the task")
    blocked_by: Optional[str] = Field(None, description="What or who is blocking the task, if any")

# Wrapper model for a list of Action Items (better for SDK compatibility)
class ActionItemList(BaseModel):
    items: List[ActionItem]

# Realistic, messy sample standup notes
SAMPLE_NOTES = """
Standup March 10th:
Sarah: I'm finishing the auth fix, should be done by Friday. 
Mike: Still stuck on the database setup because the infra team hasn't responded to my ticket yet. 
Jane: I'll start UI mockups tomorrow, aiming for next Tuesday. 
Oh, Mike also needs to review Sarah's PR by EOD today - Sarah said that's high priority. 
Jane's mockup work is probably medium.
And we need someone to check the logs but no one's on it yet.
"""

def extract_action_items(notes: str, api_key: str) -> List[ActionItem]:
    """
    Uses Google Gemini Flash to extract structured action items from unstructured notes.
    """
    # Use gemini-flash-latest for maximum compatibility and reliability across tiers
    MODEL_ID = "gemini-flash-latest"
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Extract a structured list of action items from the following meeting notes.
    
    Notes:
    {notes}
    """

    try:
        logger.info(f"Sending notes to Gemini {MODEL_ID} for extraction...")
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': ActionItemList,
            }
        )
        
        # The SDK returns a parsed object if a schema is provided
        if response.parsed is not None:
            return response.parsed.items
        else:
            # Fallback for empty or unexpected responses
            logger.warning("Gemini returned an empty or unparsable response.")
            return []

    except ValidationError as e:
        logger.error(f"Pydantic validation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during API call: {e}")
        raise

def main():
    # Try to load from .env or environment
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("\n[!] ERROR: GOOGLE_API_KEY not found in environment variables.")
        print("Please set it in a .env file or export it: export GOOGLE_API_KEY='your-key'\n")
        return

    print("--- RAW STANDUP NOTES ---")
    print(SAMPLE_NOTES.strip())
    print("-" * 20 + "\n")

    try:
        items = extract_action_items(SAMPLE_NOTES, api_key)
        
        print("--- EXTRACTED ACTION ITEMS (VALIDATED JSON) ---")
        # Print the validated objects as a clean JSON list
        output_json = [item.model_dump() for item in items]
        print(json.dumps(output_json, indent=2))
        print("-" * 40)
        
    except Exception:
        # Errors are already logged in the helper function
        pass

if __name__ == "__main__":
    main()
