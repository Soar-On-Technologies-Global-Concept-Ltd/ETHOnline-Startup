"""FR-3 text only: the ranking is already decided in code (services/trust/ranking.py); the model writes why and trade-offs."""
from app.integrations.llm.client import AIUnavailable, llm
from app.core.explanation import rec_text
from app.integrations.llm.schemas import RecTexts


async def explain(request: dict, quotes: list[dict]) -> dict[str, dict]:
    """quotes: ranked [{quote_id, provider, price_minor, trust}] → {quote_id: {why, trade_offs}}; templates when the model is unavailable."""
    texts = {q["quote_id"]: rec_text(q, request) for q in quotes}
    if not quotes:
        return texts
    try:
        result = await llm().run("recommend", {"request": request, "quotes": quotes}, RecTexts, max_tokens=2048)
    except AIUnavailable:
        return texts
    for item in result.output.items:
        if str(item.quote_id) in texts:
            texts[str(item.quote_id)] = {"why": item.why, "trade_offs": item.trade_offs}
    return texts
