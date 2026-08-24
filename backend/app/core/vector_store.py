"""pgvector-backed embedding storage and similarity search, used for RAG.

The vector columns are added by an Alembic migration (production path), NOT
by the ORM models. This keeps pgvector a soft dependency: environments that
run ``alembic upgrade head`` get real vector search, while every other path
(tests using ``create_all``, or an operator who hasn't installed the
extension) transparently falls back to the calling service's keyword logic.

Every function here returns ``None``/empty when pgvector is unavailable so
callers can degrade without special-casing.
"""
from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.engine import Connection

# Embedding table names and their embedding column as created by the migration.
TICKET_EMBEDDINGS = "ticket_embeddings"
KB_EMBEDDINGS = "kb_article_embeddings"

# Maps table -> name of the foreign-key id column that points at the parent
# ticket/article row. Both tables share the same shape otherwise.
_TABLE_ID_COL = {TICKET_EMBEDDINGS: "ticket_id", KB_EMBEDDINGS: "article_id"}


def _vec_literal(embedding: list[float]) -> str:
    """Render an embedding as a safe inline pgvector literal (''[..]'')."""
    body = ",".join(repr(float(x)) for x in embedding)
    return f"'[{body}]'"


def _vector_usable(conn: Connection, table: str) -> bool:
    """True when pgvector is installed and the table has an embedding column."""
    try:
        row = conn.execute(
            text(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            )
        ).fetchone()
        if not row:
            return False
        col = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = 'embedding'"
            ),
            {"t": table},
        ).fetchone()
        return col is not None
    except Exception:
        return False


def embedding_column_exists(conn: Connection, table: str) -> bool:
    return _vector_usable(conn, table)


def upsert_embedding(
    conn: Connection,
    table: str,
    *,
    record_id: str,   # the ticket/article id (uuid)
    embedding: list[float],
    model: str,
    version: str = "1",
) -> bool:
    """Insert a fresh embedding row. Returns False if pgvector is missing.

    The embedding table keeps at most one current row per ticket/article; we
    delete any existing row for the same record first, then insert.
    ``id`` is a plain varchar here (no DB default), so we generate it here to
    stay independent of the environment's uuid extension.
    """
    id_col = _TABLE_ID_COL.get(table)
    if id_col is None:
        return False
    try:
        rid = str(uuid.uuid4())  # embedding row id (varchar)
        vec = _vec_literal(embedding)
        with conn.begin():
            # Remove any existing row for this record (uuid key column).
            conn.execute(
                text(
                    f"DELETE FROM {table} WHERE {id_col} = CAST(:rid AS uuid)"
                ),
                {"rid": record_id},
            )
            conn.execute(
                text(
                    f"INSERT INTO {table} (id, {id_col}, embedding, model, version, created_at) "
                    f"VALUES (:rid_new, CAST(:parent AS uuid), {vec}::vector, :model, :version, now())"
                ),
                {"rid_new": rid, "parent": record_id, "model": model, "version": version},
            )
        return True
    except Exception:
        return False


def search_by_embedding(
    conn: Connection,
    table: str,
    *,
    embedding: list[float],
    limit: int = 5,
) -> list[tuple[str, float]]:
    """Return ``[(record_id, cosine_similarity), ...]`` ordered best-first.

    Uses pgvector's ``<=>`` (cosine distance). Only called when the column
    exists; returns [] otherwise. The id column is derived from the table.
    """
    id_col = _TABLE_ID_COL.get(table)
    if id_col is None:
        return []
    if not _vector_usable(conn, table):
        return []
    vec = _vec_literal(embedding)
    rows = conn.execute(
        text(
            f"SELECT {id_col} AS rid, 1 - (embedding <=> {vec}) AS sim "
            f"FROM {table} ORDER BY embedding <-> {vec} LIMIT :limit"
        ),
        {"limit": limit},
    ).fetchall()
    return [(str(r.rid), float(r.sim)) for r in rows]
