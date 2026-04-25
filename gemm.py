from google import genai
from google.genai import types
import os


with open("words.txt", "r", encoding="utf-8") as f:
    words = f.read()

with open("SYSTEM.md", "r", encoding="utf-8") as f:
    system = f.read()

with open("SYSTEM_DECODE.md", "r", encoding="utf-8") as f:
    system_decode = f.read()


client = genai.Client(api_key="AIzaSyCqxFhePrT5k5G7M9TnkxRBXffU3uqvJ6c")

response = client.models.generate_content(
    model="gemma-4-26b-a4b-it", 
    config=types.GenerateContentConfig(
        system_instruction=system,
        thinking_config=types.ThinkingConfig(include_thoughts=True)
    ),
    contents=words
)
print(response.text)