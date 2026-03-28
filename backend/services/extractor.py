"""
NormClaim — AI Extraction Service
Hybrid extraction pipeline:
1) spaCy/medspaCy deterministic preprocessing
2) Gemini semantic extraction
3) Post-processing negation override (spaCy wins)
"""

import os
import json
import re
import time
import logging
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

from google import genai
from rapidfuzz import process, fuzz

from models.schemas import (
    ExtractionResult,
    PatientInfo,
    EncounterInfo,
    Diagnosis,
    Procedure,
    Medication,
)
from services.pdf_parser import extract_text_from_pdf, pdf_to_base64_image
from services.nlp_preprocessor import preprocess

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
with open(os.path.join(_DATA_DIR, "icd10_codes.json"), "r", encoding="utf-8") as f:
    ICD10_LOOKUP: dict = json.load(f)
with open(os.path.join(_DATA_DIR, "drug_map.json"), "r", encoding="utf-8") as f:
    DRUG_MAP: dict = json.load(f)

ICD10_CODES = list(ICD10_LOOKUP.keys())
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]
GEMINI_MODEL = "gemini-2.5-flash-lite"

FEW_SHOT_EXAMPLES = r"""
EXAMPLE (discharge summary style — mirror this structure):
Input expanded_text contains: "Discharge diagnosis: CAP J18.9. k/c/o T2DM E11.9, HTN I10, CKD N18.3. No h/o TB."
Output diagnoses must include J18.9, E11.9, I10, N18.3; TB must be negated=true if listed as "No h/o TB".
Billed codes on slip only: ["J18.9"].
Medication line "Tab Glycomet 500mg" → generic_name Metformin; "Mox 500" → Amoxicillin.
"""

EXTRACTION_SYSTEM_PROMPT = (
    "You are a clinical NLP engine specialized in Indian hospital documents. "
    "The input has already been pre-processed by spaCy and includes expanded_text, "
    "section_map, and negated_spans.\n"
    "Use section context to infer intent (complaint/history/diagnosis).\n"
    "Any diagnosis matching negated_spans must have negated=true.\n"
    "Family history is NOT a patient diagnosis — omit from diagnoses[].\n"
    f"{FEW_SHOT_EXAMPLES}\n"
    "Use this drug brand-to-generic hint map:\n"
    f"{json.dumps(DRUG_MAP, ensure_ascii=False)}\n\n"
    "Return ONLY valid JSON with keys: patient, encounter, diagnoses, procedures, "
    "medications, billed_codes, low_confidence_flags."
)


def validate_icd10_codes(diagnoses: List[Dict]) -> List[Dict]:
    for d in diagnoses:
        code = str(d.get("icd10_code", "")).strip().upper()
        d["icd10_code"] = code
        if not code:
            continue
        if code not in ICD10_LOOKUP:
            result = process.extractOne(code, ICD10_CODES, scorer=fuzz.ratio)
            if result:
                match, score, _ = result
                if score > 70:
                    d["icd10_code"] = match
        if not d.get("icd10_display"):
            d["icd10_display"] = ICD10_LOOKUP.get(d["icd10_code"], d.get("text"))
        d.setdefault("icd10_system", "http://hl7.org/fhir/sid/icd-10")
    return diagnoses


def apply_negation_override(result: Dict, negated_spans: List[str]) -> Dict:
    lowered = [s.lower() for s in negated_spans]
    for diagnosis in result.get("diagnoses", []):
        text = str(diagnosis.get("text", "")).lower()
        if any(span in text for span in lowered):
            diagnosis["negated"] = True
    return result


def _parse_json(raw: str) -> Dict:
    cleaned = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError(f"Gemini returned non-JSON: {cleaned[:200]}")
        return json.loads(match.group())


def _extract_response_text(response: object) -> str:
    """Extract text from google-genai response objects across SDK variants."""
    text = getattr(response, "text", None)
    if text:
        return str(text).strip()

    candidates = getattr(response, "candidates", None) or []
    chunks: List[str] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = getattr(part, "text", None)
            if part_text:
                chunks.append(str(part_text))
    return "\n".join(chunks).strip()


def _normalize_low_confidence_flags(value: object) -> list[str]:
    """Coerce model output into a stable list[str] for schema validation."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    if isinstance(value, dict):
        # Gemini occasionally emits an object; preserve information deterministically.
        if "flags" in value and isinstance(value["flags"], list):
            return [str(v) for v in value["flags"] if v is not None]
        return [str(k) for k in value.keys()]
    return [str(value)]


def _call_gemini_with_retry(client: genai.Client, prompt_text: str) -> Dict:
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt_text,
                config={"temperature": 0.1},
            )
            raw = _extract_response_text(response)
            if not raw:
                raise ValueError("Gemini returned empty response body")
            return _parse_json(raw)
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
            else:
                logger.error("Gemini API failed after retries: %s", e)
    raise RuntimeError("Gemini API call failed") from last_error


def extract_from_document(file_bytes: bytes, document_id: str) -> ExtractionResult:
    if os.getenv("USE_DEMO_CACHE", "false").lower() == "true":
        cache_path = Path(__file__).resolve().parent.parent.parent / "test-data" / "cached_extraction.json"
        if cache_path.is_file():
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)
            data["document_id"] = document_id
            if isinstance(data.get("section_map"), dict):
                data["section_map"] = {str(k): v for k, v in data["section_map"].items()}
            medications = []
            for m in data.get("medications", []):
                med = dict(m)
                med.setdefault("name", med.get("generic_name") or med.get("brand_name"))
                medications.append(Medication(**med))
            return ExtractionResult(
                document_id=document_id,
                patient=PatientInfo(**data.get("patient", {})),
                encounter=EncounterInfo(**data.get("encounter", {})),
                diagnoses=[Diagnosis(**d) for d in data.get("diagnoses", [])],
                procedures=[Procedure(**p) for p in data.get("procedures", [])],
                medications=medications,
                billed_codes=data.get("billed_codes", []),
                raw_text_preview=(data.get("raw_text_preview") or "")[:500],
                detected_script=data.get("detected_script"),
                section_map=data.get("section_map") or {},
                negated_spans=data.get("negated_spans") or [],
                low_confidence_flags=data.get("low_confidence_flags", []),
            )

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")

    client = genai.Client(api_key=api_key)
    raw_text = extract_text_from_pdf(file_bytes)

    if not raw_text or len(raw_text) < 100:
        b64_image = pdf_to_base64_image(file_bytes)
        if not b64_image:
            raise ValueError("Could not extract text or image from PDF")
        raw_text = f"[scanned_image_b64]\n{b64_image[:8000]}"

    spacy_result = preprocess(raw_text)
    prompt_payload = {
        "expanded_text": spacy_result["expanded_text"],
        "section_map": spacy_result["section_map"],
        "negated_spans": spacy_result["negated_spans"],
    }
    prompt_text = f"{EXTRACTION_SYSTEM_PROMPT}\n\nINPUT:\n{json.dumps(prompt_payload, ensure_ascii=False)}"

    data = _call_gemini_with_retry(client, prompt_text)
    data = apply_negation_override(data, spacy_result["negated_spans"])
    data["diagnoses"] = validate_icd10_codes(data.get("diagnoses", []))
    data["low_confidence_flags"] = _normalize_low_confidence_flags(
        data.get("low_confidence_flags")
    )

    medications = []
    for m in data.get("medications", []):
        med = dict(m)
        med.setdefault("name", med.get("generic_name") or med.get("brand_name"))
        medications.append(Medication(**med))

    return ExtractionResult(
        document_id=document_id,
        patient=PatientInfo(**data.get("patient", {})),
        encounter=EncounterInfo(**data.get("encounter", {})),
        diagnoses=[Diagnosis(**d) for d in data.get("diagnoses", [])],
        procedures=[Procedure(**p) for p in data.get("procedures", [])],
        medications=medications,
        billed_codes=data.get("billed_codes", []),
        raw_text_preview=spacy_result["expanded_text"][:500],
        detected_script=spacy_result.get("detected_script"),
        section_map=spacy_result.get("section_map", {}),
        negated_spans=spacy_result.get("negated_spans", []),
        low_confidence_flags=data.get("low_confidence_flags", []),
    )
