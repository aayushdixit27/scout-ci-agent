# HACKATHON ASSISTANT — READ THIS FIRST

You are Aayush's AI co-pilot for the Autonomous Agents Hackathon. Your job is to help him go from blank slate → working demo → confident pitch.

**On first message from Aayush:**
Ask him one question: "What's the challenge / idea space you're working in?" Then immediately spin up research agents (via the Task tool) in parallel to find:
1. **The real problem** — who has the pain, how often, what it costs them
2. **A humble-guide solution** — the simplest agent that demonstrably solves it (not the most impressive, the most *completable*)
3. **Clear stakes and results** — what the output looks like, what a judge sees in real time

While agents run, help Aayush fill in the one-sentence test:
> "My agent takes **[input]**, automatically does **[multi-step work]**, and produces **[output]** — which normally takes a person **[time/effort]**."

Don't let him start coding until that sentence is done.

---

## WORKING DIRECTORY

```
~/Downloads/Votal Docs/Autonomous Agents Hackathon/agent-prep/
```

Key files already there:
- `agent_template.py` — streaming agent skeleton, ready to copy
- `sponsor_tool_practice.py` — Reka + Tavily tool wrappers, working example
- `research_agent.py` — end-to-end working fallback (emergency use)
- `.env` — has `OPENAI_API_KEY`, `TAVILY_API_KEY`, `REKA_API_KEY`

**Day-of workflow:**
```bash
cp agent_template.py my_agent.py
# open my_agent.py, fill in the ← EDIT THIS lines
# test handle_tool() in isolation before wiring into the loop
```

---

## SCHEDULE

| Time | Event | Action |
|---|---|------|
| 9:30 AM | Doors open | Laptop out, run `python main.py`, confirm .env keys work |
| 9:45 AM | Keynote | Listen for sponsor API mentions / free credits |
| 10:00–11:00 | Sponsor tables | Get API keys, decide what you're building |
| **11:00 AM** | **Coding starts** | **Idea must be locked by now** |
| 1:30 PM | Lunch | Hard stop — step away, reset |
| **3:30 PM** | **Feature freeze** | Whatever works, works. Polish demo. |
| 4:15 PM | Stop coding | Run through demo script, make backup recording |
| 4:30 PM | Submission | Submit |

---

## SPONSOR API CHEAT SHEETS

Try to use these APIs where they naturally fit. Don't force it — a clean working demo with one API beats a broken demo with five.

---

### YUTORI — Web Agents & Monitoring
**Judge: Dhruv Batra (co-founder). Even one Yutori call = noticed.**

Yutori runs actual browsers. Use it when you need to interact with pages (click, fill, navigate JS-heavy sites) or monitor the web over time. Not a search API — it's an agent that operates the browser for you.

**Four APIs:**

```
Base URL: https://api.yutori.com/v1
Auth: X-API-KEY header (or x-api-key)
```

**1. Research API** — multi-agent deep research (~5-10 min, 76 parallel subagents)
```python
import requests, time, json, os

def yutori_research(query):
    headers = {"X-API-KEY": os.getenv("YUTORI_API_KEY"), "Content-Type": "application/json"}
    r = requests.post("https://api.yutori.com/v1/research/tasks",
                      headers=headers, json={"query": query})
    task_id = r.json()["task_id"]
    for _ in range(60):          # poll up to 5 min
        time.sleep(5)
        r = requests.get(f"https://api.yutori.com/v1/research/tasks/{task_id}", headers=headers)
        data = r.json()
        if data.get("status") == "completed":
            return json.dumps(data.get("result", ""))
    return "research timed out"
```

**2. Browsing API** — single-task browser automation (fills forms, extracts data, handles JS)
```python
def yutori_browse(task, start_url):
    headers = {"X-API-KEY": os.getenv("YUTORI_API_KEY"), "Content-Type": "application/json"}
    r = requests.post("https://api.yutori.com/v1/browsing/tasks",
                      headers=headers, json={"task": task, "start_url": start_url})
    task_id = r.json()["task_id"]
    for _ in range(30):
        time.sleep(5)
        r = requests.get(f"https://api.yutori.com/v1/browsing/tasks/{task_id}", headers=headers)
        data = r.json()
        if data.get("status") == "completed":
            return json.dumps(data.get("result", ""))
    return "browse timed out"
```

**3. Scouting API** — schedule recurring monitors (daily/weekly alerts)
```python
def yutori_create_scout(query, interval_seconds=86400):
    headers = {"X-API-KEY": os.getenv("YUTORI_API_KEY"), "Content-Type": "application/json"}
    r = requests.post("https://api.yutori.com/v1/scouts",
                      headers=headers,
                      json={"query": query, "output_interval": interval_seconds})
    return r.json()   # returns scout_id, use GET /v1/scouts/{id}/updates for results
```

**4. n1 Model API** — their own VLM for browser actions (OpenAI-compatible)
```python
from openai import OpenAI
n1 = OpenAI(api_key=os.getenv("YUTORI_API_KEY"), base_url="https://api.yutori.com/v1")
response = n1.chat.completions.create(model="n1-latest", messages=[...])
```

**Best hackathon fits for Yutori:**
- Monitor competitor pricing / job listings / product drops → Scouting API
- Extract data from JS-heavy sites or pages requiring login → Browsing API
- Deep research report on a company/topic → Research API
- Any "watch this for me and alert me" demo → Scouting API (very impressive live)

**Quirks:**
- All tasks are async. Always poll or use `webhook_url`.
- Research takes minutes — plan your demo accordingly (run it before judges arrive).
- Structured output: pass a Pydantic model to get typed results.

---

### REKA — Multimodal LLM (image, video, audio, text)
**Judge: Josemaria Soriano (Product & Growth). Use for anything generative/analytical.**

Reka's models are natively multimodal from pretraining — not text-first with vision bolted on. Reka Flash is 3x cheaper than GPT-4o on input tokens.

**Models:**
| Model | Use |
|---|---|
| `reka-flash` | General chat, coding, reasoning, multimodal. Cheapest. |
| `reka-core` | Frontier-class, harder tasks |
| `reka-flash-research` | Agentic web search with character-level citations |

**CRITICAL: Response path is different from OpenAI**
```python
# OpenAI:  response.choices[0].message.content
# Reka:    response.responses[0].message.content   ← don't forget this
```

**Text chat:**
```python
from reka.client import Reka
reka = Reka(api_key=os.getenv("REKA_API_KEY"))

response = reka.chat.create(
    messages=[{"role": "user", "content": "Your prompt here"}],
    model="reka-flash"
)
return response.responses[0].message.content
```

**Multimodal (image):**
```python
response = reka.chat.create(
    messages=[{"role": "user", "content": [
        {"type": "image_url", "image_url": "https://..."},   # ← image FIRST
        {"type": "text",      "text": "What's in this?"}    # ← text AFTER
    ]}],
    model="reka-flash"
)
return response.responses[0].message.content
```

**Multimodal (video):**
```python
response = reka.chat.create(
    messages=[{"role": "user", "content": [
        {"type": "video_url", "video_url": "https://..."},
        {"type": "text", "text": "Summarize this video"}
    ]}],
    model="reka-core"
)
```

**Reka Research (web-grounded, with citations) — OpenAI-compatible:**
```python
from openai import OpenAI
reka_research = OpenAI(api_key=os.getenv("REKA_API_KEY"), base_url="https://api.reka.ai/v1")
response = reka_research.chat.completions.create(
    model="reka-flash-research",
    messages=[{"role": "user", "content": "Your query"}]
)
# response.choices[0].message.content  ← OpenAI format here
# Also has: .annotations (list of url_citation with start_index, end_index, url, title)
```

**Best hackathon fits for Reka:**
- Analyze images/screenshots → Flash multimodal
- Video understanding, clip summarization → Core
- Research with auditable citations → reka-flash-research
- Anything where you need generative analysis and want to name-drop a non-OpenAI model

**Quirks:**
- Media (image/video) must come BEFORE text in content arrays
- Native Chat API auth: `X-Api-Key` header (SDK handles this)
- Research model auth: OpenAI-compat format (swap base_url + same key)
- `reka-flash-research` pricing is flat per query ($25/1K), not per token

---

### TAVILY — LLM-Optimized Web Search
**Judges: Sofia Guzowski + Greta Ernst. Already in your code — mention it explicitly.**

Tavily is not a Google/Bing wrapper. It runs its own search + AI scoring pipeline and returns pre-extracted, LLM-ready text. Eliminates the scrape-clean-chunk pipeline entirely.

**Already installed:** `pip install tavily-python` / `from tavily import TavilyClient`

**Basic search:**
```python
from tavily import TavilyClient
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

results = tavily.search("your query", max_results=5)
# results["results"] → list of {title, url, content, score}
# results["answer"] → AI-generated summary (if include_answer=True)
```

**Full parameter reference:**
```python
results = tavily.search(
    query="your query",
    search_depth="basic",       # "basic" | "advanced" (2x credits, higher recall)
    topic="general",            # "general" | "news" | "finance"
    max_results=5,              # 1–20
    include_answer=True,        # get an AI-written summary inline
    include_raw_content=False,  # full page text (big, use sparingly)
    include_images=False,
    time_range="week",          # "day" | "week" | "month" | "year"
    include_domains=[],         # whitelist
    exclude_domains=[],         # blacklist
)
```

**Extract content from specific URLs:**
```python
extracted = tavily.extract(urls=["https://...", "https://..."])
# extracted["results"] → list of {url, raw_content}
# extracted["failed_results"] → always check this
```

**Response fields that matter:**
```python
results["results"][0]["content"]   # clean extracted text, LLM-ready
results["results"][0]["score"]     # relevance score, already sorted desc
results["answer"]                   # inline AI answer (only if include_answer=True)
```

**Best hackathon fits for Tavily:**
- Fast real-time search as a tool in any agent → basic search
- News monitoring with `topic="news"` + `time_range="day"` → freshness-sensitive agents
- Domain-restricted research → `include_domains=["docs.aws.amazon.com"]`
- Any step where you need "find current info about X"

**Quirks:**
- Credits don't roll over. Free tier: 1,000/month. Basic search = 1 credit. Advanced = 2.
- `include_raw_content=True` can blow up your context window — use carefully.
- `extract()` fails silently per URL — always check `failed_results`.
- `country` param only works with `topic="general"`, silently ignored otherwise.

---

### AWS
**Judge: Jon Turdiev. One throwaway line about cloud infra = noticed.**

If you deploy to Render, Railway, or mention production scale: "In production this would run on AWS Lambda / ECS with auto-scaling." That's enough. If you use S3 for file output, mention it.

---

## AGENT CODE PATTERNS

### Streaming Agent Loop (already in `agent_template.py`)
```python
def run_agent(user_message):
    messages = [
        {"role": "system", "content": "You are a ??? agent..."},
        {"role": "user",   "content": user_message}
    ]
    while True:
        stream = client.chat.completions.create(
            model="gpt-4o", messages=messages, tools=tools, stream=True
        )
        content, tool_calls = "", []
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                print(delta.content, end="", flush=True)
                content += delta.content
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    while len(tool_calls) <= tc.index:
                        tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                    if tc.id:              tool_calls[tc.index]["id"] = tc.id
                    if tc.function.name:   tool_calls[tc.index]["function"]["name"] += tc.function.name
                    if tc.function.arguments: tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments

        assistant_msg = {"role": "assistant", "content": content}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {"id": tc["id"], "type": "function", "function": tc["function"]}
                for tc in tool_calls
            ]
        messages.append(assistant_msg)
        if not tool_calls:
            print(); return

        for tc in tool_calls:
            args = json.loads(tc["function"]["arguments"])
            print(f"\n  → calling {tc['function']['name']}({args})")
            result = handle_tool(tc["function"]["name"], args)
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
```

### Adding a New Tool (5-min checklist)
```
1. Add key to .env: NEW_KEY=...
2. pip install their-sdk  (or just use requests)
3. Copy a tool block in tools[], edit name / description / parameters
4. Add elif branch in handle_tool()
5. Test handle_tool() directly with hardcoded args BEFORE wiring into agent
6. Done — loop is unchanged
```

### Tool description rules
- Bad:  `"Calls the Yutori research API"`
- Good: `"Use this when you need to research a topic in depth across multiple web sources"`
- It answers "when should I call this?" not "what does it do internally"

---

## PITCH FRAMEWORK

### The one-sentence test (must complete before coding)
> "My agent takes **[input]**, automatically does **[multi-step work]**, and produces **[output]** — which normally takes a person **[time/effort]**."

### 60-second demo script
```
"The problem: [one sentence — what's painful/slow today]

Our agent: [one sentence — what it does]

Watch: [type the input live, streaming output shows work happening]

Result: [show the output — a file, a report, a saved result]

We used [Sponsor API] for [specific step] because [why it was the right tool]."
```

### What judges care about (in order)
1. Does it work? Live demo beats slides every time.
2. Is the problem real? "Saves me 2 hours a week" > "technically impressive."
3. Did you use sponsor APIs? Name-drop deliberately.
4. Can it scale? One line: "In production this would..." is enough.

### Strong idea patterns
| Pattern | Example | Best APIs |
|---|---|---|
| Research → report | "Research competitor X and write a brief" | Yutori Research + Tavily |
| Monitor → alert | "Watch this site, notify me when price drops" | Yutori Scouting |
| Data → structured output | "Turn these URLs into a comparison table" | Tavily extract + Reka |
| Task automation | "Fill out this form / extract data from a site" | Yutori Browsing |
| Content pipeline | "Search → analyze → draft → save" | Tavily + Reka + file save |
| Media analysis | "Analyze this video/image and summarize findings" | Reka multimodal |

---

## WHEN THINGS BREAK

| Symptom | Likely cause | Fix |
|---|---|---|
| Agent loops forever | Tool returns error string; LLM keeps retrying | Print `handle_tool()` return value; fix the API call |
| Tool never gets called | Description too vague | Add "Use X tool when you need to Y" to system prompt |
| `KeyError` in tool | Wrong param name | Print `args` at top of `handle_tool()` |
| Streaming crashes on append | Building assistant message wrong | Use exact structure from agent_template.py |
| 401/403 | Key not loaded | `print(os.getenv("KEY"))` — check .env spelling |
| Yutori times out | Research takes 5-10 min by design | Run before demo; show result, not the wait |
| Reka wrong response path | Using `choices[0]` instead of `responses[0]` | `response.responses[0].message.content` |
| Out of time at 3:30 | Scope too big | Cut to one working tool, get a demo-able state |

---

## EMERGENCY FALLBACK

If nothing new works by 3:30 PM:
1. Open `research_agent.py` — already works end-to-end
2. Change the last line to a query relevant to your idea
3. Run it, record the output
4. Demo that with a story around it

**A working demo of a simple agent beats a broken demo of an ambitious one.**

---

## JUDGES & SPONSORS (name-drop deliberately)

| Judge | Company | What to say |
|---|---|---|
| Dhruv Batra | Yutori (co-founder) | "We used Yutori's Research API to..." |
| Josemaria Soriano | Reka (Product & Growth) | "We used Reka Flash for [multimodal/analytical step] because..." |
| Sofia Guzowski | Tavily | "Tavily's LLM-optimized search eliminated our whole scraping pipeline" |
| Greta Ernst | Tavily | Same |
| Jon Turdiev | AWS | "In production this would scale on AWS [Lambda/ECS]" |
