# Hackathon Prep Plan

## Steps

| # | Task | Status |
|---|------|--------|
| 1 | Build blank agent template | ✅ done → `agent_template.py` |
| 2 | Practice wrapping a sponsor API as a tool | ✅ done → `sponsor_tool_practice.py` |
| 3 | Add streaming output to the template | ✅ done → see below |
| 4 | Think through your pitch | ✅ done → see below |

---

## Step 1 — Blank Agent Template ✅
**File:** `agent_template.py`

Clean skeleton with `# ← EDIT THIS` on every line to change.
Open it at 9:30 AM, copy it, slot in your tool, run it.

---

## Step 2 — Sponsor API Practice ✅
**File:** `sponsor_tool_practice.py`

**Skill drilled:** read docs → define tool schema → write `handle_tool` branch → drop it in.

**Reka** (multimodal LLM — chosen for practice):
```python
# pip install "reka-api>=2.0.0"  |  REKA_API_KEY in .env
from reka.client import Reka
reka = Reka(api_key=os.getenv("REKA_API_KEY"))

response = reka.chat.create(
    messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    model="reka-flash"   # or "reka-core" for harder tasks
)
return response.responses[0].message.content
# ↑ note: NOT .choices[0] — this is different from OpenAI
```

**Yutori** (Research / Browsing — co-founder is a judge, use it):
```python
# YUTORI_API_KEY in .env  |  no SDK needed
import requests, time

def yutori_research(query):
    headers = {"x-api-key": os.getenv("YUTORI_API_KEY"), "Content-Type": "application/json"}
    r = requests.post("https://api.yutori.com/v1/client/research",
                      headers=headers, json={"query": query})
    task_id = r.json()["task_id"]
    for _ in range(30):          # poll up to ~2.5 min
        time.sleep(5)
        r = requests.get(f"https://api.yutori.com/v1/client/research/{task_id}", headers=headers)
        data = r.json()
        if data.get("status") == "completed":
            return json.dumps(data.get("result", ""))
    return "research timed out"
```

**Key rule:** The tool `description` field is what the LLM reads to decide when to call it.
Write it to answer "when should I use this?" — not "what does it do internally."

---

## Step 3 — Streaming Output ✅

**Why bother:** without streaming, your demo shows a blank terminal for 10 seconds then
dumps everything at once. With streaming, judges see it working in real time. Much better demo.

**The tricky part:** when you stream, the response comes back as chunks. Tool calls are also
chunked — you have to accumulate the pieces before you can execute them. The loop structure
changes slightly.

**Full drop-in replacement for `run_agent()`:**

```python
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
            stream=True          # ← only change from non-streaming
        )

        # --- Accumulate the stream ---
        content    = ""
        tool_calls = []          # list of dicts, built up from chunks

        for chunk in stream:
            delta = chunk.choices[0].delta

            # Print content tokens as they arrive
            if delta.content:
                print(delta.content, end="", flush=True)
                content += delta.content

            # Accumulate tool call chunks
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    # Grow the list to fit this index
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
            args   = json.loads(tc["function"]["arguments"])
            print(f"\n  → calling {tc['function']['name']}({args})")
            result = handle_tool(tc["function"]["name"], args)
            messages.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      result
            })
```

**What changed vs the non-streaming version:**
- `create(..., stream=True)` returns an iterator, not a response object
- You loop over chunks and accumulate `content` and `tool_calls` manually
- The assistant message is built by hand (not `msg = response.choices[0].message`)
- Everything else — the while loop, handle_tool(), the tool result append — is identical

---

## Step 4 — Pitch Framework ✅

### The one-sentence test
Before writing any code, complete this sentence:

> "My agent takes **[input]**, automatically does **[multi-step work]**, and produces **[output]** — which normally takes a person **[time/effort]**."

If you can't complete it, the idea isn't scoped yet.

---

### Strong idea patterns for this hackathon

These work because they're demonstrable in real time and naturally use the sponsor APIs:

| Pattern | Example | APIs |
|---|---|---|
| Research → report | "Research competitor X and write a brief" | Yutori Research + Tavily |
| Monitor → alert | "Watch this website, notify me when price drops" | Yutori Scouting |
| Data → structured output | "Turn these URLs into a comparison table" | Yutori Browsing + Reka |
| Task automation | "Fill out this form / extract this data from a site" | Yutori Browsing |
| Content pipeline | "Search → analyze → draft → save" | Tavily + Reka + file save |

---

### What judges actually care about

1. **Does it work?** A live demo beats a polished slide every time.
2. **Is the problem real?** "This saves me 2 hours a week" > "this is technically impressive."
3. **Did you use sponsor APIs?** Judges represent those companies. Name-drop deliberately.
4. **Can it scale?** One throwaway line about "in production this would..." is enough.

---

### The 60-second demo script structure

```
"The problem: [one sentence — what's painful/slow today]

Our agent: [one sentence — what it does]

Watch: [type the input live, let the streaming output show the work happening]

Result: [show the output — a file, a report, a saved result]

We used [Sponsor API] for [specific step] because [why it was the right tool]."
```

Practice this before 11 AM. The coding is the easy part — judges remember the pitch.

---

### Which APIs to mention to which judges
- **Yutori** — Dhruv Batra (co-founder, judge). Even one tool call to Yutori = noticed.
- **Reka** — Josemaria Soriano (Product & Growth, judge). Use for anything generative/analytical.
- **Tavily** — Sofia Guzowski + Greta Ernst (both judges). Already in your code, mention it.
- **AWS** — Jon Turdiev (judge). If you deploy to Render or mention cloud infra, nod to AWS.

---

---

# DAY-OF GUIDE
## 9:30 AM → 4:30 PM

---

## Schedule

| Time | Event | Action |
|---|---|---|
| 9:30 AM | Doors open | Laptop out, run setup checklist below |
| 9:45 AM | Keynote | Listen for sponsor API mentions / free credits |
| 10:00–11:00 | Sponsor tables open | Get API keys, decide what you're building |
| 11:00 AM | Coding starts | You should know your idea by now |
| 1:30 PM | Lunch | Hard stop — step away, reset |
| 3:30 PM | Feature freeze | Whatever works, works. Polish the demo. |
| 4:15 PM | Stop coding | Run through the demo script, make a backup recording |
| 4:30 PM | Submission | Submit |

---

## Morning Setup Checklist (run before coding starts)

```bash
cd ~/Downloads/Votal\ Docs/Autonomous\ Agents\ Hackathon/agent-prep

# 1. Check your keys are there
cat .env
# Should have: OPENAI_API_KEY, TAVILY_API_KEY
# Add new sponsor keys as you get them at the event

# 2. Confirm things still work
python main.py

# 3. Start your new agent from the template
cp agent_template.py my_agent.py
# open my_agent.py and fill in the EDIT THIS lines
```

---

## Adding Any New Sponsor API (5-minute checklist)

When someone hands you an API key at the event:

- [ ] Add `THEIR_KEY=...` to `.env`
- [ ] `pip install their-sdk` (or just use `requests`)
- [ ] Copy a tool block from `agent_template.py`, paste into your `tools` list
- [ ] Edit: `name`, `description`, `parameters`
- [ ] Add an `elif tool_name == "..."` branch in `handle_tool()`
- [ ] Test the function call directly (hardcode args) before wiring into the agent
- [ ] Done — the loop is unchanged

---

## When Things Break

| Symptom | Likely cause | Fix |
|---|---|---|
| Agent loops forever | Tool returns an error string; LLM keeps retrying | Print what `handle_tool()` returns; fix the API call |
| Tool never gets called | Description too vague | Add "Use X tool when you need to Y" to system prompt |
| `KeyError` in tool | Wrong param name | Print `args` at top of `handle_tool()` to see what arrived |
| Streaming crashes on append | Building assistant message wrong | Use the exact structure from Step 3 above |
| API call 401/403 | Key not loaded | `print(os.getenv("KEY"))` — check `.env` spelling |
| Out of time at 3:30 | Scope too big | Cut to one working tool, get a demo-able state |

---

## Emergency Fallback

If nothing new works by 3:30 PM:

1. Open `research_agent.py` — it already works end-to-end
2. Change the last line to a query relevant to your idea
3. Run it, record the output
4. Demo that with a story around it

A working demo of a simple agent beats a broken demo of an ambitious one.
