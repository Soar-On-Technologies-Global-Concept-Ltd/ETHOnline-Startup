"""Advisory coverage notes per checklist item: context for L2, never a decision."""
from app.integrations.llm.client import AIUnavailable, llm
from app.integrations.llm.schemas import CoverageNotes


def tagged_coverage(checklist: list[str], catalog: list[dict]) -> dict[str, str]:
    covered = {e["scope_item"] for e in catalog if e["kind"] == "AFTER_PHOTO" and e.get("scope_item")}
    return {item: ("covered" if item in covered else "missing") for item in checklist}


async def coverage_notes(checklist: list[str], catalog: list[dict]) -> dict[str, str]:
    try:
        result = await llm().run("evidence", {"checklist": checklist, "evidence": catalog}, CoverageNotes, max_tokens=2048)
    except AIUnavailable:
        return tagged_coverage(checklist, catalog)
    notes = {n.scope_item: n.status for n in result.output.items}
    return {item: notes.get(item, "unclear") for item in checklist}
