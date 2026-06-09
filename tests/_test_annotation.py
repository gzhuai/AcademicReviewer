from app.utils.annotation_builder import build_annotated_markdown
import json

with open("data/jl_review_full.json", "r", encoding="utf-8") as f:
    d = json.load(f)

with open("tests/fixtures/john_locke_sample_2.txt", "r", encoding="utf-8") as f:
    original = f.read()

md = build_annotated_markdown(
    original_text=original,
    structure=d.get("structure"),
    argument=d.get("argument"),
    language=d.get("language"),
    integrity=d.get("integrity"),
    rubric=d.get("rubric"),
)

with open("data/jl_annotated.md", "w", encoding="utf-8") as out:
    out.write(md)

print(f"Saved: {len(md)} chars, {md.count('### 段落')} paragraphs")
print("---first 2000 chars---")
print(md[:2000])
