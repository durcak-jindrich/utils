"""Tests for the MCP Linear Tickets server."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp_linear_tickets.main import mcp


@pytest.mark.asyncio
async def test_mcp_list_teams():
    """Integration test for list_teams via MCP interface."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "teams": {
                "nodes": [{"id": "team-1", "name": "Team One", "key": "T1"}]
            }
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        # Call via MCP interface
        result = await mcp.call_tool("list_teams", {})

        # Access the text content from ToolResult
        text_content = result.content[0].text

        assert "Team One" in text_content
        assert "team-1" in text_content
        assert "T1" in text_content


@pytest.mark.asyncio
async def test_mcp_create_ticket():
    """Integration test for create_ticket via MCP interface."""
    # Mock Groq response
    mock_groq_data = {
        "title": "Bug: Test issue",
        "description": "This is a test",
        "steps_to_reproduce": "Step 1",
        "expected_behavior": "Should work",
        "actual_behavior": "Broken",
        "priority": "High",
    }

    # Mock Linear response
    mock_linear_response = MagicMock()
    mock_linear_response.json.return_value = {
        "data": {
            "issueCreate": {
                "success": True,
                "issue": {
                    "id": "issue-1",
                    "identifier": "LIN-1",
                    "title": "Bug: Test issue",
                    "url": "https://linear.app/issue/LIN-1",
                },
            }
        }
    }
    mock_linear_response.raise_for_status = MagicMock()

    with patch(
        "mcp_linear_tickets.main.structure_ticket_with_groq", new_callable=AsyncMock
    ) as mock_structure:
        mock_structure.return_value = mock_groq_data

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_linear_response

            # Call via MCP interface
            result = await mcp.call_tool(
                "create_ticket",
                {"description": "Something is broken", "team_id": "team-123"}
            )

            text_content = result.content[0].text

            assert "Ticket created" in text_content
            assert "LIN-1" in text_content
            assert "https://linear.app/issue/LIN-1" in text_content


@pytest.mark.asyncio
async def test_mcp_get_ticket():
    """Integration test for get_ticket via MCP interface."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "issue": {
                "id": "issue-1",
                "identifier": "LIN-1",
                "title": "Test Issue",
                "description": "Description here",
                "priority": 2,
                "state": {"name": "Todo"},
                "url": "https://linear.app/issue/LIN-1",
            }
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        # Call via MCP interface
        result = await mcp.call_tool("get_ticket", {"issue_id": "LIN-1"})

        text_content = result.content[0].text

        assert "LIN-1" in text_content
        assert "Test Issue" in text_content
        assert "Todo" in text_content
        assert "High" in text_content
