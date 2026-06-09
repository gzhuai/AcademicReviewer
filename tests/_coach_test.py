import httpx, json, time

t0 = time.time()
with open("tests/fixtures/john_locke_sample_2.txt", "rb") as f:
    r = httpx.post(
        "http://127.0.0.1:8000/api/v1/review",
        data={"competition": "John Locke", "student_name": "CoachTest", "model_provider": "deepseek"},
        files={"file": ("essay.txt", f, "text/plain")},
        timeout=300,
    )
elapsed = time.time()-t0
print(f"HTTP {r.status_code} ({elapsed:.0f}s)")

d = r.json()
print(f"Total={d.get('total_score','?')}  Scores={d.get('scores',{})}")

# Save annotated doc
annotated = d.get("meta", {}).get("annotated_md", "")
if annotated:
    with open("tests/fixtures/jl_coach_annotated.md", "w", encoding="utf-8") as out:
        out.write(annotated)
    print(f"Annotated: {len(annotated)} chars, {annotated.count(chr(10))} lines")
else:
    print("No annotated_md in response")

# Print key coaching fields
s = d.get("structure", {})
tc = s.get("thesis_coaching", {})
if tc:
    print(f"\n=== THESIS COACHING ===")
    print(f"  Current: {tc.get('current_thesis','?')[:120]}")
    print(f"  Vulnerability: {tc.get('vulnerability','?')}")
    print(f"  Stronger: {tc.get('stronger_version','?')[:120]}")

a = d.get("argument", {})
ca = a.get("counterargument_analysis", {})
if ca:
    print(f"\n=== COUNTERARGUMENT COACHING ===")
    print(f"  Strength: {ca.get('current_strength','?')}")
    print(f"  Strongest Objection: {ca.get('strongest_objection_not_addressed','?')[:150]}")
    print(f"  Rebuttal Guide: {ca.get('rebuttal_guidance','?')[:150]}")

print(f"\nDone. Annotated file: tests/fixtures/jl_coach_annotated.md")
