"""
NormClaim — NLP Preprocessor
Handles deterministic text preprocessing using spaCy and medspaCy.
"""

import spacy
import json
import re
import os
from typing import List, Dict

from Extraction_pipeline.text_features import (
    build_section_map as shared_build_section_map,
    detect_script_label,
    extract_negated_spans as shared_extract_negated_spans,
)

# medspaCy 1.x registers the "medspacy_context" factory on import.
MEDSPACY_AVAILABLE = False
try:
    import medspacy.context  # noqa: F401 — registers @Language.factory("medspacy_context")

    nlp = spacy.load("en_core_web_sm")
    nlp.add_pipe("medspacy_context", last=True)
    MEDSPACY_AVAILABLE = True
except Exception:
    nlp = spacy.load("en_core_web_sm")

# Load abbreviation map
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
with open(os.path.join(_DATA_DIR, "abbrev_map.json"), "r", encoding="utf-8") as f:
    _abbrev_map = json.load(f)

# Longest keys first to avoid partial replacements like replacing c/o before k/c/o.
ABBREV_MAP = {k: v for k, v in sorted(_abbrev_map.items(), key=lambda x: -len(x[0]))}

def expand_abbreviations(text: str) -> str:
    """Expand abbreviations in the input text."""
    for abbr, full_form in ABBREV_MAP.items():
        pattern = re.compile(r"\b" + re.escape(abbr) + r"\b", re.IGNORECASE)
        text = pattern.sub(full_form, text)
    return text

def detect_sections(doc) -> Dict[str, str]:
    """Detect sections in the text based on keywords."""
    section_keywords = {
        "complaint": ["c/o", "complaining of", "presenting complaint", "chief complaint", "p/c"],
        "history": ["h/o", "history of", "k/c/o", "known case", "past history", "p/h", "f/h/o", "family history"],
        "diagnosis": ["diagnosis", "d/c dx", "discharge diagnosis", "final diagnosis", "impression", "d/d", "differential"],
        "medications": ["rx", "treatment", "medicines", "drugs", "prescription", "medication", "tab.", "inj.", "syrup"],
        "investigations": ["investigation", "lab", "report", "test", "usg", "x-ray", "ecg", "mri", "ct", "echo", "lft", "rft"],
        "examination": ["on examination", "o/e", "general examination", "vitals", "bp", "pulse", "spo2", "temp"],
        "advice": ["advice", "adv", "follow up", "r/v", "review", "discharge advice", "discharge instructions"]
    }
    section_map = {}
    for sent in doc.sents:
        sent_key = str(sent.start)
        for section, keywords in section_keywords.items():
            if any(keyword.lower() in sent.text.lower() for keyword in keywords):
                section_map[sent_key] = section
                break
        else:
            section_map[sent_key] = "unknown"
    return section_map

def detect_negated_spans(doc) -> List[str]:
    """Detect negated spans using medspaCy ConText and regex patterns."""
    negated_spans = []
    if MEDSPACY_AVAILABLE:
        negated_spans.extend([
            ent.text for ent in doc.ents if hasattr(ent._, "is_negated") and ent._.is_negated
        ])
    regex_patterns = [
        r"no\s+h/o\s+(\w+)",
        r"not\s+a\s+k/c/o\s+(\w+)",
        r"ruled\s+out\s+(\w+)",
        r"(\w+)\s+not\s+present",
        r"no\s+evidence\s+of\s+(\w+)",
        r"(\w+)\s+excluded"
    ]
    for pattern in regex_patterns:
        matches = re.findall(pattern, doc.text, re.IGNORECASE)
        negated_spans.extend(matches)
    return list(set(negated_spans))

def detect_script(text: str) -> str:
    """Detect the script of the text (Roman, Devanagari, or Mixed)."""
    devanagari_range = re.compile(r"[\u0900-\u097F]")
    has_devanagari = bool(devanagari_range.search(text))
    has_latin = bool(re.search(r"[a-zA-Z]", text))
    if has_devanagari and has_latin:
        return "mixed"
    elif has_devanagari:
        return "devanagari"
    else:
        return "roman"

def preprocess(raw_text: str) -> Dict:
    """Run the full preprocessing pipeline."""
    expanded_text = expand_abbreviations(raw_text)
    doc = nlp(expanded_text)

    # Keep existing spaCy/medspaCy section mapping, but backfill unknown slots
    # from shared Extraction_pipeline rules to avoid drift across pipelines.
    section_map = detect_sections(doc)
    shared_section_map = shared_build_section_map(expanded_text)
    for key, label in shared_section_map.items():
        if key not in section_map or section_map.get(key) == "unknown":
            section_map[key] = label

    # Merge medspaCy negation findings with shared regex-based extraction.
    negated_spans = list(
        set(detect_negated_spans(doc) + shared_extract_negated_spans(expanded_text))
    )
    detected_script = detect_script_label(raw_text)
    return {
        "expanded_text": expanded_text,
        "section_map": section_map,
        "negated_spans": negated_spans,
        "detected_script": detected_script
    }