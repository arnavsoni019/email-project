"""Phase 5 — the agent that proposes mailbox changes.

The agent never touches Gmail directly. It writes *proposals* into the ``actions``
table; a human approves or rejects them; only then does the executor act. That split is
the whole point of the phase, so it is enforced structurally: nothing in this package
imports a Gmail write API.
"""
