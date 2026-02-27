#!/usr/bin/env python3
"""
neo4j_setup.py — Run once after pasting Neo4j credentials into .env.
Creates constraints and indexes for Scout's knowledge graph.

Usage: python neo4j_setup.py
"""
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
load_dotenv()

uri      = os.getenv("NEO4J_URI")
user     = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE", "neo4j")

print(f"Connecting to {uri}...")
driver = GraphDatabase.driver(uri, auth=(user, password))

try:
    with driver.session(database=database) as session:
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company)  REQUIRE c.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person)   REQUIRE p.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Event)    REQUIRE e.id   IS UNIQUE")
        session.run("CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.name)")
        print("✅ Neo4j constraints and indexes created")
        # Verify with a simple query
        result = session.run("RETURN 'Neo4j is ready for Scout' AS msg")
        print(f"✅ {result.single()['msg']}")
except Exception as e:
    print(f"❌ Neo4j setup failed: {e}")
    print("   Check NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD in .env")
finally:
    driver.close()
