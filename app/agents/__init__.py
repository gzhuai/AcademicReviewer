"""AcademicReviewer agents package.

Five specialized review agents in a two-round parallel pipeline:

Round 1 (parallel): A1 RubricParser + A2 StructureLogic + A3 ArgumentEvidence
Round 2 (parallel): A4 LanguageStyle + A5 AcademicIntegrity
"""

from app.agents.base import BaseAgent
from app.agents.rubric_parser import RubricParserAgent
from app.agents.structure_logic import StructureLogicAgent
from app.agents.argument_evidence import ArgumentEvidenceAgent
from app.agents.language_style import LanguageStyleAgent
from app.agents.academic_integrity import AcademicIntegrityAgent

__all__ = [
    "BaseAgent",
    "RubricParserAgent",
    "StructureLogicAgent",
    "ArgumentEvidenceAgent",
    "LanguageStyleAgent",
    "AcademicIntegrityAgent",
]
