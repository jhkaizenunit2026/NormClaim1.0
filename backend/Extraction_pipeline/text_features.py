"""Shared text-feature utilities for extraction pipelines.

This module intentionally stays lightweight so it can be imported by both
pre-auth extraction and generic backend NLP preprocessing code paths.
"""

from __future__ import annotations

import re


SECTION_PATTERNS: dict[str, list[str]] = {
    "diagnosis": [
        r"diagnosis", r"impression", r"assessment", r"icd", r"clinical diagnosis",
        r"final diagnosis", r"provisional diagnosis", r"\u0928\u093f\u0926\u093e\u0928",
    ],
    "history": [
        r"history", r"c/o", r"complaints", r"presenting", r"chief complaint",
        r"h/o", r"past history", r"\u0907\u0924\u093f\u0939\u093e\u0938",
    ],
    "medications": [
        r"medication", r"prescription", r"drug", r"tablet", r"capsule",
        r"injection", r"syrup", r"\u0926\u0935\u093e\u0908",
    ],
    "procedures": [
        r"procedure", r"surgery", r"operation", r"operation notes", r"intervention",
    ],
    "vitals": [
        r"vitals", r"blood pressure", r"pulse", r"temperature", r"spo2", r"weight",
    ],
    "referral": [
        r"referred", r"referral", r"refer to", r"consulting", r"\u0930\u0947\u092b\u0930\u0932",
    ],
}


def build_section_map(text: str) -> dict[str, str]:
    """Map sentence indices to section labels as a compact JSON-friendly dict."""
    sentences = [s.strip() for s in re.split(r"[.!\n]+", text) if s.strip()]
    section_map: dict[str, str] = {}
    current_section = "general"

    for idx, sentence in enumerate(sentences):
        lower = sentence.lower()
        for section, patterns in SECTION_PATTERNS.items():
            if any(re.search(p, lower) for p in patterns):
                current_section = section
                break
        section_map[str(idx)] = current_section

    return section_map


def extract_negated_spans(text: str) -> list[str]:
    """Find short negated phrase spans using rule-based patterns."""
    negation_patterns = [
        r"no\s+(\w+(?:\s+\w+){0,2})",
        r"not\s+(\w+(?:\s+\w+){0,2})",
        r"denies?\s+(\w+(?:\s+\w+){0,2})",
        r"absent\s+(\w+(?:\s+\w+){0,2})",
        r"without\s+(\w+(?:\s+\w+){0,2})",
        r"\u0928\u0939\u0940\u0902\s+(\w+(?:\s+\w+){0,2})",
    ]
    negated: list[str] = []
    for pattern in negation_patterns:
        negated.extend(re.findall(pattern, text, re.IGNORECASE))
    return list(set(negated))


def detect_script_enum_value(text: str) -> str:
    """Return script label used by pre-auth extraction models."""
    dev_count = len(re.findall(r"[\u0900-\u097F]", text))
    eng_count = len(re.findall(r"[A-Za-z]", text))
    if dev_count > 20 and eng_count > 20:
        return "Hinglish"
    if dev_count > eng_count:
        return "Devanagari"
    return "English"


def detect_script_label(text: str) -> str:
    """Return script label used by generic backend extraction."""
    enum_label = detect_script_enum_value(text)
    if enum_label == "Hinglish":
        return "mixed"
    if enum_label == "Devanagari":
        return "devanagari"
    return "roman"
