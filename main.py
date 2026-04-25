
# import os
# from openai import OpenAI

# client = OpenAI(
#     # This is the default and can be omitted
#     api_key="sk-lm-UudaIYkg:84XHUx8svlzJoNrXCJIm",
#     base_url="http://127.0.0.1:1234/v1"
# )

# # response = client.responses.create(
# #     model="google/gemma-4-e2b",
# #     instructions="You are a coding assistant that talks like a pirate. keep response as short as possible",
# #     input="How do I check if a Python object is an instance of a class?",
# # )

# with open("words.txt", "r") as f:
#     response = client.responses.create(
#         model="google/gemma-4-e2b",
#         instructions="read the text and return a list of words that can be removed from the text while keeping the tone and context of the text. keep response as short as possible",
#         input=f"{f}",
#     )



#print(response.output_text)

from ollama import chat
from ollama import ChatResponse

with open("words.txt", "r", encoding="utf-8") as f:
    words = f.read()

with open("SYSTEM.md", "r", encoding="utf-8") as f:
    system = f.read()

with open("SYSTEM_DECODE.md", "r", encoding="utf-8") as f:
    system_decode = f.read()


#words = words.replace(" ", "")

response: ChatResponse = chat(model='gemma4:e2b', messages=[
    {
        'role': 'system',
        'content': system
    },
    {
        'role': 'user',
        'content': f"the following is the text you should remove redundant words: {words}",
    },
], think=False)
print("compresion is done...")
print("====================================================")
print(response.message.content)
print("====================================================")

response2: ChatResponse = chat(model='gemma4:e2b', messages=[
    {
        'role': 'system',
        'content': system_decode
    },
    {
        'role': 'user',
        'content': response.message.content,
    },
])


#print(system)
print(response2.message.content)
# or access fields directly from the response object
# print(response.message.content)