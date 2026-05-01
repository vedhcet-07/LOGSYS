"""
Phase 4A Sanity Test — Session Store + Graph Store + Pinecone namespacing
Run: .venv\Scripts\python backend\data\test_phase4a.py
"""
import sys
sys.path.insert(0, 'backend')

from dotenv import load_dotenv
load_dotenv('.env', override=True)

PASS = "[PASS]"
FAIL = "[FAIL]"
errors = []

def check(label, condition, detail=""):
    if condition:
        print(f"{PASS} {label}")
    else:
        msg = f"{FAIL} {label}" + (f" — {detail}" if detail else "")
        print(msg)
        errors.append(msg)

print("=" * 55)
print("Phase 4A: Session Store Test Suite")
print("=" * 55)
print()

# ── 1. Imports ────────────────────────────────────────────────────────────────
try:
    from services.session_store import (
        create_session, get_session, list_sessions,
        update_session, delete_session,
        get_session_graph, save_session_graph,
        get_session_chat, append_session_chat,
        get_session_graph_json,
    )
    from services.graph_store import add_entity, add_relationship, get_neighbors, get_stats, get_graph_json
    from services.pinecone_store import upsert_chunks, query
    from models import Session, ChatEntry, CreateSessionRequest
    check("Imports", True)
except Exception as e:
    check("Imports", False, str(e))
    print("\nCannot continue — fix imports first.")
    sys.exit(1)

# ── 2. Create sessions ────────────────────────────────────────────────────────
s1 = create_session("Incident May 2 - Auth Failure")
s2 = create_session("Incident May 1 - DB Outage")
check("create_session s1", s1.get("id") and s1.get("name"))
check("create_session s2", s2.get("id") and s2.get("name"))

# ── 3. List sessions ──────────────────────────────────────────────────────────
sessions = list_sessions()
check("list_sessions returns 2+", len(sessions) >= 2)

# ── 4. Graph isolation ────────────────────────────────────────────────────────
add_entity("auth-service", "service",  session_id=s1["id"])
add_entity("user-db",      "database", session_id=s1["id"])
add_relationship("auth-service", "user-db", "depends_on", session_id=s1["id"])

stats1 = get_stats(session_id=s1["id"])
stats2 = get_stats(session_id=s2["id"])
check("Session 1 has 2 nodes", stats1["nodes"] == 2, f"got {stats1['nodes']}")
check("Session 1 has 1 edge",  stats1["edges"] == 1, f"got {stats1['edges']}")
check("Session 2 has 0 nodes (isolated)", stats2["nodes"] == 0, f"got {stats2['nodes']}")

# ── 5. Graph JSON ─────────────────────────────────────────────────────────────
gjson = get_graph_json(session_id=s1["id"])
check("get_graph_json nodes", len(gjson["nodes"]) == 2)
check("get_graph_json edges", len(gjson["edges"]) == 1)

# ── 6. Graph neighbours ───────────────────────────────────────────────────────
neighbors = get_neighbors("auth-service", depth=2, session_id=s1["id"])
check("get_neighbors finds user-db", any(n["node"] == "user-db" for n in neighbors))
no_neighbors = get_neighbors("auth-service", depth=2, session_id=s2["id"])
check("get_neighbors empty in s2 (isolated)", len(no_neighbors) == 0)

# ── 7. Chat history ───────────────────────────────────────────────────────────
append_session_chat(s1["id"], {"role": "user",      "content": "Why did auth fail?"})
append_session_chat(s1["id"], {"role": "assistant",  "content": {"root_cause": "DB pool exhausted"}})
chat1 = get_session_chat(s1["id"])
chat2 = get_session_chat(s2["id"])
check("Chat history s1 has 2 entries", len(chat1) == 2)
check("Chat history s2 is empty (isolated)", len(chat2) == 0)
check("Chat entry has timestamp", "timestamp" in chat1[0])

# ── 8. update_session ─────────────────────────────────────────────────────────
updated = update_session(s1["id"], node_count=2, edge_count=1, files=["auth.log"])
check("update_session node_count", updated and updated["node_count"] == 2)
check("update_session files",      updated and updated["files"] == ["auth.log"])

# ── 9. Pydantic Session model ─────────────────────────────────────────────────
try:
    sess_model = Session(**get_session(s1["id"]))
    check("Session Pydantic model validates", sess_model.id == s1["id"])
except Exception as e:
    check("Session Pydantic model validates", False, str(e))

# ── 10. Index stays synced ────────────────────────────────────────────────────
refreshed = list_sessions()
s1_entry  = next((s for s in refreshed if s["id"] == s1["id"]), None)
check("Session 1 in index after update", s1_entry is not None)
check("Index synced node_count", s1_entry and s1_entry["node_count"] == 2)

# ── 11. Delete session ────────────────────────────────────────────────────────
deleted = delete_session(s2["id"])
check("delete_session returns True",         deleted)
remaining = list_sessions()
check("Session 2 removed from index",        not any(s["id"] == s2["id"] for s in remaining))
check("Session 1 unaffected after s2 delete", any(s["id"] == s1["id"] for s in remaining))

# ── 12. Global graph backward-compat ─────────────────────────────────────────
global_stats = get_stats(session_id=None)
check("Global graph unmodified (backward-compat)", isinstance(global_stats["nodes"], int))

# ── Pinecone namespace signature check ───────────────────────────────────────
import inspect
upsert_sig = inspect.signature(upsert_chunks)
query_sig  = inspect.signature(query)
check("upsert_chunks has namespace param", "namespace" in upsert_sig.parameters)
check("query has namespace param",         "namespace" in query_sig.parameters)

# ── Cleanup test session ──────────────────────────────────────────────────────
delete_session(s1["id"])

# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("=" * 55)
if errors:
    print(f"PHASE 4A: {len(errors)} FAILURE(S)")
    for e in errors:
        print(" ", e)
    sys.exit(1)
else:
    print("PHASE 4A: ALL TESTS PASSED [OK]")
    print("=" * 55)
