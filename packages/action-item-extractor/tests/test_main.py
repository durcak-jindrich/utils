import os
import pytest
import time
from dotenv import load_dotenv
from action_item_extractor.main import ActionItem, extract_action_items
from pydantic import ValidationError
from google.genai import errors

# Load environment variables from .env file
load_dotenv()

# --- Unit Tests ---

def test_action_item_valid():
    """Tests the ActionItem model with valid data."""
    data = {
        "owner": "Sarah",
        "task": "Complete the auth fix",
        "deadline": "Friday",
        "priority": "high",
        "blocked_by": None
    }
    item = ActionItem(**data)
    assert item.owner == "Sarah"
    assert item.priority == "high"

def test_action_item_invalid_priority():
    """Tests that the model fails with an invalid priority value."""
    data = {
        "owner": "Mike",
        "task": "Fix DB",
        "deadline": "Today",
        "priority": "urgent",
        "blocked_by": "Infra"
    }
    with pytest.raises(ValidationError):
        ActionItem(**data)

# --- Integration Test ---

def test_extract_action_items_integration():
    """Integration test calling the real Gemini API.
    
    This test WILL fail if GOOGLE_API_KEY is not set correctly or if quota is exceeded.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        pytest.fail("GOOGLE_API_KEY is missing from the environment. Follow the instructions to add it to a .env file.")

    test_notes = "Tom needs to fix the login bug by Monday. It's high priority."
    
    # Simple retry for 429
    for attempt in range(2):
        try:
            results = extract_action_items(test_notes, api_key)
            
            assert isinstance(results, list)
            assert len(results) > 0
            assert any(item.owner.lower() == "tom" for item in results)
            assert any("login" in item.task.lower() for item in results)
            assert any(item.priority == "high" for item in results)
            return # Success
        except errors.ClientError as e:
            if "429" in str(e) and attempt == 0:
                time.sleep(2) # Brief wait
                continue
            pytest.fail(f"Integration test failed with API error: {e}")
        except Exception as e:
            pytest.fail(f"Integration test failed with unexpected error: {e}")
