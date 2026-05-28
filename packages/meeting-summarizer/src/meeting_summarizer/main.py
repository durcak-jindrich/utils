import os
import logging
from typing import Dict, List, Any
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("meeting-summarizer")

# Load environment variables
load_dotenv()

def get_llm():
    """Initialize the Groq LLM."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        logger.warning("GROQ_API_KEY is not set correctly. LLM calls will fail.")
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        groq_api_key=api_key
    )

def create_summarizer_chain(llm):
    """Create a chain for summarizing meeting notes."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a professional secretary. Summarize the following meeting notes concisely."),
        ("user", "{meeting_notes}")
    ])
    return prompt | llm | StrOutputParser()

def create_action_item_chain(llm):
    """Create a chain for extracting action items."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract a list of clear action items from the following summary. Format as a bulleted list."),
        ("user", "{summary}")
    ])
    return prompt | llm | StrOutputParser()

def create_priority_chain(llm):
    """Create a chain for classifying priority of action items."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Classify the priority (High, Medium, Low) for each of the following action items. Explain why."),
        ("user", "{action_items}")
    ])
    return prompt | llm | StrOutputParser()

class MeetingSummarizer:
    def __init__(self):
        self.llm = get_llm()
        self.summarize_chain = create_summarizer_chain(self.llm)
        self.action_chain = create_action_item_chain(self.llm)
        self.priority_chain = create_priority_chain(self.llm)
        
        # Multi-step workflow using LCEL
        self.workflow = (
            {"summary": self.summarize_chain}
            | RunnablePassthrough.assign(action_items=self.action_chain)
            | RunnablePassthrough.assign(priorities=self.priority_chain)
        )

    def process(self, meeting_notes: str) -> Dict[str, Any]:
        """Run the full workflow on meeting notes."""
        logger.info("Starting meeting notes processing...")
        try:
            result = self.workflow.invoke({"meeting_notes": meeting_notes})
            logger.info("Processing completed successfully.")
            return result
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            return {"error": str(e)}

if __name__ == "__main__":
    # Simple verification script
    # sample_notes = """
    # Date: 2024-05-20
    # Attendees: Alice, Bob, Charlie
    # Topic: Q3 Project Orion Launch
    
    # Alice reported that the frontend is 80% complete. 
    # Bob mentioned that the backend API needs more load testing. 
    # Charlie suggested we move the launch date to September 15th to allow for more QA.
    # Alice agreed and will update the project timeline.
    # Bob will coordinate with the DevOps team for load testing by next Friday.
    # """

    sample_notes = """
    Date: 2024-06-10
    Attendees: David, Emma, Lucas
    Topic: Mobile App Redesign Sprint

    David reported that the new UI components are nearly finalized.
    Emma mentioned that the authentication flow needs additional security review.
    Lucas suggested delaying the release to October 1st to ensure stability.
    David agreed and will adjust the sprint roadmap.
    Emma will work with the security team to complete the review by next Wednesday.
    """
    
    summarizer = MeetingSummarizer()
    output = summarizer.process(sample_notes)
    
    if "error" in output:
        print(f"FAILED: {output['error']}")
    else:
        print("\n--- SUMMARY ---")
        print(output.get("summary"))
        print("\n--- ACTION ITEMS ---")
        print(output.get("action_items"))
        print("\n--- PRIORITIES ---")
        print(output.get("priorities"))
