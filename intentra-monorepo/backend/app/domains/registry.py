"""Importing this module registers every table on SQLModel.metadata.

Domains own their own tables, so nothing imports them all except Alembic, `create_all` in tests, and this file.
Add a line here when a new domain gets its first table.
"""
from app.core import models as _platform  # noqa: F401
from app.domains.audit import models as _audit  # noqa: F401
from app.domains.authorization import models as _authorization  # noqa: F401
from app.domains.disputes import models as _disputes  # noqa: F401
from app.domains.evidence import models as _evidence  # noqa: F401
from app.domains.fulfillment import models as _fulfillment  # noqa: F401
from app.domains.identity import models as _identity  # noqa: F401
from app.domains.intents import models as _intents  # noqa: F401
from app.domains.payments import models as _payments  # noqa: F401
from app.domains.providers import models as _providers  # noqa: F401
from app.domains.transactions import models as _transactions  # noqa: F401

__all__ = ["metadata"]

from sqlmodel import SQLModel  # noqa: E402

metadata = SQLModel.metadata
