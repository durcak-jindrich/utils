"""MCP Server for Linear Ticket creation from plain English."""

import json
import logging
from typing import Any, Dict, Optional

import httpx
from fastmcp import FastMCP
from groq import Groq

from mcp_linear_tickets.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mcp-linear-tickets")

# Initialize FastMCP
mcp = FastMCP(settings.server_name)


def get_linear_headers() -> Dict[str, str]:
    """Get headers for Linear API requests."""
    return {
        "Authorization": settings.linear_api_key,
        "Content-Type": "application/json",
    }


def get_groq_client() -> Groq:
    """Initialize and return the Groq client."""
    return Groq(api_key=settings.groq_api_key)


async def structure_ticket_with_groq(description: str) -> Dict[str, Any]:
    """Structure a plain English description into a ticket JSON using Groq."""
    logger.info("Structuring ticket description with Groq")
    client = get_groq_client()

    system_prompt = (
        "You are a technical project manager. Return only valid JSON with keys: "
        "title, description, steps_to_reproduce, expected_behavior, actual_behavior, "
        "priority (Low/Medium/High)."
    )

    try:
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": description},
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from Groq")

        structured_data = json.loads(content)
        logger.info("Successfully structured ticket data")
        return structured_data
    except Exception as e:
        logger.error(f"Groq structuring failed: {e}")
        raise


@mcp.tool()
async def list_teams() -> str:
    """List available Linear teams and their IDs."""
    logger.info("Listing Linear teams")
    query = """
    query {
      teams {
        nodes {
          id
          name
          key
        }
      }
    }
    """

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.linear_api_url,
                json={"query": query},
                headers=get_linear_headers(),
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                logger.error(f"Linear API errors: {data['errors']}")
                return f"Error fetching teams: {data['errors'][0]['message']}"

            teams = data["data"]["teams"]["nodes"]
            if not teams:
                return "No teams found in your Linear workspace."

            team_list = [
                f"- {t['name']} (ID: {t['id']}, Key: {t['key']})" for t in teams
            ]
            return "Available Teams:\n" + "\n".join(team_list)
        except Exception as e:
            logger.error(f"Failed to list teams: {e}")
            return f"Error connecting to Linear API: {str(e)}"


@mcp.tool()
async def create_ticket(description: str, team_id: Optional[str] = None) -> str:
    """Create a Linear ticket from a plain English description.

    Args:
        description: The plain English description of the bug or task.
        team_id: Optional Linear team ID. If not provided, uses default from settings.

    """
    logger.info("Creating ticket...")

    actual_team_id = team_id or settings.linear_team_id
    if not actual_team_id:
        return (
            "Error: team_id is required. Provide it as an argument or "
            "set LINEAR_TEAM_ID in your settings."
        )

    try:
        structured_data = await structure_ticket_with_groq(description)
    except Exception as e:
        return f"Error structuring ticket with AI: {str(e)}"

    # Format description with structured fields
    full_description = f"""
{structured_data.get('description', '')}

### Steps to Reproduce
{structured_data.get('steps_to_reproduce', 'N/A')}

### Expected Behavior
{structured_data.get('expected_behavior', 'N/A')}

### Actual Behavior
{structured_data.get('actual_behavior', 'N/A')}
    """.strip()

    # Map priority string to Linear priority number (0-4)
    # 0 = No priority, 1 = Urgent, 2 = High, 3 = Medium, 4 = Low
    priority_map = {"Urgent": 1, "High": 2, "Medium": 3, "Low": 4}
    priority = priority_map.get(structured_data.get("priority"), 0)

    mutation = """
    mutation IssueCreate($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue {
          id
          identifier
          title
          url
        }
      }
    }
    """

    variables = {
        "input": {
            "title": structured_data.get("title", "New Ticket"),
            "description": full_description,
            "teamId": actual_team_id,
            "priority": priority,
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.linear_api_url,
                json={"query": mutation, "variables": variables},
                headers=get_linear_headers(),
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                logger.error(f"Linear API errors: {data['errors']}")
                return f"Error creating ticket: {data['errors'][0]['message']}"

            issue = data["data"]["issueCreate"]["issue"]
            return f"Ticket created: [{issue['identifier']}] {issue['title']} -> {issue['url']}"
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            return f"Error connecting to Linear API: {str(e)}"


@mcp.tool()
async def get_ticket(issue_id: str) -> str:
    """Fetch a Linear ticket by its ID (e.g., LIN-42)."""
    logger.info(f"Fetching ticket: {issue_id}")
    query = """
    query Issue($id: String!) {
      issue(id: $id) {
        id
        identifier
        title
        description
        priority
        state {
          name
        }
        url
      }
    }
    """

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.linear_api_url,
                json={"query": query, "variables": {"id": issue_id}},
                headers=get_linear_headers(),
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                logger.error(f"Linear API errors: {data['errors']}")
                return f"Error fetching ticket: {data['errors'][0]['message']}"

            issue = data["data"]["issue"]
            if not issue:
                return f"Ticket {issue_id} not found."

            priority_label = {
                0: "None",
                1: "Urgent",
                2: "High",
                3: "Medium",
                4: "Low",
            }.get(issue["priority"], "Unknown")

            return (
                f"[{issue['identifier']}] {issue['title']}\n"
                f"Status: {issue['state']['name']}\n"
                f"Priority: {priority_label} ({issue['priority']})\n"
                f"URL: {issue['url']}\n\n"
                f"Description:\n{issue['description']}"
            )
        except Exception as e:
            logger.error(f"Failed to fetch ticket: {e}")
            return f"Error connecting to Linear API: {str(e)}"


if __name__ == "__main__":
    mcp.run()
