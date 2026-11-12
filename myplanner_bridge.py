import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DEFAULT_PLANNER_DB = os.getenv("PLANNER_DB", os.path.expanduser("~/ai-projects/myplanner/instance/planner.db"))

def is_myplanner_available(db_path: str = DEFAULT_PLANNER_DB) -> bool:
    """Check if a MyPlanner SQLite database exists at the target path."""
    return bool(db_path and os.path.exists(db_path))

def get_db_connection(db_path: str = DEFAULT_PLANNER_DB) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"MyPlanner database not found at: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_active_sprint(conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT id, name, status FROM sprint WHERE status = 'active' LIMIT 1")
    row = cur.fetchone()
    if row:
        return dict(row)
    return None

def get_category_by_name(conn: sqlite3.Connection, name: str) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT id, name, color, icon FROM category WHERE LOWER(name) LIKE ? LIMIT 1", (f"%{name.strip().lower()}%",))
    row = cur.fetchone()
    if row:
        return dict(row)
    return None

def create_task_in_myplanner(
    title: str,
    description: str = "",
    notes: str = "",
    priority: str = "P2 - Medium",
    category_id: Optional[int] = 5, # Default to 5 (Ideation)
    sprint_id: Optional[int] = None,
    story_id: Optional[int] = None,
    due_date: Optional[str] = None,
    db_path: str = DEFAULT_PLANNER_DB
) -> Dict[str, Any]:
    """
    Directly insert a task into MyPlanner's task table.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        if sprint_id is None:
            active_sprint = get_active_sprint(conn)
            if active_sprint:
                sprint_id = active_sprint["id"]

        cur.execute(
            """
            INSERT INTO task (
                title, description, notes, due_date, priority, status,
                category_id, story_id, sprint_id, created_at
            ) VALUES (?, ?, ?, ?, ?, 'To Do', ?, ?, ?, ?)
            """,
            (
                title.strip(),
                description.strip(),
                notes.strip(),
                due_date,
                priority,
                category_id,
                story_id,
                sprint_id,
                now_str
            )
        )
        task_id = cur.lastrowid
        conn.commit()

        return {
            "success": True,
            "task_id": task_id,
            "title": title.strip(),
            "category_id": category_id,
            "sprint_id": sprint_id,
            "priority": priority,
            "status": "To Do"
        }
    finally:
        conn.close()

def import_tasks_from_action_items(
    action_items: List[Dict[str, Any]],
    file_name: str,
    category_name: str = "Ideation",
    sprint_name: str = "active",
    db_path: str = DEFAULT_PLANNER_DB
) -> Dict[str, Any]:
    """
    Convert a list of action items into MyPlanner tasks.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        # Find category
        cat = get_category_by_name(conn, category_name)
        cat_id = cat["id"] if cat else 5 # Fallback to Ideation

        # Find sprint
        sprint_id = None
        if sprint_name.lower() == "active":
            act = get_active_sprint(conn)
            sprint_id = act["id"] if act else None
        elif sprint_name:
            cur.execute("SELECT id FROM sprint WHERE LOWER(name) LIKE ? LIMIT 1", (f"%{sprint_name.lower()}%",))
            row = cur.fetchone()
            if row:
                sprint_id = row["id"]

        created_tasks = []
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        for item in action_items:
            t_title = item.get("title", "").strip()
            if not t_title:
                continue
            t_desc = item.get("description", f"Imported from discussion file: {file_name}")
            t_prio = item.get("priority", "P2 - Medium")
            t_notes = f"Source Document: {file_name}\nImported via Downloads MCP Server on {now_str}\n\nTask Detail:\n{t_title}"

            cur.execute(
                """
                INSERT INTO task (
                    title, description, notes, priority, status,
                    category_id, sprint_id, created_at
                ) VALUES (?, ?, ?, ?, 'To Do', ?, ?, ?)
                """,
                (t_title, t_desc, t_notes, t_prio, cat_id, sprint_id, now_str)
            )
            t_id = cur.lastrowid
            created_tasks.append({
                "id": t_id,
                "title": t_title,
                "priority": t_prio,
                "category_id": cat_id,
                "sprint_id": sprint_id
            })

        conn.commit()
        return {
            "success": True,
            "count": len(created_tasks),
            "file_name": file_name,
            "created_tasks": created_tasks
        }
    finally:
        conn.close()
