from openai import OpenAI
from tavily import TavilyClient
import json, os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Broad search for overview and recent news on a topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_more_detail",
            "description": "Fetch detailed content from a specific URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to read in depth"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_report",
            "description": "Save the final research report to a markdown file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content": {"type": "string", "description": "Full markdown report"}
                },
                "required": ["filename", "content"]
            }
        }
    }
]

def handle_tool(tool_name, args):
    if tool_name == "search_web":
        results = tavily.search(args["query"])
        return json.dumps(results["results"][:5])

    elif tool_name == "get_more_detail":
        result = tavily.extract(urls=[args["url"]])
        return json.dumps(result)

    elif tool_name == "save_report":
        with open(args["filename"], "w") as f:
            f.write(args["content"])
        return f"Saved to {args['filename']}"

def run_agent(user_message):
    messages = [
        {"role": "system", "content": "You are a research agent. When asked to research a topic: first search broadly, then pick 1-2 interesting URLs to read in depth, then save a structured markdown report with what you found."},
        {"role": "user", "content": user_message}
    ]

    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools
        )
        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            print(msg.content)
            return

        for tool_call in msg.tool_calls:
            args = json.loads(tool_call.function.arguments)
            print(f"  → calling {tool_call.function.name}({args})")
            result = handle_tool(tool_call.function.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

run_agent("Research the current state of AI agent frameworks in 2026. Save a report.")
