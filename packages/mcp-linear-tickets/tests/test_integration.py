"""Integration tests for the MCP Linear Tickets server using network-level mocking."""

import json

import pytest
import respx
from httpx import Response
from mcp_linear_tickets.config import settings
from mcp_linear_tickets.main import mcp


@pytest.mark.asyncio
@respx.mock
async def test_create_ticket_integration():
    """Test the full flow from MCP tool call to Linear API mutation."""
    # 1. Mock Groq API response
    groq_route = respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "title": "Integrated Bug",
                                "description": "Found via integration test",
                                "steps_to_reproduce": "1. Run test",
                                "expected_behavior": "Success",
                                "actual_behavior": "Failure",
                                "priority": "High"
                            })
                        }
                    }
                ]
            }
        )
    )

    # 2. Mock Linear API response
    linear_route = respx.post(settings.linear_api_url).mock(
        return_value=Response(
            200,
            json={
                "data": {
                    "issueCreate": {
                        "success": True,
                        "issue": {
                            "id": "issue-int",
                            "identifier": "INT-1",
                            "title": "Integrated Bug",
                            "url": "https://linear.app/issue/INT-1"
                        }
                    }
                }
            }
        )
    )

    # 3. Call the tool via MCP interface
    description = "There is a bug in the integration test system"
    result = await mcp.call_tool("create_ticket", {"description": description, "team_id": "test-team"})

    # 4. Verify results
    text_result = result.content[0].text
    assert "Ticket created: [INT-1]" in text_result
    assert "https://linear.app/issue/INT-1" in text_result

    # 5. Verify Groq was called correctly
    assert groq_route.called
    groq_request = groq_route.calls.last.request
    groq_body = json.loads(groq_request.content)
    assert description in groq_body["messages"][1]["content"]

    # 6. Verify Linear was called correctly
    assert linear_route.called
    linear_request = linear_route.calls.last.request
    linear_body = json.loads(linear_request.content)
    assert "Integrated Bug" in linear_body["variables"]["input"]["title"]
    assert "test-team" == linear_body["variables"]["input"]["teamId"]

@pytest.mark.asyncio
@respx.mock
async def test_list_teams_integration():
    """Test listing teams via real network interception."""
    respx.post(settings.linear_api_url).mock(
        return_value=Response(
            200,
            json={
                "data": {
                    "teams": {
                        "nodes": [
                            {"id": "team-real-1", "name": "Engineering", "key": "ENG"}
                        ]
                    }
                }
            }
        )
    )

    result = await mcp.call_tool("list_teams", {})
    text_result = result.content[0].text

    assert "Engineering" in text_result
    assert "team-real-1" in text_result
    assert "ENG" in text_result

@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_integration():
    """Test fetching a ticket via real network interception."""
    respx.post(settings.linear_api_url).mock(
        return_value=Response(
            200,
            json={
                "data": {
                    "issue": {
                        "id": "issue-real",
                        "identifier": "ENG-42",
                        "title": "Deep Integration",
                        "description": "Verify the network layer",
                        "priority": 1,
                        "state": {"name": "In Progress"},
                        "url": "https://linear.app/issue/ENG-42"
                    }
                }
            }
        )
    )

    result = await mcp.call_tool("get_ticket", {"issue_id": "ENG-42"})
    text_result = result.content[0].text

    assert "ENG-42" in text_result
    assert "Deep Integration" in text_result
    assert "Urgent" in text_result
    assert "In Progress" in text_result
