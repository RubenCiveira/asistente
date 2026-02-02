"""Ingest topic documents into PostgreSQL RAG tables."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Iterable, List

from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import AppConfig
from app.context.progress import ProgressMonitor
from app.rag.content_extractor import RagContentExtractor


class RagIngest:
    def __init__(self, app_conf: AppConfig, model: str = "bge-m3", base_url: str = "http://localhost:11434") -> None:
        self.config = app_conf
        self.pg = app_conf.postgres_rag
        prefix = self.pg.table or ""
        self.documents_table = prefix + "documents"
        self.embeddings_table = prefix + "embeddings"
        self.embeddings = OllamaEmbeddings(model=model, base_url=base_url)
        self.extractor = RagContentExtractor()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=900,
            chunk_overlap=150,
        )

    def ingest(self, monitor: ProgressMonitor) -> int:
        files = self._collect_files()
        monitor.set_title("RAG ingest")
        monitor.set_total_pending(len(files))
        created = 0

        for topic_name, topic_path, file_path in files:
            relative_path = file_path.relative_to(topic_path).as_posix()
            monitor.set_message(f"{topic_name}: {relative_path}")
            conn = None
            try:
                conn = self._connect()
                with conn:
                    with conn.cursor() as cur:
                        if self._document_exists(cur, topic_name, relative_path):
                            continue
                        content = self._read_text(file_path)
                        if not content.strip():
                            continue
                        if not self._is_text_like(content):
                            continue
                        document_id = self._insert_document(
                            cur,
                            topic_name,
                            relative_path,
                            content,
                        )
                        chunks = self._split_text(content)
                        if chunks:
                            embeddings = self.embeddings.embed_documents(chunks)
                            for chunk_text, embedding in zip(chunks, embeddings):
                                self._insert_embedding(
                                    cur,
                                    document_id,
                                    chunk_text,
                                    embedding,
                                )
                        created += 1
                        conn.commit()
            except Exception as exc:
                monitor.add_error(f"{topic_name}: {relative_path}: {exc}")
                if conn is not None:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
            finally:
                monitor.advance(1)

        monitor.finish()
        return created

    def _collect_files(self) -> list[tuple[str, Path, Path]]:
        files: list[tuple[str, Path, Path]] = []
        for topic in self.config.topics:
            if not topic.path:
                continue
            topic_path = Path(topic.path).expanduser()
            if not topic_path.exists():
                continue
            for file_path in self._iter_files(topic_path):
                files.append((topic.name, topic_path, file_path))
        return files

    def _connect(self) -> Any:
        pg_module, _ = self._load_psycopg()
        return pg_module.connect(
            host=self.pg.host,
            port=self.pg.port,
            dbname=self.pg.database,
            user=self.pg.user,
            password=self.pg.password,
        )

    def _iter_files(self, root: Path) -> Iterable[Path]:
        for path in root.rglob("*"):
            if path.is_file():
                yield path

    def _read_text(self, path: Path) -> str:
        try:
            extracted = self.extractor.extract(path)
            if extracted:
                return extracted
            if not self._is_probably_text_file(path):
                return ""
            return path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeError) as exc:
            raise RuntimeError(f"Failed to read {path}") from exc

    def _is_probably_text_file(self, path: Path) -> bool:
        try:
            with path.open("rb") as handle:
                chunk = handle.read(2048)
        except OSError:
            return False

        if not chunk:
            return False

        if b"\x00" in chunk:
            return False

        non_text = 0
        for byte in chunk:
            if byte in (9, 10, 13):
                continue
            if 32 <= byte <= 126:
                continue
            non_text += 1

        return (non_text / len(chunk)) < 0.3

    def _is_text_like(self, content: str) -> bool:
        sample = content[:4000]
        if "\x00" in sample:
            return False

        printable = 0
        meaningful = 0
        for ch in sample:
            if ch.isprintable() or ch in "\n\r\t":
                printable += 1
            if ch.isalnum():
                meaningful += 1

        if not sample:
            return False

        printable_ratio = printable / len(sample)
        meaningful_ratio = meaningful / len(sample)
        return printable_ratio >= 0.95 and meaningful_ratio >= 0.2

    def _split_text(self, content: str) -> list[str]:
        return self.splitter.split_text(content)

    def _document_exists(self, cur: Any, topic: str, path: str) -> bool:
        _, sql_module = self._load_psycopg()
        cur.execute(
            sql_module.SQL(
                "SELECT 1 FROM {} WHERE topic = %s AND path = %s"
            ).format(sql_module.Identifier(self.documents_table)),
            (topic, path),
        )
        return cur.fetchone() is not None

    def _insert_document(
        self,
        cur: Any,
        topic: str,
        path: str,
        content: str,
    ) -> int:
        _, sql_module = self._load_psycopg()
        if topic is None:
            raise RuntimeError("No topic")
        if path is None:
            raise RuntimeError("No path on " + topic)
        if content is None:
            raise RuntimeError("No content for " + path + " on " + topic)
        cur.execute(
            sql_module.SQL(
                "INSERT INTO {} (path, topic, content) VALUES (%s, %s, %s) RETURNING id"
            ).format(sql_module.Identifier(self.documents_table)),
            (path, topic, content),
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to insert document row.")
        return int(row[0])

    def _insert_embedding(
        self,
        cur: Any,
        document_id: int,
        content: str,
        embedding: List[float],
    ) -> None:
        _, sql_module = self._load_psycopg()
        vector_literal = self._vector_literal(embedding)
        cur.execute(
            sql_module.SQL(
                "INSERT INTO {} (document_id, content, embedding) VALUES (%s, %s, %s::vector)"
            ).format(sql_module.Identifier(self.embeddings_table)),
            (document_id, content, vector_literal),
        )

    def _vector_literal(self, embedding: List[float]) -> str:
        return "[" + ",".join(f"{value:.6f}" for value in embedding) + "]"

    def _load_psycopg(self):
        try:
            pg_module = importlib.import_module("psycopg")
            sql_module = importlib.import_module("psycopg.sql")
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "psycopg is required for PostgreSQL RAG ingestion. "
                "Install it with 'pip install psycopg[binary]'."
            ) from exc
        return pg_module, sql_module
