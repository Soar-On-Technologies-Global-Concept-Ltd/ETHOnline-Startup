"""Seeds the demo: three painters with labelled history, so the first screen is not empty (FR-19).

    python scripts/seed.py [--reset]

Seeded rows are marked `seeded = true` everywhere and the trust card reports them separately from on-chain history.
"""
import argparse
import asyncio
import datetime as dt
import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlmodel import delete, select  # noqa: E402

from app.core.db import dispose_engine, session_scope  # noqa: E402
from app.core.money import kobo_to_micro_usdc  # noqa: E402
from app.core.states import TxState  # noqa: E402
from app.core.columns import utcnow  # noqa: E402
from app.domains.identity.models import User  # noqa: E402
from app.domains.intents.models import Intent  # noqa: E402
from app.domains.providers.models import Provider  # noqa: E402
from app.domains.transactions.models import Transaction  # noqa: E402

RATE = 1650
PROVIDERS = [
    {"email": "tunde@intentra.demo", "display_name": "Tunde's Painting", "trade": "painting",
     "areas": ["Surulere", "Yaba", "Ikeja"], "base_rate_minor": 8_250_000, "verified": True,
     "history": {"released": 13, "settled": 1, "refunded": 0}},
    {"email": "chinedu@intentra.demo", "display_name": "Chinedu Painting Services", "trade": "painting",
     "areas": ["Surulere", "Lekki", "Ajah"], "base_rate_minor": 8_700_000, "verified": True,
     "history": {"released": 9, "settled": 2, "refunded": 1}},
    {"email": "bisi@intentra.demo", "display_name": "Bisi Finishes", "trade": "painting",
     "areas": ["Surulere", "Yaba"], "base_rate_minor": 8_000_000, "verified": True,
     "history": {"released": 1, "settled": 0, "refunded": 0}},
]
HISTORY_CUSTOMER = "history@intentra.demo"


def tx_key(seed: str) -> str:
    return "0x" + hashlib.sha256(seed.encode()).hexdigest()


async def upsert_user(s, email: str, role: str, display_name: str) -> User:
    user = (await s.exec(select(User).where(User.email == email))).one_or_none()
    if user is None:
        user = User(privy_did=f"seed:{email}", email=email, role=role, display_name=display_name)
        s.add(user)
        await s.flush()
    return user


async def seed(reset: bool) -> None:
    async with session_scope() as s:
        if reset:
            seeded = list((await s.exec(select(Transaction.id, Transaction.intent_id).where(Transaction.seeded.is_(True)))).all())
            for tx_id, intent_id in seeded:
                await s.exec(delete(Transaction).where(Transaction.id == tx_id))
                await s.exec(delete(Intent).where(Intent.id == intent_id))
            print(f"removed {len(seeded)} seeded transactions")

        customer = await upsert_user(s, HISTORY_CUSTOMER, "customer", "Past customers")
        for spec in PROVIDERS:
            user = await upsert_user(s, spec["email"], "provider", spec["display_name"])
            provider = (await s.exec(select(Provider).where(Provider.email == spec["email"]))).one_or_none()
            if provider is None:
                provider = Provider(email=spec["email"], display_name=spec["display_name"], trade=spec["trade"],
                                    areas=spec["areas"], base_rate_minor=spec["base_rate_minor"], currency="NGN",
                                    verified=spec["verified"], available_dates=[], seeded=True, user_id=user.id)
                s.add(provider)
                await s.flush()
            else:
                provider.areas, provider.base_rate_minor, provider.verified = spec["areas"], spec["base_rate_minor"], spec["verified"]
                provider.user_id = provider.user_id or user.id
                s.add(provider)

            existing = len(list((await s.exec(select(Transaction.id).where(Transaction.provider_id == provider.id,
                                                                          Transaction.seeded.is_(True)))).all()))
            wanted = [(TxState.RELEASED, spec["history"]["released"]), (TxState.SETTLED, spec["history"]["settled"]),
                      (TxState.CANCELLED, spec["history"]["refunded"])]
            made = 0
            for state, count in wanted:
                for i in range(count):
                    seed_id = f"{spec['email']}:{state.value}:{i}"
                    key = tx_key(seed_id)
                    if (await s.exec(select(Transaction).where(Transaction.tx_key == key))).one_or_none() is not None:
                        continue
                    amount_kobo = spec["base_rate_minor"] * 2
                    when = utcnow() - dt.timedelta(days=7 * (i + 1))
                    intent = Intent(customer_id=customer.id, raw_text=f"Paint a 2-bedroom (seeded history {i + 1})",
                                    structured={"service": "painting", "area": spec["areas"][0], "rooms": 2,
                                                "budget_max_minor": amount_kobo, "currency": "NGN",
                                                "date": (when.date()).isoformat(), "requirements": []},
                                    status="STRUCTURED", created_at=when)
                    s.add(intent)
                    await s.flush()
                    s.add(Transaction(tx_key=key, intent_id=intent.id, customer_id=customer.id, provider_id=provider.id,
                                      state=state.value, version=6, amount_minor=kobo_to_micro_usdc(amount_kobo, RATE),
                                      display_amount_minor=amount_kobo, fx_rate_ngn_per_usdc=RATE, currency="USDC",
                                      seeded=True, created_at=when, updated_at=when, closed_at=when,
                                      close_reason="refunded" if state is TxState.CANCELLED else None))
                    made += 1
            print(f"{spec['display_name']:<28} {existing + made:>3} seeded jobs  ({made} new)")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="delete existing seeded transactions first")
    args = parser.parse_args()
    await seed(args.reset)
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
