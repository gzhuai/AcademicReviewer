import re
from collections import Counter
from dataclasses import dataclass, field

LOGICAL_MARKERS = {
    "therefore", "thus", "hence", "consequently", "as a result",
    "however", "nevertheless", "nonetheless", "although", "even though",
    "moreover", "furthermore", "in addition", "additionally",
    "for example", "for instance", "specifically", "in particular",
    "in contrast", "on the other hand", "conversely",
    "first", "second", "third", "finally", "lastly",
    "in conclusion", "to summarize", "in summary",
    "because", "since", "due to", "owing to",
    "if", "unless", "provided that", "assuming that",
    "indeed", "in fact", "certainly", "undoubtedly",
}

TRANSITION_PATTERNS = re.compile(
    r"\b(?:however|therefore|thus|hence|consequently|"
    r"nevertheless|nonetheless|moreover|furthermore|"
    r"additionally|meanwhile|similarly|likewise|"
    r"in contrast|on the other hand|conversely|"
    r"for example|for instance|specifically|"
    r"in particular|indeed|in fact|first|second|third|"
    r"finally|lastly|in conclusion|to summarize|"
    r"in summary|as a result|accordingly|subsequently)"
    r"(?:\s*,\s*|\s+)",
    re.IGNORECASE,
)

PASSIVE_PATTERNS = re.compile(
    r"\b(?:am|is|are|was|were|be|been|being)\s+"
    r"(?:\w+ly\s+)?(?:\w+ed|written|drawn|known|born|"
    r"built|sent|made|found|given|seen|taken|shown|"
    r"chosen|driven|broken|spoken|risen|fallen|grown|"
    r"thrown|blown|flown|worn|sworn|torn|swum|begun|"
    r"sung|rung|drunk|sunk|stung|swung|hung|struck|"
    r"stuck|won|met|lost|kept|slept|swept|wept|crept|"
    r"felt|dealt|meant|dreamt|spent|bent|lent|sent|"
    r"built)\b",
    re.IGNORECASE,
)

CITATION_PATTERNS = re.compile(
    r"\([^)]*\d{4}[^)]*\)|"
    r"\[\d+(?:,\s*\d+)*\]|"
    r"(?:[A-Z][a-z]+(?:\s+(?:&|and)\s+[A-Z][a-z]+)?\s*\(\d{4}\)|"
    r"[A-Z][a-z]+\s+et\s+al\.?\s*\(\d{4}\))",
)

SECTION_HEADERS = [
    r"(?i)^\s*(?:Abstract|Summary)\s*$",
    r"(?i)^\s*(?:Introduction|Background)\s*$",
    r"(?i)^\s*(?:Literature\s+Review|Related\s+Work)\s*$",
    r"(?i)^\s*(?:Method(?:ology|s)?|Materials?\s*(?:and|&)\s*Methods?|Experimental\s+Design)\s*$",
    r"(?i)^\s*(?:Results?|Findings)\s*$",
    r"(?i)^\s*(?:Discussions?)\s*$",
    r"(?i)^\s*(?:Conclusions?|Summary)\s*$",
    r"(?i)^\s*(?:References?|Bibliography|Works\s+Cited)\s*$",
]

NUMERIC_PATTERN = re.compile(r"p\s*[<>=]\s*0?\.\d+|p[- ]value|statistical(?:ly)?\s+significant")
EFFECT_SIZE_PATTERN = re.compile(
    r"Cohen'?s\s+d|effect\s+size|η²|η2|partial\s+η²|"
    r"r\s*=\s*0?\.\d+|R²|R2|odds\s+ratio|Hedges'?\s+g"
)
CONTROL_GROUP_PATTERN = re.compile(r"control\s+group|baseline|placebo|untreated|wild[-\s]type|sham")
SAMPLE_SIZE_PATTERN = re.compile(r"n\s*=\s*\d+|sample\s+size\s*(?:of\s*)?\d+|N\s*=\s*\d+")

EVIDENCE_TYPES = {
    "academic_journal": re.compile(r"\b(?:Journal|Review|Proceedings|Annals)\s+of\b"),
    "gov_report": re.compile(r"\b(?:WHO|UN|UNESCO|CDC|EPA|NIH|NSF|NASA|Government|Ministry|Department)\b"),
    "statistical_data": re.compile(r"\b(?:mean|median|SD|standard\s+deviation|variance|correlation|regression|t-test|ANOVA|chi-square)\b", re.IGNORECASE),
    "primary_experiment": re.compile(r"\b(?:we\s+(?:conducted|performed|carried\s+out|measured|observed|tested|examined))\b", re.IGNORECASE),
    "case_study": re.compile(r"\b(?:case\s+study|subject|participant|respondent)\b", re.IGNORECASE),
}


@dataclass
class DocumentFeatures:
    filename: str = ""
    word_count: int = 0
    sentence_count: int = 0
    avg_sentence_length: float = 0.0
    sentence_length_std: float = 0.0
    citation_density: float = 0.0
    passive_voice_ratio: float = 0.0
    vocabulary_diversity: float = 0.0
    logical_marker_density: float = 0.0
    transition_frequency: float = 0.0
    avg_paragraph_length: float = 0.0
    section_coverage: float = 0.0
    has_p_value: float = 0.0
    has_effect_size: float = 0.0
    has_control_group: float = 0.0
    has_sample_size: float = 0.0
    evidence_diversity_score: float = 0.0
    evidence_source_count: int = 0
    claim_count_estimate: int = 0
    hook_sentence_present: float = 0.0
    gap_statement_present: float = 0.0
    limitations_section_present: float = 0.0
    future_work_mentioned: float = 0.0


def extract_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in raw if len(s.split()) >= 3]


def tokenize_words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z]+", text.lower())


def extract_features(text: str, filename: str = "") -> DocumentFeatures:
    f = DocumentFeatures(filename=filename)

    sentences = extract_sentences(text)
    words = tokenize_words(text)
    f.word_count = len(words)
    f.sentence_count = len(sentences) if sentences else 1

    sent_lens = [len(tokenize_words(s)) for s in sentences]
    if sent_lens:
        f.avg_sentence_length = sum(sent_lens) / len(sent_lens)
        if len(sent_lens) > 1:
            mean_sl = f.avg_sentence_length
            variance = sum((x - mean_sl) ** 2 for x in sent_lens) / (len(sent_lens) - 1)
            f.sentence_length_std = variance ** 0.5

    if f.word_count > 0:
        f.citation_density = len(CITATION_PATTERNS.findall(text)) * 1000 / f.word_count

        passive_matches = len(PASSIVE_PATTERNS.findall(text))
        total_verbs = len(re.findall(r"\b(?:am|is|are|was|were|be|been|being)\b", text, re.IGNORECASE))
        total_verbs += len(re.findall(r"\b\w+(?:ed|en)\b", text))
        total_verbs = max(total_verbs, 1)
        f.passive_voice_ratio = min(passive_matches / max(total_verbs, 1), 1.0)

        unique_words = set(words)
        f.vocabulary_diversity = len(unique_words) / len(words) if words else 0

        logical_count = sum(
            text.lower().count(marker) for marker in LOGICAL_MARKERS
        )
        f.logical_marker_density = logical_count * 1000 / f.word_count

        transition_count = len(TRANSITION_PATTERNS.findall(text))
        f.transition_frequency = transition_count * 1000 / f.word_count

    if sentences:
        f.claim_count_estimate = sum(
            1 for s in sentences
            if any(marker in s.lower() for marker in ["argue", "claim", "suggest", "demonstrate", "indicate", "show", "find", "reveal", "conclude", "propose", "hypothesize", "contend", "assert"])
        )

    paragraphs = [p for p in text.split("\n\n") if len(p.strip()) > 20]
    if paragraphs:
        para_lens = [len(tokenize_words(p)) for p in paragraphs]
        f.avg_paragraph_length = sum(para_lens) / len(para_lens)

    matched_sections = 0
    for pattern in SECTION_HEADERS:
        if re.search(pattern, text, re.MULTILINE):
            matched_sections += 1
    f.section_coverage = matched_sections / len(SECTION_HEADERS) if SECTION_HEADERS else 0

    f.has_p_value = 1.0 if NUMERIC_PATTERN.search(text) else 0.0
    f.has_effect_size = 1.0 if EFFECT_SIZE_PATTERN.search(text) else 0.0
    f.has_control_group = 1.0 if CONTROL_GROUP_PATTERN.search(text) else 0.0
    f.has_sample_size = 1.0 if SAMPLE_SIZE_PATTERN.search(text) else 0.0

    evidence_scores = []
    for ev_type, pattern in EVIDENCE_TYPES.items():
        if pattern.search(text):
            evidence_scores.append(1)
    f.evidence_diversity_score = sum(evidence_scores) / len(EVIDENCE_TYPES) if EVIDENCE_TYPES else 0
    f.evidence_source_count = sum(evidence_scores)

    first_paragraph = paragraphs[0] if paragraphs else ""
    f.hook_sentence_present = 1.0 if re.search(
        r"\b(?:imagine|consider|picture|what\s+if|in\s+\d{4}|over\s+the\s+past|recently|"
        r"did\s+you\s+know|surprisingly|despite|could\s+(?:it|we|you))",
        first_paragraph, re.IGNORECASE
    ) else 0.0

    f.gap_statement_present = 1.0 if re.search(
        r"\b(?:however,?\s+(?:little|few|no|limited)|remains\s+(?:unclear|unknown|unexplored)|"
        r"gap\s+(?:in|exists)|lack\s+(?:of|ing)|"
        r"has\s+not\s+(?:been|yet)|further\s+(?:research|investigation|study))",
        text, re.IGNORECASE
    ) else 0.0

    f.limitations_section_present = 1.0 if re.search(
        r"\b(?:limitations?|shortcomings?|weaknesses?|caveats?|"
        r"should\s+be\s+(?:interpreted|viewed|considered)\s+with\s+caution)",
        text, re.IGNORECASE
    ) else 0.0

    f.future_work_mentioned = 1.0 if re.search(
        r"\b(?:future\s+(?:research|work|studies|investigation|direction)|"
        r"further\s+(?:research|investigation|study|work|analysis)|"
        r"next\s+steps?)",
        text, re.IGNORECASE
    ) else 0.0

    return f


def features_to_dict(f: DocumentFeatures) -> dict:
    return {
        "filename": f.filename,
        "word_count": f.word_count,
        "sentence_count": f.sentence_count,
        "avg_sentence_length": round(f.avg_sentence_length, 2),
        "sentence_length_std": round(f.sentence_length_std, 2),
        "citation_density": round(f.citation_density, 2),
        "passive_voice_ratio": round(f.passive_voice_ratio, 3),
        "vocabulary_diversity": round(f.vocabulary_diversity, 3),
        "logical_marker_density": round(f.logical_marker_density, 2),
        "transition_frequency": round(f.transition_frequency, 2),
        "avg_paragraph_length": round(f.avg_paragraph_length, 2),
        "section_coverage": round(f.section_coverage, 3),
        "has_p_value": f.has_p_value,
        "has_effect_size": f.has_effect_size,
        "has_control_group": f.has_control_group,
        "has_sample_size": f.has_sample_size,
        "evidence_diversity_score": round(f.evidence_diversity_score, 3),
        "evidence_source_count": f.evidence_source_count,
        "claim_count_estimate": f.claim_count_estimate,
        "hook_sentence_present": f.hook_sentence_present,
        "gap_statement_present": f.gap_statement_present,
        "limitations_section_present": f.limitations_section_present,
        "future_work_mentioned": f.future_work_mentioned,
    }


def feature_names() -> list[str]:
    return [
        "word_count", "avg_sentence_length", "sentence_length_std",
        "citation_density", "passive_voice_ratio", "vocabulary_diversity",
        "logical_marker_density", "transition_frequency",
        "avg_paragraph_length", "section_coverage",
        "has_p_value", "has_effect_size", "has_control_group", "has_sample_size",
        "evidence_diversity_score", "evidence_source_count", "claim_count_estimate",
        "hook_sentence_present", "gap_statement_present",
        "limitations_section_present", "future_work_mentioned",
    ]
