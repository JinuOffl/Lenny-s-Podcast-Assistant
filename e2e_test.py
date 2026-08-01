"""
e2e_test.py - End-to-end API tests for all 3 skills via HTTP.
Run from project root: python e2e_test.py
Requires: uvicorn running on port 8000
"""
import json, sys, urllib.request, urllib.error

BASE = "http://localhost:8000"

def post(path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if data else "GET",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return json.loads(r.read())

def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f": {detail}" if detail else ""))
    return condition

print("=" * 60)
print("Lenny's Growth Assistant — End-to-End Test")
print("=" * 60)

# ── Health ────────────────────────────────────────────────────────
print("\n[1] Health check")
health = get("/health")
check("status ok",       health["status"] == "ok")
check("database true",   health["database"])
check("ollama_llm true", health.get("ollama_llm") or health.get("ollama_llm", False))
check("ollama true",     health["ollama"])

# ── Create session ────────────────────────────────────────────────
print("\n[2] Create session")
session = post("/sessions", {"title": "e2e-test"})
sid = session["id"]
check("session id exists", bool(sid), sid[:8] + "...")

# ── Skill 1: Q&A ──────────────────────────────────────────────────
print("\n[3] Q&A skill")
qa = post(f"/sessions/{sid}/chat", {"message": "What did Brian Chesky say about company culture?"})
check("skill_used = qa",         qa["skill_used"] == "qa",          qa["skill_used"])
check("response non-empty",      len(qa["response"]) > 100,          f"{len(qa['response'])} chars")
check("sources present",         len(qa.get("sources", [])) > 0,     f"{len(qa.get('sources',[]))} sources")
check("artifact is null",        qa.get("artifact") is None)
if qa.get("sources"):
    src = qa["sources"][0]
    check("source has guest",    bool(src.get("guest")),             src.get("guest",""))
    check("source has yt url",   bool(src.get("youtube_url")),       src.get("youtube_url","")[:40])

# ── Skill 2: Ship30for30 ──────────────────────────────────────────
print("\n[4] Ship30for30 essay skill")
essay = post(f"/sessions/{sid}/chat", {"message": "Write a Ship30for30 essay on product-market fit"})
check("skill_used = ship30for30", essay["skill_used"] == "ship30for30", essay["skill_used"])
check("response >= 600 chars",    len(essay["response"]) >= 600,        f"{len(essay['response'])} chars")
check("artifact is null",         essay.get("artifact") is None)

# ── Skill 3: Artifact ─────────────────────────────────────────────
print("\n[5] Artifact skill")
art = post(f"/sessions/{sid}/chat", {"message": "Create an HTML page summarizing the top 3 growth lessons from the podcast"})
check("skill_used = artifact",  art["skill_used"] == "artifact",     art["skill_used"])
check("artifact not null",      art.get("artifact") is not None)
if art.get("artifact"):
    a = art["artifact"]
    check("artifact type = html", a["type"] in ("html", "markdown"),  a["type"])
    check("artifact content non-empty", len(a["content"]) > 200,     f"{len(a['content'])} chars")
    if a["type"] == "html":
        check("contains html tag", "<html" in a["content"].lower() or "<!doctype" in a["content"].lower())

# ── Router edge cases ─────────────────────────────────────────────
print("\n[6] Router edge cases (via classify_skill, no LLM)")
sys.path.insert(0, "backend")
from router import classify_skill
edge_cases = [
    ("Generate a list of retention frameworks", "qa"),
    ("Build a case for product-led growth",     "qa"),
    ("Make a table comparing PMF strategies",   "qa"),
    ("Create an HTML dashboard",                "artifact"),
    ("Write a Ship30for30 essay on growth",     "ship30for30"),
]
for msg, expected in edge_cases:
    got = classify_skill(msg)
    check(f'"{msg[:45]}"', got == expected, f"got={got} want={expected}")

# ── Message persistence ───────────────────────────────────────────
print("\n[7] Message persistence")
msgs = get(f"/sessions/{sid}/messages")
check("messages saved",    len(msgs) >= 6,  f"{len(msgs)} messages in DB")  # 3 user + 3 assistant
check("roles correct",     all(m["role"] in ("user","assistant") for m in msgs))
check("skill_used stored", any(m.get("skill_used") for m in msgs if m["role"]=="assistant"))

print("\n" + "=" * 60)
print("Done.")
