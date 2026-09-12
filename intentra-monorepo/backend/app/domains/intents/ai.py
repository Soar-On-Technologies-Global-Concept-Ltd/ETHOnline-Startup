"""FR-2: a sentence becomes an IntentSpec or one clarifying question. Code, not the model, converts units and checks the date."""
import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from app.core.money import naira_to_kobo
from app.integrations.llm.client import AIUnavailable, llm
from app.integrations.llm.schemas import IntentResult

LAGOS = ZoneInfo("Africa/Lagos")
SUPPORTED_SERVICES = ["painting"]
FALLBACK_QUESTION = "Tell me the job, the area, how many rooms, your budget in naira and the day you want it done."
MAX_DAYS_AHEAD = 90


@dataclass(frozen=True)
class ParsedIntent:
    spec: dict | None
    clarifying_question: str | None
    model: str | None
    prompt_version: str | None


def lagos_today() -> dt.date:
    return dt.datetime.now(LAGOS).date()


async def parse(text: str, today: dt.date | None = None) -> ParsedIntent:
    today = today or lagos_today()
    try:
        result = await llm().run("intent", {"text": text, "today": today.isoformat(), "services": SUPPORTED_SERVICES},
                                 IntentResult, max_tokens=2048)
    except AIUnavailable:
        return ParsedIntent(None, FALLBACK_QUESTION, None, None)
    out, model, version = result.output, result.model, result.prompt_version
    if out.spec is None:
        return ParsedIntent(None, out.clarifying_question, model, version)
    spec = out.spec
    if spec.date < today:
        return ParsedIntent(None, "That day has already passed. Which upcoming day works for you?", model, version)
    if spec.date > today + dt.timedelta(days=MAX_DAYS_AHEAD):
        return ParsedIntent(None, "Please choose a day within the next three months.", model, version)
    return ParsedIntent({"service": spec.service, "area": spec.area.strip(), "rooms": spec.rooms,
                         "budget_max_minor": naira_to_kobo(spec.budget_max_naira), "currency": "NGN",
                         "date": spec.date.isoformat(), "requirements": list(spec.requirements)}, None, model, version)
