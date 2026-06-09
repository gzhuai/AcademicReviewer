from app.config import normalize_competition_name, get_competition_list

tests = ["isef", "John locke", "john locke", "ISEF", "himcm", "JL", "wghs", "Marshall Society", "unknown_x"]
print("=== NORMALIZATION ===")
for t in tests:
    result = normalize_competition_name(t)
    status = "OK" if result != t else "(未匹配)"
    print(f"  {t:20s} -> {result:20s} {status}")

print()
print("=== COMPETITION LIST ===")
for c in get_competition_list():
    print(f"  {c['name']:20s} type={c['type']:18s} ({c['type_cn']})")
print()
print("All OK")
