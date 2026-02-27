# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 PRACTICE: Wrapping a sponsor API as a tool
#
# SKILL BEING DRILLED:
#   read docs → define tool schema → write handle_tool branch → drop it in
#
# THIS FILE: wraps Reka's multimodal API as a tool inside an OpenAI agent.
#   - OpenAI (gpt-4o) does the reasoning and decides when to call tools
#   - Reka handles image analysis (its multimodal strength)
#   - Tavily handles web search
#
# REKA DOCS:  https://docs.reka.ai
# REKA SETUP: pip install "reka-api>=2.0.0"
#             REKA_API_KEY=... in .env
# ─────────────────────────────────────────────────────────────────────────────

from openai import OpenAI
from reka.client import Reka
from tavily import TavilyClient
import json, os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()
reka   = Reka(api_key=os.getenv("REKA_API_KEY"))
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# ─────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for current information on any topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        }
    },
    # ── NEW SPONSOR TOOL ──────────────────────────────────────────────────────
    # Pattern to replicate tomorrow for any new API:
    #   1. name: snake_case, descriptive
    #   2. description: tell the LLM WHEN to use it (it reads this to decide)
    #   3. parameters: only what you actually need, keep it minimal
    {
        "type": "function",
        "function": {
            "name": "analyze_image_with_reka",
            "description": "Use Reka's multimodal model to analyze an image and answer a question about it. Use this when the task involves understanding visual content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_url": {"type": "string", "description": "Public URL of the image to analyze"},
                    "question":  {"type": "string", "description": "What to ask or look for in the image"}
                },
                "required": ["image_url", "question"]
            }
        }
    }
]

# ─────────────────────────────────────────────
# TOOL EXECUTION
# ─────────────────────────────────────────────
def handle_tool(tool_name, args):
    if tool_name == "search_web":
        results = tavily.search(args["query"])
        return json.dumps(results["results"][:3])

    elif tool_name == "analyze_image_with_reka":
        # Reka's message format differs from OpenAI:
        #   content is a LIST of typed chunks, not a plain string
        response = reka.chat.create(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": args["image_url"]},
                    {"type": "text",      "text":      args["question"]}
                ]
            }],
            model="reka-flash"   # or "reka-core" for the big model
        )
        # Reka response path: response.responses[0].message.content
        # (different from OpenAI: response.choices[0].message.content)
        return response.responses[0].message.content

# ─────────────────────────────────────────────
# AGENT LOOP — unchanged from template
# ─────────────────────────────────────────────
def run_agent(user_message):
    messages = [
        {"role": "system", "content": "You are a multimodal research agent. You can search the web and analyze images. Use Reka for anything visual."},
        {"role": "user",   "content": user_message}
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

run_agent("Analyze this image and describe what you see: https://v0.docs.reka.ai/_images/000000245576.jpg")
