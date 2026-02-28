# Scout — Sponsor Tools Tracker
*Autonomous Agents Hackathon · Feb 27, 2026*

---

## Prize Targets

| Sponsor | Prize | Requirement | Status |
|---|---|---|---|
| Senso | **$3,000** 1st | Self-improving agent | ✅ |
| Modulate | **$1,000** 1st | Voice input + emotion detection | ✅ |
| Yutori | **$1,000** 1st | Research API used | ✅ |
| Tavily | Credits | Search API used, judges present | ✅ |
| Neo4j | Bose + credits | Visual graph on screen | ✅ |
| Render | Credits | Web service + cron job (2 services) | ✅ |

---

## Tool-by-Tool Detail

### ✅ Yutori — Research API
- **What we do:** `prebake.py` runs Yutori Research API on Salesforce, HubSpot, Notion ahead of demo. `load_prebaked()` in `scout.py` loads results into the agent context.
- **Endpoint:** `POST https://api.yutori.com/v1/research/tasks` → poll until `status: succeeded`
- **Auth:** `X-API-KEY` header
- **Prebaked files:** `prebaked/salesforce.json`, `hubspot.json`, `notion.json`
- **Judge line:** *"Yutori's Research API runs 100+ parallel sub-agents — we couldn't get this depth from a search API"*
- **Judge:** Dhruv Batra (co-founder) — using Yutori = noticed

---

### ✅ Tavily — Live News Search
- **What we do:** `search_news_tavily()` in `scout.py` fires on every run. `topic="news"`, `time_range="week"`, `max_results=5`. Returns LLM-ready text, no scraping needed.
- **Endpoint:** Tavily Python SDK — `TavilyClient.search()`
- **Auth:** `TAVILY_API_KEY` env var
- **Fires:** Every single run, live during demo
- **Judge line:** *"Tavily eliminated our entire scraping pipeline — it returns LLM-ready text directly"*
- **Judges:** Sofia Guzowski, Greta Ernst (present at event)

---

### ✅ Neo4j — Knowledge Graph
- **What we do:** `write_to_neo4j()` writes Company, Person, Event nodes + COMPETES_WITH, EMPLOYS, HAD_EVENT relationships on every run.
- **Endpoint:** `bolt://3.87.228.70` (Neo4j sandbox)
- **Auth:** `NEO4J_USERNAME` / `NEO4J_PASSWORD` env vars
- **Visual:** Graph renders live in Flask UI via `vis.js` at `/api/graph` — 31 nodes, 29 edges already in DB. Company=green, Person=blue, Event=yellow.
- **Setup:** `neo4j_setup.py` created constraints + indexes
- **Judge line:** *"Neo4j lets us trace the reasoning path — every relationship between companies, people, and events is queryable and auditable"*
- **Prize requirement:** Visual graph growing on screen ✅ — embedded in Flask UI + collapses/expands

---

### ✅ Modulate — Voice Input + Emotion Detection
- **What we do:** `capture_voice()` in `scout.py` records 5s from mic → POST to Modulate Velma STT → returns transcript + emotion label per utterance.
- **Endpoint:** `POST https://modulate-developer-apis.com/api/velma-2-stt-batch`
- **Auth:** `X-API-Key` header with `MODULATE_API_KEY`
- **Fields sent:** `upload_file` (wav), `emotion_signal: true`, `speaker_diarization: true`
- **Response parsed:** `data["text"]` for transcript, `data["utterances"][0]["emotion"]` for emotion label
- **Used in:** CLI mode (`python3 scout.py` with no args) + voice button in Flask UI (browser Web Speech API → text → agent)
- **Emotion routing:** `urgent` emotion prepends `[URGENT]` to agent message
- **Judge line:** *"Modulate's Velma model gives us emotion detection — the agent knows when a rep is stressed and prioritizes urgent signals"*
- **Prize requirement:** Voice input + emotion detection ✅

---

### ✅ Senso — Self-Improvement / Skill Memory
- **What we do:** `ingest_to_senso()` in `scout.py` uploads each completed battlecard to Senso after every run. 3-step flow: request presigned S3 URL → PUT file to S3 → brief indexed and searchable.
- **Endpoint:** `POST https://apiv2.senso.ai/api/v1/org/ingestion/upload`
- **Auth:** `X-API-Key` header (NOT Bearer — confirmed from docs)
- **Upload flow:** MD5 hash → presigned S3 URL → PUT raw bytes
- **Verified:** Both steps return 200, `content_id` confirmed
- **Judge line:** *"Senso is the self-improvement layer — every brief becomes a skill, Scout gets smarter with every query without retraining"*
- **Prize requirement:** Self-improving agent ✅ — each run stores a new skill

---

### ⚠️ Render — Web Service (partial)
- **What we have:** `flask_app.py` is a production-ready web service. `render.yaml` and `requirements.txt` created. `gunicorn` with `gthread` workers + 120s timeout for SSE.
- **Deployed:** https://github.com/aayushdixit27/scout-ci-agent
- **Web service:** `scout-ci-agent` — Flask app with SSE streaming, live on Render
- **Cron job:** `scout-prebake-refresh` — runs `prebake.py` nightly at 2AM, refreshes research
- **Judge line:** *"In production this runs on Render — web service handles the live UI, cron job pre-researches companies from the calendar the night before"*

---

## OpenAI (non-prize, required)
- `gpt-4o` — agent orchestration, tool calling, battlecard generation
- `tts-1` / `alloy` voice — CLI mode spoken brief (`speak_brief()`)
- Browser `SpeechSynthesis` used in Flask UI instead (avoids server-side audio timing issues)

---

## What Each Demo Run Shows Judges

```
[Voice input]  →  Modulate transcription + emotion tag
[Tool 1]       →  research_company   — Yutori prebaked deep research
[Tool 2]       →  search_news        — Tavily live news (this week)
[Tool 3]       →  save_to_graph      — Neo4j nodes growing (visible in graph panel)
[Tool 4]       →  store_in_senso     — Senso skill stored (self-improvement)
[Output]       →  Battlecard streams in + spoken aloud
[UI]           →  Company logo · pipeline cards · knowledge graph
[Backend]      →  Flask on Render (web service)
```

---

## Files Reference

| File | Purpose |
|---|---|
| `scout.py` | Main agent — all tool implementations |
| `flask_app.py` | Web dashboard — SSE streaming, `/api/graph` |
| `templates/index.html` | UI — pipeline cards, battlecard, graph panel |
| `prebake.py` | Pre-run Yutori Research on demo companies |
| `neo4j_setup.py` | One-time DB constraints + indexes |
| `prebaked/salesforce.json` | Yutori result — Salesforce |
| `prebaked/hubspot.json` | Yutori result — HubSpot |
| `prebaked/notion.json` | Yutori result — Notion |
| `render.yaml` | Render deploy config |
| `requirements.txt` | Python dependencies |
| `.env` | All API keys |
