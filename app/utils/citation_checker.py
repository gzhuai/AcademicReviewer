import re
from dataclasses import dataclass, field


@dataclass
class CitationPair:
    cite_id: str
    cite_text: str
    reference_text: str | None
    is_matched: bool
    issue: str | None = None


@dataclass
class CitationReport:
    pairs: list[CitationPair] = field(default_factory=list)
    unmatched_cites: list[str] = field(default_factory=list)
    unmatched_refs: list[str] = field(default_factory=list)
    format_issues: list[str] = field(default_factory=list)

    @property
    def total_cites(self) -> int:
        return len(self.pairs)

    @property
    def matched_count(self) -> int:
        return sum(1 for p in self.pairs if p.is_matched)

    @property
    def match_rate(self) -> float:
        if self.total_cites == 0:
            return 1.0
        return self.matched_count / self.total_cites


CITE_PATTERNS = [
    re.compile(r"\[(\d+)\]"),
    re.compile(r"\(([\w\s]+,?\s*\d{4}[a-z]?)\)"),
    re.compile(r"\(([\w\s]+et\s*al\.?,?\s*\d{4}[a-z]?)\)"),
    re.compile(r"([A-Z][a-z]+\s*et\s*al\.?\s*\(\d{4}[a-z]?\))"),
    re.compile(r"\(([A-Z][a-z]+(?:\s+et\s+al\.?)?)\s+\d+\)"),
    re.compile(r"([A-Z][a-z]+(?:\s+et\s+al\.?)?)\s+\(\d{4}[a-z]?\)"),
]


def extract_cite_keys(text: str) -> list[str]:
    keys = []
    for pattern in CITE_PATTERNS:
        for match in pattern.finditer(text):
            keys.append(match.group(1))
    return keys


def extract_reference_lines(ref_section: str) -> list[str]:
    lines = [line.strip() for line in ref_section.split("\n") if line.strip()]
    return lines


def check_citations(text: str, ref_section: str) -> CitationReport:
    cite_keys = extract_cite_keys(text)
    ref_lines = extract_reference_lines(ref_section)

    matched_cites = set()
    matched_refs = set()

    pairs = []
    for cite in cite_keys:
        matched_ref = None
        cite_surname = cite.split(",")[0].split(" et")[0].strip()
        for i, ref in enumerate(ref_lines):
            if cite_surname.lower() in ref.lower():
                matched_ref = ref
                matched_cites.add(cite)
                matched_refs.add(i)
                break
        pairs.append(CitationPair(
            cite_id=cite,
            cite_text=cite,
            reference_text=matched_ref,
            is_matched=matched_ref is not None,
            issue=None if matched_ref else f"引用 [{cite}] 在参考文献列表中未找到",
        ))

    unmatched_cites = [c for c in cite_keys if c not in matched_cites]
    unmatched_refs = [ref for i, ref in enumerate(ref_lines) if i not in matched_refs]

    return CitationReport(
        pairs=pairs,
        unmatched_cites=unmatched_cites,
        unmatched_refs=unmatched_refs,
        format_issues=[],
    )
