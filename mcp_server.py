import os
import glob
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from mcp.server.mcpserver import MCPServer

from parsers.docx_parser import parse_docx
from parsers.pdf_parser import parse_pdf
from parsers.text_parser import parse_text_or_json
from parsers.extractor import extract_discussion_structure
from myplanner_bridge import import_tasks_from_action_items, create_task_in_myplanner
from classifier import classify_file
from organizer import (
    scan_and_plan_organization,
    execute_organization,
    file_document_to_project as do_file_to_project,
    KNOWN_PROJECT_TARGETS
)

# Initialize MCPServer
mcp = MCPServer("downloads")

DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "/mnt/c/Users/lokes/Downloads")
SUPPORTED_EXTENSIONS = {".docx", ".md", ".txt", ".pdf", ".json"}

def _resolve_file_path(file_name: str) -> str:
    """Resolve file name against DOWNLOADS_DIR or its subfolders."""
    if os.path.isabs(file_name) and os.path.exists(file_name):
        return file_name

    # Check root Downloads directory
    candidate = os.path.join(DOWNLOADS_DIR, file_name)
    if os.path.exists(candidate):
        return candidate

    # Search case-insensitively in root Downloads and all subfolders
    target_lower = file_name.lower()
    for root, dirs, files in os.walk(DOWNLOADS_DIR):
        for fname in files:
            if fname.lower() == target_lower:
                return os.path.join(root, fname)

    raise FileNotFoundError(f"File '{file_name}' not found in '{DOWNLOADS_DIR}' or its subfolders.")

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
        raise ValueError(f"Unsupported file format '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}")


@mcp.tool()
def list_recent_discussions(
    limit: int = 15,
    days: int = 30,
    category: str = "ai_discussions",
    file_type: str = ""
) -> dict:
    """
    Scan the Downloads folder for recent AI chat exports, brainstorming documents,
    and technical roadmaps. Automatically filters out school homework and generic files
    by default using heuristic classification.

    Args:
        limit: Maximum number of files to return (default 15).
        days: Lookback window in days (default 30).
        category: Filter category ('ai_discussions', 'all', 'academic_cbse', 'resumes_career', 'official_financial'). Default is 'ai_discussions'.
        file_type: Optional extension filter (e.g. 'docx', 'md', 'pdf', 'json', 'txt').

    Returns:
        Dictionary with list of classified files, metadata, categories, and preview snippets.
    """
    if not os.path.exists(DOWNLOADS_DIR):
        return {"error": f"Downloads directory not found at: {DOWNLOADS_DIR}"}

    cutoff = datetime.now() - timedelta(days=days)
    filter_ext = f".{file_type.lower().lstrip('.')}" if file_type else ""

    files_found = []
    category_counts = {}

    # Scan both root Downloads and immediate subfolders (like AI_Brainstorming)
    scan_paths = [DOWNLOADS_DIR]
    try:
        for entry in os.scandir(DOWNLOADS_DIR):
            if entry.is_dir() and not entry.name.startswith("."):
                scan_paths.append(entry.path)
    except Exception:
        pass

    for folder in scan_paths:
        try:
            entries = os.scandir(folder)
        except Exception:
            continue

        for entry in entries:
            if not entry.is_file():
                continue
            ext = os.path.splitext(entry.name)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            if filter_ext and ext != filter_ext:
                continue
            if entry.name.startswith("~$"):
                continue

            try:
                stat = entry.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                if mtime >= cutoff:
                    cls = classify_file(entry.name, entry.path)
                    cat = cls["category"]
                    category_counts[cat] = category_counts.get(cat, 0) + 1

                    if category != "all" and cat != category:
                        continue

                    files_found.append({
                        "name": entry.name,
                        "path": entry.path,
                        "folder": os.path.basename(folder) if folder != DOWNLOADS_DIR else "Downloads",
                        "category": cat,
                        "category_label": cls["label"],
                        "size_kb": round(stat.st_size / 1024, 1),
                        "modified_at": mtime.strftime("%Y-%m-%d %H:%M"),
                        "mtime_raw": stat.st_mtime,
                        "extension": ext
                    })
            except Exception:
                continue

    # Sort by modification time descending
    files_found.sort(key=lambda x: x["mtime_raw"], reverse=True)
    selected = files_found[:limit]

    # Quick preview snippets
    for f in selected:
        del f["mtime_raw"]
        snippet = ""
        try:
            if f["extension"] in (".md", ".txt"):
                with open(f["path"], "r", encoding="utf-8", errors="ignore") as fl:
                    snippet = fl.read(200).replace("\n", " ").strip()
            elif f["extension"] == ".docx":
                snippet = "Word document roadmap"
            elif f["extension"] == ".pdf":
                snippet = "PDF document"
            elif f["extension"] == ".json":
                snippet = "JSON structured export"
        except Exception:
            pass
        f["preview_snippet"] = snippet

    return {
        "success": True,
        "count": len(selected),
        "total_matching": len(files_found),
        "filter_category": category,
        "all_categories_in_window": category_counts,
        "lookback_days": days,
        "downloads_dir": DOWNLOADS_DIR,
        "files": selected
    }


@mcp.tool()
def read_chat_discussion(
    file_name: str,
    extract_structure: bool = True
) -> dict:
    """
    Read and parse a downloaded AI discussion or document (.docx, .md, .txt, .pdf, .json).
    Reconstructs clean, formatted Markdown and extracts key architectural decisions,
    executive summaries, and actionable roadmap items.

    Args:
        file_name: Name of the file in Downloads or subfolders (or full absolute path).
        extract_structure: Whether to extract structured decisions and action items (default True).

    Returns:
        Dictionary containing full markdown content, file classification, and extracted discussion structure.
    """
    try:
        resolved_path = _resolve_file_path(file_name)
    except FileNotFoundError as e:
        return {"error": str(e)}

    try:
        raw_markdown = _parse_file(resolved_path)
    except Exception as e:
        return {"error": f"Failed to parse file '{file_name}': {e}"}

    stat = os.stat(resolved_path)
    cls = classify_file(os.path.basename(resolved_path), resolved_path)

    result = {
        "success": True,
        "file_name": os.path.basename(resolved_path),
        "file_path": resolved_path,
        "category": cls["category"],
        "category_label": cls["label"],
        "file_size_kb": round(stat.st_size / 1024, 1),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        "full_content": raw_markdown
    }

    if extract_structure:
        structure = extract_discussion_structure(raw_markdown, os.path.basename(resolved_path))
        result["structure"] = structure

    return result


@mcp.tool()
def search_chat_discussions(
    query: str,
    limit: int = 10,
    max_files: int = 40,
    category: str = "ai_discussions"
) -> dict:
    """
    Fast full-text search across downloaded AI chat sessions and documents
    in the Downloads folder and organized subfolders.

    Args:
        query: Search keywords or technical terms (e.g. 'MCP', 'Agent Runtime', 'SQLite').
        limit: Maximum number of matching files to return (default 10).
        max_files: Maximum number of recent files to scan (default 40).
        category: Filter by category ('ai_discussions', 'all'). Default 'ai_discussions'.

    Returns:
        Dictionary with matching files and context snippets showing lines where query appears.
    """
    if not query or not query.strip():
        return {"error": "Query string is required."}

    q_lower = query.strip().lower()
    recent = list_recent_discussions(limit=max_files, days=90, category=category)
    files = recent.get("files", [])

    matches = []
    for f_meta in files:
        f_path = f_meta["path"]
        try:
            content = _parse_file(f_path)
        except Exception:
            continue

        if q_lower in content.lower():
            # Extract matching context lines
            context_lines = []
            for i, line in enumerate(content.splitlines()):
                if q_lower in line.lower():
                    context_lines.append(f"Line {i+1}: {line.strip()}")
                if len(context_lines) >= 4:
                    break

            matches.append({
                "file_name": f_meta["name"],
                "file_path": f_path,
                "category": f_meta.get("category", "other"),
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
def organize_downloads(
    category: str = "all",
    dry_run: bool = True,
    days: int = 180
) -> dict:
    """
    Organize the Windows Downloads folder by automatically categorizing and moving files
    into structured subdirectories:
    - AI_Brainstorming: AI chat exports, tech roadmaps, programming specs
    - School_CBSE: School/CBSE assignments and question papers
    - Resumes_Career: Resumes, CVs, job profiles
    - Official_Financial: Challans, invoices, tax documents, receipts
    - Media_Photos: Photos, images, audio, video

    Args:
        category: Target category to organize ('all', 'ai_discussions', 'academic_cbse', 'resumes_career', 'official_financial', 'media').
        dry_run: If True (default), previews what would be moved without moving anything. Set to False to execute!
        days: Lookback window in days (default 180).

    Returns:
        Summary of planned or executed file moves.
    """
    return execute_organization(category_filter=category, days=days, dry_run=dry_run, downloads_dir=DOWNLOADS_DIR)


@mcp.tool()
def file_discussion_to_project(
    file_name: str,
    target_project: str = "tekku_research",
    copy_or_move: str = "copy"
) -> dict:
    """
    Pick a specific document from Downloads and file/copy it directly into an active project:
    - 'tekku_research': Places it in nextgen-technologies/article_research/
    - 'study_notes': Places it in nextgen-technologies/study_notes/
    - 'ai_brainstorming': Places it in Downloads/AI_Brainstorming/
    - Or any custom absolute directory path.

    Args:
        file_name: Name of the file in Downloads or subfolders.
        target_project: Target destination ('tekku_research', 'study_notes', 'ai_brainstorming', or custom path). Default is 'tekku_research'.
        copy_or_move: 'copy' (default) or 'move'.

    Returns:
        Destination path and file details.
    """
    return do_file_to_project(file_name=file_name, target_project=target_project, copy_or_move=copy_or_move, downloads_dir=DOWNLOADS_DIR)


@mcp.tool()
def import_discussion_to_myplanner(
    file_name: str,
    category: str = "Ideation",
    sprint: str = "active"
) -> dict:
    """
    Automatically extract actionable roadmap items from a downloaded AI chat export
    or technical document and convert them into trackable tasks in MyPlanner.

    Args:
        file_name: Name of the file in Downloads (or full path).
        category: MyPlanner category name (default 'Ideation').
        sprint: Target sprint name or 'active' for current sprint (default 'active').

    Returns:
        Summary of created tasks with their IDs, titles, and assigned sprint/category.
    """
    try:
        resolved_path = _resolve_file_path(file_name)
    except FileNotFoundError as e:
        return {"error": str(e)}

    try:
        content = _parse_file(resolved_path)
    except Exception as e:
        return {"error": f"Failed to parse file: {e}"}

    structure = extract_discussion_structure(content, os.path.basename(resolved_path))
    action_items = structure.get("action_items", [])

    if not action_items:
        action_items = [{
            "title": f"Review & Synthesize: {structure.get('title', file_name)}",
            "description": structure.get("summary", "Review discussion document and extract action plan."),
            "priority": "P2 - Medium"
        }]

    res = import_tasks_from_action_items(
        action_items=action_items,
        file_name=os.path.basename(resolved_path),
        category_name=category,
        sprint_name=sprint
    )

    return {
        "success": True,
        "message": f"Successfully imported {res['count']} tasks from '{os.path.basename(resolved_path)}' into MyPlanner.",
        "imported_count": res["count"],
        "category": category,
        "sprint": sprint,
        "tasks": res["created_tasks"]
    }


if __name__ == "__main__":
    mcp.run()
