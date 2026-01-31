"""PostgreSQL setup helpers for RAG storage."""

from __future__ import annotations

import importlib
from typing import Any, Dict

from app.config import PostgresRagConfig



class PostgresRagSetup:
    """Validate and configure the PostgreSQL schema for RAG."""

    def __init__(self, config: PostgresRagConfig) -> None:
        self.config = config
        self.documents_table = config.table or "documents"
        self.embeddings_table = "embeddings"

    def configure(self) -> None:
        """Connect to PostgreSQL and ensure schema requirements."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_pgvector(cur)
                self._ensure_documents_table(cur, self.documents_table)
                self._ensure_embeddings_table(
                    cur,
                    self.embeddings_table,
                    self.documents_table,
                )
            conn.commit()

    def _connect(self) -> Any:
        pg_module, _ = self._load_psycopg()
        return pg_module.connect(
            host=self.config.host,
            port=self.config.port,
            dbname=self.config.database,
            user=self.config.user,
            password=self.config.password,
        )

    def _ensure_pgvector(self, cur: Any) -> None:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        if cur.fetchone() is None:
            raise RuntimeError("pgvector extension is not available in the database.")

    def _ensure_documents_table(
        self, cur: Any, table_name: str
    ) -> None:
        if not self._table_exists(cur, table_name):
            self._create_documents_table(cur, table_name)
            return

        columns = self._column_types(cur, table_name)
        required = {"path": "text", "topic": "text", "content": "text"}
        self._validate_columns(table_name, columns, required)

    def _ensure_embeddings_table(
        self,
        cur: Any,
        table_name: str,
        documents_table: str,
    ) -> None:
        if not self._table_exists(cur, table_name):
            self._create_embeddings_table(cur, table_name, documents_table)
            return

        columns = self._column_types(cur, table_name)
        required = {"document_id": "bigint", "embedding": "vector"}
        self._validate_columns(table_name, columns, required)

        if not self._has_foreign_key(cur, table_name, "document_id", documents_table):
            raise RuntimeError(
                f"Table '{table_name}' must have a foreign key from "
                f"'document_id' to '{documents_table}.id'."
            )

    def _table_exists(self, cur: Any, table_name: str) -> bool:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = %s
            )
            """,
            (table_name,),
        )
        return bool(cur.fetchone()[0])

    def _column_types(
        self, cur: Any, table_name: str
    ) -> Dict[str, str]:
        cur.execute(
            """
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            """,
            (table_name,),
        )

        columns: Dict[str, str] = {}
        for name, data_type, udt_name in cur.fetchall():
            if data_type == "USER-DEFINED":
                columns[name] = udt_name
            else:
                columns[name] = data_type
        return columns

    def _validate_columns(
        self,
        table_name: str,
        columns: Dict[str, str],
        required: Dict[str, str],
    ) -> None:
        missing = [name for name in required if name not in columns]
        if missing:
            raise RuntimeError(
                f"Table '{table_name}' is missing columns: {', '.join(missing)}."
            )

        mismatched = [
            name
            for name, expected in required.items()
            if columns.get(name) != expected
        ]
        if mismatched:
            details = ", ".join(
                f"{name} (expected {required[name]}, got {columns[name]})"
                for name in mismatched
            )
            raise RuntimeError(
                f"Table '{table_name}' has invalid column types: {details}."
            )

    def _has_foreign_key(
        self,
        cur: Any,
        table_name: str,
        column_name: str,
        target_table: str,
    ) -> bool:
        cur.execute(
            """
            SELECT 1
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = %s
              AND kcu.column_name = %s
              AND ccu.table_name = %s
              AND ccu.column_name = 'id'
            """,
            (table_name, column_name, target_table),
        )
        return cur.fetchone() is not None

    def _create_documents_table(
        self, cur: Any, table_name: str
    ) -> None:
        _, sql_module = self._load_psycopg()
        cur.execute(
            sql_module.SQL(
                """
                CREATE TABLE {table} (
                    id BIGSERIAL PRIMARY KEY,
                    path TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL
                )
                """
            ).format(table=sql_module.Identifier(table_name))
        )

    def _create_embeddings_table(
        self,
        cur: Any,
        table_name: str,
        documents_table: str,
    ) -> None:
        _, sql_module = self._load_psycopg()
        cur.execute(
            sql_module.SQL(
                """
                CREATE TABLE {table} (
                    id BIGSERIAL PRIMARY KEY,
                    document_id BIGINT NOT NULL REFERENCES {documents}(id) ON DELETE CASCADE,
                    embedding VECTOR
                )
                """
            ).format(
                table=sql_module.Identifier(table_name),
                documents=sql_module.Identifier(documents_table),
            )
        )

    def _load_psycopg(self):
        try:
            pg_module = importlib.import_module("psycopg")
            sql_module = importlib.import_module("psycopg.sql")
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "psycopg is required for PostgreSQL RAG setup. "
                "Install it with 'pip install psycopg[binary]'."
            ) from exc
        return pg_module, sql_module
