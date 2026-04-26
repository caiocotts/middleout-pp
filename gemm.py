# from google import genai
# from google.genai import types
# import os


# with open("words.txt", "r", encoding="utf-8") as f:
#     words = f.read()

# with open("SYSTEM.md", "r", encoding="utf-8") as f:
#     system = f.read()

# with open("SYSTEM_DECODE.md", "r", encoding="utf-8") as f:
#     system_decode = f.read()


# client = genai.Client(api_key="")

# response = client.models.generate_content(
#     model="gemma-4-26b-a4b-it", 
#     config=types.GenerateContentConfig(
#         system_instruction=system,
#         thinking_config=types.ThinkingConfig(include_thoughts=False)
#     ),
#     contents=words
# )
# print(response.text)



# To run this code you need to install the following dependencies:
# pip install google-genai

import os
from google import genai
from google.genai import types


def generate():
    client = genai.Client(
        api_key="AIzaSyCgnc1d9GHXS6i0sLpvlzrAZtd_6lh3dvE",
    )

    model = "gemma-4-26b-a4b-it"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""hello"""),
            ],
        ),
    ]
    tools = [
        types.Tool(googleSearch=types.GoogleSearch(
        )),
    ]
    # generate_content_config = types.GenerateContentConfig(
    #     thinking_config=types.ThinkingConfig(
    #         thinking_level="HIGH",
    #     ),
    #     tools=tools,
    # )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        #config=generate_content_config,
    ):
        if text := chunk.text:
            print(text, end="")

if __name__ == "__main__":
    generate()


