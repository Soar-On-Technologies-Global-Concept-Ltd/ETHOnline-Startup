"""When the two sides disagree. A complaint is not a verdict: both accounts are kept, compared with the agreed scope,
and no money moves until both parties sign or a person decides.
"""
import asyncio
import logging
import uuid
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.columns import utcnow
from app.core.config import get_settings
from app.core.db import session_scope, sessionmaker
from app.core.errors import Conflict, Forbidden, Gone, NotFound, Unprocessable
from app.core.hashing import complaint_hash
from app.core.money import split
from app.core.remedies import REMEDY_BPS, Remedy
from app.core.states import Event, TxState
from app.core.hashing import outcome_hash
from app.domains.authorization import service as authorization
from app.domains.disputes import ladder
from app.domains.disputes.models import Complaint, Dispute, ResolutionAcceptance, ResolutionProposal
from app.domains.evidence import service as evidence_service
from app.domains.identity import service as identity
from app.domains.intents import service as intents
from app.domains.payments import resolver
from app.domains.transactions import machine
from app.domains.transactions import policy as tx_policy
from app.integrations.arc import eip712

logger = logging.getLogger("disputes")
_running: set[uuid.UUID] = set()


# ---------------------------------------------------------------- reads other domains ask for

async def by_id(s: AsyncSession, dispute_id: uuid.UUID) -> Dispute:
    dispute = await s.get(Dispute, dispute_id)
    if dispute is None:
        raise NotFound("dispute not found")
    return dispute


async def for_transaction(s: AsyncSession, transaction_id: uuid.UUID) -> Dispute | None:
    return (await s.exec(select(Dispute).where(Dispute.transaction_id == transaction_id))).one_or_none()


async def view_for_transaction(s: AsyncSession, transaction_id: uuid.UUID) -> dict | None:
    dispute = await for_transaction(s, transaction_id)
    if dispute is None:
        return None
    return {"id": str(dispute.id), "status": dispute.status, "level": dispute.level,
            "response_deadline": dispute.response_deadline, "response_text": dispute.response_text}


async def proposal_for(s: AsyncSession, dispute_id: uuid.UUID) -> ResolutionProposal | None:
    return (await s.exec(select(ResolutionProposal).where(ResolutionProposal.dispute_id == dispute_id))).one_or_none()


async def complaint_hash_for(s: AsyncSession, transaction_id: uuid.UUID) -> str | None:
    row = (await s.exec(select(Complaint).where(Complaint.transaction_id == transaction_id)
                        .order_by(Complaint.created_at.desc()).limit(1))).first()
    return row.complaint_hash if row else None


async def mark_open(s: AsyncSession, transaction_id: uuid.UUID) -> None:
    """The escrow confirmed the freeze: the provider's clock starts now."""
    dispute = await for_transaction(s, transaction_id)
    if dispute is not None:
        dispute.status = "OPEN"
        dispute.response_deadline = utcnow() + timedelta(seconds=get_settings().response_window_seconds)
        dispute.updated_at = utcnow()
        s.add(dispute)


async def settlement_view(s: AsyncSession, transaction_id: uuid.UUID) -> dict | None:
    """What the watcher checks a Resolved event against."""
    dispute = await for_transaction(s, transaction_id)
    proposal = None if dispute is None else await proposal_for(s, dispute.id)
    if proposal is None:
        return None
    return {"proposal_id": str(proposal.id), "provider_bps": proposal.provider_bps,
            "to_provider_minor": proposal.to_provider_minor, "to_customer_minor": proposal.to_customer_minor,
            "outcome_hash": proposal.outcome_hash}


async def mark_settled(s: AsyncSession, transaction_id: uuid.UUID) -> None:
    dispute = await for_transaction(s, transaction_id)
    if dispute is None:
        return
    proposal = await proposal_for(s, dispute.id)
    if proposal is not None:
        proposal.status = "SETTLED"
        s.add(proposal)
    dispute.status, dispute.updated_at = "SETTLED", utcnow()
    s.add(dispute)


async def mark_too_late(s: AsyncSession, transaction_id: uuid.UUID) -> None:
    dispute = await for_transaction(s, transaction_id)
    if dispute is not None:
        dispute.status, dispute.updated_at = "TOO_LATE", utcnow()
        s.add(dispute)


# ---------------------------------------------------------------- the complaint

async def verify_complaint(tx, idkit_result: dict):
    return await identity.verify_human(idkit_result, action=get_settings().world_action_complaint, signal=tx.tx_key)


async def file_complaint(s: AsyncSession, tx, customer_id: uuid.UUID, category: str, text: str,
                         evidence_ids: list[uuid.UUID], human) -> tuple[int, dict]:
    """Selfie Check, at least one photo, and inside the window: then the resolver freezes the money on-chain."""
    settings = get_settings()
    if tx.release_after is not None and utcnow() >= tx.release_after - timedelta(seconds=settings.complaint_margin_seconds):
        raise Conflict("the dispute window has closed; the payment is already releasing", code="window_closed")
    items = {e.id: e for e in await evidence_service.rows(s, tx.id)}
    chosen = [items[i] for i in evidence_ids if i in items]
    if not chosen:
        raise Unprocessable("attach at least one photo of the problem", code="validation_error")
    await tx_policy.enforce(tx, f"customer:{customer_id}",
                            tx_policy.Action(kind="complaint", state=tx.state, currency=tx.currency,
                                             human_check_ok=human is not None),
                            tx_policy.context(tx, await authorization.view(s, tx.id)))
    check_id = await identity.record_human_check(s, user_id=customer_id, transaction_id=tx.id,
                                                 action=settings.world_action_complaint, verified=human,
                                                 scope_key=str(tx.id))
    digest = complaint_hash(tx.tx_key, category, text, [e.sha256 for e in chosen])
    complaint = Complaint(transaction_id=tx.id, filed_by=customer_id, category=category, text=text,
                          evidence_ids=[e.id for e in chosen], complaint_hash=digest, human_check_id=check_id)
    s.add(complaint)
    await s.flush()
    dispute = Dispute(transaction_id=tx.id, complaint_id=complaint.id, level="L1", status="OPENING")
    s.add(dispute)
    await s.flush()
    queued = await resolver.queue_open_dispute(s, tx.id, tx.tx_key, digest)
    await machine.note(s, tx, f"customer:{customer_id}", "HUMAN_CHECK_VERIFIED",
                       {"action": settings.world_action_complaint, "human_check_id": str(check_id)})
    await machine.note(s, tx, f"customer:{customer_id}", "TX_QUEUED",
                       {"kind": "OPEN_DISPUTE", "chain_tx_id": queued.id, "complaint_hash": digest,
                        "complaint_id": str(complaint.id), "dispute_id": str(dispute.id), "category": category})
    return 202, {"dispute": {"id": str(dispute.id), "status": "OPENING",
                             "response_deadline": utcnow() + timedelta(seconds=settings.response_window_seconds)},
                 "complaint": {"id": str(complaint.id), "complaint_hash": digest},
                 "transaction": {"id": str(tx.id), "state": tx.state}}


# ---------------------------------------------------------------- response, ladder, proposal

async def respond(s: AsyncSession, tx, dispute: Dispute, user_id: uuid.UUID, text: str) -> tuple[int, dict]:
    if tx.state != TxState.DISPUTED.value:
        raise machine.IllegalTransition(f"a response is not accepted while the job is {tx.state}", details={"state": tx.state})
    dispute.response_text, dispute.status, dispute.updated_at = text, "RESPONDED", utcnow()
    s.add(dispute)
    await machine.apply(s, tx, Event.RESPONSE_RECEIVED, f"provider:{user_id}",
                        {"dispute_id": str(dispute.id), "chars": len(text)})
    return 200, {"dispute": {"id": str(dispute.id), "status": "RESOLVING"},
                 "transaction": {"id": str(tx.id), "state": tx.state}}


async def _input(s: AsyncSession, tx, dispute: Dispute) -> ladder.LadderInput:
    complaint = await s.get(Complaint, dispute.complaint_id)
    quote = await intents.quote_view(s, tx.quote_id)
    scope = dict(quote["scope"]) if quote else {}
    items = await evidence_service.rows(s, tx.id)
    return ladder.LadderInput(amount_minor=int(tx.amount_minor or 0), scope=scope, checklist=list(scope.get("checklist", [])),
                              catalog=evidence_service.catalog(items),
                              complaint={"category": complaint.category, "text": complaint.text},
                              response=dispute.response_text, evidence_ids={str(e.id) for e in items})


async def run_ladder(dispute_id: uuid.UUID) -> None:
    """Called after a response or a timeout. The model call happens outside the database transaction."""
    if dispute_id in _running:
        return
    _running.add(dispute_id)
    try:
        async with sessionmaker()() as s:
            dispute = await s.get(Dispute, dispute_id)
            if dispute is None:
                return
            from app.domains.transactions import service as transactions
            tx = await transactions.get(s, dispute.transaction_id)
            if tx.state != TxState.RESOLVING.value or await proposal_for(s, dispute_id) is not None:
                return
            tx_id = tx.id
            data = await _input(s, tx, dispute)
        result = await ladder.decide(data)
        async with session_scope() as s:
            tx = await machine.lock(s, tx_id)
            dispute = await s.get(Dispute, dispute_id)
            if tx.state != TxState.RESOLVING.value or await proposal_for(s, dispute_id) is not None:
                return
            if result.escalated:
                dispute.status, dispute.level, dispute.updated_at = "ESCALATED", result.level, utcnow()
                s.add(dispute)
                await machine.apply(s, tx, Event.ESCALATION_REQUIRED, "system:ladder",
                                    {"level": result.level, "reason": result.escalate_reason, "coverage": result.coverage})
                log_escalation(dispute_id, result.escalate_reason)
                return
            proposal = _build(tx, dispute, result)
            s.add(proposal)
            dispute.status, dispute.level, dispute.updated_at = "PROPOSED", result.level, utcnow()
            s.add(dispute)
            await machine.apply(s, tx, Event.PROPOSAL_MADE, "system:ladder",
                                {"proposal_id": str(proposal.id), "level": result.level, "remedy": proposal.remedy,
                                 "provider_bps": proposal.provider_bps, "outcome_hash": proposal.outcome_hash,
                                 "confidence": str(result.confidence), "model": result.model})
    except Exception as err:
        logger.info("ladder failed", extra={"fields": {"dispute_id": str(dispute_id), "error": f"{type(err).__name__}: {err}"}})
    finally:
        _running.discard(dispute_id)


def log_escalation(dispute_id: uuid.UUID, reason: str | None) -> None:
    logger.info("dispute escalated", extra={"fields": {"dispute_id": str(dispute_id), "reason": reason}})


def _build(tx, dispute: Dispute, result: ladder.LadderResult) -> ResolutionProposal:
    """The split comes from REMEDY_BPS, never from the model."""
    proposal_id = uuid.uuid4()
    bps = REMEDY_BPS[Remedy(result.remedy)]
    to_provider, to_customer = split(int(tx.amount_minor or 0), bps)
    cited = [str(i) for i in result.cited_evidence_ids]
    digest = outcome_hash(tx.tx_key, str(proposal_id), str(result.remedy), bps, cited, result.rationale,
                          result.model, result.prompt_version)
    return ResolutionProposal(id=proposal_id, dispute_id=dispute.id, level=result.level, remedy=str(result.remedy),
                              provider_bps=bps, to_provider_minor=to_provider, to_customer_minor=to_customer,
                              rationale=result.rationale, cited_evidence_ids=[uuid.UUID(c) for c in cited],
                              model=result.model, prompt_version=result.prompt_version, input_hash=result.input_hash,
                              confidence=None if result.confidence is None else round(result.confidence, 2),
                              outcome_hash=digest,
                              accept_deadline=utcnow() + timedelta(seconds=get_settings().accept_window_seconds))


def schedule_ladder(dispute_id: uuid.UUID) -> None:
    """Runs after the response is committed; reconciliation retries if the process dies first."""
    asyncio.get_running_loop().create_task(run_ladder(dispute_id))


async def proposal_view(s: AsyncSession, tx, dispute: Dispute) -> dict:
    proposal = await proposal_for(s, dispute.id)
    if proposal is None:
        return {"status": dispute.status, "level": dispute.level, "state": tx.state,
                "message": "Intentra is reviewing both sides." if tx.state == TxState.RESOLVING.value else None}
    items = {e.id: e for e in await evidence_service.rows(s, tx.id)}
    cited = [{"id": str(i), "sha256": items[i].sha256, "caption": items[i].caption, "kind": items[i].kind}
             for i in proposal.cited_evidence_ids if i in items]
    acceptances = (await s.exec(select(ResolutionAcceptance)
                                .where(ResolutionAcceptance.proposal_id == proposal.id))).all()
    return {"proposal_id": str(proposal.id), "level": proposal.level, "remedy": proposal.remedy,
            "provider_bps": proposal.provider_bps,
            "split": {"to_provider_minor": proposal.to_provider_minor, "to_customer_minor": proposal.to_customer_minor,
                      "currency": tx.currency},
            "rationale": proposal.rationale, "cited_evidence": cited,
            "confidence": None if proposal.confidence is None else float(proposal.confidence),
            "outcome_hash": proposal.outcome_hash, "accept_deadline": proposal.accept_deadline, "status": proposal.status,
            "acceptances": [{"role": a.role, "decision": a.decision} for a in acceptances],
            "resolution_typed_data": eip712.for_client(
                eip712.resolution_typed_data(tx.tx_key, proposal.provider_bps, proposal.outcome_hash)),
            "model": proposal.model, "prompt_version": proposal.prompt_version}


# ---------------------------------------------------------------- acceptance and settlement

async def _record_decision(s: AsyncSession, proposal: ResolutionProposal, user_id: uuid.UUID, role: str, decision: str,
                           signature: str | None, typed_data: dict | None) -> ResolutionAcceptance:
    row = ResolutionAcceptance(proposal_id=proposal.id, user_id=user_id, role=role, decision=decision,
                               signature=signature, typed_data=typed_data)
    try:
        async with s.begin_nested():
            s.add(row)
            await s.flush()
    except IntegrityError as err:
        raise Conflict("you have already answered this proposal", code="already_answered") from err
    return row


async def accept(s: AsyncSession, tx, dispute: Dispute, proposal: ResolutionProposal, user_id: uuid.UUID, role: str,
                 signature: str) -> tuple[int, dict]:
    """Two signatures, checked here and again by the contract. The resolver only relays."""
    if proposal.status not in ("OPEN", "SETTLING"):
        raise Conflict(f"this proposal is {proposal.status.lower()}", code="proposal_closed")
    if proposal.accept_deadline <= utcnow():
        raise Gone("this proposal has expired", code="proposal_expired")
    typed = eip712.resolution_typed_data(tx.tx_key, proposal.provider_bps, proposal.outcome_hash)
    signer = eip712.recover(typed, signature)
    wallet = await identity.wallet_of(s, user_id)
    if wallet is None or signer != wallet.lower():
        raise Forbidden("that signature does not match your wallet", code="signature_mismatch")
    await _record_decision(s, proposal, user_id, role, "ACCEPT", signature, typed)
    rows = list((await s.exec(select(ResolutionAcceptance)
                              .where(ResolutionAcceptance.proposal_id == proposal.id))).all())
    accepted = {r.role: r for r in rows if r.decision == "ACCEPT"}
    await machine.note(s, tx, f"{role}:{user_id}", "RESOLUTION_ACCEPTED",
                       {"proposal_id": str(proposal.id), "role": role, "outcome_hash": proposal.outcome_hash})
    if not {"customer", "provider"} <= set(accepted):
        return 200, {"acceptances": sorted(accepted), "status": "AWAITING_OTHER_PARTY"}
    await tx_policy.enforce(tx, f"{role}:{user_id}",
                            tx_policy.Action(kind="settle", state=tx.state, currency=tx.currency,
                                             amount_minor=int(tx.amount_minor or 0)),
                            tx_policy.context(tx, await authorization.view(s, tx.id)))
    queued = await resolver.queue_resolve(s, tx.id, tx.tx_key, proposal.provider_bps, proposal.outcome_hash,
                                          accepted["customer"].signature, accepted["provider"].signature)
    proposal.status = "SETTLING"
    s.add(proposal)
    await machine.note(s, tx, f"{role}:{user_id}", "TX_QUEUED",
                       {"kind": "RESOLVE", "chain_tx_id": queued.id, "outcome_hash": proposal.outcome_hash})
    return 200, {"acceptances": sorted(accepted), "status": "SETTLING", "pending_tx": "RESOLVE"}


async def reject(s: AsyncSession, tx, dispute: Dispute, proposal: ResolutionProposal, user_id: uuid.UUID, role: str,
                 reason: str | None) -> tuple[int, dict]:
    if proposal.status == "SETTLING":
        raise Conflict("this proposal is already being settled", code="proposal_closed")
    await _record_decision(s, proposal, user_id, role, "REJECT", None, None)
    proposal.status = "REJECTED"
    dispute.status, dispute.updated_at = "ESCALATED", utcnow()
    s.add(proposal)
    s.add(dispute)
    await machine.note(s, tx, f"{role}:{user_id}", "PROPOSAL_REJECTED", {"proposal_id": str(proposal.id), "reason": reason})
    await machine.apply(s, tx, Event.REJECTED, f"{role}:{user_id}", {"proposal_id": str(proposal.id), "reason": reason})
    return 200, {"status": "ESCALATED", "transaction": {"id": str(tx.id), "state": tx.state}}


# ---------------------------------------------------------------- deadlines the reconciliation loop watches

async def due_responses(s: AsyncSession) -> list[tuple[uuid.UUID, uuid.UUID]]:
    from app.domains.transactions.models import Transaction

    return list((await s.exec(select(Dispute.id, Dispute.transaction_id)
                              .join(Transaction, Transaction.id == Dispute.transaction_id)
                              .where(Transaction.state == TxState.DISPUTED.value,
                                     Dispute.response_deadline.is_not(None),
                                     Dispute.response_deadline <= utcnow()))).all())


async def due_acceptances(s: AsyncSession) -> list[tuple[uuid.UUID, uuid.UUID, uuid.UUID]]:
    from app.domains.transactions.models import Transaction

    return list((await s.exec(select(ResolutionProposal.id, Dispute.id, Dispute.transaction_id)
                              .join(Dispute, Dispute.id == ResolutionProposal.dispute_id)
                              .join(Transaction, Transaction.id == Dispute.transaction_id)
                              .where(Transaction.state == TxState.PROPOSED.value,
                                     ResolutionProposal.status == "OPEN",
                                     ResolutionProposal.accept_deadline <= utcnow()))).all())


async def awaiting_ladder(s: AsyncSession) -> list[uuid.UUID]:
    """A crash between RESOLVING and the proposal would otherwise leave the dispute waiting forever."""
    from app.domains.transactions.models import Transaction

    rows = list((await s.exec(select(Dispute.id).join(Transaction, Transaction.id == Dispute.transaction_id)
                              .where(Transaction.state == TxState.RESOLVING.value))).all())
    return [d for d in rows if await proposal_for(s, d) is None]


async def opening_on_closed(s: AsyncSession) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """A complaint that lost the race with release: the on-chain call reverted."""
    from app.domains.transactions.models import Transaction

    return list((await s.exec(select(Dispute.id, Dispute.transaction_id)
                              .join(Transaction, Transaction.id == Dispute.transaction_id)
                              .where(Dispute.status == "OPENING",
                                     Transaction.state.in_([TxState.RELEASED.value, TxState.SETTLED.value])))).all())


async def mark_no_response(s: AsyncSession, dispute_id: uuid.UUID) -> None:
    dispute = await s.get(Dispute, dispute_id)
    if dispute is not None:
        dispute.status, dispute.updated_at = "NO_RESPONSE", utcnow()
        s.add(dispute)


async def expire_proposal(s: AsyncSession, proposal_id: uuid.UUID, dispute_id: uuid.UUID) -> None:
    proposal = await s.get(ResolutionProposal, proposal_id)
    dispute = await s.get(Dispute, dispute_id)
    if proposal is not None:
        proposal.status = "EXPIRED"
        s.add(proposal)
    if dispute is not None:
        dispute.status, dispute.updated_at = "ESCALATED", utcnow()
        s.add(dispute)
