#!/usr/bin/env python3
"""
Scout — Flask Web Dashboard
Streams agent events to a live browser UI via SSE.

Usage: python3 flask_app.py
Then open: http://localhost:5000
"""

import json
import os
import sys
import threading
import uuid
from queue import Queue, Empty

from flask import Flask, Response, render_template, request, stream_with_context
from dotenv import load_dotenv

load_dotenv()

# Add agent-prep to path so we can import scout
sys.path.insert(0, os.path.dirname(__file__))
from scout import run_agent

app = Flask(__name__)
app.config["SECRET_KEY"] = "scout-hackathon-2026"

# In-memory store: session_id → Queue
event_queues: dict[str, Queue] = {}


# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return "ok"


@app.route("/api/graph")
def api_graph():
    from scout import neo4j_driver, NEO4J_DB
    company = request.args.get("company", "")
    try:
        with neo4j_driver.session(database=NEO4J_DB) as session:
            if company:
                # Only show the subgraph for the searched company
                result = session.run("""
                    MATCH (c:Company {name: $name})-[r]->(m)
                    RETURN c AS n, r, m
                    UNION
                    MATCH (c:Company {name: $name})-[:COMPETES_WITH]->(rival)
                    RETURN c AS n, null AS r, rival AS m
                """, name=company)
                # Simpler: just get everything connected to this company in 1 hop
                result = session.run("""
                    MATCH (c:Company {name: $name})-[r]->(m)
                    RETURN c AS n, r, m
                """, name=company)
            else:
                result = session.run("MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 60")
            nodes, edges = {}, []
            for record in result:
                n, m, r = record["n"], record["m"], record["r"]
                nid, mid = str(n.element_id), str(m.element_id)
                if nid not in nodes:
                    nodes[nid] = {"id": nid, "label": n.get("name") or n.get("title") or "?",
                                  "group": list(n.labels)[0] if n.labels else "Node"}
                if mid not in nodes:
                    nodes[mid] = {"id": mid, "label": m.get("name") or m.get("title") or "?",
                                  "group": list(m.labels)[0] if m.labels else "Node"}
                edges.append({"from": nid, "to": mid, "type": r.type})
        return {"nodes": list(nodes.values()), "edges": edges}
    except Exception as e:
        return {"error": str(e), "nodes": [], "edges": []}


@app.route("/run", methods=["POST"])
def run():
    data    = request.get_json()
    company = (data.get("company") or "").strip()
    emotion = (data.get("emotion") or "neutral").strip()

    if not company:
        return {"error": "company is required"}, 400

    session_id = str(uuid.uuid4())
    q: Queue = Queue()
    event_queues[session_id] = q

    def emit_event(event_type: str, payload: dict):
        q.put(json.dumps({"type": event_type, **payload}))

    def run_in_thread():
        try:
            run_agent(
                f"I have a call with {company} in 20 minutes. Give me everything I need.",
                emotion=emotion,
                emit_event=emit_event,
                speak=False  # browser handles TTS via brief_done event
            )
        except Exception as e:
            emit_event("error", {"message": str(e)})
        finally:
            q.put(None)  # sentinel — stream is done

    threading.Thread(target=run_in_thread, daemon=True).start()
    return {"session_id": session_id}


@app.route("/stream/<session_id>")
def stream(session_id):
    q = event_queues.get(session_id)
    if not q:
        return {"error": "session not found"}, 404

    def generate():
        try:
            while True:
                try:
                    msg = q.get(timeout=60)
                except Empty:
                    yield "data: {\"type\":\"heartbeat\"}\n\n"
                    continue
                if msg is None:
                    yield "data: {\"type\":\"done\"}\n\n"
                    break
                yield f"data: {msg}\n\n"
        finally:
            event_queues.pop(session_id, None)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n[SCOUT] Dashboard running → http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
