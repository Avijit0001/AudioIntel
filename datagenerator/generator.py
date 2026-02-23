from groq import Groq
import json
import os
import dotenv

dotenv.load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ----- Tools -----
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a file with given name and content",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "File name"},
                    "content": {"type": "string", "description": "File content"}
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit (overwrite) an existing file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "File name"},
                    "content": {"type": "string", "description": "New content"}
                },
                "required": ["filename", "content"]
            }
        }
    }
]

# ----- Tool tracking -----
tool_call_counts = {}  # { tool_name: call_count }
print(f"[Tools Available] {len(tools)} tool(s): {[t['function']['name'] for t in tools]}")

# ----- First call (force tool) -----
response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {"role": "user", "content": "Create a file named notes.txt with content 'Hello World'."}
    ],
    tools=tools,
    tool_choice="required"
)

message = response.choices[0].message

# ----- Handle tool call -----
if message.tool_calls:
    print(f"\n[Tool Calls in Response] {len(message.tool_calls)} call(s) made by the model")
    for tc in message.tool_calls:
        tool_call_counts[tc.function.name] = tool_call_counts.get(tc.function.name, 0) + 1
        print(f"  → '{tc.function.name}' called with args: {tc.function.arguments}")

    tool_call = message.tool_calls[0]
    arguments = json.loads(tool_call.function.arguments)

    result = None

    if tool_call.function.name == "create_file":
        filename = arguments["filename"]
        content = arguments["content"]

        with open(filename, "w") as f:
            f.write(content)

        result = f"File {filename} created."

    elif tool_call.function.name == "edit_file":
        filename = arguments["filename"]
        content = arguments["content"]

        with open(filename, "w") as f:
            f.write(content)

        result = f"File {filename} edited."

    # ----- Second call with tool result -----
    final = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "user", "content": "Create a file named notes.txt with content 'Hello World'."},
            message,
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            }
        ],
        tools=tools
    )

    # Track any additional tool calls in the final response
    if final.choices[0].message.tool_calls:
        for tc in final.choices[0].message.tool_calls:
            tool_call_counts[tc.function.name] = tool_call_counts.get(tc.function.name, 0) + 1

    print(final.choices[0].message.content)

    # ----- Tool Call Summary -----
    total_calls = sum(tool_call_counts.values())
    print(f"\n{'='*40}")
    print(f"[Tool Call Summary]")
    print(f"  Total tools available : {len(tools)}")
    print(f"  Total tool calls made : {total_calls}")
    for name, count in tool_call_counts.items():
        print(f"  '{name}' called {count} time(s)")
    print(f"{'='*40}")

else:
    print(message.content)
