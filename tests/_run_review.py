import httpx, json, time

t0 = time.time()
with open("tests/fixtures/john_locke_sample_2.txt", "rb") as f:
    r = httpx.post(
        "http://127.0.0.1:8000/api/v1/review",
        data={"competition": "John Locke", "student_name": "Test_Student_2", "model_provider": "deepseek"},
        files={"file": ("essay2.txt", f, "text/plain")},
        timeout=300,
    )
elapsed = time.time() - t0
print(f"HTTP {r.status_code} ({elapsed:.0f}s)")

with open("data/jl_review_full.json", "w", encoding="utf-8") as out:
    out.write(r.text)

if r.status_code != 200:
    print(f"ERROR: {r.text[:500]}")
    exit(1)

d = r.json()
print(f"Total={d.get('total_score','N/A')} Type={d.get('competition_type','?')} Words={d.get('meta',{}).get('word_count','?')}")
print(f"Duration: {d.get('meta',{}).get('duration_seconds','?')}s Model: {d.get('meta',{}).get('model','?')}")
print()
for agent, score in d.get("scores", {}).items():
    print(f"  {agent}: {score}")

for key in ["rubric", "structure", "argument", "language", "integrity"]:
    v = d.get(key)
    if v:
        print(f"\n{'='*60}")
        print(f"=== {key.upper()} (Agent: {v.get('agent','?')}) ===")
        print(f"{'='*60}")
        print(json.dumps(v, ensure_ascii=False, indent=2))
        print()

print("\nFull response saved to data/jl_review_full.json")
