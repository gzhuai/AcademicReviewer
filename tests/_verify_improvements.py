from app.agents.argument_evidence import ArgumentEvidenceAgent
from app.agents.language_style import LanguageStyleAgent
from app.orchestrator import Orchestrator

# A3 type_hints from config
hint = ArgumentEvidenceAgent._load_type_hint("business_case")
assert "SWOT" in hint, hint
hint2 = ArgumentEvidenceAgent._load_type_hint("discursive")
assert "counterargument" in hint2, hint2
print(f"A3 OK: discursive hint uses counterargument={True}")

# A4 style_guide loading
sg = Orchestrator._load_style_guide({"style_template": "tech_academic.json"})
assert sg, "tech_academic not loaded"
assert sg["style_parameters"]["max_passive_ratio"] == 0.40
print(f"A4 research OK: max_passive_ratio={sg['style_parameters']['max_passive_ratio']}")

sg2 = Orchestrator._load_style_guide({"style_template": "discursive.json"})
assert sg2, "discursive not loaded"
assert sg2["style_parameters"]["max_passive_ratio"] == 0.30
print(f"A4 discursive OK: max_passive_ratio={sg2['style_parameters']['max_passive_ratio']}")

# Empty fallback
sg3 = Orchestrator._load_style_guide({})
assert sg3 == {}
print("A4 empty fallback OK")

# Main imports
from app.main import app
print("\nALL OK")
