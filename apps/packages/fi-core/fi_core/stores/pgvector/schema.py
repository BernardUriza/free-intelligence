"""DDL for the pgvector store — parametrized twin of the ``_DDL_*``
module-constant convention ``fi_core.memory.stores.pgvector_memory``
already uses; parametrized because table names carry the consumer's
``table_prefix`` and the chunks table locks the embedding dimension.

Schema convention (per task spec): two tables, prefix-parameterized so
multiple stores can coexist in one database without colliding.

  - ``{prefix}_documents`` (document_id PK, namespace, content,
    status, created_at, indexed_at, attributes jsonb)
  - ``{prefix}_chunks`` (chunk_id PK, document_id FK, namespace, text,
    source_type, source_ref, embedding vector(N), created_at)

Index choice: IVFFlat with ``vector_cosine_ops`` and ``lists=100`` —
matches what the discord-bot deep-memory schema uses and is the
standard pgvector starting point for tables under ~1M rows. For larger
catalogs migrate to HNSW (``CREATE INDEX ... USING hnsw``) which is
more memory-hungry but offers better recall at scale.
"""

from __future__ import annotations

# pgvector cosine index. lists=100 is the standard starting point for tables
# under ~1M rows; consumers crossing that threshold should rebuild as HNSW.
_IVFFLAT_LISTS = 100


def schema_statements(
    *,
    table_prefix: str,
    docs_table: str,
    chunks_table: str,
    embedding_dim: int,
) -> list[str]:
    """The idempotent DDL batch ``init_schema()`` runs, in order.

    Every statement is ``IF NOT EXISTS`` so re-running against an
    initialized database is a no-op.
    """
    return [
        f"""
        CREATE TABLE IF NOT EXISTS {docs_table} (
            document_id     TEXT NOT NULL,
            namespace       TEXT NOT NULL,
            content         TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'pending',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            indexed_at      TIMESTAMPTZ,
            attributes      JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            PRIMARY KEY (namespace, document_id)
        )
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_{table_prefix}_docs_ns_status
            ON {docs_table} (namespace, status)
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {chunks_table} (
            chunk_id        TEXT NOT NULL,
            document_id     TEXT NOT NULL,
            namespace       TEXT NOT NULL,
            text            TEXT NOT NULL,
            source_type     TEXT NOT NULL,
            source_ref      TEXT NOT NULL,
            embedding       vector({embedding_dim}) NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (namespace, chunk_id),
            FOREIGN KEY (namespace, document_id)
                REFERENCES {docs_table} (namespace, document_id)
                ON DELETE CASCADE
        )
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_{table_prefix}_chunks_doc
            ON {chunks_table} (namespace, document_id)
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_{table_prefix}_chunks_embedding
            ON {chunks_table}
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = {_IVFFLAT_LISTS})
        """,
    ]
