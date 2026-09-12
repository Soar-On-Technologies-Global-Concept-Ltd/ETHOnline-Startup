"""Identity routes: start a session from a Privy token, and sign Selfie Check requests with the RP key."""
from fastapi import APIRouter, Depends

from app.core.db import session_scope
from app.domains.identity import service as identity_service
from app.domains.identity.deps import CurrentUser, PrivyIdentity, current_user, privy_identity
from app.domains.identity.schemas import RpSignatureIn, SessionIn
from app.domains.providers import service as providers

router = APIRouter(tags=["identity"])


@router.post("/auth/session", summary="Start or refresh a session")
async def session(body: SessionIn | None = None, identity: PrivyIdentity = Depends(privy_identity)) -> dict:
    """The wallet address comes from Privy's server API, never from the browser."""
    async with session_scope() as s:
        user = await identity_service.start_session(s, identity, body.display_name if body else None)
        provider = await providers.claim_for_user(s, user.id, user.email)
        return {"user": {"id": str(user.id), "role": user.role, "email": user.email, "display_name": user.display_name,
                         "wallet_address": user.wallet_address, "wallet_ready": user.wallet_address is not None},
                "provider": await providers.summary(s, provider.id) if provider else None}


@router.post("/world/rp-signature", summary="Sign a Selfie Check request")
async def rp_signature(body: RpSignatureIn, user: CurrentUser = Depends(current_user)) -> dict:
    return {"rp_context": identity_service.rp_context(body.action)}
