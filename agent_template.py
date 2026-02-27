from openai import OpenAI
from tavily import TavilyClient
import json, os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# ─────────────────────────────────────────────
# TOOLS — copy/paste this block to add more
# ─────────────────────────────────────────────
tools = [
    {
        "type": "function",
        "function": {
            "name": "example_tool",                          # ← EDIT THIS
            "description": "What this tool does and when to use it",  # ← EDIT THIS (GPT reads this)
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "what to pass in"}  # ← EDIT THIS
                },
                "required": ["input"]                        # ← EDIT THIS
            }
        }
    },
    # paste another block here for a second tool
]

# ─────────────────────────────────────────────
# TOOL EXECUTION — add a branch for each tool
# ─────────────────────────────────────────────
def handle_tool(tool_name, args):
    if tool_name == "example_tool":                          # ← EDIT THIS
        result = args["input"]                               # ← EDIT THIS — call your API here
        return json.dumps(result)

    # elif tool_name == "another_tool":
    #     ...

# ─────────────────────────────────────────────
# AGENT LOOP — don't touch this
# ─────────────────────────────────────────────
def run_agent(user_message):
    messages = [
        {"role": "system", "content": "You are a ??? agent. Your job is to ???"},  # ← EDIT THIS
        {"role": "user", "content": user_message}
    ]

    while True:
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            stream=True
        )

        # --- Accumulate the stream ---
        content    = ""
        tool_calls = []          # built up from chunks

        for chunk in stream:
            delta = chunk.choices[0].delta

            # Print content tokens as they arrive
            if delta.content:
                print(delta.content, end="", flush=True)
                content += delta.content

            # Accumulate tool call chunks
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    while len(tool_calls) <= tc.index:
                        tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                    if tc.id:
                        tool_calls[tc.index]["id"] = tc.id
                    if tc.function.name:
                        tool_calls[tc.index]["function"]["name"] += tc.function.name
                    if tc.function.arguments:
                        tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments

        # --- Rebuild assistant message and append ---
        assistant_msg = {"role": "assistant", "content": content}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {"id": tc["id"], "type": "function", "function": tc["function"]}
                for tc in tool_calls
            ]
        messages.append(assistant_msg)

        # --- No tool calls = final answer, done ---
        if not tool_calls:
            print()   # newline after streamed content
            return

        # --- Execute each tool and feed results back ---
        for tc in tool_calls:
            args = json.loads(tc["function"]["arguments"])
            print(f"\n  → calling {tc['function']['name']}({args})")
            result = handle_tool(tc["function"]["name"], args)
            messages.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      result
            })

run_agent("Your task here")  # ← EDIT THIS
