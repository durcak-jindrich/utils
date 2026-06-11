"""Test configuration for the MCP Linear Tickets server."""

import os

# Set dummy environment variables before any other imports
os.environ["LINEAR_API_KEY"] = "dummy_linear_key"
os.environ["GROQ_API_KEY"] = "dummy_groq_key"
os.environ["LINEAR_TEAM_ID"] = "dummy_team_id"
