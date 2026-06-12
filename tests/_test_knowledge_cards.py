from app.calibration.expert_annotator import unify_parse, merge_insights
from app.calibration.knowledge_cards import build_knowledge_cards, render_knowledge_cards_for_prompt

for name, path in [
    ("ISEF", "data/expert_insights/ISEF_张老师.md"),
    ("John Locke", "data/expert_insights/John_Locke_李老师.md"),
]:
    insights = unify_parse(path)
    cards = build_knowledge_cards(insights)
    rendered = render_knowledge_cards_for_prompt(cards)
    l1_count = sum(len(v) for v in cards["layer_1_core"].values())
    print(f"{name}: {len(insights.annotations)} annotations -> L1={l1_count}, L2={len(cards['layer_2_benchmarks'])}, L3={len(cards['layer_3_notes'])}")
    print(f"  Rendered prompt block: {len(rendered)} chars")
    # Print first fatal_defect
    for a in insights.annotations:
        if a.annotation_type == "fatal_defect":
            print(f"  First fatal_defect: {a.title}")
            break

print("\nALL OK")
