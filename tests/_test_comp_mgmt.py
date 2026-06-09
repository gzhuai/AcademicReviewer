from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)

# Test GET
r = c.get("/api/v1/admin/competitions")
d = r.json()
print(f"GET: {len(d['competitions'])} competitions")
print(f"Names: {[c['_name'] for c in d['competitions']]}")

# Test POST (round-trip)
r2 = c.post("/api/v1/admin/competitions", json=d)
print(f"POST: {r2.json()}")

# Test add new competition
d["competitions"].append({
    "_name": "IMMC",
    "type": "math_modeling",
    "subtype": None,
    "structure_schema": "math_modeling.json",
    "evidence_config": "math_modeling.json",
    "style_template": "tech_academic.json",
    "citation_style": "APA",
    "aliases": ["immc", "国际数学建模挑战赛"],
})
r3 = c.post("/api/v1/admin/competitions", json=d)
print(f"Add IMMC: {r3.json()}")

# Verify
r4 = c.get("/api/v1/admin/competitions")
d4 = r4.json()
print(f"After add: {len(d4['competitions'])} competitions, has IMMC: {any(c['_name']=='IMMC' for c in d4['competitions'])}")

# Remove IMMC (cleanup)
d4["competitions"] = [c for c in d4["competitions"] if c["_name"] != "IMMC"]
r5 = c.post("/api/v1/admin/competitions", json=d4)
print(f"Remove IMMC: {r5.json()}")

print("\nALL OK")
