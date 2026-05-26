import json

with open("data/jl_review_full.json", "r", encoding="utf-8") as f:
    d = json.load(f)

# Structure
s = d["structure"]
print("=== STRUCTURE: SECTION ISSUES ===")
for si in s.get("section_issues", []):
    print(json.dumps(si, ensure_ascii=False, indent=2))
    print("---")

print("\n=== STRUCTURE: LOGIC ISSUES ===")
for li in s.get("logic_issues", []):
    print(json.dumps(li, ensure_ascii=False, indent=2))
    print("---")

print("\n=== STRUCTURE: POSITIVE ===")
for p in s.get("positive_points", []):
    print(f"  + {p}")
print("\n=== STRUCTURE: KEY_ISSUES ===")
for p in s.get("key_issues", []):
    print(f"  - {p}")

# Argument
a = d["argument"]
print("\n=== ARGUMENT: CLAIMS ===")
for c in a.get("claims", []):
    print(json.dumps(c, ensure_ascii=False, indent=2))
    print("---")

print("\n=== ARGUMENT: FALLACIES ===")
for fl in a.get("logical_fallacies", []):
    print(json.dumps(fl, ensure_ascii=False, indent=2))
    print("---")

print("\n=== ARGUMENT: POSITIVE ===")
for p in a.get("positive_points", []):
    print(f"  + {p}")
print("\n=== ARGUMENT: KEY_ISSUES ===")
for p in a.get("key_issues", []):
    print(f"  - {p}")

# Language - get first 5 rewrites and all suggestions
la = d["language"]
rws = la.get("rewrites", [])
sgs = la.get("suggestions", [])
print(f"\n=== LANGUAGE: {len(rws)} rewrites, {len(sgs)} suggestions ===")
for rw in rws[:5]:
    print(json.dumps(rw, ensure_ascii=False, indent=2))
    print("---")
for sg in sgs[:5]:
    print(json.dumps(sg, ensure_ascii=False, indent=2))
    print("---")

# Integrity
i = d["integrity"]
cr = i.get("citation_report", {})
print("\n=== INTEGRITY: CITATION ===")
print(json.dumps({
    "total_cites": cr.get("total_cites"),
    "matched": cr.get("matched"),
    "match_rate": cr.get("match_rate"),
    "format_issues": cr.get("format_issues"),
    "suspicious_citations": cr.get("suspicious_citations"),
}, ensure_ascii=False, indent=2))

print("\n=== INTEGRITY: ORIGINALITY ===")
print(json.dumps(i.get("originality_report", {}), ensure_ascii=False, indent=2))

print("\n=== INTEGRITY: COMBINED ===")
print(i.get("combined_assessment", ""))
print("\n=== INTEGRITY: POSITIVE ===")
for p in i.get("positive_points", []):
    print(f"  + {p}")
print("\n=== INTEGRITY: KEY_ISSUES ===")
for p in i.get("key_issues", []):
    print(f"  - {p}")
