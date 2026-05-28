import os
import sys
import logging
import time
from typing import List, Optional
from dotenv import load_dotenv
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from duckduckgo_search import DDGS
from langchain_core.tools import tool
from langchain_groq import ChatGroq

# Configure logging for observability
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

load_dotenv()

CURRENT_OUTPUT_FILE = "output.txt"

@tool
def search(query: str) -> str:
    """Searches the web for current information. Input: a search query string."""
    try:
        logger.info(f"Action: Searching for '{query}'")
        # Throttle to avoid rate limiting on Groq and DuckDuckGo
        time.sleep(4) 
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                # Provide a fallback hint to the agent
                return "No results found. Try a more general query (e.g., 'Python trends' instead of 'Python trends 2025')."
            
            # Format results concisely for the LLM
            formatted = "\n".join([f"- {r.get('title')}: {r.get('body')}" for r in results[:3]])
            logger.info(f"Observation: Found {len(results)} results")
            return formatted
    except Exception as e:
        logger.error(f"Search error: {e}")
        return "Search failed due to technical error. Attempt to summarize based on general knowledge if possible."

@tool
def save_to_file(content: str) -> str:
    """Saves the final findings to output.txt. Input: the text to save."""
    try:
        filename = CURRENT_OUTPUT_FILE
        logger.info(f"Action: Saving summary to {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully saved to {filename}"
    except Exception as e:
        logger.error(f"Save error: {e}")
        return f"Failed to save to file: {e}"

def run_agent(topic: str):
    # Use llama-3.1-8b-instant for better rate limits on Groq's free tier
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
        max_retries=10 # Robustness against transient 429s
    )

    tools = [search, save_to_file]
    
    # Pull the standard ReAct prompt
    prompt = hub.pull("hwchase17/react")
    
    # Construct the ReAct agent
    agent = create_react_agent(llm, tools, prompt)
    
    # Executor handles the loop, error parsing, and iteration limits
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10
    )

    # Explicit multi-step instructions for the agent
    input_text = (
        f"1. Research '{topic}' using the search tool.\n"
        f"2. Summarize findings in 3 bullet points. If search results are empty, provide a general summary based on your knowledge.\n"
        f"3. Use 'save_to_file' to save this summary.\n"
        f"4. Provide a Final Answer confirming the file was saved."
    )

    logger.info(f"Agent starting research on: {topic}")
    try:
        result = agent_executor.invoke({"input": input_text})
        logger.info("Agent task execution finished.")
        return result
    except Exception as e:
        logger.error(f"Agent executor encountered a fatal error: {e}")
        return {"output": "Execution failed."}

if __name__ == "__main__":
    topic_input = sys.argv[1] if len(sys.argv) > 1 else "latest developments in AI agents 2025"
    run_agent(topic_input)
