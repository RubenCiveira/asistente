"""RAG configuration provider for the application config dialog.

Provides a four-page hierarchy for configuring PostgreSQL RAG connection
settings, global topic definitions, and per-workspace / per-project topic
selection.

Page hierarchy::

    RAG (PostgreSQL connection)
    └── Topics (global topic definitions as ``name:path``)
        ├── Workspace Topics (selection from known topics)
        └── Project Topics  (selection from known topics)
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.config import PostgresRagConfig, Topic
from app.ui.textual.app_config_dialog import ConfigProvider   
from app.ui.textual.widgets.config_dialog import ConfigPage, ConfigValues


def _topic_selection_schema(
    options: List[Dict[str, Any]], description: str
) -> Dict[str, Any]:
    """Build a JSON Schema for a topic selection array.

    When *options* is non-empty the items use ``oneOf`` so the dialog
    renders a :class:`~textual.widgets.SelectionList`.  When empty it
    falls back to a plain string array.
    """
    items: Dict[str, Any] = {"oneOf": options} if options else {"type": "string"}
    return {
        "type": "object",
        "properties": {
            "topics": {
                "type": "array",
                "items": items,
                "description": description,
            },
        },
    }


class RagConfigProvider(ConfigProvider):
    """Configuration provider for RAG database and topic settings.

    Args:
        window: The main application instance (provides access to
            ``config``, ``get_active_workspace()`` and
            ``get_active_project()``).
    """

    def __init__(self, window) -> None:
        self.window = window

    # ------------------------------------------------------------------
    # ConfigProvider interface
    # ------------------------------------------------------------------

    def config_page(self) -> ConfigPage:
        topic_names = [t.name for t in self.window.config.topics]
        topic_options = [{"const": n, "title": n} for n in topic_names]

        return ConfigPage(
            id="rag",
            title="RAG",
            schema={
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "Host"},
                    "port": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Port",
                    },
                    "database": {"type": "string", "description": "Database"},
                    "user": {"type": "string", "description": "User"},
                    "password": {"type": "string", "description": "Password"},
                    "table": {"type": "string", "description": "Table"},
                },
            },
            children=[
                ConfigPage(
                    id="topics",
                    title="Topics",
                    schema={
                        "type": "object",
                        "properties": {
                            "entries": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Name",
                                        },
                                        "path": {
                                            "type": "string",
                                            "format": "directory",
                                            "description": "Path",
                                        },
                                    },
                                    "required": ["name", "path"],
                                },
                                "uniqueItems": True,
                                "description": "Topics",
                            },
                        },
                    },
                    children=[
                        ConfigPage(
                            id="workspace_topics",
                            title="Workspace Topics",
                            schema=_topic_selection_schema(
                                topic_options,
                                "Topics for active workspace",
                            ),
                        ),
                        ConfigPage(
                            id="project_topics",
                            title="Project Topics",
                            schema=_topic_selection_schema(
                                topic_options,
                                "Topics for active project",
                            ),
                        ),
                    ],
                ),
            ],
        )

    def config_values(self) -> ConfigValues:
        pg = self.window.config.postgres_rag
        topics = self.window.config.topics
        ws = self.window.get_active_workspace()
        prj = self.window.get_active_project()

        return ConfigValues(
            values={
                "host": pg.host,
                "port": pg.port,
                "database": pg.database,
                "user": pg.user,
                "password": pg.password,
                "table": pg.table,
            },
            childs={
                "topics": ConfigValues(
                    values={
                        "entries": [
                            {"name": t.name, "path": t.path} for t in topics
                        ],
                    },
                    childs={
                        "workspace_topics": ConfigValues(
                            values={"topics": ws.topics if ws else []},
                        ),
                        "project_topics": ConfigValues(
                            values={"topics": prj.topics if prj else []},
                        ),
                    },
                ),
            },
        )

    def save_config(self, values: Dict[str, ConfigValues]) -> None:
        rag_cv = values.get("rag")
        if rag_cv is None:
            return

        # 1. Update PostgreSQL connection
        v = rag_cv.values
        self.window.config.postgres_rag = PostgresRagConfig(
            host=v.get("host", "localhost"),
            port=v.get("port", 5432),
            database=v.get("database", ""),
            user=v.get("user", ""),
            password=v.get("password", ""),
            table=v.get("table", ""),
        )

        # 2. Update global topic definitions
        topics_cv = rag_cv.childs.get("topics")
        if topics_cv:
            entries = topics_cv.values.get("entries", [])
            new_topics: List[Topic] = []
            for entry in entries:
                name = str(entry.get("name", "")).strip()
                path = str(entry.get("path", "")).strip()
                if name:
                    new_topics.append(Topic(name=name, path=path))
            self.window.config.topics = new_topics

            valid = self.window.config.topic_names()

            # 3. Update workspace topics
            ws = self.window.get_active_workspace()
            ws_cv = topics_cv.childs.get("workspace_topics")
            if ws and ws_cv:
                ws.topics = ws_cv.values.get("topics", [])
                ws.save(valid_topics=valid)

            # 4. Update project topics
            prj = self.window.get_active_project()
            prj_cv = topics_cv.childs.get("project_topics")
            if prj and prj_cv:
                prj.topics = prj_cv.values.get("topics", [])
                prj.save(valid_topics=valid)

        self.window.config.save()
