"""Retrieve RAG context filtered by workspace/project topics."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Iterable, List

from langchain_ollama import OllamaEmbeddings

from app.config import AppConfig
from app.context.project import Project
from app.context.workspace import Workspace


class ProjectContextRetriever:
    def __init__(self, config: AppConfig, model: str = "bge-m3") -> None:
        self.config = config
        pg = config.postgres_rag
        prefix = pg.table or ""
        self.documents_table = prefix + "documents"
        self.embeddings_table = prefix + "embeddings"
        self.embeddings = OllamaEmbeddings(model=model)

    def get_context(
        self,
        question: str,
        workspace: Workspace,
        project: Project,
        k: int = 5,
    ) -> str:
        topics = self._collect_topics(workspace, project)
        if not topics:
            return ""

        query_vector = self.embeddings.embed_query(question)
        vector_literal = self._vector_literal(query_vector)

        rows = self._search(vector_literal, topics, k)
        return "\n\n".join(content for content in rows)

    def get_active_context(self, question: str, k: int = 5) -> str:
        workspace, project = self._load_active_context()
        if workspace is None or project is None:
            return ""
        return self.get_context(question, workspace, project, k=k)

    def _collect_topics(self, workspace: Workspace, project: Project) -> List[str]:
        topics = []
        if workspace:
            topics.extend(workspace.topics)
        if project:
            topics.extend(project.topics)
        seen = set()
        unique = []
        for topic in topics:
            if topic and topic not in seen:
                seen.add(topic)
                unique.append(topic)
        return unique

    def _load_active_context(self) -> tuple[Workspace | None, Project | None]:
        sessions = self.config.sessions
        if not sessions:
            return None, None
        index = self.config.active_session_index
        if index < 0 or index >= len(sessions):
            return None, None
        session = sessions[index]
        ws_path = session.get("workspace") if isinstance(session, dict) else None
        prj_path = session.get("project") if isinstance(session, dict) else None
        if not ws_path or not prj_path:
            return None, None

        ws = None
        prj = None
        valid_topics = self.config.topic_names()
        ws_candidate = Path(ws_path)
        if ws_candidate.exists():
            ws = Workspace.load_or_create(ws_candidate, valid_topics=valid_topics)
        prj_candidate = Path(prj_path)
        if prj_candidate.exists():
            prj = Project.load_or_create(prj_candidate, valid_topics=valid_topics)
        return ws, prj

    def _search(self, vector_literal: str, topics: List[str], k: int) -> List[str]:
        pg_module, sql_module = self._load_psycopg()
        query = sql_module.SQL(
            """
            SELECT e.content
            FROM {embeddings} e
            JOIN {documents} d ON d.id = e.document_id
            WHERE d.topic = ANY(%s)
            ORDER BY e.embedding <-> %s::vector
            LIMIT %s
            """
        ).format(
            embeddings=sql_module.Identifier(self.embeddings_table),
            documents=sql_module.Identifier(self.documents_table),
        )

        with pg_module.connect(
            host=self.config.postgres_rag.host,
            port=self.config.postgres_rag.port,
            dbname=self.config.postgres_rag.database,
            user=self.config.postgres_rag.user,
            password=self.config.postgres_rag.password,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (topics, vector_literal, k))
                return [row[0] for row in cur.fetchall()]

    def _vector_literal(self, embedding: Iterable[float]) -> str:
        return "[" + ",".join(f"{value:.6f}" for value in embedding) + "]"

    def _load_psycopg(self):
        try:
            pg_module = importlib.import_module("psycopg")
            sql_module = importlib.import_module("psycopg.sql")
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "psycopg is required for PostgreSQL RAG retrieval. "
                "Install it with 'pip install psycopg[binary]'."
            ) from exc
        return pg_module, sql_module
