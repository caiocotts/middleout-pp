from google import genai
from google.genai import types

with open("words.txt", "r", encoding="utf-8") as f:
    words = f.read()

with open("SYSTEM.md", "r", encoding="utf-8") as f:
    system = f.read()

client = genai.Client(api_key="AIzaSyCqxFhePrT5k5G7M9TnkxRBXffU3uqvJ6c")

print("Testing with include_thoughts=True...")
try:
    response = client.models.generate_content(
        model="gemma-4-26b-a4b-it", 
        contents=words[:100],  # Shortened for quick test
        config=types.GenerateContentConfig(
            system_instruction=system,
            thinking_config=types.ThinkingConfig(include_thoughts=True)
        )
    )
    print("Success")
except Exception as e:
    print(f"Error: {e}")
