from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

try:
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents="Say hello"
    )
    print(f"Success: {response.text}")
except Exception as e:
    print(f"Error: {e}")

try:
    print("Listing models...")
    for m in client.models.list():
        print(f" - {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
