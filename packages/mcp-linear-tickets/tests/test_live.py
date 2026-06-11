"""Live end-to-end integration test for MCP Linear Tickets with Cleanup."""

import pytest
import os
import asyncio
import httpx
from mcp_linear_tickets.main import mcp
from mcp_linear_tickets.config import settings

@pytest.mark.asyncio
async def test_live_full_flow_with_cleanup():
    """Verify full flow: list teams -> create ticket -> pause -> delete ticket."""
    
    # 1. Check keys
    lin_key = os.getenv("LINEAR_API_KEY")
    if not lin_key or "your_" in lin_key:
        pytest.fail("LINEAR_API_KEY not set in .env")

    print(f"\n[LIVE TEST] 1. Fetching teams to get a target...")
    result = await mcp.call_tool("list_teams", {})
    text_result = result.content[0].text
    
    if "Error" in text_result:
        pytest.fail(f"Failed to list teams: {text_result}")
    
    # Extract the first team ID found
    import re
    team_match = re.search(r"ID: ([a-f0-9\-]+)", text_result)
    if not team_match:
        pytest.fail(f"Could not find a team ID in the response: {text_result}")
    
    team_id = team_match.group(1)
    print(f"✅ Using Team ID: {team_id}")

    print(f"[LIVE TEST] 2. Creating a real ticket via AI structuring...")
    description = "TEST TICKET: The integration test is successful. This ticket should be visible for 15 seconds."
    create_result = await mcp.call_tool("create_ticket", {"description": description, "team_id": team_id})
    create_text = create_result.content[0].text
    
    if "Error" in create_text:
        pytest.fail(f"Failed to create ticket: {create_text}")
    
    # Extract ticket ID and identifier
    # Format is: Ticket created: [LIN-1] Title -> URL
    id_match = re.search(r"\[([A-Z0-9\-]+)\]", create_text)
    url_match = re.search(r"-> (https://linear.app/issue/[^\s]+)", create_text)
    
    if not id_match or not url_match:
        pytest.fail(f"Could not parse ticket info: {create_text}")
        
    ticket_identifier = id_match.group(1)
    ticket_url = url_match.group(1)
    
    print(f"✅ Ticket created: {ticket_identifier}")
    print(f"🔗 URL: {ticket_url}")
    print(f"⏳ PAUSING FOR 15 SECONDS. Please verify the ticket manually.")
    
    await asyncio.sleep(15)
    
    print(f"[LIVE TEST] 3. Cleaning up: Deleting ticket {ticket_identifier}...")
    
    # We need to get the internal ID (UUID) for deletion, but the identifier works in some queries.
    # To delete, we first need the UUID.
    query_id = """
    query Issue($id: String!) {
      issue(id: $id) {
        id
      }
    }
    """
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": lin_key, "Content-Type": "application/json"}
        # Fetch UUID
        resp = await client.post(
            settings.linear_api_url, 
            json={"query": query_id, "variables": {"id": ticket_identifier}},
            headers=headers
        )
        issue_data = resp.json()
        internal_id = issue_data["data"]["issue"]["id"]
        
        # Perform deletion
        delete_mutation = """
        mutation IssueDelete($id: ID!) {
          issueDelete(id: $id) {
            success
          }
        }
        """
        resp = await client.post(
            settings.linear_api_url,
            json={"query": delete_mutation, "variables": {"id": internal_id}},
            headers=headers
        )
        delete_data = resp.json()
        
        if delete_data.get("data", {}).get("issueDelete", {}).get("success"):
            print(f"✅ Ticket {ticket_identifier} deleted successfully.")
        else:
            print(f"❌ Failed to delete ticket: {delete_data}")

@pytest.mark.asyncio
async def test_live_list_teams_to_console():
    """Helper to list teams."""
    result = await mcp.call_tool("list_teams", {})
    print(f"\n[LIVE DATA] {result.content[0].text}")
