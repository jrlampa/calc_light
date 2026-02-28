import sqlite3

from app.domain.models import NodeSpanConfig, Project, ProjectNode


class ProjectRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_project(self, project: Project) -> Project:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO projects (name) VALUES (?)", (project.name,))
            project.id = cursor.lastrowid
            conn.commit()
            return project

    def get_projects(self) -> list[Project]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [Project(**dict(row)) for row in rows]

    def get_project(self, project_id: int) -> Project | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            return Project(**dict(row)) if row else None

    # --- Project Nodes ---
    def add_node(self, node: ProjectNode) -> ProjectNode:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO project_nodes (project_id, pole_id, label, pos_x, pos_y, effort_dan)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (node.project_id, node.pole_id, node.label, node.pos_x, node.pos_y, node.effort_dan))
            node.id = cursor.lastrowid
            conn.commit()
            return node

    def get_project_nodes(self, project_id: int) -> list[ProjectNode]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM project_nodes WHERE project_id = ?", (project_id,))
            rows = cursor.fetchall()
            return [ProjectNode(**dict(row)) for row in rows]

    def update_node_effort(self, node_id: int, effort_dan: float):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE project_nodes SET effort_dan = ? WHERE id = ?", (effort_dan, node_id))
            conn.commit()

    def update_node_position(self, node_id: int, pos_x: float, pos_y: float) -> ProjectNode | None:
        """Persiste a posição XY após drag-and-drop no React Flow."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE project_nodes SET pos_x = ?, pos_y = ? WHERE id = ?",
                (pos_x, pos_y, node_id)
            )
            conn.commit()
            cursor.execute("SELECT * FROM project_nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()
            return ProjectNode(**dict(row)) if row else None


    # --- Node Span Configs (Edges) ---
    def add_span_config(self, span: NodeSpanConfig) -> NodeSpanConfig:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO node_span_configs
                (source_node_id, target_node_id, mt_conductor_id, mt_sag_m, bt_conductor_id, bt_sag_m, span_length_m, angle_deg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (span.source_node_id, span.target_node_id, span.mt_conductor_id, span.mt_sag_m,
                  span.bt_conductor_id, span.bt_sag_m, span.span_length_m, span.angle_deg))
            span.id = cursor.lastrowid
            conn.commit()
            return span

    def get_span_configs_for_project(self, project_id: int) -> list[NodeSpanConfig]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Join with project_nodes to ensure they belong to the project
            cursor.execute("""
                SELECT s.* FROM node_span_configs s
                JOIN project_nodes n ON s.source_node_id = n.id
                WHERE n.project_id = ?
            """, (project_id,))
            rows = cursor.fetchall()
            return [NodeSpanConfig(**dict(row)) for row in rows]
