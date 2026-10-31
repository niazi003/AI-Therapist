"""Legacy memory service — DEPRECATED.

All memory management is now handled by the LangGraph multi-agent graph:
  - Short-term per-thread: LangGraph AsyncPostgresSaver (checkpointer)
  - Long-term cross-thread: LangGraph AsyncPostgresStore (graph_store.py)

This file is retained as a stub in case any external scripts still
reference it. No production code should import from here.
"""
