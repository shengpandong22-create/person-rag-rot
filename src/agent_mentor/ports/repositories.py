from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from agent_mentor.domain.users import User


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...

    async def get_by_email(self, email: str) -> User | None: ...


class TransactionManager(Protocol):
    def transaction(self) -> AsyncIterator[None]: ...
