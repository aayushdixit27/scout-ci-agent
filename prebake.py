#!/usr/bin/env python3
"""
prebake.py — Run Yutori Research on demo companies BEFORE the demo.
Yutori takes 5-10 min per company. Run this NOW and let it cook.

Usage: python prebake.py
"""
import os, json, time, requests
from dotenv import load_dotenv
load_dotenv()

os.makedirs("prebaked", exist_ok=True)

HEADERS = {
    "X-API-KEY": os.getenv("YUTORI_API_KEY"),
    "Content-Type": "application/json"
}

COMPANIES = [
    # Salesforce already prebaked — prebaked/salesforce.json exists, skipped here
    ("HubSpot",     "Deep competitive intelligence on HubSpot: pricing tiers, recent product changes, executive team, key weaknesses vs Salesforce, customer complaints, recent news"),
    ("Notion",      "Deep competitive intelligence on Notion: pricing, recent feature launches, executive team, key weaknesses vs Confluence and Linear, customer complaints, recent news"),
]

def research_and_save(company: str, query: str):
    filename = f"prebaked/{company.lower().replace(' ', '_')}.json"
    if os.path.exists(filename):
        print(f"[PREBAKE] ✅ {company} already exists, skipping")
        return

    print(f"\n[PREBAKE] 🔍 Starting Yutori Research for {company}...")
    try:
        r = requests.post(
            "https://api.yutori.com/v1/research/tasks",
            headers=HEADERS,
            json={"query": query},
            timeout=30
        )
        r.raise_for_status()
        task_id = r.json()["task_id"]
        print(f"[PREBAKE]    Task ID: {task_id}")
    except Exception as e:
        print(f"[PREBAKE] ❌ Failed to start task for {company}: {e}")
        return

    for i in range(120):  # poll up to 20 min
        time.sleep(10)
        try:
            r = requests.get(
                f"https://api.yutori.com/v1/research/tasks/{task_id}",
                headers=HEADERS,
                timeout=15
            )
            data = r.json()
            status = data.get("status", "unknown")
            print(f"[PREBAKE]    {company} [{(i+1)*10}s] → {status}", flush=True)
            if status in ("completed", "succeeded"):
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"[PREBAKE] ✅ {company} saved → keys: {list(data.keys())}", flush=True)
                return
            elif status in ("failed", "error"):
                print(f"[PREBAKE] ❌ {company} failed: {data}", flush=True)
                return
        except Exception as e:
            print(f"[PREBAKE]    Poll error: {e}", flush=True)

    print(f"[PREBAKE] ⏰ Timed out for {company}", flush=True)

if __name__ == "__main__":
    print("=" * 60)
    print("PREBAKE — Yutori Research (5-10 min per company)")
    print("Let this run in the background while you build scout.py")
    print("=" * 60)

    for company, query in COMPANIES:
        research_and_save(company, query)

    print("\n[PREBAKE] Done! Check prebaked/ folder for results.")
