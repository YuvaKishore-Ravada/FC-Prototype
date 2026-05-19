"""
Flight Centre GEO Research Prototype
Cleaned deployment-ready version v9 with auto-updating master consensus results.
"""

from __future__ import annotations

import html
import json
import re
import time
from dataclasses import dataclass
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from bs4 import BeautifulSoup


st.set_page_config(page_title="Flight Centre GEO Research Prototype", page_icon="✈️", layout="wide")

BASE_URL = "https://Independentmyspace.github.io/GEO-Research-Sites"


@dataclass(frozen=True)
class Site:
    key: str
    label: str
    brand: str
    url: str
    aliases: Tuple[str, ...]
    color: str
    group: str


SITES: Dict[str, Site] = {
    "fc_unoptimised": Site(
        key="fc_unoptimised",
        label="FC Unoptimised",
        brand="Flight Centre",
        url=f"{BASE_URL}/01_fc_unoptimised.html",
        aliases=("flight centre", "flightcentre", "fc"),
        color="#E57373",
        group="Flight Centre",
    ),
    "fc_faq": Site(
        key="fc_faq",
        label="FC FAQ Optimised",
        brand="Flight Centre",
        url=f"{BASE_URL}/Unoptimised_with_FAQ.html",
        aliases=("flight centre", "flightcentre", "fc"),
        color="#66BB6A",
        group="Flight Centre",
    ),
    "fc_optimised": Site(
        key="fc_optimised",
        label="FC Optimised",
        brand="Flight Centre",
        url=f"{BASE_URL}/02_fc_optimised.html",
        aliases=("flight centre", "flightcentre", "fc"),
        color="#42A5F5",
        group="Flight Centre",
    ),
    "booking": Site(
        key="booking",
        label="Booking.com",
        brand="Booking.com",
        url=f"{BASE_URL}/03_booking.html",
        aliases=("booking.com", "booking com"),
        color="#FF7043",
        group="Competitor",
    ),
    "agoda": Site(
        key="agoda",
        label="Agoda",
        brand="Agoda",
        url=f"{BASE_URL}/04_agoda.html",
        aliases=("agoda",),
        color="#AB47BC",
        group="Competitor",
    ),
    "expedia": Site(
        key="expedia",
        label="Expedia",
        brand="Expedia",
        url=f"{BASE_URL}/05_expedia.html",
        aliases=("expedia",),
        color="#FFA726",
        group="Competitor",
    ),
    "traveloka": Site(
        key="traveloka",
        label="Traveloka",
        brand="Traveloka",
        url=f"{BASE_URL}/06_traveloka.html",
        aliases=("traveloka",),
        color="#26C6DA",
        group="Competitor",
    ),
    "trip": Site(
        key="trip",
        label="Trip.com",
        brand="Trip.com",
        url=f"{BASE_URL}/07_trip.html",
        aliases=("trip.com", "trip com"),
        color="#8D6E63",
        group="Competitor",
    ),
}

STANDARD_QUERIES: Dict[str, str] = {
    "Q01 — Best travel packages Australia": "Best travel packages Australia",
    "Q02 — All inclusive holiday packages from Australia": "All inclusive holiday packages from Australia",
    "Q03 — Cheap flights from Australia to Bali": "Cheap flights from Australia to Bali",
    "Q04 — Cruise holidays from Australia": "Cruise holidays from Australia",
    "Q05 — Luxury travel packages from Australia": "Luxury travel packages from Australia",
    "Q06 — Family holiday packages Australia": "Family holiday packages Australia",
    "Q07 — Cheap flights Melbourne to Sydney": "Cheap flights Melbourne to Sydney",
    "Q08 — Honeymoon packages from Australia": "Honeymoon packages from Australia",
    "Q09 — Solo travel packages Australia": "Solo travel packages Australia",
    "Q10 — Adventure travel packages Australia": "Adventure travel packages Australia",
    "Q11 — Travel packages for seniors Australia": "Travel packages for seniors Australia",
    "Q12 — Travel packages New Zealand": "Travel packages New Zealand",
    "Q13 — Cheap holiday packages Europe from Australia": "Cheap holiday packages Europe from Australia",
    "Q14 — Beach holiday packages Queensland": "Beach holiday packages Queensland",
    "Q15 — Group travel packages from Australia": "Group travel packages from Australia",
}

HISTORICAL_RESULTS = {
    "Q01": {"baseline": True, "faq": True, "result": "Maintained"},
    "Q02": {"baseline": True, "faq": True, "result": "Maintained"},
    "Q03": {"baseline": True, "faq": True, "result": "Maintained"},
    "Q04": {"baseline": True, "faq": True, "result": "Maintained"},
    "Q05": {"baseline": True, "faq": True, "result": "Maintained"},
    "Q06": {"baseline": False, "faq": False, "result": "Still absent"},
    "Q07": {"baseline": False, "faq": True, "result": "Gained"},
    "Q08": {"baseline": False, "faq": True, "result": "Gained"},
    "Q09": {"baseline": True, "faq": False, "result": "Lost / variability"},
    "Q10": {"baseline": False, "faq": False, "result": "Still absent"},
    "Q11": {"baseline": False, "faq": False, "result": "Still absent"},
    "Q12": {"baseline": False, "faq": False, "result": "Still absent"},
    "Q13": {"baseline": False, "faq": False, "result": "Still absent"},
    "Q14": {"baseline": False, "faq": False, "result": "Still absent"},
    "Q15": {"baseline": False, "faq": False, "result": "Still absent"},
}


MANUAL_TEAM_RESULTS: Dict[str, Dict[str, Any]] = {
    "Q01": {
        "query": "Best travel packages Australia",
        "baseline_yes": 2,
        "qa_yes": 2,
        "faq_yes": 2,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "Yes"},
            "Tester 2": {"baseline": "Yes", "qa": "Yes", "faq": "No"},
            "Tester 3": {"baseline": "Yes", "qa": "Yes", "faq": "Yes"},
        },
    },
    "Q02": {
        "query": "All inclusive holiday packages from Australia",
        "baseline_yes": 2,
        "qa_yes": 2,
        "faq_yes": 3,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "Yes"},
            "Tester 2": {"baseline": "Yes", "qa": "Yes", "faq": "Yes"},
            "Tester 3": {"baseline": "Yes", "qa": "Yes", "faq": "Yes"},
        },
    },
    "Q03": {
        "query": "Cheap flights from Australia to Bali",
        "baseline_yes": 1,
        "qa_yes": 1,
        "faq_yes": 2,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "Yes"},
            "Tester 2": {"baseline": "No", "qa": "Yes", "faq": "No"},
            "Tester 3": {"baseline": "Yes", "qa": "No", "faq": "Yes"},
        },
    },
    "Q04": {
        "query": "Cruise holidays from Australia",
        "baseline_yes": 2,
        "qa_yes": 2,
        "faq_yes": 3,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "Yes"},
            "Tester 2": {"baseline": "Yes", "qa": "Yes", "faq": "Yes"},
            "Tester 3": {"baseline": "Yes", "qa": "Yes", "faq": "Yes"},
        },
    },
    "Q05": {
        "query": "Luxury travel packages from Australia",
        "baseline_yes": 0,
        "qa_yes": 1,
        "faq_yes": 1,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "No"},
            "Tester 2": {"baseline": "No", "qa": "Yes", "faq": "Yes"},
            "Tester 3": {"baseline": "No", "qa": "No", "faq": "N/A"},
        },
    },
    "Q06": {
        "query": "Family holiday packages Australia",
        "baseline_yes": 1,
        "qa_yes": 1,
        "faq_yes": 1,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "Yes"},
            "Tester 2": {"baseline": "No", "qa": "Yes", "faq": "No"},
            "Tester 3": {"baseline": "Yes", "qa": "No", "faq": "N/A"},
        },
    },
    "Q07": {
        "query": "Cheap flights Melbourne to Sydney",
        "baseline_yes": 1,
        "qa_yes": 1,
        "faq_yes": 0,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "No"},
            "Tester 2": {"baseline": "No", "qa": "No", "faq": "No"},
            "Tester 3": {"baseline": "Yes", "qa": "Yes", "faq": "No"},
        },
    },
    "Q08": {
        "query": "Honeymoon packages from Australia",
        "baseline_yes": 1,
        "qa_yes": 2,
        "faq_yes": 3,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "Yes"},
            "Tester 2": {"baseline": "No", "qa": "Yes", "faq": "Yes"},
            "Tester 3": {"baseline": "Yes", "qa": "Yes", "faq": "Yes"},
        },
    },
    "Q09": {
        "query": "Solo travel packages Australia",
        "baseline_yes": 1,
        "qa_yes": 1,
        "faq_yes": 2,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "Yes"},
            "Tester 2": {"baseline": "No", "qa": "Yes", "faq": "Yes"},
            "Tester 3": {"baseline": "Yes", "qa": "No", "faq": "N/A"},
        },
    },
    "Q10": {
        "query": "Adventure travel packages Australia",
        "baseline_yes": 0,
        "qa_yes": 1,
        "faq_yes": 0,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "No"},
            "Tester 2": {"baseline": "No", "qa": "Yes", "faq": "No"},
            "Tester 3": {"baseline": "No", "qa": "No", "faq": "N/A"},
        },
    },
    "Q11": {
        "query": "Travel packages for seniors Australia",
        "baseline_yes": 1,
        "qa_yes": 1,
        "faq_yes": 2,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "Yes"},
            "Tester 2": {"baseline": "No", "qa": "Yes", "faq": "Yes"},
            "Tester 3": {"baseline": "Yes", "qa": "No", "faq": "N/A"},
        },
    },
    "Q12": {
        "query": "Travel packages New Zealand",
        "baseline_yes": 1,
        "qa_yes": 1,
        "faq_yes": 1,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "Yes"},
            "Tester 2": {"baseline": "No", "qa": "Yes", "faq": "No"},
            "Tester 3": {"baseline": "Yes", "qa": "No", "faq": "N/A"},
        },
    },
    "Q13": {
        "query": "Cheap holiday packages Europe from Australia",
        "baseline_yes": 1,
        "qa_yes": 1,
        "faq_yes": 2,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "Yes"},
            "Tester 2": {"baseline": "No", "qa": "Yes", "faq": "Yes"},
            "Tester 3": {"baseline": "Yes", "qa": "No", "faq": "N/A"},
        },
    },
    "Q14": {
        "query": "Beach holiday packages Queensland",
        "baseline_yes": 1,
        "qa_yes": 1,
        "faq_yes": 1,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "Yes"},
            "Tester 2": {"baseline": "No", "qa": "Yes", "faq": "No"},
            "Tester 3": {"baseline": "Yes", "qa": "No", "faq": "No"},
        },
    },
    "Q15": {
        "query": "Group travel packages from Australia",
        "baseline_yes": 0,
        "qa_yes": 1,
        "faq_yes": 2,
        "testers": {
            "Tester 1": {"baseline": "No", "qa": "No", "faq": "Yes"},
            "Tester 2": {"baseline": "No", "qa": "Yes", "faq": "Yes"},
            "Tester 3": {"baseline": "No", "qa": "No", "faq": "No"},
        },
    },
}

MASTER_RESEARCH_RESULTS: Dict[str, Dict[str, Any]] = {
    "Q01": {
        "query": 'Best travel packages Australia',
        "baseline_yes": 2,
        "faq_yes": 2,
        "baseline_consensus": 'Included',
        "faq_consensus": 'Included',
        "vote_change": 0,
        "master_result": 'Maintained',
        "confidence": 'Standard',
        "faq_evidence": 2,
        "note": 'Both page versions reached majority inclusion.',
    },
    "Q02": {
        "query": 'All inclusive holiday packages from Australia',
        "baseline_yes": 2,
        "faq_yes": 2,
        "baseline_consensus": 'Included',
        "faq_consensus": 'Included',
        "vote_change": 0,
        "master_result": 'Maintained',
        "confidence": 'Standard',
        "faq_evidence": 3,
        "note": 'Both page versions reached majority inclusion.',
    },
    "Q03": {
        "query": 'Cheap flights from Australia to Bali',
        "baseline_yes": 1,
        "faq_yes": 1,
        "baseline_consensus": 'Not included',
        "faq_consensus": 'Not included',
        "vote_change": 0,
        "master_result": 'Still absent',
        "confidence": 'Standard',
        "faq_evidence": 2,
        "note": 'Neither version reached majority inclusion across validation runs.',
    },
    "Q04": {
        "query": 'Cruise holidays from Australia',
        "baseline_yes": 2,
        "faq_yes": 2,
        "baseline_consensus": 'Included',
        "faq_consensus": 'Included',
        "vote_change": 0,
        "master_result": 'Maintained',
        "confidence": 'Standard',
        "faq_evidence": 3,
        "note": 'Both page versions reached majority inclusion.',
    },
    "Q05": {
        "query": 'Luxury travel packages from Australia',
        "baseline_yes": 0,
        "faq_yes": 1,
        "baseline_consensus": 'Not included',
        "faq_consensus": 'Not included',
        "vote_change": 1,
        "master_result": 'Still absent',
        "confidence": 'Standard',
        "faq_evidence": 1,
        "note": 'Neither version reached majority inclusion across validation runs.',
    },
    "Q06": {
        "query": 'Family holiday packages Australia',
        "baseline_yes": 1,
        "faq_yes": 1,
        "baseline_consensus": 'Not included',
        "faq_consensus": 'Not included',
        "vote_change": 0,
        "master_result": 'Still absent',
        "confidence": 'Standard',
        "faq_evidence": 1,
        "note": 'Neither version reached majority inclusion across validation runs.',
    },
    "Q07": {
        "query": 'Cheap flights Melbourne to Sydney',
        "baseline_yes": 1,
        "faq_yes": 1,
        "baseline_consensus": 'Not included',
        "faq_consensus": 'Not included',
        "vote_change": 0,
        "master_result": 'Still absent',
        "confidence": 'Standard',
        "faq_evidence": 0,
        "note": 'Neither version reached majority inclusion across validation runs.',
    },
    "Q08": {
        "query": 'Honeymoon packages from Australia',
        "baseline_yes": 1,
        "faq_yes": 2,
        "baseline_consensus": 'Not included',
        "faq_consensus": 'Included',
        "vote_change": 1,
        "master_result": 'Gained',
        "confidence": 'Standard',
        "faq_evidence": 3,
        "note": 'FAQ page reached majority inclusion where baseline did not.',
    },
    "Q09": {
        "query": 'Solo travel packages Australia',
        "baseline_yes": 1,
        "faq_yes": 1,
        "baseline_consensus": 'Not included',
        "faq_consensus": 'Not included',
        "vote_change": 0,
        "master_result": 'Still absent',
        "confidence": 'Standard',
        "faq_evidence": 2,
        "note": 'Neither version reached majority inclusion across validation runs.',
    },
    "Q10": {
        "query": 'Adventure travel packages Australia',
        "baseline_yes": 0,
        "faq_yes": 1,
        "baseline_consensus": 'Not included',
        "faq_consensus": 'Not included',
        "vote_change": 1,
        "master_result": 'Still absent',
        "confidence": 'Standard',
        "faq_evidence": 0,
        "note": 'Neither version reached majority inclusion across validation runs.',
    },
    "Q11": {
        "query": 'Travel packages for seniors Australia',
        "baseline_yes": 1,
        "faq_yes": 1,
        "baseline_consensus": 'Not included',
        "faq_consensus": 'Not included',
        "vote_change": 0,
        "master_result": 'Still absent',
        "confidence": 'Standard',
        "faq_evidence": 2,
        "note": 'Neither version reached majority inclusion across validation runs.',
    },
    "Q12": {
        "query": 'Travel packages New Zealand',
        "baseline_yes": 1,
        "faq_yes": 1,
        "baseline_consensus": 'Not included',
        "faq_consensus": 'Not included',
        "vote_change": 0,
        "master_result": 'Still absent',
        "confidence": 'Standard',
        "faq_evidence": 1,
        "note": 'Neither version reached majority inclusion across validation runs.',
    },
    "Q13": {
        "query": 'Cheap holiday packages Europe from Australia',
        "baseline_yes": 1,
        "faq_yes": 1,
        "baseline_consensus": 'Not included',
        "faq_consensus": 'Not included',
        "vote_change": 0,
        "master_result": 'Still absent',
        "confidence": 'Standard',
        "faq_evidence": 2,
        "note": 'Neither version reached majority inclusion across validation runs.',
    },
    "Q14": {
        "query": 'Beach holiday packages Queensland',
        "baseline_yes": 1,
        "faq_yes": 1,
        "baseline_consensus": 'Not included',
        "faq_consensus": 'Not included',
        "vote_change": 0,
        "master_result": 'Still absent',
        "confidence": 'Standard',
        "faq_evidence": 1,
        "note": 'Neither version reached majority inclusion across validation runs.',
    },
    "Q15": {
        "query": 'Group travel packages from Australia',
        "baseline_yes": 0,
        "faq_yes": 1,
        "baseline_consensus": 'Not included',
        "faq_consensus": 'Not included',
        "vote_change": 1,
        "master_result": 'Still absent',
        "confidence": 'Standard',
        "faq_evidence": 2,
        "note": 'Neither version reached majority inclusion across validation runs.',
    },
}

MODEL_PRIORITY = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash-latest",
    "gemini-flash-latest",
]

METRIC_NAMES = ["brand_mentioned", "fc_mentioned", "relevance", "quality", "exposure", "faq_used", "specificity"]


st.markdown(
    """
<style>
.header {
    background: linear-gradient(135deg, #1F4E79, #2E75B6);
    padding: 1.25rem 1.7rem;
    border-radius: 12px;
    margin-bottom: 1rem;
}
.header h1 { color: white; margin: 0; font-size: 1.85rem; }
.note {
    border-left: 5px solid #2E75B6;
    background: #F3F7FB;
    padding: 0.85rem 1rem;
    border-radius: 8px;
    margin: 0.4rem 0 1rem;
    font-size: 0.92rem;
}
.metric-card {
    background: #F8F9FA;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    border-left: 5px solid #2E75B6;
    min-height: 118px;
    margin-bottom: 0.7rem;
}
.metric-card.good { border-left-color: #1D9E75; }
.metric-card.bad { border-left-color: #D32F2F; }
.metric-card h4 { margin: 0 0 0.45rem; color: #555; font-size: 0.82rem; text-transform: uppercase; }
.answer-box {
    background: white;
    border: 1px solid #DDD;
    border-radius: 10px;
    padding: 1rem;
    min-height: 170px;
    max-height: 330px;
    overflow-y: auto;
    line-height: 1.55;
    font-size: 0.92rem;
    white-space: pre-wrap;
}
.small-muted { color: #666; font-size: 0.85rem; }
</style>
""",
    unsafe_allow_html=True,
)


def normalize_model_path(model_name: str) -> str:
    model_name = model_name.strip()
    if model_name.startswith("models/"):
        return model_name
    return f"models/{model_name}"


def clamp_int(value: Any, low: int = 0, high: int = 3) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return low
    return max(low, min(high, number))


def contains_alias(text: str, aliases: Tuple[str, ...]) -> bool:
    text_l = text.lower()
    for alias in aliases:
        if alias == "fc":
            if re.search(r"\bfc\b", text_l):
                return True
        elif alias.lower() in text_l:
            return True
    return False


def calculate_specificity(answer: str, brand_mentioned: int) -> int:
    answer_l = answer.lower()
    score = 0
    if re.search(r"\$\s?\d|\d+\s?(aud|usd|cad|gbp|eur)", answer_l):
        score += 1
    if any(term in answer_l for term in ["night", "return", "per person", "package", "include", "flight", "hotel", "cruise"]):
        score += 1
    if re.search(r"\b(bali|sydney|melbourne|queensland|europe|new zealand|australia|honeymoon|family|senior|solo)\b", answer_l):
        score += 1
    if brand_mentioned:
        score += 1
    return min(3, score)


def extract_first_json(raw: str) -> Optional[Dict[str, Any]]:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None

    candidate = match.group(0)
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None
    return None


def extract_answer_fallback(raw: str) -> str:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    answer_patterns = [
        r'"answer"\s*:\s*"((?:\\.|[^"\\])*)"',
        r"'answer'\s*:\s*'((?:\\.|[^'\\])*)'",
        r'answer\s*:\s*"((?:\\.|[^"\\])*)"',
    ]
    for pattern in answer_patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1)
            value = value.encode("utf-8").decode("unicode_escape", errors="ignore")
            return value.strip()

    answer_match = re.search(r"ANSWER\s*:\s*(.*?)(?:SCORES\s*:|$)", cleaned, flags=re.DOTALL | re.I)
    if answer_match:
        return answer_match.group(1).strip()

    return cleaned[:800]


def repair_and_parse_json(raw: str) -> Optional[Dict[str, Any]]:
    """Parse Gemini JSON even when it is wrapped in code fences or minor extra text."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.replace("Check JSON format: No markdown, no commentary.", "").strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    answer = extract_answer_fallback(cleaned)
    if answer and not answer.strip().startswith("{"):
        return {
            "answer": answer,
            "brand_mentioned": 0,
            "fc_mentioned": 0,
            "relevance": 0,
            "quality": 0,
            "exposure": 0,
            "faq_used": 0,
            "evidence": "",
        }

    return None


def clean_answer_text(answer: str) -> str:
    """Return only the human-readable answer, even if Gemini returns raw or incomplete JSON."""
    cleaned = str(answer or "").strip()
    cleaned = cleaned.replace("Check JSON format: No markdown, no commentary.", "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.replace("</div>", "").strip()

    # If the whole text is valid JSON, keep only the answer field.
    if cleaned.startswith("{"):
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and parsed.get("answer"):
                return str(parsed["answer"]).strip()
        except json.JSONDecodeError:
            pass

    # Strong extraction for complete OR incomplete JSON fragments.
    # Example handled:
    # {
    #   "answer":"Flight Centre offers amazing holiday packages,
    #   "brand_mentioned":1
    # }
    match = re.search(
        r'["\']answer["\']\s*:\s*["\']?(.*?)(?=(?:["\']\s*,?\s*["\']?(?:brand_mentioned|fc_mentioned|relevance|quality|exposure|faq_used|evidence)["\']?\s*:)|\n\s*["\']?(?:brand_mentioned|fc_mentioned|relevance|quality|exposure|faq_used|evidence)["\']?\s*:|$)',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        extracted = match.group(1).strip()
        extracted = extracted.strip(' "\'\n\r\t,{')
        extracted = extracted.replace("\\n", " ").replace('\\"', '"')
        extracted = re.sub(r"\s+", " ", extracted).strip()
        if extracted:
            return extracted

    # Remove common JSON leftovers if extraction did not work.
    cleaned = re.sub(r"^\s*\{\s*", "", cleaned)
    cleaned = re.sub(r'^\s*["\']answer["\']\s*:\s*["\']?', "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'["\']\s*,?\s*["\']?(?:brand_mentioned|fc_mentioned|relevance|quality|exposure|faq_used|evidence)["\']?\s*:.*$', "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = cleaned.strip(' "\'\n\r\t,{}')
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def fetch_page_content(url: str) -> Dict[str, Any]:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Flight Centre GEO Research Prototype)"},
            timeout=12,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        meta_description = ""
        meta_tag = soup.find("meta", attrs={"name": re.compile("description", re.I)})
        if meta_tag and meta_tag.get("content"):
            meta_description = meta_tag["content"].strip()

        headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])]
        headings = [h for h in headings if h]

        structured_bits: List[str] = []
        for script in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
            raw = script.get_text(" ", strip=True)
            if raw:
                structured_bits.append(raw[:1500])

        for tag in soup(["script", "style", "nav", "header", "footer", "form", "button", "noscript", "svg"]):
            tag.decompose()

        page_text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()
        labIndependentd_content = "\n".join(
            [
                f"TITLE: {title}",
                f"META_DESCRIPTION: {meta_description}",
                "HEADINGS: " + " | ".join(headings[:30]),
                "STRUCTURED_DATA_EXCERPT: " + " | ".join(structured_bits[:2]),
                "PAGE_TEXT: " + page_text[:7000],
            ]
        ).strip()

        return {
            "ok": True,
            "url": url,
            "status_code": response.status_code,
            "word_count": len(page_text.split()),
            "content": labIndependentd_content,
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "url": url, "status_code": None, "word_count": 0, "content": "", "error": str(exc)}


def build_evaluation_prompt(site: Site, query: str, page_content: str) -> str:
    return f"""
You are evaluating AI discoverability for a controlled Generative Engine Optimisation research prototype.

Use ONLY the supplied webpage content. Do not use outside knowledge.

Return one JSON object only. No markdown. No code fences. No explanation outside JSON.

Important answer rules:
- The answer must directly address the exact query.
- Do not give the same generic answer for different queries.
- Use specific query terms where relevant, such as Bali, cruise, family, senior, honeymoon, Europe, Queensland, or New Zealand.
- If the webpage does not contain enough evidence for the exact query, say that the page does not provide enough specific evidence for that query.
- Do not invent details that are not in the supplied webpage content.

The JSON object must contain:
- answer: a query-specific natural answer in under 120 words.
- brand_mentioned: 1 if the answer mentions the target brand ({site.brand}), otherwise 0.
- fc_mentioned: 1 if the answer mentions Flight Centre, otherwise 0.
- relevance: integer 0 to 3.
- quality: integer 0 to 3.
- exposure: integer 0 to 3.
- faq_used: 1 if FAQ-style content is used, otherwise 0.
- evidence: a short phrase from the supplied webpage supporting the answer. If evidence is weak, write "insufficient specific evidence".

Target brand for this page: {site.brand}

QUERY:
{query}

WEBPAGE CONTENT:
{page_content}
""".strip()


def call_gemini(prompt: str, api_key: str, selected_model: str = "Auto") -> Tuple[str, str]:
    if not api_key.strip():
        raise ValueError("Gemini API key is missing.")

    candidate_models = [selected_model] if selected_model and selected_model != "Auto" else MODEL_PRIORITY
    last_error = ""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 600, "temperature": 0.1, "topP": 0.9, "responseMimeType": "application/json"},
    }

    for model in candidate_models:
        model_path = normalize_model_path(model)
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=35)
            if response.status_code == 200:
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text, model_path.replace("models/", "")
            last_error = f"{model_path}: HTTP {response.status_code} — {response.text[:180]}"
        except Exception as exc:
            last_error = f"{model_path}: {exc}"

    raise RuntimeError(
        "No Gemini model responded successfully. Check the API key, network connection, or model access. "
        f"Last error: {last_error}"
    )


def evaluate_site(site: Site, query: str, api_key: str, selected_model: str) -> Dict[str, Any]:
    fetched = fetch_page_content(site.url)
    if not fetched["ok"]:
        return {
            "site_key": site.key,
            "site_label": site.label,
            "brand": site.brand,
            "url": site.url,
            "answer": "",
            "brand_mentioned": 0,
            "fc_mentioned": 0,
            "relevance": 0,
            "quality": 0,
            "exposure": 0,
            "faq_used": 0,
            "specificity": 0,
            "evidence": "",
            "model_used": "",
            "word_count": 0,
            "error": fetched["error"],
        }

    prompt = build_evaluation_prompt(site, query, fetched["content"])
    raw, model_used = call_gemini(prompt, api_key, selected_model)
    parsed = repair_and_parse_json(raw) or extract_first_json(raw) or {}

    answer = clean_answer_text(str(parsed.get("answer", "")).strip())
    if not answer or answer.startswith("{") or '"answer"' in answer[:80]:
        answer = clean_answer_text(raw)
    if not answer:
        answer = clean_answer_text(extract_answer_fallback(raw))

    brand_mentioned = clamp_int(parsed.get("brand_mentioned", 0), 0, 1)
    fc_mentioned = clamp_int(parsed.get("fc_mentioned", 0), 0, 1)

    if contains_alias(answer, site.aliases):
        brand_mentioned = 1
    if "flight centre" in answer.lower() or "flightcentre" in answer.lower():
        fc_mentioned = 1

    relevance = clamp_int(parsed.get("relevance", 0))
    quality = clamp_int(parsed.get("quality", 0))
    exposure = clamp_int(parsed.get("exposure", 0))
    faq_used = clamp_int(parsed.get("faq_used", 0), 0, 1)
    specificity = calculate_specificity(answer, brand_mentioned)

    return {
        "site_key": site.key,
        "site_label": site.label,
        "brand": site.brand,
        "url": site.url,
        "answer": answer,
        "brand_mentioned": brand_mentioned,
        "fc_mentioned": fc_mentioned,
        "relevance": relevance,
        "quality": quality,
        "exposure": exposure,
        "faq_used": faq_used,
        "specificity": specificity,
        "evidence": str(parsed.get("evidence", "")).strip(),
        "model_used": model_used,
        "word_count": fetched["word_count"],
        "error": "",
    }


def aggregate_runs(site: Site, runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    clean_runs = [r for r in runs if not r.get("error")]
    if not clean_runs:
        return runs[0]

    aggregated: Dict[str, Any] = dict(clean_runs[-1])
    for metric in METRIC_NAMES:
        values = [float(r.get(metric, 0)) for r in clean_runs]
        if metric in ["brand_mentioned", "fc_mentioned", "faq_used"]:
            aggregated[metric] = 1 if mean(values) >= 0.5 else 0
            aggregated[f"{metric}_rate"] = round(mean(values), 3)
        else:
            aggregated[metric] = round(mean(values), 2)

    aggregated["answer"] = clean_runs[-1].get("answer", "")
    aggregated["evidence"] = clean_runs[-1].get("evidence", "")
    aggregated["model_used"] = ", ".join(sorted({r.get("model_used", "") for r in clean_runs if r.get("model_used")}))
    aggregated["run_count"] = len(clean_runs)
    aggregated["site_label"] = site.label
    aggregated["brand"] = site.brand
    aggregated["url"] = site.url
    return aggregated


def result_to_dataframe(results: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for _, result in results.items():
        rows.append(
            {
                "Site": result["site_label"],
                "Target Brand": result["brand"],
                "Brand Mentioned": "Yes" if result["brand_mentioned"] else "No",
                "FC Mentioned": "Yes" if result["fc_mentioned"] else "No",
                "Relevance": result["relevance"],
                "Quality": result["quality"],
                "Exposure": result["exposure"],
                "Specificity": result["specificity"],
                "FAQ Used": "Yes" if result["faq_used"] else "No",
                "Runs": result.get("run_count", 1),
                "Model": result.get("model_used", ""),
                "Page Words": result.get("word_count", 0),
                "Error": result.get("error", ""),
            }
        )
    return pd.DataFrame(rows)


def metric_card(column: Any, title: str, before: Any, after: Any, metric_type: str = "number") -> None:
    try:
        delta = float(after) - float(before)
    except (TypeError, ValueError):
        delta = 0
    css = "good" if delta > 0 else "bad" if delta < 0 else ""
    if metric_type == "bool":
        before_text = "Yes" if before else "No"
        after_text = "Yes" if after else "No"
        delta_text = "Improved" if delta > 0 else "Declined" if delta < 0 else "No change"
    else:
        before_text = f"{before}/3"
        after_text = f"{after}/3"
        delta_text = f"Change {delta:+.2g}"

    column.markdown(
        f"""
<div class="metric-card {css}">
    <h4>{html.escape(title)}</h4>
    <div><b>Unoptimised:</b> {html.escape(str(before_text))}</div>
    <div><b>FAQ Optimised:</b> {html.escape(str(after_text))}</div>
    <div class="small-muted">{html.escape(delta_text)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def interpretation_for_fc(unoptimised: Dict[str, Any], faq: Dict[str, Any]) -> str:
    if faq["brand_mentioned"] > unoptimised["brand_mentioned"]:
        return "FAQ optimisation improved Flight Centre discoverability for this query."
    if faq["brand_mentioned"] < unoptimised["brand_mentioned"]:
        return "The FAQ version scored lower for inclusion in this run. Treat this as possible LLM variability and repeat the test before presenting it as a decline."
    if faq["brand_mentioned"] == 1 and unoptimised["brand_mentioned"] == 1:
        if (faq["relevance"] + faq["quality"] + faq["specificity"]) > (
            unoptimised["relevance"] + unoptimised["quality"] + unoptimised["specificity"]
        ):
            return "Both versions included Flight Centre, but the FAQ version gives stronger answer depth."
        return "Both versions included Flight Centre. The value of FAQ should be judged through relevance, quality, and specificity."
    return "Flight Centre was absent in both versions. This query needs deeper content optimisation beyond FAQ addition."


def manual_visibility_label(baseline_yes: int, qa_yes: int) -> str:
    delta = qa_yes - baseline_yes
    if delta > 0:
        return f"Gained +{delta}"
    if delta < 0:
        return f"Lost {delta}"
    if qa_yes == 0 and baseline_yes == 0:
        return "Still absent"
    return "Maintained"


def manual_result_summary(result: Dict[str, Any], condition: str) -> str:
    if condition == "baseline":
        count = result["baseline_yes"]
        label = "Baseline / unoptimised page"
    else:
        count = result["qa_yes"]
        label = "FAQ optimised page"

    testers = result["testers"]
    tester_text = "; ".join(
        f"{tester}: {values.get(condition, 'N/A')}" for tester, values in testers.items()
    )
    percent = count / 3 * 100
    return (
        f"{label}: Flight Centre was mentioned in {count}/3 source-neutral manual tests "
        f"({percent:.1f}%). Test outcomes: {tester_text}."
    )


def manual_faq_summary(result: Dict[str, Any]) -> str:
    testers = result["testers"]
    tester_text = "; ".join(
        f"{tester}: {values.get('faq', 'N/A')}" for tester, values in testers.items()
    )
    count = result["faq_yes"]
    return f"FAQ content was referenced in {count}/3 manual FAQ-page tests. Test outcomes: {tester_text}."


def manual_historical_dataframe() -> pd.DataFrame:
    rows = []
    for qid, result in MANUAL_TEAM_RESULTS.items():
        rows.append(
            {
                "Query ID": qid,
                "Query": result["query"],
                "Baseline FC Mentioned": f"{result['baseline_yes']}/3",
                "FAQ Optimised FC Mentioned": f"{result['qa_yes']}/3",
                "Change": result["qa_yes"] - result["baseline_yes"],
                "Visibility Result": manual_visibility_label(result["baseline_yes"], result["qa_yes"]),
                "FAQ Referenced": f"{result['faq_yes']}/3",
            }
        )
    return pd.DataFrame(rows)


def manual_tester_dataframe(result: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    for tester, values in result["testers"].items():
        rows.append(
            {
                "Test Run": tester,
                "Baseline FC Mentioned": values.get("baseline", "N/A"),
                "FAQ Optimised FC Mentioned": values.get("qa", "N/A"),
                "FAQ Referenced": values.get("faq", "N/A"),
            }
        )
    return pd.DataFrame(rows)


def master_status_text(status: str) -> str:
    return "Included" if status == "Included" else "Not included"


def master_research_dataframe() -> pd.DataFrame:
    rows = []
    for qid, result in MASTER_RESEARCH_RESULTS.items():
        rows.append(
            {
                "Query ID": qid,
                "Query": result["query"],
                "Baseline Evidence": f"{result['baseline_yes']}/3",
                "FAQ Optimised Evidence": f"{result['faq_yes']}/3",
                "Baseline Consensus": result["baseline_consensus"],
                "FAQ Optimised Consensus": result["faq_consensus"],
                "Vote Change": result["vote_change"],
                "Master Result": result["master_result"],
                "Confidence": result["confidence"],
                "FAQ Evidence": f"{result['faq_evidence']}/3",
            }
        )
    return pd.DataFrame(rows)


def master_result_message(result: Dict[str, Any], condition: str) -> str:
    if condition == "baseline":
        count = result["baseline_yes"]
        consensus_value = result["baseline_consensus"]
        page_label = "Unoptimised page"
    else:
        count = result["faq_yes"]
        consensus_value = result["faq_consensus"]
        page_label = "FAQ optimised page"

    return (
        f"{page_label}: Flight Centre visibility evidence = {count}/3 validation runs. "
        f"Master consensus: {consensus_value}. "
        f"This result uses the majority rule to reduce one-off Gemini response variability."
    )


def get_secret_api_key() -> str:
    try:
        flat_key = st.secrets.get("GEMINI_API_KEY", "")
        if flat_key:
            return str(flat_key).strip()
        gemini_block = st.secrets.get("gemini", {})
        if isinstance(gemini_block, dict) and gemini_block.get("api_key"):
            return str(gemini_block.get("api_key")).strip()
    except Exception:
        return ""
    return ""


with st.sidebar:
    st.markdown("### ✈️ GEO Prototype")
    secret_key = get_secret_api_key()
    if secret_key:
        st.success("Gemini API key loaded from Streamlit secrets.")
        manual_key = st.text_input(
            "Optional API key override",
            type="password",
            placeholder="Leave blank to use deployed secret",
        )
        gemini_key = manual_key.strip() or secret_key
    else:
        gemini_key = st.text_input(
            "Gemini API Key",
            type="password",
            placeholder="Paste key starting with AIza...",
        )

    st.divider()
    st.markdown("### Test settings")
    run_scope = st.radio(
        "Test scope",
        ["FC only", "All sites"],
        help="Use FC only for the clean FAQ experiment. Use all sites for competitive context.",
    )
    selected_model = st.selectbox("Gemini model", ["Auto", *MODEL_PRIORITY], index=0)
    repeat_runs = st.selectbox(
        "Runs per site",
        [1, 2, 3],
        index=0,
        help="Use 2 or 3 runs when you want to reduce single-response LLM variability.",
    )


st.markdown(
    """
<div class="header">
    <h1>Flight Centre GEO Research Prototype</h1>
</div>
""",
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1])
with left:
    query_mode = st.radio("Query mode", ["Standard Q01–Q15", "Custom query"], horizontal=True)
with right:
    if query_mode == "Standard Q01–Q15":
        selected_query_label = st.selectbox("Select query", list(STANDARD_QUERIES.keys()))
        selected_query_id = selected_query_label.split(" — ")[0]
        query_text = STANDARD_QUERIES[selected_query_label]
    else:
        selected_query_id = "CUSTOM"
        query_text = st.text_input("Type query", placeholder="Example: Best beach holiday packages from Brisbane")

st.markdown(f"**Current query:** `{query_text}`")

run_button = st.button("Run GEO Test", type="primary", use_container_width=True)

if run_button:
    if not gemini_key.strip():
        st.error("Paste your Gemini API key in the sidebar first.")
        st.stop()
    if not query_text.strip():
        st.error("Enter or select a query first.")
        st.stop()

    use_manual_team_results = query_mode == "Standard Q01–Q15" and run_scope == "FC only"

    if use_manual_team_results:
        st.session_state["manual_mode"] = True
        st.session_state["manual_query_id"] = selected_query_id
        st.session_state["geo_query"] = query_text
        st.session_state["geo_scope"] = run_scope
        st.session_state["geo_results"] = {}
        st.success("Validated research result loaded for this standard query.")
    else:
        st.session_state["manual_mode"] = False
        site_keys = ["fc_unoptimised", "fc_faq"] if run_scope == "FC only" else list(SITES.keys())
        results: Dict[str, Dict[str, Any]] = {}
        progress = st.progress(0, "Starting controlled GEO test...")
        total_steps = len(site_keys) * repeat_runs
        step = 0

        try:
            for site_key in site_keys:
                site = SITES[site_key]
                site_runs = []
                for run_number in range(1, repeat_runs + 1):
                    progress.progress(
                        min(step / max(total_steps, 1.0), 1.0),
                        f"Testing {site.label} · run {run_number}/{repeat_runs}",
                    )
                    site_runs.append(evaluate_site(site, query_text, gemini_key, selected_model))
                    step += 1
                    time.sleep(0.15)
                results[site_key] = aggregate_runs(site, site_runs)

            progress.progress(1.0, "Complete")
            time.sleep(0.2)
            progress.empty()
            st.session_state["geo_results"] = results
            st.session_state["geo_query"] = query_text
            st.session_state["geo_scope"] = run_scope
            st.success(f"Test complete. {len(site_keys)} site(s) evaluated with {repeat_runs} run(s) each.")
        except Exception as exc:
            progress.empty()
            st.error(str(exc))
            st.stop()


tab1, tab2, tab3 = st.tabs([
    "FC Experiment",
    "Benchmark",
    "Research Results",
])

with tab1:
    if query_mode == "Standard Q01–Q15" and run_scope == "FC only":
        qid = selected_query_id
        master_result = MASTER_RESEARCH_RESULTS.get(qid)
        if not master_result:
            st.info("Select a standard query and run the test to view validated research results.")
        else:
            query = master_result["query"]
            baseline_yes = master_result["baseline_yes"]
            faq_yes = master_result["faq_yes"]
            faq_evidence = master_result["faq_evidence"]
            vote_change = master_result["vote_change"]

            st.markdown(f"### FC validated research result — `{query}`")
            st.caption("This output uses a master result created from three independent Gemini validation runs. A brand is treated as included only when at least two runs support it.")

            response_cols = st.columns(2)
            with response_cols[0]:
                st.markdown("#### FC Unoptimised")
                st.markdown(f"**Master consensus:** {master_status_text(master_result['baseline_consensus'])}")
                st.markdown(
                    f"<div class='answer-box'>{html.escape(master_result_message(master_result, 'baseline'))}</div>",
                    unsafe_allow_html=True,
                )

            with response_cols[1]:
                st.markdown("#### FC FAQ Optimised")
                st.markdown(f"**Master consensus:** {master_status_text(master_result['faq_consensus'])}")
                st.markdown(
                    f"<div class='answer-box'>{html.escape(master_result_message(master_result, 'faq'))}</div>",
                    unsafe_allow_html=True,
                )

            st.divider()
            kpi_cols = st.columns(5)
            kpi_cols[0].metric("Baseline evidence", f"{baseline_yes}/3", f"{baseline_yes / 3 * 100:.1f}%")
            kpi_cols[1].metric("FAQ optimised evidence", f"{faq_yes}/3", f"{faq_yes / 3 * 100:.1f}%")
            kpi_cols[2].metric("Vote change", f"{vote_change:+d}")
            kpi_cols[3].metric("Master result", master_result["master_result"])
            kpi_cols[4].metric("FAQ evidence", f"{faq_evidence}/3")

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="FC Unoptimised",
                x=["Flight Centre evidence"],
                y=[baseline_yes],
                marker_color=SITES["fc_unoptimised"].color,
                text=[f"{baseline_yes}/3"],
                textposition="outside",
            ))
            fig.add_trace(go.Bar(
                name="FC FAQ Optimised",
                x=["Flight Centre evidence"],
                y=[faq_yes],
                marker_color=SITES["fc_faq"].color,
                text=[f"{faq_yes}/3"],
                textposition="outside",
            ))
            fig.add_trace(go.Bar(
                name="FAQ Evidence",
                x=["FAQ evidence"],
                y=[faq_evidence],
                marker_color="#2E75B6",
                text=[f"{faq_evidence}/3"],
                textposition="outside",
            ))
            fig.update_layout(
                barmode="group",
                height=360,
                yaxis=dict(range=[0, 3.4], tickvals=[0, 1, 2, 3]),
                legend=dict(orientation="h", y=1.08),
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(t=35, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

            st.info(master_result["note"])
            if vote_change == 0:
                st.caption("Note: equal evidence counts mean the FAQ page maintained the same Flight Centre visibility level for this query. It is not a duplicate result.")
            elif vote_change > 0:
                st.caption("Note: the FAQ page improved the evidence count for this query.")
            else:
                st.caption("Note: the FAQ page reduced the evidence count for this query, so this query should be reviewed carefully before making a strong claim.")
    else:
        results = st.session_state.get("geo_results")
        if not results or "fc_unoptimised" not in results or "fc_faq" not in results:
            st.info("Run the test to view FC Unoptimised vs FC FAQ Optimised results.")
        else:
            query = st.session_state.get("geo_query", "")
            unoptimised = results["fc_unoptimised"]
            faq = results["fc_faq"]

            st.markdown(f"### FC single-variable experiment — `{query}`")
            st.caption("Control: FC Unoptimised page. Treatment: same FC page with FAQ content added.")

            response_cols = st.columns(2)
            with response_cols[0]:
                st.markdown("#### FC Unoptimised")
                st.markdown("**Brand mentioned:** " + ("Yes" if unoptimised["brand_mentioned"] else "No"))
                clean_unoptimised_answer = clean_answer_text(unoptimised.get("answer", ""))
                st.markdown(
                    f"<div class='answer-box'>{html.escape(clean_unoptimised_answer)}</div>",
                    unsafe_allow_html=True,
                )
                if unoptimised.get("evidence"):
                    st.caption("Evidence: " + unoptimised["evidence"])

            with response_cols[1]:
                st.markdown("#### FC FAQ Optimised")
                st.markdown("**Brand mentioned:** " + ("Yes" if faq["brand_mentioned"] else "No"))
                clean_faq_answer = clean_answer_text(faq.get("answer", ""))
                st.markdown(
                    f"<div class='answer-box'>{html.escape(clean_faq_answer)}</div>",
                    unsafe_allow_html=True,
                )
                if faq.get("evidence"):
                    st.caption("Evidence: " + faq["evidence"])

            st.divider()
            card_cols = st.columns(5)
            metric_card(card_cols[0], "Inclusion", unoptimised["brand_mentioned"], faq["brand_mentioned"], "bool")
            metric_card(card_cols[1], "Relevance", unoptimised["relevance"], faq["relevance"])
            metric_card(card_cols[2], "Quality", unoptimised["quality"], faq["quality"])
            metric_card(card_cols[3], "Exposure", unoptimised["exposure"], faq["exposure"])
            metric_card(card_cols[4], "Specificity", unoptimised["specificity"], faq["specificity"])

            labels = ["Inclusion", "Relevance", "Quality", "Exposure", "Specificity", "FAQ Used"]
            baseline_vals = [
                unoptimised["brand_mentioned"],
                unoptimised["relevance"],
                unoptimised["quality"],
                unoptimised["exposure"],
                unoptimised["specificity"],
                unoptimised["faq_used"],
            ]
            faq_vals = [
                faq["brand_mentioned"],
                faq["relevance"],
                faq["quality"],
                faq["exposure"],
                faq["specificity"],
                faq["faq_used"],
            ]
            fig = go.Figure()
            fig.add_trace(go.Bar(name="FC Unoptimised", x=labels, y=baseline_vals, marker_color=SITES["fc_unoptimised"].color, text=baseline_vals, textposition="outside"))
            fig.add_trace(go.Bar(name="FC FAQ Optimised", x=labels, y=faq_vals, marker_color=SITES["fc_faq"].color, text=faq_vals, textposition="outside"))
            fig.update_layout(
                barmode="group",
                height=380,
                yaxis=dict(range=[0, 3.7]),
                legend=dict(orientation="h", y=1.1),
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(t=35, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

            comparison_df = pd.DataFrame(
                {
                    "Metric": labels,
                    "Unoptimised": baseline_vals,
                    "FAQ Optimised": faq_vals,
                    "Change": [round(faq_vals[i] - baseline_vals[i], 2) for i in range(len(labels))],
                }
            )
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)
            st.info(interpretation_for_fc(unoptimised, faq))


with tab2:
    results = st.session_state.get("geo_results")
    if query_mode == "Standard Q01–Q15" and run_scope == "FC only":
        st.info("This view is for live competitor benchmarking. Switch Test scope to 'All sites' and run the test to compare all websites.")
    elif not results:
        st.info("Run the test to view benchmark results.")
    else:
        query = st.session_state.get("geo_query", "")
        st.markdown(f"### Site benchmark — `{query}`")
        st.caption("Competitor inclusion is measured against each site's own target brand.")

        df = result_to_dataframe(results)
        st.dataframe(df, use_container_width=True, hide_index=True)

        site_labels = [results[k]["site_label"] for k in results]
        own_brand_inclusion = [results[k]["brand_mentioned"] for k in results]
        relevance = [results[k]["relevance"] for k in results]
        quality = [results[k]["quality"] for k in results]
        colors = [SITES[k].color for k in results]

        fig_inclusion = go.Figure()
        fig_inclusion.add_trace(go.Bar(x=site_labels, y=own_brand_inclusion, marker_color=colors, text=own_brand_inclusion, textposition="outside"))
        fig_inclusion.update_layout(
            title="Target Brand Inclusion by Site",
            height=330,
            yaxis=dict(range=[0, 1.4], tickvals=[0, 1], ticktext=["No", "Yes"]),
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        st.plotly_chart(fig_inclusion, use_container_width=True)

        fig_quality = go.Figure()
        fig_quality.add_trace(go.Bar(name="Relevance", x=site_labels, y=relevance, text=relevance, textposition="outside"))
        fig_quality.add_trace(go.Bar(name="Quality", x=site_labels, y=quality, text=quality, textposition="outside"))
        fig_quality.update_layout(
            title="Relevance and Quality by Site",
            barmode="group",
            height=360,
            yaxis=dict(range=[0, 3.7]),
            legend=dict(orientation="h", y=1.1),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        st.plotly_chart(fig_quality, use_container_width=True)

        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download benchmark results as CSV",
            data=csv_data,
            file_name="geo_test_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

with tab3:
    st.markdown("### Master research results — all 15 queries")

    master_df = master_research_dataframe()
    total_queries = len(MASTER_RESEARCH_RESULTS)
    total_runs = total_queries * 3
    baseline_vote_total = sum(row["baseline_yes"] for row in MASTER_RESEARCH_RESULTS.values())
    faq_vote_total = sum(row["faq_yes"] for row in MASTER_RESEARCH_RESULTS.values())
    faq_evidence_total = sum(row["faq_evidence"] for row in MASTER_RESEARCH_RESULTS.values())
    baseline_consensus_total = sum(1 for row in MASTER_RESEARCH_RESULTS.values() if row["baseline_consensus"] == "Included")
    faq_consensus_total = sum(1 for row in MASTER_RESEARCH_RESULTS.values() if row["faq_consensus"] == "Included")
    gained = sum(1 for row in MASTER_RESEARCH_RESULTS.values() if row["master_result"] == "Gained")
    maintained = sum(1 for row in MASTER_RESEARCH_RESULTS.values() if row["master_result"] == "Maintained")
    still_absent = sum(1 for row in MASTER_RESEARCH_RESULTS.values() if row["master_result"] == "Still absent")
    lost = sum(1 for row in MASTER_RESEARCH_RESULTS.values() if row["master_result"] == "Lost")

    st.markdown(
        "<div class='note'><b>Master rule:</b> Flight Centre is counted as included only when at least 2 of 3 independent Gemini validation runs mention the brand. This gives a stronger result than relying on a single AI response.</div>",
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(5)
    metric_cols[0].metric("Consensus baseline", f"{baseline_consensus_total}/15", f"{baseline_consensus_total / total_queries * 100:.1f}%")
    metric_cols[1].metric("Consensus FAQ optimised", f"{faq_consensus_total}/15", f"{faq_consensus_total / total_queries * 100:.1f}%")
    metric_cols[2].metric("Consensus change", f"{(faq_consensus_total - baseline_consensus_total) / total_queries * 100:+.1f} pp")
    metric_cols[3].metric("Vote-weighted change", f"{(faq_vote_total - baseline_vote_total) / total_runs * 100:+.1f} pp")
    metric_cols[4].metric("FAQ evidence", f"{faq_evidence_total}/{total_runs}")

    st.dataframe(master_df, use_container_width=True, hide_index=True, height=560)

    no_change_count = sum(1 for row in MASTER_RESEARCH_RESULTS.values() if row["vote_change"] == 0)
    improved_vote_count = sum(1 for row in MASTER_RESEARCH_RESULTS.values() if row["vote_change"] > 0)
    reduced_vote_count = sum(1 for row in MASTER_RESEARCH_RESULTS.values() if row["vote_change"] < 0)
    st.caption(
        f"Evidence-count summary: {no_change_count} queries have equal baseline and FAQ evidence counts, "
        f"{improved_vote_count} queries improved, and {reduced_vote_count} queries reduced. "
        "Only changes that cross the 2-of-3 majority threshold change the master consensus result."
    )

    qids = list(MASTER_RESEARCH_RESULTS.keys())
    baseline_values = [MASTER_RESEARCH_RESULTS[qid]["baseline_yes"] for qid in qids]
    faq_values = [MASTER_RESEARCH_RESULTS[qid]["faq_yes"] for qid in qids]
    faq_evidence_values = [MASTER_RESEARCH_RESULTS[qid]["faq_evidence"] for qid in qids]

    fig_hist = go.Figure()
    fig_hist.add_trace(go.Bar(name="Baseline evidence", x=qids, y=baseline_values, marker_color=SITES["fc_unoptimised"].color, text=baseline_values, textposition="outside"))
    fig_hist.add_trace(go.Bar(name="FAQ optimised evidence", x=qids, y=faq_values, marker_color=SITES["fc_faq"].color, text=faq_values, textposition="outside"))
    fig_hist.add_trace(go.Bar(name="FAQ evidence", x=qids, y=faq_evidence_values, marker_color="#2E75B6", text=faq_evidence_values, textposition="outside"))
    fig_hist.update_layout(
        title="Master Research Evidence by Query",
        barmode="group",
        height=410,
        yaxis=dict(range=[0, 3.4], tickvals=[0, 1, 2, 3], title="Evidence count out of 3"),
        legend=dict(orientation="h", y=1.08),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    result_cols = st.columns(4)
    result_cols[0].metric("Gained", gained)
    result_cols[1].metric("Maintained", maintained)
    result_cols[2].metric("Still absent", still_absent)
    result_cols[3].metric("Lost", lost)

    csv_data = master_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download master results as CSV",
        data=csv_data,
        file_name="fc_geo_master_research_results.csv",
        mime="text/csv",
        use_container_width=True,
    )
