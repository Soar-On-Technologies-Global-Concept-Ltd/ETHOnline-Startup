"""Who may see or act on a transaction. Non-parties are told it does not exist."""
import uuid

from app.core.errors import Forbidden, NotFound
from app.core.logging import transaction_id_var
from app.domains.identity.deps import CurrentUser
from app.domains.transactions.models import Transaction


def party_role(user: CurrentUser, tx: Transaction) -> str:
    if tx.customer_id == user.id:
        return "customer"
    if user.provider_id is not None and tx.provider_id == user.provider_id:
        return "provider"
    if user.role == "operator":
        return "operator"
    raise Forbidden("you are not a party to this transaction")


def require(role: str, actual: str) -> None:
    if actual != role:
        raise Forbidden(f"only the {role} can do this", code="wrong_role")


async def load_transaction(s, tx_id: uuid.UUID, user: CurrentUser) -> tuple[Transaction, str]:
    """Non-parties get 404, not 403: they should not learn that the transaction exists."""
    tx = await s.get(Transaction, tx_id)
    if tx is None:
        raise NotFound("transaction not found")
    try:
        role = party_role(user, tx)
    except Forbidden as err:
        raise NotFound("transaction not found") from err
    transaction_id_var.set(str(tx.id))
    return tx, role
