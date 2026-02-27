#!/usr/bin/env python3
"""
SCOUT — Competitive Intelligence Agent for Sales Reps
======================================================
A rep speaks (or types) a company name.
Scout researches it across the live web, builds a knowledge graph,
stores the pattern in Senso, and returns a spoken + visual battlecard.

Usage:
  python scout.py "Salesforce"          # CLI mode (fast, good for testing)
  python scout.py                        # Voice mode (Modulate mic input)

APIs: Yutori Research, Tavily, Neo4j, Senso, Modulate, OpenAI
"""

import os, sys, json, time, requests
from openai import OpenAI
from tavily import TavilyClient
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# ── CLIENTS ──────────────────────────────────────────────────────────────────
openai_client = OpenAI()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)
NEO4J_DB = os.getenv("NEO4J_DATABASE", "neo4j")

YUTORI_HEADERS = {
    "X-API-KEY": os.getenv("YUTORI_API_KEY"),
    "Content-Type": "application/json"
}

# ─────────────────────────────────────────────────────────────────────────────
# YUTORI
# ─────────────────────────────────────────────────────────────────────────────

def yutori_research_live(query: str) -> str:
    """Run Yutori Research live. Takes 5-10 min. Only for non-demo use."""
    try:
        r = requests.post(
            "https://api.yutori.com/v1/research/tasks",
            headers=YUTORI_HEADERS,
            json={"query": query},
            timeout=30
        )
        r.raise_for_status()
        task_id = r.json()["task_id"]
        for _ in range(72):
            time.sleep(10)
            r = requests.get(
                f"https://api.yutori.com/v1/research/tasks/{task_id}",
                headers=YUTORI_HEADERS,
                timeout=15
            )
            data = r.json()
            if data.get("status") in ("completed", "succeeded"):
                return json.dumps(data.get("result", ""))
        return "Yutori research timed out"
    except Exception as e:
        return f"Yutori research error: {e}"

def load_prebaked(company: str) -> str:
    """Load pre-run Yutori Research result from disk. Use for demo."""
    path = f"prebaked/{company.lower().replace(' ', '_').replace('.', '')}.json"
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        # Extract the result text from Yutori's response structure
        result = data.get("result", data)
        if isinstance(result, dict):
            return json.dumps(result)
        return str(result)
    # Try fuzzy match
    import glob
    matches = glob.glob(f"prebaked/*{company.lower().split()[0]}*.json")
    if matches:
        with open(matches[0]) as f:
            data = json.load(f)
        result = data.get("result", data)
        return json.dumps(result) if isinstance(result, dict) else str(result)
    return f"No prebaked data for '{company}'. Add to prebake.py and run it."

# ─────────────────────────────────────────────────────────────────────────────
# TAVILY
# ─────────────────────────────────────────────────────────────────────────────

def search_news_tavily(query: str) -> str:
    """Live news search — fast, runs during demo."""
    try:
        results = tavily.search(
            query,
            search_depth="basic",
            topic="news",
            time_range="week",
            max_results=5
        )
        items = results.get("results", [])
        return json.dumps([
            {"title": r["title"], "url": r["url"], "content": r["content"][:400]}
            for r in items
        ])
    except Exception as e:
        return f"Tavily search error: {e}"

# ─────────────────────────────────────────────────────────────────────────────
# NEO4J
# ─────────────────────────────────────────────────────────────────────────────

def write_to_neo4j(company: str, data: dict) -> str:
    """Write company entities and relationships to Neo4j knowledge graph."""
    try:
        with neo4j_driver.session(database=NEO4J_DB) as session:
            # Company node
            session.run(
                "MERGE (c:Company {name: $name}) SET c.summary = $summary, c.updated = $ts",
                name=company,
                summary=data.get("summary", ""),
                ts=int(time.time())
            )
            # Competitors → COMPETES_WITH edges
            for rival in data.get("competitors", []):
                if rival and rival != company:
                    session.run(
                        """
                        MERGE (c:Company {name: $company})
                        MERGE (r:Company {name: $rival})
                        MERGE (c)-[:COMPETES_WITH]->(r)
                        """,
                        company=company, rival=rival
                    )
            # Key people → EMPLOYS edges
            for person in data.get("key_people", []):
                name = person.get("name", "").strip()
                role = person.get("role", "").strip()
                if name:
                    session.run(
                        """
                        MERGE (c:Company {name: $company})
                        MERGE (p:Person {name: $name})
                        SET p.role = $role
                        MERGE (c)-[:EMPLOYS]->(p)
                        """,
                        company=company, name=name, role=role
                    )
            # Recent events → HAD_EVENT edges
            for i, event in enumerate(data.get("recent_events", [])):
                title = event.get("title", "").strip()
                if title:
                    session.run(
                        """
                        MERGE (c:Company {name: $company})
                        MERGE (e:Event {id: $event_id})
                        SET e.title = $title, e.date = $date
                        MERGE (c)-[:HAD_EVENT]->(e)
                        """,
                        company=company,
                        event_id=f"{company}_{i}_{int(time.time())}",
                        title=title,
                        date=event.get("date", "2026")
                    )
        nodes = (1 + len(data.get("competitors", [])) +
                 len(data.get("key_people", [])) +
                 len(data.get("recent_events", [])))
        return f"✅ Neo4j graph updated: {nodes} nodes written for {company}"
    except Exception as e:
        return f"Neo4j write error: {e}"

# ─────────────────────────────────────────────────────────────────────────────
# SENSO
# ─────────────────────────────────────────────────────────────────────────────

def ingest_to_senso(company: str, brief: str) -> str:
    """Store completed brief in Senso via presigned S3 upload flow."""
    import hashlib
    api_key = os.getenv("SENSO_API_KEY")
    if not api_key:
        return "Senso key not set — skipping (non-blocking)"
    try:
        BASE = "https://apiv2.senso.ai/api/v1"
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        file_bytes = brief.encode("utf-8")
        filename = f"scout_brief_{company.lower().replace(' ', '_')}_{int(time.time())}.txt"

        # Step 1 — request presigned upload URL
        r = requests.post(f"{BASE}/org/ingestion/upload", headers=headers, json={
            "files": [{
                "filename": filename,
                "file_size_bytes": len(file_bytes),
                "content_type": "text/plain",
                "content_hash_md5": hashlib.md5(file_bytes).hexdigest()
            }]
        }, timeout=10)
        r.raise_for_status()
        result = r.json()["results"][0]
        if result.get("status") not in ("upload_pending",):
            return f"Senso upload init failed: {result.get('status')} — {result.get('error')}"

        # Step 2 — PUT file to S3 (no API key needed)
        s3 = requests.put(result["upload_url"], data=file_bytes, timeout=15)
        if s3.status_code not in (200, 204):
            return f"Senso S3 upload failed: {s3.status_code}"

        return f"✅ Brief stored in Senso (content_id: {result['content_id']})"
    except Exception as e:
        return f"Senso ingest failed: {e} (non-blocking)"

# ─────────────────────────────────────────────────────────────────────────────
# MODULATE — VOICE INPUT
# ─────────────────────────────────────────────────────────────────────────────

def capture_voice() -> dict:
    """Record 5s from mic → Modulate transcription + emotion detection."""
    try:
        import sounddevice as sd
        import scipy.io.wavfile as wav
        import tempfile, numpy as np

        print("\n[SCOUT] 🎙  Listening... (5 seconds)")
        sample_rate = 16000
        recording = sd.rec(
            int(5 * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16"
        )
        sd.wait()
        print("[SCOUT]    Recording done, transcribing...")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav.write(f.name, sample_rate, recording)
            audio_path = f.name

        api_key = os.getenv("MODULATE_API_KEY")
        with open(audio_path, "rb") as audio_file:
            r = requests.post(
                "https://modulate-developer-apis.com/api/velma-2-stt-batch",
                headers={"X-API-Key": api_key},
                files={"upload_file": ("audio.wav", audio_file, "audio/wav")},
                data={"emotion_signal": "true", "speaker_diarization": "true"},
                timeout=30
            )
        r.raise_for_status()
        data = r.json()
        transcript = data.get("text", "")
        # Emotion comes from first utterance
        utterances = data.get("utterances", [])
        emotion_label = utterances[0].get("emotion", "Neutral") if utterances else "Neutral"
        return {
            "text":       transcript,
            "emotion":    emotion_label.lower(),
            "confidence": 1.0
        }
    except ImportError:
        print("[SCOUT] sounddevice not installed — falling back to text input")
        return _text_fallback()
    except Exception as e:
        print(f"[SCOUT] Voice capture failed ({e}) — falling back to text input")
        return _text_fallback()

def _text_fallback() -> dict:
    text = input("[SCOUT] Type company name: ").strip()
    return {"text": text, "emotion": "neutral", "confidence": 1.0}

# ─────────────────────────────────────────────────────────────────────────────
# SPEAK BRIEF (OpenAI TTS)
# ─────────────────────────────────────────────────────────────────────────────

def speak_brief(text: str):
    """Play the brief as audio through speakers."""
    try:
        import tempfile, subprocess
        # Take the first 600 chars — enough to impress judges
        snippet = text[:600].replace("#", "").replace("*", "")
        response = openai_client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=snippet
        )
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            response.stream_to_file(f.name)
            # macOS: afplay. Linux: mpg123. Fallback: print only.
            subprocess.run(["afplay", f.name], check=False)
    except Exception as e:
        print(f"[SCOUT] TTS playback failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# TOOLS SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

tools = [
    {
        "type": "function",
        "function": {
            "name": "research_company",
            "description": (
                "Get deep competitive intelligence on a company: funding, leadership, "
                "products, pricing, recent moves, and key weaknesses. Always call this "
                "first when a company is mentioned."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "The company to research, e.g. 'Salesforce'"
                    },
                    "use_prebaked": {
                        "type": "boolean",
                        "description": "True to use pre-run research (fast). False to run live Yutori research (5-10 min). Default true."
                    }
                },
                "required": ["company_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": (
                "Search for the latest news and developments about a company or topic "
                "from the past week. Call this after researching the company to get "
                "the most recent updates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "News search query, e.g. 'Salesforce pricing changes 2026'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_to_graph",
            "description": (
                "Save company entities and relationships to the Neo4j knowledge graph. "
                "Call this after researching a company to persist the intelligence for future queries."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "summary":       {"type": "string"},
                            "competitors":   {"type": "array", "items": {"type": "string"}},
                            "key_people": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "role": {"type": "string"}
                                    }
                                }
                            },
                            "recent_events": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "date":  {"type": "string"}
                                    }
                                }
                            }
                        },
                        "required": ["summary"]
                    }
                },
                "required": ["company", "data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "store_in_senso",
            "description": (
                "Store the completed battlecard brief in Senso skill memory so Scout "
                "gets smarter with every query. Always call this as the final step "
                "after generating the brief."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "brief":   {"type": "string", "description": "The full battlecard brief"}
                },
                "required": ["company", "brief"]
            }
        }
    }
]

# ─────────────────────────────────────────────────────────────────────────────
# HANDLE TOOL
# ─────────────────────────────────────────────────────────────────────────────

def handle_tool(name: str, args: dict, emit_event=None) -> str:
    print(f"\n  [{name}] ← {list(args.keys())}")
    if emit_event:
        emit_event("tool_start", {"name": name, "args": list(args.keys())})

    if name == "research_company":
        company      = args["company_name"]
        use_prebaked = args.get("use_prebaked", True)
        if use_prebaked:
            result = load_prebaked(company)
        else:
            result = yutori_research_live(
                f"Competitive intelligence on {company}: funding, leadership, "
                f"products, pricing, weaknesses, recent news, competitors"
            )
        if emit_event:
            emit_event("tool_done", {"name": name, "result": f"Research loaded for {company}", "company": company})
        return result

    if name == "search_news":
        result = search_news_tavily(args["query"])
        if emit_event:
            emit_event("tool_done", {"name": name, "result": "Live news fetched"})
        return result

    if name == "save_to_graph":
        result = write_to_neo4j(args["company"], args["data"])
        if emit_event:
            emit_event("tool_done", {"name": name, "result": result[:120]})
        return result

    if name == "store_in_senso":
        result = ingest_to_senso(args["company"], args["brief"])
        if emit_event:
            emit_event("tool_done", {"name": name, "result": result[:120]})
        return result

    result = f"Unknown tool: {name}"
    if emit_event:
        emit_event("tool_done", {"name": name, "result": result[:120]})
    return result

# ─────────────────────────────────────────────────────────────────────────────
# AGENT LOOP
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Scout, a competitive intelligence agent for B2B sales reps.

When a rep tells you who they're meeting with, you MUST always call all 4 tools in order — no exceptions, even if data is limited:
1. Call research_company() to get deep background on that company
2. Call search_news() with a targeted query for recent news (e.g. "[Company] pricing 2026")
3. ALWAYS call save_to_graph() — use whatever data you have. Infer competitors and key people if not explicitly provided. This is required.
4. Write a battlecard brief in this exact format:

---
## [Company] — Scout Battlecard

**TL;DR**: One sentence a rep can say walking into the room.

### What They Do
2-3 sentences.

### Recent News (This Week)
- [date] Headline — implication for your call
- [date] Headline — implication for your call

### Key People
- Name, Title — one useful fact about them

### Known Weaknesses (from customers / reviews)
- Specific complaint 1
- Specific complaint 2

### Competitors They Fear
- Company A — why
- Company B — why

### 3 Talking Points for Your Call
1. Specific, concrete opener using their recent news
2. Pain point their customers complain about that you solve
3. Competitive angle — where you win vs them

### Red Flags / Watch Out For
- Any concerns worth knowing

### Sources
- [Source title](url) — what it was used for
- [Source title](url) — what it was used for
---

5. ALWAYS call store_in_senso() with company name and the full brief. This is required.

Be specific. Reps need facts, dates, and names — not summaries.
If emotion context is URGENT, front-load the most critical points.
"""

def run_agent(user_message: str, emotion: str = "neutral", emit_event=None, speak: bool = True) -> str:
    if emotion == "urgent":
        user_message = f"[URGENT] {user_message}"

    messages = [
        {"role": "system",  "content": SYSTEM_PROMPT},
        {"role": "user",    "content": user_message}
    ]

    print(f"\n{'='*60}")
    print(f"SCOUT  |  {user_message}")
    if emotion != "neutral":
        print(f"       |  Emotion detected: {emotion.upper()}")
    print(f"{'='*60}\n")

    if emit_event:
        emit_event("status", {"message": f"Running Scout for: {user_message}", "emotion": emotion})

    final_brief = ""

    while True:
        stream = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            stream=True
        )

        content, tool_calls = "", []

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                print(delta.content, end="", flush=True)
                content += delta.content
                if emit_event:
                    emit_event("text_chunk", {"text": delta.content})
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    while len(tool_calls) <= tc.index:
                        tool_calls.append({
                            "id": "", "function": {"name": "", "arguments": ""}
                        })
                    if tc.id:
                        tool_calls[tc.index]["id"] = tc.id
                    if tc.function.name:
                        tool_calls[tc.index]["function"]["name"] += tc.function.name
                    if tc.function.arguments:
                        tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments

        assistant_msg = {"role": "assistant", "content": content}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {"id": tc["id"], "type": "function", "function": tc["function"]}
                for tc in tool_calls
            ]
        messages.append(assistant_msg)

        if not tool_calls:
            print()
            final_brief = content
            if emit_event:
                emit_event("brief_done", {"brief": final_brief})
            break

        for tc in tool_calls:
            args   = json.loads(tc["function"]["arguments"])
            result = handle_tool(tc["function"]["name"], args, emit_event=emit_event)
            messages.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      result
            })

    # Save brief to file
    os.makedirs("output", exist_ok=True)
    ts       = int(time.time())
    outfile  = f"output/brief_{ts}.md"
    with open(outfile, "w") as f:
        f.write(final_brief)
    print(f"\n[SCOUT] Brief saved → {outfile}")

    # Speak the brief — disabled in Flask mode (browser handles TTS via brief_done event)
    if speak:
        speak_brief(final_brief)

    return final_brief

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # CLI: python scout.py "Salesforce"
        company = " ".join(sys.argv[1:])
        run_agent(f"I have a call with {company} in 20 minutes. Give me everything I need.")
    else:
        # Voice mode: python scout.py
        voice = capture_voice()
        print(f"\n[SCOUT] Heard: '{voice['text']}'  (emotion: {voice['emotion']}, confidence: {voice['confidence']:.0%})")
        if not voice["text"].strip():
            print("[SCOUT] Nothing heard. Exiting.")
            sys.exit(1)
        run_agent(voice["text"], emotion=voice["emotion"])
