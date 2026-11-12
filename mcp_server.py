"""
BrainstormBridge: Secure Context Bridge for AI Coding Agents.
Brings AI chatbot brainstorming exports (ChatGPT, Claude, DeepSeek) into coding harnesses
(Claude Code, Antigravity, Cursor, Copilot) with full Prompt Injection Defense.
"""

import os
import glob
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from mcp.server.mcpserver import MCPServer

from parsers.docx_parser import parse_docx
from parsers.pdf_parser import parse_pdf
from parsers.text_parser import parse_text_or_json
from parsers.extractor import extract_discussion_structure
from sanitizer import sanitize_text, wrap_sandboxed_content
from task_exporter import export_tasks_to_markdown, export_tasks_to_json
from myplanner_bridge import (
    import_tasks_from_action_items,
    is_myplanner_available,
    DEFAULT_PLANNER_DB
)
from classifier import classify_file

# Initialize MCPServer as brainstorm-bridge
mcp = MCPServer("brainstorm-bridge")

# Safe Quarantined Inbox Directory (NEVER defaults to raw system Downloads)
BRAINSTORM_INBOX_DIR = os.getenv("BRAINSTORM_INBOX_DIR", os.path.expanduser("~/.brainstorm-inbox"))
SUPPORTED_EXTENSIONS = {".docx", ".md", ".txt", ".pdf", ".json"}

def _ensure_inbox_exists():
    """Ensure the safe quarantined inbox directory exists."""
    try:
        os.makedirs(BRAINSTORM_INBOX_DIR, exist_ok=True)
    except Exception:
        pass

def _resolve_file_path(file_name_or_path: str) -> str:
    """
    Resolve file path securely:
    1. Direct absolute or relative path if provided and exists.
    2. Quarantined inbox directory (~/.brainstorm-inbox/).
    """
    # 1. Direct path check
    if os.path.isabs(file_name_or_path) and os.path.exists(file_name_or_path):
        return file_name_or_path
    
    local_rel = os.path.abspath(file_name_or_path)
    if os.path.exists(local_rel):
        return local_rel

    # 2. Check quarantined inbox directory
    candidate = os.path.join(BRAINSTORM_INBOX_DIR, file_name_or_path)
    if os.path.exists(candidate):
        return candidate

    # Search case-insensitively inside the inbox directory only
    target_lower = file_name_or_path.lower()
    if os.path.exists(BRAINSTORM_INBOX_DIR):
        for root, dirs, files in os.walk(BRAINSTORM_INBOX_DIR):
            for fname in files:
                if fname.lower() == target_lower:
                    return os.path.join(root, fname)

    raise FileNotFoundError(
        f"File '{file_name_or_path}' not found at explicit path or in safe inbox '{BRAINSTORM_INBOX_DIR}'."
    )

def _parse_file(file_path: str) -> str:
    """Dispatch file parsing to appropriate format parser."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".docx":
        return parse_docx(file_path)
    elif ext == ".pdf":
        return parse_pdf(file_path)
    elif ext in (".md", ".txt", ".json"):
        return parse_text_or_json(file_path)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}")


@mcp.tool()
def list_inbox_brainstorms(
    limit: int = 15,
    file_type: str = ""
) -> dict:
    """
    List discussion exports, specs, and roadmaps in the safe quarantined inbox (~/.brainstorm-inbox).
    Files placed here are protected and reviewed before ingestion into the coding harness.

    Args:
        limit: Maximum number of files to return (default 15).
        file_type: Optional extension filter (e.g. 'docx', 'md', 'pdf', 'json', 'txt').

    Returns:
        Dictionary with list of available files, metadata, categories, and preview snippets.
    """
    _ensure_inbox_exists()
    if not os.path.exists(BRAINSTORM_INBOX_DIR):
        return {"error": f"Inbox directory not found at: {BRAINSTORM_INBOX_DIR}"}

    filter_ext = f".{file_type.lower().lstrip('.')}" if file_type else ""
    files_found = []

    try:
        entries = os.scandir(BRAINSTORM_INBOX_DIR)
        for entry in entries:
            if not entry.is_file():
                continue
            ext = os.path.splitext(entry.name)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            if filter_ext and ext != filter_ext:
                continue

            stat = entry.stat()
            cls = classify_file(entry.name, entry.path)

            files_found.append({
                "name": entry.name,
                "path": entry.path,
                "size_kb": round(stat.st_size / 1024, 1),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "extension": ext,
                "category": cls.get("category", "ai_discussions"),
                "category_label": cls.get("label", "Discussion Export")
            })
    except Exception as e:
        return {"error": f"Failed to read inbox directory: {e}"}

    # Sort newest first
    files_found.sort(key=lambda x: x["modified_at"], reverse=True)
    selected = files_found[:limit]

    return {
        "success": True,
        "inbox_directory": BRAINSTORM_INBOX_DIR,
        "count": len(selected),
        "total_files": len(files_found),
        "files": selected
    }


@mcp.tool()
def ingest_brainstorm(
    file_name_or_path: str,
    extract_structure: bool = True
) -> dict:
    """
    Read, sanitize, and parse a chatbot discussion export (.docx, .md, .txt, .pdf, .json).
    Applies comprehensive Indirect Prompt Injection sanitization (steganography stripping,
    hidden comment neutralization, and immutable XML sandboxing).

    Extracts:
    - Inferred Title / Topic
    - Executive Summary
    - Architectural & Technical Decisions
    - Actionable Roadmap Items / Checklists with priority ratings

    Args:
        file_name_or_path: File name inside ~/.brainstorm-inbox/ or absolute/relative file path.
        extract_structure: Whether to extract structured decisions and action items (default True).

    Returns:
        Sandboxed markdown content, security audit warnings, and structured architecture plan.
    """
    try:
        resolved_path = _resolve_file_path(file_name_or_path)
    except FileNotFoundError as e:
        return {"error": str(e)}

    try:
        raw_content = _parse_file(resolved_path)
    except Exception as e:
        return {"error": f"Failed to parse file '{file_name_or_path}': {e}"}

    # Apply Prompt Injection Defense Layer
    sanitized_content, security_warnings = sanitize_text(raw_content)
    sandboxed_envelope = wrap_sandboxed_content(
        clean_text=sanitized_content,
        source_name=os.path.basename(resolved_path),
        warnings=security_warnings
    )

    stat = os.stat(resolved_path)
    cls = classify_file(os.path.basename(resolved_path), resolved_path)

    result = {
        "success": True,
        "file_name": os.path.basename(resolved_path),
        "file_path": resolved_path,
        "file_size_kb": round(stat.st_size / 1024, 1),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        "security_warnings": security_warnings,
        "is_sanitized": True,
        "sandboxed_envelope": sandboxed_envelope
    }

    if extract_structure:
        # Extract structure from the clean, sanitized content
        structure = extract_discussion_structure(sanitized_content, os.path.basename(resolved_path))
        result["structure"] = structure

    return result


@mcp.tool()
def export_brainstorm_to_roadmap(
    file_name_or_path: str,
    format: str = "markdown",
    output_file: str = "ROADMAP.md"
) -> dict:
    """
    Convert actionable roadmap items from an AI brainstorm export directly into
    a clean project roadmap file (Markdown or JSON).

    Args:
        file_name_or_path: Name of the file in ~/.brainstorm-inbox/ or absolute path.
        format: 'markdown' (creates a GitHub Flavored checklist) or 'json'.
        output_file: Output path (default 'ROADMAP.md').

    Returns:
        Summary of created roadmap file and task breakdown.
    """
    parsed = ingest_brainstorm(file_name_or_path, extract_structure=True)
    if "error" in parsed:
        return parsed

    structure = parsed.get("structure", {})
    action_items = structure.get("action_items", [])
    title = structure.get("title", "Project Roadmap")

    if not action_items:
        action_items = [{
            "title": f"Review & Implement: {title}",
            "description": structure.get("summary", "Synthesized from discussion export."),
            "priority": "P2 - Medium"
        }]

    if format.lower() == "json":
        return export_tasks_to_json(
            action_items=action_items,
            title=title,
            source_name=parsed["file_name"],
            output_path=output_file
        )
    else:
        return export_tasks_to_markdown(
            action_items=action_items,
            title=title,
            source_name=parsed["file_name"],
            output_path=output_file
        )


@mcp.tool()
def search_inbox(
    query: str,
    limit: int = 10
) -> dict:
    """
    Fast full-text search across all AI chat sessions and documents in the safe inbox.

    Args:
        query: Search keywords or technical terms (e.g. 'PostgreSQL', 'Auth', 'Architecture').
        limit: Maximum number of matching files to return (default 10).

    Returns:
        Matching files and snippet lines where query appears.
    """
    if not query or not query.strip():
        return {"error": "Query string is required."}

    q_lower = query.strip().lower()
    inbox_files = list_inbox_brainstorms(limit=50)
    files = inbox_files.get("files", [])

    matches = []
    for f_meta in files:
        f_path = f_meta["path"]
        try:
            content = _parse_file(f_path)
        except Exception:
            continue

        if q_lower in content.lower():
            context_lines = []
            for i, line in enumerate(content.splitlines()):
                if q_lower in line.lower():
                    context_lines.append(f"Line {i+1}: {line.strip()[:160]}")
                if len(context_lines) >= 4:
                    break

            matches.append({
                "file_name": f_meta["name"],
                "file_path": f_path,
                "modified_at": f_meta["modified_at"],
                "matches_count": content.lower().count(q_lower),
                "snippets": context_lines
            })
            if len(matches) >= limit:
                break

    return {
        "success": True,
        "query": query,
        "matched_files_count": len(matches),
        "matches": matches
    }


@mcp.tool()
def export_brainstorm_to_myplanner(
    file_name_or_path: str,
    category: str = "Ideation",
    sprint: str = "active"
) -> dict:
    """
    Extract actionable roadmap items from an AI chat export and convert them into
    trackable tasks in MyPlanner (if MyPlanner database is configured).

    Args:
        file_name_or_path: Name of the file in ~/.brainstorm-inbox/ or full path.
        category: MyPlanner category name (default 'Ideation').
        sprint: Target sprint name or 'active' for current sprint (default 'active').

    Returns:
        Summary of created tasks or instructions if MyPlanner database is absent.
    """
    if not is_myplanner_available():
        return {
            "error": "MyPlanner database is not configured or not found. "
                     "Use 'export_brainstorm_to_roadmap' to export to ROADMAP.md instead, "
                     "or configure PLANNER_DB environment variable."
        }

    parsed = ingest_brainstorm(file_name_or_path, extract_structure=True)
    if "error" in parsed:
        return parsed

    structure = parsed.get("structure", {})
    action_items = structure.get("action_items", [])
    title = structure.get("title", "Ideation Task")

    if not action_items:
        action_items = [{
            "title": f"Review & Synthesize: {title}",
            "description": structure.get("summary", "Review discussion document and extract action plan."),
            "priority": "P2 - Medium"
        }]

    res = import_tasks_from_action_items(
        action_items=action_items,
        file_name=parsed["file_name"],
        category_name=category,
        sprint_name=sprint
    )

    return {
        "success": True,
        "message": f"Successfully imported {res['count']} tasks into MyPlanner.",
        "imported_count": res["count"],
        "category": category,
        "sprint": sprint,
        "tasks": res["created_tasks"]
    }


# Backwards compatibility aliases
read_chat_discussion = ingest_brainstorm
list_recent_discussions = list_inbox_brainstorms
import_discussion_to_myplanner = export_brainstorm_to_myplanner

if __name__ == "__main__":
    _ensure_inbox_exists()
    mcp.run()
