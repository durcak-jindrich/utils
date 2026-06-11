"""
End-to-end live test for MCP Linear Tickets.
Creates a ticket, waits for verification, and cleans up.
"""
import asyncio
import os
import re
import httpx
from dotenv import load_dotenv
from mcp_linear_tickets.main import mcp
from mcp_linear_tickets.config import settings

async def run_live_test():
    # Load environment variables from .env
    load_dotenv()
    
    lin_key = os.getenv("LINEAR_API_KEY")
    if not lin_key:
        print("❌ Error: LINEAR_API_KEY not found in environment.")
        return

    print("🚀 Starting Live End-to-End Test")

    # 1. List Teams
    print("\n1️⃣  Listing teams...")
    result = await mcp.call_tool("list_teams", {})
    text_result = result.content[0].text
    print(f"✅ Teams found:\n{text_result}")

    # Extract first Team ID
    match = re.search(r"ID: ([a-f0-9\-]+)", text_result)
    if not match:
        print("❌ Error: Could not parse Team ID from result.")
        return
    team_id = match.group(1)

    # 2. Create Ticket
    print(f"\n2️⃣  Creating ticket for team {team_id}...")
    description = "LIVE VERIFICATION: This ticket was created by the Gemini CLI agent. It will be automatically deleted in 15 seconds."
    create_res = await mcp.call_tool("create_ticket", {"description": description, "team_id": team_id})
    create_text = create_res.content[0].text
    
    if "Error" in create_text:
        print(f"❌ Error creating ticket: {create_text}")
        return

    print(f"✅ {create_text}")
    
    # Extract identifier (e.g., ART-11)
    id_match = re.search(r"\[([A-Z0-9\-]+)\]", create_text)
    if not id_match:
        print("❌ Error: Could not parse ticket identifier.")
        return
    identifier = id_match.group(1)

    print(f"\n⏳ PAUSING FOR 15 SECONDS.")
    print(f"Please check your Linear dashboard now. Ticket: {identifier}")
    await asyncio.sleep(15)

    # 3. Cleanup
    print(f"\n3️⃣  Cleaning up ticket {identifier}...")
    headers = {
        "Authorization": lin_key,
        "Content-Type": "application/json"
    }

    # First, get the internal UUID
    query = """
    query Issue($id: String!) {
      issue(id: $id) {
        id
      }
    }
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            settings.linear_api_url,
            json={"query": query, "variables": {"id": identifier}},
            headers=headers
        )
        data = resp.json()
        if "errors" in data:
            print(f"❌ Error fetching ticket UUID: {data['errors']}")
            return
        
        internal_id = data["data"]["issue"]["id"]

        # Now delete it
        mutation = """
        mutation IssueDelete($id: String!) {
          issueDelete(id: $id) {
            success
          }
        }
        """
        resp = await client.post(
            settings.linear_api_url,
            json={"query": mutation, "variables": {"id": internal_id}},
            headers=headers
        )
        del_data = resp.json()
        if del_data.get("data", {}).get("issueDelete", {}).get("success"):
            print(f"✅ Ticket {identifier} (ID: {internal_id}) successfully deleted.")
        else:
            print(f"❌ Failed to delete ticket: {del_data}")

if __name__ == "__main__":
    asyncio.run(run_live_test())
