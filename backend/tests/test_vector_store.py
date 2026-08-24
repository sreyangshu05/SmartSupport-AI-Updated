"""Regression tests for the pgvector embedding store (RAG path).

These apply the real pgvector migration code to the isolated test schema so
the semantic-search path is exercised, not just the keyword fallback. They
skip cleanly if pgvector isn't installed in the test PostgreSQL.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.core import vector_store
from app.models.ticket import Ticket
from app.models.enums import TicketStatus, TicketPriority, SLABreachStatus


def _apply_pgvector_migration(engine):
    """Mirror migrations/versions/add_pgvector_embeddings.py upgrade()."""
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(
            text("ALTER TABLE ticket_embeddings ADD COLUMN embedding vector(1536)")
        )
        conn.execute(
            text("ALTER TABLE kb_article_embeddings ADD COLUMN embedding vector(1536)")
        )


def _emb(seed: int) -> list[float]:
    """Deterministic pseudo-random 1536-dim vector."""
    import random
    rng = random.Random(seed)
    return [rng.random() for _ in range(1536)]


def test_vector_upsert_and_cosine_search(test_engine, db_session):
    _apply_pgvector_migration(test_engine)

    # Create real tickets whose embeddings star this test could hang on.
    a = Ticket(ticket_number="V-1", subject="password reset email not arriving",
               description="user cannot reset password via email", status=TicketStatus.OPEN,
               priority=TicketPriority.MEDIUM, sla_status=SLABreachStatus.GREEN,
               created_by_email="cust@example.com")
    b = Ticket(ticket_number="V-2", subject="cannot reset my account password",
               description="reset link not received", status=TicketStatus.OPEN,
               priority=TicketPriority.MEDIUM, sla_status=SLABreachStatus.GREEN,
               created_by_email="cust@example.com")
    c = Ticket(ticket_number="V-3", subject="invoice billing amount wrong",
               description="charged incorrect amount on monthly invoice", status=TicketStatus.OPEN,
               priority=TicketPriority.LOW, sla_status=SLABreachStatus.GREEN,
               created_by_email="cust@example.com")
    db_session.add_all([a, b, c])
    db_session.commit()

    va, vb, vc = _emb(1), _emb(1), _emb(999)  # a and b similarly-ish structured, c dissimilar

    with test_engine.connect() as conn:
        assert vector_store.upsert_embedding(conn, vector_store.TICKET_EMBEDDINGS,
                                             record_id=str(a.id), embedding=va, model="test")
        assert vector_store.upsert_embedding(conn, vector_store.TICKET_EMBEDDINGS,
                                             record_id=str(b.id), embedding=vb, model="test")
        assert vector_store.upsert_embedding(conn, vector_store.TICKET_EMBEDDINGS,
                                             record_id=str(c.id), embedding=vc, model="test")

    # Re-upsert one row to prove dedupe keeps exactly one row per record.
    with test_engine.connect() as conn:
        assert vector_store.upsert_embedding(conn, vector_store.TICKET_EMBEDDINGS,
                                             record_id=str(a.id), embedding=va, model="test")
        count = conn.execute(text("SELECT count(*) FROM ticket_embeddings")).scalar()
        assert count == 3

    # Cosine search from a's embedding: a and b (identical emb) rank first (~1.0),
    # c (dissimilar) is lower.
    with test_engine.connect() as conn:
        hits = vector_store.search_by_embedding(
            conn, vector_store.TICKET_EMBEDDINGS, embedding=va, limit=5
        )
    scored = {rid: sim for rid, sim in hits}
    assert str(a.id) in scored and str(b.id) in scored
    assert scored[str(a.id)] > 0.99
    assert scored[str(b.id)] > 0.99
    assert scored[str(a.id)] > scored[str(c.id)]


def test_vector_store_degrades_without_pgvector(test_engine, db_session):
    """Without the vector column, the store returns empty/False, never raises."""
    # The default conftest schema has no embedding column, so this is the real
    # degraded state: upsert should be a no-op False and search returns [].
    with test_engine.connect() as conn:
        assert not vector_store.embedding_column_exists(conn, vector_store.TICKET_EMBEDDINGS)
        assert vector_store.upsert_embedding(conn, vector_store.TICKET_EMBEDDINGS,
                                             record_id="anything", embedding=_emb(1), model="test") is False
        assert vector_store.search_by_embedding(conn, vector_store.TICKET_EMBEDDINGS,
                                                embedding=_emb(1)) == []
