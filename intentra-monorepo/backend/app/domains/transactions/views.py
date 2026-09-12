"""One screen's worth of a transaction, gathered from every domain that owns part of it.

Domains do not read each other's tables, so the joining happens here, through their services. It lives beside the
aggregate root because that is what a transaction view is; nothing else imports it except the router.
"""
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.explanation import status_line
from app.domains.audit import service as audit
from app.domains.disputes import service as disputes
from app.domains.evidence import service as evidence
from app.domains.fulfillment import service as fulfillment
from app.domains.identity import service as identity
from app.domains.intents import service as intents
from app.domains.payments import service as payments
from app.domains.providers import service as providers
from app.domains.transactions import service as transactions


async def transaction(s: AsyncSession, tx, role: str) -> dict:
    """Everything the screen needs, and `allowed_actions` so the frontend never re-implements the state machine."""
    quote = await intents.quote_view(s, tx.quote_id)
    items = await evidence.rows(s, tx.id)
    return {
        "id": str(tx.id), "tx_key": tx.tx_key, "state": tx.state, "version": tx.version, "rail": tx.rail,
        "amount": transactions.amount_view(tx), "created_at": tx.created_at, "updated_at": tx.updated_at,
        "funded_at": tx.funded_at, "delivered_at": tx.delivered_at, "release_after": tx.release_after,
        "expires_at": tx.expires_at, "closed_at": tx.closed_at, "close_reason": tx.close_reason,
        "parties": {"customer": {"display_name": await identity.display_name_of(s, tx.customer_id)},
                    "provider": await providers.summary(s, tx.provider_id)},
        "scope": quote["scope"] if quote else None,
        "checklist": await fulfillment.view(s, tx.id, items),
        "evidence": await evidence.visible(items),
        "payments": await payments.payments_for(s, tx.id),
        "pending_tx": await payments.pending_for(s, tx.id),
        "dispute": await disputes.view_for_transaction(s, tx.id),
        "allowed_actions": transactions.allowed_actions(tx, role),
        "status_line": status_line(tx.state, role, tx.close_reason),
        "your_role": role,
    }


async def timeline(s: AsyncSession, tx) -> dict:
    """The audit trail with its hash chain recomputed, so a judge can check it in the room (FR-20)."""
    events = await audit.events_for(s, tx.id)
    return {"transaction_id": str(tx.id), "state": tx.state,
            "events": [{"seq": e.seq, "event": e.event, "from": e.from_state, "to": e.to_state, "actor": e.actor,
                        "payload": e.payload, "created_at": e.created_at, "hash": e.hash, "prev_hash": e.prev_hash}
                       for e in events],
            "verification": audit.verify_chain(events)}
