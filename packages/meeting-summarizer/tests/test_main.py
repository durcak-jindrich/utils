import pytest
import os
from dotenv import load_dotenv
from unittest.mock import MagicMock, patch

# Load environment variables for skipif check
load_dotenv()

from meeting_summarizer.main import MeetingSummarizer

def test_workflow_structure_with_mocks():
    """Verify the workflow logic structure using mocks."""
    with patch("meeting_summarizer.main.ChatGroq") as mock_groq:
        # Mock the LLM response
        mock_llm = MagicMock()
        mock_groq.return_value = mock_llm
        
        # We need to mock the invoke method of the chains
        summarizer = MeetingSummarizer()
        summarizer.workflow = MagicMock()
        summarizer.workflow.invoke.return_value = {
            "summary": "Mock summary",
            "action_items": "Mock action items",
            "priorities": "Mock priorities"
        }
        
        result = summarizer.process("Test notes")
        
        assert "summary" in result
        assert "action_items" in result
        assert "priorities" in result
        assert result["summary"] == "Mock summary"
        summarizer.workflow.invoke.assert_called_once()

@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "your_groq_api_key_here",
    reason="GROQ_API_KEY not set"
)
def test_integration_real_llm():
    """Integration test with real LLM (requires API key)."""
    summarizer = MeetingSummarizer()
    sample_notes = "Alice and Bob met to discuss the budget. Bob will send the report by Tuesday."
    result = summarizer.process(sample_notes)
    
    assert "error" not in result
    assert len(result["summary"]) > 0
    assert len(result["action_items"]) > 0
    assert len(result["priorities"]) > 0
