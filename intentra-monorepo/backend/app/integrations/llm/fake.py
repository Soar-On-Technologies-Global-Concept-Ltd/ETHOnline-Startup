"""Deterministic stand-in for the model (LLM_PROVIDER=fake, dev and test only). Outputs go through the same schemas and checks."""
import datetime as dt
import re

from app.core.explanation import RATIONALES, rec_text

AREAS = ["Surulere", "Yaba", "Ikeja", "Lekki", "Ajah", "Victoria Island", "Ikoyi", "Gbagada", "Magodo", "Maryland", "Festac",
         "Apapa", "Ogba", "Ojodu", "Ilupeju", "Ebute Metta", "Mushin", "Oshodi", "Agege", "Ketu", "Isolo", "Ogudu", "Oregun", "Ikorodu"]
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _date(text: str, today: dt.date) -> str | None:
    t = text.lower()
    if m := re.search(r"\b(\d{4}-\d{2}-\d{2})\b", t):
        return m.group(1)
    if "tomorrow" in t:
        return (today + dt.timedelta(days=1)).isoformat()
    if re.search(r"\btoday\b", t):
        return today.isoformat()
    for i, name in enumerate(WEEKDAYS):
        if re.search(rf"\b{name}\b", t):
            return (today + dt.timedelta(days=(i - today.weekday()) % 7)).isoformat()
    return None


def _budget(text: str) -> int | None:
    m = re.search(r"(?:₦|\bngn\s?)\s?(\d[\d,]*(?:\.\d+)?)\s*(k|m)?\b", text, re.I) \
        or re.search(r"\b(?:under|below|max(?:imum)?|budget(?:\s+of)?|up to)\s+(\d[\d,]*(?:\.\d+)?)\s*(k|m)?\b", text, re.I)
    if not m:
        return None
    unit = (m.group(2) or "").lower()
    return int(float(m.group(1).replace(",", "")) * (1_000 if unit == "k" else 1_000_000 if unit == "m" else 1))


def intent(data: dict) -> dict:
    text, today = data["text"], dt.date.fromisoformat(data["today"])
    if not re.search(r"\bpaint", text, re.I):
        return {"clarifying_question": "Intentra can book painting jobs for now. Is this a painting job?"}
    rooms = re.search(r"(\d+)\s*-?\s*(?:bed(?:room)?s?|rooms?)\b", text, re.I)
    area = next((a for a in AREAS if re.search(rf"\b{re.escape(a)}\b", text, re.I)), None)
    budget, date = _budget(text), _date(text, today)
    for value, question in ((rooms, "How many rooms should be painted?"), (area, "Which area of Lagos is the property in?"),
                            (budget, "What is the most you want to spend, in naira?"), (date, "Which day should the job happen?")):
        if not value:
            return {"clarifying_question": question}
    requirements = []
    if m := re.search(r"(\d+)\s*coats?\b", text, re.I):
        requirements.append(f"{m.group(1)} coats")
    if re.search(r"paint\s+included|with\s+paint|including\s+paint", text, re.I):
        requirements.append("paint included")
    return {"spec": {"service": "painting", "area": area, "rooms": int(rooms.group(1)), "budget_max_naira": budget,
                     "date": date, "requirements": requirements}}


def recommend(data: dict) -> dict:
    return {"items": [{"quote_id": q["quote_id"], **rec_text(q, data["request"])} for q in data["quotes"]]}


def evidence(data: dict) -> dict:
    covered = {e["scope_item"] for e in data["evidence"] if e["kind"] == "AFTER_PHOTO" and e.get("scope_item")}
    return {"items": [{"scope_item": item, "status": "covered" if item in covered else "missing",
                       "note": "After-photo uploaded." if item in covered else "No after-photo for this item."} for item in data["checklist"]]}


def resolve(data: dict) -> dict:
    category = data["complaint"]["category"]
    gaps = [k for k, v in (data.get("coverage") or {}).items() if v != "covered"]
    if category == "NO_SHOW":
        remedy, confidence = "REFUND_FULL", 0.9
    elif category == "INCOMPLETE":
        remedy, confidence = ("SPLIT_50_50", 0.7) if gaps else ("SPLIT_70_30", 0.78)
    elif category == "NOT_AS_AGREED":
        remedy, confidence = "SPLIT_50_50", 0.66
    else:
        remedy, confidence = "SPLIT_50_50", 0.62
    return {"remedy": remedy, "cited_evidence_ids": [e["id"] for e in data["evidence_catalog"]][:6],
            "rationale": RATIONALES[remedy], "confidence": confidence}


HANDLERS = {"intent": intent, "recommend": recommend, "evidence": evidence, "resolve": resolve}
