"""Phase 4 — semantic search and grounded Q&A over the local mail store.

SQLite remains the system of record. Everything here is a *derived* index that can be
deleted and rebuilt from it, so a bad chunking or embedding decision is never
destructive.
"""
