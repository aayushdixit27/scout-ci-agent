from openai import OpenAI
from tavily import TavilyClient
import json, os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

tools = [{
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Search the web for current information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"]
        }
    }
}]

def run_agent(user_message):
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools
        )
        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return msg.content

        for tool_call in msg.tool_calls:
            args = json.loads(tool_call.function.arguments)
            result = tavily.search(args["query"])
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result["results"][:3])
            })

print(run_agent("What are the most interesting AI agent projects from the last 2 weeks?"))
