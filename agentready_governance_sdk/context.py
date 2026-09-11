"""Multi-agent delegation and execution context management via contextvars."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

_CURRENT_EXECUTION_ID: ContextVar[str | None] = ContextVar(
    "agentready_execution_id", default=None
)
_CURRENT_AGENT_ID: ContextVar[str | None] = ContextVar(
    "agentready_agent_id", default=None
)
_CURRENT_DELEGATION_CHAIN: ContextVar[tuple[str, ...]] = ContextVar(
    "agentready_delegation_chain", default=()
)
_CURRENT_CLIENT: ContextVar[Any | None] = ContextVar("agentready_client", default=None)


def get_current_execution_id() -> str | None:
    """Return the active execution ID from context, if set."""
    return _CURRENT_EXECUTION_ID.get()


def get_current_agent_id() -> str | None:
    """Return the active agent ID from context, if set."""
    return _CURRENT_AGENT_ID.get()


def get_current_delegation_chain() -> list[str]:
    """Return the current delegation chain as a list of agent IDs."""
    return list(_CURRENT_DELEGATION_CHAIN.get())


def get_current_client() -> Any | None:
    """Return the active AgentReady client from context, if set."""
    return _CURRENT_CLIENT.get()


def set_current_execution(
    execution_id: str,
    agent_id: str,
    delegation_chain: list[str] | None = None,
    client: Any | None = None,
) -> tuple[
    Token[str | None],
    Token[str | None],
    Token[tuple[str, ...]],
    Token[Any | None] | None,
]:
    """Explicitly set execution context variables.

    Returns the tokens so they can be reset if needed.
    """
    token_exec = _CURRENT_EXECUTION_ID.set(execution_id)
    token_agent = _CURRENT_AGENT_ID.set(agent_id)

    if delegation_chain is not None:
        chain = list(delegation_chain)
    else:
        existing = list(_CURRENT_DELEGATION_CHAIN.get())
        chain = existing if existing else []
        if not chain or chain[-1] != agent_id:
            chain.append(agent_id)

    token_chain = _CURRENT_DELEGATION_CHAIN.set(tuple(chain))
    token_client = _CURRENT_CLIENT.set(client) if client is not None else None

    return token_exec, token_agent, token_chain, token_client


class agentready_execution:
    """Context manager for tracking execution ID and multi-agent delegation chains.

    Supports both sync (``with agentready_execution(...)``) and async
    (``async with agentready_execution(...)``) blocks.
    """

    def __init__(
        self,
        execution_id: str,
        agent_id: str,
        delegation_chain: list[str] | None = None,
        client: Any | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.agent_id = agent_id
        self.delegation_chain = delegation_chain
        self.client = client
        self._tokens: list[tuple[ContextVar[Any], Token[Any]]] = []

    def __enter__(self) -> agentready_execution:
        if self.delegation_chain is not None:
            chain = list(self.delegation_chain)
        else:
            existing = list(_CURRENT_DELEGATION_CHAIN.get())
            chain = existing if existing else []
            if not chain or chain[-1] != self.agent_id:
                chain.append(self.agent_id)

        self._tokens.append(
            (_CURRENT_EXECUTION_ID, _CURRENT_EXECUTION_ID.set(self.execution_id))
        )
        self._tokens.append((_CURRENT_AGENT_ID, _CURRENT_AGENT_ID.set(self.agent_id)))
        self._tokens.append(
            (_CURRENT_DELEGATION_CHAIN, _CURRENT_DELEGATION_CHAIN.set(tuple(chain)))
        )
        if self.client is not None:
            self._tokens.append((_CURRENT_CLIENT, _CURRENT_CLIENT.set(self.client)))
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        for var, token in reversed(self._tokens):
            var.reset(token)
        self._tokens.clear()

    async def __aenter__(self) -> agentready_execution:
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)
