# BUILDING.md — What's Left
*Last updated: Feb 27, 2026 ~2PM*

---

## DONE ✅
- All keys in `.env`
- All dependencies installed
- `prebaked/salesforce.json`, `hubspot.json`, `notion.json` — all 3 exist
- `scout.py` runs end-to-end
- Tavily firing live
- Yutori prebaked data flowing through
- Neo4j nodes writing (confirmed)
- Senso ingest firing (`store_in_senso` tool called)
- Spoken brief via OpenAI TTS (heard it)
- **Milestones 1, 2, 4 = complete**

---

## REMAINING — in order

### [x] 1. Verify Senso actually worked ✅ DONE — 200 both steps, content_id confirmed
Check the API actually accepted the brief (not just that the tool was called).
```bash
python3 -c "
import requests, os; from dotenv import load_dotenv; load_dotenv()
r = requests.post('https://api.senso.ai/v1/context',
  headers={'Authorization': f'Bearer {os.getenv(\"SENSO_API_KEY\")}', 'Content-Type': 'application/json'},
  json={'content': 'test', 'metadata': {'company': 'test'}})
print(r.status_code, r.text[:200])
"
```
**Pass:** 200 or 201. **Fail:** anything else → fix endpoint at docs.senso.ai.

---

### [ ] 2. Modulate voice input — BLOCKED on correct API URL
`api.modulate.ai` doesn't resolve. Walk to Carter/Graham table, ask: "What's the base URL for the transcription API?"
Then update the URL in scout.py line ~243.
Run with no args — mic should capture → Modulate transcribes → emotion tag → pipeline fires.
```bash
python3 scout.py
```
Speak: *"I have a call with Salesforce"*

**Pass:** transcription printed, emotion tag shown, agent runs.
**Fail:** falls back to text input (acceptable for demo — still mention Modulate verbally).

---

### [ ] 3. Neo4j browser — open graph visually
Open your sandbox URL in Chrome. You should see Company, Person, Event nodes.
This is the visual "wow" moment for judges — graph growing on screen.

Find URL at: sandbox.neo4j.com → your instance → "Open Browser"

**Pass:** nodes visible, relationships shown.

---

### [ ] 4. Record backup demo video
Screen record one clean run of:
```bash
python3 scout.py "Salesforce"
```
Show: terminal with tool calls firing + Neo4j browser tab with graph + spoken brief playing.
Save as `demo_backup.mp4`.

---

### [ ] 5. Devpost submission
Start the submission NOW even if description isn't done. Fill in:
- Project name: Scout
- Tagline: AI-powered competitive intelligence for sales reps — 2 hours of research in 60 seconds
- Sponsor tracks: Senso, Yutori, Modulate, Tavily, Neo4j, Render
- Description: (paste from pitch below)
- Demo video: upload backup recording

---

### [ ] 6. Rehearse pitch 3x out loud
60-second script (from scout.md):

> "Sales teams spend 6 hours a week — $400K a year per 50-person org — manually researching competitors before calls.
>
> Scout changes that.
>
> [speak into mic] 'I have a call with Salesforce in 20 minutes, give me everything.'
>
> [show tool calls firing in terminal]
> [show Neo4j graph nodes appearing]
> [show battlecard output]
>
> Every brief Scout generates, Senso stores as a skill — so the next query on a similar company is smarter than the last. The agent improves without retraining.
>
> We used Yutori's research sub-agent swarm for deep intelligence, Tavily's LLM-optimized search for live news, Neo4j for the relationship graph, Modulate for voice input with emotion detection, and Senso as the self-improvement layer.
>
> In production this runs on AWS Lambda with event-driven triggers — fires automatically before every calendar event with an external company."

---

## TIME CHECK
- It's ~2PM. Submission at 4:30PM. **2.5 hours left.**
- Modulate + Senso verify: 30 min
- Neo4j browser: 5 min
- Demo video: 10 min
- Devpost: 15 min
- Rehearsal: 15 min
- Buffer: 45 min
