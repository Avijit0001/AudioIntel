from openai import OpenAI
import json
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Define a tool
tools = [
    {
        "type": "function",
        "function": {
            "name": "count_r_letters",
            "description": "Count how many times the letter 'r' appears in a word",
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {
                        "type": "string",
                        "description": "The word to analyze"
                    }
                },
                "required": ["word"]
            }
        }
    }
]

# First call - let model decide to call tool
response = client.chat.completions.create(
    model="openai/gpt-oss-20b:free",
    messages=[
        {"role": "user", "content": "How many r's are in the word strawberry?"}
    ],
    tools=tools,
    tool_choice="auto"
)

message = response.choices[0].message

# Check if model called a tool
if message.tool_calls:
    tool_call = message.tool_calls[0]
    arguments = json.loads(tool_call.function.arguments)

    # Execute tool locally
    word = arguments["word"]
    result = word.lower().count("r")

    # Send tool result back to model
    response2 = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=[
            {"role": "user", "content": "How many r's are in the word strawberry?"},
            message,  # assistant tool call
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result)
            }
        ],
        tools=tools
    )

    print(response2.choices[0].message.content)
else:
    print("Model did not call tool.")
